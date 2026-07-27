#!/usr/bin/env python3
"""Generate seamless swirling-paint GIFs for the NYXUS rail caps.

CSS gradients cannot swirl - they can only slide a straight edge around.
This renders an actual fluid-looking field: a smooth noise texture whose
coordinates are warped by a second noise field, with the warp driven by
sin/cos of the loop phase. Because the displacement is periodic in t, the
last frame flows back into the first, so the GIF loops with no visible cut.
"""
import sys, numpy as np
from PIL import Image

N = 84          # render size (caps draw at 42px; 2x keeps it crisp)
FRAMES = 30
OCT = (3, 6, 12)   # noise octaves (low-res grids, bilinearly upsampled)


def smooth_noise(res, rng):
    """Value noise: random on a coarse grid, bicubic-upsampled to NxN."""
    g = rng.random((res + 1, res + 1)).astype(np.float32)
    g[-1, :] = g[0, :]          # wrap so the field tiles
    g[:, -1] = g[:, 0]
    return np.asarray(
        Image.fromarray((g * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC),
        dtype=np.float32) / 255.0


def field(rng):
    out = np.zeros((N, N), np.float32)
    amp = 1.0
    tot = 0.0
    for res in OCT:
        out += amp * smooth_noise(res, rng)
        tot += amp
        amp *= 0.5
    return out / tot


def make(hex_lo, hex_hi, seed, path):
    rng = np.random.default_rng(seed)
    base = field(rng)                 # the "paint" pattern being pushed around
    wx, wy = field(rng), field(rng)   # the flow that pushes it

    ys, xs = np.mgrid[0:N, 0:N].astype(np.float32)
    lo = np.array([int(hex_lo[i:i + 2], 16) for i in (0, 2, 4)], np.float32)
    hi = np.array([int(hex_hi[i:i + 2], 16) for i in (0, 2, 4)], np.float32)

    frames = []
    for f in range(FRAMES):
        p = 2.0 * np.pi * f / FRAMES
        # periodic displacement -> perfect loop; the two noise fields give the
        # displacement spatial structure, which is what reads as *swirl*
        dx = 13.0 * np.sin(p + 6.28 * wx)
        dy = 13.0 * np.cos(p + 6.28 * wy)
        sx = np.clip(xs + dx, 0, N - 1).astype(np.int32)
        sy = np.clip(ys + dy, 0, N - 1).astype(np.int32)
        v = base[sy, sx]
        v = (v - v.min()) / max(float(v.max() - v.min()), 1e-6)
        v = np.clip(v * 1.35 - 0.16, 0, 1)          # punch up the contrast
        rgb = lo[None, None, :] + (hi - lo)[None, None, :] * v[:, :, None]
        frames.append(Image.fromarray(rgb.astype(np.uint8), "RGB"))

    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=70, loop=0, optimize=True)
    return path


if __name__ == "__main__":
    # hue name -> (dark paint, bright paint) taken from the accent already
    # resolved in eww.css so the caps keep the theme's colour mapping
    HUES = {
        "pink":     ("2a1150", "7d3dff"),
        "green":    ("50102f", "ff2dad"),
        "purple":   ("11400a", "39ff14"),
        "gold":     ("50290a", "ff8a1e"),
        "orange":   ("50290a", "ff8a1e"),
        "blue":     ("102a50", "4d9fff"),
        "cyan":     ("500f1c", "ff2d55"),
        "occupied": ("2a1150", "7d3dff"),
    }
    out = sys.argv[1]
    for i, (h, (a, b)) in enumerate(HUES.items()):
        make(a, b, 1000 + i, f"{out}/nyxus-liquid-{h}.gif")
        print("wrote", f"nyxus-liquid-{h}.gif")
