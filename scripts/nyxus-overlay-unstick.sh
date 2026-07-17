#!/usr/bin/env bash
# NYXUS · nyxus-overlay-unstick — emergency: close stuck EWW overlays + restore bars.
set -u

runtime="${XDG_RUNTIME_DIR:-/tmp}"
lock="${runtime}/nyxus-overlay-shield.d"

# Close fullscreen overlays / flyouts (keep bar-* windows).
if command -v eww >/dev/null 2>&1; then
  while IFS= read -r line; do
    win="${line%%:*}"
    win="${win#"${win%%[![:space:]]*}"}"
    [[ -z "$win" || "$win" == bar-* ]] && continue
    eww close "$win" 2>/dev/null || true
  done < <(eww active-windows 2>/dev/null || true)
fi

# Restore bars from shield stash or relaunch clean.
if [[ -f "${lock}/bars" ]]; then
  while read -r b; do
    [[ -n "$b" ]] && eww open "$b" 2>/dev/null || true
  done < "${lock}/bars"
fi
rm -rf "$lock"

if command -v nyxus-eww-launch-safe >/dev/null 2>&1; then
  nyxus-eww-launch-safe
elif command -v nyxus-eww-launch >/dev/null 2>&1; then
  nyxus-eww-launch
fi

notify-send -u normal "NYXUS" "Overlays closed · bars restored" 2>/dev/null || true
