"""
NYXUS GodsApp — local REST API for automation.
© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED

Pure stdlib http.server (no Flask dependency). Binds to 127.0.0.1:7331
by default. Provides:

    GET  /api/health
    GET  /api/scans?limit=N
    GET  /api/scans/<id>
    GET  /api/findings?severity=<>
    GET  /api/devices
    GET  /api/schedules
    POST /api/schedules           {name,module,target,cadence_seconds}
    DELETE /api/schedules/<id>

Authentication: a bearer token written to ~/.config/nyxus-godsapp/api_token
on first run. Connections from non-loopback addresses are refused.
"""
from __future__ import annotations

import json
import os
import secrets
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import db
import scheduler

TOKEN_PATH = Path.home() / ".config" / "nyxus-godsapp" / "api_token"


def _ensure_token() -> str:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    if TOKEN_PATH.is_file():
        return TOKEN_PATH.read_text().strip()
    tok = secrets.token_urlsafe(32)
    TOKEN_PATH.write_text(tok)
    os.chmod(TOKEN_PATH, 0o600)
    return tok


TOKEN = _ensure_token()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):  # silence the default stderr spam
        pass

    def _check_auth(self) -> bool:
        if not self.client_address[0].startswith("127.") and self.client_address[0] != "::1":
            return False
        h = self.headers.get("Authorization", "")
        return h == f"Bearer {TOKEN}"

    def _send_json(self, payload, status: int = 200):
        body = json.dumps(payload, default=str).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self) -> dict:
        n = int(self.headers.get("Content-Length") or "0")
        if not n:
            return {}
        raw = self.rfile.read(n).decode("utf-8", errors="replace")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        if not self._check_auth():
            return self._send_json({"error": "unauthorized"}, 401)

        path = self.path.split("?", 1)[0]
        query = dict(qp.split("=", 1) for qp in (self.path.split("?", 1)[1] if "?" in self.path else "").split("&") if "=" in qp)

        if path == "/api/health":
            return self._send_json({"ok": True, "version": "1.0"})

        if path == "/api/scans":
            limit = int(query.get("limit", "50"))
            return self._send_json(db.list_recent_scans(limit))

        if path.startswith("/api/scans/"):
            scan_id = path.rsplit("/", 1)[1]
            cur = db.conn().execute("SELECT * FROM scans WHERE id=?", (scan_id,))
            row = cur.fetchone()
            if not row:
                return self._send_json({"error": "not found"}, 404)
            cols = [d[0] for d in cur.description]
            return self._send_json(dict(zip(cols, row)))

        if path == "/api/findings":
            sev = query.get("severity", "")
            sql = "SELECT * FROM findings"
            params = ()
            if sev:
                sql += " WHERE severity=?"
                params = (sev.upper(),)
            sql += " ORDER BY id DESC LIMIT 200"
            cur = db.conn().execute(sql, params)
            cols = [d[0] for d in cur.description]
            return self._send_json([dict(zip(cols, r)) for r in cur.fetchall()])

        if path == "/api/devices":
            cur = db.conn().execute("SELECT * FROM device_history ORDER BY last_seen DESC")
            cols = [d[0] for d in cur.description]
            return self._send_json([dict(zip(cols, r)) for r in cur.fetchall()])

        if path == "/api/schedules":
            return self._send_json(scheduler.list_schedules())

        return self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if not self._check_auth():
            return self._send_json({"error": "unauthorized"}, 401)
        if self.path == "/api/schedules":
            data = self._read_body()
            try:
                sid = scheduler.add_schedule(
                    data["name"], data["module"], data.get("target", ""),
                    int(data["cadence_seconds"]),
                )
                return self._send_json({"id": sid}, 201)
            except Exception as exc:
                return self._send_json({"error": str(exc)}, 400)
        return self._send_json({"error": "not found"}, 404)

    def do_DELETE(self):
        if not self._check_auth():
            return self._send_json({"error": "unauthorized"}, 401)
        if self.path.startswith("/api/schedules/"):
            sid = int(self.path.rsplit("/", 1)[1])
            scheduler.delete_schedule(sid)
            return self._send_json({"ok": True})
        return self._send_json({"error": "not found"}, 404)


_server: ThreadingHTTPServer | None = None


def start(host: str = "127.0.0.1", port: int = 7331) -> str:
    global _server
    if _server is not None:
        return f"already running on {host}:{port}"
    _server = ThreadingHTTPServer((host, port), Handler)
    threading.Thread(target=_server.serve_forever, daemon=True, name="api").start()
    return f"http://{host}:{port}  (token in {TOKEN_PATH})"


def stop() -> None:
    global _server
    if _server is not None:
        _server.shutdown()
        _server = None
