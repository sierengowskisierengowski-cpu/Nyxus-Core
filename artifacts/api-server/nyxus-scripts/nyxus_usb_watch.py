#!/usr/bin/env python3
"""nyxus-usb-watch — toast on USB block-device add/remove.

Tails `udevadm monitor --udev --subsystem-match=block` and emits a
desktop notification through `notify-send` whenever a removable storage
device or media is plugged in or unplugged.

Why udevadm rather than pyudev: zero Python deps beyond stdlib so this
ships in the airootfs without needing a virtualenv.

Logs to ~/.cache/nyxus/usb-watch.log per the cross-cutting rule.
Designed to run as a user systemd service (nyxus-usb-watch.service);
SIGTERM/SIGINT exit cleanly.
"""
from __future__ import annotations

import logging
import os
import signal
import subprocess
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_DIR = Path.home() / ".cache" / "nyxus"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "usb-watch.log"

logger = logging.getLogger("nyxus-usb-watch")
logger.setLevel(logging.INFO)
_h = RotatingFileHandler(LOG_PATH, maxBytes=512_000, backupCount=2)
_h.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logger.addHandler(_h)


def have(cmd: str) -> bool:
    from shutil import which
    return which(cmd) is not None


def notify(summary: str, body: str = "", urgency: str = "normal") -> None:
    if not have("notify-send"):
        logger.warning("notify-send missing — skipping toast: %s", summary)
        return
    try:
        subprocess.run(
            ["notify-send", "-u", urgency, "-a", "NYXUS", "-i",
             "drive-removable-media", summary, body],
            timeout=3,
            check=False)
    except Exception as e:
        logger.warning("notify-send: %s", e)


def main() -> int:
    if not have("udevadm"):
        logger.error("udevadm not on PATH; cannot watch USB events")
        return 2

    logger.info("nyxus-usb-watch starting (pid=%d)", os.getpid())

    # Track the currently-pending event so we can emit one toast per
    # block-device add/remove rather than one per attribute line.
    proc = subprocess.Popen(
        ["udevadm", "monitor", "--udev",
         "--subsystem-match=block", "--property"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    def _term(_sig: int, _frm: object) -> None:
        logger.info("nyxus-usb-watch stopping")
        try:
            proc.terminate()
        except Exception:
            pass
        sys.exit(0)

    signal.signal(signal.SIGTERM, _term)
    signal.signal(signal.SIGINT, _term)

    action: str = ""
    devname: str = ""
    devtype: str = ""
    id_model: str = ""
    id_vendor: str = ""

    assert proc.stdout is not None
    for raw in proc.stdout:
        line = raw.rstrip("\n")
        # Header line marks a new event; flush previous before resetting.
        if line.startswith("UDEV  ") or line.startswith("KERNEL"):
            _flush(action, devname, devtype, id_model, id_vendor)
            action = ""
            devname = ""
            devtype = ""
            id_model = ""
            id_vendor = ""
            # Parse the header itself for an action verb in [brackets].
            #   "UDEV  [12345.678] add /devices/... (block)"
            parts = line.split()
            if len(parts) >= 3:
                action = parts[2].strip()
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip()
        if k == "DEVNAME":
            devname = v
        elif k == "DEVTYPE":
            devtype = v
        elif k == "ID_MODEL":
            id_model = v.replace("_", " ")
        elif k == "ID_VENDOR":
            id_vendor = v.replace("_", " ")
    # Last event flush (only reached on EOF, e.g. udevadm killed).
    _flush(action, devname, devtype, id_model, id_vendor)
    return 0


def _flush(action: str, devname: str, devtype: str,
           id_model: str, id_vendor: str) -> None:
    if not action or action not in ("add", "remove"):
        return
    if devtype not in ("disk", "partition"):
        return
    if not devname:
        return
    title_bits = [b for b in (id_vendor, id_model) if b]
    title = " ".join(title_bits) if title_bits else devname
    if action == "add":
        notify(f"Device connected: {title}",
               f"{devname} ({devtype})", urgency="normal")
        logger.info("add %s vendor=%r model=%r type=%s",
                    devname, id_vendor, id_model, devtype)
    else:
        notify(f"Device removed: {title}",
               f"{devname} ({devtype})", urgency="low")
        logger.info("remove %s type=%s", devname, devtype)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(0)
    except Exception as e:
        logger.exception("fatal: %s", e)
        raise
