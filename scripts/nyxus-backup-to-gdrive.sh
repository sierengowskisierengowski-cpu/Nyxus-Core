#!/usr/bin/env bash
# nyxus-backup-to-gdrive.sh
#
# Full-scope ($HOME, everything except true junk/cache) backup to the
# pre-configured rclone "gdrive:" remote. Designed to run for a long time
# (many hours) unattended via nohup/systemd-run, and to be safely resumable:
# re-running this script re-invokes `rclone copy`, which only (re)transfers
# files that are missing or differ by size/modtime on the remote, so an
# interrupted run can just be restarted with the same TS to continue.
#
# Usage:
#   ./nyxus-backup-to-gdrive.sh [TIMESTAMP]
#
# If TIMESTAMP is omitted, a new one is generated (fresh backup folder).
# Pass an existing TIMESTAMP (as printed by a previous run, e.g.
# 20260716-031500) to resume/continue that same backup folder on gdrive.
#
# Progress/log: see $LOG_FILE printed at startup. Check with:
#   tail -f <LOG_FILE>
#   rclone size gdrive:nyxus-backup-<TIMESTAMP>   # bytes copied so far

set -uo pipefail

SRC_HOME="${HOME}"
REMOTE="gdrive"
TS="${1:-$(date +%Y%m%d-%H%M%S)}"
REMOTE_ROOT="${REMOTE}:nyxus-backup-${TS}"
LOG_DIR="${HOME}/.nyxus/backup-logs"
mkdir -p "$LOG_DIR"
LOG_FILE="${LOG_DIR}/gdrive-backup-${TS}.log"
STATUS_FILE="${LOG_DIR}/gdrive-backup-${TS}.status"

echo "backup_ts=${TS}"        > "$STATUS_FILE"
echo "remote_root=${REMOTE_ROOT}" >> "$STATUS_FILE"
echo "log_file=${LOG_FILE}"   >> "$STATUS_FILE"
echo "started_at=$(date -Iseconds)" >> "$STATUS_FILE"
echo "state=running"          >> "$STATUS_FILE"

exec >>"$LOG_FILE" 2>&1
echo "=== nyxus-backup-to-gdrive.sh starting $(date -Iseconds) ==="
echo "Remote root: $REMOTE_ROOT"
echo "Source home: $SRC_HOME"

if [[ "$(id -u)" -eq 0 ]]; then
  echo "ERROR: run as normal user, not root."
  echo "state=failed" >> "$STATUS_FILE"
  exit 1
fi

if ! command -v rclone >/dev/null; then
  echo "ERROR: rclone not installed."
  echo "state=failed" >> "$STATUS_FILE"
  exit 1
fi

if ! rclone listremotes | grep -qx "${REMOTE}:"; then
  echo "ERROR: rclone remote '${REMOTE}:' not configured. Run 'rclone config' first."
  echo "state=failed" >> "$STATUS_FILE"
  exit 1
fi

echo "--- rclone about ${REMOTE}: ---"
rclone about "${REMOTE}:" || echo "(rclone about failed, continuing anyway)"

# True junk/cache/regenerable-build-artifact excludes only — everything else
# in $HOME is included per the full-scope backup decision.
EXCLUDES=(
  --exclude ".cache/**"
  --exclude "**/node_modules/**"
  --exclude "**/.venv/**"
  --exclude "**/venv/**"
  --exclude "**/target/**"
  --exclude "**/__pycache__/**"
  --exclude ".local/share/Trash/**"
  --exclude ".config/chromium/*/Cache/**"
  --exclude ".config/chromium/*/Code Cache/**"
  --exclude ".config/chromium/*/GPUCache/**"
  --exclude ".config/mozilla/firefox/*/cache2/**"
  --exclude ".npm/**"
  --exclude ".cargo/registry/**"
  --exclude ".rustup/**"
  --exclude ".gradle/**"
  --exclude ".pub-cache/**"
  --exclude ".ufbt/**"
  --exclude ".gowskinet-flipper-stage/**"
  --exclude ".nyxus/backup-logs/**"
)

RCLONE_OPTS=(
  --transfers 8
  --checkers 16
  --stats 60s
  --stats-log-level NOTICE
  --retries 5
  --low-level-retries 10
  --contimeout 30s
  --timeout 5m
)

echo "--- Step 1/5: main home mirror -> ${REMOTE_ROOT}/home/ ---"
rclone copy "$SRC_HOME/" "${REMOTE_ROOT}/home/" "${EXCLUDES[@]}" "${RCLONE_OPTS[@]}"
HOME_RC=$?
echo "home mirror rclone exit code: $HOME_RC"

echo "--- Step 2/5: SSH keys -> ${REMOTE_ROOT}/ssh-keys/.ssh/ ---"
if [[ -d "$SRC_HOME/.ssh" ]]; then
  rclone copy "$SRC_HOME/.ssh/" "${REMOTE_ROOT}/ssh-keys/.ssh/" "${RCLONE_OPTS[@]}"
fi

echo "--- Step 3/5: GnuPG -> ${REMOTE_ROOT}/gnupg/.gnupg/ ---"
if [[ -d "$SRC_HOME/.gnupg" ]]; then
  rclone copy "$SRC_HOME/.gnupg/" "${REMOTE_ROOT}/gnupg/.gnupg/" "${RCLONE_OPTS[@]}"
