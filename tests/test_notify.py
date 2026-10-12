# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Native notification targets and explicit recipient options."""

from typing import Never
from unittest.mock import AsyncMock

import pytest
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, HomeAssistantError
from homeassistant.helpers import entity_registry as er
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms.api import (
    TextbeltApiClientError,
    TextbeltApiClientUnknownOutcomeError,
)
from custom_components.textbelt_sms.const import DOMAIN
from custom_components.textbelt_sms.recipients import normalize_recipients
from tests.test_init import _Session


async def test_native_targets(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Configured targets share formatting, identity, and failure semantics."""
    session = _Session()
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: session
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-key"},
        options={"notification_recipients": ["+15551234567", "+15551234568"]},
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    targets = hass.states.async_entity_ids("notify")
    assert len(targets) == len(entry.options["notification_recipients"])
    assert all("155512345" not in target for target in targets)
    await hass.services.async_call(
        "notify",
        "send_message",
        {"entity_id": targets, "message": "Water detected", "title": "Leak"},
        blocking=True,
    )
    assert {data["phone"] for _, data in session.calls} == {
        "+15551234567",
        "+15551234568",
    }
    assert all(data["message"] == "Leak: Water detected" for _, data in session.calls)
    previous = hass.states.get(targets[0]).state
    entry.runtime_data.client.async_send_sms = AsyncMock(
        return_value={"success": False}
    )
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "notify",
            "send_message",
            {"entity_id": targets[0], "message": "fail"},
            blocking=True,
        )
    assert hass.states.get(targets[0]).state == previous
    await hass.config_entries.async_unload(entry.entry_id)


async def test_options_normalize_and_preserve(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Options normalize explicit numbers without losing future options."""
    monkeypatch.setattr(
        hass.config_entries, "async_reload", AsyncMock(return_value=True)
    )
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_API_KEY: "test-key"}, options={"future": True}
    )
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            "notification_recipients": (
                "+1 (555) 123-4567\n+15551234567\n+44 20 1234 5678"
            )
        },
    )
    assert result["type"] == "create_entry"
    assert result["data"] == {
        "future": True,
        "notification_recipients": ["+15551234567", "+442012345678"],
    }


@pytest.mark.parametrize(
    "number",
    [
        "+1",
        "15551234567",
        "+\uff11\uff12\uff13",
        "+0123",
        "+123 ext 5",
        "+1234567890123456",
    ],
)
async def test_options_reject_ambiguous_numbers(
    hass: HomeAssistant, number: str
) -> None:
    """No country inference, extensions, or non-ASCII digits."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_API_KEY: "test-key"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"notification_recipients": number}
    )
    assert result["type"] == "form"
    assert result["errors"] == {"notification_recipients": "invalid_recipient"}


async def test_recipient_reload_remove_readd(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removed targets stop sending and re-added recipients retain identity."""
    session = _Session()
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: session
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-key"},
        options={"notification_recipients": ["+15551234567", "+15551234568"]},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    registry = er.async_get(hass)
    target = hass.states.async_entity_ids("notify")[0]
    registry.async_update_entity(
        target, new_entity_id="notify.my_renamed_phone", name="My phone"
    )
    await hass.async_block_till_done()
    original = set(hass.states.async_entity_ids("notify"))
    assert "notify.my_renamed_phone" in original
    old_runtime = entry.runtime_data
    hass.config_entries.async_update_entry(
        entry, options={"notification_recipients": []}
    )
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert all(hass.states.get(target).state == "unavailable" for target in original)
    with pytest.raises(HomeAssistantError):
        await old_runtime.async_send(hass, "+15551234567", "stale")
    assert session.calls == []
    hass.config_entries.async_update_entry(
        entry, options={"notification_recipients": ["+15551234568", "+15551234567"]}
    )
    await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()
    assert set(hass.states.async_entity_ids("notify")) == original
    await hass.config_entries.async_unload(entry.entry_id)


