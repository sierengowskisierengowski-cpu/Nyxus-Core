#!/usr/bin/env python3
"""
NYXUS GRUB theme pixmap generator.

Emits all PNG assets referenced by airootfs/usr/share/grub/themes/nyxus/
theme.txt:

  background.png         - 1920x1080 deep-space gradient + faint wordmark
  select_c.png           - 1x36 horizontal stretch of the selection bar
  select_e.png/select_w.png - 4x36 selection-bar caps
  terminal_box_c.png     - 1x1 terminal background tile
  terminal_box_n/s/e/w   - 1x4 / 4x1 edges
  terminal_box_ne/nw/se/sw - 4x4 corners

Reproducible: run from repo root with `python3 scripts/generate-grub-theme.py`.
Idempotent: overwrites existing files.

(c) 2026 JOSEPH SIERENGOWSKI - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "iso-builder/nyx-profile/airootfs/usr/share/grub/themes/nyxus"
DEST.mkdir(parents=True, exist_ok=True)

PURPLE = (160, 107, 255)
CYAN   = (58, 216, 255)
BG     = (5, 5, 8)
PANEL  = (16, 14, 26)
EDGE   = (42, 42, 60)


def background() -> None:
    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), BG)
    px = img.load()
    cx, cy = W * 0.5, H * 0.55
    max_d = math.hypot(cx, cy)
    for y in range(H):
        for x in range(0, W, 2):
            d = math.hypot(x - cx, y - cy) / max_d
            t = max(0.0, 1.0 - d)
            r = int(BG[0] + (PURPLE[0] - BG[0]) * 0.18 * t)
            g = int(BG[1] + (PURPLE[1] - BG[1]) * 0.10 * t)
            b = int(BG[2] + (PURPLE[2] - BG[2]) * 0.30 * t)
            px[x, y]   = (r, g, b)
            if x + 1 < W:
                px[x + 1, y] = (r, g, b)
    img = img.filter(ImageFilter.GaussianBlur(2))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf", 96)
    except OSError:
        font = ImageFont.load_default()
    text = "NYXUS"
    bbox = d.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((W - tw) // 2, int(H * 0.12)), text,
           font=font, fill=(232, 237, 245))
    sub = "DARK MIRROR EDITION"
    try:
        sf = ImageFont.truetype(
            "/usr/share/fonts/TTF/DejaVuSans.ttf", 22)
    except OSError:
        sf = ImageFont.load_default()
    sb = d.textbbox((0, 0), sub, font=sf)
    sw = sb[2] - sb[0]
    d.text(((W - sw) // 2, int(H * 0.12) + th + 12), sub,
           font=sf, fill=CYAN)
    img.save(DEST / "background.png", optimize=True)


def select_bar() -> None:
    H = 36
    cx = Image.new("RGBA", (1, H), (0, 0, 0, 0))
    for y in range(H):
        edge = min(y, H - 1 - y)
        a = 200 if edge > 2 else 60 + edge * 35
        cx.putpixel((0, y), (PURPLE[0], PURPLE[1], PURPLE[2], a))
    cx.save(DEST / "select_c.png")
    for name in ("select_e.png", "select_w.png"):
        cap = Image.new("RGBA", (4, H), (0, 0, 0, 0))
        for x in range(4):
            for y in range(H):
                edge_y = min(y, H - 1 - y)
                edge_x = x if name.endswith("w.png") else (3 - x)
                fade = max(0, edge_y - 2) * 0.18
                a = int(min(200, 60 + fade * 100) * (edge_x + 1) / 4)
                cap.putpixel(
                    (x, y),
                    (PURPLE[0], PURPLE[1], PURPLE[2], a))
        cap.save(DEST / name)


def terminal_box() -> None:
    Image.new("RGBA", (1, 1), PANEL + (235,)).save(
        DEST / "terminal_box_c.png")
    for name, size in (
        ("terminal_box_n.png", (1, 4)),
        ("terminal_box_s.png", (1, 4)),
        ("terminal_box_e.png", (4, 1)),
        ("terminal_box_w.png", (4, 1)),
    ):
        Image.new("RGBA", size, EDGE + (235,)).save(DEST / name)
    for name in ("terminal_box_ne.png", "terminal_box_nw.png",
                 "terminal_box_se.png", "terminal_box_sw.png"):
        Image.new("RGBA", (4, 4), EDGE + (235,)).save(DEST / name)


def main() -> None:
    background()
    select_bar()
    terminal_box()
    print(f"[OK] wrote GRUB theme pixmaps to {DEST}")


if __name__ == "__main__":
    main()
