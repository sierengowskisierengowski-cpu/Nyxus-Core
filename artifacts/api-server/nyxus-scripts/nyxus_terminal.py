#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Terminal — Graffiti Frame · Spray Can Controls · NYXUS BG        ║
# ║  Idle Blur · Spray Selection · Caveat font · GTK4 + VTE                 ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-TERM-2026-SIERENGOWSKI-LOCKED         ║
# ╚══════════════════════════════════════════════════════════════════════════╝
import gi, sys, os, math, random, time, traceback
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Pango, Gio

# VTE — try GTK4 version first, fall back to GTK3 version
HAS_VTE = False
_vte_err_msg = ""
for _vte_ver in ("3.91", "2.91"):
    try:
        try:
            gi.require_version("Vte", _vte_ver)
        except ValueError:
            pass
        from gi.repository import Vte
        HAS_VTE = True
        break
    except Exception as _e:
        _vte_err_msg = str(_e)

# ── Dimensions ────────────────────────────────────────────────────────────────
WIN_W, WIN_H   = 1100, 680
BORDER_TOP     = 70   # title bar height
BORDER_BOTTOM  = 28
BORDER_SIDE    = 28
IDLE_SECS      = 90

# ── NYXUS palette ────────────────────────────────────────────────────────────
C_PINK   = (1.00, 0.00, 1.00)
C_PURPLE = (0.80, 0.00, 1.00)
C_BLUE   = (0.00, 0.53, 1.00)
C_GREEN  = (0.22, 1.00, 0.08)
C_YELLOW = (1.00, 1.00, 0.00)
C_ORANGE = (1.00, 0.33, 0.00)
PALETTE  = [C_PINK, C_PURPLE, C_BLUE, C_GREEN, C_YELLOW, C_ORANGE]
C_DARK   = (0.031, 0.031, 0.055)  # #08080e

# Spray-can button areas (cx, cy)
CAN_CLOSE = {"cx": WIN_W - 44,  "cy": 32, "color": (0.95, 0.15, 0.15)}
CAN_MIN   = {"cx": WIN_W - 96,  "cy": 32, "color": (1.00, 0.82, 0.00)}
CAN_MAX   = {"cx": WIN_W - 148, "cy": 32, "color": (0.16, 0.85, 0.16)}

# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = b"""
window { background-color: #08080e; }
vte-terminal {
    background-color: transparent;
    color: rgba(232,224,245,0.92);
    font-family: 'Caveat', 'Patrick Hand', 'DejaVu Sans Mono', monospace;
}
"""

# ── Cairo helpers ─────────────────────────────────────────────────────────────

def _rng(seed):
    return random.Random(int(seed) % 999983)


def spray_dots(cr, cx, cy, color, n=60, spread=18, alpha_max=0.55, rng=None):
    r, g, b = color
    if rng is None:
        rng = random.Random()
    for _ in range(n):
        dx = rng.gauss(0, spread * 0.5)
        dy = rng.gauss(0, spread * 0.5)
        dist = math.sqrt(dx * dx + dy * dy) / max(spread, 1)
        alpha = alpha_max * max(0, 1 - dist) * rng.uniform(0.3, 1.0)
        size = rng.uniform(0.8, 3.5) * max(0, 1 - dist * 0.5)
        cr.set_source_rgba(r, g, b, alpha)
        cr.arc(cx + dx, cy + dy, max(0.3, size), 0, math.pi * 2)
        cr.fill()


def _draw_drip(cr, x, top_y, color, length, rng):
    r, g, b = color
    drip_w = rng.uniform(4, 9)
    cr.set_source_rgba(r, g, b, 0.72)
    cr.arc(x, top_y, drip_w * 0.7, 0, math.pi * 2)
    cr.fill()
    wobble = rng.uniform(-5, 5)
    cr.set_source_rgba(r, g, b, 0.60)
    cr.move_to(x - drip_w / 2, top_y)
    cr.curve_to(x - drip_w / 2 + wobble, top_y + length * 0.4,
                x + drip_w / 2 + wobble, top_y + length * 0.6,
                x + drip_w * 0.3, top_y + length)
    cr.curve_to(x - drip_w * 0.3, top_y + length,
                x - drip_w / 2 - wobble, top_y + length * 0.6,
                x - drip_w / 2, top_y)
    cr.fill()
    cr.set_source_rgba(r, g, b, 0.50)
    cr.arc(x + wobble * 0.3, top_y + length, drip_w * 0.45, 0, math.pi * 2)
    cr.fill()


def _draw_star(cr, cx, cy, color, radius):
    r, g, b = color
    for i in range(6):
        angle = math.radians(i * 30)
        cr.set_source_rgba(r, g, b, 0.75)
        cr.set_line_width(2.5)
        cr.move_to(cx - math.cos(angle) * radius, cy - math.sin(angle) * radius)
        cr.line_to(cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)
        cr.stroke()
    cr.set_source_rgba(r, g, b, 0.65)
    cr.arc(cx, cy, radius * 0.28, 0, math.pi * 2)
    cr.fill()


def _draw_graffiti_word(cr, cx, cy, word, color1, color2, size, rng):
    import cairo as _cairo
    r1, g1, b1 = color1
    r2, g2, b2 = color2
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(size)
    ext = cr.text_extents(word)
    tx = cx - ext.width / 2 - ext.x_bearing
    ty = cy - ext.height / 2 - ext.y_bearing

    # Outer glow passes
    for blur_r, alpha in [(16, 0.06), (10, 0.12), (6, 0.20), (3, 0.30)]:
        cr.set_source_rgba(r1, g1, b1, alpha)
        cr.set_line_width(blur_r * 2)
        cr.move_to(tx + 1, ty + 1)
        cr.text_path(word)
        cr.stroke()

    # Dark outline
    cr.set_source_rgba(0.04, 0.01, 0.07, 0.90)
    cr.set_line_width(7)
    cr.move_to(tx, ty)
    cr.text_path(word)
    cr.stroke()

    # Gradient fill
    h_span = max(ext.height, 1)
    pat = _cairo.LinearGradient(0, ty, 0, ty + h_span)
    pat.add_color_stop_rgba(0.0, r1, g1, b1, 0.95)
    pat.add_color_stop_rgba(0.5, (r1 + r2) / 2, (g1 + g2) / 2, (b1 + b2) / 2, 0.90)
    pat.add_color_stop_rgba(1.0, r2, g2, b2, 0.95)
    cr.set_source(pat)
    cr.move_to(tx, ty)
    cr.text_path(word)
    cr.fill()

    # White inner highlight
    cr.set_source_rgba(1, 1, 1, 0.25)
    cr.set_line_width(1.5)
    cr.move_to(tx + 2, ty + 2)
    cr.text_path(word)
    cr.stroke()

    # Scatter spray
    for _ in range(8):
        px = tx + rng.uniform(0, ext.width)
        py = ty + rng.uniform(-size * 0.5, size * 0.5)
        spray_dots(cr, px, py, color1 if rng.random() < 0.5 else color2,
                   n=10, spread=14, alpha_max=0.20, rng=rng)


# ── Terminal background (graffiti wall with NYXUS watermark) ──────────────────

def draw_terminal_bg(cr, x, y, w, h):
    """Full graffiti bg — faint brick outline + NYXUS tag + blobs + drips."""
    rng = _rng(42)
    import cairo as _cairo

    # Base dark fill
    cr.set_source_rgb(*C_DARK)
    cr.rectangle(x, y, w, h)
    cr.fill()

    # Faint ghost brick lines (very subtle, not the border style)
    BH2, M2 = 26, 3
    row2 = 0; yy2 = y
    while yy2 < y + h:
        off2 = 40 if row2 % 2 else 0
        xx2 = x - off2
        while xx2 < x + w + 80:
            bw2 = 82 + rng.randint(-10, 10)
            lx = max(x, xx2 + M2); rx = min(x + w, xx2 + bw2 - M2)
            if rx - lx > 4:
                cr.set_line_width(0.5)
                cr.set_source_rgba(0.25, 0.16, 0.08, 0.09)
                cr.rectangle(lx, yy2 + M2, rx - lx, BH2 - M2 * 2)
                cr.stroke()
            xx2 += bw2
        yy2 += BH2; row2 += 1

    # Large background paint blobs
    blob_data = [
        (0.08, 0.15, C_GREEN,  60), (0.92, 0.12, C_ORANGE, 50),
        (0.50, 0.08, C_BLUE,   44), (0.22, 0.80, C_YELLOW, 55),
        (0.78, 0.75, C_PURPLE, 62), (0.15, 0.48, C_PINK,   40),
        (0.85, 0.50, C_BLUE,   48), (0.40, 0.30, C_ORANGE, 35),
        (0.62, 0.65, C_GREEN,  42), (0.30, 0.60, C_PURPLE, 32),
        (0.70, 0.25, C_PINK,   36), (0.55, 0.88, C_YELLOW, 46),
        (0.05, 0.72, C_BLUE,   28), (0.95, 0.40, C_GREEN,  30),
        (0.48, 0.52, C_ORANGE, 24), (0.20, 0.20, C_PURPLE, 22),
        (0.80, 0.82, C_PINK,   26), (0.35, 0.42, C_YELLOW, 20),
        (0.65, 0.38, C_BLUE,   18), (0.12, 0.90, C_ORANGE, 22),
    ]
    for bfx, bfy, bcol, brad in blob_data:
        bpx = x + w * bfx; bpy = y + h * bfy
        cr.set_source_rgba(*bcol, rng.uniform(0.08, 0.20))
        cr.arc(bpx, bpy, brad, 0, math.pi * 2)
        cr.fill()
        spray_dots(cr, bpx, bpy, bcol, n=70, spread=int(brad * 1.6),
                   alpha_max=0.22, rng=rng)

    # Splatter streaks
    for _ in range(30):
        sx = rng.uniform(x, x + w); sy = rng.uniform(y, y + h)
        ex = sx + rng.uniform(-140, 140); ey = sy + rng.uniform(-20, 20)
        col = rng.choice(PALETTE)
        cr.set_source_rgba(*col, rng.uniform(0.10, 0.35))
        cr.set_line_width(rng.uniform(0.6, 2.5))
        cr.move_to(sx, sy); cr.line_to(ex, ey); cr.stroke()
        spray_dots(cr, ex, ey, col, n=10, spread=7, alpha_max=0.28, rng=rng)

    # Dense small dot field
    for _ in range(100):
        bpx = rng.uniform(x + 4, x + w - 4)
        bpy = rng.uniform(y + 4, y + h - 4)
        brad = rng.uniform(0.8, 4.0)
        col = rng.choice(PALETTE)
        cr.set_source_rgba(*col, rng.uniform(0.18, 0.55))
        cr.arc(bpx, bpy, brad, 0, math.pi * 2); cr.fill()

    # BIG NYXUS background watermark — fills the terminal area
    _draw_graffiti_word(cr, x + w * 0.5, y + h * 0.44, "NYXUS",
                        C_PINK, C_PURPLE, min(w * 0.55, 320), rng)

    # TERMINAL crew tag below
    _draw_graffiti_word(cr, x + w * 0.5, y + h * 0.78, "TERMINAL",
                        C_BLUE, C_GREEN, min(w * 0.24, 80), rng)

    # Stars
    star_pts = [
        (x + w * 0.04, y + h * 0.55, C_YELLOW, 18),
        (x + w * 0.96, y + h * 0.48, C_PINK,   14),
        (x + w * 0.46, y + h * 0.94, C_GREEN,  12),
        (x + w * 0.88, y + h * 0.88, C_ORANGE, 10),
        (x + w * 0.06, y + h * 0.25, C_BLUE,   10),
    ]
    for sx2, sy2, scol, sr in star_pts:
        _draw_star(cr, sx2, sy2, scol, sr)

    # Drips from top edge of inner area
    drip_data = [
        (x + w * 0.13, y, C_PINK,   h * 0.28),
        (x + w * 0.32, y, C_GREEN,  h * 0.20),
        (x + w * 0.58, y, C_ORANGE, h * 0.25),
        (x + w * 0.77, y, C_BLUE,   h * 0.18),
        (x + w * 0.90, y, C_YELLOW, h * 0.15),
    ]
    for dx2, dy2, dcol, dlen in drip_data:
        _draw_drip(cr, dx2, dy2, dcol, dlen, rng)

    # Subtle notebook rules on top for readability
    cr.set_line_width(0.30)
    for ry in range(int(y) + 24, int(y + h), 24):
        cr.set_source_rgba(1, 1, 1, 0.028)
        cr.move_to(x, ry); cr.line_to(x + w, ry); cr.stroke()


# ── Graffiti frame (no bricks — pure spray paint) ─────────────────────────────

def draw_graffiti_frame(cr, w, h, hovering_can=None):
    """Paint-sprayed window frame — neon splatter, drips, tags, NO bricks."""
    import cairo as _cairo
    rng = _rng(77)

    # Dark base for all border strips
    cr.set_source_rgb(*C_DARK)
    # Top bar
    cr.rectangle(0, 0, w, BORDER_TOP); cr.fill()
    # Bottom bar
    cr.rectangle(0, h - BORDER_BOTTOM, w, BORDER_BOTTOM); cr.fill()
    # Left strip
    cr.rectangle(0, 0, BORDER_SIDE, h); cr.fill()
    # Right strip
    cr.rectangle(w - BORDER_SIDE, 0, BORDER_SIDE, h); cr.fill()

    # ── Heavy paint splatter blobs on frame strips ──
    frame_blobs = [
        # Top bar blobs
        (w * 0.08, BORDER_TOP * 0.5,   C_GREEN,  28),
        (w * 0.20, BORDER_TOP * 0.6,   C_ORANGE, 22),
        (w * 0.35, BORDER_TOP * 0.4,   C_BLUE,   20),
        (w * 0.55, BORDER_TOP * 0.5,   C_PURPLE, 18),
        (w * 0.68, BORDER_TOP * 0.6,   C_PINK,   24),
        (w * 0.82, BORDER_TOP * 0.5,   C_YELLOW, 18),
        # Bottom bar
        (w * 0.15, h - BORDER_BOTTOM * 0.5, C_BLUE,   16),
        (w * 0.42, h - BORDER_BOTTOM * 0.5, C_GREEN,  18),
        (w * 0.70, h - BORDER_BOTTOM * 0.5, C_ORANGE, 14),
        # Left strip
        (BORDER_SIDE * 0.5, h * 0.22, C_PINK,   20),
        (BORDER_SIDE * 0.5, h * 0.50, C_YELLOW, 18),
        (BORDER_SIDE * 0.5, h * 0.78, C_PURPLE, 16),
        # Right strip
        (w - BORDER_SIDE * 0.5, h * 0.28, C_ORANGE, 20),
        (w - BORDER_SIDE * 0.5, h * 0.55, C_GREEN,  18),
        (w - BORDER_SIDE * 0.5, h * 0.78, C_BLUE,   16),
    ]
    for bx, by, col, brad in frame_blobs:
        cr.set_source_rgba(*col, rng.uniform(0.30, 0.55))
        cr.arc(bx, by, brad, 0, math.pi * 2); cr.fill()
        spray_dots(cr, bx, by, col, n=55, spread=int(brad * 1.8),
                   alpha_max=0.42, rng=rng)

    # ── Thick neon border edge lines (inner edge glow) ──
    neon_colors = [C_PINK, C_PURPLE, C_BLUE, C_GREEN, C_YELLOW, C_ORANGE]
    # Bottom edge of title bar — rainbow strip
    pat = _cairo.LinearGradient(0, BORDER_TOP - 3, w, BORDER_TOP - 3)
    for i, col in enumerate(neon_colors):
        pat.add_color_stop_rgb(i / (len(neon_colors) - 1), *col)
    cr.set_source(pat)
    cr.rectangle(0, BORDER_TOP - 3, w, 4); cr.fill()

    # Left edge of left border
    cr.set_source_rgba(*C_PINK, 0.60)
    cr.set_line_width(2)
    cr.move_to(BORDER_SIDE, BORDER_TOP)
    cr.line_to(BORDER_SIDE, h - BORDER_BOTTOM)
    cr.stroke()
    spray_dots(cr, BORDER_SIDE, h * 0.45, C_PINK, n=30, spread=8, alpha_max=0.30, rng=rng)

    # Right edge of right border
    cr.set_source_rgba(*C_BLUE, 0.60)
    cr.set_line_width(2)
    cr.move_to(w - BORDER_SIDE, BORDER_TOP)
    cr.line_to(w - BORDER_SIDE, h - BORDER_BOTTOM)
    cr.stroke()
    spray_dots(cr, w - BORDER_SIDE, h * 0.55, C_BLUE, n=30, spread=8, alpha_max=0.30, rng=rng)

    # Top edge of bottom bar
    cr.set_source_rgba(*C_GREEN, 0.50)
    cr.set_line_width(2)
    cr.move_to(0, h - BORDER_BOTTOM)
    cr.line_to(w, h - BORDER_BOTTOM)
    cr.stroke()

    # ── Corner splatters ──
    for cx2, cy2, col2 in [
        (0, 0, C_ORANGE), (w, 0, C_PURPLE),
        (0, h, C_GREEN),  (w, h, C_YELLOW),
    ]:
        spray_dots(cr, cx2, cy2, col2, n=45, spread=28, alpha_max=0.38, rng=rng)
        cr.set_source_rgba(*col2, 0.25)
        cr.arc(cx2, cy2, 14, 0, math.pi * 2); cr.fill()

    # ── Paint drips from top-bar bottom edge into the terminal ──
    drip_srcs = [
        (w * 0.12, BORDER_TOP, C_PINK,   28),
        (w * 0.28, BORDER_TOP, C_GREEN,  22),
        (w * 0.45, BORDER_TOP, C_ORANGE, 18),
        (w * 0.60, BORDER_TOP, C_BLUE,   24),
        (w * 0.76, BORDER_TOP, C_YELLOW, 16),
        (w * 0.90, BORDER_TOP, C_PURPLE, 20),
    ]
    for dx, dy, dcol, dlen in drip_srcs:
        _draw_drip(cr, dx, dy, dcol, dlen, rng)

    # ── Left-strip graffiti tag (NYX rotated) ──
    cr.save()
    cr.translate(BORDER_SIDE * 0.55, h * 0.50)
    cr.rotate(-math.pi / 2)
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(16)
    # Glow
    cr.set_source_rgba(*C_PINK, 0.30)
    cr.set_line_width(5)
    cr.move_to(-28, 0); cr.text_path("NYX"); cr.stroke()
    # Fill
    cr.set_source_rgba(*C_PINK, 0.80)
    cr.move_to(-28, 0); cr.show_text("NYX")
    cr.restore()
    spray_dots(cr, BORDER_SIDE * 0.5, h * 0.50, C_PINK,
               n=22, spread=BORDER_SIDE // 2, alpha_max=0.28, rng=rng)

    # ── Right-strip tag (TERM rotated) ──
    cr.save()
    cr.translate(w - BORDER_SIDE * 0.45, h * 0.50)
    cr.rotate(math.pi / 2)
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(14)
    cr.set_source_rgba(*C_BLUE, 0.28)
    cr.set_line_width(5)
    cr.move_to(-28, 0); cr.text_path("TERM"); cr.stroke()
    cr.set_source_rgba(*C_BLUE, 0.78)
    cr.move_to(-28, 0); cr.show_text("TERM")
    cr.restore()
    spray_dots(cr, w - BORDER_SIDE * 0.5, h * 0.50, C_BLUE,
               n=22, spread=BORDER_SIDE // 2, alpha_max=0.25, rng=rng)

    # ── Stars on side strips ──
    _draw_star(cr, BORDER_SIDE * 0.5, h * 0.25, C_YELLOW, 7)
    _draw_star(cr, BORDER_SIDE * 0.5, h * 0.75, C_GREEN,  6)
    _draw_star(cr, w - BORDER_SIDE * 0.5, h * 0.30, C_ORANGE, 7)
    _draw_star(cr, w - BORDER_SIDE * 0.5, h * 0.75, C_PURPLE, 6)
    _draw_star(cr, w * 0.20, h - BORDER_BOTTOM * 0.55, C_YELLOW, 5)
    _draw_star(cr, w * 0.70, h - BORDER_BOTTOM * 0.55, C_PINK, 5)

    # ── NYXUS Terminal title text in top bar ──
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(24)
    title = "NYXUS Terminal"
    ext = cr.text_extents(title)
    ty_base = BORDER_TOP / 2 + ext.height / 2 - ext.y_bearing - ext.height

    # Pink glow
    cr.set_source_rgba(1, 0, 1, 0.35)
    cr.set_line_width(4)
    cr.move_to(20, ty_base + 1)
    cr.text_path(title); cr.stroke()
    # White fill
    cr.set_source_rgba(1, 1, 1, 0.92)
    cr.move_to(20, ty_base)
    cr.show_text(title)

    # Spray scatter around title
    spray_dots(cr, 120, BORDER_TOP * 0.5, C_PINK,
               n=18, spread=22, alpha_max=0.22, rng=rng)

    # ── Spray can buttons ──
    cans = [(CAN_CLOSE, "close"), (CAN_MIN, "min"), (CAN_MAX, "max")]
    for can, key in cans:
        _draw_spray_can(cr, can["cx"], can["cy"], can["color"],
                        hovered=(hovering_can == key))

    # Can labels
    labels = [("✕", CAN_CLOSE), ("▂", CAN_MIN), ("▣", CAN_MAX)]
    for lbl, can in labels:
        cr.select_font_face("Caveat", 0, 0)
        cr.set_font_size(11)
        ext2 = cr.text_extents(lbl)
        cr.set_source_rgba(1, 1, 1, 0.42)
        cr.move_to(can["cx"] - ext2.width / 2 - ext2.x_bearing, BORDER_TOP - 6)
        cr.show_text(lbl)


def _draw_spray_can(cr, cx, cy, color, hovered=False):
    r, g, b = color
    can_w, can_h = 20, 34
    bx, by = cx - can_w / 2, cy - can_h / 2 + 4

    # Shadow
    cr.set_source_rgba(0, 0, 0, 0.50)
    cr.rectangle(bx + 3, by + 4, can_w, can_h); cr.fill()

    # Body
    cr.set_source_rgb(r * 0.65, g * 0.65, b * 0.65)
    cr.rectangle(bx, by, can_w, can_h); cr.fill()

    # Main color band
    cr.set_source_rgb(r, g, b)
    cr.rectangle(bx + 3, by + 5, can_w - 6, can_h - 10); cr.fill()

    # Highlight
    cr.set_source_rgba(1, 1, 1, 0.26)
    cr.rectangle(bx + 3, by + 5, 4, can_h - 10); cr.fill()

    # Cap
    cap_w, cap_h = 14, 6
    cr.set_source_rgb(0.70, 0.70, 0.74)
    cr.rectangle(cx - cap_w / 2, by - cap_h, cap_w, cap_h); cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.20)
    cr.rectangle(cx - cap_w / 2, by - cap_h, cap_w, 2); cr.fill()

    # Nozzle tip
    cr.set_source_rgb(0.48, 0.50, 0.54)
    cr.rectangle(cx + cap_w / 2 - 3, by - cap_h - 6, 9, 5); cr.fill()

    # Hover — spray cloud
    if hovered:
        rng2 = random.Random()
        spray_dots(cr, cx + cap_w / 2 + 14, by - cap_h - 2,
                   color, n=35, spread=12, alpha_max=0.50, rng=rng2)


# ── Idle overlay ──────────────────────────────────────────────────────────────

def draw_idle_overlay(cr, w, h, phase):
    alpha = min(phase, 1.0)
    cr.set_source_rgba(0.03, 0.02, 0.08, alpha * 0.90)
    cr.rectangle(0, 0, w, h); cr.fill()

    rng = _rng(999)
    for _ in range(14):
        bx = rng.uniform(0, w); by = rng.uniform(0, h)
        bw = rng.uniform(80, 300)
        bcol = rng.choice(PALETTE)
        cr.set_source_rgba(*bcol, alpha * 0.035)
        cr.arc(bx, by, bw * 0.6, 0, math.pi * 2); cr.fill()

    if alpha < 0.25:
        return

    cx_lgo, cy_lgo = w / 2, h / 2 - 30
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(72)
    logo = "NYXUS"
    ext = cr.text_extents(logo)
    lx = cx_lgo - ext.width / 2 - ext.x_bearing
    ly = cy_lgo

    for blur_a in [0.06, 0.12, 0.20]:
        cr.set_source_rgba(*C_PINK, alpha * blur_a)
        cr.set_line_width(14)
        cr.move_to(lx + 1, ly + 1)
        cr.text_path(logo); cr.stroke()
    cr.set_source_rgba(1, 0, 1, alpha * 0.94)
    cr.move_to(lx, ly); cr.show_text(logo)

    cr.select_font_face("Caveat", 0, 0)
    cr.set_font_size(18)
    sub = "terminal sleeping — press any key"
    ext2 = cr.text_extents(sub)
    cr.set_source_rgba(1, 1, 1, alpha * 0.55)
    cr.move_to(w / 2 - ext2.width / 2 - ext2.x_bearing, cy_lgo + 58)
    cr.show_text(sub)

    rng2 = _rng(77)
    for i, col in enumerate(PALETTE[:4]):
        dx = lx + (i + 0.5) * ext.width / 4
        _draw_drip(cr, dx, cy_lgo + 10, col, h * 0.22, rng2)


# ── Spray-paint selection overlay ─────────────────────────────────────────────

class SelSplatter:
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.color = color
        self.alpha = 0.75
        self.size = random.uniform(10, 26)
        self.born = time.monotonic()

    @property
    def alive(self):
        return (time.monotonic() - self.born) < 4.0

    @property
    def opacity(self):
        age = time.monotonic() - self.born
        if age < 2.5:
            return self.alpha
        return self.alpha * max(0, 1 - (age - 2.5) / 1.5)

    def draw(self, cr):
        op = self.opacity
        if op <= 0:
            return
        rng = random.Random()
        spray_dots(cr, self.x, self.y, self.color,
                   n=32, spread=self.size, alpha_max=op * 0.75, rng=rng)
        cr.set_source_rgba(*self.color, op * 0.42)
        cr.arc(self.x, self.y, self.size * 0.32, 0, math.pi * 2)
        cr.fill()


# ── VTE-missing fallback (drawn, not a widget) ────────────────────────────────

def draw_no_vte(cr, x, y, w, h):
    """Draw a hand-drawn error card when VTE is missing."""
    import cairo as _cairo
    rng = _rng(55)

    # Error card background
    cr.set_source_rgba(0.10, 0.04, 0.18, 0.92)
    cr.rectangle(x + 20, y + 20, w - 40, h - 40); cr.fill()

    # Sketchy border
    cr.set_source_rgba(*C_ORANGE, 0.80)
    cr.set_line_width(2.5)
    for i in range(3):
        off = i * 1.5
        cr.rectangle(x + 22 + off, y + 22 + off, w - 44 - off * 2, h - 44 - off * 2)
        cr.stroke()

    # Spray scatter on card edges
    spray_dots(cr, x + 20, y + 20, C_ORANGE, n=30, spread=14, alpha_max=0.40, rng=rng)
    spray_dots(cr, x + w - 20, y + h - 20, C_YELLOW, n=25, spread=12, alpha_max=0.35, rng=rng)

    # Warning symbol
    cx2, cy2 = x + w / 2, y + 60
    cr.set_source_rgba(*C_ORANGE, 0.80)
    cr.set_line_width(3)
    cr.move_to(cx2, cy2 - 20); cr.line_to(cx2 - 18, cy2 + 14); cr.line_to(cx2 + 18, cy2 + 14); cr.close_path()
    cr.stroke()
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(20)
    cr.set_source_rgba(*C_YELLOW, 0.90)
    ext = cr.text_extents("!")
    cr.move_to(cx2 - ext.width / 2 - ext.x_bearing, cy2 + 10)
    cr.show_text("!")

    # Heading
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(28)
    head = "VTE terminal not found"
    ext = cr.text_extents(head)
    # Glow
    cr.set_source_rgba(*C_ORANGE, 0.25)
    cr.set_line_width(4)
    cr.move_to(x + w / 2 - ext.width / 2 - ext.x_bearing + 1, y + h / 2 - 40 + 1)
    cr.text_path(head); cr.stroke()
    cr.set_source_rgba(1.0, 0.85, 0.50, 0.95)
    cr.move_to(x + w / 2 - ext.width / 2 - ext.x_bearing, y + h / 2 - 40)
    cr.show_text(head)

    # Install commands
    cr.select_font_face("Caveat", 0, 0)
    cr.set_font_size(20)
    lines = [
        ("run this in your terminal:", C_YELLOW, 0.70),
        ("sudo pacman -S vte4 python-gobject",   C_GREEN,  0.92),
        ("",                                     C_GREEN,  0.00),
        ("or re-run the NYXUS installer:",        C_YELLOW, 0.65),
        ("curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_install.sh | bash",
                                                 C_BLUE,   0.88),
        ("",                                     C_BLUE,   0.00),
        ("then relaunch NYXUS Terminal",          C_PINK,   0.75),
    ]
    cy3 = y + h / 2 + 4
    for txt, col, alp in lines:
        if not txt:
            cy3 += 10
            continue
        ext2 = cr.text_extents(txt)
        # Keep long lines from overflowing
        if ext2.width > w - 80:
            cr.set_font_size(14)
            ext2 = cr.text_extents(txt)
        cr.set_source_rgba(*col, alp)
        cr.move_to(x + w / 2 - ext2.width / 2 - ext2.x_bearing, cy3)
        cr.show_text(txt)
        cr.set_font_size(20)
        cy3 += 32

    # Spray dots around the text block
    spray_dots(cr, x + 40, y + h * 0.60, C_PINK, n=20, spread=16, alpha_max=0.28, rng=rng)
    spray_dots(cr, x + w - 40, y + h * 0.60, C_GREEN, n=20, spread=16, alpha_max=0.28, rng=rng)


# ── Main Application ──────────────────────────────────────────────────────────

class NyxusTerminal(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.terminal",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self._hovering_can = None
        self._last_input = time.monotonic()
        self._idle_phase = 0.0
        self._splatters: list[SelSplatter] = []
        self._btn_pressed = False
        self._sel_color_idx = 0
        self._anim_t = 0.0
        self._bg_surface = None   # cached static bg surface
        self._bg_size = (0, 0)

    def do_activate(self):
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self, title="NYXUS Terminal")
        self.win.set_default_size(WIN_W, WIN_H)
        self.win.set_decorated(False)
        self.win.set_resizable(True)

        overlay = Gtk.Overlay()
        self.win.set_child(overlay)

        # Layer 0 — graffiti background + frame (full window)
        self._chrome_da = Gtk.DrawingArea()
        self._chrome_da.set_draw_func(self._draw_chrome_bg, None)
        self._chrome_da.set_can_focus(False)
        overlay.set_child(self._chrome_da)

        if HAS_VTE:
            self._vte = Vte.Terminal()
            self._vte.set_halign(Gtk.Align.FILL)
            self._vte.set_valign(Gtk.Align.FILL)
            self._vte.set_margin_top(BORDER_TOP)
            self._vte.set_margin_bottom(BORDER_BOTTOM)
            self._vte.set_margin_start(BORDER_SIDE)
            self._vte.set_margin_end(BORDER_SIDE)
            self._setup_vte()
            overlay.add_overlay(self._vte)

        # Layer 2 — spray selection overlay
        self._sel_da = Gtk.DrawingArea()
        self._sel_da.set_draw_func(self._draw_sel_overlay, None)
        self._sel_da.set_can_focus(False)
        self._sel_da.set_halign(Gtk.Align.FILL)
        self._sel_da.set_valign(Gtk.Align.FILL)
        overlay.add_overlay(self._sel_da)
        overlay.set_clip_overlay(self._sel_da, False)

        # Layer 3 — idle overlay
        self._idle_da = Gtk.DrawingArea()
        self._idle_da.set_draw_func(self._draw_idle, None)
        self._idle_da.set_can_focus(False)
        self._idle_da.set_halign(Gtk.Align.FILL)
        self._idle_da.set_valign(Gtk.Align.FILL)
        overlay.add_overlay(self._idle_da)
        overlay.set_clip_overlay(self._idle_da, False)

        # ── Input controllers ──
        click = Gtk.GestureClick()
        click.set_button(1)
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect("pressed",  self._on_click_pressed)
        click.connect("released", self._on_click_released)
        self._chrome_da.add_controller(click)

        motion = Gtk.EventControllerMotion()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        motion.connect("motion", self._on_motion)
        self.win.add_controller(motion)

        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect("key-pressed", self._on_key)
        self.win.add_controller(key_ctrl)

        win_click = Gtk.GestureClick()
        win_click.set_button(0)
        win_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        win_click.connect("pressed",  self._on_win_press)
        win_click.connect("released", self._on_win_release)
        self.win.add_controller(win_click)

        # Timers — slow anim (500ms), decay (150ms), idle (5s)
        GLib.timeout_add(500, self._animate)
        GLib.timeout_add(5000, self._check_idle)
        GLib.timeout_add(150, self._decay_splatters)

        self.win.present()

    # ── VTE setup ─────────────────────────────────────────────────────────────
    def _setup_vte(self):
        vte = self._vte
        fdesc = Pango.FontDescription.from_string("Caveat 15")
        vte.set_font(fdesc)
        vte.set_allow_bold(True)
        vte.set_scroll_on_output(True)
        vte.set_scroll_on_keystroke(True)
        vte.set_scrollback_lines(50000)
        vte.set_mouse_autohide(True)
        try: vte.set_cell_height_scale(1.05)
        except AttributeError: pass
        try: vte.set_allow_hyperlink(True)
        except AttributeError: pass
        try: vte.set_enable_sixel_graphics(True)
        except AttributeError: pass

        # Background — slightly transparent so graffiti watermark shows through
        bg = Gdk.RGBA(); bg.red=0.04; bg.green=0.02; bg.blue=0.10; bg.alpha=0.80
        fg = Gdk.RGBA(); fg.red=0.92; fg.green=0.88; fg.blue=0.98; fg.alpha=1.0
        vte.set_color_background(bg)
        vte.set_color_foreground(fg)

        # Spray-paint selection — neon orange blob
        hl    = Gdk.RGBA(); hl.red=1.0; hl.green=0.34; hl.blue=0.0; hl.alpha=0.60
        hl_fg = Gdk.RGBA(); hl_fg.red=1.0; hl_fg.green=1.0; hl_fg.blue=1.0; hl_fg.alpha=1.0
        try:
            vte.set_color_highlight(hl)
            vte.set_color_highlight_foreground(hl_fg)
        except AttributeError: pass

        # Neon pink cursor
        cur = Gdk.RGBA(); cur.red=1.0; cur.green=0.0; cur.blue=1.0; cur.alpha=1.0
        vte.set_color_cursor(cur)

        def c(r, g, b):
            col = Gdk.RGBA(); col.red=r; col.green=g; col.blue=b; col.alpha=1; return col
        colors = [
            c(0.08, 0.06, 0.14), c(1.00, 0.20, 0.20), c(0.22, 1.00, 0.08),
            c(1.00, 1.00, 0.00), c(0.00, 0.53, 1.00), c(1.00, 0.00, 1.00),
            c(0.00, 0.85, 1.00), c(0.90, 0.88, 0.96), c(0.30, 0.22, 0.44),
            c(1.00, 0.40, 0.40), c(0.50, 1.00, 0.40), c(1.00, 1.00, 0.50),
            c(0.40, 0.75, 1.00), c(1.00, 0.40, 1.00), c(0.40, 1.00, 1.00),
            c(1.00, 1.00, 1.00),
        ]
        vte.set_colors(fg, bg, colors)

        shell = os.environ.get("SHELL", "/bin/bash")
        env = dict(os.environ)
        env.update({"TERM": "xterm-256color", "COLORTERM": "truecolor",
                    "TERM_PROGRAM": "nyxus-terminal", "FORCE_COLOR": "3"})
        env_list = [f"{k}={v}" for k, v in env.items()]
        vte.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.path.expanduser("~"),
            [shell],
            env_list,
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None, None, -1, None, None)

        vte.connect("child-exited", lambda *_: self.quit())

    # ── Draw callbacks ─────────────────────────────────────────────────────────
    def _draw_chrome_bg(self, area, cr, w, h, _):
        self._anim_t += 0.015
        inner_x = BORDER_SIDE
        inner_y = BORDER_TOP
        inner_w = w - BORDER_SIDE * 2
        inner_h = h - BORDER_TOP - BORDER_BOTTOM

        # Cache the static terminal BG so we only redraw it on resize
        if (self._bg_surface is None or self._bg_size != (w, h)):
            import cairo as _cairo
            surf = cr.get_target().create_similar(
                _cairo.Content.COLOR_ALPHA, w, h)
            bk = _cairo.Context(surf)
            if inner_w > 0 and inner_h > 0:
                draw_terminal_bg(bk, inner_x, inner_y, inner_w, inner_h)
            self._bg_surface = surf
            self._bg_size = (w, h)

        cr.set_source_surface(self._bg_surface, 0, 0)
        cr.paint()

        # Frame redraws every tick (spray can hover, drip animation, etc.)
        draw_graffiti_frame(cr, w, h, self._hovering_can)

        # If VTE not available, draw the error card over the inner area
        if not HAS_VTE and inner_w > 0 and inner_h > 0:
            draw_no_vte(cr, inner_x, inner_y, inner_w, inner_h)

    def _draw_sel_overlay(self, area, cr, w, h, _):
        cr.set_operator(1)
        for s in self._splatters:
            if s.alive:
                s.draw(cr)

    def _draw_idle(self, area, cr, w, h, _):
        if self._idle_phase <= 0:
            return
        draw_idle_overlay(cr, w, h, self._idle_phase)

    # ── Timers ─────────────────────────────────────────────────────────────────
    def _animate(self):
        self._chrome_da.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _check_idle(self):
        elapsed = time.monotonic() - self._last_input
        if elapsed >= IDLE_SECS and self._idle_phase < 1.0:
            self._idle_phase = min(1.0, self._idle_phase + 0.10)
            self._idle_da.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _decay_splatters(self):
        self._splatters = [s for s in self._splatters if s.alive]
        self._sel_da.queue_draw()
        return GLib.SOURCE_CONTINUE

    # ── Input ──────────────────────────────────────────────────────────────────
    def _reset_idle(self):
        self._last_input = time.monotonic()
        if self._idle_phase > 0:
            self._idle_phase = 0.0
            self._idle_da.queue_draw()

    def _on_key(self, ctrl, keyval, keycode, state):
        self._reset_idle()
        return False

    def _on_win_press(self, gesture, n, x, y):
        self._reset_idle()
        self._btn_pressed = True
        self._sel_color_idx = (self._sel_color_idx + 1) % len(PALETTE)

    def _on_win_release(self, gesture, n, x, y):
        self._btn_pressed = False

    def _on_motion(self, ctrl, x, y):
        prev = self._hovering_can
        self._hovering_can = None
        for key, can in [("close", CAN_CLOSE), ("min", CAN_MIN), ("max", CAN_MAX)]:
            if abs(x - can["cx"]) < 18 and abs(y - can["cy"]) < 28:
                self._hovering_can = key
                break
        if self._hovering_can != prev:
            self._chrome_da.queue_draw()

        # Spray selection splatters when dragging inside terminal area
        if self._btn_pressed:
            ix = BORDER_SIDE; iy = BORDER_TOP
            iw = (self.win.get_width() or WIN_W) - BORDER_SIDE * 2
            ih = (self.win.get_height() or WIN_H) - BORDER_TOP - BORDER_BOTTOM
            if ix < x < ix + iw and iy < y < iy + ih:
                color = PALETTE[self._sel_color_idx]
                self._splatters.append(SelSplatter(x, y, color))
                if random.random() < 0.25:
                    self._splatters.append(
                        SelSplatter(x + random.gauss(0, 12),
                                    y + random.gauss(0, 12),
                                    PALETTE[(self._sel_color_idx + 1) % len(PALETTE)]))
                self._sel_da.queue_draw()

    def _on_click_pressed(self, gesture, n, x, y):
        self._reset_idle()
        for key, can in [("close", CAN_CLOSE), ("min", CAN_MIN), ("max", CAN_MAX)]:
            if abs(x - can["cx"]) < 18 and abs(y - can["cy"]) < 28:
                if key == "close":
                    self.quit()
                elif key == "min":
                    self.win.minimize()
                elif key == "max":
                    if self.win.is_maximized():
                        self.win.unmaximize()
                    else:
                        self.win.maximize()
                return
        if y < BORDER_TOP:
            self.win.begin_move_drag(1, int(x), int(y), Gdk.CURRENT_TIME)

    def _on_click_released(self, gesture, n, x, y):
        pass


if __name__ == "__main__":
    try:
        NyxusTerminal().run(None)
    except Exception:
        log = "/tmp/nyxus-terminal.log"
        with open(log, "w") as f:
            traceback.print_exc(file=f)
        print(f"NYXUS Terminal crashed — see {log}")
        sys.exit(1)
