#!/usr/bin/env bash
# NYXUS · EWW · per-app notification mute toggle
# Usage:
#   notif-mute.sh toggle <AppName>
#   notif-mute.sh add    <AppName>
#   notif-mute.sh remove <AppName>
#   notif-mute.sh list
#
# Maintains ~/.config/nyxus/notif-mutes — one app name per line, no
# duplicates, blank/comment lines preserved on read but stripped on write.
# notif-history.sh consumes this file to flag entries with `muted: true`,
# and the EWW layout filters or dims them accordingly.
set -u

mute_file="${XDG_CONFIG_HOME:-$HOME/.config}/nyxus/notif-mutes"
mkdir -p "$(dirname "$mute_file")"
[[ -f "$mute_file" ]] || : > "$mute_file"

cmd="${1:-list}"
app="${2:-}"

_normalize() {
  # Sort + uniq, dropping blank lines.
  awk 'NF' "$mute_file" | sort -u
}

_write() {
  local tmp; tmp=$(mktemp "${mute_file}.XXXX")
  cat > "$tmp"
  mv -f "$tmp" "$mute_file"
}

case "$cmd" in
  list)
    _normalize
    ;;
  add)
    [[ -z "$app" ]] && { echo "notif-mute: add requires <AppName>" >&2; exit 2; }
    { _normalize; printf '%s\n' "$app"; } | sort -u | _write
    ;;
  remove)
    [[ -z "$app" ]] && { echo "notif-mute: remove requires <AppName>" >&2; exit 2; }
    _normalize | grep -Fxv -- "$app" | _write
    ;;
  toggle)
    [[ -z "$app" ]] && { echo "notif-mute: toggle requires <AppName>" >&2; exit 2; }
    if _normalize | grep -Fxq -- "$app"; then
      _normalize | grep -Fxv -- "$app" | _write
      echo "unmuted: $app"
    else
      { _normalize; printf '%s\n' "$app"; } | sort -u | _write
      echo "muted: $app"
    fi
    ;;
  *)
    echo "notif-mute: unknown command '$cmd' (use list|add|remove|toggle)" >&2
    exit 2
    ;;
esac
