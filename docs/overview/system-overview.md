# System Overview

## Identity

Nyxus-Core is the platform repository for NYXUS and its NYX delivery image.

- **NYX**: the bootable ISO artifact.
- **NYXUS**: the operating system/platform and its application ecosystem delivered by NYX.

## What the System Contains

NYXUS combines:
- Arch-based operating environment composition
- Hyprland-centered desktop/runtime configuration with **EWW** bars (top and bottom)
- Native application payloads and install/runtime scripts — 12 desktop apps with launcher entries plus additional runtime utilities and overlay components
- Web/API distribution surfaces for platform artifacts
- DARK MIRROR · TRIPLE-BLACK LAYERED visual design system shared across all GUI components

## What This Repository Contains

Nyxus-Core is a monorepo that centralizes:
- ISO build pipeline (`iso-builder/`)
- Deployable services and app surfaces (`artifacts/`)
- Shared TypeScript libraries (`lib/`) — including API spec, client, zod, db, and i18n scaffold
- Build/developer automation scripts (`scripts/`)
- Release and governance documents at the repository root
- Design contract and master checklist in `docs/`

## Delivery Model

1. Workspace packages are validated and built.
2. API/web distribution components are produced from `artifacts/`.
3. ISO staging mirrors required runtime payloads into the archiso profile.
4. NYX ISO is baked and released as the canonical distribution image.

The live ISO boots into NYXUS with a full chrome layer — Hyprland, EWW bars, Dunst notifications, SDDM login theme, the complete Python GTK4 app suite, and NYXUS Phantom (`nyxus-intel`) — all staged at build time from `artifacts/api-server/nyxus-scripts/`.
