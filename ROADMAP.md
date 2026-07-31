# NYXUS v2 — Roadmap

> **Status:** living document · **corrected 2026-07-30**
>
> This roadmap describes the intended direction for NYXUS (delivered via the
> NYX ISO). It is written to reflect the *current* repository reality as a
> starting point and to be honest about what is aspirational.
>
> ⚠ **Everything here is a GOAL, not a description of the build.** For what is
> actually true today read **[`HANDOFF.md`](HANDOFF.md)** and
> [`STATUS.md`](STATUS.md). Two goals in this file were being read as directives
> and are now explicitly annotated with the owner decisions that override them
> (Hyprland Lua, and the download host). Do not action a bullet here without
> checking `HANDOFF.md` first.

---

## Vision / Goals

NYXUS is a custom Arch Linux distribution built around Hyprland, designed
to deliver an experience that feels cohesive, polished, and complete — closer
to a commercial product than a hobbyist rice. The platform combines:

- A hand-crafted Wayland desktop (Hyprland) with a unified design language:
  **ALIEN NEON** — urban-alien graffiti on triple-black glass. *(The
  "DARK MIRROR" name this line used to carry was **purged** on 2026-07-23 along
  with its palette; see [`docs/THEME.md`](docs/THEME.md).)*
- A bespoke **Kage-Ryu** kernel (XanMod, Alder-Lake-tuned, security-lab config)
  as the primary kernel, with stock `linux` kept only as a rescue entry
- A suite of native GTK4 Python applications replacing fragmented system tools
- A download/distribution API and web presence — **host TBD.**
  `nyxus-core.replit.app` is **retired**; no replacement has been chosen. This
  is an open owner decision, not a working endpoint
- An opinionated ISO build pipeline with automated verification
  (`verify-profile.sh`, whose gates are regression tests for bugs that shipped)

The v2 vision is to ship a bootable NYX ISO that a new user can flash to a USB,
boot from bare metal, and have a fully working desktop environment within
60 seconds — no manual configuration required.

---

## User Experience Goals

- **Zero-configuration first boot:** the `nyxus-bootstrap` flow completes
  silently; the user lands in a fully themed Hyprland session without editing
  a single config file.
- **Offline-capable install:** offline cache baked into the ISO means the
  first-boot setup works without Wi-Fi.
- **Consistent chrome:** every surface — login screen, lock screen, bars,
  launcher, apps, settings — shares the NYXUS design system with no visual
  inconsistencies.
- **App parity:** each NYXUS GTK4 app reads real system state on launch,
  writes via the correct system tool, and persists settings across reboots.
- **Discoverable keyboard shortcuts:** every keybind is listed in
  Settings → Keyboard → Shortcuts and reachable from the help overlay.
- **Graceful degradation:** if a component fails, the user gets a visible
  toast notification and a clear path to recovery (not a silent crash).

---

## Platform / System Goals

- Arch Linux base kept minimal — only packages that NYXUS actively uses are
  included.
- Hyprland as the only supported compositor; no fallback X11 session in the
  ISO.
- Python GTK4 app suite validated with `python -m py_compile` in CI; no
  silent import errors on first launch.
- All runtime daemons have a Settings toggle to disable them.
- Logging goes to `~/.cache/nyxus/<app>.log`; no `print` / `console.log`
  calls in production code paths.
- `nyxus-crashd` uploads anonymized crash reports to the API endpoint when
  the user opts in.

---

## Installer / Setup Goals

- Calamares graphical installer with NYXUS branding, slideshow, and
  post-install script that removes the live-session sudoers override.
- Disk install produces a system indistinguishable from the live session
  (same theme, same apps, same settings defaults).
- `nyxus-postinstall` sets up the first real user, timezone, locale,
  and runs a health audit.
- Recovery mode: `nyxus-bootstrap --recover` re-runs the install flow from a
  running system.

---

## Desktop / Hyprland Goals

- **Hyprland Lua config:** all window rules, animations, and binds live in
  `hyprland.lua` + shards; no deprecated `.conf` syntax.

  > ⛔ **OWNER DECISION 2026-07-28: DO NOT MIGRATE YET.** Hyprland 0.57 removes
  > hyprlang, and this profile is `hyprland.conf` + 17 hyprlang shards, so a
  > premature migration ships an ISO whose desktop config never loads. The
  > migration is also **big-bang** — if `hyprland.lua` exists, `hyprland.conf` is
  > never read — and three shards are *generated at runtime*
  > (`nyxus-stations.conf`, `nyxus-freeform.conf`, `nyxus-monitors.conf`). Order
  > of operations: **pin the Hyprland version first, stabilise the build, then
  > migrate on a branch after 0.57 actually ships.** Gate `13x` hard-fails a bake
  > if the repos offer ≥ 0.57 (override: `NYX_ALLOW_HYPRLAND=1`).
  > `hyprlock`/`hypridle` keep hyprlang indefinitely; only the compositor entry
  > point moves.

