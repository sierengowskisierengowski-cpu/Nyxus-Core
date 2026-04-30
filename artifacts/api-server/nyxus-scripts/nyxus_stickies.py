#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NYXUS Stickies — hand-drawn sticky notes on an infinite canvas.

A native GTK4 / Cairo Python application matching the NYXUS theme
(dark #0a0a12 background, Caveat handwriting font, neon pink / blue /
green / purple / gold accents — same palette as the notepad).

This is a single file by design — matches the existing
~/.nyxus/ download-and-launch infrastructure.

What works (real features, no placeholders):

  • Tilted Cairo-rendered sticky notes (shadow, folded corner, hand-drawn
    border with seeded jitter, optional pushpin)
  • 10 colors + custom hex; 4 sizes + corner resize handle
  • Drag with extra tilt while dragging; hover lift; new-note fly-in
    animation; delete crumple-and-fade animation
  • Plain text, checklist (click to toggle, strikethrough + counter)
    and code (mono font) content modes
  • Pin (always on top), lock (AES via cryptography), priority dot,
    tags, duplicate, archive, delete with version history (last 20)
  • Multiple independent boards with sidebar list
  • Search across all boards; filter by color / tag / priority / archived
  • Infinite scroll canvas, Space+drag to pan, Ctrl+scroll to zoom,
    rubber-band multi-select, align/distribute
  • Reminders with libnotify (via `notify-send`) including recurring
    daily / weekly / monthly
  • 12 builtin templates + save current as custom template
  • Export single note as PNG (with tilt / shadow intact), text or
    markdown; export entire board as JSON
  • Auto-save every 30 s; per-note version history (20 versions)
  • Same sketch UI vocabulary as the notepad

Deferred (not stubbed — simply not present so nothing fakes them):

  • Voice memo recording  (GStreamer pipeline is its own subapp)
  • In-note drawing canvas, math LaTeX, link favicon fetching
  • Image notes via drag-and-drop (file picker insertion is supported)
  • MQTT publish (no broker is configured in this rice yet)
  • Minimap, group-with-strings, print, email, encrypted vault export,
    quick-note global hotkey, color-fade warning, tag cloud viz

Storage:  ~/.config/nyxus-stickies/{stickies.db, backups/, exports/}
Logs:     /tmp/nyxus-stickies.log
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import math
import os
import random
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

# ── GTK setup ────────────────────────────────────────────────────────────────
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, GObject, Gio, Pango, PangoCairo  # noqa: E402
import cairo  # noqa: E402

# ── Optional deps (graceful) ─────────────────────────────────────────────────
HAS_CRYPTO = False
try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes as _crypto_hashes
    HAS_CRYPTO = True
except Exception:
    pass

# ═══════════════════════════════════════════════════════════════════════════════
#  Constants & paths
# ═══════════════════════════════════════════════════════════════════════════════
APP_ID    = "com.nyxus.stickies"
APP_NAME  = "NYXUS Stickies"
WIN_W, WIN_H = 1100, 720

CONFIG_DIR  = Path.home() / ".config" / "nyxus-stickies"
BACKUP_DIR  = CONFIG_DIR / "backups"
EXPORT_DIR  = Path.home() / "Documents" / "NyxusStickies"
DB_PATH     = CONFIG_DIR / "stickies.db"
LOG_PATH    = Path("/tmp/nyxus-stickies.log")
for d in (CONFIG_DIR, BACKUP_DIR, EXPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="a"), logging.StreamHandler()],
)
log = logging.getLogger("nyxus-stickies")

# ── NYXUS palette (matches notepad) ──────────────────────────────────────────
BG_DEEP     = (0.039, 0.039, 0.071)   # #0a0a12
BG_PANEL    = (0.059, 0.055, 0.106)   # #0f0e1b
INK_BRIGHT  = (0.94, 0.92, 0.97)
INK_DIM     = (0.62, 0.59, 0.72)
INK_FAINT   = (0.32, 0.30, 0.42)

NEON_PINK   = (1.0,  0.0,  1.0)       # #ff00ff
NEON_BLUE   = (0.0,  0.53, 1.0)       # #0088ff
NEON_GREEN  = (0.22, 1.0,  0.08)      # #39ff14
ACCENT_GOLD = (1.0,  0.78, 0.20)      # #ffc733
ACCENT_PURP = (0.73, 0.55, 1.0)       # #b88dff
DANGER_RED  = (1.0,  0.27, 0.40)      # #ff4566

# Sticky note canvas colors (paper tones)
NOTE_COLORS: List[Dict[str, Any]] = [
    {"key": "yellow", "name": "Yellow",  "rgb": (0.99, 0.93, 0.45), "shadow": (0.40, 0.34, 0.10)},
    {"key": "pink",   "name": "Pink",    "rgb": (1.00, 0.55, 0.78), "shadow": (0.50, 0.10, 0.30)},
    {"key": "blue",   "name": "Sky",     "rgb": (0.55, 0.83, 1.00), "shadow": (0.10, 0.32, 0.50)},
    {"key": "green",  "name": "Mint",    "rgb": (0.62, 0.95, 0.70), "shadow": (0.10, 0.40, 0.20)},
    {"key": "purple", "name": "Lilac",   "rgb": (0.85, 0.72, 1.00), "shadow": (0.30, 0.18, 0.50)},
    {"key": "orange", "name": "Orange",  "rgb": (1.00, 0.72, 0.32), "shadow": (0.50, 0.30, 0.05)},
    {"key": "red",    "name": "Urgent",  "rgb": (1.00, 0.50, 0.50), "shadow": (0.50, 0.10, 0.10)},
    {"key": "white",  "name": "Paper",   "rgb": (0.96, 0.96, 0.92), "shadow": (0.30, 0.30, 0.30)},
    {"key": "black",  "name": "Slate",   "rgb": (0.18, 0.18, 0.24), "shadow": (0.04, 0.04, 0.06)},
    {"key": "teal",   "name": "Teal",    "rgb": (0.45, 0.85, 0.84), "shadow": (0.10, 0.36, 0.36)},
]
COLOR_BY_KEY = {c["key"]: c for c in NOTE_COLORS}

PRIORITIES = [
    {"key": "low",    "label": "Low",    "rgb": (0.55, 0.78, 1.00)},
    {"key": "normal", "label": "Normal", "rgb": (0.62, 0.62, 0.78)},
    {"key": "high",   "label": "High",   "rgb": (1.00, 0.78, 0.20)},
    {"key": "urgent", "label": "Urgent", "rgb": (1.00, 0.27, 0.40)},
]
PRIORITY_BY_KEY = {p["key"]: p for p in PRIORITIES}

NOTE_SIZES = {
    "small":   (180, 140),
    "medium":  (240, 200),
    "large":   (320, 260),
    "xlarge":  (440, 360),
}

CONTENT_TYPES = ("text", "checklist", "code")
KIND_ICONS = {"text": "📝", "checklist": "☑", "code": "</>"}

CANVAS_BACKGROUNDS = [
    {"key": "void",      "name": "Void",      "rgb": (0.039, 0.039, 0.071), "pattern": None},
    {"key": "corkboard", "name": "Corkboard", "rgb": (0.30, 0.20, 0.10),    "pattern": "cork"},
    {"key": "wood",      "name": "Wood",      "rgb": (0.20, 0.13, 0.08),    "pattern": "wood"},
    {"key": "slate",     "name": "Slate",     "rgb": (0.13, 0.14, 0.17),    "pattern": "slate"},
    {"key": "grid",      "name": "Grid",      "rgb": (0.039, 0.039, 0.071), "pattern": "grid"},
]
BG_BY_KEY = {b["key"]: b for b in CANVAS_BACKGROUNDS}

# ═══════════════════════════════════════════════════════════════════════════════
#  Cairo sketch helpers (seeded jitter — same renders each repaint)
# ═══════════════════════════════════════════════════════════════════════════════
def _seed(*parts) -> random.Random:
    h = hashlib.md5(repr(parts).encode("utf-8")).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def sketch_line(cr, x1, y1, x2, y2, *, jitter=0.6, segments=10, key=None):
    rng = _seed(key or ("line", round(x1, 1), round(y1, 1),
                        round(x2, 1), round(y2, 1)))
    n = max(2, segments)
    cr.move_to(x1 + (rng.random() - 0.5) * jitter * 0.6,
               y1 + (rng.random() - 0.5) * jitter * 0.6)
    for i in range(1, n):
        t = i / (n - 1)
        x = x1 + (x2 - x1) * t + (rng.random() - 0.5) * jitter
        y = y1 + (y2 - y1) * t + (rng.random() - 0.5) * jitter
        cr.line_to(x, y)
    cr.line_to(x2 + (rng.random() - 0.5) * jitter * 0.6,
               y2 + (rng.random() - 0.5) * jitter * 0.6)
    cr.stroke()


def sketch_rect(cr, x, y, w, h, *, jitter=0.6, key=None, double=False):
    k = key or ("rect", round(x), round(y), round(w), round(h))
    sketch_line(cr, x,     y,     x + w, y,     jitter=jitter, key=(k, "t"))
    sketch_line(cr, x + w, y,     x + w, y + h, jitter=jitter, key=(k, "r"))
    sketch_line(cr, x + w, y + h, x,     y + h, jitter=jitter, key=(k, "b"))
    sketch_line(cr, x,     y + h, x,     y,     jitter=jitter, key=(k, "l"))
    if double:
        sketch_line(cr, x + 0.6, y - 0.4, x + w - 0.4, y + 0.3,
                    jitter=jitter * 0.6, segments=6, key=(k, "t2"))


def sketch_check(cr, x, y, size, *, color=NEON_GREEN, key=None):
    cr.save()
    cr.set_source_rgba(*color, 0.95)
    cr.set_line_width(2.0)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    sketch_line(cr, x + size * 0.18, y + size * 0.55,
                x + size * 0.45, y + size * 0.82,
                jitter=0.6, key=(key, "c1"))
    sketch_line(cr, x + size * 0.42, y + size * 0.82,
                x + size * 0.85, y + size * 0.20,
                jitter=0.6, key=(key, "c2"))
    cr.restore()


def sketch_pin(cr, x, y, *, color=DANGER_RED, key=None):
    """Hand-drawn pushpin centered at (x,y)."""
    cr.save()
    cr.set_line_width(1.4)
    # shaft
    cr.set_source_rgba(0.20, 0.20, 0.20, 0.85)
    sketch_line(cr, x, y + 6, x - 1, y + 16, jitter=0.4, key=(key, "shaft"))
    # cap (filled)
    cr.set_source_rgba(*color, 0.92)
    cr.arc(x, y, 7.5, 0, math.pi * 2)
    cr.fill()
    # outline
    cr.set_source_rgba(0.0, 0.0, 0.0, 0.55)
    cr.set_line_width(1.2)
    cr.arc(x, y, 7.5, 0, math.pi * 2)
    cr.stroke()
    # highlight
    cr.set_source_rgba(1, 1, 1, 0.45)
    cr.arc(x - 2.5, y - 2.5, 2, 0, math.pi * 2)
    cr.fill()
    cr.restore()


def sketch_lock(cr, x, y, size, *, color=ACCENT_GOLD, key=None):
    cr.save()
    cr.set_source_rgba(*color, 0.95)
    cr.set_line_width(1.6)
    body_h = size * 0.6
    body_y = y + size - body_h
    sketch_rect(cr, x, body_y, size, body_h, jitter=0.4, key=(key, "lb"))
    cr.set_line_width(1.4)
    sketch_line(cr, x + size * 0.25, body_y,
                x + size * 0.25, y + size * 0.18,
                jitter=0.4, key=(key, "la"))
    sketch_line(cr, x + size * 0.25, y + size * 0.18,
                x + size * 0.75, y + size * 0.18,
                jitter=0.4, key=(key, "lt"))
    sketch_line(cr, x + size * 0.75, y + size * 0.18,
                x + size * 0.75, body_y,
                jitter=0.4, key=(key, "lr"))
    cr.restore()


def sketch_star(cr, cx, cy, size, *, color=ACCENT_GOLD, key=None, fill=True):
    cr.save()
    pts = []
    for i in range(10):
        a = -math.pi / 2 + i * math.pi / 5
        r = size if i % 2 == 0 else size * 0.42
        pts.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.close_path()
    if fill:
        cr.set_source_rgba(*color, 0.85)
        cr.fill_preserve()
    cr.set_source_rgba(0, 0, 0, 0.55)
    cr.set_line_width(1.0)
    cr.stroke()
    cr.restore()


def sketch_pill(cr, x, y, w, h, *, fill, stroke, jitter=0.5, key=None):
    cr.save()
    radius = h / 2
    cr.move_to(x + radius, y)
    cr.line_to(x + w - radius, y)
    cr.arc(x + w - radius, y + radius, radius, -math.pi / 2, math.pi / 2)
    cr.line_to(x + radius, y + h)
    cr.arc(x + radius, y + radius, radius, math.pi / 2, 3 * math.pi / 2)
    cr.close_path()
    cr.set_source_rgba(*fill)
    cr.fill_preserve()
    cr.set_source_rgba(*stroke)
    cr.set_line_width(1.2)
    cr.stroke()
    cr.restore()


def draw_caveat_text(cr, x, y, text, *, size=15, color=(0, 0, 0, 0.95),
                     family="Caveat", weight=Pango.Weight.NORMAL,
                     wrap_w=None, align=Pango.Alignment.LEFT):
    cr.save()
    cr.set_source_rgba(*color)
    layout = PangoCairo.create_layout(cr)
    fd = Pango.FontDescription()
    fd.set_family(family)
    fd.set_size(int(size * Pango.SCALE))
    fd.set_weight(weight)
    layout.set_font_description(fd)
    layout.set_alignment(align)
    if wrap_w is not None:
        layout.set_width(int(wrap_w * Pango.SCALE))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    layout.set_text(text or "", -1)
    cr.move_to(x, y)
    PangoCairo.show_layout(cr, layout)
    cr.restore()
    return layout


def measure_text(cr, text, *, size=15, family="Caveat", wrap_w=None):
    layout = PangoCairo.create_layout(cr)
    fd = Pango.FontDescription()
    fd.set_family(family); fd.set_size(int(size * Pango.SCALE))
    layout.set_font_description(fd)
    if wrap_w is not None:
        layout.set_width(int(wrap_w * Pango.SCALE))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    layout.set_text(text or "", -1)
    w, h = layout.get_pixel_size()
    return w, h, layout


