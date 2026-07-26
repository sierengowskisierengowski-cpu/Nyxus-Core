# NYXUS — AGENT HANDOFF & BUILD STATE (read this FIRST)

> **Last updated: 2026-07-25 evening (bottom-bar eww redesign + audio detection on main)** · Owner: Joseph A. Sierengowski (`nyx` / `nyxus`)
> If you are a new agent picking up NYXUS: **read this entire file before touching
> anything.** It exists because this project got scattered across duplicate clones
> and the same problems got re-diagnosed and re-broken multiple times, costing the
> owner a lot of time and money. Do not veer off into a different approach. Keep the
> flow, and **update this file as you work** so the next agent re-derives nothing.
>
> **Live USB report + full sweep:**  
> [`docs/LIVE_BOOT_AUDIT_2026-07-25.md`](./docs/LIVE_BOOT_AUDIT_2026-07-25.md)
>
> **Last ~day of building (story + done/open):**  
> [`docs/BUILD_DAY_BRIEF_2026-07-24.md`](./docs/BUILD_DAY_BRIEF_2026-07-24.md)
>
> **Deep consistency audit (revised evening):**  
> [`docs/DEEP_BUILD_AUDIT_2026-07-24.md`](./docs/DEEP_BUILD_AUDIT_2026-07-24.md) —
> bake wipe gaps (`eww/assets`, `hypr/scripts`) fixed via **#76** (on `main`).
>
> **Theme + Settings workstream:**  
> [`docs/ALIEN_NEON_SETTINGS_BRIEF.md`](./docs/ALIEN_NEON_SETTINGS_BRIEF.md) then
> [`docs/ALIEN_NEON_SETTINGS_AUDIT.md`](./docs/ALIEN_NEON_SETTINGS_AUDIT.md) /
> [`docs/PRE_BAKE_CLEANUP_AND_SETTINGS.md`](./docs/PRE_BAKE_CLEANUP_AND_SETTINGS.md).
> Stay-as-is: Bifrost / GodsApp / Meli / Arsenal.

---

## WHERE WE STAND — 2026-07-25 · late (eww boombox + audio · bake GO)

> Short status for the owner. Detail lives in §5 / §6 below. **Update this block
> whenever bake readiness changes.**

| | |
|---|---|
| **Repo** | `~/Nyxus-Core` · **`main`** |
| **HEAD** | `d7f8be99` / tip after `8013121a` — confirm with `git rev-parse --short HEAD` |
| **Open PRs** | **none** (evening eww pushed straight to `main`) |
| **Live-boot audit** | [`docs/LIVE_BOOT_AUDIT_2026-07-25.md`](./docs/LIVE_BOOT_AUDIT_2026-07-25.md) |
| **Repo state for bake** | ✅ **GO** — live-boot fixes + saucer center/flip + side-rail glass + alien boombox + universal audio/`CAVA_BASS`. NS↔skel lockstep. `verify-profile` PASS. |
| **Last ISO on disk** | `nyxus-2026.07.25` @ **15:00** — **STALE** vs evening tip. Rebake before flash. |
| **Kage-Ryu on stick** | ✅ splash / boot path worked on prior live USB |
| **Running desktop kernel** | Stock on builder; Kage on stick |
| **Gates** | ✅ `iso-builder/verify-profile.sh` |

### 🔦 ALIEN NEON palette/brand audit — this pass (2026-07-24 PM)

**Every shipped surface is now the ONE ALIEN NEON palette** (no gold `#d4b87a`,
no cream, no old violet `#a06bff`, no `DARK MIRROR`/`OBSIDIAN PRISM` brand)
outside the deliberate carve-outs (Arsenal/Bifrost/GodsApp/Meli/Security Center,
`nyxus_palette.py` ban-statement, `docs/legacy-visuals.md` history).

