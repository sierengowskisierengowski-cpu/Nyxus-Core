#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  NYXUS SDDM Theme Installer
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

THEME_NAME="nyxus"
THEME_DIR="/usr/share/sddm/themes/${THEME_NAME}"
SDDM_CONF="/etc/sddm.conf.d/nyxus.conf"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

RED='\033[0;31m'; GREEN='\033[0;32m'; PURPLE='\033[0;35m'
ORANGE='\033[0;33m'; RESET='\033[0m'; BOLD='\033[1m'

echo -e "${PURPLE}"
cat << 'EOF'
 _   ___   ____  ____  _   _ ____
| \ | \ \ / /\ \/ /  | | | / ___|
|  \| |\ V /  \  /| | | | \___ \
| |\  | | |   /  \| |_| |_| |___) |
|_| \_| |_|  /_/\_\\___/ \___/
  SDDM THEME INSTALLER  v2.0
EOF
echo -e "${RESET}"

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}✗ Run as root: sudo bash install.sh${RESET}"
    exit 1
fi

echo -e "${PURPLE}→${RESET} Installing NYXUS SDDM theme to ${THEME_DIR} ..."
mkdir -p "${THEME_DIR}"
cp -r "${SCRIPT_DIR}/." "${THEME_DIR}/"
rm -f "${THEME_DIR}/install.sh"

# Use the best available wallpaper as background
if [[ -f "${SCRIPT_DIR}/background.png" ]]; then
    cp "${SCRIPT_DIR}/background.png" "${THEME_DIR}/background.png"
elif command -v curl &>/dev/null; then
    echo -e "${ORANGE}→${RESET} Downloading NYXUS wallpaper ..."
    curl -fsSL -o "${THEME_DIR}/background.png" \
        "https://jsierengowski-workspace.replit.app/api/download/nyxus/nyxus-wallpaper.png" \
        || echo -e "${ORANGE}⚠  Wallpaper download failed — add background.png manually${RESET}"
fi

# Set permissions
chmod 755 "${THEME_DIR}"
find "${THEME_DIR}" -type f -exec chmod 644 {} \;

# Write SDDM config
mkdir -p /etc/sddm.conf.d
cat > "${SDDM_CONF}" << EOF
[Theme]
Current=${THEME_NAME}
EOF
echo -e "${GREEN}✓${RESET} SDDM config written: ${SDDM_CONF}"

# Optional: set Wayland/Hyprland backend
if command -v hyprctl &>/dev/null; then
    if ! grep -q "DisplayServer" "${SDDM_CONF}" 2>/dev/null; then
        cat >> "${SDDM_CONF}" << 'EOF'

[General]
DisplayServer=wayland
GreeterEnvironment=QT_WAYLAND_SHELL_INTEGRATION=layer-shell
EOF
        echo -e "${GREEN}✓${RESET} Hyprland/Wayland display server configured"
    fi
fi

echo ""
echo -e "${GREEN}${BOLD}✓ NYXUS SDDM theme installed successfully${RESET}"
echo -e "  ${PURPLE}Restart SDDM:${RESET}  sudo systemctl restart sddm"
echo -e "  ${PURPLE}Preview:${RESET}       sddm-greeter --test-mode --theme ${THEME_DIR}"
echo ""
echo -e "${PURPLE}NYX-J5W-2026-SIERENGOWSKI-LOCKED${RESET}"
