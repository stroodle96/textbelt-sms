# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Tests for the Textbelt message status coordinator and sensor."""

from unittest.mock import AsyncMock

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms.api import TextbeltApiClientCommunicationError
from custom_components.textbelt_sms.const import DOMAIN
from custom_components.textbelt_sms.sensor import (
    LastMessage,
    LastMessageStatusSensor,
    MessageStatus,
    TextbeltStatusCoordinator,
)


class FakeClient:
    """Small status client double for coordinator tests."""

    def __init__(self, response: dict | Exception) -> None:
        """Initialize the fake status client."""
        self.response = response
        self.async_get_status = AsyncMock(side_effect=self._get_status)

    async def _get_status(self, _text_id: str) -> dict:
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def _entry() -> MockConfigEntry:
    return MockConfigEntry(domain=DOMAIN, title="Textbelt SMS", data={})


async def test_coordinator_exposes_pending_and_delivered(hass: HomeAssistant) -> None:
    """A sent message is pending until one status refresh reports delivered."""
    client = FakeClient({"success": True, "status": "DELIVERED"})
    coordinator = TextbeltStatusCoordinator(hass, client)
    coordinator.set_last_message("abc", "+15551234567", "hello")

    assert coordinator.data == LastMessage(
        text_id="abc",
        phone="+15551234567",
        message="hello",
        status=MessageStatus.PENDING,
    )

    await coordinator.async_refresh()

    assert coordinator.data.status is MessageStatus.DELIVERED
    await coordinator.async_shutdown()


async def test_coordinator_maps_failed_and_unknown(hass: HomeAssistant) -> None:
    """Provider status values map to the public enum, including unknown values."""
    client = FakeClient({"success": True, "status": "FAILED"})
    coordinator = TextbeltStatusCoordinator(hass, client)
    coordinator.set_last_message("abc", "+1", "hello")
    await coordinator.async_refresh()
    assert coordinator.data.status is MessageStatus.FAILED

    client.response = {"success": True, "status": "IN_TRANSIT"}
    await coordinator.async_refresh()
    assert coordinator.data.status is MessageStatus.UNKNOWN
    await coordinator.async_shutdown()


async def test_coordinator_status_error_is_unavailable(hass: HomeAssistant) -> None:
    """Transient status failures are update failures, not delivery failures."""
    client = FakeClient(TextbeltApiClientCommunicationError("offline"))
    coordinator = TextbeltStatusCoordinator(hass, client)
    coordinator.set_last_message("abc", "+1", "hello")

    await coordinator.async_refresh()

    assert isinstance(coordinator.last_update_success, bool)
    assert coordinator.last_update_success is False
    assert isinstance(coordinator.last_exception, UpdateFailed)
    assert coordinator.data.status is MessageStatus.PENDING
    sensor = LastMessageStatusSensor(coordinator, _entry())
    assert sensor.available is False
    await coordinator.async_shutdown()


async def test_sensor_exposes_required_detail_attributes(hass: HomeAssistant) -> None:
    """The enum sensor retains the last message details for HA state history."""
    coordinator = TextbeltStatusCoordinator(hass, FakeClient({"status": "PENDING"}))
    coordinator.set_last_message("abc", "+1", "hello")
    sensor = LastMessageStatusSensor(coordinator, _entry())

    assert sensor.native_value == MessageStatus.PENDING
    assert sensor.options == ["pending", "delivered", "failed", "unknown"]
    assert sensor.extra_state_attributes == {
        "delivery_status": "pending",
        "text_id": "abc",
        "phone": "+1",
        "message": "hello",
    }
    assert sensor.state_class is None
    await coordinator.async_shutdown()
