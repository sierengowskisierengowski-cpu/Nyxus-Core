#!/usr/bin/env bash
# NYXUS · EWW · charging-pill shimmer driver
# Streams {"sh":0..1} for liquid-fill opacity pulse on batt-charge pills.
# NYXUS_BAR_FX=off → static 1.0 (no CPU).
set -u

CONF="${HOME}/.config/eww/nyxus.conf"
[[ -r "$CONF" ]] && . "$CONF" 2>/dev/null || true

echo '{"sh":1}'
if [[ "${NYXUS_BAR_FX:-on}" == "off" ]]; then
  exec sleep infinity
fi

exec python3 -u <<'PY'
import json, math, time

t0 = time.monotonic()
while True:
    t = time.monotonic() - t0
    sh = round((math.sin(t * math.tau / 1.8) + 1.0) / 2.0, 3)
    print(json.dumps({"sh": sh}), flush=True)
    time.sleep(1.0 / 12.0)
PY
