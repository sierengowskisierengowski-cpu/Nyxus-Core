#!/usr/bin/env bash
# NYXUS · EWW · workspace state
# Output keys consumed by yuck:
#   active           — currently focused workspace id (int)
#   occupied         — sorted array of occupied ids (kept for tooling)
#   occ1 .. occ10    — individual booleans for direct field access in yuck
#                      (yuck cannot dynamically index a property by id, so
#                      we materialize one boolean per pill)
set -u

active=1
occupied="[]"
declare -a occ_ids=()

if command -v hyprctl >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
  active=$(hyprctl activeworkspace -j 2>/dev/null | jq -r '.id' 2>/dev/null || echo 1)
  occupied=$(hyprctl workspaces -j 2>/dev/null \
    | jq -c '[.[] | select(.windows > 0) | .id] | sort' 2>/dev/null || echo "[]")
  if [[ "$occupied" != "[]" && -n "$occupied" ]]; then
    while read -r id; do occ_ids+=("$id"); done < <(jq -r '.[]' <<<"$occupied")
  fi
fi
[[ -z "$active" || "$active" == "null" ]] && active=1

is_occ() {
  local target="$1"
  for id in "${occ_ids[@]}"; do
    [[ "$id" == "$target" ]] && { echo true; return; }
  done
  echo false
}

if command -v jq >/dev/null 2>&1; then
  jq -nc \
    --argjson active "$active" \
    --argjson occupied "$occupied" \
    --argjson occ1  "$(is_occ 1)"  --argjson occ2  "$(is_occ 2)" \
    --argjson occ3  "$(is_occ 3)"  --argjson occ4  "$(is_occ 4)" \
    --argjson occ5  "$(is_occ 5)"  --argjson occ6  "$(is_occ 6)" \
    --argjson occ7  "$(is_occ 7)"  --argjson occ8  "$(is_occ 8)" \
    --argjson occ9  "$(is_occ 9)"  --argjson occ10 "$(is_occ 10)" \
    '{active:$active, occupied:$occupied,
      occ1:$occ1, occ2:$occ2, occ3:$occ3, occ4:$occ4, occ5:$occ5,
      occ6:$occ6, occ7:$occ7, occ8:$occ8, occ9:$occ9, occ10:$occ10}'
else
  printf '{"active":%s,"occupied":%s,"occ1":false,"occ2":false,"occ3":false,"occ4":false,"occ5":false,"occ6":false,"occ7":false,"occ8":false,"occ9":false,"occ10":false}\n' \
    "$active" "$occupied"
fi
