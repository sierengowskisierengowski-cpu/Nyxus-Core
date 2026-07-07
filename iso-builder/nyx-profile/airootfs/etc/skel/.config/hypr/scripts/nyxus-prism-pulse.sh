#!/usr/bin/env bash
# NYXUS easter egg - "prism pulse". Secret chord: SUPER+SHIFT+X.
# Spins the iridescent border gradient a full 3 turns around every
# window, then settles back to the stock 270deg Obsidian Prism ring.
# Single-instance guarded so mashing the chord can't stack spinners.
LOCK=/tmp/.nyxus-prism-pulse.lock
exec 9>"$LOCK"
flock -n 9 || exit 0

COLORS="rgba(ff3cacff) rgba(2bd2ffff) rgba(784bffff) rgba(ffb84dff)"

notify-send -u low -t 2600 "◤ X ◥ PRISM PULSE" "the eye is watching" 2>/dev/null

# 3 revolutions, 15deg per step, ~24ms per step = ~1.7s of spin
for rev in 1 2 3; do
  for ((deg = 270; deg < 630; deg += 15)); do
    hyprctl --batch "keyword general:col.active_border $COLORS $((deg % 360))deg" >/dev/null
    sleep 0.024
  done
done

hyprctl keyword general:col.active_border "$COLORS 270deg" >/dev/null
