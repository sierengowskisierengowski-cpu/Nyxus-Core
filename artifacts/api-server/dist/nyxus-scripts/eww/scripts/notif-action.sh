#!/usr/bin/env bash
# NYXUS · EWW · notification action handler
# Usage:
#   notif-action.sh pop
#   notif-action.sh clear-all
#   notif-action.sh toggle-dnd
#   notif-action.sh close-id   <id>
#   notif-action.sh invoke-id  <id>           # fires the notification's default action
#   notif-action.sh mute-app   b64:<base64>   # delegates to notif-mute.sh toggle
#                                              # (b64 prefix is mandatory — raw
#                                              # app names from notification
#                                              # metadata are NEVER trusted
#                                              # as shell input.)
set -u

cmd="${1:-}"
arg="${2:-}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

case "$cmd" in
  pop)        dunstctl history-pop ;;
  clear-all)  dunstctl close-all ;;
  toggle-dnd) dunstctl set-paused toggle ;;
  close-id)
    [[ -n "$arg" ]] || { echo "notif-action: close-id requires <id>" >&2; exit 2; }
    dunstctl close "$arg"
    ;;
  invoke-id)
    [[ -n "$arg" ]] || { echo "notif-action: invoke-id requires <id>" >&2; exit 2; }
    # dunstctl action invokes the notification's default action by id.
    # If no default action is registered, dunstctl is a silent no-op,
    # which is the correct UX (nothing should explode).
    dunstctl action "$arg" 2>/dev/null || true
    ;;
  mute-app)
    [[ -n "$arg" ]] || { echo "notif-action: mute-app requires b64:<base64>" >&2; exit 2; }
    # Strict prefix: refuse any non-b64 form so a future caller cannot
    # accidentally re-introduce raw interpolation. Decode failure → exit.
    case "$arg" in
      b64:*) decoded=$(printf '%s' "${arg#b64:}" | base64 -d 2>/dev/null) ;;
      *)     echo "notif-action: mute-app requires b64:<base64> (got raw)" >&2; exit 2 ;;
    esac
    [[ -n "$decoded" ]] || { echo "notif-action: mute-app got empty/invalid base64" >&2; exit 2; }
    "${script_dir}/notif-mute.sh" toggle "$decoded"
    ;;
  *)
    echo "notif-action: unknown '$cmd'" >&2
    exit 2
    ;;
esac
