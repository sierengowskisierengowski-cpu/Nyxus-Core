#!/usr/bin/env python3
# ============================================================================
# NYXUS — Screensaver
# /usr/share/nyxus/scripts/nyxus_screensaver.py
#
# Minimal fullscreen idle screen. Displays the NYXUS logo, wordmark, clock,
# and tagline on a pure-black background. Owned and torn down by hypridle:
#
#     listener {
#       timeout    = 180
#       on-timeout = nyxus-screensaver &
#       on-resume  = pkill -f nyxus_screensaver ; nyxus-demon-wake &
#     }
#
# So this process does NOT handle input itself — hypridle pkills it on
# wake and then spawns the demon jumpscare overlay.
#
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
import gi
import sys
import signal
import time

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

# ── chrome intentionally NOT imported: this app runs fullscreen and the
#    chrome size-policy hook would unfullscreen it. The unified palette is
#    still applied via in-file CSS that uses nyxus_palette constants.
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio  # noqa: E402


_CSS = b"""
window.nyx-screensaver { background: #000000; }
.nyx-logo {
  color: rgba(192, 132, 252, 0.95);
  font-family: 'JetBrains Mono', monospace;
  font-size: 96px;
  font-weight: 800;
  text-shadow: 0 0 28px rgba(192, 132, 252, 0.60);
}
.nyx-word {
  color: rgba(192, 132, 252, 0.85);
  font-family: 'JetBrains Mono', monospace;
  font-size: 28px;
  font-weight: 700;
  letter-spacing: 0.55em;
  text-shadow: 0 0 14px rgba(192, 132, 252, 0.40);
}
.nyx-clock {
  color: rgba(192, 132, 252, 0.85);
  font-family: 'JetBrains Mono', monospace;
  font-size: 56px;
  font-weight: 600;
}
.nyx-tag {
  color: rgba(120, 80, 160, 0.55);
  font-family: 'JetBrains Mono', monospace;
  font-size: 13px;
  letter-spacing: 0.45em;
}
.nyx-pulse {
  color: rgba(192, 132, 252, 0.18);
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.6em;
}
"""


class ScreensaverWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NYXUS Screensaver")
        self.add_css_class("nyx-screensaver")
        self.set_decorated(False)
        self.fullscreen()

        css = Gtk.CssProvider()
        css.load_from_data(_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_USER,
        )

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_hexpand(True)
        box.set_vexpand(True)

        logo = Gtk.Label(label="\u25e4 X \u25e5")
        logo.add_css_class("nyx-logo")

        word = Gtk.Label(label="N Y X U S")
        word.add_css_class("nyx-word")

        sep_top = Gtk.Label(label="\u2500" * 28)
        sep_top.add_css_class("nyx-pulse")

        self.clock = Gtk.Label(label=time.strftime("%H:%M"))
        self.clock.add_css_class("nyx-clock")

        sep_bot = Gtk.Label(label="\u2500" * 28)
        sep_bot.add_css_class("nyx-pulse")

        tag = Gtk.Label(label="S I L E N T  .  D A R K  .  P U R E L Y   F U N C T I O N A L")
        tag.add_css_class("nyx-tag")

        for w in (logo, word, sep_top, self.clock, sep_bot, tag):
            box.append(w)

        self.set_child(box)
        GLib.timeout_add_seconds(10, self._tick_clock)

    def _tick_clock(self):
        try:
            self.clock.set_text(time.strftime("%H:%M"))
        except Exception:
            pass
        return True


def _on_activate(app):
    win = ScreensaverWindow(app)
    win.present()


def main():
    # hypridle on-resume sends `pkill -f nyxus_screensaver`; honor SIGTERM cleanly.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    app = Gtk.Application(
        application_id="app.nyxus.Screensaver",
        flags=Gio.ApplicationFlags.FLAGS_NONE,
    )
    app.connect("activate", _on_activate)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
