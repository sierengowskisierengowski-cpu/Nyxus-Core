#!/usr/bin/env bash
# Open a stack popup. $1 = stack id from dock.toml.
# Renders a fuzzel-driven file list with thumbnails (via fuzzel --image).
set -u
id="${1:-}"
[[ -z "$id" ]] && exit 0

state="$(nyxus-dock state 2>/dev/null || echo '{}')"
path="$(printf '%s' "$state" | python3 -c "
import json, sys
s = json.loads(sys.stdin.read())
for st in s.get('stacks', []):
    if st.get('id') == '$id':
        print(st.get('path','')); break
")"

[[ -z "$path" || ! -d "$path" ]] && { notify-send "NYXUS Dock" "Stack '$id' has no folder."; exit 0; }

mapfile -t files < <(ls -1tr "$path" 2>/dev/null | tail -50 | tac)

if command -v fuzzel >/dev/null; then
  pick="$(printf '%s\n' "${files[@]}" | fuzzel --dmenu --prompt="$id " --lines=10)"
elif command -v rofi >/dev/null; then
  pick="$(printf '%s\n' "${files[@]}" | rofi -dmenu -p "$id")"
else
  pick="${files[0]:-}"
fi

[[ -n "${pick:-}" ]] && xdg-open "$path/$pick" >/dev/null 2>&1 &
