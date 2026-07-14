#!/usr/bin/env bash
# NYXUS · nyxus-restore-session — restore last GOLD snapshot + relaunch bars.
set -euo pipefail

RECOVERY="${HOME}/nyxus-build-recovery"
GOLD="${RECOVERY}/GOLD-LATEST"

[[ -L "$GOLD" || -d "$GOLD" ]] || {
  echo "nyxus-restore-session: no GOLD-LATEST at ${RECOVERY}" >&2
  exit 1
}

echo "── NYXUS · restore session from $(readlink -f "$GOLD") ──"

if [[ -d "${GOLD}/eww" ]]; then
  rsync -a --delete \
    --exclude='.restore-points/' --exclude='*.bak*' \
    "${GOLD}/eww/" "${HOME}/.config/eww/"
  rm -f "${HOME}/.config/eww/eww.scss"
fi

if [[ -x "${HOME}/.config/eww/scripts/compile-eww-css.sh" ]]; then
  "${HOME}/.config/eww/scripts/compile-eww-css.sh" || true
fi

if command -v nyxus-overlay-unstick >/dev/null 2>&1; then
  nyxus-overlay-unstick
elif command -v nyxus-eww-launch-safe >/dev/null 2>&1; then
  nyxus-eww-launch-safe
fi

echo "── session restored ──"
