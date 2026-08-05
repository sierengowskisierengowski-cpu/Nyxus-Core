#!/usr/bin/env bash
# ===========================================================================
# Cloud Agent install — idempotent repository bootstrap for Nyxus-Core.
#
# Runs after the repo is checked out. Prepares durable, source-derived state:
#   1. PostgreSQL 16   — the API server + @workspace/db require it (see AGENTS.md).
#   2. pnpm 11          — CI pins pnpm 11; pnpm 9 fails frozen-lockfile installs.
#   3. Workspace deps   — pnpm install --frozen-lockfile (respects the lockfile
#                          and the .npmrc supply-chain policy).
#
# Per-boot runtime work (starting Postgres, applying the schema, dev servers)
# lives in start.sh / the environment terminals, NOT here.
# ===========================================================================
set -euo pipefail

cd "$(dirname "$0")/.."

# 1. System dependency: PostgreSQL 16 (Ubuntu 24.04 ships it). Guarded so a
#    re-run — or a boot from a snapshot that already has it — is a fast no-op.
if ! command -v pg_ctlcluster >/dev/null 2>&1; then
  echo "[install] Installing PostgreSQL..."
  sudo apt-get update -qq
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq postgresql postgresql-contrib
else
  echo "[install] PostgreSQL already present — skipping apt."
fi

# 2. Pin pnpm 11 via corepack (Node 22 on PATH runs the full stack fine).
echo "[install] pnpm version: $(corepack pnpm@11 --version)"

# 3. Install workspace dependencies against the committed lockfile.
echo "[install] Installing workspace dependencies..."
corepack pnpm@11 install --frozen-lockfile

echo "[install] Done."
