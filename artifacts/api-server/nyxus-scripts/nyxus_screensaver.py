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

gi.require_version("Gtk", "4.0")
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
