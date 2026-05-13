# NYX ISO Build Pipeline

## Definition

The NYX ISO pipeline is implemented in `iso-builder/` and produces the NYX distribution image containing NYXUS runtime payloads.

## Prerequisites

- Arch Linux host
- Root access
- `archiso` toolchain (`mkarchiso`, `squashfs-tools`, `libisoburn`, `dosfstools`)
- Sufficient temporary disk space for build workspace (~6 GB in `/tmp`)

Install once:
```bash
sudo pacman -S --needed archiso squashfs-tools libisoburn dosfstools
```

## Build Command

```bash
cd iso-builder
sudo ./build-iso.sh
```

Override the ISO date for deterministic re-bakes:
```bash
NYX_ISO_DATE=2026.05.11 sudo ./build-iso.sh
```

## Pipeline Responsibilities

`build-iso.sh` performs the following stages:

1. **Preflight** — validates root, Arch Linux host, and `mkarchiso` availability
2. **Version stamp** — writes `ISO_DATE` into `profiledef.sh` and `airootfs/etc/os-release` so filename, metadata, and live system all match
3. **Phantom tarball** — fetches `nyxus-intel.tgz` (NYXUS Phantom) from local repo or production URL; prints SHA-256 for sign-off
4. **Chrome staging** — copies full NYXUS chrome layer from `artifacts/api-server/nyxus-scripts/` into `airootfs`:
   - Hyprland + Hyprlock + Hypridle configs, `conf.d/` overlays
   - EWW bars (`eww.yuck`, `eww.scss`, `nyxus.conf`, scripts)
   - Dunst, Rofi, wlogout, Alacritty configs
   - All `nyxus_*.py` GTK4 apps and helper modules → `/opt/nyxus/`
   - Wallpapers → `/etc/skel/.config/hypr/walls/` and `/usr/share/backgrounds/nyxus/`
   - Helper scripts (`wallpaper-rotate`, `nyxus-eww-launch`) → `/usr/local/bin/`
5. **User units + policies** — stages EWW service, security daemon service, USB watch unit, parental control helper and polkit policies
6. **Welcome Wizard companion files** — stages `nyxus-welcome`, `nyxus-welcome-helper`, and `nyxus-welcome.policy`
7. **Bootstrap shims** — stages `nyxus-bootstrap` and `nyxus-wait-bootstrap` (first-run installer hooks fired by Hyprland `exec-once`)
8. **App launchers** — generates `/usr/local/bin/nyxus-*` wrapper scripts and `/usr/share/applications/io.nyxus.*.desktop` entries for 12 desktop apps
9. **Phantom staging** — extracts `nyxus-intel.tgz` into `/opt/nyxus-intel/`, seals tamper manifest, stages Phantom launcher and desktop entry
10. **Offline cache** — mirrors `artifacts/api-server/dist/nyxus-scripts/` to `/opt/nyxus-cache/` (enables offline-first bootstrap on first boot)
11. **SDDM theme** — extracts `nyxus-sddm-theme.tar.gz` into `/usr/share/sddm/themes/nyxus/` and writes `sddm.conf.d/nyxus.conf`
12. **OS-level docs** — mirrors `LICENSE.md`, `README.md`, `CHANGELOG.md`, `CREDITS.md` into `airootfs/etc/nyxus/`
13. **`mkarchiso` execution** — bakes the squashfs and produces the ISO
14. **Rename** — renames output to canonical `nyx-<ISO_DATE>-x86_64.iso`

## Inputs and Outputs

### Inputs
- Archiso profile under `iso-builder/nyx-profile/`
- Runtime payload source under `artifacts/api-server/nyxus-scripts/`
- Optional API dist cache under `artifacts/api-server/dist/nyxus-scripts/`
- Phantom tarball at `artifacts/api-server/nyxus-scripts/nyxus-intel.tgz` (or downloaded)
- SDDM theme tarball at `artifacts/api-server/nyxus-scripts/nyxus-sddm-theme.tar.gz`

### Output
- `iso-builder/out/nyx-<ISO_DATE>-x86_64.iso`

## Desktop Apps Staged (12 with .desktop entries)

| App | Binary |
|-----|--------|
| NYXUS Notepad | `nyxus-notepad` |
| NYXUS Stickies | `nyxus-stickies` |
| NYXUS Notes | `nyxus-notes` |
| NYXUS System Monitor | `nyxus-sysmon` |
| NYXUS Settings | `nyxus-settings` |
| NYXUS Control | `nyxus-control` |
| NYXUS Terminal | `nyxus-terminal` |
| NYXUS Launcher | `nyxus-launcher` |
| NYXUS Screenshot | `nyxus-screenshot` |
| NYXUS App Store | `nyxus-store` |
| NYXUS Power Menu | `nyxus-powermenu` |
| NYXUS Doctor | `nyxus-doctor` |

## Common Caveats

- ISO build is not supported in Replit environments.
- Building without API dist cache produces an online-only first-boot path; run `pnpm --filter @workspace/api-server run build` first to enable offline fallback.
- Build host must be treated as part of release-chain integrity.
- Set `NYXUS_INTEL_SHA256` in the environment to enforce tarball SHA verification (fail-closed).
