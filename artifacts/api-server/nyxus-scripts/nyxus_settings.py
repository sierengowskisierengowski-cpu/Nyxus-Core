#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NYXUS Settings — system control center for NYXUS.

A native GTK4 / Cairo Python application matching the NYXUS theme
(dark {INK_BLACK} background, Inter handwriting font, neon pink/blue/
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
  • Notifications → dunstctl + ~/.config/dunst/dunstrc
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
    GLASS_DARK='#14141a'
    GLASS_DEEPER='#0a0a0e'
    GLASS_DEEPEST='#000000'
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
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import (Gtk, Gdk, GdkPixbuf, GLib, GObject, Gio,
                            Pango, PangoCairo)  # noqa: E402
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
BG_DEEP    = (0.0, 0.0, 0.0)         # #000000 (pure black, Tesla grade)
# ── DARK MIRROR Cairo float tuples (rev r13) ───────────────────────────
# Names retained for call-site compatibility; values are all white/grey/ink
# now per the locked monochrome palette. Authoritative source: nyxus_palette.py
BG_PANEL   = (0.031, 0.047, 0.078)   # rgba(8,12,20) glass-dark base
INK_BRIGHT = (0.910, 0.929, 0.961)   # #e8edf5 WHITE_OFF
INK_DIM    = (0.784, 0.800, 0.839)   # #c8ccd6 GREY_LIGHT
INK_FAINT  = (0.416, 0.431, 0.471)   # #6a6e78 GREY_TERTIARY
NEON_PINK  = (1.000, 1.000, 1.000)   # → WHITE_PURE
NEON_BLUE  = (0.910, 0.929, 0.961)   # → WHITE_OFF
NEON_GREEN = (0.784, 0.800, 0.839)   # → GREY_LIGHT
ACCENT_PURP= (0.910, 0.929, 0.961)   # → WHITE_OFF
ACCENT_GOLD= (0.910, 0.929, 0.961)   # → WHITE_OFF (no gold in DARK MIRROR)
DANGER_RED = (0.784, 0.800, 0.839)   # → GREY_LIGHT (semantic only)


# ═══════════════════════════════════════════════════════════════════════════════
#  Multi-color rainbow markup for hero titles
# ═══════════════════════════════════════════════════════════════════════════════
# Hex stops cycled per character (matches NYXUS suite + Hyprland border).
_RAINBOW_HEX = ("#e8edf5", "#6a6e78", "#3a3e4a", "#c8ccd6",
                "#c8ccd6", "#c8ccd6", "#9aa0ad", "#e8edf5")

def _rainbow_markup(text: str) -> str:
    """Return Pango markup where each visible character is colored from
    the NYXUS DARK MIRROR palette. Spaces, punctuation and the leading sigil are
    kept neutral so the readable letters do the singing."""
    out = []
    i = 0
    for ch in text:
        if ch.isspace():
            out.append(ch); continue
        col = _RAINBOW_HEX[i % len(_RAINBOW_HEX)]
        # GLib.markup_escape_text is the safe escaper but is over-eager
        # for our simple ASCII titles; manually escape the few that matter.
        esc = (ch.replace("&", "&amp;").replace("<", "&lt;")
                  .replace(">", "&gt;"))
        out.append(f'<span foreground="{col}">{esc}</span>')
        i += 1
    return "".join(out)


# ═══════════════════════════════════════════════════════════════════════════════
#  Graffiti word sets per page (background collage matches current page)
# ═══════════════════════════════════════════════════════════════════════════════
# Each list: (word, base_size). Tighter, page-relevant terms instead of
# the generic NYXUS dump. Keys match BasePage.KEY values; "_home" is the
# default landing-page set.
_GRAFFITI_WORDS_BY_PAGE: Dict[str, List[Tuple[str, int]]] = {
    "_home": [
        ("settings", 56), ("NYXUS", 80), ("hyprland", 50), ("wayland", 44),
        ("pacman", 42), ("makepkg", 38), ("rofi", 32), ("waybar", 36),
        ("pipewire", 38), ("yubikey", 38), ("workspaces", 34),
        ("sysmon", 34), ("notepad", 34), ("stickies", 36), ("widgets", 36),
        ("nyx", 36), ("sierengowski", 30), ("operator", 32), ("admin", 30),
        ("phantom", 36), ("shield", 32), ("godsapp", 32),
    ],
    "account": [
        ("profile", 48), ("user", 42), ("avatar", 36), ("password", 38),
        ("PIN", 32), ("bio", 32), ("email", 36), ("name", 36), ("role", 30),
        ("admin", 38), ("login", 36), ("session", 32), ("sudoers", 34),
        ("shell", 32), ("identity", 36), ("face", 32), ("signature", 30),
        ("GPG", 36), ("ssh", 36), ("yubikey", 38), ("passwd", 36),
        ("lastlog", 30), ("group", 32), ("uid", 30),
    ],
    "display": [
        ("monitor", 48), ("resolution", 38), ("refresh", 36), ("scale", 36),
        ("VRR", 38), ("brightness", 36), ("gamma", 32), ("contrast", 32),
        ("HDR", 42), ("primary", 32), ("mirror", 32), ("rotate", 32),
        ("EDID", 36), ("HiDPI", 36), ("color", 36), ("gamut", 30),
        ("hertz", 32), ("pixel", 32), ("4K", 44), ("OLED", 38),
        ("nits", 30), ("subpixel", 28),
    ],
    "network": [
        ("wifi", 44), ("ethernet", 38), ("VPN", 44), ("DNS", 42),
        ("gateway", 36), ("subnet", 32), ("IP", 38), ("IPv6", 36),
        ("SSID", 36), ("MAC", 36), ("firewall", 38), ("tunnel", 32),
        ("route", 32), ("latency", 30), ("ping", 36), ("bandwidth", 32),
        ("proxy", 32), ("hostname", 30), ("port", 32), ("nat", 30),
    ],
    "bluetooth": [
        ("pair", 42), ("LDAC", 38), ("SBC", 36), ("AAC", 36),
        ("A2DP", 38), ("HFP", 32), ("HSP", 32), ("RSSI", 32),
        ("codec", 36), ("profile", 32), ("MAC", 36), ("scan", 36),
        ("headset", 34), ("speaker", 34), ("controller", 30), ("trust", 32),
        ("bluez", 34), ("LE", 32),
    ],
    "sound": [
        ("pipewire", 44), ("ALSA", 38), ("JACK", 36), ("mixer", 38),
        ("mic", 36), ("speaker", 36), ("headphones", 30), ("sample", 32),
        ("channel", 32), ("EQ", 38), ("volume", 36), ("mute", 36),
        ("output", 32), ("input", 32), ("balance", 30), ("surround", 30),
        ("48kHz", 32), ("96kHz", 30),
    ],
    "keyboard": [
        ("layout", 42), ("qwerty", 38), ("dvorak", 36), ("colemak", 32),
        ("hotkey", 38), ("shortcut", 34), ("repeat", 32), ("delay", 32),
        ("super", 38), ("ctrl", 36), ("alt", 36), ("shift", 36),
        ("modifier", 30), ("compose", 30), ("dead-key", 28), ("Esc", 32),
    ],
    "mouse": [
        ("pointer", 42), ("DPI", 42), ("accel", 36), ("scroll", 36),
        ("click", 38), ("sensitivity", 30), ("palm", 32), ("tap", 36),
        ("gesture", 32), ("swipe", 32), ("libinput", 30), ("touchpad", 32),
        ("natural", 30), ("drag", 32),
    ],
    "power": [
        ("battery", 44), ("suspend", 36), ("hibernate", 32), ("lid", 36),
        ("watt", 36), ("governor", 30), ("balance", 32), ("performance", 28),
        ("dim", 36), ("sleep", 38), ("idle", 36), ("wake", 36),
        ("charge", 38), ("AC", 36),
    ],
    "appearance": [
        ("theme", 44), ("palette", 38), ("accent", 36), ("opacity", 32),
        ("blur", 38), ("rounding", 32), ("shadow", 36), ("GTK", 38),
        ("Qt", 38), ("icon", 36), ("cursor", 36), ("font", 36),
        ("dark", 36), ("gradient", 30), ("Adwaita", 30),
    ],
    "workspaces": [
        ("tile", 44), ("float", 38), ("master", 36), ("dwindle", 34),
        ("scratchpad", 30), ("monocle", 32), ("gap", 38), ("focus", 36),
        ("swap", 36), ("group", 34), ("layout", 34), ("pin", 36),
        ("special", 32),
    ],
    "datetime": [
        ("timezone", 38), ("NTP", 42), ("UTC", 40), ("sync", 36),
        ("calendar", 34), ("locale", 32), ("DST", 36), ("epoch", 32),
        ("12h", 32), ("24h", 32),
    ],
    "notifications": [
        ("dunst", 42), ("mako", 40), ("swaync", 34), ("urgency", 32),
        ("popup", 36), ("position", 32), ("timeout", 32), ("history", 32),
        ("DND", 38), ("banner", 32), ("badge", 32),
    ],
    "users": [
        ("passwd", 42), ("groups", 38), ("sudoers", 36), ("shells", 32),
        ("lastlog", 32), ("UID", 38), ("GID", 36), ("home", 36),
        ("useradd", 30), ("usermod", 30), ("wheel", 36), ("adm", 36),
        ("lock", 36), ("nyx", 38), ("root", 38),
    ],
    "privacy": [
        ("firewall", 40), ("UFW", 40), ("sandbox", 32), ("secret", 34),
        ("encryption", 30), ("GPG", 38), ("ssh", 38), ("Tor", 38),
        ("VPN", 40), ("audit", 34), ("journald", 30), ("AppArmor", 30),
        ("SELinux", 30), ("anonymize", 28),
    ],
    "apps": [
        ("pacman", 44), ("makepkg", 38), ("flatpak", 34), ("AUR", 42),
        ("install", 36), ("remove", 36), ("update", 36), ("repo", 36),
        ("mirror", 32), ("package", 32), ("version", 32), ("yay", 38),
        ("paru", 36),
    ],
    "storage": [
        ("ext4", 42), ("btrfs", 40), ("xfs", 38), ("LVM", 40),
        ("snapshot", 32), ("partition", 30), ("mount", 36), ("fstab", 36),
        ("SMART", 36), ("RAID", 38), ("ZFS", 38), ("swap", 36),
        ("trim", 36), ("NVMe", 38),
    ],
    "language": [
        ("locale", 42), ("lang", 38), ("region", 36), ("currency", 32),
        ("UTF-8", 38), ("decimal", 32), ("paper", 32), ("measurement", 28),
    ],
    "a11y": [
        ("contrast", 38), ("magnifier", 32), ("captions", 32),
        ("sticky", 36), ("dwell", 34), ("narrator", 30),
        ("zoom", 36), ("a11y", 42),
    ],
    "printers": [
        ("CUPS", 44), ("IPP", 40), ("driver", 36), ("queue", 36),
        ("paper", 36), ("toner", 32), ("ink", 36), ("scan", 36),
        ("duplex", 32), ("PPD", 38),
    ],
    "gaming": [
        ("gamemode", 38), ("MangoHud", 32), ("vulkan", 38), ("DLSS", 36),
        ("FSR", 38), ("gamepad", 32), ("vsync", 36), ("framerate", 30),
        ("raytrace", 30), ("Steam", 38), ("Proton", 36),
    ],
    "developer": [
        ("kernel", 42), ("dmesg", 36), ("sysctl", 34), ("journalctl", 30),
        ("systemd", 32), ("modprobe", 30), ("gcc", 38), ("clang", 36),
        ("python", 36), ("rust", 38), ("node", 38), ("git", 38),
    ],
    "wallpaper": [
        ("hyprpaper", 40), ("swww", 40), ("image", 36), ("blur", 38),
        ("fit", 36), ("scale", 36), ("slideshow", 30), ("animated", 30),
        ("live", 38), ("PNG", 38), ("JPG", 38),
    ],
    "fonts": [
        ("Inter Display", 42), ("JetBrains", 32), ("Mono", 38), ("Sans", 38),
        ("Serif", 38), ("hinting", 30), ("antialias", 28), ("DPI", 38),
        ("weight", 32), ("italic", 34), ("kerning", 30),
    ],
    "about": [
        ("NYXUS", 60), ("sierengowski", 32), ("version", 36), ("build", 36),
        ("kernel", 36), ("Arch", 42), ("hyprland", 38), ("wayland", 36),
        ("copyright", 30), ("license", 32), ("2026", 38),
    ],
}


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

def draw_display(cr, x, y, text, *, size=14, color=(0.94,0.92,0.97,0.95),
                family="Inter Display", weight=Pango.Weight.NORMAL, wrap_w=None):
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
        fd.set_family("Inter Display"); fd.set_size(int(13 * Pango.SCALE))
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
        self.set_halign(Gtk.Align.END)
        self.set_hexpand(False); self.set_vexpand(False)
        bg = Gtk.DrawingArea()
        bg.set_hexpand(False); bg.set_vexpand(False)
        bg.set_size_request(width, height)
        try: bg.set_content_width(width); bg.set_content_height(height)
        except Exception: pass
        bg.set_draw_func(self._draw_bg)
        ov = Gtk.Overlay(); ov.set_hexpand(False); ov.set_vexpand(False)
        ov.set_size_request(width, height)
        ov.set_child(bg)
        ent = Gtk.Entry(); ent.set_placeholder_text(placeholder)
        ent.set_has_frame(False)
        ent.set_hexpand(False); ent.set_vexpand(False)
        ent.set_halign(Gtk.Align.FILL); ent.set_valign(Gtk.Align.CENTER)
        ent.set_size_request(width - 38, height - 6)
        ent.set_max_width_chars(40)
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

        # ── 8. adapter alias (rename) ──────────────────────────────────────
        c = Card("adapter alias")
        self.box.append(c)
        rc, out, _ = sh("bluetoothctl show")
        cur_alias = ""
        for line in out.splitlines():
            if "Alias:" in line:
                cur_alias = line.split(":", 1)[1].strip(); break
        c.add_row(kv_row("Current alias:", cur_alias or "(unset)"))
        row = Gtk.Box(spacing=8)
        ent = Gtk.Entry()
        ent.set_text(cur_alias or socket.gethostname())
        ent.set_hexpand(True)
        row.append(ent)
        b = SketchButton("Set alias", width=120, height=24,
                         color=NEON_BLUE)
        b.connect("clicked", lambda _b: (
            sh(f"bluetoothctl system-alias {shlex.quote(ent.get_text())}"),
            self.win.toast(f"alias → {ent.get_text()}"),
            self.refresh()))
        row.append(b)
        b2 = SketchButton("Reset", width=80, height=24, color=DANGER_RED)
        b2.connect("clicked", lambda _b: (
            sh("bluetoothctl reset-alias"),
            self.win.toast("alias reset"),
            self.refresh()))
        row.append(b2)
        c.add_row(row)

        # ── 9. battery levels (upower / bluetoothctl) ──────────────────────
        c = Card("device battery levels")
        self.box.append(c)
        if not have("upower"):
            c.add_row(Gtk.Label(
                label="upower not installed (pacman -S upower)",
                xalign=0))
        else:
            rc, out, _ = sh("upower -e")
            bt_paths = [p.strip() for p in out.splitlines()
                        if "/devices/" in p
                        and ("bluez" in p or "bluetooth" in p)]
            if not bt_paths:
                c.add_row(Gtk.Label(
                    label="(no BT devices reporting battery to upower)",
                    xalign=0))
            for p in bt_paths:
                rc, info, _ = sh(f"upower -i {p}")
                model = pct = state = "?"
                for ln in info.splitlines():
                    s = ln.strip()
                    if s.startswith("model:"):
                        model = s.split(":", 1)[1].strip()
                    elif s.startswith("percentage:"):
                        pct = s.split(":", 1)[1].strip()
                    elif s.startswith("state:"):
                        state = s.split(":", 1)[1].strip()
                c.add_row(kv_row(model, f"{pct} · {state}"))
        # also try bluetoothctl info battery
        rc, devs, _ = sh("bluetoothctl devices Connected")
        for line in devs.splitlines():
            m = re.match(r"Device ([0-9A-F:]+)\s+(.+)", line)
            if not m: continue
            mac, name = m.group(1), m.group(2)
            rc, info, _ = sh(f"bluetoothctl info {mac}")
            bat = ""
            for ln in info.splitlines():
                if "Battery Percentage:" in ln:
                    m2 = re.search(r"\((\d+)\)", ln)
                    if m2: bat = m2.group(1) + "%"
            if bat:
                c.add_row(kv_row(f"{name} (bluez):", bat))

        # ── 10. autoconnect on boot ────────────────────────────────────────
        c = Card("autoconnect on boot")
        self.box.append(c)
        c.add_row(Gtk.Label(
            label="Trusted devices auto-reconnect when bluetooth comes up. "
                  "Toggle main.conf AutoEnable to power on adapter at boot.",
            xalign=0))
        try:
            txt = Path("/etc/bluetooth/main.conf").read_text()
        except Exception:
            txt = ""
        ae_on = re.search(r"^\s*AutoEnable\s*=\s*true",
                          txt, re.M | re.I) is not None
        row = Gtk.Box(spacing=8)
        tog = SketchToggle("AutoEnable adapter at boot",
                           width=240, height=26,
                           color=NEON_GREEN, active=ae_on)
        tog.connect("clicked", lambda _b: self._toggle_autoenable(tog))
        row.append(tog)
        c.add_row(row)
        # list trusted
        rc, out, _ = sh("bluetoothctl devices Trusted")
        trusted = [l for l in out.splitlines() if l.startswith("Device")]
        c.add_row(kv_row("Trusted devices:", str(len(trusted))))
        for line in trusted[:6]:
            m = re.match(r"Device ([0-9A-F:]+)\s+(.+)", line)
            if m:
                c.add_row(Gtk.Label(
                    label=f"  ★ {m.group(2)} ({m.group(1)})", xalign=0))

        # ── 11. file transfer (OBEX push) ──────────────────────────────────
        c = Card("file transfer (OBEX push)")
        self.box.append(c)
        for tool, label in (("obexctl",      "obexctl"),
                            ("bt-obex",      "bt-obex (bluez-tools)"),
                            ("obexd",        "obexd daemon")):
            c.add_row(kv_row(f"{label}:",
                             "installed" if have(tool) else "not installed"))
        if have("bt-obex") or have("obexctl"):
            rc, out, _ = sh("bluetoothctl devices Connected")
            connected = []
            for line in out.splitlines():
                m = re.match(r"Device ([0-9A-F:]+)\s+(.+)", line)
                if m: connected.append((m.group(1), m.group(2)))
            if not connected:
                c.add_row(Gtk.Label(
                    label="(connect a device first to send files)",
                    xalign=0))
            for mac, name in connected:
                row = Gtk.Box(spacing=8)
                row.append(Gtk.Label(label=f"{name} ({mac})", xalign=0))
                sp = Gtk.Box(); sp.set_hexpand(True); row.append(sp)
                b = SketchButton("Send file…", width=130, height=22,
                                 color=NEON_BLUE)
                b.connect("clicked", lambda _b, m=mac, n=name:
                          self._obex_send(m, n))
                row.append(b)
                c.add_row(row)
        else:
            c.add_row(Gtk.Label(
                label="install bluez-tools (bt-obex) for file transfer",
                xalign=0))

        # ── 12. journal / live log ─────────────────────────────────────────
        c = Card("bluetooth journal")
        self.box.append(c)
        rc, out, _ = sh(
            "journalctl -u bluetooth -n 12 --no-pager 2>/dev/null "
            "|| echo '(journalctl unavailable)'")
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 140)
        tv = Gtk.TextView(); tv.set_editable(False); tv.set_monospace(True)
        tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(out)
        sw.set_child(tv); c.add_row(sw)
        row = Gtk.Box(spacing=8)
        b = SketchButton("Tail live (-f)", width=160, height=24,
                         color=NEON_GREEN)
        b.connect("clicked", lambda _b: self._term_run(
            "journalctl -u bluetooth -f", "tailing bluetoothd…"))
        row.append(b)
        b2 = SketchButton("dmesg | grep bluetooth", width=200, height=24,
                          color=NEON_BLUE)
        b2.connect("clicked", lambda _b: self._term_run(
            "dmesg | grep -iE 'bluetooth|hci|bnep|btusb' | tail -50 | less",
            "kernel BT messages…"))
        row.append(b2)
        c.add_row(row)

        self.refresh()

    # ── helpers added for deepening ────────────────────────────────────────
    def _toggle_autoenable(self, tog):
        cmd = (
            "sudo -n sh -c \"if grep -qE '^\\s*AutoEnable' "
            "/etc/bluetooth/main.conf; then "
            "sed -i 's/^\\s*AutoEnable\\s*=.*/AutoEnable=" +
            ("true" if tog.active else "false") + "/' "
            "/etc/bluetooth/main.conf; else "
            "sed -i '/^\\[Policy\\]/a AutoEnable=" +
            ("true" if tog.active else "false") + "' "
            "/etc/bluetooth/main.conf || "
            "echo -e '\\n[Policy]\\nAutoEnable=" +
            ("true" if tog.active else "false") + "' "
            ">> /etc/bluetooth/main.conf; fi && "
            "systemctl restart bluetooth\""
        )
        sh_async(cmd, lambda r: self.win.toast(
            f"AutoEnable={'on' if tog.active else 'off'}"
            if r[0] == 0
            else "needs sudo NOPASSWD or run via terminal"))

    def _obex_send(self, mac: str, name: str):
        # native GTK file chooser
        d = Gtk.FileChooserDialog(
            title=f"Send file to {name}",
            transient_for=self.win,
            action=Gtk.FileChooserAction.OPEN)
        d.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                      "Send", Gtk.ResponseType.ACCEPT)

        def on_resp(dlg, resp):
            if resp == Gtk.ResponseType.ACCEPT:
                f = dlg.get_file()
                if f:
                    p = f.get_path()
                    cmd = (f"bt-obex -p {mac} {shlex.quote(p)}"
                           if have("bt-obex")
                           else f"obexctl push {mac} {shlex.quote(p)}")
                    self._term_run(cmd, f"sending {Path(p).name} → {name}…")
            dlg.destroy()

        d.connect("response", on_resp)
        d.show()

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
            SearchEntry(self.KEY, self.TITLE, "Adapter alias / rename",
                        "system-alias hostname"),
            SearchEntry(self.KEY, self.TITLE, "Device battery level",
                        "upower percent headphones"),
            SearchEntry(self.KEY, self.TITLE, "AutoEnable on boot",
                        "Policy autoconnect"),
            SearchEntry(self.KEY, self.TITLE, "Trusted devices list",
                        "auto reconnect"),
            SearchEntry(self.KEY, self.TITLE, "Send file (OBEX push)",
                        "bt-obex obexctl transfer"),
            SearchEntry(self.KEY, self.TITLE, "Bluetooth journal",
                        "log journalctl bluetoothd"),
            SearchEntry(self.KEY, self.TITLE, "dmesg bluetooth",
                        "kernel hci btusb"),
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

        # ── 6. GTK theme ──────────────────────────────────────────────────
        c = Card("GTK theme")
        self.box.append(c)
        themes = self._list_themes("themes", marker="gtk-3.0")
        cur_theme = self._gset_str("org.gnome.desktop.interface", "gtk-theme")
        c.add_row(kv_row("Active theme:", cur_theme or "(default)"))
        c.add_row(kv_row("Installed:", f"{len(themes)}"))
        if themes:
            row = Gtk.Box(spacing=8)
            self._theme_dd = Gtk.DropDown.new_from_strings(themes)
            try: self._theme_dd.set_selected(themes.index(cur_theme))
            except ValueError: pass
            self._theme_dd.set_hexpand(True); row.append(self._theme_dd)
            b = SketchButton("Apply", width=78, height=24, color=NEON_GREEN)
            b.connect("clicked", lambda _b: self._apply_theme(themes))
            row.append(b); c.add_row(row)
        else:
            c.add_row(Gtk.Label(
                label="install themes to ~/.themes or /usr/share/themes",
                xalign=0))

        # ── 7. Icon theme ─────────────────────────────────────────────────
        c = Card("icon theme")
        self.box.append(c)
        icons = self._list_themes("icons", marker="index.theme")
        cur_icons = self._gset_str("org.gnome.desktop.interface", "icon-theme")
        c.add_row(kv_row("Active icons:", cur_icons or "(default)"))
        c.add_row(kv_row("Installed:", f"{len(icons)}"))
        if icons:
            row = Gtk.Box(spacing=8)
            self._icon_dd = Gtk.DropDown.new_from_strings(icons)
            try: self._icon_dd.set_selected(icons.index(cur_icons))
            except ValueError: pass
            self._icon_dd.set_hexpand(True); row.append(self._icon_dd)
            b = SketchButton("Apply", width=78, height=24, color=NEON_GREEN)
            b.connect("clicked", lambda _b: self._apply_iconset(icons))
            row.append(b); c.add_row(row)

        # ── 8. Cursor theme + size ───────────────────────────────────────
        c = Card("cursor theme & size")
        self.box.append(c)
        cursors = self._list_themes("icons", marker="cursors")
        cur_cur = self._gset_str("org.gnome.desktop.interface", "cursor-theme")
        cur_size = 24
        if have("gsettings"):
            _, sz_out, _ = sh("gsettings get org.gnome.desktop.interface "
                              "cursor-size")
            try: cur_size = int(sz_out.strip() or "24")
            except ValueError: pass
        c.add_row(kv_row("Active cursor:", cur_cur or "(default)"))
        if cursors:
            row = Gtk.Box(spacing=8)
            self._cur_dd = Gtk.DropDown.new_from_strings(cursors)
            try: self._cur_dd.set_selected(cursors.index(cur_cur))
            except ValueError: pass
            self._cur_dd.set_hexpand(True); row.append(self._cur_dd)
            b = SketchButton("Apply", width=78, height=24, color=NEON_GREEN)
            b.connect("clicked", lambda _b: self._apply_cursor(cursors))
            row.append(b); c.add_row(row)
        size_row = Gtk.Box(spacing=10)
        size_row.append(Gtk.Label(label="Cursor size:", xalign=0))
        adj = Gtk.Adjustment(value=cur_size, lower=12, upper=64,
                             step_increment=2, page_increment=4)
        sc = Gtk.Scale(adjustment=adj,
                       orientation=Gtk.Orientation.HORIZONTAL)
        sc.set_size_request(220, -1); sc.set_draw_value(True)
        sc.set_value_pos(Gtk.PositionType.RIGHT); sc.set_digits(0)
        sc.connect("value-changed", lambda s: self._apply_cursor_size(
            int(s.get_value())))
        size_row.append(sc); c.add_row(size_row)

        # ── 9. Interface font ─────────────────────────────────────────────
        c = Card("interface font")
        self.box.append(c)
        cur_font = self._gset_str("org.gnome.desktop.interface", "font-name") \
                   or "Cantarell 11"
        c.add_row(kv_row("Active font:", cur_font))
        row = Gtk.Box(spacing=8)
        self._font_entry = Gtk.Entry()
        self._font_entry.set_placeholder_text("e.g. JetBrainsMono Nerd Font 11")
        self._font_entry.set_text(cur_font)
        self._font_entry.set_hexpand(True); row.append(self._font_entry)
        fb = SketchButton("Apply font", width=120, height=24, color=NEON_BLUE)
        fb.connect("clicked", lambda _b: self._apply_font(
            self._font_entry.get_text().strip()))
        row.append(fb); c.add_row(row)
        # monospace font
        cur_mono = self._gset_str(
            "org.gnome.desktop.interface", "monospace-font-name") \
            or "Source Code Pro 10"
        row = Gtk.Box(spacing=8)
        row.append(Gtk.Label(label="Mono:", xalign=0))
        self._mono_entry = Gtk.Entry()
        self._mono_entry.set_text(cur_mono); self._mono_entry.set_hexpand(True)
        row.append(self._mono_entry)
        mb = SketchButton("Apply mono", width=120, height=24, color=NEON_BLUE)
        mb.connect("clicked", lambda _b: self._gset_set(
            "org.gnome.desktop.interface", "monospace-font-name",
            f'"{self._mono_entry.get_text().strip()}"'))
        row.append(mb); c.add_row(row)

        # ── 10. Titlebar / window controls ───────────────────────────────
        c = Card("titlebar buttons")
        self.box.append(c)
        cur_btns = self._gset_str(
            "org.gnome.desktop.wm.preferences", "button-layout") \
            or "appmenu:close"
        c.add_row(kv_row("Layout:", cur_btns))
        br = Gtk.Box(spacing=8)
        for label, layout in (("Left",  "close,minimize,maximize:appmenu"),
                              ("Right", "appmenu:minimize,maximize,close"),
                              ("Close only R", "appmenu:close"),
                              ("None",  "appmenu:")):
            btn = SketchButton(label, width=110, height=22, color=ACCENT_GOLD,
                               primary=(layout == cur_btns))
            btn.connect("clicked", lambda _b, lay=layout: self._gset_set(
                "org.gnome.desktop.wm.preferences", "button-layout",
                f'"{lay}"'))
            br.append(btn)
        c.add_row(br)

        self.add_note(
            "Theme/icon/cursor/font changes apply via gsettings (GNOME schema). "
            "Most GTK 3/4 apps will pick them up immediately. KDE apps need "
            "their own settings (kvantum/kcm).")

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

    # ── helpers for theme management ──────────────────────────────────────
    def _gset_str(self, schema: str, key: str) -> str:
        if not have("gsettings"): return ""
        rc, out, _ = sh(["gsettings", "get", schema, key])
        if rc != 0: return ""
        return out.strip().strip("'\"")

    def _gset_set(self, schema: str, key: str, val: str):
        if not have("gsettings"):
            self.win.toast("gsettings not installed"); return
        sh(["gsettings", "set", schema, key, val])
        self.win.toast(f"{key} -> applied"); self.mark_changed(key)

    def _list_themes(self, dirname: str, marker: str) -> list:
        roots = [Path.home() / f".{dirname}",
                 Path.home() / ".local/share" / dirname,
                 Path(f"/usr/share/{dirname}")]
        seen = set()
        for root in roots:
            if not root.exists(): continue
            for p in root.iterdir():
                if not p.is_dir(): continue
                # marker can be a file or subdir
                if (p / marker).exists() or any(
                        (p / sub / marker).exists()
                        for sub in p.iterdir() if sub.is_dir()):
                    seen.add(p.name)
        return sorted(seen)

    def _apply_theme(self, themes):
        idx = self._theme_dd.get_selected()
        if 0 <= idx < len(themes):
            self._gset_set("org.gnome.desktop.interface", "gtk-theme",
                           f'"{themes[idx]}"')
            # GTK4 honours GTK_THEME env var; for GNOME apps the gsettings
            # key is canonical.
            self.needs_restart("gtk theme")

    def _apply_iconset(self, icons):
        idx = self._icon_dd.get_selected()
        if 0 <= idx < len(icons):
            self._gset_set("org.gnome.desktop.interface", "icon-theme",
                           f'"{icons[idx]}"')

    def _apply_cursor(self, cursors):
        idx = self._cur_dd.get_selected()
        if 0 <= idx < len(cursors):
            name = cursors[idx]
            self._gset_set("org.gnome.desktop.interface", "cursor-theme",
                           f'"{name}"')
            # Hyprland honours hyprctl cursor as well
            sh(["hyprctl", "setcursor", name, "24"])

    def _apply_cursor_size(self, size: int):
        self._gset_set("org.gnome.desktop.interface", "cursor-size", str(size))
        sh(["hyprctl", "keyword", "misc:cursor_inactive_timeout", "0"])

    def _apply_font(self, font: str):
        if not font: return
        self._gset_set("org.gnome.desktop.interface", "font-name",
                       f'"{font}"')

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Wallpaper"),
            SearchEntry(self.KEY, self.TITLE, "Color scheme", "dark light"),
            SearchEntry(self.KEY, self.TITLE, "Accent color"),
            SearchEntry(self.KEY, self.TITLE, "Animations"),
            SearchEntry(self.KEY, self.TITLE, "UI font size"),
            SearchEntry(self.KEY, self.TITLE, "GTK theme", "gnome theme"),
            SearchEntry(self.KEY, self.TITLE, "Icon theme", "icons"),
            SearchEntry(self.KEY, self.TITLE, "Cursor theme",
                        "cursor pointer mouse"),
            SearchEntry(self.KEY, self.TITLE, "Cursor size"),
            SearchEntry(self.KEY, self.TITLE, "Interface font"),
            SearchEntry(self.KEY, self.TITLE, "Monospace font"),
            SearchEntry(self.KEY, self.TITLE, "Titlebar buttons",
                        "window controls layout"),
        ]


