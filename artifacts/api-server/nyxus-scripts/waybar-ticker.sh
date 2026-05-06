#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────
# NYXUS Waybar Airport-Ticker  ·  rev 2026-05-06r
# Outputs ONE line of JSON per invocation: {"text": "...", "tooltip": "..."}
# Waybar invokes this every 5s (return-type: json) and updates the module.
# Bulletproof: every probe has its own short timeout, no probe can block.
# ─────────────────────────────────────────────────────────────────────────

set -u
export LC_ALL=C

# ── Probes (each capped, never block) ────────────────────────────────────
UPTIME=$(uptime -p 2>/dev/null | sed 's/^up //; s/ minutes/m/; s/ minute/m/; s/ hours/h/; s/ hour/h/; s/ days/d/; s/ day/d/; s/, /·/g')
[ -z "$UPTIME" ] && UPTIME="—"

KERNEL=$(uname -r 2>/dev/null | cut -d- -f1)
[ -z "$KERNEL" ] && KERNEL="—"

LOAD=$(awk '{printf "%.2f", $1}' /proc/loadavg 2>/dev/null)
[ -z "$LOAD" ] && LOAD="—"

MEM=$(awk '/MemTotal/ {t=$2} /MemAvailable/ {a=$2} END {if (t>0) printf "%d%%", (t-a)*100/t; else print "—"}' /proc/meminfo 2>/dev/null)
[ -z "$MEM" ] && MEM="—"

CPU_PCT=$(top -bn1 2>/dev/null | awk '/^%Cpu/ {printf "%d%%", 100 - $8; exit}')
[ -z "$CPU_PCT" ] && CPU_PCT="—"

if timeout 1 ip route get 1.1.1.1 >/dev/null 2>&1; then NET="ONLINE"; else NET="OFFLINE"; fi

UPDATES=$(timeout 6 checkupdates 2>/dev/null | wc -l)
[ -z "$UPDATES" ] && UPDATES="0"

NOW=$(date +%s)

# ── Rotating message board (changes every 5 seconds) ────────────────────
MESSAGES=(
    "  NYXUS  ·  SYSTEM  NOMINAL"
    "  UPTIME  ·  $UPTIME"
    "  KERNEL  ·  $KERNEL"
    "  CPU $CPU_PCT  ·  MEM $MEM  ·  LOAD $LOAD"
    "  UPDATES  ·  $UPDATES  pending"
    "  NETWORK  ·  $NET"
    "  HYPRLAND  ·  WAYLAND  ACTIVE"
    "  SIERENGOWSKI  ·  2026"
)
COUNT=${#MESSAGES[@]}
INDEX=$(( (NOW / 5) % COUNT ))
TEXT="${MESSAGES[$INDEX]}"

# ── Tooltip: full snapshot every refresh ────────────────────────────────
TOOLTIP="<span size='x-large' weight='bold' foreground='#1a1816'>NYXUS · LIVE STATUS</span>"
TOOLTIP+=$'\n'
TOOLTIP+="<span size='small' foreground='#58524c'>Uptime:    ${UPTIME}"$'\n'
TOOLTIP+="Kernel:    ${KERNEL}"$'\n'
TOOLTIP+="CPU:       ${CPU_PCT}"$'\n'
TOOLTIP+="Memory:    ${MEM}"$'\n'
TOOLTIP+="Load:      ${LOAD}"$'\n'
TOOLTIP+="Updates:   ${UPDATES} pending"$'\n'
TOOLTIP+="Network:   ${NET}</span>"

# ── JSON-escape & emit ──────────────────────────────────────────────────
esc() {
    printf '%s' "$1" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read())[1:-1], end="")'
}

printf '{"text":"%s","tooltip":"%s","class":"ticker","alt":"ticker"}\n' \
    "$(esc "$TEXT")" "$(esc "$TOOLTIP")"
