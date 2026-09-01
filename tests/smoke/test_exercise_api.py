"""Tests for the real Home Assistant smoke API exercise helper."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

from tests.smoke import exercise_api

if TYPE_CHECKING:
    import pytest


def test_bootstrap_token_uses_home_assistant_client_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use HA's client ID for both onboarding and token exchange."""
    calls: list[dict] = []

    def fake_call(url: str, **kwargs: object) -> dict:
        calls.append({"url": url, **kwargs})
        if url.endswith("/api/onboarding/users"):
            return {"auth_code": "onboarding-code"}
        return {"access_token": "access-token"}

    monkeypatch.setattr(exercise_api, "call", fake_call)

    assert exercise_api.bootstrap_token("http://ha") == "access-token"
    assert calls[0]["payload"]["client_id"] == "http://home-assistant.io"
    assert calls[1]["form"]["client_id"] == "http://home-assistant.io"


def test_failure_mode_calls_existing_entry_service_without_config_flow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Failure mode reuses an existing token and entry after initial setup."""
    calls: list[dict[str, object]] = []

    def fake_call(
        url: str,
        token: str = "",
        method: str = "GET",
        payload: dict | None = None,
        **kwargs: object,
    ) -> dict:
        calls.append(
            {"url": url, "token": token, "method": method, "payload": payload, **kwargs}
        )
        if url.endswith("/api/services/textbelt_sms/send_sms"):
            raise exercise_api.error.HTTPError(url, 500, "failure", {}, None)
        if url.endswith("/api/config/config_entries/entry"):
            return [{"domain": "textbelt_sms", "state": "loaded"}]
        if url.endswith("/api/services"):
            return [{"domain": "textbelt_sms", "services": {"send_sms": {}}}]
        return {}

    monkeypatch.setattr(exercise_api, "call", fake_call)
    monkeypatch.setattr(exercise_api, "wait_for_ha", lambda _base: None)
    monkeypatch.setattr(
        sys,
        "argv",
        ["exercise_api.py", "--token", "existing-token", "--failure"],
    )

    exercise_api.main()

    assert [call["url"] for call in calls] == [
        "http://127.0.0.1:8123/api/config/config_entries/entry",
        "http://127.0.0.1:8123/api/services",
        "http://127.0.0.1:8123/api/services/textbelt_sms/send_sms",
    ]
    assert calls[-1]["token"] == "existing-token"  # noqa: S105
# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
