"""Tests for the integration setup helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from custom_components.textbelt_sms import _validate_api_key, async_setup
from custom_components.textbelt_sms.const import DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
else:  # pragma: no cover - only used for type checking
    HomeAssistant = Any


def test_validate_api_key_accepts_string() -> None:
    """Ensure a valid string key is returned unchanged."""
    assert _validate_api_key("abc123") == "abc123"


@pytest.mark.parametrize("invalid", [None, 123, ""])
def test_validate_api_key_requires_non_empty_string(invalid: Any) -> None:
    """Invalid API keys should raise a ValueError."""
    with pytest.raises(ValueError, match="API key must be provided"):
        _validate_api_key(invalid)


@pytest.mark.asyncio
async def test_async_setup_initialises_domain_storage(hass: HomeAssistant) -> None:
    """async_setup should prepare hass.data for the integration namespace."""
    hass.data.pop(DOMAIN, None)

    result = await async_setup(hass, {})

    assert result is True
    assert DOMAIN in hass.data
    assert hass.data[DOMAIN] == {}
