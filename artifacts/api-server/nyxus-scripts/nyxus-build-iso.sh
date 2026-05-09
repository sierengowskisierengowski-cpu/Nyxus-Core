#!/usr/bin/env bash
# ============================================================================
#  NYXUS — nyxus-build-iso.sh                                  rev 2026-05-09 r1
#  ~/.local/bin/nyxus-build-iso  (or run from /tmp)
#
#  Curl-installable wrapper that bakes the bootable NYX ISO from the
#  iso-builder/nyx-profile/ archiso recipe in this repo. Designed to be
#  reviewed first, then run as root once the user has eyeballed it.
#
#  RECOMMENDED USAGE (safe — review before sudo):
#    curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus-build-iso.sh \
#      -o /tmp/nyxus-build-iso.sh
#    less /tmp/nyxus-build-iso.sh           # review what you're about to run
#    sudo bash /tmp/nyxus-build-iso.sh --yes
#
#  Constraints:
#   - Must run on Arch Linux (or arch-based) — checks /etc/os-release
#   - Must be root (refuses to run otherwise)
#   - Needs loop devices + ≥25GB free in workdir
#   - Idempotent — re-runs cleanly, reusing the cached profile checkout
#   - Self-diagnosing — fails LOUDLY on the mkinitcpio "Hook 'archiso'
#     cannot be found" / "errors were encountered during the build" class
#     of bugs so you don't ship a non-bootable ISO
#
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
set -euo pipefail

# ── colours ────────────────────────────────────────────────────────────────
B=$'\e[1m'; R=$'\e[0m'
WHITE=$'\e[38;5;255m'; DIM=$'\e[38;5;245m'
GOLD=$'\e[38;5;220m'; RED=$'\e[38;5;196m'; GREEN=$'\e[38;5;82m'

step() { printf "\n${WHITE}▌${R} ${B}%s${R}\n" "$*"; }
ok()   { printf "  ${GREEN}✓${R}  %s\n" "$*"; }
warn() { printf "  ${GOLD}!${R}  %s\n" "$*"; }
fail() { printf "  ${RED}✗${R}  %s\n" "$*" >&2; }
die()  { fail "$*"; exit 1; }

# ── resolve invoking user (so output lands in THEIR home, not /root) ──────
# When run via `sudo bash …`, $HOME=/root and ~ expands to /root, which is
# wrong — the user wants the ISO in their own ~/nyx-out. Use SUDO_USER to
# discover who actually invoked us, then look up their real home dir from
# /etc/passwd so we don't depend on the env var being preserved.
REAL_USER="${SUDO_USER:-$(id -un)}"
REAL_HOME="$(getent passwd "$REAL_USER" 2>/dev/null | cut -d: -f6)"
[[ -n "$REAL_HOME" && -d "$REAL_HOME" ]] || REAL_HOME="${HOME:-/root}"

# ── defaults (overridable via flags) ───────────────────────────────────────
PROFILE_REPO="https://github.com/sierengowskisierengowski-cpu/Nyxus-Core.git"
PROFILE_REF="main"
PROFILE_SUBDIR="iso-builder/nyx-profile"
SRC_CACHE="/var/lib/nyxus/profile-src"
OUT_DIR="${REAL_HOME}/nyx-out"
WORK_DIR="/var/tmp/nyxus-archiso-work"
ASSUME_YES="no"
KEEP_WORKDIR="no"
DATE_TAG="$(date +%Y.%m.%d)"

usage() {
  cat <<EOF
${B}nyxus-build-iso.sh${R}  —  build the NYX bootable ISO from the GitHub profile

Usage:
  sudo bash nyxus-build-iso.sh [OPTIONS]

Options:
  --profile-repo URL   Git repo containing iso-builder/nyx-profile/
                       (default: $PROFILE_REPO)
  --profile-ref REF    Branch / tag / commit to checkout
                       (default: $PROFILE_REF)
  --out DIR            Where the finished .iso lands
                       (default: $OUT_DIR)
  --workdir DIR        mkarchiso scratch space (large — needs disk)
                       (default: $WORK_DIR)
  --yes                Skip the interactive "proceed?" prompt
  --keep-workdir       Don't wipe \$WORK_DIR on success (for debugging)
  -h, --help           This help text

Output:
  \$OUT_DIR/nyxus-${DATE_TAG}.iso         (the bootable ISO)
  \$OUT_DIR/build-${DATE_TAG}.log         (full mkarchiso log)
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile-repo)  PROFILE_REPO="$2"; shift 2 ;;
    --profile-ref)   PROFILE_REF="$2"; shift 2 ;;
    --out)           OUT_DIR="$2"; shift 2 ;;
    --workdir)       WORK_DIR="$2"; shift 2 ;;
    --yes)           ASSUME_YES="yes"; shift ;;
    --keep-workdir)  KEEP_WORKDIR="yes"; shift ;;
    -h|--help)       usage; exit 0 ;;
    *)               die "unknown flag: $1   (run --help)" ;;
  esac
