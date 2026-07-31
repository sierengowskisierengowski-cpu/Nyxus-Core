# NYX ISO builder
### `iso-builder/` — bakes `out/nyxus-<YYYY.MM.DD>-x86_64.iso`

> **Rewritten 2026-07-30.** The previous revision described the May-2026 build
> and had gone materially wrong: it said the output was `nyx-*.iso`, gave the ISO
> label as `NYX_2026_05` (it is **`NYXUS_2026_07`**, and a label mismatch means
> the live media does not boot at all), claimed **116 packages** (there are
> **408**), said the Phantom tarball is fetched from the retired Replit host, and
> did not mention the **Kage-Ryu kernel** — which is the default kernel and a
> hard bake requirement. Re-derived from `build-iso.sh` and `profiledef.sh`.

> **Read [`../HANDOFF.md`](../HANDOFF.md) before baking.** It carries current
> bake readiness, the do-not-repeat gotchas, and the canonical
> bake → flash → boot procedure. The printable tick-list is
> [`../SHIPPING.md`](../SHIPPING.md).

> **Auto-dated builds:** every bake stamps today's date into the ISO filename,
> `iso_version` (mkarchiso metadata), `BUILD_ID` (`/etc/os-release`) and
> `/etc/nyxus-build` (which also records the **source commit** — that is how you
> tell what a stick actually contains). Override with
> `NYX_ISO_DATE=2026.07.31 sudo ./build-iso.sh` for a deterministic re-bake.

This directory contains the `archiso` profile and a one-command wrapper that
produces the NYX ISO.

## Requirements

Must run on an **Arch Linux host as root**. `mkarchiso` needs root + loop
devices, `pacman` against live Arch repos, and:

```bash
sudo pacman -S --needed archiso squashfs-tools libisoburn dosfstools
```

Disk: the ISO is ~**9.5–10 GB**, so budget **≥ 40 GB** for the work dir and
**≥ 12 GB** for `out/` (which is gitignored and fills up with old ISOs).

**The bake hard-fails if the prebuilt Kage-Ryu packages are missing** — they live
at `~/Projects/arch-custom-kernel/linux-kage-ryu/` and are found automatically.
The kernel is never compiled inside the bake.

## Build it

```bash
cd iso-builder
sudo ./build-iso.sh
```

| Env var | Effect |
|---|---|
| `NYX_WITH_KAGE_RYU=0` | Opt **out** of Kage-Ryu; bake a stock-kernel-only debug ISO. Default is `1`. |
| `NYX_SQUASH_COMP=xz` | Use the old `xz` squashfs compressor: ~10.8% smaller ISO, ~**7.6× slower cold reads**. Default is `zstd`. Gate `13ad` warns when you pick `xz`. |
| `NYX_ISO_DATE=<Y.M.D>` | Pin the stamped date. |
| `NYX_ALLOW_HYPRLAND=1` | Bypass gate `13x`, which hard-fails if the repos offer Hyprland ≥ 0.57 (that release drops hyprlang and this profile is `hyprland.conf` + hyprlang shards). |
| `NYXUS_INTEL_SHA256=<sha>` | Enforce (fail-closed) the SHA-256 of the staged Phantom tarball. |

Output: `iso-builder/out/nyxus-<today>-x86_64.iso`

**Bake from a clean, committed, idle repo.** Bash re-reads scripts by byte
offset, and the bake reads the profile as it runs — an in-flight edit produces an
ISO containing a partial change set. This has already cost a stick (2026-07-22).

## What `build-iso.sh` does

The real step list, in order (`rg '^step ' build-iso.sh`):

1. **preflight** — root + Arch checks
2. **stage a throwaway profile copy** — the bake never mutates the repo's
   `nyx-profile/` (fixed 2026-07-22, `fe089345`)
3. **stamp the ISO version** into `profiledef.sh`, `os-release`, `/etc/nyxus-build`
4. **fetch NYXUS Phantom** (`nyxus-intel.tgz`) — **prefers the in-repo copy** at
   `artifacts/api-server/nyxus-scripts/nyxus-intel.tgz`; the network fetch is a
   fallback only, and it points at the **retired** Replit host, so it will fail.
   The SHA-256 is always printed for sign-off.
