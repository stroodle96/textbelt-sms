# Copyright (c) 2026 Textbelt SMS contributors
"""Verified callback security behavior, independently signed fixtures."""

import hashlib
import hmac
import json
from collections.abc import AsyncIterator
from http import HTTPStatus

import pytest
from aiohttp.test_utils import make_mocked_request
from aiohttp.web import Request
from multidict import CIMultiDict

from custom_components.textbelt_sms import webhook
from custom_components.textbelt_sms.api import normalize_text_id


class Body:
    """Controlled body transport boundary."""

    def __init__(self, body: bytes) -> None:
        """Init  ."""
        self.body = body

    async def iter_chunked(self, size: int) -> AsyncIterator[bytes]:
        """Yield bytes without a Content-Length dependency."""
        for start in range(0, len(self.body), size):
            yield self.body[start : start + size]


def request(
    body: bytes,
    timestamp: str = "1000",
    *,
    headers: list[tuple[str, str]] | None = None,
    method: str = "POST",
) -> Request:
    """Request."""
    signature = hmac.new(
        b"secret", timestamp.encode() + body, hashlib.sha256
    ).hexdigest()
    values = CIMultiDict(
        {
            "Content-Type": "application/json",
            "X-textbelt-timestamp": timestamp,
            "X-textbelt-signature": signature,
        }
    )
    if headers:
        for key, value in headers:
            values.add(key, value)
    return make_mocked_request(method, "/", headers=values, payload=Body(body))


@pytest.mark.asyncio
async def test_verified_identity_exact_text_and_control() -> None:
    """Test verified identity exact text and control."""
    reply = await webhook.async_verify_reply(
        request(
            b'{"textId":42,"fromNumber":"+1 (555) 123-4567",'
            b'"text":"  sToP ","data":"tag"}'
        ),
        api_key="secret",
        entry_id="entry",
        now=1000,
    )
    assert (reply.text_id, reply.phone, reply.text, reply.control_message) == (
        "42",
        "+15551234567",
        "  sToP ",
        "STOP",
    )
    assert reply.event_data == {
        "textId": 42,
        "fromNumber": "+1 (555) 123-4567",
        "text": "  sToP ",
        "data": "tag",
    }
    with pytest.raises((AttributeError, TypeError)):
        reply.event_data["text"] = "changed"


@pytest.mark.parametrize(
    "body",
    [
        b"[]",
        b'{"textId":"a","textId":"b","fromNumber":"+15551234567","text":"x"}',
        b'{"textId":true,"fromNumber":"+15551234567","text":"x"}',
        b'{"textId":1,"fromNumber":"5551234567","text":"x"}',
        b'{"textId":1,"fromNumber":"+15551234567","text":NaN}',
        b"\xff",
        b"[" * 1100,
    ],
)
@pytest.mark.asyncio
async def test_signed_malformed_payload_rejected(body: bytes) -> None:
    """Test signed malformed payload rejected."""
    with pytest.raises(webhook.ReplyValidationError):
        await webhook.async_verify_reply(
            request(body), api_key="secret", entry_id="entry", now=1000
        )


@pytest.mark.parametrize(
    ("timestamp", "now"),
    [("99", 1000), ("1901", 1000), ("+1000", 1000), ("\u0661\u0660\u0660\u0660", 1000)],
)
@pytest.mark.asyncio
async def test_invalid_freshness_and_timestamp(timestamp: str, now: float) -> None:
    """Test invalid freshness and timestamp."""
    with pytest.raises(webhook.ReplyValidationError):
        await webhook.async_verify_reply(
            request(b"{}", timestamp), api_key="secret", entry_id="entry", now=now
        )


@pytest.mark.asyncio
async def test_conflicting_headers_tampering_and_chunked_limit() -> None:
    """Test conflicting headers tampering and chunked limit."""
    for req in (
        request(b"{}", headers=[("X-textbelt-signature", "0" * 64)]),
        request(b"{}"),
        request(b"x" * 16385),
        request(b"{}", method="GET"),
    ):
        with pytest.raises(webhook.ReplyValidationError):
            await webhook.async_verify_reply(
                req,
                api_key="wrong" if req.content.body == b"{}" else "secret",
                entry_id="entry",
                now=1000,
            )


@pytest.mark.parametrize("value", [0, -1, 1.0, False, None, "", " " * 129, "x" * 129])
def test_ids_reject_ambiguous_values(value: object) -> None:
    """Test ids reject ambiguous values."""
    with pytest.raises(ValueError, match="numeric"):
        normalize_text_id(value)


