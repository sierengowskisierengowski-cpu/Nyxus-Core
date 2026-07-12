#!/usr/bin/env bash
# NYXUS - audio-reactive bar visualizer feed for EWW
# Runs cava in raw ascii mode and converts each frame (0-7 per bar)
# into unicode block glyphs. Emits one line per frame for deflisten.
set -u
CONF="$HOME/.config/eww/cava.conf"
GLYPHS=(▁ ▂ ▃ ▄ ▅ ▆ ▇ █)

command -v cava >/dev/null || { echo ""; exit 0; }

# Restart cava if it dies (e.g. pulse restart) so the bar never goes stale.
while :; do
  cava -p "$CONF" 2>/dev/null | while IFS= read -r line; do
    out=""
    IFS=';' read -ra vals <<< "$line"
    for v in "${vals[@]}"; do
      [[ "$v" =~ ^[0-7]$ ]] && out+="${GLYPHS[$v]}"
    done
    echo "$out"
  done
  sleep 2
done
