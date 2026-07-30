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
# © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
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
    WHITE_PURE='#ffffff'; WHITE_OFF='#eef2fa'; GREY_LIGHT='#c8ccd6'
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
gi.require_version("Adw", "1")

# ── chrome intentionally NOT imported: this app runs fullscreen and the
#    chrome size-policy hook would unfullscreen it. The unified palette is
#    still applied via in-file CSS that uses nyxus_palette constants.
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio, Adw  # noqa: E402


_CSS = b"""
window.nyx-screensaver { background: #05010d; }
/* dim scrim over the alien wallpaper so the clock stays legible */
.nyx-scrim { background: rgba(5, 3, 14, 0.55); }

/* ALIEN NEON card -- same visual language as hyprlock's Prism HUD clock
 * card (near-black glass, 1px neon hairline, 2px accent top rule) so the
 * idle screen doesn't read as a plain, undesigned placeholder before
 * hyprlock takes over. */
.nyx-card {
  background-color: rgba(7, 5, 14, 0.82);
  border: 1px solid rgba(125, 61, 255, 0.32);
  border-top: 2px solid #7d3dff;
  border-radius: 16px;
  padding: 40px 64px;
}
.nyx-card.nyx-pulse-on { border-top-color: #ff2dad; }

.nyx-logo {
  color: #7d3dff;
  font-family: 'JetBrains Mono', monospace;
  font-size: 72px;
  font-weight: 800;
  text-shadow: 0 0 8px rgba(125, 61, 255, 0.85),
               0 0 28px rgba(125, 61, 255, 0.55),
               0 0 60px rgba(125, 61, 255, 0.30);
}
.nyx-word {
  color: #eef2fa;
  font-family: 'JetBrains Mono', monospace;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 0.55em;
  text-shadow: 0 0 10px rgba(255, 45, 173, 0.45);
}
.nyx-clock {
  color: #eef2fa;
  font-family: 'JetBrains Mono', monospace;
  font-size: 56px;
  font-weight: 600;
  text-shadow: 0 0 18px rgba(43, 210, 255, 0.45);
}
.nyx-tag {
  color: rgba(238, 242, 250, 0.45);
  font-family: 'JetBrains Mono', monospace;
  font-size: 12px;
  letter-spacing: 0.42em;
}
.nyx-pulse {
  color: rgba(125, 61, 255, 0.55);
  font-family: 'JetBrains Mono', monospace;
  font-size: 9px;
  letter-spacing: 0.6em;
}
.nyx-pulse.nyx-pulse-on { color: rgba(255, 45, 173, 0.75); }
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

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=22)
        card.set_halign(Gtk.Align.CENTER)
        card.set_valign(Gtk.Align.CENTER)
        card.add_css_class("nyx-card")

        logo = Gtk.Label(label="\u25e4 X \u25e5")
        logo.add_css_class("nyx-logo")

        word = Gtk.Label(label="N Y X U S")
        word.add_css_class("nyx-word")

        self.sep_top = Gtk.Label(label="\u2500" * 28)
        self.sep_top.add_css_class("nyx-pulse")

        self.clock = Gtk.Label(label=time.strftime("%H:%M"))
        self.clock.add_css_class("nyx-clock")

        self.sep_bot = Gtk.Label(label="\u2500" * 28)
        self.sep_bot.add_css_class("nyx-pulse")

        tag = Gtk.Label(label="S I L E N T  .  D A R K  .  P U R E L Y   F U N C T I O N A L")
        tag.add_css_class("nyx-tag")

        for w in (logo, word, self.sep_top, self.clock, self.sep_bot, tag):
            card.append(w)

        # Outer centering box \u2014 the card hugs its content; this fills/centers it.
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_halign(Gtk.Align.CENTER)
        box.set_valign(Gtk.Align.CENTER)
        box.set_hexpand(True)
        box.set_vexpand(True)
        box.append(card)
        self._card = card
        self._pulse_on = False

        # Alien-wallpaper backdrop (rev 2026-07-21): the idle screen shows one
        # of the NYXUS alien walls behind the clock instead of flat black.
        # Falls back to the CSS base colour if no wallpaper resolves, so the
        # saver never fails to open. Override with NYXUS_SCREENSAVER_WALL.
        import os
        overlay = Gtk.Overlay()
        wall = os.environ.get("NYXUS_SCREENSAVER_WALL", "")
        candidates = [wall] if wall else []
        candidates += [
            "/usr/share/backgrounds/nyxus/nyxus-urban-alien.png",
            "/usr/share/backgrounds/nyxus/nyxus-login-wall.png",
            "/usr/share/backgrounds/nyxus/nyxus-desktop-hero.png",
            os.path.expanduser("~/.config/hypr/walls/nyxus-urban-alien.png"),
        ]
        picked = next((p for p in candidates if p and os.path.isfile(p)), None)
        if picked:
            try:
                pic = Gtk.Picture.new_for_filename(picked)
                pic.set_content_fit(Gtk.ContentFit.COVER)
                pic.set_can_shrink(True)
                pic.set_hexpand(True)
                pic.set_vexpand(True)
                overlay.set_child(pic)
                scrim = Gtk.Box()
                scrim.add_css_class("nyx-scrim")
                scrim.set_hexpand(True)
                scrim.set_vexpand(True)
                overlay.add_overlay(scrim)
            except Exception:
                pass
        overlay.add_overlay(box)
        self.set_child(overlay)
        GLib.timeout_add_seconds(10, self._tick_clock)
        # Slow violet<->magenta breathing glow on the card's top rule + the
        # hairline separators — the one bit of ambient motion on an
        # otherwise static idle screen, matching the "living" feel of the
        # reactive layer on the main desktop.
        GLib.timeout_add_seconds(2, self._tick_pulse)

    def _tick_clock(self):
        try:
            self.clock.set_text(time.strftime("%H:%M"))
        except Exception:
            pass
        return True

    def _tick_pulse(self):
        try:
            self._pulse_on = not self._pulse_on
            for w in (self._card, self.sep_top, self.sep_bot):
                if self._pulse_on:
                    w.add_css_class("nyx-pulse-on")
                else:
                    w.remove_css_class("nyx-pulse-on")
        except Exception:
            pass
        return True


def _on_activate(app):
    win = ScreensaverWindow(app)
    win.present()
    # Re-assert fullscreen AFTER the surface is mapped. The fullscreen() call
    # in __init__ runs before the wayland surface exists and wlroots drops it,
    # so on its own the saver maps as a 900x650 floating window with the
    # desktop showing all around it. The window rules cannot rescue this:
    # `pin on` forces the window floating, which defeats `fullscreen on`.
    # nyxus_matrix_saver.py already carries this same idle_add for the same
    # reason -- measured on a live session 2026-07-30.
    GLib.idle_add(win.fullscreen)


def main():
    # hypridle on-resume sends `pkill -f nyxus_screensaver`; honor SIGTERM cleanly.
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    try: Adw.init()
    except Exception: pass
    app = Adw.Application(
        application_id="app.nyxus.Screensaver",
        flags=Gio.ApplicationFlags.FLAGS_NONE,
    )
    def _on_activate_dark(_app):
        try:
            sm = Adw.StyleManager.get_default()
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        except Exception: pass
        _on_activate(_app)
    app.connect("activate", _on_activate_dark)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
