#!/usr/bin/env bash
# NYXUS · EWW · dunst notification queue + DND state
set -u

paused="false"
waiting=0
displayed=0

if command -v dunstctl >/dev/null 2>&1; then
  paused=$(dunstctl is-paused 2>/dev/null || echo false)
  waiting=$(dunstctl count waiting 2>/dev/null || echo 0)
  displayed=$(dunstctl count displayed 2>/dev/null || echo 0)
fi

total=$(( waiting + displayed ))

if [[ "$paused" == "true" ]]; then
  icon="✕"; label="DND"
  tooltip="Notifications · do-not-disturb (${total} queued)"
elif [[ $total -eq 0 ]]; then
  icon="○"; label="0"
  tooltip="Notifications · clear"
else
  icon="●"; label="$total"
  tooltip="Notifications · ${total} pending — click to pop next, right-click to clear"
fi

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg icon "$icon" --arg label "$label" --arg tooltip "$tooltip" \
    --arg paused "$paused" --argjson total "$total" \
    '{icon:$icon,label:$label,tooltip:$tooltip,paused:$paused,total:$total}'
else
  printf '{"icon":"%s","label":"%s","tooltip":"%s","paused":"%s","total":%s}\n' \
    "$icon" "$label" "${tooltip//\"/}" "$paused" "$total"
fi
