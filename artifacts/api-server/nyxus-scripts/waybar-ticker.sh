#!/usr/bin/env bash
# NYXUS Airport-Style Looping Marquee Ticker
# Scrolls continuously left→right→wrap, like an airport departure board
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED

STATE="/tmp/nyxus-ticker-pos"
WIDTH=110  # chars shown at once — fills the left side of the top bar

# ── Gather live stats ──────────────────────────────────────────────────────────
CPU=$(top -bn1 2>/dev/null | awk '/Cpu\(s\)/{printf "%.0f", $2+$4}' | head -1 2>/dev/null || echo "?")
RAM=$(free 2>/dev/null | awk '/Mem:/{printf "%.0f", $3/$2*100}')
DISK=$(df -h / 2>/dev/null | awk 'NR==2{print $5}')
TIME=$(date "+%H:%M:%S")
DATE=$(date "+%a  %b %d  %Y")

# CPU Temp
TEMP="--"
for z in /sys/class/thermal/thermal_zone*/temp; do
  [[ -f "$z" ]] && TEMP=$(awk '{printf "%.0f", $1/1000}' "$z") && break
done

# Battery
BAT=$(cat /sys/class/power_supply/BAT*/capacity 2>/dev/null | head -1 || echo "--")
BAT_STATUS=$(cat /sys/class/power_supply/BAT*/status 2>/dev/null | head -1 || echo "")
[[ "$BAT_STATUS" == "Charging" ]] && BAT_ICON="⚡" || BAT_ICON="🔋"
[[ "$BAT" == "--" ]] && BAT_STR="NO BAT" || BAT_STR="${BAT_ICON} ${BAT}%"

# WiFi / Network
SSID=$(iwgetid -r 2>/dev/null || nmcli -t -f active,ssid dev wifi 2>/dev/null | grep "^yes" | cut -d: -f2 2>/dev/null || echo "")
[[ -z "$SSID" ]] && SSID="NO WIFI"
IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "--")

# Network speeds via /sys
IF=$(ip route 2>/dev/null | awk '/default/{print $5; exit}')
DN_S="--" ; UP_S="--"
if [[ -n "$IF" && -f "/sys/class/net/$IF/statistics/rx_bytes" ]]; then
  R1=$(cat /sys/class/net/$IF/statistics/rx_bytes)
  T1=$(cat /sys/class/net/$IF/statistics/tx_bytes)
  sleep 0.25
  R2=$(cat /sys/class/net/$IF/statistics/rx_bytes)
  T2=$(cat /sys/class/net/$IF/statistics/tx_bytes)
  DN=$(( (R2 - R1) * 4 / 1024 ))
  UP=$(( (T2 - T1) * 4 / 1024 ))
  [[ $DN -gt 1024 ]] && DN_S="$(awk "BEGIN{printf \"%.1f\", $DN/1024}")MB/s" || DN_S="${DN}KB/s"
  [[ $UP -gt 1024 ]] && UP_S="$(awk "BEGIN{printf \"%.1f\", $UP/1024}")MB/s" || UP_S="${UP}KB/s"
fi

# ── Build the full looping string ─────────────────────────────────────────────
SEP="   ◈   "
T="${SEP}CPU ${CPU}%${SEP}RAM ${RAM}%${SEP}TEMP ${TEMP}°C${SEP}↓ ${DN_S}  ↑ ${UP_S}${SEP}${SSID}  ·  ${IP}${SEP}${BAT_STR}${SEP}DISK ${DISK}${SEP}${DATE}  ·  ${TIME}${SEP}SILENT · DARK · PURELY FUNCTIONAL${SEP}"

LEN=${#T}
POS=$(cat "$STATE" 2>/dev/null || echo 0)
[[ "$POS" -ge "$LEN" || "$POS" -lt 0 ]] && POS=0

# Circular slice — wraps seamlessly
if [[ $((POS + WIDTH)) -le $LEN ]]; then
  SLICE="${T:$POS:$WIDTH}"
else
  REM=$((LEN - POS))
  SLICE="${T:$POS:$REM}${T:0:$((WIDTH - REM))}"
fi

# Advance 3 chars per tick — adjust for speed
echo $(( (POS + 3) % LEN )) > "$STATE"

echo "$SLICE"
