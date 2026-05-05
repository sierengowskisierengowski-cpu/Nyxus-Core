#!/usr/bin/env bash
# nyxus-set-frost-wallpaper.sh — one-shot Seattle Frost wallpaper installer.
#
# Downloads the SIERENGOWSKI frosted-glass wallpaper and applies it via
# whichever wallpaper daemon is currently running (swaybg / hyprpaper /
# swww). Safe to re-run; will replace the existing frost wallpaper.
#
# Usage:
#   curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus-set-frost-wallpaper.sh | bash
#
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
set -euo pipefail

VERSION="2026.05.05-r2"
PROD="https://nyxus-core.replit.app/api/download/nyxus"
WP_NAME="nyxus-frost-sierengowski.png"
WP_DIR="${HOME}/Pictures/nyxus"
WP_DST="${WP_DIR}/${WP_NAME}"
MODE="${1:-fit}"             # fit | fill | center | tile  (default fit — shows whole SIERENGOWSKI centered)
LETTERBOX_COLOR="#f5f3ef"    # cream — matches wallpaper's own background, seamless margins

c_cyan="$(printf '\033[1;36m')"; c_grn="$(printf '\033[1;32m')"
c_yel="$(printf '\033[1;33m')"; c_red="$(printf '\033[1;31m')"
c_rst="$(printf '\033[0m')"
say()  { printf '%s▌%s %s\n' "$c_cyan" "$c_rst" "$*"; }
ok()   { printf '  %s✓%s  %s\n' "$c_grn" "$c_rst" "$*"; }
warn() { printf '  %s!%s  %s\n' "$c_yel" "$c_rst" "$*"; }
fail() { printf '  %s✗%s  %s\n' "$c_red" "$c_rst" "$*"; }

say "nyxus-set-frost-wallpaper ${VERSION}  (mode: ${MODE})"

# 1. Download the wallpaper
mkdir -p "$WP_DIR"
if curl -fsSL --max-time 30 "${PROD}/${WP_NAME}" -o "${WP_DST}.new"; then
  mv "${WP_DST}.new" "$WP_DST"
  ok "downloaded ${WP_NAME} → ${WP_DST}  ($(stat -c%s "$WP_DST" 2>/dev/null || echo '?') bytes)"
else
  fail "failed to download ${WP_NAME} from ${PROD}"
  exit 1
fi

# 2. Detect running wallpaper daemon
DAEMON=""
for d in swaybg hyprpaper swww-daemon mpvpaper wpaperd; do
  if pgrep -x "$d" >/dev/null 2>&1; then DAEMON="$d"; break; fi
done

if [[ -z "$DAEMON" ]]; then
  warn "no wallpaper daemon running — starting swaybg"
  if ! command -v swaybg >/dev/null 2>&1; then
    fail "swaybg not installed.  sudo pacman -S swaybg  then re-run this script."
    exit 1
  fi
  DAEMON="swaybg"
fi
ok "active wallpaper daemon: ${DAEMON}"

# 3. Apply the wallpaper
case "$DAEMON" in
  swaybg)
    pkill -x swaybg 2>/dev/null || true
    sleep 0.3
    nohup swaybg -i "$WP_DST" -m "$MODE" -c "$LETTERBOX_COLOR" >/dev/null 2>&1 &
    disown 2>/dev/null || true
    ok "swaybg restarted with ${WP_NAME} (mode: ${MODE}, letterbox: ${LETTERBOX_COLOR})"
    ;;
  hyprpaper)
    HYPRP_CONF="${HOME}/.config/hypr/hyprpaper.conf"
    mkdir -p "$(dirname "$HYPRP_CONF")"
    cat > "$HYPRP_CONF" <<EOF
# nyxus frost wallpaper — written by nyxus-set-frost-wallpaper.sh ${VERSION}
preload = ${WP_DST}
wallpaper = ,${WP_DST}
splash = false
EOF
    ok "wrote ${HYPRP_CONF}"
    if command -v hyprctl >/dev/null 2>&1; then
      hyprctl hyprpaper unload all >/dev/null 2>&1 || true
      hyprctl hyprpaper preload "$WP_DST" >/dev/null 2>&1 || true
      hyprctl hyprpaper wallpaper ",${WP_DST}" >/dev/null 2>&1 \
        && ok "applied via hyprctl (live, no restart)" \
        || warn "hyprctl apply failed — will load on next hyprpaper start"
    fi
    ;;
  swww-daemon)
    if command -v swww >/dev/null 2>&1; then
      swww img "$WP_DST" --transition-type fade --transition-duration 1 \
        && ok "applied via swww (fade transition)" \
        || fail "swww img failed"
    else
      fail "swww-daemon running but 'swww' CLI missing"
    fi
    ;;
  mpvpaper|wpaperd)
    warn "${DAEMON} detected — manual config required, wallpaper saved to ${WP_DST}"
    ;;
esac

echo
say "DONE.  wallpaper at: ${WP_DST}"
echo "  Re-run with a different mode:"
echo "    nyxus-set-frost-wallpaper.sh fit      # whole image centered, cream margins (default)"
echo "    nyxus-set-frost-wallpaper.sh fill     # crop to fill screen"
echo "    nyxus-set-frost-wallpaper.sh center   # sharp 1:1 image, cream borders"
echo "    nyxus-set-frost-wallpaper.sh tile     # repeat tile"
