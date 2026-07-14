"""
NYXUS Home - the six dashboard cards.
Faithful port of HomeDashboard.tsx (Clock / Weather / Calendar /
Notifications / Notepad / Password Manager).
(c) 2026 Joseph Sierengowski - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import calendar
import datetime as _dt
import json
import os
import secrets
import string
import threading
import time as _time
import urllib.parse
import urllib.request
from typing import Optional

import gi

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

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib  # noqa: E402

from style import PALETTE  # noqa: E402
from storage import PasswordStore  # noqa: E402

DATA_DIR = os.path.join(
    os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share")),
    "nyxus-home",
)
os.makedirs(DATA_DIR, exist_ok=True)
NOTEPAD_FILE = os.path.join(DATA_DIR, "notepad.txt")
WEATHER_FILE = os.path.join(DATA_DIR, "weather.json")
NOTIF_FILE   = os.path.join(DATA_DIR, "notifications.json")


# ── shared card chrome ─────────────────────────────────────────────────────
def _stamp(color):
    lbl = Gtk.Label(label="NYX-J5W-2026", xalign=1.0)
    lbl.add_css_class(f"card-{color}-header-stamp")
    return lbl


def make_card(color_key: str, title: str, glyph: str, footer_text: str):
    """Create a card frame -> (root_box, content_box, footer_label_setter)."""
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    root.add_css_class(f"card-{color_key}")
    root.set_hexpand(True)

    # Header row: glyph + title + spacer + stamp
    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    glyph_lbl = Gtk.Label(label=glyph)
    glyph_lbl.add_css_class(f"card-{color_key}-header-glyph")
    title_lbl = Gtk.Label(label=title, xalign=0.0)
    title_lbl.add_css_class(f"card-{color_key}-header-title")
    header.append(glyph_lbl)
    header.append(title_lbl)
    spacer = Gtk.Box()
    spacer.set_hexpand(True)
    header.append(spacer)
    header.append(_stamp(color_key))
    root.append(header)

    # dashed under-rule
    rule = Gtk.Box()
    rule.add_css_class(f"card-{color_key}-header-rule")
    rule.set_size_request(-1, 1)
    root.append(rule)

    # content
    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    content.set_vexpand(True)
    root.append(content)

    # footer
    footer_lbl = Gtk.Label(label=footer_text, xalign=0.0)
    footer_lbl.set_wrap(True)
    footer_lbl.add_css_class(f"card-{color_key}-footer")
    root.append(footer_lbl)

    def set_footer(t: str):
        footer_lbl.set_text(t)

    return root, content, set_footer


# ── CLOCK ──────────────────────────────────────────────────────────────────
class ClockCard:
    def __init__(self):
        self.root, content, _ = make_card("pink", "Clock", "\u25f4",
                                          "SYSTEM TIME \u00b7 LOCAL")
        self.time_lbl = Gtk.Label()
        self.time_lbl.set_use_markup(True)
        self.time_lbl.add_css_class("clock-time")
        self.time_lbl.set_xalign(0.5)
        self.day_lbl = Gtk.Label(xalign=0.5)
        self.day_lbl.add_css_class("clock-day")
        self.date_lbl = Gtk.Label(xalign=0.5)
        self.date_lbl.add_css_class("clock-date")
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        wrap.append(self.time_lbl)
        wrap.append(self.day_lbl)
        wrap.append(self.date_lbl)
        content.append(wrap)
        self._tick()
        GLib.timeout_add(1000, self._tick)

    def _tick(self):
        now = _dt.datetime.now()
        hh = f"{now.hour:02d}"
        mm = f"{now.minute:02d}"
        ss = f"{now.second:02d}"
        colon = '<span foreground="#e8edf5"' \
                + (' alpha="40%"' if now.second % 2 else "") \
                + ">:</span>"
        markup = (f"{hh}{colon}{mm}"
                  f"<span foreground='#c8ccd6' font_desc='JetBrains Mono 14'>"
                  f"  {ss}</span>")
        self.time_lbl.set_markup(markup)
        self.day_lbl.set_text(now.strftime("%A"))
        self.date_lbl.set_text(now.strftime("%B %-d, %Y"))
        return True


# ── WEATHER (Open-Meteo, real API, no auth) ────────────────────────────────
WX_CODES = {
    0:  ("Clear", "\u2600"),
    1:  ("Mainly Clear", "\u2600"),
    2:  ("Partly Cloudy", "\u25d0"),
    3:  ("Overcast", "\u2601"),
    45: ("Fog", "\u224b"),
    48: ("Rime Fog", "\u224b"),
    51: ("Light Drizzle", "\u2602"),
    53: ("Drizzle", "\u2602"),
    55: ("Heavy Drizzle", "\u2602"),
    61: ("Light Rain", "\u2602"),
    63: ("Rain", "\u2602"),
    65: ("Heavy Rain", "\u2602"),
    71: ("Light Snow", "\u2744"),
    73: ("Snow", "\u2744"),
    75: ("Heavy Snow", "\u2744"),
    77: ("Snow Grains", "\u2744"),
    80: ("Rain Showers", "\u2602"),
    81: ("Heavy Showers", "\u2602"),
    82: ("Violent Showers", "\u2602"),
    85: ("Snow Showers", "\u2744"),
    86: ("Heavy Snow Show", "\u2744"),
    95: ("Thunderstorm", "\u26a1"),
    96: ("Storm + Hail", "\u26a1"),
    99: ("Storm + Heavy Hail", "\u26a1"),
}


class WeatherCard:
    def __init__(self):
        self.root, content, self.set_footer = make_card(
            "gold", "Weather", "\u263c", "OPEN-METEO \u00b7 LIVE \u00b7 NO AUTH")
        self.loc = self._load_loc()

        # main row
        self.main_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.glyph_lbl = Gtk.Label(label="…")
        self.glyph_lbl.add_css_class("wx-glyph")
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.temp_lbl = Gtk.Label(xalign=0.0)
        self.temp_lbl.set_use_markup(True)
        self.temp_lbl.add_css_class("wx-temp")
        self.label_lbl = Gtk.Label(xalign=0.0, label="loading…")
        self.label_lbl.add_css_class("wx-label")
        info_box.append(self.temp_lbl)
        info_box.append(self.label_lbl)
        self.main_row.append(self.glyph_lbl)
        self.main_row.append(info_box)
        content.append(self.main_row)

        # stats row (hi/lo/wind)
        self.stats_lbl = Gtk.Label(xalign=0.0, label="")
        self.stats_lbl.add_css_class("wx-stats")
        content.append(self.stats_lbl)

        # location row + edit button
        loc_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.loc_lbl = Gtk.Label(xalign=0.0, label=self.loc["label"])
        self.loc_lbl.add_css_class("wx-loc")
        self.loc_lbl.set_hexpand(True)
        edit_btn = Gtk.Button(label="EDIT")
        edit_btn.add_css_class("btn-nav-mono")
        edit_btn.connect("clicked", self._toggle_edit)
        loc_row.append(self.loc_lbl)
        loc_row.append(edit_btn)
        content.append(loc_row)

        # editor (hidden by default)
        self.editor = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.label_in = Gtk.Entry()
        self.label_in.add_css_class("input-mono")
        self.label_in.set_placeholder_text("Label")
        self.label_in.set_text(self.loc["label"])
        coord_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.lat_in = Gtk.Entry()
        self.lat_in.add_css_class("input-mono")
        self.lat_in.set_placeholder_text("Lat")
        self.lat_in.set_text(str(self.loc["lat"]))
        self.lon_in = Gtk.Entry()
        self.lon_in.add_css_class("input-mono")
        self.lon_in.set_placeholder_text("Lon")
        self.lon_in.set_text(str(self.loc["lon"]))
        self.lat_in.set_hexpand(True)
        self.lon_in.set_hexpand(True)
        coord_row.append(self.lat_in)
        coord_row.append(self.lon_in)
        save_btn = Gtk.Button(label="SAVE LOCATION")
        save_btn.add_css_class("btn-primary-mono")
        save_btn.connect("clicked", self._save_loc)
        self.editor.append(self.label_in)
        self.editor.append(coord_row)
        self.editor.append(save_btn)
        self.editor.set_visible(False)
        content.append(self.editor)

        self._fetch()

    def _load_loc(self):
        try:
            with open(WEATHER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"lat": 40.7128, "lon": -74.0060, "label": "New York, NY"}

    def _save_loc(self, _btn):
        try:
            lat = float(self.lat_in.get_text())
            lon = float(self.lon_in.get_text())
        except ValueError:
            return
        label = self.label_in.get_text().strip() or f"{lat:.2f}, {lon:.2f}"
        self.loc = {"lat": lat, "lon": lon, "label": label}
        try:
            with open(WEATHER_FILE, "w", encoding="utf-8") as f:
                json.dump(self.loc, f)
        except OSError:
            pass
        self.loc_lbl.set_text(label)
        self.editor.set_visible(False)
        self._fetch()

    def _toggle_edit(self, _btn):
        self.editor.set_visible(not self.editor.get_visible())

    def _fetch(self):
        self.temp_lbl.set_markup(
            "<span foreground='#c8ccd6' font_desc='Inter Display 13'>loading…</span>"
        )
        self.label_lbl.set_text("")
        self.stats_lbl.set_text("")
        threading.Thread(target=self._fetch_bg, daemon=True).start()

    def _fetch_bg(self):
        try:
            url = (
                "https://api.open-meteo.com/v1/forecast?"
                + urllib.parse.urlencode({
                    "latitude":           self.loc["lat"],
                    "longitude":          self.loc["lon"],
                    "current":            "temperature_2m,weather_code,wind_speed_10m",
                    "temperature_unit":   "fahrenheit",
                    "wind_speed_unit":    "mph",
                    "daily":              "temperature_2m_max,temperature_2m_min",
                    "timezone":           "auto",
                    "forecast_days":      1,
                })
            )
            req = urllib.request.Request(url, headers={"User-Agent": "nyxus-home/1.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            GLib.idle_add(self._apply, data)
        except Exception as e:
            GLib.idle_add(self._apply_error, str(e))

    def _apply(self, data):
        cur = data.get("current", {}) or {}
        daily = data.get("daily", {}) or {}
        code = int(cur.get("weather_code", 0))
        label, glyph = WX_CODES.get(code, ("Unknown", "\u25cb"))
        temp = round(float(cur.get("temperature_2m", 0)))
        wind = round(float(cur.get("wind_speed_10m", 0)))
        hi = (daily.get("temperature_2m_max") or [None])[0]
        lo = (daily.get("temperature_2m_min") or [None])[0]
        hi_s = f"{round(hi)}\u00b0" if hi is not None else "\u2014"
        lo_s = f"{round(lo)}\u00b0" if lo is not None else "\u2014"
        self.glyph_lbl.set_text(glyph)
        self.temp_lbl.set_markup(
            f"{temp}<span foreground='#c8ccd6' font_desc='JetBrains Mono 11'>"
            f"\u00b0F</span>"
        )
        self.label_lbl.set_text(label)
        self.stats_lbl.set_text(f"\u2191 {hi_s}    \u2193 {lo_s}    WIND {wind} MPH")
        return False

    def _apply_error(self, msg):
        self.glyph_lbl.set_text("\u26a0")
        self.temp_lbl.set_markup(
            f"<span foreground='#c8ccd6' font_desc='JetBrains Mono 11'>"
            f"{GLib.markup_escape_text(msg)[:40]}</span>"
        )
        self.label_lbl.set_text("network error")
        self.stats_lbl.set_text("")
        return False


# ── CALENDAR ───────────────────────────────────────────────────────────────
class CalendarCard:
    def __init__(self):
        self.root, content, _ = make_card("purple", "Calendar", "\u25a6",
                                          "LOCAL \u00b7 GREGORIAN")
        today = _dt.date.today()
        self.today = today
        self.view_y, self.view_m = today.year, today.month

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        prev_b = Gtk.Button(label="\u25c0")
        prev_b.add_css_class("btn-nav-mono")
        prev_b.connect("clicked", lambda _b: self._nav(-1))
        nav.append(prev_b)
        self.month_lbl = Gtk.Label(xalign=0.5)
        self.month_lbl.add_css_class("cal-month")
        self.month_lbl.set_hexpand(True)
        nav.append(self.month_lbl)
        next_b = Gtk.Button(label="\u25b6")
        next_b.add_css_class("btn-nav-mono")
        next_b.connect("clicked", lambda _b: self._nav(1))
        nav.append(next_b)
        content.append(nav)

        self.grid = Gtk.Grid(column_homogeneous=True, row_spacing=2,
                             column_spacing=2)
        content.append(self.grid)

        today_btn = Gtk.Button(label="\u25c9 TODAY")
        today_btn.add_css_class("btn-nav-mono")
        today_btn.set_halign(Gtk.Align.START)
        today_btn.connect("clicked", self._goto_today)
        content.append(today_btn)

        self._render()

    def _nav(self, delta):
        m = self.view_m + delta
        y = self.view_y + ((m - 1) // 12)
        self.view_m = ((m - 1) % 12) + 1
        self.view_y = y
        self._render()

    def _goto_today(self, _b):
        self.view_y, self.view_m = self.today.year, self.today.month
        self._render()

    def _render(self):
        # clear grid
        child = self.grid.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.grid.remove(child)
            child = nxt

        month_name = _dt.date(self.view_y, self.view_m, 1).strftime("%B")
        self.month_lbl.set_text(f"{month_name} {self.view_y}")
        for col, dow in enumerate(["S", "M", "T", "W", "T", "F", "S"]):
            lbl = Gtk.Label(label=dow)
            lbl.add_css_class("cal-dow")
            self.grid.attach(lbl, col, 0, 1, 1)

        first = _dt.date(self.view_y, self.view_m, 1)
        start_dow = (first.weekday() + 1) % 7   # python: Mon=0 -> shift
        days_in_month = calendar.monthrange(self.view_y, self.view_m)[1]
        cells = [None] * start_dow + list(range(1, days_in_month + 1))
        while len(cells) % 7:
            cells.append(None)

        for i, d in enumerate(cells):
            row = (i // 7) + 1
            col = i % 7
            if d is None:
                spacer = Gtk.Box()
                self.grid.attach(spacer, col, row, 1, 1)
                continue
            is_today = (d == self.today.day
                        and self.view_m == self.today.month
                        and self.view_y == self.today.year)
            lbl = Gtk.Label(label=str(d))
            lbl.set_halign(Gtk.Align.CENTER)
            lbl.add_css_class("cal-day-today" if is_today else "cal-day")
            self.grid.attach(lbl, col, row, 1, 1)


# ── NOTIFICATIONS ──────────────────────────────────────────────────────────
SEED_NOTIFS = [
    {"id": "n1", "glyph": "\u25c9", "color": "purple",
     "title": "INTEL",   "body": "Investigation auto-saved (3 findings).",         "time": "2m"},
    {"id": "n2", "glyph": "\u26e8", "color": "green",
     "title": "Shield",  "body": "Local scan complete \u2014 0 open ports outside policy.", "time": "8m"},
    {"id": "n3", "glyph": "\u25c8", "color": "blue",
     "title": "Phantom", "body": "Daemon armed. 0 threats since boot.",            "time": "14m"},
    {"id": "n4", "glyph": "\u2726", "color": "gold",
     "title": "GodsApp", "body": "WiFi audit module ready.",                        "time": "22m"},
    {"id": "n5", "glyph": "\u2711", "color": "purple",
     "title": "Notepad", "body": "5 notes synced to ~/.nyxus/notepad.json.",        "time": "1h"},
    {"id": "n6", "glyph": "\u25e7", "color": "cyan",
     "title": "SysMon",  "body": "CPU steady at 15% \u00b7 RAM 56% \u00b7 Temp 84\u00b0C.", "time": "2h"},
]


class NotificationsCard:
    def __init__(self):
        self.root, self.content, self.set_footer = make_card(
            "green", "Notifications", "\u2709", "")
        self.items = self._load()
        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(self.list_box)
        scroller.set_min_content_height(200)
        self.content.append(scroller)
        self.reload_btn = Gtk.Button(label="\u21ba RELOAD FEED")
        self.reload_btn.add_css_class("btn-nav-mono")
        self.reload_btn.set_halign(Gtk.Align.START)
        self.reload_btn.connect("clicked", self._reload)
        self.content.append(self.reload_btn)
        self._render()

    def _load(self):
        try:
            with open(NOTIF_FILE, "r", encoding="utf-8") as f:
                d = json.load(f)
                if isinstance(d, list):
                    return d
        except Exception:
            pass
        return [dict(n) for n in SEED_NOTIFS]

    def _save(self):
        try:
            with open(NOTIF_FILE, "w", encoding="utf-8") as f:
                json.dump(self.items, f)
        except OSError:
            pass

    def _reload(self, _b):
        self.items = [dict(n) for n in SEED_NOTIFS]
        self._save()
        self._render()

    def _dismiss(self, nid):
        self.items = [n for n in self.items if n["id"] != nid]
        self._save()
        self._render()

    def _render(self):
        child = self.list_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.list_box.remove(child)
            child = nxt
        if not self.items:
            empty = Gtk.Label(label="Inbox zero \u00b7 all clear")
            empty.add_css_class("wx-loc")
            empty.set_xalign(0.5)
            self.list_box.append(empty)
        for n in self.items:
            color_hex = PALETTE.get(n["color"], PALETTE["green"])
            color_key = n["color"] if n["color"] in (
                "pink", "cyan", "purple", "gold", "green", "orange", "red"
            ) else "green"
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.add_css_class(f"notif-{color_key}")
            glyph = Gtk.Label(label=n["glyph"])
            glyph.add_css_class("notif-glyph")
            glyph.set_markup(
                f"<span foreground='{color_hex}'>{GLib.markup_escape_text(n['glyph'])}</span>"
            )
            row.append(glyph)
            mid = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            mid.set_hexpand(True)
            head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            title = Gtk.Label(xalign=0.0)
            title.set_markup(
                f"<span foreground='{color_hex}' font_desc='Inter Display 13'>"
                f"{GLib.markup_escape_text(n['title'])}</span>"
            )
            title.add_css_class("notif-title")
            head.append(title)
            spacer = Gtk.Box()
            spacer.set_hexpand(True)
            head.append(spacer)
            t = Gtk.Label(label=n["time"])
            t.add_css_class("notif-time")
            head.append(t)
            mid.append(head)
            body = Gtk.Label(label=n["body"], xalign=0.0)
            body.set_wrap(True)
            body.add_css_class("notif-body")
            mid.append(body)
            row.append(mid)
            x_btn = Gtk.Button(label="\u2715")
            x_btn.add_css_class(f"btn-icon-{color_key}")
            x_btn.connect("clicked", lambda _b, nid=n["id"]: self._dismiss(nid))
            row.append(x_btn)
            self.list_box.append(row)
        self.set_footer(f"{len(self.items)} ACTIVE \u00b7 LIVE FEED")


# ── NOTEPAD ───────────────────────────────────────────────────────────────
class NotepadCard:
    def __init__(self):
        self.root, content, self.set_footer = make_card(
            "cyan", "Notepad", "\u2711", "")
        self.text_view = Gtk.TextView()
        self.text_view.add_css_class("np-textarea")
        self.text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text_view.set_top_margin(10)
        self.text_view.set_bottom_margin(10)
        self.text_view.set_left_margin(13)
        self.text_view.set_right_margin(13)
        self.buf = self.text_view.get_buffer()
        try:
            with open(NOTEPAD_FILE, "r", encoding="utf-8") as f:
                self.buf.set_text(f.read())
        except Exception:
            pass
        self.buf.connect("changed", self._on_change)
        self._save_timer: Optional[int] = None
        self._last_save = 0.0

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(self.text_view)
        scroller.set_min_content_height(200)
        scroller.set_vexpand(True)
        content.append(scroller)

        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        clr = Gtk.Button(label="\u2715 CLEAR")
        clr.add_css_class("btn-nav-mono")
        clr.connect("clicked", lambda _b: self.buf.set_text(""))
        cpy = Gtk.Button(label="\u2024 COPY ALL")
        cpy.add_css_class("btn-nav-mono")
        cpy.connect("clicked", self._copy_all)
        btn_row.append(clr)
        btn_row.append(cpy)
        content.append(btn_row)
        self._refresh_footer()
        GLib.timeout_add(1000, self._refresh_footer)

    def _on_change(self, *_):
        if self._save_timer is not None:
            GLib.source_remove(self._save_timer)
        self._save_timer = GLib.timeout_add(350, self._save)
        return False

    def _save(self):
        self._save_timer = None
        text = self.buf.get_text(self.buf.get_start_iter(),
                                 self.buf.get_end_iter(), False)
        try:
            tmp = NOTEPAD_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                f.write(text)
            os.replace(tmp, NOTEPAD_FILE)
            self._last_save = _time.time()
        except OSError:
            pass
        return False

    def _copy_all(self, _b):
        text = self.buf.get_text(self.buf.get_start_iter(),
                                 self.buf.get_end_iter(), False)
        clip = Gdk.Display.get_default().get_clipboard()
        clip.set(text)

    def _refresh_footer(self):
        text = self.buf.get_text(self.buf.get_start_iter(),
                                 self.buf.get_end_iter(), False)
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        if self._last_save:
            since = int(_time.time() - self._last_save)
            self.set_footer(
                f"AUTOSAVE \u00b7 {chars} CHARS \u00b7 {words} WORDS "
                f"\u00b7 SAVED {since}S AGO"
            )
        else:
            self.set_footer(
                f"AUTOSAVE \u00b7 {chars} CHARS \u00b7 {words} WORDS"
            )
        return True


# ── PASSWORD MANAGER ──────────────────────────────────────────────────────
ALPHABETS = {
    "upper": string.ascii_uppercase,
    "lower": string.ascii_lowercase,
    "num":   string.digits,
    "sym":   "!@#$%^&*()-_=+[]{};:,.<>?/~",
}


def generate_password(length: int, upper: bool, lower: bool,
                      num: bool, sym: bool) -> str:
    pool = ""
    if upper:  pool += ALPHABETS["upper"]
    if lower:  pool += ALPHABETS["lower"]
    if num:    pool += ALPHABETS["num"]
    if sym:    pool += ALPHABETS["sym"]
    if not pool:
        return ""
    return "".join(secrets.choice(pool) for _ in range(length))


class PasswordManagerCard:
    def __init__(self):
        self.root, content, self.set_footer = make_card(
            "orange", "Password Manager", "\u26bf", "")
        self.store = PasswordStore()

        # generator section
        gen = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        gen.add_css_class("pw-section")

        gen_head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        glb = Gtk.Label(label="Generator", xalign=0.0)
        glb.add_css_class("pw-gen-label")
        gen_head.append(glb)
        self.len_lbl = Gtk.Label(label="length 18", xalign=0.0)
        self.len_lbl.add_css_class("pw-gen-len")
        self.len_lbl.set_hexpand(True)
        gen_head.append(self.len_lbl)
        gen.append(gen_head)

        adj = Gtk.Adjustment(value=18, lower=8, upper=64, step_increment=1)
        self.len_scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                                   adjustment=adj)
        self.len_scale.set_draw_value(False)
        self.len_scale.set_hexpand(True)
        self.len_scale.connect("value-changed", self._on_opts)
        gen.append(self.len_scale)

        opts_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.opt_buttons = {}
        for k in ("upper", "lower", "num", "sym"):
            cb = Gtk.CheckButton(label=k.upper())
            cb.set_active(True)
            cb.connect("toggled", self._on_opts)
            self.opt_buttons[k] = cb
            opts_row.append(cb)
        gen.append(opts_row)

        self.preview_lbl = Gtk.Label(xalign=0.0)
        self.preview_lbl.set_wrap(True)
        self.preview_lbl.set_wrap_mode(2)  # CHAR
        self.preview_lbl.add_css_class("pw-gen-preview")
        gen.append(self.preview_lbl)

        roll_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        roll = Gtk.Button(label="\u21bb ROLL")
        roll.add_css_class("btn-primary-mono")
        roll.connect("clicked", self._roll)
        use = Gtk.Button(label="\u21b3 USE")
        use.add_css_class("btn-nav-mono")
        use.connect("clicked", self._use)
        roll_row.append(roll)
        roll_row.append(use)
        gen.append(roll_row)
        content.append(gen)

        # add-entry row
        add_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.site_in = Gtk.Entry()
        self.site_in.add_css_class("input-mono")
        self.site_in.set_placeholder_text("site / app")
        self.user_in = Gtk.Entry()
        self.user_in.add_css_class("input-mono")
        self.user_in.set_placeholder_text("username / email")
        self.pass_in = Gtk.Entry()
        self.pass_in.add_css_class("input-mono")
        self.pass_in.set_placeholder_text("password")
        self.pass_in.set_visibility(False)
        for w in (self.site_in, self.user_in, self.pass_in):
            w.set_hexpand(True)
            add_row.append(w)
        add_btn = Gtk.Button(label="+ ADD")
        add_btn.add_css_class("btn-primary-mono")
        add_btn.connect("clicked", self._add)
        add_row.append(add_btn)
        content.append(add_row)

        # entries list
        self.list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(self.list_box)
        scroller.set_min_content_height(180)
        scroller.set_vexpand(True)
        content.append(scroller)

        self._reveal = {}
        self._roll(None)
        self._render()

    def _opts(self):
        return {
            "length": int(self.len_scale.get_value()),
            "upper":  self.opt_buttons["upper"].get_active(),
            "lower":  self.opt_buttons["lower"].get_active(),
            "num":    self.opt_buttons["num"].get_active(),
            "sym":    self.opt_buttons["sym"].get_active(),
        }

    def _on_opts(self, *_):
        o = self._opts()
        self.len_lbl.set_text(f"length {o['length']}")
        self._roll(None)

    def _roll(self, _b):
        o = self._opts()
        pw = generate_password(o["length"], o["upper"], o["lower"],
                               o["num"], o["sym"])
        self._gen_preview = pw
        self.preview_lbl.set_text(pw or "pick at least one option")

    def _use(self, _b):
        if getattr(self, "_gen_preview", ""):
            self.pass_in.set_text(self._gen_preview)

    def _add(self, _b):
        site = self.site_in.get_text().strip()
        user = self.user_in.get_text().strip()
        pw = self.pass_in.get_text()
        if not site or not user or not pw:
            return
        self.store.add(site=site, user=user, pw=pw)
        self.site_in.set_text("")
        self.user_in.set_text("")
        self.pass_in.set_text("")
        self._render()

    def _render(self):
        child = self.list_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.list_box.remove(child)
            child = nxt
        entries = self.store.list_entries()
        if not entries:
            empty = Gtk.Label(
                label="no entries yet \u2014 add one above or generate a password"
            )
            empty.set_xalign(0.5)
            empty.add_css_class("wx-loc")
            self.list_box.append(empty)
        for e in entries:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.add_css_class("pw-row")
            site = Gtk.Label(label=e["site"], xalign=0.0)
            site.set_hexpand(True)
            site.set_ellipsize(3)
            site.add_css_class("pw-row-site")
            user = Gtk.Label(label=e["user"], xalign=0.0)
            user.set_hexpand(True)
            user.set_ellipsize(3)
            user.add_css_class("pw-row-user")
            shown = self._reveal.get(e["id"], False)
            pw = self.store.get_password(e["id"]) or ""
            pw_lbl = Gtk.Label(
                label=pw if shown else "\u2022" * min(len(pw), 18),
                xalign=0.0,
            )
            pw_lbl.set_hexpand(True)
            pw_lbl.set_ellipsize(3)
            pw_lbl.add_css_class("pw-row-pass" if shown else "pw-row-pass-hidden")
            row.append(site)
            row.append(user)
            row.append(pw_lbl)
            eye = Gtk.Button(label="\u25d0" if shown else "\u25cb")
            eye.add_css_class("btn-icon-mono")
            eye.connect("clicked", self._toggle, e["id"])
            cpy = Gtk.Button(label="\u2024")
            cpy.add_css_class("btn-icon-mono")
            cpy.connect("clicked", self._copy, e["id"])
            dl = Gtk.Button(label="\u2715")
            dl.add_css_class("btn-icon-mono")
            dl.connect("clicked", self._delete, e["id"])
            row.append(eye)
            row.append(cpy)
            row.append(dl)
            self.list_box.append(row)
        backend = self.store.backend_status
        self.set_footer(
            f"{len(entries)} ENTRIES \u00b7 {backend} \u00b7 secrets.getRandomBytes"
        )

    def _toggle(self, _b, eid):
        self._reveal[eid] = not self._reveal.get(eid, False)
        self._render()

    def _copy(self, _b, eid):
        pw = self.store.get_password(eid) or ""
        clip = Gdk.Display.get_default().get_clipboard()
        clip.set(pw)

    def _delete(self, _b, eid):
        self.store.delete(eid)
        self._render()


# ── SYSTEM PULSE ───────────────────────────────────────────────────────────
def _hex_rgb(h):
    h = h.lstrip("#")
    return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255


class _Sparkline(Gtk.DrawingArea):
    """Filled-area sparkline over a rolling 0-100 history."""

    def __init__(self, color_hex, history, height=56):
        super().__init__()
        self.color = _hex_rgb(color_hex)
        self.history = history
        self.set_content_height(height)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)

    def _draw(self, _area, cr, w, h):
        pts = list(self.history)
        if len(pts) < 2:
            return
        # baseline grid
        cr.set_source_rgba(1, 1, 1, 0.06)
        cr.set_line_width(1)
        for frac in (0.25, 0.5, 0.75):
            cr.move_to(0, h * frac)
            cr.line_to(w, h * frac)
            cr.stroke()
        step = w / (len(pts) - 1)
        r, g, b = self.color
        # filled area
        cr.move_to(0, h)
        for i, v in enumerate(pts):
            cr.line_to(i * step, h - (max(0.0, min(100.0, v)) / 100.0) * (h - 3) - 1)
        cr.line_to(w, h)
        cr.close_path()
        grad = __import__("cairo").LinearGradient(0, 0, 0, h)
        grad.add_color_stop_rgba(0, r, g, b, 0.35)
        grad.add_color_stop_rgba(1, r, g, b, 0.02)
        cr.set_source(grad)
        cr.fill()
        # crest line
        cr.set_source_rgba(r, g, b, 0.95)
        cr.set_line_width(1.6)
        for i, v in enumerate(pts):
            y = h - (max(0.0, min(100.0, v)) / 100.0) * (h - 3) - 1
            (cr.move_to if i == 0 else cr.line_to)(i * step, y)
        cr.stroke()


class SystemPulseCard:
    """Live machine-health graphs: CPU · RAM · NET, plus temp/load/uptime."""

    HISTORY = 90  # seconds of history

    def __init__(self):
        from collections import deque
        self.root, content, self.set_footer = make_card(
            "cyan", "System Pulse", "◉",
            "sampling /proc · 1s cadence")

        self.cpu_hist = deque([0.0] * self.HISTORY, maxlen=self.HISTORY)
        self.ram_hist = deque([0.0] * self.HISTORY, maxlen=self.HISTORY)
        self.net_hist = deque([0.0] * self.HISTORY, maxlen=self.HISTORY)
        self._prev_cpu = self._read_cpu_raw()
        self._prev_net = self._read_net_raw()
        self._net_peak = 1.0  # bytes/s autoscale for the net sparkline

        grid = Gtk.Grid()
        grid.set_column_spacing(14)
        grid.set_row_spacing(2)
        grid.set_column_homogeneous(True)

        self._value_labels = {}
        specs = [
            ("CPU", "pink",   self.cpu_hist, 0),
            ("RAM", "purple", self.ram_hist, 1),
            ("NET", "cyan",   self.net_hist, 2),
        ]
        for title, color_key, hist, col in specs:
            head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            t = Gtk.Label(label=title, xalign=0.0)
            t.add_css_class("pulse-metric-title")
            v = Gtk.Label(label="—", xalign=1.0)
            v.add_css_class("pulse-metric-value")
            v.set_hexpand(True)
            head.append(t)
            head.append(v)
            self._value_labels[title] = v
            grid.attach(head, col, 0, 1, 1)
            grid.attach(_Sparkline(PALETTE[color_key], hist), col, 1, 1, 1)

        content.append(grid)
        self._sparks = grid
        GLib.timeout_add(1000, self._tick)
        self._tick()

    # ── /proc readers ────────────────────────────────────────────────
    @staticmethod
    def _read_cpu_raw():
        with open("/proc/stat") as f:
            parts = f.readline().split()[1:]
        vals = [int(x) for x in parts]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        return idle, sum(vals)

    @staticmethod
    def _read_mem_pct():
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k] = int(v.strip().split()[0])
                if len(info) > 4 and "MemAvailable" in info:
                    break
        total = info.get("MemTotal", 1)
        avail = info.get("MemAvailable", total)
        return 100.0 * (total - avail) / total, total

    @staticmethod
    def _read_net_raw():
        rx = tx = 0
        with open("/proc/net/dev") as f:
            for line in f.readlines()[2:]:
                name, data = line.split(":", 1)
                if name.strip() == "lo":
                    continue
                cols = data.split()
                rx += int(cols[0])
                tx += int(cols[8])
        return rx + tx

    @staticmethod
    def _read_temp():
        import glob as _glob
        best = None
        for hw in _glob.glob("/sys/class/hwmon/hwmon*"):
            try:
                name = open(os.path.join(hw, "name")).read().strip()
            except OSError:
                continue
            if name in ("coretemp", "k10temp", "zenpower", "acpitz"):
                try:
                    best = int(open(os.path.join(hw, "temp1_input")).read()) / 1000
                    break
                except OSError:
                    continue
        return best

    # ── 1 Hz sampler ─────────────────────────────────────────────────
    def _tick(self):
        # CPU
        idle, total = self._read_cpu_raw()
        didle = idle - self._prev_cpu[0]
        dtotal = max(1, total - self._prev_cpu[1])
        self._prev_cpu = (idle, total)
        cpu = 100.0 * (1.0 - didle / dtotal)
        self.cpu_hist.append(cpu)
        self._value_labels["CPU"].set_text(f"{cpu:4.0f}%")

        # RAM
        ram, total_kb = self._read_mem_pct()
        self.ram_hist.append(ram)
        self._value_labels["RAM"].set_text(
            f"{ram:4.0f}% of {total_kb / 1048576:.0f}G")

        # NET (autoscaling: history stored as % of rolling peak)
        cur = self._read_net_raw()
        rate = max(0, cur - self._prev_net)
        self._prev_net = cur
        self._net_peak = max(self._net_peak * 0.995, rate, 1024.0)
        self.net_hist.append(100.0 * rate / self._net_peak)
        if rate >= 1048576:
            self._value_labels["NET"].set_text(f"{rate / 1048576:.1f} MB/s")
        elif rate >= 1024:
            self._value_labels["NET"].set_text(f"{rate / 1024:.0f} KB/s")
        else:
            self._value_labels["NET"].set_text(f"{rate} B/s")

        # footer: load · temp · uptime
        try:
            load1, load5, _ = os.getloadavg()
            up = float(open("/proc/uptime").read().split()[0])
            hrs, mins = int(up // 3600), int(up % 3600 // 60)
            temp = self._read_temp()
            tstr = f" · {temp:.0f}°C" if temp is not None else ""
            self.set_footer(
                f"load {load1:.2f} / {load5:.2f}{tstr} · up {hrs}h {mins:02d}m")
        except OSError:
            pass

        # repaint sparklines
        child = self._sparks.get_first_child()
        while child is not None:
            if isinstance(child, _Sparkline):
                child.queue_draw()
            child = child.get_next_sibling()
        return True
