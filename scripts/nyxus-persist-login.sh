#!/usr/bin/env bash
# NYXUS · persist-login — restore theme/bars after every Hyprland login.
set -u

LOG="${HOME}/.cache/nyxus-eww/persist-login.log"
mkdir -p "$(dirname "$LOG")"
ts() { date '+%F %T'; }

{
  echo "[$(ts)] persist-login start"

  # Clear stuck overlay locks from prior session
  rm -rf "${XDG_RUNTIME_DIR:-/tmp}/nyxus-overlay-shield.d" 2>/dev/null || true

  # Ensure CSS exists (offline-safe compile)
  if [[ -x "${HOME}/.config/eww/scripts/compile-eww-css.sh" ]]; then
    "${HOME}/.config/eww/scripts/compile-eww-css.sh" || true
  fi

  # Wallpaper
  if command -v nyxus-wallpaper-autostart >/dev/null 2>&1; then
    nyxus-wallpaper-autostart >>"$LOG" 2>&1 || true
  fi

  sleep 1

  # Bars — safe relaunch (compile + single daemon + 4 windows)
  if command -v nyxus-eww-launch-safe >/dev/null 2>&1; then
    nyxus-eww-launch-safe >>"$LOG" 2>&1 || true
  elif command -v nyxus-eww-launch >/dev/null 2>&1; then
    nyxus-eww-launch >>"$LOG" 2>&1 || true
  fi

  # Verify; restore from GOLD if bars still broken
  bars="$(eww active-windows 2>/dev/null | grep -cE '^bar-' || echo 0)"
  if [[ "$bars" -lt 4 ]] && command -v nyxus-restore-session >/dev/null 2>&1; then
    echo "[$(ts)] bars=$bars — restoring from GOLD-LATEST"
    nyxus-restore-session >>"$LOG" 2>&1 || true
  fi

  echo "[$(ts)] persist-login done (bars=$(eww active-windows 2>/dev/null | grep -cE '^bar-' || echo 0))"
} >>"$LOG" 2>&1
