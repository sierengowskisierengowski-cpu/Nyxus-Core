#!/usr/bin/env bash
# Dock click router. eww calls this with: <event> <entry-id> [<addr>]
# event ∈ left | middle | right | drop
set -u

ev="${1:-left}"
id="${2:-}"
addr="${3:-}"

if [[ -z "$id" ]]; then exit 0; fi

case "$ev" in
  left)
    # If running and focused → minimize/cycle. If running not focused → focus first window.
    # If not running → launch.
    if [[ -n "$addr" ]]; then
      nyxus-dock focus "$addr" >/dev/null
    else
      # Lookup whether app has any addresses in current state
      state="$(nyxus-dock state 2>/dev/null || true)"
      first_addr="$(printf '%s' "$state" | python3 -c "
import json, sys
try:
    s = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)
for e in s.get('entries', []):
    if e.get('id') == '$id' and e.get('addresses'):
        print(e['addresses'][0]); break
")"
      if [[ -n "$first_addr" ]]; then
        nyxus-dock focus "$first_addr" >/dev/null
      else
        nyxus-dock launch "$id" >/dev/null
      fi
    fi
    ;;
  middle)
    # middle-click → always launch new instance
    nyxus-dock launch "$id" >/dev/null
    ;;
  right)
    exec "$HOME/.config/eww/scripts/dock-menu.sh" "$id" "$addr"
    ;;
  drop)
    exec "$HOME/.config/eww/scripts/dock-drop.sh" "$id" "${@:3}"
    ;;
  trash)
    case "$id" in
      open)  xdg-open "$HOME/.local/share/Trash/files" >/dev/null 2>&1 ;;
      empty) gio trash --empty 2>/dev/null || rm -rf "$HOME/.local/share/Trash/files/"* ;;
    esac
    ;;
esac
