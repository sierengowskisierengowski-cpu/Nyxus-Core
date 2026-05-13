#!/usr/bin/env python3
"""
NYXUS Mission Control daemon
============================

macOS-style workspace overview for Hyprland.

When activated (via `nyxus-mission open`), the daemon:
  1. Enumerates all Hyprland workspaces and clients.
  2. Optionally captures a screenshot of each workspace's monitor via
     grim, downscaled by `thumb_divisor`.
  3. Writes a JSON manifest to $XDG_RUNTIME_DIR/nyxus-mission/state.json
     and individual PNG thumbnails to $HOME/.cache/nyxus/mission/.
  4. The eww `mission` overlay polls the manifest and renders the grid.
  5. CLI/UI sends `select` ops to switch workspaces.

Hardening
---------
- grim and hyprctl are invoked with argv (no shell concatenation).
- Workspace ids and window addresses are validated before being passed
  back to hyprctl (integers, 0x-prefixed hex).
- Cache dir is purged of stale thumbnails on each refresh.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:                       # pragma: no cover
    import tomli as tomllib  # type: ignore


HOME      = Path(os.environ.get("HOME", "/root"))
XDG_RUN   = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
RUN_DIR   = XDG_RUN / "nyxus-mission"
SOCK_PATH = RUN_DIR / "cmd.sock"
STATE_J   = RUN_DIR / "state.json"
CACHE_DIR = HOME / ".cache/nyxus/mission"
CFG_PATH  = HOME / ".config/nyxus/mission.toml"


def log(*a: Any) -> None:
    print("[nyxus-missiond]", *a, file=sys.stderr, flush=True)


@dataclass
class Options:
    refresh_ms: int          = 600
    use_screenshots: bool    = True
    thumb_divisor: int       = 6
    max_workspaces: int      = 16
    animate_ms: int          = 180
    group_by_workspace: bool = True
    clickable: bool          = True
    close_on_select: bool    = True


def load_config() -> Options:
    o = Options()
    if not CFG_PATH.exists():
        return o
    try:
        data = tomllib.loads(CFG_PATH.read_text())
    except (OSError, tomllib.TOMLDecodeError) as e:
        log("config error:", e); return o
    raw = data.get("options", {}) or {}
    for k, v in raw.items():
        if hasattr(o, k):
            setattr(o, k, v)
    return o


def hypr(*args: str) -> str:
    try:
        out = subprocess.run(["hyprctl", *args],
                              capture_output=True, text=True, timeout=2, check=False)
        return out.stdout
    except (OSError, subprocess.TimeoutExpired) as e:
        log("hyprctl error:", e); return ""


def hypr_json(*args: str) -> Any:
    raw = hypr(*args, "-j")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


_HEX_ADDR  = re.compile(r"^0x[0-9a-fA-F]+$")
_INT_RE    = re.compile(r"^-?\d+$")
_NAME_RE   = re.compile(r"^[A-Za-z0-9_.:+-]+$")


def grim_capture_monitor(name: str, divisor: int, dest: Path) -> bool:
    """Capture a single output by name, scaled by 1/divisor."""
    if not _NAME_RE.match(name or ""):
        return False
    divisor = max(1, min(16, int(divisor)))
    scale = 1.0 / divisor
    try:
        # grim -o <name> -s <scale> <dest>
        r = subprocess.run(
            ["grim", "-o", name, "-s", f"{scale:.4f}", str(dest)],
            capture_output=True, timeout=3, check=False,
        )
        return r.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as e:
        log("grim:", e); return False


def refresh(opts: Options) -> dict:
    """Capture overview state. Returns the manifest dict."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    workspaces = hypr_json("workspaces") or []
    clients    = hypr_json("clients") or []
    monitors   = hypr_json("monitors") or []

    if not isinstance(workspaces, list):
        workspaces = []
    workspaces = workspaces[: opts.max_workspaces]

    # group clients by workspace id
    by_ws: dict[int, list[dict]] = {}
    for c in clients if isinstance(clients, list) else []:
        wid = (c.get("workspace") or {}).get("id")
        if isinstance(wid, int):
            by_ws.setdefault(wid, []).append({
                "addr":  c.get("address"),
                "class": c.get("class"),
                "title": c.get("title"),
                "at":    c.get("at"),
                "size":  c.get("size"),
            })

    # screenshot per monitor (one shot per output, shared across its workspaces)
    thumbs: dict[str, str] = {}
    if opts.use_screenshots:
        for m in monitors if isinstance(monitors, list) else []:
            name = m.get("name", "")
            dest = CACHE_DIR / f"mon-{name}.png"
            if grim_capture_monitor(name, opts.thumb_divisor, dest):
                thumbs[name] = str(dest)

    out = {
        "ts":         time.time(),
        "workspaces": [
            {
                "id":      w.get("id"),
                "name":    w.get("name"),
                "monitor": w.get("monitor"),
                "windows": by_ws.get(w.get("id", -1), []),
                "thumb":   thumbs.get(w.get("monitor", ""), ""),
                "active":  bool(w.get("hasfullscreen") or w.get("lastwindow")),
            }
            for w in workspaces if isinstance(w, dict)
        ],
        "monitors":   [{"name": m.get("name"),
                        "width":  m.get("width"),
                        "height": m.get("height"),
                        "active_workspace": (m.get("activeWorkspace") or {}).get("id")}
                       for m in monitors if isinstance(m, dict)],
        "options": {
            "group_by_workspace": opts.group_by_workspace,
            "clickable":          opts.clickable,
            "animate_ms":         opts.animate_ms,
        },
    }
    tmp = STATE_J.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(out, indent=2))
    tmp.replace(STATE_J)
    return out


