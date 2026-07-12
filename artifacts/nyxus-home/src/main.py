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
from aurora import AuroraArea                                          # noqa: E402
from hero import HeroStrip                                             # noqa: E402
from widgets import (                                                  # noqa: E402
    WeatherCard, CalendarCard, NotepadCard, PasswordManagerCard,
)
from notif import NotificationsCard                                    # noqa: E402
from deck import MusicDeckCard                                         # noqa: E402
from sentinel import JettCard, HoneypotCard                            # noqa: E402
from hud import (                                                      # noqa: E402
    SystemCoreCard, FansCard, NetworkCard, StorageCard, ProcessesCard,
)

APP_ID = "io.nyxus.home"


def _build_grid():
    """4-column OBSIDIAN REACTOR command deck (all live data):
       Row 0: SYSTEM CORE — rings + per-core bars + temps    (spans 4)
       Row 1: JETT AI EDR (2)         | HONEYPOT GRID (2)     SENTINEL row
       Row 2: MUSIC DECK (2)          | NETWORK (2)
       Row 3: Fans | Storage | Weather | Calendar
       Row 4: Notepad (2) | Top Procs (1) | Notifications (1)
       Row 5: Password Manager (spans 4)
    """
    grid = Gtk.Grid()
    grid.set_valign(Gtk.Align.START)
    grid.set_halign(Gtk.Align.FILL)
    grid.set_column_spacing(24)
    grid.set_row_spacing(24)
    grid.set_column_homogeneous(True)
    grid.set_hexpand(True)

    layout = [
        # (card,                    col, row, w, h)
        (SystemCoreCard(),          0, 0, 4, 1),
        (JettCard(),                0, 1, 2, 1),
        (HoneypotCard(),            2, 1, 2, 1),
        (MusicDeckCard(),           0, 2, 2, 1),
        (NetworkCard(),             2, 2, 2, 1),
        (FansCard(),                0, 3, 1, 1),
        (StorageCard(),             1, 3, 1, 1),
        (WeatherCard(),             2, 3, 1, 1),
        (CalendarCard(),            3, 3, 1, 1),
        (NotepadCard(),             0, 4, 2, 1),
        (ProcessesCard(),           2, 4, 1, 1),
        (NotificationsCard(),       3, 4, 1, 1),
        (PasswordManagerCard(),     0, 5, 4, 1),
    ]
    for c, col, row, w, h in layout:
        c.root.set_hexpand(True)
        c.root.set_halign(Gtk.Align.FILL)
        grid.attach(c.root, col, row, w, h)
    return grid


class HomeWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("NYXUS Home")
        self.set_default_size(1280, 820)

        # Overlay: animated cosmic BG underneath, content on top
        overlay = Gtk.Overlay()
        try:
            from nyxus_cosmic_bg import CosmicSceneArea
            bg = CosmicSceneArea("milky_way")
        except Exception:
            bg = AuroraArea()
        overlay.set_child(bg)

        content_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                spacing=18)
        content_outer.set_margin_start(20)
        content_outer.set_margin_end(20)
        content_outer.set_margin_top(16)
        content_outer.set_margin_bottom(16)
        content_outer.append(HeroStrip().root)

        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_child(_build_grid())
        scroller.set_vexpand(True)
        scroller.set_hexpand(True)
        content_outer.append(scroller)

        # NYXUS_HOME_SCROLL=0..1 — open pre-scrolled to that fraction
        # (debug/screenshot aid; no effect when the var is unset).
        frac = os.environ.get("NYXUS_HOME_SCROLL")
        if frac:
            def _pre_scroll():
                adj = scroller.get_vadjustment()
                try:
                    f = min(1.0, max(0.0, float(frac)))
                except ValueError:
                    return False
                adj.set_value(adj.get_lower()
                              + f * (adj.get_upper() - adj.get_page_size()
                                     - adj.get_lower()))
                return False
            GLib.timeout_add(600, _pre_scroll)

        overlay.add_overlay(content_outer)
        self.set_child(overlay)

        # Esc leaves the dashboard (back to the previous workspace) —
        # the home page itself stays alive on name:0 permanently.
        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._on_key)
        self.add_controller(kc)

    def _on_key(self, _ctrl, keyval, _kc, _state):
        if keyval == Gdk.KEY_Escape:
            import subprocess
            try:
                subprocess.Popen(
                    ["hyprctl", "dispatch", "workspace", "previous"])
            except OSError:
                pass
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
