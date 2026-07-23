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
    col = random.choice([(125, 61, 255, 18), (57, 255, 20, 14), (255, 45, 85, 12)])
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
for rad, col, a in [(140, (255, 138, 30), 90), (110, (255, 120, 70), 70), (85, (255, 45, 85), 50)]:
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
nd.ellipse((-60, 80, 360, 420), fill=(125, 61, 255, 28))
nd.ellipse((180, 200, 560, 520), fill=(57, 255, 20, 18))
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

# dashboard - wide milky way panorama
DW, DH = 1280, 900
img = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
for y in range(DH):
    t = y / max(1, DH - 1)
    c = (int(6 + 8 * (1 - t)), int(2 + 6 * (1 - t)), int(14 + 18 * (1 - t)), 250)
    d.line([(0, y), (DW, y)], fill=c)
band = Image.new("RGBA", (DW, DH), (0, 0, 0, 0))
bd = ImageDraw.Draw(band)
for i in range(120):
    x = random.randint(-80, DW + 80)
    y = random.randint(200, 650)
    rr = random.randint(80, 260)
    col = random.choice([(125, 61, 255, 16), (57, 255, 20, 12), (255, 45, 85, 10)])
    bd.ellipse((x - rr, y - rr // 2, x + rr, y + rr // 2), fill=col)
band = band.filter(ImageFilter.GaussianBlur(26))
img = Image.alpha_composite(img, band)
d = ImageDraw.Draw(img)
for _ in range(420):
    x, y = random.randint(0, DW - 1), random.randint(0, DH - 1)
    br = random.randint(130, 255)
    r = random.choice([1, 1, 2, 2, 3])
    d.ellipse((x - r, y - r, x + r, y + r), fill=(br, br, min(255, br + 10), br))
    if r >= 2 and random.random() < 0.3:
        ln = r * 5
        d.line([(x - ln, y), (x + ln, y)], fill=(255, 255, 255, 110), width=1)
        d.line([(x, y - ln), (x, y + ln)], fill=(255, 255, 255, 90), width=1)
save("cosmic-overlay-dashboard.png", img)

# powermenu - black hole accretion (wide)
PW, PH = 960, 640
img = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
for y in range(PH):
    t = y / max(1, PH - 1)
    c = (int(4 + 6 * (1 - t)), int(1 + 4 * (1 - t)), int(10 + 14 * (1 - t)), 248)
    d.line([(0, y), (PW, y)], fill=c)
bh = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
bd = ImageDraw.Draw(bh)
cx, cy = PW // 2, PH // 2
for rad, col, a in [(220, (255, 138, 30), 70), (170, (255, 120, 70), 55), (120, (255, 45, 85), 40)]:
    bd.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), outline=(*col, a), width=5)
bd.ellipse((cx - 58, cy - 58, cx + 58, cy + 58), fill=(0, 0, 0, 255))
bh = bh.filter(ImageFilter.GaussianBlur(1.5))
img = Image.alpha_composite(img, bh)
d = ImageDraw.Draw(img)
for _ in range(200):
    x, y = random.randint(0, PW - 1), random.randint(0, PH - 1)
    br = random.randint(120, 255)
    r = random.choice([1, 1, 2])
    d.ellipse((x - r, y - r, x + r, y + r), fill=(br, br, min(255, br + 8), br))
save("cosmic-overlay-powermenu.png", img)

# cheatsheet - diamond star field (wide)
cs = Image.new("RGBA", (PW, PH), (0, 0, 0, 0))
cd = ImageDraw.Draw(cs)
for y in range(PH):
    t = y / max(1, PH - 1)
    c = (int(6 + 8 * (1 - t)), int(2 + 6 * (1 - t)), int(14 + 18 * (1 - t)), 245)
    cd.line([(0, y), (PW, y)], fill=c)
for _ in range(380):
    x, y = random.randint(0, PW - 1), random.randint(0, PH - 1)
    br = random.randint(140, 255)
    r = random.choice([1, 1, 2, 2, 3])
    cd.ellipse((x - r, y - r, x + r, y + r), fill=(br, br, min(255, br + 10), br))
    if r >= 2 and random.random() < 0.35:
        ln = r * 5
        cd.line([(x - ln, y), (x + ln, y)], fill=(255, 255, 255, 120), width=1)
        cd.line([(x, y - ln), (x, y + ln)], fill=(255, 255, 255, 100), width=1)
save("cosmic-overlay-cheatsheet.png", cs)

