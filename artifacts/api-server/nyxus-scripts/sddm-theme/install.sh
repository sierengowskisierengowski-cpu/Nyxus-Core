#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  NYXUS SDDM Theme Installer · COSMIC INK SWIRL · DARK GLASS LOGIN
#  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
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

# ── Background: rev r26c — STARFIELD LOGIN (pure black + 4-point starbursts).
# Priority order: nyxus-login-stars.png (current) → nyxus-ink-swirl.png
# (legacy local) → bundled background.png → network fetch of starfield.
if [[ -f "${SCRIPT_DIR}/../nyxus-login-stars.png" ]]; then
    echo "${C_DIM}→${C_RST} Using local NYXUS starfield (nyxus-login-stars.png)"
    cp "${SCRIPT_DIR}/../nyxus-login-stars.png" "${THEME_DIR}/background.png"
elif [[ -f "${SCRIPT_DIR}/../nyxus-ink-swirl.png" ]]; then
    echo "${C_DIM}→${C_RST} Using local cosmic ink swirl wallpaper (legacy)"
    cp "${SCRIPT_DIR}/../nyxus-ink-swirl.png" "${THEME_DIR}/background.png"
elif [[ -f "${SCRIPT_DIR}/background.png" ]]; then
    echo "${C_DIM}→${C_RST} Using bundled background.png"
elif command -v curl &>/dev/null; then
    echo "${C_WARN}→${C_RST} Downloading NYXUS starfield ..."
    curl -fsSL -o "${THEME_DIR}/background.png" \
        "${NYX_BASE}/nyxus-login-stars.png" \
        || echo "${C_WARN}⚠  Wallpaper download failed — drop a background.png in ${THEME_DIR}/${C_RST}"
fi

# ── Permissions
chmod 755 "${THEME_DIR}"
find "${THEME_DIR}" -type f -exec chmod 644 {} \;

# ── SDDM activation config
mkdir -p /etc/sddm.conf.d
cat > "${SDDM_CONF}" <<EOF
[Theme]
Current=${THEME_NAME}

[General]
DisplayServer=wayland
GreeterEnvironment=QT_WAYLAND_SHELL_INTEGRATION=layer-shell

[Wayland]
SessionDir=/usr/share/wayland-sessions
EOF
echo "${C_OK}✓${C_RST} Wrote ${SDDM_CONF}"

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
