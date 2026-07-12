#!/usr/bin/env bash
# NYXUS · EWW · notification history (dunst)
# Emits {items:[{id,app,summary,body,timestamp}], total, paused}
set -u

items="[]"
total=0
paused="false"

if command -v dunstctl >/dev/null 2>&1; then
  [[ "$(dunstctl is-paused 2>/dev/null)" == "true" ]] && paused="true"
  total=$(dunstctl count history 2>/dev/null || echo 0)

  if command -v jq >/dev/null 2>&1; then
    raw=$(dunstctl history 2>/dev/null)
    if [[ -n "$raw" ]]; then
      items=$(echo "$raw" | jq -c '
        (.data[0] // []) | map({
          id:        (.id.data // 0),
          app:       (.appname.data // ""),
          summary:   (.summary.data // ""),
          body:      ((.body.data // "") | gsub("\n"; " ") | .[0:140]),
          timestamp: (.timestamp.data // 0)
        }) | sort_by(-.timestamp) | .[0:25]
      ' 2>/dev/null || echo "[]")
    fi
  fi
fi

if command -v jq >/dev/null 2>&1; then
  jq -nc --argjson items "$items" --argjson total "${total:-0}" --arg paused "$paused" \
    '{items:$items, total:$total, paused:$paused}'
else
  printf '{"items":%s,"total":%s,"paused":"%s"}\n' "$items" "${total:-0}" "$paused"
fi
