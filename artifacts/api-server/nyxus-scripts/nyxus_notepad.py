#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║   NYXUS NOTEPAD — Hand-drawn rich notes for the NYXUS desktop        ║
# ║                                                                      ║
# ║   • Hand-drawn Cairo aesthetic on every widget                       ║
# ║   • Rich-text editor with bold/italic/underline/strike/headings/code ║
# ║   • Markdown preview, code-block syntax highlighting                 ║
# ║   • Search, pin, star, colours, tags, notebooks                      ║
# ║   • AES-256 locked notes (Fernet)                                    ║
# ║   • Export: Markdown / TXT / HTML / PDF                              ║
# ║   • Auto-save, drafts, command palette, distraction-free mode        ║
# ║   • Find & replace, word/char/reading-time, statistics               ║
# ║   • All formatting shortcuts: Ctrl+B/I/U, Ctrl+S, Ctrl+F, etc.       ║
# ║                                                                      ║
# ║   © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED      ║
# ╚══════════════════════════════════════════════════════════════════════╝
"""NYXUS Notepad — single-file GTK4 Python application.

All persistent data lives under ~/.config/nyxus-notepad/.
Database is sqlite3, locked-note encryption is Fernet (AES-128 CBC + HMAC).
"""
from __future__ import annotations

import base64, hashlib, html, json, math, os, random, re, sqlite3, subprocess
import sys, threading, time, traceback, uuid
from datetime import datetime, timedelta
from pathlib import Path

# ── Optional dependencies (degrade gracefully) ─────────────────────────────────
try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    gi.require_version("Pango", "1.0")
    gi.require_version("PangoCairo", "1.0")
    from gi.repository import Gtk, Gdk, GLib, Gio, Pango, PangoCairo, GObject
except Exception as e:
    sys.stderr.write(
        "ERROR: PyGObject/GTK4 not available.\n"
        "  Arch:  sudo pacman -S --needed python-gobject gtk4 python-cairo\n"
        f"  Detail: {e}\n"
    )
    sys.exit(1)

try:
    gi.require_version("GtkSource", "5")
    from gi.repository import GtkSource
    HAS_SOURCEVIEW = True
except Exception:
    HAS_SOURCEVIEW = False

try:
    from cryptography.fernet import Fernet, InvalidToken
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    HAS_CRYPTO = True
except Exception:
    HAS_CRYPTO = False

try:
    from reportlab.lib.pagesizes import LETTER
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Preformatted, PageBreak)
    from reportlab.lib.colors import HexColor
    HAS_REPORTLAB = True
except Exception:
    HAS_REPORTLAB = False

try:
    import markdown as _md
    HAS_MARKDOWN = True
except Exception:
    HAS_MARKDOWN = False

# ═══════════════════════════════════════════════════════════════════════════════
#  Constants & paths
# ═══════════════════════════════════════════════════════════════════════════════
APP_ID    = "com.nyxus.notepad"
APP_NAME  = "NYXUS Notepad"
WIN_W, WIN_H = 1280, 820

CONFIG_DIR  = Path.home() / ".config" / "nyxus-notepad"
NOTES_DIR   = CONFIG_DIR / "notes"
BACKUP_DIR  = CONFIG_DIR / "backups"
EXPORT_DIR  = Path.home() / "Documents" / "NyxusNotes"
DB_PATH     = CONFIG_DIR / "notes.db"
CONFIG_PATH = CONFIG_DIR / "config.json"
LOG_PATH    = "/tmp/nyxus-notepad.log"
for d in (CONFIG_DIR, NOTES_DIR, BACKUP_DIR, EXPORT_DIR):
    d.mkdir(parents=True, exist_ok=True)


def log(msg: str):
    try:
        with open(LOG_PATH, "a") as f:
            f.write(f"[{datetime.now().isoformat(timespec='seconds')}] {msg}\n")
    except Exception:
        pass

# ── NYXUS colour palette (RGB floats) ───────────────────────────────────────
BG_DARK     = (0.039, 0.039, 0.071)   # #0a0a12
BG_PANEL    = (0.072, 0.067, 0.110)
BG_RAISED   = (0.101, 0.094, 0.156)
INK_BRIGHT  = (0.941, 0.922, 0.980)
INK_DIM     = (0.620, 0.604, 0.690)
INK_FAINT   = (0.380, 0.365, 0.450)

NEON_PINK   = (1.000, 0.000, 1.000)   # #ff00ff
NEON_BLUE   = (0.000, 0.533, 1.000)   # #0088ff
NEON_GREEN  = (0.224, 1.000, 0.078)   # #39ff14
ACCENT_GOLD = (1.000, 0.776, 0.196)
ACCENT_PURP = (0.545, 0.361, 0.965)   # #8b5cf6
DANGER_RED  = (1.000, 0.302, 0.243)

NOTE_COLORS = [
    {"key": "lemon",    "rgb": (0.996, 0.941, 0.541), "name": "Lemon"},
    {"key": "rose",     "rgb": (0.992, 0.643, 0.686), "name": "Rose"},
    {"key": "sky",      "rgb": (0.576, 0.773, 0.992), "name": "Sky"},
    {"key": "mint",     "rgb": (0.525, 0.937, 0.671), "name": "Mint"},
    {"key": "lavender", "rgb": (0.914, 0.835, 1.000), "name": "Lavender"},
    {"key": "peach",    "rgb": (0.992, 0.729, 0.455), "name": "Peach"},
    {"key": "cloud",    "rgb": (0.580, 0.580, 0.620), "name": "Cloud"},
]
NOTE_COLOR_BY_KEY = {c["key"]: c for c in NOTE_COLORS}

# ═══════════════════════════════════════════════════════════════════════════════
#  Hand-drawn Cairo helpers
# ═══════════════════════════════════════════════════════════════════════════════
def _seeded(key) -> random.Random:
    """Stable per-shape RNG so jitter doesn't shimmer between repaints."""
    r = random.Random()
    r.seed(hash(key) & 0xFFFFFFFF)
    return r


def sketch_line(cr, x1, y1, x2, y2, *, jitter=0.7, segments=10, key=None):
    """A single wobbly hand-drawn line."""
    rng = _seeded(key or (round(x1), round(y1), round(x2), round(y2)))
    dx, dy = (x2 - x1) / segments, (y2 - y1) / segments
    cr.move_to(x1 + (rng.random() - 0.5) * jitter * 0.4,
               y1 + (rng.random() - 0.5) * jitter * 0.4)
    for i in range(1, segments):
        cr.line_to(x1 + dx * i + (rng.random() - 0.5) * jitter,
                   y1 + dy * i + (rng.random() - 0.5) * jitter)
    cr.line_to(x2 + (rng.random() - 0.5) * jitter * 0.4,
               y2 + (rng.random() - 0.5) * jitter * 0.4)
    cr.stroke()


def sketch_rect(cr, x, y, w, h, *, jitter=0.6, key=None, double=True):
    """Hand-drawn rectangle outline.  `double` adds a faint second top pass."""
    k = key or ("rect", round(x), round(y), round(w), round(h))
    sketch_line(cr, x, y,         x + w, y,         jitter=jitter, key=(k, "t1"))
    sketch_line(cr, x + w, y,     x + w, y + h,     jitter=jitter, key=(k, "r1"))
    sketch_line(cr, x + w, y + h, x,     y + h,     jitter=jitter, key=(k, "b1"))
    sketch_line(cr, x, y + h,     x,     y,         jitter=jitter, key=(k, "l1"))
    if double:
        sketch_line(cr, x + 0.6, y - 0.4, x + w - 0.4, y + 0.3,
                    jitter=jitter * 0.6, segments=6, key=(k, "t2"))


def sketch_filled_rect(cr, x, y, w, h, fill, stroke, *, jitter=0.7,
                       radius=0, key=None):
    """Filled rounded rectangle with sketchy outline."""
    cr.save()
    cr.set_source_rgba(*fill)
    if radius > 0:
        _rounded_path(cr, x, y, w, h, radius)
        cr.fill()
    else:
        cr.rectangle(x, y, w, h)
        cr.fill()
    cr.set_source_rgba(*stroke)
    cr.set_line_width(1.2)
    sketch_rect(cr, x, y, w, h, jitter=jitter, key=key)
    cr.restore()


def _rounded_path(cr, x, y, w, h, r):
    cr.new_sub_path()
    cr.arc(x + w - r, y + r,         r, -math.pi/2, 0)
    cr.arc(x + w - r, y + h - r,     r, 0,           math.pi/2)
    cr.arc(x + r,     y + h - r,     r, math.pi/2,   math.pi)
    cr.arc(x + r,     y + r,         r, math.pi,     3*math.pi/2)
    cr.close_path()


def sketch_underline(cr, x, y, w, *, jitter=0.8, key=None):
    """Wavy underline / divider."""
    rng = _seeded(key or ("ul", round(x), round(y), round(w)))
    cr.move_to(x, y)
    seg = max(6, int(w / 12))
    for i in range(1, seg + 1):
        px = x + w * i / seg
        py = y + (rng.random() - 0.5) * jitter * 1.4
        cr.line_to(px, py)
    cr.stroke()


def sketch_check(cr, x, y, size, *, key=None):
    """Hand-drawn check-mark inside a `size`-pixel box."""
    cr.set_line_cap(1)  # round
    rng = _seeded(key or ("chk", round(x), round(y)))
    cr.move_to(x + size * 0.18,
               y + size * 0.55 + (rng.random() - 0.5) * 0.5)
    cr.line_to(x + size * 0.42 + (rng.random() - 0.5) * 0.5,
               y + size * 0.78)
    cr.line_to(x + size * 0.85 + (rng.random() - 0.5) * 0.5,
               y + size * 0.22)
    cr.stroke()


def sketch_pin(cr, x, y, size, *, color=DANGER_RED, key=None):
    """Hand-drawn push-pin glyph."""
    cr.save()
    cr.set_source_rgba(*color, 0.95)
    cr.arc(x + size/2, y + size*0.42, size*0.32, 0, math.pi*2)
    cr.fill()
    cr.set_source_rgba(0, 0, 0, 0.5)
    cr.set_line_width(1.0)
    cr.move_to(x + size/2, y + size*0.74)
    cr.line_to(x + size/2, y + size*0.95)
    cr.stroke()
    cr.set_source_rgba(1, 1, 1, 0.65)
    cr.arc(x + size*0.42, y + size*0.34, size*0.10, 0, math.pi*2)
    cr.fill()
    cr.restore()


def sketch_star(cr, x, y, size, *, filled=False, color=ACCENT_GOLD):
    """5-point hand-drawn star."""
    cx, cy = x + size/2, y + size/2
    r_outer = size/2 - 1
    r_inner = r_outer * 0.42
    cr.save()
    cr.set_source_rgba(*color, 0.95 if filled else 0.7)
    for i in range(11):
        ang  = -math.pi/2 + math.pi * i / 5
        rad  = r_outer if i % 2 == 0 else r_inner
        px   = cx + math.cos(ang) * rad
        py   = cy + math.sin(ang) * rad
        if i == 0:
            cr.move_to(px, py)
        else:
            cr.line_to(px, py)
    cr.close_path()
    if filled:
        cr.fill_preserve()
    cr.set_line_width(1.2)
    cr.stroke()
    cr.restore()


def sketch_lock(cr, x, y, size, *, color=ACCENT_GOLD, locked=True):
    """Hand-drawn padlock."""
    cr.save()
    cr.set_source_rgba(*color, 0.92)
    cr.set_line_width(1.4)
    bw, bh = size * 0.7, size * 0.45
    bx, by = x + (size - bw) / 2, y + size - bh - 1
    sketch_rect(cr, bx, by, bw, bh, jitter=0.5,
                key=("lock-body", round(x), round(y)))
    cr.arc(x + size/2, by - size*0.06, size * 0.22,
           math.pi if locked else math.pi*0.9, math.pi*2)
    cr.stroke()
    cr.set_source_rgba(*color, 0.55)
    cr.arc(x + size/2, by + bh*0.55, size*0.06, 0, math.pi*2)
    cr.fill()
    cr.restore()


def text_at(cr, x, y, txt, *, size=14, family="Caveat", bold=False,
            color=INK_BRIGHT, alpha=1.0, max_w=None):
    """Lay out Pango text and stamp it at (x,y).  Returns (width, height)."""
    layout = PangoCairo.create_layout(cr)
    desc = Pango.FontDescription()
    desc.set_family(family)
    desc.set_size(int(size * Pango.SCALE))
    desc.set_weight(Pango.Weight.BOLD if bold else Pango.Weight.NORMAL)
    layout.set_font_description(desc)
    if max_w:
        layout.set_width(int(max_w * Pango.SCALE))
        layout.set_ellipsize(Pango.EllipsizeMode.END)
    layout.set_text(txt or "", -1)
    cr.save()
    cr.set_source_rgba(*color, alpha)
    cr.move_to(x, y)
    PangoCairo.show_layout(cr, layout)
    cr.restore()
    w, h = layout.get_pixel_size()
    return w, h


