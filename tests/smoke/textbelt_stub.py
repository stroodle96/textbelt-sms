# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Deterministic Textbelt test double for the real Home Assistant smoke test."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

REQUESTS = Path(os.getenv("TEXTBELT_STUB_REQUESTS", "textbelt-requests.json"))
MODE = REQUESTS.with_name("mode")
STATUS = REQUESTS.with_name("status")
QUOTA = REQUESTS.with_name("quota")
QUOTA_MODE = REQUESTS.with_name("quota-mode")


class Handler(BaseHTTPRequestHandler):
    """Record requests and return controllable Textbelt responses."""

    def do_GET(self) -> None:
        """Serve health, mode, and recorded-request endpoints."""
        if self.path.startswith("/quota/"):
            valid = self.path == "/quota/smoke-test-key"
            self._send(
                200,
                {
                    "success": valid and self._quota_mode() == "success",
                    "quotaRemaining": self._quota(),
                },
            )
            return
        if self.path == "/requests":
            self._send(200, {"requests": self._read()})
            return
        if self.path == "/health":
            self._send(200, {"ok": True})
            return
        if self.path == "/mode":
            self._send(200, {"mode": self._mode()})
            return
        if self.path == "/status":
            self._send(200, {"status": self._status()})
            return
        if self.path.startswith("/status/") and "?" not in self.path:
            self._send(200, {"status": self._status()})
            return
        self._send(404, {})

    def do_POST(self) -> None:
        """Handle mode changes and record Textbelt requests."""
        if self.path in {"/quota-mode/success", "/quota-mode/failure"}:
            QUOTA_MODE.write_text(self.path.rsplit("/", 1)[-1], encoding="utf-8")
            self._send(200, {"ok": True})
            return
        if self.path == "/reset":
            REQUESTS.write_text("[]", encoding="utf-8")
            self._send(200, {"ok": True})
            return
        if self.path in {"/mode/success", "/mode/failure"}:
            MODE.write_text(
                "success" if self.path.endswith("success") else "failure",
                encoding="utf-8",
            )
            self._send(200, {"ok": True})
            return
        if self.path in {"/status/pending", "/status/delivered", "/status/failed"}:
            STATUS.write_text(self.path.rsplit("/", 1)[-1], encoding="utf-8")
            self._send(200, {"ok": True})
            return
        if self.path != "/text":
            self._send(404, {})
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        request = {key: values[-1] for key, values in parse_qs(payload).items()}
        requests = self._read()
        requests.append(request)
        REQUESTS.write_text(json.dumps(requests), encoding="utf-8")
        success = self._mode() == "success"
        if success:
            QUOTA.write_text(str(max(0, self._quota() - 1)), encoding="utf-8")
        self._send(
            200,
            {
                "success": success,
                "textId": len(requests),
                "quotaRemaining": self._quota(),
            },
        )

    def _read(self) -> list[dict[str, str]]:
        if not REQUESTS.exists():
            return []
        return json.loads(REQUESTS.read_text(encoding="utf-8"))

    def _quota(self) -> int:
        return int(QUOTA.read_text(encoding="utf-8")) if QUOTA.exists() else 98

    def _quota_mode(self) -> str:
        return (
            QUOTA_MODE.read_text(encoding="utf-8") if QUOTA_MODE.exists() else "success"
        )

    def _mode(self) -> str:
        return MODE.read_text(encoding="utf-8") if MODE.exists() else "success"

    def _status(self) -> str:
        return STATUS.read_text(encoding="utf-8") if STATUS.exists() else "pending"

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args: object) -> None:
        """Keep the deterministic stub quiet."""
        return


if __name__ == "__main__":
    REQUESTS.write_text("[]", encoding="utf-8")
    MODE.write_text("success", encoding="utf-8")
    STATUS.write_text("pending", encoding="utf-8")
    QUOTA.write_text("98", encoding="utf-8")
    QUOTA_MODE.write_text("success", encoding="utf-8")
    HTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler).serve_forever()  # noqa: S104
