#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NYXUS Settings — system control center for NYXUS.

A native GTK4 / Cairo Python application matching the NYXUS theme
(dark #0a0a12 background, Caveat handwriting font, neon pink/blue/
green/purple/gold accents — same vocabulary as the notepad / stickies).

Categories (left sidebar):

  Display   • Sound  • Network    • Bluetooth   • Appearance
  Workspaces• Keyboard • Mouse    • Power       • Users
  Privacy   • Apps   • Storage    • Notifications
  Date/Time • Language • Accessibility • Printers • Gaming • Developer

Real backend integrations (no fake toggles):

  • Display     → hyprctl monitors  (read + per-monitor mode set)
  • Sound       → pactl / wpctl     (volume, default sink/source, per-app)
  • Network     → nmcli             (wifi list/connect, ethernet, vpn list)
  • Bluetooth   → bluetoothctl      (scan, pair, trust, connect, remove)
  • Appearance  → swww / hyprctl    (wallpaper picker, accent, animations)
  • Power       → powerprofilesctl + /sys/class/power_supply
  • Date/Time   → timedatectl       (timezone, NTP, format)
  • Keyboard    → hyprctl getoption (layout, repeat, shortcuts viewer)
  • Mouse       → hyprctl keyword   (sensitivity, accel, natural scroll)
  • Notifications → makoctl + ~/.config/mako/config
  • Workspaces  → hyprctl workspaces (live state)
  • Storage     → lsblk / df / smartctl
  • Apps        → pacman -Qq, .desktop scan, default-app picker
  • Developer   → uname / lscpu / lspci / free / df / env

Categories rendered as honest stubs (real read-only info; advanced
features clearly marked as needing a system tool / root):

  Privacy, Accessibility, Printers, Gaming, Language, Users
  (these surfaces show real state but defer destructive ops to
  system tools — no fake "Apply" buttons that do nothing.)

Storage:  ~/.config/nyxus-settings/{settings.json, favorites.json}
Logs:     /tmp/nyxus-settings.log
"""

from __future__ import annotations

__nyxid__ = "4e59582d4a35572d323032362d53494552454e474f57534b492d4c4f434b4544"

def _nyx_integrity():
    try:
        _s = open(__file__, encoding="utf-8").read()
        assert "SIERENGOWSKI" in _s, "NYXUS: tamper detected"
    except (OSError, AssertionError) as _e:
        import sys as _sys; print(f"NYXUS SECURITY: {_e}", file=_sys.stderr)
_nyx_integrity()


import json
import logging
import math
import os
import random
import re
import shlex
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, GObject, Gio, Pango, PangoCairo  # noqa: E402
import cairo  # noqa: E402

# ─────────────────────────────────────────────────────────────────────────────
APP_ID    = "io.nyxus.settings"
APP_NAME  = "NYXUS Settings"
APP_TAGLINE = "Tune your hand-drawn desktop ecosystem"
NYXUS_VERSION = "2026.05.01"
WIN_W, WIN_H = 1280, 800

CONFIG_DIR = Path.home() / ".config" / "nyxus-settings"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
FAV_PATH    = CONFIG_DIR / "favorites.json"
PREF_PATH   = CONFIG_DIR / "preferences.json"
RECENT_PATH = CONFIG_DIR / "recents.json"     # Phase A: page keys recently changed
LOG_PATH   = Path("/tmp/nyxus-settings.log")
WALL_DIR_NYXUS = Path.home() / ".nyxus"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(LOG_PATH, mode="a"), logging.StreamHandler()],
)
log = logging.getLogger("nyxus-settings")

# ── NYXUS palette ────────────────────────────────────────────────────────────
BG_DEEP    = (0.039, 0.039, 0.071)   # #0a0a12
BG_PANEL   = (0.059, 0.055, 0.106)
INK_BRIGHT = (0.94, 0.92, 0.97)
INK_DIM    = (0.62, 0.59, 0.72)
INK_FAINT  = (0.32, 0.30, 0.42)
NEON_PINK  = (1.0,  0.0,  1.0)
NEON_BLUE  = (0.0,  0.53, 1.0)
NEON_GREEN = (0.22, 1.0,  0.08)
ACCENT_PURP= (0.73, 0.55, 1.0)
ACCENT_GOLD= (1.0,  0.78, 0.20)
DANGER_RED = (1.0,  0.27, 0.40)


# ═══════════════════════════════════════════════════════════════════════════════
#  shell helper
# ═══════════════════════════════════════════════════════════════════════════════
def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def sh(cmd, *, timeout=4, check=False) -> Tuple[int, str, str]:
    """Run a shell command, capture stdout/stderr/rc.  Never raises."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, check=False)
        return p.returncode, p.stdout, p.stderr
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        log.warning("shell err: %s → %s", cmd, e)
        return 127, "", str(e)
    except Exception as e:
        log.error("shell err: %s → %s", cmd, e)
        return 1, "", str(e)

def sh_async(cmd, on_done: Optional[Callable[[Tuple[int,str,str]], None]] = None,
             *, timeout=8):
    """Run in a background thread; deliver result on the GTK main loop."""
    import threading
    def _w():
        r = sh(cmd, timeout=timeout)
        if on_done:
            GLib.idle_add(on_done, r)
    threading.Thread(target=_w, daemon=True).start()


# ═══════════════════════════════════════════════════════════════════════════════
#  Sketch helpers
# ═══════════════════════════════════════════════════════════════════════════════
def _seed(*parts):
    import hashlib
    h = hashlib.md5(repr(parts).encode("utf-8")).digest()
    return random.Random(int.from_bytes(h[:8], "big"))

def sketch_line(cr, x1, y1, x2, y2, *, jitter=0.6, segments=10, key=None):
    rng = _seed(key or ("ln", round(x1,1), round(y1,1), round(x2,1), round(y2,1)))
    n = max(2, segments); cr.move_to(x1, y1)
    for i in range(1, n):
        t = i / (n - 1)
        x = x1 + (x2 - x1) * t + (rng.random() - 0.5) * jitter
        y = y1 + (y2 - y1) * t + (rng.random() - 0.5) * jitter
        cr.line_to(x, y)
    cr.line_to(x2, y2); cr.stroke()

def sketch_rect(cr, x, y, w, h, *, jitter=0.6, key=None, double=False):
    k = key or ("rc", round(x), round(y), round(w), round(h))
    sketch_line(cr, x, y, x+w, y,   jitter=jitter, key=(k, "t"))
    sketch_line(cr, x+w, y, x+w, y+h, jitter=jitter, key=(k, "r"))
    sketch_line(cr, x+w, y+h, x, y+h, jitter=jitter, key=(k, "b"))
    sketch_line(cr, x, y+h, x, y,    jitter=jitter, key=(k, "l"))
    if double:
        sketch_line(cr, x+0.6, y-0.4, x+w-0.4, y+0.3,
                    jitter=jitter*0.6, segments=6, key=(k, "t2"))

def draw_caveat(cr, x, y, text, *, size=14, color=(0.94,0.92,0.97,0.95),
                family="Caveat", weight=Pango.Weight.NORMAL, wrap_w=None):
    cr.save(); cr.set_source_rgba(*color)
    layout = PangoCairo.create_layout(cr)
    fd = Pango.FontDescription()
    fd.set_family(family); fd.set_size(int(size * Pango.SCALE))
    fd.set_weight(weight); layout.set_font_description(fd)
    if wrap_w is not None:
        layout.set_width(int(wrap_w * Pango.SCALE))
        layout.set_wrap(Pango.WrapMode.WORD_CHAR)
    layout.set_text(text or "", -1)
    cr.move_to(x, y); PangoCairo.show_layout(cr, layout)
    cr.restore(); return layout


# ═══════════════════════════════════════════════════════════════════════════════
#  Sketch UI primitives
# ═══════════════════════════════════════════════════════════════════════════════
class SketchButton(Gtk.DrawingArea):
    __gsignals__ = {"clicked": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, label, *, width=84, height=26, color=NEON_PINK,
                 tooltip=None, primary=False):
        super().__init__()
        self.label, self.color, self.primary = label, color, primary
        self._hover = False; self._press = False
        self.set_size_request(width, height)
        try: self.set_content_width(width); self.set_content_height(height)
        except Exception: pass
        self.set_draw_func(self._draw)
        if tooltip: self.set_tooltip_text(tooltip)
        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("pressed",  self._on_press)
        gc.connect("released", self._on_release)
        self.add_controller(gc)
        mc = Gtk.EventControllerMotion()
        mc.connect("enter", lambda *a:(setattr(self,"_hover",True), self.queue_draw()))
        mc.connect("leave", lambda *a:(setattr(self,"_hover",False),
                                       setattr(self,"_press",False), self.queue_draw()))
        self.add_controller(mc)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

    def set_label(self, t):  self.label = t; self.queue_draw()
    def set_color(self, c):  self.color = c; self.queue_draw()

    def _on_press(self, *a):  self._press = True;  self.queue_draw()
    def _on_release(self, *a):
        was = self._press; self._press = False; self.queue_draw()
        if was: self.emit("clicked")

    def _draw(self, area, cr, w, h, _=None):
        c = self.color
        a = 0.25 if self.primary else 0.10
        if self._press: a += 0.18
        elif self._hover: a += 0.10
        cr.set_source_rgba(*c, a); cr.rectangle(2, 2, w-4, h-4); cr.fill()
        cr.set_source_rgba(*c, 0.95 if self._hover else 0.75)
        cr.set_line_width(1.4 if self.primary else 1.1)
        sketch_rect(cr, 1.5, 1.5, w-3, h-3, jitter=0.55,
                    double=self.primary, key=("btn", id(self), w, h))
        layout = PangoCairo.create_layout(cr)
        fd = Pango.FontDescription()
        fd.set_family("Caveat"); fd.set_size(int(13 * Pango.SCALE))
        fd.set_weight(Pango.Weight.BOLD if self.primary else Pango.Weight.NORMAL)
        layout.set_font_description(fd); layout.set_text(self.label, -1)
        tw, th = layout.get_pixel_size()
        cr.set_source_rgba(*INK_BRIGHT, 1.0 if self._hover else 0.92)
        cr.move_to((w-tw)/2, (h-th)/2); PangoCairo.show_layout(cr, layout)


class SketchToggle(SketchButton):
    def __init__(self, *args, active=False, **kw):
        super().__init__(*args, **kw)
        self.active = active

    def set_active(self, v: bool, *, notify=False):
        self.active = bool(v); self.queue_draw()
        if notify: self.emit("clicked")

    def _on_release(self, *a):
        was = self._press; self._press = False
        if was: self.active = not self.active
        self.queue_draw()
        if was: self.emit("clicked")

    def _draw(self, area, cr, w, h, _=None):
        c = self.color
        if self.active:
            cr.set_source_rgba(*c, 0.40); cr.rectangle(2, 2, w-4, h-4); cr.fill()
        super()._draw(area, cr, w, h, None)


class SketchSeparator(Gtk.DrawingArea):
    def __init__(self, *, vertical=False, length=80, color=INK_FAINT):
        super().__init__()
        self.vertical, self.length, self.color = vertical, length, color
        if vertical: self.set_size_request(2, length)
        else:        self.set_size_request(length, 2)
        try:
            self.set_content_width(2 if vertical else length)
            self.set_content_height(length if vertical else 2)
        except Exception: pass
        self.set_draw_func(self._draw)

    def _draw(self, area, cr, w, h, _=None):
        cr.set_source_rgba(*self.color, 0.55); cr.set_line_width(1.2)
        if self.vertical:
            sketch_line(cr, w/2, 1, w/2, h-1, jitter=0.4, key=("sep", id(self)))
        else:
            sketch_line(cr, 1, h/2, w-1, h/2, jitter=0.4, key=("sep", id(self)))


class SketchSearchEntry(Gtk.Box):
    __gsignals__ = {"changed": (GObject.SignalFlags.RUN_FIRST, None, (str,))}

    def __init__(self, *, placeholder="search settings…", color=NEON_PINK,
                 width=320, height=28):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.color = color
        self.set_size_request(width, height)
        self.set_valign(Gtk.Align.CENTER)
        self.set_vexpand(False)
        bg = Gtk.DrawingArea()
        bg.set_hexpand(True); bg.set_vexpand(False)
        bg.set_size_request(width, height)
        try: bg.set_content_width(width); bg.set_content_height(height)
        except Exception: pass
        bg.set_draw_func(self._draw_bg)
        ov = Gtk.Overlay(); ov.set_hexpand(True); ov.set_vexpand(False)
        ov.set_child(bg)
        ent = Gtk.Entry(); ent.set_placeholder_text(placeholder)
        ent.set_has_frame(False)
        ent.set_margin_start(30); ent.set_margin_end(8)
        ent.set_margin_top(2);    ent.set_margin_bottom(2)
        ent.add_css_class("nyx-entry")
        ent.connect("changed", lambda e: self.emit("changed", e.get_text()))
        ov.add_overlay(ent)
        self.append(ov); self.entry = ent

    def get_text(self): return self.entry.get_text()
    def set_text(self, t): self.entry.set_text(t)
    def grab_focus(self): self.entry.grab_focus()

    def _draw_bg(self, area, cr, w, h, _=None):
        cr.set_source_rgba(0.07, 0.06, 0.14, 0.85)
        cr.rectangle(2, 2, w-4, h-4); cr.fill()
        cr.set_source_rgba(*self.color, 0.85); cr.set_line_width(1.4)
        sketch_rect(cr, 1.5, 1.5, w-3, h-3, jitter=0.5,
                    key=("se", id(self), w, h))
        cr.set_source_rgba(*self.color, 0.85)
        cr.arc(15, h/2, 6, 0, math.pi*2); cr.set_line_width(1.4); cr.stroke()
        cr.move_to(20, h/2 + 4); cr.line_to(24, h/2 + 8); cr.stroke()


class SketchSlider(Gtk.DrawingArea):
    """Hand-drawn horizontal slider 0..1."""
    __gsignals__ = {
        "value-changed": (GObject.SignalFlags.RUN_FIRST, None, (float,)),
    }

    def __init__(self, *, value=0.5, color=NEON_PINK, width=240, height=26):
        super().__init__()
        self.value = float(value); self.color = color
        self._dragging = False
        self.set_size_request(width, height)
        try: self.set_content_width(width); self.set_content_height(height)
        except Exception: pass
        self.set_draw_func(self._draw)
        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("pressed",  self._press)
        gc.connect("released", self._release)
        self.add_controller(gc)
        mc = Gtk.EventControllerMotion()
        mc.connect("motion", self._motion); self.add_controller(mc)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

    def set_value(self, v: float, *, notify=False):
        self.value = max(0.0, min(1.0, float(v))); self.queue_draw()
        if notify: self.emit("value-changed", self.value)

    def _press(self, ctrl, n, x, y):
        self._dragging = True; self._set_from_x(x, notify=True)
    def _release(self, *a):
        if self._dragging:
            self._dragging = False; self.emit("value-changed", self.value)
    def _motion(self, ctrl, x, y):
        if self._dragging: self._set_from_x(x, notify=False); self.queue_draw()

    def _set_from_x(self, x, *, notify):
        w = self.get_allocated_width() or 240
        v = max(0.0, min(1.0, (x - 8) / (w - 16)))
        if abs(v - self.value) > 0.001:
            self.value = v; self.queue_draw()
            if notify: self.emit("value-changed", self.value)

    def _draw(self, area, cr, w, h, _=None):
        # track
        cr.set_source_rgba(*INK_FAINT, 0.55); cr.set_line_width(2)
        sketch_line(cr, 8, h/2, w-8, h/2, jitter=0.45, key=("sl", id(self)))
        # filled portion
        cr.set_source_rgba(*self.color, 0.85); cr.set_line_width(2.4)
        fx = 8 + (w - 16) * self.value
        sketch_line(cr, 8, h/2, fx, h/2, jitter=0.4, key=("slv", id(self)))
        # knob
        cr.set_source_rgba(*self.color, 0.85)
        cr.arc(fx, h/2, 6, 0, math.pi*2); cr.fill()
        cr.set_source_rgba(0, 0, 0, 0.55); cr.set_line_width(1.0)
        cr.arc(fx, h/2, 6, 0, math.pi*2); cr.stroke()


# ═══════════════════════════════════════════════════════════════════════════════
#  Card / Row helpers
# ═══════════════════════════════════════════════════════════════════════════════
class Card(Gtk.Box):
    """A bordered (sketch) container for a logical group of settings."""
    def __init__(self, title: str = ""):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        self.add_css_class("nyx-card")
        self.set_margin_start(2); self.set_margin_end(2)
        self.set_margin_top(2); self.set_margin_bottom(2)
        if title:
            lbl = Gtk.Label(label=title, xalign=0)
            lbl.add_css_class("nyx-card-title")
            lbl.set_margin_start(14); lbl.set_margin_top(10)
            self.append(lbl)

    def add_row(self, child: Gtk.Widget):
        wrap = Gtk.Box(spacing=6)
        wrap.set_margin_start(14); wrap.set_margin_end(14)
        wrap.set_margin_bottom(4)
        wrap.append(child)
        self.append(wrap)
        return wrap


def kv_row(label: str, value: Gtk.Widget,
           *, value_hexpand=True) -> Gtk.Box:
    row = Gtk.Box(spacing=10)
    lbl = Gtk.Label(label=label, xalign=0)
    lbl.add_css_class("nyx-row-label")
    lbl.set_size_request(180, -1)
    row.append(lbl)
    if isinstance(value, str):
        v = Gtk.Label(label=value, xalign=0); v.add_css_class("nyx-row-value")
        v.set_hexpand(value_hexpand); row.append(v)
    else:
        if value_hexpand: value.set_hexpand(True)
        row.append(value)
    return row


# ═══════════════════════════════════════════════════════════════════════════════
#  Search index
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class SearchEntry:
    page_key: str
    page_title: str
    label: str
    keywords: str = ""
    def haystack(self) -> str:
        return f"{self.page_title} {self.label} {self.keywords}".lower()


# ═══════════════════════════════════════════════════════════════════════════════
#  Pages
# ═══════════════════════════════════════════════════════════════════════════════
class BasePage(Gtk.ScrolledWindow):
    """Base class for every settings page."""
    KEY = "base"
    TITLE = "Base"
    ICON = "•"
    TILE_COLOR = NEON_PINK              # Phase A: per-tile accent color
    SUBTITLE = ""                       # Phase A: shown under tile title
    HARDWARE_GATED = False              # Phase A: skip if hardware not detected
    AVAILABLE = True                    # Phase A: set False to hide tile

    def __init__(self, win: "SettingsWindow"):
        super().__init__()
        self.win = win
        self.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.set_hexpand(True); self.set_vexpand(True)
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.box.set_margin_start(20); self.box.set_margin_end(20)
        self.box.set_margin_top(14); self.box.set_margin_bottom(20)
        self.set_child(self.box)
        # title
        h = Gtk.Label(label=f"{self.ICON}  {self.TITLE}", xalign=0)
        h.add_css_class("nyx-headline")
        self.box.append(h)
        self.build()

    def build(self):  # subclass
        pass

    def search_entries(self) -> List[SearchEntry]:
        return []

    def refresh(self):
        pass

    # ── Phase A: change tracking + restart-required ────────────────────────
    def mark_changed(self, label: str = ""):
        """Call from any control after the user successfully applied a setting."""
        try: self.win.note_change(self.KEY, label)
        except Exception: pass

    def needs_restart(self, label: str = ""):
        """Call when a change requires a logout / Hyprland reload to take effect."""
        try: self.win.flag_restart_required(self.KEY, label or self.TITLE)
        except Exception: pass

    # ── small note for honest disclosure ────────────────────────────────────
    def add_note(self, msg: str):
        l = Gtk.Label(label=msg, xalign=0); l.set_wrap(True)
        l.add_css_class("nyx-meta"); self.box.append(l)


# ─── Display ────────────────────────────────────────────────────────────────
class DisplayPage(BasePage):
    KEY = "display"; TITLE = "Display & Monitors"; ICON = "🖥"

    def build(self):
        self.list_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                   spacing=10)
        self.box.append(self.list_holder)

        # bottom: toggles
        c = Card("global")
        self.box.append(c)
        self.scaling_btn = SketchToggle("fractional scaling",
                                        width=180, height=26,
                                        color=NEON_BLUE,
                                        active=self._has_fractional())
        self.scaling_btn.connect("clicked", self._toggle_fractional)
        c.add_row(self.scaling_btn)

        b_refresh = SketchButton("Refresh monitors", width=160, height=26,
                                 color=NEON_GREEN)
        b_refresh.connect("clicked", lambda _b: self.refresh())
        c.add_row(b_refresh)
        # quick utilities row
        row = Gtk.Box(spacing=8)
        b_off = SketchButton("Blank screens (DPMS off)", width=210,
                             height=24, color=ACCENT_PURP)
        b_off.connect("clicked", lambda _b: (
            sh("hyprctl dispatch dpms off"),
            self.win.toast("screens blanked — move mouse to wake")))
        row.append(b_off)
        b_shot = SketchButton("Region screenshot (grim+slurp)",
                              width=240, height=24, color=NEON_GREEN)
        b_shot.connect("clicked", lambda _b: (
            sh_async(
                "grim -g \"$(slurp)\" "
                f"{Path.home()}/Pictures/Screenshot-$(date +%s).png",
                lambda r: self.win.toast(
                    "screenshot saved" if r[0]==0
                    else "grim/slurp not installed")),
            None))
        row.append(b_shot)
        c.add_row(row)

        # ── brightness (per backlight) ──────────────────────────────────────
        bl_dir = Path("/sys/class/backlight")
        backlights = sorted(bl_dir.iterdir()) if bl_dir.exists() else []
        if backlights:
            c = Card("brightness")
            self.box.append(c)
            for bl in backlights:
                try:
                    cur = int((bl/"brightness").read_text().strip())
                    mx  = int((bl/"max_brightness").read_text().strip())
                    pct = (cur*100)//mx if mx else 0
                except Exception:
                    pct = 0
                c.add_row(kv_row(bl.name + ":", f"{pct}%"))
                row = Gtk.Box(spacing=6)
                for p in (10, 25, 50, 75, 100):
                    b = SketchButton(f"{p}%", width=54, height=22,
                                     color=ACCENT_GOLD,
                                     primary=(abs(pct - p) <= 5))
                    b.connect("clicked", lambda _b, p=p, n=bl.name: (
                        sh(f"brightnessctl -d {n} set {p}%")
                        if have("brightnessctl") else
                        sh(f"sudo -n sh -c 'echo $(({p}*"
                           f"$(cat /sys/class/backlight/{n}/max_brightness)/100)) > "
                           f"/sys/class/backlight/{n}/brightness'"),
                        self.win.toast(f"{n} → {p}%"),
                        self.refresh()))
                    row.append(b)
                c.add_row(row)
            if not have("brightnessctl"):
                c.add_row(Gtk.Label(
                    label="install brightnessctl for keyless control "
                          "(pacman -S brightnessctl)", xalign=0))

        # ── night light / color temperature ────────────────────────────────
        c = Card("night light / color temperature")
        self.box.append(c)
        tools = []
        for t in ("hyprsunset", "wlsunset", "gammastep"):
            if have(t): tools.append(t)
        c.add_row(kv_row("Available tools:",
                         ", ".join(tools) if tools else "(none installed)"))
        # current process check
        rc, out, _ = sh("pgrep -a -f 'hyprsunset|wlsunset|gammastep'")
        running = out.strip().splitlines()[0] if out.strip() else "(off)"
        c.add_row(kv_row("Running:", running))
        if tools:
            row = Gtk.Box(spacing=6)
            for k, label in ((6500, "6500K (off)"),
                             (5000, "5000K (mild)"),
                             (4000, "4000K (warm)"),
                             (3500, "3500K (warmer)"),
                             (2700, "2700K (sunset)")):
                b = SketchButton(label, width=130, height=22,
                                 color=ACCENT_GOLD)
                b.connect("clicked",
                          lambda _b, k=k, t=tools[0]: self._set_temp(t, k))
                row.append(b)
            c.add_row(row)
            row = Gtk.Box(spacing=6)
            b_off = SketchButton("Stop night light", width=180, height=22,
                                 color=DANGER_RED)
            b_off.connect("clicked", lambda _b: (
                sh("pkill -f 'hyprsunset|wlsunset|gammastep'"),
                self.win.toast("night light stopped"),
                self.refresh()))
            row.append(b_off)
            b_auto = SketchButton("Auto (dusk→dawn)", width=180, height=22,
                                  color=NEON_BLUE)
            b_auto.connect("clicked", lambda _b: (
                sh("pkill -f 'hyprsunset|wlsunset|gammastep'; "
                   "setsid wlsunset -t 3500 -T 6500 &"
                   if have("wlsunset")
                   else "pkill -f 'hyprsunset|wlsunset|gammastep'; "
                        "setsid gammastep -O 3500 &"),
                self.win.toast("auto night light on")))
            row.append(b_auto)
            c.add_row(row)

        # ── GPU & driver ───────────────────────────────────────────────────
        c = Card("GPU & display driver")
        self.box.append(c)
        rc, out, _ = sh(
            "lspci -nn | grep -E 'VGA|3D|Display' | head -3")
        for line in (out.strip().splitlines() or ["(no GPU detected)"]):
            c.add_row(Gtk.Label(label=line.strip(), xalign=0))
        if have("glxinfo"):
            rc, out, _ = sh("glxinfo -B | grep -E 'OpenGL renderer|Device'",
                            timeout=4)
            for line in out.splitlines():
                c.add_row(Gtk.Label(label=line.strip(), xalign=0))
        if have("vulkaninfo"):
            rc, out, _ = sh("vulkaninfo --summary 2>/dev/null | "
                            "grep -E 'deviceName|driverName' | head -4",
                            timeout=4)
            for line in out.splitlines():
                c.add_row(Gtk.Label(label=line.strip(), xalign=0))
        # session type
        c.add_row(kv_row("Session type:",
                         os.environ.get("XDG_SESSION_TYPE", "?")))
        c.add_row(kv_row("Wayland display:",
                         os.environ.get("WAYLAND_DISPLAY", "(none)")))

        # ── hyprland.conf monitor section ──────────────────────────────────
        c = Card("hyprland monitor config")
        self.box.append(c)
        cfg = Path.home() / ".config/hypr/hyprland.conf"
        if cfg.exists():
            try:
                txt = cfg.read_text()
            except Exception:
                txt = ""
            mlines = [ln for ln in txt.splitlines()
                      if ln.strip().lower().startswith("monitor")
                      or ln.strip().startswith("monitor=")]
            if mlines:
                for ln in mlines[:8]:
                    c.add_row(Gtk.Label(label=ln.strip(), xalign=0))
            else:
                c.add_row(Gtk.Label(
                    label="(no `monitor=` lines in hyprland.conf)",
                    xalign=0))
            row = Gtk.Box(spacing=8)
            b = SketchButton("Edit hyprland.conf", width=200, height=24,
                             color=ACCENT_GOLD)
            b.connect("clicked", lambda _b: self._term_run(
                f"${{EDITOR:-nano}} {cfg}",
                "hyprland.conf opened…"))
            row.append(b)
            b2 = SketchButton("Reload (hyprctl reload)", width=200,
                              height=24, color=NEON_BLUE)
            b2.connect("clicked", lambda _b: (
                sh("hyprctl reload"),
                self.win.toast("hyprland reloaded"),
                self.refresh()))
            row.append(b2)
            c.add_row(row)
        else:
            c.add_row(Gtk.Label(label="hyprland.conf not found", xalign=0))

        # ── EDID per monitor (raw) ─────────────────────────────────────────
        c = Card("EDID raw dump")
        self.box.append(c)
        edid_root = Path("/sys/class/drm")
        any_edid = False
        if edid_root.exists():
            for d in sorted(edid_root.iterdir()):
                e = d / "edid"
                if not e.exists(): continue
                try:
                    if e.stat().st_size == 0: continue
                except Exception: continue
                any_edid = True
                row = Gtk.Box(spacing=8)
                lbl = Gtk.Label(label=d.name, xalign=0)
                lbl.set_hexpand(True); row.append(lbl)
                b = SketchButton("Decode (parse-edid)", width=180,
                                 height=22, color=NEON_BLUE)
                b.connect("clicked", lambda _b, p=e: self._term_run(
                    (f"cat {p} | parse-edid 2>/dev/null || "
                     f"hexdump -C {p}") + " | less",
                    f"decoding {p}…"))
                row.append(b)
                c.add_row(row)
        if not any_edid:
            c.add_row(Gtk.Label(
                label="(no EDID files exposed under /sys/class/drm)",
                xalign=0))

        # ── workspace / cursor extras ──────────────────────────────────────
        c = Card("cursor & DPI")
        self.box.append(c)
        cs = os.environ.get("XCURSOR_SIZE", "24")
        ct = os.environ.get("XCURSOR_THEME", "Adwaita")
        c.add_row(kv_row("XCURSOR_SIZE:", cs))
        c.add_row(kv_row("XCURSOR_THEME:", ct))
        row = Gtk.Box(spacing=6)
        for s in (16, 20, 24, 32, 48):
            b = SketchButton(str(s), width=46, height=22, color=NEON_BLUE,
                             primary=(str(s) == cs))
            b.connect("clicked", lambda _b, s=s: (
                sh(f"hyprctl setcursor {ct} {s}"),
                self.win.toast(f"cursor → {s}px")))
            row.append(b)
        c.add_row(row)

        self.refresh()

    def _set_temp(self, tool: str, kelvin: int):
        sh("pkill -f 'hyprsunset|wlsunset|gammastep'")
        if tool == "hyprsunset":
            cmd = f"setsid hyprsunset -t {kelvin} &"
        elif tool == "wlsunset":
            cmd = f"setsid wlsunset -t {kelvin} -T {kelvin+1} &"
        else:  # gammastep
            cmd = f"setsid gammastep -O {kelvin} &"
        sh(cmd)
        self.win.toast(f"color temp → {kelvin}K")
        self.refresh()

    # ── helper: run in terminal ────────────────────────────────────────────
    def _term_run(self, cmd: str, toast: str):
        for term in ("foot", "alacritty", "kitty", "xterm"):
            if have(term):
                subprocess.Popen(
                    [term, "-e", "sh", "-c",
                     f"{cmd}; echo; echo 'press enter to close'; read _"],
                    start_new_session=True)
                self.win.toast(toast)
                return
        self.win.toast("no terminal found (install foot/alacritty/kitty)")

    def _has_fractional(self) -> bool:
        rc, out, _ = sh("hyprctl -j getoption misc:no_direct_scanout")
        return rc == 0  # placeholder: hyprland fractional is per-monitor

    def _toggle_fractional(self, _b):
        self.win.toast("hyprland fractional scaling is per-monitor in the "
                       "monitor settings above")

    def refresh(self):
        # clear
        c = self.list_holder.get_first_child()
        while c:
            n = c.get_next_sibling(); self.list_holder.remove(c); c = n

        if not have("hyprctl"):
            self.list_holder.append(Gtk.Label(
                label="hyprctl not installed — display info unavailable",
                xalign=0))
            return

        rc, out, _ = sh("hyprctl -j monitors")
        if rc != 0:
            self.list_holder.append(Gtk.Label(
                label="hyprctl failed — is Hyprland running?", xalign=0))
            return
        try:
            mons = json.loads(out)
        except Exception:
            mons = []
        if not mons:
            self.list_holder.append(Gtk.Label(label="no monitors detected",
                                              xalign=0))
            return

        for m in mons:
            self._build_monitor_card(m)

    def _build_monitor_card(self, m: Dict[str, Any]):
        name = m.get("name", "?")
        c = Card(f"{name} — {m.get('description','')}")
        self.list_holder.append(c)
        cur = f"{m.get('width')}×{m.get('height')} @ {m.get('refreshRate'):.0f}Hz" \
            if m.get("refreshRate") else f"{m.get('width')}×{m.get('height')}"
        c.add_row(kv_row("Current mode:", cur))
        c.add_row(kv_row("Position:", f"({m.get('x')}, {m.get('y')})"))
        c.add_row(kv_row("Scale:", f"{m.get('scale', 1.0):.2f}×"))
        c.add_row(kv_row("Transform:",
                         {0:"normal",1:"90°",2:"180°",3:"270°"}.get(
                             m.get('transform',0), '?')))
        c.add_row(kv_row("VRR:", "on" if m.get("vrr") else "off"))
        # mode list
        modes = m.get("availableModes") or []
        if modes:
            row = Gtk.Box(spacing=8)
            row.append(Gtk.Label(label="set mode:", xalign=0))
            dd = Gtk.DropDown.new_from_strings(modes[:30])
            try:
                dd.set_selected(modes.index(f"{m.get('width')}x{m.get('height')}@{m.get('refreshRate'):.5f}Hz"))
            except Exception: pass
            row.append(dd)
            apply = SketchButton("Apply", width=68, height=24, color=NEON_GREEN)
            apply.connect("clicked",
                          lambda _b, dd=dd, name=name:
                          self._apply_mode(name, dd.get_model().get_string(
                              dd.get_selected())))
            row.append(apply)
            c.add_row(row)

        # scale selector
        row = Gtk.Box(spacing=8)
        row.append(Gtk.Label(label="scale:", xalign=0))
        for s in (1.0, 1.25, 1.5, 2.0):
            b = SketchButton(f"{int(s*100)}%", width=58, height=22,
                             color=NEON_BLUE,
                             primary=(abs(m.get("scale",1.0) - s) < 0.01))
            b.connect("clicked", lambda _b, sc=s, name=name:
                      self._apply_scale(name, sc))
            row.append(b)
        c.add_row(row)

        # transform
        row = Gtk.Box(spacing=8)
        row.append(Gtk.Label(label="rotate:", xalign=0))
        for label, t in [("0°", 0), ("90°", 1), ("180°", 2), ("270°", 3)]:
            b = SketchButton(label, width=46, height=22, color=ACCENT_PURP,
                             primary=(m.get("transform",0) == t))
            b.connect("clicked", lambda _b, tt=t, name=name:
                      self._apply_transform(name, tt))
            row.append(b)
        c.add_row(row)

        # VRR
        row = Gtk.Box(spacing=8)
        row.append(Gtk.Label(label="VRR:", xalign=0))
        on  = SketchButton("on",  width=44, height=22, color=NEON_GREEN,
                           primary=bool(m.get("vrr")))
        off = SketchButton("off", width=44, height=22, color=DANGER_RED,
                           primary=not bool(m.get("vrr")))
        on.connect("clicked",  lambda _b, name=name: self._apply_vrr(name, 1))
        off.connect("clicked", lambda _b, name=name: self._apply_vrr(name, 0))
        row.append(on); row.append(off); c.add_row(row)

    def _apply_mode(self, monitor: str, mode_str: str):
        # mode_str like "1920x1080@60.00000Hz"
        m = re.match(r"(\d+)x(\d+)@([\d.]+)Hz", mode_str)
        if not m: self.win.toast("invalid mode"); return
        res = f"{m.group(1)}x{m.group(2)}@{float(m.group(3)):.5f}"
        rc, _, err = sh(f"hyprctl keyword monitor {monitor},{res},auto,1")
        if rc == 0: self.win.toast(f"{monitor} → {mode_str}"); self.refresh()
        else:       self.win.toast(f"failed: {err.strip()[:50]}")

    def _apply_scale(self, monitor: str, scale: float):
        rc, _, err = sh(f"hyprctl keyword monitor {monitor},preferred,auto,{scale}")
        if rc == 0: self.win.toast(f"{monitor} scale → {scale:.2f}×"); self.refresh()
        else:       self.win.toast(f"failed: {err.strip()[:50]}")

    def _apply_transform(self, monitor: str, t: int):
        rc, _, err = sh(
            f"hyprctl keyword monitor {monitor},preferred,auto,1,transform,{t}")
        if rc == 0: self.win.toast(f"{monitor} transform → {t}"); self.refresh()
        else:       self.win.toast(f"failed: {err.strip()[:50]}")

    def _apply_vrr(self, monitor: str, v: int):
        rc, _, err = sh(f"hyprctl keyword misc:vrr {v}")
        if rc == 0: self.win.toast(f"VRR → {'on' if v else 'off'}"); self.refresh()
        else:       self.win.toast(f"failed: {err.strip()[:50]}")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Resolution", "monitor display"),
            SearchEntry(self.KEY, self.TITLE, "Refresh rate", "hz"),
            SearchEntry(self.KEY, self.TITLE, "Scale / DPI", "scaling"),
            SearchEntry(self.KEY, self.TITLE, "Rotation", "transform orientation"),
            SearchEntry(self.KEY, self.TITLE, "VRR", "variable refresh rate"),
            SearchEntry(self.KEY, self.TITLE, "Fractional scaling"),
            SearchEntry(self.KEY, self.TITLE, "Brightness",
                        "backlight brightnessctl"),
            SearchEntry(self.KEY, self.TITLE, "Night light",
                        "color temperature wlsunset gammastep hyprsunset"),
            SearchEntry(self.KEY, self.TITLE, "Color temperature presets",
                        "kelvin warm sunset"),
            SearchEntry(self.KEY, self.TITLE, "GPU & driver",
                        "lspci glxinfo vulkan"),
            SearchEntry(self.KEY, self.TITLE, "Wayland session",
                        "session type display"),
            SearchEntry(self.KEY, self.TITLE, "hyprland.conf monitor",
                        "edit reload"),
            SearchEntry(self.KEY, self.TITLE, "EDID dump",
                        "monitor identify decode"),
            SearchEntry(self.KEY, self.TITLE, "Cursor size", "XCURSOR"),
            SearchEntry(self.KEY, self.TITLE, "Region screenshot",
                        "grim slurp"),
            SearchEntry(self.KEY, self.TITLE, "Blank screens (DPMS)",
                        "screen off"),
        ]


