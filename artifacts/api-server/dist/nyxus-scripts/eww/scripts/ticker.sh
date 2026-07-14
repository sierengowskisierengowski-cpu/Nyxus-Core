#!/usr/bin/env bash
# NYXUS · EWW · top-bar ticker  (live system data, JSON for eww)
# Outputs a single-line JSON {"text":"…","tooltip":"…"} consumed by the
# marquee `.ticker` label in eww.yuck (CSS @keyframes nyx-marquee).
#
# Design note (rev 2026-05-12): the previous version shuffled segments
# every 3s which RESET the CSS animation each tick, killing the smooth
# scroll. This version emits a STABLE ordered string and is polled
# infrequently (TICKER defpoll lowered to 30s in eww.yuck), so the
# marquee animation runs uninterrupted between updates. Time-of-day
# is intentionally rendered down to minutes (HH:MM) so the string
# stays identical across consecutive seconds — eww only redraws when
# the JSON actually changes.
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

# Minute-resolution clock — keeps the string stable across seconds so
# eww doesn't redraw and reset the marquee animation 30 times a minute.
TIME=$(date '+%H:%M')

# ── compose stable segment chain (NO shuffle) ────────────────────────
SEGS=(
  "▌ NYXUS · DARK MIRROR"
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

text=""
for s in "${SEGS[@]}"; do text+="${s}     "; done
# Duplicate the chain so when the marquee scrolls past the end there's
# no visible gap before the loop restarts — the second copy fills the
# void while the animation rewinds via @keyframes margin-left reset.
text="${text}${text}"

# JSON-escape minimally (eww label only needs " and \ escaped).
text="${text//\\/\\\\}"
text="${text//\"/\\\"}"
tooltip="NYXUS LIVE · ${TIME} · CPU ${cpu}% · MEM ${mem}% · TEMP ${TEMP} · NET ${INET:-offline}"
tooltip="${tooltip//\"/\\\"}"

printf '{"text":"%s","tooltip":"%s"}\n' "$text" "$tooltip"
