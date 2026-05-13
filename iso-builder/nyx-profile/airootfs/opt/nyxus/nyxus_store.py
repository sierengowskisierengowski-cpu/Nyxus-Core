#!/usr/bin/env python3
"""NYXUS Store · curated app catalog browser + installer.

Reads ~/.config/nyxus/store-catalog.json (falls back to skel) and shows
categorized apps. Install button shells out to a wrapper script
(/usr/local/bin/nyxus-store-install) that picks pacman vs an AUR helper
(yay/paru) at runtime. The wrapper opens a terminal so the user sees
the password prompt + transaction summary.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gtk  # noqa: E402

USER_CAT = Path(os.path.expanduser("~/.config/nyxus/store-catalog.json"))
SKEL_CAT = Path("/etc/skel/.config/nyxus/store-catalog.json")
INSTALLER = "/usr/local/bin/nyxus-store-install"


def load_catalog() -> dict:
    for p in (USER_CAT, SKEL_CAT):
        if p.is_file():
            try:
                return json.loads(p.read_text())
            except json.JSONDecodeError:
                continue
    return {"categories": []}


class StoreWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="NYXUS Store")
        self.set_default_size(960, 680)
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="NYXUS Store"))
        toolbar.add_top_bar(header)

        self.split = Adw.NavigationSplitView()
        self.split.set_min_sidebar_width(200)
        self.split.set_max_sidebar_width(280)

        # Sidebar with categories
        side_page = Adw.NavigationPage(); side_page.set_title("Categories")
        self.cat_list = Gtk.ListBox(); self.cat_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.cat_list.add_css_class("nyxus-store-sidebar")
        side_scroll = Gtk.ScrolledWindow(); side_scroll.set_child(self.cat_list)
        side_page.set_child(side_scroll)
        self.split.set_sidebar(side_page)

        # Content
        content_page = Adw.NavigationPage(); content_page.set_title("Apps")
        self.app_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.app_box.set_margin_top(16); self.app_box.set_margin_bottom(16)
        self.app_box.set_margin_start(16); self.app_box.set_margin_end(16)
        c_scroll = Gtk.ScrolledWindow(); c_scroll.set_child(self.app_box)
        content_page.set_child(c_scroll)
        self.split.set_content(content_page)

        toolbar.set_content(self.split)
        self.toast = Adw.ToastOverlay(); self.toast.set_child(toolbar)
        self.set_content(self.toast)

        self.cat = load_catalog().get("categories", [])
        for c in self.cat:
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=c["name"]); lbl.set_xalign(0)
            lbl.set_margin_top(8); lbl.set_margin_bottom(8)
            lbl.set_margin_start(12); lbl.set_margin_end(12)
            lbl.add_css_class("nyxus-store-cat")
            row.set_child(lbl); self.cat_list.append(row)
        self.cat_list.connect("row-selected", self._on_cat)
        if self.cat:
            self.cat_list.select_row(self.cat_list.get_row_at_index(0))

    def _on_cat(self, _list, row):
        if row is None:
            return
        idx = row.get_index()
        if not (0 <= idx < len(self.cat)):
            return
        # GTK4: Box is not Python-iterable; walk the sibling chain.
        child = self.app_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.app_box.remove(child)
            child = nxt
        for app in self.cat[idx].get("apps", []):
            self.app_box.append(self._app_card(app))

    def _app_card(self, app: dict) -> Gtk.Widget:
        card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        card.add_css_class("nyxus-store-card")
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2); info.set_hexpand(True)
        name = Gtk.Label(label=app.get("name", app.get("id", "?")))
        name.add_css_class("nyxus-store-name"); name.set_xalign(0)
        sub = Gtk.Label(label=app.get("summary", "")); sub.add_css_class("nyxus-store-sub")
        sub.set_xalign(0); sub.set_wrap(True)
        meta = Gtk.Label(label=f"{app.get('source', '?')} · {' '.join(app.get('pkgs', []))}")
        meta.add_css_class("nyxus-store-meta"); meta.set_xalign(0)
        info.append(name); info.append(sub); info.append(meta)
        btn = Gtk.Button(label="Install"); btn.add_css_class("suggested-action")
        btn.connect("clicked", lambda *_: self._install(app))
        btn.set_valign(Gtk.Align.CENTER)
        card.append(info); card.append(btn)
        return card

    def _install(self, app: dict) -> None:
        if not shutil.which("nyxus-store-install"):
            self.toast.add_toast(Adw.Toast.new("nyxus-store-install missing"))
            return
        pkgs = app.get("pkgs", [])
        src = app.get("source", "pacman")
        try:
            subprocess.Popen([INSTALLER, src, *pkgs])
            self.toast.add_toast(Adw.Toast.new(f"Launching install: {app.get('name')}"))
        except Exception as e:
            t = Adw.Toast.new(f"Install failed: {e}"); t.set_priority(Adw.ToastPriority.HIGH)
            self.toast.add_toast(t)


class StoreApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.nyxus.store")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.get_style_manager().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            .nyxus-store-cat  { color:#cfd6e2; font-weight:600; }
            .nyxus-store-card { background:rgba(10,13,20,0.85); border:1px solid rgba(58,216,255,0.18);
                                border-radius:12px; padding:12px; }
            .nyxus-store-name { color:#e8edf5; font-weight:700; font-size:14px; }
            .nyxus-store-sub  { color:#cfd6e2; font-size:12px; }
            .nyxus-store-meta { color:#7e8794; font-size:11px; font-family:monospace; padding-top:4px; }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        StoreWindow(self).present()


def main(argv=None) -> int:
    return StoreApp().run(argv or [])


if __name__ == "__main__":
    raise SystemExit(main())