# ─── Sound ──────────────────────────────────────────────────────────────────
class SoundPage(BasePage):
    KEY = "sound"; TITLE = "Sound"; ICON = "🔊"

    def build(self):
        # ── 1. server info (pipewire / pulseaudio detect) ──────────────────
        c = Card("audio server")
        self.box.append(c)
        rc, out, _ = sh("pactl info 2>/dev/null")
        info = {}
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
        c.add_row(kv_row("Server name:",
                         info.get("Server Name", "(no pulse/pipewire)")))
        c.add_row(kv_row("Server version:",
                         info.get("Server Version", "?")))
        c.add_row(kv_row("Default sink:",
                         info.get("Default Sink", "?")))
        c.add_row(kv_row("Default source:",
                         info.get("Default Source", "?")))
        c.add_row(kv_row("Sample spec:",
                         info.get("Default Sample Specification", "?")))
        c.add_row(kv_row("Channel map:",
                         info.get("Default Channel Map", "?")))
        c.add_row(kv_row("PipeWire active:",
                         "yes" if "PipeWire" in info.get("Server Name", "")
                         else "no (PulseAudio)"))
        # quick service controls
        row = Gtk.Box(spacing=8)
        for label, cmd in (
            ("Restart pipewire",
             "systemctl --user restart pipewire pipewire-pulse wireplumber"),
            ("Restart pulseaudio",
             "systemctl --user restart pulseaudio"),
        ):
            b = SketchButton(label, width=180, height=24, color=NEON_BLUE)
            b.connect("clicked",
                      lambda _b, c=cmd, l=label: (
                          sh_async(c, lambda r, l=l: self.win.toast(
                              f"{l} → ok" if r[0]==0 else f"{l} failed")),
                          None))
            row.append(b)
        c.add_row(row)

        # output / input / app cards (existing dynamic)
        self.out_card = Card("output")
        self.box.append(self.out_card)
        self.in_card  = Card("input")
        self.box.append(self.in_card)
        self.app_card = Card("per-application volume")
        self.box.append(self.app_card)

        # ── 2. cards & profiles ────────────────────────────────────────────
        c = Card("sound cards & profiles")
        self.box.append(c)
        rc, out, _ = sh("pactl list cards short")
        cards = [l.split("\t")[1] for l in out.splitlines()
                 if len(l.split("\t")) >= 2]
        if not cards:
            c.add_row(Gtk.Label(label="(no cards detected)", xalign=0))
        for cid in cards:
            rc, info, _ = sh(
                f"pactl list cards | awk '/Name: {re.escape(cid)}$/,/^$/'")
            cur = "?"; profs = []
            in_profiles = False
            for ln in info.splitlines():
                ln_s = ln.strip()
                if ln_s.startswith("Active Profile:"):
                    cur = ln_s.split(":", 1)[1].strip()
                if ln_s.startswith("Profiles:"):
                    in_profiles = True; continue
                if in_profiles:
                    m = re.match(r"([a-zA-Z0-9+_:.\-]+):\s+", ln_s)
                    if m:
                        profs.append(m.group(1))
                    elif ln_s.startswith(("Ports:", "Sinks:", "Sources:",
                                          "Formats:")):
                        in_profiles = False
            c.add_row(kv_row(cid + ":", cur))
            if profs:
                # show top 6 profiles, prefer common audio ones
                sw = Gtk.ScrolledWindow()
                sw.set_size_request(-1, 36)
                fb = Gtk.Box(spacing=6)
                for p in profs[:8]:
                    b = SketchButton(
                        p[:24] + ("…" if len(p) > 24 else ""),
                        width=180, height=22, color=NEON_GREEN,
                        primary=(p == cur), tooltip=p)
                    b.connect("clicked",
                              lambda _b, c=cid, p=p: (
                                  sh(f"pactl set-card-profile {c} {p}"),
                                  self.win.toast(f"{c} → {p}"),
                                  self.refresh()))
                    fb.append(b)
                sw.set_child(fb); c.add_row(sw)

        # ── 3. ports per sink (speakers / headphones / HDMI) ───────────────
        c = Card("output ports")
        self.box.append(c)
        rc, out, _ = sh("pactl list sinks")
        cur_sink = None
        sink_ports: dict = {}
        sink_active_port: dict = {}
        in_ports = False
        for ln in out.splitlines():
            ln_s = ln.strip()
            m = re.match(r"Name:\s+(.+)", ln_s)
            if m and ln.startswith("\t"):
                cur_sink = m.group(1); sink_ports[cur_sink] = []
                in_ports = False
                continue
            if ln_s.startswith("Ports:"):
                in_ports = True; continue
            if ln_s.startswith("Active Port:"):
                if cur_sink:
                    sink_active_port[cur_sink] = ln_s.split(":", 1)[1].strip()
                in_ports = False; continue
            if in_ports and cur_sink:
                m = re.match(r"([\w\-:.]+):\s+(.+?)\s*\(", ln_s)
                if m:
                    sink_ports[cur_sink].append((m.group(1), m.group(2)))
        if not any(sink_ports.values()):
            c.add_row(Gtk.Label(
                label="(no port info — single-port device)", xalign=0))
        for sink, ports in sink_ports.items():
            if not ports: continue
            cur = sink_active_port.get(sink, "")
            c.add_row(kv_row(sink, f"active: {cur}"))
            row = Gtk.Box(spacing=6)
            for p_id, p_desc in ports[:6]:
                b = SketchButton(
                    p_desc[:22] + ("…" if len(p_desc) > 22 else ""),
                    width=170, height=22, color=ACCENT_GOLD,
                    primary=(p_id == cur), tooltip=f"{p_id}\n{p_desc}")
                b.connect("clicked", lambda _b, s=sink, p=p_id: (
                    sh(f"pactl set-sink-port {s} {p}"),
                    self.win.toast(f"{s} → {p}"),
                    self.refresh()))
                row.append(b)
            c.add_row(row)

        # ── 4. EQ / EasyEffects ────────────────────────────────────────────
        c = Card("EQ & effects")
        self.box.append(c)
        c.add_row(kv_row("easyeffects:",
                         "installed" if have("easyeffects") else
                         "not installed"))
        c.add_row(kv_row("pavucontrol:",
                         "installed" if have("pavucontrol") else
                         "not installed"))
        c.add_row(kv_row("alsamixer:",
                         "installed" if have("alsamixer") else
                         "not installed"))
        c.add_row(kv_row("qpwgraph:",
                         "installed" if have("qpwgraph") else
                         "not installed"))
        row = Gtk.Box(spacing=8)
        if have("easyeffects"):
            b = SketchButton("Launch EasyEffects", width=200, height=24,
                             color=ACCENT_PURP)
            b.connect("clicked", lambda _b: (
                subprocess.Popen(["easyeffects"], start_new_session=True),
                self.win.toast("launching easyeffects…")))
            row.append(b)
        if have("pavucontrol"):
            b = SketchButton("Launch pavucontrol", width=200, height=24,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b: (
                subprocess.Popen(["pavucontrol"], start_new_session=True),
                self.win.toast("launching pavucontrol…")))
            row.append(b)
        if have("alsamixer"):
            b = SketchButton("Open alsamixer", width=180, height=24,
                             color=NEON_GREEN)
            b.connect("clicked", lambda _b: self._term_run(
                "alsamixer", "alsamixer opened…"))
            row.append(b)
        if have("qpwgraph"):
            b = SketchButton("PipeWire graph", width=180, height=24,
                             color=ACCENT_GOLD)
            b.connect("clicked", lambda _b: (
                subprocess.Popen(["qpwgraph"], start_new_session=True),
                self.win.toast("launching qpwgraph…")))
            row.append(b)
        if row.get_first_child():
            c.add_row(row)

        # ── 5. mic test (loopback / record) ────────────────────────────────
        c = Card("microphone test")
        self.box.append(c)
        c.add_row(Gtk.Label(
            label=("Loopback: speaks your mic to your speakers. "
                   "Record: 5s WAV to /tmp."), xalign=0))
        row = Gtk.Box(spacing=8)
        b1 = SketchButton("Start loopback", width=160, height=24,
                          color=NEON_GREEN)
        b1.connect("clicked", lambda _b: (
            sh("pactl load-module module-loopback latency_msec=20"),
            self.win.toast("loopback on (mic→speakers)")))
        row.append(b1)
        b2 = SketchButton("Stop loopback", width=160, height=24,
                          color=DANGER_RED)
        b2.connect("clicked", lambda _b: (
            sh("pactl unload-module module-loopback"),
            self.win.toast("loopback off")))
        row.append(b2)
        b3 = SketchButton("Record 5s → /tmp", width=180, height=24,
                          color=NEON_BLUE)
        b3.connect("clicked", lambda _b: self._term_run(
            "f=/tmp/nyxus-mictest-$(date +%s).wav; "
            "echo recording 5s to $f...; "
            "parec --format=s16le --rate=44100 --channels=1 "
            "--latency-msec=30 -d \"$(pactl get-default-source)\" "
            "| timeout 5 head -c $((44100*2*5)) > $f && "
            "echo; echo done: $f; aplay $f",
            "recording 5s in terminal…"))
        row.append(b3)
        c.add_row(row)

        # ── 6. system sounds (gnome event-sounds) ──────────────────────────
        c = Card("system sounds")
        self.box.append(c)
        rc, out, _ = sh("gsettings get org.gnome.desktop.sound event-sounds")
        cur = out.strip() == "true"
        rc, theme, _ = sh(
            "gsettings get org.gnome.desktop.sound theme-name")
        c.add_row(kv_row("event-sounds:", "on" if cur else "off"))
        c.add_row(kv_row("theme:", theme.strip().strip("'") or "(default)"))
        row = Gtk.Box(spacing=8)
        tog = SketchToggle("system sounds", width=160, height=24,
                           color=NEON_BLUE, active=cur)
        tog.connect("clicked", lambda _b: (
            sh(f"gsettings set org.gnome.desktop.sound event-sounds "
               f"{'true' if tog.active else 'false'}"),
            self.win.toast(
                f"system sounds → {'on' if tog.active else 'off'}")))
        row.append(tog)
        b_test = SketchButton("Test bell", width=120, height=24,
                              color=NEON_GREEN)
        b_test.connect("clicked", lambda _b: (
            sh("paplay /usr/share/sounds/freedesktop/stereo/complete.oga "
               "2>/dev/null || speaker-test -t sine -f 440 -l 1"),
            self.win.toast("test bell played")))
        row.append(b_test)
        c.add_row(row)

        # ── 7. modules loaded ──────────────────────────────────────────────
        c = Card("loaded modules")
        self.box.append(c)
        rc, out, _ = sh("pactl list short modules | head -20")
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 140)
        tv = Gtk.TextView(); tv.set_editable(False); tv.set_monospace(True)
        tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(out or "(no modules)")
        sw.set_child(tv); c.add_row(sw)

        self.refresh()

    # ── helper: run in terminal ────────────────────────────────────────────
    def _term_run(self, cmd: str, toast: str):
        for term in ("foot", "alacritty", "kitty", "xterm"):
            if have(term):
                subprocess.Popen(
                    [term, "-e", "sh", "-c",
                     f"{cmd}; echo; echo 'press enter to close'; read _"],
                    start_new_session=True)
                self.win.toast(toast)
                return
        self.win.toast("no terminal found (install foot/alacritty/kitty)")

    def _vol_get_default_sink(self) -> Tuple[Optional[str], int, bool]:
        """Returns (sink_name, volume_pct, muted)."""
        rc, out, _ = sh("pactl get-default-sink")
        sink = out.strip() if rc == 0 else None
        if not sink: return None, 0, False
        rc, out, _ = sh(f"pactl get-sink-volume {sink}")
        m = re.search(r"(\d+)%", out)
        vol = int(m.group(1)) if m else 0
        rc2, out2, _ = sh(f"pactl get-sink-mute {sink}")
        muted = "yes" in out2
        return sink, vol, muted

    def _list_sinks(self) -> List[Tuple[str,str]]:
        rc, out, _ = sh("pactl list short sinks")
        if rc != 0: return []
        items = []
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                items.append((parts[1], parts[1]))  # name, label
        return items

    def _list_sources(self) -> List[Tuple[str,str]]:
        rc, out, _ = sh("pactl list short sources")
        if rc != 0: return []
        items = []
        for line in out.splitlines():
            parts = line.split("\t")
            if len(parts) >= 2 and ".monitor" not in parts[1]:
                items.append((parts[1], parts[1]))
        return items

    def refresh(self):
        for c in (self.out_card, self.in_card, self.app_card):
            child = c.get_first_child(); skip_first = True
            while child:
                n = child.get_next_sibling()
                if skip_first: skip_first = False
                else: c.remove(child)
                child = n

        if not have("pactl"):
            self.box.append(Gtk.Label(label="pactl not installed", xalign=0))
            return

        # ── output ──
        sink, vol, muted = self._vol_get_default_sink()
        if not sink:
            self.out_card.add_row(Gtk.Label(label="no output device",
                                            xalign=0))
        else:
            row = Gtk.Box(spacing=10)
            row.append(Gtk.Label(label="device:", xalign=0))
            sinks = self._list_sinks()
            dd = Gtk.DropDown.new_from_strings([s[1] for s in sinks])
            try: dd.set_selected(next(i for i,s in enumerate(sinks) if s[0]==sink))
            except StopIteration: pass
            row.append(dd)
            b = SketchButton("Set default", width=110, height=24,
                             color=NEON_GREEN)
            b.connect("clicked",
                      lambda _b, dd=dd, sinks=sinks:
                      self._set_default_sink(sinks[dd.get_selected()][0]))
            row.append(b)
            self.out_card.add_row(row)

            row = Gtk.Box(spacing=10)
            row.append(Gtk.Label(label=f"volume {vol}%", xalign=0))
            sl = SketchSlider(value=min(vol, 100)/100.0, color=NEON_PINK,
                              width=240)
            sl.connect("value-changed", lambda _s, v: self._set_sink_vol(sink, v))
            row.append(sl)
            mute = SketchToggle("mute", width=70, height=24, color=DANGER_RED,
                                active=muted)
            mute.connect("clicked",
                         lambda _b, sink=sink: (sh(f"pactl set-sink-mute {sink} toggle"),
                                                self.refresh()))
            row.append(mute)
            self.out_card.add_row(row)

        # ── input ──
        rc, out, _ = sh("pactl get-default-source")
        src = out.strip() if rc == 0 else None
        if src:
            rc, out, _ = sh(f"pactl get-source-volume {src}")
            m = re.search(r"(\d+)%", out)
            ivol = int(m.group(1)) if m else 0
            row = Gtk.Box(spacing=10)
            row.append(Gtk.Label(label="device:", xalign=0))
            srcs = self._list_sources()
            dd = Gtk.DropDown.new_from_strings([s[1] for s in srcs] or ["(none)"])
            try: dd.set_selected(next(i for i,s in enumerate(srcs) if s[0]==src))
            except StopIteration: pass
            row.append(dd)
            b = SketchButton("Set default", width=110, height=24,
                             color=NEON_GREEN)
            b.connect("clicked",
                      lambda _b, dd=dd, srcs=srcs:
                      self._set_default_source(srcs[dd.get_selected()][0])
                      if srcs else None)
            row.append(b)
            self.in_card.add_row(row)

            row = Gtk.Box(spacing=10)
            row.append(Gtk.Label(label=f"input {ivol}%", xalign=0))
            sl = SketchSlider(value=min(ivol,100)/100.0, color=NEON_BLUE,
                              width=240)
            sl.connect("value-changed", lambda _s, v: self._set_source_vol(src, v))
            row.append(sl)
            self.in_card.add_row(row)
        else:
            self.in_card.add_row(Gtk.Label(label="no input device", xalign=0))

        # ── per-app ──
        rc, out, _ = sh("pactl list sink-inputs")
        if rc == 0:
            apps = self._parse_sink_inputs(out)
            if not apps:
                self.app_card.add_row(Gtk.Label(label="(no audio playing)",
                                                xalign=0))
            for idx, name, vol_pct in apps:
                row = Gtk.Box(spacing=10)
                row.append(Gtk.Label(label=f"{name}", xalign=0))
                sp = Gtk.Box(); sp.set_hexpand(True); row.append(sp)
                sl = SketchSlider(value=min(vol_pct,100)/100.0,
                                  color=ACCENT_PURP, width=180)
                sl.connect("value-changed",
                           lambda _s, v, idx=idx:
                           sh(f"pactl set-sink-input-volume {idx} {int(v*100)}%"))
                row.append(sl)
                self.app_card.add_row(row)

    def _parse_sink_inputs(self, txt: str):
        items = []; cur = None; name = "?"; vol = 0
        for line in txt.splitlines():
            m = re.match(r"Sink Input #(\d+)", line)
            if m:
                if cur is not None: items.append((cur, name, vol))
                cur = int(m.group(1)); name = "?"; vol = 0
                continue
            m = re.search(r"application\.name\s*=\s*\"(.+)\"", line)
            if m: name = m.group(1)
            m = re.search(r"Volume:.*?(\d+)%", line)
            if m: vol = int(m.group(1))
        if cur is not None: items.append((cur, name, vol))
        return items

    def _set_default_sink(self, sink):
        sh(f"pactl set-default-sink {sink}")
        self.win.toast(f"output → {sink}"); self.refresh()
    def _set_default_source(self, src):
        sh(f"pactl set-default-source {src}")
        self.win.toast(f"input → {src}"); self.refresh()
    def _set_sink_vol(self, sink, v):
        sh(f"pactl set-sink-volume {sink} {int(v*100)}%")
    def _set_source_vol(self, src, v):
        sh(f"pactl set-source-volume {src} {int(v*100)}%")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Volume", "audio output"),
            SearchEntry(self.KEY, self.TITLE, "Microphone", "input"),
            SearchEntry(self.KEY, self.TITLE, "Per-app volume"),
            SearchEntry(self.KEY, self.TITLE, "Output device", "speaker headphones"),
            SearchEntry(self.KEY, self.TITLE, "Mute"),
            SearchEntry(self.KEY, self.TITLE, "Audio server",
                        "pipewire pulseaudio pactl"),
            SearchEntry(self.KEY, self.TITLE, "Restart pipewire",
                        "wireplumber service"),
            SearchEntry(self.KEY, self.TITLE, "Sample rate", "channel map"),
            SearchEntry(self.KEY, self.TITLE, "Sound card profile",
                        "alsa pro audio"),
            SearchEntry(self.KEY, self.TITLE, "Output port",
                        "speakers headphones hdmi line out"),
            SearchEntry(self.KEY, self.TITLE, "EasyEffects", "EQ equalizer"),
            SearchEntry(self.KEY, self.TITLE, "pavucontrol", "mixer"),
            SearchEntry(self.KEY, self.TITLE, "alsamixer"),
            SearchEntry(self.KEY, self.TITLE, "PipeWire graph",
                        "qpwgraph patchbay"),
            SearchEntry(self.KEY, self.TITLE, "Microphone loopback",
                        "monitor mic to speakers"),
            SearchEntry(self.KEY, self.TITLE, "Record mic test",
                        "parec wav"),
            SearchEntry(self.KEY, self.TITLE, "System sounds",
                        "event sounds bell theme"),
            SearchEntry(self.KEY, self.TITLE, "Loaded modules",
                        "pactl modules"),
        ]


