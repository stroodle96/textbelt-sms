"""Exercise config flow, service, failure, webhook, and restart via HA's API."""

from __future__ import annotations

import argparse
import json
import time
from urllib import error, request


def call(
    url: str, token: str, method: str = "GET", payload: dict | None = None
) -> dict:
    body = None if payload is None else json.dumps(payload).encode()
    req = request.Request(url, data=body, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    with request.urlopen(req, timeout=10) as response:
        return json.load(response)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--token", required=True)
    parser.add_argument("--base", default="http://127.0.0.1:8123")
    parser.add_argument("--failure", action="store_true")
    parser.add_argument("--webhook-only", action="store_true")
    args = parser.parse_args()
    for _ in range(60):
        try:
            call(f"{args.base}/api/", args.token)
            break
        except OSError:
            time.sleep(2)
    else:
        raise RuntimeError("Home Assistant API did not become ready")
    if args.webhook_only:
        call(
            f"{args.base}/api/webhook/textbelt_sms_reply",
            "",
            "POST",
            {"text": "reply"},
        )
        return
    flow = call(
        f"{args.base}/api/config/config_entries/flow",
        args.token,
        "POST",
        {"handler": "textbelt_sms", "show_advanced_options": False},
    )
    result = call(
        f"{args.base}/api/config/config_entries/flow/{flow['flow_id']}",
        args.token,
        "POST",
        {"api_key": "smoke-test-key"},
    )
    if result.get("type") != "create_entry":
        raise RuntimeError(f"config flow failed: {result}")
    try:
        call(
            f"{args.base}/api/services/textbelt_sms/send_sms",
            args.token,
            "POST",
            {"phone": "+15551234567", "message": "smoke"},
        )
    except error.HTTPError:
        if not args.failure:
            raise
    else:
        if args.failure:
            raise RuntimeError("failure stub unexpectedly returned success")


if __name__ == "__main__":
    main()
