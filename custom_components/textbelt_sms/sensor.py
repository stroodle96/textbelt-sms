"""Sensor platform for the Textbelt SMS integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from .api import TextbeltApiClient

from .api import TextbeltApiClientError
from .const import (
    ATTR_MESSAGE,
    ATTR_PHONE,
    ATTR_RESPONSE,
    ATTR_STATUS,
    ATTR_TEXT_ID,
    DEFAULT_NAME,
    DEFAULT_STATUS,
    DOMAIN,
    LOGGER,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Textbelt SMS sensor based on a config entry."""
    client = hass.data[DOMAIN][entry.entry_id]

    # Add last message status sensor
    async_add_entities([LastMessageStatusSensor(client, entry)], update_before_add=True)


class LastMessageStatusSensor(SensorEntity):
    """Sensor for tracking the last sent SMS message status."""

    _attr_has_entity_name = True
    _attr_name = DEFAULT_NAME
    _attr_native_value = DEFAULT_STATUS
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:message-text"

    def __init__(
        self,
        client: TextbeltApiClient,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        self._attr_unique_id = f"{entry.entry_id}_last_message_status"
        self._client = client
        self._last_text_id = None
        self._attr_options = ["delivered", "failed", "pending", "unknown"]
        self._attr_extra_state_attributes = {
            ATTR_TEXT_ID: None,
            ATTR_PHONE: None,
            ATTR_MESSAGE: None,
            ATTR_RESPONSE: None,
            ATTR_STATUS: DEFAULT_STATUS,
        }

        # Device info for HA UI
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name="Textbelt SMS",
            manufacturer="Textbelt",
            model="SMS Gateway",
            entry_type=DeviceEntryType.SERVICE,
        )

    async def async_update(self) -> None:
        """Update the sensor state if we have a text ID to check."""
        if not self._last_text_id:
            LOGGER.debug("No text ID available to check status")
            return

        LOGGER.debug("Checking status for text ID: %s", self._last_text_id)
        try:
            status = await self._client.async_check_status(self._last_text_id)
            if not status:
                LOGGER.warning("No status returned for text ID: %s", self._last_text_id)
                return

            self._attr_native_value = status.get("status", DEFAULT_STATUS)
            self._attr_extra_state_attributes.update(
                {
                    ATTR_STATUS: status.get("status", DEFAULT_STATUS),
                    ATTR_RESPONSE: status,
                }
            )
        except TextbeltApiClientError as err:
            LOGGER.error("Error checking SMS status: %s", err)
            self._attr_native_value = "failed"

    @callback
    def set_last_text_id(self, text_id: str | None) -> None:
        """Update the text ID and trigger an immediate state update."""
        LOGGER.debug("Setting new text ID: %s", text_id)
        self._last_text_id = text_id
        self._attr_extra_state_attributes[ATTR_TEXT_ID] = text_id
        self.async_schedule_update_ha_state(force_refresh=True)

    @callback
    def update_message_info(self, phone: str, message: str) -> None:
        """Update the message information displayed in attributes."""
        self._attr_extra_state_attributes.update(
            {
                ATTR_PHONE: phone,
                ATTR_MESSAGE: message,
            }
        )
        self.async_schedule_update_ha_state(force_refresh=True)
