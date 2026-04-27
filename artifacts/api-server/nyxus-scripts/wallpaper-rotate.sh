#!/usr/bin/env bash
# NYXUS Wallpaper Auto-Rotate
# Cycles through all 16 NYXUS wallpapers every 5 minutes
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED

BASE_URL="https://nyxus-core.replit.app/api/download/nyxus"
WALL_DIR="$HOME/.config/hypr/walls"
INTERVAL=300  # seconds between wallpaper changes (5 min)

mkdir -p "$WALL_DIR"

# Download all wallpapers if not already present
for i in $(seq -w 1 16); do
  FILE="$WALL_DIR/nyxus-wall-${i}.png"
  if [ ! -f "$FILE" ]; then
    echo "[NYXUS] Downloading wallpaper ${i}/16..."
    curl -fsSL "$BASE_URL/nyxus-wall-${i}.png" -o "$FILE"
  fi
done

WALLS=("$WALL_DIR"/nyxus-wall-*.png)
TOTAL=${#WALLS[@]}

if [ "$TOTAL" -eq 0 ]; then
  echo "[NYXUS] No wallpapers found in $WALL_DIR"
  exit 1
fi

echo "[NYXUS] Starting wallpaper rotation — $TOTAL wallpapers, cycling every ${INTERVAL}s"

IDX=0
while true; do
  WALL="${WALLS[$IDX]}"
  echo "[NYXUS] Setting wallpaper: $(basename "$WALL")"
  pkill swaybg 2>/dev/null
  swaybg -i "$WALL" -m fill &
  IDX=$(( (IDX + 1) % TOTAL ))
  sleep "$INTERVAL"
done
