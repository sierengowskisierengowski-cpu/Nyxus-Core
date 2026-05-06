#!/usr/bin/env bash
# nyxus-ticker.sh — rolling status line for the NYXUS top-bar ticker well.
#
# Output one line per invocation; waybar's custom/ticker module re-execs
# this every second and prints the result inside the inset ticker well.
# We cycle through a handful of status lines so the well "rolls" through
# the system's current state (notifications, mail, wifi, etc).
#
# To customize: edit the LINES array below or replace the line bodies
# with real shell commands (notify-send count, getmail count, etc).
#
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
set -euo pipefail

# How many seconds each line stays on screen before rolling to the next.
DWELL="${NYXUS_TICKER_DWELL:-3}"

# Live status lookups -- safe fallbacks if the underlying tool is missing.
notif_count() {
  if command -v dunstctl >/dev/null 2>&1; then
    dunstctl count waiting 2>/dev/null || echo 0
  else
    echo 0
  fi
}

wifi_status() {
  if command -v iwgetid >/dev/null 2>&1; then
    local s
    s="$(iwgetid -r 2>/dev/null || true)"
    [[ -n "$s" ]] && echo "$s" || echo "offline"
  else
    echo "n/a"
  fi
}

mail_count() {
  # Maildir new-mail count if INBOX exists, otherwise 0.
  local n=0
  if [[ -d "${HOME}/Mail/INBOX/new" ]]; then
    n=$(find "${HOME}/Mail/INBOX/new" -type f 2>/dev/null | wc -l)
  fi
  echo "$n"
}

LINES=(
  "  Notifications · $(notif_count) waiting"
  "  Mail · $(mail_count) unread"
  "  Wi-Fi · $(wifi_status)"
  "  Hyprland · $(date +%H:%M:%S)"
)

# Pick the line for this tick.  date/$DWELL gives us a slowly-advancing index.
INDEX=$(( ($(date +%s) / DWELL) % ${#LINES[@]} ))
echo "${LINES[$INDEX]}"
