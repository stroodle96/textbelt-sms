# Copyright (c) 2026 Textbelt SMS contributors
"""Behavioral local HTTP checks for the deterministic provider fixture."""

# Dynamic transport fixture returns JSON from an ephemeral HTTP server.
# ruff: noqa: ANN001, ANN201, PLR2004
import json
import threading
from http.client import RemoteDisconnected
from http.server import HTTPServer
from urllib import error, request

import pytest
import pytest_socket

from tests.smoke import textbelt_stub as stub


@pytest.fixture
def server(tmp_path, monkeypatch):
    """Run the actual stub handler on an ephemeral loopback port."""
    pytest_socket.enable_socket()
    for name in (
        "REQUESTS",
        "MODE",
        "STATUS",
        "QUOTA",
        "QUOTA_MODE",
        "PLAN",
        "OUTCOMES",
    ):
        monkeypatch.setattr(stub, name, tmp_path / name)
    httpd = HTTPServer(("127.0.0.1", 0), stub.Handler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    yield f"http://127.0.0.1:{httpd.server_port}"
    httpd.shutdown()
    worker.join()
    httpd.server_close()
    pytest_socket.disable_socket(allow_unix_socket=True)


def call(base, path, data=None):
    """Use actual standard-library HTTP transport."""
    body = None if data is None else json.dumps(data).encode()
    with request.urlopen(base + path, data=body, timeout=2) as response:  # noqa: S310
        return json.load(response)


def send(base):
    """Send the same synthetic payload used by the integration."""
    with request.urlopen(  # noqa: S310
        base + "/text",
        data=b"phone=%2B15551234567&message=test&key=smoke-test-key",
        timeout=2,
    ) as response:
        return json.load(response)


def test_fifo_accept_disconnect_debits_once_and_does_not_retry(server):
    """Observe uncertain acceptance without an extra HTTP attempt."""
    call(server, "/plan", ["success", "accept_disconnect", "provider_reject"])
    assert send(server)["success"]
    with pytest.raises(RemoteDisconnected):
        send(server)
    ledger = call(server, "/outcomes")["outcomes"]
    assert [x["kind"] for x in ledger] == ["success", "accept_disconnect"]
    assert [x["quotaRemaining"] for x in ledger] == [97, 96]
    assert len(call(server, "/requests")["requests"]) == 2
    assert not send(server)["success"]
    assert call(server, "/quota/smoke-test-key")["quotaRemaining"] == 96


def test_reset_removes_plan_ledger_but_preserves_quota(server):
    """Reset isolation keeps account quota realistic."""
    send(server)
    call(server, "/plan", ["provider_reject"])
    call(server, "/reset", {})
    assert call(server, "/requests") == {"requests": []}
    assert call(server, "/outcomes") == {"outcomes": []}
    assert send(server)["success"]
    assert call(server, "/quota/smoke-test-key")["quotaRemaining"] == 96


def test_status_http_failure_and_malformed_quota_are_independent(server):
    """Lookup failure does not prevent sends."""
    call(server, "/status/http_failure", {})
    with pytest.raises(error.HTTPError) as exc:
        call(server, "/status/1")
    assert exc.value.code == 503
    call(server, "/quota-mode/malformed_json", {})
    with pytest.raises(json.JSONDecodeError):
        call(server, "/quota/smoke-test-key")
    assert send(server)["success"]
