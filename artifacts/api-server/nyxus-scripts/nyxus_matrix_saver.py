#!/usr/bin/env python3
# ============================================================================
# NYXUS — Alien Matrix-Rain Screensaver
# ~/.config/nyxus/nyxus_matrix_saver.py  (launched via `nyxus-screensaver`)
#
# A live GTK4/Cairo matrix rain of cryptic "alien" glyphs cascading in the
# NYXUS accent gradient (mint heads → violet/magenta trails) over a dimmed
# urban backdrop, with the clock + NYXUS wordmark floating centre.
#
# Owned + torn down by hypridle:
#     on-timeout = nyxus-screensaver &
#     on-resume  = pkill -f nyxus_matrix_saver
#
# SAFETY: the window quits on ANY key press, mouse click, or mouse motion,
# and honours SIGTERM/SIGINT — so the user can NEVER get trapped behind it.
#
# © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
import gi
import os
import sys
import time
import json
import math
import signal
import random

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio  # noqa: E402
import cairo  # noqa: E402

HOME = os.path.expanduser("~")
BACKDROP = os.path.join(HOME, ".config/eww/assets/nyxus-saver-backdrop.png")
ACCENT_JSON = os.path.join(HOME, ".config/nyxus/accent.json")

# ── accent palette (follows wallpaper accent, with safe fallback) ───────────
def _hex(h, d):
    h = (h or d).lstrip("#")
    try:
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)
    except Exception:
        h = d.lstrip("#")
        return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)

def load_accent():
    prim, sec, ok = "#7d3dff", "#ff2dad", "#39ff14"
    try:
        with open(ACCENT_JSON) as f:
            data = json.load(f)
        active = data.get("active", "wallpaper")
        pal = data.get("wallpaper" if active == "wallpaper" else "presets", {})
        if active != "wallpaper":
            pal = data.get("presets", {}).get(active, {})
        prim = pal.get("primary", prim)
        sec = pal.get("secondary", sec)
        ok = pal.get("ok", ok)
    except Exception:
        pass
    return _hex(prim, "#7d3dff"), _hex(sec, "#ff2dad"), _hex(ok, "#39ff14")

VIOLET, MAGENTA, MINT = load_accent()

# ── glyph set: Greek + math + latin + digits (all render in JetBrains Mono) ──
GLYPHS = list(
    "ΑΒΓΔΕΖΗΘΛΞΠΣΦΨΩαβγδεζηθλξπσφψωϟϞϠ"
    "0123456789"
    "∆∇∂∑∏√∞≡≈⊕⊗⊘⌀⎔⏣◇◆◈✦✧⟁⟒⌬"
    "ΛXVNYZ"
)

CELL_W = 15
CELL_H = 22
FONT_SIZE = 17
FPS_MS = 55  # ~18 fps — smooth enough, light on CPU


class Column:
    __slots__ = ("head", "speed", "length", "chars", "mutate_at")

    def __init__(self, rows):
        self.reset(rows, initial=True)

    def reset(self, rows, initial=False):
        self.head = random.uniform(-rows, 0) if initial else random.uniform(-24, -2)
        self.speed = random.uniform(0.30, 0.95)
        self.length = random.randint(8, 26)
        self.chars = {}
        self.mutate_at = 0


