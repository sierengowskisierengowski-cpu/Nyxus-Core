#!/usr/bin/env bash
# NYXUS · EWW · bottom-bar fan strip (MSI msi_wmi / lm_sensors / hw_profile)
# Output: {"text":"FAN1 3200 · FAN2 2800","tooltip":"..."}
set -u
export LC_ALL=C.UTF-8

HW="${HOME}/.config/nyxus/hw_profile.json"
parts=()
tooltip_parts=()

read_rpm() {
  local path="$1"
  [[ -r "$path" ]] || { echo "--"; return; }
  local v
  v=$(<"$path")
  [[ "$v" =~ ^[0-9]+$ ]] && echo "$v" || echo "--"
}

if [[ -r "$HW" ]] && command -v jq >/dev/null 2>&1; then
  while IFS=$'\t' read -r label path; do
    [[ -z "$label" || -z "$path" ]] && continue
    rpm=$(read_rpm "$path")
    short="${label// /}"
    parts+=("${short} ${rpm}")
    tooltip_parts+=("${label}: ${rpm} RPM")
  done < <(jq -r '
    .hwmon[]? | select(.name == "msi_wmi_platform" or (.fans | length) > 0) |
    .fans[]? | "\(.label // ("FAN" + .idx)) \(.path)"
  ' "$HW" 2>/dev/null | head -4)
fi

if [[ ${#parts[@]} -eq 0 ]] && command -v sensors >/dev/null 2>&1; then
  while IFS= read -r line; do
    [[ -z "$line" ]] && continue
    parts+=("$line")
    tooltip_parts+=("$line RPM")
  done < <(sensors 2>/dev/null | awk '
    /[Ff]an[0-9]*:/ {
      gsub(/:/, "", $1)
      gsub(/[^0-9]/, "", $2)
      if ($2+0 > 0) printf "%s %s\n", toupper($1), $2
    }' | head -4)
fi

text="FAN —"
tooltip="Fan speeds · no sensors"
if [[ ${#parts[@]} -gt 0 ]]; then
  text=$(IFS=' · '; echo "${parts[*]}")
  tooltip=$(IFS=' · '; echo "${tooltip_parts[*]}")
fi

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg text "$text" --arg tooltip "$tooltip" '{text:$text,tooltip:$tooltip}'
else
  text="${text//\"/}"; tooltip="${tooltip//\"/}"
  printf '{"text":"%s","tooltip":"%s"}\n' "$text" "$tooltip"
fi
