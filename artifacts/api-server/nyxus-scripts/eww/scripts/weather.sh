#!/usr/bin/env bash
# NYXUS · EWW · weather (wttr.in JSON, single-line, 15-min cache)
# Honours NYXUS_WEATHER_LOCATION from ~/.config/eww/nyxus.conf
# (empty → wttr.in geo-IP guess).
set -u

CONF="${HOME}/.config/eww/nyxus.conf"
[[ -r "$CONF" ]] && . "$CONF"
LOC="${NYXUS_WEATHER_LOCATION:-}"

CACHE="${XDG_CACHE_HOME:-$HOME/.cache}/nyxus-weather.json"
mkdir -p "$(dirname "$CACHE")"

stale=true
if [[ -f "$CACHE" ]]; then
  age=$(( $(date +%s) - $(stat -c %Y "$CACHE" 2>/dev/null || echo 0) ))
  [[ $age -lt 900 ]] && stale=false
fi

if $stale; then
  url="https://wttr.in/${LOC}?format=j1"
  raw=$(curl -fsS --max-time 5 "$url" 2>/dev/null || echo "")
  if [[ -n "$raw" ]] && command -v jq >/dev/null 2>&1; then
    jq -c \
      '{temp: ((.current_condition[0].temp_C // "—") + "°C"),
        summary: (.current_condition[0].weatherDesc[0].value // "—")}' \
      <<<"$raw" > "$CACHE" 2>/dev/null || true
  fi
fi

if [[ -s "$CACHE" ]]; then
  cat "$CACHE"
else
  printf '{"temp":"—","summary":"offline"}\n'
fi