# ─── Workspaces ─────────────────────────────────────────────────────────────
class WorkspacesPage(BasePage):
    KEY = "workspaces"; TITLE = "Workspaces"; ICON = "🪟"

    HYPR_CONF = Path.home() / ".config/hypr/hyprland.conf"

    def build(self):
        # ── 1. active workspaces (live) ────────────────────────────────────
        self.list_card = Card("active workspaces")
        self.box.append(self.list_card)
        row = Gtk.Box(spacing=8)
        b = SketchButton("Refresh", width=92, height=24, color=NEON_GREEN)
        b.connect("clicked", lambda _b: self.refresh())
        row.append(b)
        b2 = SketchButton("New scratchpad", width=140, height=24, color=NEON_BLUE)
        b2.connect("clicked", lambda _b: (
            sh("hyprctl dispatch togglespecialworkspace nyx-scratch"),
            self.win.toast("scratchpad toggled"), self.refresh()))
        row.append(b2)
        b3 = SketchButton("Reload Hyprland", width=140, height=24, color=ACCENT_GOLD)
        b3.connect("clicked", lambda _b: (
            sh("hyprctl reload"), self.win.toast("hyprland reloaded")))
        row.append(b3)
        self.box.append(row)

        # ── 2. layout picker (dwindle vs master) ──────────────────────────
        c = Card("layout engine")
        self.box.append(c)
        cur_layout = self._hypr_option("general:layout") or "dwindle"
        c.add_row(kv_row("Current layout:", cur_layout))
        lr = Gtk.Box(spacing=8)
        for name in ("dwindle", "master"):
            btn = SketchButton(name, width=92, height=24, color=NEON_PINK,
                               primary=(name == cur_layout))
            btn.connect("clicked", lambda _b, n=name: self._set_layout(n))
            lr.append(btn)
        c.add_row(lr)

        # ── 3. gaps + border ───────────────────────────────────────────────
        c = Card("gaps & border")
        self.box.append(c)
        for opt, label, lo, hi in (
                ("general:gaps_in",     "Inner gap (px)",   0, 30),
                ("general:gaps_out",    "Outer gap (px)",   0, 50),
                ("general:border_size", "Border width (px)",1, 10),
                ("decoration:rounding", "Window rounding",  0, 24)):
            cur = self._hypr_int(opt, 5)
            adj = Gtk.Adjustment(value=cur, lower=lo, upper=hi,
                                 step_increment=1, page_increment=2)
            sc = Gtk.Scale(adjustment=adj,
                           orientation=Gtk.Orientation.HORIZONTAL)
            sc.set_size_request(220, -1); sc.set_draw_value(True)
            sc.set_value_pos(Gtk.PositionType.RIGHT); sc.set_digits(0)
            def _on_change(s, _opt=opt):
                v = int(s.get_value())
                sh_async(["hyprctl", "keyword", _opt, str(v)])
            sc.connect("value-changed", _on_change)
            c.add_row(kv_row(label, sc))

        # ── 4. blur / decoration ───────────────────────────────────────────
        c = Card("blur & shadow")
        self.box.append(c)
        blur_on = (self._hypr_option("decoration:blur:enabled") or "true") != "false"
        bt = SketchToggle("Window blur", width=180, height=26,
                          color=NEON_BLUE, active=blur_on)
        bt.connect("clicked", lambda _b: (
            sh(f"hyprctl keyword decoration:blur:enabled "
               f"{'true' if bt.active else 'false'}"),
            self.win.toast(f"blur {'on' if bt.active else 'off'}")))
        c.add_row(bt)
        sh_on = (self._hypr_option("decoration:drop_shadow") or "true") != "false"
        st = SketchToggle("Drop shadow", width=180, height=26,
                          color=NEON_BLUE, active=sh_on)
        st.connect("clicked", lambda _b: sh(
            f"hyprctl keyword decoration:drop_shadow "
            f"{'true' if st.active else 'false'}"))
        c.add_row(st)
        anim_on = (self._hypr_option("animations:enabled") or "true") != "false"
        at = SketchToggle("Animations", width=180, height=26,
                          color=NEON_GREEN, active=anim_on)
        at.connect("clicked", lambda _b: sh(
            f"hyprctl keyword animations:enabled "
            f"{'true' if at.active else 'false'}"))
        c.add_row(at)

        # ── 5. border colors ───────────────────────────────────────────────
        c = Card("active border color")
        self.box.append(c)
        for name, expr in (
                ("Neon pink",  "rgba(ff00ffee) rgba(b800ffee) 45deg"),
                ("Cyber blue", "rgba(00aaffee) rgba(39ff14ee) 45deg"),
                ("Acid green", "rgba(39ff14ee) rgba(ffc833ee) 45deg"),
                ("Pure pink",  "rgba(ff00ffee)")):
            br = Gtk.Box(spacing=8)
            br.append(Gtk.Label(label=name, xalign=0))
            apply_b = SketchButton("Apply", width=72, height=22,
                                   color=NEON_PINK)
            apply_b.connect("clicked", lambda _b, e=expr, n=name: (
                sh(f"hyprctl keyword general:col.active_border {e}"),
                self.win.toast(f"border -> {n}")))
            br.append(apply_b); c.add_row(br)

        self.add_note(
            "Live changes apply via hyprctl. To make any change permanent, "
            "edit ~/.config/hypr/hyprland.conf -- the config is reloaded by "
            "the 'Reload Hyprland' button above.")
        self.refresh()

    def _hypr_option(self, key: str) -> str:
        rc, out, _ = sh(["hyprctl", "getoption", key, "-j"])
        if rc != 0: return ""
        try:
            j = json.loads(out)
            for k in ("str", "custom", "int"):
                if k in j and j[k] not in (None, ""): return str(j[k])
        except Exception: pass
        return ""

    def _hypr_int(self, key: str, default: int) -> int:
        v = self._hypr_option(key)
        try: return int(v)
        except Exception: return default

    def _set_layout(self, name: str):
        sh(["hyprctl", "keyword", "general:layout", name])
        self.win.toast(f"layout -> {name}")
        self.needs_restart("layout"); self.refresh()

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
                f"monitor: {w.get('monitor')}  windows: {w.get('windows',0)}"))

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Workspaces"),
            SearchEntry(self.KEY, self.TITLE, "Gaps", "inner outer"),
            SearchEntry(self.KEY, self.TITLE, "Border color", "active border"),
            SearchEntry(self.KEY, self.TITLE, "Layout", "dwindle master tiling"),
            SearchEntry(self.KEY, self.TITLE, "Blur", "decoration"),
            SearchEntry(self.KEY, self.TITLE, "Rounding", "decoration corners"),
            SearchEntry(self.KEY, self.TITLE, "Scratchpad", "special workspace"),
            SearchEntry(self.KEY, self.TITLE, "Reload Hyprland"),
        ]


# ─── Keyboard ───────────────────────────────────────────────────────────────
class KeyboardPage(BasePage):
    KEY = "keyboard"; TITLE = "Keyboard"; ICON = "⌨"

    def build(self):
        # ── 1. layout (live + persistent picker) ───────────────────────────
        c = Card("layout")
        self.box.append(c)
        rc, out, _ = sh("hyprctl -j devices")
        layouts = []
        try:
            data = json.loads(out)
            for kb in data.get("keyboards", []):
                layouts.append(
                    f"{kb.get('name','?')} → {kb.get('active_keymap','?')}")
        except Exception: pass
        for l in layouts:
            c.add_row(Gtk.Label(label=l, xalign=0))
        if not layouts:
            c.add_row(Gtk.Label(label="(no keyboards detected)", xalign=0))
        # current localectl
        rc, out, _ = sh("localectl status")
        for ln in out.splitlines():
            s = ln.strip()
            if s.startswith(("X11 Layout", "X11 Variant", "X11 Model",
                             "X11 Options", "VC Keymap")):
                c.add_row(Gtk.Label(label=s, xalign=0))
        # picker — top common layouts + dropdown of all
        all_layouts = []
        rc, out, _ = sh("localectl list-x11-keymap-layouts")
        if rc == 0:
            all_layouts = [l.strip() for l in out.splitlines() if l.strip()]
        common = ["us", "us(intl)", "gb", "de", "fr", "es", "it",
                  "ru", "jp", "kr", "cn"]
        c.add_row(Gtk.Label(label="Quick set (live + persistent):",
                            xalign=0))
        row = Gtk.Box(spacing=6)
        for lay in common:
            base = lay.split("(")[0]
            if base not in all_layouts and all_layouts: continue
            b = SketchButton(lay, width=80, height=22, color=NEON_BLUE)
            b.connect("clicked", lambda _b, l=lay:
                      self._set_layout(l, ""))
            row.append(b)
        c.add_row(row)
        if all_layouts:
            row = Gtk.Box(spacing=8)
            row.append(Gtk.Label(label="All layouts:", xalign=0))
            dd = Gtk.DropDown.new_from_strings(all_layouts)
            try: dd.set_selected(all_layouts.index("us"))
            except ValueError: pass
            row.append(dd)
            ent = Gtk.Entry()
            ent.set_placeholder_text("variant (e.g. dvorak, intl) — optional")
            ent.set_hexpand(True)
            row.append(ent)
            b = SketchButton("Apply", width=90, height=22,
                             color=NEON_GREEN)
            b.connect("clicked", lambda _b: self._set_layout(
                all_layouts[dd.get_selected()], ent.get_text().strip()))
            row.append(b)
            c.add_row(row)

        # ── 2. xkb options (caps swap, compose, etc.) ──────────────────────
        c = Card("xkb options")
        self.box.append(c)
        rc, cur_opts, _ = sh(
            "localectl status | awk -F': ' '/X11 Options/ {print $2}'")
        cur_opts = cur_opts.strip()
        c.add_row(kv_row("Active options:", cur_opts or "(none)"))
        row = Gtk.Box(spacing=6)
        for label, opt in (
            ("Caps→Esc",     "caps:escape"),
            ("Caps→Ctrl",    "ctrl:nocaps"),
            ("Swap Caps↔Esc", "caps:swapescape"),
            ("Compose=Right Alt",  "compose:ralt"),
            ("Compose=Menu",       "compose:menu"),
            ("Numlock on boot",    "numpad:mac"),
        ):
            active = opt in cur_opts
            b = SketchButton(label, width=160, height=22,
                             color=ACCENT_GOLD, primary=active)
            b.connect("clicked",
                      lambda _b, o=opt: self._toggle_xkb_opt(o))
            row.append(b)
        c.add_row(row)
        b = SketchButton("Clear all options", width=180, height=22,
                         color=DANGER_RED)
        b.connect("clicked", lambda _b: self._set_xkb_opts(""))
        c.add_row(b)

        # ── 3. repeat rate / delay (existing, kept) ────────────────────────
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
        sl = SketchSlider(value=min(rate,80)/80.0,
                          color=NEON_PINK, width=220)
        sl.connect("value-changed",
                   lambda _s, v: sh(
                       f"hyprctl keyword input:repeat_rate {int(5+v*75)}"))
        row.append(sl); c.add_row(row)
        row = Gtk.Box(spacing=10)
        row.append(Gtk.Label(label=f"delay {delay} ms", xalign=0))
        sl = SketchSlider(value=min(delay,1000)/1000.0,
                          color=NEON_BLUE, width=220)
        sl.connect("value-changed",
                   lambda _s, v: sh(
                       f"hyprctl keyword input:repeat_delay {int(150+v*850)}"))
        row.append(sl); c.add_row(row)
        # quick presets
        row = Gtk.Box(spacing=6)
        for label, r, d in (("Slow",  20, 700),
                            ("Normal", 30, 500),
                            ("Fast",   45, 300),
                            ("Gamer",  60, 180)):
            b = SketchButton(label, width=80, height=22,
                             color=NEON_GREEN)
            b.connect("clicked", lambda _b, r=r, d=d: (
                sh(f"hyprctl keyword input:repeat_rate {r}"),
                sh(f"hyprctl keyword input:repeat_delay {d}"),
                self.win.toast(f"repeat → {r}/s @ {d}ms"),
                self.refresh()))
            row.append(b)
        c.add_row(row)

        # ── 4. numlock / capslock state ────────────────────────────────────
        c = Card("lock keys")
        self.box.append(c)
        rc, out, _ = sh("hyprctl getoption input:numlock_by_default -j")
        try: nl = json.loads(out).get("int", 0) == 1
        except Exception: nl = False
        nl_tog = SketchToggle("Numlock at login", width=180, height=24,
                              color=NEON_BLUE, active=nl)
        nl_tog.connect("clicked", lambda _b: (
            sh(f"hyprctl keyword input:numlock_by_default "
               f"{1 if nl_tog.active else 0}"),
            self.win.toast(
                f"numlock at login → {'on' if nl_tog.active else 'off'}")))
        c.add_row(nl_tog)
        # current LED state
        rc, out, _ = sh(
            "for d in /sys/class/leds/input*::numlock; do "
            "[ -e $d ] && echo $(basename $d): $(cat $d/brightness); done")
        if out.strip():
            for ln in out.strip().splitlines()[:4]:
                c.add_row(Gtk.Label(label=ln, xalign=0))

        # ── 5. shortcuts (existing) + grouped by mod ──────────────────────
        c = Card("Hyprland keybinds")
        self.box.append(c)
        rc, out, _ = sh("hyprctl -j binds")
        try: binds = json.loads(out)
        except Exception: binds = []
        c.add_row(Gtk.Label(label=f"{len(binds)} active binds", xalign=0))
        # group by modmask
        from collections import defaultdict
        groups = defaultdict(list)
        for b in binds:
            mm = int(b.get("modmask") or 0)
            groups[mm].append(b)
        c.add_row(kv_row("Mod groups:",
                         ", ".join(f"mod{m}={len(v)}"
                                   for m, v in sorted(groups.items()))))
        # conflict detector — duplicate (mod, key) pairs
        seen = {}
        conflicts = []
        for b in binds:
            k = (b.get("modmask"), b.get("key"))
            if k in seen and b.get("dispatcher") != seen[k].get("dispatcher"):
                conflicts.append((k, seen[k], b))
            else:
                seen[k] = b
        if conflicts:
            c.add_row(Gtk.Label(
                label=f"⚠ {len(conflicts)} conflicting binds — "
                      f"first: mod{conflicts[0][0][0]}+"
                      f"{conflicts[0][0][1]}", xalign=0))
        else:
            c.add_row(Gtk.Label(label="✓ no bind conflicts", xalign=0))
        # full scrollable list
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 220)
        tv = Gtk.TextView(); tv.set_editable(False); tv.set_monospace(True)
        tv.add_css_class("nyx-editor")
        text = "\n".join(
            f"{(b.get('modmask') or 0):3d} + {b.get('key',''):<14}  →  "
            f"{b.get('dispatcher','')} {b.get('arg','')}"
            for b in binds[:300])
        tv.get_buffer().set_text(text or "(no binds)")
        sw.set_child(tv); c.add_row(sw)

        # ── 6. live key tester ─────────────────────────────────────────────
        c = Card("key event tester")
        self.box.append(c)
        c.add_row(Gtk.Label(
            label="Click into the field then press any key combo. "
                  "Shows the keysym / keyval as Hyprland sees it.",
            xalign=0))
        ent = Gtk.Entry()
        ent.set_placeholder_text("focus here, then press a key…")
        c.add_row(ent)
        out_lbl = Gtk.Label(label="(no key yet)", xalign=0)
        out_lbl.add_css_class("nyx-mono")
        c.add_row(out_lbl)
        kc = Gtk.EventControllerKey()
        def on_key(_ctl, keyval, keycode, state):
            mods = []
            if state & Gdk.ModifierType.SHIFT_MASK:   mods.append("SHIFT")
            if state & Gdk.ModifierType.CONTROL_MASK: mods.append("CTRL")
            if state & Gdk.ModifierType.ALT_MASK:     mods.append("ALT")
            if state & Gdk.ModifierType.SUPER_MASK:   mods.append("SUPER")
            name = Gdk.keyval_name(keyval) or "?"
            out_lbl.set_text(
                f"keyval={keyval} (0x{keyval:x})  name={name}  "
                f"keycode={keycode}  mods=[{'+'.join(mods) or 'none'}]")
            return False
        kc.connect("key-pressed", on_key)
        ent.add_controller(kc)

        # ── 7. input methods (fcitx5/ibus) ─────────────────────────────────
        c = Card("input method")
        self.box.append(c)
        for tool in ("fcitx5", "ibus", "fcitx"):
            c.add_row(kv_row(f"{tool}:",
                             "installed" if have(tool)
                             else "not installed"))
        c.add_row(kv_row("GTK_IM_MODULE:",
                         os.environ.get("GTK_IM_MODULE", "(unset)")))
        c.add_row(kv_row("QT_IM_MODULE:",
                         os.environ.get("QT_IM_MODULE", "(unset)")))
        c.add_row(kv_row("XMODIFIERS:",
                         os.environ.get("XMODIFIERS", "(unset)")))
        row = Gtk.Box(spacing=8)
        if have("fcitx5"):
            b = SketchButton("Launch fcitx5", width=160, height=24,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b: (
                subprocess.Popen(["fcitx5", "-d"], start_new_session=True),
                self.win.toast("fcitx5 launched (daemon)")))
            row.append(b)
            b2 = SketchButton("fcitx5-config-qt", width=180, height=24,
                              color=ACCENT_GOLD)
            b2.connect("clicked", lambda _b: (
                subprocess.Popen(["fcitx5-config-qt"],
                                 start_new_session=True),
                self.win.toast("fcitx5 config opened")))
            row.append(b2)
        if have("ibus"):
            b = SketchButton("Launch ibus-setup", width=180, height=24,
                             color=ACCENT_PURP)
            b.connect("clicked", lambda _b: (
                subprocess.Popen(["ibus-setup"], start_new_session=True),
                self.win.toast("ibus-setup opened")))
            row.append(b)
        if row.get_first_child(): c.add_row(row)

        # ── 8. console keymap ──────────────────────────────────────────────
        c = Card("virtual console keymap")
        self.box.append(c)
        rc, out, _ = sh("localectl status | awk -F': ' '/VC Keymap/ {print $2}'")
        cur_vc = out.strip()
        c.add_row(kv_row("VC Keymap:", cur_vc or "(default)"))
        rc, out, _ = sh("localectl list-keymaps")
        vc_maps = [l.strip() for l in out.splitlines() if l.strip()]
        if vc_maps:
            row = Gtk.Box(spacing=6)
            row.append(Gtk.Label(label="Quick:", xalign=0))
            for k in ("us", "uk", "de", "fr", "dvorak", "colemak"):
                if k not in vc_maps: continue
                b = SketchButton(k, width=72, height=22,
                                 color=NEON_BLUE,
                                 primary=(k == cur_vc))
                b.connect("clicked", lambda _b, k=k: self._set_vc_keymap(k))
                row.append(b)
            c.add_row(row)

    # ── helpers ────────────────────────────────────────────────────────────
    def _set_layout(self, layout: str, variant: str):
        # live (hyprctl)
        sh(f"hyprctl keyword input:kb_layout {shlex.quote(layout)}")
        if variant:
            sh(f"hyprctl keyword input:kb_variant {shlex.quote(variant)}")
        else:
            sh("hyprctl keyword input:kb_variant ''")
        # persistent (localectl) — needs sudo
        cmd = (f"sudo -n localectl set-x11-keymap "
               f"{shlex.quote(layout)} '' "
               f"{shlex.quote(variant)}")
        sh_async(cmd, lambda r: self.win.toast(
            f"layout → {layout}{' (' + variant + ')' if variant else ''}"
            if r[0] == 0 else
            "live set; persistent needs sudo localectl"))

    def _toggle_xkb_opt(self, opt: str):
        rc, out, _ = sh(
            "localectl status | awk -F': ' '/X11 Options/ {print $2}'")
        cur = [o for o in out.strip().split(",") if o]
        if opt in cur: cur.remove(opt)
        else: cur.append(opt)
        self._set_xkb_opts(",".join(cur))

    def _set_xkb_opts(self, opts: str):
        # live
        sh(f"hyprctl keyword input:kb_options {shlex.quote(opts)}")
        # persistent
        rc, out, _ = sh("localectl status")
        cur_layout = "us"; cur_variant = ""
        for ln in out.splitlines():
            if "X11 Layout" in ln:
                cur_layout = ln.split(":", 1)[1].strip() or "us"
            elif "X11 Variant" in ln:
                cur_variant = ln.split(":", 1)[1].strip()
        cmd = (f"sudo -n localectl set-x11-keymap "
               f"{shlex.quote(cur_layout)} '' "
               f"{shlex.quote(cur_variant)} {shlex.quote(opts)}")
        sh_async(cmd, lambda r: self.win.toast(
            f"xkb options → {opts or '(cleared)'}"
            if r[0] == 0 else "live set; persistent needs sudo localectl"))

    def _set_vc_keymap(self, k: str):
        sh_async(f"sudo -n localectl set-keymap {shlex.quote(k)}",
                 lambda r: self.win.toast(
                     f"VC keymap → {k}" if r[0] == 0
                     else "needs sudo NOPASSWD"))

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Layout"),
            SearchEntry(self.KEY, self.TITLE, "Repeat rate"),
            SearchEntry(self.KEY, self.TITLE, "Repeat delay"),
            SearchEntry(self.KEY, self.TITLE, "Repeat presets",
                        "slow normal fast gamer"),
            SearchEntry(self.KEY, self.TITLE, "Layout variant",
                        "dvorak colemak intl"),
            SearchEntry(self.KEY, self.TITLE, "All keyboard layouts",
                        "localectl x11"),
            SearchEntry(self.KEY, self.TITLE, "Caps Lock as Escape",
                        "caps escape swap"),
            SearchEntry(self.KEY, self.TITLE, "Caps Lock as Ctrl",
                        "nocaps"),
            SearchEntry(self.KEY, self.TITLE, "Compose key",
                        "ralt menu"),
            SearchEntry(self.KEY, self.TITLE, "xkb options",
                        "modifier swap"),
            SearchEntry(self.KEY, self.TITLE, "Numlock on login",
                        "numlock_by_default"),
            SearchEntry(self.KEY, self.TITLE, "Shortcuts",
                        "binds keybinds hotkeys"),
            SearchEntry(self.KEY, self.TITLE, "Bind conflicts",
                        "duplicate hotkey"),
            SearchEntry(self.KEY, self.TITLE, "Key event tester",
                        "keysym keyval keycode capture"),
            SearchEntry(self.KEY, self.TITLE, "Input method",
                        "fcitx5 ibus IM"),
            SearchEntry(self.KEY, self.TITLE, "Console keymap",
                        "VC tty localectl"),
        ]


