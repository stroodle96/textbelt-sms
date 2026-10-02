# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Tests for the real Home Assistant smoke API exercise helper."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sys
from io import BytesIO
from pathlib import Path

import pytest

from custom_components.textbelt_sms.options import callback_base_url
from tests.smoke import exercise_api


def test_call_accepts_successful_empty_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Treat Home Assistant's empty successful webhook response as success."""
    monkeypatch.setattr(
        exercise_api.request,
        "urlopen",
        lambda *_args, **_kwargs: BytesIO(b""),
    )

    assert exercise_api.call("http://ha/api/webhook/test", method="POST") == {}


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


def test_assert_runtime_waits_for_entry_to_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Wait for config-entry setup to finish after a real HA restart."""
    entry_responses = [
        [{"domain": "textbelt_sms", "state": "not_loaded"}],
        [{"domain": "textbelt_sms", "state": "loaded"}],
    ]

    def fake_call(url: str, _token: str = "") -> dict | list:
        if url.endswith("/api/config/config_entries/entry"):
            return entry_responses.pop(0)
        return [{"domain": "textbelt_sms", "services": {"send_sms": {}}}]

    monkeypatch.setattr(exercise_api, "call", fake_call)
    monkeypatch.setattr(exercise_api.time, "sleep", lambda _seconds: None)

    exercise_api.assert_runtime("http://ha", "token")

    assert entry_responses == []


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
            return [
                {"domain": "sun", "state": "loaded"},
                {"domain": "textbelt_sms", "state": "loaded"},
                {"domain": "analytics", "state": "setup_in_progress"},
            ]
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


@pytest.mark.parametrize("restart", [False, True])
def test_live_smoke_does_not_assume_stub_quota(
    monkeypatch: pytest.MonkeyPatch, *, restart: bool
) -> None:
    """A real _test key may have any quota or no quota lookup support."""
    calls: list[str] = []

    def fake_call(
        url: str, _token: str = "", _method: str = "GET", _payload: dict | None = None
    ) -> dict | list:
        calls.append(url)
        if url.endswith("/api/config/config_entries/entry"):
            return [{"domain": "textbelt_sms", "state": "loaded"}]
        if url.endswith("/api/services"):
            return [{"domain": "textbelt_sms", "services": {"send_sms": {}}}]
        if url.endswith("/api/config/config_entries/flow"):
            return {"flow_id": "test-flow"}
        if url.endswith("/api/config/config_entries/flow/test-flow"):
            return {"type": "create_entry"}
        if url.endswith("/api/services/textbelt_sms/send_sms"):
            return []
        message = f"Live smoke unexpectedly depended on stub or sensor state: {url}"
        raise AssertionError(message)

    monkeypatch.setenv("LIVE_SMOKE", "1")
    monkeypatch.setattr(exercise_api, "call", fake_call)
    monkeypatch.setattr(exercise_api, "wait_for_ha", lambda _base: None)
    monkeypatch.setattr(exercise_api, "bootstrap_token", lambda _base: "test-token")
    args = ["exercise_api.py", "--api-key", "provider_test"]
    if restart:
        args.extend(["--token", "test-token", "--verify-runtime"])
    monkeypatch.setattr(sys, "argv", args)

    exercise_api.main()

    assert "http://127.0.0.1:8123/api/services/textbelt_sms/send_sms" in calls


def test_native_notify_configures_options_and_discovers_entity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The local smoke sends through HA's native notify entity after reload."""
    calls = []

    def fake_call(  # noqa: PLR0911
        url: str, _token: str = "", method: str = "GET", payload: dict | None = None
    ) -> dict | list:
        calls.append((url, method, payload))
        if url.endswith("/entry"):
            return [{"domain": "textbelt_sms", "entry_id": "entry-1"}]
        if url.endswith("/options/flow"):
            return {"flow_id": "options-1"}
        if url.endswith("/options/flow/options-1"):
            return {"type": "create_entry"}
        if url.endswith("/api/states"):
            return [
                {
                    "entity_id": "notify.textbelt_sms_4567_abcd",
                    "state": "unknown",
                    "attributes": {"friendly_name": "Textbelt SMS 4567"},
                }
            ]
        if "/api/states/notify." in url:
            return {"state": "2026-10-01T12:00:00+00:00"}
        if url.endswith("/requests"):
            return {
                "requests": [
                    {},
                    {},
                    {},
                    {
                        "phone": "+15551234567",
                        "message": "Water leak: Water was detected in utility room.",
                        "key": "smoke-test-key",
                    },
                ]
            }
        return []

    monkeypatch.setattr(exercise_api, "call", fake_call)
    exercise_api.exercise_notify("http://ha", "token", "http://stub", "smoke-test-key")
    assert (
        "http://ha/api/config/config_entries/options/flow",
        "POST",
        {"handler": "entry-1"},
    ) in calls
    assert (
        "http://ha/api/config/config_entries/options/flow/options-1",
        "POST",
        {"notification_recipients": "+15551234567"},
    ) in calls
    assert (
        "http://ha/api/services/notify/send_message",
        "POST",
        {
            "entity_id": "notify.textbelt_sms_4567_abcd",
            "title": "Water leak",
            "message": "Water was detected in utility room.",
        },
    ) in calls


