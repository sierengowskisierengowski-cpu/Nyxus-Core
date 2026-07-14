#!/usr/bin/env bash
# NYXUS — Phase 2: rebuild the SDDM greeter + fix the hybrid-GPU blank screen.
# Run once with sudo:  sudo nyxus-fix-login   (or: bash scripts/nyxus-fix-login.sh)
#
# Root cause this fixes: on hybrid Intel+NVIDIA (MSI GS77) the SDDM greeter
# SIGSEGVs in hardware GL/EGL → blank screen + cursor, no login, forcing a
# TTY + manual Hyprland. The greeter QML/theme is fine (renders offscreen);
# the crash is the GPU render path. QT_QUICK_BACKEND=software renders the
# greeter via llvmpipe and sidesteps the GPU entirely. Login sessions
# (Hyprland/COSMIC) still use the full GPU under Wayland — unaffected.
#
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NS="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"
THEME_SRC="${NS}/sddm-theme"
THEME_DIR="/usr/share/sddm/themes/nyxus"
REAL_USER="${SUDO_USER:-${USER}}"
REAL_HOME="$(getent passwd "${REAL_USER}" | cut -d: -f6)"

if [[ $EUID -ne 0 ]]; then
  echo "elevating with sudo …"
  exec sudo -E bash "$0" "$@"
fi

echo "▌ NYXUS Phase 2 — SDDM greeter rebuild for ${REAL_USER}"

# 1. Single source-of-truth SDDM drop-in. Remove older conflicting ones
#    (10-nyxus-login.conf set X11 but no software backend; nyxus.conf set a
#    contradictory Wayland layer-shell env).
rm -f /etc/sddm.conf.d/nyxus.conf /etc/sddm.conf.d/10-nyxus-login.conf
mkdir -p /etc/sddm.conf.d
cat > /etc/sddm.conf.d/10-nyxus.conf <<EOF
# NYXUS — login (rev 2026-07-14 · Phase 2 rebuild)
# QT_QUICK_BACKEND=software is the fix for the hybrid-GPU greeter SIGSEGV
# (blank screen + cursor). Do not remove it on this hardware.
[General]
DisplayServer=x11
Numlock=on
GreeterEnvironment=QT_QUICK_BACKEND=software,QT_XCB_GL_INTEGRATION=none

[Theme]
Current=nyxus

[Users]
RememberLastUser=true
RememberLastSession=true

[Wayland]
SessionDir=/usr/share/wayland-sessions,${REAL_HOME}/.local/share/wayland-sessions

[X11]
SessionDir=/usr/share/xsessions
EOF
echo "  ✓ /etc/sddm.conf.d/10-nyxus.conf (software-render greeter, X11)"

# 2. Deploy the rebuilt theme (pure-QtQuick, Nyxus black + purple/magenta).
mkdir -p "${THEME_DIR}"
rsync -a --delete --exclude='install.sh' "${THEME_SRC}/" "${THEME_DIR}/"
chmod 755 "${THEME_DIR}"
find "${THEME_DIR}" -type f -exec chmod 644 {} \;
echo "  ✓ theme → ${THEME_DIR}"

# 3. The greeter runs as user 'sddm' and cannot read ${REAL_HOME}. Install
#    the Nyxus fonts system-wide so the greeter can render them.
if [[ -d "${REAL_HOME}/.local/share/fonts/nyxus" ]]; then
  install -d -m0755 /usr/share/fonts/nyxus
  install -m0644 "${REAL_HOME}/.local/share/fonts/nyxus/"*.ttf \
    /usr/share/fonts/nyxus/ 2>/dev/null || true
  fc-cache -f >/dev/null 2>&1 || true
  echo "  ✓ Nyxus fonts installed system-wide for the greeter"
fi

# 4. Session entries: install NYXUS (Hyprland) + starter; remove the old
#    bare Hyprland entries the brief says must not exist as options.
#    COSMIC stays (cosmic.desktop) as a selectable session.
install -Dm755 "${NS}/nyxus-session-start" /usr/local/bin/nyxus-session-start
install -Dm644 "${NS}/desktop-entries/nyxus-hyprland.desktop" \
  /usr/share/wayland-sessions/nyxus-hyprland.desktop
rm -f /usr/share/wayland-sessions/hyprland.desktop \
      /usr/share/wayland-sessions/hyprland-uwsm.desktop
echo "  ✓ sessions: NYXUS (Hyprland) + COSMIC; removed stock hyprland*.desktop"

# 5. SDDM is the display manager. Keep greetd/cosmic-greeter installed but
#    inactive so nothing fights over display-manager.service.
systemctl disable greetd.service          >/dev/null 2>&1 || true
systemctl disable cosmic-greeter.service  >/dev/null 2>&1 || true
systemctl enable  sddm.service            >/dev/null 2>&1 || true
echo "  ✓ sddm enabled as display-manager; greetd/cosmic-greeter disabled"

cat <<EOF

── done. TEST WITHOUT REBOOTING FIRST ────────────────────────────────
Preview the greeter render right now, inside your Hyprland session:

    QT_QUICK_BACKEND=software sddm-greeter --test-mode --theme ${THEME_DIR}

A themed NYXUS login window should appear (black + purple/magenta, clock,
username/passphrase, session pills for NYXUS + COSMIC). Close with Esc.

If it renders, take it live with a real reboot (the true test):

    sudo systemctl reboot

At the greeter: confirm it appears (no blank screen), pick NYXUS (Hyprland)
or COSMIC, and log in without any TTY workaround.
───────────────────────────────────────────────────────────────────────
EOF
