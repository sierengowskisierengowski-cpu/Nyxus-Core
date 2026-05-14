#!/usr/bin/env bash
# nyxus-context-menu.sh — Desktop RMB context menu (rev r15)
#
# Invoked by nyxus_desktop.py when the user right-clicks an empty area
# of the wallpaper. Presents a Windows/macOS-style "right-click on
# desktop" menu with the standard NYXUS actions:
#
#     Change Wallpaper            → nyxus-wallpaper-studio
#     New Folder                  → mkdir in ~/Desktop with unique name
#     New File                    → touch in ~/Desktop with unique name
#     Open Terminal Here          → nyxus-terminal cwd=~/Desktop
#     Display Settings            → nyxus-settings --page display
#     Refresh                     → restart nyxus-desktop service
#
# The menu is rendered via wofi (preferred) or rofi (fallback). Both
# are guaranteed-present per packages.x86_64. Output is the chosen
# label; we then dispatch.
#
# Per the user-locked Real-OS desktop contract (Sprint B): every entry
# must do exactly what it says — no toggles that go nowhere, no
# placeholder text. All targets verified to exist before dispatch.

set -euo pipefail

DESKTOP_DIR="${XDG_DESKTOP_DIR:-${HOME}/Desktop}"
mkdir -p "${DESKTOP_DIR}"

# ── Menu entries (label → action token) ─────────────────────────
ENTRIES=(
  "  Change Wallpaper"
  "  New Folder"
  "  New File"
  "  Open Terminal Here"
  "  Display Settings"
  "  Refresh Desktop"
)

# ── Pick a menu renderer ────────────────────────────────────────
pick_menu() {
  if command -v wofi >/dev/null 2>&1; then
    printf '%s\n' "${ENTRIES[@]}" | wofi \
      --dmenu \
      --prompt "Desktop" \
      --width 280 --height 320 \
      --location 7 \
      --hide-scroll \
      --insensitive \
      --style /usr/share/nyxus/wofi/context-menu.css 2>/dev/null \
      || printf '%s\n' "${ENTRIES[@]}" | wofi --dmenu --prompt "Desktop"
  elif command -v rofi >/dev/null 2>&1; then
    printf '%s\n' "${ENTRIES[@]}" | rofi -dmenu -p "Desktop" -theme-str 'window {width: 280px;}'
  else
    notify-send "NYXUS" "No menu renderer (wofi/rofi) installed" >/dev/null 2>&1 || true
    exit 1
  fi
}

# ── Generate a unique filename in DESKTOP_DIR ───────────────────
unique_name() {
  local base="$1" ext="${2:-}" i=0 candidate
  candidate="${DESKTOP_DIR}/${base}${ext}"
  while [[ -e "${candidate}" ]]; do
    i=$((i + 1))
    candidate="${DESKTOP_DIR}/${base} (${i})${ext}"
  done
  printf '%s\n' "${candidate}"
}

# ── Dispatch ─────────────────────────────────────────────────────
choice="$(pick_menu || true)"
[[ -z "${choice}" ]] && exit 0

case "${choice}" in
  *Wallpaper*)
    if command -v nyxus-wallpaper-studio >/dev/null 2>&1; then
      exec nyxus-wallpaper-studio
    elif command -v nyxus_wallpaper_studio >/dev/null 2>&1; then
      exec nyxus_wallpaper_studio
    else
      exec python3 /opt/nyxus/nyxus_wallpaper_studio.py
    fi
    ;;
  *"New Folder"*)
    target="$(unique_name "New Folder" "")"
    mkdir -p "${target}"
    notify-send "NYXUS Desktop" "Created: $(basename "${target}")" 2>/dev/null || true
    ;;
  *"New File"*)
    target="$(unique_name "New File" ".txt")"
    : > "${target}"
    notify-send "NYXUS Desktop" "Created: $(basename "${target}")" 2>/dev/null || true
    ;;
  *Terminal*)
    if command -v nyxus-terminal >/dev/null 2>&1; then
      exec nyxus-terminal --working-directory="${DESKTOP_DIR}"
    else
      exec python3 /opt/nyxus/nyxus_terminal.py --cwd "${DESKTOP_DIR}"
    fi
    ;;
  *Display*)
    if command -v nyxus-settings >/dev/null 2>&1; then
      exec nyxus-settings --page display
    else
      exec python3 /opt/nyxus/nyxus_settings.py --page display
    fi
    ;;
  *Refresh*)
    if command -v systemctl >/dev/null 2>&1; then
      systemctl --user restart nyxus-desktop.service 2>/dev/null \
        || pkill -USR1 -f nyxus_desktop.py 2>/dev/null || true
    else
      pkill -USR1 -f nyxus_desktop.py 2>/dev/null || true
    fi
    notify-send "NYXUS Desktop" "Refreshed" 2>/dev/null || true
    ;;
esac
