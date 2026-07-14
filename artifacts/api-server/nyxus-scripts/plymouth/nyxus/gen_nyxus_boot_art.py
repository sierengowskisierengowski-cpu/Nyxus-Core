#!/usr/bin/env python3
# ─────────────────────────────────────────────────────────────────────────────
#  NYXUS · Cinematic Boot Splash · asset generator
#  Renders every PNG the Plymouth "nyxus" theme animates:
#    background.png  saucer.png  saucer_glow.png  beam.png  orb.png
#    wordmark.png    tagline.png subline.png
#
#  All sprites carry a true alpha channel so Plymouth can layer them over the
#  nebula backdrop. The saucer, beam and glow are drawn procedurally (clean
#  alpha, tiny files); the nebula backdrop is a rendered cosmic plate; the
#  NYXUS wordmark uses the on-brand Orbitron face.
#
#  Re-run any time:   python3 gen_nyxus_boot_art.py [path/to/nebula-source.png]
#
#  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ─────────────────────────────────────────────────────────────────────────────
import os
import sys
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

HERE = os.path.dirname(os.path.abspath(__file__))

# ── Brand palette (violet / magenta cosmic) ─────────────────────────────────
VIOLET      = (150,  95, 240)
MAGENTA     = (232,  92, 210)
HOT_MAGENTA = (255, 120, 225)
ICE         = (210, 225, 255)
STARLIGHT   = (232, 238, 255)

FONT_ORBITRON = os.path.expanduser("~/.local/share/fonts/nyxus/Orbitron.ttf")
FONT_DEJAVU   = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"

W, H = 1920, 1080  # design reference; the theme scales sprites to the screen


def _load_font(path, size, fallback):
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.truetype(fallback, size)


def save(img, name):
    out = os.path.join(HERE, name)
    img.save(out)
    print(f"  · {name:16s} {img.size[0]}x{img.size[1]}")
    return out


