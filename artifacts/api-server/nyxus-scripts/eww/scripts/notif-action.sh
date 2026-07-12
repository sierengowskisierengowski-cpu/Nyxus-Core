#!/usr/bin/env bash
# NYXUS · EWW · notification action handler
# Usage: notif-action.sh <pop|clear-all|toggle-dnd|close-id> [id]
set -u
cmd="${1:-}"; id="${2:-}"
case "$cmd" in
  pop)        dunstctl history-pop ;;
  clear-all)  dunstctl close-all ;;
  toggle-dnd) dunstctl set-paused toggle ;;
  close-id)   [[ -n "$id" ]] && dunstctl close "$id" ;;
  *) echo "notif-action: unknown '$cmd'" >&2; exit 2 ;;
esac
