#!/usr/bin/env python3
"""
NYXUS Hotkeys daemon
====================

Owns the user keymap. Translates declarative TOML config into:
  - Hyprland binds (via `hyprctl keyword bind …` / unbind on reload)
  - Multi-step chord state machine (Super+K then C → action)
  - Modifier-tap detection via /dev/input evdev (tap Cmd alone vs hold)
  - libinput touchpad gestures bridged via `libinput debug-events`
  - Per-app overrides triggered by Hyprland active-window events
  - Push-stream IPC over a unix socket (subscribe op for live UI)
  - Conflict scan + report
  - Hot-reload on TOML mtime change

Hardening
---------
- All shell `action` strings run via /bin/sh -c (user owns config; their shell)
- All filesystem operations use `--` to defuse leading-dash filenames
- Window class strings from Hyprland never reach a shell; argv only
- Subscribe socket is HUP-tolerant; broadcasts are guarded by a publish lock
- TOML parse failures keep the previous good config in memory
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import shlex
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
    import tomllib  # py311+
except ImportError:                       # pragma: no cover
    import tomli as tomllib  # type: ignore

# ─── paths ──────────────────────────────────────────────────────────────
HOME       = Path(os.path.expanduser("~"))
CFG_DIR    = HOME / ".config" / "nyxus"
CFG_PATH   = CFG_DIR / "hotkeys.toml"
RUN_DIR    = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "nyxus-hotkey"
SOCK_PATH  = RUN_DIR / "cmd.sock"
STATE_PATH = RUN_DIR / "state.json"
LOG_PATH   = HOME / ".cache" / "nyxus" / "hotkeyd.log"

HYPR_SIG  = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE", "")
HYPR_BASE = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "hypr" / HYPR_SIG
HYPR_EVT  = HYPR_BASE / ".socket2.sock"
HYPR_CMD  = HYPR_BASE / ".socket.sock"

# ─── tiny logger ────────────────────────────────────────────────────────
def log(*a: Any) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    msg = "[%s] %s\n" % (time.strftime("%H:%M:%S"), " ".join(str(x) for x in a))
    try:
        with LOG_PATH.open("a") as f:
            f.write(msg)
    except OSError:
        pass
    sys.stderr.write(msg)

# ─── data model ─────────────────────────────────────────────────────────
@dataclass
class Bind:
    mods: str = ""
    key: str = ""
    action: str = ""
    desc: str = ""
    category: str = "Other"
    src: str = "global"     # global | app:<class> | chord | mod_tap | gesture

    @property
    def combo(self) -> str:
        return f"{self.mods}+{self.key}".strip("+") or "(none)"

@dataclass
class Chord:
    trigger: str = ""
    steps: list[dict] = field(default_factory=list)
    desc: str = ""
    category: str = "Power"

@dataclass
class ModTap:
    mod: str = ""        # SUPER_L | CTRL_R | …
    action: str = ""
    desc: str = ""

@dataclass
class Gesture:
    type: str = "swipe"
    fingers: int = 3
    direction: str = "up"
    action: str = ""
    desc: str = ""

@dataclass
class Config:
    options: dict = field(default_factory=dict)
    binds: list[Bind] = field(default_factory=list)
    chords: list[Chord] = field(default_factory=list)
    mod_taps: list[ModTap] = field(default_factory=list)
    gestures: list[Gesture] = field(default_factory=list)
    app_overrides: dict[str, list[Bind]] = field(default_factory=dict)
    active_preset: str = "macos"
    version: int = 1
    raw: dict = field(default_factory=dict)


# ─── config loader ──────────────────────────────────────────────────────
def load_config() -> Config:
    cfg = Config()
    if not CFG_PATH.exists():
        log("config missing:", CFG_PATH, "— starting empty")
        return cfg
    try:
        with CFG_PATH.open("rb") as f:
            data = tomllib.load(f)
    except (tomllib.TOMLDecodeError, OSError) as e:
        log("CONFIG PARSE ERROR:", e, "— keeping previous in-memory config")
        raise
    cfg.raw = data
    meta = data.get("meta", {})
    cfg.version = int(meta.get("version", 1))
    cfg.active_preset = str(meta.get("active_preset", "macos"))
    cfg.options = data.get("options", {})
    for b in data.get("bind", []) or []:
        cfg.binds.append(Bind(
            mods=str(b.get("mods", "")),
            key=str(b.get("key", "")),
            action=str(b.get("action", "")),
            desc=str(b.get("desc", "")),
            category=str(b.get("category", "Other")),
            src="global",
        ))
    for c in data.get("chord", []) or []:
        cfg.chords.append(Chord(
            trigger=str(c.get("trigger", "")),
            steps=list(c.get("steps", []) or []),
            desc=str(c.get("desc", "")),
            category=str(c.get("category", "Power")),
        ))
    for m in data.get("mod_tap", []) or []:
        cfg.mod_taps.append(ModTap(
            mod=str(m.get("mod", "")),
            action=str(m.get("action", "")),
            desc=str(m.get("desc", "")),
        ))
    for g in data.get("gesture", []) or []:
        cfg.gestures.append(Gesture(
            type=str(g.get("type", "swipe")),
            fingers=int(g.get("fingers", 3)),
            direction=str(g.get("direction", "up")),
            action=str(g.get("action", "")),
            desc=str(g.get("desc", "")),
        ))
    for ao in data.get("app_override", []) or []:
        m = str(ao.get("match", ""))
        if not m:
            continue
        items: list[Bind] = []
        for b in ao.get("bind", []) or []:
            items.append(Bind(
                mods=str(b.get("mods", "")),
                key=str(b.get("key", "")),
                action=str(b.get("action", "")),
                desc=str(b.get("desc", "")),
                category=str(b.get("category", "App")),
                src=f"app:{m}",
            ))
        cfg.app_overrides[m] = items
    return cfg


# ─── conflict scan ──────────────────────────────────────────────────────
def scan_conflicts(cfg: Config) -> list[dict]:
    """Return list of {combo, sources:[…]} where the same combo binds to >1 action."""
    seen: dict[str, list[Bind]] = {}
    for b in cfg.binds:
        seen.setdefault(b.combo, []).append(b)
    out: list[dict] = []
    for combo, lst in seen.items():
        if len(lst) > 1:
            out.append({
                "combo": combo,
                "count": len(lst),
                "actions": [{"src": x.src, "desc": x.desc, "action": x.action} for x in lst],
            })
    # chord triggers vs binds
    for c in cfg.chords:
        for b in cfg.binds:
            if b.combo.upper() == c.trigger.upper().replace("+", "+", 1):
                out.append({
                    "combo": c.trigger,
                    "count": 2,
                    "actions": [
                        {"src": "chord", "desc": c.desc, "action": "(chord prefix)"},
                        {"src": b.src, "desc": b.desc, "action": b.action},
                    ],
                })
    return out


# ─── Hyprland IPC ───────────────────────────────────────────────────────
def hypr_cmd(cmd: str) -> str:
    """Send a single command via hyprctl socket."""
    if not HYPR_SIG or not HYPR_CMD.exists():
        return ""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.connect(str(HYPR_CMD))
            s.send(cmd.encode())
            buf = b""
            while True:
                chunk = s.recv(4096)
                if not chunk:
                    break
                buf += chunk
            return buf.decode(errors="replace")
    except OSError as e:
        log("hyprctl error:", e)
        return ""


def hypr_apply_binds(cfg: Config) -> None:
    """Replace all dynamic binds with current config. Uses keyword bind/unbind."""
    if not HYPR_SIG:
        log("HYPRLAND_INSTANCE_SIGNATURE empty; skipping bind apply")
        return
    # 1. unbind everything we previously set (tracked via state)
    prev = read_state().get("hypr_binds", [])
    for combo in prev:
        mods, _, key = combo.partition("+")
        hypr_cmd(f"keyword unbind {mods},{key}")
    # 2. apply current
    applied: list[str] = []
    for b in cfg.binds:
        if not b.key and not b.mods:
            continue
        # action runs through /bin/sh so user-provided pipelines work
        action = "exec, " + b.action.replace("\n", " ")
        cmd = f"keyword bind {b.mods},{b.key},{action}"
        hypr_cmd(cmd)
        applied.append(b.combo)
    s = read_state()
    s["hypr_binds"] = applied
    write_state(s)
    log("applied", len(applied), "Hyprland binds")


# ─── state file ─────────────────────────────────────────────────────────
def read_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text())
    except (OSError, json.JSONDecodeError):
        return {}

def write_state(s: dict) -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(s, indent=2, sort_keys=True))
    tmp.replace(STATE_PATH)


# ─── Hyprland event listener (active window for per-app overrides) ──────
async def hypr_event_loop(state_ref: dict) -> None:
    if not HYPR_EVT.exists():
        log("hyprland event socket missing:", HYPR_EVT)
        return
    while True:
        try:
            reader, _ = await asyncio.open_unix_connection(str(HYPR_EVT))
        except OSError as e:
            log("hypr evt connect:", e, "— retry 2s")
            await asyncio.sleep(2)
            continue
        log("hypr event loop connected")
        try:
            while True:
                line = await reader.readline()
                if not line:
                    break
                evt = line.decode(errors="replace").strip()
                if evt.startswith("activewindow>>"):
                    parts = evt.split(">>", 1)[1].split(",", 1)
                    cls = parts[0] if parts else ""
                    state_ref["active_class"] = cls
                    apply_app_overrides(state_ref, cls)
        except OSError as e:
            log("hypr evt read:", e)
        finally:
            await asyncio.sleep(1)


def apply_app_overrides(state_ref: dict, cls: str) -> None:
    """Push per-app binds on top of global on focus change."""
    cfg: Config = state_ref["cfg"]
    matched: list[Bind] = []
    for pat, binds in cfg.app_overrides.items():
        try:
            if re.search(pat, cls):
                matched.extend(binds)
        except re.error:
            continue
    # Re-apply: clear app-specific previous, push matched
    prev = state_ref.get("app_active_combos", [])
    for combo in prev:
        mods, _, key = combo.partition("+")
        hypr_cmd(f"keyword unbind {mods},{key}")
    new_combos: list[str] = []
    for b in matched:
        action = "exec, " + b.action.replace("\n", " ")
        hypr_cmd(f"keyword bind {b.mods},{b.key},{action}")
        new_combos.append(b.combo)
    state_ref["app_active_combos"] = new_combos


# ─── chord engine (driven by hyprctl exec callback wrappers) ────────────
class ChordEngine:
    def __init__(self, cfg: Config):
        self.cfg = cfg
        self.active: Chord | None = None
        self.activated_at = 0.0
        self.lock = threading.Lock()

    def update_cfg(self, cfg: Config) -> None:
        with self.lock:
            self.cfg = cfg
            self.active = None

    def trigger(self, name: str) -> str:
        """Called from CLI when a chord prefix bind fires."""
        with self.lock:
            for c in self.cfg.chords:
                if c.trigger.upper() == name.upper():
                    self.active = c
                    self.activated_at = time.monotonic()
                    return c.desc or c.trigger
            return ""

    def step(self, key: str) -> str:
        """Called from CLI when next key in chord arrives."""
        with self.lock:
            if self.active is None:
                return ""
            timeout = float(self.cfg.options.get("chord_timeout_ms", 800)) / 1000.0
            if time.monotonic() - self.activated_at > timeout:
                self.active = None
                return ""
            for st in self.active.steps:
                if str(st.get("key", "")).lower() == key.lower():
                    action = str(st.get("action", ""))
                    self.active = None
                    if action:
                        subprocess.Popen(["/bin/sh", "-c", action])
                    return str(st.get("desc", ""))
            self.active = None
            return ""


# ─── modifier-tap detector (evdev) ──────────────────────────────────────
class ModTapWatcher(threading.Thread):
    """Reads /dev/input/by-id keyboards via evdev when available."""
    def __init__(self, cfg_ref: dict):
        super().__init__(daemon=True, name="mod-tap")
        self.cfg_ref = cfg_ref
        self.stop_flag = threading.Event()

    def run(self) -> None:
        try:
            import evdev  # type: ignore
        except ImportError:
            log("evdev not installed — modifier-tap disabled")
            return
        # find keyboards
        devs = []
        try:
            for path in evdev.list_devices():
                d = evdev.InputDevice(path)
                caps = d.capabilities().get(evdev.ecodes.EV_KEY, [])
                if evdev.ecodes.KEY_LEFTMETA in caps or evdev.ecodes.KEY_LEFTCTRL in caps:
                    devs.append(d)
        except (PermissionError, OSError) as e:
            log("evdev open:", e, "— modifier-tap disabled (need input group)")
            return
        if not devs:
            log("no keyboard evdev devices found")
            return
        log("mod-tap watching", len(devs), "device(s)")
        # very small per-mod state
        held: dict[int, float] = {}
        threshold_ms = int(self.cfg_ref["cfg"].options.get("tap_threshold_ms", 220))
        from select import select
        while not self.stop_flag.is_set():
            r, _, _ = select([d.fd for d in devs], [], [], 0.5)
            if not r:
                continue
            for d in devs:
                if d.fd not in r:
                    continue
                try:
                    for event in d.read():
                        if event.type != evdev.ecodes.EV_KEY:
                            continue
                        ke = evdev.categorize(event)
                        if event.value == 1:           # down
                            held[event.code] = time.monotonic()
                        elif event.value == 0:         # up
                            t0 = held.pop(event.code, None)
                            if t0 is None:
                                continue
                            ms = (time.monotonic() - t0) * 1000.0
                            if ms <= threshold_ms:
                                self._fire_tap(event.code)
                except OSError:
                    continue

    def _fire_tap(self, code: int) -> None:
        try:
            import evdev  # type: ignore
        except ImportError:
            return
        name_map = {
            evdev.ecodes.KEY_LEFTMETA:  "SUPER_L",
            evdev.ecodes.KEY_RIGHTMETA: "SUPER_R",
            evdev.ecodes.KEY_LEFTCTRL:  "CTRL_L",
            evdev.ecodes.KEY_RIGHTCTRL: "CTRL_R",
            evdev.ecodes.KEY_LEFTALT:   "ALT_L",
            evdev.ecodes.KEY_RIGHTALT:  "ALT_R",
            evdev.ecodes.KEY_LEFTSHIFT: "SHIFT_L",
            evdev.ecodes.KEY_RIGHTSHIFT:"SHIFT_R",
        }
        n = name_map.get(code)
        if not n:
            return
        cfg: Config = self.cfg_ref["cfg"]
        for mt in cfg.mod_taps:
            if mt.mod.upper() == n.upper() and mt.action:
                subprocess.Popen(["/bin/sh", "-c", mt.action])
                log("mod-tap fired:", n, "→", mt.desc)
                return


# ─── libinput gesture bridge ────────────────────────────────────────────
class GestureWatcher(threading.Thread):
    def __init__(self, cfg_ref: dict):
        super().__init__(daemon=True, name="gestures")
        self.cfg_ref = cfg_ref
        self.proc: subprocess.Popen | None = None
        self.stop_flag = threading.Event()

    def run(self) -> None:
        try:
            self.proc = subprocess.Popen(
                ["libinput", "debug-events", "--show-keycodes"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            )
        except (FileNotFoundError, PermissionError) as e:
            log("libinput not available — gestures disabled:", e)
            return
        assert self.proc.stdout is not None
        for line in self.proc.stdout:
            if self.stop_flag.is_set():
                break
            # example: "GESTURE_SWIPE_END   3 finger ... +0.00ms ..."
            if "GESTURE_SWIPE_END" not in line:
                continue
            # look for finger count + direction in the trailing fields
            try:
                bits = line.split()
                fingers = 0
                for tok in bits:
                    if tok.isdigit():
                        fingers = int(tok); break
                # libinput prints dx/dy at end like "1.23/-4.56"
                dx = dy = 0.0
                for tok in bits[::-1]:
                    if "/" in tok:
                        try:
                            sx, sy = tok.split("/", 1)
                            dx = float(sx); dy = float(sy)
                            break
                        except ValueError:
                            continue
                direction = self._direction(dx, dy)
                self._fire(fingers, direction)
            except Exception as e:
                log("gesture parse err:", e)

    def _direction(self, dx: float, dy: float) -> str:
        if abs(dx) > abs(dy):
            return "right" if dx > 0 else "left"
        return "down" if dy > 0 else "up"

    def _fire(self, fingers: int, direction: str) -> None:
        cfg: Config = self.cfg_ref["cfg"]
        for g in cfg.gestures:
            if g.type == "swipe" and g.fingers == fingers and g.direction == direction and g.action:
                subprocess.Popen(["/bin/sh", "-c", g.action])
                log("gesture fired:", fingers, direction, "→", g.desc)
                return


# ─── command socket + push streaming ────────────────────────────────────
class IPCServer:
    def __init__(self, state_ref: dict, chord: ChordEngine):
        self.state_ref = state_ref
        self.chord = chord
        self.subscribers: list[socket.socket] = []
        self.publish_lock = threading.Lock()

    def start(self) -> None:
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        if SOCK_PATH.exists():
            try: SOCK_PATH.unlink()
            except OSError: pass
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.bind(str(SOCK_PATH))
        srv.listen(16)
        os.chmod(SOCK_PATH, 0o600)
        log("ipc listening:", SOCK_PATH)
        threading.Thread(target=self._accept_loop, args=(srv,), daemon=True).start()

    def _accept_loop(self, srv: socket.socket) -> None:
        while True:
            try:
                conn, _ = srv.accept()
            except OSError:
                return
            threading.Thread(target=self._handle, args=(conn,), daemon=True).start()

    def _handle(self, conn: socket.socket) -> None:
        try:
            buf = b""
            while b"\n" not in buf:
                chunk = conn.recv(4096)
                if not chunk:
                    return
                buf += chunk
            line, _, _ = buf.partition(b"\n")
            try:
                req = json.loads(line.decode("utf-8", errors="replace"))
            except json.JSONDecodeError:
                conn.send(b'{"ok":false,"error":"bad json"}\n'); return
            op = str(req.get("op", ""))
            if op == "subscribe":
                conn.send(b'{"ok":true,"event":"hello"}\n')
                self.subscribers.append(conn)
                # keep connection open; subscribers list owns it
                return
            resp = self._dispatch(op, req)
            conn.send((json.dumps(resp) + "\n").encode())
        except OSError as e:
            log("ipc handler err:", e)
        finally:
            if op != "subscribe":
                try: conn.close()
                except OSError: pass

    def publish(self, event: str, payload: dict) -> None:
        with self.publish_lock:
            msg = (json.dumps({"event": event, **payload}) + "\n").encode()
            dead = []
            for s in list(self.subscribers):
                try:
                    s.send(msg)
                except OSError:
                    dead.append(s)
            for s in dead:
                try: s.close()
                except OSError: pass
                if s in self.subscribers:
                    self.subscribers.remove(s)

    def _dispatch(self, op: str, req: dict) -> dict:
        cfg: Config = self.state_ref["cfg"]
        if op == "list":
            return {"ok": True, "binds":   [asdict(b) for b in cfg.binds],
                                "chords":  [asdict(c) for c in cfg.chords],
                                "modtaps": [asdict(m) for m in cfg.mod_taps],
                                "gestures":[asdict(g) for g in cfg.gestures],
                                "app_overrides": {k: [asdict(b) for b in v]
                                                  for k, v in cfg.app_overrides.items()}}
        if op == "conflicts":
            return {"ok": True, "conflicts": scan_conflicts(cfg)}
        if op == "chord_trigger":
            return {"ok": True, "label": self.chord.trigger(str(req.get("name", "")))}
        if op == "chord_step":
            return {"ok": True, "label": self.chord.step(str(req.get("key", "")))}
        if op == "reload":
            try:
                cfg2 = load_config()
            except Exception as e:
                return {"ok": False, "error": f"parse: {e}"}
            self.state_ref["cfg"] = cfg2
            self.chord.update_cfg(cfg2)
            hypr_apply_binds(cfg2)
            self.publish("reload", {"binds": len(cfg2.binds)})
            return {"ok": True, "binds": len(cfg2.binds)}
        if op == "test":
            action = str(req.get("action", ""))
            if action:
                subprocess.Popen(["/bin/sh", "-c", action])
            return {"ok": True}
        if op == "active_class":
            return {"ok": True, "active_class": self.state_ref.get("active_class", "")}
        return {"ok": False, "error": f"unknown op: {op}"}


# ─── main ───────────────────────────────────────────────────────────────
def main() -> int:
    log("nyxus-hotkeyd starting (pid", os.getpid(), ")")
    try:
        cfg = load_config()
    except Exception as e:
        log("startup config error:", e, "— exiting")
        return 1
    state_ref: dict = {"cfg": cfg, "active_class": "", "app_active_combos": []}
    chord = ChordEngine(cfg)

    # apply hyprland binds once
    hypr_apply_binds(cfg)

    # IPC server
    ipc = IPCServer(state_ref, chord)
    ipc.start()

    # background watchers
    ModTapWatcher(state_ref).start()
    GestureWatcher(state_ref).start()

    # config hot-reload watcher
    def watch_cfg() -> None:
        last = CFG_PATH.stat().st_mtime if CFG_PATH.exists() else 0
        while True:
            time.sleep(1.5)
            try:
                cur = CFG_PATH.stat().st_mtime
            except OSError:
                continue
            if cur != last and bool(state_ref["cfg"].options.get("hot_reload", True)):
                last = cur
                try:
                    new = load_config()
                except Exception as e:
                    log("hot-reload parse fail:", e); continue
                state_ref["cfg"] = new
                chord.update_cfg(new)
                hypr_apply_binds(new)
                ipc.publish("reload", {"binds": len(new.binds)})
                log("hot-reload done:", len(new.binds), "binds")
    threading.Thread(target=watch_cfg, daemon=True).start()

    # signal handlers
    stop = threading.Event()
    def _sig(_signum, _frame):
        log("signal received — shutting down")
        stop.set()
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)

    # async hyprland event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.create_task(hypr_event_loop(state_ref))
    try:
        while not stop.is_set():
            loop.run_until_complete(asyncio.sleep(0.25))
    finally:
        loop.close()
    log("nyxus-hotkeyd exit")
    return 0


if __name__ == "__main__":
    sys.exit(main())