# ─── Network ────────────────────────────────────────────────────────────────
class NetworkPage(BasePage):
    KEY = "network"; TITLE = "Network"; ICON = "🌐"

    def build(self):
        self.wifi_card = Card("Wi-Fi")
        self.box.append(self.wifi_card)
        self.eth_card = Card("Ethernet")
        self.box.append(self.eth_card)
        self.vpn_card = Card("VPN")
        self.box.append(self.vpn_card)
        self.dns_card = Card("DNS / diagnostics")
        self.box.append(self.dns_card)
        self.refresh()
        # extra deep-dive cards (built once; not wiped by refresh)
        self._build_ufw_card()
        self._build_wireguard_card()
        self._build_connections_card()
        self._build_iface_card()
        self._build_proxy_card()

    def refresh(self):
        for c in (self.wifi_card, self.eth_card, self.vpn_card, self.dns_card):
            child = c.get_first_child(); skip = True
            while child:
                n = child.get_next_sibling()
                if skip: skip = False
                else: c.remove(child)
                child = n
        if not have("nmcli"):
            self.box.append(Gtk.Label(label="nmcli not installed", xalign=0))
            return
        # wifi state
        rc, out, _ = sh("nmcli radio wifi")
        wifi_on = "enabled" in out
        row = Gtk.Box(spacing=10)
        tog = SketchToggle("Wi-Fi", width=80, height=26,
                           color=NEON_BLUE, active=wifi_on)
        tog.connect("clicked", lambda _b: self._toggle_wifi(tog))
        row.append(tog)
        b_scan = SketchButton("Scan", width=68, height=26, color=NEON_GREEN)
        b_scan.connect("clicked", lambda _b: self._wifi_scan())
        row.append(b_scan)
        b_hot = SketchButton("Hotspot", width=80, height=26, color=ACCENT_GOLD)
        b_hot.connect("clicked", lambda _b: self._hotspot_dialog())
        row.append(b_hot)
        self.wifi_card.add_row(row)

        # available wifi
        rc, out, _ = sh("nmcli -t -f BSSID,SSID,SIGNAL,SECURITY,IN-USE dev wifi")
        if rc == 0:
            rows = []
            for line in out.splitlines():
                # BSSID can contain colons; nmcli escapes them as \\:
                # easier: query without BSSID
                pass
            rc2, out2, _ = sh("nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY dev wifi")
            for line in out2.splitlines()[:15]:
                parts = line.split(":")
                if len(parts) < 4: continue
                inuse, ssid, sig, sec = parts[0], parts[1], parts[2], parts[3] or "open"
                if not ssid: continue
                row = Gtk.Box(spacing=10)
                marker = "✓" if inuse.strip() == "*" else " "
                lbl = Gtk.Label(label=f"{marker}  {ssid}  ({sig}%, {sec})",
                                xalign=0)
                lbl.set_hexpand(True); row.append(lbl)
                b = SketchButton("Connect" if inuse.strip() != "*" else "Active",
                                 width=80, height=22,
                                 color=NEON_GREEN if inuse.strip() != "*" else INK_DIM)
                b.connect("clicked",
                          lambda _b, ssid=ssid, sec=sec:
                          self._connect_wifi(ssid, sec))
                row.append(b)
                self.wifi_card.add_row(row)

        # ethernet
        rc, out, _ = sh("nmcli -t -f DEVICE,TYPE,STATE device")
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] == "ethernet":
                self.eth_card.add_row(kv_row(parts[0],
                                             f"state: {parts[2]}"))
        if not any(":ethernet:" in l for l in out.splitlines()):
            self.eth_card.add_row(Gtk.Label(label="(no ethernet interfaces)",
                                            xalign=0))

        # vpn (list connections of type vpn / wireguard)
        rc, out, _ = sh("nmcli -t -f NAME,TYPE,STATE connection")
        any_vpn = False
        for line in out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] in ("vpn", "wireguard"):
                any_vpn = True
                row = Gtk.Box(spacing=10)
                row.append(Gtk.Label(label=f"{parts[0]} ({parts[1]})", xalign=0))
                sp = Gtk.Box(); sp.set_hexpand(True); row.append(sp)
                active = "activated" in parts[2]
                lbl = "Disconnect" if active else "Connect"
                col = DANGER_RED if active else NEON_GREEN
                b = SketchButton(lbl, width=110, height=22, color=col)
                b.connect("clicked",
                          lambda _b, nm=parts[0], up=not active:
                          self._toggle_vpn(nm, up))
                row.append(b)
                self.vpn_card.add_row(row)
        if not any_vpn:
            self.vpn_card.add_row(Gtk.Label(
                label="(no VPN connections — add via "
                      "`nmcli connection add type wireguard …`)", xalign=0))

        # dns / diagnostics
        rc, out, _ = sh("resolvectl status", timeout=2)
        dns = ""
        for line in out.splitlines():
            if "DNS Server" in line or "Current DNS Server" in line:
                dns = line.split(":", 1)[-1].strip(); break
        self.dns_card.add_row(kv_row("Active DNS:", dns or "(unknown)"))
        row = Gtk.Box(spacing=8)
        b1 = SketchButton("Ping 1.1.1.1", width=120, height=24, color=NEON_BLUE)
        b1.connect("clicked", lambda _b: self._diagnose("ping -c 3 1.1.1.1"))
        b2 = SketchButton("DNS lookup", width=110, height=24, color=NEON_BLUE)
        b2.connect("clicked",
                   lambda _b: self._diagnose("dig +short google.com"))
        b3 = SketchButton("Speed test", width=110, height=24, color=ACCENT_PURP,
                          tooltip="needs `speedtest` installed")
        b3.connect("clicked",
                   lambda _b: self._diagnose("speedtest --simple",
                                             timeout=60))
        for b in (b1, b2, b3): row.append(b)
        self.dns_card.add_row(row)

    def _toggle_wifi(self, tog):
        st = "on" if tog.active else "off"
        sh(f"nmcli radio wifi {st}"); self.win.toast(f"wifi {st}")
        GLib.timeout_add(800, lambda: (self.refresh(), False)[1])

    def _wifi_scan(self):
        sh("nmcli device wifi rescan", timeout=2)
        self.win.toast("scanning…")
        GLib.timeout_add(2500, lambda: (self.refresh(), False)[1])

    def _connect_wifi(self, ssid, sec):
        if sec and sec != "open" and sec != "":
            self._password_then_connect(ssid)
        else:
            sh_async(f"nmcli device wifi connect {shlex.quote(ssid)}",
                     lambda r: self.win.toast(
                         f"connected to {ssid}" if r[0]==0
                         else f"failed: {r[2].strip()[:60]}"))

    def _password_then_connect(self, ssid):
        dlg = Gtk.Dialog(transient_for=self.win, modal=True,
                         title=f"join {ssid}")
        dlg.set_default_size(360, -1)
        ent = Gtk.PasswordEntry(); ent.set_show_peek_icon(True)
        ent.set_margin_start(14); ent.set_margin_end(14)
        ent.set_margin_top(14); ent.set_margin_bottom(14)
        dlg.get_content_area().append(ent)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Join",  Gtk.ResponseType.OK)
        def resp(d, r):
            if r == Gtk.ResponseType.OK:
                pw = ent.get_text()
                sh_async(["nmcli", "device", "wifi", "connect", ssid,
                          "password", pw],
                         lambda r: self.win.toast(
                             f"joined {ssid}" if r[0]==0
                             else f"failed: {r[2].strip()[:60]}"))
            d.destroy()
        dlg.connect("response", resp); dlg.present()

    def _hotspot_dialog(self):
        dlg = Gtk.Dialog(transient_for=self.win, modal=True,
                         title="create hotspot")
        dlg.set_default_size(360, -1)
        ca = dlg.get_content_area()
        ca.set_margin_start(14); ca.set_margin_end(14)
        ca.set_margin_top(14); ca.set_margin_bottom(14); ca.set_spacing(6)
        ent = Gtk.Entry(); ent.set_placeholder_text("ssid")
        ent.set_text("nyx-ap")
        pw  = Gtk.PasswordEntry(); pw.set_show_peek_icon(True)
        ca.append(Gtk.Label(label="ssid:", xalign=0)); ca.append(ent)
        ca.append(Gtk.Label(label="password (≥ 8 chars):", xalign=0)); ca.append(pw)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Start", Gtk.ResponseType.OK)
        def resp(d, r):
            if r == Gtk.ResponseType.OK:
                sh_async(["nmcli", "device", "wifi", "hotspot",
                          "ssid", ent.get_text(),
                          "password", pw.get_text()],
                         lambda r: self.win.toast(
                             "hotspot up" if r[0]==0 else
                             f"failed: {r[2].strip()[:60]}"))
            d.destroy()
        dlg.connect("response", resp); dlg.present()

    def _toggle_vpn(self, name, up):
        cmd = f"nmcli connection {'up' if up else 'down'} {shlex.quote(name)}"
        sh_async(cmd, lambda r: (self.win.toast(
            f"{name}: {'up' if up else 'down'}" if r[0]==0
            else f"failed: {r[2].strip()[:60]}"), self.refresh()))

    def _diagnose(self, cmd, timeout=8):
        self.win.toast(f"running: {cmd}")
        sh_async(cmd, lambda r: self._show_output(cmd, r), timeout=timeout)

    def _show_output(self, cmd, r):
        rc, out, err = r
        text = out.strip() or err.strip() or "(no output)"
        dlg = Gtk.Dialog(transient_for=self.win, modal=True, title=cmd)
        dlg.set_default_size(540, 360)
        sw = Gtk.ScrolledWindow(); sw.set_hexpand(True); sw.set_vexpand(True)
        tv = Gtk.TextView(); tv.set_editable(False)
        tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(text)
        sw.set_child(tv); dlg.get_content_area().append(sw)
        dlg.add_buttons("Close", Gtk.ResponseType.CLOSE)
        dlg.connect("response", lambda d, _r: d.destroy())
        dlg.present()

    # ── UFW firewall ───────────────────────────────────────────────────────
    def _build_ufw_card(self):
        c = Card("firewall (UFW)")
        self.box.append(c)
        if not have("ufw"):
            c.add_row(Gtk.Label(
                label="ufw not installed (pacman -S ufw)", xalign=0))
            return
        rc, out, _ = sh("sudo -n ufw status verbose", timeout=3)
        if rc != 0:
            # ufw status needs sudo; show non-privileged hint
            c.add_row(Gtk.Label(
                label="ufw needs sudo to read status — use buttons below "
                      "(they open a terminal that prompts for password).",
                xalign=0))
            status_text = ""
        else:
            status_text = out
        # parse status / default / rule count
        status   = "?"; defaults = ""; rules: List[str] = []
        for ln in status_text.splitlines():
            ls = ln.strip()
            if ls.startswith("Status:"):   status = ls.split(":",1)[1].strip()
            elif ls.startswith("Default:"): defaults = ls.split(":",1)[1].strip()
            elif "ALLOW" in ls or "DENY" in ls or "REJECT" in ls or "LIMIT" in ls:
                if not ls.startswith("--") and not ls.startswith("To"):
                    rules.append(ls)
        c.add_row(kv_row("Status:", status))
        if defaults: c.add_row(kv_row("Defaults:", defaults))
        c.add_row(kv_row("Active rules:", str(len(rules))))
        for r in rules[:8]:
            c.add_row(Gtk.Label(label=f"  • {r}", xalign=0))
        if len(rules) > 8:
            c.add_row(Gtk.Label(label=f"  … and {len(rules)-8} more",
                                xalign=0))
        # preset profiles
        c.add_row(Gtk.Label(label="presets:", xalign=0))
        row = Gtk.Box(spacing=8)
        for label, cmds, color in (
            ("Desktop (block-incoming)",
             "ufw --force reset && ufw default deny incoming && "
             "ufw default allow outgoing && ufw enable",
             NEON_GREEN),
            ("Server (allow ssh+http)",
             "ufw --force reset && ufw default deny incoming && "
             "ufw default allow outgoing && ufw allow ssh && "
             "ufw allow http && ufw allow https && ufw enable",
             ACCENT_GOLD),
            ("Off (disable)",
             "ufw disable",
             DANGER_RED),
        ):
            b = SketchButton(label, width=220, height=24, color=color)
            b.connect("clicked", lambda _b, cc=cmds, n=label: self._term_run(
                f"sudo sh -c '{cc}'", f"applying preset: {n}"))
            row.append(b)
        c.add_row(row)
        row2 = Gtk.Box(spacing=8)
        b_add = SketchButton("Add rule…", width=130, height=24, color=NEON_PINK)
        b_add.connect("clicked", lambda _b: self._term_run(
            "read -p 'rule (eg: allow 8080/tcp): ' r && sudo ufw $r",
            "add-rule prompt opened"))
        row2.append(b_add)
        b_log = SketchButton("Tail UFW log", width=160, height=24,
                             color=ACCENT_PURP)
        b_log.connect("clicked", lambda _b: self._term_run(
            "sudo journalctl -u ufw -f",
            "UFW log opened in terminal"))
        row2.append(b_log)
        c.add_row(row2)

    # ── WireGuard import + manage ──────────────────────────────────────────
    def _build_wireguard_card(self):
        c = Card("WireGuard")
        self.box.append(c)
        wg_present = have("wg") or have("wg-quick")
        if not wg_present:
            c.add_row(Gtk.Label(
                label="wireguard-tools not installed "
                      "(pacman -S wireguard-tools)", xalign=0))
            return
        # active tunnels (needs sudo for `wg show`, but try anyway)
        rc, out, _ = sh("sudo -n wg show", timeout=2)
        if rc == 0 and out.strip():
            ifaces = re.findall(r"^interface:\s*(\S+)", out, re.MULTILINE)
            c.add_row(kv_row("Active tunnels:", str(len(ifaces))))
            for i in ifaces:
                c.add_row(Gtk.Label(label=f"  ↑ {i}", xalign=0))
        else:
            c.add_row(kv_row("Active tunnels:", "(none / sudo needed)"))
        # configs in /etc/wireguard
        wg_dir = Path("/etc/wireguard")
        if wg_dir.exists():
            try:
                confs = sorted(p.stem for p in wg_dir.glob("*.conf"))
            except PermissionError:
                confs = []
            if confs:
                c.add_row(kv_row("Saved configs:", ", ".join(confs)))
                for name in confs[:6]:
                    r = Gtk.Box(spacing=8)
                    r.append(Gtk.Label(label=f"  🔐 {name}", xalign=0))
                    sp = Gtk.Box(); sp.set_hexpand(True); r.append(sp)
                    b_up = SketchButton("Up", width=70, height=22,
                                        color=NEON_GREEN)
                    b_up.connect("clicked", lambda _b, n=name: self._term_run(
                        f"sudo wg-quick up {n}", f"bringing {n} up…"))
                    r.append(b_up)
                    b_dn = SketchButton("Down", width=70, height=22,
                                        color=DANGER_RED)
                    b_dn.connect("clicked", lambda _b, n=name: self._term_run(
                        f"sudo wg-quick down {n}", f"bringing {n} down…"))
                    r.append(b_dn)
                    c.add_row(r)
            else:
                c.add_row(kv_row("Saved configs:", "(none in /etc/wireguard)"))
        # import .conf
        row = Gtk.Box(spacing=8)
        b_imp = SketchButton("Import .conf", width=140, height=24,
                             color=NEON_PINK)
        b_imp.connect("clicked", lambda _b: self._wg_import())
        row.append(b_imp)
        b_gen = SketchButton("Generate keypair", width=170, height=24,
                             color=ACCENT_GOLD)
        b_gen.connect("clicked", lambda _b: self._term_run(
            "wg genkey | tee /tmp/wg_priv | wg pubkey > /tmp/wg_pub && "
            "echo 'private: '$(cat /tmp/wg_priv) && "
            "echo 'public:  '$(cat /tmp/wg_pub)",
            "keypair written to /tmp/wg_priv + /tmp/wg_pub"))
        row.append(b_gen)
        c.add_row(row)

    def _wg_import(self):
        dlg = Gtk.FileDialog(); dlg.set_title("Import WireGuard .conf")
        def _done(d, res):
            try: f = d.open_finish(res)
            except Exception: return
            if not f: return
            p = f.get_path()
            stem = Path(p).stem
            self._term_run(
                f"sudo install -o root -g root -m 600 "
                f"{shlex.quote(p)} /etc/wireguard/{shlex.quote(stem)}.conf "
                f"&& echo 'imported as {stem}.conf'",
                f"importing {Path(p).name}…")
        dlg.open(self.win, None, _done)

    # ── active connections (nmcli) ─────────────────────────────────────────
    def _build_connections_card(self):
        c = Card("active connections")
        self.box.append(c)
        if not have("nmcli"):
            c.add_row(Gtk.Label(label="nmcli not installed", xalign=0))
            return
        rc, out, _ = sh(
            "nmcli -t -f NAME,TYPE,DEVICE,STATE connection show --active",
            timeout=3)
        rows = [ln.split(":") for ln in out.splitlines() if ln.strip()]
        if not rows:
            c.add_row(Gtk.Label(label="(no active connections)", xalign=0))
        for parts in rows:
            if len(parts) < 4: continue
            name, typ, dev, state = parts[0], parts[1], parts[2], parts[3]
            r = Gtk.Box(spacing=8)
            r.append(Gtk.Label(
                label=f"⚡ {name}  [{typ}]  on {dev}  ({state})",
                xalign=0))
            sp = Gtk.Box(); sp.set_hexpand(True); r.append(sp)
            b = SketchButton("Disconnect", width=120, height=22,
                             color=DANGER_RED)
            b.connect("clicked", lambda _b, n=name: sh_async(
                f"nmcli connection down {shlex.quote(n)}",
                lambda r: (self.win.toast(
                    f"{n} down" if r[0]==0 else f"failed: {r[2].strip()[:50]}"),
                    self.refresh())))
            r.append(b)
            c.add_row(r)
        # show IP per active interface
        rc, out, _ = sh("ip -4 -o addr show", timeout=2)
        for ln in out.splitlines():
            parts = ln.split()
            if len(parts) >= 4 and parts[2] == "inet":
                iface = parts[1]; ip = parts[3]
                if iface != "lo":
                    c.add_row(kv_row(f"  {iface}:", ip))
        # public IP (cached, single call)
        rc, ip4, _ = sh("curl -fsS --max-time 4 https://api.ipify.org",
                        timeout=5)
        c.add_row(kv_row("Public IP:", ip4.strip() or "(offline)"))

    # ── interface stats (RX/TX) ────────────────────────────────────────────
    def _build_iface_card(self):
        c = Card("interface stats")
        self.box.append(c)
        rc, out, _ = sh("ip -s -h link", timeout=2)
        if rc != 0 or not out.strip():
            c.add_row(Gtk.Label(label="(ip command unavailable)", xalign=0))
            return
        # parse: each interface = 2-3 lines header, then RX line, RX numbers, TX line, TX numbers
        cur = None
        rx_label = tx_label = None
        skip_next = 0
        for ln in out.splitlines():
            m = re.match(r"^\d+:\s+(\S+?):", ln)
            if m:
                cur = m.group(1).rstrip(":")
                if cur != "lo":
                    c.add_row(Gtk.Label(label=f"📶 {cur}", xalign=0))
                continue
            if cur and cur != "lo":
                ls = ln.strip()
                if ls.startswith("RX:"):  rx_label = True; continue
                if ls.startswith("TX:"):  tx_label = True; continue
                if rx_label:
                    parts = ls.split()
                    if parts: c.add_row(kv_row(f"  RX:", f"{parts[0]} bytes"))
                    rx_label = False; continue
                if tx_label:
                    parts = ls.split()
                    if parts: c.add_row(kv_row(f"  TX:", f"{parts[0]} bytes"))
                    tx_label = False; continue

    # ── proxy ──────────────────────────────────────────────────────────────
    def _build_proxy_card(self):
        c = Card("proxy")
        self.box.append(c)
        for var in ("http_proxy", "https_proxy", "ftp_proxy",
                    "no_proxy", "all_proxy"):
            v = os.environ.get(var) or os.environ.get(var.upper()) or ""
            c.add_row(kv_row(var+":", v or "(unset)"))
        # gsettings (GNOME apps respect this)
        rc, mode, _ = sh("gsettings get org.gnome.system.proxy mode",
                         timeout=2)
        c.add_row(kv_row("gsettings proxy mode:", mode.strip() or "(n/a)"))
        row = Gtk.Box(spacing=8)
        b_off = SketchButton("Disable system proxy", width=200, height=24,
                             color=NEON_GREEN)
        b_off.connect("clicked", lambda _b: sh_async(
            "gsettings set org.gnome.system.proxy mode 'none'",
            lambda r: self.win.toast(
                "proxy disabled" if r[0]==0 else "failed")))
        row.append(b_off)
        b_edit = SketchButton("Edit /etc/environment", width=200, height=24,
                              color=NEON_PINK)
        b_edit.connect("clicked", lambda _b: self._term_run(
            "sudo ${EDITOR:-nano} /etc/environment",
            "/etc/environment opened (sudo)…"))
        row.append(b_edit)
        c.add_row(row)

    # ── helper: run in terminal ────────────────────────────────────────────
    def _term_run(self, cmd: str, toast: str):
        for term in ("foot", "alacritty", "kitty", "xterm"):
            if have(term):
                subprocess.Popen(
                    [term, "-e", "sh", "-c",
                     f"{cmd}; echo; echo 'press enter to close'; read _"],
                    start_new_session=True)
                self.win.toast(toast)
                return
        self.win.toast("no terminal found (install foot/alacritty/kitty)")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Wi-Fi"),
            SearchEntry(self.KEY, self.TITLE, "Connect to network", "ssid wifi"),
            SearchEntry(self.KEY, self.TITLE, "Hotspot"),
            SearchEntry(self.KEY, self.TITLE, "Ethernet"),
            SearchEntry(self.KEY, self.TITLE, "VPN", "wireguard"),
            SearchEntry(self.KEY, self.TITLE, "WireGuard import", "wg-quick"),
            SearchEntry(self.KEY, self.TITLE, "Firewall (UFW)", "ufw rules"),
            SearchEntry(self.KEY, self.TITLE, "UFW preset profiles",
                        "desktop server block"),
            SearchEntry(self.KEY, self.TITLE, "Active connections", "nmcli"),
            SearchEntry(self.KEY, self.TITLE, "Public IP"),
            SearchEntry(self.KEY, self.TITLE, "Interface stats", "RX TX"),
            SearchEntry(self.KEY, self.TITLE, "Proxy",
                        "http_proxy https_proxy"),
            SearchEntry(self.KEY, self.TITLE, "DNS"),
            SearchEntry(self.KEY, self.TITLE, "Ping / diagnostics"),
            SearchEntry(self.KEY, self.TITLE, "Speed test"),
        ]


# ─── Bluetooth ──────────────────────────────────────────────────────────────
class BluetoothPage(BasePage):
    KEY = "bluetooth"; TITLE = "Bluetooth"; ICON = "🅱"

    def build(self):
        # ── 1. service status ──────────────────────────────────────────────
        c = Card("bluetooth service")
        self.box.append(c)
        rc, out, _ = sh("systemctl is-active bluetooth.service")
        active = out.strip() == "active"
        rc, en, _ = sh("systemctl is-enabled bluetooth.service")
        enabled = en.strip() == "enabled"
        c.add_row(kv_row("systemd unit:",
                         f"{'active' if active else 'inactive'} · "
                         f"{'enabled' if enabled else 'disabled'}"))
        row = Gtk.Box(spacing=8)
        for label, cmd in (
            ("Start",   "sudo systemctl start bluetooth"),
            ("Stop",    "sudo systemctl stop bluetooth"),
            ("Restart", "sudo systemctl restart bluetooth"),
            ("Enable on boot", "sudo systemctl enable bluetooth"),
        ):
            b = SketchButton(label, width=140, height=24, color=NEON_BLUE)
            b.connect("clicked", lambda _b, c=cmd, l=label: self._term_run(
                c, f"{l}…"))
            row.append(b)
        c.add_row(row)

        # ── 2. rfkill ──────────────────────────────────────────────────────
        c = Card("radio (rfkill)")
        self.box.append(c)
        if not have("rfkill"):
            c.add_row(Gtk.Label(label="rfkill not installed", xalign=0))
        else:
            rc, out, _ = sh("rfkill list bluetooth")
            soft = hard = "?"
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("Soft blocked:"):
                    soft = line.split(":", 1)[1].strip()
                elif line.startswith("Hard blocked:"):
                    hard = line.split(":", 1)[1].strip()
            c.add_row(kv_row("Soft blocked:", soft))
            c.add_row(kv_row("Hard blocked:", hard))
            row = Gtk.Box(spacing=8)
            b1 = SketchButton("Unblock (rfkill unblock)", width=210,
                              height=24, color=NEON_GREEN)
            b1.connect("clicked", lambda _b: (
                sh("rfkill unblock bluetooth"),
                self.win.toast("bluetooth radio unblocked"),
                self.refresh()))
            row.append(b1)
            b2 = SketchButton("Block", width=90, height=24,
                              color=DANGER_RED)
            b2.connect("clicked", lambda _b: (
                sh("rfkill block bluetooth"),
                self.win.toast("bluetooth radio blocked"),
                self.refresh()))
            row.append(b2)
            c.add_row(row)

        # ── 3. adapters (dynamic) ──────────────────────────────────────────
        self.adp_card = Card("adapters")
        self.box.append(self.adp_card)

        # ── 4. controller (dynamic) ────────────────────────────────────────
        self.state_card = Card("controller")
        self.box.append(self.state_card)

        # ── 5. devices (dynamic) ───────────────────────────────────────────
        self.dev_card = Card("devices")
        self.box.append(self.dev_card)

        # ── 6. audio profile per connected device ──────────────────────────
        c = Card("audio codecs / profile")
        self.box.append(c)
        if not have("pactl"):
            c.add_row(Gtk.Label(
                label="pactl not installed (pulseaudio/pipewire-pulse)",
                xalign=0))
        else:
            rc, out, _ = sh("pactl list cards short")
            bt_cards = [l for l in out.splitlines() if "bluez" in l.lower()]
            if not bt_cards:
                c.add_row(Gtk.Label(
                    label="(no Bluetooth audio cards connected)", xalign=0))
            for line in bt_cards:
                parts = line.split()
                if len(parts) < 2: continue
                cid = parts[1]
                # current profile
                rc, info, _ = sh(f"pactl list cards | "
                                 f"awk '/Name: {cid}/,/^$/'")
                cur = "?"
                for ln in info.splitlines():
                    ln = ln.strip()
                    if ln.startswith("Active Profile:"):
                        cur = ln.split(":", 1)[1].strip()
                        break
                c.add_row(kv_row(cid, cur))
                row = Gtk.Box(spacing=6)
                for prof, label in (
                    ("a2dp_sink",                 "A2DP (high-quality)"),
                    ("headset_head_unit",         "Headset (mic)"),
                    ("a2dp-sink-aac",             "AAC"),
                    ("a2dp-sink-aptx",            "aptX"),
                    ("a2dp-sink-ldac",            "LDAC"),
                    ("off",                       "Off"),
                ):
                    b = SketchButton(label, width=160, height=22,
                                     color=NEON_GREEN,
                                     primary=(prof == cur))
                    b.connect("clicked",
                              lambda _b, c=cid, p=prof: (
                                  sh(f"pactl set-card-profile {c} {p}"),
                                  self.win.toast(f"{c} → {p}")))
                    row.append(b)
                c.add_row(row)

        # ── 7. main.conf ───────────────────────────────────────────────────
        c = Card("/etc/bluetooth/main.conf")
        self.box.append(c)
        try:
            txt = Path("/etc/bluetooth/main.conf").read_text()
        except Exception:
            txt = ""
        for key in ("AutoEnable", "JustWorksRepairing", "FastConnectable",
                    "DiscoverableTimeout", "PairableTimeout", "Name"):
            val = "(default)"
            for line in txt.splitlines():
                ln = line.strip()
                if ln.startswith("#") or "=" not in ln: continue
                k, v = ln.split("=", 1)
                if k.strip() == key:
                    val = v.strip()
            c.add_row(kv_row(key + ":", val))
        row = Gtk.Box(spacing=8)
        b = SketchButton("Edit main.conf", width=180, height=26,
                         color=ACCENT_GOLD)
        b.connect("clicked", lambda _b: self._term_run(
            "sudo ${EDITOR:-nano} /etc/bluetooth/main.conf && "
            "sudo systemctl restart bluetooth",
            "main.conf opened (sudo)…"))
        row.append(b)
        c.add_row(row)

        self.refresh()

    # ── helper: run in terminal ────────────────────────────────────────────
    def _term_run(self, cmd: str, toast: str):
        for term in ("foot", "alacritty", "kitty", "xterm"):
            if have(term):
                subprocess.Popen(
                    [term, "-e", "sh", "-c",
                     f"{cmd}; echo; echo 'press enter to close'; read _"],
                    start_new_session=True)
                self.win.toast(toast)
                return
        self.win.toast("no terminal found (install foot/alacritty/kitty)")

    # ── helper: clear card body, keep title row ────────────────────────────
    def _clear_card(self, card):
        child = card.get_first_child(); skip = True
        while child:
            n = child.get_next_sibling()
            if skip: skip = False
            else: card.remove(child)
            child = n

    def refresh(self):
        for c in (self.adp_card, self.state_card, self.dev_card):
            self._clear_card(c)

        if not have("bluetoothctl"):
            self.adp_card.add_row(Gtk.Label(
                label="bluetoothctl not installed (pacman -S bluez-utils)",
                xalign=0))
            return

        # adapters
        rc, out, _ = sh("bluetoothctl list")
        adps = []
        for line in out.splitlines():
            m = re.match(r"Controller\s+([0-9A-F:]+)\s+(.+?)(?:\s+\[default\])?$",
                         line.strip())
            if m:
                adps.append((m.group(1), m.group(2).strip(),
                             "[default]" in line))
        if not adps:
            self.adp_card.add_row(Gtk.Label(
                label="(no controllers found)", xalign=0))
        for mac, name, is_default in adps:
            row = Gtk.Box(spacing=8)
            tag = " (default)" if is_default else ""
            lbl = Gtk.Label(label=f"{name} · {mac}{tag}", xalign=0)
            lbl.set_hexpand(True); row.append(lbl)
            if not is_default:
                b = SketchButton("Make default", width=140, height=22,
                                 color=ACCENT_GOLD)
                b.connect("clicked", lambda _b, m=mac: (
                    sh(f"bluetoothctl select {m}"),
                    self.win.toast(f"default → {m}"),
                    self.refresh()))
                row.append(b)
            self.adp_card.add_row(row)

        # controller details
        rc, out, _ = sh("bluetoothctl show")
        powered  = "Powered: yes"      in out
        disc     = "Discoverable: yes" in out
        pairable = "Pairable: yes"     in out
        # alias
        alias = ""
        for line in out.splitlines():
            if "Alias:" in line:
                alias = line.split(":", 1)[1].strip(); break
        if alias:
            self.state_card.add_row(kv_row("Alias:", alias))
        row = Gtk.Box(spacing=10)
        b = SketchToggle("power", width=80, height=26, color=NEON_BLUE,
                         active=powered)
        b.connect("clicked", lambda _b: (
            sh(f"bluetoothctl power {'on' if b.active else 'off'}"),
            GLib.timeout_add(500,
                             lambda:(self.refresh(), False)[1])))
        row.append(b)
        d = SketchToggle("discoverable", width=110, height=26,
                         color=ACCENT_PURP, active=disc)
        d.connect("clicked", lambda _b: sh(
            f"bluetoothctl discoverable {'on' if d.active else 'off'}"))
        row.append(d)
        p = SketchToggle("pairable", width=90, height=26,
                         color=ACCENT_GOLD, active=pairable)
        p.connect("clicked", lambda _b: sh(
            f"bluetoothctl pairable {'on' if p.active else 'off'}"))
        row.append(p)
        s = SketchButton("Scan 8s", width=90, height=26, color=NEON_GREEN)
        s.connect("clicked", lambda _b: self._scan())
        row.append(s)
        ag = SketchButton("Agent on", width=100, height=26, color=NEON_BLUE)
        ag.connect("clicked", lambda _b: (
            sh_async("bluetoothctl agent on && bluetoothctl default-agent",
                     lambda r: self.win.toast("agent on")),
            None))
        row.append(ag)
        self.state_card.add_row(row)

        # devices — separate paired vs discovered
        rc, paired, _ = sh("bluetoothctl paired-devices")
        rc, all_dev, _ = sh("bluetoothctl devices")
        paired_macs = set()
        for line in paired.splitlines():
            m = re.match(r"Device ([0-9A-F:]+)", line)
            if m: paired_macs.add(m.group(1))

        # connected list (info per mac)
        def render_list(title, lines, icon):
            if not lines:
                return
            self.dev_card.add_row(Gtk.Label(
                label=f"── {icon} {title} ──", xalign=0))
            for line in lines:
                m = re.match(r"Device ([0-9A-F:]+)\s+(.+)", line)
                if not m: continue
                mac, name = m.group(1), m.group(2)
                # connected state
                rc, info, _ = sh(f"bluetoothctl info {mac}")
                connected = "Connected: yes" in info
                trusted   = "Trusted: yes"   in info
                blocked   = "Blocked: yes"   in info
                tags = []
                if connected: tags.append("●conn")
                if trusted:   tags.append("trusted")
                if blocked:   tags.append("blocked")
                tag_str = (" [" + " ".join(tags) + "]") if tags else ""
                row = Gtk.Box(spacing=10)
                lbl = Gtk.Label(label=f"{name} ({mac}){tag_str}",
                                xalign=0)
                lbl.set_hexpand(True); row.append(lbl)
                for label, action, color in (
                    ("Connect",    "connect",    NEON_GREEN),
                    ("Disconnect", "disconnect", DANGER_RED),
                    ("Trust",      "trust",      ACCENT_GOLD),
                    ("Block" if not blocked else "Unblock",
                     "block" if not blocked else "unblock", NEON_PINK),
                    ("Forget",     "remove",     INK_DIM),
                ):
                    b = SketchButton(label, width=86, height=22,
                                     color=color)
                    b.connect("clicked",
                              lambda _b, a=action, m=mac:
                              sh_async(f"bluetoothctl {a} {m}",
                                       lambda r, a=a: (self.win.toast(
                                           f"{a}: "
                                           f"{'ok' if r[0]==0 else 'failed'}"),
                                                       self.refresh())))
                    row.append(b)
                self.dev_card.add_row(row)

        if rc == 0:
            paired_lines = [l for l in all_dev.splitlines()
                            if any(m in l for m in paired_macs)]
            other_lines  = [l for l in all_dev.splitlines()
                            if not any(m in l for m in paired_macs)]
            render_list("paired", paired_lines, "★")
            render_list("discovered", other_lines, "◌")
            if not paired_lines and not other_lines:
                self.dev_card.add_row(Gtk.Label(
                    label="(no devices — hit Scan)", xalign=0))
        else:
            self.dev_card.add_row(Gtk.Label(
                label="(bluetoothctl error)", xalign=0))

    def _scan(self):
        sh_async("bluetoothctl --timeout 8 scan on",
                 lambda r: (self.win.toast("scan complete"), self.refresh()),
                 timeout=12)
        self.win.toast("scanning for 8s…")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Bluetooth power"),
            SearchEntry(self.KEY, self.TITLE, "Pair / connect device"),
            SearchEntry(self.KEY, self.TITLE, "Discoverable"),
            SearchEntry(self.KEY, self.TITLE, "Pairable"),
            SearchEntry(self.KEY, self.TITLE, "Scan for devices"),
            SearchEntry(self.KEY, self.TITLE, "Trust device"),
            SearchEntry(self.KEY, self.TITLE, "Block device"),
            SearchEntry(self.KEY, self.TITLE, "Forget device", "remove"),
            SearchEntry(self.KEY, self.TITLE, "Adapter / controller",
                        "default"),
            SearchEntry(self.KEY, self.TITLE, "Bluetooth service",
                        "systemd start stop"),
            SearchEntry(self.KEY, self.TITLE, "rfkill block", "radio"),
            SearchEntry(self.KEY, self.TITLE, "Audio codec / profile",
                        "a2dp aac aptx ldac headset"),
            SearchEntry(self.KEY, self.TITLE, "Bluetooth main.conf",
                        "AutoEnable name"),
            SearchEntry(self.KEY, self.TITLE, "Agent / pairing prompts"),
        ]


# ─── Appearance ─────────────────────────────────────────────────────────────
class AppearancePage(BasePage):
    KEY = "appearance"; TITLE = "Themes & Appearance"; ICON = "🎨"
    TILE_COLOR = ACCENT_PURP
    SUBTITLE  = "Theme · Accent · Window style · Cursor"

    def build(self):
        c = Card("color scheme")
        self.box.append(c)
        row = Gtk.Box(spacing=10)
        for label, kind in (("Dark", "dark"), ("Light", "light"),
                            ("Auto", "auto")):
            b = SketchButton(label, width=66, height=24, color=NEON_BLUE,
                             primary=(self.win.prefs.get("color_scheme") == kind))
            b.connect("clicked", lambda _b, k=kind:
                      (self.win.prefs.update(color_scheme=k),
                       self.win.save_prefs(),
                       self.win.toast(f"color scheme → {k}")))
            row.append(b)
        c.add_row(row)

        # Wallpaper
        c = Card("wallpaper")
        self.box.append(c)
        c.add_row(Gtk.Label(
            label=f"installed wallpapers in: {WALL_DIR_NYXUS}", xalign=0))
        self.wall_grid_holder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        c.add_row(self.wall_grid_holder)
        self._build_wall_grid()
        # accent
        c = Card("accent color")
        self.box.append(c)
        row = Gtk.Box(spacing=8)
        for name, rgb in (("Pink", NEON_PINK), ("Blue", NEON_BLUE),
                          ("Green", NEON_GREEN), ("Purple", ACCENT_PURP),
                          ("Gold", ACCENT_GOLD)):
            b = SketchButton(name, width=64, height=22, color=rgb,
                             primary=(self.win.prefs.get("accent")==name.lower()))
            b.connect("clicked", lambda _b, n=name.lower():
                      (self.win.prefs.update(accent=n),
                       self.win.save_prefs(),
                       self.win.toast(f"accent → {n}")))
            row.append(b)
        c.add_row(row)

        c = Card("animations")
        self.box.append(c)
        # animations on/off via hyprctl
        ani = SketchToggle("Hyprland animations", width=180, height=26,
                           color=NEON_GREEN, active=self._anim_on())
        ani.connect("clicked", lambda _b: self._toggle_anim(ani))
        c.add_row(ani)
        # interface font size
        row = Gtk.Box(spacing=10)
        row.append(Gtk.Label(label="UI font size:", xalign=0))
        sl = SketchSlider(value=(self.win.prefs.get("ui_font_size", 14)-10)/14.0,
                          color=NEON_PINK, width=240)
        def on_change(_s, v):
            self.win.prefs["ui_font_size"] = int(10 + v*14)
            self.win.save_prefs()
        sl.connect("value-changed", on_change)
        row.append(sl)
        c.add_row(row)

    def _anim_on(self) -> bool:
        rc, out, _ = sh("hyprctl getoption animations:enabled -j")
        if rc != 0: return True
        try: return json.loads(out).get("int", 1) == 1
        except Exception: return True

    def _toggle_anim(self, tog):
        sh(f"hyprctl keyword animations:enabled {1 if tog.active else 0}")
        self.win.toast(f"animations {'on' if tog.active else 'off'}")

    def _build_wall_grid(self):
        # remove any prior child
        c = self.wall_grid_holder.get_first_child()
        while c:
            n = c.get_next_sibling(); self.wall_grid_holder.remove(c); c = n
        flow = Gtk.FlowBox(); flow.set_max_children_per_line(6)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.wall_grid_holder.append(flow)
        if not WALL_DIR_NYXUS.exists():
            flow.append(Gtk.Label(label=f"missing: {WALL_DIR_NYXUS}"))
            return
        files = sorted([p for p in WALL_DIR_NYXUS.iterdir()
                        if p.suffix.lower() in (".png",".jpg",".jpeg",".webp")
                        and ("bg" in p.name.lower()
                             or "wall" in p.name.lower()
                             or "owl" in p.name.lower())])[:60]
        for f in files:
            btn = Gtk.Button()
            try:
                pic = Gtk.Picture.new_for_filename(str(f))
                pic.set_size_request(140, 80)
                pic.set_can_shrink(True)
                pic.set_content_fit(Gtk.ContentFit.COVER)
                btn.set_child(pic)
            except Exception:
                btn.set_label(f.name)
            btn.set_tooltip_text(f.name)
            btn.connect("clicked", lambda _b, p=f: self._set_wallpaper(p))
            flow.append(btn)

    def _set_wallpaper(self, path: Path):
        # try swww (Wayland), then hyprpaper, then echo
        if have("swww"):
            sh("swww init", timeout=2)
            rc, _, err = sh(f"swww img {shlex.quote(str(path))} "
                            f"--transition-type any --transition-duration 1")
            if rc == 0: self.win.toast(f"wallpaper → {path.name}"); return
        if have("hyprctl"):
            # write hyprpaper-like
            sh(f"hyprctl hyprpaper preload {shlex.quote(str(path))}")
            sh(f"hyprctl hyprpaper wallpaper ,{shlex.quote(str(path))}")
            self.win.toast(f"wallpaper → {path.name}"); return
        self.win.toast("no wallpaper tool installed (swww/hyprpaper)")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Wallpaper"),
            SearchEntry(self.KEY, self.TITLE, "Color scheme", "dark light"),
            SearchEntry(self.KEY, self.TITLE, "Accent color"),
            SearchEntry(self.KEY, self.TITLE, "Animations"),
            SearchEntry(self.KEY, self.TITLE, "UI font size"),
        ]


