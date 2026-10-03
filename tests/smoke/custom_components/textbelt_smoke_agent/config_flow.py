# Copyright (c) 2026 Textbelt SMS contributors
"""Disposable deterministic agent config flow."""

import voluptuous as vol

# ruff: noqa: ANN001, ANN201
from homeassistant import config_entries


class SmokeFlow(config_entries.ConfigFlow, domain="textbelt_smoke_agent"):
    """Create two labelled agent entries through the normal HA flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Accept a synthetic label."""
        if user_input is not None:
            return self.async_create_entry(title=user_input["label"], data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=vol.Schema({"label": str})
        )
