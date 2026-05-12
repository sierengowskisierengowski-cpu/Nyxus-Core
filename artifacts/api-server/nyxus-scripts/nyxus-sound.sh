#!/usr/bin/env bash
# NYXUS sound dispatcher — single shim every NYXUS app uses.
#
# Events (must stay 1:1 with /usr/share/sounds/nyxus/index.theme):
#   boot                System start
#   login               Successful login
#   logout              Session end
#   notification        Generic notif chime
#   message             High-priority message
#   error               Error / failed action
#   lock                Screen locked
#   unlock              Screen unlocked
#   battery-low         Power < 15%
#   battery-critical    Power < 5%
#   plug                AC plugged in
#   unplug              AC unplugged
#   screenshot          Shutter
#   trash               File moved to trash
#   alert               Attention
#
# Resolution order:
#   1) ~/.local/share/sounds/nyxus/<event>.oga       (user override)
#   2) /usr/share/sounds/nyxus/<event>.oga           (NYXUS theme)
#   3) canberra-gtk-play -i <event>                  (freedesktop fallback)
#
# Honors per-user mute via:
#   ~/.config/nyxus/sound.conf  →  enabled=0   (disables all events)
#
# Usage:
#   nyxus-sound.sh <event>            play and exit
#   nyxus-sound.sh --list             list known events
#   nyxus-sound.sh --test             play every event in sequence
#   nyxus-sound.sh --enable|--disable flip mute state
#
set -u

EVENTS=(boot login logout notification message error lock unlock
        battery-low battery-critical plug unplug screenshot trash alert)
CFG="${XDG_CONFIG_HOME:-$HOME/.config}/nyxus/sound.conf"
mkdir -p "$(dirname "$CFG")"
[[ -f "$CFG" ]] || printf 'enabled=1\nvolume=80\n' > "$CFG"

_get() { awk -F= -v k="$1" '$1==k{print $2;exit}' "$CFG" 2>/dev/null; }
_set() { local k="$1" v="$2"
  if grep -q "^$k=" "$CFG" 2>/dev/null; then
    sed -i "s|^$k=.*|$k=$v|" "$CFG"
  else
    echo "$k=$v" >> "$CFG"
  fi
}

_play() {
  local event="$1"
  local user_path="$HOME/.local/share/sounds/nyxus/${event}.oga"
  local sys_path="/usr/share/sounds/nyxus/${event}.oga"
  local vol; vol="$(_get volume)"; vol="${vol:-80}"
  local pct=$(awk -v v="$vol" 'BEGIN{print v/100}')

  if [[ -f "$user_path" ]]; then
    file="$user_path"
  elif [[ -f "$sys_path" ]]; then
    file="$sys_path"
  else
    file=""
  fi

  if [[ -n "$file" ]]; then
    if command -v pw-play >/dev/null 2>&1; then
      pw-play --volume="$pct" "$file" >/dev/null 2>&1 &
    elif command -v paplay >/dev/null 2>&1; then
      paplay --volume=$(awk -v v="$vol" 'BEGIN{print int(v*655.35)}') "$file" >/dev/null 2>&1 &
    elif command -v ffplay >/dev/null 2>&1; then
      ffplay -nodisp -autoexit -loglevel error "$file" >/dev/null 2>&1 &
    fi
    return 0
  fi

  # Fallback: freedesktop event id via canberra
  if command -v canberra-gtk-play >/dev/null 2>&1; then
    case "$event" in
      boot|login)        cb=desktop-login ;;
      logout)            cb=desktop-logout ;;
      notification|message) cb=message-new-instant ;;
      error|alert)       cb=dialog-error ;;
      lock)              cb=screen-locked ;;
      unlock)            cb=screen-unlocked ;;
      battery-low)       cb=battery-low ;;
      battery-critical)  cb=battery-caution ;;
      plug)              cb=power-plug ;;
      unplug)            cb=power-unplug ;;
      screenshot)        cb=camera-shutter ;;
      trash)             cb=trash-empty ;;
      *)                 cb=bell ;;
    esac
    canberra-gtk-play -i "$cb" >/dev/null 2>&1 &
    return 0
  fi
  return 1
}

case "${1:-}" in
  --list)    printf '%s\n' "${EVENTS[@]}"; exit 0 ;;
  --enable)  _set enabled 1; echo "enabled"; exit 0 ;;
  --disable) _set enabled 0; echo "disabled"; exit 0 ;;
  --test)
    for e in "${EVENTS[@]}"; do
      echo "→ $e"; _play "$e"; sleep 1
    done
    exit 0
    ;;
  --status)
    en="$(_get enabled)"; vol="$(_get volume)"
    echo "enabled=${en:-1} volume=${vol:-80}"
    exit 0
    ;;
  "")
    echo "usage: nyxus-sound.sh <event> | --list | --test | --enable | --disable | --status" >&2
    exit 2
    ;;
esac

# Mute respect
en="$(_get enabled)"
[[ "${en:-1}" == "0" ]] && exit 0

event="$1"
case " ${EVENTS[*]} " in
  *" $event "*) _play "$event" ;;
  *) echo "unknown event: $event (try --list)" >&2; exit 2 ;;
esac
