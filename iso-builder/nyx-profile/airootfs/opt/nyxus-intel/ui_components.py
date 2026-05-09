# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · ui_components.py
Hand-drawn aesthetic widgets, Cairo sketch borders, and CSS theme.

Everything visible in the app should pass through these helpers so we keep a
consistent look. The aesthetic:
  • Inter font for headlines / handwritten labels, JetBrains Mono Nerd Font
    for monospace and glyphs (NEVER emoji).
  • Dark base (#0f1420) with pale paper / warm-paper highlight tones.
  • Borders are intentionally jittery — drawn by Cairo with small random
    perturbations so they look hand-sketched.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import math
import random
from typing import Optional, Iterable

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
from gi.repository import Gtk, Gdk, GLib, Pango


# ── icons (Font Awesome / Nerd Font glyphs only) ────────────────────────
# Pulled from the Nerd Font code points so they render with the bundled
# JetBrains Mono Nerd Font. Plain Font Awesome glyphs without the mono font
# fall back to whatever the system has and may render as a missing glyph
# box — that is acceptable; we never fall back to emoji.
class GLYPH:
    LOCK            = "\uF023"   # 
    UNLOCK          = "\uF09C"   # 
    GEAR            = "\uF013"   # 
    PLUS            = "\uF067"   # 
    SEARCH          = "\uF002"   # 
    USER            = "\uF007"   # 
    ENVELOPE        = "\uF0E0"   # 
    GLOBE           = "\uF0AC"   # 
    GLOBE_ALT       = "\uF57D"   # 
    SERVER          = "\uF233"   # 
    BITCOIN         = "\uF15A"   # 
    ETHEREUM        = "\uF42E"   # 
    PHOTO           = "\uF03E"   # 
    DOCUMENT        = "\uF15B"   # 
    EYE             = "\uF06E"   # 
    SHIELD          = "\uF132"   # 
    WARNING         = "\uF071"   # 
    INFO            = "\uF129"   # 
    CHEVRON_RIGHT   = "\uF054"   # 
    CHEVRON_LEFT    = "\uF053"   # 
    CHECK           = "\uF00C"   # 
    CROSS           = "\uF00D"   # 
    REFRESH         = "\uF021"   # 
    EXPORT          = "\uF56E"   # 
    TRASH           = "\uF1F8"   # 
    NOTES           = "\uF249"   # 
    CRYPTO          = "\uF341"   # 
    CHART           = "\uF080"   # 
    CLOCK           = "\uF017"   # 
    DATABASE        = "\uF1C0"   # 
    PHONE           = "\uF095"   # 
    KEY             = "\uF084"   # 
    LINK            = "\uF0C1"   # 


# ── colour palette ──────────────────────────────────────────────────────
class PALETTE:
    BG_DEEP    = (0.051, 0.055, 0.063)   # #0f1420
    BG_PANEL   = (0.094, 0.102, 0.114)   # #1a1e2a
    BG_CARD    = (0.137, 0.145, 0.157)   # #2a2e3a
    INK        = (0.91,  0.89,  0.85 )   # warm paper
    INK_DIM    = (0.62,  0.60,  0.56 )
    ACCENT     = (1.00,  0.78,  0.30 )   # warm gold marker
    ACCENT_2   = (0.45,  0.78,  1.00 )   # cool blue ink
    WARN       = (1.00,  0.45,  0.30 )
    OK         = (0.45,  0.85,  0.55 )
    PINK       = (0.95,  0.43,  0.78 )


# ── Cairo sketch border ─────────────────────────────────────────────────
class SketchBox(Gtk.DrawingArea):
    """A drawing area that paints a hand-drawn rectangular border around its
    own allocation. Pair it with an Overlay to wrap any widget."""

    def __init__(self, *, ink: tuple[float, float, float] = PALETTE.INK,
                 jitter: float = 1.4, double_pass: bool = True,
                 corner_radius: float = 6.0, line_width: float = 1.6):
        super().__init__()
        self._ink = ink
        self._jitter = jitter
        self._double = double_pass
        self._radius = corner_radius
        self._lw = line_width
        self._seed = random.randint(0, 1 << 30)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr, w, h):
        if w <= 4 or h <= 4:
            return
        rng = random.Random(self._seed)
        cr.set_line_cap(1)
        cr.set_line_join(1)
        cr.set_line_width(self._lw)
        cr.set_source_rgba(*self._ink, 0.85)

        passes = 2 if self._double else 1
        for p in range(passes):
            inset = 1.5 + p * 0.6
            self._stroke_rect(cr, rng,
                              inset, inset,
                              w - 2 * inset, h - 2 * inset,
                              self._radius)

    def _stroke_rect(self, cr, rng, x, y, w, h, r):
        x1, y1 = x, y
        x2, y2 = x + w, y + h

        def jp(v):  # jittered point
            return v + rng.uniform(-self._jitter, self._jitter)

        # straight segments — break into ~20px chunks so the jitter shows
        def seg(x_start, y_start, x_end, y_end):
            dx, dy = x_end - x_start, y_end - y_start
            length = math.hypot(dx, dy)
            steps = max(2, int(length / 18))
            cr.move_to(jp(x_start), jp(y_start))
            for i in range(1, steps + 1):
                t = i / steps
                cr.line_to(jp(x_start + dx * t), jp(y_start + dy * t))
            cr.stroke()

        seg(x1 + r, y1, x2 - r, y1)
        seg(x2,     y1 + r, x2, y2 - r)
        seg(x2 - r, y2, x1 + r, y2)
        seg(x1,     y2 - r, x1, y1 + r)

        # rounded corners
        def arc(cx, cy, a1, a2):
            steps = 8
            cr.move_to(cx + r * math.cos(a1) + rng.uniform(-self._jitter, self._jitter),
                       cy + r * math.sin(a1) + rng.uniform(-self._jitter, self._jitter))
            for i in range(1, steps + 1):
                t = i / steps
                a = a1 + (a2 - a1) * t
                cr.line_to(cx + r * math.cos(a) + rng.uniform(-self._jitter, self._jitter),
                           cy + r * math.sin(a) + rng.uniform(-self._jitter, self._jitter))
            cr.stroke()

        arc(x2 - r, y1 + r, -math.pi/2, 0)
        arc(x2 - r, y2 - r, 0, math.pi/2)
        arc(x1 + r, y2 - r, math.pi/2, math.pi)
        arc(x1 + r, y1 + r, math.pi, 3*math.pi/2)


