#!/usr/bin/env bash
# NYXUS · compile eww.scss → eww.css for eww 0.5 (GTK rejects @charset).
# eww cannot load both files — keep eww.scss as source, ship eww.css live.
set -euo pipefail
eww_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$eww_dir"
SRC="eww.scss.source"
[[ -f "$SRC" ]] || SRC="eww.scss"
[[ -r "$SRC" ]] || { echo "no scss source at $SRC" >&2; exit 1; }
npx --yes sass --no-charset --load-path=. "$SRC" eww.css
echo "compiled $SRC → eww.css ($(wc -c < eww.css) bytes, no @charset)"
if [[ -f eww.scss && ! -f eww.scss.source ]]; then
  mv eww.scss eww.scss.source
  echo "moved eww.scss → eww.scss.source (eww needs only eww.css)"
fi
