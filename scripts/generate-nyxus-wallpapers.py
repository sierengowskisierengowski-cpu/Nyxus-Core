#!/usr/bin/env python3
"""Generate the NYXUS wallpaper pack (procedural SVGs).

Output: iso-builder/nyx-profile/airootfs/usr/share/backgrounds/nyxus/<slug>.svg
The studio picker (nyxus_wallpaper_studio.py) lists this directory.
swaybg renders SVG via gdk-pixbuf when gdk-pixbuf-loaders is installed.
"""
from __future__ import annotations
import math
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "iso-builder/nyx-profile/airootfs/usr/share/backgrounds/nyxus"
W, H = 3840, 2160  # 4K canvas


def shell(body: str, defs: str = "") -> str:
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice">\n'
        f'<defs>{defs}</defs>\n'
        f'{body}\n'
        f'</svg>\n'
    )


def w_void_vortex() -> str:
    defs = (
        '<radialGradient id="g" cx="50%" cy="50%" r="70%">'
        '<stop offset="0%" stop-color="#0d0820"/>'
        '<stop offset="55%" stop-color="#050308"/>'
        '<stop offset="100%" stop-color="#000000"/>'
        '</radialGradient>'
    )
    rings = ""
    for i in range(28):
        r = 80 + i * 90
        op = max(0.02, 0.22 - i * 0.007)
        rings += (
            f'<circle cx="{W//2}" cy="{H//2}" r="{r}" fill="none" '
            f'stroke="#a06bff" stroke-opacity="{op:.3f}" stroke-width="1.2"/>'
        )
    return shell(f'<rect width="{W}" height="{H}" fill="url(#g)"/>{rings}', defs)


def w_dark_mirror_grid() -> str:
    lines = []
    step = 120
    for x in range(0, W + 1, step):
        op = 0.06 + 0.10 * (1 - abs(x - W / 2) / (W / 2))
        lines.append(
            f'<line x1="{x}" y1="0" x2="{x}" y2="{H}" stroke="#3ad8ff" '
            f'stroke-opacity="{op:.3f}" stroke-width="1"/>'
        )
    for y in range(0, H + 1, step):
        op = 0.06 + 0.10 * (1 - abs(y - H / 2) / (H / 2))
        lines.append(
            f'<line x1="0" y1="{y}" x2="{W}" y2="{y}" stroke="#3ad8ff" '
            f'stroke-opacity="{op:.3f}" stroke-width="1"/>'
        )
    body = (
        f'<rect width="{W}" height="{H}" fill="#04070b"/>'
        + "".join(lines)
        + f'<circle cx="{W//2}" cy="{H//2}" r="6" fill="#3ad8ff"/>'
    )
    return shell(body)


def w_aurora_drift() -> str:
    defs = (
        '<radialGradient id="a" cx="20%" cy="30%" r="60%">'
        '<stop offset="0%" stop-color="#a06bff" stop-opacity="0.55"/>'
        '<stop offset="100%" stop-color="#000000" stop-opacity="0"/>'
        '</radialGradient>'
        '<radialGradient id="b" cx="80%" cy="70%" r="60%">'
        '<stop offset="0%" stop-color="#3ad8ff" stop-opacity="0.55"/>'
        '<stop offset="100%" stop-color="#000000" stop-opacity="0"/>'
        '</radialGradient>'
        '<radialGradient id="c" cx="50%" cy="50%" r="70%">'
        '<stop offset="0%" stop-color="#82ffd2" stop-opacity="0.18"/>'
        '<stop offset="100%" stop-color="#000000" stop-opacity="0"/>'
        '</radialGradient>'
    )
    body = (
        f'<rect width="{W}" height="{H}" fill="#02030a"/>'
        f'<rect width="{W}" height="{H}" fill="url(#a)"/>'
        f'<rect width="{W}" height="{H}" fill="url(#b)"/>'
        f'<rect width="{W}" height="{H}" fill="url(#c)"/>'
    )
    return shell(body, defs)


def w_phantom_mesh() -> str:
    pts = []
    rows, cols = 9, 16
    import random
    random.seed(1337)
    for r in range(rows):
        for c in range(cols):
            x = c * (W / (cols - 1))
            y = r * (H / (rows - 1))
            x += random.uniform(-30, 30)
            y += random.uniform(-30, 30)
            pts.append((x, y))
    edges = []
    for r in range(rows):
        for c in range(cols):
            i = r * cols + c
            x1, y1 = pts[i]
            if c < cols - 1:
                x2, y2 = pts[i + 1]
                edges.append((x1, y1, x2, y2))
            if r < rows - 1:
                x2, y2 = pts[i + cols]
                edges.append((x1, y1, x2, y2))
    body = [f'<rect width="{W}" height="{H}" fill="#03050a"/>']
    for x1, y1, x2, y2 in edges:
        body.append(
            f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" '
            f'stroke="#3ad8ff" stroke-opacity="0.10" stroke-width="0.8"/>'
        )
    for x, y in pts:
        body.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2" fill="#a06bff" fill-opacity="0.7"/>')
    return shell("".join(body))


