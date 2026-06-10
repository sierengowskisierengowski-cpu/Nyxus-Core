# NyXxOS v2 — Roadmap

> **Status:** living document — updated as milestones are reached
>
> This roadmap describes the intended direction for NyXxOS (delivered via the
> NYX ISO). It is written to reflect the *current* repository reality as a
> starting point and to be honest about what is aspirational.

---

## Vision / Goals

NyXxOS is a custom Arch Linux distribution built around Hyprland, designed
to deliver an experience that feels cohesive, polished, and complete — closer
to a commercial product than a hobbyist rice. The platform combines:

- A hand-crafted Wayland desktop (Hyprland) with a unified design language
  (DARK MIRROR · TRIPLE-BLACK LAYERED)
- A suite of native GTK4 Python applications replacing fragmented system tools
- A download/distribution API and web presence at nyxus-core.replit.app
- An opinionated ISO build pipeline with automated verification

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
  `hyprland.lua` + `conf.d` shards; no deprecated `.conf` syntax.
- **Named workspaces** with per-workspace wallpaper via `nyxus-ws-wallpaperd`.
- **EWW bars** (top + bottom): all flyout panels (network, audio, calendar,
  notifications, quick settings) open real system state; no placeholder data.
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

- `README.md`: high-level overview with a clear "What works today" section.
- `STATUS.md`: ground-truth snapshot updated with each significant change.
- `ROADMAP.md`: (this file) publicly tracked vision.
- `SHIPPING.md`: print-before-flash checklist for ISO releases.
- `docs/` hierarchy: architecture overview, deployment guides, design
  contract, master checklist.
- Contributor guide (`CONTRIBUTING.md`) — published.
- Hardware compatibility matrix — not yet written.

---

## Phased Milestones

### Phase A — Repository foundation ✅
- pnpm workspace builds and typechecks cleanly
- CI validates shell, Python, and TypeScript
- ISO profile lint scripts pass
- All config files in the archiso profile use correct syntax

### Phase B — Verified live boot 🟡
- Build NYX ISO on Arch Linux host using `build-iso.sh`
- Boot to greetd + tuigreet, log in as `nyx`
- `nyxus-bootstrap` completes, EWW bars appear, wallpaper loads
- All 12 GTK4 apps launch without errors
- Settings app: every page reads real system state

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

© 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
