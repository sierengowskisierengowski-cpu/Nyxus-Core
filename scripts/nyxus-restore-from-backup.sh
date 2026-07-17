#!/usr/bin/env bash
# nyxus-restore-from-backup.sh
#
# Companion to nyxus-backup-for-reinstall.sh. Run this AFTER the fresh NYXUS
# install, once you're logged in as your normal user on the new system.
#
# It restores home-directory content, SSH/GPG keys (with correct
# permissions), reinstalls the recorded package set, and re-checks out
# Nyxus-Core — WITHOUT blindly overwriting anything unexpected. Default mode
# is a dry run; you must pass --apply to actually write anything.
#
# Usage:
#   ./nyxus-restore-from-backup.sh /path/to/nyxus-backup-TIMESTAMP [options]
#
# Options:
#   --apply           Actually perform the restore (default is dry-run/preview).
#   --skip-packages   Don't reinstall pacman/AUR packages.
#   --skip-home       Don't restore home-directory files (keys/pkgs only).
#   --yes             Skip confirmation prompts (still respects --apply).

set -euo pipefail

BACKUP_DIR=""
APPLY=0
SKIP_PACKAGES=0
SKIP_HOME=0
ASSUME_YES=0

log()  { printf '\033[1;36m[restore]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
err()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; }

usage() { sed -n '2,20p' "$0"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --apply) APPLY=1; shift ;;
    --skip-packages) SKIP_PACKAGES=1; shift ;;
    --skip-home) SKIP_HOME=1; shift ;;
    --yes|-y) ASSUME_YES=1; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) err "Unknown option: $1"; usage; exit 1 ;;
    *) BACKUP_DIR="$1"; shift ;;
  esac
done

if [[ -z "$BACKUP_DIR" || ! -d "$BACKUP_DIR" ]]; then
  err "Give me the backup directory (the nyxus-backup-TIMESTAMP folder, containing MANIFEST.txt)."
  usage
  exit 1
fi
if [[ ! -f "$BACKUP_DIR/MANIFEST.txt" ]]; then
  err "'$BACKUP_DIR' doesn't look like a nyxus backup (no MANIFEST.txt found)."
  exit 1
fi
if [[ "$(id -u)" -eq 0 ]]; then
  err "Run this as your normal user, not root. It will use sudo internally where needed (package install)."
  exit 1
fi

if [[ "$APPLY" -eq 0 ]]; then
  warn "DRY RUN MODE (default). No files will be written, no packages installed."
  warn "Re-run with --apply once you've reviewed the plan below."
fi

log "Backup source: $BACKUP_DIR"
log "Manifest:"
sed 's/^/  /' "$BACKUP_DIR/MANIFEST.txt" | head -n 20
echo

if [[ "$ASSUME_YES" -ne 1 ]]; then
  read -r -p "Continue with restore plan on THIS machine? [y/N] " ans
  [[ "$ans" =~ ^[Yy]$ ]] || { log "Aborted by user."; exit 0; }
fi

run() {
  if [[ "$APPLY" -eq 1 ]]; then
    "$@"
  else
    echo "  (dry-run) $*"
  fi
}

# ---------------------------------------------------------------------------
# 1. Package set
# ---------------------------------------------------------------------------
if [[ "$SKIP_PACKAGES" -eq 0 ]]; then
  log "=== Package restore ==="
  PKGLIST="$BACKUP_DIR/pkglists/pkglist.txt"
  AURLIST="$BACKUP_DIR/pkglists/aur-pkglist.txt"

  if [[ -s "$PKGLIST" ]]; then
    MISSING_NATIVE="$(comm -23 <(sort -u "$PKGLIST") <(pacman -Qq | sort -u) || true)"
    COUNT="$(echo "$MISSING_NATIVE" | grep -c . || true)"
    log "Repo packages to (re)install: $COUNT"
    if [[ "$COUNT" -gt 0 ]]; then
      if [[ "$APPLY" -eq 1 ]]; then
        sudo pacman -S --needed - < "$PKGLIST"
      else
        echo "  (dry-run) sudo pacman -S --needed - < $PKGLIST"
      fi
    fi
  else
    warn "No pkglist.txt found in backup — skipping repo package restore."
  fi

  if [[ -s "$AURLIST" ]]; then
    log "AUR packages recorded: $(wc -l < "$AURLIST")"
    warn "AUR packages need an AUR helper (yay/paru). This script does NOT install"
    warn "an AUR helper automatically. Once you have one, run:"
    warn "  yay -S --needed - < $AURLIST"
    warn "(or your preferred AUR helper). Review the list first — some AUR"
    warn "packages may be abandoned/renamed since this backup was made."
  fi
else
  log "Skipping package restore (--skip-packages)."
fi

