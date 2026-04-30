#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NYXUS Stickies — minimal hand-drawn sticky notes on a dark canvas.

Just the notes. Nothing else.

  • Tilted Cairo-rendered sticky notes (yellow, pink, blue, green,
    orange, purple, white) with subtle drop shadow and folded corner
  • Click to select, double-click (or click ✎) to edit, drag to move
  • Small color dot top-left to change color, X top-right to delete
  • Save button to commit edits
  • Auto-saved to ~/.config/nyxus-stickies/notes.db (sqlite3)
  • NYXUS dark theme + Caveat handwritten font
"""
from __future__ import annotations

import logging
import math
import os
import random
import sqlite3
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Tuple

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, GObject, Gio, Pango, PangoCairo  # noqa: E402
import cairo  # noqa: E402

# ── paths ────────────────────────────────────────────────────────────────────
APP_ID    = "com.nyxus.stickies"
APP_NAME  = "NYXUS Stickies"
WIN_W, WIN_H = 1000, 680

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

# ── NYXUS palette (matches notepad) ──────────────────────────────────────────
BG_DEEP    = (0.039, 0.039, 0.071)   # #0a0a12
INK_BRIGHT = (0.94, 0.92, 0.97)
INK_DIM    = (0.62, 0.59, 0.72)
INK_FAINT  = (0.32, 0.30, 0.42)
NEON_PINK  = (1.0,  0.0,  1.0)
NEON_BLUE  = (0.0,  0.53, 1.0)
NEON_GREEN = (0.22, 1.0,  0.08)
DANGER_RED = (1.0,  0.27, 0.40)

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
#  Sketch helpers (seeded jitter)
# ═══════════════════════════════════════════════════════════════════════════════
def _seed(*parts):
    import hashlib
    h = hashlib.md5(repr(parts).encode("utf-8")).digest()
    return random.Random(int.from_bytes(h[:8], "big"))


def sketch_line(cr, x1, y1, x2, y2, *, jitter=0.6, segments=10, key=None):
    rng = _seed(key or ("ln", round(x1,1), round(y1,1), round(x2,1), round(y2,1)))
    n = max(2, segments)
    cr.move_to(x1, y1)
    for i in range(1, n):
        t = i / (n - 1)
        x = x1 + (x2 - x1) * t + (rng.random() - 0.5) * jitter
        y = y1 + (y2 - y1) * t + (rng.random() - 0.5) * jitter
        cr.line_to(x, y)
    cr.line_to(x2, y2); cr.stroke()


def sketch_rect(cr, x, y, w, h, *, jitter=0.6, key=None):
    k = key or ("rc", round(x), round(y), round(w), round(h))
    sketch_line(cr, x,   y,   x+w, y,   jitter=jitter, key=(k, "t"))
    sketch_line(cr, x+w, y,   x+w, y+h, jitter=jitter, key=(k, "r"))
    sketch_line(cr, x+w, y+h, x,   y+h, jitter=jitter, key=(k, "b"))
    sketch_line(cr, x,   y+h, x,   y,   jitter=jitter, key=(k, "l"))


def draw_caveat(cr, x, y, text, *, size=15, color=(0,0,0,0.95),
                family="Caveat", weight=Pango.Weight.NORMAL, wrap_w=None):
    cr.save(); cr.set_source_rgba(*color)
    layout = PangoCairo.create_layout(cr)
    fd = Pango.FontDescription()
    fd.set_family(family); fd.set_size(int(size * Pango.SCALE))
    fd.set_weight(weight); layout.set_font_description(fd)
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
#  Sketch button
# ═══════════════════════════════════════════════════════════════════════════════
class SketchButton(Gtk.DrawingArea):
    __gsignals__ = {"clicked": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, label, *, width=78, height=26, color=NEON_PINK,
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
        gc.connect("pressed",  self._press_cb)
        gc.connect("released", self._release_cb)
        self.add_controller(gc)
        mc = Gtk.EventControllerMotion()
        mc.connect("enter", lambda *a: (setattr(self,"_hover",True), self.queue_draw()))
        mc.connect("leave", lambda *a: (setattr(self,"_hover",False),
                                        setattr(self,"_press",False), self.queue_draw()))
        self.add_controller(mc)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

    def _press_cb(self, *a):  self._press = True;  self.queue_draw()
    def _release_cb(self, *a):
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
        fd.set_family("Caveat"); fd.set_size(int(13 * Pango.SCALE))
        fd.set_weight(Pango.Weight.BOLD if self.primary else Pango.Weight.NORMAL)
        layout.set_font_description(fd); layout.set_text(self.label, -1)
        tw, th = layout.get_pixel_size()
        cr.set_source_rgba(*INK_BRIGHT, 1.0 if self._hover else 0.92)
        cr.move_to((w-tw)/2, (h-th)/2); PangoCairo.show_layout(cr, layout)


# ═══════════════════════════════════════════════════════════════════════════════
#  Sticky note widget
# ═══════════════════════════════════════════════════════════════════════════════
class StickyNote(Gtk.DrawingArea):
    """Cairo-rendered tilted sticky note with X / color-dot buttons."""
    __gsignals__ = {
        "request-edit":   (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "moved":          (GObject.SignalFlags.RUN_FIRST, None, (str, float, float)),
        "selected":       (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "delete":         (GObject.SignalFlags.RUN_FIRST, None, (str,)),
        "color-cycle":    (GObject.SignalFlags.RUN_FIRST, None, (str,)),
    }

    PADDING = 16

    def __init__(self, note: sqlite3.Row):
        super().__init__()
        self.nid  = note["id"]
        self.note = dict(note)
        self.tilt = float(note["tilt"] or 0)
        self.w    = float(note["w"]); self.h = float(note["h"])
        self.dragging = False
        self.hover    = False
        self.selected = False
        self.lift     = 0.0
        self.entrance = 0.0
        self.fade     = 1.0; self.crumple = 0.0
        self._press_x = 0.0; self._press_y = 0.0
        self._last_click_t = 0.0
        self._anim = None
        self._refresh_size()
        self.set_draw_func(self._draw)

        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("pressed",  self._press)
        gc.connect("released", self._release)
        self.add_controller(gc)
        mc = Gtk.EventControllerMotion()
        mc.connect("enter", self._enter); mc.connect("leave", self._leave)
        self.add_controller(mc)
        # entrance
        def step():
            self.entrance += 0.10
            if self.entrance >= 1: self.entrance = 1; self.queue_draw(); return False
            self.queue_draw(); return True
        GLib.timeout_add(16, step)

    def update_from_row(self, n):
        self.note = dict(n); self.tilt = float(n["tilt"] or 0)
        self.w = float(n["w"]); self.h = float(n["h"])
        self._refresh_size(); self.queue_draw()

    def _refresh_size(self):
        slop = 36 + abs(math.sin(math.radians(self.tilt))) * max(self.w, self.h)
        wx = int(self.w + slop * 2); wy = int(self.h + slop * 2)
        self.set_size_request(wx, wy)
        try: self.set_content_width(wx); self.set_content_height(wy)
        except Exception: pass

    def _set_lift(self, target):
        if self._anim:
            try: GLib.source_remove(self._anim)
            except Exception: pass
        def step():
            d = target - self.lift
            if abs(d) < 0.02: self.lift = target; self.queue_draw(); return False
            self.lift += d * 0.25; self.queue_draw(); return True
        self._anim = GLib.timeout_add(16, step)

    def start_fade(self, on_done):
        def step():
            self.crumple += 0.08; self.fade = max(0.0, 1.0 - self.crumple)
            if self.crumple >= 1: on_done(); return False
            self.queue_draw(); return True
        GLib.timeout_add(16, step)

    # ── transforms ──────────────────────────────────────────────────────────
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
        return math.hypot(nx - (self.w - 14), ny - 14) <= 11

    def _hits_color(self, lx, ly):
        nx, ny = self._local_to_note(lx, ly)
        return math.hypot(nx - 14, ny - 14) <= 9

    # ── events ──────────────────────────────────────────────────────────────
    def _enter(self, *a):
        self.hover = True; self._set_lift(1.0)
    def _leave(self, *a):
        self.hover = False; self._set_lift(0.0)

    def _press(self, ctrl, n, x, y):
        if not self._hits_note(x, y): return
        if self._hits_close(x, y):
            self.emit("delete", self.nid); return
        if self._hits_color(x, y):
            self.emit("color-cycle", self.nid); return
        # double-click → edit
        now = time.monotonic()
        if now - self._last_click_t < 0.35:
            self.emit("request-edit", self.nid)
            self._last_click_t = 0; return
        self._last_click_t = now
        self.emit("selected", self.nid)
        self.dragging = True; self._press_x = x; self._press_y = y
        self._drag_extra = random.uniform(-3, 3); self.tilt += self._drag_extra
        self.queue_draw()

    def _release(self, ctrl, n, x, y):
        if self.dragging:
            self.dragging = False
            self.tilt -= getattr(self, "_drag_extra", 0)
            self.emit("moved", self.nid, x - self._press_x, y - self._press_y)
            self.queue_draw()

    # ── draw ────────────────────────────────────────────────────────────────
    def _color_rgb(self):
        c = COLOR_BY_KEY.get(self.note["color"], COLOR_BY_KEY["yellow"])
        return c["rgb"]
    def _shadow_rgb(self):
        c = COLOR_BY_KEY.get(self.note["color"], COLOR_BY_KEY["yellow"])
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
        # shadow
        sh_off = 4 + 6 * self.lift
        cr.set_source_rgba(0, 0, 0, 0.45 * self.fade)
        cr.rectangle(sh_off, sh_off, self.w, self.h); cr.fill()
        cr.set_source_rgba(*sh, 0.30 * self.fade)
        cr.rectangle(sh_off+1, sh_off+1, self.w, self.h); cr.fill()
        # body
        cr.set_source_rgba(*col, self.fade)
        cr.rectangle(0, 0, self.w, self.h); cr.fill()
        # paper noise
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

        # color dot (top-left button)
        cr.save()
        cr.set_source_rgba(*col, 0.95)
        cr.arc(14, 14, 8, 0, math.pi*2); cr.fill()
        cr.set_source_rgba(0, 0, 0, 0.7); cr.set_line_width(1.2)
        cr.arc(14, 14, 8, 0, math.pi*2); cr.stroke()
        cr.restore()

        # close X (top-right button)
        cr.save()
        close_alpha = 0.8 if self.hover else 0.45
        cr.set_source_rgba(*DANGER_RED, close_alpha * 0.3)
        cr.arc(self.w - 14, 14, 10, 0, math.pi*2); cr.fill()
        cr.set_source_rgba(0, 0, 0, close_alpha)
        cr.set_line_width(1.6); cr.set_line_cap(cairo.LINE_CAP_ROUND)
        sketch_line(cr, self.w-19, 9,  self.w-9, 19, jitter=0.4,
                    key=("x1", self.nid))
        sketch_line(cr, self.w-9,  9,  self.w-19, 19, jitter=0.4,
                    key=("x2", self.nid))
        cr.restore()

        # body text
        text_color = (0.10, 0.08, 0.14, 0.95 * self.fade)
        body = self.note.get("body") or "(double-click to write…)"
        is_placeholder = not (self.note.get("body") or "").strip()
        if is_placeholder:
            text_color = (0.10, 0.08, 0.14, 0.45 * self.fade)
        draw_caveat(cr, self.PADDING, self.PADDING + 14, body,
                    size=16, color=text_color,
                    wrap_w=self.w - self.PADDING * 2)

        # selection halo
        if self.selected:
            cr.set_source_rgba(*NEON_PINK, 0.85); cr.set_line_width(2.4)
            sketch_rect(cr, -4, -4, self.w + 8, self.h + 8, jitter=0.9,
                        key=("sel", self.nid))
        cr.restore()


# ═══════════════════════════════════════════════════════════════════════════════
#  Edit popover
# ═══════════════════════════════════════════════════════════════════════════════
class NoteEditor(Gtk.Window):
    def __init__(self, win, nid):
        super().__init__(transient_for=win, title="edit note")
        self.win = win; self.nid = nid
        self.set_default_size(400, 320); self.set_modal(True)
        row = win.db.get(nid)
        if not row: GLib.idle_add(self.close); return

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_start(14); outer.set_margin_end(14)
        outer.set_margin_top(14);   outer.set_margin_bottom(14)
        self.set_child(outer)

        sw = Gtk.ScrolledWindow(); sw.set_hexpand(True); sw.set_vexpand(True)
        outer.append(sw)
        self.tv = Gtk.TextView(); self.tv.add_css_class("nyx-editor")
        self.tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.buf = self.tv.get_buffer(); self.buf.set_text(row["body"] or "")
        sw.set_child(self.tv)

        btns = Gtk.Box(spacing=8); outer.append(btns)
        save = SketchButton("💾 Save", width=110, height=28,
                            color=NEON_GREEN, primary=True)
        save.connect("clicked", lambda _b: self._save())
        cancel = SketchButton("Cancel", width=88, height=28, color=INK_DIM)
        cancel.connect("clicked", lambda _b: self.close())
        btns.append(save); btns.append(cancel)

    def _save(self):
        body = self.buf.get_text(self.buf.get_start_iter(),
                                 self.buf.get_end_iter(), False)
        self.win.db.update(self.nid, body=body)
        self.win.canvas.update_note(self.nid)
        self.close()


# ═══════════════════════════════════════════════════════════════════════════════
#  Color picker (for "New note")
# ═══════════════════════════════════════════════════════════════════════════════
class ColorPicker(Gtk.Window):
    def __init__(self, win):
        super().__init__(transient_for=win, title="pick color")
        self.win = win
        self.set_default_size(360, -1); self.set_modal(True)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_margin_start(16); outer.set_margin_end(16)
        outer.set_margin_top(16); outer.set_margin_bottom(16)
        self.set_child(outer)
        outer.append(Gtk.Label(label="choose a color for your new note",
                               xalign=0))
        flow = Gtk.FlowBox(); flow.set_max_children_per_line(7)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        outer.append(flow)
        for c in NOTE_COLORS:
            btn = Gtk.Button()
            da = Gtk.DrawingArea()
            da.set_size_request(44, 44)
            da.set_content_width(44); da.set_content_height(44)
            def make_draw(rgb, name):
                def _d(area, cr, w, h, _=None):
                    cr.set_source_rgba(0, 0, 0, 0.4)
                    cr.rectangle(6, 6, w-10, h-10); cr.fill()
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
#  Canvas
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

        # click on bg to deselect
        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("pressed", self._bg_click)
        self.bg.add_controller(gc)

    def _bg_click(self, *a):
        for sn in self.notes.values():
            sn.selected = False; sn.queue_draw()

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
        sn.connect("request-edit", lambda _w, nid: self.win.open_editor(nid))
        sn.connect("moved",        self._on_moved)
        sn.connect("selected",     self._on_selected)
        sn.connect("delete",       lambda _w, nid: self.win.delete_note(nid))
        sn.connect("color-cycle",  lambda _w, nid: self.win.cycle_color(nid))
        ax = float(n["x"]) - (sn.get_size_request()[0] - sn.w) / 2
        ay = float(n["y"]) - (sn.get_size_request()[1] - sn.h) / 2
        self.fixed.put(sn, int(ax), int(ay))

    def update_note(self, nid):
        sn = self.notes.get(nid)
        if not sn: return
        row = self.win.db.get(nid)
        if not row: return
        sn.update_from_row(row)
        ax = float(row["x"]) - (sn.get_size_request()[0] - sn.w) / 2
        ay = float(row["y"]) - (sn.get_size_request()[1] - sn.h) / 2
        self.fixed.move(sn, int(ax), int(ay))

    def remove_note(self, nid):
        sn = self.notes.pop(nid, None)
        if sn:
            try: self.fixed.remove(sn)
            except Exception: pass

    def _on_moved(self, sn, nid, dx, dy):
        row = self.win.db.get(nid)
        if not row: return
        nx = float(row["x"]) + dx; ny = float(row["y"]) + dy
        self.win.db.update(nid, x=nx, y=ny); self.update_note(nid)

    def _on_selected(self, sn, nid):
        for k, w in self.notes.items():
            w.selected = (k == nid); w.queue_draw()

    # dark canvas with subtle dots
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

    def _build_css(self):
        css = b"""
