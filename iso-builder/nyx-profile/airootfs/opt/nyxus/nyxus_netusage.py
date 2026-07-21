#!/usr/bin/env python3
"""
NYXUS Network Usage — libadwaita live per-interface traffic monitor.

DARK MIRROR rev r1

Reads /proc/net/dev directly (no daemon dependency):
    Rates           live RX/TX throughput per interface (1 s poll)
    Totals          bytes received / transmitted since boot
    Link state      operstate from /sys/class/net/<if>/operstate

Loopback is hidden by default. §9 empty states: if no non-loopback
interface exists the window shows an explicit "No network interfaces"
status page rather than a blank panel.

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import sys
import time
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

APP_ID = "io.nyxus.netusage"
PROC_NET_DEV = Path("/proc/net/dev")
REFRESH_SECONDS = 1


def read_counters() -> dict[str, tuple[int, int]]:
    """iface -> (rx_bytes, tx_bytes) from /proc/net/dev; loopback skipped."""
    counters: dict[str, tuple[int, int]] = {}
    try:
        lines = PROC_NET_DEV.read_text().splitlines()[2:]
    except OSError:
        return counters
    for line in lines:
        if ":" not in line:
            continue
        name, rest = line.split(":", 1)
        name = name.strip()
        if name == "lo":
            continue
        fields = rest.split()
        if len(fields) >= 9:
            try:
                counters[name] = (int(fields[0]), int(fields[8]))
            except ValueError:
                continue
    return counters


def operstate(iface: str) -> str:
    try:
        return (Path("/sys/class/net") / iface / "operstate").read_text().strip()
    except OSError:
        return "unknown"


def human_bytes(n: float) -> str:
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PiB"


def human_rate(bps: float) -> str:
    return f"{human_bytes(bps)}/s"


class NetUsageWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title="NYXUS Network Usage")
        self.set_default_size(600, 640)
        if HAS_CHROME:
            try:
                install_chrome(self, page_key="_netusage")
            except Exception:
                pass

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(Adw.HeaderBar())
        self.set_content(toolbar)

        self._scroller = Gtk.ScrolledWindow(vexpand=True)
        toolbar.set_content(self._scroller)

        self._prev = read_counters()
        self._prev_t = time.monotonic()
        self._rebuild({name: (0.0, 0.0) for name in self._prev})
        GLib.timeout_add_seconds(REFRESH_SECONDS, self._tick)

    def _tick(self) -> bool:
        now_counters = read_counters()
        now_t = time.monotonic()
        dt = max(now_t - self._prev_t, 1e-6)
        rates: dict[str, tuple[float, float]] = {}
        for name, (rx, tx) in now_counters.items():
            prx, ptx = self._prev.get(name, (rx, tx))
            rates[name] = (max(rx - prx, 0) / dt, max(tx - ptx, 0) / dt)
        self._prev, self._prev_t = now_counters, now_t
        self._rebuild(rates)
        return GLib.SOURCE_CONTINUE

    def _rebuild(self, rates: dict[str, tuple[float, float]]):
        counters = self._prev
        if not counters:
            status = Adw.StatusPage(
                icon_name="network-offline-symbolic",
                title="No network interfaces",
                description=("No non-loopback interfaces found in "
                             "/proc/net/dev. Check cabling, drivers, or "
                             "NetworkManager (nmtui / nm-connection-editor)."),
            )
            self._scroller.set_child(status)
            return

        page = Adw.PreferencesPage()
        for name in sorted(counters):
            rx_total, tx_total = counters[name]
            rx_rate, tx_rate = rates.get(name, (0.0, 0.0))
            group = Adw.PreferencesGroup(
                title=name, description=f"link: {operstate(name)}")
            rows = [
                ("Download", f"{human_rate(rx_rate)}  ·  {human_bytes(rx_total)} total"),
                ("Upload", f"{human_rate(tx_rate)}  ·  {human_bytes(tx_total)} total"),
            ]
            for label, value in rows:
                row = Adw.ActionRow(title=label)
                row.add_suffix(Gtk.Label(label=value, css_classes=["dim-label"]))
                group.add(row)
            page.add(group)
        self._scroller.set_child(page)


class NyxusNetUsage(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID)

    def do_activate(self):
        win = self.get_active_window() or NetUsageWindow(self)
        win.present()


if __name__ == "__main__":
    sys.exit(NyxusNetUsage().run(sys.argv))
