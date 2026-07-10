#!/usr/bin/env bash
# NYXUS · EWW · per-pill neon-tube rim animator
# Streams JSON at ~15fps:
#   a   — rim sweep angle (deg)
#   f0-f7 — per-pill flicker opacity (phase-offset sines; f5/f6 get rare dips)
# Consumed via PILLRIM deflisten + inline :style on bar pills / hud-tiles.
set -u

CONF="${HOME}/.config/eww/nyxus.conf"
[[ -r "$CONF" ]] && . "$CONF" 2>/dev/null || true

FPS="${NYXUS_BAR_FX_FPS:-15}"
FX="${NYXUS_BAR_FX:-on}"

if [[ "$FX" != "on" ]]; then
  echo '{"a":100,"f0":1,"f1":1,"f2":1,"f3":1,"f4":1,"f5":1,"f6":1,"f7":1}'
  exec sleep infinity
fi

exec python3 -u - "$FPS" <<'PY'
import json, math, random, sys, time

fps = max(1.0, min(30.0, float(sys.argv[1])))
dt = 1.0 / fps
t0 = time.monotonic()
next_dip = t0 + random.uniform(4.0, 9.0)
dip_until = 0.0
dip_vals = [1.0, 0.45, 0.75, 1.0]

while True:
    t = time.monotonic() - t0
    now = time.monotonic()
    a = (t * 55.0) % 360.0
    frame = {"a": round(a, 1)}
    for i in range(8):
        phase = i * 0.85
        flick = 0.82 + 0.18 * (math.sin(t * math.tau / 3.2 + phase) + 1.0) / 2.0
        frame[f"f{i}"] = round(flick, 3)
    if now >= next_dip and now >= dip_until:
        next_dip = now + random.uniform(5.0, 10.0)
        dip_until = now + 0.35
        for j, v in enumerate(dip_vals):
            frame["f5"] = round(v, 3)
            frame["f6"] = round(v * 0.9 + 0.1, 3)
            print(json.dumps(frame), flush=True)
            time.sleep(0.055)
        frame["f5"] = 1.0
        frame["f6"] = 1.0
    print(json.dumps(frame), flush=True)
    time.sleep(dt)
PY
