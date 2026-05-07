#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NYXUS Clock — large monochrome digital clock + world clocks + simple stopwatch.

  • Big primary digital clock (local timezone)
  • Date sub-line
  • World clocks: UTC, NY, LA, London, Tokyo (extend via env var
    NYXUS_CLOCK_ZONES="UTC,America/New_York,...")
  • Stopwatch tab (start/stop/reset)
  • DARK MIRROR look applied centrally by nyxus_chrome.py — no per-app CSS.
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

import os
import sys
import time
import datetime as dt
from typing import List, Tuple

import gi
gi.require_version("Gtk", "4.0")

# ── DARK MIRROR chrome (rev r13): unified DARK MIRROR theme on every window ──
try:
    import nyxus_chrome  # noqa: F401  (auto-installs CHROME_CSS via Gtk import hook)
except Exception as _nyx_chrome_err:
    import logging as _l
    _l.getLogger("nyxus").debug("nyxus_chrome unavailable: %s", _nyx_chrome_err)
# ─────────────────────────────────────────────────────────────────────────────
from gi.repository import Gtk, GLib

try:
    from zoneinfo import ZoneInfo  # py3.9+
except ImportError:  # pragma: no cover
    ZoneInfo = None  # type: ignore


DEFAULT_ZONES = "UTC,America/New_York,America/Los_Angeles,Europe/London,Asia/Tokyo"


def _zone_label(z: str) -> str:
    # "America/New_York" -> "New York"
    tail = z.split("/")[-1]
    return tail.replace("_", " ")


def _now_in(zone: str) -> dt.datetime:
    if ZoneInfo is None:
        return dt.datetime.now()
    try:
        return dt.datetime.now(ZoneInfo(zone))
    except Exception:
        return dt.datetime.now()


class ClockWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title="NYXUS Clock")
        self.set_default_size(560, 520)
        self.get_style_context().add_class("nyxus-window")

        self._zones: List[str] = [
            z.strip() for z in os.environ.get("NYXUS_CLOCK_ZONES", DEFAULT_ZONES).split(",") if z.strip()
        ]

        # Stopwatch state
        self._sw_running = False
        self._sw_start_ts = 0.0
        self._sw_acc = 0.0

        notebook = Gtk.Notebook()
        notebook.set_margin_top(12); notebook.set_margin_bottom(12)
        notebook.set_margin_start(12); notebook.set_margin_end(12)
        self.set_child(notebook)

        notebook.append_page(self._build_clock_tab(), Gtk.Label(label="Clock"))
        notebook.append_page(self._build_world_tab(), Gtk.Label(label="World"))
        notebook.append_page(self._build_stopwatch_tab(), Gtk.Label(label="Stopwatch"))

        # 250ms tick is more than enough for second-level precision
        # while keeping CPU near zero.
        GLib.timeout_add(250, self._tick)
        self._tick()

    # ── Tab 1: Big digital clock ──────────────────────────────────────
    def _build_clock_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_valign(Gtk.Align.CENTER); box.set_halign(Gtk.Align.CENTER)
        box.set_margin_top(24); box.set_margin_bottom(24)

        self.big_time = Gtk.Label()
        self.big_time.get_style_context().add_class("title-1")
        self.big_time.set_xalign(0.5)
        # Hint at huge type via attributes if chrome supports it
        try:
            attrs = self.big_time.get_attributes() or self.big_time.get_pango_context()
        except Exception:
            pass
        # Fallback: rely on chrome.py title-1 sizing
        box.append(self.big_time)

        self.big_date = Gtk.Label()
        self.big_date.get_style_context().add_class("title-3")
        self.big_date.set_xalign(0.5)
        box.append(self.big_date)

        self.big_zone = Gtk.Label()
        self.big_zone.get_style_context().add_class("dim-label")
        self.big_zone.set_xalign(0.5)
        box.append(self.big_zone)

        return box

    # ── Tab 2: World clocks list ──────────────────────────────────────
    def _build_world_tab(self) -> Gtk.Widget:
        scroller = Gtk.ScrolledWindow()
        scroller.set_hexpand(True); scroller.set_vexpand(True)

        self.world_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.world_box.set_margin_top(12); self.world_box.set_margin_bottom(12)
        self.world_box.set_margin_start(12); self.world_box.set_margin_end(12)
        scroller.set_child(self.world_box)

        # Build one row per zone — labels updated in _tick()
        self._world_rows: List[Tuple[str, Gtk.Label, Gtk.Label]] = []
        for z in self._zones:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.get_style_context().add_class("frame")
            row.set_margin_bottom(2)

            name_lbl = Gtk.Label(label=_zone_label(z), xalign=0)
            name_lbl.set_hexpand(True)
            row.append(name_lbl)

            time_lbl = Gtk.Label(xalign=1)
            time_lbl.get_style_context().add_class("title-3")
            row.append(time_lbl)

            sub_lbl = Gtk.Label(xalign=1)
            sub_lbl.get_style_context().add_class("dim-label")
            row.append(sub_lbl)

            self.world_box.append(row)
            self._world_rows.append((z, time_lbl, sub_lbl))

        return scroller

    # ── Tab 3: Stopwatch ──────────────────────────────────────────────
    def _build_stopwatch_tab(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_valign(Gtk.Align.CENTER); box.set_halign(Gtk.Align.CENTER)

        self.sw_label = Gtk.Label(label="00:00:00.00")
        self.sw_label.get_style_context().add_class("title-1")
        box.append(self.sw_label)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_row.set_halign(Gtk.Align.CENTER)
        box.append(btn_row)

        self.sw_toggle = Gtk.Button(label="Start")
        self.sw_toggle.connect("clicked", self._on_sw_toggle)
        btn_row.append(self.sw_toggle)

        reset_btn = Gtk.Button(label="Reset")
        reset_btn.connect("clicked", self._on_sw_reset)
        btn_row.append(reset_btn)

        return box

    # ── Tick ──────────────────────────────────────────────────────────
    def _tick(self) -> bool:
        now = dt.datetime.now()
        self.big_time.set_text(now.strftime("%H:%M:%S"))
        self.big_date.set_text(now.strftime("%A, %B %-d, %Y"))
        try:
            tz = time.tzname[time.daylight] if time.daylight else time.tzname[0]
        except Exception:
            tz = ""
        self.big_zone.set_text(tz)

        for z, tlbl, slbl in self._world_rows:
            t = _now_in(z)
            tlbl.set_text(t.strftime("%H:%M:%S"))
            slbl.set_text(t.strftime("%a · %b %-d"))

        if self._sw_running:
            elapsed = self._sw_acc + (time.monotonic() - self._sw_start_ts)
            self.sw_label.set_text(self._fmt_sw(elapsed))

        return True

    @staticmethod
    def _fmt_sw(elapsed: float) -> str:
        h = int(elapsed // 3600)
        m = int((elapsed % 3600) // 60)
        s = int(elapsed % 60)
        cs = int((elapsed - int(elapsed)) * 100)
        return f"{h:02d}:{m:02d}:{s:02d}.{cs:02d}"

    # ── Stopwatch handlers ────────────────────────────────────────────
    def _on_sw_toggle(self, _btn: Gtk.Button) -> None:
        if self._sw_running:
            self._sw_acc += time.monotonic() - self._sw_start_ts
            self._sw_running = False
            self.sw_toggle.set_label("Start")
        else:
            self._sw_start_ts = time.monotonic()
            self._sw_running = True
            self.sw_toggle.set_label("Stop")

    def _on_sw_reset(self, _btn: Gtk.Button) -> None:
        self._sw_running = False
        self._sw_start_ts = 0.0
        self._sw_acc = 0.0
        self.sw_toggle.set_label("Start")
        self.sw_label.set_text("00:00:00.00")


class ClockApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.clock")

    def do_activate(self):
        win = ClockWindow(self)
        win.present()


def main() -> int:
    app = ClockApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
