# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Serialized provider-compatible batches with explicit submission outcomes."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

from .api import (
    TextbeltApiClient,
    TextbeltApiClientError,
    TextbeltApiClientUnknownOutcomeError,
    normalize_text_id,
)
from .message import prepare_message
from .models import DEFAULT_POLICY, MessagePreparationError, ProviderPolicy

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass(frozen=True)
class PartResult:
    """One attempted part; acceptance is distinct from delivery."""

    index: int
    text_id: str | None
    outcome: str
    error_code: str | None = None


@dataclass(frozen=True)
class SendResult:
    """Submission result retaining every known provider identifier."""

    parts: tuple[PartResult, ...]
    total_parts: int
    outcome: str
    error_code: str | None = None
    shortened: bool = False

    @property
    def text_ids(self) -> tuple[str, ...]:
        """Return identifiers from accepted parts in submission order."""
        return tuple(part.text_id for part in self.parts if part.text_id is not None)

    @property
    def accepted_parts(self) -> int:
        """Count known accepted parts, including a partial batch."""
        return len(self.text_ids)


def _accepted_text_id(response: object) -> str:
    """Validate mocked as well as real client acceptance responses."""
    if not isinstance(response, dict) or response.get("success") is not True:
        if isinstance(response, dict) and response.get("success") is False:
            msg = "Provider rejected SMS"
            raise TextbeltApiClientError(msg)
        msg = "Malformed send response"
        raise TextbeltApiClientUnknownOutcomeError(msg)
    try:
        return normalize_text_id(response.get("textId"))
    except ValueError:
        msg = "Missing text ID"
        raise TextbeltApiClientUnknownOutcomeError(msg) from None


class TextbeltSender:
    """Prepare all parts before the first POST and serialize whole batches."""

    def __init__(
        self,
        client: TextbeltApiClient,
        *,
        policy: ProviderPolicy = DEFAULT_POLICY,
        on_result: Callable[[SendResult, str, str], None] | None = None,
    ) -> None:
        """Own one integration-wide send queue and its lifecycle."""
        self.client = client
        self.policy = policy
        self.lock = asyncio.Lock()
        self.active = True
        self.last_result: SendResult | None = None
        self._on_result = on_result

    def shutdown(self) -> None:
        """Prevent queued sends and subsequent parts after unload."""
        self.active = False

    def _publish(self, result: SendResult, phone: str, message: str) -> SendResult:
        self.last_result = result
        if self._on_result is not None:
            self._on_result(result, phone, message)
        return result

    def _validate_parts(self, parts: tuple[str, ...]) -> None:
        """Defensively validate final copy before contacting the provider."""
        if not parts or len(parts) > self.policy.max_parts:
            code, msg = "message_too_long", "Invalid SMS part count"
            raise MessagePreparationError(code, msg)
        for part in parts:
            if not part or any(c not in self.policy.allowed_characters for c in part):
                code, msg = "unsupported_character", "Invalid SMS part"
                raise MessagePreparationError(code, msg)
            units = sum(2 if c in self.policy.extension_characters else 1 for c in part)
            if units > self.policy.max_part_septets:
                code, msg = "message_too_long", "SMS part exceeds budget"
                raise MessagePreparationError(code, msg)

    async def async_send(  # noqa: PLR0913
        self,
        phone: str,
        message: str,
        *,
        title: str | None = None,
        mode: Literal["automation", "assist"] = "automation",
        compact: bool = False,
        webhook_url: str | None = None,
    ) -> SendResult:
        """Send once per part, stopping on rejection or uncertain acceptance."""
        async with self.lock:
            if not self.active:
                return self._publish(
                    SendResult((), 0, "rejected", "inactive"), phone, message
                )
            try:
                prepared = prepare_message(
                    message, title=title, mode=mode, compact=compact, policy=self.policy
                )
                self._validate_parts(prepared.parts)
            except MessagePreparationError as err:
                self._publish(SendResult((), 0, "rejected", err.code), phone, message)
                raise
            attempted: list[PartResult] = []
            outcome = "accepted"
            error_code = None
            for index, part in enumerate(prepared.parts, 1):
                if not self.active:
                    outcome = "partial" if attempted else "rejected"
                    error_code = "inactive"
                    break
                try:
                    response = await self.client.async_send_sms(
                        phone, part, webhook_url
                    )
                    text_id = _accepted_text_id(response)
                except asyncio.CancelledError:
                    attempted.append(PartResult(index, None, "unknown", "cancelled"))
                    self._publish(
                        SendResult(
                            tuple(attempted),
                            len(prepared.parts),
                            "unknown",
                            "cancelled",
                            prepared.shortened,
                        ),
                        phone,
                        prepared.normalized_text,
                    )
                    raise
                except TextbeltApiClientUnknownOutcomeError:
                    attempted.append(
                        PartResult(index, None, "unknown", "unknown_outcome")
                    )
                    outcome, error_code = "unknown", "unknown_outcome"
                    break
                except TextbeltApiClientError:
                    attempted.append(
                        PartResult(index, None, "rejected", "provider_rejected")
                    )
                    outcome = (
                        "partial" if any(p.text_id for p in attempted) else "rejected"
                    )
                    error_code = "provider_rejected"
                    break
                attempted.append(PartResult(index, text_id, "accepted"))
            return self._publish(
                SendResult(
                    tuple(attempted),
                    len(prepared.parts),
                    outcome,
                    error_code,
                    prepared.shortened,
                ),
                phone,
                prepared.normalized_text,
            )
