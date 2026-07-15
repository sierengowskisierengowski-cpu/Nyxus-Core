#!/usr/bin/env python3
"""Cut the PILOTED-saucer companion alien from the existing Nyxus wallpaper art.

The piloted companion is the *actual* graffiti alien dude the user loves from
``nyxus-wall-alien-hero.png`` — the grey alien in the NYXUS snapback throwing a
peace sign against the cosmic galaxy. He's posted up in the center UFO-saucer
clock, so we only need a head-and-shoulders BUST plus his raised peace hand.

Matting a purple alien off a purple galaxy defeats a global color model, so we
use two targeted passes:

  * BUST  — an OpenCV GrabCut with a rectangle around the compact head + cap +
    hoodie (which separates cleanly from the bordering galaxy).
  * HAND  — a hand-authored polygon over the raised peace-sign hand, refined by
    a LOCAL GrabCut seeded from that polygon, so we keep the real wallpaper
    pixels with a clean silhouette (and the notch between the V-fingers).

The two alphas are unioned in the shared wallpaper coordinate space (so the hand
sits exactly where it belongs relative to the head), giving:

  * chill.png — bust only (his kicked-back idle, hand down/out of frame)
  * peace.png — bust + peace hand (his reaction)

The engine (companion.py) drives everything else — breathing, a peace "pop",
wave/cheer/alert variations, tints — so two clean real-art frames cover the
whole repertoire.

Usage:  python3 gen_piloted_sprites.py [--source PATH] [--out DIR]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageFilter

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCE = (HERE.parent / "hypr-walls" / "nyxus-wall-alien-hero.png").resolve()
DEFAULT_OUT = HERE / "assets" / "frames"

# Region of the wallpaper holding the alien's upper body + raised hand.
CROP = (150, 180, 565, 600)          # left, top, right, bottom  -> 415x420

# Sub-rect (crop-local) around the compact head+cap+hoodie for the bust GrabCut.
BUST_RECT = (150, 92, 220, 328)      # x, y, w, h

# Peace-hand silhouette (crop-local), authored TIGHT from the art so the V-notch
# between the two fingers stays open and little galaxy is captured. Used directly
# as alpha (with a bright-galaxy carve), not via a leaky color model.
HAND_FINGER_L = [(50, 175), (67, 174), (71, 248), (54, 250)]
HAND_FINGER_R = [(83, 185), (102, 187), (95, 250), (78, 248)]
HAND_FIST = [(48, 244), (126, 244), (128, 320), (40, 322)]
HAND_WRIST = [(34, 315), (120, 318), (104, 384), (20, 382)]
# Galaxy directly behind the hand is much brighter than the grey fingers; drop
# any pixel inside the hand polygon brighter than this to kill the halo.
HAND_MAX_LUMA = 168


def _grabcut_rect(bgr, rect, iters=7):
    m = np.zeros(bgr.shape[:2], np.uint8)
    cv2.grabCut(bgr, m, rect, np.zeros((1, 65), np.float64),
                np.zeros((1, 65), np.float64), iters, cv2.GC_INIT_WITH_RECT)
    return np.where((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)


def _grabcut_mask(bgr, pr_fg, sure_fg, iters=6):
    """Local refine: pr_fg polygon = probable FG, its erosion = sure FG."""
    h, w = bgr.shape[:2]
    m = np.full((h, w), cv2.GC_PR_BGD, np.uint8)
    m[pr_fg > 0] = cv2.GC_PR_FGD
    m[sure_fg > 0] = cv2.GC_FGD
    if not (m == cv2.GC_PR_FGD).any() and not (m == cv2.GC_FGD).any():
        return np.zeros((h, w), np.uint8)
    cv2.grabCut(bgr, m, None, np.zeros((1, 65), np.float64),
                np.zeros((1, 65), np.float64), iters, cv2.GC_INIT_WITH_MASK)
    return np.where((m == cv2.GC_FGD) | (m == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)


def _poly_mask(shape, polys):
    m = np.zeros(shape, np.uint8)
    for p in polys:
        cv2.fillPoly(m, [np.array(p, np.int32)], 255)
    return m


def _largest(mask):
    n, lab, stats, _ = cv2.connectedComponentsWithStats(mask, 8)
    if n <= 1:
        return mask
    big = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.where(lab == big, 255, 0).astype(np.uint8)


def _clean(mask, close=5, open_=3, blur=0.9):
    if close:
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((close, close), np.uint8))
    if open_:
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((open_, open_), np.uint8))
    if blur:
        mask = cv2.GaussianBlur(mask, (0, 0), blur)
    return mask


def _rgba(bgr, alpha):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    return Image.fromarray(np.dstack([rgb, alpha]), "RGBA")


def _autocrop(im, pad=4):
    bbox = im.getchannel("A").getbbox()
    if not bbox:
        return im
    l, t, r, b = bbox
    l = max(0, l - pad); t = max(0, t - pad)
    r = min(im.width, r + pad); b = min(im.height, b + pad)
    return im.crop((l, t, r, b))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=str(DEFAULT_SOURCE))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    src = Path(args.source)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if not src.exists():
        print("source not found:", src)
        return 1

    full = cv2.imread(str(src))
    x0, y0, x1, y1 = CROP
    crop = full[y0:y1, x0:x1].copy()
    h, w = crop.shape[:2]

    # --- BUST (head + cap + hoodie) ---------------------------------------
    bust = _clean(_largest(_grabcut_rect(crop, BUST_RECT)))

    # --- PEACE HAND (tight authored polygon, bright-galaxy carved) --------
    hand_poly = _poly_mask((h, w), [HAND_FINGER_L, HAND_FINGER_R, HAND_FIST, HAND_WRIST])
    luma = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    # inside the polygon, drop the bright galaxy core (keeps the grey fingers)
    hand = hand_poly.copy()
    hand[(hand_poly > 0) & (luma > HAND_MAX_LUMA)] = 0
    hand = _largest(hand)
    hand = _clean(hand, close=5, open_=0, blur=0.8)

    chill_alpha = bust
    peace_alpha = np.maximum(bust, hand)

    chill = _autocrop(_rgba(crop, chill_alpha))
    peace = _autocrop(_rgba(crop, peace_alpha))

    # Normalize both onto a shared canvas anchored by the HEAD so the bust never
    # shifts between chill<->peace (peace just adds the hand to the left).
    cw = max(chill.width, peace.width)
    ch = max(chill.height, peace.height)
    cw += cw % 2; ch += ch % 2

    def place(im):
        canvas = Image.new("RGBA", (cw, ch), (0, 0, 0, 0))
        # anchor bottom-center-right (head sits right side; hand extends left)
        px = cw - im.width
        py = ch - im.height
        canvas.alpha_composite(im, (px, py))
        return canvas

    chill_c = place(chill)
    peace_c = place(peace)
    chill_c.save(out / "chill.png")
    peace_c.save(out / "peace.png")

    baseline_y = ch - 4
    manifest = {
        "name": "nyxus-alien-piloted",
        "note": "Piloted-saucer companion cut from nyxus-wall-alien-hero.png "
                "(the wallpaper peace-sign alien). chill=bust, peace=bust+hand; "
                "the engine drives wave/cheer/alert as motion/tint variations.",
        "sprite_width": cw,
        "sprite_height": ch,
        "baseline_y": baseline_y,
        "default_facing": "left",
        "states": {
            "chill":  {"frames": ["chill"], "fps": 1, "loop": True},
            "idle":   {"frames": ["chill"], "fps": 1, "loop": True},
            "peace":  {"frames": ["peace"], "fps": 1, "loop": False},
            "wave":   {"frames": ["peace"], "fps": 1, "loop": False},
            "cheer":  {"frames": ["peace"], "fps": 1, "loop": False},
            "alert":  {"frames": ["peace"], "fps": 1, "loop": False},
            "notify": {"frames": ["peace"], "fps": 1, "loop": False},
        },
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"wrote chill.png + peace.png ({cw}x{ch}) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
