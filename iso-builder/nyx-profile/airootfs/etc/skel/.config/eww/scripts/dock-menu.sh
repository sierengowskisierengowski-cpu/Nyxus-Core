#!/usr/bin/env bash
# Right-click context menu for a dock entry. Driven by fuzzel --dmenu (preferred)
# falling back to wofi or rofi if fuzzel is missing.
set -u

id="${1:-}"; addr="${2:-}"
if [[ -z "$id" ]]; then exit 0; fi

state="$(nyxus-dock state 2>/dev/null || echo '{}')"

is_pinned="$(printf '%s' "$state" | python3 -c "
import json, sys
try:
    s = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)
for e in s.get('entries', []):
    if e.get('id') == '$id':
        print('yes' if e.get('pinned') else 'no'); break
")"

is_running="$(printf '%s' "$state" | python3 -c "
import json, sys
try:
    s = json.loads(sys.stdin.read())
except Exception:
    sys.exit(0)
for e in s.get('entries', []):
    if e.get('id') == '$id':
        print('yes' if e.get('running') else 'no'); break
")"

opts=()
[[ "$is_running" == "yes" ]] && opts+=("Show all windows")
opts+=("Open new window")
if [[ "$is_pinned" == "yes" ]]; then
  opts+=("Remove from Dock")
else
  opts+=("Keep in Dock")
fi
opts+=("Open at Login")
[[ "$is_running" == "yes" ]] && opts+=("Quit")
opts+=("Options…" "Close menu")

picker() {
  if command -v fuzzel >/dev/null 2>&1; then
    printf '%s\n' "$@" | fuzzel --dmenu --prompt="$id " --lines=8 --width=22 2>/dev/null
  elif command -v wofi >/dev/null 2>&1; then
    printf '%s\n' "$@" | wofi --dmenu --prompt="$id"
  elif command -v rofi >/dev/null 2>&1; then
    printf '%s\n' "$@" | rofi -dmenu -p "$id" -theme ~/.config/rofi/nyxus.rasi
  else
    notify-send "NYXUS Dock" "No menu picker installed (fuzzel/wofi/rofi)."
    return 1
  fi
}

choice="$(picker "${opts[@]}")"
case "$choice" in
  "Show all windows")
    # cycle through addresses
    addrs="$(printf '%s' "$state" | python3 -c "
import json, sys
s = json.loads(sys.stdin.read())
for e in s.get('entries', []):
    if e.get('id') == '$id':
        print(' '.join(e.get('addresses', []))); break
")"
    for a in $addrs; do
      hyprctl dispatch focuswindow "address:$a" >/dev/null
      sleep 0.4
    done
    ;;
  "Open new window")        nyxus-dock launch "$id" ;;
  "Keep in Dock")           nyxus-dock pin "$id" ;;
  "Remove from Dock")       nyxus-dock unpin "$id" ;;
  "Open at Login")
    autostart="$HOME/.config/autostart"
    mkdir -p "$autostart"
    f="$autostart/${id}.desktop"
    if [[ -f "$f" ]]; then
      rm -f "$f"
      notify-send "NYXUS Dock" "Removed $id from login items."
    else
      cat > "$f" <<EOF
[Desktop Entry]
Type=Application
Name=$id
Exec=nyxus-dock launch $id
X-GNOME-Autostart-enabled=true
NoDisplay=true
EOF
      notify-send "NYXUS Dock" "Added $id to login items."
    fi
    ;;
  "Quit")                   nyxus-dock quit "$id" ;;
  "Options…")               python3 /opt/nyxus/nyxus_dock_settings.py --focus "$id" >/dev/null 2>&1 & ;;
  *)                        : ;;
esac
