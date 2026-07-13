#!/usr/bin/env bash
# Slow trapped-fog drift for obsidian pill interiors (rev 2026-07-12).
set -u
FPS="${NYXUS_FOG_FPS:-3}"
STEP=$(python3 - <<'PY'
import os
fps=float(os.environ.get("NYXUS_FOG_FPS","3") or 3)
print(f"{1.0/max(fps,0.5):.3f}")
PY
)
t=0
while true; do
  read -r x y a < <(python3 - "$t" <<'PY'
import math, sys
t = float(sys.argv[1])
x = 50 + 38*math.sin(t*0.31) + 14*math.cos(t*0.17)
y = 50 + 34*math.cos(t*0.23) + 16*math.sin(t*0.19)
a = (t*7.5) % 360
print(f"{x:.1f} {y:.1f} {a:.1f}")
PY
)
  printf '{"x":%s,"y":%s,"a":%s}\n' "$x" "$y" "$a"
  t=$((t + 1))
  sleep "$STEP"
done
