"""
NYXUS Panel — System stats tile.

Live CPU / RAM / GPU / network stats refreshed every 5 s on a GLib timer.
GPU info comes from `nvidia-smi --query-gpu=...`.  Net I/O from psutil deltas.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import shutil
import subprocess
import time
from typing import Optional, Tuple

import gi

# ── NYXUS palette (single source of truth · rev r13) ────────────────
try:
    from nyxus_palette import (
        WHITE_PURE, WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        INK_FADED, INK_BLACK,
        GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE, HAIRLINE_INK,
        SHADOW_INK_ACTIVE, SHADOW_INK_INACTIVE,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
        format_css, assert_no_forbidden,
    )
except Exception:
    # palette module is shipped alongside every NYXUS app via
    # nyxus_install.sh; if it's missing, fall back to literals so
    # the app still launches.
    WHITE_PURE='#ffffff'; WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    INK_FADED='#0a0a0a'; INK_BLACK='#000000'
    GLASS_DARK='rgba(8, 12, 20, 0.55)'
    GLASS_DEEPER='rgba(15, 20, 32, 0.72)'
    GLASS_DEEPEST='rgba(5, 7, 12, 0.92)'
    HAIRLINE_WHITE='rgba(255, 255, 255, 0.10)'
    HAIRLINE_INK='rgba(0, 0, 0, 0.45)'
    SHADOW_INK_ACTIVE='rgba(0, 0, 0, 0.65)'
    SHADOW_INK_INACTIVE='rgba(0, 0, 0, 0.20)'
    RADIUS_CARD=14; RADIUS_PILL=12; RADIUS_INPUT=10
    FONT_UI='Inter'; FONT_MONO='JetBrains Mono'; FONT_DISPLAY='Inter Display'
    def format_css(t):
        _d = {
            'WHITE_PURE': WHITE_PURE, 'WHITE_OFF': WHITE_OFF,
            'GREY_LIGHT': GREY_LIGHT, 'GREY_MID': GREY_MID,
            'GREY_TERTIARY': GREY_TERTIARY,
            'INK_FADED': INK_FADED, 'INK_BLACK': INK_BLACK,
            'GLASS_DARK': GLASS_DARK, 'GLASS_DEEPER': GLASS_DEEPER,
            'GLASS_DEEPEST': GLASS_DEEPEST,
            'HAIRLINE_WHITE': HAIRLINE_WHITE, 'HAIRLINE_INK': HAIRLINE_INK,
            'SHADOW_INK_ACTIVE': SHADOW_INK_ACTIVE,
            'SHADOW_INK_INACTIVE': SHADOW_INK_INACTIVE,
            'RADIUS_CARD': RADIUS_CARD, 'RADIUS_PILL': RADIUS_PILL,
            'RADIUS_INPUT': RADIUS_INPUT,
            'FONT_UI': FONT_UI, 'FONT_MONO': FONT_MONO,
            'FONT_DISPLAY': FONT_DISPLAY,
        }
        return t.format_map(_d)
    def assert_no_forbidden(*a, **k): pass
# ─────────────────────────────────────────────────────────────────────

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

import psutil  # type: ignore


# ──────────────────────────────────────────────────── helpers
def _color_for(pct: float) -> str:
    if pct >= 80:
        return "nyxus-stat-red"
    if pct >= 50:
        return "nyxus-stat-yellow"
    return "nyxus-stat-green"


def _human_speed(bps: float) -> str:
    if bps >= 1024 * 1024:
        return f"{bps / (1024*1024):.1f} MB/s"
    if bps >= 1024:
        return f"{bps / 1024:.1f} KB/s"
    return f"{int(bps)} B/s"


def _nvidia_query() -> Optional[Tuple[float, float, str]]:
    """Return (gpu_util_pct, gpu_temp_c, gpu_name) or None if no GPU / nvidia-smi missing."""
    if not shutil.which("nvidia-smi"):
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,name",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2,
        )
        if out.returncode != 0:
            return None
        line = out.stdout.strip().splitlines()[0]
        parts = [p.strip() for p in line.split(",")]
        if len(parts) < 3:
            return None
        return float(parts[0]), float(parts[1]), parts[2]
    except (subprocess.TimeoutExpired, ValueError, OSError):
        return None


# ──────────────────────────────────────────────────── widget
class SystemWidget(Gtk.Box):
    """Tile that shows live CPU / RAM / GPU / Net stats."""

    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add_css_class("nyxus-tile")
        self.add_css_class("nyxus-tile-system")
        self.set_margin_top(0); self.set_margin_bottom(0)
        self.set_margin_start(0); self.set_margin_end(0)

        # header
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_top=10, margin_start=14, margin_end=14)
        ico = Gtk.Label(label="\uf2db")  # FA microchip
        ico.add_css_class("nyxus-tile-icon")
        title = Gtk.Label(label="System"); title.set_xalign(0); title.set_hexpand(True)
        title.add_css_class("nyxus-tile-title")
        self._stamp = Gtk.Label(label=""); self._stamp.add_css_class("nyxus-tile-stamp")
        hdr.append(ico); hdr.append(title); hdr.append(self._stamp)
        self.append(hdr)

        # rows
        self._cpu = self._stat_row("CPU",  "—",   "\uf85a")
        self._ram = self._stat_row("RAM",  "—",   "\uf538")
        self._gpu = self._stat_row("GPU",  "—",   "\uf109")
        self._net = self._stat_row("NET",  "↓ — ↑ —", "\uf6ff")

        for r in (self._cpu, self._ram, self._gpu, self._net):
            self.append(r["row"])

        # state for net delta
        self._last_net = psutil.net_io_counters()
        self._last_t   = time.monotonic()
        self._gpu_present = _nvidia_query() is not None

        # initial paint then schedule
        self._refresh()
        self._timer_id = GLib.timeout_add_seconds(5, self._refresh)

    def _stat_row(self, label: str, value: str, glyph: str):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_start=14, margin_end=14, margin_top=2)
        ico = Gtk.Label(label=glyph); ico.add_css_class("nyxus-stat-icon")
        lbl = Gtk.Label(label=label); lbl.set_xalign(0); lbl.add_css_class("nyxus-stat-label")
        lbl.set_size_request(46, -1)
        bar = Gtk.LevelBar(); bar.set_min_value(0); bar.set_max_value(100)
        bar.add_offset_value(Gtk.LEVEL_BAR_OFFSET_LOW,  50)
        bar.add_offset_value(Gtk.LEVEL_BAR_OFFSET_HIGH, 80)
        bar.add_offset_value(Gtk.LEVEL_BAR_OFFSET_FULL, 100)
        bar.set_hexpand(True)
        bar.add_css_class("nyxus-stat-bar")
        val = Gtk.Label(label=value); val.set_xalign(1); val.add_css_class("nyxus-stat-value")
        val.set_size_request(110, -1)
        row.append(ico); row.append(lbl); row.append(bar); row.append(val)
        return {"row": row, "bar": bar, "val": val}

    def _set(self, widget, pct: float, text: str) -> None:
        widget["bar"].set_value(max(0.0, min(100.0, pct)))
        widget["val"].set_text(text)
        for c in ("nyxus-stat-green", "nyxus-stat-yellow", "nyxus-stat-red"):
            widget["val"].remove_css_class(c)
        widget["val"].add_css_class(_color_for(pct))

    def _refresh(self) -> bool:
        # CPU
        cpu = psutil.cpu_percent(interval=None)
        self._set(self._cpu, cpu, f"{cpu:>5.1f} %")

        # RAM
        m = psutil.virtual_memory()
        used_gb = m.used / (1024**3); total_gb = m.total / (1024**3)
        self._set(self._ram, m.percent, f"{used_gb:.1f} / {total_gb:.1f} GB")

        # GPU
        if self._gpu_present:
            q = _nvidia_query()
            if q is not None:
                util, temp, _name = q
                self._set(self._gpu, util, f"{util:>4.0f} %  {temp:.0f}°C")
            else:
                self._set(self._gpu, 0, "n/a")
        else:
            self._set(self._gpu, 0, "no NVIDIA")

        # NET
        now = time.monotonic()
        n = psutil.net_io_counters()
        dt = max(0.001, now - self._last_t)
        rx = (n.bytes_recv - self._last_net.bytes_recv) / dt
        tx = (n.bytes_sent - self._last_net.bytes_sent) / dt
        self._last_net = n; self._last_t = now
        # use the higher of the two for the bar (% of 50 MB/s)
        peak = max(rx, tx)
        pct  = min(100.0, peak / (50 * 1024 * 1024) * 100.0)
        self._set(self._net, pct, f"↓ {_human_speed(rx)}  ↑ {_human_speed(tx)}")

        self._stamp.set_text(time.strftime("%H:%M:%S"))
        return True  # keep scheduled

    def stop(self) -> None:
        if hasattr(self, "_timer_id") and self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = 0


__all__ = ["SystemWidget"]
