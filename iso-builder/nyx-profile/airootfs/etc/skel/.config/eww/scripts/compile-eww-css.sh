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
# GTK CSS (eww 0.5 / GTK3) rejects web-only props. A SINGLE invalid property
# makes GTK abort parsing at that line and silently drop every rule after it —
# which is what left the bars/pills falling back to grey defaults. Strip the
# whole `property: value;` declaration (the old regex only matched a valueless
# `property;` form, so it never actually removed anything).
sed -i -E \
  -e '/^[[:space:]]*(justify-content|justify-items|justify-self|align-items|align-content|align-self|flex|flex-direction|flex-wrap|flex-flow|flex-grow|flex-shrink|flex-basis|order|gap|row-gap|column-gap|text-align|white-space|line-height|vertical-align|object-fit|overflow|overflow-x|overflow-y|position|top|right|bottom|left|z-index|float|clear|cursor|content|display)[[:space:]]*:[^;}]*;/d' \
  -e '/^[[:space:]]*(background-blend-mode|background-clip|background-origin|background-size|filter|backdrop-filter|mix-blend-mode|isolation|mask|mask-image|clip-path|caret-color|appearance|user-select)[[:space:]]*:[^;}]*;/d' \
  -e '/^[[:space:]]*margin:[[:space:]]*0[[:space:]]+auto[[:space:]]*;/d' \
  -e '/^[[:space:]]*(width|height|max-width|max-height):[^;}]*;/d' \
  eww.css
echo "compiled $SRC → eww.css ($(wc -c < eww.css) bytes, no @charset)"
if [[ -f eww.scss && ! -f eww.scss.source ]]; then
  mv eww.scss eww.scss.source
  echo "moved eww.scss → eww.scss.source (eww needs only eww.css)"
fi
