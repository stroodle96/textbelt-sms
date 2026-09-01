"""Tests for the Textbelt HTTP client."""

from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.textbelt_sms.api import (
    TextbeltApiClient,
    TextbeltApiClientAuthenticationError,
    TextbeltApiClientCommunicationError,
    TextbeltApiClientError,
)


def _response(status: int, payload: object) -> MagicMock:
    response = MagicMock(status=status)
    response.json = AsyncMock(return_value=payload)
    return response


def _session(response: MagicMock) -> MagicMock:
    request = MagicMock()
    request.__aenter__ = AsyncMock(return_value=response)
    request.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.post.return_value = request
    return session


@pytest.mark.asyncio
async def test_send_sms_posts_exact_payload_with_webhook(api_base_url: str) -> None:
    """Post the expected payload, including the optional reply webhook."""
    response = _response(200, {"success": True, "textId": "abc"})
    session = _session(response)

    result = await TextbeltApiClient("secret", session).async_send_sms(
        "+15551234567", "hello", "https://ha.test/api/webhook/textbelt_sms_reply"
    )

    assert result == {"success": True, "textId": "abc"}
    session.post.assert_called_once_with(
        f"{api_base_url}/text",
        data={
            "phone": "+15551234567",
            "message": "hello",
            "key": "secret",
            "webhookUrl": "https://ha.test/api/webhook/textbelt_sms_reply",
        },
    )


@pytest.mark.asyncio
async def test_send_sms_uses_default_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use production Textbelt when no test endpoint override is set."""
    monkeypatch.delenv("TEXTBELT_SMS_API_BASE_URL", raising=False)
    response = _response(200, {"success": True})
    session = _session(response)

    await TextbeltApiClient("secret", session).async_send_sms("+1", "hello")

    session.post.assert_called_once_with(
        "https://textbelt.com/text",
        data={"phone": "+1", "message": "hello", "key": "secret"},
    )


@pytest.mark.asyncio
async def test_send_sms_normalizes_base_url(
    api_base_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Normalize trailing slashes on a configured API endpoint."""
    monkeypatch.setenv("TEXTBELT_SMS_API_BASE_URL", f"{api_base_url}/")
    response = _response(200, {"success": True})
    session = _session(response)

    await TextbeltApiClient("secret", session).async_send_sms("+1", "hello")

    session.post.assert_called_once_with(
        f"{api_base_url}/text",
        data={"phone": "+1", "message": "hello", "key": "secret"},
    )


@pytest.mark.asyncio
async def test_send_sms_raises_authentication_error() -> None:
    """Classify unauthorized Textbelt responses as authentication failures."""
    response = _response(401, {"success": False, "error": "invalid key"})

    with pytest.raises(TextbeltApiClientAuthenticationError):
        await TextbeltApiClient("secret", _session(response)).async_send_sms(
            "+1", "hello"
        )


@pytest.mark.asyncio
async def test_send_sms_raises_api_error() -> None:
    """Propagate a provider-declared failure as a client error."""
    response = _response(200, {"success": False, "error": "no credits"})

    with pytest.raises(TextbeltApiClientError, match="no credits"):
        await TextbeltApiClient("secret", _session(response)).async_send_sms(
            "+1", "hello"
        )


@pytest.mark.asyncio
async def test_send_sms_raises_http_error() -> None:
    """Classify non-success HTTP responses as client errors."""
    response = _response(500, {"success": False})

    with pytest.raises(TextbeltApiClientError, match="HTTP 500"):
        await TextbeltApiClient("secret", _session(response)).async_send_sms(
            "+1", "hello"
        )


@pytest.mark.asyncio
async def test_send_sms_raises_communication_error() -> None:
    """Classify connection failures as communication errors."""
    session = MagicMock()
    request = MagicMock()
    request.__aenter__ = AsyncMock(side_effect=aiohttp.ClientConnectionError("offline"))
    request.__aexit__ = AsyncMock(return_value=None)
    session.post.return_value = request

    with pytest.raises(TextbeltApiClientCommunicationError, match="Network error"):
        await TextbeltApiClient("secret", session).async_send_sms("+1", "hello")


@pytest.mark.asyncio
async def test_send_sms_raises_timeout_error() -> None:
    """Classify request timeouts as communication errors."""
    session = MagicMock()
    request = MagicMock()
    request.__aenter__ = AsyncMock(side_effect=TimeoutError)
    request.__aexit__ = AsyncMock(return_value=None)
    session.post.return_value = request

    with pytest.raises(TextbeltApiClientCommunicationError, match="Network error"):
        await TextbeltApiClient("secret", session).async_send_sms("+1", "hello")


@pytest.mark.asyncio
async def test_send_sms_raises_error_for_malformed_json() -> None:
    """Reject a successful HTTP response with malformed JSON."""
    response = MagicMock(status=200)
    response.json = AsyncMock(side_effect=ValueError("not json"))

    with pytest.raises(TextbeltApiClientError, match="invalid response"):
        await TextbeltApiClient("secret", _session(response)).async_send_sms(
            "+1", "hello"
        )
# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
