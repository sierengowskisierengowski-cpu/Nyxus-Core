#!/usr/bin/env python3
# ============================================================
#  NYXUS TERMINAL — bare VTE (DARK MIRROR rev 2026-05-07 r13)
#
#  Rewritten 2026-05-07: stripped every overlay, graffiti layer,
#  spray-can header, idle animation, and color palette. The window
#  is now just the VTE terminal widget on a dark-glass surface.
#
#  All visual presence (rim-light, glow, shadow, blur) is supplied
#  by Hyprland's system-wide DARK MIRROR active-border gradient
#  (white -> off-white #e8edf5 -> light grey #c8ccd6 -> faded
#  black -> ink black) defined in hyprland.conf. The terminal
#  itself contributes nothing — exactly what the user asked for.
#
#  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================
import gi, os, sys
gi.require_version("Gtk",  "4.0")
gi.require_version("Gdk",  "4.0")
try:
    gi.require_version("Vte", "3.91")  # GTK4 build
    from gi.repository import Vte
    HAS_VTE = True
except (ValueError, ImportError):
    HAS_VTE = False

from gi.repository import Gtk, Gdk, Gio, GLib, Pango

APP_ID  = "io.nyxus.terminal"
WIN_W   = 700
WIN_H   = 480

# DARK MIRROR palette
BG_RGBA       = (0.031, 0.047, 0.078, 0.55)   # rgba(8,12,20,0.55) dark glass
FG_HEX        = "#e8edf5"                     # off-white text
CURSOR_HEX    = "#ffffff"                     # pure white caret
SELECT_BG_HEX = "#c8ccd6"                     # light grey selection
SELECT_FG_HEX = "#000000"                     # ink on selection

# 16-color VTE palette — pure monochrome ramp, no neon
def _hex(h: str) -> Gdk.RGBA:
    r = Gdk.RGBA()
    r.parse(h)
    return r

VTE_PALETTE = [
    _hex("#0a0e16"),  # 0  black
    _hex("#6a6e78"),  # 1  red    -> tertiary grey
    _hex("#c8ccd6"),  # 2  green  -> secondary
    _hex("#e8edf5"),  # 3  yellow -> off-white
    _hex("#6a6e78"),  # 4  blue   -> tertiary grey
    _hex("#c8ccd6"),  # 5  magenta-> secondary
    _hex("#e8edf5"),  # 6  cyan   -> off-white
    _hex("#e8edf5"),  # 7  white  -> off-white
    _hex("#1a1f2a"),  # 8  bright black
    _hex("#9aa0ad"),  # 9  bright red    -> mid grey
    _hex("#c8ccd6"),  # 10 bright green
    _hex("#ffffff"),  # 11 bright yellow -> pure white
    _hex("#9aa0ad"),  # 12 bright blue
    _hex("#c8ccd6"),  # 13 bright magenta
    _hex("#ffffff"),  # 14 bright cyan
    _hex("#ffffff"),  # 15 bright white
]

CSS = b"""
window, .background {
    background: rgba(8, 12, 20, 0.55);
}
"""


class NyxusTerminal(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.NON_UNIQUE)

    def do_activate(self):
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        win = Gtk.ApplicationWindow(application=self, title="NYXUS Terminal")
        win.set_default_size(WIN_W, WIN_H)
        win.set_decorated(False)            # no titlebar — Hyprland glow IS the frame
        win.set_resizable(True)
        win.add_css_class("background")

        if not HAS_VTE:
            lbl = Gtk.Label(label="VTE not available — install vte3 / vte-2.91-gtk4")
            lbl.set_margin_top(40); lbl.set_margin_bottom(40)
            lbl.set_margin_start(40); lbl.set_margin_end(40)
            win.set_child(lbl)
            win.present()
            return

        vte = Vte.Terminal()
        vte.set_hexpand(True)
        vte.set_vexpand(True)

        # Colors
        bg = Gdk.RGBA(); bg.red, bg.green, bg.blue, bg.alpha = BG_RGBA
        fg = _hex(FG_HEX)
        vte.set_colors(fg, bg, VTE_PALETTE)
        vte.set_color_cursor(_hex(CURSOR_HEX))
        vte.set_color_cursor_foreground(_hex("#000000"))
        vte.set_color_highlight(_hex(SELECT_BG_HEX))
        vte.set_color_highlight_foreground(_hex(SELECT_FG_HEX))

        # Font: clean monospace, no ligatures
        vte.set_font(Pango.FontDescription("JetBrains Mono 11"))
        vte.set_cursor_blink_mode(Vte.CursorBlinkMode.ON)
        vte.set_cursor_shape(Vte.CursorShape.BLOCK)
        vte.set_scrollback_lines(10000)
        vte.set_mouse_autohide(True)
        vte.set_allow_hyperlink(True)

        # Modest inner padding so the dark glass shows around the text
        vte.set_margin_top(12); vte.set_margin_bottom(12)
        vte.set_margin_start(14); vte.set_margin_end(14)

        # Spawn the user's shell
        shell = os.environ.get("SHELL", "/bin/bash")
        vte.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.environ.get("HOME", "/"),
            [shell],
            [], GLib.SpawnFlags.DEFAULT,
            None, None, -1, None, None,
        )
        vte.connect("child-exited", lambda *_: win.close())

        # Ctrl+Shift+C / Ctrl+Shift+V — copy / paste
        kc = Gtk.EventControllerKey()
        def _on_key(_c, keyval, _kc, state):
            ctrl  = state & Gdk.ModifierType.CONTROL_MASK
            shift = state & Gdk.ModifierType.SHIFT_MASK
            if ctrl and shift:
                if keyval in (Gdk.KEY_c, Gdk.KEY_C):
                    vte.copy_clipboard_format(Vte.Format.TEXT); return True
                if keyval in (Gdk.KEY_v, Gdk.KEY_V):
                    vte.paste_clipboard(); return True
                if keyval in (Gdk.KEY_q, Gdk.KEY_Q):
                    win.close(); return True
            return False
        kc.connect("key-pressed", _on_key)
        win.add_controller(kc)

        win.set_child(vte)
        win.present()
        vte.grab_focus()


# ── Try to apply unified DARK MIRROR chrome (no-op if unavailable) ──────────
try:
    sys.path.insert(0, os.path.expanduser("~/.nyxus"))
    from nyxus_chrome import install_chrome as _nyx_install_chrome  # noqa
except Exception:
    pass


def main():
    app = NyxusTerminal()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
