#!/usr/bin/env bash
# NYXUS · compile every locale/<lang>/LC_MESSAGES/nyxus.po to nyxus.mo
# so the gettext shim can pick it up at runtime.
#
# Usage:
#   bash locale/compile.sh
#
# Re-run after editing any .po file. Safe to run repeatedly.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"

if ! command -v msgfmt >/dev/null 2>&1; then
  echo "msgfmt not found — install gettext" >&2
  exit 127
fi

count=0
while IFS= read -r -d '' po; do
  mo="${po%.po}.mo"
  msgfmt --check --output-file="$mo" "$po"
  echo "compiled $po → $mo"
  count=$((count + 1))
done < <(find "$here" -name 'nyxus.po' -print0)

echo "done — $count locale(s) compiled"
