#!/usr/bin/env bash
# NYXUS · nyxus-save-state — one-shot: compile EWW CSS, bake accent baseline,
# GOLD recovery snapshot, backport live → canonical repo.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RECOVERY="${HOME}/nyxus-build-recovery"
STAMP="$(date +%Y%m%d-%H%M%S)"
GOLD="${RECOVERY}/GOLD-daily-driver-${STAMP}"
BASELINE="${HOME}/.config/nyxus/accent-baseline/home/cosmic/.config/eww"

echo "── NYXUS · save state (${STAMP}) ───────────────────────────────"

if [[ -x "${HOME}/.config/eww/scripts/compile-eww-css.sh" ]]; then
  "${HOME}/.config/eww/scripts/compile-eww-css.sh"
else
  echo "warn: compile-eww-css.sh missing" >&2
fi

mkdir -p "${BASELINE}"
if [[ -f "${HOME}/.config/eww/eww.scss.source" ]]; then
  cp "${HOME}/.config/eww/eww.scss.source" "${BASELINE}/eww.scss"
elif [[ -f "${HOME}/.config/eww/eww.scss" ]]; then
  cp "${HOME}/.config/eww/eww.scss" "${BASELINE}/eww.scss"
fi

mkdir -p "${GOLD}"/{eww,hypr,nyxus,dot-nyxus,local-bin,manifest}
rsync -a --exclude='.restore-points/' --exclude='*.bak*' --exclude='__pycache__/' \
  "${HOME}/.config/eww/" "${GOLD}/eww/"
rsync -a "${HOME}/.config/hypr/" "${GOLD}/hypr/"
for f in accent.json wallpaper.conf stations.json; do
  [[ -f "${HOME}/.config/nyxus/$f" ]] && cp "${HOME}/.config/nyxus/$f" "${GOLD}/nyxus/$f"
done
[[ -f "${HOME}/.config/nyxus/hw_profile.json" ]] && \
  cp "${HOME}/.config/nyxus/hw_profile.json" "${GOLD}/nyxus/hw_profile.json"
mkdir -p "${REPO}/artifacts/nyxus-config/hw_profiles"
[[ -f "${HOME}/.config/nyxus/hw_profile.json" ]] && \
  cp "${HOME}/.config/nyxus/hw_profile.json" "${REPO}/artifacts/nyxus-config/hw_profiles/gs77-ms17p1-cosmic.json"
[[ -d "${HOME}/.config/nyxus/accent-baseline" ]] && \
  rsync -a "${HOME}/.config/nyxus/accent-baseline/" "${GOLD}/nyxus/accent-baseline/"

# dot-nyxus essentials
for item in "${HOME}/.nyxus"/*; do
  base="$(basename "$item")"
  case "$base" in
    theme-backups|notes|store-catalog.json) continue ;;
  esac
  rsync -a "$item" "${GOLD}/dot-nyxus/" 2>/dev/null || true
done
[[ -f "${HOME}/.nyxus/nyxus-palette.css" ]] && \
  cp "${HOME}/.nyxus/nyxus-palette.css" "${GOLD}/dot-nyxus/" 2>/dev/null || true

for bin in "${HOME}/.local/bin"/nyxus-*; do
  [[ -f "$bin" ]] && cp "$bin" "${GOLD}/local-bin/$(basename "$bin")"
done

{
  echo "snapshot_at=$(date -Iseconds)"
  echo "hostname=$(hostname)"
  echo "user=${USER}"
  git -C "${REPO}" rev-parse HEAD 2>/dev/null | sed 's/^/git_head=/'
  git -C "${REPO}" log -1 --oneline 2>/dev/null || true
  echo "eww_count=$(pgrep -c -x eww 2>/dev/null || echo 0)"
  command -v eww >/dev/null && eww active-windows 2>/dev/null || true
  echo "--- hyprctl configerrors ---"
  hyprctl configerrors 2>/dev/null || true
  echo "--- wallpaper.conf ---"
  cat "${HOME}/.config/nyxus/wallpaper.conf" 2>/dev/null || true
} > "${GOLD}/manifest/health.txt"

ln -sfn "$(basename "$GOLD")" "${RECOVERY}/GOLD-LATEST"
echo "GOLD-LATEST -> $(basename "$GOLD")" > "${RECOVERY}/LATEST_SNAPSHOT"

"${REPO}/scripts/nyxus-backport-live.sh"

mkdir -p "${HOME}/.nyxus"
date -Iseconds > "${HOME}/.nyxus/.state-saved"

echo "── saved: ${GOLD}"
echo "── marker: ${HOME}/.nyxus/.state-saved"
