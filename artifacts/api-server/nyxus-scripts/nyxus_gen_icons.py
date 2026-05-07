#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Icon Generator — Paint-splatter neon app icons via Cairo      ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝

__nyxid__ = "4e59582d4a35572d323032362d53494552454e474f57534b492d4c4f434b4544"

def _nyx_integrity():
    try:
        _s = open(__file__, encoding="utf-8").read()
        assert "SIERENGOWSKI" in _s, "NYXUS: tamper detected"
    except (OSError, AssertionError) as _e:
        import sys as _sys; print(f"NYXUS SECURITY: {_e}", file=_sys.stderr)

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

_nyx_integrity()


import math, os, random
try:
    import cairo
except ImportError:
    print("pycairo not found — run: pip install pycairo  or  pacman -S python-cairo")
    raise SystemExit(1)

ICON_DIR = os.path.expanduser("~/.local/share/icons/hicolor/256x256/apps")
os.makedirs(ICON_DIR, exist_ok=True)

SIZE = 256
BG   = (0.031, 0.031, 0.055)

NEON = [
    (1.00, 0.00, 1.00),
    (0.80, 0.00, 1.00),
    (0.00, 0.53, 1.00),
    (0.22, 1.00, 0.08),
    (1.00, 1.00, 0.00),
    (1.00, 0.33, 0.00),
]

APPS = [
    # ── original apps ────────────────────────────────────────────────────
    ("io.nyxus.sysmon",        "SYSMON",   (1.00, 0.00, 1.00)),
    ("io.nyxus.stickies",      "STICKIES", (1.00, 1.00, 0.00)),
    ("io.nyxus.weather",       "WEATHER",  (0.00, 0.53, 1.00)),
    ("io.nyxus.notepad",       "NOTEPAD",  (0.80, 0.00, 1.00)),
    ("io.nyxus.terminal",      "TERMINAL", (0.22, 1.00, 0.08)),
    ("io.nyxus.control",       "CONTROL",  (1.00, 0.33, 0.00)),
    ("io.nyxus.godsapp",       "GODSAPP",  (1.00, 0.84, 0.00)),
    ("io.nyxus.studio",        "STUDIO",   (1.00, 0.24, 0.65)),
    ("io.nyxus.sage",          "SAGE",     (0.30, 0.89, 0.89)),
    ("io.nyxus.shield",        "SHIELD",   (0.29, 0.87, 0.50)),
    ("io.nyxus.settings",      "SETTINGS", (0.65, 0.55, 0.98)),
    # ── extended apps ────────────────────────────────────────────────────
    ("io.nyxus.passwords",     "PASSWD",   (1.00, 0.33, 0.00)),
    ("io.nyxus.panel",         "PANEL",    (0.00, 0.53, 1.00)),
    ("io.nyxus.intel",         "INTEL",    (0.00, 0.73, 1.00)),
    ("io.nyxus.start",         "START",    (1.00, 0.00, 0.80)),
    ("io.nyxus.home",          "HOME",     (1.00, 0.84, 0.00)),
    ("io.nyxus.phantom",       "PHANTOM",  (0.50, 0.00, 1.00)),
    # ── legacy aliases (match .desktop Icon= names from older installs) ──
    ("nyxus-home",             "HOME",     (1.00, 0.84, 0.00)),
]


def sketch_rect(cr, x, y, w, h, r, g, b, thick=3.0):
    rng = random.Random(int(x*3+y*7+w*11+h*13) % 65535)
    j = lambda s=1.0: rng.uniform(-3*s, 3*s)
    cr.set_source_rgba(r, g, b, 0.88)
    cr.set_line_width(thick)
    cr.set_line_cap(1); cr.set_line_join(1)
    cr.move_to(x+j(.4),       y+j(.4))
    cr.curve_to(x+w*.33+j(), y+j(),      x+w*.67+j(), y+j(),      x+w+j(.4), y+j(.4))
    cr.curve_to(x+w+j(),     y+h*.33+j(), x+w+j(),    y+h*.67+j(), x+w+j(.4), y+h+j(.4))
    cr.curve_to(x+w*.67+j(), y+h+j(),    x+w*.33+j(), y+h+j(),    x+j(.4),   y+h+j(.4))
    cr.curve_to(x+j(),       y+h*.67+j(), x+j(),      y+h*.33+j(), x+j(.4),   y+j(.4))
    cr.close_path(); cr.stroke()


