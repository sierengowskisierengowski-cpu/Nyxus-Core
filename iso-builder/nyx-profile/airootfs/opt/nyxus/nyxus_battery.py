#!/usr/bin/env python3
"""NYXUS Battery Health · GTK4/libadwaita.

Reads /sys/class/power_supply/BAT*/ for design vs full capacity, cycle
count, current charge, status, technology, and manufacturer. Computes
Health % = (energy_full / energy_full_design) * 100. Refreshes every 5s.
"""
from __future__ import annotations

import os
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gtk  # noqa: E402

PSDIR = Path("/sys/class/power_supply")


def _read(p: Path) -> str:
    try:
        return p.read_text().strip()
    except OSError:
        return ""


def _read_int(p: Path) -> int | None:
    v = _read(p)
    try:
        return int(v)
    except ValueError:
        return None


def discover_batteries() -> list[Path]:
    if not PSDIR.is_dir():
        return []
    return sorted(p for p in PSDIR.iterdir() if p.name.startswith("BAT") and (p / "type").is_file())


def read_battery(p: Path) -> dict:
    full = _read_int(p / "energy_full") or _read_int(p / "charge_full")
    full_design = _read_int(p / "energy_full_design") or _read_int(p / "charge_full_design")
    now = _read_int(p / "energy_now") or _read_int(p / "charge_now")
    health = None
    if full and full_design and full_design > 0:
        health = round(100.0 * full / full_design, 1)
    return {
        "name":         p.name,
        "manufacturer": _read(p / "manufacturer") or "—",
        "model":        _read(p / "model_name") or "—",
        "technology":   _read(p / "technology") or "—",
        "status":       _read(p / "status") or "Unknown",
        "capacity":     _read_int(p / "capacity"),
        "cycles":       _read_int(p / "cycle_count"),
        "full_design":  full_design,
        "full":         full,
        "now":          now,
        "health":       health,
        "voltage":      _read_int(p / "voltage_now"),
    }


def fmt_wh(uwh: int | None) -> str:
    if uwh is None:
        return "—"
    return f"{uwh / 1_000_000:.2f} Wh"


class BatteryWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="NYXUS Battery Health")
        self.set_default_size(560, 640)
        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="Battery Health"))
        toolbar.add_top_bar(header)
        self.scroll = Gtk.ScrolledWindow()
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.box.set_margin_top(16); self.box.set_margin_bottom(16)
        self.box.set_margin_start(16); self.box.set_margin_end(16)
        self.scroll.set_child(self.box)
        toolbar.set_content(self.scroll)
        self.set_content(toolbar)
        self.refresh()
        GLib.timeout_add_seconds(5, self.refresh)

    def refresh(self) -> bool:
        child = self.box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.box.remove(child)
            child = nxt
        bats = discover_batteries()
        if not bats:
            lbl = Gtk.Label(label="No battery detected.")
            lbl.add_css_class("nyxus-bh-empty")
            self.box.append(lbl)
            return True
        for p in bats:
            info = read_battery(p)
            self.box.append(self._card(info))
        return True

    def _card(self, info: dict) -> Gtk.Widget:
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        card.add_css_class("nyxus-bh-card")
        card.set_margin_bottom(4)
        # Title row
        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        t = Gtk.Label(label=f"{info['name']} · {info['manufacturer']} {info['model']}")
        t.add_css_class("nyxus-bh-title"); t.set_xalign(0); t.set_hexpand(True)
        s = Gtk.Label(label=info["status"]); s.add_css_class("nyxus-bh-status")
        title_row.append(t); title_row.append(s)
        card.append(title_row)
        # Health bar
        health = info["health"] if info["health"] is not None else 0
        bar = Gtk.LevelBar(); bar.set_min_value(0); bar.set_max_value(100); bar.set_value(health)
        bar.set_size_request(-1, 14); bar.add_css_class("nyxus-bh-bar")
        card.append(bar)
        h_lbl = Gtk.Label(
            label=f"Health: {info['health']}%  ·  Cycles: {info['cycles'] if info['cycles'] is not None else '—'}"
        )
        h_lbl.add_css_class("nyxus-bh-meta"); h_lbl.set_xalign(0)
        card.append(h_lbl)
        # Detail grid
        grid = Gtk.Grid(); grid.set_column_spacing(20); grid.set_row_spacing(4)
        rows = [
            ("Charge",         f"{info['capacity']}%" if info['capacity'] is not None else "—"),
            ("Now",            fmt_wh(info["now"])),
            ("Full",           fmt_wh(info["full"])),
            ("Full (design)",  fmt_wh(info["full_design"])),
            ("Technology",     info["technology"]),
            ("Voltage",        f"{info['voltage'] / 1_000_000:.2f} V" if info['voltage'] else "—"),
        ]
        for r, (k, v) in enumerate(rows):
            kl = Gtk.Label(label=k); kl.add_css_class("nyxus-bh-k"); kl.set_xalign(0)
            vl = Gtk.Label(label=v); vl.add_css_class("nyxus-bh-v"); vl.set_xalign(0)
            grid.attach(kl, 0, r, 1, 1); grid.attach(vl, 1, r, 1, 1)
        card.append(grid)
        return card


class BatteryApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.nyxus.battery")
        self.connect("activate", self.on_activate)

    def on_activate(self, app):
        self.get_style_manager().set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        css = Gtk.CssProvider()
        css.load_from_data(
            b"""
            .nyxus-bh-card { background: rgba(10,13,20,0.85); border:1px solid rgba(58,216,255,0.18);
                             border-radius:12px; padding:14px; }
            .nyxus-bh-title { color:#e8edf5; font-weight:700; font-size:14px; }
            .nyxus-bh-status { color:#3ad8ff; font-weight:600; font-size:11px; letter-spacing:0.12em;
                               text-transform:uppercase; padding:2px 8px; border-radius:8px;
                               background:rgba(58,216,255,0.10); }
            .nyxus-bh-meta { color:#cfd6e2; font-size:12px; padding-top:2px; }
            .nyxus-bh-k { color:#7e8794; font-size:12px; }
            .nyxus-bh-v { color:#e8edf5; font-size:12px; font-family:monospace; }
            .nyxus-bh-empty { color:#7e8794; font-size:14px; padding:24px; }
            """
        )
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        BatteryWindow(self).present()


def main(argv=None) -> int:
    return BatteryApp().run(argv or [])


if __name__ == "__main__":
    raise SystemExit(main())
