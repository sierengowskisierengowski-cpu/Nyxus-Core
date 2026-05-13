#!/bin/sh
# Toggle the Quick Settings drop-down (Super+Shift+Q by default).
set -eu
if eww active-windows 2>/dev/null | grep -q '^quicksettings'; then
  eww close quicksettings
else
  eww open quicksettings
fi
