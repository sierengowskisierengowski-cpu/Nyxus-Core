# NYXUS — Master Completion Checklist

**Goal:** Grade-A, no-dead-ends, no-mockups OS that "works like you
bought it from Best Buy." Every menu opens a real panel. Every panel
reads/writes real system state. Every setting persists.

**Status legend:** ✅ DONE · 🟡 IN PROGRESS · ⬜ PENDING

Last updated: 2026-05-13 (rev r10)

---

## Cross-cutting rules (apply to every task)

- Every user-facing feature MUST appear in **Settings** under its
  correct page AND be reachable from at least one menu (start menu,
  control center, context menu, or tray).
- Every keybind MUST be listed in Settings → Keyboard → Shortcuts.
- Every running daemon MUST have a Settings toggle to disable it.
- No `print` for errors — use `logging` to `~/.cache/nyxus/<app>.log`.
- No `console.log` in server code — use `req.log` / singleton `logger`.
- Validation: bash `-n` for shell, `python -m py_compile` for Python,
  `eww` yuck/scss balance check.
- After every ~3 items: architect review pass + push tag for MSI to pull.

---

## Phase 1 — 8 PARTIAL Settings pages → fully wired

- ✅ P1.1 PowerPage / P1.2 PrivacyPage / P1.3 AppsPage / P1.4 StoragePage
- ✅ P1.5 UpdatesPage / P1.6 UsersPage / P1.7 AppearancePage / P1.8 AboutPage

## Phase 2 — Tier 1 system polish

- ✅ P2.9 nyxus_welcome
- ✅ P2.10 SDDM polish
- ✅ P2.11 Notification Center
- ✅ P2.12 Quick Settings / Control Center

## Phase 3 — Tier 2 power-user

- ✅ P3.13 Mission Control
- ✅ P3.14 Spotlight
- ✅ P3.14b Desktop layer (T1–T5)
- ✅ P3.14c Files manager
- ✅ P3.15 Clipboard
- ✅ P3.16 Updater UI
- ✅ P3.17 Software Store catalog depth

## Phase 4 — Tier 3 polish

- ✅ P4.18 Sound design
- ✅ P4.19 Animation sweep
- ✅ P4.20 Recovery
- ✅ P4.21 Backup (Timeshift)
- ✅ P4.22 Crash reporter

## Phase 5 — Tier 4 brand-defining

- ✅ P5.23 NYXUS Account
- ✅ P5.24 NYXUS Drop
- ✅ P5.25 Screen recorder

## Cross-cutting fixed

- ✅ WiFi popup white-GTK regression
- ✅ Terminal copy/paste fix
- ✅ Security Center (10 sections + helper + daemon + API + keybinds)

---

## Phase 6 — Mac/Windows-class polish

- ✅ P6.26 Calamares installer branding (slideshow + theme + post-install)
- ✅ P6.27 Time Machine snapshot browser (Backup → Snapshots scrubber)
- ✅ P6.28 Parental Controls (Settings page + helper, OFF by default)
- ✅ P6.29 System-wide search index (tracker3 in Spotlight) — wired in
  `nyxus_launcher.py:search_files()` (tracker3 → fd → find chain)
- ✅ P6.30 App Sandboxing UI (Privacy → App permissions, Flatpak granular)
  — `AppPermissionsPage` reads/writes via `flatpak override --user`
- ✅ P6.31 i18n / multi-language scaffold (gettext + en/es/fr stubs)
  — `nyxus_i18n.py` shim, `locale/` POT + PO + extract/compile scripts,
  `LanguagePage` in Settings → Personal
- ✅ P6.32 Accessibility (Orca/wvkbd/magnus + autostart toggles)
- ✅ P6.33 SDDM avatar / user list (AccountsService icons via `~/.face`
  + `/var/lib/AccountsService/users/<u>` Icon= line)

## Phase 7 — Real code gaps + ops

- ✅ P7.34 swaync notification history viewer
  — `NotificationsPage._swaync_history()` calls
  `busctl --user --json=short … GetHistory` and renders the latest 8
- ✅ P7.35 Crash-report upload endpoint + wire client
  — `routes/crash-reports.ts` POST `/api/crash-reports` with quota GC,
  client at `nyxus-crash-report.py`
- ✅ P7.36 ISO build verification script (lint profile, dry-run)
  — `scripts/iso-build-verify.sh`
- ✅ P7.37 CI pipeline (typecheck, bash -n, py_compile, profile lint)
  — `.github/workflows/typecheck.yml` + `validate.yml`
- ✅ P7.38 Release automation (ISO publish + checksum + manifest)
  — `scripts/iso-release.sh`

---

## Definition of grade-A done (hard gate before ship)

1. Reads its current state from the system on launch.
2. Writes back via the proper system tool (no behind-the-back file edits
   when an API exists).
3. Survives reboot — state persists.
4. Has a Settings home AND a menu/keybind entry.
5. Logs to `~/.cache/nyxus/<app>.log`, not stdout.
6. Fails loud with a user-visible error toast, never silently.
7. Architect review: zero severe findings.

---

## Bonus features (Tier 3 — landed as part of r10 grind)

- ✅ Hot Corners (Settings + `nyxus_hotcorners.py`, hot-reloadable
  tunables via `parse_tunables`)
- ✅ Night Light (gammastep wrapper + Settings toggles)
- ✅ Dynamic Wallpaper (time-of-day rotator with sunset/sunrise)
