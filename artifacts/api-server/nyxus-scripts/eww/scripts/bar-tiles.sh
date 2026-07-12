#!/usr/bin/env bash
# NYXUS · EWW · top-bar HUD tile data (rev 2026-07-09)
# Slow-changing system facts for the bar-top mini HUD cards. Fast
# metrics (cpu/mem/temp) come from SYSPULSE — do not duplicate here.
# Emits {host, kern, up, disk, ip, gw, users, pkgs}
set -u
export LC_ALL=C.UTF-8

host=$(hostname 2>/dev/null || echo "?")
kern=$(uname -r 2>/dev/null | cut -d- -f1)
up=$(uptime -p 2>/dev/null | sed 's/^up //; s/ hours\?/h/; s/ minutes\?/m/; s/ days\?/d/; s/,//g')
disk=$(df -h --output=pcent / 2>/dev/null | tail -1 | tr -d ' %')
ip=$(ip -4 addr show 2>/dev/null | awk '/inet /{print $2}' | grep -v '^127' | head -1 | cut -d/ -f1)
gw=$(ip route 2>/dev/null | awk '/default/{print $3; exit}')
users=$(who 2>/dev/null | wc -l)
pkgs=$(pacman -Qq 2>/dev/null | wc -l)
user=$(whoami 2>/dev/null || echo operator)

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg host "$host" --arg kern "$kern" --arg up "${up:-?}" \
         --arg disk "${disk:-?}" --arg ip "${ip:-offline}" --arg gw "${gw:-none}" \
         --arg users "$users" --arg pkgs "$pkgs" --arg user "$user" \
    '{host:$host, kern:$kern, up:$up, disk:$disk, ip:$ip, gw:$gw, users:$users, pkgs:$pkgs, user:$user}'
else
  printf '{"host":"%s","kern":"%s","up":"%s","disk":"%s","ip":"%s","gw":"%s","users":"%s","pkgs":"%s","user":"%s"}\n' \
    "$host" "$kern" "${up:-?}" "${disk:-?}" "${ip:-offline}" "${gw:-none}" "$users" "$pkgs" "$user"
fi
