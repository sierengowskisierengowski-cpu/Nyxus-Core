#!/usr/bin/env bash
# NYXUS · EWW · current Hyprland workspace
set -u

active=1
if command -v hyprctl >/dev/null 2>&1; then
  active=$(hyprctl activeworkspace -j 2>/dev/null | jq -r '.id' 2>/dev/null || echo 1)
fi
[[ -z "$active" || "$active" == "null" ]] && active=1

printf '{"active":%s}\n' "$active"
