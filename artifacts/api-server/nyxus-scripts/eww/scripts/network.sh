#!/usr/bin/env bash
# NYXUS · EWW · network probe  (wifi SSID + signal, or wired/none)
# Output is JSON with all dynamic strings escaped via jq so SSIDs
# containing quotes/backslashes can never break the defpoll parse.
set -u

icon="✕"
label="OFFLINE"
tooltip="Network · disconnected"

if command -v nmcli >/dev/null 2>&1; then
  active=$(nmcli -t -f NAME,TYPE,DEVICE connection show --active 2>/dev/null | head -1)
  if [[ -n "$active" ]]; then
    name=$(cut -d: -f1 <<<"$active")
    type=$(cut -d: -f2 <<<"$active")
    dev=$(cut -d: -f3 <<<"$active")
    case "$type" in
      *wireless*)
        sig=$(nmcli -t -f IN-USE,SIGNAL,SSID device wifi list 2>/dev/null | awk -F: '/^\*/{print $2; exit}')
        sig="${sig:-0}"
        if   [[ $sig -ge 75 ]]; then icon="▰▰▰▰"
        elif [[ $sig -ge 50 ]]; then icon="▰▰▰▱"
        elif [[ $sig -ge 25 ]]; then icon="▰▰▱▱"
        else                          icon="▰▱▱▱"
        fi
        label="$name"
        tooltip="WiFi · $name · ${sig}% · $dev"
        ;;
      *ethernet*|*wired*)
        icon="⌁"
        label="ETH"
        tooltip="Ethernet · $name · $dev"
        ;;
      *)
        icon="◉"
        label="$name"
        tooltip="$type · $name"
        ;;
    esac
  fi
fi

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg icon "$icon" --arg label "$label" --arg tooltip "$tooltip" \
    '{icon:$icon,label:$label,tooltip:$tooltip}'
else
  # jq missing fallback: strip risky chars
  label="${label//\"/}"; label="${label//\\/}"
  tooltip="${tooltip//\"/}"; tooltip="${tooltip//\\/}"
  printf '{"icon":"%s","label":"%s","tooltip":"%s"}\n' "$icon" "$label" "$tooltip"
fi
