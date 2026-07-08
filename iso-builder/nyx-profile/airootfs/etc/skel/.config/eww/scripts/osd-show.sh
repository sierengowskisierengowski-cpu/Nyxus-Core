#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS · EWW OSD pop-up helper                                       ║
# ║  Usage: osd-show.sh <window-name> [duration-seconds]                 ║
# ║                                                                      ║
# ║  Opens an EWW window, then closes it after DURATION seconds. Uses an ║
# ║  ATOMIC mkdir-based lock + epoch deadline so rapid repeat key-presses║
# ║  (e.g. holding XF86AudioRaiseVolume) don't stack closers — each new  ║
# ║  call simply pushes the deadline forward; only one closer ever runs. ║
# ║                                                                      ║
# ║  Reads NYXUS_OSD_DURATION from ~/.config/eww/nyxus.conf when no      ║
# ║  duration arg is provided.                                           ║
# ║                                                                      ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
set -u
window="${1:?usage: osd-show.sh <window> [duration]}"

CONF="${HOME}/.config/eww/nyxus.conf"
[[ -r "$CONF" ]] && . "$CONF"
duration="${2:-${NYXUS_OSD_DURATION:-1.5}}"

runtime="${XDG_RUNTIME_DIR:-/tmp}"
deadline_file="${runtime}/nyxus-osd-${window}.deadline"
lock_dir="${runtime}/nyxus-osd-${window}.lock.d"

# Push the new deadline forward (epoch ms).
new_deadline=$(awk -v d="$duration" 'BEGIN{
  cmd = "date +%s%3N"; cmd | getline now; close(cmd);
  printf "%.0f", now + d * 1000
}')
echo "$new_deadline" > "$deadline_file"

# INSTANT VALUE (rev 2026-07-07): the OSD widgets read defpoll vars with
# 2-5s intervals, so a rapid volume-key burst used to show stale values.
# Force-refresh the backing var synchronously before the window opens.
scripts="${HOME}/.config/eww/scripts"
case "$window" in
  osd-volume)     eww update AUDIO="$("$scripts/audio.sh")"          2>/dev/null || true ;;
  osd-brightness) eww update BACKLIGHT="$("$scripts/brightness.sh")" 2>/dev/null || true ;;
  osd-mic)        eww update MIC="$("$scripts/mic.sh")"              2>/dev/null || true ;;
esac

# Open (idempotent) — re-opening triggers a value refresh on the bar.
eww open "$window" 2>/dev/null || true

# ATOMIC lock acquisition — mkdir succeeds for exactly one process.
# If another closer is already running it will read the bumped deadline
# from the file and wait further; we simply exit.
if ! mkdir "$lock_dir" 2>/dev/null; then
  # If the holder died without cleanup, stale lock — sweep it once.
  if [[ -e "$lock_dir/pid" ]] && ! kill -0 "$(cat "$lock_dir/pid" 2>/dev/null)" 2>/dev/null; then
    rm -rf "$lock_dir"
    mkdir "$lock_dir" 2>/dev/null || exit 0
  else
    exit 0
  fi
fi

# Spawn the single closer.
(
  echo $$ > "$lock_dir/pid"
  trap 'rm -rf "$lock_dir" "$deadline_file"' EXIT
  while :; do
    now=$(date +%s%3N)
    target=$(cat "$deadline_file" 2>/dev/null || echo 0)
    [[ $now -ge $target ]] && break
    remaining_ms=$(( target - now ))
    sleep "$(awk -v ms="$remaining_ms" 'BEGIN{printf "%.3f", ms/1000}')"
  done
  eww close "$window" 2>/dev/null || true
) &
disown
