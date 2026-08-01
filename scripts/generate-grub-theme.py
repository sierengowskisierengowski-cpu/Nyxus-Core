#!/usr/bin/env python3
"""
NYXUS GRUB theme pixmap generator.

Writes the complete pixmap set for BOTH GRUB themes this repo ships:

  iso-builder/nyx-profile/grub/themes/nyxus/                  <- live ISO menu
  iso-builder/nyx-profile/airootfs/usr/share/grub/themes/nyxus <- installed system

GRUB's styled boxes are NINE-SLICE. A box declared as `foo_*.png` makes GRUB
look for foo_c/foo_n/foo_s/foo_e/foo_w/foo_nw/foo_ne/foo_sw/foo_se.png; every
slice that is absent is simply not drawn, so a partial set renders as a broken
frame with no error anywhere. The live-ISO theme shipped only c/e/w and pointed
`terminal-box` at the selection bar's prefix, which is why the UEFI menu drew
nothing recognisable. Both sets are emitted here in full, every time.

Colours are ALIEN NEON canon (see docs/THEME.md). The previous revision of this
script emitted an old violet and an old cyan, both of which are on the
FORBIDDEN list in artifacts/api-server/nyxus-scripts/nyxus_palette.py.

PIL is optional: the flat slices are written by a small built-in PNG encoder so
any host can regenerate them. The 1920x1080 background needs PIL; without it the
committed background.png is left untouched.

Reproducible: run from anywhere with `python3 scripts/generate-grub-theme.py`.
Idempotent: overwrites existing files.

(c) 2026 JOSEPH A. SIERENGOWSKI - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import math
import struct
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DESTS = [
    ROOT / "iso-builder/nyx-profile/grub/themes/nyxus",
    ROOT / "iso-builder/nyx-profile/airootfs/usr/share/grub/themes/nyxus",
]

# ALIEN NEON canon -- keep in lockstep with nyxus_palette.py.
VIOLET = (0x7D, 0x3D, 0xFF)   # #7d3dff  ACCENT_PRIMARY
MAGENTA = (0xFF, 0x2D, 0xAD)  # #ff2dad  ACCENT_SECONDARY
VOID = (0x05, 0x06, 0x0A)     # #05060a  VOID
TEXT = (0xEE, 0xF2, 0xFA)     # #eef2fa  WHITE_OFF
PANEL = (0x0A, 0x0D, 0x14)    # derived panel elevation

SELECT_H = 44   # must match item_height in theme.txt
CAP_W = 8
EDGE = 4

# The nine slices GRUB looks for behind a `prefix_*.png` box declaration.
SLICES = ("c", "n", "s", "e", "w", "nw", "ne", "sw", "se")


def write_png(path: Path, width: int, height: int, pixels) -> None:
    """Write an 8-bit RGBA PNG. `pixels(x, y)` returns an (r, g, b, a) tuple."""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (None)
        for x in range(width):
            raw.extend(pixels(x, y))

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    path.write_bytes(png)


def selection_box(dest: Path) -> None:
    """Violet frosted highlight behind the selected menu entry."""

    def body_alpha(y: int, height: int) -> int:
        # Soft top/bottom falloff so the bar reads as a glow, not a slab.
        edge = min(y, height - 1 - y)
        return 210 if edge > 3 else 70 + edge * 35

    def rim(x: int, y: int, w: int, h: int, horiz: bool) -> tuple:
        # Bright 1px rim on the outer edge, fading into the body.
        edge = (x if horiz else y)
        outer = edge == 0
        colour = MAGENTA if outer else VIOLET
        alpha = 235 if outer else body_alpha(y if horiz else x, h if horiz else w)
        return (*colour, alpha)

    write_png(
        dest / "select_c.png", 1, SELECT_H,
        lambda x, y: (*VIOLET, body_alpha(y, SELECT_H)),
    )
    for name, flip in (("select_w.png", False), ("select_e.png", True)):
        write_png(
            dest / name, CAP_W, SELECT_H,
            lambda x, y, flip=flip: (
                *VIOLET,
                int(body_alpha(y, SELECT_H) * ((CAP_W - x) if flip else (x + 1)) / CAP_W),
            ),
        )
    for name in ("select_n.png", "select_s.png"):
        write_png(dest / name, 1, EDGE, lambda x, y: (*MAGENTA, 120))
    for name in ("select_nw.png", "select_ne.png", "select_sw.png", "select_se.png"):
        write_png(dest / name, CAP_W, EDGE, lambda x, y: (*MAGENTA, 90))


def terminal_box(dest: Path) -> None:
    """Dark frosted panel behind GRUB's command line / edit view."""
    write_png(dest / "terminal_box_c.png", 1, 1, lambda x, y: (*PANEL, 238))
    for name, (w, h) in (
        ("terminal_box_n.png", (1, EDGE)),
        ("terminal_box_s.png", (1, EDGE)),
        ("terminal_box_e.png", (EDGE, 1)),
        ("terminal_box_w.png", (EDGE, 1)),
    ):
        write_png(dest / name, w, h, lambda x, y: (*VIOLET, 200))
    for name in ("terminal_box_nw.png", "terminal_box_ne.png",
                 "terminal_box_sw.png", "terminal_box_se.png"):
        write_png(dest / name, EDGE, EDGE, lambda x, y: (*VIOLET, 200))


