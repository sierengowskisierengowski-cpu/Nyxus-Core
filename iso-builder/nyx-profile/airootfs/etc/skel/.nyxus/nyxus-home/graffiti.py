"""
NYXUS Home - graffiti spatter background (Cairo)
Mirrors GraffitiLayer in HomeDashboard.tsx: word collage + paint splats + drips.
Deterministic seeds so layout is stable per session.
(c) 2026 Joseph Sierengowski - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
import math
import random

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
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, Pango, PangoCairo  # noqa: E402

from style import NEONS  # noqa: E402

GRAFFITI_WORDS = [
    "NYXUS", "NYX", "ARCH", "LINUX", "HYPRLAND", "WAYBAR", "KITTY", "FOOT",
    "ROFI", "DUNST", "NEOVIM", "ZSH", "TMUX", "BTRFS", "WAYLAND", "PIPEWIRE",
    "NETWORKD", "SYSTEMD", "PACMAN", "AUR", "MAKEPKG", "CACHYOS", "REISERFS",
    "INTEL", "PHANTOM", "SHIELD", "GODSAPP", "SAGE", "PANEL", "STUDIO",
    "NOTEPAD", "STICKIES", "SYSMON", "WIDGETS", "START",
    "INTER", "JETBRAINS", "NERDFONT", "NEON", "ROOT", "OPS",
    "AES-256-GCM", "PBKDF2", "SHA-256", "TAMPER-OK", "ARMED",
    "SIERENGOWSKI", "J5W", "2026", "v2.0",
    "SILENT", "DARK", "FUNCTIONAL", "OPERATIONAL", "LOCKED",
]


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255)


def _layout(seed_words=20260502, seed_drips=60606060, seed_splats=31415927):
    rw = random.Random(seed_words)
    words = []
    for w in GRAFFITI_WORDS:
        words.append({
            "text":    w,
            "x":       rw.random() * 96 + 1,           # % width
            "y":       rw.random() * 94 + 2,           # % height
            "rot_deg": -28 + rw.random() * 56,
            "size":    0.85 + rw.random() * 1.95,      # rem -> px later
            "color":   NEONS[int(rw.random() * len(NEONS))],
            "opacity": 0.10 + rw.random() * 0.22,
            "weight":  Pango.Weight.BOLD if rw.random() > 0.55 else Pango.Weight.NORMAL,
            "is_display": rw.random() > 0.30,
        })
    rd = random.Random(seed_drips)
    drips = []
    for _ in range(20):
        drips.append({
            "x":       rd.random() * 100,
            "y":       rd.random() * 90,
            "len":     8 + rd.random() * 30,
            "color":   NEONS[int(rd.random() * len(NEONS))],
            "opacity": 0.10 + rd.random() * 0.20,
        })
    rs = random.Random(seed_splats)
    splats = []
    for _ in range(14):
        splats.append({
            "cx":      rs.random() * 100,
            "cy":      rs.random() * 100,
            "rx":      6 + rs.random() * 14,
            "ry":      4 + rs.random() * 12,
            "rot_deg": rs.random() * 360,
            "color":   NEONS[int(rs.random() * len(NEONS))],
            "opacity": 0.05 + rs.random() * 0.10,
        })
    return words, drips, splats


# Computed once - deterministic.
_WORDS, _DRIPS, _SPLATS = _layout()


class GraffitiArea(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_can_focus(False)
        self.set_can_target(False)
        self.set_draw_func(self._draw, None)

    def _draw(self, _area, cr, width, height, _user):
        # Base wash - very dark void with a faint purple gradient.
        cr.set_source_rgb(0.024, 0.0, 0.063)
        cr.paint()

        # ── splats (blurred mist - emulated by stacked low-opacity ellipses) ──
        for s in _SPLATS:
            cx = s["cx"] * width / 100
            cy = s["cy"] * height / 100
            rx = s["rx"] * width / 400        # web divides rx/ry by 4
            ry = s["ry"] * height / 400
            r, g, b = _hex_to_rgb(s["color"])
            for i in range(4):
                cr.save()
                cr.translate(cx, cy)
                cr.rotate(math.radians(s["rot_deg"]))
                cr.scale(rx + i * 1.5, ry + i * 1.5)
                cr.set_source_rgba(r, g, b, s["opacity"] * (0.45 - i * 0.10))
                cr.arc(0, 0, 1.0, 0, 2 * math.pi)
                cr.fill()
                cr.restore()

        # ── drips (vertical neon tick marks) ──
        for d in _DRIPS:
            x = d["x"] * width / 100
            y0 = d["y"] * height / 100
            y1 = y0 + (d["len"] / 3) * height / 100
            r, g, b = _hex_to_rgb(d["color"])
            cr.set_source_rgba(r, g, b, d["opacity"])
            cr.set_line_width(1.2)
            cr.set_line_cap(1)  # ROUND
            cr.move_to(x, y0)
            cr.line_to(x, y1)
            cr.stroke()

        # ── word collage (Pango text rotated) ──
        for w in _WORDS:
            x = w["x"] * width / 100
            y = w["y"] * height / 100
            r, g, b = _hex_to_rgb(w["color"])
            font_px = max(10, int(w["size"] * 16))   # 1rem ~= 16px
            cr.save()
            cr.translate(x, y)
            cr.rotate(math.radians(w["rot_deg"]))
            layout = PangoCairo.create_layout(cr)
            font_desc = Pango.FontDescription()
            if w["is_display"]:
                font_desc.set_family("Inter Display")
            else:
                font_desc.set_family("JetBrains Mono")
            font_desc.set_weight(w["weight"])
            font_desc.set_absolute_size(font_px * Pango.SCALE)
            layout.set_font_description(font_desc)
            layout.set_text(w["text"], -1)
            ext = layout.get_pixel_extents()[1]
            cr.translate(-ext.width / 2, -ext.height / 2)
            # soft outer glow
            cr.set_source_rgba(r, g, b, w["opacity"] * 0.35)
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                cr.move_to(dx, dy)
                PangoCairo.show_layout(cr, layout)
            # main fill
            cr.set_source_rgba(r, g, b, w["opacity"])
            cr.move_to(0, 0)
            PangoCairo.show_layout(cr, layout)
            cr.restore()
