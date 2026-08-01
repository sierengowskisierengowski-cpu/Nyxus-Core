#!/usr/bin/env bash
# ============================================
# NYXUS
# Copyright © 2026 Joseph A. Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
#
# archiso profile definition for the NYX ISO.
# See: https://wiki.archlinux.org/title/Archiso

iso_name="nyxus"
iso_label="NYXUS_2026_07"
iso_publisher="Joseph A. Sierengowski <https://github.com/sierengowski/NyX.OS-V1>"
iso_application="NYXUS Live/Install"
iso_version="2026.07.22"
install_dir="arch"
buildmodes=('iso')
bootmodes=(
  'bios.syslinux'
  'uefi.grub'
)
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
# ── SQUASHFS COMPRESSION — zstd, NOT xz (changed 2026-07-30) ─────────────────
# archiso's stock releng profile uses xz, and so did every NYXUS ISO up to and
# including 2026.07.29. That default is written for a ~1GB installer image.
# NYXUS's airootfs is 7.3GB, and xz decode cost is paid on EVERY cold read for
# the whole life of the live session.
#
# MEASURED on this builder box, same 2140MB of the real 07.29 image
# (/usr/bin + /usr/lib/systemd), single-threaded unsquashfs, warm page cache
# so USB I/O is excluded and only decode cost is compared:
#
#     -comp xz  -Xbcj x86 -b 1M -Xdict-size 1M   647.0 MB   29.5 s   ( 72 MB/s)
#     -comp zstd -Xcompression-level 19 -b 1M    716.7 MB    3.9 s   (549 MB/s)
#
# => 7.6x faster reads for +10.8% image size (whole ISO ~8.06GB -> ~8.9GB).
# Per 1MiB squashfs block that is ~14.5ms of CPU under xz vs ~1.9ms under zstd,
# and squashfs must inflate a WHOLE block to serve a single 4KiB read — so a
# desktop session start, which touches thousands of scattered small files,
# spends most of its time inflating. This is the dominant cause of the "eww
# takes minutes to appear / everything loads slowly" reports on the 07.29 stick.
#
# To bake the old xz image: `sudo NYX_SQUASH_COMP=xz ./build-iso.sh`
# (build-iso.sh rewrites this line in the staged profile copy).
airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '19' '-b' '1M')
bootstrap_tarball_compression=(zstd -c -T0 --auto-threads=logical --long -19)
file_permissions=(
  ["/root"]="0:0:750"
  ["/root/customize_airootfs.sh"]="0:0:755"
  # Auto-regenerated 2026-07-24 from airootfs (W1 pre-bake audit).
  # archiso squashfs only preserves perms listed here — every executable under
  # /usr/local/{bin,libexec,sbin}, /etc/nyxus-firstboot.d, bifrost, and live
  # sudoers MUST appear. Re-run the regen in HANDOFF if you add launchers.
  ["/usr/local/bin/arsenal"]="0:0:755"
  ["/usr/local/bin/arsenal-hub"]="0:0:755"
  ["/usr/local/bin/jeTT"]="0:0:755"
  ["/usr/local/bin/jett"]="0:0:755"
  ["/usr/local/bin/meli"]="0:0:755"
  ["/usr/local/bin/nyxus"]="0:0:755"
  ["/usr/local/bin/nyxus-accent-from-wallpaper"]="0:0:755"
  ["/usr/local/bin/nyxus-account"]="0:0:755"
  ["/usr/local/bin/nyxus-app-shell"]="0:0:755"
  ["/usr/local/bin/nyxus-apply-accent"]="0:0:755"
  ["/usr/local/bin/nyxus-backdoor-log"]="0:0:755"
  ["/usr/local/bin/nyxus-backup"]="0:0:755"
  ["/usr/local/bin/nyxus-bar-plugins"]="0:0:755"
  ["/usr/local/bin/nyxus-battery"]="0:0:755"
  ["/usr/local/bin/nyxus-bd-detect"]="0:0:755"
  ["/usr/local/bin/nyxus-bd-router"]="0:0:755"
  ["/usr/local/bin/nyxus-beat"]="0:0:755"
  ["/usr/local/bin/nyxus-beatd"]="0:0:755"
  ["/usr/local/bin/nyxus-blackarch-full"]="0:0:755"
  ["/usr/local/bin/nyxus-boot-check"]="0:0:755"
  ["/usr/local/bin/nyxus-bootstrap"]="0:0:755"
  ["/usr/local/bin/nyxus-c2"]="0:0:755"
  ["/usr/local/bin/nyxus-clipboard"]="0:0:755"
  ["/usr/local/bin/nyxus-companion"]="0:0:755"
  ["/usr/local/bin/nyxus-context-menu.sh"]="0:0:755"
  ["/usr/local/bin/nyxus-control"]="0:0:755"
  ["/usr/local/bin/nyxus-crash-report"]="0:0:755"
  ["/usr/local/bin/nyxus-crashd"]="0:0:755"
  ["/usr/local/bin/nyxus-desktop"]="0:0:755"
  ["/usr/local/bin/nyxus-distrobox-helper"]="0:0:755"
  ["/usr/local/bin/nyxus-dock"]="0:0:755"
  ["/usr/local/bin/nyxus-doctor"]="0:0:755"
  ["/usr/local/bin/nyxus-doh"]="0:0:755"
  ["/usr/local/bin/nyxus-drop"]="0:0:755"
  ["/usr/local/bin/nyxus-dynamic-wallpaper.sh"]="0:0:755"
  ["/usr/local/bin/nyxus-eww-cinematic"]="0:0:755"
  ["/usr/local/bin/nyxus-eww-launch"]="0:0:755"
  ["/usr/local/bin/nyxus-eww-launch-safe"]="0:0:755"
  ["/usr/local/bin/nyxus-files"]="0:0:755"
  ["/usr/local/bin/nyxus-focusmode"]="0:0:755"
  ["/usr/local/bin/nyxus-freeform"]="0:0:755"
  ["/usr/local/bin/nyxus-gamemode"]="0:0:755"
  ["/usr/local/bin/nyxus-gen-backdrop"]="0:0:755"
  ["/usr/local/bin/nyxus-ghost"]="0:0:755"
  ["/usr/local/bin/nyxus-ghost-auth"]="0:0:755"
  ["/usr/local/bin/nyxus-ghost-helper"]="0:0:755"
  ["/usr/local/bin/nyxus-ghost-register"]="0:0:755"
  ["/usr/local/bin/nyxus-glow"]="0:0:755"
  ["/usr/local/bin/nyxus-godsapp"]="0:0:755"
  ["/usr/local/bin/nyxus-graffiti-wall"]="0:0:755"
  ["/usr/local/bin/nyxus-greeter"]="0:0:755"
  ["/usr/local/bin/nyxus-hacker-mode"]="0:0:755"
  ["/usr/local/bin/nyxus-home"]="0:0:755"
  ["/usr/local/bin/nyxus-honeypot-firewall"]="0:0:755"
  ["/usr/local/bin/nyxus-hotkey"]="0:0:755"
  ["/usr/local/bin/nyxus-hub-apps"]="0:0:755"
  ["/usr/local/bin/nyxus-hub-close"]="0:0:755"
  ["/usr/local/bin/nyxus-hub-launch"]="0:0:755"
  ["/usr/local/bin/nyxus-hub-open"]="0:0:755"
  ["/usr/local/bin/nyxus-hub-search"]="0:0:755"
  ["/usr/local/bin/nyxus-install"]="0:0:755"
  ["/usr/local/bin/nyxus-intel"]="0:0:755"
  ["/usr/local/bin/nyxus-kernel-switch"]="0:0:755"
  ["/usr/local/bin/nyxus-launcher"]="0:0:755"
  ["/usr/local/bin/nyxus-lens"]="0:0:755"
  ["/usr/local/bin/nyxus-live-wallpaper"]="0:0:755"
  ["/usr/local/bin/nyxus-livewall-flagship"]="0:0:755"
  ["/usr/local/bin/nyxus-livewall-generate"]="0:0:755"
  ["/usr/local/bin/nyxus-living"]="0:0:755"
  ["/usr/local/bin/nyxus-lock-art"]="0:0:755"
  ["/usr/local/bin/nyxus-lock-track"]="0:0:755"
  ["/usr/local/bin/nyxus-loginscreen"]="0:0:755"
  ["/usr/local/bin/nyxus-mac-randomize"]="0:0:755"
  ["/usr/local/bin/nyxus-mission"]="0:0:755"
  ["/usr/local/bin/nyxus-mission-control-toggle"]="0:0:755"
  ["/usr/local/bin/nyxus-mood"]="0:0:755"
  ["/usr/local/bin/nyxus-netusage"]="0:0:755"
  ["/usr/local/bin/nyxus-notepad"]="0:0:755"
  ["/usr/local/bin/nyxus-notes"]="0:0:755"
  ["/usr/local/bin/nyxus-notif-to-eww"]="0:0:755"
  ["/usr/local/bin/nyxus-notifications"]="0:0:755"
  ["/usr/local/bin/nyxus-nowplaying"]="0:0:755"
  ["/usr/local/bin/nyxus-oath-register"]="0:0:755"
  ["/usr/local/bin/nyxus-pacman-toast"]="0:0:755"
  ["/usr/local/bin/nyxus-palette-extract"]="0:0:755"
  ["/usr/local/bin/nyxus-panic"]="0:0:755"
  ["/usr/local/bin/nyxus-passwords"]="0:0:755"
  ["/usr/local/bin/nyxus-persist-login"]="0:0:755"
  ["/usr/local/bin/nyxus-plugins"]="0:0:755"
  ["/usr/local/bin/nyxus-plymouth"]="0:0:755"
  ["/usr/local/bin/nyxus-plymouth-install"]="0:0:755"
  ["/usr/local/bin/nyxus-postinstall"]="0:0:755"
  ["/usr/local/bin/nyxus-powermenu"]="0:0:755"
  ["/usr/local/bin/nyxus-protonup"]="0:0:755"
  ["/usr/local/bin/nyxus-pulsed"]="0:0:755"
  ["/usr/local/bin/nyxus-qs"]="0:0:755"
  ["/usr/local/bin/nyxus-record"]="0:0:755"
  ["/usr/local/bin/nyxus-rotate-walls"]="0:0:755"
  ["/usr/local/bin/nyxus-sage"]="0:0:755"
  ["/usr/local/bin/nyxus-screensaver"]="0:0:755"
  ["/usr/local/bin/nyxus-screenshot"]="0:0:755"
  ["/usr/local/bin/nyxus-secboot"]="0:0:755"
  ["/usr/local/bin/nyxus-security"]="0:0:755"
  ["/usr/local/bin/nyxus-sense"]="0:0:755"
  ["/usr/local/bin/nyxus-session-start"]="0:0:755"
  ["/usr/local/bin/nyxus-set-grub-default-kage"]="0:0:755"
  ["/usr/local/bin/nyxus-set-wallpaper"]="0:0:755"
  ["/usr/local/bin/nyxus-set-wallpaper.sh"]="0:0:755"
  ["/usr/local/bin/nyxus-settings"]="0:0:755"
  ["/usr/local/bin/nyxus-setup-apps"]="0:0:755"
  ["/usr/local/bin/nyxus-sfx"]="0:0:755"
  ["/usr/local/bin/nyxus-shader"]="0:0:755"
  ["/usr/local/bin/nyxus-shield"]="0:0:755"
  ["/usr/local/bin/nyxus-snap"]="0:0:755"
  ["/usr/local/bin/nyxus-sound"]="0:0:755"
  ["/usr/local/bin/nyxus-sound-bake"]="0:0:755"
  ["/usr/local/bin/nyxus-sound-forge"]="0:0:755"
  ["/usr/local/bin/nyxus-sound.sh"]="0:0:755"
  ["/usr/local/bin/nyxus-soundd"]="0:0:755"
  ["/usr/local/bin/nyxus-sounds"]="0:0:755"
  ["/usr/local/bin/nyxus-spray"]="0:0:755"
  ["/usr/local/bin/nyxus-start"]="0:0:755"
  ["/usr/local/bin/nyxus-stickies"]="0:0:755"
  ["/usr/local/bin/nyxus-store"]="0:0:755"
  ["/usr/local/bin/nyxus-store-install"]="0:0:755"
  ["/usr/local/bin/nyxus-studio"]="0:0:755"
  ["/usr/local/bin/nyxus-supernova"]="0:0:755"
  ["/usr/local/bin/nyxus-sync-stations"]="0:0:755"
  ["/usr/local/bin/nyxus-sysmon"]="0:0:755"
  ["/usr/local/bin/nyxus-terminal"]="0:0:755"
  ["/usr/local/bin/nyxus-tint"]="0:0:755"
  ["/usr/local/bin/nyxus-threatd"]="0:0:755"
  ["/usr/local/bin/nyxus-tintd"]="0:0:755"
  ["/usr/local/bin/nyxus-tour"]="0:0:755"
  ["/usr/local/bin/nyxus-updater"]="0:0:755"
  ["/usr/local/bin/nyxus-usbguard-helper"]="0:0:755"
  ["/usr/local/bin/nyxus-usbwatch-event"]="0:0:755"
  ["/usr/local/bin/nyxus-virt-setup"]="0:0:755"
  ["/usr/local/bin/nyxus-voice"]="0:0:755"
  ["/usr/local/bin/nyxus-voice-install"]="0:0:755"
  ["/usr/local/bin/nyxus-voice-model"]="0:0:755"
  ["/usr/local/bin/nyxus-voiced"]="0:0:755"
  ["/usr/local/bin/nyxus-vpn"]="0:0:755"
  ["/usr/local/bin/nyxus-wait-bootstrap"]="0:0:755"
  ["/usr/local/bin/nyxus-webapp"]="0:0:755"
  ["/usr/local/bin/nyxus-wall-cycle"]="0:0:755"
  ["/usr/local/bin/nyxus-wall-fx"]="0:0:755"
  ["/usr/local/bin/nyxus-wall-next"]="0:0:755"
  ["/usr/local/bin/nyxus-wallpaper-autostart"]="0:0:755"
  ["/usr/local/bin/nyxus-wallpaper-studio"]="0:0:755"
  ["/usr/local/bin/nyxus-weather"]="0:0:755"
  ["/usr/local/bin/nyxus-weather-line"]="0:0:755"
  ["/usr/local/bin/nyxus-welcome"]="0:0:755"
  ["/usr/local/bin/nyxus-welcome-helper"]="0:0:755"
  ["/usr/local/bin/nyxus-welcome-note"]="0:0:755"
  ["/usr/local/bin/nyxus-dream"]="0:0:755"
  ["/usr/local/bin/nyxus-whispers"]="0:0:755"
  ["/usr/local/bin/nyxus-workspace-wallpaperd"]="0:0:755"
  ["/usr/local/bin/scripts/jett-ctl.sh"]="0:0:755"
  ["/usr/local/bin/wallpaper-rotate"]="0:0:755"
  ["/usr/local/libexec/nyxus-account-helper"]="0:0:755"
  ["/usr/local/libexec/nyxus-backup-helper"]="0:0:755"
  ["/usr/local/libexec/nyxus-doctor-helper"]="0:0:755"
  ["/usr/local/libexec/nyxus-parental-helper"]="0:0:755"
  ["/usr/local/libexec/nyxus-security-helper"]="0:0:755"
  ["/usr/local/libexec/nyxus-sound-system-default"]="0:0:755"
  ["/usr/local/libexec/nyxus-usbwatch-helper"]="0:0:755"
  ["/usr/local/libexec/nyxus-welcome-helper"]="0:0:755"
  ["/usr/local/sbin/nyxus-firstboot"]="0:0:755"
  ["/etc/nyxus-firstboot.d/01-machine-id.sh"]="0:0:755"
  ["/etc/nyxus-firstboot.d/02-xdg-user-dirs.sh"]="0:0:755"
  ["/etc/nyxus-firstboot.d/03-mime-defaults.sh"]="0:0:755"
  ["/etc/nyxus-firstboot.d/04-welcome.sh"]="0:0:755"
  ["/etc/nyxus-firstboot.d/05-icon-cache.sh"]="0:0:755"
  ["/etc/nyxus-firstboot.d/06-honeypot-stack.sh"]="0:0:755"
  ["/usr/bin/bifrost"]="0:0:755"
  ["/usr/bin/bifrost-guardian"]="0:0:755"
  ["/etc/sudoers.d/10-nyxus-live"]="0:0:440"
  ["/etc/nyxus"]="0:0:755"
)
