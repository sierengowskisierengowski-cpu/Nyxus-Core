#!/usr/bin/env bash
# Renders the cheat-sheet body as eww-loadable widget literal.
#   hotkey-cheatsheet.sh              → render using saved query
#   hotkey-cheatsheet.sh set <query>  → save query + push HK_CONTENT live
set -euo pipefail
qfile="${XDG_RUNTIME_DIR:-/tmp}/nyxus-hk-query"

if [[ "${1:-}" == "set" ]]; then
  printf '%s' "${2:-}" > "$qfile"
  eww update HK_CONTENT="$("$0")" 2>/dev/null || true
  exit 0
fi

q="${1:-$(cat "$qfile" 2>/dev/null || true)}"
# literal needs exactly ONE root widget — wrap all lines in a vbox
printf '(box :orientation "v" :space-evenly false :spacing 2 :halign "start"\n'
nyxus-hotkey list 2>/dev/null | awk -v q="$q" '
function trim(s){ gsub(/^[[:space:]]+|[[:space:]]+$/,"",s); return s }
BEGIN{ cur="" }
/^── / {
  cur=$0
  gsub(/^── | ──$/,"",cur)
  printf "(label :class \"hk-cat-h\" :xalign 0 :text \"%s\")\n", cur
  next
}
NF>0 {
  line=trim($0)
  if (q != "" && tolower(line) !~ tolower(q)) next
  gsub(/"/,"\\\"",line)
  printf "(label :class \"hk-line\" :xalign 0 :text \"  %s\")\n", line
}'
printf ')\n'
