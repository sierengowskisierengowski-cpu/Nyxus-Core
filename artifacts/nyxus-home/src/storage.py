# ============================================
# NYXUS Home — storage layer
# © 2026 Joseph A. Sierengowski
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
Persistent storage:

* Notepad text  → ~/.local/share/nyxus-home/notepad.txt
* Notif state   → ~/.local/share/nyxus-home/notif_state.json (dismissed ids)
* Weather/UI    → ~/.config/nyxus-home/config.json
* Password META → ~/.local/share/nyxus-home/passwords.json (NO PASSWORDS HERE)
* Password VAL  → Secret Service (gnome-keyring) via python-keyring,
                  service "nyxus-home", username = entry id

If the keyring backend is unavailable we fall back to a JSON file with a
loud `__plaintext_fallback` flag so the UI can warn the user. We never
silently leak a password to disk.
"""

import json
import os
import secrets
import string
import time
from typing import Dict, List, Optional

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


CONFIG_DIR = os.path.expanduser("~/.config/nyxus-home")
DATA_DIR   = os.path.expanduser("~/.local/share/nyxus-home")
os.makedirs(CONFIG_DIR, exist_ok=True)
os.makedirs(DATA_DIR,   exist_ok=True)

CONFIG_FILE   = os.path.join(CONFIG_DIR, "config.json")
NOTEPAD_FILE  = os.path.join(DATA_DIR,   "notepad.txt")
NOTIF_FILE    = os.path.join(DATA_DIR,   "notif_state.json")
PW_INDEX_FILE = os.path.join(DATA_DIR,   "passwords.json")
PW_FALLBACK   = os.path.join(DATA_DIR,   "passwords_plaintext.json")  # only if keyring missing

KEYRING_SERVICE = "nyxus-home"

DEFAULT_CONFIG = {
    "weather": {
        "lat": 40.7128,
        "lon": -74.0060,
        "label": "New York, NY",
        "unit": "fahrenheit",
    },
    "ui": {"graffiti_density": "high"},
}


# ── CONFIG (weather location, etc.) ─────────────────────────────────────
def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return dict(DEFAULT_CONFIG)
    # Merge with defaults
    out = dict(DEFAULT_CONFIG)
    for k, v in data.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k].update(v)
        else:
            out[k] = v
    return out


def save_config(cfg: dict) -> None:
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ── NOTEPAD ─────────────────────────────────────────────────────────────
def load_notepad() -> str:
    if not os.path.exists(NOTEPAD_FILE):
        return ""
    try:
        with open(NOTEPAD_FILE, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""


def save_notepad(text: str) -> None:
    tmp = NOTEPAD_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, NOTEPAD_FILE)


# ── NOTIFICATION DISMISSAL STATE ────────────────────────────────────────
def load_dismissed_notifs() -> List[str]:
    if not os.path.exists(NOTIF_FILE):
        return []
    try:
        with open(NOTIF_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("dismissed", [])
    except Exception:
        return []


def save_dismissed_notifs(ids: List[str]) -> None:
    with open(NOTIF_FILE, "w", encoding="utf-8") as f:
        json.dump({"dismissed": ids}, f, indent=2)


# ── PASSWORDS ───────────────────────────────────────────────────────────
class PasswordStore:
    """
    Thin wrapper over python-keyring with a plaintext fallback.
    Caller treats it as a CRUD store of {id, site, user, created} and
    fetches the password value via .get_password(id).
    """

    def __init__(self):
        self._kr = None
        self._kr_error: Optional[str] = None
        try:
            import keyring                                  # noqa: WPS433
            self._kr = keyring
            # Sanity check that a backend is actually wired up
            backend = keyring.get_keyring()
            name = type(backend).__name__
            if "Fail" in name or "Null" in name:
                self._kr = None
                self._kr_error = f"keyring backend is {name} (no Secret Service?)"
        except Exception as e:
            self._kr_error = f"keyring import failed: {e}"

    @property
    def secure(self) -> bool:
        return self._kr is not None

    @property
    def backend_status(self) -> str:
        if self.secure:
            try:
                name = type(self._kr.get_keyring()).__name__
            except Exception:
                name = "unknown"
            return f"OS keyring · {name}"
        return f"plaintext fallback · {self._kr_error or 'no keyring'}"

    # ── index ──
    def _load_index(self) -> List[Dict]:
        if not os.path.exists(PW_INDEX_FILE):
            return []
        try:
            with open(PW_INDEX_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("entries", [])
        except Exception:
            return []

    def _save_index(self, entries: List[Dict]) -> None:
        tmp = PW_INDEX_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"entries": entries, "saved_at": time.time()}, f, indent=2)
        os.replace(tmp, PW_INDEX_FILE)

    def list_entries(self) -> List[Dict]:
        return self._load_index()

    # ── plaintext fallback ──
    def _fallback_load(self) -> Dict[str, str]:
        if not os.path.exists(PW_FALLBACK):
            return {}
        try:
            with open(PW_FALLBACK, "r", encoding="utf-8") as f:
                return json.load(f).get("values", {})
        except Exception:
            return {}

    def _fallback_save(self, values: Dict[str, str]) -> None:
        tmp = PW_FALLBACK + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(
                {"__plaintext_fallback": True,
                 "warning": "no Secret Service backend available",
                 "values": values},
                f, indent=2,
            )
        os.replace(tmp, PW_FALLBACK)
        os.chmod(PW_FALLBACK, 0o600)

    # ── CRUD ──
    def add(self, site: str, user: str, pw: str) -> Dict:
        entry = {
            "id":      f"{int(time.time())}_{secrets.token_hex(3)}",
            "site":    site.strip(),
            "user":    user.strip(),
            "created": time.time(),
        }
        if self.secure:
            self._kr.set_password(KEYRING_SERVICE, entry["id"], pw)
        else:
            vals = self._fallback_load()
            vals[entry["id"]] = pw
            self._fallback_save(vals)

        entries = self._load_index()
        entries.insert(0, entry)
        self._save_index(entries)
        return entry

    def delete(self, entry_id: str) -> None:
        if self.secure:
            try:
                self._kr.delete_password(KEYRING_SERVICE, entry_id)
            except Exception:
                pass
        else:
            vals = self._fallback_load()
            vals.pop(entry_id, None)
            self._fallback_save(vals)

        entries = [e for e in self._load_index() if e["id"] != entry_id]
        self._save_index(entries)

    def get_password(self, entry_id: str) -> str:
        if self.secure:
            try:
                v = self._kr.get_password(KEYRING_SERVICE, entry_id)
                return v or ""
            except Exception:
                return ""
        return self._fallback_load().get(entry_id, "")


# ── PASSWORD GENERATOR ──────────────────────────────────────────────────
ALPHABETS = {
    "upper": string.ascii_uppercase,
    "lower": string.ascii_lowercase,
    "num":   string.digits,
    "sym":   "!@#$%^&*()-_=+[]{};:,.<>?/~",
}


def generate_password(length: int = 18,
                      use_upper: bool = True,
                      use_lower: bool = True,
                      use_num:   bool = True,
                      use_sym:   bool = True) -> str:
    pool = ""
    if use_upper: pool += ALPHABETS["upper"]
    if use_lower: pool += ALPHABETS["lower"]
    if use_num:   pool += ALPHABETS["num"]
    if use_sym:   pool += ALPHABETS["sym"]
    if not pool:
        return ""
    return "".join(secrets.choice(pool) for _ in range(int(length)))
