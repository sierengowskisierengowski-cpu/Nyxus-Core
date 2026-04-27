#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║          NYXUS OS — Full System Installer                            ║
# ║  Downloads and deploys all NYXUS configs, scripts, and wallpapers    ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
#
# Usage:
#   curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_install.sh | bash

set -euo pipefail

# ── CONFIG ────────────────────────────────────────────────────────────────────
BASE_URL="${NYXUS_BASE_URL:-https://nyxus-core.replit.app}"
API="${BASE_URL}/api/download/nyxus"

SCRIPTS_DIR="$HOME/.nyxus"
HYPR_DIR="$HOME/.config/hypr"
WAYBAR_DIR="$HOME/.config/waybar"
ROFI_DIR="$HOME/.config/rofi"
MAKO_DIR="$HOME/.config/mako"

# ── COLORS ────────────────────────────────────────────────────────────────────
R="\033[0m"
B="\033[1m"
PURPLE="\033[38;5;135m"
PINK="\033[38;5;213m"
GOLD="\033[38;5;220m"
DIM="\033[2m"
GREEN="\033[92m"
RED="\033[91m"
CYAN="\033[96m"

ok()   { printf "  ${GREEN}${B}✓${R}  ${DIM}%s${R}\n" "$1"; }
fail() { printf "  ${RED}${B}✗${R}  ${DIM}%s — FAILED${R}\n" "$1"; }
hdr()  { printf "\n${PURPLE}${B}── %s ${DIM}%s${R}\n" "$1" "────────────────────────────────────────────"; }

dl() {
  local name="$1" dest="$2"
  if curl -fsSL -o "$dest" "${API}/${name}" 2>/dev/null; then
    ok "$name → $dest"
  else
    fail "$name"
    return 1
  fi
}

# ── HEADER ────────────────────────────────────────────────────────────────────
clear
echo ""
printf "${PURPLE}${B}  ███   ██  ██  ██  ██  ██  ██  █████ ${R}\n"
printf "${PINK}${B}  ████  ██   ████   ██  ██  ██  ██    ${R}\n"
printf "${GOLD}${B}  ██ █  ██    ██    ██  ██  ██   ████ ${R}\n"
printf "${PINK}${B}  ██  █ ██    ██     ████   ██      ██ ${R}\n"
printf "${PURPLE}${B}  ██   ████   ██      ██    ██  █████ ${R}\n"
echo ""
printf "  ${DIM}S I L E N T  ·  D A R K  ·  P U R E L Y   F U N C T I O N A L${R}\n"
printf "  ${DIM}© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED${R}\n"
echo ""

failed=0

# ── PYTHON TERMINAL SCRIPTS ───────────────────────────────────────────────────
hdr "Python Terminal Scripts"
mkdir -p "$SCRIPTS_DIR"
for f in nyxus_preboot.py nyxus_motd.py nyxus_splash.py nyxus_error.py; do
  dl "$f" "$SCRIPTS_DIR/$f" && chmod +x "$SCRIPTS_DIR/$f" || failed=$((failed+1))
done

# ── HYPRLAND CONFIGS ──────────────────────────────────────────────────────────
hdr "Hyprland"
mkdir -p "$HYPR_DIR"
dl "hyprland.conf" "$HYPR_DIR/hyprland.conf" || failed=$((failed+1))
dl "hyprlock.conf"  "$HYPR_DIR/hyprlock.conf"  || failed=$((failed+1))
dl "hypridle.conf"  "$HYPR_DIR/hypridle.conf"  || failed=$((failed+1))

# ── WALLPAPER ─────────────────────────────────────────────────────────────────
hdr "Wallpaper (SIERENGOWSKI)"
WALLS_DIR="$HYPR_DIR/walls"
mkdir -p "$WALLS_DIR"
dl "nyxus-sierengowski-clean.png" "$WALLS_DIR/nyxus-sierengowski-clean.png" || failed=$((failed+1))