# ═══════════════════════════════════════════════════════════════════════════════
#  Database
# ═══════════════════════════════════════════════════════════════════════════════
DB_SCHEMA = """
CREATE TABLE IF NOT EXISTS notebooks (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, parent_id TEXT, created REAL
);
CREATE TABLE IF NOT EXISTS notes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '',
    content TEXT NOT NULL DEFAULT '',
    notebook_id TEXT,
    color TEXT DEFAULT 'cloud',
    pinned INTEGER DEFAULT 0,
    starred INTEGER DEFAULT 0,
    locked INTEGER DEFAULT 0,
    locked_blob BLOB,
    created REAL,
    modified REAL,
    word_count INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS tags (
    note_id TEXT NOT NULL, tag TEXT NOT NULL,
    PRIMARY KEY(note_id, tag)
);
CREATE TABLE IF NOT EXISTS drafts (
    note_id TEXT NOT NULL, ts REAL NOT NULL, content TEXT,
    PRIMARY KEY(note_id, ts)
);
CREATE TABLE IF NOT EXISTS templates (
    id TEXT PRIMARY KEY, name TEXT, content TEXT, builtin INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY, value TEXT
);
CREATE INDEX IF NOT EXISTS idx_notes_modified ON notes(modified DESC);
CREATE INDEX IF NOT EXISTS idx_notes_notebook ON notes(notebook_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
"""

BUILTIN_TEMPLATES = [
    ("meeting",  "Meeting Notes",
     "# Meeting Notes\n**Date:** {date}\n**Attendees:** \n\n## Agenda\n- \n\n## Discussion\n\n## Action Items\n- [ ] \n"),
    ("project",  "Project Plan",
     "# {title}\n\n## Goals\n- \n\n## Milestones\n- [ ] \n\n## Resources\n\n## Risks\n"),
    ("daily",    "Daily Journal",
     "# {date}\n\n## What went well\n\n## What didn't\n\n## Tomorrow\n- [ ] \n"),
    ("bug",      "Bug Report",
     "# Bug: \n\n**Severity:** \n**Component:** \n**Found:** {date}\n\n## Steps to reproduce\n1. \n\n## Expected\n\n## Actual\n\n## Logs\n```\n```\n"),
    ("review",   "Code Review",
     "# Code Review — \n\n**PR:** \n**Reviewer:** \n\n## Summary\n\n## Comments\n- \n\n## Verdict\n- [ ] Approve\n- [ ] Request changes\n"),
    ("research", "Research Notes",
     "# Research: \n\n## Question\n\n## Sources\n- \n\n## Findings\n\n## Open questions\n"),
    ("recipe",   "Recipe",
     "# \n\n**Serves:** \n**Time:** \n\n## Ingredients\n- \n\n## Method\n1. \n"),
    ("reading",  "Reading Notes",
     "# \n**Author:** \n**Started:** {date}\n\n## Key ideas\n- \n\n## Quotes\n> \n\n## My takeaway\n"),
    ("weekly",   "Weekly Review",
     "# Week of {date}\n\n## Wins\n\n## Challenges\n\n## Lessons learned\n\n## Next week\n- [ ] \n"),
    ("travel",   "Travel Itinerary",
     "# Trip to \n\n**Dates:** \n**Travelers:** \n\n## Day 1 — \n- \n\n## Packing\n- [ ] \n"),
]


class DB:
    def __init__(self, path: Path = DB_PATH):
        self.path = str(path)
        self.cn = sqlite3.connect(self.path)
        self.cn.row_factory = sqlite3.Row
        self.cn.executescript(DB_SCHEMA)
        self._seed_templates()

    def _seed_templates(self):
        cur = self.cn.execute("SELECT COUNT(*) FROM templates WHERE builtin=1")
        if cur.fetchone()[0] == 0:
            for tid, name, body in BUILTIN_TEMPLATES:
                self.cn.execute(
                    "INSERT INTO templates(id, name, content, builtin) VALUES(?,?,?,1)",
                    (tid, name, body))
            self.cn.commit()

    # ── settings ──────────────────────────────────────────────────────────
    def get_setting(self, key, default=None):
        cur = self.cn.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = cur.fetchone()
        return row["value"] if row else default

    def set_setting(self, key, value):
        self.cn.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)))
        self.cn.commit()

    # ── notebooks ─────────────────────────────────────────────────────────
    def list_notebooks(self):
        return list(self.cn.execute(
            "SELECT * FROM notebooks ORDER BY name COLLATE NOCASE"))

    def add_notebook(self, name, parent_id=None):
        nid = str(uuid.uuid4())[:8]
        self.cn.execute(
            "INSERT INTO notebooks(id, name, parent_id, created) VALUES(?,?,?,?)",
            (nid, name, parent_id, time.time()))
        self.cn.commit()
        return nid

    def delete_notebook(self, nid):
        self.cn.execute("UPDATE notes SET notebook_id=NULL WHERE notebook_id=?", (nid,))
        self.cn.execute("DELETE FROM notebooks WHERE id=?", (nid,))
        self.cn.commit()

    # ── notes ─────────────────────────────────────────────────────────────
    def list_notes(self, *, search="", notebook_id=None, color=None,
                   tag=None, sort="modified"):
        sql = "SELECT * FROM notes WHERE 1=1"
        args = []
        if search:
            sql += " AND (title LIKE ? OR content LIKE ?)"
            args += [f"%{search}%", f"%{search}%"]
        if notebook_id is not None:
            if notebook_id == "":
                sql += " AND notebook_id IS NULL"
            else:
                sql += " AND notebook_id=?"
                args.append(notebook_id)
        if color:
            sql += " AND color=?"
            args.append(color)
        if tag:
            sql += " AND id IN (SELECT note_id FROM tags WHERE tag=?)"
            args.append(tag)
        # sort key — pinned & starred always first
        sort_col = {
            "modified": "modified DESC",
            "created":  "created DESC",
            "title":    "title COLLATE NOCASE ASC",
            "words":    "word_count DESC",
        }.get(sort, "modified DESC")
        sql += f" ORDER BY pinned DESC, starred DESC, {sort_col}"
        return list(self.cn.execute(sql, args))

    def get_note(self, nid):
        cur = self.cn.execute("SELECT * FROM notes WHERE id=?", (nid,))
        return cur.fetchone()

    def create_note(self, *, title="", content="", notebook_id=None,
                    color="cloud"):
        nid = str(uuid.uuid4())
        now = time.time()
        wc = len(content.split()) if content else 0
        self.cn.execute(
            "INSERT INTO notes(id,title,content,notebook_id,color,"
            "created,modified,word_count) VALUES(?,?,?,?,?,?,?,?)",
            (nid, title, content, notebook_id, color, now, now, wc))
        self.cn.commit()
        return nid

    def update_note(self, nid, **fields):
        if not fields:
            return
        if "content" in fields:
            fields["word_count"] = len(fields["content"].split())
        fields["modified"] = time.time()
        cols = ", ".join(f"{k}=?" for k in fields)
        args = list(fields.values()) + [nid]
        self.cn.execute(f"UPDATE notes SET {cols} WHERE id=?", args)
        self.cn.commit()

    def delete_note(self, nid):
        self.cn.execute("DELETE FROM notes WHERE id=?", (nid,))
        self.cn.execute("DELETE FROM tags  WHERE note_id=?", (nid,))
        self.cn.execute("DELETE FROM drafts WHERE note_id=?", (nid,))
        self.cn.commit()

    def duplicate_note(self, nid):
        n = self.get_note(nid)
        if not n: return None
        return self.create_note(
            title=(n["title"] or "Untitled") + " (copy)",
            content=n["content"], notebook_id=n["notebook_id"],
            color=n["color"])

    # ── tags ──────────────────────────────────────────────────────────────
    def get_tags(self, nid=None):
        if nid:
            return [r["tag"] for r in self.cn.execute(
                "SELECT tag FROM tags WHERE note_id=? ORDER BY tag", (nid,))]
        return [r["tag"] for r in self.cn.execute(
            "SELECT DISTINCT tag FROM tags ORDER BY tag")]

    def set_tags(self, nid, tags):
        self.cn.execute("DELETE FROM tags WHERE note_id=?", (nid,))
        for t in tags:
            t = t.strip().lstrip("#").lower()
            if t:
                self.cn.execute(
                    "INSERT OR IGNORE INTO tags(note_id, tag) VALUES(?,?)",
                    (nid, t))
        self.cn.commit()

    # ── drafts ────────────────────────────────────────────────────────────
    def add_draft(self, nid, content):
        self.cn.execute(
            "INSERT INTO drafts(note_id, ts, content) VALUES(?,?,?)",
            (nid, time.time(), content))
        # keep last 30 drafts per note
        self.cn.execute(
            "DELETE FROM drafts WHERE note_id=? AND ts NOT IN ("
            "  SELECT ts FROM drafts WHERE note_id=? ORDER BY ts DESC LIMIT 30)",
            (nid, nid))
        self.cn.commit()

    def list_drafts(self, nid):
        return list(self.cn.execute(
            "SELECT ts, content FROM drafts WHERE note_id=? "
            "ORDER BY ts DESC", (nid,)))

    # ── templates ─────────────────────────────────────────────────────────
    def list_templates(self):
        return list(self.cn.execute(
            "SELECT * FROM templates ORDER BY builtin DESC, name"))

    def save_template(self, name, content):
        tid = str(uuid.uuid4())[:8]
        self.cn.execute(
            "INSERT INTO templates(id, name, content, builtin) VALUES(?,?,?,0)",
            (tid, name, content))
        self.cn.commit()

    # ── stats ─────────────────────────────────────────────────────────────
    def stats(self):
        c = self.cn.execute(
            "SELECT COUNT(*) AS n, COALESCE(SUM(word_count),0) AS w, "
            "COALESCE(SUM(LENGTH(content)),0) AS ch FROM notes").fetchone()
        return {"notes": c["n"], "words": c["w"], "chars": c["ch"]}


# ═══════════════════════════════════════════════════════════════════════════════
#  Crypto for locked notes
# ═══════════════════════════════════════════════════════════════════════════════
class Crypto:
    """Fernet (AES-128 CBC + HMAC-SHA256) with PBKDF2HMAC key derivation."""
    SALT_KEY = "crypto.salt"
    VERIFIER_KEY = "crypto.verifier"

    def __init__(self, db: DB):
        self.db   = db
        self._key = None  # derived Fernet key cached during session

    @property
    def available(self) -> bool:
        return HAS_CRYPTO

    @property
    def is_unlocked(self) -> bool:
        return self._key is not None

    def lock_session(self):
        self._key = None

    def _ensure_salt(self) -> bytes:
        salt_b64 = self.db.get_setting(self.SALT_KEY)
        if salt_b64:
            return base64.b64decode(salt_b64)
        salt = os.urandom(16)
        self.db.set_setting(self.SALT_KEY, base64.b64encode(salt).decode())
        return salt

    def _derive(self, password: str) -> bytes:
        salt = self._ensure_salt()
        kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32,
                         salt=salt, iterations=200_000)
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))

    def has_password(self) -> bool:
        return bool(self.db.get_setting(self.VERIFIER_KEY))

    def set_password(self, password: str):
        if not HAS_CRYPTO:
            raise RuntimeError("cryptography library not installed")
        key = self._derive(password)
        f = Fernet(key)
        token = f.encrypt(b"NYXUS-NOTEPAD-VERIFIER")
        self.db.set_setting(self.VERIFIER_KEY, token.decode())
        self._key = key

    def verify_and_unlock(self, password: str) -> bool:
        if not HAS_CRYPTO: return False
        token = self.db.get_setting(self.VERIFIER_KEY)
        if not token: return False
        key = self._derive(password)
        try:
            Fernet(key).decrypt(token.encode())
            self._key = key
            return True
        except InvalidToken:
            return False

    def encrypt(self, plaintext: str) -> bytes:
        if not self._key: raise RuntimeError("locked — unlock first")
        return Fernet(self._key).encrypt(plaintext.encode())

    def decrypt(self, blob: bytes) -> str:
        if not self._key: raise RuntimeError("locked — unlock first")
        return Fernet(self._key).decrypt(blob).decode()


