#!/usr/bin/env python3
# ============================================================
#  NYXUS Notes — Tesla-tier minimal text editor
#  /opt/nyxus-notes/main.py
#
#  r1 · 2026.05.05
#
#  Philosophy: ONE textarea. Cream paper. Charcoal pencil.
#  No toolbar. No sidebar. No menus. No tags. No formatting.
#  Just write. Auto-saves to ~/.config/nyxus/notes/notes.txt
#  every keystroke (debounced 800ms).
#
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================

import sys
import os
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib

# ── Storage ────────────────────────────────────────────────────────────────
NOTES_DIR = Path.home() / ".config" / "nyxus" / "notes"
NOTES_FILE = NOTES_DIR / "notes.txt"
NOTES_DIR.mkdir(parents=True, exist_ok=True)

# ── Seattle Frost palette (CSS) ────────────────────────────────────────────
CSS = b"""
* {
    font-family: 'Inter', 'Cantarell', sans-serif;
}
window, .background {
    background-color: #f5f3ef;
    color: #1a1816;
}
headerbar {
    background-color: #f5f3ef;
    background-image: none;
    border: none;
    box-shadow: none;
    min-height: 38px;
    padding: 4px 12px;
}
headerbar .title {
    font-family: 'Architects Daughter', 'Caveat', cursive;
    font-size: 17px;
    color: #58524c;
    font-weight: 400;
    letter-spacing: 0.06em;
}
headerbar windowcontrols button {
    background: transparent;
    border: none;
    color: #58524c;
    box-shadow: none;
    min-width: 24px;
    min-height: 24px;
    margin: 0 2px;
}
headerbar windowcontrols button:hover {
    background-color: rgba(26, 24, 22, 0.06);
    border-radius: 6px;
}
headerbar windowcontrols button image {
    color: #58524c;
}
scrolledwindow, scrolledwindow viewport {
    background-color: #f5f3ef;
    border: none;
}
scrollbar {
    background: transparent;
    border: none;
    min-width: 6px;
    min-height: 6px;
}
scrollbar slider {
    background-color: rgba(26, 24, 22, 0.18);
    border-radius: 3px;
    min-width: 4px;
    min-height: 4px;
    margin: 2px;
}
scrollbar slider:hover {
    background-color: rgba(26, 24, 22, 0.32);
}
textview, textview text {
    background-color: #f5f3ef;
    color: #1a1816;
    font-family: 'Inter', 'Cantarell', sans-serif;
    font-size: 17px;
    caret-color: #58524c;
}
textview text selection {
    background-color: rgba(26, 24, 22, 0.16);
    color: #1a1816;
}
.statusrow {
    padding: 0 24px 12px 0;
    background: transparent;
}
.savedot {
    color: #9e948a;
    font-size: 11px;
    font-family: 'Inter', sans-serif;
    letter-spacing: 0.18em;
    font-weight: 400;
}
.savedot.dirty {
    color: #c97a2b;
}
"""


class NotesWindow(Gtk.ApplicationWindow):
    SAVE_DEBOUNCE_MS = 800

    def __init__(self, app: Gtk.Application):
        super().__init__(application=app, title="notes")
        self.set_default_size(720, 800)
        self._save_id = 0

        # ── CSS (one provider for the whole display) ─────────────────────
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # ── HeaderBar (minimal; just lowercase title + close button) ─────
        header = Gtk.HeaderBar()
        header.set_show_title_buttons(True)
        title = Gtk.Label(label="notes")
        title.add_css_class("title")
        header.set_title_widget(title)
        self.set_titlebar(header)

        # ── Body ─────────────────────────────────────────────────────────
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        root.set_vexpand(True)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hscrollbar_policy(Gtk.PolicyType.NEVER)
        scroll.set_vscrollbar_policy(Gtk.PolicyType.AUTOMATIC)

        self.buffer = Gtk.TextBuffer()
        self.text = Gtk.TextView(buffer=self.buffer)
        self.text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text.set_top_margin(60)
        self.text.set_bottom_margin(60)
        self.text.set_left_margin(80)
        self.text.set_right_margin(80)
        self.text.set_pixels_above_lines(3)
        self.text.set_pixels_below_lines(3)
        self.text.set_pixels_inside_wrap(3)
        self.text.set_accepts_tab(True)
        scroll.set_child(self.text)
        root.append(scroll)

        # ── Bottom-right "saved" dot (8px subtle) ────────────────────────
        statusrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        statusrow.set_halign(Gtk.Align.END)
        statusrow.add_css_class("statusrow")
        self.savedot = Gtk.Label(label="saved")
        self.savedot.add_css_class("savedot")
        statusrow.append(self.savedot)
        root.append(statusrow)

        self.set_child(root)

        # ── Load existing content & wire change handler ──────────────────
        self.load()
        self.buffer.connect("changed", self.on_changed)

        # ── Keyboard: Ctrl+S forces immediate save ───────────────────────
        ctrl = Gtk.ShortcutController()
        ctrl.add_shortcut(
            Gtk.Shortcut.new(
                Gtk.ShortcutTrigger.parse_string("<Control>s"),
                Gtk.CallbackAction.new(self._on_save_shortcut, None),
            )
        )
        self.add_controller(ctrl)

    # ─── persistence ───────────────────────────────────────────────────────
    def load(self):
        try:
            if NOTES_FILE.exists():
                text = NOTES_FILE.read_text(encoding="utf-8")
                self.buffer.set_text(text)
                # placing cursor at end keeps last write spot
                end = self.buffer.get_end_iter()
                self.buffer.place_cursor(end)
        except Exception as e:
            sys.stderr.write(f"[notes] load error: {e}\n")

    def on_changed(self, *_):
        self.savedot.set_text("•")
        self.savedot.add_css_class("dirty")
        if self._save_id:
            GLib.source_remove(self._save_id)
        self._save_id = GLib.timeout_add(self.SAVE_DEBOUNCE_MS, self._save_now)

    def _save_now(self) -> bool:
        self._save_id = 0
        self.save()
        return False  # one-shot timer

    def _on_save_shortcut(self, *_):
        self.save()
        return True

    def save(self):
        try:
            start, end = self.buffer.get_bounds()
            text = self.buffer.get_text(start, end, True)
            tmp = NOTES_FILE.with_suffix(".txt.tmp")
            tmp.write_text(text, encoding="utf-8")
            os.replace(tmp, NOTES_FILE)
            self.savedot.set_text("saved")
            self.savedot.remove_css_class("dirty")
        except Exception as e:
            sys.stderr.write(f"[notes] save error: {e}\n")
            self.savedot.set_text("save failed")
            self.savedot.add_css_class("dirty")


class NotesApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.nyxus.notes")
        self.win = None

    def do_activate(self):
        if self.win is None:
            self.win = NotesWindow(self)
        self.win.present()


def main():
    app = NotesApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
