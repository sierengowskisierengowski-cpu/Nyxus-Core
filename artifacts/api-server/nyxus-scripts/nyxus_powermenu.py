#!/usr/bin/env python3
"""
NYXUS Power Menu — standalone Adw.Application replacement for the legacy
EWW powermenu overlay, for users who launch from the app menu instead of
the keybind.

DARK MIRROR rev r1 · 2026-05-12

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

© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
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

CSS = b"""
window.pm-window { background: rgba(8, 12, 20, 0.92); }

.pm-title {
    font-family: "Inter Display", "Inter", sans-serif;
    font-weight: 600;
    font-size: 22px;
    color: #ffffff;
    letter-spacing: 0.18em;
    margin: 28px 0 8px 0;
}
.pm-subtitle {
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    color: #9aa0ad;
    letter-spacing: 0.22em;
    margin-bottom: 28px;
}

.pm-tile {
    background: rgba(15, 20, 32, 0.72);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 14px;
    min-width: 180px;
    min-height: 160px;
    padding: 22px;
    transition: all 160ms ease-out;
}
.pm-tile:hover {
    background: rgba(28, 36, 56, 0.85);
    border-color: rgba(255, 255, 255, 0.22);
}
.pm-tile.pm-warn:hover {
    border-color: rgba(255, 200, 80, 0.55);
}
.pm-tile.pm-danger:hover {
    border-color: rgba(255, 90, 90, 0.65);
}
.pm-tile.pm-cancel { background: rgba(8, 12, 20, 0.55); }

.pm-glyph {
    font-family: "Symbols Nerd Font", "JetBrainsMono Nerd Font", monospace;
    font-size: 38px;
    color: #e8edf5;
}
.pm-tile.pm-warn   .pm-glyph { color: #ffd07a; }
.pm-tile.pm-danger .pm-glyph { color: #ff7a7a; }

.pm-label {
    font-family: "Inter", sans-serif;
    font-weight: 500;
    font-size: 14px;
    color: #e8edf5;
    letter-spacing: 0.10em;
    margin-top: 14px;
}

.pm-hint {
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    color: #6a6e78;
    letter-spacing: 0.18em;
    margin-top: 22px;
    margin-bottom: 18px;
}
"""


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

        title = Gtk.Label(label="POWER")
        title.add_css_class("pm-title")
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

        prov = Gtk.CssProvider()
        try: prov.load_from_data(CSS)
        except Exception:
            try: prov.load_from_string(CSS.decode())
            except Exception: pass
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        win = PowermenuWindow(self)
        win.present()


def main() -> int:
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT,  lambda *_: sys.exit(0))
    return PowermenuApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
