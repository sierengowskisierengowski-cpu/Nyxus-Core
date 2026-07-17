#!/usr/bin/env bash
# nyxus-backup-for-reinstall.sh
#
# Full pre-wipe backup for a NYXUS clean-install migration.
# Mirrors the important parts of $HOME plus package lists and SSH/GPG keys
# onto an external destination (external drive, second internal drive, or
# a network mount), so everything can be restored after a fresh install with
# scripts/nyxus-restore-from-backup.sh.
#
# This script is READ-ONLY on the source (never deletes/modifies anything in
# $HOME). It only writes under the destination directory you give it.
#
# Usage:
#   ./nyxus-backup-for-reinstall.sh /path/to/destination [options]
#
# Options:
#   --dry-run        Show what would be copied/sized, write nothing.
#   --include-bulk   Also back up large "bulk" dirs skipped by default
#                     (Music, VirtualBox VMs, existing nyxus-*-backup-* dirs,
#                     the ~/Backups folder, staging dirs). Default: skipped,
#                     see MANIFEST.txt for the exact list.
#   --yes            Skip the confirmation prompt.
#   --resume-ts TS   Resume/continue an existing backup folder
#                     (nyxus-backup-TS) instead of creating a new
#                     timestamped one. rsync will skip files that are
#                     already present and unchanged, so this is safe to
#                     re-run after an interruption without re-copying
#                     everything from scratch.
#
# Requires: rsync, pacman (for package lists). Run as your normal user
# (cosmic), not root — it only reads your own home directory.

set -euo pipefail

SCRIPT_VERSION="1.1"
SRC_HOME="${HOME}"
DEST=""
DRY_RUN=0
INCLUDE_BULK=0
ASSUME_YES=0
RESUME_TS=""

log()  { printf '\033[1;36m[backup]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; }

usage() { sed -n '2,26p' "$0"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --include-bulk) INCLUDE_BULK=1; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    --resume-ts) RESUME_TS="$2"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    -*) err "Unknown option: $1"; usage; exit 1 ;;
    *) DEST="$1"; shift ;;
  esac
done

if [[ -z "$DEST" ]]; then
  err "You must supply a destination path."
  usage
  exit 1
fi

if [[ "$(id -u)" -eq 0 ]]; then
  err "Run this as your normal user (cosmic), not root."
  exit 1
fi

if [[ -n "$RESUME_TS" ]]; then
  TS="$RESUME_TS"
else
  TS="$(date +%Y%m%d-%H%M%S)"
fi
DEST_ROOT="${DEST%/}/nyxus-backup-${TS}"
if [[ -n "$RESUME_TS" ]]; then
  if [[ ! -d "$DEST_ROOT" ]]; then
    err "Cannot resume: '$DEST_ROOT' does not exist."
    exit 1
  fi
  log "Resuming existing backup folder: $DEST_ROOT"
fi

# ---------------------------------------------------------------------------
# Destination sanity checks
# ---------------------------------------------------------------------------
if [[ ! -d "$DEST" ]]; then
  err "Destination '$DEST' does not exist or is not a directory."
  err "Mount/connect your backup drive first, then point this script at it,"
  err "e.g. /run/media/cosmic/<drive-label> or /mnt/<something>."
  exit 1
fi

if [[ ! -w "$DEST" ]]; then
  err "Destination '$DEST' is not writable by $(whoami)."
  exit 1
fi

DEST_DEV="$(df --output=source "$DEST" 2>/dev/null | tail -n1 || true)"
SRC_DEV="$(df --output=source "$SRC_HOME" 2>/dev/null | tail -n1 || true)"
if [[ -n "$DEST_DEV" && "$DEST_DEV" == "$SRC_DEV" ]]; then
  err "Destination '$DEST' is on the SAME filesystem/device as \$HOME ($SRC_DEV)."
  err "That would put the backup on the very drive you're about to wipe. Refusing."
  exit 1
fi

log "Backup destination : $DEST_ROOT"
log "Destination device  : ${DEST_DEV:-unknown}"
log "Source home         : $SRC_HOME (on ${SRC_DEV:-unknown})"

