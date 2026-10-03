# Copyright (c) 2019 - 2025  Joakim Sørensen @ludeeus
"""Deterministic Textbelt test double for the real Home Assistant smoke test."""

from __future__ import annotations

import json
import os
import socket
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

REQUESTS = Path(os.getenv("TEXTBELT_STUB_REQUESTS", "textbelt-requests.json"))
MODE = REQUESTS.with_name("mode")
STATUS = REQUESTS.with_name("status")
QUOTA = REQUESTS.with_name("quota")
PLAN = REQUESTS.with_name("plan.json")
OUTCOMES = REQUESTS.with_name("outcomes.json")
QUOTA_MODE = REQUESTS.with_name("quota-mode")


class Handler(BaseHTTPRequestHandler):
    """Record requests and return controllable Textbelt responses."""

    def do_GET(self) -> None:  # noqa: PLR0911
        """Serve health, mode, and recorded-request endpoints."""
        if self.path.startswith("/quota/"):
            if self._failure_response(self._quota_mode()):
                return
            valid = self.path == "/quota/smoke-test-key"
            self._send(
                200,
                {
                    "success": valid and self._quota_mode() == "success",
                    "quotaRemaining": self._quota(),
                },
            )
            return
        if self.path == "/outcomes":
            self._send(200, {"outcomes": self._json_file(OUTCOMES)})
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
            if self._failure_response(self._status()):
                return
            self._send(200, {"status": self._status()})
            return
        self._send(404, {})

    def do_POST(self) -> None:  # noqa: PLR0911
        """Handle mode changes and record Textbelt requests."""
        if self.path in {
            "/quota-mode/success",
            "/quota-mode/failure",
            "/quota-mode/http_failure",
            "/quota-mode/malformed_json",
        }:
            QUOTA_MODE.write_text(self.path.rsplit("/", 1)[-1], encoding="utf-8")
            self._send(200, {"ok": True})
            return
        if self.path == "/plan":
            plan = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            allowed = {
                "success",
                "provider_reject",
                "http_failure",
                "malformed_json",
                "accept_disconnect",
            }
            if not isinstance(plan, list) or any(item not in allowed for item in plan):
                self._send(400, {"error": "invalid plan"})
                return
            PLAN.write_text(json.dumps(plan), encoding="utf-8")
            self._send(200, {"ok": True})
            return
        if self.path == "/reset":
            PLAN.write_text("[]", encoding="utf-8")
            OUTCOMES.write_text("[]", encoding="utf-8")
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
        if self.path in {
            "/status/pending",
            "/status/delivered",
            "/status/failed",
            "/status/http_failure",
            "/status/malformed_json",
        }:
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
        plan = self._json_file(PLAN)
        outcome = (
            plan.pop(0)
            if plan
            else ("success" if self._mode() == "success" else "provider_reject")
        )
        PLAN.write_text(json.dumps(plan), encoding="utf-8")
        success = outcome in {"success", "accept_disconnect"}
        if success:
            QUOTA.write_text(str(max(0, self._quota() - 1)), encoding="utf-8")
        ledger = self._json_file(OUTCOMES)
        ledger.append(
            {
                "attempt": len(requests),
                "accepted": success,
                "textId": str(len(requests)) if success else None,
                "quotaRemaining": self._quota(),
                "kind": outcome,
            }
        )
        OUTCOMES.write_text(json.dumps(ledger), encoding="utf-8")
        if outcome == "accept_disconnect":
            self.close_connection = True
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        if outcome == "malformed_json":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"not-json")
            return
        self._send(
            503 if outcome == "http_failure" else 200,
            {
                "success": success,
                "textId": len(requests),
                "quotaRemaining": self._quota(),
            },
        )

    @staticmethod
    def _json_file(path: Path) -> list:
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else []

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

    def _failure_response(self, mode: str) -> bool:
        if mode == "http_failure":
            self._send(503, {"error": "synthetic failure"})
            return True
        if mode == "malformed_json":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"not-json")
            return True
        return False

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
