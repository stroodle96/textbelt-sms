"""Home Assistant custom component to send SMS using the Textbelt API."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TextbeltApiClient
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall


def _validate_api_key(api_key: str | None) -> str:
    """Validate that the API key is provided and is a string."""
    msg = "API key must be provided as a string in the integration configuration."
    if not api_key or not isinstance(api_key, str):
        raise ValueError(msg)
    return api_key


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Textbelt SMS integration from a config entry."""
    api_key = _validate_api_key(entry.data.get("api_key"))
    session = async_get_clientsession(hass)
    client = TextbeltApiClient(api_key, session)

    # Store the client for use in the service
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = client

    async def handle_send_sms(call: ServiceCall) -> None:
        """
        Handle the service call to send an SMS using Textbelt.

        Expects 'phone' and 'message' in the service data.
        """
        phone = call.data.get("phone")
        message = call.data.get("message")
        if not phone or not message:
            LOGGER.error("Phone and message must be provided to send_sms service.")
            return
        try:
            result = await client.async_send_sms(phone, message)
            if result.get("success"):
                LOGGER.info(f"SMS sent successfully to {phone}.")
            else:
                LOGGER.error(f"Failed to send SMS: {result.get('error')}")
        except (KeyError, ValueError) as err:
            LOGGER.error(f"Error while sending SMS: {err}")

    # Register the send_sms service
    hass.services.async_register(
        DOMAIN,
        "send_sms",
        handle_send_sms,
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and remove the client."""
    hass.data[DOMAIN].pop(entry.entry_id, None)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
