"""
NYXUS Panel — Settings module.

Provides a Gtk.Window-based settings dialog (notebook-tabbed) and a tiny
JSON-backed config object.  All defaults live here; the rest of the app
imports `load_config()` and `save_config()`.

© 2026 Joseph A. Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

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
from gi.repository import Gtk, GLib, Gio, Pango  # noqa: E402

# ───────────────────────────────────────────────── paths
CFG_DIR  = Path(os.path.expanduser("~/.config/nyxus-panel"))
CFG_PATH = CFG_DIR / "config.json"
CACHE_DIR = CFG_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
(CACHE_DIR / "thumbs").mkdir(parents=True, exist_ok=True)
(CACHE_DIR / "favicons").mkdir(parents=True, exist_ok=True)

# ───────────────────────────────────────────────── default sources
# Curated tech / Linux / security RSS feeds.  Each entry: id, label, url, category.
DEFAULT_SOURCES: List[Dict[str, str]] = [
    # Linux
    {"id": "distrowatch", "label": "DistroWatch",       "url": "https://distrowatch.com/news/dw.xml",                     "cat": "linux"},
    {"id": "lwn",          "label": "LWN.net",           "url": "https://lwn.net/headlines/newrss",                        "cat": "linux"},
    {"id": "phoronix",     "label": "Phoronix",          "url": "https://www.phoronix.com/rss.php",                        "cat": "linux"},
    {"id": "archnews",     "label": "Arch Linux News",   "url": "https://archlinux.org/feeds/news/",                       "cat": "linux"},
    {"id": "kalinews",     "label": "Kali Linux Blog",   "url": "https://www.kali.org/rss.xml",                            "cat": "linux"},
    # Security
    {"id": "krebs",        "label": "Krebs on Security", "url": "https://krebsonsecurity.com/feed/",                       "cat": "security"},
    {"id": "thn",          "label": "The Hacker News",   "url": "https://feeds.feedburner.com/TheHackersNews",             "cat": "security"},
    {"id": "bleeping",     "label": "Bleeping Computer", "url": "https://www.bleepingcomputer.com/feed/",                  "cat": "security"},
    {"id": "nvd_critical", "label": "NVD CVEs",          "url": "https://nvd.nist.gov/feeds/xml/cve/misc/nvd-rss.xml",     "cat": "security"},
    # Hardware
    {"id": "nvidia_dev",   "label": "NVIDIA Developer",  "url": "https://developer.nvidia.com/blog/feed/",                 "cat": "hardware"},
    {"id": "anandtech",    "label": "AnandTech",         "url": "https://www.anandtech.com/rss/",                          "cat": "hardware"},
    {"id": "tomshw",       "label": "Tom's Hardware",    "url": "https://www.tomshardware.com/feeds/all",                  "cat": "hardware"},
    {"id": "notebook",     "label": "NotebookCheck",     "url": "https://www.notebookcheck.net/News.152.0.html?type=rss",  "cat": "hardware"},
    # Developer
    {"id": "github",       "label": "GitHub Blog",       "url": "https://github.blog/feed/",                               "cat": "dev"},
    {"id": "python",       "label": "Python.org",        "url": "https://www.python.org/jobs/feed/rss/",                   "cat": "dev"},
]

DEFAULT_CONFIG: Dict[str, Any] = {
    "version": 1,
    "open_on_hover": False,
    "hover_delay_ms": 500,
    "open_on_click": True,
    "reduce_animations": False,
    "panel_position": "above-taskbar",     # above-taskbar | side
    "refresh_interval_min": 30,            # 15 | 30 | 60
    "max_articles": 30,
    "browser": "chromium",                 # chromium | firefox | xdg-open | <custom>
    "browser_private": False,
    "browser_reader_mode": False,
    "notify_breaking_security": True,
    "load_on_startup": True,
    # source enable/disable: dict id -> bool (anything missing defaults to True)
    "sources": {s["id"]: True for s in DEFAULT_SOURCES},
    "custom_sources": [],                  # list of {label, url, cat}
    "keyword_allow": [],                   # only show articles containing any of these (empty == all)
    "keyword_block": [],                   # never show articles containing these
    "saved_articles": [],                  # heart icon
    "read_later": [],                      # bookmark icon
    # ── Appearance (cross-app theme tuning) ──────────────────────────
    "theme_glow_intensity": 35,            # 0-100 — neon-glow strength
    "theme_bg_opacity":     100,           # 0-100 — graffiti background opacity
    "theme_font_scale":     100,           # 80-140 — global font size multiplier (%)
    "theme_palette":        "godsapp",     # "godsapp" (chalky white) | "neon" (legacy pink/purple)
}

# ── Cross-app config locations (Profile + Notifications tabs read/write here)
START_CFG_FILE  = Path(os.path.expanduser("~/.config/nyxus-start/config.json"))
NOTIF_CFG_DIR   = Path(os.path.expanduser("~/.config/nyxus-notifications"))
NOTIF_STATE     = NOTIF_CFG_DIR / "state.json"
NOTIF_REMINDERS = NOTIF_CFG_DIR / "reminders.json"

# Build / version metadata surfaced in the About tab.
NYXUS_VERSION = "2026.05.01"
NYXUS_KEY     = "NYX-J5W-2026-SIERENGOWSKI-LOCKED"
NYXUS_AUTHOR  = "Joseph A. Sierengowski"


# ────────────────────────────────────────────────────── load / save
def _ensure_dir() -> None:
    CFG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, Any]:
    _ensure_dir()
    if not CFG_PATH.exists():
        save_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with CFG_PATH.open() as f:
            cfg = json.load(f)
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULT_CONFIG)
    # Merge in any missing keys (forward-compat with new releases)
    out = dict(DEFAULT_CONFIG)
    out.update(cfg)
    # Ensure every default source has an entry
    src_map = dict(DEFAULT_CONFIG["sources"])
    src_map.update(out.get("sources", {}))
    out["sources"] = src_map
    return out


def save_config(cfg: Dict[str, Any]) -> None:
    _ensure_dir()
    tmp = CFG_PATH.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(cfg, f, indent=2)
    tmp.replace(CFG_PATH)


def all_sources(cfg: Dict[str, Any]) -> List[Dict[str, str]]:
    """Return enabled sources (built-in + custom)."""
    out: List[Dict[str, str]] = []
    for s in DEFAULT_SOURCES:
        if cfg.get("sources", {}).get(s["id"], True):
            out.append(s)
    for c in cfg.get("custom_sources", []):
        # custom sources default to enabled
        out.append({
            "id":    c.get("id") or f"custom_{abs(hash(c.get('url', ''))) % 999999}",
            "label": c.get("label", c.get("url", "Custom")),
            "url":   c.get("url", ""),
            "cat":   c.get("cat", "custom"),
        })
    return out


def clear_cache() -> int:
    """Wipe cache dir, return number of bytes freed."""
    total = 0
    if CACHE_DIR.exists():
        for p in CACHE_DIR.rglob("*"):
            if p.is_file():
                try:
                    total += p.stat().st_size
                except OSError:
                    pass
        try:
            shutil.rmtree(CACHE_DIR)
        except OSError:
            pass
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / "thumbs").mkdir(parents=True, exist_ok=True)
    (CACHE_DIR / "favicons").mkdir(parents=True, exist_ok=True)
    return total


# ────────────────────────────────────────────────────── settings dialog (GTK4)
class SettingsWindow(Gtk.Window):
    """Standalone settings window — opened from the Panel header pencil icon."""

    def __init__(self, on_saved=None):
        super().__init__(title="NYXUS Panel · Settings")
        self.set_default_size(640, 720)
        self._cfg = load_config()
        self._on_saved = on_saved
        self.add_css_class("nyxus-settings")

        # Bigger window — premium feel needs room to breathe.
        self.set_default_size(960, 720)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.add_css_class("nyxus-settings-outer")
        self.set_child(outer)

        # ── HERO HEADER ─────────────────────────────────────────────
        hero = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14,
                       margin_top=18, margin_bottom=14, margin_start=22, margin_end=22)
        hero.add_css_class("nyxus-hero")
        glyph = Gtk.Label(label="\uf013")            # cog
        glyph.add_css_class("nyxus-hero-glyph")
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        col.set_hexpand(True)
        title = Gtk.Label(label="NYXUS Settings", xalign=0)
        title.add_css_class("nyxus-hero-title")
        sub   = Gtk.Label(
            label="Tune your hand-drawn desktop ecosystem", xalign=0)
        sub.add_css_class("nyxus-hero-sub")
        col.append(title); col.append(sub)
        ver = Gtk.Label(label=f"v{NYXUS_VERSION}", xalign=1)
        ver.add_css_class("nyxus-hero-ver")
        hero.append(glyph); hero.append(col); hero.append(ver)
        outer.append(hero)

        # ── BODY: sidebar nav  +  content stack ─────────────────────
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        body.set_vexpand(True); body.set_hexpand(True)
        outer.append(body)

        # Sidebar
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4,
                          margin_top=14, margin_bottom=14, margin_start=14, margin_end=8)
        sidebar.add_css_class("nyxus-sidebar")
        sidebar.set_size_request(220, -1)
        body.append(sidebar)

        # Content area (Stack — switched by sidebar buttons)
        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(160)
        self._stack.set_vexpand(True); self._stack.set_hexpand(True)
        self._stack.set_margin_top(14); self._stack.set_margin_bottom(8)
        self._stack.set_margin_start(8); self._stack.set_margin_end(14)
        body.append(self._stack)

        # Page registry: (name, glyph, builder)  — name doubles as Stack key
        pages = [
            ("Appearance",     "\uf53f", self._tab_appearance),     # palette
            ("Profile",        "\uf007", self._tab_profile),        # user
            ("Notifications",  "\uf0f3", self._tab_notifications),  # bell
            ("Panel",          "\uf0a1", self._tab_general),        # bullhorn
            ("News Sources",   "\uf09e", self._tab_sources),        # rss
            ("Filters",        "\uf0b0", self._tab_filters),        # filter
            ("Browser",        "\uf0ac", self._tab_browser),        # globe
            ("Cache",          "\uf1c0", self._tab_cache),          # database
            ("About",          "\uf05a", self._tab_about),          # info-circle
        ]
        self._side_buttons: List[Gtk.ToggleButton] = []
        for name, glyph, builder in pages:
            self._stack.add_named(builder(), name)
            btn = self._mk_sidebar_btn(name, glyph)
            sidebar.append(btn)
            self._side_buttons.append(btn)
        # Push About down to the bottom of the sidebar
        if len(self._side_buttons) >= 2:
            spacer = Gtk.Label(label=""); spacer.set_vexpand(True)
            sidebar.insert_child_after(spacer, self._side_buttons[-2])
        # Activate the first page (stack name first, then button — order
        # matters because the toggle handler reads from the buttons array).
        self._stack.set_visible_child_name(pages[0][0])
        self._side_buttons[0].set_active(True)

        # ── FOOTER ─────────────────────────────────────────────────
        ft = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10,
                     margin_top=8, margin_bottom=18, margin_start=22, margin_end=22)
        ft.add_css_class("nyxus-footer-bar")
        cw = Gtk.Label(label=f"\uf1f9  © 2026 {NYXUS_AUTHOR}", xalign=0)
        cw.add_css_class("nyxus-footer-credit"); cw.set_hexpand(True)
        cancel = Gtk.Button(label="Cancel"); cancel.add_css_class("nyxus-btn-ghost")
        save   = Gtk.Button(label="\uf0c7  Save"); save.add_css_class("nyxus-btn-primary")
        ft.append(cw); ft.append(cancel); ft.append(save)
        outer.append(ft)

        cancel.connect("clicked", lambda *_: self.close())
        save.connect("clicked",   self._on_save)

    # ── sidebar helpers ─────────────────────────────────────────────
    def _mk_sidebar_btn(self, name: str, glyph: str) -> Gtk.ToggleButton:
        btn = Gtk.ToggleButton()
        btn.add_css_class("nyxus-sidebar-btn")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        gl = Gtk.Label(label=glyph); gl.add_css_class("nyxus-sidebar-glyph")
        gl.set_size_request(22, -1); gl.set_xalign(0.5)
        lb = Gtk.Label(label=name, xalign=0); lb.add_css_class("nyxus-sidebar-label")
        lb.set_hexpand(True)
        row.append(gl); row.append(lb)
        btn.set_child(row)
        btn.connect("toggled", lambda b: self._select_page(b, name))
        return btn

    def _select_page(self, sender: Gtk.ToggleButton, name: str) -> None:
        # Guard against the recursive toggling that radio-button-style sidebars
        # are prone to: when we deselect a sibling below, that sibling's own
        # `toggled` handler will fire — we need to ignore those re-entries.
        if getattr(self, "_in_select_page", False):
            return
        self._in_select_page = True
        try:
            if not sender.get_active():
                # User clicked the already-active button — keep it active
                # (a settings sidebar must always have one selection).
                sender.set_active(True)
                return
            for b in self._side_buttons:
                if b is not sender and b.get_active():
                    b.set_active(False)
            self._stack.set_visible_child_name(name)
        finally:
            self._in_select_page = False

    # ───────────── tab builders ─────────────
    def _tab_appearance(self) -> Gtk.Widget:
        box = self._tab_box()
        intro = Gtk.Label(label="Tune the NYXUS hand-drawn look across every app.")
        intro.set_xalign(0); intro.add_css_class("nyxus-help"); intro.set_wrap(True)
        box.append(intro)

        hdr = Gtk.Label(label="PALETTE"); hdr.set_xalign(0); hdr.add_css_class("nyxus-cat")
        box.append(hdr)
        self.w_palette = self._combo_row(
            box, "Theme palette",
            ["godsapp", "neon"],
            self._cfg.get("theme_palette", "godsapp"),
        )

        hdr2 = Gtk.Label(label="GLOW & DEPTH"); hdr2.set_xalign(0); hdr2.add_css_class("nyxus-cat")
        box.append(hdr2)
        self.w_glow = self._slider_row(
            box, "Neon glow intensity",
            0, 100, int(self._cfg.get("theme_glow_intensity", 35)), unit=" %",
        )
        self.w_bg = self._slider_row(
            box, "Background graffiti opacity",
            0, 100, int(self._cfg.get("theme_bg_opacity", 100)), unit=" %",
        )

        hdr3 = Gtk.Label(label="TYPOGRAPHY"); hdr3.set_xalign(0); hdr3.add_css_class("nyxus-cat")
        box.append(hdr3)
        self.w_font_scale = self._slider_row(
            box, "Font size",
            80, 140, int(self._cfg.get("theme_font_scale", 100)), unit=" %",
        )

        note = Gtk.Label(label=(
            "Some changes only apply to NYXUS apps launched after Save. "
            "Restart the panel via the header refresh icon to see live updates."
        ))
        note.set_xalign(0); note.set_wrap(True); note.add_css_class("nyxus-help")
        note.set_margin_top(14)
        box.append(note)
        return box

    def _tab_profile(self) -> Gtk.Widget:
        box = self._tab_box()
        intro = Gtk.Label(label="Your name and avatar appear in the NYXUS Start menu header.")
        intro.set_xalign(0); intro.add_css_class("nyxus-help"); intro.set_wrap(True)
        box.append(intro)

        # Pull current profile from the Start config (matches keys in
        # nyxus-start: user_name / user_subtitle / user_avatar).
        prof = self._load_start_profile()

        hdr = Gtk.Label(label="IDENTITY"); hdr.set_xalign(0); hdr.add_css_class("nyxus-cat")
        box.append(hdr)

        nrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_top=6)
        nlbl = Gtk.Label(label="Display name"); nlbl.set_xalign(0); nlbl.set_size_request(140, -1); nlbl.add_css_class("nyxus-row-title")
        self.w_user_name = Gtk.Entry()
        self.w_user_name.set_text(prof.get("user_name", "Joey"))
        self.w_user_name.set_hexpand(True)
        nrow.append(nlbl); nrow.append(self.w_user_name)
        box.append(nrow)

        srow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_top=6)
        slbl = Gtk.Label(label="Subtitle"); slbl.set_xalign(0); slbl.set_size_request(140, -1); slbl.add_css_class("nyxus-row-title")
        self.w_user_sub = Gtk.Entry()
        self.w_user_sub.set_text(prof.get("user_subtitle", "operator"))
        self.w_user_sub.set_hexpand(True)
        srow.append(slbl); srow.append(self.w_user_sub)
        box.append(srow)

        hdr2 = Gtk.Label(label="AVATAR"); hdr2.set_xalign(0); hdr2.add_css_class("nyxus-cat")
        box.append(hdr2)

        arow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_top=6)
        self.w_user_avatar = Gtk.Entry()
        self.w_user_avatar.set_text(prof.get("user_avatar", ""))
        self.w_user_avatar.set_placeholder_text("~/Pictures/me.png")
        self.w_user_avatar.set_hexpand(True)
        pickbtn = Gtk.Button(label="Browse…"); pickbtn.add_css_class("nyxus-btn-ghost")
        pickbtn.connect("clicked", self._pick_avatar)
        arow.append(self.w_user_avatar); arow.append(pickbtn)
        box.append(arow)

        ahelp = Gtk.Label(label=(
            "PNG / JPG. Square images look best (Start will circle-crop). "
            "On Save, the chosen file is copied into ~/.config/nyxus-start/avatars/."
        ))
        ahelp.set_xalign(0); ahelp.set_wrap(True); ahelp.add_css_class("nyxus-help")
        box.append(ahelp)
        return box

    def _store_avatar_for_start(self, src_path: str) -> str:
        """Mirror nyxus-start's store_avatar(): copy chosen file into the
        Start app's avatars directory and return the stored path. Returns
        empty string on failure or empty input."""
        src_path = (src_path or "").strip()
        if not src_path:
            return ""
        try:
            src = Path(os.path.expanduser(src_path))
            if not src.is_file():
                return ""
            avatar_dir = START_CFG_FILE.parent / "avatars"
            avatar_dir.mkdir(parents=True, exist_ok=True)
            ext = src.suffix.lower() or ".png"
            import time as _t
            dst = avatar_dir / f"avatar-{int(_t.time())}{ext}"
            shutil.copy2(src, dst)
            return str(dst)
        except OSError:
            return ""

    def _tab_notifications(self) -> Gtk.Widget:
        box = self._tab_box()
        intro = Gtk.Label(label="Quiet hours, sound, and reminders for the NYXUS Notification Center.")
        intro.set_xalign(0); intro.add_css_class("nyxus-help"); intro.set_wrap(True)
        box.append(intro)

        nstate = self._load_notif_state()

        hdr = Gtk.Label(label="DO NOT DISTURB"); hdr.set_xalign(0); hdr.add_css_class("nyxus-cat")
        box.append(hdr)
        self.w_dnd = self._switch_row(
            box, "Do Not Disturb",
            "Silences all NYXUS notifications and dims the notification dot.",
            bool(nstate.get("dnd", False)),
        )
        self.w_sound = self._switch_row(
            box, "Notification sound",
            "Play a soft chime when a new notification arrives.",
            bool(nstate.get("sound", True)),
        )

        hdr2 = Gtk.Label(label="REMINDERS"); hdr2.set_xalign(0); hdr2.add_css_class("nyxus-cat")
        box.append(hdr2)
        rems = self._load_reminders()
        rcount = Gtk.Label(label=f"You have {len(rems)} active reminder{'s' if len(rems) != 1 else ''}.")
        rcount.set_xalign(0); rcount.add_css_class("nyxus-help")
        box.append(rcount)

        clear_btn = Gtk.Button(label="Clear all reminders")
        clear_btn.add_css_class("nyxus-btn-danger")
        clear_btn.set_halign(Gtk.Align.START); clear_btn.set_margin_top(8)
        def _do_clear(_):
            self._save_reminders([])
            rcount.set_text("Cleared. You have 0 active reminders.")
        clear_btn.connect("clicked", _do_clear)
        box.append(clear_btn)
        return box

    def _tab_about(self) -> Gtk.Widget:
        box = self._tab_box()

        title = Gtk.Label(label="NYXUS"); title.set_xalign(0); title.add_css_class("nyxus-title")
        box.append(title)
        sub = Gtk.Label(label="Hand-drawn desktop ecosystem for Arch Linux.")
        sub.set_xalign(0); sub.set_wrap(True); sub.add_css_class("nyxus-subtitle")
        box.append(sub)

        sep = Gtk.Separator(); sep.set_margin_top(12); sep.set_margin_bottom(8); box.append(sep)

        hdr = Gtk.Label(label="BUILD"); hdr.set_xalign(0); hdr.add_css_class("nyxus-cat")
        box.append(hdr)
        for label, value in (
            ("Version", NYXUS_VERSION),
            ("Author",  NYXUS_AUTHOR),
            ("License key", NYXUS_KEY),
        ):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_top=4)
            l = Gtk.Label(label=label); l.set_xalign(0); l.set_size_request(120, -1); l.add_css_class("nyxus-row-title")
            v = Gtk.Label(label=value); v.set_xalign(0); v.set_hexpand(True); v.set_selectable(True); v.add_css_class("nyxus-mono")
            row.append(l); row.append(v); box.append(row)

        hdr2 = Gtk.Label(label="MODULES"); hdr2.set_xalign(0); hdr2.add_css_class("nyxus-cat")
        box.append(hdr2)
        modules = [
            ("Start",         "nyxus-start"),
            ("Panel",         "nyxus-panel"),
            ("Notifications", "nyxus-notifications"),
            ("App Store",     "nyxus-store"),
            ("Settings",      "nyxus-settings"),
        ]
        for name, binname in modules:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_top=2)
            l = Gtk.Label(label=name); l.set_xalign(0); l.set_size_request(120, -1); l.add_css_class("nyxus-row-title")
            v = Gtk.Label(label=binname); v.set_xalign(0); v.set_hexpand(True); v.set_selectable(True); v.add_css_class("nyxus-mono")
            row.append(l); row.append(v); box.append(row)

        sep2 = Gtk.Separator(); sep2.set_margin_top(14); sep2.set_margin_bottom(8); box.append(sep2)
        cw = Gtk.Label(label=f"© 2026 {NYXUS_AUTHOR} — {NYXUS_KEY}")
        cw.set_xalign(0); cw.set_wrap(True); cw.add_css_class("nyxus-help")
        box.append(cw)
        return box

    # ───────────── cross-app config helpers ─────────────
    def _load_start_profile(self) -> Dict[str, Any]:
        try:
            with START_CFG_FILE.open() as f:
                return json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_start_profile(self, patch: Dict[str, Any]) -> None:
        try:
            START_CFG_FILE.parent.mkdir(parents=True, exist_ok=True)
            cur: Dict[str, Any] = {}
            if START_CFG_FILE.exists():
                try:
                    with START_CFG_FILE.open() as f:
                        cur = json.load(f) or {}
                except (OSError, json.JSONDecodeError):
                    cur = {}
            cur.update(patch)
            tmp = START_CFG_FILE.with_suffix(".json.tmp")
            with tmp.open("w") as f:
                json.dump(cur, f, indent=2)
            tmp.replace(START_CFG_FILE)
        except OSError:
            pass

    def _load_notif_state(self) -> Dict[str, Any]:
        try:
            with NOTIF_STATE.open() as f:
                return json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _save_notif_state(self, patch: Dict[str, Any]) -> None:
        try:
            NOTIF_CFG_DIR.mkdir(parents=True, exist_ok=True)
            cur = self._load_notif_state()
            cur.update(patch)
            tmp = NOTIF_STATE.with_suffix(".json.tmp")
            with tmp.open("w") as f:
                json.dump(cur, f, indent=2)
            tmp.replace(NOTIF_STATE)
        except OSError:
            pass

    def _load_reminders(self) -> List[Dict[str, Any]]:
        try:
            with NOTIF_REMINDERS.open() as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
        except (OSError, json.JSONDecodeError):
            return []

    def _save_reminders(self, items: List[Dict[str, Any]]) -> None:
        try:
            NOTIF_CFG_DIR.mkdir(parents=True, exist_ok=True)
            tmp = NOTIF_REMINDERS.with_suffix(".json.tmp")
            with tmp.open("w") as f:
                json.dump(items, f, indent=2)
            tmp.replace(NOTIF_REMINDERS)
        except OSError:
            pass

    def _pick_avatar(self, _btn) -> None:
        dialog = Gtk.FileChooserDialog(
            title="Choose avatar image",
            transient_for=self,
            action=Gtk.FileChooserAction.OPEN,
        )
        dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL,
                           "Select", Gtk.ResponseType.ACCEPT)
        flt = Gtk.FileFilter(); flt.set_name("Images")
        for ext in ("png", "jpg", "jpeg", "webp"):
            flt.add_pattern(f"*.{ext}")
        dialog.add_filter(flt)
        def _resp(d, response):
            if response == Gtk.ResponseType.ACCEPT:
                f = d.get_file()
                if f is not None:
                    self.w_user_avatar.set_text(f.get_path() or "")
            d.destroy()
        dialog.connect("response", _resp)
        dialog.show()

    def _tab_general(self) -> Gtk.Widget:
        box = self._tab_box()

        self.w_hover  = self._switch_row(box, "Open on hover",
                                         "Hover the taskbar button to open the panel automatically",
                                         self._cfg["open_on_hover"])
        self.w_hover_ms = self._slider_row(box, "Hover delay",
                                           300, 1000, self._cfg["hover_delay_ms"], unit=" ms")
        self.w_click  = self._switch_row(box, "Open on click",
                                         "Click the taskbar button to toggle the panel",
                                         self._cfg["open_on_click"])
        self.w_anim   = self._switch_row(box, "Reduce animations",
                                         "Skip the slide-up / fade animations",
                                         self._cfg["reduce_animations"])

        self.w_position = self._combo_row(box, "Panel position",
                                          ["above-taskbar", "side"],
                                          self._cfg["panel_position"])
        self.w_refresh = self._combo_row(box, "Auto refresh interval",
                                         ["15", "30", "60"],
                                         str(self._cfg["refresh_interval_min"]),
                                         suffix=" min")
        self.w_max = self._slider_row(box, "Max articles",
                                      10, 80, self._cfg["max_articles"])
        self.w_notify = self._switch_row(box, "Breaking security notifications",
                                         "Send a desktop notification for new high-severity CVEs",
                                         self._cfg["notify_breaking_security"])
        self.w_startup = self._switch_row(box, "Load content on boot",
                                          "Start fetching feeds on login (otherwise: wait until panel opens)",
                                          self._cfg["load_on_startup"])
        return box

    def _tab_sources(self) -> Gtk.Widget:
        box = self._tab_box()
        intro = Gtk.Label(label="Toggle each built-in source on or off.")
        intro.set_xalign(0); intro.add_css_class("nyxus-help")
        box.append(intro)

        self.src_switches: Dict[str, Gtk.Switch] = {}
        # Group by category
        categories = [("linux", "Linux & Distros"), ("security", "Security & CVEs"),
                      ("hardware", "Hardware & GPUs"), ("dev", "Developer")]
        for cat_id, cat_label in categories:
            hdr = Gtk.Label(label=cat_label.upper()); hdr.set_xalign(0)
            hdr.add_css_class("nyxus-cat")
            box.append(hdr)
            for s in DEFAULT_SOURCES:
                if s["cat"] != cat_id:
                    continue
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_top=4)
                lbl = Gtk.Label(label=s["label"]); lbl.set_xalign(0); lbl.set_hexpand(True)
                sw  = Gtk.Switch()
                sw.set_active(self._cfg["sources"].get(s["id"], True))
                sw.set_valign(Gtk.Align.CENTER)
                self.src_switches[s["id"]] = sw
                row.append(lbl); row.append(sw)
                box.append(row)

        # ── custom RSS feeds ──
        sep = Gtk.Separator(); sep.set_margin_top(12); sep.set_margin_bottom(8); box.append(sep)
        chdr = Gtk.Label(label="CUSTOM RSS FEEDS"); chdr.set_xalign(0); chdr.add_css_class("nyxus-cat")
        box.append(chdr)

        self.custom_list_box = Gtk.ListBox()
        self.custom_list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.custom_list_box.add_css_class("nyxus-listbox")
        box.append(self.custom_list_box)
        for c in self._cfg.get("custom_sources", []):
            self._append_custom_row(c)

        # add row
        addrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_top=10)
        self.add_label = Gtk.Entry(); self.add_label.set_placeholder_text("Label  (e.g. My Blog)")
        self.add_url   = Gtk.Entry(); self.add_url.set_placeholder_text("https://example.com/feed.xml")
        self.add_url.set_hexpand(True)
        addbtn = Gtk.Button(label="Add"); addbtn.add_css_class("nyxus-btn-primary")
        addbtn.connect("clicked", self._on_add_custom)
        addrow.append(self.add_label); addrow.append(self.add_url); addrow.append(addbtn)
        box.append(addrow)
        return box

    def _tab_filters(self) -> Gtk.Widget:
        box = self._tab_box()
        intro = Gtk.Label(label=(
            "Allow-list: only show articles whose title or summary contains any of these words.\n"
            "Block-list: never show articles containing any of these words.\n"
            "One word per line. Case-insensitive."
        ))
        intro.set_xalign(0); intro.add_css_class("nyxus-help"); intro.set_wrap(True)
        box.append(intro)

        # allow list
        a_lbl = Gtk.Label(label="ALLOW (one per line)"); a_lbl.set_xalign(0); a_lbl.add_css_class("nyxus-cat")
        box.append(a_lbl)
        sw_a = Gtk.ScrolledWindow(); sw_a.set_min_content_height(120)
        self.tv_allow = Gtk.TextView(); self.tv_allow.add_css_class("nyxus-textarea")
        self.tv_allow.get_buffer().set_text("\n".join(self._cfg.get("keyword_allow", [])))
        sw_a.set_child(self.tv_allow)
        box.append(sw_a)

        # block list
        b_lbl = Gtk.Label(label="BLOCK (one per line)"); b_lbl.set_xalign(0); b_lbl.add_css_class("nyxus-cat")
        box.append(b_lbl)
        sw_b = Gtk.ScrolledWindow(); sw_b.set_min_content_height(120)
        self.tv_block = Gtk.TextView(); self.tv_block.add_css_class("nyxus-textarea")
        self.tv_block.get_buffer().set_text("\n".join(self._cfg.get("keyword_block", [])))
        sw_b.set_child(self.tv_block)
        box.append(sw_b)
        return box

    def _tab_browser(self) -> Gtk.Widget:
        box = self._tab_box()
        intro = Gtk.Label(label="Where to open article links when you click a news card.")
        intro.set_xalign(0); intro.add_css_class("nyxus-help")
        box.append(intro)

        # Detect installed browsers
        candidates = ["chromium", "google-chrome", "firefox", "brave", "vivaldi", "qutebrowser", "xdg-open"]
        present = [c for c in candidates if shutil.which(c)]
        if not present:
            present = ["xdg-open"]
        if self._cfg["browser"] not in present:
            present = list(dict.fromkeys([self._cfg["browser"], *present]))

        self.w_browser = self._combo_row(box, "Browser", present, self._cfg["browser"])
        self.w_private = self._switch_row(box, "Private window",
                                          "Open links in a private/incognito window",
                                          self._cfg["browser_private"])
        self.w_reader  = self._switch_row(box, "Reader mode",
                                          "Open links with browser reader/distraction-free mode",
                                          self._cfg["browser_reader_mode"])
        return box

    def _tab_cache(self) -> Gtk.Widget:
        box = self._tab_box()
        size_lbl = Gtk.Label(label=f"Cache location: {CACHE_DIR}")
        size_lbl.set_xalign(0); size_lbl.set_wrap(True); size_lbl.add_css_class("nyxus-mono")
        box.append(size_lbl)

        total = sum(p.stat().st_size for p in CACHE_DIR.rglob("*") if p.is_file())
        usage = Gtk.Label(label=f"Disk usage: {total/1024:.1f} KiB")
        usage.set_xalign(0); usage.add_css_class("nyxus-help")
        box.append(usage)

        clear = Gtk.Button(label="Clear cache")
        clear.add_css_class("nyxus-btn-danger")
        clear.set_halign(Gtk.Align.START); clear.set_margin_top(10)
        def _do_clear(_):
            n = clear_cache()
            usage.set_text(f"Cleared {n/1024:.1f} KiB.")
        clear.connect("clicked", _do_clear)
        box.append(clear)
        return box

    # ───────────── helpers ─────────────
    def _tab_box(self) -> Gtk.Widget:
        """Return a ScrolledWindow that *acts* like a Box for `.append()`.

        Notebook pages must be the ScrolledWindow itself (not a wrapped Box)
        for the page to actually scroll, so we expose the inner Box's
        ``append`` method on the wrapper for ergonomic use by callers.
        """
        inner = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=8,
            margin_top=16, margin_bottom=16, margin_start=16, margin_end=16,
        )
        sw = Gtk.ScrolledWindow()
        sw.set_child(inner)
        sw.set_vexpand(True); sw.set_hexpand(True)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        # Forward .append to the inner box so existing callers keep working.
        sw.append = inner.append  # type: ignore[attr-defined]
        return sw

    def _switch_row(self, parent, label, help_text, value: bool) -> Gtk.Switch:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_top=8)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); col.set_hexpand(True)
        l = Gtk.Label(label=label); l.set_xalign(0); l.add_css_class("nyxus-row-title")
        h = Gtk.Label(label=help_text); h.set_xalign(0); h.set_wrap(True); h.add_css_class("nyxus-help")
        col.append(l); col.append(h)
        sw = Gtk.Switch(); sw.set_active(bool(value)); sw.set_valign(Gtk.Align.CENTER)
        row.append(col); row.append(sw)
        parent.append(row)
        return sw

    def _slider_row(self, parent, label, lo, hi, value, unit="") -> Gtk.Scale:
        row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, margin_top=10)
        l = Gtk.Label(label=label); l.set_xalign(0); l.add_css_class("nyxus-row-title")
        sl = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, lo, hi, 1)
        sl.set_value(value); sl.set_draw_value(True); sl.set_value_pos(Gtk.PositionType.RIGHT)
        if unit:
            sl.set_format_value_func(lambda _s, v: f"{int(v)}{unit}")
        row.append(l); row.append(sl)
        parent.append(row)
        return sl

    def _combo_row(self, parent, label, options, value, suffix="") -> Gtk.DropDown:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10, margin_top=10)
        l = Gtk.Label(label=label); l.set_xalign(0); l.set_hexpand(True); l.add_css_class("nyxus-row-title")
        sl = Gtk.StringList()
        for o in options:
            sl.append(f"{o}{suffix}")
        dd = Gtk.DropDown(model=sl)
        try:
            dd.set_selected(options.index(value))
        except ValueError:
            dd.set_selected(0)
        dd._options = options  # type: ignore[attr-defined]
        row.append(l); row.append(dd)
        parent.append(row)
        return dd

    def _append_custom_row(self, c: Dict[str, str]) -> None:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, margin_top=4, margin_bottom=4, margin_start=6, margin_end=6)
        l = Gtk.Label(label=f"{c.get('label','(no label)')} — {c.get('url','')}")
        l.set_xalign(0); l.set_hexpand(True); l.set_ellipsize(Pango.EllipsizeMode.END)
        rm = Gtk.Button(label="Remove"); rm.add_css_class("nyxus-btn-ghost")
        def _remove(_):
            self._cfg["custom_sources"] = [
                x for x in self._cfg.get("custom_sources", [])
                if x.get("url") != c.get("url")
            ]
            parent_lb = row.get_parent()
            if parent_lb is not None:
                parent_lb.remove(row.get_parent())
        rm.connect("clicked", _remove)
        row.append(l); row.append(rm)
        self.custom_list_box.append(row)

    def _on_add_custom(self, _btn) -> None:
        url = self.add_url.get_text().strip()
        lbl = self.add_label.get_text().strip() or url
        if not url:
            return
        c = {"label": lbl, "url": url, "cat": "custom"}
        self._cfg.setdefault("custom_sources", []).append(c)
        self._append_custom_row(c)
        self.add_label.set_text(""); self.add_url.set_text("")

    # ───────────── save ─────────────
    def _on_save(self, _btn) -> None:
        self._cfg["open_on_hover"]            = self.w_hover.get_active()
        self._cfg["hover_delay_ms"]           = int(self.w_hover_ms.get_value())
        self._cfg["open_on_click"]            = self.w_click.get_active()
        self._cfg["reduce_animations"]        = self.w_anim.get_active()
        self._cfg["panel_position"]           = self.w_position._options[self.w_position.get_selected()]  # type: ignore[attr-defined]
        self._cfg["refresh_interval_min"]     = int(self.w_refresh._options[self.w_refresh.get_selected()])  # type: ignore[attr-defined]
        self._cfg["max_articles"]             = int(self.w_max.get_value())
        self._cfg["notify_breaking_security"] = self.w_notify.get_active()
        self._cfg["load_on_startup"]          = self.w_startup.get_active()
        self._cfg["browser"]                  = self.w_browser._options[self.w_browser.get_selected()]  # type: ignore[attr-defined]
        self._cfg["browser_private"]          = self.w_private.get_active()
        self._cfg["browser_reader_mode"]      = self.w_reader.get_active()
        # sources
        for sid, sw in self.src_switches.items():
            self._cfg["sources"][sid] = sw.get_active()
        # filters
        ab = self.tv_allow.get_buffer()
        bb = self.tv_block.get_buffer()
        self._cfg["keyword_allow"] = [w.strip() for w in ab.get_text(ab.get_start_iter(), ab.get_end_iter(), True).splitlines() if w.strip()]
        self._cfg["keyword_block"] = [w.strip() for w in bb.get_text(bb.get_start_iter(), bb.get_end_iter(), True).splitlines() if w.strip()]
        # Appearance
        self._cfg["theme_palette"]        = self.w_palette._options[self.w_palette.get_selected()]  # type: ignore[attr-defined]
        self._cfg["theme_glow_intensity"] = int(self.w_glow.get_value())
        self._cfg["theme_bg_opacity"]     = int(self.w_bg.get_value())
        self._cfg["theme_font_scale"]     = int(self.w_font_scale.get_value())
        save_config(self._cfg)
        # Cross-app: profile (writes to nyxus-start config). Use the
        # exact keys nyxus-start expects: user_name / user_subtitle /
        # user_avatar. If the user picked a new avatar path that isn't
        # already inside ~/.config/nyxus-start/avatars/, mirror Start's
        # store_avatar() copy-in so the file survives if the user moves
        # or deletes the source later.
        avatar_in = self.w_user_avatar.get_text().strip()
        cur_prof  = self._load_start_profile()
        cur_av    = cur_prof.get("user_avatar", "")
        if avatar_in and avatar_in != cur_av:
            avatars_dir = str(START_CFG_FILE.parent / "avatars")
            if not avatar_in.startswith(avatars_dir):
                stored = self._store_avatar_for_start(avatar_in)
                if stored:
                    avatar_in = stored
        self._save_start_profile({
            "user_name":     self.w_user_name.get_text().strip() or "Joey",
            "user_subtitle": self.w_user_sub.get_text().strip()  or "operator",
            "user_avatar":   avatar_in,
        })
        # Cross-app: notifications state
        self._save_notif_state({
            "dnd":   self.w_dnd.get_active(),
            "sound": self.w_sound.get_active(),
        })
        if callable(self._on_saved):
            try:
                self._on_saved(self._cfg)
            except Exception:
                pass
        self.close()


__all__ = ["DEFAULT_CONFIG", "DEFAULT_SOURCES", "CFG_DIR", "CFG_PATH", "CACHE_DIR",
           "load_config", "save_config", "all_sources", "clear_cache", "SettingsWindow"]
