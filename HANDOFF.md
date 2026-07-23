# NYXUS — AGENT HANDOFF & BUILD STATE (read this FIRST)

> **Last updated: 2026-07-22** · Owner: Joseph A. Sierengowski (`nyx` / `nyxus`)
> If you are a new agent picking up NYXUS: **read this entire file before touching
> anything.** It exists because this project got scattered across duplicate clones
> and the same problems got re-diagnosed and re-broken multiple times, costing the
> owner a lot of time and money. Do not veer off into a different approach. Keep the
> flow, and **update this file as you work** so the next agent re-derives nothing.

---

## 0. THE RULES (do not break these)

1. **There is exactly ONE canonical repo: `~/Nyxus-Core`** (capital N-C, branch
   `main`, remote `sierengowskisierengowski-cpu/Nyxus-Core`). Always work here,
   commit + push every change. A lowercase `~/nyxus-core` or any
   `~/.nyxus-backup-*`, `~/nyxus-KNOWN-GOOD-*`, `~/nyxus-build-recovery`,
   `~/Backups/nyxus*` is a **stale snapshot — never work in it.** The lowercase
   duplicate was already deleted (2026-07-22) after verifying it held nothing
   unique. If one reappears, it's a wrong clone.
2. **Sudo on this machine is FINGERPRINT ONLY (no passwordless).** The agent
   **cannot** run `sudo`, `dd`, `chown`, or the bake (it needs root). The USER
   runs those in their own terminal. Never assume you can.
3. **Never edit `build-iso.sh` (or any script) while it is baking/running** —
   bash re-reads scripts by byte offset and it corrupts the live run.
