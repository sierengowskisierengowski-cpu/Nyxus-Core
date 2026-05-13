#!/bin/sh
# Toggle the NYXUS Snap zone picker overlay.
# Bound to Super+Shift+S in default hotkeys.toml (post-Tier-1).
set -eu
if eww active-windows 2>/dev/null | grep -q '^snap-picker'; then
  eww close snap-picker
else
  nyxus-snap picker --layout "${1:-halves}" >/dev/null
  eww open snap-picker
fi
