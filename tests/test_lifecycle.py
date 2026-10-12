# Copyright (c) 2026 Textbelt SMS contributors
"""Lifecycle, migration and signed endpoint integration behavior."""

import asyncio
import hashlib
import hmac
import json
import time
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from aiohttp.test_utils import make_mocked_request

# Literal HTTP status/cap values are behavioral contracts.
# ruff: noqa: PLR2004, SLF001
from homeassistant.core import HomeAssistant, HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components import textbelt_sms as integration
from custom_components.textbelt_sms import conversation
from custom_components.textbelt_sms.assist import AssistResult
from custom_components.textbelt_sms.const import DOMAIN
from custom_components.textbelt_sms.sender import PartResult, SendResult
from custom_components.textbelt_sms.state import ReplyState
from tests.test_conversation import PHONE, Body


@pytest.fixture
async def entry(hass: Any, monkeypatch: Any) -> Any:
    """Create a runtime with mocked platform setup and owned teardown."""
    obj = MockConfigEntry(domain=DOMAIN, entry_id="entry", data={"api_key": "secret"})
    obj.add_to_hass(hass)
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())
    monkeypatch.setattr(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
    )
    await integration.async_setup_entry(hass, obj)
    yield obj
    if obj.runtime_data and not await integration.async_unload_entry(hass, obj):
        await obj.runtime_data.async_shutdown()


