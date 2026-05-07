#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────
# NYXUS Waybar Notification Status  ·  rev 2026-05-06x
# Emits a Waybar JSON line describing notification state via dunstctl.
# Used by the bottom waybar's notification fly-out button.
# ─────────────────────────────────────────────────────────────────────────

set -u
export LC_ALL=C.UTF-8

WAITING=$(timeout 1 dunstctl count waiting 2>/dev/null || echo 0)
DISPLAYED=$(timeout 1 dunstctl count displayed 2>/dev/null || echo 0)
HISTORY=$(timeout 1 dunstctl count history 2>/dev/null || echo 0)
PAUSED=$(timeout 1 dunstctl is-paused 2>/dev/null || echo false)

# Bell glyph (Symbols Nerd Font · 0xf0f3)
ICON=""
[ "$PAUSED" = "true" ] && ICON=""   # bell-slash (0xf1f6) when paused

# Show count badge only when there's something
TOTAL=$(( WAITING + DISPLAYED ))
if (( TOTAL > 0 )); then
  TEXT="${ICON} ${TOTAL}"
else
  TEXT="${ICON}"
fi

CLASS="notif"
[ "$PAUSED" = "true" ] && CLASS="notif paused"
(( TOTAL > 0 )) && CLASS="notif active"

TOOLTIP="<span size='x-large' weight='bold' foreground='#e8edf5'>NYXUS · Notifications</span>"
TOOLTIP+=$'\n'
TOOLTIP+="<span size='small' foreground='#a8b0bd'>"
TOOLTIP+="Waiting:    ${WAITING}"$'\n'
TOOLTIP+="Displayed:  ${DISPLAYED}"$'\n'
TOOLTIP+="History:    ${HISTORY}"$'\n'
TOOLTIP+="Paused:     ${PAUSED}"$'\n'
TOOLTIP+=$'\n'
TOOLTIP+="Click           · pop the latest"$'\n'
TOOLTIP+="Right-click     · clear all"$'\n'
TOOLTIP+="Middle-click    · toggle Do-Not-Disturb"
TOOLTIP+="</span>"

esc_json() {
  local s=$1
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\n'/\\n}
  printf '%s' "$s"
}

printf '{"text":"%s","tooltip":"%s","class":"%s","alt":"%s"}\n' \
  "$(esc_json "$TEXT")" "$(esc_json "$TOOLTIP")" "$CLASS" "$CLASS"
