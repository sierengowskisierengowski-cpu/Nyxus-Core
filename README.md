# Nyxus-Core

Canonical source repository for the NYXUS platform and NYX image pipeline.

**Terminology standard**
- **NYX**: the bootable ISO image artifact only.
- **NYXUS**: the operating system, platform services, and application ecosystem delivered by NYX.

---

## System Overview

Nyxus-Core contains the end-to-end platform implementation:
- Arch-based image construction for **NYX**
- Core runtime payloads and desktop assets for **NYXUS**
- API and web distribution surfaces
- Shared TypeScript packages and automation scripts

The repository is intentionally organized as a pnpm workspace so application, service, and shared-library changes can be versioned and shipped together.

---

## Architecture at a Glance

NYXUS is delivered through three coordinated layers:

1. **Build-time**
   - Workspace typechecking and package builds (`lib/*`, `artifacts/*`, `scripts`)
   - API server bundling and dist payload generation
2. **Distribution-time**
   - API and web surfaces distribute installers, tarballs, and related assets
   - ISO staging mirrors runtime payloads into the archiso profile
3. **Runtime**
   - NYX boots into NYXUS runtime components: Hyprland + EWW bars + full GTK4 app suite + NYXUS Phantom

See `/docs/architecture/architecture-overview.md` for component relationships and responsibility boundaries.

---

## Repository Map

```text
.
├── artifacts/                  # Deployable apps/services and runtime payload sources
│   ├── api-server/             # API distribution service and nyxus-scripts payload source
│   ├── nyxus-web/              # Main web surface
│   ├── nyxus-notepad/          # Web demo app
│   ├── nyxus-stickies/         # Web demo app
│   ├── nyxus-sysmon/           # Web demo app
│   ├── nyxus-widgets/          # Web demo app
│   └── mockup-sandbox/         # Preview and mockup environment
├── iso-builder/                # Archiso profile and NYX ISO build pipeline
├── lib/                        # Shared TypeScript packages (API spec/client/zod/db/i18n)
├── scripts/                    # Workspace automation scripts
├── docs/                       # Structured project documentation
├── CHANGELOG.md
├── CREDITS.md
├── LICENSE.md
├── SHIPPING.md
└── replit.md                   # Replit-specific development notes
```

---

## Build and Deployment Summary

### Workspace validation
- `pnpm run typecheck`
- `pnpm run build`

### API/Web packaging flow
- API server build produces distribution outputs under `artifacts/api-server/dist/`
- Vite-based web artifacts use environment-based ports/base paths (see deployment docs)

### NYX ISO flow
- Build host requirement: Arch Linux + root + `mkarchiso`
- Entry point: `iso-builder/build-iso.sh`
- Output artifact: `iso-builder/out/nyx-<version>-x86_64.iso`

Operational detail is documented in `/docs/deployment/*`.

---

## Documentation Index

- Documentation hub: [`docs/README.md`](docs/README.md)
- System overview: [`docs/overview/system-overview.md`](docs/overview/system-overview.md)
- Creator and authorship: [`docs/overview/creator.md`](docs/overview/creator.md)
- Architecture overview: [`docs/architecture/architecture-overview.md`](docs/architecture/architecture-overview.md)
- Repository structure: [`docs/architecture/repository-structure.md`](docs/architecture/repository-structure.md)
- Build pipeline: [`docs/deployment/build-pipeline.md`](docs/deployment/build-pipeline.md)
- ISO build pipeline: [`docs/deployment/iso-build.md`](docs/deployment/iso-build.md)
- Web/API deployment: [`docs/deployment/web-and-api-deployment.md`](docs/deployment/web-and-api-deployment.md)
- Design contract: [`docs/DESIGN_CONTRACT.md`](docs/DESIGN_CONTRACT.md)
- Master checklist: [`docs/MASTER_CHECKLIST.md`](docs/MASTER_CHECKLIST.md)
- Legacy visual history: [`docs/legacy-visuals.md`](docs/legacy-visuals.md)

---

## Created by Joseph Sierengowski

Nyxus-Core, NYX, and NYXUS were created, architected, and built by **Joseph Sierengowski**.

Joseph serves as the original system designer and primary platform architect, defining the repository's direction across ISO engineering, runtime composition, application integration, and delivery workflow.