def test_native_notify_mode_is_disabled_for_live_smoke(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The new native notify case never adds a provider send to live smoke."""
    monkeypatch.setenv("LIVE_SMOKE", "1")
    monkeypatch.setattr(exercise_api, "wait_for_ha", lambda _base: None)
    monkeypatch.setattr(
        sys, "argv", ["exercise_api.py", "--token", "test-token", "--notify-only"]
    )

    def unexpected_notify(*_args: object) -> None:
        pytest.fail("Native notify must not run against the provider")

    monkeypatch.setattr(exercise_api, "exercise_notify", unexpected_notify)
    exercise_api.main()


def test_signed_fixture_uses_raw_timestamp_and_bytes() -> None:
    """Match the provider contract with independently computed HMAC."""
    raw = b'{"text":"a b"}'
    headers = exercise_api.signed_headers(raw, "smoke-test-key", "123")
    assert (
        headers["X-textbelt-signature"]
        == hmac.new(b"smoke-test-key", b"123" + raw, hashlib.sha256).hexdigest()
    )


def test_generated_callback_discovery_rejects_fixed_or_foreign_hosts() -> None:
    """Discover only the configured generated path."""
    assert (
        exercise_api.callback_path("https://ha.example.com/api/webhook/abc")
        == "/api/webhook/abc"
    )
    for url in (
        "https://evil.test/api/webhook/abc",
        "https://ha.example.com/api/webhook/textbelt_sms_reply",
    ):
        with pytest.raises(exercise_api.SmokeError):
            exercise_api.callback_path(url)


def test_offline_credentials_override_inherited_provider_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An offline run cannot inherit a provider credential."""
    monkeypatch.setenv("LIVE_SMOKE", "0")
    assert exercise_api.smoke_key("real-provider-key") == "smoke-test-key"


def test_offline_placeholder_matches_product_callback_validation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Validate the actual runner placeholder without any external HTTP request."""

    def unexpected_request(*_args: object, **_kwargs: object) -> None:
        pytest.fail("Placeholder validation must not contact a provider or public host")

    monkeypatch.setenv("LIVE_SMOKE", "0")
    monkeypatch.setattr(exercise_api.request, "urlopen", unexpected_request)
    source = Path(exercise_api.__file__).with_name("run.sh").read_text()
    match = re.search(r"external_url: (\S+)", source)
    assert match is not None
    base = match.group(1)
    assert callback_base_url(base) == base
    assert exercise_api.callback_path(base + "/api/webhook/generated-id") == (
        "/api/webhook/generated-id"
    )
    assert exercise_api.smoke_key("provider-key") == "smoke-test-key"


def test_expected_ha_plaintext_error_does_not_require_json() -> None:
    """HA's deliberate partial-send HTTP500 response is valid plaintext."""
    raw = b"500 Internal Server Error\n\nServer got itself in trouble"
    assert exercise_api.decode_expected_response(raw, status=500, expected=500) == {}


@pytest.mark.parametrize(("status", "expected"), [(400, 500), (200, 500), (500, 200)])
def test_expected_error_decoder_rejects_wrong_status(
    status: int, expected: int
) -> None:
    """A status mismatch cannot be excused by expected-error body handling."""
    with pytest.raises(exercise_api.SmokeError, match="Unexpected HTTP status"):
        exercise_api.decode_expected_response(b"{}", status=status, expected=expected)


def test_success_response_decoder_keeps_json_validation_strict() -> None:
    """Invalid successful JSON remains a harness failure."""
    with pytest.raises(json.JSONDecodeError):
        exercise_api.decode_expected_response(b"not-json", status=200, expected=200)
    assert exercise_api.decode_expected_response(b'{"ok":true}', status=200) == {
        "ok": True
    }
