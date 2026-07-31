#!/usr/bin/env bash
# ============================================
# NYXUS — NYXUS Live ISO
# Copyright © 2026 Joseph A. Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
#
# build-iso.sh — bakes the NYX ISO from this archiso profile.
# Must run as root on an Arch Linux host with archiso installed.
#
# Usage:
#   sudo ./build-iso.sh
#
# Output:
#   ./out/NYXUS Live ISO
set -euo pipefail

# Colours
B=$'\e[1m'; R=$'\e[0m'
PINK=$'\e[38;5;201m'; CYAN=$'\e[38;5;51m'
GOLD=$'\e[38;5;220m'; PURPLE=$'\e[38;5;177m'

step() { printf "\n${PURPLE}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${CYAN}✓${R}  %s\n" "$*"; }
warn() { printf "  ${GOLD}!${R}  %s\n" "$*"; }
fail() { printf "  ${PINK}✗${R}  %s\n" "$*" >&2; }

# ── ISO version (auto-dated) ─────────────────────────────────────────────
# Default = today's date in YYYY.MM.DD; override with NYX_ISO_DATE env var
# for deterministic re-bakes (e.g. NYX_ISO_DATE=2026.05.11 sudo ./build-iso.sh).
ISO_DATE="${NYX_ISO_DATE:-$(date +%Y.%m.%d)}"
ISO_NAME="nyxus-${ISO_DATE}-x86_64.iso"

TARBALL_URL="https://nyxus-core.replit.app/api/download/nyxus/nyxus-intel.tgz"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# The COMMITTED profile in the repo. This is READ-ONLY during a bake — the
# bake never mutates it in place (see PROFILE_DIR below).
REPO_PROFILE="${SCRIPT_DIR}/nyx-profile"
# The bake stages heavily into the profile's airootfs as root (chrome layer,
# app builds, kage-ryu activation files, os-release, package list, pacman.conf).
# Doing that on the repo tree corrupted it every run (root-owned files + ~327
# deletions → a wrecked working tree needing a sudo chown to recover). So the
# bake now works on a THROWAWAY COPY under /var/tmp: the repo profile stays
# pristine no matter what the bake does, and the copy is deleted on exit.
PROFILE_DIR="${NYX_PROFILE_WORK:-/var/tmp/nyxus-profile-bake}"
WORK_DIR="${NYX_WORK_DIR:-/var/tmp/nyxus-work}"
OUT_DIR="${SCRIPT_DIR}/out"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# ── preflight ────────────────────────────────────────────────────────────
step "preflight"
if [[ $EUID -ne 0 ]]; then
  fail "must be run as root"; exit 1
fi
if [[ ! -f /etc/arch-release ]]; then
  fail "this script must run on Arch Linux (mkarchiso requires it)"; exit 1
fi

# ── bake from a throwaway copy of the profile (repo stays pristine) ───────
# Everything below this point uses ${PROFILE_DIR}, which is the /var/tmp copy,
# NOT the committed repo tree (${REPO_PROFILE}). This is the single guarantee
# that a bake can never again corrupt the repo profile.
if [[ ! -d "${REPO_PROFILE}" ]]; then
  fail "committed profile not found at ${REPO_PROFILE}"; exit 1
fi
step "staging a throwaway profile copy → ${PROFILE_DIR}"
rm -rf "${PROFILE_DIR}"
mkdir -p "$(dirname "${PROFILE_DIR}")"
cp -a "${REPO_PROFILE}" "${PROFILE_DIR}" || { fail "failed to copy profile to ${PROFILE_DIR}"; exit 1; }
ok "profile copied — repo tree ${REPO_PROFILE} will not be touched by this bake"

# ── auto-install required host packages ─────────────────────────────────
# rev r24 (2026-05-18) — self-healing preflight: every tool mkarchiso
# needs to bake a UEFI+BIOS ISO is installed here in one shot so the user
# never has to play whack-a-mole with "X not found" failures.
# rev r25 (2026-07-21) — added jq (workspaces.json generation), python
# (host-side tamper-manifest hashing + inline helpers), curl (tarball
# fallback download) and rsync (meli app staging) — this script invokes
# them directly and none of archiso's own dependencies pull them in, so a
# bare `archlinux:latest` + archiso host was failing with "command not
# found" mid-bake.
HOST_DEPS=(archiso squashfs-tools libisoburn dosfstools grub mtools edk2-ovmf jq python curl rsync)
MISSING_DEPS=()
for pkg in "${HOST_DEPS[@]}"; do
  if ! pacman -Q "${pkg}" >/dev/null 2>&1; then
    MISSING_DEPS+=("${pkg}")
  fi
