# NYX ISO builder
### `iso-builder/` — bakes `nyx-2026.05.02-x86_64.iso`

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

Output: `iso-builder/out/nyx-2026.05.02-x86_64.iso`

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
7. Renames the produced ISO to `nyx-2026.05.02-x86_64.iso`

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
    │           └── hypr/hyprland.conf  # placeholder
    └── opt/nyxus-intel/          # populated by build-iso.sh
```

## What still needs your input

The default `airootfs/etc/skel/.config/hypr/hyprland.conf` is a
**placeholder**. Drop your own working `hyprland.conf` (and waybar,
hyprlock, etc.) into `airootfs/etc/skel/.config/` so every new NYXUS
user gets your daily-driver setup out of the box.

The `packages.x86_64` list is a sane Hyprland-on-Arch baseline. Add
anything else you depend on (AUR packages need to be vendored
separately — archiso doesn't pull from AUR).

The other 13 apps in the suite are listed in CHANGELOG.md but only
NYXUS Phantom (`nyxus-intel.tgz`) ships with this build. As you finish
the others, drop their tarballs into `artifacts/api-server/nyxus-scripts/`
and add them to `build-iso.sh` next to the Phantom step.

## Legal
Copyright © 2026 Joseph Sierengowski
All Rights Reserved
NYX-J5W-2026-SIERENGOWSKI-LOCKED
See LICENSE.md.
