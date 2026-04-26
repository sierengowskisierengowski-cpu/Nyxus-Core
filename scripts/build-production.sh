#!/usr/bin/env bash
set -euo pipefail

echo "→ building API server..."
pnpm --filter @workspace/api-server run build

echo "✅ production build complete"
