# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Home Assistant custom component to send SMS using the Textbelt API."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, NoReturn

import voluptuous as vol
from homeassistant.components.webhook import (
    async_register as async_register_webhook,
)
from homeassistant.components.webhook import (
    async_unregister as async_unregister_webhook,
)
from homeassistant.const import CONF_API_KEY, Platform
from homeassistant.core import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .api import TextbeltApiClient, TextbeltApiClientError, normalize_text_id
from .const import DOMAIN, EVENT_REPLY, LOGGER, SERVICE_SEND_SMS, WEBHOOK_ID
from .sensor import TextbeltStatusCoordinator

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
MISSING_TEXT_ID_ERROR = "Textbelt response did not include a text ID"


def _raise_action_error(message: str) -> NoReturn:
    """Raise a user-visible Home Assistant action error."""
    raise HomeAssistantError(message)


def _validate_api_key(api_key: str | None) -> str:
    """Validate that the API key is provided and is a string."""
    LOGGER.debug("Validating API key")
    msg = "API key must be provided as a string in the integration configuration."
    if not api_key or not isinstance(api_key, str):
        LOGGER.error("Invalid API key: %s", msg)
        raise ValueError(msg)
    return api_key


def _reply_webhook_url(hass: HomeAssistant) -> str | None:
    """Return a provider-reachable reply webhook URL when HA exposes one."""
    try:
        base_url = get_url(hass, allow_internal=False)
    except NoURLAvailableError:
        return None
    return f"{base_url.rstrip('/')}/api/webhook/{WEBHOOK_ID}"


async def async_setup(hass: HomeAssistant, _: ConfigType) -> bool:
    """Set up the Textbelt SMS integration."""
    LOGGER.debug("Setting up Textbelt SMS integration")
    hass.data.setdefault(DOMAIN, {})
    return True


PLATFORMS = [Platform.SENSOR]


@dataclass
class TextbeltRuntimeData:
    """Runtime objects owned by one Textbelt config entry."""

    client: TextbeltApiClient
    coordinator: TextbeltStatusCoordinator
    send_lock: asyncio.Lock
    active: bool = True


async def async_setup_entry(  # noqa: PLR0915
    hass: HomeAssistant, entry: ConfigEntry
) -> bool:
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

    coordinator = TextbeltStatusCoordinator(hass, client)
    runtime = TextbeltRuntimeData(client, coordinator, asyncio.Lock())
    webhook_registered = False
    platform_setup_attempted = False

    try:
        # Register the webhook endpoint.
        async_register_webhook(
            hass,
            DOMAIN,
            "Textbelt SMS Reply Webhook",
            WEBHOOK_ID,
            handle_webhook,
        )
        webhook_registered = True

        # Store one typed runtime object shared by the service and sensor.
        entry.runtime_data = runtime

        async def handle_send_sms(call: ServiceCall) -> None:
            """Handle the send_sms service call to send an SMS using Textbelt."""
            LOGGER.debug("Handling send_sms service call")
            phone = call.data.get("phone")
            message = call.data.get("message")
            # Textbelt must receive an externally reachable URL for SMS replies.
            webhook_url = _reply_webhook_url(hass)
            if not phone or not message:
                _raise_action_error(MISSING_FIELDS_ERROR)

            async with runtime.send_lock:
                if not runtime.active:
                    _raise_action_error(SEND_ERROR)
                try:
                    result = await client.async_send_sms(phone, message, webhook_url)
                except TextbeltApiClientError:
                    _raise_action_error(SEND_ERROR)

                if result.get("success"):
                    try:
                        text_id = normalize_text_id(result.get("textId"))
                    except ValueError:
                        _raise_action_error(MISSING_TEXT_ID_ERROR)
                    if not runtime.active:
                        return
                    coordinator.set_last_message(text_id, phone, message)
                    hass.async_create_task(coordinator.async_request_refresh())
                    return
                _raise_action_error(FAILED_SEND_ERROR)

        # Register the send_sms service.
        LOGGER.debug("Registering send_sms service")
        hass.services.async_register(
            DOMAIN, SERVICE_SEND_SMS, handle_send_sms, schema=SERVICE_SCHEMA
        )
        platform_setup_attempted = True
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except Exception:
        runtime.active = False
        if platform_setup_attempted:
            try:
                await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
            except Exception:  # noqa: BLE001 - preserve the original setup error
                LOGGER.exception("Failed to roll back Textbelt SMS platforms")
        await coordinator.async_shutdown()
        entry.runtime_data = None
        hass.services.async_remove(DOMAIN, SERVICE_SEND_SMS)
        if webhook_registered:
            async_unregister_webhook(hass, WEBHOOK_ID)
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry and unregister the webhook."""
    LOGGER.debug("Unloading Textbelt SMS config entry")
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if not unload_ok:
        return False
    if entry.runtime_data is not None:
        entry.runtime_data.active = False
        await entry.runtime_data.coordinator.async_shutdown()
    entry.runtime_data = None
    hass.services.async_remove(DOMAIN, SERVICE_SEND_SMS)
    async_unregister_webhook(hass, WEBHOOK_ID)
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry."""
    LOGGER.debug("Reloading Textbelt SMS config entry")
    if not await async_unload_entry(hass, entry):
        return
    await async_setup_entry(hass, entry)