# ═══════════════════════════════════════════════════════════════════════════════
#  Custom hand-drawn widgets
# ═══════════════════════════════════════════════════════════════════════════════
class SketchButton(Gtk.DrawingArea):
    """Hand-drawn pushbutton with sketchy outline."""
    __gsignals__ = {"clicked": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, label, *, width=88, height=32, color=NEON_PINK,
                 icon_draw=None, tooltip=None, primary=False):
        super().__init__()
        self.label    = label
        self.color    = color
        self.primary  = primary
        self.icon_draw = icon_draw
        self._hover   = False
        self._press   = False
        self._enabled = True
        self.set_size_request(width, height)
        try:
            self.set_content_width(width)
            self.set_content_height(height)
        except Exception: pass
        self.set_draw_func(self._draw)
        if tooltip: self.set_tooltip_text(tooltip)

        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("pressed",  self._on_press)
        gc.connect("released", self._on_release)
        self.add_controller(gc)
        mc = Gtk.EventControllerMotion()
        mc.connect("enter", lambda *a: (setattr(self, "_hover", True),
                                        self.queue_draw()))
        mc.connect("leave", lambda *a: (setattr(self, "_hover", False),
                                        setattr(self, "_press", False),
                                        self.queue_draw()))
        self.add_controller(mc)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

    def set_enabled(self, on):
        self._enabled = on; self.queue_draw()

    def set_label(self, label):
        self.label = label; self.queue_draw()

    def _on_press(self, *a):
        if not self._enabled: return
        self._press = True; self.queue_draw()

    def _on_release(self, *a):
        if not self._enabled: return
        was = self._press
        self._press = False; self.queue_draw()
        if was: self.emit("clicked")

    def _draw(self, area, cr, w, h, _):
        try:
            self._draw_inner(cr, w, h)
        except Exception:
            log("SketchButton " + traceback.format_exc())

    def _draw_inner(self, cr, w, h):
        col = self.color
        alpha_bg = 0.30 if self.primary else 0.12
        if self._press:    alpha_bg += 0.25
        elif self._hover:  alpha_bg += 0.12
        if not self._enabled: alpha_bg = 0.06

        # body
        cr.set_source_rgba(*col, alpha_bg)
        _rounded_path(cr, 1.5, 1.5, w - 3, h - 3, 6)
        cr.fill()
        # sketchy outline
        cr.set_source_rgba(*col, 0.95 if self._enabled else 0.30)
        cr.set_line_width(1.6)
        sketch_rect(cr, 2, 2, w - 4, h - 4, jitter=0.6,
                    key=("btn", id(self)))

        x_inner = 12
        if self.icon_draw:
            self.icon_draw(cr, x_inner, h/2 - 8, 16)
            x_inner += 22

        # label
        layout = PangoCairo.create_layout(cr)
        d = Pango.FontDescription()
        d.set_family("Caveat")
        d.set_size(int(15 * Pango.SCALE))
        d.set_weight(Pango.Weight.BOLD)
        layout.set_font_description(d)
        layout.set_text(self.label, -1)
        tw, th = layout.get_pixel_size()
        cr.set_source_rgba(*col, 1.0 if self._enabled else 0.40)
        if self.icon_draw:
            cr.move_to(x_inner, (h - th) / 2)
        else:
            cr.move_to((w - tw) / 2, (h - th) / 2)
        PangoCairo.show_layout(cr, layout)


class SketchToggle(SketchButton):
    """Toggle variant (state retained between clicks)."""
    def __init__(self, *args, active=False, **kw):
        super().__init__(*args, **kw)
        self.active = active

    def set_active(self, on):
        self.active = on; self.queue_draw()

    def _on_release(self, *a):
        if not self._enabled: return
        was = self._press
        self._press = False
        if was:
            self.active = not self.active
            self.emit("clicked")
        self.queue_draw()

    def _draw_inner(self, cr, w, h):
        # background extra-bright when active
        if self.active:
            cr.set_source_rgba(*self.color, 0.42)
            _rounded_path(cr, 1.5, 1.5, w - 3, h - 3, 6)
            cr.fill()
        super()._draw_inner(cr, w, h)
        if self.active:
            cr.set_source_rgba(*self.color, 1.0)
            cr.set_line_width(2.0)
            sketch_rect(cr, 3, 3, w - 6, h - 6, jitter=0.5,
                        key=("toggle", id(self), "out"))


class SketchSeparator(Gtk.DrawingArea):
    def __init__(self, vertical=False, length=200, color=None):
        super().__init__()
        self.vertical = vertical
        self.color    = color or INK_FAINT
        if vertical:
            self.set_size_request(2, length)
        else:
            self.set_size_request(length, 2)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr, w, h, _):
        cr.set_source_rgba(*self.color, 0.55)
        cr.set_line_width(1.2)
        if self.vertical:
            sketch_line(cr, w/2, 2, w/2, h - 2, jitter=0.5,
                        key=("sepV", id(self)), segments=int(h/14))
        else:
            sketch_line(cr, 2, h/2, w - 2, h/2, jitter=0.5,
                        key=("sepH", id(self)), segments=int(w/14))


class SketchPanel(Gtk.Box):
    """Box with hand-drawn border drawn behind via an Overlay+DrawingArea."""
    def __init__(self, *, color=ACCENT_PURP, fill=None, padding=12,
                 jitter=0.6, orientation=Gtk.Orientation.VERTICAL):
        super().__init__(orientation=orientation, spacing=0)
        self._border_color = color
        self._fill         = fill
        self._jitter       = jitter
        self.set_margin_start(padding); self.set_margin_end(padding)
        self.set_margin_top(padding);   self.set_margin_bottom(padding)
        # We can't paint behind a Box natively, so we paint inside a snapshot.
        # For simplicity, use a CSS class for fill, and the border is omitted
        # for normal panels — sketch panels are used in the main canvas.

    # Note: For real hand-drawn panel borders we use SketchCanvas inside.


class SketchSearchEntry(Gtk.Box):
    """Hand-drawn search box (custom-painted around a real Gtk.Entry)."""
    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, (str,))}

    def __init__(self, *, placeholder="search…", color=NEON_PINK):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.color = color
        self.set_size_request(220, 32)
        # background DrawingArea
        self.bg = Gtk.DrawingArea()
        self.bg.set_hexpand(True); self.bg.set_vexpand(True)
        self.bg.set_draw_func(self._draw_bg)
        # entry placed in an Overlay so the bg sits behind
        ov = Gtk.Overlay()
        ov.set_hexpand(True); ov.set_vexpand(True)
        ov.set_child(self.bg)
        entry = Gtk.Entry()
        entry.set_placeholder_text(placeholder)
        entry.set_has_frame(False)
        entry.set_margin_start(34); entry.set_margin_end(8)
        entry.set_margin_top(2);    entry.set_margin_bottom(2)
        entry.add_css_class("nyxus-entry")
        entry.connect("changed",
                      lambda e: self.emit("changed", e.get_text()))
        ov.add_overlay(entry)
        self.append(ov)
        self.entry = entry

    def get_text(self): return self.entry.get_text()
    def set_text(self, t): self.entry.set_text(t)

    def _draw_bg(self, area, cr, w, h, _):
        cr.set_source_rgba(*self.color, 0.06)
        _rounded_path(cr, 2, 2, w - 4, h - 4, 6); cr.fill()
        cr.set_source_rgba(*self.color, 0.55)
        cr.set_line_width(1.4)
        sketch_rect(cr, 3, 3, w - 6, h - 6, jitter=0.6,
                    key=("search", id(self)))
        # magnifier icon
        cr.set_source_rgba(*self.color, 0.85)
        cr.set_line_width(1.8)
        cr.arc(15, h/2 - 1, 5.5, 0, math.pi*2); cr.stroke()
        cr.move_to(19, h/2 + 3); cr.line_to(24, h/2 + 8); cr.stroke()


# ═══════════════════════════════════════════════════════════════════════════════
#  Sidebar note card (hand-drawn)
# ═══════════════════════════════════════════════════════════════════════════════
class NoteCard(Gtk.DrawingArea):
    """Single note row in the sidebar (ListBox child)."""
    CARD_H = 92

    def __init__(self, note, tags, *, on_click, on_context):
        super().__init__()
        self.note = note
        self.tags = tags
        self._sel = False
        self._hover = False
        self.set_size_request(-1, self.CARD_H)
        try: self.set_content_height(self.CARD_H)
        except Exception: pass
        self.set_hexpand(True)
        self.set_draw_func(self._draw)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        self._on_click = on_click
        self._on_context = on_context
        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("released", lambda *a: on_click(note["id"]))
        self.add_controller(gc)
        gc2 = Gtk.GestureClick(); gc2.set_button(3)
        gc2.connect("released",
                    lambda g, n, x, y: on_context(note["id"], x, y))
        self.add_controller(gc2)
        mc = Gtk.EventControllerMotion()
        mc.connect("enter", lambda *a: (setattr(self,"_hover",True), self.queue_draw()))
        mc.connect("leave", lambda *a: (setattr(self,"_hover",False), self.queue_draw()))
        self.add_controller(mc)

    def set_selected(self, sel):
        if sel != self._sel:
            self._sel = sel; self.queue_draw()

    def _draw(self, area, cr, w, h, _):
        try:
            self._draw_inner(cr, w, h)
        except Exception:
            log("NoteCard " + traceback.format_exc())

    def _draw_inner(self, cr, w, h):
        n = self.note
        c = NOTE_COLOR_BY_KEY.get(n["color"] or "cloud", NOTE_COLOR_BY_KEY["cloud"])
        ckey = ("card", n["id"])

        # background
        if self._sel:
            cr.set_source_rgba(*c["rgb"], 0.18)
        elif self._hover:
            cr.set_source_rgba(1, 1, 1, 0.05)
        else:
            cr.set_source_rgba(0, 0, 0, 0.0)
        _rounded_path(cr, 6, 4, w - 12, h - 8, 6); cr.fill()

        # left colour bar (always)
        cr.set_source_rgba(*c["rgb"], 0.85)
        sketch_filled_rect(cr, 8, 8, 4, h - 16,
                           fill=(*c["rgb"], 0.9),
                           stroke=(*c["rgb"], 0.95),
                           jitter=0.4, radius=2,
                           key=(ckey, "bar"))

        # outline if selected
        if self._sel:
            cr.set_source_rgba(*NEON_PINK, 0.85)
            cr.set_line_width(1.6)
            sketch_rect(cr, 7, 5, w - 14, h - 10, jitter=0.5, key=(ckey, "sel"))

        # title
        title = n["title"] or "(untitled)"
        text_at(cr, 22, 10, title, size=18, bold=True,
                color=INK_BRIGHT, max_w=w - 80)

        # preview body  (first non-empty line of content, or '…')
        preview = ""
        for line in (n["content"] or "").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                preview = line
                break
        if not preview:
            preview = "(empty note)"
        text_at(cr, 22, 36, preview, size=13, color=INK_DIM, alpha=0.85,
                max_w=w - 80, family="Caveat")

        # bottom row: date · word count · tags
        date_str = self._fmt_date(n["modified"] or n["created"])
        wc       = n["word_count"] or 0
        meta = f"{date_str}  ·  {wc} word{'s' if wc != 1 else ''}"
        text_at(cr, 22, h - 26, meta, size=12, color=INK_FAINT, max_w=w - 110)

        if self.tags:
            tx = 22
            ty = h - 26
            # tags shown as little hand-drawn pills on right
            tx_right = w - 16
            for t in self.tags[:3]:
                pill_w = 8 + len(t) * 7
                px = tx_right - pill_w
                if px < 22 + 100: break
                cr.set_source_rgba(*c["rgb"], 0.18)
                _rounded_path(cr, px, h - 26, pill_w, 16, 5); cr.fill()
                cr.set_source_rgba(*c["rgb"], 0.85)
                cr.set_line_width(1.0)
                sketch_rect(cr, px + 0.5, h - 26 + 0.5, pill_w - 1, 15,
                            jitter=0.4, double=False,
                            key=(ckey, "tag", t))
                text_at(cr, px + 4, h - 28, t,
                        size=11, color=c["rgb"], alpha=0.95)
                tx_right = px - 4

        # icons: pin / star / lock — top right
        ix = w - 22; iy = 8
        if n["locked"]:
            sketch_lock(cr, ix - 16, iy, 16, color=ACCENT_GOLD); ix -= 22
        if n["starred"]:
            sketch_star(cr, ix - 16, iy, 16, filled=True, color=ACCENT_GOLD)
            ix -= 22
        if n["pinned"]:
            sketch_pin(cr, ix - 16, iy, 16, color=DANGER_RED)

        # bottom divider (very faint)
        cr.set_source_rgba(*INK_FAINT, 0.20)
        cr.set_line_width(0.8)
        sketch_underline(cr, 14, h - 3, w - 28,
                         jitter=0.4, key=(ckey, "div"))

    @staticmethod
    def _fmt_date(ts):
        if not ts: return ""
        d = datetime.fromtimestamp(ts)
        delta = datetime.now() - d
        if delta < timedelta(minutes=1):  return "just now"
        if delta < timedelta(hours=1):    return f"{int(delta.total_seconds()/60)}m ago"
        if delta < timedelta(days=1):     return f"{int(delta.total_seconds()/3600)}h ago"
        if delta < timedelta(days=7):     return d.strftime("%a %H:%M")
        return d.strftime("%b %d")


