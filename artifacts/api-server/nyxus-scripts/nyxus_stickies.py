#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NYXUS Stickies — minimal hand-drawn sticky notes on a dark canvas.

Just the notes. Nothing else.

  • Tilted Cairo paper notes with subtle shadow + folded corner
  • 7 store-bought colors: yellow, pink, blue, green, orange, purple, white
  • Click to select, double-click to edit text DIRECTLY ON THE NOTE
  • Color dot top-left to cycle, X top-right to delete (with fade)
  • Drag to move anywhere on the canvas
  • Auto-saved to ~/.config/nyxus-stickies/notes.db (sqlite3)
"""

from __future__ import annotations

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


__nyxid__ = "4e59582d4a35572d323032362d53494552454e474f57534b492d4c4f434b4544"

def _nyx_integrity():
    try:
        _s = open(__file__, encoding="utf-8").read()
        assert "SIERENGOWSKI" in _s, "NYXUS: tamper detected"
    except (OSError, AssertionError) as _e:
        import sys as _sys; print(f"NYXUS SECURITY: {_e}", file=_sys.stderr)
_nyx_integrity()

import logging
import math
import random
import sqlite3
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, GLib, GObject, Gio, Pango, PangoCairo, Adw  # noqa: E402

# ── NYXUS shared chrome (rainbow titles + graffiti walls, system-wide) ──
def _nyxus_load_chrome():
    try:
        from nyxus_chrome import install_chrome, rainbow_markup
        return install_chrome, rainbow_markup
    except ImportError:
        try:
            import os, sys, urllib.request
            _here = os.path.dirname(os.path.abspath(__file__))
            urllib.request.urlretrieve(
                "https://nyxus-core.replit.app/api/download/nyxus/nyxus_chrome.py",
                os.path.join(_here, "nyxus_chrome.py"))
            if _here not in sys.path: sys.path.insert(0, _here)
            from nyxus_chrome import install_chrome, rainbow_markup
            return install_chrome, rainbow_markup
        except Exception:
            return (lambda *a, **kw: None), (lambda t: t)
_nyx_install_chrome, _nyx_rainbow = _nyxus_load_chrome()
import cairo  # noqa: E402

# ── paths ────────────────────────────────────────────────────────────────────
APP_ID    = "io.nyxus.stickies"
APP_NAME  = "NYXUS Stickies"
WIN_W, WIN_H = 1280, 800

CONFIG_DIR = Path.home() / ".config" / "nyxus-stickies"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH  = CONFIG_DIR / "notes.db"
LOG_PATH = Path("/tmp/nyxus-stickies.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="a"), logging.StreamHandler()],
)
log = logging.getLogger("nyxus-stickies")

# ── DARK MIRROR Cairo float tuples (rev r13) ────────────────────────────
# Names retained for call-site compatibility; values remapped to the
# locked monochrome palette. Authoritative source: nyxus_palette.py
# (NOTE_COLORS below remain colored — sticky-note paper colors are an
# inherent product identity, not a UI accent.)
BG_DEEP    = (0.031, 0.047, 0.078)   # rgba(8,12,20) glass-dark base
NEON_PINK  = (1.000, 1.000, 1.000)   # → WHITE_PURE
NEON_GREEN = (0.784, 0.800, 0.839)   # → GREY_LIGHT
INK_DIM    = (0.784, 0.800, 0.839)   # → GREY_LIGHT
DANGER_RED = (0.910, 0.929, 0.961)   # → WHITE_OFF (semantic only)

# ── store-bought sticky note colors ──────────────────────────────────────────
NOTE_COLORS = [
    {"key": "yellow", "name": "Yellow", "rgb": (0.99, 0.92, 0.42), "shadow": (0.40, 0.34, 0.10)},
    {"key": "pink",   "name": "Pink",   "rgb": (1.00, 0.55, 0.78), "shadow": (0.50, 0.10, 0.30)},
    {"key": "blue",   "name": "Blue",   "rgb": (0.55, 0.83, 1.00), "shadow": (0.10, 0.32, 0.50)},
    {"key": "green",  "name": "Green",  "rgb": (0.62, 0.95, 0.70), "shadow": (0.10, 0.40, 0.20)},
    {"key": "orange", "name": "Orange", "rgb": (1.00, 0.72, 0.32), "shadow": (0.50, 0.30, 0.05)},
    {"key": "purple", "name": "Purple", "rgb": (0.85, 0.72, 1.00), "shadow": (0.30, 0.18, 0.50)},
    {"key": "white",  "name": "White",  "rgb": (0.96, 0.96, 0.92), "shadow": (0.30, 0.30, 0.30)},
]
COLOR_BY_KEY = {c["key"]: c for c in NOTE_COLORS}


# ═══════════════════════════════════════════════════════════════════════════════
#  Sketch helpers
# ═══════════════════════════════════════════════════════════════════════════════
def _seed(*parts):
    import hashlib
    h = hashlib.md5(repr(parts).encode("utf-8")).digest()
    return random.Random(int.from_bytes(h[:8], "big"))

def sketch_line(cr, x1, y1, x2, y2, *, jitter=0.6, segments=10, key=None):
    rng = _seed(key or ("ln", round(x1,1), round(y1,1), round(x2,1), round(y2,1)))
    n = max(2, segments); cr.move_to(x1, y1)
    for i in range(1, n):
        t = i / (n - 1)
        x = x1 + (x2 - x1) * t + (rng.random() - 0.5) * jitter
        y = y1 + (y2 - y1) * t + (rng.random() - 0.5) * jitter
        cr.line_to(x, y)
    cr.line_to(x2, y2); cr.stroke()

def sketch_rect(cr, x, y, w, h, *, jitter=0.6, key=None):
    k = key or ("rc", round(x), round(y), round(w), round(h))
    sketch_line(cr, x, y, x+w, y,   jitter=jitter, key=(k, "t"))
    sketch_line(cr, x+w, y, x+w, y+h, jitter=jitter, key=(k, "r"))
    sketch_line(cr, x+w, y+h, x, y+h, jitter=jitter, key=(k, "b"))
    sketch_line(cr, x, y+h, x, y,    jitter=jitter, key=(k, "l"))

def draw_caveat(cr, x, y, text, *, size=16, color=(0,0,0,0.95),
                family="Inter Display", wrap_w=None):
    cr.save(); cr.set_source_rgba(*color)
    layout = PangoCairo.create_layout(cr)
    fd = Pango.FontDescription()
    fd.set_family(family); fd.set_size(int(size * Pango.SCALE))
    layout.set_font_description(fd)
    if wrap_w is not None:
        layout.set_width(int(wrap_w * Pango.SCALE))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    layout.set_text(text or "", -1)
    cr.move_to(x, y); PangoCairo.show_layout(cr, layout)
    cr.restore(); return layout


# ═══════════════════════════════════════════════════════════════════════════════
#  Database
# ═══════════════════════════════════════════════════════════════════════════════
class DB:
    def __init__(self, path: Path = DB_PATH):
        self.conn = sqlite3.connect(str(path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS notes(
                id     TEXT PRIMARY KEY,
                body   TEXT DEFAULT '',
                color  TEXT DEFAULT 'yellow',
                x      REAL DEFAULT 100,
                y      REAL DEFAULT 100,
                w      REAL DEFAULT 220,
                h      REAL DEFAULT 200,
                tilt   REAL DEFAULT 0,
                created INTEGER NOT NULL,
                updated INTEGER NOT NULL
            )""")
        self.conn.commit()

    def list_notes(self):
        return list(self.conn.execute(
            "SELECT * FROM notes ORDER BY updated ASC"))

    def get(self, nid):
        return self.conn.execute("SELECT * FROM notes WHERE id=?",
                                 (nid,)).fetchone()

    def create(self, color="yellow", x=120, y=120):
        nid = uuid.uuid4().hex[:12]; ts = int(time.time())
        self.conn.execute(
            "INSERT INTO notes(id,body,color,x,y,w,h,tilt,created,updated) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (nid, "", color, x, y, 220, 200,
             random.uniform(-7, 7), ts, ts))
        self.conn.commit(); return nid

    def update(self, nid, **kw):
        if not kw: return
        cols = ", ".join(f"{k}=?" for k in kw)
        vals = list(kw.values()) + [int(time.time()), nid]
        self.conn.execute(f"UPDATE notes SET {cols}, updated=? WHERE id=?",
                          vals)
        self.conn.commit()

    def delete(self, nid):
        self.conn.execute("DELETE FROM notes WHERE id=?", (nid,))
        self.conn.commit()


