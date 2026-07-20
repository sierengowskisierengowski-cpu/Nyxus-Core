#!/usr/bin/env bash
# ============================================
# NYXUS — nyx-2026.05.11-x86_64.iso
# Copyright © 2026 Joseph A. Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
#
# archiso profile definition for the NYX ISO.
# See: https://wiki.archlinux.org/title/Archiso

iso_name="nyx"
iso_label="NYX_2026_05"
iso_publisher="Joseph A. Sierengowski <https://github.com/sierengowski/NyX.OS-V1>"
iso_application="NYXUS Live/Install"
iso_version="2026.07.16"
install_dir="arch"
buildmodes=('iso')
bootmodes=(
  'bios.syslinux'
  'uefi.grub'
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
  ["/usr/local/bin/nyxus-mission-control-toggle"]="0:0:755"
  ["/usr/local/bin/nyxus-files"]="0:0:755"
  ["/usr/local/bin/nyxus-record"]="0:0:755"
  ["/usr/local/bin/nyxus-security"]="0:0:755"
  ["/usr/local/bin/nyxus-set-wallpaper.sh"]="0:0:755"
  ["/usr/local/bin/nyxus-sound.sh"]="0:0:755"
  ["/usr/local/bin/nyxus-updater"]="0:0:755"
  ["/usr/local/bin/wallpaper-rotate"]="0:0:755"
  # ── Dynamically-generated app launchers (build-iso.sh APPS_LIST loop) ─
  # These are heredoc-emitted by build-iso.sh during bake. Each maps to a
  # nyxus_<mod>.py in /opt/nyxus/. MUST be locked or the start menu .desktop
  # entries point at non-executable files and apps refuse to launch.
  ["/usr/local/bin/nyxus-notepad"]="0:0:755"
  ["/usr/local/bin/nyxus-stickies"]="0:0:755"
  ["/usr/local/bin/nyxus-notes"]="0:0:755"
  ["/usr/local/bin/nyxus-sysmon"]="0:0:755"
  ["/usr/local/bin/nyxus-settings"]="0:0:755"
  ["/usr/local/bin/nyxus-control"]="0:0:755"
  ["/usr/local/bin/nyxus-terminal"]="0:0:755"
  ["/usr/local/bin/nyxus-launcher"]="0:0:755"
  ["/usr/local/bin/nyxus-screenshot"]="0:0:755"
  ["/usr/local/bin/nyxus-store"]="0:0:755"
  ["/usr/local/bin/nyxus-powermenu"]="0:0:755"
  ["/usr/local/bin/nyxus-doctor"]="0:0:755"
  ["/usr/local/bin/nyxus-battery"]="0:0:755"
  ["/usr/local/bin/nyxus-netusage"]="0:0:755"
  ["/usr/local/bin/nyxus-tour"]="0:0:755"
  # ── Welcome wizard launcher + privileged helper ──────────────────────
  # nyxus-welcome is installed by customize_airootfs.sh from /root/ stage.
  # The auto-generated APPS_LIST wrapper would also have produced one,
  # but the staged version (with marker-file gating + flock) overrides it.
  ["/usr/local/bin/nyxus-welcome"]="0:0:755"
  ["/usr/local/libexec/nyxus-welcome-helper"]="0:0:755"
  # Privileged helpers (libexec) — invoked via polkit, must be executable.
  ["/usr/local/libexec/nyxus-parental-helper"]="0:0:755"
  # ── VM boot-test regression (2026-07-15) ─────────────────────────────
  # First-ever real `mkarchiso` bake + boot test found nyxus-greeter shipped
  # NON-EXECUTABLE (greetd: "/bin/sh: /usr/local/bin/nyxus-greeter: Permission
  # denied" → login-loop with zero recovery, the exact class of bug this
  # array exists to prevent). Root cause: this array was only ever patched
  # piecemeal for whichever files broke a given outage — most of
  # /usr/local/bin, /usr/local/libexec, /usr/local/sbin, and
  # /etc/nyxus-firstboot.d/*.sh were never added and had never been through
  # a real bake+boot cycle before tonight. Locking every currently-shipped
  # executable in those trees here, generated from the actual airootfs
  # contents at the time of this fix — see git history for the exact
  # audit if this list needs regenerating after new scripts are added.
  ["/etc/nyxus-firstboot.d/01-machine-id.sh"]="0:0:755"
  ["/etc/nyxus-firstboot.d/02-xdg-user-dirs.sh"]="0:0:755"
  ["/etc/nyxus-firstboot.d/03-mime-defaults.sh"]="0:0:755"
  ["/etc/nyxus-firstboot.d/04-welcome.sh"]="0:0:755"
  ["/etc/nyxus-firstboot.d/05-icon-cache.sh"]="0:0:755"
  ["/usr/local/bin/nyxus"]="0:0:755"
  ["/usr/local/bin/nyxus-account"]="0:0:755"
  ["/usr/local/bin/nyxus-apply-accent"]="0:0:755"
  ["/usr/local/bin/nyxus-backdoor-log"]="0:0:755"
  ["/usr/local/bin/nyxus-bar-plugins"]="0:0:755"
  ["/usr/local/bin/nyxus-bd-detect"]="0:0:755"
  ["/usr/local/bin/nyxus-bd-router"]="0:0:755"
  ["/usr/local/bin/nyxus-crash-report"]="0:0:755"
  ["/usr/local/bin/nyxus-distrobox-helper"]="0:0:755"
  ["/usr/local/bin/nyxus-dock"]="0:0:755"
  ["/usr/local/bin/nyxus-doh"]="0:0:755"
  ["/usr/local/bin/nyxus-eww-launch-safe"]="0:0:755"
  ["/usr/local/bin/nyxus-focusmode"]="0:0:755"
  ["/usr/local/bin/nyxus-gamemode"]="0:0:755"
  ["/usr/local/bin/nyxus-gen-backdrop"]="0:0:755"
  ["/usr/local/bin/nyxus-ghost-auth"]="0:0:755"
  ["/usr/local/bin/nyxus-ghost-register"]="0:0:755"
  ["/usr/local/bin/nyxus-ghost"]="0:0:755"
  ["/usr/local/bin/nyxus-ghost-helper"]="0:0:755"
  ["/usr/local/bin/nyxus-hacker-mode"]="0:0:755"
  ["/usr/local/bin/nyxus-blackarch-full"]="0:0:755"
  ["/usr/local/bin/nyxus-panic"]="0:0:755"
  ["/usr/local/bin/nyxus-start"]="0:0:755"
  ["/usr/local/bin/nyxus-greeter"]="0:0:755"
  ["/usr/local/bin/nyxus-hotkey"]="0:0:755"
  ["/usr/local/bin/nyxus-hub-apps"]="0:0:755"
  ["/usr/local/bin/nyxus-hub-close"]="0:0:755"
  ["/usr/local/bin/nyxus-hub-launch"]="0:0:755"
  ["/usr/local/bin/nyxus-hub-open"]="0:0:755"
  ["/usr/local/bin/nyxus-hub-search"]="0:0:755"
  ["/usr/local/bin/nyxus-kernel-switch"]="0:0:755"
  ["/usr/local/bin/nyxus-loginscreen"]="0:0:755"
  ["/usr/local/bin/nyxus-mac-randomize"]="0:0:755"
  ["/usr/local/bin/nyxus-mission"]="0:0:755"
  ["/usr/local/bin/nyxus-oath-register"]="0:0:755"
  ["/usr/local/bin/nyxus-pacman-toast"]="0:0:755"
  ["/usr/local/bin/nyxus-plymouth"]="0:0:755"
  ["/usr/local/bin/nyxus-protonup"]="0:0:755"
  ["/usr/local/bin/nyxus-qs"]="0:0:755"
  ["/usr/local/bin/nyxus-screensaver"]="0:0:755"
  ["/usr/local/bin/nyxus-secboot"]="0:0:755"
  ["/usr/local/bin/nyxus-session-start"]="0:0:755"
  ["/usr/local/bin/nyxus-set-wallpaper"]="0:0:755"
  ["/usr/local/bin/nyxus-shader"]="0:0:755"
  ["/usr/local/bin/nyxus-snap"]="0:0:755"
  ["/usr/local/bin/nyxus-sound"]="0:0:755"
  ["/usr/local/bin/nyxus-store-install"]="0:0:755"
  ["/usr/local/bin/nyxus-sync-stations"]="0:0:755"
  ["/usr/local/bin/nyxus-usbguard-helper"]="0:0:755"
  ["/usr/local/bin/nyxus-usbwatch-event"]="0:0:755"
  ["/usr/local/bin/nyxus-virt-setup"]="0:0:755"
  ["/usr/local/bin/nyxus-vpn"]="0:0:755"
  ["/usr/local/bin/nyxus-wallpaper-autostart"]="0:0:755"
  ["/usr/local/bin/nyxus-wallpaper-studio"]="0:0:755"
  ["/usr/local/bin/nyxus-workspace-wallpaperd"]="0:0:755"
  ["/usr/local/libexec/nyxus-account-helper"]="0:0:755"
  ["/usr/local/libexec/nyxus-backup-helper"]="0:0:755"
  ["/usr/local/libexec/nyxus-doctor-helper"]="0:0:755"
  ["/usr/local/libexec/nyxus-security-helper"]="0:0:755"
  ["/usr/local/libexec/nyxus-sound-system-default"]="0:0:755"
  ["/usr/local/libexec/nyxus-usbwatch-helper"]="0:0:755"
  ["/usr/local/sbin/nyxus-firstboot"]="0:0:755"
  # Bifrost (Master Hub) — staged by build-iso.sh's "stage NYXUS Master Hub"
  # step, same non-pacman-managed-file risk as everything else above.
  ["/usr/bin/bifrost"]="0:0:755"
  ["/usr/bin/bifrost-guardian"]="0:0:755"
  # Live-session sudoers drop-in: passwordless sudo for nyx user on the
  # live ISO ONLY. Calamares post-install removes /etc/sudoers.d/10-nyxus-live
  # so the installed system reverts to standard wheel + password.
  ["/etc/sudoers.d/10-nyxus-live"]="0:0:440"
  ["/etc/nyxus"]="0:0:755"
)