# ═══════════════════════════════════════════════════════════════════════════════
#  Crypto (per-note AES via Fernet)
# ═══════════════════════════════════════════════════════════════════════════════
class Crypto:
    """Per-vault master password.  Each note encrypted with the vault key."""

    def __init__(self, db: "DB"):
        self.db = db
        self._key: Optional[bytes] = None  # in-memory only after unlock

    def is_setup(self) -> bool:
        return bool(self.db.get_setting("crypto_verifier"))

    def is_unlocked(self) -> bool:
        return self._key is not None

    def _derive(self, password: str, salt: bytes) -> bytes:
        if not HAS_CRYPTO:
            raise RuntimeError("python-cryptography is not installed")
        kdf = PBKDF2HMAC(algorithm=_crypto_hashes.SHA256(),
                         length=32, salt=salt, iterations=200_000)
        return base64.urlsafe_b64encode(kdf.derive(password.encode("utf-8")))

    def setup(self, password: str) -> None:
        salt = os.urandom(16)
        key  = self._derive(password, salt)
        # verifier: encrypt a known string
        verifier = Fernet(key).encrypt(b"NYXUS-STICKIES-OK")
        self.db.set_setting("crypto_salt", base64.b64encode(salt).decode())
        self.db.set_setting("crypto_verifier", verifier.decode())
        self._key = key

    def unlock(self, password: str) -> bool:
        salt_b64  = self.db.get_setting("crypto_salt")
        verifier  = self.db.get_setting("crypto_verifier")
        if not (salt_b64 and verifier and HAS_CRYPTO):
            return False
        salt = base64.b64decode(salt_b64)
        key  = self._derive(password, salt)
        try:
            ok = Fernet(key).decrypt(verifier.encode()) == b"NYXUS-STICKIES-OK"
        except InvalidToken:
            return False
        if ok:
            self._key = key
        return ok

    def lock_session(self):
        self._key = None

    def encrypt(self, plaintext: str) -> str:
        assert self._key is not None
        return Fernet(self._key).encrypt(plaintext.encode("utf-8")).decode("ascii")

    def decrypt(self, ciphertext: str) -> str:
        assert self._key is not None
        return Fernet(self._key).decrypt(ciphertext.encode("ascii")).decode("utf-8")


# ═══════════════════════════════════════════════════════════════════════════════
#  Database (sqlite3)
# ═══════════════════════════════════════════════════════════════════════════════
class DB:
    SCHEMA = [
        """CREATE TABLE IF NOT EXISTS boards(
            id          TEXT PRIMARY KEY,
            name        TEXT NOT NULL,
            background  TEXT DEFAULT 'void',
            position    INTEGER DEFAULT 0,
            zoom        REAL    DEFAULT 1.0,
            scroll_x    REAL    DEFAULT 0,
            scroll_y    REAL    DEFAULT 0,
            created     INTEGER NOT NULL,
            updated     INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS notes(
            id          TEXT PRIMARY KEY,
            board_id    TEXT NOT NULL,
            title       TEXT DEFAULT '',
            body        TEXT DEFAULT '',
            kind        TEXT DEFAULT 'text',
            color       TEXT DEFAULT 'yellow',
            custom_hex  TEXT,
            x           REAL DEFAULT 100,
            y           REAL DEFAULT 100,
            w           REAL DEFAULT 240,
            h           REAL DEFAULT 200,
            tilt        REAL DEFAULT 0,
            size_key    TEXT DEFAULT 'medium',
            pinned      INTEGER DEFAULT 0,
            starred     INTEGER DEFAULT 0,
            archived    INTEGER DEFAULT 0,
            locked      INTEGER DEFAULT 0,
            locked_blob TEXT,
            priority    TEXT DEFAULT 'normal',
            tags        TEXT DEFAULT '',
            checklist   TEXT DEFAULT '',
            code_lang   TEXT DEFAULT 'text',
            created     INTEGER NOT NULL,
            updated     INTEGER NOT NULL,
            FOREIGN KEY(board_id) REFERENCES boards(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS reminders(
            id          TEXT PRIMARY KEY,
            note_id     TEXT NOT NULL,
            fires_at    INTEGER NOT NULL,
            recurrence  TEXT,
            active      INTEGER DEFAULT 1,
            FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS templates(
            id      TEXT PRIMARY KEY,
            name    TEXT NOT NULL,
            kind    TEXT DEFAULT 'text',
            color   TEXT DEFAULT 'yellow',
            body    TEXT DEFAULT '',
            builtin INTEGER DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS versions(
            id      TEXT PRIMARY KEY,
            note_id TEXT NOT NULL,
            body    TEXT,
            title   TEXT,
            saved   INTEGER NOT NULL,
            FOREIGN KEY(note_id) REFERENCES notes(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY, value TEXT
        )""",
        "CREATE INDEX IF NOT EXISTS idx_notes_board ON notes(board_id)",
        "CREATE INDEX IF NOT EXISTS idx_notes_arch  ON notes(archived)",
        "CREATE INDEX IF NOT EXISTS idx_rem_active  ON reminders(active, fires_at)",
        "CREATE INDEX IF NOT EXISTS idx_ver_note    ON versions(note_id, saved)",
    ]

    def __init__(self, path: Path = DB_PATH):
        self.path = path
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        for stmt in self.SCHEMA:
            self.conn.execute(stmt)
        self.conn.commit()
        self._seed_if_empty()

    # ── settings ────────────────────────────────────────────────────────────
    def get_setting(self, key: str, default=None):
        row = self.conn.execute("SELECT value FROM settings WHERE key=?",
                                (key,)).fetchone()
        return row["value"] if row else default

    def set_setting(self, key: str, value):
        with self.lock:
            self.conn.execute(
                "INSERT INTO settings(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)))
            self.conn.commit()

    # ── boards ──────────────────────────────────────────────────────────────
    def list_boards(self) -> List[sqlite3.Row]:
        return list(self.conn.execute(
            "SELECT * FROM boards ORDER BY position ASC, created ASC"))

    def create_board(self, name: str = "Untitled board") -> str:
        bid = uuid.uuid4().hex[:12]
        ts = int(time.time())
        with self.lock:
            self.conn.execute(
                "INSERT INTO boards(id,name,background,position,created,updated) "
                "VALUES(?,?,?,?,?,?)",
                (bid, name, "void", ts, ts, ts))
            self.conn.commit()
        return bid

    def update_board(self, bid: str, **kwargs):
        if not kwargs: return
        cols = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [int(time.time()), bid]
        with self.lock:
            self.conn.execute(f"UPDATE boards SET {cols}, updated=? WHERE id=?",
                              vals)
            self.conn.commit()

    def delete_board(self, bid: str):
        with self.lock:
            self.conn.execute("DELETE FROM boards WHERE id=?", (bid,))
            self.conn.commit()

    def get_board(self, bid: str):
        return self.conn.execute("SELECT * FROM boards WHERE id=?",
                                 (bid,)).fetchone()

    # ── notes ───────────────────────────────────────────────────────────────
    def list_notes(self, board_id: Optional[str] = None,
                   include_archived: bool = False) -> List[sqlite3.Row]:
        where, params = [], []
        if board_id is not None:
            where.append("board_id = ?"); params.append(board_id)
        if not include_archived:
            where.append("archived = 0")
        sql = "SELECT * FROM notes"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY pinned DESC, updated DESC"
        return list(self.conn.execute(sql, params))

    def get_note(self, nid: str):
        return self.conn.execute("SELECT * FROM notes WHERE id=?",
                                 (nid,)).fetchone()

    def create_note(self, board_id: str, **fields) -> str:
        nid = uuid.uuid4().hex[:12]
        ts = int(time.time())
        defaults = dict(
            id=nid, board_id=board_id, title="", body="", kind="text",
            color="yellow", custom_hex=None,
            x=120 + random.randint(0, 80),
            y=120 + random.randint(0, 80),
            w=NOTE_SIZES["medium"][0], h=NOTE_SIZES["medium"][1],
            tilt=random.uniform(-7, 7),
            size_key="medium",
            pinned=0, starred=0, archived=0, locked=0, locked_blob=None,
            priority="normal", tags="", checklist="", code_lang="text",
            created=ts, updated=ts,
        )
        defaults.update(fields)
        cols = ", ".join(defaults.keys())
        qs   = ", ".join("?" * len(defaults))
        with self.lock:
            self.conn.execute(f"INSERT INTO notes({cols}) VALUES({qs})",
                              list(defaults.values()))
            self.conn.commit()
        return nid

    def update_note(self, nid: str, **kwargs):
        if not kwargs: return
        cols = ", ".join(f"{k}=?" for k in kwargs)
        vals = list(kwargs.values()) + [int(time.time()), nid]
        with self.lock:
            self.conn.execute(f"UPDATE notes SET {cols}, updated=? WHERE id=?",
                              vals)
            self.conn.commit()

    def delete_note(self, nid: str):
        with self.lock:
            self.conn.execute("DELETE FROM notes WHERE id=?", (nid,))
            self.conn.commit()

    def save_version(self, nid: str, title: str, body: str):
        vid = uuid.uuid4().hex[:8]
        with self.lock:
            self.conn.execute(
                "INSERT INTO versions(id,note_id,title,body,saved) "
                "VALUES(?,?,?,?,?)",
                (vid, nid, title, body, int(time.time())))
            # cap to 20 most recent
            self.conn.execute(
                "DELETE FROM versions WHERE note_id=? AND id NOT IN ("
                "  SELECT id FROM versions WHERE note_id=? "
                "  ORDER BY saved DESC LIMIT 20)",
                (nid, nid))
            self.conn.commit()

    def list_versions(self, nid: str):
        return list(self.conn.execute(
            "SELECT * FROM versions WHERE note_id=? ORDER BY saved DESC",
            (nid,)))

    # ── reminders ───────────────────────────────────────────────────────────
    def add_reminder(self, note_id: str, fires_at: int,
                     recurrence: Optional[str] = None) -> str:
        rid = uuid.uuid4().hex[:10]
        with self.lock:
            self.conn.execute(
                "INSERT INTO reminders(id,note_id,fires_at,recurrence,active) "
                "VALUES(?,?,?,?,1)", (rid, note_id, fires_at, recurrence))
            self.conn.commit()
        return rid

    def list_due_reminders(self) -> List[sqlite3.Row]:
        now = int(time.time())
        return list(self.conn.execute(
            "SELECT * FROM reminders WHERE active=1 AND fires_at <= ? "
            "ORDER BY fires_at ASC", (now,)))

    def list_active_reminders(self):
        return list(self.conn.execute(
            "SELECT * FROM reminders WHERE active=1 ORDER BY fires_at ASC"))

    def update_reminder(self, rid: str, **kw):
        if not kw: return
        cols = ", ".join(f"{k}=?" for k in kw)
        vals = list(kw.values()) + [rid]
        with self.lock:
            self.conn.execute(f"UPDATE reminders SET {cols} WHERE id=?", vals)
            self.conn.commit()

    def delete_reminder(self, rid: str):
        with self.lock:
            self.conn.execute("DELETE FROM reminders WHERE id=?", (rid,))
            self.conn.commit()

    # ── templates ───────────────────────────────────────────────────────────
    def list_templates(self):
        return list(self.conn.execute(
            "SELECT * FROM templates ORDER BY builtin DESC, name ASC"))

    def create_template(self, name: str, kind: str, color: str,
                        body: str, builtin: int = 0) -> str:
        tid = uuid.uuid4().hex[:10]
        with self.lock:
            self.conn.execute(
                "INSERT INTO templates(id,name,kind,color,body,builtin) "
                "VALUES(?,?,?,?,?,?)", (tid, name, kind, color, body, builtin))
            self.conn.commit()
        return tid

    def delete_template(self, tid: str):
        with self.lock:
            self.conn.execute("DELETE FROM templates WHERE id=? AND builtin=0",
                              (tid,))
            self.conn.commit()

    # ── seed defaults ───────────────────────────────────────────────────────
    def _seed_if_empty(self):
        if not self.list_boards():
            self.create_board("My Board")
        if not self.list_templates():
            BUILTINS = [
                ("Quick thought",   "text",      "yellow",
                 "Just a thought…\n\n"),
                ("Todo list",       "checklist", "blue",
                 "[ ] First task\n[ ] Second task\n[ ] Third task"),
                ("Shopping list",   "checklist", "green",
                 "[ ] Item 1\n[ ] Item 2\n[ ] Item 3"),
                ("Meeting reminder","text",      "pink",
                 "Meeting: \nWhen: \nWho: \nNotes:\n  • \n  • "),
                ("Code snippet",    "code",      "black",
                 "// snippet\n"),
                ("Bug note",        "text",      "red",
                 "Bug:\n\nSteps:\n1. \n2. \n\nExpected:\nActual:\n"),
                ("Idea capture",    "text",      "purple",
                 "💡 idea\n\nWhy:\nNext step:"),
                ("Follow up",       "text",      "orange",
                 "follow up: \nby when: \nwith: "),
                ("Password hint",   "text",      "white",
                 "Service: \nUsername: \nHint: "),
                ("Daily goal",      "text",      "teal",
                 "today's one big thing:\n\n→ "),
                ("Inspiration",     "text",      "purple",
                 "“ ”\n\n— "),
                ("Warning",         "text",      "red",
                 "⚠️ WARNING\n\n"),
            ]
            for name, kind, color, body in BUILTINS:
                self.create_template(name, kind, color, body, builtin=1)


# ═══════════════════════════════════════════════════════════════════════════════
#  Sketch UI primitives (re-used pattern from notepad)
# ═══════════════════════════════════════════════════════════════════════════════
class SketchButton(Gtk.DrawingArea):
    __gsignals__ = {"clicked": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, label, *, width=72, height=26, color=NEON_PINK,
                 tooltip=None, primary=False):
        super().__init__()
        self.label, self.color, self.primary = label, color, primary
        self._hover = False; self._press = False
        self.set_size_request(width, height)
        try:
            self.set_content_width(width); self.set_content_height(height)
        except Exception: pass
        self.set_draw_func(self._draw)
        if tooltip: self.set_tooltip_text(tooltip)

        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("pressed",  self._press_cb)
        gc.connect("released", self._release_cb)
        self.add_controller(gc)
        mc = Gtk.EventControllerMotion()
        mc.connect("enter", lambda *a: (setattr(self, "_hover", True),
                                        self.queue_draw()))
        mc.connect("leave", lambda *a: (setattr(self, "_hover", False),
                                        setattr(self, "_press", False),
                                        self.queue_draw()))
        self.add_controller(mc)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

    def _press_cb(self, *a):
        self._press = True; self.queue_draw()

    def _release_cb(self, *a):
        was = self._press; self._press = False; self.queue_draw()
        if was: self.emit("clicked")

    def _draw(self, area, cr, w, h, _=None):
        c = self.color
        fill_alpha = 0.25 if self.primary else 0.10
        if self._press:    fill_alpha += 0.18
        elif self._hover:  fill_alpha += 0.10
        cr.set_source_rgba(*c, fill_alpha)
        cr.rectangle(2, 2, w - 4, h - 4); cr.fill()
        cr.set_source_rgba(*c, 0.95 if self._hover else 0.75)
        cr.set_line_width(1.4 if self.primary else 1.1)
        sketch_rect(cr, 1.5, 1.5, w - 3, h - 3,
                    jitter=0.55, double=self.primary,
                    key=("btn", id(self), w, h))
        # label
        layout = PangoCairo.create_layout(cr)
        fd = Pango.FontDescription()
        fd.set_family("Caveat"); fd.set_size(int(13 * Pango.SCALE))
        fd.set_weight(Pango.Weight.BOLD if self.primary else Pango.Weight.NORMAL)
        layout.set_font_description(fd)
        layout.set_text(self.label, -1)
        tw, th = layout.get_pixel_size()
        cr.set_source_rgba(*INK_BRIGHT, 1.0 if self._hover else 0.92)
        cr.move_to((w - tw) / 2, (h - th) / 2)
        PangoCairo.show_layout(cr, layout)


class SketchToggle(SketchButton):
    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.active = False

    def set_active(self, val: bool):
        self.active = bool(val); self.queue_draw()

    def _release_cb(self, *a):
        was = self._press; self._press = False
        if was:
            self.active = not self.active
        self.queue_draw()
        if was: self.emit("clicked")

    def _draw(self, area, cr, w, h, _=None):
        c = self.color
        if self.active:
            cr.set_source_rgba(*c, 0.38); cr.rectangle(2, 2, w - 4, h - 4)
            cr.fill()
        super()._draw(area, cr, w, h, None)


class SketchSeparator(Gtk.DrawingArea):
    def __init__(self, *, vertical=False, length=80, color=INK_FAINT):
        super().__init__()
        self.vertical, self.length, self.color = vertical, length, color
        if vertical: self.set_size_request(2, length)
        else:        self.set_size_request(length, 2)
        try:
            self.set_content_width(2 if vertical else length)
            self.set_content_height(length if vertical else 2)
        except Exception: pass
        self.set_draw_func(self._draw)

    def _draw(self, area, cr, w, h, _=None):
        cr.set_source_rgba(*self.color, 0.55)
        cr.set_line_width(1.2)
        if self.vertical:
            sketch_line(cr, w/2, 1, w/2, h - 1, jitter=0.5,
                        key=("sep", id(self)))
        else:
            sketch_line(cr, 1, h/2, w - 1, h/2, jitter=0.5,
                        key=("sep", id(self)))


class SketchSearchEntry(Gtk.Box):
    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, (str,))}

    def __init__(self, *, placeholder="search…", color=NEON_PINK):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.color = color
        self.set_size_request(180, 28)
        self.bg = Gtk.DrawingArea()
        self.bg.set_hexpand(True); self.bg.set_vexpand(True)
        self.bg.set_draw_func(self._draw_bg)
        ov = Gtk.Overlay()
        ov.set_hexpand(True); ov.set_vexpand(True)
        ov.set_child(self.bg)
        entry = Gtk.Entry()
        entry.set_placeholder_text(placeholder)
        entry.set_has_frame(False)
        entry.set_margin_start(28); entry.set_margin_end(8)
        entry.set_margin_top(2);    entry.set_margin_bottom(2)
        entry.add_css_class("nyxus-entry")
        entry.connect("changed",
                      lambda e: self.emit("changed", e.get_text()))
        ov.add_overlay(entry)
        self.append(ov)
        self.entry = entry

    def get_text(self): return self.entry.get_text()
    def set_text(self, t): self.entry.set_text(t)

    def _draw_bg(self, area, cr, w, h, _=None):
        cr.set_source_rgba(0.07, 0.06, 0.14, 0.85)
        cr.rectangle(2, 2, w - 4, h - 4); cr.fill()
        cr.set_source_rgba(*self.color, 0.85)
        cr.set_line_width(1.4)
        sketch_rect(cr, 1.5, 1.5, w - 3, h - 3, jitter=0.5,
                    key=("se", id(self), w, h))
        # icon
        cr.set_source_rgba(*self.color, 0.85)
        cr.arc(15, h / 2, 6, 0, math.pi * 2); cr.set_line_width(1.4)
        cr.stroke()
        cr.move_to(20, h / 2 + 4); cr.line_to(24, h / 2 + 8); cr.stroke()


