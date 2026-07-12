#!/usr/bin/env bash
# NYXUS · EWW · quick-settings state probe
# Emits a single JSON object with all toggle states for the QS panel.
set -u

state_file="${XDG_RUNTIME_DIR:-/tmp}/nyxus-qs.state"
touch "$state_file" 2>/dev/null || true
. "$state_file" 2>/dev/null || true

# WiFi
wifi="off"
if command -v nmcli >/dev/null 2>&1; then
  nmcli radio wifi 2>/dev/null | grep -qi enabled && wifi="on"
fi

# Bluetooth
bt="off"
if command -v bluetoothctl >/dev/null 2>&1; then
  bluetoothctl show 2>/dev/null | grep -q 'Powered: yes' && bt="on"
fi

# Airplane (rfkill all)
airplane="off"
if command -v rfkill >/dev/null 2>&1; then
  rfkill list 2>/dev/null | grep -q 'Soft blocked: yes' && airplane="on"
fi

# DND (dunst)
dnd="off"
if command -v dunstctl >/dev/null 2>&1; then
  [[ "$(dunstctl is-paused 2>/dev/null)" == "true" ]] && dnd="on"
fi

# Night Light (gammastep / wlsunset / nyxus-shader night filter)
nightlight="off"
if pgrep -x gammastep >/dev/null 2>&1 || pgrep -x wlsunset >/dev/null 2>&1; then
  nightlight="on"
elif [[ "$(cat "$HOME/.config/nyxus/shader.state" 2>/dev/null)" == "night" ]]; then
  nightlight="on"
fi

# Power profile
profile="balanced"
if command -v powerprofilesctl >/dev/null 2>&1; then
  profile=$(powerprofilesctl get 2>/dev/null || echo balanced)
fi

# Mic
mic_mute="off"
if command -v wpctl >/dev/null 2>&1; then
  wpctl get-volume @DEFAULT_AUDIO_SOURCE@ 2>/dev/null | grep -q MUTED && mic_mute="on"
fi

# Audio mute
audio_mute="off"
if command -v wpctl >/dev/null 2>&1; then
  wpctl get-volume @DEFAULT_AUDIO_SINK@ 2>/dev/null | grep -q MUTED && audio_mute="on"
fi

# Rotation lock (laptop)
rot_lock="${NYXUS_ROT_LOCK:-off}"

# Auto-brightness placeholder
auto_bright="${NYXUS_AUTO_BRIGHT:-off}"

if command -v jq >/dev/null 2>&1; then
  jq -nc \
    --arg wifi "$wifi" --arg bt "$bt" --arg airplane "$airplane" \
    --arg dnd "$dnd" --arg nightlight "$nightlight" --arg profile "$profile" \
    --arg mic_mute "$mic_mute" --arg audio_mute "$audio_mute" \
    --arg rot_lock "$rot_lock" --arg auto_bright "$auto_bright" \
    '{wifi:$wifi,bt:$bt,airplane:$airplane,dnd:$dnd,nightlight:$nightlight,profile:$profile,mic_mute:$mic_mute,audio_mute:$audio_mute,rot_lock:$rot_lock,auto_bright:$auto_bright}'
else
  printf '{"wifi":"%s","bt":"%s","airplane":"%s","dnd":"%s","nightlight":"%s","profile":"%s","mic_mute":"%s","audio_mute":"%s","rot_lock":"%s","auto_bright":"%s"}\n' \
    "$wifi" "$bt" "$airplane" "$dnd" "$nightlight" "$profile" "$mic_mute" "$audio_mute" "$rot_lock" "$auto_bright"
fi
