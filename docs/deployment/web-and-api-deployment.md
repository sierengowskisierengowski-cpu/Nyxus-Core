# Web and API Deployment

> ⚠ **Read first (2026-07-30): the `nyxus-core.replit.app` production host is
> RETIRED.** There is no public deployment of the API or the web surfaces. Every
> URL naming that host anywhere in the tree is a **dead fallback**, not a live
> endpoint. Choosing a replacement host is an open owner decision.
>
> Two consequences worth internalising:
> 1. **The ISO does not depend on it.** The offline cache at `/opt/nyxus-cache` is
>    baked from `artifacts/api-server/nyxus-scripts/` and first boot works with no
>    network. The bake hard-fails rather than ship an online-only ISO.
> 2. `artifacts/api-server/dist/` is **not** the ISO's payload source and should
>    not be built for a bake — see
>    [`build-pipeline.md`](build-pipeline.md).

## Scope

Deployment surfaces in this repository are centered in `artifacts/`, with `artifacts/api-server` acting as a core distribution service.

## API Service Role

`artifacts/api-server` is responsible for serving distribution content and packaged NYXUS payloads. The `nyxus-scripts` subtree is a critical payload source used both for network delivery and ISO staging.

## Web Surface Role

Web packages (`nyxus-web`, demo artifacts, and sandbox surfaces) provide download and product-facing entry points. These packages are built with Vite and deployed as static outputs.

## Staging and Caching Model

- API build output includes `dist/` content used for runtime distribution.
- ISO staging optionally mirrors `artifacts/api-server/dist/nyxus-scripts/` into `/opt/nyxus-cache/` during ISO build.
- This cache enables offline-first bootstrap behavior on first boot when network is unavailable.

## Release Artifact Expectations

Minimum expected release outputs:
- NYX ISO artifact from `iso-builder/out/`
- API server build output from `artifacts/api-server/dist/`
- Web build outputs for deployment-targeted web surfaces

## Operational Prerequisites

- Environment variables required by Vite packages must be provided by deployment environment.
- Deployment environment should preserve naming contract:
  - NYX = ISO
  - NYXUS = platform/system/apps


---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
