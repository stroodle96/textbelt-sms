# Copyright (c) 2026 Textbelt SMS contributors
"""Native routing behavior at the verified ingress and owned worker boundary."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

# Literal HTTP status/cap values are behavioral contracts.
# ruff: noqa: PLR2004, PLC0415, SLF001
from aiohttp.test_utils import make_mocked_request
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms import conversation
from custom_components.textbelt_sms.assist import AssistResult
from custom_components.textbelt_sms.sender import PartResult, SendResult
from custom_components.textbelt_sms.state import ReplyState, ReplyStorageError
from custom_components.textbelt_sms.webhook import async_verify_reply

PHONE = "+15551234567"
OTHER = "+15551234568"


class Body:
    """Stream an independently signed callback body."""

    def __init__(self, raw: Any) -> None:
        """Retain the bounded fixture bytes."""
        self.raw = raw

    async def iter_chunked(self, _size: Any) -> Any:
        """Yield the transport body to the real parser."""
        yield self.raw


async def packet(text: Any = "hello", phone: Any = PHONE, text_id: Any = None) -> Any:
    """Packet."""
    raw = json.dumps(
        {
            "textId": text_id or ("out" if phone == PHONE else "other"),
            "fromNumber": phone,
            "text": text,
        }
    ).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(
        b"secret", timestamp.encode() + raw, hashlib.sha256
    ).hexdigest()
    req = make_mocked_request(
        "POST",
        "/",
        headers={
            "Content-Type": "application/json",
            "X-textbelt-timestamp": timestamp,
            "X-textbelt-signature": signature,
        },
        payload=Body(raw),
    )
    return await async_verify_reply(req, api_key="secret", entry_id="entry")


@pytest.fixture
async def manager(hass: Any, monkeypatch: Any) -> Any:
    """Create an owned manager with real parser and durable state."""
    entry = MockConfigEntry(
        domain="textbelt_sms",
        entry_id="entry",
        data={"api_key": "secret"},
        options={"assist_enabled": True, "authorized_senders": [PHONE, OTHER]},
    )
    entry.add_to_hass(hass)
    state = ReplyState(hass, "entry")
    await state.async_load()
    for phone in (PHONE, OTHER):
        state.record_send_result(
            SendResult(
                (PartResult(1, "out" if phone == PHONE else "other", "accepted"),),
                1,
                "accepted",
            ),
            phone,
        )
    runtime = SimpleNamespace(
        active=True,
        async_send=AsyncMock(),
        reply_url=lambda **_kwargs: "https://ha.example/api/webhook/id",
    )
    monkeypatch.setattr(
        conversation, "async_resolve_pipeline", lambda *_: SimpleNamespace(id="first")
    )
    monkeypatch.setattr(
        conversation,
        "async_run_assist",
        AsyncMock(return_value=AssistResult("first", "agent", "Done", None, "ha")),
    )
    obj = conversation.ConversationManager(hass, entry, state, runtime)
    obj.start()
    yield obj
    await obj.async_shutdown()


async def test_durable_duplicate_and_fifo(manager: Any, monkeypatch: Any) -> None:
    """Durable duplicate and fifo."""
    entered, release = asyncio.Event(), asyncio.Event()
    calls = []

    async def run(_hass: Any, **kwargs: Any) -> None:
        """Run."""
        calls.append(kwargs["text"])
        if len(calls) == 1:
            entered.set()
            await release.wait()
        return AssistResult("first", "agent", "Done", None, "ha")

    monkeypatch.setattr(conversation, "async_run_assist", run)
    first = await packet("one")
    assert await manager.async_handle_reply(first) == 200
    await entered.wait()
    assert await manager.async_handle_reply(first) == 200
    assert await manager.async_handle_reply(await packet("two")) == 200
    assert calls == ["one"]
    release.set()
    await manager.async_wait_idle()
    assert calls == ["one", "two"]
    assert manager.runtime.async_send.await_count == 2


async def test_capacity_before_claim_and_save_failure(
    manager: Any, monkeypatch: Any
) -> None:
    """Capacity before claim and save failure."""
    entered = asyncio.Event()

    async def run(*_args: Any, **_kwargs: Any) -> None:
        entered.set()
        await asyncio.Event().wait()

    monkeypatch.setattr(conversation, "async_run_assist", run)
    replies = [await packet(str(i)) for i in range(11)]
    for reply in replies[:10]:
        assert await manager.async_handle_reply(reply) == 200
    await entered.wait()
    assert await manager.async_handle_reply(replies[10]) == 429
    assert not manager.state.is_duplicate(replies[10])
    assert await manager.async_handle_reply(replies[0]) == 200
    await manager.async_policy_changed()
    # Fail the actual persistence boundary, not admission itself.
    monkeypatch.setattr(
        manager.state._store,
        "async_save",
        AsyncMock(side_effect=ReplyStorageError("save")),
    )
    assert await manager.async_handle_reply(replies[10]) == 503
    assert not manager.state.is_duplicate(replies[10])
    await manager.async_shutdown()


async def test_controls_new_and_live_revoke(manager: Any) -> None:
    """Controls new and live revoke."""
    run = conversation.async_run_assist
    for text in (" STOP ", "start", "help"):
        assert await manager.async_handle_reply(await packet(text)) == 200
    assert await manager.async_handle_reply(await packet(" /NeW ")) == 200
    await manager.async_wait_idle()
    run.assert_not_awaited()
    assert manager.runtime.async_send.await_count == 1
    manager.hass.config_entries.async_update_entry(
        manager.entry, options={"assist_enabled": False}
    )
    await manager.async_policy_changed()
    assert await manager.async_handle_reply(await packet("new input")) == 200
    await manager.async_wait_idle()
    run.assert_not_awaited()


async def test_inflight_revocation_blocks_completed_reply(
    manager: Any, monkeypatch: Any
) -> None:
    """Inflight revocation blocks completed reply."""
    entered, release = asyncio.Event(), asyncio.Event()

    async def run(*_args: Any, **_kwargs: Any) -> None:
        entered.set()
        await release.wait()
        return AssistResult("first", "agent", "Done", None, "ha")

    monkeypatch.setattr(conversation, "async_run_assist", run)
    await manager.async_handle_reply(await packet())
    await entered.wait()
    manager.hass.config_entries.async_update_entry(
        manager.entry, options={"assist_enabled": True, "authorized_senders": []}
    )
    release.set()
    await manager.async_wait_idle()
    manager.runtime.async_send.assert_not_awaited()


async def test_different_senders_run_concurrently(
    manager: Any, monkeypatch: Any
) -> None:
    """Different senders run concurrently."""
    started = set()
    both = asyncio.Event()
    release = asyncio.Event()

    async def run(_hass: Any, **kwargs: Any) -> None:
        """Run."""
        started.add(kwargs["text"])
        if len(started) == 2:
            both.set()
        await release.wait()
        return AssistResult("first", kwargs["text"], "Done", None, kwargs["text"])

    monkeypatch.setattr(conversation, "async_run_assist", run)
    await manager.async_handle_reply(await packet("phone1"))
    await manager.async_handle_reply(await packet("phone2", OTHER))
    await asyncio.wait_for(both.wait(), 2)
    assert started == {"phone1", "phone2"}
    release.set()
    await manager.async_wait_idle()
    assert len(manager.sessions) == 2


async def test_concurrent_capacity_reservation_is_atomic(
    manager: Any, monkeypatch: Any
) -> None:
    """Concurrent capacity reservation is atomic."""

    async def run(*_args: Any, **_kwargs: Any) -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(conversation, "async_run_assist", run)
    replies = [await packet(f"concurrent{i}") for i in range(20)]
    results = await asyncio.gather(
        *(manager.async_handle_reply(reply) for reply in replies)
    )
    assert results.count(200) == 10
    assert results.count(429) == 10
    assert sum(manager.state.is_duplicate(reply) for reply in replies) == 10


async def test_global_capacity_counts_active_and_queued(
    manager: Any, monkeypatch: Any
) -> None:
    """Global capacity counts active and queued."""
    phones = [f"+155512345{n:02}" for n in range(6)]
    manager.hass.config_entries.async_update_entry(
        manager.entry, options={"assist_enabled": True, "authorized_senders": phones}
    )
    for phone in phones:
        manager.state.record_send_result(
            SendResult((PartResult(1, phone, "accepted"),), 1, "accepted"), phone
        )

    async def run(*_args: Any, **_kwargs: Any) -> None:
        await asyncio.Event().wait()

    monkeypatch.setattr(conversation, "async_run_assist", run)
    for phone in phones[:5]:
        for n in range(10):
            assert (
                await manager.async_handle_reply(
                    await packet(str(n), phone, text_id=phone)
                )
                == 200
            )
    rejected = await packet("no room", phones[5], text_id=phones[5])
    assert await manager.async_handle_reply(rejected) == 429
    assert not manager.state.is_duplicate(rejected)


async def test_pipeline_change_expiry_new_and_missing_selection(
    manager: Any, monkeypatch: Any
) -> None:
    """Pipeline change expiry new and missing selection."""
    selected = ["first"]

    def resolve(*_args: Any) -> None:
        """Resolve."""
        if selected[0] is None:
            message = "deleted"
            raise ValueError(message)
        return SimpleNamespace(id=selected[0])

    monkeypatch.setattr(conversation, "async_resolve_pipeline", resolve)

    async def run(_hass: Any, **kwargs: Any) -> None:
        """Run."""
        return AssistResult(
            kwargs["pipeline_id"],
            "id-" + kwargs["pipeline_id"],
            "Done",
            None,
            "ha-" + kwargs["pipeline_id"],
        )

    adapter = AsyncMock(side_effect=run)
    monkeypatch.setattr(conversation, "async_run_assist", adapter)
    await manager.async_handle_reply(await packet("first"))
    await manager.async_wait_idle()
    await manager.async_handle_reply(await packet("second"))
    await manager.async_wait_idle()
    assert adapter.call_args.kwargs["conversation_id"] == "id-first"
    selected[0] = "second"
    await manager.async_handle_reply(await packet("changed"))
    await manager.async_wait_idle()
    assert adapter.call_args.kwargs["conversation_id"] is None
    session = next(iter(manager.sessions.values()))
    session.last_activity -= 1800
    await manager.async_handle_reply(await packet("expired"))
    await manager.async_wait_idle()
    assert adapter.call_args.kwargs["conversation_id"] is None
    selected[0] = None
    await manager.async_handle_reply(await packet("deleted"))
    await manager.async_wait_idle()
    assert not manager.sessions
    assert (
        "Check Home Assistant before resending"
        in manager.runtime.async_send.call_args.args[2]
    )


@pytest.mark.parametrize(
    "result",
    [
        AssistResult("first", "id", "漢", None, "ha"),
        AssistResult("first", "id", "", "empty_reply", "ha"),
        AssistResult("first", "id", "", "timeout", "ha"),
    ],
)
async def test_safe_reply_for_unsupported_empty_or_uncertain_pipeline(
    manager: Any, monkeypatch: Any, result: Any
) -> None:
    """Safe reply for unsupported empty or uncertain pipeline."""
    adapter = AsyncMock(return_value=result)
    monkeypatch.setattr(conversation, "async_run_assist", adapter)
    await manager.async_handle_reply(await packet())
    await manager.async_wait_idle()
    text = manager.runtime.async_send.call_args.args[2]
    assert "Check Home Assistant before resending" in text
    assert manager.runtime.async_send.call_args.kwargs["mode"] == "assist"
    assert manager.runtime.async_send.call_args.kwargs["compact"] is True
    assert adapter.await_count == 1


async def test_response_failure_never_replays_action(manager: Any) -> None:
    """Response failure never replays action."""
    from homeassistant.core import HomeAssistantError

    manager.runtime.async_send.side_effect = HomeAssistantError("failed")
    await manager.async_handle_reply(await packet())
    await manager.async_wait_idle()
    assert conversation.async_run_assist.await_count == 1
    assert manager.runtime.async_send.await_count == 1


async def test_real_ha_history_kept_beyond_five_minutes_and_dropped_at_sms_expiry(
    manager: Any, freezer: Any
) -> None:
    """Real ha history kept beyond five minutes and dropped at sms expiry."""
    from datetime import timedelta

    from homeassistant.components import conversation as native
    from homeassistant.core import Context
    from homeassistant.helpers import chat_session
    from homeassistant.util import dt as dt_util
    from pytest_homeassistant_custom_component.common import async_fire_time_changed

    from custom_components.textbelt_sms.conversation import ConversationSession

    with chat_session.async_get_chat_session(manager.hass) as session:
        identity = session.conversation_id
        user = native.ConversationInput(
            text="hello",
            context=Context(),
            conversation_id=identity,
            language="en",
            agent_id="homeassistant",
            device_id=None,
            satellite_id=None,
        )
        with native.async_get_chat_log(manager.hass, session, user) as log:
            log.async_add_assistant_content_without_tools(
                native.AssistantContent(
                    agent_id="homeassistant", content="Remember this"
                )
            )
    manager.clock = lambda: dt_util.utcnow().timestamp()
    key = (manager.entry.entry_id, PHONE, "first")
    manager.sessions[key] = ConversationSession(
        "legacy-agent", identity, manager.clock()
    )
    for _n in range(4):
        freezer.tick(timedelta(seconds=120))
        manager.maintain_sessions()
        async_fire_time_changed(manager.hass, dt_util.utcnow())
        await manager.hass.async_block_till_done()
    assert manager.sessions[key].ha_session_id == identity
    assert manager.sessions[key].conversation_id == "legacy-agent"
    assert (
        manager.hass.data["conversation_chat_logs"][identity].content[-1].content
        == "Remember this"
    )
    conversation.async_run_assist.assert_not_awaited()
    manager.runtime.async_send.assert_not_awaited()
    freezer.tick(timedelta(seconds=1320))
    manager.maintain_sessions()
    assert not manager.sessions
    async_fire_time_changed(manager.hass, dt_util.utcnow())
    await manager.hass.async_block_till_done()
    assert identity not in manager.hass.data[chat_session.DATA_CHAT_SESSION]
    assert identity not in manager.hass.data["conversation_chat_logs"]


async def test_lost_ulid_history_is_not_resurrected(manager: Any) -> None:
    """Lost ulid history is not resurrected."""
    from homeassistant.helpers import chat_session

    from custom_components.textbelt_sms.conversation import ConversationSession

    with chat_session.async_get_chat_session(manager.hass) as session:
        identity = session.conversation_id
    manager.hass.data[chat_session.DATA_CHAT_SESSION].pop(identity).async_cleanup()
    manager.sessions[(manager.entry.entry_id, PHONE, "first")] = ConversationSession(
        identity, identity, manager.clock()
    )
    manager.maintain_sessions()
    assert not manager.sessions


async def test_malformed_options_fail_closed_and_legacy_is_never_native(
    manager: Any,
) -> None:
    """Malformed options fail closed and legacy is never native."""
    manager.hass.config_entries.async_update_entry(
        manager.entry, options={"assist_enabled": "yes"}
    )
    assert await manager.async_handle_reply(await packet()) == 403
    assert not manager.sessions
    manager.hass.config_entries.async_update_entry(
        manager.entry, options={"assist_enabled": True, "authorized_senders": [PHONE]}
    )
    assert (
        await manager.async_handle_reply(
            await packet("historic", text_id="unknown"), legacy=True
        )
        == 200
    )
    await manager.async_wait_idle()
    conversation.async_run_assist.assert_not_awaited()


async def test_restart_preserves_admission_without_sessions_or_replay(
    manager: Any,
) -> None:
    """A restart restores duplicate metadata but never turns or volatile history."""
    reply = await packet("before restart")
    await manager.async_handle_reply(reply)
    await manager.async_wait_idle()
    await manager.async_shutdown()
    state = ReplyState(manager.hass, manager.entry.entry_id)
    await state.async_load()
    restarted = conversation.ConversationManager(
        manager.hass, manager.entry, state, manager.runtime
    )
    restarted.start()
    try:
        assert not restarted.sessions
        assert await restarted.async_handle_reply(reply) == 200
        await restarted.async_wait_idle()
        assert conversation.async_run_assist.await_count == 1
        assert manager.runtime.async_send.await_count == 1
    finally:
        await restarted.async_shutdown()


async def test_prestart_worker_cancellation_releases_all_reservations(
    manager: Any,
) -> None:
    """Release queue capacity when cancelling an unstarted worker."""
    assert await manager.async_handle_reply(await packet("not started")) == 200
    await manager.async_policy_changed()
    assert manager._total == 0
    assert not manager._pending
    assert not manager._queues
    assert not manager._workers
    conversation.async_run_assist.assert_not_awaited()
    manager.runtime.async_send.assert_not_awaited()
