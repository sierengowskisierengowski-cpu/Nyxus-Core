#!/usr/bin/env python3
"""
NYXUS · graffiti ghost asset generator (rev 2026-07-09)

Renders the barely-there spray-art texture strips that the eww bars and
overlay backdrops weave into their fills:

  assets/graffiti-strip.png   1896x49   bottom bar underlay
  assets/graffiti-top.png     1896x32   top bar underlay
  assets/graffiti-rail.png      56x760  vertical rail underlay
  assets/graffiti-corner.png   520x300  dashboard/overlay corner tag

Style contract: deep-ink transparent background, spray blobs / marker
tags / drips at 4-8% alpha, denser near the end-caps where bar content
is sparse. Colors ride the live accent pair + fixed HUD neons pulled
from ~/.config/nyxus/accent.json at generation time — re-run this after
switching presets if you want the ghosting re-tinted.
"""
import json, math, os, random
from PIL import Image, ImageDraw, ImageFilter, ImageFont

random.seed(58)  # deterministic assets

HOME = os.path.expanduser("~")
OUT = os.path.join(HOME, ".config/eww/assets")
FONTS = os.path.join(HOME, ".local/share/fonts/nyxus")
os.makedirs(OUT, exist_ok=True)

def accent_pair():
    try:
        with open(os.path.join(HOME, ".config/nyxus/accent.json")) as f:
            data = json.load(f)
        preset = data["presets"][data.get("active", "prism")]
        return preset["primary"], preset["secondary"], preset.get("warn", "#ff8b26")
    except Exception:
        return "#ff4994", "#26ff39", "#ff8b26"

PRIMARY, SECONDARY, WARN = accent_pair()
WHITE = "#e8edf5"

def rgb(hexcol):
    h = hexcol.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

PALETTE = [rgb(PRIMARY), rgb(SECONDARY), rgb(WARN), rgb(WHITE)]

def spray_blob(draw, cx, cy, r, color, alpha, n=140):
    """clustered dot cloud ≈ a spray-paint burst"""
    for _ in range(n):
        ang = random.uniform(0, math.tau)
        dist = abs(random.gauss(0, r / 2.2))
        x, y = cx + dist * math.cos(ang), cy + dist * math.sin(ang)
        s = random.uniform(0.6, 2.2)
        a = int(alpha * max(0.18, 1 - dist / (r + 1)))
        draw.ellipse((x - s, y - s, x + s, y + s), fill=color + (a,))

def marker_tag(img, text, xy, size, color, alpha, angle=0, font="PermanentMarker-Regular.ttf"):
    fnt = ImageFont.truetype(os.path.join(FONTS, font), size)
    pad = size
    tag = Image.new("RGBA", (int(size * len(text) * 0.9) + pad * 2, size * 2 + pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(tag)
    d.text((pad, pad // 2), text, font=fnt, fill=color + (alpha,))
    tag = tag.rotate(angle, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(tag, (int(xy[0]), int(xy[1])))

def drip(draw, x, y, length, color, alpha, w=2):
    """paint run: a thin fading vertical dribble with a bead at the end"""
    for i in range(length):
        a = int(alpha * (1 - i / length) ** 0.6)
        draw.line((x, y + i, x, y + i + 1), fill=color + (a,), width=w)
    draw.ellipse((x - w, y + length - 2, x + w, y + length + 2),
                 fill=color + (int(alpha * 0.8),))

def strip(path, w, h, tags, blobs, drips, edge_boost=True):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    for _ in range(blobs):
        col = random.choice(PALETTE)
        # denser near the end caps where content is sparse
        if edge_boost and random.random() < 0.55:
            cx = random.choice([random.uniform(0, w * 0.16), random.uniform(w * 0.84, w)])
        else:
            cx = random.uniform(0, w)
        spray_blob(draw, cx, random.uniform(0, h), random.uniform(h * 0.25, h * 0.85),
                   col, random.randint(34, 58), n=260)
    for text, rel_x, size, angle in tags:
        col = random.choice(PALETTE)
        marker_tag(img, text, (rel_x * w, random.uniform(-h * 0.15, h * 0.25)),
                   size, col, random.randint(44, 72), angle)
    for _ in range(drips):
        col = random.choice(PALETTE)
        x = random.choice([random.uniform(6, w * 0.14), random.uniform(w * 0.86, w - 6)]) if edge_boost else random.uniform(0, w)
        drip(draw, x, random.uniform(0, h * 0.4), random.randint(int(h * 0.3), int(h * 0.85)),
             col, random.randint(34, 56), w=3)
    img = img.filter(ImageFilter.GaussianBlur(0.5))
    img.save(path)
    print("wrote", path)

# bottom bar underlay
strip(os.path.join(OUT, "graffiti-strip.png"), 1896, 49,
      tags=[("NYXUS", 0.015, 28, 4), ("✕", 0.10, 32, -8), ("VOID", 0.885, 26, -5), ("✕", 0.965, 30, 10)],
      blobs=52, drips=14)

# top bar underlay
strip(os.path.join(OUT, "graffiti-top.png"), 1896, 32,
      tags=[("✕", 0.02, 22, -6), ("NYXUS", 0.42, 20, 3), ("nyx", 0.94, 20, 6)],
      blobs=42, drips=10)

# vertical rail underlay
img = Image.new("RGBA", (56, 760), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
for _ in range(46):
    col = random.choice(PALETTE)
    spray_blob(d, random.uniform(0, 56), random.uniform(0, 760), random.uniform(16, 36),
               col, random.randint(32, 54), n=240)
for _ in range(12):
    col = random.choice(PALETTE)
    drip(d, random.uniform(8, 48), random.uniform(20, 640), random.randint(40, 110),
         col, random.randint(32, 54), w=3)
img = img.filter(ImageFilter.GaussianBlur(0.5))
img.save(os.path.join(OUT, "graffiti-rail.png"))
print("wrote", os.path.join(OUT, "graffiti-rail.png"))

# overlay corner tag (dashboard bottom-right ghost)
img = Image.new("RGBA", (520, 300), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
for _ in range(10):
    col = random.choice(PALETTE)
    spray_blob(d, random.uniform(140, 520), random.uniform(60, 300), random.uniform(40, 90),
               col, random.randint(8, 14), n=220)
marker_tag(img, "NYXUS", (30, 60), 84, rgb(PRIMARY), 14, -7)
marker_tag(img, "dark mirror", (120, 190), 40, rgb(SECONDARY), 16, -4, font="Caveat.ttf")
for _ in range(4):
    col = random.choice(PALETTE)
    drip(d, random.uniform(60, 460), random.uniform(120, 200), random.randint(40, 90),
         col, random.randint(10, 18), w=3)
img = img.filter(ImageFilter.GaussianBlur(0.8))
img.save(os.path.join(OUT, "graffiti-corner.png"))
print("wrote", os.path.join(OUT, "graffiti-corner.png"))
