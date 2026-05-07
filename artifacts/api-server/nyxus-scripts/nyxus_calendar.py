#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NYXUS Calendar — minimal monochrome month-view calendar.

  • Month grid with today highlighted
  • Prev / Next month navigation, "Today" jump
  • Per-day notes saved to ~/.config/nyxus-calendar/notes.db (sqlite3)
  • DARK MIRROR look applied centrally by nyxus_chrome.py — this file
    contains no per-app CSS / colors.
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

import calendar
import datetime as dt
import sqlite3
import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")

# ── DARK MIRROR chrome (rev r13): unified DARK MIRROR theme on every window ──
try:
    import nyxus_chrome  # noqa: F401  (auto-installs CHROME_CSS via Gtk import hook)
except Exception as _nyx_chrome_err:
    import logging as _l
    _l.getLogger("nyxus").debug("nyxus_chrome unavailable: %s", _nyx_chrome_err)
# ─────────────────────────────────────────────────────────────────────────────
from gi.repository import Gtk, Gdk, GLib

DB_DIR = Path.home() / ".config" / "nyxus-calendar"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "notes.db"

WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS notes (date TEXT PRIMARY KEY, body TEXT)")
    return conn


def get_note(date: dt.date) -> str:
    with _db() as c:
        row = c.execute("SELECT body FROM notes WHERE date=?", (date.isoformat(),)).fetchone()
    return row[0] if row else ""


def set_note(date: dt.date, body: str) -> None:
    with _db() as c:
        if body.strip():
            c.execute(
                "INSERT INTO notes(date, body) VALUES(?, ?) "
                "ON CONFLICT(date) DO UPDATE SET body=excluded.body",
                (date.isoformat(), body),
            )
        else:
            c.execute("DELETE FROM notes WHERE date=?", (date.isoformat(),))


def has_note(date: dt.date) -> bool:
    return bool(get_note(date))


class CalendarWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title="NYXUS Calendar")
        self.set_default_size(720, 620)
        self.get_style_context().add_class("nyxus-window")

        today = dt.date.today()
        self.year = today.year
        self.month = today.month
        self.selected = today

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(16); root.set_margin_bottom(16)
        root.set_margin_start(16); root.set_margin_end(16)
        self.set_child(root)

        # ── Header: prev / month label / next / today ─────────────────
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.get_style_context().add_class("frame")
        header.set_margin_bottom(4)
        root.append(header)

        prev_btn = Gtk.Button(label="‹")
        prev_btn.connect("clicked", lambda *_: self._shift(-1))
        header.append(prev_btn)

        self.title_label = Gtk.Label()
        self.title_label.set_hexpand(True)
        self.title_label.set_xalign(0.5)
        self.title_label.get_style_context().add_class("title-2")
        header.append(self.title_label)

        today_btn = Gtk.Button(label="Today")
        today_btn.connect("clicked", lambda *_: self._goto_today())
        header.append(today_btn)

        next_btn = Gtk.Button(label="›")
        next_btn.connect("clicked", lambda *_: self._shift(1))
        header.append(next_btn)

        # ── Grid: 7 weekday headers + up to 6 rows of day buttons ─────
        self.grid = Gtk.Grid(column_spacing=4, row_spacing=4)
        self.grid.set_column_homogeneous(True)
        self.grid.set_row_homogeneous(True)
        self.grid.set_hexpand(True); self.grid.set_vexpand(True)
        root.append(self.grid)

        # ── Footer: per-day note editor ───────────────────────────────
        editor_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        editor_box.get_style_context().add_class("frame")
        root.append(editor_box)

        self.editor_label = Gtk.Label(xalign=0)
        self.editor_label.get_style_context().add_class("dim-label")
        editor_box.append(self.editor_label)

        scroller = Gtk.ScrolledWindow()
        scroller.set_min_content_height(96)
        scroller.set_hexpand(True)
        self.note_view = Gtk.TextView()
        self.note_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scroller.set_child(self.note_view)
        editor_box.append(scroller)

        save_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        save_row.set_halign(Gtk.Align.END)
        editor_box.append(save_row)

        save_btn = Gtk.Button(label="Save note")
        save_btn.connect("clicked", lambda *_: self._save_note())
        save_row.append(save_btn)

        self._render()

    def _shift(self, delta: int) -> None:
        m = self.month + delta
        y = self.year
        while m < 1:  m += 12; y -= 1
        while m > 12: m -= 12; y += 1
        self.year, self.month = y, m
        self._render()

    def _goto_today(self) -> None:
        t = dt.date.today()
        self.year, self.month, self.selected = t.year, t.month, t
        self._render()

    def _render(self) -> None:
        # Title
        first = dt.date(self.year, self.month, 1)
        self.title_label.set_text(first.strftime("%B %Y"))

        # Clear grid
        child = self.grid.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.grid.remove(child)
            child = nxt

        # Weekday headers
        for col, name in enumerate(WEEKDAYS):
            lbl = Gtk.Label(label=name)
            lbl.get_style_context().add_class("dim-label")
            self.grid.attach(lbl, col, 0, 1, 1)

        today = dt.date.today()
        cal = calendar.Calendar(firstweekday=0)  # Monday-first
        row = 1
        for week in cal.monthdatescalendar(self.year, self.month):
            for col, day in enumerate(week):
                btn = Gtk.Button()
                lbl_text = str(day.day)
                if has_note(day):
                    lbl_text += " •"
                btn.set_label(lbl_text)
                btn.set_hexpand(True); btn.set_vexpand(True)
                ctx = btn.get_style_context()
                if day.month != self.month:
                    ctx.add_class("dim-label")
                if day == today:
                    ctx.add_class("suggested-action")
                if day == self.selected:
                    ctx.add_class("destructive-action")
                btn.connect("clicked", self._on_day_clicked, day)
                self.grid.attach(btn, col, row, 1, 1)
            row += 1

        self._refresh_editor()

    def _on_day_clicked(self, _btn: Gtk.Button, day: dt.date) -> None:
        # If clicking a day from prev/next month, navigate there too
        if day.month != self.month or day.year != self.year:
            self.year, self.month = day.year, day.month
        self.selected = day
        self._render()

    def _refresh_editor(self) -> None:
        d = self.selected
        self.editor_label.set_text(d.strftime("Note for %A, %B %-d, %Y"))
        buf = self.note_view.get_buffer()
        buf.set_text(get_note(d))

    def _save_note(self) -> None:
        buf = self.note_view.get_buffer()
        body = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), True)
        set_note(self.selected, body)
        self._render()


class CalendarApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.calendar")

    def do_activate(self):
        win = CalendarWindow(self)
        win.present()


def main() -> int:
    app = CalendarApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