- **Shell apps** — killed local gold; `nyxus_account/backup/clipboard/drop/files/updater`
  now import `ACCENT_PRIMARY` (prism violet, fallback `#7d3dff`); `nyxus_toast`
  accents → canon green/orange/red/cyan; desktop icon-select + rofi context menu → violet.
- **Brand** — `DARK MIRROR`/`OBSIDIAN PRISM` → **ALIEN NEON** across the whole
  desktop (login `issue`/`motd`, eww ticker + boot-splash label, `.desktop`
  tooltips, cursor theme, hypr/eww/greetd/sddm/wlogout, locale `.po`, bootstrap,
  install.sh, cava, btop, nyxus-home HUD, asset generators, calamares slideshow).
- **Installer** — Calamares branding synced to the ALIEN-NEON `show.qml`; stale
  gold `stylesheet.qss` cleared.
- **Build wiring (key finding)** — `build-iso.sh` regenerates skel + `/opt/nyxus`
  from `artifacts/api-server/nyxus-scripts` (**NS = source of truth**) at bake.
  NS lagged the baked profile, so a bake would have **stripped the Welcome-
  Transmission windowrules** and shipped the old wlogout/greeter — synced NS back
  up so the offline payload matches what boots. Bumped `BOOTSTRAP_VERSION` →
  `2026.07.24-r14-alien-neon` so installed systems re-pull the retheme.
- **verify-profile.sh** — fixed a stale assertion (grepped `nyxus welcome` space
  vs the real `nyxus-welcome` hyphen exec-once) that was **failing the gate on `main`**.

**Deferred (documented, NOT bake-blocking):**
SDDM `Main.qml` offline-payload copy drifts from the baked theme (fallback
greeter, not the live greetd path). WaybarMockup `#/waybars` **deleted** this
pass. Settings Phase 3/4 deepened on branch (Kernel/Kage + MINIMAL/PARTIAL
controls; `APP_REV` r16) — **on-device QA still required** after bake.

### 🧹 Pre-bake cleanup + Settings coverage — same branch (2026-07-24 PM)

Roadmap + owner-confirm list: **[`docs/PRE_BAKE_CLEANUP_AND_SETTINGS.md`](./docs/PRE_BAKE_CLEANUP_AND_SETTINGS.md)**.

- **Stripped dead cruft** (safe): 32 duplicate app `.py` from committed
  `skel/.config/nyxus/` (apps run from `~/.nyxus`→`/opt/nyxus`; kept the
  screensaver chain), stale `.bootstrapped` + `NYXUS_STATUS.md`, orphan
  `wlogout-theme/`. Riskier deletions (download-portal-mapped orphans,
  `dist/` bake-host tree) are listed as owner-confirm — **do NOT** delete
  the `nyxus-recovery-*`/`sddm-themes` cluster (it's live via the shipped
  `pam.d/sddm-recovery-snippet`).
- **Settings master coverage + deepen:** 57 sections; KernelPage =
  Kage-Ryu + stock rescue; MINIMAL/PARTIAL pages deepened (`APP_REV` r16);
  `empty_group` bug fixed; helpers/fastfetch/safemode/orphans cleaned per
  roadmap. **GUI pages still need on-device QA** (`nyxus-settings`).

**Owner next:** merge PR #75 → clean idle repo → `sudo ./build-iso.sh` →
flash → verify (`/etc/nyxus-build`, bars, welcome, Kage/stock); QA Settings
(esp. Kernel + new shell sections + deepened pages).  
**Next agent:** on-device Settings QA notes + any bake regressions only.

### 🛸 Bottom-bar eww redesign + audio detection — this pass (2026-07-25 evening)

Owner reported a live-boot punch list (login-screen background missing, ~5min
wallpaper delay, saucer clock off-center, rainbow kitty, black box around eww
bars, arsenal apps hanging ~90s each). Investigated each individually instead
of assuming they were all one thing — three turned out to be **already-correct
code** (kitty.conf, greeter background wiring, eww bar CSS all verified clean
via a live Hyprland session on the builder box — see §0 note below on how).
Two were real bugs, now fixed. Commits `4c7b52ca`, `bb11fb6a`, `99aa77af`,
`8013121a`, all pushed:

