"""
NYXUS Start — recently-used apps & files.

Combines two sources:
    1. Our own ~/.config/nyxus-start/recent.json  — every Start launch is
       pushed here, so the most recent app activity is always reflected
       even if Gtk.RecentManager is empty.
    2. Gtk.RecentManager  — system-wide recent files (last opened docs).

Returned shape (newest first, deduped, capped at 10):
    [
        {
            "kind":   "app" | "file",
            "id":     "firefox.desktop"  | "/path/to/file.txt",
            "name":   "Firefox"          | "report.txt",
            "icon":   "firefox"          | "text-x-generic",
            "ts":     1714665600,        # unix epoch
            "exec":   "firefox %u",      # apps only
            "uri":    "file:///..."      # files only
        }, ...
    ]

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations
import os
import time
from pathlib import Path
from typing import Dict, List

import gi

# ── NYXUS palette (single source of truth · rev r13) ────────────────
try:
    from nyxus_palette import (
        WHITE_PURE, WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        INK_FADED, INK_BLACK,
        GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE, HAIRLINE_INK,
        SHADOW_INK_ACTIVE, SHADOW_INK_INACTIVE,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
        format_css, assert_no_forbidden,
    )
except Exception:
    # palette module is shipped alongside every NYXUS app via
    # nyxus_install.sh; if it's missing, fall back to literals so
    # the app still launches.
    WHITE_PURE='#ffffff'; WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    INK_FADED='#0a0a0a'; INK_BLACK='#000000'
    GLASS_DARK='rgba(8, 12, 20, 0.55)'
    GLASS_DEEPER='rgba(15, 20, 32, 0.72)'
    GLASS_DEEPEST='rgba(5, 7, 12, 0.92)'
    HAIRLINE_WHITE='rgba(255, 255, 255, 0.10)'
    HAIRLINE_INK='rgba(0, 0, 0, 0.45)'
    SHADOW_INK_ACTIVE='rgba(0, 0, 0, 0.65)'
    SHADOW_INK_INACTIVE='rgba(0, 0, 0, 0.20)'
    RADIUS_CARD=14; RADIUS_PILL=12; RADIUS_INPUT=10
    FONT_UI='Inter'; FONT_MONO='JetBrains Mono'; FONT_DISPLAY='Inter Display'
    def format_css(t):
        _d = {
            'WHITE_PURE': WHITE_PURE, 'WHITE_OFF': WHITE_OFF,
            'GREY_LIGHT': GREY_LIGHT, 'GREY_MID': GREY_MID,
            'GREY_TERTIARY': GREY_TERTIARY,
            'INK_FADED': INK_FADED, 'INK_BLACK': INK_BLACK,
            'GLASS_DARK': GLASS_DARK, 'GLASS_DEEPER': GLASS_DEEPER,
            'GLASS_DEEPEST': GLASS_DEEPEST,
            'HAIRLINE_WHITE': HAIRLINE_WHITE, 'HAIRLINE_INK': HAIRLINE_INK,
            'SHADOW_INK_ACTIVE': SHADOW_INK_ACTIVE,
            'SHADOW_INK_INACTIVE': SHADOW_INK_INACTIVE,
            'RADIUS_CARD': RADIUS_CARD, 'RADIUS_PILL': RADIUS_PILL,
            'RADIUS_INPUT': RADIUS_INPUT,
            'FONT_UI': FONT_UI, 'FONT_MONO': FONT_MONO,
            'FONT_DISPLAY': FONT_DISPLAY,
        }
        return t.format_map(_d)
    def assert_no_forbidden(*a, **k): pass
# ─────────────────────────────────────────────────────────────────────

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, Gtk, GLib  # noqa: E402

from settings import load_recent, push_recent, clear_recent  # noqa: F401  (re-exported)
from apps import find_app_by_id


def _icon_for_uri(uri: str) -> str:
    """Pick a sensible themed icon name based on file extension."""
    lower = uri.lower()
    if any(lower.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".bmp")):
        return "image-x-generic"
    if any(lower.endswith(ext) for ext in (".mp4", ".mkv", ".webm", ".avi", ".mov")):
        return "video-x-generic"
    if any(lower.endswith(ext) for ext in (".mp3", ".flac", ".wav", ".ogg", ".m4a")):
        return "audio-x-generic"
    if any(lower.endswith(ext) for ext in (".pdf",)):
        return "application-pdf"
    if any(lower.endswith(ext) for ext in (".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz", ".tgz")):
        return "package-x-generic"
    if any(lower.endswith(ext) for ext in (".py", ".js", ".ts", ".sh", ".rs", ".go", ".cpp", ".c",
                                           ".h", ".java", ".rb", ".php", ".html", ".css", ".json", ".yaml", ".yml")):
        return "text-x-script"
    return "text-x-generic"


def _file_recent() -> List[Dict]:
    out: List[Dict] = []
    try:
        rm = Gtk.RecentManager.get_default()
        items = rm.get_items() or []
        for ri in items:
            try:
                uri = ri.get_uri() or ""
                if not uri.startswith("file://"):
                    continue
                path = ri.get_uri_display() or ""
                if not path or not Path(path).exists():
                    continue
                ts = ri.get_modified()
                # gtk4 GDateTime → seconds
                try:
                    ts_unix = int(ts.to_unix()) if hasattr(ts, "to_unix") else int(ts)
                except Exception:
                    ts_unix = int(time.time())
                out.append({
                    "kind": "file",
                    "id":   path,
                    "name": Path(path).name,
                    "icon": _icon_for_uri(path),
                    "ts":   ts_unix,
                    "exec": "",
                    "uri":  uri,
                })
            except Exception:
                continue
    except Exception:
        pass
    return out


def _app_recent() -> List[Dict]:
    out: List[Dict] = []
    for entry in load_recent():
        out.append({
            "kind": "app",
            "id":   entry.get("id", ""),
            "name": entry.get("name", entry.get("id", "")),
            "icon": entry.get("icon", ""),
            "ts":   int(entry.get("ts", 0)),
            "exec": "",
            "uri":  "",
        })
    return out


def list_recent(limit: int = 10) -> List[Dict]:
    """Return the merged most-recent entries (apps + files), newest first."""
    merged = _app_recent() + _file_recent()
    seen = set()
    deduped: List[Dict] = []
    for item in sorted(merged, key=lambda d: d.get("ts", 0), reverse=True):
        key = (item["kind"], item["id"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped


def humanize_ts(ts: int) -> str:
    """e.g. 'just now', '5 min ago', '2 h ago', 'Apr 28'."""
    if ts <= 0:
        return ""
    delta = int(time.time()) - int(ts)
    if delta < 30:
        return "just now"
    if delta < 3600:
        return f"{delta // 60} min ago"
    if delta < 86400:
        return f"{delta // 3600} h ago"
    if delta < 7 * 86400:
        return f"{delta // 86400} d ago"
    try:
        return time.strftime("%b %d", time.localtime(ts))
    except Exception:
        return ""


def remove_from_recent(kind: str, item_id: str) -> None:
    """Remove a single entry from the appropriate source."""
    if kind == "app":
        items = load_recent()
        items = [r for r in items if r.get("id") != item_id]
        from settings import RECENT_FILE
        try:
            import json as _json
            with RECENT_FILE.open("w") as f:
                _json.dump(items, f, indent=2)
        except OSError:
            pass
    elif kind == "file":
        try:
            rm = Gtk.RecentManager.get_default()
            uri = "file://" + item_id if not item_id.startswith("file://") else item_id
            rm.remove_item(uri)
        except Exception:
            pass
