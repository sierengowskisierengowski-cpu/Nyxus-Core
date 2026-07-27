#!/usr/bin/env python3
"""
NYXUS · EWW · START station search.

Called from the panel's search box on every keystroke:
    (input :onchange "~/.config/eww/scripts/start-search.py {}")

Filtering happens HERE rather than in an eww expression on purpose - eww
0.5's expression language has no reliable array-filter, and pushing the
result with `eww update` is deterministic (the same reason the mood daemon
pushes SENSE instead of relying on a lazy per-window defpoll).

Also handles launching: `--run <query>` launches the top match, which is
what Enter in the search box does.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

APP_DIR = Path.home() / ".nyxus" / "nyxus-start"
sys.path.insert(0, str(APP_DIR))
sys.path.insert(0, str(Path.home() / ".config" / "eww" / "scripts"))

LIMIT = 8


def _eww(*args):
    subprocess.run(["eww", *args], check=False,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def _matches(query):
    """Reads the CACHED catalogue - see start_feed.catalogue(). Re-scanning
    desktop entries per keystroke is what froze the search box."""
    from start_feed import catalogue
    if not query.strip():
        return []
    q = query.strip().lower()
    rows = catalogue()
    scored = []
    for r in rows:
        name = r["name"].lower()
        if q in name:
            scored.append((0 if name.startswith(q) else 1, len(name), r))
        elif q in (r.get("tagline") or "").lower():
            scored.append((2, len(name), r))
    scored.sort(key=lambda t: (t[0], t[1]))
    return [r for _, _, r in scored[:LIMIT]]


def main():
    argv = sys.argv[1:]
    run = False
    if argv and argv[0] == "--run":
        run, argv = True, argv[1:]
    query = " ".join(argv).strip()

    try:
        rows = _matches(query)
    except Exception:
        rows = []

    if run:
        # Enter: launch the best match, then leave the box clean.
        if rows:
            cmd = rows[0]["cmd"]
            # strip desktop-entry field codes (%u %f %U ...) - they are not
            # shell arguments and a bare shell chokes on them
            cmd = " ".join(w for w in cmd.split() if not w.startswith("%"))
            subprocess.Popen(["sh", "-c", f"{cmd} &"], start_new_session=True)
        _eww("update", "STARTQ=")
        _eww("update", "STARTFOUND=" + json.dumps({"rows": [], "n": 0}))
        return

    _eww("update", "STARTFOUND=" + json.dumps({"rows": rows, "n": len(rows)}))


if __name__ == "__main__":
    main()
