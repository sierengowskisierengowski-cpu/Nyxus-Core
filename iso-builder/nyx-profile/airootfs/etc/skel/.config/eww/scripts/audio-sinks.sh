#!/usr/bin/env bash
# NYXUS · EWW · audio mixer probe (rev 2026-07-09 — pactl JSON backend)
# Emits {sinks:[{id,name,description,default,vol,mute}],
#        sources:[...same shape...],
#        apps:[{id,name,vol,mute}]}
# Uses `pactl -f json` (pipewire-pulse) for reliable human descriptions;
# monitors are filtered out of sources.
set -u

if ! command -v pactl >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
  echo '{"sinks":[],"sources":[],"apps":[]}'
  exit 0
fi

def_sink=$(pactl get-default-sink 2>/dev/null)
def_source=$(pactl get-default-source 2>/dev/null)

sinks=$(pactl -f json list sinks 2>/dev/null | jq -c --arg def "$def_sink" '
  [.[] | {
     id: (.index|tostring),
     name: .name,
     description: .description,
     default: (.name == $def),
     vol: ((.volume | to_entries | .[0].value.value_percent // "0%") | rtrimstr("%") | tonumber? // 0),
     mute: .mute
  }]' 2>/dev/null || echo '[]')

sources=$(pactl -f json list sources 2>/dev/null | jq -c --arg def "$def_source" '
  [.[] | select(.monitor_source == "" or (.name | test("\\.monitor$") | not)) | {
     id: (.index|tostring),
     name: .name,
     description: .description,
     default: (.name == $def),
     vol: ((.volume | to_entries | .[0].value.value_percent // "0%") | rtrimstr("%") | tonumber? // 0),
     mute: .mute
  }]' 2>/dev/null || echo '[]')

apps=$(pactl -f json list sink-inputs 2>/dev/null | jq -c '
  [.[] | {
     id: (.index|tostring),
     name: (.properties["application.name"] // .properties["media.name"] // ("app#" + (.index|tostring))),
     vol: ((.volume | to_entries | .[0].value.value_percent // "0%") | rtrimstr("%") | tonumber? // 0),
     mute: .mute
  }]' 2>/dev/null || echo '[]')

[[ -z "$sinks"   ]] && sinks="[]"
[[ -z "$sources" ]] && sources="[]"
[[ -z "$apps"    ]] && apps="[]"

jq -nc --argjson sinks "$sinks" --argjson sources "$sources" --argjson apps "$apps" \
  '{sinks:$sinks, sources:$sources, apps:$apps}'
