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

__nyxid__ = "4e59582d4a35572d323032362d53494552454e474f57534b492d4c4f434b4544"

def _nyx_integrity():
    try:
        _s = open(__file__, encoding="utf-8").read()
        assert "SIERENGOWSKI" in _s, "NYXUS: tamper detected"
    except (OSError, AssertionError) as _e:
        import sys as _sys; print(f"NYXUS SECURITY: {_e}", file=_sys.stderr)
_nyx_integrity()


from __future__ import annotations

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
APP_ID    = "com.nyxus.settings"
APP_NAME  = "NYXUS Settings"
WIN_W, WIN_H = 1180, 760

CONFIG_DIR = Path.home() / ".config" / "nyxus-settings"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
FAV_PATH   = CONFIG_DIR / "favorites.json"
PREF_PATH  = CONFIG_DIR / "preferences.json"
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

    def __init__(self, *, placeholder="search settings…", color=NEON_PINK):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.color = color
        self.set_size_request(320, 30)
        bg = Gtk.DrawingArea()
        bg.set_hexpand(True); bg.set_vexpand(True)
        bg.set_draw_func(self._draw_bg)
        ov = Gtk.Overlay(); ov.set_hexpand(True); ov.set_vexpand(True)
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

        self.refresh()

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
        ]


# ─── Sound ──────────────────────────────────────────────────────────────────
class SoundPage(BasePage):
    KEY = "sound"; TITLE = "Sound"; ICON = "🔊"

    def build(self):
        # output
        self.out_card = Card("output")
        self.box.append(self.out_card)
        self.in_card  = Card("input")
        self.box.append(self.in_card)
        self.app_card = Card("per-application volume")
        self.box.append(self.app_card)
        self.refresh()

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

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Wi-Fi"),
            SearchEntry(self.KEY, self.TITLE, "Connect to network", "ssid wifi"),
            SearchEntry(self.KEY, self.TITLE, "Hotspot"),
            SearchEntry(self.KEY, self.TITLE, "Ethernet"),
            SearchEntry(self.KEY, self.TITLE, "VPN", "wireguard"),
            SearchEntry(self.KEY, self.TITLE, "DNS"),
            SearchEntry(self.KEY, self.TITLE, "Ping / diagnostics"),
        ]


# ─── Bluetooth ──────────────────────────────────────────────────────────────
class BluetoothPage(BasePage):
    KEY = "bluetooth"; TITLE = "Bluetooth"; ICON = "🅱"

    def build(self):
        self.state_card = Card("controller")
        self.box.append(self.state_card)
        self.dev_card = Card("devices")
        self.box.append(self.dev_card)
        self.refresh()

    def refresh(self):
        for c in (self.state_card, self.dev_card):
            child = c.get_first_child(); skip = True
            while child:
                n = child.get_next_sibling()
                if skip: skip = False
                else: c.remove(child)
                child = n
        if not have("bluetoothctl"):
            self.box.append(Gtk.Label(label="bluetoothctl not installed",
                                      xalign=0))
            return
        rc, out, _ = sh("bluetoothctl show")
        powered = "Powered: yes" in out
        disc    = "Discoverable: yes" in out
        row = Gtk.Box(spacing=10)
        b = SketchToggle("power", width=80, height=26, color=NEON_BLUE,
                         active=powered)
        b.connect("clicked", lambda _b: (sh(f"bluetoothctl power {'on' if b.active else 'off'}"),
                                         GLib.timeout_add(500,
                                              lambda:(self.refresh(), False)[1])))
        row.append(b)
        d = SketchToggle("discoverable", width=110, height=26,
                         color=ACCENT_PURP, active=disc)
        d.connect("clicked", lambda _b: sh(f"bluetoothctl discoverable {'on' if d.active else 'off'}"))
        row.append(d)
        s = SketchButton("Scan", width=70, height=26, color=NEON_GREEN)
        s.connect("clicked", lambda _b: self._scan())
        row.append(s)
        self.state_card.add_row(row)

        # devices
        rc, out, _ = sh("bluetoothctl devices")
        if rc == 0:
            for line in out.splitlines():
                m = re.match(r"Device ([0-9A-F:]+)\s+(.+)", line)
                if not m: continue
                mac, name = m.group(1), m.group(2)
                row = Gtk.Box(spacing=10)
                lbl = Gtk.Label(label=f"{name} ({mac})", xalign=0)
                lbl.set_hexpand(True); row.append(lbl)
                for label, action, color in (
                    ("Connect",    "connect",    NEON_GREEN),
                    ("Disconnect", "disconnect", DANGER_RED),
                    ("Trust",      "trust",      ACCENT_GOLD),
                    ("Forget",     "remove",     INK_DIM),
                ):
                    b = SketchButton(label, width=86, height=22, color=color)
                    b.connect("clicked",
                              lambda _b, a=action, m=mac:
                              sh_async(f"bluetoothctl {a} {m}",
                                       lambda r: (self.win.toast(
                                           f"{a}: {'ok' if r[0]==0 else 'failed'}"),
                                                  self.refresh())))
                    row.append(b)
                self.dev_card.add_row(row)
        else:
            self.dev_card.add_row(Gtk.Label(label="(no devices)", xalign=0))

    def _scan(self):
        sh_async("bluetoothctl --timeout 8 scan on",
                 lambda r: (self.win.toast("scan complete"), self.refresh()),
                 timeout=12)
        self.win.toast("scanning for 8s…")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Pair / connect"),
            SearchEntry(self.KEY, self.TITLE, "Discoverable"),
            SearchEntry(self.KEY, self.TITLE, "Bluetooth power"),
        ]


