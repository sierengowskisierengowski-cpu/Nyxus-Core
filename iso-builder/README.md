# NYX ISO builder
### `iso-builder/` — bakes `nyx-<YYYY.MM.DD>-x86_64.iso`

> **Auto-dated builds:** every bake stamps today's date into the ISO
> filename, `iso_version` (mkarchiso metadata), and `BUILD_ID`
> (`/etc/os-release` inside the live system). Override with
> `NYX_ISO_DATE=2026.05.11 sudo ./build-iso.sh` for deterministic
> re-bakes of a specific release.

This directory contains the `archiso` profile and a one-command wrapper
that produces the NYX ISO. The ISO boots into NYXUS (the OS) with
NYXUS Phantom and the rest of the app suite preinstalled to
`/opt/nyxus-intel/` on the live system.

## Requirements

This **must run on an Arch Linux host** as root. archiso cannot be
built inside Replit, Docker, or non-Arch distributions because
`mkarchiso` needs:

- Root + loop devices
- `pacman` against live Arch repos
- `archiso`, `squashfs-tools`, `libisoburn`, `dosfstools`
- ~6 GB of free disk in `/tmp`

Install the prereqs once on your MSI:

```bash
sudo pacman -S --needed archiso squashfs-tools libisoburn dosfstools
```

## Build it

```bash
cd iso-builder
sudo ./build-iso.sh
```

Output: `iso-builder/out/nyx-<today>-x86_64.iso` (e.g. `nyx-2026.05.11-x86_64.iso`)

## What `build-iso.sh` does

1. Verifies you are root and on Arch
2. Pulls the latest `nyxus-intel.tgz` from
   `https://nyxus-core.replit.app/api/download/nyxus/nyxus-intel.tgz`
   (so the ISO always ships the latest watermarked Phantom build)
3. Extracts it into `nyx-profile/airootfs/opt/nyxus-intel/`
4. Seals the tamper manifest at `airootfs/opt/nyxus-intel/.manifest.sha256`
5. Mirrors the OS-level docs (`LICENSE.md`, `README.md`, `CHANGELOG.md`,
   `CREDITS.md`) into `airootfs/etc/nyxus/`
6. Runs `mkarchiso -v -w /tmp/nyx-work -o ./out ./nyx-profile/`
7. Renames the produced ISO to `nyx-<today>-x86_64.iso`

## Profile layout

```
nyx-profile/
├── profiledef.sh                 # ISO label NYX_2026_05, output filename
├── packages.x86_64               # every pacman package the ISO ships
├── pacman.conf                   # pacman config used during build
├── syslinux/syslinux.cfg         # BIOS boot menu (says NYXUS, not Arch)
├── efiboot/loader/loader.conf    # UEFI boot loader
├── efiboot/loader/entries/01-nyx.conf
├── grub/grub.cfg                 # secondary GRUB entry
└── airootfs/                     # overlay copied onto the live system
    ├── etc/
    │   ├── os-release            # NAME=NYXUS, PRETTY_NAME, etc.
    │   ├── motd                  # boot banner
    │   ├── hostname              # nyxus
    │   ├── nyxus/                # OS-level docs at /etc/nyxus/
    │   │   ├── LICENSE.md
    │   │   ├── README.md
    │   │   ├── CHANGELOG.md
    │   │   └── CREDITS.md
    │   └── skel/                 # default config for new users
    │       └── .config/
    │           └── hypr/hyprland.lua  # placeholder
    └── opt/nyxus-intel/          # populated by build-iso.sh
```

## NYXUS chrome staging (Phase 2 — May 2026)

`build-iso.sh` now stages the full NYXUS chrome layer into airootfs at
bake time, with a single source of truth at
`artifacts/api-server/nyxus-scripts/`. You no longer drop configs into
`airootfs/etc/skel/` by hand — they get copied in fresh on every bake
so `iso-builder/` and the live download portal can never drift apart.

What gets staged on every `sudo ./build-iso.sh`:

| Source (in `nyxus-scripts/`) | Destination in airootfs |
|---|---|
| `hyprland.lua`, `hyprlock.conf`, `hypridle.conf` | `/etc/skel/.config/hypr/` |
| `eww/eww.yuck`, `eww/eww.scss`, `eww/nyxus.conf`, `eww/scripts/*.sh` | `/etc/skel/.config/eww/` (rev r7-eww — replaces waybar) |
| `nyxus-dunstrc` → `dunstrc` | `/etc/skel/.config/dunst/` |
| `rofi-config.rasi`, `rofi-nyxus.rasi`, `rofi-startmenu.rasi` | `/etc/skel/.config/rofi/` |
| `wlogout-style.css`, `wlogout-layout` | `/etc/skel/.config/wlogout/` |
| `alacritty.toml` | `/etc/skel/.config/alacritty/` |
| `nyxus_*.py` (all 19 GTK apps + chrome library + helpers) | `/opt/nyxus/` |
| `nyxus-bg-*.png`, `nyxus-sierengowski-*.png`, `nyxus-void-vortex.png` (default wallpaper) | `/etc/skel/.config/hypr/walls/` AND `/usr/share/backgrounds/nyxus/` |
| `wallpaper-rotate.sh`, `nyxus-eww-launch` | `/usr/local/bin/` (renamed without `.sh`) |
| 12 launcher wrappers + `.desktop` entries | `/usr/local/bin/nyxus-*` and `/usr/share/applications/io.nyxus.*.desktop` |

The 12 apps with launchers + desktop entries are:
notepad, stickies, notes, sysmon (system monitor), settings, control,
terminal, launcher, screenshot, store (app store), powermenu, doctor.

## packages.x86_64

116 packages. Hyprland-on-Arch baseline plus every Phase 2 dep
(`dunst`, `swaybg`, `hyprshade`, `ttf-caveat`, `python-cairo`,
`python-psutil`, `power-profiles-daemon`, `blueman`, `wdisplays`,
`geoclue`, `alacritty`, `rofi`, `bluez`, `network-manager-applet`).
`mako` was removed in Phase 2 — NYXUS standardized on `dunst`.

AUR packages still need to be vendored separately — archiso doesn't
pull from AUR.

## Other tarball apps

Only NYXUS Phantom (`nyxus-intel.tgz`) gets a dedicated staging step
in `build-iso.sh`. As the other tarball apps stabilize
(godsapp, home, panel, sage, security, shield, start, studio,
passwords), add their staging step alongside the Phantom block.

## Legal
Copyright © 2026 Joseph Sierengowski
All Rights Reserved
NYX-J5W-2026-SIERENGOWSKI-LOCKED
See LICENSE.md.