@pytest.mark.asyncio
async def test_digest_ignores_signature_time_but_packet_does_not() -> None:
    """Test digest ignores signature time but packet does not."""
    body = json.dumps(
        {"textId": " 0042 ", "fromNumber": "+15551234567", "text": "help me"}
    ).encode()
    a = await webhook.async_verify_reply(
        request(body), api_key="secret", entry_id="entry", now=1000
    )
    b = await webhook.async_verify_reply(
        request(body, "1001"), api_key="secret", entry_id="entry", now=1001
    )
    assert a.text_id == " 0042 "
    assert a.control_message is None
    assert a.duplicate_digest == b.duplicate_digest
    assert a.packet_digest != b.packet_digest
    expected_expiry = 1900
    assert a.packet_expires_at == expected_expiry


@pytest.mark.asyncio
async def test_nonfinite_number_in_unknown_field_rejected() -> None:
    """Test nonfinite number in unknown field rejected."""
    body = b'{"textId":1,"fromNumber":"+15551234567","text":"x","unknown":1e400}'
    with pytest.raises(webhook.ReplyValidationError):
        await webhook.async_verify_reply(
            request(body), api_key="secret", entry_id="entry", now=1000
        )


@pytest.mark.parametrize(("length", "allowed"), [(4096, True), (4097, False)])
@pytest.mark.asyncio
async def test_unicode_text_limit_counts_characters(
    length: int, *, allowed: bool
) -> None:
    """Apply the text limit to Unicode codepoints rather than UTF-8 bytes."""
    body = json.dumps(
        {"textId": 1, "fromNumber": "+15551234567", "text": "é" * length},
        ensure_ascii=False,
    ).encode()
    if allowed:
        reply = await webhook.async_verify_reply(
            request(body), api_key="secret", entry_id="entry", now=1000
        )
        assert len(reply.text) == length
    else:
        with pytest.raises(webhook.ReplyValidationError, match="payload"):
            await webhook.async_verify_reply(
                request(body), api_key="secret", entry_id="entry", now=1000
            )


@pytest.mark.asyncio
async def test_uppercase_signature_and_original_timestamp_spelling() -> None:
    """Verify original timestamp bytes and either-case hexadecimal signature."""
    req = request(b'{"textId":"x","fromNumber":"+15551234567","text":"x"}', "0001000")
    headers = CIMultiDict(req.headers)
    headers["X-textbelt-signature"] = headers["X-textbelt-signature"].upper()
    req = make_mocked_request("POST", "/", headers=headers, payload=req.content)
    reply = await webhook.async_verify_reply(
        req, api_key="secret", entry_id="entry", now=1000
    )
    assert reply.text_id == "x"


@pytest.mark.asyncio
async def test_exact_raw_body_tampering_rejected() -> None:
    """Catch implementations that sign a decoded or reserialized payload."""
    req = request(b'{"textId":"x","fromNumber":"+15551234567","text":"x"}')
    req.content.body += b" "
    with pytest.raises(webhook.ReplyValidationError, match="signature"):
        await webhook.async_verify_reply(
            req, api_key="secret", entry_id="entry", now=1000
        )


@pytest.mark.parametrize("header", ["X-textbelt-signature", "X-textbelt-timestamp"])
@pytest.mark.asyncio
async def test_duplicate_security_header_even_identical_rejected(header: str) -> None:
    """Catch first-header-only verification independently of signature failure."""
    body = b'{"textId":"x","fromNumber":"+15551234567","text":"x"}'
    original = request(body)
    duplicate = request(body, headers=[(header, original.headers[header])])
    with pytest.raises(webhook.ReplyValidationError, match="headers") as error:
        await webhook.async_verify_reply(
            duplicate, api_key="secret", entry_id="entry", now=1000
        )
    assert error.value.status == HTTPStatus.UNAUTHORIZED


@pytest.mark.asyncio
async def test_signed_non_json_content_type_rejected() -> None:
    """Do not accept correctly signed callbacks with another media type."""
    original = request(b'{"textId":"x","fromNumber":"+15551234567","text":"x"}')
    headers = CIMultiDict(original.headers)
    headers["Content-Type"] = "text/plain"
    req = make_mocked_request("POST", "/", headers=headers, payload=original.content)
    with pytest.raises(webhook.ReplyValidationError, match="content_type"):
        await webhook.async_verify_reply(
            req, api_key="secret", entry_id="entry", now=1000
        )


@pytest.mark.parametrize(
    ("command", "expected"),
    [("stop", "STOP"), (" START ", "START"), ("\nHelp\t", "HELP")],
)
@pytest.mark.asyncio
async def test_exact_control_commands_identified(command: str, expected: str) -> None:
    """Exclude exact controls from the native-processing candidate contract."""
    body = json.dumps(
        {"textId": 1, "fromNumber": "+15551234567", "text": command}
    ).encode()
    reply = await webhook.async_verify_reply(
        request(body), api_key="secret", entry_id="entry", now=1000
    )
    assert reply.control_message == expected
