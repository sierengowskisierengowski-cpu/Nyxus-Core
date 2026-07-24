#!/usr/bin/env bash
# NYXUS LENS — smooth compositor magnifier (rev r1 · 2026-07-07).
# Bound in nyxus-hyprland-flair.conf: SUPER+ALT+scroll in/out,
# SUPER+ALT+middle-click or SUPER+ALT+0 to reset.
# usage: nyxus-lens.sh in|out|reset

cur=$(hyprctl getoption cursor:zoom_factor -j 2>/dev/null | jq -r '.float' 2>/dev/null)
[ -z "$cur" ] || [ "$cur" = "null" ] && cur=1

case "$1" in
  in)  new=$(awk -v z="$cur" 'BEGIN { n = z * 1.2; if (n > 6) n = 6; printf "%.3f", n }') ;;
  out) new=$(awk -v z="$cur" 'BEGIN { n = z / 1.2; if (n < 1) n = 1; printf "%.3f", n }') ;;
  *)   new=1 ;;
esac

hyprctl keyword cursor:zoom_factor "$new" >/dev/null
