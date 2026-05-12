#!/usr/bin/env bash
# NYXUS desktop context menu.
# Usage:
#   nyxus-context-menu.sh main       -> top-level right-click menu
#   nyxus-context-menu.sh wallpaper  -> wallpaper picker submenu
#   nyxus-context-menu.sh display    -> display-arrange submenu
#   nyxus-context-menu.sh sort       -> icon sort submenu (used by T2+)
#   nyxus-context-menu.sh dismiss    -> close any open menus / launcher
#
# Front-end: rofi -dmenu themed with NYXUS palette. Falls back to wofi
# if rofi is missing. Falls back to a notify-send error if neither.
set -euo pipefail

MODE="${1:-main}"
LOG="${HOME}/.cache/nyxus/context-menu.log"
mkdir -p "$(dirname "$LOG")"
exec 2>>"$LOG"
echo "--- $(date -Iseconds) mode=$MODE ---" >&2

GOLD="#d4b87a"
INK="#080a10"
INK2="#10131c"
TXT="#e6e8ee"
DIM="#8a8f9b"

_have() { command -v "$1" >/dev/null 2>&1; }

# ---------- frontend ----------
_menu() {
  # $1 = prompt, stdin = options (one per line)
  local prompt="$1"
  if _have rofi; then
    rofi -dmenu -i -no-custom -p "$prompt" \
      -theme-str "
        * { background-color: ${INK}; text-color: ${TXT};
            font: \"Inter 11\"; }
        window { width: 320px; padding: 6px; border: 1px;
                 border-color: ${GOLD}; border-radius: 10px; }
        mainbox { children: [ inputbar, listview ]; }
        inputbar { padding: 8px 10px; children: [ prompt, entry ];
                   background-color: ${INK2}; border-radius: 6px;
                   margin: 0 0 6px 0; }
        prompt { text-color: ${GOLD}; padding: 0 6px 0 0; }
        entry { placeholder-color: ${DIM}; }
        listview { lines: 12; spacing: 1px; scrollbar: false; }
        element { padding: 7px 10px; border-radius: 5px; }
        element selected { background-color: ${GOLD}; text-color: ${INK}; }
        element-text { background-color: inherit; text-color: inherit; }
      " 2>>"$LOG"
  elif _have wofi; then
    wofi --dmenu --prompt "$prompt" --width 320 --height 360
  else
    notify-send -u critical "NYXUS desktop" \
      "Install 'rofi' or 'wofi' to use the right-click menu."
    return 127
  fi
}

# ---------- helpers ----------
_term() {
  for t in nyxus-terminal kitty alacritty foot wezterm xterm; do
    if _have "$t"; then "$t" "$@" & return; fi
  done
  notify-send "NYXUS" "No terminal found"
}

_files_app() {
  if _have nyxus-files; then nyxus-files "$@" &
  elif _have nautilus; then nautilus "$@" &
  elif _have thunar; then thunar "$@" &
  elif _have dolphin; then dolphin "$@" &
  else _term -- "$(command -v lf || command -v ranger || echo bash)" "$@"; fi
}

_settings() {
  # arg = page id (Display, Appearance, etc.)
  if _have nyxus-settings; then nyxus-settings --page "${1:-}" &
  else notify-send "NYXUS" "Settings binary missing"; fi
}

_uniq_path() {
  # Suggest "name", "name 2", "name 3"... in $1 dir for base $2
  local dir="$1" base="$2" i=1 candidate
  candidate="$dir/$base"
  while [[ -e "$candidate" ]]; do
    i=$((i+1)); candidate="$dir/$base $i"
  done
  printf '%s' "$candidate"
}

_dismiss() {
  pkill -x rofi 2>/dev/null || true
  pkill -x wofi 2>/dev/null || true
  pkill -f nyxus_launcher.py 2>/dev/null || true
  exit 0
}

# ---------- menus ----------
_main_menu() {
  local choice
  choice=$(_menu "desktop" <<'EOF'
 New folder
 New text file
 Open in terminal
 Open Files
 Change wallpaper…
 Display settings
 Personalize…
 Sort icons…
 Refresh desktop
 System info
 Lock screen
 Power…
EOF
)
  [[ -z "${choice:-}" ]] && exit 0

  local desk="${HOME}/Desktop"; mkdir -p "$desk"
  case "$choice" in
    *"New folder")
      mkdir -p "$(_uniq_path "$desk" "New Folder")"
      ;;
    *"New text file")
      : > "$(_uniq_path "$desk" "New Text Document.txt")"
      ;;
    *"Open in terminal")
      ( cd "$desk" && _term )
      ;;
    *"Open Files")
      _files_app "$desk"
      ;;
    *"Change wallpaper"*)
      exec "$0" wallpaper
      ;;
    *"Display settings")
      _settings Display
      ;;
    *"Personalize"*)
      _settings Appearance
      ;;
    *"Sort icons"*)
      exec "$0" sort
      ;;
    *"Refresh desktop")
      _ipc_send "RELOAD"
      ;;
    *"System info")
      _settings About
      ;;
    *"Lock screen")
      if _have hyprlock; then hyprlock & 
      elif _have swaylock; then swaylock & 
      else loginctl lock-session; fi
      ;;
    *"Power"*)
      if _have nyxus_powermenu.py; then python3 "$(command -v nyxus_powermenu.py)" &
      elif [[ -x "${HOME}/.local/bin/nyxus_powermenu.py" ]]; then
        python3 "${HOME}/.local/bin/nyxus_powermenu.py" &
      else
        # inline mini power menu
        local p
        p=$(_menu "power" <<'PEOF'
 Suspend
 Hibernate
 Reboot
 Shutdown
 Log out
PEOF
)
        case "$p" in
          *Suspend)   systemctl suspend ;;
          *Hibernate) systemctl hibernate ;;
          *Reboot)    systemctl reboot ;;
          *Shutdown)  systemctl poweroff ;;
          *"Log out") hyprctl dispatch exit 2>/dev/null || loginctl terminate-session "${XDG_SESSION_ID:-}" ;;
        esac
      fi
      ;;
  esac
}

