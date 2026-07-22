#!/usr/bin/env python3
"""
NYXUS Battery Health — libadwaita battery diagnostics panel.

DARK MIRROR rev r1

Reads /sys/class/power_supply/* directly (no daemon dependency):
    Charge          capacity %, charging status, time estimates
    Health          energy_full vs energy_full_design wear level
    Cycles          cycle_count (when the firmware exposes it)
    Power           instantaneous draw (power_now / current*voltage)

Desktop-safe (§9 empty states): machines with no battery (towers on
ethernet, VMs) get an explicit "No battery detected" status page
instead of a blank window — the app never crashes on missing sysfs
attributes; every read degrades to "—".

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, GLib, Adw  # noqa: E402

# ── NYXUS shared chrome (rainbow titles + graffiti walls, system-wide) ──
sys.path.insert(0, str(Path.home() / ".local" / "bin"))
sys.path.insert(0, "/opt/nyxus")
try:
    from nyxus_chrome import install_chrome  # type: ignore
    HAS_CHROME = True
except Exception:
    HAS_CHROME = False

APP_ID = "io.nyxus.battery"
PSU_ROOT = Path("/sys/class/power_supply")
REFRESH_SECONDS = 5


def _read(supply: Path, attr: str) -> str | None:
    try:
        return (supply / attr).read_text().strip()
    except OSError:
        return None


def _read_int(supply: Path, attr: str) -> int | None:
    raw = _read(supply, attr)
    if raw is None:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def find_batteries() -> list[Path]:
    if not PSU_ROOT.is_dir():
        return []
    out = []
    for supply in sorted(PSU_ROOT.iterdir()):
        if _read(supply, "type") == "Battery":
            out.append(supply)
    return out


def battery_snapshot(supply: Path) -> dict:
    """Collect one battery's stats; every field is optional."""
    snap: dict = {"name": supply.name}
    snap["status"] = _read(supply, "status") or "Unknown"
    snap["capacity"] = _read_int(supply, "capacity")
    snap["cycles"] = _read_int(supply, "cycle_count")
    snap["technology"] = _read(supply, "technology")
    snap["manufacturer"] = _read(supply, "manufacturer")
    snap["model"] = _read(supply, "model_name")

    # Health: full vs design, in either energy (µWh) or charge (µAh) units.
    full = _read_int(supply, "energy_full") or _read_int(supply, "charge_full")
    design = (_read_int(supply, "energy_full_design")
              or _read_int(supply, "charge_full_design"))
    snap["health"] = round(100 * full / design, 1) if full and design else None

    # Instantaneous draw: power_now (µW) or current_now*voltage_now (µA·µV).
    power = _read_int(supply, "power_now")
    if power is None:
        cur = _read_int(supply, "current_now")
        volt = _read_int(supply, "voltage_now")
        power = int(cur * volt / 1_000_000) if cur and volt else None
    snap["watts"] = round(power / 1_000_000, 2) if power else None
    return snap


def _fmt(value, suffix: str = "") -> str:
    return f"{value}{suffix}" if value is not None else "—"


class BatteryWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="NYXUS Battery Health")
        self.set_default_size(560, 640)
        if HAS_CHROME:
            try:
                install_chrome(self, page_key="_battery")
            except Exception:
                pass

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.set_content(toolbar)

        self._scroller = Gtk.ScrolledWindow(vexpand=True)
        toolbar.set_content(self._scroller)
        self._rebuild()
        GLib.timeout_add_seconds(REFRESH_SECONDS, self._tick)

    def _tick(self) -> bool:
        self._rebuild()
        return GLib.SOURCE_CONTINUE

    def _rebuild(self):
        batteries = find_batteries()
        if not batteries:
            status = Adw.StatusPage(
                icon_name="battery-missing-symbolic",
                title="No battery detected",
                description=("This machine has no battery exposed under "
                             "/sys/class/power_supply — desktops, servers "
                             "and most VMs land here. Nothing is wrong."),
            )
            self._scroller.set_child(status)
            return

        page = Adw.PreferencesPage()
        for supply in batteries:
            snap = battery_snapshot(supply)
            group = Adw.PreferencesGroup(title=snap["name"])
            model = " ".join(x for x in (snap["manufacturer"], snap["model"]) if x)
            if model:
                group.set_description(model)

            rows = [
                ("Charge", _fmt(snap["capacity"], " %")),
                ("Status", snap["status"]),
                ("Health (full vs design)", _fmt(snap["health"], " %")),
                ("Cycle count", _fmt(snap["cycles"])),
                ("Power draw", _fmt(snap["watts"], " W")),
                ("Technology", _fmt(snap["technology"])),
            ]
            for label, value in rows:
                row = Adw.ActionRow(title=label)
                row.add_suffix(Gtk.Label(label=value, css_classes=["dim-label"]))
                group.add(row)
            page.add(group)
        self._scroller.set_child(page)


class NyxusBattery(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.get_active_window() or BatteryWindow(self)
        win.present()


if __name__ == "__main__":
    sys.exit(NyxusBattery().run(sys.argv))
