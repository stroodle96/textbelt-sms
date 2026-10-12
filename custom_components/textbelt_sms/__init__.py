# Copyright (c) 2026 Textbelt SMS contributors
"""Textbelt SMS entry lifecycle, shared outbound runtime and verified replies."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal, NoReturn

import voluptuous as vol
from aiohttp import web
from homeassistant.components.webhook import async_generate_id
from homeassistant.components.webhook import async_register as async_register_webhook
from homeassistant.components.webhook import (
    async_unregister as async_unregister_webhook,
)
from homeassistant.const import CONF_API_KEY, EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import HomeAssistantError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .api import TextbeltApiClient
from .assist import async_ensure_assist_pipeline, async_resolve_pipeline
from .const import (
    CONF_WEBHOOK_ID,
    CONFIG_VERSION,
    DOMAIN,
    LOGGER,
    SERVICE_SEND_SMS,
    SERVICE_START_CONVERSATION,
    WEBHOOK_ID,
    reply_key_usable,
)
from .conversation import GREETING, ConversationManager
from .models import MessagePreparationError
from .options import AssistOptions, callback_base_url
from .sender import SendResult, TextbeltSender
from .sensor import TextbeltQuotaCoordinator, TextbeltStatusCoordinator
from .state import ReplyState, ReplyStorageError
from .webhook import ReplyValidationError, async_verify_reply, normalize_phone

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine
    from typing import Any

    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant, ServiceCall
    from homeassistant.helpers.typing import ConfigType

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)
SERVICE_SCHEMA = vol.Schema(
    {vol.Required("phone"): cv.string, vol.Required("message"): cv.string}
)
START_SCHEMA = vol.Schema({vol.Required("phone"): cv.string})
MISSING_FIELDS_ERROR = "Phone and message are required"
SEND_ERROR = "Unable to send SMS via Textbelt"
PLATFORMS = [Platform.SENSOR, Platform.NOTIFY]


def _raise_action_error(message: str) -> NoReturn:
    raise HomeAssistantError(message)


def _validate_api_key(api_key: str | None) -> str:
    if not api_key or not isinstance(api_key, str):
        msg = "API key must be provided as a string in the integration configuration."
        raise ValueError(msg)
    return api_key


def _reply_webhook_url(
    hass: HomeAssistant, webhook_id: str = WEBHOOK_ID, *, native: bool = False
) -> str | None:
    """Validate native callback shape; preserve optional legacy outbound URLs."""
    if native:
        base_url = callback_base_url(hass.config.external_url)
    else:
        try:
            base_url = get_url(hass, allow_internal=False)
        except NoURLAvailableError:
            return None
    return f"{base_url.rstrip('/')}/api/webhook/{webhook_id}"


async def async_setup(hass: HomeAssistant, _: ConfigType) -> bool:
    """Initialize integration data for config-entry setup."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Add disabled native defaults and stable identity without an opt-in upgrade."""
    if entry.version > CONFIG_VERSION:
        return False
    if entry.version == 1:
        data = dict(entry.data)
        data.setdefault(CONF_WEBHOOK_ID, async_generate_id())
        options = dict(entry.options)
        options.update(
            {
                "assist_enabled": False,
                "pipeline_id": None,
                "authorized_senders": [],
                "conversation_timeout": 1800,
            }
        )
        hass.config_entries.async_update_entry(
            entry, data=data, options=options, version=CONFIG_VERSION
        )
    return entry.version == CONFIG_VERSION


