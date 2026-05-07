#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  NYXUS · Boot Splash Installer
#  Installs Plymouth theme (kernel-phase splash) + GRUB theme (bootloader menu)
#  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ─────────────────────────────────────────────────────────────────────────────
#
#  USAGE — INSTALLED SYSTEM (post-bake on real hardware):
#      sudo bash install.sh
#
#  USAGE — INSIDE ARCHISO PROFILE (during ISO build):
#      sudo NYX_PROFILE_ROOT=/path/to/nyx-profile bash install.sh --iso
#
#  REQUIRES on installed system:
#      plymouth, plymouth-set-default-theme, grub, mkinitcpio, sed
#
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
THEME_NAME="nyxus"
MODE="${1:-system}"

C_RST=$'\033[0m'; C_DIM=$'\033[2m'; C_BOLD=$'\033[1m'
C_OK=$'\033[0;32m'; C_WARN=$'\033[0;33m'; C_ERR=$'\033[0;31m'
C_GOLD=$'\033[38;5;179m'

cat <<EOF

${C_BOLD}${C_GOLD}     N Y X U S${C_RST}
${C_DIM}     SIERENGOWSKI · 2026${C_RST}
${C_DIM}     BOOT SPLASH · WELCOME TO THE DARKSIDE${C_RST}

EOF

if [[ $EUID -ne 0 ]]; then
    echo "${C_ERR}✗ Run as root: sudo bash install.sh${C_RST}"
    exit 1
fi

# ═════════════════════════════════════════════════════════════════════════════
# MODE: --iso  (mutate an archiso profile so the ISO bakes the splash in)
# ═════════════════════════════════════════════════════════════════════════════
if [[ "$MODE" == "--iso" ]]; then
    : "${NYX_PROFILE_ROOT:?Set NYX_PROFILE_ROOT to your nyx-profile/ directory}"
    PROFILE="${NYX_PROFILE_ROOT}"
    AIROOT="${PROFILE}/airootfs"

    echo "${C_DIM}→${C_RST} Profile: ${PROFILE}"

    # 1. Stage Plymouth theme into airootfs
    install -d "${AIROOT}/usr/share/plymouth/themes/${THEME_NAME}"
    install -m 0644 "${SCRIPT_DIR}/plymouth/${THEME_NAME}/"* \
        "${AIROOT}/usr/share/plymouth/themes/${THEME_NAME}/"
    echo "${C_OK}✓${C_RST} Plymouth theme staged → /usr/share/plymouth/themes/${THEME_NAME}/"

    # 2. Stage GRUB theme into airootfs
    install -d "${AIROOT}/usr/share/grub/themes/${THEME_NAME}"
    install -m 0644 "${SCRIPT_DIR}/grub/themes/${THEME_NAME}/"* \
        "${AIROOT}/usr/share/grub/themes/${THEME_NAME}/"
    echo "${C_OK}✓${C_RST} GRUB theme staged → /usr/share/grub/themes/${THEME_NAME}/"

    # 3. Append plymouth packages to packages.x86_64 (idempotent)
    PKGS="${PROFILE}/packages.x86_64"
    for pkg in plymouth; do
        if ! grep -qE "^${pkg}\$" "${PKGS}"; then
            echo "${pkg}" >> "${PKGS}"
            echo "${C_OK}✓${C_RST} Added ${pkg} to packages.x86_64"
        fi
    done

    # 4. Patch mkinitcpio HOOKS to include plymouth (after udev, before encrypt/filesystems)
    MKICONF="${AIROOT}/etc/mkinitcpio.conf.d/archiso.conf"
    [[ -f "${MKICONF}" ]] || MKICONF="${AIROOT}/etc/mkinitcpio.conf"
    if [[ -f "${MKICONF}" ]]; then
        if ! grep -qE 'HOOKS=.*plymouth' "${MKICONF}"; then
            sed -i -E 's/^(HOOKS=\([^)]*udev)([^)]*)\)/\1 plymouth\2)/' "${MKICONF}"
            echo "${C_OK}✓${C_RST} Inserted plymouth hook into ${MKICONF}"
        fi
    else
        echo "${C_WARN}⚠${C_RST}  No mkinitcpio.conf found in airootfs — add 'plymouth' hook manually after 'udev'"
    fi

    # 5. Stamp default theme
    install -d "${AIROOT}/etc/plymouth"
    cat > "${AIROOT}/etc/plymouth/plymouthd.conf" <<EOF