5. **stage the NYXUS chrome** — configs, GTK apps, wallpapers, scripts (see below)
6. **stage Phantom** into `airootfs/opt/nyxus-intel/` + seal its tamper manifest
7. **wave-4 install wiring** — helper binaries, firstboot units, themes,
   `.desktop` entries, polkit policies
8. **stage the security lab** — Bifrost (Master Hub), Meli (Honeypot Command
   Center), the live honeypot/Docker stack, jeTT, Arsenal
9. **mirror the OS-level docs** (`LICENSE.md`, `README.md`, `CHANGELOG.md`,
   `CREDITS.md`) into `airootfs/etc/nyxus/`
10. **stage Kage-Ryu** into a profile-local `[nyxus-local]` repo, append it to
    `packages.x86_64`, and rewrite the three live boot menus (grub /
    systemd-boot / syslinux) so Kage-Ryu is entry **#0** and stock `linux` is a
    labelled **rescue** entry — all inside the throwaway copy
11. **run `mkarchiso`** and rename the result to `nyxus-<today>-x86_64.iso`

## ⚠ The single most important fact about this profile

**The bake wipes `airootfs/etc/skel/.config/{hypr,eww,...}` and repopulates it
from `artifacts/api-server/nyxus-scripts/` (NS = the source of truth).**

Committing a file under `airootfs/` is **not** enough to ship it for most paths.
This exact class of bug has shipped at least four times — dropped hypr shards,
dropped eww assets, a polkit Replit purge silently reverted on every bake,
`regreet.css`/`regreet.toml` never staged at all, and `nyxus_screensaver.py`
never staged. `verify-profile.sh` gate `13w` now derives the shard requirement
from `hyprland.conf` itself rather than from the staging whitelist, so adding a
shard needs no edit there.

Three shards are **generated at runtime** and must never be glob-copied over:
`nyxus-stations.conf` (by `nyxus-hacker-mode`), `nyxus-freeform.conf` (by
`nyxus-freeform`), `nyxus-monitors.conf` (by Settings).

## Chrome staging (source of truth → airootfs)

| Source (in `nyxus-scripts/`) | Destination in airootfs |
|---|---|
| `hyprland.conf`, `hyprlock.conf`, `hypridle.conf` | `/etc/skel/.config/hypr/` |
| `nyxus-*.conf` shards | `/etc/skel/.config/hypr/conf.d/` (17 sourced + `nyxus-safemode.conf`) |
| `eww/eww.yuck`, `eww/eww.css`, `eww/eww.scss.source`, `eww/nyxus.conf`, `eww/scripts/*`, `eww/assets/*` | `/etc/skel/.config/eww/` |
| `greetd/regreet.css`, `greetd/regreet.toml` | `/etc/greetd/` |
| `nyxus-dunstrc` → `dunstrc` | `/etc/skel/.config/dunst/` |
| `rofi-*.rasi` | `/etc/skel/.config/rofi/` |
| `wlogout-style.css`, `wlogout-layout` | `/etc/skel/.config/wlogout/` |
| `alacritty.toml`, `kitty.conf` | `/etc/skel/.config/{alacritty,kitty}/` |
| `nyxus_*.py` (GTK app suite + `nyxus_chrome` + `nyxus_palette` + both screensavers) | `/opt/nyxus/` |
| `hypr-walls/` incl. `rotation/` (32 images) | `/etc/skel/.config/hypr/walls/` **and** `/usr/share/backgrounds/nyxus/` |
| `nyxus-*` tools | `/usr/local/bin/` |
| `desktop-entries/*.desktop` | `/usr/share/applications/` (entries carrying `DesktopNames=` are skipped — those are **session** entries, not apps) |
| `polkit-policies/*` | `/usr/share/polkit-1/actions/` |
| everything, verbatim | `/opt/nyxus-cache/` (the offline first-boot cache) |

The **default wallpaper is `nyxus-urban-alien.png`** and every station wallpaper
is alien art. `wallpaper.conf` / `wallpaper.json` / the greeter / hyprlock / the
screensaver / wlogout all resolve to the same hero image.

