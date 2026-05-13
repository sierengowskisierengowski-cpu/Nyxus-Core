#!/usr/bin/env bash
# NYXUS Night Light wrapper.
#
# Reads ~/.config/nyxus/nightlight.conf and runs wlsunset (preferred)
# or hyprsunset / gammastep with the matching arguments. Designed to
# be invoked by the systemd --user nyxus-nightlight.service unit.
#
# Config keys (key=value, # comments):
#   mode=off|always|sunset|custom
#   temp_day=<K>      default 6500
#   temp_night=<K>    default 4000
#   start=HH:MM       custom mode only
#   stop=HH:MM        custom mode only
#   lat=<float>       sunset mode (auto sun calc)
#   lon=<float>       sunset mode
#
# Failure is loud: bad config aborts non-zero so the service status
# reflects reality instead of silently doing nothing.
#
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
set -u

CONF="$HOME/.config/nyxus/nightlight.conf"
LOG_DIR="$HOME/.cache/nyxus"
LOG="$LOG_DIR/nightlight.log"
mkdir -p "$LOG_DIR"

ts() { date '+%Y-%m-%d %H:%M:%S'; }
say() { printf '%s nightlight: %s\n' "$(ts)" "$*" >> "$LOG"; }

if [ ! -f "$CONF" ]; then
  say "no config at $CONF — exiting"
  exit 0
fi

# Defaults
mode="off"
temp_day=6500
temp_night=4000
start=""
stop=""
lat=""
lon=""

while IFS='=' read -r k v; do
  k="${k%%[[:space:]]*}"; k="${k##[[:space:]]*}"
  v="${v%%[[:space:]]*}"; v="${v##[[:space:]]*}"
  case "$k" in
    ''|\#*) continue;;
    mode)        mode="$v";;
    temp_day)    temp_day="$v";;
    temp_night)  temp_night="$v";;
    start)       start="$v";;
    stop)        stop="$v";;
    lat)         lat="$v";;
    lon)         lon="$v";;
  esac
done < "$CONF"

# Kill any prior night-light daemons before launching ours.
for proc in wlsunset hyprsunset gammastep; do
  pkill -x "$proc" >/dev/null 2>&1 || true
done

case "$mode" in
  off)
    say "mode=off — services killed, exiting"
    exit 0
    ;;
  always)
    if command -v wlsunset >/dev/null 2>&1; then
      say "mode=always temp=$temp_night via wlsunset"
      exec wlsunset -T "$temp_night" -t "$temp_night" \
                    -S "00:00" -s "23:59"
    elif command -v hyprsunset >/dev/null 2>&1; then
      say "mode=always temp=$temp_night via hyprsunset"
      exec hyprsunset -t "$temp_night"
    else
      say "ERROR: no wlsunset/hyprsunset installed for always mode"
      exit 1
    fi
    ;;
  custom)
    if [ -z "$start" ] || [ -z "$stop" ]; then
      say "ERROR: custom mode needs start= and stop= (got '$start' / '$stop')"
      exit 1
    fi
    if command -v wlsunset >/dev/null 2>&1; then
      say "mode=custom $start..$stop temps=$temp_night/$temp_day"
      exec wlsunset -T "$temp_day" -t "$temp_night" \
                    -S "$start" -s "$stop"
    else
      say "ERROR: wlsunset required for custom schedule, not found"
      exit 1
    fi
    ;;
  sunset)
    if [ -z "$lat" ] || [ -z "$lon" ]; then
      say "ERROR: sunset mode needs lat= and lon= (got '$lat' / '$lon')"
      exit 1
    fi
    if command -v wlsunset >/dev/null 2>&1; then
      say "mode=sunset lat=$lat lon=$lon temps=$temp_night/$temp_day"
      exec wlsunset -T "$temp_day" -t "$temp_night" \
                    -l "$lat" -L "$lon"
    elif command -v gammastep >/dev/null 2>&1; then
      say "mode=sunset via gammastep -l $lat:$lon"
      exec gammastep -l "${lat}:${lon}" \
                     -t "${temp_day}:${temp_night}"
    else
      say "ERROR: no wlsunset/gammastep installed for sunset mode"
      exit 1
    fi
    ;;
  *)
    say "ERROR: unknown mode '$mode'"
    exit 1
    ;;
esac
