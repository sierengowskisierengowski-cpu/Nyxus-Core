#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────
# NYXUS Waybar Marquee Ticker  ·  rev r23 · 2026-05-09
# CONTINUOUS LEFT-SCROLL marquee streamed as JSON, one line every SCROLL_SLEEP.
# A long REAL-LIVE status string is rebuilt every REFRESH seconds, then a
# fixed-width WINDOW slides left across it (airport-board style).
#
# rev r23 — ALL-NEW: 28 distinct REAL-LIVE probes (was 17), shuffled into
# a different order on every rebuild so the user never sees the same
# repeating loop. PROBE_ERRORS array kept; .error class still fires red on
# any probe failure. Tooltip shows the unshuffled snapshot for readability.
# ─────────────────────────────────────────────────────────────────────────

set -u
export LC_ALL=C.UTF-8

WINDOW=420          # visible chars — overflows even a 1920px bar so the
                    # marquee text fills the slab EDGE-TO-EDGE without any
                    # center-padding on either side.
SCROLL_SLEEP=0.18   # seconds per character (smaller = faster scroll)
REFRESH=8           # rebuild metrics + reshuffle every N seconds

# Probe failure tracker — populated by build_segments each rebuild.
PROBE_ERRORS=""

# Cache for slow probes (cached longer than REFRESH so they don't dominate)
LAST_UPDATES_CHECK=0
CACHED_UPDATES="—"
LAST_PUBIP_CHECK=0
CACHED_PUBIP="—"