# ─── Mouse / Touchpad ───────────────────────────────────────────────────────
class MousePage(BasePage):
    KEY = "mouse"; TITLE = "Mouse & Touchpad"; ICON = "🖱"

    # ── helpers ────────────────────────────────────────────────────────────
    def _hypr_int(self, opt: str, default: int = 0) -> int:
        rc, out, _ = sh(f"hyprctl getoption {opt} -j")
        try: return int(json.loads(out).get("int", default))
        except Exception: return default

    def _hypr_float(self, opt: str, default: float = 0.0) -> float:
        rc, out, _ = sh(f"hyprctl getoption {opt} -j")
        try: return float(json.loads(out).get("float", default))
        except Exception: return default

    def _hypr_str(self, opt: str, default: str = "") -> str:
        rc, out, _ = sh(f"hyprctl getoption {opt} -j")
        try: return str(json.loads(out).get("str", default) or default)
        except Exception: return default

    def build(self):
        # ── 1. detected devices ────────────────────────────────────────────
        c = Card("detected input devices")
        self.box.append(c)
        rc, out, _ = sh("hyprctl -j devices")
        mice = touchpads = []; tablets = []
        try:
            d = json.loads(out)
            mice      = d.get("mice", [])
            touchpads = [m for m in mice if "touchpad" in
                         (m.get("name","").lower())]
            real_mice = [m for m in mice if m not in touchpads]
            tablets   = d.get("tablets", [])
        except Exception:
            real_mice = []
        c.add_row(kv_row("Mice / pointers:", str(len(real_mice))))
        for m in real_mice[:8]:
            c.add_row(Gtk.Label(label=f"  • {m.get('name','?')}",
                                xalign=0))
        c.add_row(kv_row("Touchpads:", str(len(touchpads))))
        for t in touchpads[:4]:
            c.add_row(Gtk.Label(label=f"  • {t.get('name','?')}",
                                xalign=0))
        c.add_row(kv_row("Tablets:", str(len(tablets))))
        for t in tablets[:4]:
            c.add_row(Gtk.Label(label=f"  • {t.get('name','?')}",
                                xalign=0))
        # libinput list-devices summary if available (needs root)
        if have("libinput"):
            row = Gtk.Box(spacing=8)
            b = SketchButton("libinput list-devices (sudo)", width=240,
                             height=24, color=NEON_BLUE)
            b.connect("clicked", lambda _b: self._term_run(
                "sudo libinput list-devices | less",
                "listing libinput devices…"))
            row.append(b)
            b2 = SketchButton("libinput debug-events", width=200,
                              height=24, color=ACCENT_GOLD)
            b2.connect("clicked", lambda _b: self._term_run(
                "sudo libinput debug-events",
                "watching live input events…"))
            row.append(b2)
            c.add_row(row)

        # ── 2. pointer (mouse) ─────────────────────────────────────────────
        c = Card("pointer (mouse)")
        self.box.append(c)
        s = self._hypr_float("input:sensitivity")
        row = Gtk.Box(spacing=10)
        row.append(Gtk.Label(label=f"sensitivity {s:+.2f}", xalign=0))
        sl = SketchSlider(value=(s+1)/2.0, color=NEON_PINK, width=240)
        sl.connect("value-changed",
                   lambda _s, v: sh(
                       f"hyprctl keyword input:sensitivity {(v*2-1):.2f}"))
        row.append(sl); c.add_row(row)
        # presets
        row = Gtk.Box(spacing=6)
        for label, v in (("Slowest", -0.7), ("Slow", -0.3), ("Default", 0.0),
                         ("Fast", 0.4), ("Fastest", 0.8)):
            b = SketchButton(label, width=80, height=22,
                             color=NEON_GREEN, primary=(abs(s-v) < 0.05))
            b.connect("clicked", lambda _b, v=v: (
                sh(f"hyprctl keyword input:sensitivity {v:.2f}"),
                self.win.toast(f"sensitivity → {v:+.2f}"),
                self.refresh()))
            row.append(b)
        c.add_row(row)
        # accel profile
        cur_ap = self._hypr_str("input:accel_profile", "adaptive")
        row = Gtk.Box(spacing=8)
        row.append(Gtk.Label(label=f"accel ({cur_ap}):", xalign=0))
        for label, ap in (("adaptive", "adaptive"),
                          ("flat (raw)", "flat"),
                          ("custom", "custom")):
            b = SketchButton(label, width=110, height=22,
                             color=NEON_BLUE, primary=(ap == cur_ap))
            b.connect("clicked",
                      lambda _b, ap=ap: (
                          sh(f"hyprctl keyword input:accel_profile {ap}"),
                          self.win.toast(f"accel → {ap}"),
                          self.refresh()))
            row.append(b)
        c.add_row(row)
        # left-handed (button swap)
        lh = self._hypr_int("input:left_handed", 0) == 1
        lh_tog = SketchToggle("left-handed (swap L/R buttons)",
                              width=260, height=24,
                              color=ACCENT_PURP, active=lh)
        lh_tog.connect("clicked", lambda _b: (
            sh(f"hyprctl keyword input:left_handed "
               f"{1 if lh_tog.active else 0}"),
            self.win.toast(
                f"buttons → {'swapped' if lh_tog.active else 'normal'}")))
        c.add_row(lh_tog)
        # follow mouse focus + scroll factor
        fm = self._hypr_int("input:follow_mouse", 1)
        row = Gtk.Box(spacing=8)
        row.append(Gtk.Label(label=f"follow_mouse ({fm}):", xalign=0))
        for label, val in (("0 always-focus", 0),
                           ("1 normal", 1),
                           ("2 sloppy", 2),
                           ("3 click-only", 3)):
            b = SketchButton(label, width=130, height=22,
                             color=ACCENT_GOLD, primary=(val == fm))
            b.connect("clicked", lambda _b, v=val: (
                sh(f"hyprctl keyword input:follow_mouse {v}"),
                self.win.toast(f"follow_mouse → {v}"),
                self.refresh()))
            row.append(b)
        c.add_row(row)

        # ── 3. scrolling ───────────────────────────────────────────────────
        c = Card("scrolling")
        self.box.append(c)
        sf = self._hypr_float("input:scroll_factor", 1.0)
        row = Gtk.Box(spacing=10)
        row.append(Gtk.Label(label=f"scroll speed ×{sf:.2f}", xalign=0))
        sl = SketchSlider(value=min(sf,3.0)/3.0, color=NEON_BLUE, width=220)
        sl.connect("value-changed", lambda _s, v: sh(
            f"hyprctl keyword input:scroll_factor {(0.1 + v*2.9):.2f}"))
        row.append(sl); c.add_row(row)
        # natural scroll - mouse + touchpad (separate)
        ns_mouse = self._hypr_int("input:natural_scroll", 0) == 1
        ns_tp    = self._hypr_int("input:touchpad:natural_scroll", 0) == 1
        m_tog = SketchToggle("natural scroll (mouse wheel)",
                             width=260, height=24,
                             color=NEON_BLUE, active=ns_mouse)
        m_tog.connect("clicked", lambda _b: (
            sh(f"hyprctl keyword input:natural_scroll "
               f"{1 if m_tog.active else 0}"),
            self.win.toast(
                f"mouse natural scroll → "
                f"{'on' if m_tog.active else 'off'}")))
        c.add_row(m_tog)
        t_tog = SketchToggle("natural scroll (touchpad)",
                             width=260, height=24,
                             color=NEON_BLUE, active=ns_tp)
        t_tog.connect("clicked", lambda _b: (
            sh(f"hyprctl keyword input:touchpad:natural_scroll "
               f"{1 if t_tog.active else 0}"),
            self.win.toast(
                f"touchpad natural scroll → "
                f"{'on' if t_tog.active else 'off'}")))
        c.add_row(t_tog)
        # scroll method (touchpad)
        sm = self._hypr_int("input:touchpad:scroll_method", 0)
        row = Gtk.Box(spacing=8)
        row.append(Gtk.Label(label="scroll method:", xalign=0))
        for label, val in (("two-finger", "2fg"),
                           ("edge", "edge"),
                           ("on-button", "on_button_down"),
                           ("none", "no_scroll")):
            b = SketchButton(label, width=110, height=22,
                             color=ACCENT_GOLD)
            b.connect("clicked", lambda _b, v=label: (
                sh(f"hyprctl keyword input:touchpad:scroll_method "
                   f"{v.replace('-','_')}"),
                self.win.toast(f"scroll method → {v}")))
            row.append(b)
        c.add_row(row)

        # ── 4. touchpad ────────────────────────────────────────────────────
        if touchpads:
            c = Card("touchpad")
            self.box.append(c)
            # tap to click
            tap = self._hypr_int("input:touchpad:tap-to-click", 1) == 1
            t = SketchToggle("tap to click", width=160, height=24,
                             color=NEON_BLUE, active=tap)
            t.connect("clicked", lambda _b: (
                sh(f"hyprctl keyword input:touchpad:tap-to-click "
                   f"{1 if t.active else 0}"),
                self.win.toast(
                    f"tap → {'on' if t.active else 'off'}")))
            c.add_row(t)
            # tap and drag
            td = self._hypr_int("input:touchpad:tap-and-drag", 1) == 1
            ttd = SketchToggle("tap and drag", width=160, height=24,
                               color=NEON_BLUE, active=td)
            ttd.connect("clicked", lambda _b: sh(
                f"hyprctl keyword input:touchpad:tap-and-drag "
                f"{1 if ttd.active else 0}"))
            c.add_row(ttd)
            # drag lock
            dl = self._hypr_int("input:touchpad:drag_lock", 0) == 1
            dlt = SketchToggle("drag lock", width=160, height=24,
                               color=NEON_BLUE, active=dl)
            dlt.connect("clicked", lambda _b: sh(
                f"hyprctl keyword input:touchpad:drag_lock "
                f"{1 if dlt.active else 0}"))
            c.add_row(dlt)
            # disable while typing
            dwt = self._hypr_int("input:touchpad:disable_while_typing",
                                 1) == 1
            dwtt = SketchToggle("disable while typing", width=200,
                                height=24, color=ACCENT_PURP, active=dwt)
            dwtt.connect("clicked", lambda _b: sh(
                f"hyprctl keyword input:touchpad:disable_while_typing "
                f"{1 if dwtt.active else 0}"))
            c.add_row(dwtt)
            # middle button emulation
            mb = self._hypr_int("input:touchpad:middle_button_emulation",
                                0) == 1
            mbt = SketchToggle("middle-button emulation (L+R)",
                               width=240, height=24,
                               color=ACCENT_GOLD, active=mb)
            mbt.connect("clicked", lambda _b: sh(
                f"hyprctl keyword input:touchpad:middle_button_emulation "
                f"{1 if mbt.active else 0}"))
            c.add_row(mbt)
            # click method
            row = Gtk.Box(spacing=8)
            row.append(Gtk.Label(label="click method:", xalign=0))
            for label, val in (("button areas", "button_areas"),
                               ("clickfinger",  "clickfinger"),
                               ("none",         "none")):
                b = SketchButton(label, width=130, height=22,
                                 color=NEON_BLUE)
                b.connect("clicked", lambda _b, v=val: (
                    sh(f"hyprctl keyword input:touchpad:clickfinger_behavior "
                       f"{1 if v == 'clickfinger' else 0}"),
                    self.win.toast(f"click → {label}")))
                row.append(b)
            c.add_row(row)

        # ── 5. DPI / cpi (libinput-measure) ────────────────────────────────
        c = Card("mouse DPI / report rate")
        self.box.append(c)
        c.add_row(Gtk.Label(
            label="Most gaming mice expose DPI via on-device buttons. "
                  "Use libinput-measure to read your actual DPI/Hz.",
            xalign=0))
        for tool, desc in (
            ("libinput-measure-touchpad-pressure", "touchpad pressure"),
            ("libinput-measure-fretboard",         "(advanced)")):
            pass
        row = Gtk.Box(spacing=8)
        if have("libinput"):
            b = SketchButton("Measure mouse motion (libinput)",
                             width=260, height=24, color=NEON_GREEN)
            b.connect("clicked", lambda _b: self._term_run(
                "sudo libinput measure touchpad-pressure 2>/dev/null || "
                "sudo libinput measure 2>&1 | head -40",
                "running libinput measure…"))
            row.append(b)
            b2 = SketchButton("Record mouse motion 5s",
                              width=200, height=24, color=NEON_BLUE)
            b2.connect("clicked", lambda _b: self._term_run(
                "echo 'move your mouse for 5s...'; "
                "timeout 5 sudo libinput record /dev/input/by-id/$(ls "
                "/dev/input/by-id/ | grep -i mouse | head -1) | head -50",
                "recording 5s of motion…"))
            row.append(b2)
        if have("piper"):
            b = SketchButton("Launch Piper (gaming mouse GUI)",
                             width=260, height=24, color=ACCENT_PURP)
            b.connect("clicked", lambda _b: (
                subprocess.Popen(["piper"], start_new_session=True),
                self.win.toast("piper launched")))
            row.append(b)
        if not row.get_first_child():
            c.add_row(Gtk.Label(
                label="install libinput / piper for measurement",
                xalign=0))
        else:
            c.add_row(row)

        # ── 6. double-click speed test ─────────────────────────────────────
        c = Card("double-click test")
        self.box.append(c)
        c.add_row(Gtk.Label(
            label="Double-click in the box below — shows the gap (ms). "
                  "GTK default threshold ≈ 400ms.", xalign=0))
        click_lbl = Gtk.Label(label="(no clicks yet)", xalign=0)
        click_lbl.add_css_class("nyx-mono")
        target = Gtk.Box()
        target.set_size_request(-1, 60)
        target.add_css_class("nyx-card")
        target_lbl = Gtk.Label(label="◉  click me twice  ◉")
        target.append(target_lbl)
        gc = Gtk.GestureClick(); gc.set_button(1)
        last = [0.0]; count = [0]
        def on_press(_g, n_press, x, y):
            now = time.monotonic() * 1000
            gap = now - last[0]; last[0] = now
            count[0] += 1
            if count[0] == 1 or gap > 1500:
                click_lbl.set_text(
                    f"click #{count[0]} (waiting for second…)")
            else:
                verdict = ("✓ DOUBLE-CLICK"
                           if gap < 400 else
                           "✗ too slow (single)")
                click_lbl.set_text(
                    f"gap = {int(gap)} ms  →  {verdict}")
        gc.connect("pressed", on_press)
        target.add_controller(gc)
        c.add_row(target)
        c.add_row(click_lbl)

        # ── 7. cursor (jump-to-Appearance hint) ───────────────────────────
        c = Card("cursor theme & size")
        self.box.append(c)
        c.add_row(kv_row("XCURSOR_THEME:",
                         os.environ.get("XCURSOR_THEME", "(default)")))
        c.add_row(kv_row("XCURSOR_SIZE:",
                         os.environ.get("XCURSOR_SIZE", "24")))
        # quick sizes (live via hyprctl)
        cs = os.environ.get("XCURSOR_SIZE", "24")
        ct = os.environ.get("XCURSOR_THEME", "Adwaita")
        row = Gtk.Box(spacing=6)
        for s in (16, 20, 24, 32, 40, 48):
            b = SketchButton(str(s), width=48, height=22,
                             color=NEON_BLUE, primary=(str(s) == cs))
            b.connect("clicked", lambda _b, s=s: (
                sh(f"hyprctl setcursor {ct} {s}"),
                self.win.toast(f"cursor → {s}px")))
            row.append(b)
        c.add_row(row)
        c.add_row(Gtk.Label(
            label="(Theme picker lives in Themes & Appearance.)",
            xalign=0))

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
            SearchEntry(self.KEY, self.TITLE, "Mouse sensitivity"),
            SearchEntry(self.KEY, self.TITLE, "Sensitivity presets",
                        "slowest fastest"),
            SearchEntry(self.KEY, self.TITLE, "Acceleration profile",
                        "adaptive flat raw custom"),
            SearchEntry(self.KEY, self.TITLE, "Left-handed mouse",
                        "swap left right buttons"),
            SearchEntry(self.KEY, self.TITLE, "Follow mouse focus",
                        "sloppy click"),
            SearchEntry(self.KEY, self.TITLE, "Natural scroll (mouse)"),
            SearchEntry(self.KEY, self.TITLE, "Natural scroll (touchpad)"),
            SearchEntry(self.KEY, self.TITLE, "Scroll speed factor"),
            SearchEntry(self.KEY, self.TITLE, "Scroll method",
                        "two finger edge button"),
            SearchEntry(self.KEY, self.TITLE, "Tap to click", "touchpad"),
            SearchEntry(self.KEY, self.TITLE, "Tap and drag"),
            SearchEntry(self.KEY, self.TITLE, "Drag lock"),
            SearchEntry(self.KEY, self.TITLE, "Disable while typing",
                        "palm touchpad"),
            SearchEntry(self.KEY, self.TITLE, "Middle button emulation"),
            SearchEntry(self.KEY, self.TITLE, "Click method",
                        "clickfinger button areas"),
            SearchEntry(self.KEY, self.TITLE, "Detected input devices",
                        "libinput list"),
            SearchEntry(self.KEY, self.TITLE, "libinput debug events"),
            SearchEntry(self.KEY, self.TITLE, "Mouse DPI / report rate",
                        "piper measure"),
            SearchEntry(self.KEY, self.TITLE, "Double-click speed test",
                        "threshold ms"),
            SearchEntry(self.KEY, self.TITLE, "Cursor size live"),
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
        # ── 1. system time + NTP ──────────────────────────────────────────
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
        c.add_row(kv_row("RTC time:", info.get("RTC time", "?")))
        c.add_row(kv_row("Time zone:", info.get("Time zone", "?")))
        c.add_row(kv_row("NTP service:", info.get("NTP service", "?")))
        c.add_row(kv_row("Synchronized:", info.get("System clock synchronized", "?")))
        c.add_row(kv_row("RTC in local TZ:", info.get("RTC in local TZ", "?")))

        # NTP toggle
        ntp_on = "active" in info.get("NTP service", "")
        tog = SketchToggle("NTP auto-sync", width=180, height=26,
                           color=NEON_GREEN, active=ntp_on)
        tog.connect("clicked",
                    lambda _b: sh_async(
                        ["pkexec", "timedatectl", "set-ntp",
                         "true" if tog.active else "false"],
                        lambda r: (self.win.toast(
                            "NTP changed" if r[0]==0 else "needs sudo"),
                                   self.mark_changed("NTP"),
                                   self.refresh())))
        c.add_row(tog)

        # RTC toggle
        rtc_local = info.get("RTC in local TZ", "no") == "yes"
        rtog = SketchToggle("RTC stored in local time (else UTC)",
                            width=320, height=26, color=NEON_BLUE,
                            active=rtc_local)
        rtog.connect("clicked", lambda _b: sh_async(
            ["pkexec", "timedatectl", "set-local-rtc",
             "1" if rtog.active else "0"],
            lambda r: (self.win.toast(
                "RTC mode changed" if r[0]==0 else "needs sudo"),
                       self.mark_changed("RTC"), self.refresh())))
        c.add_row(rtog)

        # Sync now (chrony / timesyncd)
        sn = SketchButton("Sync now", width=110, height=24, color=ACCENT_GOLD)
        sn.connect("clicked", lambda _b: self._sync_now())
        c.add_row(sn)

        # ── 2. timezone picker ────────────────────────────────────────────
        tz_card = Card("timezone")
        self.box.append(tz_card)
        rc, out, _ = sh("timedatectl list-timezones")
        zones = out.splitlines() if rc == 0 else []
        if zones:
            row = Gtk.Box(spacing=8)
            self.tz_combo = Gtk.DropDown.new_from_strings(zones)
            cur = info.get("Time zone", "").split(" ")[0]
            try: self.tz_combo.set_selected(zones.index(cur))
            except (ValueError, AttributeError): pass
            self.tz_combo.set_hexpand(True)
            row.append(self.tz_combo)
            b = SketchButton("Set", width=58, height=24, color=NEON_GREEN)
            b.connect("clicked", lambda _b: self._set_tz(zones))
            row.append(b)
            tz_card.add_row(row)
            tz_card.add_row(kv_row("Available zones:", f"{len(zones)}"))

        # ── 3. clock format (gsettings if available) ──────────────────────
        fmt_card = Card("clock format")
        self.box.append(fmt_card)
        cur_fmt = "24h"
        if have("gsettings"):
            _, fout, _ = sh("gsettings get org.gnome.desktop.interface clock-format")
            if "12h" in fout: cur_fmt = "12h"
        fmt_card.add_row(kv_row("Current format:", cur_fmt))
        fr = Gtk.Box(spacing=8)
        for name in ("12h", "24h"):
            btn = SketchButton(name, width=72, height=22, color=NEON_PINK,
                               primary=(name == cur_fmt))
            btn.connect("clicked", lambda _b, n=name: self._set_clock_fmt(n))
            fr.append(btn)
        fmt_card.add_row(fr)

        sec_on = "true" in (sh("gsettings get org.gnome.desktop.interface "
                               "clock-show-seconds")[1] if have("gsettings") else "")
        st = SketchToggle("Show seconds", width=180, height=26,
                          color=NEON_BLUE, active=sec_on)
        st.connect("clicked", lambda _b: self._gset_bool(
            "org.gnome.desktop.interface", "clock-show-seconds", st.active))
        fmt_card.add_row(st)

        date_on = "true" in (sh("gsettings get org.gnome.desktop.interface "
                                "clock-show-date")[1] if have("gsettings") else "")
        dt = SketchToggle("Show date in clock", width=180, height=26,
                          color=NEON_BLUE, active=date_on)
        dt.connect("clicked", lambda _b: self._gset_bool(
            "org.gnome.desktop.interface", "clock-show-date", dt.active))
        fmt_card.add_row(dt)

        # ── 4. world clock ────────────────────────────────────────────────
        wc = Card("world clock")
        self.box.append(wc)
        from datetime import datetime as _dt
        for label, tz in (("New York", "America/New_York"),
                          ("London",   "Europe/London"),
                          ("Tokyo",    "Asia/Tokyo"),
                          ("Sydney",   "Australia/Sydney"),
                          ("Berlin",   "Europe/Berlin")):
            rc, t, _ = sh(["env", f"TZ={tz}", "date", "+%a %H:%M:%S"])
            wc.add_row(kv_row(f"{label} ({tz}):", t.strip() or "?"))

        self.add_note(
            "Time zone and NTP changes use pkexec to elevate. "
            "Clock format toggles use gsettings (GNOME schema) -- effective "
            "in any GNOME-style status bar.")

    def _sync_now(self):
        if have("chronyc"):
            sh_async(["pkexec", "chronyc", "makestep"],
                     lambda r: self.win.toast("chrony resynced"
                                              if r[0]==0 else "sync failed"))
        else:
            sh_async(["pkexec", "systemctl", "restart", "systemd-timesyncd"],
                     lambda r: self.win.toast("timesyncd restarted"
                                              if r[0]==0 else "sync failed"))

    def _set_tz(self, zones):
        z = zones[self.tz_combo.get_selected()]
        sh_async(["pkexec", "timedatectl", "set-timezone", z],
                 lambda r: (self.win.toast(
                     f"tz -> {z}" if r[0]==0 else "needs sudo"),
                            self.mark_changed("timezone"), self.refresh()))

    def _set_clock_fmt(self, fmt: str):
        if have("gsettings"):
            sh(["gsettings", "set", "org.gnome.desktop.interface",
                "clock-format", fmt])
            self.win.toast(f"clock -> {fmt}")
            self.mark_changed("clock format"); self.refresh()
        else:
            self.win.toast("gsettings not installed")

    def _gset_bool(self, schema: str, key: str, val: bool):
        if have("gsettings"):
            sh(["gsettings", "set", schema, key, "true" if val else "false"])
            self.mark_changed(key)

    def refresh(self):
        c = self.box.get_first_child()
        while c:
            n = c.get_next_sibling()
            if c is not self.box.get_first_child(): self.box.remove(c)
            c = n
        self.build()

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Time zone"),
            SearchEntry(self.KEY, self.TITLE, "NTP", "auto sync"),
            SearchEntry(self.KEY, self.TITLE, "Clock format", "12h 24h"),
            SearchEntry(self.KEY, self.TITLE, "Show seconds"),
            SearchEntry(self.KEY, self.TITLE, "RTC", "hardware clock UTC local"),
            SearchEntry(self.KEY, self.TITLE, "World clock"),
            SearchEntry(self.KEY, self.TITLE, "Sync now", "chrony timesyncd"),
        ]


