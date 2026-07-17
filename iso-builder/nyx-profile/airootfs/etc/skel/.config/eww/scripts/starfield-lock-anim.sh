#!/usr/bin/env bash
# NYXUS · Starfield lock veil twinkle driver (fullscreen screensaver)
CONF="${HOME}/.config/eww/nyxus.conf"
[[ -r "$CONF" ]] && . "$CONF"

FX="${NYXUS_BAR_FX:-on}"
FPS="${NYXUS_BAR_FX_FPS:-8}"

if [[ "$FX" != "on" ]]; then
  echo '{"f":0}'
  exec sleep infinity
fi

exec python3 -u - "$FPS" <<'PY'
import json, math, sys, time

fps = max(1.0, min(12.0, float(sys.argv[1])))
dt = 1.0 / fps
t0 = time.monotonic()

while True:
    t = time.monotonic() - t0
    f = int(t * 5.0) % 16
    print(json.dumps({"f": f}), flush=True)
    time.sleep(dt)
PY
