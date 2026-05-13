#!/usr/bin/env bash
# NYXUS · Refresh nyxus.pot from every Python script that uses _().
# Requires `xgettext` (gettext package). Idempotent.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="${ROOT}/artifacts/api-server/nyxus-scripts"

if ! command -v xgettext >/dev/null; then
  echo "xgettext not found — install the gettext package" >&2
  exit 1
fi

mapfile -t pyfiles < <(find "$SRC" -maxdepth 1 -type f -name "*.py")
xgettext \
  --language=Python \
  --keyword=_ \
  --keyword=N_ \
  --from-code=UTF-8 \
  --package-name=nyxus \
  --package-version=rolling \
  --copyright-holder="NYXUS contributors" \
  --output="${HERE}/nyxus.pot" \
  "${pyfiles[@]}"

# Merge into existing .po files so translators don't lose work.
for po in "${HERE}/locale/"*/LC_MESSAGES/nyxus.po; do
  [[ -f "$po" ]] || continue
  msgmerge --quiet --update --backup=none "$po" "${HERE}/nyxus.pot"
done

echo "nyxus.pot refreshed; ${#pyfiles[@]} source files scanned"
