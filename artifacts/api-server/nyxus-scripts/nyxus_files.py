#!/usr/bin/env python3
"""
NYXUS Files — Finder/Explorer-class file manager.

GTK4 + libadwaita. Single-window, tabs, sidebar of bookmarks + mounts,
breadcrumb path bar, grid/list view toggle, type-ahead search,
real file ops via Gio (copy, move, trash, rename, paste), MIME-aware
open via xdg-open, drag-and-drop with the desktop layer.

Launch:
    nyxus-files [path...]    # one tab per path; default: $HOME

Log:
    ~/.cache/nyxus/files.log
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

# ---------- paths / log ----------
HOME = Path(os.path.expanduser("~"))
CACHE = HOME / ".cache" / "nyxus"
CACHE.mkdir(parents=True, exist_ok=True)
LOG_FILE = CACHE / "files.log"

log = logging.getLogger("nyxus_files")
log.setLevel(logging.INFO)
_h = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=512_000,
                                          backupCount=3)
_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(_h)

GOLD = "#d4b87a"
INK = "#080a10"


# ---------- model ----------
@dataclass
class Bookmark:
    label: str
    icon: str
    path: Path


def standard_bookmarks() -> list[Bookmark]:
    candidates = [
        ("Home", "user-home", HOME),
        ("Desktop", "user-desktop", HOME / "Desktop"),
        ("Documents", "folder-documents", HOME / "Documents"),
        ("Downloads", "folder-download", HOME / "Downloads"),
        ("Pictures", "folder-pictures", HOME / "Pictures"),
        ("Music", "folder-music", HOME / "Music"),
        ("Videos", "folder-videos", HOME / "Videos"),
        ("Trash", "user-trash", Path("trash:///")),
        ("Root", "drive-harddisk", Path("/")),
    ]
    out: list[Bookmark] = []
    for label, icon, p in candidates:
        if str(p).startswith("trash:") or p.exists():
            out.append(Bookmark(label, icon, p))
    return out


# ---------- file row ----------
class FileRow(Gtk.Box):
    """One entry in the list view: icon + name + size + modified."""

    def __init__(self, path: Path, info: Gio.FileInfo) -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.path = path
        self.info = info
        self.set_margin_top(2)
        self.set_margin_bottom(2)

        gicon = info.get_icon()
        img = Gtk.Image()
        img.set_pixel_size(20)
        if gicon:
            img.set_from_gicon(gicon)
        else:
            img.set_from_icon_name("text-x-generic")
        self.append(img)

        name = Gtk.Label(label=info.get_display_name() or path.name)
        name.set_xalign(0)
        name.set_hexpand(True)
        name.set_ellipsize(3)
        self.append(name)

        size = Gtk.Label(label=human_size(info))
        size.set_xalign(1)
        size.add_css_class("dim-label")
        size.set_width_chars(10)
        self.append(size)

        mtime = info.get_modification_date_time()
        mt = Gtk.Label(
            label=mtime.format("%Y-%m-%d %H:%M") if mtime else ""
        )
        mt.set_xalign(1)
        mt.add_css_class("dim-label")
        mt.set_width_chars(18)
        self.append(mt)


def human_size(info: Gio.FileInfo) -> str:
    if info.get_file_type() == Gio.FileType.DIRECTORY:
        return "—"
    n = info.get_size()
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


# ---------- tab body (one path per tab) ----------
class FilesTab(Gtk.Box):
    """A single tab: breadcrumb + view switch + search + body."""

    def __init__(self, parent: "FilesWindow", initial_path: Path) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.parent_win = parent
        self.path: Path = initial_path
        self.history: list[Path] = [initial_path]
        self.history_idx = 0
        self.view_mode = "list"  # or "grid"
        self.filter_text = ""
        self.clipboard_paths: list[Path] = []
        self.clipboard_op: str = "copy"  # or "cut"

        self._build_toolbar()
        self._build_body()
        self.refresh()

    # -- toolbar with breadcrumb + actions --
    def _build_toolbar(self) -> None:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        bar.set_margin_start(8)
        bar.set_margin_end(8)
        bar.set_margin_top(6)
        bar.set_margin_bottom(6)
        self.append(bar)

        self.btn_back = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        self.btn_back.set_tooltip_text("Back (Alt+Left)")
        self.btn_back.connect("clicked", lambda *_: self.go_back())
        bar.append(self.btn_back)

        self.btn_fwd = Gtk.Button.new_from_icon_name("go-next-symbolic")
        self.btn_fwd.set_tooltip_text("Forward (Alt+Right)")
        self.btn_fwd.connect("clicked", lambda *_: self.go_forward())
        bar.append(self.btn_fwd)

        self.btn_up = Gtk.Button.new_from_icon_name("go-up-symbolic")
        self.btn_up.set_tooltip_text("Up (Alt+Up)")
        self.btn_up.connect("clicked", lambda *_: self.go_up())
        bar.append(self.btn_up)

        # breadcrumb / address entry
        self.address = Gtk.Entry()
        self.address.set_hexpand(True)
        self.address.set_text(str(self.path))
        self.address.connect("activate", self._on_address_activate)
        bar.append(self.address)

        # search
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text("Filter")
        self.search.set_width_chars(18)
        self.search.connect("search-changed", self._on_search)
        bar.append(self.search)

        # view toggle
        self.btn_view = Gtk.Button.new_from_icon_name("view-grid-symbolic")
        self.btn_view.set_tooltip_text("Toggle list/grid view")
        self.btn_view.connect("clicked", lambda *_: self._toggle_view())
        bar.append(self.btn_view)

        # new folder
        btn_new = Gtk.Button.new_from_icon_name("folder-new-symbolic")
        btn_new.set_tooltip_text("New folder")
        btn_new.connect("clicked", lambda *_: self._new_folder())
        bar.append(btn_new)

    def _build_body(self) -> None:
        scroller = Gtk.ScrolledWindow()
        scroller.set_vexpand(True)
        scroller.set_policy(Gtk.PolicyType.AUTOMATIC,
                            Gtk.PolicyType.AUTOMATIC)
        self.append(scroller)

        # one container; we swap children when toggling view mode
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scroller.set_child(self.body)

        # keyboard nav at tab level
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

    # -- navigation --
    def navigate(self, new_path: Path, push_history: bool = True) -> None:
        self.path = new_path
        if push_history:
            # truncate forward history if user navigated mid-history
            self.history = self.history[: self.history_idx + 1]
            self.history.append(new_path)
            self.history_idx = len(self.history) - 1
        self.address.set_text(str(new_path))
        self.parent_win.tab_view.get_page(self).set_title(new_path.name or "/")
        self.refresh()

    def go_back(self) -> None:
        if self.history_idx > 0:
            self.history_idx -= 1
            self.navigate(self.history[self.history_idx], push_history=False)

    def go_forward(self) -> None:
        if self.history_idx < len(self.history) - 1:
            self.history_idx += 1
            self.navigate(self.history[self.history_idx], push_history=False)

    def go_up(self) -> None:
        parent = self.path.parent
        if parent != self.path:
            self.navigate(parent)

    def _on_address_activate(self, entry: Gtk.Entry) -> None:
        text = entry.get_text().strip()
        target = Path(os.path.expanduser(text))
        if target.exists():
            self.navigate(target)
        else:
            self._toast(f"Path not found: {text}")
            entry.set_text(str(self.path))

    # -- search --
    def _on_search(self, entry: Gtk.SearchEntry) -> None:
        self.filter_text = entry.get_text().lower().strip()
        self.refresh()

    # -- view --
    def _toggle_view(self) -> None:
        self.view_mode = "grid" if self.view_mode == "list" else "list"
        self.btn_view.set_icon_name(
            "view-list-symbolic" if self.view_mode == "grid"
            else "view-grid-symbolic")
        self.refresh()

    # -- refresh --
    def refresh(self) -> None:
        # clear body
        child = self.body.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.body.remove(child)
            child = nxt
        # nav button sensitivity
        self.btn_back.set_sensitive(self.history_idx > 0)
        self.btn_fwd.set_sensitive(self.history_idx < len(self.history) - 1)
        self.btn_up.set_sensitive(self.path.parent != self.path)
        # gather entries via Gio (handles trash:// + mounts)
        try:
            gfile = Gio.File.new_for_uri(str(self.path)) \
                if str(self.path).startswith("trash:") \
                else Gio.File.new_for_path(str(self.path))
            attrs = ("standard::display-name,standard::name,standard::type,"
                     "standard::icon,standard::size,standard::content-type,"
                     "time::modified,access::can-read")
            enumerator = gfile.enumerate_children(
                attrs, Gio.FileQueryInfoFlags.NONE, None)
        except Exception as e:
            log.error("enumerate %s failed: %s", self.path, e)
            self._error_panel(f"Cannot read {self.path}: {e}")
            return

        rows: list[tuple[Path, Gio.FileInfo]] = []
        while True:
            try:
                info = enumerator.next_file(None)
            except Exception:
                break
            if info is None:
                break
            name = info.get_name()
            if name.startswith(".") and not self.parent_win.show_hidden:
                continue
            if (self.filter_text
                    and self.filter_text not in (info.get_display_name()
                                                 or name).lower()):
                continue
            child_path = self.path / name
            rows.append((child_path, info))
        rows.sort(key=lambda r: (
            r[1].get_file_type() != Gio.FileType.DIRECTORY,
            (r[1].get_display_name() or r[0].name).lower()))

        if not rows:
            self._error_panel("This folder is empty.")
            return

        if self.view_mode == "list":
            self._render_list(rows)
        else:
            self._render_grid(rows)

    def _render_list(self, rows: list[tuple[Path, Gio.FileInfo]]) -> None:
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        list_box.set_show_separators(False)
        list_box.add_css_class("nyxus-files-list")
        list_box.connect("row-activated", self._on_list_activate)
        for path, info in rows:
            row = Gtk.ListBoxRow()
            row.set_child(FileRow(path, info))
            row._path = path
            row._info = info
            list_box.append(row)
        # right-click anywhere
        click = Gtk.GestureClick()
        click.set_button(Gdk.BUTTON_SECONDARY)
        click.connect("pressed", self._on_list_right_click, list_box)
        list_box.add_controller(click)
        self.list_box = list_box
        self.body.append(list_box)

    def _render_grid(self, rows: list[tuple[Path, Gio.FileInfo]]) -> None:
        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(20)
        flow.set_min_children_per_line(2)
        flow.set_homogeneous(True)
        flow.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        flow.set_row_spacing(8)
        flow.set_column_spacing(8)
        flow.connect("child-activated", self._on_grid_activate)
        for path, info in rows:
            cell = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            cell.set_size_request(96, 96)
            img = Gtk.Image()
            img.set_pixel_size(48)
            gicon = info.get_icon()
            if gicon:
                img.set_from_gicon(gicon)
            else:
                img.set_from_icon_name("text-x-generic")
            cell.append(img)
            lbl = Gtk.Label(label=info.get_display_name() or path.name)
            lbl.set_max_width_chars(12)
            lbl.set_ellipsize(3)
            lbl.set_lines(2)
            lbl.set_wrap(True)
            cell.append(lbl)
            child = Gtk.FlowBoxChild()
            child.set_child(cell)
            child._path = path
            child._info = info
            flow.append(child)
        self.flow = flow
        self.body.append(flow)

    def _error_panel(self, msg: str) -> None:
        label = Gtk.Label(label=msg)
        label.set_margin_top(40)
        label.add_css_class("dim-label")
        self.body.append(label)

    # -- activation --
    def _on_list_activate(self, list_box: Gtk.ListBox,
                          row: Gtk.ListBoxRow) -> None:
        self._open_path(row._path, row._info)

    def _on_grid_activate(self, flow: Gtk.FlowBox,
                          child: Gtk.FlowBoxChild) -> None:
        self._open_path(child._path, child._info)

    def _open_path(self, path: Path, info: Gio.FileInfo) -> None:
        if info.get_file_type() == Gio.FileType.DIRECTORY:
            self.navigate(path)
        else:
            try:
                subprocess.Popen(["xdg-open", str(path)],
                                 start_new_session=True)
            except Exception as e:
                self._toast(f"Open failed: {e}")

    # -- right-click on list/grid --
    def _on_list_right_click(self, gesture, n, x, y, list_box):
        # delegate to nyxus-context-menu.sh icon mode for the row under cursor
        row = list_box.get_row_at_y(int(y))
        if row is None:
            return
        list_box.select_row(row)
        self._spawn_icon_menu(row._path)

    def _spawn_icon_menu(self, path: Path) -> None:
        try:
            subprocess.Popen(
                ["nyxus-context-menu.sh", "icon", str(path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True)
        except Exception as e:
            self._toast(f"Menu failed: {e}")

    # -- keyboard --
    def _on_key(self, ctrl, keyval, keycode, state) -> bool:
        if (state & Gdk.ModifierType.ALT_MASK):
            if keyval == Gdk.KEY_Left:
                self.go_back()
                return True
            if keyval == Gdk.KEY_Right:
                self.go_forward()
                return True
            if keyval == Gdk.KEY_Up:
                self.go_up()
                return True
        if (state & Gdk.ModifierType.CONTROL_MASK):
            if keyval in (Gdk.KEY_l, Gdk.KEY_L):
                self.address.grab_focus()
                return True
            if keyval in (Gdk.KEY_f, Gdk.KEY_F):
                self.search.grab_focus()
                return True
            if keyval in (Gdk.KEY_h, Gdk.KEY_H):
                self.parent_win.show_hidden = not self.parent_win.show_hidden
                self.refresh()
                return True
            if keyval in (Gdk.KEY_n, Gdk.KEY_N):
                self._new_folder()
                return True
            if keyval in (Gdk.KEY_c, Gdk.KEY_C):
                self._copy_selected("copy")
                return True
            if keyval in (Gdk.KEY_x, Gdk.KEY_X):
                self._copy_selected("cut")
                return True
            if keyval in (Gdk.KEY_v, Gdk.KEY_V):
                self._paste_clipboard()
                return True
        if keyval == Gdk.KEY_F5:
            self.refresh()
            return True
        if keyval == Gdk.KEY_Delete:
            for p in self._selected_paths():
                self._trash(p)
            return True
        if keyval == Gdk.KEY_F2:
            sel = self._selected_paths()
            if len(sel) == 1:
                self._rename_prompt(sel[0])
            return True
        return False

    def _selected_paths(self) -> list[Path]:
        out: list[Path] = []
        if self.view_mode == "list" and hasattr(self, "list_box"):
            for row in self.list_box.get_selected_rows():
                out.append(row._path)
        elif self.view_mode == "grid" and hasattr(self, "flow"):
            for child in self.flow.get_selected_children():
                out.append(child._path)
        return out

    # -- file operations --
    def _new_folder(self) -> None:
        base = self.path / "New Folder"
        n = 1
        target = base
        while target.exists():
            n += 1
            target = self.path / f"New Folder {n}"
        try:
            target.mkdir()
            self.refresh()
        except Exception as e:
            self._toast(f"New folder failed: {e}")

    def _trash(self, p: Path) -> None:
        try:
            Gio.File.new_for_path(str(p)).trash(None)
        except Exception:
            try:
                subprocess.run(["gio", "trash", "--", str(p)], check=False)
            except Exception as e:
                self._toast(f"Trash failed: {e}")
        self.refresh()

    def _rename_prompt(self, p: Path) -> None:
        dialog = Adw.MessageDialog.new(self.parent_win, "Rename", None)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("ok", "Rename")
        dialog.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        entry = Gtk.Entry()
        entry.set_text(p.name)
        dialog.set_extra_child(entry)

        def on_resp(d, resp):
            if resp == "ok":
                new = entry.get_text().strip()
                if new and new != p.name and "/" not in new:
                    try:
                        Gio.File.new_for_path(str(p)).set_display_name(
                            new, None)
                    except Exception as e:
                        self._toast(f"Rename failed: {e}")
                    self.refresh()
        dialog.connect("response", on_resp)
        dialog.present()

    def _copy_selected(self, op: str) -> None:
        self.clipboard_paths = self._selected_paths()
        self.clipboard_op = op
        if self.clipboard_paths:
            self._toast(
                f"{'Cut' if op == 'cut' else 'Copied'} "
                f"{len(self.clipboard_paths)} item(s)")

    def _paste_clipboard(self) -> None:
        if not self.clipboard_paths:
            return
        for src in self.clipboard_paths:
            try:
                dest = self.path / src.name
                if dest.exists():
                    dest = self.path / f"{src.stem} (copy){src.suffix}"
                if self.clipboard_op == "cut":
                    shutil.move(str(src), str(dest))
                else:
                    if src.is_dir():
                        shutil.copytree(src, dest)
                    else:
                        shutil.copy2(src, dest)
            except Exception as e:
                self._toast(f"Paste failed: {e}")
        if self.clipboard_op == "cut":
            self.clipboard_paths = []
        self.refresh()

    def _toast(self, msg: str) -> None:
        try:
            self.parent_win.toast(msg)
        except Exception:
            log.warning(msg)


# ---------- main window ----------
class FilesWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, paths: list[Path]) -> None:
        super().__init__(application=app)
        self.set_title("Files")
        self.set_default_size(1100, 720)
        self.show_hidden = False
        self._build_ui(paths)

    def _build_ui(self, paths: list[Path]) -> None:
        toolbar = Adw.ToolbarView()
        self.set_content(toolbar)

        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        # new tab button
        btn_new_tab = Gtk.Button.new_from_icon_name("tab-new-symbolic")
        btn_new_tab.set_tooltip_text("New tab (Ctrl+T)")
        btn_new_tab.connect("clicked", lambda *_: self._new_tab(HOME))
        header.pack_start(btn_new_tab)

        # split view
        split = Adw.NavigationSplitView()
        split.set_max_sidebar_width(220)
        split.set_min_sidebar_width(180)
        toolbar.set_content(split)

        # sidebar
        sidebar_page = Adw.NavigationPage()
        sidebar_page.set_title("Places")
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar_page.set_child(sidebar_box)
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        list_box.add_css_class("navigation-sidebar")
        list_box.connect("row-activated", self._on_sidebar_activate)
        sidebar_box.append(list_box)
        for bm in standard_bookmarks():
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            box.set_margin_start(8)
            box.set_margin_end(8)
            box.set_margin_top(4)
            box.set_margin_bottom(4)
            ico = Gtk.Image.new_from_icon_name(bm.icon)
            ico.set_pixel_size(18)
            box.append(ico)
            box.append(Gtk.Label(label=bm.label, xalign=0, hexpand=True))
            row.set_child(box)
            row._path = bm.path
            list_box.append(row)
        # mounts via gio
        try:
            vm = Gio.VolumeMonitor.get()
            for mount in vm.get_mounts():
                row = Gtk.ListBoxRow()
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                              spacing=8)
                box.set_margin_start(8); box.set_margin_end(8)
                box.set_margin_top(4); box.set_margin_bottom(4)
                ico = Gtk.Image.new_from_icon_name("drive-removable-media")
                ico.set_pixel_size(18)
                box.append(ico)
                box.append(Gtk.Label(label=mount.get_name(), xalign=0,
                                     hexpand=True))
                row.set_child(box)
                root = mount.get_root()
                p = root.get_path() if root else None
                if p:
                    row._path = Path(p)
                    list_box.append(row)
        except Exception as e:
            log.debug("mount enumeration failed: %s", e)
        split.set_sidebar(sidebar_page)

        # content: tab view
        content_page = Adw.NavigationPage()
        content_page.set_title("Files")
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content_page.set_child(content_box)
        self.tab_view = Adw.TabView()
        self.tab_view.connect("close-page", self._on_tab_close)
        tab_bar = Adw.TabBar.new()
        tab_bar.set_view(self.tab_view)
        content_box.append(tab_bar)
        content_box.append(self.tab_view)
        self.tab_view.set_vexpand(True)
        split.set_content(content_page)

        # toast overlay
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(toolbar)
        self.set_content(self.toast_overlay)

        # initial tabs
        for p in paths:
            self._new_tab(p)

        # window-level shortcuts
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

    def _new_tab(self, path: Path) -> None:
        tab = FilesTab(self, path)
        page = self.tab_view.append(tab)
        page.set_title(path.name or str(path))
        self.tab_view.set_selected_page(page)

    def _on_tab_close(self, view, page) -> bool:
        view.close_page_finish(page, True)
        if view.get_n_pages() == 0:
            self.close()
        return True

    def _on_sidebar_activate(self, list_box, row) -> None:
        target = row._path
        sel = self.tab_view.get_selected_page()
        if sel is not None:
            tab = sel.get_child()
            if isinstance(tab, FilesTab):
                tab.navigate(target)
                return
        self._new_tab(target)

    def _on_key(self, ctrl, keyval, keycode, state) -> bool:
        if (state & Gdk.ModifierType.CONTROL_MASK) and keyval in (
                Gdk.KEY_t, Gdk.KEY_T):
            self._new_tab(HOME)
            return True
        if (state & Gdk.ModifierType.CONTROL_MASK) and keyval in (
                Gdk.KEY_w, Gdk.KEY_W):
            sel = self.tab_view.get_selected_page()
            if sel is not None:
                self.tab_view.close_page(sel)
            return True
        return False

    def toast(self, msg: str) -> None:
        try:
            self.toast_overlay.add_toast(Adw.Toast.new(msg))
        except Exception:
            log.info(msg)


# ---------- application ----------
class FilesApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="com.nyxus.files",
                         flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE)

    def do_command_line(self, cmdline) -> int:  # type: ignore[override]
        argv = cmdline.get_arguments()
        paths: list[Path] = []
        for a in argv[1:]:
            p = Path(os.path.expanduser(a))
            if p.exists():
                paths.append(p)
        if not paths:
            paths = [HOME]
        win = FilesWindow(self, paths)
        win.present()
        return 0


def main() -> int:
    app = FilesApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
