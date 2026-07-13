"""
NYXUS Start — settings + config persistence.

Two JSON files in ~/.config/nyxus-start/:
    config.json   — user preferences
    pins.json     — list of pinned .desktop ids (and arbitrary-command pins)
    recent.json   — last 10 launched apps (rotating)

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations
import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List

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


CFG_DIR     = Path(os.path.expanduser("~/.config/nyxus-start"))
CFG_FILE    = CFG_DIR / "config.json"
PINS_FILE   = CFG_DIR / "pins.json"
RECENT_FILE = CFG_DIR / "recent.json"
SCRATCH_FILE = CFG_DIR / "scratchpad.txt"
AVATAR_DIR  = CFG_DIR / "avatars"

CFG_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_PINS: List[str] = [
    "nyxus-store",       # NYXUS App Store — discover/install all NYXUS apps
    "nyxus-terminal",
    "nyxus-settings",
    "nyxus-control",
    "nyxus-sysmon",
    "nyxus-security",
    "godsapp",
    "nyxus-sage",
    "nyxus-notepad",
    "nyxus-stickies",
    "nyxus-weather",
    "nyxus-panel",
    "thunar",
    "firefox",
    "chromium",
    "discord",
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "user_name":        "Joey",
    "user_avatar":      "",
    "user_subtitle":    "operator",
    "reduce_animations": False,
    "search_focus_on_open": True,
    "max_recent":       10,
    "max_all_apps":     500,
    "notepad_visible":  True,
}


def load_config() -> Dict[str, Any]:
    if not CFG_FILE.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with CFG_FILE.open() as f:
            data = json.load(f)
        merged = dict(DEFAULT_CONFIG)
        merged.update({k: v for k, v in data.items() if k in DEFAULT_CONFIG})
        return merged
    except (OSError, ValueError):
        return dict(DEFAULT_CONFIG)


def save_config(cfg: Dict[str, Any]) -> None:
    try:
        with CFG_FILE.open("w") as f:
            json.dump(cfg, f, indent=2)
    except OSError:
        pass


def load_pins() -> List[str]:
    if not PINS_FILE.exists():
        save_pins(DEFAULT_PINS)
        return list(DEFAULT_PINS)
    try:
        with PINS_FILE.open() as f:
            data = json.load(f)
        if isinstance(data, list):
            return [str(x) for x in data]
    except (OSError, ValueError):
        pass
    return list(DEFAULT_PINS)


def save_pins(pins: List[str]) -> None:
    try:
        with PINS_FILE.open("w") as f:
            json.dump(pins, f, indent=2)
    except OSError:
        pass


def load_recent() -> List[Dict[str, Any]]:
    if not RECENT_FILE.exists():
        return []
    try:
        with RECENT_FILE.open() as f:
            data = json.load(f)
        if isinstance(data, list):
            return [d for d in data if isinstance(d, dict) and "id" in d]
    except (OSError, ValueError):
        pass
    return []


def push_recent(app_id: str, name: str, icon: str = "") -> None:
    """Add or move an app to the head of recent (capped at 10)."""
    items = load_recent()
    items = [r for r in items if r.get("id") != app_id]
    items.insert(0, {
        "id":   app_id,
        "name": name,
        "icon": icon,
        "ts":   int(time.time()),
    })
    items = items[:10]
    try:
        with RECENT_FILE.open("w") as f:
            json.dump(items, f, indent=2)
    except OSError:
        pass


def clear_recent() -> None:
    try:
        if RECENT_FILE.exists():
            RECENT_FILE.unlink()
    except OSError:
        pass


# ──────────────────────────────────────── scratchpad (built-in notepad)
def load_scratch() -> str:
    """Return the persisted scratchpad text (empty string if missing)."""
    if not SCRATCH_FILE.exists():
        return ""
    try:
        return SCRATCH_FILE.read_text(encoding="utf-8")
    except OSError:
        return ""


def save_scratch(text: str) -> None:
    """Persist scratchpad text. Best-effort, silent on failure."""
    try:
        SCRATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
        SCRATCH_FILE.write_text(text or "", encoding="utf-8")
    except OSError:
        pass


# ──────────────────────────────────────── profile (avatar copy-in)
def store_avatar(src_path: str) -> str:
    """
    Copy a user-chosen avatar image into ~/.config/nyxus-start/avatars/
    so the path stays valid even if the source is later moved/deleted.
    Returns the destination path (or "" on failure).
    """
    if not src_path:
        return ""
    try:
        AVATAR_DIR.mkdir(parents=True, exist_ok=True)
        src = Path(src_path)
        if not src.exists():
            return ""
        ext = src.suffix.lower() or ".png"
        if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"):
            ext = ".png"
        dst = AVATAR_DIR / f"avatar-{int(time.time())}{ext}"
        dst.write_bytes(src.read_bytes())
        return str(dst)
    except OSError:
        return ""
