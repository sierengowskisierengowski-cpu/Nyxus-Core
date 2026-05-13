#!/usr/bin/env bash
# Dock click router. eww calls this with: <event> <entry-id> [<addr>]
# event ∈ left | middle | right | drop | trash
#
# IDs are passed as argv to python (never interpolated into source) to
# eliminate any chance of shell/Python injection from a malicious window
# class name.
set -u

ev="${1:-left}"
id="${2:-}"
addr="${3:-}"

[[ -z "$id" ]] && exit 0

case "$ev" in
  left)
    if [[ -n "$addr" ]]; then
      nyxus-dock focus "$addr" >/dev/null
    else
      first_addr="$(nyxus-dock state 2>/dev/null \
        | python3 -c 'import json,sys
try: s = json.loads(sys.stdin.read())
except Exception: sys.exit(0)
target = sys.argv[1]
for e in s.get("entries", []):
    if e.get("id") == target and e.get("addresses"):
        print(e["addresses"][0]); break
' -- "$id")"
      if [[ -n "$first_addr" ]]; then
        nyxus-dock focus "$first_addr" >/dev/null
      else
        nyxus-dock launch "$id" >/dev/null
      fi
    fi
    ;;
  middle) nyxus-dock launch "$id" >/dev/null ;;
  right)  exec "$HOME/.config/eww/scripts/dock-menu.sh" "$id" "$addr" ;;
  drop)   exec "$HOME/.config/eww/scripts/dock-drop.sh" "$id" "${@:3}" ;;
  trash)
    case "$id" in
      open)  xdg-open "$HOME/.local/share/Trash/files" >/dev/null 2>&1 ;;
      empty) gio trash --empty 2>/dev/null \
               || { shopt -s nullglob; for f in "$HOME"/.local/share/Trash/files/*; do rm -rf -- "$f"; done; } ;;
    esac
    ;;
esac
