"""
NYXUS Home — HERO strip (rev r1 · 2026-07-12)
Command-deck masthead: giant neon clock w/ Cairo seconds arc, live date,
host / kernel / uptime readout, and a one-line Open-Meteo weather pull.
(c) 2026 Joseph Sierengowski - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import datetime as _dt
import json
import math
import os
import platform
import socket
import threading
import time
import urllib.parse
import urllib.request

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

from style import PALETTE  # noqa: E402
from hud import _rgb  # noqa: E402
from widgets import WEATHER_FILE, WX_CODES  # noqa: E402


class SecondsRing(Gtk.DrawingArea):
    """Thin neon arc that sweeps once per minute, smooth at 20 fps."""

    def __init__(self, size=118):
        super().__init__()
        self.set_content_width(size)
        self.set_content_height(size)
        self.set_draw_func(self._draw)
        GLib.timeout_add(50, lambda: (self.queue_draw(), True)[1])

    def _draw(self, _a, cr, w, h):
        now = time.time()
        frac = (now % 60) / 60.0
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 6
        r, g, b = _rgb(PALETTE["cyan"])
        # track
        cr.set_source_rgba(r, g, b, 0.12)
        cr.set_line_width(2)
        cr.arc(cx, cy, radius, 0, math.tau)
        cr.stroke()
        # minute ticks
        cr.set_source_rgba(1, 1, 1, 0.15)
        for i in range(12):
            a = math.tau * i / 12 - math.pi / 2
            cr.move_to(cx + math.cos(a) * (radius - 4),
                       cy + math.sin(a) * (radius - 4))
            cr.line_to(cx + math.cos(a) * radius,
                       cy + math.sin(a) * radius)
            cr.stroke()
        # sweep
        start = -math.pi / 2
        end = start + math.tau * frac
        for lw, alpha in ((7, 0.10), (2.5, 0.95)):
            cr.set_source_rgba(r, g, b, alpha)
            cr.set_line_width(lw)
            cr.arc(cx, cy, radius, start, end)
            cr.stroke()
        # tip
        tx = cx + math.cos(end) * radius
        ty = cy + math.sin(end) * radius
        cr.set_source_rgba(1, 1, 1, 0.95)
        cr.arc(tx, ty, 2.6, 0, math.tau)
        cr.fill()
        # seconds digits in the middle
        sec = int(now % 60)
        cr.set_source_rgba(r, g, b, 0.9)
        cr.select_font_face("JetBrains Mono")
        cr.set_font_size(26)
        text = f"{sec:02d}"
        ext = cr.text_extents(text)
        cr.move_to(cx - ext.width / 2, cy + ext.height / 2)
        cr.show_text(text)


class HeroStrip:
    def __init__(self):
        self.root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                            spacing=26)
        self.root.add_css_class("ghost-card")
        self.root.set_margin_start(8)
        self.root.set_margin_end(8)

        # left: brand + giant clock
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        tag = Gtk.Label(label="NYXUS · OBSIDIAN REACTOR · SUPER+0 · HOME",
                        xalign=0.0)
        tag.add_css_class("hero-tag")
        left.append(tag)
        clock_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                            spacing=16)
        self.time_lbl = Gtk.Label(xalign=0.0)
        self.time_lbl.set_use_markup(True)
        self.time_lbl.add_css_class("hero-time")
        clock_row.append(self.time_lbl)
        ring = SecondsRing()
        ring.set_valign(Gtk.Align.CENTER)
        clock_row.append(ring)
        left.append(clock_row)
        self.date_lbl = Gtk.Label(xalign=0.0)
        self.date_lbl.add_css_class("hero-date")
        left.append(self.date_lbl)
        left.set_hexpand(True)
        self.root.append(left)

        # right: host block + weather line
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        right.set_valign(Gtk.Align.CENTER)
        right.set_halign(Gtk.Align.END)
        host = Gtk.Label(
            label=f"{socket.gethostname().upper()} · {platform.machine()}",
            xalign=1.0)
        host.add_css_class("hero-host")
        right.append(host)
        kern = Gtk.Label(label=f"LINUX {platform.release()}", xalign=1.0)
        kern.add_css_class("hero-meta")
        right.append(kern)
        self.up_lbl = Gtk.Label(xalign=1.0)
        self.up_lbl.add_css_class("hero-meta")
        right.append(self.up_lbl)
        self.wx_lbl = Gtk.Label(xalign=1.0, label="weather · fetching…")
        self.wx_lbl.set_use_markup(True)
        self.wx_lbl.add_css_class("hero-wx")
        right.append(self.wx_lbl)
        stamp = Gtk.Label(label="NYX-J5W-2026 · SIERENGOWSKI-LOCKED",
                          xalign=1.0)
        stamp.add_css_class("header-stamp")
        right.append(stamp)
        self.root.append(right)

        self._tick()
        GLib.timeout_add(1000, self._tick)
        self._fetch_wx()
        GLib.timeout_add_seconds(900, self._fetch_wx)

    def _tick(self):
        now = _dt.datetime.now()
        blink = "" if now.second % 2 else " alpha='38%'"
        self.time_lbl.set_markup(
            f"<span font_desc='JetBrains Mono Heavy 58'>"
            f"{now.hour:02d}<span{blink}>:</span>{now.minute:02d}</span>")
        self.date_lbl.set_text(now.strftime("%A · %B %-d · %Y").upper())
        try:
            up = float(open("/proc/uptime").read().split()[0])
            d, hh, mm = int(up // 86400), int(up % 86400 // 3600), \
                int(up % 3600 // 60)
            self.up_lbl.set_text(
                f"UPTIME {d}D {hh}H {mm:02d}M" if d
                else f"UPTIME {hh}H {mm:02d}M")
        except OSError:
            pass
        return True

    def _fetch_wx(self):
        threading.Thread(target=self._fetch_wx_bg, daemon=True).start()
        return True

    def _fetch_wx_bg(self):
        try:
            with open(WEATHER_FILE) as f:
                loc = json.load(f)
        except Exception:
            loc = {"lat": 40.7128, "lon": -74.0060, "label": "New York, NY"}
        try:
            url = ("https://api.open-meteo.com/v1/forecast?"
                   + urllib.parse.urlencode({
                       "latitude": loc["lat"], "longitude": loc["lon"],
                       "current": "temperature_2m,weather_code",
                       "temperature_unit": "fahrenheit",
                       "timezone": "auto", "forecast_days": 1}))
            req = urllib.request.Request(
                url, headers={"User-Agent": "nyxus-home/2.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode())
            cur = data.get("current", {})
            code = int(cur.get("weather_code", 0))
            label, glyph = WX_CODES.get(code, ("?", "○"))
            temp = round(float(cur.get("temperature_2m", 0)))
            text = (f"<span foreground='{PALETTE['gold']}'>{glyph}</span> "
                    f"{temp}°F {label} · {loc['label']}")
        except Exception:
            text = f"<span foreground='{PALETTE['dim']}'>weather offline</span>"
        GLib.idle_add(lambda: (self.wx_lbl.set_markup(text), False)[1])
