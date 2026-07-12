#!/usr/bin/env bash
# NYXUS · nyxus-audit-sync.sh
# Full round-trip: backport live → canonical, regenerate assets,
# deploy canonical → live, reload compositor + EWW, verify health.
#
# Usage:
#   ~/Nyxus-Core/scripts/nyxus-audit-sync.sh
#   ~/Nyxus-Core/scripts/nyxus-audit-sync.sh --no-backport   # deploy only
#   ~/Nyxus-Core/scripts/nyxus-audit-sync.sh --dry-run

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CANON="${REPO}/artifacts/api-server/nyxus-scripts"
backport=1
dry=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --no-backport) backport=0 ;;
    --dry-run)     dry=1; backport=1 ;;
    -h|--help)
      sed -n '2,11p' "$0"; exit 0 ;;
    *) echo "nyxus-audit-sync: unknown flag '$1'" >&2; exit 2 ;;
  esac
  shift
done

echo "═══════════════════════════════════════════════════════════════"
echo "  NYXUS BUILD AUDIT SYNC"
echo "  $(date -Iseconds)"
echo "═══════════════════════════════════════════════════════════════"

# 1. Backport live → canonical
if [[ $backport -eq 1 ]]; then
  bp_args=()
  [[ $dry -eq 1 ]] && bp_args+=(--dry-run)
  bash "${REPO}/scripts/nyxus-backport-live.sh" "${bp_args[@]}"
  [[ $dry -eq 1 ]] && exit 0
fi

# 2. Regenerate procedural assets (fog, starlight, cosmic flyouts)
EWW_SCRIPTS="${CANON}/eww/scripts"
regen_ok=0
for gen in gen-fog-texture.py gen-starlight-assets.py gen-cosmic-flyout-assets.py; do
  if [[ -x "${EWW_SCRIPTS}/$gen" ]] || [[ -f "${EWW_SCRIPTS}/$gen" ]]; then
    echo "── regenerate: $gen ──────────────────────────────────────────"
    python3 "${EWW_SCRIPTS}/$gen" 2>/dev/null && regen_ok=$((regen_ok+1)) || \
      echo "  ! $gen failed (non-fatal)"
  fi
done
echo "  regenerated $regen_ok asset generator(s)"

# 3. Mirror palette to all theme consumers
PAL="${CANON}/nyxus-palette.css"
if [[ -f "$PAL" ]]; then
  for dest in "${HOME}/.config/eww" "${HOME}/.config/wlogout" \
              "${HOME}/.config/dunst" "${HOME}/.config/rofi" \
              "${HOME}/.config/hypr" "${HOME}/.nyxus"; do
    [[ -d "$dest" ]] && cp -f "$PAL" "$dest/nyxus-palette.css"
  done
  echo "  ✓ palette mirrored to theme consumers"
fi

# 4. Deploy canonical → live
bash "${CANON}/sync-eww.sh" --no-reload
bash "${CANON}/sync-hypr.sh" --no-reload

# Copy hypr walls from canonical hypr-walls/ if present
if [[ -d "${CANON}/hypr-walls" ]]; then
  mkdir -p "${HOME}/.config/hypr/walls"
  rsync -a "${CANON}/hypr-walls/" "${HOME}/.config/hypr/walls/"
fi

# 5. Single-daemon EWW relaunch
if command -v nyxus-eww-launch-safe >/dev/null 2>&1; then
  echo "── relaunch EWW (single daemon) ────────────────────────────────"
  nyxus-eww-launch-safe
elif command -v eww >/dev/null 2>&1; then
  eww reload 2>/dev/null || true
fi

# 6. Hyprland reload
if command -v hyprctl >/dev/null 2>&1; then
  hyprctl reload 2>/dev/null && echo "  ✓ hyprctl reload" || true
  errs="$(hyprctl configerrors 2>/dev/null || true)"
  if [[ -n "$errs" && "$errs" != "no errors" ]]; then
    echo "── hyprctl configerrors ──────────────────────────────────────"
    echo "$errs"
  else
    echo "  ✓ hyprctl configerrors: clean"
  fi
fi

# 7. Health checks
echo "── health checks ───────────────────────────────────────────────"
eww_count="$(pgrep -c -x eww 2>/dev/null || echo 0)"
if [[ "$eww_count" -eq 1 ]]; then
  echo "  ✓ eww daemon count: 1"
elif [[ "$eww_count" -eq 0 ]]; then
  echo "  ! eww daemon not running"
else
  echo "  ! eww daemon count: $eww_count (expected 1 — double-bar risk)"
fi

for f in eww.yuck eww.scss nyxus.conf; do
  [[ -s "${HOME}/.config/eww/$f" ]] && echo "  ✓ eww/$f" || echo "  ✗ eww/$f MISSING"
done

script_count="$(find "${HOME}/.config/eww/scripts" -maxdepth 1 -type f | wc -l)"
canon_count="$(find "${CANON}/eww/scripts" -maxdepth 1 -type f | wc -l)"
echo "  eww scripts: live=$script_count canonical=$canon_count"

asset_count="$(find "${HOME}/.config/eww/assets" -type f 2>/dev/null | wc -l)"
echo "  eww assets: $asset_count files"

echo "═══════════════════════════════════════════════════════════════"
echo "  AUDIT SYNC COMPLETE"
echo "  Canonical: $CANON"
echo "  Next: git status → commit → push"
echo "═══════════════════════════════════════════════════════════════"
