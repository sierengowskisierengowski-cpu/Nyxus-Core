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