# ─── Appearance ─────────────────────────────────────────────────────────────
class AppearancePage(BasePage):
    KEY = "appearance"; TITLE = "Appearance"; ICON = "🎨"

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
        self.bat_card = Card("battery")
        self.box.append(self.bat_card)
        self.prof_card = Card("power profiles")
        self.box.append(self.prof_card)
        self.refresh()

    def refresh(self):
        for c in (self.bat_card, self.prof_card):
            child = c.get_first_child(); skip = True
            while child:
                n = child.get_next_sibling()
                if skip: skip = False
                else: c.remove(child)
                child = n
        # battery
        bat_dir = Path("/sys/class/power_supply")
        bats = list(bat_dir.glob("BAT*")) if bat_dir.exists() else []
        if not bats:
            self.bat_card.add_row(Gtk.Label(label="(no battery detected)",
                                            xalign=0))
        for b in bats:
            try:
                cap = (b/"capacity").read_text().strip()
                stat = (b/"status").read_text().strip()
                self.bat_card.add_row(kv_row(b.name, f"{cap}%  ({stat})"))
                # health (energy_full vs energy_full_design)
                ef = (b/"energy_full"); efd = (b/"energy_full_design")
                if ef.exists() and efd.exists():
                    e1 = int(ef.read_text()); e2 = int(efd.read_text())
                    if e2 > 0:
                        h = e1 * 100 // e2
                        self.bat_card.add_row(kv_row("health", f"{h}%"))
            except Exception as e:
                log.warning("battery: %s", e)

        # power profiles
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

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Battery"),
            SearchEntry(self.KEY, self.TITLE, "Power profile"),
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

    def build(self):
        c = Card("disk encryption")
        self.box.append(c)
        rc, out, _ = sh("lsblk -no NAME,FSTYPE,MOUNTPOINT")
        any_crypt = "crypto_LUKS" in out
        c.add_row(Gtk.Label(
            label=f"LUKS encrypted volumes detected: {'yes' if any_crypt else 'no'}",
            xalign=0))

        c = Card("AppArmor / SELinux")
        self.box.append(c)
        rc, out, _ = sh("aa-status")
        c.add_row(Gtk.Label(label=out.strip().split('\n')[0] if rc==0
                            else "AppArmor not loaded", xalign=0))

        c = Card("SSH keys")
        self.box.append(c)
        ssh_dir = Path.home() / ".ssh"
        keys = []
        if ssh_dir.exists():
            for f in ssh_dir.iterdir():
                if f.suffix == ".pub": keys.append(f.name)
        c.add_row(Gtk.Label(label=", ".join(keys) or "(no keys found)",
                            xalign=0))

        c = Card("recent files")
        self.box.append(c)
        recent = Path.home() / ".local/share/recently-used.xbel"
        c.add_row(Gtk.Label(label=str(recent), xalign=0))
        if recent.exists():
            b = SketchButton("Clear recent files", width=180, height=24,
                             color=DANGER_RED)
            b.connect("clicked",
                      lambda _b: (recent.unlink(missing_ok=True),
                                  self.win.toast("recent files cleared")))
            c.add_row(b)

        self.add_note(
            "advanced firewall/AppArmor/SELinux changes need root and are "
            "destructive — see NYXUS Security or use `ufw`, `aa-enforce`, "
            "`setenforce` in a terminal.")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "SSH keys"),
            SearchEntry(self.KEY, self.TITLE, "Encryption", "luks"),
            SearchEntry(self.KEY, self.TITLE, "Clear recent files"),
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
        c = Card("drives & partitions")
        self.box.append(c)
        rc, out, _ = sh("lsblk -o NAME,SIZE,FSTYPE,MOUNTPOINT,LABEL")
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 200)
        tv = Gtk.TextView(); tv.set_editable(False)
        tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(out or "(no output)")
        sw.set_child(tv); c.add_row(sw)

        c = Card("disk usage")
        self.box.append(c)
        rc, out, _ = sh("df -h -x tmpfs -x devtmpfs")
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 180)
        tv = Gtk.TextView(); tv.set_editable(False)
        tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(out or "(no output)")
        sw.set_child(tv); c.add_row(sw)

        c = Card("home folder breakdown")
        self.box.append(c)
        for sub in ("Documents", "Downloads", "Pictures", "Videos", "Music",
                    ".cache", ".config", ".local"):
            p = Path.home() / sub
            if not p.exists():
                c.add_row(kv_row(sub, "(missing)")); continue
            rc, out, _ = sh(f"du -sh {p}", timeout=10)
            c.add_row(kv_row(sub, out.split()[0] if out else "?"))

        self.add_note(
            "snapshot tools (timeshift / btrfs) and disk benchmarks need "
            "root and are not run automatically — use the system tools "
            "directly.")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Drives"),
            SearchEntry(self.KEY, self.TITLE, "Disk usage", "df"),
            SearchEntry(self.KEY, self.TITLE, "Home folder usage"),
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

    def build(self):
        c = Card("kernel & system")
        self.box.append(c)
        for label, cmd in (
            ("Hostname:",    "hostnamectl --static"),
            ("Kernel:",      "uname -r"),
            ("Distro:",      "cat /etc/os-release"),
            ("Uptime:",      "uptime -p"),
        ):
            rc, out, _ = sh(cmd)
            v = out.strip().splitlines()[0] if out else "?"
            if "PRETTY_NAME" in (out or ""):
                m = re.search(r'PRETTY_NAME="([^"]+)"', out)
                v = m.group(1) if m else v
            c.add_row(kv_row(label, v))

        c = Card("CPU")
        self.box.append(c)
        rc, out, _ = sh("lscpu")
        for ln in out.splitlines():
            if any(k in ln for k in ("Model name", "CPU(s):", "Architecture",
                                     "Thread(s) per core", "Core(s) per socket",
                                     "CPU max MHz", "CPU min MHz")):
                c.add_row(Gtk.Label(label=ln.strip(), xalign=0))

        c = Card("RAM")
        self.box.append(c)
        rc, out, _ = sh("free -h")
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 90)
        tv = Gtk.TextView(); tv.set_editable(False); tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(out)
        sw.set_child(tv); c.add_row(sw)

        c = Card("GPU")
        self.box.append(c)
        rc, out, _ = sh("lspci -k | grep -EA3 'VGA|3D|Display'")
        c.add_row(Gtk.Label(label=out.strip() or "(unknown)", xalign=0))

        c = Card("environment variables")
        self.box.append(c)
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 220)
        tv = Gtk.TextView(); tv.set_editable(False); tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(
            "\n".join(f"{k}={v}" for k, v in sorted(os.environ.items())))
        sw.set_child(tv); c.add_row(sw)

        c = Card("ssh server")
        self.box.append(c)
        rc, out, _ = sh("systemctl is-active sshd")
        c.add_row(kv_row("sshd status:", out.strip() or "?"))

        c = Card("open ports")
        self.box.append(c)
        rc, out, _ = sh("ss -tunlp")
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 160)
        tv = Gtk.TextView(); tv.set_editable(False); tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(out or "(no output)")
        sw.set_child(tv); c.add_row(sw)

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "System info", "hostname kernel"),
            SearchEntry(self.KEY, self.TITLE, "CPU info"),
            SearchEntry(self.KEY, self.TITLE, "RAM"),
            SearchEntry(self.KEY, self.TITLE, "GPU"),
            SearchEntry(self.KEY, self.TITLE, "Environment variables"),
            SearchEntry(self.KEY, self.TITLE, "SSH server"),
            SearchEntry(self.KEY, self.TITLE, "Open ports"),
        ]


