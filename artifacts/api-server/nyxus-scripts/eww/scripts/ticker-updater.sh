#!/usr/bin/env bash
# NYXUS · EWW · ticker background updater
#
# rev 2026-05-16 r1 — long-running companion to ticker.sh.
#
# Refreshes /tmp/nyxus-ticker.src every $INTERVAL seconds with live
# system probes and recent notifications. ticker.sh (the fast eww
# poll script) reads that cache and emits a scrolling substring.
#
# This script self-terminates if a duplicate is already running, so
# ticker.sh can safely re-spawn it on every poll.

set -u
export LC_ALL=C.UTF-8

CACHE_SRC="/tmp/nyxus-ticker.src"
CACHE_TMP="/tmp/nyxus-ticker.src.new"
PIDFILE="/tmp/nyxus-ticker.updater.pid"
NOTIF_LOG="/tmp/nyxus-notifications.log"
INTERVAL=5

# Single-instance guard.
if [[ -r $PIDFILE ]]; then
  other=$(cat "$PIDFILE" 2>/dev/null || echo "")
  if [[ -n $other ]] && [[ "$other" != "$$" ]] && kill -0 "$other" 2>/dev/null; then
    exit 0
  fi
fi
echo $$ > "$PIDFILE"
trap 'rm -f "$PIDFILE"' EXIT

# Pre-compute slow values once at startup.
HOST=$(hostname 2>/dev/null || echo "nyxus")
KERN=$(uname -r 2>/dev/null || echo "?")
PKG=""
if command -v pacman >/dev/null 2>&1; then
  PKG=$(ls /var/lib/pacman/local 2>/dev/null | wc -l)
fi

# /proc/stat snapshot helpers — sub-millisecond CPU% computation.
read_cpu_totals() {
  awk '/^cpu /{print $2+$3+$4+$5+$6+$7+$8, $5}' /proc/stat 2>/dev/null
}
last_total=0; last_idle=0
read -r last_total last_idle < <(read_cpu_totals)

while :; do
  sleep "$INTERVAL"

  # ── CPU % via /proc/stat delta ───────────────────────────────────
  read -r total idle < <(read_cpu_totals)
  dt=$(( total - last_total ))
  di=$(( idle  - last_idle ))
  if (( dt > 0 )); then
    cpu=$(( 100 * (dt - di) / dt ))
  else
    cpu=0
  fi
  last_total=$total
  last_idle=$idle

  # ── memory % via /proc/meminfo ───────────────────────────────────
  mem=$(awk '
    /^MemTotal:/     {t=$2}
    /^MemAvailable:/ {a=$2}
    END { if (t>0) printf "%d", (t-a)*100/t; else print 0 }
  ' /proc/meminfo 2>/dev/null)

  # ── temperature ──────────────────────────────────────────────────
  temp_file="/sys/class/thermal/thermal_zone0/temp"
  if [[ -r $temp_file ]]; then
    TEMP="$(awk '{printf "%d", $1/1000}' "$temp_file")°C"
  else
    TEMP="--"
  fi

  # ── light system info ────────────────────────────────────────────
  UP=$(uptime -p 2>/dev/null | sed 's/^up //')
  LOAD=$(awk '{print $1, $2, $3}' /proc/loadavg 2>/dev/null)
  PROCS=$(ls /proc 2>/dev/null | grep -c '^[0-9]')
  USERS=$(who 2>/dev/null | wc -l)
  DISK=$(df -h --output=pcent / 2>/dev/null | tail -1 | tr -d ' %')
  INET=$(ip -4 addr show 2>/dev/null | awk '/inet /{print $2}' | grep -v '^127' | head -1)
  GW=$(ip route 2>/dev/null | awk '/default/{print $3; exit}')
  TIME=$(date '+%H:%M')

  SEGS=(
    "▌ NYXUS · ECLIPSE"
    "▌ TIME ${TIME}"
    "▌ HOST ${HOST}"
    "▌ KERNEL ${KERN}"
    "▌ UPTIME ${UP:-?}"
    "▌ LOAD ${LOAD:-? ? ?}"
    "▌ CPU ${cpu}%"
    "▌ MEM ${mem}%"
    "▌ TEMP ${TEMP}"
    "▌ DISK ${DISK:-?}%"
    "▌ PROCS ${PROCS:-?}"
    "▌ USERS ${USERS:-?}"
    "▌ NET ${INET:-offline}"
    "▌ GW ${GW:-—}"
    "▌ PKGS ${PKG:-?}"
  )

  # ── live notifications (last 5, <10min old) ──────────────────────
  if [[ -r $NOTIF_LOG ]]; then
    now=$(date +%s)
    cutoff=$(( now - 600 ))
    awk -v c="$cutoff" -F'|' 'NF<2 || $1+0 > c' "$NOTIF_LOG" \
      > "${NOTIF_LOG}.tmp" 2>/dev/null && mv "${NOTIF_LOG}.tmp" "$NOTIF_LOG"
    while IFS='|' read -r _ msg; do
      [[ -n $msg ]] && SEGS+=("◆ ${msg}")
    done < <(tail -n 5 "$NOTIF_LOG" 2>/dev/null)
  fi

  src=""
  for s in "${SEGS[@]}"; do src+="${s}     "; done

  printf '%s' "$src" > "$CACHE_TMP" && mv "$CACHE_TMP" "$CACHE_SRC"
done
