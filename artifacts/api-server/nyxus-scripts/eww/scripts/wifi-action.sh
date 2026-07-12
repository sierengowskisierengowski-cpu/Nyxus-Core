#!/usr/bin/env bash
# NYXUS · EWW · wifi action handler
#
# rev r9-eww 2026-05-11 hardening:
#   SSIDs are accepted ONLY as base64-encoded strings (the `b64` field
#   from wifi-list.sh). They are decoded internally and passed to nmcli
#   as a discrete argv element, so quoting metacharacters in the SSID
#   cannot escape into shell.
#
# Usage:
#   wifi-action.sh connect    <BASE64_SSID>
#   wifi-action.sh disconnect <BASE64_SSID>   (take saved connection down)
#   wifi-action.sh autoconnect <BASE64_SSID>  (toggle autoconnect flag)
#   wifi-action.sh forget  <BASE64_SSID>
#   wifi-action.sh rescan
#   wifi-action.sh toggle
set -u

cmd="${1:-}"; arg="${2:-}"

decode_b64() {
  # validate input is a plausible base64 token before decoding
  [[ "$1" =~ ^[A-Za-z0-9+/=]+$ ]] || { echo "" ; return; }
  printf '%s' "$1" | base64 -d 2>/dev/null
}

prompt() {
  if   command -v rofi   >/dev/null 2>&1; then rofi -dmenu -password -p "Password" -lines 0 < /dev/null
  elif command -v wofi   >/dev/null 2>&1; then wofi --dmenu --password --prompt "Password" < /dev/null
  elif command -v zenity >/dev/null 2>&1; then zenity --password --title="WiFi password"
  else echo ""
  fi
}

case "$cmd" in
  toggle)
    cur=$(nmcli radio wifi 2>/dev/null)
    [[ "$cur" == enabled ]] && nmcli radio wifi off || nmcli radio wifi on
    ;;
  rescan)
    nmcli device wifi rescan 2>/dev/null || true
    ;;
  connect)
    ssid=$(decode_b64 "$arg")
    [[ -z "$ssid" ]] && { echo "wifi-action: invalid b64 ssid" >&2; exit 2; }
    if ! nmcli connection up    "$ssid" 2>/dev/null \
      && ! nmcli device wifi connect "$ssid" 2>/dev/null; then
      pw=$(prompt)
      [[ -z "$pw" ]] && exit 0
      out=$(nmcli device wifi connect "$ssid" password "$pw" 2>&1)
      command -v notify-send >/dev/null 2>&1 \
        && notify-send "WiFi" "$out" \
        || printf '%s\n' "$out"
    fi
    ;;
  disconnect)
    ssid=$(decode_b64 "$arg")
    [[ -z "$ssid" ]] && { echo "wifi-action: invalid b64 ssid" >&2; exit 2; }
    nmcli connection down "$ssid" 2>/dev/null || true
    ;;
  autoconnect)
    ssid=$(decode_b64 "$arg")
    [[ -z "$ssid" ]] && { echo "wifi-action: invalid b64 ssid" >&2; exit 2; }
    cur=$(nmcli -g connection.autoconnect connection show "$ssid" 2>/dev/null)
    if [[ "$cur" == "yes" ]]; then
      nmcli connection modify "$ssid" connection.autoconnect no 2>/dev/null || true
    else
      nmcli connection modify "$ssid" connection.autoconnect yes 2>/dev/null || true
    fi
    ;;
  forget)
    ssid=$(decode_b64 "$arg")
    [[ -z "$ssid" ]] && { echo "wifi-action: invalid b64 ssid" >&2; exit 2; }
    nmcli connection delete "$ssid" 2>/dev/null || true
    ;;
  *)
    echo "wifi-action: unknown command '$cmd'" >&2; exit 2 ;;
esac
