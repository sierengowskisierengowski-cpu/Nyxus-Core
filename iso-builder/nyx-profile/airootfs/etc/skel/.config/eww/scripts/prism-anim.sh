#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# NYXUS · prism rim animator
# Streams JSON frames that drive the animated bar borders:
#   a  — rim sweep angle (deg), one full lap ~8.5s
#   b  — counter-rotating angle (a + 180, wraps)
#   p  — breath pulse 0..1, 3.4s sine cycle (glow intensity)
#   g  — slow secondary drift 0..1, 5.2s offset sine (inner sheen)
# Consumed by the PRISM deflisten in eww.yuck via inline :style on the
# four bar roots. Toggle with NYXUS_BAR_FX=off in nyxus.conf (emits one
# static frame and idles — zero CPU, bars keep a fixed prism rim).
# ─────────────────────────────────────────────────────────────────────
CONF="${HOME}/.config/eww/nyxus.conf"
[ -r "$CONF" ] && . "$CONF"

FX="${NYXUS_BAR_FX:-on}"
FPS="${NYXUS_BAR_FX_FPS:-15}"

if [ "$FX" != "on" ]; then
  echo '{"a":100,"b":280,"p":0.5,"g":0.5}'
  exec sleep infinity
fi

exec python3 -u - "$FPS" <<'PY'
import json, math, sys, time

fps = max(1.0, min(30.0, float(sys.argv[1])))
dt = 1.0 / fps
t0 = time.monotonic()
while True:
    t = time.monotonic() - t0
    a = (t * 42.0) % 360.0
    frame = {
        "a": round(a, 1),
        "b": round((a + 180.0) % 360.0, 1),
        "p": round((math.sin(t * math.tau / 3.4) + 1.0) / 2.0, 3),
        "g": round((math.sin(t * math.tau / 5.2 + 1.7) + 1.0) / 2.0, 3),
    }
    print(json.dumps(frame), flush=True)
    time.sleep(dt)
PY
