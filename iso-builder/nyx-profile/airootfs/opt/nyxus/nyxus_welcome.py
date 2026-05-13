#!/usr/bin/env python3
"""NYXUS first-run welcome tour.

A 5-page paged GTK4/libadwaita tour: Welcome → Hotkeys → Bar → Modes →
Done. Drops a sentinel at ~/.config/nyxus/welcome.done so it never auto
appears again. Re-launch via `nyxus welcome`.
"""
from __future__ import annotations

import os
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

SENTINEL = Path(os.path.expanduser("~/.config/nyxus/welcome.done"))

PAGES: list[tuple[str, str, str]] = [
    (
        "Welcome to NYXUS",
        "DARK MIRROR",
        "You are running the NYXUS desktop on Arch Linux.\n"
        "This short tour shows the essentials. You can re-open it any time\n"
        "by running:  nyxus welcome",
    ),
    (
        "Hotkeys",
        "Super = your launcher",
        "Super + Return  →  terminal\n"
        "Super + Space   →  app launcher\n"
        "Super + 1..0    →  switch to workspace 1..10\n"
        "Super + Q       →  close the focused window\n"
        "Super + Shift + W → screenshot a region",
    ),
    (
        "The Bar",
        "Top edge, always visible",
        "Click the workspace pill to jump.\n"
        "Click the right-side icons to open Quick Settings, Wifi, Bluetooth,\n"
        "Brightness, Sound, Calendar, and the Notification Center.\n"
        "The center marquee streams system + news + weather.",
    ),
    (
        "Game Mode & Focus Mode",
        "Two toggles for two moods",
        "Super + Alt + G  →  Game Mode (kills animations, allows tearing,\n"
        "                  CPU governor → performance, mutes notifications)\n"
        "Super + Alt + F  →  Focus Mode (hides bar, dims inactive windows,\n"
        "                  enables Do Not Disturb)",
    ),
    (
        "You're set",
        "Personalize, then explore",
        "Super + Alt + W   →  Wallpaper Studio\n"
        "Quick Settings    →  accent color, theme, account\n"
        "nyxus             →  list every NYXUS module from the terminal\n\n"
        "Have fun. Welcome to the dark side.",
    ),
]


class TourWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="NYXUS Welcome")
        self.set_default_size(720, 520)
        self.idx = 0

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="NYXUS · Welcome"))
        toolbar.add_top_bar(header)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        for i, (title, sub, body) in enumerate(PAGES):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=18)
            box.set_margin_top(48); box.set_margin_bottom(24)
            box.set_margin_start(48); box.set_margin_end(48)
            box.set_valign(Gtk.Align.CENTER)
            t = Gtk.Label(label=title); t.add_css_class("nyxus-tour-title"); t.set_xalign(0)
            s = Gtk.Label(label=sub);   s.add_css_class("nyxus-tour-sub");   s.set_xalign(0)
            b = Gtk.Label(label=body);  b.add_css_class("nyxus-tour-body");  b.set_xalign(0)
            b.set_wrap(True); b.set_selectable(True)
            box.append(t); box.append(s); box.append(b)
            self.stack.add_named(box, f"page{i}")

        nav = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        nav.set_margin_top(8); nav.set_margin_bottom(16)
        nav.set_margin_start(16); nav.set_margin_end(16)
        self.dots = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.dots.set_hexpand(True); self.dots.set_halign(Gtk.Align.CENTER)
        self.dot_widgets = []
        for _ in PAGES:
            d = Gtk.Label(label="●"); d.add_css_class("nyxus-tour-dot")
            self.dots.append(d); self.dot_widgets.append(d)
        self.back = Gtk.Button(label="Back");  self.back.connect("clicked", lambda *_: self.go(-1))
        self.next = Gtk.Button(label="Next");  self.next.add_css_class("suggested-action")
        self.next.connect("clicked", lambda *_: self.go(+1))
        nav.append(self.back); nav.append(self.dots); nav.append(self.next)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.append(self.stack); outer.append(nav)
        toolbar.set_content(outer)
        self.set_content(toolbar)
        self.refresh()

    def refresh(self) -> None:
        self.stack.set_visible_child_name(f"page{self.idx}")
        self.back.set_sensitive(self.idx > 0)
        self.next.set_label("Finish" if self.idx == len(PAGES) - 1 else "Next")
        for i, d in enumerate(self.dot_widgets):
            if i == self.idx:
                d.add_css_class("nyxus-tour-dot-active")
            else:
                d.remove_css_class("nyxus-tour-dot-active")

    def go(self, delta: int) -> None:
        new = self.idx + delta
        if new >= len(PAGES):
            SENTINEL.parent.mkdir(parents=True, exist_ok=True)
            SENTINEL.write_text("done\n")
            self.close()
            return
        if 0 <= new < len(PAGES):
            self.idx = new
            self.refresh()


class TourApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.nyxus.welcome")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.get_style_manager().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            .nyxus-tour-title { color:#e8edf5; font-size:30px; font-weight:800; letter-spacing:0.06em; }
            .nyxus-tour-sub   { color:#3ad8ff; font-size:14px; font-weight:600; letter-spacing:0.18em;
                                text-transform:uppercase; padding-bottom:12px; }
            .nyxus-tour-body  { color:#cfd6e2; font-size:15px; line-height:1.6; font-family:monospace; }
            .nyxus-tour-dot   { color:rgba(232,237,245,0.25); font-size:18px; }
            .nyxus-tour-dot-active { color:#3ad8ff; }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        TourWindow(self).present()


def main(argv=None) -> int:
    return TourApp().run(argv or [])


if __name__ == "__main__":
    raise SystemExit(main())
