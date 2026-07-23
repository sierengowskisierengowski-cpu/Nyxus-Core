#!/usr/bin/env python3
"""
NYXUS · Starfield Lock Veil asset generator (rev 2026-07-13)

Fullscreen black/purple void with twinkling stars for the EWW screensaver
and hyprlock background. Reuses the starlight realism model at monitor
resolution. Also writes starfield-center-star.png for the double-click
unlock target.

Outputs (under ~/.config/eww/assets/):
  starfield-lock-base.png
  starfield-lock-twinkle-{0..15}.png
  starfield-center-star.png
"""
import json
import math
import os
import random
import subprocess

from PIL import Image, ImageDraw, ImageFilter

random.seed(20260713)
FRAMES = 16
OUT = os.path.join(os.path.expanduser("~"), ".config", "eww", "assets")
os.makedirs(OUT, exist_ok=True)

FELT_TOP = (14, 7, 26)
FELT_MID = (8, 4, 16)
FELT_BOT = (3, 1, 8)
FELT_ALPHA = 255
LINE = (190, 175, 255)


def tint():
    roll = random.random()
    if roll < 0.72:
        return (255, 255, 255)
    if roll < 0.86:
        return (248, 250, 255)
    if roll < 0.95:
        return (255, 252, 242)
    return (235, 242, 255)


def monitor_size():
    try:
        raw = subprocess.check_output(["hyprctl", "monitors", "-j"], text=True, timeout=3)
        data = json.loads(raw)
        if data:
            return int(data[0].get("width", 1920)), int(data[0].get("height", 1080))
    except Exception:
        pass
    return 1920, 1080