# ═══════════════════════════════════════════════════════════════════════════════
#  Sketch button (used only on the toolbar)
# ═══════════════════════════════════════════════════════════════════════════════
class SketchButton(Gtk.DrawingArea):
    __gsignals__ = {"clicked": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, label, *, width=120, height=28, color=NEON_PINK,
                 tooltip=None, primary=False):
        super().__init__()
        self.label, self.color, self.primary = label, color, primary
        self._hover = False; self._press = False
        self.set_size_request(width, height)
        try: self.set_content_width(width); self.set_content_height(height)
        except Exception: pass
        self.set_draw_func(self._draw)
        if tooltip: self.set_tooltip_text(tooltip)
        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("pressed", lambda *a: (setattr(self,"_press",True), self.queue_draw()))
        gc.connect("released", self._release)
        self.add_controller(gc)
        mc = Gtk.EventControllerMotion()
        mc.connect("enter", lambda *a: (setattr(self,"_hover",True), self.queue_draw()))
        mc.connect("leave", lambda *a: (setattr(self,"_hover",False),
                                        setattr(self,"_press",False), self.queue_draw()))
        self.add_controller(mc)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

    def _release(self, *a):
        was = self._press; self._press = False; self.queue_draw()
        if was: self.emit("clicked")

    def _draw(self, area, cr, w, h, _=None):
        c = self.color
        a = 0.25 if self.primary else 0.10
        if self._press: a += 0.18
        elif self._hover: a += 0.10
        cr.set_source_rgba(*c, a); cr.rectangle(2, 2, w-4, h-4); cr.fill()
        cr.set_source_rgba(*c, 0.95 if self._hover else 0.75)
        cr.set_line_width(1.4 if self.primary else 1.1)
        sketch_rect(cr, 1.5, 1.5, w-3, h-3, jitter=0.55,
                    key=("btn", id(self), w, h))
        layout = PangoCairo.create_layout(cr)
        fd = Pango.FontDescription()
        fd.set_family("Inter Display"); fd.set_size(int(14 * Pango.SCALE))
        fd.set_weight(Pango.Weight.BOLD if self.primary else Pango.Weight.NORMAL)
        layout.set_font_description(fd); layout.set_text(self.label, -1)
        tw, th = layout.get_pixel_size()
        cr.set_source_rgba(0.94, 0.92, 0.97, 1.0 if self._hover else 0.92)
        cr.move_to((w-tw)/2, (h-th)/2); PangoCairo.show_layout(cr, layout)


