# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Pipeline adapter behavior against real HA run/input/session classes."""

from __future__ import annotations

# Fixture-only arguments and HA private run bookkeeping are intentional.
# ruff: noqa: ARG001, PLR0913, PLR0917, SLF001
import asyncio
from dataclasses import replace
from unittest.mock import AsyncMock

import pytest
from homeassistant.components.assist_pipeline.pipeline import (
    KEY_ASSIST_PIPELINE,
    Pipeline,
    PipelineData,
    PipelineEvent,
    PipelineEventType,
    PipelineRun,
    PipelineStorageCollection,
    PipelineStore,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.helpers import chat_session
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms import const
from custom_components.textbelt_sms.assist import (
    async_ensure_assist_pipeline,
    async_run_assist,
)


@pytest.fixture
def pipelines(hass: HomeAssistant) -> PipelineStorageCollection:
    """Use real HA pipeline lookup and run bookkeeping, without services/network."""
    store = PipelineStorageCollection(PipelineStore(hass, 1, "test_pipeline"))
    first = Pipeline(
        conversation_engine="homeassistant",
        conversation_language="en",
        language="en",
        name="First",
        stt_engine=None,
        stt_language=None,
        tts_engine=None,
        tts_language=None,
        tts_voice=None,
        wake_word_entity=None,
        wake_word_id=None,
        id="first",
        prefer_local_intents=True,
    )
    store.data["first"] = first
    store.data["second"] = replace(
        first, id="second", language="fr", conversation_language="fr"
    )
    store.async_set_preferred_item("first")
    hass.data[KEY_ASSIST_PIPELINE] = PipelineData(store)
    return store


@pytest.fixture
def intent_engine(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace only intent preparation/recognition; retain actual input/run cleanup."""
    monkeypatch.setattr(PipelineRun, "prepare_recognize_intent", AsyncMock())

    async def recognize(
        run: PipelineRun, text: str, conversation_id: str, prompt: str | None
    ) -> tuple[str, bool]:
        assert text == "hello"
        assert prompt is None
        assert run.context.user_id == "authorized-user"
        assert chat_session.current_session.get().conversation_id == conversation_id
        assert run.pipeline.prefer_local_intents
        run.process_event(
            PipelineEvent(
                PipelineEventType.INTENT_PROGRESS, {"chat_log_delta": "do not send"}
            )
        )
        run.process_event(
            PipelineEvent(
                PipelineEventType.INTENT_END,
                {
                    "intent_output": {
                        "response": {
                            "speech": {"plain": {"speech": f"Done {run.language}"}},
                            "language": run.language,
                            "response_type": "action_done",
                            "data": {},
                        },
                        "conversation_id": conversation_id,
                        "continue_conversation": False,
                    }
                },
            )
        )
        return "Done", False

    monkeypatch.setattr(PipelineRun, "recognize_intent", recognize)


async def test_current_preference_resolves_each_turn(
    hass: HomeAssistant, pipelines: PipelineStorageCollection, intent_engine: None
) -> None:
    """A preference change changes the actual pipeline/language on the next call."""
    first = await async_run_assist(
        hass,
        text="hello",
        pipeline_id=None,
        conversation_id=None,
        context=Context(user_id="authorized-user"),
    )
    pipelines.async_set_preferred_item("second")
    second = await async_run_assist(
        hass,
        text="hello",
        pipeline_id="preferred",
        conversation_id=first.conversation_id,
        context=Context(user_id="authorized-user"),
    )
    assert (first.pipeline_id, first.reply, first.error_code) == (
        "first",
        "Done en",
        None,
    )
    assert (second.pipeline_id, second.reply, second.error_code) == (
        "second",
        "Done fr",
        None,
    )
    assert first.conversation_id == second.conversation_id
    assert chat_session.current_session.get() is None
    assert not hass.data[KEY_ASSIST_PIPELINE].pipeline_runs._pipeline_runs["first"]


async def test_explicit_deleted_pipeline_never_falls_back(
    hass: HomeAssistant, pipelines: PipelineStorageCollection, intent_engine: None
) -> None:
    """An explicit selection remains fixed and its deletion returns a failure."""
    pipelines.async_set_preferred_item("second")
    result = await async_run_assist(
        hass,
        text="hello",
        pipeline_id="first",
        conversation_id=None,
        context=Context(user_id="authorized-user"),
    )
    assert result.pipeline_id == "first"
    del pipelines.data["first"]
    result = await async_run_assist(
        hass,
        text="hello",
        pipeline_id="first",
        conversation_id=result.conversation_id,
        context=Context(),
    )
    assert result.error_code == "pipeline_not_found"
    assert result.reply == ""


@pytest.mark.parametrize(
    ("speech", "reply", "error"),
    [
        (
            {
                "plain": {"speech": ""},
                "ssml": {
                    "speech": "<speak>All <emphasis>done</emphasis> &amp; ready</speak>"
                },
            },
            "All done & ready",
            None,
        ),
        ({}, "", "empty_reply"),
        ({"ssml": {"speech": "<speak>broken"}}, "", "empty_reply"),
        (
            {"ssml": {"speech": '<!DOCTYPE x [<!ENTITY a "bad">]><speak>&a;</speak>'}},
            "",
            "empty_reply",
        ),
    ],
)
async def test_completed_speech_only(
    hass: HomeAssistant,
    pipelines: PipelineStorageCollection,
    intent_engine: None,
    monkeypatch: pytest.MonkeyPatch,
    speech: dict,
    reply: str,
    error: str | None,
) -> None:
    """Completed speech has safe SSML fallback; fragments cannot produce a reply."""

    async def recognize(run: PipelineRun, *_: object) -> tuple[str, bool]:
        run.process_event(
            PipelineEvent(PipelineEventType.INTENT_PROGRESS, {"speech": "fragment"})
        )
        run.process_event(
            PipelineEvent(
                PipelineEventType.INTENT_END,
                {
                    "intent_output": {
                        "response": {"speech": speech},
                        "conversation_id": "agent-session",
                    }
                },
            )
        )
        return "", False

    monkeypatch.setattr(PipelineRun, "recognize_intent", recognize)
    result = await async_run_assist(
        hass, text="hello", pipeline_id=None, conversation_id=None, context=Context()
    )
    assert result.ha_session_id in hass.data[chat_session.DATA_CHAT_SESSION]
    assert result.ha_session_id != "agent-session"
    assert (result.reply, result.error_code, result.conversation_id) == (
        reply,
        error,
        "agent-session",
    )


async def test_error_event(
    hass: HomeAssistant,
    pipelines: PipelineStorageCollection,
    intent_engine: None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pipeline errors have a structured code and never leak their message into SMS."""

    async def recognize(run: PipelineRun, *_: object) -> tuple[str, bool]:
        run.process_event(
            PipelineEvent(
                PipelineEventType.ERROR,
                {"code": "intent-failed", "message": "sensitive details"},
            )
        )
        return "", False

    monkeypatch.setattr(PipelineRun, "recognize_intent", recognize)
    result = await async_run_assist(
        hass, text="hello", pipeline_id=None, conversation_id=None, context=Context()
    )
    assert (result.reply, result.error_code) == ("", "intent-failed")


@pytest.mark.parametrize("cancel", [False, True])
async def test_timeout_and_cancellation_clean_up(
    hass: HomeAssistant,
    pipelines: PipelineStorageCollection,
    intent_engine: None,
    monkeypatch: pytest.MonkeyPatch,
    *,
    cancel: bool,
) -> None:
    """A stalled engine is cancelled once, run/session cleanup completes, no retry."""
    started = asyncio.Event()
    stopped = asyncio.Event()

    async def recognize(*_: object) -> tuple[str, bool]:
        started.set()
        try:
            await asyncio.Event().wait()
        finally:
            stopped.set()
        return "", False

    monkeypatch.setattr(PipelineRun, "recognize_intent", recognize)
    task = asyncio.create_task(
        async_run_assist(
            hass,
            text="hello",
            pipeline_id=None,
            conversation_id=None,
            context=Context(),
            timeout=0.5 if not cancel else 60,
        )
    )
    await asyncio.wait_for(started.wait(), timeout=2)
    if cancel:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        result = await task
        assert result.error_code == "timeout"
        assert result.reply == ""
    assert stopped.is_set()
    assert not hass.data[KEY_ASSIST_PIPELINE].pipeline_runs._pipeline_runs["first"]
    assert chat_session.current_session.get() is None


async def test_options_enable_selected_pipeline(
    hass: HomeAssistant, pipelines: PipelineStorageCollection
) -> None:
    """Enabling persists normalized independent authorization and a valid pipeline."""
    entry = MockConfigEntry(
        domain=const.DOMAIN,
        data={"api_key": "test-key"},
        options={"future": True, "notification_recipients": ["+15551234568"]},
    )
    entry.add_to_hass(hass)
    hass.config.external_url = "https://ha.example.com"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "assist_enabled": True,
            "pipeline_id": "second",
            "authorized_senders": "+1 (555) 123-4567\n+15551234567",
            "conversation_timeout": 300,
        },
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {
        "future": True,
        "notification_recipients": ["+15551234568"],
        "assist_enabled": True,
        "pipeline_id": "second",
        "authorized_senders": ["+15551234567"],
        "conversation_timeout": 300,
    }


@pytest.mark.parametrize("pipeline_id", ["deleted", "conversation.missing"])
async def test_options_reject_deleted_pipeline(
    hass: HomeAssistant, pipelines: PipelineStorageCollection, pipeline_id: str
) -> None:
    """The options flow never enables a nonexistent explicit pipeline."""
    entry = MockConfigEntry(domain=const.DOMAIN, data={"api_key": "test-key"})
    entry.add_to_hass(hass)
    hass.config.external_url = "https://ha.example.com"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "assist_enabled": True,
            "pipeline_id": pipeline_id,
            "authorized_senders": "+15551234567",
        },
    )
    assert result["errors"] == {"pipeline_id": "invalid_pipeline"}


