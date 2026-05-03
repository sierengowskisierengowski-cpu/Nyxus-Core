#!/usr/bin/env bash
# ============================================================
#  NYXUS — Wlogout Theme Installer
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================

set -euo pipefail

WLOGOUT_DIR="$HOME/.config/wlogout"

echo ""
echo "  NYXUS Wlogout Theme Installer"
echo "  ──────────────────────────────────"
echo ""

mkdir -p "$WLOGOUT_DIR"

cp layout   "$WLOGOUT_DIR/layout"
cp style.css "$WLOGOUT_DIR/style.css"

echo "  [OK] layout   → $WLOGOUT_DIR/layout"
echo "  [OK] style.css → $WLOGOUT_DIR/style.css"
echo ""
echo "  Run wlogout with:"
echo "    wlogout --protocol layer-shell --layout $WLOGOUT_DIR/layout --css $WLOGOUT_DIR/style.css -b 4 -c 0 -r 0 -L 0"
echo ""
echo "  Or bind in hyprland.conf:"
echo "    bind = \$mod SHIFT, M, exec, wlogout --protocol layer-shell -b 4 -c 0 -r 0 -L 0"
echo ""
echo "  Silent. Dark. Purely Functional."
echo ""
