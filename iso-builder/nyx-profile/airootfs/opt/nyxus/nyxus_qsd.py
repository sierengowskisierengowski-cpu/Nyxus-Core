#!/usr/bin/env python3
"""
NYXUS Quick Settings daemon
===========================

Aggregates per-tile system state for the eww `quicksettings` panel and
serves toggles/sliders over a unix socket.

Tiles
-----
- wifi         : nmcli radio wifi on/off
- bluetooth    : bluetoothctl power on/off
- dnd          : dunstctl set-paused
- nightlight   : gammastep / hyprsunset (toggle)
- volume       : wpctl set-volume / set-mute
- brightness   : brightnessctl
- battery      : read sysfs /sys/class/power_supply

All shell-outs are argv lists; no user input is concatenated into command
strings. Tile values are validated (ints clamped, names regex-checked).
"""
from __future__ import annotations

import json
import os
import re
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
RUN_DIR   = XDG_RUN / "nyxus-qs"
SOCK_PATH = RUN_DIR / "cmd.sock"
STATE_J   = RUN_DIR / "state.json"
CFG_PATH  = HOME / ".config/nyxus/quicksettings.toml"


def log(*a: Any) -> None:
    print("[nyxus-qsd]", *a, file=sys.stderr, flush=True)


# ─── safe shell-out ─────────────────────────────────────────────────────
def run(*argv: str, timeout: float = 2.0) -> str:
    try:
        out = subprocess.run(list(argv), capture_output=True, text=True,
                              timeout=timeout, check=False)
        return out.stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def run_rc(*argv: str, timeout: float = 2.0) -> int:
    try:
        return subprocess.run(list(argv), capture_output=True,
                               timeout=timeout, check=False).returncode
    except (OSError, subprocess.TimeoutExpired):
        return -1


# ─── config ─────────────────────────────────────────────────────────────
@dataclass
class TileCfg:
    enabled: bool = True
    extra:   dict = field(default_factory=dict)

@dataclass
class Config:
    poll_ms:             int    = 1500
    always_show_battery: bool   = False
    brightness_backend:  str    = "brightnessctl"
    audio_backend:       str    = "wpctl"
    order:               list[str] = field(default_factory=lambda: [
        "wifi", "bluetooth", "dnd", "nightlight",
        "volume", "brightness", "battery"])
    tiles:               dict[str, TileCfg] = field(default_factory=dict)
    mtime:               float  = 0.0


_BACKEND_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


def load_config() -> Config:
    cfg = Config()
    if not CFG_PATH.exists():
        return cfg
    cfg.mtime = CFG_PATH.stat().st_mtime
    try:
        data = tomllib.loads(CFG_PATH.read_text())
    except (OSError, tomllib.TOMLDecodeError) as e:
        log("config error:", e); return cfg
    o = data.get("options", {}) or {}
    if isinstance(o.get("poll_ms"), int):
        cfg.poll_ms = max(200, o["poll_ms"])
    if isinstance(o.get("always_show_battery"), bool):
        cfg.always_show_battery = o["always_show_battery"]
    bb = str(o.get("brightness_backend", cfg.brightness_backend))
    ab = str(o.get("audio_backend", cfg.audio_backend))
    if _BACKEND_RE.match(bb): cfg.brightness_backend = bb
    if _BACKEND_RE.match(ab): cfg.audio_backend      = ab

    t = data.get("tiles", {}) or {}
    if isinstance(t.get("order"), list):
        cfg.order = [str(x) for x in t["order"]
                     if isinstance(x, str) and re.match(r"^[a-z]+$", x)]
    raw_tiles = data.get("tile", {}) or {}
    for name, opts in raw_tiles.items():
        if not re.match(r"^[a-z]+$", name) or not isinstance(opts, dict):
            continue
        cfg.tiles[name] = TileCfg(
            enabled=bool(opts.get("enabled", True)),
            extra={k: v for k, v in opts.items() if k != "enabled"},
        )
    return cfg


# ─── tile probes ────────────────────────────────────────────────────────
def probe_wifi() -> dict:
    out = run("nmcli", "-t", "-f", "WIFI", "radio").strip()
    on = out.endswith("enabled")
    ssid = ""
    if on:
        for line in run("nmcli", "-t", "-f", "ACTIVE,SSID", "device", "wifi").splitlines():
            if line.startswith("yes:"):
                ssid = line.split(":", 1)[1]; break
    return {"on": on, "ssid": ssid}


