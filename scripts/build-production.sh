#!/usr/bin/env bash
set -euo pipefail

echo "→ building web portal..."
pnpm --filter @workspace/nyxus-web run build

echo "→ building API server..."
pnpm --filter @workspace/api-server run build

echo "✅ production build complete"
