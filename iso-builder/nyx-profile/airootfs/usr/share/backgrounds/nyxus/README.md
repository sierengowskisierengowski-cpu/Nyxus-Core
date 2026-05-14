# NYXUS · wallpaper pack

Canonical wallpaper directory shipped with the NYXUS profile. Consumed
by `nyxus-wallpaper-autostart`, `nyxus_wallpaper_studio.py`, and the
SDDM lockscreen mirror.

## Contents

- 9 vector originals (`*.svg`) — DARK MIRROR brand wallpapers
- 83 cosmic PNGs auto-categorized into four families:
  - `nyxus-void-NN.png` — deepest black / minimal noise
  - `nyxus-deepspace-NN.png` — low-light starfields
  - `nyxus-blackhole-NN.png` — dark structured swirls
  - `nyxus-nebula-NN.png` — colorful galactic shots

Total: 92 wallpapers. All listed in `manifest.tsv`
(tab-delimited `slug<TAB>display name`, one per file, strict 1:1 parity
enforced by `iso-builder/verify-profile.sh` section 13c).

## Default

The shipped default is set in `/etc/skel/.config/nyxus/wallpaper.conf`
using the runtime schema:

```sh
WALLPAPER="nyxus-nebula-01"
WALLPAPER_PATH="/usr/share/backgrounds/nyxus/nyxus-nebula-01.png"
```

Both keys are required — `nyxus-wallpaper-autostart` reads
`WALLPAPER_PATH` to launch swaybg, and `nyxus_wallpaper_studio.py`
reads `WALLPAPER` to highlight the active tile.

## SDDM mirror

PNGs are mirrored to
`iso-builder/nyx-profile/airootfs/usr/share/sddm/themes/nyxus/backgrounds/`
so the lockscreen and login picker can show the same pack. Verify
ensures parity at build time.

## Adding a wallpaper

1. Drop the file into this directory (PNG ≥1024px or SVG).
2. Append a line to `manifest.tsv` — `slug<TAB>Display Name`, where
   slug matches the filename without extension.
3. Mirror the PNG to the SDDM `backgrounds/` dir.
4. Re-run `bash iso-builder/verify-profile.sh` — section 13c will
   enforce parity, slug uniqueness, default validity, and SDDM mirror
   coverage.
