# NYXUS — Pre-Bake Cleanup + Settings Completion Roadmap

> Started 2026-07-24 PM on branch `cursor/alien-neon-theme-audit-ac8f`.
> Companion to `HANDOFF.md`, `docs/ALIEN_NEON_SETTINGS_AUDIT.md`.
> Goal: finish stripping dead cruft (so nothing stale gets baked in) and
> drive the master Settings app to full coverage.

---

## A. What's DONE (this branch)

### Theme / brand (earlier commits)
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

### Settings — master coverage
- **Added 9 missing shell-feature sections** (all wired to real CLIs,
  graceful `have()`/`empty_row` fallbacks, standard footer):
  Compositor, Bars & Widgets, Live Wallpaper, Lock Screen, Screensaver &
  Idle, Reactive FX, Mission Control, Session Modes (Hacker/Ghost/Panic),
  Firewall. Settings now has **57 sections**, every one mapped to a page.

---

## B. Settings — remaining completion work (prioritized)

The app is a single `SectionPage` framework (`nyxus_settings.py`). Adding
or deepening a page is mechanical:
1. `SectionDef(...)` in the `SECTIONS` tuple (+ a `GLYPHS` entry for new).
2. A `class XPage(SectionPage)` with `build()` using `Adw.PreferencesGroup`
   + helper rows (`kv_row`, `action_row`, `empty_row`, `Adw.SwitchRow`,
   `status_pill`) and the `STANDARD_*` class attrs (Keybinds/Reset/Advanced
   footer is auto-appended).
3. Register in `PAGE_CLASSES`.
`build()` is try/except-wrapped, so a bad page shows an error row instead
of crashing — but **verify each new/edited page by running the app**
(`nyxus-settings`) since GTK can't be exercised headlessly in CI.

### B1. MINIMAL pages to deepen (1–4 controls today)
`app_perms`, `cameras_mics`, `color`, `containers`, `controllers`, `doh`,
`drop`, `editors`, `gaming`, `kernel`, `mac_random`, `secboot`, `sync`,
`usb_firewall`, `virt`.
- **`kernel` is factually stale:** its active-kernel logic still checks for
  `-lts/-zen/-hardened` (dropped). Retarget to **Kage-Ryu (default) + stock
  (rescue)** per HANDOFF; surface `/etc/nyxus-build` + `nyxus-set-grub-default-kage`.

### B2. PARTIAL pages to bring to "master depth" (5–14 controls)
`about`, `accessibility`, `assistant`, `backup`, `bluetooth`, `clipboard`,
`datetime`, `dock`, `keyboard`, `language`, `mouse`, `notifications`,
`parental`, `plymouth`, `printers`, `record`, `security`, `sound`,
`sounds`, `storage`, `wallpaper`.

### B3. SUBSTANTIVE pages — polish only
`appearance`, `apps`, `display`, `loginscreen`, `network`, `power`,
`privacy`, `updates`, `users` (some still carry "stub text" — replace with
real controls / copy).

### B4. Keep verifying against the app inventory
When a NEW app/feature lands in the build, add its Settings section in the
same PR. Cross-check `.desktop` entries + `/usr/local/bin/nyxus-*` +
hyprland `exec-once` against `SECTIONS` so nothing ships un-configurable.
(Stay-as-is — no Settings needed: Arsenal/lab, Bifrost, GodsApp, Meli.)

---

## C. Dead-code stripping — remaining (NEEDS OWNER CONFIRMATION)

> A blind pre-bake audit flagged these; each is verified below. **Do NOT
> mass-delete** — several "orphans" are live via subtle paths.

### C1. CORRECTION — do NOT delete (they are LIVE)
- `nyxus-recovery-setup` / `nyxus-recovery-register` / `nyxus-recovery-auth`
  and `sddm-themes/nyxus/Main.qml`: the recovery auth is wired into the
  **shipped** `etc/pam.d/sddm-recovery-snippet` (SDDM recovery backdoor).
  Keep the whole cluster.

### C2. NS orphans mapped by the download portal (`download.ts`)
`nyxus-notif-status.sh` (waybar emitter; waybar removed), `nyxus-greetd.toml`
(live uses `/etc/greetd/config.toml`), `nyxus-waybar-stars.png` (waybar
asset), `hyprland.lua` (reverted lua migration; quarantined by
`nyxus-restore-desktop.sh`). Deleting each requires **also** removing its
`artifacts/api-server/src/routes/download.ts` entry (and any restore-script
map) so the portal doesn't 404. Safe once done together; deferred here to
avoid touching the typechecked api-server in a theme/settings PR.

### C3. Bake-host hygiene (not committed, but poisons a local bake)
- `artifacts/api-server/dist/nyxus-scripts/` (if present): `build-iso.sh`
  prefers `dist/` over NS for `/opt/nyxus-cache`, and that tree contains
  symlinks to `/home/cosmic/...` (dead on any target). **Ensure `dist/`
  is absent before baking**, or fix the api-server dist build to
  dereference symlinks.

### C4. Stale-but-harmless (restamped at bake)
- `etc/os-release` `BUILD_ID=nyx-2026.07.16-x86_64` (old `nyx-` prefix) —
  `build-iso.sh` restamps at bake; cosmetic only.

### C5. Confirm-then-remove
- `nyxus-safemode.conf` still `exec`s a `waybar` fallback that no longer
  ships — repoint to eww or drop the fallback.
- `fastfetch/` config is present but never staged though `fastfetch` is in
  `packages.x86_64` — wire it or drop it.
- SDDM `00-nyxus-live.conf` autologin: greetd is the live DM, so this is
  likely dead on the live ISO (kept for installed SDDM).

---

## D. Other "look into" items
- **WaybarMockup.tsx** (`nyxus-web`, route `#/waybars`): legacy cream/clay
  EWW preview; full reskin or delete the page + nav pill. Non-shipping.
- **SDDM `Main.qml`** offline-payload copy drifts from the baked theme
  (fallback greeter; live path is greetd) — sync or stop shipping the
  duplicate source.
- **Replit runtime fallbacks** (`nyxus-bootstrap`, `nyxus_install.sh`,
  `nyxus_chrome.py`, `nyxus.conf`, …): offline-first works via
  `/opt/nyxus-cache`; decide whether to repoint the network fallback to a
  live host or remove it entirely.

*Update this file as items land; tick the audit checklist in parallel.*
