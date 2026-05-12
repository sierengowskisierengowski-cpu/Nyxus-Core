#!/usr/bin/env bash
# NYXUS · EWW · notification history (dunst)
# Emits a single JSON object consumed by eww.yuck `notifications_layout`:
#   {
#     "items":  [ {id,app,summary,body,timestamp,default_action,muted}, ... ],
#     "groups": [ {app, count, muted, items: [...]}, ... ],   // grouped by app
#     "muted":  ["AppName", ...],                              // muted-app list
#     "total":   N,                                            // total in history
#     "shown":   N,                                            // total minus muted
#     "paused": "true|false"                                   // DND state
#   }
#
# Per-app mutes live in ~/.config/nyxus/notif-mutes (one app name per line,
# blank lines and # comments ignored). Toggled by notif-mute.sh.
set -u

mute_file="${XDG_CONFIG_HOME:-$HOME/.config}/nyxus/notif-mutes"
mkdir -p "$(dirname "$mute_file")"
[[ -f "$mute_file" ]] || : > "$mute_file"

# Build the muted-apps JSON array safely even when jq is absent.
muted_json="[]"
if command -v jq >/dev/null 2>&1; then
  muted_json=$(grep -Ev '^\s*(#|$)' "$mute_file" 2>/dev/null \
               | jq -R -s -c 'split("\n") | map(select(length>0))' \
               || echo "[]")
fi

items="[]"
groups="[]"
total=0
shown=0
paused="false"

if command -v dunstctl >/dev/null 2>&1; then
  [[ "$(dunstctl is-paused 2>/dev/null)" == "true" ]] && paused="true"
  total=$(dunstctl count history 2>/dev/null || echo 0)

  if command -v jq >/dev/null 2>&1; then
    raw=$(dunstctl history 2>/dev/null)
    if [[ -n "$raw" ]]; then
      # 1. Normalize each notification into a flat record + a `muted` flag.
      items=$(printf '%s' "$raw" | jq --argjson mutes "$muted_json" -c '
        (.data[0] // []) | map({
          id:             (.id.data // 0),
          app:            (.appname.data // "system"),
          summary:        (.summary.data // ""),
          body:           ((.body.data // "") | gsub("\n"; " ") | .[0:160]),
          timestamp:      (.timestamp.data // 0),
          default_action: (.default_action_name.data // ""),
          muted:          (([(.appname.data // "system")] | inside($mutes)))
        }) | sort_by(-.timestamp) | .[0:60]
      ' 2>/dev/null || echo "[]")

      shown=$(printf '%s' "$items" \
              | jq -r 'map(select(.muted | not)) | length' 2>/dev/null \
              || echo 0)

      # 2. Group by app for the section-style UI.
      #    `app_b64` is a base64 of the raw app name, used as a safe
      #    transport across the EWW → shell boundary so notification
      #    metadata can never inject shell syntax (closes a command-
      #    injection report from the P2.12 architect review).
      groups=$(printf '%s' "$items" | jq -c '
        group_by(.app) | map({
          app:     .[0].app,
          app_b64: (.[0].app | @base64),
          count:   length,
          muted:   .[0].muted,
          items:   (. | sort_by(-.timestamp))
        }) | sort_by(.muted, -(.items[0].timestamp))
      ' 2>/dev/null || echo "[]")
    fi
  fi
fi

if command -v jq >/dev/null 2>&1; then
  jq -nc \
    --argjson items  "$items" \
    --argjson groups "$groups" \
    --argjson muted  "$muted_json" \
    --argjson total  "${total:-0}" \
    --argjson shown  "${shown:-0}" \
    --arg     paused "$paused" \
    '{items:$items, groups:$groups, muted:$muted, total:$total, shown:$shown, paused:$paused}'
else
  # No-jq fallback: we can't build items/groups without jq, so the
  # contract MUST report total=0 to match — otherwise the EWW layout
  # would render a non-zero count badge over an empty list (P2.12
  # review round-2 regression fix). Empty-state copy is honest.
  printf '{"items":[],"groups":[],"muted":[],"total":0,"shown":0,"paused":"%s"}\n' \
    "$paused"
fi
