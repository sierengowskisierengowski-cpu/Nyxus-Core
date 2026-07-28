#!/usr/bin/env python3
"""
sharkdash_health.py — Health watchdog + alert system for SharkFin v2.0
Reads thresholds from config.json, fires notifications with fallbacks,
writes state files, runs as a daemon via systemd.
"""
from __future__ import annotations
import os, sys, time, json, subprocess, logging, logging.handlers, argparse
from pathlib import Path
from datetime import datetime

HOME     = Path(os.path.expanduser("~"))
STATE    = HOME / ".cache" / "sharkdash"
DATA     = HOME / ".local" / "share" / "sharkdash"
CFG_PATH = HOME / ".config" / "sharkdash" / "config.json"
LOG_PATH = DATA / "sharkdash.log"
ALERT_LOG= DATA / "missed_alerts.log"

STATE.mkdir(parents=True, exist_ok=True)
DATA.mkdir(parents=True, exist_ok=True)

# ── Logging ────────────────────────────────────────────────────────────────
def setup_logging():
    logger = logging.getLogger("sharkdash")
    logger.setLevel(logging.DEBUG)
    h = logging.handlers.RotatingFileHandler(
        LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3)
    h.setFormatter(logging.Formatter("%(asctime)s %(name)s %(levelname)s %(message)s"))
    logger.addHandler(h)
    return logger

log = logging.getLogger("sharkdash.health")

# ── Config ──────────────────────────────────────────────────────────────────
DEFAULTS = {
    "cpu_warn":         75.0,
    "cpu_crit":         90.0,
    "gpu_temp_warn":    80.0,
    "gpu_temp_crit":    90.0,
    "mem_warn":         80.0,
    "mem_crit":         92.0,
    "disk_warn":        85.0,
    "disk_crit":        95.0,
    "fan_min_warn":     800,
    "temp_cpu_warn":    80.0,
    "temp_cpu_crit":    95.0,
    "screensaver_idle_seconds": 300,
    "notify_enabled":   True,
    "daemon_interval":  10,
    "log_level":        "INFO",
    "alert_cooldown_sec": 300,
}

_cfg_mtime = 0.0
_cfg: dict = dict(DEFAULTS)

def load_config() -> dict:
    global _cfg, _cfg_mtime
    try:
        mtime = CFG_PATH.stat().st_mtime if CFG_PATH.exists() else 0
        if mtime != _cfg_mtime:
            data   = json.loads(CFG_PATH.read_text()) if CFG_PATH.exists() else {}
            _cfg   = {**DEFAULTS, **data}
            _cfg_mtime = mtime
            log.info("Config reloaded from %s", CFG_PATH)
    except Exception as e:
        log.warning("Config load error: %s", e)
    return _cfg

def save_config():
    CFG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CFG_PATH.write_text(json.dumps(_cfg, indent=2))

def cfg(key: str):
    return _cfg.get(key, DEFAULTS.get(key))

# ── Notification ────────────────────────────────────────────────────────────
_notify_available: bool | None = None

def _check_notify_available() -> bool:
    global _notify_available
    if _notify_available is not None:
        return _notify_available
    import shutil
    if not shutil.which("notify-send"):
        _notify_available = False
        return False
    r = subprocess.run(["notify-send", "--version"],
                       capture_output=True, timeout=2)
    _notify_available = (r.returncode == 0)
    return _notify_available

_last_alert_ts: dict[str, float] = {}

def notify(title: str, body: str, urgency="normal", icon="dialog-warning", key: str | None = None):
    """
    Fire desktop notification with D-Bus fallback chain.
    1. notify-send
    2. gdbus call (COSMIC/GNOME)
    3. Write to missed_alerts.log

    `key` (e.g. "cpu_crit") debounces repeat alerts of the same condition —
    without it, a sustained critical reading refires a popup every poll cycle.
    """
    if key is not None:
        now = time.time()
        last = _last_alert_ts.get(key, 0.0)
        cooldown = cfg("alert_cooldown_sec")
        if now - last < cooldown:
            log.debug("Suppressed duplicate alert (key=%s, %.0fs since last)", key, now - last)
            return
        _last_alert_ts[key] = now

    if not cfg("notify_enabled"):
        _log_missed(title, body)
        return

    success = False

    # Attempt 1: notify-send
    if _check_notify_available():
        r = subprocess.run(
            ["notify-send", f"--urgency={urgency}", f"--icon={icon}",
             "--app-name=SharkDash", title, body],
            capture_output=True, timeout=5, check=False)
        success = (r.returncode == 0)

    # Attempt 2: gdbus (COSMIC / GNOME desktop)
    if not success:
        try:
            r = subprocess.run([
                "gdbus", "call", "--session",
                "--dest", "org.freedesktop.Notifications",
                "--object-path", "/org/freedesktop/Notifications",
                "--method", "org.freedesktop.Notifications.Notify",
                "SharkDash", "0", icon, title, body,
                "[]", "{}", "5000",
            ], capture_output=True, timeout=5, check=False)
            success = (r.returncode == 0)
        except Exception:
            pass

    if not success:
        _log_missed(title, body)
        log.warning("Notification failed, logged to %s", ALERT_LOG)
    else:
        log.debug("Notification sent: %s — %s", title, body)

