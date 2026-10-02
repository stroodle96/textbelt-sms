# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Config flow for the Textbelt SMS integration."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_API_KEY
from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.selector import (
    AssistPipelineSelector,
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TextSelectorConfig,
)

from .assist import async_ensure_assist_pipeline, async_resolve_pipeline
from .const import DOMAIN
from .options import (
    CONF_ASSIST_ENABLED,
    CONF_AUTHORIZED_SENDERS,
    CONF_CONVERSATION_TIMEOUT,
    CONF_PIPELINE_ID,
    DEFAULT_CONVERSATION_TIMEOUT,
    callback_base_url,
    normalize_authorized_senders,
    normalize_conversation_timeout,
    normalize_pipeline_id,
)
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
    """Outbound destinations and opt-in native Assist configuration."""

    async def async_step_init(  # noqa: PLR0912 -- report each independent option error.
        self, user_input: dict | None = None
    ) -> config_entries.ConfigFlowResult:
        """Validate independent authorization and preserve unrelated options."""
        errors = {}
        options = dict(self.config_entry.options)
        if user_input is not None:
            options.update(user_input)
            try:
                options[CONF_NOTIFICATION_RECIPIENTS] = normalize_recipients(
                    user_input.get(
                        CONF_NOTIFICATION_RECIPIENTS,
                        "\n".join(
                            self.config_entry.options.get(
                                CONF_NOTIFICATION_RECIPIENTS, []
                            )
                        ),
                    )
                )
            except ValueError:
                errors[CONF_NOTIFICATION_RECIPIENTS] = "invalid_recipient"
            for key, normalize, error in (
                (
                    CONF_AUTHORIZED_SENDERS,
                    normalize_authorized_senders,
                    "invalid_recipient",
                ),
                (CONF_PIPELINE_ID, normalize_pipeline_id, "invalid_pipeline"),
                (
                    CONF_CONVERSATION_TIMEOUT,
                    normalize_conversation_timeout,
                    "invalid_timeout",
                ),
            ):
                if key in options:
                    try:
                        value = normalize(options[key])
                        options[key] = (
                            list(value) if key == CONF_AUTHORIZED_SENDERS else value
                        )
                    except ValueError:
                        errors[key] = error
            if options.get(CONF_ASSIST_ENABLED, False):
                if (
                    not options.get(CONF_AUTHORIZED_SENDERS)
                    and CONF_AUTHORIZED_SENDERS not in errors
                ):
                    errors[CONF_AUTHORIZED_SENDERS] = "authorized_sender_required"
                try:
                    callback_base_url(self.hass.config.external_url)
                except ValueError:
                    errors["base"] = "invalid_callback_url"
                if not errors:
                    try:
                        if await async_ensure_assist_pipeline(self.hass):
                            async_resolve_pipeline(
                                self.hass, options.get(CONF_PIPELINE_ID)
                            )
                        else:
                            errors[CONF_PIPELINE_ID] = "invalid_pipeline"
                    except (HomeAssistantError, KeyError, ValueError):
                        errors[CONF_PIPELINE_ID] = "invalid_pipeline"
            if not errors:
                return self.async_create_entry(title="", data=options)
        defaults = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_NOTIFICATION_RECIPIENTS,
                        default="\n".join(
                            defaults.get(CONF_NOTIFICATION_RECIPIENTS, [])
                        ),
                    ): TextSelector(TextSelectorConfig(multiline=True)),
                    vol.Optional(
                        CONF_ASSIST_ENABLED,
                        description={
                            "suggested_value": defaults.get(CONF_ASSIST_ENABLED, False)
                        },
                    ): BooleanSelector(),
                    vol.Optional(
                        CONF_PIPELINE_ID,
                        description={
                            "suggested_value": defaults.get(CONF_PIPELINE_ID)
                            or "preferred"
                        },
                    ): AssistPipelineSelector(),
                    vol.Optional(
                        CONF_AUTHORIZED_SENDERS,
                        description={
                            "suggested_value": "\n".join(
                                defaults.get(CONF_AUTHORIZED_SENDERS, [])
                            )
                        },
                    ): TextSelector(TextSelectorConfig(multiline=True)),
                    vol.Optional(
                        CONF_CONVERSATION_TIMEOUT,
                        description={
                            "suggested_value": defaults.get(
                                CONF_CONVERSATION_TIMEOUT, DEFAULT_CONVERSATION_TIMEOUT
                            )
                        },
                    ): NumberSelector(
                        NumberSelectorConfig(mode=NumberSelectorMode.BOX, step=1)
                    ),
                }
            ),
            errors=errors,
        )
