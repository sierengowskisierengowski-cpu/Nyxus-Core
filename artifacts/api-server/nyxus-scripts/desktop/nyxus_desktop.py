#!/usr/bin/env python3
"""
NYXUS Desktop — interactive layer-shell desktop client.

Replaces swaybg. Paints the wallpaper itself per-monitor at the `bottom`
layer-shell layer (under bars, under all windows). Catches mouse events
on the wallpaper and dispatches to nyxus-context-menu.sh.

Turn 1 scope (this file): wallpaper paint + click dispatch + multi-monitor
+ hot-plug + IPC socket hook for live wallpaper hot-swap. No icons yet
(those land in T2).

Config:  ~/.config/nyxus/desktop.toml  (wallpaper, fit, bg_color)
State:   ~/.config/nyxus/desktop-icons.json  (used by T2)
Log:     ~/.cache/nyxus/desktop.log
IPC:     $XDG_RUNTIME_DIR/nyxus-desktop.sock  (line protocol)
"""
from __future__ import annotations

import hashlib
import json
import logging
import logging.handlers
import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional
from urllib.parse import unquote, urlparse

import gi

# --- hard-required deps -----------------------------------------------------
try:
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402
except Exception as _gtk_err:
    sys.stderr.write(f"nyxus_desktop: GTK4 unavailable ({_gtk_err}); "
                     "falling back to swaybg.\n")
    os.execvp("swaybg", [
        "swaybg", "-i",
        os.path.expanduser(
            "~/.config/hypr/walls/nyxus-void-vortex.png"),
        "-m", "fill", "-c", "#000000",
    ])

# --- soft-required: gtk4-layer-shell (no shell layer = no desktop) ---------
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402
except Exception as _ls_err:
    sys.stderr.write(f"nyxus_desktop: gtk4-layer-shell unavailable "
                     f"({_ls_err}); falling back to swaybg.\n")
    os.execvp("swaybg", [
        "swaybg", "-i",
        os.path.expanduser(
            "~/.config/hypr/walls/nyxus-void-vortex.png"),
        "-m", "fill", "-c", "#000000",
    ])

# ---------- paths ----------
HOME = Path(os.path.expanduser("~"))
CFG_DIR = HOME / ".config" / "nyxus"
CACHE_DIR = HOME / ".cache" / "nyxus"
CFG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CFG_FILE = CFG_DIR / "desktop.toml"
LOG_FILE = CACHE_DIR / "desktop.log"
SOCK_PATH = Path(
    os.environ.get("XDG_RUNTIME_DIR", "/tmp")
) / "nyxus-desktop.sock"

DEFAULT_WALL = HOME / ".config" / "hypr" / "walls" / "nyxus-void-vortex.png"
DEFAULT_BG = "#080a10"
CONTEXT_MENU = "nyxus-context-menu.sh"
THUMB_DIR = HOME / ".cache" / "thumbnails" / "normal"
THUMB_DIR.mkdir(parents=True, exist_ok=True)
THUMB_SIZE = 128
IMAGE_MIMES = {"image/png", "image/jpeg", "image/jpg", "image/webp",
               "image/gif", "image/bmp", "image/tiff"}

# ---------- logging ----------
log = logging.getLogger("nyxus_desktop")
log.setLevel(logging.INFO)
_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=512_000, backupCount=3
)
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s")
)
log.addHandler(_handler)


# ---------- config ----------
def load_config() -> dict:
    """Return wallpaper config. TOML if available, else defaults."""
    cfg = {
        "wallpaper": str(DEFAULT_WALL),
        "fit": "fill",
        "bg_color": DEFAULT_BG,
    }
    if CFG_FILE.exists():
        try:
            import tomllib  # py 3.11+
            with CFG_FILE.open("rb") as f:
                data = tomllib.load(f)
            cfg.update({k: v for k, v in data.items() if k in cfg})
        except Exception as e:
            log.warning("config parse failed: %s", e)
    # resolve ~ in wallpaper
    cfg["wallpaper"] = os.path.expanduser(cfg["wallpaper"])
    return cfg


def save_config(cfg: dict) -> None:
    lines = [
        f'wallpaper = "{cfg["wallpaper"]}"',
        f'fit = "{cfg["fit"]}"',
        f'bg_color = "{cfg["bg_color"]}"',
    ]
    CFG_FILE.write_text("\n".join(lines) + "\n")


# ---------- thumbnail (XDG spec) ----------
def thumbnail_for(path: Path, mime: Optional[str]) -> Optional[Path]:
    """Return a cached thumbnail PNG path per XDG thumbnail spec, or None.

    Spec: ~/.cache/thumbnails/normal/<md5(file://uri)>.png  (128px max).
    Generates on demand for image MIMEs only (non-blocking from caller's
    perspective — caller decides when to invoke).
    """
    if not mime or mime not in IMAGE_MIMES:
        return None
    try:
        uri = "file://" + str(path.resolve())
        digest = hashlib.md5(uri.encode("utf-8")).hexdigest()
        thumb = THUMB_DIR / f"{digest}.png"
        # validate cache: regen if missing or older than source
        try:
            src_mtime = path.stat().st_mtime
        except OSError:
            return None
        if thumb.exists() and thumb.stat().st_mtime >= src_mtime:
            return thumb
        # generate via GdkPixbuf
        try:
            from gi.repository import GdkPixbuf
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                str(path), THUMB_SIZE, THUMB_SIZE, True)
            pb.savev(str(thumb), "png",
                     ["tEXt::Thumb::URI", "tEXt::Thumb::MTime"],
                     [uri, str(int(src_mtime))])
            return thumb
        except Exception as e:
            log.debug("thumbnail gen failed for %s: %s", path, e)
            return None
    except Exception:
        return None