_wallpaper_menu() {
  local walls_dir="${HOME}/.config/hypr/walls"
  [[ -d "$walls_dir" ]] || walls_dir="${HOME}/Pictures/Wallpapers"
  [[ -d "$walls_dir" ]] || { notify-send "NYXUS" "No wallpapers dir"; exit 1; }
  local list
  list=$(find "$walls_dir" -maxdepth 1 -type f \
    \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.webp' \) \
    -printf '%f\n' | sort)
  list=$'Browse files…\nOpen Appearance settings…\n'"$list"
  local pick
  pick=$(printf '%s' "$list" | _menu "wallpaper")
  [[ -z "${pick:-}" ]] && exit 0
  case "$pick" in
    "Browse files"*)
      local f
      f=$(_have zenity && zenity --file-selection --title="Pick wallpaper" \
            --file-filter='Images | *.png *.jpg *.jpeg *.webp' 2>/dev/null || true)
      [[ -z "$f" ]] && exit 0
      _set_wallpaper "$f"
      ;;
    "Open Appearance"*)
      _settings Appearance
      ;;
    *)
      _set_wallpaper "$walls_dir/$pick"
      ;;
  esac
}

# Send a line over the desktop IPC socket. $1 = command, $2 = optional arg.
# Path is passed via env var to a python helper so filenames with quotes,
# spaces, or non-ASCII characters cannot break the call or inject code.
_ipc_send() {
  local cmd="$1" arg="${2:-}"
  local sock="${XDG_RUNTIME_DIR:-/tmp}/nyxus-desktop.sock"
  [[ -S "$sock" ]] || return 0
  if _have ncat; then
    if [[ -n "$arg" ]]; then printf '%s %s\n' "$cmd" "$arg"; else printf '%s\n' "$cmd"; fi \
      | ncat -U "$sock" >/dev/null 2>&1 || true
  elif _have socat; then
    if [[ -n "$arg" ]]; then printf '%s %s\n' "$cmd" "$arg"; else printf '%s\n' "$cmd"; fi \
      | socat - "UNIX-CONNECT:$sock" >/dev/null 2>&1 || true
  else
    NYXUS_IPC_SOCK="$sock" NYXUS_IPC_CMD="$cmd" NYXUS_IPC_ARG="$arg" \
      python3 -c '
import os, socket
sock = os.environ["NYXUS_IPC_SOCK"]
cmd  = os.environ["NYXUS_IPC_CMD"]
arg  = os.environ.get("NYXUS_IPC_ARG", "")
payload = (cmd + (" " + arg if arg else "") + "\n").encode("utf-8")
s = socket.socket(socket.AF_UNIX)
s.connect(sock)
s.sendall(payload)
s.close()
' >/dev/null 2>&1 || true
  fi
}

_set_wallpaper() {
  local path="$1"
  [[ -f "$path" ]] || { notify-send "NYXUS" "Not a file: $path"; exit 1; }
  # 1. Persist via shared setter (single source of truth on disk)
  if _have nyxus-set-wallpaper.sh; then
    nyxus-set-wallpaper.sh "$path" >/dev/null 2>&1 || true
  fi
  # 2. Hot-swap on the live desktop via safe IPC (no shell interpolation)
  _ipc_send "WALLPAPER" "$path"
  notify-send -i preferences-desktop-wallpaper "NYXUS" "Wallpaper updated"
}

_sort_menu() {
  local choice
  choice=$(_menu "sort" <<'EOF'
 By name
 By kind
 By date modified
 By size
 Snap to grid
 Auto-arrange
EOF
)
  [[ -z "${choice:-}" ]] && exit 0
  # T2 will read this state from ~/.config/nyxus/desktop-icons.json
  local key="name"
  case "$choice" in
    *kind) key="kind" ;;
    *date*) key="mtime" ;;
    *size) key="size" ;;
    *"Snap to grid") key="grid" ;;
    *"Auto-arrange") key="auto" ;;
  esac
  python3 - "$key" <<'PY' 2>/dev/null || true
import json,sys,os,pathlib
p=pathlib.Path(os.path.expanduser("~/.config/nyxus/desktop-icons.json"))
p.parent.mkdir(parents=True, exist_ok=True)
data={}
if p.exists():
    try: data=json.loads(p.read_text())
    except Exception: data={}
data["sort"]=sys.argv[1]
p.write_text(json.dumps(data, indent=2))
PY
  notify-send "NYXUS" "Sort: $choice (applied on next refresh)"
}

case "$MODE" in
  main)      _main_menu ;;
  wallpaper) _wallpaper_menu ;;
  sort)      _sort_menu ;;
  display)   _settings Display ;;
  dismiss)   _dismiss ;;
  *)         echo "unknown mode: $MODE" >&2; exit 2 ;;
esac
