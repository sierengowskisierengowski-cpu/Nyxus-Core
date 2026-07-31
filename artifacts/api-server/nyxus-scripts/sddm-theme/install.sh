#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  NYXUS SDDM Theme Installer · COSMIC INK SWIRL · DARK GLASS LOGIN
#  © 2026 Joseph A. Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

THEME_NAME="nyxus"
THEME_DIR="/usr/share/sddm/themes/${THEME_NAME}"
SDDM_CONF="/etc/sddm.conf.d/nyxus.conf"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NYX_BASE="${NYX_BASE:-https://nyxus-core.replit.app/api/download/nyxus}"

C_RST=$'\033[0m'; C_BOLD=$'\033[1m'
C_DIM=$'\033[2m'; C_OK=$'\033[0;32m'
C_WARN=$'\033[0;33m'; C_ERR=$'\033[0;31m'
C_GOLD=$'\033[38;5;179m'

cat <<EOF

${C_BOLD}${C_GOLD}     N Y X U S${C_RST}
${C_DIM}     SIERENGOWSKI · 2026${C_RST}
${C_DIM}     SDDM · DARK GLASS LOGIN · v3.0${C_RST}

EOF

if [[ $EUID -ne 0 ]]; then
    echo "${C_ERR}✗ Run as root: sudo bash install.sh${C_RST}"
    exit 1
fi

echo "${C_DIM}→${C_RST} Installing theme to ${THEME_DIR} ..."
mkdir -p "${THEME_DIR}"
cp -r "${SCRIPT_DIR}/." "${THEME_DIR}/"
rm -f "${THEME_DIR}/install.sh"

# ── Background: rev r27 — URBAN ALIEN LOGIN (2026-07-26).
# The owner's chosen look for every login/lock surface is the urban-alien
# graffiti art, so the login wall now WINS this chain. The starfield used to
# win, which is why a reinstall kept reverting the login screen away from the
# rest of the theme. Priority: nyxus-login-wall.png (urban alien, matches
# hyprlock) → nyxus-urban-alien.png → bundled background.png → network fetch.
# The nyxus-login-stars.png (starfield) rungs were removed 2026-07-30 when that
# image was dropped for being a monochrome galaxy with no subject; a fallback
# rung naming a deleted file is a rung that silently does nothing.
# Scaled to 1920x1080 cover so the panel never letterboxes.
_nyx_set_bg() {
    if command -v magick &>/dev/null; then
        magick "$1" -resize 1920x1080^ -gravity center -extent 1920x1080 \
            "${THEME_DIR}/background.png"
    else
        cp "$1" "${THEME_DIR}/background.png"
    fi
}
if [[ -f "${SCRIPT_DIR}/../nyxus-login-wall.png" ]]; then
    echo "${C_DIM}→${C_RST} Using NYXUS urban-alien login wall"
    _nyx_set_bg "${SCRIPT_DIR}/../nyxus-login-wall.png"
elif [[ -f "${SCRIPT_DIR}/../nyxus-urban-alien.png" ]]; then
    echo "${C_DIM}→${C_RST} Using NYXUS urban-alien hero"
    _nyx_set_bg "${SCRIPT_DIR}/../nyxus-urban-alien.png"
elif [[ -f "${SCRIPT_DIR}/background.png" ]]; then
    echo "${C_DIM}→${C_RST} Using bundled background.png"
elif command -v curl &>/dev/null; then
    echo "${C_WARN}→${C_RST} Downloading NYXUS urban-alien wall ..."
    curl -fsSL -o "${THEME_DIR}/background.png" \
        "${NYX_BASE}/nyxus-urban-alien.png" \
        || echo "${C_WARN}⚠  Wallpaper download failed — drop a background.png in ${THEME_DIR}/${C_RST}"
fi

# ── Permissions
chmod 755 "${THEME_DIR}"
find "${THEME_DIR}" -type f -exec chmod 644 {} \;

# ── SDDM activation config
# THEME SELECTION ONLY. Do NOT write [General] here: this file sorts AFTER
# 10-nyxus.conf, so anything set here wins, and both keys we used to write
# broke the greeter outright (2026-07-26 "no login screen"):
#   DisplayServer=wayland  -> sddm looks for a wayland greeter compositor
#     (weston) that is not installed -> HELPER_DISPLAYSERVER_ERROR, exit 4,
#     then a fallback to x11-user.
#   GreeterEnvironment=... -> REPLACES the whole var, dropping
#     QT_QUICK_BACKEND=software, which the hybrid-GPU laptop requires ->
#     the x11 fallback greeter then SIGSEGVs (exit 11) and nothing renders.
# DisplayServer / GreeterEnvironment belong to 10-nyxus.conf. Leave them there.
mkdir -p /etc/sddm.conf.d
cat > "${SDDM_CONF}" <<EOF
[Theme]
Current=${THEME_NAME}
EOF
echo "${C_OK}✓${C_RST} Wrote ${SDDM_CONF} (theme only)"

# ── Ensure SDDM is enabled
if command -v systemctl &>/dev/null; then
    systemctl enable sddm.service >/dev/null 2>&1 || true
    echo "${C_OK}✓${C_RST} sddm.service enabled"
fi

cat <<EOF

${C_OK}${C_BOLD}✓ NYXUS SDDM theme installed${C_RST}

  ${C_DIM}Restart SDDM:${C_RST}  sudo systemctl restart sddm
  ${C_DIM}Preview:${C_RST}       sddm-greeter --test --theme ${THEME_DIR}

${C_GOLD}NYX-J5W-2026-SIERENGOWSKI-LOCKED${C_RST}

EOF