def w_deep_static() -> str:
    import random
    random.seed(42)
    dots = []
    for _ in range(2400):
        x = random.uniform(0, W)
        y = random.uniform(0, H)
        op = random.uniform(0.05, 0.35)
        r = random.uniform(0.4, 1.6)
        dots.append(
            f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" fill="#e8edf5" fill-opacity="{op:.2f}"/>'
        )
    body = f'<rect width="{W}" height="{H}" fill="#02030a"/>' + "".join(dots)
    return shell(body)


def w_crimson_eclipse() -> str:
    defs = (
        '<radialGradient id="g" cx="50%" cy="55%" r="40%">'
        '<stop offset="0%" stop-color="#000000"/>'
        '<stop offset="70%" stop-color="#000000"/>'
        '<stop offset="100%" stop-color="#ff4d6b" stop-opacity="0.25"/>'
        '</radialGradient>'
    )
    body = (
        f'<rect width="{W}" height="{H}" fill="#070306"/>'
        f'<circle cx="{W//2}" cy="{int(H*0.55)}" r="{int(H*0.42)}" fill="url(#g)"/>'
        f'<circle cx="{W//2}" cy="{int(H*0.55)}" r="{int(H*0.42)}" fill="none" '
        f'stroke="#ff4d6b" stroke-opacity="0.55" stroke-width="3"/>'
    )
    return shell(body, defs)


def w_cyan_pulse() -> str:
    defs = (
        '<radialGradient id="g" cx="50%" cy="50%" r="60%">'
        '<stop offset="0%" stop-color="#3ad8ff" stop-opacity="0.32"/>'
        '<stop offset="50%" stop-color="#08111a" stop-opacity="0.85"/>'
        '<stop offset="100%" stop-color="#000000"/>'
        '</radialGradient>'
    )
    arcs = ""
    for i, r in enumerate([400, 700, 1050, 1400, 1750]):
        op = 0.28 - i * 0.05
        arcs += (
            f'<circle cx="{W//2}" cy="{H//2}" r="{r}" fill="none" '
            f'stroke="#3ad8ff" stroke-opacity="{op:.2f}" stroke-width="1.5"/>'
        )
    body = f'<rect width="{W}" height="{H}" fill="url(#g)"/>{arcs}'
    return shell(body, defs)


def w_carbon_weave() -> str:
    body = [f'<rect width="{W}" height="{H}" fill="#06080d"/>']
    s = 60
    for y in range(0, H, s):
        for x in range(0, W, s):
            shade = "#0a0d14" if (x // s + y // s) % 2 == 0 else "#0d1018"
            body.append(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" fill="{shade}"/>')
    body.append(
        f'<rect width="{W}" height="{H}" fill="none" stroke="#3ad8ff" '
        f'stroke-opacity="0.05" stroke-width="2"/>'
    )
    return shell("".join(body))


def w_nyxus_sigil() -> str:
    cx, cy = W // 2, H // 2
    rays = ""
    for i in range(24):
        a = i * (math.pi / 12)
        x2 = cx + math.cos(a) * 1500
        y2 = cy + math.sin(a) * 1500
        rays += (
            f'<line x1="{cx}" y1="{cy}" x2="{x2:.0f}" y2="{y2:.0f}" '
            f'stroke="#a06bff" stroke-opacity="0.06" stroke-width="1.5"/>'
        )
    body = (
        f'<rect width="{W}" height="{H}" fill="#02030a"/>{rays}'
        f'<circle cx="{cx}" cy="{cy}" r="320" fill="none" stroke="#a06bff" stroke-opacity="0.45" stroke-width="3"/>'
        f'<circle cx="{cx}" cy="{cy}" r="180" fill="none" stroke="#3ad8ff" stroke-opacity="0.55" stroke-width="2"/>'
        f'<circle cx="{cx}" cy="{cy}" r="60"  fill="#0a0d14" stroke="#e8edf5" stroke-opacity="0.65" stroke-width="2"/>'
        f'<text x="{cx}" y="{cy+18}" text-anchor="middle" font-family="Inter, sans-serif" '
        f'font-size="48" font-weight="700" fill="#e8edf5" letter-spacing="8">NYXUS</text>'
    )
    return shell(body)


WALLPAPERS = {
    "nyxus-void-vortex": ("Void Vortex", w_void_vortex),
    "nyxus-dark-mirror-grid": ("Dark Mirror Grid", w_dark_mirror_grid),
    "nyxus-aurora-drift": ("Aurora Drift", w_aurora_drift),
    "nyxus-phantom-mesh": ("Phantom Mesh", w_phantom_mesh),
    "nyxus-deep-static": ("Deep Static", w_deep_static),
    "nyxus-crimson-eclipse": ("Crimson Eclipse", w_crimson_eclipse),
    "nyxus-cyan-pulse": ("Cyan Pulse", w_cyan_pulse),
    "nyxus-carbon-weave": ("Carbon Weave", w_carbon_weave),
    "nyxus-sigil": ("NYXUS Sigil", w_nyxus_sigil),
}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    manifest = []
    for slug, (title, fn) in WALLPAPERS.items():
        path = OUT / f"{slug}.svg"
        path.write_text(fn())
        manifest.append(f"{slug}\t{title}")
    (OUT / "manifest.tsv").write_text("\n".join(manifest) + "\n")
    print(f"NYXUS wallpapers: wrote {len(WALLPAPERS)} svgs to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