@pytest.mark.parametrize(
    ("responses", "outcome"),
    [
        ([{"success": False}], "rejected"),
        ([TextbeltApiClientUnknownOutcomeError("uncertain")], "unknown"),
        ([{"success": True, "textId": "one"}, {"success": False}], "partial"),
    ],
)
async def test_failed_batch_no_success_timestamp(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, responses: list, outcome: str
) -> None:
    """Failed batches retain results and never advance target state."""
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: _Session()
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-key"},
        options={"notification_recipients": ["+15551234567"]},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    target = hass.states.async_entity_ids("notify")[0]
    previous = hass.states.get(target).state
    post = AsyncMock(side_effect=responses)
    entry.runtime_data.client.async_send_sms = post
    refresh = AsyncMock()
    entry.runtime_data.quota_coordinator.async_request_refresh = refresh
    with pytest.raises(HomeAssistantError, match=outcome):
        await hass.services.async_call(
            "notify",
            "send_message",
            {"entity_id": target, "message": "a" * 200},
            blocking=True,
        )
    await hass.async_block_till_done()
    assert hass.states.get(target).state == previous
    assert entry.runtime_data.sender.last_result.outcome == outcome
    refresh.assert_awaited_once()
    assert post.await_count == len(responses)
    assert entry.runtime_data.sender.last_result.accepted_parts == (
        1 if outcome == "partial" else 0
    )
    await hass.config_entries.async_unload(entry.entry_id)


async def test_empty_options_and_number_bounds(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty options retain outbound-only behavior and syntax bounds are explicit."""
    assert normalize_recipients("+12\n+123456789012345") == ["+12", "+123456789012345"]
    monkeypatch.setattr(
        hass.config_entries, "async_reload", AsyncMock(return_value=True)
    )
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_API_KEY: "test-key"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"notification_recipients": ""}
    )
    assert result["data"] == {"notification_recipients": []}


async def test_accepted_notification_survives_quota_outage(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Quota failures cannot make an accepted alert fail or suppress its timestamp."""
    session = _Session()
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: session
    )
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-key"},
        options={"notification_recipients": ["+15551234567"]},
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    target = hass.states.async_entity_ids("notify")[0]

    async def quota_outage() -> Never:
        msg = "quota offline"
        raise TextbeltApiClientError(msg)

    entry.runtime_data.client.async_get_quota = quota_outage

    async def refresh_now() -> None:
        await entry.runtime_data.quota_coordinator.async_refresh()

    refresh = AsyncMock(side_effect=refresh_now)
    entry.runtime_data.quota_coordinator.async_request_refresh = refresh
    await hass.services.async_call(
        "notify",
        "send_message",
        {"entity_id": target, "message": "accepted"},
        blocking=True,
    )
    await hass.async_block_till_done()
    assert hass.states.get(target).state not in ("unknown", "unavailable")
    assert not entry.runtime_data.quota_coordinator.last_update_success
    refresh.assert_awaited_once()
    assert len(session.calls) == 1
    await hass.config_entries.async_unload(entry.entry_id)


async def test_options_automatically_reload_targets(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Saving recipient options replaces runtime and exposes the native target."""
    session = _Session()
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: session
    )
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_API_KEY: "test-key"})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert not hass.states.async_entity_ids("notify")
    previous_runtime = entry.runtime_data
    result = await hass.config_entries.options.async_init(entry.entry_id)
    await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"notification_recipients": "+15551234567"},
    )
    await hass.async_block_till_done()
    assert entry.runtime_data is not previous_runtime
    assert not previous_runtime.active
    target = hass.states.async_entity_ids("notify")[0]
    with pytest.raises(HomeAssistantError, match="Unsupported character"):
        await hass.services.async_call(
            "notify",
            "send_message",
            {"entity_id": target, "message": "\u6f22"},
            blocking=True,
        )
    assert session.calls == []
    assert hass.states.get(target).state == "unknown"
    await hass.config_entries.async_unload(entry.entry_id)
