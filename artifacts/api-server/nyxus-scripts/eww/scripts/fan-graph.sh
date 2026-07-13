#!/usr/bin/env bash
# NYXUS · EWW · bottom-bar fan graph meters + sparkline history
# Output: {"fans":[{"id":1,"label":"FAN1","rpm":4200,"pct":47,"bar":26,"hist":[...]}],"tooltip":"..."}
set -u
export LC_ALL=C.UTF-8

STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/nyxus-fan-graph"
STATE="${STATE_DIR}/state.json"
HW="${HOME}/.config/nyxus/hw_profile.json"
HIST_LEN=16
MAX_RPM=9000
BAR_MAX=56

mkdir -p "${STATE_DIR}"
command -v jq >/dev/null 2>&1 || { echo '{"fans":[],"tooltip":"fan speeds"}'; exit 0; }

read_rpm() {
  local path="$1"
  [[ -r "$path" ]] || { echo 0; return; }
  local v
  v=$(<"$path")
  [[ "$v" =~ ^[0-9]+$ ]] || { echo 0; return; }
  echo "$v"
}

push_hist() {
  local hist="$1" val="$2"
  [[ -z "$hist" || "$hist" == "null" ]] && hist="[]"
  jq -c --argjson v "$val" --argjson n "$HIST_LEN" \
    '. + [$v] | if length > $n then .[-$n:] else . end' <<<"$hist"
}

old_hist_for() {
  local id="$1"
  [[ -r "$STATE" ]] || { echo "[]"; return; }
  jq -c --argjson id "$id" '.fans[]? | select(.id == $id) | .hist' "$STATE" 2>/dev/null | head -1 || echo "[]"
}

rows=()
if [[ -r "$HW" ]]; then
  while IFS=$'\t' read -r id label path; do
    [[ -z "$id" || -z "$path" ]] && continue
    rpm=$(read_rpm "$path")
    rows+=("${id}|${label}|${rpm}")
  done < <(jq -r '
    .hwmon[]? | select(.name == "msi_wmi_platform" or (.fans | length) > 0) |
    .fans[]? | "\(.idx // 0)\t\(.label // ("FAN" + (.idx|tostring)))\t\(.path)"
  ' "$HW" 2>/dev/null | head -4)
fi

if [[ ${#rows[@]} -eq 0 ]] && command -v sensors >/dev/null 2>&1; then
  local_i=0
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    local_i=$((local_i + 1))
    rpm=$(awk '{print $2}' <<<"$line")
    rows+=("${local_i}|$(awk '{print $1}' <<<"$line")|${rpm}")
  done < <(sensors 2>/dev/null | awk '
    /[Ff]an[0-9]*:/ {
      gsub(/:/, "", $1)
      gsub(/[^0-9]/, "", $2)
      if ($2+0 >= 0) printf "%s %s\n", toupper($1), $2
    }' | head -4)
fi

json_rows=()
for row in "${rows[@]}"; do
  IFS='|' read -r id label rpm <<<"$row"
  label="${label// /}"
  label=$(printf '%s' "$label" | tr '[:lower:]' '[:upper:]')
  pct=$(( rpm * 100 / MAX_RPM ))
  (( pct < 0 )) && pct=0
  (( pct > 100 )) && pct=100
  bar=$(( pct * BAR_MAX / 100 ))
  spark=$(( pct < 4 ? 4 : pct ))
  hist=$(push_hist "$(old_hist_for "$id")" "$spark")
  json_rows+=("$(jq -nc --argjson id "$id" --arg label "$label" --argjson rpm "$rpm" \
    --argjson pct "$pct" --argjson bar "$bar" --argjson hist "$hist" \
    '{id:$id,label:$label,rpm:$rpm,pct:$pct,bar:$bar,hist:$hist}')")
done

if [[ ${#json_rows[@]} -eq 0 ]]; then
  fans='[{"id":1,"label":"FAN1","rpm":0,"pct":0,"bar":0,"hist":[4,4,4,4,4,4,4,4,4,4,4,4,4,4,4,4]}]'
  tooltip="Fan speeds · no sensors"
else
  fans=$(printf '%s\n' "${json_rows[@]}" | jq -sc '.')
  tooltip=$(jq -r '[.[] | "\(.label) \(.rpm) RPM (\(.pct)%)" ] | join(" · ")' <<<"$fans")
fi

jq -nc --argjson fans "$fans" --arg tooltip "$tooltip" '{fans:$fans,tooltip:$tooltip}' | tee "$STATE"
