#!/usr/bin/env bash
# NYXUS · EWW · bluetooth probe
# Reports power state, paired/connected device count, and a tooltip
# listing connected device names. JSON-escaped via jq.
set -u

powered="off"
connected=0
paired=0
device_list=""

if command -v bluetoothctl >/dev/null 2>&1; then
  if bluetoothctl show 2>/dev/null | grep -q 'Powered: yes'; then
    powered="on"
  fi
  paired=$(bluetoothctl devices Paired 2>/dev/null | wc -l)
  while read -r line; do
    [[ -z "$line" ]] && continue
    mac=$(awk '{print $2}' <<<"$line")
    name=$(cut -d' ' -f3- <<<"$line")
    if bluetoothctl info "$mac" 2>/dev/null | grep -q 'Connected: yes'; then
      connected=$((connected + 1))
      device_list="${device_list}${name}, "
    fi
  done < <(bluetoothctl devices 2>/dev/null)
fi

device_list="${device_list%, }"

if [[ "$powered" == "off" ]]; then
  icon="✕"; label="OFF"
  tooltip="Bluetooth · disabled"
elif [[ $connected -gt 0 ]]; then
  icon="◉"; label="$connected"
  tooltip="Bluetooth · ${connected} connected · ${device_list:-—}"
else
  icon="○"; label="ON"
  tooltip="Bluetooth · on · ${paired} paired devices"
fi

if command -v jq >/dev/null 2>&1; then
  jq -nc --arg icon "$icon" --arg label "$label" --arg tooltip "$tooltip" \
    --arg powered "$powered" --argjson connected "$connected" --argjson paired "$paired" \
    '{icon:$icon,label:$label,tooltip:$tooltip,powered:$powered,connected:$connected,paired:$paired}'
else
  printf '{"icon":"%s","label":"%s","tooltip":"%s","powered":"%s","connected":%s,"paired":%s}\n' \
    "$icon" "$label" "${tooltip//\"/}" "$powered" "$connected" "$paired"
fi
