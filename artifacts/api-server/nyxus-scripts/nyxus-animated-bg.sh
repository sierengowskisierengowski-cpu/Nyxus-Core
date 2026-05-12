#!/usr/bin/env bash
# NYXUS Animated Wallpaper — mpvpaper driver
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
# Loops a video file as the desktop background using mpvpaper. Falls
# back to swaybg + the still frame when mpvpaper is not installed.
#
# Install once:  pacman -S mpvpaper
# Autostart:     add  `exec-once = ~/.local/bin/nyxus-animated-bg.sh` to hyprland.conf
#
# Usage:
#   nyxus-animated-bg.sh                 # loops the default dark-mirror clip
#   nyxus-animated-bg.sh /path/to.mp4    # loops a custom clip

set -u

VIDEO="${1:-$HOME/.config/hypr/walls/nyxus-bg-darkmirror.mp4}"
STILL="${VIDEO%.mp4}.png"
MONITOR="${NYXUS_BG_MONITOR:-*}"   # "*" = all monitors

# Kill any previous wallpaper daemons so we don't stack processes.
pkill -x mpvpaper 2>/dev/null
pkill -x swaybg   2>/dev/null
sleep 0.2

if command -v mpvpaper >/dev/null 2>&1 && [ -f "$VIDEO" ]; then
  # Mute, loop, hardware decode if available, no on-screen controls,
  # GPU video output for low CPU on the MSI iGPU.
  exec mpvpaper -o "no-audio loop hwdec=auto vo=gpu --no-osc --no-input-default-bindings --really-quiet" \
                -f "$MONITOR" "$VIDEO"
fi

# Fallback: static frame.
if command -v swaybg >/dev/null 2>&1 && [ -f "$STILL" ]; then
  exec swaybg -i "$STILL" -m fill
fi

echo "[nyxus-animated-bg] no usable backend (need mpvpaper or swaybg)" >&2
exit 1
