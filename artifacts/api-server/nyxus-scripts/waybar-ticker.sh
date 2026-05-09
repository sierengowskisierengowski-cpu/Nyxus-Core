#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────
# NYXUS Waybar Marquee Ticker  ·  rev r22 · 2026-05-09
# CONTINUOUS LEFT-SCROLL marquee streamed as JSON, one line every SCROLL_SLEEP.
# A long REAL-LIVE status string is rebuilt every REFRESH seconds, then a
# fixed-width WINDOW slides left across it (airport-board style).
#
# rev r22 — full-bar width (WINDOW=210), structured PROBE_ERRORS array,
# red `.error` class emitted whenever ANY probe fails so the user can see
# the failure live in the bar. Tooltip shows the actual failing probes.
# ─────────────────────────────────────────────────────────────────────────

set -u
export LC_ALL=C.UTF-8

WINDOW=380          # visible chars — overflows even a 1920px bar so the
                    # marquee text fills the slab EDGE-TO-EDGE without any
                    # center-padding on either side. Anything that doesn't
                    # fit in the bar is naturally clipped by waybar; the
                    # marquee shifts one char per tick so the user sees
                    # continuous left-scroll across the full width.
SCROLL_SLEEP=0.18   # seconds per character (smaller = faster scroll)
REFRESH=5           # rebuild metrics every N seconds

# Probe failure tracker — populated by build_string each rebuild.
PROBE_ERRORS=""

# ── Build the long status string ────────────────────────────────────────
build_string() {
  local UPTIME KERNEL LOAD MEM CPU DISK NET IP GPU CPUTEMP UPDATES HOST USER WS SEP NOW BAT
  local errs=""

  UPTIME=$(uptime -p 2>/dev/null | sed 's/^up //; s/ minutes/m/; s/ minute/m/; s/ hours/h/; s/ hour/h/; s/ days/d/; s/ day/d/; s/, /·/g')
  if [ -z "$UPTIME" ]; then UPTIME="ERR"; errs="${errs}uptime "; fi

  KERNEL=$(uname -r 2>/dev/null | cut -d- -f1)
  if [ -z "$KERNEL" ]; then KERNEL="ERR"; errs="${errs}kernel "; fi

  LOAD=$(awk '{printf "%.2f", $1}' /proc/loadavg 2>/dev/null)
  if [ -z "$LOAD" ]; then LOAD="ERR"; errs="${errs}loadavg "; fi

  MEM=$(awk '/MemTotal/ {t=$2} /MemAvailable/ {a=$2} END {if (t>0) printf "%d%%", (t-a)*100/t; else print ""}' /proc/meminfo 2>/dev/null)
  if [ -z "$MEM" ]; then MEM="ERR"; errs="${errs}meminfo "; fi

  CPU=$(top -bn1 2>/dev/null | awk '/^%Cpu/ {printf "%d%%", 100 - $8; exit}')
  if [ -z "$CPU" ]; then CPU="ERR"; errs="${errs}cpu "; fi

  DISK=$(df / 2>/dev/null | awk 'NR==2 {print $5}')
  if [ -z "$DISK" ]; then DISK="ERR"; errs="${errs}disk "; fi

  if timeout 1 ip route get 1.1.1.1 >/dev/null 2>&1; then
    NET="ONLINE"
    IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}')
    [ -z "$IP" ] && { IP="ERR"; errs="${errs}net-ip "; }
  else
    NET="OFFLINE"; IP="—"
    errs="${errs}offline "
  fi

  CPUTEMP=$(timeout 1 sensors 2>/dev/null | awk '/^Package id 0:|^Tctl:/ {gsub(/\+|°C/,"",$2); printf "%s°C", $2; exit}')
  [ -z "$CPUTEMP" ] && CPUTEMP="—"     # sensors is optional, no error

  GPU=$(timeout 1 sensors 2>/dev/null | awk '/edge:|GPU:|junction:/ {gsub(/\+|°C/,"",$2); printf "%s°C", $2; exit}')
  [ -z "$GPU" ] && GPU="—"

  UPDATES=$(timeout 4 checkupdates 2>/dev/null | wc -l)
  [ -z "$UPDATES" ] && UPDATES="0"

  HOST=$(hostname 2>/dev/null);     [ -z "$HOST" ] && HOST="nyxus"
  USER=${USER:-$(whoami 2>/dev/null)};  [ -z "$USER" ] && USER="nyx"

  WS=$(timeout 1 hyprctl -j activeworkspace 2>/dev/null | awk -F'[:,]' '/"id":/ {gsub(/[ "]/,"",$2); print $2; exit}')
  [ -z "$WS" ] && WS="—"

  # Battery — present on laptops only, optional
  BAT="—"
  for b in /sys/class/power_supply/BAT*; do
    if [ -d "$b" ]; then
      cap=$(cat "$b/capacity" 2>/dev/null)
      sta=$(cat "$b/status" 2>/dev/null)
      if [ -n "$cap" ]; then BAT="${cap}% ${sta}"; break; fi
    fi
  done

  NOW=$(date '+%a %d · %H:%M:%S' 2>/dev/null)
  [ -z "$NOW" ] && NOW="—"

  # Publish probe errors (newline-joined for tooltip readability)
  PROBE_ERRORS="${errs}"

  SEP="   ◆   "
  printf '%s' \
"NYXUS · SIERENGOWSKI · 2026${SEP}HOST ${USER}@${HOST}${SEP}WS ${WS}${SEP}UPTIME ${UPTIME}${SEP}KERNEL ${KERNEL}${SEP}CPU ${CPU} @ ${CPUTEMP}${SEP}MEM ${MEM}${SEP}LOAD ${LOAD}${SEP}DISK ${DISK}${SEP}GPU ${GPU}${SEP}BAT ${BAT}${SEP}NET ${NET}${SEP}IP ${IP}${SEP}UPDATES ${UPDATES} pending${SEP}${NOW}${SEP}HYPRLAND · WAYLAND · ARCH LINUX${SEP}"
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
  if [ -n "$PROBE_ERRORS" ]; then
    CLASS="error"
    ERR_LINE="<span size='small' foreground='#ff6464'>⚠ failed probes: ${PROBE_ERRORS}</span>"
  else
    CLASS="ok"
    ERR_LINE="<span size='small' foreground='#7aff7a'>● all probes nominal</span>"
  fi
  TIP_RAW="<span size='x-large' weight='bold' foreground='#e8edf5'>NYXUS · LIVE TICKER</span>
${ERR_LINE}
<span size='small' foreground='#9aa0ad'>${TOOLTIP_BODY}</span>"
  TIP_ESC=$(esc_json "$TIP_RAW")

  printf '{"text":"%s","tooltip":"%s","class":"%s","alt":"%s"}\n' "$TXT_ESC" "$TIP_ESC" "$CLASS" "$CLASS"

  OFFSET=$(( OFFSET + 1 ))
  TICK=$(( TICK + 1 ))
  sleep "$SCROLL_SLEEP"
done