def progress_box(dest: Path) -> None:
    """Countdown bar: dim violet trough, magenta fill."""
    write_png(dest / "progress_trough_c.png", 1, 1, lambda x, y: (*VIOLET, 60))
    for name, (w, h) in (
        ("progress_trough_n.png", (1, 1)),
        ("progress_trough_s.png", (1, 1)),
        ("progress_trough_e.png", (1, 1)),
        ("progress_trough_w.png", (1, 1)),
    ):
        write_png(dest / name, w, h, lambda x, y: (*VIOLET, 90))
    for name in ("progress_trough_nw.png", "progress_trough_ne.png",
                 "progress_trough_sw.png", "progress_trough_se.png"):
        write_png(dest / name, 1, 1, lambda x, y: (*VIOLET, 90))

    write_png(dest / "progress_fill_c.png", 1, 1, lambda x, y: (*MAGENTA, 230))
    for suffix in ("n", "s", "e", "w", "nw", "ne", "sw", "se"):
        write_png(
            dest / f"progress_fill_{suffix}.png", 1, 1,
            lambda x, y: (*MAGENTA, 230),
        )


def background(dest: Path) -> bool:
    """1920x1080 void gradient + wordmark. Requires PIL; returns False if absent."""
    try:
        from PIL import Image, ImageDraw, ImageFilter, ImageFont
    except ImportError:
        return False

    W, H = 1920, 1080
    img = Image.new("RGB", (W, H), VOID)
    px = img.load()
    cx, cy = W * 0.5, H * 0.55
    max_d = math.hypot(cx, cy)
    for y in range(H):
        for x in range(0, W, 2):
            t = max(0.0, 1.0 - math.hypot(x - cx, y - cy) / max_d)
            r = int(VOID[0] + (VIOLET[0] - VOID[0]) * 0.18 * t)
            g = int(VOID[1] + (VIOLET[1] - VOID[1]) * 0.10 * t)
            b = int(VOID[2] + (VIOLET[2] - VOID[2]) * 0.30 * t)
            px[x, y] = (r, g, b)
            if x + 1 < W:
                px[x + 1, y] = (r, g, b)
    img = img.filter(ImageFilter.GaussianBlur(2))

    d = ImageDraw.Draw(img)

    def load(name: str, size: int):
        try:
            return ImageFont.truetype(f"/usr/share/fonts/TTF/{name}", size)
        except OSError:
            return ImageFont.load_default()

    font = load("DejaVuSans-Bold.ttf", 96)
    bbox = d.textbbox((0, 0), "NYXUS", font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    d.text(((W - tw) // 2, int(H * 0.12)), "NYXUS", font=font, fill=TEXT)

    sf = load("DejaVuSans.ttf", 22)
    sub = "ALIEN NEON  ·  KAGE RYU"
    sb = d.textbbox((0, 0), sub, font=sf)
    d.text(((W - (sb[2] - sb[0])) // 2, int(H * 0.12) + th + 12), sub,
           font=sf, fill=MAGENTA)

    img.save(dest / "background.png", optimize=True)
    return True


def main() -> int:
    wrote_bg = False
    for dest in DESTS:
        dest.mkdir(parents=True, exist_ok=True)
        selection_box(dest)
        terminal_box(dest)
        progress_box(dest)
        wrote_bg = background(dest) or wrote_bg
        print(f"[OK] pixmaps -> {dest.relative_to(ROOT)}")

    if not wrote_bg:
        print("[WARN] PIL not installed - background.png left as committed "
              "(install python-pillow to regenerate it)")

    # Fail loudly if any theme.txt still points at a box we did not emit.
    missing = 0
    for dest in DESTS:
        theme = dest / "theme.txt"
        if not theme.is_file():
            continue
        for line in theme.read_text(encoding="utf-8").splitlines():
            if "_*.png" not in line:
                continue
            prefix = line.split('"')[1].removesuffix("_*.png")
            for slice_ in SLICES:
                if not (dest / f"{prefix}_{slice_}.png").is_file():
                    print(f"[FAIL] {theme.relative_to(ROOT)} references "
                          f"{prefix}_*.png but {prefix}_{slice_}.png is missing")
                    missing += 1
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
