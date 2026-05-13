#!/usr/bin/env python3
"""
NYXUS · nyxus-dockd
====================

Long-running user-session daemon that drives the NYXUS dock.

Responsibilities
----------------
1. Connect to Hyprland IPC (events socket `.socket2.sock`) and maintain
   a live model of all client windows: address, app_id (class), title,
   workspace, focused, urgent.
2. Read pinned apps, recents, layout, magnification and behaviour from
   `~/.config/nyxus/dock.toml`. Hot-reload on SIGHUP and on file mtime
   change (poll once per second — cheap).
3. Maintain a bounded LRU of recently-launched apps in
   `~/.local/state/nyxus/dock-recents.json`.
4. Poll lightweight sources every N seconds: trash count, swaync badge
   counts per app (best-effort, falls back to 0), workspace count.
5. Compute "live icon" overrides: today's day-of-month for Calendar,
   current temp for Weather (cached weather.json from eww), HH:MM for
   Clock — all returned as small inline SVG strings so eww can render
   without extra IO.
6. Emit a single canonical state JSON to
   `$XDG_RUNTIME_DIR/nyxus-dock/state.json` (atomic write) and a
   stream-mode line on stdout so eww `deflisten` can subscribe.
7. Honour `nyxus-dock` CLI commands over a small unix socket at
   `$XDG_RUNTIME_DIR/nyxus-dock/cmd.sock`: pin, unpin, reorder,
   focus, quit, reveal-trash, reload.

The daemon is restart-safe; eww never crashes if the daemon dies,
it just stops getting fresh state until systemd restarts the unit.

Lives at: /opt/nyxus/nyxus_dockd.py
Entry:    /usr/local/bin/nyxus-dockd  (symlink installed by airootfs)

(c) 2026 JOSEPH SIERENGOWSKI — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import argparse
import errno
import json
import logging
import os
import signal
import socket
import subprocess
import sys
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

try:
    import tomllib  # py 3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

LOG = logging.getLogger("nyxus-dockd")

# ────────────────────────────────────────────────────────────────────────────
# Paths & constants
# ────────────────────────────────────────────────────────────────────────────
HOME = Path(os.path.expanduser("~"))
CONFIG_PATH = HOME / ".config" / "nyxus" / "dock.toml"
STATE_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "nyxus-dock"
STATE_FILE = STATE_DIR / "state.json"
CMD_SOCK = STATE_DIR / "cmd.sock"
RECENTS_FILE = HOME / ".local" / "state" / "nyxus" / "dock-recents.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "general": {
        "position": "bottom",            # bottom | left | right
        "size": 56,                      # icon px at rest
        "magnification_enabled": True,
        "magnification_max": 1.65,       # scale multiplier of hovered icon
        "magnification_falloff": 2,      # neighbours that get partial bump
        "auto_hide": False,
        "auto_hide_reveal_px": 4,
        "show_recents": True,
        "recents_limit": 3,
        "show_trash": True,
        "show_running_indicator": True,
        "show_badges": True,
        "live_icons": True,
        "follow_cursor_monitor": False,  # else stays on primary
        "monitors": ["primary"],         # ["primary"] | ["all"] | ["DP-1","HDMI-A-1"]
        "section_dividers": True,
        "smart_focus_indicator": True,
    },
    "pinned": [
        {"id": "nyxus-launcher", "exec": "python3 ~/.nyxus/nyxus_launcher.py", "icon": "nyxus-launcher"},
        {"id": "firefox", "exec": "firefox", "icon": "firefox"},
        {"id": "nautilus", "exec": "nautilus", "icon": "system-file-manager"},
        {"id": "nyxus-notepad", "exec": "python3 ~/.nyxus/nyxus_notepad.py", "icon": "accessories-text-editor"},
        {"id": "nyxus-control", "exec": "python3 ~/.nyxus/nyxus_control.py", "icon": "preferences-system"},
        {"id": "nyxus-store", "exec": "python3 ~/.nyxus/nyxus_store.py", "icon": "system-software-install"},
        {"id": "alacritty", "exec": "alacritty", "icon": "utilities-terminal"},
    ],
    "stacks": [
        {"id": "downloads", "label": "Downloads",
         "path": "~/Downloads", "view": "fan",
         "icon": "folder-download"},
    ],
    "drop_zones": {
        "firefox": {"action": "open"},
        "nyxus-notepad": {"action": "open"},
    },
    "live_icons": {
        "calendar": {"enabled": True, "icon": "io.nyxus.calendar"},
        "clock": {"enabled": False, "icon": "io.nyxus.clock"},
        "weather": {"enabled": False, "icon": "io.nyxus.weather"},
    },
}

# ────────────────────────────────────────────────────────────────────────────
# Hyprland IPC
# ────────────────────────────────────────────────────────────────────────────
HYPR_SIG = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
HYPR_RUNTIME = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "hypr" / HYPR_SIG
HYPR_EVENT_SOCK = HYPR_RUNTIME / ".socket2.sock"
HYPR_CMD_SOCK = HYPR_RUNTIME / ".socket.sock"


def hypr_cmd(line: str) -> str:
    """Send a command over hyprctl IPC and return raw response."""
    if not HYPR_CMD_SOCK.exists():
        return ""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(str(HYPR_CMD_SOCK))
            s.sendall(line.encode())
            chunks = []
            while True:
                data = s.recv(8192)
                if not data:
                    break
                chunks.append(data)
            return b"".join(chunks).decode(errors="replace")
    except OSError as e:
        LOG.debug("hypr_cmd %s failed: %s", line, e)
        return ""


def hypr_clients() -> list[dict[str, Any]]:
    raw = hypr_cmd("j/clients")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


def hypr_active_window() -> dict[str, Any]:
    raw = hypr_cmd("j/activewindow")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def hypr_monitors() -> list[dict[str, Any]]:
    raw = hypr_cmd("j/monitors")
    if not raw:
        return []
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return []


# ────────────────────────────────────────────────────────────────────────────
# State model
# ────────────────────────────────────────────────────────────────────────────
@dataclass
class DockEntry:
    id: str                       # stable key (pinned id, or app_id for runtime)
    label: str
    icon: str                     # icon name (XDG) or absolute path
    pinned: bool = False
    running: bool = False
    focused: bool = False
    urgent: bool = False
    badge: int = 0                # notification count
    addresses: list[str] = field(default_factory=list)  # window addrs
    workspace: int | None = None
    other_workspace: bool = False  # running but not on focused workspace
    recent: bool = False
    section: str = "pinned"       # pinned | recent | running | stack | trash
    exec_cmd: str | None = None
    live_overlay: str | None = None  # text overlay (e.g. day number)
    drop_zone: str | None = None   # action key when file dropped


# ────────────────────────────────────────────────────────────────────────────
# Recents tracking
# ────────────────────────────────────────────────────────────────────────────
class Recents:
    def __init__(self, limit: int = 10):
        self.limit = limit
        self.path = RECENTS_FILE
        self.items: OrderedDict[str, float] = OrderedDict()
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text())
            for k, v in data.get("items", []):
                self.items[k] = v
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(json.dumps({"items": list(self.items.items())}))
            tmp.replace(self.path)
        except OSError as e:
            LOG.debug("recents save failed: %s", e)

    def touch(self, app_id: str) -> None:
        if not app_id:
            return
        self.items.pop(app_id, None)
        self.items[app_id] = time.time()
        while len(self.items) > self.limit:
            self.items.popitem(last=False)
        self.save()

    def latest(self, n: int) -> list[str]:
        return list(reversed(list(self.items.keys())))[:n]


# ────────────────────────────────────────────────────────────────────────────
# Badges & trash
# ────────────────────────────────────────────────────────────────────────────
def trash_count() -> int:
    p = HOME / ".local" / "share" / "Trash" / "files"
    try:
        return sum(1 for _ in p.iterdir())
    except (FileNotFoundError, NotADirectoryError, OSError):
        return 0


def swaync_badges() -> dict[str, int]:
    """Return {app_id: count} of pending notifications. Best-effort."""
    out: dict[str, int] = {}
    try:
        raw = subprocess.check_output(
            ["swaync-client", "-lN"], stderr=subprocess.DEVNULL, timeout=1.5
        ).decode()
        data = json.loads(raw)
        for n in data.get("notifications", []) if isinstance(data, dict) else data:
            app = (n.get("app", "") or n.get("app-name", "")).lower()
            if app:
                out[app] = out.get(app, 0) + 1
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError,
            FileNotFoundError, json.JSONDecodeError):
        pass
    return out


# ────────────────────────────────────────────────────────────────────────────
# Live icons
# ────────────────────────────────────────────────────────────────────────────
def live_overlay_calendar() -> str:
    return time.strftime("%-d")


def live_overlay_clock() -> str:
    return time.strftime("%H:%M")


def live_overlay_weather() -> str:
    cache = HOME / ".cache" / "nyxus-eww" / "weather.json"
    try:
        data = json.loads(cache.read_text())
        return str(data.get("temp", "—"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return ""


# ────────────────────────────────────────────────────────────────────────────
# Daemon core
# ────────────────────────────────────────────────────────────────────────────
class DockDaemon:
    def __init__(self) -> None:
        self.config = DEFAULT_CONFIG.copy()
        self.config_mtime = 0.0
        self.recents = Recents()
        self.clients: dict[str, dict[str, Any]] = {}
        self.active_addr: str | None = None
        self.workspaces_active: int = 1
        self.lock = threading.Lock()
        self.stop = threading.Event()
        # Long-lived `op:"subscribe"` connections that get every state
        # change pushed as a JSON line. cmd_loop adds them; publish()
        # writes to them; both go through subscribers_lock.
        self.subscribers: list[socket.socket] = []
        self.subscribers_lock = threading.Lock()
        self.publish_lock = threading.Lock()  # serialise publish() across threads
        self.last_state_hash: int = 0
        self.last_state_text: str = ""

    # ── config ──────────────────────────────────────────────────────────
    def load_config(self) -> None:
        try:
            mtime = CONFIG_PATH.stat().st_mtime
            if mtime == self.config_mtime:
                return
            with CONFIG_PATH.open("rb") as f:
                user = tomllib.load(f)
            cfg = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
            for section, vals in user.items():
                if isinstance(vals, dict) and isinstance(cfg.get(section), dict):
                    cfg[section].update(vals)
                else:
                    cfg[section] = vals
            self.config = cfg
            self.config_mtime = mtime
            LOG.info("config reloaded from %s", CONFIG_PATH)
        except FileNotFoundError:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            self._write_default_config()
        except (OSError, tomllib.TOMLDecodeError) as e:
            LOG.warning("config load error: %s — using defaults", e)

    def _write_default_config(self) -> None:
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(_DEFAULT_TOML)
            self.config_mtime = CONFIG_PATH.stat().st_mtime
            LOG.info("default config written to %s", CONFIG_PATH)
        except OSError as e:
            LOG.warning("could not write default config: %s", e)

    # ── hypr event loop ─────────────────────────────────────────────────
    def hypr_event_loop(self) -> None:
        backoff = 0.5
        while not self.stop.is_set():
            if not HYPR_EVENT_SOCK.exists():
                LOG.debug("hyprland socket not present yet")
                time.sleep(backoff)
                backoff = min(backoff * 1.5, 5.0)
                continue
            try:
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                    s.connect(str(HYPR_EVENT_SOCK))
                    s.settimeout(1.0)
                    backoff = 0.5
                    self._refresh_full()
                    buf = b""
                    while not self.stop.is_set():
                        try:
                            data = s.recv(4096)
                        except socket.timeout:
                            continue
                        if not data:
                            break
                        buf += data
                        while b"\n" in buf:
                            line, buf = buf.split(b"\n", 1)
                            self._handle_event(line.decode(errors="replace"))
            except OSError as e:
                LOG.debug("hypr socket loop: %s", e)
                time.sleep(backoff)
                backoff = min(backoff * 1.5, 5.0)

    def _handle_event(self, line: str) -> None:
        if ">>" not in line:
            return
        evt, _, payload = line.partition(">>")
        evt = evt.strip()
        # Most events warrant a quick refresh. We could be granular but the
        # cost is one IPC round-trip; cheaper than tracking every field.
        if evt in {
            "openwindow", "closewindow", "movewindow", "windowtitle",
            "activewindow", "activewindowv2", "urgent", "workspace",
            "focusedmon", "monitorremoved", "monitoradded",
        }:
            self._refresh_full()
            if evt == "openwindow":
                # payload: addr,workspace,class,title
                parts = payload.split(",", 3)
                if len(parts) >= 3:
                    self.recents.touch(parts[2].strip().lower())

    def _refresh_full(self) -> None:
        clients = hypr_clients()
        active = hypr_active_window()
        with self.lock:
            self.clients = {c["address"]: c for c in clients if "address" in c}
            self.active_addr = active.get("address")
            self.workspaces_active = (
                active.get("workspace", {}).get("id", 1)
                if isinstance(active.get("workspace"), dict) else 1
            )
        self.publish()

    # ── state composition ───────────────────────────────────────────────
    def compose_state(self) -> dict[str, Any]:
        gen = self.config["general"]
        pinned_cfg = self.config.get("pinned", [])
        stacks_cfg = self.config.get("stacks", [])
        drop_cfg = self.config.get("drop_zones", {})
        live_cfg = self.config.get("live_icons", {})

        with self.lock:
            clients = list(self.clients.values())
            active = self.active_addr
            ws_active = self.workspaces_active

        # group clients by app_id (lowercase class)
        by_app: dict[str, list[dict[str, Any]]] = {}
        for c in clients:
            app = (c.get("class") or "").strip().lower()
            if not app:
                continue
            by_app.setdefault(app, []).append(c)

        badges = swaync_badges() if gen.get("show_badges", True) else {}

        entries: list[DockEntry] = []
        seen_apps: set[str] = set()

        for p in pinned_cfg:
            pid = (p.get("id") or "").lower()
            running_clients = by_app.get(pid, [])
            addrs = [c.get("address", "") for c in running_clients]
            focused = active is not None and active in addrs
            urgent = any(c.get("urgent") for c in running_clients)
            ws_match = any(
                (c.get("workspace") or {}).get("id") == ws_active
                for c in running_clients
            )
            entry = DockEntry(
                id=pid,
                label=p.get("label", pid),
                icon=p.get("icon", pid),
                pinned=True,
                running=bool(running_clients),
                focused=focused,
                urgent=urgent,
                badge=badges.get(pid, 0),
                addresses=addrs,
                workspace=(running_clients[0].get("workspace") or {}).get("id")
                          if running_clients else None,
                other_workspace=bool(running_clients) and not ws_match,
                section="pinned",
                exec_cmd=p.get("exec"),
                drop_zone=(drop_cfg.get(pid) or {}).get("action"),
            )
            # live overlay
            if gen.get("live_icons", True) and live_cfg:
                if pid == live_cfg.get("calendar", {}).get("icon", "") and \
                   live_cfg["calendar"].get("enabled"):
                    entry.live_overlay = live_overlay_calendar()
                elif pid == live_cfg.get("clock", {}).get("icon", "") and \
                     live_cfg["clock"].get("enabled"):
                    entry.live_overlay = live_overlay_clock()
                elif pid == live_cfg.get("weather", {}).get("icon", "") and \
                     live_cfg["weather"].get("enabled"):
                    entry.live_overlay = live_overlay_weather()
            entries.append(entry)
            seen_apps.add(pid)

        # recents (running but not pinned, OR launched-recently apps)
        if gen.get("show_recents", True):
            limit = int(gen.get("recents_limit", 3))
            for r in self.recents.latest(limit * 2):
                if len(entries) >= len(pinned_cfg) + limit:
                    break
                if r in seen_apps:
                    continue
                running_clients = by_app.get(r, [])
                addrs = [c.get("address", "") for c in running_clients]
                entries.append(DockEntry(
                    id=r,
                    label=r,
                    icon=r,
                    pinned=False,
                    running=bool(running_clients),
                    focused=active in addrs if active else False,
                    badge=badges.get(r, 0),
                    addresses=addrs,
                    section="recent",
                    recent=True,
                ))
                seen_apps.add(r)

        # running (not pinned, not in recents already)
        for app, cl in by_app.items():
            if app in seen_apps:
                continue
            addrs = [c.get("address", "") for c in cl]
            entries.append(DockEntry(
                id=app, label=app, icon=app,
                running=True,
                focused=active in addrs if active else False,
                urgent=any(c.get("urgent") for c in cl),
                badge=badges.get(app, 0),
                addresses=addrs,
                section="running",
            ))
            seen_apps.add(app)

        # stacks (folder shortcuts that fan-out)
        stacks = []
        for s in stacks_cfg:
            path = Path(os.path.expanduser(s.get("path", "")))
            count = 0
            try:
                count = sum(1 for _ in path.iterdir())
            except (FileNotFoundError, NotADirectoryError, OSError):
                pass
            stacks.append({
                "id": s.get("id"),
                "label": s.get("label"),
                "icon": s.get("icon", "folder"),
                "path": str(path),
                "view": s.get("view", "fan"),
                "count": count,
            })

        # trash
        trash = None
        if gen.get("show_trash", True):
            tc = trash_count()
            trash = {
                "id": "trash",
                "label": "Trash" if tc == 0 else f"Trash ({tc})",
                "icon": "user-trash" if tc == 0 else "user-trash-full",
                "count": tc,
            }

        return {
            "schema": 1,
            "ts": time.time(),
            "general": gen,
            "entries": [asdict(e) for e in entries],
            "stacks": stacks,
            "trash": trash,
            "active_workspace": ws_active,
        }

    def publish(self) -> None:
        # Serialise across the hypr/event, periodic, and cmd threads. Without
        # this lock two publishers can both observe stale `last_state_hash`,
        # race the atomic file write, and double-fan-out to subscribers.
        with self.publish_lock:
            state = self.compose_state()
            text = json.dumps(state, separators=(",", ":"))
            h = hash(text)
            if h == self.last_state_hash:
                return
            self.last_state_hash = h
            self.last_state_text = text
            payload = (text + "\n").encode()
            # atomic write
            try:
                STATE_DIR.mkdir(parents=True, exist_ok=True)
                tmp = STATE_FILE.with_suffix(".tmp")
                tmp.write_text(text)
                tmp.replace(STATE_FILE)
            except OSError as e:
                LOG.warning("state write failed: %s", e)
        # fan-out outside publish_lock so a slow subscriber can't stall publishes.
        with self.subscribers_lock:
            dead: list[socket.socket] = []
            for sub in self.subscribers:
                try:
                    sub.sendall(payload)
                except (BrokenPipeError, ConnectionResetError, OSError):
                    dead.append(sub)
            for d in dead:
                try:
                    self.subscribers.remove(d)
                except ValueError:
                    pass
                try:
                    d.close()
                except OSError:
                    pass

    # ── periodic refresh (badges/trash/live overlay) ────────────────────
    def periodic_loop(self) -> None:
        while not self.stop.is_set():
            self.load_config()
            self.publish()
            self.stop.wait(2.0)

    # ── command socket ──────────────────────────────────────────────────
    def cmd_loop(self) -> None:
        try:
            CMD_SOCK.unlink()
        except FileNotFoundError:
            pass
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            srv.bind(str(CMD_SOCK))
            os.chmod(CMD_SOCK, 0o600)
            srv.listen(8)
            srv.settimeout(1.0)
        except OSError as e:
            LOG.warning("cmd socket bind failed: %s", e)
            return

        while not self.stop.is_set():
            try:
                conn, _ = srv.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                conn.settimeout(2.0)
                req = conn.recv(8192).decode().strip()
                # `op:"subscribe"` opts out of the request/response model:
                # the connection becomes a long-lived push channel that
                # `publish()` writes JSON lines to whenever state changes.
                # We hand it to the subscribers list and DON'T close it.
                try:
                    obj = json.loads(req)
                except json.JSONDecodeError:
                    obj = {}
                if obj.get("op") == "subscribe":
                    initial = self.last_state_text or json.dumps(self.compose_state())
                    try:
                        conn.settimeout(None)
                        conn.sendall((initial + "\n").encode())
                    except OSError:
                        try: conn.close()
                        except OSError: pass
                        continue
                    with self.subscribers_lock:
                        self.subscribers.append(conn)
                    continue  # do NOT close
                resp = self._handle_cmd(req)
                conn.sendall((resp + "\n").encode())
            except OSError as e:
                LOG.debug("cmd conn: %s", e)
                try: conn.close()
                except OSError: pass
                continue
            try:
                conn.close()
            except OSError:
                pass

        try:
            srv.close()
            CMD_SOCK.unlink(missing_ok=True)
        except OSError:
            pass

    def _handle_cmd(self, req: str) -> str:
        try:
            obj = json.loads(req)
        except json.JSONDecodeError:
            return json.dumps({"ok": False, "error": "bad-json"})
        op = obj.get("op", "")
        try:
            if op == "ping":
                return json.dumps({"ok": True, "pong": time.time()})
            if op == "state":
                return self.last_state_text or json.dumps(self.compose_state())
            if op == "reload":
                self.config_mtime = 0.0
                self.load_config()
                self.publish()
                return json.dumps({"ok": True})
            if op == "pin":
                return self._do_pin(obj)
            if op == "unpin":
                return self._do_unpin(obj.get("id", ""))
            if op == "reorder":
                return self._do_reorder(obj.get("ids", []))
            if op == "focus":
                return self._do_focus(obj.get("address", ""))
            if op == "launch":
                return self._do_launch(obj.get("id", ""))
            if op == "quit-app":
                return self._do_quit_app(obj.get("id", ""))
            return json.dumps({"ok": False, "error": f"unknown-op:{op}"})
        except Exception as e:  # pragma: no cover  - keep daemon alive
            LOG.exception("cmd handler crashed: %s", e)
            return json.dumps({"ok": False, "error": str(e)})

    def _do_pin(self, obj: dict[str, Any]) -> str:
        pid = (obj.get("id") or "").lower()
        if not pid:
            return json.dumps({"ok": False, "error": "no-id"})
        for p in self.config.get("pinned", []):
            if (p.get("id") or "").lower() == pid:
                return json.dumps({"ok": True, "already": True})
        new = {
            "id": pid,
            "exec": obj.get("exec") or pid,
            "icon": obj.get("icon") or pid,
            "label": obj.get("label") or pid,
        }
        self.config.setdefault("pinned", []).append(new)
        self._persist_config()
        self.publish()
        return json.dumps({"ok": True})

    def _do_unpin(self, pid: str) -> str:
        pid = pid.lower()
        before = self.config.get("pinned", [])
        after = [p for p in before if (p.get("id") or "").lower() != pid]
        if len(before) == len(after):
            return json.dumps({"ok": False, "error": "not-pinned"})
        self.config["pinned"] = after
        self._persist_config()
        self.publish()
        return json.dumps({"ok": True})

    def _do_reorder(self, ids: list[str]) -> str:
        ids_l = [i.lower() for i in ids]
        existing = {p.get("id", "").lower(): p for p in self.config.get("pinned", [])}
        new = [existing[i] for i in ids_l if i in existing]
        # append any pinned not in supplied list (defensive)
        for p in self.config.get("pinned", []):
            if p.get("id", "").lower() not in ids_l:
                new.append(p)
        self.config["pinned"] = new
        self._persist_config()
        self.publish()
        return json.dumps({"ok": True, "n": len(new)})

    def _do_focus(self, addr: str) -> str:
        if not addr:
            return json.dumps({"ok": False, "error": "no-addr"})
        hypr_cmd(f"dispatch focuswindow address:{addr}")
        return json.dumps({"ok": True})

    def _do_launch(self, pid: str) -> str:
        pid = pid.lower()
        for p in self.config.get("pinned", []):
            if (p.get("id") or "").lower() == pid:
                cmd = p.get("exec", pid)
                try:
                    subprocess.Popen(
                        ["sh", "-c", os.path.expanduser(cmd)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                        start_new_session=True,
                    )
                    self.recents.touch(pid)
                    return json.dumps({"ok": True})
                except OSError as e:
                    return json.dumps({"ok": False, "error": str(e)})
        # fallback: try executing pid as a command
        try:
            subprocess.Popen(
                [pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            self.recents.touch(pid)
            return json.dumps({"ok": True})
        except OSError as e:
            return json.dumps({"ok": False, "error": str(e)})

    def _do_quit_app(self, pid: str) -> str:
        pid = pid.lower()
        with self.lock:
            addrs = [
                c.get("address", "")
                for c in self.clients.values()
                if (c.get("class") or "").lower() == pid
            ]
        for a in addrs:
            if a:
                hypr_cmd(f"dispatch closewindow address:{a}")
        return json.dumps({"ok": True, "closed": len(addrs)})

    def _persist_config(self) -> None:
        try:
            CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
            CONFIG_PATH.write_text(_render_toml(self.config))
            self.config_mtime = CONFIG_PATH.stat().st_mtime
        except OSError as e:
            LOG.warning("persist config failed: %s", e)

    # ── lifecycle ───────────────────────────────────────────────────────
    def run(self) -> None:
        self.load_config()
        threads = [
            threading.Thread(target=self.hypr_event_loop, daemon=True, name="hypr"),
            threading.Thread(target=self.periodic_loop,   daemon=True, name="poll"),
            threading.Thread(target=self.cmd_loop,        daemon=True, name="cmd"),
        ]
        for t in threads:
            t.start()
        signal.signal(signal.SIGTERM, lambda *_: self.stop.set())
        signal.signal(signal.SIGINT,  lambda *_: self.stop.set())
        signal.signal(signal.SIGHUP,  lambda *_: setattr(self, "config_mtime", 0.0))
        # initial publish even before hypr connects (so eww renders pinned)
        self.publish()
        while not self.stop.is_set():
            time.sleep(0.5)
        for t in threads:
            t.join(timeout=1.0)


# ────────────────────────────────────────────────────────────────────────────
# TOML rendering (small enough to hand-roll; avoids tomli-w dep)
# ────────────────────────────────────────────────────────────────────────────
def _toml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        if all(isinstance(x, str) for x in v):
            inner = ", ".join(f"\"{x}\"" for x in v)
            return f"[{inner}]"
        return json.dumps(v)
    return json.dumps(str(v))


def _render_toml(cfg: dict[str, Any]) -> str:
    lines: list[str] = ["# NYXUS dock config — managed by nyxus-dockd", ""]
    # scalars/dicts first
    for section, value in cfg.items():
        if isinstance(value, dict):
            lines.append(f"[{section}]")
            for k, v in value.items():
                if isinstance(v, dict):
                    lines.append(f"\n[{section}.{k}]")
                    for kk, vv in v.items():
                        lines.append(f"{kk} = {_toml_value(vv)}")
                else:
                    lines.append(f"{k} = {_toml_value(v)}")
            lines.append("")
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, dict):
                    lines.append(f"[[{section}]]")
                    for k, v in item.items():
                        lines.append(f"{k} = {_toml_value(v)}")
                    lines.append("")
    return "\n".join(lines).rstrip() + "\n"


_DEFAULT_TOML = _render_toml(DEFAULT_CONFIG)


# ────────────────────────────────────────────────────────────────────────────
# CLI entry
# ────────────────────────────────────────────────────────────────────────────
def main() -> int:
    parser = argparse.ArgumentParser(prog="nyxus-dockd")
    parser.add_argument("--log-level", default="INFO")
    parser.add_argument("--watch", action="store_true",
                        help="run in watch mode: stream state to stdout (for eww deflisten)")
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    if args.watch:
        # subscribe to running daemon's state stream via cmd socket
        return _watch_mode()

    daemon = DockDaemon()
    daemon.run()
    return 0


def _watch_mode() -> int:
    """For eww `deflisten` — open a long-lived subscription to the daemon
    and print every JSON state line as it arrives. Reconnects on daemon
    restart with exponential backoff."""
    backoff = 0.5
    while True:
        try:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.connect(str(CMD_SOCK))
                s.sendall(b'{"op":"subscribe"}')
                s.settimeout(None)
                backoff = 0.5
                buf = b""
                while True:
                    chunk = s.recv(65536)
                    if not chunk:
                        break  # daemon went away
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        if line:
                            sys.stdout.write(line.decode(errors="replace") + "\n")
                            sys.stdout.flush()
        except (FileNotFoundError, ConnectionRefusedError, OSError):
            pass
        except KeyboardInterrupt:
            return 0
        time.sleep(backoff)
        backoff = min(backoff * 1.5, 5.0)


if __name__ == "__main__":
    sys.exit(main())
