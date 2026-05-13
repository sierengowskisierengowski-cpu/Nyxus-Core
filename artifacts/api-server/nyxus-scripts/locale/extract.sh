#!/usr/bin/env bash
# NYXUS · re-extract the gettext template (.pot) from every Python
# source under nyxus-scripts/. Run this whenever a new _("...") is
# added so translators have an up-to-date template.
#
# Usage:
#   bash locale/extract.sh
#
# Output:
#   locale/nyxus.pot
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
src_root="$(cd "$here/.." && pwd)"
pot="$here/nyxus.pot"

if ! command -v xgettext >/dev/null 2>&1; then
  echo "xgettext not found — install gettext" >&2
  exit 127
fi

# Collect every .py under the scripts dir.
mapfile -t files < <(find "$src_root" -maxdepth 2 -name '*.py' -print)
if [[ ${#files[@]} -eq 0 ]]; then
  echo "no python sources found under $src_root" >&2
  exit 1
fi

xgettext \
  --language=Python \
  --keyword=_ \
  --from-code=UTF-8 \
  --package-name=nyxus \
  --package-version=1.0 \
  --copyright-holder="NYXUS Project" \
  --output="$pot" \
  "${files[@]}"

echo "wrote $pot ($(wc -l < "$pot") lines)"
