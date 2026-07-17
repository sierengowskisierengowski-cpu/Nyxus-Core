#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
# nyxus-set-wallpaper.sh <name-or-path>   ·   rev 2026-07-07 r1 (Signature)
#
# Short-name resolver shim for nyxus-dynamic-wallpaper.sh, which has
# exec'd this (previously nonexistent!) script since Sprint G — the
# time-of-day wallpaper feature was silently broken because of it.
#
# Resolves, in order:
#   1. an absolute/relative path that exists as-is
#   2. nyxus-bg-<name>.png / nyxus-<name>.png / <name>.png in
#      ~/.config/hypr/walls and /usr/share/backgrounds/nyxus
#   3. fuzzy: first file in those dirs whose name contains <name>
# then hands off to nyxus-set-wallpaper (swww ripple + accent follow).
#
# © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ════════════════════════════════════════════════════════════════════
set -u
export PATH="${HOME}/.local/bin:${PATH}"

NAME="${1:-}"
[[ -z "${NAME}" ]] && { echo "usage: nyxus-set-wallpaper.sh <name-or-path>" >&2; exit 2; }

DIRS=("${HOME}/.config/hypr/walls" "/usr/share/backgrounds/nyxus")
TARGET=""

if [[ -r "${NAME}" ]]; then
  TARGET="${NAME}"
else
  for d in "${DIRS[@]}"; do
    for cand in "nyxus-bg-${NAME}.png" "nyxus-${NAME}.png" "${NAME}.png" \
                "nyxus-bg-${NAME}.jpg" "nyxus-${NAME}.jpg" "${NAME}.jpg"; do
      [[ -r "${d}/${cand}" ]] && { TARGET="${d}/${cand}"; break 2; }
    done
  done
fi

if [[ -z "${TARGET}" ]]; then
  for d in "${DIRS[@]}"; do
    hit="$(find "${d}" -maxdepth 1 -type f \( -name '*.png' -o -name '*.jpg' \) \
           -iname "*${NAME}*" 2>/dev/null | sort | head -1)"
    [[ -n "${hit}" ]] && { TARGET="${hit}"; break; }
  done
fi

if [[ -z "${TARGET}" ]]; then
  echo "nyxus-set-wallpaper.sh: no wallpaper matches '${NAME}'" >&2
  exit 1
fi

exec nyxus-set-wallpaper "${TARGET}"
