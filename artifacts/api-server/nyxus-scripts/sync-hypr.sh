#!/usr/bin/env bash
# NYXUS · sync-hypr.sh
# Post-`git pull` helper: copy the canonical Hyprland configs from the
# repo into the live ~/.config/hypr/ tree, then `hyprctl reload` so the
# new keybinds, window rules, blur tuning, etc. apply without a logout.
#
# Companion to sync-eww.sh — together they cover the whole NYXUS UI
# surface that lives outside /usr/local/bin.
#
# Files copied (canonical → installed):
#   hyprland.conf              → ~/.config/hypr/hyprland.conf
#   hyprlock.conf              → ~/.config/hypr/hyprlock.conf
#   hypridle.conf              → ~/.config/hypr/hypridle.conf
#   nyxus-hyprland-*.conf      → ~/.config/hypr/conf.d/
#
# Usage (from anywhere on the MSI host):
#   ~/Nyxus-Core/artifacts/api-server/nyxus-scripts/sync-hypr.sh
#
# Flags:
#   --dry-run     show what would change without copying
#   --no-reload   copy only; don't `hyprctl reload`
#   --target DIR  override destination (default: ~/.config/hypr)

set -euo pipefail

src_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
dst_dir="${HOME}/.config/hypr"
dry=0
reload=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)   dry=1 ;;
    --no-reload) reload=0 ;;
    --target)    shift; dst_dir="$1" ;;
    -h|--help)
      sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "sync-hypr: unknown flag '$1'" >&2; exit 2 ;;
  esac
  shift
done

[[ -d "$src_dir" ]] || { echo "sync-hypr: source missing: $src_dir" >&2; exit 3; }

# Required top-level files. If any is missing in the source we abort
# rather than silently shipping a half-config.
required=(hyprland.conf hyprlock.conf hypridle.conf)
for f in "${required[@]}"; do
  [[ -f "$src_dir/$f" ]] || { echo "sync-hypr: missing canonical $f in $src_dir" >&2; exit 4; }
done

# Confd shards (sourced by hyprland.conf). At least one must exist.
shopt -s nullglob
shards=( "$src_dir"/nyxus-hyprland-*.conf )
shopt -u nullglob
[[ ${#shards[@]} -gt 0 ]] || {
  echo "sync-hypr: no nyxus-hyprland-*.conf shards found in $src_dir" >&2
  exit 5
}

echo "── NYXUS · sync-hypr ─────────────────────────────────────────"
echo "  source : $src_dir"
echo "  target : $dst_dir"
echo "  shards : ${#shards[@]} (→ $dst_dir/conf.d)"
echo "  mode   : $([[ $dry -eq 1 ]] && echo DRY-RUN || echo COPY)"

if [[ $dry -eq 1 ]]; then
  echo "  would copy:"
  for f in "${required[@]}"; do echo "    $f"; done
  for f in "${shards[@]}"; do echo "    conf.d/$(basename "$f")"; done
  echo "── dry-run, no changes ───────────────────────────────────────"
  exit 0
fi

mkdir -p "$dst_dir" "$dst_dir/conf.d"

# Top-level files
for f in "${required[@]}"; do
  cp -f "$src_dir/$f" "$dst_dir/$f"
  echo "  ✓ $f"
done

# Shards into conf.d/
for f in "${shards[@]}"; do
  cp -f "$f" "$dst_dir/conf.d/$(basename "$f")"
  echo "  ✓ conf.d/$(basename "$f")"
done

if [[ $reload -eq 1 ]]; then
  if command -v hyprctl >/dev/null 2>&1; then
    echo "── reloading hyprland ────────────────────────────────────────"
    if hyprctl reload >/dev/null 2>&1; then
      echo "  ✓ hyprctl reload"
    else
      echo "  ! hyprctl reload failed — try logging out and back in" >&2
    fi
    # Surface any config errors so the user sees them immediately
    # instead of via the on-screen Hyprland overlay.
    if errs="$(hyprctl configerrors 2>/dev/null)" && [[ -n "$errs" && "$errs" != "no errors" ]]; then
      echo "── hyprctl configerrors ──────────────────────────────────────"
      echo "$errs"
    fi
  else
    echo "  (hyprctl not on PATH — skipping reload)"
  fi
fi

echo "── done ──────────────────────────────────────────────────────"
