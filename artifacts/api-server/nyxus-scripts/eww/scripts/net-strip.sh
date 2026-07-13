#!/usr/bin/env bash
# NYXUS · EWW · bottom-bar network strip — SSID/signal · ↑↓ rates · IP snippet
# Output: {"text":"...","tooltip":"..."}
set -u
export LC_ALL=C.UTF-8

icon="…"
ssid="OFFLINE"
sig=""
ip=""
rx="--"
tx="--"
tooltip="Network · disconnected"

read_bytes() {
  awk 'NR>2 && $1!~/^lo:/ {gsub(/:/,"",$1); rx+=$2; tx+=$10} END{print rx+0, tx+0}' /proc/net/dev 2>/dev/null
}
fmt_rate() {
  awk -v b="$1" 'BEGIN{
    if (b<1024) printf "%dB", b;
    else if (b<1048576) printf "%.0fK", b/1024;
    else printf "%.1fM", b/1048576;
  }'
}

ip=$(ip -4 addr show 2>/dev/null | awk '/inet /{print $2}' | grep -v '^127' | head -1 | cut -d/ -f1)
[[ -z "$ip" ]] && ip="—"

read -r rx1 tx1 < <(read_bytes)
sleep 0.35
read -r rx2 tx2 < <(read_bytes)
if [[ -n "${rx1:-}" && -n "${rx2:-}" ]]; then
  rx=$(fmt_rate $(( (rx2 - rx1) * 3 )))
  tx=$(fmt_rate $(( (tx2 - tx1) * 3 )))
fi

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
        ssid="$name"
        tooltip="WiFi · $name · ${sig}% · $dev · $ip"
        ;;
      *ethernet*|*wired*)
        icon="⌁"
        ssid="ETH"
        tooltip="Ethernet · $name · $dev · $ip"
        ;;
      *)
        icon="◉"
        ssid="$name"
        tooltip="$type · $name · $ip"
        ;;
    esac
  fi
fi

ip_short="${ip}"
[[ ${#ip_short} -gt 15 ]] && ip_short="${ip_short:0:12}…"

if [[ -n "$sig" ]]; then
  text="${icon} ${ssid} ${sig}% ↑${tx} ↓${rx} ${ip_short}"
else
  text="${icon} ${ssid} ↑${tx} ↓${rx} ${ip_short}"
fi

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg text "$text" --arg tooltip "$tooltip" '{text:$text,tooltip:$tooltip}'
else
  text="${text//\"/}"; tooltip="${tooltip//\"/}"
  printf '{"text":"%s","tooltip":"%s"}\n' "$text" "$tooltip"
fi
