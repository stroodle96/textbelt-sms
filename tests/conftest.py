"""Pytest fixtures for the Textbelt SMS integration."""

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(request: pytest.FixtureRequest) -> None:
    """Allow Home Assistant to load the custom integration under test."""
    request.getfixturevalue("enable_custom_integrations")


@pytest.fixture
def api_base_url(monkeypatch: pytest.MonkeyPatch) -> str:
    """Point the API client at the deterministic test server."""
    url = "http://textbelt.test"
    monkeypatch.setenv("TEXTBELT_SMS_API_BASE_URL", url)
    return url
# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
