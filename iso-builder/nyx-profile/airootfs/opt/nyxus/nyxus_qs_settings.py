#!/usr/bin/env python3
"""GTK4/libadwaita settings page for NYXUS Quick Settings."""
from __future__ import annotations

import json
import os
import socket
import threading
from pathlib import Path

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
SOCK_PATH = XDG_RUN / "nyxus-qs" / "cmd.sock"
CFG_PATH  = HOME / ".config/nyxus/quicksettings.toml"


def rpc(op: str, **kw) -> dict:
    if not SOCK_PATH.exists():
        return {"ok": False, "error": "daemon not running"}
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(3); s.connect(str(SOCK_PATH))
        s.send((json.dumps({"op": op, **kw}) + "\n").encode())
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536)
            if not chunk:
                break
            buf += chunk
        s.close()
        return json.loads(buf.split(b"\n", 1)[0].decode() or '{"ok":false}')
    except (OSError, json.JSONDecodeError) as e:
        return {"ok": False, "error": str(e)}


def run_async(fn, on_done):
    def _w():
        try:
            r = fn()
        except Exception as e:
            r = {"ok": False, "error": str(e)}
        GLib.idle_add(on_done, r)
    threading.Thread(target=_w, daemon=True).start()


class QuickSettingsPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(16); self.set_margin_end(16)
        self.set_margin_top(16); self.set_margin_bottom(16)

        self.append(Gtk.Label(
            label="<span size='x-large' weight='bold'>NYXUS Quick Settings</span>",
            use_markup=True, xalign=0))
        sub = Gtk.Label(label="Wi-Fi, Bluetooth, audio, brightness, battery, DND.",
                         xalign=0)
        sub.add_css_class("dim-label"); self.append(sub)

        # Live state
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card"); card.set_margin_top(12)
        card.append(Gtk.Label(label="<b>Live tile state</b>", use_markup=True, xalign=0))
        self.tiles_label = Gtk.Label(label="(loading)", xalign=0, wrap=True,
                                       use_markup=True)
        card.append(self.tiles_label)
        self.append(card)

        # Toggles
        toggles = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        toggles.add_css_class("card")
        toggles.append(Gtk.Label(label="<b>Toggles</b>", use_markup=True, xalign=0))
        for name in ("wifi", "bluetooth", "dnd", "nightlight"):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl = Gtk.Label(label=name, xalign=0); lbl.set_hexpand(True)
            sw = Gtk.Switch()
            sw.connect("state-set",
                       lambda _s, st, n=name: self._set_toggle(n, st) or False)
            row.append(lbl); row.append(sw); toggles.append(row)
        self.append(toggles)

        # Sliders
        sliders = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        sliders.add_css_class("card")
        sliders.append(Gtk.Label(label="<b>Sliders</b>", use_markup=True, xalign=0))
        for name in ("volume", "brightness"):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            lbl = Gtk.Label(label=name, xalign=0); lbl.set_hexpand(True)
            sl = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 5)
            sl.set_hexpand(True); sl.set_size_request(180, -1)
            sl.connect("value-changed",
                       lambda s, n=name: self._set_slider(n, int(s.get_value())))
            row.append(lbl); row.append(sl); sliders.append(row)
        self.append(sliders)

        # Action
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions.set_margin_top(12)
        rb = Gtk.Button(label="Reload"); rb.connect("clicked", self._reload)
        actions.append(rb); self.append(actions)

        self._refresh()

    def _refresh(self):
        run_async(lambda: rpc("state"), self._populate)

    def _populate(self, r):
        s = (r or {}).get("state", {}).get("tiles", {}) or {}
        lines = []
        for name, v in s.items():
            lines.append(f"<b>{name}</b>: {json.dumps(v)}")
        self.tiles_label.set_label("\n".join(lines) or "(empty)")
        return False

    def _set_toggle(self, name: str, on: bool):
        run_async(lambda: rpc(name, on=on), lambda _r: self._refresh() or False)

    def _set_slider(self, name: str, pct: int):
        run_async(lambda: rpc(name, pct=pct), lambda _r: False)

    def _reload(self, _b):
        run_async(lambda: rpc("reload"), lambda _r: self._refresh() or False)


def main():
    if HAVE_ADW:
        app = Adw.Application(application_id="dev.nyxus.QuickSettings")
    else:
        app = Gtk.Application(application_id="dev.nyxus.QuickSettings")

    def on_activate(a):
        win = Gtk.ApplicationWindow(application=a, title="NYXUS Quick Settings")
        win.set_default_size(560, 620)
        sw = Gtk.ScrolledWindow(); sw.set_child(QuickSettingsPage())
        win.set_child(sw); win.present()

    app.connect("activate", on_activate)
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
