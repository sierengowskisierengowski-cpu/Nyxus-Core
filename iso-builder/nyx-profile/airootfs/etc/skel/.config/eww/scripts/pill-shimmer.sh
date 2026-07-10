#!/usr/bin/env bash
# NYXUS · pill liquid-fill shimmer (charging state)
# Streams {"sh": 0..1} for opacity/position pulse on .pill-fill-charging.
# NYXUS_BAR_FX=off pins at 0.5 (static half-bright fill).
set -u

CONF="${HOME}/.config/eww/nyxus.conf"
[[ -r "$CONF" ]] && . "$CONF" 2>/dev/null || true

if [[ "${NYXUS_BAR_FX:-on}" == "off" ]]; then
  echo '{"sh":0.5}'
  exec sleep infinity
fi

exec python3 -u <<'PY'
import json, math, time
t0 = time.monotonic()
while True:
    t = time.monotonic() - t0
    sh = (math.sin(t * math.tau / 1.8) + 1.0) / 2.0
    print(json.dumps({"sh": round(0.35 + sh * 0.55, 3)}), flush=True)
    time.sleep(1 / 12)
PY
