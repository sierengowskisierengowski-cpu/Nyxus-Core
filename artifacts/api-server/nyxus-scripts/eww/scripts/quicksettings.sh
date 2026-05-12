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

# Night Light (gammastep / wlsunset)
nightlight="off"
if pgrep -x gammastep >/dev/null 2>&1 || pgrep -x wlsunset >/dev/null 2>&1; then
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

# Display rotation — read the current Hyprland transform on the focused
# monitor (0=normal, 1=90°, 2=180°, 3=270°). Reported as the integer so
# the EWW tile can show "ROT 0/90/180/270" without guessing.
# This replaces the previous flag-only "rot_lock" stub (P2.12 review
# fix): rotation is now a real, observable system property.
rotate="0"
if command -v hyprctl >/dev/null 2>&1; then
  if command -v jq >/dev/null 2>&1; then
    rotate=$(hyprctl -j monitors 2>/dev/null \
             | jq -r '(map(select(.focused)) | .[0].transform) // 0' 2>/dev/null \
             || echo 0)
  else
    # No-jq fallback: walk plain-text `hyprctl monitors` output to
    # find the focused monitor's transform field (P2.12 review
    # round-3 fix — mirrors the awk strategy in qs-toggle.sh so the
    # rotate probe stays accurate on minimal Arch installs without jq).
    raw=$(hyprctl monitors 2>/dev/null) || raw=""
    mon=$(printf '%s\n' "$raw" \
          | awk '/^Monitor /{name=$2}
                 /focused: yes/{print name; exit}')
    if [[ -n "$mon" ]]; then
      rotate=$(printf '%s\n' "$raw" \
               | awk -v m="$mon" '
                   $1=="Monitor" && $2==m {found=1}
                   found && /transform:/ {print $2; exit}' \
               || echo 0)
    fi
  fi
  case "$rotate" in 0|1|2|3) : ;; *) rotate=0 ;; esac
fi

if command -v jq >/dev/null 2>&1; then
  jq -nc \
    --arg wifi "$wifi" --arg bt "$bt" --arg airplane "$airplane" \
    --arg dnd "$dnd" --arg nightlight "$nightlight" --arg profile "$profile" \
    --arg mic_mute "$mic_mute" --arg audio_mute "$audio_mute" \
    --arg rotate "$rotate" \
    '{wifi:$wifi,bt:$bt,airplane:$airplane,dnd:$dnd,nightlight:$nightlight,profile:$profile,mic_mute:$mic_mute,audio_mute:$audio_mute,rotate:$rotate}'
else
  printf '{"wifi":"%s","bt":"%s","airplane":"%s","dnd":"%s","nightlight":"%s","profile":"%s","mic_mute":"%s","audio_mute":"%s","rotate":"%s"}\n' \
    "$wifi" "$bt" "$airplane" "$dnd" "$nightlight" "$profile" "$mic_mute" "$audio_mute" "$rotate"
fi
