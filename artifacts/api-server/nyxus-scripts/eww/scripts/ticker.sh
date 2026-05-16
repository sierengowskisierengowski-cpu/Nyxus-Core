#!/usr/bin/env bash
# NYXUS · EWW · top-bar ticker  (live system data + notifications)
#
# rev 2026-05-16 r5: script-driven scroll + notification feed.
#
# How the scroll works:
#   * The full ticker source string (system probes + recent notifications)
#     is cached in /tmp/nyxus-ticker.src and refreshed every $REFRESH_SECS.
#   * A scroll offset is kept in /tmp/nyxus-ticker.off and incremented
#     by $STEP each call.
#   * Each call emits a fixed-width substring window of the source,
#     starting at the offset, wrapping seamlessly via a doubled source.
#   * eww polls this script at 500ms — 3 chars/call ≈ 6 chars/sec
#     smooth horizontal scroll that runs in a continuous big circle.
#
# Live notifications:
#   * Any process can append a line to /tmp/nyxus-notifications.log.
#   * The ticker injects the last 5 lines into the scroll source.
#   * Notifications older than 10 minutes are auto-pruned.
set -u
export LC_ALL=C.UTF-8

CACHE_SRC="/tmp/nyxus-ticker.src"
CACHE_OFF="/tmp/nyxus-ticker.off"
CACHE_STAMP="/tmp/nyxus-ticker.stamp"
NOTIF_LOG="/tmp/nyxus-notifications.log"
REFRESH_SECS=15        # refresh probes + notifs every 15s
STEP=3                 # chars to advance each poll (visual speed)
WINDOW=200             # chars visible in the bar at once

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

  # ── live notifications ─────────────────────────────────────────────
  if [[ -r $NOTIF_LOG ]]; then
    # prune notifications older than 10min (epoch-prefixed lines only)
    cutoff=$(( now - 600 ))
    awk -v c="$cutoff" -F'|' 'NF<2 || $1+0 > c' "$NOTIF_LOG" > "${NOTIF_LOG}.tmp" 2>/dev/null \
      && mv "${NOTIF_LOG}.tmp" "$NOTIF_LOG"
    # inject last 5 notification messages (drop epoch prefix)
    while IFS='|' read -r _ msg; do
      [[ -n $msg ]] && SEGS+=("◆ ${msg}")
    done < <(tail -n 5 "$NOTIF_LOG" 2>/dev/null)
  fi

  src=""
  for s in "${SEGS[@]}"; do src+="${s}     "; done
  printf '%s' "$src" > "$CACHE_SRC"
  printf '%s' "$now" > "$CACHE_STAMP"
fi

src=$(cat "$CACHE_SRC")
src_doubled="${src}${src}"   # doubled so the substring window wraps seamlessly
src_len=${#src}

if (( src_len == 0 )); then
  printf '{"text":"NYXUS · ECLIPSE · LIVE","tooltip":"NYXUS"}\n'
  exit 0
fi

off=$(cat "$CACHE_OFF" 2>/dev/null || echo 0)
off=$(( (off + STEP) % src_len ))
printf '%s' "$off" > "$CACHE_OFF"

view="${src_doubled:$off:$WINDOW}"

view="${view//\\/\\\\}"
view="${view//\"/\\\"}"
TIME=$(date '+%H:%M')
tooltip="NYXUS LIVE · ${TIME} · scrolling system probes + notifications"
tooltip="${tooltip//\"/\\\"}"

printf '{"text":"%s","tooltip":"%s"}\n' "$view" "$tooltip"