# ═══════════════════════════════════════════════════════════════════════════════
#  CSS for chrome
# ═══════════════════════════════════════════════════════════════════════════════
CSS = """
* { font-family: 'Caveat', 'Patrick Hand', cursive; }
window, .nyx-bg {
    background-color: #0a0a12;
    color: #f0eef8;
}
.nyx-sidebar  { background-color: rgba(255,255,255,0.025); }
.nyx-toolbar  { background-color: rgba(10,10,18,0.96); padding: 6px 14px; }
.nyx-statusbar{ background-color: rgba(10,10,18,0.96); padding: 4px 14px;
                border-top: 1px solid rgba(255,255,255,0.05); }

.nyxus-entry {
    background-color: transparent;
    border: none; outline: none; box-shadow: none;
    color: rgba(240,235,250,0.92);
    font-size: 16px; font-family: 'Caveat', cursive;
    caret-color: #ff00ff;
}
.nyxus-entry:focus { outline: none; box-shadow: none; }

.nyx-title-entry {
    background-color: transparent;
    border: none; outline: none; box-shadow: none;
    color: #ffffff;
    font-family: 'Caveat', cursive;
    font-size: 32px; font-weight: bold;
    padding: 12px 20px;
    caret-color: #ff00ff;
}
.nyx-title-entry:focus { outline: none; box-shadow: none; }

.nyx-editor textview, .nyx-editor text {
    background-color: transparent;
    color: rgba(240,235,250,0.95);
    font-family: 'Caveat', 'Patrick Hand', cursive;
    font-size: 18px;
    caret-color: #ff00ff;
    padding: 0 20px;
}
.nyx-editor { background-color: transparent; }

.nyx-mono {
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 13px;
}

scrollbar slider {
    background-color: rgba(255,0,255,0.30);
    border: 1px solid rgba(255,0,255,0.45);
    border-radius: 6px;
    min-width: 8px; min-height: 8px;
}
scrollbar slider:hover { background-color: rgba(255,0,255,0.55); }
scrollbar { background-color: transparent; }

.nyx-headline {
    color: #ff00ff;
    text-shadow: 0 0 12px rgba(255,0,255,0.55);
    font-size: 22px; font-weight: bold;
}
.nyx-meta { color: rgba(240,235,250,0.45); font-size: 13px; }
.nyx-accent { color: #ff00ff; }
.nyx-accent2 { color: #0088ff; }
.nyx-accent3 { color: #39ff14; }

.nyx-dialog-bg {
    background-color: rgba(15,12,28,0.99);
}
.nyx-tag-pill {
    background-color: rgba(139,92,246,0.18);
    color: #c8a8ff;
    border: 1px solid rgba(139,92,246,0.55);
    border-radius: 10px;
    padding: 1px 10px;
    font-size: 13px;
}
.nyx-popover {
    background-color: rgba(15,12,28,0.98);
    color: rgba(240,235,250,0.92);
}
.nyx-cmdpalette entry, .nyx-cmdpalette text {
    background-color: rgba(15,12,28,0.99);
    color: #f0eef8;
    border: 2px solid rgba(255,0,255,0.55);
    border-radius: 8px;
    padding: 12px;
    font-family: 'Caveat', cursive; font-size: 20px;
    caret-color: #ff00ff;
}
.nyx-cmdpalette row {
    background-color: transparent;
    color: rgba(240,235,250,0.85);
    padding: 8px 12px;
    font-family: 'Caveat', cursive; font-size: 17px;
}
.nyx-cmdpalette row:selected {
    background-color: rgba(255,0,255,0.28);
    color: #ffffff;
}
.nyx-cmdpalette listview { background-color: transparent; }

textview text selection { background-color: rgba(255,0,255,0.35); color: #fff; }
"""

# ═══════════════════════════════════════════════════════════════════════════════
#  Editor — rich text via TextTags
# ═══════════════════════════════════════════════════════════════════════════════
class Editor(Gtk.Box):
    """Rich-text editor wrapping a Gtk.TextView with custom tags."""
    def __init__(self, on_change=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add_css_class("nyx-editor")
        self.on_change = on_change
        self._suspend_change = False

        self.buf = Gtk.TextBuffer()
        self._init_tags()
        self.view = Gtk.TextView(buffer=self.buf)
        self.view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.view.set_left_margin(20)
        self.view.set_right_margin(20)
        self.view.set_top_margin(12)
        self.view.set_bottom_margin(60)
        self.view.set_pixels_above_lines(2)
        self.view.set_pixels_below_lines(2)
        self.view.set_pixels_inside_wrap(2)
        self.view.set_accepts_tab(True)
        self.view.set_monospace(False)

        sc = Gtk.ScrolledWindow()
        sc.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sc.set_hexpand(True); sc.set_vexpand(True)
        sc.set_child(self.view)
        self.append(sc)

        self.buf.connect("changed", self._on_buf_changed)

    # ── tag table ─────────────────────────────────────────────────────────
    def _init_tags(self):
        self.buf.create_tag("bold",       weight=Pango.Weight.BOLD)
        self.buf.create_tag("italic",     style=Pango.Style.ITALIC)
        self.buf.create_tag("underline",  underline=Pango.Underline.SINGLE)
        self.buf.create_tag("strike",     strikethrough=True)
        self.buf.create_tag("code",
            family="JetBrains Mono, Fira Code, monospace",
            background="#1a1530", foreground="#ff88ff",
            scale=0.92)
        # Headings
        self.buf.create_tag("h1", weight=Pango.Weight.BOLD,
                            scale=2.2, foreground="#ff00ff",
                            pixels_above_lines=10, pixels_below_lines=4)
        self.buf.create_tag("h2", weight=Pango.Weight.BOLD,
                            scale=1.7, foreground="#ff66ff",
                            pixels_above_lines=8, pixels_below_lines=3)
        self.buf.create_tag("h3", weight=Pango.Weight.BOLD,
                            scale=1.35, foreground="#cc88ff",
                            pixels_above_lines=6, pixels_below_lines=2)
        self.buf.create_tag("h4", weight=Pango.Weight.BOLD,
                            scale=1.18, foreground="#a0a0ff")
        self.buf.create_tag("h5", weight=Pango.Weight.BOLD, scale=1.08)
        self.buf.create_tag("h6", weight=Pango.Weight.BOLD, scale=1.0,
                            foreground="#888")
        self.buf.create_tag("quote",
                            left_margin=40, foreground="#a8c0ff",
                            style=Pango.Style.ITALIC,
                            background="#11111c")
        self.buf.create_tag("code_block",
            family="JetBrains Mono, Fira Code, monospace",
            background="#0e0a18", foreground="#a8ffd0",
            scale=0.95, left_margin=30,
            pixels_above_lines=6, pixels_below_lines=6)
        self.buf.create_tag("link",
            foreground="#39ff14", underline=Pango.Underline.SINGLE)
        self.buf.create_tag("hr", foreground="#444")
        self.buf.create_tag("bullet", indent=20)
        # color tags created on demand

    def _on_buf_changed(self, buf):
        if self._suspend_change: return
        if self.on_change: self.on_change(self.get_text())

    # ── public API ─────────────────────────────────────────────────────────
    def get_text(self):
        s = self.buf.get_start_iter(); e = self.buf.get_end_iter()
        return self.buf.get_text(s, e, True)

    def set_text(self, txt, *, render_markdown=True):
        self._suspend_change = True
        self.buf.set_text(txt or "")
        if render_markdown:
            self._apply_markdown_tags()
        self._suspend_change = False

    def insert_at_cursor(self, txt):
        self.buf.insert_at_cursor(txt)

    def get_selection_bounds(self):
        rv = self.buf.get_selection_bounds()
        if rv: return rv
        return (None, None)

    # ── formatting actions ────────────────────────────────────────────────
    def toggle_tag(self, tag_name):
        s, e = self.buf.get_selection_bounds() or (None, None)
        if s is None:
            # toggle for next typing — wrap empty insertion of a marker word
            return
        tag = self.buf.get_tag_table().lookup(tag_name)
        if tag is None: return
        # determine if the entire selection has this tag
        it = s.copy(); applied = True
        while it.compare(e) < 0:
            if not it.has_tag(tag):
                applied = False; break
            it.forward_char()
        if applied:
            self.buf.remove_tag(tag, s, e)
        else:
            self.buf.apply_tag(tag, s, e)

    def apply_heading(self, level):
        s, e = self._line_bounds()
        # remove other heading tags on this line
        for n in ("h1","h2","h3","h4","h5","h6"):
            self.buf.remove_tag_by_name(n, s, e)
        self.buf.apply_tag_by_name(f"h{level}", s, e)

    def apply_bullet_to_lines(self, marker="• "):
        s, e = self.buf.get_selection_bounds() or (
            self._line_bounds()[0], self._line_bounds()[1])
        # iterate lines
        line_start = s.copy()
        line_start.set_line(s.get_line())
        end_line = e.get_line()
        for ln in range(line_start.get_line(), end_line + 1):
            it = self.buf.get_iter_at_line(ln)
            self.buf.insert(it, marker)

    def apply_numbered(self):
        s, e = self.buf.get_selection_bounds() or (
            self._line_bounds()[0], self._line_bounds()[1])
        sl = s.get_line(); el = e.get_line()
        n = 1
        for ln in range(sl, el + 1):
            it = self.buf.get_iter_at_line(ln)
            self.buf.insert(it, f"{n}. "); n += 1

    def apply_checkbox(self):
        s, e = self.buf.get_selection_bounds() or (
            self._line_bounds()[0], self._line_bounds()[1])
        sl = s.get_line(); el = e.get_line()
        for ln in range(sl, el + 1):
            it = self.buf.get_iter_at_line(ln)
            self.buf.insert(it, "- [ ] ")

    def insert_horizontal_rule(self):
        self.buf.insert_at_cursor("\n────────────────────\n")

    def insert_link(self, url, text=""):
        self.buf.insert_at_cursor(f"[{text or url}]({url})")

    def insert_table(self, rows=2, cols=3):
        header = "| " + " | ".join(f"col{i+1}" for i in range(cols)) + " |\n"
        sep    = "|" + "|".join("------" for _ in range(cols)) + "|\n"
        body   = "\n".join("| " + " | ".join(" " for _ in range(cols)) + " |"
                           for _ in range(rows)) + "\n"
        self.buf.insert_at_cursor(header + sep + body)

    def insert_code_block(self, lang="python"):
        self.buf.insert_at_cursor(f"\n```{lang}\n\n```\n")
        # move cursor inside the block
        cur = self.buf.get_iter_at_mark(self.buf.get_insert())
        cur.backward_chars(5)
        self.buf.place_cursor(cur)

    def _line_bounds(self):
        it = self.buf.get_iter_at_mark(self.buf.get_insert())
        s = it.copy(); s.set_line_offset(0)
        e = it.copy(); e.forward_to_line_end()
        return s, e

    # ── markdown re-render ─────────────────────────────────────────────────
    def _apply_markdown_tags(self):
        """Lightweight inline parse of markdown to colour the buffer."""
        s = self.buf.get_start_iter(); e = self.buf.get_end_iter()
        for n in ("bold","italic","underline","strike","code","link",
                  "h1","h2","h3","h4","h5","h6","code_block","quote"):
            self.buf.remove_tag_by_name(n, s, e)
        text = self.buf.get_text(s, e, True)
        # process line by line for headings, blockquotes, code blocks
        in_code = False
        offset = 0
        for line in text.split("\n"):
            line_len = len(line)
            line_start = self.buf.get_iter_at_offset(offset)
            line_end   = self.buf.get_iter_at_offset(offset + line_len)
            stripped = line.lstrip()
            if in_code:
                if stripped.startswith("```"):
                    in_code = False
                else:
                    self.buf.apply_tag_by_name("code_block",
                                               line_start, line_end)
            else:
                if stripped.startswith("```"):
                    in_code = True
                elif stripped.startswith("# "):
                    self.buf.apply_tag_by_name("h1", line_start, line_end)
                elif stripped.startswith("## "):
                    self.buf.apply_tag_by_name("h2", line_start, line_end)
                elif stripped.startswith("### "):
                    self.buf.apply_tag_by_name("h3", line_start, line_end)
                elif stripped.startswith("#### "):
                    self.buf.apply_tag_by_name("h4", line_start, line_end)
                elif stripped.startswith(">"):
                    self.buf.apply_tag_by_name("quote", line_start, line_end)
            offset += line_len + 1

        # inline: **bold**, *italic*, __under__, ~~strike~~, `code`
        self._apply_inline(text, r"\*\*(.+?)\*\*", "bold", marker_len=2)
        self._apply_inline(text, r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", "italic", 1)
        self._apply_inline(text, r"__([^_]+?)__", "underline", 2)
        self._apply_inline(text, r"~~(.+?)~~", "strike", 2)
        self._apply_inline(text, r"`([^`\n]+?)`", "code", 1)
        self._apply_inline(text, r"\[([^\]]+)\]\(([^)]+)\)", "link", 0)

    def _apply_inline(self, text, pattern, tag, marker_len):
        for m in re.finditer(pattern, text):
            s_off, e_off = m.start(), m.end()
            if marker_len:
                s_off += marker_len; e_off -= marker_len
            si = self.buf.get_iter_at_offset(s_off)
            ei = self.buf.get_iter_at_offset(e_off)
            try:
                self.buf.apply_tag_by_name(tag, si, ei)
            except Exception: pass


# ═══════════════════════════════════════════════════════════════════════════════
#  Export helpers
# ═══════════════════════════════════════════════════════════════════════════════
class Exporter:
    @staticmethod
    def to_markdown(note) -> str:
        return note["content"] or ""

    @staticmethod
    def to_text(note) -> str:
        return re.sub(r"[*_`#>~\[\]()-]+", "", note["content"] or "")

    @staticmethod
    def to_html(note) -> str:
        body_md = note["content"] or ""
        if HAS_MARKDOWN:
            body = _md.markdown(
                body_md,
                extensions=["fenced_code", "tables", "nl2br",
                            "codehilite", "toc", "sane_lists"])
        else:
            body = "<pre>" + html.escape(body_md) + "</pre>"
        title = html.escape(note["title"] or "Untitled")
        return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ font-family: 'Caveat', 'Patrick Hand', cursive;
        background:#0a0a12; color:#f0eef8;
        max-width:780px; margin:40px auto; padding:0 20px; }}