# ── WAYBAR ────────────────────────────────────────────────────────────────────
hdr "Waybar"
mkdir -p "$WAYBAR_DIR"
dl "waybar-config.json"       "$WAYBAR_DIR/config"            || failed=$((failed+1))
dl "waybar-style.css"         "$WAYBAR_DIR/style.css"         || failed=$((failed+1))
# Inject real wallpaper path into CSS (replaces NYXUS_WALL_PATH placeholder)
WALL_PATH="$HOME/.config/hypr/walls/nyxus-sierengowski-clean.png"
sed -i "s|NYXUS_WALL_PATH|${WALL_PATH}|g" "$WAYBAR_DIR/style.css"
dl "waybar-ticker.sh"         "$WAYBAR_DIR/ticker.sh"         || failed=$((failed+1))
dl "waybar-stats.sh"          "$WAYBAR_DIR/stats.sh"          || failed=$((failed+1))
dl "nyxus_quicksettings.py"   "$WAYBAR_DIR/quicksettings.py"  || failed=$((failed+1))
chmod +x "$WAYBAR_DIR/ticker.sh" "$WAYBAR_DIR/stats.sh" "$WAYBAR_DIR/quicksettings.py" 2>/dev/null || true

# ── ROFI ─────────────────────────────────────────────────────────────────────
hdr "Rofi"
mkdir -p "$ROFI_DIR"
dl "rofi-config.rasi"    "$ROFI_DIR/config.rasi"     || failed=$((failed+1))
dl "rofi-nyxus.rasi"     "$ROFI_DIR/nyxus.rasi"      || failed=$((failed+1))
dl "rofi-startmenu.rasi" "$ROFI_DIR/startmenu.rasi"  || failed=$((failed+1))

# ── MAKO ─────────────────────────────────────────────────────────────────────
hdr "Mako Notifications"
mkdir -p "$MAKO_DIR"
dl "mako-config" "$MAKO_DIR/config" || failed=$((failed+1))

# ── ALACRITTY ────────────────────────────────────────────────────────────────
hdr "Alacritty"
mkdir -p "$HOME/.config/alacritty"
dl "alacritty.toml" "$HOME/.config/alacritty/alacritty.toml" || failed=$((failed+1))

# ── APPLY LIVE ───────────────────────────────────────────────────────────────
hdr "Applying Changes"

if command -v hyprctl &>/dev/null && [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  hyprctl reload &>/dev/null && ok "Hyprland config reloaded" || true
else
  printf "  ${DIM}Run ${PURPLE}hyprctl reload${DIM} to apply the new config${R}\n"
fi

if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  pkill waybar 2>/dev/null || true
  sleep 0.5
  waybar --config ~/.config/waybar/config --style ~/.config/waybar/style.css &>/dev/null &
  disown
  ok "Waybar restarted — 4-bar NYXUS layout active"
fi

if [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  pkill swaybg 2>/dev/null || true
  swaybg -i "$WALLS_DIR/nyxus-sierengowski-clean.png" -m fill &
  disown
  ok "Wallpaper set — nyxus-sierengowski-clean"
fi

if command -v makoctl &>/dev/null && [[ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]]; then
  makoctl reload 2>/dev/null && ok "Mako reloaded" || true
fi

# ── SUMMARY ───────────────────────────────────────────────────────────────────
echo ""
printf "${DIM}──────────────────────────────────────────────────────────────────────${R}\n"
echo ""

if [[ $failed -eq 0 ]]; then
  printf "  ${GREEN}${B}NYXUS fully installed.${R}\n\n"
  printf "  ${GOLD}Wallpaper:${R} SIERENGOWSKI (permanent — set at boot)\n"
  printf "    ${DIM}Super+Alt+W  → reload wallpaper if it ever clears${R}\n\n"
  printf "  ${PURPLE}${B}Lock your screen:${R}  ${DIM}Super+L${R}\n"
  printf "  ${PURPLE}${B}Open launcher:${R}    ${DIM}Super+D${R}\n"
  printf "  ${PURPLE}${B}Screenshot:${R}       ${DIM}Super+Print  (region)${R}\n"
  printf "  ${PURPLE}${B}Logout menu:${R}      ${DIM}Super+Shift+E${R}\n\n"
  printf "  ${DIM}S I L E N T · D A R K · P U R E L Y   F U N C T I O N A L${R}\n"
else
  printf "  ${RED}${B}${failed} item(s) failed.${R}\n"
  printf "  ${DIM}Check your connection and re-run.${R}\n"
  exit 1
fi

echo ""