def hatch_lines(cr, x, y, w, h, r, g, b, alpha=0.10, spacing=14, rng=None):
    """Diagonal sketchy hatch lines for texture."""
    if rng is None:
        rng = random.Random(0)
    cr.save()
    cr.set_source_rgba(r, g, b, alpha)
    cr.set_line_width(1.0)
    n = int((w + h) / spacing)
    for i in range(n):
        off = i * spacing - h
        sx = x + off + rng.uniform(-2, 2)
        sy = y + rng.uniform(-2, 2)
        ex = sx + h + rng.uniform(-4, 4)
        ey = sy + h + rng.uniform(-4, 4)
        cr.move_to(sx, sy); cr.line_to(ex, ey); cr.stroke()
    cr.restore()


def sketch_circle(cr, cx, cy, radius, r, g, b, thick=2.0, alpha=0.85, segments=3, rng=None):
    """Hand-drawn wobbly circle — multiple overlapping passes for sketch feel."""
    if rng is None:
        rng = random.Random(int(cx*7 + cy*11 + radius*13) % 65535)
    cr.set_source_rgba(r, g, b, alpha)
    cr.set_line_width(thick)
    cr.set_line_cap(1)
    for _ in range(segments):
        cr.save()
        cr.translate(cx, cy)
        cr.rotate(rng.uniform(-0.06, 0.06))
        steps = 36
        for i in range(steps + 1):
            ang = (i / steps) * math.pi * 2
            jr = radius + rng.uniform(-2.5, 2.5)
            px = math.cos(ang) * jr
            py = math.sin(ang) * jr
            if i == 0:
                cr.move_to(px, py)
            else:
                cr.line_to(px, py)
        cr.stroke()
        cr.restore()


