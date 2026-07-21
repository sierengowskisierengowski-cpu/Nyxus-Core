#!/usr/bin/env python3
"""
meli_http_honeypot.py — Lightweight HTTP honeypot for Meli.

Runs a small HTTP server that logs every request as a canonical Meli event
and publishes it to the same `meli/events/ingest` MQTT topic Cowrie uses.
Returns plausible-looking responses so scanners hang around long enough to
reveal what they're after (path probes, auth brute force, exploit payloads).

Why stdlib only?
    The whole point is that this runs on a Pi alongside Cowrie. We don't want
    to drag in a web framework or async runtime. `http.server` is enough.

Usage:
    python3 meli_http_honeypot.py                     # listen on 0.0.0.0:8080
    python3 meli_http_honeypot.py --bind 0.0.0.0 --port 8080 \\
        --mqtt-host 127.0.0.1 --mqtt-port 1883 \\
        --topic meli/events/ingest --name pi-http

Networking on the Pi:
    Bind to an unprivileged port (default 8080) and redirect 80 to it:
        sudo iptables -t nat -A PREROUTING -p tcp --dport 80 \\
            -j REDIRECT --to-port 8080

Reliability:
    * MQTT publish failures fall back to a JSON line in --backup-log so a
      `tail -F | mosquitto_pub` retry loop (or manual reconcile) can recover.
    * If --backup-log is unset, dropped events are only logged to stderr.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlsplit


MAX_BODY_BYTES = 8192  # Cap captured POST bodies so a 4 GiB upload doesn't OOM us.
MAX_HEADER_BYTES = 4096

_shutdown = threading.Event()


def _handle_signal(signum, frame):  # noqa: ARG001
    _shutdown.set()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ── Realistic-looking response bodies ────────────────────────────────────────
# These are intentionally generic so we look like a stock nginx box. Scanners
# fingerprint on these strings; mismatching them is a giveaway.

_NGINX_INDEX = (
    b"<!DOCTYPE html>\n<html><head><title>Welcome to nginx!</title></head>"
    b"<body><h1>Welcome to nginx!</h1>"
    b"<p>If you see this page, the nginx web server is successfully installed "
    b"and working. Further configuration is required.</p></body></html>\n"
)
_NGINX_404 = (
    b"<html>\r\n<head><title>404 Not Found</title></head>\r\n"
    b"<body>\r\n<center><h1>404 Not Found</h1></center>\r\n"
    b"<hr><center>nginx/1.18.0</center>\r\n</body>\r\n</html>\r\n"
)
_BASIC_AUTH_PAGE = (
    b"<html><head><title>401 Authorization Required</title></head>"
    b"<body><h1>401 Authorization Required</h1></body></html>"
)


def _classify_path(path: str) -> tuple[int, bytes, dict[str, str]]:
    """Pick a realistic response (status, body, extra headers) for a path."""
    p = path.lower()
    if p in ("/", "/index.html"):
        return 200, _NGINX_INDEX, {"Content-Type": "text/html; charset=utf-8"}
    if p == "/robots.txt":
        return 200, b"User-agent: *\nDisallow:\n", {"Content-Type": "text/plain"}
    if p == "/favicon.ico":
        return 404, b"", {}
    # Common admin / auth probes — challenge for basic auth so scanners send creds.
    auth_prefixes = (
        "/admin", "/wp-admin", "/wp-login", "/phpmyadmin", "/manager",
        "/console", "/.env", "/login", "/owa", "/cgi-bin",
    )
    if any(p.startswith(pfx) for pfx in auth_prefixes):
        return 401, _BASIC_AUTH_PAGE, {
            "Content-Type": "text/html",
            "WWW-Authenticate": 'Basic realm="Restricted"',
        }
    return 404, _NGINX_404, {"Content-Type": "text/html"}


# ── MQTT publisher (lazy import so the script also runs in --log-only mode) ─

class _Publisher:
    """Publishes canonical Meli events to MQTT with a backup-log fallback."""

    def __init__(self, host: str, port: int, topic: str, client_id: str,
                 backup_log: str | None) -> None:
        self.topic = topic
        self.backup_log = backup_log
        self._client = None
        self._lock = threading.Lock()
        self._mqtt_ok = False

        try:
            import paho.mqtt.client as mqtt
            self._client = mqtt.Client(client_id=client_id, clean_session=True)
            self._client.reconnect_delay_set(min_delay=1, max_delay=30)
            self._client.connect_async(host, port, keepalive=60)
            self._client.loop_start()
            self._mqtt_ok = True
            print(f"[meli-http] MQTT publisher started -> mqtt://{host}:{port}/{topic}",
                  flush=True)
        except Exception as e:
            print(f"[meli-http] WARN: MQTT init failed ({e}); falling back to "
                  f"backup-log only", file=sys.stderr, flush=True)

    def publish(self, event: dict) -> None:
        payload = json.dumps(event, default=str)
        sent = False
        if self._mqtt_ok and self._client is not None:
            try:
                info = self._client.publish(self.topic, payload, qos=1)
                # Don't wait long — we're inside the request handler.
                info.wait_for_publish(timeout=2)
                sent = info.is_published()
            except Exception as e:
                print(f"[meli-http] MQTT publish failed: {e}",
                      file=sys.stderr, flush=True)
                sent = False

        if not sent and self.backup_log:
            try:
                with self._lock, open(self.backup_log, "a") as f:
                    f.write(payload + "\n")
            except OSError as e:
                print(f"[meli-http] backup-log write failed: {e}",
                      file=sys.stderr, flush=True)
        elif not sent:
            print(f"[meli-http] dropped event (no MQTT, no backup-log): "
                  f"{payload[:160]}", file=sys.stderr, flush=True)

    def close(self) -> None:
        if self._client is not None:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass


# ── Request handler ──────────────────────────────────────────────────────────

class _HoneypotHandler(BaseHTTPRequestHandler):
    # Set by HoneypotServer at construction.
    publisher: "_Publisher"
    honeypot_name: str

    # Quieter than the default which prints every request to stderr; we have
    # our own structured logging via the publisher.
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def _read_body(self) -> bytes:
        length = 0
        try:
            length = int(self.headers.get("Content-Length", "0") or 0)
        except ValueError:
            return b""
        if length <= 0:
            return b""
        return self.rfile.read(min(length, MAX_BODY_BYTES))

    def _captured_headers(self) -> dict[str, str]:
        out: dict[str, str] = {}
        total = 0
        for k, v in self.headers.items():
            entry_size = len(k) + len(v) + 2
            if total + entry_size > MAX_HEADER_BYTES:
                out["__truncated__"] = "true"
                break
            out[k] = v
            total += entry_size
        return out

    def _handle(self, method: str) -> None:
        body = self._read_body() if method in ("POST", "PUT", "PATCH") else b""
        split = urlsplit(self.path)
        path = split.path or "/"
        query = split.query

        status, resp_body, extra_headers = _classify_path(path)

        try:
            self.send_response(status)
            self.send_header("Server", "nginx/1.18.0")
            for hk, hv in extra_headers.items():
                self.send_header(hk, hv)
            self.send_header("Content-Length", str(len(resp_body)))
            self.send_header("Connection", "close")
            self.end_headers()
            if method != "HEAD":
                self.wfile.write(resp_body)
        except (BrokenPipeError, ConnectionResetError):
            # Scanner hung up — that's normal.
            pass

        # Build canonical Meli event. The ingest pipeline's GenericJsonParser
        # consumes this shape directly (see meli/ingest/parsers/generic_json.py).
        client_ip, client_port = (self.client_address + ("",))[:2]
        try:
            body_text = body.decode("utf-8", errors="replace")
        except Exception:
            body_text = ""

        ua = self.headers.get("User-Agent", "")
        full_path = path if not query else f"{path}?{query}"

        event = {
            "timestamp": _utc_iso(),
            "network": {
                "source_ip": client_ip,
                "source_port": int(client_port) if isinstance(client_port, int)
                               or (isinstance(client_port, str) and client_port.isdigit())
                               else None,
                "destination_port": self.server.server_address[1],
                "protocol": "tcp",
                "transport": "http",
            },
            "honeypot": {
                "type": "http",
                "name": self.honeypot_name,
            },
            "action": {
                "type": "web_request",
                # `command` is what the Live Feed shows, so make it readable.
                "details": {
                    "command": f"{method} {full_path}",
                    "method": method,
                    "path": full_path,
                    "user_agent": ua,
                    "headers": self._captured_headers(),
                    "body": body_text,
                    "response_status": status,
                },
            },
            "session": {
                # Each request gets its own ID — HTTP is stateless and scanners
                # rarely use keep-alive, so per-request is the honest mapping.
                "session_id": uuid.uuid4().hex,
            },
        }

        try:
            self.publisher.publish(event)
        except Exception as e:
            print(f"[meli-http] publish raised: {e}", file=sys.stderr, flush=True)

    # Method dispatchers
    def do_GET(self): self._handle("GET")        # noqa: N802
    def do_POST(self): self._handle("POST")      # noqa: N802
    def do_HEAD(self): self._handle("HEAD")      # noqa: N802
    def do_PUT(self): self._handle("PUT")        # noqa: N802
    def do_DELETE(self): self._handle("DELETE")  # noqa: N802
    def do_PATCH(self): self._handle("PATCH")    # noqa: N802
    def do_OPTIONS(self): self._handle("OPTIONS")  # noqa: N802


def _make_handler(publisher: _Publisher, name: str):
    """Bind the publisher onto a fresh handler subclass per server instance."""
    return type(
        "BoundHoneypotHandler",
        (_HoneypotHandler,),
        {"publisher": publisher, "honeypot_name": name},
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a lightweight HTTP honeypot that publishes to Meli")
    parser.add_argument("--bind", default="0.0.0.0", help="Interface to listen on")
    parser.add_argument("--port", type=int, default=8080,
                        help="Port to listen on (use iptables to redirect :80)")
    parser.add_argument("--mqtt-host", default="127.0.0.1")
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--topic", default="meli/events/ingest")
    parser.add_argument(
        "--name",
        default=f"http-{os.uname().nodename}",
        help="Honeypot name reported in the event (honeypot.name)",
    )
    parser.add_argument(
        "--client-id",
        default=f"meli-http-{os.uname().nodename}-{os.getpid()}",
        help="MQTT client id",
    )
    parser.add_argument(
        "--backup-log",
        default="",
        help="Path to append JSON events to when MQTT publish fails (recommended)",
    )
    args = parser.parse_args()

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    publisher = _Publisher(
        args.mqtt_host, args.mqtt_port, args.topic, args.client_id,
        args.backup_log or None,
    )
    handler_cls = _make_handler(publisher, args.name)

    # Allow rapid restart without "Address already in use".
    ThreadingHTTPServer.allow_reuse_address = True
    try:
        server = ThreadingHTTPServer((args.bind, args.port), handler_cls)
    except OSError as e:
        print(f"[meli-http] cannot bind {args.bind}:{args.port}: {e}",
              file=sys.stderr, flush=True)
        publisher.close()
        return 1
    server.daemon_threads = True
    # Don't let one slow scanner block clean shutdown.
    server.socket.settimeout(None)

    print(f"[meli-http] listening on {args.bind}:{args.port} as '{args.name}'",
          flush=True)

    # Run the server on a background thread so SIGTERM is handled promptly.
    serve_thread = threading.Thread(target=server.serve_forever,
                                    kwargs={"poll_interval": 0.5}, daemon=True)
    serve_thread.start()

    try:
        while not _shutdown.is_set():
            _shutdown.wait(timeout=1.0)
    finally:
        print("[meli-http] shutting down", flush=True)
        try:
            server.shutdown()
            server.server_close()
        except Exception:
            pass
        publisher.close()

    return 0


if __name__ == "__main__":
    sys.exit(main())
