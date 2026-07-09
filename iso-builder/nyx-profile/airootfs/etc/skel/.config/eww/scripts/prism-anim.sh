#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────
# NYXUS · prism rim animator + living-theme frame mixer
# Streams JSON frames that drive the animated bar borders:
#   a  — rim sweep angle (deg), one full lap ~8.5s
#   b  — counter-rotating angle (a + 180, wraps)
#   p  — breath pulse 0..1, 3.4s sine cycle (glow intensity)
#   g  — slow secondary drift 0..1, 5.2s offset sine (inner sheen)
# Living-theme fields, mixed in from nyxus-pulsed's state file
# ($XDG_RUNTIME_DIR/nyxus-pulse.json, mtime-gated so idle cost is one
# stat per frame):
#   pr,pg,pb — event pulse color (rgb ints)   ps — pulse strength 0..1
#   fr,fg,fb — focused-app tint (rgb ints)    fs — tint strength 0..1
# Consumed by the PRISM deflisten in eww.yuck via inline :style on the
# four bar roots. Toggle with NYXUS_BAR_FX=off in nyxus.conf (emits one
# static frame and idles — zero CPU, bars keep a fixed prism rim).
# ─────────────────────────────────────────────────────────────────────
CONF="${HOME}/.config/eww/nyxus.conf"
[ -r "$CONF" ] && . "$CONF"

FX="${NYXUS_BAR_FX:-on}"
FPS="${NYXUS_BAR_FX_FPS:-15}"

if [ "$FX" != "on" ]; then
  echo '{"a":100,"b":280,"p":0.5,"g":0.5,"pr":255,"pg":60,"pb":172,"ps":0,"fr":43,"fg":210,"fb":255,"fs":0}'
  exec sleep infinity
fi

exec python3 -u - "$FPS" <<'PY'
import json, math, os, sys, time

fps = max(1.0, min(30.0, float(sys.argv[1])))
dt = 1.0 / fps
t0 = time.monotonic()

state_path = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"),
                          "nyxus-pulse.json")
live = {"pr": 255, "pg": 60, "pb": 172, "ps": 0.0,
        "fr": 43, "fg": 210, "fb": 255, "fs": 0.0}
last_mtime = 0.0

while True:
    t = time.monotonic() - t0
    a = (t * 42.0) % 360.0
    frame = {
        "a": round(a, 1),
        "b": round((a + 180.0) % 360.0, 1),
        "p": round((math.sin(t * math.tau / 3.4) + 1.0) / 2.0, 3),
        "g": round((math.sin(t * math.tau / 5.2 + 1.7) + 1.0) / 2.0, 3),
    }
    try:
        mt = os.stat(state_path).st_mtime
        if mt != last_mtime:
            last_mtime = mt
            with open(state_path) as f:
                st = json.load(f)
            pc, fc = st.get("pc", [255, 60, 172]), st.get("fc", [43, 210, 255])
            live = {"pr": int(pc[0]), "pg": int(pc[1]), "pb": int(pc[2]),
                    "ps": float(st.get("ps", 0.0)),
                    "fr": int(fc[0]), "fg": int(fc[1]), "fb": int(fc[2]),
                    "fs": float(st.get("fs", 0.0))}
    except (OSError, ValueError, IndexError, TypeError):
        pass
    frame.update(live)
    print(json.dumps(frame), flush=True)
    time.sleep(dt)
PY
