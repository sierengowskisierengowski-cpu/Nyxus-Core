#!/bin/bash
# ─────────────────────────────────────────────────────────────
# NYXUS Waybar Stats (right side of top bar)
# ~/.config/waybar/stats.sh
# ─────────────────────────────────────────────────────────────

cpu=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk '{print $2+$4}' | cut -d. -f1 2>/dev/null || echo "?")
mem=$(free -m 2>/dev/null | awk '/Mem:/{printf "%.0f", $3/$2*100}' || echo "?")

temp_file="/sys/class/thermal/thermal_zone0/temp"
if [[ -f "$temp_file" ]]; then
    temp=$(awk '{printf "%.0f", $1/1000}' "$temp_file")°C
else
    temp="--°C"
fi

echo "  ${cpu}%   ${mem}%   ${temp}"
