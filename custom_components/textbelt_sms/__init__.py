# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Home Assistant custom component to send SMS using the Textbelt API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import voluptuous as vol
from homeassistant.components.webhook import (
    async_register as async_register_webhook,
)
from homeassistant.components.webhook import (
    async_unregister as async_unregister_webhook,
)
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TextbeltApiClient, TextbeltApiClientError
from .const import DOMAIN, EVENT_REPLY, LOGGER, SERVICE_SEND_SMS

if TYPE_CHECKING:
    from aiohttp import web
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers.typing import ConfigType


CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required("phone"): cv.string,
        vol.Required("message"): cv.string,
    }
)
MISSING_FIELDS_ERROR = "Phone and message are required"
SEND_ERROR = "Unable to send SMS via Textbelt"
FAILED_SEND_ERROR = "Textbelt did not send the SMS"


def _validate_api_key(api_key: str | None) -> str:
    """Validate that the API key is provided and is a string."""
    LOGGER.debug("Validating API key")
    msg = "API key must be provided as a string in the integration configuration."
    if not api_key or not isinstance(api_key, str):
        LOGGER.error("Invalid API key: %s", msg)
        raise ValueError(msg)
    return api_key


async def async_setup(hass: HomeAssistant, _: ConfigType) -> bool:
    """Set up the Textbelt SMS integration."""
    LOGGER.debug("Setting up Textbelt SMS integration")
    hass.data.setdefault(DOMAIN, {})
    return True


WEBHOOK_ID = "textbelt_sms_reply"


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Textbelt SMS integration from a config entry."""
    LOGGER.debug("Setting up Textbelt SMS config entry")
    try:
        api_key = _validate_api_key(entry.data.get(CONF_API_KEY))
        session = async_get_clientsession(hass)
        client = TextbeltApiClient(api_key, session)
    except ValueError as err:
        LOGGER.error("Failed to validate API key: %s", err)
        return False

    async def handle_webhook(
        hass: HomeAssistant,
        _webhook_id: str,
        request: web.Request,
    ) -> None:
        """
        Handle incoming webhook from Textbelt for SMS replies.

        The webhook handler receives the Home Assistant instance, the webhook id
        (unused, prefixed with an underscore) and the aiohttp request.

        """
        data = await request.json()
        # Fire a Home Assistant event for automations or further processing
        hass.bus.async_fire(EVENT_REPLY, data)

    # Register the webhook endpoint
    async_register_webhook(
        hass,
        DOMAIN,
        "Textbelt SMS Reply Webhook",
        WEBHOOK_ID,
        handle_webhook,
    )

    # Store the client on the config entry so all runtime consumers share the
    # same typed lifecycle state.  The service closure below deliberately
    # captures this instance instead of looking it up through the entity
    # registry or a second mutable store.
    entry.runtime_data = client

    async def handle_send_sms(call: ServiceCall) -> None:
        """Handle the send_sms service call to send an SMS using Textbelt."""
        LOGGER.debug("Handling send_sms service call")
        phone = call.data.get("phone")
        message = call.data.get("message")
        # Construct the public webhook URL (user must expose HA to the internet)
        base_url = getattr(hass.config.api, "base_url", "") or ""
        webhook_url = (
            f"{base_url.rstrip('/')}/api/webhook/{WEBHOOK_ID}" if base_url else None
        )
        if not phone or not message:
            raise HomeAssistantError(MISSING_FIELDS_ERROR)

        try:
            result = await client.async_send_sms(phone, message, webhook_url)
        except TextbeltApiClientError as err:
            raise HomeAssistantError(SEND_ERROR) from err

        if result.get("success"):
            return
        raise HomeAssistantError(FAILED_SEND_ERROR)

    # Register the send_sms service
    LOGGER.debug("Registering send_sms service")
    hass.services.async_register(
        DOMAIN, SERVICE_SEND_SMS, handle_send_sms, schema=SERVICE_SCHEMA
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and unregister the webhook."""
    LOGGER.debug("Unloading Textbelt SMS config entry")
    entry.runtime_data = None
    hass.services.async_remove(DOMAIN, SERVICE_SEND_SMS)
    async_unregister_webhook(hass, WEBHOOK_ID)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry."""
    LOGGER.debug("Reloading Textbelt SMS config entry")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
