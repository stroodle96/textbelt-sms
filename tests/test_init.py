# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Tests for Home Assistant setup and service behavior."""

import asyncio
from types import SimpleNamespace
from typing import Self
from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms import (
    SERVICE_SEND_SMS,
    WEBHOOK_ID,
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.textbelt_sms.const import DOMAIN, EVENT_REPLY
from custom_components.textbelt_sms.sensor import LastMessage, MessageStatus


class _Response:
    status = 200

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def json(self) -> dict[str, bool | int]:
        return {"success": True, "textId": 123}


class _FailureResponse(_Response):
    status = 500


class _Session:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str]]] = []

    def post(self, url: str, *, data: dict[str, str]) -> _Response:
        self.calls.append((url, data))
        return _Response()


class _FailureSession(_Session):
    def post(self, url: str, *, data: dict[str, str]) -> _Response:
        self.calls.append((url, data))
        return _FailureResponse()


def _entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="Textbelt SMS",
        data={CONF_API_KEY: "test-key"},
        entry_id="test-entry",
    )


@pytest.fixture(autouse=True)
def mock_platform_forwarding(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Keep direct setup tests focused on integration lifecycle callbacks."""
    monkeypatch.setattr(hass.config_entries, "async_forward_entry_setups", AsyncMock())
    monkeypatch.setattr(
        hass.config_entries, "async_unload_platforms", AsyncMock(return_value=True)
    )


async def test_setup_registers_service_and_stores_client(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, api_base_url: str
) -> None:
    """Set up the integration and exercise its public service."""
    session = _Session()
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: session
    )
    entry = _entry()

    assert await async_setup_entry(hass, entry)
    assert hass.services.has_service(DOMAIN, SERVICE_SEND_SMS)
    assert entry.runtime_data is not None

    service_info = hass.services.async_services()[DOMAIN][SERVICE_SEND_SMS]
    with pytest.raises(vol.Invalid):
        service_info.schema({})

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SEND_SMS,
        {"phone": "+15551234567", "message": "hello"},
        blocking=True,
    )
    assert session.calls == [
        (
            f"{api_base_url}/text",
            {
                "phone": "+15551234567",
                "message": "hello",
                "key": "test-key",
            },
        )
    ]
    assert entry.runtime_data.coordinator.data == LastMessage(
        text_id="123",
        phone="+15551234567",
        message="hello",
        status=MessageStatus.PENDING,
    )
    await entry.runtime_data.coordinator.async_shutdown()


async def test_service_rejects_empty_values(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject service calls with empty required fields."""
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: _Session()
    )
    entry = _entry()
    await async_setup_entry(hass, entry)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, SERVICE_SEND_SMS, {"phone": "+1", "message": ""}, blocking=True
        )
    await entry.runtime_data.coordinator.async_shutdown()


async def test_service_sends_reply_webhook_field(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Send requests use Textbelt's replyWebhookUrl field exactly."""
    session = _Session()
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: session
    )
    monkeypatch.setattr(
        hass.config,
        "api",
        SimpleNamespace(base_url="https://ha.test/"),
        raising=False,
    )
    entry = _entry()
    await async_setup_entry(hass, entry)

    await hass.services.async_call(
        DOMAIN,
        SERVICE_SEND_SMS,
        {"phone": "+1", "message": "hello"},
        blocking=True,
    )

    assert session.calls == [
        (
            "http://textbelt.test/text",
            {
                "phone": "+1",
                "message": "hello",
                "key": "test-key",
                "replyWebhookUrl": "https://ha.test/api/webhook/textbelt_sms_reply",
            },
        )
    ]
    await entry.runtime_data.coordinator.async_shutdown()


