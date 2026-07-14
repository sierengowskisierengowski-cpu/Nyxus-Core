#!/usr/bin/env bash
# NYXUS · EWW · bluetooth scan + device list
# Emits {devices:[{mac,name,paired,connected,trusted,icon,battery}], powered, scanning}
set -u

powered="false"
scanning="false"
devices="[]"

if command -v bluetoothctl >/dev/null 2>&1; then
  bluetoothctl show 2>/dev/null | grep -q 'Powered: yes' && powered="true"
  bluetoothctl show 2>/dev/null | grep -q 'Discovering: yes' && scanning="true"

  if [[ "$powered" == "true" ]]; then
    rows=""
    while read -r line; do
      [[ -z "$line" ]] && continue
      mac=$(awk '{print $2}' <<<"$line")
      name=$(cut -d' ' -f3- <<<"$line")
      info=$(bluetoothctl info "$mac" 2>/dev/null)
      paired=false; connected=false; trusted=false; battery=-1; icon="○"
      grep -q 'Paired: yes'    <<<"$info" && paired=true
      grep -q 'Connected: yes' <<<"$info" && { connected=true; icon="◉"; }
      grep -q 'Trusted: yes'   <<<"$info" && trusted=true
      bp=$(awk '/Battery Percentage:/{gsub(/[()%]/,"",$NF); print $NF; exit}' <<<"$info")
      [[ "$bp" =~ ^[0-9]+$ ]] && battery=$bp
      rows+="$(printf '{"mac":"%s","name":"%s","paired":%s,"connected":%s,"trusted":%s,"icon":"%s","battery":%s}' \
        "$mac" "${name//\"/}" "$paired" "$connected" "$trusted" "$icon" "$battery"),"
    done < <(bluetoothctl devices 2>/dev/null)
    rows="${rows%,}"
    devices="[$rows]"
  fi
fi

if command -v jq >/dev/null 2>&1; then
  echo "$devices" | jq -c --arg powered "$powered" --arg scanning "$scanning" \
    '{devices:., powered:$powered, scanning:$scanning}' 2>/dev/null \
    || printf '{"devices":[],"powered":"%s","scanning":"%s"}\n' "$powered" "$scanning"
else
  printf '{"devices":%s,"powered":"%s","scanning":"%s"}\n' "$devices" "$powered" "$scanning"
fi