# ---------------------------------------------------------------------------
# 2. SSH keys (correct permissions are critical — ssh silently refuses keys
#    with loose permissions)
# ---------------------------------------------------------------------------
log "=== SSH keys ==="
SRC_SSH="$BACKUP_DIR/ssh-keys/.ssh"
if [[ -d "$SRC_SSH" ]]; then
  if [[ -d "$HOME/.ssh" && -n "$(ls -A "$HOME/.ssh" 2>/dev/null)" ]]; then
    warn "$HOME/.ssh already has content on this fresh system — will NOT overwrite."
    warn "Backup copy is at: $SRC_SSH — merge manually if needed."
  else
    run mkdir -p "$HOME/.ssh"
    run cp -a "$SRC_SSH/." "$HOME/.ssh/"
    run chmod 700 "$HOME/.ssh"
    run bash -c "chmod 600 '$HOME'/.ssh/id_* 2>/dev/null || true"
    run bash -c "chmod 644 '$HOME'/.ssh/*.pub 2>/dev/null || true"
    log "SSH keys restored with chmod 700 (~/.ssh) / 600 (private keys) / 644 (*.pub)."
  fi
else
  warn "No .ssh directory found in backup."
fi

# ---------------------------------------------------------------------------
# 3. GnuPG
# ---------------------------------------------------------------------------
log "=== GnuPG ==="
SRC_GPG="$BACKUP_DIR/gnupg/.gnupg"
if [[ -d "$SRC_GPG" ]]; then
  if [[ -d "$HOME/.gnupg" && -n "$(ls -A "$HOME/.gnupg" 2>/dev/null)" ]]; then
    warn "$HOME/.gnupg already has content — will NOT overwrite. Backup copy: $SRC_GPG"
  else
    run mkdir -p "$HOME/.gnupg"
    run cp -a "$SRC_GPG/." "$HOME/.gnupg/"
    run chmod 700 "$HOME/.gnupg"
    run bash -c "find '$HOME/.gnupg' -type f -exec chmod 600 {} +"
    run bash -c "find '$HOME/.gnupg' -type d -exec chmod 700 {} +"
    log "GnuPG keyring restored. You'll need your GPG passphrase to use the keys."
  fi
else
  warn "No .gnupg directory found in backup."
fi

# ---------------------------------------------------------------------------
# 4. Home-directory content (careful, additive-only merge via rsync -a
#    without --delete, and skip files that already exist and differ unless
#    --apply + explicit confirmation)
# ---------------------------------------------------------------------------
if [[ "$SKIP_HOME" -eq 0 ]]; then
  log "=== Home-directory restore ==="
  if [[ -d "$BACKUP_DIR/home" ]]; then
    log "This will rsync $BACKUP_DIR/home/* into \$HOME, WITHOUT deleting anything"
    log "already present on this fresh system, and without clobbering files that"
    log "already exist (rsync --ignore-existing) so you don't lose default configs"
    log "you haven't touched yet. Re-run manually with different rsync flags if"
    log "you explicitly want backup versions to win."
    if [[ "$APPLY" -eq 1 ]]; then
      rsync -aH --info=progress2 --ignore-existing "$BACKUP_DIR/home/" "$HOME/"
    else
      echo "  (dry-run) rsync -aH --ignore-existing $BACKUP_DIR/home/ $HOME/"
      rsync -aHn --info=progress2 --ignore-existing "$BACKUP_DIR/home/" "$HOME/" | tail -n 30
    fi
  else
    warn "No home/ directory found in backup."
  fi
else
  log "Skipping home-directory restore (--skip-home)."
fi

# ---------------------------------------------------------------------------
# 5. Nyxus-Core sanity check
# ---------------------------------------------------------------------------
log "=== Nyxus-Core check ==="
if [[ -d "$HOME/Nyxus-Core/.git" ]]; then
  log "Nyxus-Core already present at $HOME/Nyxus-Core (restored above or freshly cloned)."
  (cd "$HOME/Nyxus-Core" && git status --short | head -n 10)
else
  warn "$HOME/Nyxus-Core not present yet."
  warn "Clone it fresh with:"
  warn "  git clone https://github.com/sierengowskisierengowski-cpu/Nyxus-Core $HOME/Nyxus-Core"
  warn "then check $BACKUP_DIR/home/Nyxus-Core for any UNCOMMITTED changes to reapply"
  warn "(there were uncommitted changes to 263 files at backup time)."
fi

# ---------------------------------------------------------------------------
# 6. Reminders
# ---------------------------------------------------------------------------
cat <<'EOF'

=== Manual follow-ups (not automated) ===
  - Log out/in (or reboot) so shell rc files (.bashrc/.zshrc) take effect.
  - Re-enable any systemd --user services you rely on (see
    <backup>/system-info/enabled-services.txt for the old list).
  - Firefox/Chromium profiles were copied byte-for-byte; if saved logins don't
    unlock, you may need to re-enter your browser master password / OS
    keyring password once.
  - AUR packages: install an AUR helper (yay/paru) first, then feed it
    <backup>/pkglists/aur-pkglist.txt as shown above.
  - Re-pair/re-register hardware tokens (YubiKeys) with any services that
    need it if the new install changed anything security-key related.
  - Run scripts/nyxus-verify-build.sh once packages+configs are back in place.
EOF

log "Restore pass finished. APPLY=$APPLY"
