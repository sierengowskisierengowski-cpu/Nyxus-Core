# NYXUS Build — Single Source of Truth

This document defines the **one unified NYXUS desktop build** for development,
live runtime, and ISO baking. Everything lives in **Nyxus-Core** on GitHub.

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
| `~/nyxus-build-recovery/` | Local timestamped snapshots — not in git |
| `~/.config/eww/.restore-points/` | Local EWW rollback — prune periodically |

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
2. **Never** use `height:` or `max-width:` in EWW CSS — invalid in GTK CSS
3. Bars must use `box` not `centerbox` for background `:style` to render
4. Bar CSS must keep static starlight/prism fallbacks — do not set `background-image: none` on bar classes
5. `nyxus-eww-launch-safe` must NOT start a second daemon — only kill strays + exec `nyxus-eww-launch`

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

Safe to remove after backport:

- `~/.nyxus/nyxus-home.bak-*`
- `~/.config/eww/*.bak*`
- Old entries in `~/.config/eww/.restore-points/` (keep latest 3)

Archive before deleting: `~/nyxus-build-recovery/`
