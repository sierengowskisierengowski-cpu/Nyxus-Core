#!/usr/bin/env bash
# nyxus-window-menu.sh — Title-bar RMB window menu (rev r15)
#
# Invoked when the user right-clicks the title bar / header bar of
# any NYXUS GTK4 app (wired via install_chrome in nyxus_chrome.py).
# Presents the Windows/macOS-style window menu:
#
#     Move           → hyprctl dispatch movewindow (pointer-driven)
#     Resize         → hyprctl dispatch resizeactive (pointer-driven)
#     Minimize       → hyprctl dispatch togglespecialworkspace
#     Maximize       → hyprctl dispatch fullscreen 1 (toggle maximize)
#     Restore        → hyprctl dispatch fullscreen 0 (clear maximize)
#     Close          → hyprctl dispatch killactive
#
# The Move and Resize actions activate Hyprland's interactive grab so
# the user can drag the pointer to position/size — exactly matching
# the macOS/Windows behaviour where "Move" enters a drag-grab state.

set -euo pipefail

if ! command -v hyprctl >/dev/null 2>&1; then
  notify-send "NYXUS" "hyprctl not available; window menu unavailable" 2>/dev/null || true
  exit 1
fi

# ── Detect current maximize state for adaptive label ────────────
state="$(hyprctl -j activewindow 2>/dev/null \
  | grep -oE '"fullscreen": *[0-9]+' | head -1 | grep -oE '[0-9]+' || echo 0)"
if [[ "${state}" == "0" ]]; then
  MAXIMIZE_LABEL="  Maximize"
else
  MAXIMIZE_LABEL="  Restore"
fi

ENTRIES=(
  "  Move"
  "  Resize"
  "  Minimize"
  "${MAXIMIZE_LABEL}"
  "  Close"
)

pick_menu() {
  if command -v wofi >/dev/null 2>&1; then
    printf '%s\n' "${ENTRIES[@]}" | wofi \
      --dmenu --prompt "Window" --width 240 --height 280 --location 7 \
      --hide-scroll --insensitive 2>/dev/null \
      || printf '%s\n' "${ENTRIES[@]}" | wofi --dmenu --prompt "Window"
  elif command -v rofi >/dev/null 2>&1; then
    printf '%s\n' "${ENTRIES[@]}" | rofi -dmenu -p "Window"
  else
    exit 1
  fi
}

choice="$(pick_menu || true)"
[[ -z "${choice}" ]] && exit 0

case "${choice}" in
  *Move*)
    # Enter Hyprland's interactive "windowmove" submap (defined in
    # nyxus-windowrules.conf). Arrow keys step 30px; SHIFT+arrows step
    # finer. Esc or Enter exits the submap. The window must be
    # floating for movewindow to work freely; force-float first.
    hyprctl dispatch setfloating active >/dev/null 2>&1 || true
    hyprctl dispatch submap windowmove >/dev/null 2>&1 || true
    notify-send "NYXUS Window" "Move mode — use arrows / Esc to finish" 2>/dev/null || true
    ;;
  *Resize*)
    # Enter the "windowresize" submap. Same Esc/Enter exit contract.
    hyprctl dispatch setfloating active >/dev/null 2>&1 || true
    hyprctl dispatch submap windowresize >/dev/null 2>&1 || true
    notify-send "NYXUS Window" "Resize mode — use arrows / Esc to finish" 2>/dev/null || true
    ;;
  *Minimize*)
    # Hyprland has no true "minimize" — closest is move-to-special workspace.
    hyprctl dispatch movetoworkspacesilent special:minimized >/dev/null 2>&1 || true
    ;;
  *Maximize*)
    hyprctl dispatch fullscreen 1 >/dev/null 2>&1 || true
    ;;
  *Restore*)
    hyprctl dispatch fullscreen 0 >/dev/null 2>&1 || true
    ;;
  *Close*)
    hyprctl dispatch killactive >/dev/null 2>&1 || true
    ;;
esac
