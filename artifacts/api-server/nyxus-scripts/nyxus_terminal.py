#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Terminal — Brick Wall · Graffiti Art · Spray Can Controls         ║
# ║  Idle Blur · Graffiti Selection · Caveat font                            ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-TERM-2026-SIERENGOWSKI-LOCKED          ║
# ╚══════════════════════════════════════════════════════════════════════════╝
import gi, sys, os, math, random, time, traceback
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Pango, Gio  # lock GTK4 first

try:
    try:
        gi.require_version("Vte", "2.91")
    except ValueError:
        pass  # already required
    from gi.repository import Vte
    HAS_VTE = True
except Exception as _vte_err:
    HAS_VTE = False
    print(f"[nyxus-terminal] VTE import failed: {_vte_err}")

# ── Dimensions ────────────────────────────────────────────────────────────────
WIN_W, WIN_H   = 1100, 680
BORDER_TOP     = 68   # title bar + top brick
BORDER_BOTTOM  = 38
BORDER_SIDE    = 34
IDLE_SECS      = 90   # seconds before blur kicks in

# ── NYXUS palette (r,g,b floats) ─────────────────────────────────────────────
C_PINK   = (1.00, 0.00, 1.00)
C_PURPLE = (0.80, 0.00, 1.00)
C_BLUE   = (0.00, 0.53, 1.00)
C_GREEN  = (0.22, 1.00, 0.08)
C_YELLOW = (1.00, 1.00, 0.00)
C_ORANGE = (1.00, 0.33, 0.00)
PALETTE  = [C_PINK, C_PURPLE, C_BLUE, C_GREEN, C_YELLOW, C_ORANGE]
C_DARK   = (0.031, 0.031, 0.055)   # #08080e

# Spray-can button areas (cx, cy, radius, color, action)
CAN_CLOSE = {"cx": WIN_W - 44,  "cy": 28, "color": (0.95, 0.15, 0.15)}
CAN_MIN   = {"cx": WIN_W - 92,  "cy": 28, "color": (1.00, 0.82, 0.00)}
CAN_MAX   = {"cx": WIN_W - 140, "cy": 28, "color": (0.16, 0.85, 0.16)}


# ── CSS ───────────────────────────────────────────────────────────────────────
CSS = b"""
window { background-color: #08080e; }
vte-terminal {
    background-color: transparent;
    color: rgba(232,224,245,0.92);
    font-family: 'Caveat', 'Patrick Hand', 'DejaVu Sans Mono', monospace;
}
"""


# ── Cairo drawing helpers ─────────────────────────────────────────────────────

def _rng(seed):
    return random.Random(int(seed) % 999983)


