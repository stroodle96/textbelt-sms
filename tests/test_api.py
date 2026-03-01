"""Tests for the Textbelt API client."""

from __future__ import annotations

import aiohttp
import pytest

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from custom_components.textbelt_sms.api import (
    TextbeltApiClient,
    TextbeltApiClientAuthenticationError,
    TextbeltApiClientCommunicationError,
    TextbeltApiClientError,
)

API_URL = "https://textbelt.com/text"
STATUS_URL = "https://textbelt.com/status/{text_id}"


@pytest.mark.asyncio
async def test_async_send_sms_success(hass, aioclient_mock) -> None:
    """A successful API response should return the payload unchanged."""
    session = async_get_clientsession(hass)
    aioclient_mock.post(
        API_URL,
        json={"success": True, "textId": "abc123"},
    )

    client = TextbeltApiClient("test-key", session)
    result = await client.async_send_sms("+1234567890", "Hello from HA")

    assert result == {"success": True, "textId": "abc123"}
    assert aioclient_mock.call_count == 1


@pytest.mark.asyncio
async def test_async_send_sms_includes_webhook(hass, aioclient_mock) -> None:
    """Passing a webhook URL should include it in the POST payload."""
    session = async_get_clientsession(hass)
    aioclient_mock.post(
        API_URL,
        json={"success": True, "textId": "abc123"},
    )

    client = TextbeltApiClient("test-key", session)
    await client.async_send_sms(
        "+1234567890",
        "Hello from HA",
        webhook_url="https://example.com/webhook",
    )

    request = aioclient_mock.requests[("post", API_URL)][0]
    assert request.kwargs["data"]["webhookUrl"] == "https://example.com/webhook"


@pytest.mark.asyncio
async def test_async_send_sms_authentication_error(hass, aioclient_mock) -> None:
    """A 401/403 response should raise an authentication error."""
    session = async_get_clientsession(hass)
    aioclient_mock.post(
        API_URL,
        status=401,
        json={"success": False, "error": "Invalid key"},
    )

    client = TextbeltApiClient("bad-key", session)
    with pytest.raises(TextbeltApiClientAuthenticationError):
        await client.async_send_sms("+1234567890", "Hello from HA")


@pytest.mark.asyncio
async def test_async_send_sms_api_error(hass, aioclient_mock) -> None:
    """An API response with success=False should raise a client error."""
    session = async_get_clientsession(hass)
    aioclient_mock.post(
        API_URL,
        json={"success": False, "error": "Quota exceeded"},
    )

    client = TextbeltApiClient("test-key", session)
    with pytest.raises(TextbeltApiClientError):
        await client.async_send_sms("+1234567890", "Hello from HA")


@pytest.mark.asyncio
async def test_async_send_sms_network_error(hass, aioclient_mock) -> None:
    """Network failures should raise a communication error."""
    session = async_get_clientsession(hass)
    aioclient_mock.post(
        API_URL,
        exc=aiohttp.ClientError("Boom"),
    )

    client = TextbeltApiClient("test-key", session)
    with pytest.raises(TextbeltApiClientCommunicationError):
        await client.async_send_sms("+1234567890", "Hello from HA")


@pytest.mark.asyncio
async def test_async_check_status_success(hass, aioclient_mock) -> None:
    """The status endpoint should return the JSON payload on success."""
    session = async_get_clientsession(hass)
    aioclient_mock.get(
        STATUS_URL.format(text_id="abc123"),
        json={"status": "delivered"},
    )

    client = TextbeltApiClient("test-key", session)
    result = await client.async_check_status("abc123")

    assert result == {"status": "delivered"}


@pytest.mark.asyncio
async def test_async_check_status_error(hass, aioclient_mock) -> None:
    """Non-200 responses from the status endpoint raise an error."""
    session = async_get_clientsession(hass)
    aioclient_mock.get(
        STATUS_URL.format(text_id="abc123"),
        status=500,
        json={"status": "error", "error": "Server error"},
    )

    client = TextbeltApiClient("test-key", session)
    with pytest.raises(TextbeltApiClientError):
        await client.async_check_status("abc123")
