"""Config flow for the Textbelt SMS integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY

from .const import DOMAIN


class TextbeltSMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Textbelt SMS."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        errors = {}
        if user_input is not None:
            api_key = user_input.get(CONF_API_KEY)
            if not api_key:
                errors[CONF_API_KEY] = "API key required."
            if not errors:
                return self.async_create_entry(
                    title="Textbelt SMS",
                    data={CONF_API_KEY: api_key},
                )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_KEY): str,
                }
            ),
            errors=errors,
        )
