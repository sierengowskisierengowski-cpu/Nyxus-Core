# NYXUS
### NYX is the ISO. NYXUS is the OS.

> "Silent. Dark. Purely Functional."
> "The Night Has Eyes."

NYXUS is a custom Linux based operating system
built from the ground up by Joseph Sierengowski.
Distributed via the NYX ISO.

ISO: nyx-2026.05.02-x86_64.iso

## Built by
Joseph Sierengowski
Self-taught developer and hardware enthusiast
2026

## NYXUS App Suite
- NYXUS SYSMON
- NYXUS Control
- NYXUS Terminal
- NYXUS Notepad
- NYXUS Stickies
- NYXUS Weather
- NYXUS Settings
- NYXUS SAGE
- NYXUS Shield
- NYXUS Panel
- NYXUS Start
- NYXUS GodsApp
- NYXUS Phantom
- NYXUS Creative Studio

## Repository Layout

```
.
├── artifacts/                # Web download portal + app-suite scaffolds
│   ├── nyxus-web/            # Download portal (this is the live site)
│   ├── nyxus-notepad/        # Web demo of NYXUS Notepad
│   ├── nyxus-stickies/       # Web demo of NYXUS Stickies
│   ├── nyxus-sysmon/         # Web demo of NYXUS SYSMON
│   ├── nyxus-widgets/        # Web demo of NYXUS Widgets
│   └── api-server/           # Express API + tarball downloads
│       └── nyxus-scripts/
│           └── nyxus-intel.tgz   # NYXUS Phantom installer
├── iso-builder/              # archiso profile that bakes the NYX ISO
│   ├── build-iso.sh          # one-command wrapper (run on Arch as root)
│   └── nyx-profile/          # mkarchiso profile (releng-style)
├── LICENSE.md                # NYX & NYXUS Custom License v1.0
├── CHANGELOG.md
└── CREDITS.md
```

## Building the ISO
See `iso-builder/README.md`. Short version (run on an Arch host with
`archiso` installed, as root):

```bash
cd iso-builder
sudo ./build-iso.sh
```

The output lands in `iso-builder/out/nyx-2026.05.02-x86_64.iso`.

## Legal
Copyright © 2026 Joseph Sierengowski
All Rights Reserved
NYX-J5W-2026-SIERENGOWSKI-LOCKED
See LICENSE.md for full terms.
