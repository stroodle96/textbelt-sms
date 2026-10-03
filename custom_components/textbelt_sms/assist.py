# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Provider-independent text turns through Home Assistant's native pipeline."""

from __future__ import annotations

# Defer HA pipeline imports until native Assist setup installs its dependencies.
# ruff: noqa: PLC0415
import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from xml.etree.ElementTree import ParseError, fromstring

from homeassistant.core import Context, HomeAssistant, callback
from homeassistant.helpers import chat_session
from homeassistant.setup import async_setup_component

if TYPE_CHECKING:
    from homeassistant.components.assist_pipeline import Pipeline, PipelineEvent

from .options import normalize_pipeline_id

DEFAULT_ASSIST_TIMEOUT = 60


@dataclass(frozen=True, slots=True)
class AssistResult:
    """Completed text response or structured failure; never a provider send."""

    pipeline_id: str | None
    conversation_id: str | None
    reply: str
    error_code: str | None
    ha_session_id: str | None = None


async def async_ensure_assist_pipeline(hass: HomeAssistant) -> bool:
    """Initialize HA Assist and its requirements only for native opt-in users."""
    if "assist_pipeline" in hass.data:
        return True
    return await async_setup_component(hass, "assist_pipeline", {})


@callback
def async_resolve_pipeline(hass: HomeAssistant, pipeline_id: str | None) -> Pipeline:
    """Resolve the current preference or explicit ID, raising HA pipeline errors."""
    from homeassistant.components.assist_pipeline import (
        async_get_pipeline,
        async_get_pipelines,
    )
    from homeassistant.components.assist_pipeline.error import PipelineNotFound

    pipeline_id = normalize_pipeline_id(pipeline_id)
    if pipeline_id is not None and pipeline_id not in {
        pipeline.id for pipeline in async_get_pipelines(hass)
    }:
        code = "pipeline_not_found"
        msg = "Selected pipeline no longer exists"
        raise PipelineNotFound(code, msg)
    return async_get_pipeline(hass, pipeline_id)


def _completed_speech(output: dict[str, Any]) -> str:
    """Flatten only completed intent speech, preferring plain text over SSML."""
    speech = output.get("response", {}).get("speech", {})
    plain = speech.get("plain", {}).get("speech")
    if isinstance(plain, str) and plain.strip():
        return plain.strip()
    ssml = speech.get("ssml", {}).get("speech")
    if not isinstance(ssml, str) or not ssml.strip():
        return ""
    try:
        if "<!" in ssml:
            return ""
        root = fromstring(ssml)  # noqa: S314 -- declarations/entities are rejected above.
    except ParseError:
        return ""
    return " ".join("".join(root.itertext()).split())


async def async_run_assist(  # noqa: PLR0913 -- frozen provider-independent interface.
    hass: HomeAssistant,
    *,
    text: str,
    pipeline_id: str | None,
    conversation_id: str | None,
    context: Context,
    timeout: float = DEFAULT_ASSIST_TIMEOUT,  # noqa: ASYNC109 -- owned asyncio.timeout.
) -> AssistResult:
    """Run INTENT through INTENT, with owned timeout/cancellation and no retry."""
    if not await async_ensure_assist_pipeline(hass):
        return AssistResult(pipeline_id, conversation_id, "", "pipeline_unavailable")
    from homeassistant.components.assist_pipeline import (
        PipelineInput,
        PipelineRun,
        PipelineStage,
    )
    from homeassistant.components.assist_pipeline.error import PipelineError

    try:
        pipeline = async_resolve_pipeline(hass, pipeline_id)
    except PipelineError as err:
        return AssistResult(pipeline_id, conversation_id, "", err.code)
    except (KeyError, ValueError):
        return AssistResult(pipeline_id, conversation_id, "", "pipeline_unavailable")

    output: dict[str, Any] | None = None
    error_code: str | None = None
    ended = False

    @callback
    def on_event(event: PipelineEvent) -> None:
        nonlocal output, error_code, ended
        if event.type == "intent-end" and event.data:
            output = event.data.get("intent_output")
        elif event.type == "run-end":
            ended = True
        elif event.type == "error":
            error_code = (event.data or {}).get("code") or "assist_failed"

    cancelled: asyncio.CancelledError | None = None
    # HA's context manager performs cleanup after a normal yield. Catch failures
    # inside it so cancellation also updates/removes the active session context.
    with chat_session.async_get_chat_session(hass, conversation_id) as session:
        run: PipelineRun | None = None
        try:
            async with asyncio.timeout(timeout):
                run = PipelineRun(
                    hass=hass,
                    context=context,
                    pipeline=pipeline,
                    start_stage=PipelineStage.INTENT,
                    end_stage=PipelineStage.INTENT,
                    event_callback=on_event,
                )
                await PipelineInput(
                    run=run, session=session, intent_input=text
                ).execute(validate=True)
        except TimeoutError:
            error_code = "timeout"
        except asyncio.CancelledError as err:
            cancelled = err
        except PipelineError as err:
            error_code = err.code
        except Exception:  # noqa: BLE001 -- isolate arbitrary HA conversation engines.
            error_code = "assist_failed"
        finally:
            # execute validates before entering HA run cleanup. Own that gap.
            if run is not None and not ended:
                await run.end()
        conversation_id = session.conversation_id
    if cancelled is not None:
        raise cancelled
    if error_code:
        return AssistResult(
            pipeline.id, conversation_id, "", error_code, session.conversation_id
        )
    if output is None:
        return AssistResult(
            pipeline.id, conversation_id, "", "empty_reply", session.conversation_id
        )
    conversation_id = output.get("conversation_id") or conversation_id
    reply = _completed_speech(output)
    return AssistResult(
        pipeline.id,
        conversation_id,
        reply,
        None if reply else "empty_reply",
        session.conversation_id,
    )
