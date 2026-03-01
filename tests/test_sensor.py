"""Tests for the Textbelt status sensor."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms.api import TextbeltApiClientError
from custom_components.textbelt_sms.const import (
    ATTR_MESSAGE,
    ATTR_PHONE,
    ATTR_STATUS,
    ATTR_TEXT_ID,
    DEFAULT_STATUS,
)
from custom_components.textbelt_sms.sensor import LastMessageStatusSensor


def _create_sensor(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> tuple[LastMessageStatusSensor, AsyncMock]:
    """Build a sensor together with a mocked API client."""
    client = AsyncMock()
    sensor = LastMessageStatusSensor(client, mock_config_entry)
    sensor.hass = hass
    return sensor, client


def test_sensor_starts_with_defaults(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """The sensor should expose known defaults when created."""
    sensor, _ = _create_sensor(hass, mock_config_entry)

    assert sensor.native_value == DEFAULT_STATUS
    assert sensor.extra_state_attributes[ATTR_STATUS] == DEFAULT_STATUS
    assert sensor.extra_state_attributes[ATTR_TEXT_ID] is None


@pytest.mark.asyncio
async def test_sensor_updates_status(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Updating the sensor should call the API and store the status."""
    sensor, client = _create_sensor(hass, mock_config_entry)
    client.async_check_status.return_value = {"status": "delivered"}

    sensor.set_last_text_id("abc123")
    await sensor.async_update()

    assert sensor.native_value == "delivered"
    assert sensor.extra_state_attributes[ATTR_STATUS] == "delivered"


@pytest.mark.asyncio
async def test_sensor_handles_api_error(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """If the API raises an error the sensor should fall back to failed."""
    sensor, client = _create_sensor(hass, mock_config_entry)
    sensor.set_last_text_id("abc123")
    client.async_check_status.side_effect = TextbeltApiClientError("Boom")

    await sensor.async_update()

    assert sensor.native_value == "failed"


def test_update_message_info_stores_attributes(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Message metadata should be persisted on the sensor."""
    sensor, _ = _create_sensor(hass, mock_config_entry)

    sensor.update_message_info("+1234567890", "hello world")

    assert sensor.extra_state_attributes[ATTR_PHONE] == "+1234567890"
    assert sensor.extra_state_attributes[ATTR_MESSAGE] == "hello world"
