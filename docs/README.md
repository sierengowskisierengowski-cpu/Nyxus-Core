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
- [`DESIGN_CONTRACT.md`](DESIGN_CONTRACT.md): Active design quality bar for all NYXUS UI components — layout, typography, color. Colour section carries the locked ALIEN NEON palette plus the banned-hex list.
- [`ALIEN_NEON_SETTINGS_BRIEF.md`](ALIEN_NEON_SETTINGS_BRIEF.md): **START HERE** for ALIEN NEON + Settings workstream (phases, stay-as-is, progress log).
- [`ALIEN_NEON_SETTINGS_AUDIT.md`](ALIEN_NEON_SETTINGS_AUDIT.md): Full counted checklist — unthemed surfaces, thin Settings pages, missing sections.
- [`BUILD_DAY_BRIEF_2026-07-24.md`](BUILD_DAY_BRIEF_2026-07-24.md): **Master brief for the last day of building** (Jul 23–24) — story, timeline, done/open, bake readiness.
- [`DEEP_BUILD_AUDIT_2026-07-24.md`](DEEP_BUILD_AUDIT_2026-07-24.md): Deep consistency audit (lockstep, palette, keybinds, profiledef) — bake GO snapshot.
- [`PRE_BAKE_CLEANUP_AND_SETTINGS.md`](PRE_BAKE_CLEANUP_AND_SETTINGS.md): Pre-bake cleanup + Settings coverage roadmap.
- [`MASTER_CHECKLIST.md`](MASTER_CHECKLIST.md): Master build and feature delivery checklist tracking overall platform progress.
- [`../HANDOFF.md`](../HANDOFF.md): Live bake/boot state — read first for ISO/kernel; points at the day brief + audits.

### Historical Reference
- [`legacy-visuals.md`](legacy-visuals.md): Superseded visual specifications kept for historical context.

## Terminology Contract

- **NYX** = ISO image only
- **NYXUS** = OS/platform/application ecosystem

This naming is enforced throughout repository documentation.


---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
