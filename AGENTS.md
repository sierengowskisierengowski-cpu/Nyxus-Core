# AGENTS.md

## Cursor Cloud specific instructions

This is a pnpm workspace (`Nyxus-Core`). The runnable dev surfaces are the
TypeScript **API server** (`@workspace/api-server`) and the Vite **web apps**
(`@workspace/nyxus-web` is the primary one; `nyxus-notepad`, `nyxus-stickies`,
`nyxus-sysmon`, `nyxus-widgets`, `mockup-sandbox` are additional surfaces). The
Arch ISO builder (`iso-builder/`), the GTK4 desktop runtime
(`artifacts/api-server/nyxus-scripts/*.py`), and Meli require an Arch live-boot /
graphical session and cannot be built or run headlessly here — treat them as out
of scope for dev/testing in this environment.

### Toolchain / gotchas
- `node` on PATH resolves to `/exec-daemon/node` (Node 22.x) regardless of nvm,
  because `/exec-daemon` precedes the nvm bin dir. Node 24 (matching CI) is
  installed via nvm but is not what `node`/`pnpm` actually use. Node 22 runs the
  full stack fine (install, typecheck, build, dev servers). Don't fight the PATH;
  if you truly need Node 24, prepend `~/.nvm/versions/node/v24.*/bin` to PATH.
- pnpm is provided via corepack (pinned to pnpm 9, matching CI). npm/yarn are
  blocked by the root `preinstall` guard.
- `.npmrc` enforces `minimumReleaseAge: 1440` (packages must be ≥1 day old).
  Frozen-lockfile installs are unaffected; only adding brand-new deps can trip it.

### Standard commands (already documented; do not duplicate config)
- Lint/typecheck: `pnpm run typecheck` (root). Build: `pnpm run build` (root).
- Web dev servers: `pnpm --filter @workspace/<app> run dev` (see each app's
  `vite.config.ts` for default port/base — e.g. `nyxus-web` = `18304`).
- API codegen: `pnpm --filter @workspace/api-spec run codegen`.
- More in `replit.md` and `CONTRIBUTING.md`.

### Running the API server + database (non-obvious)
The API server and `@workspace/db` require Postgres; there is **no bundled
docker-compose or local DB** — you must start one and export `DATABASE_URL`.
Postgres 16 is installed in this environment. To bring up the backend:

1. Start Postgres and ensure a `nyxus` database exists (idempotent):
   ```bash
   sudo pg_ctlcluster 16 main start
   sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres';"
   sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='nyxus'" | grep -q 1 \
     || sudo -u postgres psql -c "CREATE DATABASE nyxus;"
   export DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/nyxus"
   ```
2. Push the drizzle schema (run once after schema changes):
   `pnpm --filter @workspace/db run push`
3. Run the API server (requires both `DATABASE_URL` and `PORT`, else it throws):
   `DATABASE_URL=... PORT=8080 pnpm --filter @workspace/api-server run dev`

Notes:
- `PORT` is mandatory for the API server and overrides the Vite web-app default
  port when exported globally, so keep `PORT` scoped to the API command (do not
  `export PORT` in a shell you also start web dev servers from).
- The API `dev` script runs an esbuild bundle then `node dist/index.mjs`; it is
  not a watcher — restart it to pick up source changes.
- If `DATABASE_URL` is unset the server still boots but persistence routes
  (`/api/nyxus-account/*`, crash reports) return 500.
- Quick end-to-end check: `curl localhost:8080/api/healthz` → `{"status":"ok"}`.
