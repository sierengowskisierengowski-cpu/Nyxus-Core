#!/usr/bin/env bash
# NYXUS · nyxus-backport-live.sh
# Copy the live runtime (~/.config, ~/.nyxus, ~/.local/bin) into the
# canonical Nyxus-Core source tree at artifacts/api-server/nyxus-scripts/.
#
# Run this after polishing on the live desktop so git stays in sync.
# Companion: sync-eww.sh / sync-hypr.sh deploy canonical → live.
#
# Usage:
#   ~/Nyxus-Core/scripts/nyxus-backport-live.sh
#   ~/Nyxus-Core/scripts/nyxus-backport-live.sh --dry-run

set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CANON="${REPO}/artifacts/api-server/nyxus-scripts"
NYXUS_CFG="${REPO}/artifacts/nyxus-config"
dry=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) dry=1 ;;
    -h|--help)
      sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "nyxus-backport-live: unknown flag '$1'" >&2; exit 2 ;;
  esac
  shift
done

RSYNC=(rsync -a --itemize-changes)
[[ $dry -eq 1 ]] && RSYNC+=(--dry-run)

echo "── NYXUS · backport live → canonical ─────────────────────────"
echo "  repo   : $REPO"
echo "  canon  : $CANON"
echo "  mode   : $([[ $dry -eq 1 ]] && echo DRY-RUN || echo COPY)"

# ── EWW (exclude restore points, backups, pycache) ───────────────────────
if [[ -d "${HOME}/.config/eww" ]]; then
  echo "── eww config + scripts + assets ───────────────────────────────"
  "${RSYNC[@]}" \
    --exclude='.restore-points/' \
    --exclude='*.bak' \
    --exclude='*.bak-*' \
    --exclude='__pycache__/' \
    "${HOME}/.config/eww/" "${CANON}/eww/"
fi

# ── Hyprland ─────────────────────────────────────────────────────────────
if [[ -d "${HOME}/.config/hypr" ]]; then
  echo "── hyprland.conf + conf.d shards ───────────────────────────────"
  for f in hyprland.conf hyprlock.conf hypridle.conf; do
    if [[ -f "${HOME}/.config/hypr/$f" ]]; then
      "${RSYNC[@]}" "${HOME}/.config/hypr/$f" "${CANON}/$f"
    fi
  done
  mkdir -p "${CANON}/hypr-walls"
  if [[ -d "${HOME}/.config/hypr/walls" ]]; then
    "${RSYNC[@]}" "${HOME}/.config/hypr/walls/" "${CANON}/hypr-walls/"
  fi
  for shard in "${HOME}/.config/hypr/conf.d/"*.conf; do
    [[ -f "$shard" ]] || continue
    base="$(basename "$shard")"
    "${RSYNC[@]}" "$shard" "${CANON}/$base"
  done
fi

# ── Theme consumers (palette mirror) ─────────────────────────────────────
for theme_dir in dunst rofi wlogout; do
  src="${HOME}/.config/${theme_dir}"
  case "$theme_dir" in
    dunst) dst_name=nyxus-dunstrc; src_file="${src}/dunstrc" ;;
    rofi)  continue ;;  # rofi handled below
    wlogout)
      [[ -f "${src}/style.css" ]] && "${RSYNC[@]}" "${src}/style.css" "${CANON}/wlogout-style.css"
      [[ -f "${src}/layout" ]]   && "${RSYNC[@]}" "${src}/layout"   "${CANON}/wlogout-layout"
      continue
      ;;
  esac
  [[ -f "$src_file" ]] && "${RSYNC[@]}" "$src_file" "${CANON}/$dst_name"
done
for rasi in config.rasi nyxus.rasi startmenu.rasi; do
  src="${HOME}/.config/rofi/$rasi"
  case "$rasi" in
    config.rasi)    dst=rofi-config.rasi ;;
    nyxus.rasi)     dst=rofi-nyxus.rasi ;;
    startmenu.rasi) dst=rofi-startmenu.rasi ;;
  esac
  [[ -f "$src" ]] && "${RSYNC[@]}" "$src" "${CANON}/$dst"
