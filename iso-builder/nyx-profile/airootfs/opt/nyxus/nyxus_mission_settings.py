#!/usr/bin/env python3
"""GTK4/libadwaita settings page for NYXUS Mission Control."""
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
SOCK_PATH = XDG_RUN / "nyxus-mission" / "cmd.sock"
CFG_PATH  = HOME / ".config/nyxus/mission.toml"


def rpc(op: str, **kw) -> dict:
    if not SOCK_PATH.exists():
        return {"ok": False, "error": "daemon not running"}
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.settimeout(4)
        s.connect(str(SOCK_PATH))
        s.send((json.dumps({"op": op, **kw}) + "\n").encode())
        buf = b""
        while b"\n" not in buf:
            chunk = s.recv(65536 * 4)
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


class MissionSettingsPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_start(16); self.set_margin_end(16)
        self.set_margin_top(16); self.set_margin_bottom(16)

        self.append(Gtk.Label(
            label="<span size='x-large' weight='bold'>NYXUS Mission Control</span>",
            use_markup=True, xalign=0))
        sub = Gtk.Label(label="Workspace overview, thumbnails, and window peek.", xalign=0)
        sub.add_css_class("dim-label"); self.append(sub)

        # info card
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("card"); card.set_margin_top(12)
        card.append(Gtk.Label(label="<b>Live state</b>", use_markup=True, xalign=0))
        self.state_label = Gtk.Label(label="(loading)", xalign=0, wrap=True)
        card.append(self.state_label)
        self.append(card)

        # actions
        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        actions.set_margin_top(12)
        for label, op in [("Open overview", "open"),
                          ("Refresh now", "refresh"),
                          ("Close overview", "close"),
                          ("Reload config", "reload")]:
            b = Gtk.Button(label=label)
            b.connect("clicked", lambda _b, o=op: self._do(o))
            actions.append(b)
        self.append(actions)

        self._refresh()

    def _refresh(self):
        run_async(lambda: rpc("state"), self._populate)

    def _populate(self, r):
        m = (r or {}).get("manifest") or {}
        ws = m.get("workspaces", [])
        mons = m.get("monitors", [])
        lines = [
            f"Workspaces: <b>{len(ws)}</b>   Monitors: <b>{len(mons)}</b>",
        ]
        for w in ws[:8]:
            lines.append(f"  ws {w.get('id')} ({w.get('monitor','?')}) — "
                          f"{len(w.get('windows', []))} windows")
        self.state_label.set_label("\n".join(lines))
        self.state_label.set_use_markup(True)
        return False

    def _do(self, op: str):
        run_async(lambda: rpc(op), lambda _r: self._refresh() or False)


def main():
    if HAVE_ADW:
        app = Adw.Application(application_id="dev.nyxus.MissionSettings")
    else:
        app = Gtk.Application(application_id="dev.nyxus.MissionSettings")

    def on_activate(a):
        win = Gtk.ApplicationWindow(application=a, title="NYXUS Mission Control")
        win.set_default_size(540, 480)
        win.set_child(MissionSettingsPage()); win.present()

    app.connect("activate", on_activate)
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
