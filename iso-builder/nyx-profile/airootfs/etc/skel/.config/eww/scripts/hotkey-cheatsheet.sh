#!/usr/bin/env bash
# Renders the cheat-sheet body as eww-loadable widget literal.
# Argument 1: optional search query.
set -euo pipefail
q="${1:-}"
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
