"""Tests for Home Assistant setup and service behavior."""

from unittest.mock import AsyncMock, MagicMock

import pytest
import voluptuous as vol
from homeassistant.const import CONF_API_KEY
from homeassistant.core import HomeAssistant, HomeAssistantError
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms import (
    SERVICE_SEND_SMS,
    WEBHOOK_ID,
    async_setup_entry,
    async_reload_entry,
    async_unload_entry,
)
from custom_components.textbelt_sms.const import DOMAIN, EVENT_REPLY


class _Response:
    status = 200

    async def __aenter__(self) -> "_Response":
        return self

    async def __aexit__(self, *_args: object) -> None:
        return None

    async def json(self) -> dict[str, bool]:
        return {"success": True}


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


async def test_setup_registers_service_and_stores_client(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch, api_base_url: str
) -> None:
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


async def test_service_rejects_empty_values(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: _Session()
    )
    entry = _entry()
    await async_setup_entry(hass, entry)

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, SERVICE_SEND_SMS, {"phone": "+1", "message": ""}, blocking=True
        )


async def test_service_exposes_textbelt_failure_as_homeassistant_error(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession",
        lambda _: _FailureSession(),
    )
    await async_setup_entry(hass, _entry())

    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            DOMAIN, SERVICE_SEND_SMS, {"phone": "+1", "message": "hello"}, blocking=True
        )


async def test_unload_removes_service_webhook_and_client(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: _Session()
    )
    entry = _entry()
    await async_setup_entry(hass, entry)

    assert await async_unload_entry(hass, entry)
    assert not hass.services.has_service(DOMAIN, SERVICE_SEND_SMS)
    assert entry.runtime_data is None


async def test_reload_replaces_service_and_client(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "custom_components.textbelt_sms.async_get_clientsession", lambda _: _Session()
    )
    entry = _entry()
    await async_setup_entry(hass, entry)

    await async_reload_entry(hass, entry)

    assert hass.services.has_service(DOMAIN, SERVICE_SEND_SMS)
    assert entry.runtime_data is not None


async def test_reply_webhook_fires_event_without_logging_payload(
    hass: HomeAssistant, monkeypatch: pytest.MonkeyPatch
) -> None:
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
