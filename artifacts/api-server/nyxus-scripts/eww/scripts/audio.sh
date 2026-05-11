#!/usr/bin/env bash
# NYXUS · EWW · audio probe (volume + mute state)
set -u

vol=0
mute="no"
sink="default"

if command -v pamixer >/dev/null 2>&1; then
  vol=$(pamixer --get-volume 2>/dev/null || echo 0)
  pamixer --get-mute 2>/dev/null | grep -q true && mute="yes"
  sink=$(pamixer --get-default-sink 2>/dev/null | tail -1 | awk -F'"' '{print $4}')
elif command -v wpctl >/dev/null 2>&1; then
  out=$(wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null || echo "0")
  vol=$(awk '{printf "%d", $2*100}' <<<"$out")
  grep -q MUTED <<<"$out" && mute="yes"
fi

if [[ "$mute" == "yes" || "$vol" -eq 0 ]]; then
  icon="✕"
elif [[ $vol -ge 66 ]]; then icon="▶▶▶"
elif [[ $vol -ge 33 ]]; then icon="▶▶"
else                          icon="▶"
fi

tooltip="Audio · ${vol}%"
[[ "$mute" == "yes" ]] && tooltip="Audio · MUTED"

printf '{"vol":%s,"icon":"%s","tooltip":"%s"}\n' "$vol" "$icon" "$tooltip"
