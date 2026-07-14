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
  echo '{"a":100,"b":280,"p":0.5,"g":0.5,"pr":255,"pg":60,"pb":172,"ps":0,"fr":43,"fg":210,"fb":255,"fs":0,"ctop":-60,"cright":-60,"cbot":-60,"cleft":-60}'
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
    # Perimeter comet: ONE light travels clockwise around the screen edge,
    # handed off bar-to-bar at the corners. ~7s lap. Off-quadrant bars get
    # -60 (off-canvas) so only one bar shows the comet at a time.
    cang = (t * (360.0 / 32.0)) % 360.0
    ctop = cright = cbot = cleft = -60.0
    if cang < 90.0:
        ctop = cang / 0.9                       # left -> right across top
    elif cang < 180.0:
        cright = (cang - 90.0) / 0.9            # top -> bottom, right rail
    elif cang < 270.0:
        cbot = 100.0 - (cang - 180.0) / 0.9     # right -> left across bottom
    else:
        cleft = 100.0 - (cang - 270.0) / 0.9    # bottom -> top, left rail
    frame = {
        "a": round(a, 1),
        "b": round((a + 180.0) % 360.0, 1),
        "p": round((math.sin(t * math.tau / 3.4) + 1.0) / 2.0, 3),
        "g": round((math.sin(t * math.tau / 5.2 + 1.7) + 1.0) / 2.0, 3),
        "ctop": round(ctop, 1), "cright": round(cright, 1),
        "cbot": round(cbot, 1), "cleft": round(cleft, 1),
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
