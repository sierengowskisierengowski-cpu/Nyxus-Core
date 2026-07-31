#!/usr/bin/env bash
# NYXUS · EWW · fullscreen-overlay shield (rev 2026-07-13)
#
# Closes the four bars while a fullscreen overlay is up, restores when all
# overlays close. Includes orphan recovery so a crash/reboot cannot leave
# bars hidden permanently.
set -u
win="${1:?usage: overlay-shield.sh <overlay-window>}"

runtime="${XDG_RUNTIME_DIR:-/tmp}"
lock="${runtime}/nyxus-overlay-shield.d"
OVERLAY_RE='^(dashboard|powermenu|cheatsheet|deepcore|mission|nyxus-hub|hotkey-cheatsheet|hotkey-recorder|screensaver|quicksettings|wifi|bluetooth|mixer|calendar|notifications|brightness-flyout|updates|snap-picker): '

restore_bars() {
  # A lock dir with no `bars` file inside is the signature of a run that was
  # killed between `mkdir "$lock"` and writing the stash. Returning early
  # here WITHOUT clearing the dir used to wedge the shield permanently: the
  # `mkdir "$lock"` below then failed on every later invocation, so the
  # script exited before it could ever hide the bars again, and every
  # fullscreen overlay kept its reserved-zone gap until the next reboot.
  # Always clear the lock, whether or not there was anything to restore.
  if [[ -f "${lock}/bars" ]]; then
    while read -r b; do
      [[ -n "$b" ]] && eww open "$b" 2>/dev/null || true
    done < "${lock}/bars"
  fi
  rm -rf "$lock"
}

# Orphan lock from crash/kill — no overlay active but bars were stashed.
#
# ⚠ GRACE PERIOD — do not remove. nyxus-overlay-open / nyxus-hub-open create
# this lock, stash the bars, close them, and only THEN map the overlay. For
# that window eww has not yet registered the new window, so `active-windows`
# does not list it and this branch would conclude the lock is orphaned and
# reopen the bars the opener just closed. Measured 2026-07-31: bar surfaces
# went 4 -> 6 -> 8 mid-open, the restored bar-top put reserved_top back to
# 40, and the overlay was shoved from y=0 back to y=40 — the very gap the
# opener exists to prevent. A lock younger than the grace period means an
# open is in flight; leave it alone. Real orphans are seconds-to-minutes old
# and are still collected on the next poll.
if [[ -d "$lock" ]]; then
  _age=$(( $(date +%s) - $(stat -c %Y "$lock" 2>/dev/null || echo 0) ))
  if [[ "$_age" -lt 3 ]]; then
    echo ""
    exit 0
  fi
  act="$(eww active-windows 2>/dev/null || true)"
  if ! grep -qE "$OVERLAY_RE" <<<"$act"; then
    restore_bars
  else
    echo ""
    exit 0
  fi
fi

mkdir "$lock" 2>/dev/null || { echo ""; exit 0; }

bars=$(eww active-windows 2>/dev/null | awk -F': ' '/^bar-/{print $1}')
if [[ -z "$bars" ]]; then
  rmdir "$lock" 2>/dev/null
  echo ""
  exit 0
fi
printf '%s\n' $bars > "$lock/bars"

for b in $bars; do eww close "$b" 2>/dev/null; done

(
  ticks=0
  while :; do
    act=$(eww active-windows 2>/dev/null) || break
    grep -qE "$OVERLAY_RE" <<<"$act" || break
    ticks=$((ticks + 1))
    # Safety: force restore after ~10 min stuck
    [[ $ticks -ge 1500 ]] && break
    sleep 0.4
  done
  restore_bars
) >/dev/null 2>&1 & disown

echo ""
