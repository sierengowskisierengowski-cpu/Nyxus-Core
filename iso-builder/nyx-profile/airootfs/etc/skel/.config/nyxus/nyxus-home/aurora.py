"""
NYXUS Home — OBSIDIAN REACTOR animated background (rev r2 · 2026-07-12)
Layered live Cairo scene: void wash → drifting aurora plasma → parallax
starfield → perspective grid floor → scanline sweep → corner HUD frame.
Everything is time-driven (no random per-frame jitter) so it renders
deterministically and cheaply at 20 fps.
(c) 2026 Joseph A. Sierengowski - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
import math
import random
import time

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

from style import PALETTE  # noqa: E402


def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255


# ── deterministic star layout ────────────────────────────────────────
_rs = random.Random(20260712)
STARS = [
    {
        "x": _rs.random(),            # fraction of width
        "y": _rs.random() * 0.92,     # keep off the grid floor
        "r": 0.4 + _rs.random() * 1.3,
        "phase": _rs.random() * math.tau,
        "speed": 0.35 + _rs.random() * 1.4,   # twinkle rate
        "drift": 0.5 + _rs.random() * 1.5,    # parallax factor
        "tint": _rs.choice(["#e8edf5", "#e8edf5", "#e8edf5",
                            "#7d3dff", "#39ff14", "#ff2d55"]),
    }
    for _ in range(140)
]

# aurora plasma blobs: (palette key, orbit-x amp, orbit-y amp, period s,
#                       base cx, base cy, radius frac)
BLOBS = [
    ("pink",   0.10, 0.06, 47.0, 0.18, 0.22, 0.42),
    ("purple", 0.12, 0.08, 61.0, 0.82, 0.18, 0.46),
    ("cyan",   0.08, 0.10, 53.0, 0.55, 0.75, 0.40),
    ("gold",   0.06, 0.05, 71.0, 0.12, 0.85, 0.30),
]


class AuroraArea(Gtk.DrawingArea):
    """Animated reactor backdrop. 20 fps, pure function of wall time."""

    def __init__(self):
        super().__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_can_focus(False)
        self.set_can_target(False)
        self.set_draw_func(self._draw, None)
        self._t0 = time.monotonic()
        GLib.timeout_add(50, self._tick)

    def _tick(self):
        self.queue_draw()
        return True

    # ── layers ────────────────────────────────────────────────────────
    def _draw(self, _a, cr, w, h, _u):
        t = time.monotonic() - self._t0

        # 1 · void wash
        base = cairo.LinearGradient(0, 0, 0, h)
        base.add_color_stop_rgb(0.0, 0.010, 0.004, 0.030)
        base.add_color_stop_rgb(0.55, 0.016, 0.008, 0.045)
        base.add_color_stop_rgb(1.0, 0.006, 0.002, 0.020)
        cr.set_source(base)
        cr.paint()

        # 2 · aurora plasma (slow orbiting radial blobs)
        for key, ax, ay, period, bx, by, rad in BLOBS:
            r, g, b = _rgb(PALETTE[key])
            ang = math.tau * (t / period)
            cx = (bx + ax * math.sin(ang)) * w
            cy = (by + ay * math.cos(ang * 0.8)) * h
            rr = rad * min(w, h)
            # breathing intensity
            breath = 0.055 + 0.02 * math.sin(ang * 1.7 + bx * 9)
            grad = cairo.RadialGradient(cx, cy, 0, cx, cy, rr)
            grad.add_color_stop_rgba(0, r, g, b, breath)
            grad.add_color_stop_rgba(0.6, r, g, b, breath * 0.45)
            grad.add_color_stop_rgba(1, r, g, b, 0)
            cr.set_source(grad)
            cr.rectangle(cx - rr, cy - rr, 2 * rr, 2 * rr)
            cr.fill()

        # 3 · starfield with parallax drift + twinkle
        for s in STARS:
            x = ((s["x"] + t * 0.0015 * s["drift"]) % 1.04 - 0.02) * w
            y = s["y"] * h
            tw = 0.5 + 0.5 * math.sin(t * s["speed"] + s["phase"])
            a = 0.10 + 0.55 * tw * tw
            r, g, b = _rgb(s["tint"])
            cr.set_source_rgba(r, g, b, a)
            cr.arc(x, y, s["r"], 0, math.tau)
            cr.fill()
            if s["r"] > 1.3 and tw > 0.86:      # sparkle cross on the big ones
                cr.set_source_rgba(r, g, b, a * 0.5)
                cr.set_line_width(0.7)
                L = s["r"] * 4
                cr.move_to(x - L, y); cr.line_to(x + L, y)
                cr.move_to(x, y - L); cr.line_to(x, y + L)
                cr.stroke()

        # 4 · perspective grid floor (bottom 22%)
        gy = h * 0.78
        r, g, b = _rgb(PALETTE["pink"])
        # horizon glow
        hg = cairo.LinearGradient(0, gy - 30, 0, gy + 8)
        hg.add_color_stop_rgba(0, r, g, b, 0)
        hg.add_color_stop_rgba(1, r, g, b, 0.13)
        cr.set_source(hg)
        cr.rectangle(0, gy - 30, w, 38)
        cr.fill()
        cr.set_line_width(1)
        # radial lines from vanishing point
        vx = w / 2
        for i in range(-14, 15):
            cr.set_source_rgba(r, g, b, 0.05 + 0.03 * (1 - abs(i) / 14))
            cr.move_to(vx, gy)
            cr.line_to(vx + i * w * 0.12, h + 20)
            cr.stroke()
        # scrolling horizontal lines (accelerating toward viewer)
        scroll = (t * 0.35) % 1.0
        for k in range(10):
            f = ((k + scroll) / 10.0) ** 2.2
            y = gy + f * (h - gy)
            cr.set_source_rgba(r, g, b, 0.03 + 0.14 * f)
            cr.move_to(0, y)
            cr.line_to(w, y)
            cr.stroke()

        # 5 · scanline sweep (a slow bright band falling down the screen)
        sy = (t * 26.0) % (h + 240) - 120
        band = cairo.LinearGradient(0, sy - 90, 0, sy + 90)
        band.add_color_stop_rgba(0.0, 1, 1, 1, 0)
        band.add_color_stop_rgba(0.5, 1, 1, 1, 0.022)
        band.add_color_stop_rgba(1.0, 1, 1, 1, 0)
        cr.set_source(band)
        cr.rectangle(0, sy - 90, w, 180)
        cr.fill()

        # 6 · fine static scanlines
        cr.set_source_rgba(0, 0, 0, 0.10)
        cr.set_line_width(1)
        y = 0
        while y < h:
            cr.move_to(0, y)
            cr.line_to(w, y)
            cr.stroke()
            y += 4

        # 7 · vignette
        vg = cairo.RadialGradient(w / 2, h / 2, min(w, h) * 0.35,
                                  w / 2, h / 2, max(w, h) * 0.75)
        vg.add_color_stop_rgba(0, 0, 0, 0, 0)
        vg.add_color_stop_rgba(1, 0, 0, 0, 0.42)
        cr.set_source(vg)
        cr.paint()

        # 8 · corner HUD brackets (breathing)
        pulse = 0.35 + 0.20 * math.sin(t * 1.4)
        cr.set_source_rgba(r, g, b, pulse)
        cr.set_line_width(1.5)
        L = 34
        for cx, cy, sx, sy_ in ((14, 14, 1, 1), (w - 14, 14, -1, 1),
                                (14, h - 14, 1, -1), (w - 14, h - 14, -1, -1)):
            cr.move_to(cx + sx * L, cy)
            cr.line_to(cx, cy)
            cr.line_to(cx, cy + sy_ * L)
            cr.stroke()
