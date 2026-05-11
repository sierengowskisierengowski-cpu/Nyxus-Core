#!/usr/bin/env bash
# NYXUS · EWW · backlight probe
set -u

pct=0
if command -v brightnessctl >/dev/null 2>&1; then
  cur=$(brightnessctl get 2>/dev/null || echo 0)
  max=$(brightnessctl max 2>/dev/null || echo 1)
  [[ $max -gt 0 ]] && pct=$(( cur * 100 / max ))
fi

printf '{"percent":%s}\n' "$pct"
