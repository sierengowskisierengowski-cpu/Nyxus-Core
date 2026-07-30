#!/usr/bin/env python3
"""
NYXUS Power Menu — standalone Adw.Application replacement for the legacy
EWW powermenu overlay, for users who launch from the app menu instead of
the keybind.

ALIEN NEON rev r1 · 2026-05-12

Six actions, each a big tactile tile with a nerd-font glyph + label:

    Lock      Suspend   Logout
    Restart   Shutdown  Cancel

Destructive actions (Restart, Shutdown, Logout) gate behind an
Adw.MessageDialog confirm so a misclick can't nuke an unsaved session.

Backends:
    Lock      → hyprlock                   (or `loginctl lock-session`)
    Suspend   → systemctl suspend
    Logout    → hyprctl dispatch exit      (or `loginctl terminate-session`)
    Restart   → systemctl reboot
    Shutdown  → systemctl poweroff

Esc cancels the window. Honors $NYXUS_DRY_RUN=1 for safe local testing.

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, GLib, Gio, Adw  # noqa: E402

# ── NYXUS shared chrome (rainbow titles + graffiti walls, system-wide) ──
sys.path.insert(0, str(Path.home() / ".local" / "bin"))
sys.path.insert(0, "/opt/nyxus")
try:
    from nyxus_chrome import install_chrome  # type: ignore
    HAS_CHROME = True
except Exception:
    HAS_CHROME = False

APP_ID = "io.nyxus.powermenu"
DRY_RUN = os.environ.get("NYXUS_DRY_RUN") == "1"

# ── Action table ────────────────────────────────────────────────────────────
# (key, label, glyph, css-class, requires-confirm, primary-cmd, fallback-cmd)
ACTIONS = [
    ("lock",     "Lock",      "\uf023",  "pm-safe",   False,
     ["hyprlock"],            ["loginctl", "lock-session"]),
    ("suspend",  "Suspend",   "\uf186",  "pm-safe",   False,
     ["systemctl", "suspend"], None),
    ("logout",   "Logout",    "\uf08b",  "pm-warn",   True,
     ["hyprctl", "dispatch", "exit"], ["loginctl", "terminate-user", os.environ.get("USER", "")]),
    ("restart",  "Restart",   "\uf021",  "pm-danger", True,
     ["systemctl", "reboot"], None),
    ("shutdown", "Shutdown",  "\uf011",  "pm-danger", True,
     ["systemctl", "poweroff"], None),
    ("cancel",   "Cancel",    "\uf00d",  "pm-cancel", False,
     None, None),
]

# ── HOME HUD visual language + graffiti voice, from the shared
#    nyxus_palette helpers. Tiles wear per-action HUD hues:
#    safe = cyan · warn = gold · danger = red · cancel = mono.
try:
    from nyxus_palette import (HUD_PALETTE, hud_css_bundle,
                               install_hud_css)
except Exception:
    HUD_PALETTE = {"pink": "#ff2dad", "cyan": "#2bd2ff", "gold": "#ff8a1e",
                   "red": "#ff2d55", "mono": "#eef2fa"}
    def hud_css_bundle(sel="window", hues=()):  # noqa: E704
        return ""
    install_hud_css = None


def _pm_css() -> str:
    pink = HUD_PALETTE.get("pink", "#ff2dad")
    css = hud_css_bundle("window.pm-window", ("pink",))
    css += f"""
/* Stays as the base coat AND as the fallback: if no urban-alien wall resolves
 * (see _find_wall) the window simply reads as it always did, flat void. */
window.pm-window {{
    background: rgba(5, 1, 13, 0.96);
}}
/* Same ink as the screensaver's .nyx-scrim, but ramped instead of flat.
 * The six tiles carry their own rgba(7,5,14,0.93) fill so their glyphs and
 * labels never depend on the scrim; the title, "WHAT DO YOU WANT TO DO" and
 * "ESC TO DISMISS" sit straight on the wall, and at a flat 0.55 the 9px hint
 * was unreadable wherever the nebula was bright (a text-shadow outline was
 * tried first and GTK did not carry it far enough). So: heavy ink in the top
 * and bottom bands where the loose text lives, lighter than 0.55 through the
 * middle where only tiles and gutters are — which shows MORE art, not less. */
.pm-scrim {{
    background: linear-gradient(to bottom,
                rgba(5, 3, 14, 0.90)   0%,
                rgba(5, 3, 14, 0.42)  24%,
                rgba(5, 3, 14, 0.42)  72%,
                rgba(5, 3, 14, 0.94) 100%);
}}
.pm-title {{
    font-family: "Permanent Marker", cursive;
    font-size: 30px;
    color: {pink};
    text-shadow: 0 0 10px alpha({pink}, 0.70),
                 0 0 26px alpha({pink}, 0.40);
    letter-spacing: 0.06em;
    margin: 28px 0 4px 0;
}}
/* The two grey strings sit directly on the wall, not on a tile, so they are
 * the only text the art can eat. An ink halo (no colour change — the ALIEN
 * NEON greys stay exactly as they were) carries them over the graffiti. */
