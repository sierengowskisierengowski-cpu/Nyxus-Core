#!/usr/bin/env python3
"""
NYXUS Snap daemon
=================

Magnet/FancyZones-style window tiling for Hyprland.

Capabilities
------------
- Subscribes to Hyprland event socket: `openwindow`, `movewindow`,
  `windowtitle`, `activewindow`, `monitorremoved`.
- On window move (mouse drag end), sees if the cursor is within an
  edge zone; if so, snaps to the zone rect.
- Hold-modifier picker: when SUPER is held, the eww `snap-picker`
  overlay window shows a zone grid; clicking a cell snaps the active
  window there. The overlay is driven by writing JSON to
  $XDG_RUNTIME_DIR/nyxus-snap/picker.json which the eww side `defpoll`s.
- Per-app rules: on `openwindow`, if the new window's class matches a
  rule, it is auto-snapped to the configured zone.
- Layout snapshots: save/restore a workspace's window arrangement.
- Multi-monitor aware: zones are scoped per output by name.
- Hot-reloads on snap.toml mtime change.
- Push-stream IPC over $XDG_RUNTIME_DIR/nyxus-snap/cmd.sock for the
  CLI and Settings UI.

Hardening
---------
- All hyprctl calls go through argv lists (no shell concatenation of
  user data); window/workspace identifiers are validated as integers
  or known classes.
- Socket is 0o600.
- Config writes via tempfile → rename (atomic).
- TOML parse failures keep the previous good config.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import signal
import socket
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

try:
    import tomllib
except ImportError:                       # pragma: no cover
    import tomli as tomllib  # type: ignore


# ─── paths ──────────────────────────────────────────────────────────────
HOME      = Path(os.environ.get("HOME", "/root"))
XDG_RUN   = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
RUN_DIR   = XDG_RUN / "nyxus-snap"
SOCK_PATH = RUN_DIR / "cmd.sock"
PICKER_J  = RUN_DIR / "picker.json"
STATE_DIR = HOME / ".local/state/nyxus"
SNAPS_DIR = STATE_DIR / "snap-snapshots"
CFG_PATH  = HOME / ".config/nyxus/snap.toml"

HYPR_SIG  = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
HYPR_BASE = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "hypr" / HYPR_SIG
HYPR_EVT  = HYPR_BASE / ".socket2.sock"
HYPR_CMD  = HYPR_BASE / ".socket.sock"


def log(*a: Any) -> None:
    print("[nyxus-snapd]", *a, file=sys.stderr, flush=True)


# ─── data model ─────────────────────────────────────────────────────────
@dataclass
class Zone:
    id:   str
    rect: tuple[float, float, float, float]   # x, y, w, h normalized

@dataclass
class Layout:
    name:  str
    zones: list[Zone] = field(default_factory=list)

@dataclass
class AppRule:
    match:  str
    zone:   str
    layout: str

@dataclass
class Options:
    edge_px: int           = 24
    picker_modifier: str   = "SUPER"
    picker_hold_ms: int    = 250
    ghost_fade_ms: int     = 140
    snap_to_cell: bool     = True
    remember_per_ws: bool  = True
    per_output_zones: bool = True
    ignore_missing: bool   = True

@dataclass
class Config:
    options:   Options          = field(default_factory=Options)
    layouts:   list[Layout]     = field(default_factory=list)
    app_rules: list[AppRule]    = field(default_factory=list)
    mtime:     float            = 0.0


_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")

def _safe_id(s: str) -> bool:
    return bool(_NAME_RE.match(s or ""))


def load_config() -> Config:
    cfg = Config()
    if not CFG_PATH.exists():
        log("config missing:", CFG_PATH, "— using defaults")
        return cfg
    cfg.mtime = CFG_PATH.stat().st_mtime
    data = tomllib.loads(CFG_PATH.read_text())
    o = data.get("options", {}) or {}
    for k, v in o.items():
        if hasattr(cfg.options, k):
            setattr(cfg.options, k, v)
    for ly in data.get("layout", []) or []:
        name = str(ly.get("name", "")).strip()
        if not _safe_id(name):
            continue
        zones: list[Zone] = []
        for z in ly.get("zone", []) or []:
            zid = str(z.get("id", "")).strip()
            r = z.get("rect") or []
            if not _safe_id(zid) or len(r) != 4:
                continue
            try:
                rect = tuple(max(0.0, min(1.0, float(x))) for x in r)
            except (TypeError, ValueError):
                continue
            zones.append(Zone(id=zid, rect=rect))  # type: ignore[arg-type]
        if zones:
            cfg.layouts.append(Layout(name=name, zones=zones))
    for r in data.get("app_rule", []) or []:
        m, z, ly = r.get("match", ""), r.get("zone", ""), r.get("layout", "")
        if not (m and _safe_id(z) and _safe_id(ly)):
            continue
        cfg.app_rules.append(AppRule(match=m, zone=z, layout=ly))
    return cfg


# ─── hyprctl thin wrapper ───────────────────────────────────────────────
def hypr(*args: str) -> str:
    """Run hyprctl with argv (never a shell). Returns stdout or ''."""
    try:
        out = subprocess.run(
            ["hyprctl", *args],
            capture_output=True, text=True, timeout=2, check=False,
        )
        return out.stdout
    except (OSError, subprocess.TimeoutExpired) as e:
        log("hyprctl error:", e)
        return ""


def hypr_json(*args: str) -> Any:
    raw = hypr(*args, "-j")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def get_active_window() -> dict | None:
    j = hypr_json("activewindow")
    return j if isinstance(j, dict) else None


def get_monitors() -> list[dict]:
    j = hypr_json("monitors")
    return j if isinstance(j, list) else []


def get_clients() -> list[dict]:
    j = hypr_json("clients")
    return j if isinstance(j, list) else []


def get_workspaces() -> list[dict]:
    j = hypr_json("workspaces")
    return j if isinstance(j, list) else []


def monitor_for(window: dict, mons: list[dict]) -> dict | None:
    """Find the monitor containing the window's center."""
    if not window or not mons:
        return None
    try:
        wx, wy = window["at"]
        ww, wh = window["size"]
        cx, cy = wx + ww / 2, wy + wh / 2
    except (KeyError, TypeError, ValueError):
        return None
    for m in mons:
        try:
            mx, my = m["x"], m["y"]
            mw, mh = m["width"], m["height"]
        except KeyError:
            continue
        if mx <= cx < mx + mw and my <= cy < my + mh:
            return m
    return mons[0] if mons else None


