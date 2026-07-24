# NYXUS — Pre-Bake Cleanup + Settings Completion Roadmap

> Started 2026-07-24 PM · branch `cursor/pre-bake-cleanup-settings-ac8f`.
> Companion to `HANDOFF.md`, `docs/ALIEN_NEON_SETTINGS_AUDIT.md`.
> Goal: finish stripping dead cruft (so nothing stale gets baked in) and
> drive the master Settings app to full coverage.

---

## A. What's DONE (this branch)

### Theme / brand (earlier commits / PR #74)
- Whole-build ALIEN NEON palette + brand purge (gold `#d4b87a`, cream,
  `DARK MIRROR`, `OBSIDIAN PRISM`) — see HANDOFF "WHERE WE STAND".

### Dead-code stripping
- **Removed 32 dead duplicate app `.py`** from committed
  `skel/.config/nyxus/` (apps actually run from `~/.nyxus`→`/opt/nyxus`
  symlinks; only `nyxus-screensaver` uses the `~/.config/nyxus/` path, so
  the screensaver chain — `nyxus_screensaver.py`, `nyxus_palette.py`,
  `nyxus_matrix_saver.py` — was kept).
- Removed stale `skel/.config/nyxus/.bootstrapped` (wrong path + ancient
  version) and the `NYXUS_STATUS.md` dev diary.
- Removed orphan `artifacts/api-server/nyxus-scripts/wlogout-theme/`
  (unused dup of the root `wlogout-style.css`/`wlogout-layout`).
- **C2 orphans removed** (with `download.ts` entries):
  `nyxus-notif-status.sh`, `nyxus-greetd.toml`, `hyprland.lua`.
- **`nyxus-waybar-stars.png` kept** — it is a live wallpaper via the
  bake `nyxus-*.png` glob + `manifest.tsv` (moved to WALLPAPERS section
  in `download.ts`; not a waybar chrome asset).
- **C5 safemode** — dropped dead `waybar` fallback; safemode now starts
  `alacritty` only (NS + skel conf.d lockstep).
- **C5 fastfetch** — `build-iso.sh` now stages
  `NS/fastfetch/{config.jsonc,nyxus-logo.txt}` →
  `skel/.config/fastfetch/` (package already in `packages.x86_64`).
- **WaybarMockup.tsx deleted** — route `#/waybars` removed; nav pills
  now point at `#/build` (Build Manifest). Non-shipping web cruft gone.
- **Tier B/C helpers** — `build-iso.sh` installs from NS when present
  (`nyxus-kernel-switch`, virt/proton/distrobox/usbguard/secboot/doh/
  mac-randomize). NS copies seeded from airootfs for lockstep.

### Settings — master coverage + deepen (`APP_REV` r16)
- **Added 9 missing shell-feature sections** (all wired to real CLIs,
  graceful `have()`/`empty_row` fallbacks, standard footer):
  Compositor, Bars & Widgets, Live Wallpaper, Lock Screen, Screensaver &
  Idle, Reactive FX, Mission Control, Session Modes (Hacker/Ghost/Panic),
  Firewall. Settings has **57 sections**, every one mapped to a page.
- **KernelPage** retargeted to **Kage-Ryu (primary) + stock linux
  (rescue)** — dropped lts/zen/hardened; surfaces `/etc/nyxus-build` +
  `nyxus-set-grub-default-kage`. Matching `nyxus-kernel-switch` rewrite.
- **Bugfix:** defined missing `empty_group()` helper (was crashing
  App Permissions / Language early-returns).
- **Deepened MINIMAL/PARTIAL pages** with real controls (not stubs):
  Gaming (GameMode/MangoHud/Gamescope), Containers (enter/stop/rm),
  Virt (start/shutdown domains), USB (allow/block devices), Cameras
  (mute + jump to App Permissions), Controllers (per-device Test),
  Editors (multi-mime defaults), Color (import/jump Display), Drop
  (start/stop daemon + list available), Sync (reload/edit account.json),
  About (bake stamp), Appearance (killed `nyx-wip-body`), Parental
  (honest empty-state copy).
- `SectionPage._jump_to` shared so any page can cross-link sections.

---

## B. Settings — remaining (on-device QA + polish)

GTK cannot run headlessly here. After bake/flash, owner should walk
`nyxus-settings` and tick:

### B1. MINIMAL — largely deepened; verify on device
`app_perms`, `cameras_mics`, `color`, `containers`, `controllers`, `doh`,
`drop`, `editors`, `gaming`, `kernel`, `mac_random`, `secboot`, `sync`,
`usb_firewall`, `virt`.

### B2. PARTIAL — many already substantive; spot-check
`about`, `accessibility`, `assistant`, `backup`, `bluetooth`, `clipboard`,
`datetime`, `dock`, `keyboard`, `language`, `mouse`, `notifications`,
`parental`, `plymouth`, `printers`, `record`, `security`, `sound`,
`sounds`, `storage`, `wallpaper`.

### B3. SUBSTANTIVE — polish only (on device)
`appearance`, `apps`, `display`, `loginscreen`, `network`, `power`,
`privacy`, `updates`, `users`.

### B4. Keep verifying against the app inventory
When a NEW app/feature lands, add its Settings section in the same PR.
Stay-as-is (no Settings needed): Arsenal/lab, Bifrost, GodsApp, Meli.

---

## C. Dead-code stripping — remaining notes

### C1. CORRECTION — do NOT delete (they are LIVE)
- `nyxus-recovery-setup` / `nyxus-recovery-register` / `nyxus-recovery-auth`
  and `sddm-themes/nyxus/Main.qml`: recovery auth is wired into the
  **shipped** `etc/pam.d/sddm-recovery-snippet`. Keep the whole cluster.

### C2. ✅ DONE (this pass)
Orphans removed + `download.ts` updated. `hyprland.lua` gone (restore
script still quarantines any live `~/.config/hypr/*.lua` — fine).

### C3. Bake-host hygiene (not committed, but poisons a local bake)
- `artifacts/api-server/dist/nyxus-scripts/` (if present): `build-iso.sh`
  prefers `dist/` over NS for `/opt/nyxus-cache`, and that tree can
  contain dead `/home/cosmic/...` symlinks. **Ensure `dist/` is absent
  before baking.**

### C4. Stale-but-harmless (restamped at bake)
- `etc/os-release` `BUILD_ID=nyx-2026.07.16-x86_64` — restamped at bake.

### C5. ✅ DONE (this pass)
Safemode waybar fallback → alacritty; fastfetch staged; WaybarMockup
deleted.

---

## D. Other "look into" items (non-blocking)
- **SDDM `Main.qml`** offline-payload copy drifts from the baked theme
  (fallback greeter; live path is greetd) — sync or stop shipping the
  duplicate source.
- **Replit runtime fallbacks** (`nyxus-bootstrap`, `nyxus_install.sh`,
  …): offline-first works via `/opt/nyxus-cache`; decide whether to
  repoint the network fallback to a live host or remove it.

*Update this file as items land; tick the audit checklist in parallel.*
