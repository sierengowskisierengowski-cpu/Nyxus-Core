#!/usr/bin/env bash
# NYXUS · restore Cosmic greeter login with session picker (COSMIC · Hyprland · NYXUS).
# Run once with sudo when SDDM replaced your Cosmic login screen or sessions fail.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"
REAL_USER="${SUDO_USER:-${USER}}"
REAL_HOME="$(getent passwd "${REAL_USER}" | cut -d: -f6)"

if [[ $EUID -ne 0 ]]; then
  echo "Run: sudo nyxus-restore-login" >&2
  exit 1
fi

echo "▌ restoring Cosmic greeter login for ${REAL_USER}"

# 1. Cosmic greeter is the stable dual-session picker on this machine.
systemctl disable sddm.service 2>/dev/null || true
systemctl stop sddm.service 2>/dev/null || true
systemctl enable cosmic-greeter.service
systemctl restart cosmic-greeter.service

# 2. Session entries — Cosmic greeter reads /usr/share/wayland-sessions/.
install -Dm644 "${NS}/desktop-entries/nyxus-hyprland.desktop" \
  /usr/share/wayland-sessions/nyxus-hyprland.desktop
install -Dm755 "${NS}/nyxus-session-start" /usr/local/bin/nyxus-session-start

USER_SESS="${REAL_HOME}/.local/share/wayland-sessions"
install -d -m 0755 -o "${REAL_USER}" -g "$(id -gn "${REAL_USER}")" "${USER_SESS}"
install -Dm644 -o "${REAL_USER}" -g "$(id -gn "${REAL_USER}")" \
  "${NS}/desktop-entries/nyxus-hyprland.desktop" \
  "${USER_SESS}/nyxus-hyprland.desktop"
install -Dm755 -o "${REAL_USER}" -g "$(id -gn "${REAL_USER}")" \
  "${NS}/nyxus-session-start" "${REAL_HOME}/.local/bin/nyxus-session-start"

if [[ -f /usr/share/wayland-sessions/hyprland.desktop ]]; then
  sed -i 's/^Name=.*/Name=Hyprland/' /usr/share/wayland-sessions/hyprland.desktop 2>/dev/null || true
fi

# 3. Recovery scripts on PATH for SDDM/greeter-launched sessions (no ~/.local/bin dependency).
for script in nyxus-persist-login nyxus-boot-check nyxus-overlay-unstick \
              nyxus-restore-session nyxus-eww-launch-safe; do
  src="${REPO_ROOT}/scripts/${script}.sh"
  [[ -f "$src" ]] && install -Dm755 "$src" "/usr/local/bin/${script}"
done
install -Dm755 "${NS}/nyxus-session-start" /usr/local/bin/nyxus-session-start

# 4. Keep SDDM config sane if user switches back later (X11 greeter, session picker).
mkdir -p /etc/sddm.conf.d
cat > /etc/sddm.conf.d/10-nyxus-login.conf <<'SDDM'
# NYXUS — SDDM fallback (cosmic-greeter is primary on this machine)
[General]
DisplayServer=x11
DefaultSession=nyxus-hyprland.desktop
Numlock=on

[Theme]
Current=nyxus

[Users]
RememberLastSession=true
RememberLastUser=true

[Wayland]
SessionDir=/usr/share/wayland-sessions
SDDM

echo "  ✓ cosmic-greeter enabled (display-manager.service)"
echo "  ✓ sessions: COSMIC · Hyprland · NYXUS (Hyprland)"
echo ""
echo "Reboot or log out — you should see the Cosmic login screen with a session picker."
echo "Pick NYXUS (Hyprland) for your themed build, or COSMIC for your main desktop."
