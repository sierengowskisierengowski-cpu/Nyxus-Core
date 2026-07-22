#!/usr/bin/env bash
# ============================================================
#  NYXUS — build + install "Kage Ryu Nyxus" as a SELECTABLE kernel
#  © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
#  Display name: "Kage Ryu Nyxus". Technical package/build id stays
#  `linux-kage-ryu` (pkgbase) so the bootloader/pacman/module paths keep
#  working — only the human-facing name changes, not the underlying slug.
#
#  Builds the operator's Kage Ryu Nyxus security kernel and installs it
#  ALONGSIDE the stock kernel. Stock `linux` remains the DEFAULT boot entry —
#  Kage Ryu Nyxus is picked from the bootloader menu. A bad custom-kernel
#  build can never strand you.
#
#  DO NOT run this until the Nyxus greetd login is verified stable (we hold
#  custom-kernel work off an unverified login change on purpose).
#
#  Usage:  sudo kernel/install-kage-ryu.sh
#          sudo kernel/install-kage-ryu.sh --repo /path/to/kage-ryu
# ============================================================
set -euo pipefail

KAGE_REPO="${KAGE_REPO:-$HOME/Projects/arch-custom-kernel/linux-kage-ryu}"
KAGE_GIT="https://github.com/sierengowskisierengowski-cpu/kage-ryu.git"
REAL_USER="${SUDO_USER:-${USER}}"

[[ "${1:-}" == "--repo" && -n "${2:-}" ]] && KAGE_REPO="$2"

if [[ $EUID -ne 0 ]]; then echo "run: sudo $0"; exit 1; fi

echo "▌ Kage Ryu Nyxus selectable-kernel install (stock stays default)"

# makepkg must NOT run as root — build as the real user, install as root.
if [[ ! -d "$KAGE_REPO" ]]; then
  echo "  · cloning kage-ryu → $KAGE_REPO"
  sudo -u "$REAL_USER" git clone "$KAGE_GIT" "$KAGE_REPO"
fi

echo "  · building (this takes a while; localmodconfig if ~/.config/modprobed.db exists)"
LOCALMOD=n
[[ -f "$(getent passwd "$REAL_USER" | cut -d: -f6)/.config/modprobed.db" ]] && LOCALMOD=y
sudo -u "$REAL_USER" bash -lc "cd '$KAGE_REPO' && env _localmodcfg=$LOCALMOD makepkg -sc --noconfirm"

echo "  · installing kernel packages"
pacman -U --noconfirm "$KAGE_REPO"/linux-kage-ryu-*.pkg.tar.zst \
                      "$KAGE_REPO"/linux-kage-ryu-headers-*.pkg.tar.zst

# Regenerate the bootloader menu WITHOUT changing the default entry.
if command -v grub-mkconfig >/dev/null 2>&1 && [[ -d /boot/grub ]]; then
  echo "  · grub: regenerating menu (GRUB_DEFAULT unchanged — stock stays default)"
  grub-mkconfig -o /boot/grub/grub.cfg
elif [[ -d /boot/loader/entries ]]; then
  echo "  · systemd-boot: kernel pacman hook writes the entry; default unchanged"
  bootctl update 2>/dev/null || true
else
  echo "  ! unknown bootloader — verify kage-ryu entry exists before rebooting"
fi

# Install + run the Kage-Ryu auto-activation layer (tuning + sched-ext), which
# supersedes the old standalone BBR drop-in and makes the kernel self-activate
# on every future upgrade (pacman hook). Falls back to just the BBR sysctl if
# the kage-ryu checkout predates the packaging/ layer.
if [[ -x "${KAGE_REPO}/packaging/install-activation.sh" ]]; then
  echo "  · installing Kage-Ryu auto-activation layer (self-activates on kernel upgrades)"
  "${KAGE_REPO}/packaging/install-activation.sh" \
    || echo "  ! activation layer returned non-zero (kernel is still installed)"
else
  echo "  · packaging/ layer not present in ${KAGE_REPO}; shipping standalone BBR sysctl"
  install -Dm644 "$(dirname "$0")/nyxus-bbr.conf" /etc/sysctl.d/99-nyxus-bbr.conf
fi

cat <<EOF

── Kage Ryu Nyxus installed as a SELECTABLE kernel ──────────────────
Default boot is still stock 'linux'. To boot Kage Ryu Nyxus: pick it from
the bootloader menu (GRUB: 'Advanced options'; systemd-boot: the entry
built from the linux-kage-ryu package — title shows the NYXUS os-release
name + kernel version). Verify after boot:
    uname -r            # will show -kage-ryu (build/package id, unchanged)
    zcat /proc/config.gz | grep -E 'MALDERLAKE|PREEMPT=|BPF_LSM'
    bpftool btf list | head   # BTF present for jeTT CO-RE sensor
If it misbehaves, just reboot and pick stock — nothing is lost.
──────────────────────────────────────────────────────────────────────
EOF
