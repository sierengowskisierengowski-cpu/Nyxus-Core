"""
NYXUS Start — GowskiNet quick status.

Probes four signals (best-effort, never blocks UI):
    Phantom    — `pgrep -f nyxus-phantom` and/or systemd unit
    Honeypot   — counter from ~/.nyxus/honeypot/attacks.count or journalctl
    VPN        — `nmcli con show --active` for any vpn / wireguard
    Network    — does ping/curl reach a known anchor

Each probe is fast and safe to call from a GLib timer.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations
import os
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Dict

# ── NYXUS palette (single source of truth · rev r13) ────────────────
try:
    from nyxus_palette import (
        WHITE_PURE, WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        INK_FADED, INK_BLACK,
        GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE, HAIRLINE_INK,
        SHADOW_INK_ACTIVE, SHADOW_INK_INACTIVE,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
        format_css, assert_no_forbidden,
    )
except Exception:
    # palette module is shipped alongside every NYXUS app via
    # nyxus_install.sh; if it's missing, fall back to literals so
    # the app still launches.
    WHITE_PURE='#ffffff'; WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    INK_FADED='#0a0a0a'; INK_BLACK='#000000'
    GLASS_DARK='rgba(8, 12, 20, 0.55)'
    GLASS_DEEPER='rgba(15, 20, 32, 0.72)'
    GLASS_DEEPEST='rgba(5, 7, 12, 0.92)'
    HAIRLINE_WHITE='rgba(255, 255, 255, 0.10)'
    HAIRLINE_INK='rgba(0, 0, 0, 0.45)'
    SHADOW_INK_ACTIVE='rgba(0, 0, 0, 0.65)'
    SHADOW_INK_INACTIVE='rgba(0, 0, 0, 0.20)'
    RADIUS_CARD=14; RADIUS_PILL=12; RADIUS_INPUT=10
    FONT_UI='Inter'; FONT_MONO='JetBrains Mono'; FONT_DISPLAY='Inter Display'
    def format_css(t):
        _d = {
            'WHITE_PURE': WHITE_PURE, 'WHITE_OFF': WHITE_OFF,
            'GREY_LIGHT': GREY_LIGHT, 'GREY_MID': GREY_MID,
            'GREY_TERTIARY': GREY_TERTIARY,
            'INK_FADED': INK_FADED, 'INK_BLACK': INK_BLACK,
            'GLASS_DARK': GLASS_DARK, 'GLASS_DEEPER': GLASS_DEEPER,
            'GLASS_DEEPEST': GLASS_DEEPEST,
            'HAIRLINE_WHITE': HAIRLINE_WHITE, 'HAIRLINE_INK': HAIRLINE_INK,
            'SHADOW_INK_ACTIVE': SHADOW_INK_ACTIVE,
            'SHADOW_INK_INACTIVE': SHADOW_INK_INACTIVE,
            'RADIUS_CARD': RADIUS_CARD, 'RADIUS_PILL': RADIUS_PILL,
            'RADIUS_INPUT': RADIUS_INPUT,
            'FONT_UI': FONT_UI, 'FONT_MONO': FONT_MONO,
            'FONT_DISPLAY': FONT_DISPLAY,
        }
        return t.format_map(_d)
    def assert_no_forbidden(*a, **k): pass
# ─────────────────────────────────────────────────────────────────────



def _has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _run(parts: list, timeout: float = 1.5) -> str:
    try:
        out = subprocess.check_output(parts, timeout=timeout,
                                      stderr=subprocess.DEVNULL)
        return out.decode("utf-8", errors="ignore")
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return ""


def phantom_running() -> bool:
    if _has("pgrep"):
        out = _run(["pgrep", "-f", "nyxus-phantom"])
        if out.strip():
            return True
    if _has("systemctl"):
        out = _run(["systemctl", "--user", "is-active", "nyxus-phantom"])
        if out.strip() == "active":
            return True
        out = _run(["systemctl", "is-active", "nyxus-phantom"])
        if out.strip() == "active":
            return True
    return False


def honeypot_attacks() -> int:
    p = Path(os.path.expanduser("~/.nyxus/honeypot/attacks.count"))
    if p.exists():
        try:
            return int(p.read_text().strip())
        except (OSError, ValueError):
            pass
    log = Path(os.path.expanduser("~/.nyxus/honeypot/attacks.log"))
    if log.exists():
        try:
            count = 0
            with log.open() as f:
                for _ in f:
                    count += 1
            return count
        except OSError:
            pass
    return 0


def vpn_connected() -> bool:
    if _has("nmcli"):
        out = _run(["nmcli", "-t", "-f", "TYPE,NAME", "con", "show", "--active"])
        for line in out.splitlines():
            if line.startswith("vpn:") or line.startswith("wireguard:"):
                return True
    if _has("wg"):
        out = _run(["wg", "show"])
        if out.strip():
            return True
    return False


def network_online() -> bool:
    """Single fast TCP probe — no DNS, no payload."""
    for host, port in (("1.1.1.1", 53), ("8.8.8.8", 53), ("9.9.9.9", 53)):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(0.6)
            s.connect((host, port))
            s.close()
            return True
        except OSError:
            continue
    return False


def gather() -> Dict[str, dict]:
    """Run all probes. Returned shape is ready for the UI to render."""
    phantom = phantom_running()
    attacks = honeypot_attacks()
    vpn     = vpn_connected()
    online  = network_online()

    return {
        "phantom": {
            "label":  "Phantom",
            "value":  "running" if phantom else "stopped",
            "ok":     phantom,
            "glyph":  "\uf6d9",   # nf-fa-shield
            "target": "nyxus-control",
        },
        "honeypot": {
            "label":  "Honeypot",
            "value":  f"{attacks} attacks" if attacks else "0 attacks",
            "ok":     True,                   # informational, not a fault
            "glyph":  "\uf06e",   # nf-fa-eye
            "target": "nyxus-security",
        },
        "vpn": {
            "label":  "VPN",
            "value":  "connected" if vpn else "off",
            "ok":     vpn,
            "glyph":  "\uf084",   # nf-fa-key
            "target": "nm-connection-editor",
        },
        "network": {
            "label":  "GowskiNet",
            "value":  "online" if online else "offline",
            "ok":     online,
            "glyph":  "\uf0ac",   # nf-fa-globe
            "target": "nyxus-sysmon",
        },
    }
