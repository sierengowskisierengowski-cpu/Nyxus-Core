#!/usr/bin/env bash
# NYXUS · EWW · station matrix + workspace state
# Reads ~/.config/nyxus/stations.json and hyprctl for live occupancy.
set -u

STATIONS_JSON="${HOME}/.config/nyxus/stations.json"
active=1
home_active=false
start_active=false
start_occupied=false
home_occupied=false
occupied="[]"
declare -a occ_ids=()

  if command -v hyprctl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
  raw_id=$(hyprctl activeworkspace -j 2>/dev/null | jq -r '.id' 2>/dev/null || echo 1)
  raw_name=$(hyprctl activeworkspace -j 2>/dev/null | jq -r '.name' 2>/dev/null || echo "")
  # station names, not ids: HOME/START are NAMED workspaces (Hyprland gives
  # named workspaces negative ids from -1337 down, so an id test is fragile).
  if [[ "$raw_name" == "HOME" || "$raw_id" == "-1337" || "$raw_name" == "0" ]]; then
    home_active=true
    active=0
  elif [[ "$raw_name" == "START" ]]; then
    start_active=true
    active=-1
  else
    active="$raw_id"
  fi
  occupied=$(hyprctl workspaces -j 2>/dev/null \
    | jq -c '[.[] | select(.windows > 0) | .id] | sort' 2>/dev/null || echo "[]")
  home_occupied=$(hyprctl workspaces -j 2>/dev/null \
    | jq -r 'any(.[]; (.name == "HOME" or .id == -1337 or .name == "0") and .windows > 0)' 2>/dev/null || echo false)
  start_occupied=$(hyprctl workspaces -j 2>/dev/null \
    | jq -r 'any(.[]; .name == "START" and .windows > 0)' 2>/dev/null || echo false)
  if [[ "$occupied" != "[]" && -n "$occupied" ]]; then
    while read -r id; do occ_ids+=("$id"); done < <(jq -r '.[]' <<<"$occupied")
  fi
fi
[[ -z "$active" || "$active" == "null" ]] && active=1
[[ -z "${home_occupied:-}" ]] && home_occupied=false
[[ -z "${start_occupied:-}" ]] && start_occupied=false
[[ -z "${start_active:-}" ]] && start_active=false

is_occ() {
  local target="$1"
  for id in "${occ_ids[@]}"; do
    [[ "$id" == "$target" ]] && { echo true; return; }
  done
  echo false
}

if [[ ! -r "$STATIONS_JSON" ]] || ! command -v jq >/dev/null 2>&1; then
  printf '{"active":%s,"home_active":%s,"home":{"code":"HOME","name":"HOME","hue":"cyan"},"start":{"active":false,"occupied":false},"stations":[]}\n' \
    "$active" "$home_active"
  exit 0
fi

jq -nc \
  --argjson active "$active" \
  --argjson home_active "$home_active" \
  --argjson start_active "$start_active" \
  --argjson start_occupied "$start_occupied" \
  --argjson occupied "$occupied" \
  --argjson occ1  "$(is_occ 1)"  --argjson occ2  "$(is_occ 2)" \
  --argjson occ3  "$(is_occ 3)"  --argjson occ4  "$(is_occ 4)" \
  --argjson occ5  "$(is_occ 5)"  --argjson occ6  "$(is_occ 6)" \
  --argjson occ7  "$(is_occ 7)"  --argjson occ8  "$(is_occ 8)" \
  --argjson occ9  "$(is_occ 9)"  --argjson occ10 "$(is_occ 10)" \
  --argjson home_occupied "${home_occupied:-false}" \
  --slurpfile cfg "$STATIONS_JSON" '
  ($cfg[0].home + {active: $home_active, occupied: $home_occupied}) as $home |
  {
    active: $active,
    home_active: $home_active,
    start: {active: $start_active, occupied: $start_occupied},
    occupied: $occupied,
    occ1:$occ1, occ2:$occ2, occ3:$occ3, occ4:$occ4, occ5:$occ5,
    occ6:$occ6, occ7:$occ7, occ8:$occ8, occ9:$occ9, occ10:$occ10,
    home: $home,
    stations: [
      $cfg[0].stations[] |
      . + {
        active: ($active == .id),
        occupied: (
          if .id == 1 then $occ1 elif .id == 2 then $occ2
          elif .id == 3 then $occ3 elif .id == 4 then $occ4
          elif .id == 5 then $occ5 elif .id == 6 then $occ6
          elif .id == 7 then $occ7 elif .id == 8 then $occ8
          elif .id == 9 then $occ9 elif .id == 10 then $occ10
          else false end)
      }
    ]
  }'