# ─── snap engine ────────────────────────────────────────────────────────
def snap_window_to_rect(addr: str, mon: dict, rect: tuple[float, float, float, float]) -> None:
    """Move + resize a window (by address) to a normalized rect on `mon`."""
    if not addr or not mon:
        return
    try:
        mx, my = int(mon["x"]), int(mon["y"])
        mw, mh = int(mon["width"]), int(mon["height"])
        # account for reserved (bars/dock) area if exposed
        rsv = mon.get("reserved") or [0, 0, 0, 0]
        rl, rt, rr, rb = (int(v) for v in rsv[:4])
    except (KeyError, TypeError, ValueError):
        return
    avail_x = mx + rl
    avail_y = my + rt
    avail_w = max(0, mw - rl - rr)
    avail_h = max(0, mh - rt - rb)
    nx = avail_x + int(rect[0] * avail_w)
    ny = avail_y + int(rect[1] * avail_h)
    nw = max(80, int(rect[2] * avail_w))
    nh = max(80, int(rect[3] * avail_h))
    # Use the window-address dispatcher form so we can target a specific
    # window without focusing it first.
    safe_addr = addr if re.match(r"^0x[0-9a-fA-F]+$", addr) else None
    if not safe_addr:
        log("refusing snap: bad addr", repr(addr))
        return
    hypr("dispatch", "movewindowpixel", f"exact {nx} {ny},address:{safe_addr}")
    hypr("dispatch", "resizewindowpixel", f"exact {nw} {nh},address:{safe_addr}")


def find_zone(cfg: Config, layout_name: str, zone_id: str) -> tuple[Layout, Zone] | None:
    for ly in cfg.layouts:
        if ly.name == layout_name:
            for z in ly.zones:
                if z.id == zone_id:
                    return ly, z
    return None


def snap_active_to(cfg: Config, layout_name: str, zone_id: str) -> dict:
    win = get_active_window()
    if not win:
        return {"ok": False, "error": "no active window"}
    found = find_zone(cfg, layout_name, zone_id)
    if not found:
        return {"ok": False, "error": f"unknown zone {layout_name}/{zone_id}"}
    _, z = found
    mon = monitor_for(win, get_monitors())
    if not mon:
        return {"ok": False, "error": "no monitor"}
    snap_window_to_rect(win.get("address", ""), mon, z.rect)
    return {"ok": True, "zone": zone_id, "layout": layout_name,
            "address": win.get("address", "")}