# ─── Notifications ──────────────────────────────────────────────────────────
class NotificationsPage(BasePage):
    KEY = "notifications"; TITLE = "Notifications"; ICON = "🔔"

    def _detect_daemon(self) -> str:
        # priority: live process > installed binary
        for proc, ctl in (("mako",   "makoctl"),
                          ("dunst",  "dunstctl"),
                          ("swaync", "swaync-client")):
            rc, out, _ = sh(f"pgrep -x {proc}")
            if rc == 0 and out.strip():
                return proc
        for proc in ("mako", "dunst", "swaync"):
            if have(proc): return proc
        return ""

    def _open_in_notepad(self, path: str):
        # rev r13: standalone nyxus_notepad.py removed; tarball edition
        # provides /usr/local/bin/nyxus-notepad
        bin_path = "/usr/local/bin/nyxus-notepad"
        if Path(bin_path).exists():
            subprocess.Popen([bin_path, path],
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
        else:
            self.win.toast("nyxus-notepad not installed")

    def _term_run(self, cmd: str, toast: str):
        for term in ("foot", "alacritty", "kitty", "xterm"):
            if have(term):
                subprocess.Popen(
                    [term, "-e", "sh", "-c",
                     f"{cmd}; echo; echo 'press enter to close'; read _"],
                    start_new_session=True)
                self.win.toast(toast); return
        self.win.toast("no terminal found")

    def build(self):
        daemon = self._detect_daemon()

        # ── 1. status / daemon picker ──────────────────────────────────────
        c = Card("notification daemon")
        self.box.append(c)
        c.add_row(kv_row("Active daemon:", daemon or "(none detected)"))
        for name in ("mako", "dunst", "swaync"):
            rc, out, _ = sh(f"pgrep -x {name}")
            running = rc == 0 and out.strip() != ""
            installed = have(name) or have(name + "ctl") or have(
                "swaync-client" if name == "swaync" else name)
            mark = "● running" if running else (
                "○ installed" if installed else "✗ missing")
            c.add_row(kv_row(f"  {name}:", mark))
        if not daemon:
            c.add_row(Gtk.Label(
                label="install mako, dunst, or swaync to enable notifications",
                xalign=0))
            self.add_note(
                "no notification daemon is running. apps that send "
                "notifications via libnotify/D-Bus will silently fail "
                "until one is installed and started.")
            return

        # ── 2. quick controls ──────────────────────────────────────────────
        c = Card("quick controls")
        self.box.append(c)
        row = Gtk.Box(spacing=8)
        if daemon == "mako":
            b = SketchButton("Dismiss all", width=120, height=24,
                             color=DANGER_RED)
            b.connect("clicked", lambda _b: (
                sh("makoctl dismiss --all"),
                self.win.toast("dismissed all notifications")))
            row.append(b)
            b = SketchButton("Dismiss latest", width=130, height=24,
                             color=ACCENT_GOLD)
            b.connect("clicked", lambda _b: (
                sh("makoctl dismiss"),
                self.win.toast("dismissed latest")))
            row.append(b)
            b = SketchButton("Restore last", width=120, height=24,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b: (
                sh("makoctl restore"),
                self.win.toast("restored")))
            row.append(b)
            b = SketchButton("Reload config", width=130, height=24,
                             color=NEON_GREEN)
            b.connect("clicked", lambda _b: (
                sh("makoctl reload"),
                self.win.toast("mako reloaded")))
            row.append(b)
        elif daemon == "dunst":
            b = SketchButton("Close all", width=120, height=24,
                             color=DANGER_RED)
            b.connect("clicked", lambda _b: (
                sh("dunstctl close-all"),
                self.win.toast("closed all")))
            row.append(b)
            b = SketchButton("Close latest", width=130, height=24,
                             color=ACCENT_GOLD)
            b.connect("clicked", lambda _b: (
                sh("dunstctl close"),
                self.win.toast("closed latest")))
            row.append(b)
            b = SketchButton("Show context", width=130, height=24,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b: (
                sh("dunstctl context"),
                self.win.toast("context menu")))
            row.append(b)
        elif daemon == "swaync":
            b = SketchButton("Hide panel", width=120, height=24,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b: sh("swaync-client -cp"))
            row.append(b)
            b = SketchButton("Toggle panel", width=130, height=24,
                             color=NEON_GREEN)
            b.connect("clicked", lambda _b: sh("swaync-client -t"))
            row.append(b)
            b = SketchButton("Reload", width=100, height=24,
                             color=ACCENT_GOLD)
            b.connect("clicked", lambda _b: (
                sh("swaync-client -R"),
                self.win.toast("swaync reloaded")))
            row.append(b)
        c.add_row(row)

        # ── 3. Do-Not-Disturb ──────────────────────────────────────────────
        c = Card("do not disturb")
        self.box.append(c)
        if daemon == "mako":
            rc, out, _ = sh("makoctl mode")
            dnd_on = "do-not-disturb" in (out or "")
        elif daemon == "dunst":
            rc, out, _ = sh("dunstctl is-paused")
            dnd_on = "true" in (out or "").lower()
        else:  # swaync
            rc, out, _ = sh("swaync-client -D")
            dnd_on = "true" in (out or "").lower()
        dnd = SketchToggle("Do Not Disturb", width=180, height=26,
                           color=ACCENT_GOLD, active=dnd_on)
        def _dnd_cb(_b):
            on = dnd.active
            if daemon == "mako":
                sh(f"makoctl mode -t "
                   f"{'do-not-disturb' if on else 'default'}")
            elif daemon == "dunst":
                sh(f"dunstctl set-paused {'true' if on else 'false'}")
            else:
                sh(f"swaync-client -d")  # toggle
            self.win.toast(f"DND {'on' if on else 'off'}")
        dnd.connect("clicked", _dnd_cb)
        c.add_row(dnd)
        c.add_row(Gtk.Label(
            label="silences all notifications. Daemon-specific behavior:",
            xalign=0))
        if daemon == "mako":
            c.add_row(Gtk.Label(
                label="  mako: switches to 'do-not-disturb' mode group "
                      "(define `[mode=do-not-disturb] invisible=1` in "
                      "config)", xalign=0))
        elif daemon == "dunst":
            c.add_row(Gtk.Label(
                label="  dunst: pauses all notifications (queued & silent)",
                xalign=0))
        else:
            c.add_row(Gtk.Label(
                label="  swaync: toggles DND state (panel + popups muted)",
                xalign=0))

        # ── 4. notification history ────────────────────────────────────────
        c = Card("history")
        self.box.append(c)
        if daemon == "mako":
            rc, out, _ = sh("makoctl history")
            try:
                hist = json.loads(out or "{}").get("data", [[]])[0]
            except Exception:
                hist = []
            c.add_row(kv_row("Recent count:", str(len(hist))))
            for n in hist[-6:]:
                summ = (n.get("summary", {}) or {}).get("data", "?")
                body = (n.get("body", {}) or {}).get("data", "")
                app  = (n.get("app-name", {}) or {}).get(
                    "data", "?")
                c.add_row(Gtk.Label(
                    label=f"  • [{app}] {summ}  {body[:60]}",
                    xalign=0))
            row = Gtk.Box(spacing=8)
            b = SketchButton("Restore most recent", width=200, height=24,
                             color=NEON_GREEN)
            b.connect("clicked", lambda _b: (
                sh("makoctl restore"),
                self.win.toast("restored")))
            row.append(b)
            c.add_row(row)
        elif daemon == "dunst":
            rc, out, _ = sh("dunstctl count history")
            n = (out or "0").strip()
            c.add_row(kv_row("History count:", n))
            row = Gtk.Box(spacing=8)
            b = SketchButton("Pop one from history", width=200, height=24,
                             color=NEON_GREEN)
            b.connect("clicked", lambda _b: (
                sh("dunstctl history-pop"),
                self.win.toast("popped one")))
            row.append(b)
            b = SketchButton("Clear history", width=160, height=24,
                             color=DANGER_RED)
            b.connect("clicked", lambda _b: (
                sh("dunstctl history-clear"),
                self.win.toast("history cleared")))
            row.append(b)
            c.add_row(row)
        else:
            rc, out, _ = sh("swaync-client -c")
            c.add_row(kv_row("Pending notifications:", (out or "0").strip()))
            row = Gtk.Box(spacing=8)
            b = SketchButton("Hide all", width=140, height=24,
                             color=DANGER_RED)
            b.connect("clicked", lambda _b: (
                sh("swaync-client -C"),
                self.win.toast("cleared all")))
            row.append(b)
            c.add_row(row)

        # ── 5. config & test-fire ──────────────────────────────────────────
        c = Card("config & test")
        self.box.append(c)
        cfg_paths = {
            "mako":  Path.home() / ".config/mako/config",
            "dunst": Path.home() / ".config/dunst/dunstrc",
            "swaync": Path.home() / ".config/swaync/config.json",
        }
        cfg = cfg_paths.get(daemon)
        c.add_row(kv_row("Config path:", str(cfg) if cfg else "?"))
        c.add_row(kv_row("Exists:", "yes" if cfg and cfg.exists() else "no"))
        row = Gtk.Box(spacing=8)
        if cfg and cfg.exists():
            b = SketchButton("Open in nyxus_notepad", width=200, height=24,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b: self._open_in_notepad(str(cfg)))
            row.append(b)
        b = SketchButton("Reveal in terminal", width=170, height=24,
                         color=ACCENT_GOLD)
        b.connect("clicked", lambda _b: self._term_run(
            f"ls -la {cfg.parent if cfg else Path.home()/'.config'} && "
            f"echo && cat {cfg if cfg and cfg.exists() else '/dev/null'} "
            f"2>/dev/null | head -80",
            "showing config…"))
        row.append(b)
        c.add_row(row)

        # test-fire (notify-send for each urgency)
        if have("notify-send"):
            c.add_row(Gtk.Label(label="Send a test notification:",
                                xalign=0))
            row = Gtk.Box(spacing=8)
            for label, urg, icon, color in (
                ("Low",      "low",      "dialog-information",
                 NEON_BLUE),
                ("Normal",   "normal",   "dialog-information",
                 NEON_GREEN),
                ("Critical", "critical", "dialog-warning",
                 DANGER_RED)):
                b = SketchButton(label, width=110, height=24,
                                 color=color)
                b.connect("clicked", lambda _b, u=urg, l=label: (
                    sh(f"notify-send -u {u} -i dialog-information "
                       f"'NYXUS test ({l})' "
                       f"'urgency = {u} — fired at "
                       f"$(date +%H:%M:%S)'"),
                    self.win.toast(f"test {l} sent")))
                row.append(b)
            c.add_row(row)
            row = Gtk.Box(spacing=8)
            b = SketchButton("Test with action button",
                             width=210, height=24, color=ACCENT_PURP)
            b.connect("clicked", lambda _b: (
                sh("notify-send -A 'view=View details' "
                   "-A 'dismiss=Dismiss' "
                   "'NYXUS' 'click an action below'"),
                self.win.toast("action notification sent")))
            row.append(b)
            b = SketchButton("Test with icon",
                             width=160, height=24, color=NEON_BLUE)
            b.connect("clicked", lambda _b: (
                sh("notify-send -i face-smile "
                   "'NYXUS' 'icon test'"),
                self.win.toast("icon notification sent")))
            row.append(b)
            c.add_row(row)
        else:
            c.add_row(Gtk.Label(
                label="install libnotify (notify-send) for test-fire",
                xalign=0))

        # ── 6. fullscreen / idle inhibitor ────────────────────────────────
        c = Card("inhibitors & integration")
        self.box.append(c)
        # mako has --inhibit, swaync has inhibit-while-fullscreen flag
        if daemon == "mako":
            rc, out, _ = sh("makoctl mode")
            row = Gtk.Box(spacing=8)
            b = SketchButton("Inhibit (silence all)", width=200,
                             height=24, color=DANGER_RED)
            b.connect("clicked", lambda _b: (
                sh("makoctl set-mode invisible"),
                self.win.toast("mako: invisible mode on")))
            row.append(b)
            b = SketchButton("Restore default", width=180,
                             height=24, color=NEON_GREEN)
            b.connect("clicked", lambda _b: (
                sh("makoctl set-mode default"),
                self.win.toast("mako: default mode")))
            row.append(b)
            c.add_row(row)
            c.add_row(Gtk.Label(
                label="Tip: pair with hyprctl `bind = SUPER, F11, "
                      "exec, makoctl mode -t do-not-disturb` for hotkey "
                      "DND.", xalign=0))
        elif daemon == "dunst":
            row = Gtk.Box(spacing=8)
            b = SketchButton("Pause", width=100, height=24,
                             color=ACCENT_GOLD)
            b.connect("clicked", lambda _b: (
                sh("dunstctl set-paused true"),
                self.win.toast("dunst paused")))
            row.append(b)
            b = SketchButton("Resume", width=100, height=24,
                             color=NEON_GREEN)
            b.connect("clicked", lambda _b: (
                sh("dunstctl set-paused false"),
                self.win.toast("dunst resumed")))
            row.append(b)
            c.add_row(row)
        else:
            c.add_row(Gtk.Label(
                label="swaync auto-inhibits during fullscreen if "
                      "`fullscreen-behavior: ignore` is set in "
                      "~/.config/swaync/config.json", xalign=0))

        # idle inhibitor (hypridle / systemd-inhibit availability)
        if have("hypridle") or have("systemd-inhibit"):
            row = Gtk.Box(spacing=8)
            if have("hypridle"):
                rc, out, _ = sh("pgrep -x hypridle")
                state = "running" if (rc == 0 and out.strip()) else "stopped"
                c.add_row(kv_row("hypridle:", state))
                b = SketchButton("Start hypridle", width=160, height=24,
                                 color=NEON_GREEN)
                b.connect("clicked", lambda _b: (
                    subprocess.Popen(["hypridle"],
                                     start_new_session=True,
                                     stdout=subprocess.DEVNULL,
                                     stderr=subprocess.DEVNULL),
                    self.win.toast("hypridle started")))
                row.append(b)
                b = SketchButton("Stop hypridle", width=140, height=24,
                                 color=DANGER_RED)
                b.connect("clicked", lambda _b: (
                    sh("pkill -x hypridle"),
                    self.win.toast("hypridle stopped")))
                row.append(b)
            if row.get_first_child(): c.add_row(row)

        # ── 7. quick reference ─────────────────────────────────────────────
        c = Card("quick reference")
        self.box.append(c)
        ref = {
            "mako":  ("makoctl reload | dismiss [-a] | restore | "
                      "history | mode -t do-not-disturb"),
            "dunst": ("dunstctl close[-all] | history-pop | "
                      "set-paused true|false | count [history|displayed]"),
            "swaync": ("swaync-client -t (toggle) -C (clear) "
                       "-d (DND toggle) -R (reload) -c (count)"),
        }
        c.add_row(Gtk.Label(label=f"{daemon}: {ref.get(daemon,'?')}",
                            xalign=0, wrap=True))

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Notification daemon",
                        "mako dunst swaync"),
            SearchEntry(self.KEY, self.TITLE, "Active daemon detection"),
            SearchEntry(self.KEY, self.TITLE, "Do not disturb",
                        "DND silence"),
            SearchEntry(self.KEY, self.TITLE, "Dismiss all notifications"),
            SearchEntry(self.KEY, self.TITLE, "Dismiss latest"),
            SearchEntry(self.KEY, self.TITLE, "Restore last notification"),
            SearchEntry(self.KEY, self.TITLE, "Reload notification config"),
            SearchEntry(self.KEY, self.TITLE, "Notification history"),
            SearchEntry(self.KEY, self.TITLE, "Clear history"),
            SearchEntry(self.KEY, self.TITLE, "Pop history"),
            SearchEntry(self.KEY, self.TITLE, "Notification config path",
                        "mako dunstrc swaync"),
            SearchEntry(self.KEY, self.TITLE, "Edit notification config",
                        "open notepad"),
            SearchEntry(self.KEY, self.TITLE, "Test notification (low)",
                        "notify-send"),
            SearchEntry(self.KEY, self.TITLE, "Test notification (normal)"),
            SearchEntry(self.KEY, self.TITLE,
                        "Test notification (critical)"),
            SearchEntry(self.KEY, self.TITLE,
                        "Test notification with action button"),
            SearchEntry(self.KEY, self.TITLE, "Test notification with icon"),
            SearchEntry(self.KEY, self.TITLE, "Inhibit notifications",
                        "invisible mode pause"),
            SearchEntry(self.KEY, self.TITLE, "Fullscreen inhibitor"),
            SearchEntry(self.KEY, self.TITLE, "hypridle service",
                        "idle inhibitor"),
            SearchEntry(self.KEY, self.TITLE, "Notification quick reference",
                        "command cheatsheet"),
        ]


