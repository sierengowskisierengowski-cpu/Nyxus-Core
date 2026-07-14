#!/usr/bin/env bash
# NYXUS · EWW · power-profiles-daemon probe
set -u

active="balanced"
icon="◐"
label="BAL"
tooltip="Power profile · balanced"

if command -v powerprofilesctl >/dev/null 2>&1; then
  active=$(powerprofilesctl get 2>/dev/null || echo balanced)
  case "$active" in
    performance)  icon="▲"; label="PERF"; tooltip="Power profile · performance · max clocks, fans up" ;;
    balanced)     icon="◐"; label="BAL";  tooltip="Power profile · balanced · default" ;;
    power-saver)  icon="▼"; label="SAVE"; tooltip="Power profile · power-saver · throttled, quiet" ;;
  esac
fi

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg active "$active" --arg icon "$icon" --arg label "$label" --arg tooltip "$tooltip" \
    '{active:$active,icon:$icon,label:$label,tooltip:$tooltip}'
else
  printf '{"active":"%s","icon":"%s","label":"%s","tooltip":"%s"}\n' \
    "$active" "$icon" "$label" "$tooltip"
fi
