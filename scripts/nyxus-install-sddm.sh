#!/usr/bin/env bash
# NYXUS · install SDDM login with session picker (COSMIC · Hyprland · NYXUS).
# NOTE: This DISABLES cosmic-greeter. On this machine, cosmic-greeter is the
# preferred stable login. Use `sudo nyxus-restore-login` to switch back.
set -euo pipefail

if [[ $EUID -ne 0 ]]; then
  echo "Run: sudo nyxus-install-sddm" >&2
  exit 1
fi

if systemctl is-enabled cosmic-greeter.service >/dev/null 2>&1; then
  echo "⚠  cosmic-greeter is currently your login manager."
  echo "   Installing SDDM will replace it. To keep Cosmic login, use:"
  echo "   sudo nyxus-restore-login"
  echo ""
fi

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="${REPO}/artifacts/api-server/nyxus-scripts/sddm-theme"
THEME_DIR="/usr/share/sddm/themes/nyxus"
# Was nyxus-login-stars.png until 2026-07-30; that starfield was dropped, and
# copying a nonexistent file left SDDM on whatever background.png happened to
# be in the theme dir.
WALL="${REPO}/artifacts/api-server/nyxus-scripts/nyxus-urban-alien.png"

mkdir -p "${THEME_DIR}" /etc/sddm.conf.d
rsync -a --exclude='install.sh' "${SRC}/" "${THEME_DIR}/"
[[ -f "$WALL" ]] && cp "$WALL" "${THEME_DIR}/background.png"
chmod 755 "${THEME_DIR}"
find "${THEME_DIR}" -type f -exec chmod 644 {} \;

TARGET_USER="${SUDO_USER:-${USER}}"
USER_HOME="$(getent passwd "$TARGET_USER" | cut -d: -f6)"

cat > /etc/sddm.conf.d/10-nyxus-login.conf <<EOF
# NYXUS login — X11 greeter (reliable on MSI GS77 hybrid NVIDIA)
# QT_QUICK_BACKEND=software: greeter SIGSEGVs in hardware GL on this
# hybrid Intel+NVIDIA GPU (blank screen). Software render sidesteps it.
[General]
DisplayServer=x11
Numlock=on
GreeterEnvironment=QT_QUICK_BACKEND=software,QT_XCB_GL_INTEGRATION=none

[Theme]
Current=nyxus

[Users]
RememberLastUser=true
RememberLastSession=false

[Wayland]
SessionDir=/usr/share/wayland-sessions,${USER_HOME}/.local/share/wayland-sessions
EOF

cat > /etc/sddm.conf.d/nyxus.conf <<'EOF'
[Theme]
Current=nyxus
EOF

# Clear labels for session picker
if [[ -f /usr/share/wayland-sessions/hyprland.desktop ]]; then
  sed -i 's/^Name=.*/Name=Hyprland/' /usr/share/wayland-sessions/hyprland.desktop 2>/dev/null || true
fi

systemctl enable sddm.service >/dev/null 2>&1 || true
echo "✓ NYXUS SDDM installed — sessions: COSMIC, Hyprland, NYXUS (Hyprland)"
echo "  Restart greeter: sudo systemctl restart sddm"