AVAIL_KB="$(df --output=avail "$DEST" | tail -n1 | tr -d ' ')"
AVAIL_HUMAN="$(df -h --output=avail "$DEST" | tail -n1 | tr -d ' ')"
log "Free space at destination: ${AVAIL_HUMAN}"

# ---------------------------------------------------------------------------
# What we back up
# ---------------------------------------------------------------------------
# Always-included, high-value / irreplaceable paths.
INCLUDE_PATHS=(
  ".ssh"
  ".gnupg"
  "Nyxus-Core"
  "Projects"
  ".config"
  ".nyxus"
  ".local/bin"
  ".local/share/applications"
  ".local/state"
  ".bashrc" ".bash_profile" ".zshrc" ".zprofile" ".profile" ".xinitrc"
  ".gitconfig" ".gitignore_global"
  ".tmux.conf" ".tmux"
  "Documents" "Pictures" "Desktop" "Downloads"
  ".config/mozilla"
  "Scripts"
  "CommandVault"
)

# Regenerable / cache / junk — always excluded regardless of --include-bulk.
ALWAYS_EXCLUDE=(
  ".cache"
  "**/node_modules"
  "**/.venv"
  "**/venv"
  "**/target"
  "**/__pycache__"
  ".local/share/Trash"
  ".config/chromium/*/Cache" ".config/chromium/*/Code Cache" ".config/chromium/*/GPUCache"
  ".config/mozilla/firefox/*/cache2"
  ".mozilla/*/cache2"
  ".npm" ".cargo/registry" ".rustup" ".gradle" ".pub-cache" ".ufbt"
  ".gowskinet-flipper-stage"
  "Projects/jeTT/models" "Projects/jeTT/knowledge_base" "Projects/jeTT/intelligence"
  "Projects/archive"
)

# Large "bulk" dirs — skipped by default (already-covered / regenerable /
# not irreplaceable), included only with --include-bulk.
BULK_PATHS=(
  "Music"
  "VirtualBox VMs"
  "Backups"
  "blast-64gb-staging"
  "nyxus-build-recovery"
  "Attic"
  ".config/nyxus-safe-backup-*"
  ".config/nyxus-restore-backup-*"
  ".config/hypr.broken"
  "Models"
  "GowskiNet-Vault"
)

RSYNC_EXCLUDES=()
for e in "${ALWAYS_EXCLUDE[@]}"; do RSYNC_EXCLUDES+=(--exclude "$e"); done
if [[ "$INCLUDE_BULK" -eq 0 ]]; then
  for b in "${BULK_PATHS[@]}"; do RSYNC_EXCLUDES+=(--exclude "$b"); done
fi

RSYNC_OPTS=(-aH --partial --info=progress2 --stats)
[[ "$DRY_RUN" -eq 1 ]] && RSYNC_OPTS+=(--dry-run)

if [[ "$ASSUME_YES" -ne 1 && "$DRY_RUN" -ne 1 ]]; then
  echo
  warn "About to copy the following from $SRC_HOME into $DEST_ROOT/home/:"
  printf '  - %s\n' "${INCLUDE_PATHS[@]}"
  if [[ "$INCLUDE_BULK" -eq 1 ]]; then
    warn "Also including BULK dirs (this can be very large):"
    printf '  - %s\n' "${BULK_PATHS[@]}"
  else
    warn "Skipping BULK dirs by default (re-run with --include-bulk to add them):"
    printf '  - %s\n' "${BULK_PATHS[@]}"
  fi
  echo
  read -r -p "Proceed? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || { log "Aborted by user."; exit 0; }
fi

mkdir -p "$DEST_ROOT"/{home,pkglists,ssh-keys,gnupg,system-info}

# ---------------------------------------------------------------------------
# 1. rsync mirror of home-directory content
# ---------------------------------------------------------------------------
log "Mirroring home-directory paths (this can take a while for large trees)..."
for p in "${INCLUDE_PATHS[@]}"; do
  src="$SRC_HOME/$p"
  [[ -e "$src" ]] || continue
  destdir="$DEST_ROOT/home/$(dirname "$p")"
  mkdir -p "$destdir"
  rsync "${RSYNC_OPTS[@]}" "${RSYNC_EXCLUDES[@]}" "$src" "$destdir/" || warn "rsync reported issues for $p (see output above)"
