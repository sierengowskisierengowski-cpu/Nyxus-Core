#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# NYXUS · Starlight Headliner twinkle driver
# Streams {f, tw} JSON frames for the fiber-optic star fields on all
# four bar backgrounds. `f` selects one of 8 pre-rendered twinkle PNG
# overlays; `tw` drives a subtle ambient ceiling glow in the ink layer.
# Toggle with NYXUS_BAR_FX=off in nyxus.conf (static frame, zero CPU).
# ─────────────────────────────────────────────────────────────────────
CONF="${HOME}/.config/eww/nyxus.conf"
[ -r "$CONF" ] && . "$CONF"

FX="${NYXUS_BAR_FX:-on}"
FPS="${NYXUS_BAR_FX_FPS:-12}"

if [ "$FX" != "on" ]; then
  echo '{"f":0,"tw":0.5}'
  exec sleep infinity
fi

exec python3 -u - "$FPS" <<'PY'
import json, math, sys, time

fps = max(1.0, min(20.0, float(sys.argv[1])))
dt = 1.0 / fps
t0 = time.monotonic()

while True:
    t = time.monotonic() - t0
    # 16 frames at 5 fps → 3.2s seamless loop; stars inside run 1x/2x/3x
    # harmonics so individual twinkles land every ~1-3s, all out of sync
    f = int(t * 5.0) % 16
    tw = round((math.sin(t * math.tau / 4.8 + 0.4) + 1.0) / 2.0, 3)
    print(json.dumps({"f": f, "tw": tw}), flush=True)
    time.sleep(dt)
PY
