#!/usr/bin/env python3
"""
NYXUS · EWW · START station feed.

Emits ONE json blob for the big Start panel widget. This deliberately reuses
the existing nyxus-start modules (apps.py / status.py / settings.py) instead
of reimplementing app discovery and the GowskiNet probes - they already work,
and a second copy would drift.

Modes:
  meta    user chip + pins + recent + scratchpad preview   (slow poll)
  status  GowskiNet row: Phantom / Honeypot / VPN / online (fast poll)
  apps    the full installed-app catalogue                 (very slow poll)

Everything is wrapped so a failing probe degrades to a placeholder rather
than emitting invalid JSON - eww drops a var entirely if the poll prints
garbage, which would blank the whole panel.
"""
import json
import os
import sys
import time
from pathlib import Path

APP_DIR = Path.home() / ".nyxus" / "nyxus-start"
sys.path.insert(0, str(APP_DIR))

# nyxus-start's modules import Gtk bits for their own UI helpers; keep them
# from needing a display when we only want their data functions.
os.environ.setdefault("GDK_BACKEND", "x11")


def _safe(fn, default):
    try:
        return fn()
    except Exception:
        return default


def _icon_glyph(app):
    """The panel renders Nerd Font glyphs, not themed icons - eww cannot pull
    a GTK icon theme name. Map by category/name onto glyphs the bars already
    use (verified present in JetBrainsMono Nerd Font)."""
    name = (app.get("name") or "").lower()
    cats = " ".join(app.get("categories") or []).lower()
    table = [
        ("term", ""), ("console", ""),
        ("firefox", ""), ("chrom", ""), ("browser", ""),
        ("file", ""), ("thunar", ""), ("nautilus", ""),
        ("code", ""), ("develop", ""), ("editor", ""),
        ("music", ""), ("audio", ""), ("video", ""),
        ("game", ""), ("graphic", ""), ("image", ""),
        ("mail", ""), ("chat", ""), ("discord", ""),
        ("net", ""), ("system", ""), ("setting", ""),
        ("secur", ""), ("nyxus", "\U000f08c7"),
    ]
    for key, glyph in table:
        if key in name or key in cats:
            return glyph
    return ""


def _app_row(a):
    return {
        "id": a.get("id", ""),
        "name": a.get("name", "?"),
        "cmd": a.get("exec") or a.get("id") or "",
        "glyph": _icon_glyph(a),
        "tagline": (a.get("comment") or "")[:48],
    }


CACHE_FILE = Path.home() / ".cache" / "nyxus-start-apps.json"
CACHE_TTL = 600  # seconds


def catalogue(force=False):
    """Installed-app list, CACHED.

    PERF - this is why the search box froze: `input :onchange` fires per
    keystroke, and each fire re-enumerated ~400 desktop entries off disk
    (seconds per character). The catalogue changes only when software is
    installed, so it is cached and every keystroke now hits a json read.
    """
    import apps as A
    try:
        if not force and CACHE_FILE.exists():
            age = time.time() - CACHE_FILE.stat().st_mtime
            if age < CACHE_TTL:
                return json.loads(CACHE_FILE.read_text())
    except Exception:
        pass
    rows = [_app_row(a) for a in _safe(lambda: A.list_installed_apps(max_count=400), [])]
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(rows))
    except Exception:
        pass
    return rows


def chunk(rows, per):
    """eww has no wrapping grid - emit explicit rows so the panel fills its
    width instead of running one long line into a scroller."""
    return [{"i": i, "cells": rows[i:i + per]} for i in range(0, len(rows), per)]


def mode_apps():
    rows = catalogue()
    return {"apps": rows, "rows": chunk(rows, 6), "count": len(rows)}


def mode_status():
    import status as S
    g = _safe(S.gather, {})
    out = []
    for key in ("phantom", "honeypot", "vpn", "network"):
        v = g.get(key) or {}
        out.append({
            "key": key,
            "label": v.get("label", key.title()),
            "value": str(v.get("value", "--")),
            "ok": bool(v.get("ok", False)),
        })
    return {"items": out}


def mode_meta():
    import settings as S
    cfg = _safe(S.load_config, {})

    # pins.json is a bare list of app ids; resolve each to a launchable row
    pins = []
    pins_raw = _safe(lambda: json.loads(S.PINS_FILE.read_text()), [])
    if isinstance(pins_raw, dict):
        pins_raw = pins_raw.get("pinned", [])
    if pins_raw:
        import apps as A
        for pid in pins_raw[:18]:
            a = _safe(lambda p=pid: A.find_app_by_id(p), None)
            if a:
                pins.append(_app_row(a))

    scratch = _safe(lambda: S.SCRATCH_FILE.read_text(encoding="utf-8"), "")
    lines = [l for l in scratch.splitlines() if l.strip()][:9]

    allrows = _safe(catalogue, [])
    pinned_ids = {p["id"] for p in pins}
    others = [a for a in allrows if a["id"] not in pinned_ids]

    return {
        "pin_rows": chunk(pins, 6),
        "app_rows": chunk(others[:36], 6),
        "app_total": len(allrows),
        "user": {
            "name": cfg.get("user_name") or os.environ.get("USER", "operator"),
            "subtitle": cfg.get("user_subtitle") or "operator",
            "initial": (cfg.get("user_name") or os.environ.get("USER", "N"))[:1].upper(),
        },
        "pins": pins,
        "pin_count": len(pins),
        "scratch": lines,
        "scratch_empty": not lines,
        "scratch_path": str(S.SCRATCH_FILE),
    }


MODES = {"meta": mode_meta, "status": mode_status, "apps": mode_apps}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "meta"
    fallback = {
        "meta": {"user": {"name": "operator", "subtitle": "", "initial": "N"},
                 "pins": [], "pin_count": 0, "scratch": [],
                 "scratch_empty": True, "scratch_path": ""},
        "status": {"items": []},
        "apps": {"apps": [], "count": 0},
    }
    try:
        print(json.dumps(MODES[mode]()))
    except Exception:
        print(json.dumps(fallback.get(mode, {})))
