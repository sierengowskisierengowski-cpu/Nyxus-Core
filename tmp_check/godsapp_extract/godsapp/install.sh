#!/usr/bin/env bash
# ============================================================================
# NYXUS GodsApp — installer
# © 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#   sudo bash install.sh
# ============================================================================
set -euo pipefail
if [[ $EUID -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    echo "[NYXUS GodsApp] elevating with sudo …"
    exec sudo -E bash "$0" "$@"
  fi
  echo "ERROR: must be run as root (sudo not available)" >&2; exit 1
fi

INSTALL_DIR="/opt/nyxus-godsapp"
ICON_SYS="/usr/share/icons/hicolor/scalable/apps/nyxus.svg"
BIN_LINK="/usr/local/bin/nyxus-godsapp"
DESKTOP_FILE="/usr/share/applications/nyxus-godsapp.desktop"
HERE="$(cd "$(dirname "$0")" && pwd)"

echo "──────────────────────────────────────────────────────────────"
echo "  NYXUS GodsApp · install"
echo "──────────────────────────────────────────────────────────────"

echo "[1/8] system packages …"
if [[ -f "$HERE/packages.txt" ]]; then
  if command -v pacman >/dev/null 2>&1; then
    pacman -Sy --needed --noconfirm $(grep -v '^#' "$HERE/packages.txt" | grep -v '^$' | tr '\n' ' ') || true
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get update
    apt-get install -y $(grep -v '^#' "$HERE/packages.txt" | grep -v '^$' | tr '\n' ' ') || true
  fi
fi

echo "[2/8] python deps …"
python3 -m pip install --break-system-packages --quiet \
    -r "$HERE/requirements.txt" 2>/dev/null || \
python3 -m pip install --quiet -r "$HERE/requirements.txt" || true

echo "[3/8] install app …"
mkdir -p "$INSTALL_DIR/modules"
install -m 0755 "$HERE/main.py"        "$INSTALL_DIR/main.py"
install -m 0644 "$HERE/ui.py"          "$INSTALL_DIR/ui.py"
install -m 0644 "$HERE/screensaver.py" "$INSTALL_DIR/screensaver.py"
install -m 0644 "$HERE/db.py"          "$INSTALL_DIR/db.py"
install -m 0644 "$HERE/scheduler.py"   "$INSTALL_DIR/scheduler.py"
install -m 0644 "$HERE/api.py"         "$INSTALL_DIR/api.py"
install -m 0644 "$HERE/modules/"*.py   "$INSTALL_DIR/modules/"
touch "$INSTALL_DIR/modules/__init__.py"

echo "[4/8] unified app icon …"
if [[ -f "$HERE/icon.svg" ]]; then
  install -D -m 0644 "$HERE/icon.svg" "$ICON_SYS"
  install -D -m 0644 "$HERE/icon.svg" "$INSTALL_DIR/icon.svg"
  if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor 2>/dev/null || true
  fi
fi

echo "[5/8] handwritten fonts (Caveat) …"
# the UI ships its own @import for Caveat via CSS; this step is now optional.
# users with no internet during first launch can install Caveat from packages:
if command -v pacman >/dev/null 2>&1; then
  pacman -S --needed --noconfirm ttf-caveat 2>/dev/null || true
elif command -v apt-get >/dev/null 2>&1; then
  apt-get install -y fonts-caveat 2>/dev/null || true
fi

echo "[6/8] udev rules for hardware access …"
if [[ -f "$HERE/udev.rules" ]]; then
  install -m 0644 "$HERE/udev.rules" /etc/udev/rules.d/99-nyxus-godsapp.rules
  udevadm control --reload-rules || true
  udevadm trigger || true
fi

echo "[7/8] launchers + .desktop …"
ln -sf "$INSTALL_DIR/main.py" "$BIN_LINK"
chmod +x "$BIN_LINK"
cat > "$DESKTOP_FILE" <<'DESK'
[Desktop Entry]
Type=Application
Name=NYXUS GodsApp
Comment=Professional security auditing & research suite
Exec=python3 /opt/nyxus-godsapp/main.py
Icon=io.nyxus.godsapp
Terminal=false
Categories=System;Security;Network;
StartupNotify=true
DESK
update-desktop-database /usr/share/applications 2>/dev/null || true

echo "[8/8] done."
echo
echo "  launch with:  nyxus-godsapp"
echo "  legal:        cat $INSTALL_DIR/LEGAL.md"
echo "  modules dir:  $INSTALL_DIR/modules"
echo "  idle saver:   appears after 2 min idle — any key/click wakes it"
