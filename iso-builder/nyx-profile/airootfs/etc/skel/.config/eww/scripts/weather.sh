#!/usr/bin/env bash
# NYXUS · EWW · weather (wttr.in JSON, single-line, 15-min cache)
set -u

CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/nyxus-weather.json"
mkdir -p "$(dirname "$CACHE")"

stale=true
if [[ -f "$CACHE" ]]; then
  age=$(( $(date +%s) - $(stat -c %Y "$CACHE" 2>/dev/null || echo 0) ))
  [[ $age -lt 900 ]] && stale=false
fi

if $stale; then
  raw=$(curl -fsS --max-time 5 "https://wttr.in/?format=j1" 2>/dev/null || echo "")
  if [[ -n "$raw" ]]; then
    temp=$(jq -r '.current_condition[0].temp_C + "°C"' <<<"$raw" 2>/dev/null || echo "—")
    desc=$(jq -r '.current_condition[0].weatherDesc[0].value' <<<"$raw" 2>/dev/null || echo "—")
    printf '{"temp":"%s","summary":"%s"}\n' "$temp" "$desc" > "$CACHE"
  fi
fi

if [[ -s "$CACHE" ]]; then
  cat "$CACHE"
else
  printf '{"temp":"—","summary":"offline"}\n'
fi