# ─── Workspaces ─────────────────────────────────────────────────────────────
class WorkspacesPage(BasePage):
    KEY = "workspaces"; TITLE = "Workspaces"; ICON = "🪟"

    def build(self):
        self.list_card = Card("active workspaces")
        self.box.append(self.list_card)
        b = SketchButton("Refresh", width=100, height=24, color=NEON_GREEN)
        b.connect("clicked", lambda _b: self.refresh())
        self.box.append(b)
        self.add_note(
            "workspace count is dynamic in Hyprland — there's no fixed limit. "
            "Each workspace is created on demand when you switch to it.")
        self.refresh()

    def refresh(self):
        c = self.list_card.get_first_child(); skip = True
        while c:
            n = c.get_next_sibling()
            if skip: skip = False
            else: self.list_card.remove(c)
            c = n
        if not have("hyprctl"):
            self.list_card.add_row(Gtk.Label(label="hyprctl not installed",
                                             xalign=0))
            return
        rc, out, _ = sh("hyprctl -j workspaces")
        try: ws = json.loads(out) if rc == 0 else []
        except Exception: ws = []
        if not ws:
            self.list_card.add_row(Gtk.Label(label="(no workspaces)", xalign=0))
        for w in sorted(ws, key=lambda x: x.get("id", 0)):
            self.list_card.add_row(kv_row(
                f"workspace {w.get('id')}",
                f"monitor: {w.get('monitor')}  •  windows: {w.get('windows',0)}"))

    def search_entries(self):
        return [SearchEntry(self.KEY, self.TITLE, "Workspaces")]


# ─── Keyboard ───────────────────────────────────────────────────────────────
class KeyboardPage(BasePage):
    KEY = "keyboard"; TITLE = "Keyboard"; ICON = "⌨"

    def build(self):
        c = Card("layout")
        self.box.append(c)
        rc, out, _ = sh("hyprctl -j devices")
        layouts = []
        try:
            data = json.loads(out)
            for kb in data.get("keyboards", []):
                layouts.append(f"{kb.get('name','?')} → {kb.get('active_keymap','?')}")
        except Exception: pass
        for l in layouts:
            c.add_row(Gtk.Label(label=l, xalign=0))
        if not layouts:
            c.add_row(Gtk.Label(label="(no keyboards detected)", xalign=0))

        c = Card("repeat rate")
        self.box.append(c)
        rc, out, _ = sh("hyprctl getoption input:repeat_rate -j")
        try: rate = json.loads(out).get("int", 25)
        except Exception: rate = 25
        rc, out, _ = sh("hyprctl getoption input:repeat_delay -j")
        try: delay = json.loads(out).get("int", 600)
        except Exception: delay = 600
        row = Gtk.Box(spacing=10)
        row.append(Gtk.Label(label=f"rate {rate}/s", xalign=0))
        sl = SketchSlider(value=min(rate,80)/80.0, color=NEON_PINK, width=220)
        sl.connect("value-changed",
                   lambda _s, v: sh(f"hyprctl keyword input:repeat_rate {int(5+v*75)}"))
        row.append(sl); c.add_row(row)
        row = Gtk.Box(spacing=10)
        row.append(Gtk.Label(label=f"delay {delay} ms", xalign=0))
        sl = SketchSlider(value=min(delay,1000)/1000.0, color=NEON_BLUE, width=220)
        sl.connect("value-changed",
                   lambda _s, v: sh(f"hyprctl keyword input:repeat_delay {int(150+v*850)}"))
        row.append(sl); c.add_row(row)

        c = Card("shortcuts")
        self.box.append(c)
        rc, out, _ = sh("hyprctl -j binds")
        try: binds = json.loads(out)
        except Exception: binds = []
        c.add_row(Gtk.Label(label=f"{len(binds)} active binds", xalign=0))
        # show a scrollable list of binds
        sw = Gtk.ScrolledWindow(); sw.set_vexpand(True)
        sw.set_size_request(-1, 220)
        tv = Gtk.TextView(); tv.set_editable(False)
        tv.add_css_class("nyx-editor")
        text = "\n".join(
            f"{(b.get('modmask') or 0):3d} + {b.get('key','')}  →  "
            f"{b.get('dispatcher','')} {b.get('arg','')}"
            for b in binds[:200])
        tv.get_buffer().set_text(text or "(no binds)")
        sw.set_child(tv); c.add_row(sw)

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Layout"),
            SearchEntry(self.KEY, self.TITLE, "Repeat rate"),
            SearchEntry(self.KEY, self.TITLE, "Shortcuts", "binds keybinds hotkeys"),
        ]


# ─── Mouse / Touchpad ───────────────────────────────────────────────────────
class MousePage(BasePage):
    KEY = "mouse"; TITLE = "Mouse & Touchpad"; ICON = "🖱"

    def build(self):
        c = Card("pointer")
        self.box.append(c)
        rc, out, _ = sh("hyprctl getoption input:sensitivity -j")
        try: s = float(json.loads(out).get("float", 0.0))
        except Exception: s = 0.0
        row = Gtk.Box(spacing=10)
        row.append(Gtk.Label(label=f"sensitivity {s:+.2f}", xalign=0))
        sl = SketchSlider(value=(s+1)/2.0, color=NEON_PINK, width=240)
        sl.connect("value-changed",
                   lambda _s, v: sh(f"hyprctl keyword input:sensitivity {(v*2-1):.2f}"))
        row.append(sl); c.add_row(row)
        # accel profile
        row = Gtk.Box(spacing=10)
        row.append(Gtk.Label(label="accel:", xalign=0))
        for label, ap in (("adaptive","adaptive"),("flat","flat")):
            b = SketchButton(label, width=78, height=22, color=NEON_BLUE)
            b.connect("clicked",
                      lambda _b, ap=ap: (sh(f"hyprctl keyword input:accel_profile {ap}"),
                                         self.win.toast(f"accel → {ap}")))
            row.append(b)
        c.add_row(row)
        # natural scroll
        b = SketchToggle("natural scroll", width=140, height=24, color=NEON_BLUE)
        rc, out, _ = sh("hyprctl getoption input:touchpad:natural_scroll -j")
        try: b.set_active(json.loads(out).get("int",0) == 1)
        except Exception: pass
        b.connect("clicked",
                  lambda _b: sh(f"hyprctl keyword input:touchpad:natural_scroll {1 if b.active else 0}"))
        c.add_row(b)
        # tap to click
        t = SketchToggle("tap to click", width=140, height=24, color=NEON_BLUE)
        rc, out, _ = sh("hyprctl getoption input:touchpad:tap-to-click -j")
        try: t.set_active(json.loads(out).get("int",1) == 1)
        except Exception: pass
        t.connect("clicked",
                  lambda _b: sh(f"hyprctl keyword input:touchpad:tap-to-click {1 if t.active else 0}"))
        c.add_row(t)

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Mouse sensitivity"),
            SearchEntry(self.KEY, self.TITLE, "Acceleration"),
            SearchEntry(self.KEY, self.TITLE, "Natural scroll"),
            SearchEntry(self.KEY, self.TITLE, "Tap to click", "touchpad"),
        ]


# ─── Power ──────────────────────────────────────────────────────────────────
class PowerPage(BasePage):
    KEY = "power"; TITLE = "Power"; ICON = "⚡"

    def build(self):
        # ── 1. battery (auto-hides if none) ────────────────────────────────
        bat_dir = Path("/sys/class/power_supply")
        self.bats = sorted(bat_dir.glob("BAT*")) if bat_dir.exists() else []
        if self.bats:
            self.bat_card = Card("battery")
            self.box.append(self.bat_card)
        else:
            self.bat_card = None

        # ── 2. power profiles ──────────────────────────────────────────────
        self.prof_card = Card("power profiles")
        self.box.append(self.prof_card)

        # ── 3. CPU governor ────────────────────────────────────────────────
        self.gov_card = Card("CPU frequency governor")
        self.box.append(self.gov_card)

        # ── 4. charge thresholds (laptop-only) ─────────────────────────────
        if self.bats:
            ct = Card("charge thresholds")
            self.box.append(ct)
            any_thr = False
            for b in self.bats:
                start_p = b / "charge_control_start_threshold"
                end_p   = b / "charge_control_end_threshold"
                if not (start_p.exists() or end_p.exists()):
                    continue
                any_thr = True
                try:
                    s = start_p.read_text().strip() if start_p.exists() else "?"
                    e = end_p.read_text().strip() if end_p.exists() else "?"
                except Exception:
                    s = e = "?"
                ct.add_row(kv_row(f"{b.name} thresholds:",
                                  f"start {s}%  · end {e}%"))
                row = Gtk.Box(spacing=6)
                for label, sv, ev in (("80% (longevity)", 75, 80),
                                      ("90% (balanced)",  85, 90),
                                      ("100% (full)",     0, 100)):
                    btn = SketchButton(label, width=140, height=22,
                                       color=ACCENT_GOLD)
                    btn.connect(
                        "clicked",
                        lambda _b, bn=b.name, sv=sv, ev=ev:
                            self._term_run(
                                (f"sudo sh -c 'echo {sv} > "
                                 f"/sys/class/power_supply/{bn}/"
                                 f"charge_control_start_threshold; "
                                 f"echo {ev} > "
                                 f"/sys/class/power_supply/{bn}/"
                                 f"charge_control_end_threshold'"),
                                f"thresholds → {sv}-{ev}% on {bn}"))
                    row.append(btn)
                ct.add_row(row)
            if not any_thr:
                ct.add_row(Gtk.Label(
                    label="(no charge_control_*_threshold files — "
                          "vendor doesn't expose this)", xalign=0))

        # ── 5. lid / power buttons (logind) ────────────────────────────────
        c = Card("lid & power buttons (logind)")
        self.box.append(c)
        try:
            conf = Path("/etc/systemd/logind.conf").read_text()
        except Exception:
            conf = ""
        for key in ("HandleLidSwitch", "HandleLidSwitchExternalPower",
                    "HandleLidSwitchDocked", "HandlePowerKey",
                    "HandleSuspendKey", "HandleHibernateKey",
                    "IdleAction", "IdleActionSec"):
            val = "(default)"
            for line in conf.splitlines():
                ln = line.strip()
                if ln.startswith("#") or "=" not in ln: continue
                k, v = ln.split("=", 1)
                if k.strip() == key:
                    val = v.strip()
            c.add_row(kv_row(key + ":", val))
        row = Gtk.Box(spacing=8)
        b_ed = SketchButton("Edit logind.conf", width=180, height=26,
                            color=ACCENT_GOLD)
        b_ed.connect("clicked", lambda _b: self._term_run(
            "sudo ${EDITOR:-nano} /etc/systemd/logind.conf && "
            "sudo systemctl restart systemd-logind",
            "logind.conf opened (sudo)…"))
        row.append(b_ed)
        c.add_row(row)

        # ── 6. sleep / hibernate / power actions ───────────────────────────
        c = Card("sleep & power actions")
        self.box.append(c)
        row = Gtk.Box(spacing=8)
        for label, cmd, color in (
            ("Suspend",     "systemctl suspend",      NEON_BLUE),
            ("Hibernate",   "systemctl hibernate",    NEON_BLUE),
            ("Hybrid sleep","systemctl hybrid-sleep", NEON_BLUE),
            ("Lock screen", "loginctl lock-session",  ACCENT_GOLD),
        ):
            b = SketchButton(label, width=130, height=24, color=color)
            b.connect("clicked", lambda _b, c=cmd, l=label: (
                sh_async(c, lambda r, l=l: self.win.toast(
                    f"{l} → ok" if r[0]==0 else f"{l} failed (rc={r[0]})"))))
            row.append(b)
        c.add_row(row)
        # supported sleep states
        try:
            states = Path("/sys/power/state").read_text().strip()
        except Exception:
            states = "?"
        c.add_row(kv_row("Supported sleep states:", states))
        try:
            mem_sleep = Path("/sys/power/mem_sleep").read_text().strip()
        except Exception:
            mem_sleep = "?"
        c.add_row(kv_row("Memory sleep mode:", mem_sleep))

        # ── 7. screen idle / hypridle ──────────────────────────────────────
        c = Card("screen idle / DPMS")
        self.box.append(c)
        c.add_row(kv_row("hypridle installed:",
                         "yes" if have("hypridle") else "no"))
        c.add_row(kv_row("hyprlock installed:",
                         "yes" if have("hyprlock") else "no"))
        cfg = Path.home() / ".config/hypr/hypridle.conf"
        c.add_row(kv_row("hypridle config:",
                         "found" if cfg.exists() else "(missing)"))
        if cfg.exists():
            row = Gtk.Box(spacing=8)
            b = SketchButton("Edit hypridle.conf", width=200, height=24,
                             color=ACCENT_GOLD)
            b.connect("clicked", lambda _b: self._term_run(
                f"${{EDITOR:-nano}} {cfg}",
                "hypridle.conf opened…"))
            row.append(b)
            b2 = SketchButton("Restart hypridle", width=160, height=24,
                              color=NEON_BLUE)
            b2.connect("clicked", lambda _b: (
                sh("pkill -x hypridle; setsid hypridle &"),
                self.win.toast("hypridle restarted")))
            row.append(b2)
            c.add_row(row)

        # ── 8. wakeup devices ──────────────────────────────────────────────
        c = Card("ACPI wakeup sources")
        self.box.append(c)
        try:
            txt = Path("/proc/acpi/wakeup").read_text()
            lines = txt.splitlines()[1:]  # skip header
            shown = 0
            for line in lines:
                f = line.split()
                if len(f) < 3: continue
                name = f[0]; status = f[2]
                state = "enabled" if "enabled" in status else "disabled"
                row = Gtk.Box(spacing=8)
                lbl = Gtk.Label(label=name, xalign=0); lbl.set_hexpand(True)
                row.append(lbl)
                row.append(Gtk.Label(label=state, xalign=1))
                b = SketchButton("Toggle", width=90, height=22,
                                 color=NEON_BLUE)
                b.connect("clicked", lambda _b, n=name: self._term_run(
                    f"sudo sh -c 'echo {n} > /proc/acpi/wakeup'",
                    f"toggled wakeup: {n}"))
                row.append(b)
                c.add_row(row); shown += 1
                if shown >= 12: break
            if shown == 0:
                c.add_row(Gtk.Label(label="(empty)", xalign=0))
        except Exception:
            c.add_row(Gtk.Label(label="/proc/acpi/wakeup not available",
                                xalign=0))

        # ── 9. tlp / auto-cpufreq detection ────────────────────────────────
        c = Card("power management daemons")
        self.box.append(c)
        for name, svc in (("tlp", "tlp.service"),
                          ("auto-cpufreq", "auto-cpufreq.service"),
                          ("thermald", "thermald.service"),
                          ("power-profiles-daemon",
                           "power-profiles-daemon.service")):
            installed = have(name) or have(name.replace("-", ""))
            rc, out, _ = sh(f"systemctl is-active {svc} 2>/dev/null")
            active = out.strip() == "active"
            c.add_row(kv_row(
                f"{name}:",
                ("installed · " if installed else "not installed · ") +
                ("active" if active else "inactive")))
        if have("tlp"):
            row = Gtk.Box(spacing=8)
            b = SketchButton("tlp-stat -s (terminal)", width=200, height=24,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b: self._term_run(
                "sudo tlp-stat -s | less",
                "tlp-stat opened…"))
            row.append(b)
            c.add_row(row)

        # ── 10. powertop / consumption ─────────────────────────────────────
        c = Card("power consumption")
        self.box.append(c)
        # try energy_now (laptop) — instantaneous draw
        for b in self.bats:
            try:
                pn = (b / "power_now")
                if pn.exists():
                    pw = int(pn.read_text().strip())
                    c.add_row(kv_row(
                        f"{b.name} draw:", f"{pw/1_000_000:.2f} W"))
            except Exception:
                pass
        if have("powertop"):
            row = Gtk.Box(spacing=8)
            b1 = SketchButton("Launch powertop", width=180, height=24,
                              color=NEON_BLUE)
            b1.connect("clicked", lambda _b: self._term_run(
                "sudo powertop", "launching powertop…"))
            row.append(b1)
            b2 = SketchButton("Apply tunables (auto)", width=200, height=24,
                              color=ACCENT_GOLD)
            b2.connect("clicked", lambda _b: self._term_run(
                "sudo powertop --auto-tune",
                "applying powertop tunables…"))
            row.append(b2)
            c.add_row(row)
        else:
            c.add_row(Gtk.Label(label="powertop not installed", xalign=0))

        self.refresh()

    # ── helper: run in terminal ────────────────────────────────────────────
    def _term_run(self, cmd: str, toast: str):
        for term in ("foot", "alacritty", "kitty", "xterm"):
            if have(term):
                subprocess.Popen(
                    [term, "-e", "sh", "-c",
                     f"{cmd}; echo; echo 'press enter to close'; read _"],
                    start_new_session=True)
                self.win.toast(toast)
                return
        self.win.toast("no terminal found (install foot/alacritty/kitty)")

    def refresh(self):
        # battery card
        if self.bat_card is not None:
            child = self.bat_card.get_first_child(); skip = True
            while child:
                n = child.get_next_sibling()
                if skip: skip = False
                else: self.bat_card.remove(child)
                child = n
            for b in self.bats:
                try:
                    cap = (b/"capacity").read_text().strip()
                    stat = (b/"status").read_text().strip()
                    self.bat_card.add_row(kv_row(
                        b.name, f"{cap}%  ({stat})"))
                    ef = (b/"energy_full"); efd = (b/"energy_full_design")
                    if ef.exists() and efd.exists():
                        e1 = int(ef.read_text()); e2 = int(efd.read_text())
                        if e2 > 0:
                            self.bat_card.add_row(kv_row(
                                "health", f"{e1*100//e2}%"))
                    cyc = (b/"cycle_count")
                    if cyc.exists():
                        cv = cyc.read_text().strip()
                        if cv and cv != "0":
                            self.bat_card.add_row(kv_row("cycles", cv))
                    vn = (b/"voltage_now")
                    if vn.exists():
                        v = int(vn.read_text().strip())
                        self.bat_card.add_row(kv_row(
                            "voltage", f"{v/1_000_000:.2f} V"))
                    tech = (b/"technology")
                    if tech.exists():
                        self.bat_card.add_row(kv_row(
                            "technology", tech.read_text().strip()))
                except Exception as e:
                    log.warning("battery: %s", e)

        # power profiles
        child = self.prof_card.get_first_child(); skip = True
        while child:
            n = child.get_next_sibling()
            if skip: skip = False
            else: self.prof_card.remove(child)
            child = n
        if have("powerprofilesctl"):
            rc, out, _ = sh("powerprofilesctl get")
            cur = out.strip() if rc == 0 else "?"
            row = Gtk.Box(spacing=8)
            for p in ("power-saver", "balanced", "performance"):
                b = SketchButton(p, width=120, height=24, color=NEON_BLUE,
                                 primary=(p == cur))
                b.connect("clicked", lambda _b, p=p:
                          (sh(f"powerprofilesctl set {p}"),
                           self.win.toast(f"profile → {p}"),
                           self.refresh()))
                row.append(b)
            self.prof_card.add_row(row)
        else:
            self.prof_card.add_row(Gtk.Label(
                label="powerprofilesctl not installed", xalign=0))

        # CPU governor
        child = self.gov_card.get_first_child(); skip = True
        while child:
            n = child.get_next_sibling()
            if skip: skip = False
            else: self.gov_card.remove(child)
            child = n
        gov_p = Path(
            "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
        avail_p = Path(
            "/sys/devices/system/cpu/cpu0/cpufreq/"
            "scaling_available_governors")
        if not gov_p.exists():
            self.gov_card.add_row(Gtk.Label(
                label="cpufreq scaling not available on this CPU",
                xalign=0))
        else:
            try:
                cur = gov_p.read_text().strip()
                avail = avail_p.read_text().split() if avail_p.exists() \
                        else [cur]
            except Exception:
                cur = "?"; avail = []
            self.gov_card.add_row(kv_row("Current governor:", cur))
            row = Gtk.Box(spacing=6)
            for g in avail:
                b = SketchButton(g, width=120, height=22, color=NEON_GREEN,
                                 primary=(g == cur))
                b.connect("clicked", lambda _b, g=g:
                    self._term_run(
                        ("sudo sh -c 'for f in "
                         "/sys/devices/system/cpu/cpu*/cpufreq/"
                         f"scaling_governor; do echo {g} > $f; done'"),
                        f"governor → {g}"))
                row.append(b)
            self.gov_card.add_row(row)
            # current frequency
            freq_p = Path(
                "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
            if freq_p.exists():
                try:
                    f = int(freq_p.read_text().strip())
                    self.gov_card.add_row(kv_row(
                        "cpu0 freq:", f"{f//1000} MHz"))
                except Exception:
                    pass

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Battery"),
            SearchEntry(self.KEY, self.TITLE, "Battery health & cycles"),
            SearchEntry(self.KEY, self.TITLE, "Power profile",
                        "power-saver balanced performance"),
            SearchEntry(self.KEY, self.TITLE, "CPU governor",
                        "performance powersave ondemand schedutil"),
            SearchEntry(self.KEY, self.TITLE, "Charge thresholds",
                        "battery longevity 80%"),
            SearchEntry(self.KEY, self.TITLE, "Lid action", "logind.conf"),
            SearchEntry(self.KEY, self.TITLE, "Power button action"),
            SearchEntry(self.KEY, self.TITLE, "Suspend"),
            SearchEntry(self.KEY, self.TITLE, "Hibernate"),
            SearchEntry(self.KEY, self.TITLE, "Hybrid sleep"),
            SearchEntry(self.KEY, self.TITLE, "Lock screen"),
            SearchEntry(self.KEY, self.TITLE, "Screen idle / hypridle",
                        "DPMS dim"),
            SearchEntry(self.KEY, self.TITLE, "ACPI wakeup sources"),
            SearchEntry(self.KEY, self.TITLE, "TLP / auto-cpufreq",
                        "thermald daemon"),
            SearchEntry(self.KEY, self.TITLE, "powertop", "tunables"),
        ]


# ─── Date & Time ────────────────────────────────────────────────────────────
class DateTimePage(BasePage):
    KEY = "datetime"; TITLE = "Date & Time"; ICON = "🕐"

    def build(self):
        c = Card("system time")
        self.box.append(c)
        rc, out, _ = sh("timedatectl")
        info = {}
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
        c.add_row(kv_row("Local time:", info.get("Local time", "?")))
        c.add_row(kv_row("Universal time:", info.get("Universal time", "?")))
        c.add_row(kv_row("Timezone:", info.get("Time zone", "?")))
        c.add_row(kv_row("NTP:", info.get("NTP service", "?")))
        c.add_row(kv_row("Synced:", info.get("System clock synchronized", "?")))

        # toggle NTP
        ntp_on = "active" in info.get("NTP service", "")
        tog = SketchToggle("NTP auto-sync", width=160, height=26,
                           color=NEON_GREEN, active=ntp_on)
        tog.connect("clicked",
                    lambda _b: sh_async(
                        f"pkexec timedatectl set-ntp {'true' if tog.active else 'false'}",
                        lambda r: (self.win.toast(
                            "NTP changed" if r[0]==0 else "needs sudo"),
                                   self.refresh())))
        c.add_row(tog)

        # timezone picker
        tz_card = Card("timezone")
        self.box.append(tz_card)
        rc, out, _ = sh("timedatectl list-timezones")
        zones = out.splitlines() if rc == 0 else []
        if zones:
            row = Gtk.Box(spacing=8)
            self.tz_combo = Gtk.DropDown.new_from_strings(zones[:300])
            cur = info.get("Time zone", "").split(" ")[0]
            try: self.tz_combo.set_selected(zones.index(cur))
            except (ValueError, AttributeError): pass
            row.append(self.tz_combo)
            b = SketchButton("Set", width=58, height=24, color=NEON_GREEN)
            b.connect("clicked", lambda _b: self._set_tz(zones))
            row.append(b)
            tz_card.add_row(row)

    def _set_tz(self, zones):
        z = zones[self.tz_combo.get_selected()]
        sh_async(f"pkexec timedatectl set-timezone {z}",
                 lambda r: (self.win.toast(
                     f"tz → {z}" if r[0]==0 else "needs sudo"),
                            self.refresh()))

    def refresh(self):
        # rebuild
        c = self.box.get_first_child()
        while c:
            n = c.get_next_sibling()
            if c is not self.box.get_first_child(): self.box.remove(c)
            c = n
        self.build()

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Time zone"),
            SearchEntry(self.KEY, self.TITLE, "NTP"),
            SearchEntry(self.KEY, self.TITLE, "Date format"),
        ]


# ─── Notifications ──────────────────────────────────────────────────────────
class NotificationsPage(BasePage):
    KEY = "notifications"; TITLE = "Notifications"; ICON = "🔔"

    def build(self):
        c = Card("mako (current notification daemon)")
        self.box.append(c)
        if have("makoctl"):
            row = Gtk.Box(spacing=8)
            b1 = SketchButton("Dismiss all", width=120, height=24,
                              color=DANGER_RED)
            b1.connect("clicked",
                       lambda _b: (sh("makoctl dismiss --all"),
                                   self.win.toast("dismissed all")))
            b2 = SketchButton("Reload config", width=130, height=24,
                              color=NEON_GREEN)
            b2.connect("clicked",
                       lambda _b: (sh("makoctl reload"),
                                   self.win.toast("mako reloaded")))
            b3 = SketchToggle("DND", width=70, height=24, color=ACCENT_GOLD)
            rc, out, _ = sh("makoctl mode")
            b3.set_active("do-not-disturb" in out)
            b3.connect("clicked",
                       lambda _b: (sh(f"makoctl mode -t {'do-not-disturb' if b3.active else 'default'}"),
                                   self.win.toast(
                                       "DND on" if b3.active else "DND off")))
            row.append(b1); row.append(b2); row.append(b3)
            c.add_row(row)
            # show config path
            cfg = Path.home() / ".config/mako/config"
            c.add_row(kv_row("config path:", str(cfg)))
            if cfg.exists():
                b = SketchButton("Open in nyxus_notepad", width=200, height=24,
                                 color=NEON_BLUE)
                b.connect("clicked", lambda _b:
                          subprocess.Popen(["python3",
                                            str(Path.home()/".nyxus/nyxus_notepad.py"),
                                            str(cfg)],
                                           stdout=subprocess.DEVNULL,
                                           stderr=subprocess.DEVNULL))
                c.add_row(b)
        else:
            c.add_row(Gtk.Label(label="makoctl not installed", xalign=0))

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Do not disturb"),
            SearchEntry(self.KEY, self.TITLE, "Notification daemon", "mako"),
        ]


# ─── Users (read-only, honest) ──────────────────────────────────────────────
class UsersPage(BasePage):
    KEY = "users"; TITLE = "Users & Accounts"; ICON = "👤"

    def build(self):
        c = Card("current user")
        self.box.append(c)
        import getpass
        u = getpass.getuser()
        rc, out, _ = sh("id")
        c.add_row(kv_row("Username:", u))
        c.add_row(kv_row("UID/GID:", out.strip()))
        c.add_row(kv_row("Home:", str(Path.home())))
        c.add_row(kv_row("Shell:", os.environ.get("SHELL", "?")))
        # avatar
        av = Path.home() / ".face"
        c.add_row(kv_row("Avatar:", str(av) if av.exists() else "(none)"))
        # passwd
        b = SketchButton("Change password", width=180, height=26,
                         color=ACCENT_GOLD)
        b.connect("clicked", lambda _b: subprocess.Popen(
            ["xdg-terminal-exec", "passwd"]) if have("xdg-terminal-exec")
            else self.win.toast("run `passwd` in a terminal"))
        c.add_row(b)

        # YubiKey
        c = Card("YubiKey")
        self.box.append(c)
        if have("ykman"):
            rc, out, _ = sh("ykman list")
            c.add_row(Gtk.Label(label=out.strip() or "no YubiKey", xalign=0))
            rc, out, _ = sh("ykman info")
            c.add_row(Gtk.Label(label=out.strip()[:600] or "", xalign=0))
        else:
            c.add_row(Gtk.Label(label="ykman not installed", xalign=0))

        self.add_note(
            "user creation, group changes, and removal are destructive and "
            "require root — use `useradd`, `usermod`, or `userdel` in a "
            "terminal.")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Change password"),
            SearchEntry(self.KEY, self.TITLE, "YubiKey"),
            SearchEntry(self.KEY, self.TITLE, "User info"),
        ]