def probe_bluetooth() -> dict:
    out = run("bluetoothctl", "show")
    on = "Powered: yes" in out
    devs = []
    for line in run("bluetoothctl", "devices", "Connected").splitlines():
        parts = line.split(" ", 2)
        if len(parts) == 3 and parts[0] == "Device":
            devs.append(parts[2])
    return {"on": on, "connected": devs}


def probe_dnd() -> dict:
    out = run("dunstctl", "is-paused").strip()
    return {"on": out == "true"}


def probe_nightlight() -> dict:
    rc = run_rc("pgrep", "-x", "gammastep")
    if rc == 0:
        return {"on": True, "backend": "gammastep"}
    rc = run_rc("pgrep", "-x", "hyprsunset")
    return {"on": rc == 0, "backend": "hyprsunset" if rc == 0 else ""}


def probe_volume(backend: str) -> dict:
    if backend == "wpctl":
        out = run("wpctl", "get-volume", "@DEFAULT_AUDIO_SINK@").strip()
        # "Volume: 0.55 [MUTED]"
        m = re.search(r"Volume:\s*([\d.]+)", out)
        muted = "[MUTED]" in out
        v = float(m.group(1)) if m else 0.0
        return {"pct": int(round(v * 100)), "muted": muted}
    out = run("pactl", "get-sink-volume", "@DEFAULT_SINK@")
    m = re.search(r"(\d+)%", out)
    muted = "yes" in run("pactl", "get-sink-mute", "@DEFAULT_SINK@").lower()
    return {"pct": int(m.group(1)) if m else 0, "muted": muted}


def probe_brightness(backend: str) -> dict:
    if backend == "ddcutil":
        out = run("ddcutil", "getvcp", "10")
        m = re.search(r"current value =\s*(\d+)", out)
        return {"pct": int(m.group(1)) if m else 0}
    cur = run("brightnessctl", "g").strip()
    mx  = run("brightnessctl", "m").strip()
    try:
        pct = int(round(int(cur) * 100 / max(1, int(mx))))
    except ValueError:
        pct = 0
    return {"pct": pct}


def probe_battery() -> dict:
    base = Path("/sys/class/power_supply")
    if not base.exists():
        return {"present": False}
    bats = sorted(p for p in base.iterdir() if p.name.startswith("BAT"))
    if not bats:
        return {"present": False}
    b = bats[0]
    def _read(name):
        try:
            return (b / name).read_text().strip()
        except OSError:
            return ""
    pct = _read("capacity") or "0"
    status = _read("status") or "Unknown"
    try:
        pct_i = int(pct)
    except ValueError:
        pct_i = 0
    return {"present": True, "pct": pct_i, "status": status}


def probe_all(cfg: Config) -> dict:
    out: dict[str, Any] = {}
    out["wifi"]       = probe_wifi()
    out["bluetooth"]  = probe_bluetooth()
    out["dnd"]        = probe_dnd()
    out["nightlight"] = probe_nightlight()
    out["volume"]     = probe_volume(cfg.audio_backend)
    out["brightness"] = probe_brightness(cfg.brightness_backend)
    bat = probe_battery()
    if bat.get("present") or cfg.always_show_battery:
        out["battery"] = bat
    return {"tiles": out, "order": cfg.order, "ts": time.time()}


# ─── tile actions ───────────────────────────────────────────────────────
def act_wifi(on: bool) -> dict:
    rc = run_rc("nmcli", "radio", "wifi", "on" if on else "off")
    return {"ok": rc == 0}

def act_bluetooth(on: bool) -> dict:
    rc = run_rc("bluetoothctl", "power", "on" if on else "off")
    return {"ok": rc == 0}

def act_dnd(on: bool) -> dict:
    rc = run_rc("dunstctl", "set-paused", "true" if on else "false")
    return {"ok": rc == 0}