# ═════════════════════════════════════════════════════════════════════════════
# 1 · BACKGROUND — cosmic nebula plate (1920x1080, no alpha needed)
#     Uses a rendered nebula source if provided/available, else a procedural
#     fallback so the generator is fully self-contained.
# ═════════════════════════════════════════════════════════════════════════════
def build_background(src=None):
    candidates = [src] if src else []
    candidates += [
        os.path.join(HERE, "_nebula_source.png"),
        os.path.expanduser(
            "~/.cursor/projects/home-cosmic-Nyxus-Core/assets/nyxus-boot-nebula.png"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            im = Image.open(c).convert("RGB")
            # cover-fit to 1920x1080
            scale = max(W / im.width, H / im.height)
            im = im.resize((round(im.width * scale), round(im.height * scale)),
                           Image.LANCZOS)
            left = (im.width - W) // 2
            top = (im.height - H) // 2
            im = im.crop((left, top, left + W, top + H))
            # deepen the top so the descending saucer reads against dark space
            grad = np.linspace(0.55, 1.0, H)[:, None]
            arr = np.asarray(im).astype(np.float32)
            arr *= grad[..., None]
            save(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)),
                 "background.png")
            return

    # ── procedural fallback nebula ──
    rng = np.random.default_rng(7)
    y = np.linspace(0, 1, H)[:, None]
    base = np.zeros((H, W, 3), np.float32)
    glow = (np.clip(1.0 - (np.linspace(0, 1, H) - 0.82) ** 2 * 6, 0, 1))[:, None]
    for ch, v in enumerate(MAGENTA):
        base[..., ch] += glow * v * 0.5
    base[..., 0] += y[:, 0][:, None] * VIOLET[0] * 0.12
    base[..., 2] += y[:, 0][:, None] * VIOLET[2] * 0.18
    img = Image.fromarray(np.clip(base, 0, 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(60))
    d = ImageDraw.Draw(img)
    for _ in range(1400):
        x, yy = rng.integers(0, W), rng.integers(0, H)
        r = rng.choice([1, 1, 1, 2])
        b = rng.integers(120, 255)
        d.ellipse([x - r, yy - r, x + r, yy + r], fill=(b, b, min(255, b + 20)))
    save(img, "background.png")


# ═════════════════════════════════════════════════════════════════════════════
# 2 · SAUCER — glowing metallic disc with dome + underlights (alpha)
# ═════════════════════════════════════════════════════════════════════════════
def build_saucer():
    S = 4  # supersample
    cw, ch = 1120, 460
    im = Image.new("RGBA", (cw * S, ch * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    cx = cw * S // 2
    hull_cy = int(ch * S * 0.60)
    hw = int(cw * S * 0.46)   # hull half-width
    hh = int(ch * S * 0.13)   # hull half-height

    # lower hull (dark violet metal, layered ellipses for a beveled look)
    for i, (col, sx, sy, dy) in enumerate([
        ((36, 26, 60),   1.00, 1.00, 0),
        ((58, 40, 96),   0.94, 0.86, -int(hh * 0.18)),
        ((92, 66, 150),  0.82, 0.66, -int(hh * 0.42)),
        ((140, 104, 210), 0.66, 0.5, -int(hh * 0.62)),
    ]):
        d.ellipse([cx - int(hw * sx), hull_cy - int(hh * sy) + dy,
                   cx + int(hw * sx), hull_cy + int(hh * sy) + dy], fill=col)

    # bright rim edge
    d.ellipse([cx - hw, hull_cy - hh, cx + hw, hull_cy + hh], outline=ICE,
              width=3 * S)

    # dome (glassy violet)
    dome_w = int(hw * 0.42)
    dome_h = int(hh * 2.4)
    dome_cy = hull_cy - int(hh * 0.35)
    for col, s in [((70, 52, 120), 1.0), ((120, 92, 200), 0.7),
                   ((200, 180, 255), 0.34)]:
        d.ellipse([cx - int(dome_w * s), dome_cy - int(dome_h * s),
                   cx + int(dome_w * s), dome_cy + int(dome_h * (s * 0.6))],
                  fill=col)

    # underside rim lights
    n = 9
    for i in range(n):
        t = i / (n - 1)
        lx = cx + int((t - 0.5) * 2 * hw * 0.78)
        ly = hull_cy + int(hh * 0.55) - int(math.cos((t - 0.5) * math.pi) * hh * 0.25)
        col = HOT_MAGENTA if i % 2 == 0 else (150, 210, 255)
        r = 7 * S
        d.ellipse([lx - r, ly - r, lx + r, ly + r], fill=col + (255,))

    # central emitter (bright, where the beam is born)
    er = int(hw * 0.13)
    ey = hull_cy + int(hh * 0.65)
    d.ellipse([cx - er, ey - er // 2, cx + er, ey + er // 2],
              fill=HOT_MAGENTA + (255,))

    im = im.resize((cw, ch), Image.LANCZOS)

    # soft outer glow behind the hull
    glow = im.filter(ImageFilter.GaussianBlur(18))
    out = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    out = Image.alpha_composite(out, glow)
    out = Image.alpha_composite(out, im)
    save(out, "saucer.png")

    # separate big soft halo (added under the saucer for the "arrival" bloom)
    halo = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
    hd = ImageDraw.Draw(halo)
    hd.ellipse([cx // S - hw // S, hull_cy // S - hh // S,
                cx // S + hw // S, hull_cy // S + hh // S],
               fill=MAGENTA + (120,))
    halo = halo.filter(ImageFilter.GaussianBlur(70))
    save(halo, "saucer_glow.png")


# ═════════════════════════════════════════════════════════════════════════════
# 3 · BEAM — tractor beam cone (alpha, magenta → transparent)
# ═════════════════════════════════════════════════════════════════════════════
def build_beam():
    bw, bh = 900, 780
    xs = np.linspace(-1, 1, bw)[None, :]
    ys = np.linspace(0, 1, bh)[:, None]
    top_half = 0.06          # cone half-width at the top (at emitter)
    bot_half = 0.95          # cone half-width at the floor
    half = top_half + (bot_half - top_half) * ys
    inside = np.abs(xs) < half
    edge = np.clip(1.0 - (np.abs(xs) / np.maximum(half, 1e-3)) ** 2, 0, 1)
    vert = np.clip(1.0 - ys * 0.65, 0, 1)          # fades toward the floor
    vert *= np.clip(ys * 6, 0, 1)                  # soft birth at the emitter
    alpha = (edge * vert) * inside
    alpha = alpha ** 1.1

    beam = np.zeros((bh, bw, 4), np.float32)
    # colour ramps violet(top) → magenta(bottom)
    for ch in range(3):
        beam[..., ch] = VIOLET[ch] + (HOT_MAGENTA[ch] - VIOLET[ch]) * ys
    beam[..., 3] = alpha * 210
    img = Image.fromarray(np.clip(beam, 0, 255).astype(np.uint8))
    img = img.filter(ImageFilter.GaussianBlur(6))
    # bright core seam
    core = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    cd = ImageDraw.Draw(core)
    cd.polygon([(bw // 2 - 4, 0), (bw // 2 + 4, 0),
                (bw // 2 + 40, bh), (bw // 2 - 40, bh)],
               fill=HOT_MAGENTA + (90,))
    core = core.filter(ImageFilter.GaussianBlur(10))
    img = Image.alpha_composite(img, core)
    save(img, "beam.png")


# ═════════════════════════════════════════════════════════════════════════════
# 4 · ORB — rising beam particle (alpha)
# ═════════════════════════════════════════════════════════════════════════════
def build_orb():
    s = 96
    im = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([s * 0.30, s * 0.30, s * 0.70, s * 0.70],
              fill=HOT_MAGENTA + (255,))
    im = im.filter(ImageFilter.GaussianBlur(9))
    d = ImageDraw.Draw(im)
    d.ellipse([s * 0.42, s * 0.42, s * 0.58, s * 0.58], fill=ICE + (255,))
    save(im, "orb.png")


# ═════════════════════════════════════════════════════════════════════════════
# 5 · TEXT — NYXUS wordmark (Orbitron) + tagline + subline (alpha, glow)
# ═════════════════════════════════════════════════════════════════════════════
def _glow_text(text, font, fill, glow_col, tracking=0, glow_radius=16,
               glow_alpha=200, pad=80):
    # measure with tracking
    tmp = Image.new("RGBA", (10, 10))
    td = ImageDraw.Draw(tmp)
    widths, height = [], 0
    for chx in text:
        b = td.textbbox((0, 0), chx, font=font)
        widths.append(b[2] - b[0])
        height = max(height, b[3] - b[1])
    total = sum(widths) + tracking * max(0, len(text) - 1)
    W2 = int(total + pad * 2)
    H2 = int(height + pad * 2)
    layer = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    x = pad
    asc, desc = font.getmetrics()
    y = pad - (asc - height) + (asc - height)  # baseline-ish; we top-align
    y = pad - 0
    for chx, w in zip(text, widths):
        ld.text((x, pad), chx, font=font, fill=fill + (255,))
        x += w + tracking
    # build glow from alpha
    glow = Image.new("RGBA", (W2, H2), (0, 0, 0, 0))
    a = layer.split()[3]
    solid = Image.new("RGBA", (W2, H2), glow_col + (0,))
    solid.putalpha(a)
    glow = solid.filter(ImageFilter.GaussianBlur(glow_radius))
    # amplify glow alpha
    ga = glow.split()[3].point(lambda p: min(255, int(p * (glow_alpha / 120))))
    glow.putalpha(ga)
    out = Image.alpha_composite(glow, layer)
    return out.crop(out.getbbox())


def build_text():
    orb = _load_font(FONT_ORBITRON, 240, FONT_DEJAVU)
    wm = _glow_text("NYXUS", orb, STARLIGHT, MAGENTA, tracking=28,
                    glow_radius=26, glow_alpha=235)
    save(wm, "wordmark.png")

    tag_f = _load_font(FONT_DEJAVU, 52, FONT_DEJAVU)
    tag = _glow_text("W E L C O M E   T O   T H E   D A R K S I D E", tag_f,
                     ICE, VIOLET, tracking=6, glow_radius=12, glow_alpha=150)
    save(tag, "tagline.png")

    sub_f = _load_font(FONT_DEJAVU, 30, FONT_DEJAVU)
    sub = _glow_text("NYXUS · SIERENGOWSKI · 2026", sub_f, (168, 176, 200),
                     VIOLET, tracking=4, glow_radius=6, glow_alpha=90)
    save(sub, "subline.png")


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else None
    print("NYXUS cinematic boot art →", HERE)
    build_background(src)
    build_saucer()
    build_beam()
    build_orb()
    build_text()
    print("done.")
