"""Home Assistant custom component to send SMS using the Textbelt API."""

from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING

from homeassistant.components import webhook
from homeassistant.const import Platform
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TextbeltApiClient, TextbeltApiClientError
from .const import DOMAIN, LOGGER

if TYPE_CHECKING:
    from aiohttp import web
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers.typing import ConfigType

PLATFORMS: list[Platform] = [Platform.SENSOR]


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

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = client

    # Load platforms (sensors)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def handle_webhook(
        hass: HomeAssistant,
        _webhook_id: str,  # underscore prefix indicates intentionally unused
        request: web.Request,
    ) -> None:
        """Handle incoming webhook from Textbelt for SMS replies."""
        data = await request.json()
        LOGGER.info("Received SMS reply via webhook: %s", data)
        hass.bus.async_fire("textbelt_sms_reply", data)

    # Ensure any existing webhook is unregistered first
    with suppress(ValueError):
        webhook.async_unregister(hass, WEBHOOK_ID)

    try:
        webhook.async_register(
            hass,
            DOMAIN,
            "Textbelt SMS Reply Webhook",
            WEBHOOK_ID,
            handle_webhook,
        )
    except ValueError as err:
        LOGGER.error("Failed to register webhook: %s", err)
        return False

    async def handle_send_sms(call: ServiceCall) -> None:
        """Handle the send_sms service call to send an SMS using Textbelt."""
        LOGGER.debug("Handling send_sms service call")
        phone = call.data.get("phone")
        message = call.data.get("message")

        # Construct the public webhook URL (user must expose HA to the internet)
        webhook_url = None
        if hass.config.external_url:
            webhook_url = f"{hass.config.external_url}/api/webhook/{WEBHOOK_ID}"

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
            text_id = result.get("textId")
            # Find the sensor entity and update it
            entity_reg = hass.helpers.entity_registry.async_get(hass)
            sensor_entity_id = f"sensor.{DOMAIN}_last_message_status"
            sensor = entity_reg.async_get(sensor_entity_id)

            if sensor:
                # Get the actual entity object
                sensor_state = hass.states.get(sensor.entity_id)
                if sensor_state:
                    for entity in hass.data[DOMAIN].get("entities", []):
                        if entity.entity_id == sensor.entity_id:
                            LOGGER.debug("Updating sensor with text_id: %s", text_id)
                            entity.set_last_text_id(text_id)
                            entity.update_message_info(phone, message)
                            break
        else:
            LOGGER.error("Failed to send SMS: %s", result.get("error"))

    # Register the send_sms service
    LOGGER.debug("Registering send_sms service")
    hass.services.async_register(DOMAIN, "send_sms", handle_send_sms)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and unregister the webhook."""
    LOGGER.debug("Unloading Textbelt SMS config entry")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        with suppress(ValueError):
            webhook.async_unregister(hass, WEBHOOK_ID)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry."""
    LOGGER.debug("Reloading Textbelt SMS config entry")
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
