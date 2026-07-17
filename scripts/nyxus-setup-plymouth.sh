#!/usr/bin/env bash
# ═════════════════════════════════════════════════════════════════════════════
#  nyxus-setup-plymouth.sh   ·   NYXUS "COSMIC ARRIVAL" boot cinematic installer
#
#  Wires the NYXUS UFO-landing Plymouth theme into the boot chain so boot flows:
#      BIOS → themed Plymouth UFO animation → greeter (regreet) → desktop
#
#  What it does (all idempotent, all configs backed up as *.nyxus-bak):
#    1. installs `plymouth` if missing (pacman)
#    2. copies the theme  → /usr/share/plymouth/themes/nyxus
#    3. writes /etc/plymouth/plymouthd.conf  (Theme=nyxus, ShowDelay=0)
#    4. ensures the `plymouth` hook is in /etc/mkinitcpio.conf HOOKS (after kms)
#    5. ensures `quiet splash` kernel params — BOOTLOADER AWARE:
#         · systemd-boot + UKI / kernel-install → /etc/kernel/cmdline   (THIS box)
#         · systemd-boot type#1 entries         → /boot/loader/entries/*.conf
#         · GRUB                                 → /etc/default/grub + grub-mkconfig
#    6. sets the default theme + rebuilds the initramfs/UKI:
#         plymouth-set-default-theme -R nyxus     (runs mkinitcpio -P)
#    7. VERIFIES every step and prints a reboot reminder.
#
#  ── THIS SCRIPT NEEDS ROOT. Run it yourself: ────────────────────────────────
#         sudo bash scripts/nyxus-setup-plymouth.sh
#
#  The splash is only VISIBLE after this runs AND you reboot.
#
#  Revert:  restore the *.nyxus-bak files and rerun `sudo mkinitcpio -P`
#           (GRUB: also `sudo grub-mkconfig -o /boot/grub/grub.cfg`).
#
#  © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ═════════════════════════════════════════════════════════════════════════════
set -euo pipefail

THEME_NAME="nyxus"
PLY_DEST="/usr/share/plymouth/themes/${THEME_NAME}"
MKCONF="/etc/mkinitcpio.conf"
KCMDLINE="/etc/kernel/cmdline"

# ── colours ─────────────────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  C_RST=$'\033[0m'; C_B=$'\033[1m'; C_DIM=$'\033[2m'
  C_OK=$'\033[38;5;120m'; C_WARN=$'\033[38;5;214m'; C_ERR=$'\033[38;5;203m'
  C_V=$'\033[38;5;177m'
else
  C_RST=""; C_B=""; C_DIM=""; C_OK=""; C_WARN=""; C_ERR=""; C_V=""
fi
ok()   { echo "${C_OK}✓${C_RST} $*"; }
info() { echo "${C_V}→${C_RST} $*"; }
warn() { echo "${C_WARN}⚠${C_RST} $*" >&2; }
die()  { echo "${C_ERR}✗ $*${C_RST}" >&2; exit 1; }

# ── locate the theme source (repo copy) ─────────────────────────────────────
SELF="$(readlink -f "${BASH_SOURCE[0]}")"
REPO_ROOT="$(cd "$(dirname "${SELF}")/.." && pwd)"
THEME_SRC="${NYXUS_THEME_SRC:-${1:-${REPO_ROOT}/artifacts/api-server/nyxus-scripts/plymouth/${THEME_NAME}}}"

echo
echo "${C_B}${C_V}   ◤ NYXUS ◥  COSMIC ARRIVAL · boot cinematic setup${C_RST}"
echo "${C_DIM}   SIERENGOWSKI · 2026 · Welcome to the darkside${C_RST}"
echo

[[ ${EUID} -eq 0 ]] || die "run me with root:  sudo bash $(basename "$0")"
[[ -f "${THEME_SRC}/${THEME_NAME}.plymouth" ]] \
  || die "theme source not found at: ${THEME_SRC}  (pass path as arg or set NYXUS_THEME_SRC)"

