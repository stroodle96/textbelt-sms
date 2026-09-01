# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Tests for the Textbelt message status coordinator and sensor."""

import asyncio
from typing import Self
from unittest.mock import AsyncMock

import pytest
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
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
    client = FakeClient({"status": "DELIVERED"})
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
    client = FakeClient({"status": "FAILED"})
    coordinator = TextbeltStatusCoordinator(hass, client)
    coordinator.set_last_message("abc", "+1", "hello")
    await coordinator.async_refresh()
    assert coordinator.data.status is MessageStatus.FAILED

    client.response = {"status": "IN_TRANSIT"}
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


async def test_sensor_starts_as_available_unknown(hass: HomeAssistant) -> None:
    """Expose unknown before the first message is sent."""
    coordinator = TextbeltStatusCoordinator(hass, FakeClient({}))
    sensor = LastMessageStatusSensor(coordinator, _entry())

    assert sensor.native_value == MessageStatus.UNKNOWN
    assert sensor.available is True
    await coordinator.async_shutdown()


async def test_coordinator_maps_sending_and_sent_to_pending(
    hass: HomeAssistant,
) -> None:
    """Provider in-progress statuses remain pending to users."""
    client = FakeClient({"status": "SENDING"})
    coordinator = TextbeltStatusCoordinator(hass, client)
    coordinator.set_last_message(123, "+1", "hello")
    await coordinator.async_refresh()
    assert coordinator.data.status is MessageStatus.PENDING
    assert coordinator.data.text_id == "123"

    client.response = {"status": "sent"}
    await coordinator.async_refresh()
    assert coordinator.data.status is MessageStatus.PENDING
    await coordinator.async_shutdown()


class BlockingClient(FakeClient):
    """Status client whose response can be interleaved with a new send."""

    def __init__(self) -> None:
        """Initialize synchronization events."""
        super().__init__({"status": "DELIVERED"})
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def _get_status(self, _text_id: str) -> dict:
        """Wait until the test releases the controlled response."""
        self.started.set()
        await self.release.wait()
        return self.response


class SetupResponse:
    """Minimal successful send response for platform setup."""

    status = 200

    async def __aenter__(self) -> Self:
        """Enter the response context."""
        return self

    async def __aexit__(self, *_args: object) -> None:
        """Exit the response context."""

    async def json(self) -> dict[str, bool | int]:
        """Return a successful numeric-ID response."""
        return {"success": True, "textId": 1}


class SetupSession:
    """Minimal HTTP session for platform setup."""

    def post(self, _url: str, *, data: dict[str, str]) -> SetupResponse:
        """Return a successful response."""
        del data
        return SetupResponse()


async def test_stale_status_response_cannot_overwrite_newer_message(
    hass: HomeAssistant,
) -> None:
    """An old status response preserves metadata from the newer message."""
    client = BlockingClient()
    coordinator = TextbeltStatusCoordinator(hass, client)
    coordinator.set_last_message("old", "+1", "old message")
    refresh = asyncio.create_task(coordinator.async_refresh())
    await client.started.wait()
    coordinator.set_last_message("new", "+2", "new message")
    client.release.set()
    await refresh

    assert coordinator.data == LastMessage("new", "+2", "new message")
    await coordinator.async_shutdown()


async def test_shutdown_deactivates_stale_status_response(
    hass: HomeAssistant,
) -> None:
    """A response completing after unload cannot update coordinator state."""
    client = BlockingClient()
    coordinator = TextbeltStatusCoordinator(hass, client)
    coordinator.set_last_message("old", "+1", "old message")
    refresh = asyncio.create_task(coordinator.async_refresh())
    await client.started.wait()
    await coordinator.async_shutdown()
    client.release.set()
    await refresh

    assert coordinator.data == LastMessage("old", "+1", "old message")


async def test_platform_setup_creates_guaranteed_status_entity_id(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The real sensor platform creates the documented object ID and state."""
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession",
        lambda _: SetupSession(),
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Textbelt SMS",
        data={CONF_API_KEY: "test-key"},
        entry_id="platform-entry",
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    state = hass.states.get("sensor.textbelt_sms_last_message_status")
    assert state is not None
    assert state.state == MessageStatus.UNKNOWN
    registry_entry = er.async_get(hass).async_get(
        "sensor.textbelt_sms_last_message_status"
    )
    assert registry_entry is not None
    assert registry_entry.entity_id == "sensor.textbelt_sms_last_message_status"
    assert await hass.config_entries.async_unload(entry.entry_id)
