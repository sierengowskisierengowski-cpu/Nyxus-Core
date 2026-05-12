"""
NYXUS Start — power options.

Tries multiple backends in order so it works on barebones systems too:
    lock      → hyprlock | swaylock | loginctl lock-session
    logout    → hyprctl dispatch exit | loginctl terminate-user
    suspend   → systemctl suspend | loginctl suspend
    restart   → systemctl reboot
    shutdown  → systemctl poweroff

All actions are detached so the Start panel can close cleanly.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations
import os
import shutil
import subprocess
from typing import List, Tuple

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


def _run_detached(parts: List[str]) -> bool:
    try:
        subprocess.Popen(parts, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (FileNotFoundError, OSError):
        return False


def lock_screen() -> bool:
    if _has("hyprlock") and _run_detached(["hyprlock"]):
        return True
    if _has("swaylock") and _run_detached(["swaylock", "-f"]):
        return True
    if _has("loginctl") and _run_detached(["loginctl", "lock-session"]):
        return True
    return False


def log_out() -> bool:
    if _has("hyprctl") and _run_detached(["hyprctl", "dispatch", "exit"]):
        return True
    if _has("loginctl") and os.environ.get("USER"):
        if _run_detached(["loginctl", "terminate-user", os.environ["USER"]]):
            return True
    return False


def suspend() -> bool:
    if _has("systemctl") and _run_detached(["systemctl", "suspend"]):
        return True
    if _has("loginctl") and _run_detached(["loginctl", "suspend"]):
        return True
    return False


def restart() -> bool:
    if _has("systemctl") and _run_detached(["systemctl", "reboot"]):
        return True
    return False


def shutdown() -> bool:
    if _has("systemctl") and _run_detached(["systemctl", "poweroff"]):
        return True
    return False


# ─────────────────────────────────── catalog for the UI to render
# Each entry: (key, label, glyph, color_hex, requires_confirmation)
POWER_ACTIONS: List[Tuple[str, str, str, str, bool]] = [
    ("lock",     "Lock",     "\uf023", "#9aa0ad", False),  # nf-fa-lock
    ("logout",   "Log Out",  "\uf2f5", "#c8ccd6", False),  # nf-fa-sign_out
    ("suspend",  "Suspend",  "\uf186", "#c8ccd6", False),  # nf-fa-moon
    ("restart",  "Restart",  "\uf021", "#e8edf5", True),   # nf-fa-refresh
    ("shutdown", "Shutdown", "\uf011", "#6a6e78", True),   # nf-fa-power_off
]


def perform(key: str) -> bool:
    return {
        "lock":     lock_screen,
        "logout":   log_out,
        "suspend":  suspend,
        "restart":  restart,
        "shutdown": shutdown,
    }.get(key, lambda: False)()