def uris_to_paths(uri_list: str) -> list[Path]:
    """Parse text/uri-list payload into local Paths, dropping non-file URIs."""
    out: list[Path] = []
    for line in uri_list.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            parsed = urlparse(line)
            if parsed.scheme == "file":
                out.append(Path(unquote(parsed.path)))
        except Exception:
            continue
    return out


# ---------- icon model ----------
ICON_W = 96
ICON_H = 96
ICON_PAD_X = 24
ICON_PAD_Y = 28
ICON_GRID_W = ICON_W + ICON_PAD_X
ICON_GRID_H = ICON_H + ICON_PAD_Y
DESKTOP_DIR = HOME / "Desktop"
ICON_STATE_FILE = CFG_DIR / "desktop-icons.json"


class DesktopEntry:
    """One thing on the desktop: file, folder, .desktop launcher, or symlink.

    Resolves: display name, icon name (XDG icon-theme lookup), launch command.
    """

    __slots__ = ("path", "name", "is_dir", "is_launcher",
                 "app_info", "icon_name", "mime")

    def __init__(self, path: Path) -> None:
        self.path = path
        self.is_launcher = path.suffix == ".desktop" and path.is_file()
        self.is_dir = path.is_dir()
        self.name = path.name
        self.app_info: Optional[Gio.DesktopAppInfo] = None
        self.icon_name = "text-x-generic"
        self.mime: Optional[str] = None
        self._resolve()

    def _resolve(self) -> None:
        if self.is_launcher:
            self._parse_desktop_file()
            return
        if self.is_dir:
            self.icon_name = "folder"
            return
        # regular file: query MIME + icon via Gio
        try:
            gfile = Gio.File.new_for_path(str(self.path))
            info = gfile.query_info(
                "standard::display-name,standard::icon,standard::content-type",
                Gio.FileQueryInfoFlags.NONE,
                None,
            )
            disp = info.get_display_name()
            if disp:
                self.name = disp
            self.mime = info.get_content_type()
            gicon = info.get_icon()
            if isinstance(gicon, Gio.ThemedIcon):
                names = gicon.get_names()
                if names:
                    self.icon_name = names[0]
        except Exception as e:
            log.debug("MIME query failed for %s: %s", self.path, e)

    def _parse_desktop_file(self) -> None:
        # Use Gio.DesktopAppInfo — handles Type/Terminal/TryExec/Exec field
        # codes correctly and never shell-evals the Exec line.
        try:
            self.app_info = Gio.DesktopAppInfo.new_from_filename(
                str(self.path))
        except Exception as e:
            log.warning("DesktopAppInfo build failed for %s: %s",
                        self.path, e)
            self.app_info = None
        if self.app_info is not None:
            n = self.app_info.get_display_name() or self.app_info.get_name()
            if n:
                self.name = n
            icon = self.app_info.get_icon()
            if isinstance(icon, Gio.ThemedIcon):
                names = icon.get_names()
                if names:
                    self.icon_name = names[0]
            elif icon is not None:
                # FileIcon or other → use string repr as icon name fallback
                try:
                    self.icon_name = icon.to_string() or self.icon_name
                except Exception:
                    pass

    def launch(self) -> None:
        try:
            # .desktop files: launch via the parsed AppInfo (no shell)
            if self.is_launcher and self.app_info is not None:
                ctx = Gio.AppLaunchContext()
                self.app_info.launch([], ctx)
                return
            # everything else: hand to xdg-open (respects MIME defaults)
            subprocess.Popen(["xdg-open", str(self.path)],
                             start_new_session=True)
        except Exception as e:
            log.error("launch failed for %s: %s", self.path, e)