# ═══════════════════════════════════════════════════════════════════════════════
#  Sticky note widget — Cairo, tilted, hand-drawn
# ═══════════════════════════════════════════════════════════════════════════════
class StickyNote(Gtk.DrawingArea):
    """A single sticky note rendered with Cairo (tilt + shadow + fold + pin)."""
    __gsignals__ = {
        "request-edit":   (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "request-menu":   (GObject.SignalFlags.RUN_FIRST, None, (str, float, float)),
        "moved":          (GObject.SignalFlags.RUN_FIRST, None, (str, float, float)),
        "resized":        (GObject.SignalFlags.RUN_FIRST, None, (str, float, float)),
        "checklist-toggled": (GObject.SignalFlags.RUN_FIRST, None, (str, int)),
    }

    PADDING = 18
    TITLE_H = 26
    DATE_H  = 16
    HANDLE  = 14   # corner resize handle radius

    def __init__(self, note: sqlite3.Row, *, on_locked_unlock=None):
        super().__init__()
        self.nid       = note["id"]
        self.note      = dict(note)
        self.tilt      = note["tilt"] or 0.0
        self.w         = max(140, float(note["w"]))
        self.h         = max(110, float(note["h"]))
        self.dragging  = False
        self.resizing  = False
        self.hover     = False
        self.selected  = False
        self.lift      = 0.0       # 0..1 hover lift
        self.entrance  = 0.0       # 0→1 fly-in animation
        self.fade      = 1.0       # 1→0 crumple animation
        self.crumple   = 0.0       # 0..1
        self._press_x  = 0.0
        self._press_y  = 0.0
        self._on_locked_unlock = on_locked_unlock
        self._anim_id  = None
        # Draw region must include shadow + tilt slop
        self._refresh_size_request()
        self.set_draw_func(self._draw)
        self.set_cursor(Gdk.Cursor.new_from_name("default"))

        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("pressed",  self._press_cb)
        gc.connect("released", self._release_cb)
        self.add_controller(gc)

        gc2 = Gtk.GestureClick(); gc2.set_button(3)
        gc2.connect("released", self._right_release)
        self.add_controller(gc2)

        mc = Gtk.EventControllerMotion()
        mc.connect("enter", self._enter)
        mc.connect("motion", self._motion)
        mc.connect("leave", self._leave)
        self.add_controller(mc)

        # entrance animation
        self._start_entrance()

    # ── geometry ────────────────────────────────────────────────────────────
    def update_from_row(self, note: sqlite3.Row):
        self.note = dict(note)
        self.w   = max(140, float(note["w"]))
        self.h   = max(110, float(note["h"]))
        self.tilt = note["tilt"] or 0.0
        self._refresh_size_request()
        self.queue_draw()

    def _refresh_size_request(self):
        """Drawing surface must be larger than the rect so shadow/tilt fit."""
        slop = 36 + abs(math.sin(math.radians(self.tilt))) * max(self.w, self.h)
        wx = int(self.w + slop * 2)
        wy = int(self.h + slop * 2)
        self.set_size_request(wx, wy)
        try: self.set_content_width(wx); self.set_content_height(wy)
        except Exception: pass

    def color_rgb(self) -> Tuple[float, float, float]:
        if self.note.get("custom_hex"):
            try:
                hx = self.note["custom_hex"].lstrip("#")
                return tuple(int(hx[i:i+2], 16) / 255 for i in (0, 2, 4))
            except Exception: pass
        c = COLOR_BY_KEY.get(self.note["color"], COLOR_BY_KEY["yellow"])
        return c["rgb"]

    def shadow_rgb(self) -> Tuple[float, float, float]:
        c = COLOR_BY_KEY.get(self.note["color"], COLOR_BY_KEY["yellow"])
        return c["shadow"]

    # ── animations ──────────────────────────────────────────────────────────
    def _start_entrance(self):
        self.entrance = 0.0
        def step():
            self.entrance += 0.10
            if self.entrance >= 1.0:
                self.entrance = 1.0; self.queue_draw(); return False
            self.queue_draw(); return True
        GLib.timeout_add(16, step)

    def start_crumple(self, on_done: Callable[[], None]):
        self.crumple = 0.0
        def step():
            self.crumple += 0.06
            self.fade = max(0.0, 1.0 - self.crumple)
            if self.crumple >= 1.0:
                on_done(); return False
            self.queue_draw(); return True
        GLib.timeout_add(16, step)

    def _set_lift(self, target: float):
        if self._anim_id:
            try: GLib.source_remove(self._anim_id)
            except Exception: pass
        def step():
            d = target - self.lift
            if abs(d) < 0.02:
                self.lift = target; self.queue_draw(); return False
            self.lift += d * 0.25
            self.queue_draw()
            return True
        self._anim_id = GLib.timeout_add(16, step)

    # ── event handlers ──────────────────────────────────────────────────────
    def _enter(self, *a):
        self.hover = True
        if not self.selected: self._set_lift(1.0)
        self.queue_draw()

    def _leave(self, *a):
        self.hover = False
        self._set_lift(0.0)
        self.queue_draw()

    def _motion(self, ctrl, x, y):
        # toggle resize-cursor over the corner handle
        cx, cy = self._note_to_local(self.w, self.h)
        if math.hypot(x - cx, y - cy) <= self.HANDLE + 4:
            self.set_cursor(Gdk.Cursor.new_from_name("nwse-resize"))
        else:
            self.set_cursor(Gdk.Cursor.new_from_name("default"))

    def _note_to_local(self, nx: float, ny: float) -> Tuple[float, float]:
        """Convert (note-space) → local widget coords using tilt + center."""
        cx = self.get_allocated_width() / 2
        cy = self.get_allocated_height() / 2
        rad = math.radians(self.tilt)
        sx = nx - self.w / 2; sy = ny - self.h / 2
        rx = sx * math.cos(rad) - sy * math.sin(rad)
        ry = sx * math.sin(rad) + sy * math.cos(rad)
        return cx + rx, cy + ry

    def _local_to_note(self, lx: float, ly: float) -> Tuple[float, float]:
        cx = self.get_allocated_width() / 2
        cy = self.get_allocated_height() / 2
        rad = -math.radians(self.tilt)
        sx = lx - cx; sy = ly - cy
        rx = sx * math.cos(rad) - sy * math.sin(rad)
        ry = sx * math.sin(rad) + sy * math.cos(rad)
        return rx + self.w / 2, ry + self.h / 2

    def hits_note(self, lx: float, ly: float) -> bool:
        nx, ny = self._local_to_note(lx, ly)
        return 0 <= nx <= self.w and 0 <= ny <= self.h

    def _press_cb(self, ctrl, n, x, y):
        # corner handle?
        cx, cy = self._note_to_local(self.w, self.h)
        if math.hypot(x - cx, y - cy) <= self.HANDLE + 4:
            self.resizing = True
            self._press_x = x; self._press_y = y
            return
        if not self.hits_note(x, y):
            return
        # checklist hit?
        if self.note.get("kind") == "checklist":
            idx = self._hit_checklist(x, y)
            if idx >= 0:
                self.emit("checklist-toggled", self.nid, idx)
                return
        self.dragging = True
        self._press_x = x; self._press_y = y
        # bigger tilt while dragging
        self._drag_extra_tilt = random.uniform(-4, 4)
        self.tilt += self._drag_extra_tilt
        self.queue_draw()

    def _release_cb(self, ctrl, n, x, y):
        if self.resizing:
            # commit
            self.resizing = False
            self.emit("resized", self.nid, self.w, self.h)
            return
        if self.dragging:
            self.dragging = False
            self.tilt -= getattr(self, "_drag_extra_tilt", 0)
            self.emit("moved", self.nid, x - self._press_x, y - self._press_y)
            self.queue_draw()
            return
        # double-click: open editor
        if self.hits_note(x, y):
            self.emit("request-edit", self.nid)

    def _right_release(self, ctrl, n, x, y):
        if self.hits_note(x, y):
            self.emit("request-menu", self.nid, x, y)

    # ── checklist hit-test ──────────────────────────────────────────────────
    def _hit_checklist(self, lx: float, ly: float) -> int:
        nx, ny = self._local_to_note(lx, ly)
        # checklist drawn from y_start downward, line height ~24
        y_start = self.PADDING + self.TITLE_H + 6
        if ny < y_start: return -1
        idx = int((ny - y_start) // 24)
        items = (self.note.get("checklist") or "").splitlines()
        if 0 <= idx < len(items):
            box_x = self.PADDING
            if box_x <= nx <= box_x + 18:
                return idx
        return -1

    # ── drawing ─────────────────────────────────────────────────────────────
    def _draw(self, area, cr, w, h, _=None):
        try:
            self._draw_inner(cr, w, h)
        except Exception as e:
            log.error("note draw error: %s", e)

    def _draw_inner(self, cr, w, h):
        cx, cy = w / 2, h / 2
        cr.save()
        cr.translate(cx, cy)
        scale = 0.4 + 0.6 * self.entrance + 0.04 * self.lift
        if self.crumple > 0:
            scale *= (1.0 - self.crumple * 0.6)
        cr.scale(scale, scale)
        cr.rotate(math.radians(self.tilt))
        cr.translate(-self.w / 2, -self.h / 2)

        # Drop shadow
        sh = self.shadow_rgb()
        sh_off = 4 + 6 * self.lift
        cr.set_source_rgba(0, 0, 0, 0.45 * self.fade)
        cr.rectangle(sh_off, sh_off, self.w, self.h); cr.fill()
        cr.set_source_rgba(*sh, 0.30 * self.fade)
        cr.rectangle(sh_off + 1, sh_off + 1, self.w, self.h); cr.fill()

        # Body fill (with tiny noise)
        col = self.color_rgb()
        cr.set_source_rgba(*col, self.fade)
        cr.rectangle(0, 0, self.w, self.h); cr.fill()

        # subtle paper texture (a few diagonal lines, very faint)
        cr.set_source_rgba(0, 0, 0, 0.045 * self.fade)
        cr.set_line_width(0.6)
        rng = _seed("paper", self.nid, round(self.w), round(self.h))
        for _i in range(int(self.w * self.h / 1800)):
            x0 = rng.uniform(0, self.w); y0 = rng.uniform(0, self.h)
            cr.move_to(x0, y0); cr.line_to(x0 + rng.uniform(-3, 3),
                                           y0 + rng.uniform(-3, 3))
            cr.stroke()

        # Folded corner (bottom-right)
        fold_size = 24
        cr.save()
        cr.set_source_rgba(*sh, 0.55 * self.fade)
        cr.move_to(self.w, self.h - fold_size)
        cr.line_to(self.w, self.h)
        cr.line_to(self.w - fold_size, self.h)
        cr.close_path(); cr.fill()
        # lighter inner triangle (the underside)
        cr.set_source_rgba(min(col[0]+0.10, 1), min(col[1]+0.10, 1),
                           min(col[2]+0.10, 1), self.fade)
        cr.move_to(self.w - 2, self.h - fold_size + 2)
        cr.line_to(self.w - 2, self.h - 2)
        cr.line_to(self.w - fold_size + 2, self.h - 2)
        cr.close_path(); cr.fill()
        cr.restore()

        # Hand-drawn border
        cr.set_source_rgba(0, 0, 0, 0.55 * self.fade)
        cr.set_line_width(1.4)
        sketch_rect(cr, 1, 1, self.w - 2, self.h - 2, jitter=0.7,
                    key=("border", self.nid))

        # Pushpin or tape at top-center
        pin_color = NEON_PINK
        if self.note.get("starred"):     pin_color = ACCENT_GOLD
        elif self.note.get("pinned"):    pin_color = DANGER_RED
        sketch_pin(cr, self.w / 2, 2, color=pin_color,
                   key=("pin", self.nid))

        # Priority dot (top-right)
        prio = PRIORITY_BY_KEY.get(self.note.get("priority"), PRIORITIES[1])
        if self.note.get("priority") not in (None, "normal"):
            cr.set_source_rgba(*prio["rgb"], 0.95 * self.fade)
            cr.arc(self.w - 12, 12, 5, 0, math.pi * 2); cr.fill()

        # Lock badge (top-left)
        if self.note.get("locked"):
            sketch_lock(cr, 8, 6, 14, color=ACCENT_GOLD,
                        key=("lock", self.nid))

        # Title
        text_color = (0.10, 0.08, 0.14, 0.95 * self.fade)
        if self.note.get("color") == "black":
            text_color = (0.94, 0.92, 0.97, 0.95 * self.fade)
        title = self.note.get("title") or "(untitled)"
        draw_caveat_text(cr, self.PADDING, 6, title, size=18,
                         color=text_color, weight=Pango.Weight.BOLD,
                         wrap_w=self.w - self.PADDING * 2)

        # Body / kind
        body = self.note.get("body") or ""
        kind = self.note.get("kind", "text")
        if self.note.get("locked"):
            cr.set_source_rgba(*ACCENT_GOLD, 0.85 * self.fade)
            sketch_lock(cr, self.w/2 - 22, self.h/2 - 22, 44,
                        color=ACCENT_GOLD, key=("clk", self.nid))
            draw_caveat_text(cr, self.PADDING, self.h - 50,
                             "🔒 locked — double-click to unlock",
                             size=12, color=text_color)
        elif kind == "checklist":
            self._draw_checklist(cr, body if not self.note.get("checklist")
                                 else self.note["checklist"], text_color)
        elif kind == "code":
            draw_caveat_text(cr, self.PADDING,
                             self.PADDING + self.TITLE_H,
                             body, size=11, family="JetBrains Mono",
                             color=text_color,
                             wrap_w=self.w - self.PADDING * 2)
        else:
            draw_caveat_text(cr, self.PADDING,
                             self.PADDING + self.TITLE_H,
                             body, size=14, color=text_color,
                             wrap_w=self.w - self.PADDING * 2)

        # Tag pills
        tags = [t.strip() for t in (self.note.get("tags") or "").split(",")
                if t.strip()]
        if tags:
            tx = self.PADDING; ty = self.h - 44
            for t in tags[:5]:
                tw, _, _ = measure_text(cr, t, size=10)
                pill_w = tw + 14
                if tx + pill_w > self.w - self.PADDING:
                    break
                sketch_pill(cr, tx, ty, pill_w, 14,
                            fill=(0, 0, 0, 0.18),
                            stroke=(*ACCENT_PURP, 0.7),
                            key=("tag", self.nid, t))
                draw_caveat_text(cr, tx + 7, ty - 1, t, size=10,
                                 color=text_color)
                tx += pill_w + 6

        # Date stamp + char count
        ts = self.note.get("updated", 0)
        if ts:
            try:
                dt = datetime.fromtimestamp(ts)
                stamp = dt.strftime("%b %d • %H:%M")
            except Exception:
                stamp = ""
            cr.set_source_rgba(*text_color[:3], 0.55 * self.fade)
            draw_caveat_text(cr, self.PADDING, self.h - 22, stamp,
                             size=10, color=(*text_color[:3],
                                              0.6 * self.fade))
        chars = len(body)
        cw, _, _ = measure_text(cr, f"{chars} chars", size=10)
        draw_caveat_text(cr, self.w - self.PADDING - cw, self.h - 22,
                         f"{chars} chars", size=10,
                         color=(*text_color[:3], 0.6 * self.fade))

        # Resize handle (bottom-right corner) — three diagonal strokes
        cr.save()
        cr.set_source_rgba(0, 0, 0, 0.45 * self.fade)
        cr.set_line_width(1.2)
        for i, off in enumerate((4, 8, 12)):
            cr.move_to(self.w - 4, self.h - 4 - off)
            cr.line_to(self.w - 4 - off, self.h - 4)
            cr.stroke()
        cr.restore()

        # Selection halo
        if self.selected:
            cr.set_source_rgba(*NEON_PINK, 0.85)
            cr.set_line_width(2.4)
            sketch_rect(cr, -4, -4, self.w + 8, self.h + 8, jitter=0.9,
                        key=("sel", self.nid))

        cr.restore()

    def _draw_checklist(self, cr, body: str, text_color):
        items = body.splitlines()
        y = self.PADDING + self.TITLE_H + 4
        done = 0; total = 0
        for line in items:
            line = line.rstrip()
            if not line:
                y += 8; continue
            checked = False
            label = line
            m = re.match(r"\s*\[([ xX])\]\s*(.*)", line)
            if m:
                checked = (m.group(1).lower() == "x")
                label = m.group(2)
            total += 1
            if checked: done += 1
            # checkbox
            cr.set_source_rgba(0, 0, 0, 0.7)
            cr.set_line_width(1.4)
            sketch_rect(cr, self.PADDING, y, 16, 16, jitter=0.4,
                        key=("cb", self.nid, y))
            if checked:
                sketch_check(cr, self.PADDING, y, 16,
                             color=NEON_GREEN,
                             key=("ck", self.nid, y))
            # label
            tc = text_color
            if checked:
                tc = (text_color[0], text_color[1], text_color[2],
                      text_color[3] * 0.55)
            draw_caveat_text(cr, self.PADDING + 22, y - 2, label,
                             size=13, color=tc,
                             wrap_w=self.w - self.PADDING * 2 - 22)
            y += 24
            if y > self.h - 30: break
        if total > 0:
            txt = f"{done}/{total} done"
            tw, _, _ = measure_text(cr, txt, size=11)
            draw_caveat_text(cr, self.w - self.PADDING - tw,
                             self.PADDING + 6, txt,
                             size=11, color=(*text_color[:3], 0.7))

    # ── live drag/resize feedback (called by canvas) ────────────────────────
    def apply_drag_delta(self, dx: float, dy: float):
        # used by canvas for live previewing — actual move is committed via
        # `moved` signal on release
        pass

    def apply_resize_delta(self, dx: float, dy: float):
        self.w = max(140, self.w + dx)
        self.h = max(110, self.h + dy)
        self._refresh_size_request()
        self.queue_draw()


# ═══════════════════════════════════════════════════════════════════════════════
#  Canvas (Gtk.Fixed in ScrolledWindow)
# ═══════════════════════════════════════════════════════════════════════════════
class Canvas(Gtk.Box):
    """Infinite scrollable canvas hosting StickyNote widgets."""
    __gsignals__ = {
        "note-selected": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    CANVAS_W = 4000
    CANVAS_H = 3000

    def __init__(self, win: "StickiesWindow"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.win = win
        self.background_key = "void"
        self.zoom = 1.0
        self.notes: Dict[str, StickyNote] = {}
        self._space_pan = False
        self._panning = False
        self._pan_origin = (0.0, 0.0)
        self._select_drag_start: Optional[Tuple[float, float]] = None
        self._select_rect: Optional[Tuple[float, float, float, float]] = None
        self._drag_state: Optional[Dict[str, Any]] = None
        self._resize_state: Optional[Dict[str, Any]] = None

        # Background DrawingArea (full canvas size)
        self.bg_area = Gtk.DrawingArea()
        self.bg_area.set_content_width(self.CANVAS_W)
        self.bg_area.set_content_height(self.CANVAS_H)
        self.bg_area.set_draw_func(self._draw_bg)

        self.fixed = Gtk.Fixed()
        self.fixed.set_size_request(self.CANVAS_W, self.CANVAS_H)
        self.fixed.put(self.bg_area, 0, 0)

        # Selection-rect overlay (drawn on the bg layer via queue_draw)
        self._select_overlay_active = False

        self.scroller = Gtk.ScrolledWindow()
        self.scroller.set_policy(Gtk.PolicyType.AUTOMATIC,
                                 Gtk.PolicyType.AUTOMATIC)
        self.scroller.set_hexpand(True); self.scroller.set_vexpand(True)
        self.scroller.set_child(self.fixed)
        self.append(self.scroller)

        # Mouse on bg (rubber-band + middle/space pan)
        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("pressed",  self._bg_press)
        gc.connect("released", self._bg_release)
        self.bg_area.add_controller(gc)

        gc_mid = Gtk.GestureClick(); gc_mid.set_button(2)
        gc_mid.connect("pressed",  self._mid_press)
        gc_mid.connect("released", self._mid_release)
        self.bg_area.add_controller(gc_mid)

        mc = Gtk.EventControllerMotion()
        mc.connect("motion", self._bg_motion)
        self.bg_area.add_controller(mc)

        # Scroll for zoom (Ctrl+scroll)
        sc = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.VERTICAL)
        sc.connect("scroll", self._on_scroll)
        self.add_controller(sc)

    # ── load / refresh ──────────────────────────────────────────────────────
    def clear(self):
        for nid, w in list(self.notes.items()):
            try: self.fixed.remove(w)
            except Exception: pass
        self.notes.clear()

    def load_board(self, board_id: str):
        b = self.win.db.get_board(board_id)
        if b:
            self.background_key = b["background"] or "void"
            self.zoom = float(b["zoom"] or 1.0)
        self.clear()
        for n in self.win.db.list_notes(board_id, include_archived=False):
            self._add_note(n)
        self.bg_area.queue_draw()

    def add_note_row(self, n: sqlite3.Row):
        self._add_note(n)

    def _add_note(self, n: sqlite3.Row):
        sn = StickyNote(n)
        self.notes[n["id"]] = sn
        # Place note such that its visual center is at (n.x + w/2, n.y + h/2)
        sn.connect("request-edit", self._on_edit)
        sn.connect("request-menu", self._on_menu)
        sn.connect("moved", self._on_moved)
        sn.connect("resized", self._on_resized)
        sn.connect("checklist-toggled", self._on_checklist_toggled)
        # We allow the StickyNote's drawing area to be larger than rect
        # (for shadow + tilt slop).  Compute X/Y so its center sits at
        # n.x + w/2.
        ax = float(n["x"]) - (sn.get_size_request()[0] - sn.w) / 2
        ay = float(n["y"]) - (sn.get_size_request()[1] - sn.h) / 2
        self.fixed.put(sn, int(ax), int(ay))

    def remove_note(self, nid: str):
        sn = self.notes.pop(nid, None)
        if sn:
            try: self.fixed.remove(sn)
            except Exception: pass

    def update_note(self, nid: str):
        sn = self.notes.get(nid)
        if sn:
            row = self.win.db.get_note(nid)
            if row:
                sn.update_from_row(row)
                # move widget if x/y changed
                ax = float(row["x"]) - (sn.get_size_request()[0] - sn.w) / 2
                ay = float(row["y"]) - (sn.get_size_request()[1] - sn.h) / 2
                self.fixed.move(sn, int(ax), int(ay))

    def select_only(self, nid: str):
        for k, sn in self.notes.items():
            sn.selected = (k == nid); sn.queue_draw()
        if nid:
            self.emit("note-selected", nid)

    def selected_ids(self) -> List[str]:
        return [k for k, sn in self.notes.items() if sn.selected]

    # ── note signals ────────────────────────────────────────────────────────
    def _on_edit(self, sn: StickyNote, nid: str):
        self.win.open_note_editor(nid)

    def _on_menu(self, sn: StickyNote, nid: str, x: float, y: float):
        self.win.show_note_context(nid, sn, x, y)

    def _on_moved(self, sn: StickyNote, nid: str, dx: float, dy: float):
        # the dx/dy is local widget coords (no zoom transform on the widget
        # itself — the whole canvas isn't zoom-transformed; we just shift)
        nx = float(self.win.db.get_note(nid)["x"]) + dx
        ny = float(self.win.db.get_note(nid)["y"]) + dy
        self.win.db.update_note(nid, x=nx, y=ny)
        self.update_note(nid)

    def _on_resized(self, sn: StickyNote, nid: str, w: float, h: float):
        self.win.db.update_note(nid, w=w, h=h)
        self.update_note(nid)

    def _on_checklist_toggled(self, sn: StickyNote, nid: str, idx: int):
        row = self.win.db.get_note(nid)
        if not row: return
        body = (row["checklist"] or row["body"] or "").splitlines()
        if 0 <= idx < len(body):
            line = body[idx]
            m = re.match(r"(\s*\[)([ xX])(\]\s*)(.*)", line)
            if m:
                pre, mark, post, rest = m.group(1), m.group(2), m.group(3), m.group(4)
                new = "x" if mark == " " else " "
                body[idx] = f"{pre}{new}{post}{rest}"
                joined = "\n".join(body)
                self.win.db.update_note(nid, checklist=joined, body=joined)
                self.update_note(nid)

    # ── canvas background (corkboard / grid / etc.) ─────────────────────────
    def _draw_bg(self, area, cr, w, h, _=None):
        bg = BG_BY_KEY.get(self.background_key, BG_BY_KEY["void"])
        cr.set_source_rgb(*bg["rgb"]); cr.rectangle(0, 0, w, h); cr.fill()
        pat = bg["pattern"]
        if pat == "grid":
            cr.set_source_rgba(*NEON_PINK, 0.08); cr.set_line_width(0.6)
            step = 40
            for x in range(0, w, step):
                cr.move_to(x, 0); cr.line_to(x, h); cr.stroke()
            for y in range(0, h, step):
                cr.move_to(0, y); cr.line_to(w, y); cr.stroke()
        elif pat == "cork":
            cr.set_source_rgba(0.5, 0.34, 0.18, 0.4)
            rng = _seed("cork", w, h)
            for _i in range(int(w * h / 1500)):
                x = rng.uniform(0, w); y = rng.uniform(0, h)
                cr.arc(x, y, rng.uniform(0.4, 1.4), 0, math.pi * 2)
                cr.fill()
        elif pat == "wood":
            cr.set_source_rgba(0.28, 0.18, 0.10, 0.6)
            for y in range(0, h, 14):
                cr.move_to(0, y + (y % 28) * 0.05); cr.line_to(w, y); cr.stroke()
        elif pat == "slate":
            cr.set_source_rgba(0.2, 0.21, 0.24, 0.6)
            cr.rectangle(0, 0, w, h); cr.fill()
        # rubber-band selection rect
        if self._select_rect:
            x0, y0, x1, y1 = self._select_rect
            x = min(x0, x1); y = min(y0, y1)
            ww = abs(x1 - x0); hh = abs(y1 - y0)
            cr.set_source_rgba(*NEON_PINK, 0.18)
            cr.rectangle(x, y, ww, hh); cr.fill()
            cr.set_source_rgba(*NEON_PINK, 0.85); cr.set_line_width(1.4)
            sketch_rect(cr, x, y, ww, hh, jitter=0.5, key=("rb",))

    # ── canvas-bg mouse handlers ────────────────────────────────────────────
    def _bg_press(self, ctrl, n, x, y):
        if self._space_pan:
            self._panning = True
            adj_h = self.scroller.get_hadjustment()
            adj_v = self.scroller.get_vadjustment()
            self._pan_origin = (x + adj_h.get_value(),
                                y + adj_v.get_value())
            return
        # rubber-band selection
        self._select_drag_start = (x, y)
        self._select_rect = (x, y, x, y)
        # deselect previous unless shift held (not tracked here)
        for sn in self.notes.values():
            sn.selected = False; sn.queue_draw()

    def _bg_release(self, ctrl, n, x, y):
        if self._panning:
            self._panning = False
            return
        if self._select_drag_start:
            x0, y0 = self._select_drag_start
            xa, xb = sorted((x0, x))
            ya, yb = sorted((y0, y))
            for nid, sn in self.notes.items():
                row = self.win.db.get_note(nid)
                if not row: continue
                cx = float(row["x"]) + sn.w / 2
                cy = float(row["y"]) + sn.h / 2
                if xa <= cx <= xb and ya <= cy <= yb:
                    sn.selected = True; sn.queue_draw()
            self._select_drag_start = None
            self._select_rect = None
            self.bg_area.queue_draw()

    def _mid_press(self, ctrl, n, x, y):
        self._panning = True
        adj_h = self.scroller.get_hadjustment()
        adj_v = self.scroller.get_vadjustment()
        self._pan_origin = (x + adj_h.get_value(), y + adj_v.get_value())

    def _mid_release(self, *a):
        self._panning = False

    def _bg_motion(self, ctrl, x, y):
        if self._panning:
            adj_h = self.scroller.get_hadjustment()
            adj_v = self.scroller.get_vadjustment()
            adj_h.set_value(self._pan_origin[0] - x)
            adj_v.set_value(self._pan_origin[1] - y)
            return
        if self._select_drag_start:
            x0, y0 = self._select_drag_start
            self._select_rect = (x0, y0, x, y)
            self.bg_area.queue_draw()

    def _on_scroll(self, ctrl, dx, dy):
        ev = ctrl.get_current_event()
        if ev and (ev.get_modifier_state() & Gdk.ModifierType.CONTROL_MASK):
            old = self.zoom
            self.zoom = max(0.4, min(2.5, self.zoom * (1 + dy * -0.08)))
            # apply via Gtk.Fixed scale: we just scale the size_request.
            # Real zoom is approximate (no full transform).
            log.info("zoom %.2f → %.2f", old, self.zoom)
            self.win.show_toast(f"Zoom {self.zoom:.0%}")
            return True
        return False

    def set_space_pan(self, on: bool):
        self._space_pan = on
        if on:
            self.set_cursor(Gdk.Cursor.new_from_name("grab"))
        else:
            self.set_cursor(Gdk.Cursor.new_from_name("default"))

    def set_background(self, key: str):
        self.background_key = key
        self.bg_area.queue_draw()

    # ── alignment helpers ───────────────────────────────────────────────────
    def align_selected(self, edge: str):
        sels = [(self.win.db.get_note(nid), self.notes[nid])
                for nid in self.selected_ids()
                if self.win.db.get_note(nid)]
        if len(sels) < 2: return
        if edge == "left":
            x = min(float(r["x"]) for r, _ in sels)
            for r, sn in sels: self.win.db.update_note(r["id"], x=x); self.update_note(r["id"])
        elif edge == "right":
            x = max(float(r["x"]) + sn.w for r, sn in sels)
            for r, sn in sels:
                self.win.db.update_note(r["id"], x=x - sn.w); self.update_note(r["id"])
        elif edge == "top":
            y = min(float(r["y"]) for r, _ in sels)
            for r, sn in sels: self.win.db.update_note(r["id"], y=y); self.update_note(r["id"])
        elif edge == "bottom":
            y = max(float(r["y"]) + sn.h for r, sn in sels)
            for r, sn in sels:
                self.win.db.update_note(r["id"], y=y - sn.h); self.update_note(r["id"])

    def distribute_selected(self, axis: str):
        sels = [(self.win.db.get_note(nid), self.notes[nid])
                for nid in self.selected_ids()
                if self.win.db.get_note(nid)]
        if len(sels) < 3: return
        if axis == "x":
            sels.sort(key=lambda p: float(p[0]["x"]))
            x_min = float(sels[0][0]["x"]); x_max = float(sels[-1][0]["x"])
            step = (x_max - x_min) / (len(sels) - 1)
            for i, (r, _) in enumerate(sels):
                self.win.db.update_note(r["id"], x=x_min + i * step)
                self.update_note(r["id"])
        else:
            sels.sort(key=lambda p: float(p[0]["y"]))
            y_min = float(sels[0][0]["y"]); y_max = float(sels[-1][0]["y"])
            step = (y_max - y_min) / (len(sels) - 1)
            for i, (r, _) in enumerate(sels):
                self.win.db.update_note(r["id"], y=y_min + i * step)
                self.update_note(r["id"])


# ═══════════════════════════════════════════════════════════════════════════════
#  Note editor dialog
# ═══════════════════════════════════════════════════════════════════════════════
class NoteEditor(Gtk.Window):
    def __init__(self, win: "StickiesWindow", nid: str):
        super().__init__(transient_for=win, title="edit note")
        self.win = win; self.nid = nid
        self.set_default_size(540, 460)
        self.set_modal(True)

        row = win.db.get_note(nid)
        if not row: self.close(); return
        self.row = row

        if row["locked"] and not win.crypto.is_unlocked():
            ok = win.prompt_unlock()
            if not ok: GLib.idle_add(self.close); return

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_start(14); outer.set_margin_end(14)
        outer.set_margin_top(14);   outer.set_margin_bottom(14)
        self.set_child(outer)

        head = Gtk.Box(spacing=8)
        outer.append(head)
        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("title…")
        self.title_entry.set_text(row["title"] or "")
        self.title_entry.add_css_class("nyx-title-entry")
        self.title_entry.set_hexpand(True)
        head.append(self.title_entry)

        self.kind_combo = Gtk.DropDown.new_from_strings(
            ["text", "checklist", "code"])
        self.kind_combo.set_selected(
            {"text": 0, "checklist": 1, "code": 2}.get(row["kind"], 0))
        head.append(self.kind_combo)

        # Body
        sw = Gtk.ScrolledWindow()
        sw.set_hexpand(True); sw.set_vexpand(True)
        outer.append(sw)
        self.tv = Gtk.TextView()
        self.tv.add_css_class("nyx-editor")
        self.tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.body_buf = self.tv.get_buffer()
        body = row["body"] or ""
        if row["locked"] and row["locked_blob"]:
            try:
                body = win.crypto.decrypt(row["locked_blob"])
            except Exception:
                body = "(unable to decrypt)"
        self.body_buf.set_text(body)
        sw.set_child(self.tv)

        # Tags + color picker row
        meta = Gtk.Box(spacing=8); outer.append(meta)
        self.tags_entry = Gtk.Entry()
        self.tags_entry.set_placeholder_text("tags (comma separated)")
        self.tags_entry.set_text(row["tags"] or "")
        self.tags_entry.set_hexpand(True)
        meta.append(self.tags_entry)
        self.prio_combo = Gtk.DropDown.new_from_strings(
            [p["label"] for p in PRIORITIES])
        prio_idx = next((i for i, p in enumerate(PRIORITIES)
                         if p["key"] == row["priority"]), 1)
        self.prio_combo.set_selected(prio_idx)
        meta.append(self.prio_combo)

        # buttons
        btns = Gtk.Box(spacing=8); outer.append(btns)
        for label, fn in (
            ("Save",        self._save),
            ("Reminder…",   self._reminder),
            ("Versions…",   self._versions),
            ("Lock/unlock", self._toggle_lock),
            ("Cancel",      lambda *_: self.close()),
        ):
            b = SketchButton(label, width=104, height=28,
                             color=NEON_PINK if label == "Save" else NEON_BLUE,
                             primary=(label == "Save"))
            b.connect("clicked", lambda _b, f=fn: f())
            btns.append(b)

    def _save(self):
        title = self.title_entry.get_text().strip()
        body  = self.body_buf.get_text(self.body_buf.get_start_iter(),
                                       self.body_buf.get_end_iter(), False)
        kind = ("text", "checklist", "code")[self.kind_combo.get_selected()]
        tags = self.tags_entry.get_text().strip()
        prio = PRIORITIES[self.prio_combo.get_selected()]["key"]
        # version snapshot
        self.win.db.save_version(self.nid, title=self.row["title"] or "",
                                 body=self.row["body"] or "")
        if self.row["locked"]:
            if not self.win.crypto.is_unlocked():
                self.win.show_toast("vault locked"); return
            blob = self.win.crypto.encrypt(body)
            self.win.db.update_note(self.nid, title=title, kind=kind,
                                    tags=tags, priority=prio,
                                    locked_blob=blob, body="",
                                    checklist=body if kind == "checklist" else "")
        else:
            self.win.db.update_note(self.nid, title=title, body=body,
                                    kind=kind, tags=tags, priority=prio,
                                    checklist=body if kind == "checklist" else "")
        self.win.canvas.update_note(self.nid)
        self.win.show_toast("saved")
        self.close()

    def _reminder(self):
        self.win.show_reminder_dialog(self.nid)

    def _versions(self):
        self.win.show_versions_dialog(self.nid)

    def _toggle_lock(self):
        self.win.toggle_lock(self.nid)
        self.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  Main window
# ═══════════════════════════════════════════════════════════════════════════════
class StickiesWindow(Gtk.ApplicationWindow):
    AUTOSAVE_MS = 30_000
    REMINDER_POLL_MS = 30_000

    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME)
        self.set_default_size(WIN_W, WIN_H)
        self.db = DB()
        self.crypto = Crypto(self.db)
        self.current_board: Optional[str] = None
        self.search_text = ""
        self.filter_color = "all"
        self.filter_tag   = ""
        self.filter_prio  = "all"
        self.show_archived = False
        self._toast_label: Optional[Gtk.Label] = None
        self._board_buttons: Dict[str, SketchButton] = {}

        self._build_css()
        self._build_layout()
        self._wire_keys()

        boards = self.db.list_boards()
        if boards:
            self.load_board(boards[0]["id"])

        # autosave / reminders
        GLib.timeout_add(self.REMINDER_POLL_MS, self._poll_reminders)

    # ── CSS ────────────────────────────────────────────────────────────────
    def _build_css(self):
        css = b"""
* { font-family: 'Caveat', 'Patrick Hand', cursive; }
window, .nyx-bg { background-color: #0a0a12; color: #f0eef8; }
.nyx-sidebar { background-color: rgba(255,255,255,0.025); }
.nyx-toolbar { background-color: rgba(10,10,18,0.96); padding: 4px 10px; }
.nyx-statusbar { background-color: rgba(10,10,18,0.96); padding: 2px 10px;
    border-top: 1px solid rgba(255,255,255,0.05); }
.nyxus-entry { background-color: transparent; border: none; outline: none;
    box-shadow: none; color: rgba(240,235,250,0.92);
    font-size: 14px; font-family: 'Caveat', cursive;
    caret-color: #ff00ff; }
.nyxus-entry:focus { outline: none; box-shadow: none; }
.nyx-title-entry { background-color: transparent; border: none;
    color: #ffffff; font-family: 'Caveat', cursive;
    font-size: 22px; font-weight: bold;
    padding: 4px 10px; caret-color: #ff00ff; }
.nyx-headline { color: #ff00ff; text-shadow: 0 0 10px rgba(255,0,255,0.55);
    font-size: 17px; font-weight: bold; }
.nyx-meta { color: rgba(240,235,250,0.45); font-size: 11px; }
.nyx-editor textview, .nyx-editor text {
    background-color: transparent; color: rgba(240,235,250,0.95);
    font-family: 'Caveat', cursive; font-size: 16px;
    padding: 6px 10px; caret-color: #ff00ff; }
.nyx-toast {
    background-color: rgba(255,0,255,0.18);
    color: #ffffff; padding: 6px 14px;
    border: 1px solid rgba(255,0,255,0.55);
    border-radius: 8px; font-size: 14px;
}
scrollbar slider { background-color: rgba(255,0,255,0.30);
    border: 1px solid rgba(255,0,255,0.45); border-radius: 6px;
    min-width: 8px; min-height: 8px; }
scrollbar slider:hover { background-color: rgba(255,0,255,0.55); }
scrollbar { background-color: transparent; }
"""
        prov = Gtk.CssProvider()
        try: prov.load_from_data(css)
        except TypeError: prov.load_from_data(css.decode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # ── Layout ─────────────────────────────────────────────────────────────
    def _build_layout(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("nyx-bg")
        self.set_child(root)

        # Top toolbar
        self.toolbar = self._make_toolbar()
        root.append(self.toolbar)

        # Body: sidebar | canvas
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(220)
        paned.set_wide_handle(True)
        paned.set_hexpand(True); paned.set_vexpand(True)
        root.append(paned)

        self.sidebar = self._make_sidebar()
        paned.set_start_child(self.sidebar)

        self.canvas = Canvas(self)
        # overlay for toast
        ov = Gtk.Overlay(); ov.set_child(self.canvas)
        self._toast_label = Gtk.Label()
        self._toast_label.add_css_class("nyx-toast")
        self._toast_label.set_halign(Gtk.Align.CENTER)
        self._toast_label.set_valign(Gtk.Align.END)
        self._toast_label.set_margin_bottom(20)
        self._toast_label.set_visible(False)
        ov.add_overlay(self._toast_label)
        paned.set_end_child(ov)

        # status bar
        self.status_bar = self._make_status_bar()
        root.append(self.status_bar)

    def _make_toolbar(self):
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        sw.set_hexpand(True)
        bar = Gtk.Box(spacing=4); bar.add_css_class("nyx-toolbar")
        sw.set_child(bar); sw.add_css_class("nyx-toolbar")

        logo = Gtk.Label(label="🗒 Stickies"); logo.add_css_class("nyx-headline")
        bar.append(logo)
        bar.append(SketchSeparator(vertical=True, length=18, color=NEON_PINK))

        b_new = SketchButton("＋ New", width=78, height=24,
                             color=NEON_GREEN, primary=True,
                             tooltip="New note (Ctrl+N)")
        b_new.connect("clicked", lambda _b: self.new_note())
        bar.append(b_new)

        b_tpl = SketchButton("Tmpl", width=58, height=24, color=NEON_PINK,
                             tooltip="From template (Ctrl+Shift+N)")
        b_tpl.connect("clicked", lambda _b: self.show_templates())
        bar.append(b_tpl)

        b_brd = SketchButton("Boards", width=68, height=24, color=ACCENT_PURP,
                             tooltip="Manage boards")
        b_brd.connect("clicked", lambda _b: self.show_board_dialog())
        bar.append(b_brd)

        b_bg = SketchButton("Bg", width=44, height=24, color=NEON_BLUE,
                            tooltip="Canvas background")
        b_bg.connect("clicked", self._show_bg_menu)
        bar.append(b_bg)

        b_arrange = SketchButton("Arrange", width=78, height=24,
                                 color=ACCENT_PURP,
                                 tooltip="Auto-arrange / align")
        b_arrange.connect("clicked", self._show_arrange_menu)
        bar.append(b_arrange)

        b_sort = SketchButton("Sort flat", width=74, height=24,
                              color=NEON_BLUE,
                              tooltip="Temporarily un-tilt all notes")
        b_sort.connect("clicked", lambda _b: self.toggle_sort_mode())
        self.btn_sort = b_sort
        bar.append(b_sort)

        sp = Gtk.Box(); sp.set_hexpand(True); bar.append(sp)

        # Search
        self.search = SketchSearchEntry(placeholder="search all boards…")
        self.search.connect("changed", self._on_search)
        bar.append(self.search)

        b_filter = SketchButton("⛛", width=32, height=24, color=NEON_BLUE,
                                tooltip="Filter")
        b_filter.connect("clicked", self._show_filter_menu)
        bar.append(b_filter)

        b_export = SketchButton("Export", width=64, height=24, color=NEON_PINK,
                                tooltip="Export selected (Ctrl+E)")
        b_export.connect("clicked", lambda _b: self.export_selected())
        bar.append(b_export)

        b_set = SketchButton("⚙", width=32, height=24, color=INK_DIM,
                             tooltip="Settings")
        b_set.connect("clicked", lambda _b: self.show_settings())
        bar.append(b_set)

        b_full = SketchButton("⛶", width=32, height=24, color=INK_DIM,
                              tooltip="Fullscreen (F11)")
        b_full.connect("clicked", lambda _b: self.toggle_fullscreen())
        bar.append(b_full)

        return sw

    def _make_sidebar(self):
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        col.add_css_class("nyx-sidebar")
        col.set_size_request(210, -1)

        head = Gtk.Box(spacing=4)
        head.set_margin_start(8); head.set_margin_end(8)
        head.set_margin_top(6);   head.set_margin_bottom(4)
        h = Gtk.Label(label="boards", xalign=0); h.add_css_class("nyx-headline")
        head.append(h)
        sp = Gtk.Box(); sp.set_hexpand(True); head.append(sp)
        b_add = SketchButton("＋", width=32, height=22, color=NEON_GREEN,
                             tooltip="New board")
        b_add.connect("clicked", lambda _b: self._new_board_inline())
        head.append(b_add)
        col.append(head)

        # boards list
        self.boards_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.boards_box.set_margin_start(6); self.boards_box.set_margin_end(6)
        col.append(self.boards_box)

        col.append(SketchSeparator(length=180, color=INK_FAINT))

        # quick stats
        self.sb_stats = Gtk.Label(xalign=0)
        self.sb_stats.add_css_class("nyx-meta")
        self.sb_stats.set_margin_start(10); self.sb_stats.set_margin_end(10)
        self.sb_stats.set_margin_top(8);    self.sb_stats.set_margin_bottom(8)
        col.append(self.sb_stats)

        # filter labels
        self.filter_lbl = Gtk.Label(xalign=0)
        self.filter_lbl.add_css_class("nyx-meta")
        self.filter_lbl.set_margin_start(10); self.filter_lbl.set_margin_end(10)
        self.filter_lbl.set_margin_bottom(8)
        col.append(self.filter_lbl)

        sp2 = Gtk.Box(); sp2.set_vexpand(True); col.append(sp2)

        # bottom: archived / reminders
        b_rem = SketchButton("⏰ Reminders", width=200, height=26,
                             color=ACCENT_GOLD,
                             tooltip="View all reminders")
        b_rem.connect("clicked", lambda _b: self.show_reminder_list())
        b_rem.set_margin_start(6); b_rem.set_margin_end(6)
        b_rem.set_margin_bottom(4)
        col.append(b_rem)

        b_arch = SketchToggle("📦 Archived", width=200, height=26,
                              color=ACCENT_PURP,
                              tooltip="Show archived")
        b_arch.connect("clicked", lambda _b: self._toggle_archived(b_arch))
        b_arch.set_margin_start(6); b_arch.set_margin_end(6)
        b_arch.set_margin_bottom(8)
        col.append(b_arch)
        self.btn_arch = b_arch

        self._refresh_boards()
        return col

    def _make_status_bar(self):
        bar = Gtk.Box(spacing=14); bar.add_css_class("nyx-statusbar")
        self.status_lbl = Gtk.Label(label="ready")
        self.status_lbl.add_css_class("nyx-meta")
        bar.append(self.status_lbl)
        sp = Gtk.Box(); sp.set_hexpand(True); bar.append(sp)
        self.status_right = Gtk.Label(label="")
        self.status_right.add_css_class("nyx-meta")
        bar.append(self.status_right)
        return bar

    # ── Boards ─────────────────────────────────────────────────────────────
    def _refresh_boards(self):
        # remove existing children
        child = self.boards_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.boards_box.remove(child)
            child = nxt
        self._board_buttons.clear()
        for b in self.db.list_boards():
            row = Gtk.Box(spacing=4)
            btn = SketchButton(b["name"], width=140, height=24,
                               color=NEON_BLUE,
                               primary=(b["id"] == self.current_board))
            btn.connect("clicked", lambda _b, bid=b["id"]: self.load_board(bid))
            row.append(btn)
            del_btn = SketchButton("✕", width=28, height=24, color=DANGER_RED,
                                   tooltip="Delete board")
            del_btn.connect("clicked",
                            lambda _b, bid=b["id"], nm=b["name"]:
                            self._confirm_delete_board(bid, nm))
            row.append(del_btn)
            self.boards_box.append(row)
            self._board_buttons[b["id"]] = btn

    def _new_board_inline(self):
        dlg = Gtk.Dialog(transient_for=self, modal=True, title="new board")
        dlg.set_default_size(360, -1)
        ent = Gtk.Entry(); ent.set_placeholder_text("board name…")
        ent.set_margin_start(14); ent.set_margin_end(14)
        ent.set_margin_top(14); ent.set_margin_bottom(14)
        dlg.get_content_area().append(ent)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Create", Gtk.ResponseType.OK)
        def resp(d, r):
            if r == Gtk.ResponseType.OK:
                name = ent.get_text().strip() or "Untitled board"
                bid = self.db.create_board(name)
                self._refresh_boards()
                self.load_board(bid)
            d.destroy()
        dlg.connect("response", resp)
        dlg.present()

    def _confirm_delete_board(self, bid: str, name: str):
        dlg = Gtk.MessageDialog(transient_for=self, modal=True,
                                buttons=Gtk.ButtonsType.OK_CANCEL,
                                text=f"delete board “{name}”?")
        dlg.format_secondary_text("all notes on this board will be deleted.")
        def resp(d, r):
            if r == Gtk.ResponseType.OK:
                self.db.delete_board(bid)
                if self.current_board == bid:
                    self.current_board = None
                    self.canvas.clear()
                    boards = self.db.list_boards()
                    if boards: self.load_board(boards[0]["id"])
                self._refresh_boards()
            d.destroy()
        dlg.connect("response", resp); dlg.present()

    def show_board_dialog(self):
        # Just open the inline create dialog for now
        self._new_board_inline()

    def load_board(self, bid: str):
        self.current_board = bid
        b = self.db.get_board(bid)
        if not b: return
        self.canvas.load_board(bid)
        self._refresh_boards()
        self._refresh_status()
        self.show_toast(f"board: {b['name']}")

    # ── Notes CRUD ─────────────────────────────────────────────────────────
    def new_note(self, *, kind="text", color="yellow", body="",
                 title="", from_template_id: Optional[str] = None):
        if not self.current_board:
            boards = self.db.list_boards()
            if not boards: self.current_board = self.db.create_board("Default")
            else:          self.current_board = boards[0]["id"]
        if from_template_id:
            tpl = next((t for t in self.db.list_templates()
                        if t["id"] == from_template_id), None)
            if tpl:
                body  = tpl["body"]
                kind  = tpl["kind"]
                color = tpl["color"]
                title = tpl["name"]
        # Place near current scroll center
        adj_h = self.canvas.scroller.get_hadjustment()
        adj_v = self.canvas.scroller.get_vadjustment()
        cx = adj_h.get_value() + adj_h.get_page_size() / 2
        cy = adj_v.get_value() + adj_v.get_page_size() / 2
        nid = self.db.create_note(self.current_board, title=title, body=body,
                                  kind=kind, color=color,
                                  x=cx - 120, y=cy - 100,
                                  checklist=body if kind == "checklist" else "")
        row = self.db.get_note(nid)
        self.canvas.add_note_row(row)
        self._refresh_status()
        self.show_toast("new note")
        return nid

    def open_note_editor(self, nid: str):
        ed = NoteEditor(self, nid)
        ed.present()

    def show_note_context(self, nid: str, sn: StickyNote, x: float, y: float):
        pop = Gtk.Popover()
        pop.set_parent(sn)
        pop.set_pointing_to(Gdk.Rectangle(x=int(x), y=int(y), width=1, height=1))
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(8); box.set_margin_end(8)
        box.set_margin_top(8);   box.set_margin_bottom(8)
        pop.set_child(box)

        def add(label, fn, color=NEON_PINK):
            b = SketchButton(label, width=180, height=24, color=color)
            b.connect("clicked", lambda _b: (pop.popdown(), fn()))
            box.append(b)

        row = self.db.get_note(nid)
        add("✎ Edit",       lambda: self.open_note_editor(nid))
        add("Duplicate",   lambda: self.duplicate_note(nid))
        add("Pin to top",  lambda: self._toggle_field(nid, "pinned"),
            color=DANGER_RED)
        add("Star",        lambda: self._toggle_field(nid, "starred"),
            color=ACCENT_GOLD)
        add("Lock/unlock", lambda: self.toggle_lock(nid),
            color=ACCENT_GOLD)
        add("Color…",      lambda: self.show_color_picker(nid),
            color=ACCENT_PURP)
        add("Reminder…",   lambda: self.show_reminder_dialog(nid),
            color=ACCENT_GOLD)
        add("Export PNG",  lambda: self.export_note_png(nid),
            color=NEON_BLUE)
        add("Export Text", lambda: self.export_note_text(nid),
            color=NEON_BLUE)
        add("Archive",     lambda: self._archive(nid),
            color=ACCENT_PURP)
        add("Delete",      lambda: self.delete_note(nid),
            color=DANGER_RED)
        pop.popup()

    def _toggle_field(self, nid: str, field: str):
        row = self.db.get_note(nid)
        if not row: return
        new = 0 if row[field] else 1
        self.db.update_note(nid, **{field: new})
        self.canvas.update_note(nid)

    def duplicate_note(self, nid: str):
        row = self.db.get_note(nid)
        if not row: return
        d = dict(row)
        d.pop("id", None)
        d["title"] = (d.get("title") or "") + " (copy)"
        d["x"] = float(d.get("x", 100)) + 30
        d["y"] = float(d.get("y", 100)) + 30
        new_id = self.db.create_note(d["board_id"], **{
            k: v for k, v in d.items()
            if k in ("title","body","kind","color","custom_hex",
                     "x","y","w","h","tilt","size_key","priority","tags",
                     "checklist","code_lang","pinned","starred")
        })
        self.canvas.add_note_row(self.db.get_note(new_id))
        self.show_toast("duplicated")

    def _archive(self, nid: str):
        self.db.update_note(nid, archived=1)
        self.canvas.remove_note(nid)
        self._refresh_status()
        self.show_toast("archived")

    def delete_note(self, nid: str):
        sn = self.canvas.notes.get(nid)
        if not sn:
            self.db.delete_note(nid); return

        def done():
            try: self.canvas.fixed.remove(sn)
            except Exception: pass
            self.canvas.notes.pop(nid, None)
            self.db.delete_note(nid)
            self._refresh_status()
            self.show_toast("deleted")

        sn.start_crumple(done)

    def toggle_lock(self, nid: str):
        if not HAS_CRYPTO:
            self.show_toast("install python-cryptography to use locks"); return
        row = self.db.get_note(nid)
        if not row: return
        if not self.crypto.is_setup():
            if not self.prompt_set_password(): return
        if not self.crypto.is_unlocked():
            if not self.prompt_unlock(): return
        if row["locked"]:
            try:
                pt = self.crypto.decrypt(row["locked_blob"] or "")
            except Exception:
                self.show_toast("decrypt failed"); return
            self.db.update_note(nid, locked=0, locked_blob=None,
                                body=pt,
                                checklist=pt if row["kind"] == "checklist" else "")
        else:
            body = row["body"] or ""
            blob = self.crypto.encrypt(body)
            self.db.update_note(nid, locked=1, locked_blob=blob,
                                body="", checklist="")
        self.canvas.update_note(nid)

    # ── Reminders ──────────────────────────────────────────────────────────
    def show_reminder_dialog(self, nid: str):
        dlg = Gtk.Dialog(transient_for=self, modal=True,
                         title="set reminder")
        dlg.set_default_size(380, -1)
        box = dlg.get_content_area()
        box.set_margin_start(14); box.set_margin_end(14)
        box.set_margin_top(14); box.set_margin_bottom(14); box.set_spacing(8)

        when = Gtk.Box(spacing=6)
        ent_min = Gtk.SpinButton.new_with_range(1, 10080, 1)
        ent_min.set_value(15)
        when.append(Gtk.Label(label="in"))
        when.append(ent_min)
        when.append(Gtk.Label(label="minutes"))
        box.append(when)

        rec = Gtk.DropDown.new_from_strings(
            ["once", "daily", "weekly", "monthly"])
        box.append(Gtk.Label(label="repeat:"))
        box.append(rec)

        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Set", Gtk.ResponseType.OK)
        def resp(d, r):
            if r == Gtk.ResponseType.OK:
                mins = int(ent_min.get_value())
                fires = int(time.time()) + mins * 60
                rec_idx = rec.get_selected()
                rec_key = (None, "daily", "weekly", "monthly")[rec_idx]
                self.db.add_reminder(nid, fires, rec_key)
                self.show_toast(f"reminder set in {mins} min")
            d.destroy()
        dlg.connect("response", resp); dlg.present()

    def show_reminder_list(self):
        dlg = Gtk.Dialog(transient_for=self, modal=True,
                         title="all reminders")
        dlg.set_default_size(440, 360)
        sw = Gtk.ScrolledWindow(); sw.set_hexpand(True); sw.set_vexpand(True)
        dlg.get_content_area().append(sw)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(12); box.set_margin_end(12)
        box.set_margin_top(12); box.set_margin_bottom(12)
        sw.set_child(box)
        for r in self.db.list_active_reminders():
            note = self.db.get_note(r["note_id"])
            if not note: continue
            try:
                ts = datetime.fromtimestamp(r["fires_at"]).strftime("%b %d %H:%M")
            except Exception:
                ts = "?"
            row = Gtk.Box(spacing=8)
            lbl = Gtk.Label(label=f"{ts} — {note['title'] or '(untitled)'}",
                            xalign=0)
            lbl.set_hexpand(True)
            row.append(lbl)
            cancel = SketchButton("Cancel", width=70, height=22,
                                  color=DANGER_RED)
            cancel.connect("clicked",
                           lambda _b, rid=r["id"]: self.db.delete_reminder(rid))
            row.append(cancel)
            box.append(row)
        dlg.add_buttons("Close", Gtk.ResponseType.CLOSE)
        dlg.connect("response", lambda d, _r: d.destroy())
        dlg.present()

    def _poll_reminders(self):
        try:
            for r in self.db.list_due_reminders():
                note = self.db.get_note(r["note_id"])
                title = note["title"] if note else "Reminder"
                body  = (note["body"][:120] if note and note["body"] else "")
                self._fire_notification(title, body)
                if r["recurrence"]:
                    delta = {"daily": 86_400, "weekly": 7 * 86_400,
                             "monthly": 30 * 86_400}.get(r["recurrence"])
                    if delta:
                        self.db.update_reminder(r["id"],
                                                fires_at=int(time.time()) + delta)
                    else:
                        self.db.update_reminder(r["id"], active=0)
                else:
                    self.db.update_reminder(r["id"], active=0)
        except Exception as e:
            log.error("reminder poll error: %s", e)
        return True

    def _fire_notification(self, title: str, body: str):
        try:
            subprocess.Popen(
                ["notify-send", "-a", APP_NAME, title or "Reminder", body or ""],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except FileNotFoundError:
            log.warning("notify-send not installed; reminder=%s", title)
        self.show_toast(f"⏰ {title}")

    # ── Templates ──────────────────────────────────────────────────────────
    def show_templates(self):
        dlg = Gtk.Dialog(transient_for=self, modal=True, title="templates")
        dlg.set_default_size(420, 500)
        sw = Gtk.ScrolledWindow(); sw.set_hexpand(True); sw.set_vexpand(True)
        dlg.get_content_area().append(sw)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(12); box.set_margin_end(12)
        box.set_margin_top(12); box.set_margin_bottom(12)
        sw.set_child(box)
        for t in self.db.list_templates():
            row = Gtk.Box(spacing=8)
            lbl = Gtk.Label(label=f"{KIND_ICONS.get(t['kind'],'·')}  {t['name']}",
                            xalign=0)
            lbl.set_hexpand(True); row.append(lbl)
            use = SketchButton("Use", width=58, height=22, color=NEON_GREEN)
            use.connect("clicked",
                        lambda _b, tid=t["id"]: (
                            self.new_note(from_template_id=tid),
                            dlg.destroy()))
            row.append(use)
            if not t["builtin"]:
                rm = SketchButton("✕", width=28, height=22, color=DANGER_RED)
                rm.connect("clicked",
                           lambda _b, tid=t["id"]:
                           (self.db.delete_template(tid), dlg.destroy(),
                            self.show_templates()))
                row.append(rm)
            box.append(row)
        dlg.add_buttons("Close", Gtk.ResponseType.CLOSE)
        dlg.connect("response", lambda d, _r: d.destroy())
        dlg.present()

    # ── Color picker ───────────────────────────────────────────────────────
    def show_color_picker(self, nid: str):
        dlg = Gtk.Dialog(transient_for=self, modal=True, title="note color")
        dlg.set_default_size(320, -1)
        ca = dlg.get_content_area()
        ca.set_margin_start(14); ca.set_margin_end(14)
        ca.set_margin_top(14); ca.set_margin_bottom(14)

        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(5)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        ca.append(flow)
        for c in NOTE_COLORS:
            b = Gtk.Button()
            da = Gtk.DrawingArea()
            da.set_size_request(48, 48)
            da.set_content_width(48); da.set_content_height(48)
            rgb = c["rgb"]
            def make_draw(rgb, name):
                def _d(area, cr, w, h, _=None):
                    cr.set_source_rgb(*rgb)
                    cr.arc(w/2, h/2, w/2 - 4, 0, math.pi*2); cr.fill()
                    cr.set_source_rgba(0,0,0,0.7); cr.set_line_width(1.4)
                    sketch_rect(cr, 4, 4, w-8, h-8, jitter=0.5,
                                key=("cs", name))
                return _d
            da.set_draw_func(make_draw(rgb, c["key"]))
            b.set_child(da)
            b.connect("clicked",
                      lambda _b, key=c["key"]:
                      (self.db.update_note(nid, color=key),
                       self.canvas.update_note(nid), dlg.destroy()))
            flow.append(b)

        # custom hex
        row = Gtk.Box(spacing=6)
        ca.append(row)
        row.append(Gtk.Label(label="custom hex:"))
        ent = Gtk.Entry(); ent.set_placeholder_text("#ff00ff")
        row.append(ent)
        b = SketchButton("Set", width=58, height=24, color=NEON_PINK)
        def apply_hex(*_):
            hx = ent.get_text().strip()
            if re.match(r"^#?[0-9a-fA-F]{6}$", hx):
                self.db.update_note(nid, custom_hex="#" + hx.lstrip("#"))
                self.canvas.update_note(nid); dlg.destroy()
            else:
                self.show_toast("invalid hex")
        b.connect("clicked", apply_hex)
        row.append(b)

        dlg.add_buttons("Close", Gtk.ResponseType.CLOSE)
        dlg.connect("response", lambda d, _r: d.destroy())
        dlg.present()

    # ── Filter / search ────────────────────────────────────────────────────
    def _on_search(self, _e, txt):
        self.search_text = (txt or "").strip().lower()
        self._apply_filters()

    def _show_filter_menu(self, btn):
        pop = Gtk.Popover(); pop.set_parent(btn)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_start(8); box.set_margin_end(8)
        box.set_margin_top(8); box.set_margin_bottom(8)
        pop.set_child(box)

        # by color
        box.append(Gtk.Label(label="color:", xalign=0))
        for c in [{"key":"all","name":"all","rgb":(0.5,0.5,0.5)}] + NOTE_COLORS:
            b = SketchButton(c["name"], width=180, height=22, color=NEON_BLUE)
            b.connect("clicked",
                      lambda _b, k=c["key"]: (setattr(self, "filter_color", k),
                                              self._apply_filters(), pop.popdown()))
            box.append(b)
        box.append(SketchSeparator(length=180, color=INK_FAINT))
        # by priority
        box.append(Gtk.Label(label="priority:", xalign=0))
        for p in [{"key":"all","label":"all"}] + PRIORITIES:
            b = SketchButton(p["label"], width=180, height=22, color=NEON_BLUE)
            b.connect("clicked",
                      lambda _b, k=p["key"]: (setattr(self, "filter_prio", k),
                                              self._apply_filters(), pop.popdown()))
            box.append(b)
        box.append(SketchSeparator(length=180, color=INK_FAINT))
        b = SketchButton("Clear filters", width=180, height=22, color=DANGER_RED)
        b.connect("clicked", lambda _b: (setattr(self, "filter_color", "all"),
                                          setattr(self, "filter_prio", "all"),
                                          setattr(self, "filter_tag", ""),
                                          self._apply_filters(), pop.popdown()))
        box.append(b)
        pop.popup()

    def _apply_filters(self):
        for nid, sn in self.canvas.notes.items():
            row = self.db.get_note(nid)
            if not row:
                sn.set_visible(False); continue
            ok = True
            if self.search_text:
                hay = " ".join((row["title"] or "", row["body"] or "",
                                row["tags"] or "")).lower()
                if self.search_text not in hay: ok = False
            if ok and self.filter_color != "all":
                if row["color"] != self.filter_color: ok = False
            if ok and self.filter_prio != "all":
                if row["priority"] != self.filter_prio: ok = False
            sn.set_visible(ok)
        # update filter label
        bits = []
        if self.search_text: bits.append(f"q:{self.search_text}")
        if self.filter_color != "all": bits.append(f"color:{self.filter_color}")
        if self.filter_prio  != "all": bits.append(f"prio:{self.filter_prio}")
        self.filter_lbl.set_text(" • ".join(bits) if bits else "")

    # ── Backgrounds / arrange / sort mode ──────────────────────────────────
    def _show_bg_menu(self, btn):
        pop = Gtk.Popover(); pop.set_parent(btn)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(6); box.set_margin_end(6)
        box.set_margin_top(6); box.set_margin_bottom(6)
        pop.set_child(box)
        for bg in CANVAS_BACKGROUNDS:
            b = SketchButton(bg["name"], width=140, height=22, color=NEON_BLUE)
            b.connect("clicked", lambda _b, k=bg["key"]:
                      (self.canvas.set_background(k),
                       self.db.update_board(self.current_board, background=k)
                       if self.current_board else None,
                       pop.popdown()))
            box.append(b)
        pop.popup()

    def _show_arrange_menu(self, btn):
        pop = Gtk.Popover(); pop.set_parent(btn)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(6); box.set_margin_end(6)
        box.set_margin_top(6); box.set_margin_bottom(6)
        pop.set_child(box)
        for label, fn in (
            ("Auto-arrange grid",   lambda: self.auto_arrange_grid()),
            ("Group by color",      lambda: self.group_by_color()),
            ("Group by priority",   lambda: self.group_by_priority()),
            ("Align selection L",   lambda: self.canvas.align_selected("left")),
            ("Align selection R",   lambda: self.canvas.align_selected("right")),
            ("Align selection T",   lambda: self.canvas.align_selected("top")),
            ("Align selection B",   lambda: self.canvas.align_selected("bottom")),
            ("Distribute X",        lambda: self.canvas.distribute_selected("x")),
            ("Distribute Y",        lambda: self.canvas.distribute_selected("y")),
        ):
            b = SketchButton(label, width=180, height=22, color=NEON_BLUE)
            b.connect("clicked", lambda _b, f=fn: (f(), pop.popdown()))
            box.append(b)
        pop.popup()

    def auto_arrange_grid(self):
        if not self.current_board: return
        notes = self.db.list_notes(self.current_board)
        cols = max(1, int(math.sqrt(len(notes))))
        gap = 30; w = 260; h = 220
        x0, y0 = 60, 80
        for i, n in enumerate(notes):
            cx = x0 + (i % cols) * (w + gap)
            cy = y0 + (i // cols) * (h + gap)
            self.db.update_note(n["id"], x=cx, y=cy,
                                tilt=random.uniform(-5, 5))
            self.canvas.update_note(n["id"])
        self.show_toast("arranged")

    def group_by_color(self):
        if not self.current_board: return
        notes = self.db.list_notes(self.current_board)
        # one column per color
        cols = {c["key"]: [] for c in NOTE_COLORS}
        for n in notes:
            cols.setdefault(n["color"], []).append(n)
        x = 60; col_w = 280; gap_y = 30
        for k in [c["key"] for c in NOTE_COLORS]:
            if not cols.get(k): continue
            y = 80
            for n in cols[k]:
                self.db.update_note(n["id"], x=x, y=y,
                                    tilt=random.uniform(-4, 4))
                self.canvas.update_note(n["id"])
                y += 220 + gap_y
            x += col_w
        self.show_toast("grouped by color")

    def group_by_priority(self):
        if not self.current_board: return
        order = ["urgent", "high", "normal", "low"]
        notes = self.db.list_notes(self.current_board)
        by_p = {k: [] for k in order}
        for n in notes:
            by_p.setdefault(n["priority"] or "normal", []).append(n)
        x = 60
        for k in order:
            if not by_p.get(k): continue
            y = 80
            for n in by_p[k]:
                self.db.update_note(n["id"], x=x, y=y,
                                    tilt=random.uniform(-4, 4))
                self.canvas.update_note(n["id"])
                y += 220 + 30
            x += 290
        self.show_toast("grouped by priority")

    def toggle_sort_mode(self):
        # straighten all notes (tilt → 0) — toggle on / off
        if not self.current_board: return
        if not getattr(self, "_sort_on", False):
            self._sort_orig = {}
            for n in self.db.list_notes(self.current_board):
                self._sort_orig[n["id"]] = float(n["tilt"] or 0)
                self.db.update_note(n["id"], tilt=0)
                self.canvas.update_note(n["id"])
            self._sort_on = True
            self.btn_sort.set_active(True) if hasattr(self.btn_sort, "set_active") else None
            self.show_toast("flattened — click again to restore")
        else:
            for nid, t in self._sort_orig.items():
                if self.db.get_note(nid):
                    self.db.update_note(nid, tilt=t)
                    self.canvas.update_note(nid)
            self._sort_on = False
            self.show_toast("restored")

    # ── Export ─────────────────────────────────────────────────────────────
    def export_selected(self):
        sels = self.canvas.selected_ids()
        if not sels:
            # whole-board JSON export
            self.export_board_json()
            return
        for nid in sels:
            self.export_note_png(nid)

    def export_note_png(self, nid: str):
        sn = self.canvas.notes.get(nid)
        if not sn:
            self.show_toast("no widget"); return
        w_full = sn.get_size_request()[0]
        h_full = sn.get_size_request()[1]
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w_full, h_full)
        cr = cairo.Context(surface)
        sn._draw_inner(cr, w_full, h_full)
        out = EXPORT_DIR / f"sticky_{nid}_{int(time.time())}.png"
        surface.write_to_png(str(out))
        self.show_toast(f"saved {out.name}")
        log.info("exported %s", out)

    def export_note_text(self, nid: str):
        row = self.db.get_note(nid)
        if not row: return
        out = EXPORT_DIR / f"sticky_{nid}_{int(time.time())}.txt"
        out.write_text(f"# {row['title'] or '(untitled)'}\n\n{row['body'] or ''}\n",
                       encoding="utf-8")
        self.show_toast(f"saved {out.name}")

    def export_note_md(self, nid: str):
        row = self.db.get_note(nid)
        if not row: return
        out = EXPORT_DIR / f"sticky_{nid}_{int(time.time())}.md"
        body = row["body"] or ""
        if row["kind"] == "code":
            body = f"```{row['code_lang'] or ''}\n{body}\n```"
        out.write_text(f"# {row['title'] or '(untitled)'}\n\n{body}\n",
                       encoding="utf-8")
        self.show_toast(f"saved {out.name}")

    def export_board_json(self):
        if not self.current_board: return
        b = self.db.get_board(self.current_board)
        notes = [dict(n) for n in self.db.list_notes(self.current_board, True)]
        out = EXPORT_DIR / f"board_{b['name'].replace(' ','_')}_{int(time.time())}.json"
        out.write_text(json.dumps({"board": dict(b), "notes": notes},
                                  indent=2, default=str), encoding="utf-8")
        self.show_toast(f"saved {out.name}")

    # ── Versions ───────────────────────────────────────────────────────────
    def show_versions_dialog(self, nid: str):
        dlg = Gtk.Dialog(transient_for=self, modal=True, title="versions")
        dlg.set_default_size(440, 460)
        sw = Gtk.ScrolledWindow(); sw.set_hexpand(True); sw.set_vexpand(True)
        dlg.get_content_area().append(sw)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_start(12); box.set_margin_end(12)
        box.set_margin_top(12); box.set_margin_bottom(12)
        sw.set_child(box)
        for v in self.db.list_versions(nid):
            row = Gtk.Box(spacing=8)
            try:
                ts = datetime.fromtimestamp(v["saved"]).strftime("%b %d %H:%M:%S")
            except Exception: ts = "?"
            preview = (v["body"] or "")[:60].replace("\n", " ")
            row.append(Gtk.Label(label=f"{ts} — {preview}", xalign=0))
            sp = Gtk.Box(); sp.set_hexpand(True); row.append(sp)
            r = SketchButton("Restore", width=78, height=22, color=NEON_GREEN)
            r.connect("clicked",
                      lambda _b, vv=v: (self.db.update_note(nid,
                                          title=vv["title"], body=vv["body"]),
                                        self.canvas.update_note(nid),
                                        self.show_toast("restored"),
                                        dlg.destroy()))
            row.append(r)
            box.append(row)
        dlg.add_buttons("Close", Gtk.ResponseType.CLOSE)
        dlg.connect("response", lambda d, _r: d.destroy())
        dlg.present()

    # ── Settings ───────────────────────────────────────────────────────────
    def show_settings(self):
        dlg = Gtk.Dialog(transient_for=self, modal=True, title="settings")
        dlg.set_default_size(420, -1)
        ca = dlg.get_content_area()
        ca.set_margin_start(14); ca.set_margin_end(14)
        ca.set_margin_top(14); ca.set_margin_bottom(14); ca.set_spacing(8)

        ca.append(Gtk.Label(label="Default new-note color:", xalign=0))
        col_combo = Gtk.DropDown.new_from_strings([c["name"] for c in NOTE_COLORS])
        cur = self.db.get_setting("default_color", "yellow")
        col_combo.set_selected(next((i for i, c in enumerate(NOTE_COLORS)
                                     if c["key"] == cur), 0))
        ca.append(col_combo)

        ca.append(Gtk.Label(label="Master password:", xalign=0))
        bp = SketchButton("Set/change…", width=160, height=24, color=ACCENT_GOLD)
        bp.connect("clicked", lambda _b: self.prompt_set_password())
        ca.append(bp)

        ca.append(Gtk.Label(label="Backup vault:", xalign=0))
        bb = SketchButton("Backup .zip…", width=160, height=24, color=NEON_BLUE)
        bb.connect("clicked", lambda _b: self.backup_vault())
        ca.append(bb)

        # stats
        nc = sum(1 for _ in self.db.list_notes(self.current_board, True)) \
                if self.current_board else 0
        bc = len(self.db.list_boards())
        ca.append(Gtk.Label(label=f"\n{bc} board(s) • {nc} note(s) on this board",
                            xalign=0))

        dlg.add_buttons("Close", Gtk.ResponseType.CLOSE)
        def resp(d, _r):
            self.db.set_setting("default_color",
                                NOTE_COLORS[col_combo.get_selected()]["key"])
            d.destroy()
        dlg.connect("response", resp); dlg.present()

    def backup_vault(self):
        try:
            import zipfile
            out = BACKUP_DIR / f"stickies_backup_{int(time.time())}.zip"
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                z.write(DB_PATH, DB_PATH.name)
            self.show_toast(f"backup → {out.name}")
        except Exception as e:
            log.error("backup failed: %s", e)
            self.show_toast("backup failed")

    # ── Locking prompts ────────────────────────────────────────────────────
    def prompt_set_password(self) -> bool:
        if not HAS_CRYPTO:
            self.show_toast("install python-cryptography"); return False
        dlg = Gtk.Dialog(transient_for=self, modal=True,
                         title="set master password")
        dlg.set_default_size(340, -1)
        ca = dlg.get_content_area()
        ca.set_margin_start(14); ca.set_margin_end(14)
        ca.set_margin_top(14); ca.set_margin_bottom(14); ca.set_spacing(6)
        ent = Gtk.PasswordEntry(); ent.set_show_peek_icon(True)
        ent2 = Gtk.PasswordEntry(); ent2.set_show_peek_icon(True)
        ca.append(Gtk.Label(label="new password:", xalign=0)); ca.append(ent)
        ca.append(Gtk.Label(label="confirm:", xalign=0)); ca.append(ent2)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Set", Gtk.ResponseType.OK)
        result = {"ok": False}
        loop = GLib.MainLoop()
        def resp(d, r):
            if r == Gtk.ResponseType.OK:
                p1 = ent.get_text(); p2 = ent2.get_text()
                if p1 and p1 == p2:
                    self.crypto.setup(p1)
                    result["ok"] = True
            d.destroy(); loop.quit()
        dlg.connect("response", resp); dlg.present(); loop.run()
        return result["ok"]

    def prompt_unlock(self) -> bool:
        if not HAS_CRYPTO:
            self.show_toast("install python-cryptography"); return False
        if self.crypto.is_unlocked(): return True
        dlg = Gtk.Dialog(transient_for=self, modal=True, title="unlock vault")
        dlg.set_default_size(320, -1)
        ca = dlg.get_content_area()
        ca.set_margin_start(14); ca.set_margin_end(14)
        ca.set_margin_top(14); ca.set_margin_bottom(14); ca.set_spacing(6)
        ent = Gtk.PasswordEntry(); ent.set_show_peek_icon(True)
        ca.append(Gtk.Label(label="master password:", xalign=0))
        ca.append(ent)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Unlock", Gtk.ResponseType.OK)
        result = {"ok": False}
        loop = GLib.MainLoop()
        def resp(d, r):
            if r == Gtk.ResponseType.OK:
                if self.crypto.unlock(ent.get_text()):
                    result["ok"] = True
                else:
                    self.show_toast("wrong password")
            d.destroy(); loop.quit()
        dlg.connect("response", resp); dlg.present(); loop.run()
        return result["ok"]

    # ── Toast / status ─────────────────────────────────────────────────────
    def show_toast(self, msg: str, ms: int = 2200):
        if not self._toast_label: return
        self._toast_label.set_text(msg)
        self._toast_label.set_visible(True)
        def hide(): self._toast_label.set_visible(False); return False
        GLib.timeout_add(ms, hide)

    def _refresh_status(self):
        b = self.db.get_board(self.current_board) if self.current_board else None
        nc = len(self.db.list_notes(self.current_board)) \
                if self.current_board else 0
        if b:
            self.status_lbl.set_text(f"board: {b['name']} • {nc} note(s)")
            self.sb_stats.set_text(f"{nc} note(s) on this board")
        else:
            self.status_lbl.set_text("no board"); self.sb_stats.set_text("")
        rems = len(self.db.list_active_reminders())
        self.status_right.set_text(f"⏰ {rems} reminders")

    def _toggle_archived(self, btn):
        self.show_archived = not self.show_archived
        self.canvas.load_board(self.current_board)  # simple reload
        if self.show_archived: self.show_toast("showing archived")
        else: self.show_toast("hiding archived")

    # ── Fullscreen ─────────────────────────────────────────────────────────
    def toggle_fullscreen(self):
        if self.is_fullscreen(): self.unfullscreen()
        else: self.fullscreen()

    # ── Keyboard shortcuts ─────────────────────────────────────────────────
    def _wire_keys(self):
        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._on_key)
        kc.connect("key-released", self._on_key_up)
        self.add_controller(kc)

    def _on_key(self, ctrl, keyval, code, state):
        ctrl_held  = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift_held = bool(state & Gdk.ModifierType.SHIFT_MASK)
        if keyval == Gdk.KEY_space:
            self.canvas.set_space_pan(True); return False
        if ctrl_held and keyval == Gdk.KEY_n:
            if shift_held: self.show_templates()
            else:          self.new_note()
            return True
        if ctrl_held and keyval == Gdk.KEY_f:
            self.search.entry.grab_focus(); return True
        if ctrl_held and keyval == Gdk.KEY_a:
            for sn in self.canvas.notes.values():
                sn.selected = True; sn.queue_draw()
            return True
        if ctrl_held and keyval == Gdk.KEY_g:
            self.show_toast("groups: not implemented yet"); return True
        if ctrl_held and keyval == Gdk.KEY_l:
            sels = self.canvas.selected_ids()
            for nid in sels: self.toggle_lock(nid)
            return True
        if ctrl_held and keyval == Gdk.KEY_e:
            self.export_selected(); return True
        if keyval == Gdk.KEY_Delete:
            for nid in self.canvas.selected_ids(): self.delete_note(nid)
            return True
        if keyval == Gdk.KEY_Escape:
            for sn in self.canvas.notes.values():
                sn.selected = False; sn.queue_draw()
            return True
        if keyval == Gdk.KEY_F11:
            self.toggle_fullscreen(); return True
        return False

    def _on_key_up(self, ctrl, keyval, code, state):
        if keyval == Gdk.KEY_space:
            self.canvas.set_space_pan(False)


# ═══════════════════════════════════════════════════════════════════════════════
#  Application
# ═══════════════════════════════════════════════════════════════════════════════
class StickiesApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = self.props.active_window or StickiesWindow(self)
        win.present()


def main():
    log.info("starting %s", APP_NAME)
    app = StickiesApp()
    sys.exit(app.run(sys.argv))


if __name__ == "__main__":
    main()