h1,h2,h3 {{ color:#ff00ff; }}
a {{ color:#39ff14; }}
code {{ background:#1a1530; color:#ff88ff;
        padding:2px 5px; border-radius:3px; font-family:monospace; }}
pre {{ background:#0e0a18; color:#a8ffd0;
        padding:12px; border-radius:6px; overflow:auto;
        font-family:monospace; }}
blockquote {{ border-left:3px solid #8b5cf6;
              padding-left:14px; color:#a8c0ff; }}
table {{ border-collapse:collapse; }}
td,th {{ border:1px solid #444; padding:4px 8px; }}
</style></head><body>
<h1>{title}</h1>
{body}
</body></html>"""

    @staticmethod
    def to_pdf(note, out_path: Path):
        if not HAS_REPORTLAB:
            raise RuntimeError("reportlab not installed — cannot export PDF")
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "title", parent=styles["Title"],
            fontSize=22, textColor=HexColor("#ff00ff"),
            spaceAfter=14)
        body_style = ParagraphStyle(
            "body", parent=styles["BodyText"],
            fontName="Helvetica", fontSize=11, leading=15,
            textColor=HexColor("#1a1530"))
        h_style = lambda n: ParagraphStyle(
            f"h{n}", parent=styles[f"Heading{n}"],
            fontSize=20 - n*2, textColor=HexColor("#8b5cf6"),
            spaceBefore=10, spaceAfter=6)
        code_style = ParagraphStyle(
            "code", parent=styles["Code"],
            fontName="Courier", fontSize=9,
            textColor=HexColor("#a8ffd0"),
            backColor=HexColor("#0e0a18"),
            leftIndent=12, rightIndent=12,
            spaceBefore=6, spaceAfter=6, leading=11)

        doc = SimpleDocTemplate(str(out_path), pagesize=LETTER,
                                topMargin=0.7*inch, bottomMargin=0.7*inch,
                                leftMargin=0.8*inch, rightMargin=0.8*inch,
                                title=note["title"] or "Untitled")
        flow = [Paragraph(html.escape(note["title"] or "Untitled"), title_style),
                Spacer(1, 8)]
        in_code = False; code_buf = []
        for line in (note["content"] or "").split("\n"):
            if line.strip().startswith("```"):
                if in_code:
                    flow.append(Preformatted("\n".join(code_buf), code_style))
                    code_buf = []
                in_code = not in_code; continue
            if in_code:
                code_buf.append(line); continue
            stripped = line.strip()
            if stripped.startswith("# "):
                flow.append(Paragraph(html.escape(stripped[2:]), h_style(1)))
            elif stripped.startswith("## "):
                flow.append(Paragraph(html.escape(stripped[3:]), h_style(2)))
            elif stripped.startswith("### "):
                flow.append(Paragraph(html.escape(stripped[4:]), h_style(3)))
            elif stripped.startswith(("- ", "* ")):
                flow.append(Paragraph("• " + html.escape(stripped[2:]),
                                      body_style))
            elif stripped == "":
                flow.append(Spacer(1, 6))
            else:
                # convert simple inline markdown to ReportLab tags
                rl = html.escape(line)
                rl = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", rl)
                rl = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)",
                            r"<i>\1</i>", rl)
                rl = re.sub(r"`([^`]+?)`",
                            r'<font name="Courier" color="#ff66ff">\1</font>',
                            rl)
                flow.append(Paragraph(rl, body_style))
        if in_code and code_buf:
            flow.append(Preformatted("\n".join(code_buf), code_style))
        doc.build(flow)


# ═══════════════════════════════════════════════════════════════════════════════
#  Command palette
# ═══════════════════════════════════════════════════════════════════════════════
class CommandPalette(Gtk.Window):
    def __init__(self, parent, commands):
        super().__init__(title="Command Palette", transient_for=parent,
                         modal=True, decorated=False)
        self.set_default_size(540, 360)
        self.commands = commands
        self.add_css_class("nyx-cmdpalette")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_start(12); outer.set_margin_end(12)
        outer.set_margin_top(12);   outer.set_margin_bottom(12)
        self.set_child(outer)

        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text("Type a command…")
        self.entry.connect("changed", lambda *_: self._refilter())
        self.entry.connect("activate", lambda *_: self._activate_selected())
        outer.append(self.entry)

        self.list = Gtk.ListBox()
        self.list.add_css_class("nyx-cmdpalette")
        self.list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list.connect("row-activated", lambda *_: self._activate_selected())
        sw = Gtk.ScrolledWindow()
        sw.set_min_content_height(280); sw.set_vexpand(True)
        sw.set_child(self.list)
        outer.append(sw)

        self._refilter()

        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._on_key)
        self.add_controller(kc)

    def _refilter(self):
        q = self.entry.get_text().lower().strip()
        # clear
        while True:
            r = self.list.get_row_at_index(0)
            if r is None: break
            self.list.remove(r)
        for label, fn in self.commands:
            if q and q not in label.lower(): continue
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=label, xalign=0)
            lbl.set_margin_start(8); lbl.set_margin_end(8)
            lbl.set_margin_top(4);   lbl.set_margin_bottom(4)
            row.set_child(lbl)
            row.fn = fn
            self.list.append(row)
        first = self.list.get_row_at_index(0)
        if first: self.list.select_row(first)

    def _activate_selected(self):
        row = self.list.get_selected_row()
        if row is None: return
        fn = getattr(row, "fn", None)
        self.close()
        if fn: GLib.idle_add(fn)

    def _on_key(self, ctl, keyval, kc, st):
        if keyval == Gdk.KEY_Escape:
            self.close(); return True
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            sel = self.list.get_selected_row()
            idx = sel.get_index() if sel else 0
            new = idx + (1 if keyval == Gdk.KEY_Down else -1)
            row = self.list.get_row_at_index(new)
            if row: self.list.select_row(row)
            return True
        return False


# ═══════════════════════════════════════════════════════════════════════════════
#  Find & replace bar
# ═══════════════════════════════════════════════════════════════════════════════
class FindBar(Gtk.Box):
    def __init__(self, editor: Editor):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.editor = editor
        self.set_margin_start(12); self.set_margin_end(12)
        self.set_margin_top(6);    self.set_margin_bottom(6)

        self.find_entry = Gtk.Entry()
        self.find_entry.set_placeholder_text("Find…")
        self.find_entry.add_css_class("nyxus-entry")
        self.find_entry.set_hexpand(True)
        self.find_entry.connect("changed", lambda *_: self._highlight())
        self.find_entry.connect("activate", lambda *_: self.find_next())
        self.append(self.find_entry)

        self.replace_entry = Gtk.Entry()
        self.replace_entry.set_placeholder_text("Replace…")
        self.replace_entry.add_css_class("nyxus-entry")
        self.replace_entry.set_hexpand(True)
        self.append(self.replace_entry)

        for label, fn in (("Prev", self.find_prev),
                          ("Next", self.find_next),
                          ("Replace", self.replace_one),
                          ("Replace All", self.replace_all),
                          ("Close", self.close)):
            b = SketchButton(label, width=92, color=NEON_PINK)
            b.connect("clicked", lambda _b, f=fn: f())
            self.append(b)

        self._tag = editor.buf.get_tag_table().lookup("find_match")
        if self._tag is None:
            self._tag = editor.buf.create_tag("find_match",
                background="#ff00ff",
                foreground="#000000")
        self._regex = False

    def open(self):
        self.set_visible(True)
        self.find_entry.grab_focus()

    def close(self):
        self.set_visible(False)
        self._clear_highlights()

    def _clear_highlights(self):
        s = self.editor.buf.get_start_iter()
        e = self.editor.buf.get_end_iter()
        self.editor.buf.remove_tag(self._tag, s, e)

    def _highlight(self):
        self._clear_highlights()
        q = self.find_entry.get_text()
        if not q: return
        text = self.editor.get_text()
        try:
            for m in re.finditer(re.escape(q), text, re.IGNORECASE):
                si = self.editor.buf.get_iter_at_offset(m.start())
                ei = self.editor.buf.get_iter_at_offset(m.end())
                self.editor.buf.apply_tag(self._tag, si, ei)
        except Exception: pass

    def find_next(self):
        q = self.find_entry.get_text()
        if not q: return
        cur = self.editor.buf.get_iter_at_mark(self.editor.buf.get_insert())
        m = cur.forward_search(q, Gtk.TextSearchFlags.CASE_INSENSITIVE, None)
        if not m:
            s = self.editor.buf.get_start_iter()
            m = s.forward_search(q, Gtk.TextSearchFlags.CASE_INSENSITIVE, None)
        if m:
            self.editor.buf.select_range(m[0], m[1])
            self.editor.view.scroll_to_iter(m[0], 0.1, False, 0, 0)

    def find_prev(self):
        q = self.find_entry.get_text()
        if not q: return
        cur = self.editor.buf.get_iter_at_mark(self.editor.buf.get_insert())
        m = cur.backward_search(q, Gtk.TextSearchFlags.CASE_INSENSITIVE, None)
        if m:
            self.editor.buf.select_range(m[0], m[1])
            self.editor.view.scroll_to_iter(m[0], 0.1, False, 0, 0)

    def replace_one(self):
        q = self.find_entry.get_text()
        rep = self.replace_entry.get_text()
        if not q: return
        s, e = self.editor.buf.get_selection_bounds() or (None, None)
        if s and e and self.editor.buf.get_text(s, e, True).lower() == q.lower():
            self.editor.buf.delete(s, e)
            self.editor.buf.insert_at_cursor(rep)
        self.find_next()

    def replace_all(self):
        q = self.find_entry.get_text()
        rep = self.replace_entry.get_text()
        if not q: return
        text = self.editor.get_text()
        new = re.sub(re.escape(q), rep, text, flags=re.IGNORECASE)
        if new != text:
            self.editor.set_text(new)


# ═══════════════════════════════════════════════════════════════════════════════
#  Main window
# ═══════════════════════════════════════════════════════════════════════════════
class NotepadWindow(Gtk.ApplicationWindow):
    AUTOSAVE_MS = 30_000

    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME)
        self.set_default_size(WIN_W, WIN_H)
        self.db = DB()
        self.crypto = Crypto(self.db)
        self.current_id = None
        self._dirty = False
        self._sort = "modified"
        self._search = ""
        self._tag_filter = None
        self._color_filter = None
        self._notebook_filter = None
        self._df_mode = False  # distraction-free
        self._tw_mode = False  # typewriter
        self._note_cards = {}
        self._build_css()
        self._build_layout()
        self._wire_shortcuts()
        self._refresh_sidebar()
        # Autosave timer
        GLib.timeout_add(self.AUTOSAVE_MS, self._autosave_tick)
        # Open most-recent or create
        notes = self.db.list_notes()
        if notes:
            self._open_note(notes[0]["id"])
        else:
            self._new_note()

    # ── CSS ────────────────────────────────────────────────────────────────
    def _build_css(self):
        prov = Gtk.CssProvider()
        try: prov.load_from_string(CSS)
        except AttributeError: prov.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # ── Layout ────────────────────────────────────────────────────────────
    def _build_layout(self):
        self.add_css_class("nyx-bg")

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(root)

        # Top toolbar
        self.toolbar = self._make_toolbar()
        root.append(self.toolbar)

        # Body — paned (sidebar | editor)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(300)
        paned.set_wide_handle(True)
        paned.set_hexpand(True); paned.set_vexpand(True)
        root.append(paned)

        # ── Sidebar ────────────────────────────────────────────────────────
        self.sidebar = self._make_sidebar()
        paned.set_start_child(self.sidebar)

        # ── Editor area ────────────────────────────────────────────────────
        editor_area = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        editor_area.add_css_class("nyx-bg")

        # Title bar
        self.title_entry = Gtk.Entry()
        self.title_entry.set_placeholder_text("Untitled note…")
        self.title_entry.add_css_class("nyx-title-entry")
        self.title_entry.connect("changed", self._on_title_changed)
        editor_area.append(self.title_entry)

        # Tags row
        self.tags_row = self._make_tags_row()
        editor_area.append(self.tags_row)

        # Format toolbar
        self.format_bar = self._make_format_bar()
        editor_area.append(self.format_bar)

        # Editor
        self.editor = Editor(on_change=self._on_editor_change)
        editor_area.append(self.editor)

        # Find bar
        self.find_bar = FindBar(self.editor)
        self.find_bar.set_visible(False)
        editor_area.append(self.find_bar)

        paned.set_end_child(editor_area)
        self.paned = paned

        # Status bar
        self.status_bar = self._make_status_bar()
        root.append(self.status_bar)

    def _make_toolbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.add_css_class("nyx-toolbar")

        # Title / logo
        logo = Gtk.Label(label="📓 NYXUS Notepad")
        logo.add_css_class("nyx-headline")
        bar.append(logo)

        bar.append(SketchSeparator(vertical=True, length=24, color=NEON_PINK))

        # New note button
        b_new = SketchButton("＋ New", width=92, color=NEON_GREEN, primary=True,
                             tooltip="New note (Ctrl+N)")
        b_new.connect("clicked", lambda _b: self._new_note())
        bar.append(b_new)

        b_save = SketchButton("Save", width=78, color=NEON_BLUE,
                              tooltip="Save (Ctrl+S)")
        b_save.connect("clicked", lambda _b: self._save_now())
        bar.append(b_save)

        b_dup = SketchButton("Duplicate", width=104, color=ACCENT_PURP,
                             tooltip="Duplicate")
        b_dup.connect("clicked", lambda _b: self._duplicate_current())
        bar.append(b_dup)

        b_lock = SketchButton("Lock", width=78, color=ACCENT_GOLD,
                              tooltip="Lock note (Ctrl+L)")
        b_lock.connect("clicked", lambda _b: self._toggle_lock())
        bar.append(b_lock); self.btn_lock = b_lock

        b_pin = SketchToggle("Pin", width=68, color=DANGER_RED,
                             tooltip="Pin to top")
        b_pin.connect("clicked", lambda _b: self._toggle_pin())
        bar.append(b_pin); self.btn_pin = b_pin

        b_star = SketchToggle("★ Star", width=86, color=ACCENT_GOLD,
                              tooltip="Star this note")
        b_star.connect("clicked", lambda _b: self._toggle_star())
        bar.append(b_star); self.btn_star = b_star

        # spacer
        sp = Gtk.Box(); sp.set_hexpand(True); bar.append(sp)

        # Templates / Export / Settings / Cmd palette
        b_tpl = SketchButton("Templates", width=110, color=NEON_PINK)
        b_tpl.connect("clicked", lambda _b: self._show_templates())
        bar.append(b_tpl)

        b_exp = SketchButton("Export", width=88, color=NEON_PINK,
                             tooltip="Export (Ctrl+E)")
        b_exp.connect("clicked", lambda _b: self._show_export())
        bar.append(b_exp)

        b_cmd = SketchButton("⌘ Cmd", width=78, color=NEON_PINK,
                             tooltip="Command palette (Ctrl+Shift+P)")
        b_cmd.connect("clicked", lambda _b: self._show_command_palette())
        bar.append(b_cmd)

        b_set = SketchButton("⚙", width=42, color=INK_DIM,
                             tooltip="Settings (Ctrl+,)")
        b_set.connect("clicked", lambda _b: self._show_settings())
        bar.append(b_set)

        b_full = SketchButton("⛶", width=42, color=INK_DIM,
                              tooltip="Distraction-free mode (Ctrl+Shift+F)")
        b_full.connect("clicked", lambda _b: self._toggle_distraction_free())
        bar.append(b_full)

        return bar

    def _make_format_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        bar.set_margin_start(20); bar.set_margin_end(20)
        bar.set_margin_top(4);    bar.set_margin_bottom(4)

        def addbtn(label, fn, *, color=NEON_PINK, w=44, tip=None):
            b = SketchButton(label, width=w, height=28, color=color,
                             tooltip=tip)
            b.connect("clicked", lambda _b: fn())
            bar.append(b); return b

        addbtn("B", lambda: self.editor.toggle_tag("bold"),
               color=NEON_PINK, tip="Bold (Ctrl+B)")
        addbtn("I", lambda: self.editor.toggle_tag("italic"),
               color=NEON_PINK, tip="Italic (Ctrl+I)")
        addbtn("U", lambda: self.editor.toggle_tag("underline"),
               color=NEON_PINK, tip="Underline (Ctrl+U)")
        addbtn("S̶", lambda: self.editor.toggle_tag("strike"),
               color=NEON_PINK, tip="Strikethrough")
        addbtn("`</>", lambda: self.editor.toggle_tag("code"),
               color=NEON_GREEN, w=58, tip="Inline code")
        bar.append(SketchSeparator(vertical=True, length=22, color=INK_FAINT))

        addbtn("H1", lambda: self.editor.apply_heading(1), color=NEON_BLUE)
        addbtn("H2", lambda: self.editor.apply_heading(2), color=NEON_BLUE)
        addbtn("H3", lambda: self.editor.apply_heading(3), color=NEON_BLUE)
        addbtn("H4", lambda: self.editor.apply_heading(4), color=NEON_BLUE)
        bar.append(SketchSeparator(vertical=True, length=22, color=INK_FAINT))

        addbtn("•", lambda: self.editor.apply_bullet_to_lines(),
               color=ACCENT_PURP, tip="Bullet list")
        addbtn("1.", lambda: self.editor.apply_numbered(),
               color=ACCENT_PURP, tip="Numbered list")
        addbtn("☐", lambda: self.editor.apply_checkbox(),
               color=ACCENT_PURP, tip="Checkbox list")
        addbtn(">", lambda: self._insert_quote(),
               color=ACCENT_PURP, tip="Block quote")
        addbtn("⎯", lambda: self.editor.insert_horizontal_rule(),
               color=ACCENT_PURP, tip="Horizontal rule")
        bar.append(SketchSeparator(vertical=True, length=22, color=INK_FAINT))

        addbtn("⛓ Link", lambda: self._insert_link(),
               color=NEON_GREEN, w=72, tip="Insert link (Ctrl+K)")
        addbtn("▦ Tbl", lambda: self.editor.insert_table(),
               color=NEON_GREEN, w=64, tip="Insert table")
        addbtn("⊞ Code", lambda: self.editor.insert_code_block(),
               color=NEON_GREEN, w=78, tip="Code block")

        bar.append(SketchSeparator(vertical=True, length=22, color=INK_FAINT))

        # Color picker swatches
        for c in NOTE_COLORS:
            sw = self._make_swatch(c)
            bar.append(sw)

        # Find button on the right
        sp = Gtk.Box(); sp.set_hexpand(True); bar.append(sp)
        addbtn("🔍 Find", lambda: self.find_bar.open(),
               color=NEON_PINK, w=86, tip="Find & Replace (Ctrl+F)")
        return bar

    def _make_swatch(self, color):
        da = Gtk.DrawingArea()
        da.set_size_request(22, 22)
        da.set_tooltip_text(color["name"])
        try: da.set_content_width(22); da.set_content_height(22)
        except Exception: pass
        rgb = color["rgb"]
        def _draw(area, cr, w, h, _):
            cr.set_source_rgb(*rgb)
            cr.arc(w/2, h/2, w/2 - 3, 0, math.pi*2); cr.fill()
            sel = self.current_id and self._cur_color() == color["key"]
            cr.set_source_rgba(0, 0, 0, 0.85 if sel else 0.30)
            cr.set_line_width(1.6 if sel else 1.0)
            cr.arc(w/2, h/2, w/2 - 3, 0, math.pi*2); cr.stroke()
        da.set_draw_func(_draw)
        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("released", lambda *a: self._set_color(color["key"]))
        da.add_controller(gc)
        da.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        self._note_cards.setdefault("_swatches", []).append((color["key"], da))
        return da

    def _make_tags_row(self):
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        box.set_margin_start(20); box.set_margin_end(20)
        box.set_margin_top(2); box.set_margin_bottom(4)
        lbl = Gtk.Label(label="🏷"); lbl.add_css_class("nyx-meta")
        box.append(lbl)
        self.tags_pills = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                  spacing=4)
        box.append(self.tags_pills)
        self.tag_entry = Gtk.Entry()
        self.tag_entry.set_placeholder_text("add tag, press Enter")
        self.tag_entry.add_css_class("nyxus-entry")
        self.tag_entry.set_size_request(180, 28)
        self.tag_entry.connect("activate", self._on_tag_added)
        box.append(self.tag_entry)
        return box

    def _make_sidebar(self):
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        col.add_css_class("nyx-sidebar")
        col.set_size_request(280, -1)

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        head.set_margin_start(12); head.set_margin_end(12)
        head.set_margin_top(10); head.set_margin_bottom(6)
        h = Gtk.Label(label="my notes", xalign=0)
        h.add_css_class("nyx-headline"); head.append(h)
        sp = Gtk.Box(); sp.set_hexpand(True); head.append(sp)
        col.append(head)

        # search
        sb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sb.set_margin_start(10); sb.set_margin_end(10); sb.set_margin_bottom(4)
        self.search = SketchSearchEntry(placeholder="search notes…")
        self.search.connect("changed", self._on_search)
        sb.append(self.search)
        col.append(sb)

        # filter row (sort dropdown + tag filter)
        fr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        fr.set_margin_start(10); fr.set_margin_end(10); fr.set_margin_bottom(6)

        sort_btn = SketchButton("⇅ Sort", width=86, height=26, color=NEON_BLUE,
                                tooltip="Sort notes")
        sort_btn.connect("clicked", lambda _b: self._show_sort_menu(sort_btn))
        fr.append(sort_btn); self.sort_btn = sort_btn

        filt_btn = SketchButton("⛛ Filter", width=92, height=26, color=NEON_BLUE,
                                tooltip="Filter notes")
        filt_btn.connect("clicked", lambda _b: self._show_filter_menu(filt_btn))
        fr.append(filt_btn)

        sp2 = Gtk.Box(); sp2.set_hexpand(True); fr.append(sp2)

        self.count_lbl = Gtk.Label(label="0", xalign=1.0)
        self.count_lbl.add_css_class("nyx-meta")
        fr.append(self.count_lbl)
        col.append(fr)

        col.append(SketchSeparator(length=240, color=INK_FAINT))

        # list of notes
        self.notes_list = Gtk.ListBox()
        self.notes_list.add_css_class("nyx-bg")
        self.notes_list.set_selection_mode(Gtk.SelectionMode.NONE)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_hexpand(True); sw.set_vexpand(True)
        sw.set_child(self.notes_list)
        col.append(sw)

        return col

    def _make_status_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        bar.add_css_class("nyx-statusbar")
        for nm in ("words", "chars", "lines", "reading", "saved"):
            lbl = Gtk.Label(label="—"); lbl.add_css_class("nyx-meta")
            setattr(self, f"sb_{nm}", lbl); bar.append(lbl)
            if nm != "saved":
                bar.append(SketchSeparator(vertical=True, length=14, color=INK_FAINT))
        sp = Gtk.Box(); sp.set_hexpand(True); bar.append(sp)
        # right side: lock / autosave indicator
        self.sb_state = Gtk.Label(label=""); self.sb_state.add_css_class("nyx-meta")
        bar.append(self.sb_state)
        return bar

    # ── Shortcuts ─────────────────────────────────────────────────────────
    def _wire_shortcuts(self):
        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._on_key_pressed)
        self.add_controller(kc)

    def _on_key_pressed(self, ctl, kv, kc, st):
        ctrl  = bool(st & Gdk.ModifierType.CONTROL_MASK)
        shift = bool(st & Gdk.ModifierType.SHIFT_MASK)
        if ctrl and kv == Gdk.KEY_n: self._new_note(); return True
        if ctrl and kv == Gdk.KEY_s: self._save_now(); return True
        if ctrl and kv == Gdk.KEY_b: self.editor.toggle_tag("bold"); return True
        if ctrl and kv == Gdk.KEY_i: self.editor.toggle_tag("italic"); return True
        if ctrl and kv == Gdk.KEY_u: self.editor.toggle_tag("underline"); return True
        if ctrl and kv == Gdk.KEY_f: self.find_bar.open(); return True
        if ctrl and kv == Gdk.KEY_h: self.find_bar.open(); return True
        if ctrl and kv == Gdk.KEY_l: self._toggle_lock(); return True
        if ctrl and kv == Gdk.KEY_e: self._show_export(); return True
        if ctrl and kv == Gdk.KEY_d: self._duplicate_current(); return True
        if ctrl and kv == Gdk.KEY_k: self._insert_link(); return True
        if ctrl and kv == Gdk.KEY_comma: self._show_settings(); return True
        if ctrl and shift and kv == Gdk.KEY_p:
            self._show_command_palette(); return True
        if ctrl and shift and kv == Gdk.KEY_f:
            self._toggle_distraction_free(); return True
        if kv == Gdk.KEY_Escape and self.find_bar.get_visible():
            self.find_bar.close(); return True
        return False

    # ── Note operations ───────────────────────────────────────────────────
    def _new_note(self):
        nid = self.db.create_note(title="", content="")
        self._open_note(nid)
        self._refresh_sidebar()
        self.title_entry.grab_focus()

    def _open_note(self, nid):
        # Save current first
        if self.current_id and self._dirty:
            self._save_now()
        n = self.db.get_note(nid)
        if not n: return
        # If locked, prompt to unlock
        if n["locked"]:
            if not self.crypto.is_unlocked:
                if not self._prompt_unlock(): return
            try:
                content = self.crypto.decrypt(n["locked_blob"])
            except Exception:
                self._toast("Failed to decrypt note"); return
        else:
            content = n["content"]
        self.current_id = nid
        self._suspend_ui = True
        self.title_entry.set_text(n["title"] or "")
        self.editor.set_text(content, render_markdown=True)
        self._suspend_ui = False
        self.btn_pin.set_active(bool(n["pinned"]))
        self.btn_star.set_active(bool(n["starred"]))
        self.btn_lock.set_label("Unlock" if n["locked"] else "Lock")
        self._refresh_tag_pills()
        self._refresh_status()
        self._dirty = False
        # update selection in sidebar
        for cid, card in self._note_cards.items():
            if isinstance(card, NoteCard):
                card.set_selected(cid == nid)

    def _on_title_changed(self, entry):
        if getattr(self, "_suspend_ui", False): return
        self._dirty = True

    def _on_editor_change(self, _txt):
        if getattr(self, "_suspend_ui", False): return
        self._dirty = True
        self._refresh_status()
        # re-apply markdown styling on new content (rate-limited)
        if not getattr(self, "_md_pending", False):
            self._md_pending = True
            GLib.timeout_add(400, self._reapply_md)

    def _reapply_md(self):
        self._md_pending = False
        try: self.editor._apply_markdown_tags()
        except Exception: pass
        return False

    def _save_now(self):
        if not self.current_id: return
        title  = self.title_entry.get_text()
        content = self.editor.get_text()
        n = self.db.get_note(self.current_id)
        if n and n["locked"] and self.crypto.is_unlocked:
            blob = self.crypto.encrypt(content)
            self.db.update_note(self.current_id, title=title,
                                content="", locked_blob=blob)
        else:
            self.db.update_note(self.current_id, title=title,
                                content=content)
        self.db.add_draft(self.current_id, content)
        self._dirty = False
        self.sb_saved.set_label("✓ saved " + datetime.now().strftime("%H:%M"))
        self._refresh_sidebar(preserve_open=True)

    def _autosave_tick(self):
        if self.current_id and self._dirty:
            self._save_now()
        return True

    def _duplicate_current(self):
        if not self.current_id: return
        nid = self.db.duplicate_note(self.current_id)
        if nid: self._open_note(nid); self._refresh_sidebar()

    def _toggle_pin(self):
        if not self.current_id: return
        n = self.db.get_note(self.current_id)
        self.db.update_note(self.current_id, pinned=int(not n["pinned"]))
        self._refresh_sidebar(preserve_open=True)

    def _toggle_star(self):
        if not self.current_id: return
        n = self.db.get_note(self.current_id)
        self.db.update_note(self.current_id, starred=int(not n["starred"]))
        self._refresh_sidebar(preserve_open=True)

    def _set_color(self, color_key):
        if not self.current_id: return
        self.db.update_note(self.current_id, color=color_key)
        self._refresh_sidebar(preserve_open=True)
        # repaint swatches
        for k, w in self._note_cards.get("_swatches", []):
            w.queue_draw()

    def _cur_color(self):
        if not self.current_id: return None
        n = self.db.get_note(self.current_id)
        return n["color"] if n else None

    def _toggle_lock(self):
        if not self.current_id: return
        if not HAS_CRYPTO:
            self._toast("Install python-cryptography to use locked notes")
            return
        n = self.db.get_note(self.current_id)
        if n["locked"]:
            # unlock for this note → store as plaintext
            if not self.crypto.is_unlocked:
                if not self._prompt_unlock(): return
            try:
                content = self.crypto.decrypt(n["locked_blob"])
            except Exception:
                self._toast("Could not decrypt"); return
            self.db.update_note(self.current_id, locked=0,
                                content=content, locked_blob=None)
            self.btn_lock.set_label("Lock")
            self._toast("Note unlocked — stored as plaintext")
        else:
            if not self.crypto.has_password():
                if not self._prompt_set_master(): return
            if not self.crypto.is_unlocked:
                if not self._prompt_unlock(): return
            content = self.editor.get_text()
            blob = self.crypto.encrypt(content)
            self.db.update_note(self.current_id, locked=1, content="",
                                locked_blob=blob)
            self.btn_lock.set_label("Unlock")
            self._toast("Note locked")
        self._refresh_sidebar(preserve_open=True)

    def _prompt_set_master(self) -> bool:
        dlg = Gtk.Dialog(title="Set Master Password",
                         transient_for=self, modal=True)
        dlg.set_default_size(360, -1)
        ca = dlg.get_content_area()
        ca.set_margin_top(14); ca.set_margin_bottom(14)
        ca.set_margin_start(20); ca.set_margin_end(20); ca.set_spacing(8)
        ca.append(Gtk.Label(label="Choose a master password for locked notes.\n"
                                  "It cannot be recovered if forgotten.",
                            xalign=0))
        e1 = Gtk.Entry(); e1.set_visibility(False)
        e1.set_placeholder_text("password"); ca.append(e1)
        e2 = Gtk.Entry(); e2.set_visibility(False)
        e2.set_placeholder_text("confirm"); ca.append(e2)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Set", Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)
        result = {"ok": False}
        def _resp(d, r):
            if r == Gtk.ResponseType.OK:
                p1, p2 = e1.get_text(), e2.get_text()
                if p1 and p1 == p2:
                    self.crypto.set_password(p1); result["ok"] = True
                else:
                    self._toast("Passwords don't match"); return
            d.destroy()
        dlg.connect("response", _resp)
        loop = GLib.MainLoop()
        dlg.connect("destroy", lambda *_: loop.quit())
        dlg.present()
        loop.run()
        return result["ok"]

    def _prompt_unlock(self) -> bool:
        dlg = Gtk.Dialog(title="Unlock Locked Notes",
                         transient_for=self, modal=True)
        dlg.set_default_size(340, -1)
        ca = dlg.get_content_area()
        ca.set_margin_top(14); ca.set_margin_bottom(14)
        ca.set_margin_start(20); ca.set_margin_end(20); ca.set_spacing(8)
        ca.append(Gtk.Label(label="Enter master password:", xalign=0))
        e = Gtk.Entry(); e.set_visibility(False); ca.append(e)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Unlock", Gtk.ResponseType.OK)
        dlg.set_default_response(Gtk.ResponseType.OK)
        result = {"ok": False}
        def _resp(d, r):
            if r == Gtk.ResponseType.OK:
                if self.crypto.verify_and_unlock(e.get_text()):
                    result["ok"] = True
                else:
                    self._toast("Wrong password"); return
            d.destroy()
        dlg.connect("response", _resp)
        loop = GLib.MainLoop()
        dlg.connect("destroy", lambda *_: loop.quit())
        e.connect("activate", lambda _e: dlg.response(Gtk.ResponseType.OK))
        dlg.present()
        loop.run()
        return result["ok"]

    # ── Sidebar refresh ────────────────────────────────────────────────────
    def _refresh_sidebar(self, *, preserve_open=False):
        # clear list
        while True:
            r = self.notes_list.get_row_at_index(0)
            if r is None: break
            self.notes_list.remove(r)
        for k in list(self._note_cards):
            if k != "_swatches": del self._note_cards[k]

        notes = self.db.list_notes(
            search=self._search,
            notebook_id=self._notebook_filter,
            color=self._color_filter,
            tag=self._tag_filter,
            sort=self._sort)
        self.count_lbl.set_label(f"{len(notes)}")
        for n in notes:
            tags = self.db.get_tags(n["id"])
            card = NoteCard(n, tags,
                            on_click=self._open_note,
                            on_context=self._show_note_context)
            card.set_selected(n["id"] == self.current_id)
            row = Gtk.ListBoxRow()
            row.set_child(card)
            row.set_selectable(False)
            self._note_cards[n["id"]] = card
            self.notes_list.append(row)

    def _on_search(self, _, txt):
        self._search = txt
        self._refresh_sidebar(preserve_open=True)

    def _show_sort_menu(self, anchor):
        menu = Gtk.Popover(); menu.set_parent(anchor)
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        b.set_margin_top(6); b.set_margin_bottom(6)
        b.set_margin_start(6); b.set_margin_end(6)
        for key, label in (("modified", "Date modified"),
                           ("created",  "Date created"),
                           ("title",    "Title"),
                           ("words",    "Word count")):
            btn = Gtk.Button(label=("● " if key == self._sort else "  ") + label)
            btn.set_has_frame(False)
            def _set(_b, k=key):
                self._sort = k
                self._refresh_sidebar(preserve_open=True)
                menu.popdown()
            btn.connect("clicked", _set)
            b.append(btn)
        menu.set_child(b); menu.popup()

    def _show_filter_menu(self, anchor):
        menu = Gtk.Popover(); menu.set_parent(anchor)
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        b.set_margin_top(6); b.set_margin_bottom(6)
        b.set_margin_start(6); b.set_margin_end(6)
        all_btn = Gtk.Button(label="✕  Clear filters")
        all_btn.set_has_frame(False)
        def _clear(_b):
            self._color_filter = None; self._tag_filter = None
            self._refresh_sidebar(preserve_open=True); menu.popdown()
        all_btn.connect("clicked", _clear)
        b.append(all_btn)
        b.append(Gtk.Label(label="By color:", xalign=0))
        cb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        for c in NOTE_COLORS:
            d = Gtk.Button(); d.set_size_request(22, 22)
            d.set_has_frame(False)
            d.add_css_class("nyx-popover")
            def _filt(_b, k=c["key"]):
                self._color_filter = k
                self._refresh_sidebar(preserve_open=True); menu.popdown()
            d.connect("clicked", _filt)
            d.set_tooltip_text(c["name"])
            d.set_child(self._make_color_dot(c["rgb"]))
            cb.append(d)
        b.append(cb)
        tags = self.db.get_tags()
        if tags:
            b.append(Gtk.Label(label="By tag:", xalign=0))
            for t in tags[:20]:
                btn = Gtk.Button(label="#" + t)
                btn.set_has_frame(False)
                def _t(_b, tt=t):
                    self._tag_filter = tt
                    self._refresh_sidebar(preserve_open=True); menu.popdown()
                btn.connect("clicked", _t)
                b.append(btn)
        menu.set_child(b); menu.popup()

    def _make_color_dot(self, rgb):
        da = Gtk.DrawingArea()
        da.set_size_request(18, 18)
        try: da.set_content_width(18); da.set_content_height(18)
        except Exception: pass
        def _d(area, cr, w, h, _):
            cr.set_source_rgb(*rgb); cr.arc(w/2, h/2, w/2 - 2, 0, math.pi*2); cr.fill()
            cr.set_source_rgba(0,0,0,0.4); cr.set_line_width(1.0)
            cr.arc(w/2, h/2, w/2 - 2, 0, math.pi*2); cr.stroke()
        da.set_draw_func(_d)
        return da

    def _show_note_context(self, nid, x, y):
        """Right-click context menu on a note in the sidebar."""
        menu = Gtk.Popover()
        card = self._note_cards.get(nid)
        if card: menu.set_parent(card)
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        b.set_margin_top(4); b.set_margin_bottom(4)
        b.set_margin_start(4); b.set_margin_end(4)
        for label, fn in (
            ("Open", lambda: self._open_note(nid)),
            ("Duplicate", lambda: self._duplicate_specific(nid)),
            ("Pin / Unpin", lambda: self._toggle_pin_for(nid)),
            ("Star / Unstar", lambda: self._toggle_star_for(nid)),
            ("Export…", lambda: (self._open_note(nid), self._show_export())),
            ("Delete", lambda: self._confirm_delete(nid)),
        ):
            btn = Gtk.Button(label=label); btn.set_has_frame(False)
            def _w(_b, f=fn):
                menu.popdown(); GLib.idle_add(f)
            btn.connect("clicked", _w)
            b.append(btn)
        menu.set_child(b); menu.popup()

    def _duplicate_specific(self, nid):
        new = self.db.duplicate_note(nid)
        if new: self._open_note(new); self._refresh_sidebar()

    def _toggle_pin_for(self, nid):
        n = self.db.get_note(nid)
        if n: self.db.update_note(nid, pinned=int(not n["pinned"]))
        self._refresh_sidebar(preserve_open=True)

    def _toggle_star_for(self, nid):
        n = self.db.get_note(nid)
        if n: self.db.update_note(nid, starred=int(not n["starred"]))
        self._refresh_sidebar(preserve_open=True)

    def _confirm_delete(self, nid):
        n = self.db.get_note(nid)
        title = n["title"] if n else nid
        dlg = Gtk.MessageDialog(transient_for=self, modal=True,
                                message_type=Gtk.MessageType.WARNING,
                                buttons=Gtk.ButtonsType.OK_CANCEL,
                                text=f"Delete \"{title or 'Untitled'}\"?")
        dlg.format_secondary_text("This cannot be undone.")
        def _r(d, r):
            if r == Gtk.ResponseType.OK:
                self.db.delete_note(nid)
                if nid == self.current_id:
                    notes = self.db.list_notes()
                    self.current_id = None
                    if notes: self._open_note(notes[0]["id"])
                    else: self._new_note()
                self._refresh_sidebar()
            d.destroy()
        dlg.connect("response", _r); dlg.present()

    # ── Tags UI ────────────────────────────────────────────────────────────
    def _refresh_tag_pills(self):
        # clear
        for c in list(self.tags_pills):
            self.tags_pills.remove(c)
        if not self.current_id: return
        for t in self.db.get_tags(self.current_id):
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            box.add_css_class("nyx-tag-pill")
            box.append(Gtk.Label(label="#" + t))
            x = Gtk.Button(label="✕")
            x.set_has_frame(False)
            x.connect("clicked", lambda _b, tt=t: self._remove_tag(tt))
            box.append(x)
            self.tags_pills.append(box)

    def _on_tag_added(self, entry):
        if not self.current_id: return
        txt = entry.get_text().strip().lstrip("#")
        if not txt: return
        cur = set(self.db.get_tags(self.current_id))
        cur.add(txt.lower())
        self.db.set_tags(self.current_id, list(cur))
        entry.set_text("")
        self._refresh_tag_pills()
        self._refresh_sidebar(preserve_open=True)

    def _remove_tag(self, t):
        if not self.current_id: return
        cur = set(self.db.get_tags(self.current_id)) - {t}
        self.db.set_tags(self.current_id, list(cur))
        self._refresh_tag_pills()
        self._refresh_sidebar(preserve_open=True)

    # ── Inline insertions ──────────────────────────────────────────────────
    def _insert_link(self):
        dlg = Gtk.Dialog(title="Insert Link", transient_for=self, modal=True)
        dlg.set_default_size(360, -1)
        ca = dlg.get_content_area()
        ca.set_margin_top(12); ca.set_margin_bottom(12)
        ca.set_margin_start(20); ca.set_margin_end(20); ca.set_spacing(6)
        e_text = Gtk.Entry(); e_text.set_placeholder_text("Display text")
        e_url  = Gtk.Entry(); e_url.set_placeholder_text("https://…")
        ca.append(e_text); ca.append(e_url)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Insert", Gtk.ResponseType.OK)
        def _r(d, r):
            if r == Gtk.ResponseType.OK and e_url.get_text():
                self.editor.insert_link(e_url.get_text(), e_text.get_text())
            d.destroy()
        dlg.connect("response", _r); dlg.present()

    def _insert_quote(self):
        s, _ = self.editor._line_bounds()
        self.editor.buf.insert(s, "> ")

    # ── Templates dialog ──────────────────────────────────────────────────
    def _show_templates(self):
        dlg = Gtk.Dialog(title="Templates", transient_for=self, modal=True)
        dlg.set_default_size(560, 460)
        ca = dlg.get_content_area()
        ca.set_margin_top(14); ca.set_margin_bottom(14)
        ca.set_margin_start(20); ca.set_margin_end(20); ca.set_spacing(8)
        lbl = Gtk.Label(label="Pick a template to start a new note:",
                        xalign=0); lbl.add_css_class("nyx-headline")
        ca.append(lbl)
        sw = Gtk.ScrolledWindow(); sw.set_vexpand(True)
        lb = Gtk.ListBox()
        for t in self.db.list_templates():
            row = Gtk.ListBoxRow()
            r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            r.set_margin_start(8); r.set_margin_end(8)
            r.set_margin_top(6); r.set_margin_bottom(6)
            tag = "[built-in]" if t["builtin"] else "[custom]"
            r.append(Gtk.Label(label=t["name"], xalign=0))
            sp = Gtk.Box(); sp.set_hexpand(True); r.append(sp)
            mlbl = Gtk.Label(label=tag); mlbl.add_css_class("nyx-meta")
            r.append(mlbl)
            row.set_child(r); row.tpl = t; lb.append(row)
        def _act(_lb, row):
            t = row.tpl
            content = t["content"].format(
                date=datetime.now().strftime("%Y-%m-%d"),
                time=datetime.now().strftime("%H:%M"),
                title="")
            nid = self.db.create_note(title=t["name"], content=content)
            self._open_note(nid); self._refresh_sidebar()
            dlg.destroy()
        lb.connect("row-activated", _act)
        sw.set_child(lb); ca.append(sw)
        # Save current as template
        sb = SketchButton("Save current as template",
                          width=240, color=NEON_GREEN)
        def _save_cur(_b):
            if not self.current_id: dlg.destroy(); return
            n = self.db.get_note(self.current_id)
            self.db.save_template(n["title"] or "Untitled",
                                  self.editor.get_text())
            dlg.destroy(); self._toast("Template saved")
        sb.connect("clicked", _save_cur); ca.append(sb)
        dlg.add_buttons("Close", Gtk.ResponseType.CLOSE)
        dlg.connect("response", lambda d, r: d.destroy())
        dlg.present()

    # ── Export dialog ──────────────────────────────────────────────────────
    def _show_export(self):
        if not self.current_id: return
        n = self.db.get_note(self.current_id)
        # if locked, decrypt for export
        if n["locked"]:
            if not self.crypto.is_unlocked:
                if not self._prompt_unlock(): return
            try:
                content = self.crypto.decrypt(n["locked_blob"])
                n = dict(n); n["content"] = content
            except Exception:
                self._toast("Failed to decrypt"); return

        dlg = Gtk.Dialog(title="Export Note", transient_for=self, modal=True)
        dlg.set_default_size(420, -1)
        ca = dlg.get_content_area()
        ca.set_margin_top(14); ca.set_margin_bottom(14)
        ca.set_margin_start(20); ca.set_margin_end(20); ca.set_spacing(8)
        lbl = Gtk.Label(label=f"Export “{n['title'] or 'Untitled'}” as:",
                        xalign=0); lbl.add_css_class("nyx-headline")
        ca.append(lbl)
        formats = [
            ("Markdown (.md)", "md", lambda: Exporter.to_markdown(n)),
            ("Plain text (.txt)", "txt", lambda: Exporter.to_text(n)),
            ("HTML (.html)", "html", lambda: Exporter.to_html(n)),
        ]
        if HAS_REPORTLAB:
            formats.append(("PDF (.pdf)", "pdf", None))
        for label, ext, fn in formats:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.append(Gtk.Label(label=label, xalign=0))
            sp = Gtk.Box(); sp.set_hexpand(True); row.append(sp)
            b = SketchButton("Save", width=78, color=NEON_GREEN)
            def _x(_b, e=ext, f=fn):
                self._do_export(n, e, f); dlg.destroy()
            b.connect("clicked", _x); row.append(b)
            ca.append(row)
        if not HAS_REPORTLAB:
            ca.append(Gtk.Label(
                label="(install python-reportlab for PDF export)",
                xalign=0))
        ca.append(SketchSeparator(length=240))
        # Export ALL
        bx = SketchButton("Export ALL notes as ZIP",
                          width=240, color=ACCENT_PURP)
        bx.connect("clicked", lambda _b: (self._export_all_zip(), dlg.destroy()))
        ca.append(bx)
        dlg.add_buttons("Close", Gtk.ResponseType.CLOSE)
        dlg.connect("response", lambda d, r: d.destroy())
        dlg.present()

    def _do_export(self, n, ext, render_fn):
        safe = re.sub(r"[^A-Za-z0-9._-]+", "_",
                      n["title"] or "untitled")[:40] or "untitled"
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = EXPORT_DIR / f"{safe}-{ts}.{ext}"
        try:
            if ext == "pdf":
                Exporter.to_pdf(n, out)
            else:
                content = render_fn()
                out.write_text(content, encoding="utf-8")
            self._toast(f"Exported → {out}")
        except Exception as e:
            log("export " + traceback.format_exc())
            self._toast(f"Export failed: {e}")

    def _export_all_zip(self):
        import zipfile
        ts = datetime.now().strftime("%Y%m%d-%H%M%S")
        out = EXPORT_DIR / f"nyxus-notes-{ts}.zip"
        try:
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                for n in self.db.list_notes():
                    if n["locked"]: continue
                    safe = re.sub(r"[^A-Za-z0-9._-]+", "_",
                                  n["title"] or n["id"])[:40] or n["id"]
                    z.writestr(f"{safe}.md", Exporter.to_markdown(n))
            self._toast(f"Exported → {out}")
        except Exception as e:
            log("zip " + traceback.format_exc())
            self._toast(f"Export failed: {e}")

    # ── Settings dialog ────────────────────────────────────────────────────
    def _show_settings(self):
        dlg = Gtk.Dialog(title="Settings", transient_for=self, modal=True)
        dlg.set_default_size(440, -1)
        ca = dlg.get_content_area()
        ca.set_margin_top(14); ca.set_margin_bottom(14)
        ca.set_margin_start(20); ca.set_margin_end(20); ca.set_spacing(10)
        h = Gtk.Label(label="settings", xalign=0)
        h.add_css_class("nyx-headline"); ca.append(h)

        # autosave interval
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.append(Gtk.Label(label="Auto-save interval (seconds):", xalign=0))
        spn = Gtk.SpinButton.new_with_range(5, 600, 5)
        spn.set_value(self.AUTOSAVE_MS / 1000)
        def _on_save(_s):
            self.AUTOSAVE_MS = int(spn.get_value() * 1000)
            self.db.set_setting("autosave_ms", self.AUTOSAVE_MS)
        spn.connect("value-changed", _on_save)
        row.append(spn); ca.append(row)

        # Master password
        if HAS_CRYPTO:
            mpw = SketchButton(
                "Set / change master password",
                width=260, color=ACCENT_GOLD)
            mpw.connect("clicked", lambda _b: (dlg.destroy(),
                                               self._prompt_set_master()))
            ca.append(mpw)
        else:
            ca.append(Gtk.Label(label="(install python-cryptography for locked notes)",
                                xalign=0))

        # Backup
        bk = SketchButton("Backup vault now (zip)",
                          width=260, color=ACCENT_PURP)
        def _bkup(_b):
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            out = BACKUP_DIR / f"vault-{ts}.zip"
            import zipfile
            with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
                for p in CONFIG_DIR.rglob("*"):
                    if p.is_file() and BACKUP_DIR not in p.parents:
                        z.write(p, p.relative_to(CONFIG_DIR))
            self._toast(f"Backup → {out}"); dlg.destroy()
        bk.connect("clicked", _bkup); ca.append(bk)

        # Stats
        s = self.db.stats()
        st = Gtk.Label(
            label=f"Total notes: {s['notes']}   "
                  f"Words: {s['words']:,}   "
                  f"Characters: {s['chars']:,}",
            xalign=0)
        st.add_css_class("nyx-meta"); ca.append(st)

        dlg.add_buttons("Close", Gtk.ResponseType.CLOSE)
        dlg.connect("response", lambda d, r: d.destroy())
        dlg.present()

    # ── Distraction-free / typewriter modes ────────────────────────────────
    def _toggle_distraction_free(self):
        self._df_mode = not self._df_mode
        if self._df_mode:
            self.toolbar.set_visible(False)
            self.sidebar.set_visible(False)
            self.format_bar.set_visible(False)
            self.tags_row.set_visible(False)
            self.status_bar.set_visible(False)
        else:
            self.toolbar.set_visible(True)
            self.sidebar.set_visible(True)
            self.format_bar.set_visible(True)
            self.tags_row.set_visible(True)
            self.status_bar.set_visible(True)

    # ── Status bar refresh ─────────────────────────────────────────────────
    def _refresh_status(self):
        text = self.editor.get_text()
        words = len(text.split())
        chars = len(text)
        lines = text.count("\n") + (1 if text else 0)
        reading = max(1, round(words / 220))   # ~220 wpm
        self.sb_words.set_label(f"{words} words")
        self.sb_chars.set_label(f"{chars} chars")
        self.sb_lines.set_label(f"{lines} lines")
        self.sb_reading.set_label(f"{reading} min read")
        if not self._dirty:
            self.sb_saved.set_label("✓ saved")
        else:
            self.sb_saved.set_label("• unsaved")

    # ── Command palette ────────────────────────────────────────────────────
    def _show_command_palette(self):
        cmds = [
            ("New note",                  self._new_note),
            ("Save note",                 self._save_now),
            ("Duplicate note",            self._duplicate_current),
            ("Lock / unlock note",        self._toggle_lock),
            ("Pin / unpin",               self._toggle_pin),
            ("Star / unstar",             self._toggle_star),
            ("Insert link",               self._insert_link),
            ("Insert table",              lambda: self.editor.insert_table()),
            ("Insert code block",         lambda: self.editor.insert_code_block()),
            ("Insert horizontal rule",    lambda: self.editor.insert_horizontal_rule()),
            ("Bold",                      lambda: self.editor.toggle_tag("bold")),
            ("Italic",                    lambda: self.editor.toggle_tag("italic")),
            ("Underline",                 lambda: self.editor.toggle_tag("underline")),
            ("Strikethrough",             lambda: self.editor.toggle_tag("strike")),
            ("Heading 1",                 lambda: self.editor.apply_heading(1)),
            ("Heading 2",                 lambda: self.editor.apply_heading(2)),
            ("Heading 3",                 lambda: self.editor.apply_heading(3)),
            ("Bullet list",               lambda: self.editor.apply_bullet_to_lines()),
            ("Numbered list",             lambda: self.editor.apply_numbered()),
            ("Checkbox list",             lambda: self.editor.apply_checkbox()),
            ("Find & replace",            lambda: self.find_bar.open()),
            ("Templates…",                self._show_templates),
            ("Export…",                   self._show_export),
            ("Settings…",                 self._show_settings),
            ("Distraction-free mode",     self._toggle_distraction_free),
            ("Show statistics",           lambda: self._show_settings()),
        ]
        for c in NOTE_COLORS:
            cmds.append((f"Set colour: {c['name']}",
                         lambda k=c["key"]: self._set_color(k)))
        cp = CommandPalette(self, cmds); cp.present()

    # ── Toast ──────────────────────────────────────────────────────────────
    def _toast(self, msg):
        self.sb_state.set_label("⚡ " + msg)
        log(msg)
        GLib.timeout_add_seconds(4, lambda: (self.sb_state.set_label(""), False)[1])


# ═══════════════════════════════════════════════════════════════════════════════
class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = NotepadWindow(self)
        win.present()


if __name__ == "__main__":
    try:
        App().run(sys.argv)
    except Exception:
        log("FATAL " + traceback.format_exc())
        raise