class IconWidget(Gtk.Box):
    """A single desktop icon: image + label, selectable, draggable, renameable."""

    def __init__(
        self,
        entry: DesktopEntry,
        on_open,        # callable(entry)
        on_select,      # callable(IconWidget, additive)
        on_context,     # callable(entry)
        on_drag_begin,  # callable() -> list[IconWidget] to include in drag
        on_drag_end,    # callable(IconWidget)
        on_rename,      # callable(IconWidget, new_name)
    ) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.entry = entry
        self._on_open = on_open
        self._on_select = on_select
        self._on_context = on_context
        self._on_drag_begin = on_drag_begin
        self._on_drag_end = on_drag_end
        self._on_rename = on_rename
        self._selected = False
        self._renaming = False

        self.set_size_request(ICON_W, ICON_H)
        self.add_css_class("nyxus-desktop-icon")
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.START)
        self.set_focusable(True)

        # icon image — thumbnail if available, else themed icon
        self.image = Gtk.Image()
        self.image.set_pixel_size(56)
        self.image.set_halign(Gtk.Align.CENTER)
        thumb = thumbnail_for(entry.path, entry.mime)
        if thumb is not None:
            try:
                self.image.set_from_file(str(thumb))
            except Exception:
                self.image.set_from_icon_name(entry.icon_name)
        else:
            self.image.set_from_icon_name(entry.icon_name)
        self.append(self.image)

        # label (swapped with Entry on rename)
        self.label_box = Gtk.Box()
        self.label_box.set_halign(Gtk.Align.CENTER)
        self.label = Gtk.Label(label=entry.name)
        self.label.set_max_width_chars(12)
        self.label.set_wrap(True)
        self.label.set_wrap_mode(2)
        self.label.set_lines(2)
        self.label.set_ellipsize(3)
        self.label.set_justify(Gtk.Justification.CENTER)
        self.label.set_halign(Gtk.Align.CENTER)
        self.label.add_css_class("nyxus-desktop-icon-label")
        self.label_box.append(self.label)
        self.append(self.label_box)

        # click gesture
        click = Gtk.GestureClick()
        click.set_button(0)
        click.connect("pressed", self._on_press)
        self.add_controller(click)

        # drag source — produces text/uri-list for external drops
        # (file managers, mail composers, etc.)
        drag = Gtk.DragSource()
        drag.set_actions(Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        drag.connect("prepare", self._on_drag_prepare)
        drag.connect("drag-begin", self._on_drag_begin_evt)
        drag.connect("drag-end", self._on_drag_end_evt)
        self.add_controller(drag)

    # -- click --
    def _on_press(self, gesture: Gtk.GestureClick, n: int,
                  x: float, y: float) -> None:
        if self._renaming:
            return
        gesture.set_state(Gtk.EventSequenceState.CLAIMED)
        button = gesture.get_current_button()
        event = gesture.get_last_event(None)
        modifiers = event.get_modifier_state() if event else 0
        additive = bool(modifiers & (Gdk.ModifierType.CONTROL_MASK
                                     | Gdk.ModifierType.SHIFT_MASK))
        self.grab_focus()
        if button == Gdk.BUTTON_SECONDARY:
            if not self._selected:
                self._on_select(self, False)
            self._on_context(self.entry)
            return
        if button == Gdk.BUTTON_PRIMARY:
            if n >= 2:
                self._on_open(self.entry)
            else:
                self._on_select(self, additive)

    # -- drag source --
    def _on_drag_prepare(self, src: Gtk.DragSource, x: float, y: float):
        # If this icon isn't selected, select it exclusively first.
        if not self._selected:
            self._on_select(self, False)
        # Build URI list for all currently selected icons.
        try:
            members = self._on_drag_begin() or [self]
        except Exception:
            members = [self]
        uris = "\r\n".join(
            "file://" + str(m.entry.path.resolve()) for m in members
        ) + "\r\n"
        return Gdk.ContentProvider.new_for_bytes(
            "text/uri-list", GLib.Bytes.new(uris.encode("utf-8")))

    def _on_drag_begin_evt(self, src: Gtk.DragSource,
                           drag: Gdk.Drag) -> None:
        # Visual: icon pixbuf as drag image (best-effort)
        try:
            paintable = Gtk.WidgetPaintable.new(self.image)
            src.set_icon(paintable, 28, 28)
        except Exception:
            pass
        self.add_css_class("dragging")

    def _on_drag_end_evt(self, src: Gtk.DragSource,
                        drag: Gdk.Drag, deleted: bool) -> None:
        self.remove_css_class("dragging")
        self._on_drag_end(self)

    # -- selection state --
    def set_selected(self, val: bool) -> None:
        if val == self._selected:
            return
        self._selected = val
        if val:
            self.add_css_class("selected")
        else:
            self.remove_css_class("selected")

    @property
    def is_selected(self) -> bool:
        return self._selected

    # -- inline rename --
    def begin_rename(self) -> None:
        if self._renaming:
            return
        self._renaming = True
        self.label_box.remove(self.label)
        self._entry = Gtk.Entry()
        self._entry.set_text(self.entry.name)
        self._entry.set_max_width_chars(12)
        self._entry.set_halign(Gtk.Align.CENTER)
        self._entry.add_css_class("nyxus-desktop-icon-rename")
        self._entry.connect("activate", self._commit_rename)
        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self._on_rename_key)
        self._entry.add_controller(key)
        # commit on focus loss too
        focus = Gtk.EventControllerFocus()
        focus.connect("leave", lambda *_: self._commit_rename(self._entry))
        self._entry.add_controller(focus)
        self.label_box.append(self._entry)
        self._entry.grab_focus()
        # select stem (no extension) for fast typing
        name = self.entry.name
        dot = name.rfind(".")
        if 0 < dot < len(name) - 1 and not self.entry.is_dir:
            self._entry.select_region(0, dot)
        else:
            self._entry.select_region(0, -1)

    def _on_rename_key(self, ctrl, keyval, keycode, state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self._cancel_rename()
            return True
        return False

    def _cancel_rename(self) -> None:
        if not self._renaming:
            return
        self._renaming = False
        try:
            self.label_box.remove(self._entry)
        except Exception:
            pass
        self.label_box.append(self.label)

    def _commit_rename(self, entry: Gtk.Entry) -> None:
        if not self._renaming:
            return
        new = entry.get_text().strip()
        self._cancel_rename()
        if not new or new == self.entry.name:
            return
        self._on_rename(self, new)


# ---------- desktop window per monitor ----------
class DesktopSurface(Gtk.ApplicationWindow):
    """One layer-shell window per monitor."""

    def __init__(
        self,
        app: Gtk.Application,
        monitor: Gdk.Monitor,
        cfg: dict,
    ) -> None:
        super().__init__(application=app)
        self.monitor = monitor
        self.cfg = cfg
        self.icons: list[IconWidget] = []
        self._build_layer()
        self._build_content()
        self._build_input()
        # icons (filesystem watch is owned by DesktopApp, not per-window)
        DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
        self._populate_icons()
        # ensure we tear down cleanly on close (hot-unplug etc.)
        self.connect("close-request", self._on_close)

    def _on_close(self, *_: object) -> bool:
        for ico in self.icons:
            try:
                self.icon_layer.remove(ico)
            except Exception:
                pass
        self.icons.clear()
        return False

    # -- layer-shell config --
    def _build_layer(self) -> None:
        LayerShell.init_for_window(self)
        LayerShell.set_layer(self, LayerShell.Layer.BOTTOM)
        LayerShell.set_monitor(self, self.monitor)
        for edge in (
            LayerShell.Edge.TOP,
            LayerShell.Edge.BOTTOM,
            LayerShell.Edge.LEFT,
            LayerShell.Edge.RIGHT,
        ):
            LayerShell.set_anchor(self, edge, True)
        # do not push other layers around
        LayerShell.set_exclusive_zone(self, -1)
        LayerShell.set_namespace(self, "nyxus-desktop")
        # ON_DEMAND lets keyboard work for icon nav + inline rename
        # without ever stealing focus from real app windows.
        LayerShell.set_keyboard_mode(self, LayerShell.KeyboardMode.ON_DEMAND)

    # -- content (wallpaper + future icon layer) --
    def _build_content(self) -> None:
        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        # background fill (always covers, even before image loads)
        bg = Gtk.Box()
        bg.add_css_class("nyxus-desktop-bg")
        self.overlay.set_child(bg)

        # wallpaper picture
        self.picture = Gtk.Picture()
        self.picture.set_can_shrink(True)
        self.picture.set_keep_aspect_ratio(False)  # fit=fill
        self._apply_wallpaper(self.cfg.get("wallpaper", ""))
        self.overlay.add_overlay(self.picture)

        # icon layer (populated in T2). Transparent, swallows nothing.
        self.icon_layer = Gtk.Fixed()
        self.icon_layer.add_css_class("nyxus-desktop-icons")
        self.overlay.add_overlay(self.icon_layer)

    def _apply_wallpaper(self, path: str) -> None:
        p = Path(os.path.expanduser(path or ""))
        if not p.exists():
            log.warning("wallpaper missing: %s", p)
            return
        try:
            self.picture.set_filename(str(p))
            log.info("wallpaper applied on %s: %s",
                     self.monitor.get_connector(), p.name)
        except Exception as e:
            log.error("set wallpaper failed: %s", e)

    # -- input: right/left click on bare desktop, rubber-band, keyboard --
    def _build_input(self) -> None:
        # right-click + bare-area left-click → menu / dismiss
        click = Gtk.GestureClick()
        click.set_button(0)
        click.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        click.connect("pressed", self._on_click)
        self.overlay.add_controller(click)

        # left-button drag on bare desktop → rubber-band selection rect
        self._rb_active = False
        self._rb_start = (0.0, 0.0)
        self._rb_box: Optional[Gtk.Box] = None
        drag = Gtk.GestureDrag()
        drag.set_button(Gdk.BUTTON_PRIMARY)
        drag.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        drag.connect("drag-begin", self._rb_begin)
        drag.connect("drag-update", self._rb_update)
        drag.connect("drag-end", self._rb_end)
        self.overlay.add_controller(drag)

        # keyboard navigation across icons
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

        # drop target on icon_layer — accepts files dragged from
        # external apps (browser, file manager, mail).
        drop = Gtk.DropTarget.new(GLib.Bytes.__gtype__,
                                  Gdk.DragAction.COPY | Gdk.DragAction.MOVE)
        drop.set_gtypes([Gdk.FileList.__gtype__,
                         GLib.Bytes.__gtype__, str])
        drop.connect("drop", self._on_drop)
        self.icon_layer.add_controller(drop)

    def _hit_is_icon(self, x: float, y: float) -> bool:
        """True if (x,y) lands inside an icon widget on the icon layer."""
        try:
            target = self.overlay.pick(x, y, Gtk.PickFlags.DEFAULT)
        except Exception:
            return False
        w = target
        while w is not None:
            if w is self.icon_layer:
                # bare icon_layer (no child) = bare desktop, treat as bg
                return target is not self.icon_layer
            w = w.get_parent()
        return False

    def _on_click(self, gesture: Gtk.GestureClick, n: int,
                  x: float, y: float) -> None:
        if self._hit_is_icon(x, y):
            return  # icon handler owns it
        button = gesture.get_current_button()
        if button == Gdk.BUTTON_SECONDARY:
            self._spawn_menu("main")
        elif button == Gdk.BUTTON_PRIMARY:
            # Bare-area left-click clears selection; menus dismissed via Esc
            # or by clicking outside. Don't fire dismiss every press — that
            # made T3 rubber-band feel wrong.
            self._clear_selection()

    # -- rubber-band selection --
    def _rb_begin(self, gesture: Gtk.GestureDrag, x: float, y: float) -> None:
        if self._hit_is_icon(x, y):
            # let icon's drag source own this gesture
            gesture.set_state(Gtk.EventSequenceState.DENIED)
            return
        self._rb_active = True
        self._rb_start = (x, y)
        # additive only if Ctrl/Shift held
        event = gesture.get_last_event(None)
        mods = event.get_modifier_state() if event else 0
        if not (mods & (Gdk.ModifierType.CONTROL_MASK
                        | Gdk.ModifierType.SHIFT_MASK)):
            self._clear_selection()
        # spawn marquee
        self._rb_box = Gtk.Box()
        self._rb_box.add_css_class("nyxus-desktop-marquee")
        self._rb_box.set_can_target(False)
        self.icon_layer.put(self._rb_box, int(x), int(y))
        self._rb_box.set_size_request(1, 1)

    def _rb_update(self, gesture: Gtk.GestureDrag,
                   ox: float, oy: float) -> None:
        if not self._rb_active or self._rb_box is None:
            return
        sx, sy = self._rb_start
        x = int(min(sx, sx + ox))
        y = int(min(sy, sy + oy))
        w = int(max(1, abs(ox)))
        h = int(max(1, abs(oy)))
        self.icon_layer.move(self._rb_box, x, y)
        self._rb_box.set_size_request(w, h)
        # live-select icons inside the rect
        for ico in self.icons:
            ix, iy = self._icon_position(ico)
            inside = (ix + ICON_W >= x and ix <= x + w
                      and iy + ICON_H >= y and iy <= y + h)
            ico.set_selected(inside)

    def _rb_end(self, gesture: Gtk.GestureDrag,
                ox: float, oy: float) -> None:
        if self._rb_box is not None:
            try:
                self.icon_layer.remove(self._rb_box)
            except Exception:
                pass
            self._rb_box = None
        self._rb_active = False

    def _icon_position(self, ico: IconWidget) -> tuple[int, int]:
        try:
            child = self.icon_layer.get_first_child()
            while child is not None:
                if child is ico:
                    # Gtk.Fixed exposes per-child x/y via a ChildIter or
                    # we re-read from the layout-manager; simplest: track
                    # via stored attribute we set in _populate_icons / move.
                    break
                child = child.get_next_sibling()
        except Exception:
            pass
        return getattr(ico, "_pos", (0, 0))

    # -- keyboard nav --
    def _on_key(self, ctrl, keyval: int, keycode: int,
                state: Gdk.ModifierType) -> bool:
        if not self.icons:
            return False
        # Ctrl+A → select all
        if (state & Gdk.ModifierType.CONTROL_MASK) and keyval in (
                Gdk.KEY_a, Gdk.KEY_A):
            for ico in self.icons:
                ico.set_selected(True)
            return True
        sel = [i for i in self.icons if i.is_selected]
        if keyval == Gdk.KEY_Escape:
            self._clear_selection()
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            for ico in sel:
                self._open_entry(ico.entry)
            return True
        if keyval == Gdk.KEY_F2 and len(sel) == 1:
            sel[0].begin_rename()
            return True
        if keyval == Gdk.KEY_Delete and sel:
            for ico in sel:
                self._trash_path(ico.entry.path)
            return True
        # arrow keys: move selection to spatial neighbor
        if keyval in (Gdk.KEY_Left, Gdk.KEY_Right,
                      Gdk.KEY_Up, Gdk.KEY_Down):
            self._move_selection(keyval, sel)
            return True
        return False

    def _move_selection(self, keyval: int,
                        sel: list[IconWidget]) -> None:
        if not sel:
            sel = [self.icons[0]]
        anchor = sel[-1]
        ax, ay = self._icon_position(anchor)
        best: Optional[IconWidget] = None
        best_d = float("inf")
        for ico in self.icons:
            if ico is anchor:
                continue
            ix, iy = self._icon_position(ico)
            dx, dy = ix - ax, iy - ay
            ok = False
            if keyval == Gdk.KEY_Left and dx < 0 and abs(dy) <= ICON_GRID_H / 2:
                ok = True
            elif keyval == Gdk.KEY_Right and dx > 0 and abs(dy) <= ICON_GRID_H / 2:
                ok = True
            elif keyval == Gdk.KEY_Up and dy < 0 and abs(dx) <= ICON_GRID_W / 2:
                ok = True
            elif keyval == Gdk.KEY_Down and dy > 0 and abs(dx) <= ICON_GRID_W / 2:
                ok = True
            if ok:
                d = dx * dx + dy * dy
                if d < best_d:
                    best, best_d = ico, d
        if best is not None:
            self._on_icon_select(best, additive=False)
            best.grab_focus()

    # -- drop target on icon_layer (external drops) --
    def _on_drop(self, target: Gtk.DropTarget, value, x: float, y: float):
        paths: list[Path] = []
        if isinstance(value, Gdk.FileList):
            for f in value.get_files():
                p = f.get_path()
                if p:
                    paths.append(Path(p))
        elif isinstance(value, GLib.Bytes):
            try:
                txt = value.get_data().decode("utf-8", "ignore")
                paths = uris_to_paths(txt)
            except Exception:
                paths = []
        elif isinstance(value, str):
            paths = uris_to_paths(value)
        if not paths:
            return False
        for src in paths:
            try:
                if src.parent == DESKTOP_DIR:
                    continue  # internal move handled elsewhere
                dest = DESKTOP_DIR / src.name
                if dest.exists():
                    dest = DESKTOP_DIR / f"{src.stem} (copy){src.suffix}"
                if src.is_dir():
                    shutil.copytree(src, dest)
                else:
                    shutil.copy2(src, dest)
            except Exception as e:
                log.warning("drop copy failed %s → %s: %s", src, DESKTOP_DIR, e)
        return True

    def _clear_selection(self) -> None:
        for ico in self.icons:
            ico.set_selected(False)

    def _trash_path(self, path: Path) -> None:
        try:
            subprocess.run(["gio", "trash", "--", str(path)],
                           check=False)
        except Exception as e:
            log.error("trash failed: %s", e)

    def _spawn_menu(self, mode: str, *args: str) -> None:
        try:
            subprocess.Popen(
                [CONTEXT_MENU, mode, *args],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError:
            log.error("context menu script not on PATH: %s", CONTEXT_MENU)
        except Exception as e:
            log.error("menu spawn failed: %s", e)

    # -- public: hot-swap wallpaper --
    def set_wallpaper(self, path: str) -> None:
        self.cfg["wallpaper"] = path
        self._apply_wallpaper(path)

    # ============ icons ============
    def _load_positions(self) -> dict:
        if not ICON_STATE_FILE.exists():
            return {}
        try:
            data = json.loads(ICON_STATE_FILE.read_text())
            return data.get("positions", {})
        except Exception as e:
            log.warning("icon state read failed: %s", e)
            return {}

    def _save_positions(self, positions: dict) -> None:
        try:
            existing = {}
            if ICON_STATE_FILE.exists():
                existing = json.loads(ICON_STATE_FILE.read_text())
            existing["positions"] = positions
            ICON_STATE_FILE.write_text(json.dumps(existing, indent=2))
        except Exception as e:
            log.warning("icon state write failed: %s", e)

    def _populate_icons(self) -> None:
        # tear down previous icons
        for ico in self.icons:
            self.icon_layer.remove(ico)
        self.icons.clear()

        positions = self._load_positions()
        # auto-grid: row-major then column-wrap, leaving margin for top bar
        grid_x = 16
        grid_y = 48
        margin_right = 16
        margin_bottom = 16
        try:
            geom = self.monitor.get_geometry()
            max_rows = max(1,
                (geom.height - grid_y - margin_bottom) // ICON_GRID_H)
            max_cols = max(1,
                (geom.width - grid_x - margin_right) // ICON_GRID_W)
        except Exception:
            max_rows, max_cols = 8, 12

        try:
            entries = sorted(
                [p for p in DESKTOP_DIR.iterdir()
                 if not p.name.startswith(".")],
                key=lambda p: (not p.is_dir(), p.name.lower()),
            )
        except Exception as e:
            log.error("scan ~/Desktop failed: %s", e)
            entries = []

        col = 0
        row = 0
        for path in entries:
            try:
                entry = DesktopEntry(path)
            except Exception as e:
                log.warning("entry build failed for %s: %s", path, e)
                continue
            ico = IconWidget(
                entry,
                on_open=self._open_entry,
                on_select=self._on_icon_select,
                on_context=self._on_icon_context,
                on_drag_begin=self._collect_selected_for_drag,
                on_drag_end=self._on_icon_drag_end,
                on_rename=self._on_icon_rename,
            )
            saved = positions.get(str(path))
            if saved and isinstance(saved, list) and len(saved) == 2:
                x, y = int(saved[0]), int(saved[1])
            else:
                # column-major: fill column top→bottom, then next column
                x = grid_x + col * ICON_GRID_W
                y = grid_y + row * ICON_GRID_H
                row += 1
                if row >= max_rows:
                    row = 0
                    col += 1
                    if col >= max_cols:
                        # overflow: stack remaining at last cell — caller
                        # can scroll/sort; we never paint off-screen
                        col = max_cols - 1
                        row = max_rows - 1
            self.icon_layer.put(ico, x, y)
            ico._pos = (x, y)
            self.icons.append(ico)
        log.info("populated %d icons on %s (grid=%dx%d)",
                 len(self.icons), self.monitor.get_connector(),
                 max_cols, max_rows)

    def refresh_icons(self) -> None:
        """Public hook called by DesktopApp when ~/Desktop changes."""
        self._populate_icons()

    def _open_entry(self, entry: DesktopEntry) -> None:
        entry.launch()

    def _on_icon_select(self, ico: IconWidget, additive: bool) -> None:
        if not additive:
            for other in self.icons:
                other.set_selected(other is ico)
        else:
            ico.set_selected(not ico._selected)

    def _on_icon_context(self, entry: DesktopEntry) -> None:
        self._spawn_menu("icon", str(entry.path))

    def _collect_selected_for_drag(self) -> list[IconWidget]:
        sel = [i for i in self.icons if i.is_selected]
        return sel if sel else []

    def _snap_enabled(self) -> bool:
        try:
            if not ICON_STATE_FILE.exists():
                return False
            data = json.loads(ICON_STATE_FILE.read_text())
            return data.get("snap_to_grid", False) is True
        except Exception:
            return False

    def _snap(self, x: int, y: int) -> tuple[int, int]:
        if not self._snap_enabled():
            return x, y
        gx = 16
        gy = 48
        col = round((x - gx) / ICON_GRID_W)
        row = round((y - gy) / ICON_GRID_H)
        return gx + col * ICON_GRID_W, gy + row * ICON_GRID_H

    def _on_icon_drag_end(self, ico: IconWidget) -> None:
        # When an icon was dragged but landed back on the desktop (no other
        # drop target consumed it), persist its new position. We use the
        # pointer position via Gdk.Display.get_pointer().
        try:
            display = Gdk.Display.get_default()
            seat = display.get_default_seat()
            pointer = seat.get_pointer()
            surface = self.get_surface()
            if surface is None:
                return
            ok, px, py, _ = surface.get_device_position(pointer)
            if not ok:
                return
            x, y = self._snap(int(px - ICON_W // 2), int(py - ICON_H // 2))
            x = max(0, min(x, self.monitor.get_geometry().width - ICON_W))
            y = max(0, min(y, self.monitor.get_geometry().height - ICON_H))
            self.icon_layer.move(ico, x, y)
            ico._pos = (x, y)
            self._persist_position(ico.entry.path, x, y)
        except Exception as e:
            log.debug("drag end position save failed: %s", e)

    def _persist_position(self, path: Path, x: int, y: int) -> None:
        positions = self._load_positions()
        positions[str(path)] = [x, y]
        self._save_positions(positions)

    def _on_icon_rename(self, ico: IconWidget, new_name: str) -> None:
        # Validate: no slashes, no leading dot abuse
        if "/" in new_name or new_name in (".", ".."):
            log.warning("invalid rename target: %r", new_name)
            return
        old = ico.entry.path
        new = old.parent / new_name
        if new.exists():
            log.warning("rename target exists: %s", new)
            return
        try:
            gfile = Gio.File.new_for_path(str(old))
            gfile.set_display_name(new_name, None)
            log.info("renamed %s → %s", old.name, new_name)
        except Exception as e:
            log.error("rename failed: %s", e)


# ---------- IPC server (live wallpaper hot-swap from any process) ----------
class IPCServer(threading.Thread):
    """Tiny line-protocol Unix socket. Commands:
        WALLPAPER <abs-path>\n   -> swap on all monitors
        RELOAD\n                 -> re-read config
        PING\n                   -> reply PONG
    """

    def __init__(self, app: "DesktopApp") -> None:
        super().__init__(daemon=True)
        self.app = app

    def run(self) -> None:
        try:
            if SOCK_PATH.exists():
                SOCK_PATH.unlink()
            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv.bind(str(SOCK_PATH))
            os.chmod(SOCK_PATH, 0o600)
            srv.listen(4)
            log.info("ipc listening on %s", SOCK_PATH)
            while True:
                conn, _ = srv.accept()
                try:
                    data = conn.recv(4096).decode("utf-8", "ignore").strip()
                    self._handle(conn, data)
                finally:
                    conn.close()
        except Exception as e:
            log.error("ipc crashed: %s", e)

    def _handle(self, conn: socket.socket, data: str) -> None:
        if not data:
            return
        if data == "PING":
            conn.sendall(b"PONG\n")
            return
        if data.startswith("WALLPAPER "):
            path = data[len("WALLPAPER "):].strip()
            GLib.idle_add(self.app.set_wallpaper_all, path)
            conn.sendall(b"OK\n")
            return
        if data in ("RELOAD", "REFRESH"):
            GLib.idle_add(self.app.refresh_all)
            conn.sendall(b"OK\n")
            return
        if data == "STATUS":
            mons = ",".join(self.app.windows_by_monitor.keys()) or "none"
            n = sum(len(w.icons) for w in self.app.windows_by_monitor.values())
            conn.sendall(f"OK monitors={mons} icons={n}\n".encode())
            return
        conn.sendall(b"ERR unknown command\n")


# ---------- application ----------
CSS = b"""
.nyxus-desktop-bg { background: #080a10; }
.nyxus-desktop-icons { background: transparent; }

.nyxus-desktop-icon {
    padding: 6px;
    border-radius: 10px;
    border: 1px solid transparent;
    transition: background-color 120ms ease, border-color 120ms ease;
}
.nyxus-desktop-icon:hover {
    background: rgba(212, 184, 122, 0.10);
    border-color: rgba(212, 184, 122, 0.35);
}
.nyxus-desktop-icon.selected {
    background: rgba(212, 184, 122, 0.22);
    border-color: #d4b87a;
}

.nyxus-desktop-icon-label {
    color: #ffffff;
    font-size: 11px;
    font-weight: 500;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.85),
                 0 0 4px rgba(0, 0, 0, 0.7);
    padding: 2px 4px;
    background: rgba(8, 10, 16, 0.55);
    border-radius: 4px;
}
.nyxus-desktop-icon.selected .nyxus-desktop-icon-label {
    background: rgba(212, 184, 122, 0.95);
    color: #080a10;
    text-shadow: none;
}
.nyxus-desktop-icon.dragging {
    opacity: 0.55;
}
.nyxus-desktop-icon-rename {
    min-height: 22px;
    padding: 1px 4px;
    background: #ffffff;
    color: #080a10;
    border: 1px solid #d4b87a;
    border-radius: 4px;
    font-size: 11px;
}
.nyxus-desktop-marquee {
    background: rgba(212, 184, 122, 0.18);
    border: 1px solid rgba(212, 184, 122, 0.85);
    border-radius: 2px;
}
"""


class DesktopApp(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="com.nyxus.desktop",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.windows_by_monitor: dict[str, DesktopSurface] = {}
        self.cfg: dict = load_config()
        # single shared filesystem watcher (no per-monitor duplication)
        self._desktop_monitor: Optional[Gio.FileMonitor] = None
        self._refresh_pending = False
        self._refresh_source_id: int = 0

    def do_startup(self) -> None:  # type: ignore[override]
        Gtk.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def do_activate(self) -> None:  # type: ignore[override]
        display = Gdk.Display.get_default()
        if display is None:
            log.error("no Gdk display; bailing")
            return
        self._spawn_for_all_monitors(display)
        # hot-plug
        monitors = display.get_monitors()
        monitors.connect("items-changed", self._on_monitors_changed, display)
        # one shared filesystem watcher for ~/Desktop, fans out to surfaces
        self._start_desktop_watch()
        # ipc
        IPCServer(self).start()

    def _start_desktop_watch(self) -> None:
        try:
            DESKTOP_DIR.mkdir(parents=True, exist_ok=True)
            gfile = Gio.File.new_for_path(str(DESKTOP_DIR))
            self._desktop_monitor = gfile.monitor_directory(
                Gio.FileMonitorFlags.WATCH_MOVES, None)
            self._desktop_monitor.connect(
                "changed", self._on_desktop_changed)
            log.info("watching %s", DESKTOP_DIR)
        except Exception as e:
            log.warning("desktop watcher failed: %s", e)

    def _on_desktop_changed(self, monitor, gfile, other,
                            event_type) -> None:
        # debounce: coalesce bursts (cp -r, mv, etc.) into one refresh.
        # Cancel any pending source so we restart the 150ms window.
        if self._refresh_source_id:
            try:
                GLib.source_remove(self._refresh_source_id)
            except Exception:
                pass
            self._refresh_source_id = 0
        self._refresh_source_id = GLib.timeout_add(
            150, self._do_debounced_refresh)

    def _do_debounced_refresh(self) -> bool:
        self._refresh_source_id = 0
        for win in self.windows_by_monitor.values():
            try:
                win.refresh_icons()
            except Exception as e:
                log.warning("refresh failed on %s: %s",
                            win.monitor.get_connector(), e)
        return False  # one-shot

    # -- monitors --
    def _spawn_for_all_monitors(self, display: Gdk.Display) -> None:
        monitors = display.get_monitors()
        for i in range(monitors.get_n_items()):
            monitor = monitors.get_item(i)
            if monitor is None:
                continue
            self._spawn_for_monitor(monitor)

    def _spawn_for_monitor(self, monitor: Gdk.Monitor) -> None:
        key = monitor.get_connector() or f"mon{id(monitor)}"
        if key in self.windows_by_monitor:
            return
        win = DesktopSurface(self, monitor, dict(self.cfg))
        win.present()
        self.windows_by_monitor[key] = win
        log.info("desktop spawned on %s", key)

    def _on_monitors_changed(
        self,
        monitors,
        position: int,
        removed: int,
        added: int,
        display: Gdk.Display,
    ) -> None:
        # rebuild known set
        present = set()
        for i in range(monitors.get_n_items()):
            mon = monitors.get_item(i)
            if mon is None:
                continue
            key = mon.get_connector() or f"mon{id(mon)}"
            present.add(key)
            if key not in self.windows_by_monitor:
                self._spawn_for_monitor(mon)
        # close stale
        for key in list(self.windows_by_monitor.keys()):
            if key not in present:
                self.windows_by_monitor[key].close()
                del self.windows_by_monitor[key]
                log.info("desktop closed on %s (unplugged)", key)

    # -- public hooks for IPC --
    def set_wallpaper_all(self, path: str) -> bool:
        self.cfg["wallpaper"] = path
        save_config(self.cfg)
        for win in self.windows_by_monitor.values():
            win.set_wallpaper(path)
        return False  # one-shot idle

    def reload_config(self) -> bool:
        self.cfg = load_config()
        for win in self.windows_by_monitor.values():
            win.set_wallpaper(self.cfg["wallpaper"])
        return False

    def refresh_all(self) -> bool:
        # Reload wallpaper config + repopulate every surface's icons
        self.cfg = load_config()
        for win in self.windows_by_monitor.values():
            try:
                win.set_wallpaper(self.cfg["wallpaper"])
                win.refresh_icons()
            except Exception as e:
                log.warning("refresh_all on %s: %s",
                            win.monitor.get_connector(), e)
        return False


def main() -> int:
    app = DesktopApp()
    try:
        return app.run(sys.argv)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
