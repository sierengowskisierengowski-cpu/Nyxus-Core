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
  [[ -f "${lock}/bars" ]] || return 0
  while read -r b; do
    [[ -n "$b" ]] && eww open "$b" 2>/dev/null || true
  done < "${lock}/bars"
  rm -rf "$lock"
}

# Orphan lock from crash/kill — no overlay active but bars were stashed.
if [[ -d "$lock" ]]; then
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
