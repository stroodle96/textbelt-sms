"""Pytest configuration for Textbelt SMS integration tests."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms.const import CONF_API_KEY, DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Create a mock config entry for the integration."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-api-key"},
        entry_id="test-entry",
    )