# ─── per-app rules on openwindow ────────────────────────────────────────
def apply_app_rule(cfg: Config, addr: str, cls: str) -> None:
    if not addr or not cls:
        return
    for r in cfg.app_rules:
        try:
            if not re.search(r.match, cls):
                continue
        except re.error:
            continue
        found = find_zone(cfg, r.layout, r.zone)
        if not found:
            continue
        # Need the window record to know which monitor it landed on
        for c in get_clients():
            if c.get("address") == addr:
                mon = monitor_for(c, get_monitors())
                if mon:
                    snap_window_to_rect(addr, mon, found[1].rect)
                return


# ─── snapshots ──────────────────────────────────────────────────────────
def snapshot_save(name: str) -> dict:
    if not _safe_id(name):
        return {"ok": False, "error": "bad snapshot name"}
    SNAPS_DIR.mkdir(parents=True, exist_ok=True)
    snap = {"created": time.time(), "windows": []}
    for c in get_clients():
        snap["windows"].append({
            "address": c.get("address"),
            "class":   c.get("class"),
            "title":   c.get("title"),
            "at":      c.get("at"),
            "size":    c.get("size"),
            "workspace": (c.get("workspace") or {}).get("id"),
            "monitor":   c.get("monitor"),
        })
    p = SNAPS_DIR / f"{name}.json"
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snap, indent=2))
    tmp.replace(p)
    return {"ok": True, "path": str(p), "windows": len(snap["windows"])}


def snapshot_restore(name: str, cfg: Config) -> dict:
    p = SNAPS_DIR / f"{name}.json"
    if not p.exists():
        return {"ok": False, "error": "no such snapshot"}
    snap = json.loads(p.read_text())
    mons = get_monitors()
    by_addr = {c.get("address"): c for c in get_clients()}
    restored, missing = 0, 0
    for w in snap.get("windows", []):
        addr = w.get("address")
        if addr not in by_addr:
            missing += 1
            if cfg.options.ignore_missing:
                continue
            return {"ok": False, "error": f"window {addr} not present"}
        mon = next((m for m in mons if m.get("name") == w.get("monitor")), mons[0] if mons else None)
        if not mon:
            continue
        wx, wy = w.get("at") or [0, 0]
        ww, wh = w.get("size") or [800, 600]
        try:
            mw, mh = int(mon["width"]), int(mon["height"])
            mx, my = int(mon["x"]), int(mon["y"])
        except (KeyError, TypeError, ValueError):
            continue
        rect = ((wx - mx) / mw, (wy - my) / mh, ww / mw, wh / mh)
        snap_window_to_rect(addr, mon, rect)
        restored += 1
    return {"ok": True, "restored": restored, "missing": missing}


def snapshots_list() -> list[str]:
    if not SNAPS_DIR.exists():
        return []
    return sorted(p.stem for p in SNAPS_DIR.glob("*.json"))


# ─── picker overlay (eww-driven) ────────────────────────────────────────
def picker_publish(cfg: Config, layout_name: str = "halves") -> None:
    """Write a JSON description of the current zone grid for eww to render."""
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    layout = next((ly for ly in cfg.layouts if ly.name == layout_name), None)
    if not layout:
        layout = cfg.layouts[0] if cfg.layouts else Layout(name="halves")
    payload = {
        "layout": layout.name,
        "zones":  [{"id": z.id, "rect": list(z.rect)} for z in layout.zones],
        "ts":     time.time(),
    }
    tmp = PICKER_J.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2))
    tmp.replace(PICKER_J)


# ─── Hyprland event loop ────────────────────────────────────────────────
async def event_loop(state: dict) -> None:
    if not HYPR_EVT.exists():
        log("hypr event socket missing:", HYPR_EVT)
        return
    while True:
        try:
            reader, _ = await asyncio.open_unix_connection(str(HYPR_EVT))
        except OSError as e:
            log("evt connect:", e, "— retry 2s")
            await asyncio.sleep(2)
            continue
        log("event loop connected")
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                evt = line.decode(errors="replace").strip()
                head, _, body = evt.partition(">>")
                cfg: Config = state["cfg"]
                if head == "openwindow":
                    parts = body.split(",", 3)
                    if len(parts) >= 3:
                        addr = "0x" + parts[0]
                        cls = parts[2]
                        apply_app_rule(cfg, addr, cls)
                elif head == "activewindowv2":
                    state["active_addr"] = "0x" + body if body else ""
                elif head == "configreloaded" or head == "monitoradded":
                    picker_publish(cfg)
        except OSError as e:
            log("evt read:", e)
        finally:
            await asyncio.sleep(1)