# ═══════════════════════════════════════════════════════════════════════════════
#  Sticky note widget — Cairo paper + overlaid TextView for INLINE editing
# ═══════════════════════════════════════════════════════════════════════════════
class StickyNote(Gtk.Overlay):
    __gsignals__ = {
        "moved":       (GObject.SignalFlags.RUN_FIRST, None, (str, float, float)),
        "drag-step":   (GObject.SignalFlags.RUN_FIRST, None, (str, float, float)),
        "selected":    (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "delete":      (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "color-cycle": (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "text-saved":  (GObject.SignalFlags.RUN_FIRST, None, (str, str)),
    }

    PADDING = 18

    def __init__(self, note: sqlite3.Row):
        super().__init__()
        self.nid  = note["id"]
        self.note = dict(note)
        self.tilt_target = float(note["tilt"] or 0)
        self.tilt        = self.tilt_target
        self.w    = float(note["w"]); self.h = float(note["h"])
        self.editing  = False
        self.dragging = False
        self.hover    = False
        self.selected = False
        self.lift     = 0.0
        self.entrance = 0.0
        self.fade     = 1.0; self.crumple = 0.0
        self._press_x = 0.0; self._press_y = 0.0
        self._last_click_t = 0.0
        self._anim_lift = None
        self._anim_tilt = None

        self._refresh_size()

        # ── bottom layer: Cairo paper ──
        self.paper = Gtk.DrawingArea()
        self.paper.set_draw_func(self._draw)
        self.set_child(self.paper)

        # ── overlay: inline editor (hidden until double-clicked) ──
        self.tv = Gtk.TextView()
        self.tv.set_visible(False)
        self.tv.add_css_class("nyx-sticky-text")
        self.tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.tv.set_top_margin(8); self.tv.set_bottom_margin(8)
        self.tv.set_left_margin(6); self.tv.set_right_margin(6)
        self.tv.set_halign(Gtk.Align.CENTER)
        self.tv.set_valign(Gtk.Align.CENTER)
        self.tv.set_size_request(int(self.w - 36), int(self.h - 50))
        self.buf = self.tv.get_buffer()
        self.buf.set_text(self.note.get("body") or "")
        self.add_overlay(self.tv)

        fc = Gtk.EventControllerFocus()
        fc.connect("leave", lambda *a: self.end_edit())
        self.tv.add_controller(fc)
        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._key)
        self.tv.add_controller(kc)

        # ── paper gestures (drag handles both click + drag) ──
        gd = Gtk.GestureDrag(); gd.set_button(1)
        gd.connect("drag-begin",  self._drag_begin)
        gd.connect("drag-update", self._drag_update)
        gd.connect("drag-end",    self._drag_end)
        self.paper.add_controller(gd)
        mc = Gtk.EventControllerMotion()
        mc.connect("enter", self._enter); mc.connect("leave", self._leave)
        self.paper.add_controller(mc)
        self.paper.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        self._drag_started = False
        self._suppress_click = False

        # entrance pop-in
        def step():
            self.entrance += 0.10
            if self.entrance >= 1: self.entrance = 1; self.paper.queue_draw(); return False
            self.paper.queue_draw(); return True
        GLib.timeout_add(16, step)

    # ── geometry ────────────────────────────────────────────────────────────
    def _refresh_size(self):
        slop = 36 + abs(math.sin(math.radians(max(7, abs(self.tilt_target)))))\
               * max(self.w, self.h)
        wx = int(self.w + slop * 2); wy = int(self.h + slop * 2)
        self.set_size_request(wx, wy)
        try: self.set_content_width(wx); self.set_content_height(wy)
        except Exception: pass

    def update_from_row(self, n):
        was_edit = self.editing
        self.note = dict(n); self.tilt_target = float(n["tilt"] or 0)
        if not was_edit: self.tilt = self.tilt_target
        self.w = float(n["w"]); self.h = float(n["h"])
        self._refresh_size()
        if not was_edit: self.buf.set_text(self.note.get("body") or "")
        self.paper.queue_draw()

    # ── animations ──────────────────────────────────────────────────────────
    def _set_lift(self, target):
        if self._anim_lift:
            try: GLib.source_remove(self._anim_lift)
            except Exception: pass
            self._anim_lift = None
        def step():
            d = target - self.lift
            if abs(d) < 0.02: self.lift = target; self.paper.queue_draw(); return False
            self.lift += d * 0.28; self.paper.queue_draw(); return True
        self._anim_lift = GLib.timeout_add(16, step)

    def _animate_tilt(self, target):
        if self._anim_tilt:
            try: GLib.source_remove(self._anim_tilt)
            except Exception: pass
            self._anim_tilt = None
        def step():
            d = target - self.tilt
            if abs(d) < 0.15:
                self.tilt = target; self.paper.queue_draw(); return False
            self.tilt += d * 0.30; self.paper.queue_draw(); return True
        self._anim_tilt = GLib.timeout_add(16, step)

    def start_fade(self, on_done):
        def step():
            self.crumple += 0.08; self.fade = max(0.0, 1.0 - self.crumple)
            if self.crumple >= 1: on_done(); return False
            self.paper.queue_draw(); return True
        GLib.timeout_add(16, step)

    # ── coord transforms ────────────────────────────────────────────────────
    def _local_to_note(self, lx, ly):
        cx = self.get_allocated_width()/2; cy = self.get_allocated_height()/2
        rad = -math.radians(self.tilt)
        sx = lx - cx; sy = ly - cy
        rx = sx*math.cos(rad) - sy*math.sin(rad)
        ry = sx*math.sin(rad) + sy*math.cos(rad)
        return rx + self.w/2, ry + self.h/2

    def _hits_note(self, lx, ly):
        nx, ny = self._local_to_note(lx, ly)
        return 0 <= nx <= self.w and 0 <= ny <= self.h

    def _hits_close(self, lx, ly):
        nx, ny = self._local_to_note(lx, ly)
        return math.hypot(nx - (self.w - 14), ny - 14) <= 12

    def _hits_color(self, lx, ly):
        nx, ny = self._local_to_note(lx, ly)
        return math.hypot(nx - 14, ny - 14) <= 10

    # ── events ──────────────────────────────────────────────────────────────
    def _enter(self, *a):
        self.hover = True; self._set_lift(1.0)
    def _leave(self, *a):
        self.hover = False; self._set_lift(0.0)

    def _key(self, ctrl, keyval, *a):
        if keyval == Gdk.KEY_Escape:
            self.end_edit(); return True
        return False

    def _drag_begin(self, ctrl, x, y):
        self._drag_started = False
        self._suppress_click = False
        self._press_x, self._press_y = x, y
        if self.editing:
            self._suppress_click = True; return
        if not self._hits_note(x, y):
            self._suppress_click = True; return
        # corner buttons handled on release (drag-end), not here, so a
        # tiny drag still counts as a click on them.
        if self._hits_close(x, y) or self._hits_color(x, y):
            return
        # bring this note to front + select on press start
        self.emit("selected", self.nid)

    def _drag_update(self, ctrl, dx, dy):
        if self._suppress_click: return
        # corner buttons: don't move the note
        if self._hits_close(self._press_x, self._press_y): return
        if self._hits_color(self._press_x, self._press_y): return
        if not self._drag_started and (abs(dx) + abs(dy)) > 4:
            self._drag_started = True
            self._drag_extra = random.uniform(-3, 3)
            self.tilt += self._drag_extra
            self.paper.queue_draw()
        if self._drag_started:
            self.emit("drag-step", self.nid, dx, dy)

    def _drag_end(self, ctrl, dx, dy):
        if self._suppress_click: return
        if self._drag_started:
            self.tilt -= getattr(self, "_drag_extra", 0)
            self.emit("moved", self.nid, dx, dy)
            self._drag_started = False
            self.paper.queue_draw()
            return
        # treated as a click
        x, y = self._press_x, self._press_y
        if self._hits_close(x, y):
            self.emit("delete", self.nid); return
        if self._hits_color(x, y):
            self.emit("color-cycle", self.nid); return
        # double-click → inline edit
        now = time.monotonic()
        if now - self._last_click_t < 0.35:
            self.begin_edit()
            self._last_click_t = 0; return
        self._last_click_t = now

    # ── inline editing ──────────────────────────────────────────────────────
    def begin_edit(self):
        if self.editing: return
        self.editing = True
        self._animate_tilt(0.0)
        self.tv.set_size_request(int(self.w - 36), int(self.h - 50))
        self.tv.set_visible(True)
        self.buf.set_text(self.note.get("body") or "")
        # focus next tick so animation can start
        GLib.idle_add(lambda: (self.tv.grab_focus(), False)[1])
        self.paper.queue_draw()

    def end_edit(self):
        if not self.editing: return
        self.editing = False
        body = self.buf.get_text(self.buf.get_start_iter(),
                                 self.buf.get_end_iter(), False)
        self.note["body"] = body
        self.tv.set_visible(False)
        self._animate_tilt(self.tilt_target)
        self.paper.queue_draw()
        self.emit("text-saved", self.nid, body)

    # ── draw ────────────────────────────────────────────────────────────────
    def _color_rgb(self):
        c = COLOR_BY_KEY.get(self.note.get("color"), COLOR_BY_KEY["yellow"])
        return c["rgb"]
    def _shadow_rgb(self):
        c = COLOR_BY_KEY.get(self.note.get("color"), COLOR_BY_KEY["yellow"])
        return c["shadow"]

    def _draw(self, area, cr, w, h, _=None):
        try: self._draw_inner(cr, w, h)
        except Exception as e: log.error("draw err: %s", e)

    def _draw_inner(self, cr, w, h):
        cx, cy = w/2, h/2
        cr.save()
        cr.translate(cx, cy)
        scale = 0.5 + 0.5 * self.entrance + 0.04 * self.lift
        if self.crumple > 0: scale *= (1.0 - self.crumple * 0.5)
        cr.scale(scale, scale)
        cr.rotate(math.radians(self.tilt))
        cr.translate(-self.w/2, -self.h/2)

        col = self._color_rgb(); sh = self._shadow_rgb()
        # drop shadow
        sh_off = 4 + 6 * self.lift
        cr.set_source_rgba(0, 0, 0, 0.45 * self.fade)
        cr.rectangle(sh_off, sh_off, self.w, self.h); cr.fill()
        cr.set_source_rgba(*sh, 0.30 * self.fade)
        cr.rectangle(sh_off+1, sh_off+1, self.w, self.h); cr.fill()
        # paper body
        cr.set_source_rgba(*col, self.fade)
        cr.rectangle(0, 0, self.w, self.h); cr.fill()
        # paper texture
        cr.set_source_rgba(0, 0, 0, 0.04 * self.fade); cr.set_line_width(0.6)
        rng = _seed("paper", self.nid)
        for _ in range(int(self.w * self.h / 2200)):
            x0 = rng.uniform(0, self.w); y0 = rng.uniform(0, self.h)
            cr.move_to(x0, y0)
            cr.line_to(x0 + rng.uniform(-3, 3), y0 + rng.uniform(-3, 3))
            cr.stroke()
        # folded corner
        fold = 22
        cr.set_source_rgba(*sh, 0.55 * self.fade)
        cr.move_to(self.w, self.h - fold); cr.line_to(self.w, self.h)
        cr.line_to(self.w - fold, self.h); cr.close_path(); cr.fill()
        cr.set_source_rgba(min(col[0]+0.10,1), min(col[1]+0.10,1),
                           min(col[2]+0.10,1), self.fade)
        cr.move_to(self.w-2, self.h - fold + 2)
        cr.line_to(self.w-2, self.h-2); cr.line_to(self.w-fold+2, self.h-2)
        cr.close_path(); cr.fill()
        # hand-drawn border
        cr.set_source_rgba(0, 0, 0, 0.55 * self.fade); cr.set_line_width(1.4)
        sketch_rect(cr, 1, 1, self.w-2, self.h-2, jitter=0.7,
                    key=("border", self.nid))

        # color dot (top-left)
        cr.save()
        cr.set_source_rgba(*col, 0.95)
        cr.arc(14, 14, 8, 0, math.pi*2); cr.fill()
        cr.set_source_rgba(0, 0, 0, 0.7); cr.set_line_width(1.2)
        cr.arc(14, 14, 8, 0, math.pi*2); cr.stroke()
        cr.restore()

        # close X (top-right)
        cr.save()
        close_alpha = 0.85 if self.hover else 0.45
        cr.set_source_rgba(*DANGER_RED, close_alpha * 0.30)
        cr.arc(self.w - 14, 14, 10, 0, math.pi*2); cr.fill()
        cr.set_source_rgba(0, 0, 0, close_alpha)
        cr.set_line_width(1.6); cr.set_line_cap(cairo.LINE_CAP_ROUND)
        sketch_line(cr, self.w-19, 9,  self.w-9, 19, jitter=0.4,
                    key=("x1", self.nid))
        sketch_line(cr, self.w-9,  9,  self.w-19, 19, jitter=0.4,
                    key=("x2", self.nid))
        cr.restore()

        # body text — drawn here ONLY when not editing (TextView shows it otherwise)
        if not self.editing:
            text_color = (0.10, 0.08, 0.14, 0.95 * self.fade)
            body = self.note.get("body") or "(double-click to write…)"
            if not (self.note.get("body") or "").strip():
                text_color = (0.10, 0.08, 0.14, 0.40 * self.fade)
            draw_caveat(cr, self.PADDING, self.PADDING + 14, body,
                        size=18, color=text_color,
                        wrap_w=self.w - self.PADDING * 2)

        # selection halo
        if self.selected and not self.editing:
            cr.set_source_rgba(*NEON_PINK, 0.85); cr.set_line_width(2.4)
            sketch_rect(cr, -4, -4, self.w + 8, self.h + 8, jitter=0.9,
                        key=("sel", self.nid))
        cr.restore()


# ═══════════════════════════════════════════════════════════════════════════════
#  Color picker (for "New note")
# ═══════════════════════════════════════════════════════════════════════════════
class ColorPicker(Gtk.Window):
    def __init__(self, win):
        super().__init__(transient_for=win, title="pick color")
        self.win = win
        self.set_default_size(380, -1); self.set_modal(True)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_margin_start(16); outer.set_margin_end(16)
        outer.set_margin_top(16); outer.set_margin_bottom(16)
        self.set_child(outer)
        outer.append(Gtk.Label(label="pick a color for your new note",
                               xalign=0))
        flow = Gtk.FlowBox(); flow.set_max_children_per_line(7)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        outer.append(flow)
        for c in NOTE_COLORS:
            btn = Gtk.Button()
            da = Gtk.DrawingArea()
            da.set_size_request(48, 48)
            try: da.set_content_width(48); da.set_content_height(48)
            except Exception: pass
            def make_draw(rgb, name):
                def _d(area, cr, w, h, _=None):
                    cr.set_source_rgba(0, 0, 0, 0.4)
                    cr.rectangle(7, 7, w-10, h-10); cr.fill()
                    cr.set_source_rgb(*rgb)
                    cr.rectangle(4, 4, w-10, h-10); cr.fill()
                    cr.set_source_rgba(0, 0, 0, 0.7); cr.set_line_width(1.2)
                    sketch_rect(cr, 4, 4, w-10, h-10, jitter=0.5, key=("cs", name))
                return _d
            da.set_draw_func(make_draw(c["rgb"], c["key"]))
            btn.set_child(da)
            btn.set_tooltip_text(c["name"])
            btn.connect("clicked",
                        lambda _b, k=c["key"]:
                        (self.win.create_note(k), self.close()))
            flow.append(btn)


# ═══════════════════════════════════════════════════════════════════════════════
#  Canvas (scrollable Fixed)
# ═══════════════════════════════════════════════════════════════════════════════
class Canvas(Gtk.Box):
    CANVAS_W = 4000
    CANVAS_H = 3000

    def __init__(self, win):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.win = win
        self.notes: Dict[str, StickyNote] = {}
        self.bg = Gtk.DrawingArea()
        self.bg.set_content_width(self.CANVAS_W)
        self.bg.set_content_height(self.CANVAS_H)
        self.bg.set_draw_func(self._draw_bg)
        self.fixed = Gtk.Fixed()
        self.fixed.set_size_request(self.CANVAS_W, self.CANVAS_H)
        self.fixed.put(self.bg, 0, 0)
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.set_hexpand(True); sw.set_vexpand(True)
        sw.set_child(self.fixed); self.append(sw)
        self.scroller = sw
        # click on bg to deselect / commit any open editor
        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("pressed", self._bg_click)
        self.bg.add_controller(gc)

    def _bg_click(self, *a):
        for sn in self.notes.values():
            if sn.editing: sn.end_edit()
            sn.selected = False; sn.paper.queue_draw()

    def load_all(self):
        for nid, w in list(self.notes.items()):
            try: self.fixed.remove(w)
            except Exception: pass
        self.notes.clear()
        for n in self.win.db.list_notes():
            self.add_row(n)

    def add_row(self, n):
        sn = StickyNote(n)
        self.notes[n["id"]] = sn
        sn.connect("moved",       self._on_moved)
        sn.connect("drag-step",   self._on_drag_step)
        sn.connect("selected",    self._on_selected)
        sn.connect("delete",      lambda _w, nid: self.win.delete_note(nid))
        sn.connect("color-cycle", lambda _w, nid: self.win.cycle_color(nid))
        sn.connect("text-saved",  self._on_text_saved)
        ax = float(n["x"]) - (sn.get_size_request()[0] - sn.w) / 2
        ay = float(n["y"]) - (sn.get_size_request()[1] - sn.h) / 2
        sn._anchor_x = ax; sn._anchor_y = ay
        self.fixed.put(sn, int(ax), int(ay))

    def update_note(self, nid):
        sn = self.notes.get(nid)
        if not sn: return
        row = self.win.db.get(nid)
        if not row: return
        sn.update_from_row(row)
        ax = float(row["x"]) - (sn.get_size_request()[0] - sn.w) / 2
        ay = float(row["y"]) - (sn.get_size_request()[1] - sn.h) / 2
        sn._anchor_x = ax; sn._anchor_y = ay
        self.fixed.move(sn, int(ax), int(ay))

    def _on_drag_step(self, sn, nid, dx, dy):
        # live cursor follow during drag (no DB write yet)
        ax = sn._anchor_x + dx; ay = sn._anchor_y + dy
        self.fixed.move(sn, int(ax), int(ay))

    def _on_moved(self, sn, nid, dx, dy):
        row = self.win.db.get(nid)
        if not row: return
        nx = float(row["x"]) + dx; ny = float(row["y"]) + dy
        self.win.db.update(nid, x=nx, y=ny); self.update_note(nid)

    def _on_selected(self, sn, nid):
        for k, w in self.notes.items():
            if k != nid and w.editing: w.end_edit()
            w.selected = (k == nid); w.paper.queue_draw()
        # bring selected note to front so it's not hidden behind others
        try: self.fixed.set_child_above_sibling(sn, None)
        except Exception:
            try:
                self.fixed.remove(sn)
                self.fixed.put(sn, int(sn._anchor_x), int(sn._anchor_y))
            except Exception: pass

    def _on_text_saved(self, sn, nid, body):
        self.win.db.update(nid, body=body)

    def save_all_open_editors(self):
        for sn in self.notes.values():
            if sn.editing: sn.end_edit()

    def _draw_bg(self, area, cr, w, h, _=None):
        cr.set_source_rgb(*BG_DEEP); cr.rectangle(0, 0, w, h); cr.fill()
        cr.set_source_rgba(*NEON_PINK, 0.04)
        for x in range(0, w, 60):
            for y in range(0, h, 60):
                cr.arc(x, y, 0.8, 0, math.pi*2); cr.fill()


# ═══════════════════════════════════════════════════════════════════════════════
#  Main window
# ═══════════════════════════════════════════════════════════════════════════════
class StickiesWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME)
        self.set_default_size(WIN_W, WIN_H)
        self.db = DB()
        self._build_css()
        self._build_layout()
        self.canvas.load_all()
        try: _nyx_install_chrome(self, page_key="_stickies")
        except Exception: pass
        self.connect("close-request", self._on_close)

    def _on_close(self, *a):
        # auto-save: commit any open editor before exit
        self.canvas.save_all_open_editors()
        return False

    def _build_css(self):
        css = b"""
* { font-family: 'Inter Display', 'Inter Display', cursive; }
window, .nyx-bg { background-color: #000000; color: #e8edf5; }
.nyx-toolbar { background-color: rgba(10,10,18,0.96); padding: 4px 10px;
    border-bottom: 1px solid rgba(8, 12, 20, 0.12); }
.nyx-headline { color: #e8edf5; text-shadow: 0 0 10px rgba(8, 12, 20, 0.55);
    font-size: 18px; font-weight: bold; }
.nyx-meta { color: rgba(240,235,250,0.45); font-size: 12px; }
.nyx-sticky-text, .nyx-sticky-text text {
    background-color: transparent;
    background-image: none;
    color: #0f1420;
    caret-color: #0f1420;
    font-family: 'Inter Display', 'Inter Display', cursive;
    font-size: 18px;
}
.nyx-sticky-text { border: none; }
scrollbar slider { background-color: rgba(8, 12, 20, 0.30);
    border: 1px solid rgba(8, 12, 20, 0.45); border-radius: 6px;
    min-width: 8px; min-height: 8px; }
scrollbar { background-color: transparent; }
"""
        prov = Gtk.CssProvider()
        try: prov.load_from_data(css)
        except TypeError: prov.load_from_data(css.decode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _build_layout(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("nyx-bg"); self.set_child(root)
        # toolbar
        bar = Gtk.Box(spacing=10); bar.add_css_class("nyx-toolbar")
        root.append(bar)
        logo = Gtk.Label(label="🗒  Stickies"); logo.add_css_class("nyx-headline")
        bar.append(logo)
        new = SketchButton("＋ New note", width=120, height=28,
                           color=NEON_GREEN, primary=True,
                           tooltip="Create a new sticky note")
        new.connect("clicked", lambda _b: ColorPicker(self).present())
        bar.append(new)
        sp = Gtk.Box(); sp.set_hexpand(True); bar.append(sp)
        self.count_lbl = Gtk.Label(label=""); self.count_lbl.add_css_class("nyx-meta")
        bar.append(self.count_lbl)
        # canvas
        self.canvas = Canvas(self); root.append(self.canvas)
        self._refresh_count()

    def _refresh_count(self):
        n = len(self.db.list_notes())
        self.count_lbl.set_text(f"{n} note{'s' if n != 1 else ''}")

    # ── operations ─────────────────────────────────────────────────────────
    def create_note(self, color):
        adj_h = self.canvas.scroller.get_hadjustment()
        adj_v = self.canvas.scroller.get_vadjustment()
        cx = adj_h.get_value() + adj_h.get_page_size() / 2
        cy = adj_v.get_value() + adj_v.get_page_size() / 2
        nid = self.db.create(color=color, x=cx - 110, y=cy - 100)
        self.canvas.add_row(self.db.get(nid))
        self._refresh_count()
        # immediately enter inline edit mode so user can type
        sn = self.canvas.notes.get(nid)
        if sn: GLib.timeout_add(180, lambda: (sn.begin_edit(), False)[1])

    def delete_note(self, nid):
        sn = self.canvas.notes.get(nid)
        if not sn:
            self.db.delete(nid); self._refresh_count(); return
        if sn.editing: sn.end_edit()
        def done():
            try: self.canvas.fixed.remove(sn)
            except Exception: pass
            self.canvas.notes.pop(nid, None)
            self.db.delete(nid)
            self._refresh_count()
        sn.start_fade(done)

    def cycle_color(self, nid):
        row = self.db.get(nid)
        if not row: return
        keys = [c["key"] for c in NOTE_COLORS]
        i = keys.index(row["color"]) if row["color"] in keys else 0
        new = keys[(i + 1) % len(keys)]
        self.db.update(nid, color=new)
        self.canvas.update_note(nid)


# ═══════════════════════════════════════════════════════════════════════════════
#  App
# ═══════════════════════════════════════════════════════════════════════════════
class StickiesApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        try: Adw.init()
        except Exception: pass
    def do_activate(self):
        # Force dark theme to match NYXUS DARK MIRROR aesthetic
        try:
            sm = Adw.StyleManager.get_default()
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        except Exception: pass
        win = self.props.active_window or StickiesWindow(self)
        win.present()


def main():
    log.info("starting %s", APP_NAME)
    sys.exit(StickiesApp().run(sys.argv))


if __name__ == "__main__":
    main()
