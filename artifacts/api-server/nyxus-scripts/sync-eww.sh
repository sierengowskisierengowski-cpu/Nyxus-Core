#!/usr/bin/env bash
# NYXUS · sync-eww.sh
# Post-`git pull` helper: copy the canonical EWW config from the repo
# into the live ~/.config/eww/ tree, then reload the daemon so the
# Control Center / Notification Center / bar pick up the changes
# without a logout.
#
# Usage (from anywhere on the MSI host):
#   ~/Nyxus-Core/artifacts/api-server/nyxus-scripts/sync-eww.sh
#
# Flags:
#   --dry-run     show what would change without copying
#   --no-reload   copy only; don't touch the running eww daemon
#   --target DIR  override destination (default: ~/.config/eww)

set -euo pipefail

src_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/eww" && pwd)"
dst_dir="${HOME}/.config/eww"
dry=0
reload=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)   dry=1 ;;
    --no-reload) reload=0 ;;
    --target)    shift; dst_dir="$1" ;;
    -h|--help)
      sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "sync-eww: unknown flag '$1'" >&2; exit 2 ;;
  esac
  shift
done

[[ -d "$src_dir" ]] || { echo "sync-eww: source missing: $src_dir" >&2; exit 3; }

echo "── NYXUS · sync-eww ──────────────────────────────────────────"
echo "  source : $src_dir"
echo "  target : $dst_dir"
echo "  mode   : $([[ $dry -eq 1 ]] && echo DRY-RUN || echo COPY)"

mkdir -p "$dst_dir"

# rsync if available — handles deletes, perms, and gives a clean diff
# preview. Plain cp -a fallback for minimal installs.
if command -v rsync >/dev/null 2>&1; then
  rsync_args=(-a --delete --itemize-changes --exclude='.git')
  [[ $dry -eq 1 ]] && rsync_args+=(--dry-run)
  rsync "${rsync_args[@]}" "${src_dir}/" "${dst_dir}/"
else
  echo "  (rsync not found — using cp -a; --dry-run not supported)"
  [[ $dry -eq 1 ]] && { echo "sync-eww: --dry-run requires rsync" >&2; exit 4; }
  cp -a "${src_dir}/." "${dst_dir}/"
fi

# Make sure helper scripts are executable on the target.
find "${dst_dir}/scripts" -maxdepth 1 -type f -name '*.sh' -exec chmod +x {} + 2>/dev/null || true

# eww 0.5: only one of eww.scss / eww.css — prefer precompiled css + .source
if [[ -f "${dst_dir}/eww.scss.source" ]]; then
  rm -f "${dst_dir}/eww.scss"
fi
if [[ $dry -eq 0 && -x "${dst_dir}/scripts/compile-eww-css.sh" ]]; then
  echo "── compiling eww.css from source ───────────────────────────────"
  (cd "${dst_dir}" && "${dst_dir}/scripts/compile-eww-css.sh") ||     echo "sync-eww: compile-eww-css failed (using shipped eww.css if present)" >&2
fi

if [[ $dry -eq 1 ]]; then
  echo "  (dry-run, no reload)"; exit 0
fi

if [[ $reload -eq 1 ]]; then
  if command -v nyxus-eww-launch-safe >/dev/null 2>&1; then
    echo "── relaunching eww via nyxus-eww-launch-safe ───────────────────"
    nyxus-eww-launch-safe >>"${HOME}/.cache/nyxus-eww/sync.log" 2>&1 || \
      echo "sync-eww: nyxus-eww-launch-safe failed — run manually" >&2
  elif command -v nyxus-eww-launch >/dev/null 2>&1; then
    echo "── relaunching eww via nyxus-eww-launch ────────────────────────"
    nyxus-eww-launch >>"${HOME}/.cache/nyxus-eww/sync.log" 2>&1 || true
  elif command -v eww >/dev/null 2>&1; then
    echo "sync-eww: nyxus-eww-launch not found — skipping reload (no bare eww reload)" >&2
  fi
fi

echo "── done ──────────────────────────────────────────────────────"
