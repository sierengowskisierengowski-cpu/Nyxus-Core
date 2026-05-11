#!/usr/bin/env bash
# NYXUS · EWW · now-playing (playerctl)
set -u

status="Stopped"
title="—"
artist=""
icon="□"

if command -v playerctl >/dev/null 2>&1; then
  status=$(playerctl status 2>/dev/null || echo Stopped)
  if [[ "$status" != "Stopped" && "$status" != "No players found" ]]; then
    title=$(playerctl metadata title  2>/dev/null || echo "—")
    artist=$(playerctl metadata artist 2>/dev/null || echo "")
  else
    status="Stopped"
  fi
fi

case "$status" in
  Playing) icon="▶" ;;
  Paused)  icon="⏸" ;;
  *)       icon="□" ;;
esac

[[ -n "$artist" && "$artist" != "—" ]] && tooltip="${icon} ${artist} — ${title}" || tooltip="${icon} ${title}"

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg status "$status" --arg title "$title" --arg artist "$artist" \
        --arg icon "$icon" --arg tooltip "$tooltip" \
    '{status:$status,title:$title,artist:$artist,icon:$icon,tooltip:$tooltip}'
else
  printf '{"status":"%s","title":"%s","artist":"%s","icon":"%s","tooltip":"%s"}\n' \
    "$status" "${title//\"/}" "${artist//\"/}" "$icon" "${tooltip//\"/}"
fi
