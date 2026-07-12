#!/usr/bin/env bash
# Generate a small thumbnail of a Hyprland window for hover-preview.
# $1 = window address (with or without 0x prefix). Writes PNG to
# $XDG_RUNTIME_DIR/nyxus-dock/preview-<addr>.png and prints the path.
set -u
addr="${1:-}"
[[ -z "$addr" ]] && exit 0
addr="${addr#0x}"
out_dir="${XDG_RUNTIME_DIR:-/tmp}/nyxus-dock"
mkdir -p "$out_dir"
out="$out_dir/preview-$addr.png"

# Throttle: reuse cached preview if generated within last 2s
if [[ -f "$out" ]]; then
  age=$(( $(date +%s) - $(stat -c %Y "$out" 2>/dev/null || echo 0) ))
  if (( age < 2 )); then echo "$out"; exit 0; fi
fi

# Find geometry of this window
geo=$(hyprctl -j clients 2>/dev/null | python3 -c "
import json, sys
addr = '0x$addr'
clients = json.loads(sys.stdin.read())
for c in clients:
    if c.get('address') == addr:
        x, y = c.get('at', [0,0])
        w, h = c.get('size', [0,0])
        print(f'{x},{y} {w}x{h}'); break
")

if [[ -n "$geo" ]] && command -v grim >/dev/null; then
  grim -g "$geo" -s 0.25 -t png "$out" 2>/dev/null && echo "$out"
fi
