# Build Pipeline

## Workspace Entry Points

From repository root:

- `pnpm run typecheck`
  - Runs workspace typechecks, including `artifacts/*` and `scripts` packages.
- `pnpm run build`
  - Runs typecheck and then package builds across the workspace.

## Build Flow

1. Validate shared libraries and package contracts.
2. Build application/service packages under `artifacts/*`.
3. Produce API distribution outputs in `artifacts/api-server/dist/`.
4. Use generated outputs as inputs for deployment surfaces and ISO staging.

## Web/API Build Behavior

- API server build entrypoint: `pnpm --filter @workspace/api-server run build`
- Vite-based artifacts read environment configuration for network and base-path settings.
- Some packages enforce required environment variables (`PORT`, `BASE_PATH`) in build config.

## Operational Caveats

- Missing required environment variables causes Vite build-time failures.
- Building all packages from root may fail until per-package deployment environment variables are provided.

> ⚠ **Corrected 2026-07-30.** This section used to say *"For ISO offline cache
> staging, API server dist output should be built before ISO baking."* **That is
> wrong, and following it is actively harmful.** `build-iso.sh` stages
> `/opt/nyxus-cache` from **`artifacts/api-server/nyxus-scripts/`** — the git
> source of truth — and only falls back to `artifacts/api-server/dist/nyxus-scripts`
> if the former is absent. Worse, the bake **rejects** `dist/` outright if it
> contains dangling symlinks, which is exactly what a build on this host produces
> (`/home/cosmic/…` links); `dist/` has historically poisoned bakes for that
> reason. You do **not** need to build `dist/` before baking, and the bake
> hard-fails rather than ship an online-only ISO. See
> [`../../iso-builder/README.md`](../../iso-builder/README.md).


---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
