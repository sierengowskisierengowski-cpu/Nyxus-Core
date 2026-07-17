#!/usr/bin/env bash
# NYXUS . EWW . bottom-bar network live graph (Phase 6, rev 2026-07-14b)
# Up/down throughput as rolling block-character sparklines (ghost-HUD
# label render) + compact rates + connection identity.
#
# Output: {"ssid":"ETH","icon":"...","up_fmt":"7K","down_fmt":"54K",
#          "up_spark":"...","down_spark":"...","tooltip":"..."}
set -u
export LC_ALL=C.UTF-8

STATE_DIR="${XDG_RUNTIME_DIR:-/tmp}/nyxus-net-graph"
STATE="${STATE_DIR}/hist.csv"    # 2 lines: down / up (0..100 log-scaled)
HIST_LEN=24
mkdir -p "${STATE_DIR}"
BLOCKS=( "▁" "▂" "▃" "▄" "▅" "▆" "▇" "█" )
have() { command -v "$1" >/dev/null 2>&1; }

spark() {
  local csv="$1" out="" v lvl
  local -a a
  IFS=',' read -r -a a <<<"$csv"
  (( ${#a[@]} == 0 )) && { printf '%s' "${BLOCKS[0]}"; return; }
  for v in "${a[@]}"; do
    [[ "$v" =~ ^[0-9]+$ ]] || v=0
    lvl=$(( v * 7 / 100 ))
    (( lvl < 0 )) && lvl=0; (( lvl > 7 )) && lvl=7
    out+="${BLOCKS[$lvl]}"
  done
  printf '%s' "$out"
}

trim() {
  awk -v s="$1" -v n="$HIST_LEN" 'BEGIN{k=split(s,a,","); st=(k>n?k-n+1:1);
    for(i=st;i<=k;i++) printf (i>st?",":"") a[i]}'
}

read_bytes() {
  awk 'NR>2 && $1!~/^lo:/ {gsub(/:/,"",$1); rx+=$2; tx+=$10} END{print rx+0, tx+0}' /proc/net/dev 2>/dev/null
}
fmt_rate() {
  awk -v b="$1" 'BEGIN{
    if (b < 1024) printf "%dB", b;
    else if (b < 1048576) printf "%.0fK", b/1024;
    else printf "%.1fM", b/1048576; }'
}
log_pct() {  # bytes/s -> 0..100 on a log scale topping at ~10 MB/s
  awk -v b="$1" 'BEGIN{
    if (b <= 0) { print 0; exit }
    x = log(b+1) / log(10485760) * 100
    if (x < 0) x = 0; if (x > 100) x = 100
    printf "%d", int(x) }'
}

# ---- sample throughput ---------------------------------------------------
read -r rx1 tx1 < <(read_bytes)
sleep 0.35
read -r rx2 tx2 < <(read_bytes)
rx_bps=0; tx_bps=0
if [[ -n "${rx1:-}" && -n "${rx2:-}" ]]; then
  rx_bps=$(( (rx2 - rx1) * 3 )); (( rx_bps < 0 )) && rx_bps=0
  tx_bps=$(( (tx2 - tx1) * 3 )); (( tx_bps < 0 )) && tx_bps=0
fi

# ---- connection identity -------------------------------------------------
icon="~"; ssid="OFFLINE"; tooltip="Network . disconnected"
ip=$(ip -4 addr show 2>/dev/null | awk '/inet /{print $2}' | grep -v '^127' | head -1 | cut -d/ -f1)
[[ -z "$ip" ]] && ip="-"
if have nmcli; then
  active=$(nmcli -t -f NAME,TYPE,DEVICE connection show --active 2>/dev/null | head -1)
  if [[ -n "$active" ]]; then
    name=$(cut -d: -f1 <<<"$active"); type=$(cut -d: -f2 <<<"$active"); dev=$(cut -d: -f3 <<<"$active")
    case "$type" in
      *wireless*)
        sig=$(nmcli -t -f IN-USE,SIGNAL device wifi list 2>/dev/null | awk -F: '/^\*/{print $2; exit}')
        icon="󰖩"; ssid="$name"
        tooltip="WiFi . $name . ${sig:-0}% . $dev . $ip" ;;
      *ethernet*|*wired*)
        icon="󰈀"; ssid="ETH"
        tooltip="Ethernet . $name . $dev . $ip" ;;
      *)
        icon="󰛳"; ssid="$name"
        tooltip="$type . $name . $ip" ;;
    esac
  fi
fi

# ---- roll histories + sparklines ------------------------------------------
down_pct=$(log_pct "$rx_bps"); up_pct=$(log_pct "$tx_bps")
dh=""; uh=""
if [[ -r "$STATE" ]]; then { read -r dh; read -r uh; } < "$STATE"; fi
dh=$(trim "${dh:+$dh,}$down_pct")
uh=$(trim "${uh:+$uh,}$up_pct")
printf '%s\n%s\n' "$dh" "$uh" > "$STATE"

printf '{"ssid":"%s","icon":"%s","up_fmt":"%s","down_fmt":"%s","up_spark":"%s","down_spark":"%s","tooltip":"%s"}\n' \
  "${ssid//\"/}" "$icon" "$(fmt_rate "$tx_bps")" "$(fmt_rate "$rx_bps")" \
  "$(spark "$uh")" "$(spark "$dh")" "${tooltip//\"/}"
