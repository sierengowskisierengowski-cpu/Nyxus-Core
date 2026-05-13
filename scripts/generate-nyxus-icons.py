#!/usr/bin/env python3
"""Generate the NYXUS-Dark icon theme.

Each icon = 64x64 SVG with:
  * dark glass radial-gradient disc background (#0a0a14 -> #000)
  * thin purple-to-cyan ring stroke (#a06bff -> #3ad8ff)
  * unique glyph centered (white #e8edf5)

Outputs into:
  iso-builder/nyx-profile/airootfs/usr/share/icons/NYXUS-Dark/scalable/<ctx>/<name>.svg

Run from repo root:
  python3 scripts/generate-nyxus-icons.py
"""
from __future__ import annotations

import os
import sys
import textwrap
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
THEME_ROOT = REPO / "iso-builder/nyx-profile/airootfs/usr/share/icons/NYXUS-Dark"

# (icon-name, context, glyph-svg-fragment)
# context is one of: apps, places, devices, status, actions
# glyph fragment is centered around (32, 32), drawn in #e8edf5
ICONS: list[tuple[str, str, str]] = [
    # ── Applications ─────────────────────────────────────────────
    ("nyxus-settings", "apps",
     '<circle cx="32" cy="32" r="6" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<g stroke="#e8edf5" stroke-width="3" stroke-linecap="round">'
     '<line x1="32" y1="14" x2="32" y2="20"/><line x1="32" y1="44" x2="32" y2="50"/>'
     '<line x1="14" y1="32" x2="20" y2="32"/><line x1="44" y1="32" x2="50" y2="32"/>'
     '<line x1="19.5" y1="19.5" x2="23.5" y2="23.5"/><line x1="40.5" y1="40.5" x2="44.5" y2="44.5"/>'
     '<line x1="19.5" y1="44.5" x2="23.5" y2="40.5"/><line x1="40.5" y1="23.5" x2="44.5" y2="19.5"/>'
     '</g>'),
    ("preferences-system", "apps", "__alias__:nyxus-settings"),
    ("preferences-desktop", "apps", "__alias__:nyxus-settings"),
    ("preferences-desktop-display", "apps",
     '<rect x="14" y="16" width="36" height="24" rx="2" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<line x1="22" y1="46" x2="42" y2="46" stroke="#e8edf5" stroke-width="3" stroke-linecap="round"/>'
     '<line x1="32" y1="40" x2="32" y2="46" stroke="#e8edf5" stroke-width="3"/>'),
    ("preferences-desktop-locale", "apps",
     '<circle cx="32" cy="32" r="16" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<ellipse cx="32" cy="32" rx="8" ry="16" fill="none" stroke="#e8edf5" stroke-width="2"/>'
     '<line x1="16" y1="32" x2="48" y2="32" stroke="#e8edf5" stroke-width="2"/>'),
    ("preferences-desktop-screensaver", "apps",
     '<rect x="14" y="16" width="36" height="26" rx="3" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<circle cx="32" cy="29" r="4" fill="#e8edf5"/>'
     '<path d="M22 38 Q32 32 42 38" fill="none" stroke="#e8edf5" stroke-width="2"/>'),
    ("preferences-desktop-theme", "apps",
     '<circle cx="32" cy="32" r="16" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<circle cx="26" cy="26" r="3" fill="#a06bff"/>'
     '<circle cx="38" cy="26" r="3" fill="#3ad8ff"/>'
     '<circle cx="26" cy="38" r="3" fill="#82ffd2"/>'
     '<circle cx="38" cy="38" r="3" fill="#ffb45e"/>'),
    ("preferences-desktop-wallpaper", "apps",
     '<rect x="12" y="16" width="40" height="28" rx="3" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<circle cx="22" cy="26" r="3" fill="#e8edf5"/>'
     '<path d="M14 40 L24 30 L34 38 L44 28 L50 34 L50 42 L14 42 Z" fill="#e8edf5" opacity="0.9"/>'),
    ("system-file-manager", "apps",
     '<path d="M14 22 L14 44 Q14 46 16 46 L48 46 Q50 46 50 44 L50 26 Q50 24 48 24 L30 24 L26 20 L16 20 Q14 20 14 22 Z" '
     'fill="none" stroke="#e8edf5" stroke-width="3" stroke-linejoin="round"/>'),
    ("system-search", "apps",
     '<circle cx="28" cy="28" r="11" fill="none" stroke="#e8edf5" stroke-width="3.5"/>'
     '<line x1="36" y1="36" x2="46" y2="46" stroke="#e8edf5" stroke-width="4" stroke-linecap="round"/>'),
    ("system-shutdown", "apps",
     '<path d="M32 14 L32 30" stroke="#e8edf5" stroke-width="4" stroke-linecap="round"/>'
     '<path d="M22 22 A14 14 0 1 0 42 22" fill="none" stroke="#e8edf5" stroke-width="4" stroke-linecap="round"/>'),
    ("system-software-install", "apps",
     '<rect x="16" y="18" width="32" height="28" rx="3" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<line x1="32" y1="24" x2="32" y2="40" stroke="#e8edf5" stroke-width="3" stroke-linecap="round"/>'
     '<line x1="24" y1="32" x2="40" y2="32" stroke="#e8edf5" stroke-width="3" stroke-linecap="round"/>'),
    ("system-software-update", "apps",
     '<path d="M20 30 A12 12 0 1 1 24 41" fill="none" stroke="#e8edf5" stroke-width="3" stroke-linecap="round"/>'
     '<polyline points="14,26 20,30 26,26" fill="none" stroke="#e8edf5" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'),
    ("system-run", "apps",
     '<polygon points="22,16 50,32 22,48" fill="#e8edf5"/>'),
    ("utilities-terminal", "apps",
     '<rect x="12" y="16" width="40" height="32" rx="3" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<polyline points="20,26 26,32 20,38" fill="none" stroke="#e8edf5" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
     '<line x1="30" y1="40" x2="42" y2="40" stroke="#e8edf5" stroke-width="3" stroke-linecap="round"/>'),
    ("utilities-system-monitor", "apps",
     '<rect x="12" y="18" width="40" height="24" rx="2" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<polyline points="16,36 22,28 28,32 34,22 40,30 48,24" '
     'fill="none" stroke="#3ad8ff" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>'),
    ("accessories-text-editor", "apps",
     '<path d="M18 14 L42 14 L46 18 L46 50 L18 50 Z" fill="none" stroke="#e8edf5" stroke-width="3" stroke-linejoin="round"/>'
     '<line x1="24" y1="26" x2="40" y2="26" stroke="#e8edf5" stroke-width="2"/>'
     '<line x1="24" y1="32" x2="40" y2="32" stroke="#e8edf5" stroke-width="2"/>'
     '<line x1="24" y1="38" x2="34" y2="38" stroke="#e8edf5" stroke-width="2"/>'),
    ("applets-screenshooter", "apps",
     '<rect x="12" y="20" width="40" height="26" rx="3" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<circle cx="32" cy="33" r="7" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<rect x="26" y="14" width="12" height="6" rx="1" fill="#e8edf5"/>'),
    ("applications-graphics", "apps",
     '<path d="M16 46 Q16 28 32 16 Q48 28 48 46 Z" fill="none" stroke="#e8edf5" stroke-width="3" stroke-linejoin="round"/>'
     '<circle cx="24" cy="38" r="3" fill="#a06bff"/>'
     '<circle cx="32" cy="32" r="3" fill="#3ad8ff"/>'
     '<circle cx="40" cy="38" r="3" fill="#82ffd2"/>'),
    ("applications-development", "apps",
     '<polyline points="22,22 14,32 22,42" fill="none" stroke="#e8edf5" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
     '<polyline points="42,22 50,32 42,42" fill="none" stroke="#e8edf5" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
     '<line x1="36" y1="18" x2="28" y2="46" stroke="#e8edf5" stroke-width="3" stroke-linecap="round"/>'),
    ("calamares", "apps",
     '<polygon points="32,12 50,42 14,42" fill="none" stroke="#e8edf5" stroke-width="3" stroke-linejoin="round"/>'
     '<circle cx="32" cy="34" r="3" fill="#3ad8ff"/>'
     '<line x1="32" y1="22" x2="32" y2="29" stroke="#e8edf5" stroke-width="3" stroke-linecap="round"/>'),
    ("dialog-error", "apps",
     '<circle cx="32" cy="32" r="14" fill="none" stroke="#ff4d6b" stroke-width="3"/>'
     '<line x1="25" y1="25" x2="39" y2="39" stroke="#ff4d6b" stroke-width="3" stroke-linecap="round"/>'
     '<line x1="39" y1="25" x2="25" y2="39" stroke="#ff4d6b" stroke-width="3" stroke-linecap="round"/>'),
    ("dialog-information", "apps",
     '<circle cx="32" cy="32" r="14" fill="none" stroke="#3ad8ff" stroke-width="3"/>'
     '<circle cx="32" cy="24" r="2.2" fill="#3ad8ff"/>'
     '<rect x="30" y="28" width="4" height="14" rx="1" fill="#3ad8ff"/>'),
    ("tools-report-bug", "apps",
     '<ellipse cx="32" cy="34" rx="11" ry="13" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<line x1="26" y1="20" x2="22" y2="14" stroke="#e8edf5" stroke-width="2" stroke-linecap="round"/>'
     '<line x1="38" y1="20" x2="42" y2="14" stroke="#e8edf5" stroke-width="2" stroke-linecap="round"/>'
     '<line x1="14" y1="34" x2="21" y2="34" stroke="#e8edf5" stroke-width="2" stroke-linecap="round"/>'
     '<line x1="43" y1="34" x2="50" y2="34" stroke="#e8edf5" stroke-width="2" stroke-linecap="round"/>'),
    ("help-about", "apps",
     '<circle cx="32" cy="32" r="14" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<path d="M27 26 Q32 21 37 26 Q37 31 32 33 L32 37" fill="none" stroke="#e8edf5" stroke-width="3" stroke-linecap="round"/>'
     '<circle cx="32" cy="42" r="2" fill="#e8edf5"/>'),
    ("user-info", "apps",
     '<circle cx="32" cy="24" r="8" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<path d="M16 50 Q16 36 32 36 Q48 36 48 50" fill="none" stroke="#e8edf5" stroke-width="3" stroke-linecap="round"/>'),
    ("security-high", "apps",
     '<path d="M32 12 L48 18 L48 32 Q48 44 32 52 Q16 44 16 32 L16 18 Z" fill="none" stroke="#e8edf5" stroke-width="3" stroke-linejoin="round"/>'
     '<polyline points="24,32 30,38 42,26" fill="none" stroke="#82ffd2" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'),
    ("edit-paste", "apps",
     '<rect x="18" y="16" width="28" height="34" rx="2" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<rect x="24" y="12" width="16" height="8" rx="2" fill="#e8edf5"/>'
     '<line x1="24" y1="30" x2="40" y2="30" stroke="#e8edf5" stroke-width="2"/>'
     '<line x1="24" y1="36" x2="40" y2="36" stroke="#e8edf5" stroke-width="2"/>'
     '<line x1="24" y1="42" x2="34" y2="42" stroke="#e8edf5" stroke-width="2"/>'),
    ("folder-download", "apps",
     '<path d="M14 20 L26 20 L30 24 L50 24 L50 46 Q50 48 48 48 L16 48 Q14 48 14 46 Z" '
     'fill="none" stroke="#e8edf5" stroke-width="3" stroke-linejoin="round"/>'
     '<line x1="32" y1="28" x2="32" y2="40" stroke="#3ad8ff" stroke-width="3" stroke-linecap="round"/>'
     '<polyline points="26,36 32,42 38,36" fill="none" stroke="#3ad8ff" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'),
    ("drive-harddisk", "apps",
     '<rect x="12" y="22" width="40" height="20" rx="3" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<circle cx="42" cy="32" r="2" fill="#82ffd2"/>'
     '<line x1="18" y1="32" x2="34" y2="32" stroke="#e8edf5" stroke-width="2"/>'),
    ("drive-removable-media", "apps",
     '<rect x="22" y="14" width="20" height="36" rx="3" fill="none" stroke="#e8edf5" stroke-width="3"/>'
     '<line x1="22" y1="22" x2="42" y2="22" stroke="#e8edf5" stroke-width="2"/>'
     '<rect x="28" y="16" width="3" height="4" fill="#e8edf5"/>'
     '<rect x="33" y="16" width="3" height="4" fill="#e8edf5"/>'),
    ("io.nyxus.intel", "apps",
     '<circle cx="32" cy="32" r="14" fill="none" stroke="#a06bff" stroke-width="3"/>'
     '<circle cx="32" cy="32" r="6" fill="none" stroke="#3ad8ff" stroke-width="2.5"/>'
     '<circle cx="32" cy="32" r="2" fill="#e8edf5"/>'
     '<line x1="32" y1="14" x2="32" y2="18" stroke="#e8edf5" stroke-width="2"/>'
     '<line x1="32" y1="46" x2="32" y2="50" stroke="#e8edf5" stroke-width="2"/>'
     '<line x1="14" y1="32" x2="18" y2="32" stroke="#e8edf5" stroke-width="2"/>'
     '<line x1="46" y1="32" x2="50" y2="32" stroke="#e8edf5" stroke-width="2"/>'),
]

