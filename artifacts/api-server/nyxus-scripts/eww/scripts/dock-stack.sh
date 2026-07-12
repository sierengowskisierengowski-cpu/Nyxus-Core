#!/usr/bin/env bash
# Open a stack popup. $1 = stack id from dock.toml.
set -u
id="${1:-}"
[[ -z "$id" ]] && exit 0

state="$(nyxus-dock state 2>/dev/null || echo '{}')"
path="$(printf '%s' "$state" | python3 -c '
import json, sys
try: s = json.loads(sys.stdin.read())
except Exception: sys.exit(0)
target = sys.argv[1]
for st in s.get("stacks", []):
    if st.get("id") == target:
        print(st.get("path", "")); break
' -- "$id")"

if [[ -z "$path" || ! -d "$path" ]]; then
  notify-send "NYXUS Dock" "Stack '$id' has no folder."
  exit 0
fi

# Read filenames safely (NUL-delimited so weird names — including those
# starting with `-` or containing spaces — round-trip without breaking).
mapfile -d '' files < <(find "$path" -maxdepth 1 -mindepth 1 -printf '%T@ %P\0' \
                        | sort -z -nr | head -z -n 50 | cut -z -d' ' -f2-)

[[ ${#files[@]} -eq 0 ]] && { notify-send "NYXUS Dock" "$id is empty."; exit 0; }

if   command -v fuzzel >/dev/null; then pick="$(printf '%s\n' "${files[@]}" | fuzzel --dmenu --prompt="$id " --lines=10)"
elif command -v rofi   >/dev/null; then pick="$(printf '%s\n' "${files[@]}" | rofi -dmenu -p "$id")"
else                                    pick="${files[0]:-}"
fi

[[ -n "${pick:-}" ]] && xdg-open -- "$path/$pick" >/dev/null 2>&1 &
