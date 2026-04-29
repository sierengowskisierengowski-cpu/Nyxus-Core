#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Icon Generator — Paint-splatter neon app icons via Cairo      ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
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
    ("io.nyxus.sysmon",   "SYSMON",   (1.00, 0.00, 1.00)),
    ("io.nyxus.stickies", "STICKIES", (1.00, 1.00, 0.00)),
    ("io.nyxus.weather",  "WEATHER",  (0.00, 0.53, 1.00)),
    ("io.nyxus.notepad",  "NOTEPAD",  (0.80, 0.00, 1.00)),
    ("io.nyxus.terminal", "TERMINAL", (0.22, 1.00, 0.08)),
    ("io.nyxus.control",  "CONTROL",  (1.00, 0.33, 0.00)),
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


def gen_icon(app_id, label, color):
    r, g, b = color
    seed = abs(hash(app_id)) % 99991

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, SIZE, SIZE)
    cr = cairo.Context(surface)

    # Dark background
    cr.set_source_rgb(*BG); cr.rectangle(0, 0, SIZE, SIZE); cr.fill()

    rng = random.Random(seed)

    # Large splatter blobs (background)
    for _ in range(14):
        bx = rng.uniform(8, SIZE-8)
        by = rng.uniform(8, SIZE-8)
        br = rng.uniform(6, 22)
        nc = rng.choice(NEON)
        cr.set_source_rgba(*nc, rng.uniform(0.08, 0.28))
        cr.arc(bx, by, br, 0, math.pi*2); cr.fill()

    # Thin splatter streaks
    for _ in range(20):
        sx = rng.uniform(0, SIZE); sy = rng.uniform(0, SIZE)
        ex = sx + rng.uniform(-40, 40); ey = sy + rng.uniform(-8, 8)
        nc = rng.choice(NEON)
        cr.set_source_rgba(*nc, rng.uniform(0.15, 0.45))
        cr.set_line_width(rng.uniform(0.8, 2.5))
        cr.move_to(sx, sy); cr.line_to(ex, ey); cr.stroke()

    # Small dots
    for _ in range(60):
        bx = rng.uniform(4, SIZE-4); by = rng.uniform(4, SIZE-4)
        br = rng.uniform(1, 4)
        nc = rng.choice(NEON)
        cr.set_source_rgba(*nc, rng.uniform(0.25, 0.65))
        cr.arc(bx, by, br, 0, math.pi*2); cr.fill()

    # Accent splats near the accent color
    for _ in range(8):
        bx = rng.uniform(30, SIZE-30); by = rng.uniform(30, SIZE-30)
        br = rng.uniform(3, 12)
        cr.set_source_rgba(r, g, b, rng.uniform(0.20, 0.50))
        cr.arc(bx, by, br, 0, math.pi*2); cr.fill()

    # Wobbly border
    sketch_rect(cr, 6, 6, SIZE-12, SIZE-12, r, g, b, thick=2.8)

    # "NYXUS" glow text
    cr.select_font_face("Caveat", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    cr.set_font_size(62)
    ext = cr.text_extents("NYXUS")
    tx = (SIZE - ext.width) / 2 - ext.x_bearing
    ty = SIZE * 0.52
    for dx, dy in [(-2,-2),(2,-2),(-2,2),(2,2),(0,-3),(0,3),(-3,0),(3,0)]:
        cr.set_source_rgba(r, g, b, 0.20)
        cr.move_to(tx+dx, ty+dy); cr.show_text("NYXUS")
    cr.set_source_rgba(r, g, b, 1.0)
    cr.move_to(tx, ty); cr.show_text("NYXUS")

    # App label below
    cr.select_font_face("Caveat", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
    cr.set_font_size(24)
    ext2 = cr.text_extents(label)
    tx2 = (SIZE - ext2.width) / 2 - ext2.x_bearing
    cr.set_source_rgba(r, g, b, 0.72)
    cr.move_to(tx2, SIZE * 0.79); cr.show_text(label)

    path = os.path.join(ICON_DIR, f"{app_id}.png")
    surface.write_to_png(path)
    print(f"  \033[92m✓\033[0m  {path}")


print("\n\033[1m\033[38;5;135m──  NYXUS Icon Generator  ──────────────────────────────────\033[0m")
for app_id, label, color in APPS:
    gen_icon(app_id, label, color)

# Refresh icon cache
os.system("gtk-update-icon-cache ~/.local/share/icons/hicolor/ 2>/dev/null || true")
os.system("update-desktop-database ~/.local/share/applications/ 2>/dev/null || true")
print("\n\033[1m\033[92mIcons installed.\033[0m\n")
