# Copyright (c) 2026 Textbelt SMS contributors
"""Fail-closed verification of Textbelt signed reply packets."""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import re
import time
from dataclasses import InitVar, dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from aiohttp.web import Request

from .api import normalize_text_id
from .recipients import normalize_recipients

MAX_TIMESTAMP_SECONDS = 900
MAX_SIGNIFICANT_TIMESTAMP_DIGITS = 20
_VERIFIED = object()
MAX_BODY_BYTES = 16384
MAX_INBOUND_TEXT_CHARS = 4096


class ReplyValidationError(ValueError):
    """Safe public error, without callback or credential material."""

    def __init__(self, code: str, status: int = 400) -> None:
        """Expose only a safe code and deliberate HTTP status."""
        super().__init__(code)
        self.code = code
        self.status = status


@dataclass(frozen=True, slots=True)
class VerifiedReply:
    """Authenticated metadata; construct through async_verify_reply only."""

    entry_id: str
    text_id: str
    phone: str
    text: str
    duplicate_digest: str
    packet_digest: str
    packet_expires_at: float
    event_data: Mapping[str, Any]
    _token: InitVar[object] = None

    def __post_init__(self, _token: object) -> None:
        """Prevent callers from constructing an unverified reply."""
        if _token is not _VERIFIED:
            message = "unverified_reply"
            raise ValueError(message)

    @property
    def control_message(self) -> str | None:
        """Identify exact provider control words without substring matching."""
        value = self.text.strip().upper()
        return value if value in {"STOP", "START", "HELP"} else None


def normalize_phone(value: object) -> str:
    """Require exactly one explicit international recipient."""
    if not isinstance(value, str) or "\n" in value or "\r" in value:
        message = "invalid_phone"
        raise ValueError(message)
    phones = normalize_recipients(value)
    if len(phones) != 1:
        message = "invalid_phone"
        raise ValueError(message)
    return phones[0]


def _digest(*values: bytes) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(len(value).to_bytes(8, "big"))
        digest.update(value)
    return digest.hexdigest()


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            message = "duplicate_key"
            raise ValueError(message)
        result[key] = value
    return result


def _reject_constant(_value: str) -> None:
    message = "nonfinite_json"
    raise ValueError(message)


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        message = "nonfinite_json"
        raise ValueError(message)
    return parsed


def _validate_payload(data: object) -> tuple[str, str, str]:
    if not isinstance(data, dict):
        code = "payload"
        raise ReplyValidationError(code)
    text_id = normalize_text_id(data.get("textId"))
    phone = normalize_phone(data.get("fromNumber"))
    text = data.get("text")
    if not isinstance(text, str) or len(text) > MAX_INBOUND_TEXT_CHARS:
        code = "payload"
        raise ReplyValidationError(code)
    if "data" in data and not isinstance(data["data"], str):
        code = "payload"
        raise ReplyValidationError(code)
    return text_id, phone, text


async def async_verify_reply(
    request: Request, *, api_key: str, entry_id: str, now: float | None = None
) -> VerifiedReply:
    """Verify exact signed bytes before decoding or exposing callback fields."""
    if request.method != "POST":
        code = "method"
        raise ReplyValidationError(code, 405)
    if request.content_type != "application/json":
        code = "content_type"
        raise ReplyValidationError(code, 415)
    timestamps = request.headers.getall("X-textbelt-timestamp", [])
    signatures = request.headers.getall("X-textbelt-signature", [])
    if len(timestamps) != 1 or len(signatures) != 1:
        code = "headers"
        raise ReplyValidationError(code, 401)
    timestamp, signature = timestamps[0], signatures[0]
    if not re.fullmatch(r"[0-9]+", timestamp) or not re.fullmatch(
        r"[0-9a-fA-F]{64}", signature
    ):
        code = "headers"
        raise ReplyValidationError(code, 401)
    current = time.time() if now is None else now
    significant = timestamp.lstrip("0") or "0"
    if len(significant) > MAX_SIGNIFICANT_TIMESTAMP_DIGITS:
        code = "timestamp"
        raise ReplyValidationError(code, 401)
    signed_at = int(significant)
    if abs(current - signed_at) > MAX_TIMESTAMP_SECONDS:
        code = "timestamp"
        raise ReplyValidationError(code, 401)
    body = bytearray()
    async for chunk in request.content.iter_chunked(4096):
        if len(body) + len(chunk) > MAX_BODY_BYTES:
            code = "body_too_large"
            raise ReplyValidationError(code, 413)
        body.extend(chunk)
    raw = bytes(body)
    expected = hmac.digest(
        api_key.encode("utf-8"), timestamp.encode("utf-8") + raw, "sha256"
    )
    if not hmac.compare_digest(expected, bytes.fromhex(signature)):
        code = "signature"
        raise ReplyValidationError(code, 401)
    try:
        data = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_object,
            parse_constant=_reject_constant,
            parse_float=_finite_float,
        )
        text_id, phone, text = _validate_payload(data)
        # Unknown fields are never copied into downstream events.
        event = {
            key: data[key]
            for key in ("textId", "fromNumber", "text", "data")
            if key in data
        }
        identity = entry_id.encode("utf-8")
        duplicate = _digest(
            identity, text_id.encode("utf-8"), phone.encode("utf-8"), raw
        )
    except ReplyValidationError:
        raise
    except (ValueError, TypeError, RecursionError, UnicodeError):
        code = "payload"
        raise ReplyValidationError(code) from None
    return VerifiedReply(
        entry_id,
        text_id,
        phone,
        text,
        duplicate,
        _digest(identity, timestamp.encode("utf-8"), raw),
        signed_at + MAX_TIMESTAMP_SECONDS,
        MappingProxyType(event),
        _VERIFIED,
    )
