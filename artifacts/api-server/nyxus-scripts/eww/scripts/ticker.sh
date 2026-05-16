#!/usr/bin/env bash
# NYXUS · EWW · top-bar ticker  (live system data, JSON for eww)
#
# rev 2026-05-16: GTK3 CSS @keyframes margin-left does NOT animate
# label margins reliably across drivers, so we abandoned the pure-CSS
# marquee and switched to a script-driven shifter.
#
# How the scroll works now:
#   * The full ticker source string (system probes) is cached in
#     /tmp/nyxus-ticker.src and refreshed every $REFRESH_SECS.
#   * A scroll offset counter is kept in /tmp/nyxus-ticker.off and
#     incremented by $STEP characters every call.
#   * Each call emits a fixed-width substring window of the source,
#     starting at the offset, wrapping around when it overflows.
#   * eww polls this script at 150ms intervals (set in eww.yuck), so
#     2 chars/call * ~6 calls/sec ≈ 12 chars/sec horizontal scroll —
#     close to a 60-second full-loop on a typical screen-width string.
#
# This entirely avoids GTK CSS animation issues and works on any GTK.
set -u
export LC_ALL=C.UTF-8

CACHE_SRC="/tmp/nyxus-ticker.src"
CACHE_OFF="/tmp/nyxus-ticker.off"
CACHE_STAMP="/tmp/nyxus-ticker.stamp"
REFRESH_SECS=30        # refresh system probes every 30s (string changes infrequently)
STEP=2                 # chars to advance each poll (smoothness vs CPU)
WINDOW=240             # chars visible in the bar at once (overflows are clipped)

now=$(date +%s)
need_refresh=1
if [[ -r $CACHE_STAMP && -r $CACHE_SRC ]]; then
  last=$(cat "$CACHE_STAMP" 2>/dev/null || echo 0)
  (( now - last < REFRESH_SECS )) && need_refresh=0
fi

if (( need_refresh )); then
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
  TIME=$(date '+%H:%M')

  SEGS=(
    "▌ NYXUS · ECLIPSE"
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
  )
  src=""
  for s in "${SEGS[@]}"; do src+="${s}     "; done
  printf '%s' "$src" > "$CACHE_SRC"
  printf '%s' "$now" > "$CACHE_STAMP"
fi

src=$(cat "$CACHE_SRC")
src_doubled="${src}${src}"   # doubled so the substring window can wrap seamlessly
src_len=${#src}

off=$(cat "$CACHE_OFF" 2>/dev/null || echo 0)
off=$(( (off + STEP) % src_len ))
printf '%s' "$off" > "$CACHE_OFF"

# Emit a substring window starting at $off into the doubled source.
# Bash native substring expansion — no awk/python overhead.
view="${src_doubled:$off:$WINDOW}"

# JSON-escape minimally (eww label only needs " and \ escaped).
view="${view//\\/\\\\}"
view="${view//\"/\\\"}"
TIME=$(date '+%H:%M')
tooltip="NYXUS LIVE · ${TIME} · scrolling system probes"
tooltip="${tooltip//\"/\\\"}"

printf '{"text":"%s","tooltip":"%s"}\n' "$view" "$tooltip"
