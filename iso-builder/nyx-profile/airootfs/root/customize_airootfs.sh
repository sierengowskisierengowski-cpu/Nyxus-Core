#!/usr/bin/env bash
# ============================================
# NYXUS — airootfs customization hook
# Copyright © 2026 Joseph Sierengowski
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
#
# archiso runs this script INSIDE the airootfs (chroot) at build time.
# Used to create the live user, set passwords, and enable services that
# can't be set up purely by dropping config files into airootfs/.
#
# Reference: https://wiki.archlinux.org/title/Archiso#Adding_users
set -e -u

# ── Locale ──────────────────────────────────────────────────────────────
locale-gen

# ── Root password ───────────────────────────────────────────────────────
# Default live root password is `nyx`. Change after install.
echo 'root:nyx' | chpasswd

# ── Create the live `nyx` user ──────────────────────────────────────────
# wheel    → sudo
# audio/video/input/storage/network → device access for daily-driver use
if ! id -u nyx >/dev/null 2>&1; then
  useradd -m -G wheel,audio,video,input,storage,network,uucp -s /bin/bash nyx
fi
echo 'nyx:nyx' | chpasswd

# ── Sudoers: allow wheel to sudo with password ─────────────────────────
sed -i 's/^# *%wheel ALL=(ALL:ALL) ALL$/%wheel ALL=(ALL:ALL) ALL/' /etc/sudoers
sed -i 's/^# *%wheel ALL=(ALL) ALL$/%wheel ALL=(ALL) ALL/' /etc/sudoers

# ── Skel → /home/nyx (wallpapers, hyprland.conf, etc.) ─────────────────
# /etc/skel was already populated at airootfs build time; copy any files
# that landed AFTER useradd ran. Owner is fixed below.
if [ -d /etc/skel ]; then
  cp -rT /etc/skel /home/nyx
  chown -R nyx:nyx /home/nyx
fi

# ── Enable display + network services ──────────────────────────────────
systemctl enable sddm.service           2>/dev/null || true
systemctl enable NetworkManager.service 2>/dev/null || true
systemctl enable systemd-timesyncd.service 2>/dev/null || true
