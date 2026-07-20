# Nyxus-Core Documentation

This directory contains the canonical project documentation for system scope, architecture, and deployment.

## Documentation Structure

### Repository-Level Docs
- [`../README.md`](../README.md): High-level project overview and documentation index.
- [`../STATUS.md`](../STATUS.md): Point-in-time verified status snapshot.
- [`../ROADMAP.md`](../ROADMAP.md): NYXUS v2 direction and phased milestones.
- [`../SHIPPING.md`](../SHIPPING.md): Release and pre-flash checklist.
- [`../CONTRIBUTING.md`](../CONTRIBUTING.md): Contributor workflow and expectations.

### Overview
- [`overview/system-overview.md`](overview/system-overview.md): What NYXUS is, what NYX is, and what this repository contains.
- [`overview/creator.md`](overview/creator.md): Creator and authorship context.

### Architecture
- [`architecture/architecture-overview.md`](architecture/architecture-overview.md): System composition, component boundaries, and responsibility model.
- [`architecture/repository-structure.md`](architecture/repository-structure.md): Workspace and directory-level structure details.
- [`architecture/live-build-notes.md`](architecture/live-build-notes.md): Hard-won runtime constraints and design decisions for the live Hyprland/EWW desktop (theme spec, typography, EWW bar gotchas, living-wallpaper FX layer, addon status) — consolidated from agent session memory.

### Deployment
- [`deployment/build-pipeline.md`](deployment/build-pipeline.md): Workspace build/typecheck flow and packaging expectations.
- [`deployment/iso-build.md`](deployment/iso-build.md): NYX ISO pipeline, prerequisites, and outputs.
- [`deployment/web-and-api-deployment.md`](deployment/web-and-api-deployment.md): API/web deployment behavior and distribution flow.

### Design and Quality
- [`DESIGN_CONTRACT.md`](DESIGN_CONTRACT.md): Active design quality bar for all NYXUS UI components — layout, typography, color (DARK MIRROR palette), motion, accessibility, and per-component checklists.
- [`MASTER_CHECKLIST.md`](MASTER_CHECKLIST.md): Master build and feature delivery checklist tracking overall platform progress.

### Historical Reference
- [`legacy-visuals.md`](legacy-visuals.md): Superseded visual specifications kept for historical context.

## Terminology Contract

- **NYX** = ISO image only
- **NYXUS** = OS/platform/application ecosystem

This naming is enforced throughout repository documentation.


---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
