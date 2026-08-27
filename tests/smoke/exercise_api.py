# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Exercise config flow, service, failure, webhook, and restart via HA's API."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from urllib import error, parse, request


class SmokeError(RuntimeError):
    """Raised when a real-HA smoke assertion fails."""


HA_CLIENT_ID = "http://home-assistant.io"


def call(
    url: str,
    token: str = "",
    method: str = "GET",
    payload: dict | None = None,
    *,
    form: dict[str, str] | None = None,
) -> dict | list:
    """Call a Home Assistant HTTP API endpoint and decode its JSON response."""
    if form is not None:
        body = parse.urlencode(form).encode()
    else:
        body = None if payload is None else json.dumps(payload).encode()
    req = request.Request(url, data=body, method=method)  # noqa: S310
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header(
        "Content-Type",
        "application/x-www-form-urlencoded" if form else "application/json",
    )
    with request.urlopen(req, timeout=10) as response:  # noqa: S310
        content = response.read()
        return json.loads(content) if content else {}


def stub_call(stub: str, path: str) -> dict:
    """Change or inspect the deterministic local Textbelt stub."""
    method = "POST" if path.startswith(("/mode/", "/status/")) else "GET"
    return call(f"{stub}{path}", method=method)


def wait_for_state(base: str, token: str, expected: str) -> None:
    """Wait for a sensor state after requesting a coordinator refresh."""
    for _ in range(30):
        state = call(
            f"{base}/api/states/sensor.textbelt_sms_last_message_status", token
        )
        if state.get("state") == expected:
            return
        time.sleep(1)
    raise SmokeError(f"Sensor did not reach {expected}: {state}")


def wait_for_ha(base: str) -> None:
    """Wait until HA's HTTP/onboarding stack is responding."""
    for _ in range(90):
        try:
            onboarding = call(f"{base}/api/onboarding")
            if isinstance(onboarding, dict):
                return
        except error.HTTPError:
            pass
        except OSError:
            pass
        else:
            return
        time.sleep(2)
    message = "Home Assistant HTTP API did not become ready"
    raise SmokeError(message)


def bootstrap_token(base: str) -> str:
    """Create the first HA user and exchange the onboarding code for a token."""
    onboarding = call(
        f"{base}/api/onboarding/users",
        method="POST",
        payload={
            "name": "Textbelt smoke",
            "username": "smoke",
            "password": "textbelt-smoke-password",
            "language": "en",
            "client_id": HA_CLIENT_ID,
        },
    )
    auth = call(
        f"{base}/auth/token",
        method="POST",
        form={
            "grant_type": "authorization_code",
            "code": onboarding["auth_code"],
            "client_id": HA_CLIENT_ID,
        },
    )
    return auth["access_token"]


def assert_runtime(base: str, token: str) -> None:
    """Assert one loaded entry and one callable public service."""
    textbelt_entries = []
    for _ in range(60):
        entries = call(f"{base}/api/config/config_entries/entry", token)
        textbelt_entries = [
            entry for entry in entries if entry.get("domain") == "textbelt_sms"
        ]
        if len(textbelt_entries) == 1 and textbelt_entries[0].get("state") == "loaded":
            break
        time.sleep(1)
    else:
        if len(textbelt_entries) != 1:
            raise SmokeError(f"Unexpected Textbelt config entries: {textbelt_entries}")
        raise SmokeError(f"Textbelt entry is not loaded: {textbelt_entries[0]}")
    services = call(f"{base}/api/services", token)
    matches = [
        service
        for service in services
        if service.get("domain") == "textbelt_sms"
        and service.get("services", {}).get("send_sms") is not None
    ]
    if len(matches) != 1:
        raise SmokeError(f"Unexpected send_sms service registration: {matches}")


def configure_entry(base: str, token: str, api_key: str) -> None:
    """Create the Textbelt config entry during the first smoke run."""
    flow = call(
        f"{base}/api/config/config_entries/flow",
        token,
        "POST",
        {"handler": "textbelt_sms", "show_advanced_options": False},
    )
    result = call(
        f"{base}/api/config/config_entries/flow/{flow['flow_id']}",
        token,
        "POST",
        {"api_key": api_key},
    )
    if result.get("type") != "create_entry":
        raise SmokeError(f"config flow failed: {result}")


def exercise_service(
    base: str, token: str, message: str, *, expect_failure: bool = False
) -> None:
    """Call the public service and assert its expected success or failure."""
    try:
        call(
            f"{base}/api/services/textbelt_sms/send_sms",
            token,
            "POST",
            {"phone": "+15551234567", "message": message},
        )
    except error.HTTPError:
        if not expect_failure:
            raise
    else:
        if expect_failure:
            message = "failure stub unexpectedly returned success"
            raise SmokeError(message)


def main() -> None:
    """Run the onboarding, config-entry, service, and webhook smoke checks."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--token")
    parser.add_argument(
        "--api-key", default=os.environ.get("TEXTBELT_API_KEY", "smoke-test-key")
    )
    parser.add_argument("--base", default="http://127.0.0.1:8123")
    parser.add_argument(
        "--stub", default=os.environ.get("TEXTBELT_STUB_URL", "http://127.0.0.1:8080")
    )
    parser.add_argument("--failure", action="store_true")
    parser.add_argument("--webhook-only", action="store_true")
    parser.add_argument("--verify-runtime", action="store_true")
    args = parser.parse_args()
    if args.failure and not args.token:
        parser.error("--failure requires --token from the initial smoke run")
    wait_for_ha(args.base)
    token = args.token or bootstrap_token(args.base)
    if args.webhook_only:
        call(
            f"{args.base}/api/webhook/textbelt_sms_reply",
            "",
            "POST",
            {"text": "reply"},
        )
        return
    if args.verify_runtime:
        assert_runtime(args.base, token)
        exercise_service(args.base, token, "restart-smoke")
        return
    if args.failure:
        assert_runtime(args.base, token)
        exercise_service(args.base, token, "smoke", expect_failure=True)
        return
    configure_entry(args.base, token, args.api_key)
    exercise_service(args.base, token, "smoke")
    if not args.failure:
        requests = call(f"{args.stub}/requests").get("requests", [])
        expected_request = {
            "phone": "+15551234567",
            "message": "smoke",
            "key": args.api_key,
        }
        expected_requests = [
            expected_request,
            {
                **expected_request,
                "webhookUrl": "http://homeassistant:8123/api/webhook/textbelt_sms_reply",
            },
        ]
        if len(requests) != 1 or requests[0] not in expected_requests:
            raise SmokeError(f"Unexpected Textbelt stub request: {requests}")
        wait_for_state(args.base, token, "pending")
        stub_call(args.stub, "/status/delivered")
        call(
            f"{args.base}/api/services/homeassistant/update_entity",
            token,
            "POST",
            {"entity_id": "sensor.textbelt_sms_last_message_status"},
        )
        wait_for_state(args.base, token, "delivered")
        stub_call(args.stub, "/status/failed")
        call(
            f"{args.base}/api/services/homeassistant/update_entity",
            token,
            "POST",
            {"entity_id": "sensor.textbelt_sms_last_message_status"},
        )
        wait_for_state(args.base, token, "failed")
    assert_runtime(args.base, token)
    sys.stdout.write(token)


if __name__ == "__main__":
    main()
