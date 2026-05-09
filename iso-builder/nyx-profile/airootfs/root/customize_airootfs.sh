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

# ── Build mpvpaper from source (AUR-only, can't pacstrap) ──────────────
# rev r25 — animated wallpaper daemon. Runtime deps (mpv, wayland-protocols)
# and build deps (base-devel, meson, ninja, scdoc, git) are already pulled
# in via packages.x86_64. We clone, build, and install to /usr/local/bin
# during airootfs customization so the live ISO + every fresh install ships
# with mpvpaper available system-wide. No AUR helper required.
if ! command -v mpvpaper >/dev/null 2>&1; then
  echo "[customize_airootfs] building mpvpaper from source..."
  _bdir=$(mktemp -d)
  if git clone --depth 1 https://github.com/GhostNaN/mpvpaper.git "$_bdir/mpvpaper" \
     && cd "$_bdir/mpvpaper" \
     && meson setup build \
     && ninja -C build \
     && ninja -C build install; then
    echo "[customize_airootfs] mpvpaper installed → $(command -v mpvpaper)"
  else
    echo "[customize_airootfs] WARNING: mpvpaper build failed — wallpaper will fall back to static swaybg"
  fi
  cd / && rm -rf "$_bdir"
fi

# ── Enable display + network services ──────────────────────────────────
systemctl enable sddm.service           2>/dev/null || true
systemctl enable NetworkManager.service 2>/dev/null || true
systemctl enable systemd-timesyncd.service 2>/dev/null || true
