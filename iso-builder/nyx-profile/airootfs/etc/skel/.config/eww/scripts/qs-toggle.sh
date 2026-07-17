#!/usr/bin/env bash
# NYXUS · EWW · quick-settings action handler
# Usage: qs-toggle.sh <wifi|bt|airplane|dnd|nightlight|profile|mic|audio|rot|auto-bright>
set -u

state_file="${XDG_RUNTIME_DIR:-/tmp}/nyxus-qs.state"
touch "$state_file" 2>/dev/null || true

target="${1:-}"
case "$target" in
  wifi)
    cur=$(nmcli radio wifi 2>/dev/null)
    [[ "$cur" == enabled ]] && nmcli radio wifi off || nmcli radio wifi on
    ;;
  bt)
    if bluetoothctl show 2>/dev/null | grep -q 'Powered: yes'; then
      bluetoothctl power off
    else
      bluetoothctl power on
    fi
    ;;
  airplane)
    if rfkill list 2>/dev/null | grep -q 'Soft blocked: yes'; then
      rfkill unblock all
    else
      rfkill block all
    fi
    ;;
  dnd)
    dunstctl set-paused toggle
    ;;
  nightlight)
    if pgrep -x gammastep >/dev/null; then
      pkill -x gammastep
    elif pgrep -x wlsunset >/dev/null; then
      pkill -x wlsunset
    elif command -v gammastep >/dev/null; then
      nohup gammastep -O 4500 >/dev/null 2>&1 & disown
    elif command -v nyxus-shader >/dev/null; then
      # no gamma tool installed — use the Hyprland screen-shader warm
      # filter (nyxus-shader night) as the native NYXUS night light
      if [[ "$(nyxus-shader status 2>/dev/null)" == "night" ]]; then
        nyxus-shader off >/dev/null 2>&1
      else
        nyxus-shader night >/dev/null 2>&1
      fi
    fi
    ;;
  profile)
    cur=$(powerprofilesctl get 2>/dev/null || echo balanced)
    case "$cur" in
      power-saver) next=balanced ;;
      balanced)    next=performance ;;
      performance) next=power-saver ;;
      *)           next=balanced ;;
    esac
    powerprofilesctl set "$next" 2>/dev/null || true
    ;;
  mic)
    wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle
    ;;
  audio)
    wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle
    ;;
  rot)
    if grep -q 'NYXUS_ROT_LOCK=on' "$state_file" 2>/dev/null; then
      sed -i '/NYXUS_ROT_LOCK=/d' "$state_file"
      echo 'NYXUS_ROT_LOCK=off' >> "$state_file"
    else
      sed -i '/NYXUS_ROT_LOCK=/d' "$state_file"
      echo 'NYXUS_ROT_LOCK=on' >> "$state_file"
    fi
    ;;
  auto-bright)
    if grep -q 'NYXUS_AUTO_BRIGHT=on' "$state_file" 2>/dev/null; then
      sed -i '/NYXUS_AUTO_BRIGHT=/d' "$state_file"
      echo 'NYXUS_AUTO_BRIGHT=off' >> "$state_file"
    else
      sed -i '/NYXUS_AUTO_BRIGHT=/d' "$state_file"
      echo 'NYXUS_AUTO_BRIGHT=on' >> "$state_file"
    fi
    ;;
  *)
    echo "qs-toggle: unknown target '$target'" >&2; exit 2 ;;
esac