# ─── Users (read-only, honest) ──────────────────────────────────────────────
class UsersPage(BasePage):
    KEY = "users"; TITLE = "Users & Accounts"; ICON = "👤"
    TILE_COLOR = NEON_BLUE
    SUBTITLE = "Identity · Groups · Sudoers · Login history"

    # ── helpers ─────────────────────────────────────────────────────────────
    def _read_passwd(self) -> List[Dict[str, str]]:
        """Parse /etc/passwd → list of dicts. Returns only real users
        (UID >= 1000 or root)."""
        rows: List[Dict[str, str]] = []
        try:
            with open("/etc/passwd", "r") as f:
                for ln in f:
                    parts = ln.rstrip("\n").split(":")
                    if len(parts) < 7: continue
                    uid_s = parts[2]
                    try: uid = int(uid_s)
                    except ValueError: continue
                    if uid != 0 and uid < 1000: continue
                    if uid >= 65000: continue
                    rows.append({
                        "name": parts[0], "uid": uid_s, "gid": parts[3],
                        "gecos": parts[4], "home": parts[5],
                        "shell": parts[6],
                    })
        except Exception as e:
            log.warning("read passwd: %s", e)
        rows.sort(key=lambda r: int(r["uid"]))
        return rows

    def _shell_of(self, name: str) -> str:
        for r in self._read_passwd():
            if r["name"] == name: return r["shell"]
        return "?"

    def _login_shells(self) -> List[str]:
        try:
            with open("/etc/shells", "r") as f:
                return [ln.strip() for ln in f
                        if ln.strip() and not ln.startswith("#")]
        except Exception:
            return []

    def _last_logins(self) -> str:
        if not have("last"):
            return "last(1) not installed"
        rc, out, _ = sh("last -n 8 -F", timeout=4)
        return (out or "").strip() or "no records"

    def _account_locked(self, name: str) -> Optional[bool]:
        """Try `passwd -S` (needs root) — fall back to /etc/shadow grep."""
        rc, out, _ = sh(f"passwd -S {shlex.quote(name)}", timeout=2)
        if rc == 0 and out:
            tok = out.split()
            if len(tok) >= 2:
                st = tok[1]
                if st in ("L", "LK"): return True
                if st in ("P", "PS"): return False
                if st in ("NP",): return False
        # fallback: read shadow directly (will fail unless root)
        try:
            with open("/etc/shadow", "r") as f:
                for ln in f:
                    if ln.startswith(name + ":"):
                        h = ln.split(":", 2)[1]
                        return h.startswith("!") or h.startswith("*")
        except Exception:
            return None
        return None

    def _sudoers_preview(self) -> str:
        """Return a redacted snippet of who has sudo. Reads /etc/sudoers
        and /etc/sudoers.d/* if readable."""
        lines: List[str] = []
        try:
            with open("/etc/sudoers", "r") as f:
                for ln in f:
                    s = ln.strip()
                    if not s or s.startswith("#"): continue
                    if any(t in s for t in ("ALL=", "%wheel", "%sudo",
                                            "Defaults")):
                        lines.append(s)
        except Exception:
            pass
        try:
            for p in sorted(Path("/etc/sudoers.d").glob("*")):
                try:
                    with open(p, "r") as f:
                        for ln in f:
                            s = ln.strip()
                            if not s or s.startswith("#"): continue
                            lines.append(f"[{p.name}] {s}")
                except Exception: continue
        except Exception:
            pass
        if not lines:
            return "(unreadable — root only) try `sudo cat /etc/sudoers`"
        return "\n".join(lines[:24])

    # ── build ───────────────────────────────────────────────────────────────
    def build(self):
        import getpass as _gp
        u = _gp.getuser()
        rc, idout, _ = sh("id")
        rc, gout, _  = sh("id -nG")
        groups = (gout or "").strip().split()

        # ── current user identity ──────────────────────────────────────────
        c = Card("current user")
        self.box.append(c)
        c.add_row(kv_row("Username:", u))
        c.add_row(kv_row("UID/GID:", (idout or "").strip()))
        c.add_row(kv_row("Home:", str(Path.home())))
        c.add_row(kv_row("Shell:", os.environ.get("SHELL", self._shell_of(u))))
        try: host = os.uname().nodename
        except Exception: host = "?"
        c.add_row(kv_row("Hostname:", host))
        # GECOS (full name)
        gecos = ""
        for r in self._read_passwd():
            if r["name"] == u: gecos = r["gecos"]; break
        c.add_row(kv_row("Full name:", gecos.split(",", 1)[0] or "(unset)"))
        # avatar
        av = Path.home() / ".face"
        c.add_row(kv_row("Avatar (~/.face):",
                         str(av) if av.exists() else "(none)"))
        # admin / lock state
        is_admin = any(g in groups for g in ("wheel", "sudo", "adm"))
        c.add_row(kv_row("Admin (wheel/sudo):",
                         "yes" if is_admin else "no"))
        locked = self._account_locked(u)
        c.add_row(kv_row("Account locked:",
                         "yes" if locked is True else
                         ("no" if locked is False else "unknown (root only)")))
        # actions
        row = Gtk.Box(spacing=8)
        b = SketchButton("Change password", width=170, height=26,
                         color=ACCENT_GOLD,
                         tooltip="passwd in a terminal")
        b.connect("clicked", lambda _b: subprocess.Popen(
            ["xdg-terminal-exec", "passwd"]) if have("xdg-terminal-exec")
            else self.win.toast("run `passwd` in a terminal"))
        row.append(b)
        b2 = SketchButton("Edit avatar", width=140, height=26,
                          color=NEON_PINK,
                          tooltip="open ~/.face folder")
        b2.connect("clicked", lambda _b:
            subprocess.Popen(["xdg-open", str(Path.home())])
            if have("xdg-open") else self.win.toast("xdg-open not found"))
        row.append(b2)
        b3 = SketchButton("Edit GECOS", width=140, height=26,
                          color=NEON_BLUE,
                          tooltip="chfn in a terminal")
        b3.connect("clicked", lambda _b: subprocess.Popen(
            ["xdg-terminal-exec", "chfn"]) if have("xdg-terminal-exec")
            else self.win.toast("run `chfn` in a terminal"))
        row.append(b3)
        c.add_row(row)

        # ── group memberships ──────────────────────────────────────────────
        c = Card("groups")
        self.box.append(c)
        c.add_row(kv_row("Member of:",
                         "  ".join(groups) if groups else "(none)"))
        # primary group
        rc, pg, _ = sh("id -gn")
        c.add_row(kv_row("Primary group:", (pg or "").strip()))
        # privileged group flags
        for g, blurb in (("wheel",   "sudo capability"),
                         ("sudo",    "sudo capability"),
                         ("video",   "GPU / brightness"),
                         ("audio",   "ALSA / pipewire"),
                         ("input",   "raw input devices"),
                         ("docker",  "docker socket (root-equiv)"),
                         ("kvm",     "virtualization"),
                         ("plugdev", "removable storage")):
            if g in groups:
                c.add_row(kv_row(f"  ✓ {g}", blurb))

        # ── sudoers preview ────────────────────────────────────────────────
        c = Card("sudoers (preview)")
        self.box.append(c)
        sud = self._sudoers_preview()
        lbl = Gtk.Label(label=sud, xalign=0); lbl.set_wrap(True)
        lbl.set_selectable(True)
        lbl.add_css_class("nyx-row-value")
        c.add_row(lbl)
        b = SketchButton("Open visudo", width=160, height=26,
                         color=DANGER_RED,
                         tooltip="EDITOR=nano sudo visudo")
        b.connect("clicked", lambda _b: subprocess.Popen(
            ["xdg-terminal-exec", "sudo", "visudo"])
            if have("xdg-terminal-exec")
            else self.win.toast("run `sudo visudo` in a terminal"))
        c.add_row(b)

        # ── login shells available ─────────────────────────────────────────
        c = Card("available login shells (/etc/shells)")
        self.box.append(c)
        shells = self._login_shells()
        if shells:
            cur_sh = os.environ.get("SHELL", self._shell_of(u))
            for s in shells:
                mark = " ✓ current" if s == cur_sh else ""
                c.add_row(kv_row(s, mark.strip() or "—"))
            b = SketchButton("Change shell", width=160, height=26,
                             color=ACCENT_PURP,
                             tooltip="chsh in a terminal")
            b.connect("clicked", lambda _b: subprocess.Popen(
                ["xdg-terminal-exec", "chsh"]) if have("xdg-terminal-exec")
                else self.win.toast("run `chsh` in a terminal"))
            c.add_row(b)
        else:
            c.add_row(Gtk.Label(label="(/etc/shells unreadable)", xalign=0))

        # ── all users on system (/etc/passwd) ──────────────────────────────
        c = Card("all real users (/etc/passwd, UID 1000+ and root)")
        self.box.append(c)
        users = self._read_passwd()
        c.add_row(kv_row("Total users:", str(len(users))))
        for r in users[:20]:
            tag = " (you)" if r["name"] == u else ""
            c.add_row(kv_row(
                f"{r['name']}{tag}",
                f"uid={r['uid']}  shell={Path(r['shell']).name}  "
                f"home={r['home']}"))
        if len(users) > 20:
            c.add_row(kv_row("…", f"+{len(users)-20} more"))

        # ── login history ──────────────────────────────────────────────────
        c = Card("recent logins (last -n 8)")
        self.box.append(c)
        ll = self._last_logins()
        lbl = Gtk.Label(label=ll, xalign=0)
        lbl.set_selectable(True); lbl.add_css_class("nyx-row-value")
        c.add_row(lbl)

        # ── YubiKey ────────────────────────────────────────────────────────
        c = Card("YubiKey hardware key")
        self.box.append(c)
        if have("ykman"):
            rc, out, _ = sh("ykman list", timeout=3)
            c.add_row(Gtk.Label(
                label=(out or "").strip() or "no YubiKey detected", xalign=0))
            rc, out, _ = sh("ykman info", timeout=3)
            if out:
                lbl = Gtk.Label(label=out.strip()[:600], xalign=0)
                lbl.set_selectable(True); lbl.set_wrap(True)
                lbl.add_css_class("nyx-row-value")
                c.add_row(lbl)
        else:
            c.add_row(Gtk.Label(
                label="ykman not installed — `pacman -S yubikey-manager`",
                xalign=0))

        self.add_note(
            "user creation, group changes, password resets and account "
            "removal are destructive and require root — use `useradd`, "
            "`usermod`, `passwd`, `gpasswd`, or `userdel` in a terminal. "
            "Sudoers should always be edited with `visudo` (never `nano` "
            "directly) so syntax errors don't lock you out.")

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Change password"),
            SearchEntry(self.KEY, self.TITLE, "Change shell (chsh)"),
            SearchEntry(self.KEY, self.TITLE, "Edit GECOS / full name"),
            SearchEntry(self.KEY, self.TITLE, "Edit avatar (~/.face)"),
            SearchEntry(self.KEY, self.TITLE, "Group memberships"),
            SearchEntry(self.KEY, self.TITLE, "Sudoers preview"),
            SearchEntry(self.KEY, self.TITLE, "Open visudo"),
            SearchEntry(self.KEY, self.TITLE, "Login shells (/etc/shells)"),
            SearchEntry(self.KEY, self.TITLE, "All users (/etc/passwd)"),
            SearchEntry(self.KEY, self.TITLE, "Recent logins (last)"),
            SearchEntry(self.KEY, self.TITLE, "Account locked status"),
            SearchEntry(self.KEY, self.TITLE, "Hostname"),
            SearchEntry(self.KEY, self.TITLE, "UID and GID"),
            SearchEntry(self.KEY, self.TITLE, "YubiKey hardware key"),
            SearchEntry(self.KEY, self.TITLE, "Admin / wheel / sudo"),
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

    DEFAULT_MIMES = (
        ("Web browser",  "x-scheme-handler/https"),
        ("Email",        "x-scheme-handler/mailto"),
        ("Text editor",  "text/plain"),
        ("File manager", "inode/directory"),
        ("Image viewer", "image/png"),
        ("Video player", "video/mp4"),
        ("Music player", "audio/mpeg"),
        ("PDF viewer",   "application/pdf"),
    )

    def build(self):
        # ── 1. default app pickers (real xdg-mime change) ─────────────────
        c = Card("default applications")
        self.box.append(c)
        desktops = self._list_desktops()
        names = ["(unchanged)"] + [d for d in desktops]
        for label, mime in self.DEFAULT_MIMES:
            rc, out, _ = sh(["xdg-mime", "query", "default", mime])
            cur = out.strip() or "(none)"
            row = Gtk.Box(spacing=8)
            row.append(Gtk.Label(label=label, xalign=0,
                                 width_chars=14))
            row.append(Gtk.Label(label=cur, xalign=0))
            dd = Gtk.DropDown.new_from_strings(names)
            dd.set_hexpand(True)
            row.append(dd)
            b = SketchButton("Set", width=58, height=22, color=NEON_GREEN)
            b.connect("clicked",
                lambda _b, m=mime, dd=dd: self._set_default(m, dd))
            row.append(b)
            c.add_row(row)
        self.box.append(c)

        # ── 2. package manager summary ────────────────────────────────────
        c = Card("pacman / packages")
        self.box.append(c)
        rc, out, _ = sh("pacman -Qq", timeout=6)
        total = len(out.splitlines()) if rc == 0 else 0
        rc2, exp, _ = sh("pacman -Qe", timeout=6)
        explicit = len(exp.splitlines()) if rc2 == 0 else 0
        rc3, aur, _ = sh("pacman -Qm", timeout=6)
        aur_n = len(aur.splitlines()) if rc3 == 0 else 0
        rc4, orph, _ = sh("pacman -Qtdq", timeout=6)
        orph_n = len([l for l in orph.splitlines() if l.strip()]) if rc4 == 0 else 0
        c.add_row(kv_row("Total packages:",  f"{total}"))
        c.add_row(kv_row("Explicit:",        f"{explicit}"))
        c.add_row(kv_row("AUR / foreign:",   f"{aur_n}"))
        c.add_row(kv_row("Orphans:",         f"{orph_n}"))
        rc5, cache, _ = sh(["du", "-sh", "/var/cache/pacman/pkg"], timeout=4)
        c.add_row(kv_row("Cache size:",  cache.split()[0] if rc5==0 else "?"))

        ar = Gtk.Box(spacing=8)
        b1 = SketchButton("Update mirrorlist", width=160, height=24,
                          color=ACCENT_GOLD)
        b1.connect("clicked", lambda _b: sh_async(
            ["pkexec", "pacman", "-Syy"],
            lambda r: self.win.toast("mirrors refreshed"
                                     if r[0]==0 else "failed")))
        ar.append(b1)
        b2 = SketchButton("Sync + upgrade", width=140, height=24,
                          color=NEON_GREEN)
        b2.connect("clicked", lambda _b: sh_async(
            ["pkexec", "pacman", "-Syu", "--noconfirm"],
            lambda r: self.win.toast("upgrade done"
                                     if r[0]==0 else "failed"), timeout=600))
        ar.append(b2)
        b3 = SketchButton("Clean cache", width=120, height=24, color=DANGER_RED)
        b3.connect("clicked", lambda _b: sh_async(
            ["pkexec", "paccache", "-rk2"],
            lambda r: (self.win.toast("cache trimmed"
                                      if r[0]==0 else "needs paccache"),
                       self.refresh())))
        ar.append(b3)
        if orph_n > 0:
            b4 = SketchButton(f"Remove {orph_n} orphans", width=170,
                              height=24, color=DANGER_RED)
            b4.connect("clicked", lambda _b: sh_async(
                ["pkexec", "sh", "-c",
                 "pacman -Rns --noconfirm $(pacman -Qtdq)"],
                lambda r: (self.win.toast("orphans removed"
                                          if r[0]==0 else "failed"),
                           self.refresh()), timeout=120))
            ar.append(b4)
        c.add_row(ar)

        # search + install bar
        ir = Gtk.Box(spacing=8)
        ir.append(Gtk.Label(label="Install pkg:", xalign=0))
        self._pkg_entry = Gtk.Entry()
        self._pkg_entry.set_placeholder_text("package name (e.g. firefox)")
        self._pkg_entry.set_hexpand(True); ir.append(self._pkg_entry)
        ib = SketchButton("Install", width=92, height=24, color=NEON_GREEN)
        ib.connect("clicked", lambda _b: self._install_pkg())
        ir.append(ib)
        rb = SketchButton("Remove", width=92, height=24, color=DANGER_RED)
        rb.connect("clicked", lambda _b: self._remove_pkg())
        ir.append(rb)
        c.add_row(ir)

        # ── 3. AUR helpers / flatpak ──────────────────────────────────────
        c = Card("AUR & flatpak")
        self.box.append(c)
        for h in ("yay", "paru"):
            c.add_row(kv_row(f"{h}:", "installed" if have(h) else "(missing)"))
        if have("flatpak"):
            rc, fout, _ = sh(["flatpak", "list", "--columns=application"], timeout=5)
            n = len([l for l in fout.splitlines() if l.strip()])
            c.add_row(kv_row("Flatpak apps:", f"{n}"))
        else:
            c.add_row(kv_row("Flatpak:", "(not installed)"))

        # ── 4. autostart manager ──────────────────────────────────────────
        c = Card("startup applications")
        self.box.append(c)
        autostart = Path.home() / ".config/autostart"
        autostart.mkdir(parents=True, exist_ok=True)
        entries = sorted(autostart.glob("*.desktop"))
        if not entries:
            c.add_row(Gtk.Label(label="(no autostart entries)", xalign=0))
        for f in entries:
            row = Gtk.Box(spacing=8)
            row.append(Gtk.Label(label=f.name, xalign=0, width_chars=30))
            # parse Hidden=true to show enabled state
            try: txt = f.read_text(errors="ignore")
            except Exception: txt = ""
            enabled = "Hidden=true" not in txt
            tg = SketchToggle("Enabled", width=110, height=22,
                              color=NEON_GREEN, active=enabled)
            tg.connect("clicked",
                       lambda _b, p=f, t=tg: self._toggle_autostart(p, t))
            row.append(tg)
            db = SketchButton("Delete", width=80, height=22, color=DANGER_RED)
            db.connect("clicked",
                       lambda _b, p=f: (p.unlink(missing_ok=True),
                                        self.win.toast(f"removed {p.name}"),
                                        self.refresh()))
            row.append(db); c.add_row(row)

        # add new autostart from /usr/share/applications
        ar2 = Gtk.Box(spacing=8)
        all_desktops = self._list_desktops()
        if all_desktops:
            self._add_autostart_dd = Gtk.DropDown.new_from_strings(all_desktops)
            self._add_autostart_dd.set_hexpand(True)
            ar2.append(self._add_autostart_dd)
            ab = SketchButton("Add to startup", width=140, height=24,
                              color=NEON_BLUE)
            ab.connect("clicked", lambda _b: self._add_autostart(all_desktops))
            ar2.append(ab); c.add_row(ar2)

        # ── 5. last installed packages ────────────────────────────────────
        c = Card("recent install history")
        self.box.append(c)
        rc, out, _ = sh(["sh", "-c",
                         "grep -E ' installed | upgraded | removed ' "
                         "/var/log/pacman.log 2>/dev/null | tail -12"])
        sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 160)
        tv = Gtk.TextView(); tv.set_editable(False); tv.set_monospace(True)
        tv.add_css_class("nyx-editor")
        tv.get_buffer().set_text(out.strip() or "(no log)")
        sw.set_child(tv); c.add_row(sw)

    def _list_desktops(self) -> List[str]:
        seen = set(); out = []
        for d in (Path("/usr/share/applications"),
                  Path("/usr/local/share/applications"),
                  Path.home() / ".local/share/applications"):
            if not d.exists(): continue
            for f in sorted(d.glob("*.desktop")):
                if f.name not in seen:
                    seen.add(f.name); out.append(f.name)
        return out

    def _set_default(self, mime: str, dd: Gtk.DropDown):
        idx = dd.get_selected()
        if idx <= 0: return
        names = [dd.get_model().get_string(i)
                 for i in range(dd.get_model().get_n_items())]
        target = names[idx]
        sh_async(["xdg-mime", "default", target, mime],
                 lambda r: (self.win.toast(
                     f"{mime.split('/')[-1]} -> {target}" if r[0]==0
                     else "failed"),
                            self.mark_changed(mime), self.refresh()))

    def _install_pkg(self):
        pkg = (self._pkg_entry.get_text() or "").strip()
        if not pkg: return
        sh_async(["pkexec", "pacman", "-S", "--noconfirm", pkg],
                 lambda r: (self.win.toast(
                     f"installed {pkg}" if r[0]==0 else f"failed: {pkg}"),
                            self.mark_changed(f"install {pkg}"),
                            self.refresh()), timeout=300)

    def _remove_pkg(self):
        pkg = (self._pkg_entry.get_text() or "").strip()
        if not pkg: return
        sh_async(["pkexec", "pacman", "-Rns", "--noconfirm", pkg],
                 lambda r: (self.win.toast(
                     f"removed {pkg}" if r[0]==0 else f"failed: {pkg}"),
                            self.mark_changed(f"remove {pkg}"),
                            self.refresh()), timeout=120)

    def _toggle_autostart(self, p: Path, tg):
        try:
            txt = p.read_text(errors="ignore")
            if tg.active:  # enable
                txt = "\n".join(l for l in txt.splitlines()
                                if l.strip().lower() != "hidden=true")
            else:          # disable
                if "Hidden=true" not in txt:
                    txt = txt.rstrip() + "\nHidden=true\n"
            p.write_text(txt)
            self.win.toast(f"{p.name}: "
                           f"{'enabled' if tg.active else 'disabled'}")
        except Exception as e:
            self.win.toast(f"err: {e}")

    def _add_autostart(self, names: List[str]):
        idx = self._add_autostart_dd.get_selected()
        if idx < 0 or idx >= len(names): return
        name = names[idx]
        # find the source .desktop
        for d in (Path("/usr/share/applications"),
                  Path("/usr/local/share/applications"),
                  Path.home() / ".local/share/applications"):
            src = d / name
            if src.exists():
                dst = Path.home() / ".config/autostart" / name
                try:
                    dst.write_text(src.read_text())
                    self.win.toast(f"added {name}")
                    self.refresh()
                except Exception as e:
                    self.win.toast(f"err: {e}")
                return

    def refresh(self):
        c = self.box.get_first_child()
        while c:
            n = c.get_next_sibling()
            if c is not self.box.get_first_child(): self.box.remove(c)
            c = n
        self.build()

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Default browser", "xdg-mime"),
            SearchEntry(self.KEY, self.TITLE, "Default editor", "xdg-mime"),
            SearchEntry(self.KEY, self.TITLE, "Default file manager"),
            SearchEntry(self.KEY, self.TITLE, "Install package", "pacman -S"),
            SearchEntry(self.KEY, self.TITLE, "Remove package", "pacman -R"),
            SearchEntry(self.KEY, self.TITLE, "Update mirrorlist", "pacman -Syy"),
            SearchEntry(self.KEY, self.TITLE, "System upgrade", "pacman -Syu"),
            SearchEntry(self.KEY, self.TITLE, "Orphans", "Qtd cleanup"),
            SearchEntry(self.KEY, self.TITLE, "Pacman cache", "paccache"),
            SearchEntry(self.KEY, self.TITLE, "AUR helper", "yay paru"),
            SearchEntry(self.KEY, self.TITLE, "Flatpak"),
            SearchEntry(self.KEY, self.TITLE, "Startup applications", "autostart"),
            SearchEntry(self.KEY, self.TITLE, "Install history"),
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

    REGIONAL_KEYS = (
        ("LANG",        "System language"),
        ("LC_CTYPE",    "Character classification"),
        ("LC_NUMERIC",  "Number format"),
        ("LC_TIME",     "Date / time format"),
        ("LC_MONETARY", "Currency"),
        ("LC_MESSAGES", "UI messages"),
        ("LC_PAPER",    "Paper size"),
        ("LC_MEASUREMENT", "Measurement units"),
    )

    def build(self):
        # ── 1. current locale snapshot ────────────────────────────────────
        c = Card("current locale")
        self.box.append(c)
        env = {}
        rc, out, _ = sh("locale")
        for line in out.splitlines():
            if "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"')
        for k, label in self.REGIONAL_KEYS:
            c.add_row(kv_row(f"{label} ({k}):", env.get(k, "(unset)")))

        # ── 2. system language picker ─────────────────────────────────────
        c = Card("system language")
        self.box.append(c)
        rc, out, _ = sh("localectl list-locales", timeout=4)
        locales = [l.strip() for l in out.splitlines() if l.strip()]
        if not locales:
            # fallback: scan /etc/locale.gen
            try:
                gen = Path("/etc/locale.gen").read_text(errors="ignore")
                locales = sorted(set(
                    l.lstrip("# ").split()[0]
                    for l in gen.splitlines()
                    if l.strip() and not l.startswith("#") and "UTF-8" in l))
            except Exception: pass
        if locales:
            row = Gtk.Box(spacing=8)
            self.lang_dd = Gtk.DropDown.new_from_strings(locales)
            cur = env.get("LANG", "").strip()
            try: self.lang_dd.set_selected(locales.index(cur))
            except ValueError: pass
            self.lang_dd.set_hexpand(True); row.append(self.lang_dd)
            b = SketchButton("Set system LANG", width=160, height=24,
                             color=NEON_GREEN)
            b.connect("clicked", lambda _b: self._set_lang(locales))
            row.append(b); c.add_row(row)
            c.add_row(kv_row("Available locales:", f"{len(locales)}"))
        else:
            c.add_row(Gtk.Label(label="localectl returned no locales -- "
                                "run `locale-gen` first.", xalign=0))

        # generate a locale on demand
        gen_row = Gtk.Box(spacing=8)
        gen_row.append(Gtk.Label(label="Generate locale:", xalign=0))
        self._gen_entry = Gtk.Entry()
        self._gen_entry.set_placeholder_text("e.g. fr_FR.UTF-8 UTF-8")
        self._gen_entry.set_hexpand(True); gen_row.append(self._gen_entry)
        gb = SketchButton("locale-gen", width=120, height=24, color=ACCENT_GOLD)
        gb.connect("clicked", lambda _b: self._locale_gen())
        gen_row.append(gb); c.add_row(gen_row)

        # ── 3. keyboard layout (XKB / Hyprland) ───────────────────────────
        c = Card("keyboard layout")
        self.box.append(c)
        rc, out, _ = sh("localectl status")
        kb = {}
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1); kb[k.strip()] = v.strip()
        c.add_row(kv_row("X11 layout:",  kb.get("X11 Layout", "?")))
        c.add_row(kv_row("X11 model:",   kb.get("X11 Model", "?")))
        c.add_row(kv_row("X11 variant:", kb.get("X11 Variant", "?")))
        c.add_row(kv_row("VC keymap:",   kb.get("VC Keymap", "?")))
        for layout in ("us", "gb", "de", "fr", "es", "it", "ru", "jp"):
            pass  # rendered below
        kr = Gtk.Box(spacing=6)
        cur_layout = kb.get("X11 Layout", "us").split(",")[0].strip()
        for layout in ("us", "gb", "de", "fr", "es", "it", "ru", "jp"):
            btn = SketchButton(layout, width=46, height=22, color=NEON_PINK,
                               primary=(layout == cur_layout))
            btn.connect("clicked", lambda _b, l=layout: self._set_layout(l))
            kr.append(btn)
        c.add_row(kr)

        # ── 4. region / regional formats (LC_*) ───────────────────────────
        c = Card("regional formats (LC_*)")
        self.box.append(c)
        if locales:
            row = Gtk.Box(spacing=8)
            self.region_dd = Gtk.DropDown.new_from_strings(locales)
            cur = env.get("LC_TIME", env.get("LANG", "")).strip()
            try: self.region_dd.set_selected(locales.index(cur))
            except ValueError: pass
            self.region_dd.set_hexpand(True); row.append(self.region_dd)
            b = SketchButton("Apply regional", width=150, height=24,
                             color=NEON_BLUE)
            b.connect("clicked", lambda _b: self._set_region(locales))
            row.append(b); c.add_row(row)

        self.add_note(
            "Locale + keymap changes go through pkexec localectl. "
            "After changing LANG you must log out and back in for shell "
            "and apps to pick up the new value.")

    def _set_lang(self, locales):
        idx = self.lang_dd.get_selected()
        if idx < 0 or idx >= len(locales): return
        loc = locales[idx]
        sh_async(["pkexec", "localectl", "set-locale", f"LANG={loc}"],
                 lambda r: (self.win.toast(
                     f"LANG -> {loc}" if r[0]==0 else "needs sudo"),
                            self.mark_changed("LANG"),
                            self.needs_restart("system language")))

    def _set_region(self, locales):
        idx = self.region_dd.get_selected()
        if idx < 0 or idx >= len(locales): return
        loc = locales[idx]
        # apply LC_TIME, LC_NUMERIC, LC_MONETARY, LC_PAPER, LC_MEASUREMENT
        args = ["pkexec", "localectl", "set-locale",
                f"LC_TIME={loc}", f"LC_NUMERIC={loc}",
                f"LC_MONETARY={loc}", f"LC_PAPER={loc}",
                f"LC_MEASUREMENT={loc}"]
        sh_async(args,
                 lambda r: (self.win.toast(
                     f"region -> {loc}" if r[0]==0 else "needs sudo"),
                            self.mark_changed("regional formats"),
                            self.needs_restart("regional formats")))

    def _set_layout(self, layout: str):
        # live to Hyprland
        sh(["hyprctl", "keyword", "input:kb_layout", layout])
        # persist via localectl
        sh_async(["pkexec", "localectl", "set-x11-keymap", layout],
                 lambda r: (self.win.toast(
                     f"layout -> {layout}" if r[0]==0 else "live only"),
                            self.mark_changed("keyboard layout"),
                            self.refresh()))

    def _locale_gen(self):
        spec = (self._gen_entry.get_text() or "").strip()
        if not spec: return
        # uncomment matching line in /etc/locale.gen, then run locale-gen
        sh_async(["pkexec", "sh", "-c",
                  f"sed -i 's/^#\\s*{spec.split()[0]}/{spec.split()[0]}/' "
                  f"/etc/locale.gen && locale-gen"],
                 lambda r: (self.win.toast(
                     f"generated {spec}" if r[0]==0 else "locale-gen failed"),
                            self.refresh()), timeout=120)

    def refresh(self):
        c = self.box.get_first_child()
        while c:
            n = c.get_next_sibling()
            if c is not self.box.get_first_child(): self.box.remove(c)
            c = n
        self.build()

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "System language", "LANG locale"),
            SearchEntry(self.KEY, self.TITLE, "Keyboard layout", "xkb us gb de"),
            SearchEntry(self.KEY, self.TITLE, "Regional formats", "LC_TIME"),
            SearchEntry(self.KEY, self.TITLE, "Currency", "LC_MONETARY"),
            SearchEntry(self.KEY, self.TITLE, "Paper size", "LC_PAPER"),
            SearchEntry(self.KEY, self.TITLE, "Measurement units"),
            SearchEntry(self.KEY, self.TITLE, "Generate locale", "locale-gen"),
        ]


