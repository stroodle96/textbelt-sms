"""Tests for the Textbelt SMS send_sms service."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms.const import DOMAIN

SERVICE = "send_sms"


async def test_send_sms_service_calls_api(
    hass,
    config_entry: MockConfigEntry,
) -> None:
    """Ensure the send_sms service calls the API client with expected payload."""
    config_entry.add_to_hass(hass)
    client = AsyncMock()
    client.async_send_sms.return_value = {"success": True}

    with patch(
        "custom_components.textbelt_sms.__init__.TextbeltApiClient",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE,
        {"phone": "+1234567890", "message": "Hello"},
        blocking=True,
    )

    client.async_send_sms.assert_awaited_once_with(
        "+1234567890",
        "Hello",
        "/api/webhook/textbelt_sms_reply",
    )


async def test_send_sms_service_aborts_on_missing_data(
    hass,
    config_entry: MockConfigEntry,
) -> None:
    """Verify the service returns early if phone or message are missing."""
    config_entry.add_to_hass(hass)
    client = AsyncMock()

    with patch(
        "custom_components.textbelt_sms.__init__.TextbeltApiClient",
        return_value=client,
    ):
        assert await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

    await hass.services.async_call(
        DOMAIN,
        SERVICE,
        {"phone": "+1234567890"},
        blocking=True,
    )

    client.async_send_sms.assert_not_called()

    await hass.services.async_call(
        DOMAIN,
        SERVICE,
        {"message": "Hello"},
        blocking=True,
    )

    client.async_send_sms.assert_not_called()
