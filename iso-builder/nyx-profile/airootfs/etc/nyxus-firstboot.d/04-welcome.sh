#!/usr/bin/env bash
# NYXUS firstboot · launch welcome wizard once.
set -e
[ -f "$HOME/.cache/nyxus/welcome.done" ] && exit 0
( python3 /opt/nyxus/nyxus_welcome.py >/dev/null 2>&1 & ) || true
mkdir -p "$HOME/.cache/nyxus"
touch "$HOME/.cache/nyxus/welcome.done"
