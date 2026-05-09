# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
Standard NYXUS About window.

Every NYXUS app exposes the same About dialog so the brand stays
consistent across the suite.
"""
from __future__ import annotations

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
from gi.repository import Gtk

ISO_NAME = "nyx-2026.05.02-x86_64.iso"
AUTHOR = "Joseph Sierengowski"
YEAR = "2026"
LICENSE_NAME = "NYX & NYXUS Custom License v1.0"
TAGLINE = '"The Night Has Eyes."'


def show_about(parent: Gtk.Window | None,
               app_name: str = "NYXUS Phantom",
               version: str = "1.0.0") -> None:
    dlg = Gtk.Window(title=f"About {app_name}")
    dlg.set_modal(True)
    if parent is not None:
        dlg.set_transient_for(parent)
    dlg.set_default_size(440, 360)
    dlg.set_resizable(False)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                  margin_top=22, margin_bottom=18,
                  margin_start=24, margin_end=24)
    dlg.set_child(box)

    title = Gtk.Label(label=app_name)
    title.add_css_class("title-1")
    title.set_xalign(0.0)
    box.append(title)

    sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    box.append(sep)

    rows = [
        ("Name",       app_name),
        ("Version",    version),
        ("ISO",        ISO_NAME),
        ("Created by", AUTHOR),
        ("Year",       YEAR),
        ("License",    LICENSE_NAME),
    ]
    grid = Gtk.Grid(column_spacing=14, row_spacing=4)
    for i, (k, v) in enumerate(rows):
        kw = Gtk.Label(label=k); kw.set_xalign(0.0)
        kw.add_css_class("dim-label")
        vw = Gtk.Label(label=v); vw.set_xalign(0.0)
        vw.set_selectable(True)
        grid.attach(kw, 0, i, 1, 1)
        grid.attach(vw, 1, i, 1, 1)
    box.append(grid)

    spacer = Gtk.Box(vexpand=True)
    box.append(spacer)

    tag = Gtk.Label(label=TAGLINE)
    tag.set_xalign(0.0)
    tag.add_css_class("dim-label")
    box.append(tag)

    btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                      halign=Gtk.Align.END)
    box.append(btn_row)
    close = Gtk.Button(label="Close")
    close.connect("clicked", lambda *_: dlg.close())
    btn_row.append(close)

    dlg.present()
