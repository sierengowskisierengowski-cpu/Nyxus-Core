#!/usr/bin/env bash
# NYXUS bulletproof wallpaper setter — tries every backend in order
# until one works, no matter the install state. Idempotent — safe to
# re-run from any shell.
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
# Usage:
#   nyxus-set-wallpaper.sh                       # default cosmos-gold
#   nyxus-set-wallpaper.sh /abs/path/to/img.png
#   nyxus-set-wallpaper.sh cosmic-dust           # short name lookup
#
# After picking the image it: kills every existing wallpaper daemon,
# tries swww → swaybg → hyprpaper → feh → nitrogen, and reports
# which backend won. Always exits 0 if a backend ran successfully.

set -u
export LC_ALL=C.UTF-8

WALL_DIR="$HOME/.config/hypr/walls"
DEFAULT_NAME="cosmos-gold"

# ── resolve the target image ──────────────────────────────────────────
ARG="${1:-$DEFAULT_NAME}"
IMG=""

if [ -f "$ARG" ]; then
  IMG="$ARG"
elif [ -f "$WALL_DIR/nyxus-bg-${ARG}.png" ]; then
  IMG="$WALL_DIR/nyxus-bg-${ARG}.png"
elif [ -f "$WALL_DIR/${ARG}" ]; then
  IMG="$WALL_DIR/${ARG}"
else
  # Auto-bootstrap: copy from the repo if the user has it cloned in
  # the canonical location.
  for repo in \
      "$HOME/Nyxus-Core/artifacts/api-server/nyxus-scripts" \
      "$HOME/nyxus-core/artifacts/api-server/nyxus-scripts" \
      "$HOME/workspace/artifacts/api-server/nyxus-scripts" \
      "/var/lib/nyxus/scripts" ; do
    if [ -f "$repo/nyxus-bg-${ARG}.png" ]; then
      mkdir -p "$WALL_DIR"
      cp -f "$repo"/nyxus-bg-*.png "$WALL_DIR"/ 2>/dev/null || true
      IMG="$WALL_DIR/nyxus-bg-${ARG}.png"
      break
    fi
  done
fi

if [ -z "$IMG" ] || [ ! -f "$IMG" ]; then
  echo "[nyxus-wallpaper] could not locate image for '${ARG}'" >&2
  echo "[nyxus-wallpaper] looked in $WALL_DIR and the canonical repo paths" >&2
  echo "[nyxus-wallpaper] available wallpapers in $WALL_DIR:" >&2
  ls -1 "$WALL_DIR" 2>/dev/null | sed 's/^/    /' >&2
  exit 1
fi

echo "[nyxus-wallpaper] target: $IMG"

# ── kill every existing wallpaper daemon ──────────────────────────────
pkill -x swaybg     2>/dev/null || true
pkill -x mpvpaper   2>/dev/null || true
pkill -x hyprpaper  2>/dev/null || true
pkill -x swww-daemon 2>/dev/null || true
pkill -x feh        2>/dev/null || true
sleep 0.3

# ── try backends in priority order ────────────────────────────────────
try_swww() {
  command -v swww >/dev/null 2>&1 || return 1
  swww-daemon >/dev/null 2>&1 &
  sleep 0.5
  swww img "$IMG" --transition-type any --transition-duration 1.0 \
    >/dev/null 2>&1 || return 1
  echo "[nyxus-wallpaper] OK · backend = swww"
  return 0
}

try_swaybg() {
  command -v swaybg >/dev/null 2>&1 || return 1
  nohup swaybg -i "$IMG" -m fill >/dev/null 2>&1 &
  disown 2>/dev/null || true
  sleep 0.4
  pgrep -x swaybg >/dev/null 2>&1 || return 1
  echo "[nyxus-wallpaper] OK · backend = swaybg"
  return 0
}

try_hyprpaper() {
  command -v hyprpaper >/dev/null 2>&1 || return 1
  local cfg="$HOME/.config/hypr/hyprpaper.conf"
  cat > "$cfg" <<EOF
preload = $IMG
wallpaper = ,$IMG
splash = false
EOF
  nohup hyprpaper >/dev/null 2>&1 &
  disown 2>/dev/null || true
  sleep 0.4
  pgrep -x hyprpaper >/dev/null 2>&1 || return 1
  echo "[nyxus-wallpaper] OK · backend = hyprpaper"
  return 0
}

try_feh() {
  command -v feh >/dev/null 2>&1 || return 1
  feh --bg-fill "$IMG" >/dev/null 2>&1 || return 1
  echo "[nyxus-wallpaper] OK · backend = feh"
  return 0
}

if try_swww || try_swaybg || try_hyprpaper || try_feh; then
  # Save the choice so a re-launch (or first-boot script) can restore it.
  mkdir -p "$HOME/.config/nyxus"
  printf 'WALLPAPER=%s\n' "$IMG" > "$HOME/.config/nyxus/wallpaper.conf"
  exit 0
fi

echo "[nyxus-wallpaper] no usable backend found." >&2
echo "[nyxus-wallpaper] install one of:  pacman -S swww swaybg hyprpaper" >&2
exit 1
