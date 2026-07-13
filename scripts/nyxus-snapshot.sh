#!/usr/bin/env bash
# NYXUS · nyxus-snapshot.sh
# Capture a GOLD recovery point from the current live desktop.
# Snapshots live at ~/nyxus-build-recovery/GOLD-<timestamp>/ (local only).
#
# Usage:
#   ~/Nyxus-Core/scripts/nyxus-snapshot.sh
#   ~/Nyxus-Core/scripts/nyxus-snapshot.sh --label post-bar-fix

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RECOVERY="${HOME}/nyxus-build-recovery"
label=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --label) shift; label="-$1" ;;
    -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
    *) echo "nyxus-snapshot: unknown flag '$1'" >&2; exit 2 ;;
  esac
  shift
done

STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="${RECOVERY}/GOLD${label}-${STAMP}"
mkdir -p "$DEST"

RSYNC=(rsync -a --exclude='.restore-points/' --exclude='__pycache__/' --exclude='*.bak' --exclude='*.bak-*')

echo "── NYXUS GOLD snapshot ───────────────────────────────────────"
echo "  dest : $DEST"

# Core UI
for pair in \
  "eww:${HOME}/.config/eww" \
  "hypr:${HOME}/.config/hypr" \
  "nyxus:${HOME}/.config/nyxus" \
  "rofi:${HOME}/.config/rofi" \
  "wlogout:${HOME}/.config/wlogout" \
  "dunst:${HOME}/.config/dunst"; do
  name="${pair%%:*}"; src="${pair#*:}"
  [[ -d "$src" ]] || continue
  mkdir -p "$DEST/$name"
  "${RSYNC[@]}" "$src/" "$DEST/$name/"
  echo "  ✓ $name"
done

# NYXUS apps (python + packages, not backgrounds bulk)
mkdir -p "$DEST/dot-nyxus"
for f in "${HOME}/.nyxus"/nyxus*.py "${HOME}/.nyxus"/nyxus-*.py; do
  [[ -f "$f" ]] && cp -a "$f" "$DEST/dot-nyxus/"
done
for pkg in nyxus-home nyxus-start nyxus-panel; do
  [[ -d "${HOME}/.nyxus/$pkg" ]] && \
    "${RSYNC[@]}" "${HOME}/.nyxus/$pkg/" "$DEST/dot-nyxus/$pkg/"
done
[[ -f "${HOME}/.nyxus/nyxus-palette.css" ]] && \
  cp -a "${HOME}/.nyxus/nyxus-palette.css" "$DEST/dot-nyxus/"
echo "  ✓ dot-nyxus"

# Launchers
mkdir -p "$DEST/local-bin"
for b in "${HOME}/.local/bin"/nyxus-*; do
  [[ -f "$b" ]] && cp -a "$b" "$DEST/local-bin/"
done
echo "  ✓ local-bin ($(ls "$DEST/local-bin" 2>/dev/null | wc -l) scripts)"

# Wallpaper manifest (paths only — walls stay in ~/.config/hypr/walls/)
mkdir -p "$DEST/manifest"
[[ -f "${HOME}/.config/nyxus/wallpaper.conf" ]] && \
  cp -a "${HOME}/.config/nyxus/wallpaper.conf" "$DEST/manifest/"
ls -la "${HOME}/.config/hypr/walls/" > "$DEST/manifest/walls-ls.txt" 2>/dev/null || true

# Health + git metadata
{
  echo "snapshot_at=$(date -Iseconds)"
  echo "hostname=$(hostname)"
  echo "user=$USER"
  git -C "$REPO" rev-parse HEAD 2>/dev/null && echo "git_head=$(git -C "$REPO" rev-parse HEAD)"
  git -C "$REPO" log -1 --oneline 2>/dev/null
  echo "eww_count=$(pgrep -c -x eww 2>/dev/null || echo 0)"
  eww active-windows 2>/dev/null || true
} > "$DEST/manifest/health.txt"

# Pin as latest GOLD symlink
rm -f "${RECOVERY}/GOLD-LATEST"
ln -sfn "$(basename "$DEST")" "${RECOVERY}/GOLD-LATEST"
echo "  ✓ GOLD-LATEST → $(basename "$DEST")"
echo "── done ──────────────────────────────────────────────────────"
