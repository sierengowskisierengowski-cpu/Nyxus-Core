#!/usr/bin/env bash
# NYXUS · EWW · bottom-bar network sparklines + rates
# Output: {"ssid":"ETH","ip":"192.168.1.1","up":7500,"down":54000,"up_fmt":"7K","down_fmt":"54K","up_hist":[...],"down_hist":[...],"tooltip":"..."}
set -u
export LC_ALL=C.UTF-8

STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/nyxus-net-graph"
STATE="${STATE_DIR}/state.json"
HIST_LEN=16
BAR_MAX=48

mkdir -p "${STATE_DIR}"

read_bytes() {
  awk 'NR>2 && $1!~/^lo:/ {gsub(/:/,"",$1); rx+=$2; tx+=$10} END{print rx+0, tx+0}' /proc/net/dev 2>/dev/null
}

fmt_rate() {
  awk -v b="$1" 'BEGIN{
    if (b < 1024) printf "%dB", b;
    else if (b < 1048576) printf "%.0fK", b/1024;
    else printf "%.1fM", b/1048576;
  }'
}

bar_of() {
  awk -v b="$1" 'BEGIN{
  # log-ish scale: 0..10M -> 4..48px
    if (b <= 0) { print 4; exit }
    x = log(b+1) / log(10485760) * 44 + 4
    if (x < 4) x = 4
    if (x > 48) x = 48
    printf "%d", int(x)
  }'
}

spark_of() {
  bar_of "$1"
}

shift_hist() {
  local json="$1" val="$2"
  command -v jq >/dev/null 2>&1 || { echo "[$val]"; return; }
  jq -c --argjson v "$val" --argjson n "$HIST_LEN" '
    . as $h | ($h + [$v]) | if length > $n then .[-$n:] else . end
  ' <<<"$json" 2>/dev/null || echo "[$val]"
}

icon="…"
ssid="OFFLINE"
sig=""
ip="—"
rx_bps=0
tx_bps=0
tooltip="Network · disconnected"

ip=$(ip -4 addr show 2>/dev/null | awk '/inet /{print $2}' | grep -v '^127' | head -1 | cut -d/ -f1)
[[ -z "$ip" ]] && ip="—"

read -r rx1 tx1 < <(read_bytes)
sleep 0.35
read -r rx2 tx2 < <(read_bytes)
if [[ -n "${rx1:-}" && -n "${rx2:-}" ]]; then
  rx_bps=$(( (rx2 - rx1) * 3 ))
  tx_bps=$(( (tx2 - tx1) * 3 ))
  (( rx_bps < 0 )) && rx_bps=0
  (( tx_bps < 0 )) && tx_bps=0
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

up_fmt=$(fmt_rate "$tx_bps")
down_fmt=$(fmt_rate "$rx_bps")
up_bar=$(spark_of "$tx_bps")
down_bar=$(spark_of "$rx_bps")

up_hist="[]"
down_hist="[]"
if [[ -r "$STATE" ]] && command -v jq >/dev/null 2>&1; then
  up_hist=$(jq -c '.up_hist // []' "$STATE" 2>/dev/null)
  down_hist=$(jq -c '.down_hist // []' "$STATE" 2>/dev/null)
fi
up_hist=$(shift_hist "$up_hist" "$up_bar")
down_hist=$(shift_hist "$down_hist" "$down_bar")

ip_short="$ip"
[[ ${#ip_short} -gt 14 ]] && ip_short="${ip_short:0:11}…"

if command -v jq >/dev/null 2>&1; then
  jq -nc \
    --arg ssid "$ssid" --arg icon "$icon" --arg ip "$ip_short" --arg sig "$sig" \
    --argjson up "$tx_bps" --argjson down "$rx_bps" \
    --arg up_fmt "$up_fmt" --arg down_fmt "$down_fmt" \
    --argjson up_bar "$up_bar" --argjson down_bar "$down_bar" \
    --argjson up_hist "$up_hist" --argjson down_hist "$down_hist" \
    --arg tooltip "$tooltip" \
    '{ssid:$ssid,icon:$icon,ip:$ip,sig:$sig,up:$up,down:$down,up_fmt:$up_fmt,down_fmt:$down_fmt,up_bar:$up_bar,down_bar:$down_bar,up_hist:$up_hist,down_hist:$down_hist,tooltip:$tooltip}' \
    | tee "$STATE"
else
  printf '{"ssid":"%s","ip":"%s","up_fmt":"%s","down_fmt":"%s","tooltip":"%s"}\n' \
    "$ssid" "$ip_short" "$up_fmt" "$down_fmt" "$tooltip"
fi