done

if [[ "$INCLUDE_BULK" -eq 1 ]]; then
  log "Mirroring BULK paths..."
  for p in "${BULK_PATHS[@]}"; do
    for src in $SRC_HOME/$p; do
      [[ -e "$src" ]] || continue
      destdir="$DEST_ROOT/home"
      rsync "${RSYNC_OPTS[@]}" "${RSYNC_EXCLUDES[@]}" "$src" "$destdir/" || warn "rsync reported issues for $src"
    done
  done
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
  log "Dry run complete. Nothing was written except the empty directory skeleton."
  exit 0
fi

# ---------------------------------------------------------------------------
# 2. SSH / GPG keys — explicit copy with tight verification (belt & suspenders
#    on top of the rsync above, since these are the hardest to recover).
# ---------------------------------------------------------------------------
if [[ -d "$SRC_HOME/.ssh" ]]; then
  cp -a "$SRC_HOME/.ssh" "$DEST_ROOT/ssh-keys/"
  log "SSH dir copied ($(du -sh "$DEST_ROOT/ssh-keys" | cut -f1))"
fi
if [[ -d "$SRC_HOME/.gnupg" ]]; then
  cp -a "$SRC_HOME/.gnupg" "$DEST_ROOT/gnupg/"
  log "GnuPG dir copied ($(du -sh "$DEST_ROOT/gnupg" | cut -f1))"
fi

# ---------------------------------------------------------------------------
# 3. Package lists
# ---------------------------------------------------------------------------
log "Recording package lists..."
pacman -Qqe  > "$DEST_ROOT/pkglists/pkglist.txt"      2>/dev/null || true
pacman -Qqm  > "$DEST_ROOT/pkglists/aur-pkglist.txt"  2>/dev/null || true
pacman -Qq   > "$DEST_ROOT/pkglists/pkglist-all.txt"  2>/dev/null || true
pacman -Qqd  > "$DEST_ROOT/pkglists/pkglist-deps.txt" 2>/dev/null || true

# ---------------------------------------------------------------------------
# 4. System info snapshot (services, fstab, hostname, etc.)
# ---------------------------------------------------------------------------
log "Recording system info snapshot..."
{
  echo "# hostnamectl"; hostnamectl 2>/dev/null
  echo; echo "# lsblk -f"; lsblk -f 2>/dev/null
  echo; echo "# df -h"; df -h 2>/dev/null
} > "$DEST_ROOT/system-info/hardware.txt" 2>/dev/null || true

systemctl list-unit-files --state=enabled --no-pager > "$DEST_ROOT/system-info/enabled-services.txt" 2>/dev/null || true
[[ -f /etc/fstab ]] && cp /etc/fstab "$DEST_ROOT/system-info/fstab.txt" 2>/dev/null || true
[[ -f /etc/hostname ]] && cp /etc/hostname "$DEST_ROOT/system-info/hostname.txt" 2>/dev/null || true
crontab -l > "$DEST_ROOT/system-info/crontab-user.txt" 2>/dev/null || echo "(no user crontab)" > "$DEST_ROOT/system-info/crontab-user.txt"

# ---------------------------------------------------------------------------
# 5. Manifest
# ---------------------------------------------------------------------------
BACKUP_SIZE="$(du -sh "$DEST_ROOT" 2>/dev/null | cut -f1)"
cat > "$DEST_ROOT/MANIFEST.txt" <<EOF
NYXUS pre-reinstall backup
===========================
Created:      $(date -Iseconds)
Script:       nyxus-backup-for-reinstall.sh v${SCRIPT_VERSION}
Source host:  $(hostname) ($(hostnamectl --static 2>/dev/null || true))
Source home:  $SRC_HOME
Bulk dirs included: $( [[ "$INCLUDE_BULK" -eq 1 ]] && echo yes || echo no )
Total backup size (approx): ${BACKUP_SIZE}

