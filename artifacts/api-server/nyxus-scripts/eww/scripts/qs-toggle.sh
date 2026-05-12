#!/usr/bin/env bash
# NYXUS · EWW · quick-settings action handler
# Usage: qs-toggle.sh <wifi|bt|airplane|dnd|nightlight|profile|mic|audio|rotate>
# (P2.12 review: removed `rot` and `auto-bright` flag-only stubs;
#  added real `rotate` that drives Hyprland monitor transform.)
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
    else
      command -v gammastep >/dev/null && nohup gammastep -O 4500 >/dev/null 2>&1 & disown
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
  rotate)
    # Real display rotation via Hyprland (P2.12 stub-removal fix).
    # Cycle the focused monitor's transform 0 → 1 → 2 → 3 → 0.
    # Replaces the prior flag-only `rot` stub which never touched
    # display state.
    if ! command -v hyprctl >/dev/null 2>&1; then
      echo "qs-toggle: hyprctl not available; cannot rotate display" >&2
      exit 3
    fi
    # Prefer jq for robust JSON parsing; fall back to plain-text
    # `hyprctl monitors` parsing on minimal installs without jq
    # (P2.12 review round-2: avoid silent rotate failure).
    mon=""; cur=0
    if command -v jq >/dev/null 2>&1; then
      mon=$(hyprctl -j monitors 2>/dev/null \
            | jq -r '(map(select(.focused)) | .[0].name)      // empty')
      cur=$(hyprctl -j monitors 2>/dev/null \
            | jq -r '(map(select(.focused)) | .[0].transform) // 0')
    else
      # Walk text output: locate the focused monitor block, then
      # pull its name (header line) and `transform: N` field.
      raw=$(hyprctl monitors 2>/dev/null) || raw=""
      mon=$(printf '%s\n' "$raw" \
            | awk '/^Monitor /{name=$2}
                   /focused: yes/{print name; exit}')
      cur=$(printf '%s\n' "$raw" \
            | awk -v m="$mon" '
                $1=="Monitor" && $2==m {found=1}
                found && /transform:/ {print $2; exit}' \
            || echo 0)
    fi
    [[ -z "$mon" ]] && { echo "qs-toggle: no focused monitor" >&2; exit 4; }
    case "$cur" in 0|1|2|3) : ;; *) cur=0 ;; esac
    next=$(( (cur + 1) % 4 ))
    hyprctl keyword monitor "${mon},transform,${next}" >/dev/null 2>&1
    ;;
  *)
    echo "qs-toggle: unknown target '$target'" >&2; exit 2 ;;
esac
