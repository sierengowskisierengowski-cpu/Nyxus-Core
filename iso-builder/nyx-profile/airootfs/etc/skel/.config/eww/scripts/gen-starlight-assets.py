#!/usr/bin/env python3
"""
NYXUS · Starlight Headliner asset generator (rev 2026-07-11c)

Rolls-Royce fiber-optic night sky for the four eww bars.

Realism model:
  - base PNG: blackish-purple velvet (gradient + fabric grain + violet
    haze), constellation hairlines, and only the faintest static dust —
    the aggregate glow a real sky has between visible stars.
  - 16 twinkle frames: EVERY visible star is animated. Each star owns a
    random baseline, amplitude, harmonic speed (1/2/3 cycles per loop —
    integer harmonics keep the loop seamless), phase and gamma, so small
    dust shimmers gently while heroes flare with 4-point diffraction
    spikes, all out of sync. Nothing pulses together, nothing strobes.

Surfaces:
  starlight-strip.png / -twinkle-strip-{0..15}.png   1896x49  · Cassiopeia
  starlight-top.png   / -twinkle-top-{0..15}.png     1896x32  · Lyra
  starlight-rail.png  / -twinkle-rail-{0..15}.png      56x760 · Orion

Stars are rendered as small local sprites (patch composite, not
full-image blurs) so the 16-frame full-field animation stays cheap.
"""
import math
import os
import random
from PIL import Image, ImageDraw, ImageFilter

random.seed(2026)

HOME = os.path.expanduser("~")
OUT = os.path.join(HOME, ".config/eww/assets")
os.makedirs(OUT, exist_ok=True)

FRAMES = 16

# OBSIDIAN rework (rev 2026-07-12): near-black obsidian velvet with only
# a whisper of violet at the top edge — the Rolls-Royce headliner is a
# BLACK ceiling, the fibers are the color. Deeper + more opaque than the
# old plum so the wallpaper no longer bleeds a bright "coat" through the
# felt and every star reads as a crisp point of light on true black.
FELT_TOP = (14, 7, 26)     # faint obsidian violet at the top edge
FELT_MID = (8, 4, 16)
FELT_BOT = (3, 1, 8)       # essentially black at the bottom
FELT_ALPHA = 252           # ~0.99 true black ceiling; fibers are the light

LINE = (190, 175, 255)


