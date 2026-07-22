"""
NYXUS Panel — Weather tile.

Reads the city/lat/lon set by the user in the existing NYXUS Weather app
(at ~/.nyxus/weather.json) and fetches a fresh forecast from open-meteo.com
(no API key required).  Caches the response in ~/.config/nyxus-panel/cache/.

Click the tile to launch the full NYXUS Weather window.

© 2026 Joseph A. Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

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
from gi.repository import Gtk, GLib  # noqa: E402

from settings import CACHE_DIR

# ───────────────────────────── shared paths
WEATHER_CFG = Path(os.path.expanduser("~/.nyxus/weather.json"))
WEATHER_CACHE = CACHE_DIR / "weather.json"

# Map open-meteo's WMO weather codes to a label + Font-Awesome glyph.
# (Glyphs assume Font Awesome 6 / Nerd Font is installed.)
WMO = {
    0:  ("Clear",                   "\uf185"),  # sun
    1:  ("Mostly clear",            "\uf6c4"),
    2:  ("Partly cloudy",           "\uf6c4"),
    3:  ("Overcast",                "\uf0c2"),  # cloud
    45: ("Fog",                     "\uf75f"),
    48: ("Depositing rime fog",     "\uf75f"),
    51: ("Light drizzle",           "\uf73d"),
    53: ("Moderate drizzle",        "\uf73d"),
    55: ("Dense drizzle",           "\uf73d"),
    61: ("Light rain",              "\uf73d"),
    63: ("Moderate rain",           "\uf73d"),
    65: ("Heavy rain",              "\uf740"),
    71: ("Light snow",              "\uf2dc"),
    73: ("Moderate snow",           "\uf2dc"),
    75: ("Heavy snow",              "\uf2dc"),
    77: ("Snow grains",             "\uf2dc"),
    80: ("Rain showers",            "\uf73d"),
    81: ("Rain showers",            "\uf73d"),
    82: ("Violent rain showers",    "\uf740"),
    85: ("Snow showers",            "\uf2dc"),
    86: ("Heavy snow showers",      "\uf2dc"),
    95: ("Thunderstorm",            "\uf76c"),
    96: ("Thunderstorm + hail",     "\uf76c"),
    99: ("Severe thunderstorm",     "\uf76c"),
}


# ───────────────────────────── network fetcher
def _fetch_open_meteo(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    try:
        import requests  # type: ignore
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,apparent_temperature,weather_code"
            f"&daily=temperature_2m_max,temperature_2m_min"
            f"&temperature_unit=fahrenheit&timezone=auto"
        )
        r = requests.get(url, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception:
        return None


def _read_weather_cfg() -> Dict[str, Any]:
    if not WEATHER_CFG.exists():
        return {}
    try:
        with WEATHER_CFG.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _read_cache() -> Optional[Dict[str, Any]]:
    if not WEATHER_CACHE.exists():
        return None
    try:
        with WEATHER_CACHE.open() as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def _write_cache(payload: Dict[str, Any]) -> None:
    try:
        WEATHER_CACHE.parent.mkdir(parents=True, exist_ok=True)
        with WEATHER_CACHE.open("w") as f:
            json.dump(payload, f)
    except OSError:
        pass


# ───────────────────────────── widget
class WeatherWidget(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.add_css_class("nyxus-tile")
        self.add_css_class("nyxus-tile-weather")

        # header row: location + refresh
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                      margin_top=10, margin_start=14, margin_end=14)
        self._loc = Gtk.Label(label="—"); self._loc.set_xalign(0); self._loc.set_hexpand(True)
        self._loc.add_css_class("nyxus-tile-title")
        hdr.append(self._loc)
        self.append(hdr)

        # main row: glyph + temp
        main = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14,
                       margin_start=14, margin_end=14, margin_top=2, margin_bottom=2)
        self._glyph = Gtk.Label(label="\uf185"); self._glyph.add_css_class("nyxus-weather-glyph")
        self._temp  = Gtk.Label(label="—°"); self._temp.add_css_class("nyxus-weather-temp")
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2); col.set_hexpand(True)
        self._cond  = Gtk.Label(label="—"); self._cond.set_xalign(0); self._cond.add_css_class("nyxus-weather-cond")
        self._feels = Gtk.Label(label=""); self._feels.set_xalign(0); self._feels.add_css_class("nyxus-tile-stamp")
        col.append(self._cond); col.append(self._feels)
        main.append(self._glyph); main.append(self._temp); main.append(col)
        self.append(main)

        # hi/lo + click hint
        foot = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10,
                       margin_start=14, margin_end=14, margin_bottom=10, margin_top=2)
        self._hilo = Gtk.Label(label=""); self._hilo.set_xalign(0); self._hilo.set_hexpand(True)
        self._hilo.add_css_class("nyxus-weather-hilo")
        hint = Gtk.Label(label="\uf35d  open"); hint.add_css_class("nyxus-tile-stamp")
        foot.append(self._hilo); foot.append(hint)
        self.append(foot)

        # whole tile is clickable to launch NYXUS Weather
        click = Gtk.GestureClick()
        click.connect("released", lambda *_: self._launch_weather_app())
        self.add_controller(click)
        self.set_cursor_from_name("pointer")

        # initial paint from cache, then async refresh
        self._render_from_cache()
        self.refresh()

    # ─────────────── public API
    def refresh(self) -> None:
        threading.Thread(target=self._fetch_async, daemon=True).start()

    # ─────────────── render
    def _render_from_cache(self) -> None:
        c = _read_cache()
        cfg = _read_weather_cfg()
        city = (cfg.get("city") or "Set city in NYXUS Weather").upper()
        self._loc.set_text(city)
        if c is None:
            self._cond.set_text("Loading…")
            return
        self._render(c)

    def _render(self, payload: Dict[str, Any]) -> None:
        cur = payload.get("current") or {}
        daily = payload.get("daily") or {}
        code = int(cur.get("weather_code", 0))
        label, glyph = WMO.get(code, ("Unknown", "\uf186"))
        temp = cur.get("temperature_2m")
        feels = cur.get("apparent_temperature")
        unit = "°F"
        try:
            tmax = (daily.get("temperature_2m_max") or [None])[0]
            tmin = (daily.get("temperature_2m_min") or [None])[0]
        except Exception:
            tmax = tmin = None

        self._glyph.set_text(glyph)
        self._temp.set_text(f"{int(round(temp))}{unit}" if temp is not None else "—")
        self._cond.set_text(label)
        self._feels.set_text(f"feels like {int(round(feels))}{unit}" if feels is not None else "")
        if tmax is not None and tmin is not None:
            self._hilo.set_text(f"\uf062 {int(round(tmax))}{unit}    \uf063 {int(round(tmin))}{unit}")
        else:
            self._hilo.set_text("")

    def _fetch_async(self) -> None:
        cfg = _read_weather_cfg()
        lat = cfg.get("lat"); lon = cfg.get("lon")
        if lat is None or lon is None:
            return
        payload = _fetch_open_meteo(float(lat), float(lon))
        if payload is None:
            return
        payload["_fetched_at"] = time.time()
        _write_cache(payload)
        GLib.idle_add(self._render, payload)

    def _launch_weather_app(self) -> None:
        for p in ("~/.nyxus/nyxus_weather.py",
                  "~/.local/share/nyxus/nyxus_weather.py"):
            full = os.path.expanduser(p)
            if os.path.exists(full):
                subprocess.Popen(
                    ["python3", full],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                return


__all__ = ["WeatherWidget"]
