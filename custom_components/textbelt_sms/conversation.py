# Copyright (c) 2026 Textbelt SMS contributors
"""Entry-owned verified reply admission, native turns and session maintenance."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass
from http import HTTPStatus
from typing import TYPE_CHECKING

from homeassistant.core import Context, HomeAssistantError
from homeassistant.helpers import chat_session

from .assist import async_resolve_pipeline, async_run_assist
from .const import EVENT_REPLY, LOGGER, reply_key_usable
from .message import prepare_message
from .models import MessagePreparationError
from .options import AssistOptions
from .state import ReplyStorageError

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

    from . import TextbeltRuntimeData
    from .state import ReplyState
    from .webhook import VerifiedReply

MAX_PENDING_PER_SENDER = 10
MAX_PENDING_TOTAL = 50
MAINTENANCE_SECONDS = 120
SAFE_REPLY = (
    "Home Assistant could not format the reply. Check Home Assistant before resending."
)
ERROR_REPLY = (
    "Home Assistant could not complete this reply. "
    "Check Home Assistant before resending; an action may have completed."
)
NEW_REPLY = "Home Assistant: new conversation started. Send your next request."
GREETING = (
    "Home Assistant: reply with a request. Send /new to start a new conversation."
)


@dataclass(slots=True)
class ConversationSession:
    """Volatile IDs and SMS activity, never transcript or persisted work."""

    conversation_id: str
    ha_session_id: str
    last_activity: float


class ConversationManager:
    """Serialize each phone while owning admission, workers and retention."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        state: ReplyState,
        runtime: TextbeltRuntimeData,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Own per-entry admission and volatile native session state."""
        self.hass, self.entry, self.state, self.runtime = hass, entry, state, runtime
        self.clock = clock
        self.active = True
        self._lock = asyncio.Lock()
        self._queues: dict[str, deque[VerifiedReply]] = {}
        self._workers: dict[str, asyncio.Task] = {}
        self._pending: dict[str, int] = {}
        self._total = 0
        self.sessions: dict[tuple[str, str, str], ConversationSession] = {}
        self._maintenance: asyncio.Task | None = None

    def options(self) -> AssistOptions | None:
        """Fail closed against current live entry options, including failed reload."""
        try:
            return AssistOptions.from_mapping(self.entry.options)
        except ValueError:
            return None

    def authorized(self, phone: str) -> bool:
        """Read live authorization without deriving it from notify recipients."""
        options = self.options()
        return bool(
            self.active
            and self.runtime.active
            and options
            and options.enabled
            and phone in options.authorized_senders
            and reply_key_usable(self.entry.data.get("api_key"))
        )

    def start(self) -> None:
        """Start maintenance outside any adapter session context."""
        self._maintenance = self.hass.async_create_background_task(
            self._maintain(), "Textbelt session maintenance"
        )

    async def async_handle_reply(  # noqa: PLR0911, PLR0912 -- explicit security admission stages.
        self, reply: VerifiedReply, *, legacy: bool = False
    ) -> int:
        """Durably admit then acknowledge; never await a native pipeline turn."""
        async with self._lock:
            if not self.active or not self.runtime.active:
                return HTTPStatus.SERVICE_UNAVAILABLE
            if reply.entry_id != self.entry.entry_id:
                return HTTPStatus.FORBIDDEN
            options = self.options()
            if options is None:
                return HTTPStatus.FORBIDDEN
            if not legacy and not self.state.correlates(reply.text_id, reply.phone):
                return HTTPStatus.FORBIDDEN
            native = not legacy and options.enabled
            if native and not self.authorized(reply.phone):
                return HTTPStatus.FORBIDDEN
            if reply.control_message:
                return HTTPStatus.OK
            if self.state.is_duplicate(reply):
                return HTTPStatus.OK
            if native:
                if (
                    self._pending.get(reply.phone, 0) >= MAX_PENDING_PER_SENDER
                    or self._total >= MAX_PENDING_TOTAL
                ):
                    return HTTPStatus.TOO_MANY_REQUESTS
                self._pending[reply.phone] = self._pending.get(reply.phone, 0) + 1
                self._total += 1
            try:
                claimed = await self.state.async_claim(reply)
            except (ReplyStorageError, ValueError):
                if native:
                    self._release(reply.phone)
                LOGGER.warning("Textbelt reply admission failed: metadata_not_durable")
                return HTTPStatus.SERVICE_UNAVAILABLE
            except asyncio.CancelledError:
                if native:
                    self._release(reply.phone)
                raise
            if not claimed:
                if native:
                    self._release(reply.phone)
                return HTTPStatus.OK
            # Options can change while disk persistence is settling.
            if (
                not self.active
                or not self.runtime.active
                or self.options() is None
                or (
                    not legacy and not self.state.correlates(reply.text_id, reply.phone)
                )
                or (native and not self.authorized(reply.phone))
            ):
                if native:
                    self._release(reply.phone)
                return HTTPStatus.OK
            self.hass.bus.async_fire(EVENT_REPLY, dict(reply.event_data))
            if native:
                self._queues.setdefault(reply.phone, deque()).append(reply)
                if reply.phone not in self._workers:
                    self._workers[reply.phone] = self.hass.async_create_background_task(
                        self._worker(reply.phone),
                        "Textbelt native turn",
                        eager_start=False,
                    )
            return HTTPStatus.OK

    def _release(self, phone: str) -> None:
        self._total -= 1
        self._pending[phone] -= 1
        if not self._pending[phone]:
            del self._pending[phone]

    async def _worker(self, phone: str) -> None:
        try:
            queue = self._queues[phone]
            while queue:
                reply = queue.popleft()
                try:
                    await self._turn(reply)
                except HomeAssistantError:
                    LOGGER.warning("Textbelt native reply failed: send_failed")
                except Exception:  # noqa: BLE001 -- isolate engine/runtime failure, no retry.
                    LOGGER.warning("Textbelt native reply failed: turn_failed")
                finally:
                    self._release(phone)
        finally:
            for _reply in self._queues.pop(phone, ()):
                self._release(phone)
            self._workers.pop(phone, None)

    async def _turn(self, reply: VerifiedReply) -> None:
        if not self.authorized(reply.phone) or not self.state.correlates(
            reply.text_id, reply.phone
        ):
            return
        options = self.options()
        if options is None:
            return
        if reply.text.strip().lower() == "/new":
            self._drop_phone(reply.phone)
            await self._respond(reply, NEW_REPLY)
            return
        try:
            pipeline = async_resolve_pipeline(self.hass, options.pipeline_id)
        except (HomeAssistantError, KeyError, ValueError):
            self._drop_phone(reply.phone)
            await self._respond(reply, ERROR_REPLY)
            return
        key = (self.entry.entry_id, reply.phone, pipeline.id)
        for old_key in list(self.sessions):
            if old_key[1] == reply.phone and old_key != key:
                del self.sessions[old_key]
        self.maintain_sessions()
        session = self.sessions.get(key)
        result = await async_run_assist(
            self.hass,
            text=reply.text,
            pipeline_id=pipeline.id,
            conversation_id=session.conversation_id if session else None,
            context=Context(),
        )
        if not self.authorized(reply.phone):
            self._drop_phone(reply.phone)
            return
        current = self.options()
        try:
            current_pipeline = (
                async_resolve_pipeline(self.hass, current.pipeline_id).id
                if current
                else None
            )
        except (HomeAssistantError, KeyError, ValueError):
            current_pipeline = None
        if current_pipeline != pipeline.id:
            self._drop_phone(reply.phone)
            return
        if result.conversation_id and result.ha_session_id:
            self.sessions[key] = ConversationSession(
                result.conversation_id, result.ha_session_id, self.clock()
            )
        response = (
            SAFE_REPLY
            if result.error_code == "empty_reply"
            else ERROR_REPLY
            if result.error_code
            else result.reply
        )
        await self._respond(reply, response)

    async def _respond(self, reply: VerifiedReply, text: str) -> None:
        if not self.authorized(reply.phone) or not self.state.correlates(
            reply.text_id, reply.phone
        ):
            return
        try:
            prepare_message(text, mode="assist", compact=True)
        except MessagePreparationError:
            text = SAFE_REPLY
        await self.runtime.async_send(
            self.hass,
            reply.phone,
            text,
            mode="assist",
            compact=True,
            webhook_url=self.runtime.reply_url(native=True),
        )

    def _drop_phone(self, phone: str) -> None:
        for key in list(self.sessions):
            if key[1] == phone:
                del self.sessions[key]

    def maintain_sessions(self) -> None:
        """Refresh actual HA sessions with public no-await context blocks."""
        options = self.options()
        try:
            pipeline = (
                async_resolve_pipeline(self.hass, options.pipeline_id).id
                if options and options.enabled
                else None
            )
        except (HomeAssistantError, KeyError, ValueError):
            pipeline = None
        for key, session in list(self.sessions.items()):
            if (
                not self.authorized(key[1])
                or pipeline != key[2]
                or options is None
                or self.clock() - session.last_activity >= options.conversation_timeout
            ):
                del self.sessions[key]
                continue
            with chat_session.async_get_chat_session(
                self.hass, session.ha_session_id
            ) as actual:
                if actual.conversation_id != session.ha_session_id:
                    del self.sessions[key]

    async def _maintain(self) -> None:
        while self.active:
            await asyncio.sleep(MAINTENANCE_SECONDS)
            self.maintain_sessions()

    async def async_policy_changed(self) -> None:
        """Cancel native work promptly on options changes even if unload fails."""
        async with self._lock:
            tasks = list(self._workers.values())
            for task in tasks:
                task.cancel()
            self.sessions.clear()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            # A task cancelled before its first instruction never enters finally.
            for phone, queue in list(self._queues.items()):
                for _reply in queue:
                    self._release(phone)
            self._queues.clear()
            self._workers.clear()

    async def async_wait_idle(self) -> None:
        """Await owned turns without waiting on maintenance."""
        while self._workers:
            await asyncio.gather(*list(self._workers.values()), return_exceptions=True)

    async def async_shutdown(self) -> None:
        """Block admission and await all owned native tasks."""
        self.active = False
        await self.async_policy_changed()
        if self._maintenance:
            self._maintenance.cancel()
            await asyncio.gather(self._maintenance, return_exceptions=True)
            self._maintenance = None
