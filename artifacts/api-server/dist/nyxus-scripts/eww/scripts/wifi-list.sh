#!/usr/bin/env bash
# NYXUS · EWW · wifi list (passive — uses last cached scan)
#
# rev r9-eww 2026-05-11 hardening:
#   • SSIDs are base64-encoded into a `b64` field so EWW onclick handlers
#     never interpolate raw SSIDs into shell commands. Display SSID stays
#     in `ssid` (rendered as a label only — never spliced into a command).
#   • Active rescans removed from the poll path. Use wifi-action.sh rescan
#     (button) to refresh; the kernel/nm cache is read passively here.
set -u

enabled="false"
current=""
networks="[]"

if command -v nmcli >/dev/null 2>&1; then
  if nmcli radio wifi 2>/dev/null | grep -qi enabled; then
    enabled="true"
    current=$(nmcli -t -f NAME,TYPE connection show --active 2>/dev/null \
              | awk -F: '$2 ~ /wireless/ {print $1; exit}')

    rows=$(nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY device wifi list 2>/dev/null \
           | awk -F: 'NF>=4 && $2 != ""')

    if [[ -n "$rows" && -x "$(command -v jq)" ]]; then
      networks=$(printf '%s\n' "$rows" | jq -Rsc '
        split("\n") | map(select(length>0)) | map(
          split(":") as $p
          | ($p[2]|tonumber? // 0) as $sig
          | ($p[1]) as $ssid
          | {
              ssid: $ssid,
              b64:  ($ssid | @base64),
              signal: $sig,
              bars: (if $sig>=75 then "▰▰▰▰" elif $sig>=50 then "▰▰▰▱" elif $sig>=25 then "▰▰▱▱" else "▰▱▱▱" end),
              security: (if ($p[3]|length)==0 then "open" else $p[3] end),
              active: ($p[0]=="*"),
              icon: (if ($p[3]|length)==0 then "○" else "◉" end)
            }
        ) | unique_by(.ssid) | sort_by(-.signal)
      ')
    fi
  fi
fi

[[ -z "$networks" ]] && networks="[]"
current_b64=$(printf '%s' "$current" | base64 -w0 2>/dev/null || true)

if command -v jq >/dev/null 2>&1; then
  jq -nc --argjson nets "$networks" --arg enabled "$enabled" \
         --arg current "$current" --arg current_b64 "$current_b64" \
    '{networks:$nets, enabled:$enabled, current:$current, current_b64:$current_b64}'
else
  printf '{"networks":%s,"enabled":"%s","current":"","current_b64":""}\n' "$networks" "$enabled"
fi
