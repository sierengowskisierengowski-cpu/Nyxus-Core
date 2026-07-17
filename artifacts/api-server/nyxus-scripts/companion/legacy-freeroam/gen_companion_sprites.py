#!/usr/bin/env python3
"""Turn the generated green-screen alien-dude art into game-ready sprite frames.

The companion character is a single, consistent identity rendered once per pose
(full-body grey alien street dude — NYXUS UFO snapback, graffiti hoodie, ripped
jeans, gold chain, chunky sneakers) in the urban/cosmic Nyxus style. Each pose
is generated on a flat chroma-key GREEN background (see assets/source/*.png).

This script:
  1. keys the green backdrop to transparent (with edge feather + green despill),
  2. auto-crops each pose to its silhouette,
  3. scales EVERY pose by ONE global factor (calibrated on the standing poses so
     a crouch stays short and a jump stays a jump — no per-frame height stretch),
  4. places each pose on a UNIFORM canvas anchored by the FOOT centroid + ground
     baseline, so the character never pops/jitters/rescales between frames,
  5. writes assets/frames/<pose>.png + manifest.json (the engine's real contract).

The engine (companion.py) adds the *motion* — sub-pixel eased tweening, velocity
-synced walk/run, gravity-arc jumps, squash/stretch breathing, lean, a moving
contact shadow, and cross-fades between poses — so a handful of clean, perfectly
-anchored key poses reads as a fully rigged, "alive" 3D-ish character.

Usage:
    python3 gen_companion_sprites.py [--src DIR] [--out DIR] [--stand-px N]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
DEFAULT_SRC = HERE / "assets" / "source"
DEFAULT_OUT = HERE / "assets" / "frames"

# Every pose we key out of assets/source/. Order is cosmetic.
POSES = [
    "idle", "walk_a", "walk_b", "run", "jump",
    "crouch", "point", "wave", "peace", "laugh", "sit",
]

# Poses used to calibrate the global scale (pure upright stances, no overhead
# arm / no crouch), so the on-screen body size is consistent everywhere.
CALIBRATION = ["idle", "walk_a", "walk_b"]

# Target standing body height in px for the calibration poses.
DEFAULT_STAND_PX = 208


def key_green(img: Image.Image) -> Image.Image:
    """Chroma-key a flat green background to alpha, feather + despill edges."""
    rgb = np.asarray(img.convert("RGB")).astype(np.int16)
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    max_rb = np.maximum(r, b)
    greenness = g - max_rb  # high on the backdrop, <=0 on the character

    # Alpha ramp: greenness <= lo -> opaque, >= hi -> transparent, linear between.
    lo, hi = 18.0, 78.0
    alpha = np.clip((hi - greenness) / (hi - lo), 0.0, 1.0)
    alpha = (alpha * 255.0).astype(np.uint8)

    # Green-spill suppression: pull the green channel back down to max(r,b) on
    # any pixel that still leans green (kills the bright fringe halo).
    spill = greenness > 0
    g_fixed = np.where(spill, max_rb, g).astype(np.uint8)
    out = np.dstack([
        r.astype(np.uint8),
        g_fixed,
        b.astype(np.uint8),
        alpha,
    ])
    im = Image.fromarray(out, "RGBA")

    # Erode 1px to shave any residual key line, then a hair of blur for a soft
    # anti-aliased edge.
    a = im.getchannel("A")
    a = a.filter(ImageFilter.MinFilter(3))
    a = a.filter(ImageFilter.GaussianBlur(0.6))
    # Hard-zero the long transparent tail so autocrop is tight.
    a = a.point(lambda v: 0 if v < 12 else v)
    im.putalpha(a)
    return im


def largest_blob(im: Image.Image) -> Image.Image:
    """Keep only the largest opaque region (drop stray keyed specks)."""
    a = np.asarray(im.getchannel("A"))
    mask = a > 24
    if not mask.any():
        return im
    # 4-connected labelling via iterative propagation on a coarse grid is heavy;
    # a cheap row/col span heuristic is enough here since the character is one
    # big blob — just trim isolated pixels by an opening.
    from PIL import ImageChops  # local import; only used here
    opened = im.getchannel("A").filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MaxFilter(3))
    im = im.copy()
    im.putalpha(ImageChops.multiply(im.getchannel("A"), opened.point(lambda v: 255 if v > 24 else 0)))
    return im


def cutout(im: Image.Image):
    """Return (tight_rgba, bbox) cropped to the alpha silhouette."""
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return im, (0, 0, im.width, im.height)
    return im.crop(bbox), bbox


def foot_anchor_x(im: Image.Image) -> float:
    """Alpha-weighted x-centroid of the bottom band == where the feet plant."""
    a = np.asarray(im.getchannel("A")).astype(np.float32)
    h, w = a.shape
    band = max(6, int(round(h * 0.07)))
    strip = a[h - band:h, :]
    col = strip.sum(axis=0)
    total = col.sum()
    if total <= 0:
        return w / 2.0
    xs = np.arange(w, dtype=np.float32)
    return float((xs * col).sum() / total)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default=str(DEFAULT_SRC))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--stand-px", type=int, default=DEFAULT_STAND_PX)
    args = ap.parse_args()

    src = Path(args.src)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    # --- Pass 1: key + cutout + measure --------------------------------------
    cut: dict[str, Image.Image] = {}
    heights: dict[str, int] = {}
    for pose in POSES:
        p = src / f"{pose}.png"
        if not p.exists():
            print(f"  ! missing source: {p}")
            continue
        keyed = key_green(Image.open(p))
        keyed = largest_blob(keyed)
        tight, _ = cutout(keyed)
        cut[pose] = tight
        heights[pose] = tight.height

    if not cut:
        print("no source poses found; nothing to do")
        return 1

    cal = [heights[p] for p in CALIBRATION if p in heights] or list(heights.values())
    stand_h = float(np.median(cal))
    scale = args.stand_px / stand_h
    print(f"calibration height={stand_h:.0f}px  global scale={scale:.4f}")

    # Scale every cutout by the SAME factor.
    scaled: dict[str, Image.Image] = {}
    anchors: dict[str, tuple[float, int]] = {}  # pose -> (foot_x, height)
    for pose, im in cut.items():
        nw = max(1, int(round(im.width * scale)))
        nh = max(1, int(round(im.height * scale)))
        s = im.resize((nw, nh), Image.LANCZOS)
        scaled[pose] = s
        anchors[pose] = (foot_anchor_x(s), nh)

    # --- Pass 2: derive a uniform canvas that fits every pose ----------------
    pad_x, pad_top, pad_bottom = 14, 16, 10
    half_w = 0
    top_ext = 0
    for pose, im in scaled.items():
        fx, nh = anchors[pose]
        half_w = max(half_w, fx, im.width - fx)
        top_ext = max(top_ext, nh)  # foot at baseline -> whole height is above
    canvas_w = int(round(half_w * 2 + pad_x * 2))
    canvas_h = int(round(top_ext + pad_top + pad_bottom))
    # Even dimensions render crisper.
    canvas_w += canvas_w % 2
    canvas_h += canvas_h % 2
    baseline_y = canvas_h - pad_bottom
    print(f"canvas {canvas_w}x{canvas_h}  baseline_y={baseline_y}")

    # --- Pass 3: composite each pose foot-anchored to the baseline -----------
    sizes = {}
    for pose, im in scaled.items():
        fx, nh = anchors[pose]
        canvas = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
        px = int(round(canvas_w / 2 - fx))
        py = int(round(baseline_y - nh))
        canvas.alpha_composite(im, (px, py))
        canvas.save(out / f"{pose}.png")
        sizes[pose] = (canvas_w, canvas_h)

    def st(frames, fps, loop=True):
        return {"frames": frames, "fps": fps, "loop": loop}

    manifest = {
        "name": "nyxus-alien-dude",
        "note": "Full-body Nyxus alien street dude. Key poses keyed from "
                "assets/source/*.png by gen_companion_sprites.py; the engine "
                "adds tweening/squash/lean/shadow/cross-fade for rigged motion.",
        "sprite_width": canvas_w,
        "sprite_height": canvas_h,
        "baseline_y": baseline_y,
        "default_facing": "right",
        "states": {
            # Locomotion cycles advance from DISTANCE travelled (engine-driven),
            # not wall-clock fps, so they never flail. The passing "idle" frame
            # between opposing strides gives a 4-count walk.
            "idle":   st(["idle"], 2),
            "walk":   st(["walk_a", "idle", "walk_b", "idle"], 6),
            "run":    st(["run", "walk_a", "run", "walk_b"], 11),
            # Every gesture is a SINGLE held pose — the engine adds life via a
            # gentle breathing/squash bob. No 2-frame toggles (those read as
            # frantic arm-flapping).
            "jump":   st(["jump"], 1, loop=False),
            "crouch": st(["crouch"], 1, loop=False),
            "wave":   st(["wave"], 1, loop=False),
            "peace":  st(["peace"], 1, loop=False),
            "laugh":  st(["laugh"], 1, loop=False),
            "sit":    st(["sit"], 1, loop=True),
            "sleep":  st(["sit"], 1, loop=True),
            # Reactions (point pose retired per design): peace-sign a
            # notification, throw arms up (jump pose) on a critical alert.
            "notify": st(["peace"], 1, loop=False),
            "alert":  st(["jump"], 1, loop=False),
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))

    print(f"wrote {len(scaled)} frames -> {out}")
    for pose in sorted(sizes):
        print(f"  {pose}.png  {sizes[pose][0]}x{sizes[pose][1]}")
    print("  manifest.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