.pm-subtitle {{
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    color: #9aa0ad;
    letter-spacing: 0.26em;
    margin-bottom: 26px;
    text-shadow: -1px 0 0 rgba(5, 1, 13, 0.95),
                  1px 0 0 rgba(5, 1, 13, 0.95),
                  0 -1px 0 rgba(5, 1, 13, 0.95),
                  0  1px 0 rgba(5, 1, 13, 0.95),
                  0 0 9px rgba(5, 1, 13, 1.0);
}}
.pm-hint {{
    font-family: "JetBrains Mono", monospace;
    font-size: 9px;
    color: #6a6e78;
    letter-spacing: 0.22em;
    margin-top: 22px;
    margin-bottom: 18px;
    text-shadow: -1px 0 0 rgba(5, 1, 13, 0.95),
                  1px 0 0 rgba(5, 1, 13, 0.95),
                  0 -1px 0 rgba(5, 1, 13, 0.95),
                  0  1px 0 rgba(5, 1, 13, 0.95),
                  0 0 9px rgba(5, 1, 13, 1.0);
}}
"""
    # Per-action hue tiles — HUD cards with solid top rule + bloom.
    for cls, hue in (("pm-safe", "cyan"), ("pm-warn", "gold"),
                     ("pm-danger", "red"), ("pm-cancel", "mono")):
        c = HUD_PALETTE.get(hue, "#eef2fa")
        css += f"""
