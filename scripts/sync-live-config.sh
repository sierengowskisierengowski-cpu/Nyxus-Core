#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════
# sync-live-config.sh · rev 2026-07-07
#
# Pull the LIVE desktop configuration from this machine into the ISO
# skel + airootfs so the repo (and every future install) matches what
# is actually running. Run from anywhere; then review `git status`
# and commit.
#
#   ./scripts/sync-live-config.sh          # sync everything
#
# Volatile junk (logs, backups, caches, per-machine geometry) is
# excluded so diffs stay reviewable.
# © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ════════════════════════════════════════════════════════════════════
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SKEL="${REPO}/iso-builder/nyx-profile/airootfs/etc/skel"
ROOTFS="${REPO}/iso-builder/nyx-profile/airootfs"

RSYNC=(rsync -a --delete
  --exclude '*.bak*' --exclude '*.log' --exclude '__pycache__'
  --exclude '*.pyc'  --exclude 'welcome.done' --exclude 'theme-backups'
  --exclude '.claude' --exclude '*.mp4'
  --exclude 'accent-baseline'   # per-machine cache; regenerates on first accent apply
)

# ── ~/.config surfaces that define the NYXUS look ────────────────────
CONFIG_DIRS=(
  eww hypr rofi dunst swaync wlogout alacritty kitty cava btop
  qt5ct qt6ct gtk-3.0 gtk-4.0 nyxus
)
for d in "${CONFIG_DIRS[@]}"; do
  SRC="${HOME}/.config/${d}"
  [[ -d "${SRC}" ]] || { echo "skip (missing): ${d}"; continue; }
  mkdir -p "${SKEL}/.config/${d}"
  "${RSYNC[@]}" "${SRC}/" "${SKEL}/.config/${d}/"
  echo "synced: .config/${d}"
done

# per-machine noise that must not ship in skel
rm -f  "${SKEL}/.config/nyxus/welcome.done" \
       "${SKEL}/.config/qt6ct/qt6ct.conf.bak" 2>/dev/null || true
# qt SettingsWindow geometry is per-machine — strip the section
for q in qt5ct qt6ct; do
  f="${SKEL}/.config/${q}/${q}.conf"
  [[ -f "$f" ]] && sed -i '/^\[SettingsWindow\]/,/^\[/{/^\[SettingsWindow\]/d;/^\[/!d}' "$f"
done

# ── user + system scripts ────────────────────────────────────────────
mkdir -p "${ROOTFS}/usr/local/bin"
for f in "${HOME}/.local/bin/"nyxus-*; do
  [[ -f "$f" ]] || continue
  install -m 755 "$f" "${ROOTFS}/usr/local/bin/$(basename "$f")"
  echo "synced: usr/local/bin/$(basename "$f")"
done
for f in /usr/local/bin/nyxus*; do
  [[ -f "$f" ]] || continue
  # ~/.local/bin versions shadow and win — don't overwrite those
  [[ -f "${HOME}/.local/bin/$(basename "$f")" ]] && continue
  install -m 755 "$f" "${ROOTFS}/usr/local/bin/$(basename "$f")"
done
echo "synced: /usr/local/bin/nyxus*"

echo
echo "done — review with:  git -C ${REPO} status"
