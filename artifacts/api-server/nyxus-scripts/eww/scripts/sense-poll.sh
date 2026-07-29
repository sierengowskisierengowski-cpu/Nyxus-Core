#!/usr/bin/env bash
# NYXUS - eww bridge for the nyxus-sense bus. Emits a compact JSON object
# (mood lowercased for CSS class use, energy, hacker) that the bars poll
# to drive the living-theme mood glow. ASCII-only. Safe if sense is down.
#
# Also carries the THREAT signal (2026-07-29) so the desktop can react to what
# the machine is actually experiencing, not just to its own CPU load:
#
#   threat        calm | watch | alert | breach   (lowercased, safe as a CSS class)
#   threat_blind  true when the threat state is UNKNOWN rather than quiet
#   threat_reason one short human line, for a tooltip
#
# `threat_blind` exists because quiet and blind must never render the same. This
# build already shipped a security component that reported healthy while seeing
# nothing (Bifrost's guardian answered "active" while dropping ~15,000 events an
# hour), so a consumer that shows blind as "all clear" is repeating that bug.
# When sense itself is down, the fallback below is blind=true for the same reason.
# NOTE on jq: `false // true` evaluates to TRUE, because `//` treats false as
# empty just like null. So a boolean whose default is true CANNOT use `//` - it
# would report blind=true even when the bus explicitly said blind=false, which
# is precisely the misreport this field exists to prevent. Check for null.
jq -c '{
  mood:          (.mood // "prowl" | ascii_downcase),
  energy:        (.energy // 0),
  hacker:        (if (.hacker == null) then false else .hacker end),
  threat:        (.threat.level // "calm" | ascii_downcase),
  threat_blind:  (if (.threat.blind == null) then true else .threat.blind end),
  threat_reason: (.threat.reason // "no threat feed")
}' "$HOME/.config/nyxus/sense.json" 2>/dev/null \
  || echo '{"mood":"prowl","energy":0,"hacker":false,"threat":"calm","threat_blind":true,"threat_reason":"sense bus down"}'