Layout
------
home/            Mirror of the include-list below, rooted the same as \$HOME.
ssh-keys/.ssh/   Extra verified copy of ~/.ssh (keys + known_hosts).
gnupg/.gnupg/    Extra verified copy of ~/.gnupg (GPG keyring).
pkglists/        pacman package lists for restoring the exact package set.
system-info/     hostnamectl/lsblk/fstab/enabled-services/crontab snapshot.

Included from \$HOME
--------------------
$(printf '  %s\n' "${INCLUDE_PATHS[@]}")

Skipped by default (regenerable/cache — always excluded)
----------------------------------------------------------
$(printf '  %s\n' "${ALWAYS_EXCLUDE[@]}")

Bulk dirs ($( [[ "$INCLUDE_BULK" -eq 1 ]] && echo "INCLUDED this run" || echo "SKIPPED this run — rerun with --include-bulk to add" ))
----------------------------------------------------------
$(printf '  %s\n' "${BULK_PATHS[@]}")

Restore
-------
After the fresh NYXUS install, run:
  scripts/nyxus-restore-from-backup.sh $DEST_ROOT

See docs/REINSTALL_GUIDE.md for the full step-by-step process.

Manual attention needed (NOT fully captured by this script)
-------------------------------------------------------------
- Browser-saved passwords: Firefox logins.db / Chromium "Login Data" are
  encrypted with OS-level secrets (Firefox master password / freedesktop
  Secret Service, Chromium OS keyring). The files ARE copied, but they will
  only unlock correctly if the same keyring/password is set up again on the
  new install. Consider exporting bookmarks/passwords via the browser's own
  export feature as a fallback.
- 2FA/authenticator app data on your phone, and the two YubiKeys seen on this
  system (Yubico 4/5 OTP+U2F+CCID) — hardware tokens are not "backed up" by
  this script; make sure you still have them and know their PINs.
- Any accounts/services that only exist in the cloud (GitHub, etc.) are not
  touched by this script — Nyxus-Core's git remote is:
  https://github.com/sierengowskisierengowski-cpu/Nyxus-Core.git
  (263 files had uncommitted changes at backup time — see home/Nyxus-Core).
- GPG/SSH key passphrases are not stored anywhere — you must remember them.
EOF

log "Manifest written to $DEST_ROOT/MANIFEST.txt"

# ---------------------------------------------------------------------------
# 6. Verification — spot-check + size sanity
# ---------------------------------------------------------------------------
log "Verifying backup..."
FAIL=0
for p in ".ssh/id_rsa" "Nyxus-Core/README.md" ".config/hypr" "pkglists/pkglist.txt"; do
  target="$DEST_ROOT/home/$p"
  [[ "$p" == .ssh/* ]] && target="$DEST_ROOT/ssh-keys/$p"
  [[ "$p" == pkglists/* ]] && target="$DEST_ROOT/$p"
  if [[ -e "$target" ]]; then
    sz="$(du -sh "$target" 2>/dev/null | cut -f1)"
    log "OK: $p present (${sz})"
  else
    warn "MISSING: expected $target"
    FAIL=1
  fi
done

SRC_SIZE_KB=0
for p in "${INCLUDE_PATHS[@]}"; do
  [[ -e "$SRC_HOME/$p" ]] || continue
  SRC_SIZE_KB=$(( SRC_SIZE_KB + $(du -sk -L --exclude='.cache' "$SRC_HOME/$p" 2>/dev/null | awk '{s+=$1} END{print s+0}') ))
done
DEST_SIZE_KB="$(du -sk "$DEST_ROOT/home" 2>/dev/null | cut -f1)"
log "Source include-list size (approx): $(( SRC_SIZE_KB / 1024 )) MB"
log "Destination home/ size:            $(( DEST_SIZE_KB / 1024 )) MB"

if [[ "$FAIL" -eq 1 ]]; then
  err "One or more spot-checks failed — review the warnings above before wiping anything."
  exit 2
fi

log "Backup complete: $DEST_ROOT"
log "Total size: ${BACKUP_SIZE}"
