# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Textbelt message status sensor."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)

from .api import TextbeltApiClient, TextbeltApiClientError
from .const import (
    ATTR_DELIVERY_STATUS,
    ATTR_MESSAGE,
    ATTR_PHONE,
    ATTR_TEXT_ID,
    LOGGER,
    STATUS_DELIVERED,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_UNKNOWN,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback


class MessageStatus(StrEnum):
    """Public delivery states exposed by the sensor."""

    PENDING = STATUS_PENDING
    DELIVERED = STATUS_DELIVERED
    FAILED = STATUS_FAILED
    UNKNOWN = STATUS_UNKNOWN


@dataclass(frozen=True)
class LastMessage:
    """Last message sent through this integration."""

    text_id: str
    phone: str
    message: str
    status: MessageStatus = MessageStatus.PENDING


class TextbeltStatusCoordinator(DataUpdateCoordinator[LastMessage | None]):
    """Poll Textbelt status for the last message sent by the integration."""

    def __init__(self, hass: HomeAssistant, client: TextbeltApiClient) -> None:
        """Initialize the status coordinator."""
        self.client = client
        super().__init__(
            hass,
            LOGGER,
            name="Textbelt SMS status",
            update_interval=timedelta(seconds=30),
            update_method=self._async_update_data,
            always_update=False,
        )

    async def _async_update_data(self) -> LastMessage | None:
        """Fetch status for the current message, if one exists."""
        if self.data is None:
            return None
        try:
            response = await self.client.async_get_status(self.data.text_id)
        except TextbeltApiClientError as err:
            msg = "Unable to fetch Textbelt message status"
            raise UpdateFailed(msg) from err
        raw_status = str(response.get("status", STATUS_UNKNOWN)).lower()
        try:
            status = MessageStatus(raw_status)
        except ValueError:
            status = MessageStatus.UNKNOWN
        return replace(self.data, status=status)

    def set_last_message(self, text_id: str, phone: str, message: str) -> None:
        """Publish a newly sent message as pending immediately."""
        self.async_set_updated_data(LastMessage(text_id, phone, message))


async def async_setup_entry(
    _hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the last-message status sensor."""
    async_add_entities([LastMessageStatusSensor(entry.runtime_data.coordinator, entry)])


class LastMessageStatusSensor(
    CoordinatorEntity[TextbeltStatusCoordinator], SensorEntity
):
    """Expose the last Textbelt delivery status and message details."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_icon = "mdi:message-text"
    _attr_has_entity_name = True
    _attr_name = "Last Message Status"
    _attr_options: ClassVar[list[str]] = [status.value for status in MessageStatus]
    _attr_should_poll = False

    def __init__(
        self, coordinator: TextbeltStatusCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialize the status sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_last_message_status"

    @property
    def native_value(self) -> str:
        """Return the current enum state."""
        status = (
            self.coordinator.data.status
            if self.coordinator.data
            else MessageStatus.UNKNOWN
        )
        return status.value

    @property
    def available(self) -> bool:
        """Go unavailable while a transient status refresh is failing."""
        return super().available and self.coordinator.last_update_success is not False

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Return the required last-message detail attributes."""
        message = self.coordinator.data
        status = self.native_value
        return {
            ATTR_DELIVERY_STATUS: status,
            ATTR_TEXT_ID: message.text_id if message else None,
            ATTR_PHONE: message.phone if message else None,
            ATTR_MESSAGE: message.message if message else None,
        }
