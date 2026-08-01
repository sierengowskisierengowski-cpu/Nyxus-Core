# NYXUS ISO Build Pipeline

> ⚠ **SUPERSEDED — read [`../../iso-builder/README.md`](../../iso-builder/README.md)
> instead.** That file was re-derived from `build-iso.sh` on 2026-07-30 and is the
> current description of the pipeline. This document is a May-2026 snapshot; the
> stages below are broadly right in shape but several specifics are wrong, and the
> four worst have been corrected inline (marked **CORRECTED 2026-07-30**) because
> following them costs real time:
>
> - the output is `nyxus-<date>-x86_64.iso`, **not** `nyx-…`
> - the offline cache comes from **`nyxus-scripts/`**, not `dist/nyxus-scripts/`
> - the ISO is ~**9.5–10 GB**, not ~2 GB, so the disk figures were ~5× too small
> - the **Kage-Ryu kernel** stage is missing entirely, and it is a hard bake
>   requirement

## Definition

The NYXUS ISO pipeline is implemented in `iso-builder/` and produces the NYXUS distribution image containing NYXUS runtime payloads.

## Prerequisites

- Arch Linux host
- Root access
- `archiso` toolchain (`mkarchiso`, `squashfs-tools`, `libisoburn`, `dosfstools`)
- **CORRECTED 2026-07-30:** ~**40 GB** free for the build workspace plus ~12 GB
  for `out/`. The old figure of "~6 GB in `/tmp`" was written when the ISO was
  ~2 GB; it is now ~9.5–10 GB.
- Prebuilt `linux-kage-ryu` packages at
  `~/Projects/arch-custom-kernel/linux-kage-ryu/` — **the bake hard-fails without
  them**, so it can never silently ship kernel-less.

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
10. **Offline cache** — **CORRECTED 2026-07-30:** mirrors
    **`artifacts/api-server/nyxus-scripts/`** (the git source of truth) to
    `/opt/nyxus-cache/`. `dist/nyxus-scripts/` is only a *fallback* and is
    **rejected outright** if it contains dangling symlinks — which is what a build
    on this host produces, and it has poisoned bakes before. The bake
    **hard-fails** if `nyxus_install.sh` would be missing, so an online-only ISO
    can no longer ship silently.
11. **SDDM theme** — extracts `nyxus-sddm-theme.tar.gz` into `/usr/share/sddm/themes/nyxus/` and writes `sddm.conf.d/nyxus.conf`. **Dormant** — the live greeter is greetd → regreet, not SDDM
12. **Security lab** — stages Bifrost, Meli, the honeypot/Docker stack, jeTT and Arsenal (this stage did not exist when this document was written)
13. **OS-level docs** — mirrors `LICENSE.md`, `README.md`, `CHANGELOG.md`, `CREDITS.md` into `airootfs/etc/nyxus/`
14. **Kage-Ryu kernel** — **MISSING FROM THIS LIST until 2026-07-30.** Stages the
    prebuilt packages into a profile-local `[nyxus-local]` repo, appends them to
    `packages.x86_64`, and rewrites all three live boot menus (grub /
    systemd-boot / syslinux) so Kage-Ryu is entry **#0** and stock `linux` is a
    labelled **rescue** entry — all inside the throwaway profile copy.
    `NYX_WITH_KAGE_RYU=0` opts out.
15. **`mkarchiso` execution** — bakes the squashfs (`zstd` since 2026-07-30; `NYX_SQUASH_COMP=xz` reverts) and produces the ISO
16. **Rename** — renames output to canonical **`nyxus-<ISO_DATE>-x86_64.iso`**
    (**CORRECTED 2026-07-30** — this said `nyx-…`)

## Inputs and Outputs

### Inputs
- Archiso profile under `iso-builder/nyx-profile/`
- Runtime payload source under `artifacts/api-server/nyxus-scripts/`
- Optional API dist cache under `artifacts/api-server/dist/nyxus-scripts/`
- Phantom tarball at `artifacts/api-server/nyxus-scripts/nyxus-intel.tgz` (or downloaded)
- SDDM theme tarball at `artifacts/api-server/nyxus-scripts/nyxus-sddm-theme.tar.gz`

### Output
- **`iso-builder/out/nyxus-<ISO_DATE>-x86_64.iso`** (~9.5–10 GB, gitignored) ·
  ISO label **`NYXUS_2026_07`** (**CORRECTED 2026-07-30**)

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

- ISO build requires an Arch Linux host with root; it cannot run in a container
  or on a non-Arch distribution.
- **CORRECTED 2026-07-30:** the old caveat *"Building without API dist cache
  produces an online-only first-boot path; run `pnpm --filter
  @workspace/api-server run build` first"* is **wrong**. Do **not** build `dist/`
  for a bake — the cache comes from `nyxus-scripts/`, and a `dist/` tree built on
  this host carries `/home/cosmic/…` symlinks that the bake rejects.
- **Bake only from a clean, committed, idle repo.** The bake reads the profile as
  it runs, so an in-flight edit ships a partial change set (this cost a stick on
  2026-07-22).
- **Run `bash iso-builder/verify-profile.sh` first.** Its gates are regression
  tests for bugs that already shipped.
- Build host must be treated as part of release-chain integrity.
- Set `NYXUS_INTEL_SHA256` in the environment to enforce tarball SHA verification
  (fail-closed). The network fallback for that tarball points at the **retired**
  Replit host, so the in-repo copy is what is actually used.


---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
