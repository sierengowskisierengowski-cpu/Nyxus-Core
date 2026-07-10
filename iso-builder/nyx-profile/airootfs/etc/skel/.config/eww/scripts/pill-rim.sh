#!/usr/bin/env bash
# NYXUS · per-pill neon tube rim driver
# Streams JSON: a (rim angle deg), f0-f7 (per-pill flicker opacity 0.82-1.0)
# with phase offsets so chips don't blink in sync. NYXUS_BAR_FX=off freezes.
set -u

CONF="${HOME}/.config/eww/nyxus.conf"
[[ -r "$CONF" ]] && . "$CONF" 2>/dev/null || true

FPS="${NYXUS_BAR_FX_FPS:-15}"

if [[ "${NYXUS_BAR_FX:-on}" == "off" ]]; then
  echo '{"a":100,"f0":1,"f1":1,"f2":1,"f3":1,"f4":1,"f5":1,"f6":1,"f7":1}'
  exec sleep infinity
fi

exec python3 -u - "$FPS" <<'PY'
import json, math, random, sys, time

fps = max(1.0, min(30.0, float(sys.argv[1])))
dt = 1.0 / fps
t0 = time.monotonic()
burst_t = -99.0
burst_v = 1.0

while True:
    t = time.monotonic() - t0
    a = (t * 55.0) % 360.0
    frame = {"a": round(a, 1)}
    for i in range(8):
        phase = i * 1.15
        flick = 0.84 + 0.16 * (math.sin(t * math.tau / 2.9 + phase) + 1.0) / 2.0
        frame[f"f{i}"] = round(flick, 3)
    # rare irregular double-blink on brand-adjacent chips (f5 net, f6 notif, f7 power)
    if t - burst_t > 6.0 + random.random() * 5.0:
        burst_t = t
        for k in (5, 6, 7):
            frame[f"f{k}"] = round(0.42 + random.random() * 0.2, 3)
    elif t - burst_t < 0.18:
        for k in (5, 6, 7):
            frame[f"f{k}"] = round(min(1.0, frame[f"f{k}"] + 0.35), 3)
    print(json.dumps(frame), flush=True)
    time.sleep(dt)
PY
