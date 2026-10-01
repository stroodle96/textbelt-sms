# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Quota entity behavior through Home Assistant's real sensor platform."""

from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import TYPE_CHECKING, Self

import pytest
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.textbelt_sms.const import DOMAIN

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from freezegun.api import FrozenDateTimeFactory

ENTITY_ID = "sensor.textbelt_sms_quota_remaining"


class Response:
    """Minimal HTTP response at the external API boundary."""

    status = 200

    def __init__(self, payload: dict) -> None:
        """Store one provider payload."""
        self.payload = payload

    async def __aenter__(self) -> Self:
        """Enter the HTTP response context."""
        return self

    async def __aexit__(self, *_args: object) -> None:
        """Exit the HTTP response context."""

    async def json(self) -> dict:
        """Return provider JSON."""
        return self.payload


class Session:
    """Controllable provider allowing quota failures independently of sends."""

    def __init__(self) -> None:
        """Start with 98 credits."""
        self.balance = 98
        self.quota_ok = True
        self.send_ok = True
        self.quota_requests: list[str] = []
        self.sends = 0

    def get(self, url: str, **_kwargs: object) -> Response:
        """Serve quota or delivery status."""
        if "/quota/" in url:
            self.quota_requests.append(url)
            return Response({"success": self.quota_ok, "quotaRemaining": self.balance})
        return Response({"status": "DELIVERED"})

    def post(self, _url: str, *, data: dict, **_kwargs: object) -> Response:
        """Send against the configured key and consume a credit on success."""
        assert data["key"] == "quota-test-key"
        self.sends += 1
        if self.send_ok:
            self.balance -= 1
        return Response(
            {
                "success": self.send_ok,
                "textId": self.sends,
                "quotaRemaining": self.balance,
            }
        )


@pytest.fixture
async def quota_entry(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> AsyncGenerator[tuple[MockConfigEntry, Session]]:
    """Set up and clean up a real config entry with only HTTP replaced."""
    assert await async_setup_component(hass, "homeassistant", {})
    monkeypatch.setenv("TEXTBELT_SMS_API_BASE_URL", "http://textbelt.test")
    session = Session()
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: session
    )
    entry = MockConfigEntry(
        domain=DOMAIN, title="Textbelt SMS", data={CONF_API_KEY: "quota-test-key"}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    yield entry, session
    await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()


async def refresh(hass: HomeAssistant) -> None:
    """Refresh the public quota entity."""
    await hass.services.async_call(
        "homeassistant", "update_entity", {"entity_id": ENTITY_ID}, blocking=True
    )
    await hass.async_block_till_done()


async def test_quota_is_available_without_sending(
    hass: HomeAssistant, quota_entry: tuple[MockConfigEntry, Session], api_base_url: str
) -> None:
    """Startup must expose a numeric balance using the configured API key."""
    entry, session = quota_entry
    state = hass.states.get(ENTITY_ID)
    assert state is not None
    assert state.state == "98"
    assert state.attributes["unit_of_measurement"] == "credits"
    assert session.quota_requests == [f"{api_base_url}/quota/quota-test-key"]
    assert session.sends == 0
    registry_entry = er.async_get(hass).async_get(ENTITY_ID)
    assert registry_entry.unique_id == f"{entry.entry_id}_quota_remaining"
    assert "quota-test-key" not in str(state.as_dict())


async def test_zero_quota_is_a_valid_state(
    hass: HomeAssistant, quota_entry: tuple[MockConfigEntry, Session]
) -> None:
    """Zero means an empty balance, not unknown or unavailable."""
    _, session = quota_entry
    session.balance = 0
    await refresh(hass)
    assert hass.states.get(ENTITY_ID).state == "0"


async def test_quota_failure_recovers_and_sending_remains_available(
    hass: HomeAssistant,
    quota_entry: tuple[MockConfigEntry, Session],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Quota lookup failure must affect only quota availability."""
    _, session = quota_entry
    session.quota_ok = False
    await refresh(hass)
    assert hass.states.get(ENTITY_ID).state == "unavailable"
    await hass.services.async_call(
        DOMAIN, "send_sms", {"phone": "+15551234567", "message": "hello"}, blocking=True
    )
    await hass.async_block_till_done()
    assert session.sends == 1
    assert (
        hass.states.get("sensor.textbelt_sms_last_message_status").state == "delivered"
    )
    session.quota_ok = True
    freezer.tick(timedelta(seconds=301))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "97"


@pytest.mark.parametrize("send_ok", [True, False])
async def test_send_refreshes_quota_even_when_provider_rejects_send(
    hass: HomeAssistant, quota_entry: tuple[MockConfigEntry, Session], *, send_ok: bool
) -> None:
    """Send attempts refresh the real balance, including quota exhaustion."""
    _, session = quota_entry
    session.send_ok = send_ok
    session.balance = 50 if send_ok else 0
    if send_ok:
        await hass.services.async_call(
            DOMAIN,
            "send_sms",
            {"phone": "+15551234567", "message": "hello"},
            blocking=True,
        )
    else:
        with pytest.raises(HomeAssistantError):
            await hass.services.async_call(
                DOMAIN,
                "send_sms",
                {"phone": "+15551234567", "message": "hello"},
                blocking=True,
            )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == ("49" if send_ok else "0")


async def test_quota_polls_and_stops_after_unload(
    hass: HomeAssistant,
    quota_entry: tuple[MockConfigEntry, Session],
    freezer: FrozenDateTimeFactory,
) -> None:
    """Changes outside HA are discovered in five minutes; unload cancels polling."""
    entry, session = quota_entry
    session.balance = 125
    freezer.tick(timedelta(seconds=301))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "125"
    assert await hass.config_entries.async_unload(entry.entry_id)
    request_count = len(session.quota_requests)
    freezer.tick(timedelta(seconds=601))
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert len(session.quota_requests) == request_count


async def test_quota_reloads_with_updated_balance_and_same_entity(
    hass: HomeAssistant, quota_entry: tuple[MockConfigEntry, Session]
) -> None:
    """Reload must refetch the balance without creating duplicate sensors."""
    entry, session = quota_entry
    session.balance = 150
    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "150"
    entities = er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
    assert sum(entity.entity_id == ENTITY_ID for entity in entities) == 1


async def test_quota_initial_failure_does_not_block_setup(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An unavailable quota endpoint must not disable the SMS integration."""
    monkeypatch.setenv("TEXTBELT_SMS_API_BASE_URL", "http://textbelt.test")
    session = Session()
    session.quota_ok = False
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: session
    )
    entry = MockConfigEntry(
        domain=DOMAIN, title="Textbelt SMS", data={CONF_API_KEY: "quota-test-key"}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "unavailable"
    session.quota_ok = True
    await hass.services.async_call(
        DOMAIN, "send_sms", {"phone": "+15551234567", "message": "hello"}, blocking=True
    )
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY_ID).state == "97"
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_unload_discards_inflight_quota_response(
    hass: HomeAssistant,
    quota_entry: tuple[MockConfigEntry, Session],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An old request must not publish new data after its entry unloads."""
    entry, _ = quota_entry
    coordinator = entry.runtime_data.quota_coordinator
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocked_quota() -> int:
        started.set()
        await release.wait()
        return 12

    monkeypatch.setattr(entry.runtime_data.client, "async_get_quota", blocked_quota)
    task = asyncio.create_task(coordinator.async_refresh())
    await started.wait()
    assert await hass.config_entries.async_unload(entry.entry_id)
    release.set()
    await task
    assert coordinator.data == 98  # noqa: PLR2004 - known pre-unload balance
