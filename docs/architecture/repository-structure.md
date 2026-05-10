# Repository Structure

## Workspace Model

Nyxus-Core uses `pnpm-workspace.yaml` with:
- `artifacts/*`
- `lib/*`
- `scripts`

This allows versioned, repository-wide builds and typechecking from root scripts.

## Top-Level Directory Roles

### `iso-builder/`
Archiso profile and orchestration scripts for building NYX ISO.

### `artifacts/`
Deployable application/service units and payload sources.

- `api-server/`: API distribution service and payload packaging
- `nyxus-web/`: primary web surface
- `nyxus-notepad`, `nyxus-stickies`, `nyxus-sysmon`, `nyxus-widgets`: web demo surfaces
- `mockup-sandbox/`: internal preview/mockup surface

### `lib/`
Shared reusable packages:
- `api-spec`
- `api-client-react`
- `api-zod`
- `db`

### `scripts/`
Repository automation and utility scripts.

### `docs/`
Canonical architecture, deployment, and system reference documentation.

## Why `artifacts/` Exists

Although the directory name can appear ambiguous, in this repository it is a primary source area for deployable platform surfaces and payload staging inputs. It is documented as a stable project structure rather than treated as disposable output.