async def test_version1_migration_disabled_identity(hass: Any) -> None:
    """Version1 migration disabled identity."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        version=1,
        data={"api_key": "secret"},
        options={"notification_recipients": [PHONE], "custom": 42},
    )
    entry.add_to_hass(hass)
    assert await integration.async_migrate_entry(hass, entry)
    assert entry.version == 2
    assert not entry.options["assist_enabled"]
    assert entry.options["custom"] == 42
    assert entry.options["notification_recipients"] == [PHONE]
    identity = entry.data["webhook_id"]
    assert len(identity) == 64
    assert await integration.async_migrate_entry(hass, entry)
    assert entry.data["webhook_id"] == identity


async def test_future_version_refused(hass: Any) -> None:
    """Future version refused."""
    entry = MockConfigEntry(domain=DOMAIN, version=3, data={"api_key": "secret"})
    assert not await integration.async_migrate_entry(hass, entry)


async def test_entry_owns_both_endpoints_and_services(hass: Any, entry: Any) -> None:
    """Entry owns both endpoints and services."""
    assert hass.services.has_service(DOMAIN, "start_conversation")
    assert entry.data["webhook_id"] != "textbelt_sms_reply"
    await integration.async_unload_entry(hass, entry)
    assert not hass.services.has_service(DOMAIN, "send_sms")
    assert not hass.services.has_service(DOMAIN, "start_conversation")


async def test_failed_unload_retains_outbound_but_live_disable_blocks_native(
    hass: Any, entry: Any, monkeypatch: Any
) -> None:
    """Failed unload retains outbound but live disable blocks native."""
    runtime = entry.runtime_data
    monkeypatch.setattr(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False)
    )
    assert not await integration.async_unload_entry(hass, entry)
    assert runtime.active
    assert hass.services.has_service(DOMAIN, "send_sms")
    assert not runtime.manager.authorized(PHONE)
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "start_conversation", {"phone": PHONE}, blocking=True
        )


@pytest.mark.parametrize("key", ["textbelt", "secret_test"])
async def test_public_key_cannot_authenticate_legacy(
    hass: Any, monkeypatch: Any, key: str
) -> None:
    """Public key cannot authenticate legacy."""
    handlers = {}

    def register(
        _hass: Any,
        _domain: Any,
        _name: Any,
        identity: Any,
        handler: Any,
        **_kwargs: Any,
    ) -> None:
        handlers[identity] = handler

    monkeypatch.setattr(integration, "async_register_webhook", register)
    monkeypatch.setattr(integration, "async_unregister_webhook", lambda *_: None)
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())
    monkeypatch.setattr(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
    )
    entry = MockConfigEntry(domain=DOMAIN, data={"api_key": key})
    entry.add_to_hass(hass)
    await integration.async_setup_entry(hass, entry)
    # A caller can compute HMAC for this publicly known key; reject before parsing.
    response = await handlers["textbelt_sms_reply"](
        hass, "textbelt_sms_reply", signed_request(key=key)
    )
    assert response.status == 403
    native_id = entry.data["webhook_id"]
    response = await handlers[native_id](hass, native_id, signed_request(key=key))
    assert response.status == 403
    await integration.async_unload_entry(hass, entry)


def signed_request(
    text: str = "hello", *, key: str = "secret", text_id: str = "out"
) -> Any:
    """Sign fixture bytes independently of the production verifier."""
    raw = json.dumps({"textId": text_id, "fromNumber": PHONE, "text": text}).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(
        key.encode(), timestamp.encode() + raw, hashlib.sha256
    ).hexdigest()
    return make_mocked_request(
        "POST",
        "/",
        headers={
            "Content-Type": "application/json",
            "X-textbelt-timestamp": timestamp,
            "X-textbelt-signature": signature,
        },
        payload=Body(raw),
    )


def handler(hass: HomeAssistant, entry: Any, *, legacy: bool = False) -> Any:
    """Read the actual registered endpoint, without bypassing signature verification."""
    identity = "textbelt_sms_reply" if legacy else entry.data["webhook_id"]
    return hass.data["webhook"][identity].handler, identity


async def test_signed_legacy_random_events_and_unsigned_rejection(
    hass: Any, entry: Any
) -> None:
    """Require signatures and correlation on registered endpoints."""
    events = []
    hass.bus.async_listen("textbelt_sms_reply", lambda event: events.append(event.data))
    callback, identity = handler(hass, entry, legacy=True)
    assert (
        await callback(hass, identity, signed_request("legacy", text_id="historic"))
    ).status == 200
    await hass.async_block_till_done()
    assert events == [{"textId": "historic", "fromNumber": PHONE, "text": "legacy"}]
    unsigned = make_mocked_request(
        "POST", "/", headers={"Content-Type": "application/json"}, payload=Body(b"{}")
    )
    assert (await callback(hass, identity, unsigned)).status == 401
    native, native_id = handler(hass, entry)
    assert (await native(hass, native_id, signed_request())).status == 403
    assert (await native(hass, "unknown", signed_request())).status == 404

    entry.runtime_data.state.record_send_result(
        SendResult((PartResult(1, "out", "accepted"),), 1, "accepted"), PHONE
    )
    assert (await native(hass, native_id, signed_request("custom route"))).status == 200
    await hass.async_block_till_done()
    assert events[-1]["text"] == "custom route"
    assert not entry.runtime_data.manager.sessions
    assert (await callback(hass, identity, signed_request(" STOP "))).status == 200
    assert len(events) == 2


async def enable_native(hass: Any, entry: Any, monkeypatch: Any) -> None:
    """Apply a live native policy while retaining direct-test runtime ownership."""
    hass.config.external_url = "https://ha.example.com"
    monkeypatch.setattr(
        hass.config_entries, "async_reload", AsyncMock(return_value=False)
    )
    monkeypatch.setattr(
        conversation, "async_resolve_pipeline", lambda *_: SimpleNamespace(id="first")
    )
    hass.config_entries.async_update_entry(
        entry, options={"assist_enabled": True, "authorized_senders": [PHONE]}
    )
    await hass.async_block_till_done()
    entry.runtime_data.client.async_get_quota = AsyncMock(return_value=10)
    entry.runtime_data.client.async_get_status = AsyncMock(return_value="PENDING")


async def test_start_greeting_restriction_ids_and_canonical_callback(
    hass: Any, entry: Any, monkeypatch: Any
) -> None:
    """Send restricted greetings with durable IDs and generated callbacks."""
    await enable_native(hass, entry, monkeypatch)
    runtime = entry.runtime_data
    runtime.client.async_send_sms = AsyncMock(
        return_value={"success": True, "textId": "greeting"}
    )
    await hass.services.async_call(
        DOMAIN, "start_conversation", {"phone": PHONE}, blocking=True
    )
    assert runtime.state.correlates("greeting", PHONE)
    restored = ReplyState(hass, entry.entry_id)
    await restored.async_load()
    assert restored.correlates("greeting", PHONE)
    posted = runtime.client.async_send_sms.call_args.args
    assert posted[0] == PHONE
    assert "Home Assistant" in posted[1]
    assert "/new" in posted[1]
    assert posted[2].endswith(entry.data["webhook_id"])
    assert runtime.sender.last_result.total_parts == 1
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "start_conversation", {"phone": "+15551234568"}, blocking=True
        )
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "start_conversation", {"phone": "5551234567"}, blocking=True
        )
    assert runtime.client.async_send_sms.await_count == 1


async def test_dynamic_legacy_phone_preserves_signed_events_callback(
    hass: Any, entry: Any, monkeypatch: Any
) -> None:
    """Retain signed events for legacy destinations without guessing country."""
    monkeypatch.setattr(
        integration, "get_url", lambda *_args, **_kwargs: "https://ha.example.com"
    )
    runtime = entry.runtime_data
    runtime.client.async_send_sms = AsyncMock(
        return_value={"success": True, "textId": "legacy-send"}
    )
    runtime.client.async_get_quota = AsyncMock(return_value=10)
    runtime.client.async_get_status = AsyncMock(return_value="PENDING")
    await hass.services.async_call(
        DOMAIN, "send_sms", {"phone": "5551234567", "message": "hello"}, blocking=True
    )
    assert runtime.client.async_send_sms.call_args.args[2].endswith(
        "textbelt_sms_reply"
    )
    assert runtime.sender.last_result.outcome == "accepted"
    assert not runtime.state.correlates("legacy-send", PHONE)
    await hass.services.async_call(
        DOMAIN, "send_sms", {"phone": PHONE, "message": "hello"}, blocking=True
    )
    assert runtime.client.async_send_sms.call_args.args[2].endswith(
        entry.data["webhook_id"]
    )
    assert runtime.state.correlates("legacy-send", PHONE)


@pytest.mark.parametrize(
    "options",
    [{"assist_enabled": False}, {"assist_enabled": True, "authorized_senders": []}],
)
async def test_policy_listener_cancels_inflight_on_failed_unload(
    hass: Any, entry: Any, monkeypatch: Any, options: Any
) -> None:
    """Cancel native work when options change during a failed unload."""
    await enable_native(hass, entry, monkeypatch)
    runtime = entry.runtime_data

    runtime.state.record_send_result(
        SendResult((PartResult(1, "out", "accepted"),), 1, "accepted"), PHONE
    )
    started, cancelled = asyncio.Event(), asyncio.Event()

    async def run(*_args: Any, **_kwargs: Any) -> AssistResult:
        started.set()
        try:
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            cancelled.set()
            raise
        return AssistResult("first", "id", "unreachable", None)

    monkeypatch.setattr(conversation, "async_run_assist", run)
    runtime.client.async_send_sms = AsyncMock()
    native, identity = handler(hass, entry)
    assert (await native(hass, identity, signed_request())).status == 200
    await asyncio.wait_for(started.wait(), 2)
    monkeypatch.setattr(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=False)
    )

    async def reload_entry(_identity: str) -> None:
        await integration.async_reload_entry(hass, entry)

    monkeypatch.setattr(
        hass.config_entries, "async_reload", AsyncMock(side_effect=reload_entry)
    )
    hass.config_entries.async_update_entry(entry, options=options)
    await hass.async_block_till_done()
    assert cancelled.is_set()
    hass.config_entries.async_unload_platforms.assert_awaited_once()
    assert runtime.active
    assert entry.runtime_data is runtime
    assert not runtime.manager.sessions
    runtime.client.async_send_sms.assert_not_awaited()
    assert hass.services.has_service(DOMAIN, "send_sms")
    assert not runtime.manager.authorized(PHONE)


async def test_unload_settles_known_ids_and_cancels_all_owned_tasks(
    hass: Any, entry: Any
) -> None:
    """Cancellation retains accepted parts and unload awaits final durable metadata."""
    runtime = entry.runtime_data
    started = asyncio.Event()

    async def post(*_args: Any) -> dict:
        if runtime.client.async_send_sms.await_count == 1:
            return {"success": True, "textId": "accepted-first"}
        started.set()
        await asyncio.Event().wait()
        return {"success": True, "textId": "unreachable"}

    runtime.client.async_send_sms = AsyncMock(side_effect=post)
    runtime.client.async_get_status = AsyncMock(return_value="PENDING")
    runtime.client.async_get_quota = AsyncMock(return_value=10)
    task = asyncio.create_task(runtime.async_send(hass, PHONE, "a" * 400))
    await asyncio.wait_for(started.wait(), 2)
    await integration.async_unload_entry(hass, entry)
    with pytest.raises(asyncio.CancelledError):
        await task
    assert runtime.sender.last_result.text_ids == ("accepted-first",)
    assert runtime.sender.last_result.outcome == "unknown"
    restored = ReplyState(hass, entry.entry_id)
    await restored.async_load()
    assert restored.correlates("accepted-first", PHONE)
    assert not runtime._sends
    assert not runtime._aux
    assert not runtime.listeners
    assert runtime.manager._maintenance is None
    assert not runtime.manager._workers
    assert not entry.update_listeners
    with pytest.raises(HomeAssistantError):
        await runtime.async_send(hass, PHONE, "stale")


async def test_full_unload_waits_for_flush_despite_repeated_caller_cancellation(
    hass: Any, entry: Any, monkeypatch: Any
) -> None:
    """Finish unload ownership before propagating cancellation."""
    runtime = entry.runtime_data
    entered, release = asyncio.Event(), asyncio.Event()
    original = runtime.state.async_flush

    async def flush() -> None:
        entered.set()
        await release.wait()
        await original()

    monkeypatch.setattr(runtime.state, "async_flush", flush)
    shutdown = asyncio.create_task(integration.async_unload_entry(hass, entry))
    await asyncio.wait_for(entered.wait(), 2)
    shutdown.cancel()
    await asyncio.sleep(0)
    shutdown.cancel()
    await asyncio.sleep(0)
    pending = not shutdown.done()
    release.set()
    assert pending
    with pytest.raises(asyncio.CancelledError):
        await shutdown
    assert runtime._closed
    assert not runtime.listeners
    assert not runtime._sends
    assert not runtime._aux
    assert runtime.manager._maintenance is None
    assert entry.runtime_data is None
    assert not hass.services.has_service(DOMAIN, "send_sms")
    assert not hass.services.has_service(DOMAIN, "start_conversation")
    assert entry.data["webhook_id"] not in hass.data["webhook"]
    assert "textbelt_sms_reply" not in hass.data["webhook"]
    assert not entry.update_listeners


async def test_notify_style_outbound_survives_lost_native_callback(
    hass: Any, entry: Any, monkeypatch: Any
) -> None:
    """Keep outbound notifications usable without a native callback."""
    await enable_native(hass, entry, monkeypatch)
    hass.config.external_url = None
    runtime = entry.runtime_data
    runtime.client.async_send_sms = AsyncMock(
        return_value={"success": True, "textId": "outbound-only"}
    )
    runtime.client.async_get_quota = AsyncMock(return_value=10)
    runtime.client.async_get_status = AsyncMock(return_value="PENDING")
    await runtime.async_send(hass, PHONE, "notification", title="Alert")
    assert runtime.sender.last_result.outcome == "accepted"
    assert runtime.client.async_send_sms.call_args.args[2] is None
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, "start_conversation", {"phone": PHONE}, blocking=True
        )


async def test_failed_setup_cleanup_settles_before_repeated_cancellation(
    hass: Any, monkeypatch: Any
) -> None:
    """Finish failed-setup cleanup before propagating cancellation."""
    entry = MockConfigEntry(
        domain=DOMAIN, entry_id="failed-entry", data={"api_key": "secret"}
    )
    entry.add_to_hass(hass)
    entered, release = asyncio.Event(), asyncio.Event()
    original = ReplyState.async_flush

    async def flush(state: Any) -> None:
        entered.set()
        await release.wait()
        await original(state)

    monkeypatch.setattr(ReplyState, "async_flush", flush)
    monkeypatch.setattr(
        hass.config_entries,
        "async_forward_entry_setups",
        AsyncMock(side_effect=RuntimeError("platform failed")),
    )
    monkeypatch.setattr(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
    )
    setup = asyncio.create_task(integration.async_setup_entry(hass, entry))
    await asyncio.wait_for(entered.wait(), 2)
    runtime = entry.runtime_data
    setup.cancel()
    await asyncio.sleep(0)
    setup.cancel()
    await asyncio.sleep(0)
    pending = not setup.done()
    release.set()
    assert pending
    with pytest.raises(asyncio.CancelledError):
        await setup
    assert runtime._closed
    assert entry.runtime_data is None
    hass.config_entries.async_unload_platforms.assert_awaited_once()
    assert not runtime.listeners
    assert not runtime._sends
    assert not runtime._aux
    assert not hass.services.has_service(DOMAIN, "send_sms")
    assert not hass.services.has_service(DOMAIN, "start_conversation")
    assert entry.data["webhook_id"] not in hass.data["webhook"]
    assert "textbelt_sms_reply" not in hass.data["webhook"]


async def test_live_policy_cancels_greeting_waiting_for_shared_sender(
    hass: Any, entry: Any, monkeypatch: Any
) -> None:
    """Revoke a queued greeting before it can post through the shared sender."""
    await enable_native(hass, entry, monkeypatch)
    runtime = entry.runtime_data
    runtime.client.async_send_sms = AsyncMock()
    await runtime.sender.lock.acquire()
    greeting = asyncio.create_task(
        hass.services.async_call(
            DOMAIN, "start_conversation", {"phone": PHONE}, blocking=True
        )
    )
    try:
        for _n in range(4):
            await asyncio.sleep(0)
        assert runtime._native_sends
        hass.config_entries.async_update_entry(entry, options={"assist_enabled": False})
        await hass.async_block_till_done()
        with pytest.raises(asyncio.CancelledError):
            await greeting
        runtime.client.async_send_sms.assert_not_awaited()
        assert not runtime._native_sends
    finally:
        runtime.sender.lock.release()
