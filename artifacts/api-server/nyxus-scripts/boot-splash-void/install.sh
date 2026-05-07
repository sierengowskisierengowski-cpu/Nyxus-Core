#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  NYXUS VOID · Boot Splash Installer · Premium reveal · v2.0
#  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ─────────────────────────────────────────────────────────────────────────────
#
#  USAGE — installed system (real hardware):
#      sudo bash install.sh
#
#  USAGE — archiso profile (during ISO bake):
#      sudo NYX_PROFILE_ROOT=/path/to/nyx-profile bash install.sh --iso
#
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_NAME="nyxus-void"
MODE="${1:-system}"

C_RST=$'\033[0m'; C_DIM=$'\033[2m'; C_BOLD=$'\033[1m'
C_OK=$'\033[0;32m'; C_WARN=$'\033[0;33m'; C_ERR=$'\033[0;31m'
C_GOLD=$'\033[38;5;179m'; C_WHITE=$'\033[38;5;255m'

cat <<EOF

${C_WHITE}${C_BOLD}     N Y X U S    V O I D${C_RST}
${C_DIM}     ─────────────────────────${C_RST}
${C_DIM}     Premium boot splash · v2.0${C_RST}

EOF

if [[ $EUID -ne 0 ]]; then
    echo "${C_ERR}✗ Run as root: sudo bash install.sh${C_RST}"
    exit 1
fi

# ═════════════════════════════════════════════════════════════════════════════
# MODE: --iso  (mutate an archiso profile)
# ═════════════════════════════════════════════════════════════════════════════
if [[ "$MODE" == "--iso" ]]; then
    : "${NYX_PROFILE_ROOT:?Set NYX_PROFILE_ROOT to the nyx-profile/ directory}"
    PROFILE="${NYX_PROFILE_ROOT}"
    AIROOT="${PROFILE}/airootfs"

    install -d "${AIROOT}/usr/share/plymouth/themes/${THEME_NAME}"
    install -m 0644 "${SCRIPT_DIR}/plymouth/${THEME_NAME}/"* \
        "${AIROOT}/usr/share/plymouth/themes/${THEME_NAME}/"
    echo "${C_OK}✓${C_RST} Theme staged → /usr/share/plymouth/themes/${THEME_NAME}/"

    PKGS="${PROFILE}/packages.x86_64"
    if ! grep -qE '^plymouth$' "${PKGS}"; then
        echo "plymouth" >> "${PKGS}"
        echo "${C_OK}✓${C_RST} Added 'plymouth' to packages.x86_64"
    fi

    MKICONF="${AIROOT}/etc/mkinitcpio.conf.d/archiso.conf"
    [[ -f "${MKICONF}" ]] || MKICONF="${AIROOT}/etc/mkinitcpio.conf"
    if [[ -f "${MKICONF}" ]] && ! grep -qE 'HOOKS=.*plymouth' "${MKICONF}"; then
        sed -i -E 's/^(HOOKS=\([^)]*udev)([^)]*)\)/\1 plymouth\2)/' "${MKICONF}"
        echo "${C_OK}✓${C_RST} Inserted 'plymouth' hook in ${MKICONF}"
    fi

    install -d "${AIROOT}/etc/plymouth"
    cat > "${AIROOT}/etc/plymouth/plymouthd.conf" <<EOF
[Daemon]
Theme=${THEME_NAME}
ShowDelay=0
DeviceTimeout=8
EOF
    echo "${C_OK}✓${C_RST} Wrote /etc/plymouth/plymouthd.conf (Theme=${THEME_NAME})"

    cat <<EOF

${C_OK}${C_BOLD}✓ ISO profile patched${C_RST}
  Build the ISO:  ${C_DIM}sudo mkarchiso -v -w /tmp/archiso-work -o ./out ${PROFILE}${C_RST}

${C_GOLD}NYX-J5W-2026-SIERENGOWSKI-LOCKED${C_RST}

EOF
    exit 0
fi

# ═════════════════════════════════════════════════════════════════════════════
# MODE: system  (install onto running NYXUS box)
# ═════════════════════════════════════════════════════════════════════════════
if ! command -v plymouth-set-default-theme &>/dev/null; then
    echo "${C_WARN}→${C_RST} plymouth not installed — installing ..."
    if command -v pacman &>/dev/null; then
        pacman -Sy --noconfirm plymouth
    else
        echo "${C_ERR}✗ Need plymouth + pacman. Install plymouth manually then re-run.${C_RST}"
        exit 1
    fi
fi

PLY_DIR="/usr/share/plymouth/themes/${THEME_NAME}"
echo "${C_DIM}→${C_RST} Installing theme → ${PLY_DIR}"
install -d "${PLY_DIR}"
install -m 0644 "${SCRIPT_DIR}/plymouth/${THEME_NAME}/"* "${PLY_DIR}/"

# Activate (rebuilds initramfs)
plymouth-set-default-theme -R "${THEME_NAME}" >/dev/null 2>&1 \
    && echo "${C_OK}✓${C_RST} Default theme = ${THEME_NAME} (initramfs rebuilt)" \
    || { echo "${C_WARN}⚠ -R failed, doing it manually${C_RST}"
         plymouth-set-default-theme "${THEME_NAME}"
         mkinitcpio -P; }

# quiet splash on kernel cmdline
DEFAULT_GRUB="/etc/default/grub"
if [[ -f "${DEFAULT_GRUB}" ]] \
   && ! grep -qE 'GRUB_CMDLINE_LINUX_DEFAULT=.*splash' "${DEFAULT_GRUB}"; then
    sed -i 's/^\(GRUB_CMDLINE_LINUX_DEFAULT="\)/\1quiet splash /' "${DEFAULT_GRUB}"
    command -v grub-mkconfig &>/dev/null \
        && grub-mkconfig -o /boot/grub/grub.cfg \
        || true
    echo "${C_OK}✓${C_RST} Added 'quiet splash' to GRUB_CMDLINE_LINUX_DEFAULT"
fi

install -d /etc/plymouth
cat > /etc/plymouth/plymouthd.conf <<EOF
[Daemon]
Theme=${THEME_NAME}
ShowDelay=0
DeviceTimeout=8
EOF
echo "${C_OK}✓${C_RST} /etc/plymouth/plymouthd.conf written"

cat <<EOF

${C_OK}${C_BOLD}✓ NYXUS VOID boot splash installed${C_RST}

  ${C_DIM}Preview without rebooting:${C_RST}
      sudo plymouthd
      sudo plymouth --show-splash
      sleep 6
      sudo plymouth quit

  ${C_DIM}Test on next boot:${C_RST}
      sudo reboot

${C_GOLD}NYX-J5W-2026-SIERENGOWSKI-LOCKED${C_RST}

EOF
