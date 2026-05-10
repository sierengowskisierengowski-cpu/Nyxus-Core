#!/bin/bash
# NYXUS sys-pulse — live "astrolabe sigil" for the bottom waybar.
# Rotates a 4-frame quarter-circle glyph (◴◵◶◷). Rotation rate is
# modulated by 1-minute load average: low load = slow turn (every 4s),
# medium = 2s, high = 1s. Emits JSON { text, class, tooltip } so the
# CSS can colour low/med/high differently. No external deps.

set -e

read -r load1 _ < /proc/loadavg
load_int=$(awk -v l="$load1" 'BEGIN{ printf "%d", l * 100 }')

if   [ "$load_int" -gt 150 ]; then div=1; cls="high"
elif [ "$load_int" -gt  50 ]; then div=2; cls="med"
else                                div=4; cls="low"
fi

glyphs=("◴" "◵" "◶" "◷")
idx=$(( ($(date +%s) / div) % 4 ))
g="${glyphs[$idx]}"

# Plain ASCII tooltip — no embedded quotes / HTML to keep JSON safe.
printf '{"text":"%s","class":"%s","tooltip":"NYXUS · Live Pulse — load %s (%s)"}\n' \
       "$g" "$cls" "$load1" "$cls"
