# Replit Notes

This file is limited to Replit-specific operational guidance.

For canonical project architecture and deployment documentation, use:
- `docs/README.md`
- `docs/architecture/*`
- `docs/deployment/*`
- `docs/overview/*`

## Replit Development Commands

- `pnpm run typecheck`
- `pnpm run build`
- `pnpm --filter @workspace/api-server run dev`
- `pnpm --filter @workspace/api-spec run codegen`
- `pnpm --filter @workspace/db run push` (development only)

## Replit Environment Notes

- ISO building is out of scope for Replit; use an Arch Linux host for `iso-builder/` workflows.
- Vite packages may require deployment environment variables (such as `PORT` and `BASE_PATH`) depending on package config.

## Naming Contract

- **NYX** = ISO image only
- **NYXUS** = operating system/platform/application ecosystem

## User preferences

- **Auth lockout policies stay OFF until post-install.** Do NOT add or
  enable `fail2ban`, `pam_faillock`, `pam_tally2`, or any account-lockout
  PAM module in the ISO build, base airootfs, or first-boot scripts.
  These have repeatedly locked the user out during install/recovery.
  They will be turned on by the user (as designed) only AFTER the system
  is fully installed and verified working. Slow-failure delays inside
  custom helpers (e.g. the 1.5s sleep in `nyxus-ghost-auth`) are fine —
  no account state is changed.

- **Settings Completeness Standard (NON-NEGOTIABLE).** Every feature,
  app, addon, widget, and component shipped in NYXUS must include its
  own fully populated settings section wired into the main Settings hub
  (`artifacts/api-server/nyxus-scripts/nyxus_settings.py`).

  Required for EVERY page, no exceptions:
    * General options relevant to the feature (enable/disable, autostart, etc.)
    * Appearance options where applicable (theme, sizing, position, animations)
    * Behavior options (triggers, defaults, what it does)
    * Keybind configuration for that feature
    * "Reset to defaults" button
    * Feature-specific advanced options a power user would expect

  Hard rules:
    * NO empty pages, NO greyed-out options, NO placeholder text.
    * NO toggles that do nothing — every switch must call a real helper.
    * NO sliders that go nowhere — every slider must mutate real state.
    * If a feature exists in the OS but has no settings page → add one.
    * If a settings option exists but does nothing → wire it or delete it.
    * Benchmark: macOS System Preferences / Windows 11 Settings depth.
      A user coming from those platforms must open NYXUS Settings and
      feel nothing is missing.

  Applies retroactively (audit + fix existing sparse pages) AND going
  forward (no new feature merges without its settings page complete).
  Code review will reject any PR with empty / non-functional settings.
