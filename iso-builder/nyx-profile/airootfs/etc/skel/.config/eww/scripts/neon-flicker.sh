#!/usr/bin/env bash
# NYXUS · EWW · neon-sign flicker driver (rev 2026-07-09)
#
# Streams an opacity value for the wordmark-level labels (brand, hero
# clock, overlay titles) so they occasionally buzz like a real neon
# tube: long steady stretches (5-10s) punctuated by a short irregular
# double-blink. GTK3-in-eww ignores CSS @keyframes, so this deflisten
# drives inline :style opacity instead — same mechanism as the PRISM
# rim animator. Nearly zero CPU (sleeps between bursts).
#
# NYXUS_NEON_FLICKER=off in nyxus.conf pins it at full brightness.
set -u

CONF="${HOME}/.config/eww/nyxus.conf"
[[ -r "$CONF" ]] && . "$CONF" 2>/dev/null || true

echo "1"
if [[ "${NYXUS_NEON_FLICKER:-on}" == "off" ]]; then
  exec sleep infinity
fi

# a burst is a quick irregular dip-recover sequence (dips to ~0.5 for visibility)
BURSTS=(
  "0.50 1 0.65 1"
  "0.35 0.90 0.50 1"
  "0.45 1 0.40 0.85 1"
  "0.55 0.50 1"
  "0.30 1 0.55 1"
)

while :; do
  sleep $(( 5 + RANDOM % 6 ))
  burst="${BURSTS[$(( RANDOM % ${#BURSTS[@]} ))]}"
  for v in $burst; do
    echo "$v"
    sleep "0.0$(( 4 + RANDOM % 5 ))"
  done
  echo "1"
done
