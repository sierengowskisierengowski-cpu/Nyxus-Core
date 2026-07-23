"""
NYXUS Panel — entry point.

A GTK4 flyout panel modeled after the Windows 11 News & Interests popup,
fully NYXUS-themed: graffiti collage background, hand-drawn Inter Display font,
neon glow accents, no emojis (Font Awesome / Nerd Font glyphs only).

Behavior
────────
  • Fixed 460 × 680 floating window
  • Toggle behavior — re-running the script kills the running instance
    (so binding it to a Waybar custom module gives a click-to-toggle button)
  • Auto-closes on Escape and on focus-out
  • Slides up on open, slides down on close (unless settings.reduce_animations)
  • Graffiti background is rendered once via Cairo and cached
  • All work that can block the UI runs on a background thread

Layout
──────
  ┌──────────────────────────────────────────────┐
  │  📍 Location          ↻  ✎  ⋯                │   ← header
  ├──────────────────────────┬───────────────────┤
  │                          │  ☀ 72°  Sunny     │   ← weather tile
  │                          ├───────────────────┤
  │     [hero news card]     │  CPU ▰▰░░ 41 %    │   ← system tile
  │                          │  RAM ▰▰▰░ 63 %    │
  │                          │  GPU ▰▰▰▰ 78 %    │
  │                          │  NET ↓1.2  ↑0.3   │
  ├──────────────────────────┴───────────────────┤
  │   [sub-card]   [sub-card]   [sub-card]  …    │   ← news feed
  │   (scrollable)                                │
  ├──────────────────────────────────────────────┤
  │   See more news    🖳 ⚙ 🛡 ✦ 🤖 🗀            │   ← footer
  └──────────────────────────────────────────────┘

© 2026 Joseph A. Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import math
import os
import random
import shlex
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

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
    WHITE_PURE='#ffffff'; WHITE_OFF='#eef2fa'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    INK_FADED='#0a0a0a'; INK_BLACK='#000000'
    GLASS_DARK='#14141a'
    GLASS_DEEPER='#0a0a0e'
    GLASS_DEEPEST='#000000'
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


# ── allow `import settings` etc. when launched as a script
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Gio, GLib, GObject, Pango  # noqa: E402

# Layer-shell is optional — without it we still get a floating window,
# we just can't anchor to the screen edge.
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell  # type: ignore
    _HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    _HAS_LAYER_SHELL = False

import cairo  # type: ignore

from settings import (
    CFG_DIR, CACHE_DIR, load_config, save_config, SettingsWindow,
)
from news_feed     import NewsEngine
from news_card     import HeroCard, SubCard
from weather_widget import WeatherWidget
from system_widget  import SystemWidget

# ──────────────────────────────────────────────── constants
APP_ID    = "io.nyxus.panel"
PANEL_W   = 460
PANEL_H   = 680
PID_FILE  = Path("/tmp/nyxus-panel.pid")
BG_DIR    = Path(os.path.expanduser("~/.cache/nyxus-panel"))
BG_DIR.mkdir(parents=True, exist_ok=True)
BG_PATH   = BG_DIR / f"bg-matte-{PANEL_W}x{PANEL_H}.png"

# NYXUS palette
C_BG       = (0.020, 0.020, 0.024)
C_PANEL    = "#000000"
# HUD neon family — accent.json-live via the shared palette helpers.
try:
    from nyxus_palette import (HUD_PALETTE, install_hud_css,
                               neon_flicker_css)
except Exception:
    HUD_PALETTE = {"pink": "#ff2dad", "cyan": "#2bd2ff", "gold": "#ff8a1e",
                   "purple": "#7d3dff", "green": "#7dff5e",
                   "red": "#ff2d55", "mono": "#eef2fa"}
    def neon_flicker_css():  # noqa: E704
        return ""
    install_hud_css = None

C_PINK     = HUD_PALETTE["pink"]
C_PURPLE   = HUD_PALETTE["purple"]
C_CYAN     = HUD_PALETTE["cyan"]
C_GOLD     = HUD_PALETTE["gold"]
C_GREEN    = HUD_PALETTE["green"]
C_TEXT     = "#eef2fa"
C_DIM      = "#c8ccd6"


# ──────────────────────────────────────────────── PID toggle
def _running_pid() -> Optional[int]:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None
    # check if alive
    try:
        os.kill(pid, 0)
        return pid
    except OSError:
        try:
            PID_FILE.unlink()
        except OSError:
            pass
        return None


def _write_pid() -> None:
    try:
        PID_FILE.write_text(str(os.getpid()))
    except OSError:
        pass


def _clear_pid() -> None:
    try:
        if PID_FILE.exists() and PID_FILE.read_text().strip() == str(os.getpid()):
            PID_FILE.unlink()
    except OSError:
        pass


# ──────────────────────────────────────────────── graffiti background
def _render_background(width: int = PANEL_W, height: int = PANEL_H,
                       seed: int = 0xDEADBEEF) -> str:
    """Render a graffiti collage to BG_PATH and return its path.  Cached."""
    if BG_PATH.exists():
        return str(BG_PATH)

    rng = random.Random(seed)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    cr   = cairo.Context(surf)

    # ── matte black paint base (rev r18: graffiti removed by user request)
    cr.set_source_rgb(0.078, 0.078, 0.102)   # #14141a — matte paint
    cr.rectangle(0, 0, width, height); cr.fill()

    # ── faint vignette so widgets read on top
    vg = cairo.RadialGradient(width / 2, height / 2, height * 0.25,
                              width / 2, height / 2, height * 0.85)
    vg.add_color_stop_rgba(0.0, 0, 0, 0, 0.0)
    vg.add_color_stop_rgba(1.0, 0, 0, 0, 0.45)
    cr.set_source(vg); cr.rectangle(0, 0, width, height); cr.fill()

    surf.write_to_png(str(BG_PATH))
    return str(BG_PATH)


# ──────────────────────────────────────────────── CSS
def _install_css(cfg: Dict[str, Any]) -> None:
    css = f"""
    * {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   14px;
        color:       {C_TEXT};
    }}

    /* root window — cosmic scene shows through transparent shell */
    .nyxus-panel {{
        background-color:    transparent;
        background-image:    none;
    }}

    /* every floating panel is a near-black HUD card (nyxus-home voice) */
    .nyxus-tile,
    .nyxus-card,
    .nyxus-header,
    .nyxus-footer,
    .nyxus-feed {{
        background-color: rgba(7, 5, 14, 0.93);
        border:           1px dashed alpha({C_CYAN}, 0.45);
        border-top:       2px solid {C_CYAN};
        border-radius:    8px;
        box-shadow:       0 0 14px alpha({C_CYAN}, 0.16),
                          inset 0 0 24px rgba(0, 0, 0, 0.18);
    }}

    /* HEADER — pink family + spray wordmark */
    .nyxus-header {{
        margin: 8px 8px 4px 8px;
        padding: 6px 10px;
        border-color: alpha({C_PINK}, 0.45);
        border-top-color: {C_PINK};
        box-shadow: 0 0 14px alpha({C_PINK}, 0.20),
                    inset 0 0 24px rgba(0, 0, 0, 0.18);
    }}
    .nyxus-header-loc {{
        font-family: "Permanent Marker", cursive;
        font-size:   21px;
        color:       {C_PINK};
        text-shadow: 0 0 10px alpha({C_PINK}, 0.70),
                     0 0 24px alpha({C_PINK}, 0.35);
    }}
    .nyxus-header-icon {{
        font-family: "JetBrains Mono Nerd Font", "Symbols Nerd Font", monospace;
        font-size:   18px;
        color:       {C_TEXT};
        background:  transparent;
        padding:     6px 8px;
        border-radius: 8px;
        border:      none;
    }}
    .nyxus-header-icon:hover {{
        background:  rgba(255, 255, 255, 0.38);
        color:       {C_GOLD};
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.85);
    }}

    /* TILES (weather + system) */
    .nyxus-tile {{
        margin: 4px;
    }}
    .nyxus-tile-title {{
        font-family: "JetBrains Mono", monospace;
        font-size:   11px;
        font-weight: bold;
        letter-spacing: 0.24em;
        color:       {C_CYAN};
        text-shadow: 0 0 8px alpha({C_CYAN}, 0.45);
    }}
    .nyxus-tile-icon {{
        font-family: "JetBrains Mono Nerd Font", monospace;
        font-size:   16px;
        color:       {C_GOLD};
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.65);
    }}
    .nyxus-tile-stamp {{
        color:       {C_DIM};
        font-size:   11px;
    }}

    .nyxus-tile-weather {{
        border-color: rgba(255, 255, 255, 0.45);
    }}
    .nyxus-weather-glyph {{
        font-family: "JetBrains Mono Nerd Font", monospace;
        font-size:   46px;
        color:       {C_GOLD};
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.55);
    }}
    .nyxus-weather-temp {{
        font-family: "Orbitron", "JetBrains Mono", monospace;
        font-size:   40px;
        font-weight: bold;
        color:       {C_CYAN};
        text-shadow: 0 0 12px alpha({C_CYAN}, 0.55),
                     0 0 26px alpha({C_CYAN}, 0.25);
    }}
    .nyxus-weather-cond {{
        font-size:   16px; color: {C_TEXT};
    }}
    .nyxus-weather-hilo {{
        font-family: "JetBrains Mono Nerd Font", monospace;
        font-size:   12px; color: {C_DIM};
    }}

    .nyxus-tile-system {{
        border-color: rgba(255, 255, 255, 0.40);
    }}
    .nyxus-stat-icon {{
        font-family: "JetBrains Mono Nerd Font", monospace;
        font-size:   14px; color: {C_PURPLE};
    }}
    .nyxus-stat-label {{
        font-size: 12px; color: {C_DIM}; font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
    }}
    .nyxus-stat-value {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   12px;
    }}
    .nyxus-stat-green  {{ color: {C_GREEN}; text-shadow: 0 0 6px rgba(255, 255, 255, 0.45); }}
    .nyxus-stat-yellow {{ color: {C_GOLD};  text-shadow: 0 0 6px rgba(255, 255, 255, 0.45); }}
    .nyxus-stat-red    {{ color: #c8ccd6;   text-shadow: 0 0 6px #14141a; }}
    levelbar.nyxus-stat-bar block.filled {{
        background-color: {C_PURPLE}; min-height: 6px; border-radius: 3px;
    }}
    levelbar.nyxus-stat-bar block.high   {{ background-color: {C_GOLD}; }}
    levelbar.nyxus-stat-bar block.full   {{ background-color: #c8ccd6; }}
    levelbar.nyxus-stat-bar trough {{
        background-color: rgba(255, 255, 255, 0.06); border-radius: 3px; min-height: 6px;
    }}

    /* NEWS feed */
    .nyxus-feed {{
        margin: 4px;
        padding: 6px;
        border-color: rgba(255, 255, 255, 0.55);
    }}
    scrolledwindow undershoot.top, scrolledwindow undershoot.bottom {{ background: none; }}

    .nyxus-card {{
        margin: 4px 2px;
        padding: 0;
        border-radius: 8px;
        border: 1px dashed alpha({C_PURPLE}, 0.40);
        border-top: 2px solid alpha({C_PURPLE}, 0.80);
        background-color: rgba(0, 0, 0, 0.55);
        transition: box-shadow 320ms ease, border-color 320ms ease;
    }}
    .nyxus-card:hover {{
        border-color: {C_PURPLE};
        background-color: alpha({C_PURPLE}, 0.07);
        box-shadow: 0 0 18px alpha({C_PURPLE}, 0.35);
    }}
    .nyxus-card-img,
    .nyxus-card-img-placeholder {{
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
    }}
    .nyxus-card-img-placeholder {{
        background: linear-gradient(135deg,
            rgba(255, 255, 255, 0.40),
            rgba(255, 255, 255, 0.16));
    }}
    .nyxus-card-img-glyph {{
        font-family: "JetBrains Mono Nerd Font", monospace;
        font-size: 36px; color: rgba(255, 255, 255, 0.40);
    }}
    .nyxus-card-title-hero {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size: 22px; font-weight: bold;
        color: {C_TEXT};
    }}
    .nyxus-card-title {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size: 16px; font-weight: bold;
        color: {C_TEXT};
    }}
    .nyxus-card-source {{
        color: {C_PURPLE}; font-size: 11px; font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
    }}
    .nyxus-card-time {{
        color: {C_DIM}; font-size: 11px; font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
    }}
    button.nyxus-action {{
        font-family: "JetBrains Mono Nerd Font", monospace;
        font-size: 12px;
        background: transparent;
        border: none;
        color: {C_DIM};
        padding: 2px 8px;
    }}
    button.nyxus-action:hover {{
        color: {C_PINK};
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.35);
    }}
    button.nyxus-action.nyxus-action-active {{
        color: {C_PINK};
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.35);
    }}

    /* FOOTER */
    .nyxus-footer {{
        margin: 4px 8px 8px 8px;
        padding: 6px 10px;
        border-color: rgba(255, 255, 255, 0.35);
    }}
    .nyxus-footer-cta {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size: 16px; font-weight: bold;
        color: {C_CYAN};
        background: transparent; border: none;
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.55);
    }}
    .nyxus-footer-cta:hover {{
        color: {C_GOLD};
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.75);
    }}
    .nyxus-quick {{
        font-family: "JetBrains Mono Nerd Font", monospace;
        font-size: 16px;
        background: transparent;
        border: 1px solid rgba(255, 255, 255, 0.55);
        border-radius: 8px;
        color: {C_TEXT};
        padding: 4px 8px;
        margin: 0 2px;
    }}
    .nyxus-quick:hover {{
        border-color: {C_GOLD};
        color: {C_GOLD};
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.65);
    }}

    /* SETTINGS window */
    .nyxus-settings  {{ background-color: rgba(0, 0, 0, 0.98); }}
    .nyxus-title     {{ font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif; font-size: 26px; font-weight: bold;
                       color: {C_PINK}; text-shadow: 0 0 6px rgba(255, 255, 255, 0.35); }}
    .nyxus-subtitle  {{ font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif; font-size: 20px; color: {C_TEXT}; }}
    .nyxus-row-title {{ font-size: 14px; color: {C_TEXT}; }}
    .nyxus-help      {{ font-size: 11px; color: {C_DIM}; }}
    .nyxus-cat       {{ font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif; font-size: 11px;
                       color: {C_PURPLE}; margin-top: 14px; }}
    .nyxus-mono      {{ font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif; font-size: 11px; color: {C_DIM}; }}
    .nyxus-textarea  {{ background-color: rgba(0,0,0,0.40); color: {C_TEXT};
                       font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif; font-size: 12px; padding: 6px; }}
    button.nyxus-btn-primary {{
        background: rgba(255, 255, 255, 0.50); color: {C_TEXT};
        border: 2px solid {C_PURPLE}; border-radius: 8px;
        padding: 6px 16px; font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif; font-size: 16px;
    }}
    button.nyxus-btn-primary:hover {{
        background: rgba(255, 255, 255, 0.65);
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.35);
    }}
    button.nyxus-btn-ghost {{
        background: transparent; color: {C_DIM};
        border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 8px;
        padding: 6px 14px;
    }}
    button.nyxus-btn-ghost:hover {{ color: {C_TEXT}; border-color: {C_PURPLE}; }}
    button.nyxus-btn-danger {{
        background: rgba(8, 12, 20, 0.20); color: #c8ccd6;
        border: 1px solid #c8ccd6; border-radius: 8px;
        padding: 6px 14px;
    }}
    .nyxus-listbox {{ background: transparent; }}
    .nyxus-listbox row {{ padding: 0; border: none; background: transparent; }}

    /* ── PREMIUM SETTINGS LAYOUT (sidebar nav + hero header) ────── */
    .nyxus-settings-outer {{
        background: rgba(0, 0, 0, 0.97);
    }}
    .nyxus-hero {{
        border-bottom: 1.5px dashed rgba(255, 255, 255, 0.40);
        padding-bottom: 14px;
    }}
    .nyxus-hero-glyph {{
        font-family: "JetBrains Mono Nerd Font", "Symbols Nerd Font", monospace;
        font-size: 32px; color: {C_PURPLE};
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.85),
                     0 0 22px rgba(255, 255, 255, 0.45);
        padding: 6px 12px;
        border: 1.5px solid rgba(255, 255, 255, 0.55);
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.10);
    }}
    .nyxus-hero-title {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size: 30px; font-weight: bold; color: {C_PINK};
        text-shadow: 0 0 8px rgba(255, 255, 255, 0.55);
    }}
    .nyxus-hero-sub {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size: 17px; color: {C_TEXT}; opacity: 0.85;
    }}
    .nyxus-hero-ver {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size: 16px; color: {C_DIM};
        padding: 4px 10px;
        border: 1px dashed rgba(255, 255, 255, 0.25);
        border-radius: 999px;
    }}

    .nyxus-sidebar {{
        background: rgba(255, 255, 255, 0.05);
        border-right: 1px dashed rgba(255, 255, 255, 0.30);
        padding-right: 6px;
    }}
    button.nyxus-sidebar-btn {{
        background: transparent;
        border: 1.5px solid transparent;
        border-radius: 10px;
        padding: 8px 12px;
        margin: 1px 0;
        color: {C_TEXT};
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size: 17px;
        transition: all 0.14s ease;
    }}
    button.nyxus-sidebar-btn:hover {{
        background: rgba(255, 255, 255, 0.12);
        border-color: rgba(255, 255, 255, 0.45);
    }}
    button.nyxus-sidebar-btn:checked,
    button.nyxus-sidebar-btn:active {{
        background: rgba(255, 255, 255, 0.18);
        border-color: rgba(255, 255, 255, 0.65);
        color: {C_PINK};
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.55);
    }}
    .nyxus-sidebar-glyph {{
        font-family: "JetBrains Mono Nerd Font", "Symbols Nerd Font", monospace;
        font-size: 16px;
    }}
    .nyxus-sidebar-label {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size: 17px;
    }}

    .nyxus-footer-bar {{
        border-top: 1.5px dashed rgba(255, 255, 255, 0.35);
        padding-top: 10px;
    }}
    .nyxus-footer-credit {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size: 13px; color: {C_DIM};
    }}
    """
    css += neon_flicker_css()
    # PRIORITY_USER + 1 so HUD cards outrank the nyxus_chrome layer.
    if install_hud_css is None or not install_hud_css(css):
        provider = Gtk.CssProvider()
        provider.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_USER + 1,
        )


# ──────────────────────────────────────────────── helpers
def _detached(cmd: str) -> None:
    try:
        subprocess.Popen(
            cmd, shell=True,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def _has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _open_url(url: str, cfg: Dict[str, Any]) -> None:
    browser = cfg.get("browser", "chromium")
    args = [browser]
    if cfg.get("browser_private"):
        if browser in ("chromium", "google-chrome", "brave"):
            args.append("--incognito")
        elif browser == "firefox":
            args.append("--private-window")
    args.append(url)
    try:
        subprocess.Popen(args, start_new_session=True,
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        try:
            subprocess.Popen(["xdg-open", url], start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass


def _read_weather_city() -> str:
    p = Path(os.path.expanduser("~/.nyxus/weather.json"))
    if not p.exists():
        return "Set city in Weather"
    try:
        import json as _json
        with p.open() as f:
            return (_json.load(f).get("city") or "Set city in Weather").upper()
    except Exception:
        return "Set city in Weather"


# ──────────────────────────────────────────────── panel window
class PanelWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application):
        super().__init__(application=app)
        self.set_title("NYXUS Panel")
        self.set_default_size(PANEL_W, PANEL_H)
        self.set_resizable(False)
        self.set_decorated(False)
        self.add_css_class("nyxus-panel")

        self._cfg = load_config()
        _install_css(self._cfg)

        # Layer-shell: anchor to bottom-right (above taskbar)
        if _HAS_LAYER_SHELL:
            try:
                LayerShell.init_for_window(self)
                LayerShell.set_layer(self, LayerShell.Layer.OVERLAY)
                LayerShell.set_keyboard_mode(self, LayerShell.KeyboardMode.ON_DEMAND)
                if self._cfg.get("panel_position", "above-taskbar") == "side":
                    LayerShell.set_anchor(self, LayerShell.Edge.RIGHT, True)
                    LayerShell.set_anchor(self, LayerShell.Edge.TOP, True)
                    LayerShell.set_margin(self, LayerShell.Edge.TOP,    20)
                    LayerShell.set_margin(self, LayerShell.Edge.RIGHT,  60)
                else:
                    LayerShell.set_anchor(self, LayerShell.Edge.BOTTOM, True)
                    LayerShell.set_anchor(self, LayerShell.Edge.RIGHT,  True)
                    LayerShell.set_margin(self, LayerShell.Edge.BOTTOM, 60)
                    LayerShell.set_margin(self, LayerShell.Edge.RIGHT,  10)
            except Exception:
                pass

        # ── Revealer for slide animation
        self._revealer = Gtk.Revealer()
        self._revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self._revealer.set_transition_duration(0 if self._cfg.get("reduce_animations") else 220)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_size_request(PANEL_W, PANEL_H)

        try:
            from nyxus_cosmic_bg import CosmicSceneArea
            cosmic_wrap = Gtk.Overlay()
            cosmic_wrap.set_child(CosmicSceneArea("nebula_moon"))
            cosmic_wrap.add_overlay(outer)
            self._revealer.set_child(cosmic_wrap)
        except Exception:
            self._revealer.set_child(outer)

        self.set_child(self._revealer)

        outer.append(self._build_header())

        # body: row with [left=feed] [right=tiles]
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        body.set_vexpand(True); body.set_hexpand(True)
        outer.append(body)

        # ── right column: weather + system tiles
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        right.set_size_request(180, -1)
        right.set_margin_top(0); right.set_margin_bottom(0)
        right.set_margin_start(0); right.set_margin_end(4)
        self._weather = WeatherWidget(); right.append(self._weather)
        self._system  = SystemWidget();  right.append(self._system)

        # ── left column: news feed
        feed_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        feed_wrap.set_hexpand(True); feed_wrap.set_vexpand(True)
        feed_wrap.add_css_class("nyxus-feed")
        feed_wrap.set_margin_start(4)
        feed_wrap.set_margin_top(4); feed_wrap.set_margin_bottom(0)

        self._feed_status = Gtk.Label(label="Loading news…")
        self._feed_status.add_css_class("nyxus-help"); self._feed_status.set_xalign(0)
        self._feed_status.set_margin_start(8); self._feed_status.set_margin_top(6)
        feed_wrap.append(self._feed_status)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True); scroller.set_hexpand(True)
        feed_wrap.append(scroller)

        self._feed_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._feed_box.set_margin_start(4); self._feed_box.set_margin_end(4)
        self._feed_box.set_margin_top(2); self._feed_box.set_margin_bottom(4)
        scroller.set_child(self._feed_box)

        body.append(feed_wrap)
        body.append(right)

        outer.append(self._build_footer())

        # ── close on Escape ONLY — flyout stays open while user works in it.
        # User explicitly asked panel to "stay open when mouse moves into it"
        # and "Only close when clicking completely outside". The cleanest way
        # to honor that is to drop the focus-out auto-dismiss; user dismisses
        # by clicking the Waybar Panel button again (PID toggle) or pressing
        # Escape.
        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._on_key)
        self.add_controller(kc)

        # ── news engine
        self._news = NewsEngine(lambda: self._cfg)
        self._news.add_listener(self._on_news)
        # paint cache instantly so the panel never looks empty
        self._on_news(self._news.cached())
        self._news.start_auto_refresh()

        # ── reveal after attaching
        GLib.timeout_add(20, lambda: (self._revealer.set_reveal_child(True), False)[1])

    # ────────────── header
    def _build_header(self) -> Gtk.Widget:
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hdr.add_css_class("nyxus-header")

        loc_pin = Gtk.Label(label="\uf3c5")
        loc_pin.add_css_class("nyxus-tile-icon")
        self._loc_lbl = Gtk.Label(label=_read_weather_city())
        self._loc_lbl.add_css_class("nyxus-header-loc"); self._loc_lbl.set_xalign(0)
        self._loc_lbl.set_hexpand(True)

        refresh = Gtk.Button(label="\uf2f1")  # FA arrows-rotate
        refresh.add_css_class("nyxus-header-icon")
        refresh.set_tooltip_text("Refresh all content")
        refresh.connect("clicked", lambda *_: self._refresh_all())

        pencil = Gtk.Button(label="\uf303")  # FA pen
        pencil.add_css_class("nyxus-header-icon")
        pencil.set_tooltip_text("Panel settings")
        pencil.connect("clicked", lambda *_: self._open_settings())

        dots = Gtk.MenuButton()
        dots.set_icon_name("view-more-symbolic")
        dots.add_css_class("nyxus-header-icon")
        dots.set_tooltip_text("More")
        dots.set_label("\uf142")  # FA ellipsis-vertical
        # popover with 4 items
        pop = Gtk.Popover()
        pbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                       margin_top=6, margin_bottom=6, margin_start=6, margin_end=6)
        for label, handler in (
            ("Open on hover",         self._toggle_hover),
            ("Reduce animations",     self._toggle_anim),
            ("Notification settings", self._open_settings),
            ("About NYXUS Panel",     self._show_about),
        ):
            b = Gtk.Button(label=label)
            b.add_css_class("nyxus-btn-ghost")
            b.connect("clicked", lambda _b, h=handler: (pop.popdown(), h()))
            pbox.append(b)
        pop.set_child(pbox)
        dots.set_popover(pop)

        hdr.append(loc_pin); hdr.append(self._loc_lbl)
        hdr.append(refresh); hdr.append(pencil); hdr.append(dots)
        return hdr

    # ────────────── footer
    def _build_footer(self) -> Gtk.Widget:
        ft = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ft.add_css_class("nyxus-footer")

        cta = Gtk.Button(label="\uf35d  See more tech news")
        cta.add_css_class("nyxus-footer-cta")
        cta.set_hexpand(True); cta.set_halign(Gtk.Align.START)
        cta.connect("clicked", lambda *_: _open_url("https://news.ycombinator.com/", self._cfg))
        ft.append(cta)

        # quick-launch row
        quick = (
            ("\uf120", "NYXUS Terminal", "python3 ~/.nyxus/nyxus_terminal.py"),
            ("\uf013", "NYXUS Settings", "nyxus-settings"),
            ("\uf3ed", "NYXUS Shield",   "python3 -m shield.main"),
            ("\uf005", "GodsApp",        "python3 -m godsapp.main"),
            ("\uf544", "NYXUS SAGE",     "nyxus-sage || python3 -m sage.main"),
            ("\uf07b", "Files",          "thunar || nautilus || pcmanfm-qt || dolphin"),
        )
        for glyph, tip, cmd in quick:
            b = Gtk.Button(label=glyph)
            b.add_css_class("nyxus-quick")
            b.set_tooltip_text(tip)
            b.connect("clicked", lambda _b, c=cmd: _detached(c))
            ft.append(b)

        return ft

    # ────────────── header callbacks
    def _toggle_hover(self) -> None:
        self._cfg["open_on_hover"] = not self._cfg.get("open_on_hover", False)
        save_config(self._cfg)

    def _toggle_anim(self) -> None:
        self._cfg["reduce_animations"] = not self._cfg.get("reduce_animations", False)
        save_config(self._cfg)
        self._revealer.set_transition_duration(0 if self._cfg["reduce_animations"] else 220)

    def _show_about(self) -> None:
        about = Gtk.AboutDialog(transient_for=self, modal=True)
        about.set_program_name("NYXUS Panel")
        about.set_version("1.0")
        about.set_comments("News, weather, and system stats — Windows-style flyout, NYXUS-themed.")
        about.set_copyright("© 2026 Joseph A. Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED")
        about.set_license_type(Gtk.License.MIT_X11)
        about.present()

    def _open_settings(self) -> None:
        def _on_saved(new_cfg: Dict[str, Any]):
            self._cfg = new_cfg
            self._news.start_auto_refresh()
        win = SettingsWindow(on_saved=_on_saved)
        win.set_transient_for(self)
        win.present()

    # ────────────── refresh
    def _refresh_all(self) -> None:
        self._loc_lbl.set_text(_read_weather_city())
        self._weather.refresh()
        self._news.refresh_async()
        self._feed_status.set_text("Refreshing…")

    # ────────────── news rendering
    def _on_news(self, articles: List[Dict[str, Any]]) -> None:
        # remove existing children
        c = self._feed_box.get_first_child()
        while c is not None:
            nxt = c.get_next_sibling()
            self._feed_box.remove(c)
            c = nxt

        if not articles:
            self._feed_status.set_text("No articles yet — try Refresh.")
            return
        self._feed_status.set_text(f"{len(articles)} articles · {time.strftime('%H:%M')}")

        cfg_get = lambda: self._cfg
        cfg_set = lambda c: (self._cfg.update(c), save_config(self._cfg))[1]

        # hero
        self._feed_box.append(HeroCard(articles[0], cfg_get, cfg_set))
        # subs
        for art in articles[1:]:
            self._feed_box.append(SubCard(art, cfg_get, cfg_set))

    # ────────────── lifecycle
    def _on_key(self, _ctrl, keyval, _kc, _state):
        if keyval == Gdk.KEY_Escape:
            self._dismiss()
            return True
        return False

    def _dismiss(self) -> None:
        if self._cfg.get("reduce_animations"):
            self._real_close()
            return
        self._revealer.set_reveal_child(False)
        GLib.timeout_add(240, lambda: (self._real_close(), False)[1])

    def _real_close(self) -> None:
        try:
            self._system.stop()
            self._news.stop_auto_refresh()
        except Exception:
            pass
        self.close()


# ──────────────────────────────────────────────── application
class NyxusPanelApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        win = PanelWindow(self)
        win.present()


def _kill_existing(pid: int) -> None:
    """Send SIGTERM to a running panel instance — its handler will close cleanly."""
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        pass


def main(argv: Optional[List[str]] = None) -> int:
    argv = argv or sys.argv

    # toggle: if another instance is alive, ask it to close, then exit.
    pid = _running_pid()
    if pid:
        _kill_existing(pid)
        try:
            PID_FILE.unlink()
        except OSError:
            pass
        return 0

    _write_pid()

    def _handle_sig(_signum, _frame):
        # gracefully quit — main loop will tear down the window
        try:
            app.quit()
        except Exception:
            pass

    signal.signal(signal.SIGTERM, _handle_sig)
    signal.signal(signal.SIGINT,  _handle_sig)

    app = NyxusPanelApp()
    try:
        return app.run(argv)
    finally:
        _clear_pid()


if __name__ == "__main__":
    sys.exit(main())


# ─────────────────────────── NYXUS CHROME (auto-injected r4) ────────────────
# Unifies look across every NYXUS GTK4 app: fully transparent window so the
# user's desktop wallpaper shows through, frosted-glass dark panels, Inter Display
# font, neon-pink outlined buttons, hover-scramble labels. install_chrome()
# is idempotent and runs once per top-level window via a `present` hook.
# nyxus_chrome.py is shipped to ~/.nyxus by the install pipeline.
try:
    import os as _nyx_os, sys as _nyx_sys
    _nyx_chrome_dir = _nyx_os.path.expanduser("~/.nyxus")
    if _nyx_chrome_dir not in _nyx_sys.path:
        _nyx_sys.path.insert(0, _nyx_chrome_dir)
    try:
        from nyxus_chrome import install_chrome as _nyx_install_chrome
    except ImportError:
        _nyx_install_chrome = lambda *a, **kw: None  # noqa: E731 silent no-op
    _NYX_PAGE_KEY = "_panel"

    def _nyx_make_present_hook(_orig):
        def _nyx_present(self, *args, **kwargs):
            try:
                _nyx_install_chrome(self, page_key=_NYX_PAGE_KEY)
            except Exception:
                pass
            return _orig(self, *args, **kwargs)
        return _nyx_present

    # Gtk.Window.present — base case, also covers Gtk.ApplicationWindow.
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk as _NyxGtk
        if not getattr(_NyxGtk.Window, "_nyx_chrome_hooked", False):
            _NyxGtk.Window.present = _nyx_make_present_hook(_NyxGtk.Window.present)
            _NyxGtk.Window._nyx_chrome_hooked = True
    except Exception as _nyx_eg:
        import sys as _nyx_sys
        print("nyxus-chrome Gtk.Window hook skipped: %s" % _nyx_eg, file=_nyx_sys.stderr)

    # Adw.ApplicationWindow.present — covers shield, sage, studio, godsapp.
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Adw", "1")
        from gi.repository import Adw as _NyxAdw
        if not getattr(_NyxAdw.ApplicationWindow, "_nyx_chrome_hooked", False):
            _NyxAdw.ApplicationWindow.present = _nyx_make_present_hook(
                _NyxAdw.ApplicationWindow.present)
            _NyxAdw.ApplicationWindow._nyx_chrome_hooked = True
    except Exception:
        pass  # Adw is optional
except Exception as _nyx_e:
    import sys as _nyx_sys
    print("nyxus-chrome injection failed: %s" % _nyx_e, file=_nyx_sys.stderr)
