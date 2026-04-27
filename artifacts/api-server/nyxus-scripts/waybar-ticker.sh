#!/bin/bash
# ─────────────────────────────────────────────────────────────
# NYXUS Waybar Live Ticker
# ~/.config/waybar/ticker.sh
# Rotates through system stats every 4s
# ─────────────────────────────────────────────────────────────

PHASE=$(( $(date +%s) / 4 % 6 ))

cpu=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk '{print $2+$4}' | cut -d. -f1 2>/dev/null || echo "?")
mem=$(free -m 2>/dev/null | awk '/Mem:/{printf "%.0f", $3/$2*100}' || echo "?")
disk=$(df -h / 2>/dev/null | awk 'NR==2{print $5}' | tr -d '%' || echo "?")
ip=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "?")
up=$(uptime -p 2>/dev/null | sed 's/up //' || echo "?")

temp_file="/sys/class/thermal/thermal_zone0/temp"
if [[ -f "$temp_file" ]]; then
    temp=$(awk '{printf "%.0f", $1/1000}' "$temp_file")°C
else
    temp="--°C"
fi

case $PHASE in
    0) echo "  CPU ${cpu}%   MEM ${mem}%   DISK ${disk}%   TEMP ${temp}" ;;
    1) echo "  IP ${ip}   UP ${up}" ;;
    2) echo "  CPU ${cpu}%   RAM ${mem}%" ;;
    3) echo "  DISK ${disk}%   TEMP ${temp}" ;;
    4) echo "  SILENT · DARK · PURELY FUNCTIONAL" ;;
    5) echo "  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026" ;;
esac
