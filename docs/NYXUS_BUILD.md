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


## Save & verify (daily driver)

After polishing on the live desktop, persist everything in one shot:

```bash
nyxus-save-state
```

This compiles `eww.css` from `eww.scss.source`, bakes the accent baseline,
writes a local GOLD snapshot under `~/nyxus-build-recovery/` (not in git),
and runs `nyxus-backport-live.sh` into `artifacts/`.

Health check without touching the session:

```bash
nyxus-verify-build          # session health + untangle audit
nyxus-audit-untangle.sh     # cross-project refs only
```

**Single source of truth:** `Nyxus-Core/artifacts/api-server/nyxus-scripts/` +
`artifacts/nyxus-config/`. ISO builds read the same tree via `iso-builder/build-iso.sh`.
`~/sharkdash/nyxus/` and `~/nyxus-build-recovery/` are local backups only — never product.

## One roof policy

NYXUS Hyprland ships **only** from Nyxus-Core artifacts. These are **separate
projects** and must never be wired into NYXUS exec-once, keybinds, rofi menus, or
EWW onclick handlers:

| Project | Location | NYXUS relationship |
|---------|----------|-------------------|
| **SharkDash** | `~/.local/bin/sharkdash*`, `~/.config/sharkdash/` | Local TUI monitor — not part of NYXUS product |
| **Bifrost EDR** | `~/Projects/bifrost` | Separate security stack; deepcore widget may *report* service status only |
| **Gowskinet/Qtile** | `~/.config/gowskinet/`, `~/.config/qtile/` | Legacy desktop — not NYXUS Hyprland |
| **Nexus (old name)** | `nexus.jpg`, `@theme "nexus"` | Retired — use `nyxus` theme and `nyxus-*` walls |

Audit for drift:

```bash
nyxus-audit-untangle.sh    # cross-project refs, palette, hyprlock/hyprexpo policy
nyxus-verify-build         # includes untangle checks + live session health
```

**Lock policy:** Super+L or idle → EWW **starfield lock veil** (`screensaver` window).
Double-click the center ✦ star to reveal **hyprlock** (Prism HUD). Agents must **not**
run `hyprlock` during automated tests — user validates manually. `wlogout` for power actions.

**Kernel / ISO:** see [KERNEL_ISO.md](KERNEL_ISO.md) for MSI GS77 boot alignment and lean ISO tiers.

**Plugin policy:** `hyprexpo` must not autoload or be keybound (crash risk); use `nyxus-mission-control-toggle` instead.

### Starfield lock veil

Generate fullscreen twinkle assets (once per resolution change):

```bash
python3 ~/.config/eww/scripts/gen-starfield-lock.py
nyxus-eww-launch-safe
```

Assets land in `~/.config/eww/assets/starfield-lock-*.png`. Hyprlock background
uses the same base PNG for visual continuity.

### EWW 0.5 CSS rule

Live and canonical ship **`eww.css`** + **`eww.scss.source`** only — never both
`eww.scss` and `eww.css`. Compile with `~/.config/eww/scripts/compile-eww-css.sh`
(`--no-charset`). `nyxus-eww-launch` compiles on boot before opening bars.

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
| `~/Projects/bifrost` | Separate EDR project — deepcore widget reports status only |
| `~/.local/bin/sharkdash*` | Local SharkDash tools — not NYXUS ship surface |
| `~/.config/gowskinet/` | Legacy Qtile/gowski desktop — not NYXUS Hyprland |
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
cp ~/.config/eww/eww.scss.source \
   ~/.config/nyxus/accent-baseline/home/cosmic/.config/eww/eww.scss
# or: nyxus-save-state (does this automatically)
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
