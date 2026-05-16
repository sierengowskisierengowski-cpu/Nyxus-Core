#!/usr/bin/env bash
# NYXUS · EWW · top-bar ticker  (fast scroll reader)
#
# rev 2026-05-16 r6 — SAFE FOR 500ms POLL.
#
# Design:
#   * This script is the *fast path* called by eww every 500ms.
#     It NEVER calls slow tools (pacman, nmcli, top). It only:
#       1. reads the current cached source string,
#       2. advances a scroll offset,
#       3. emits a fixed-width substring window.
#     Each call completes in <20ms.
#   * A separate background updater (ticker-updater.sh) refreshes
#     the cache every 5s with full live probes. This script spawns
#     the updater on demand if it isn't already running.
#   * Live notifications are read from /tmp/nyxus-notifications.log
#     by the updater (any app can append "EPOCH|message" lines).

set -u
export LC_ALL=C.UTF-8

CACHE_SRC="/tmp/nyxus-ticker.src"
CACHE_OFF="/tmp/nyxus-ticker.off"
UPDATER_PID="/tmp/nyxus-ticker.updater.pid"
UPDATER_BIN="${HOME}/.config/eww/scripts/ticker-updater.sh"
STEP=3        # chars to advance per call (~6 chars/sec at 500ms)
WINDOW=200    # chars visible in the bar at once

# ── make sure the background updater is alive ──────────────────────
need_spawn=1
if [[ -r $UPDATER_PID ]]; then
  pid=$(cat "$UPDATER_PID" 2>/dev/null || echo "")
  if [[ -n $pid ]] && kill -0 "$pid" 2>/dev/null; then
    need_spawn=0
  fi
fi
if (( need_spawn )) && [[ -x $UPDATER_BIN ]]; then
  nohup "$UPDATER_BIN" >/dev/null 2>&1 &
  echo $! > "$UPDATER_PID"
fi

# ── emit a substring of the cache (or a startup placeholder) ────────
if [[ ! -r $CACHE_SRC ]] || [[ ! -s $CACHE_SRC ]]; then
  TIME=$(date '+%H:%M')
  printf '{"text":"▌ NYXUS · ECLIPSE · LIVE   ▌ TIME %s   ▌ INITIALIZING SYSTEM PROBES …     ","tooltip":"NYXUS LIVE · starting"}\n' "$TIME"
  exit 0
fi

src=$(cat "$CACHE_SRC")
src_len=${#src}
if (( src_len == 0 )); then
  printf '{"text":"NYXUS · ECLIPSE · LIVE","tooltip":"NYXUS"}\n'
  exit 0
fi

src_doubled="${src}${src}"
off=$(cat "$CACHE_OFF" 2>/dev/null || echo 0)
[[ $off =~ ^[0-9]+$ ]] || off=0
off=$(( (off + STEP) % src_len ))
printf '%s' "$off" > "$CACHE_OFF"

view="${src_doubled:$off:$WINDOW}"
view="${view//\\/\\\\}"
view="${view//\"/\\\"}"

TIME=$(date '+%H:%M')
tooltip="NYXUS LIVE · ${TIME} · scrolling system probes + notifications"
tooltip="${tooltip//\"/\\\"}"

printf '{"text":"%s","tooltip":"%s"}\n' "$view" "$tooltip"