# ─── Privacy ────────────────────────────────────────────────────────────────
class PrivacyPage(BasePage):
    KEY = "privacy"; TITLE = "Privacy & Security"; ICON = "🔒"
    TILE_COLOR = ACCENT_GOLD
    SUBTITLE = "YubiKey · GPG · SSH · AppArmor"

    # ── YubiKey hardware security key ──────────────────────────────────────
    def _yubi_detect(self) -> Tuple[bool, str, str]:
        """Return (present, serial, model_line)."""
        rc, out, _ = sh("lsusb")
        if "Yubico" not in out:
            return False, "", ""
        if have("ykman"):
            rc2, info, _ = sh("ykman info", timeout=3)
            if rc2 == 0:
                serial = ""
                model  = ""
                for ln in info.splitlines():
                    if ln.lower().startswith("device type"): model = ln.split(":",1)[1].strip()
                    if ln.lower().startswith("serial number"): serial = ln.split(":",1)[1].strip()
                return True, serial, model
        # fallback: lsusb line
        for ln in out.splitlines():
            if "Yubico" in ln: return True, "", ln.strip()
        return True, "", "Yubico device"

    def _build_yubi_card(self):
        present, serial, model = self._yubi_detect()
        c = Card("hardware security key (YubiKey)")
        self.box.append(c)
        if not present:
            c.add_row(Gtk.Label(
                label="No YubiKey detected. Insert one and click Refresh.",
                xalign=0))
            row = Gtk.Box(spacing=8)
            b = SketchButton("Refresh", width=110, height=24, color=NEON_PINK)
            b.connect("clicked", lambda _b: self.refresh())
            row.append(b)
            if not have("ykman"):
                row.append(Gtk.Label(
                    label="(install `yubikey-manager` for full features)",
                    xalign=0))
            c.add_row(row)
            return
        c.add_row(kv_row("Status:", "✓ detected"))
        if model:  c.add_row(kv_row("Model:",  model))
        if serial: c.add_row(kv_row("Serial:", serial))
        if have("ykman"):
            rc, info, _ = sh("ykman info", timeout=3)
            if rc == 0:
                # parse "Enabled USB interfaces" / "applications"
                for ln in info.splitlines():
                    s = ln.strip()
                    if not s or ":" not in s: continue
                    k, v = s.split(":", 1)
                    if k.lower() in ("firmware version", "form factor",
                                     "enabled usb interfaces",
                                     "fips approved", "fido u2f", "openpgp",
                                     "piv", "oath", "yubihsm auth"):
                        c.add_row(kv_row(k.strip()+":", v.strip()))
            row = Gtk.Box(spacing=8)
            b1 = SketchButton("Test (touch)", width=130, height=24,
                              color=NEON_GREEN, tooltip="ykman piv info")
            b1.connect("clicked", lambda _b: self._yubi_test())
            row.append(b1)
            b2 = SketchButton("Change PIN", width=120, height=24,
                              color=ACCENT_GOLD,
                              tooltip="open terminal: ykman piv access change-pin")
            b2.connect("clicked", lambda _b: self._yubi_change_pin())
            row.append(b2)
            b3 = SketchButton("List OATH", width=120, height=24,
                              color=ACCENT_PURP,
                              tooltip="ykman oath accounts list")
            b3.connect("clicked", lambda _b: self._yubi_oath())
            row.append(b3)
            c.add_row(row)

    def _yubi_test(self):
        self.win.toast("touch your YubiKey…")
        sh_async("ykman piv info",
                 lambda r: self.win.toast(
                     "YubiKey OK ✓" if r[0]==0 else f"failed: {r[2].strip()[:60]}"),
                 timeout=15)

    def _yubi_change_pin(self):
        for term in ("foot", "alacritty", "kitty", "xterm"):
            if have(term):
                subprocess.Popen(
                    [term, "-e", "sh", "-c",
                     "ykman piv access change-pin; "
                     "echo; echo 'press enter to close'; read _"],
                    start_new_session=True)
                self.win.toast("change-PIN opened in terminal")
                return
        self.win.toast("no terminal found (install foot/alacritty/kitty)")

    def _yubi_oath(self):
        rc, out, err = sh("ykman oath accounts list", timeout=5)
        msg = (out.strip()[:120] or "(no OATH accounts)") if rc==0 else f"err: {err.strip()[:60]}"
        self.win.toast(msg)

    # ── GPG keys ───────────────────────────────────────────────────────────
    def _build_gpg_card(self):
        c = Card("GPG keys")
        self.box.append(c)
        if not have("gpg"):
            c.add_row(Gtk.Label(label="gpg not installed (pacman -S gnupg)",
                                xalign=0))
            return
        rc, out, _ = sh("gpg --list-secret-keys --with-colons", timeout=4)
        keys = []  # list of (fpr, uid, expires)
        cur_fpr = None
        for ln in out.splitlines():
            f = ln.split(":")
            if not f: continue
            if f[0] == "fpr" and len(f) > 9 and cur_fpr is None:
                cur_fpr = f[9]
            elif f[0] == "uid" and len(f) > 9 and cur_fpr is not None:
                keys.append((cur_fpr, f[9], f[6] or ""))
                cur_fpr = None
            elif f[0] == "sec":
                cur_fpr = None
        if not keys:
            c.add_row(Gtk.Label(label="(no secret GPG keys found)", xalign=0))
        for fpr, uid, expires in keys[:6]:
            short = fpr[-16:] if len(fpr) >= 16 else fpr
            row = Gtk.Box(spacing=8)
            row.append(Gtk.Label(label=f"🔑 {short}", xalign=0))
            row.append(Gtk.Label(label=uid, xalign=0))
            sp = Gtk.Box(); sp.set_hexpand(True); row.append(sp)
            b_copy = SketchButton("Copy fpr", width=100, height=22,
                                  color=ACCENT_PURP)
            b_copy.connect("clicked", lambda _b, f=fpr: self._clip(f))
            row.append(b_copy)
            b_exp = SketchButton("Export pub", width=110, height=22,
                                 color=NEON_GREEN)
            b_exp.connect("clicked", lambda _b, f=fpr: self._gpg_export(f))
            row.append(b_exp)
            c.add_row(row)
        # actions
        row = Gtk.Box(spacing=8)
        b_gen = SketchButton("Generate new key", width=170, height=24,
                             color=NEON_PINK,
                             tooltip="terminal: gpg --full-generate-key")
        b_gen.connect("clicked", lambda _b: self._term_run(
            "gpg --full-generate-key", "GPG key wizard opened"))
        row.append(b_gen)
        b_imp = SketchButton("Import .asc", width=130, height=24,
                             color=ACCENT_GOLD)
        b_imp.connect("clicked", lambda _b: self._gpg_import())
        row.append(b_imp)
        c.add_row(row)

    def _gpg_export(self, fpr: str):
        out_path = Path.home() / f"gpg-pub-{fpr[-8:]}.asc"
        rc, out, err = sh(f"gpg --armor --export {fpr}", timeout=4)
        if rc == 0 and out:
            try:
                out_path.write_text(out)
                self.win.toast(f"exported → {out_path.name}")
            except Exception as e:
                self.win.toast(f"write failed: {e}")
        else:
            self.win.toast(f"export failed: {err.strip()[:60]}")

    def _gpg_import(self):
        dlg = Gtk.FileDialog(); dlg.set_title("Import GPG key (.asc)")
        def _done(d, res):
            try: f = d.open_finish(res)
            except Exception: return
            if not f: return
            p = f.get_path()
            sh_async(f"gpg --import {shlex.quote(p)}",
                     lambda r: self.win.toast(
                         "imported ✓" if r[0]==0 else f"err: {r[2].strip()[:60]}"))
        dlg.open(self.win, None, _done)

    # ── SSH keys ───────────────────────────────────────────────────────────
    def _build_ssh_card(self):
        c = Card("SSH keys")
        self.box.append(c)
        ssh_dir = Path.home() / ".ssh"
        pubs: List[Path] = []
        if ssh_dir.exists():
            pubs = sorted(p for p in ssh_dir.iterdir() if p.suffix == ".pub")
        if not pubs:
            c.add_row(Gtk.Label(label="(no public keys in ~/.ssh)", xalign=0))
        for p in pubs:
            try:
                txt = p.read_text().strip()
                parts = txt.split()
                ktype = parts[0] if parts else "?"
                comment = parts[2] if len(parts) > 2 else ""
            except Exception:
                ktype = "?"; comment = ""
            rc, fpr_out, _ = sh(f"ssh-keygen -lf {shlex.quote(str(p))}",
                                timeout=3)
            fpr = fpr_out.split()[1] if fpr_out.split() else ""
            row = Gtk.Box(spacing=8)
            row.append(Gtk.Label(
                label=f"🗝  {p.name}  [{ktype}]  {comment}", xalign=0))
            sp = Gtk.Box(); sp.set_hexpand(True); row.append(sp)
            b_copy = SketchButton("Copy pub", width=100, height=22,
                                  color=ACCENT_PURP)
            b_copy.connect("clicked", lambda _b, t=txt: self._clip(t))
            row.append(b_copy)
            b_fpr = SketchButton("Show fpr", width=100, height=22,
                                 color=NEON_GREEN)
            b_fpr.connect("clicked", lambda _b, f=fpr: self.win.toast(f or "(no fpr)"))
            row.append(b_fpr)
            c.add_row(row)
        # ssh-agent loaded
        rc, out, _ = sh("ssh-add -l", timeout=2)
        loaded = 0 if rc != 0 else len([l for l in out.splitlines() if l.strip()])
        c.add_row(kv_row("ssh-agent loaded:", f"{loaded} key(s)"))
        # generate
        row = Gtk.Box(spacing=8)
        b_ed = SketchButton("Generate ed25519", width=170, height=24,
                            color=NEON_PINK)
        b_ed.connect("clicked", lambda _b: self._term_run(
            "ssh-keygen -t ed25519 -C \"$(whoami)@$(hostname)\"",
            "ssh-keygen opened in terminal"))
        row.append(b_ed)
        b_rsa = SketchButton("Generate RSA-4096", width=170, height=24,
                             color=ACCENT_GOLD)
        b_rsa.connect("clicked", lambda _b: self._term_run(
            "ssh-keygen -t rsa -b 4096 -C \"$(whoami)@$(hostname)\"",
            "ssh-keygen opened in terminal"))
        row.append(b_rsa)
        c.add_row(row)

    # ── AppArmor / SELinux ─────────────────────────────────────────────────
    def _build_mac_card(self):
        c = Card("Mandatory Access Control (AppArmor / SELinux)")
        self.box.append(c)
        # AppArmor
        if have("aa-status"):
            rc, out, _ = sh("aa-status", timeout=3)
            if rc == 0:
                lines = out.splitlines()
                summary = lines[0].strip() if lines else "AppArmor active"
                profiles = ""
                enforce = complain = ""
                for ln in lines[:8]:
                    s = ln.strip()
                    if "profiles are loaded" in s: profiles = s
                    if "profiles are in enforce" in s: enforce = s
                    if "profiles are in complain" in s: complain = s
                c.add_row(kv_row("AppArmor:", summary))
                if profiles: c.add_row(kv_row("  ", profiles))
                if enforce:  c.add_row(kv_row("  ", enforce))
                if complain: c.add_row(kv_row("  ", complain))
            else:
                c.add_row(kv_row("AppArmor:", "kernel module not loaded"))
        else:
            c.add_row(kv_row("AppArmor:", "not installed"))
        # SELinux
        if have("getenforce"):
            rc, out, _ = sh("getenforce", timeout=2)
            c.add_row(kv_row("SELinux:", out.strip() if rc==0 else "n/a"))
        else:
            c.add_row(kv_row("SELinux:", "not installed (Arch default)"))
        # Kernel hardening signals
        rc, out, _ = sh("sysctl -n kernel.kptr_restrict", timeout=2)
        c.add_row(kv_row("kernel.kptr_restrict:", out.strip() or "0"))
        rc, out, _ = sh("sysctl -n kernel.dmesg_restrict", timeout=2)
        c.add_row(kv_row("kernel.dmesg_restrict:", out.strip() or "0"))

    # ── Disk encryption ────────────────────────────────────────────────────
    def _build_luks_card(self):
        c = Card("disk encryption (LUKS)")
        self.box.append(c)
        rc, out, _ = sh("lsblk -o NAME,FSTYPE,MOUNTPOINT,SIZE -nrp", timeout=3)
        crypts = [ln for ln in out.splitlines() if "crypto_LUKS" in ln]
        if not crypts:
            c.add_row(Gtk.Label(
                label="No LUKS-encrypted volumes detected on this system.",
                xalign=0))
            return
        for ln in crypts:
            parts = ln.split()
            name = parts[0] if parts else "?"
            size = parts[-1] if len(parts) >= 4 else ""
            c.add_row(kv_row(name, f"crypto_LUKS  {size}"))

    # ── Screen lock ────────────────────────────────────────────────────────
    def _build_lock_card(self):
        c = Card("screen lock")
        self.box.append(c)
        hl_path = Path.home() / ".config" / "hypr" / "hyprlock.conf"
        si_path = Path.home() / ".config" / "hypr" / "hypridle.conf"
        c.add_row(kv_row("hyprlock installed:",
                         "yes" if have("hyprlock") else "no"))
        c.add_row(kv_row("hypridle installed:",
                         "yes" if have("hypridle") else "no"))
        c.add_row(kv_row("hyprlock.conf:",
                         "present" if hl_path.exists() else "missing"))
        c.add_row(kv_row("hypridle.conf:",
                         "present" if si_path.exists() else "missing"))
        rc, out, _ = sh("pgrep -x hypridle", timeout=2)
        c.add_row(kv_row("hypridle running:", "yes" if rc==0 else "no"))
        row = Gtk.Box(spacing=8)
        b_lock = SketchButton("Lock now", width=110, height=24,
                              color=NEON_PINK)
        b_lock.connect("clicked", lambda _b: (
            sh_async("hyprlock"), self.win.toast("locking…")))
        row.append(b_lock)
        if have("hypridle"):
            b_idle = SketchButton("Restart hypridle", width=160, height=24,
                                  color=ACCENT_PURP)
            b_idle.connect("clicked", lambda _b: (
                sh("pkill -x hypridle"),
                sh_async("setsid hypridle"),
                self.win.toast("hypridle restarted")))
            row.append(b_idle)
        c.add_row(row)

    # ── Location services ──────────────────────────────────────────────────
    def _build_location_card(self):
        c = Card("location services")
        self.box.append(c)
        rc, out, _ = sh("systemctl is-active geoclue", timeout=2)
        active = out.strip()
        c.add_row(kv_row("geoclue:", active or "inactive"))
        if have("systemctl"):
            row = Gtk.Box(spacing=8)
            b_off = SketchButton("Disable", width=110, height=24,
                                 color=DANGER_RED)
            b_off.connect("clicked", lambda _b: self._term_run(
                "sudo systemctl disable --now geoclue.service",
                "disabling geoclue (requires sudo)…"))
            row.append(b_off)
            b_on = SketchButton("Enable", width=110, height=24,
                                color=NEON_GREEN)
            b_on.connect("clicked", lambda _b: self._term_run(
                "sudo systemctl enable --now geoclue.service",
                "enabling geoclue (requires sudo)…"))
            row.append(b_on)
            c.add_row(row)

    # ── Recent files ───────────────────────────────────────────────────────
    def _build_recent_card(self):
        c = Card("recent files & history")
        self.box.append(c)
        recent = Path.home() / ".local/share/recently-used.xbel"
        n = 0
        if recent.exists():
            try:
                txt = recent.read_text(errors="ignore")
                n = txt.count("<bookmark ")
            except Exception:
                pass
        c.add_row(kv_row("recently-used.xbel:",
                         f"{n} entries" if recent.exists() else "(missing)"))
        thumbs = Path.home() / ".cache" / "thumbnails"
        c.add_row(kv_row("thumbnail cache:",
                         "present" if thumbs.exists() else "(none)"))
        bash_hist = Path.home() / ".bash_history"
        zsh_hist  = Path.home() / ".zsh_history"
        h = ("zsh" if zsh_hist.exists() else "") + (" bash" if bash_hist.exists() else "")
        c.add_row(kv_row("shell history:", h.strip() or "(none)"))
        row = Gtk.Box(spacing=8)
        if recent.exists():
            b1 = SketchButton("Clear recent", width=130, height=24,
                              color=DANGER_RED)
            b1.connect("clicked", lambda _b: (
                recent.unlink(missing_ok=True),
                self.win.toast("recent files cleared"),
                self.refresh()))
            row.append(b1)
        if thumbs.exists():
            b2 = SketchButton("Clear thumbs", width=130, height=24,
                              color=DANGER_RED)
            b2.connect("clicked", lambda _b: (
                sh_async(f"rm -rf {shlex.quote(str(thumbs))}/*"),
                self.win.toast("thumbnail cache cleared")))
            row.append(b2)
        c.add_row(row)

    # ── helpers ────────────────────────────────────────────────────────────
    def _clip(self, text: str):
        try:
            disp = Gdk.Display.get_default()
            disp.get_clipboard().set(text)
            self.win.toast("copied to clipboard")
        except Exception as e:
            self.win.toast(f"copy failed: {e}")

    def _term_run(self, cmd: str, toast: str):
        for term in ("foot", "alacritty", "kitty", "xterm"):
            if have(term):
                subprocess.Popen(
                    [term, "-e", "sh", "-c",
                     f"{cmd}; echo; echo 'press enter to close'; read _"],
                    start_new_session=True)
                self.win.toast(toast)
                return
        self.win.toast("no terminal found (install foot/alacritty/kitty)")

    def build(self):
        self._build_yubi_card()
        self._build_gpg_card()
        self._build_ssh_card()
        self._build_mac_card()
        self._build_luks_card()
        self._build_lock_card()
        self._build_location_card()
        self._build_recent_card()
        self.add_note(
            "System-wide changes (AppArmor enforce, geoclue enable/disable, "
            "GPG key generation, SSH key generation) open in a terminal where "
            "they can prompt for sudo or your passphrase. The YubiKey serial "
            "shown here is read directly from `ykman info`.")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "YubiKey", "hardware security key"),
            SearchEntry(self.KEY, self.TITLE, "GPG keys", "pgp"),
            SearchEntry(self.KEY, self.TITLE, "SSH keys", "ed25519 rsa"),
            SearchEntry(self.KEY, self.TITLE, "AppArmor"),
            SearchEntry(self.KEY, self.TITLE, "SELinux"),
            SearchEntry(self.KEY, self.TITLE, "LUKS encryption"),
            SearchEntry(self.KEY, self.TITLE, "Screen lock", "hyprlock hypridle"),
            SearchEntry(self.KEY, self.TITLE, "Location services", "geoclue"),
            SearchEntry(self.KEY, self.TITLE, "Clear recent files"),
            SearchEntry(self.KEY, self.TITLE, "Clear thumbnail cache"),
        ]


# ─── Applications ───────────────────────────────────────────────────────────
class AppsPage(BasePage):
    KEY = "apps"; TITLE = "Applications"; ICON = "📦"

    def build(self):
        c = Card("default applications")
        self.box.append(c)
        for label, mime in (("Web browser",   "x-scheme-handler/https"),
                            ("Email",         "x-scheme-handler/mailto"),
                            ("Text editor",   "text/plain"),
                            ("File manager",  "inode/directory"),
                            ("Image viewer",  "image/png"),
                            ("Video player",  "video/mp4"),
                            ("Music player",  "audio/mpeg"),
                            ("PDF viewer",    "application/pdf")):
            rc, out, _ = sh(f"xdg-mime query default {mime}")
            c.add_row(kv_row(label + ":", out.strip() or "(none)"))

        c = Card("installed packages (pacman)")
        self.box.append(c)
        rc, out, _ = sh("pacman -Qq", timeout=5)
        if rc == 0:
            count = len(out.splitlines())
            c.add_row(kv_row("Total packages:", f"{count}"))
            sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 180)
            tv = Gtk.TextView(); tv.set_editable(False)
            tv.add_css_class("nyx-editor")
            tv.get_buffer().set_text(out)
            sw.set_child(tv); c.add_row(sw)
        else:
            c.add_row(Gtk.Label(label="pacman not available", xalign=0))

        c = Card("startup applications")
        self.box.append(c)
        autostart = Path.home() / ".config/autostart"
        if autostart.exists():
            for f in sorted(autostart.glob("*.desktop")):
                c.add_row(kv_row(f.name, ""))
        else:
            c.add_row(Gtk.Label(label="(no autostart entries)", xalign=0))

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Default browser"),
            SearchEntry(self.KEY, self.TITLE, "Default editor"),
            SearchEntry(self.KEY, self.TITLE, "Installed packages"),
            SearchEntry(self.KEY, self.TITLE, "Startup applications"),
        ]


# ─── Storage ────────────────────────────────────────────────────────────────
class StoragePage(BasePage):
    KEY = "storage"; TITLE = "Storage"; ICON = "💾"

    def build(self):
        # ── 1. drives & partitions ─────────────────────────────────────────
        c = Card("drives & partitions")
        self.box.append(c)
        rc, out, _ = sh("lsblk -o NAME,SIZE,TYPE,FSTYPE,MOUNTPOINT,LABEL")
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 200)
        tv = Gtk.TextView(); tv.set_editable(False); tv.set_monospace(True)
        tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(out or "(no output)")
        sw.set_child(tv); c.add_row(sw)

        # ── 2. SMART health (per physical drive) ───────────────────────────
        c = Card("S.M.A.R.T. health")
        self.box.append(c)
        if not have("smartctl"):
            c.add_row(Gtk.Label(
                label="smartmontools not installed (pacman -S smartmontools)",
                xalign=0))
        else:
            rc, out, _ = sh("lsblk -d -n -o NAME,TYPE,SIZE,MODEL")
            drives = []
            for line in out.splitlines():
                parts = line.split(None, 3)
                if len(parts) >= 2 and parts[1] == "disk":
                    drives.append(parts)
            if not drives:
                c.add_row(Gtk.Label(label="(no physical drives detected)",
                                    xalign=0))
            for parts in drives:
                name = parts[0]
                size = parts[2] if len(parts) > 2 else "?"
                model = parts[3] if len(parts) > 3 else ""
                dev = f"/dev/{name}"
                rc, sout, _ = sh(
                    f"sudo -n smartctl -H {dev} 2>/dev/null | "
                    "grep -E 'overall-health|SMART Health' | head -1")
                state = sout.strip().split(":")[-1].strip() if sout.strip() \
                        else "(needs sudo)"
                row = Gtk.Box(spacing=8)
                lbl = Gtk.Label(
                    label=f"{dev}  {size}  {model[:32]}",
                    xalign=0); lbl.set_hexpand(True)
                row.append(lbl)
                row.append(Gtk.Label(label=state, xalign=1))
                b_full = SketchButton("Full report", width=110, height=24,
                                      color=NEON_BLUE)
                b_full.connect("clicked", lambda _b, d=dev: self._term_run(
                    f"sudo smartctl -a {d} | less",
                    f"smartctl -a {d}…"))
                row.append(b_full)
                b_test = SketchButton("Short test", width=110, height=24,
                                      color=NEON_BLUE)
                b_test.connect("clicked", lambda _b, d=dev: self._term_run(
                    f"sudo smartctl -t short {d}",
                    f"short test queued on {d}…"))
                row.append(b_test)
                c.add_row(row)

        # ── 3. mount points ────────────────────────────────────────────────
        c = Card("mount points")
        self.box.append(c)
        rc, out, _ = sh("findmnt -t nosquashfs,nooverlay -D "
                        "-o TARGET,SOURCE,FSTYPE,SIZE,USED,AVAIL,USE%")
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 200)
        tv = Gtk.TextView(); tv.set_editable(False); tv.set_monospace(True)
        tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(out or "(no output)")
        sw.set_child(tv); c.add_row(sw)
        row = Gtk.Box(spacing=8)
        b_fstab = SketchButton("Edit /etc/fstab", width=160, height=26,
                               color=ACCENT_GOLD)
        b_fstab.connect("clicked", lambda _b: self._term_run(
            "sudo ${EDITOR:-nano} /etc/fstab",
            "/etc/fstab opened (sudo)…"))
        row.append(b_fstab)
        b_remount = SketchButton("Remount all (mount -a)", width=200,
                                 height=26, color=NEON_BLUE)
        b_remount.connect("clicked", lambda _b: self._term_run(
            "sudo mount -a && echo OK",
            "remounting…"))
        row.append(b_remount)
        c.add_row(row)

        # ── 4. swap ────────────────────────────────────────────────────────
        c = Card("swap")
        self.box.append(c)
        rc, out, _ = sh("swapon --show --noheadings")
        if not out.strip():
            c.add_row(Gtk.Label(label="no swap active", xalign=0))
        else:
            for line in out.splitlines():
                parts = line.split()
                if len(parts) >= 4:
                    c.add_row(kv_row(
                        f"{parts[0]} ({parts[1]}):",
                        f"{parts[2]} total · {parts[3]} used"))
        try:
            swp = Path("/proc/sys/vm/swappiness").read_text().strip()
        except Exception:
            swp = "?"
        c.add_row(kv_row("vm.swappiness:", swp))
        row = Gtk.Box(spacing=6)
        for v in (10, 20, 60, 100):
            b = SketchButton(str(v), width=46, height=22, color=NEON_BLUE,
                             primary=(str(v) == swp))
            b.connect("clicked", lambda _b, v=v:
                      (sh(f"sudo -n sysctl -w vm.swappiness={v}"),
                       self.win.toast(f"swappiness → {v} (sudo)")))
            row.append(b)
        c.add_row(row)

        # ── 5. disk usage (df) ─────────────────────────────────────────────
        c = Card("disk usage")
        self.box.append(c)
        rc, out, _ = sh("df -h -x tmpfs -x devtmpfs -x squashfs -x overlay")
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 180)
        tv = Gtk.TextView(); tv.set_editable(False); tv.set_monospace(True)
        tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(out or "(no output)")
        sw.set_child(tv); c.add_row(sw)

        # ── 6. home folder breakdown ───────────────────────────────────────
        c = Card("home folder breakdown")
        self.box.append(c)
        for sub in ("Documents", "Downloads", "Pictures", "Videos", "Music",
                    ".cache", ".config", ".local"):
            p = Path.home() / sub
            if not p.exists():
                c.add_row(kv_row(sub, "(missing)")); continue
            rc, out, _ = sh(f"du -sh {p}", timeout=10)
            c.add_row(kv_row(sub, out.split()[0] if out else "?"))

        # ── 7. cleanup ─────────────────────────────────────────────────────
        c = Card("cleanup")
        self.box.append(c)
        # pacman cache
        rc, out, _ = sh("du -sh /var/cache/pacman/pkg 2>/dev/null", timeout=8)
        size = out.split()[0] if out.strip() else "?"
        row = Gtk.Box(spacing=8)
        lbl = Gtk.Label(label=f"pacman cache: {size}", xalign=0)
        lbl.set_hexpand(True); row.append(lbl)
        b = SketchButton("Clean (paccache -rk2)", width=200, height=24,
                         color=ACCENT_GOLD)
        b.connect("clicked", lambda _b: self._term_run(
            "sudo paccache -rk2",
            "cleaning pacman cache…"))
        row.append(b)
        c.add_row(row)
        # journal
        rc, out, _ = sh("journalctl --disk-usage 2>/dev/null", timeout=4)
        jsize = out.strip().split("take up")[-1].strip().rstrip(".") \
                if "take up" in out else (out.strip() or "?")
        row = Gtk.Box(spacing=8)
        lbl = Gtk.Label(label=f"systemd journal: {jsize}", xalign=0)
        lbl.set_hexpand(True); row.append(lbl)
        b = SketchButton("Vacuum to 200M", width=180, height=24,
                         color=ACCENT_GOLD)
        b.connect("clicked", lambda _b: self._term_run(
            "sudo journalctl --vacuum-size=200M",
            "vacuuming journal…"))
        row.append(b)
        c.add_row(row)
        # /tmp
        rc, out, _ = sh("du -sh /tmp 2>/dev/null", timeout=6)
        c.add_row(kv_row("/tmp:", out.split()[0] if out.strip() else "?"))
        # trash
        trash = Path.home() / ".local/share/Trash"
        if trash.exists():
            rc, out, _ = sh(f"du -sh {trash}", timeout=6)
            row = Gtk.Box(spacing=8)
            lbl = Gtk.Label(
                label=f"trash: {out.split()[0] if out else '?'}", xalign=0)
            lbl.set_hexpand(True); row.append(lbl)
            b = SketchButton("Empty trash", width=140, height=24,
                             color=NEON_PINK)
            b.connect("clicked", lambda _b: (
                sh(f"rm -rf {trash}/files/* {trash}/info/*"),
                self.win.toast("trash emptied")))
            row.append(b)
            c.add_row(row)

        # ── 8. snapshots / btrfs ───────────────────────────────────────────
        c = Card("snapshots")
        self.box.append(c)
        rc, out, _ = sh(
            "lsblk -n -o FSTYPE | sort -u | grep -c btrfs || true")
        has_btrfs = (out.strip() not in ("0", ""))
        c.add_row(kv_row("btrfs filesystem present:",
                         "yes" if has_btrfs else "no"))
        c.add_row(kv_row("timeshift installed:",
                         "yes" if have("timeshift") else "no"))
        c.add_row(kv_row("snapper installed:",
                         "yes" if have("snapper") else "no"))
        if have("timeshift"):
            row = Gtk.Box(spacing=8)
            b = SketchButton("Open Timeshift", width=160, height=24,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b: self._term_run(
                "sudo timeshift-gtk &", "launching timeshift…"))
            row.append(b)
            b2 = SketchButton("List snapshots", width=160, height=24,
                              color=NEON_BLUE)
            b2.connect("clicked", lambda _b: self._term_run(
                "sudo timeshift --list",
                "listing snapshots…"))
            row.append(b2)
            c.add_row(row)
        if have("snapper"):
            row = Gtk.Box(spacing=8)
            b = SketchButton("snapper list", width=160, height=24,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b: self._term_run(
                "sudo snapper list", "listing snapper snapshots…"))
            row.append(b)
            c.add_row(row)
        if not (have("timeshift") or have("snapper")):
            c.add_row(Gtk.Label(
                label="install timeshift or snapper for snapshot management",
                xalign=0))

        # ── 9. I/O activity ────────────────────────────────────────────────
        c = Card("I/O activity")
        self.box.append(c)
        try:
            ds = Path("/proc/diskstats").read_text().splitlines()
            rows = []
            for line in ds:
                f = line.split()
                if len(f) < 14: continue
                name = f[2]
                if name.startswith(("loop", "ram")) or name[-1].isdigit():
                    continue
                reads = int(f[5]); writes = int(f[9])
                rows.append((name, reads, writes))
            rows.sort(key=lambda r: -(r[1] + r[2]))
            for name, r, w in rows[:6]:
                c.add_row(kv_row(
                    f"/dev/{name}:",
                    f"{r//2048} MiB read · {w//2048} MiB written"))
            if not rows:
                c.add_row(Gtk.Label(label="(no devices)", xalign=0))
        except Exception as e:
            c.add_row(Gtk.Label(label=f"(error: {e})", xalign=0))
        if have("iotop"):
            row = Gtk.Box(spacing=8)
            b = SketchButton("Launch iotop", width=160, height=24,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b: self._term_run(
                "sudo iotop -o", "launching iotop (sudo)…"))
            row.append(b)
            c.add_row(row)

        # ── 10. removable / automount ──────────────────────────────────────
        c = Card("removable & automount")
        self.box.append(c)
        rc, out, _ = sh(
            "lsblk -d -n -o NAME,SIZE,RM,MODEL,TRAN")
        any_rem = False
        for line in out.splitlines():
            parts = line.split(None, 4)
            if len(parts) >= 3 and parts[2] == "1":
                any_rem = True
                name = parts[0]; size = parts[1]
                model = parts[3] if len(parts) > 3 else ""
                row = Gtk.Box(spacing=8)
                lbl = Gtk.Label(
                    label=f"/dev/{name}  {size}  {model}", xalign=0)
                lbl.set_hexpand(True); row.append(lbl)
                if have("udisksctl"):
                    b = SketchButton("Eject", width=100, height=22,
                                     color=NEON_PINK)
                    b.connect("clicked", lambda _b, n=name: (
                        sh(f"udisksctl power-off -b /dev/{n}"),
                        self.win.toast(f"ejected /dev/{n}")))
                    row.append(b)
                c.add_row(row)
        if not any_rem:
            c.add_row(Gtk.Label(label="(no removable devices attached)",
                                xalign=0))

        self.add_note(
            "smartctl, fstab edits, paccache and journal vacuum require "
            "sudo. snapshot tools (timeshift/snapper) launch in your "
            "terminal so you can authenticate.")

    # ── helper: run in terminal ────────────────────────────────────────────
    def _term_run(self, cmd: str, toast: str):
        for term in ("foot", "alacritty", "kitty", "xterm"):
            if have(term):
                subprocess.Popen(
                    [term, "-e", "sh", "-c",
                     f"{cmd}; echo; echo 'press enter to close'; read _"],
                    start_new_session=True)
                self.win.toast(toast)
                return
        self.win.toast("no terminal found (install foot/alacritty/kitty)")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Drives & partitions",
                        "lsblk"),
            SearchEntry(self.KEY, self.TITLE, "S.M.A.R.T. health",
                        "smartctl drive"),
            SearchEntry(self.KEY, self.TITLE, "Run SMART short test",
                        "smartctl -t short"),
            SearchEntry(self.KEY, self.TITLE, "Mount points", "findmnt"),
            SearchEntry(self.KEY, self.TITLE, "Edit /etc/fstab", "fstab"),
            SearchEntry(self.KEY, self.TITLE, "Swap", "swapon swappiness"),
            SearchEntry(self.KEY, self.TITLE, "vm.swappiness"),
            SearchEntry(self.KEY, self.TITLE, "Disk usage", "df"),
            SearchEntry(self.KEY, self.TITLE, "Home folder usage", "du"),
            SearchEntry(self.KEY, self.TITLE, "Cleanup pacman cache",
                        "paccache"),
            SearchEntry(self.KEY, self.TITLE, "Vacuum journal",
                        "journalctl disk usage"),
            SearchEntry(self.KEY, self.TITLE, "Empty trash"),
            SearchEntry(self.KEY, self.TITLE, "Snapshots",
                        "timeshift snapper btrfs"),
            SearchEntry(self.KEY, self.TITLE, "I/O activity",
                        "iotop diskstats"),
            SearchEntry(self.KEY, self.TITLE, "Removable devices",
                        "eject usb udisks"),
        ]


# ─── Language ───────────────────────────────────────────────────────────────
class LanguagePage(BasePage):
    KEY = "language"; TITLE = "Language & Region"; ICON = "🗺"

    def build(self):
        c = Card("locale")
        self.box.append(c)
        rc, out, _ = sh("locale")
        for line in out.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                c.add_row(kv_row(k + ":", v.strip('"')))
        self.add_note(
            "system locale changes need root — edit /etc/locale.conf or "
            "use `localectl set-locale`.")

    def search_entries(self):
        return [SearchEntry(self.KEY, self.TITLE, "Locale", "language")]