async def test_options_preferred_stores_no_snapshot(
    hass: HomeAssistant, pipelines: PipelineStorageCollection
) -> None:
    """Preferred UI selection persists None rather than the current preferred ID."""
    entry = MockConfigEntry(domain=const.DOMAIN, data={"api_key": "test-key"})
    entry.add_to_hass(hass)
    hass.config.external_url = "https://ha.example.com"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "assist_enabled": True,
            "pipeline_id": "preferred",
            "authorized_senders": "+15551234567",
        },
    )
    assert result["data"]["pipeline_id"] is None


async def test_native_enable_sets_up_pipeline(
    hass: HomeAssistant,
    pipelines: PipelineStorageCollection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Native enable initializes HA Assist if it was not already configured."""
    data = hass.data.pop(KEY_ASSIST_PIPELINE)

    async def setup(target_hass: HomeAssistant, domain: str, config: dict) -> bool:
        assert target_hass is hass
        assert domain == "assist_pipeline"
        assert config == {}
        hass.data[KEY_ASSIST_PIPELINE] = data
        return True

    monkeypatch.setattr(
        "custom_components.textbelt_sms.assist.async_setup_component", setup
    )
    assert await async_ensure_assist_pipeline(hass)
    assert hass.data[KEY_ASSIST_PIPELINE].pipeline_store.data["first"].id == "first"


async def test_timeout_during_validation_cleans_run(
    hass: HomeAssistant,
    pipelines: PipelineStorageCollection,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cancellation before HA execute enters its run try/finally still owns cleanup."""

    async def prepare(*_: object) -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(PipelineRun, "prepare_recognize_intent", prepare)
    result = await async_run_assist(
        hass,
        text="hello",
        pipeline_id=None,
        conversation_id=None,
        context=Context(),
        timeout=0.5,
    )
    assert result.error_code == "timeout"
    assert not hass.data[KEY_ASSIST_PIPELINE].pipeline_runs._pipeline_runs["first"]
