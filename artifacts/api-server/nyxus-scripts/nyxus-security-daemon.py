#!/usr/bin/env python3
# ============================================================================
#  NYXUS · Security Indicator daemon         rev 2026-05-13 r1
#
#  Background watcher that:
#    · polls the camera/microphone/location/screen-record state every 2s
#    · writes a tiny JSON status file to ~/.cache/nyxus/indicators.json
#    · POSTs an EWW update so the top-bar dots flip red the moment a
#      sensor activates (and back to grey when it stops)
#    · tails journalctl for SECURITY events and forwards critical ones
#      to notify-send so the user sees them immediately
#
#  Logs to ~/.cache/nyxus/security-daemon.log.
#
#  Designed to run as a user systemd unit (nyxus-security-daemon.service).
#  Stop with: systemctl --user stop nyxus-security-daemon
#
#  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
from __future__ import annotations
import json, os, subprocess, time, logging, signal, sys, threading
from pathlib import Path

CACHE = Path.home() / ".cache" / "nyxus"
CACHE.mkdir(parents=True, exist_ok=True)
STATE_FILE = CACHE / "indicators.json"
LOG_FILE   = CACHE / "security-daemon.log"

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("nyxus-security-daemon")

POLL_INTERVAL = 2.0  # seconds
RUN = True


def _sh(cmd: list[str], timeout: int = 2) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, (p.stdout or "").strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 1, ""
    except Exception as e:  # pylint: disable=broad-except
        log.debug("sh %s: %s", cmd, e)
        return 1, ""


def detect() -> dict:
    """Same probe logic as nyxus_security.detect_priv_indicators()
    but standalone so the daemon never imports the GUI module."""
    cam = mic = loc = scr = False
    rc, _ = _sh(["fuser", "-s", "/dev/video0"])
    cam = (rc == 0)
    rc, out = _sh(["lsof", "+D", "/dev/snd"])
    if rc == 0 and "snd/pcm" in out:
        mic = True
    rc, out = _sh(["busctl", "tree", "org.freedesktop.GeoClue2", "--no-pager"])
    if "Client" in out:
        loc = True
    rc, _ = _sh(["pgrep", "-x", "wf-recorder"])
    scr = (rc == 0)
    return dict(camera=cam, mic=mic, location=loc, screen=scr,
                ts=int(time.time()))


def push_eww(state: dict) -> None:
    """Push to EWW if available. Silently skip if EWW is not running."""
    for key in ("camera", "mic", "location", "screen"):
        var = f"nyxus-priv-{key}"
        val = "active" if state[key] else "idle"
        try:
            subprocess.run(["eww", "update", f"{var}={val}"],
                           capture_output=True, timeout=2)
        except Exception:
            pass


def notify(title: str, body: str, urgency: str = "normal") -> None:
    try:
        subprocess.Popen(["notify-send", "-u", urgency,
                          "-a", "NYXUS Security", title, body])
    except Exception as e:
        log.warning("notify-send: %s", e)


def journal_watcher():
    """Tail journalctl for security-relevant events and notify."""
    cmd = ["journalctl", "-f", "--no-pager",
           "-g", "denied|EXEC|AVC|sudo:.*FAILED|authentication failure",
           "--output", "short-iso"]
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL,
                                text=True, bufsize=1)
    except Exception as e:
        log.error("journal watcher start: %s", e)
        return
    last_notify = 0.0
    for line in proc.stdout:  # type: ignore[union-attr]
        if not RUN: break
        line = line.strip()
        if not line: continue
        log.info("EVENT %s", line[:300])
        # rate-limit notifications to one per 30s
        now = time.time()
        if now - last_notify > 30:
            notify("Security event", line[:160], urgency="normal")
            last_notify = now


def main():
    def _stop(*_a):
        global RUN
        RUN = False
        log.info("stopping")
    signal.signal(signal.SIGINT,  _stop)
    signal.signal(signal.SIGTERM, _stop)

    log.info("nyxus-security-daemon starting")
    threading.Thread(target=journal_watcher, daemon=True).start()

    last: dict = {}
    while RUN:
        try:
            state = detect()
            STATE_FILE.write_text(json.dumps(state))
            push_eww(state)
            # Notify on rising edge
            for k, label in (("camera",   "Camera"),
                             ("mic",      "Microphone"),
                             ("location", "Location"),
                             ("screen",   "Screen recording")):
                if state[k] and not last.get(k):
                    notify(f"{label} active",
                           "An application is using your "
                           f"{label.lower()} right now.",
                           urgency="critical")
            last = state
        except Exception as e:  # pylint: disable=broad-except
            log.exception("loop: %s", e)
        time.sleep(POLL_INTERVAL)
    log.info("stopped")


if __name__ == "__main__":
    sys.exit(main() or 0)