[Daemon]
Theme=${THEME_NAME}
ShowDelay=0
DeviceTimeout=8
EOF
    echo "${C_OK}✓${C_RST} Wrote /etc/plymouth/plymouthd.conf"

    # 6. Patch grub.cfg to load theme
    GRUB_CFG="${PROFILE}/grub/grub.cfg"
    if [[ -f "${GRUB_CFG}" ]] && ! grep -q "set theme=" "${GRUB_CFG}"; then
        # Insert theme block after the gfxterm setup
        sed -i '/^terminal_output gfxterm/a \
\
# ── NYXUS theme ──────────────────────────────────────────────\
insmod png\
loadfont $prefix/themes/'"${THEME_NAME}"'/dejavu-mono-12.pf2 2>/dev/null || true\
set theme=$prefix/themes/'"${THEME_NAME}"'/theme.txt\
export theme' "${GRUB_CFG}"
        echo "${C_OK}✓${C_RST} Patched ${GRUB_CFG} to load NYXUS theme"
    fi

    # 7. Stage GRUB theme into the ISO's grub/ tree too
    install -d "${PROFILE}/grub/themes/${THEME_NAME}"
    install -m 0644 "${SCRIPT_DIR}/grub/themes/${THEME_NAME}/"* \
        "${PROFILE}/grub/themes/${THEME_NAME}/"
    echo "${C_OK}✓${C_RST} GRUB theme staged → ${PROFILE}/grub/themes/${THEME_NAME}/"

    cat <<EOF

${C_OK}${C_BOLD}✓ ISO profile patched${C_RST}

  Now build the ISO:
    ${C_DIM}sudo mkarchiso -v -w /tmp/archiso-work -o ./out ${PROFILE}${C_RST}

${C_GOLD}NYX-J5W-2026-SIERENGOWSKI-LOCKED${C_RST}

EOF
    exit 0
fi

# ═════════════════════════════════════════════════════════════════════════════
# MODE: system  (install onto the running NYXUS box)
# ═════════════════════════════════════════════════════════════════════════════

# 1. Plymouth dependencies
if ! command -v plymouth-set-default-theme &>/dev/null; then
    echo "${C_WARN}→${C_RST} plymouth not installed — installing ..."
    if command -v pacman &>/dev/null; then
        pacman -Sy --noconfirm plymouth
    else
        echo "${C_ERR}✗ Need plymouth and pacman. Install plymouth manually then re-run.${C_RST}"
        exit 1
    fi
fi

# 2. Install plymouth theme
PLY_DIR="/usr/share/plymouth/themes/${THEME_NAME}"
echo "${C_DIM}→${C_RST} Installing Plymouth theme → ${PLY_DIR}"
install -d "${PLY_DIR}"
install -m 0644 "${SCRIPT_DIR}/plymouth/${THEME_NAME}/"* "${PLY_DIR}/"

# 3. Activate it
plymouth-set-default-theme -R "${THEME_NAME}" >/dev/null 2>&1 \
    && echo "${C_OK}✓${C_RST} Plymouth default theme = ${THEME_NAME} (initramfs rebuilt)" \
    || { echo "${C_WARN}⚠ plymouth-set-default-theme failed, doing it manually${C_RST}"; \
         plymouth-set-default-theme "${THEME_NAME}"; \
         mkinitcpio -P; }

# 4. Ensure kernel cmdline has 'splash quiet' (idempotent)
DEFAULT_GRUB="/etc/default/grub"
if [[ -f "${DEFAULT_GRUB}" ]]; then
    if ! grep -qE 'GRUB_CMDLINE_LINUX_DEFAULT=.*splash' "${DEFAULT_GRUB}"; then
        sed -i 's/^\(GRUB_CMDLINE_LINUX_DEFAULT="\)/\1quiet splash /' "${DEFAULT_GRUB}"
        echo "${C_OK}✓${C_RST} Added 'quiet splash' to GRUB_CMDLINE_LINUX_DEFAULT"
    fi
    if ! grep -qE '^GRUB_THEME=' "${DEFAULT_GRUB}"; then
        echo "GRUB_THEME=\"/usr/share/grub/themes/${THEME_NAME}/theme.txt\"" >> "${DEFAULT_GRUB}"
        echo "${C_OK}✓${C_RST} Set GRUB_THEME"
    fi
fi

# 5. Install GRUB theme
GRUB_DIR="/usr/share/grub/themes/${THEME_NAME}"
echo "${C_DIM}→${C_RST} Installing GRUB theme → ${GRUB_DIR}"
install -d "${GRUB_DIR}"
install -m 0644 "${SCRIPT_DIR}/grub/themes/${THEME_NAME}/"* "${GRUB_DIR}/"

# 6. Regenerate grub.cfg
if command -v grub-mkconfig &>/dev/null && [[ -f /boot/grub/grub.cfg ]]; then
    grub-mkconfig -o /boot/grub/grub.cfg
    echo "${C_OK}✓${C_RST} grub.cfg regenerated"
fi

# 7. Patch plymouthd.conf
install -d /etc/plymouth
cat > /etc/plymouth/plymouthd.conf <<EOF
[Daemon]
Theme=${THEME_NAME}
ShowDelay=0
DeviceTimeout=8
EOF
echo "${C_OK}✓${C_RST} Wrote /etc/plymouth/plymouthd.conf"

cat <<EOF

${C_OK}${C_BOLD}✓ NYXUS boot splash installed${C_RST}

  ${C_DIM}Preview without rebooting:${C_RST}
      sudo plymouthd
      sudo plymouth --show-splash
      sleep 6
      sudo plymouth quit

  ${C_DIM}Test on next boot:${C_RST}
      sudo reboot

${C_GOLD}NYX-J5W-2026-SIERENGOWSKI-LOCKED${C_RST}

EOF