def _log_missed(title: str, body: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with ALERT_LOG.open("a") as f:
            f.write(f"[{ts}] {title}: {body}\n")
    except Exception:
        pass

# ── State files ─────────────────────────────────────────────────────────────
def write_state(data: dict):
    data["last_ok_at"] = time.time()
    (STATE / "health.json").write_text(json.dumps(data, indent=2))

def read_state() -> dict:
    f = STATE / "health.json"
    try:
        return json.loads(f.read_text()) if f.exists() else {}
    except Exception:
        return {}

def write_governor(data: dict):
    (STATE / "governor.json").write_text(json.dumps(data, indent=2))

def read_governor() -> dict:
    f = STATE / "governor.json"
    try:
        return json.loads(f.read_text()) if f.exists() else {}
    except Exception:
        return {}

# ── Assessment ──────────────────────────────────────────────────────────────
def assess() -> dict:
    """Evaluate system health against config thresholds. Returns state dict."""
    load_config()
    from sharkdash_core import temps, mem, fans, cpu_usage, gpu, disks

    alerts = []
    state  = "ok"

    def flag(level, msg):
        nonlocal state
        alerts.append({"level": level, "msg": msg, "ts": time.time()})
        if level == "crit" or (level == "warn" and state == "ok"):
            state = level

    # CPU temps
    t = temps()
    pkg = t.get("cpu_pkg", 0)
    if pkg >= cfg("temp_cpu_crit"):
        flag("crit", f"CPU CRITICAL {pkg:.0f}°C")
        notify("⚠ CPU CRITICAL", f"CPU package {pkg:.0f}°C — throttling imminent",
               urgency="critical", key="cpu_crit")
    elif pkg >= cfg("temp_cpu_warn"):
        flag("warn", f"CPU HOT {pkg:.0f}°C")

    # GPU temp
    g = gpu()
    nv = g.get("nvidia", {})
    if nv:
        gt = nv.get("temp", 0)
        if gt >= cfg("gpu_temp_crit"):
            flag("crit", f"GPU CRITICAL {gt:.0f}°C")
            notify("⚠ GPU CRITICAL", f"RTX temp {gt:.0f}°C", urgency="critical", key="gpu_crit")
        elif gt >= cfg("gpu_temp_warn"):
            flag("warn", f"GPU HOT {gt:.0f}°C")

    # Memory
    m = mem()
    if m["pct"] >= cfg("mem_crit"):
        flag("crit", f"RAM CRITICAL {m['pct']:.0f}%")
        notify("⚠ RAM CRITICAL", f"Memory {m['pct']:.0f}% used", urgency="critical", key="mem_crit")
    elif m["pct"] >= cfg("mem_warn"):
        flag("warn", f"RAM HIGH {m['pct']:.0f}%")

    # Disks
    for d in disks():
        if d["pct"] >= cfg("disk_crit"):
            flag("crit", f"DISK {d['mount']} {d['pct']:.0f}%")
            notify("⚠ DISK FULL", f"{d['mount']} at {d['pct']:.0f}%", urgency="critical", key=f"disk_crit:{d['mount']}")
        elif d["pct"] >= cfg("disk_warn"):
            flag("warn", f"DISK {d['mount']} {d['pct']:.0f}%")

    # Fans (if msi-ec available)
    fan_list = fans()
    if fan_list:
        for i, rpm in enumerate(fan_list):
            if rpm < cfg("fan_min_warn") and rpm > 0:
                flag("warn", f"FAN {i+1} LOW {rpm} RPM")

    data = dict(
        state=state, alerts=alerts,
        temps=t, mem=m,
        last_ok_at=time.time(),
        ts=time.time(),
    )
    write_state(data)
    return data

# ── Full-screen popup alert (for CRITICAL) ─────────────────────────────────
def popup_alert(msg: str):
    """Display a full-screen critical alert in the terminal."""
    import curses
    def _inner(stdscr):
        curses.curs_set(0)
        curses.start_color()
        curses.use_default_colors()
        curses.init_pair(1, curses.COLOR_RED, -1)
        rows, cols = stdscr.getmaxyx()
        stdscr.clear()
        stdscr.attron(curses.A_BOLD | curses.color_pair(1))
        border = "!" * (cols - 2)
        stdscr.addstr(0,         1, border)
        stdscr.addstr(rows - 1,  1, border)
        y = rows // 2
        stdscr.addstr(y - 1, max(0, (cols - 20) // 2), "⚠  CRITICAL ALERT  ⚠")
        stdscr.addstr(y + 1, max(0, (cols - len(msg))  // 2), msg)
        stdscr.addstr(y + 3, max(0, (cols - 22) // 2), "Press any key to dismiss")
        stdscr.attroff(curses.A_BOLD | curses.color_pair(1))
        stdscr.getch()
    try:
        curses.wrapper(_inner)
    except Exception:
        pass

# ── Daemon ──────────────────────────────────────────────────────────────────
def daemon():
    setup_logging()
    log.info("SharkDash health daemon started")
    while True:
        try:
            load_config()
            result = assess()
            log.debug("Health: %s, alerts: %d", result["state"], len(result["alerts"]))
        except Exception as e:
            log.error("Assessment error: %s", e)
        time.sleep(cfg("daemon_interval"))

# ── CLI ──────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="SharkDash Health Monitor")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--health", action="store_true", help="Print current health JSON and exit")
    parser.add_argument("--alert",  metavar="MSG",       help="Fire a test notification")
    args = parser.parse_args()

    if args.health:
        setup_logging()
        load_config()
        result = assess()
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["state"] == "ok" else 1)

    if args.alert:
        setup_logging()
        load_config()
        notify("SharkDash Test", args.alert, urgency="normal")
        print(f"Alert fired: {args.alert}")
        sys.exit(0)

    if args.daemon:
        daemon()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
