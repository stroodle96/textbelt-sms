# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Config flow for the Textbelt SMS integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.helpers.selector import TextSelector, TextSelectorConfig

from .const import DOMAIN
from .recipients import CONF_NOTIFICATION_RECIPIENTS, normalize_recipients


class TextbeltSMSConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Textbelt SMS."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        _config_entry: config_entries.ConfigEntry,
    ) -> TextbeltOptionsFlow:
        """Configure outbound notification recipients."""
        return TextbeltOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        if self.hass.config_entries.async_entries(DOMAIN):
            return self.async_abort(reason="already_configured")

        errors = {}
        if user_input is not None:
            api_key = user_input.get(CONF_API_KEY)
            if not api_key:
                errors[CONF_API_KEY] = "invalid_api_key"
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
            description_placeholders={"docs_url": "https://docs.textbelt.com/"},
        )


class TextbeltOptionsFlow(config_entries.OptionsFlowWithReload):
    """Minimal outbound options; recipients do not grant Assist access."""

    async def async_step_init(
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Accept explicit international numbers, preserving other options."""
        errors = {}
        if user_input is not None:
            try:
                recipients = normalize_recipients(
                    user_input.get(CONF_NOTIFICATION_RECIPIENTS, "")
                )
            except ValueError:
                errors[CONF_NOTIFICATION_RECIPIENTS] = "invalid_recipient"
            else:
                return self.async_create_entry(
                    title="",
                    data={
                        **self.config_entry.options,
                        CONF_NOTIFICATION_RECIPIENTS: recipients,
                    },
                )
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NOTIFICATION_RECIPIENTS,
                        default="\n".join(
                            self.config_entry.options.get(
                                CONF_NOTIFICATION_RECIPIENTS, []
                            )
                        ),
                    ): TextSelector(TextSelectorConfig(multiline=True))
                }
            ),
            errors=errors,
        )
