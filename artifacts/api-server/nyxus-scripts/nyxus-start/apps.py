"""
NYXUS Start — installed-app discovery via Gio.AppInfo.

Returns a normalized list of dicts:
    {
        "id":          "firefox.desktop",        # Gio app id (unique)
        "name":        "Firefox",
        "exec":        "firefox %u",
        "icon":        "firefox",                # gtk icon name (or empty)
        "comment":     "Web Browser",
        "categories":  ["Internet"],             # mapped NYXUS categories
        "raw":         "Application;Network;WebBrowser;",
        "desktop":     "/usr/share/applications/firefox.desktop"  # may be ""
    }

NYXUS categories (matches the UI filter):
    System, Security, Internet, Media, Development, Games, Settings, Other

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations
import os
import shlex
from pathlib import Path
from typing import Dict, List, Optional

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
from gi.repository import Gio  # noqa: E402


# ── XDG → NYXUS category mapping (first match wins; case-insensitive)
CATEGORY_MAP = [
    ("Security",    {"security", "nyxus-security", "phantom", "shield", "godsapp"}),
    ("Internet",    {"network", "webbrowser", "email", "chat", "instantmessaging",
                     "filetransfer", "p2p", "remoteaccess", "telephony", "internet"}),
    ("Media",       {"audiovideo", "audio", "video", "player", "tv", "graphics",
                     "photography", "music", "art"}),
    ("Development", {"development", "ide", "building", "debugger", "revisioncontrol",
                     "translation", "webdevelopment"}),
    ("Games",       {"game", "actiongame", "adventuregame", "arcadegame", "boardgame",
                     "kidsgame", "logicgame", "roleplaying", "shootergame", "simulation",
                     "sportsgame", "strategygame"}),
    ("Settings",    {"settings", "desktopsettings", "hardwaresettings", "preferences"}),
    ("System",      {"system", "monitor", "filemanager", "filetools", "terminalemulator",
                     "utility", "core", "accessibility"}),
]

NYXUS_CATEGORIES = ["System", "Security", "Internet", "Media",
                    "Development", "Games", "Settings", "Other"]


def _classify(raw_categories: str, app_id: str = "", name: str = "") -> List[str]:
    raw_lower = (raw_categories or "").lower()
    name_lower = (name or "").lower()
    id_lower = (app_id or "").lower()

    out: List[str] = []
    # Force NYXUS-branded apps into Security if they're security stack pieces
    if any(t in id_lower or t in name_lower for t in
           ("nyxus-phantom", "phantom", "shield", "godsapp", "nyxus-security")):
        out.append("Security")

    for cat, tokens in CATEGORY_MAP:
        for tok in tokens:
            if tok in raw_lower:
                if cat not in out:
                    out.append(cat)
                break

    if not out:
        out.append("Other")
    return out


def _icon_to_string(icon: Optional[Gio.Icon]) -> str:
    """
    Best effort to coerce a Gio.Icon → an icon "spec" string GTK can resolve.

    Themed icons normally carry a chain of fallback names (e.g.
    "firefox;applications-internet"). We preserve the entire chain
    semicolon-joined so the renderer can try each one in order — this
    is what makes pinned tiles actually show their app icon instead of
    falling back to the purple rocket glyph for every entry whose
    primary icon name isn't present in the user's icon theme.
    """
    if icon is None:
        return ""
    try:
        if isinstance(icon, Gio.ThemedIcon):
            names = list(icon.get_names() or [])
            return ";".join(n for n in names if n)
        if isinstance(icon, Gio.FileIcon):
            f = icon.get_file()
            return f.get_path() or ""
        return icon.to_string() or ""
    except Exception:
        return ""


def list_installed_apps(max_count: int = 500) -> List[Dict]:
    """Return all visible Gio.AppInfo entries, sorted A→Z."""
    out: List[Dict] = []
    for ai in Gio.AppInfo.get_all():
        try:
            if not ai.should_show():
                continue
            name = (ai.get_display_name() or ai.get_name() or "").strip()
            if not name:
                continue
            app_id = ai.get_id() or ""
            exec_cmd = ai.get_commandline() or ""
            comment = ai.get_description() or ""
            icon = _icon_to_string(ai.get_icon())

            raw_cats = ""
            try:
                raw_cats = ai.get_categories() or ""
            except Exception:
                pass

            cats = _classify(raw_cats, app_id, name)

            desktop_path = ""
            try:
                if hasattr(ai, "get_filename"):
                    desktop_path = ai.get_filename() or ""
            except Exception:
                pass

            out.append({
                "id":         app_id,
                "name":       name,
                "exec":       exec_cmd,
                "icon":       icon,
                "comment":    comment,
                "categories": cats,
                "raw":        raw_cats,
                "desktop":    desktop_path,
            })
        except Exception:
            continue

    out.sort(key=lambda d: d["name"].lower())
    return out[:max_count]


def find_app_by_id(app_id: str) -> Optional[Dict]:
    """Find a single installed app by id (or partial id / launcher name)."""
    if not app_id:
        return None
    target = app_id.lower()
    target_no_ext = target.replace(".desktop", "")
    for app in list_installed_apps(max_count=2000):
        aid = (app["id"] or "").lower()
        if aid == target or aid.replace(".desktop", "") == target_no_ext:
            return app
    # Fall back: match by exec basename or display-name slug
    for app in list_installed_apps(max_count=2000):
        exec_first = ""
        try:
            exec_parts = shlex.split(app["exec"])
            if exec_parts:
                exec_first = os.path.basename(exec_parts[0]).lower()
        except Exception:
            pass
        if exec_first == target_no_ext:
            return app
    return None


def search_apps(query: str, apps: List[Dict], limit: int = 30) -> List[Dict]:
    """Score apps by how well they match a free-text query."""
    q = (query or "").strip().lower()
    if not q:
        return apps[:limit]
    scored = []
    for app in apps:
        name = app["name"].lower()
        desc = (app.get("comment") or "").lower()
        score = 0
        if name == q:
            score += 100
        if name.startswith(q):
            score += 60
        if q in name:
            score += 30
        for word in name.split():
            if word.startswith(q):
                score += 12
                break
        if q in desc:
            score += 6
        if score:
            scored.append((score, app))
    scored.sort(key=lambda t: (-t[0], t[1]["name"].lower()))
    return [a for _, a in scored[:limit]]