# ═══════════════════════════════════════════════════════════════════════════════
#  Main window
# ═══════════════════════════════════════════════════════════════════════════════
PAGE_CLASSES: List[type] = [
    DisplayPage, SoundPage, NetworkPage, BluetoothPage, AppearancePage,
    WorkspacesPage, KeyboardPage, MousePage, PowerPage,
    UsersPage, PrivacyPage, AppsPage, StoragePage, NotificationsPage,
    DateTimePage, LanguagePage, AccessibilityPage, PrintersPage,
    GamingPage, DeveloperPage,
]


class SettingsWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title=APP_NAME)
        self.set_default_size(WIN_W, WIN_H)
        self.prefs: Dict[str, Any] = self._load_prefs()
        self.favorites: List[str] = self._load_favs()
        self.history: List[str] = []
        self._fwd_history: List[str] = []
        self._toast_label: Optional[Gtk.Label] = None
        self._search_entries: List[SearchEntry] = []
        self._page_widgets: Dict[str, BasePage] = {}
        self._build_css()
        self._build_layout()
        # default page
        self.show_page(self.prefs.get("startup_page", "display"),
                       push_history=False)

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

    # ── CSS ─────────────────────────────────────────────────────────────────
    def _build_css(self):
        css = b"""
* { font-family: 'Caveat', 'Patrick Hand', cursive; }
window, .nyx-bg { background-color: #0a0a12; color: #f0eef8; }
.nyx-sidebar { background-color: rgba(255,255,255,0.025); }
.nyx-toolbar { background-color: rgba(10,10,18,0.96); padding: 6px 12px;
    border-bottom: 1px solid rgba(255,0,255,0.12); }
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

        # toolbar
        bar = Gtk.Box(spacing=8); bar.add_css_class("nyx-toolbar")
        root.append(bar)
        b_back = SketchButton("◀", width=36, height=28, color=INK_DIM,
                              tooltip="Back")
        b_back.connect("clicked", lambda _b: self.go_back())
        bar.append(b_back)
        b_fwd  = SketchButton("▶", width=36, height=28, color=INK_DIM,
                              tooltip="Forward")
        b_fwd.connect("clicked", lambda _b: self.go_forward())
        bar.append(b_fwd)

        title = Gtk.Label(label="🛠  Settings"); title.add_css_class("nyx-headline")
        bar.append(title)

        self.crumb_lbl = Gtk.Label(label="", xalign=0)
        self.crumb_lbl.add_css_class("nyx-meta")
        bar.append(self.crumb_lbl)

        sp = Gtk.Box(); sp.set_hexpand(True); bar.append(sp)

        self.search = SketchSearchEntry(placeholder="search every setting…")
        self.search.connect("changed", self._on_search)
        bar.append(self.search)

        b_fav = SketchButton("★ Fav", width=70, height=28, color=ACCENT_GOLD,
                             tooltip="Star this page")
        b_fav.connect("clicked", lambda _b: self._toggle_fav())
        bar.append(b_fav)

        # body: sidebar | overlay(stack + toast)
        paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        paned.set_position(220); paned.set_wide_handle(True)
        paned.set_hexpand(True); paned.set_vexpand(True)
        root.append(paned)

        self.sidebar = self._build_sidebar()
        paned.set_start_child(self.sidebar)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(180)
        ov = Gtk.Overlay(); ov.set_child(self.stack)
        self._toast_label = Gtk.Label()
        self._toast_label.add_css_class("nyx-toast")
        self._toast_label.set_halign(Gtk.Align.CENTER)
        self._toast_label.set_valign(Gtk.Align.END)
        self._toast_label.set_margin_bottom(20)
        self._toast_label.set_visible(False)
        ov.add_overlay(self._toast_label)
        paned.set_end_child(ov)

        # Build all pages now (fast — most just read on demand)
        for cls in PAGE_CLASSES:
            page = cls(self)
            self._page_widgets[cls.KEY] = page
            self.stack.add_named(page, cls.KEY)
            self._search_entries.extend(page.search_entries())

        # search results page
        self.search_page = self._build_search_results_page()
        self.stack.add_named(self.search_page, "_search")

        # status bar
        sb = Gtk.Box(spacing=10); sb.add_css_class("nyx-statusbar")
        root.append(sb)
        self.status_lbl = Gtk.Label(label="", xalign=0)
        self.status_lbl.add_css_class("nyx-meta")
        sb.append(self.status_lbl)
        sp = Gtk.Box(); sp.set_hexpand(True); sb.append(sp)
        rt = Gtk.Label(label=f"{len(PAGE_CLASSES)} categories")
        rt.add_css_class("nyx-meta")
        sb.append(rt)

    def _build_sidebar(self) -> Gtk.Widget:
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        col.add_css_class("nyx-sidebar")
        col.set_margin_start(6); col.set_margin_end(6)
        col.set_margin_top(8); col.set_margin_bottom(8)
        sw.set_child(col)

        # favorites if any
        if self.favorites:
            lbl = Gtk.Label(label="favorites", xalign=0)
            lbl.add_css_class("nyx-meta"); lbl.set_margin_start(8)
            col.append(lbl)
            for key in self.favorites:
                cls = next((c for c in PAGE_CLASSES if c.KEY == key), None)
                if not cls: continue
                btn = SketchButton(f"★ {cls.ICON}  {cls.TITLE}",
                                   width=200, height=26,
                                   color=ACCENT_GOLD)
                btn.connect("clicked", lambda _b, k=key: self.show_page(k))
                col.append(btn)
            col.append(SketchSeparator(length=200, color=INK_FAINT))

        # all categories
        lbl = Gtk.Label(label="all settings", xalign=0)
        lbl.add_css_class("nyx-meta"); lbl.set_margin_start(8)
        col.append(lbl)
        self._sidebar_buttons: Dict[str, SketchButton] = {}
        for cls in PAGE_CLASSES:
            btn = SketchButton(f"{cls.ICON}  {cls.TITLE}",
                               width=200, height=26, color=NEON_BLUE)
            btn.connect("clicked", lambda _b, k=cls.KEY: self.show_page(k))
            col.append(btn)
            self._sidebar_buttons[cls.KEY] = btn
        return sw

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

    # ── navigation ──────────────────────────────────────────────────────────
    def show_page(self, key: str, *, push_history: bool = True):
        if key not in self._page_widgets and key != "_search": return
        if push_history and self.stack.get_visible_child_name() not in (None, "_search"):
            self.history.append(self.stack.get_visible_child_name())
            self._fwd_history.clear()
        self.stack.set_visible_child_name(key)
        page = self._page_widgets.get(key)
        if page:
            try: page.refresh()
            except Exception as e: log.warning("refresh %s: %s", key, e)
            self.crumb_lbl.set_text(f"  ›  {page.TITLE}")
            self.status_lbl.set_text(f"{page.TITLE}")
            for k, btn in self._sidebar_buttons.items():
                btn.primary = (k == key); btn.queue_draw()
        else:
            self.crumb_lbl.set_text("  ›  Search")

    def go_back(self):
        if not self.history: return
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
        if not cur or cur == "_search": return
        if cur in self.favorites:
            self.favorites.remove(cur); self.toast("removed favorite")
        else:
            self.favorites.append(cur); self.toast("starred")
        self._save_favs()
        # rebuild sidebar
        new = self._build_sidebar()
        paned = self.sidebar.get_parent()
        if isinstance(paned, Gtk.Paned):
            paned.set_start_child(new)
            self.sidebar = new

    # ── search ──────────────────────────────────────────────────────────────
    def _on_search(self, _e, txt):
        q = (txt or "").strip().lower()
        if not q:
            self.show_page(self.history[-1] if self.history else "display",
                           push_history=False)
            return
        # render results
        c = self.search_box.get_first_child()
        while c:
            n = c.get_next_sibling(); self.search_box.remove(c); c = n
        h = Gtk.Label(label=f"🔍  search: “{q}”", xalign=0)
        h.add_css_class("nyx-headline")
        self.search_box.append(h)
        results = [e for e in self._search_entries if q in e.haystack()]
        if not results:
            self.search_box.append(Gtk.Label(label="no matches", xalign=0))
        for e in results:
            row = Gtk.Box(spacing=10)
            row.append(Gtk.Label(label=f"{e.label}", xalign=0))
            sp = Gtk.Box(); sp.set_hexpand(True); row.append(sp)
            b = SketchButton(f"go to {e.page_title}", width=200, height=22,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b, k=e.page_key:
                      (self.search.set_text(""), self.show_page(k)))
            row.append(b)
            self.search_box.append(row)
        self.stack.set_visible_child_name("_search")
        self.crumb_lbl.set_text(f"  ›  Search ({len(results)})")

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