## Profile layout

```
nyx-profile/
├── profiledef.sh                 # iso_name=nyxus, iso_label=NYXUS_2026_07,
│                                 # file_permissions (181 entries), zstd squashfs
├── packages.x86_64               # 408 packages (+ heavy inline rationale comments)
├── packages.x86_64.lean          # reduced list, not the default
├── pacman.conf                   # build-time pacman (wires [blackarch])
├── syslinux/syslinux.cfg         # BIOS boot menu (plain text — see below)
├── efiboot/loader/…              # UEFI boot loader entries
├── grub/                         # 🐉 dragon GRUB theme for the LIVE USB
│   ├── grub.cfg, fonts/ (.pf2), themes/nyxus/
└── airootfs/                     # overlay copied onto the live system
    ├── etc/
    │   ├── os-release, motd, hostname, issue
    │   ├── greetd/               # greetd config + regreet theme
    │   ├── pam.d/                # incl. sddm-recovery-snippet (LIVE — do not delete)
    │   ├── nyxus/                # OS-level docs + /etc/nyxus/nyxus.conf
    │   └── skel/.config/         # hypr, eww, nyxus, dunst, rofi, wlogout,
    │                             # alacritty, kitty, btop, cava, swaync, gtk-*
    ├── opt/                      # nyxus, nyxus-intel, nyxus-cache, arsenal
    ├── usr/local/bin/            # every nyxus-* tool the desktop calls
    └── usr/share/                # plymouth theme, backgrounds, icons, cursors,
                                  # applications, polkit actions, installed-GRUB theme
```

**Boot menus.** The 🐉 dragon GRUB menu is **UEFI-only**. A Legacy/BIOS boot gets
the plain `syslinux` text menu — that is the "normal menu" you see if you do not
pick the **"UEFI: <device>"** entry, and it is not a bug.

**`iso_label` must be identical** in `profiledef.sh` and all five `archisolabel`
references, or the live media will not boot.

## packages.x86_64

**408 real package lines** (the file is 772 lines; the rest is rationale
comments, which are load-bearing documentation — read them before removing a
package). Notable facts encoded there:

- **No `waybar`** — removed 2026-05-11, replaced by **eww**. eww itself is
  AUR-only (`eww-wayland`) and is built from source by `customize_airootfs.sh`,
  along with `mpvpaper` and `wlogout`.
- **No `sddm`.** The live greeter is **greetd** → `nyxus-greeter` → **regreet**
  under **cage**, with **tuigreet** as the text fallback. `greetd`,
  `greetd-regreet`, `greetd-tuigreet` and `cage` are all in the list; without
  them the ISO boots to greetd with no greeter binary at all. The SDDM QML theme
  is still staged, but only for a disk install that chooses to enable it.
- **`calamares` is a plain binary package** from **`[blackarch]`**, pacstrapped
  directly. It is **not** AUR-built in the chroot — that false premise cost four
  failed ISOs before 2026-07-28. The AUR fallback call is left in place but
  early-returns.
- **`btop` was missing for weeks** while the profile shipped three btop themes
  and four launch paths that fell back to it. Added 2026-07-30.
- `swaybg` ships, plus `awww` (upstream renamed `swww`; a `swww`→`awww` compat
  symlink is added at bake so existing scripts keep working) and `mpvpaper` for
  the live wallpaper loop.
- `cava` is **required**, not eye candy — it drives the eww CAVA widget, the
  PULSE window halo, and the bass-reactive border animation.
- `mako` was removed — NYXUS standardized on `dunst`.

## Gates

`bash verify-profile.sh` from the repo root, before every bake. Its gates are
regression tests for bugs that already shipped: bake-wipe gaps, unsourced
shards, tools unreachable through an empty `~/.local/bin`, station-matrix drift,
the splash→greeter critical path, layer-blur rule ordering, `workspace name:0`,
eww handler timeouts, greeter theming, and the Hyprland version guard. If a gate
fails, fix the cause.

## Legal
Copyright © 2026 Joseph A. Sierengowski · All Rights Reserved ·
NYX-J5W-2026-SIERENGOWSKI-LOCKED · See LICENSE.md.
