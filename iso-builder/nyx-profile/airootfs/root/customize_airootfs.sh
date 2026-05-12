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
# EWW build (rev r9-eww-3 2026-05-11):
#   • v0.6.0 is the latest published tag (no v0.6.1/v0.6.2 exist).
#   • v0.6.0 ships a Cargo.lock with time-0.3.34, which fails to compile
#     against rustc ≥ 1.80 with E0282 (type-inference failure in
#     time::format_description::parse::mod::parse). This is a known
#     upstream-unfixed regression because EWW v0.6.0 was tagged in 2024.
#   • SOLUTION: run `cargo fetch` first to populate the registry cache,
#     then apply the EXACT one-line type annotation rustc's diagnostic
#     prints (`let items: Box<_> = format_items`), then build. This is
#     deterministic and doesn't depend on the dep resolver picking newer
#     versions or upstream re-publishing anything.
#   • Override NYXUS_EWW_TAG to track a different ref if v0.6.0 ever
#     becomes truly unbuildable (e.g. NYXUS_EWW_TAG=master).
#   • FAIL-FAST: waybar is gone; missing eww = no bar. Treat as a hard
#     ISO requirement (exit 1).
NYXUS_EWW_TAG="${NYXUS_EWW_TAG:-v0.6.0}"
if ! command -v eww >/dev/null 2>&1; then
  echo "[customize_airootfs] building eww ${NYXUS_EWW_TAG} from source..."
  _edir=$(mktemp -d)
  # ── time-0.3.34 E0282 patch ────────────────────────────────────────
  # Apply the rustc-suggested type annotation to every copy of
  # time-0.3.34 found in the cargo registry. Uses `find` instead of a
  # shell glob to be robust to non-standard CARGO_HOME locations and
  # multiple registry indexes.
  CARGO_HOME_REAL="${CARGO_HOME:-/root/.cargo}"
  # E0282 / E0283 fix per upstream rustc guidance. History of attempts:
  #   v1: annotate binding `let items: Box<_> = …` — rustc 1.80+ still
  #       fails because the turbofish kept `Box<_>` too.
  #   v2: rewrite to `Vec<_>` + `collect::<Result<_, _>>()?` — fixes
  #       the binding but exposes TWO new ambiguities: `.map(Into::into)`
  #       can't infer T, and the final `Ok(items.into())` matches
  #       multiple `From<Vec<_>> for OwnedFormatItem` impls.
  #   v3 (current): fully qualify BOTH conversions with the explicit
  #       `crate::format_description::OwnedFormatItem::from` path so
  #       inference has nothing left to guess. Element type on the
  #       binding is also spelled out for the same reason.
  #
  # Idempotent: the perl regex matches the raw upstream block AND the
  # earlier half-patched v2 block, so re-running on a partially-patched
  # tree is safe. The sentinel skip short-circuits a fully-patched file.
  PATCH_SENTINEL='Vec<crate::format_description::OwnedFormatItem>'  # post-patch line
  ORIG_REGEX='let items.* = format_items'                           # pre-patch line (matches raw + v2)
  patch_time_034() {
    local f changed=0
    while IFS= read -r f; do
      [ -f "$f" ] || continue
      if grep -q "$PATCH_SENTINEL" "$f"; then
        echo "[customize_airootfs] $f already patched (skipping)"
        changed=1; continue
      fi
      if grep -q "$ORIG_REGEX" "$f"; then
        chmod u+w "$f" 2>/dev/null || true
        # Multi-line block rewrite via perl -0777. Regex tolerates the
        # raw upstream form (`let items = … Result<Box<_>, _> … items.into()`)
        # AND the prior v2 partial form (`let items: Vec<_> = …
        # Result<_, _> … items.into()`) so re-runs on a partially-patched
        # tree converge to the v3 fully-qualified form.
        perl -i -0777 -pe '
          s{    let items(?::\s*Vec<_>)?\s*=\s*format_items\s*\n\s*\.map\(\|res\|\s*res\.map\(Into::into\)\)\s*\n\s*\.collect::<Result<(?:Box<_>|_)\s*,\s*_>>\(\)\?;\s*\n\s*Ok\(items\.into\(\)\)}
           {    let items: Vec<crate::format_description::OwnedFormatItem> = format_items\n        .map(|res| res.map(crate::format_description::OwnedFormatItem::from))\n        .collect::<Result<_, _>>()?;\n    Ok(crate::format_description::OwnedFormatItem::from(items))}s
        ' "$f"
        if grep -q "$PATCH_SENTINEL" "$f"; then
          echo "[customize_airootfs] patched $f for E0282/E0283 (fully-qualified OwnedFormatItem::from)"
          changed=1
        else
          echo "[customize_airootfs] WARN: perl rewrite did not land on $f — block text differs from expected"
        fi
      else
        echo "[customize_airootfs] WARN: $f does not contain expected line"
      fi
    done < <(find "$CARGO_HOME_REAL/registry/src" -type f \
                  -path '*/time-0.3.34/src/format_description/parse/mod.rs' 2>/dev/null)
    return $((1 - changed))   # 0 if anything was patched/already-patched
  }

  # Pre-extract every cached time-0.3.34.crate tarball into the matching
  # registry/src/<index>/ tree, write the .cargo-ok sentinel cargo uses
  # to mark a valid extraction, then patch. This bypasses cargo's lazy
  # extraction entirely — used as a fallback when warm-up extraction
  # didn't materialize the source tree for some reason.
  preextract_time_034() {
    local cache_dir tarball src_root extracted=0
    while IFS= read -r tarball; do
      cache_dir=$(dirname "$tarball")
      # cache and src dirs use the same <index> sub-directory name
      local idx
      idx=$(basename "$cache_dir")
      src_root="$CARGO_HOME_REAL/registry/src/$idx"
      mkdir -p "$src_root"
      if [ ! -d "$src_root/time-0.3.34" ]; then
        echo "[customize_airootfs] pre-extracting $tarball → $src_root/"
        tar -xzf "$tarball" -C "$src_root" || continue
        # Cargo recognises this empty file as proof of a clean extraction
        # and won't redo (or wipe) the work.
        touch "$src_root/time-0.3.34/.cargo-ok"
      fi
      extracted=1
    done < <(find "$CARGO_HOME_REAL/registry/cache" -type f -name 'time-0.3.34.crate' 2>/dev/null)
    [ "$extracted" = 1 ]
  }

  # Verify the patch landed on disk in EVERY extracted copy. Fails loudly
  # with a directory listing so we never silently fall through to a
  # broken build again.
  verify_time_034() {
    local f bad=0 found=0
    while IFS= read -r f; do
      found=1
      if ! grep -q "$PATCH_SENTINEL" "$f"; then
        echo "[customize_airootfs] FAIL: $f is NOT patched"
        bad=1
      fi
    done < <(find "$CARGO_HOME_REAL/registry/src" -type f \
                  -path '*/time-0.3.34/src/format_description/parse/mod.rs' 2>/dev/null)
    if [ "$found" = 0 ]; then
      echo "[customize_airootfs] verify: no time-0.3.34 source on disk (likely newer version in use — OK)"
      return 0
    fi
    [ "$bad" = 0 ]
  }

  build_eww() {
    cd "$_edir/eww" || return 1

    # Step 1: download dep tarballs into the cargo cache.
    echo "[customize_airootfs] step 1/5: cargo fetch..."
    cargo fetch || return 1

    # Step 2: warm-up build. Allowed to fail; purpose is to force cargo
    # to extract every dep into registry/src/. Output silenced because
    # it's noisy and not actionable on its own.
    echo "[customize_airootfs] step 2/5: warm-up build (failure expected at time-0.3.34)..."
    cargo build --release --no-default-features --features=wayland --offline >/dev/null 2>&1 || true

    # Step 3: patch the extracted time-0.3.34. If warm-up didn't extract
    # it for any reason, pre-extract the tarball ourselves and try again.
    echo "[customize_airootfs] step 3/5: patching time-0.3.34..."
    if ! patch_time_034; then
      echo "[customize_airootfs] no extracted time-0.3.34 found — pre-extracting from cache..."
      preextract_time_034 || true
      patch_time_034 || true
    fi

    # Step 4: hard verification. If any extracted copy is still
    # unpatched, dump diagnostics and bail BEFORE wasting time on a
    # final build that will definitely fail.
    echo "[customize_airootfs] step 4/5: verifying patch..."
    if ! verify_time_034; then
      echo "[customize_airootfs] ── DIAGNOSTICS ──"
      echo "[customize_airootfs] CARGO_HOME=$CARGO_HOME_REAL"
      find "$CARGO_HOME_REAL/registry" -maxdepth 4 -type d 2>/dev/null | head -20
      find "$CARGO_HOME_REAL/registry/src" -type f \
           -path '*/time-0.3.34/src/format_description/parse/mod.rs' 2>/dev/null \
        | while IFS= read -r f; do
            echo "[customize_airootfs] ── head of $f ──"
            sed -n '80,90p' "$f"
          done
      echo "[customize_airootfs] FATAL: time-0.3.34 patch could not be applied. Aborting."
      return 1
    fi

    # Step 5: real build. Cargo recompiles only the patched crate and
    # everything downstream — fast because warm-up cached the rest.
    echo "[customize_airootfs] step 5/5: final build..."
    cargo build --release --no-default-features --features=wayland --offline
  }
  if git clone --depth 1 --branch "${NYXUS_EWW_TAG}" \
        https://github.com/elkowar/eww.git "$_edir/eww" \
     && build_eww \
     && install -Dm755 "$_edir/eww/target/release/eww" /usr/local/bin/eww; then
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