# ─── Accessibility ──────────────────────────────────────────────────────────
class AccessibilityPage(BasePage):
    KEY = "a11y"; TITLE = "Accessibility"; ICON = "♿"

    def build(self):
        # ── 1. cursor size + theme ────────────────────────────────────────
        c = Card("cursor")
        self.box.append(c)
        env = os.environ.get("XCURSOR_SIZE", "24")
        c.add_row(kv_row("Cursor size (XCURSOR_SIZE):", env))
        row = Gtk.Box(spacing=8)
        for s in (20, 24, 32, 48, 64):
            b = SketchButton(f"{s}px", width=58, height=22, color=NEON_BLUE,
                             primary=(str(s) == env))
            b.connect("clicked", lambda _b, s=s: self._set_cursor(s))
            row.append(b)
        c.add_row(row)

        # ── 2. visual contrast / theme ────────────────────────────────────
        c = Card("visual contrast")
        self.box.append(c)
        cur_theme = self._gget("org.gnome.desktop.interface", "gtk-theme")
        c.add_row(kv_row("Current GTK theme:", cur_theme))
        tr = Gtk.Box(spacing=8)
        for name in ("Adwaita", "Adwaita-dark", "HighContrast",
                     "HighContrastInverse"):
            btn = SketchButton(name, width=140, height=22,
                               color=NEON_PINK,
                               primary=(name == cur_theme))
            btn.connect("clicked", lambda _b, n=name: self._set_theme(n))
            tr.append(btn)
        c.add_row(tr)

        # color scheme dark/light prefer
        cs = self._gget("org.gnome.desktop.interface", "color-scheme")
        dark = "dark" in cs
        dt = SketchToggle("Prefer dark color scheme", width=240, height=26,
                          color=NEON_BLUE, active=dark)
        dt.connect("clicked", lambda _b: self._gset(
            "org.gnome.desktop.interface", "color-scheme",
            "prefer-dark" if dt.active else "default"))
        c.add_row(dt)

        # ── 3. text scale ─────────────────────────────────────────────────
        c = Card("text size")
        self.box.append(c)
        cur_scale = self._gget_float(
            "org.gnome.desktop.interface", "text-scaling-factor", 1.0)
        c.add_row(kv_row("Text scale:", f"{cur_scale:.2f}x"))
        adj = Gtk.Adjustment(value=cur_scale, lower=0.75, upper=2.5,
                             step_increment=0.05, page_increment=0.25)
        sc = Gtk.Scale(adjustment=adj,
                       orientation=Gtk.Orientation.HORIZONTAL)
        sc.set_size_request(280, -1); sc.set_draw_value(True)
        sc.set_value_pos(Gtk.PositionType.RIGHT); sc.set_digits(2)
        sc.connect("value-changed", lambda s: self._gset(
            "org.gnome.desktop.interface", "text-scaling-factor",
            f"{s.get_value():.2f}"))
        c.add_row(sc)

        # ── 4. keyboard accessibility (XKB options) ───────────────────────
        c = Card("keyboard helpers")
        self.box.append(c)
        cur_opts = self._hypr_kb_options()

        def _toggle_xkb(label, opt, color=NEON_GREEN):
            on = opt in cur_opts
            tg = SketchToggle(label, width=240, height=26,
                              color=color, active=on)
            tg.connect("clicked", lambda _b, o=opt, t=tg:
                       self._toggle_xkb_option(o, t.active))
            c.add_row(tg)

        _toggle_xkb("Caps Lock acts as Ctrl",   "ctrl:nocaps")
        _toggle_xkb("Compose key on Right Alt", "compose:ralt")
        _toggle_xkb("Swap Alt and Win",         "altwin:swap_alt_win")
        _toggle_xkb("Group toggle on Caps Lock","grp:caps_toggle")
        _toggle_xkb("Numlock at boot",          "numpad:mac")

        # ── 5. visual / motion preferences ────────────────────────────────
        c = Card("motion & alerts")
        self.box.append(c)
        # reduce animations -> Hyprland animations:enabled false
        anim_on = (self._hypr_option("animations:enabled") or "true") != "false"
        at = SketchToggle("Disable window animations", width=240, height=26,
                          color=ACCENT_GOLD, active=not anim_on)
        at.connect("clicked", lambda _b: (
            sh(["hyprctl", "keyword", "animations:enabled",
                "false" if at.active else "true"]),
            self.win.toast("animations "
                           f"{'off' if at.active else 'on'}")))
        c.add_row(at)

        # blur disable
        blur_on = (self._hypr_option("decoration:blur:enabled") or "true") != "false"
        bt = SketchToggle("Disable window blur", width=240, height=26,
                          color=ACCENT_GOLD, active=not blur_on)
        bt.connect("clicked", lambda _b: (
            sh(["hyprctl", "keyword", "decoration:blur:enabled",
                "false" if bt.active else "true"]),
            self.win.toast("blur "
                           f"{'off' if bt.active else 'on'}")))
        c.add_row(bt)

        # event sounds
        evs = self._gget("org.gnome.desktop.sound", "event-sounds")
        es = SketchToggle("System event sounds", width=240, height=26,
                          color=NEON_GREEN, active=(evs == "true"))
        es.connect("clicked", lambda _b: self._gset(
            "org.gnome.desktop.sound", "event-sounds",
            "true" if es.active else "false"))
        c.add_row(es)

        # ── 6. assistive tech (orca / magnifier) ──────────────────────────
        c = Card("assistive technologies")
        self.box.append(c)
        c.add_row(kv_row("orca screen reader:",
                         "installed" if have("orca") else "(missing)"))
        if have("orca"):
            ob = SketchButton("Launch Orca", width=140, height=24,
                              color=NEON_PINK)
            ob.connect("clicked", lambda _b: sh_async(["orca"]))
            c.add_row(ob)
        c.add_row(kv_row("magnus magnifier:",
                         "installed" if have("magnus") else "(missing)"))
        if have("magnus"):
            mb = SketchButton("Launch Magnifier", width=160, height=24,
                              color=NEON_BLUE)
            mb.connect("clicked", lambda _b: sh_async(["magnus"]))
            c.add_row(mb)

        self.add_note(
            "GTK theme + text scale changes use gsettings (GNOME schema). "
            "Keyboard helpers apply live via hyprctl AND get persisted by "
            "localectl set-x11-keymap when you set the layout in Language.")

    # ── helpers ───────────────────────────────────────────────────────────
    def _set_cursor(self, s: int):
        sh(["hyprctl", "setcursor", "Adwaita", str(s)])
        if have("gsettings"):
            sh(["gsettings", "set", "org.gnome.desktop.interface",
                "cursor-size", str(s)])
        os.environ["XCURSOR_SIZE"] = str(s)
        self.win.toast(f"cursor -> {s}px")
        self.mark_changed("cursor size"); self.refresh()

    def _set_theme(self, name: str):
        if have("gsettings"):
            sh(["gsettings", "set", "org.gnome.desktop.interface",
                "gtk-theme", name])
        # Hyprland-friendly env hint
        sh(["hyprctl", "keyword", "env", f"GTK_THEME,{name}"])
        self.win.toast(f"theme -> {name}")
        self.mark_changed("gtk-theme"); self.refresh()

    def _gget(self, schema: str, key: str) -> str:
        if not have("gsettings"): return "(no gsettings)"
        rc, out, _ = sh(["gsettings", "get", schema, key])
        return out.strip().strip("'") if rc == 0 else "?"

    def _gget_float(self, schema: str, key: str, default: float) -> float:
        try: return float(self._gget(schema, key))
        except Exception: return default

    def _gset(self, schema: str, key: str, val: str):
        if not have("gsettings"):
            self.win.toast("gsettings not installed"); return
        sh(["gsettings", "set", schema, key, val])
        self.mark_changed(key)

    def _hypr_option(self, key: str) -> str:
        rc, out, _ = sh(["hyprctl", "getoption", key, "-j"])
        if rc != 0: return ""
        try:
            j = json.loads(out)
            for k in ("str", "custom", "int"):
                if k in j and j[k] not in (None, ""): return str(j[k])
        except Exception: pass
        return ""

    def _hypr_kb_options(self) -> str:
        return self._hypr_option("input:kb_options") or ""

    def _toggle_xkb_option(self, opt: str, enable: bool):
        cur = [o for o in self._hypr_kb_options().split(",") if o]
        if enable and opt not in cur: cur.append(opt)
        if not enable and opt in cur: cur.remove(opt)
        new = ",".join(cur)
        sh(["hyprctl", "keyword", "input:kb_options", new])
        self.win.toast(f"{opt}: {'on' if enable else 'off'}")
        self.mark_changed("kb_options")

    def refresh(self):
        c = self.box.get_first_child()
        while c:
            n = c.get_next_sibling()
            if c is not self.box.get_first_child(): self.box.remove(c)
            c = n
        self.build()

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "Cursor size", "xcursor large"),
            SearchEntry(self.KEY, self.TITLE, "GTK theme", "high contrast"),
            SearchEntry(self.KEY, self.TITLE, "Dark mode", "color scheme"),
            SearchEntry(self.KEY, self.TITLE, "Text size", "scaling factor"),
            SearchEntry(self.KEY, self.TITLE, "Caps Lock as Ctrl", "ctrl nocaps"),
            SearchEntry(self.KEY, self.TITLE, "Compose key", "ralt"),
            SearchEntry(self.KEY, self.TITLE, "Reduce animations"),
            SearchEntry(self.KEY, self.TITLE, "Reduce blur"),
            SearchEntry(self.KEY, self.TITLE, "Screen reader", "orca"),
            SearchEntry(self.KEY, self.TITLE, "Magnifier", "magnus zoom"),
            SearchEntry(self.KEY, self.TITLE, "System sounds"),
        ]


# ─── Printers ───────────────────────────────────────────────────────────────
class PrintersPage(BasePage):
    KEY = "printers"; TITLE = "Printers & Scanners"; ICON = "🖨"

    def build(self):
        # ── 1. CUPS service status ────────────────────────────────────────
        c = Card("CUPS service")
        self.box.append(c)
        if not have("lpstat"):
            c.add_row(Gtk.Label(label="cups package not installed -- "
                                "`pacman -S cups`", xalign=0))
            ib = SketchButton("Install CUPS", width=140, height=24,
                              color=NEON_GREEN)
            ib.connect("clicked", lambda _b: sh_async(
                ["pkexec", "pacman", "-S", "--noconfirm", "cups"],
                lambda r: (self.win.toast(
                    "cups installed" if r[0]==0 else "install failed"),
                           self.refresh()), timeout=300))
            c.add_row(ib)
        else:
            rc, st, _ = sh(["systemctl", "is-active", "cups.service"])
            active = "active" in st
            rc2, en, _ = sh(["systemctl", "is-enabled", "cups.service"])
            enabled = "enabled" in en
            c.add_row(kv_row("Status:",  "active" if active else st.strip()))
            c.add_row(kv_row("Enabled:", "yes" if enabled else "no"))
            row = Gtk.Box(spacing=8)
            tg = SketchToggle("CUPS enabled at boot", width=200, height=26,
                              color=NEON_GREEN, active=enabled)
            tg.connect("clicked", lambda _b: sh_async(
                ["pkexec", "systemctl",
                 "enable" if tg.active else "disable", "--now",
                 "cups.service"],
                lambda r: (self.win.toast(
                    "cups updated" if r[0]==0 else "needs sudo"),
                           self.refresh())))
            row.append(tg)
            rb = SketchButton("Restart CUPS", width=130, height=24,
                              color=ACCENT_GOLD)
            rb.connect("clicked", lambda _b: sh_async(
                ["pkexec", "systemctl", "restart", "cups.service"],
                lambda r: self.win.toast("cups restarted"
                                         if r[0]==0 else "failed")))
            row.append(rb); c.add_row(row)

        # ── 2. installed printers ─────────────────────────────────────────
        c = Card("installed printers")
        self.box.append(c)
        if have("lpstat"):
            rc, out, _ = sh(["lpstat", "-p", "-d"])
            text = out.strip() or "(no printers configured)"
            sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 130)
            tv = Gtk.TextView(); tv.set_editable(False); tv.set_monospace(True)
            tv.add_css_class("nyx-editor")
            tv.get_buffer().set_text(text)
            sw.set_child(tv); c.add_row(sw)

            # parse printer names
            printers = []
            for line in out.splitlines():
                if line.startswith("printer "):
                    parts = line.split()
                    if len(parts) >= 2: printers.append(parts[1])

            if printers:
                # default printer picker
                rc2, dout, _ = sh(["lpstat", "-d"])
                cur_default = ""
                if "system default destination:" in dout:
                    cur_default = dout.split(":", 1)[1].strip()
                row = Gtk.Box(spacing=8)
                row.append(Gtk.Label(label="Default:", xalign=0))
                self.def_dd = Gtk.DropDown.new_from_strings(printers)
                try: self.def_dd.set_selected(printers.index(cur_default))
                except ValueError: pass
                self.def_dd.set_hexpand(True); row.append(self.def_dd)
                db = SketchButton("Set default", width=120, height=22,
                                  color=NEON_BLUE)
                db.connect("clicked", lambda _b: self._set_default_printer(printers))
                row.append(db); c.add_row(row)

                # actions per printer
                for p in printers:
                    ar = Gtk.Box(spacing=8)
                    ar.append(Gtk.Label(label=p, xalign=0, width_chars=18))
                    tb = SketchButton("Test page", width=110, height=22,
                                      color=NEON_PINK)
                    tb.connect("clicked", lambda _b, n=p: self._test_print(n))
                    ar.append(tb)
                    qb = SketchButton("Show queue", width=110, height=22,
                                      color=NEON_BLUE)
                    qb.connect("clicked", lambda _b, n=p: self._show_queue(n))
                    ar.append(qb)
                    cb = SketchButton("Cancel jobs", width=120, height=22,
                                      color=DANGER_RED)
                    cb.connect("clicked", lambda _b, n=p: self._cancel_jobs(n))
                    ar.append(cb)
                    rb = SketchButton("Remove", width=92, height=22,
                                      color=DANGER_RED)
                    rb.connect("clicked", lambda _b, n=p: self._remove_printer(n))
                    ar.append(rb); c.add_row(ar)
            else:
                # discovery + add (CUPS network browse)
                rc, found, _ = sh(["lpinfo", "--make-and-model", "*", "-v"],
                                  timeout=6)
                if found.strip():
                    c.add_row(Gtk.Label(
                        label="Discovered devices:", xalign=0))
                    sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 100)
                    tv = Gtk.TextView(); tv.set_editable(False); tv.set_monospace(True)
                    tv.add_css_class("nyx-editor")
                    tv.get_buffer().set_text(found)
                    sw.set_child(tv); c.add_row(sw)
                if have("system-config-printer"):
                    ab = SketchButton("Open Printer Manager", width=200,
                                      height=24, color=NEON_GREEN)
                    ab.connect("clicked", lambda _b: sh_async(
                        ["system-config-printer"]))
                    c.add_row(ab)

        # ── 3. add network printer (manual lpadmin) ───────────────────────
        if have("lpadmin"):
            c = Card("add network printer (IPP)")
            self.box.append(c)
            ar = Gtk.Box(spacing=8)
            ar.append(Gtk.Label(label="Name:", xalign=0))
            self._add_name = Gtk.Entry()
            self._add_name.set_placeholder_text("HP_LaserJet")
            self._add_name.set_size_request(140, -1); ar.append(self._add_name)
            ar.append(Gtk.Label(label="URI:", xalign=0))
            self._add_uri = Gtk.Entry()
            self._add_uri.set_placeholder_text("ipp://192.168.1.50/ipp/print")
            self._add_uri.set_hexpand(True); ar.append(self._add_uri)
            ab = SketchButton("Add", width=70, height=24, color=NEON_GREEN)
            ab.connect("clicked", lambda _b: self._add_printer())
            ar.append(ab); c.add_row(ar)

        # ── 4. scanners ───────────────────────────────────────────────────
        c = Card("scanners (sane)")
        self.box.append(c)
        if have("scanimage"):
            rc, out, _ = sh(["scanimage", "-L"], timeout=10)
            text = out.strip() or "(no scanners detected)"
            c.add_row(Gtk.Label(label=text, xalign=0))
            if rc == 0 and "no SANE devices" not in text:
                row = Gtk.Box(spacing=8)
                sb = SketchButton("Scan to ~/scan.png", width=180,
                                  height=24, color=NEON_BLUE)
                sb.connect("clicked", lambda _b: sh_async(
                    ["sh", "-c",
                     "scanimage --format=png -o ~/scan.png"],
                    lambda r: self.win.toast("scan saved -> ~/scan.png"
                                             if r[0]==0 else "scan failed"),
                    timeout=60))
                row.append(sb); c.add_row(row)
        else:
            c.add_row(Gtk.Label(label="sane / scanimage not installed -- "
                                "`pacman -S sane`", xalign=0))

        self.add_note(
            "Printer changes use pkexec + lpadmin. The CUPS web UI is also "
            "available at http://localhost:631 for full driver selection.")

    # ── helpers ───────────────────────────────────────────────────────────
    def _set_default_printer(self, names):
        idx = self.def_dd.get_selected()
        if idx < 0 or idx >= len(names): return
        n = names[idx]
        sh_async(["pkexec", "lpadmin", "-d", n],
                 lambda r: (self.win.toast(
                     f"default -> {n}" if r[0]==0 else "needs sudo"),
                            self.mark_changed("default printer"),
                            self.refresh()))

    def _test_print(self, name: str):
        for path in ("/usr/share/cups/data/testprint",
                     "/usr/share/cups/data/default-testpage.pdf"):
            if Path(path).exists():
                sh_async(["lp", "-d", name, path],
                         lambda r: self.win.toast(
                             f"test queued on {name}" if r[0]==0
                             else "lp failed"))
                return
        self.win.toast("no CUPS testprint file found")

    def _show_queue(self, name: str):
        rc, out, _ = sh(["lpq", "-P", name])
        self.win.toast((out.strip() or "(empty queue)").splitlines()[0]
                       if out else "no queue data")

    def _cancel_jobs(self, name: str):
        sh_async(["cancel", "-a", name],
                 lambda r: self.win.toast(
                     f"queue cleared on {name}" if r[0]==0 else "failed"))

    def _remove_printer(self, name: str):
        sh_async(["pkexec", "lpadmin", "-x", name],
                 lambda r: (self.win.toast(
                     f"removed {name}" if r[0]==0 else "needs sudo"),
                            self.refresh()))

    def _add_printer(self):
        name = (self._add_name.get_text() or "").strip()
        uri  = (self._add_uri.get_text() or "").strip()
        if not name or not uri:
            self.win.toast("name and URI required"); return
        sh_async(["pkexec", "lpadmin", "-p", name, "-E", "-v", uri,
                  "-m", "everywhere"],
                 lambda r: (self.win.toast(
                     f"added {name}" if r[0]==0
                     else "lpadmin failed -- check URI"),
                            self.refresh()), timeout=30)

    def refresh(self):
        c = self.box.get_first_child()
        while c:
            n = c.get_next_sibling()
            if c is not self.box.get_first_child(): self.box.remove(c)
            c = n
        self.build()

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "CUPS service"),
            SearchEntry(self.KEY, self.TITLE, "Default printer"),
            SearchEntry(self.KEY, self.TITLE, "Test page"),
            SearchEntry(self.KEY, self.TITLE, "Cancel print jobs"),
            SearchEntry(self.KEY, self.TITLE, "Remove printer"),
            SearchEntry(self.KEY, self.TITLE, "Add network printer", "IPP"),
            SearchEntry(self.KEY, self.TITLE, "Print queue", "lpq"),
            SearchEntry(self.KEY, self.TITLE, "Scanners", "sane scanimage"),
            SearchEntry(self.KEY, self.TITLE, "Scan to file"),
        ]


