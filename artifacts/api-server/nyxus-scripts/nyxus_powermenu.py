#!/usr/bin/env python3
"""
NYXUS Power Menu — lock / logout / suspend / reboot / shutdown.

GTK4 + unified NYXUS chrome. Esc or click-outside cancels. Each action
is a sketch-style button with neon glow. Keyboard shortcuts: L lock,
O logout, S suspend, R reboot, P poweroff.

Bind to a Hyprland keybind:
    bind = SUPER, Escape, exec, python3 ~/.local/bin/nyxus_powermenu.py
"""
from __future__ import annotations
import gi, os, sys, subprocess
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".local" / "bin"))
try:
    from nyxus_chrome import install_chrome, rainbow_markup  # type: ignore
    HAS_CHROME = True
except Exception:
    HAS_CHROME = False
    def install_chrome(win, key="_powermenu"): return None
    def rainbow_markup(s: str) -> str:
        return f"<span foreground='#e8edf5' font_weight='bold'>{s}</span>"

WIN_W, WIN_H = 560, 360


def run(cmd: str) -> None:
    try:
        subprocess.Popen(cmd, shell=True, start_new_session=True)
    except Exception as e:
        print(f"powermenu: {cmd} failed: {e}", file=sys.stderr)


def lock_cmd() -> str:
    if any((Path(p) / "hyprlock").exists()
           for p in os.environ.get("PATH", "").split(":")):
        return "hyprlock"
    return "swaylock -c 000000"


ACTIONS = [
    ("Lock",     "L", "🔒", "#c8ccd6", lambda: run(lock_cmd())),
    ("Logout",   "O", "↩",  "#c8ccd6",
        lambda: run("hyprctl dispatch exit")),
    ("Suspend",  "S", "💤", "#e8edf5",
        lambda: run("systemctl suspend")),
    ("Hibernate","H", "🛌", "#ff8800",
        lambda: run("systemctl hibernate")),
    ("Reboot",   "R", "↻",  "#e8edf5",
        lambda: run("systemctl reboot")),
    ("Shutdown", "P", "⏻",  "#ff3030",
        lambda: run("systemctl poweroff")),
]


class PowerMenu(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.powermenu",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)

    def do_activate(self):
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self,
                                         title="NYXUS Power")
        self.win.set_default_size(WIN_W, WIN_H)
        self.win.set_decorated(False)
        self.win.set_resizable(False)
        self.win.add_css_class("nyxus-power")

        if HAS_CHROME:
            try: install_chrome(self.win, key="_powermenu")
            except Exception: pass

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        outer.set_margin_top(20); outer.set_margin_bottom(20)
        outer.set_margin_start(24); outer.set_margin_end(24)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        self.win.set_child(outer)

        title = Gtk.Label()
        title.set_markup(rainbow_markup("POWER · NYXUS"))
        title.add_css_class("nyxus-title")
        outer.append(title)

        sub = Gtk.Label(
            label="choose your exit · esc to cancel", xalign=0.5)
        sub.add_css_class("nyxus-sub")
        outer.append(sub)

        # 3-column grid of buttons
        grid = Gtk.Grid()
        grid.set_column_spacing(14); grid.set_row_spacing(14)
        grid.set_halign(Gtk.Align.CENTER)
        outer.append(grid)
        for i, (label, key, glyph, color, fn) in enumerate(ACTIONS):
            btn = Gtk.Button()
            btn.set_size_request(140, 90)
            btn.add_css_class("nyxus-pwrbtn")
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            g = Gtk.Label()
            g.set_markup(f"<span foreground='{color}' "
                         f"font_weight='bold' size='xx-large'>{glyph}</span>")
            inner.append(g)
            l = Gtk.Label()
            l.set_markup(f"<span foreground='{color}' "
                         f"font_weight='bold' size='large'>{label}</span>")
            inner.append(l)
            kl = Gtk.Label()
            kl.set_markup(f"<span foreground='#aaaaaa' size='small'>"
                          f"({key})</span>")
            inner.append(kl)
            btn.set_child(inner)
            btn.connect("clicked", lambda _b, f=fn: (f(), self.quit()))
            grid.attach(btn, i % 3, i // 3, 1, 1)

        # ── input ────────────────────────────────────────────────────
        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._on_key)
        kc.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.win.add_controller(kc)
        self.win.present()

    def _on_key(self, _ctl, keyval, _kc, _state):
        if keyval == Gdk.KEY_Escape:
            self.quit(); return True
        # letter shortcuts
        try:
            ch = chr(Gdk.keyval_to_unicode(keyval)).upper()
        except Exception:
            return False
        for label, key, glyph, color, fn in ACTIONS:
            if ch == key:
                fn(); self.quit(); return True
        return False


CSS = """
window.nyxus-power {
    background: rgba(8, 6, 14, 0.85);
    border-radius: 6px;
}
.nyxus-title {
    font-family: 'Caveat', sans-serif;
    font-size: 32px;
    text-shadow: 0 0 10px rgba(255, 0, 255, 0.5);
}
.nyxus-sub {
    font-family: 'Caveat', sans-serif;
    font-size: 16px;
    color: rgba(255, 255, 255, 0.55);
}
.nyxus-pwrbtn {
    background: rgba(15, 12, 24, 0.92);
    border: 2px solid rgba(255, 0, 255, 0.40);
    border-radius: 4px;
    color: #ffffff;
    font-family: 'Caveat', sans-serif;
    transition: all 0.12s ease;
}
.nyxus-pwrbtn:hover {
    background: rgba(255, 0, 255, 0.18);
    border-color: #e8edf5;
    box-shadow: 0 0 16px rgba(255, 0, 255, 0.55);
}
.nyxus-pwrbtn:active {
    background: rgba(255, 0, 255, 0.28);
    box-shadow: inset 0 0 10px rgba(255, 0, 255, 0.45);
}
"""


if __name__ == "__main__":
    sys.exit(PowerMenu().run(sys.argv))
