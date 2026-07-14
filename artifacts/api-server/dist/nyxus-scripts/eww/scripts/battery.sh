#!/usr/bin/env bash
# NYXUS · EWW · battery probe (capacity / status / icon / tooltip)
set -u

bat=""
for b in /sys/class/power_supply/BAT*; do
  [[ -d "$b" ]] && { bat="$b"; break; }
done

if [[ -z "$bat" ]]; then
  printf '{"capacity":0,"status":"AC","icon":"⚡","tooltip":"No battery — AC powered"}\n'
  exit 0
fi

cap=$(cat "$bat/capacity" 2>/dev/null || echo 0)
status=$(cat "$bat/status" 2>/dev/null || echo Unknown)

icon="▮"
case "$status" in
  Charging) icon="⚡" ;;
  Discharging)
    if   [[ $cap -ge 80 ]]; then icon="▮"
    elif [[ $cap -ge 50 ]]; then icon="▮"
    elif [[ $cap -ge 25 ]]; then icon="▯"
    else                          icon="▯"
    fi
    ;;
  Full) icon="✓" ;;
esac

tooltip="Battery ${cap}% · ${status}"
printf '{"capacity":%s,"status":"%s","icon":"%s","tooltip":"%s"}\n' "$cap" "$status" "$icon" "$tooltip"
