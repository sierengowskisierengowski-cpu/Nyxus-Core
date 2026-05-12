#!/usr/bin/env bash
# NYXUS · EWW · taskbar — running windows from Hyprland
# Emits {"items":[{address,title,class,glyph,active,workspace}, …]}
# Used by the live taskbar widget in the bottom bar.
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
set -u
export LC_ALL=C.UTF-8

empty='{"items":[]}'

if ! command -v hyprctl >/dev/null 2>&1; then
  printf '%s\n' "$empty"
  exit 0
fi

clients_json="$(hyprctl clients -j 2>/dev/null)"
[ -z "$clients_json" ] && { printf '%s\n' "$empty"; exit 0; }

active_addr="$(hyprctl activewindow -j 2>/dev/null | jq -r '.address // ""' 2>/dev/null)"

if ! command -v jq >/dev/null 2>&1; then
  printf '%s\n' "$empty"
  exit 0
fi

# Filter: real windows only (mapped, has workspace > 0, not floating
# overlay junk like the screensaver). Truncate title to 28 chars so
# the bar doesn't blow out on a 1366 panel. Glyph = upper-case first
# letter of class — same convention as the start menu tiles.
items="$(jq -c --arg active "$active_addr" '
  [ .[]
    | select(.mapped == true)
    | select(.workspace.id > 0)
    | select((.class // "") != "")
    | { address: .address,
        title:   ((.title // .class) | .[0:28]),
        class:   .class,
        glyph:   ( (.class // "?") | ascii_upcase | .[0:1] ),
        active:  ( .address == $active ),
        workspace: .workspace.id }
  ] | sort_by(.workspace, .class)
' <<<"$clients_json" 2>/dev/null)"

[ -z "$items" ] && items="[]"
printf '{"items":%s}\n' "$items"