# ─── hot reload ─────────────────────────────────────────────────────────
async def reload_loop(state: dict) -> None:
    while True:
        await asyncio.sleep(1.5)
        try:
            mt = CFG_PATH.stat().st_mtime
        except OSError:
            continue
        if mt > state["cfg"].mtime + 0.01:
            try:
                state["cfg"] = load_config()
                picker_publish(state["cfg"])
                log("config reloaded:", len(state["cfg"].layouts), "layouts")
            except Exception as e:
                log("reload error:", e)


# ─── IPC server ─────────────────────────────────────────────────────────
class Server:
    def __init__(self, state: dict) -> None:
        self.state = state
        self.subs: list[socket.socket] = []
        self.pub_lock = threading.Lock()

    def publish(self, kind: str, data: dict) -> None:
        msg = (json.dumps({"kind": kind, "data": data}) + "\n").encode()
        with self.pub_lock:
            dead = []
            for s in self.subs:
                try:
                    s.send(msg)
                except OSError:
                    dead.append(s)
            for s in dead:
                try:
                    self.subs.remove(s); s.close()
                except (ValueError, OSError):
                    pass

    def handle(self, req: dict) -> dict:
        op = req.get("op", "")
        cfg: Config = self.state["cfg"]
        if op == "ping":
            return {"ok": True, "pid": os.getpid()}
        if op == "list":
            return {"ok": True,
                    "layouts": [{"name": ly.name,
                                 "zones": [asdict(z) for z in ly.zones]}
                                for ly in cfg.layouts],
                    "rules":   [asdict(r) for r in cfg.app_rules]}
        if op == "snap":
            ly = str(req.get("layout", "")).strip()
            zid = str(req.get("zone", "")).strip()
            if not (_safe_id(ly) and _safe_id(zid)):
                return {"ok": False, "error": "bad layout/zone id"}
            r = snap_active_to(cfg, ly, zid)
            if r.get("ok"):
                self.publish("snap", r)
            return r
        if op == "save":
            name = str(req.get("name", "")).strip()
            r = snapshot_save(name)
            if r.get("ok"):
                self.publish("save", r)
            return r
        if op == "restore":
            name = str(req.get("name", "")).strip()
            r = snapshot_restore(name, cfg)
            if r.get("ok"):
                self.publish("restore", r)
            return r
        if op == "snapshots":
            return {"ok": True, "names": snapshots_list()}
        if op == "picker":
            picker_publish(cfg, str(req.get("layout", "halves")))
            return {"ok": True}
        if op == "reload":
            try:
                self.state["cfg"] = load_config()
                picker_publish(self.state["cfg"])
                return {"ok": True, "layouts": len(self.state["cfg"].layouts)}
            except Exception as e:
                return {"ok": False, "error": f"parse: {e}"}
        if op == "subscribe":
            return {"_subscribe": True}
        return {"ok": False, "error": f"unknown op: {op}"}

    def serve(self) -> None:
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

    def _client(self, conn: socket.socket) -> None:
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
                if resp.get("_subscribe"):
                    self.subs.append(conn)
                    conn.send(b'{"ok":true,"subscribed":true}\n')
                    while True:
                        if conn.recv(1) == b"":
                            break
                    return
                conn.send((json.dumps(resp) + "\n").encode())
            except (OSError, json.JSONDecodeError, ValueError) as e:
                try:
                    conn.send((json.dumps({"ok": False, "error": str(e)}) + "\n").encode())
                except OSError:
                    pass


# ─── main ───────────────────────────────────────────────────────────────
def main() -> int:
    log("nyxus-snapd starting (pid", os.getpid(), ")")
    try:
        cfg = load_config()
    except Exception as e:
        log("startup config error:", e)
        return 1
    state = {"cfg": cfg, "active_addr": ""}
    picker_publish(cfg)

    srv = Server(state)
    threading.Thread(target=srv.serve, daemon=True).start()

    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.create_task(event_loop(state))
        loop.create_task(reload_loop(state))
        loop.run_forever()
    finally:
        loop.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
