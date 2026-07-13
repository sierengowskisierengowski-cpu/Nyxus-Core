#!/usr/bin/env bash
# NYXUS · EWW · bluetooth action handler
# Usage: bt-action.sh <toggle|scan|connect|disconnect|pair|unpair|trust> [mac]
set -u

cmd="${1:-}"; mac="${2:-}"

# Strict MAC validation — bluetoothctl arg must be AA:BB:CC:DD:EE:FF form.
# Any non-empty $mac that fails this regex is rejected (defence-in-depth
# against malicious device names — though MAC is fixed-format anyway).
if [[ -n "$mac" && ! "$mac" =~ ^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$ ]]; then
  echo "bt-action: rejected non-MAC arg '$mac'" >&2
  exit 2
fi

case "$cmd" in
  toggle)
    if bluetoothctl show 2>/dev/null | grep -q 'Powered: yes'; then
      bluetoothctl power off
    else
      bluetoothctl power on
    fi
    ;;
  scan)
    # 8-second async scan window
    ( bluetoothctl --timeout 8 scan on >/dev/null 2>&1 ) &
    ;;
  connect)    [[ -n "$mac" ]] && bluetoothctl connect "$mac"    >/dev/null 2>&1 ;;
  disconnect) [[ -n "$mac" ]] && bluetoothctl disconnect "$mac" >/dev/null 2>&1 ;;
  pair)       [[ -n "$mac" ]] && bluetoothctl pair "$mac"       >/dev/null 2>&1 ;;
  unpair)     [[ -n "$mac" ]] && bluetoothctl remove "$mac"     >/dev/null 2>&1 ;;
  trust)      [[ -n "$mac" ]] && bluetoothctl trust "$mac"      >/dev/null 2>&1 ;;
  untrust)    [[ -n "$mac" ]] && bluetoothctl untrust "$mac"    >/dev/null 2>&1 ;;
  trust-toggle)
    if [[ -n "$mac" ]]; then
      if bluetoothctl info "$mac" 2>/dev/null | grep -q 'Trusted: yes'; then
        bluetoothctl untrust "$mac" >/dev/null 2>&1
      else
        bluetoothctl trust "$mac" >/dev/null 2>&1
      fi
    fi
    ;;
  *) echo "bt-action: unknown command '$cmd'" >&2; exit 2 ;;
esac
