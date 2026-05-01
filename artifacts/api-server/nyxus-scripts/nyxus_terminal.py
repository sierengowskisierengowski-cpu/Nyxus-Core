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
BORDER_TOP     = 40   # minimal strip for spray-can buttons only
BORDER_BOTTOM  = 0
BORDER_SIDE    = 0
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

# Spray-can button colors + fixed offsets from RIGHT edge + cy
CAN_SPECS = [
    ("close", 44,  32, (0.95, 0.15, 0.15)),
    ("min",   96,  32, (1.00, 0.82, 0.00)),
    ("max",   148, 32, (0.16, 0.85, 0.16)),
]

def _can_positions(w):
    """Return [(key, cx, cy, color), ...] computed from actual window width."""
    return [(key, w - off, cy, col) for key, off, cy, col in CAN_SPECS]

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


def _draw_nyxus_piece(cr, cx, cy, size, rng):
    """Graffiti piece: spray cans above + chunky NYXUS, thick white outline + drips.
    Drawn at full opacity — caller controls the push_group alpha."""
    import cairo as _cairo
    word = "NYXUS"
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(size)
    ext = cr.text_extents(word)
    tx = cx - ext.width / 2 - ext.x_bearing
    ty = cy - ext.height / 2 - ext.y_bearing

    # ── Spray cans above the text ─────────────────────────────────────────
    can_cols = [C_PINK, C_BLUE, C_GREEN, C_YELLOW, C_ORANGE]
    n_cans = 5
    can_y_base = ty - size * 0.52
    for i in range(n_cans):
        cx_can = tx + ext.width * (i + 0.5) / n_cans
        angle = rng.uniform(-0.30, 0.30)
        cr.save()
        cr.translate(cx_can, can_y_base + rng.uniform(-8, 8))
        cr.rotate(angle)
        _draw_spray_can(cr, 0, 0, can_cols[i % len(can_cols)])
        cr.restore()

    # ── Scattered spray dots around the word ──────────────────────────────
    for _ in range(14):
        px = tx + rng.uniform(-size * 0.25, ext.width + size * 0.25)
        py = ty + rng.uniform(-size * 0.35, ext.height + size * 0.35)
        spray_dots(cr, px, py, rng.choice(PALETTE),
                   n=14, spread=18, alpha_max=0.32, rng=rng)

    # ── Thick WHITE outer outline — the graffiti bubble effect ───────────
    cr.set_source_rgba(1, 1, 1, 0.97)
    cr.set_line_width(24)
    cr.set_line_join(_cairo.LineJoin.ROUND)
    cr.move_to(tx, ty)
    cr.text_path(word)
    cr.stroke()

    # ── Thin dark inner outline ────────────────────────────────────────────
    cr.set_source_rgba(0.04, 0.01, 0.08, 0.92)
    cr.set_line_width(6)
    cr.set_line_join(_cairo.LineJoin.ROUND)
    cr.move_to(tx, ty)
    cr.text_path(word)
    cr.stroke()

    # ── Rainbow neon gradient fill (left→right, all 5 colors) ─────────────
    pat = _cairo.LinearGradient(tx, 0, tx + ext.width, 0)
    pat.add_color_stop_rgba(0.00, *C_PINK,   0.98)
    pat.add_color_stop_rgba(0.25, *C_PURPLE, 0.98)
    pat.add_color_stop_rgba(0.50, *C_BLUE,   0.98)
    pat.add_color_stop_rgba(0.75, *C_GREEN,  0.98)
    pat.add_color_stop_rgba(1.00, *C_YELLOW, 0.98)
    cr.set_source(pat)
    cr.move_to(tx, ty)
    cr.text_path(word)
    cr.fill()

    # ── White inner shine stroke ───────────────────────────────────────────
    cr.set_source_rgba(1, 1, 1, 0.28)
    cr.set_line_width(2.0)
    cr.move_to(tx + 4, ty + 4)
    cr.text_path(word)
    cr.stroke()

    # ── Paint drips from bottom of letters ────────────────────────────────
    drip_y = ty + ext.height * 0.88
    drip_cols = [C_PINK, C_BLUE, C_GREEN, C_PURPLE, C_ORANGE, C_YELLOW]
    for i in range(7):
        dx = tx + ext.width * rng.uniform(0.04, 0.96)
        _draw_drip(cr, dx, drip_y, drip_cols[i % len(drip_cols)],
                   rng.uniform(size * 0.22, size * 0.50), rng)


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
    """Terminal interior: dark base only. NYXUS piece lives on its own overlay layer."""
    # Base dark fill
    cr.set_source_rgb(*C_DARK)
    cr.rectangle(x, y, w, h)
    cr.fill()

    # Barely-there notebook rules
    cr.set_line_width(0.25)
    for ry in range(int(y) + 24, int(y + h), 24):
        cr.set_source_rgba(1, 1, 1, 0.018)
        cr.move_to(x, ry); cr.line_to(x + w, ry); cr.stroke()


