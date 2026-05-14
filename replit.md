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

- **NYXUS BUILD STANDARD — THE GOLDEN RULE (NON-NEGOTIABLE).**
  This supersedes the older "Settings Completeness Standard". It applies
  to EVERY feature, app, addon, widget, helper, daemon, and component —
  past, present, and future. If something is incomplete it does NOT
  ship.

  Every feature must have:
    * A fully populated Settings page registered in the main Settings
      hub (`artifacts/api-server/nyxus-scripts/nyxus_settings.py`)
    * Six required sections on EVERY page:
        General · Appearance · Behavior · Keybinds · Advanced · Reset
    * Every option wired to a real function that actually does what it
      says — every toggle toggles real state, every slider mutates real
      state, every keybind points to a real existing binary or script.
    * A valid `.desktop` entry with a correct `Exec=` path (if user-launchable)
    * All binaries existing and executable in `/usr/local/bin/` or `/opt/nyxus/`
    * All systemd units with valid `ExecStart` paths
    * All polkit policies in place where privileged operations are used
    * All Python imports satisfiable from `packages.x86_64`
    * No hardcoded usernames, hostnames, or absolute paths that break
      in a live session — always derive from `$HOME`, `$USER`, etc.

  Hard rules:
    * NO empty pages, NO greyed-out options, NO placeholder text.
    * NO toggles that do nothing.
    * NO sliders that go nowhere.
    * NO `# TODO`, `# FIXME`, or `pass  # implement later` in shipped code.
    * NO mockups — if it's in the build, it works.

  Quality benchmark: open System Preferences on macOS or Settings on
  Windows 11 — NYXUS must match or exceed that depth for every
  equivalent feature. A user coming from those platforms must open
  NYXUS Settings and feel nothing is missing.

  Pre-merge checklist (every session, every PR):
    1. `verify-profile.sh` passes
    2. Full CI suite passes
    3. Every new and modified file is properly staged in `airootfs/`
    4. Every new feature has its complete Settings page
    5. Nothing is empty, stubbed, placeholder, or greyed-out

  Applies retroactively AND going forward. Code review will reject any
  PR that violates this standard. The rule is simple: if it ships
  incomplete, it goes back. Every time. No exceptions.
