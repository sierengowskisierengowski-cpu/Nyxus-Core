#!/usr/bin/env bash
# ============================================================================
#  NYXUS — render brand SVGs to PNG sizes for runtime consumers
#  ----------------------------------------------------------------------------
#  Invoked by the mkarchiso profile-build pre-seal hook (and may be run
#  manually). Uses rsvg-convert (librsvg) which is a hard dep of GTK and
#  therefore always present in the build host.
#
#  Output layout:
#    /usr/share/nyxus/brand/png/<mark>-<size>.png
#  Sizes: 16, 32, 48, 64, 96, 128, 256, 512.
#
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
set -euo pipefail

BRAND_DIR="${1:-iso-builder/nyx-profile/airootfs/usr/share/nyxus/brand}"
OUT_DIR="$BRAND_DIR/png"
SIZES=(16 32 48 64 96 128 256 512)
MARKS=(eclipse eclipse-cream constellation-n eye-of-nyx)

if ! command -v rsvg-convert >/dev/null 2>&1; then
  echo "render-brand-pngs: rsvg-convert not found — install librsvg" >&2
  exit 1
fi

mkdir -p "$OUT_DIR"

for mark in "${MARKS[@]}"; do
  src="$BRAND_DIR/${mark}.svg"
  if [[ ! -f "$src" ]]; then
    echo "render-brand-pngs: missing $src" >&2
    continue
  fi
  for size in "${SIZES[@]}"; do
    out="$OUT_DIR/${mark}-${size}.png"
    rsvg-convert -w "$size" -h "$size" "$src" -o "$out"
    echo "  ✓ ${mark}-${size}.png"
  done
done

# Wordmark (rectangular, render at common heights).
if [[ -f "$BRAND_DIR/wordmark-nyxus.svg" ]]; then
  for h in 32 48 64 96 128; do
    w=$((h * 5))
    rsvg-convert -w "$w" -h "$h" "$BRAND_DIR/wordmark-nyxus.svg" \
      -o "$OUT_DIR/wordmark-nyxus-${h}.png"
    echo "  ✓ wordmark-nyxus-${h}.png"
  done
fi

echo "render-brand-pngs: done ($(ls "$OUT_DIR" | wc -l) files in $OUT_DIR)"
