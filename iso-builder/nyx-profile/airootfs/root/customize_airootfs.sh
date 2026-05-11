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

# ── Build howdy (face authentication) from source ──────────────────────
# rev r1 — AUR-only PAM module that does IR-camera face match.  Runtime
# deps (python-opencv, python-dlib, v4l2loopback-dkms) are pulled in via
# packages.x86_64.  We install into /lib/security/howdy where the PAM
# rules in /etc/pam.d/sddm and /etc/pam.d/hyprlock expect to find pam.py.
# If the build fails (e.g. dlib model download blocked), the PAM line
# `auth sufficient pam_python.so /lib/security/howdy/pam.py` becomes a
# no-op (pam_python returns FAIL, control falls through to the next
# `sufficient` line) — fingerprint + passphrase still work.
if [ ! -f /lib/security/howdy/pam.py ]; then
  echo "[customize_airootfs] building howdy from source..."
  _hdir=$(mktemp -d)
  if git clone --depth 1 https://github.com/boltgolt/howdy.git "$_hdir/howdy" \
     && cd "$_hdir/howdy" \
     && ./debian/install.sh; then
    echo "[customize_airootfs] howdy installed → /lib/security/howdy/"
  else
    echo "[customize_airootfs] WARNING: howdy build failed — face auth disabled, fingerprint + passphrase still work"
    # Drop a no-op pam.py so the PAM rule doesn't error every boot.
    mkdir -p /lib/security/howdy
    cat > /lib/security/howdy/pam.py <<'PYEOF'
def pam_sm_authenticate(pamh, flags, args):
    return 7  # PAM_AUTH_ERR — falls through to next sufficient rule
def pam_sm_setcred(pamh, flags, args):
    return 0
PYEOF
  fi
  cd / && rm -rf "$_hdir"
fi

# ── NYXUS auth helpers: permissions + runtime directories ──────────────
# Ghost-auth (zero-width password verifier), ghost-register, backdoor
# router, and audit logger all live in /usr/local/bin and need to be
# executable + owned by root.
for _bin in /usr/local/bin/nyxus-ghost-auth \
            /usr/local/bin/nyxus-ghost-register \
            /usr/local/bin/nyxus-bd-router \
            /usr/local/bin/nyxus-bd-detect \
            /usr/local/bin/nyxus-backdoor-log \
            /usr/local/bin/nyxus-oath-register; do
  if [ -f "$_bin" ]; then
    chown root:root "$_bin"
    chmod 755 "$_bin"
  fi
done

# Secure storage for the ghost-password hash and the U2F mapping file.
# Both are root-only so even the live `nyx` user cannot read them.
mkdir -p /etc/nyxus
chown root:root /etc/nyxus
chmod 700 /etc/nyxus

# Empty u2f_keys placeholder so pam_u2f doesn't error on first boot before
# the user runs `pamu2fcfg > /etc/nyxus/u2f_keys` to register a YubiKey.
# The backdoor stack will simply deny until a real key is registered.
if [ ! -f /etc/nyxus/u2f_keys ]; then
  : > /etc/nyxus/u2f_keys
  chmod 600 /etc/nyxus/u2f_keys
fi

# Audit log directory (root-only)
mkdir -p /var/log/nyxus
chown root:root /var/log/nyxus
chmod 700 /var/log/nyxus

# ── Enable display + network + hardware services on the LIVE ISO ───────
# These are also re-enabled by nyxus-postinstall on the installed system,
# but enabling them in the live image means hardware works for live demos.
systemctl enable sddm.service                2>/dev/null || true
systemctl enable NetworkManager.service      2>/dev/null || true
systemctl enable systemd-timesyncd.service   2>/dev/null || true
systemctl enable bluetooth.service           2>/dev/null || true
systemctl enable thermald.service            2>/dev/null || true
systemctl enable power-profiles-daemon.service 2>/dev/null || true
systemctl enable acpid.service               2>/dev/null || true
systemctl enable cups.service                2>/dev/null || true
systemctl enable fstrim.timer                2>/dev/null || true
# NVIDIA suspend/resume hooks ship with nvidia-utils ≥435
systemctl enable nvidia-suspend.service      2>/dev/null || true
systemctl enable nvidia-resume.service       2>/dev/null || true
systemctl enable nvidia-hibernate.service    2>/dev/null || true
