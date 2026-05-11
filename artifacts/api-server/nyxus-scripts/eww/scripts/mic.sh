#!/usr/bin/env bash
# NYXUS · EWW · microphone state (mute / level)
set -u

vol=0; mute="no"; icon="○"; tooltip="Microphone · idle"

if command -v wpctl >/dev/null 2>&1; then
  out=$(wpctl get-volume @DEFAULT_AUDIO_SOURCE@ 2>/dev/null || echo "")
  vol=$(awk '{printf "%d", $2*100}' <<<"$out")
  grep -q MUTED <<<"$out" && mute="yes"
elif command -v pamixer >/dev/null 2>&1; then
  vol=$(pamixer --default-source --get-volume 2>/dev/null || echo 0)
  pamixer --default-source --get-mute 2>/dev/null | grep -q true && mute="yes"
fi

if [[ "$mute" == "yes" ]]; then
  icon="✕"; tooltip="Microphone · MUTED"
else
  icon="●"; tooltip="Microphone · ${vol}%"
fi

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg icon "$icon" --arg mute "$mute" --argjson vol "$vol" --arg tooltip "$tooltip" \
    '{icon:$icon,mute:$mute,vol:$vol,tooltip:$tooltip}'
else
  printf '{"icon":"%s","mute":"%s","vol":%s,"tooltip":"%s"}\n' "$icon" "$mute" "$vol" "$tooltip"
fi
