#!/usr/bin/env bash
# NYXUS · Starfield lock veil → hyprlock reveal
# Double-click the center star within 500ms to tear down the EWW veil
# and launch hyprlock (Prism HUD login). Config-only wiring — user tests
# hyprlock manually (never auto-run in CI/agent sessions).
set -euo pipefail

STAMP="${XDG_RUNTIME_DIR:-/tmp}/nyxus-star-dclick"
now=$(($(date +%s%N) / 1000000))

if [[ "${1:-}" == "--dismiss" ]]; then
  rm -f "$STAMP"
  eww close screensaver 2>/dev/null || true
  exit 0
fi

if [[ -f "$STAMP" ]]; then
  last=$(cat "$STAMP")
  if (( now - last < 500 )); then
    rm -f "$STAMP"
    eww close screensaver 2>/dev/null || true
    sleep 0.15
    hyprlock &
    exit 0
  fi
fi

echo "$now" > "$STAMP"