3b. **Only start a bake from a fully COMMITTED, IDLE repo.** A bake reads the
   profile/scripts as it runs; if you kick it off mid-edit it captures a
   partial set of your changes. (2026-07-22: a bake started while edits were
   in flight shipped the offline-cache + saucer fixes but MISSED the
   ungated-bars fix — verify baked ISOs with `unsquashfs`, don't assume.)
4. **Don't fold the two sibling repos into Nyxus-Core** without explicit
   direction (see §1).
5. **When something surprises you, write it in this file the moment you hit it.**

---

## 1. THE THREE REPOS (single source of truth for each)

| Repo | Path | Remote | What it holds |
|---|---|---|---|
| **Nyxus-Core** | `~/Nyxus-Core` | `Nyxus-Core` (branch `main`) | The distro: ISO builder, all desktop configs, scripts, apps, docs. **Canonical.** |
| **kage-ryu** | `~/Projects/arch-custom-kernel/linux-kage-ryu` | `kage-ryu` | The custom kernel PKGBUILD + the `scheduler/` scx_kage sched-ext source. |
| **companion-3d** | `~/Nyxus-Core/companion-3d` | `Nyxus-Companion-3D` | A **separate** Godot 3D-companion project. Nested inside Nyxus-Core but its own git repo — **gitignored by the parent.** Not part of the ISO build. |

Live desktop surfaces (`~/.config`, `~/.local/bin`, `~/.nyxus`) mirror the repo —
keep them in sync, but **the repo is canonical.**

---

## 2. WHAT NYXUS IS

A custom **Hyprland-based Arch Linux security-lab distro** — "DARK MIRROR" /
alien-graffiti-space aesthetic — with a bespoke **"Kage Ryu" kernel**. Purpose:
an OSINT / malware-analysis / honeypot workstation that also looks like nothing
else. Login `nyx` / `nyx`, hostname `nyxus`.

---

## 3. ⚠️ HOW THE DESKTOP IS ACTUALLY DELIVERED (the thing that caused the "circles")

**This is the single most important architectural fact. Misunderstanding it is why
the build felt like it went in circles for months.**

The ISO does **not** boot a fully-formed desktop by itself. It ships:

1. **A base airootfs + `/etc/skel`** — the baked configs. `customize_airootfs.sh`
   creates the live user `nyx` and copies `/etc/skel` → `/home/nyx`. This includes
   `hyprland.conf` + its 15 `conf.d/*.conf` shards, all 9 eww `.yuck` bars, the
   theme, wallpaper, keybinds. **The core desktop lives here and is fully offline.**
2. **A first-boot bootstrap** — `nyxus-bootstrap` (Hyprland `exec-once`, every
   login, idempotent via `~/.nyxus/.bootstrapped`). It installs the heavier
   **web-apps / chrome library / Phantom** by running `nyxus_install.sh`, pulled
   either from **production `nyxus-core.replit.app`** (network) or, offline, from a
   **pre-staged cache at `/opt/nyxus-cache`** baked into the ISO.

**Consequences you must internalize:**
- Editing `~/Nyxus-Core/.../etc/skel` changes the **core desktop** (bars, theme,
  wallpaper, keybinds). This is offline-complete and is what boots.
- The **apps** (the Hub's "Main Page / NYXUS Account / App Store / Chrome Library"
  etc.) come from `nyxus_install.sh` + its payload — i.e. from replit or the
  offline cache. Their up-to-date source is `artifacts/api-server/nyxus-scripts/`
  (tracked). `BOOTSTRAP_VERSION` in `nyxus-bootstrap` is still `2026.05.12-r11`
  — **not bumped for July work.** If you need installed systems to re-pull, bump it.
- **The accent color is auto-generated FROM THE WALLPAPER** by
  `~/.local/bin/nyxus-accent-from-wallpaper`. The alien nebula wallpaper is
  blue/purple, so the accent is currently blue (`#1caef2`). **This is not a bug**
  — the owner didn't set it; the wallpaper did. Reversible any time.

---

## 4. WHAT THE BUILD INCLUDES

### ISO
- Output: `iso-builder/out/nyxus-<YYYY.MM.DD>-x86_64.iso` (gitignored, ~9.5–10 GB).
- `iso_name=nyxus`, `iso_label=NYXUS_2026_07` (**must be identical in profiledef +
  all 5 archisolabel refs** or live media won't boot). Only remaining "nyx" is the
  internal source dir name `nyx-profile` (never appears in the ISO).
- Built by `iso-builder/build-iso.sh` (archiso/mkarchiso, UEFI GRUB + BIOS syslinux).
  **Bakes from a throwaway copy** of the profile → never corrupts the repo (fixed
  2026-07-22, commit `fe089345`).
- **Offline cache** at `/opt/nyxus-cache` is staged from `artifacts/api-server/
  nyxus-scripts` (the bake **hard-fails** if the cache would ship without
  `nyxus_install.sh` — no more silent online-only ISOs). This makes first boot work
  with **no internet**.

### Boot experience
- **🐉 Dragon GRUB menu** — centered Kage-Ryu black-dragon theme with real fonts
  (`.pf2`), no "?" boxes. **UEFI ONLY.** A Legacy/BIOS boot uses the plain
  `syslinux` text menu (unthemed) — that's the "normal menu" if you don't pick the
  **"UEFI: <device>"** entry. `EFI/BOOT/BOOTx64.EFI` is present in the ISO.
- **🛸 UFO "Cosmic Arrival" plymouth splash** — the saucer descends with a beam.
  As of 2026-07-22 the saucer art is the **real NYXUS/HYPRLAND graffiti craft**
  (extracted from `livewall/nyxus-livewall-ufo.png`, magenta glow-blob floodfilled
  out), matching the desktop wallpaper. Plymouth reuses it on shutdown/reboot too.

### Kernel — "Kage Ryu Nyxus" (`linux-kage-ryu`)
- XanMod **7.0.12**, Alder-Lake-tuned (i7-12700H), lean `localmodconfig` build
  (~27 MB pkg). Security-lab config: kprobes/uprobes/BPF/BTF, userns/cgroup-bpf/
  overlayfs/CRIU/bridge/veth/vxlan (Docker), KVM-Intel, BBR+FQ, MGLRU, io_uring;
  CPU mitigations stay **available** (never hardcoded off).
- **Selectable at boot; stock `linux` stays DEFAULT** — a bad custom build can
  never strand you.
- Built via `kernel/install-kage-ryu.sh` (on the running system) or
  `cd <kage-ryu repo> && makepkg -sc`. Baked into the ISO **opt-in** with
  `NYX_WITH_KAGE_RYU=1` (off by default; kernel is never compiled inside the bake).
- `scheduler/scx_kage` — sched-ext scheduler; source now committed to the kage-ryu
  repo (branch `feat/scx-kage-scheduler`). Binary staged into the ISO.
- Honest alternatives documented in `kernel/README.md` (linux-zen / linux-hardened
  / stock). Bumping to 7.1.x needs a matching XanMod patch + fresh sha256 (not a
  blind edit).

### Desktop features
- 4 reactive features: **Mood Engine, Machine Whispers, Supernova, Graffiti Memory
  Wall** (built on the `nyxus-sense` bus → `~/.config/nyxus/sense.json`).
- **Reflex layer** coexistence contract: `tintd`=border colors, `beatd`=border
  angle, `pulsed`=event pulses, `wall-fx`=cava→mpv. Don't duplicate these.
- **Hacker mode** (Super+Ctrl+X) transforms the desktop; pauses/resumes the reflex
  layer; `reconcile-boot` clears stale state on login.
- **eww bars** (4) — relaunch ONLY with `nyxus-eww-launch-safe` (one daemon + 4
  bars). Repeated `eww kill`/reload cycles can leave TWO daemons → double bars.
- **Music flip** bottom bar; **NYXUS Hub** (Super-driven quick-settings/apps).

---

## 5. CURRENT STATE (2026-07-22)

### Done + pushed
- Repo un-scattered: one canonical `~/Nyxus-Core`; duplicate deleted; nothing lost.
- Build-iso no longer corrupts the profile (throwaway copy) — `fe089345`.
- **Live-boot post-mortem fixes** — `7ccbaf0b`:
  - Offline cache never ships empty (falls back to in-repo source + hard-fail guard).
  - eww bars **ungated** from the network bootstrap → desktop comes up offline.
  - Splash saucer = real graffiti UFO (both ISO theme + offline-cache source).
- kage-ryu `scheduler/` source committed + pushed (branch `feat/scx-kage-scheduler`).
- `companion-3d/` gitignored by the parent.

### The `nyxus-2026.07.22` stick booted BROKEN — and why (post-mortem)
That stick was built **before** the fixes above (and likely from a partially
corrupted profile). It showed: old wallpaper, blue base theme, no eww bars, no
music flip, `hyprland.conf 600/605 source= globbing no match`, "no internet + no
offline cache" note. All root causes are the §5 fixes. `nyx@nyxus` and the
auto-login live session are **correct/expected** (it's a live ISO, not an install).

### PENDING (do this next)
1. **RE-BAKE** (owner runs): `cd ~/Nyxus-Core/iso-builder && NYX_WITH_KAGE_RYU=1
   sudo ./build-iso.sh`. Safe now — won't corrupt the repo, will refuse to ship an
   empty offline cache.
2. **Re-flash** `/dev/sda` and **boot the UEFI entry**; verify: dragon menu →
   graffiti-saucer splash → full desktop with bars **offline** → apps install from
   cache.
3. Optional leanness: the offline cache pulls `hypr-walls/` (~300 MB) but rotation
   is locked to the alien theme only — prune non-alien walls from the payload if
   size matters.
4. Owner's call: fold `companion-3d` under one roof or keep separate; bump
   `BOOTSTRAP_VERSION` if syncing replit-served apps.

---

## 6. THE BAKE → FLASH → BOOT PROCEDURE (canonical)

```bash
# 1. BAKE (owner, root). Kernel opt-in via the env flag. From a clean repo.
cd ~/Nyxus-Core/iso-builder
NYX_WITH_KAGE_RYU=1 sudo ./build-iso.sh
#   → iso-builder/out/nyxus-<date>-x86_64.iso  (NO post-bake cleanup needed anymore)

# 2. FLASH (owner, root). USB = /dev/sda (SanDisk 57 GB). Internal = /dev/nvme0n1
#    — NEVER put nvme as of=. Double-check the target before Enter.
sudo dd if=~/Nyxus-Core/iso-builder/out/nyxus-<date>-x86_64.iso \
        of=/dev/sda bs=4M status=progress oflag=sync

# 3. BOOT: reboot → boot menu (MSI: F11) → pick the "UEFI: SanDisk" entry
#    (UEFI is required for the dragon menu). Login nyx / nyx.
```

Verify a flashed stick from the agent side (no sudo needed):
`lsblk -o NAME,SIZE,FSTYPE,LABEL /dev/sda` → expect `iso9660` + label `NYXUS_2026_07`
+ an `ARCHISO_EFI` vfat partition. Inspect ISO contents with `bsdtar -tf <iso>`.

---

## 7. DO-NOT-REPEAT GOTCHAS (hard-won)

- **The desktop must NOT depend on the network to come up.** Bars/wallpaper/theme
  are in skel and launch immediately; the app-install layers on after and may never
  block/break the core desktop. (Regressing this = the broken 07-22 boot.)
- **Full-screen GTK/eww overlays MUST be bottom-layer + empty input region
  re-applied per-frame**, or they TRAP the desktop (the "whispers" incident forced
  multiple hard resets). Never OVERLAY-layer a full-screen input surface.
- **iso_label identical** in profiledef + all 5 archisolabel refs, or no boot.
- **Dragon menu is UEFI-only** — Legacy boot = plain text menu (not a bug).
- **Accent follows the wallpaper** — "it turned blue on its own" is expected.
- **eww**: one daemon via `nyxus-eww-launch-safe`; watch for double bars.
- **Restore-before-bake is obsolete** now that the bake uses a throwaway copy — but
  if you ever see the repo `nyx-profile` go root-owned/dirty after a bake, the fix
  regressed; the owner must `sudo chown -R cosmic:cosmic` it, then
  `git checkout -- iso-builder/nyx-profile/ && git clean -fdx -- iso-builder/nyx-profile/`.

---

## 8. KEY PATHS

- ISO builder: `iso-builder/build-iso.sh`, profile `iso-builder/nyx-profile/`
- Baked desktop: `iso-builder/nyx-profile/airootfs/etc/skel/.config/{hypr,eww,nyxus}`
- Plymouth theme: `iso-builder/nyx-profile/airootfs/usr/share/plymouth/themes/nyxus/`
- GRUB dragon: `iso-builder/nyx-profile/grub/{grub.cfg,fonts/,themes/nyxus/}`
- Apps / offline payload SOURCE: `artifacts/api-server/nyxus-scripts/`
  (`nyxus_install.sh`, `nyxus-bootstrap`, `nyxus-wait-bootstrap`, `eww/`,
  `plymouth/`, `hypr-walls/`, `livewall/`)
- Kernel recipe: `kernel/` (README + `install-kage-ryu.sh` + `nyxus-bbr.conf`)
- Other docs: `docs/` (KERNEL_ISO, REBOOT_SURVIVAL, INSTALL, THEME, KEYBINDS, …),
  root `STATUS.md`, `ROADMAP.md`, `SHIPPING.md`.

---

*Keep this file honest and current. The next agent — and the owner's sanity —
depends on it.*
