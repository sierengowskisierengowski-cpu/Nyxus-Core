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
        "cats": (a.get("categories") or ["Other"]),
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


CAT_ORDER = ["Internet", "Development", "Media", "Games", "Security",
             "Settings", "System", "Other"]


def sections(rows, per_cat=10, per_row=10):
    """Group the catalogue into labelled category sections.

    A flat grid of ~80 tiles reads as an undifferentiated wall - the owner's
    words: "looks like a ton of apps bunched together". Grouping gives the
    eye somewhere to land, and each category is capped to one row so the
    panel stays scannable; rofi covers the long tail.
    """
    buckets = {}
    for r in rows:
        cat = next((c for c in CAT_ORDER if c in r.get("cats", [])), "Other")
        buckets.setdefault(cat, []).append(r)
    out = []
    for cat in CAT_ORDER:
        items = buckets.get(cat) or []
        if not items:
            continue
        out.append({"label": cat.upper(),
                    "count": len(items),
                    "rows": chunk(items[:per_cat], per_row)})
    return out


def chunk(rows, per):
    """eww has no wrapping grid - emit explicit rows so the panel fills its
    width instead of running one long line into a scroller."""
    return [{"i": i, "cells": rows[i:i + per]} for i in range(0, len(rows), per)]


def mode_apps():
    rows = catalogue()
    return {"apps": rows, "rows": chunk(rows, 10), "count": len(rows)}


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
        for pid in pins_raw[:30]:
            a = _safe(lambda p=pid: A.find_app_by_id(p), None)
            if a:
                pins.append(_app_row(a))

    scratch = _safe(lambda: S.SCRATCH_FILE.read_text(encoding="utf-8"), "")
    lines = [l for l in scratch.splitlines() if l.strip()][:9]

    allrows = _safe(catalogue, [])
    pinned_ids = {p["id"] for p in pins}
    others = [a for a in allrows if a["id"] not in pinned_ids]

    return {
        "pin_rows": chunk(pins, 10),
        "cat_sections": sections(others),
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



PLACES = [
    ("Home",      "~",              "\uf015"),
    ("Downloads", "~/Downloads",    "\uf019"),
    ("Documents", "~/Documents",    "\uf0f6"),
    ("Pictures",  "~/Pictures",     "\uf03e"),
    ("Projects",  "~/Projects",     "\uf121"),
    ("Config",    "~/.config",      "\uf013"),
]


def mode_live():
    """START-only content: what is running, what was launched recently, and
    quick places. Deliberately NOT the machine vitals / weather / media that
    the HOME deck already shows - duplicating those makes the two stations
    interchangeable, which is the opposite of the point."""
    import subprocess

    running = []
    try:
        raw = subprocess.run(["hyprctl", "clients", "-j"], capture_output=True,
                             text=True, timeout=3).stdout
        for c in json.loads(raw):
            title = (c.get("title") or "").strip()
            if not title:
                continue
            running.append({
                "title": title[:34],
                "cls": (c.get("class") or "?")[:18],
                "ws": (c.get("workspace") or {}).get("name", "?"),
                "addr": c.get("address", ""),
            })
    except Exception:
        pass

    recent = []
    try:
        import settings as S
        import apps as A
        raw = json.loads(S.RECENT_FILE.read_text())
        for r in raw[:8]:
            a = _safe(lambda i=r.get("id"): A.find_app_by_id(i), None)
            if a:
                recent.append(_app_row(a))
    except Exception:
        pass

    return {
        "running": running,
        "run_count": len(running),
        "recent": recent,
        # two-up so PLACES costs 3 rows of height instead of 6 - the panel
        # is sized to its content and must fit the 882px gap between bars
        "place_rows": chunk([{"name": n, "path": p, "glyph": g}
                             for n, p, g in PLACES], 2),
    }



ARSENAL_REGISTRY = Path.home() / "Arsenal" / "registry.toml"
ARSENAL_CATS = {"defense": "DEFENSE", "offense": "OFFENSE",
                "ai": "AI", "infra": "INFRA"}


def _probe(spec):
    """Resolve a registry `status =` spec to a live bool. Mirrors what the
    Arsenal TUI does. Every probe is short-timeout: this runs on a poll and
    must never stall the panel."""
    import subprocess
    if not spec or spec == "none":
        return None
    try:
        kind, _, arg = spec.partition("=")
        if kind == "service_system":
            r = subprocess.run(["systemctl", "is-active", arg],
                               capture_output=True, text=True, timeout=2)
            return r.stdout.strip() == "active"
        if kind == "service_user":
            r = subprocess.run(["systemctl", "--user", "is-active", arg],
                               capture_output=True, text=True, timeout=2)
            return r.stdout.strip() == "active"
        if kind == "docker":
            r = subprocess.run(["docker", "ps", "--filter", f"name={arg}",
                                "--format", "{{.Names}}"],
                               capture_output=True, text=True, timeout=3)
            return bool(r.stdout.strip())
        if kind == "web":
            r = subprocess.run(["curl", "-fsS", "-o", "/dev/null",
                                "--max-time", "2", arg],
                               capture_output=True, timeout=3)
            return r.returncode == 0
    except Exception:
        return False
    return None


def mode_arsenal():
    """GowskiNet toolkit (jeTT / Bifrost / Meli / Honeypot / ...) with live
    state, straight off the same ~/Arsenal/registry.toml the Arsenal TUI
    reads - so adding a [[tool]] block shows up here too, no code change."""
    try:
        import tomllib
        data = tomllib.loads(ARSENAL_REGISTRY.read_text())
    except Exception:
        return {"groups": [], "live": 0, "total": 0}

    tools = data.get("tool", []) or []
    rows, live = [], 0
    for t in tools:
        ok = _probe(t.get("status"))
        if ok:
            live += 1
        rows.append({
            "id": t.get("id", ""),
            "name": t.get("name", "?"),
            "desc": (t.get("desc") or "")[:60],
            "cat": t.get("category", "infra"),
            "iface": t.get("interface", ""),
            "launch": t.get("launch", ""),
            "state": "live" if ok else ("down" if ok is False else "idle"),
        })

    groups = []
    for key, label in ARSENAL_CATS.items():
        items = [r for r in rows if r["cat"] == key]
        if items:
            groups.append({"label": label, "items": items, "n": len(items)})
    return {"groups": groups, "live": live, "total": len(rows)}


MODES = {"meta": mode_meta, "status": mode_status, "apps": mode_apps, "live": mode_live, "arsenal": mode_arsenal}

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "meta"
    fallback = {
        "meta": {"user": {"name": "operator", "subtitle": "", "initial": "N"},
                 "pins": [], "pin_count": 0, "scratch": [],
                 "scratch_empty": True, "scratch_path": ""},
        "status": {"items": []},
        "live": {"running": [], "run_count": 0, "recent": [], "places": []},
        "arsenal": {"groups": [], "live": 0, "total": 0},
        "apps": {"apps": [], "count": 0},
    }
    try:
        print(json.dumps(MODES[mode]()))
    except Exception:
        print(json.dumps(fallback.get(mode, {})))