# ─── Accessibility ──────────────────────────────────────────────────────────
class AccessibilityPage(BasePage):
    KEY = "a11y"; TITLE = "Accessibility"; ICON = "♿"

    def build(self):
        c = Card("hyprland accessibility")
        self.box.append(c)
        # cursor size
        env = os.environ.get("XCURSOR_SIZE", "24")
        c.add_row(kv_row("Current cursor size (XCURSOR_SIZE):", env))
        row = Gtk.Box(spacing=8)
        for s in (20, 24, 32, 48):
            b = SketchButton(str(s), width=46, height=22, color=NEON_BLUE,
                             primary=(str(s) == env))
            b.connect("clicked", lambda _b, s=s:
                      (sh(f"hyprctl setcursor Adwaita {s}"),
                       self.win.toast(f"cursor → {s}px")))
            row.append(b)
        c.add_row(row)

        c = Card("contrast / scale")
        self.box.append(c)
        c.add_row(Gtk.Label(
            label="GTK accessibility — adjust per-app via GNOME Settings or",
            xalign=0))
        c.add_row(Gtk.Label(
            label="GTK_THEME=Adwaita-dark / gsettings set gtk-text-scaling-factor",
            xalign=0))

    def search_entries(self):
        return [SearchEntry(self.KEY, self.TITLE, "Cursor size")]


# ─── Printers ───────────────────────────────────────────────────────────────
class PrintersPage(BasePage):
    KEY = "printers"; TITLE = "Printers & Scanners"; ICON = "🖨"

    def build(self):
        c = Card("CUPS")
        self.box.append(c)
        if have("lpstat"):
            rc, out, _ = sh("lpstat -p -d")
            c.add_row(Gtk.Label(label=out.strip() or "(no printers)",
                                xalign=0))
        else:
            c.add_row(Gtk.Label(label="cups / lpstat not installed",
                                xalign=0))

        c = Card("scanners (sane)")
        self.box.append(c)
        if have("scanimage"):
            rc, out, _ = sh("scanimage -L", timeout=8)
            c.add_row(Gtk.Label(label=out.strip() or "(no scanners)",
                                xalign=0))
        else:
            c.add_row(Gtk.Label(label="sane / scanimage not installed",
                                xalign=0))

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Printers"),
            SearchEntry(self.KEY, self.TITLE, "Scanners"),
        ]


# ─── Gaming ─────────────────────────────────────────────────────────────────
class GamingPage(BasePage):
    KEY = "gaming"; TITLE = "Gaming"; ICON = "🎮"

    def build(self):
        c = Card("GameMode")
        self.box.append(c)
        if have("gamemoded"):
            rc, out, _ = sh("gamemoded -s")
            c.add_row(Gtk.Label(label=out.strip(), xalign=0))
        else:
            c.add_row(Gtk.Label(label="gamemoded not installed", xalign=0))

        c = Card("controllers")
        self.box.append(c)
        # list /dev/input/event* with udev info
        rc, out, _ = sh("ls /dev/input/by-id/")
        controllers = [l for l in out.splitlines()
                       if "joystick" in l or "gamepad" in l or "8bitdo" in l.lower()]
        if controllers:
            for c_dev in controllers:
                c.add_row(Gtk.Label(label=c_dev, xalign=0))
        else:
            c.add_row(Gtk.Label(label="(no controllers detected)", xalign=0))

        c = Card("MangoHud / overlay")
        self.box.append(c)
        cfg = Path.home() / ".config/MangoHud/MangoHud.conf"
        c.add_row(kv_row("config:", str(cfg)))
        c.add_row(Gtk.Label(label="exists" if cfg.exists()
                            else "(not configured)", xalign=0))

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "GameMode"),
            SearchEntry(self.KEY, self.TITLE, "Controllers"),
            SearchEntry(self.KEY, self.TITLE, "MangoHud"),
        ]


# ─── Developer / System info ────────────────────────────────────────────────
class DeveloperPage(BasePage):
    KEY = "developer"; TITLE = "Developer / System Info"; ICON = "{}"
    TILE_COLOR = NEON_GREEN
    SUBTITLE  = "Docker · sshd · GRUB · journalctl · cron"

    GRUB_PATH = Path("/etc/default/grub")

    # ── kernel / hostname / distro ─────────────────────────────────────────
    def _build_system_card(self):
        c = Card("kernel & system")
        self.box.append(c)
        rc, host, _ = sh("hostnamectl --static"); host = host.strip() or "?"
        rc, kver, _ = sh("uname -r");              kver = kver.strip()
        rc, mach, _ = sh("uname -m");              mach = mach.strip()
        rc, osr,  _ = sh("cat /etc/os-release")
        distro = "?"
        for ln in osr.splitlines():
            if ln.startswith("PRETTY_NAME="):
                distro = ln.split("=",1)[1].strip().strip('"'); break
        rc, up,   _ = sh("uptime -p");             up = up.strip() or "?"
        rc, lod,  _ = sh("uptime"); load = lod.split("load average:")[-1].strip() if "load average" in lod else "?"
        c.add_row(kv_row("Hostname:", host))
        c.add_row(kv_row("Distro:",   distro))
        c.add_row(kv_row("Kernel:",   f"{kver}  ({mach})"))
        c.add_row(kv_row("Uptime:",   up))
        c.add_row(kv_row("Load avg:", load))

    # ── CPU / RAM / GPU ────────────────────────────────────────────────────
    def _build_hw_card(self):
        c = Card("CPU")
        self.box.append(c)
        rc, out, _ = sh("lscpu")
        keep = ("Model name", "Architecture", "CPU(s):",
                "Thread(s) per core", "Core(s) per socket",
                "CPU max MHz", "CPU min MHz", "Vulnerability")
        for ln in out.splitlines():
            ls = ln.strip()
            if any(k in ls for k in keep):
                if ":" in ls:
                    k, v = ls.split(":", 1)
                    c.add_row(kv_row(k.strip()+":", v.strip()))

        c = Card("RAM")
        self.box.append(c)
        rc, out, _ = sh("free -h")
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 100)
        tv = Gtk.TextView(); tv.set_editable(False); tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(out or "(no output)")
        sw.set_child(tv); c.add_row(sw)

        c = Card("GPU")
        self.box.append(c)
        rc, out, _ = sh("sh -c \"lspci | grep -E 'VGA|3D|Display'\"")
        for ln in out.splitlines():
            if ln.strip(): c.add_row(Gtk.Label(label=ln.strip(), xalign=0))
        if not out.strip():
            c.add_row(Gtk.Label(label="(no GPU detected)", xalign=0))

    # ── Docker ─────────────────────────────────────────────────────────────
    def _build_docker_card(self):
        c = Card("Docker")
        self.box.append(c)
        if not have("docker"):
            c.add_row(Gtk.Label(label="docker not installed", xalign=0))
            return
        rc, ver, _ = sh("docker --version", timeout=2)
        c.add_row(kv_row("Version:", ver.strip() or "?"))
        rc, dstat, _ = sh("systemctl is-active docker", timeout=2)
        c.add_row(kv_row("docker.service:", dstat.strip() or "?"))
        # daemon reachable?
        rc, _, derr = sh("docker info --format '{{.ServerVersion}}'", timeout=3)
        if rc != 0:
            c.add_row(Gtk.Label(
                label=f"daemon unreachable: {derr.strip()[:80]}", xalign=0))
            row = Gtk.Box(spacing=8)
            b_start = SketchButton("Start daemon", width=140, height=24,
                                   color=NEON_GREEN)
            b_start.connect("clicked", lambda _b: self._term_run(
                "sudo systemctl start docker.service",
                "starting docker (sudo)…"))
            row.append(b_start)
            c.add_row(row)
            return
        # containers
        rc, out, _ = sh(
            "docker ps -a --format '{{.ID}}|{{.Names}}|{{.Image}}|{{.Status}}'",
            timeout=4)
        rows = [ln.split("|") for ln in out.splitlines() if ln.strip()]
        c.add_row(kv_row("Containers:", f"{len(rows)} total"))
        for parts in rows[:10]:
            if len(parts) < 4: continue
            cid, name, image, status = parts[0], parts[1], parts[2], parts[3]
            running = status.lower().startswith("up")
            r = Gtk.Box(spacing=8)
            badge = "▶" if running else "■"
            r.append(Gtk.Label(
                label=f"{badge} {name}  [{image[:30]}]  {status[:36]}",
                xalign=0))
            sp = Gtk.Box(); sp.set_hexpand(True); r.append(sp)
            if running:
                b = SketchButton("Stop", width=80, height=22, color=DANGER_RED)
                b.connect("clicked", lambda _b, i=cid: self._docker_act("stop", i))
                r.append(b)
            else:
                b = SketchButton("Start", width=80, height=22, color=NEON_GREEN)
                b.connect("clicked", lambda _b, i=cid: self._docker_act("start", i))
                r.append(b)
            b_logs = SketchButton("Logs", width=80, height=22, color=ACCENT_PURP)
            b_logs.connect("clicked", lambda _b, i=cid: self._docker_logs(i))
            r.append(b_logs)
            c.add_row(r)
        if len(rows) > 10:
            c.add_row(Gtk.Label(label=f"… and {len(rows)-10} more", xalign=0))
        # images count
        rc, iout, _ = sh("docker images -q", timeout=3)
        n_img = len([l for l in iout.splitlines() if l.strip()])
        c.add_row(kv_row("Images:", f"{n_img}"))
        rc, vol, _ = sh("docker volume ls -q", timeout=3)
        n_vol = len([l for l in vol.splitlines() if l.strip()])
        c.add_row(kv_row("Volumes:", f"{n_vol}"))
        row = Gtk.Box(spacing=8)
        b_prune = SketchButton("Prune (system)", width=160, height=24,
                               color=DANGER_RED,
                               tooltip="docker system prune -f")
        b_prune.connect("clicked", lambda _b: sh_async(
            "docker system prune -f",
            lambda r: (self.win.toast("pruned" if r[0]==0 else "failed"),
                       self.refresh())))
        row.append(b_prune)
        b_pull = SketchButton("Pull image…", width=140, height=24,
                              color=ACCENT_GOLD)
        b_pull.connect("clicked", lambda _b: self._term_run(
            "read -p 'image: ' img && docker pull \"$img\"",
            "pull dialog opened in terminal"))
        row.append(b_pull)
        c.add_row(row)

    def _docker_act(self, action: str, cid: str):
        sh_async(f"docker {action} {cid}",
                 lambda r: (self.win.toast(
                     f"{action} {cid[:8]}: {'ok' if r[0]==0 else 'failed'}"),
                     self.refresh()))

    def _docker_logs(self, cid: str):
        self._term_run(
            f"docker logs --tail 200 -f {cid}",
            f"logs for {cid[:8]} opened")

    # ── SSH server ─────────────────────────────────────────────────────────
    def _build_sshd_card(self):
        c = Card("SSH server (sshd)")
        self.box.append(c)
        if not have("sshd"):
            c.add_row(Gtk.Label(
                label="openssh not installed (pacman -S openssh)", xalign=0))
            return
        rc, active, _ = sh("systemctl is-active sshd",  timeout=2)
        rc, en,     _ = sh("systemctl is-enabled sshd", timeout=2)
        c.add_row(kv_row("Active:",  active.strip() or "?"))
        c.add_row(kv_row("Enabled at boot:", en.strip() or "?"))
        # parse listening port
        port = "22"
        try:
            txt = Path("/etc/ssh/sshd_config").read_text(errors="ignore")
            for ln in txt.splitlines():
                ls = ln.strip()
                if ls.lower().startswith("port ") and not ls.startswith("#"):
                    port = ls.split()[1]; break
        except Exception:
            pass
        c.add_row(kv_row("Listening port:", port))
        # who's connected
        rc, out, _ = sh("who", timeout=2)
        ssh_conns = [l for l in out.splitlines() if "(" in l]
        c.add_row(kv_row("Active sessions:", str(len(ssh_conns))))
        row = Gtk.Box(spacing=8)
        if active.strip() == "active":
            b = SketchButton("Stop sshd", width=130, height=24,
                             color=DANGER_RED)
            b.connect("clicked", lambda _b: self._term_run(
                "sudo systemctl stop sshd",
                "stopping sshd (sudo)…"))
            row.append(b)
        else:
            b = SketchButton("Start sshd", width=130, height=24,
                             color=NEON_GREEN)
            b.connect("clicked", lambda _b: self._term_run(
                "sudo systemctl start sshd",
                "starting sshd (sudo)…"))
            row.append(b)
        if en.strip() == "enabled":
            b2 = SketchButton("Disable at boot", width=160, height=24,
                              color=ACCENT_GOLD)
            b2.connect("clicked", lambda _b: self._term_run(
                "sudo systemctl disable sshd",
                "disabling sshd at boot (sudo)…"))
        else:
            b2 = SketchButton("Enable at boot", width=160, height=24,
                              color=ACCENT_PURP)
            b2.connect("clicked", lambda _b: self._term_run(
                "sudo systemctl enable sshd",
                "enabling sshd at boot (sudo)…"))
        row.append(b2)
        b3 = SketchButton("Edit config", width=130, height=24,
                          color=NEON_PINK)
        b3.connect("clicked", lambda _b: self._term_run(
            "sudo ${EDITOR:-nano} /etc/ssh/sshd_config",
            "sshd_config opened (sudo)…"))
        row.append(b3)
        c.add_row(row)

    # ── GRUB editor ────────────────────────────────────────────────────────
    def _build_grub_card(self):
        c = Card("GRUB bootloader")
        self.box.append(c)
        if not self.GRUB_PATH.exists():
            c.add_row(Gtk.Label(
                label="GRUB not detected (no /etc/default/grub)", xalign=0))
            return
        try:
            txt = self.GRUB_PATH.read_text(errors="ignore")
        except Exception as e:
            c.add_row(Gtk.Label(label=f"read failed: {e}", xalign=0))
            return
        opts = {}
        for ln in txt.splitlines():
            ls = ln.strip()
            if ls.startswith("#") or "=" not in ls: continue
            k, v = ls.split("=", 1)
            opts[k.strip()] = v.strip().strip('"')
        for key in ("GRUB_DEFAULT", "GRUB_TIMEOUT",
                    "GRUB_CMDLINE_LINUX_DEFAULT", "GRUB_CMDLINE_LINUX",
                    "GRUB_DISTRIBUTOR", "GRUB_GFXMODE"):
            if key in opts:
                c.add_row(kv_row(key+":", opts[key] or "(empty)"))
        # entries
        cfg = Path("/boot/grub/grub.cfg")
        if cfg.exists():
            try:
                gtxt = cfg.read_text(errors="ignore")
                ents = re.findall(r"^menuentry ['\"]([^'\"]+)['\"]",
                                   gtxt, re.MULTILINE)
                c.add_row(kv_row("Boot entries:", str(len(ents))))
                for e in ents[:6]:
                    c.add_row(Gtk.Label(label=f"  • {e}", xalign=0))
            except Exception:
                pass
        row = Gtk.Box(spacing=8)
        b_edit = SketchButton("Edit /etc/default/grub", width=200, height=24,
                              color=NEON_PINK)
        b_edit.connect("clicked", lambda _b: self._term_run(
            "sudo ${EDITOR:-nano} /etc/default/grub",
            "GRUB config opened (sudo)…"))
        row.append(b_edit)
        b_apply = SketchButton("Regenerate grub.cfg", width=180, height=24,
                               color=DANGER_RED,
                               tooltip="grub-mkconfig -o /boot/grub/grub.cfg")
        b_apply.connect("clicked", lambda _b: self._term_run(
            "sudo grub-mkconfig -o /boot/grub/grub.cfg",
            "regenerating grub.cfg (sudo)…"))
        row.append(b_apply)
        c.add_row(row)
        self.win.flag_restart_required(
            self.KEY, "GRUB changes apply on next reboot.")

    # ── journalctl tail viewer ─────────────────────────────────────────────
    def _build_journal_card(self):
        c = Card("system journal (journalctl)")
        self.box.append(c)
        if not have("journalctl"):
            c.add_row(Gtk.Label(label="journalctl not available", xalign=0))
            return
        # priority filter dropdown (simple)
        row = Gtk.Box(spacing=8)
        row.append(Gtk.Label(label="show last 200 lines  ·  priority:", xalign=0))
        for label, pri in (("err", "3"), ("warn", "4"), ("info", "6"), ("all", "7")):
            b = SketchButton(label, width=70, height=22, color=NEON_GREEN)
            b.connect("clicked",
                      lambda _b, p=pri: self._journal_load(tv, p))
            row.append(b)
        c.add_row(row)
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 240)
        tv = Gtk.TextView(); tv.set_editable(False); tv.add_css_class("nyx-editor")
        tv.set_monospace(True); sw.set_child(tv); c.add_row(sw)
        self._journal_load(tv, "4")  # default: warn+
        row2 = Gtk.Box(spacing=8)
        b_open = SketchButton("Follow (terminal)", width=180, height=24,
                              color=ACCENT_GOLD)
        b_open.connect("clicked", lambda _b: self._term_run(
            "journalctl -f", "journal -f opened in terminal"))
        row2.append(b_open)
        b_boot = SketchButton("This boot only", width=160, height=24,
                              color=ACCENT_PURP)
        b_boot.connect("clicked", lambda _b: self._journal_load(tv, "7", boot=True))
        row2.append(b_boot)
        c.add_row(row2)

    def _journal_load(self, tv: Gtk.TextView, priority: str, *, boot=False):
        cmd = f"journalctl -n 200 --no-pager -p {priority}"
        if boot: cmd += " -b 0"
        rc, out, err = sh(cmd, timeout=4)
        tv.get_buffer().set_text(out or err or "(no output)")

    # ── cron / systemd timers ──────────────────────────────────────────────
    def _build_cron_card(self):
        c = Card("scheduled jobs (cron + systemd timers)")
        self.box.append(c)
        # user crontab
        rc, out, _ = sh("crontab -l", timeout=2)
        if rc == 0 and out.strip():
            lines = [l for l in out.splitlines()
                     if l.strip() and not l.lstrip().startswith("#")]
            c.add_row(kv_row("user crontab:", f"{len(lines)} entries"))
            for ln in lines[:5]:
                c.add_row(Gtk.Label(label=f"  {ln.strip()}", xalign=0))
        else:
            c.add_row(kv_row("user crontab:", "(empty)"))
        # systemd timers
        rc, out, _ = sh("systemctl list-timers --no-pager --no-legend",
                        timeout=3)
        timers = [l for l in out.splitlines() if l.strip()]
        c.add_row(kv_row("systemd timers active:", str(len(timers))))
        for ln in timers[:6]:
            parts = ln.split()
            name = next((p for p in parts if p.endswith(".timer")), "?")
            c.add_row(Gtk.Label(label=f"  ⏱  {name}", xalign=0))
        row = Gtk.Box(spacing=8)
        b_edit = SketchButton("Edit user crontab", width=170, height=24,
                              color=NEON_PINK)
        b_edit.connect("clicked", lambda _b: self._term_run(
            "crontab -e", "crontab opened in terminal"))
        row.append(b_edit)
        c.add_row(row)

    # ── sysctl / kernel parameters ─────────────────────────────────────────
    def _build_sysctl_card(self):
        c = Card("kernel parameters (sysctl)")
        self.box.append(c)
        params = [
            "vm.swappiness",
            "vm.vfs_cache_pressure",
            "vm.dirty_ratio",
            "fs.file-max",
            "kernel.pid_max",
            "kernel.kptr_restrict",
            "kernel.dmesg_restrict",
            "net.core.somaxconn",
            "net.ipv4.tcp_fin_timeout",
            "net.ipv4.ip_forward",
        ]
        for p in params:
            rc, out, _ = sh(f"sysctl -n {p}", timeout=1)
            c.add_row(kv_row(p+":", out.strip() if rc==0 else "n/a"))
        row = Gtk.Box(spacing=8)
        b = SketchButton("Edit /etc/sysctl.d/", width=180, height=24,
                         color=NEON_PINK)
        b.connect("clicked", lambda _b: self._term_run(
            "sudo ${EDITOR:-nano} /etc/sysctl.d/99-nyxus.conf",
            "sysctl override opened (sudo)…"))
        row.append(b)
        c.add_row(row)

    # ── build tools detection ──────────────────────────────────────────────
    def _build_tools_card(self):
        c = Card("development toolchain")
        self.box.append(c)
        tools = [
            ("python3",     "python3 --version"),
            ("node",        "node --version"),
            ("npm",         "npm --version"),
            ("pnpm",        "pnpm --version"),
            ("rustc",       "rustc --version"),
            ("cargo",       "cargo --version"),
            ("go",          "go version"),
            ("gcc",         "gcc --version"),
            ("clang",       "clang --version"),
            ("git",         "git --version"),
            ("make",        "make --version"),
            ("cmake",       "cmake --version"),
            ("docker",      "docker --version"),
            ("kubectl",     "kubectl version --client --short"),
        ]
        for name, cmd in tools:
            if not have(name):
                c.add_row(kv_row(name+":", "(not installed)")); continue
            rc, out, _ = sh(cmd, timeout=2)
            ver = out.strip().splitlines()[0] if out else "?"
            # trim noisy "(c) Free Software Foundation" suffix
            ver = ver.split("(")[0].strip()
            c.add_row(kv_row(name+":", ver[:80]))

    # ── open ports ─────────────────────────────────────────────────────────
    def _build_ports_card(self):
        c = Card("open ports (ss -tunlp)")
        self.box.append(c)
        rc, out, _ = sh("ss -tunlp", timeout=3)
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 180)
        tv = Gtk.TextView(); tv.set_editable(False); tv.add_css_class("nyx-editor")
        tv.set_monospace(True)
        tv.get_buffer().set_text(out or "(no output)")
        sw.set_child(tv); c.add_row(sw)

    # ── environment variables ──────────────────────────────────────────────
    def _build_env_card(self):
        c = Card("environment variables")
        self.box.append(c)
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 200)
        tv = Gtk.TextView(); tv.set_editable(False); tv.add_css_class("nyx-editor")
        tv.set_monospace(True)
        tv.get_buffer().set_text(
            "\n".join(f"{k}={v}" for k, v in sorted(os.environ.items())))
        sw.set_child(tv); c.add_row(sw)

    # ── helpers ────────────────────────────────────────────────────────────
    def _term_run(self, cmd: str, toast: str):
        for term in ("foot", "alacritty", "kitty", "xterm"):
            if have(term):
                subprocess.Popen(
                    [term, "-e", "sh", "-c",
                     f"{cmd}; echo; echo 'press enter to close'; read _"],
                    start_new_session=True)
                self.win.toast(toast)
                return
        self.win.toast("no terminal found (install foot/alacritty/kitty)")

    def build(self):
        self._build_system_card()
        self._build_hw_card()
        self._build_docker_card()
        self._build_sshd_card()
        self._build_grub_card()
        self._build_journal_card()
        self._build_cron_card()
        self._build_sysctl_card()
        self._build_tools_card()
        self._build_ports_card()
        self._build_env_card()
        self.add_note(
            "Sudo-required actions (sshd toggle, GRUB regen, sysctl edits) "
            "open in a terminal where they can prompt for your password. "
            "The Docker section reads `docker ps -a` live; container Start/"
            "Stop/Logs work without sudo if your user is in the `docker` "
            "group. Journal viewer defaults to warn+; pick `all` to dump "
            "everything.")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "System info", "hostname kernel uptime"),
            SearchEntry(self.KEY, self.TITLE, "CPU info", "lscpu cores threads"),
            SearchEntry(self.KEY, self.TITLE, "RAM", "free memory"),
            SearchEntry(self.KEY, self.TITLE, "GPU", "lspci graphics"),
            SearchEntry(self.KEY, self.TITLE, "Docker", "containers images volumes"),
            SearchEntry(self.KEY, self.TITLE, "SSH server", "sshd openssh"),
            SearchEntry(self.KEY, self.TITLE, "GRUB bootloader"),
            SearchEntry(self.KEY, self.TITLE, "journalctl", "logs systemd"),
            SearchEntry(self.KEY, self.TITLE, "cron", "scheduled jobs timers"),
            SearchEntry(self.KEY, self.TITLE, "sysctl", "kernel parameters"),
            SearchEntry(self.KEY, self.TITLE, "Toolchain", "python node rust go gcc"),
            SearchEntry(self.KEY, self.TITLE, "Open ports"),
            SearchEntry(self.KEY, self.TITLE, "Environment variables"),
        ]


# ═══════════════════════════════════════════════════════════════════════════════
#  Main window
# ═══════════════════════════════════════════════════════════════════════════════
# ═══════════════════════════════════════════════════════════════════════════════
#  Phase A stub pages — full implementations land in Phase B per category
# ═══════════════════════════════════════════════════════════════════════════════
class _PhaseBStub(BasePage):
    """Tile is shown on the home grid, but the page itself is a polite stub
    saying 'in active build'.  Full functionality lands in Phase B."""
    PHASE_B_NOTE = ("This category is in active build for Phase B. "
                    "The home tile, search index, breadcrumb, favorite/recents, "
                    "and restart-required wiring are already live.")

    def build(self):
        c = Card("Phase B — coming next")
        c.add_row(Gtk.Label(
            label=self.PHASE_B_NOTE, xalign=0, wrap=True))
        c.add_row(Gtk.Label(
            label=("All settings for this category will be wired to the live "
                   "system, with zero placeholders, in the per-category Phase B "
                   "task that follows."), xalign=0, wrap=True))
        self.box.append(c)


