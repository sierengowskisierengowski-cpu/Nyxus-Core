#!/usr/bin/env bash
# NYXUS Animated Wallpaper — mpvpaper driver with rotation
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
#
# Loops video files as the desktop background using mpvpaper. When a
# directory is supplied (or the default WALL_DIR contains multiple
# clips), each clip plays for $INTERVAL seconds before rotating to
# the next. Falls back to swaybg + a still PNG if mpvpaper is absent.
#
# Install once:  pacman -S mpvpaper
# Drop clips:    cp *.mp4 ~/.config/hypr/walls/animated/
# Autostart:     add  exec-once = ~/.local/bin/nyxus-animated-bg.sh
#                to ~/.config/hypr/hyprland.lua
#
# Usage:
#   nyxus-animated-bg.sh                       # rotate all clips in WALL_DIR
#   nyxus-animated-bg.sh /path/to.mp4          # loop a single clip forever
#   nyxus-animated-bg.sh /path/to/clipdir      # rotate clips in that dir
#
# Tunables (env vars):
#   NYXUS_BG_INTERVAL  seconds per clip in rotation mode (default 180)
#   NYXUS_BG_MONITOR   mpvpaper -f selector, "*" for all (default "*")
#   NYXUS_BG_DIR       override default rotation dir

set -u

WALL_DIR="${NYXUS_BG_DIR:-$HOME/.config/hypr/walls/animated}"
INTERVAL="${NYXUS_BG_INTERVAL:-180}"
MONITOR="${NYXUS_BG_MONITOR:-*}"
MPV_OPTS="no-audio loop hwdec=auto vo=gpu --no-osc --no-input-default-bindings --really-quiet"

# ── resolve target ────────────────────────────────────────────────────
TARGET="${1:-$WALL_DIR}"
declare -a CLIPS=()
SINGLE_FILE=""

if [ -d "$TARGET" ]; then
  shopt -s nullglob
  for f in "$TARGET"/*.mp4 "$TARGET"/*.webm "$TARGET"/*.mkv; do
    CLIPS+=("$f")
  done
  shopt -u nullglob
elif [ -f "$TARGET" ]; then
  SINGLE_FILE="$TARGET"
fi

# Legacy fallback: if WALL_DIR is empty, look for the canonical
# nyxus-bg-darkmirror*.mp4 pair in ~/.config/hypr/walls/.
if [ -z "$SINGLE_FILE" ] && [ "${#CLIPS[@]}" -eq 0 ]; then
  shopt -s nullglob
  for f in "$HOME/.config/hypr/walls"/nyxus-bg-darkmirror*.mp4; do
    CLIPS+=("$f")
  done
  shopt -u nullglob
fi

# ── kill previous wallpaper daemons ───────────────────────────────────
pkill -x mpvpaper 2>/dev/null
pkill -x swaybg   2>/dev/null
# also kill any prior instance of THIS rotator (so re-running replaces).
pgrep -f "nyxus-animated-bg.sh" | grep -v $$ | xargs -r kill 2>/dev/null
sleep 0.3

# ── single clip mode ──────────────────────────────────────────────────
if [ -n "$SINGLE_FILE" ]; then
  if command -v mpvpaper >/dev/null 2>&1; then
    exec mpvpaper -o "$MPV_OPTS" -f "$MONITOR" "$SINGLE_FILE"
  fi
  STILL="${SINGLE_FILE%.*}.png"
  if command -v swaybg >/dev/null 2>&1 && [ -f "$STILL" ]; then
    exec swaybg -i "$STILL" -m fill
  fi
  echo "[nyxus-animated-bg] no usable backend (need mpvpaper or swaybg)" >&2
  exit 1
fi

# ── no clips found anywhere → static fallback ─────────────────────────
if [ "${#CLIPS[@]}" -eq 0 ]; then
  STILL="$HOME/.config/hypr/walls/nyxus-bg-darkmirror.png"
  if command -v swaybg >/dev/null 2>&1 && [ -f "$STILL" ]; then
    exec swaybg -i "$STILL" -m fill
  fi
  echo "[nyxus-animated-bg] no clips in $WALL_DIR and no fallback still" >&2
  exit 1
fi

# ── rotation mode ─────────────────────────────────────────────────────
if ! command -v mpvpaper >/dev/null 2>&1; then
  # mpvpaper missing → static rotation via swaybg over the matching PNGs.
  if ! command -v swaybg >/dev/null 2>&1; then
    echo "[nyxus-animated-bg] need mpvpaper or swaybg installed" >&2
    exit 1
  fi
  IDX=0
  while true; do
    CLIP="${CLIPS[$IDX]}"
    STILL="${CLIP%.*}.png"
    if [ -f "$STILL" ]; then
      pkill -x swaybg 2>/dev/null
      swaybg -i "$STILL" -m fill &
    fi
    IDX=$(( (IDX + 1) % ${#CLIPS[@]} ))
    sleep "$INTERVAL"
  done
fi

# Single clip in the dir? Just loop it forever, no rotation churn.
if [ "${#CLIPS[@]}" -eq 1 ]; then
  exec mpvpaper -o "$MPV_OPTS" -f "$MONITOR" "${CLIPS[0]}"
fi

# Multi-clip rotation: relaunch mpvpaper every $INTERVAL seconds with
# the next clip in the list.
trap 'pkill -x mpvpaper 2>/dev/null; exit 0' INT TERM
IDX=0
while true; do
  CLIP="${CLIPS[$IDX]}"
  pkill -x mpvpaper 2>/dev/null
  sleep 0.2
  mpvpaper -o "$MPV_OPTS" -f "$MONITOR" "$CLIP" &
  IDX=$(( (IDX + 1) % ${#CLIPS[@]} ))
  sleep "$INTERVAL"
done
