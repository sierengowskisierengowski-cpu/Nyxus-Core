#!/usr/bin/env python3
"""NYXUS Hot Corners — Hyprland cursor-corner action daemon.

Polls `hyprctl cursorpos -j` every 200 ms. If the cursor sits in the
configured corner area for the dwell window, the matching action is
fired exactly once until the cursor leaves the area.

Configuration: ~/.config/nyxus/hotcorners.conf
  Plain key=value, lines starting with # are comments.
  Keys (one per corner):
    tl=<action>   tr=<action>   bl=<action>   br=<action>
  Optional tuning:
    dwell_ms=<int>      default 400
    edge_px=<int>       default 6 (corner zone size)
    poll_ms=<int>       default 200

Actions are looked up in ACTIONS below; "none" disables that corner.

© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import json
import logging
import os
import signal
import subprocess
import sys
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Optional, Tuple

# ── logging ──────────────────────────────────────────────────────────
LOG_DIR = Path.home() / ".cache" / "nyxus"
LOG_DIR.mkdir(parents=True, exist_ok=True)
log = logging.getLogger("nyxus-hotcorners")
log.setLevel(logging.INFO)
_h = RotatingFileHandler(
    LOG_DIR / "hotcorners.log",
    maxBytes=256_000, backupCount=2, encoding="utf-8")
_h.setFormatter(logging.Formatter(
    "%(asctime)s %(levelname)s %(message)s"))
log.addHandler(_h)

# ── config ───────────────────────────────────────────────────────────
CONF = Path.home() / ".config" / "nyxus" / "hotcorners.conf"

# Action whitelist — values are arg lists fed straight to subprocess.
# Edit here (NOT via the conf file) to add new actions, then surface
# them in the Settings UI.
ACTIONS: Dict[str, list[str]] = {
    "none":            [],
    "mission_control": ["nyxus-mission-control"],
    "spotlight":       ["nyxus-spotlight"],
    "show_desktop":    ["hyprctl", "dispatch",
                        "togglespecialworkspace", "scratch"],
    "lock":            ["hyprlock"],
    "menu":            ["nyxus-start-menu"],
    "control_center":  ["nyxus-control-center"],
    "notifications":   ["swaync-client", "-t"],
}

DEFAULTS = {
    "tl": "none", "tr": "none", "bl": "none", "br": "none",
    "dwell_ms": "400", "edge_px": "6", "poll_ms": "200",
}


def load_conf() -> Dict[str, str]:
    cfg = dict(DEFAULTS)
    if not CONF.exists():
        return cfg
    try:
        for raw in CONF.read_text(encoding="utf-8").splitlines():
            s = raw.strip()
            if not s or s.startswith("#") or "=" not in s:
                continue
            k, _, v = s.partition("=")
            cfg[k.strip().lower()] = v.strip()
    except OSError as e:
        log.warning("read %s: %s", CONF, e)
    return cfg


def cursor_pos() -> Optional[Tuple[int, int]]:
    """Return (x, y) global cursor position via hyprctl, or None."""
    try:
        r = subprocess.run(
            ["hyprctl", "cursorpos", "-j"],
            capture_output=True, text=True, timeout=1)
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        log.warning("hyprctl cursorpos: %s", e)
        return None
    if r.returncode != 0:
        return None
    try:
        d = json.loads(r.stdout)
        return int(d["x"]), int(d["y"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
        log.warning("parse cursorpos %r: %s", r.stdout[:60], e)
        return None


def screen_bounds() -> Optional[Tuple[int, int, int, int]]:
    """Union bounding box of all monitors as (xmin, ymin, xmax, ymax).

    Returns None on failure — caller will skip this tick rather than
    fall back to a wrong default that would fire actions in the middle
    of the screen.
    """
    try:
        r = subprocess.run(
            ["hyprctl", "monitors", "-j"],
            capture_output=True, text=True, timeout=1)
    except (FileNotFoundError, subprocess.SubprocessError) as e:
        log.warning("hyprctl monitors: %s", e)
        return None
    if r.returncode != 0:
        return None
    try:
        mons = json.loads(r.stdout)
    except json.JSONDecodeError as e:
        log.warning("parse monitors: %s", e)
        return None
    if not mons:
        return None
    xs, ys, xe, ye = [], [], [], []
    for m in mons:
        x = int(m.get("x", 0) or 0)
        y = int(m.get("y", 0) or 0)
        w = int(m.get("width", 0) or 0)
        h = int(m.get("height", 0) or 0)
        scale = float(m.get("scale", 1.0) or 1.0)
        # cursorpos is in logical coords — divide by scale to match.
        if scale > 0:
            w = int(w / scale)
            h = int(h / scale)
        xs.append(x); ys.append(y); xe.append(x + w); ye.append(y + h)
    return min(xs), min(ys), max(xe), max(ye)


def in_corner(pos: Tuple[int, int],
              bb: Tuple[int, int, int, int],
              edge: int) -> Optional[str]:
    """Return 'tl'/'tr'/'bl'/'br' if cursor is in that corner zone."""
    x, y = pos
    xmin, ymin, xmax, ymax = bb
    left   = x <= xmin + edge
    right  = x >= xmax - edge - 1
    top    = y <= ymin + edge
    bottom = y >= ymax - edge - 1
    if top    and left:  return "tl"
    if top    and right: return "tr"
    if bottom and left:  return "bl"
    if bottom and right: return "br"
    return None


def fire(action: str) -> None:
    cmd = ACTIONS.get(action)
    if not cmd:
        return
    try:
        subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            start_new_session=True)
        log.info("fire %s -> %s", action, " ".join(cmd))
    except (FileNotFoundError, OSError) as e:
        log.warning("fire %s failed: %s", action, e)


def main() -> int:
    # Refuse to run twice — the systemd user unit will keep us as a
    # singleton anyway, but a manual launch should still bail out.
    pid_file = LOG_DIR / "hotcorners.pid"
    try:
        if pid_file.exists():
            old = int(pid_file.read_text().strip())
            try:
                os.kill(old, 0)
                log.info("already running pid=%d, exiting", old)
                return 0
            except ProcessLookupError:
                pass
            except (OSError, ValueError):
                pass
        pid_file.write_text(str(os.getpid()), encoding="utf-8")
    except OSError as e:
        log.warning("pidfile: %s", e)

    stop = {"flag": False}

    def _stop(*_):
        stop["flag"] = True
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    def parse_tunables(c: Dict[str, str]) -> Tuple[int, int, int]:
        """Parse and clamp dwell/edge/poll out of a freshly-loaded
        config. Pulled out of `main` so it can be re-run on every
        mtime reload — the previous version only parsed these at
        startup, so editing tunables required a daemon restart."""
        try:
            d = max(100, int(c.get("dwell_ms", "400")))
        except ValueError:
            d = 400
        try:
            e = max(2, int(c.get("edge_px", "6")))
        except ValueError:
            e = 6
        try:
            p = max(50, int(c.get("poll_ms", "200")))
        except ValueError:
            p = 200
        return d, e, p

    cfg = load_conf()
    cfg_mtime = CONF.stat().st_mtime if CONF.exists() else 0.0
    dwell, edge, poll = parse_tunables(cfg)
    log.info("started dwell=%d edge=%d poll=%d", dwell, edge, poll)

    in_zone: Optional[str] = None
    zone_since = 0.0
    fired_this_dwell = False

    while not stop["flag"]:
        # Hot-reload config if it was edited. Tunables (dwell/edge/
        # poll) are re-parsed too so changes take effect without a
        # daemon restart.
        try:
            mt = CONF.stat().st_mtime if CONF.exists() else 0.0
            if mt != cfg_mtime:
                cfg = load_conf()
                cfg_mtime = mt
                new_dwell, new_edge, new_poll = parse_tunables(cfg)
                if (new_dwell, new_edge, new_poll) != \
                        (dwell, edge, poll):
                    log.info(
                        "tunables changed: dwell %d->%d  "
                        "edge %d->%d  poll %d->%d",
                        dwell, new_dwell,
                        edge, new_edge,
                        poll, new_poll)
                    dwell, edge, poll = new_dwell, new_edge, new_poll
                else:
                    log.info("config reloaded (corner actions only)")
        except OSError:
            pass

        pos = cursor_pos()
        bb = screen_bounds()
        if pos is None or bb is None:
            time.sleep(poll / 1000.0)
            continue

        zone = in_corner(pos, bb, edge)
        now = time.monotonic()
        if zone != in_zone:
            in_zone = zone
            zone_since = now
            fired_this_dwell = False
        elif (zone is not None
              and not fired_this_dwell
              and (now - zone_since) * 1000.0 >= dwell):
            action = cfg.get(zone, "none")
            if action != "none":
                fire(action)
            fired_this_dwell = True

        time.sleep(poll / 1000.0)

    try:
        pid_file.unlink()
    except OSError:
        pass
    log.info("stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
