#!/usr/bin/env python3
"""NYXUS trapped-fog vessel texture for obsidian pills (rev 2026-07-12)."""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter

random.seed(7712)
OUT = os.path.join(os.path.expanduser("~"), ".config/eww/assets")
os.makedirs(OUT, exist_ok=True)
SIZE = 160

img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
layer = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
d = ImageDraw.Draw(layer)

for _ in range(42):
    cx = random.uniform(0, SIZE)
    cy = random.uniform(0, SIZE)
    rr = random.uniform(18, 58)
    alpha = random.randint(10, 28)
    tone = random.choice([(210, 220, 255), (195, 205, 245), (225, 230, 255)])
    d.ellipse((cx - rr, cy - rr * 0.55, cx + rr, cy + rr * 0.55), fill=(*tone, alpha))

for _ in range(18):
    cx = random.uniform(0, SIZE)
    cy = random.uniform(0, SIZE)
    rr = random.uniform(8, 22)
    alpha = random.randint(18, 42)
    d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(255, 255, 255, alpha))

layer = layer.filter(ImageFilter.GaussianBlur(radius=9))
layer = layer.filter(ImageFilter.GaussianBlur(radius=4))

# soft vignette so fog feels trapped inside the vessel walls
vig = Image.new("L", (SIZE, SIZE), 0)
vd = ImageDraw.Draw(vig)
vd.ellipse((8, 10, SIZE - 8, SIZE - 10), fill=255)
vig = vig.filter(ImageFilter.GaussianBlur(radius=14))
layer.putalpha(Image.eval(layer.split()[3], lambda a: min(255, int(a * 0.92))))
img = Image.composite(layer, img, vig)

path = os.path.join(OUT, "fog-vessel.png")
img.save(path)
print("wrote", path)
