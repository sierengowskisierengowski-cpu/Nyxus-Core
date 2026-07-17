#!/usr/bin/env bash
# NYXUS · EWW · pending pacman updates
# `checkupdates` (from pacman-contrib) uses a private DB so it doesn't
# interfere with running pacman. Result is cached for 30 minutes.
set -u

CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/nyxus-updates.json"
mkdir -p "$(dirname "$CACHE")"

stale=true
if [[ -f "$CACHE" ]]; then
  age=$(( $(date +%s) - $(stat -c %Y "$CACHE" 2>/dev/null || echo 0) ))
  [[ $age -lt 1800 ]] && stale=false
fi

if $stale; then
  count=0
  if command -v checkupdates >/dev/null 2>&1; then
    count=$(checkupdates 2>/dev/null | wc -l)
  else
    # pacman-contrib not installed — fall back to the local sync DB
    count=$(pacman -Qu 2>/dev/null | grep -vc '\[ignored\]')
  fi
  if [[ $count -eq 0 ]]; then
    icon="✓"; label="OK"; tooltip="System · up to date"
  elif [[ $count -lt 25 ]]; then
    icon="↓"; label="$count"; tooltip="System · ${count} updates pending"
  else
    icon="!"; label="$count"; tooltip="System · ${count} updates pending — consider syncing"
  fi
  if command -v jq >/dev/null 2>&1; then
    jq -nc --argjson count "$count" --arg icon "$icon" --arg label "$label" --arg tooltip "$tooltip" \
      '{count:$count,icon:$icon,label:$label,tooltip:$tooltip}' > "$CACHE"
  else
    printf '{"count":%s,"icon":"%s","label":"%s","tooltip":"%s"}\n' \
      "$count" "$icon" "$label" "$tooltip" > "$CACHE"
  fi
fi

cat "$CACHE"
