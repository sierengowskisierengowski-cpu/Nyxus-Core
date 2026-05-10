# System Overview

## Identity

Nyxus-Core is the platform repository for NYXUS and its NYX delivery image.

- **NYX**: the bootable ISO artifact.
- **NYXUS**: the operating system/platform and its application ecosystem delivered by NYX.

## What the System Contains

NYXUS combines:
- Arch-based operating environment composition
- Hyprland-centered desktop/runtime configuration
- Native application payloads and install/runtime scripts
- Web/API distribution surfaces for platform artifacts

## What This Repository Contains

Nyxus-Core is a monorepo that centralizes:
- ISO build pipeline (`iso-builder/`)
- deployable services and app surfaces (`artifacts/`)
- shared TypeScript libraries (`lib/`)
- build/developer automation scripts (`scripts/`)
- release and governance documents at the repository root

## Delivery Model

1. Workspace packages are validated and built.
2. API/web distribution components are produced from `artifacts/`.
3. ISO staging mirrors required runtime payloads into the archiso profile.
4. NYX ISO is baked and released as the canonical distribution image.
