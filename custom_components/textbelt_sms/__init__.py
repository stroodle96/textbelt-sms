"""Home Assistant custom component to send SMS using the Textbelt API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.webhook import (
    async_register_webhook,
    async_unregister_webhook,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TextbeltApiClient, TextbeltApiClientError
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from aiohttp import web
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers.typing import ConfigType


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
        api_key = _validate_api_key(entry.data.get("api_key"))
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
        LOGGER.info("Received SMS reply via webhook: %s", data)
        # Fire a Home Assistant event for automations or further processing
        hass.bus.async_fire("textbelt_sms_reply", data)

    # Register the webhook endpoint
    async_register_webhook(
        hass,
        DOMAIN,
        "Textbelt SMS Reply Webhook",
        WEBHOOK_ID,
        handle_webhook,
    )

    # Store the client for use in the service
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    async def handle_send_sms(call: ServiceCall) -> None:
        """Handle the send_sms service call to send an SMS using Textbelt."""
        LOGGER.debug("Handling send_sms service call")
        phone = call.data.get("phone")
        message = call.data.get("message")
        # Construct the public webhook URL (user must expose HA to the internet)
        base_url = getattr(hass.config.api, "base_url", "")
        webhook_url = f"{base_url}/api/webhook/{WEBHOOK_ID}"
        if not phone or not message:
            LOGGER.error("Phone and message must be provided to send_sms service")
            return

        try:
            result = await client.async_send_sms(phone, message, webhook_url)
        except TextbeltApiClientError as err:
            LOGGER.error("Error while sending SMS: %s", err)
            return

        if result.get("success"):
            LOGGER.info("SMS sent successfully to %s", phone)
        else:
            LOGGER.error("Failed to send SMS: %s", result.get("error"))

    # Register the send_sms service
    LOGGER.debug("Registering send_sms service")
    hass.services.async_register(DOMAIN, "send_sms", handle_send_sms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and unregister the webhook."""
    LOGGER.debug("Unloading Textbelt SMS config entry")
    hass.data[DOMAIN].pop(entry.entry_id, None)
    async_unregister_webhook(hass, WEBHOOK_ID)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry."""
    LOGGER.debug("Reloading Textbelt SMS config entry")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