# ── NYXUS Welcome Wizard staging (rev r9-eww 2026-05-11) ───────────────
# nyxus_welcome.py itself is staged into /opt/nyxus/ by build-iso.sh
# alongside the other nyxus_*.py modules. Here we install the three
# hand-written companion files that don't follow that pattern:
#   1. /usr/local/bin/nyxus-welcome           — gating launcher (marker check + flock)
#   2. /usr/local/libexec/nyxus-welcome-helper — privileged helper (root-only ops)
#   3. /usr/share/polkit-1/actions/dev.nyxus.welcome.policy
#
# Source files are copied into /root/ by mkarchiso (since they live under
# nyx-profile/airootfs/root/ — same path used by every other build asset).
# Each install block guards itself with `[ -f ]` and warns on miss.
if [ -f /root/nyxus-welcome ]; then
  install -Dm755 /root/nyxus-welcome           /usr/local/bin/nyxus-welcome
  echo "[customize_airootfs] installed /usr/local/bin/nyxus-welcome (overrides auto-generated wrapper)"
else
  echo "[customize_airootfs] WARNING: /root/nyxus-welcome not staged — wizard will not auto-run"
fi
if [ -f /root/nyxus-welcome-helper ]; then
  install -Dm755 -o root -g root /root/nyxus-welcome-helper /usr/local/libexec/nyxus-welcome-helper
  echo "[customize_airootfs] installed /usr/local/libexec/nyxus-welcome-helper"
else
  echo "[customize_airootfs] WARNING: /root/nyxus-welcome-helper not staged — wizard's privileged ops will fail"
fi
if [ -f /root/nyxus-welcome.policy ]; then
  install -Dm644 /root/nyxus-welcome.policy /usr/share/polkit-1/actions/dev.nyxus.welcome.policy
  echo "[customize_airootfs] installed polkit policy dev.nyxus.welcome"
else
  echo "[customize_airootfs] WARNING: /root/nyxus-welcome.policy not staged — pkexec will deny helper invocation"
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
