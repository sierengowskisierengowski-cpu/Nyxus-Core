#!/usr/bin/env bash
# NYXUS · EWW · audio mixer probe
# Emits {sinks:[{id,name,description,default,vol,mute}], sources:[...], apps:[{id,name,vol,mute}]}
set -u

sinks="[]"; sources="[]"; apps="[]"

emit_node_list() {
  # $1 = "Sink" | "Source"  — uses wpctl status parser fallback to pactl
  local kind="$1" out=""
  if command -v pactl >/dev/null 2>&1; then
    local short
    if [[ "$kind" == "Sink" ]]; then short=sinks; else short=sources; fi
    local def
    def=$(pactl get-default-${short%s} 2>/dev/null)
    while IFS=$'\t' read -r id name desc; do
      [[ -z "$id" ]] && continue
      local volraw vol mute
      volraw=$(pactl get-${short%s}-volume "$id" 2>/dev/null | head -1)
      vol=$(grep -oE '[0-9]+%' <<<"$volraw" | head -1 | tr -d '%')
      vol="${vol:-0}"
      mute=$(pactl get-${short%s}-mute "$id" 2>/dev/null | awk '{print $2}')
      [[ "$mute" == yes ]] && mute=true || mute=false
      local default=false
      [[ "$name" == "$def" ]] && default=true
      out+="$(printf '{"id":"%s","name":"%s","description":"%s","default":%s,"vol":%s,"mute":%s},' \
        "$id" "${name//\"/}" "${desc//\"/}" "$default" "$vol" "$mute")"
    done < <(pactl list short ${short} 2>/dev/null | awk -F'\t' '{print $1"\t"$2"\t"$2}')
    # Pretty descriptions from `pactl list ${short}`
    out="${out%,}"
    echo "[$out]"
    return
  fi
  echo "[]"
}

emit_apps() {
  local out=""
  if command -v pactl >/dev/null 2>&1; then
    while read -r id; do
      [[ -z "$id" ]] && continue
      local name vol mute
      name=$(pactl list sink-inputs 2>/dev/null \
              | awk -v id="$id" '
                  /^Sink Input #/{cur=$3; sub("#","",cur)}
                  cur==id && /application.name = /{
                    gsub(/.*= "|"$/,""); print; exit
                  }')
      [[ -z "$name" ]] && name="app#$id"
      vol=$(pactl list sink-inputs 2>/dev/null \
              | awk -v id="$id" '
                  /^Sink Input #/{cur=$3; sub("#","",cur)}
                  cur==id && /Volume:/{
                    for(i=1;i<=NF;i++) if($i~"%"){gsub("%","",$i); print $i; exit}
                  }')
      vol="${vol:-100}"
      mute=$(pactl list sink-inputs 2>/dev/null \
              | awk -v id="$id" '
                  /^Sink Input #/{cur=$3; sub("#","",cur)}
                  cur==id && /Mute:/{print $2; exit}')
      [[ "$mute" == yes ]] && mute=true || mute=false
      out+="$(printf '{"id":"%s","name":"%s","vol":%s,"mute":%s},' \
        "$id" "${name//\"/}" "$vol" "$mute")"
    done < <(pactl list short sink-inputs 2>/dev/null | awk '{print $1}')
  fi
  out="${out%,}"
  echo "[$out]"
}

sinks=$(emit_node_list Sink)
sources=$(emit_node_list Source)
apps=$(emit_apps)

if command -v jq >/dev/null 2>&1; then
  jq -nc --argjson sinks "$sinks" --argjson sources "$sources" --argjson apps "$apps" \
    '{sinks:$sinks, sources:$sources, apps:$apps}'
else
  printf '{"sinks":%s,"sources":%s,"apps":%s}\n' "$sinks" "$sources" "$apps"
fi
