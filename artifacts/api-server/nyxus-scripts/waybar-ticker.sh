#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────
# NYXUS Waybar Marquee Ticker  ·  rev 2026-05-06x
# CONTINUOUS LEFT-SCROLL marquee. Streams one JSON line every ~0.18s.
# A long status string is built every REFRESH seconds, then a fixed-width
# WINDOW slides left across it, wrapping around in a loop (airport-board
# style). Bulletproof: every probe has its own short timeout.
#
# Waybar config:  no "interval" — the script streams forever.
#                 use "exec" + "return-type": "json".
# ─────────────────────────────────────────────────────────────────────────

set -u
export LC_ALL=C.UTF-8

WINDOW=100      # visible chars in the marquee window
SCROLL_SLEEP=0.18   # seconds per character (smaller = faster scroll)
REFRESH=5       # rebuild metrics every N seconds

# ── Build the long status string ────────────────────────────────────────
build_string() {
  local UPTIME KERNEL LOAD MEM CPU DISK NET IP GPU CPUTEMP UPDATES HOST USER WS SEP

  UPTIME=$(uptime -p 2>/dev/null | sed 's/^up //; s/ minutes/m/; s/ minute/m/; s/ hours/h/; s/ hour/h/; s/ days/d/; s/ day/d/; s/, /·/g')
  [ -z "$UPTIME" ] && UPTIME="—"
  KERNEL=$(uname -r 2>/dev/null | cut -d- -f1)
  [ -z "$KERNEL" ] && KERNEL="—"
  LOAD=$(awk '{printf "%.2f", $1}' /proc/loadavg 2>/dev/null)
  [ -z "$LOAD" ] && LOAD="—"
  MEM=$(awk '/MemTotal/ {t=$2} /MemAvailable/ {a=$2} END {if (t>0) printf "%d%%", (t-a)*100/t; else print "—"}' /proc/meminfo 2>/dev/null)
  [ -z "$MEM" ] && MEM="—"
  CPU=$(top -bn1 2>/dev/null | awk '/^%Cpu/ {printf "%d%%", 100 - $8; exit}')
  [ -z "$CPU" ] && CPU="—"
  DISK=$(df / 2>/dev/null | awk 'NR==2 {print $5}')
  [ -z "$DISK" ] && DISK="—"

  if timeout 1 ip route get 1.1.1.1 >/dev/null 2>&1; then
    NET="ONLINE"
    IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}')
  else
    NET="OFFLINE"; IP="—"
  fi
  [ -z "$IP" ] && IP="—"

  CPUTEMP=$(timeout 1 sensors 2>/dev/null | awk '/^Package id 0:|^Tctl:/ {gsub(/\+|°C/,"",$2); printf "%s°C", $2; exit}')
  [ -z "$CPUTEMP" ] && CPUTEMP="—"

  GPU=$(timeout 1 sensors 2>/dev/null | awk '/edge:|GPU:|junction:/ {gsub(/\+|°C/,"",$2); printf "%s°C", $2; exit}')
  [ -z "$GPU" ] && GPU="—"

  UPDATES=$(timeout 4 checkupdates 2>/dev/null | wc -l)
  [ -z "$UPDATES" ] && UPDATES="0"

  HOST=$(hostname 2>/dev/null)
  [ -z "$HOST" ] && HOST="nyxus"
  USER=${USER:-$(whoami 2>/dev/null)}
  [ -z "$USER" ] && USER="nyx"

  WS=$(timeout 1 hyprctl -j activeworkspace 2>/dev/null | awk -F'[:,]' '/"id":/ {gsub(/[ "]/,"",$2); print $2; exit}')
  [ -z "$WS" ] && WS="—"

  SEP="   ◆   "
  printf '%s' \
    "NYXUS · SIERENGOWSKI · 2026${SEP}HOST ${USER}@${HOST}${SEP}WORKSPACE ${WS}${SEP}UPTIME ${UPTIME}${SEP}KERNEL ${KERNEL}${SEP}CPU ${CPU} @ ${CPUTEMP}${SEP}MEM ${MEM}${SEP}LOAD ${LOAD}${SEP}DISK ${DISK}${SEP}GPU ${GPU}${SEP}NET ${NET}${SEP}IP ${IP}${SEP}UPDATES ${UPDATES} pending${SEP}HYPRLAND · WAYLAND${SEP}ARCH LINUX${SEP}BUILT BY HAND${SEP}"
}

# ── Tooltip = pretty-printed full snapshot ──────────────────────────────
build_tooltip() {
  printf '%s' "$1" | awk '
    BEGIN { RS = "   ◆   "; printed = 0 }
    {
      gsub(/^[ \t]+|[ \t]+$/, "");
      if (length($0) == 0) next;
      printf "%s\n", $0;
      printed++;
    }
  '
}

# ── Bash-only JSON escape (no python fork on every tick) ────────────────
esc_json() {
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\n'/\\n}
  s=${s//$'\r'/}
  s=${s//$'\t'/\\t}
  printf '%s' "$s"
}

# ── Main streaming loop ─────────────────────────────────────────────────
OFFSET=0
NEXT_REBUILD=0       # tick counter (no date fork)
TICKS_PER_REFRESH=$(awk -v r="$REFRESH" -v s="$SCROLL_SLEEP" 'BEGIN{printf "%d", r/s}')
(( TICKS_PER_REFRESH < 1 )) && TICKS_PER_REFRESH=1
TICK=0
STR=""
TOOLTIP_BODY=""

while true; do
  if (( TICK >= NEXT_REBUILD )) || [ -z "$STR" ]; then
    STR="$(build_string)"
    NEXT_REBUILD=$(( TICK + TICKS_PER_REFRESH ))
    TOOLTIP_BODY="$(build_tooltip "$STR")"
  fi

  LEN=${#STR}
  if (( LEN <= WINDOW )); then
    WIN="$STR"
  else
    POS=$(( OFFSET % LEN ))
    DOUBLED="${STR}${STR}"
    WIN="${DOUBLED:$POS:$WINDOW}"
  fi

  TXT_ESC=$(esc_json "$WIN")
  TIP_RAW="<span size='x-large' weight='bold' foreground='#e8edf5'>NYXUS · LIVE TICKER</span>
<span size='small' foreground='#9aa0ad'>${TOOLTIP_BODY}</span>"
  TIP_ESC=$(esc_json "$TIP_RAW")

  printf '{"text":"%s","tooltip":"%s","class":"ticker","alt":"ticker"}\n' "$TXT_ESC" "$TIP_ESC"

  OFFSET=$(( OFFSET + 1 ))
  TICK=$(( TICK + 1 ))
  sleep "$SCROLL_SLEEP"
done
