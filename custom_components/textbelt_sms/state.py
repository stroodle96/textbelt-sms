# Copyright (c) 2026 Textbelt SMS contributors
"""Bounded durable reply correlation and replay admission; no transcripts."""

from __future__ import annotations

import asyncio
import math
import re
import time
from typing import TYPE_CHECKING

from homeassistant.helpers.storage import Store

from .api import normalize_text_id
from .webhook import VerifiedReply, normalize_phone

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.core import HomeAssistant

    from .sender import SendResult

OUTGOING_ID_RETENTION_SECONDS = 604800
MAX_OUTGOING_IDS_PER_SENDER = 100
MAX_OUTGOING_IDS_TOTAL = 1000
DUPLICATE_TTL_SECONDS = 120
MAX_DIGESTS = 1000
MAX_PACKET_RETENTION_SECONDS = 1800


def _number(value: object) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


class ReplyStorageError(RuntimeError):
    """Durable completion could not be confirmed; native execution is forbidden."""


class _DurableStore(Store[dict]):
    """Retain HA atomic writes but detect swallowed errors and deferred saves."""

    async def async_save(self, data: dict) -> None:
        """Require this serialized save's write to finish before returning."""
        self._write_completed = False
        await super().async_save(data)
        if not self._write_completed:
            message = "reply_metadata_not_durable"
            raise ReplyStorageError(message)

    async def _async_write_data(self, data: dict) -> None:
        await super()._async_write_data(data)
        self._write_completed = True