def gen_icon(app_id, label, color):
    """Hand-drawn sketch-style NYXUS app icon — slightly tilted, consistent set.

    Style spec (matches dashboard aesthetic):
      - Dark frosted background (#08080e)
      - Sketchy wobbly outer border in app color
      - Diagonal hatch texture (very faint)
      - Centered tilted "NYXUS" wordmark in Inter (handwritten)
      - App label below in Inter, tilted in opposite direction
      - Single accent dot for color identity
    """
    r, g, b = color
    seed = abs(hash(app_id)) % 99991
    rng = random.Random(seed)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, SIZE, SIZE)
    cr = cairo.Context(surface)

    # ── Background: deep frosted black ───────────────────────────────────────
    cr.set_source_rgb(*BG)
    cr.rectangle(0, 0, SIZE, SIZE); cr.fill()

    # Subtle inner panel tone
    cr.set_source_rgba(r, g, b, 0.04)
    cr.rectangle(10, 10, SIZE-20, SIZE-20); cr.fill()

    # ── Faint diagonal hatch texture ─────────────────────────────────────────
    hatch_lines(cr, 0, 0, SIZE, SIZE, r, g, b, alpha=0.06, spacing=18, rng=rng)

    # ── Hand-drawn outer border (double-pass for sketch feel) ────────────────
    sketch_rect(cr, 14, 14, SIZE-28, SIZE-28, r, g, b, thick=2.6)
    sketch_rect(cr, 18, 18, SIZE-36, SIZE-36, r, g, b, thick=1.2)

    # ── Sketch corner ticks (hand-drawn) ─────────────────────────────────────
    cr.set_source_rgba(r, g, b, 0.55)
    cr.set_line_width(1.6)
    cr.set_line_cap(1)
    for cx, cy in [(22, 22), (SIZE-22, 22), (22, SIZE-22), (SIZE-22, SIZE-22)]:
        for _ in range(2):
            jx = cx + rng.uniform(-1.5, 1.5)
            jy = cy + rng.uniform(-1.5, 1.5)
            cr.move_to(jx-5, jy); cr.line_to(jx+5, jy); cr.stroke()
            cr.move_to(jx, jy-5); cr.line_to(jx, jy+5); cr.stroke()

    # ── NYXUS wordmark — tilted -4°, hand-drawn shadow + outline ─────────────
    cr.save()
    cr.translate(SIZE/2, SIZE * 0.46)
    cr.rotate(math.radians(-4))
    cr.select_font_face("Inter Display", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(72)
    ext = cr.text_extents("NYXUS")
    tx = -ext.width/2 - ext.x_bearing
    ty = ext.height/2

    # Soft shadow
    cr.set_source_rgba(0, 0, 0, 0.55)
    cr.move_to(tx+2, ty+3); cr.show_text("NYXUS")

    # Color fill
    cr.set_source_rgba(r, g, b, 1.0)
    cr.move_to(tx, ty); cr.show_text("NYXUS")
    cr.restore()

    # ── App label — tilted +5° in opposite direction ─────────────────────────
    cr.save()
    cr.translate(SIZE/2, SIZE * 0.74)
    cr.rotate(math.radians(5))
    cr.select_font_face("Inter Display", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(30)
    ext2 = cr.text_extents(label)
    tx2 = -ext2.width/2 - ext2.x_bearing

    # Hand-drawn underline (wobbly)
    cr.set_source_rgba(r, g, b, 0.75)
    cr.set_line_width(1.8)
    cr.set_line_cap(1)
    ux1 = tx2 - 4
    ux2 = tx2 + ext2.width + 4
    uy = 8
    cr.move_to(ux1, uy + rng.uniform(-1, 1))
    cr.curve_to(
        ux1 + (ux2-ux1)*0.33, uy + rng.uniform(-2, 2),
        ux1 + (ux2-ux1)*0.67, uy + rng.uniform(-2, 2),
        ux2, uy + rng.uniform(-1, 1)
    )
    cr.stroke()

    # Label text
    cr.set_source_rgba(0.95, 0.92, 0.98, 0.92)
    cr.move_to(tx2, 0); cr.show_text(label)
    cr.restore()

    # ── Accent dot (color identity marker, top-left) ─────────────────────────
    sketch_circle(cr, 36, 36, 8, r, g, b, thick=2.0, alpha=0.95, segments=2, rng=rng)
    cr.set_source_rgba(r, g, b, 0.85)
    cr.arc(36, 36, 4, 0, math.pi*2); cr.fill()

    path = os.path.join(ICON_DIR, f"{app_id}.png")
    surface.write_to_png(path)
    sz = os.path.getsize(path)
    print(f"  \033[92m✓\033[0m  {label:10s}  {path}  ({sz} bytes)")


print("\n\033[1m\033[38;5;135m──  NYXUS Icon Generator  ──────────────────────────────────\033[0m")
print(f"   Target dir: {ICON_DIR}")
print(f"   Generating {len(APPS)} icons...\n")

# Wipe ALL old NYXUS icons first so stale files can't shadow new ones
import glob
for stale in glob.glob(os.path.join(ICON_DIR, "io.nyxus.*.png")):
    os.remove(stale)

for app_id, label, color in APPS:
    gen_icon(app_id, label, color)

# Make sure hicolor index.theme exists (otherwise gtk-update-icon-cache silently bails)
hicolor_root = os.path.expanduser("~/.local/share/icons/hicolor")
index_path = os.path.join(hicolor_root, "index.theme")
if not os.path.exists(index_path):
    with open(index_path, "w") as f:
        f.write("[Icon Theme]\nName=Hicolor\nComment=Default Icon Theme\nDirectories=256x256/apps\n\n[256x256/apps]\nSize=256\nType=Fixed\n")

# Force-refresh icon cache (--force --ignore-theme-index)
ret = os.system(f"gtk-update-icon-cache --force --ignore-theme-index {hicolor_root} 2>&1")
print(f"\n   gtk-update-icon-cache exit: {ret}")
os.system("update-desktop-database ~/.local/share/applications/ 2>/dev/null || true")

# Final verification
print("\n\033[1mFinal disk state:\033[0m")
import subprocess
subprocess.run(["ls", "-la", ICON_DIR])

print("\n\033[1m\033[92mIcons installed. Now run:  pkill waybar; sleep 1; setsid waybar &\033[0m\n")
