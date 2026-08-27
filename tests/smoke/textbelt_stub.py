"""Deterministic Textbelt test double for the real Home Assistant smoke test."""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

REQUESTS = Path(os.getenv("TEXTBELT_STUB_REQUESTS", "textbelt-requests.json"))
MODE = REQUESTS.with_name("mode")


class Handler(BaseHTTPRequestHandler):
    """Record requests and return controllable Textbelt responses."""

    def do_GET(self) -> None:
        """Serve health, mode, and recorded-request endpoints."""
        if self.path == "/requests":
            self._send(200, {"requests": self._read()})
            return
        if self.path == "/health":
            self._send(200, {"ok": True})
            return
        if self.path == "/mode":
            self._send(200, {"mode": self._mode()})
            return
        self._send(404, {})

    def do_POST(self) -> None:
        """Handle mode changes and record Textbelt requests."""
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
        if self.path != "/text":
            self._send(404, {})
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = self.rfile.read(length).decode("utf-8")
        request = {key: values[-1] for key, values in parse_qs(payload).items()}
        requests = self._read()
        requests.append(request)
        REQUESTS.write_text(json.dumps(requests), encoding="utf-8")
        self._send(
            200,
            {"success": self._mode() == "success"},
        )

    def _read(self) -> list[dict[str, str]]:
        if not REQUESTS.exists():
            return []
        return json.loads(REQUESTS.read_text(encoding="utf-8"))

    def _mode(self) -> str:
        return MODE.read_text(encoding="utf-8") if MODE.exists() else "success"

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
    HTTPServer(("0.0.0.0", int(os.getenv("PORT", "8080"))), Handler).serve_forever()  # noqa: S104
