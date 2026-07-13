#!/usr/bin/env bash
# NYXUS · EWW · fullscreen-overlay shield (rev 2026-07-09)
#
# Layer-shell surfaces can never cover the bars' exclusive zones, so a
# "100%x100%" overlay still leaves the bar strips peeking through. This
# shield closes the four bars while a fullscreen overlay window is up
# (Hyprland then re-arranges the overlay to true fullscreen) and
# restores them the moment it closes.
#
# Wired as a defpoll that only the overlay windows reference — eww only
# runs polls for open windows, so opening the overlay starts the shield
# automatically. Idempotent via a runtime state dir.
set -u
win="${1:?usage: overlay-shield.sh <overlay-window>}"

runtime="${XDG_RUNTIME_DIR:-/tmp}"
lock="${runtime}/nyxus-overlay-shield.d"

# already shielding (any overlay) — nothing to do
mkdir "$lock" 2>/dev/null || { echo ""; exit 0; }

bars=$(eww active-windows 2>/dev/null | awk -F': ' '/^bar-/{print $1}')
if [[ -z "$bars" ]]; then
  rmdir "$lock" 2>/dev/null
  echo ""
  exit 0
fi
printf '%s\n' $bars > "$lock/bars"

for b in $bars; do eww close "$b" 2>/dev/null; done

(
  # wait for ANY shielded overlay to close, then restore the bars.
  # covers dashboard/powermenu/cheatsheet/deepcore chained via
  # "close X && open Y" — as long as one is up, bars stay hidden.
  while :; do
    act=$(eww active-windows 2>/dev/null) || break
    grep -qE '^(dashboard|powermenu|cheatsheet|deepcore|mission): ' <<<"$act" || break
    sleep 0.4
  done
  while read -r b; do eww open "$b" 2>/dev/null; done < "$lock/bars"
  rm -rf "$lock"
) >/dev/null 2>&1 & disown

echo ""
