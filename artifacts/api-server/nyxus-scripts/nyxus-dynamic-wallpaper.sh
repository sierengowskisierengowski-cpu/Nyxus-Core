#!/usr/bin/env bash
# NYXUS Dynamic / time-of-day wallpaper picker.
#
# Reads ~/.config/nyxus/dynamic-wallpaper.conf for the chosen "set"
# and applies the appropriate image based on local time:
#   05:00–09:00 → dawn
#   09:00–17:00 → day
#   17:00–20:00 → dusk
#   20:00–05:00 → night
#
# Config (key=value, # comments):
#   set=cosmos|darkmirror|watercolor|custom
#   custom_dawn=/path/to/img.png   (custom set only)
#   custom_day=...
#   custom_dusk=...
#   custom_night=...
#
# Driven by the nyxus-dynamic-wallpaper.timer (hourly + on boot).
# Delegates the actual paint to nyxus-set-wallpaper.sh so every
# backend (swww/swaybg/hyprpaper/feh) is tried.
#
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
set -u

CONF="$HOME/.config/nyxus/dynamic-wallpaper.conf"
LOG_DIR="$HOME/.cache/nyxus"
LOG="$LOG_DIR/dynamic-wallpaper.log"
mkdir -p "$LOG_DIR"
ts() { date '+%Y-%m-%d %H:%M:%S'; }
say() { printf '%s dyn-wp: %s\n' "$(ts)" "$*" >> "$LOG"; }

[ -f "$CONF" ] || { say "no config — exiting"; exit 0; }

set_name="cosmos"
custom_dawn=""; custom_day=""; custom_dusk=""; custom_night=""
while IFS='=' read -r k v; do
  k="${k%%[[:space:]]*}"; k="${k##[[:space:]]*}"
  v="${v%%[[:space:]]*}"; v="${v##[[:space:]]*}"
  case "$k" in
    ''|\#*) continue;;
    set)           set_name="$v";;
    custom_dawn)   custom_dawn="$v";;
    custom_day)    custom_day="$v";;
    custom_dusk)   custom_dusk="$v";;
    custom_night)  custom_night="$v";;
  esac
done < "$CONF"

hour=$(date +%H)
hour=${hour#0}
if   [ "$hour" -ge 5  ] && [ "$hour" -lt 9  ]; then phase="dawn"
elif [ "$hour" -ge 9  ] && [ "$hour" -lt 17 ]; then phase="day"
elif [ "$hour" -ge 17 ] && [ "$hour" -lt 20 ]; then phase="dusk"
else phase="night"
fi

# Built-in sets — keys are short names matched by nyxus-set-wallpaper.sh
# in $WALL_DIR/nyxus-bg-<name>.png.
case "$set_name" in
  cosmos)
    declare -A imgs=(
      [dawn]="cosmic-dust" [day]="cosmos-gold"
      [dusk]="light-shaft" [night]="darkmirror")
    ;;
  darkmirror)
    declare -A imgs=(
      [dawn]="darkmirror-02" [day]="darkmirror"
      [dusk]="darkmirror-03" [night]="moon-crater")
    ;;
  watercolor)
    declare -A imgs=(
      [dawn]="sepia-watercolor" [day]="cosmos-gold"
      [dusk]="sepia-watercolor" [night]="moon-crater")
    ;;
  custom)
    declare -A imgs=(
      [dawn]="$custom_dawn" [day]="$custom_day"
      [dusk]="$custom_dusk" [night]="$custom_night")
    ;;
  *)
    say "ERROR: unknown set '$set_name'"
    exit 1
    ;;
esac

target="${imgs[$phase]:-}"
if [ -z "$target" ]; then
  say "ERROR: no image configured for phase=$phase set=$set_name"
  exit 1
fi

say "phase=$phase set=$set_name target=$target"
exec nyxus-set-wallpaper.sh "$target"