def act_nightlight(on: bool, temp_k: int = 3500) -> dict:
    # Stop whichever is running first.
    run_rc("pkill", "-x", "gammastep")
    run_rc("pkill", "-x", "hyprsunset")
    if not on:
        return {"ok": True}
    # Try hyprsunset first (Hyprland-native), fall back to gammastep.
    if run_rc("which", "hyprsunset") == 0:
        subprocess.Popen(["hyprsunset", "-t", str(int(temp_k))],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True, "backend": "hyprsunset"}
    if run_rc("which", "gammastep") == 0:
        subprocess.Popen(["gammastep", "-O", str(int(temp_k))],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return {"ok": True, "backend": "gammastep"}
    return {"ok": False, "error": "no nightlight backend"}

def act_volume(backend: str, pct: int | None = None,
               delta: int | None = None, mute: bool | None = None) -> dict:
    if backend == "wpctl":
        if mute is not None:
            return {"ok": run_rc("wpctl", "set-mute",
                                  "@DEFAULT_AUDIO_SINK@",
                                  "1" if mute else "0") == 0}
        if pct is not None:
            p = max(0, min(100, int(pct)))
            return {"ok": run_rc("wpctl", "set-volume",
                                  "@DEFAULT_AUDIO_SINK@",
                                  f"{p/100:.2f}") == 0}
        if delta is not None:
            d = max(-100, min(100, int(delta)))
            sign = "+" if d >= 0 else "-"
            return {"ok": run_rc("wpctl", "set-volume",
                                  "@DEFAULT_AUDIO_SINK@",
                                  f"{abs(d)/100:.2f}{sign}") == 0}
    return {"ok": False, "error": "no-op"}

def act_brightness(backend: str, pct: int | None = None,
                    delta: int | None = None) -> dict:
    if backend == "brightnessctl":
        if pct is not None:
            p = max(1, min(100, int(pct)))
            return {"ok": run_rc("brightnessctl", "set", f"{p}%") == 0}
        if delta is not None:
            d = max(-100, min(100, int(delta)))
            sign = "+" if d >= 0 else "-"
            return {"ok": run_rc("brightnessctl", "set",
                                  f"{abs(d)}%{sign}") == 0}
    if backend == "ddcutil" and pct is not None:
        return {"ok": run_rc("ddcutil", "setvcp", "10", str(int(pct))) == 0}
    return {"ok": False, "error": "no-op"}


# ─── poll loop ──────────────────────────────────────────────────────────
class Poll(threading.Thread):
    def __init__(self, state: dict):
        super().__init__(daemon=True)
        self.state = state

    def run(self):
        while True:
            cfg: Config = self.state["cfg"]
            try:
                snap = probe_all(cfg)
                tmp = STATE_J.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(snap, indent=2))
                tmp.replace(STATE_J)
                self.state["last"] = snap
            except Exception as e:
                log("probe:", e)
            # hot reload
            try:
                mt = CFG_PATH.stat().st_mtime
                if mt > cfg.mtime + 0.01:
                    self.state["cfg"] = load_config()
                    log("config reloaded")
            except OSError:
                pass
            time.sleep(max(0.2, self.state["cfg"].poll_ms / 1000.0))


# ─── IPC ────────────────────────────────────────────────────────────────
class Server:
    def __init__(self, state: dict):
        self.state = state

    def handle(self, req: dict) -> dict:
        op = req.get("op", "")
        cfg: Config = self.state["cfg"]
        if op == "ping":     return {"ok": True, "pid": os.getpid()}
        if op == "state":    return {"ok": True, "state": self.state.get("last", {})}
        if op == "probe":    return {"ok": True, "state": probe_all(cfg)}
        if op == "wifi":     return act_wifi(bool(req.get("on")))
        if op == "bluetooth":return act_bluetooth(bool(req.get("on")))
        if op == "dnd":      return act_dnd(bool(req.get("on")))
        if op == "nightlight":
            tk = int(cfg.tiles.get("nightlight", TileCfg()).extra.get("temp_k", 3500))
            return act_nightlight(bool(req.get("on")), tk)
        if op == "volume":
            return act_volume(cfg.audio_backend,
                               pct=req.get("pct"),
                               delta=req.get("delta"),
                               mute=req.get("mute"))
        if op == "brightness":
            return act_brightness(cfg.brightness_backend,
                                   pct=req.get("pct"),
                                   delta=req.get("delta"))
        if op == "reload":
            self.state["cfg"] = load_config()
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
    log("nyxus-qsd starting (pid", os.getpid(), ")")
    cfg = load_config()
    state: dict = {"cfg": cfg, "last": {}}
    Poll(state).start()
    srv = Server(state)
    threading.Thread(target=srv.serve, daemon=True).start()
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    while True:
        time.sleep(60)
    return 0  # unreachable


if __name__ == "__main__":
    sys.exit(main())
