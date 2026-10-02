# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Assist configuration behavior and upgrade defaults."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from homeassistant.const import CONF_API_KEY
from homeassistant.helpers.config_validation import custom_serializer
from voluptuous_serialize import convert

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms.const import DOMAIN
from custom_components.textbelt_sms.options import AssistOptions


def test_upgrade_is_opt_in() -> None:
    """Existing outbound options never grant permission to control the home."""
    options = AssistOptions.from_mapping({"notification_recipients": ["+15551234567"]})
    assert not options.enabled
    assert options.pipeline_id is None
    assert options.authorized_senders == ()
    assert options.conversation_timeout == 1800  # noqa: PLR2004 -- upgrade contract.


@pytest.mark.parametrize("value", [None, "", "preferred"])
def test_preferred_selector_normalizes(value: str | None) -> None:
    """The frontend preferred sentinel never becomes an explicit pipeline ID."""
    assert AssistOptions.from_mapping({"pipeline_id": value}).pipeline_id is None


@pytest.mark.parametrize(
    "url",
    [
        None,
        "http://example.com",
        "https://localhost",
        "https://192.168.1.2",
        "https://example.com/?token=x",
        "https://user:pass@example.com",
    ],
)
async def test_enabling_requires_external_callback(
    hass: HomeAssistant, url: str | None
) -> None:
    """An allowlist alone cannot enable ingress with an unsuitable callback base."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_API_KEY: "test-key"})
    entry.add_to_hass(hass)
    hass.config.external_url = url
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={"assist_enabled": True, "authorized_senders": "+15551234567"},
    )
    assert result["errors"]["base"] == "invalid_callback_url"


async def test_recipients_do_not_authorize_assist(hass: HomeAssistant) -> None:
    """Notification targets cannot satisfy the independent sender allowlist."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-key"},
        options={"notification_recipients": ["+15551234567"]},
    )
    entry.add_to_hass(hass)
    hass.config.external_url = "https://ha.example.com"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input={"assist_enabled": True}
    )
    assert result["errors"] == {"authorized_senders": "authorized_sender_required"}


@pytest.mark.parametrize(
    ("input_data", "error"),
    [
        (
            {"authorized_senders": "5551234567"},
            {"authorized_senders": "invalid_recipient"},
        ),
        ({"conversation_timeout": 0}, {"conversation_timeout": "invalid_timeout"}),
        ({"conversation_timeout": 1.5}, {"conversation_timeout": "invalid_timeout"}),
    ],
)
async def test_reject_invalid_assist_options(
    hass: HomeAssistant, input_data: dict, error: dict
) -> None:
    """Malformed authorization or timeout values are never persisted."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_API_KEY: "test-key"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], user_input=input_data
    )
    assert result["errors"] == error


async def test_options_form_serializes_for_frontend(hass: HomeAssistant) -> None:
    """The actual options schema can be rendered by Home Assistant's frontend."""
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_API_KEY: "test-key"})
    entry.add_to_hass(hass)
    result = await hass.config_entries.options.async_init(entry.entry_id)
    fields = convert(result["data_schema"], custom_serializer=custom_serializer)
    timeout = next(field for field in fields if field["name"] == "conversation_timeout")
    assert timeout["selector"]["number"]["mode"] == "box"
