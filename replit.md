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
