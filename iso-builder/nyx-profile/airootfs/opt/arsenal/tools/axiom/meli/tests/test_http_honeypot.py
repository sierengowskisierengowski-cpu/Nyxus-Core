"""Tests for the bundled Meli HTTP honeypot script + the Attackers
service-tag formatter that distinguishes SSH vs HTTP attackers."""
from __future__ import annotations

import importlib.util
import json
import pathlib
import socket
import threading
import time
import urllib.request

import pytest


SCRIPT = pathlib.Path(__file__).parent.parent / "scripts" / "meli_http_honeypot.py"


def _load_honeypot_module():
    spec = importlib.util.spec_from_file_location("meli_http_honeypot", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _RecordingPublisher:
    """Stand-in for the MQTT publisher — captures events in memory."""
    def __init__(self):
        self.events: list[dict] = []
    def publish(self, event):
        self.events.append(event)
    def close(self):
        pass


def _free_port() -> int:
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


@pytest.fixture
def running_honeypot():
    """Spin up the honeypot bound to a random local port for the test."""
    from http.server import ThreadingHTTPServer
    mod = _load_honeypot_module()
    publisher = _RecordingPublisher()
    handler = mod._make_handler(publisher, "test-http")
    port = _free_port()
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    server.daemon_threads = True
    t = threading.Thread(target=server.serve_forever,
                         kwargs={"poll_interval": 0.05}, daemon=True)
    t.start()
    try:
        yield port, publisher
    finally:
        server.shutdown()
        server.server_close()


class TestRequestCapture:
    def test_get_request_emits_canonical_event(self, running_honeypot):
        port, publisher = running_honeypot
        # /wp-admin returns 401 by design — urllib raises on non-2xx, swallow.
        try:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/wp-admin/login.php?next=%2F",
                timeout=2,
            )
        except urllib.error.HTTPError:
            pass
        # Give the handler thread a moment to publish.
        for _ in range(20):
            if publisher.events:
                break
            time.sleep(0.05)
        assert publisher.events, "no event was published"
        ev = publisher.events[0]

        # Canonical shape the ingest pipeline expects.
        assert ev["honeypot"]["type"] == "http"
        assert ev["honeypot"]["name"] == "test-http"
        assert ev["network"]["source_ip"] == "127.0.0.1"
        assert ev["network"]["destination_port"] == port
        assert ev["network"]["transport"] == "http"
        assert ev["action"]["type"] == "web_request"

        details = ev["action"]["details"]
        assert details["method"] == "GET"
        assert details["path"] == "/wp-admin/login.php?next=%2F"
        assert details["command"].startswith("GET /wp-admin/login.php")
        # The /wp-admin probe should be challenged for basic auth so scanners
        # send credentials we can capture next time.
        assert details["response_status"] == 401

    def test_post_body_captured_and_truncated(self, running_honeypot):
        port, publisher = running_honeypot
        big = b"a" * (32 * 1024)  # 32 KiB body — well over the 8 KiB cap.
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/api/v1/exploit",
            data=big,
            headers={"Content-Type": "application/octet-stream"},
            method="POST",
        )
        try:
            urllib.request.urlopen(req, timeout=2)
        except urllib.error.HTTPError:
            pass
        for _ in range(20):
            if publisher.events:
                break
            time.sleep(0.05)
        assert publisher.events
        ev = publisher.events[0]
        details = ev["action"]["details"]
        assert details["method"] == "POST"
        # Body must be captured but capped — never echo a 32 KiB blob into
        # every downstream event.
        MAX_BODY_BYTES = _load_honeypot_module().MAX_BODY_BYTES
        assert 0 < len(details["body"]) <= MAX_BODY_BYTES

    def test_unknown_path_returns_nginx_404(self, running_honeypot):
        port, _ = running_honeypot
        with pytest.raises(urllib.error.HTTPError) as exc:
            urllib.request.urlopen(
                f"http://127.0.0.1:{port}/does-not-exist", timeout=2,
            )
        assert exc.value.code == 404


class TestServiceFormatter:
    """The Attackers view groups events by honeypot_service so SSH-only vs
    HTTP-only vs both is visible without opening the detail panel."""

    def test_known_services_get_short_labels(self):
        from meli.utils.helpers import format_honeypot_services as fmt
        assert fmt(["cowrie"]) == "SSH"
        assert fmt(["http"]) == "HTTP"
        assert fmt(["cowrie", "http"]) == "SSH | HTTP"

    def test_duplicates_and_aliases_collapse(self):
        from meli.utils.helpers import format_honeypot_services as fmt
        assert fmt(["cowrie", "ssh", "ssh"]) == "SSH"

    def test_unknown_service_passes_through(self):
        from meli.utils.helpers import format_honeypot_services as fmt
        assert "weirdpot" in fmt(["weirdpot"])

    def test_empty_returns_empty(self):
        from meli.utils.helpers import format_honeypot_services as fmt
        assert fmt([]) == ""
