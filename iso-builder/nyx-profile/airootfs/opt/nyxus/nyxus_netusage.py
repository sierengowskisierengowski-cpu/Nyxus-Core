#!/usr/bin/env python3
"""NYXUS Network Usage · per-process bandwidth viewer (GTK4/libadwaita).

Uses `nethogs -t -d 1` (text-mode, 1s output) parsed line-by-line. Falls
back to a per-interface roll-up from /proc/net/dev if nethogs is missing
or not setuid. The viewer never blocks the GTK loop — the parser runs
on a worker thread and pumps via GLib.idle_add.
"""
from __future__ import annotations

import os
import subprocess
import threading
from collections import OrderedDict
from pathlib import Path
from typing import Iterable

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

PROC_NET_DEV = Path("/proc/net/dev")


def have_nethogs() -> bool:
    try:
        subprocess.run(["nethogs", "-V"], stdout=subprocess.DEVNULL,
                       stderr=subprocess.DEVNULL, timeout=2)
        return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def parse_proc_net_dev() -> list[tuple[str, int, int]]:
    out: list[tuple[str, int, int]] = []
    if not PROC_NET_DEV.is_file():
        return out
    for line in PROC_NET_DEV.read_text().splitlines()[2:]:
        if ":" not in line:
            continue
        iface, rest = line.split(":", 1)
        parts = rest.split()
        if len(parts) < 16:
            continue
        out.append((iface.strip(), int(parts[0]), int(parts[8])))
    return out


def fmt_bytes(n: float) -> str:
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


class NetUsageWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="NYXUS Network Usage")
        self.set_default_size(720, 540)
        self.rows: "OrderedDict[str, dict]" = OrderedDict()
        self._stop = threading.Event()

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Network Usage"))
        toolbar.add_top_bar(header)

        self.list = Gtk.ListBox(); self.list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list.add_css_class("nyxus-nu-list")
        self.scroll = Gtk.ScrolledWindow(); self.scroll.set_child(self.list)
        self.scroll.set_margin_top(8); self.scroll.set_margin_bottom(8)
        self.scroll.set_margin_start(12); self.scroll.set_margin_end(12)

        self.banner = Gtk.Label(label="Collecting…"); self.banner.add_css_class("nyxus-nu-banner")
        self.banner.set_xalign(0); self.banner.set_margin_start(12); self.banner.set_margin_top(8)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.append(self.banner); outer.append(self.scroll)
        toolbar.set_content(outer)
        self.set_content(toolbar)

        self.connect("close-request", self._on_close)
        threading.Thread(target=self._worker, daemon=True).start()

    def _on_close(self, *a) -> bool:
        self._stop.set()
        return False

    def _worker(self) -> None:
        if have_nethogs():
            self._run_nethogs()
        else:
            self._run_proc_net_dev()

    def _run_nethogs(self) -> None:
        try:
            proc = subprocess.Popen(
                ["nethogs", "-t", "-d", "1"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True,
            )
        except Exception as e:
            GLib.idle_add(self._set_banner, f"nethogs failed: {e}")
            self._run_proc_net_dev()
            return
        GLib.idle_add(self._set_banner, "Per-process bandwidth (nethogs · 1s)")
        try:
            for line in iter(proc.stdout.readline, ""):  # type: ignore
                if self._stop.is_set():
                    proc.terminate(); break
                line = line.strip()
                if not line or line.startswith("Refreshing") or "/" not in line:
                    continue
                # Format:  prog/PID/UID  sent KB/s  recv KB/s
                parts = line.split()
                if len(parts) < 3:
                    continue
                key = parts[0]
                try:
                    sent = float(parts[-2]); recv = float(parts[-1])
                except ValueError:
                    continue
                GLib.idle_add(self._upsert, key, sent * 1024, recv * 1024)
        finally:
            try: proc.terminate()
            except Exception: pass

    def _run_proc_net_dev(self) -> None:
        GLib.idle_add(self._set_banner,
                      "Per-interface bandwidth (/proc/net/dev · install nethogs for per-process)")
        prev: dict[str, tuple[int, int]] = {}
        while not self._stop.wait(1.0):
            for iface, rx, tx in parse_proc_net_dev():
                p = prev.get(iface)
                if p is not None:
                    GLib.idle_add(self._upsert, iface, tx - p[1], rx - p[0])
                prev[iface] = (rx, tx)

    def _set_banner(self, txt: str) -> bool:
        self.banner.set_label(txt); return False

    def _upsert(self, key: str, sent: float, recv: float) -> bool:
        if key not in self.rows:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.set_margin_top(6); box.set_margin_bottom(6)
            box.set_margin_start(10); box.set_margin_end(10)
            name = Gtk.Label(label=key); name.set_xalign(0); name.set_hexpand(True)
            name.add_css_class("nyxus-nu-name")
            up = Gtk.Label(label="↑ —"); up.add_css_class("nyxus-nu-up")
            dn = Gtk.Label(label="↓ —"); dn.add_css_class("nyxus-nu-dn")
            box.append(name); box.append(up); box.append(dn)
            row.set_child(box); self.list.append(row)
            self.rows[key] = {"row": row, "up": up, "dn": dn}
        r = self.rows[key]
        r["up"].set_label(f"↑ {fmt_bytes(sent)}/s")
        r["dn"].set_label(f"↓ {fmt_bytes(recv)}/s")
        return False


class NetUsageApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.nyxus.netusage")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.get_style_manager().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            .nyxus-nu-banner { color:#3ad8ff; font-weight:600; letter-spacing:0.06em; padding:6px 4px; }
            .nyxus-nu-list  row { background: rgba(10,13,20,0.55); border-bottom:1px solid rgba(58,216,255,0.08); }
            .nyxus-nu-name  { color:#e8edf5; font-family:monospace; font-size:12px; }
            .nyxus-nu-up    { color:#a06bff; font-family:monospace; font-size:12px; }
            .nyxus-nu-dn    { color:#3ad8ff; font-family:monospace; font-size:12px; }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        NetUsageWindow(self).present()


def main(argv=None) -> int:
    return NetUsageApp().run(argv or [])


if __name__ == "__main__":
    raise SystemExit(main())
