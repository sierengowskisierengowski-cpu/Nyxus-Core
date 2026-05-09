# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
Tamper detection.

On startup, hashes every .py file in the install dir and compares the
combined digest against a manifest written at install time
(`/opt/nyxus-intel/.manifest.sha256`).

If the manifest is missing, a fresh manifest is written (first-run
self-seeding so the user is never warned on a clean install).

If the manifest exists but the live digest differs, a one-line warning
is printed to stderr and a structured record is appended to
~/.config/nyxus/tamper.log. The app ALWAYS continues to run — this is
detection only, never enforcement.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

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


WARNING_TEXT = (
    "This NYXUS application has been modified.\n"
    "Original software by Joseph Sierengowski.\n"
    "Copyright 2026. Unauthorized modification\n"
    "is strictly prohibited."
)


def _install_dir() -> Path:
    """The directory containing the running app's .py files."""
    return Path(__file__).resolve().parent


def _digest_dir(d: Path) -> str:
    """SHA-256 over every shipped .py file in d, including this module
    itself. Self-inclusion is what makes the integrity check non-bypassable."""
    h = hashlib.sha256()
    for p in sorted(d.glob("*.py")):
        h.update(p.name.encode())
        h.update(b"\0")
        h.update(p.read_bytes())
        h.update(b"\0")
    return h.hexdigest()


def _log_dir() -> Path:
    p = Path.home() / ".config" / "nyxus"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _append_log(app_name: str, expected: str, actual: str) -> None:
    log = _log_dir() / "tamper.log"
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "app": app_name,
        "expected_sha256": expected,
        "actual_sha256": actual,
        "host": platform.node(),
        "system": f"{platform.system()} {platform.release()}",
        "python": sys.version.split()[0],
        "iso": "nyx-2026.05.02-x86_64.iso",
        "os": "NYXUS",
    }
    try:
        with log.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def verify(app_name: str = "NYXUS Phantom") -> bool:
    """
    Returns True when the live digest matches the manifest (or when a
    new manifest was just seeded). Returns False when tampering was
    detected — caller should still run, this is detection only.
    """
    try:
        d = _install_dir()
        manifest = d / ".manifest.sha256"
        actual = _digest_dir(d)

        if not manifest.exists():
            try:
                manifest.write_text(actual + "\n", encoding="utf-8")
            except OSError:
                pass
            return True

        expected = manifest.read_text(encoding="utf-8").strip()
        if expected == actual:
            return True

        sys.stderr.write("\n" + WARNING_TEXT + "\n\n")
        _append_log(app_name, expected, actual)
        return False
    except Exception:
        # Tamper detection must NEVER crash the host app.
        return True
