#!/usr/bin/env bash
set -u

pick() {
  (( RANDOM % 100 < 35 )) && echo true || echo false
}

# The saucer alien is a rare easter egg, not a recurring effect: at a 7s poll
# interval, 6% works out to roughly once every two minutes. Deliberately much
# rarer than the other glitches - the whole point is that it catches the owner
# off guard, so it must not become wallpaper.
rare() {
  (( RANDOM % 100 < 6 )) && echo true || echo false
}

printf '{"brand":%s,"stamp":%s,"clock":%s,"ticker":%s,"search":%s,"alien":%s}\n' \
  "$(pick)" "$(pick)" "$(pick)" "$(pick)" "$(pick)" "$(rare)"
