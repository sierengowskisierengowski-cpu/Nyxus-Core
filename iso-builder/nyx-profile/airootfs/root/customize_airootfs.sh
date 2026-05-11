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

# ── Build EWW (ElKowar's Wacky Widgets) from source ────────────────────
# rev r2 — widget toolkit (replaces the now-removed waybar) — built from
# 2026-05-11. Build deps (rust, cargo) are pulled in transiently below.
# Runtime deps (gtk-layer-shell, socat, jq, acpi) are in packages.x86_64.
#
# PINNED to a known-good upstream release tag so the ISO build is
# reproducible and not vulnerable to upstream HEAD breakage / supply
# chain surprises. Bump NYXUS_EWW_TAG when you've verified a newer tag.
#
# `cargo update -p time@0.3.34 --precise 0.3.37` bumps the broken time
# crate pinned in EWW v0.6.0's Cargo.lock. Version 0.3.34 has a type-
# inference bug (E0282) that breaks against rustc 1.80+. The qualifier
# is required because EWW also depends on legacy time 0.1.45 (via
# chrono), so unqualified `cargo update -p time` is ambiguous.
#
# FAIL-FAST: since waybar has been removed, a missing eww binary leaves
# the system with NO bar/widget stack at all. Treat the build as a hard
# ISO requirement.
NYXUS_EWW_TAG="${NYXUS_EWW_TAG:-v0.6.0}"
if ! command -v eww >/dev/null 2>&1; then
  echo "[customize_airootfs] building eww ${NYXUS_EWW_TAG} from source..."
  # rust/cargo are pacstrapped via packages.x86_64 — the chroot has no
  # mirrors, so we can't `pacman -S` here.
  _edir=$(mktemp -d)
  if git clone --depth 1 --branch "${NYXUS_EWW_TAG}" \
        https://github.com/elkowar/eww.git "$_edir/eww" \
     && cd "$_edir/eww" \
     && cargo update -p time@0.3.34 --precise 0.3.37 \
     && cargo build --release --no-default-features --features=wayland \
     && install -Dm755 target/release/eww /usr/local/bin/eww; then
    echo "[customize_airootfs] eww installed → $(command -v eww)"
    cd / && rm -rf "$_edir"
  else
    echo "[customize_airootfs] FATAL: eww ${NYXUS_EWW_TAG} build failed."
    echo "[customize_airootfs] waybar has been removed; the ISO would ship without any bar."
    echo "[customize_airootfs] Override NYXUS_EWW_TAG or fix the build before re-running mkarchiso."
    cd / && rm -rf "$_edir"
    exit 1
  fi
fi

# ── Make all EWW helper scripts executable ─────────────────────────────
if [ -d /etc/skel/.config/eww/scripts ]; then
  chmod +x /etc/skel/.config/eww/scripts/*.sh 2>/dev/null || true
fi

# ── Build wlogout from upstream source ─────────────────────────────────
# rev r1 (2026-05-11) — wlogout was failing pacstrap on mirrors that
# don't carry it in extra. Build from upstream so the ISO doesn't depend
# on mirror state. Bound to Super+Shift+E; if missing, user can still
# log out via the EWW powermenu, so this is fail-TOLERANT (warn, not
# fatal).
if ! command -v wlogout >/dev/null 2>&1; then
  echo "[customize_airootfs] building wlogout from source..."
  # scdoc + gtk-layer-shell are pacstrapped via packages.x86_64; gtk3 is
  # pulled in transitively by hyprland/gtk-layer-shell. No in-chroot
  # pacman call is possible (chroot mirrorlist is empty).
  _wdir=$(mktemp -d)
  if git clone --depth 1 https://github.com/ArtsyMacaw/wlogout.git "$_wdir/wlogout" \
     && cd "$_wdir/wlogout" \
     && meson setup build --prefix=/usr \
     && ninja -C build \
     && ninja -C build install; then
    echo "[customize_airootfs] wlogout installed → $(command -v wlogout)"
  else
    echo "[customize_airootfs] WARNING: wlogout build failed — Super+Shift+E will be a no-op; use EWW powermenu instead"
  fi
  cd / && rm -rf "$_wdir"
fi

# ── Build pamtester from upstream source (AUR equivalent) ──────────────
# rev r1 (2026-05-11) — used at runtime by nyxus-bd-router for U2F PIN
# verification via PAM conversation. AUR-only, so we build from upstream
# autotools tarball. Fail-TOLERANT: if the build fails, the backdoor
# U2F factor degrades to deny-only, but normal sddm + hyprlock auth is
# unaffected.
if ! command -v pamtester >/dev/null 2>&1; then
  echo "[customize_airootfs] building pamtester from source..."
  _pdir=$(mktemp -d)
  if curl -fsSL "https://downloads.sourceforge.net/project/pamtester/pamtester/0.1.2/pamtester-0.1.2.tar.gz" \
        -o "$_pdir/pamtester.tar.gz" \
     && tar -xzf "$_pdir/pamtester.tar.gz" -C "$_pdir" \
     && cd "$_pdir/pamtester-0.1.2" \
     && ./configure --prefix=/usr \
     && make \
     && make install; then
    echo "[customize_airootfs] pamtester installed → $(command -v pamtester)"
  else
    echo "[customize_airootfs] WARNING: pamtester build failed — nyxus-bd-router U2F factor will deny-only"
  fi
  cd / && rm -rf "$_pdir"
fi

# ── Build howdy (face authentication) from source ──────────────────────
# rev r2 — AUR-only PAM module that does IR-camera face match.  Runtime
# deps: python-opencv + v4l2loopback-dkms come from packages.x86_64;
# python-dlib is pulled in by howdy's own ./debian/install.sh (since it
# is AUR-only and was failing pacstrap).  We install into /lib/security/howdy where the PAM
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
