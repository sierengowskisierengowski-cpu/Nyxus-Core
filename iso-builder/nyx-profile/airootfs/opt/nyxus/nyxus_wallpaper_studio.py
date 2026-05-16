#!/usr/bin/env python3
"""NYXUS Wallpaper Studio — GTK4/libadwaita picker.

Lists wallpapers from /usr/share/backgrounds/nyxus/ (system pack) and
~/.local/share/backgrounds/nyxus/ (user pack), shows previews, and
applies the selected wallpaper via /usr/local/bin/nyxus-set-wallpaper.

The selected slug is persisted at ~/.config/nyxus/wallpaper.conf so it
survives reboot (sourced by the swaybg autostart wrapper).
"""
from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GdkPixbuf, Gio, GLib, Gtk  # noqa: E402

LOG_DIR = Path(os.path.expanduser("~/.cache/nyxus"))
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "wallpaper-studio.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("wallpaper-studio")

SYSTEM_DIR = Path("/usr/share/backgrounds/nyxus")
USER_DIR = Path(os.path.expanduser("~/.local/share/backgrounds/nyxus"))
CONFIG = Path(os.path.expanduser("~/.config/nyxus/wallpaper.conf"))
SETTER = "/usr/local/bin/nyxus-set-wallpaper"


def discover() -> list[tuple[str, str, Path]]:
    """Return [(slug, title, path), ...] from system + user dirs."""
    found: dict[str, tuple[str, Path]] = {}
    for base in (SYSTEM_DIR, USER_DIR):
        if not base.is_dir():
            continue
        manifest = base / "manifest.tsv"
        titles: dict[str, str] = {}
        if manifest.is_file():
            for line in manifest.read_text().splitlines():
                if "\t" in line:
                    s, t = line.split("\t", 1)
                    titles[s.strip()] = t.strip()
        for ext in ("svg", "png", "jpg", "jpeg", "webp"):
            for p in sorted(base.glob(f"*.{ext}")):
                slug = p.stem
                title = titles.get(slug, slug.replace("nyxus-", "").replace("-", " ").title())
                found[slug] = (title, p)
    return [(s, t, p) for s, (t, p) in sorted(found.items())]


def current_slug() -> str | None:
    if not CONFIG.is_file():
        return None
    for line in CONFIG.read_text().splitlines():
        line = line.strip()
        if line.startswith("WALLPAPER="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def apply_wallpaper(slug: str, path: Path) -> bool:
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    CONFIG.write_text(f'WALLPAPER="{slug}"\nWALLPAPER_PATH="{path}"\n')
    try:
        subprocess.run([SETTER, str(path)], check=True, timeout=10)
        log.info("applied %s -> %s", slug, path)
        return True
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as e:
        log.error("setter failed for %s: %s", slug, e)
        return False


class TileButton(Gtk.Button):
    def __init__(self, slug: str, title: str, path: Path, on_select):
        super().__init__()
        self.slug = slug
        self.path = path
        self.add_css_class("nyxus-wp-tile")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_margin_start(8); box.set_margin_end(8)
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), 320, 180, True)
            img = Gtk.Picture.new_for_pixbuf(pix)
            img.set_size_request(320, 180)
            img.add_css_class("nyxus-wp-preview")
        except GLib.Error as e:
            log.warning("preview failed for %s: %s", slug, e)
            img = Gtk.Label(label="(preview unavailable)")
            img.set_size_request(320, 180)
        box.append(img)
        lbl = Gtk.Label(label=title)
        lbl.add_css_class("nyxus-wp-title")
        box.append(lbl)
        self.set_child(box)
        self.connect("clicked", lambda *_: on_select(slug, path))


class WallpaperWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="NYXUS Wallpaper Studio")
        self.set_default_size(1100, 720)

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Wallpaper Studio"))
        toolbar.add_top_bar(header)

        self.toast = Adw.ToastOverlay()
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        flow = Gtk.FlowBox()
        flow.set_valign(Gtk.Align.START)
        flow.set_max_children_per_line(4)
        flow.set_min_children_per_line(2)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.set_margin_top(16); flow.set_margin_bottom(16)
        flow.set_margin_start(16); flow.set_margin_end(16)
        flow.set_row_spacing(12); flow.set_column_spacing(12)

        for slug, title, path in discover():
            flow.append(TileButton(slug, title, path, self.on_select))

        scroll.set_child(flow)
        self.toast.set_child(scroll)
        toolbar.set_content(self.toast)
        self.set_content(toolbar)

        cur = current_slug()
        if cur:
            self.toast.add_toast(Adw.Toast.new(f"Current: {cur}"))

    def on_select(self, slug: str, path: Path) -> None:
        if apply_wallpaper(slug, path):
            self.toast.add_toast(Adw.Toast.new(f"Applied: {slug}"))
        else:
            t = Adw.Toast.new(f"Failed to apply {slug} — see log")
            t.set_priority(Adw.ToastPriority.HIGH)
            self.toast.add_toast(t)


class WallpaperApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.nyxus.wallpaperstudio")
        self.set_resource_base_path(None)
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        sm = self.get_style_manager()
        sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            .nyxus-wp-tile {
              background: rgba(10, 13, 20, 0.85);
              border: 1px solid rgba(58, 216, 255, 0.18);
              border-radius: 14px;
              padding: 0;
            }
            .nyxus-wp-tile:hover {
              border-color: rgba(58, 216, 255, 0.55);
              background: rgba(15, 18, 28, 0.95);
            }
            .nyxus-wp-preview {
              border-radius: 10px;
            }
            .nyxus-wp-title {
              color: #e8edf5;
              font-weight: 600;
              letter-spacing: 0.04em;
              padding: 4px 0 8px 0;
            }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        win = WallpaperWindow(self)
        win.present()


def main(argv: list[str] | None = None) -> int:
    app = WallpaperApp()
    return app.run(argv or [])


if __name__ == "__main__":
    raise SystemExit(main())