SVG_TEMPLATE = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">
      <defs>
        <radialGradient id="bg" cx="50%" cy="40%" r="60%">
          <stop offset="0%" stop-color="#0a0a14"/>
          <stop offset="100%" stop-color="#000000"/>
        </radialGradient>
        <linearGradient id="ring" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#a06bff"/>
          <stop offset="100%" stop-color="#3ad8ff"/>
        </linearGradient>
      </defs>
      <circle cx="32" cy="32" r="29" fill="url(#bg)" stroke="url(#ring)" stroke-width="1.5"/>
      {glyph}
    </svg>
    """)


def main() -> int:
    # resolve aliases (icons that mirror another)
    glyph_map: dict[str, str] = {}
    for name, _ctx, glyph in ICONS:
        if not glyph.startswith("__alias__:"):
            glyph_map[name] = glyph

    written = 0
    for name, ctx, glyph in ICONS:
        if glyph.startswith("__alias__:"):
            target = glyph.split(":", 1)[1]
            if target not in glyph_map:
                print(f"ERROR: alias {name} -> {target} (target missing)", file=sys.stderr)
                return 1
            glyph = glyph_map[target]
        out_dir = THEME_ROOT / "scalable" / ctx
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{name}.svg"
        out_path.write_text(SVG_TEMPLATE.format(glyph=glyph))
        written += 1

    print(f"NYXUS-Dark: wrote {written} icons to {THEME_ROOT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
