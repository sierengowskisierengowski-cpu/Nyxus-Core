#!/usr/bin/env bash
# NYXUS - audio-reactive bar visualizer feed for EWW
# Runs cava in raw ascii mode and converts each frame (0-7 per bar)
# into unicode block glyphs. Emits one line per frame for deflisten.
set -u
CONF="$HOME/.config/eww/cava.conf"
GLYPHS=(▁ ▂ ▃ ▄ ▅ ▆ ▇ █)

command -v cava >/dev/null || { echo ""; exit 0; }

# Push a plain 0-100 energy scalar to a separate eww var alongside the
# glyph stream, so widgets that want to react to the beat (the boombox
# speaker "cones") don't have to parse glyph characters back into
# numbers. Uses the LOUDEST bar across the whole spectrum rather than a
# fixed low-frequency index -- which bars carry the energy shifts with
# cava's own frequency-range config and the source material (tested live
# against an 80Hz tone: it peaked in bars 4-9, not bars 0-1), so reading
# every bar's peak is the only assumption that holds for any track.
# Backgrounded + best-effort: a slow/failed `eww update` must never stall
# the audio-visualizer frame loop that the glyph stream depends on.
push_bass() {
  local mx=0
  for v in "$@"; do
    [[ "$v" =~ ^[0-7]$ ]] || continue
    (( v > mx )) && mx=$v
  done
  local bass=$(( mx * 100 / 7 ))
  eww update CAVA_BASS="$bass" >/dev/null 2>&1 &
}

# Restart cava if it dies (e.g. pulse restart) so the bar never goes stale.
while :; do
  cava -p "$CONF" 2>/dev/null | while IFS= read -r line; do
    out=""
    IFS=';' read -ra vals <<< "$line"
    for v in "${vals[@]}"; do
      [[ "$v" =~ ^[0-7]$ ]] && out+="${GLYPHS[$v]}"
    done
    echo "$out"
    push_bass "${vals[@]}"
  done
  sleep 2
done