# brightness flyout - soft nebula
img = void()
neb = Image.new("RGBA", (W, H), (0, 0, 0, 0))
nd = ImageDraw.Draw(neb)
nd.ellipse((40, 120, 440, 480), fill=(255, 138, 30, 22))
nd.ellipse((200, 60, 520, 360), fill=(125, 61, 255, 20))
neb = neb.filter(ImageFilter.GaussianBlur(24))
img = Image.alpha_composite(img, neb)
img = stars(img, 200, True)
save("cosmic-flyout-brightness.png", img)

# deepcore - security grid nebula (wide)
DCW, DCH = 1200, 720
img = Image.new("RGBA", (DCW, DCH), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
for y in range(DCH):
    t = y / max(1, DCH - 1)
    c = (int(4 + 6 * (1 - t)), int(1 + 4 * (1 - t)), int(10 + 14 * (1 - t)), 248)
    d.line([(0, y), (DCW, y)], fill=c)
grid = Image.new("RGBA", (DCW, DCH), (0, 0, 0, 0))
gd = ImageDraw.Draw(grid)
for x in range(0, DCW, 48):
    gd.line([(x, 0), (x, DCH)], fill=(57, 255, 20, 10), width=1)
for y in range(0, DCH, 48):
    gd.line([(0, y), (DCW, y)], fill=(125, 61, 255, 10), width=1)
img = Image.alpha_composite(img, grid)
neb = Image.new("RGBA", (DCW, DCH), (0, 0, 0, 0))
nd = ImageDraw.Draw(neb)
nd.ellipse((200, 120, 900, 580), fill=(57, 255, 20, 16))
nd.ellipse((500, 200, 1100, 620), fill=(255, 45, 85, 12))
neb = neb.filter(ImageFilter.GaussianBlur(32))
img = Image.alpha_composite(img, neb)
d = ImageDraw.Draw(img)
for _ in range(320):
    x, y = random.randint(0, DCW - 1), random.randint(0, DCH - 1)
    br = random.randint(120, 255)
    r = random.choice([1, 1, 2])
    d.ellipse((x - r, y - r, x + r, y + r), fill=(br, br, min(255, br + 8), br))
save("cosmic-overlay-deepcore.png", img)

# mission control - milky way panorama (wide)
MW, MH = 1280, 800
img = Image.new("RGBA", (MW, MH), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
for y in range(MH):
    t = y / max(1, MH - 1)
    c = (int(6 + 8 * (1 - t)), int(2 + 6 * (1 - t)), int(14 + 18 * (1 - t)), 248)
    d.line([(0, y), (MW, y)], fill=c)
band = Image.new("RGBA", (MW, MH), (0, 0, 0, 0))
bd = ImageDraw.Draw(band)
for i in range(90):
    x = random.randint(-60, MW + 60)
    y = random.randint(180, 560)
    rr = random.randint(70, 220)
    col = random.choice([(125, 61, 255, 14), (57, 255, 20, 10), (255, 45, 85, 8)])
    bd.ellipse((x - rr, y - rr // 2, x + rr, y + rr // 2), fill=col)
band = band.filter(ImageFilter.GaussianBlur(24))
img = Image.alpha_composite(img, band)
d = ImageDraw.Draw(img)
for _ in range(360):
    x, y = random.randint(0, MW - 1), random.randint(0, MH - 1)
    br = random.randint(130, 255)
    r = random.choice([1, 1, 2, 2, 3])
    d.ellipse((x - r, y - r, x + r, y + r), fill=(br, br, min(255, br + 10), br))
save("cosmic-overlay-mission.png", img)

# boot splash - obsidian prism void (fullscreen)
SW, SH = 1920, 1080
img = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
for y in range(SH):
    t = y / max(1, SH - 1)
    c = (int(3 + 5 * (1 - t)), int(1 + 3 * (1 - t)), int(8 + 12 * (1 - t)), 255)
    d.line([(0, y), (SW, y)], fill=c)
prism = Image.new("RGBA", (SW, SH), (0, 0, 0, 0))
pd = ImageDraw.Draw(prism)
cx, cy = SW // 2, SH // 2
for rad, col, a in [(420, (125, 61, 255), 28), (320, (57, 255, 20), 22), (220, (255, 45, 85), 18)]:
    pd.ellipse((cx - rad, cy - rad, cx + rad, cy + rad), outline=(*col, a), width=3)
prism = prism.filter(ImageFilter.GaussianBlur(2.5))
img = Image.alpha_composite(img, prism)
d = ImageDraw.Draw(img)
for _ in range(500):
    x, y = random.randint(0, SW - 1), random.randint(0, SH - 1)
    br = random.randint(100, 255)
    r = random.choice([1, 1, 2])
    d.ellipse((x - r, y - r, x + r, y + r), fill=(br, br, min(255, br + 10), br))
save("cosmic-overlay-splash.png", img)
