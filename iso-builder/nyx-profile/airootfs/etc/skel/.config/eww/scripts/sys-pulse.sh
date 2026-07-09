#!/usr/bin/env bash
# NYXUS · EWW · system pulse  (CPU% / MEM% / temp°C / load / swap%)
set -u

cpu=$(top -bn1 2>/dev/null | awk '/Cpu\(s\)/{printf "%d", $2+$4}' || echo 0)
mem=$(free -m 2>/dev/null | awk '/Mem:/{printf "%d", $3/$2*100}' || echo 0)
swap=$(free -m 2>/dev/null | awk '/Swap:/{ if ($2>0) printf "%d", $3/$2*100; else print 0 }' || echo 0)
load=$(awk '{print $1}' /proc/loadavg 2>/dev/null || echo 0)

temp_file="/sys/class/thermal/thermal_zone0/temp"
if [[ -r "$temp_file" ]]; then
  temp=$(awk '{printf "%d", $1/1000}' "$temp_file")
else
  temp="--"
fi

printf '{"cpu":"%s","mem":"%s","temp":"%s","load":"%s","swap":"%s"}\n' \
  "$cpu" "$mem" "$temp" "$load" "$swap"