# ── Spray-painted brick wall ──────────────────────────────────────────────────

def draw_spray_brick_wall(cr, x, y, w, h, seed=0):
    """White brick wall — light mortar, near-white bricks, like the reference images."""
    rng = _rng(seed + int(x * 0.1) + int(y * 0.3))
    MORTAR = 4
    BH = 22

    # ── Step 1: light grey mortar background ────────────────────────────────
    cr.set_source_rgb(0.68, 0.66, 0.70)
    cr.rectangle(x, y, w, h); cr.fill()

    # ── Step 2: near-white bricks ────────────────────────────────────────────
    row = 0; yy = y
    while yy < y + h + BH:
        offset = 36 if (row % 2) else 0
        xx = x - offset
        while xx < x + w + 80:
            bw = 68 + rng.randint(-10, 12)
            bx2_val = max(x, xx + MORTAR // 2)
            bx3_val = min(x + w, xx + bw - MORTAR // 2)
            bw_draw = bx3_val - bx2_val
            by_val = yy + MORTAR // 2
            bh_draw = BH - MORTAR
            if bw_draw > 4:
                by_clip = max(by_val, y + MORTAR // 2)
                bh_clip = min(by_val + bh_draw, y + h - MORTAR // 2) - by_clip
                if bh_clip > 0:
                    # Near-white brick face with slight warm variation
                    wv = rng.uniform(0.90, 0.98)
                    cr.set_source_rgb(wv, wv * 0.985, wv * 0.975)
                    cr.rectangle(bx2_val, by_clip, bw_draw, bh_clip); cr.fill()
                    # Very subtle shadow on bottom/right edge
                    cr.set_source_rgba(0, 0, 0, 0.06)
                    cr.rectangle(bx2_val, by_clip + bh_clip - 2, bw_draw, 2); cr.fill()
            xx += bw
        yy += BH; row += 1


# ── Graffiti frame — spray-painted bricks + tags + drips ──────────────────────

def draw_graffiti_frame(cr, w, h, hovering_can=None):
    """Spray-painted brick frame — neon bricks + graffiti tags + drips."""
    import cairo as _cairo
    rng = _rng(77)

    # Draw spray-painted bricks for all border strips
    draw_spray_brick_wall(cr, 0, 0, w, BORDER_TOP, seed=1)
    draw_spray_brick_wall(cr, 0, h - BORDER_BOTTOM, w, BORDER_BOTTOM, seed=2)
    draw_spray_brick_wall(cr, 0, BORDER_TOP, BORDER_SIDE,
                          h - BORDER_TOP - BORDER_BOTTOM, seed=3)
    draw_spray_brick_wall(cr, w - BORDER_SIDE, BORDER_TOP, BORDER_SIDE,
                          h - BORDER_TOP - BORDER_BOTTOM, seed=4)
    # Corners
    draw_spray_brick_wall(cr, 0, 0, BORDER_SIDE, BORDER_TOP, seed=5)
    draw_spray_brick_wall(cr, w - BORDER_SIDE, 0, BORDER_SIDE, BORDER_TOP, seed=6)
    draw_spray_brick_wall(cr, 0, h - BORDER_BOTTOM, BORDER_SIDE, BORDER_BOTTOM, seed=7)
    draw_spray_brick_wall(cr, w - BORDER_SIDE, h - BORDER_BOTTOM,
                          BORDER_SIDE, BORDER_BOTTOM, seed=8)

    # ── Light spray scatter on bricks — small dots only, don't cover brick color ──
    for fx, fy, col in [
        (0.08, 0.5, C_GREEN), (0.35, 0.4, C_BLUE), (0.68, 0.6, C_PINK),
        (BORDER_SIDE / w, 0.5, C_YELLOW), (1 - BORDER_SIDE / w, 0.5, C_ORANGE),
    ]:
        spray_dots(cr, w * fx, BORDER_TOP * fy, col,
                   n=18, spread=10, alpha_max=0.28, rng=rng)

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

    # ── Spray can buttons — positions computed from actual w ──
    label_map = {"close": "✕", "min": "▂", "max": "▣"}
    for key, cx, cy, color in _can_positions(w):
        _draw_spray_can(cr, cx, cy, color, hovered=(hovering_can == key))
        cr.select_font_face("Caveat", 0, 0)
        cr.set_font_size(11)
        lbl = label_map[key]
        ext2 = cr.text_extents(lbl)
        cr.set_source_rgba(1, 1, 1, 0.42)
        cr.move_to(cx - ext2.width / 2 - ext2.x_bearing, BORDER_TOP - 6)
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


# ── Paint blob (HARLEY-style large ink throw on wall) ─────────────────────────

def draw_paint_blob(cr, cx, cy, col, size, rng):
    """Organic ink blob + mist + drips — like paint thrown at a white wall."""
    r, g, b = col
    n_pts = rng.randint(9, 14)
    step = (math.pi * 2) / n_pts
    angles = sorted(i * step + rng.uniform(-step * 0.3, step * 0.3)
                    for i in range(n_pts))
    radii  = [size * rng.uniform(0.45, 1.38) for _ in range(n_pts)]

    # Main blob shape (bezier)
    cr.set_source_rgba(r, g, b, rng.uniform(0.68, 0.86))
    fx = cx + math.cos(angles[0]) * radii[0]
    fy = cy + math.sin(angles[0]) * radii[0] * 0.52
    cr.move_to(fx, fy)
    for i in range(1, n_pts + 1):
        ai = angles[i % n_pts]; ri = radii[i % n_pts]
        ap = angles[(i - 1) % n_pts]; rp = radii[(i - 1) % n_pts]
        am = (ap + ai) / 2
        rm = (rp + ri) / 2 * rng.uniform(0.72, 1.28)
        cr.curve_to(cx + math.cos(am) * rm,       cy + math.sin(am) * rm * 0.52,
                    cx + math.cos(am) * rm,       cy + math.sin(am) * rm * 0.52,
                    cx + math.cos(ai) * ri,        cy + math.sin(ai) * ri * 0.52)
    cr.close_path(); cr.fill()

    # Outer mist ring
    spray_dots(cr, cx, cy, col, n=90,  spread=int(size * 1.35), alpha_max=0.30, rng=rng)
    spray_dots(cr, cx, cy, col, n=55,  spread=int(size * 0.65), alpha_max=0.60, rng=rng)

    # Fine splatter dots scattered outward
    for _ in range(rng.randint(6, 12)):
        ang = rng.uniform(0, math.pi * 2)
        dist = rng.uniform(size * 0.6, size * 1.8)
        sx = cx + math.cos(ang) * dist
        sy = cy + math.sin(ang) * dist * 0.55
        spray_dots(cr, sx, sy, col, n=14, spread=int(size * 0.15),
                   alpha_max=0.55, rng=rng)

    # Paint drips
    for _ in range(rng.randint(2, 4)):
        dx = cx + rng.uniform(-size * 0.55, size * 0.55)
        _draw_drip(cr, dx, cy + size * rng.uniform(0.35, 0.70), col,
                   rng.uniform(size * 0.4, size * 0.95), rng)


# ── Idle overlay ──────────────────────────────────────────────────────────────

def draw_idle_overlay(cr, w, h, phase):
    alpha = min(phase, 1.0)
    cr.set_source_rgba(0.03, 0.02, 0.08, alpha * 0.90)
    cr.rectangle(0, 0, w, h); cr.fill()

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
        self.alpha = 0.92
        self.size = random.uniform(14, 32)
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
        r, g, b = self.color
        rng = random.Random()
        # Solid filled ellipse base — this is the "paint hit"
        cr.set_source_rgba(r, g, b, op * 0.72)
        cr.save()
        cr.translate(self.x, self.y)
        cr.scale(self.size * 0.80, self.size * 0.55)
        cr.arc(0, 0, 1, 0, math.pi * 2)
        cr.restore()
        cr.fill()
        # Dense spray cloud on top
        spray_dots(cr, self.x, self.y, self.color,
                   n=55, spread=self.size, alpha_max=op * 0.90, rng=rng)
        # Bright center hot-spot
        cr.set_source_rgba(r, g, b, op * 0.55)
        cr.arc(self.x, self.y, self.size * 0.22, 0, math.pi * 2)
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

        # Layer 1.5 — NYXUS graffiti piece (above VTE, invisible to events)
        self._nyxus_da = Gtk.DrawingArea()
        self._nyxus_da.set_draw_func(self._draw_nyxus_overlay, None)
        self._nyxus_da.set_can_focus(False)
        self._nyxus_da.set_can_target(False)   # mouse/keyboard fall through to VTE
        self._nyxus_da.set_halign(Gtk.Align.FILL)
        self._nyxus_da.set_valign(Gtk.Align.FILL)
        overlay.add_overlay(self._nyxus_da)
        overlay.set_clip_overlay(self._nyxus_da, False)

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
        win_click.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
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

        # Background — transparent enough for brick wall texture to show through
        bg = Gdk.RGBA(); bg.red=0.04; bg.green=0.02; bg.blue=0.10; bg.alpha=0.65
        fg = Gdk.RGBA(); fg.red=0.92; fg.green=0.88; fg.blue=0.98; fg.alpha=1.0
        vte.set_color_background(bg)
        vte.set_color_foreground(fg)

        # Selection — solid neon orange so selected text is actually visible
        hl    = Gdk.RGBA(); hl.red=1.0; hl.green=0.34; hl.blue=0.0; hl.alpha=1.0
        hl_fg = Gdk.RGBA(); hl_fg.red=0.04; hl_fg.green=0.02; hl_fg.blue=0.10; hl_fg.alpha=1.0
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

        # ── Right-click context menu (Copy / Paste / Select All) ──
        rc = Gtk.GestureClick()
        rc.set_button(3)  # right mouse button
        rc.connect("pressed", self._on_vte_right_click)
        vte.add_controller(rc)

        # Action group backing the menu items declared in _on_vte_right_click.
        actions = Gio.SimpleActionGroup()

        def _act(name, fn):
            a = Gio.SimpleAction.new(name, None)
            a.connect("activate", lambda *_: fn())
            actions.add_action(a)

        def _do_copy():
            try: vte.copy_clipboard_format(Vte.Format.TEXT)
            except Exception:
                try: vte.copy_clipboard()
                except Exception: pass
        def _do_paste():
            try: vte.paste_clipboard()
            except Exception: pass
        def _do_select_all():
            try: vte.select_all()
            except Exception: pass

        _act("copy",      _do_copy)
        _act("paste",     _do_paste)
        _act("selectall", _do_select_all)
        # Insert under the "term" prefix so menu items "term.copy" etc. resolve.
        vte.insert_action_group("term", actions)

    # ── Draw callbacks ─────────────────────────────────────────────────────────
    def _draw_chrome_bg(self, area, cr, w, h, _):
        import cairo as _cairo
        self._anim_t += 0.015

        # 1. Solid dark base
        cr.set_source_rgb(*C_DARK)
        cr.rectangle(0, 0, w, h); cr.fill()

        # 2. White brick wall texture at 52% opacity — clearly visible bricks
        cr.push_group()
        draw_spray_brick_wall(cr, 0, 0, w, h, seed=42)
        cr.pop_group_to_source()
        cr.paint_with_alpha(0.52)

        # 3. Subtle dark tint on the top strip so buttons are readable
        cr.set_source_rgba(0.03, 0.01, 0.08, 0.72)
        cr.rectangle(0, 0, w, BORDER_TOP); cr.fill()

        # 4. Neon rainbow separator at bottom of top strip
        pat = _cairo.LinearGradient(0, BORDER_TOP - 2, w, BORDER_TOP - 2)
        for i, col in enumerate(PALETTE):
            pat.add_color_stop_rgb(i / max(len(PALETTE) - 1, 1), *col)
        cr.set_source(pat)
        cr.rectangle(0, BORDER_TOP - 2, w, 2); cr.fill()

        # 5. "NYXUS Terminal" title in top strip
        cr.select_font_face("Caveat", 0, 1)
        cr.set_font_size(20)
        title = "NYXUS Terminal"
        ty = BORDER_TOP - 10
        cr.set_source_rgba(1, 0, 1, 0.30)
        cr.set_line_width(3)
        cr.move_to(16, ty); cr.text_path(title); cr.stroke()
        cr.set_source_rgba(1, 1, 1, 0.90)
        cr.move_to(16, ty); cr.show_text(title)


        if not HAS_VTE:
            draw_no_vte(cr, 0, BORDER_TOP, w, h - BORDER_TOP)

    def _draw_nyxus_overlay(self, area, cr, w, h, _):
        """NYXUS on white bricks — HARLEY-style ink blob splatters + graffiti piece."""
        inner_x = BORDER_SIDE
        inner_y = BORDER_TOP
        inner_w = w - BORDER_SIDE * 2
        inner_h = h - BORDER_TOP - BORDER_BOTTOM
        if inner_w <= 0 or inner_h <= 0:
            return

        rng  = _rng(42)
        rng2 = _rng(77)
        cx   = inner_x + inner_w * 0.5
        cy   = inner_y + inner_h * 0.46
        # Half the old size (old was min(inner_w*0.32, 200))
        piece_size = min(inner_w * 0.16, 100)
        blob_sz    = piece_size * 1.10   # blob radius relative to text size

        cr.push_group()

        # ── Large HARLEY-style ink blobs BEHIND the text ───────────────────
        # Centre mega-blob (like the main splat behind HARLEY)
        draw_paint_blob(cr, cx, cy, C_PURPLE, blob_sz * 1.6, rng)

        # Offset blobs left + right for asymmetry
        draw_paint_blob(cr, cx - piece_size * 0.9, cy + piece_size * 0.15,
                        C_PINK,  blob_sz * 1.1, rng2)
        draw_paint_blob(cr, cx + piece_size * 0.85, cy - piece_size * 0.10,
                        C_BLUE,  blob_sz * 1.0, rng2)

        # Smaller accent blobs scattered around
        for i, col in enumerate([C_GREEN, C_ORANGE, C_YELLOW]):
            ang = math.radians(i * 120 + 40)
            bx  = cx + math.cos(ang) * piece_size * 1.6
            by  = cy + math.sin(ang) * piece_size * 0.8
            draw_paint_blob(cr, bx, by, col, blob_sz * 0.55, rng)

        # ── NYXUS graffiti piece on top ────────────────────────────────────
        _draw_nyxus_piece(cr, cx, cy, piece_size, rng)

        cr.pop_group_to_source()
        cr.paint_with_alpha(0.45)

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

        # ── Copy / paste keyboard shortcuts ──
        # VTE doesn't bind these by default; the host app must wire them up.
        # Standard terminal bindings:
        #   Ctrl+Shift+C / Ctrl+Insert  → copy selection to clipboard
        #   Ctrl+Shift+V / Shift+Insert → paste clipboard at cursor
        #   Ctrl+Shift+A                → select all
        ctrl_mask  = bool(state & Gdk.ModifierType.CONTROL_MASK)
        shift_mask = bool(state & Gdk.ModifierType.SHIFT_MASK)

        if self._vte is not None:
            # Copy
            if (ctrl_mask and shift_mask and keyval in (
                    Gdk.KEY_c, Gdk.KEY_C)) or \
               (ctrl_mask and keyval == Gdk.KEY_Insert):
                try:
                    self._vte.copy_clipboard_format(Vte.Format.TEXT)
                except Exception:
                    try: self._vte.copy_clipboard()
                    except Exception: pass
                return True

            # Paste
            if (ctrl_mask and shift_mask and keyval in (
                    Gdk.KEY_v, Gdk.KEY_V)) or \
               (shift_mask and keyval == Gdk.KEY_Insert):
                try:
                    self._vte.paste_clipboard()
                except Exception: pass
                return True

            # Select all
            if ctrl_mask and shift_mask and keyval in (Gdk.KEY_a, Gdk.KEY_A):
                try:
                    self._vte.select_all()
                except Exception: pass
                return True

        return False

    def _on_vte_right_click(self, gesture, n, x, y):
        """Right-click anywhere in the terminal opens a copy/paste menu."""
        if self._vte is None:
            return
        menu = Gio.Menu()
        menu.append("Copy",  "term.copy")
        menu.append("Paste", "term.paste")
        menu.append("Select All", "term.selectall")

        popover = Gtk.PopoverMenu.new_from_model(menu)
        popover.set_parent(self._vte)
        popover.set_has_arrow(False)
        rect = Gdk.Rectangle()
        rect.x = int(x); rect.y = int(y); rect.width = 1; rect.height = 1
        popover.set_pointing_to(rect)
        popover.popup()

    def _on_win_press(self, gesture, n, x, y):
        self._reset_idle()
        self._btn_pressed = True
        self._sel_color_idx = (self._sel_color_idx + 1) % len(PALETTE)

    def _on_win_release(self, gesture, n, x, y):
        self._btn_pressed = False

    def _on_motion(self, ctrl, x, y):
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