fi

echo "--- Step 4/5: package lists + system info ---"
STAGE="$(mktemp -d)"
mkdir -p "$STAGE/pkglists" "$STAGE/system-info"
pacman -Qqe  > "$STAGE/pkglists/pkglist.txt"      2>/dev/null || true
pacman -Qqm  > "$STAGE/pkglists/aur-pkglist.txt"  2>/dev/null || true
pacman -Qq   > "$STAGE/pkglists/pkglist-all.txt"  2>/dev/null || true
pacman -Qqd  > "$STAGE/pkglists/pkglist-deps.txt" 2>/dev/null || true
{
  echo "# hostnamectl"; hostnamectl 2>/dev/null
  echo; echo "# lsblk -f"; lsblk -f 2>/dev/null
  echo; echo "# df -h"; df -h 2>/dev/null
} > "$STAGE/system-info/hardware.txt" 2>/dev/null || true
systemctl list-unit-files --state=enabled --no-pager > "$STAGE/system-info/enabled-services.txt" 2>/dev/null || true
[[ -f /etc/fstab ]] && cp /etc/fstab "$STAGE/system-info/fstab.txt" 2>/dev/null || true
[[ -f /etc/hostname ]] && cp /etc/hostname "$STAGE/system-info/hostname.txt" 2>/dev/null || true
crontab -l > "$STAGE/system-info/crontab-user.txt" 2>/dev/null || echo "(no user crontab)" > "$STAGE/system-info/crontab-user.txt"

rclone copy "$STAGE/" "${REMOTE_ROOT}/" "${RCLONE_OPTS[@]}"
rm -rf "$STAGE"

echo "--- Step 5/5: manifest + verification ---"
TOTAL_SIZE_LINE="$(rclone size "${REMOTE_ROOT}" 2>/dev/null || true)"
echo "$TOTAL_SIZE_LINE"

STAGE2="$(mktemp -d)"
cat > "$STAGE2/MANIFEST.txt" <<EOF
NYXUS pre-reinstall backup (FULL SCOPE) -> Google Drive
=========================================================
Created:      $(date -Iseconds)
Script:       nyxus-backup-to-gdrive.sh
Source host:  $(hostname) ($(hostnamectl --static 2>/dev/null || true))
Source home:  $SRC_HOME
Destination:  ${REMOTE_ROOT} (rclone remote 'gdrive:')
Scope:        FULL — everything under \$HOME except true junk/cache
              (node_modules, .venv, target, __pycache__, browser Cache
              subdirs, .cache, package-manager caches). Music,
              VirtualBox VMs, the existing ~/Backups folder, and all other
              previously-optional "bulk" dirs ARE included this run.

$TOTAL_SIZE_LINE

Layout
------
home/            Full mirror of \$HOME (minus junk/cache excludes above).
ssh-keys/.ssh/   Extra verified copy of ~/.ssh (keys + known_hosts).
gnupg/.gnupg/    Extra verified copy of ~/.gnupg (GPG keyring).
pkglists/        pacman package lists for restoring the exact package set.
system-info/     hostnamectl/lsblk/fstab/enabled-services/crontab snapshot.

Restore
-------
Use scripts/nyxus-restore-from-backup.sh, but point it at a LOCAL copy of
this backup (rclone sync/copy "${REMOTE_ROOT}" /some/local/path first), since
the restore script expects a local directory, not an rclone remote path.
See docs/REINSTALL_GUIDE.md.

Manual attention needed (NOT fully captured by this script)
-------------------------------------------------------------
- Browser-saved passwords (Firefox logins.db/key4.db, Chromium Login Data)
  are copied byte-for-byte but tied to OS keyring / master password.
- 2FA/authenticator apps on your phone, and any hardware security keys
  (YubiKeys) are not backed up by this script.
- GPG/SSH key passphrases are not stored anywhere.
- Nyxus-Core git remote: https://github.com/sierengowskisierengowski-cpu/Nyxus-Core.git
  (had uncommitted local changes at backup time — see home/Nyxus-Core).
EOF
rclone copyto "$STAGE2/MANIFEST.txt" "${REMOTE_ROOT}/MANIFEST.txt"
rm -rf "$STAGE2"

echo "--- Spot-check a few known files on the remote ---"
FAIL=0
for p in "home/.ssh/id_rsa" "home/Nyxus-Core/README.md" "pkglists/pkglist.txt" "ssh-keys/.ssh/id_rsa"; do
  if rclone lsf "${REMOTE_ROOT}/$(dirname "$p")" 2>/dev/null | grep -qx "$(basename "$p")"; then
    echo "OK: $p present"
  else
    echo "WARN: $p not found on remote"
    FAIL=1
  fi
done

echo "=== nyxus-backup-to-gdrive.sh finished $(date -Iseconds), spot-check FAIL=$FAIL ==="
if [[ "$HOME_RC" -eq 0 && "$FAIL" -eq 0 ]]; then
  echo "state=completed" >> "$STATUS_FILE"
else
  echo "state=completed_with_warnings (home_rc=$HOME_RC fail=$FAIL)" >> "$STATUS_FILE"
fi
echo "finished_at=$(date -Iseconds)" >> "$STATUS_FILE"