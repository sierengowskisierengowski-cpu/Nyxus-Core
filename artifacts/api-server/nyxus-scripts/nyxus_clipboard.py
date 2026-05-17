#!/usr/bin/env python3
"""
NYXUS Clipboard — clipboard-history popup (Win+V / Cmd+Shift+V parity).

Reads cliphist history (must be running — installed by base image) and
shows a NYXUS-styled GTK4 popup. Click an entry → it's pushed back to
the clipboard via wl-copy (Wayland) or xclip (X11 fallback). Esc / focus
loss closes.

Launch:
    nyxus-clipboard          # show popup
    nyxus-clipboard --clear  # wipe history
    nyxus-clipboard --status # quick health check (exit 0 = OK)

Hyprland keybind (set in hyprland.lua):
    bind = SUPER, V, exec, nyxus-clipboard

Log:
    ~/.cache/nyxus/clipboard.log
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell
    HAS_LAYER_SHELL = True
except Exception:
    HAS_LAYER_SHELL = False

from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

HOME = Path(os.path.expanduser("~"))
CACHE = HOME / ".cache" / "nyxus"
CACHE.mkdir(parents=True, exist_ok=True)
LOG_FILE = CACHE / "clipboard.log"

log = logging.getLogger("nyxus_clipboard")
log.setLevel(logging.INFO)
_h = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=256_000,
                                          backupCount=2)
_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(_h)


def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def cliphist_list() -> list[tuple[str, str]]:
    """Return [(id, preview), ...] from cliphist."""
    if not have("cliphist"):
        return []
    try:
        out = subprocess.run(
            ["cliphist", "list"],
            capture_output=True, text=True, timeout=2, check=False)
    except Exception as e:
        log.error("cliphist list failed: %s", e)
        return []
    rows: list[tuple[str, str]] = []
    for line in out.stdout.splitlines():
        if "\t" in line:
            cid, preview = line.split("\t", 1)
            rows.append((cid.strip(), preview.strip()))
    return rows


def push_to_clipboard(cid: str) -> bool:
    """cliphist decode <id> | wl-copy (or xclip on X11)."""
    if not have("cliphist"):
        return False
    try:
        decoded = subprocess.run(
            ["cliphist", "decode", cid],
            capture_output=True, timeout=3, check=False)
    except Exception as e:
        log.error("cliphist decode failed: %s", e)
        return False
    payload = decoded.stdout
    if have("wl-copy"):
        cmd = ["wl-copy"]
    elif have("xclip"):
        cmd = ["xclip", "-selection", "clipboard"]
    else:
        log.error("no wl-copy or xclip installed")
        return False
    try:
        subprocess.run(cmd, input=payload, check=False, timeout=3)
        return True
    except Exception as e:
        log.error("clipboard push failed: %s", e)
        return False


def cliphist_wipe() -> None:
    if have("cliphist"):
        subprocess.run(["cliphist", "wipe"], check=False)


def cliphist_status() -> int:
    if not have("cliphist"):
        return 1
    rows = cliphist_list()
    print(f"cliphist OK, {len(rows)} entries")
    return 0


GOLD = "#d4b87a"
INK = "#080a10"
INK2 = "#10131c"
TXT = "#e6e8ee"

CSS = f"""
.nyxus-clip-window {{
    background: {INK};
    border: 1px solid {GOLD};
    border-radius: 12px;
}}
.nyxus-clip-header {{
    color: {GOLD};
    font-weight: 600;
    font-size: 12px;
    padding: 8px 12px 4px 12px;
    letter-spacing: 0.06em;
}}
.nyxus-clip-row {{
    color: {TXT};
    background: {INK2};
    padding: 8px 12px;
    margin: 2px 6px;
    border-radius: 6px;
    border: 1px solid transparent;
}}
.nyxus-clip-row:hover {{
    border-color: rgba(212, 184, 122, 0.55);
    background: rgba(212, 184, 122, 0.10);
}}
.nyxus-clip-row.selected {{
    background: {GOLD};
    color: {INK};
}}
.nyxus-clip-empty {{
    color: rgba(230, 232, 238, 0.55);
    padding: 24px;
    font-style: italic;
}}
""".encode("utf-8")


class ClipboardWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app)
        self.set_title("NYXUS Clipboard")
        self.set_default_size(420, 480)

        if HAS_LAYER_SHELL:
            LayerShell.init_for_window(self)
            LayerShell.set_layer(self, LayerShell.Layer.OVERLAY)
            LayerShell.set_keyboard_mode(self,
                                         LayerShell.KeyboardMode.EXCLUSIVE)
            LayerShell.set_namespace(self, "nyxus-clipboard")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.add_css_class("nyxus-clip-window")
        self.set_child(outer)

        header = Gtk.Label(label="CLIPBOARD HISTORY", xalign=0)
        header.add_css_class("nyxus-clip-header")
        outer.append(header)

        # search
        self.search = Gtk.SearchEntry()
        self.search.set_margin_start(8)
        self.search.set_margin_end(8)
        self.search.set_margin_bottom(4)
        self.search.connect("search-changed", lambda *_: self._populate())
        outer.append(self.search)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        outer.append(scroll)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.connect("row-activated", self._on_activate)
        scroll.set_child(self.list_box)

        # esc closes
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

        self._populate()

    def _populate(self) -> None:
        # clear
        child = self.list_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.list_box.remove(child)
            child = nxt
        rows = cliphist_list()
        q = self.search.get_text().lower().strip()
        if q:
            rows = [r for r in rows if q in r[1].lower()]
        if not rows:
            empty = Gtk.Label(
                label=("No clipboard history."
                       if not q else "No matches."),
                xalign=0)
            empty.add_css_class("nyxus-clip-empty")
            row = Gtk.ListBoxRow()
            row.set_child(empty)
            row.set_selectable(False)
            self.list_box.append(row)
            return
        for cid, preview in rows[:200]:  # cap for perf
            row = Gtk.ListBoxRow()
            lbl = Gtk.Label(label=preview[:200], xalign=0)
            lbl.set_ellipsize(3)
            lbl.add_css_class("nyxus-clip-row")
            row.set_child(lbl)
            row._cid = cid
            self.list_box.append(row)
        first = self.list_box.get_row_at_index(0)
        if first is not None:
            self.list_box.select_row(first)

    def _on_activate(self, lb, row) -> None:
        cid = getattr(row, "_cid", None)
        if cid is None:
            return
        if push_to_clipboard(cid):
            log.info("pushed clip %s", cid)
        self.close()

    def _on_key(self, ctrl, keyval, keycode, state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            row = self.list_box.get_selected_row()
            if row is not None:
                self._on_activate(self.list_box, row)
            return True
        return False


class ClipboardApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="com.nyxus.clipboard")

    def do_activate(self) -> None:  # type: ignore[override]
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        win = ClipboardWindow(self)
        win.present()


def main() -> int:
    if "--clear" in sys.argv:
        cliphist_wipe()
        return 0
    if "--status" in sys.argv:
        return cliphist_status()
    if not have("cliphist"):
        sys.stderr.write(
            "nyxus-clipboard: cliphist not installed.\n"
            "  sudo pacman -S cliphist wl-clipboard\n"
            "Then add to hyprland.lua:\n"
            "  exec-once = wl-paste --type text  --watch cliphist store\n"
            "  exec-once = wl-paste --type image --watch cliphist store\n")
        return 1
    return ClipboardApp().run([])


if __name__ == "__main__":
    sys.exit(main())
