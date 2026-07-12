#!/usr/bin/env bash
# Right-click context menu for a dock entry.
# IDs flow through argv into python — never via string interpolation —
# so a hostile window class can't escape into Python or the shell.
set -u

id="${1:-}"; addr="${2:-}"
[[ -z "$id" ]] && exit 0

state="$(nyxus-dock state 2>/dev/null || echo '{}')"

read -r is_pinned is_running < <(printf '%s' "$state" | python3 -c '
import json, sys
try: s = json.loads(sys.stdin.read())
except Exception: print("no no"); sys.exit(0)
target = sys.argv[1]
pin, run = "no", "no"
for e in s.get("entries", []):
    if e.get("id") == target:
        pin = "yes" if e.get("pinned") else "no"
        run = "yes" if e.get("running") else "no"
        break
print(pin, run)
' -- "$id")

opts=()
[[ "$is_running" == "yes" ]] && opts+=("Show all windows")
opts+=("Open new window")
[[ "$is_pinned"  == "yes" ]] && opts+=("Remove from Dock") || opts+=("Keep in Dock")
opts+=("Open at Login")
[[ "$is_running" == "yes" ]] && opts+=("Quit")
opts+=("Options…" "Close menu")

picker() {
  if   command -v fuzzel >/dev/null 2>&1; then printf '%s\n' "$@" | fuzzel --dmenu --prompt="$id " --lines=8 --width=22 2>/dev/null
  elif command -v wofi   >/dev/null 2>&1; then printf '%s\n' "$@" | wofi   --dmenu --prompt="$id"
  elif command -v rofi   >/dev/null 2>&1; then printf '%s\n' "$@" | rofi   -dmenu -p "$id" -theme ~/.config/rofi/nyxus.rasi
  else notify-send "NYXUS Dock" "No menu picker installed (fuzzel/wofi/rofi)."; return 1
  fi
}

choice="$(picker "${opts[@]}")"
case "$choice" in
  "Show all windows")
    addrs="$(printf '%s' "$state" | python3 -c '
import json, sys
try: s = json.loads(sys.stdin.read())
except Exception: sys.exit(0)
target = sys.argv[1]
for e in s.get("entries", []):
    if e.get("id") == target:
        print(" ".join(e.get("addresses", []))); break
' -- "$id")"
    for a in $addrs; do
      hyprctl dispatch focuswindow "address:$a" >/dev/null
      sleep 0.4
    done
    ;;
  "Open new window") nyxus-dock launch "$id" ;;
  "Keep in Dock")    nyxus-dock pin    "$id" ;;
  "Remove from Dock") nyxus-dock unpin "$id" ;;
  "Open at Login")
    autostart="$HOME/.config/autostart"
    mkdir -p -- "$autostart"
    safe_id="$(printf '%s' "$id" | tr -c 'A-Za-z0-9._-' '_')"
    f="$autostart/${safe_id}.desktop"
    if [[ -f "$f" ]]; then
      rm -f -- "$f"
      notify-send "NYXUS Dock" "Removed $id from login items."
    else
      {
        printf '[Desktop Entry]\n'
        printf 'Type=Application\n'
        printf 'Name=%s\n' "$id"
        printf 'Exec=nyxus-dock launch %q\n' "$id"
        printf 'X-GNOME-Autostart-enabled=true\n'
        printf 'NoDisplay=true\n'
      } > "$f"
      notify-send "NYXUS Dock" "Added $id to login items."
    fi
    ;;
  "Quit")    nyxus-dock quit "$id" ;;
  "Options…") python3 /opt/nyxus/nyxus_dock_settings.py --focus "$id" >/dev/null 2>&1 & ;;
  *) : ;;
esac