done
if (( ${#MISSING_DEPS[@]} > 0 )); then
  step "installing missing host packages: ${MISSING_DEPS[*]}"
  pacman -Sy --needed --noconfirm "${MISSING_DEPS[@]}" || {
    fail "failed to install host packages: ${MISSING_DEPS[*]}"; exit 1; }
  ok "host packages installed"
fi

# ── strip any leftover chaotic-aur config from prior bakes ──────────────
# NYX no longer uses chaotic-aur — the greeter is `agreety` (built into
# the `greetd` package in official Arch `extra`), so no AUR access is
# needed. Earlier bake attempts may have appended a [chaotic-aur] block
# to the profile pacman.conf; strip it idempotently so the build chroot
# does not try to resolve from a repo that may be unreachable.
PROFILE_PACMAN="${PROFILE_DIR}/pacman.conf"
if [[ -f "${PROFILE_PACMAN}" ]] && grep -q "^\[chaotic-aur\]" "${PROFILE_PACMAN}"; then
  awk '
    /^\[chaotic-aur\]/ { skip=1; next }
    skip && /^\[/      { skip=0 }
    !skip              { print }
  ' "${PROFILE_PACMAN}" > "${PROFILE_PACMAN}.tmp" && mv "${PROFILE_PACMAN}.tmp" "${PROFILE_PACMAN}"
  ok "stripped legacy chaotic-aur block from profile pacman.conf"
fi

# Final sanity: mkarchiso must now exist.
if ! command -v mkarchiso >/dev/null 2>&1; then
  fail "mkarchiso still not found after install — aborting"; exit 1
fi
ok "running on Arch as root with mkarchiso available"
ok "iso version: ${ISO_DATE} → ${ISO_NAME}"

# ── clean up the throwaway profile copy on exit ──────────────────────────
# The bake works entirely on ${PROFILE_DIR} (a /var/tmp copy of the committed
# repo profile — see the copy step in preflight), so there is nothing in the
# repo to "restore" anymore: the repo tree is never mutated. All this does now
# is delete the throwaway copy on ANY exit (success or mid-run death) so it
# doesn't accumulate. Set NYX_KEEP_PROFILE_WORK=1 to keep it for debugging.
_nyx_restore_profile() {
  if [[ "${NYX_KEEP_PROFILE_WORK:-0}" != "1" ]]; then
    rm -rf "${PROFILE_DIR}"
  fi
  return 0
}
trap _nyx_restore_profile EXIT

# ── lean ISO tier (optional) ─────────────────────────────────────────────
NYX_ISO_TIER="${NYX_ISO_TIER:-full}"
if [[ "${NYX_ISO_TIER}" == "lean" && -f "${PROFILE_DIR}/packages.x86_64.lean" ]]; then
  cp "${PROFILE_DIR}/packages.x86_64" "${PROFILE_DIR}/packages.x86_64.bake.bak"
  cp "${PROFILE_DIR}/packages.x86_64.lean" "${PROFILE_DIR}/packages.x86_64"
  ok "NYX_ISO_TIER=lean — using packages.x86_64.lean"
fi

# ── Kage Ryu Nyxus custom kernel (DEFAULT — rev 2026-07-23) ──────────────
# NYXUS ships the operator's own linux-kage-ryu security kernel as the
# PRIMARY/default boot kernel — on the live USB (so you validate the real
# kernel before installing) AND on the installed system. Stock `linux` is
# kept purely as a RESCUE entry so a bad custom-kernel boot can never strand
# you. This block also rewrites the three live boot menus so Kage-Ryu is
# entry #0 and stock is a clearly-labelled rescue (throwaway copy only — the
# repo's static menus stay stock-safe, so any failure falls back to a
# bootable stock ISO, never a brick).
#
# ON BY DEFAULT (NYX_WITH_KAGE_RYU=1). Set NYX_WITH_KAGE_RYU=0 to opt OUT and
# bake a stock-only ISO (dev/debug). The kernel is NOT in any Arch repo and
# is a multi-GB, long compile, so it is NEVER built inside this script — you
# build the package once (see kernel/README.md + kernel/install-kage-ryu.sh,
# or `cd <kage-ryu repo> && makepkg -sc`); the bake then hard-fails if the
# prebuilt packages are missing (so it can never silently ship kernel-less).
#
# It looks for the prebuilt linux-kage-ryu + headers packages under
# NYX_KAGE_PKGDIR (default ~/Projects/arch-custom-kernel/linux-kage-ryu),
# stages them into a profile-local [nyxus-local] pacman repo, wires that repo
# into the build pacman.conf, and appends the two packages to the bake's
# package list. All of that is undone on exit by _nyx_restore_profile.
if [[ "${NYX_WITH_KAGE_RYU:-1}" == "1" ]]; then
  step "Kage Ryu Nyxus custom kernel (default — primary boot kernel)"
  # Under `sudo` $HOME is /root; the kernel package was built in the invoking
  # user's home. Look there by default so the bake finds it without needing
  # NYX_KAGE_PKGDIR set explicitly.
  _kage_home="$(getent passwd "${SUDO_USER:-root}" | cut -d: -f6)"; _kage_home="${_kage_home:-$HOME}"
  KAGE_PKGDIR="${NYX_KAGE_PKGDIR:-${_kage_home}/Projects/arch-custom-kernel/linux-kage-ryu}"
  LOCAL_REPO="${SCRIPT_DIR}/local-repo"
  _kage_main="$(ls -t "${KAGE_PKGDIR}"/linux-kage-ryu-[0-9]*.pkg.tar.zst 2>/dev/null | head -1 || true)"
  _kage_hdr="$(ls -t "${KAGE_PKGDIR}"/linux-kage-ryu-headers-*.pkg.tar.zst 2>/dev/null | head -1 || true)"
  if [[ -z "${_kage_main}" || -z "${_kage_hdr}" ]]; then
    fail "NYX_WITH_KAGE_RYU=1 but no prebuilt kernel packages found in ${KAGE_PKGDIR}"
    fail "build them first (kernel is never compiled inside the bake):"
    fail "  sudo kernel/install-kage-ryu.sh      # builds + installs on THIS host"
    fail "  # or, to only produce the packages:  cd <kage-ryu repo> && makepkg -sc"
    fail "then re-run:  NYX_WITH_KAGE_RYU=1 sudo ./build-iso.sh"
    fail "(or set NYX_KAGE_PKGDIR=/dir/with/linux-kage-ryu-*.pkg.tar.zst)"
    exit 1
  fi
  mkdir -p "${LOCAL_REPO}"
  cp -f "${_kage_main}" "${_kage_hdr}" "${LOCAL_REPO}/"
  ( cd "${LOCAL_REPO}" && repo-add -q nyxus-local.db.tar.gz \
       "$(basename "${_kage_main}")" "$(basename "${_kage_hdr}")" >/dev/null )
  ok "kernel: $(basename "${_kage_main}") + headers → ${LOCAL_REPO}/ (repo-add nyxus-local.db)"
  printf "  ${B}kernel sha256:${R} %s\n" "$(sha256sum "${_kage_main}" | cut -d' ' -f1)"

  # Wire the profile-local repo into the build pacman.conf (unsigned local
  # packages, so TrustAll for THIS repo only; official repos stay Required).
  cp "${PROFILE_DIR}/pacman.conf" "${PROFILE_DIR}/pacman.conf.bake.bak"
  if ! grep -q '^\[nyxus-local\]' "${PROFILE_DIR}/pacman.conf"; then
    cat >> "${PROFILE_DIR}/pacman.conf" <<PACMANLOCAL

[nyxus-local]
SigLevel = Optional TrustAll
Server = file://${LOCAL_REPO}
PACMANLOCAL
  else
    sed -i -E "s#^Server = file://.*/local-repo\$#Server = file://${LOCAL_REPO}#" "${PROFILE_DIR}/pacman.conf"
  fi
  ok "pacman.conf [nyxus-local] Server → file://${LOCAL_REPO}"

  # Append the kernel packages to the bake's package list (back it up first
  # unless the lean tier already did).
  [[ -f "${PROFILE_DIR}/packages.x86_64.bake.bak" ]] || cp "${PROFILE_DIR}/packages.x86_64" "${PROFILE_DIR}/packages.x86_64.bake.bak"
  if ! grep -q '^linux-kage-ryu$' "${PROFILE_DIR}/packages.x86_64"; then
    printf '\n# Kage Ryu Nyxus custom kernel (staged into [nyxus-local] by build-iso.sh)\nlinux-kage-ryu\nlinux-kage-ryu-headers\n' >> "${PROFILE_DIR}/packages.x86_64"
  fi
  ok "packages.x86_64 += linux-kage-ryu + headers (Kage-Ryu = primary; stock linux = rescue)"

  # Bake the auto-activation layer into the airootfs so a Kage-Ryu boot from
  # this image is tuned + scx_kage-scheduled on FIRST boot with no manual step.
  # Staged files are kage-namespaced and removed on exit by the restore trap,
  # so a git checkout is never left dirty (this whole block is opt-in anyway).
  if [[ -x "${KAGE_PKGDIR}/packaging/install-activation.sh" ]]; then
    if "${KAGE_PKGDIR}/packaging/install-activation.sh" --root "${PROFILE_DIR}/airootfs"; then
      NYX_KAGE_AIROOTFS_STAGED=1
      ok "auto-activation staged into airootfs (first boot: tuned + scx_kage scheduled)"
    else
      warn "kage-ryu activation staging failed — kernel still installs, but the ISO won't self-activate"
    fi
  else
    warn "no packaging/install-activation.sh in ${KAGE_PKGDIR}; ISO ships the kernel without auto-activation"
  fi

  # ── Make Kage-Ryu the DEFAULT live boot kernel (stock = rescue) ──────────
  # Rewrite the three live boot menus in the THROWAWAY profile copy only, so
  # the repo's static menus stay stock-safe (a botched rewrite can only ever
  # yield a bootable stock ISO). mkarchiso copies every installed kernel as
  # vmlinuz-<pkgbase> / initramfs-<pkgbase>.img, so with linux-kage-ryu
  # installed the live media gets vmlinuz-linux-kage-ryu automatically. The
  # ISO label is read from profiledef so the archisolabel can never drift.
  step "boot menus → Kage-Ryu default + stock linux rescue"
  _iso_label="$(grep -oP '^[[:space:]]*iso_label="?\K[^"[:space:]]+' "${PROFILE_DIR}/profiledef.sh" | head -1)"
  _iso_label="${_iso_label:-NYXUS_2026_07}"

  # GRUB (UEFI dragon menu) — quoted heredoc so grub's ${prefix} is preserved;
  # @@ISO_LABEL@@ placeholder is substituted afterward.
  cat > "${PROFILE_DIR}/grub/grub.cfg" <<'GRUBCFG'
# ============================================
# NYXUS — live boot menu · Kage Ryu dragon theme (rev 2026-07-23)
# Kage Ryu kernel = DEFAULT (entry 0) · stock linux = RESCUE
# © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
set default="0"
set timeout=8

# gfxterm is entered ONLY if a font actually loads, else we stay in the plain
# text terminal (never the broken "?"-glyph render).
if loadfont "${prefix}/fonts/mono12.pf2" ; then
    loadfont "${prefix}/fonts/mono9.pf2"
    loadfont "${prefix}/fonts/mono10.pf2"
    loadfont "${prefix}/fonts/mono11.pf2"
    loadfont "${prefix}/fonts/bold14.pf2"
    loadfont "${prefix}/fonts/bold16.pf2"
    insmod all_video
    insmod gfxterm
    insmod png
    set gfxmode=auto
    terminal_output gfxterm
    set theme="${prefix}/themes/nyxus/theme.txt"
fi

menuentry "Boot NYXUS · Kage Ryu kernel" --class nyxus --class arch {
    set gfxpayload=keep
    linux  /arch/boot/x86_64/vmlinuz-linux-kage-ryu  archisobasedir=arch archisolabel=@@ISO_LABEL@@ quiet splash
    initrd /arch/boot/intel-ucode.img /arch/boot/amd-ucode.img /arch/boot/x86_64/initramfs-linux-kage-ryu.img
}

menuentry "Boot NYXUS · Kage Ryu (safe / no KMS)" --class nyxus --class arch {
    set gfxpayload=keep
    linux  /arch/boot/x86_64/vmlinuz-linux-kage-ryu  archisobasedir=arch archisolabel=@@ISO_LABEL@@ nomodeset
    initrd /arch/boot/intel-ucode.img /arch/boot/amd-ucode.img /arch/boot/x86_64/initramfs-linux-kage-ryu.img
}

menuentry "Boot NYXUS · stock linux (rescue)" --class nyxus --class arch {
    set gfxpayload=keep
    linux  /arch/boot/x86_64/vmlinuz-linux  archisobasedir=arch archisolabel=@@ISO_LABEL@@ quiet splash
    initrd /arch/boot/intel-ucode.img /arch/boot/amd-ucode.img /arch/boot/x86_64/initramfs-linux.img
}

menuentry "UEFI Shell"             { chainloader /shellx64.efi }
menuentry "Reboot"                 { reboot }
menuentry "Power off"              { halt }
GRUBCFG

  # systemd-boot / efiboot loader entries (01 = Kage-Ryu default, 02 = rescue).
  cat > "${PROFILE_DIR}/efiboot/loader/entries/01-nyx.conf" <<'EFIKAGE'
# NYXUS — Kage Ryu (default)
title    NYXUS — The Night Has Eyes (Kage Ryu)
sort-key 01
linux    /arch/boot/x86_64/vmlinuz-linux-kage-ryu
initrd   /arch/boot/intel-ucode.img
initrd   /arch/boot/amd-ucode.img
initrd   /arch/boot/x86_64/initramfs-linux-kage-ryu.img
options  archisobasedir=arch archisolabel=@@ISO_LABEL@@ quiet splash
EFIKAGE
  cat > "${PROFILE_DIR}/efiboot/loader/entries/02-nyx-stock.conf" <<'EFISTOCK'
# NYXUS — stock linux (rescue)
title    NYXUS — stock linux (rescue)
sort-key 02
linux    /arch/boot/x86_64/vmlinuz-linux
initrd   /arch/boot/intel-ucode.img
initrd   /arch/boot/amd-ucode.img
initrd   /arch/boot/x86_64/initramfs-linux.img
options  archisobasedir=arch archisolabel=@@ISO_LABEL@@ quiet splash
EFISTOCK

  # syslinux (BIOS/Legacy text menu).
  cat > "${PROFILE_DIR}/syslinux/syslinux.cfg" <<'SYSLINUX'
# ============================================
# NYXUS — Live ISO (BIOS) · Kage Ryu default + stock rescue
# © 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
DEFAULT nyx
PROMPT 0
TIMEOUT 30

LABEL nyx
    MENU LABEL Boot NYXUS · Kage Ryu kernel
    LINUX /arch/boot/x86_64/vmlinuz-linux-kage-ryu
    INITRD /arch/boot/intel-ucode.img,/arch/boot/amd-ucode.img,/arch/boot/x86_64/initramfs-linux-kage-ryu.img
    APPEND archisobasedir=arch archisolabel=@@ISO_LABEL@@ quiet splash

LABEL nyx_kage_safe
    MENU LABEL Boot NYXUS · Kage Ryu (safe / no KMS)
    LINUX /arch/boot/x86_64/vmlinuz-linux-kage-ryu
    INITRD /arch/boot/intel-ucode.img,/arch/boot/amd-ucode.img,/arch/boot/x86_64/initramfs-linux-kage-ryu.img
    APPEND archisobasedir=arch archisolabel=@@ISO_LABEL@@ nomodeset

LABEL nyx_stock
    MENU LABEL Boot NYXUS · stock linux (rescue)
    LINUX /arch/boot/x86_64/vmlinuz-linux
    INITRD /arch/boot/intel-ucode.img,/arch/boot/amd-ucode.img,/arch/boot/x86_64/initramfs-linux.img
    APPEND archisobasedir=arch archisolabel=@@ISO_LABEL@@ quiet splash
SYSLINUX

  # Substitute the real ISO label into all three menus.
  sed -i "s/@@ISO_LABEL@@/${_iso_label}/g" \
    "${PROFILE_DIR}/grub/grub.cfg" \
    "${PROFILE_DIR}/efiboot/loader/entries/01-nyx.conf" \
    "${PROFILE_DIR}/efiboot/loader/entries/02-nyx-stock.conf" \
    "${PROFILE_DIR}/syslinux/syslinux.cfg"
  ok "boot menus rewritten: Kage-Ryu primary + stock rescue (archisolabel=${_iso_label})"
fi

# ── stamp version into profiledef.sh + os-release ────────────────────────
# Keep the date in a single place (this script). At every bake we rewrite
# the iso_version in profiledef.sh (consumed by mkarchiso for ISO metadata)
# and BUILD_ID in airootfs/etc/os-release (visible inside the live system)
# so they always match ISO_NAME. No more "is this last week's bake?" drift.
step "stamp iso version into profile metadata"
PROFILEDEF="${PROFILE_DIR}/profiledef.sh"
OSRELEASE="${PROFILE_DIR}/airootfs/etc/os-release"

# Identify the EXACT source this ISO was baked from. A date alone is not enough:
# two bakes on the same day (2026-07-22/23) were indistinguishable on the stick,
# which is precisely how a stale/partial ISO got flashed and debugged for hours.
# Commit + time make freshness unambiguous.
BUILD_COMMIT="$(cd "${REPO_ROOT}" && git rev-parse --short HEAD 2>/dev/null || echo unknown)"
BUILD_BRANCH="$(cd "${REPO_ROOT}" && git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
BUILD_DIRTY=""
if ! (cd "${REPO_ROOT}" && git diff --quiet HEAD 2>/dev/null); then BUILD_DIRTY="-dirty"; fi
BUILD_TIME="$(date '+%Y-%m-%d %H:%M:%S %Z')"
BUILD_STAMP="nyxus-${ISO_DATE}-${BUILD_COMMIT}${BUILD_DIRTY}-x86_64"

sed -i -E "s/^iso_version=\".*\"/iso_version=\"${ISO_DATE}\"/" "${PROFILEDEF}"
sed -i -E "s/^BUILD_ID=.*/BUILD_ID=${BUILD_STAMP}/" "${OSRELEASE}"

# ── squashfs compressor override ─────────────────────────────────────────
# The profile defaults to zstd because xz decode cost is paid on every cold
# read for the whole live session — measured 7.6x slower reads for -10.8%
# image size on this image's own content (see profiledef.sh for the numbers).
# `sudo NYX_SQUASH_COMP=xz ./build-iso.sh` restores the pre-2026.07.30 xz
# image if size ever matters more than speed.
NYX_SQUASH_COMP="${NYX_SQUASH_COMP:-zstd}"
case "${NYX_SQUASH_COMP}" in
  zstd)
    sed -i -E "s|^airootfs_image_tool_options=\(.*\)|airootfs_image_tool_options=('-comp' 'zstd' '-Xcompression-level' '19' '-b' '1M')|" "${PROFILEDEF}"
    ;;
  xz)
    sed -i -E "s|^airootfs_image_tool_options=\(.*\)|airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')|" "${PROFILEDEF}"
    warn "NYX_SQUASH_COMP=xz — smaller ISO, but ~7.6x slower cold reads on the live stick"
    ;;
  *)
    fail "NYX_SQUASH_COMP must be 'zstd' or 'xz' (got '${NYX_SQUASH_COMP}')"; exit 1
    ;;
esac
ok "squashfs compressor    → ${NYX_SQUASH_COMP}  ($(grep -oP "^airootfs_image_tool_options=\K.*" "${PROFILEDEF}"))"

# A dedicated, human-readable stamp file. `cat /etc/nyxus-build` on the booted
# stick answers "is this the ISO I just baked?" in one command.
cat > "${PROFILE_DIR}/airootfs/etc/nyxus-build" <<BUILDSTAMP
NYXUS live image build stamp
============================
iso            : ${ISO_NAME}
built          : ${BUILD_TIME}
source commit  : ${BUILD_COMMIT}${BUILD_DIRTY}  (branch: ${BUILD_BRANCH})
kernel baked   : $([[ "${NYX_WITH_KAGE_RYU:-1}" == "1" ]] && echo "kage-ryu (default) + stock linux (rescue)" || echo "stock linux only")
iso label      : ${ISO_LABEL:-NYXUS_2026_07}

If this commit is not what you expect, you are booting a STALE image — rebake.
BUILDSTAMP

# Surface it on every terminal login so freshness is impossible to miss.
mkdir -p "${PROFILE_DIR}/airootfs/etc/profile.d"
cat > "${PROFILE_DIR}/airootfs/etc/profile.d/nyxus-build-stamp.sh" <<'STAMPSH'
# ALIEN NEON build stamp — shown on every interactive terminal login.
# Violet #7d3dff = \033[38;2;125;61;255m  magenta #ff2dad = \033[38;2;255;45;173m
# cool-white #eef2fa = \033[38;2;238;242;250m
if [ -n "${PS1:-}" ] && [ -r /etc/nyxus-build ]; then
  printf '\033[38;2;125;61;255m── NYXUS BUILD STAMP ─────────────────────────────────\033[0m\n'
  printf '\033[38;2;238;242;250m'; sed -n '3,7p' /etc/nyxus-build; printf '\033[0m\n'
fi
STAMPSH
chmod 0644 "${PROFILE_DIR}/airootfs/etc/profile.d/nyxus-build-stamp.sh"

ok "stamped profiledef.sh   → iso_version=\"$(grep -oP '(?<=^iso_version=")[^"]+' "${PROFILEDEF}")\""
ok "stamped os-release      → $(grep -oP '^BUILD_ID=\S+' "${OSRELEASE}")"
ok "build stamp             → /etc/nyxus-build (commit ${BUILD_COMMIT}${BUILD_DIRTY}, shown at every login)"

# ── pull NYXUS Phantom tarball ───────────────────────────────────────────
step "fetch latest NYXUS Phantom (nyxus-intel.tgz)"
TGZ_LOCAL="${REPO_ROOT}/artifacts/api-server/nyxus-scripts/nyxus-intel.tgz"
TGZ_TMP="/tmp/nyxus-intel.tgz"

if [[ -f "${TGZ_LOCAL}" ]]; then
  cp "${TGZ_LOCAL}" "${TGZ_TMP}"
  ok "using local tarball at ${TGZ_LOCAL} (TRUSTED — same repo as this script)"
else
  warn "local tarball not found — downloading from production"
  warn "this is the supply chain trust boundary — verify the SHA below"
  curl -fL "${TARBALL_URL}" -o "${TGZ_TMP}"
  ok "downloaded from ${TARBALL_URL}"
fi

# Always print the SHA-256 of the staged tarball so the user can sign off
# before it gets baked into the ISO. If NYXUS_INTEL_SHA256 is set in the
# environment we enforce it (fail closed); otherwise we just display it.
TGZ_SHA="$(sha256sum "${TGZ_TMP}" | cut -d' ' -f1)"
printf "  ${B}sha256:${R} ${PINK}%s${R}\n" "${TGZ_SHA}"
if [[ -n "${NYXUS_INTEL_SHA256:-}" ]]; then
  if [[ "${NYXUS_INTEL_SHA256}" != "${TGZ_SHA}" ]]; then
    fail "tarball SHA-256 mismatch!"
    fail "expected: ${NYXUS_INTEL_SHA256}"
    fail "got:      ${TGZ_SHA}"
    exit 1
  fi
  ok "SHA-256 matches NYXUS_INTEL_SHA256 — verified"
fi

# ── stage NYXUS chrome (Phase 2: configs + GTK apps + wallpapers + scripts)
# Single source of truth: artifacts/api-server/nyxus-scripts/
# This is what makes the live ISO actually feel like NYXUS instead of vanilla
# Hyprland. Copies the full chrome layer into airootfs/ so mkarchiso bakes it
# into the squashfs. Idempotent — safe to re-run.
step "stage NYXUS chrome (configs, GTK apps, wallpapers, scripts)"
NS="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"
SKEL="${PROFILE_DIR}/airootfs/etc/skel"
OPT_NYXUS="${PROFILE_DIR}/airootfs/opt/nyxus"
WALLS_USER="${SKEL}/.config/hypr/walls"
WALLS_SYS="${PROFILE_DIR}/airootfs/usr/share/backgrounds/nyxus"
LBIN="${PROFILE_DIR}/airootfs/usr/local/bin"
APPS="${PROFILE_DIR}/airootfs/usr/share/applications"

# Wipe only NYXUS-managed config shards. Do not remove unrelated skel
# content (gtk settings, user units, app state dirs) needed at first boot.
rm -rf \
  "${SKEL}/.config/hypr" \
  "${SKEL}/.config/eww" \
  "${SKEL}/.config/dunst" \
  "${SKEL}/.config/rofi" \
  "${SKEL}/.config/wlogout" \
  "${SKEL}/.config/alacritty" \
  "${OPT_NYXUS}" \
  "${WALLS_SYS}"
mkdir -p \
  "${SKEL}/.config/hypr/conf.d" \
  "${SKEL}/.config/hypr/walls" \
  "${SKEL}/.config/eww/scripts" \
  "${SKEL}/.config/dunst" \
  "${SKEL}/.config/rofi" \
  "${SKEL}/.config/wlogout" \
  "${SKEL}/.config/alacritty" \
  "${SKEL}/.config/systemd/user" \
  "${OPT_NYXUS}" \
  "${WALLS_USER}" \
  "${WALLS_SYS}" \
  "${LBIN}" \
  "${APPS}"

# ── Configs → /etc/skel/.config/ ────────────────────────────────────────
# rev r6-eww (2026-05-11): waybar replaced by EWW. waybar-config.json,
# waybar-style.css, waybar-stats.sh, waybar-ticker.sh deleted from source.
install -m 0644 "${NS}/hyprland.conf"        "${SKEL}/.config/hypr/hyprland.conf"
install -m 0644 "${NS}/hyprlock.conf"        "${SKEL}/.config/hypr/hyprlock.conf"
install -m 0644 "${NS}/hyprlock-accent.conf" "${SKEL}/.config/hypr/hyprlock-accent.conf"
install -m 0644 "${NS}/hypridle.conf"        "${SKEL}/.config/hypr/hypridle.conf"
# Hypr extras wiped by rm -rf skel/.config/hypr above — MUST restage or
# idle-glass / prism-pulse / monitors source / hyprpaper break on the stick.
mkdir -p "${SKEL}/.config/hypr/scripts"
if [[ -d "${NS}/hypr/scripts" ]]; then
  install -m 0755 "${NS}/hypr/scripts/"*.sh "${SKEL}/.config/hypr/scripts/"
fi
for _hx in hyprpaper.conf nyxus-monitors.conf nyxus-voice.conf; do
  if [[ -f "${NS}/${_hx}" ]]; then
    install -m 0644 "${NS}/${_hx}" "${SKEL}/.config/hypr/${_hx}"
  fi
done
install -m 0644 "${NS}/nyxus-dunstrc"        "${SKEL}/.config/dunst/dunstrc"
install -m 0644 "${NS}/rofi-config.rasi"     "${SKEL}/.config/rofi/config.rasi"
install -m 0644 "${NS}/rofi-nyxus.rasi"      "${SKEL}/.config/rofi/nyxus.rasi"
install -m 0644 "${NS}/rofi-startmenu.rasi"  "${SKEL}/.config/rofi/startmenu.rasi"
install -m 0644 "${NS}/wlogout-style.css"    "${SKEL}/.config/wlogout/style.css"
install -m 0644 "${NS}/wlogout-layout"       "${SKEL}/.config/wlogout/layout"
install -m 0644 "${NS}/alacritty.toml"       "${SKEL}/.config/alacritty/alacritty.toml"
# Kitty (default terminal) + Welcome Transmission overlay conf
mkdir -p "${SKEL}/.config/kitty"
[[ -f "${NS}/kitty.conf" ]] && install -m 0644 "${NS}/kitty.conf" "${SKEL}/.config/kitty/kitty.conf"
[[ -f "${NS}/kitty-welcome.conf" ]] && install -m 0644 "${NS}/kitty-welcome.conf" "${SKEL}/.config/kitty/kitty-welcome.conf"

# ── fastfetch (neofetch successor; package in packages.x86_64) ───────────
if [[ -d "${NS}/fastfetch" ]]; then
  mkdir -p "${SKEL}/.config/fastfetch"
  install -m 0644 "${NS}/fastfetch/config.jsonc" \
    "${SKEL}/.config/fastfetch/config.jsonc"
  install -m 0644 "${NS}/fastfetch/nyxus-logo.txt" \
    "${SKEL}/.config/fastfetch/nyxus-logo.txt"
fi


# ── Hyprland conf.d/ overlays (blur/fog/general/opacity/rules/layerblur) ────
install -m 0644 "${NS}"/nyxus-hyprland-*.conf "${SKEL}/.config/hypr/conf.d/"
# Station matrix + safemode + signature + arsenal/reactive/consoles shards
# (not matched by nyxus-hyprland-*.conf). MUST list every shard hyprland.conf
# `source=`s, or the wipe of skel/.config/hypr above drops it even when
# committed in airootfs — 2026-07-24 W6 (committed-but-wiped-at-bake).
# 2026-07-28: nyxus-consoles.conf was the same bug a second time. It is
# sourced at hyprland.conf line 592, so a bake without it boots straight into
# Hyprland's "source= ... found no match" error banner. verify-profile.sh now
# derives this requirement from hyprland.conf instead of trusting this list.
for _shard in \
  nyxus-stations.conf \
  nyxus-safemode.conf \
  nyxus-signature.conf \
  nyxus-freeform.conf \
  nyxus-cometfire.conf \
  nyxus-reactive.conf \
  nyxus-arsenal-apps.conf \
  nyxus-consoles.conf \
  nyxus-stations-named.conf
do
  if [[ -f "${NS}/${_shard}" ]]; then
    install -m 0644 "${NS}/${_shard}" "${SKEL}/.config/hypr/conf.d/${_shard}"
  fi
done

# ── NYXUS station matrix (stations.json → workspaces.json) ───────────────
NYXUS_CFG="${REPO_ROOT}/artifacts/nyxus-config"
mkdir -p "${SKEL}/.config/nyxus"
if [[ -f "${NYXUS_CFG}/stations.json" ]]; then
  install -m 0644 "${NYXUS_CFG}/stations.json" "${SKEL}/.config/nyxus/stations.json"
  [[ -f "${NYXUS_CFG}/stations-hacker.json" ]] && \
    install -m 0644 "${NYXUS_CFG}/stations-hacker.json" "${SKEL}/.config/nyxus/stations-hacker.json"
  # Bake-time sync: use system wallpaper dir so skel paths survive first login.
  CONF="${SKEL}/.config/nyxus/stations.json" OUT="${SKEL}/.config/nyxus/workspaces.json" \
    bash -c '
      set -euo pipefail
      jq -n --slurpfile s "$CONF" --arg wall_dir "/usr/share/backgrounds/nyxus" "
        {
          \"_comment\": \"Auto-generated from stations.json at ISO bake. Do not hand-edit.\",
          \"workspaces\": [
            \$s[0].stations[] | {
              id: .id,
              name: .name,
              wallpaper: (\$wall_dir + \"/\" + .wallpaper)
            }
          ]
        }
      " > "$OUT"
    '
  ok "stations.json + stations-hacker.json + workspaces.json staged"
fi

# ── EWW (replaces waybar as of rev r6-eww) ──────────────────────────────────
# Top-level eww.yuck / eww.scss / nyxus.conf + all *.yuck modules + scripts/
install -m 0644 "${NS}/eww/eww.yuck"   "${SKEL}/.config/eww/eww.yuck"
install -m 0644 "${NS}/eww/nyxus.conf" "${SKEL}/.config/eww/nyxus.conf"
# eww 0.5: ship precompiled CSS + SCSS source (never both eww.scss and eww.css in skel)
if [[ -f "${NS}/eww/eww.css" ]]; then
  install -m 0644 "${NS}/eww/eww.css" "${SKEL}/.config/eww/eww.css"
fi
if [[ -f "${NS}/eww/eww.scss.source" ]]; then
  install -m 0644 "${NS}/eww/eww.scss.source" "${SKEL}/.config/eww/eww.scss.source"
elif [[ -f "${NS}/eww/eww.scss" ]]; then
  install -m 0644 "${NS}/eww/eww.scss" "${SKEL}/.config/eww/eww.scss.source"
fi
if compgen -G "${NS}/eww/*.yuck" >/dev/null; then
  install -m 0644 "${NS}"/eww/*.yuck "${SKEL}/.config/eww/" 2>/dev/null || true
fi
if [[ -f "${NS}/eww/README.md" ]]; then
  install -m 0644 "${NS}/eww/README.md" "${SKEL}/.config/eww/README.md"
fi
if [[ -d "${NS}/eww/scripts" ]]; then
  install -m 0755 "${NS}"/eww/scripts/* "${SKEL}/.config/eww/scripts/" 2>/dev/null || true
fi
# CATCH-ALL for every remaining top-level file in NS/eww (2026-07-29).
#
# The named installs above are a hand-maintained whitelist, and files kept
# falling through it. `rm -rf skel/.config/eww` above deletes EVERYTHING, so
# anything not explicitly restored simply does not exist on the ISO — silently,
# because nothing checks. Three real casualties were shipping:
#
#   cava.conf         — cava.sh runs `cava -p ~/.config/eww/cava.conf`. Missing
#                       file => cava exits, so the bar visualizer AND the
#                       CAVA_BASS scalar that drives the boombox speaker
#                       reactivity were both dead on every baked stick.
#   _nyxus_accent.scss / accent.scss
#                     — eww.scss.source line 4 is `@import "_nyxus_accent"`, so
#                       any recompile (nyxus-apply-accent) failed outright.
#   nyxus-palette.css — the @import target for the shared palette tokens.
#
# Copying whatever else NS/eww holds means adding a file there is enough; no
# edit is needed here and the whitelist can never silently lose one again.
# This runs AFTER the named installs so their explicit modes/renames still win.
for _ef in "${NS}"/eww/*; do
  [[ -f "${_ef}" ]] || continue
  _eb="$(basename "${_ef}")"
  [[ -e "${SKEL}/.config/eww/${_eb}" ]] && continue
  install -m 0644 "${_ef}" "${SKEL}/.config/eww/${_eb}"
done
# eww/assets wiped by rm -rf skel/.config/eww — bars/overlays reference
# assets/*.png from eww.yuck; without this restage the HUD is blank art.
if [[ -d "${NS}/eww/assets" ]]; then
  mkdir -p "${SKEL}/.config/eww/assets"
  cp -a "${NS}/eww/assets/." "${SKEL}/.config/eww/assets/"
fi

ok "configs: hypr (+conf.d) / eww (+assets) / dunst / rofi / wlogout / alacritty"

# ── GTK apps + chrome library + helpers → /opt/nyxus/ ───────────────────
# Plus skel symlink ~/.nyxus → /opt/nyxus so hyprland.conf keybinds (which
# launch python3 ~/.nyxus/nyxus_*.py to stay compatible with the
# download-portal install flow that uses ~/.nyxus/) work on the live ISO.
install -m 0644 "${NS}"/nyxus_*.py "${OPT_NYXUS}/"
if [[ -f "${NS}/nyxus-security-daemon.py" ]]; then
  install -m 0644 "${NS}/nyxus-security-daemon.py" "${OPT_NYXUS}/nyxus-security-daemon.py"
fi
if [[ -f "${NS}/nyxus-crash-report.py" ]]; then
  install -m 0644 "${NS}/nyxus-crash-report.py" "${OPT_NYXUS}/nyxus-crash-report.py"
fi
if [[ -f "${NS}/desktop/nyxus_desktop.py" ]]; then
  install -Dm0644 "${NS}/desktop/nyxus_desktop.py" "${OPT_NYXUS}/desktop/nyxus_desktop.py"
fi

# ── Welcome Wizard companion files (rev r9-eww 2026-05-11) ─────────────
# Stage the three hand-written files into airootfs/root/ where
# customize_airootfs.sh expects them. The launcher script overrides the
# auto-generated /usr/local/bin/nyxus-welcome wrapper because it adds
# marker-file gating and a single-instance flock.
ROOT_STAGE="${PROFILE_DIR}/airootfs/root"
mkdir -p "${ROOT_STAGE}"
for f in nyxus-welcome nyxus-welcome-helper nyxus-welcome.policy; do
  if [ -f "${NS}/${f}" ]; then
    install -m 0644 "${NS}/${f}" "${ROOT_STAGE}/${f}"
  fi
done
ok "Welcome Wizard: staged 3 companion files into airootfs/root/"
# ~/.nyxus is a REAL user-owned directory containing per-file SYMLINKS
# to each /opt/nyxus/*.py. This preserves keybind compat
# (python3 ~/.nyxus/nyxus_launcher.py still resolves) while leaving the
# directory writable for user-data files like ~/.nyxus/.bootstrapped and
# ~/.nyxus/hw_profile.json. The previous design symlinked the whole dir
# to /opt/nyxus which made every user-data write hit root-owned /opt.
rm -rf "${SKEL}/.nyxus"
mkdir -p "${SKEL}/.nyxus"
for _f in "${OPT_NYXUS}"/*.py; do
  ln -sfn "/opt/nyxus/$(basename "${_f}")" "${SKEL}/.nyxus/$(basename "${_f}")"
done
ok "GTK apps: $(ls "${OPT_NYXUS}"/*.py | wc -l) python files in /opt/nyxus/ (per-file symlinks in ~/.nyxus/ — dir is user-owned)"

# ── User services + policies (EWW / crashd / security daemon) ─────────────────
if [[ -f "${NS}/nyxus-eww.service" ]]; then
  install -m 0644 "${NS}/nyxus-eww.service" "${SKEL}/.config/systemd/user/nyxus-eww.service"
fi
if [[ -f "${NS}/nyxus-crashd.service" ]]; then
  install -m 0644 "${NS}/nyxus-crashd.service" "${SKEL}/.config/systemd/user/nyxus-crashd.service"
fi
if [[ -f "${NS}/nyxus-security-daemon.service" ]]; then
  install -m 0644 "${NS}/nyxus-security-daemon.service" "${SKEL}/.config/systemd/user/nyxus-security-daemon.service"
fi
if [[ -f "${NS}/com.nyxus.security.policy" ]]; then
  install -Dm644 "${NS}/com.nyxus.security.policy" \
    "${PROFILE_DIR}/airootfs/usr/share/polkit-1/actions/com.nyxus.security.policy"
fi
if [[ -f "${NS}/nyxus-parental-helper" ]]; then
  install -Dm755 "${NS}/nyxus-parental-helper" \
    "${PROFILE_DIR}/airootfs/usr/local/libexec/nyxus-parental-helper"
fi
# com.nyxus.parental.policy is NOT installed from NS's root (2026-07-29).
# A stale duplicate lived there: it was the only file in the whole tree with a
# malformed DTD URL (PolicyKit/1/ instead of PolicyKit/1.0/) and it declared
# auth_admin_keep with no allow_gui annotation, unlike the canonical copy. The
# wave-4 loop below installs polkit-policies/com.nyxus.parental.policy, which
# matches the committed airootfs action and is authoritative. The duplicate has
# been deleted; do not reintroduce a root-level copy of a wave-4 policy.
# Security + welcome helpers — referenced by nyxus_security.py and
# nyxus_welcome.py via /usr/local/libexec/<name>; without these the
# helper-mediated polkit calls 404 and the apps fall back to readonly.
if [[ -f "${NS}/nyxus-security-helper" ]]; then
  install -Dm755 "${NS}/nyxus-security-helper" \
    "${PROFILE_DIR}/airootfs/usr/local/libexec/nyxus-security-helper"
fi
if [[ -f "${NS}/nyxus-welcome-helper" ]]; then
  install -Dm755 "${NS}/nyxus-welcome-helper" \
    "${PROFILE_DIR}/airootfs/usr/local/libexec/nyxus-welcome-helper"
fi
ok "user units + policy: nyxus-eww / nyxus-crashd / nyxus-security-daemon / parental + security + welcome helpers"

# ── Wallpapers → both user skel (matches hyprland.conf path) and system ─
# Stage every nyxus-*.png from the canonical scripts dir (station matrix,
# lock screen, signature walls, etc.). Partial globs silently dropped walls
# on prior bakes — ship the full set every time.
if compgen -G "${NS}/nyxus-*.png" >/dev/null; then
  install -m 0644 "${NS}"/nyxus-*.png "${WALLS_USER}/"
  install -m 0644 "${NS}"/nyxus-*.png "${WALLS_SYS}/"
fi
# ROTATION SET (2026-07-29). The glob above only reaches NS's ROOT, but every
# nyxus-rot-*.png lives in NS/hypr-walls/rotation/ — and `rm -rf skel/.config/hypr`
# above deletes the committed skel copy of walls/rotation/. Net effect on every
# stick baked so far: 27 of the 32 wallpapers in the curated wall-rotation.list
# did not exist on the ISO, so the ambient rotation cycled the same 5 images and
# nyxus-rotate-walls logged a miss for the rest. Stage the subdir into BOTH
# surfaces, matching the search paths in nyxus-set-wallpaper.sh / nyxus-hacker-mode.
if compgen -G "${NS}/hypr-walls/rotation/*.png" >/dev/null; then
  mkdir -p "${WALLS_USER}/rotation" "${WALLS_SYS}/rotation"
  install -m 0644 "${NS}"/hypr-walls/rotation/*.png "${WALLS_USER}/rotation/"
  install -m 0644 "${NS}"/hypr-walls/rotation/*.png "${WALLS_SYS}/rotation/"
fi
ok "wallpapers: $(ls "${WALLS_SYS}" | wc -l) files in /usr/share/backgrounds/nyxus/ + skel (+ $(ls "${WALLS_SYS}/rotation" 2>/dev/null | wc -l) rotation)"

# ── Helper scripts → /usr/local/bin/ ────────────────────────────────────
# rev r6-eww: waybar-stats / waybar-ticker removed. nyxus-eww-launch added.
install -m 0755 "${NS}/wallpaper-rotate.sh"  "${LBIN}/wallpaper-rotate"

# Tier B/C Settings helpers (canonical copies may live in NS; keep LBIN lockstep)
for _hlp in nyxus-kernel-switch nyxus-virt-setup nyxus-protonup \
            nyxus-distrobox-helper nyxus-usbguard-helper nyxus-secboot \
            nyxus-doh nyxus-mac-randomize; do
  if [[ -f "${NS}/${_hlp}" ]]; then
    install -m 0755 "${NS}/${_hlp}" "${LBIN}/${_hlp}"
  fi
done

if [[ -f "${NS}/nyxus-eww-launch" ]]; then
  install -m 0755 "${NS}/nyxus-eww-launch" "${LBIN}/nyxus-eww-launch"
fi
if [[ -f "${NS}/nyxus-eww-launch-safe" ]]; then
  install -m 0755 "${NS}/nyxus-eww-launch-safe" "${LBIN}/nyxus-eww-launch-safe"
fi
if [[ -f "${NS}/nyxus-mission-control-toggle" ]]; then
  install -m 0755 "${NS}/nyxus-mission-control-toggle" "${LBIN}/nyxus-mission-control-toggle"
fi
if [[ -f "${NS}/nyxus-set-wallpaper.sh" ]]; then
  install -m 0755 "${NS}/nyxus-set-wallpaper.sh" "${LBIN}/nyxus-set-wallpaper.sh"
fi
if [[ -f "${NS}/nyxus-sync-stations" ]]; then
  install -m 0755 "${NS}/nyxus-sync-stations" "${LBIN}/nyxus-sync-stations"
fi
if [[ -f "${NS}/nyxus-session-start" ]]; then
  install -m 0755 "${NS}/nyxus-session-start" "${LBIN}/nyxus-session-start"
fi
if [[ -f "${NS}/nyxus-settings" ]]; then
  install -m 0755 "${NS}/nyxus-settings" "${LBIN}/nyxus-settings"
fi
if [[ -f "${NS}/nyxus-webapp" ]]; then
  install -m 0755 "${NS}/nyxus-webapp" "${LBIN}/nyxus-webapp"
fi
if [[ -f "${NS}/desktop-entries/nyxus-hyprland.desktop" ]]; then
  install -Dm644 "${NS}/desktop-entries/nyxus-hyprland.desktop" \
    "${PROFILE_DIR}/airootfs/usr/share/wayland-sessions/nyxus-hyprland.desktop"
fi
if [[ -f "${NS}/nyxus-sound.sh" ]]; then
  install -m 0755 "${NS}/nyxus-sound.sh" "${LBIN}/nyxus-sound.sh"
fi
if [[ -f "${NS}/nyxus-record" ]]; then
  install -m 0755 "${NS}/nyxus-record" "${LBIN}/nyxus-record"
fi
if [[ -f "${NS}/desktop/nyxus-context-menu.sh" ]]; then
  install -m 0755 "${NS}/desktop/nyxus-context-menu.sh" "${LBIN}/nyxus-context-menu.sh"
fi
# ── Hub + escape-path scripts (rev 2026-07-15 RC) ───────────────────────
# hyprland.conf's Escape / Super+Shift+Escape binds and the bar's start
# button call these. They MUST ship or the ISO reproduces the "trapped
# fullscreen with no bars" regression with no recovery path.
for _hub in nyxus-hub-open nyxus-hub-close nyxus-hub-launch nyxus-hub-apps \
            nyxus-hub-search nyxus-shader nyxus-screensaver; do
  if [[ -f "${NS}/${_hub}" ]]; then
    install -m 0755 "${NS}/${_hub}" "${LBIN}/${_hub}"
  fi
done
# Screensaver payloads (launched by nyxus-screensaver via hypridle).
# nyxus_screensaver.py is the CANONICAL one — the urban-alien wallpaper hero
# that e5c381d1 made the saver on 2026-07-24. It was never staged here, so it
# only ever shipped because skel/.config/nyxus is not in the wipe list above:
# an edit to the NS copy (the source of truth) would silently never reach a
# stick. nyxus_matrix_saver.py is the superseded matrix-rain effect, kept
# staged so an existing install that still points at it does not break.
for _saver in nyxus_screensaver.py nyxus_matrix_saver.py; do
  if [[ -f "${NS}/${_saver}" ]]; then
    install -Dm0755 "${NS}/${_saver}" "${SKEL}/.config/nyxus/${_saver}"
  fi
done
# greetd greeter chain — keep the airootfs copy in lockstep with the
# canonical fixed version (login-loop fix: signal-death != crash).
if [[ -f "${NS}/greetd/nyxus-greeter" ]]; then
  install -m 0755 "${NS}/greetd/nyxus-greeter" "${LBIN}/nyxus-greeter"
fi
# ...and the greeter's own config + stylesheet. These were NOT staged: NS
# carried a full copy of both and nothing ever installed it, so the login
# screen shipped whatever happened to be committed under airootfs/etc/greetd
# and an edit to the NS copy (the tree everything else here treats as the
# source of truth) reached no stick. regreet.css in particular now carries the
# card placement the owner approved, and nyxus-greeter rescales it per panel by
# reading /etc/greetd/regreet.css — so this file has to be the current one.
for _g in regreet.toml regreet.css; do
  if [[ -f "${NS}/greetd/${_g}" ]]; then
    install -Dm0644 "${NS}/greetd/${_g}" "${PROFILE_DIR}/airootfs/etc/greetd/${_g}"
  fi
done

# ── Station decks + Jul-27 ops scripts (rev 2026-07-28) ─────────────────
# nyxus-home-deck is the socket2 watcher that maps EVERY station to its eww
# window (HOME->home-deck, START->start-panel, GHOST/FORGE/LAB->their decks).
# It was never staged, so the 2026.07.27 ISO shipped a rail whose HOME and
# START pills switched to workspaces that stayed empty — the eww side was
# current, only the launcher was missing. hyprland.conf exec-once's it by
# name, so without this line the whole station layer is dead on a fresh bake.
#
# nyxus-edr-repair matters on a fresh install specifically: Bifrost's AI EDR
# ships blind (Ollama not started) and this is the only thing that fixes it.
for _station in nyxus-home-deck nyxus-consoles nyxus-edr-repair \
                nyxus-suricata-setup nyxus-journal-ship nyxus-livewall-flagship; do
  if [[ -f "${NS}/${_station}" ]]; then
    install -m 0755 "${NS}/${_station}" "${LBIN}/${_station}"
  fi
done

# SharkFin mini-NOC (2026-07-28) — the compact GowskiNet NOC the owner wanted on
# the MESH station (workspace 7, "Network · NOC · Mesh"). Pure-stdlib and
# defensive about missing honeypot/hardware dirs, so on a fresh install with no
# lab it simply reports zeros/offline rather than erroring. sharkdash_core.py +
# sharkdash_health.py are its only deps and MUST land in the SAME dir as the
# sharknoc launcher, because sharknoc adds its own dirname to sys.path. The MESH
# station launch is fail-safe (falls back to btop) so a bake that ever omits
# these is degraded, never broken.
for _shark in sharknoc sharkdash_core.py sharkdash_health.py; do
  if [[ -f "${NS}/${_shark}" ]]; then
    install -m 0755 "${NS}/${_shark}" "${LBIN}/${_shark}"
  fi
done
ok "helpers: wallpaper-rotate / nyxus-eww-launch / hub+escape set / greeter / stations / sharknoc"

# ── Security mode scripts (rev 2026-07-17) ──────────────────────────────
# nyxus-ghost, nyxus-panic, nyxus-hacker-mode, nyxus-blackarch-full
# are user-facing launchers; nyxus-ghost-helper is the privileged backend.
for _sec in nyxus-ghost nyxus-ghost-helper nyxus-panic nyxus-hacker-mode \
            nyxus-blackarch-full; do
  if [[ -f "${NS}/${_sec}" ]]; then
    install -m 0755 "${NS}/${_sec}" "${LBIN}/${_sec}"
  fi
done
# nyxus-start GTK app — install app directory to /opt/nyxus/nyxus-start
# and the launcher shim to /usr/local/bin/nyxus-start.
if [[ -d "${NS}/nyxus-start" ]]; then
  mkdir -p "${PROFILE_DIR}/airootfs/opt/nyxus/nyxus-start"
  for _f in "${NS}/nyxus-start"/*.py "${NS}/nyxus-start/nyxus-palette.css"; do
    [[ -f "${_f}" ]] || continue
    install -m 0644 "${_f}" "${PROFILE_DIR}/airootfs/opt/nyxus/nyxus-start/"
  done
  if [[ -f "${NS}/nyxus-start/nyxus-start" ]]; then
    # Adapt the launcher from user-install path (~/.nyxus) to ISO system path
    # (/opt/nyxus). Single quotes are intentional: sed must match the literal
    # characters '${HOME}' in the source file, not the expanded value.
    sed 's|${HOME}/\.nyxus/nyxus-start|/opt/nyxus/nyxus-start|g' \
      "${NS}/nyxus-start/nyxus-start" > "${LBIN}/nyxus-start"
    chmod 0755 "${LBIN}/nyxus-start"
  fi
fi

# Sound theme assets used by nyxus-sound.sh (falls back to canberra IDs if missing).
if [[ -d "${NS}/sounds" ]]; then
  install -Dm644 "${NS}/sounds/index.theme" \
    "${PROFILE_DIR}/airootfs/usr/share/sounds/nyxus/index.theme" 2>/dev/null || true
  install -m 0644 "${NS}"/sounds/*.oga \
    "${PROFILE_DIR}/airootfs/usr/share/sounds/nyxus/" 2>/dev/null || true
fi

# ── First-boot bootstrap shims → /usr/local/bin/ ────────────────────────
# nyxus-bootstrap is the first-run installer wrapper that Hyprland's
# exec-once fires on first login. nyxus-wait-bootstrap gates dependent
# autostarts (eww, swaybg, nyxus-home) on bootstrap completion.
# Both must exist on the live ISO at 0755 — see profiledef.sh
# file_permissions which enforces the perms post-bake.
install -m 0755 "${NS}/nyxus-bootstrap"      "${LBIN}/nyxus-bootstrap"
install -m 0755 "${NS}/nyxus-wait-bootstrap" "${LBIN}/nyxus-wait-bootstrap"
# Welcome Transmission (borderless kitty poem) + Dream Protocol easter egg
[[ -f "${NS}/nyxus-welcome-note" ]] && install -m 0755 "${NS}/nyxus-welcome-note" "${LBIN}/nyxus-welcome-note"
[[ -f "${NS}/nyxus-dream" ]] && install -m 0755 "${NS}/nyxus-dream" "${LBIN}/nyxus-dream"
ok "bootstrap shims: nyxus-bootstrap / nyxus-wait-bootstrap (+ welcome-note / dream if present)"

# ── User systemd units → /usr/lib/systemd/user/ ─────────────────────────
# Settings toggles ship as user systemd units so non-root users can
# enable/disable without sudo. Units are global-readable; per-user
# enablement is via `systemctl --user enable …`.
USER_SYSD="${PROFILE_DIR}/airootfs/usr/lib/systemd/user"
install -d -m 0755 "${USER_SYSD}"
install -m 0644 "${NS}/nyxus-usb-watch.service" \
                "${USER_SYSD}/nyxus-usb-watch.service"
ok "user systemd units: nyxus-usb-watch.service"

# ── Offline cache → /opt/nyxus-cache/ ───────────────────────────────────
# nyxus-bootstrap falls back to this path when the network is unreachable on
# first boot (i.e. ALWAYS on a live USB with no Wi-Fi). If this cache is
# empty, first-boot setup can't complete offline and the user lands on a
# bare desktop with a "no internet + no offline cache" note — exactly the
# failure seen on the 2026-07-22 stick. So this MUST be populated, and we
# now FAIL THE BAKE if it can't be, rather than silently shipping an
# online-only ISO.
#
# Source preference (2026-07-24 audit):
#   1. artifacts/api-server/nyxus-scripts       — git SoT (ALWAYS prefer)
#   2. artifacts/api-server/dist/nyxus-scripts  — ONLY if no broken host
#      symlinks (dist/ historically poisoned bakes with /home/cosmic/… links)
NYXUS_DIST=""
_ns_src="${REPO_ROOT}/artifacts/api-server/nyxus-scripts"
_dist_src="${REPO_ROOT}/artifacts/api-server/dist/nyxus-scripts"
if [[ -d "${_ns_src}" && -f "${_ns_src}/nyxus_install.sh" ]]; then
  NYXUS_DIST="${_ns_src}"
elif [[ -d "${_dist_src}" && -f "${_dist_src}/nyxus_install.sh" ]]; then
  # Reject dist/ if it contains dangling symlinks outside the repo.
  if find "${_dist_src}" -type l ! -exec test -e {} \; -print -quit 2>/dev/null | grep -q .; then
    fail "artifacts/api-server/dist/nyxus-scripts has broken symlinks (host poison)."
    fail "  Remove it:  rm -rf artifacts/api-server/dist/nyxus-scripts"
    fail "  Or ensure NS nyxus-scripts is present. Aborting the bake."
    exit 1
  fi
  NYXUS_DIST="${_dist_src}"
fi
OFFLINE_CACHE="${PROFILE_DIR}/airootfs/opt/nyxus-cache"
# Always wipe first so a missing source never silently ships a stale cache
# from a prior bake. The whole point of staging is fresh-each-time.
rm -rf "${OFFLINE_CACHE}"
if [[ -z "${NYXUS_DIST}" ]]; then
  fail "offline install payload not found (no nyxus_install.sh under"
  fail "  artifacts/api-server/{dist/,}nyxus-scripts) — the ISO would strand"
  fail "  the user on a bare desktop with no internet. Aborting the bake."
  exit 1
fi
mkdir -p "${OFFLINE_CACHE}"
cp -a "${NYXUS_DIST}/." "${OFFLINE_CACHE}/"
# Drop build cruft that has no business in the shipped cache (python bytecode,
# VCS, editor/agent dirs). Cheap size win; never touches payload files.
find "${OFFLINE_CACHE}" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "${OFFLINE_CACHE}" -type f -name '*.pyc' -delete 2>/dev/null || true
find "${OFFLINE_CACHE}" -type d \( -name '.git' -o -name '.claude' -o -name '.pytest_cache' \) -prune -exec rm -rf {} + 2>/dev/null || true
# Hard guarantee: the installer the bootstrap runs offline MUST be present.
if [[ ! -f "${OFFLINE_CACHE}/nyxus_install.sh" ]]; then
  fail "offline cache staged from ${NYXUS_DIST} but nyxus_install.sh is missing — aborting"
  exit 1
fi
ok "offline cache: $(find "${OFFLINE_CACHE}" -type f | wc -l) files ($(du -sh "${OFFLINE_CACHE}" | cut -f1)) from ${NYXUS_DIST#${REPO_ROOT}/} — first boot works with NO internet"

# ── SDDM theme → /usr/share/sddm/themes/nyxus/ + config ────────────────
# Stages the NYXUS QML login theme into the airootfs. The live ISO itself
# autologs into Hyprland (no SDDM at boot) so this is dormant on the live
# session — but when the disk installer (Job 2) provisions a real install,
# sddm.service gets enabled and this theme is what the user sees at boot.
SDDM_TMP_STAGE="$(mktemp -d)"
tar -xzf "${NS}/nyxus-sddm-theme.tar.gz" -C "${SDDM_TMP_STAGE}"
SDDM_THEME_DIR="${PROFILE_DIR}/airootfs/usr/share/sddm/themes/nyxus"
SDDM_CONF_DIR="${PROFILE_DIR}/airootfs/etc/sddm.conf.d"
mkdir -p "${SDDM_THEME_DIR}" "${SDDM_CONF_DIR}"
# Tarball is packed flat (files at root, no wrapper dir) so copy from STAGE root.
cp -a "${SDDM_TMP_STAGE}/." "${SDDM_THEME_DIR}/"
rm -f "${SDDM_THEME_DIR}/install.sh"  # not needed at runtime
# Override greeter background with urban-alien hero (alien theme only).
if [[ -f "${NS}/nyxus-urban-alien.png" ]]; then
  install -m 0644 "${NS}/nyxus-urban-alien.png" \
    "${SDDM_THEME_DIR}/background.png"
  ok "SDDM background overridden to urban-alien (alien theme)"
elif [[ -f "${NS}/nyxus-login-wall.png" ]]; then
  install -m 0644 "${NS}/nyxus-login-wall.png" \
    "${SDDM_THEME_DIR}/background.png"
  ok "SDDM background overridden to login-wall (alien theme)"
fi
cat > "${SDDM_CONF_DIR}/nyxus.conf" <<'SDDM'
[Theme]
Current=nyxus
SDDM
# DisplayServer is intentionally NOT set — SDDM defaults to X11 for the
# greeter, which is the only setting that works reliably across NVIDIA,
# Intel, and AMD hardware. The user's actual session (Hyprland) is still
# pure Wayland regardless of what the greeter uses to render itself.
# To opt into a Wayland greeter, the user can drop their own conf into
# /etc/sddm.conf.d/wayland.conf later.
rm -rf "${SDDM_TMP_STAGE}"
ok "SDDM theme staged: /usr/share/sddm/themes/nyxus/ + /etc/sddm.conf.d/nyxus.conf"

# ── App launchers + .desktop entries ────────────────────────────────────
# mod-name : Display Name : tooltip
#  Each entry maps to a real `nyxus_<mod>.py` in nyxus-scripts/. Any app
#  added here must have a matching script — phantom entries produce
#  launchers that exec a non-existent file and confuse the menu.
#  weather/quicksettings/powermenu live in EWW, not as standalone .py
#  apps, so they are intentionally NOT here.
APPS_LIST=(
  "notepad:Notepad:NYXUS markdown notepad"
  "stickies:Stickies:Sticky notes pinned to your desktop"
  "notes:Notes:Quick scratchpad notes"
  "sysmon_gtk:System Monitor:Real-time system metrics"
  "settings:Settings:System control center"
  "control:Control:Quick toggles & launchers"
  "terminal:Terminal:NYXUS-themed terminal"
  "launcher:Launcher:Application launcher"
  "screenshot:Screenshot:Region & full-screen capture"
  "store:App Store:Browse, install, and update software"
  "powermenu:Power:Lock / suspend / logout / restart / shutdown"
  "doctor:Doctor:NYXUS health audit"
)
for entry in "${APPS_LIST[@]}"; do
  IFS=':' read -r mod name comment <<< "${entry}"
  # Friendly bin name: nyxus_sysmon_gtk → nyxus-sysmon (special-case),
  # everything else → nyxus-<mod with underscores → dashes>.
  if [[ "${mod}" == "sysmon_gtk" ]]; then
    bin_name="nyxus-sysmon"
  else
    bin_name="nyxus-${mod//_/-}"
  fi
  cat > "${LBIN}/${bin_name}" <<LAUNCHER
#!/usr/bin/env bash
# NYXUS ${name} launcher — Copyright © 2026 Joseph A. Sierengowski
exec python3 /opt/nyxus/nyxus_${mod}.py "\$@"
LAUNCHER
  chmod 0755 "${LBIN}/${bin_name}"
  cat > "${APPS}/io.nyxus.${mod}.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=NYXUS ${name}
Comment=${comment}
Exec=/usr/local/bin/${bin_name}
Icon=preferences-system
Categories=System;Utility;
Terminal=false
StartupNotify=true
DESKTOP
done
ok "launchers + desktop entries: ${#APPS_LIST[@]} apps"

# Utility wrappers required by Hyprland keybinds/services.
cat > "${LBIN}/nyxus-clipboard" <<'LAUNCHER'
#!/usr/bin/env bash
exec python3 /opt/nyxus/nyxus_clipboard.py "$@"
LAUNCHER
chmod 0755 "${LBIN}/nyxus-clipboard"

cat > "${LBIN}/nyxus-files" <<'LAUNCHER'
#!/usr/bin/env bash
exec python3 /opt/nyxus/nyxus_files.py "$@"
LAUNCHER
chmod 0755 "${LBIN}/nyxus-files"

cat > "${LBIN}/nyxus-updater" <<'LAUNCHER'
#!/usr/bin/env bash
exec python3 /opt/nyxus/nyxus_updater.py "$@"
LAUNCHER
chmod 0755 "${LBIN}/nyxus-updater"

cat > "${LBIN}/nyxus-backup" <<'LAUNCHER'
#!/usr/bin/env bash
exec python3 /opt/nyxus/nyxus_backup.py "$@"
LAUNCHER
chmod 0755 "${LBIN}/nyxus-backup"

cat > "${LBIN}/nyxus-drop" <<'LAUNCHER'
#!/usr/bin/env bash
exec python3 /opt/nyxus/nyxus_drop.py "$@"
LAUNCHER
chmod 0755 "${LBIN}/nyxus-drop"

cat > "${LBIN}/nyxus-crash-report" <<'LAUNCHER'
#!/usr/bin/env bash
exec python3 /opt/nyxus/nyxus-crash-report.py "$@"
LAUNCHER
chmod 0755 "${LBIN}/nyxus-crash-report"

cat > "${LBIN}/nyxus-security" <<'LAUNCHER'
#!/usr/bin/env bash
exec python3 /opt/nyxus/nyxus_security.py "$@"
LAUNCHER
chmod 0755 "${LBIN}/nyxus-security"

cat > "${LBIN}/nyxus-crashd" <<'LAUNCHER'
#!/usr/bin/env bash
exec python3 /opt/nyxus/nyxus_crashd.py "$@"
LAUNCHER
chmod 0755 "${LBIN}/nyxus-crashd"

cat > "${LBIN}/nyxus-desktop" <<'LAUNCHER'
#!/usr/bin/env bash
exec python3 /opt/nyxus/desktop/nyxus_desktop.py "$@"
LAUNCHER
chmod 0755 "${LBIN}/nyxus-desktop"

cat > "${LBIN}/nyxus-wallpaper-studio" <<'LAUNCHER'
#!/usr/bin/env bash
exec python3 /opt/nyxus/nyxus_wallpaper_studio.py "$@"
LAUNCHER
chmod 0755 "${LBIN}/nyxus-wallpaper-studio"

# ── populate airootfs/opt/nyxus-intel ────────────────────────────────────
step "stage Phantom into airootfs/opt/nyxus-intel/"
INSTALL_DIR="${PROFILE_DIR}/airootfs/opt/nyxus-intel"
rm -rf "${INSTALL_DIR}"
mkdir -p "${INSTALL_DIR}"

# Extract → ${INSTALL_DIR}
TMP_EXTRACT="$(mktemp -d)"
tar -xzf "${TGZ_TMP}" -C "${TMP_EXTRACT}"
install -m 0644 "${TMP_EXTRACT}/intel/nyxus-intel/"*.py "${INSTALL_DIR}/"
ok "deployed $(ls "${INSTALL_DIR}"/*.py | wc -l) python files"

# Per-app docs alongside the binaries
for doc in LICENSE.md README.md CHANGELOG.md CREDITS.md; do
  if [[ -f "${TMP_EXTRACT}/intel/${doc}" ]]; then
    install -m 0644 "${TMP_EXTRACT}/intel/${doc}" "${INSTALL_DIR}/${doc}"
  fi
done

# Tamper manifest (matches _tamper._digest_dir)
python3 - <<'PY' "${INSTALL_DIR}"
import hashlib, sys
from pathlib import Path
d = Path(sys.argv[1])
h = hashlib.sha256()
for p in sorted(d.glob("*.py")):
    h.update(p.name.encode()); h.update(b"\0")
    h.update(p.read_bytes());   h.update(b"\0")
(d / ".manifest.sha256").write_text(h.hexdigest() + "\n", encoding="utf-8")
PY
ok "sealed tamper manifest"

# Caveat font into airootfs/usr/share/fonts/TTF/
if [[ -f "${TMP_EXTRACT}/intel/fonts/Caveat.ttf" ]]; then
  install -Dm 0644 "${TMP_EXTRACT}/intel/fonts/Caveat.ttf" \
    "${PROFILE_DIR}/airootfs/usr/share/fonts/TTF/Caveat.ttf"
  ok "staged Caveat font"
fi

# Launcher → /usr/local/bin/nyxus-intel on the live system
mkdir -p "${PROFILE_DIR}/airootfs/usr/local/bin"
cat > "${PROFILE_DIR}/airootfs/usr/local/bin/nyxus-intel" <<'LAUNCHER'
#!/usr/bin/env bash
# NYXUS Phantom launcher — Copyright © 2026 Joseph A. Sierengowski
exec python3 -c '
import sys
sys.path.insert(0, "/opt/nyxus-intel")
from main import main
sys.exit(main())
' "$@"
LAUNCHER
chmod 0755 "${PROFILE_DIR}/airootfs/usr/local/bin/nyxus-intel"

# Desktop entry
mkdir -p "${PROFILE_DIR}/airootfs/usr/share/applications"
cat > "${PROFILE_DIR}/airootfs/usr/share/applications/io.nyxus.intel.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=NYXUS Phantom
GenericName=Open Source Intelligence Workstation
Comment=Professional grade OSINT and investigation app
Exec=/usr/local/bin/nyxus-intel
Icon=preferences-system-search
Categories=Network;Security;Office;
Terminal=false
StartupNotify=true
DESKTOP
ok "launcher + desktop entry staged"

rm -rf "${TMP_EXTRACT}"

# ── COMPLETION WAVE 4: install all generated wiring artifacts ────────────
# (.desktop, polkit, system tuning, plymouth/grub themes, firstboot, helpers)
# These all live under iso-builder/nyx-profile/airootfs/ already; this step
# additionally pushes the freshly-authored helper binaries from nyxus-scripts
# into /usr/local/libexec and ensures the nyxus(1) CLI dispatcher + udev
# event helper are executable in the bake.
step "wave-4: install completion wiring (helpers, firstboot, themes)"
LIBEXEC="${PROFILE_DIR}/airootfs/usr/local/libexec"
LBIN="${PROFILE_DIR}/airootfs/usr/local/bin"
mkdir -p "${LIBEXEC}" "${LBIN}"

# Wave-4 helper binaries authored in nyxus-scripts → /usr/local/libexec
# NOTE this is an explicit allowlist, unlike the polkit loop below which
# globs com.nyxus.*.policy. A helper added to nyxus-scripts but not named
# here is silently absent from the ISO, and the Settings page that needs it
# renders its "helper missing" state on a fresh install with nothing in the
# build log to explain why. Add new helpers here.
for h in nyxus-backup-helper nyxus-usbwatch-helper \
         nyxus-account-helper nyxus-doctor-helper \
         nyxus-loginconfig-helper; do
  if [[ -f "${NS}/${h}" ]]; then
    install -Dm755 "${NS}/${h}" "${LIBEXEC}/${h}"
  fi
done

# Wave-4 desktop entries authored in nyxus-scripts/desktop-entries
if [[ -d "${NS}/desktop-entries" ]]; then
  for desk in "${NS}/desktop-entries"/nyxus-*.desktop; do
    [[ -f "${desk}" ]] || continue
    # SESSION entries are not applications (2026-07-29). This glob was pulling
    # nyxus-hyprland.desktop -- the greetd session selector -- into the app menu,
    # where it rendered as a launchable "NYXUS (Hyprland)" entry that would try
    # to start a NESTED compositor inside the running session. A DesktopNames=
    # key is what marks a session entry; those belong only in
    # usr/share/wayland-sessions/, which is staged separately above.
    if grep -q '^DesktopNames=' "${desk}"; then
      continue
    fi
    install -Dm644 "${desk}" "${PROFILE_DIR}/airootfs/usr/share/applications/$(basename "${desk}")"
  done
fi

# Wave-4 polkit policies authored under nyxus-scripts/polkit-policies
if [[ -d "${NS}/polkit-policies" ]]; then
  for pol in "${NS}/polkit-policies"/com.nyxus.*.policy; do
    [[ -f "${pol}" ]] || continue
    install -Dm644 "${pol}" \
      "${PROFILE_DIR}/airootfs/usr/share/polkit-1/actions/$(basename "${pol}")"
  done
fi

# Make sure firstboot.d scripts + nyxus dispatcher + udev event helper
# carry the executable bit (Python generator already chmod'd them, but
# git can lose modes on some checkouts).
chmod 0755 "${PROFILE_DIR}/airootfs/etc/nyxus-firstboot.d/"*.sh 2>/dev/null || true
chmod 0755 "${PROFILE_DIR}/airootfs/usr/local/bin/nyxus" \
           "${PROFILE_DIR}/airootfs/usr/local/bin/nyxus-usbwatch-event" \
           "${PROFILE_DIR}/airootfs/usr/local/bin/nyxus-pacman-toast" 2>/dev/null || true
ok "wave-4 wiring installed (helpers, polkit, firstboot, dispatcher)"

# ── stage NYXUS Master Hub (Bifrost) ─────────────────────────────────────
# rev 2026-07-15 — Bifrost is built off-tree (its own repo/pacman package,
# NOT part of this repo — see docs/NYXUS_BUILD.md "separate security stack").
# Previously the ISO shipped nothing for it (station 10/EDGE launch line in
# nyxus-stations.conf was commented out pending "the Bifrost build landing").
# That build has landed, so we stage the already-built package payload
# straight into airootfs at bake time — the same "copy prebuilt artifacts
# into airootfs" pattern used above for every other NYXUS component, rather
# than compiling Tauri/Rust/pnpm inside the mkarchiso chroot.
#
# Source precedence (first match wins), override with env vars:
#   NYX_BIFROST_BIN  — path to the built `bifrost` binary
#   NYX_BIFROST_REPO — path to a checkout of the Bifrost source repo
#                      (used for guardian python source, systemd unit,
#                      desktop icon, and the default heimdall config)
step "stage NYXUS Master Hub (Bifrost)"
BIFROST_BIN="${NYX_BIFROST_BIN:-${HOME}/Projects/bifrost/app/bifrost-desktop/src-tauri/target/release/bifrost}"
BIFROST_REPO="${NYX_BIFROST_REPO:-${HOME}/Projects/bifrost}"
if [[ ! -x "${BIFROST_BIN}" && -x /usr/bin/bifrost ]]; then
  warn "built binary not found at ${BIFROST_BIN} — falling back to the installed /usr/bin/bifrost"
  BIFROST_BIN="/usr/bin/bifrost"
fi

if [[ -x "${BIFROST_BIN}" ]]; then
  BIFROST_SHA="$(sha256sum "${BIFROST_BIN}" | cut -d' ' -f1)"
  printf "  ${B}bifrost binary:${R} %s\n" "${BIFROST_BIN}"
  printf "  ${B}sha256:${R}         %s\n" "${BIFROST_SHA}"

  install -Dm0755 "${BIFROST_BIN}" "${PROFILE_DIR}/airootfs/usr/bin/bifrost"

  # bifrost-guardian CLI wrapper — identical to packaging/PKGBUILD's
  # package() step, generated inline so this doesn't depend on host state.
  install -Dm0755 /dev/stdin "${PROFILE_DIR}/airootfs/usr/bin/bifrost-guardian" <<'BIFROSTGUARDIAN'
#!/bin/bash
export PYTHONPATH=/usr/lib/bifrost${PYTHONPATH:+:$PYTHONPATH}
export HEIMDALL_CONFIG_PATH="${HEIMDALL_CONFIG_PATH:-/etc/heimdall/heimdall_config.json}"
if [[ "${BIFROST_GUARDIAN_RUN_MODE:-app}" == "service" ]]; then
  if ! python3 - "$HEIMDALL_CONFIG_PATH" <<'PY'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
mode = "persistent"
if path.exists():
    try:
        mode = str(json.loads(path.read_text(encoding="utf-8")).get(
            "guardian_persistence_mode",
            "persistent",
        )).strip().lower()
    except Exception:
        mode = "persistent"
sys.exit(0 if mode != "session_only" else 1)
PY
  then
    echo "[bifrost-guardian] session-only mode active; skipping service start." >&2
    exit 0
  fi
fi
exec python3 -m bifrost.guardian "$@"
BIFROSTGUARDIAN
  ok "binary + bifrost-guardian wrapper → /usr/bin/"

  if [[ -d "${BIFROST_REPO}/bifrost" && -d "${BIFROST_REPO}/heimdall" ]]; then
    BIFROST_LIB="${PROFILE_DIR}/airootfs/usr/lib/bifrost"
    rm -rf "${BIFROST_LIB}"
    mkdir -p "${BIFROST_LIB}"
    cp -a "${BIFROST_REPO}/bifrost" "${BIFROST_LIB}/bifrost"
    cp -a "${BIFROST_REPO}/heimdall" "${BIFROST_LIB}/heimdall"
    find "${BIFROST_LIB}" \( -name '*.bak' -o -name '__pycache__' \) -exec rm -rf {} + 2>/dev/null || true
    ok "guardian python source → /usr/lib/bifrost/{bifrost,heimdall}"
  else
    warn "Bifrost source repo not found at ${BIFROST_REPO} — guardian python source NOT staged"
    warn "bifrost-guardian.service will fail to start until /usr/lib/bifrost/ is populated"
  fi

  # Desktop entry — must match the live installed entry exactly (same
  # Exec= env BIFROST_GUARDIAN=... wiring verified against the running
  # session tonight).
  install -Dm0644 /dev/stdin "${PROFILE_DIR}/airootfs/usr/share/applications/bifrost.desktop" <<'BIFROSTDESKTOP'
[Desktop Entry]
Type=Application
Name=Bifrost
GenericName=Security Monitor
Comment=Heimdall Never Sleeps — AI-powered endpoint detection and response.
Exec=env BIFROST_GUARDIAN=/usr/lib/bifrost/bifrost/guardian.py /usr/bin/bifrost
Icon=bifrost
Terminal=false
StartupNotify=true
Categories=Utility;Security;
Keywords=security;edr;monitoring;heimdall;guardian;
BIFROSTDESKTOP
  ok "desktop entry → /usr/share/applications/bifrost.desktop"

  BIFROST_ICON_SRC="${BIFROST_REPO}/app/bifrost-desktop/src-tauri/icons/128x128@2x.png"
  if [[ -f "${BIFROST_ICON_SRC}" ]]; then
    install -Dm0644 "${BIFROST_ICON_SRC}" \
      "${PROFILE_DIR}/airootfs/usr/share/icons/hicolor/256x256/apps/bifrost.png"
    ok "icon → /usr/share/icons/hicolor/256x256/apps/bifrost.png"
  elif [[ -f /usr/share/icons/hicolor/256x256/apps/bifrost.png ]]; then
    install -Dm0644 /usr/share/icons/hicolor/256x256/apps/bifrost.png \
      "${PROFILE_DIR}/airootfs/usr/share/icons/hicolor/256x256/apps/bifrost.png"
    ok "icon → /usr/share/icons/hicolor/256x256/apps/bifrost.png (from live install, repo copy missing)"
  else
    warn "bifrost icon not found (checked repo + live /usr/share/icons) — Icon=bifrost will 404 to a fallback"
  fi

  if [[ -f "${BIFROST_REPO}/bifrost-guardian.service" ]]; then
    install -Dm0644 "${BIFROST_REPO}/bifrost-guardian.service" \
      "${PROFILE_DIR}/airootfs/usr/lib/systemd/system/bifrost-guardian.service"
    ok "systemd unit → /usr/lib/systemd/system/bifrost-guardian.service (installed, NOT enabled by default — opt-in per docs/NYXUS_BUILD_BRIEF.md §8.1)"
  else
    warn "bifrost-guardian.service not found in ${BIFROST_REPO} — not staged"
  fi

  # Default (non-secret) Heimdall config — deliberately NOT the live
  # /etc/heimdall/heimdall_config.json / bifrost.env, which are
  # machine-specific and may carry live tokens. Ship the same
  # zero-token template a fresh `pacman -U bifrost*.pkg.tar.zst`
  # install would use.
  if [[ -f "${BIFROST_REPO}/packaging/heimdall_config.json.default" ]]; then
    install -Dm0644 "${BIFROST_REPO}/packaging/heimdall_config.json.default" \
      "${PROFILE_DIR}/airootfs/etc/heimdall/heimdall_config.json"
    ok "default heimdall_config.json → /etc/heimdall/ (no secrets, dry_run:true, autonomous_actions_enabled:false)"
  else
    warn "packaging/heimdall_config.json.default not found — /etc/heimdall/ left empty"
  fi

  ok "NYXUS Master Hub (Bifrost) staged — window app-id per tauri.conf.json: watch.bifrost.desktop"
else
  warn "no bifrost binary found at ${BIFROST_BIN} or /usr/bin/bifrost — ISO will ship WITHOUT Bifrost"
  warn "set NYX_BIFROST_BIN=/path/to/bifrost to stage it, or build it first"
fi

# ── stage Meli — Honeypot Command Center (rev 2026-07-16, r2) ────────────
# First time Meli ships in this ISO. Same "copy prebuilt/installed
# artifacts into airootfs" pattern as Bifrost above — the canonical
# install surface is /opt/meli/app + /opt/meli/venv (see ~/Projects/meli
# ... NO: Meli's real install.sh/PKGBUILD live at /opt/meli/app, that's
# the source of truth used below, not the unrelated bifrost-daemon crate
# that happens to also be named "meli" under ~/Projects/meli).
#
# r2 (same night, follow-up instruction) — the user explicitly overrode
# the r1 judgment call: the honeypot Docker stack + its Meli bridges now
# ship as REAL, auto-starting components, not opt-in templates, so a
# fresh install matches this live machine. See the "stage the live
# honeypot/Docker stack" step further down for that half; this step still
# only covers the Meli app itself.
#
# Still deliberately NOT staged:
#   - ~/.local/share/meli/meli.db and any honeypot capture/log data —
#     personal live data, not install media. Ships with fresh-DB-on-
#     first-run behaviour instead (meli.database.init_db(), same as any
#     normal software install).
step "stage Meli — Honeypot Command Center (app, no live data)"
MELI_REPO="${NYX_MELI_REPO:-/opt/meli/app}"
if [[ -d "${MELI_REPO}" ]]; then
  MELI_APP_DEST="${PROFILE_DIR}/airootfs/opt/meli/app"
  rm -rf "${MELI_APP_DEST}"
  mkdir -p "${MELI_APP_DEST}"
  rsync -a \
    --exclude=".git" --exclude="__pycache__" --exclude="*.pyc" \
    --exclude=".venv" --exclude="venv" --exclude="dist" --exclude="build" \
    --exclude="*.egg-info" \
    "${MELI_REPO}/" "${MELI_APP_DEST}/"
  ok "app source → /opt/meli/app"

  MELI_VENV_SRC="${NYX_MELI_VENV:-/opt/meli/venv}"
  if [[ -d "${MELI_VENV_SRC}" ]]; then
    MELI_VENV_DEST="${PROFILE_DIR}/airootfs/opt/meli/venv"
    rm -rf "${MELI_VENV_DEST}"
    mkdir -p "$(dirname "${MELI_VENV_DEST}")"
    cp -a "${MELI_VENV_SRC}" "${MELI_VENV_DEST}"
    find "${MELI_VENV_DEST}" -iname "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    ok "prebuilt venv (meli package pip-installed, --system-site-packages) → /opt/meli/venv"
  else
    warn "${MELI_VENV_SRC} not found — Meli app source staged WITHOUT a working venv"
    warn "run /opt/meli/app/install.sh post-boot to build the venv, or set NYX_MELI_VENV"
  fi

  install -Dm0755 /dev/stdin "${PROFILE_DIR}/airootfs/usr/local/bin/meli" <<'MELILAUNCHER'
#!/usr/bin/env bash
# Meli launcher — mirrors install.sh's Phase 4 launcher exactly: the meli
# package is pip-installed into the venv, so python finds it natively.
exec /opt/meli/venv/bin/python -m meli "$@"
MELILAUNCHER
  ok "launcher → /usr/local/bin/meli"

  if [[ -f "${MELI_REPO}/meli.desktop" ]]; then
    install -Dm0644 "${MELI_REPO}/meli.desktop" "${PROFILE_DIR}/airootfs/usr/share/applications/meli.desktop"
    ok "desktop entry → /usr/share/applications/meli.desktop"
  fi
  for size in 16 32 48 64 128 256 512; do
    ICON_SRC="${MELI_REPO}/assets/icons/meli-${size}.png"
    if [[ -f "${ICON_SRC}" ]]; then
      install -Dm0644 "${ICON_SRC}" \
        "${PROFILE_DIR}/airootfs/usr/share/icons/hicolor/${size}x${size}/apps/meli.png"
    fi
  done
  if [[ -f "${MELI_REPO}/assets/icons/meli.svg" ]]; then
    install -Dm0644 "${MELI_REPO}/assets/icons/meli.svg" \
      "${PROFILE_DIR}/airootfs/usr/share/icons/hicolor/scalable/apps/meli.svg"
  fi
  ok "icons → /usr/share/icons/hicolor/*/apps/meli.{png,svg}"

  # systemd --user unit TEMPLATES → /usr/lib/systemd/user/, the standard
  # vendor-template location. r2: now ENABLED by default (globally, via
  # `systemctl --global enable` in customize_airootfs.sh) — the live
  # machine has meli.service + meli-ingest.service enabled today, and the
  # user explicitly asked for "everything like how it was before" on
  # first boot, superseding the earlier "let the Setup Wizard decide"
  # call. The EULA/setup wizard still runs on first launch of the GUI
  # (meli.service just starts the app; it does not silently skip
  # first-run onboarding), so this does not bypass consent screens.
  MELI_UNIT_COUNT=0
  for unit in meli.service meli-ingest.service meli-labyrinth-digest.service meli-labyrinth-digest.timer; do
    if [[ -f "${MELI_REPO}/${unit}" ]]; then
      install -Dm0644 "${MELI_REPO}/${unit}" "${PROFILE_DIR}/airootfs/usr/lib/systemd/user/${unit}"
      MELI_UNIT_COUNT=$((MELI_UNIT_COUNT + 1))
    fi
  done
  ok "${MELI_UNIT_COUNT} systemd --user unit templates → /usr/lib/systemd/user/ (globally enabled in customize_airootfs.sh)"

  ok "Meli app staged — fresh empty-DB install; personal meli.db NOT baked in"
else
  warn "Meli app not found at ${MELI_REPO} — ISO will ship WITHOUT Meli"
  warn "set NYX_MELI_REPO=/path/to/meli/app to stage it"
fi

# ── stage the live honeypot/Docker stack + Meli bridges (rev 2026-07-16, r2)
# The user explicitly overrode the earlier "templates only" judgment call:
# they want cowrie/conpot/dionaea/endlessh/heralding/http-honeypot to be
# REAL, running components on first boot of the installed system, matching
# this live machine exactly — not a manual opt-in.
#
# Design choice — autostart mechanism (documented per the task's request
# to justify zero-touch vs. first-boot-triggered):
#   On THIS live machine, docker.service is `enabled`, the six containers
#   already exist with `restart: unless-stopped`, and that restart policy
#   (not any bespoke unit) is 100% of what brings them back after a
#   reboot — Docker itself resurrects them the moment dockerd starts.
#   A brand-new install has no containers yet, so there is nothing for
#   that restart policy to resurrect on first boot. To reach the exact
#   same steady state with zero manual steps, we:
#     1. Pre-pull the images ON THE BUILD HOST via `docker save` (they are
#        already running here, so this is a local export, not a fresh
#        registry pull) and bake the tarballs into the ISO — this avoids
#        depending on network access / registry availability on someone
#        else's first boot, and guarantees the exact image digests this
#        machine is running right now, not "whatever :latest resolves to
#        later."
#     2. Run ONE first-boot fragment (/etc/nyxus-firstboot.d/06-honeypot-
#        stack.sh, using the project's existing first-boot-once framework)
#        that `docker load`s those tarballs (fast, offline) and then runs
#        `docker compose up -d` exactly once to CREATE the containers.
#     3. From that point on, behavior is identical to this live machine:
#        docker.service is enabled, containers carry restart:unless-
#        stopped, so every subsequent boot resurrects them with no unit
#        of ours involved at all — same mechanism, not a re-implementation.
#   This is "zero-touch" from the installing user's perspective (no wizard
#   click, no manual `docker compose up`) while still being safe to run
#   inside the shared firstboot budget (offline `docker load` instead of a
#   multi-GB network pull racing a timeout).
#
# The Meli bridges (cowrie/conpot/dionaea/endlessh/heralding/http →
# meli/events/ingest over MQTT) are staged as the exact systemd --user
# units currently `enabled` on this machine (confirmed via `systemctl
# --user list-unit-files '*bridge*'`), globally enabled the same way.
#
# Belt-and-suspenders safety kept from the r1 pass despite going "real":
#   - Grafana's live admin password is NOT baked in — a fresh random one
#     is generated by the firstboot fragment and written (root-only) to
#     /root/nyxus-grafana-admin-password.txt, mirroring how Bifrost ships
#     a zero-token config instead of live secrets.
#   - The DOCKER-USER egress-lockdown firewall (hardening/nyxus-honeypot-
#     firewall.sh) is staged and ENABLED even though it is not yet
#     enabled on this particular live machine — it was clearly written
#     for exactly this purpose (blocks the honeypot subnet from pivoting
#     to the LAN/host while leaving inbound capture + outbound-to-internet
#     intact) and costs nothing to turn on for install media going onto
#     an unknown target network.
#   - Live capture data (~/Projects/honeypot/logs, data/, noc-data/) is
#     NOT staged — only app/config/compose/images, so the fresh install
#     starts with empty capture history, same "fresh DB" principle as Meli.
step "stage the live honeypot/Docker stack (cowrie/conpot/dionaea/endlessh/heralding/http)"
HONEYPOT_SRC="${NYX_HONEYPOT_REPO:-${HOME}/Projects/honeypot}"
HONEYPOT_DEST="${PROFILE_DIR}/airootfs/opt/honeypot"
if [[ -d "${HONEYPOT_SRC}" && -f "${HONEYPOT_SRC}/docker-compose.yml" ]]; then
  rm -rf "${HONEYPOT_DEST}"
  mkdir -p "${HONEYPOT_DEST}"/{logs,data,images}

  install -Dm0644 "${HONEYPOT_SRC}/docker-compose.yml" "${HONEYPOT_DEST}/docker-compose.yml"
  [[ -f "${HONEYPOT_SRC}/cowrie/etc/userdb.txt" ]] && \
    install -Dm0644 "${HONEYPOT_SRC}/cowrie/etc/userdb.txt" "${HONEYPOT_DEST}/cowrie/etc/userdb.txt"
  [[ -f "${HONEYPOT_SRC}/http-honeypot/server.js" ]] && \
    install -Dm0644 "${HONEYPOT_SRC}/http-honeypot/server.js" "${HONEYPOT_DEST}/http-honeypot/server.js"
  [[ -f "${HONEYPOT_SRC}/prometheus/prometheus.yml" ]] && \
    install -Dm0644 "${HONEYPOT_SRC}/prometheus/prometheus.yml" "${HONEYPOT_DEST}/prometheus/prometheus.yml"
  [[ -f "${HONEYPOT_SRC}/promtail/promtail.yml" ]] && \
    install -Dm0644 "${HONEYPOT_SRC}/promtail/promtail.yml" "${HONEYPOT_DEST}/promtail/promtail.yml"
  ok "docker-compose.yml + service configs → /opt/honeypot/"

  # .env — NOT the live one verbatim (it carries a real Grafana admin
  # password + a stale Replit API URL unrelated to the current bridge
  # design). Ship a placeholder the firstboot fragment replaces.
  install -Dm0600 /dev/stdin "${HONEYPOT_DEST}/.env" <<'HONEYPOTENV'
# Generated at bake time — GF_SECURITY_ADMIN_PASSWORD is replaced with a
# fresh random value by /etc/nyxus-firstboot.d/06-honeypot-stack.sh on
# first boot (see /root/nyxus-grafana-admin-password.txt afterward).
GF_SECURITY_ADMIN_PASSWORD=CHANGE_ME_ON_FIRST_BOOT
HONEYPOTENV
  ok "env template → /opt/honeypot/.env (password generated on first boot, not baked in)"

  # Meli bridge scripts — same six files actually running on this
  # machine, with their hardcoded ~/Projects/honeypot paths rewritten to
  # the new system-wide /opt/honeypot install path (staged COPY only; the
  # live source files under ~/Projects/honeypot are untouched).
  BRIDGE_COUNT=0
  for bridge in cowrie_to_meli.py conpot_to_meli.py dionaea_to_meli.py \
                endlessh_to_meli.py heralding_to_meli.py http_honeypot_to_meli.py; do
    if [[ -f "${HONEYPOT_SRC}/${bridge}" ]]; then
      install -Dm0755 "${HONEYPOT_SRC}/${bridge}" "${HONEYPOT_DEST}/${bridge}"
      sed -i \
        -e 's#Path\.home() / "Projects/honeypot/#Path("/opt/honeypot/#' \
        -e 's#/home/cosmic/Projects/honeypot/#/opt/honeypot/#g' \
        "${HONEYPOT_DEST}/${bridge}"
      BRIDGE_COUNT=$((BRIDGE_COUNT + 1))
    fi
  done
  ok "${BRIDGE_COUNT} honeypot→Meli bridge scripts → /opt/honeypot/ (paths rewritten for /opt/honeypot)"

  # Bridge systemd --user units — the exact ones `enabled` on this
  # machine right now (systemctl --user list-unit-files '*bridge*'),
  # ExecStart/log paths rewritten the same way, staged as vendor
  # templates and globally enabled in customize_airootfs.sh.
  BRIDGE_UNIT_COUNT=0
  BRIDGE_UNIT_SRC="${HOME}/.config/systemd/user"
  for unit in cowrie-bridge.service conpot-bridge.service dionaea-bridge.service \
              endlessh-bridge.service heralding-bridge.service http-bridge.service; do
    if [[ -f "${BRIDGE_UNIT_SRC}/${unit}" ]]; then
      install -Dm0644 "${BRIDGE_UNIT_SRC}/${unit}" "${PROFILE_DIR}/airootfs/usr/lib/systemd/user/${unit}"
      sed -i \
        -e 's#/home/cosmic/Projects/honeypot/#/opt/honeypot/#g' \
        "${PROFILE_DIR}/airootfs/usr/lib/systemd/user/${unit}"
      BRIDGE_UNIT_COUNT=$((BRIDGE_UNIT_COUNT + 1))
    fi
  done
  if (( BRIDGE_UNIT_COUNT > 0 )); then
    ok "${BRIDGE_UNIT_COUNT} bridge systemd --user units → /usr/lib/systemd/user/ (globally enabled)"
  else
    warn "no live bridge unit files found under ${BRIDGE_UNIT_SRC} — bridges staged without units, add manually"
  fi

  # Egress-lockdown firewall — staged + enabled even though it is not
  # currently enabled on THIS live machine (see step comment above).
  if [[ -f "${HONEYPOT_SRC}/hardening/nyxus-honeypot-firewall.sh" ]]; then
    install -Dm0755 "${HONEYPOT_SRC}/hardening/nyxus-honeypot-firewall.sh" \
      "${PROFILE_DIR}/airootfs/usr/local/bin/nyxus-honeypot-firewall"
    install -Dm0644 "${HONEYPOT_SRC}/hardening/nyxus-honeypot-firewall.service" \
      "${PROFILE_DIR}/airootfs/usr/lib/systemd/system/nyxus-honeypot-firewall.service"
    sed -i \
      -e 's#/home/cosmic/Projects/honeypot/hardening/nyxus-honeypot-firewall\.sh#/usr/local/bin/nyxus-honeypot-firewall#' \
      "${PROFILE_DIR}/airootfs/usr/lib/systemd/system/nyxus-honeypot-firewall.service"
    ok "egress-lockdown firewall → /usr/local/bin/nyxus-honeypot-firewall (+ unit, enabled)"
  fi
  if [[ -f "${HONEYPOT_SRC}/hardening/nyxus-fim.rules" ]]; then
    install -Dm0640 "${HONEYPOT_SRC}/hardening/nyxus-fim.rules" \
      "${PROFILE_DIR}/airootfs/etc/audit/rules.d/nyxus-fim.rules"
    ok "FIM audit ruleset → /etc/audit/rules.d/nyxus-fim.rules (auditd already enabled by base profile — lights up Bifrost's FIM panel)"
  fi

  # Pre-pull the images this machine is ACTUALLY running right now, via a
  # local export (no registry round-trip needed since they're already
  # here) — guarantees first boot matches this machine's exact digests
  # and needs no network.
  HONEYPOT_IMAGES=(
    "cowrie/cowrie:latest"
    "grafana/loki:latest"
    "node:20-alpine"
    "grafana/grafana:latest"
    "prom/prometheus:latest"
    "heywoodlh/heralding:latest"
    "linuxserver/endlessh:latest"
    "grafana/promtail:latest"
    "honeynet/conpot:latest"
    "dinotools/dionaea:latest"
  )
  if command -v docker >/dev/null 2>&1; then
    IMG_SAVED=0
    for img in "${HONEYPOT_IMAGES[@]}"; do
      if docker image inspect "${img}" >/dev/null 2>&1; then
        TAR_NAME="$(echo "${img}" | tr '/:' '__').tar"
        printf "  ${B}saving:${R} %s\n" "${img}"
        docker save "${img}" -o "${HONEYPOT_DEST}/images/${TAR_NAME}"
        IMG_SAVED=$((IMG_SAVED + 1))
      else
        warn "image ${img} not present on build host — will need a network pull on first boot"
      fi
    done
    ok "${IMG_SAVED}/${#HONEYPOT_IMAGES[@]} honeypot images pre-pulled → /opt/honeypot/images/ ($(du -sh "${HONEYPOT_DEST}/images" 2>/dev/null | cut -f1))"
  else
    warn "docker not available on build host — images NOT pre-pulled, first boot will need network access"
  fi

  # First-boot fragment — loads the pre-pulled images and brings the
  # stack up exactly once, using the project's existing firstboot-once
  # framework (see /usr/local/sbin/nyxus-firstboot).
  install -Dm0755 /dev/stdin \
    "${PROFILE_DIR}/airootfs/etc/nyxus-firstboot.d/06-honeypot-stack.sh" <<'HONEYPOTFIRSTBOOT'
#!/usr/bin/env bash
# NYXUS firstboot · bring the honeypot/Docker stack up exactly once.
# After this, docker.service + each container's restart:unless-stopped
# policy is 100% of what keeps them running across future reboots —
# same mechanism as the machine this ISO was built from, no extra unit.
set -u
MARKER=/var/lib/nyxus/honeypot-stack.done
[[ -f "${MARKER}" ]] && exit 0

# NEVER on live media (2026-07-28). nyxus-firstboot.service is Type=oneshot
# and WantedBy=multi-user.target, so multi-user.target does not complete until
# ExecStart RETURNS — and graphical.target is Requires+After multi-user.target,
# with greetd behind it. That puts this script directly on the critical path to
# the login screen: ~1GB of `docker load` off a USB stick plus ten containers
# starting, measured at 102s before the greeter appeared. On live media the
# containers are pure waste anyway (restart:unless-stopped state lives in the
# tmpfs overlay and is discarded at shutdown), and the marker is discarded too,
# so it re-ran on EVERY boot. The unit's own header says "first boot of an
# installed system" — this makes the code match that intent.
if [[ -d /run/archiso ]] || grep -qa 'archisobasedir' /proc/cmdline 2>/dev/null; then
  echo "[firstboot] live media detected — skipping honeypot stack (installed systems only)"
  exit 0
fi

if ! command -v docker >/dev/null 2>&1; then
  echo "[firstboot] docker not installed — skipping honeypot stack"
  exit 0
fi
systemctl start docker.service 2>/dev/null

cd /opt/honeypot || exit 0

if grep -q '^GF_SECURITY_ADMIN_PASSWORD=CHANGE_ME_ON_FIRST_BOOT$' .env 2>/dev/null; then
  GEN_PW="$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 20)"
  sed -i "s/^GF_SECURITY_ADMIN_PASSWORD=.*/GF_SECURITY_ADMIN_PASSWORD=${GEN_PW}/" .env
  {
    echo "Grafana admin password (generated on first boot): ${GEN_PW}"
    echo "Log in at http://localhost:3000 (user: admin)"
  } > /root/nyxus-grafana-admin-password.txt
  chmod 0600 /root/nyxus-grafana-admin-password.txt
fi

if [[ -d images ]]; then
  for tar in images/*.tar; do
    [[ -f "${tar}" ]] && docker load -i "${tar}"
  done
fi

if docker compose -f docker-compose.yml --env-file .env up -d; then
  echo "[firstboot] honeypot stack started"
else
  echo "[firstboot] honeypot stack failed to start — check 'docker compose logs' in /opt/honeypot"
fi

mkdir -p /var/lib/nyxus
date -Iseconds > "${MARKER}"
HONEYPOTFIRSTBOOT
  ok "firstboot fragment → /etc/nyxus-firstboot.d/06-honeypot-stack.sh (docker load + compose up -d, once)"

  # The shared firstboot budget (TimeoutStartSec) needs headroom for a
  # multi-GB `docker load` + container creation alongside fragments 01-05.
  NYXFB_UNIT="${PROFILE_DIR}/airootfs/etc/systemd/system/nyxus-firstboot.service"
  if [[ -f "${NYXFB_UNIT}" ]]; then
    sed -i -E 's/^TimeoutStartSec=.*/TimeoutStartSec=900s/' "${NYXFB_UNIT}"
    ok "nyxus-firstboot.service TimeoutStartSec → 900s (room for offline docker load of the honeypot images)"
  fi

  ok "honeypot/Docker stack staged — fresh install, no live capture history, auto-starts once on first boot then behaves exactly like this machine"
else
  warn "honeypot stack not found at ${HONEYPOT_SRC} (or no docker-compose.yml) — ISO will ship WITHOUT the honeypot stack"
  warn "set NYX_HONEYPOT_REPO=/path/to/honeypot to stage it"
fi

# ── stage jeTT AI Security Daemon — the real, fixed Jett (rev 2026-07-16)
# First time Jett ships in this ISO. Canonical packaged layout matches
# ~/Projects/jeTT/install.sh exactly (binary → /usr/local/bin,
# engine → /usr/local/lib/jett, unit → EnvironmentFile=-/etc/default/jett)
# rather than the live dev checkout's ad-hoc ~/Projects/jeTT/target paths.
#
# Binary source precedence — a separate in-progress task may still be
# rebuilding Jett's CUDA/eBPF binary in an isolated build dir without
# having restarted the live service yet, so grabbing whatever now sits at
# target/release/jett-daemon on disk is NOT safe (it may be that WIP
# build, half-linked or untested):
#   1. NYX_JETT_BIN override, if set
#   2. the EXACT bytes of the currently-running jett-daemon process, read
#      straight out of /proc/<pid>/exe — this is what's actually
#      confirmed active (systemctl is-active) and producing verdicts in
#      the journal right now, not whatever the on-disk file currently is
#   3. on-disk target/release/jett-daemon, last resort, explicitly
#      flagged as unverified in the build log
step "stage jeTT AI Security Daemon (real, fixed Jett)"
JETT_REPO="${NYX_JETT_REPO:-${HOME}/Projects/jeTT}"
JETT_BIN=""
JETT_SRC_DESC=""

if [[ -n "${NYX_JETT_BIN:-}" && -x "${NYX_JETT_BIN}" ]]; then
  JETT_BIN="${NYX_JETT_BIN}"
  JETT_SRC_DESC="explicit NYX_JETT_BIN override"
elif systemctl is-active --quiet jett-daemon 2>/dev/null; then
  JETT_PID="$(systemctl show -p MainPID --value jett-daemon 2>/dev/null || echo 0)"
  if [[ "${JETT_PID}" != "0" && -r "/proc/${JETT_PID}/exe" ]] \
     && cp "/proc/${JETT_PID}/exe" /tmp/nyx-jett-daemon-live.bin 2>/dev/null; then
    chmod 0755 /tmp/nyx-jett-daemon-live.bin
    JETT_BIN=/tmp/nyx-jett-daemon-live.bin
    JETT_SRC_DESC="live-running jett-daemon, pid ${JETT_PID} — confirmed active via systemctl is-active + verdicts observed in journalctl; read directly from /proc/${JETT_PID}/exe (NOT the on-disk build, which a separate GPU-restore rebuild may have already overwritten without restarting the service)"
  else
    warn "jett-daemon.service is active but its /proc/<pid>/exe was not readable (need root) — falling back"
  fi
fi

if [[ -z "${JETT_BIN}" && -x "${JETT_REPO}/target/release/jett-daemon" ]]; then
  JETT_BIN="${JETT_REPO}/target/release/jett-daemon"
  JETT_SRC_DESC="on-disk build at ${JETT_REPO}/target/release/jett-daemon — UNVERIFIED, jett-daemon.service was not active/readable at bake time so this could be a WIP rebuild"
  warn "could not confirm a live jett-daemon process — falling back to the on-disk build (unverified)"
fi

if [[ -n "${JETT_BIN}" ]]; then
  JETT_SHA="$(sha256sum "${JETT_BIN}" | cut -d' ' -f1)"
  printf "  ${B}jett-daemon source:${R} %s\n" "${JETT_SRC_DESC}"
  printf "  ${B}sha256:${R}             %s\n" "${JETT_SHA}"

  install -Dm0755 "${JETT_BIN}" "${PROFILE_DIR}/airootfs/usr/local/bin/jett-daemon"
  install -d -m 0750 "${PROFILE_DIR}/airootfs/var/log/jett"
  install -d -m 0750 "${PROFILE_DIR}/airootfs/var/jett/quarantine"
  install -d -m 0755 "${PROFILE_DIR}/airootfs/opt/jett/models"
  ok "jett-daemon binary → /usr/local/bin/jett-daemon"

  if [[ -x "${JETT_REPO}/target/release/jeTT" ]]; then
    install -Dm0755 "${JETT_REPO}/target/release/jeTT" "${PROFILE_DIR}/airootfs/usr/local/lib/jett/jeTT"
    ok "jeTT inference engine binary → /usr/local/lib/jett/jeTT"
  else
    warn "jeTT engine binary not found at ${JETT_REPO}/target/release/jeTT — CLI/eval features unavailable"
  fi

  if [[ -f "${JETT_REPO}/jett" ]]; then
    install -Dm0755 "${JETT_REPO}/jett" "${PROFILE_DIR}/airootfs/usr/local/bin/jett"
    ln -sf jett "${PROFILE_DIR}/airootfs/usr/local/bin/jeTT"
    # The wrapper resolves scripts/jett-ctl.sh relative to its OWN
    # on-disk location (readlink -f "$BASH_SOURCE"), which only works if
    # scripts/ ships alongside it — install.sh's own packaged layout has
    # this same requirement, so mirror it rather than leave `jett menu`
    # broken on a non-dev-checkout install.
    if [[ -f "${JETT_REPO}/scripts/jett-ctl.sh" ]]; then
      install -Dm0755 "${JETT_REPO}/scripts/jett-ctl.sh" \
        "${PROFILE_DIR}/airootfs/usr/local/bin/scripts/jett-ctl.sh"
    fi
    ok "jett control-panel wrapper → /usr/local/bin/jett (+ jeTT symlink, scripts/jett-ctl.sh)"
  fi

  if [[ -f "${JETT_REPO}/jett-daemon.service" ]]; then
    install -Dm0644 "${JETT_REPO}/jett-daemon.service" \
      "${PROFILE_DIR}/airootfs/usr/lib/systemd/system/jett-daemon.service"
    ok "systemd unit → /usr/lib/systemd/system/jett-daemon.service (enabled by customize_airootfs.sh — safe default is learn+dry-run, see override.conf below)"
  else
    warn "jett-daemon.service not found in ${JETT_REPO} — not staged, enable step in customize_airootfs.sh will no-op"
  fi

  # Vendor override.conf — the ONLY place effective mode gets decided.
  # Hard-pinned to learn + dry-run. Everything established tonight said
  # false positives need human review before any enforce default ships —
  # do not change this to enforce without that review happening first.
  install -Dm0644 /dev/stdin \
    "${PROFILE_DIR}/airootfs/usr/lib/systemd/system/jett-daemon.service.d/override.conf" <<'JETTOVERRIDE'
[Service]
Environment="JETT_MODE=learn"
Environment="JETT_ENFORCE_DRY_RUN=1"
Environment="JETT_TELEMETRY=both"
JETTOVERRIDE
  ok "override.conf → learn mode + dry-run pinned as the shipped default"

  # /etc/default/jett — the EnvironmentFile the unit reads. Pinned to
  # learn mode here too so both layers agree (belt-and-suspenders: the
  # live host's /etc/default/jett said enforce tonight while a drop-in
  # silently forced it back to learn — ship it consistent instead of
  # relying on override.conf alone to save us from that kind of drift).
  install -Dm0644 /dev/stdin "${PROFILE_DIR}/airootfs/etc/default/jett" <<'JETTDEFAULT'
JETT_MODEL=/opt/jett/models/jett-r6-q4_k_m.gguf
JETT_MODE=learn
JETT_ENFORCE_DRY_RUN=1
JETT_TELEMETRY=both
JETT_ALLOWLIST=/etc/jett/allowlist.conf
JETT_MODEL_PIN=/etc/jett/model.sha256
JETTDEFAULT
  ok "default env → /etc/default/jett (JETT_MODE=learn, dry-run — model NOT bundled, per INSTALL.md drop your GGUF at /opt/jett/models/)"

  # Allowlist + model-pin framework — the mechanism, not necessarily this
  # exact machine's live tuning. Prefer the live host's current (fixed)
  # allowlist since it's confirmed working tonight; fall back to the
  # repo's documented example template.
  if [[ -f /etc/jett/allowlist.conf ]]; then
    install -Dm0644 /etc/jett/allowlist.conf "${PROFILE_DIR}/airootfs/etc/jett/allowlist.conf"
    ok "allowlist (live, confirmed-working copy) → /etc/jett/allowlist.conf"
  elif [[ -f "${JETT_REPO}/config/allowlist.example.conf" ]]; then
    install -Dm0644 "${JETT_REPO}/config/allowlist.example.conf" "${PROFILE_DIR}/airootfs/etc/jett/allowlist.conf"
    ok "allowlist (documented example template) → /etc/jett/allowlist.conf"
  else
    warn "no allowlist source found — /etc/jett/allowlist.conf not staged (daemon falls back to \$HOME + system-path defaults per its own docs)"
  fi
  if [[ -f /etc/jett/model.sha256 ]]; then
    install -Dm0644 /etc/jett/model.sha256 "${PROFILE_DIR}/airootfs/etc/jett/model.sha256"
    ok "model.sha256 pin → /etc/jett/model.sha256"
  fi

  ok "jeTT AI Security Daemon staged — default mode: LEARN + dry-run; model GGUF NOT bundled (drop it in /opt/jett/models/ post-install, same as upstream)"
else
  warn "no jett-daemon binary available (live service inactive/unreadable AND no on-disk build) — ISO will ship WITHOUT Jett"
  warn "set NYX_JETT_BIN=/path/to/jett-daemon to stage it, or ensure jett-daemon.service is running+readable at bake time"
fi

# ── stage Arsenal — GowskiNet Security Hub (TUI launcher) ────────────────
# rev 2026-07-17 (r2 2026-07-21) — Arsenal is the operator's app-launcher
# hub: a Rust ratatui TUI (`arsenal-hub`) that reads a registry.toml of
# every tool and launches/monitors them.
#
# Unlike the other "stage from a local dev checkout" steps above, the
# hub binary, registry, launcher, desktop entry, and every tool's source
# tree (GSL/RedForge/Forge/CIPHER/AI-Cyber-Defense-Trainer/axiom/c2) are
# committed directly under this profile's airootfs/ — mkarchiso picks
# them up with no extra staging needed, same as any other tracked file.
# No .env or *.db ships (see .gitignore): each app's own one-shot
# `~/Arsenal/setup-apps.sh` creates its database role/schema and seeds a
# fresh admin login after install, so nobody's local secrets/lab history
# ends up baked into a distributable image.
#
# This step is ONLY for refreshing that committed tree from a newer local
# checkout before a bake (e.g. after rebuilding the Rust hub, or editing
# registry.toml) — it is a no-op when ${ARSENAL_REPO} doesn't exist,
# which is the common case (CI, or anyone else's build host).
step "stage Arsenal — GowskiNet Security Hub (TUI launcher)"
ARSENAL_REPO="${NYX_ARSENAL_REPO:-${HOME}/Arsenal}"
if [[ -d "${ARSENAL_REPO}" && -f "${ARSENAL_REPO}/registry.toml" ]]; then
  ARSENAL_BIN="${NYX_ARSENAL_BIN:-${ARSENAL_REPO}/hub/target/release/arsenal-hub}"
  ARSENAL_SKEL="${SKEL}/Arsenal"
  mkdir -p "${ARSENAL_SKEL}" \
           "${PROFILE_DIR}/airootfs/etc/arsenal" \
           "${PROFILE_DIR}/airootfs/opt/arsenal/tools"

  # 1. hub binary → /usr/local/bin/arsenal-hub (+ friendly `arsenal` wrapper)
  if [[ -x "${ARSENAL_BIN}" ]]; then
    install -Dm0755 "${ARSENAL_BIN}" "${PROFILE_DIR}/airootfs/usr/local/bin/arsenal-hub"
    printf "  ${B}arsenal-hub sha256:${R} %s\n" "$(sha256sum "${ARSENAL_BIN}" | cut -d' ' -f1)"
    ok "hub binary → /usr/local/bin/arsenal-hub (refreshed from ${ARSENAL_REPO})"
  else
    warn "arsenal-hub binary not found at ${ARSENAL_BIN} — build it (cd '${ARSENAL_REPO}/hub' && cargo build --release) or set NYX_ARSENAL_BIN"
    warn "keeping the already-committed arsenal-hub binary as-is"
  fi

  # 2. registry.toml — rewrite hardcoded live paths to shipped locations.
  #    /etc/arsenal/ (system reference) + /etc/skel/Arsenal/ (per-user seed).
  _reg_tmp="$(mktemp)"
  sed -E \
    -e 's#/home/cosmic/GowskiNet-Vault/Security/#/opt/arsenal/tools/#g' \
    -e 's#/home/cosmic/GowskiNet-Vault/AI/#/opt/arsenal/tools/#g' \
    -e 's#/home/cosmic/Projects/axiom#/opt/arsenal/tools/axiom#g' \
    -e 's#/home/cosmic/Projects/c2#/opt/arsenal/tools/c2#g' \
    -e 's#/home/cosmic/Projects/jeTT#/usr/local/lib/jett#g' \
    -e 's#/home/cosmic/Projects/bifrost#/usr/lib/bifrost#g' \
    -e 's#/home/cosmic/Projects/meli#/opt/meli/app#g' \
    -e 's#/home/cosmic/Projects/honeypot#/opt/honeypot#g' \
    "${ARSENAL_REPO}/registry.toml" > "${_reg_tmp}"
  install -Dm0644 "${_reg_tmp}" "${PROFILE_DIR}/airootfs/etc/arsenal/registry.toml"
  install -Dm0644 "${_reg_tmp}" "${ARSENAL_SKEL}/registry.toml"
  rm -f "${_reg_tmp}"
  ok "registry.toml → /etc/arsenal/ + /etc/skel/Arsenal/ (live paths rewritten to shipped locations, refreshed)"

  # 2b. setup-apps.sh — one-shot bring-up for the web tools.
  if [[ -f "${ARSENAL_REPO}/setup-apps.sh" ]]; then
    install -Dm0755 "${ARSENAL_REPO}/setup-apps.sh" \
      "${PROFILE_DIR}/airootfs/usr/local/bin/nyxus-setup-apps"
    install -Dm0755 "${ARSENAL_REPO}/setup-apps.sh" \
      "${ARSENAL_SKEL}/setup-apps.sh"
    ok "setup-apps.sh → /usr/local/bin/nyxus-setup-apps (0755) + /etc/skel/Arsenal/setup-apps.sh (refreshed)"
  fi

  # 3. Optional: refresh the tool source trees from a newer local checkout.
  #    Off by default — the committed trees already ship. Set
  #    NYX_STAGE_ARSENAL_APPS=1 to pull in local changes before a bake.
  if [[ "${NYX_STAGE_ARSENAL_APPS:-0}" == "1" ]]; then
    warn "NYX_STAGE_ARSENAL_APPS=1 — refreshing Arsenal tool repos into /opt/arsenal/tools/"
    declare -A _arsenal_srcs=(
      [GSL]="/home/cosmic/GowskiNet-Vault/Security/GSL"
      [RedForge]="/home/cosmic/GowskiNet-Vault/Security/RedForge"
      [Forge]="/home/cosmic/GowskiNet-Vault/Security/Forge"
      [CIPHER]="/home/cosmic/GowskiNet-Vault/Security/CIPHER"
      [AI-Cyber-Defense-Trainer]="/home/cosmic/GowskiNet-Vault/AI/AI-Cyber-Defense-Trainer"
      [axiom]="/home/cosmic/Projects/axiom"
      [c2]="/home/cosmic/Projects/c2"
    )
    for _name in "${!_arsenal_srcs[@]}"; do
      _src="${_arsenal_srcs[$_name]}"
      if [[ -d "${_src}" ]]; then
        rsync -a --exclude='.git' --exclude='node_modules' --exclude='.venv' \
              --exclude='venv' --exclude='target' --exclude='__pycache__' \
              --exclude='dist' --exclude='build' --exclude='.env' \
              --exclude='*.db' --exclude='*.db-shm' --exclude='*.db-wal' \
              "${_src}/" "${PROFILE_DIR}/airootfs/opt/arsenal/tools/${_name}/"
        ok "refreshed ${_name} → /opt/arsenal/tools/${_name}"
      else
        warn "Arsenal tool source not found: ${_src} — leaving the already-committed tree as-is"
      fi
    done
  fi

  ok "Arsenal staged — run 'arsenal' or search 'Arsenal' in the launcher"
else
  ok "Arsenal repo not found at ${ARSENAL_REPO} — using the already-committed Arsenal tree as shipped (this is the common case)"
fi

# ── mirror OS-level docs into /etc/nyxus/ ────────────────────────────────
step "mirror OS-level docs into airootfs/etc/nyxus/"
NYXUS_DOCS="${PROFILE_DIR}/airootfs/etc/nyxus"
mkdir -p "${NYXUS_DOCS}"
for doc in LICENSE.md README.md CHANGELOG.md CREDITS.md; do
  if [[ -f "${REPO_ROOT}/${doc}" ]]; then
    install -m 0644 "${REPO_ROOT}/${doc}" "${NYXUS_DOCS}/${doc}"
  fi
done
ok "OS-level docs in /etc/nyxus/"

# ── bake the ISO ─────────────────────────────────────────────────────────
step "running mkarchiso (this takes 5-15 minutes)"
rm -rf "${WORK_DIR}"
mkdir -p "${OUT_DIR}"
mkarchiso -v -w "${WORK_DIR}" -o "${OUT_DIR}" "${PROFILE_DIR}"

# Rename to canonical filename
cd "${OUT_DIR}"
PRODUCED="$(ls -t *.iso | head -1)"
if [[ "${PRODUCED}" != "${ISO_NAME}" ]]; then
  mv "${PRODUCED}" "${ISO_NAME}"
fi
ok "ISO baked → ${OUT_DIR}/${ISO_NAME}"

# ── done ─────────────────────────────────────────────────────────────────
cat <<EOF

──────────────────────────────────────────────────────────────────────

  ${GOLD}NYXUS ISO ready.${R}

  ${B}file:${R}   ${PINK}${OUT_DIR}/${ISO_NAME}${R}
  ${B}size:${R}   $(du -h "${OUT_DIR}/${ISO_NAME}" | cut -f1)
  ${B}sha:${R}    $(sha256sum "${OUT_DIR}/${ISO_NAME}" | cut -d' ' -f1)

  ${PURPLE}burn / dd / Ventoy and boot.${R}

EOF
