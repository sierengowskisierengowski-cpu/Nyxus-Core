#!/usr/bin/env bash
# NYXUS · EWW · saved wifi connections + active link details
# Emits {saved:[{name,b64,active,autoconnect}], details:{iface,ip,gw,dns}}
# Names travel base64-encoded (b64) into click handlers — same hardening
# contract as wifi-list.sh (rev r9-eww).
set -u

saved="[]"
details='{"iface":"","ip":"","gw":"","dns":""}'

if command -v nmcli >/dev/null 2>&1 && command -v jq >/dev/null 2>&1; then
  rows=$(nmcli -t -f NAME,TYPE,ACTIVE,AUTOCONNECT connection show 2>/dev/null \
         | awk -F: '$2 ~ /wireless/')
  if [[ -n "$rows" ]]; then
    saved=$(printf '%s\n' "$rows" | jq -Rsc '
      split("\n") | map(select(length>0)) | map(
        split(":") as $p
        | {
            name: $p[0],
            b64:  ($p[0] | @base64),
            active: ($p[2] == "yes"),
            autoconnect: ($p[3] == "yes")
          }
      ) | sort_by(.active | not)')
  fi

  # active wifi device details (falls back to any connected device)
  dev=$(nmcli -t -f DEVICE,TYPE,STATE device status 2>/dev/null \
        | awk -F: '$2=="wifi" && $3=="connected" {print $1; exit}')
  if [[ -n "${dev:-}" ]]; then
    ip=$(nmcli -t -f IP4.ADDRESS device show "$dev" 2>/dev/null | head -1 | cut -d: -f2)
    gw=$(nmcli -t -f IP4.GATEWAY device show "$dev" 2>/dev/null | head -1 | cut -d: -f2)
    dns=$(nmcli -t -f IP4.DNS device show "$dev" 2>/dev/null | cut -d: -f2 | paste -sd' ')
    details=$(jq -nc --arg iface "$dev" --arg ip "${ip:-}" --arg gw "${gw:-}" --arg dns "${dns:-}" \
      '{iface:$iface, ip:$ip, gw:$gw, dns:$dns}')
  fi
fi

if command -v jq >/dev/null 2>&1; then
  jq -nc --argjson saved "$saved" --argjson details "$details" \
    '{saved:$saved, details:$details}'
else
  printf '{"saved":[],"details":%s}\n' "$details"
fi
