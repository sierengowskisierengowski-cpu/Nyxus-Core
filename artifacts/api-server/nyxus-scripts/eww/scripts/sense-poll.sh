#!/usr/bin/env bash
# NYXUS - eww bridge for the nyxus-sense bus. Emits a compact JSON object
# (mood lowercased for CSS class use, energy, hacker) that the bars poll
# to drive the living-theme mood glow. ASCII-only. Safe if sense is down.
jq -c '{mood:(.mood//"prowl"|ascii_downcase), energy:(.energy//0), hacker:(.hacker//false)}' \
   "$HOME/.config/nyxus/sense.json" 2>/dev/null \
  || echo '{"mood":"prowl","energy":0,"hacker":false}'