- **Login screen had no background on a truly fresh bake** — `nyxus-greeter`
  runs as the unprivileged `greeter` user and needs `/var/lib/greetd` +
  `/var/cache/regreet` to exist, but neither `customize_airootfs.sh` nor
  regreet's own tmpfiles rule (which covers different paths) ever created
  them. `greeter` can't create dirs under root-owned `/var/lib`/`/var/cache`
  itself, so every `mkdir`/`cp` in the script silently no-op'd. Fixed:
  `customize_airootfs.sh` now pre-creates + chowns both, as root, at bake time.
- **Wallpaper ~5min blank on first boot** — the exec-once wiring
  (`command -v nyxus-live-wallpaper && nyxus-live-wallpaper auto || nyxus-wallpaper-autostart`)
  never fell through to the fast static-image script (the command always
  exists), so first boot blocked the whole background on a synchronous
  ffmpeg render of the flagship loop. Fixed: show the still immediately,
  render in the background, swap to the animated loop once ready.
- **nyxus_screensaver.py redesigned** — was plain white text on a dim
  wallpaper (didn't even use the ALIEN NEON palette it imports). Now a glass
  card matching hyprlock's Prism HUD language, with a violet↔magenta
  breathing pulse. Verified live with a real screenshot.
- **Saucer clock/music screen recentred** — measured the actual
  `nyxus-saucer-band.png` pixel-by-pixel: the transparent cockpit window
  sits ~31px *below* image centre, not above as the old margin assumed (that
  margin had been re-guessed twice already against different art revisions
  and drifted wrong each time). Fixed with a measured `margin-top: 10px`
  instead of another guess. Flip transition swapped `crossfade` →
  `rotate-left-right` (GTK's real card-flip, not a fade standing in for one).
- **Left/right rail "plain white box" look** — `.float-island` was painting
  its own faint single-hue rim and explicitly stripping the pills' real
  per-hue `obsidian-vessel` glass/glow styling (deep fill, neon hairline, 2px
  accent top-rule, real glow — already built, just suppressed) down to
  transparent. Removed the override; the existing rich design shows through.
- **Arsenal apps (CIPHER/Forge/RedForge/GSL/Trainer/Bifrost) hanging ~90s
  each with a cryptic port-timeout message** — root cause: they need
  `~/GowskiNet-Vault`/`~/Projects/bifrost`, dev-machine-only projects never
  shipped on live media. `nyxus-app-shell` now runs the starter synchronously
  and surfaces its actual failure reason immediately instead of blindly
  polling the port for 90s (`nyxus-app-shell/src-tauri/src/lib.rs`, rebuilt +
  redeployed to the airootfs binary). Decision: **hide/fail-fast on live
  media**, not attempt to bundle the vault. AXIOM found to have **zero**
  `nyxus-webapp` backend wired at all (separate, deeper gap, now fails fast
  too instead of hanging).
- **Universal audio detection** — `player.sh` only checked MPRIS
  (`playerctl`), so the saucer never flipped to the music face for players
  that don't implement it (bare `mpv` without `mpv-mpris`, verified live).
  Added a `pactl`-based fallback: any live PipeWire/Pulse sink-input now
  triggers "Playing" with a generic title if MPRIS finds nothing.
- **`CAVA_BASS`** — new 0-100 live scalar pushed from `cava.sh` every frame
  (loudest bar across the spectrum, not a fixed low-frequency index — tested
  live against an 80Hz tone that peaked in bars 4-9, not 0-1, so "bass = low
  bars" doesn't hold generally). Currently drives the CSS boombox speaker
  dots' size/glow; this plumbing is reusable regardless of what replaces the
  visual layer (see below).

**⚠️ IN PROGRESS, NOT WIRED IN — 3D saucer + boombox (owner's call, this
session):** the CSS-only boombox restyle in `99aa77af` was a stopgap; the
owner wants real 3D-modelled assets instead, same pipeline as the alien
companion (Meshy → render hero shot → wire in as an image, same as
`nyxus-saucer-band.png`). Live-3D-in-Godot was discussed and explicitly
rejected in favor of image-based for this — see the conversation, not
re-litigated here. **Status:** owner generated 4 new GLB models, dropped in
`~/Downloads/`:
`Meshy_AI_nyxus_oblong_saucer_3_0725230844_image-to-3d-texture.glb`,
`Meshy_AI_nyxus_boombox_3d_fina_0725230853_image-to-3d-texture.glb`,
`Meshy_AI_nyxus_left_dock_3d_0725230915_image-to-3d-texture.glb`,
`Meshy_AI_nyxus_right_dock_3d_0725230902_image-to-3d-texture.glb` (left/right
NOT started yet — owner said do saucer+boombox first). Rendered hero shots
for saucer + boombox with Blender (`blender --background --python`, EEVEE,
transparent PNG) — **Blender 5.1.2 is installed on the builder box**, this is
the render pipeline now, not a live Godot overlay. Found the boombox's true
front by rendering a full 12-angle turntable rather than guessing an azimuth
(front-facing render is `az=225 el=16 dist=2.5 lens=34`, see
`render_hero.py`-style script in conversation — not yet committed anywhere,
was a scratch job-tmp script). **Not yet done:** neither render has been
saved into the repo or wired into `saucer_base`/`bar_hub_music` — that's
still the flat `nyxus-saucer-band.png` shipping today. **Next agent, if
picking this up:** (1) get the final hero renders from wherever they landed
(job scratch dir, or re-render from the GLBs in Downloads — script logic is
in this session's transcript), (2) crop/trim transparent margins, (3) wire
in as background-image the same way `saucer_base` does today, (4) figure out
where the display/text overlay sits on the new art (old measurement approach
— pixel-scan the PNG for the transparent/dark region — won't directly apply
to a differently-shaped asset), (5) **hard requirement, owner was burned by
this before:** whatever click-handling exists must keep hub-open and
transport-controls (prev/play/next) as separate hit-regions — do NOT let a
transport click fall through to hub-open. (6) Left/right dock 3D (rail
redesign) — models exist, zero integration work started.

**⚠️ Also not committed:** none — everything discussed in this session that
reached a working state is committed and pushed as of `8013121a`. The 3D
work above is scratch-only (Blender renders in job tmp, never copied into
the repo) — treat it as **not started from the repo's perspective**.

### Bake command (reminder)

```bash
# Repo must be clean: git status  →  nothing to commit
cd ~/Nyxus-Core/iso-builder && sudo ./build-iso.sh
# → iso-builder/out/nyxus-<YYYY.MM.DD>-x86_64.iso
```

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
- **ALIEN NEON palette is LOCKED (2026-07-23).** Canonical preset = `prism` in
  `~/.config/nyxus/accent.json` / skel:
  violet `#7d3dff` · magenta `#ff2dad` · neon green `#39ff14` · orange `#ff8a1e`
  (+ fixed cyan `#2bd2ff` · red `#ff2d55` · yellow `#ffe600` · orchid `#e367ff`).
  **`follow_wallpaper` is OFF.** Do NOT re-enable wallpaper→accent extraction —
  that drift (old wallpaper blues / cream "Sprint E") is exactly how the desktop
  kept losing its alien look. Apply via `nyxus-apply-accent prism`.
- **Cream `#f4ead5` is banned.** Cool white `#eef2fa` on void `#05060a` only.

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
- **Kage-Ryu is the PRIMARY/default kernel (rev 2026-07-23)** — on the live USB
  (so you validate the real kernel before installing) AND on the installed
  system. Stock `linux` is kept ONLY as a rescue entry so a bad Kage-Ryu boot
  can never strand you. `linux-lts` / `linux-zen` / `linux-hardened` were
  dropped from `packages.x86_64` (focused custom-kernel distro).
  **⚠ 2026-07-23:** older `7.0.12` pkgs lacked iso9660/squashfs/loop. PKGBUILD
  patched; rebuilt pkgs present ~08:53 EDT 2026-07-24 — **still verify** on stick
  before trusting Kage as live default (stock rescue if iso9660 fails).
- Built via `kernel/install-kage-ryu.sh` (on the running system) or
  `cd <kage-ryu repo> && makepkg -sc`. Baked into the ISO **BY DEFAULT**
  (`NYX_WITH_KAGE_RYU` defaults to `1`; kernel is never compiled inside the
  bake). Set `NYX_WITH_KAGE_RYU=0` to opt OUT and bake a stock-only ISO.
- **The bake HARD-FAILS if the prebuilt packages are missing** (so it can never
  silently ship kernel-less — the 2026-07-22 no-kernel bake can't recur). The
  prebuilt packages (`linux-kage-ryu-7.0.12` + headers, ~28M/38M) already exist
  at `~/Projects/arch-custom-kernel/linux-kage-ryu/` and are found automatically.
- **How it's wired:** `build-iso.sh` stages the packages into a profile-local
  `[nyxus-local]` repo, appends them to `packages.x86_64`, and rewrites the three
  live boot menus (grub / systemd-boot / syslinux) so Kage-Ryu is entry #0 and
  stock is a labelled rescue — **all in the throwaway profile copy**, so the
  repo's static menus stay stock-safe. On install, Calamares copies both kernels
  and `nyxus-set-grub-default-kage` (shellprocess) flips the installed GRUB
  saved-default to Kage-Ryu.
- `scheduler/scx_kage` — sched-ext scheduler; source committed to the kage-ryu
  repo (branch `feat/scx-kage-scheduler`). Binary staged into the ISO.
- Bumping to 7.1.x needs a matching XanMod patch + fresh sha256 (not a blind edit).

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

## 5. CURRENT STATE (2026-07-24)

> **See also the top-of-file [WHERE WE STAND](#where-we-stand--2026-07-24--1146-edt) block**
> for the bake-ready snapshot (time-stamped).

### Last-day chronicle (moved)

**Full story of Jul 23–24 building** (timeline, done/open, gotchas, PRs):

→ [`docs/BUILD_DAY_BRIEF_2026-07-24.md`](./docs/BUILD_DAY_BRIEF_2026-07-24.md)

Do **not** re-expand a second diary here — append new surprises to the day brief
or to WHERE WE STAND above.

### The `nyxus-2026.07.22` stick booted BROKEN — and why (post-mortem)
Two overlapping causes: (1) that stick was baked from a **partial/stale** profile
(missed the ungate-bars fix), and (2) the deeper bugs above (dead Replit + install
`set -e`/`clear` + eww.scss + wallpaper path). All are now fixed in the repo but
**not yet in a baked ISO** — needs a fresh bake. `nyx@nyxus` + auto-login are
correct/expected (it's a live ISO, not an install).

### ⛔ Kage live-ISO substrate (status 2026-07-24 midday)

**History:** QEMU 2026-07-23 confirmed default Kage entry died with
`mount: unknown filesystem type 'iso9660'` (lean config stripped iso9660/squashfs/loop).

**Now:** PKGBUILD forces those options; rebuilt `7.0.12` pkgs on disk (~08:53 EDT).
Owner reported kernel done. **Still verify on the next baked stick** — if Kage
fails again, boot **"stock linux (rescue)"** and re-check module config.

### Live-boot fixes (#71 → #72) — summary

Landed on `main` via PR **#72** after a near-miss ( #71 merged to a branch that
was already on main). Covers: eww first-paint (`npx sass` skip), black-box path,
hyprpm header guard, ALIEN NEON `/etc/issue` + bashrc stamp, jeTT `/home/nyx`
de-leak, `BOOTSTRAP_VERSION` `2026.07.24-r13-fixes`.

Detail + timeline → day brief. Flashed `nyxus-2026.07.24` @ 03:05 was **before**
these commits — rebake required.

### Pending / owner queue

1. ~~Confirm `main` has #71~~ **DONE** via PR #72.
2. **RE-BAKE** from idle `main`: `cd ~/Nyxus-Core/iso-builder && sudo ./build-iso.sh`  
   **Do not flash** the 03:05 `nyxus-2026.07.24` ISO for today’s work.
3. **Re-flash** — re-check `lsblk` (USB letter moves). Boot **UEFI**. Verify Kage
   mounts ISO (or use stock rescue) → splash → desktop → stamp in `/etc/nyxus-build`.
4. ~~W6 arsenal/reactive shards~~ **DONE** — still verify post-bake with `unsquashfs`.
5. ~~W1 file_permissions~~ **DONE**.
6. **Still open on stick QA:** greeter/lock/UFO/welcome-note; home backup to Ventoy.
7. **Deferred hygiene:** ~33 non-boot Replit refs; prune stale remotes / old ISOs in `out/`.
8. Owner’s call: companion mascot; fold `companion-3d`.

### Copilot Deep Pre-Bake Audit (2026-07-24) — stored here (no separate memory store)

**ALIEN NEON + Settings completeness checklist (owner tracking):**
[`docs/ALIEN_NEON_SETTINGS_AUDIT.md`](./docs/ALIEN_NEON_SETTINGS_AUDIT.md)
— full counts + lists for (1) surfaces not ALIEN NEON, (2) empty/minimal/partial
Settings pages, (3) apps with no Settings section, (4) session features missing
from Settings. Regenerated 2026-07-24 from live `~/.nyxus` + desktop entries.
**Stay as-is (no ALIEN NEON / no Settings required):** Bifrost, GodsApp, Meli,
Arsenal/security lab apps (CIPHER/Forge/GSL/RedForge/Trainer/AXIOM/c2/Shield/…).

Full GO/NO-GO from Copilot audit. Cross-checked against `main` @ `fb63e2aa` (+ #71 on main).

| Gate | State |
|---|---|
| **C1** Rebuild Kage-Ryu (`ISO9660_FS` + `SQUASHFS` + `BLK_DEV_LOOP` =y); QEMU verify | ⚠️ **PKGS PRESENT** (`7.0.12` @ 08:53 EDT 2026-07-24; PKGBUILD enables live FS). Owner said kernel done; **still verify** mount before trusting. `makepkg` idle. |
| Bake from clean committed idle `main` | ✅ **READY NOW** — tip after day-brief docs; `git rev-parse --short HEAD` |
| Boot labels / offline-cache / kernel hard-fail guards | ✅ intact |
| Palette lock (ALIEN NEON; cream / `#a06bff` clean in desktop trees) | ✅ clean |
| Desktop delivery (skel + bootstrap + `/opt/nyxus-cache`) | ✅ intact |
| Welcome Transmission + Dream Protocol | ✅ **DONE** on `main` (`1af1a65f`) |
| ALIEN NEON Phase 1 (PR #73) | ✅ **MERGED** on `main` |
| **W1** Regenerate `profiledef.sh` `file_permissions` (~59 `/usr/local/bin` missing) | ✅ **DONE 2026-07-24** (177 entries regen from airootfs) |
| **W2** `verify-profile.sh`: label consistency + ban `#f4ead5` + kernel-policy + cache/daemon asserts | ⚠️ cream ban **DONE**; other W2 asserts still deferred |
| **W3** Dead Replit host fallbacks in chrome/stickies/sysmon/… | ℹ️ deferred (~33 non-boot) |
| **W4** `/home/cosmic` in jeTT/audit/arsenal `.env.example` | ℹ️ jeTT + audit **clean on current main** (#71); arsenal `.env.example` still deferred |
| **W5** `dunstrc` hard-codes `/home/nyx` icon_path | ℹ️ OK on live ISO; de-leak on install |
| **W6 (this session — Copilot missed)** bake wipes `nyxus-arsenal-apps.conf` from skel; never `source=`d | ✅ **DONE 2026-07-24** — bake shard list + `source=` in hyprland (NS+skel); also ships `nyxus-reactive.conf` |
| I1–I5 | ℹ️ cleanup / cosmetic (orphan greeter, dup python tree, Forge `#0a0a14`, stale BUILD_ID stubs restamped at bake) |

**Verdict (2026-07-24 ~11:50 EDT):** **GO for bake** from idle `main`.
Kage pkgs present; verify mount on stick (stock rescue fallback). Old ISO @ 03:05
is **not** this tip — rebake. Full day story → [`docs/BUILD_DAY_BRIEF_2026-07-24.md`](./docs/BUILD_DAY_BRIEF_2026-07-24.md).

**After bake verify:** `cat /etc/nyxus-build` → matches bake tip; label `NYXUS_2026_07`; UEFI Kage or stock rescue; desktop offline; bars OK; welcome transmission once.

---

## 5b. BRIEF — ALIEN NEON LOCK (2026-07-23 evening)

**What shipped to `main` this round:**
1. **Canonical palette** — `accent.json` active=`prism`, `follow_wallpaper=false`.
   Primary violet `#7d3dff`, secondary magenta `#ff2dad`, warn orange `#ff8a1e`,
   ok neon green `#39ff14`. Fixed neons for cyan/red/yellow/orchid used in
   terminals, borders, HUD, glow.
2. **Repo-wide re-skin** — purged cream `#f4ead5` + wallpaper-drift blues
   (`#1caef2`/`#6526ff`/…) from skel, artifacts, arsenal UI, GRUB/calamares/
   verify-profile. Window border sweep = violet→magenta→cyan→green.
3. **Terminals** — kitty + alacritty = ALIEN NEON ANSI (cool white default text;
   neon only on real ANSI). Alacritty dim colors use `0xAARRGGBB` (not `#rrggbbaa`).
   `nyxus-glow` palette updated to the same neons.
4. **Alien walls only** — default `wallpaper.conf` → `nyxus-urban-alien`;
   greeter `wall-rotation.list` alien-only; `nyxus-rotate-walls` searches
   `rotation/` + alien FALLBACK; autostart DEFAULT points at urban-alien.
5. **Install code-1 hardened** — optional wall dl soft-fails; SDDM never fails
   the install (greetd is live greeter); post-install wallpaper prefers
   urban-alien (not void-vortex); **summary no longer `exit 1`** on optional
   misses (that abort was killing first-boot theming).
6. **Live session** — palette applied on the owner's Hyprland session
   (`nyxus-apply-accent prism`); backup at
   `~/nyxus-palette-live-backup-*.tar.gz`.

**What does NOT update until the next bake:** greeter/splash/ISO skel on the
USB stick. Live session already shows ALIEN NEON; stick needs rebake+reflash.

**2026-07-23 (same evening, purge pass):** Old accent presets (aurora/ember/verdant/
violet/rose/ice/noir/wallpaper) **deleted** from `accent.json` — only `prism`/
ALIEN NEON remains selectable. Every leftover old-family hex (`#a06bff`,
`#ff7849`, `#ff4d6b`, cream-era void `#0a0a14`/`#050308`, …) remapped. All
"Sprint E" / "cream accent" labels renamed to ALIEN NEON. Live session
re-synced. Cursor theme name `NYXUS-Aurora` is unrelated (kept).

**Owner next:** rebuild Kage-Ryu pkgs (iso9660/squashfs/loop) → commit clean →
`sudo ./build-iso.sh` → flash → boot UEFI → verify.

---

## 6. THE BAKE → FLASH → BOOT PROCEDURE (canonical)

```bash
# 1. BAKE (owner, root). Kage-Ryu is baked BY DEFAULT. From a clean repo.
cd ~/Nyxus-Core/iso-builder
sudo ./build-iso.sh                    # Kage-Ryu primary + stock rescue
# sudo NYX_WITH_KAGE_RYU=0 ./build-iso.sh   # stock-only debug ISO (opt out)
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

- **Kage-Ryu MUST keep live-media FS support** (`CONFIG_ISO9660_FS`,
  `CONFIG_SQUASHFS`, `CONFIG_BLK_DEV_LOOP`, preferably `CONFIG_BLK_DEV_DM` /
  `CONFIG_UDF_FS`). A lean/localmodconfig pass that drops them makes the
  default live entry unbootable (`unknown filesystem type 'iso9660'`). Catch
  this in QEMU (`-kernel` + virtio ISO + `console=ttyS0`) before flashing.
- **The desktop must NOT depend on the network to come up.** Bars/wallpaper/theme
  are in skel and launch immediately; the app-install layers on after and may never
  block/break the core desktop. (Regressing this = the broken 07-22 boot.)
- **Full-screen GTK/eww overlays MUST be bottom-layer + empty input region
  re-applied per-frame**, or they TRAP the desktop (the "whispers" incident forced
  multiple hard resets). Never OVERLAY-layer a full-screen input surface.
- **iso_label identical** in profiledef + all 5 archisolabel refs, or no boot.
- **Dragon menu is UEFI-only** — Legacy boot = plain text menu (not a bug).
- **Accent does NOT follow wallpaper** (locked 2026-07-23). Active preset =
  `prism` / ALIEN NEON. `follow_wallpaper: false`. Cream `#f4ead5` is banned.
- **eww**: one daemon via `nyxus-eww-launch-safe`; watch for double bars.
- **Restore-before-bake is obsolete** now that the bake uses a throwaway copy — but
  if you ever see the repo `nyx-profile` go root-owned/dirty after a bake, the fix
  regressed; the owner must `sudo chown -R cosmic:cosmic` it, then
  `git checkout -- iso-builder/nyx-profile/ && git clean -fdx -- iso-builder/nyx-profile/`.
- **Alacritty rejects 8-digit `#rrggbbaa` hex** — use `0xAARRGGBB` (e.g.
  `0x8CEEF2FA`) or 6-digit `#rrggbb`. Hitting `#eef2fa8c` pops a red parse error.

---

## 8. KEY PATHS

- ISO builder: `iso-builder/build-iso.sh`, profile `iso-builder/nyx-profile/`
- Baked desktop: `iso-builder/nyx-profile/airootfs/etc/skel/.config/{hypr,eww,nyxus}`
- Plymouth theme: `iso-builder/nyx-profile/airootfs/usr/share/plymouth/themes/nyxus/`
- GRUB dragon (live USB boot): `iso-builder/nyx-profile/grub/{grub.cfg,fonts/,themes/nyxus/}` — ALIEN NEON theme, black-dragon bg, DejaVu fonts (the set `grub.cfg` loads). Installed-disk GRUB theme mirror: `iso-builder/nyx-profile/airootfs/usr/share/grub/themes/nyxus/` (same dragon bg; Unifont, which installed GRUB ships).
- Apps / offline payload SOURCE: `artifacts/api-server/nyxus-scripts/`
  (`nyxus_install.sh`, `nyxus-bootstrap`, `nyxus-wait-bootstrap`, `eww/`,
  `plymouth/`, `hypr-walls/`, `livewall/`)
- Kernel recipe: `kernel/` (README + `install-kage-ryu.sh` + `nyxus-bbr.conf`)
- Other docs: `docs/` (KERNEL_ISO, REBOOT_SURVIVAL, INSTALL, THEME, KEYBINDS, …),
  root `STATUS.md`, `ROADMAP.md`, `SHIPPING.md`.

---

*Keep this file honest and current. The next agent — and the owner's sanity —
depends on it.*
