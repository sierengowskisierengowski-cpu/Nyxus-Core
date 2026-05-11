#!/usr/bin/env bash
# NYXUS · EWW · workspace state (active id + occupancy bitmap 1..10)
# Output: {"active":N, "occupied":[1,3,4]}
set -u

active=1
occupied="[]"

if command -v hyprctl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
  active=$(hyprctl activeworkspace -j 2>/dev/null | jq -r '.id' 2>/dev/null || echo 1)
  occupied=$(hyprctl workspaces -j 2>/dev/null \
    | jq -c '[.[] | select(.windows > 0) | .id] | sort' 2>/dev/null || echo "[]")
fi
[[ -z "$active" || "$active" == "null" ]] && active=1
[[ -z "$occupied" ]] && occupied="[]"

if command -v jq >/dev/null 2>&1; then
  jq -nc --argjson active "$active" --argjson occupied "$occupied" \
    '{active:$active, occupied:$occupied}'
else
  printf '{"active":%s,"occupied":%s}\n' "$active" "$occupied"
fi
