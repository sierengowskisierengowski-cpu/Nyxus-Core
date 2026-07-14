#!/usr/bin/env bash
# NYXUS · compile eww.scss → eww.css for eww 0.5 (GTK rejects @charset).
# eww cannot load both files — keep eww.scss as source, ship eww.css live.
set -euo pipefail
eww_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$eww_dir"
SRC="eww.scss.source"
[[ -f "$SRC" ]] || SRC="eww.scss"
[[ -r "$SRC" ]] || { echo "no scss source at $SRC" >&2; exit 1; }
npx --yes sass --no-charset --load-path=. "$SRC" eww.css || {
  echo "compile failed — keeping existing eww.css ($(wc -c < eww.css 2>/dev/null || echo 0) bytes)" >&2
  exit 0
}
# GTK CSS (eww 0.5) rejects web flexbox/text props — strip so reload never fails grey.
sed -i -E \
  -e '/^[[:space:]]*(justify-content|align-items|flex-direction|text-align|display:[[:space:]]*flex)[[:space:]]*;/d' \
  -e '/^[[:space:]]*margin:[[:space:]]*0[[:space:]]+auto[[:space:]]*;/d' \
  -e '/^[[:space:]]*width:[[:space:]]*100%[[:space:]]*;/d' \
  eww.css
echo "compiled $SRC → eww.css ($(wc -c < eww.css) bytes, no @charset)"
if [[ -f eww.scss && ! -f eww.scss.source ]]; then
  mv eww.scss eww.scss.source
  echo "moved eww.scss → eww.scss.source (eww needs only eww.css)"
fi
