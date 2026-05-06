#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────
# NYXUS Waybar Airport-Ticker
# Rotating system-status board feeding the top-bar custom/ticker module.
# Output: JSON {"text": "...", "tooltip": "..."} consumed by waybar.
# Refresh: every 1s via waybar interval; message rotates every 5s.
# ─────────────────────────────────────────────────────────────────────────

set -u

# ── Cached probes (refresh every N seconds, never block waybar) ──────────
CACHE="/tmp/nyxus-ticker.cache"
NOW=$(date +%s)

read_cache() {
    local key="$1" ttl="$2"
    [[ -f "$CACHE" ]] || { echo ""; return; }
    awk -F'\t' -v k="$key" -v now="$NOW" -v ttl="$ttl" '
        $1 == k && (now - $2) < ttl { print $3; found=1; exit }
    ' "$CACHE"
}

write_cache() {
    local key="$1" val="$2"
    [[ -f "$CACHE" ]] && grep -v "^${key}	" "$CACHE" > "${CACHE}.new" 2>/dev/null || true
    printf '%s\t%s\t%s\n' "$key" "$NOW" "$val" >> "${CACHE}.new" 2>/dev/null || \
        printf '%s\t%s\t%s\n' "$key" "$NOW" "$val" > "${CACHE}.new"
    mv -f "${CACHE}.new" "$CACHE" 2>/dev/null || true
}

# ── Probes (each cached at its own TTL so the script never stalls) ──────
get_uptime() {
    local v; v=$(read_cache uptime 60)
    if [[ -z "$v" ]]; then
        v=$(uptime -p 2>/dev/null | sed 's/^up //; s/ minutes/m/; s/ minute/m/; s/ hours/h/; s/ hour/h/; s/ days/d/; s/ day/d/; s/, /·/g')
        [[ -z "$v" ]] && v="—"
        write_cache uptime "$v"
    fi
    echo "$v"
}

get_updates() {
    local v; v=$(read_cache updates 1800)
    if [[ -z "$v" ]]; then
        if command -v checkupdates >/dev/null 2>&1; then
            v=$(timeout 8 checkupdates 2>/dev/null | wc -l)
        else
            v="0"
        fi
        write_cache updates "$v"
    fi
    echo "$v"
}

get_kernel() {
    local v; v=$(read_cache kernel 3600)
    if [[ -z "$v" ]]; then
        v=$(uname -r 2>/dev/null | cut -d- -f1)
        [[ -z "$v" ]] && v="—"
        write_cache kernel "$v"
    fi
    echo "$v"
}

get_load() {
    local v
    v=$(awk '{printf "%.2f", $1}' /proc/loadavg 2>/dev/null)
    [[ -z "$v" ]] && v="—"
    echo "$v"
}

get_mem() {
    awk '/MemTotal/ {t=$2} /MemAvailable/ {a=$2} END {if (t>0) printf "%d%%", (t-a)*100/t; else print "—"}' /proc/meminfo 2>/dev/null
}

get_net() {
    if ip route get 1.1.1.1 >/dev/null 2>&1; then echo "ONLINE"; else echo "OFFLINE"; fi
}

# ── Build the ticker board ──────────────────────────────────────────────
UPTIME=$(get_uptime)
UPDATES=$(get_updates)
KERNEL=$(get_kernel)
LOAD=$(get_load)
MEM=$(get_mem)
NET=$(get_net)

MESSAGES=(
    "▸ NYXUS · SYSTEM NOMINAL"
    "▸ UPTIME · ${UPTIME}"
    "▸ KERNEL · ${KERNEL}"
    "▸ LOAD · ${LOAD}   MEM · ${MEM}"
    "▸ UPDATES · ${UPDATES} pending"
    "▸ NETWORK · ${NET}"
    "▸ HYPRLAND · WAYLAND ACTIVE"
    "▸ SIERENGOWSKI · 2026"
)

INDEX=$(( NOW / 5 % ${#MESSAGES[@]} ))
TEXT="${MESSAGES[$INDEX]}"

# Tooltip: full live status snapshot
TOOLTIP=$(printf "<span size='x-large' weight='bold' foreground='#1a1816'>NYXUS · LIVE STATUS</span>\n<span size='small' foreground='#58524c'>Uptime:   %s\nKernel:   %s\nLoad:     %s\nMemory:   %s\nUpdates:  %s pending\nNetwork:  %s</span>" \
    "$UPTIME" "$KERNEL" "$LOAD" "$MEM" "$UPDATES" "$NET")

# JSON-safe escaping
TEXT_ESC=${TEXT//\\/\\\\}; TEXT_ESC=${TEXT_ESC//\"/\\\"}
TT_ESC=${TOOLTIP//\\/\\\\};   TT_ESC=${TT_ESC//\"/\\\"};   TT_ESC=${TT_ESC//$'\n'/\\n}

printf '{"text":"%s","tooltip":"%s","class":"ticker"}\n' "$TEXT_ESC" "$TT_ESC"
