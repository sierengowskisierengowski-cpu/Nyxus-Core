#!/usr/bin/env bash
# NYXUS · EWW · network probe  (wifi SSID + signal, or wired/none)
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
        label="WIRED"
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

printf '{"icon":"%s","label":"%s","tooltip":"%s"}\n' "$icon" "$label" "$tooltip"