def wrap_sketch(widget: Gtk.Widget, **kwargs) -> Gtk.Widget:
    """Wrap any widget in a sketch-bordered overlay."""
    overlay = Gtk.Overlay()
    overlay.set_child(widget)
    border = SketchBox(**kwargs)
    border.set_can_target(False)
    overlay.add_overlay(border)
    return overlay


# ── small helper widgets ─────────────────────────────────────────────────
def hand_label(text: str, *, size: str = "h2", xalign: float = 0.0) -> Gtk.Label:
    lbl = Gtk.Label(label=text, xalign=xalign)
    lbl.add_css_class(f"nx-{size}")
    return lbl


def glyph_button(glyph: str, *, tooltip: str | None = None,
                 css: Iterable[str] = ()) -> Gtk.Button:
    b = Gtk.Button()
    lbl = Gtk.Label(label=glyph)
    lbl.add_css_class("nx-glyph")
    b.set_child(lbl)
    if tooltip: b.set_tooltip_text(tooltip)
    b.add_css_class("nx-icon-btn")
    for c in css: b.add_css_class(c)
    return b


def divider(vertical: bool = False) -> Gtk.Separator:
    s = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL if vertical
                      else Gtk.Orientation.HORIZONTAL)
    s.add_css_class("nx-sep")
    return s


def card(title: str, child: Gtk.Widget, *, glyph: str | None = None) -> Gtk.Widget:
    inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                    margin_top=12, margin_bottom=12,
                    margin_start=14, margin_end=14)
    head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    if glyph:
        g = Gtk.Label(label=glyph)
        g.add_css_class("nx-glyph"); g.add_css_class("nx-glyph-accent")
        head.append(g)
    t = hand_label(title, size="h3")
    head.append(t)
    inner.append(head)
    inner.append(child)
    inner.add_css_class("nx-card-inner")
    return wrap_sketch(inner, ink=PALETTE.INK_DIM, jitter=1.0,
                       corner_radius=10.0, line_width=1.4)


