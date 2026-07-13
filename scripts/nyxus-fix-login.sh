#!/usr/bin/env bash
# NYXUS — fix SDDM → Hyprland login handoff (needs sudo once)
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"
REAL_USER="${SUDO_USER:-${USER}}"
REAL_HOME="$(getent passwd "${REAL_USER}" | cut -d: -f6)"

if [[ $EUID -ne 0 ]]; then
  echo "elevating with sudo …"
  exec sudo bash "$0" "$@"
fi

echo "▌ fixing SDDM login chain for user ${REAL_USER}"

# 1. SDDM Wayland greeter fails on this hardware (HELPER_DISPLAYSERVER_ERROR).
#    Force the reliable X11 greeter — Hyprland session is still pure Wayland.
SDDM_DROPIN="/etc/sddm.conf.d/10-nyxus-login.conf"
cat > "${SDDM_DROPIN}" <<'SDDM'
# NYXUS — login fix (rev 2026-07-13)
# SDDM's Wayland greeter fails on hybrid NVIDIA hardware; X11 greeter is
# the only reliable path. The user's Hyprland session is still Wayland.
[General]
DisplayServer=x11
DefaultSession=nyxus-hyprland.desktop
Numlock=on

[Theme]
Current=nyxus

[Users]
RememberLastSession=true
RememberLastUser=true
SDDM

# Remove the broken Wayland override if an older bake left it behind.
if [[ -f /etc/sddm.conf.d/nyxus.conf ]]; then
  sed -i '/^DisplayServer=wayland/d' /etc/sddm.conf.d/nyxus.conf
fi

# 2. System-wide session entry (picked up by SDDM session picker).
install -Dm644 "${NS}/desktop-entries/nyxus-hyprland.desktop" \
  /usr/share/wayland-sessions/nyxus-hyprland.desktop
install -Dm755 "${NS}/nyxus-session-start" /usr/local/bin/nyxus-session-start

# 3. User-level session entry (wins over system if SDDM reads both).
USER_SESS="${REAL_HOME}/.local/share/wayland-sessions"
install -d -m 0755 -o "${REAL_USER}" -g "$(id -gn "${REAL_USER}")" "${USER_SESS}"
install -Dm644 -o "${REAL_USER}" -g "$(id -gn "${REAL_USER}")" \
  "${NS}/desktop-entries/nyxus-hyprland.desktop" \
  "${USER_SESS}/nyxus-hyprland.desktop"
install -Dm755 "${NS}/nyxus-session-start" \
  "${REAL_HOME}/.local/bin/nyxus-session-start"
chown "${REAL_USER}:$(id -gn "${REAL_USER}")" \
  "${REAL_HOME}/.local/bin/nyxus-session-start"

echo "  ✓ SDDM drop-in → ${SDDM_DROPIN}"
echo "  ✓ session → nyxus-hyprland.desktop + nyxus-session-start"
echo ""
echo "Done. Log out and pick 'NYXUS (Hyprland)' at the login screen."
