#!/usr/bin/env python3
"""
NYXUS cosmic scene backgrounds (rev 2026-07-12).
One-of-a-kind deep-space scenes for NYXUS GTK apps: milky way, twin moons,
black hole accretion disk, diamond star fields. Drop behind glass cards so
the UI stays as clean as the desktop galaxy wallpaper.
"""
import math
import random
import time
from pathlib import Path

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

CACHE = Path.home() / ".cache" / "nyxus" / "cosmic"
SCENES = ("milky_way", "twin_moons", "black_hole", "diamond_field", "nebula_moon")


def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255


def _stars(seed, n, w, h, y_max=1.0):
    rs = random.Random(seed)
    out = []
    for _ in range(n):
        out.append({
            "x": rs.random() * w,
            "y": rs.random() * h * y_max,
            "r": 0.35 + rs.random() * (2.8 if rs.random() > 0.92 else 1.1),
            "br": 0.45 + rs.random() * 0.55,
            "sp": rs.random() * math.tau,
            "spd": 0.4 + rs.random() * 1.6,
        })
    return out


class CosmicSceneArea(Gtk.DrawingArea):
    """Animated cosmic backdrop. scene selects the vista."""

    def __init__(self, scene: str = "milky_way"):
        super().__init__()
        self.scene = scene if scene in SCENES else "milky_way"
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_can_focus(False)
        self.set_can_target(False)
        self._t0 = time.monotonic()
        self._stars = _stars(abs(hash(self.scene)), 180, 1, 1)
        GLib.timeout_add(50, self._tick)
        self.set_draw_func(self._draw, None)

    def _tick(self):
        self.queue_draw()
        return True

    def _void(self, cr, w, h):
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0.0, 0.008, 0.004, 0.022)
        g.add_color_stop_rgb(0.5, 0.012, 0.006, 0.032)
        g.add_color_stop_rgb(1.0, 0.004, 0.002, 0.014)
        cr.set_source(g)
        cr.paint()

    def _paint_stars(self, cr, w, h, t, y_cap=0.98, diamond=False):
        for s in self._stars:
            tw = 0.55 + 0.45 * math.sin(t * s["spd"] + s["sp"])
            a = s["br"] * tw
            x, y = s["x"] * w, s["y"] * h * y_cap
            r = s["r"]
            cr.set_source_rgba(1, 1, 1, a * 0.85)
            cr.arc(x, y, max(0.4, r * 0.45), 0, math.tau)
            cr.fill()
            if diamond and r > 1.4 and a > 0.65:
                cr.set_line_width(0.8)
                cr.set_source_rgba(1, 1, 1, a * 0.55)
                ln = r * 4.5
                cr.move_to(x - ln, y); cr.line_to(x + ln, y); cr.stroke()
                cr.move_to(x, y - ln * 0.7); cr.line_to(x, y + ln * 0.7); cr.stroke()

    def _milky_way(self, cr, w, h, t):
        self._void(cr, w, h)
        # galactic band
        cx, cy = w * 0.52, h * 0.48
        for i, (col, a) in enumerate([
            ("#7949f2", 0.10), ("#26ffb7", 0.06), ("#ff2667", 0.05), ("#ffffff", 0.04)]):
            r, g, b = _rgb(col)
            ang = -0.35 + 0.04 * math.sin(t * 0.07)
            gx = cx + math.cos(ang) * w * 0.35
            gy = cy + math.sin(ang) * h * 0.12
            grad = cairo.RadialGradient(gx, gy, 0, gx, gy, min(w, h) * 0.75)
            grad.add_color_stop_rgba(0, r, g, b, a)
            grad.add_color_stop_rgba(1, r, g, b, 0)
            cr.set_source(grad)
            cr.paint()
        self._paint_stars(cr, w, h, t, diamond=True)

    def _twin_moons(self, cr, w, h, t):
        self._void(cr, w, h)
        self._paint_stars(cr, w, h, t, y_cap=0.72, diamond=True)
        for frac, phase, rad in [(0.28, 0.0, 0.11), (0.68, 1.2, 0.08)]:
            mx, my = w * frac, h * (0.28 + 0.02 * math.sin(t * 0.15 + phase))
            rr = min(w, h) * rad
            glow = cairo.RadialGradient(mx, my, rr * 0.7, mx, my, rr * 1.8)
            glow.add_color_stop_rgba(0, 1, 1, 1, 0.0)
            glow.add_color_stop_rgba(0.7, 0.85, 0.88, 1.0, 0.08)
            glow.add_color_stop_rgba(1, 0.7, 0.75, 0.95, 0)
            cr.set_source(glow)
            cr.arc(mx, my, rr * 1.8, 0, math.tau)
            cr.fill()
            body = cairo.RadialGradient(mx - rr * 0.25, my - rr * 0.25, rr * 0.05, mx, my, rr)
            body.add_color_stop_rgb(0.0, 0.92, 0.93, 0.96)
            body.add_color_stop_rgb(0.55, 0.55, 0.58, 0.65)
            body.add_color_stop_rgb(1.0, 0.18, 0.16, 0.22)
            cr.set_source(body)
            cr.arc(mx, my, rr, 0, math.tau)
            cr.fill()

    def _black_hole(self, cr, w, h, t):
        self._void(cr, w, h)
        self._paint_stars(cr, w, h, t, diamond=True)
        cx, cy = w * 0.5, h * 0.46
        rr = min(w, h) * 0.14
        # accretion disk
        for ring, col, width, alpha in [
            (1.55, "#ffb026", 5, 0.55), (1.35, "#ff7849", 3, 0.45),
            (1.18, "#ff2667", 2, 0.35), (1.02, "#7949f2", 1.5, 0.25)]:
            cr.set_line_width(width)
            r, g, b = _rgb(col)
            cr.set_source_rgba(r, g, b, alpha * (0.85 + 0.15 * math.sin(t * 0.9 + ring)))
            cr.arc(cx, cy, rr * ring, 0, math.tau)
            cr.stroke()
        # event horizon
        cr.set_source_rgb(0, 0, 0)
        cr.arc(cx, cy, rr * 0.98, 0, math.tau)
        cr.fill()
        lens = cairo.RadialGradient(cx, cy, rr * 0.9, cx, cy, rr * 1.25)
        lens.add_color_stop_rgba(0, 0, 0, 0, 0)
        lens.add_color_stop_rgba(0.6, 1, 0.6, 0.3, 0.12)
        lens.add_color_stop_rgba(1, 0, 0, 0, 0)
        cr.set_source(lens)
        cr.arc(cx, cy, rr * 1.3, 0, math.tau)
        cr.fill()

    def _diamond_field(self, cr, w, h, t):
        g = cairo.LinearGradient(0, 0, 0, h)
        g.add_color_stop_rgb(0.0, 0.004, 0.002, 0.010)
        g.add_color_stop_rgb(1.0, 0.002, 0.001, 0.006)
        cr.set_source(g)
        cr.paint()
        self._paint_stars(cr, w, h, t, diamond=True)

    def _nebula_moon(self, cr, w, h, t):
        self._void(cr, w, h)
        # violet-teal nebula wash
        for col, bx, by, rad in [("#7949f2", 0.2, 0.35, 0.5), ("#26ffb7", 0.75, 0.55, 0.45)]:
            r, g, b = _rgb(col)
            cx, cy = w * bx, h * by
            grad = cairo.RadialGradient(cx, cy, 0, cx, cy, min(w, h) * rad)
            grad.add_color_stop_rgba(0, r, g, b, 0.09)
            grad.add_color_stop_rgba(1, r, g, b, 0)
            cr.set_source(grad)
            cr.paint()
        self._paint_stars(cr, w, h, t, y_cap=0.8, diamond=True)
        mx, my = w * 0.72, h * 0.22
        rr = min(w, h) * 0.09
        cr.set_source_rgb(0.88, 0.90, 0.95)
        cr.arc(mx, my, rr, 0, math.tau)
        cr.fill()

    def _draw(self, _a, cr, w, h, _u):
        t = time.monotonic() - self._t0
        if self.scene == "milky_way":
            self._milky_way(cr, w, h, t)
        elif self.scene == "twin_moons":
            self._twin_moons(cr, w, h, t)
        elif self.scene == "black_hole":
            self._black_hole(cr, w, h, t)
        elif self.scene == "nebula_moon":
            self._nebula_moon(cr, w, h, t)
        else:
            self._diamond_field(cr, w, h, t)


# Per-app scene picks (here and there - not every surface)
APP_SCENES = {
    "_home": "milky_way",
    "_start": "twin_moons",
    "_notepad": "diamond_field",
    "_stickies": "nebula_moon",
    "_sysmon": "black_hole",
    "_control": "black_hole",
    "_terminal": "diamond_field",
    "display": "nebula_moon",
    "wallpaper": "milky_way",
    "about": "twin_moons",
}


def scene_for(page_key: str) -> str:
    return APP_SCENES.get(page_key, "diamond_field")


def wrap_with_cosmic(child: Gtk.Widget, page_key: str = "_home") -> Gtk.Overlay:
    overlay = Gtk.Overlay()
    overlay.set_child(CosmicSceneArea(scene_for(page_key)))
    overlay.add_overlay(child)
    return overlay
