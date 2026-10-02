# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Tests for the Textbelt HTTP client."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from custom_components.textbelt_sms.api import (
    TextbeltApiClient,
    TextbeltApiClientAuthenticationError,
    TextbeltApiClientCommunicationError,
    TextbeltApiClientError,
    TextbeltApiClientUnknownOutcomeError,
    normalize_text_id,
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


def _get_session(response: MagicMock) -> MagicMock:
    request = MagicMock()
    request.__aenter__ = AsyncMock(return_value=response)
    request.__aexit__ = AsyncMock(return_value=None)
    session = MagicMock()
    session.get.return_value = request
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
        timeout=aiohttp.ClientTimeout(total=20),
        allow_redirects=False,
        data={
            "phone": "+15551234567",
            "message": "hello",
            "key": "secret",
            "replyWebhookUrl": "https://ha.test/api/webhook/textbelt_sms_reply",
        },
    )


@pytest.mark.asyncio
async def test_send_sms_uses_default_base_url(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use production Textbelt when no test endpoint override is set."""
    monkeypatch.delenv("TEXTBELT_SMS_API_BASE_URL", raising=False)
    response = _response(200, {"success": True, "textId": "abc"})
    session = _session(response)

    await TextbeltApiClient("secret", session).async_send_sms("+1", "hello")

    session.post.assert_called_once_with(
        "https://textbelt.com/text",
        timeout=aiohttp.ClientTimeout(total=20),
        allow_redirects=False,
        data={"phone": "+1", "message": "hello", "key": "secret"},
    )


@pytest.mark.asyncio
async def test_send_sms_normalizes_base_url(
    api_base_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Normalize trailing slashes on a configured API endpoint."""
    monkeypatch.setenv("TEXTBELT_SMS_API_BASE_URL", f"{api_base_url}/")
    response = _response(200, {"success": True, "textId": "abc"})
    session = _session(response)

    await TextbeltApiClient("secret", session).async_send_sms("+1", "hello")

    session.post.assert_called_once_with(
        f"{api_base_url}/text",
        timeout=aiohttp.ClientTimeout(total=20),
        allow_redirects=False,
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

    with pytest.raises(TextbeltApiClientError, match="rejected"):
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


@pytest.mark.asyncio
async def test_get_status_uses_exact_path_without_key_or_query(
    api_base_url: str,
) -> None:
    """Fetch one message status from the path without query parameters."""
    response = _response(200, {"status": "DELIVERED"})
    session = _get_session(response)

    result = await TextbeltApiClient("secret", session).async_get_status("abc")

    assert result == {"status": "DELIVERED"}
    session.get.assert_called_once_with(
        f"{api_base_url}/status/abc",
        timeout=aiohttp.ClientTimeout(total=10),
        allow_redirects=False,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(("text_id", "path"), [(123, "123"), ("a b", "a%20b")])
async def test_get_status_normalizes_valid_text_id(
    api_base_url: str, text_id: int | str, path: str
) -> None:
    """Accept numeric or non-empty string IDs and normalize them in the path."""
    session = _get_session(_response(200, {"status": "PENDING"}))
    await TextbeltApiClient("secret", session).async_get_status(text_id)
    session.get.assert_called_once_with(
        f"{api_base_url}/status/{path}",
        timeout=aiohttp.ClientTimeout(total=10),
        allow_redirects=False,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("text_id", [None, "", True, False])
async def test_get_status_rejects_invalid_text_id(text_id: object) -> None:
    """Reject null, empty, and boolean IDs before making an HTTP request."""
    session = _get_session(_response(200, {}))
    with pytest.raises(ValueError, match="numeric"):
        await TextbeltApiClient("secret", session).async_get_status(text_id)


@pytest.mark.asyncio
@pytest.mark.parametrize("http_status", [401, 403])
async def test_get_status_raises_for_authentication_error(http_status: int) -> None:
    """Classify status authentication failures as client errors."""
    response = _response(http_status, {"status": "FAILED"})
    with pytest.raises(TextbeltApiClientAuthenticationError):
        await TextbeltApiClient("secret", _get_session(response)).async_get_status(
            "abc"
        )


@pytest.mark.asyncio
async def test_get_status_raises_for_http_error() -> None:
    """Classify non-authentication status HTTP failures as client errors."""
    response = _response(500, {"status": "FAILED"})
    with pytest.raises(TextbeltApiClientError, match="HTTP 500"):
        await TextbeltApiClient("secret", _get_session(response)).async_get_status(
            "abc"
        )


@pytest.mark.asyncio
async def test_get_status_raises_for_malformed_json() -> None:
    """Reject a successful status response with malformed JSON."""
    malformed_response = MagicMock(status=200)
    malformed_response.json = AsyncMock(side_effect=ValueError("not json"))
    with pytest.raises(TextbeltApiClientError, match="invalid response"):
        await TextbeltApiClient(
            "secret", _get_session(malformed_response)
        ).async_get_status("abc")


@pytest.mark.asyncio
async def test_get_status_raises_for_non_dict_json() -> None:
    """Reject a successful status response whose JSON is not an object."""
    response = _response(200, ["DELIVERED"])
    with pytest.raises(TextbeltApiClientError, match="invalid response"):
        await TextbeltApiClient("secret", _get_session(response)).async_get_status(
            "abc"
        )


@pytest.mark.asyncio
async def test_get_status_raises_for_connection_error() -> None:
    """Classify status connection failures as communication errors."""
    session = MagicMock()
    request = MagicMock()
    request.__aenter__ = AsyncMock(side_effect=aiohttp.ClientConnectionError("offline"))
    request.__aexit__ = AsyncMock(return_value=None)
    session.get.return_value = request

    with pytest.raises(TextbeltApiClientCommunicationError, match="Network error"):
        await TextbeltApiClient("secret", session).async_get_status("abc")


@pytest.mark.asyncio
async def test_get_status_raises_for_timeout() -> None:
    """Classify status timeouts as communication errors."""
    session = MagicMock()
    request = MagicMock()
    request.__aenter__ = AsyncMock(side_effect=TimeoutError)
    request.__aexit__ = AsyncMock(return_value=None)
    session.get.return_value = request

    with pytest.raises(TextbeltApiClientCommunicationError, match="Network error"):
        await TextbeltApiClient("secret", session).async_get_status("abc")


@pytest.mark.parametrize("quota", [0, 98])
async def test_get_quota_returns_balance_for_configured_key(
    api_base_url: str, quota: int
) -> None:
    """Fetch numeric credit balance without sending an SMS."""
    session = _get_session(_response(200, {"success": True, "quotaRemaining": quota}))
    result = await TextbeltApiClient("secret/with ?#", session).async_get_quota()
    assert result == quota
    assert type(result) is int
    assert session.get.call_args.args == (
        f"{api_base_url}/quota/secret%2Fwith%20%3F%23",
    )
    session.post.assert_not_called()


@pytest.mark.parametrize(
    "payload",
    [
        {"success": False, "quotaRemaining": 98, "error": "secret"},
        {"success": True},
        {"quotaRemaining": 98},
        {"success": True, "quotaRemaining": -1},
        {"success": True, "quotaRemaining": True},
        {"success": True, "quotaRemaining": "98"},
        {"success": True, "quotaRemaining": 1.5},
        {"success": True, "quotaRemaining": None},
        [],
    ],
)
async def test_get_quota_rejects_invalid_balances(payload: object) -> None:
    """Provider errors and malformed balances must not become sensor readings."""
    with pytest.raises(TextbeltApiClientError) as caught:
        await TextbeltApiClient(
            "secret", _get_session(_response(200, payload))
        ).async_get_quota()
    assert "secret" not in str(caught.value)


@pytest.mark.parametrize("status", [301, 401, 403, 429, 500])
async def test_get_quota_handles_http_failures(status: int) -> None:
    """HTTP failures become safe client exceptions, without following redirects."""
    session = _get_session(_response(status, {}))
    expected = (
        TextbeltApiClientAuthenticationError
        if status in {401, 403}
        else TextbeltApiClientError
    )
    with pytest.raises(expected):
        await TextbeltApiClient("secret", session).async_get_quota()
    assert session.get.call_args.kwargs["allow_redirects"] is False
    assert session.get.call_args.kwargs["timeout"] == aiohttp.ClientTimeout(total=10)


@pytest.mark.parametrize(
    "error",
    [
        aiohttp.ClientConnectionError("https://textbelt.com/quota/secret"),
        TimeoutError(),
    ],
)
async def test_get_quota_network_errors_do_not_expose_key(error: Exception) -> None:
    """Network failures must not put the key-bearing URL in error messages."""
    session = _get_session(_response(200, {}))
    session.get.return_value.__aenter__.side_effect = error
    with pytest.raises(TextbeltApiClientCommunicationError) as caught:
        await TextbeltApiClient("secret", session).async_get_quota()
    assert "secret" not in str(caught.value)
    assert caught.value.__suppress_context__


async def test_get_quota_rejects_invalid_json() -> None:
    """Invalid JSON cannot become a balance or reveal the request URL."""
    response = _response(200, {})
    response.json.side_effect = ValueError("secret")
    with pytest.raises(TextbeltApiClientError, match="invalid response") as caught:
        await TextbeltApiClient("secret", _get_session(response)).async_get_quota()
    assert caught.value.__suppress_context__


@pytest.mark.parametrize(
    "payload",
    [
        {"success": 1, "textId": "abc"},
        {"success": "true", "textId": "abc"},
        {"success": True},
        {"success": True, "textId": None},
        {"success": True, "textId": True},
        {"success": True, "textId": " "},
        {},
        [],
    ],
)
async def test_send_unknown_schema(payload: object) -> None:
    """Malformed acceptance cannot establish a known send outcome."""
    with pytest.raises(TextbeltApiClientCommunicationError) as caught:
        await TextbeltApiClient(
            "secret", _session(_response(200, payload))
        ).async_send_sms("(555) 123-4567", "hello")
    assert isinstance(caught.value, TextbeltApiClientUnknownOutcomeError)


@pytest.mark.parametrize("status", [301, 302, 307, 308, 500, 503])
async def test_send_uncertain_http(status: int) -> None:
    """Redirects and server errors never establish rejection or acceptance."""
    session = _session(_response(status, {"success": True, "textId": "abc"}))
    with pytest.raises(TextbeltApiClientCommunicationError) as caught:
        await TextbeltApiClient("secret", session).async_send_sms("+1", "hello")
    assert isinstance(caught.value, TextbeltApiClientUnknownOutcomeError)
    assert session.post.call_count == 1
    assert session.post.call_args.kwargs["allow_redirects"] is False


@pytest.mark.parametrize(
    "error",
    [
        TimeoutError("secret https://private"),
        aiohttp.ClientConnectionError("secret https://private"),
        ValueError("secret https://private"),
    ],
)
async def test_send_safe_unknown_errors(error: Exception) -> None:
    """Transport and parsing errors suppress raw provider data and never retry."""
    response = _response(200, {})
    response.json.side_effect = error
    session = _session(response)
    with pytest.raises(TextbeltApiClientCommunicationError) as caught:
        await TextbeltApiClient("secret", session).async_send_sms("+1", "hello")
    assert isinstance(caught.value, TextbeltApiClientUnknownOutcomeError)
    assert "secret" not in str(caught.value)
    assert "https" not in str(caught.value)
    assert caught.value.__suppress_context__
    assert session.post.call_count == 1


async def test_send_normalized_id_and_actual_newline() -> None:
    """Keep legacy phone and actual LF intact in the form payload."""
    session = _session(_response(200, {"success": True, "textId": 123}))
    result = await TextbeltApiClient("secret", session).async_send_sms(
        "(555) 123-4567", "a\nb&c+d"
    )
    assert result["textId"] == "123"
    assert session.post.call_args.kwargs["data"]["message"] == "a\nb&c+d"
    assert session.post.call_args.kwargs["data"]["phone"] == "(555) 123-4567"


async def test_send_rejection_sanitized() -> None:
    """A declared rejection is known and provider error strings stay private."""
    session = _session(
        _response(200, {"success": False, "error": "secret https://private"})
    )
    with pytest.raises(TextbeltApiClientError) as caught:
        await TextbeltApiClient("secret", session).async_send_sms("+1", "hello")
    assert type(caught.value) is TextbeltApiClientError
    assert "secret" not in str(caught.value)


async def test_send_cancellation_propagates() -> None:
    """Cancellation stays available to the sender's bookkeeping."""
    session = _session(_response(200, {}))
    session.post.return_value.__aenter__.side_effect = asyncio.CancelledError
    with pytest.raises(asyncio.CancelledError):
        await TextbeltApiClient("secret", session).async_send_sms("+1", "hello")


async def test_status_redirect_rejected() -> None:
    """Status reads must not follow redirects or accept their bodies."""
    session = _get_session(_response(302, {"status": "DELIVERED"}))
    with pytest.raises(TextbeltApiClientError):
        await TextbeltApiClient("secret", session).async_get_status("abc")


async def test_status_error_sanitized() -> None:
    """A failed status request must not reveal underlying URLs."""
    session = _get_session(_response(200, {}))
    session.get.return_value.__aenter__.side_effect = aiohttp.ClientConnectionError(
        "secret https://private"
    )
    with pytest.raises(TextbeltApiClientCommunicationError) as caught:
        await TextbeltApiClient("secret", session).async_get_status("abc")
    assert "secret" not in str(caught.value)
    assert caught.value.__suppress_context__


@pytest.mark.parametrize("text_id", [0, -1, 1.5, "x" * 129])
async def test_get_status_rejects_noncanonical_ids(text_id: object) -> None:
    """Reject IDs that cannot be safely correlated with verified replies."""
    with pytest.raises(ValueError, match="numeric"):
        await TextbeltApiClient(
            "secret", _get_session(_response(200, {}))
        ).async_get_status(text_id)


@pytest.mark.parametrize("text_id", [" 0042 ", "a b"])
def test_text_id_strings_preserve_identity(text_id: str) -> None:
    """Never rewrite string IDs or invent a provider ID grammar."""
    assert normalize_text_id(text_id) == text_id
