#!/usr/bin/env bash
# NYXUS · EWW · top-bar ticker  (live system data, JSON for eww)
# Outputs a single-line JSON {"text":"…","tooltip":"…"} that the marquee
# label in eww.yuck consumes. Restarted every 3s by defpoll.
set -u
export LC_ALL=C.UTF-8

# ── fast probes ──────────────────────────────────────────────────────
UP=$(uptime -p 2>/dev/null | sed 's/^up //')
LOAD=$(awk '{print $1, $2, $3}' /proc/loadavg 2>/dev/null)
PROCS=$(ps -e --no-headers 2>/dev/null | wc -l)
USERS=$(who | wc -l)
KERN=$(uname -r 2>/dev/null)
HOST=$(hostname 2>/dev/null)
DISK=$(df -h --output=pcent / 2>/dev/null | tail -1 | tr -d ' %')
INET=$(ip -4 addr show 2>/dev/null | awk '/inet /{print $2}' | grep -v '^127' | head -1)
GW=$(ip route 2>/dev/null | awk '/default/{print $3; exit}')

cpu=$(top -bn1 2>/dev/null | awk '/Cpu\(s\)/{printf "%d", $2+$4}')
mem=$(free -m 2>/dev/null | awk '/Mem:/{printf "%d", $3/$2*100}')
temp_file="/sys/class/thermal/thermal_zone0/temp"
[[ -r $temp_file ]] && TEMP="$(awk '{printf "%d", $1/1000}' "$temp_file")°C" || TEMP="--"

WIFI=""
if command -v nmcli >/dev/null 2>&1; then
  WIFI=$(nmcli -t -f IN-USE,SSID,SIGNAL device wifi list 2>/dev/null \
         | awk -F: '/^\*/{print $2 " " $3 "%"; exit}')
fi

PKG=""
if command -v pacman >/dev/null 2>&1; then
  PKG=$(pacman -Qq 2>/dev/null | wc -l)
fi

TIME=$(date '+%H:%M:%S')

# ── compose segments and shuffle ─────────────────────────────────────
SEGS=(
  "▌ TIME ${TIME}"
  "▌ HOST ${HOST:-?}"
  "▌ KERNEL ${KERN:-?}"
  "▌ UPTIME ${UP:-?}"
  "▌ LOAD ${LOAD:-? ? ?}"
  "▌ CPU ${cpu:-?}%"
  "▌ MEM ${mem:-?}%"
  "▌ TEMP ${TEMP}"
  "▌ DISK ${DISK:-?}%"
  "▌ PROCS ${PROCS:-?}"
  "▌ USERS ${USERS:-?}"
  "▌ NET ${INET:-offline}"
  "▌ GW ${GW:-—}"
  "▌ WIFI ${WIFI:-—}"
  "▌ PKGS ${PKG:-?}"
  "▌ NYXUS · DARK MIRROR"
)

# Fisher-Yates-ish shuffle so the user never sees the same loop twice.
for ((i=${#SEGS[@]}-1; i>0; i--)); do
  j=$(( RANDOM % (i + 1) ))
  tmp="${SEGS[i]}"
  SEGS[i]="${SEGS[j]}"
  SEGS[j]="$tmp"
done

text=""
for s in "${SEGS[@]}"; do text+="${s}   "; done

# JSON-escape minimally (eww label only needs " and \ escaped).
text="${text//\\/\\\\}"
text="${text//\"/\\\"}"
tooltip="NYXUS LIVE · ${TIME} · CPU ${cpu}% · MEM ${mem}% · TEMP ${TEMP} · NET ${INET:-offline}"
tooltip="${tooltip//\"/\\\"}"

printf '{"text":"%s","tooltip":"%s"}\n' "$text" "$tooltip"
