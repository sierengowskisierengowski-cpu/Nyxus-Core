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

  # Bass-reactive border animation speed. Hyprland's borderangle animation
  # duration maps silence→slow-spin, peak→fast-spin. The 240→60 range is
  # chosen so silent music keeps a slow dreamlike sweep and loud peaks make
  # the border pulse visibly without becoming a strobe. Only updates when
  # the tier changes (4 bands) so hyprctl is never called on every frame.
  local tier
  if   (( bass >= 75 )); then tier=4   # peak   → 60s duration
  elif (( bass >= 50 )); then tier=3   # loud   → 110s
  elif (( bass >= 25 )); then tier=2   # medium → 180s
  else                        tier=1   # quiet  → 240s
  fi
  if [[ "${_CAVA_LAST_TIER:-0}" != "$tier" ]]; then
    _CAVA_LAST_TIER="$tier"
    local dur
    case "$tier" in
      4) dur=60  ;; 3) dur=110 ;; 2) dur=180 ;; *) dur=240 ;;
    esac
    hyprctl keyword animation "borderangle,1,${dur},linear,loop" >/dev/null 2>&1 &
  fi
}

# Restart cava if it dies (e.g. pulse restart) so the bar never goes stale.
_CAVA_LAST_TIER=0
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
