#!/usr/bin/env python3
"""Generate PLACEHOLDER alien companion sprite frames.

This crops the Nyxus urban-alien mascot out of the emblem artwork, keys the
black background to transparent, and derives a small set of pose frames so the
companion has something to render before the parent drops in polished art.

Every frame is derived from a single clean cutout, so the results are rough on
purpose. The manifest it writes (frames/manifest.json) is the real contract:
swap the PNGs for polished per-pose art with the same filenames (or edit the
manifest) and the companion picks them up with no code changes.

Usage:
    python3 gen_placeholder_sprites.py [--source PATH] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = (
    HERE.parent / "eww" / "assets" / "nyxus-emblem-header.png"
).resolve()
DEFAULT_OUT = HERE / "assets" / "frames"

# Region of the emblem artwork that contains the alien (peace-sign hand + body
# + capped head), excluding the "NYXUS" wordmark and crown on the right.
CROP_BOX = (232, 150, 660, 600)  # left, top, right, bottom

# Target on-desktop sprite height in px (width scales to keep aspect ratio).
TARGET_H = 150

# Accent colors (Nyxus theme).
VIOLET = (121, 73, 242)
MAGENTA = (255, 38, 103)


def key_black_to_alpha(img: Image.Image, thresh: int = 34, feather: int = 10) -> Image.Image:
    """Turn the near-black backdrop transparent while keeping the neon glow.

    Alpha is derived from luminance: fully transparent below ``thresh`` and
    ramping to opaque over a short ``feather`` band, which preserves the soft
    violet halo around the mascot instead of hard-cutting it.
    """
    img = img.convert("RGBA")
    gray = img.convert("L")
    lut = []
    for v in range(256):
        if v <= thresh:
            lut.append(0)
        elif v >= thresh + feather:
            lut.append(255)
        else:
            lut.append(int(round((v - thresh) / feather * 255)))
    alpha = gray.point(lut)
    # Combine with any existing alpha.
    base_alpha = img.getchannel("A")
    alpha = ImageChops.multiply(alpha, base_alpha) if base_alpha.getextrema() != (255, 255) else alpha
    img.putalpha(alpha)
    return img


def autocrop_alpha(img: Image.Image, pad: int = 6) -> Image.Image:
    bbox = img.getchannel("A").getbbox()
    if not bbox:
        return img
    l, t, r, b = bbox
    l = max(0, l - pad)
    t = max(0, t - pad)
    r = min(img.width, r + pad)
    b = min(img.height, b + pad)
    return img.crop((l, t, r, b))


def scale_to_height(img: Image.Image, height: int) -> Image.Image:
    if img.height == height:
        return img
    w = max(1, round(img.width * height / img.height))
    return img.resize((w, height), Image.LANCZOS)


def tint(img: Image.Image, color, amount: float) -> Image.Image:
    """Blend an RGB tint over the opaque pixels, preserving alpha."""
    img = img.convert("RGBA")
    r, g, b, a = img.split()
    solid = Image.new("RGBA", img.size, color + (0,))
    tinted = Image.blend(img.convert("RGBA"), Image.merge("RGBA", (*solid.split()[:3], a)), amount)
    tinted.putalpha(a)
    return tinted


def rotate(img: Image.Image, deg: float) -> Image.Image:
    return img.rotate(deg, resample=Image.BICUBIC, expand=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    src = Path(args.source)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    if not src.exists():
        print(f"source not found: {src}")
        return 1

    full = Image.open(src).convert("RGBA")
    alien = full.crop(CROP_BOX)
    alien = key_black_to_alpha(alien)
    alien = autocrop_alpha(alien)
    base = scale_to_height(alien, TARGET_H)

    # --- Derive pose frames from the single cutout. ---------------------------
    frames: dict[str, Image.Image] = {}

    # Idle: gentle breathing via a barely-scaled second frame.
    frames["idle_0"] = base
    breathe = base.resize(
        (base.width, max(1, round(base.height * 0.985))), Image.LANCZOS
    )
    pad_top = base.height - breathe.height
    idle1 = Image.new("RGBA", base.size, (0, 0, 0, 0))
    idle1.paste(breathe, (0, pad_top), breathe)
    frames["idle_1"] = idle1

    # Walk: slight opposing rotations (code flips horizontally for direction).
    frames["walk_0"] = rotate(base, 3.5)
    frames["walk_1"] = rotate(base, -3.5)

    # Sleep: tilted, dimmed, cooler (violet). 'z z z' is drawn live by the app.
    sleep = rotate(base, 14)
    sleep = ImageEnhance.Brightness(sleep).enhance(0.72)
    sleep = tint(sleep, VIOLET, 0.18)
    frames["sleep_0"] = sleep

    # Alert: brighter, magenta-hot, slightly enlarged (excited/working-hard).
    alert = ImageEnhance.Brightness(base).enhance(1.18)
    alert = ImageEnhance.Contrast(alert).enhance(1.1)
    alert = tint(alert, MAGENTA, 0.22)
    frames["alert_0"] = alert
    alert1 = scale_to_height(alert, round(TARGET_H * 1.04))
    frames["alert_1"] = alert1

    # Peace / point / wave: reuse the base pose (it is already a peace sign).
    frames["peace_0"] = ImageEnhance.Brightness(base).enhance(1.06)
    frames["point_0"] = base
    frames["wave_0"] = rotate(base, -6)
    frames["wave_1"] = rotate(base, 6)

    # Notify: perk up (brighten + violet halo boost).
    notify = ImageEnhance.Brightness(base).enhance(1.12)
    notify = tint(notify, VIOLET, 0.12)
    frames["notify_0"] = notify

    manifest = {
        "name": "nyxus-alien-placeholder",
        "note": "PLACEHOLDER frames derived from nyxus-emblem-header.png. "
        "Replace PNGs (same names) or edit this manifest with polished art.",
        "sprite_height": TARGET_H,
        "default_facing": "right",
        "states": {
            "idle":   {"frames": ["idle_0", "idle_1"], "fps": 2, "loop": True},
            "walk":   {"frames": ["walk_0", "walk_1"], "fps": 6, "loop": True},
            "sleep":  {"frames": ["sleep_0"], "fps": 1, "loop": True},
            "alert":  {"frames": ["alert_0", "alert_1"], "fps": 8, "loop": True},
            "notify": {"frames": ["notify_0", "idle_0"], "fps": 4, "loop": True},
            "peace":  {"frames": ["peace_0"], "fps": 2, "loop": False},
            "point":  {"frames": ["point_0"], "fps": 2, "loop": False},
            "wave":   {"frames": ["wave_0", "wave_1"], "fps": 5, "loop": False},
        },
    }

    sizes = {}
    for name, img in frames.items():
        p = out / f"{name}.png"
        img.save(p)
        sizes[name] = img.size
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"wrote {len(frames)} frames -> {out}")
    for name in sorted(frames):
        print(f"  {name}.png  {sizes[name][0]}x{sizes[name][1]}")
    print(f"  manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