class ReplyState:
    """One entry's durable metadata; callers own permission and queue policy."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Create an entry-specific Home Assistant store and admission lock."""
        self.entry_id = entry_id
        self._clock = clock
        self._store = _DurableStore(hass, 1, f"textbelt_sms.reply.{entry_id}")
        self._lock = asyncio.Lock()
        self._outgoing: dict[str, tuple[str, float]] = {}
        self._duplicates: dict[str, float] = {}
        self._packets: dict[str, float] = {}

    def _prune(self) -> None:
        now = self._clock()
        outgoing = sorted(
            (
                (key, value)
                for key, value in self._outgoing.items()
                if value[1] + OUTGOING_ID_RETENTION_SECONDS > now
            ),
            key=lambda item: item[1][1],
            reverse=True,
        )
        counts: dict[str, int] = {}
        bounded = {}
        for key, value in outgoing:
            phone = value[0]
            if (
                counts.get(phone, 0) >= MAX_OUTGOING_IDS_PER_SENDER
                or len(bounded) >= MAX_OUTGOING_IDS_TOTAL
            ):
                continue
            bounded[key] = value
            counts[phone] = counts.get(phone, 0) + 1
        self._outgoing = bounded
        for name in ("_duplicates", "_packets"):
            values = getattr(self, name)
            live = sorted(
                (
                    (key, expiry)
                    for key, expiry in values.items()
                    if (expiry >= now if name == "_packets" else expiry > now)
                ),
                key=lambda item: item[1],
                reverse=True,
            )
            setattr(self, name, dict(live[:MAX_DIGESTS]))

    async def async_load(self) -> None:
        """Restore validated metadata, pruning expired and excess records."""
        async with self._lock:
            data = await self._store.async_load()
            if not isinstance(data, dict):
                return
            now = self._clock()
            outgoing = data.get("outgoing", [])
            if isinstance(outgoing, list):
                for row in outgoing:
                    if not isinstance(row, dict):
                        continue
                    try:
                        key = normalize_text_id(row.get("text_id"))
                        phone = normalize_phone(row.get("phone"))
                        sent_at = row.get("sent_at")
                        if not _number(sent_at) or sent_at > now:
                            continue
                        self._outgoing.setdefault(key, (phone, sent_at))
                    except ValueError:
                        continue
            for name, max_age in (
                ("duplicates", DUPLICATE_TTL_SECONDS),
                ("packets", MAX_PACKET_RETENTION_SECONDS),
            ):
                rows = data.get(name, [])
                if not isinstance(rows, list):
                    continue
                values = getattr(self, f"_{name}")
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    digest, expiry = row.get("digest"), row.get("expires_at")
                    if (
                        isinstance(digest, str)
                        and re.fullmatch(r"[0-9a-f]{64}", digest)
                        and _number(expiry)
                        and now <= expiry <= now + max_age
                    ):
                        values.setdefault(digest, expiry)
            self._prune()

    def record_send_result(
        self, result: SendResult, recipient: str, *, sent_at: float | None = None
    ) -> None:
        """Record every known accepted part without replacing older initiating IDs."""
        phone = normalize_phone(recipient)
        when = self._clock() if sent_at is None else sent_at
        if not _number(when):
            message = "invalid_sent_at"
            raise ValueError(message)
        for part in result.parts:
            if part.outcome == "accepted" and part.text_id is not None:
                key = normalize_text_id(part.text_id)
                self._outgoing.setdefault(key, (phone, when))
        self._prune()

    def correlates(self, text_id: object, phone: object) -> bool:
        """Require exact canonical ID and normalized recorded recipient."""
        self._prune()
        try:
            row = self._outgoing.get(normalize_text_id(text_id))
            return row is not None and row[0] == normalize_phone(phone)
        except ValueError:
            return False

    def is_duplicate(self, reply: VerifiedReply) -> bool:
        """Check packet replay and fixed two-minute body fallback without refresh."""
        self._prune()
        return reply.entry_id == self.entry_id and (
            reply.duplicate_digest in self._duplicates
            or reply.packet_digest in self._packets
        )

    def _snapshot(self) -> dict:
        return {
            "outgoing": [
                {"text_id": key, "phone": value[0], "sent_at": value[1]}
                for key, value in self._outgoing.items()
            ],
            "duplicates": [
                {"digest": key, "expires_at": value}
                for key, value in self._duplicates.items()
            ],
            "packets": [
                {"digest": key, "expires_at": value}
                for key, value in self._packets.items()
            ],
        }

    async def _async_save_snapshot(self, snapshot: dict) -> Exception | None:
        # Python 3.14 shield logs inner exceptions after outer cancellation even
        # when an owner later retrieves them. Return expected save failures as
        # values, and translate them only after the owned disk operation settles.
        try:
            await self._store.async_save(snapshot)
        except (OSError, RuntimeError, ValueError, TypeError) as error:
            return error
        return None

    async def _async_save_metadata(self) -> None:
        # Keep the owning ReplyState lock until HA's executor write settles.
        # Cancellation must never abandon a snapshot that can overtake a later
        # confirmed claim after the state and HA Store write locks release.
        write = asyncio.create_task(self._async_save_snapshot(self._snapshot()))
        cancelled: asyncio.CancelledError | None = None
        while not write.done():
            try:
                await asyncio.shield(write)
            except asyncio.CancelledError as error:
                cancelled = error
        failure = write.result()
        if cancelled is not None:
            raise cancelled
        if failure is not None:
            message = "reply_metadata_not_durable"
            raise ReplyStorageError(message) from None

    async def async_claim(self, reply: VerifiedReply) -> bool:
        """
        Persist reservation before returning True; duplicate returns False.

        Authorization, correlation, control filtering and queue reservation must
        precede this call. A save error propagates and permits no home action.
        """
        async with self._lock:
            now = self._clock()
            if reply.entry_id != self.entry_id or reply.packet_expires_at < now:
                message = "invalid_reply_admission"
                raise ValueError(message)
            if self.is_duplicate(reply):
                return False
            duplicates, packets = self._duplicates.copy(), self._packets.copy()
            self._duplicates[reply.duplicate_digest] = now + DUPLICATE_TTL_SECONDS
            self._packets[reply.packet_digest] = reply.packet_expires_at
            self._prune()
            try:
                await self._async_save_metadata()
            except BaseException:
                self._duplicates, self._packets = duplicates, packets
                raise
            return True

    async def async_flush(self) -> None:
        """Persist all accepted send metadata, including final shutdown flush."""
        async with self._lock:
            self._prune()
            await self._async_save_metadata()