# backup helper — copy once, never clobber an existing backup
backup() { [[ -e "$1" && ! -e "$1.nyxus-bak" ]] && cp -a "$1" "$1.nyxus-bak" && info "backed up $1 → $1.nyxus-bak" || true; }

# ── detect environment ──────────────────────────────────────────────────────
info "detecting boot environment …"
GEN="none"
if command -v mkinitcpio >/dev/null 2>&1 && [[ -f "${MKCONF}" ]]; then
  GEN="mkinitcpio"
elif command -v dracut >/dev/null 2>&1; then
  GEN="dracut"
fi

USES_UKI=0
if compgen -G "/etc/mkinitcpio.d/*.preset" >/dev/null 2>&1 \
   && grep -qsE '^[^#]*_uki=' /etc/mkinitcpio.d/*.preset; then
  USES_UKI=1
fi

BOOTLOADER="unknown"
if [[ -d /boot/loader/entries ]] || bootctl is-installed >/dev/null 2>&1; then
  BOOTLOADER="systemd-boot"
fi
if [[ -f /etc/default/grub ]] || [[ -f /boot/grub/grub.cfg ]]; then
  # GRUB present — prefer it only if systemd-boot isn't the active loader
  if [[ "${BOOTLOADER}" != "systemd-boot" ]]; then BOOTLOADER="grub"; fi
fi

echo "     initramfs generator : ${C_B}${GEN}${C_RST}"
echo "     bootloader          : ${C_B}${BOOTLOADER}${C_RST}"
echo "     unified kernel image: ${C_B}$([[ ${USES_UKI} -eq 1 ]] && echo yes || echo no)${C_RST}"
[[ "${GEN}" == "none" ]] && die "no supported initramfs generator (mkinitcpio/dracut) found"

# ── 1 · plymouth package ────────────────────────────────────────────────────
if command -v plymouth-set-default-theme >/dev/null 2>&1; then
  ok "plymouth already installed ($(plymouth --version 2>/dev/null | head -1))"
else
  info "installing plymouth …"
  if command -v pacman >/dev/null 2>&1; then
    pacman -S --needed --noconfirm plymouth || die "pacman failed to install plymouth"
  else
    die "plymouth missing and no pacman — install plymouth then rerun"
  fi
fi

# ── 2 · copy theme (runtime files only) ─────────────────────────────────────
info "installing theme → ${PLY_DEST}"
install -d -m 0755 "${PLY_DEST}"
install -m 0644 "${THEME_SRC}/${THEME_NAME}.plymouth" "${PLY_DEST}/"
install -m 0644 "${THEME_SRC}/${THEME_NAME}.script"   "${PLY_DEST}/"
shopt -s nullglob
for png in "${THEME_SRC}"/*.png; do
  base="$(basename "${png}")"
  [[ "${base}" == _* ]] && continue     # skip _nebula_source.png (build-only)
  install -m 0644 "${png}" "${PLY_DEST}/"
done
shopt -u nullglob
ok "theme files installed ($(ls -1 "${PLY_DEST}"/*.png | wc -l) images)"

# ── 3 · plymouthd.conf ──────────────────────────────────────────────────────
install -d -m 0755 /etc/plymouth
backup /etc/plymouth/plymouthd.conf
cat > /etc/plymouth/plymouthd.conf <<EOF
[Daemon]
Theme=${THEME_NAME}
ShowDelay=0
DeviceTimeout=8
EOF
ok "wrote /etc/plymouth/plymouthd.conf (Theme=${THEME_NAME})"

# ── 4 · mkinitcpio plymouth hook ────────────────────────────────────────────
if [[ "${GEN}" == "mkinitcpio" ]]; then
  if grep -E '^HOOKS=' "${MKCONF}" | grep -qw plymouth; then
    ok "mkinitcpio: 'plymouth' hook already present"
  else
    backup "${MKCONF}"
    if grep -E '^HOOKS=' "${MKCONF}" | grep -qw kms; then
      sed -i -E '/^HOOKS=/ s/\bkms\b/kms plymouth/' "${MKCONF}"        # after kms
    else
      sed -i -E '/^HOOKS=/ s/\budev\b/udev plymouth/' "${MKCONF}"      # else after udev
    fi
    grep -E '^HOOKS=' "${MKCONF}" | grep -qw plymouth \
      || die "failed to insert plymouth hook — edit ${MKCONF} HOOKS manually"
    ok "mkinitcpio: inserted 'plymouth' hook"
  fi
  echo "     $(grep -E '^HOOKS=' "${MKCONF}")"
elif [[ "${GEN}" == "dracut" ]]; then
  DR="/etc/dracut.conf.d/nyxus-plymouth.conf"
  echo 'add_dracutmodules+=" plymouth "' > "${DR}"
  ok "dracut: wrote ${DR} (plymouth module)"
fi

# ── 5 · kernel cmdline: ensure `quiet splash` ───────────────────────────────
ensure_tokens_in_string() {   # echoes the string with quiet/splash appended if missing
  local s="$1" tok
  for tok in quiet splash; do
    grep -qw "${tok}" <<<"${s}" || s="${s} ${tok}"
  done
  echo "${s}" | sed -E 's/[[:space:]]+/ /g; s/^ //; s/ $//'
}

CMDLINE_METHOD="none"
if [[ -f "${KCMDLINE}" ]]; then
  # systemd-boot + UKI / kernel-install: /etc/kernel/cmdline is the source of truth
  CMDLINE_METHOD="kernel-cmdline"
  cur="$(tr -d '\n' < "${KCMDLINE}")"
  new="$(ensure_tokens_in_string "${cur}")"
  if [[ "${cur}" == "${new}" ]]; then
    ok "cmdline: 'quiet splash' already in ${KCMDLINE}"
  else
    backup "${KCMDLINE}"
    printf '%s\n' "${new}" > "${KCMDLINE}"
    ok "cmdline: updated ${KCMDLINE}"
  fi
  echo "     ${KCMDLINE}: $(cat "${KCMDLINE}")"
elif compgen -G "/boot/loader/entries/*.conf" >/dev/null 2>&1; then
  # systemd-boot type#1 entries
  CMDLINE_METHOD="sdboot-entries"
  for ent in /boot/loader/entries/*.conf; do
    grep -qE '^options ' "${ent}" || continue
    cur="$(sed -nE 's/^options (.*)$/\1/p' "${ent}")"
    new="$(ensure_tokens_in_string "${cur}")"
    if [[ "${cur}" != "${new}" ]]; then
      backup "${ent}"
      sed -i -E "s|^options .*$|options ${new}|" "${ent}"
      ok "cmdline: updated $(basename "${ent}")"
    else
      ok "cmdline: 'quiet splash' already in $(basename "${ent}")"
    fi
  done
elif [[ -f /etc/default/grub ]]; then
  # GRUB
  CMDLINE_METHOD="grub"
  cur="$(sed -nE 's/^GRUB_CMDLINE_LINUX_DEFAULT="(.*)"$/\1/p' /etc/default/grub)"
  new="$(ensure_tokens_in_string "${cur}")"
  if [[ "${cur}" != "${new}" ]]; then
    backup /etc/default/grub
    sed -i -E "s|^GRUB_CMDLINE_LINUX_DEFAULT=\".*\"|GRUB_CMDLINE_LINUX_DEFAULT=\"${new}\"|" /etc/default/grub
    ok "cmdline: updated GRUB_CMDLINE_LINUX_DEFAULT"
  else
    ok "cmdline: 'quiet splash' already in /etc/default/grub"
  fi
else
  warn "could not find a kernel cmdline source — add 'quiet splash' manually."
fi

# ── 6 · set default theme + rebuild initramfs/UKI ───────────────────────────
info "setting default theme + rebuilding initramfs (this regenerates the UKI)…"
if plymouth-set-default-theme -R "${THEME_NAME}"; then
  ok "plymouth-set-default-theme -R ${THEME_NAME} complete"
else
  warn "plymouth-set-default-theme -R failed; falling back to manual rebuild"
  plymouth-set-default-theme "${THEME_NAME}" || true
  if [[ "${GEN}" == "mkinitcpio" ]]; then mkinitcpio -P; else dracut -f; fi
fi

# GRUB needs its config regenerated for the new cmdline to take effect
if [[ "${CMDLINE_METHOD}" == "grub" ]] && command -v grub-mkconfig >/dev/null 2>&1; then
  GRUB_CFG="/boot/grub/grub.cfg"; [[ -f "${GRUB_CFG}" ]] || GRUB_CFG="/boot/grub2/grub.cfg"
  grub-mkconfig -o "${GRUB_CFG}" && ok "regenerated ${GRUB_CFG}"
fi

# ── 7 · VERIFY ──────────────────────────────────────────────────────────────
echo
echo "${C_B}   verification${C_RST}"
FAIL=0
CUR_THEME="$(plymouth-set-default-theme 2>/dev/null || true)"
[[ "${CUR_THEME}" == "${THEME_NAME}" ]] \
  && ok "default theme = ${CUR_THEME}" \
  || { warn "default theme is '${CUR_THEME}', expected '${THEME_NAME}'"; FAIL=1; }

[[ -f "${PLY_DEST}/${THEME_NAME}.script" ]] \
  && ok "theme installed at ${PLY_DEST}" \
  || { warn "theme script missing in ${PLY_DEST}"; FAIL=1; }

if [[ "${GEN}" == "mkinitcpio" ]]; then
  grep -E '^HOOKS=' "${MKCONF}" | grep -qw plymouth \
    && ok "mkinitcpio HOOKS contains 'plymouth'" \
    || { warn "plymouth hook missing from HOOKS"; FAIL=1; }
fi

case "${CMDLINE_METHOD}" in
  kernel-cmdline) grep -qw splash "${KCMDLINE}" && grep -qw quiet "${KCMDLINE}" \
      && ok "'quiet splash' present in ${KCMDLINE}" || { warn "quiet/splash missing in ${KCMDLINE}"; FAIL=1; } ;;
  sdboot-entries) grep -qw splash /boot/loader/entries/*.conf \
      && ok "'splash' present in loader entries" || { warn "splash missing in loader entries"; FAIL=1; } ;;
  grub) grep -q 'splash' /etc/default/grub \
      && ok "'splash' present in /etc/default/grub" || { warn "splash missing in /etc/default/grub"; FAIL=1; } ;;
esac

# UKI/initramfs freshly built?
if [[ ${USES_UKI} -eq 1 && -f /boot/EFI/Linux/arch-linux.efi ]]; then
  if [[ /boot/EFI/Linux/arch-linux.efi -nt "${MKCONF}" ]]; then
    ok "UKI rebuilt after config edits (/boot/EFI/Linux/arch-linux.efi)"
  else
    warn "UKI may be stale — rerun 'sudo mkinitcpio -P'"
  fi
fi

echo
if [[ ${FAIL} -eq 0 ]]; then
  echo "${C_OK}${C_B}   ◤ NYXUS ◥  boot cinematics armed.${C_RST}"
else
  echo "${C_WARN}${C_B}   setup finished with warnings — see above.${C_RST}"
fi
cat <<EOF

${C_DIM}   Preview WITHOUT rebooting (optional, draws on the current VT for ~8s):${C_RST}
       sudo plymouthd ; sudo plymouth --show-splash ; sleep 8 ; sudo plymouth quit

${C_DIM}   Then to see it for real:${C_RST}
       sudo reboot

${C_V}   The saucer only descends after a reboot — this is a boot-time splash.${C_RST}
EOF
exit ${FAIL}