async def test_overlapping_sends_commit_in_call_order(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Concurrent sends serialize so the final metadata is deterministic."""
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: _Session()
    )
    entry = _entry()
    await async_setup_entry(hass, entry)
    first_started = asyncio.Event()
    release_first = asyncio.Event()
    calls: list[str] = []

    async def send(_phone: str, message: str, _webhook: str | None = None) -> dict:
        calls.append(message)
        if message == "first":
            first_started.set()
            await release_first.wait()
            return {"success": True, "textId": 1}
        return {"success": True, "textId": 2}

    entry.runtime_data.client.async_send_sms = send
    first = asyncio.create_task(
        hass.services.async_call(
            DOMAIN,
            SERVICE_SEND_SMS,
            {"phone": "+1", "message": "first"},
            blocking=True,
        )
    )
    await first_started.wait()
    second = asyncio.create_task(
        hass.services.async_call(
            DOMAIN,
            SERVICE_SEND_SMS,
            {"phone": "+2", "message": "second"},
            blocking=True,
        )
    )
    await asyncio.sleep(0)
    assert not second.done()
    release_first.set()
    await asyncio.gather(first, second)

    assert calls == ["first", "second"]
    assert entry.runtime_data.coordinator.data == LastMessage(
        "2", "+2", "second", MessageStatus.PENDING
    )
    await entry.runtime_data.coordinator.async_shutdown()


async def test_setup_rolls_back_when_platform_forwarding_fails(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failed platform setup removes service, webhook, and runtime state."""
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: _Session()
    )
    monkeypatch.setattr(
        hass.config_entries,
        "async_forward_entry_setups",
        AsyncMock(side_effect=RuntimeError("platform failed")),
    )
    unregister = MagicMock()
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_unregister_webhook", unregister
    )
    entry = _entry()

    with pytest.raises(RuntimeError, match="platform failed"):
        await async_setup_entry(hass, entry)

    assert entry.runtime_data is None
    assert not hass.services.has_service(DOMAIN, SERVICE_SEND_SMS)
    unregister.assert_called_once_with(hass, WEBHOOK_ID)


async def test_reload_does_not_setup_after_failed_unload(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reload stops when platform unloading reports failure."""
    setup = AsyncMock()
    monkeypatch.setattr("custom_components.textbelt_sms.async_setup_entry", setup)
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_unload_entry",
        AsyncMock(return_value=False),
    )

    await async_reload_entry(hass, _entry())

    setup.assert_not_awaited()


async def test_service_exposes_textbelt_failure_as_homeassistant_error(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Translate a Textbelt failure into a Home Assistant error."""
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession",
        lambda _: _FailureSession(),
    )
    entry = _entry()
    await async_setup_entry(hass, entry)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, SERVICE_SEND_SMS, {"phone": "+1", "message": "hello"}, blocking=True
        )
    await entry.runtime_data.coordinator.async_shutdown()


async def test_unload_removes_service_webhook_and_client(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unload the entry and remove all global runtime registrations."""
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: _Session()
    )
    unregister = MagicMock()
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_unregister_webhook", unregister
    )
    entry = _entry()
    await async_setup_entry(hass, entry)

    assert await async_unload_entry(hass, entry)
    assert not hass.services.has_service(DOMAIN, SERVICE_SEND_SMS)
    assert entry.runtime_data is None
    unregister.assert_called_once_with(hass, WEBHOOK_ID)


async def test_reload_replaces_service_and_client(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reload the entry and recreate its service and runtime client."""
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: _Session()
    )
    entry = _entry()
    await async_setup_entry(hass, entry)

    await async_reload_entry(hass, entry)

    assert hass.services.has_service(DOMAIN, SERVICE_SEND_SMS)
    assert entry.runtime_data is not None
    await entry.runtime_data.coordinator.async_shutdown()


async def test_reply_webhook_fires_event_without_logging_payload(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dispatch reply webhook payloads as Home Assistant events."""
    captured: dict[str, object] = {}

    def register(*args: object) -> None:
        captured["handler"] = args[-1]

    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_register_webhook", register
    )
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: _Session()
    )
    entry = _entry()
    await async_setup_entry(hass, entry)
    request = MagicMock()
    request.json = AsyncMock(return_value={"from": "+1", "text": "reply"})
    events: list[dict] = []
    hass.bus.async_listen(EVENT_REPLY, lambda event: events.append(event.data))

    await captured["handler"](hass, WEBHOOK_ID, request)
    await hass.async_block_till_done()

    assert events == [{"from": "+1", "text": "reply"}]
    await entry.runtime_data.coordinator.async_shutdown()
