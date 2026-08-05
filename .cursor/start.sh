#!/usr/bin/env bash
# ===========================================================================
# Cloud Agent start — per-boot runtime reconciliation for Nyxus-Core.
#
# Brings up the backend's stateful dependency and applies the schema so the
# API server (started in the "api-server" terminal) can serve persistence
# routes immediately. Idempotent and safe to re-run: it tolerates an
# already-running cluster, an existing database, and a schema already applied.
# It must return (no long-running foreground process) — dev servers live in
# the environment's terminals.
# ===========================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

DATABASE_URL="postgresql://postgres:postgres@127.0.0.1:5432/nyxus"
export DATABASE_URL

# 1. Start the PostgreSQL 16 cluster (no-op if it is already up).
echo "[start] Starting PostgreSQL cluster 16/main..."
sudo pg_ctlcluster 16 main start 2>/dev/null || true

# 2. Wait until the server accepts connections before touching it.
for _ in $(seq 1 30); do
  if sudo -u postgres pg_isready -q; then break; fi
  sleep 1
done
if ! sudo -u postgres pg_isready -q; then
  echo "[start] ERROR: PostgreSQL did not become ready in time." >&2
  exit 1
fi

# 3. Ensure the password and the nyxus database exist (both idempotent).
sudo -u postgres psql -v ON_ERROR_STOP=1 -c "ALTER USER postgres PASSWORD 'postgres';"
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='nyxus'" | grep -q 1 \
  || sudo -u postgres psql -v ON_ERROR_STOP=1 -c "CREATE DATABASE nyxus;"

# 4. Apply the drizzle schema (idempotent push).
echo "[start] Applying drizzle schema..."
corepack pnpm@11 --filter @workspace/db run push

echo "[start] Backend dependencies ready (DATABASE_URL=$DATABASE_URL)."
