# GowskiNet REDFORGE

AI-powered adversary emulation and training platform with dark terminal aesthetic, attack generation engine, and mission management.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server + Vite frontend (port 8080)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- Required env: `DATABASE_URL` — Postgres connection string, `SESSION_SECRET` — JWT signing secret

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5
- DB: PostgreSQL + Drizzle ORM
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)
- Frontend: React + Vite, TanStack Query, Wouter, shadcn/ui, Tailwind CSS
- Auth: JWT (HS256) with scrypt (salted, per-user) password hashing

## Where things live

- `lib/api-spec/openapi.yaml` — API contract (source of truth)
- `lib/db/src/schema/index.ts` — DB schema (missions, notes, network_devices, users)
- `artifacts/api-server/src/routes/` — Express route handlers
- `artifacts/api-server/src/lib/attack-engine.ts` — Attack generation (Template/Claude/Hybrid)
- `artifacts/redforge/src/pages/` — 8 frontend pages + Login
- `artifacts/redforge/src/contexts/` — Auth context

## Architecture decisions

- **Single-port dev serving**: The api-server (port 8080) starts Vite as a background subprocess and proxies all non-API traffic to it via `http-proxy-middleware`. This works around a Replit artifact registration issue where the redforge service port was never added to `.replit [[ports]]`.
- **JWT auth**: Stateless JWT tokens signed with `SESSION_SECRET`. No refresh tokens — sessions expire after 24h.
- **Attack engine modes**: Template (deterministic bash primitives), Claude (via Anthropic API if key present), Hybrid (template scaffold + Claude enrichment). Falls back to template if no API key.
- **WebSocket live logs**: `/ws` on the api-server streams REAL log events (honeypot records, `journalctl -f` for jett-daemon/bifrost-guardian, auditd if readable). Implemented directly on Node's http/crypto (RFC 6455) — no `ws` dependency. See `src/lib/log-sources.ts` + `src/lib/ws-server.ts`.
- **Single-origin dev**: the Vite dev server serves the SPA and proxies `/api` + `/ws` to the api-server (see `redforge/vite.config.ts`).
- **Seeded data**: there is a real seed script (`scripts/src/seed.ts`) that creates one admin operator from `SEED_ADMIN_PASSWORD` (scrypt-hashed; no committed secret). Run `pnpm --filter @workspace/scripts run seed`. Network devices come from a real `arp-scan`/`nmap` (`scripts/src/scan-network.ts`); the MITRE KB is distilled from real STIX (`scripts/src/build-mitre-dataset.ts`). See `README.md`.

## Product

- **Dashboard**: Mission stats, threat metrics, recent activity
- **Generator**: Create new attack missions with target/tactic/technique/mode selection
- **Mission Archive**: Browse all missions with status filtering
- **Mission Detail**: View revealed payloads, live logs, response scoring
- **Notes**: Operator field notes with tagging
- **Network Map**: Discovered devices with vulnerability tracking
- **Knowledge Base**: Technique library and attack patterns
- **Stats**: Performance metrics and operator analytics

## User preferences

- Dark terminal aesthetic: JetBrains Mono font, `#0a0a0f` bg, `#ef4444` red primary, `#7B5EA7` purple secondary
- Admin credentials are set at seed time via `SEED_ADMIN_PASSWORD` (no default password is committed).

## Gotchas

- In development the Vite dev server serves the SPA and proxies `/api` + `/ws` to the api-server on :8080 (see `redforge/vite.config.ts`). Open the Vite URL, not the api port.
- Run `pnpm --filter @workspace/api-server run dev` to start everything (api + frontend), or the two `dev:api` / `redforge run dev` processes separately (see README).
- If the API key `ANTHROPIC_API_KEY` is not set, attack generation falls back to template mode silently.
- The `[services.env]` section in `artifacts/redforge/.replit-artifact/artifact.toml` sets PORT but the workflow detection never works because port 20508 was never registered in `.replit [[ports]]` during artifact creation.

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
