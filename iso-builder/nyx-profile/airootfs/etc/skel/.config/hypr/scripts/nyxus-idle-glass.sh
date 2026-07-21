#!/usr/bin/env bash
# ============================================================
#  NYXUS IDLE GLASS — fade windows to frosted glass on idle
#  ~/.config/hypr/scripts/nyxus-idle-glass.sh   (rev r1 · 2026-07-21)
#
#  Driven by hypridle: after a short idle window (see hypridle.conf)
#  every window drops to near-glass opacity WHILE BLUR STAYS ON, so
#  the living wallpaper / desktop reads straight through the frosted
#  panes — the "idle see-through" look. The first key/mouse input
#  fires on-resume, which snaps the shipped NYXUS opacities back.
#
#  Only the global decoration opacities are touched (one hyprctl
#  --batch each way), so it is instant and costs nothing while idle.
#  A runtime state file makes both directions idempotent and a reboot
#  always starts un-glassed. The screensaver + hyprlock windows are
#  pinned fully opaque by a windowrule (see hyprland.conf) so this
#  never makes the saver or lock screen see-through.
#
#  usage: nyxus-idle-glass.sh on|off
#  © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================
set -u

STATE="${XDG_RUNTIME_DIR:-/tmp}/nyxus-idle-glass.state"

# Shipped NYXUS defaults (hyprland.conf decoration + flair depth-of-field).
# on-resume restores exactly these rather than doing a full `hyprctl reload`,
# so the audio-reactive halo / any other runtime tweak is left untouched.
DEF_ACTIVE=0.90
DEF_INACTIVE=0.80
GLASS_ACTIVE=0.22
GLASS_INACTIVE=0.12

command -v hyprctl >/dev/null 2>&1 || exit 0

case "${1:-}" in
  on)
    [ -f "$STATE" ] && exit 0
    : > "$STATE"
    hyprctl --batch "keyword decoration:active_opacity ${GLASS_ACTIVE} ; keyword decoration:inactive_opacity ${GLASS_INACTIVE} ; keyword decoration:dim_inactive false" >/dev/null 2>&1
    ;;
  off)
    [ -f "$STATE" ] || exit 0
    rm -f "$STATE"
    hyprctl --batch "keyword decoration:active_opacity ${DEF_ACTIVE} ; keyword decoration:inactive_opacity ${DEF_INACTIVE} ; keyword decoration:dim_inactive true" >/dev/null 2>&1
    ;;
  *)
    echo "usage: $(basename "$0") on|off" >&2
    exit 2
    ;;
esac
