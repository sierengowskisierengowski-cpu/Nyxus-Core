#!/usr/bin/env bash
# nyxus-dock state stream for eww deflisten.
# Emits one JSON line per state change. Exits cleanly on SIGTERM.
set -u
export GTK_ICON_THEME="${GTK_ICON_THEME:-NYXUS-Dark:NYXUS-Aurora:Adwaita}"
exec /usr/bin/python3 /opt/nyxus/nyxus_dockd.py --watch 2>/dev/null \
  | /usr/bin/python3 "${HOME}/.config/eww/scripts/dock-enrich-icons.py"
