# GowskiNet CIPHER

An honest, local password-security lab: real password strength analysis, real
hash-type identification, and a real front-end/manager over the standard
`hashcat` and John the Ripper binaries installed on the machine. CIPHER does
not implement any cracking algorithm itself and contains no fabricated data —
job progress, cracked results, and CPU/GPU telemetry are all real.

## Run & Operate

- `pnpm --filter @workspace/api-server run dev` — run the API server (port 8080, proxied to `/api`)
- `pnpm --filter @workspace/cipher run dev` — run the frontend (port 23051; Vite proxies `/api` -> :8080)
- `pnpm --filter @workspace/api-server run test` — backend smoke test (auth, path safety, real system stats, real binary invocation)
- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from the OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/scripts run seed` — seed the database with honest sample data
- `pnpm --filter @workspace/scripts run hash-password '<pw>'` — print a scrypt hash for `CIPHER_PASSWORD_HASH`
- Required env: `DATABASE_URL` (Postgres), and `CIPHER_PASSWORD` or `CIPHER_PASSWORD_HASH` (owner auth)
- Optional env: `CIPHER_AUTH_SECRET` (token HMAC; auto-persisted if unset), `CIPHER_WORK_DIR` (default `~/.cipher/work`)
- See `README.md` and `.env.example` for full local setup.

## Stack

- pnpm workspaces, Node.js 24, TypeScript 5.9
- API: Express 5 (port 8080, routed via `/api`)
- DB: PostgreSQL + Drizzle ORM
- Frontend: React + Vite + Tailwind CSS + wouter + TanStack Query
- Validation: Zod (`zod/v4`), `drizzle-zod`
- API codegen: Orval (from OpenAPI spec)
- Build: esbuild (CJS bundle)

## Where things live

- `lib/api-spec/openapi.yaml` — OpenAPI source of truth
- `lib/db/src/schema/` — all Drizzle table schemas
- `lib/api-client-react/src/` — generated React Query hooks (via codegen)
- `artifacts/api-server/src/routes/` — all Express route handlers
- `artifacts/cipher/src/pages/` — all 12 frontend pages
- `artifacts/cipher/src/components/` — layout, sidebar, shared UI
- `scripts/src/seed.ts` — database seed script

## Architecture decisions

- Contract-first API: OpenAPI spec defines all endpoints, Orval generates typed React Query hooks + Zod schemas automatically
- In dev the Vite server proxies `/api` → Express (8080); in production the shared proxy routes `/api` → Express and `/` → Vite
- All DB access goes through `@workspace/db` — no direct pg calls in routes
- Hash type identification is done server-side in `/api/hashes/identify` using regex pattern matching
- Real tool orchestration lives in `artifacts/api-server/src/lib/cracker.ts`: it spawns the real hashcat/john binaries against files confined to `CIPHER_WORK_DIR`, parses real progress, and persists real results
- Auth: scrypt-hashed owner password + HMAC bearer tokens (`artifacts/api-server/src/lib/auth.ts`); tool-running and mutating endpoints require the token, no secrets in source
- Real system telemetry (`artifacts/api-server/src/lib/system-stats.ts`) comes from `/proc` (CPU/memory) and `nvidia-smi` (GPU)

## Product

GowskiNet CIPHER is an 11-page local password-security lab (login-gated):

1. **Dashboard** — real stats (hashes, crack rate, active jobs, wordlists, weak hashes)
2. **Hash Submission** — paste/upload your own hashes with auto-identification
3. **Attack Engine** — launch real hashcat/john jobs (Dictionary, Brute Force, Hybrid) against your loaded hashes
4. **Live Monitor** — real job progress/speed/ETA parsed from the tool, real tool stdout, real CPU/GPU/memory telemetry
5. **Results & Analysis** — real cracked-password results with CSV export
6. **Wordlists** — upload your own wordlists (stored as real files); built-in `common-passwords.txt`
7. **Rules Library** — hashcat/john rule management with a live rule tester
8. **Hash Database** — full searchable hash database with filtering
9. **Strength Analyzer** — entropy calculation, pattern detection, crack-time estimates
10. **Research Notes** — markdown notebook with pinning, tagging, notebooks
11. **Settings** — GPU defaults, CPU threads, and hashcat/john tool paths (used to launch real jobs)

Removed as part of the "no fabricated data" cleanup: the fake honeypot
Intelligence dashboards, the `Math.random()` live feed / hardware panel, the
inert "crack engine" DB rows, and the AI-targeted/GowskiNet-Intelligence
attack theater.

## User preferences

- Dark ops aesthetic: #0a0a0f background, #06b6d4 cyan primary, #7B5EA7 purple secondary
- JetBrains Mono for all data/code fields, Inter for general UI
- No emojis in the UI
- Legal disclaimer modal on first visit (required before accessing the platform)

## Gotchas

- Run `pnpm --filter @workspace/db run push` after any schema changes
- Run `pnpm --filter @workspace/api-spec run codegen` after any openapi.yaml changes
- The seed script uses `onConflictDoNothing()` — safe to run multiple times
- API server bundles all routes at build time via esbuild — restart workflow after route changes

## Pointers

- See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details
