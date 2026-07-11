#!/usr/bin/env bash
# NYXUS · live moon phase for the starlight top bar.
# Emits {"glyph","name","pct"} — MDI moon glyphs (Nerd Fonts v3).
exec python3 - <<'PY'
import json, math, time

SYNODIC = 29.530588853
# reference new moon: 2000-01-06 18:14 UTC
REF = 947182440.0

age = ((time.time() - REF) % (SYNODIC * 86400)) / 86400
frac = age / SYNODIC
illum = round((1 - math.cos(2 * math.pi * frac)) / 2 * 100)

PHASES = [
    (0.0625, "\U000F0F64", "New Moon"),
    (0.1875, "\U000F0F67", "Waxing Crescent"),
    (0.3125, "\U000F0F61", "First Quarter"),
    (0.4375, "\U000F0F68", "Waxing Gibbous"),
    (0.5625, "\U000F0F62", "Full Moon"),
    (0.6875, "\U000F0F66", "Waning Gibbous"),
    (0.8125, "\U000F0F63", "Last Quarter"),
    (0.9375, "\U000F0F65", "Waning Crescent"),
    (1.0001, "\U000F0F64", "New Moon"),
]
for lim, glyph, name in PHASES:
    if frac < lim:
        break
print(json.dumps({"glyph": glyph, "name": name, "pct": illum}))
PY