done

ISO_NAME="nyxus-${DATE_TAG}.iso"
LOG_FILE="${OUT_DIR}/build-${DATE_TAG}.log"

# ── preflight ──────────────────────────────────────────────────────────────
step "preflight checks"

# 1. Root
if [[ $EUID -ne 0 ]]; then
  die "must run as root (try: sudo bash $0 --yes)"
fi
ok "running as root"

# 2. Arch Linux
if [[ ! -f /etc/os-release ]]; then
  die "/etc/os-release missing — cannot identify distro"
fi
. /etc/os-release
case "${ID:-unknown}:${ID_LIKE:-}" in
  arch:*|*:*arch*|artix:*|endeavouros:*|manjaro:*|garuda:*)
    ok "distro: ${PRETTY_NAME:-$ID} (arch-family — supported)"
    ;;
  *)
    die "unsupported distro: ${PRETTY_NAME:-$ID}.  Need Arch or Arch-based with pacman + archiso."
    ;;
esac

# 3. pacman present
command -v pacman >/dev/null 2>&1 || die "pacman not found in PATH"
ok "pacman: $(pacman -V | head -1)"

# 4. loop devices
if [[ ! -e /dev/loop-control ]]; then
  warn "/dev/loop-control missing — attempting modprobe loop"
  modprobe loop || die "modprobe loop failed — kernel missing loop support?"
fi
ok "loop devices available"

# 5. disk space (need ≥25GB free in workdir parent)
WORK_PARENT="$(dirname "$WORK_DIR")"
mkdir -p "$WORK_PARENT" "$OUT_DIR"
FREE_GB=$(( $(df -BG --output=avail "$WORK_PARENT" 2>/dev/null | tail -1 | tr -dc '0-9') + 0 ))
if (( FREE_GB < 25 )); then
  warn "only ${FREE_GB}GB free in $WORK_PARENT — mkarchiso may fail (recommend ≥25GB, ideally 40GB)"
else
  ok "free space in $WORK_PARENT: ${FREE_GB}GB"
fi

# 6. plan
step "build plan"
cat <<EOF
  ${DIM}repo:${R}      $PROFILE_REPO
  ${DIM}ref:${R}       $PROFILE_REF
  ${DIM}profile:${R}   $PROFILE_SUBDIR
  ${DIM}cache:${R}     $SRC_CACHE
  ${DIM}workdir:${R}   $WORK_DIR
  ${DIM}out:${R}       $OUT_DIR
  ${DIM}iso name:${R}  $ISO_NAME
  ${DIM}log:${R}       $LOG_FILE
EOF

if [[ "$ASSUME_YES" != "yes" ]]; then
  echo
  read -r -p "  ${B}Proceed?${R} [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || die "aborted by user"
fi

# ── install build deps ─────────────────────────────────────────────────────
step "install build dependencies (archiso, git, squashfs-tools, rsync)"
pacman -Sy --needed --noconfirm archiso git squashfs-tools rsync \
  || die "pacman failed to install build deps"
ok "build deps installed"

command -v mkarchiso >/dev/null 2>&1 || die "mkarchiso missing after install — archiso package broken?"

# ── fetch / update profile from GitHub ────────────────────────────────────
step "sync profile from $PROFILE_REPO @ $PROFILE_REF"
mkdir -p "$(dirname "$SRC_CACHE")"
if [[ -d "$SRC_CACHE/.git" ]]; then
  ok "cached checkout exists at $SRC_CACHE — pulling latest"
  git -C "$SRC_CACHE" fetch --depth=1 origin "$PROFILE_REF" || die "git fetch failed"
  git -C "$SRC_CACHE" reset --hard "FETCH_HEAD" || die "git reset failed"