def tint():
    roll = random.random()
    if roll < 0.72:
        return (255, 255, 255)   # diamond white
    if roll < 0.86:
        return (248, 250, 255)   # ice white
    if roll < 0.95:
        return (255, 252, 242)   # warm diamond
    return (235, 242, 255)       # faint blue-white


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
    grain = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(grain)
    for _ in range((w * h) // 55):
        x, y = random.randint(0, w - 1), random.randint(0, h - 1)
        if random.random() < 0.5:
            gd.point((x, y), fill=(200, 180, 255, random.randint(4, 9)))
        else:
            gd.point((x, y), fill=(0, 0, 0, random.randint(8, 18)))
    grain = grain.filter(ImageFilter.GaussianBlur(radius=0.6))
    img.alpha_composite(grain)
    haze = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    hd = ImageDraw.Draw(haze)
    for _ in range(max(3, (w * h) // 16000)):
        cx, cy = random.randint(0, w), random.randint(0, h)
        rr = random.randint(max(40, min(w, h)), max(90, min(w, h) * 3))
        col = random.choice([(96, 52, 190), (58, 28, 140), (120, 44, 170)])
        hd.ellipse((cx - rr, cy - rr // 3, cx + rr, cy + rr // 3), fill=(*col, 3))
    haze = haze.filter(ImageFilter.GaussianBlur(radius=max(18, min(w, h) // 3)))
    img.alpha_composite(haze)
    return img


def star_sprite(size, brightness, col, spikes, diag=False):
    """Render one star on a small patch: bloom + halo + spikes + core."""
    r, g, b = col
    spike_len = size * 6.5 if spikes else 0
    pad = int(max(size * 7, spike_len + 3, 4))
    dim = pad * 2 + 1
    cx = cy = pad

    patch = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    # wide bloom
    bloom = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    bd = ImageDraw.Draw(bloom)
    br = size * 5
    bd.ellipse((cx - br, cy - br, cx + br, cy + br), fill=(r, g, b, int(brightness * 0.48)))
    bloom = bloom.filter(ImageFilter.GaussianBlur(radius=max(0.6, size * 2.0)))
    patch.alpha_composite(bloom)
    # mid halo
    halo = Image.new("RGBA", (dim, dim), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hr = size * 2
    hd.ellipse((cx - hr, cy - hr, cx + hr, cy + hr), fill=(r, g, b, int(brightness * 0.72)))
    halo = halo.filter(ImageFilter.GaussianBlur(radius=max(0.4, size * 0.85)))
    patch.alpha_composite(halo)
    # diffraction spikes
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
    # hard core
    d = ImageDraw.Draw(patch)
    cr = max(0.6, size * 0.55)
    d.ellipse((cx - cr, cy - cr, cx + cr, cy + cr),
              fill=(255, 255, 255, min(255, int(brightness * 1.22))))
    return patch, pad


def put_star(img, x, y, size, brightness, col, spikes=False, diag=False):
    patch, pad = star_sprite(size, brightness, col, spikes, diag)
    img.alpha_composite(patch, (int(x) - pad, int(y) - pad))


# ── constellations ────────────────────────────────────────────────────
CASSIOPEIA = {
    "pts": [(0.00, 0.75), (0.25, 0.20), (0.50, 0.65), (0.75, 0.15), (1.00, 0.55)],
    "links": [(0, 1), (1, 2), (2, 3), (3, 4)],
}
LYRA = {
    "pts": [(0.10, 0.30), (0.35, 0.15), (0.45, 0.60), (0.75, 0.75), (0.95, 0.35)],
    "links": [(0, 1), (1, 2), (2, 3), (3, 4), (4, 1)],
}
ORION = {
    "pts": [(0.25, 0.05), (0.75, 0.08), (0.35, 0.42), (0.50, 0.50), (0.65, 0.58),
            (0.20, 0.92), (0.80, 0.95)],
    "links": [(0, 1), (0, 2), (1, 4), (2, 3), (3, 4), (2, 5), (4, 6)],
}


class Star:
    """One animated star: position, size, color and its own light curve."""

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


def build(name, w, h, spec, cbox, n_hero, n_mid, n_dust):
    base = felt(w, h)

    # constellation: hairlines are static on the base; its stars animate
    x0, y0, x1, y1 = cbox
    cpts = [(x0 + px * (x1 - x0), y0 + py * (y1 - y0)) for px, py in spec["pts"]]
    d = ImageDraw.Draw(base)
    for a, b in spec["links"]:
        d.line([cpts[a], cpts[b]], fill=(*LINE, 18), width=1)

    stars = []
    for x, y in cpts:
        stars.append(make_star(x, y, random.uniform(2.0, 2.6), tint(), hero=True))

    # static micro-dust floor (the between-stars glow) on the base —
    # dimmed for the obsidian ceiling so the black stays clean between
    # the crisp animated fibers (RR headliner, not a dusty sky).
    for _ in range(n_dust // 2):
        x, y = random.uniform(0, w), random.uniform(1, h - 1)
        d.point((x, y), fill=(*tint(), random.randint(9, 22)))

    # animated dust: tiny but alive
    for _ in range(n_dust // 2):
        x, y = random.uniform(0, w), random.uniform(1, h - 1)
        stars.append(make_star(x, y, random.uniform(0.35, 0.6), tint()))

    # animated mid field
    for _ in range(n_mid):
        x, y = random.uniform(0, w), random.uniform(2, h - 2)
        stars.append(make_star(x, y, random.uniform(0.7, 1.4), tint()))

    # animated heroes, spread out, avoiding the constellation box
    heroes = []
    tries = 0
    min_gap2 = (w * h / max(1, n_hero)) * 0.10
    while len(heroes) < n_hero and tries < n_hero * 40:
        tries += 1
        x, y = random.uniform(8, w - 8), random.uniform(4, h - 4)
        if x0 - 14 < x < x1 + 14 and y0 - 14 < y < y1 + 14:
            continue
        if any((x - hx) ** 2 + (y - hy) ** 2 < min_gap2 for hx, hy in heroes):
            continue
        heroes.append((x, y))
        stars.append(make_star(x, y, random.uniform(1.5, 2.5), tint(), hero=True))

    base.save(os.path.join(OUT, f"starlight-{name}.png"))
    print("wrote", f"starlight-{name}.png", f"({len(stars)} animated stars)")

    for f in range(FRAMES):
        frame = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for s in stars:
            br = s.brightness(f)
            spikes = s.size >= 0.9 and br > 72
            diag = s.size >= 1.5 and br > 115
            put_star(frame, s.x, s.y, s.size, br, s.col, spikes=spikes, diag=diag)
        frame.save(os.path.join(OUT, f"starlight-twinkle-{name}-{f}.png"))
    print(f"wrote {FRAMES} twinkle frames · {name}")


build("strip", 1896, 49, CASSIOPEIA, (1250, 8, 1520, 41), n_hero=38, n_mid=165, n_dust=620)
build("top", 1896, 32, LYRA, (1560, 5, 1740, 27), n_hero=28, n_mid=120, n_dust=460)
build("rail", 56, 760, ORION, (10, 430, 46, 640), n_hero=22, n_mid=90, n_dust=340)