- **Named workspaces** with per-workspace wallpaper via
  `nyxus-workspace-wallpaperd`. *(The old name `nyxus-ws-wallpaperd` in this
  file was wrong — no such binary has ever existed.)*
- **EWW bars** (four: top, bottom, left rail, right rail): all flyout panels
  (network, audio, calendar, notifications, quick settings) open real system
  state; no placeholder data.
- **Mission Control** (`nyxus-mission-control-toggle`): live workspace
  overview.
- **Spotlight** (`nyxus-launcher`): file search via tracker3 → fd → find
  chain; app search from `.desktop` entries.
- **Hot corners**, **Night Light** (gammastep), **Dynamic Wallpaper**
  (sunrise/sunset rotator): all user-configurable from Settings.
- **Game Mode / Focus Mode** toggles: per-output blur, animation policy,
  and notification suppression.

---

## Packaging / Update Goals

- Signed NYX ISO released via GitHub Actions; SHA-256 published in the
  release notes and the download API.
- Automated ISO CI job on Arch Linux runner: builds ISO, runs
  `iso-build-verify.sh`, uploads artifact.
- OTA update channel: `nyxus-updater` UI polls the API for new ISO versions
  and offers in-place package upgrades where possible.
- AUR PKGBUILD for `nyxus-desktop` (the full chrome layer) for users who
  want NYXUS on an existing Arch install.

---

## Security / Reliability Goals

- Live-session passwordless sudo is removed by Calamares post-install; the
  installed system requires a password for `sudo`.
- `nyxus-parental-helper` and `nyxus-welcome-helper` run via polkit; no
  setuid binaries.
- Tamper detection: all Python files ship with `__nyxid__` fingerprint and
  `_nyx_integrity()` check.
- Security Center (10 sections): firewall, AppArmor/Flatpak permissions,
  disk encryption status, SSH, privacy settings — all wired to real system
  state.
- CI: `bash -n` linting for all shell scripts; `python -m py_compile` for
  all Python files; TypeScript strict-mode typecheck.

---

## Documentation / Community Goals

- `HANDOFF.md`: the single mandatory entry point — live build state, delivery
  model, do-not-repeat gotchas. Everything else is reference.
- `README.md`: high-level overview with a clear "What works today" section.
- `STATUS.md`: ground-truth repository/CI snapshot updated with each
  significant change (**not** the same thing as bake readiness).
- `ROADMAP.md`: (this file) publicly tracked vision — goals only.
- `SHIPPING.md`: print-before-flash checklist for ISO releases.
- `docs/KEYBINDS.md`: every active keybind, re-derived from the shipped config.
- `docs/THEME.md` + `docs/DESIGN_CONTRACT.md`: the locked ALIEN NEON palette and
  the banned-hex list, both generated from `nyxus_palette.py` / `accent.json`.
- `docs/` hierarchy: architecture overview, deployment guides, design
  contract, master checklist, dated session briefs.
- Contributor guide (`CONTRIBUTING.md`) — published.
- Hardware compatibility matrix — not yet written.

> **Standing rule for every doc in this list:** if a statement can be checked
> against the tree, check it before writing it, and date the change. Docs that
> assert a purged palette or a renamed path have twice sent agents to
> reintroduce banned colour or chase deleted files.

---

## Phased Milestones

### Phase A — Repository foundation ✅
- pnpm workspace builds and typechecks cleanly
- CI validates shell, Python, and TypeScript
- ISO profile lint scripts pass
- All config files in the archiso profile use correct syntax

### Phase B — Verified live boot 🟡
- Build NYX ISO on Arch Linux host using `build-iso.sh`
- Boot to **greetd → regreet (under cage)**, log in as `nyx` — tuigreet is the
  text fallback, not the primary greeter
- Kage-Ryu boots as entry #0 and mounts the live media (`iso9660`/`squashfs`/loop)
- `nyxus-bootstrap` completes, all four EWW bars appear, wallpaper loads
- All 13 GTK4 apps launch without errors
- Settings app: every page reads real system state
- Splash → greeter well under 15s (it was 102s; see `HANDOFF.md`)

### Phase C — Installer
- Calamares disk install tested end-to-end on hardware
- Installed system is fully functional with no live-session artifacts
- `nyxus-postinstall` completes without errors

### Phase D — Distribution
- Automated ISO CI build and artifact upload
- Signed release published on GitHub with SHA-256 manifest
- Download API serves the signed ISO

### Phase E — Polish and ecosystem
- AUR PKGBUILD for `nyxus-desktop`
- OTA update channel operational
- NYXUS Account + NYXUS Drop backends shipped
- Full i18n coverage (beyond en stub)
- Hardware compatibility matrix published
- Contributor guide kept current

---

© 2026 Joseph A. Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
