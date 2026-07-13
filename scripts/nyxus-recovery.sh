#!/usr/bin/env bash
# NYXUS · nyxus-recovery.sh
# Restore the desktop from a GOLD snapshot (default: GOLD-LATEST).
#
# Usage:
#   ~/Nyxus-Core/scripts/nyxus-recovery.sh
#   ~/Nyxus-Core/scripts/nyxus-recovery.sh --from ~/nyxus-build-recovery/GOLD-...
#   ~/Nyxus-Core/scripts/nyxus-recovery.sh --dry-run

set -euo pipefail

RECOVERY="${HOME}/nyxus-build-recovery"
SRC=""
dry=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --from) shift; SRC="$1" ;;
    --dry-run) dry=1 ;;
    -h|--help) sed -n '2,9p' "$0"; exit 0 ;;
    *) echo "nyxus-recovery: unknown flag '$1'" >&2; exit 2 ;;
  esac
  shift
done

[[ -n "$SRC" ]] || SRC="${RECOVERY}/GOLD-LATEST"
[[ -L "$SRC" ]] && SRC="$(readlink -f "$SRC")"
[[ -d "$SRC" ]] || { echo "nyxus-recovery: snapshot not found: $SRC" >&2; exit 3; }

echo "── NYXUS recovery ──────────────────────────────────────────────"
echo "  source : $SRC"
echo "  mode   : $([[ $dry -eq 1 ]] && echo DRY-RUN || echo RESTORE)"

RSYNC=(rsync -a --exclude='.restore-points/' --exclude='__pycache__/')
[[ $dry -eq 1 ]] && RSYNC+=(--dry-run)

restore_dir() {
  local name="$1" src="$2" dst="$3"
  [[ -d "$src" ]] || return 0
  mkdir -p "$dst"
  "${RSYNC[@]}" "$src/" "$dst/"
  echo "  ✓ restored $name → $dst"
}

if [[ $dry -eq 1 ]]; then
  echo "  would restore eww, hypr, nyxus, rofi, wlogout, dunst, .nyxus, bin"
  exit 0
fi

restore_dir eww    "$SRC/eww"    "${HOME}/.config/eww"
restore_dir hypr   "$SRC/hypr"   "${HOME}/.config/hypr"
restore_dir nyxus  "$SRC/nyxus"  "${HOME}/.config/nyxus"
restore_dir rofi   "$SRC/rofi"   "${HOME}/.config/rofi"
restore_dir wlogout "$SRC/wlogout" "${HOME}/.config/wlogout"
restore_dir dunst  "$SRC/dunst"  "${HOME}/.config/dunst"

mkdir -p "${HOME}/.nyxus" "${HOME}/.local/bin"
[[ -d "$SRC/dot-nyxus" ]] && "${RSYNC[@]}" "$SRC/dot-nyxus/" "${HOME}/.nyxus/"
echo "  ✓ restored ~/.nyxus"

[[ -d "$SRC/local-bin" ]] && for b in "$SRC/local-bin"/nyxus-*; do
  [[ -f "$b" ]] && install -m 0755 "$b" "${HOME}/.local/bin/$(basename "$b")"
done
echo "  ✓ restored ~/.local/bin/nyxus-*"

# Palette mirror
PAL="${HOME}/.nyxus/nyxus-palette.css"
if [[ -f "$PAL" ]]; then
  for d in "${HOME}/.config/eww" "${HOME}/.config/rofi" \
           "${HOME}/.config/wlogout" "${HOME}/.config/dunst" \
           "${HOME}/.config/hypr"; do
    [[ -d "$d" ]] && cp -f "$PAL" "$d/nyxus-palette.css"
  done
fi

chmod +x "${HOME}/.config/eww/scripts/"*.sh 2>/dev/null || true
find "${HOME}/.config/eww/scripts" -maxdepth 1 -name '*.py' -exec chmod +x {} + 2>/dev/null || true

echo "── relaunching EWW ─────────────────────────────────────────────"
if command -v nyxus-eww-launch-safe >/dev/null 2>&1; then
  nyxus-eww-launch-safe
else
  pkill -x eww 2>/dev/null || true
  sleep 0.5
  eww daemon & sleep 2
  nyxus-eww-launch 2>/dev/null || true
fi

command -v hyprctl >/dev/null 2>&1 && hyprctl reload 2>/dev/null && echo "  ✓ hyprctl reload"

echo "── health ──────────────────────────────────────────────────────"
echo "  eww daemons: $(pgrep -c -x eww 2>/dev/null || echo 0)"
eww active-windows 2>/dev/null || true
echo "── recovery complete ─────────────────────────────────────────"
