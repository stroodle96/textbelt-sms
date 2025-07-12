"""Sensor platform for Textbelt SMS delivery status."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.sensor import SensorEntity
from homeassistant.const import EntityCategory

from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from collections.abc import Callable

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from .api import TextbeltApiClient  # isort: skip


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: Callable,
) -> None:
    """Set up the Last Message Status sensor."""
    client = hass.data[DOMAIN][config_entry.entry_id]
    sensor = LastMessageStatusSensor(client)
    async_add_entities([sensor])
    # Store reference to sensor for service handler integration
    hass.data[DOMAIN].setdefault("entities", []).append(sensor)


class LastMessageStatusSensor(SensorEntity):
    """Sensor to show the status of the last sent SMS message."""

    _attr_name = "Last Message Status"
    _attr_icon = "mdi:message-text"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, client: TextbeltApiClient) -> None:
        """Initialize the Last Message Status sensor."""
        self._client = client
        self._text_id: str | None = None
        self._status: str | None = None
        self._attr_extra_state_attributes = {}
        self._attr_unique_id = f"{DOMAIN}_last_message_status"

    @property
    def state(self) -> str:
        """Return the sensor state: textId and status."""
        if self._text_id and self._status:
            return f"{self._text_id}: {self._status}"
        return "No message sent"

    async def async_update(self) -> None:
        """Update the sensor with the latest message status."""
        if not self._text_id:
            return
        try:
            data = await self._client.async_get_sms_status(self._text_id)
            self._status = data.get("status", "unknown")
            self._attr_extra_state_attributes = data
        except (KeyError, AttributeError) as err:
            LOGGER.error("Failed to update SMS status: %s", err)
            self._status = "error"

    def set_last_text_id(self, text_id: str) -> None:
        """Set the last sent textId and trigger update."""
        self._text_id = text_id
        self.schedule_update_ha_state()