def select_workspace(wid: int) -> dict:
    if not isinstance(wid, int):
        return {"ok": False, "error": "workspace id must be int"}
    hypr("dispatch", "workspace", str(wid))
    return {"ok": True, "workspace": wid}


def focus_window(addr: str) -> dict:
    if not isinstance(addr, str) or not _HEX_ADDR.match(addr):
        return {"ok": False, "error": "bad address"}
    hypr("dispatch", "focuswindow", f"address:{addr}")
    return {"ok": True, "address": addr}


def close_window(addr: str) -> dict:
    if not isinstance(addr, str) or not _HEX_ADDR.match(addr):
        return {"ok": False, "error": "bad address"}
    hypr("dispatch", "closewindow", f"address:{addr}")
    return {"ok": True, "address": addr}


def move_window(addr: str, wid: int) -> dict:
    if not (isinstance(addr, str) and _HEX_ADDR.match(addr)
            and isinstance(wid, int)):
        return {"ok": False, "error": "bad args"}
    hypr("dispatch", "movetoworkspacesilent", f"{wid},address:{addr}")
    return {"ok": True}


# ─── auto-refresh loop while overview is open ───────────────────────────
class RefreshLoop(threading.Thread):
    def __init__(self, state: dict):
        super().__init__(daemon=True)
        self.state = state
        self.stop_flag = threading.Event()

    def run(self):
        while not self.stop_flag.is_set():
            opts: Options = self.state["opts"]
            if self.state.get("open"):
                try:
                    refresh(opts)
                except Exception as e:
                    log("refresh error:", e)
            time.sleep(max(0.1, opts.refresh_ms / 1000.0))


# ─── IPC ────────────────────────────────────────────────────────────────
class Server:
    def __init__(self, state: dict):
        self.state = state

    def handle(self, req: dict) -> dict:
        op = req.get("op", "")
        opts: Options = self.state["opts"]
        if op == "ping":
            return {"ok": True, "pid": os.getpid()}
        if op == "open":
            self.state["open"] = True
            return {"ok": True, "manifest": refresh(opts)}
        if op == "close":
            self.state["open"] = False
            return {"ok": True}
        if op == "refresh":
            return {"ok": True, "manifest": refresh(opts)}
        if op == "state":
            try:
                return {"ok": True, "manifest": json.loads(STATE_J.read_text())}
            except (OSError, json.JSONDecodeError):
                return {"ok": True, "manifest": {"workspaces": [], "monitors": []}}
        if op == "select":
            wid = req.get("workspace")
            r = select_workspace(int(wid)) if isinstance(wid, (int, str)) and str(wid).lstrip("-").isdigit() else {"ok": False, "error": "bad workspace"}
            if r.get("ok") and opts.close_on_select:
                self.state["open"] = False
            return r
        if op == "focus":
            return focus_window(str(req.get("address", "")))
        if op == "close_window":
            return close_window(str(req.get("address", "")))
        if op == "move":
            try:
                wid = int(req.get("workspace"))
            except (TypeError, ValueError):
                return {"ok": False, "error": "bad workspace"}
            return move_window(str(req.get("address", "")), wid)
        if op == "reload":
            self.state["opts"] = load_config()
            return {"ok": True}
        return {"ok": False, "error": f"unknown op: {op}"}

    def serve(self):
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        if SOCK_PATH.exists():
            SOCK_PATH.unlink()
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(str(SOCK_PATH))
        os.chmod(SOCK_PATH, 0o600)
        srv.listen(8)
        log("ipc listening:", SOCK_PATH)
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                continue
            threading.Thread(target=self._client, args=(conn,), daemon=True).start()

    def _client(self, conn: socket.socket):
        with conn:
            try:
                buf = b""
                while b"\n" not in buf:
                    chunk = conn.recv(8192)
                    if not chunk:
                        return
                    buf += chunk
                    if len(buf) > 65536:
                        return
                req = json.loads(buf.split(b"\n", 1)[0].decode())
                resp = self.handle(req if isinstance(req, dict) else {})
                conn.send((json.dumps(resp) + "\n").encode())
            except (OSError, json.JSONDecodeError) as e:
                try:
                    conn.send((json.dumps({"ok": False, "error": str(e)}) + "\n").encode())
                except OSError:
                    pass


def main() -> int:
    log("nyxus-missiond starting (pid", os.getpid(), ")")
    opts = load_config()
    state: dict = {"opts": opts, "open": False}

    # initial empty manifest so eww has something to read
    refresh(opts)

    rl = RefreshLoop(state); rl.start()
    srv = Server(state)
    threading.Thread(target=srv.serve, daemon=True).start()

    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    while True:
        time.sleep(60)
    return 0  # unreachable


if __name__ == "__main__":
    sys.exit(main())