* { font-family: 'Caveat', 'Patrick Hand', cursive; }
window, .nyx-bg { background-color: #0a0a12; color: #f0eef8; }
.nyx-toolbar { background-color: rgba(10,10,18,0.96); padding: 4px 10px;
    border-bottom: 1px solid rgba(255,0,255,0.12); }
.nyx-headline { color: #ff00ff; text-shadow: 0 0 10px rgba(255,0,255,0.55);
    font-size: 18px; font-weight: bold; }
.nyx-meta { color: rgba(240,235,250,0.45); font-size: 12px; }
.nyx-editor textview, .nyx-editor text {
    background-color: transparent; color: rgba(240,235,250,0.95);
    font-family: 'Caveat', cursive; font-size: 18px;
    padding: 6px 10px; caret-color: #ff00ff; }
scrollbar slider { background-color: rgba(255,0,255,0.30);
    border: 1px solid rgba(255,0,255,0.45); border-radius: 6px;
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
        new.connect("clicked", lambda _b: self.show_color_picker())
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
    def show_color_picker(self):
        ColorPicker(self).present()

    def create_note(self, color):
        adj_h = self.canvas.scroller.get_hadjustment()
        adj_v = self.canvas.scroller.get_vadjustment()
        cx = adj_h.get_value() + adj_h.get_page_size() / 2
        cy = adj_v.get_value() + adj_v.get_page_size() / 2
        nid = self.db.create(color=color, x=cx - 110, y=cy - 100)
        self.canvas.add_row(self.db.get(nid))
        self._refresh_count()

    def open_editor(self, nid):
        NoteEditor(self, nid).present()

    def delete_note(self, nid):
        sn = self.canvas.notes.get(nid)
        if not sn:
            self.db.delete(nid); self._refresh_count(); return
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
class StickiesApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
    def do_activate(self):
        win = self.props.active_window or StickiesWindow(self)
        win.present()


def main():
    log.info("starting %s", APP_NAME)
    sys.exit(StickiesApp().run(sys.argv))


if __name__ == "__main__":
    main()