done
[[ -f "${HOME}/.config/alacritty/alacritty.toml" ]] && \
  "${RSYNC[@]}" "${HOME}/.config/alacritty/alacritty.toml" "${CANON}/alacritty.toml"

# ── ~/.nyxus Python apps + packages ──────────────────────────────────────
if [[ -d "${HOME}/.nyxus" ]]; then
  echo "── ~/.nyxus python apps ────────────────────────────────────────"
  for py in "${HOME}/.nyxus"/nyxus*.py "${HOME}/.nyxus"/nyxus-*.py; do
    [[ -f "$py" ]] || continue
    base="$(basename "$py")"
    "${RSYNC[@]}" "$py" "${CANON}/$base"
  done
  [[ -f "${HOME}/.nyxus/nyxus-palette.css" ]] && \
    "${RSYNC[@]}" "${HOME}/.nyxus/nyxus-palette.css" "${CANON}/nyxus-palette.css"

  # nyxus-home → artifacts/nyxus-home/src
  if [[ -d "${HOME}/.nyxus/nyxus-home" ]]; then
    mkdir -p "${REPO}/artifacts/nyxus-home/src"
    "${RSYNC[@]}" --exclude='__pycache__/' \
      "${HOME}/.nyxus/nyxus-home/" "${REPO}/artifacts/nyxus-home/src/"
  fi

  # nyxus-start + nyxus-panel → artifacts packages
  for pkg in nyxus-start nyxus-panel; do
    if [[ -d "${HOME}/.nyxus/$pkg" ]]; then
      mkdir -p "${CANON}/$pkg"
      "${RSYNC[@]}" --exclude='__pycache__/' \
        "${HOME}/.nyxus/$pkg/" "${CANON}/$pkg/"
    fi
  done
fi

# ── ~/.local/bin nyxus-* launchers ─────────────────────────────────────
if compgen -G "${HOME}/.local/bin/nyxus-*" >/dev/null; then
  echo "── ~/.local/bin nyxus-* launchers ─────────────────────────────"
  for bin in "${HOME}/.local/bin"/nyxus-*; do
    [[ -f "$bin" ]] || continue
    base="$(basename "$bin")"
    # Skip if already canonical in CANON with same name
    "${RSYNC[@]}" "$bin" "${CANON}/$base"
  done
fi

# ── nyxus config (stations, accent) ──────────────────────────────────────
if [[ -d "${HOME}/.config/nyxus" ]]; then
  echo "── nyxus config (stations, accent) ─────────────────────────────"
  mkdir -p "$NYXUS_CFG"
  for f in stations.json accent.json wallpaper.conf; do
    [[ -f "${HOME}/.config/nyxus/$f" ]] && \
      "${RSYNC[@]}" "${HOME}/.config/nyxus/$f" "${NYXUS_CFG}/$f"
  done
  # Accent baseline (eww.scss snapshot)
  baseline="${HOME}/.config/nyxus/accent-baseline/home/cosmic/.config/eww/eww.scss"
  if [[ -f "$baseline" ]]; then
    mkdir -p "${NYXUS_CFG}/accent-baseline/home/cosmic/.config/eww"
    "${RSYNC[@]}" "$baseline" "${NYXUS_CFG}/accent-baseline/home/cosmic/.config/eww/eww.scss"
  fi
fi

# ── systemd user units ───────────────────────────────────────────────────
for unit in nyxus-eww.service nyxus-crashd.service nyxus-security-daemon.service; do
  [[ -f "${HOME}/.config/systemd/user/$unit" ]] && \
    "${RSYNC[@]}" "${HOME}/.config/systemd/user/$unit" "${CANON}/$unit"
done

[[ $dry -eq 1 ]] && echo "── dry-run complete ──────────────────────────────────────────" && exit 0

# Ensure scripts are executable
find "${CANON}/eww/scripts" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' \) -exec chmod +x {} + 2>/dev/null || true
chmod +x "${CANON}"/nyxus-* 2>/dev/null || true

echo "── backport complete ───────────────────────────────────────────"