# ── shake animation (used by the lock entry on bad password) ────────────
def shake(widget: Gtk.Widget, *, amplitude: int = 8, duration_ms: int = 350):
    """Translate the widget left/right a few times. Uses Gtk.Fixed isn't
    needed — we just abuse a CSS class swap timer."""
    css = ["nx-shake-l", "nx-shake-r"] * 4
    interval = max(1, duration_ms // len(css))

    def step(idx_box):
        i = idx_box[0]
        if i >= len(css):
            for c in ("nx-shake-l", "nx-shake-r"):
                widget.remove_css_class(c)
            return False
        for c in ("nx-shake-l", "nx-shake-r"):
            widget.remove_css_class(c)
        widget.add_css_class(css[i])
        idx_box[0] = i + 1
        return True

    GLib.timeout_add(interval, step, [0])


# ── CSS theme ────────────────────────────────────────────────────────────
CSS = b"""
@define-color nx-bg          #0f1420;
@define-color nx-panel       #1a1e2a;
@define-color nx-card        #2a2e3a;
@define-color nx-card-2      #2a2e3a;
@define-color nx-ink         #e8edf5;
@define-color nx-ink-dim     #9aa0ad;
@define-color nx-accent      #c8ccd6;
@define-color nx-accent-2    #c8ccd6;
@define-color nx-warn        #9aa0ad;
@define-color nx-ok          #c8ccd6;
@define-color nx-pink        #9aa0ad;

* {
  -gtk-secondary-caret-color: @nx-accent;
}

window.nx-window, .nx-window {
  background: @nx-bg;
  color: @nx-ink;
}

label, button, entry, passwordentry {
  color: @nx-ink;
}

.nx-h1 {
  font-family: "Inter Display", cursive;
  font-size: 36px;
  font-weight: 700;
  color: @nx-ink;
}

.nx-h2 {
  font-family: "Inter Display", cursive;
  font-size: 26px;
  color: @nx-ink;
}

.nx-h3 {
  font-family: "Inter Display", cursive;
  font-size: 20px;
  color: @nx-ink;
}

.nx-body {
  font-family: "Inter Display", cursive;
  font-size: 16px;
  line-height: 1.4;
  color: @nx-ink;
}

.nx-mono {
  font-family: "JetBrainsMono Nerd Font", "JetBrainsMono Nerd Font Mono",
               "JetBrains Mono", monospace;
  font-size: 13px;
}

.nx-dim       { color: @nx-ink-dim; }
.nx-accent    { color: @nx-accent; }
.nx-warn      { color: @nx-warn; }
.nx-ok        { color: @nx-ok; }

.nx-glyph {
  font-family: "JetBrainsMono Nerd Font", "Font Awesome 6 Free",
               "Font Awesome", "JetBrains Mono", monospace;
  font-size: 16px;
}
.nx-glyph-accent { color: @nx-accent; }

.nx-card-inner {
  background: alpha(@nx-card, 0.85);
  border-radius: 8px;
}

.nx-icon-btn {
  background: transparent;
  border: none;
  padding: 6px 8px;
  border-radius: 6px;
}
.nx-icon-btn:hover {
  background: alpha(@nx-ink, 0.08);
}

button.nx-primary {
  background: @nx-accent;
  color: #1a1e2a;
  font-family: "Inter Display", cursive;
  font-weight: 700;
  font-size: 18px;
  padding: 6px 18px;
  border-radius: 6px;
  border: 1px solid alpha(#000, 0.35);
}
button.nx-primary:hover {
  background: shade(@nx-accent, 1.10);
}

button {
  background: @nx-card;
  color: @nx-ink;
  border: 1px solid alpha(@nx-ink, 0.18);
  border-radius: 6px;
  padding: 4px 12px;
}
button:hover  { background: @nx-card-2; }

entry, passwordentry {
  background: @nx-bg;
  color: @nx-ink;
  border: 1px solid alpha(@nx-ink, 0.20);
  border-radius: 6px;
  padding: 6px 10px;
  font-family: "JetBrainsMono Nerd Font", "JetBrains Mono", monospace;
  font-size: 13px;
}
entry:focus, passwordentry:focus {
  border-color: @nx-accent;
}

.nx-sidebar {
  background: @nx-panel;
  border-right: 1px solid alpha(@nx-ink, 0.10);
}

.nx-topbar {
  background: @nx-panel;
  border-bottom: 1px solid alpha(@nx-ink, 0.10);
  padding: 6px 10px;
}

.nx-statusbar {
  background: @nx-panel;
  border-top: 1px solid alpha(@nx-ink, 0.10);
  padding: 4px 10px;
  color: @nx-ink-dim;
  font-family: "JetBrainsMono Nerd Font", "JetBrains Mono", monospace;
  font-size: 11px;
}

.nx-sep {
  background: alpha(@nx-ink, 0.08);
}

.nx-az-letter {
  font-family: "Inter Display", cursive;
  font-size: 22px;
  color: @nx-accent;
  padding: 6px 12px 0px 12px;
}

.nx-az-row {
  background: transparent;
  padding: 6px 12px;
  border-radius: 4px;
}
.nx-az-row:hover { background: alpha(@nx-ink, 0.06); }
.nx-az-row:selected { background: alpha(@nx-accent, 0.15); }

.nx-shake-l { margin-left: -8px; margin-right: 8px; }
.nx-shake-r { margin-left:  8px; margin-right: -8px; }

.nx-lock-bg {
  background: @nx-bg;
}

.nx-lock-card {
  background: @nx-panel;
  border: 1.8px dashed alpha(@nx-ink-dim, 0.85);
  border-radius: 14px;
  padding: 6px;
  box-shadow: 0 6px 22px alpha(black, 0.35);
}

.nx-lock-card > * {
  border-radius: 10px;
}
"""


def install_css() -> None:
    """Install the CSS provider on the default display. Idempotent."""
    display = Gdk.Display.get_default()
    if display is None:
        return
    if getattr(install_css, "_installed", False):
        return
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS, len(CSS))
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
    install_css._installed = True  # type: ignore[attr-defined]
