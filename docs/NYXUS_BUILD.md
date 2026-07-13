# NYXUS Build — Single Source of Truth

This document defines the **one unified NYXUS desktop build** for development,
live runtime, and ISO baking. Everything lives in **Nyxus-Core** on GitHub.

## Build status (2026-07-13)

| Layer | Status |
|-------|--------|
| **Bars** | Restored — obsidian starlight, `box` layout, 86px margins, all 4 bars |
| **Flyouts** | Working — dashboard, quicksettings, wifi, bt, mixer, calendar, notif, updates, brightness, powermenu |
| **Theme** | Unified — `nyxus-palette.css` mirrored across eww/rofi/wlogout/dunst/hypr |
| **Wallpaper** | `nyxus-cosmic-galaxy.png` via swaybg |
| **Canonical git** | `Nyxus-Core` @ `artifacts/api-server/nyxus-scripts/` |
| **Recovery** | `~/nyxus-build-recovery/GOLD-LATEST` (local, not in git) |

### Known GTK/EWW rules (do not break)

- No non-ASCII in `eww.scss`
- No `height:`, `max-width:`, `flex-shrink`, `margin: auto` in EWW CSS
- Bars use `box` not `centerbox`; keep starlight CSS fallbacks on bar classes
- `TIME` poll must use `scripts/time.sh` (never inline `date +` in yuck)
- One EWW daemon only — use `nyxus-eww-launch-safe`

## Recovery (if the desktop breaks)

```bash
# Restore from the pinned GOLD snapshot + relaunch bars:
~/Nyxus-Core/scripts/nyxus-recovery.sh

# Create a new GOLD snapshot after polishing:
~/Nyxus-Core/scripts/nyxus-snapshot.sh --label my-label

# Quick bar-only fix (daemon died):
nyxus-eww-launch-safe
```

Recovery lives at `~/nyxus-build-recovery/`:
- `GOLD-LATEST` → symlink to current known-good snapshot
- `archive-pre-gold-*.tar.gz` → compressed history (safe to delete after verifying GOLD)

## Canonical paths

| Role | Path |
|------|------|
| **Git repo (product)** | `~/Nyxus-Core` → `github.com/sierengowskisierengowski-cpu/Nyxus-Core` |
| **Source of truth** | `artifacts/api-server/nyxus-scripts/` |
| **Station matrix** | `artifacts/nyxus-config/stations.json` |
| **ISO staging** | `iso-builder/nyx-profile/airootfs/` (baked by `build-iso.sh`) |
| **Live runtime** | `~/.config/eww`, `~/.config/hypr`, `~/.config/nyxus`, `~/.nyxus`, `~/.local/bin` |

## Deploy flow

```
Live polish  →  nyxus-backport-live.sh  →  artifacts/  →  git commit
git pull     →  sync-eww.sh + sync-hypr.sh  →  ~/.config/
ISO build    →  build-iso.sh reads artifacts/  →  airootfs squashfs
```

### Quick commands

```bash
# After editing on the live desktop — save to git:
~/Nyxus-Core/scripts/nyxus-backport-live.sh

# Full round-trip (backport + regen assets + deploy + verify):
~/Nyxus-Core/scripts/nyxus-audit-sync.sh

# After git pull — apply to live session:
~/Nyxus-Core/artifacts/api-server/nyxus-scripts/sync-eww.sh
~/Nyxus-Core/artifacts/api-server/nyxus-scripts/sync-hypr.sh
nyxus-eww-launch-safe
```

## What is NOT canonical

| Path | Status |
|------|--------|
| `~/sharkdash/nyxus/` | Personal backup only — do not edit product here |
| `~/Projects/bifrost` | Separate EDR project — only referenced by deepcore widget |
| `~/nyxus-build-recovery/GOLD-LATEST` | Local recovery snapshots — not in git |
| `~/.config/eww/.restore-points/` | Deprecated — use `nyxus-snapshot.sh` instead |

## Theme consistency

All surfaces import the same palette:

- `nyxus-palette.css` — CSS variables (obsidian, neon, glass)
- `_nyxus_accent.scss` — EWW accent tokens (generated from accent.json)
- `eww.scss` — obsidian bars, fog pills, starlight, cosmic flyouts

Palette is mirrored to: `eww/`, `rofi/`, `wlogout/`, `dunst/`, `hypr/`, `~/.nyxus/`.

After `eww.scss` changes, update the accent baseline:

```bash
cp ~/.config/eww/eww.scss \
   ~/.config/nyxus/accent-baseline/home/cosmic/.config/eww/eww.scss
~/Nyxus-Core/scripts/nyxus-backport-live.sh
```

## EWW critical rules

1. **Never** put non-ASCII in `eww.scss` — kills the entire GTK stylesheet
2. **Never** use `height:`, `max-width:`, `flex-shrink`, `flex-grow`, or `margin: auto` in EWW CSS
3. Bars must use `box` not `centerbox` for background `:style` to render
4. Bar CSS must keep static starlight/prism fallbacks — do not set `background-image: none` on bar classes
5. `nyxus-eww-launch-safe` must NOT start a second daemon — only kill strays + exec `nyxus-eww-launch`
6. `TIME` defpoll must call `~/.config/eww/scripts/time.sh` — never inline `` `date +...` ``

## Package layout in artifacts

```
artifacts/api-server/nyxus-scripts/
├── eww/                  # bars, flyouts, overlays, scripts/, assets/
├── nyxus-*.py            # GTK apps + chrome + cosmic_bg
├── nyxus-start/          # start menu package
├── nyxus-panel/          # panel package
├── nyxus-hyprland-*.conf # Hyprland conf.d shards
├── hyprland.conf         # main compositor config
├── sync-eww.sh           # deploy eww → ~/.config/eww
└── sync-hypr.sh          # deploy hypr → ~/.config/hypr

artifacts/nyxus-home/src/ # home app (mirrored from ~/.nyxus/nyxus-home)
artifacts/nyxus-config/   # stations.json, accent.json, accent-baseline
```

## Verification checklist

```bash
eww reload && nyxus-eww-launch-safe
pgrep -c -x eww          # must be 1
hyprctl configerrors     # must be "no errors"
```

Test flyouts: quicksettings, wifi, mixer, calendar, notifications, updates, brightness, dashboard, powermenu.

## Stale file cleanup

Do **not** keep in the product repo:

- `**/.restore-points/` — use `nyxus-snapshot.sh` instead
- `~/.nyxus/nyxus-home.bak-*`, `~/.config/eww/*.bak*`
- `attached_assets/` (Replit scratch — already gitignored)
- `artifacts/_tmp/` except `.gitkeep`

Archive old local recovery before deleting: `~/nyxus-build-recovery/archive-pre-gold-*.tar.gz`
