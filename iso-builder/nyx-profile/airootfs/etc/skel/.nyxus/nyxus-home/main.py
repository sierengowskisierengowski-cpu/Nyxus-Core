#!/usr/bin/env python3
# ============================================
# NYXUS Home — main GTK4 entry
# (c) 2026 Joseph Sierengowski
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
Workspace-0 dashboard: Clock · Weather · Calendar · Notifications ·
Notepad · Password Manager.  Cards float over a Cairo-painted
graffiti word-collage matching the web mirror.
"""
import os
import sys

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

# Make sibling modules importable regardless of cwd
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

from style import install_css, PALETTE                                # noqa: E402
from graffiti import GraffitiArea                                     # noqa: E402
from tilt import TiltBox                                              # noqa: E402
from widgets import (                                                  # noqa: E402
    ClockCard, WeatherCard, CalendarCard,
    NotificationsCard, NotepadCard, PasswordManagerCard,
    SystemPulseCard,
)

# Per-card tilt angles (degrees) — exact values from web HomeDashboard.tsx
CARD_TILTS = {
    "Clock":         -1.2,
    "Weather":        0.8,
    "Notifications":  1.0,
    "Calendar":      -0.5,
    "Notepad":       -0.8,
    "Pulse":          0.6,
    "Passwords":      0.5,
}

APP_ID = "io.nyxus.home"


def _header_strip():
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    box.set_margin_start(8)
    box.set_margin_end(8)
    box.set_margin_top(4)
    box.set_margin_bottom(8)

    left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    tag = Gtk.Label(label="NYXUS \u00b7 WORKSPACE 0 \u00b7 HOME", xalign=0.0)
    tag.add_css_class("header-tag")
    left.append(tag)
    title = Gtk.Label(xalign=0.0)
    title.set_use_markup(True)
    title.set_markup(
        f"<span foreground='{PALETTE['pink']}'>welcome</span> "
        f"back, <span foreground='{PALETTE['gold']}'>operator</span>"
    )
    title.add_css_class("header-title")
    left.append(title)
    left.set_hexpand(True)
    box.append(left)

    right = Gtk.Label(label="NYX-J5W-2026\nSIERENGOWSKI-LOCKED", xalign=1.0)
    right.add_css_class("header-stamp")
    right.set_justify(Gtk.Justification.RIGHT)
    box.append(right)
    return box


def _build_grid():
    """4-column Gtk.Grid mirroring the web HomeDashboard layout exactly:
       Row 0: Clock | Weather | Notifications | Calendar  (each 1 col)
       Row 1: Notepad spans 2 cols (left half)
       Row 2: Password Manager spans full 4 cols
    """
    grid = Gtk.Grid()
    grid.set_valign(Gtk.Align.START)
    grid.set_halign(Gtk.Align.FILL)
    grid.set_column_spacing(28)
    grid.set_row_spacing(28)
    grid.set_column_homogeneous(True)
    grid.set_hexpand(True)

    layout = [
        # (name,            card,                       col, row, w, h)
        ("Clock",           ClockCard(),                0, 0, 1, 1),
        ("Weather",         WeatherCard(),              1, 0, 1, 1),
        ("Notifications",   NotificationsCard(),        2, 0, 1, 1),
        ("Calendar",        CalendarCard(),             3, 0, 1, 1),
        ("Notepad",         NotepadCard(),              0, 1, 2, 1),
        ("Pulse",           SystemPulseCard(),          2, 1, 2, 1),
        ("Passwords",       PasswordManagerCard(),      0, 2, 4, 1),
    ]
    for name, c, col, row, w, h in layout:
        tilt = CARD_TILTS.get(name, 0.0)
        tilted = TiltBox(c.root, tilt=tilt)
        tilted.set_hexpand(True)
        tilted.set_halign(Gtk.Align.FILL)
        grid.attach(tilted, col, row, w, h)
    return grid


class HomeWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("NYXUS Home")
        self.set_default_size(1280, 820)

        # Overlay: graffiti BG underneath, content on top
        overlay = Gtk.Overlay()
        bg = GraffitiArea()
        overlay.set_child(bg)

        content_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        content_outer.set_margin_start(16)
        content_outer.set_margin_end(16)
        content_outer.set_margin_top(14)
        content_outer.set_margin_bottom(14)
        content_outer.append(_header_strip())

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(_build_grid())
        scroller.set_vexpand(True)
        scroller.set_hexpand(True)
        content_outer.append(scroller)

        overlay.add_overlay(content_outer)
        self.set_child(overlay)

        # Esc closes
        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._on_key)
        self.add_controller(kc)

    def _on_key(self, _ctrl, keyval, _kc, _state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False


class HomeApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=0)

    def do_activate(self):
        install_css()
        win = HomeWindow(self)
        win.present()


def main():
    app = HomeApp()
    return app.run(sys.argv)



# ─────────────────────────── NYXUS CHROME (auto-injected) ───────────────────
# Unifies look across every NYXUS GTK4 app: DARK MIRROR glass, Inter
# font, DARK MIRROR palette. Monkey-patches BOTH Gtk.ApplicationWindow.present
# AND Adw.ApplicationWindow.present so the canonical install_chrome()
# runs once per top-level window — without touching the app's own
# window-construction code. install_chrome auto-detects Adw vs Gtk
# windows and uses set_content/get_content vs set_child/get_child
# accordingly. nyxus-panel is intentionally excluded (LayerShell
# incompatibility with Gtk.Overlay). nyxus_chrome.py is shipped to
# ~/.nyxus by nyxus_install.sh.
try:
    import os as _nyx_os, sys as _nyx_sys
    _nyx_chrome_dir = _nyx_os.path.expanduser("~/.nyxus")
    if _nyx_chrome_dir not in _nyx_sys.path:
        _nyx_sys.path.insert(0, _nyx_chrome_dir)
    try:
        from nyxus_chrome import install_chrome as _nyx_install_chrome
    except ImportError:
        _nyx_install_chrome = lambda *a, **kw: None  # silent no-op
    _NYX_PAGE_KEY = "_home"
    def _nyx_make_present_hook(_orig):
        def _nyx_present(self):
            try: _nyx_install_chrome(self, page_key=_NYX_PAGE_KEY)
            except Exception: pass
            return _orig(self)
        return _nyx_present
    # Hook Gtk.ApplicationWindow (covers most NYXUS apps)
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk as _NyxGtk
        if not getattr(_NyxGtk.ApplicationWindow, "_nyx_chrome_hooked", False):
            _NyxGtk.ApplicationWindow.present = _nyx_make_present_hook(
                _NyxGtk.ApplicationWindow.present)
            _NyxGtk.ApplicationWindow._nyx_chrome_hooked = True
    except Exception as _nyx_eg:
        import sys as _nyx_sys
        print("nyxus-chrome Gtk hook skipped: %s" % _nyx_eg, file=_nyx_sys.stderr)
    # Hook Adw.ApplicationWindow (covers shield, sage, studio, godsapp)
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Adw", "1")
        from gi.repository import Adw as _NyxAdw
        if not getattr(_NyxAdw.ApplicationWindow, "_nyx_chrome_hooked", False):
            _NyxAdw.ApplicationWindow.present = _nyx_make_present_hook(
                _NyxAdw.ApplicationWindow.present)
            _NyxAdw.ApplicationWindow._nyx_chrome_hooked = True
    except Exception as _nyx_ea:
        # Adw missing is fine for pure-Gtk apps; only log if non-import
        if not isinstance(_nyx_ea, (ImportError, ValueError)):
            import sys as _nyx_sys
            print("nyxus-chrome Adw hook skipped: %s" % _nyx_ea, file=_nyx_sys.stderr)
except Exception as _nyx_e:
    import sys as _nyx_sys
    print("nyxus-chrome bootstrap skipped: %s" % _nyx_e, file=_nyx_sys.stderr)
# ────────────────────────── /NYXUS CHROME ───────────────────────────────────

if __name__ == "__main__":
    raise SystemExit(main())
