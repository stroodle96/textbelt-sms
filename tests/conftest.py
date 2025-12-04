"""Global pytest fixtures for Textbelt SMS integration tests."""

from __future__ import annotations

import pytest
from homeassistant.const import CONF_API_KEY
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.textbelt_sms.const import DOMAIN

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(name="config_entry")
def config_entry_fixture() -> MockConfigEntry:
    """Provide a default mocked config entry for Textbelt SMS."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "test-key"},
        title="Textbelt SMS",
    )
