#!/usr/bin/env bash
# NYXUS · caps-lock OSD trigger (rev 2026-07-07 r1 · Signature)
# Fired by a NON-CONSUMING bindn on Caps_Lock in nyxus-signature.conf,
# so the key still toggles normally. Reads the post-toggle state from
# hyprctl and pushes it into the shared OSD pop-up machinery.
set -u
export PATH="${HOME}/.local/bin:${PATH}"

# the bind fires on key-down; give the compositor a beat to commit the
# LED state before reading it back
sleep 0.08

ON="$(hyprctl devices -j 2>/dev/null \
      | jq -r '[.keyboards[] | select(.main == true)][0].capsLock // false')"

eww update CAPSSTATE="{\"on\":${ON}}" 2>/dev/null || true
exec "${HOME}/.config/eww/scripts/osd-show.sh" osd-capslock
