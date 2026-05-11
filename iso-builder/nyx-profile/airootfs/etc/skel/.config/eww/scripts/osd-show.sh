#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS · EWW OSD pop-up helper                                       ║
# ║  Usage: osd-show.sh <window-name> [duration-seconds]                 ║
# ║                                                                      ║
# ║  Opens an EWW window, then closes it after DURATION seconds. Uses a  ║
# ║  per-window lockfile + epoch deadline so rapid repeat key-presses    ║
# ║  (e.g. holding XF86AudioRaiseVolume) don't stack closers — each new  ║
# ║  call simply pushes the deadline forward.                            ║
# ║                                                                      ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
set -u
window="${1:?usage: osd-show.sh <window> [duration]}"
duration="${2:-1.5}"

deadline_file="${XDG_RUNTIME_DIR:-/tmp}/nyxus-osd-${window}.deadline"
lock_file="${XDG_RUNTIME_DIR:-/tmp}/nyxus-osd-${window}.lock"

# Push the new deadline forward (epoch ms).
new_deadline=$(awk -v d="$duration" 'BEGIN{
  cmd = "date +%s%3N"; cmd | getline now; close(cmd);
  printf "%.0f", now + d * 1000
}')
echo "$new_deadline" > "$deadline_file"

# Always (re-)open the window — eww open is idempotent and re-opening is
# what makes the bar value update visually on each repeat key.
eww open "$window" 2>/dev/null || true

# If a closer is already running for this window, exit — it will read the
# updated deadline and wait further.
if [[ -e "$lock_file" ]] && kill -0 "$(cat "$lock_file" 2>/dev/null)" 2>/dev/null; then
  exit 0
fi

# Spawn the closer in the background and record its pid.
(
  echo $$ > "$lock_file"
  while :; do
    now=$(date +%s%3N)
    target=$(cat "$deadline_file" 2>/dev/null || echo 0)
    [[ $now -ge $target ]] && break
    remaining_ms=$(( target - now ))
    sleep "$(awk -v ms="$remaining_ms" 'BEGIN{printf "%.3f", ms/1000}')"
  done
  eww close "$window" 2>/dev/null || true
  rm -f "$lock_file" "$deadline_file"
) &
disown