.pm-tile.{cls} {{
    background: rgba(7, 5, 14, 0.93);
    border: 1px dashed alpha({c}, 0.45);
    border-top: 2px solid {c};
    border-radius: 8px;
    min-width: 180px;
    min-height: 160px;
    padding: 22px;
    transition: box-shadow 320ms ease, border-color 320ms ease;
}}
.pm-tile.{cls}:hover {{
    background: alpha({c}, 0.08);
    border-color: {c};
    box-shadow: 0 0 26px alpha({c}, 0.45);
}}
.pm-tile.{cls} .pm-glyph {{
    font-family: "Symbols Nerd Font", "JetBrainsMono Nerd Font", monospace;
    font-size: 38px;
    color: {c};
    text-shadow: 0 0 12px alpha({c}, 0.60),
                 0 0 26px alpha({c}, 0.30);
}}
.pm-tile.{cls} .pm-label {{
    font-family: "JetBrains Mono", monospace;
    font-weight: 700;
    font-size: 11px;
    color: {c};
    letter-spacing: 0.22em;
    margin-top: 14px;
}}
"""
    return css

CSS = _pm_css()

# ── URBAN-ALIEN CANVAS (rev 2026-07-30, owner decision) ─────────────────────
# The eww Super+Escape overlay, hyprlock, the greeter and the idle screensaver
# all wear nyxus-urban-alien; this window — the same menu, reached from the app
# menu instead of the keybind — was the one power surface still painted flat.
# Same resolution order as nyxus_screensaver so both agree on which file wins,
# plus the offline cache dir nyxus_chrome uses. `/usr/share/backgrounds/nyxus`
# is the shipped location; `~/.config/hypr/walls` is where a live install keeps
# it, and on a dev box only the latter exists.
_WALL_CANDIDATES = (
    "/usr/share/backgrounds/nyxus/nyxus-urban-alien.png",
    os.path.expanduser("~/.config/hypr/walls/nyxus-urban-alien.png"),
    "/opt/nyxus-cache/hypr-walls/nyxus-urban-alien.png",
)


def _find_wall() -> str | None:
    override = os.environ.get("NYXUS_POWERMENU_WALL", "")
    for p in ((override,) if override else ()) + _WALL_CANDIDATES:
        try:
            if p and os.path.isfile(p):
                return p
        except Exception:
            continue
    return None


def _run(cmd: list[str]) -> bool:
    """Best-effort exec. Returns True on success or DRY_RUN."""
    if DRY_RUN:
        sys.stderr.write(f"[powermenu DRY_RUN] {' '.join(cmd)}\n")
        return True
    if not cmd or not shutil.which(cmd[0]):
        return False
    try:
        subprocess.Popen(cmd, start_new_session=True)
        return True
    except Exception as e:
        sys.stderr.write(f"[powermenu] {' '.join(cmd)} failed: {e}\n")
        return False


def _do_action(key: str, primary: list[str] | None,
               fallback: list[str] | None) -> bool:
    if primary and _run(primary):
        return True
    if fallback and _run(fallback):
        return True
    sys.stderr.write(f"[powermenu] no working backend for '{key}'\n")
    return False


# ────────────────────────────────────────────────────────────────────────────
class PowermenuWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="NYXUS Power")
        self.set_default_size(680, 540)
        self.set_resizable(False)
        self.add_css_class("pm-window")

        if HAS_CHROME:
            try: install_chrome(self, key="_powermenu")
            except Exception: pass

        # Esc closes
        controller = Gtk.EventControllerKey()
        controller.connect("key-pressed", self._on_key)
        self.add_controller(controller)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                       halign=Gtk.Align.CENTER,
                       valign=Gtk.Align.CENTER)
        root.set_margin_top(24); root.set_margin_bottom(24)
        root.set_margin_start(24); root.set_margin_end(24)

        title = Gtk.Label(label="Power")
        title.add_css_class("pm-title")
        title.add_css_class("neon-flicker")
        title.set_xalign(0.5)

        subtitle = Gtk.Label(label="WHAT DO YOU WANT TO DO")
        subtitle.add_css_class("pm-subtitle")
        subtitle.set_xalign(0.5)

        grid = Gtk.Grid()
        grid.set_row_spacing(16)
        grid.set_column_spacing(16)
        grid.set_halign(Gtk.Align.CENTER)

        for idx, (key, label, glyph, css, confirm, primary, fb) in enumerate(ACTIONS):
            row = idx // 3
            col = idx % 3
            tile = self._make_tile(key, label, glyph, css, confirm, primary, fb)
            grid.attach(tile, col, row, 1, 1)

        hint = Gtk.Label(label="ESC TO DISMISS")
        hint.add_css_class("pm-hint")
        hint.set_xalign(0.5)

        root.append(title)
        root.append(subtitle)
        root.append(grid)
        root.append(hint)

        wall = _find_wall()
        if wall:
            try:
                overlay = Gtk.Overlay()
                pic = Gtk.Picture.new_for_filename(wall)
                pic.set_content_fit(Gtk.ContentFit.COVER)
                pic.set_can_shrink(True)
                pic.set_hexpand(True)
                pic.set_vexpand(True)
                overlay.set_child(pic)
                scrim = Gtk.Box()
                scrim.add_css_class("pm-scrim")
                scrim.set_hexpand(True)
                scrim.set_vexpand(True)
                overlay.add_overlay(scrim)
                overlay.add_overlay(root)
                # Without this the overlay measures only the Picture, which is
                # set_can_shrink(True) and therefore asks for nothing — the
                # window collapses to set_default_size and clips the outer
                # tiles and the ESC hint clean off. Measure the tile grid.
                overlay.set_measure_overlay(root, True)
                self.set_content(overlay)
                return
            except Exception:
                pass
        self.set_content(root)

    def _make_tile(self, key, label, glyph, css, confirm, primary, fb):
        btn = Gtk.Button()
        btn.add_css_class("pm-tile")
        btn.add_css_class(css)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                      halign=Gtk.Align.CENTER,
                      valign=Gtk.Align.CENTER)

        gl = Gtk.Label(label=glyph)
        gl.add_css_class("pm-glyph")
        gl.set_xalign(0.5)

        lb = Gtk.Label(label=label.upper())
        lb.add_css_class("pm-label")
        lb.set_xalign(0.5)

        box.append(gl)
        box.append(lb)
        btn.set_child(box)

        def _clicked(_b):
            if key == "cancel":
                self.close()
                return
            if confirm:
                self._confirm_then(key, label, primary, fb)
            else:
                _do_action(key, primary, fb)
                self.close()

        btn.connect("clicked", _clicked)
        return btn

    def _confirm_then(self, key, label, primary, fb):
        body = {
            "logout":   "End your session and return to the login screen?",
            "restart":  "Restart the system now?",
            "shutdown": "Power off the system now?",
        }.get(key, f"Confirm {label}?")

        dlg = Adw.MessageDialog.new(self, label.upper(), body)
        dlg.add_response("cancel",  "Cancel")
        dlg.add_response("confirm", label)
        dlg.set_response_appearance(
            "confirm",
            Adw.ResponseAppearance.DESTRUCTIVE if key in ("restart", "shutdown")
            else Adw.ResponseAppearance.SUGGESTED,
        )
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")

        def _on_resp(_d, resp):
            if resp == "confirm":
                _do_action(key, primary, fb)
            self.close()
        dlg.connect("response", _on_resp)
        dlg.present()

    def _on_key(self, _ctrl, keyval, _kc, _state):
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        return False


# ────────────────────────────────────────────────────────────────────────────
class PowermenuApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        try: Adw.init()
        except Exception: pass

    def do_activate(self):
        try:
            sm = Adw.StyleManager.get_default()
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        except Exception: pass

        # PRIORITY_USER + 1 so the HUD tiles outrank nyxus_chrome glass.
        if install_hud_css is None or not install_hud_css(CSS):
            prov = Gtk.CssProvider()
            try: prov.load_from_data(CSS.encode())
            except Exception: pass
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), prov,
                Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

        win = PowermenuWindow(self)
        win.present()


def main() -> int:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT,  lambda *_: sys.exit(0))
    return PowermenuApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