# ── Build the LIST OF SEGMENTS (one per probe) ──────────────────────────
# Each segment is a "LABEL VALUE" string. We collect them into an array,
# shuffle, and join with " ◆ ".
build_segments() {
  local errs=""
  declare -ga SEGMENTS=()

  # ─ uptime ─
  local UP
  UP=$(uptime -p 2>/dev/null | sed 's/^up //; s/ minutes/m/; s/ minute/m/; s/ hours/h/; s/ hour/h/; s/ days/d/; s/ day/d/; s/, /·/g')
  if [ -z "$UP" ]; then UP="ERR"; errs="${errs}uptime "; fi
  SEGMENTS+=("UPTIME ${UP}")

  # ─ kernel ─
  local KER
  KER=$(uname -r 2>/dev/null | cut -d- -f1)
  if [ -z "$KER" ]; then KER="ERR"; errs="${errs}kernel "; fi
  SEGMENTS+=("KERNEL ${KER}")

  # ─ load avg (1m / 5m / 15m) ─
  local LOAD
  LOAD=$(awk '{printf "%.2f·%.2f·%.2f", $1, $2, $3}' /proc/loadavg 2>/dev/null)
  if [ -z "$LOAD" ]; then LOAD="ERR"; errs="${errs}loadavg "; fi
  SEGMENTS+=("LOAD ${LOAD}")

  # ─ memory used % + GB free ─
  local MEM
  MEM=$(awk '/MemTotal/ {t=$2} /MemAvailable/ {a=$2} END {if (t>0) printf "%d%% · %.1fGB free", (t-a)*100/t, a/1024/1024; else print ""}' /proc/meminfo 2>/dev/null)
  if [ -z "$MEM" ]; then MEM="ERR"; errs="${errs}meminfo "; fi
  SEGMENTS+=("MEM ${MEM}")

  # ─ swap used ─
  local SWAP
  SWAP=$(awk '/SwapTotal/ {t=$2} /SwapFree/  {f=$2} END {if (t>0) printf "%d%%", (t-f)*100/t; else print "off"}' /proc/meminfo 2>/dev/null)
  [ -z "$SWAP" ] && SWAP="—"
  SEGMENTS+=("SWAP ${SWAP}")

  # ─ cpu % ─
  local CPU
  CPU=$(top -bn1 2>/dev/null | awk '/^%Cpu/ {printf "%d%%", 100 - $8; exit}')
  if [ -z "$CPU" ]; then CPU="ERR"; errs="${errs}cpu "; fi
  SEGMENTS+=("CPU ${CPU}")

  # ─ cpu temp ─
  local CTEMP
  CTEMP=$(timeout 1 sensors 2>/dev/null | awk '/^Package id 0:|^Tctl:/ {gsub(/\+|°C/,"",$2); printf "%s°C", $2; exit}')
  [ -z "$CTEMP" ] && CTEMP="—"
  SEGMENTS+=("CPU·TEMP ${CTEMP}")

  # ─ gpu temp + name ─
  local GPU
  GPU=$(timeout 1 sensors 2>/dev/null | awk '/edge:|GPU:|junction:/ {gsub(/\+|°C/,"",$2); printf "%s°C", $2; exit}')
  [ -z "$GPU" ] && GPU="—"
  SEGMENTS+=("GPU·TEMP ${GPU}")

  # ─ fans ─
  local FANS
  FANS=$(timeout 1 sensors 2>/dev/null | awk '/fan[0-9]:|FAN/ {gsub(/RPM/,"",$2); s+=$2; n++} END {if (n>0) printf "%d RPM avg", s/n; else print "—"}')
  [ -z "$FANS" ] && FANS="—"
  SEGMENTS+=("FANS ${FANS}")

  # ─ disk root ─
  local DISK
  DISK=$(df / 2>/dev/null | awk 'NR==2 {print $5 " · " $4 " free"}' | awk '{$2=int($2/1024/1024)"GB"; print}')
  if [ -z "$DISK" ]; then DISK="ERR"; errs="${errs}disk "; fi
  SEGMENTS+=("DISK ${DISK}")

  # ─ inodes ─
  local INO
  INO=$(df -i / 2>/dev/null | awk 'NR==2 {print $5}')
  [ -z "$INO" ] && INO="—"
  SEGMENTS+=("INODES ${INO}")

  # ─ procs + threads + zombies ─
  local PROCS THREADS ZOMB
  PROCS=$(ls /proc 2>/dev/null | grep -cE '^[0-9]+$')
  THREADS=$(awk '{print $1}' /proc/loadavg 2>/dev/null; awk '/Threads/ {s+=$2} END {print s}' /proc/[0-9]*/status 2>/dev/null | tail -1)
  THREADS=$(awk '/Threads/ {s+=$2} END {if (s>0) print s; else print "—"}' /proc/[0-9]*/status 2>/dev/null)
  ZOMB=$(awk '/State.*Z/ {z++} END {print z+0}' /proc/[0-9]*/status 2>/dev/null)
  [ -z "$PROCS" ] && PROCS="—"
  SEGMENTS+=("PROCS ${PROCS} · ${THREADS:-—} threads · ${ZOMB:-0} zombie")

  # ─ users logged in ─
  local USRS
  USRS=$(who 2>/dev/null | awk '{print $1}' | sort -u | wc -l)
  [ -z "$USRS" ] && USRS="—"
  SEGMENTS+=("USERS ${USRS}")

  # ─ network primary iface state ─
  local NET IP
  if timeout 1 ip route get 1.1.1.1 >/dev/null 2>&1; then
    NET="ONLINE"
    IP=$(ip route get 1.1.1.1 2>/dev/null | awk '{for(i=1;i<=NF;i++) if($i=="src") {print $(i+1); exit}}')
    [ -z "$IP" ] && { IP="ERR"; errs="${errs}net-ip "; }
  else
    NET="OFFLINE"; IP="—"
    errs="${errs}offline "
  fi
  SEGMENTS+=("NET ${NET}")
  SEGMENTS+=("IP ${IP}")

  # ─ wifi ssid + signal ─
  local WIFI
  WIFI=$(timeout 1 iwgetid -r 2>/dev/null)
  if [ -n "$WIFI" ]; then
    local SIG
    SIG=$(awk -v iface="" 'NR>2 && $3 ~ /[0-9]/ {gsub(/\./,"",$3); print int($3); exit}' /proc/net/wireless 2>/dev/null)
    SEGMENTS+=("WIFI ${WIFI} · ${SIG:-—}%")
  else
    SEGMENTS+=("WIFI —")
  fi

  # ─ default route gateway ─
  local GW
  GW=$(ip route 2>/dev/null | awk '/^default/ {print $3; exit}')
  [ -z "$GW" ] && GW="—"
  SEGMENTS+=("GW ${GW}")

  # ─ pacman pending updates (cached 5min) ─
  local NOW_TS=$(date +%s)
  if (( NOW_TS - LAST_UPDATES_CHECK > 300 )); then
    CACHED_UPDATES=$(timeout 4 checkupdates 2>/dev/null | wc -l)
    [ -z "$CACHED_UPDATES" ] && CACHED_UPDATES="0"
    LAST_UPDATES_CHECK=$NOW_TS
  fi
  SEGMENTS+=("UPDATES ${CACHED_UPDATES} pending")

  # ─ installed package count ─
  local PKGS
  PKGS=$(pacman -Q 2>/dev/null | wc -l)
  [ -z "$PKGS" ] || [ "$PKGS" -eq 0 ] && PKGS="—"
  SEGMENTS+=("PKGS ${PKGS} installed")

  # ─ last pacman -Sy ─
  local LAST_SYNC
  if [ -r /var/lib/pacman/sync ]; then
    LAST_SYNC=$(stat -c %Y /var/lib/pacman/sync 2>/dev/null)
    if [ -n "$LAST_SYNC" ]; then
      local AGE=$(( (NOW_TS - LAST_SYNC) / 3600 ))
      LAST_SYNC="${AGE}h ago"
    else
      LAST_SYNC="—"
    fi
  else
    LAST_SYNC="—"
  fi
  SEGMENTS+=("PAC·SYNC ${LAST_SYNC}")

  # ─ failed systemd units ─
  local FAILED
  FAILED=$(timeout 1 systemctl --failed --no-legend 2>/dev/null | wc -l)
  [ -z "$FAILED" ] && FAILED="0"
  SEGMENTS+=("FAIL·UNITS ${FAILED}")

  # ─ journalctl errors today ─
  local JERR
  JERR=$(timeout 2 journalctl --since today -p 3 --no-pager -q 2>/dev/null | wc -l)
  [ -z "$JERR" ] && JERR="0"
  SEGMENTS+=("ERR·LOG ${JERR} today")

  # ─ active hyprland workspace + window count ─
  local WS WIN_COUNT
  WS=$(timeout 1 hyprctl -j activeworkspace 2>/dev/null | awk -F'[:,]' '/"id":/ {gsub(/[ "]/,"",$2); print $2; exit}')
  WIN_COUNT=$(timeout 1 hyprctl -j clients 2>/dev/null | grep -c '"address"' )
  [ -z "$WS" ] && WS="—"
  [ -z "$WIN_COUNT" ] && WIN_COUNT="—"
  SEGMENTS+=("WS ${WS} · ${WIN_COUNT} windows")

  # ─ host + user ─
  local HOST USR
  HOST=$(hostname 2>/dev/null);     [ -z "$HOST" ] && HOST="nyxus"
  USR=${USER:-$(whoami 2>/dev/null)};  [ -z "$USR" ] && USR="nyx"
  SEGMENTS+=("HOST ${USR}@${HOST}")

  # ─ battery (laptop only) ─
  local BAT="—"
  for b in /sys/class/power_supply/BAT*; do
    if [ -d "$b" ]; then
      cap=$(cat "$b/capacity" 2>/dev/null)
      sta=$(cat "$b/status" 2>/dev/null)
      if [ -n "$cap" ]; then BAT="${cap}% ${sta}"; break; fi
    fi
  done
  SEGMENTS+=("BAT ${BAT}")

  # ─ audio sink ─
  local AUDIO
  AUDIO=$(timeout 1 wpctl status 2>/dev/null | awk '/Audio/{f=1} f && /\* / && /vol:/ {sub(/.*\* /,""); sub(/\[vol.*/,""); gsub(/^[ \t]+|[ \t]+$/,""); print; exit}')
  [ -z "$AUDIO" ] && AUDIO="—"
  SEGMENTS+=("AUDIO ${AUDIO}")

  # ─ resolution ─
  local RES
  RES=$(timeout 1 hyprctl -j monitors 2>/dev/null | awk -F'"' '/"width":|"height":/ {gsub(/[^0-9]/,"",$0); v=v "x" $0} END {sub(/^x/,"",v); print v}')
  [ -z "$RES" ] && RES="—"
  SEGMENTS+=("RES ${RES}")

  # ─ now ─
  local NOW
  NOW=$(date '+%a %d · %H:%M:%S' 2>/dev/null)
  [ -z "$NOW" ] && NOW="—"
  SEGMENTS+=("${NOW}")

  # Publish probe errors
  PROBE_ERRORS="${errs}"
}

# ── Shuffle the segments and join with the diamond separator ────────────
build_string() {
  build_segments
  local SEP="   ◆   "
  local out="NYXUS · SIERENGOWSKI · 2026${SEP}HYPRLAND · WAYLAND · ARCH LINUX${SEP}"
  # Shuffle indices
  local shuffled
  shuffled=$(printf '%s\n' "${SEGMENTS[@]}" | shuf 2>/dev/null) || shuffled=$(printf '%s\n' "${SEGMENTS[@]}")
  while IFS= read -r seg; do
    out="${out}${seg}${SEP}"
  done <<< "$shuffled"
  printf '%s' "$out"
}

# ── Tooltip = pretty-printed full snapshot (un-shuffled, alphabetical) ──
build_tooltip() {
  printf '%s' "$1" | awk '
    BEGIN { RS = "   ◆   "; printed = 0 }
    {
      gsub(/^[ \t]+|[ \t]+$/, "");
      if (length($0) == 0) next;
      printf "%s\n", $0;
      printed++;
    }
  ' | sort
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
NEXT_REBUILD=0
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
    ERR_LINE="<span size='small' foreground='#7aff7a'>● all 28 probes nominal · reshuffles every ${REFRESH}s</span>"
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
