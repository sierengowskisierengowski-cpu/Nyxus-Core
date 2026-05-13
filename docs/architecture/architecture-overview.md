# Architecture Overview

## Scope

Nyxus-Core integrates platform engineering across build, distribution, and runtime concerns.

## System Composition

The system is composed of four primary layers:

1. **Image construction layer** (`iso-builder/`)
   - Builds NYX ISO via archiso tooling.
   - Stages NYXUS runtime content into the image profile.

2. **Distribution/application layer** (`artifacts/`)
   - API service and web surfaces.
   - NYXUS script payload source (`artifacts/api-server/nyxus-scripts/`).

3. **Shared package layer** (`lib/`)
   - Shared API specification, generated client bindings, schema validation, DB package, and i18n scaffold.

4. **Automation layer** (`scripts/`)
   - Workspace-level helper scripts used during development and maintenance.

## Component Relationships

- `lib/*` packages are consumed by service/app packages in `artifacts/*`.
- `artifacts/api-server` builds distribution payloads consumed by API/runtime channels.
- `iso-builder/build-iso.sh` stages NYXUS payloads from `artifacts/api-server/nyxus-scripts/` and build outputs into the ISO profile.
- Root documentation files are mirrored into the image at `/etc/nyxus/` during ISO build.

## Responsibility Boundaries

### Build-time
- TypeScript typechecking and package compilation for workspace packages.
- API/web asset bundling.

### Runtime
- OS/runtime components, app payloads, launchers, and desktop integration delivered by NYXUS.

### Distribution-time
- API and web channels exposing installation and release payloads.
- ISO assembly and release artifact generation.
