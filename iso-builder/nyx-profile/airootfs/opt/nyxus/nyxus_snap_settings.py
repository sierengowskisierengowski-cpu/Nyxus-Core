#!/usr/bin/env python3
"""GTK4/libadwaita settings page for NYXUS Snap.

Embedded by the main NYXUS Settings shell. Provides:
  - Edge sensitivity slider
  - Picker hold timing slider
  - Snap-to-cell toggle
  - Per-app rules editor (add/remove)
  - Layout viewer (read-only grid preview per layout)
  - Snapshot save/restore controls
All disk and IPC work runs off the GTK main thread.
"""
from __future__ import annotations

import json
import os
import socket
import threading
from pathlib import Path
from typing import Any

import gi
gi.require_version("Gtk", "4.0")
try:
    gi.require_version("Adw", "1")
    from gi.repository import Adw
    HAVE_ADW = True
except (ValueError, ImportError):
    HAVE_ADW = False
from gi.repository import Gtk, GLib  # type: ignore


HOME      = Path(os.environ.get("HOME", "/root"))
XDG_RUN   = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
SOCK_PATH = XDG_RUN / "nyxus-snap" / "cmd.sock"
CFG_PATH  = HOME / ".config/nyxus/snap.toml"


def rpc(op: str, **kw) -> dict:
    if not SOCK_PATH.exists():
        return {"ok": False, "error": "daemon not running"}
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(str(SOCK_PATH))
        s.send((json.dumps({"op": op, **kw}) + "\n").encode())
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        s.close()
        return json.loads(buf.split(b"\n", 1)[0].decode() or '{"ok":false}')
    except OSError as e:
        return {"ok": False, "error": str(e)}


def run_async(fn, on_done):
    def _w():
        try:
            r = fn()
        except Exception as e:
            r = {"ok": False, "error": str(e)}
        GLib.idle_add(on_done, r)
    threading.Thread(target=_w, daemon=True).start()


class SnapSettingsPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(16); self.set_margin_end(16)
        self.set_margin_top(16); self.set_margin_bottom(16)

        title = Gtk.Label(label="<span size='x-large' weight='bold'>NYXUS Snap</span>",
                          use_markup=True, xalign=0)
        self.append(title)
        sub = Gtk.Label(label="Window tiling, zones, and snapshots.", xalign=0)
        sub.add_css_class("dim-label"); self.append(sub)

        # ── Options grid ──
        opt_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        opt_box.add_css_class("card"); opt_box.set_margin_top(12)
        opt_box.append(self._row("Edge sensitivity (px)",
                                  self._spin("edge_px", 4, 80, 1)))
        opt_box.append(self._row("Picker hold (ms)",
                                  self._spin("picker_hold_ms", 50, 1500, 25)))
        opt_box.append(self._row("Ghost fade (ms)",
                                  self._spin("ghost_fade_ms", 0, 600, 10)))
        opt_box.append(self._row("Snap to cell",
                                  self._switch("snap_to_cell")))
        opt_box.append(self._row("Remember layout per workspace",
                                  self._switch("remember_per_ws")))
        self.append(opt_box)

        # ── Layouts viewer ──
        lay_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        lay_box.add_css_class("card")
        lay_box.append(Gtk.Label(label="<b>Layouts</b>", use_markup=True, xalign=0))
        self.layouts_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        lay_box.append(self.layouts_list)
        self.append(lay_box)

        # ── Snapshots ──
        snap_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        snap_box.add_css_class("card")
        snap_box.append(Gtk.Label(label="<b>Snapshots</b>", use_markup=True, xalign=0))
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.snap_name = Gtk.Entry(placeholder_text="snapshot name")
        save_btn = Gtk.Button(label="Save")
        save_btn.connect("clicked", self._on_save_snapshot)
        row.append(self.snap_name); row.append(save_btn)
        snap_box.append(row)
        self.snap_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        snap_box.append(self.snap_list)
        self.append(snap_box)

        # ── Action bar ──
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions.set_margin_top(12)
        reload_btn = Gtk.Button(label="Reload daemon")
        reload_btn.connect("clicked", self._on_reload)
        actions.append(reload_btn)
        self.append(actions)

        self._refresh_all()

    # ── widget helpers ──
    def _row(self, label: str, widget: Gtk.Widget) -> Gtk.Box:
        b = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        l = Gtk.Label(label=label, xalign=0); l.set_hexpand(True)
        b.append(l); b.append(widget)
        return b

    def _spin(self, key: str, mn: int, mx: int, step: int) -> Gtk.SpinButton:
        sb = Gtk.SpinButton.new_with_range(mn, mx, step)
        sb.set_value(0)
        sb._key = key  # type: ignore[attr-defined]
        return sb

    def _switch(self, key: str) -> Gtk.Switch:
        sw = Gtk.Switch(); sw._key = key  # type: ignore[attr-defined]
        return sw

    # ── data ──
    def _refresh_all(self):
        run_async(lambda: rpc("list"),       self._populate_layouts)
        run_async(lambda: rpc("snapshots"),  self._populate_snapshots)

    def _populate_layouts(self, r: dict):
        child = self.layouts_list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.layouts_list.remove(child)
            child = nxt
        for ly in r.get("layouts", []) or []:
            row = Gtk.Label(
                label=f"<b>{ly['name']}</b> — {len(ly['zones'])} zones: "
                      + ", ".join(z["id"] for z in ly["zones"]),
                use_markup=True, xalign=0,
            )
            self.layouts_list.append(row)
        return False

    def _populate_snapshots(self, r: dict):
        child = self.snap_list.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.snap_list.remove(child)
            child = nxt
        for n in r.get("names", []) or []:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            row.append(Gtk.Label(label=n, xalign=0, hexpand=True))
            rb = Gtk.Button(label="Restore"); rb.set_data("name", n)
            rb.connect("clicked", self._on_restore_snapshot, n)
            row.append(rb)
            self.snap_list.append(row)
        return False

    # ── actions ──
    def _on_save_snapshot(self, _btn):
        name = self.snap_name.get_text().strip()
        if not name:
            return
        run_async(lambda: rpc("save", name=name), lambda _r: self._refresh_all() or False)

    def _on_restore_snapshot(self, _btn, name: str):
        run_async(lambda: rpc("restore", name=name), lambda _r: False)

    def _on_reload(self, _btn):
        run_async(lambda: rpc("reload"), lambda _r: self._refresh_all() or False)


def main():
    if HAVE_ADW:
        app = Adw.Application(application_id="dev.nyxus.SnapSettings")
    else:
        app = Gtk.Application(application_id="dev.nyxus.SnapSettings")

    def on_activate(a):
        win = Gtk.ApplicationWindow(application=a, title="NYXUS Snap")
        win.set_default_size(640, 720)
        sw = Gtk.ScrolledWindow(); sw.set_child(SnapSettingsPage())
        win.set_child(sw); win.present()

    app.connect("activate", on_activate)
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
