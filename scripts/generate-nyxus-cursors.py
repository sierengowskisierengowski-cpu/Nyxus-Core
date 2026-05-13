#!/usr/bin/env python3
"""Generate the NYXUS Aurora cursor theme.

Format: hyprcursor (SVG-native).
  <theme_root>/manifest.hl
  <theme_root>/hyprcursors/<shape>/meta.hl
  <theme_root>/hyprcursors/<shape>/<shape>.svg

For non-Hypr toolkits an XCursor index.theme inherits 'Adwaita' as a
fallback so legacy XWayland apps still get a sane pointer.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THEME = REPO / "iso-builder/nyx-profile/airootfs/usr/share/icons/NYXUS-Aurora"
CUR_DIR = THEME / "hyprcursors"

# DARK MIRROR palette
PURPLE = "#a06bff"
CYAN = "#3ad8ff"
INK = "#0a0d14"
BONE = "#e8edf5"
GLOW = "#3ad8ff"

CANVAS = 64  # all SVGs use 64x64 viewBox; hotspots are normalized 0..1


def svg(body: str, vb: int = CANVAS) -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{vb}" height="{vb}" '
        f'viewBox="0 0 {vb} {vb}">\n'
        f'<defs>'
        f'<filter id="glow" x="-30%" y="-30%" width="160%" height="160%">'
        f'<feGaussianBlur stdDeviation="1.4"/></filter>'
        f'</defs>\n{body}\n</svg>\n'
    )


def cur_default() -> str:
    # Classic arrow with cyan glow edge
    body = (
        f'<path d="M6 4 L6 44 L18 36 L24 50 L30 47 L24 33 L40 33 Z" '
        f'fill="{CYAN}" filter="url(#glow)" opacity="0.55"/>'
        f'<path d="M6 4 L6 44 L18 36 L24 50 L30 47 L24 33 L40 33 Z" '
        f'fill="{INK}" stroke="{BONE}" stroke-width="1.2"/>'
        f'<path d="M8 8 L8 39 L17 32 L21 41 L24 40 L20 31 L33 31 Z" '
        f'fill="{BONE}" opacity="0.85"/>'
    )
    return svg(body)


def cur_pointer() -> str:
    # Hand pointer
    body = (
        f'<g stroke="{BONE}" stroke-width="1.2" stroke-linejoin="round">'
        f'<path d="M22 10 V32 L19 28 L15 30 L20 42 Q22 50 30 50 H40 Q46 50 46 44 V28 Q46 25 43 25 Q40 25 40 28 V24 Q40 21 37 21 Q34 21 34 24 V22 Q34 19 31 19 Q28 19 28 22 V12 Q28 9 25 9 Q22 9 22 10 Z" '
        f'fill="{INK}"/>'
        f'</g>'
        f'<path d="M28 16 V28 M34 22 V28 M40 24 V28" '
        f'stroke="{CYAN}" stroke-width="0.8" opacity="0.6"/>'
    )
    return svg(body)


def cur_text() -> str:
    body = (
        f'<g stroke="{BONE}" stroke-width="2" fill="none" stroke-linecap="round">'
        f'<line x1="32" y1="10" x2="32" y2="54"/>'
        f'<line x1="26" y1="10" x2="38" y2="10"/>'
        f'<line x1="26" y1="54" x2="38" y2="54"/>'
        f'</g>'
        f'<g stroke="{INK}" stroke-width="0.8" fill="none" stroke-linecap="round" opacity="0.7">'
        f'<line x1="32" y1="10" x2="32" y2="54"/>'
        f'</g>'
    )
    return svg(body)


def cur_crosshair() -> str:
    body = (
        f'<g stroke="{BONE}" stroke-width="1.5" stroke-linecap="round">'
        f'<line x1="32" y1="6"  x2="32" y2="24"/>'
        f'<line x1="32" y1="40" x2="32" y2="58"/>'
        f'<line x1="6"  y1="32" x2="24" y2="32"/>'
        f'<line x1="40" y1="32" x2="58" y2="32"/>'
        f'</g>'
        f'<circle cx="32" cy="32" r="3" fill="{CYAN}" stroke="{BONE}" stroke-width="1"/>'
    )
    return svg(body)


def cur_wait_frame(angle: float) -> str:
    rays = []
    for i in range(8):
        a = (i * 45 + angle) * math.pi / 180
        x1 = 32 + math.cos(a) * 12
        y1 = 32 + math.sin(a) * 12
        x2 = 32 + math.cos(a) * 22
        y2 = 32 + math.sin(a) * 22
        op = 0.2 + 0.10 * i
        rays.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="{CYAN}" stroke-width="3" stroke-linecap="round" opacity="{op:.2f}"/>'
        )
    return svg(
        f'<circle cx="32" cy="32" r="22" fill="none" stroke="{INK}" opacity="0.5"/>' + "".join(rays)
    )


def cur_help() -> str:
    arrow = (
        f'<path d="M6 4 L6 44 L18 36 L24 50 L30 47 L24 33 L40 33 Z" '
        f'fill="{INK}" stroke="{BONE}" stroke-width="1.2"/>'
    )
    badge = (
        f'<circle cx="48" cy="46" r="11" fill="{PURPLE}" stroke="{BONE}" stroke-width="1.2"/>'
        f'<text x="48" y="51" text-anchor="middle" font-family="Inter, sans-serif" '
        f'font-size="14" font-weight="700" fill="{BONE}">?</text>'
    )
    return svg(arrow + badge)


def cur_not_allowed() -> str:
    body = (
        f'<circle cx="32" cy="32" r="22" fill="none" stroke="#ff4d6b" stroke-width="5"/>'
        f'<line x1="16" y1="16" x2="48" y2="48" stroke="#ff4d6b" stroke-width="5" stroke-linecap="round"/>'
    )
    return svg(body)


def cur_progress(angle: float) -> str:
    arrow = (
        f'<path d="M6 4 L6 44 L18 36 L24 50 L30 47 L24 33 L40 33 Z" '
        f'fill="{INK}" stroke="{BONE}" stroke-width="1.2"/>'
    )
    spin = ""
    for i in range(6):
        a = (i * 60 + angle) * math.pi / 180
        x = 50 + math.cos(a) * 8
        y = 50 + math.sin(a) * 8
        op = 0.2 + 0.13 * i
        spin += f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="{CYAN}" opacity="{op:.2f}"/>'
    return svg(arrow + spin)


def cur_resize(direction: str) -> str:
    # direction in: ns, ew, nesw, nwse, all
    arrows = {
        "ns": '<path d="M32 10 L24 22 L40 22 Z M32 54 L24 42 L40 42 Z M32 22 V42" stroke="{b}" fill="{b}"/>',
        "ew": '<path d="M10 32 L22 24 L22 40 Z M54 32 L42 24 L42 40 Z M22 32 H42" stroke="{b}" fill="{b}"/>',
        "nesw": '<path d="M14 50 L14 38 L26 50 Z M50 14 L50 26 L38 14 Z M22 42 L42 22" stroke="{b}" fill="{b}" stroke-width="2"/>',
        "nwse": '<path d="M14 14 L26 14 L14 26 Z M50 50 L38 50 L50 38 Z M22 22 L42 42" stroke="{b}" fill="{b}" stroke-width="2"/>',
        "all": '<path d="M32 8 L24 18 L40 18 Z M32 56 L24 46 L40 46 Z M8 32 L18 24 L18 40 Z M56 32 L46 24 L46 40 Z M32 18 V46 M18 32 H46" stroke="{b}" fill="{b}" stroke-width="2"/>',
    }
    body = arrows[direction].format(b=BONE)
    return svg(body)


CURSORS: dict[str, dict] = {
    # shape: { hotspot=(x_norm,y_norm), aliases=[...], frames=[svg,...] or static }
    "left_ptr":          {"hotspot": (0.10, 0.06), "aliases": ["default", "arrow", "top_left_arrow"], "static": cur_default()},
    "pointer":           {"hotspot": (0.43, 0.18), "aliases": ["hand", "hand1", "hand2", "pointing_hand"], "static": cur_pointer()},
    "text":              {"hotspot": (0.50, 0.50), "aliases": ["xterm", "ibeam"], "static": cur_text()},
    "crosshair":         {"hotspot": (0.50, 0.50), "aliases": ["cross"], "static": cur_crosshair()},
    "help":              {"hotspot": (0.10, 0.06), "aliases": ["question_arrow", "whats_this"], "static": cur_help()},
    "not-allowed":       {"hotspot": (0.50, 0.50), "aliases": ["forbidden", "circle"], "static": cur_not_allowed()},
    "wait":              {"hotspot": (0.50, 0.50), "aliases": ["watch"], "frames": [(cur_wait_frame(a), 60) for a in range(0, 360, 30)]},
    "progress":          {"hotspot": (0.10, 0.06), "aliases": ["left_ptr_watch", "half-busy"], "frames": [(cur_progress(a), 80) for a in range(0, 360, 60)]},
    "ns-resize":         {"hotspot": (0.50, 0.50), "aliases": ["size_ver", "v_double_arrow", "double_arrow"], "static": cur_resize("ns")},
    "ew-resize":         {"hotspot": (0.50, 0.50), "aliases": ["size_hor", "h_double_arrow"], "static": cur_resize("ew")},
    "nesw-resize":       {"hotspot": (0.50, 0.50), "aliases": ["size_bdiag", "fd_double_arrow"], "static": cur_resize("nesw")},
    "nwse-resize":       {"hotspot": (0.50, 0.50), "aliases": ["size_fdiag", "bd_double_arrow"], "static": cur_resize("nwse")},
    "all-scroll":        {"hotspot": (0.50, 0.50), "aliases": ["fleur", "size_all", "move"], "static": cur_resize("all")},
}


def write_manifest() -> None:
    THEME.mkdir(parents=True, exist_ok=True)
    (THEME / "manifest.hl").write_text(
        'name = NYXUS Aurora\n'
        'description = NYXUS DARK MIRROR cursor theme — cyan-edged ink with purple accents\n'
        'version = 1.0\n'
        'cursors_directory = hyprcursors\n'
    )
    # XCursor fallback
    (THEME / "index.theme").write_text(
        '[Icon Theme]\n'
        'Name=NYXUS-Aurora\n'
        'Comment=NYXUS DARK MIRROR cursor theme\n'
        'Inherits=Adwaita\n'
    )


def write_cursors() -> int:
    count = 0
    for shape, spec in CURSORS.items():
        d = CUR_DIR / shape
        d.mkdir(parents=True, exist_ok=True)
        hx, hy = spec["hotspot"]
        meta_lines = [
            'resize_algorithm = bilinear',
            f'hotspot_x = {hx}',
            f'hotspot_y = {hy}',
        ]
        for alias in spec.get("aliases", []):
            meta_lines.append(f'define_override = {alias}')
        if "frames" in spec:
            for i, (frame_svg, delay) in enumerate(spec["frames"]):
                fname = f"{shape}_{i:02d}.svg"
                (d / fname).write_text(frame_svg)
                meta_lines.append(f'define_size = 0, {fname}, {delay}')
        else:
            fname = f"{shape}.svg"
            (d / fname).write_text(spec["static"])
            meta_lines.append(f'define_size = 0, {fname}')
        (d / "meta.hl").write_text("\n".join(meta_lines) + "\n")
        count += 1
    return count


def main() -> int:
    write_manifest()
    n = write_cursors()
    print(f"NYXUS Aurora cursor: wrote {n} shapes to {THEME}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