class MatrixArea(Gtk.DrawingArea):
    def __init__(self, on_quit):
        super().__init__()
        self.on_quit = on_quit
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_draw_func(self._draw)
        self.columns = []
        self.cols = 0
        self.rows = 0
        self._bg = None
        self._bg_size = (0, 0)
        self._src = None
        try:
            self._src = cairo.ImageSurface.create_from_png(BACKDROP)
        except Exception:
            self._src = None
        self.start = time.time()
        GLib.timeout_add(FPS_MS, self._tick)

    def _ensure_grid(self, w, h):
        cols = max(1, w // CELL_W)
        rows = max(1, h // CELL_H) + 2
        if cols != self.cols or rows != self.rows:
            self.cols, self.rows = cols, rows
            self.columns = [Column(rows) for _ in range(cols)]

    def _build_bg(self, w, h):
        surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        c = cairo.Context(surf)
        c.set_source_rgb(0.02, 0.01, 0.05)
        c.paint()
        if self._src is not None:
            sw, sh = self._src.get_width(), self._src.get_height()
            scale = max(w / sw, h / sh)
            c.save()
            c.translate((w - sw * scale) / 2, (h - sh * scale) / 2)
            c.scale(scale, scale)
            c.set_source_surface(self._src, 0, 0)
            c.get_source().set_filter(cairo.FILTER_GOOD)
            c.paint_with_alpha(0.95)
            c.restore()
        # gentle darken so glyphs stay readable but the art still shows
        c.set_source_rgba(0.02, 0.01, 0.06, 0.34)
        c.paint()
        self._bg = surf
        self._bg_size = (w, h)

    def _tick(self):
        self.queue_draw()
        return True

    def _draw(self, area, ctx, w, h):
        self._ensure_grid(w, h)
        if self._bg is None or self._bg_size != (w, h):
            self._build_bg(w, h)
        ctx.set_source_surface(self._bg, 0, 0)
        ctx.paint()

        ctx.select_font_face("JetBrainsMono Nerd Font", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(FONT_SIZE)

        for ci, col in enumerate(self.columns):
            x = ci * CELL_W + 1
            head_row = int(col.head)
            for i in range(col.length):
                row = head_row - i
                if row < 0 or row > self.rows:
                    continue
                ch = col.chars.get(row)
                if ch is None:
                    ch = random.choice(GLYPHS)
                    col.chars[row] = ch
                y = row * CELL_H + FONT_SIZE
                if i == 0:
                    ctx.set_source_rgba(MINT[0], MINT[1], MINT[2], 1.0)
                elif i == 1:
                    ctx.set_source_rgba(0.85, 1.0, 0.92, 0.95)
                else:
                    t = i / col.length
                    # blend magenta -> violet along the trail, fading out
                    r = MAGENTA[0] * (1 - t) + VIOLET[0] * t
                    g = MAGENTA[1] * (1 - t) + VIOLET[1] * t
                    b = MAGENTA[2] * (1 - t) + VIOLET[2] * t
                    a = max(0.0, (1.0 - t) * 0.85)
                    ctx.set_source_rgba(r, g, b, a)
                ctx.move_to(x, y)
                ctx.show_text(ch)

            col.head += col.speed
            col.mutate_at += 1
            if col.mutate_at >= 3:
                col.mutate_at = 0
                if col.chars:
                    rr = random.choice(list(col.chars.keys()))
                    col.chars[rr] = random.choice(GLYPHS)
            if col.head - col.length > self.rows:
                col.reset(self.rows)

        self._draw_hud(ctx, w, h)

    def _draw_hud(self, ctx, w, h):
        cx = w / 2
        cy = h / 2
        # dark plate behind HUD for legibility
        ctx.set_source_rgba(0.02, 0.01, 0.05, 0.34)
        ctx.rectangle(cx - 340, cy - 150, 680, 300)
        ctx.fill()

        # clock
        clock = time.strftime("%H:%M")
        ctx.select_font_face("Orbitron", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        ctx.set_font_size(120)
        ext = ctx.text_extents(clock)
        ctx.move_to(cx - ext.width / 2 - ext.x_bearing, cy - 10)
        ctx.set_source_rgba(MINT[0], MINT[1], MINT[2], 0.96)
        ctx.show_text(clock)

        # date
        datestr = time.strftime("%A · %B %d").upper()
        ctx.select_font_face("JetBrainsMono Nerd Font", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(18)
        ext = ctx.text_extents(datestr)
        ctx.move_to(cx - ext.width / 2 - ext.x_bearing, cy + 34)
        ctx.set_source_rgba(0.90, 0.93, 0.96, 0.80)
        ctx.show_text(datestr)

        # wordmark
        ctx.select_font_face("Permanent Marker", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(56)
        ext = ctx.text_extents("NYXUS")
        ctx.move_to(cx - ext.width / 2 - ext.x_bearing, cy + 108)
        ctx.set_source_rgba(VIOLET[0], VIOLET[1], VIOLET[2], 0.95)
        ctx.show_text("NYXUS")

        # tagline
        ctx.select_font_face("JetBrainsMono Nerd Font", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(11)
        tag = "S I L E N T   ·   D A R K   ·   P U R E L Y   F U N C T I O N A L"
        ext = ctx.text_extents(tag)
        ctx.move_to(cx - ext.width / 2 - ext.x_bearing, cy + 138)
        ctx.set_source_rgba(MAGENTA[0], MAGENTA[1], MAGENTA[2], 0.55)
        ctx.show_text(tag)


class SaverWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NYXUS Screensaver")
        self.set_decorated(False)
        self.set_default_size(1920, 1080)
        self.fullscreen()
        self._armed_at = time.time()

        area = MatrixArea(self._quit)
        self.set_child(area)

        key = Gtk.EventControllerKey()
        key.connect("key-pressed", lambda *a: self._quit())
        self.add_controller(key)

        click = Gtk.GestureClick()
        click.connect("pressed", lambda *a: self._quit())
        self.add_controller(click)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        self.add_controller(motion)
        self._last_motion = None

    def _on_motion(self, _ctrl, x, y):
        # ignore motion for the first second (map/relayout can emit spurious
        # motion that would otherwise dismiss the saver instantly), and only
        # quit on a real, sizeable pointer move.
        if time.time() - self._armed_at < 1.0:
            self._last_motion = (x, y)
            return
        if self._last_motion is None:
            self._last_motion = (x, y)
            return
        if abs(x - self._last_motion[0]) + abs(y - self._last_motion[1]) > 8:
            self._quit()

    def _quit(self, *_):
        try:
            self.get_application().quit()
        except Exception:
            os._exit(0)
        return True


def main():
    signal.signal(signal.SIGTERM, lambda *_: os._exit(0))
    signal.signal(signal.SIGINT, lambda *_: os._exit(0))
    # app-id deliberately NOT under app.nyxus.* / nyxus* so it escapes the
    # generic NYXUS window rules (float/center/size 900x650) — the saver
    # must be free to go fullscreen.
    app = Gtk.Application(application_id="com.nyxus.matrixsaver",
                          flags=Gio.ApplicationFlags.FLAGS_NONE)

    def _activate(a):
        w = SaverWindow(a)
        w.present()
        # fullscreen AFTER the surface is mapped, else wlroots ignores it
        GLib.idle_add(w.fullscreen)

    app.connect("activate", _activate)
    return app.run(None)


if __name__ == "__main__":
    sys.exit(main())
