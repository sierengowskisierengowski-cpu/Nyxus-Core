"""
NYXUS Start — left-side flyout entry point.

A GTK4 flyout menu modeled on Windows 11 Start, fully NYXUS-themed:
graffiti collage background, hand-drawn Inter Display font, neon glow accents,
no emojis (Font Awesome / Nerd Font glyphs only).

Behavior
────────
  • Fixed 740 × 680 floating window (LEFT column 460px + notepad 280px)
  • Anchored bottom-LEFT via gtk4-layer-shell (above the Start button)
  • PID toggle — re-running the script kills the running instance
    so binding to the Waybar custom module gives a click-to-toggle button
  • Closes on Escape or by re-clicking the Waybar Start button
  • Slides up on open

Layout
──────
  ┌──────────────────────────────────┬────────────┐
  │  [👤 Joey/op]  [search]  09:42PM │ Scratchpad │
  ├──────────────────────────────────┤            │
  │  PINNED  (5-col grid, small)     │  ╭──────╮  │
  ├──────────────────────────────────┤  │ free │  │
  │  RECENTLY USED          ⌫ Clear  │  │ form │  │
  │  app · 2 min ago                 │  │ text │  │
  ├──────────────────────────────────┤  │ area │  │
  │  ALL APPS         [System]   ▾   │  │      │  │
  │  (alphabetical scroll list)      │  │ auto │  │
  ├──────────────────────────────────┤  │ save │  │
  │  GowskiNet · Phantom · …         │  ╰──────╯  │
  ├──────────────────────────────────┤            │
  │  [Joey] [⚙]  [⏻ ↻ ⏾ ⎋ 🔒]        │ open clear │
  └──────────────────────────────────┴────────────┘

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
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
from datetime import datetime
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
    WHITE_PURE='#ffffff'; WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
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


sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Gio, GLib, GObject, Pango  # noqa: E402

try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell  # type: ignore
    _HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    _HAS_LAYER_SHELL = False

import cairo  # type: ignore

from settings import (
    CFG_DIR, load_config, save_config,
    load_pins, save_pins, push_recent, clear_recent,
    load_scratch, save_scratch, store_avatar,
)
from apps import list_installed_apps, search_apps, find_app_by_id, NYXUS_CATEGORIES
from recent import list_recent, humanize_ts, remove_from_recent
from status import gather as gather_status
from power  import POWER_ACTIONS, perform as perform_power


# ──────────────────────────────────────────────── constants
APP_ID    = "io.nyxus.start"
LEFT_W    = 460          # main column (header / pinned / recent / power)
NOTEPAD_W = 280          # right-side built-in scratchpad sidebar
PANEL_W   = LEFT_W + NOTEPAD_W   # 740 — total flyout width
PANEL_H   = 680
PID_FILE  = Path("/tmp/nyxus-start.pid")
BG_DIR    = Path(os.path.expanduser("~/.cache/nyxus-start"))
BG_DIR.mkdir(parents=True, exist_ok=True)
BG_PATH   = BG_DIR / f"bg-matte-{PANEL_W}x{PANEL_H}.png"

C_TEXT    = "#e8edf5"
C_DIM     = "#c8ccd6"
C_PINK    = "#e8edf5"
C_PURPLE  = "#e8edf5"
C_CYAN    = "#c8ccd6"
C_GOLD    = "#e8edf5"
C_GREEN   = "#c8ccd6"
C_RED     = "#c8ccd6"


# ──────────────────────────────────────────────── PID toggle
def _running_pid() -> Optional[int]:
    if not PID_FILE.exists():
        return None
    try:
        pid = int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None
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
                       seed: int = 0xC0FFEE) -> str:
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


# ──────────────────────────────────────────────── CSS install
def _install_css(cfg: Dict[str, Any]) -> None:
    bg = _render_background()
    css = f"""
    * {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   14px;
        color:       {C_TEXT};
    }}

    /* ── GodsApp aesthetic: pure-black plates, chalky white sketched borders,
       big handwritten Inter Display headings, neon kept only as a faint accent.
       Background graffiti collage is preserved (the .nyxus-start image). */
    .nyxus-start {{
        background-image:    url("file://{bg}");
        background-size:     cover;
        background-position: center;
        background-color:    #0f1420;
    }}

    /* every floating section sits on a near-black plate with a chalky white
       hand-drawn border (mimics the GodsApp pencil-sketch frames). */
    .nyxus-section {{
        background-color: #000000;
        border:           1.5px solid rgba(255, 255, 255, 0.65);
        border-radius:    8px;
        margin:           4px 8px;
        padding:          8px 10px;
        box-shadow:       inset 0 0 0 1px rgba(255, 255, 255, 0.10);
    }}

    .nyxus-section-title {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:      14px;
        font-style:     italic;
        font-weight:    normal;
        color:          rgba(255, 255, 255, 0.78);
        text-shadow:    none;
        margin:         0 4px 6px 4px;
        letter-spacing: 0.5px;
    }}

    .nyxus-header {{
        background-color: #000000;
        border-bottom:    1.5px solid rgba(255, 255, 255, 0.70);
        padding:          10px 14px;
    }}
    .nyxus-brand {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:      32px;
        font-weight:    bold;
        color:          #ffffff;
        text-shadow:    0 0 1px rgba(255, 255, 255, 0.40);
        letter-spacing: 1px;
    }}
    .nyxus-username {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   18px;
        color:       #ffffff;
        text-shadow: none;
    }}
    .nyxus-time {{
        font-family: "JetBrains Mono Nerd Font", monospace;
        font-size:   12px;
        color:       rgba(255, 255, 255, 0.60);
        text-shadow: none;
    }}

    entry.nyxus-search {{
        background-color: #000000;
        border:           1.5px solid rgba(255, 255, 255, 0.60);
        border-radius:    6px;
        color:            #ffffff;
        font-family:      "JetBrains Mono Nerd Font", monospace;
        font-size:        13px;
        padding:          5px 12px;
        min-height:       28px;
    }}
    entry.nyxus-search:focus {{
        border-color: rgba(8, 12, 20, 0.85);
        box-shadow:   0 0 6px rgba(8, 12, 20, 0.45);
    }}

    /* generic item row (recent / search results / all apps) — looks like the
       GodsApp module list: just text on transparent, faint hover halo. */
    button.nyxus-row {{
        background:    transparent;
        border:        none;
        border-radius: 4px;
        padding:       5px 8px;
        color:         #ffffff;
    }}
    button.nyxus-row:hover {{
        background-color: rgba(255, 255, 255, 0.08);
        text-shadow:      none;
    }}
    .nyxus-row-title {{ font-size: 15px; color: #ffffff; }}
    .nyxus-row-sub   {{ font-size: 11px; color: rgba(255,255,255,0.55);
                        font-family: "JetBrains Mono Nerd Font", monospace; }}

    /* pinned grid tiles — chalky white frame, dark fill, soft hover. */
    button.nyxus-tile {{
        background-color: #0a0a0e;
        border:           1.5px solid rgba(255, 255, 255, 0.55);
        border-radius:    6px;
        padding:          4px 2px;
        margin:           3px;
        color:            #ffffff;
        min-width:        62px;
        min-height:       62px;
    }}
    button.nyxus-tile:hover {{
        border-color:     #ffffff;
        background-color: rgba(255, 255, 255, 0.10);
        box-shadow:       0 0 8px rgba(8, 12, 20, 0.40);
    }}
    .nyxus-tile-name {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   12px;
        color:       #ffffff;
    }}

    /* profile button — chalky frame, hover gives a subtle violet glow. */
    button.nyxus-profile-btn {{
        background:    #14141a;
        border:        1.5px solid rgba(255, 255, 255, 0.65);
        border-radius: 8px;
        padding:       4px 8px;
        min-width:     0;
    }}
    button.nyxus-profile-btn:hover {{
        border-color:     #ffffff;
        background-color: rgba(255, 255, 255, 0.10);
        box-shadow:       0 0 8px rgba(8, 12, 20, 0.40);
    }}
    .nyxus-avatar-frame {{
        background-color: #000000;
        border:           1.5px solid rgba(255, 255, 255, 0.85);
        border-radius:    50%;
        min-width:        38px;
        min-height:       38px;
        padding:          0;
        background-clip:  padding-box;
    }}
    .nyxus-avatar-frame > * {{
        border-radius: 50%;
    }}
    .nyxus-avatar-initials {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:    20px;
        font-weight:  bold;
        color:        #ffffff;
        text-shadow:  none;
    }}
    .nyxus-profile-name {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   20px;
        font-weight: bold;
        color:       #ffffff;
        text-shadow: none;
    }}
    .nyxus-profile-sub {{
        font-family: "JetBrains Mono Nerd Font", monospace;
        font-size:   10px;
        color:       rgba(255, 255, 255, 0.55);
    }}

    /* notepad sidebar — chalky divider, monospace status, handwritten body. */
    .nyxus-notepad-sidebar {{
        background-color: rgba(0, 0, 0, 0.88);
        border-left:      1.5px solid rgba(255, 255, 255, 0.65);
        padding:          12px 10px 10px 10px;
    }}
    .nyxus-notepad-title {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   24px;
        font-weight: bold;
        color:       #ffffff;
        text-shadow: none;
    }}
    .nyxus-notepad-saved {{
        font-family: "JetBrains Mono Nerd Font", monospace;
        font-size:   10px;
        color:       rgba(255, 255, 255, 0.55);
    }}
    textview.nyxus-notepad,
    textview.nyxus-notepad text {{
        background-color: #000000;
        color:            #ffffff;
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:        16px;
        padding:          8px;
    }}
    .nyxus-notepad-frame {{
        border:        1.5px solid rgba(255, 255, 255, 0.55);
        border-radius: 6px;
    }}

    /* status row — small monospace line, like GodsApp's "ready" footer. */
    .nyxus-status     {{ font-family: "JetBrains Mono Nerd Font", monospace;
                         font-size: 11px; color: rgba(255, 255, 255, 0.55); }}
    .nyxus-status-ok  {{ color: rgba(255, 255, 255, 0.85); text-shadow: none; }}
    .nyxus-status-bad {{ color: {C_RED};   text-shadow: 0 0 4px rgba(8, 12, 20, 0.45); }}

    /* power buttons — same chalky frame, subtle gold/red hover only. */
    button.nyxus-power {{
        font-family:   "JetBrains Mono Nerd Font", monospace;
        font-size:     18px;
        background:    #14141a;
        border:        1.5px solid rgba(255, 255, 255, 0.55);
        border-radius: 6px;
        color:         #ffffff;
        padding:       6px 12px;
        margin:        0 3px;
    }}
    button.nyxus-power:hover {{
        border-color: #ffffff;
        background-color: rgba(255, 255, 255, 0.08);
    }}
    button.nyxus-power-danger:hover {{
        border-color: {C_RED};
        color:        {C_RED};
        text-shadow:  0 0 6px rgba(8, 12, 20, 0.45);
    }}

    /* category chip — chalky pill (matches GodsApp's "Full sweep" buttons). */
    button.nyxus-chip {{
        background:    rgba(0, 0, 0, 0.65);
        border:        1.5px solid rgba(255, 255, 255, 0.55);
        border-radius: 6px;
        color:         #ffffff;
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:     14px;
        padding:       3px 12px;
        margin:        0 3px;
    }}
    button.nyxus-chip.active,
    button.nyxus-chip:hover {{
        border-color:     #ffffff;
        background-color: rgba(255, 255, 255, 0.10);
        box-shadow:       0 0 6px rgba(8, 12, 20, 0.40);
    }}

    /* small ghost button — dim white, lights up on hover. */
    button.nyxus-ghost {{
        background:  transparent;
        border:      none;
        color:       rgba(255, 255, 255, 0.60);
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   14px;
    }}
    button.nyxus-ghost:hover {{
        color:       #ffffff;
        text-shadow: none;
    }}

    scrolledwindow undershoot.top, scrolledwindow undershoot.bottom {{ background: none; }}
    scrollbar slider {{
        background-color: rgba(255, 255, 255, 0.45);
        border-radius:    6px;
        min-width: 6px; min-height: 6px;
    }}
    scrollbar slider:hover {{ background-color: #ffffff; }}

    popover.menu {{
        background-color: rgba(8, 4, 22, 0.97);
        border: 1px solid {C_PINK};
        border-radius: 8px;
    }}
    popover.menu modelbutton {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size: 14px;
        color: {C_TEXT};
        padding: 6px 12px;
    }}
    popover.menu modelbutton:hover {{
        background-color: rgba(8, 12, 20, 0.25);
        color: {C_PINK};
    }}

    /* ── Page switcher (Apps | Store) ──────────────────────────── */
    .nyxus-pageswitcher {{
        border-bottom: 1.5px dashed rgba(255, 255, 255, 0.30);
        padding-bottom: 6px;
    }}
    button.nyxus-page-btn {{
        background:    rgba(0, 0, 0, 0.35);
        color:         {C_TEXT};
        border:        1.5px solid rgba(255, 255, 255, 0.25);
        border-radius: 999px;
        padding:       4px 18px;
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:     17px;
        transition:    all 0.16s ease;
    }}
    button.nyxus-page-btn:hover {{
        border-color: {C_PURPLE};
        color:        #ffffff;
    }}
    button.nyxus-page-btn:checked,
    button.nyxus-page-btn:active {{
        background:    rgba(255, 255, 255, 0.20);
        border-color:  {C_PINK};
        color:         {C_PINK};
        text-shadow:   0 0 6px rgba(255, 255, 255, 0.65);
    }}

    /* ── Store page (inline App Store catalog) ─────────────────── */
    .nyxus-store-banner {{
        border-bottom: 1.5px dashed rgba(255, 255, 255, 0.30);
        padding-bottom: 8px;
    }}
    .nyxus-store-glyph {{
        font-family: "JetBrains Mono Nerd Font", "Symbols Nerd Font", monospace;
        font-size:   28px;
        color:       {C_GOLD};
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.55);
        padding:     4px 10px;
        border:      1.5px solid rgba(255, 255, 255, 0.55);
        border-radius: 12px;
        background:  rgba(255, 255, 255, 0.08);
    }}
    .nyxus-store-title {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   24px; font-weight: bold;
        color:       {C_PINK};
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.55);
    }}
    .nyxus-store-sub {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   14px;
        color:       {C_TEXT}; opacity: 0.80;
    }}
    .nyxus-store-card {{
        background:    rgba(255, 255, 255, 0.03);
        border:        1px dashed rgba(255, 255, 255, 0.18);
        border-radius: 10px;
        padding:       8px 10px;
    }}
    .nyxus-store-card:hover {{
        background:    rgba(255, 255, 255, 0.10);
        border-color:  rgba(255, 255, 255, 0.55);
    }}
    .nyxus-store-card-glyph {{
        font-family: "JetBrains Mono Nerd Font", "Symbols Nerd Font", monospace;
        font-size:   22px;
        color:       {C_PURPLE};
        text-shadow: 0 0 8px rgba(255, 255, 255, 0.55);
    }}
    .nyxus-store-card-title {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   17px; font-weight: bold;
        color:       {C_TEXT};
    }}
    .nyxus-store-card-tag {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   12px;
        color:       rgba(255, 255, 255, 0.65);
    }}
    button.nyxus-store-btn-install {{
        background:  rgba(255, 255, 255, 0.18);
        color:       #c8ccd6;
        border:      1.5px solid rgba(255, 255, 255, 0.65);
        border-radius: 8px;
        padding:     4px 14px;
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   14px;
    }}
    button.nyxus-store-btn-install:hover {{
        background:  rgba(255, 255, 255, 0.30);
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.65);
    }}
    button.nyxus-store-btn-open {{
        background:  rgba(255, 255, 255, 0.18);
        color:       {C_PURPLE};
        border:      1.5px solid rgba(255, 255, 255, 0.65);
        border-radius: 8px;
        padding:     4px 14px;
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   14px;
    }}
    button.nyxus-store-btn-open:hover {{
        background:  rgba(255, 255, 255, 0.30);
        color:       #ffffff;
        text-shadow: 0 0 6px rgba(255, 255, 255, 0.65);
    }}
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode("utf-8"))
    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )


