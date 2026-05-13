#!/usr/bin/env bash
# nyxus-dock state stream for eww deflisten.
# Emits one JSON line per state change. Exits cleanly on SIGTERM.
set -u
exec /usr/bin/python3 /opt/nyxus/nyxus_dockd.py --watch 2>/dev/null
