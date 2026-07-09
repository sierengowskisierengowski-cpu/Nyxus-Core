#!/usr/bin/env bash
# NYXUS · EWW · audio action handler (pactl + wpctl fallback)
set -u

cmd="${1:-}"; arg1="${2:-}"; arg2="${3:-}"

if [[ -n "$arg1" && ! "$arg1" =~ ^[A-Za-z0-9._:-]+$ ]]; then
  echo "audio-action: rejected id '$arg1'" >&2; exit 2
fi
if [[ -n "$arg2" && ! "$arg2" =~ ^[0-9]+$ ]]; then
  echo "audio-action: rejected vol '$arg2'" >&2; exit 2
fi
if [[ -n "$arg2" && "$arg2" -gt 150 ]]; then arg2=150; fi

wpctl_vol() {
  local target="$1" pct="$2"
  wpctl set-volume "$target" "${pct}%" 2>/dev/null
}

case "$cmd" in
  set-default-sink)
    if command -v pactl >/dev/null 2>&1; then pactl set-default-sink "$arg1"
    else wpctl status 2>/dev/null | grep -q "$arg1" && wpctl set-default "$arg1" 2>/dev/null; fi ;;
  set-default-source)
    if command -v pactl >/dev/null 2>&1; then pactl set-default-source "$arg1"
    else wpctl set-default "$arg1" 2>/dev/null; fi ;;
  set-sink-vol)
    if command -v pactl >/dev/null 2>&1; then pactl set-sink-volume "$arg1" "${arg2}%"
    elif [[ "$arg1" == @* ]]; then wpctl_vol "$arg1" "$arg2"
    else wpctl_vol "@DEFAULT_AUDIO_SINK@" "$arg2"; fi ;;
  set-source-vol)
    if command -v pactl >/dev/null 2>&1; then pactl set-source-volume "$arg1" "${arg2}%"
    else wpctl_vol "@DEFAULT_AUDIO_SOURCE@" "$arg2"; fi ;;
  set-app-vol)
    if command -v pactl >/dev/null 2>&1; then pactl set-sink-input-volume "$arg1" "${arg2}%"
    else wpctl_vol "$arg1" "$arg2"; fi ;;
  toggle-sink-mute)
    if command -v pactl >/dev/null 2>&1; then pactl set-sink-mute "$arg1" toggle
    else wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle 2>/dev/null; fi ;;
  toggle-source-mute)
    if command -v pactl >/dev/null 2>&1; then pactl set-source-mute "$arg1" toggle
    else wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle 2>/dev/null; fi ;;
  toggle-app-mute)
    if command -v pactl >/dev/null 2>&1; then pactl set-sink-input-mute "$arg1" toggle
    else wpctl set-mute "$arg1" toggle 2>/dev/null; fi ;;
  *) echo "audio-action: unknown '$cmd'" >&2; exit 2 ;;
esac
