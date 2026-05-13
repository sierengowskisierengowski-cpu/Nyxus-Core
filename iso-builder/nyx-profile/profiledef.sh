#!/usr/bin/env bash
# ============================================
# NYXUS — nyx-2026.05.11-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
#
# archiso profile definition for the NYX ISO.
# See: https://wiki.archlinux.org/title/Archiso

iso_name="nyx"
iso_label="NYX_2026_05"
iso_publisher="Joseph Sierengowski <https://github.com/sierengowski/NyX.OS-V1>"
iso_application="NYXUS Live/Install"
iso_version="2026.05.11"
install_dir="arch"
buildmodes=('iso')
bootmodes=(
  'bios.syslinux.mbr'
  'bios.syslinux.eltorito'
  'uefi-ia32.grub.esp'
  'uefi-x64.grub.esp'
  'uefi-ia32.grub.eltorito'
  'uefi-x64.grub.eltorito'
)
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
bootstrap_tarball_compression=(zstd -c -T0 --auto-threads=logical --long -19)
file_permissions=(
  ["/root"]="0:0:750"
  ["/root/customize_airootfs.sh"]="0:0:755"
  # nyxus-* CLI binaries (root cause of 2026-05-13 outage when missing).
  # archiso's squashfs only preserves the perms listed here; `install -m 0755`
  # in build-iso.sh is NOT enough by itself. Every executable shipped to
  # /usr/local/bin/ MUST be locked here or it boots non-executable.
  ["/usr/local/bin/nyxus-intel"]="0:0:755"
  ["/usr/local/bin/nyxus-bootstrap"]="0:0:755"
  ["/usr/local/bin/nyxus-wait-bootstrap"]="0:0:755"
  ["/usr/local/bin/nyxus-install"]="0:0:755"
  ["/usr/local/bin/nyxus-postinstall"]="0:0:755"
  ["/usr/local/bin/nyxus-backup"]="0:0:755"
  ["/usr/local/bin/nyxus-clipboard"]="0:0:755"
  ["/usr/local/bin/nyxus-context-menu.sh"]="0:0:755"
  ["/usr/local/bin/nyxus-crashd"]="0:0:755"
  ["/usr/local/bin/nyxus-desktop"]="0:0:755"
  ["/usr/local/bin/nyxus-drop"]="0:0:755"
  ["/usr/local/bin/nyxus-eww-launch"]="0:0:755"
  ["/usr/local/bin/nyxus-files"]="0:0:755"
  ["/usr/local/bin/nyxus-record"]="0:0:755"
  ["/usr/local/bin/nyxus-security"]="0:0:755"
  ["/usr/local/bin/nyxus-set-wallpaper.sh"]="0:0:755"
  ["/usr/local/bin/nyxus-sound.sh"]="0:0:755"
  ["/usr/local/bin/nyxus-updater"]="0:0:755"
  ["/usr/local/bin/wallpaper-rotate"]="0:0:755"
  # Privileged helpers (libexec) — invoked via polkit, must be executable.
  ["/usr/local/libexec/nyxus-parental-helper"]="0:0:755"
  # Live-session sudoers drop-in: passwordless sudo for nyx user on the
  # live ISO ONLY. Calamares post-install removes /etc/sudoers.d/10-nyxus-live
  # so the installed system reverts to standard wheel + password.
  ["/etc/sudoers.d/10-nyxus-live"]="0:0:440"
  ["/etc/nyxus"]="0:0:755"
)
