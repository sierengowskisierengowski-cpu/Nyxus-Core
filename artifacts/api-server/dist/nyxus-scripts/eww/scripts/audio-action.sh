#!/usr/bin/env bash
# NYXUS · EWW · audio action handler
# Usage:
#   audio-action.sh set-default-sink   <id>
#   audio-action.sh set-default-source <id>
#   audio-action.sh set-sink-vol       <id> <0-150>
#   audio-action.sh set-source-vol     <id> <0-150>
#   audio-action.sh set-app-vol        <id> <0-150>
#   audio-action.sh toggle-sink-mute   <id>
#   audio-action.sh toggle-app-mute    <id>
set -u

cmd="${1:-}"; arg1="${2:-}"; arg2="${3:-}"

# Strict validation: ids are pulse short-form numerics, sink/source ids are
# alnum + dot/underscore/colon (e.g. alsa_output.pci-0000_00_1f.3.analog-stereo).
if [[ -n "$arg1" && ! "$arg1" =~ ^[A-Za-z0-9._:-]+$ ]]; then
  echo "audio-action: rejected id '$arg1'" >&2; exit 2
fi
if [[ -n "$arg2" && ! "$arg2" =~ ^[0-9]+$ ]]; then
  echo "audio-action: rejected vol '$arg2'" >&2; exit 2
fi
# Clamp vol to 0..150 (matches scale max in yuck)
if [[ -n "$arg2" && "$arg2" -gt 150 ]]; then arg2=150; fi

case "$cmd" in
  set-default-sink)   pactl set-default-sink   "$arg1" ;;
  set-default-source) pactl set-default-source "$arg1" ;;
  set-sink-vol)       pactl set-sink-volume    "$arg1" "${arg2}%" ;;
  set-source-vol)     pactl set-source-volume  "$arg1" "${arg2}%" ;;
  set-app-vol)        pactl set-sink-input-volume "$arg1" "${arg2}%" ;;
  toggle-sink-mute)   pactl set-sink-mute "$arg1" toggle ;;
  toggle-app-mute)    pactl set-sink-input-mute "$arg1" toggle ;;
  *) echo "audio-action: unknown '$cmd'" >&2; exit 2 ;;
esac
