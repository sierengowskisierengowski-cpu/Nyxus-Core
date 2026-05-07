# NYXUS · Boot Splash Bundle

> Welcome to the darkside.
> NYX-J5W-2026-SIERENGOWSKI-LOCKED

Self-contained Plymouth theme + GRUB theme that match the NYXUS DARK GLASS Visual System.
Designed to drop into an `archiso` build profile **or** install on a running box.

---

## Contents

```
boot-splash/
├── plymouth/nyxus/
│   ├── nyxus.plymouth        # Theme manifest (script-type)
│   ├── nyxus.script          # Animation: fade-in + 12-dot gold spinner
│   ├── background.png        # Cosmic ink swirl, 1920x1080
│   ├── wordmark.png          # NYXUS gold serif wordmark
│   ├── tagline.png           # WELCOME  TO  THE  DARKSIDE
│   ├── subline.png           # NYXUS · SIERENGOWSKI · 2026
│   ├── dot.png               # Cool-white halo dot (idle)
│   └── dot_gold.png          # Warm-gold halo dot (active spinner head)
├── grub/themes/nyxus/
│   ├── theme.txt             # GRUB theme spec
│   ├── background.png        # Same cosmic ink swirl
│   ├── wordmark.png          # Same NYXUS wordmark
│   └── select_*.png          # Selection box pixmap (3-slice)
├── install.sh                # Two-mode installer (system / --iso)
└── README.md                 # This file
```

---

## Path A — Bake into your archiso profile (the ISO builder)

Hand the bundle to whoever's running `mkarchiso` and have them do this from the
nyx-profile directory:

```bash
# 1. Drop the bundle next to nyx-profile/
tar -xzf nyxus-boot-splash.tar.gz

# 2. Patch the profile (idempotent — safe to re-run)
sudo NYX_PROFILE_ROOT="$(pwd)/nyx-profile" \
    bash boot-splash/install.sh --iso

# 3. Build the ISO
sudo mkarchiso -v -w /tmp/archiso-work -o ./out ./nyx-profile
```

That single `--iso` install does **all** of:
- Stages plymouth theme into `airootfs/usr/share/plymouth/themes/nyxus/`
- Stages GRUB theme into `airootfs/usr/share/grub/themes/nyxus/`
- Stages GRUB theme into `nyx-profile/grub/themes/nyxus/` (so the live ISO menu uses it too)
- Adds `plymouth` to `packages.x86_64`
- Inserts `plymouth` hook into `mkinitcpio.conf` after `udev`
- Writes `/etc/plymouth/plymouthd.conf` so the daemon picks NYXUS as default
- Patches `grub/grub.cfg` to load the theme

The kernel cmdline already has `quiet splash` in the existing
`syslinux.cfg` / `loader/entries/01-nyx.conf` / `grub.cfg` — nothing to add there.

---

## Path B — Install on a live NYXUS install (real hardware)

```bash
sudo bash install.sh
```

Does:
- Installs `plymouth` if missing (via pacman)
- Copies plymouth theme to `/usr/share/plymouth/themes/nyxus/`
- Runs `plymouth-set-default-theme -R nyxus` (rebuilds initramfs)
- Adds `quiet splash` to `GRUB_CMDLINE_LINUX_DEFAULT` in `/etc/default/grub`
- Sets `GRUB_THEME=…/nyxus/theme.txt`
- Copies grub theme to `/usr/share/grub/themes/nyxus/`
- Runs `grub-mkconfig -o /boot/grub/grub.cfg`

### Preview without rebooting

```bash
sudo plymouthd
sudo plymouth --show-splash
sleep 8
sudo plymouth quit
```

---

## Visual specification (locked)

- **Background** — `nyxus-ink-swirl.png` (cosmic black-hole / silver wisps), full-bleed cover.
- **Wordmark** — `NYXUS` in DejaVu Serif Bold, 130pt, fill `#d4a73a` (warm gold), soft warm shadow.
- **Tagline** — `WELCOME  TO  THE  DARKSIDE` in DejaVu Sans Bold, 22pt, fill `#e6f0ff` (starlight cool-white), heavy letter-spacing.
- **Subline** — `NYXUS · SIERENGOWSKI · 2026` in DejaVu Sans Mono, 14pt, fill `#a8b0bd` (pencil-light).
- **Spinner** — 12 dots arrayed in a 64px-radius ring, anchored 130px from bottom-center.
  Idle ring at `0.18` opacity cool-white. A 4-dot warm-gold "comet" rotates clockwise once every ~4s with a 1.0 → 0.65 → 0.35 → 0.15 trail.
- **Vignette** — Plymouth doesn't ship a true gradient; the ink swirl already provides the dark frame.
- **Forbidden** — neon, cyan, lime, multi-color rainbows, pulsing strobes, "hacker" green/red text. None of it.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Splash doesn't show, only text scrolls | `quiet splash` missing from kernel cmdline. Check `/etc/default/grub` then `grub-mkconfig -o /boot/grub/grub.cfg`. |
| Plymouth shows but with wrong theme | `plymouth-set-default-theme -R nyxus` and re-test. |
| Initramfs missing plymouth hook | `mkinitcpio -P` after editing `/etc/mkinitcpio.conf` so `HOOKS=( base udev plymouth … )`. |
| GRUB menu still old style | `GRUB_THEME` not set in `/etc/default/grub`, or `grub-mkconfig` not re-run. |
| Splash for ~0.2s then text | Boot is too fast — that's a feature, not a bug. Add `plymouth.enable=1 splash` to cmdline if you want it forced. |

---

© 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