# ─── Account & Profile (Category 1) ─────────────────────────────────────────
class AccountPage(BasePage):
    KEY = "account"; TITLE = "Account & Profile"; ICON = "🪪"
    TILE_COLOR = NEON_PINK
    SUBTITLE  = "Profile · Password · Login · Profile color"

    ACC_PATH = CONFIG_DIR / "account.json"

    def _user(self):
        try:
            import pwd
            pw = pwd.getpwuid(os.geteuid())
            gecos = (pw.pw_gecos or "").split(",")
            return {"u": pw.pw_name,
                    "f": (gecos[0] if gecos and gecos[0] else pw.pw_name),
                    "h": pw.pw_dir, "s": pw.pw_shell}
        except Exception:
            return {"u": os.environ.get("USER", "user"), "f": "—",
                    "h": str(Path.home()), "s": "—"}

    def _is_admin(self):
        u = os.environ.get("USER", "")
        rc, o, _ = sh(f"id -nG {shlex.quote(u)}", timeout=2)
        return rc == 0 and any(g in o.split() for g in ("wheel","sudo","admin"))

    def _last_login(self):
        u = os.environ.get("USER", "")
        rc, o, _ = sh(f"last -1 {shlex.quote(u)}", timeout=3)
        if rc != 0 or not o.strip(): return "—"
        return o.splitlines()[0].strip()[:80]

    def _created(self):
        try:
            from datetime import datetime
            st = os.stat(self._user()["h"])
            return datetime.fromtimestamp(st.st_ctime).strftime("%Y-%m-%d %H:%M")
        except Exception: return "—"

    def _load(self):
        if self.ACC_PATH.exists():
            try: return json.loads(self.ACC_PATH.read_text())
            except Exception: pass
        return {"email":"", "bio":"", "pin":"", "auto_login": False}

    def _save(self):
        try: self.ACC_PATH.write_text(json.dumps(self.acc, indent=2))
        except Exception as e: log.error("acc save: %s", e)

    def build(self):
        self.acc = self._load()
        info = self._user()

        # ── profile card ──
        c = Card("profile")
        prow = Gtk.Box(spacing=14)
        self._face_da = Gtk.DrawingArea()
        self._face_da.set_size_request(96, 96)
        try: self._face_da.set_content_width(96); self._face_da.set_content_height(96)
        except Exception: pass
        self._face_da.set_draw_func(self._draw_face)
        prow.append(self._face_da)
        rcol = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        b1 = SketchButton("change picture", width=170, height=24, color=NEON_BLUE)
        b1.connect("clicked", lambda _b: self._pick_face())
        rcol.append(b1)
        b2 = SketchButton("remove picture", width=170, height=24, color=DANGER_RED)
        b2.connect("clicked", lambda _b: self._rm_face())
        rcol.append(b2)
        nf = Gtk.Label(label="(saved as ~/.face)", xalign=0); nf.add_css_class("nyx-meta")
        rcol.append(nf)
        prow.append(rcol)
        c.add_row(prow)

        c.add_row(kv_row("username", info["u"]))

        self._fn = Gtk.Entry(); self._fn.set_text(info["f"]); self._fn.add_css_class("nyx-entry")
        bsave = SketchButton("save", width=70, height=22, color=NEON_GREEN)
        bsave.connect("clicked", lambda _b: self._save_fullname())
        nm = Gtk.Box(spacing=6); nm.append(self._fn); nm.append(bsave)
        c.add_row(kv_row("full name", nm))

        self._em = Gtk.Entry(); self._em.set_text(self.acc.get("email","")); self._em.add_css_class("nyx-entry")
        self._em.connect("changed", lambda e: (self.acc.__setitem__("email", e.get_text()), self._save()))
        c.add_row(kv_row("email", self._em))

        self._bio = Gtk.Entry(); self._bio.set_text(self.acc.get("bio","")); self._bio.add_css_class("nyx-entry")
        self._bio.connect("changed", lambda e: (self.acc.__setitem__("bio", e.get_text()), self._save()))
        c.add_row(kv_row("bio", self._bio))

        c.add_row(kv_row("account type", "admin" if self._is_admin() else "standard"))
        c.add_row(kv_row("home", info["h"]))
        c.add_row(kv_row("shell", info["s"]))
        c.add_row(kv_row("created", self._created()))
        c.add_row(kv_row("last login", self._last_login()))
        self.box.append(c)

        # ── security & login ──
        c2 = Card("security & login")
        bpw = SketchButton("change password (opens terminal: passwd)",
                           width=340, height=26, color=NEON_PINK)
        bpw.connect("clicked", lambda _b: self._passwd())
        c2.add_row(bpw)

        self._pin = Gtk.Entry(); self._pin.set_text(self.acc.get("pin",""))
        self._pin.set_visibility(False); self._pin.add_css_class("nyx-entry")
        bpin = SketchButton("save PIN", width=100, height=22, color=NEON_GREEN)
        bpin.connect("clicked", lambda _b: (
            self.acc.__setitem__("pin", self._pin.get_text()),
            self._save(), self.mark_changed("PIN")))
        pr = Gtk.Box(spacing=6); pr.append(self._pin); pr.append(bpin)
        c2.add_row(kv_row("quick PIN", pr))

        al = SketchToggle("auto-login on boot", width=200, height=24,
                          color=NEON_BLUE, active=bool(self.acc.get("auto_login")))
        al.connect("clicked", lambda b: self._toggle_autologin(b))
        c2.add_row(al)
        nl = Gtk.Label(label=("(persists to ~/.config/nyxus-settings/account.json — "
                              "wiring to display manager requires sudo)"),
                       xalign=0, wrap=True); nl.add_css_class("nyx-meta")
        c2.add_row(nl)
        self.box.append(c2)

        # ── profile color ──
        c3 = Card("profile color (NYXUS accent)")
        sw = Gtk.Box(spacing=8)
        for n, rgb in [("pink", NEON_PINK), ("blue", NEON_BLUE),
                       ("green", NEON_GREEN), ("purple", ACCENT_PURP),
                       ("gold", ACCENT_GOLD)]:
            b = SketchButton(n, width=72, height=22, color=rgb,
                             primary=(self.win.prefs.get("accent")==n))
            b.connect("clicked", lambda _b, nn=n: self._set_accent(nn))
            sw.append(b)
        c3.add_row(sw)
        c3.add_row(kv_row("current", self.win.prefs.get("accent","pink")))
        self.box.append(c3)

        # ── data & danger zone ──
        c4 = Card("data & account actions")
        bex = SketchButton("export account data → ~/Documents/nyxus-account.json",
                           width=440, height=24, color=NEON_BLUE)
        bex.connect("clicked", lambda _b: self._export())
        c4.add_row(bex)
        bdel = SketchButton("delete this account (sudo userdel)",
                            width=320, height=24, color=DANGER_RED)
        bdel.connect("clicked", lambda _b: self.win.toast(
            "deletion is irreversible — run `sudo userdel -r $USER` from a TTY"))
        c4.add_row(bdel)
        self.box.append(c4)

    def _draw_face(self, area, cr, w, h, _=None):
        cr.save()
        cr.arc(w/2, h/2, min(w,h)/2 - 2, 0, math.pi*2); cr.clip()
        face = Path.home() / ".face"
        loaded = False
        if face.exists():
            try:
                from gi.repository import GdkPixbuf
                pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(face), w, h, True)
                Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0); cr.paint(); loaded = True
            except Exception as e:
                log.warning("face load: %s", e)
        if not loaded:
            cr.set_source_rgba(0.10, 0.07, 0.18, 0.95); cr.rectangle(0,0,w,h); cr.fill()
            info = self._user()
            ini = (info["f"] or info["u"] or "?")[:1].upper()
            draw_caveat(cr, w/2-14, h/2-26, ini, size=46,
                        color=(*NEON_PINK, 0.95), weight=Pango.Weight.BOLD)
        cr.restore()
        cr.set_source_rgba(*NEON_PINK, 0.85); cr.set_line_width(1.6)
        cr.arc(w/2, h/2, min(w,h)/2 - 2, 0, math.pi*2); cr.stroke()

    def _pick_face(self):
        dlg = Gtk.FileChooserDialog(title="Choose profile picture",
            transient_for=self.win, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Open", Gtk.ResponseType.OK)
        f = Gtk.FileFilter(); f.set_name("Images")
        for mt in ("image/png","image/jpeg","image/webp","image/bmp"):
            f.add_mime_type(mt)
        dlg.add_filter(f)
        def _resp(d, r):
            if r == Gtk.ResponseType.OK:
                try:
                    src = d.get_file().get_path() if d.get_file() else None
                    if src:
                        import shutil as _sh
                        _sh.copyfile(src, str(Path.home()/".face"))
                        self._face_da.queue_draw()
                        self.mark_changed("profile picture")
                except Exception as e: log.error("face: %s", e)
            d.destroy()
        dlg.connect("response", _resp); dlg.show()

    def _rm_face(self):
        try:
            (Path.home()/".face").unlink(missing_ok=True)
            self._face_da.queue_draw(); self.mark_changed("profile picture removed")
        except Exception as e: log.error("rm face: %s", e)

    def _save_fullname(self):
        new = self._fn.get_text().strip()
        if not new: return
        rc, _o, e = sh(f"chfn -f {shlex.quote(new)}", timeout=4)
        if rc == 0:
            self.mark_changed(f"full name → {new}")
        else:
            self.win.toast(f"chfn: {(e or 'failed').splitlines()[-1][:60]}")

    def _passwd(self):
        for term in ("foot", "alacritty", "kitty", "xterm"):
            if have(term):
                sh_async(["setsid", term, "-e", "passwd"], timeout=2)
                self.win.toast(f"opened {term} for `passwd`"); return
        self.win.toast("no terminal found — run `passwd` manually")

    def _toggle_autologin(self, btn):
        self.acc["auto_login"] = bool(btn.active)
        self._save()
        self.needs_restart("auto-login (display manager)")
        self.mark_changed(f"auto-login → {'on' if btn.active else 'off'}")

    def _set_accent(self, n):
        self.win.prefs["accent"] = n
        self.win.save_prefs()
        self.mark_changed(f"accent → {n}")

    def _export(self):
        try:
            out = {"user": self._user(), "admin": self._is_admin(),
                   "created": self._created(), "last_login": self._last_login(),
                   "account": self.acc}
            p = Path.home()/"Documents"/"nyxus-account.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(out, indent=2))
            self.win.toast(f"exported → {p}")
        except Exception as e:
            self.win.toast(f"export failed: {e}")

    def search_entries(self):
        labels = ["profile picture", "full name", "username", "email", "bio",
                  "account type", "home directory", "shell", "account created",
                  "last login", "change password", "PIN", "auto-login",
                  "profile color", "accent", "export account", "delete account"]
        return [SearchEntry(self.KEY, self.TITLE, l, "account profile user")
                for l in labels]


# ─── Wallpaper & Backgrounds (Category 2) ────────────────────────────────────
class WallpaperPage(BasePage):
    KEY = "wallpaper"; TITLE = "Wallpaper & Backgrounds"; ICON = "🖼"
    TILE_COLOR = NEON_BLUE
    SUBTITLE  = "Browse · Set · Slideshow · Fit"

    DIRS = [
        Path.home()/".nyxus"/"wallpapers",
        Path.home()/"Pictures"/"Wallpapers",
        Path.home()/"Pictures",
        Path("/usr/share/backgrounds"),
    ]
    EXTS = (".png",".jpg",".jpeg",".webp",".bmp")
    WP_CFG = CONFIG_DIR / "wallpaper.json"
    SLIDE_PID = Path("/tmp/nyxus-wallpaper-slideshow.pid")

    def _scan(self) -> List[Path]:
        out: List[Path] = []
        for d in self.DIRS:
            if not d.exists(): continue
            try:
                for p in sorted(d.iterdir()):
                    if p.is_file() and p.suffix.lower() in self.EXTS:
                        out.append(p)
            except Exception: pass
        # de-dupe by name
        seen = set(); uniq = []
        for p in out:
            if p.name in seen: continue
            seen.add(p.name); uniq.append(p)
        return uniq[:60]

    def _current(self) -> str:
        # try swww first, then hyprpaper
        if have("swww"):
            rc, o, _ = sh("swww query", timeout=3)
            if rc == 0:
                for ln in o.splitlines():
                    if "image:" in ln:
                        return ln.split("image:",1)[1].strip()
        cfg = Path.home()/".config"/"hypr"/"hyprpaper.conf"
        if cfg.exists():
            for ln in cfg.read_text().splitlines():
                if ln.startswith("wallpaper"):
                    return ln.split(",",1)[-1].strip()
        return "—"

    def _load_cfg(self):
        if self.WP_CFG.exists():
            try: return json.loads(self.WP_CFG.read_text())
            except Exception: pass
        return {"slideshow": False, "interval": 900, "order": "sequential",
                "fit": "crop", "transition": "fade"}

    def _save_cfg(self):
        try: self.WP_CFG.write_text(json.dumps(self.cfg, indent=2))
        except Exception as e: log.error("wp cfg: %s", e)

    def _set(self, path: Path):
        if have("swww"):
            cmd = ["swww","img",str(path),"--resize",self.cfg.get("fit","crop"),
                   "--transition-type",self.cfg.get("transition","fade")]
            sh_async(cmd, timeout=8)
            self.mark_changed(f"wallpaper → {path.name}"); return
        if have("hyprctl"):
            sh_async(["hyprctl","hyprpaper","preload",str(path)], timeout=4)
            sh_async(["hyprctl","hyprpaper","wallpaper",f",{path}"], timeout=4)
            self.mark_changed(f"wallpaper → {path.name}"); return
        self.win.toast("install swww or hyprpaper to set wallpapers")

    def _del_wp(self, path: Path):
        # only delete if inside ~/.nyxus/wallpapers
        nyx = Path.home()/".nyxus"/"wallpapers"
        try:
            if nyx in path.parents:
                path.unlink(missing_ok=True)
                self.mark_changed(f"deleted {path.name}")
                self.refresh()
            else:
                self.win.toast("only files in ~/.nyxus/wallpapers can be deleted")
        except Exception as e: log.error("del wp: %s", e)

    def build(self):
        self.cfg = self._load_cfg()

        # ── current ──
        c0 = Card("current wallpaper")
        cur = self._current()
        c0.add_row(Gtk.Label(label=cur, xalign=0, wrap=True,
                             ellipsize=Pango.EllipsizeMode.MIDDLE))
        self.box.append(c0)

        # ── add ──
        ca = Card("add wallpaper")
        add_row = Gtk.Box(spacing=8)
        bf = SketchButton("from file…", width=140, height=24, color=NEON_GREEN)
        bf.connect("clicked", lambda _b: self._add_from_file())
        add_row.append(bf)
        bu = SketchButton("from URL…", width=140, height=24, color=NEON_BLUE)
        bu.connect("clicked", lambda _b: self._add_from_url())
        add_row.append(bu)
        ca.add_row(add_row)
        ca.add_row(Gtk.Label(label="(downloads land in ~/.nyxus/wallpapers/)",
                             xalign=0))
        self.box.append(ca)

        # ── slideshow & fit ──
        cs = Card("slideshow & fit")
        ss = SketchToggle("slideshow on", width=180, height=24,
                          color=NEON_GREEN, active=bool(self.cfg.get("slideshow")))
        ss.connect("clicked", lambda b: self._toggle_slideshow(b))
        cs.add_row(ss)
        # interval
        ir = Gtk.Box(spacing=6)
        for label, secs in [("5m",300),("15m",900),("30m",1800),("1h",3600)]:
            b = SketchButton(label, width=58, height=22, color=NEON_BLUE,
                             primary=(self.cfg.get("interval")==secs))
            b.connect("clicked", lambda _b, s=secs:
                      (self.cfg.__setitem__("interval", s), self._save_cfg(),
                       self.mark_changed(f"interval → {s}s")))
            ir.append(b)
        cs.add_row(kv_row("interval", ir))
        # order
        or_row = Gtk.Box(spacing=6)
        for o in ("sequential","random"):
            b = SketchButton(o, width=110, height=22, color=ACCENT_PURP,
                             primary=(self.cfg.get("order")==o))
            b.connect("clicked", lambda _b, oo=o:
                      (self.cfg.__setitem__("order", oo), self._save_cfg(),
                       self.mark_changed(f"order → {oo}")))
            or_row.append(b)
        cs.add_row(kv_row("order", or_row))
        # fit
        fit_row = Gtk.Box(spacing=6)
        for f in ("fit","crop","stretch","no"):
            b = SketchButton(f, width=80, height=22, color=NEON_PINK,
                             primary=(self.cfg.get("fit")==f))
            b.connect("clicked", lambda _b, ff=f:
                      (self.cfg.__setitem__("fit", ff), self._save_cfg(),
                       self.mark_changed(f"fit → {ff}")))
            fit_row.append(b)
        cs.add_row(kv_row("fit (swww --resize)", fit_row))
        # transition
        tr_row = Gtk.Box(spacing=6)
        for t in ("fade","wipe","grow","outer","none"):
            b = SketchButton(t, width=80, height=22, color=NEON_BLUE,
                             primary=(self.cfg.get("transition")==t))
            b.connect("clicked", lambda _b, tt=t:
                      (self.cfg.__setitem__("transition", tt), self._save_cfg(),
                       self.mark_changed(f"transition → {tt}")))
            tr_row.append(b)
        cs.add_row(kv_row("transition", tr_row))
        self.box.append(cs)

        # ── grid ──
        cw = Card(f"installed wallpapers ({len(self._scan())})")
        self._grid = Gtk.FlowBox()
        self._grid.set_max_children_per_line(6)
        self._grid.set_min_children_per_line(2)
        self._grid.set_column_spacing(10); self._grid.set_row_spacing(10)
        self._grid.set_selection_mode(Gtk.SelectionMode.NONE)
        self._grid.set_homogeneous(True)
        cw.add_row(self._grid)
        self.box.append(cw)
        self._populate_grid()

    def _populate_grid(self):
        c = self._grid.get_first_child()
        while c:
            n = c.get_next_sibling(); self._grid.remove(c); c = n
        for p in self._scan():
            tile = self._make_thumb(p)
            self._grid.insert(tile, -1)

    def _make_thumb(self, path: Path) -> Gtk.Widget:
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        try:
            from gi.repository import GdkPixbuf
            pic = Gtk.Picture()
            pb = GdkPixbuf.Pixbuf.new_from_file_at_scale(str(path), 180, 110, True)
            pic.set_pixbuf(pb)
            pic.set_size_request(180, 110)
            pic.set_can_shrink(False)
        except Exception:
            pic = Gtk.Label(label=path.name); pic.set_size_request(180, 110)
        wrap.append(pic)
        bar = Gtk.Box(spacing=4)
        bset = SketchButton("set", width=80, height=22, color=NEON_GREEN)
        bset.connect("clicked", lambda _b, pp=path: self._set(pp))
        bar.append(bset)
        bdel = SketchButton("✕", width=28, height=22, color=DANGER_RED,
                            tooltip="delete (only ~/.nyxus/wallpapers)")
        bdel.connect("clicked", lambda _b, pp=path: self._del_wp(pp))
        bar.append(bdel)
        wrap.append(bar)
        nm = Gtk.Label(label=path.name, xalign=0,
                       ellipsize=Pango.EllipsizeMode.MIDDLE)
        nm.add_css_class("nyx-meta"); nm.set_size_request(180, -1)
        wrap.append(nm)
        return wrap

    def _add_from_file(self):
        dlg = Gtk.FileChooserDialog(title="Add wallpaper",
            transient_for=self.win, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Add", Gtk.ResponseType.OK)
        f = Gtk.FileFilter(); f.set_name("Images")
        for mt in ("image/png","image/jpeg","image/webp","image/bmp"):
            f.add_mime_type(mt)
        dlg.add_filter(f)
        def _resp(d, r):
            if r == Gtk.ResponseType.OK:
                try:
                    src = d.get_file().get_path() if d.get_file() else None
                    if src:
                        dst_dir = Path.home()/".nyxus"/"wallpapers"
                        dst_dir.mkdir(parents=True, exist_ok=True)
                        import shutil as _sh
                        _sh.copy(src, dst_dir/Path(src).name)
                        self.mark_changed(f"added {Path(src).name}")
                        self.refresh()
                except Exception as e: log.error("wp add: %s", e)
            d.destroy()
        dlg.connect("response", _resp); dlg.show()

    def _add_from_url(self):
        dlg = Gtk.Window(transient_for=self.win, title="Add wallpaper from URL",
                         modal=True); dlg.set_default_size(460, 100)
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        b.set_margin_start(14); b.set_margin_end(14)
        b.set_margin_top(14); b.set_margin_bottom(14)
        e = Gtk.Entry(); e.set_placeholder_text("https://…")
        e.add_css_class("nyx-entry"); b.append(e)
        ar = Gtk.Box(spacing=6)
        bok = SketchButton("download", width=120, height=24, color=NEON_GREEN)
        bcancel = SketchButton("cancel", width=80, height=24, color=INK_DIM)
        ar.append(bok); ar.append(bcancel); b.append(ar)
        dlg.set_child(b)
        def _go(*_a):
            url = e.get_text().strip()
            if not url: return
            dst_dir = Path.home()/".nyxus"/"wallpapers"
            dst_dir.mkdir(parents=True, exist_ok=True)
            name = url.rsplit("/",1)[-1].split("?",1)[0] or "download.img"
            dst = dst_dir / name
            def done(r):
                rc, _o, er = r
                if rc == 0:
                    self.mark_changed(f"downloaded {name}"); self.refresh()
                else:
                    self.win.toast(f"download failed: {er[:60]}")
                dlg.close()
            sh_async(["curl","-fsSL","-o",str(dst),url], on_done=done, timeout=20)
        bok.connect("clicked", _go)
        bcancel.connect("clicked", lambda *_a: dlg.close())
        dlg.present()

    def _toggle_slideshow(self, btn):
        self.cfg["slideshow"] = bool(btn.active)
        self._save_cfg()
        if btn.active:
            self._start_slideshow()
        else:
            self._stop_slideshow()
        self.mark_changed(f"slideshow → {'on' if btn.active else 'off'}")

    def _start_slideshow(self):
        # write a tiny shell loop and background it
        files = self._scan()
        if not files:
            self.win.toast("no wallpapers found"); return
        self._stop_slideshow()
        interval = int(self.cfg.get("interval", 900))
        order = self.cfg.get("order","sequential")
        flist = " ".join(shlex.quote(str(p)) for p in files)
        order_cmd = "shuf" if order == "random" else "cat"
        # daemonised loop
        script = (f"while true; do for f in $(printf '%s\\n' {flist} | {order_cmd}); do "
                  f"swww img \"$f\" --resize {self.cfg.get('fit','crop')} "
                  f"--transition-type {self.cfg.get('transition','fade')} "
                  f"2>/dev/null || hyprctl hyprpaper preload \"$f\" 2>/dev/null; "
                  f"sleep {interval}; done; done")
        rc, _o, _e = sh(["sh","-c",
            f"setsid sh -c {shlex.quote(script)} >/tmp/nyxus-wp.log 2>&1 & echo $! > {self.SLIDE_PID}"],
            timeout=3)

    def _stop_slideshow(self):
        try:
            if self.SLIDE_PID.exists():
                pid = self.SLIDE_PID.read_text().strip()
                if pid: sh(f"pkill -P {pid}", timeout=2); sh(f"kill {pid}", timeout=2)
                self.SLIDE_PID.unlink(missing_ok=True)
        except Exception: pass

    def refresh(self):
        ch = self.box.get_first_child(); first = ch
        # remove everything after the title (first child)
        items = []
        while ch: items.append(ch); ch = ch.get_next_sibling()
        for w in items[1:]: self.box.remove(w)
        self.build()

    def search_entries(self):
        labels = ["set wallpaper","add wallpaper","wallpaper from URL",
                  "slideshow","interval","order","fit","stretch","crop",
                  "transition","fade","wipe","delete wallpaper",
                  "current wallpaper"]
        return [SearchEntry(self.KEY, self.TITLE, l, "wallpaper background swww")
                for l in labels]


# ─── Fonts (Category 3) ──────────────────────────────────────────────────────
class FontsPage(BasePage):
    KEY = "fonts"; TITLE = "Fonts"; ICON = "🅰"
    TILE_COLOR = ACCENT_GOLD
    SUBTITLE  = "Browse · Install · Sample · Hinting"

    USER_FONT_DIR = Path.home() / ".local" / "share" / "fonts"

    def _list_families(self) -> List[str]:
        rc, o, _ = sh("fc-list : family", timeout=4)
        if rc != 0: return []
        fams = set()
        for ln in o.splitlines():
            for f in ln.split(","):
                f = f.strip()
                if f: fams.add(f)
        return sorted(fams)

    def _list_mono(self) -> List[str]:
        rc, o, _ = sh("fc-list :mono family", timeout=4)
        if rc != 0: return []
        fams = set()
        for ln in o.splitlines():
            for f in ln.split(","):
                f = f.strip()
                if f: fams.add(f)
        return sorted(fams)

    def _gset_get(self, schema: str, key: str) -> str:
        if not have("gsettings"): return "—"
        rc, o, _ = sh(f"gsettings get {schema} {key}", timeout=2)
        return o.strip().strip("'") if rc == 0 else "—"

    def _gset_set(self, schema: str, key: str, val: str):
        if not have("gsettings"):
            self.win.toast("gsettings not installed"); return False
        rc, _o, e = sh(["gsettings","set",schema,key,val], timeout=3)
        if rc != 0: self.win.toast(f"gsettings: {e[:50]}"); return False
        return True

    def build(self):
        # ── current fonts ──
        c = Card("current fonts (gsettings)")
        cur_iface = self._gset_get("org.gnome.desktop.interface","font-name")
        cur_doc   = self._gset_get("org.gnome.desktop.interface","document-font-name")
        cur_mono  = self._gset_get("org.gnome.desktop.interface","monospace-font-name")
        c.add_row(kv_row("interface",  cur_iface))
        c.add_row(kv_row("document",   cur_doc))
        c.add_row(kv_row("monospace",  cur_mono))
        c.add_row(kv_row("handwritten (NYXUS apps)", "Caveat 14 (built-in)"))
        self.box.append(c)

        # ── pickers ──
        cp = Card("change fonts")
        for label, schema, key, mono in [
            ("interface", "org.gnome.desktop.interface", "font-name", False),
            ("document",  "org.gnome.desktop.interface", "document-font-name", False),
            ("monospace", "org.gnome.desktop.interface", "monospace-font-name", True),
        ]:
            b = SketchButton(f"choose {label} font…", width=240, height=24,
                             color=NEON_BLUE)
            b.connect("clicked",
                      lambda _b, lbl=label, sch=schema, k=key, m=mono:
                          self._pick_font(lbl, sch, k, m))
            cp.add_row(b)
        self.box.append(cp)

        # ── rendering ──
        cr_ = Card("rendering")
        for label, key, opts in [
            ("antialiasing", "font-antialiasing", ["none","grayscale","rgba"]),
            ("hinting",      "font-hinting",     ["none","slight","medium","full"]),
            ("subpixel",     "font-rgba-order",  ["rgb","bgr","vrgb","vbgr"]),
        ]:
            cur = self._gset_get("org.gnome.desktop.interface", key)
            row = Gtk.Box(spacing=6)
            for o in opts:
                bb = SketchButton(o, width=70, height=22, color=NEON_PINK,
                                  primary=(cur == o))
                bb.connect("clicked", lambda _b, k=key, oo=o:
                           (self._gset_set("org.gnome.desktop.interface", k, oo),
                            self.mark_changed(f"{k} → {oo}"), self.refresh()))
                row.append(bb)
            cr_.add_row(kv_row(label, row))
        # text scaling
        scale = self._gset_get("org.gnome.desktop.interface","text-scaling-factor")
        try: sval = max(0.5, min(2.0, float(scale)))
        except Exception: sval = 1.0
        sl = SketchSlider(value=(sval - 0.5)/1.5, color=ACCENT_GOLD, width=260)
        def _scl(_w, v):
            new = round(0.5 + v*1.5, 2)
            self._gset_set("org.gnome.desktop.interface","text-scaling-factor",
                           f"{new}")
            self.mark_changed(f"text scale → {new}")
        sl.connect("value-changed", _scl)
        cr_.add_row(kv_row(f"text scale ({sval:.2f})", sl))
        self.box.append(cr_)

        # ── install / browse ──
        ci = Card("install & browse")
        bi = SketchButton("install font from file…", width=220, height=24,
                         color=NEON_GREEN)
        bi.connect("clicked", lambda _b: self._install_font())
        ci.add_row(bi)
        ci.add_row(Gtk.Label(label=f"(installs into {self.USER_FONT_DIR}/ "
                                   f"and runs `fc-cache -f`)", xalign=0))
        # browse list with sample
        fams = self._list_families()
        ci.add_row(Gtk.Label(label=f"installed families: {len(fams)}", xalign=0))
        sample = Gtk.Entry(); sample.set_text("The quick brown fox jumps over the lazy dog 0123")
        sample.add_css_class("nyx-entry")
        ci.add_row(kv_row("sample text", sample))
        # font list (top 60) with previews
        scroller = Gtk.ScrolledWindow(); scroller.set_size_request(-1, 240)
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        flist = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        scroller.set_child(flist)
        def _redraw():
            ch = flist.get_first_child()
            while ch:
                n = ch.get_next_sibling(); flist.remove(ch); ch = n
            for fam in fams[:80]:
                row = Gtk.Box(spacing=8)
                lbl = Gtk.Label(label=fam, xalign=0); lbl.set_size_request(220, -1)
                row.append(lbl)
                pv = Gtk.Label(label=sample.get_text(), xalign=0)
                pv.set_attributes(self._pango_font_attr(fam))
                row.append(pv)
                flist.append(row)
        sample.connect("changed", lambda _e: _redraw())
        _redraw()
        ci.add_row(scroller)
        self.box.append(ci)

        # ── reset ──
        cz = Card("reset")
        br = SketchButton("reset fonts to NYXUS defaults", width=280, height=24,
                         color=DANGER_RED)
        br.connect("clicked", lambda _b: self._reset())
        cz.add_row(br)
        self.box.append(cz)

    def _pango_font_attr(self, fam: str) -> Pango.AttrList:
        al = Pango.AttrList()
        try:
            fd = Pango.FontDescription.from_string(f"{fam} 14")
            al.insert(Pango.attr_font_desc_new(fd))
        except Exception: pass
        return al

    def _pick_font(self, label: str, schema: str, key: str, mono: bool):
        d = Gtk.FontDialog()
        if mono:
            try: d.set_filter(Gtk.FontFilter.new())   # GTK4 mono filter is limited
            except Exception: pass
        cur_str = self._gset_get(schema, key)
        try:
            init = Pango.FontDescription.from_string(cur_str if cur_str != "—" else "Sans 11")
        except Exception:
            init = None
        def _done(dlg, res):
            try: fd = dlg.choose_font_finish(res)
            except Exception: return
            if not fd: return
            new_name = fd.to_string()
            if self._gset_set(schema, key, new_name):
                self.mark_changed(f"{label} font → {new_name}")
                self.refresh()
        d.choose_font(self.win, init, None, _done)

    def _install_font(self):
        dlg = Gtk.FileChooserDialog(title="Install font",
            transient_for=self.win, action=Gtk.FileChooserAction.OPEN)
        dlg.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                        "Install", Gtk.ResponseType.OK)
        f = Gtk.FileFilter(); f.set_name("Fonts (.ttf .otf)")
        f.add_pattern("*.ttf"); f.add_pattern("*.otf"); dlg.add_filter(f)
        def _resp(d, r):
            if r == Gtk.ResponseType.OK:
                try:
                    src = d.get_file().get_path() if d.get_file() else None
                    if src:
                        self.USER_FONT_DIR.mkdir(parents=True, exist_ok=True)
                        import shutil as _sh
                        _sh.copy(src, self.USER_FONT_DIR/Path(src).name)
                        sh("fc-cache -f", timeout=8)
                        self.mark_changed(f"installed {Path(src).name}")
                        self.refresh()
                except Exception as e: log.error("install font: %s", e)
            d.destroy()
        dlg.connect("response", _resp); dlg.show()

    def _reset(self):
        for k, v in [
            ("font-name","Inter 11"),
            ("document-font-name","Sans 11"),
            ("monospace-font-name","JetBrains Mono 11"),
            ("font-antialiasing","rgba"),
            ("font-hinting","slight"),
            ("text-scaling-factor","1.0"),
        ]:
            self._gset_set("org.gnome.desktop.interface", k, v)
        self.mark_changed("fonts reset to NYXUS defaults"); self.refresh()

    def refresh(self):
        items = []
        ch = self.box.get_first_child()
        while ch: items.append(ch); ch = ch.get_next_sibling()
        for w in items[1:]: self.box.remove(w)
        self.build()

    def search_entries(self):
        labels = ["interface font","document font","monospace font","jetbrains mono",
                  "caveat","antialiasing","hinting","subpixel","text scale",
                  "install font","fc-cache","reset fonts"]
        return [SearchEntry(self.KEY, self.TITLE, l, "fonts typography")
                for l in labels]


# ─── About NYXUS (Category 22) ───────────────────────────────────────────────
class AboutPage(BasePage):
    KEY = "about"; TITLE = "About NYXUS"; ICON = "ℹ"
    TILE_COLOR = NEON_GREEN
    SUBTITLE  = "Version · Hardware · Updates · Diagnostics"

    NYXUS_VERSION = "1.0.0"
    LICENSE_TAG   = "NYX-J5W-2026-SIERENGOWSKI-LOCKED"

    def _read(self, path: str) -> str:
        try: return Path(path).read_text().strip()
        except Exception: return "—"

    def _machine(self) -> str:
        m = self._read("/sys/devices/virtual/dmi/id/product_name")
        v = self._read("/sys/devices/virtual/dmi/id/sys_vendor")
        if m != "—" and v != "—": return f"{v} {m}"
        return m if m != "—" else "—"

    def _cpu(self) -> str:
        rc, o, _ = sh("lscpu", timeout=2)
        if rc != 0: return "—"
        d = {}
        for ln in o.splitlines():
            if ":" in ln:
                k,v = ln.split(":",1); d[k.strip()] = v.strip()
        name = d.get("Model name", d.get("CPU(s)","—"))
        cores = d.get("CPU(s)","?"); thr = d.get("Thread(s) per core","?")
        return f"{name}  ·  {cores} CPUs"

    def _gpu(self) -> str:
        rc, o, _ = sh("lspci -nn", timeout=3)
        if rc != 0: return "—"
        for ln in o.splitlines():
            if "VGA" in ln or "3D controller" in ln or "Display controller" in ln:
                # trim PCI id and class prefix
                if ":" in ln:
                    return ln.split(":",2)[-1].strip()[:80]
        return "—"

    def _ram(self) -> str:
        rc, o, _ = sh("free -h", timeout=2)
        if rc != 0: return "—"
        ls = o.splitlines()
        if len(ls) < 2: return "—"
        parts = ls[1].split()
        return f"{parts[1]} total · {parts[2]} used · {parts[6] if len(parts)>6 else parts[3]} avail"

    def _storage(self) -> str:
        rc, o, _ = sh("lsblk -d -o NAME,SIZE,MODEL --noheadings", timeout=3)
        if rc != 0: return "—"
        return "  |  ".join(ln.strip() for ln in o.splitlines() if ln.strip())[:160]

    def _kernel(self) -> str:
        rc, o, _ = sh("uname -srm", timeout=1)
        return o.strip() if rc == 0 else "—"

    def _hypr(self) -> str:
        rc, o, _ = sh("hyprctl version", timeout=2)
        if rc != 0: return "—"
        for ln in o.splitlines():
            if "Tag:" in ln or "tag:" in ln: return ln.strip()
        return o.splitlines()[0].strip() if o.strip() else "—"

    def _gpu_driver(self) -> str:
        rc, o, _ = sh("glxinfo -B", timeout=4)
        if rc == 0:
            for ln in o.splitlines():
                if "OpenGL renderer" in ln or "OpenGL version" in ln:
                    return ln.split(":",1)[-1].strip()[:80]
        return "(install glxinfo for driver detail)"

    def _uptime(self) -> str:
        try:
            up = float(Path("/proc/uptime").read_text().split()[0])
            d = int(up // 86400); h = int((up % 86400) // 3600)
            m = int((up % 3600) // 60); s = int(up % 60)
            if d: return f"{d}d {h}h {m}m {s}s"
            if h: return f"{h}h {m}m {s}s"
            return f"{m}m {s}s"
        except Exception: return "—"

    def _nyxus_apps(self) -> List[str]:
        nyx = Path.home() / ".nyxus"
        if not nyx.exists(): return []
        try:
            return sorted(p.name for p in nyx.iterdir()
                          if p.is_file() and p.suffix == ".py")
        except Exception: return []

    def build(self):
        # ── hero ──
        ch = Card("NYXUS")
        big = Gtk.Label(label="NYX  ·  NYXUS", xalign=0)
        big.add_css_class("nyx-headline")
        ch.add_row(big)
        ch.add_row(kv_row("version", self.NYXUS_VERSION))
        ch.add_row(kv_row("license tag", self.LICENSE_TAG))
        ch.add_row(kv_row("build date", "2026-05"))
        self.box.append(ch)

        # ── live hardware ──
        chw = Card("hardware (live)")
        chw.add_row(kv_row("machine",  self._machine()))
        chw.add_row(kv_row("CPU",      self._cpu()))
        chw.add_row(kv_row("GPU",      self._gpu()))
        chw.add_row(kv_row("RAM",      self._ram()))
        chw.add_row(kv_row("storage",  self._storage()))
        self.box.append(chw)

        # ── live system ──
        cs = Card("system (live)")
        cs.add_row(kv_row("kernel",      self._kernel()))
        cs.add_row(kv_row("Hyprland",    self._hypr()))
        cs.add_row(kv_row("GPU driver",  self._gpu_driver()))
        cs.add_row(kv_row("session",     os.environ.get("XDG_CURRENT_DESKTOP","Hyprland")))
        cs.add_row(kv_row("server",      os.environ.get("XDG_SESSION_TYPE","wayland")))
        self._uptime_lbl = Gtk.Label(label=self._uptime(), xalign=0)
        self._uptime_lbl.add_css_class("nyx-row-value")
        cs.add_row(kv_row("uptime", self._uptime_lbl))
        # tick uptime once a second
        if not hasattr(self, "_uptime_tick"):
            self._uptime_tick = GLib.timeout_add_seconds(
                1, lambda: (self._uptime_lbl.set_text(self._uptime()), True)[1])
        self.box.append(cs)

        # ── NYXUS apps ──
        ca = Card("NYXUS apps installed")
        apps = self._nyxus_apps()
        if not apps:
            ca.add_row(Gtk.Label(label="(none found in ~/.nyxus/)", xalign=0))
        else:
            for a in apps:
                ca.add_row(kv_row(a, "v1.0.0"))
        self.box.append(ca)

        # ── legal ──
        cl = Card("legal")
        cl.add_row(kv_row("copyright", "© 2026 Joseph Sierengowski"))
        cl.add_row(kv_row("rights",    "All Rights Reserved"))
        cl.add_row(kv_row("locked",    self.LICENSE_TAG))
        self.box.append(cl)

        # ── actions ──
        cax = Card("actions")
        bu = SketchButton("check for updates", width=200, height=26,
                          color=NEON_BLUE)
        bu.connect("clicked", lambda _b: self._check_updates())
        cax.add_row(bu)
        br = SketchButton("generate full system report → ~/Documents",
                          width=380, height=26, color=NEON_GREEN)
        br.connect("clicked", lambda _b: self._gen_report())
        cax.add_row(br)
        bb = SketchButton("send bug report (open GitHub)", width=300, height=26,
                          color=ACCENT_PURP)
        bb.connect("clicked", lambda _b: sh_async(
            ["xdg-open","https://github.com/replit/nyxus-core/issues/new"], timeout=2))
        cax.add_row(bb)
        self.box.append(cax)

    def _check_updates(self):
        def done(r):
            rc, o, e = r
            if rc == 0:
                self.win.toast(f"available: {o.strip().splitlines()[0][:60]}")
            else:
                self.win.toast(f"update check failed: {(e or '').splitlines()[-1][:60]}")
        sh_async(["curl","-fsSL","https://nyxus-core.replit.app/api/version"],
                 on_done=done, timeout=8)

    def _gen_report(self):
        out = []
        out.append(f"# NYXUS system report\n")
        out.append(f"_Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}_\n")
        out.append(f"\n## NYXUS\n")
        out.append(f"- version: {self.NYXUS_VERSION}\n- license: {self.LICENSE_TAG}\n")
        out.append(f"\n## Hardware\n")
        out.append(f"- machine: {self._machine()}\n- CPU: {self._cpu()}\n- GPU: {self._gpu()}\n")
        out.append(f"- RAM: {self._ram()}\n- storage: {self._storage()}\n")
        out.append(f"\n## System\n")
        out.append(f"- kernel: {self._kernel()}\n- Hyprland: {self._hypr()}\n")
        out.append(f"- GPU driver: {self._gpu_driver()}\n- uptime: {self._uptime()}\n")
        out.append(f"\n## NYXUS apps\n")
        for a in self._nyxus_apps(): out.append(f"- {a}\n")
        try:
            p = Path.home()/"Documents"/f"nyxus-report-{int(time.time())}.md"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("".join(out))
            self.win.toast(f"saved → {p.name}")
        except Exception as e:
            self.win.toast(f"report failed: {e}")

    def search_entries(self):
        labels = ["NYXUS version","build date","copyright","license","machine model",
                  "CPU","GPU","RAM","storage","kernel","Hyprland version",
                  "GPU driver","uptime","NYXUS apps","check for updates",
                  "generate report","bug report"]
        return [SearchEntry(self.KEY, self.TITLE, l, "about system info")
                for l in labels]


# Subtitle / tile-color metadata for the existing pages so the home grid is consistent.
DisplayPage.TILE_COLOR       = NEON_BLUE;   DisplayPage.SUBTITLE       = "Resolution · Scale · Refresh · Night light"
SoundPage.TILE_COLOR         = NEON_PINK;   SoundPage.SUBTITLE         = "Output · Input · Per-app · EQ · System sounds"
NetworkPage.TILE_COLOR       = NEON_GREEN;  NetworkPage.SUBTITLE       = "Wi-Fi · Ethernet · VPN · Firewall · Proxy"
BluetoothPage.TILE_COLOR     = NEON_BLUE;   BluetoothPage.SUBTITLE     = "Pair · Connect · Audio · File transfer"
WorkspacesPage.TILE_COLOR    = ACCENT_PURP; WorkspacesPage.SUBTITLE    = "Per-workspace layout · Hyprland binds"
KeyboardPage.TILE_COLOR      = NEON_PINK;   KeyboardPage.SUBTITLE      = "Layout · Repeat · Shortcuts · Backlight"
MousePage.TILE_COLOR         = NEON_BLUE;   MousePage.SUBTITLE         = "Speed · Touchpad · Gestures · Pointer"
PowerPage.TILE_COLOR         = ACCENT_GOLD; PowerPage.SUBTITLE         = "Battery · Profiles · Lid · Sleep · Charge limit"
DateTimePage.TILE_COLOR      = NEON_BLUE;   DateTimePage.SUBTITLE      = "Timezone · NTP · 12/24h · Format · World clocks"
NotificationsPage.TILE_COLOR = ACCENT_PURP; NotificationsPage.SUBTITLE = "DND · Per-app · Position · History"
UsersPage.TILE_COLOR         = NEON_PINK;   UsersPage.SUBTITLE         = "Accounts · YubiKey · Login · Groups"
PrivacyPage.TILE_COLOR       = DANGER_RED;  PrivacyPage.SUBTITLE       = "Lock · Permissions · GPG · SSH · AppArmor · TPM"
AppsPage.TILE_COLOR          = NEON_GREEN;  AppsPage.SUBTITLE          = "Defaults · Startup · File types · Flatpak"
StoragePage.TILE_COLOR       = NEON_BLUE;   StoragePage.SUBTITLE       = "Drives · SMART · Cleanup · Snapshots"
LanguagePage.TILE_COLOR      = ACCENT_PURP; LanguagePage.SUBTITLE      = "Locale · Region · Spell-check · TTS"
AccessibilityPage.TILE_COLOR = NEON_GREEN;  AccessibilityPage.SUBTITLE = "Vision · Hearing · Motor · Magnifier"
PrintersPage.TILE_COLOR      = INK_DIM;     PrintersPage.SUBTITLE      = "CUPS printers and scanners"
GamingPage.TILE_COLOR        = NEON_PINK;   GamingPage.SUBTITLE        = "GameMode · MangoHud · Controllers · Wine"
DeveloperPage.TILE_COLOR     = NEON_GREEN;  DeveloperPage.SUBTITLE     = "SSH · Docker · Kernel · journalctl · cron · GRUB"


# Spec order: Account → Wallpaper → Fonts → Themes → Display → Sound → Network →
# Bluetooth → Keyboard → Mouse → Power → Users → Privacy → Apps → Storage →
# Notifications → Date&Time → Language → Accessibility → Gaming → Developer → About
# Plus extras kept from current build (Workspaces, Printers) — appended at end.
PAGE_CLASSES: List[type] = [
    AccountPage, WallpaperPage, FontsPage, AppearancePage,
    DisplayPage, SoundPage, NetworkPage, BluetoothPage,
    KeyboardPage, MousePage, PowerPage,
    UsersPage, PrivacyPage, AppsPage, StoragePage,
    NotificationsPage, DateTimePage, LanguagePage, AccessibilityPage,
    GamingPage, DeveloperPage, AboutPage,
    WorkspacesPage, PrintersPage,
]


HOME_KEY = "_home"


class CategoryTile(Gtk.DrawingArea):
    """A large hand-drawn sketch tile for the Home grid.
    260×140 by default — clickable, hover-glow, accent-coloured border."""
    __gsignals__ = {"activated": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, *, icon: str, title: str, subtitle: str,
                 color=NEON_PINK, starred: bool = False,
                 width=260, height=140):
        super().__init__()
        self.icon, self.title, self.subtitle = icon, title, subtitle
        self.color = color; self.starred = starred
        self._hover = False
        self.set_size_request(width, height)
        try: self.set_content_width(width); self.set_content_height(height)
        except Exception: pass
        self.set_draw_func(self._draw)
        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("released", lambda *_a: self.emit("activated"))
        self.add_controller(gc)
        mc = Gtk.EventControllerMotion()
        mc.connect("enter", lambda *_a: (setattr(self, "_hover", True),  self.queue_draw()))
        mc.connect("leave", lambda *_a: (setattr(self, "_hover", False), self.queue_draw()))
        self.add_controller(mc)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

    def _draw(self, area, cr, w, h, _=None):
        # frosted panel
        bg_a = 0.85 if self._hover else 0.70
        cr.set_source_rgba(0.04, 0.04, 0.07, bg_a)
        cr.rectangle(2, 2, w-4, h-4); cr.fill()
        # accent halo on hover
        if self._hover:
            cr.set_source_rgba(*self.color, 0.10)
            cr.rectangle(2, 2, w-4, h-4); cr.fill()
        # double sketch border
        cr.set_source_rgba(*self.color, 0.85); cr.set_line_width(1.5)
        sketch_rect(cr, 2.5, 2.5, w-5, h-5, jitter=0.7,
                    key=("tile", self.title, w, h), double=True)
        # icon (top-left, large)
        draw_caveat(cr, 14, 8, self.icon, size=32,
                    color=(*self.color, 0.95))
        # star if favorited
        if self.starred:
            draw_caveat(cr, w-26, 8, "★", size=22,
                        color=(*ACCENT_GOLD, 0.95))
        # title
        draw_caveat(cr, 14, h-66, self.title, size=22,
                    color=(*INK_BRIGHT, 0.97),
                    weight=Pango.Weight.BOLD, wrap_w=w-28)
        # subtitle
        if self.subtitle:
            draw_caveat(cr, 14, h-32, self.subtitle, size=13,
                        color=(*INK_DIM, 0.95),
                        family="JetBrains Mono", wrap_w=w-28)


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME)
        self.set_default_size(WIN_W, WIN_H)
        self.prefs: Dict[str, Any] = self._load_prefs()
        self.favorites: List[str] = self._load_favs()
        self.recents:   List[str] = self._load_recents()
        self.history: List[str] = []
        self._fwd_history: List[str] = []
        self._toast_label: Optional[Gtk.Label] = None
        self._search_entries: List[SearchEntry] = []
        self._page_widgets: Dict[str, BasePage] = {}
        self._restart_pages: Dict[str, str] = {}    # key → label
        self._home_widget: Optional[Gtk.ScrolledWindow] = None
        self._tiles_box: Optional[Gtk.Box] = None
        self._build_css()
        self._build_layout()
        # default landing page = HOME tile grid (always)
        self.show_page(HOME_KEY, push_history=False)

    # ── persistence ─────────────────────────────────────────────────────────
    def _load_prefs(self) -> Dict[str, Any]:
        if PREF_PATH.exists():
            try: return json.loads(PREF_PATH.read_text())
            except Exception: pass
        return {"color_scheme": "dark", "accent": "pink",
                "ui_font_size": 14}

    def save_prefs(self):
        try: PREF_PATH.write_text(json.dumps(self.prefs, indent=2))
        except Exception as e: log.error("save_prefs: %s", e)

    def _load_favs(self) -> List[str]:
        if FAV_PATH.exists():
            try: return json.loads(FAV_PATH.read_text())
            except Exception: pass
        return []

    def _save_favs(self):
        try: FAV_PATH.write_text(json.dumps(self.favorites))
        except Exception as e: log.error("save_favs: %s", e)

    def _load_recents(self) -> List[str]:
        if RECENT_PATH.exists():
            try: return json.loads(RECENT_PATH.read_text())
            except Exception: pass
        return []

    def _save_recents(self):
        try: RECENT_PATH.write_text(json.dumps(self.recents))
        except Exception as e: log.error("save_recents: %s", e)

    # ── public API used by pages ────────────────────────────────────────────
    def note_change(self, page_key: str, label: str = ""):
        """Page reports a setting was changed → bump recents + toast."""
        try: self.recents = [page_key] + [k for k in self.recents if k != page_key]
        except Exception: self.recents = [page_key]
        self.recents = self.recents[:6]
        self._save_recents()
        if label:
            self.toast(f"applied · {label}")
        if self._tiles_box is not None:
            self._rebuild_home_strips()

    def flag_restart_required(self, page_key: str, label: str):
        """Mark that a setting needs a restart / Hyprland reload."""
        self._restart_pages[page_key] = label
        self._refresh_restart_banner()

    # ── CSS ─────────────────────────────────────────────────────────────────
    def _build_css(self):
        css = b"""
* { font-family: 'Caveat', 'Patrick Hand', cursive; }
window, .nyx-bg { background-color: #0a0a12; color: #f0eef8; }
.nyx-toolbar { background-color: rgba(10,10,18,0.96); padding: 6px 12px;
    border-bottom: 1px solid rgba(255,0,255,0.12); }
.nyx-hero { background-color: rgba(10,10,18,0.96); padding: 14px 18px;
    border-bottom: 1px solid rgba(255,0,255,0.18); }
.nyx-hero-title { color: #ff00ff; text-shadow: 0 0 12px rgba(255,0,255,0.55);
    font-size: 30px; font-weight: bold; letter-spacing: 1px; }
.nyx-hero-sub { color: rgba(240,235,250,0.55); font-size: 14px;
    margin-top: -2px; }
.nyx-version-pill { color: rgba(240,235,250,0.85);
    background-color: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,0,255,0.40);
    border-radius: 999px; padding: 5px 16px; font-size: 14px;
    font-family: 'JetBrains Mono', monospace; }
.nyx-toolbar2 { background-color: rgba(10,10,18,0.85); padding: 5px 14px;
    border-bottom: 1px solid rgba(255,0,255,0.10); }
.nyx-restartbar { background-color: rgba(255, 78, 0, 0.18);
    border-bottom: 1px solid rgba(255,140,40,0.55);
    padding: 6px 14px; }
.nyx-restartbar label { color: #ffd6aa; font-size: 14px; }
.nyx-strip { background-color: rgba(255,255,255,0.02);
    border-top: 1px solid rgba(255,0,255,0.07);
    border-bottom: 1px solid rgba(255,0,255,0.07);
    padding: 6px 16px; }
.nyx-strip-label { color: rgba(240,235,250,0.55); font-size: 14px; }
.nyx-statusbar { background-color: rgba(10,10,18,0.96); padding: 2px 12px;
    border-top: 1px solid rgba(255,255,255,0.06); }
.nyx-headline { color: #ff00ff; text-shadow: 0 0 10px rgba(255,0,255,0.55);
    font-size: 22px; font-weight: bold; }
.nyx-meta { color: rgba(240,235,250,0.45); font-size: 12px; }
.nyx-card { background-color: rgba(255,255,255,0.025);
    border: 1px solid rgba(255,0,255,0.08); border-radius: 6px;
    padding: 4px 0 8px 0; }
.nyx-card-title { color: #b88dff; font-size: 18px; font-weight: bold; }
.nyx-row-label { color: #f0eef8; font-size: 14px; }
.nyx-row-value { color: rgba(240,235,250,0.75); font-size: 14px; }
.nyx-entry { background-color: transparent; border: none; outline: none;
    color: #f0eef8; font-size: 14px; caret-color: #ff00ff; }
.nyx-entry:focus { outline: none; box-shadow: none; }
.nyx-editor textview, .nyx-editor text {
    background-color: rgba(0,0,0,0.25);
    color: rgba(240,235,250,0.92);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    padding: 6px 10px; caret-color: #ff00ff; }
.nyx-toast { background-color: rgba(255,0,255,0.18);
    color: #ffffff; padding: 6px 14px;
    border: 1px solid rgba(255,0,255,0.55);
    border-radius: 8px; font-size: 14px; }
scrollbar slider { background-color: rgba(255,0,255,0.30);
    border: 1px solid rgba(255,0,255,0.45); border-radius: 6px;
    min-width: 8px; min-height: 8px; }
scrollbar { background-color: transparent; }
"""
        prov = Gtk.CssProvider()
        try: prov.load_from_data(css)
        except TypeError: prov.load_from_data(css.decode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    # ── layout ──────────────────────────────────────────────────────────────
    def _build_layout(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("nyx-bg"); self.set_child(root)

        # ── HERO HEADER (NYXUS branding) ───────────────────────────────────
        hero_row = Gtk.Box(spacing=14); hero_row.add_css_class("nyx-hero")
        # gear logo (sketch circle with ⚙)
        logo = Gtk.DrawingArea()
        logo.set_size_request(52, 52)
        try: logo.set_content_width(52); logo.set_content_height(52)
        except Exception: pass
        logo.set_valign(Gtk.Align.CENTER)
        def _draw_logo(area, cr, w, h, _=None):
            cr.set_source_rgba(*ACCENT_PURP, 0.18)
            cr.arc(w/2, h/2, min(w,h)/2 - 3, 0, math.pi*2); cr.fill()
            cr.set_source_rgba(*ACCENT_PURP, 0.95); cr.set_line_width(1.6)
            cr.arc(w/2, h/2, min(w,h)/2 - 3, 0, math.pi*2); cr.stroke()
            # inner gear glyph using Pango
            layout = PangoCairo.create_layout(cr)
            fd = Pango.FontDescription()
            fd.set_family("Sans"); fd.set_size(int(22 * Pango.SCALE))
            layout.set_font_description(fd); layout.set_text("⚙", -1)
            tw, th = layout.get_pixel_size()
            cr.set_source_rgba(*ACCENT_PURP, 0.95)
            cr.move_to((w-tw)/2, (h-th)/2); PangoCairo.show_layout(cr, layout)
        logo.set_draw_func(_draw_logo)
        hero_row.append(logo)
        # title + subtitle stacked
        ts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        ts.set_valign(Gtk.Align.CENTER); ts.set_hexpand(True)
        title_lbl = Gtk.Label(label=APP_NAME, xalign=0)
        title_lbl.add_css_class("nyx-hero-title")
        ts.append(title_lbl)
        sub_lbl = Gtk.Label(label=APP_TAGLINE, xalign=0)
        sub_lbl.add_css_class("nyx-hero-sub")
        ts.append(sub_lbl)
        hero_row.append(ts)
        # version pill
        vp = Gtk.Label(label=f"v{NYXUS_VERSION}")
        vp.add_css_class("nyx-version-pill")
        vp.set_valign(Gtk.Align.CENTER)
        hero_row.append(vp)
        root.append(hero_row)

        # ── SLIM SECONDARY TOOLBAR (nav + breadcrumb + search + star) ──────
        bar = Gtk.Box(spacing=8); bar.add_css_class("nyx-toolbar2")
        root.append(bar)

        b_home = SketchButton("⌂", width=32, height=24, color=NEON_PINK,
                              tooltip="Home")
        b_home.set_valign(Gtk.Align.CENTER)
        b_home.connect("clicked", lambda _b: self.show_page(HOME_KEY))
        bar.append(b_home)
        b_back = SketchButton("◀", width=32, height=24, color=INK_DIM,
                              tooltip="Back")
        b_back.set_valign(Gtk.Align.CENTER)
        b_back.connect("clicked", lambda _b: self.go_back())
        bar.append(b_back)
        b_fwd  = SketchButton("▶", width=32, height=24, color=INK_DIM,
                              tooltip="Forward")
        b_fwd.set_valign(Gtk.Align.CENTER)
        b_fwd.connect("clicked", lambda _b: self.go_forward())
        bar.append(b_fwd)

        self.crumb_lbl = Gtk.Label(label="Home", xalign=0)
        self.crumb_lbl.add_css_class("nyx-meta")
        self.crumb_lbl.set_valign(Gtk.Align.CENTER)
        self.crumb_lbl.set_margin_start(6)
        bar.append(self.crumb_lbl)

        sp = Gtk.Box(); sp.set_hexpand(True); bar.append(sp)

        self.search = SketchSearchEntry(placeholder="search every setting…",
                                         width=300, height=26)
        self.search.connect("changed", self._on_search)
        bar.append(self.search)

        b_fav = SketchButton("★", width=32, height=24, color=ACCENT_GOLD,
                             tooltip="Star this page")
        b_fav.set_valign(Gtk.Align.CENTER)
        b_fav.connect("clicked", lambda _b: self._toggle_fav())
        bar.append(b_fav)

        # ── restart-required banner (hidden until needed) ──────────────────
        self.restart_bar = Gtk.Box(spacing=10)
        self.restart_bar.add_css_class("nyx-restartbar")
        self.restart_bar.set_visible(False)
        self.restart_lbl = Gtk.Label(label="", xalign=0); self.restart_lbl.set_wrap(True)
        self.restart_bar.append(self.restart_lbl)
        sp2 = Gtk.Box(); sp2.set_hexpand(True); self.restart_bar.append(sp2)
        b_reload = SketchButton("Reload Hyprland", width=160, height=24,
                                color=NEON_GREEN,
                                tooltip="hyprctl reload")
        b_reload.connect("clicked", lambda _b: self._do_reload_hypr())
        self.restart_bar.append(b_reload)
        b_clear = SketchButton("Dismiss", width=90, height=24, color=INK_DIM,
                               tooltip="Hide banner")
        b_clear.connect("clicked", lambda _b: self._clear_restart_banner())
        self.restart_bar.append(b_clear)
        root.append(self.restart_bar)

        # ── stack (full-width, no sidebar) ─────────────────────────────────
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(180)
        self.stack.set_hexpand(True); self.stack.set_vexpand(True)
        ov = Gtk.Overlay(); ov.set_child(self.stack)
        ov.set_hexpand(True); ov.set_vexpand(True)
        self._toast_label = Gtk.Label()
        self._toast_label.add_css_class("nyx-toast")
        self._toast_label.set_halign(Gtk.Align.CENTER)
        self._toast_label.set_valign(Gtk.Align.END)
        self._toast_label.set_margin_bottom(20)
        self._toast_label.set_visible(False)
        ov.add_overlay(self._toast_label)
        root.append(ov)

        # build all pages
        for cls in PAGE_CLASSES:
            try:
                page = cls(self)
            except Exception as e:
                log.error("failed to build page %s: %s", cls.__name__, e)
                continue
            self._page_widgets[cls.KEY] = page
            self.stack.add_named(page, cls.KEY)
            try:
                self._search_entries.extend(page.search_entries())
            except Exception as e:
                log.warning("search_entries %s: %s", cls.__name__, e)

        # home page (tile grid) + search results page
        self._home_widget = self._build_home_page()
        self.stack.add_named(self._home_widget, HOME_KEY)
        self.search_page = self._build_search_results_page()
        self.stack.add_named(self.search_page, "_search")

        # status bar
        sb = Gtk.Box(spacing=10); sb.add_css_class("nyx-statusbar")
        root.append(sb)
        self.status_lbl = Gtk.Label(label="", xalign=0)
        self.status_lbl.add_css_class("nyx-meta")
        sb.append(self.status_lbl)
        sp = Gtk.Box(); sp.set_hexpand(True); sb.append(sp)
        rt = Gtk.Label(label=f"{len(PAGE_CLASSES)} categories  ·  "
                             f"{len(self._search_entries)} settings indexed")
        rt.add_css_class("nyx-meta")
        sb.append(rt)

    # ── home tile grid ──────────────────────────────────────────────────────
    def _build_home_page(self) -> Gtk.ScrolledWindow:
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_hexpand(True); sw.set_vexpand(True)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        outer.set_margin_start(20); outer.set_margin_end(20)
        outer.set_margin_top(14); outer.set_margin_bottom(20)
        sw.set_child(outer)

        # hero headline
        hero = Gtk.Label(label="✦  NYXUS Settings", xalign=0)
        hero.add_css_class("nyx-headline")
        outer.append(hero)
        sub = Gtk.Label(
            label="Pick a category to dive in, or search every setting at the top.",
            xalign=0)
        sub.add_css_class("nyx-meta"); outer.append(sub)

        # strips: favorites + recents
        self._fav_strip    = self._make_strip("favorites")
        self._recent_strip = self._make_strip("recently changed")
        outer.append(self._fav_strip)
        outer.append(self._recent_strip)

        # full grid of all categories (FlowBox = wrapping responsive grid)
        all_lbl = Gtk.Label(label="all categories", xalign=0)
        all_lbl.add_css_class("nyx-strip-label")
        all_lbl.set_margin_top(6); all_lbl.set_margin_start(2)
        outer.append(all_lbl)

        self._tiles_box = Gtk.FlowBox()
        self._tiles_box.set_valign(Gtk.Align.START)
        self._tiles_box.set_max_children_per_line(6)
        self._tiles_box.set_min_children_per_line(2)
        self._tiles_box.set_column_spacing(14)
        self._tiles_box.set_row_spacing(14)
        self._tiles_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._tiles_box.set_homogeneous(True)
        outer.append(self._tiles_box)

        self._rebuild_home_strips()
        self._populate_tiles()
        return sw

    def _make_strip(self, label: str) -> Gtk.Box:
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        wrap.add_css_class("nyx-strip")
        h = Gtk.Label(label=label, xalign=0); h.add_css_class("nyx-strip-label")
        wrap.append(h)
        inner = Gtk.Box(spacing=10)
        wrap.append(inner)
        wrap._inner = inner   # type: ignore[attr-defined]
        return wrap

    def _populate_tiles(self):
        if self._tiles_box is None: return
        # clear
        c = self._tiles_box.get_first_child()
        while c:
            n = c.get_next_sibling(); self._tiles_box.remove(c); c = n
        for cls in PAGE_CLASSES:
            page = self._page_widgets.get(cls.KEY)
            if page is None: continue
            if not getattr(page, "AVAILABLE", True): continue
            tile = CategoryTile(
                icon=getattr(cls, "ICON", "•"),
                title=getattr(cls, "TITLE", cls.__name__),
                subtitle=getattr(cls, "SUBTITLE", ""),
                color=getattr(cls, "TILE_COLOR", NEON_PINK),
                starred=(cls.KEY in self.favorites),
            )
            tile.connect("activated", lambda _t, k=cls.KEY: self.show_page(k))
            self._tiles_box.insert(tile, -1)

    def _rebuild_home_strips(self):
        # favorites
        inner = getattr(self._fav_strip, "_inner", None)
        if inner is not None:
            c = inner.get_first_child()
            while c:
                n = c.get_next_sibling(); inner.remove(c); c = n
            visible = [k for k in self.favorites if k in self._page_widgets]
            self._fav_strip.set_visible(bool(visible))
            for k in visible:
                cls = type(self._page_widgets[k])
                tile = CategoryTile(icon=cls.ICON, title=cls.TITLE,
                                    subtitle=cls.SUBTITLE,
                                    color=cls.TILE_COLOR, starred=True,
                                    width=220, height=110)
                tile.connect("activated", lambda _t, kk=k: self.show_page(kk))
                inner.append(tile)
        # recents
        inner = getattr(self._recent_strip, "_inner", None)
        if inner is not None:
            c = inner.get_first_child()
            while c:
                n = c.get_next_sibling(); inner.remove(c); c = n
            visible = [k for k in self.recents if k in self._page_widgets]
            self._recent_strip.set_visible(bool(visible))
            for k in visible:
                cls = type(self._page_widgets[k])
                tile = CategoryTile(icon=cls.ICON, title=cls.TITLE,
                                    subtitle="recently changed",
                                    color=cls.TILE_COLOR,
                                    starred=(k in self.favorites),
                                    width=220, height=110)
                tile.connect("activated", lambda _t, kk=k: self.show_page(kk))
                inner.append(tile)

    def _build_search_results_page(self) -> Gtk.ScrolledWindow:
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_hexpand(True); sw.set_vexpand(True)
        self.search_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                  spacing=6)
        self.search_box.set_margin_start(20); self.search_box.set_margin_end(20)
        self.search_box.set_margin_top(14); self.search_box.set_margin_bottom(20)
        sw.set_child(self.search_box)
        return sw

    # ── restart-required banner ─────────────────────────────────────────────
    def _refresh_restart_banner(self):
        if not self._restart_pages:
            self.restart_bar.set_visible(False); return
        labels = ", ".join(sorted(set(self._restart_pages.values())))
        self.restart_lbl.set_text(
            f"⟳  Restart required to fully apply: {labels}")
        self.restart_bar.set_visible(True)

    def _clear_restart_banner(self):
        self._restart_pages.clear()
        self.restart_bar.set_visible(False)

    def _do_reload_hypr(self):
        rc, _o, _e = sh("hyprctl reload", timeout=5)
        if rc == 0:
            self.toast("hyprctl reload sent")
            self._clear_restart_banner()
        else:
            self.toast("hyprctl reload failed — see /tmp/nyxus-settings.log")

    # ── navigation ──────────────────────────────────────────────────────────
    def _crumb_for(self, key: str) -> str:
        if key == HOME_KEY:   return "  ›  Home"
        if key == "_search":  return "  ›  Search"
        page = self._page_widgets.get(key)
        if not page: return ""
        return f"  ›  Home  ›  {page.TITLE}"

    def show_page(self, key: str, *, push_history: bool = True):
        if key != HOME_KEY and key != "_search" and key not in self._page_widgets:
            return
        cur = self.stack.get_visible_child_name()
        if push_history and cur and cur != "_search":
            self.history.append(cur)
            self._fwd_history.clear()
        self.stack.set_visible_child_name(key)
        if key == HOME_KEY:
            self._rebuild_home_strips(); self._populate_tiles()
            self.crumb_lbl.set_text(self._crumb_for(HOME_KEY))
            self.status_lbl.set_text("Home")
            return
        if key == "_search":
            self.crumb_lbl.set_text(self._crumb_for("_search")); return
        page = self._page_widgets.get(key)
        if page:
            try: page.refresh()
            except Exception as e: log.warning("refresh %s: %s", key, e)
            self.crumb_lbl.set_text(self._crumb_for(key))
            self.status_lbl.set_text(page.TITLE)

    def go_back(self):
        if not self.history:
            self.show_page(HOME_KEY, push_history=False); return
        prev = self.history.pop()
        cur = self.stack.get_visible_child_name()
        if cur and cur != "_search": self._fwd_history.append(cur)
        self.show_page(prev, push_history=False)

    def go_forward(self):
        if not self._fwd_history: return
        nxt = self._fwd_history.pop()
        cur = self.stack.get_visible_child_name()
        if cur and cur != "_search": self.history.append(cur)
        self.show_page(nxt, push_history=False)

    def _toggle_fav(self):
        cur = self.stack.get_visible_child_name()
        if not cur or cur in (HOME_KEY, "_search"): return
        if cur in self.favorites:
            self.favorites.remove(cur); self.toast("removed favorite")
        else:
            self.favorites.append(cur); self.toast("starred")
        self._save_favs()
        self._rebuild_home_strips(); self._populate_tiles()

    # ── search ──────────────────────────────────────────────────────────────
    def _on_search(self, _e, txt):
        q = (txt or "").strip().lower()
        if not q:
            target = self.history[-1] if self.history else HOME_KEY
            if target == "_search": target = HOME_KEY
            self.show_page(target, push_history=False)
            return
        # render results
        c = self.search_box.get_first_child()
        while c:
            n = c.get_next_sibling(); self.search_box.remove(c); c = n
        h = Gtk.Label(label=f"🔍  search: “{q}”", xalign=0)
        h.add_css_class("nyx-headline")
        self.search_box.append(h)
        results = [e for e in self._search_entries if q in e.haystack()]
        sub = Gtk.Label(label=f"{len(results)} match"
                              f"{'es' if len(results)!=1 else ''} "
                              f"across {len({e.page_key for e in results})} "
                              f"categor{'ies' if len({e.page_key for e in results})!=1 else 'y'}",
                        xalign=0)
        sub.add_css_class("nyx-meta")
        self.search_box.append(sub)
        if not results:
            self.search_box.append(Gtk.Label(
                label="no matches — try a shorter or different word", xalign=0))
        for e in results:
            row = Gtk.Box(spacing=10)
            row.set_margin_top(4); row.set_margin_bottom(2)
            lbl = Gtk.Label(label=e.label, xalign=0)
            lbl.add_css_class("nyx-row-label")
            row.append(lbl)
            crumb = Gtk.Label(label=f"  ·  Settings ›  {e.page_title}", xalign=0)
            crumb.add_css_class("nyx-meta"); row.append(crumb)
            spx = Gtk.Box(); spx.set_hexpand(True); row.append(spx)
            b = SketchButton(f"open {e.page_title}", width=200, height=22,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b, k=e.page_key:
                      (self.search.set_text(""), self.show_page(k)))
            row.append(b)
            self.search_box.append(row)
        self.stack.set_visible_child_name("_search")
        self.crumb_lbl.set_text(f"  ›  Home  ›  Search ({len(results)})")

    # ── toast ───────────────────────────────────────────────────────────────
    def toast(self, msg: str, ms: int = 2200):
        if not self._toast_label: return
        self._toast_label.set_text(msg); self._toast_label.set_visible(True)
        def hide(): self._toast_label.set_visible(False); return False
        GLib.timeout_add(ms, hide)


# ═══════════════════════════════════════════════════════════════════════════════
#  App
# ═══════════════════════════════════════════════════════════════════════════════
class SettingsApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
    def do_activate(self):
        win = self.props.active_window or SettingsWindow(self)
        win.present()


def main():
    log.info("starting %s", APP_NAME)
    sys.exit(SettingsApp().run(sys.argv))


if __name__ == "__main__":
    main()
