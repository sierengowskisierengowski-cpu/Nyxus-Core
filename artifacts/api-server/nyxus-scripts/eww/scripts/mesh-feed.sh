#!/usr/bin/env bash
# NYXUS · EWW · MESH station deck — connection matrix feed
# Reads ss -s summary and emits JSON for the deck stats.
set -u

if ! command -v ss >/dev/null 2>&1; then
  printf '{"conns":0,"tcp":0,"udp":0,"listen":0,"foreign":0}\n'
  exit 0
fi

summary="$(ss -s 2>/dev/null)"

# Total sockets (TCP + UDP established)
tcp="$(  printf '%s' "$summary" | awk '/^TCP:/{print $2+0; found=1} END{if(!found)print 0}')"
udp="$(  printf '%s' "$summary" | awk '/^UDP:/{print $2+0; found=1} END{if(!found)print 0}')"
total=$(( tcp + udp ))

# Listening ports
listen="$(ss -tlnH 2>/dev/null | wc -l | tr -d ' ')"

# Established connections to foreign (non-loopback) hosts
foreign="$(ss -tnH state established 2>/dev/null \
  | grep -v '127\.\|::1\|0\.0\.0\.0' | wc -l | tr -d ' ')"

printf '{"conns":%d,"tcp":%d,"udp":%d,"listen":%d,"foreign":%d}\n' \
  "$total" "$tcp" "$udp" "${listen:-0}" "${foreign:-0}"
