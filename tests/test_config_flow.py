"""Tests for the Textbelt SMS config flow."""

from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms.const import DOMAIN


async def test_user_form(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "form"
    assert result["step_id"] == "user"
    assert result["errors"] == {}


async def test_user_form_rejects_missing_api_key(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_API_KEY: ""}
    )

    assert result["type"] == "form"
    assert result["errors"] == {CONF_API_KEY: "invalid_api_key"}


async def test_user_form_creates_entry(hass: HomeAssistant) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_API_KEY: "test-key"}
    )

    assert result["type"] == "create_entry"
    assert result["title"] == "Textbelt SMS"
    assert result["data"] == {CONF_API_KEY: "test-key"}


async def test_user_form_allows_only_one_instance(hass: HomeAssistant) -> None:
    existing = MockConfigEntry(
        domain=DOMAIN,
        title="Textbelt SMS",
        data={CONF_API_KEY: "test-key"},
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "user"}
    )

    assert result["type"] == "abort"
    assert result["reason"] == "already_configured"
