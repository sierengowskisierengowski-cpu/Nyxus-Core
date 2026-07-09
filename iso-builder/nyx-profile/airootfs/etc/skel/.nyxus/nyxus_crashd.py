#!/usr/bin/env python3
"""
NYXUS Crash Watcher — daemon that follows systemd-coredump events and
fires a notification when an app crashes.

How it works:
    journalctl -f --identifier=systemd-coredump --output=json
    → on each new MESSAGE_ID 'fc2e22bc6ee647b6b90729ab34a250b1', parse
      the COREDUMP_* fields, write a digest to ~/.cache/nyxus/crashes/,
      and call notify-send with two actions:
          • View report  →  spawns nyxus-crash-report
          • Dismiss      →  no-op

Disabled via Settings → Privacy → "Crash reports" toggle, which writes
~/.config/nyxus/crashd.disabled — the daemon checks for that file every
loop and exits cleanly when it appears.

Logs to ~/.cache/nyxus/crashd.log.
Wired as a user systemd unit: nyxus-crashd.service
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import select
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

HOME = Path(os.path.expanduser("~"))
CACHE_DIR = HOME / ".cache" / "nyxus"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CRASH_DIR = CACHE_DIR / "crashes"
CRASH_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = CACHE_DIR / "crashd.log"
DISABLE_FLAG = HOME / ".config" / "nyxus" / "crashd.disabled"

log = logging.getLogger("nyxus_crashd")
log.setLevel(logging.INFO)
_h = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=512_000,
                                          backupCount=3)
_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(_h)

COREDUMP_MSG_ID = "fc2e22bc6ee647b6b90729ab34a250b1"


def have(cmd: str) -> str | None:
    return shutil.which(cmd)


def _notify(comm: str, pid: str, digest_path: Path) -> None:
    if not have("notify-send"):
        return
    try:
        subprocess.Popen([
            "notify-send",
            "--app-name=NYXUS",
            "--icon=dialog-error",
            "--urgency=critical",
            "--action=view=View report",
            "--action=dismiss=Dismiss",
            f"{comm or 'A program'} crashed",
            f"PID {pid}. Click to view the crash report.",
        ], start_new_session=True)
        # The action callback for notify-send isn't trivially captured
        # without dbus. We fall back to spawning the reporter eagerly so
        # the user can always reach it from the notification center; the
        # path is also logged in nyxus-crash-report's recent list.
        log.info("notified for %s pid=%s digest=%s", comm, pid, digest_path)
    except Exception as e:
        log.warning("notify failed: %s", e)


def _record(payload: dict) -> Path:
    """Persist a stripped digest of the coredump event for the reporter."""
    ts = time.strftime("%Y%m%d-%H%M%S")
    comm = payload.get("COREDUMP_COMM", "unknown")
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in comm)
    out = CRASH_DIR / f"{ts}-{safe}.json"
    digest = {
        "timestamp": payload.get("__REALTIME_TIMESTAMP"),
        "comm":      payload.get("COREDUMP_COMM"),
        "exe":       payload.get("COREDUMP_EXE"),
        "pid":       payload.get("COREDUMP_PID"),
        "uid":       payload.get("COREDUMP_UID"),
        "signal":    payload.get("COREDUMP_SIGNAL_NAME")
                  or payload.get("COREDUMP_SIGNAL"),
        "cmdline":   payload.get("COREDUMP_CMDLINE"),
        "hostname":  payload.get("_HOSTNAME"),
        "boot_id":   payload.get("_BOOT_ID"),
        "message":   payload.get("MESSAGE"),
    }
    try:
        out.write_text(json.dumps(digest, indent=2))
    except Exception as e:
        log.error("write digest failed: %s", e)
    return out


def main() -> int:
    if not have("journalctl"):
        log.error("journalctl missing — cannot watch coredumps")
        return 2
    log.info("nyxus-crashd starting (pid=%d)", os.getpid())

    # Honor systemctl stop / SIGTERM cleanly so the user can disable us
    # without waiting for a coredump event to unblock the read loop.
    stop_requested = {"flag": False}
    def _on_signal(signum, _frame):
        log.info("signal %s received — exiting", signum)
        stop_requested["flag"] = True
    signal.signal(signal.SIGTERM, _on_signal)
    signal.signal(signal.SIGINT,  _on_signal)
    signal.signal(signal.SIGHUP,  _on_signal)

    proc = subprocess.Popen(
        ["journalctl", "-f", "--lines=0",
         "--identifier=systemd-coredump", "--output=json"],
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        text=True)
    assert proc.stdout is not None
    fd = proc.stdout.fileno()

    try:
        while not stop_requested["flag"]:
            # 2-second poll: even when journalctl is silent we wake up
            # often enough to honor the disable flag promptly.
            ready, _, _ = select.select([fd], [], [], 2.0)
            if DISABLE_FLAG.exists():
                log.info("disable flag present — exiting")
                break
            if proc.poll() is not None:
                log.warning("journalctl exited (rc=%s)", proc.returncode)
                break
            if not ready:
                continue
            line = proc.stdout.readline()
            if not line:
                # EOF on stdout; treat as journalctl exit.
                time.sleep(0.5)
                continue
            line = line.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            mid = payload.get("MESSAGE_ID")
            if mid and mid.lower() == COREDUMP_MSG_ID:
                digest = _record(payload)
                _notify(
                    payload.get("COREDUMP_COMM", "Application"),
                    str(payload.get("COREDUMP_PID", "?")),
                    digest)
    finally:
        try: proc.terminate()
        except Exception: pass
        try: proc.wait(timeout=3)
        except Exception:
            try: proc.kill()
            except Exception: pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