else
  ok "cloning fresh into $SRC_CACHE"
  git clone --depth=1 --branch "$PROFILE_REF" "$PROFILE_REPO" "$SRC_CACHE" \
    || die "git clone failed"
fi
PROFILE_SRC="$SRC_CACHE/$PROFILE_SUBDIR"
[[ -d "$PROFILE_SRC" ]] || die "profile dir not found in repo: $PROFILE_SUBDIR"
[[ -f "$PROFILE_SRC/profiledef.sh" ]] || die "$PROFILE_SRC/profiledef.sh missing — not a valid archiso profile"
[[ -f "$PROFILE_SRC/packages.x86_64" ]] || die "$PROFILE_SRC/packages.x86_64 missing"
ok "profile validated: $PROFILE_SRC"

# ── stage profile into a clean build dir (don't mutate the git checkout) ──
BUILD_PROFILE="$WORK_DIR/profile"
step "stage profile into $BUILD_PROFILE"
rm -rf "$WORK_DIR"
mkdir -p "$BUILD_PROFILE"
rsync -a "$PROFILE_SRC/" "$BUILD_PROFILE/"
ok "profile staged"

# ── run mkarchiso ──────────────────────────────────────────────────────────
step "run mkarchiso (this takes 10–25 minutes; full log → $LOG_FILE)"
MKARCHISO_WORK="$WORK_DIR/work"
MKARCHISO_OUT="$WORK_DIR/out"
mkdir -p "$MKARCHISO_WORK" "$MKARCHISO_OUT"

set +e
mkarchiso -v -w "$MKARCHISO_WORK" -o "$MKARCHISO_OUT" "$BUILD_PROFILE" 2>&1 | tee "$LOG_FILE"
RC=${PIPESTATUS[0]}
set -e

if (( RC != 0 )); then
  fail "mkarchiso exited non-zero (rc=$RC) — see $LOG_FILE"
  die "build FAILED"
fi

# ── post-build sanity (catch the silent mkinitcpio breakage) ──────────────
step "post-build sanity checks"
if grep -qE "Hook '?archiso'? cannot be found" "$LOG_FILE"; then
  fail "mkinitcpio could not find the 'archiso' hook — this means the resulting ISO will NOT boot"
  die "build aborted as broken (refusing to ship a non-bootable ISO)"
fi
if grep -qE "errors were encountered during the build" "$LOG_FILE"; then
  fail "mkinitcpio reported build errors — image may not be complete / bootable"
  die "build aborted as broken (refusing to ship a non-bootable ISO)"
fi
ok "no mkinitcpio hook errors in log"

# ── locate produced ISO and rename ─────────────────────────────────────────
PRODUCED_ISO="$(find "$MKARCHISO_OUT" -maxdepth 1 -type f -name '*.iso' | head -1)"
[[ -n "$PRODUCED_ISO" ]] || die "mkarchiso reported success but no .iso file found in $MKARCHISO_OUT"
FINAL_ISO="$OUT_DIR/$ISO_NAME"
mv -f "$PRODUCED_ISO" "$FINAL_ISO"
ISO_SIZE=$(du -h "$FINAL_ISO" | cut -f1)
ok "ISO ready: $FINAL_ISO  ($ISO_SIZE)"

# ── cleanup ───────────────────────────────────────────────────────────────
if [[ "$KEEP_WORKDIR" == "yes" ]]; then
  warn "leaving $WORK_DIR in place (--keep-workdir)"
else
  step "cleanup"
  rm -rf "$WORK_DIR"
  ok "removed $WORK_DIR"
fi

# ── done ───────────────────────────────────────────────────────────────────
step "DONE"
cat <<EOF
  ${GREEN}✓${R}  ${B}$ISO_NAME${R}  ($ISO_SIZE)
      ${DIM}→${R} $FINAL_ISO

  ${B}Flash to USB${R} (replace /dev/sdX with your real device — DESTROYS that disk):
      ${WHITE}sudo dd if=$FINAL_ISO of=/dev/sdX bs=4M status=progress oflag=sync${R}

  ${B}Or use Ventoy${R} — just copy the .iso onto a Ventoy-formatted USB.

  ${B}Build log:${R} $LOG_FILE
EOF