def draw_brick_wall(cr, x, y, w, h, seed=0):
    """Realistic staggered brick wall using Cairo."""
    rng = _rng(seed + x + y)
    MORTAR = 4
    BH = 22  # brick height including mortar

    # Mortar (background) — dark grey
    cr.set_source_rgb(0.20, 0.18, 0.16)
    cr.rectangle(x, y, w, h)
    cr.fill()

    row = 0
    yy = y
    while yy < y + h + BH:
        offset = 36 if (row % 2) else 0
        xx = x - offset
        while xx < x + w + 80:
            bw = 68 + rng.randint(-10, 12)
            # Clip to wall bounds
            bx = max(x, xx + MORTAR // 2)
            bx2 = min(x + w, xx + bw - MORTAR // 2)
            bw_draw = bx2 - bx
            by = yy + MORTAR // 2
            bh_draw = BH - MORTAR

            if bw_draw > 4 and by + bh_draw > y and by < y + h:
                by_clip = max(by, y + MORTAR // 2)
                bh_clip = min(by + bh_draw, y + h - MORTAR // 2) - by_clip
                if bh_clip > 0:
                    # Base brick color (warm reds/browns)
                    rv = rng.uniform(0.52, 0.72)
                    gv = rng.uniform(0.16, 0.26)
                    bv = rng.uniform(0.06, 0.14)
                    cr.set_source_rgb(rv, gv, bv)
                    cr.rectangle(bx, by_clip, bw_draw, bh_clip)
                    cr.fill()

                    # Highlight strip — top of brick
                    if by_clip == by:
                        cr.set_source_rgba(1, 0.85, 0.7, 0.18)
                        cr.rectangle(bx, by_clip, bw_draw, min(3, bh_clip))
                        cr.fill()
                        # Left highlight
                        cr.set_source_rgba(1, 0.85, 0.7, 0.10)
                        cr.rectangle(bx, by_clip, min(4, bw_draw), bh_clip)
                        cr.fill()

                    # Shadow strip — bottom of brick
                    sh_y = by_clip + bh_clip - 3
                    if sh_y > by_clip and by_clip + bh_clip >= by + bh_draw - 1:
                        cr.set_source_rgba(0, 0, 0, 0.22)
                        cr.rectangle(bx, sh_y, bw_draw, 3)
                        cr.fill()

                    # Surface pores / texture
                    for _ in range(rng.randint(0, 4)):
                        tx = bx + rng.uniform(4, bw_draw - 4)
                        ty = by_clip + rng.uniform(2, bh_clip - 2)
                        cr.set_source_rgba(0, 0, 0, rng.uniform(0.05, 0.14))
                        cr.arc(tx, ty, rng.uniform(0.8, 2.5), 0, math.pi * 2)
                        cr.fill()

            xx += bw
        yy += BH
        row += 1


def spray_dots(cr, cx, cy, color, n=60, spread=18, alpha_max=0.55):
    """Scatter spray-paint dots around a point."""
    r, g, b = color
    rng = random.Random()
    for _ in range(n):
        dx = rng.gauss(0, spread * 0.5)
        dy = rng.gauss(0, spread * 0.5)
        dist = math.sqrt(dx * dx + dy * dy) / spread
        alpha = alpha_max * max(0, 1 - dist) * rng.uniform(0.3, 1.0)
        size = rng.uniform(0.8, 3.5) * max(0, 1 - dist * 0.5)
        cr.set_source_rgba(r, g, b, alpha)
        cr.arc(cx + dx, cy + dy, size, 0, math.pi * 2)
        cr.fill()


def draw_spray_can(cr, cx, cy, color, hovered=False):
    """Draw a spray paint can button."""
    r, g, b = color
    can_w, can_h = 22, 38
    bx, by = cx - can_w / 2, cy - can_h / 2 + 5

    # Drop shadow
    cr.set_source_rgba(0, 0, 0, 0.50)
    cr.rectangle(bx + 3, by + 4, can_w, can_h)
    cr.fill()

    # Can body — darker shade at sides for cylinder illusion
    cr.set_source_rgb(r * 0.70, g * 0.70, b * 0.70)
    cr.rectangle(bx, by, can_w, can_h)
    cr.fill()

    # Main color band (center)
    cr.set_source_rgb(r, g, b)
    cr.rectangle(bx + 3, by + 6, can_w - 6, can_h - 12)
    cr.fill()

    # Left highlight (cylinder edge glow)
    cr.set_source_rgba(1, 1, 1, 0.28)
    cr.rectangle(bx + 3, by + 6, 4, can_h - 12)
    cr.fill()

    # Nozzle cap (silver)
    cap_w, cap_h = 16, 7
    cr.set_source_rgb(0.72, 0.72, 0.75)
    cr.rectangle(cx - cap_w / 2, by - cap_h, cap_w, cap_h)
    cr.fill()
    cr.set_source_rgba(1, 1, 1, 0.22)
    cr.rectangle(cx - cap_w / 2, by - cap_h, cap_w, 2)
    cr.fill()

    # Nozzle tip
    cr.set_source_rgb(0.50, 0.52, 0.55)
    cr.rectangle(cx + cap_w / 2 - 4, by - cap_h - 6, 10, 5)
    cr.fill()

    # Label band (tiny white strip)
    cr.set_source_rgba(1, 1, 1, 0.18)
    cr.rectangle(bx + 3, by + can_h - 16, can_w - 6, 6)
    cr.fill()

    # Hover: spray cloud from nozzle tip
    if hovered:
        spray_dots(cr, cx + cap_w / 2 + 16, by - cap_h - 3,
                   color, n=40, spread=14, alpha_max=0.50)


def draw_graffiti_bg(cr, x, y, w, h, t=0.0):
    """Paint-splatter graffiti wall — icon-generator style, full bleed."""
    rng = _rng(42)

    # ── Base dark wall ──
    cr.set_source_rgb(*C_DARK)
    cr.rectangle(x, y, w, h)
    cr.fill()

    # ── Faint real brick outline in background (very subtle, like a real wall) ──
    BH2, M2 = 28, 3
    row2 = 0; yy2 = y
    while yy2 < y + h:
        off2 = 44 if row2 % 2 else 0
        xx2 = x - off2
        while xx2 < x + w + 88:
            bw2 = 88 + rng.randint(-12, 12)
            lx = max(x, xx2 + M2); rx = min(x + w, xx2 + bw2 - M2)
            if rx - lx > 6:
                cr.set_line_width(0.6)
                cr.set_source_rgba(0.28, 0.18, 0.10, 0.12)
                cr.rectangle(lx, yy2 + M2, rx - lx, BH2 - M2 * 2)
                cr.stroke()
            xx2 += bw2
        yy2 += BH2; row2 += 1

    # ── MASSIVE background paint blobs (like icon generator — 20 large blobs) ──
    blob_data = [
        (0.08, 0.15, C_GREEN,  52), (0.92, 0.12, C_ORANGE, 44),
        (0.50, 0.08, C_BLUE,   38), (0.22, 0.80, C_YELLOW, 48),
        (0.78, 0.75, C_PURPLE, 55), (0.15, 0.48, C_PINK,   35),
        (0.85, 0.50, C_BLUE,   42), (0.40, 0.30, C_ORANGE, 30),
        (0.62, 0.65, C_GREEN,  36), (0.30, 0.60, C_PURPLE, 28),
        (0.70, 0.25, C_PINK,   32), (0.55, 0.88, C_YELLOW, 40),
        (0.05, 0.72, C_BLUE,   24), (0.95, 0.40, C_GREEN,  26),
        (0.48, 0.52, C_ORANGE, 20), (0.20, 0.20, C_PURPLE, 18),
        (0.80, 0.82, C_PINK,   22), (0.35, 0.42, C_YELLOW, 16),
        (0.65, 0.38, C_BLUE,   14), (0.12, 0.90, C_ORANGE, 18),
    ]
    for bfx, bfy, bcol, brad in blob_data:
        bpx = x + w * bfx; bpy = y + h * bfy
        cr.set_source_rgba(*bcol, rng.uniform(0.12, 0.30))
        cr.arc(bpx, bpy, brad, 0, math.pi * 2)
        cr.fill()
        spray_dots(cr, bpx, bpy, bcol, n=90, spread=int(brad * 1.8), alpha_max=0.32)

    # ── Splatter streaks (horizontal throws) ──
    for _ in range(28):
        sx = rng.uniform(x, x + w); sy = rng.uniform(y, y + h)
        ex = sx + rng.uniform(-120, 120); ey = sy + rng.uniform(-18, 18)
        col = rng.choice(PALETTE)
        cr.set_source_rgba(*col, rng.uniform(0.14, 0.42))
        cr.set_line_width(rng.uniform(0.7, 2.8))
        cr.move_to(sx, sy); cr.line_to(ex, ey); cr.stroke()
        # Splatter dots at end of streak
        spray_dots(cr, ex, ey, col, n=12, spread=8, alpha_max=0.35)

    # ── Dense small dot field (icon-generator small dots — 80 dots) ──
    for _ in range(80):
        bpx = rng.uniform(x + 4, x + w - 4); bpy = rng.uniform(y + 4, y + h - 4)
        brad = rng.uniform(1, 4.5)
        col = rng.choice(PALETTE)
        cr.set_source_rgba(*col, rng.uniform(0.25, 0.65))
        cr.arc(bpx, bpy, brad, 0, math.pi * 2); cr.fill()

    # ── Large NYXUS graffiti tag (main piece) ──
    _draw_graffiti_word(cr, x + w * 0.5, y + h * 0.46, "NYXUS",
                        C_PINK, C_PURPLE, 92, rng)

    # ── TERMINAL crew tag ──
    _draw_graffiti_word(cr, x + w * 0.5, y + h * 0.76, "TERMINAL",
                        C_BLUE, C_GREEN, 40, rng)

    # ── Paint drips from the top brick edge ──
    drip_data = [
        (x + w * 0.13, y,       C_PINK,   h * 0.38),
        (x + w * 0.32, y,       C_GREEN,  h * 0.26),
        (x + w * 0.58, y,       C_ORANGE, h * 0.34),
        (x + w * 0.77, y,       C_BLUE,   h * 0.24),
        (x + w * 0.90, y,       C_YELLOW, h * 0.20),
    ]
    for dx2, dy2, dcol, dlen in drip_data:
        _draw_drip(cr, dx2, dy2, dcol, dlen, rng)

    # ── Graffiti stars / crowd tags ──
    star_pts = [
        (x + w * 0.04, y + h * 0.55, C_YELLOW, 18),
        (x + w * 0.96, y + h * 0.48, C_PINK,   14),
        (x + w * 0.46, y + h * 0.93, C_GREEN,  12),
        (x + w * 0.88, y + h * 0.88, C_ORANGE, 10),
        (x + w * 0.06, y + h * 0.25, C_BLUE,   10),
    ]
    for sx2, sy2, scol, sr in star_pts:
        _draw_star(cr, sx2, sy2, scol, sr)

    # ── Subtle notebook ruled lines on top (keeps it readable) ──
    cr.set_line_width(0.35)
    for ry in range(int(y) + 26, int(y + h), 26):
        cr.set_source_rgba(1, 1, 1, 0.038)
        cr.move_to(x, ry); cr.line_to(x + w, ry); cr.stroke()


def _draw_graffiti_word(cr, cx, cy, word, color1, color2, size, rng):
    """Draw bubble-letter graffiti text centered at (cx,cy)."""
    r1, g1, b1 = color1
    r2, g2, b2 = color2

    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(size)
    ext = cr.text_extents(word)
    tx = cx - ext.width / 2 - ext.x_bearing
    ty = cy - ext.height / 2 - ext.y_bearing

    # Thick outer glow / outline passes
    for blur_r, alpha in [(14, 0.08), (9, 0.14), (5, 0.22), (3, 0.32)]:
        cr.set_source_rgba(r1, g1, b1, alpha)
        cr.set_line_width(blur_r * 2)
        cr.move_to(tx + 1, ty + 1)
        cr.text_path(word)
        cr.stroke()

    # Dark outline (thick marker edge)
    cr.set_source_rgba(0.05, 0.02, 0.08, 0.88)
    cr.set_line_width(6)
    cr.move_to(tx, ty)
    cr.text_path(word)
    cr.stroke()

    # Gradient fill — color1 top → color2 bottom
    import cairo as _cairo
    h_span = ext.height
    pat = _cairo.LinearGradient(0, ty, 0, ty + h_span)
    pat.add_color_stop_rgba(0.0, r1, g1, b1, 0.92)
    pat.add_color_stop_rgba(0.5, (r1 + r2) / 2, (g1 + g2) / 2, (b1 + b2) / 2, 0.88)
    pat.add_color_stop_rgba(1.0, r2, g2, b2, 0.92)
    cr.set_source(pat)
    cr.move_to(tx, ty)
    cr.text_path(word)
    cr.fill()

    # Inner white highlight
    cr.set_source_rgba(1, 1, 1, 0.22)
    cr.set_line_width(1.5)
    cr.move_to(tx + 2, ty + 2)
    cr.text_path(word)
    cr.stroke()

    # Spray scatter around the word
    for _ in range(6):
        px = tx + rng.uniform(0, ext.width)
        py = ty + rng.uniform(-size * 0.4, size * 0.4)
        spray_dots(cr, px, py, color1 if rng.random() < 0.5 else color2,
                   n=12, spread=12, alpha_max=0.22)


def _draw_drip(cr, x, top_y, color, length, rng):
    """Draw a paint drip."""
    r, g, b = color
    drip_w = rng.uniform(5, 10)
    # Blob at top
    cr.set_source_rgba(r, g, b, 0.65)
    cr.arc(x, top_y, drip_w * 0.8, 0, math.pi * 2)
    cr.fill()
    # Drip body
    wobble = rng.uniform(-4, 4)
    cr.set_source_rgba(r, g, b, 0.55)
    cr.move_to(x - drip_w / 2, top_y)
    cr.curve_to(x - drip_w / 2 + wobble, top_y + length * 0.4,
                x + drip_w / 2 + wobble, top_y + length * 0.6,
                x + drip_w * 0.3, top_y + length)
    cr.curve_to(x - drip_w * 0.3, top_y + length,
                x - drip_w / 2 - wobble, top_y + length * 0.6,
                x - drip_w / 2, top_y)
    cr.fill()
    # Teardrop end
    cr.set_source_rgba(r, g, b, 0.48)
    cr.arc(x + wobble * 0.3, top_y + length, drip_w * 0.45, 0, math.pi * 2)
    cr.fill()


def _draw_star(cr, cx, cy, color, radius):
    """Draw a graffiti star/asterisk."""
    r, g, b = color
    for i in range(6):
        angle = math.radians(i * 30)
        cr.set_source_rgba(r, g, b, 0.70)
        cr.set_line_width(2.5)
        cr.move_to(cx - math.cos(angle) * radius, cy - math.sin(angle) * radius)
        cr.line_to(cx + math.cos(angle) * radius, cy + math.sin(angle) * radius)
        cr.stroke()
    cr.set_source_rgba(r, g, b, 0.60)
    cr.arc(cx, cy, radius * 0.28, 0, math.pi * 2)
    cr.fill()


def _draw_border_graffiti(cr, w, h, rng):
    """Spray paint tags, drips, and gang stars directly on the brick border strips."""
    # ── Left strip: "NYX" sprayed at angle ──
    cr.save()
    lx = BORDER_SIDE / 2
    cr.translate(lx, h * 0.42)
    cr.rotate(-math.pi / 2)
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(17)
    # Glow
    cr.set_source_rgba(*C_PINK, 0.28)
    cr.set_line_width(5)
    cr.move_to(0, 0); cr.text_path("NYX"); cr.stroke()
    # Fill
    cr.set_source_rgba(*C_PINK, 0.72)
    cr.move_to(0, 0); cr.show_text("NYX")
    cr.restore()

    # ── Left strip: spray scatter around tag ──
    spray_dots(cr, BORDER_SIDE * 0.5, h * 0.42, C_PINK, n=28, spread=BORDER_SIDE // 2, alpha_max=0.28)
    spray_dots(cr, BORDER_SIDE * 0.5, h * 0.62, C_PURPLE, n=20, spread=10, alpha_max=0.22)

    # ── Left strip: a graffiti crown ──
    cx = BORDER_SIDE * 0.5; cy = h * 0.25
    cr.set_source_rgba(*C_YELLOW, 0.60)
    cr.set_line_width(1.5)
    pts = [(cx - 8, cy + 6), (cx - 8, cy - 2), (cx - 4, cy + 2),
           (cx, cy - 6),     (cx + 4, cy + 2), (cx + 8, cy - 2), (cx + 8, cy + 6)]
    cr.move_to(*pts[0])
    for px2, py2 in pts[1:]: cr.line_to(px2, py2)
    cr.close_path(); cr.stroke()
    spray_dots(cr, cx, cy, C_YELLOW, n=12, spread=8, alpha_max=0.20)

    # ── Right strip: "TERM" at angle ──
    cr.save()
    rx = w - BORDER_SIDE / 2
    cr.translate(rx, h * 0.42)
    cr.rotate(-math.pi / 2)
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(14)
    cr.set_source_rgba(*C_BLUE, 0.28)
    cr.set_line_width(5)
    cr.move_to(0, 0); cr.text_path("TERM"); cr.stroke()
    cr.set_source_rgba(*C_BLUE, 0.70)
    cr.move_to(0, 0); cr.show_text("TERM")
    cr.restore()
    spray_dots(cr, w - BORDER_SIDE * 0.5, h * 0.38, C_BLUE, n=28, spread=BORDER_SIDE // 2, alpha_max=0.25)
    spray_dots(cr, w - BORDER_SIDE * 0.5, h * 0.62, C_GREEN, n=18, spread=10, alpha_max=0.20)

    # ── Top strip: scattered tags + stars ──
    for fx, col in [(0.28, C_GREEN), (0.72, C_ORANGE)]:
        spray_dots(cr, w * fx, BORDER_TOP * 0.5, col, n=22, spread=18, alpha_max=0.30)
    _draw_star(cr, w * 0.15, BORDER_TOP * 0.5, C_YELLOW, 7)
    _draw_star(cr, w * 0.82, BORDER_TOP * 0.5, C_PINK,   6)

    # ── Bottom strip: drips falling from bottom edge ──
    for fx, col in [(0.22, C_PURPLE), (0.55, C_BLUE), (0.78, C_GREEN)]:
        spray_dots(cr, w * fx, h - BORDER_BOTTOM * 0.5, col, n=16, spread=12, alpha_max=0.28)

    # ── Big background splatters over corners + sides (more rawness) ──
    for cx2, cy2, col2, sp in [
        (BORDER_SIDE * 0.5, BORDER_TOP,            C_ORANGE, 22),
        (w - BORDER_SIDE * 0.5, BORDER_TOP,        C_GREEN,  18),
        (BORDER_SIDE * 0.5, h - BORDER_BOTTOM,     C_YELLOW, 18),
        (w - BORDER_SIDE * 0.5, h - BORDER_BOTTOM, C_PINK,   16),
    ]:
        spray_dots(cr, cx2, cy2, col2, n=30, spread=sp, alpha_max=0.30)
        cr.set_source_rgba(*col2, 0.18)
        cr.arc(cx2, cy2, sp * 0.35, 0, math.pi * 2); cr.fill()


def draw_chrome(cr, w, h, hovering_can=None, t=0.0):
    """Draw the full brick-wall window frame + spray can buttons."""
    # ── Top brick border (title bar) ──
    draw_brick_wall(cr, 0, 0, w, BORDER_TOP, seed=1)

    # ── Bottom brick ──
    draw_brick_wall(cr, 0, h - BORDER_BOTTOM, w, BORDER_BOTTOM, seed=2)

    # ── Left brick ──
    draw_brick_wall(cr, 0, BORDER_TOP, BORDER_SIDE, h - BORDER_TOP - BORDER_BOTTOM, seed=3)

    # ── Right brick ──
    draw_brick_wall(cr, w - BORDER_SIDE, BORDER_TOP, BORDER_SIDE,
                    h - BORDER_TOP - BORDER_BOTTOM, seed=4)

    # ── Inner corner patches (fill the brick corners) ──
    # Top-left
    draw_brick_wall(cr, 0, 0, BORDER_SIDE, BORDER_TOP, seed=5)
    # Top-right
    draw_brick_wall(cr, w - BORDER_SIDE, 0, BORDER_SIDE, BORDER_TOP, seed=6)
    # Bottom-left
    draw_brick_wall(cr, 0, h - BORDER_BOTTOM, BORDER_SIDE, BORDER_BOTTOM, seed=7)
    # Bottom-right
    draw_brick_wall(cr, w - BORDER_SIDE, h - BORDER_BOTTOM, BORDER_SIDE, BORDER_BOTTOM, seed=8)

    # ── Street graffiti tags sprayed ON the bricks ──
    _draw_border_graffiti(cr, w, h, _rng(77))

    # ── NYXUS title in top brick bar ──
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(20)
    title = "NYXUS Terminal"
    ext = cr.text_extents(title)
    # Pink glow shadow
    cr.set_source_rgba(1, 0, 1, 0.25)
    cr.move_to(16 + 1.5, BORDER_TOP / 2 + ext.height / 2 - ext.y_bearing - ext.height + 1)
    cr.show_text(title)
    # White text
    cr.set_source_rgba(1, 1, 1, 0.88)
    cr.move_to(16, BORDER_TOP / 2 + ext.height / 2 - ext.y_bearing - ext.height)
    cr.show_text(title)

    # ── Rainbow strip under title bar ──
    import cairo as _cairo
    rbar_y = BORDER_TOP - 3
    pat = _cairo.LinearGradient(0, rbar_y, w, rbar_y)
    for stop, col in [(0, C_PINK), (0.2, C_PURPLE), (0.4, C_BLUE),
                      (0.6, C_GREEN), (0.8, C_YELLOW), (1, C_ORANGE)]:
        pat.add_color_stop_rgb(stop, *col)
    cr.set_source(pat)
    cr.rectangle(0, rbar_y, w, 3)
    cr.fill()

    # ── Spray can buttons ──
    for can, hov_key in [(CAN_CLOSE, "close"), (CAN_MIN, "min"), (CAN_MAX, "max")]:
        hov = hovering_can == hov_key
        draw_spray_can(cr, can["cx"], can["cy"], can["color"], hovered=hov)

    # ── Spray cloud label near cans (Caveat tiny) ──
    labels = [("✕ close", CAN_CLOSE), ("▂ min", CAN_MIN), ("▣ max", CAN_MAX)]
    for lbl, can in labels:
        cr.select_font_face("Caveat", 0, 0)
        cr.set_font_size(10)
        ext2 = cr.text_extents(lbl)
        cr.set_source_rgba(1, 1, 1, 0.35)
        cr.move_to(can["cx"] - ext2.width / 2 - ext2.x_bearing, BORDER_TOP - 5)
        cr.show_text(lbl)


def draw_idle_overlay(cr, w, h, phase):
    """Frosted glass idle overlay. phase 0=transparent, 1=full frost."""
    alpha = min(phase, 1.0)

    # Frosted blur simulation — multiple layers of semi-transparent dark
    cr.set_source_rgba(0.04, 0.03, 0.10, alpha * 0.88)
    cr.rectangle(0, 0, w, h)
    cr.fill()

    # Large blurred shapes to simulate frosted-glass depth
    rng = _rng(999)
    for _ in range(12):
        bx = rng.uniform(0, w)
        by = rng.uniform(0, h)
        bw = rng.uniform(80, 280)
        bh = rng.uniform(40, 180)
        bcol = rng.choice(PALETTE)
        cr.set_source_rgba(*bcol, alpha * 0.04)
        cr.arc(bx, by, bw * 0.6, 0, math.pi * 2)
        cr.fill()

    if alpha < 0.3:
        return

    # NYXUS logo (glowing, pulsing)
    cx_lgo, cy_lgo = w / 2, h / 2 - 30
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(64)
    logo = "NYXUS"
    ext = cr.text_extents(logo)
    lx = cx_lgo - ext.width / 2 - ext.x_bearing
    ly = cy_lgo
    for blur_a in [0.08, 0.14, 0.20]:
        cr.set_source_rgba(*C_PINK, alpha * blur_a)
        cr.set_line_width(12)
        cr.move_to(lx + 1, ly + 1)
        cr.text_path(logo)
        cr.stroke()
    cr.set_source_rgba(1, 0, 1, alpha * 0.92)
    cr.move_to(lx, ly)
    cr.show_text(logo)

    cr.select_font_face("Caveat", 0, 0)
    cr.set_font_size(18)
    sub = "terminal sleeping — press any key"
    ext2 = cr.text_extents(sub)
    cr.set_source_rgba(1, 1, 1, alpha * 0.55)
    cr.move_to(w / 2 - ext2.width / 2 - ext2.x_bearing, cy_lgo + 52)
    cr.show_text(sub)

    # Graffiti drips down from NYXUS text
    for i, col in enumerate(PALETTE[:4]):
        dx = lx + (i + 0.5) * ext.width / 4
        _draw_drip(cr, dx, cy_lgo + 10, col, h * 0.25, _rng(i * 37))


# ── Graffiti selection overlay ────────────────────────────────────────────────
class SelSplatter:
    """One spray-paint mark for the selection overlay."""
    def __init__(self, x, y, color):
        self.x, self.y = x, y
        self.color = color
        self.alpha = 0.72
        self.size = random.uniform(10, 28)
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
        spray_dots(cr, self.x, self.y, self.color,
                   n=35, spread=self.size, alpha_max=op * 0.7)
        cr.set_source_rgba(*self.color, op * 0.45)
        cr.arc(self.x, self.y, self.size * 0.35, 0, math.pi * 2)
        cr.fill()


# ── Main Application ──────────────────────────────────────────────────────────
class NyxusTerminal(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.terminal",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self._hovering_can = None
        self._drag_start = None
        self._win_start = None
        self._last_input = time.monotonic()
        self._idle_phase = 0.0          # 0=awake, 1=fully blurred
        self._idle_animating = False
        self._splatters: list[SelSplatter] = []
        self._btn_pressed = False
        self._sel_color_idx = 0
        self._anim_t = 0.0

    def do_activate(self):
        # CSS
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        # Window
        self.win = Gtk.ApplicationWindow(application=self, title="NYXUS Terminal")
        self.win.set_default_size(WIN_W, WIN_H)
        self.win.set_decorated(False)
        self.win.set_resizable(True)

        # ── Overlay stack ──────────────────────────────────────────────────
        overlay = Gtk.Overlay()
        self.win.set_child(overlay)

        # Layer 0 — chrome + graffiti background (full window)
        self._chrome_da = Gtk.DrawingArea()
        self._chrome_da.set_draw_func(self._draw_chrome_bg, None)
        self._chrome_da.set_can_focus(False)
        overlay.set_child(self._chrome_da)

        if HAS_VTE:
            # Layer 1 — VTE terminal inside brick borders
            self._vte = Vte.Terminal()
            self._vte.set_halign(Gtk.Align.FILL)
            self._vte.set_valign(Gtk.Align.FILL)
            self._vte.set_margin_top(BORDER_TOP)
            self._vte.set_margin_bottom(BORDER_BOTTOM)
            self._vte.set_margin_start(BORDER_SIDE)
            self._vte.set_margin_end(BORDER_SIDE)
            self._setup_vte()
            overlay.add_overlay(self._vte)
        else:
            lbl = Gtk.Label(label="⚠ VTE not installed.\nInstall: sudo pacman -S vte4 python-gobject\nor: sudo apt install gir1.2-vte-2.91")
            lbl.set_halign(Gtk.Align.CENTER)
            lbl.set_valign(Gtk.Align.CENTER)
            lbl.set_margin_top(BORDER_TOP)
            lbl.set_margin_bottom(BORDER_BOTTOM)
            lbl.set_margin_start(BORDER_SIDE)
            lbl.set_margin_end(BORDER_SIDE)
            overlay.add_overlay(lbl)

        # Layer 2 — graffiti selection overlay (transparent until used)
        self._sel_da = Gtk.DrawingArea()
        self._sel_da.set_draw_func(self._draw_sel_overlay, None)
        self._sel_da.set_can_focus(False)
        self._sel_da.set_halign(Gtk.Align.FILL)
        self._sel_da.set_valign(Gtk.Align.FILL)
        overlay.add_overlay(self._sel_da)
        overlay.set_clip_overlay(self._sel_da, False)

        # Layer 3 — idle blur overlay
        self._idle_da = Gtk.DrawingArea()
        self._idle_da.set_draw_func(self._draw_idle, None)
        self._idle_da.set_can_focus(False)
        self._idle_da.set_halign(Gtk.Align.FILL)
        self._idle_da.set_valign(Gtk.Align.FILL)
        overlay.add_overlay(self._idle_da)
        overlay.set_clip_overlay(self._idle_da, False)

        # ── Input controllers ──────────────────────────────────────────────

        # Click on chrome (spray cans, window drag)
        click = Gtk.GestureClick()
        click.set_button(1)
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect("pressed",  self._on_click_pressed)
        click.connect("released", self._on_click_released)
        self._chrome_da.add_controller(click)

        # Mouse motion for hover + drag + selection graffiti
        motion = Gtk.EventControllerMotion()
        motion.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        motion.connect("motion", self._on_motion)
        self.win.add_controller(motion)

        # Key press — wake from idle, track last input
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        key_ctrl.connect("key-pressed", self._on_key)
        self.win.add_controller(key_ctrl)

        # Mouse click — track for idle reset + graffiti
        win_click = Gtk.GestureClick()
        win_click.set_button(0)  # any button
        win_click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        win_click.connect("pressed",  self._on_win_press)
        win_click.connect("released", self._on_win_release)
        self.win.add_controller(win_click)

        # ── Timers ────────────────────────────────────────────────────────
        GLib.timeout_add(33, self._animate)         # ~30fps chrome animation
        GLib.timeout_add(5000, self._check_idle)    # idle check every 5s
        GLib.timeout_add(100, self._decay_splatters) # splatter decay

        self.win.present()

    # ── VTE setup ────────────────────────────────────────────────────────────
    def _setup_vte(self):
        vte = self._vte
        # Font — Caveat handwritten
        fdesc = Pango.FontDescription.from_string("Caveat 15")
        vte.set_font(fdesc)
        vte.set_allow_bold(True)
        vte.set_scroll_on_output(True)
        vte.set_scroll_on_keystroke(True)
        vte.set_scrollback_lines(50000)
        vte.set_mouse_autohide(True)
        vte.set_cell_height_scale(1.05)

        # Hyperlinks (Ctrl+click opens URLs)
        try: vte.set_allow_hyperlink(True)
        except AttributeError: pass

        # Sixel inline image graphics (VTE ≥ 0.65) — enables chafa/viu/timg
        try: vte.set_enable_sixel_graphics(True)
        except AttributeError: pass

        # Transparent background so graffiti shows through slightly
        bg = Gdk.RGBA(); bg.red = 0.05; bg.green = 0.03; bg.blue = 0.12; bg.alpha = 0.82
        fg = Gdk.RGBA(); fg.red = 0.92; fg.green = 0.88; fg.blue = 0.98; fg.alpha = 1.0
        vte.set_color_background(bg)
        vte.set_color_foreground(fg)

        # Spray-paint selection colors (neon orange, semi-transparent)
        hl = Gdk.RGBA(); hl.red = 1.0; hl.green = 0.34; hl.blue = 0.0; hl.alpha = 0.58
        hl_fg = Gdk.RGBA(); hl_fg.red = 1.0; hl_fg.green = 1.0; hl_fg.blue = 1.0; hl_fg.alpha = 1.0
        try:
            vte.set_color_highlight(hl)
            vte.set_color_highlight_foreground(hl_fg)
        except AttributeError: pass

        # Neon pink cursor
        cur = Gdk.RGBA(); cur.red = 1.0; cur.green = 0.0; cur.blue = 1.0; cur.alpha = 1.0
        vte.set_color_cursor(cur)

        # NYXUS neon color palette for terminal colors
        def c(r, g, b): col = Gdk.RGBA(); col.red=r; col.green=g; col.blue=b; col.alpha=1; return col
        colors = [
            c(0.08, 0.06, 0.14),  # black
            c(1.00, 0.20, 0.20),  # red
            c(0.22, 1.00, 0.08),  # green
            c(1.00, 1.00, 0.00),  # yellow
            c(0.00, 0.53, 1.00),  # blue
            c(1.00, 0.00, 1.00),  # magenta
            c(0.00, 0.85, 1.00),  # cyan
            c(0.90, 0.88, 0.96),  # white
            c(0.30, 0.22, 0.44),  # bright black
            c(1.00, 0.40, 0.40),  # bright red
            c(0.50, 1.00, 0.40),  # bright green
            c(1.00, 1.00, 0.50),  # bright yellow
            c(0.40, 0.75, 1.00),  # bright blue
            c(1.00, 0.40, 1.00),  # bright magenta
            c(0.40, 1.00, 1.00),  # bright cyan
            c(1.00, 1.00, 1.00),  # bright white
        ]
        vte.set_colors(fg, bg, colors)

        # Spawn shell with truecolor + sixel hints in the environment
        shell = os.environ.get("SHELL", "/bin/bash")
        env = dict(os.environ)
        env.update({
            "TERM":         "xterm-256color",
            "COLORTERM":    "truecolor",
            "TERM_PROGRAM": "nyxus-terminal",
            "FORCE_COLOR":  "3",
        })
        env_list = [f"{k}={v}" for k, v in env.items()]
        vte.spawn_async(
            Vte.PtyFlags.DEFAULT,
            os.path.expanduser("~"),
            [shell],
            env_list,
            GLib.SpawnFlags.DO_NOT_REAP_CHILD,
            None, None, -1, None, None)

        vte.connect("child-exited", lambda *_: self.quit())

    # ── Draw callbacks ────────────────────────────────────────────────────────
    def _draw_chrome_bg(self, area, cr, w, h, _):
        self._anim_t += 0.02
        inner_x = BORDER_SIDE
        inner_y = BORDER_TOP
        inner_w = w - BORDER_SIDE * 2
        inner_h = h - BORDER_TOP - BORDER_BOTTOM

        # Graffiti background (inner terminal area)
        if inner_w > 0 and inner_h > 0:
            draw_graffiti_bg(cr, inner_x, inner_y, inner_w, inner_h, self._anim_t)

        # Brick chrome frame + spray can buttons
        draw_chrome(cr, w, h, self._hovering_can, self._anim_t)

    def _draw_sel_overlay(self, area, cr, w, h, _):
        cr.set_operator(1)  # OVER
        for s in self._splatters:
            if s.alive:
                s.draw(cr)

    def _draw_idle(self, area, cr, w, h, _):
        if self._idle_phase <= 0:
            return
        draw_idle_overlay(cr, w, h, self._idle_phase)

    # ── Animation / timers ───────────────────────────────────────────────────
    def _animate(self):
        self._chrome_da.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _check_idle(self):
        elapsed = time.monotonic() - self._last_input
        if elapsed >= IDLE_SECS and self._idle_phase < 1.0:
            self._idle_phase = min(1.0, self._idle_phase + 0.08)
            self._idle_da.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _decay_splatters(self):
        self._splatters = [s for s in self._splatters if s.alive]
        self._sel_da.queue_draw()
        return GLib.SOURCE_CONTINUE

    # ── Input handlers ────────────────────────────────────────────────────────
    def _reset_idle(self):
        self._last_input = time.monotonic()
        if self._idle_phase > 0:
            self._idle_phase = 0.0
            self._idle_da.queue_draw()

    def _on_key(self, ctrl, keyval, keycode, state):
        self._reset_idle()
        return False  # let VTE handle it

    def _on_win_press(self, gesture, n, x, y):
        self._reset_idle()
        self._btn_pressed = True
        self._sel_color_idx = (self._sel_color_idx + 1) % len(PALETTE)

    def _on_win_release(self, gesture, n, x, y):
        self._btn_pressed = False

    def _on_motion(self, ctrl, x, y):
        # Hover detection for spray cans
        prev = self._hovering_can
        self._hovering_can = None
        for key, can in [("close", CAN_CLOSE), ("min", CAN_MIN), ("max", CAN_MAX)]:
            if abs(x - can["cx"]) < 18 and abs(y - can["cy"]) < 30:
                self._hovering_can = key
                break

        if self._hovering_can != prev:
            self._chrome_da.queue_draw()

        # Graffiti selection — scatter splatters as user drags in terminal area
        if self._btn_pressed:
            ix = BORDER_SIDE; iy = BORDER_TOP
            iw = (self.win.get_width() or WIN_W) - BORDER_SIDE * 2
            ih = (self.win.get_height() or WIN_H) - BORDER_TOP - BORDER_BOTTOM
            if ix < x < ix + iw and iy < y < iy + ih:
                color = PALETTE[self._sel_color_idx]
                self._splatters.append(SelSplatter(x, y, color))
                if random.random() < 0.25:  # occasional extra splatter
                    self._splatters.append(
                        SelSplatter(x + random.gauss(0, 12),
                                    y + random.gauss(0, 12),
                                    PALETTE[(self._sel_color_idx + 1) % len(PALETTE)]))
                self._sel_da.queue_draw()

    def _on_click_pressed(self, gesture, n, x, y):
        self._reset_idle()
        # Spray can hits
        for key, can in [("close", CAN_CLOSE), ("min", CAN_MIN), ("max", CAN_MAX)]:
            if abs(x - can["cx"]) < 18 and abs(y - can["cy"]) < 30:
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

        # Drag window from title bar area
        if y < BORDER_TOP:
            self.win.begin_move_drag(1, int(x), int(y), Gdk.CURRENT_TIME)

    def _on_click_released(self, gesture, n, x, y):
        pass


if __name__ == "__main__":
    if not HAS_VTE:
        print("WARN: VTE not found — terminal will open with install instructions.")
        print("To get the full terminal: sudo pacman -S vte4")
    try:
        NyxusTerminal().run(None)
    except Exception:
        log = "/tmp/nyxus-terminal.log"
        with open(log, "w") as f: traceback.print_exc(file=f)
        print(f"NYXUS Terminal crashed — see {log}")
        sys.exit(1)