@dataclass
class TextbeltRuntimeData:
    """Own all sends and metadata settlement for one config entry."""

    client: TextbeltApiClient
    coordinator: TextbeltStatusCoordinator
    quota_coordinator: TextbeltQuotaCoordinator
    sender: TextbeltSender
    send_lock: asyncio.Lock
    hass: HomeAssistant
    entry: ConfigEntry
    state: ReplyState
    active: bool = True
    manager: ConversationManager | None = None
    _sends: set[asyncio.Task] = field(default_factory=set)
    _aux: set[asyncio.Task] = field(default_factory=set)
    _native_sends: set[asyncio.Task] = field(default_factory=set)
    listeners: list[Callable[[], None]] = field(default_factory=list)
    _shutdown_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _closed: bool = False
    _cleanup_task: asyncio.Task | None = None
    webhook_ids: list[str] = field(default_factory=list)
    service_ids: list[str] = field(default_factory=list)
    rollback_platforms: bool = False

    def reply_url(self, *, legacy: bool = False, native: bool = False) -> str | None:
        """Generate an optional callback without coupling notify to Assist."""
        try:
            options = AssistOptions.from_mapping(self.entry.options)
        except ValueError:
            options = AssistOptions()
        try:
            return _reply_webhook_url(
                self.hass,
                WEBHOOK_ID if legacy else self.entry.data[CONF_WEBHOOK_ID],
                native=options.enabled and not legacy,
            )
        except ValueError:
            if native:
                raise
            return None

    def spawn_aux(self, coroutine: Coroutine[Any, Any, Any]) -> None:
        """Own a finite coordinator refresh through cancellation."""
        task = self.hass.async_create_background_task(
            coroutine, "Textbelt refresh", eager_start=False
        )
        self._aux.add(task)
        task.add_done_callback(self._aux.discard)

    async def async_send(  # noqa: PLR0913 -- preserve shared outbound call keywords.
        self,
        hass: HomeAssistant,
        phone: str,
        message: str,
        *,
        title: str | None = None,
        webhook_url: str | None = None,
        mode: Literal["automation", "assist"] = "automation",
        compact: bool = False,
    ) -> None:
        """Keep accepted IDs/status visible, settle persistence and never retry."""
        if not self.active:
            _raise_action_error(SEND_ERROR)
        if mode == "assist" and (
            not self.manager or not self.manager.authorized(phone)
        ):
            _raise_action_error("Native Assist sender is no longer authorized")
        if webhook_url is None:
            try:
                normalize_phone(phone)
            except ValueError:
                legacy = True
            else:
                legacy = False
            webhook_url = self.reply_url(legacy=legacy)
        task = hass.async_create_background_task(
            self._send(
                phone,
                message,
                title=title,
                webhook_url=webhook_url,
                mode=mode,
                compact=compact,
            ),
            "Textbelt SMS submission",
            eager_start=False,
        )
        self._sends.add(task)
        if mode == "assist":
            self._native_sends.add(task)
        try:
            await task
        finally:
            self._sends.discard(task)
            self._native_sends.discard(task)

    async def _send(self, phone: str, message: str, **kwargs: Any) -> None:
        try:
            if not self.active or (
                kwargs.get("mode") == "assist"
                and (not self.manager or not self.manager.authorized(phone))
            ):
                _raise_action_error("Native Assist sender is no longer authorized")
            result = await self.sender.async_send(phone, message, **kwargs)
        except MessagePreparationError as err:
            _raise_action_error(str(err))
        finally:
            # Sender cancellation publishes known accepted parts before reaching here.
            try:
                try:
                    await self.state.async_flush()
                except ReplyStorageError:
                    LOGGER.warning(
                        "Textbelt send metadata failed: metadata_not_durable"
                    )
            finally:
                if self.active:
                    self.spawn_aux(self.quota_coordinator.async_request_refresh())
        if result.outcome != "accepted":
            _raise_action_error(
                f"Textbelt SMS {result.outcome}: "
                f"{result.accepted_parts}/{result.total_parts} parts accepted"
            )

    async def async_cancel_native_sends(self) -> None:
        """Cancel native replies and greetings on live policy changes."""
        tasks = list(self._native_sends)
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._native_sends.clear()

    async def async_shutdown(self) -> None:
        """Settle owned cleanup before propagating repeated caller cancellation."""
        self.active = False
        self.sender.shutdown()
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(
                self._shutdown_owned(), name="Textbelt owned cleanup"
            )
        task = self._cleanup_task
        cancelled: asyncio.CancelledError | None = None
        while not task.done():
            try:
                await asyncio.shield(task)
            except asyncio.CancelledError as err:
                if task.cancelled():
                    raise
                cancelled = err
        task.result()
        if cancelled is not None:
            raise cancelled

    async def _shutdown_owned(self) -> None:
        """Consume all task/listener ownership and flush metadata once."""
        async with self._shutdown_lock:
            if self._closed:
                return
            for unsub in self.listeners:
                unsub()
            self.listeners.clear()
            if self.manager:
                await self.manager.async_shutdown()
            tasks = list(self._sends | self._aux)
            for task in tasks:
                task.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
            self._sends.clear()
            self._aux.clear()
            try:
                await self.state.async_flush()
            except ReplyStorageError:
                LOGGER.warning(
                    "Textbelt shutdown metadata failed: metadata_not_durable"
                )
            await self.coordinator.async_shutdown()
            await self.quota_coordinator.async_shutdown()
            if self.rollback_platforms:
                try:
                    await self.hass.config_entries.async_unload_platforms(
                        self.entry, PLATFORMS
                    )
                except Exception:  # noqa: BLE001 -- finish ownership after failed setup.
                    LOGGER.warning("Textbelt setup rollback failed: platform_unload")
            for service in self.service_ids:
                self.hass.services.async_remove(DOMAIN, service)
            self.service_ids.clear()
            for identity in self.webhook_ids:
                async_unregister_webhook(self.hass, identity)
            self.webhook_ids.clear()
            self.entry.runtime_data = None
            self._closed = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # noqa: C901, PLR0915 -- entry registration/rollback ownership.
    """Create owned runtime and register both signed endpoints with rollback."""
    try:
        api_key = _validate_api_key(entry.data.get(CONF_API_KEY))
        options = AssistOptions.from_mapping(entry.options)
        if entry.version > CONFIG_VERSION:
            return False
        if CONF_WEBHOOK_ID not in entry.data:
            hass.config_entries.async_update_entry(
                entry, data={**entry.data, CONF_WEBHOOK_ID: async_generate_id()}
            )
        if options.enabled:
            if not options.authorized_senders or not reply_key_usable(api_key):
                return False
            callback_base_url(hass.config.external_url)
            if not await async_ensure_assist_pipeline(hass):
                return False
            async_resolve_pipeline(hass, options.pipeline_id)
        client = TextbeltApiClient(api_key, async_get_clientsession(hass))
    except (ValueError, HomeAssistantError, KeyError):
        LOGGER.warning("Textbelt setup failed: invalid_configuration")
        return False
    coordinator = TextbeltStatusCoordinator(hass, client)
    quota_coordinator = TextbeltQuotaCoordinator(hass, client, entry)
    state = ReplyState(hass, entry.entry_id)

    def publish_result(result: SendResult, phone: str, message: str) -> None:
        try:
            state.record_send_result(result, phone)
        except ValueError:
            # Legacy dynamic phone acceptance remains outbound/events-only.
            LOGGER.debug("Textbelt correlation omitted: noncanonical_recipient")
        if runtime.active:
            coordinator.set_last_batch(result, phone, message)
            if result.text_ids:
                runtime.spawn_aux(coordinator.async_request_refresh())

    sender = TextbeltSender(client, on_result=publish_result)
    runtime = TextbeltRuntimeData(
        client, coordinator, quota_coordinator, sender, sender.lock, hass, entry, state
    )
    manager = runtime.manager = ConversationManager(hass, entry, state, runtime)
    registered = runtime.webhook_ids
    platform_attempted = False

    async def handle_reply(
        _hass: HomeAssistant, identity: str, request: web.Request
    ) -> web.Response:
        if identity not in registered:
            return web.Response(status=404)
        if not reply_key_usable(api_key):
            return web.Response(status=403)
        if not runtime.active:
            return web.Response(status=503)
        try:
            reply = await async_verify_reply(
                request, api_key=api_key, entry_id=entry.entry_id
            )
        except ReplyValidationError as err:
            return web.Response(status=err.status)
        status = await manager.async_handle_reply(reply, legacy=identity == WEBHOOK_ID)
        return web.Response(status=status)

    async def handle_send_sms(call: ServiceCall) -> None:
        phone, message = call.data.get("phone"), call.data.get("message")
        if not phone or not message:
            _raise_action_error(MISSING_FIELDS_ERROR)
        try:
            normalize_phone(phone)
        except ValueError:
            legacy = True
        else:
            legacy = False
        await runtime.async_send(
            hass, phone, message, webhook_url=runtime.reply_url(legacy=legacy)
        )

    async def handle_start(call: ServiceCall) -> None:
        try:
            phone = normalize_phone(call.data.get("phone"))
            if not manager.authorized(phone):
                _raise_action_error(
                    "Native Assist is disabled or this sender is not authorized"
                )
            url = runtime.reply_url(native=True)
        except ValueError:
            _raise_action_error(
                "Configure an authorized international phone and public HTTPS callback"
            )
        await runtime.async_send(
            hass, phone, GREETING, mode="assist", compact=True, webhook_url=url
        )

    async def policy_changed(_hass: HomeAssistant, _entry: ConfigEntry) -> None:
        await manager.async_policy_changed()
        await runtime.async_cancel_native_sends()
        if runtime.active:
            await hass.config_entries.async_reload(entry.entry_id)

    async def stop(_event: Any) -> None:
        await runtime.async_shutdown()

    try:
        await state.async_load()
        entry.runtime_data = runtime
        for identity in (entry.data[CONF_WEBHOOK_ID], WEBHOOK_ID):
            async_register_webhook(
                hass,
                DOMAIN,
                "Textbelt SMS Reply Webhook",
                identity,
                handle_reply,
                allowed_methods=["POST"],
                local_only=False,
            )
            registered.append(identity)
        hass.services.async_register(
            DOMAIN, SERVICE_SEND_SMS, handle_send_sms, schema=SERVICE_SCHEMA
        )
        runtime.service_ids.append(SERVICE_SEND_SMS)
        hass.services.async_register(
            DOMAIN, SERVICE_START_CONVERSATION, handle_start, schema=START_SCHEMA
        )
        runtime.service_ids.append(SERVICE_START_CONVERSATION)
        runtime.listeners.append(entry.add_update_listener(policy_changed))
        runtime.listeners.append(hass.bus.async_listen(EVENT_HOMEASSISTANT_STOP, stop))
        manager.start()
        platform_attempted = True
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        runtime.rollback_platforms = platform_attempted
        await runtime.async_shutdown()
        raise
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Keep outbound runtime operational when platform unload fails."""
    if not await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        return False
    if entry.runtime_data:
        await entry.runtime_data.async_shutdown()
    return True


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Recreate runtime only after complete platform unload."""
    if await async_unload_entry(hass, entry):
        await async_setup_entry(hass, entry)
