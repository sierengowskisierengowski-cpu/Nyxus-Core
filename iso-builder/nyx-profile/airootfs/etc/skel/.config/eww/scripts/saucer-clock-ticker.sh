#!/usr/bin/env bash
# NYXUS · EWW · saucer windshield clock — sliding marquee.
#
# Same technique as ticker.sh (fixed-width window sliding across a doubled
# ribbon, one column per poll) but for just the clock, in the saucer's
# measured windshield viewport. Content is tiny and cheap (no system-stats
# regen pass needed) so this stays a short, dedicated script rather than
# reusing ticker.sh's heavier machinery for a one-line clock.
set -u
export LC_ALL=C.UTF-8

CACHE_DIR="${XDG_RUNTIME_DIR:-/tmp}/nyxus-saucer-clock"
CACHE_OFFSET="${CACHE_DIR}/offset"
mkdir -p "${CACHE_DIR}"

WINDOW="${NYXUS_SAUCER_CLOCK_COLS:-16}"

text="$(date '+%H:%M:%S')  ·  $(date '+%a %d %b')     "
len=${#text}
if (( len < WINDOW )); then
  while (( ${#text} < WINDOW + 1 )); do text+="${text}     "; done
  len=${#text}
fi

off=0
[[ -r "${CACHE_OFFSET}" ]] && off=$(<"${CACHE_OFFSET}")
off=$(( (off + 1) % len ))
printf '%d' "${off}" > "${CACHE_OFFSET}"

double="${text}${text}"
window="${double:${off}:${WINDOW}}"

window="${window//\\/\\\\}"
window="${window//\"/\\\"}"

printf '{"text":"%s"}\n' "${window}"
