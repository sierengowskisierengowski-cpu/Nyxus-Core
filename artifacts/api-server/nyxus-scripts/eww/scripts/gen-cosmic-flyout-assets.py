#!/usr/bin/env python3
"""Cosmic flyout panel backdrops for eww (rev 2026-07-12)."""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter

random.seed(8812)
OUT = os.path.join(os.path.expanduser("~"), ".config", "eww", "assets")
os.makedirs(OUT, exist_ok=True)
W, H = 480, 560


def void():
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(H):
        t = y / max(1, H - 1)
        c = (int(6 + 8 * (1 - t)), int(2 + 6 * (1 - t)), int(14 + 18 * (1 - t)), 245)
        d.line([(0, y), (W, y)], fill=c)
    return img


def stars(img, n=220, diamond=False):
    d = ImageDraw.Draw(img)
    for _ in range(n):
        x, y = random.randint(4, W - 4), random.randint(4, H - 4)
        br = random.randint(140, 255)
        r = random.choice([1, 1, 1, 2, 2, 3])
        d.ellipse((x - r, y - r, x + r, y + r), fill=(br, br, min(255, br + 10), br))
        if diamond and r >= 2 and random.random() < 0.35:
            ln = r * 5
            d.line([(x - ln, y), (x + ln, y)], fill=(255, 255, 255, 120), width=1)
            d.line([(x, y - ln), (x, y + ln)], fill=(255, 255, 255, 100), width=1)
    return img


def save(name, img):
    p = os.path.join(OUT, name)
    img.save(p)
    print("wrote", p)


# quicksettings - milky band
img = void()
band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
bd = ImageDraw.Draw(band)
for i in range(80):
    x = random.randint(-40, W + 40)
    y = random.randint(120, 420)
    rr = random.randint(60, 180)
    col = random.choice([(121, 73, 242, 18), (38, 255, 183, 14), (255, 38, 103, 12)])
    bd.ellipse((x - rr, y - rr // 2, x + rr, y + rr // 2), fill=col)
band = band.filter(ImageFilter.GaussianBlur(22))
img = Image.alpha_composite(img, band)
img = stars(img, 260, True)
save("cosmic-flyout-qs.png", img)

# wifi - diamond field
save("cosmic-flyout-wifi.png", stars(void(), 300, True))

# mixer - black hole core
img = void()
bh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
bd = ImageDraw.Draw(bh)
cx, cy = W // 2, H // 2
for rad, col, a in [(140, (255, 176, 38), 90), (110, (255, 120, 70), 70), (85, (255, 38, 103), 50)]:
    bd.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), outline=(*col, a), width=4)
bd.ellipse((cx - 42, cy - 42, cx + 42, cy + 42), fill=(0, 0, 0, 255))
bh = bh.filter(ImageFilter.GaussianBlur(1.2))
img = Image.alpha_composite(img, bh)
img = stars(img, 180, True)
save("cosmic-flyout-mixer.png", img)

# calendar - twin moons
img = void()
img = stars(img, 200, True)
md = ImageDraw.Draw(img)
for mx in (W * 0.3, W * 0.72):
    my = H * 0.22
    rr = 36
    md.ellipse((mx - rr, my - rr, mx + rr, my + rr), fill=(210, 215, 225, 220))
save("cosmic-flyout-cal.png", img)

# notifications - nebula moon
img = void()
neb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
nd = ImageDraw.Draw(neb)
nd.ellipse((-60, 80, 360, 420), fill=(121, 73, 242, 28))
nd.ellipse((180, 200, 560, 520), fill=(38, 255, 183, 18))
neb = neb.filter(ImageFilter.GaussianBlur(28))
img = Image.alpha_composite(img, neb)
img = stars(img, 240, True)
save("cosmic-flyout-notif.png", img)

# updates - milky way variant
img = void()
band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
bd = ImageDraw.Draw(band)
bd.rectangle((0, 200, W, 280), fill=(255, 255, 255, 8))
band = band.filter(ImageFilter.GaussianBlur(12))
img = Image.alpha_composite(img, band)
img = stars(img, 280, True)
save("cosmic-flyout-upd.png", img)