# ──────────────────────────────────────────────── helpers
def _detached(parts) -> None:
    try:
        if isinstance(parts, str):
            subprocess.Popen(parts, shell=True, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            subprocess.Popen(parts, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def _has(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _launch_app(app: Dict[str, Any]) -> None:
    """Launch a discovered app dict, preferring Gio.AppInfo."""
    aid = app.get("id", "")
    name = app.get("name", aid)
    icon = app.get("icon", "")
    push_recent(aid, name, icon)

    desktop = app.get("desktop", "")
    if desktop:
        try:
            ai = Gio.DesktopAppInfo.new_from_filename(desktop)
            if ai is not None:
                ai.launch(None, None)
                return
        except Exception:
            pass

    if aid.endswith(".desktop"):
        try:
            ai = Gio.DesktopAppInfo.new(aid)
            if ai is not None:
                ai.launch(None, None)
                return
        except Exception:
            pass

    cmd = app.get("exec", "")
    if cmd:
        # strip Field codes (%U %F %u %f %i %c %k)
        clean = " ".join(p for p in cmd.split() if not (p.startswith("%") and len(p) == 2))
        _detached(clean)


def _launch_command(cmd: str) -> None:
    if cmd:
        _detached(cmd)


_ICON_SEARCH_DIRS = (
    "/usr/share/pixmaps",
    "/usr/share/icons/hicolor/scalable/apps",
    "/usr/share/icons/hicolor/256x256/apps",
    "/usr/share/icons/hicolor/128x128/apps",
    "/usr/share/icons/hicolor/64x64/apps",
    "/usr/share/icons/hicolor/48x48/apps",
    "/usr/share/icons/hicolor/32x32/apps",
)
_ICON_EXTS = (".png", ".svg", ".xpm", ".jpg", ".webp")


def _scan_pixmap_dirs(base_name: str) -> str:
    """Last-resort: scan common system icon dirs for `base_name.{png,svg,…}`."""
    if not base_name or "/" in base_name:
        return ""
    for d in _ICON_SEARCH_DIRS:
        for ext in _ICON_EXTS:
            p = Path(d) / f"{base_name}{ext}"
            if p.exists():
                return str(p)
    return ""


def _icon_widget(name: str, fallback_glyph: str = "\uf0c8",
                 fallback_color: str = C_PURPLE,
                 px: int = 36) -> Gtk.Widget:
    """
    Build a square icon widget that actually finds app icons on most desktops.

    `name` may be:
      • a single themed icon name      ("firefox")
      • a `;`-joined chain of fallbacks ("firefox;applications-internet")
      • an absolute path to an image    ("/usr/share/pixmaps/discord.png")

    Resolution order, per name in the chain:
      1. literal absolute path
      2. current Gtk icon theme (`has_icon`)
      3. scan `/usr/share/pixmaps` and `hicolor/*/apps` for `name.{png,svg,…}`

    Falls back to the Nerd Font glyph only when nothing in the chain resolves.
    """
    if name:
        names = [n for n in name.split(";") if n]
        try:
            display = Gdk.Display.get_default()
            theme = Gtk.IconTheme.get_for_display(display) if display else None
        except Exception:
            theme = None

        for cand in names:
            try:
                if cand.startswith("/") and Path(cand).exists():
                    img = Gtk.Picture.new_for_filename(cand)
                    img.set_size_request(px, px)
                    img.set_can_shrink(True)
                    img.set_content_fit(Gtk.ContentFit.CONTAIN)
                    return img
                if theme is not None and theme.has_icon(cand):
                    img = Gtk.Image.new_from_icon_name(cand)
                    img.set_pixel_size(px)
                    return img
                pixmap = _scan_pixmap_dirs(cand)
                if pixmap:
                    img = Gtk.Picture.new_for_filename(pixmap)
                    img.set_size_request(px, px)
                    img.set_can_shrink(True)
                    img.set_content_fit(Gtk.ContentFit.CONTAIN)
                    return img
            except Exception:
                continue

    lbl = Gtk.Label(label=fallback_glyph)
    lbl.add_css_class("nyxus-tile-glyph")
    lbl.set_attributes(_pango_glyph(px, fallback_color))
    return lbl


def _pango_glyph(px: int, color_hex: str) -> Pango.AttrList:
    al = Pango.AttrList()
    al.insert(Pango.attr_family_new("JetBrains Mono Nerd Font"))
    al.insert(Pango.attr_size_new_absolute(int(px * 0.85) * Pango.SCALE))
    rgba = Gdk.RGBA(); rgba.parse(color_hex)
    al.insert(Pango.attr_foreground_new(
        int(rgba.red * 65535), int(rgba.green * 65535), int(rgba.blue * 65535)))
    return al


# ──────────────────────────────────────────────── confirmation dialog
def _confirm(parent: Gtk.Window, title: str, body: str,
             on_yes: Callable[[], None]) -> None:
    dlg = Gtk.AlertDialog()
    dlg.set_modal(True)
    dlg.set_message(title)
    dlg.set_detail(body)
    dlg.set_buttons(["Cancel", "Confirm"])
    dlg.set_default_button(0)
    dlg.set_cancel_button(0)

    def _cb(d, res):
        try:
            idx = d.choose_finish(res)
            if idx == 1:
                on_yes()
        except Exception:
            pass
    dlg.choose(parent, None, _cb)


# ──────────────────────────────────────────────── start window
class StartWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application):
        super().__init__(application=app)
        self.set_title("NYXUS Start")
        self.set_default_size(PANEL_W, PANEL_H)
        self.set_resizable(False)
        self.set_decorated(False)
        self.add_css_class("nyxus-start")

        self._cfg     = load_config()
        self._pins    = load_pins()
        self._all_apps: List[Dict] = []
        self._cat     = "All"
        _install_css(self._cfg)

        # ── Layer-shell anchor: bottom-LEFT (above the Start button)
        if _HAS_LAYER_SHELL:
            try:
                LayerShell.init_for_window(self)
                LayerShell.set_layer(self, LayerShell.Layer.OVERLAY)
                LayerShell.set_keyboard_mode(self, LayerShell.KeyboardMode.ON_DEMAND)
                LayerShell.set_anchor(self, LayerShell.Edge.BOTTOM, True)
                LayerShell.set_anchor(self, LayerShell.Edge.LEFT,   True)
                LayerShell.set_margin(self, LayerShell.Edge.BOTTOM, 60)
                LayerShell.set_margin(self, LayerShell.Edge.LEFT,   10)
            except Exception:
                pass

        # ── Revealer (slide up animation)
        self._revealer = Gtk.Revealer()
        self._revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_UP)
        self._revealer.set_transition_duration(
            0 if self._cfg.get("reduce_animations") else 220
        )
        self.set_child(self._revealer)

        # outer is now HORIZONTAL: left column (header / pinned / recent / power)
        # + a fixed-width notepad sidebar on the right.
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        outer.set_size_request(PANEL_W, PANEL_H)
        self._revealer.set_child(outer)

        left_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        left_col.set_size_request(LEFT_W, PANEL_H)
        outer.append(left_col)

        left_col.append(self._build_header())

        # ── PAGE SWITCHER (Apps | Store) ───────────────────────────
        # The Start menu now has two pages, switched via the buttons in
        # the header bar below. Apps = pinned/recent/all installed apps.
        # Store = NYXUS App Store catalog (one-click installs).
        switcher = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                           margin_top=2, margin_bottom=6,
                           margin_start=14, margin_end=14)
        switcher.add_css_class("nyxus-pageswitcher")
        self._page_apps_btn  = Gtk.ToggleButton(label="\uf0c9  Apps")
        self._page_apps_btn.add_css_class("nyxus-page-btn")
        self._page_store_btn = Gtk.ToggleButton(label="\uf07a  Store")
        self._page_store_btn.add_css_class("nyxus-page-btn")
        switcher.append(self._page_apps_btn); switcher.append(self._page_store_btn)
        left_col.append(switcher)

        # ── Stack: Apps page + Store page ──────────────────────────
        self._page_stack = Gtk.Stack()
        self._page_stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self._page_stack.set_transition_duration(
            0 if self._cfg.get("reduce_animations") else 180)
        self._page_stack.set_vexpand(True); self._page_stack.set_hexpand(True)
        left_col.append(self._page_stack)

        # ── APPS PAGE: scrollable middle (pinned + recent + all) ───
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True); scroller.set_hexpand(True)
        self._page_stack.add_named(scroller, "apps")

        middle = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scroller.set_child(middle)

        self._search_results_section = self._build_section("Search Results")
        self._search_results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._search_results_section.append(self._search_results_box)
        self._search_results_section.set_visible(False)
        middle.append(self._search_results_section)

        self._pinned_section = self._build_section("Pinned",
            right_widget=self._mk_ghost_btn("\uf044  Edit", lambda *_: self._edit_pins()))
        self._pinned_grid = Gtk.FlowBox()
        # Tiles are smaller now → fit one more per row.
        self._pinned_grid.set_max_children_per_line(5)
        self._pinned_grid.set_min_children_per_line(5)
        self._pinned_grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self._pinned_grid.set_homogeneous(True)
        self._pinned_section.append(self._pinned_grid)
        middle.append(self._pinned_section)

        self._recent_section = self._build_section("Recently Used",
            right_widget=self._mk_ghost_btn("\uf2ed  Clear",
                                            lambda *_: self._clear_recent()))
        self._recent_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._recent_section.append(self._recent_box)
        middle.append(self._recent_section)

        self._all_section = self._build_section("All Apps")
        self._cats_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._cats_row.set_margin_bottom(4)
        self._all_section.append(self._cats_row)
        self._all_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._all_section.append(self._all_box)
        middle.append(self._all_section)

        # ── STORE PAGE (NYXUS App Store catalog inline) ────────────
        self._page_stack.add_named(self._build_store_page(), "store")

        # Wire switcher → stack
        self._page_apps_btn.connect("toggled",
            lambda b: self._switch_page(b, "apps", self._page_store_btn))
        self._page_store_btn.connect("toggled",
            lambda b: self._switch_page(b, "store", self._page_apps_btn))
        self._page_stack.set_visible_child_name("apps")
        self._page_apps_btn.set_active(True)

        # ── status row
        self._status_section = self._build_section("GowskiNet")
        self._status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                                    spacing=10, homogeneous=True)
        self._status_section.append(self._status_box)
        left_col.append(self._status_section)

        # ── power footer
        left_col.append(self._build_power_row())

        # ── notepad sidebar (right side)
        outer.append(self._build_notepad_sidebar())

        # close on Escape ONLY — flyout stays open while the user works in it.
        # The Waybar button toggles it (PID file → SIGTERM); clicking another
        # window will give that window focus but will NOT close us. The user
        # explicitly asked: "Only closes when clicking completely outside" /
        # "Do not close on focus-out if mouse is inside panel". The cleanest
        # way to honor that is to drop the focus-out auto-dismiss entirely
        # and let the user dismiss via Esc or clicking the button again.
        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._on_key)
        self.add_controller(kc)

        # build content
        self._refresh_pinned()
        self._refresh_recent()
        self._build_categories()

        # async-ish: fetch app list right away (it's quick) & status
        GLib.idle_add(self._load_all_apps)
        self._tick_clock()
        GLib.timeout_add_seconds(1, self._tick_clock)
        GLib.timeout_add_seconds(8, self._refresh_status_async)
        GLib.idle_add(self._refresh_status_async)

    # ─────────────────────────────── header
    def _build_header(self) -> Gtk.Widget:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.add_css_class("nyxus-header")

        # profile area: avatar + name + subtitle, click → editor
        # (Replaces the old owl mascot — user wanted a real profile here.)
        self._profile_btn = Gtk.Button()
        self._profile_btn.add_css_class("nyxus-profile-btn")
        self._profile_btn.set_tooltip_text("Edit profile")
        self._profile_btn.set_child(self._build_profile_widget())
        self._profile_btn.connect("clicked",
                                  lambda *_: self._open_profile_editor())
        bar.append(self._profile_btn)

        # search — also doubles as a Rofi-style universal launcher.
        # Pressing Enter on a query that doesn't match an app will run it
        # as a shell command (so this entry replaces the old Rofi launcher).
        # Prefix `:` to force-run as command (e.g. `:journalctl -xe`).
        self._search = Gtk.Entry()
        self._search.add_css_class("nyxus-search")
        self._search.set_placeholder_text("Search apps · type a command · :shell")
        self._search.set_hexpand(True)
        self._search.set_margin_start(8); self._search.set_margin_end(8)
        self._search.connect("changed", self._on_search_changed)
        self._search.connect("activate", self._on_search_activate)
        bar.append(self._search)

        # date / time
        self._time_lbl = Gtk.Label(label="")
        self._time_lbl.add_css_class("nyxus-time")
        bar.append(self._time_lbl)

        if self._cfg.get("search_focus_on_open", True):
            GLib.idle_add(self._search.grab_focus)
        return bar

    def _tick_clock(self) -> bool:
        now = datetime.now()
        self._time_lbl.set_text(now.strftime("%a · %H:%M"))
        return True

    # ─────────────────────────────── section helper
    def _build_section(self, title: str,
                       right_widget: Optional[Gtk.Widget] = None) -> Gtk.Box:
        sec = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sec.add_css_class("nyxus-section")

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        ttl = Gtk.Label(label=title); ttl.set_xalign(0); ttl.set_hexpand(True)
        ttl.add_css_class("nyxus-section-title")
        head.append(ttl)
        if right_widget is not None:
            head.append(right_widget)
        sec.append(head)
        return sec

    def _mk_ghost_btn(self, text: str, cb: Callable) -> Gtk.Button:
        b = Gtk.Button(label=text)
        b.add_css_class("nyxus-ghost")
        b.connect("clicked", cb)
        return b

    # ─────────────────────────────── page-stack switcher
    def _switch_page(self, sender: Gtk.ToggleButton, name: str,
                     other: Gtk.ToggleButton) -> None:
        """Wire two toggle buttons into a radio-style page switcher.
        Re-entry guard prevents the recursive-toggle bug that bites every
        manual radio implementation in Gtk."""
        if getattr(self, "_in_switch_page", False):
            return
        self._in_switch_page = True
        try:
            if not sender.get_active():
                # Don't allow turning the active page button off.
                sender.set_active(True); return
            if other.get_active():
                other.set_active(False)
            self._page_stack.set_visible_child_name(name)
        finally:
            self._in_switch_page = False

    # ─────────────────────────────── store page (App Store catalog)
    def _build_store_page(self) -> Gtk.Widget:
        """Inline NYXUS App Store — same catalog as the standalone window,
        rendered as a scrollable list of cards inside the Start menu."""
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True); scroller.set_hexpand(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0,
                        margin_top=4, margin_bottom=10,
                        margin_start=14, margin_end=14)
        scroller.set_child(outer)

        # Banner
        banner = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10,
                         margin_bottom=10)
        banner.add_css_class("nyxus-store-banner")
        glyph = Gtk.Label(label="\uf07a"); glyph.add_css_class("nyxus-store-glyph")
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        col.set_hexpand(True)
        title = Gtk.Label(label="NYXUS App Store", xalign=0)
        title.add_css_class("nyxus-store-title")
        sub = Gtk.Label(
            label="Hand-drawn apps for your desktop", xalign=0)
        sub.add_css_class("nyxus-store-sub")
        col.append(title); col.append(sub)
        banner.append(glyph); banner.append(col)
        outer.append(banner)

        # Catalog — kept inline so this page works whether or not nyxus-store
        # is even installed yet. Each entry mirrors the standalone catalog.
        catalog = [
            ("nyxus-start",         "NYXUS Start",         "\uf0c9",
             "Hand-drawn flyout — search · pinned apps · scratchpad",
             "nyxus_start_install.sh"),
            ("nyxus-panel",         "NYXUS Panel",         "\uf0a1",
             "Right-side info flyout — weather · system · news",
             "nyxus_panel_install.sh"),
            ("nyxus-notifications", "NYXUS Notifications", "\uf0f3",
             "Bottom-right notifications + calendar + DND toggle",
             "nyxus_start_install.sh"),
            ("nyxus-settings",      "NYXUS Settings",      "\uf013",
             "One window for appearance, profile & every NYXUS app",
             "nyxus_panel_install.sh"),
            ("godsapp",             "GodsApp",             "\uf005",
             "The NYXUS launcher's mother-app — handwritten everything",
             "nyxus_godsapp_install.sh"),
            ("nyxus-sage",          "NYXUS Sage",          "\uf544",
             "AI assistant + system co-pilot baked into your desktop",
             "nyxus_sage_install.sh"),
            ("nyxus-shield",        "NYXUS Shield",        "\uf3ed",
             "Hardening · firewall · audit dashboards",
             "nyxus_security_install.sh"),
            ("nyxus-studio",        "NYXUS Studio",        "\uf03d",
             "Creative suite preset — audio · video · ComfyUI",
             "nyxus_studio_install.sh"),
        ]
        for binary, name, glyph, tagline, installer in catalog:
            outer.append(self._build_store_card(binary, name, glyph,
                                                tagline, installer))

        # Open the standalone Store window for the full experience
        more = Gtk.Button(label="\uf08e  Open the full App Store")
        more.add_css_class("nyxus-ghost")
        more.set_margin_top(10)
        more.connect("clicked", lambda *_: _detached("nyxus-store"))
        outer.append(more)

        return scroller

    def _build_store_card(self, binary: str, name: str, glyph: str,
                          tagline: str, installer: str) -> Gtk.Widget:
        """One catalog row: glyph + title/tagline + install/open button."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                      margin_top=4, margin_bottom=4,
                      margin_start=2, margin_end=2)
        row.add_css_class("nyxus-store-card")
        gl = Gtk.Label(label=glyph); gl.add_css_class("nyxus-store-card-glyph")
        gl.set_size_request(44, 44); gl.set_xalign(0.5); gl.set_yalign(0.5)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        col.set_hexpand(True)
        nm = Gtk.Label(label=name, xalign=0)
        nm.add_css_class("nyxus-store-card-title")
        tg = Gtk.Label(label=tagline, xalign=0)
        tg.add_css_class("nyxus-store-card-tag")
        tg.set_wrap(True); tg.set_max_width_chars(48)
        col.append(nm); col.append(tg)

        # Detect installation by checking if the binary is on PATH.
        installed = bool(shutil.which(binary))
        if installed:
            btn = Gtk.Button(label="\uf04b  Open")
            btn.add_css_class("nyxus-store-btn-open")
            btn.connect("clicked", lambda *_: _detached(binary))
        else:
            btn = Gtk.Button(label="\uf019  Install")
            btn.add_css_class("nyxus-store-btn-install")
            btn.connect("clicked", lambda *_: self._install_from_store(installer))
        btn.set_valign(Gtk.Align.CENTER)

        row.append(gl); row.append(col); row.append(btn)
        return row

    def _install_from_store(self, installer: str) -> None:
        """Pop a terminal running the curl|sudo bash installer command.
        We avoid sudo prompts in-process by spawning a terminal that handles
        password entry itself (foot/alacritty/kitty/xterm fallback chain)."""
        url = f"https://nyxus-core.replit.app/api/download/nyxus/{installer}"
        cmd = f'bash -lc "curl -fsSL {url} | sudo bash; echo; read -p \'Press Enter to close...\'"'
        for term in ("foot", "alacritty", "kitty", "wezterm", "xterm"):
            if shutil.which(term):
                _detached(f'{term} -e {cmd}')
                return
        # No terminal found — fall back to running it detached and hope for
        # a graphical sudo agent. Better than nothing.
        _detached(cmd)

    # ─────────────────────────────── pinned grid
    def _refresh_pinned(self) -> None:
        # clear
        child = self._pinned_grid.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._pinned_grid.remove(child)
            child = nxt

        for pid in self._pins:
            app = find_app_by_id(pid)
            if app is None:
                # synth a stub app for bare command
                app = {
                    "id": pid, "name": pid.replace("-", " ").title(),
                    "exec": pid, "icon": pid, "comment": "",
                    "categories": ["Other"], "raw": "", "desktop": "",
                }
            tile = self._make_pin_tile(app, pid)
            self._pinned_grid.append(tile)

    def _make_pin_tile(self, app: Dict, pid: str) -> Gtk.Widget:
        btn = Gtk.Button()
        btn.add_css_class("nyxus-tile")

        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        col.set_halign(Gtk.Align.CENTER); col.set_valign(Gtk.Align.CENTER)
        col.append(_icon_widget(app.get("icon", ""), "\uf135", C_PURPLE, 28))
        name = Gtk.Label(label=app["name"])
        name.add_css_class("nyxus-tile-name")
        name.set_max_width_chars(8); name.set_ellipsize(Pango.EllipsizeMode.END)
        col.append(name)
        btn.set_child(col)
        btn.set_tooltip_text(app["name"])

        btn.connect("clicked", lambda *_: (_launch_app(app), self._dismiss()))

        # right-click menu
        gesture = Gtk.GestureClick.new()
        gesture.set_button(3)
        gesture.connect("pressed",
                        lambda g, n, x, y: self._show_pin_menu(btn, app, pid, x, y))
        btn.add_controller(gesture)
        return btn

    def _show_pin_menu(self, anchor: Gtk.Widget, app: Dict, pid: str,
                       x: float, y: float) -> None:
        menu = Gio.Menu()
        menu.append("Launch",            f"start.launch::{pid}")
        menu.append("Unpin from Start",  f"start.unpin::{pid}")
        menu.append("Open File Location", f"start.openloc::{pid}")
        pop = Gtk.PopoverMenu.new_from_model(menu)
        pop.set_parent(anchor)
        pop.set_pointing_to(Gdk.Rectangle(x=int(x), y=int(y), width=1, height=1))
        pop.popup()
        # actions are wired once in _wire_actions

    def _edit_pins(self) -> None:
        """Toggle a simple 'pin all installed apps' flow — opens picker dialog."""
        win = Gtk.Window(title="Edit Pinned Apps")
        win.set_default_size(360, 460); win.set_transient_for(self); win.set_modal(True)
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        win.set_child(scroller)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_margin_start(8); box.set_margin_end(8)
        scroller.set_child(box)

        for app in self._all_apps:
            aid = app["id"]
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.append(_icon_widget(app.get("icon", ""), "\uf135", C_PURPLE, 22))
            lbl = Gtk.Label(label=app["name"]); lbl.set_xalign(0); lbl.set_hexpand(True)
            row.append(lbl)
            sw = Gtk.Switch(); sw.set_active(aid in self._pins or aid.replace(".desktop","") in self._pins)
            def _toggle(s, _ps, app_id=aid):
                if s.get_active():
                    if app_id not in self._pins:
                        self._pins.append(app_id)
                else:
                    self._pins = [p for p in self._pins
                                  if p != app_id and p != app_id.replace(".desktop", "")]
                save_pins(self._pins)
                self._refresh_pinned()
            sw.connect("notify::active", _toggle)
            row.append(sw)
            box.append(row)
        win.present()

    # ─────────────────────────────── recent
    def _refresh_recent(self) -> None:
        child = self._recent_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._recent_box.remove(child)
            child = nxt

        items = list_recent(10)
        if not items:
            empty = Gtk.Label(label="(no recent activity yet)")
            empty.add_css_class("nyxus-row-sub")
            empty.set_xalign(0); empty.set_margin_start(6); empty.set_margin_top(2)
            self._recent_box.append(empty)
            return

        for it in items:
            self._recent_box.append(self._make_recent_row(it))

    def _make_recent_row(self, item: Dict) -> Gtk.Widget:
        btn = Gtk.Button(); btn.add_css_class("nyxus-row")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.append(_icon_widget(item.get("icon", ""), "\uf15b", C_CYAN, 22))
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        col.set_hexpand(True)
        n = Gtk.Label(label=item["name"]); n.set_xalign(0)
        n.add_css_class("nyxus-row-title")
        n.set_ellipsize(Pango.EllipsizeMode.END)
        col.append(n)
        s = Gtk.Label(label=humanize_ts(item.get("ts", 0))); s.set_xalign(0)
        s.add_css_class("nyxus-row-sub")
        col.append(s)
        row.append(col)
        btn.set_child(row)

        def _click(*_):
            if item["kind"] == "app":
                app = find_app_by_id(item["id"])
                if app is not None:
                    _launch_app(app)
            else:
                _detached(["xdg-open", item["uri"] or item["id"]])
                push_recent(item["id"], item["name"], item.get("icon", ""))
            self._dismiss()

        btn.connect("clicked", _click)

        gesture = Gtk.GestureClick.new()
        gesture.set_button(3)
        def _menu(g, n, x, y):
            menu = Gio.Menu()
            menu.append("Remove from Recent",
                        f"start.recentrm::{item['kind']}::{item['id']}")
            if item["kind"] == "app":
                menu.append("Pin to Start",
                            f"start.pin::{item['id']}")
            pop = Gtk.PopoverMenu.new_from_model(menu)
            pop.set_parent(btn)
            pop.set_pointing_to(Gdk.Rectangle(x=int(x), y=int(y), width=1, height=1))
            pop.popup()
        gesture.connect("pressed", _menu)
        btn.add_controller(gesture)
        return btn

    def _clear_recent(self) -> None:
        clear_recent()
        self._refresh_recent()

    # ─────────────────────────────── all apps
    def _load_all_apps(self) -> bool:
        self._all_apps = list_installed_apps(
            max_count=int(self._cfg.get("max_all_apps", 500))
        )
        self._refresh_all_apps()
        return False  # don't repeat

    def _build_categories(self) -> None:
        # clear
        child = self._cats_row.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._cats_row.remove(child)
            child = nxt
        for cat in ["All"] + NYXUS_CATEGORIES:
            chip = Gtk.Button(label=cat); chip.add_css_class("nyxus-chip")
            if cat == self._cat:
                chip.add_css_class("active")
            chip.connect("clicked", lambda b, c=cat: self._set_category(c))
            self._cats_row.append(chip)

    def _set_category(self, cat: str) -> None:
        self._cat = cat
        self._build_categories()
        self._refresh_all_apps()

    def _refresh_all_apps(self) -> None:
        child = self._all_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._all_box.remove(child)
            child = nxt

        if self._cat == "All":
            apps = self._all_apps
        else:
            apps = [a for a in self._all_apps if self._cat in a.get("categories", [])]

        if not apps:
            empty = Gtk.Label(label="(no apps in this category)")
            empty.add_css_class("nyxus-row-sub"); empty.set_xalign(0); empty.set_margin_start(6)
            self._all_box.append(empty); return

        for app in apps:
            self._all_box.append(self._make_app_row(app))

    def _make_app_row(self, app: Dict) -> Gtk.Widget:
        btn = Gtk.Button(); btn.add_css_class("nyxus-row")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.append(_icon_widget(app.get("icon", ""), "\uf135", C_PURPLE, 22))
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        col.set_hexpand(True)
        n = Gtk.Label(label=app["name"]); n.set_xalign(0)
        n.add_css_class("nyxus-row-title")
        n.set_ellipsize(Pango.EllipsizeMode.END)
        col.append(n)
        if app.get("comment"):
            s = Gtk.Label(label=app["comment"]); s.set_xalign(0)
            s.add_css_class("nyxus-row-sub")
            s.set_ellipsize(Pango.EllipsizeMode.END)
            s.set_max_width_chars(46)
            col.append(s)
        row.append(col)
        btn.set_child(row)
        btn.connect("clicked", lambda *_: (_launch_app(app), self._dismiss()))

        gesture = Gtk.GestureClick.new()
        gesture.set_button(3)
        def _menu(g, n, x, y):
            menu = Gio.Menu()
            menu.append("Launch",             f"start.launch::{app['id']}")
            menu.append("Pin to Start",       f"start.pin::{app['id']}")
            menu.append("Open File Location", f"start.openloc::{app['id']}")
            pop = Gtk.PopoverMenu.new_from_model(menu)
            pop.set_parent(btn)
            pop.set_pointing_to(Gdk.Rectangle(x=int(x), y=int(y), width=1, height=1))
            pop.popup()
        gesture.connect("pressed", _menu)
        btn.add_controller(gesture)
        return btn

    # ─────────────────────────────── search
    def _on_search_changed(self, entry: Gtk.Entry) -> None:
        q = entry.get_text().strip()
        # clear results
        c = self._search_results_box.get_first_child()
        while c is not None:
            nxt = c.get_next_sibling()
            self._search_results_box.remove(c)
            c = nxt

        if not q:
            self._search_results_section.set_visible(False)
            return
        results = search_apps(q, self._all_apps, limit=20)
        for app in results:
            self._search_results_box.append(self._make_app_row(app))
        if not results:
            empty = Gtk.Label(label="(no matches)")
            empty.add_css_class("nyxus-row-sub")
            empty.set_xalign(0); empty.set_margin_start(6)
            self._search_results_box.append(empty)
        self._search_results_section.set_visible(True)

    def _on_search_activate(self, entry: Gtk.Entry) -> None:
        q = entry.get_text().strip()
        if not q:
            return
        # `:cmd args…`  →  always run as shell command (Rofi-style escape)
        if q.startswith(":"):
            cmd = q[1:].strip()
            if cmd:
                _launch_command(cmd)
                self._dismiss()
            return
        # otherwise: try app match first, then fall back to running as a command.
        # This lets the search bar fully replace the old Rofi launcher — typing
        # `firefox` opens Firefox, typing `htop` runs it, typing `code .` works.
        results = search_apps(q, self._all_apps, limit=1)
        if results:
            _launch_app(results[0])
            self._dismiss()
            return
        _launch_command(q)
        self._dismiss()

    # ─────────────────────────────── status row
    def _refresh_status_async(self) -> bool:
        # synchronous (status probes are fast); kept on a timer for periodic refresh
        try:
            data = gather_status()
        except Exception:
            return True

        c = self._status_box.get_first_child()
        while c is not None:
            nxt = c.get_next_sibling()
            self._status_box.remove(c)
            c = nxt

        for key, info in data.items():
            self._status_box.append(self._make_status_pill(key, info))
        return True

    def _make_status_pill(self, key: str, info: Dict) -> Gtk.Widget:
        btn = Gtk.Button(); btn.add_css_class("nyxus-row")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        glyph = Gtk.Label(label=info["glyph"])
        glyph.set_attributes(_pango_glyph(20, C_GREEN if info["ok"] else C_RED))
        row.append(glyph)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        n = Gtk.Label(label=info["label"]); n.set_xalign(0)
        n.add_css_class("nyxus-row-title")
        col.append(n)
        v = Gtk.Label(label=info["value"]); v.set_xalign(0)
        v.add_css_class("nyxus-status-ok" if info["ok"] else "nyxus-status-bad")
        v.add_css_class("nyxus-status")
        col.append(v)
        row.append(col); btn.set_child(row)

        target = info.get("target", "")
        def _open(*_):
            app = find_app_by_id(target)
            if app is not None:
                _launch_app(app)
            else:
                _launch_command(target)
            self._dismiss()
        btn.connect("clicked", _open)
        return btn

    # ─────────────────────────────── profile (avatar + name)
    def _build_profile_widget(self) -> Gtk.Widget:
        """
        Compact profile chip shown where the owl used to be:
            [ avatar ]  Joey
                        operator
        Avatar = circular image (cfg["user_avatar"]) or initials fallback.
        """
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        row.set_valign(Gtk.Align.CENTER)

        avatar_path = self._cfg.get("user_avatar", "")
        name = self._cfg.get("user_name", "Joey") or "?"
        subtitle = self._cfg.get("user_subtitle", "operator") or ""

        size = 38
        avatar: Gtk.Widget
        if avatar_path and Path(avatar_path).exists():
            pic = Gtk.Picture.new_for_filename(avatar_path)
            pic.set_size_request(size, size)
            pic.set_can_shrink(True)
            pic.set_content_fit(Gtk.ContentFit.COVER)
            # round mask via overflow:hidden on the frame
            frame = Gtk.Frame()
            frame.add_css_class("nyxus-avatar-frame")
            frame.set_size_request(size, size)
            frame.set_child(pic)
            avatar = frame
        else:
            initials = "".join(p[:1] for p in name.split()[:2]).upper() or "?"
            lbl = Gtk.Label(label=initials)
            lbl.add_css_class("nyxus-avatar-initials")
            frame = Gtk.Frame()
            frame.add_css_class("nyxus-avatar-frame")
            frame.set_size_request(size, size)
            frame.set_halign(Gtk.Align.CENTER)
            frame.set_valign(Gtk.Align.CENTER)
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
            inner.set_halign(Gtk.Align.CENTER); inner.set_valign(Gtk.Align.CENTER)
            inner.append(lbl)
            frame.set_child(inner)
            avatar = frame
        row.append(avatar)

        text_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        text_col.set_valign(Gtk.Align.CENTER)
        n = Gtk.Label(label=name)
        n.add_css_class("nyxus-profile-name")
        n.set_xalign(0)
        text_col.append(n)
        if subtitle:
            s = Gtk.Label(label=subtitle)
            s.add_css_class("nyxus-profile-sub")
            s.set_xalign(0)
            text_col.append(s)
        row.append(text_col)
        return row

    def _refresh_profile(self) -> None:
        """Rebuild the avatar/name chip after the user edits their profile."""
        try:
            self._profile_btn.set_child(self._build_profile_widget())
        except Exception:
            pass

    def _open_profile_editor(self) -> None:
        """Modal dialog to set the user's name, subtitle, and avatar image."""
        dlg = Gtk.Window(title="Edit Profile")
        dlg.set_default_size(360, 220)
        dlg.set_transient_for(self)
        dlg.set_modal(True)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer.set_margin_top(14); outer.set_margin_bottom(14)
        outer.set_margin_start(14); outer.set_margin_end(14)
        dlg.set_child(outer)

        # name
        outer.append(Gtk.Label(label="Display name", xalign=0))
        name_e = Gtk.Entry()
        name_e.set_text(self._cfg.get("user_name", "Joey"))
        outer.append(name_e)

        # subtitle
        outer.append(Gtk.Label(label="Subtitle (e.g. role, host)", xalign=0))
        sub_e = Gtk.Entry()
        sub_e.set_text(self._cfg.get("user_subtitle", "operator"))
        outer.append(sub_e)

        # avatar
        outer.append(Gtk.Label(label="Avatar image", xalign=0))
        av_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        av_lbl = Gtk.Label(label=self._cfg.get("user_avatar", "") or "(none)")
        av_lbl.set_xalign(0); av_lbl.set_hexpand(True)
        av_lbl.set_ellipsize(Pango.EllipsizeMode.MIDDLE)
        av_row.append(av_lbl)

        chosen: Dict[str, str] = {"path": self._cfg.get("user_avatar", "")}

        def _pick(*_):
            fc = Gtk.FileDialog()
            fc.set_title("Choose avatar image")
            ff = Gtk.FileFilter(); ff.set_name("Images")
            for pat in ("*.png", "*.jpg", "*.jpeg", "*.webp", "*.gif", "*.bmp", "*.svg"):
                ff.add_pattern(pat)
            ff_list = Gio.ListStore.new(Gtk.FileFilter); ff_list.append(ff)
            fc.set_filters(ff_list)
            def _done(d, res):
                try:
                    f = d.open_finish(res)
                    if f is not None:
                        p = f.get_path() or ""
                        if p:
                            chosen["path"] = p
                            av_lbl.set_text(p)
                except Exception:
                    pass
            fc.open(dlg, None, _done)

        pick_btn = Gtk.Button(label="\uf07c  Choose…")
        pick_btn.add_css_class("nyxus-power")
        pick_btn.connect("clicked", _pick)
        av_row.append(pick_btn)

        clear_btn = Gtk.Button(label="\uf2ed  Clear")
        clear_btn.add_css_class("nyxus-power")
        def _clear(*_):
            chosen["path"] = ""
            av_lbl.set_text("(none)")
        clear_btn.connect("clicked", _clear)
        av_row.append(clear_btn)
        outer.append(av_row)

        # buttons
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        btn_row.set_halign(Gtk.Align.END)
        cancel = Gtk.Button(label="Cancel"); cancel.add_css_class("nyxus-power")
        cancel.connect("clicked", lambda *_: dlg.close())
        save = Gtk.Button(label="Save"); save.add_css_class("nyxus-power")
        def _save(*_):
            self._cfg["user_name"] = name_e.get_text().strip() or "Joey"
            self._cfg["user_subtitle"] = sub_e.get_text().strip()
            new_path = chosen["path"]
            if new_path and new_path != self._cfg.get("user_avatar", ""):
                stored = store_avatar(new_path)
                if stored:
                    self._cfg["user_avatar"] = stored
            elif not new_path:
                self._cfg["user_avatar"] = ""
            save_config(self._cfg)
            self._refresh_profile()
            dlg.close()
        save.connect("clicked", _save)
        btn_row.append(cancel); btn_row.append(save)
        outer.append(btn_row)

        dlg.present()

    # ─────────────────────────────── notepad sidebar
    def _build_notepad_sidebar(self) -> Gtk.Widget:
        """
        Right-side built-in scratchpad. Persists to
        ~/.config/nyxus-start/scratchpad.txt with a 600 ms debounce so
        autosave never blocks typing.
        """
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        side.add_css_class("nyxus-notepad-sidebar")
        side.set_size_request(NOTEPAD_W, PANEL_H)

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        title = Gtk.Label(label="\uf249  Scratchpad")
        title.add_css_class("nyxus-notepad-title")
        title.set_xalign(0); title.set_hexpand(True)
        head.append(title)

        self._notepad_saved = Gtk.Label(label="")
        self._notepad_saved.add_css_class("nyxus-notepad-saved")
        head.append(self._notepad_saved)
        side.append(head)

        # text area
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True); scroll.set_hexpand(True)
        scroll.add_css_class("nyxus-notepad-frame")

        self._notepad_view = Gtk.TextView()
        self._notepad_view.add_css_class("nyxus-notepad")
        self._notepad_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._notepad_view.set_top_margin(6); self._notepad_view.set_bottom_margin(6)
        self._notepad_view.set_left_margin(6); self._notepad_view.set_right_margin(6)

        # ── Editability + focus, EXPLICITLY.
        # GTK4LayerShell ON_DEMAND keyboard mode delivers keystrokes only to the
        # focused widget. TextView's default focus-on-click sometimes loses the
        # race against the layer-surface keyboard grab on Hyprland, which is
        # why typing into the scratchpad silently no-op'd before. Forcing the
        # editable + focusable flags ON and adding an explicit click-to-focus
        # gesture closes the gap.
        self._notepad_view.set_editable(True)
        self._notepad_view.set_cursor_visible(True)
        self._notepad_view.set_can_focus(True)
        self._notepad_view.set_focusable(True)
        self._notepad_view.set_focus_on_click(True)
        self._notepad_view.set_accepts_tab(True)

        _np_click = Gtk.GestureClick()
        _np_click.set_button(0)  # any mouse button
        def _np_focus(_g, _n, _x, _y):
            try:
                self._notepad_view.grab_focus()
            except Exception:
                pass
        _np_click.connect("pressed", _np_focus)
        self._notepad_view.add_controller(_np_click)

        buf = self._notepad_view.get_buffer()
        buf.set_text(load_scratch())
        self._notepad_save_handle: Optional[int] = None

        def _flush_save() -> bool:
            self._notepad_save_handle = None
            start, end = buf.get_bounds()
            text = buf.get_text(start, end, True)
            save_scratch(text)
            try:
                self._notepad_saved.set_text("\uf00c saved")
                GLib.timeout_add_seconds(2,
                    lambda: (self._notepad_saved.set_text(""), False)[1])
            except Exception:
                pass
            return False

        def _on_changed(_b):
            if self._notepad_save_handle is not None:
                try:
                    GLib.source_remove(self._notepad_save_handle)
                except Exception:
                    pass
            self._notepad_save_handle = GLib.timeout_add(600, _flush_save)

        buf.connect("changed", _on_changed)
        scroll.set_child(self._notepad_view)
        side.append(scroll)

        # footer: clear + open-in-editor
        foot = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        foot.set_halign(Gtk.Align.END)

        open_btn = Gtk.Button(label="\uf304  Open in editor")
        open_btn.add_css_class("nyxus-ghost")
        def _open_editor(*_):
            _flush_save()
            from settings import SCRATCH_FILE
            _detached(["xdg-open", str(SCRATCH_FILE)])
        open_btn.connect("clicked", _open_editor)
        foot.append(open_btn)

        clear_btn = Gtk.Button(label="\uf2ed  Clear")
        clear_btn.add_css_class("nyxus-ghost")
        def _clear(*_):
            buf.set_text("")
            save_scratch("")
        clear_btn.connect("clicked", _clear)
        foot.append(clear_btn)
        side.append(foot)

        return side

    # ─────────────────────────────── power row
    def _build_power_row(self) -> Gtk.Widget:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.add_css_class("nyxus-section")
        bar.set_margin_top(2); bar.set_margin_bottom(6)

        user_btn = Gtk.Button(label=f"\uf007  {self._cfg.get('user_name','Joey')}")
        user_btn.add_css_class("nyxus-power")
        user_btn.set_hexpand(True); user_btn.set_halign(Gtk.Align.START)
        user_btn.connect("clicked",
                         lambda *_: self._open_profile_editor())
        bar.append(user_btn)

        # Settings button — sits with lock/restart/etc. so the user has a
        # one-click path to NYXUS Settings from the power row.
        settings_btn = Gtk.Button()
        settings_btn.add_css_class("nyxus-power")
        settings_btn.set_tooltip_text("Settings")
        s_inner = Gtk.Label(label="\uf013")  # Font Awesome gear
        s_inner.set_attributes(_pango_glyph(20, C_CYAN))
        settings_btn.set_child(s_inner)
        settings_btn.connect(
            "clicked",
            lambda *_: (_launch_command("nyxus-settings"), self._dismiss()))
        bar.append(settings_btn)

        for key, label, glyph, color, requires_confirm in POWER_ACTIONS:
            b = Gtk.Button()
            b.add_css_class("nyxus-power")
            if requires_confirm:
                b.add_css_class("nyxus-power-danger")
            b.set_tooltip_text(label)
            inner = Gtk.Label(label=glyph)
            inner.set_attributes(_pango_glyph(20, color))
            b.set_child(inner)
            def _click(_btn, k=key, lbl=label, conf=requires_confirm):
                if conf:
                    _confirm(self, f"Confirm {lbl}",
                             f"Are you sure you want to {lbl.lower()} the system?",
                             lambda: (perform_power(k), self._dismiss()))
                else:
                    perform_power(k); self._dismiss()
            b.connect("clicked", _click)
            bar.append(b)
        return bar

    # ─────────────────────────────── close behavior
    def _on_key(self, ctrl, keyval, keycode, state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self._dismiss(); return True
        return False

    def _dismiss(self) -> None:
        try:
            if not self._cfg.get("reduce_animations", False):
                self._revealer.set_reveal_child(False)
                GLib.timeout_add(220, self._final_close)
                return
        except Exception:
            pass
        self._final_close()

    def _final_close(self) -> bool:
        _clear_pid()
        self.close()
        try:
            self.get_application().quit()
        except Exception:
            pass
        return False


# ──────────────────────────────────────────────── application
class NyxusStartApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self._win: Optional[StartWindow] = None
        self._actions_wired = False

    def do_activate(self) -> None:
        if self._win is None:
            self._win = StartWindow(self)
            self._wire_actions()
        self._win.present()
        # start with revealer collapsed → animate open
        try:
            self._win._revealer.set_reveal_child(False)
            GLib.idle_add(lambda: self._win._revealer.set_reveal_child(True))
        except Exception:
            pass

    def _wire_actions(self) -> None:
        if self._actions_wired or self._win is None: return
        self._actions_wired = True

        def add(name: str, cb: Callable[[str], None]):
            act = Gio.SimpleAction.new(name, GLib.VariantType.new("s"))
            act.connect("activate", lambda a, p: cb(p.get_string()))
            self.add_action(act)

        def launch(pid: str):
            app = find_app_by_id(pid)
            if app is not None:
                _launch_app(app)
            else:
                _launch_command(pid)
            self._win._dismiss()

        def pin(pid: str):
            if pid not in self._win._pins:
                self._win._pins.insert(0, pid); save_pins(self._win._pins)
                self._win._refresh_pinned()

        def unpin(pid: str):
            self._win._pins = [p for p in self._win._pins if p != pid]
            save_pins(self._win._pins); self._win._refresh_pinned()

        def openloc(pid: str):
            app = find_app_by_id(pid)
            target = app.get("desktop", "") if app else ""
            if not target:
                target = os.path.expanduser("~/.local/share/applications")
            target_dir = target if os.path.isdir(target) else os.path.dirname(target)
            if target_dir:
                _detached(["xdg-open", target_dir])
            self._win._dismiss()

        def recentrm(payload: str):
            try:
                kind, item_id = payload.split("::", 1)
            except ValueError:
                return
            remove_from_recent(kind, item_id)
            self._win._refresh_recent()

        add("launch",   launch)
        add("pin",      pin)
        add("unpin",    unpin)
        add("openloc",  openloc)
        add("recentrm", recentrm)


# ──────────────────────────────────────────────── entry
def main() -> int:
    # PID toggle (only if --no-toggle absent)
    if "--no-toggle" not in sys.argv:
        existing = _running_pid()
        if existing is not None:
            try:
                os.kill(existing, signal.SIGTERM)
            except OSError:
                pass
            return 0
    _write_pid()

    def _cleanup(*_):
        _clear_pid()
        sys.exit(0)
    for s in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
        try: signal.signal(s, _cleanup)
        except Exception: pass

    app = NyxusStartApp()
    rc = app.run(None)
    _clear_pid()
    return rc



# ─────────────────────────── NYXUS CHROME (DISABLED) ───────────────────────
# nyxus-start uses gtk4-layer-shell to anchor itself, which is INCOMPATIBLE
# with the Gtk.Overlay-based GraffitiBackground that nyxus_chrome injects.
# When chrome is enabled here the Overlay swallows or hides the start
# window's content and the user sees only the graffiti background.
# Same exclusion applies to nyxus-panel for the same reason.
#
# nyxus-start renders its own NYXUS-styled chrome inline (graffiti
# background, Inter Display font, neon accents) — see _render_background() and
# the CSS provider lower in this file.
# ────────────────────────── /NYXUS CHROME (DISABLED) ────────────────────────

if __name__ == "__main__":
    sys.exit(main())