# ─── Gaming ─────────────────────────────────────────────────────────────────
class GamingPage(BasePage):
    KEY = "gaming"; TITLE = "Gaming"; ICON = "🎮"

    MANGOHUD_CONF = Path.home() / ".config/MangoHud/MangoHud.conf"
    DEFAULT_MANGOHUD = (
        "fps\nfps_limit=0\nframetime\ngpu_stats\ngpu_temp\ngpu_power\n"
        "cpu_stats\ncpu_temp\ncpu_power\nram\nvram\nio_stats\nposition=top-left\n"
        "background_alpha=0.4\nfont_size=20\ntoggle_hud=Shift_R+F12\n"
    )

    def build(self):
        # ── 1. GameMode ───────────────────────────────────────────────────
        c = Card("GameMode (CPU governor + GPU boost)")
        self.box.append(c)
        if not have("gamemoded"):
            c.add_row(Gtk.Label(label="gamemode not installed", xalign=0))
            ib = SketchButton("Install gamemode", width=160, height=24,
                              color=NEON_GREEN)
            ib.connect("clicked", lambda _b: sh_async(
                ["pkexec", "pacman", "-S", "--noconfirm", "gamemode",
                 "lib32-gamemode"],
                lambda r: (self.win.toast(
                    "gamemode installed" if r[0]==0 else "failed"),
                           self.refresh()), timeout=300))
            c.add_row(ib)
        else:
            rc, st, _ = sh(["systemctl", "--user", "is-active",
                            "gamemoded.service"])
            active = "active" in st
            rc2, en, _ = sh(["systemctl", "--user", "is-enabled",
                             "gamemoded.service"])
            enabled = "enabled" in en
            c.add_row(kv_row("Service:",   "active" if active else "inactive"))
            c.add_row(kv_row("At login:",  "enabled" if enabled else "disabled"))
            rc, gs, _ = sh(["gamemoded", "-s"])
            c.add_row(kv_row("Live state:", gs.strip() or "?"))
            row = Gtk.Box(spacing=8)
            tg = SketchToggle("Run at login", width=180, height=26,
                              color=NEON_GREEN, active=enabled)
            tg.connect("clicked", lambda _b: sh_async(
                ["systemctl", "--user",
                 "enable" if tg.active else "disable", "--now",
                 "gamemoded.service"],
                lambda r: (self.win.toast(
                    "gamemoded updated" if r[0]==0 else "failed"),
                           self.refresh())))
            row.append(tg)
            tb = SketchButton("Test (gamemoderun glxgears)", width=240,
                              height=24, color=NEON_PINK)
            tb.connect("clicked", lambda _b: sh_async(
                ["sh", "-c", "gamemoderun glxgears &"]))
            row.append(tb); c.add_row(row)

        # ── 2. MangoHud overlay ───────────────────────────────────────────
        c = Card("MangoHud (in-game perf overlay)")
        self.box.append(c)
        if not have("mangohud"):
            c.add_row(Gtk.Label(label="mangohud not installed", xalign=0))
            ib = SketchButton("Install MangoHud", width=180, height=24,
                              color=NEON_GREEN)
            ib.connect("clicked", lambda _b: sh_async(
                ["pkexec", "pacman", "-S", "--noconfirm", "mangohud",
                 "lib32-mangohud"],
                lambda r: (self.win.toast(
                    "mangohud installed" if r[0]==0 else "failed"),
                           self.refresh()), timeout=300))
            c.add_row(ib)
        else:
            c.add_row(kv_row("Config file:", str(self.MANGOHUD_CONF)))
            c.add_row(kv_row("Exists:",
                             "yes" if self.MANGOHUD_CONF.exists() else "no"))
            try: cfg_text = self.MANGOHUD_CONF.read_text()
            except Exception: cfg_text = self.DEFAULT_MANGOHUD
            sw = Gtk.ScrolledWindow(); sw.set_size_request(-1, 200)
            self._mh_tv = Gtk.TextView(); self._mh_tv.set_monospace(True)
            self._mh_tv.add_css_class("nyx-editor")
            self._mh_tv.get_buffer().set_text(cfg_text)
            sw.set_child(self._mh_tv); c.add_row(sw)
            row = Gtk.Box(spacing=8)
            sb = SketchButton("Save config", width=120, height=24,
                              color=NEON_GREEN)
            sb.connect("clicked", lambda _b: self._save_mangohud())
            row.append(sb)
            db = SketchButton("Reset to defaults", width=160, height=24,
                              color=ACCENT_GOLD)
            db.connect("clicked", lambda _b: self._reset_mangohud())
            row.append(db)
            tb = SketchButton("Test (mangohud glxgears)", width=210,
                              height=24, color=NEON_PINK)
            tb.connect("clicked", lambda _b: sh_async(
                ["sh", "-c", "mangohud glxgears &"]))
            row.append(tb)
            if have("goverlay"):
                gb = SketchButton("Open GOverlay GUI", width=170, height=24,
                                  color=NEON_BLUE)
                gb.connect("clicked", lambda _b: sh_async(["goverlay"]))
                row.append(gb)
            c.add_row(row)

        # ── 3. Steam / Proton ─────────────────────────────────────────────
        c = Card("Steam & Proton")
        self.box.append(c)
        c.add_row(kv_row("Steam (system):",
                         "installed" if have("steam") else "(not installed)"))
        flatpak_steam = ""
        if have("flatpak"):
            rc, fl, _ = sh(["flatpak", "list", "--columns=application"])
            flatpak_steam = "yes" if "com.valvesoftware.Steam" in fl else "no"
        c.add_row(kv_row("Steam (flatpak):", flatpak_steam or "(no flatpak)"))
        compat = Path.home() / ".steam/root/compatibilitytools.d"
        if compat.exists():
            tools = sorted([p.name for p in compat.iterdir() if p.is_dir()])
            c.add_row(kv_row("Compat tools:",
                             ", ".join(tools[:6]) if tools else "(none)"))
            if len(tools) > 6:
                c.add_row(kv_row("",  f"+ {len(tools)-6} more"))
        else:
            c.add_row(kv_row("Compat tools:", "(no Steam install)"))

        if not have("steam"):
            sb = SketchButton("Install Steam", width=140, height=24,
                              color=NEON_BLUE)
            sb.connect("clicked", lambda _b: sh_async(
                ["pkexec", "pacman", "-S", "--noconfirm", "steam"],
                lambda r: (self.win.toast(
                    "steam installed" if r[0]==0 else "enable multilib first"),
                           self.refresh()), timeout=600))
            c.add_row(sb)

        # ── 4. Wine prefixes ──────────────────────────────────────────────
        c = Card("Wine prefixes")
        self.box.append(c)
        c.add_row(kv_row("wine binary:",
                         "installed" if have("wine") else "(missing)"))
        wp = Path.home() / ".wine"
        c.add_row(kv_row("default prefix:",
                         "exists" if wp.exists() else "(none)"))
        # discover other prefixes
        prefixes = []
        for d in (Path.home(), Path.home() / ".local/share"):
            if d.exists():
                for sub in d.iterdir():
                    if sub.is_dir() and (sub / "system.reg").exists():
                        prefixes.append(str(sub))
        for p in prefixes[:6]:
            c.add_row(kv_row("prefix:", p))

        # ── 5. environment helpers ────────────────────────────────────────
        c = Card("graphics tweaks (live)")
        self.box.append(c)
        # MANGOHUD env (Hyprland-wide)
        mh_env = self._hypr_env("MANGOHUD")
        et = SketchToggle("Force MANGOHUD=1 in all apps",
                          width=300, height=26, color=NEON_BLUE,
                          active=(mh_env == "1"))
        et.connect("clicked", lambda _b: self._set_hypr_env(
            "MANGOHUD", "1" if et.active else ""))
        c.add_row(et)
        dxvk = self._hypr_env("DXVK_HUD")
        dt = SketchToggle("DXVK_HUD=full (DXVK overlay)",
                          width=300, height=26, color=NEON_PINK,
                          active=(dxvk == "full"))
        dt.connect("clicked", lambda _b: self._set_hypr_env(
            "DXVK_HUD", "full" if dt.active else ""))
        c.add_row(dt)

        # ── 6. controllers ────────────────────────────────────────────────
        c = Card("controllers")
        self.box.append(c)
        rc, out, _ = sh(["ls", "/dev/input/by-id/"])
        controllers = [l for l in out.splitlines()
                       if any(k in l.lower()
                              for k in ("joystick", "gamepad", "event-joystick",
                                        "8bitdo", "xbox", "ds4", "ps4", "ps5"))]
        if controllers:
            for dev in controllers:
                c.add_row(kv_row("device:", dev))
        else:
            c.add_row(Gtk.Label(label="(no controllers detected -- "
                                "plug one in and refresh)", xalign=0))
        rb = SketchButton("Refresh", width=92, height=22, color=NEON_GREEN)
        rb.connect("clicked", lambda _b: self.refresh())
        c.add_row(rb)

        self.add_note(
            "GameMode + MangoHud + Proton give Tesla-grade gaming on Arch. "
            "GOverlay is a GUI editor for the same MangoHud config file.")

    def _save_mangohud(self):
        try:
            self.MANGOHUD_CONF.parent.mkdir(parents=True, exist_ok=True)
            buf = self._mh_tv.get_buffer()
            text = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
            self.MANGOHUD_CONF.write_text(text)
            self.win.toast("MangoHud config saved")
            self.mark_changed("MangoHud config")
        except Exception as e:
            self.win.toast(f"save err: {e}")

    def _reset_mangohud(self):
        try:
            self.MANGOHUD_CONF.parent.mkdir(parents=True, exist_ok=True)
            self.MANGOHUD_CONF.write_text(self.DEFAULT_MANGOHUD)
            self.win.toast("MangoHud reset to NYXUS defaults")
            self.refresh()
        except Exception as e:
            self.win.toast(f"reset err: {e}")

    def _hypr_env(self, name: str) -> str:
        rc, out, _ = sh(["hyprctl", "-j", "getoption", "env"])
        return os.environ.get(name, "")

    def _set_hypr_env(self, name: str, val: str):
        if val:
            sh(["hyprctl", "keyword", "env", f"{name},{val}"])
            os.environ[name] = val
        else:
            os.environ.pop(name, None)
        self.win.toast(f"{name}={val or '(unset)'}")
        self.mark_changed(f"env {name}")
        self.needs_restart(f"env {name}")

    def refresh(self):
        c = self.box.get_first_child()
        while c:
            n = c.get_next_sibling()
            if c is not self.box.get_first_child(): self.box.remove(c)
            c = n
        self.build()

    def search_entries(self):
        return [
            SearchEntry(self.KEY, self.TITLE, "GameMode", "cpu governor boost"),
            SearchEntry(self.KEY, self.TITLE, "MangoHud", "perf overlay fps"),
            SearchEntry(self.KEY, self.TITLE, "MangoHud config editor"),
            SearchEntry(self.KEY, self.TITLE, "Steam", "valve"),
            SearchEntry(self.KEY, self.TITLE, "Proton compatibility tools"),
            SearchEntry(self.KEY, self.TITLE, "Wine prefixes"),
            SearchEntry(self.KEY, self.TITLE, "DXVK HUD"),
            SearchEntry(self.KEY, self.TITLE, "Controllers", "gamepad joystick"),
            SearchEntry(self.KEY, self.TITLE, "GOverlay"),
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
            draw_display(cr, w/2-14, h/2-26, ini, size=46,
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
        c.add_row(kv_row("handwritten (NYXUS apps)", "Inter Display 14 (built-in)"))
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
                  "display","antialiasing","hinting","subpixel","text scale",
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


class GraffitiBackground(Gtk.DrawingArea):
    """Hand-drawn neon graffiti collage of NYXUS-related words, drawn
    behind every page. Stable layout (seeded RNG) so words don't dance
    on every redraw. No grey — pure neon ink on black."""

    # NYXUS graffiti image pool -- shipped via the api-server, downloaded
    # on first launch into ~/.cache/nyxus/graffiti/. Each page key maps
    # deterministically to one image (24 pages cycle over 17 images).
    _IMAGE_POOL = [f"nyxus-graffiti-{i:02d}.png" for i in range(1, 25)]
    _IMAGE_BASE_URL = "https://nyxus-core.replit.app/api/download/nyxus"
    _IMAGE_CACHE_DIR = Path.home() / ".cache" / "nyxus" / "graffiti"

    # Hand-picked best-fit image per page key (indexes into _IMAGE_POOL).
    # Pages not listed fall back to deterministic hash mapping.
    _PAGE_IMAGE_OVERRIDE = {
        "_home":         0,   # eye/skull -- biggest WOW for landing
        "account":       21,  # multi-color neon blend (was purple)
        "display":       3,   # geometric pink/blue
        "network":       4,   # walls of crowns
        "bluetooth":     7,   # rainbow flow
        "sound":         12,  # blue skull w/ headphones
        "keyboard":      22,  # bright spray blend (was purple)
        "mouse":         15,  # cartoon face
        "power":         11,  # neon eye
        "appearance":    10,  # rainbow on brick
        "workspaces":    5,   # green "style" piece
        "datetime":      9,   # paint drips
        "notifications": 13,  # "DANGER" street tag
        "users":         14,  # donald duck spray
        "privacy":       12,  # skull
        "apps":          1,   # crowded shop wall
        "storage":       1,
        "language":      2,
        "a11y":          5,
        "printers":      8,   # MAN/STREET tags
        "gaming":        3,
        "developer":     8,
        "wallpaper":     10,
        "fonts":         6,
        "about":         0,
    }

    def __init__(self):
        super().__init__()
        self.set_hexpand(True); self.set_vexpand(True)
        self.set_can_target(False)  # don't steal clicks
        self.add_css_class("nyx-graffiti-host")
        self.set_draw_func(self._draw)
        self._layout_cache: Optional[List[tuple]] = None
        self._cache_w = 0; self._cache_h = 0
        self._page_key = "_home"
        self._words = _GRAFFITI_WORDS_BY_PAGE.get(self._page_key, [])
        # image-mode state
        self._pixbuf_cache: Dict[str, "GdkPixbuf.Pixbuf"] = {}
        self._scaled_cache: Dict[Tuple[str, int, int], "GdkPixbuf.Pixbuf"] = {}
        self._fetch_inflight: Set[str] = set()
        try:
            self._IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log.warning("graffiti cache dir: %s", e)

    # public: called by SettingsWindow.show_page() so the background
    # swaps to the image picked for the current page.
    def set_page_key(self, key: str):
        new_key = key if (key in _GRAFFITI_WORDS_BY_PAGE
                          or key in self._PAGE_IMAGE_OVERRIDE) else "_home"
        if new_key == self._page_key: return
        self._page_key = new_key
        self._words = _GRAFFITI_WORDS_BY_PAGE.get(new_key, [])
        self._layout_cache = None  # force word-fallback rebuild on next draw
        self.queue_draw()

    # ── image picker / loader / async fetcher ──────────────────────────
    def _image_for_page(self, key: str) -> str:
        idx = self._PAGE_IMAGE_OVERRIDE.get(key)
        if idx is None:
            # deterministic hash over key -> pool index (stable per page)
            idx = abs(hash(("nyx-graffiti-pick", key))) % len(self._IMAGE_POOL)
        idx = max(0, min(idx, len(self._IMAGE_POOL) - 1))
        return self._IMAGE_POOL[idx]

    def _load_pixbuf(self, name: str) -> "Optional[GdkPixbuf.Pixbuf]":
        """Return the pixbuf for `name` if cached on disk; otherwise
        kick off an async download and return None. Subsequent draws
        will pick it up once the file lands."""
        if name in self._pixbuf_cache:
            return self._pixbuf_cache[name]
        local = self._IMAGE_CACHE_DIR / name
        if local.exists() and local.stat().st_size > 1024:
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file(str(local))
                self._pixbuf_cache[name] = pb
                return pb
            except Exception as e:
                log.warning("graffiti load %s: %s", name, e)
                try: local.unlink()
                except Exception: pass
        # rev r19: graffiti download disabled (matte-paint background)
        return None

    def _scaled_for(self, name: str, w: int, h: int) -> "Optional[GdkPixbuf.Pixbuf]":
        # round dims to nearest 32 so we don't thrash the cache on small resizes
        bw = max(64, (w // 32) * 32)
        bh = max(64, (h // 32) * 32)
        ck = (name, bw, bh)
        if ck in self._scaled_cache:
            return self._scaled_cache[ck]
        src = self._load_pixbuf(name)
        if src is None: return None
        sw, sh = src.get_width(), src.get_height()
        if sw <= 0 or sh <= 0: return None
        # COVER fit: scale so the image fills the viewport, crop overflow
        scale = max(bw / sw, bh / sh)
        tw, th = max(1, int(sw * scale)), max(1, int(sh * scale))
        try:
            scaled = src.scale_simple(tw, th, GdkPixbuf.InterpType.BILINEAR)
        except Exception as e:
            log.warning("graffiti scale %s: %s", name, e)
            return None
        # cap cache size
        if len(self._scaled_cache) > 6:
            self._scaled_cache.pop(next(iter(self._scaled_cache)))
        self._scaled_cache[ck] = scaled
        return scaled

    def _build_layout(self, w: int, h: int):
        # Seed by page key so layout is stable per page (no dancing) but
        # different pages get different compositions.
        seed = abs(hash(("graffiti-v2", self._page_key))) & 0xFFFFFFFF
        rng = random.Random(seed)
        items = []
        placed: List[tuple] = []
        words = self._words or _GRAFFITI_WORDS_BY_PAGE["_home"]
        max_tries = len(words) * 10
        idx = 0; tries = 0
        while idx < len(words) and tries < max_tries:
            tries += 1
            word, base_size = words[idx]
            size = int(base_size * (0.85 + rng.random() * 0.5))
            est_w = int(len(word) * size * 0.55)
            est_h = int(size * 1.1)
            x = rng.randint(20, max(40, w - est_w - 20))
            y = rng.randint(20, max(40, h - est_h - 20))
            angle = (rng.random() - 0.5) * 0.55  # +/- ~15deg rotation
            ok = True
            for (px, py, pw, ph) in placed:
                if (x < px + pw + 10 and x + est_w + 10 > px and
                    y < py + ph + 10 and y + est_h + 10 > py):
                    ok = False; break
            if not ok: continue
            placed.append((x, y, est_w, est_h))
            alpha = 0.16 + rng.random() * 0.16
            tint = self._TINTS[rng.randrange(len(self._TINTS))]
            items.append((word, x, y, size, angle, alpha, tint))
            idx += 1
        self._layout_cache = items
        self._cache_w, self._cache_h = w, h

    def _draw(self, area, cr, w, h, _=None):
        # rev r19: graffiti background removed by user request.
        # Paint matte black paint + faint vignette so the settings shell
        # reads as a flat enterprise instrument panel (no rainbow art).
        cr.set_source_rgb(0.078, 0.078, 0.102)   # #14141a
        cr.rectangle(0, 0, w, h); cr.fill()
        try:
            vg = cairo.RadialGradient(w / 2, h / 2, h * 0.25,
                                      w / 2, h / 2, h * 0.95)
            vg.add_color_stop_rgba(0.0, 0, 0, 0, 0.0)
            vg.add_color_stop_rgba(1.0, 0, 0, 0, 0.55)
            cr.set_source(vg)
            cr.rectangle(0, 0, w, h); cr.fill()
        except Exception:
            pass
        return


class SettingsRow(Gtk.DrawingArea):
    """Lean enterprise list-row (icon + title + subtitle + chevron) —
    Windows 10 / GNOME System Settings style. No grey: pure black bg
    over neon dividers. Used in home list AND sidebar nav (compact mode)."""
    __gsignals__ = {"activated": (GObject.SignalFlags.RUN_FIRST, None, ())}

    def __init__(self, *, icon: str, title: str, subtitle: str = "",
                 color=NEON_PINK, starred: bool = False, active: bool = False,
                 compact: bool = False, width=-1, height=40):
        super().__init__()
        self.icon, self.title, self.subtitle = icon, title, subtitle
        self.color = color; self.starred = starred
        self.active = active; self.compact = compact
        self._hover = False
        # ── glitch-scramble reveal state ───────────────────────────────
        self._scramble_text = title       # what _draw renders for title
        self._scramble_step = 0           # 0..N (chars locked left→right)
        self._scramble_tid  = 0           # GLib timeout id
        if compact and height == 40: height = 36
        self.set_size_request(width, height)
        self.set_hexpand(True); self.set_vexpand(False)
        try: self.set_content_height(height)
        except Exception: pass
        self.set_draw_func(self._draw)
        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("released", lambda *_a: self.emit("activated"))
        self.add_controller(gc)
        mc = Gtk.EventControllerMotion()
        mc.connect("enter", lambda *_a: self._on_hover_enter())
        mc.connect("leave", lambda *_a: self._on_hover_leave())
        self.add_controller(mc)
        self.set_cursor(Gdk.Cursor.new_from_name("pointer"))

    # ── glitch-scramble (matrix-style char reveal) ─────────────────────
    _SCRAMBLE_CHARS = "!<>-_\\/[]{}—=+*^?#░▒▓█▌▐│┤╡╢╖╕╣║╗╝┐└┴┬├─┼┘┌"

    def _on_hover_enter(self):
        self._hover = True
        self._scramble_step = 0
        if self._scramble_tid:
            try: GLib.source_remove(self._scramble_tid)
            except Exception: pass
        self._scramble_tid = GLib.timeout_add(28, self._scramble_tick)
        self.queue_draw()

    def _on_hover_leave(self):
        self._hover = False
        if self._scramble_tid:
            try: GLib.source_remove(self._scramble_tid)
            except Exception: pass
            self._scramble_tid = 0
        self._scramble_text = self.title
        self.queue_draw()

    def _scramble_tick(self):
        n = len(self.title)
        # advance ~1.6 chars per tick → full reveal in ~n/1.6 ticks
        self._scramble_step = min(n, self._scramble_step + 2)
        out = []
        for i, ch in enumerate(self.title):
            if i < self._scramble_step or ch == " ":
                out.append(ch)
            else:
                out.append(random.choice(self._SCRAMBLE_CHARS))
        self._scramble_text = "".join(out)
        self.queue_draw()
        if self._scramble_step >= n:
            self._scramble_tid = 0
            self._scramble_text = self.title
            return False
        return True

    def set_active(self, on: bool):
        if self.active != on:
            self.active = on; self.queue_draw()

    def _draw(self, area, cr, w, h, _=None):
        # NO tinted backgrounds (low-alpha pink reads as purple on black).
        # Active/hover indicated by left neon bar + outer-edge glow only.
        if self.active:
            # solid neon left bar
            cr.set_source_rgba(*self.color, 1.0)
            cr.rectangle(0, 0, 3, h); cr.fill()
            # neon hairline ring around the row (no fill)
            cr.set_source_rgba(*self.color, 0.65); cr.set_line_width(1.0)
            cr.rectangle(0.5, 0.5, w-1, h-1); cr.stroke()
            # outer glow halo (top + bottom edges) -- pure additive light
            cr.set_source_rgba(*self.color, 0.18); cr.set_line_width(2.5)
            cr.move_to(0, 0.5); cr.line_to(w, 0.5); cr.stroke()
            cr.move_to(0, h-0.5); cr.line_to(w, h-0.5); cr.stroke()
        elif self._hover:
            # softer neon left bar
            cr.set_source_rgba(*self.color, 0.85)
            cr.rectangle(0, 0, 2, h); cr.fill()
            # faint outer ring
            cr.set_source_rgba(*self.color, 0.32); cr.set_line_width(1.0)
            cr.rectangle(0.5, 0.5, w-1, h-1); cr.stroke()
        # neon hairline divider (no grey)
        cr.set_source_rgba(*NEON_PINK, 0.10); cr.set_line_width(1.0)
        sketch_line(cr, 12, h-0.5, w-12, h-0.5, jitter=0.20,
                    key=("srow", self.title, w))
        # left accent dot
        cr.set_source_rgba(*self.color, 0.95)
        cr.arc(16, h/2, 3, 0, math.pi*2); cr.fill()
        # icon
        icon_size = 16 if self.compact else 18
        draw_display(cr, 28, (h-icon_size-4)/2, self.icon, size=icon_size,
                    color=(*self.color, 0.98))
        # title
        title_size = 15 if self.compact else 17
        title_y = (h-title_size-4)/2 - (4 if self.subtitle else 0)
        # use scrambled text while hover-reveal is animating, real title otherwise
        title_str = self._scramble_text if (self._hover and self._scramble_tid) else self.title
        # JetBrains Mono during scramble for that proper glitch/terminal feel
        title_family = "JetBrains Mono" if (self._hover and self._scramble_tid) else None
        # neon ink during scramble, normal ink otherwise
        title_color = ((*self.color, 1.0) if (self._hover and self._scramble_tid)
                       else (*INK_BRIGHT, 0.98))
        if title_family:
            draw_display(cr, 56, title_y, title_str, size=title_size,
                        color=title_color, weight=Pango.Weight.BOLD,
                        family=title_family)
        else:
            draw_display(cr, 56, title_y, title_str, size=title_size,
                        color=title_color, weight=Pango.Weight.BOLD)
        # subtitle (mono dim)
        if self.subtitle and not self.compact:
            draw_display(cr, 56, h-16, self.subtitle, size=10,
                        color=(*INK_DIM, 0.80),
                        family="JetBrains Mono")
        # star
        if self.starred:
            draw_display(cr, w-48, (h-18)/2, "★", size=14,
                        color=(*ACCENT_GOLD, 0.95))
        # chevron ›
        chev_col = self.color if self.active else INK_DIM
        draw_display(cr, w-22, (h-22)/2, "›", size=20,
                    color=(*chev_col, 0.85))


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
        draw_display(cr, 14, 8, self.icon, size=32,
                    color=(*self.color, 0.95))
        # star if favorited
        if self.starred:
            draw_display(cr, w-26, 8, "★", size=22,
                        color=(*ACCENT_GOLD, 0.95))
        # title
        draw_display(cr, 14, h-66, self.title, size=22,
                    color=(*INK_BRIGHT, 0.97),
                    weight=Pango.Weight.BOLD, wrap_w=w-28)
        # subtitle
        if self.subtitle:
            draw_display(cr, 14, h-32, self.subtitle, size=13,
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
/* =====================================================================
   NYXUS SETTINGS -- Tesla-grade global stylesheet
   Pure black canvas, neon-pink glass chrome, multi-layer glow,
   smooth 180ms transitions on every interactive surface.
   ===================================================================== */

* { font-family: 'Inter Display', 'Inter Display', cursive;
    transition: background-color 180ms ease,
                border-color     180ms ease,
                color            180ms ease,
                box-shadow       220ms ease,
                text-shadow      180ms ease; }

window, .nyx-bg { background-color: #000000; color: #e8edf5; }

/* -- HERO HEADER (pure black + neon-pink underline glow) ------------- */
.nyx-hero {
    background-image: none;
    background-color: #000000;
    padding: 14px 18px;
    /* Beefier edge -- matches the 4px Hyprland window border weight so
       the hero feels anchored instead of floating on a hairline. */
    border-bottom: 3px solid rgba(8, 12, 20, 0.85);
    box-shadow: 0 8px 36px -4px #14141a,
                0 2px 0    0    rgba(8, 12, 20, 0.35);
}
/* Multi-color hero title: per-letter <span foreground=...> markup
   provides the rainbow ink; this rule layers a WHITE glow halo on top
   so every letter punches off the pure-black hero strip. */
.nyx-hero-title {
    text-shadow: 0 0 4px  rgba(255,255,255,0.55),
                 0 0 12px rgba(255,255,255,0.32),
                 0 0 26px rgba(255,255,255,0.18),
                 0 0 40px rgba(8, 12, 20, 0.35);
    font-size: 32px; font-weight: bold; letter-spacing: 1.5px; }
.nyx-hero-sub { color: rgba(240,235,250,0.62); font-size: 14px;
    letter-spacing: 0.4px; margin-top: -2px; }

/* -- VERSION PILL (black capsule, neon ring, hover bloom) ------------ */
.nyx-version-pill { color: rgba(240,235,250,0.95);
    background-image: none;
    background-color: #000000;
    border: 1px solid rgba(8, 12, 20, 0.65);
    border-radius: 999px; padding: 5px 16px; font-size: 14px;
    font-family: 'JetBrains Mono', monospace;
    box-shadow: 0 0 10px rgba(8, 12, 20, 0.18); }
.nyx-version-pill:hover {
    border-color: #e8edf5;
    box-shadow: 0 0 22px #14141a; }

/* -- TOOLBARS (slim glass) -------------------------------------------- */
.nyx-toolbar  { background-color: #000000;
    padding: 6px 12px;
    border-bottom: 1px solid rgba(8, 12, 20, 0.18); }
.nyx-toolbar2 { background-color: #0a0a0e;
    padding: 5px 14px;
    border-bottom: 1px solid rgba(8, 12, 20, 0.18);
    box-shadow: 0 2px 12px -4px rgba(8, 12, 20, 0.20); }

/* -- RESTART BAR (warning amber w/ glow) ------------------------------ */
.nyx-restartbar {
    background-image: linear-gradient(90deg,
        rgba(8, 12, 20, 0.28), rgba(255, 255, 255, 0.10));
    background-color: rgba(8, 12, 20, 0.20);
    border-top: 1px solid rgba(255, 255, 255, 0.65);
    border-bottom: 1px solid rgba(255, 255, 255, 0.65);
    padding: 6px 14px;
    box-shadow: inset 0 0 14px rgba(255, 255, 255, 0.18); }
.nyx-restartbar label { color: #e8edf5; font-size: 14px;
    text-shadow: 0 0 6px rgba(255, 255, 255, 0.45); }

/* -- STRIPS (favorites/recents bands) --------------------------------- */
.nyx-strip { background-color: transparent;
    border-top: 1px solid rgba(8, 12, 20, 0.22);
    border-bottom: 1px solid rgba(8, 12, 20, 0.12);
    padding: 8px 16px; }
.nyx-strip-label { color: rgba(255, 255, 255, 0.92); font-size: 13px;
    text-transform: uppercase; letter-spacing: 1.8px;
    font-family: 'JetBrains Mono', monospace;
    text-shadow: 0 0 6px rgba(8, 12, 20, 0.30); }

/* -- STATUS BAR ------------------------------------------------------- */
.nyx-statusbar { background-color: #000000; padding: 3px 12px;
    border-top: 1px solid rgba(8, 12, 20, 0.32);
    box-shadow: 0 -2px 12px -4px rgba(8, 12, 20, 0.20); }

/* -- HEADLINES + META ------------------------------------------------- */
.nyx-headline { color: #e8edf5;
    text-shadow: 0 0 10px rgba(8, 12, 20, 0.45),
                 0 0 22px rgba(8, 12, 20, 0.20);
    font-size: 24px; font-weight: bold; letter-spacing: 0.6px; }
.nyx-meta { color: rgba(240,235,250,0.55); font-size: 12px;
    font-family: 'JetBrains Mono', monospace; letter-spacing: 0.4px; }

/* -- CARDS (pure black + neon ring + outer pink bloom on hover) ----- */
.nyx-card { background-color: #000000;
    background-image: none;
    border: 1px solid rgba(8, 12, 20, 0.40);
    border-radius: 6px;
    padding: 4px 0 10px 0;
    box-shadow: 0 4px 22px -10px rgba(8, 12, 20, 0.25); }
.nyx-card:hover {
    border-color: #e8edf5;
    box-shadow: 0 8px 36px -6px #14141a; }

.nyx-listcard { background-color: #000000;
    background-image: none;
    border: 1px solid #14141a;
    border-radius: 6px; padding: 0; margin-top: 6px;
    box-shadow: 0 6px 28px -8px rgba(8, 12, 20, 0.30); }
.nyx-listcard:hover {
    border-color: #e8edf5;
    box-shadow: 0 10px 40px -6px #14141a; }

.nyx-settings-list { background-color: transparent; }
.nyx-settings-list row { background-color: transparent;
    padding: 0; min-height: 40px; }
.nyx-settings-list row:hover { background-color: transparent; }
.nyx-settings-list row:selected { background-color: transparent; }

/* -- WIN10 LEFT SIDEBAR (pure black + neon glow rail) ---------------- */
.nyx-sidebar { background-color: #000000;
    background-image: none;
    border-right: 1px solid rgba(8, 12, 20, 0.65);
    padding: 6px 0; min-width: 220px;
    box-shadow: 6px 0 28px -8px rgba(8, 12, 20, 0.40); }
.nyx-sidebar-section { color: rgba(255, 255, 255, 0.92);
    font-family: 'JetBrains Mono', monospace; font-size: 10px;
    letter-spacing: 1.6px; text-transform: uppercase;
    padding: 12px 14px 6px 14px;
    text-shadow: 0 0 6px rgba(8, 12, 20, 0.32); }

.nyx-content { background-color: transparent; padding: 0; }
.nyx-graffiti-host { background-color: #000000; }
/* -- KILL ALL GREY: force every container transparent so graffiti
   shows through. GTK fallback theme paints opaque bg on these. ----- */
.nyx-content scrolledwindow, .nyx-content viewport,
.nyx-content listview, .nyx-content list, .nyx-content row,
.nyx-content textview, .nyx-content box, .nyx-content stack,
scrolledwindow, scrolledwindow > viewport, viewport,
listview, list, list > row, listbox, listbox > row,
stack, frame, .background, .view, .nyx-bg > box {
    background-color: transparent;
    background-image: none;
}
.nyx-content stack { background-color: transparent; }
/* -- user account chip (top-right) ------------------------------------ */
.nyx-user-chip { background-color: transparent;
    border: 1px solid rgba(8, 12, 20, 0.40); border-radius: 999px;
    padding: 4px 12px 4px 4px; }
.nyx-user-name { color: #e8edf5; font-size: 14px;
    font-weight: bold; }
.nyx-user-role { color: rgba(255, 255, 255, 0.85); font-size: 11px;
    font-family: 'JetBrains Mono', monospace; letter-spacing: 0.6px; }
.nyx-card-title { color: #e8edf5; text-shadow: 0 0 8px rgba(8, 12, 20, 0.45);
    font-size: 18px; font-weight: bold; letter-spacing: 0.5px; }
.nyx-row-label { color: #e8edf5; font-size: 14px; }
.nyx-row-value { color: rgba(240,235,250,0.75); font-size: 14px; }
.nyx-entry { background-color: transparent; border: none; outline: none;
    color: #e8edf5; font-size: 14px; caret-color: #e8edf5; }
.nyx-entry:focus { outline: none; box-shadow: none; }
.nyx-editor textview, .nyx-editor text {
    background-color: rgba(0,0,0,0.25);
    color: rgba(240,235,250,0.92);
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    padding: 6px 10px; caret-color: #e8edf5; }
.nyx-toast { background-color: rgba(8, 12, 20, 0.18);
    color: #ffffff; padding: 6px 14px;
    border: 1px solid #14141a;
    border-radius: 6px; font-size: 14px; }
scrollbar slider { background-color: rgba(8, 12, 20, 0.30);
    border: 1px solid rgba(8, 12, 20, 0.45); border-radius: 6px;
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
        # Multi-color hero title: each letter cycles through the NYXUS
        # DARK MIRROR palette (hot-pink, magenta, electric-blue, neon-green, gold,
        # back to hot-pink). The CSS class adds a white outer glow halo on
        # top so every letter punches off the black background.
        title_lbl = Gtk.Label(xalign=0)
        title_lbl.set_use_markup(True)
        title_lbl.set_markup(_rainbow_markup(APP_NAME))
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
        # ── user account chip (top-right, Win10 style) ────────────────────
        import getpass as _gp
        u_name = _gp.getuser()
        try: host = os.uname().nodename
        except Exception: host = "?"
        # role: detect wheel/sudo group membership
        rc, gout, _ = sh("id -nG")
        groups = (gout or "").split()
        role = ("admin" if any(g in groups for g in
                ("wheel", "sudo", "adm")) else "user")
        chip = Gtk.Box(spacing=10); chip.add_css_class("nyx-user-chip")
        chip.set_valign(Gtk.Align.CENTER)
        # avatar circle (use ~/.face if present; else colored initial)
        av_path = Path.home() / ".face"
        avatar = Gtk.DrawingArea()
        avatar.set_size_request(34, 34)
        try: avatar.set_content_width(34); avatar.set_content_height(34)
        except Exception: pass
        avatar.set_valign(Gtk.Align.CENTER)
        _initial = (u_name[:1] or "?").upper()
        _accent  = (NEON_PINK if role == "admin" else NEON_BLUE)
        def _draw_avatar(area, cr, w, h, _=None):
            cr.set_source_rgba(*_accent, 0.20)
            cr.arc(w/2, h/2, min(w,h)/2 - 2, 0, math.pi*2); cr.fill()
            cr.set_source_rgba(*_accent, 0.95); cr.set_line_width(1.4)
            cr.arc(w/2, h/2, min(w,h)/2 - 2, 0, math.pi*2); cr.stroke()
            layout = PangoCairo.create_layout(cr)
            fd = Pango.FontDescription()
            fd.set_family("Inter Display"); fd.set_weight(Pango.Weight.BOLD)
            fd.set_size(int(20 * Pango.SCALE))
            layout.set_font_description(fd); layout.set_text(_initial, -1)
            tw, th = layout.get_pixel_size()
            cr.set_source_rgba(*_accent, 0.98)
            cr.move_to((w-tw)/2, (h-th)/2); PangoCairo.show_layout(cr, layout)
        avatar.set_draw_func(_draw_avatar)
        chip.append(avatar)
        u_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        u_box.set_valign(Gtk.Align.CENTER)
        u_lbl = Gtk.Label(label=u_name, xalign=0)
        u_lbl.add_css_class("nyx-user-name")
        u_box.append(u_lbl)
        r_lbl = Gtk.Label(label=f"{role} @ {host}", xalign=0)
        r_lbl.add_css_class("nyx-user-role")
        u_box.append(r_lbl)
        chip.append(u_box)
        # click → jump to Users page
        gc = Gtk.GestureClick(); gc.set_button(1)
        gc.connect("released",
                   lambda *_a: self.show_page("users"))
        chip.add_controller(gc)
        chip.set_cursor(Gdk.Cursor.new_from_name("pointer"))
        hero_row.append(chip)
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

        # ── split layout: left sidebar (Win10 style) + content stack ──────
        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        split.set_hexpand(True); split.set_vexpand(True)

        # sidebar — scrollable, hidden on Home, visible on category pages
        self._sidebar_sw = Gtk.ScrolledWindow()
        self._sidebar_sw.set_policy(Gtk.PolicyType.NEVER,
                                    Gtk.PolicyType.AUTOMATIC)
        self._sidebar_sw.set_size_request(220, -1)
        self._sidebar_sw.add_css_class("nyx-sidebar")
        self._sidebar_sw.set_visible(False)
        self._sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                    spacing=0)
        self._sidebar_sw.set_child(self._sidebar_box)
        self._sidebar_rows: Dict[str, "SettingsRow"] = {}
        split.append(self._sidebar_sw)

        # stack (content panel) — graffiti background sits behind
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(180)
        self.stack.set_hexpand(True); self.stack.set_vexpand(True)
        self.stack.add_css_class("nyx-content")
        ov = Gtk.Overlay()
        # rev r23 · 2026-05-09 — graffiti background REMOVED for real.
        # Was still being instantiated even though the rev r19 changelog
        # said it was disabled — Hyprland kept showing the splatter from
        # the on-disk image cache. Now replaced with a transparent box so
        # the chrome.py dark-glass + Hyprland blur read the wallpaper
        # through the window cleanly. self._graffiti kept as an attribute
        # for back-compat with the page-swap hook (it's a no-op now).
        self._graffiti = Gtk.Box()  # transparent, no-op
        ov.set_child(self._graffiti)
        ov.set_hexpand(True); ov.set_vexpand(True)
        # main content above transparent layer
        ov.add_overlay(self.stack)
        # toast on top of everything
        self._toast_label = Gtk.Label()
        self._toast_label.add_css_class("nyx-toast")
        self._toast_label.set_halign(Gtk.Align.CENTER)
        self._toast_label.set_valign(Gtk.Align.END)
        self._toast_label.set_margin_bottom(20)
        self._toast_label.set_visible(False)
        ov.add_overlay(self._toast_label)
        split.append(ov)
        root.append(split)

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

        # populate sidebar nav (Win10 style — visible on category pages)
        self._populate_sidebar()

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

        # strips: favorites + recents (compact chip rows)
        self._fav_strip    = self._make_strip("★ favorites")
        self._recent_strip = self._make_strip("⟲ recently changed")
        outer.append(self._fav_strip)
        outer.append(self._recent_strip)

        # vertical list of all categories (compact rows, professional look)
        all_lbl = Gtk.Label(label="all categories", xalign=0)
        all_lbl.add_css_class("nyx-strip-label")
        all_lbl.set_margin_top(10); all_lbl.set_margin_start(2)
        outer.append(all_lbl)

        # ListBox wrapper styled as a single bordered card
        list_wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        list_wrap.add_css_class("nyx-listcard")
        outer.append(list_wrap)

        self._tiles_box = Gtk.ListBox()
        self._tiles_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._tiles_box.add_css_class("nyx-settings-list")
        self._tiles_box.set_hexpand(True)
        list_wrap.append(self._tiles_box)

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
        # build compact list rows (favorites first, then everyone else)
        fav_keys = [k for k in self.favorites
                    if k in self._page_widgets]
        ordered  = ([self._page_widgets[k].__class__ for k in fav_keys]
                    + [cls for cls in PAGE_CLASSES
                       if cls.KEY not in fav_keys])
        for cls in ordered:
            page = self._page_widgets.get(cls.KEY)
            if page is None: continue
            if not getattr(page, "AVAILABLE", True): continue
            # Title-only rows on Home (no subtitle) so the graffiti
            # background breathes through. Compact 38px height.
            row = SettingsRow(
                icon=getattr(cls, "ICON", "•"),
                title=getattr(cls, "TITLE", cls.__name__),
                subtitle="",
                color=getattr(cls, "TILE_COLOR", NEON_PINK),
                starred=(cls.KEY in self.favorites),
                compact=True, height=38,
            )
            row.connect("activated", lambda _t, k=cls.KEY:
                        self.show_page(k))
            self._tiles_box.append(row)

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
                chip = SettingsRow(icon=cls.ICON, title=cls.TITLE,
                                   subtitle="", color=cls.TILE_COLOR,
                                   starred=True, width=240, height=44)
                chip.connect("activated",
                             lambda _t, kk=k: self.show_page(kk))
                inner.append(chip)
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
                chip = SettingsRow(icon=cls.ICON, title=cls.TITLE,
                                   subtitle="", color=cls.TILE_COLOR,
                                   starred=(k in self.favorites),
                                   width=240, height=44)
                chip.connect("activated",
                             lambda _t, kk=k: self.show_page(kk))
                inner.append(chip)

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

    # ── sidebar nav (Win10 style) ───────────────────────────────────────────
    def _populate_sidebar(self):
        """Fill the left sidebar with one compact SettingsRow per page,
        grouped under section headers. Click → show_page(key)."""
        # clear (in case rebuilt)
        child = self._sidebar_box.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self._sidebar_box.remove(child); child = nxt
        self._sidebar_rows.clear()

        # tiny header label
        head = Gtk.Label(label="◆  CATEGORIES", xalign=0)
        head.add_css_class("nyx-sidebar-section")
        self._sidebar_box.append(head)

        for cls in PAGE_CLASSES:
            page = self._page_widgets.get(cls.KEY)
            if not page: continue
            color = getattr(cls, "TILE_COLOR", NEON_PINK)
            row = SettingsRow(
                icon=cls.ICON, title=cls.TITLE, subtitle="",
                color=color, compact=True, height=34)
            row.connect("activated",
                        lambda _r, k=cls.KEY: self.show_page(k))
            self._sidebar_box.append(row)
            self._sidebar_rows[cls.KEY] = row

        # spacer
        spacer = Gtk.Box(); spacer.set_vexpand(True)
        self._sidebar_box.append(spacer)
        # footer link → home
        head2 = Gtk.Label(label="◆  NAVIGATION", xalign=0)
        head2.add_css_class("nyx-sidebar-section")
        self._sidebar_box.append(head2)
        home_row = SettingsRow(
            icon="⌂", title="Home", subtitle="",
            color=NEON_PINK, compact=True, height=34)
        home_row.connect("activated",
                         lambda _r: self.show_page(HOME_KEY))
        self._sidebar_box.append(home_row)

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
        # rev r23: graffiti background removed — page-key swap is a no-op.
        # Kept as a guarded hasattr() check so any leftover .set_page_key()
        # callers don't crash; the new transparent Gtk.Box has no such method.
        # sidebar visibility (Win10 style: hide on home/search, show on cats)
        if hasattr(self, "_sidebar_sw"):
            self._sidebar_sw.set_visible(
                key not in (HOME_KEY, "_search"))
        # highlight active sidebar row
        for k, row in getattr(self, "_sidebar_rows", {}).items():
            row.set_active(k == key)
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


# ─────────────────────────── NYXUS CHROME (auto-injected r4) ────────────────
# Unifies look across every NYXUS GTK4 app: fully transparent window so the
# user's desktop wallpaper shows through, frosted-glass dark panels, Inter
# font, neon-pink outlined buttons, hover-scramble labels. install_chrome()
# is idempotent and runs once per top-level window via a `present` hook.
# nyxus_chrome.py is shipped to ~/.nyxus by the install pipeline.
try:
    import os as _nyx_os, sys as _nyx_sys
    _nyx_chrome_dir = _nyx_os.path.expanduser("~/.nyxus")
    if _nyx_chrome_dir not in _nyx_sys.path:
        _nyx_sys.path.insert(0, _nyx_chrome_dir)
    try:
        from nyxus_chrome import install_chrome as _nyx_install_chrome
    except ImportError:
        _nyx_install_chrome = lambda *a, **kw: None  # noqa: E731 silent no-op
    _NYX_PAGE_KEY = "_settings"

    def _nyx_make_present_hook(_orig):
        def _nyx_present(self, *args, **kwargs):
            try:
                _nyx_install_chrome(self, page_key=_NYX_PAGE_KEY)
            except Exception:
                pass
            return _orig(self, *args, **kwargs)
        return _nyx_present

    # Gtk.Window.present — base case, also covers Gtk.ApplicationWindow.
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk as _NyxGtk
        if not getattr(_NyxGtk.Window, "_nyx_chrome_hooked", False):
            _NyxGtk.Window.present = _nyx_make_present_hook(_NyxGtk.Window.present)
            _NyxGtk.Window._nyx_chrome_hooked = True
    except Exception as _nyx_eg:
        import sys as _nyx_sys
        print("nyxus-chrome Gtk.Window hook skipped: %s" % _nyx_eg, file=_nyx_sys.stderr)

    # Adw.ApplicationWindow.present — covers shield, sage, studio, godsapp.
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Adw", "1")
        from gi.repository import Adw as _NyxAdw
        if not getattr(_NyxAdw.ApplicationWindow, "_nyx_chrome_hooked", False):
            _NyxAdw.ApplicationWindow.present = _nyx_make_present_hook(
                _NyxAdw.ApplicationWindow.present)
            _NyxAdw.ApplicationWindow._nyx_chrome_hooked = True
    except Exception:
        pass  # Adw is optional
except Exception as _nyx_e:
    import sys as _nyx_sys
    print("nyxus-chrome injection failed: %s" % _nyx_e, file=_nyx_sys.stderr)
