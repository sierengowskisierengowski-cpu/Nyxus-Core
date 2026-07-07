#!/usr/bin/env bash
# APEX RIG — keyboard shortcut cheat sheet (Super+?)
set -euo pipefail
THEME="${HOME}/.config/rofi/launcher.rasi"
SHEET="${HOME}/.config/gowskinet/cheatsheet.txt"

rofi -dmenu -i -p "APEX Keys (Enter to close)" -theme "$THEME" -lines 22 < "$SHEET" >/dev/null || true
