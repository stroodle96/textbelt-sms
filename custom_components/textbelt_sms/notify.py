# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Standard Home Assistant notification targets for configured recipients."""

from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING

from homeassistant.components.notify import NotifyEntity, NotifyEntityFeature

from .recipients import CONF_NOTIFICATION_RECIPIENTS

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback

    from . import TextbeltRuntimeData


async def async_setup_entry(
    _hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Create one stable target per normalized configured destination."""
    async_add_entities(
        TextbeltNotification(entry.runtime_data, entry.entry_id, phone)
        for phone in dict.fromkeys(entry.options.get(CONF_NOTIFICATION_RECIPIENTS, []))
    )


class TextbeltNotification(NotifyEntity):
    """Send using the integration-owned sender and its outcome handling."""

    _attr_supported_features = NotifyEntityFeature.TITLE

    def __init__(self, runtime: TextbeltRuntimeData, entry_id: str, phone: str) -> None:
        """Keep raw destinations out of registry identity and default names."""
        self._runtime = runtime
        self._phone = phone
        digest = sha256(phone.encode("ascii")).hexdigest()
        self._attr_unique_id = f"{entry_id}_notification_{digest}"
        self._attr_name = f"Textbelt SMS ending {phone[-4:]}"
        self.entity_id = f"notify.textbelt_sms_{digest}"

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Return successfully only when every part was accepted."""
        await self._runtime.async_send(self.hass, self._phone, message, title=title)