def felt(w, h):
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(h):
        t = y / max(1, h - 1)
        if t < 0.5:
            k = t * 2
            c = tuple(int(FELT_TOP[i] + (FELT_MID[i] - FELT_TOP[i]) * k) for i in range(3))
        else:
            k = (t - 0.5) * 2
            c = tuple(int(FELT_MID[i] + (FELT_BOT[i] - FELT_MID[i]) * k) for i in range(3))
        d.line([(0, y), (w, y)], fill=(*c, FELT_ALPHA))
    haze = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(haze)
    for _ in range(max(6, (w * h) // 180000)):
        cx, cy = random.randint(0, w), random.randint(0, h)
        rr = random.randint(120, max(220, min(w, h) // 3))
        col = random.choice([(96, 52, 190), (58, 28, 140), (120, 44, 170)])
        hd.ellipse((cx - rr, cy - rr // 2, cx + rr, cy + rr // 2), fill=(*col, 4))
    haze = haze.filter(ImageFilter.GaussianBlur(radius=max(28, min(w, h) // 12)))
    img.alpha_composite(haze)
    return img


def star_sprite(size, brightness, col, spikes=False, diag=False):
    r, g, b = col
    spike_len = size * 6.5 if spikes else 0
    pad = int(max(size * 7, spike_len + 3, 4))
    dim = pad * 2 + 1
    cx = cy = pad
    patch = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    bloom = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bloom)
    br = size * 5
    bd.ellipse((cx - br, cy - br, cx + br, cy + br), fill=(r, g, b, int(brightness * 0.48)))
    bloom = bloom.filter(ImageFilter.GaussianBlur(radius=max(0.6, size * 2.0)))
    patch.alpha_composite(bloom)
    halo = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hr = size * 2
    hd.ellipse((cx - hr, cy - hr, cx + hr, cy + hr), fill=(r, g, b, int(brightness * 0.72)))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=max(0.4, size * 0.85)))
    patch.alpha_composite(halo)
    if spikes:
        fl = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
        fd = ImageDraw.Draw(fl)
        a = int(brightness * 0.88)
        fd.line([(cx - spike_len, cy), (cx + spike_len, cy)], fill=(r, g, b, a), width=1)
        fd.line([(cx, cy - spike_len * 0.72), (cx, cy + spike_len * 0.72)], fill=(r, g, b, a), width=1)
        if diag:
            dl = spike_len * 0.45
            ad = int(brightness * 0.35)
            fd.line([(cx - dl, cy - dl), (cx + dl, cy + dl)], fill=(r, g, b, ad), width=1)
            fd.line([(cx - dl, cy + dl), (cx + dl, cy - dl)], fill=(r, g, b, ad), width=1)
        fl = fl.filter(ImageFilter.GaussianBlur(radius=0.7))
        patch.alpha_composite(fl)
    d = ImageDraw.Draw(patch)
    cr = max(0.6, size * 0.55)
    d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr),
              fill=(255, 255, 255, min(255, int(brightness * 1.22))))
    return patch, pad


def put_star(img, x, y, size, brightness, col, spikes=False, diag=False):
    patch, pad = star_sprite(size, brightness, col, spikes, diag)
    img.alpha_composite(patch, (int(x) - pad, int(y) - pad))


class Star:
    def __init__(self, x, y, size, col, base, amp, harmonic, phase, gamma):
        self.x, self.y, self.size, self.col = x, y, size, col
        self.base, self.amp = base, amp
        self.k, self.phase, self.gamma = harmonic, phase, gamma

    def brightness(self, f):
        s = (math.sin(math.tau * self.k * f / FRAMES + self.phase) + 1.0) / 2.0
        return self.base + self.amp * (s ** self.gamma)


def make_star(x, y, size, col, hero=False):
    if hero:
        base = random.uniform(130, 185)
        amp = random.uniform(190, 255)
        gamma = random.uniform(1.0, 1.7)
    elif size >= 1.0:
        base = random.uniform(90, 150)
        amp = random.uniform(110, 180)
        gamma = random.uniform(0.85, 1.5)
    else:
        base = random.uniform(55, 95)
        amp = random.uniform(70, 130)
        gamma = random.uniform(0.65, 1.2)
    k = random.choices([1, 2, 3], weights=[5, 3, 2])[0]
    return Star(x, y, size, col, base, amp, k, random.uniform(0, math.tau), gamma)


def build_center_star():
    size = 4.2
    col = (200, 170, 255)
    patch, pad = star_sprite(size, 255, col, spikes=True, diag=True)
    dim = patch.size[0]
    cx = cy = pad
    glow = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for rr, a in ((28, 40), (48, 22), (72, 10)):
        gd.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(125, 61, 255, a))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=6))
    out = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    out.alpha_composite(glow)
    out.alpha_composite(patch)
    path = os.path.join(OUT, "starfield-center-star.png")
    out.save(path)
    print("wrote", path)


def main():
    w, h = monitor_size()
    cx, cy = w // 2, h // 2 - 40
    base = felt(w, h)
    d = ImageDraw.Draw(base)
    d.line([(cx - 180, cy), (cx + 180, cy)], fill=(*LINE, 14), width=1)
    d.line([(cx, cy - 120), (cx, cy + 120)], fill=(*LINE, 14), width=1)

    stars = []
    n_dust = max(800, (w * h) // 3500)
    n_mid = max(120, (w * h) // 25000)
    n_hero = max(45, (w * h) // 45000)

    for _ in range(n_dust):
        x, y = random.uniform(0, w), random.uniform(0, h)
        stars.append(make_star(x, y, random.uniform(0.35, 0.65), tint()))

    for _ in range(n_mid):
        x, y = random.uniform(0, w), random.uniform(0, h)
        stars.append(make_star(x, y, random.uniform(0.8, 1.6), tint()))

    heroes = []
    tries = 0
    min_gap2 = (w * h / max(1, n_hero)) * 0.12
    while len(heroes) < n_hero and tries < n_hero * 50:
        tries += 1
        x, y = random.uniform(20, w - 20), random.uniform(20, h - 20)
        if (x - cx) ** 2 + (y - cy) ** 2 < 220 ** 2:
            continue
        if any((x - hx) ** 2 + (y - hy) ** 2 < min_gap2 for hx, hy in heroes):
            continue
        heroes.append((x, y))
        stars.append(make_star(x, y, random.uniform(1.6, 2.8), tint(), hero=True))

    stars.append(make_star(cx, cy, 3.8, (210, 180, 255), hero=True))

    base_path = os.path.join(OUT, "starfield-lock-base.png")
    base.save(base_path)
    print("wrote", base_path, f"({w}x{h}, {len(stars)} stars)")

    for f in range(FRAMES):
        frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for s in stars:
            br = s.brightness(f)
            spikes = s.size >= 0.9 and br > 72
            diag = s.size >= 1.5 and br > 115
            put_star(frame, s.x, s.y, s.size, br, s.col, spikes=spikes, diag=diag)
        frame.save(os.path.join(OUT, f"starfield-lock-twinkle-{f}.png"))
    print(f"wrote {FRAMES} twinkle frames")

    build_center_star()


if __name__ == "__main__":
    main()
