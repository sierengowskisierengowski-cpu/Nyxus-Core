#!/usr/bin/env bash
# NYXUS · EWW · event comet / pill splash driver
# Watches $XDG_RUNTIME_DIR/nyxus-pulse.json (nyxus-pulsed) and fires a
# bright streak across the bar + target-pill splash on ps spikes.
set -u

CONF="${HOME}/.config/eww/nyxus.conf"
[[ -r "$CONF" ]] && . "$CONF" 2>/dev/null || true

STATE="${XDG_RUNTIME_DIR:-/tmp}/nyxus-pulse.json"
FPS="${NYXUS_BAR_FX_FPS:-15}"

if [[ "${NYXUS_BAR_FX:-on}" == "off" ]]; then
  echo '{"x":50,"strength":0,"hue":"pink","target":"","pr":255,"pg":60,"pb":172}'
  exec sleep infinity
fi

exec python3 -u - "$STATE" "$FPS" <<'PY'
import json, math, os, sys, time

state_path, fps_s = sys.argv[1], sys.argv[2]
fps = max(4.0, min(30.0, float(fps_s)))
dt = 1.0 / fps

def hue_name(pc):
    r, g, b = pc
    if g > r and g > b:
        return "cyan"
    if r > 180 and b > 120:
        return "magenta"
    if r > 200 and g > 180:
        return "gold"
    return "pink"

def target_for(pc, fs):
    r, g, b = pc
    if fs > 0.4:
        return "cluster"
    if g > r + 40:
        return "audio"
    if r > 200 and b < 100:
        return "notif"
    return "net"

idle = {"x": 50, "strength": 0, "hue": "pink", "target": "", "pr": 255, "pg": 60, "pb": 172}
last_mtime = 0.0
last_ps = 0.0
burst = None  # (t0, pc, fs, target, hue)

while True:
    now = time.monotonic()
    try:
        mt = os.stat(state_path).st_mtime
        if mt != last_mtime:
            last_mtime = mt
            with open(state_path) as f:
                st = json.load(f)
            ps = float(st.get("ps", 0.0))
            fs = float(st.get("fs", 0.0))
            pc = st.get("pc", [255, 60, 172])
            if ps > 0.28 and ps > last_ps + 0.12:
                burst = (now, pc, max(ps, fs * 0.6), target_for(pc, fs), hue_name(pc))
            last_ps = ps
    except (OSError, ValueError, TypeError):
        pass

    if burst:
        t0, pc, peak, target, hue = burst
        elapsed = now - t0
        dur = 0.42
        if elapsed <= dur:
            p = elapsed / dur
            x = round(p * 100.0, 1)
            strength = round(peak * math.sin(p * math.pi), 3)
            frame = {"x": x, "strength": strength, "hue": hue, "target": target,
                     "pr": int(pc[0]), "pg": int(pc[1]), "pb": int(pc[2])}
        else:
            decay = min(1.0, (elapsed - dur) / 0.35)
            strength = round(peak * (1.0 - decay) * 0.35, 3)
            if strength < 0.02:
                burst = None
                frame = dict(idle)
            else:
                frame = {"x": 100, "strength": strength, "hue": hue, "target": target,
                         "pr": int(pc[0]), "pg": int(pc[1]), "pb": int(pc[2])}
    else:
        frame = dict(idle)

    print(json.dumps(frame), flush=True)
    time.sleep(dt)
PY
