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

gi.require_version("Gtk",  "4.0")
gi.require_version("Gdk",  "4.0")
gi.require_version("Adw",  "1")
try:
    gi.require_version("Vte", "3.91")  # GTK4 build
    from gi.repository import Vte
    HAS_VTE = True
except (ValueError, ImportError):
    HAS_VTE = False

from gi.repository import Gtk, Gdk, Gio, GLib, Pango, Adw

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
    _hex("#0f1420"),  # 0  black
    _hex("#6a6e78"),  # 1  red    -> tertiary grey
    _hex("#c8ccd6"),  # 2  green  -> secondary
    _hex("#e8edf5"),  # 3  yellow -> off-white
    _hex("#6a6e78"),  # 4  blue   -> tertiary grey
    _hex("#c8ccd6"),  # 5  magenta-> secondary
    _hex("#e8edf5"),  # 6  cyan   -> off-white
    _hex("#e8edf5"),  # 7  white  -> off-white
    _hex("#1a1e2a"),  # 8  bright black
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


class NyxusTerminal(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        try: Adw.init()
        except Exception: pass

    def do_activate(self):
        # Force dark theme to match NYXUS DARK MIRROR aesthetic
        try:
            sm = Adw.StyleManager.get_default()
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        except Exception: pass
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

        # ── Clipboard helpers ──────────────────────────────────────────
        def _do_copy(*_a):
            try:
                if vte.get_has_selection():
                    vte.copy_clipboard_format(Vte.Format.TEXT)
                    return True
            except Exception:
                pass
            return False

        def _do_paste(*_a):
            try:
                vte.paste_clipboard()
                return True
            except Exception:
                return False

        def _do_select_all(*_a):
            try:
                vte.select_all()
                return True
            except Exception:
                return False

        # ── Keyboard: Ctrl+Shift+C/V (and X11 Ctrl+Insert/Shift+Insert)
        # Must use CAPTURE phase — VTE handles key-pressed first and
        # stops propagation by default, so a window controller in the
        # default BUBBLE phase never sees the keystroke. That's why
        # copy/paste appeared "broken" in r13. r14 captures first.
        kc = Gtk.EventControllerKey()
        kc.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)

        def _on_key(_c, keyval, _kc, state):
            ctrl  = bool(state & Gdk.ModifierType.CONTROL_MASK)
            shift = bool(state & Gdk.ModifierType.SHIFT_MASK)
            # Ctrl+Shift+C : copy   ·  Ctrl+Shift+V : paste
            if ctrl and shift:
                if keyval in (Gdk.KEY_c, Gdk.KEY_C):
                    return _do_copy()
                if keyval in (Gdk.KEY_v, Gdk.KEY_V):
                    return _do_paste()
                if keyval in (Gdk.KEY_a, Gdk.KEY_A):
                    return _do_select_all()
                if keyval in (Gdk.KEY_q, Gdk.KEY_Q):
                    win.close(); return True
                if keyval in (Gdk.KEY_n, Gdk.KEY_N):
                    # Ctrl+Shift+N — new terminal
                    try:
                        GLib.spawn_async([sys.argv[0]],
                                         flags=GLib.SpawnFlags.SEARCH_PATH)
                    except Exception:
                        pass
                    return True
            # X11-style: Ctrl+Insert copy / Shift+Insert paste
            if keyval == Gdk.KEY_Insert:
                if ctrl  and not shift: return _do_copy()
                if shift and not ctrl:  return _do_paste()
            return False
        kc.connect("key-pressed", _on_key)
        win.add_controller(kc)

        # ── Right-click context menu — Copy / Paste / Select All / New
        # Many users right-click before they learn the Ctrl+Shift pair.
        # This menu makes the operation discoverable without docs.
        menu = Gio.Menu()
        section = Gio.Menu()
        section.append("Copy",        "win.copy")
        section.append("Paste",       "win.paste")
        section.append("Select all",  "win.select-all")
        menu.append_section(None, section)
        section2 = Gio.Menu()
        section2.append("New terminal", "win.new")
        section2.append("Close",        "win.close")
        menu.append_section(None, section2)

        # Bind the menu actions to the same helpers used by the keys.
        def _add_action(name, fn):
            act = Gio.SimpleAction.new(name, None)
            act.connect("activate", lambda *_: fn())
            win.add_action(act)
        _add_action("copy",       _do_copy)
        _add_action("paste",      _do_paste)
        _add_action("select-all", _do_select_all)
        _add_action("close",      win.close)
        _add_action("new",
                    lambda: GLib.spawn_async([sys.argv[0]],
                                             flags=GLib.SpawnFlags.SEARCH_PATH))

        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_has_arrow(False)
        popover.set_parent(vte)

        gesture = Gtk.GestureClick()
        gesture.set_button(3)  # right click
        def _on_right_click(_g, _n, x, y):
            try:
                popover.set_pointing_to(Gdk.Rectangle(x=int(x), y=int(y),
                                                     width=1, height=1))
            except Exception:
                pass
            popover.popup()
        gesture.connect("pressed", _on_right_click)
        vte.add_controller(gesture)

        # ── Middle-click paste (X11 PRIMARY selection convention)
        gesture_mid = Gtk.GestureClick()
        gesture_mid.set_button(2)
        def _on_middle_click(*_a):
            try:
                vte.paste_primary()
            except Exception:
                _do_paste()
        gesture_mid.connect("pressed", _on_middle_click)
        vte.add_controller(gesture_mid)

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
