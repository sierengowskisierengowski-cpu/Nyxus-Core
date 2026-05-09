# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · auth.py
Passwordless session + persistent device key.

The app no longer prompts for a master password. Cases are still encrypted at
rest with AES-256-GCM, but the key is generated once on first launch and
stored at ~/.config/nyxus-intel/device.key (mode 0600). The Session object
exposes that key (hex-encoded) via .password() so the rest of the codebase
(case_manager, encryption.encrypt_case) keeps working unchanged.

If a legacy auth.json (with a bcrypt hash from an earlier build) is found,
it is removed on first run — there is nothing to migrate because the user
could never get past the lock screen to create cases.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import os
import json
import time
import secrets
from pathlib import Path
from typing import Optional, Callable, List

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


CONFIG_DIR  = Path.home() / ".config" / "nyxus-intel"
CONFIG_FILE = CONFIG_DIR / "config.json"
KEY_FILE    = CONFIG_DIR / "device.key"
LEGACY_AUTH = CONFIG_DIR / "auth.json"     # bcrypt hash from older build


def _load(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text("utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save(path: Path, data: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), "utf-8")
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def load_config() -> dict:
    cfg = _load(CONFIG_FILE)
    cfg.setdefault("disclaimer_accepted_at", 0)
    cfg.setdefault("api_keys", {})
    cfg.setdefault("autostart_search", True)
    cfg.setdefault("auto_pdf",         True)
    cfg.setdefault("show_raw_tab",     False)
    cfg.setdefault("default_depth",    "thorough")  # 'quick' | 'thorough'
    cfg.setdefault("backup_schedule",  "manual")    # 'manual' | 'daily' | 'weekly'
    return cfg


def save_config(cfg: dict) -> None:
    _save(CONFIG_FILE, cfg)


# ── device key ────────────────────────────────────────────────────────────
def _purge_legacy() -> None:
    """Delete bcrypt-hash file from the password-protected build, if any."""
    try:
        if LEGACY_AUTH.exists():
            LEGACY_AUTH.unlink()
    except OSError:
        pass


def get_or_create_device_key() -> bytes:
    """Return the 32-byte device encryption key, creating it on first call.

    The key is written to ~/.config/nyxus-intel/device.key with mode 0600.
    Losing this file means losing access to every encrypted case.
    """
    _purge_legacy()
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_FILE.exists():
        try:
            data = KEY_FILE.read_bytes()
            if len(data) == 32:
                return data
        except OSError:
            pass
    # Generate a fresh 256-bit key
    key = secrets.token_bytes(32)
    tmp = KEY_FILE.with_suffix(KEY_FILE.suffix + ".tmp")
    tmp.write_bytes(key)
    os.replace(tmp, KEY_FILE)
    try:
        os.chmod(KEY_FILE, 0o600)
    except OSError:
        pass
    return key


# Backwards-compat shims so older imports don't crash. Always return True/no-op.
def is_password_set() -> bool:
    return True


def set_password(_plaintext: str) -> None:  # pragma: no cover
    return None


def verify_password(_plaintext: str) -> bool:  # pragma: no cover
    return True


def change_password(_old: str, _new: str) -> bool:  # pragma: no cover
    return True


# ── session ───────────────────────────────────────────────────────────────
class Session:
    """Passwordless session.

    Always reports unlocked. .password() returns the device key as a hex
    string so the existing PBKDF2-based case encryption still works without
    changes elsewhere in the codebase.
    """

    def __init__(self, on_lock: Optional[Callable[[], None]] = None):
        self._on_lock = on_lock  # kept for API compat, never invoked
        self._listeners: List[Callable[[bool], None]] = []
        self._key_hex: str = get_or_create_device_key().hex()
        self._unlocked_at: float = time.time()
        self._cfg = load_config()

    # ── pwd (no-op shims) ────────────────────────────────────────────────
    def attempt_unlock(self, _plaintext: str) -> bool:
        self._unlocked_at = time.time()
        self._notify(True)
        return True

    def lock(self) -> None:
        # No-op: the app is passwordless. Kept so settings/menu code can call
        # this without needing a feature check. We still notify listeners so
        # any "session locked" UI updates work consistently.
        self._notify(False)
        self._notify(True)

    def is_unlocked(self) -> bool:
        return True

    def password(self) -> str:
        """Return the hex device key. Used as KDF input by encryption.py."""
        return self._key_hex

    # ── auto-lock (no-op) ────────────────────────────────────────────────
    def touch(self) -> None:
        self._unlocked_at = time.time()

    def check_auto_lock(self) -> bool:
        return False

    def reload_config(self) -> None:
        self._cfg = load_config()

    # ── observer ─────────────────────────────────────────────────────────
    def add_listener(self, fn: Callable[[bool], None]) -> None:
        self._listeners.append(fn)

    def _notify(self, unlocked: bool) -> None:
        for fn in list(self._listeners):
            try: fn(unlocked)
            except Exception: pass

    # ── disclaimer ───────────────────────────────────────────────────────
    def disclaimer_accepted(self) -> bool:
        return bool(self._cfg.get("disclaimer_accepted_at"))

    def accept_disclaimer(self) -> None:
        self._cfg["disclaimer_accepted_at"] = int(time.time())
        save_config(self._cfg)

    @property
    def fail_count(self) -> int:
        return 0

    @property
    def fail_limit(self) -> int:
        return 0
