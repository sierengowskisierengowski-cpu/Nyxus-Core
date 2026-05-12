#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────────────
#  NYXUS · Settings                                  rev 2026.05.12-r10
# ──────────────────────────────────────────────────────────────────────
#  System control center for NYXUS. GTK4 + libadwaita Python app.
#  AdwNavigationSplitView (sidebar + content), DARK MIRROR aesthetic,
#  real backend integrations only — never mock data, never blank panels.
#
#  Sections:
#    Tier 1 (fully built this rev):
#       Appearance · Network · Bluetooth · About
#    Tier 2 (honest in-progress placeholder, contract-compliant chrome):
#       Display · Sound · Power · Notifications · Date & Time ·
#       Keyboard · Mouse · Privacy · Apps · Storage · Updates ·
#       Accessibility · Users
#
#  Storage:  ~/.config/nyxus/settings.json
#  Logs:     /tmp/nyxus-settings.log
#  Polkit:   /usr/local/libexec/nyxus-settings-helper (added later)
#
#  Design contract refs:
#    §1  type system      §7  spacing scale     §13 audit table
#    §6  glyph policy     §8  semantic colour
#    §9  empty states     §12 viewport (1366×768)
# ──────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, List, Optional, Tuple

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")
from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk  # noqa: E402

# ── App identity ──────────────────────────────────────────────────────
APP_ID    = "io.nyxus.settings"
APP_NAME  = "NYXUS Settings"
APP_REV   = "rev 2026.05.12-r10"
WIN_W     = 1180
WIN_H     = 740   # fits inside 768 with EWW bar present (§12)

# ── Paths ─────────────────────────────────────────────────────────────
HOME      = Path.home()
CFG_DIR   = HOME / ".config" / "nyxus"
CFG_FILE  = CFG_DIR / "settings.json"
LOG_FILE  = Path("/tmp/nyxus-settings.log")
WALLS_SYS = Path("/usr/share/backgrounds/nyxus")
WALLS_USR = HOME / "Pictures" / "Wallpapers"
CFG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=str(LOG_FILE),
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("nyxus-settings")

# ──────────────────────────────────────────────────────────────────────
# §1 type system  ·  §6 glyph policy  ·  §8 semantic colour
# Single source of truth pulled from nyxus_palette when available.
# ──────────────────────────────────────────────────────────────────────
try:
    from nyxus_palette import (  # type: ignore
        WHITE_PURE, WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        INK_FADED, INK_BLACK, GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE, HAIRLINE_INK,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
    )
except Exception:
    WHITE_PURE     = "#ffffff"
    WHITE_OFF      = "#e8edf5"
    GREY_LIGHT     = "#c8ccd6"
    GREY_MID       = "#9aa0ad"
    GREY_TERTIARY  = "#6a6e78"
    INK_FADED      = "#0a0a0a"
    INK_BLACK      = "#000000"
    GLASS_DARK     = "#14141a"
    GLASS_DEEPER   = "#0a0a0e"
    GLASS_DEEPEST  = "#000000"
    HAIRLINE_WHITE = "rgba(255,255,255,0.10)"
    HAIRLINE_INK   = "rgba(0,0,0,0.45)"
    RADIUS_CARD    = 14
    RADIUS_PILL    = 12
    RADIUS_INPUT   = 10
    FONT_UI        = "Inter"
    FONT_MONO      = "JetBrains Mono"
    FONT_DISPLAY   = "Inter Display"

DANGER_RED = "#ff6464"  # §8 — RESERVED for destructive only

# Nerd-font glyphs (§6 — never emoji in chrome).
GLYPHS = {
    "appearance":    "\uf53f",   # nf-mdi-palette
    "network":       "\uf1eb",   # nf-fa-wifi
    "bluetooth":     "\uf293",   # nf-fa-bluetooth_b
    "display":       "\ue163",   # nf-mdi-monitor
    "sound":         "\uf028",   # nf-fa-volume_up
    "power":         "\uf0e7",   # nf-fa-bolt
    "notifications": "\uf0f3",   # nf-fa-bell
    "datetime":      "\uf017",   # nf-fa-clock_o
    "keyboard":      "\uf11c",   # nf-fa-keyboard_o
    "mouse":         "\uf245",   # nf-fa-mouse_pointer
    "privacy":       "\uf023",   # nf-fa-lock
    "apps":          "\uf17c",   # nf-fa-th
    "storage":       "\uf0a0",   # nf-fa-hdd_o
    "updates":       "\uf0ed",   # nf-fa-cloud_download
    "accessibility": "\uf29a",   # nf-fa-universal_access
    "users":         "\uf007",   # nf-fa-user
    "about":         "\uf05a",   # nf-fa-info_circle
    "search":        "\uf002",   # nf-fa-search
    "check":         "\uf00c",   # nf-fa-check
    "chevron":       "\uf054",   # nf-fa-chevron_right
    "warn":          "\uf071",   # nf-fa-warning
    "wip":           "\uf0ad",   # nf-fa-wrench
}


# ──────────────────────────────────────────────────────────────────────
# Subprocess helpers — every backend call goes through these so we can
# log, time-bound, and never block the GTK main loop.
# ──────────────────────────────────────────────────────────────────────
def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def sh(cmd, *, timeout: int = 4) -> Tuple[int, str, str]:
    """Synchronous shell call. Use sparingly (init only)."""
    try:
        if isinstance(cmd, str):
            r = subprocess.run(cmd, shell=True, capture_output=True,
                               text=True, timeout=timeout)
        else:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s"
    except FileNotFoundError as e:
        return 127, "", str(e)
    except Exception as e:
        log.warning("sh(%r): %s", cmd, e)
        return 1, "", str(e)


def sh_async(cmd, on_done: Optional[Callable[[Tuple[int, str, str]], None]] = None,
             *, timeout: int = 8) -> None:
    """Background shell call. Result delivered on the GTK main thread."""
    def worker():
        result = sh(cmd, timeout=timeout)
        if on_done:
            GLib.idle_add(on_done, result)
        return False
    import threading
    threading.Thread(target=worker, daemon=True).start()


def fire_and_forget(cmd: str) -> None:
    """Spawn a detached process; we don't care about exit code."""
    try:
        subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)
    except Exception as e:
        log.warning("fire_and_forget(%r): %s", cmd, e)


# ──────────────────────────────────────────────────────────────────────
# Persistence
# ──────────────────────────────────────────────────────────────────────
def load_prefs() -> dict:
    if CFG_FILE.exists():
        try:
            return json.loads(CFG_FILE.read_text())
        except Exception as e:
            log.warning("load_prefs: %s", e)
    return {}


def save_prefs(prefs: dict) -> None:
    try:
        CFG_FILE.write_text(json.dumps(prefs, indent=2))
    except Exception as e:
        log.warning("save_prefs: %s", e)


# ──────────────────────────────────────────────────────────────────────
# Section registry — single source of truth for sidebar order.
# Each entry: (key, title, glyph_key, builder_callable_name)
# Tier-1 sections build the real page; Tier-2 use honest_placeholder.
# ──────────────────────────────────────────────────────────────────────
@dataclass(frozen=True)
class SectionDef:
    key: str
    title: str
    subtitle: str       # one-line description shown beneath the title
    glyph: str
    keywords: str       # search index (comma-separated)
    tier: int           # 1 = fully built, 2 = honest placeholder

SECTIONS: Tuple[SectionDef, ...] = (
    SectionDef("appearance",    "Appearance",
               "Wallpaper, theme variant, font scale",
               "appearance",
               "wallpaper,background,theme,dark,font,scale,accent,style", 1),
    SectionDef("network",       "Network",
               "Wi-Fi, ethernet, VPN, DNS",
               "network",
               "wifi,wireless,ethernet,vpn,dns,internet,connection", 1),
    SectionDef("bluetooth",     "Bluetooth",
               "Devices, pairing, audio profile",
               "bluetooth",
               "bluetooth,bt,pair,headphones,speaker,audio,device", 1),
    SectionDef("display",       "Display",
               "Resolution, refresh, scale, brightness",
               "display",
               "display,monitor,resolution,refresh,scale,brightness,hidpi", 2),
    SectionDef("sound",         "Sound",
               "Output, input, per-app volume",
               "sound",
               "sound,audio,volume,microphone,mic,speaker,headphone", 2),
    SectionDef("power",         "Power",
               "Battery, profiles, sleep, lid behavior",
               "power",
               "power,battery,sleep,suspend,lid,profile,energy,charge", 2),
    SectionDef("notifications", "Notifications",
               "Do not disturb, history, per-app rules",
               "notifications",
               "notification,dnd,quiet,alert,toast,banner", 2),
    SectionDef("datetime",      "Date & Time",
               "Timezone, NTP, format",
               "datetime",
               "date,time,timezone,clock,ntp,12,24,format", 2),
    SectionDef("keyboard",      "Keyboard",
               "Layout, repeat rate, shortcuts",
               "keyboard",
               "keyboard,layout,xkb,repeat,shortcut,hotkey,bind", 2),
    SectionDef("mouse",         "Mouse & Touchpad",
               "Speed, accel, natural scroll, tap",
               "mouse",
               "mouse,touchpad,trackpad,pointer,scroll,tap,acceleration", 2),
    SectionDef("privacy",       "Privacy & Security",
               "Location, mic, camera, screen recording",
               "privacy",
               "privacy,security,permission,location,microphone,camera", 2),
    SectionDef("apps",          "Apps & Defaults",
               "Installed apps, default browser/terminal, autostart",
               "apps",
               "apps,application,default,browser,terminal,autostart,mime", 2),
    SectionDef("storage",       "Storage",
               "Disks, usage, SMART health, cleanup",
               "storage",
               "storage,disk,drive,usage,smart,smartctl,health,clean", 2),
    SectionDef("updates",       "Updates",
               "System packages and AUR",
               "updates",
               "update,upgrade,pacman,aur,package,version", 2),
    SectionDef("accessibility", "Accessibility",
               "Large text, reduce motion, sticky keys",
               "accessibility",
               "accessibility,a11y,zoom,contrast,motion,sticky,screen reader", 2),
    SectionDef("users",         "Users",
               "Account info, password, groups, shell",
               "users",
               "user,account,password,group,shell,passwd,profile", 2),
    SectionDef("about",         "About",
               "System info, kernel, hardware, version",
               "about",
               "about,version,kernel,hardware,cpu,gpu,ram,uptime,build", 1),
)
SECTIONS_BY_KEY = {s.key: s for s in SECTIONS}


# ──────────────────────────────────────────────────────────────────────
# DARK MIRROR stylesheet — libadwaita CSS overrides.
# Keep this small: we lean on Adw built-ins (preferences groups, action
# rows, switches, sliders) and only override colour + radius + glow.
# ──────────────────────────────────────────────────────────────────────
CSS = f"""
window, .nyx-bg {{
    background-color: {INK_BLACK};
    color: {WHITE_OFF};
    font-family: '{FONT_UI}', 'Inter', sans-serif;
}}

/* ── Sidebar ──────────────────────────────────────────────────────── */
.nyx-sidebar {{
    background-color: {GLASS_DEEPEST};
    border-right: 1px solid {HAIRLINE_WHITE};
    min-width: 280px;
}}
.nyx-sidebar-header {{
    padding: 14px 18px 10px;
    border-bottom: 1px solid {HAIRLINE_WHITE};
}}
.nyx-sidebar-title {{
    font-family: '{FONT_DISPLAY}', '{FONT_UI}', sans-serif;
    font-size: 18px;
    font-weight: 600;
    letter-spacing: 0.4px;
    color: {WHITE_PURE};
    text-shadow: 0 0 14px rgba(255,255,255,0.18);
}}
.nyx-sidebar-rev {{
    font-family: '{FONT_MONO}', monospace;
    font-size: 11px;
    color: {GREY_TERTIARY};
    letter-spacing: 0.4px;
}}
.nyx-search {{
    margin: 10px 14px;
    border-radius: {RADIUS_INPUT}px;
    background-color: {GLASS_DEEPER};
    border: 1px solid {HAIRLINE_WHITE};
    color: {WHITE_OFF};
    padding: 6px 10px;
}}
.nyx-search:focus-within {{
    border-color: {WHITE_OFF};
    box-shadow: 0 0 18px rgba(255,255,255,0.10);
}}
.nyx-section-row {{
    padding: 10px 14px;
    border-radius: {RADIUS_PILL}px;
    margin: 1px 8px;
    color: {GREY_LIGHT};
    transition: background-color 160ms ease, color 160ms ease;
}}
.nyx-section-row:hover {{
    background-color: {GLASS_DARK};
    color: {WHITE_OFF};
}}
.nyx-section-row.selected, .nyx-section-row:selected {{
    background-color: {GLASS_DARK};
    color: {WHITE_PURE};
    box-shadow: inset 2px 0 0 0 {WHITE_OFF},
                0 0 14px rgba(255,255,255,0.06);
}}
.nyx-section-glyph {{
    font-family: 'Symbols Nerd Font', 'Symbols Nerd Font Mono', monospace;
    font-size: 14px;
    color: {GREY_LIGHT};
    min-width: 18px;
}}
.nyx-section-row.selected .nyx-section-glyph,
.nyx-section-row:selected .nyx-section-glyph {{
    color: {WHITE_PURE};
}}

/* ── Content panel ────────────────────────────────────────────────── */
.nyx-content {{
    background-color: {INK_BLACK};
}}
.nyx-page-header {{
    padding: 22px 28px 12px;
    border-bottom: 1px solid {HAIRLINE_WHITE};
}}
.nyx-page-title {{
    font-family: '{FONT_DISPLAY}', '{FONT_UI}', sans-serif;
    font-size: 28px;
    font-weight: 600;
    letter-spacing: 0.3px;
    color: {WHITE_PURE};
    text-shadow: 0 0 16px rgba(255,255,255,0.16);
}}
.nyx-page-sub {{
    color: {GREY_MID};
    font-size: 13px;
    margin-top: 2px;
    letter-spacing: 0.2px;
}}

/* libadwaita primitive overrides */
preferencesgroup > box > label.heading {{
    color: {WHITE_OFF};
    font-weight: 600;
    letter-spacing: 0.3px;
}}
preferencesgroup > box > label.description {{
    color: {GREY_TERTIARY};
}}
row.action, row.entry, row.combo, row.switch, row.expander {{
    background-color: {GLASS_DEEPER};
    border: 1px solid {HAIRLINE_WHITE};
    border-radius: {RADIUS_CARD}px;
    margin-bottom: 1px;
}}
row.action:hover, row.entry:hover, row.combo:hover,
row.switch:hover, row.expander:hover {{
    background-color: {GLASS_DARK};
}}
row label.title {{ color: {WHITE_OFF}; }}
row label.subtitle {{ color: {GREY_TERTIARY}; font-size: 12px; }}

switch {{ background-color: {GLASS_DARK};
         border: 1px solid {HAIRLINE_WHITE}; }}
switch:checked {{ background-color: {WHITE_OFF};
                  border-color: {WHITE_PURE}; }}
switch slider {{ background-color: {GREY_LIGHT}; }}
switch:checked slider {{ background-color: {INK_BLACK}; }}

button {{
    background-color: {GLASS_DEEPER};
    border: 1px solid {HAIRLINE_WHITE};
    color: {WHITE_OFF};
    border-radius: {RADIUS_PILL}px;
    padding: 6px 14px;
    transition: background-color 160ms ease, border-color 160ms ease;
}}
button:hover {{
    background-color: {GLASS_DARK};
    border-color: {WHITE_OFF};
}}
button.suggested-action, button.nyx-primary {{
    background-color: {WHITE_OFF};
    color: {INK_BLACK};
    border-color: {WHITE_PURE};
    font-weight: 600;
}}
button.destructive-action, button.nyx-danger {{
    background-color: transparent;
    color: {DANGER_RED};
    border-color: {DANGER_RED};
}}
button.destructive-action:hover {{
    background-color: rgba(255,100,100,0.10);
}}

scale trough {{ background-color: {GLASS_DARK};
                border: 1px solid {HAIRLINE_WHITE}; }}
scale highlight {{ background-color: {WHITE_OFF}; }}
scale slider {{ background-color: {WHITE_PURE};
                border: 1px solid {WHITE_PURE};
                box-shadow: 0 0 8px rgba(255,255,255,0.30); }}

/* ── Status pill ─────────────────────────────────────────────────── */
.nyx-pill {{
    background-color: {GLASS_DEEPER};
    border: 1px solid {HAIRLINE_WHITE};
    border-radius: 999px;
    padding: 3px 10px;
    color: {GREY_LIGHT};
    font-family: '{FONT_MONO}', monospace;
    font-size: 11px;
}}
.nyx-pill.ok      {{ color: {WHITE_PURE}; border-color: {WHITE_OFF}; }}
.nyx-pill.warn    {{ color: {GREY_LIGHT}; border-color: {GREY_MID}; }}
.nyx-pill.danger  {{ color: {DANGER_RED}; border-color: {DANGER_RED}; }}

/* ── In-progress card (Tier-2 placeholder, §9 no blank panel) ────── */
.nyx-wip-card {{
    background-color: {GLASS_DEEPER};
    border: 1px solid {HAIRLINE_WHITE};
    border-radius: {RADIUS_CARD}px;
    padding: 28px;
    margin: 20px 28px;
}}
.nyx-wip-glyph {{
    font-family: 'Symbols Nerd Font', monospace;
    font-size: 32px;
    color: {GREY_LIGHT};
    margin-bottom: 12px;
}}
.nyx-wip-title {{
    font-family: '{FONT_DISPLAY}', '{FONT_UI}', sans-serif;
    font-size: 17px;
    font-weight: 600;
    color: {WHITE_OFF};
    margin-bottom: 6px;
}}
.nyx-wip-body {{
    color: {GREY_TERTIARY};
    font-size: 13px;
    line-height: 1.5;
}}

/* ── Wallpaper grid (Appearance) ─────────────────────────────────── */
.nyx-wall-tile {{
    border: 2px solid transparent;
    border-radius: {RADIUS_CARD}px;
    padding: 0;
    background-color: {GLASS_DEEPER};
    transition: border-color 160ms ease, box-shadow 160ms ease;
}}
.nyx-wall-tile:hover {{
    border-color: {GREY_LIGHT};
}}
.nyx-wall-tile.selected {{
    border-color: {WHITE_PURE};
    box-shadow: 0 0 18px rgba(255,255,255,0.18);
}}

/* ── Toast ───────────────────────────────────────────────────────── */
toast {{
    background-color: {GLASS_DEEPEST};
    color: {WHITE_OFF};
    border: 1px solid {HAIRLINE_WHITE};
    border-radius: {RADIUS_PILL}px;
}}
"""


def install_css() -> None:
    provider = Gtk.CssProvider()
    provider.load_from_data(CSS.encode("utf-8"))
    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(
            display, provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 100,
        )


# ──────────────────────────────────────────────────────────────────────
# Shared helpers
# ──────────────────────────────────────────────────────────────────────
def status_pill(label: str, kind: str = "ok") -> Gtk.Label:
    """Tiny status capsule used in titles and rows."""
    lbl = Gtk.Label(label=label)
    lbl.add_css_class("nyx-pill")
    if kind in ("ok", "warn", "danger"):
        lbl.add_css_class(kind)
    lbl.set_halign(Gtk.Align.START)
    return lbl


def wip_card(section_title: str, what_works: str, what_lands_next: str) -> Gtk.Box:
    """
    §9 mandate — never show a blank panel. Tier-2 sections render this
    honest in-progress card explaining current state and ETA.
    """
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
    box.add_css_class("nyx-wip-card")

    glyph = Gtk.Label(label=GLYPHS["wip"])
    glyph.add_css_class("nyx-wip-glyph")
    glyph.set_halign(Gtk.Align.START)
    box.append(glyph)

    title = Gtk.Label(label=f"{section_title} — under active development")
    title.add_css_class("nyx-wip-title")
    title.set_halign(Gtk.Align.START)
    title.set_wrap(True)
    box.append(title)

    body_text = (
        f"<b>What works today:</b>  {what_works}\n"
        f"<b>Landing in the next pass:</b>  {what_lands_next}\n\n"
        "This panel is intentionally honest. NYXUS never shows fake "
        "toggles or mocked data — every control either has a real "
        "backend wired up or is held back until it does."
    )
    body = Gtk.Label()
    body.add_css_class("nyx-wip-body")
    body.set_markup(body_text)
    body.set_halign(Gtk.Align.START)
    body.set_xalign(0.0)
    body.set_wrap(True)
    box.append(body)

    return box


# ──────────────────────────────────────────────────────────────────────
# Base section page — every section subclasses this.
# Adw.PreferencesPage gives us free vertical scroll + groups + responsive.
# ──────────────────────────────────────────────────────────────────────
class SectionPage(Adw.Bin):
    """Container = page header (title + subtitle) + content area."""
    KEY: str = ""

    def __init__(self, win: "SettingsWindow", section: SectionDef):
        super().__init__()
        self.win = win
        self.section = section
        self._refresh_source: Optional[int] = None

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.add_css_class("nyx-content")

        # Header
        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        header.add_css_class("nyx-page-header")

        title_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        title = Gtk.Label(label=section.title)
        title.add_css_class("nyx-page-title")
        title.set_halign(Gtk.Align.START)
        title_row.append(title)
        # Right-aligned status pill slot (subclasses can fill via header_pill)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        title_row.append(spacer)
        self.header_pill_slot = Gtk.Box(spacing=6)
        self.header_pill_slot.set_valign(Gtk.Align.CENTER)
        title_row.append(self.header_pill_slot)
        header.append(title_row)

        sub = Gtk.Label(label=section.subtitle)
        sub.add_css_class("nyx-page-sub")
        sub.set_halign(Gtk.Align.START)
        header.append(sub)
        outer.append(header)

        # Content (scrolling)
        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.content = Adw.PreferencesPage()
        self.content.set_vexpand(True)
        scroll.set_child(self.content)
        outer.append(scroll)

        self.set_child(outer)
        try:
            self.build()
        except Exception as e:
            log.exception("build %s: %s", section.key, e)
            err = Adw.PreferencesGroup(title="Error")
            row = Adw.ActionRow(title="Failed to build this section",
                                subtitle=str(e))
            err.add(row)
            self.content.add(err)

    def add_group(self, group: Adw.PreferencesGroup) -> None:
        self.content.add(group)

    def add_pill(self, pill: Gtk.Widget) -> None:
        self.header_pill_slot.append(pill)

    def clear_pills(self) -> None:
        child = self.header_pill_slot.get_first_child()
        while child:
            nxt = child.get_next_sibling()
            self.header_pill_slot.remove(child)
            child = nxt

    def toast(self, msg: str) -> None:
        self.win.toast(msg)

    def schedule_refresh(self, interval_ms: int, fn: Callable[[], bool]) -> None:
        """Live data: re-poll while page is visible."""
        if self._refresh_source is not None:
            try:
                GLib.source_remove(self._refresh_source)
            except Exception:
                pass
        self._refresh_source = GLib.timeout_add(interval_ms, fn)

    def stop_refresh(self) -> None:
        if self._refresh_source is not None:
            try:
                GLib.source_remove(self._refresh_source)
            except Exception:
                pass
            self._refresh_source = None

    def build(self) -> None:
        """Subclasses override."""
        raise NotImplementedError


# ──────────────────────────────────────────────────────────────────────
# §9 honest placeholder — used for every Tier-2 section.
# ──────────────────────────────────────────────────────────────────────
class PlaceholderPage(SectionPage):
    KEY = ""
    WHAT_WORKS = ""
    WHAT_NEXT  = ""

    def build(self) -> None:
        # The wip card uses a free-form Box so we wrap it in a borderless
        # PreferencesGroup to live inside Adw.PreferencesPage.
        grp = Adw.PreferencesGroup()
        grp.add(wip_card(self.section.title,
                         self.WHAT_WORKS or "Section chrome only.",
                         self.WHAT_NEXT  or "Real backend wiring."))
        self.add_group(grp)
        self.add_pill(status_pill("in progress", "warn"))


def _tier2(key: str, what_works: str, what_next: str) -> type:
    """Factory: build a PlaceholderPage subclass for one section."""
    cls = type(
        f"{key.title()}Placeholder",
        (PlaceholderPage,),
        {"KEY": key, "WHAT_WORKS": what_works, "WHAT_NEXT": what_next},
    )
    return cls


# ──────────────────────────────────────────────────────────────────────
# Shared row helpers — kv_row + label_row (live in module scope, used
# by every Tier-2/3 page).
# ──────────────────────────────────────────────────────────────────────
def kv_row(title: str, value: str, subtitle: str = "") -> Adw.ActionRow:
    row = Adw.ActionRow(title=title)
    if subtitle:
        row.set_subtitle(subtitle)
    val = Gtk.Label(label=value)
    val.add_css_class("nyx-kv-value")
    val.set_valign(Gtk.Align.CENTER)
    val.set_selectable(True)
    row.add_suffix(val)
    return row


def action_row(title: str, subtitle: str, button_label: str,
               on_click: Callable[[], None],
               css: str = "nyx-pill") -> Adw.ActionRow:
    row = Adw.ActionRow(title=title, subtitle=subtitle)
    btn = Gtk.Button(label=button_label)
    btn.add_css_class(css)
    btn.set_valign(Gtk.Align.CENTER)
    btn.connect("clicked", lambda _b: on_click())
    row.add_suffix(btn)
    row.set_activatable_widget(btn)
    return row


def empty_row(title: str, subtitle: str = "") -> Adw.ActionRow:
    row = Adw.ActionRow(title=title, subtitle=subtitle)
    row.add_css_class("nyx-empty-row")
    return row


def debounced(scale: Gtk.Scale,
              on_settle: Callable[[float], None],
              delay_ms: int = 250) -> None:
    """Wire a Gtk.Scale so on_settle(value) fires once after the user
    stops dragging, not on every pixel. Prevents flooding hyprctl/IPC."""
    state = {"src": 0}

    def _changed(s):
        if state["src"]:
            try:
                GLib.source_remove(state["src"])
            except Exception:
                pass

        def _fire():
            state["src"] = 0
            try:
                on_settle(s.get_value())
            except Exception as e:
                log.warning("debounced fire: %s", e)
            return False

        state["src"] = GLib.timeout_add(delay_ms, _fire)

    scale.connect("value-changed", _changed)


def open_terminal(cmd: str, win=None) -> bool:
    """Run `cmd` in whatever terminal is installed. Returns True on success."""
    for term in ("foot", "alacritty", "kitty", "wezterm", "xterm"):
        if have(term):
            try:
                subprocess.Popen(
                    [term, "-e", "sh", "-c",
                     f"{cmd}; echo; echo '── press enter to close ──'; read _"],
                    start_new_session=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
                return True
            except Exception as e:
                log.warning("open_terminal: %s", e)
    if win is not None:
        win.toast("no terminal found (install foot/alacritty/kitty)")
    return False


# ──────────────────────────────────────────────────────────────────────
# DISPLAY — hyprctl monitors, brightnessctl, gammastep / hyprsunset
# ──────────────────────────────────────────────────────────────────────
class DisplayPage(SectionPage):
    KEY = "display"

    def build(self) -> None:
        # Monitors
        self.mon_grp = Adw.PreferencesGroup(title="Monitors")
        self.add_group(self.mon_grp)
        # Brightness (per /sys/class/backlight)
        self.bri_grp = Adw.PreferencesGroup(
            title="Brightness",
            description="Backlights detected under /sys/class/backlight")
        self.add_group(self.bri_grp)
        # Night light
        self.nl_grp = Adw.PreferencesGroup(
            title="Night light",
            description="Warm screen tint after sundown to reduce eye strain")
        self.add_group(self.nl_grp)
        # Tools
        tools = Adw.PreferencesGroup(title="Tools")
        self.add_group(tools)
        if have("wlr-randr"):
            tools.add(action_row("Open wlr-randr",
                                 "Inspect outputs in a terminal",
                                 "Launch",
                                 lambda: open_terminal("wlr-randr; read _",
                                                       self.win)))
        if have("nwg-displays"):
            tools.add(action_row("Open nwg-displays",
                                 "GUI multi-monitor arranger",
                                 "Launch",
                                 lambda: fire_and_forget("nwg-displays")))
        if not have("wlr-randr") and not have("nwg-displays"):
            tools.add(empty_row("No external display tool installed",
                                "Install wlr-randr or nwg-displays for "
                                "advanced arrangement"))

        self._render_monitors()
        self._render_brightness()
        self._render_nightlight()
        self.add_pill(status_pill("live", "ok"))
        self.schedule_refresh(10000, self._tick)

    def _tick(self) -> bool:
        self._render_monitors()
        self._render_brightness()
        return True

    def _render_monitors(self) -> None:
        _clear_group(self.mon_grp)
        if not have("hyprctl"):
            self.mon_grp.add(empty_row(
                "hyprctl not found",
                "This page expects Hyprland. Install hyprland to manage "
                "monitors."))
            return
        rc, out, _ = sh(["hyprctl", "monitors", "-j"], timeout=3)
        try:
            mons = json.loads(out) if rc == 0 else []
        except Exception:
            mons = []
        if not mons:
            self.mon_grp.add(empty_row("No monitors reported",
                                        "hyprctl returned an empty list"))
            return
        for m in mons:
            name = m.get("name", "?")
            desc = m.get("description", "")
            sub = (f"{m.get('width','?')}×{m.get('height','?')} "
                   f"@ {m.get('refreshRate', 0):.0f}Hz · "
                   f"scale {m.get('scale', 1)} · "
                   f"transform {m.get('transform', 0)}")
            row = Adw.ActionRow(title=name, subtitle=sub)
            if desc:
                row.set_subtitle(f"{desc} · {sub}")
            tag = Gtk.Label(label="primary" if m.get("focused") else "")
            tag.add_css_class("nyx-pill-ok")
            if m.get("focused"):
                row.add_suffix(tag)
            self.mon_grp.add(row)

    def _render_brightness(self) -> None:
        _clear_group(self.bri_grp)
        backlights = sorted(Path("/sys/class/backlight").glob("*")) \
            if Path("/sys/class/backlight").exists() else []
        if not backlights:
            self.bri_grp.add(empty_row(
                "No backlight device found",
                "Desktops without a panel backlight have no software "
                "brightness control"))
            return
        if not have("brightnessctl"):
            self.bri_grp.add(empty_row(
                "brightnessctl not installed",
                "Install brightnessctl to adjust panel brightness"))
            return
        for bl in backlights:
            try:
                cur = int((bl / "brightness").read_text().strip())
                mx  = int((bl / "max_brightness").read_text().strip())
                pct = int(cur * 100 / max(mx, 1))
            except Exception:
                continue
            row = Adw.ActionRow(title=bl.name, subtitle=f"{pct}% of {mx}")
            scale = Gtk.Scale.new_with_range(
                Gtk.Orientation.HORIZONTAL, 5, 100, 5)
            scale.set_value(pct)
            scale.set_size_request(220, -1)
            scale.set_draw_value(False)
            debounced(scale,
                      lambda v, name=bl.name: sh_async(
                          ["brightnessctl", "-d", name, "set",
                           f"{int(v)}%"],
                          None, timeout=3))
            row.add_suffix(scale)
            self.bri_grp.add(row)

    def _render_nightlight(self) -> None:
        _clear_group(self.nl_grp)
        # Detect any of: hyprsunset, gammastep, wlsunset
        running = ""
        for proc in ("hyprsunset", "gammastep", "wlsunset"):
            rc, out, _ = sh(["pgrep", "-x", proc], timeout=2)
            if rc == 0 and out.strip():
                running = proc
                break
        any_installed = any(have(x) for x in
                            ("hyprsunset", "gammastep", "wlsunset"))
        if not any_installed:
            self.nl_grp.add(empty_row(
                "No night-light service installed",
                "Install hyprsunset, gammastep, or wlsunset"))
            return
        sw = Adw.SwitchRow(title="Night light enabled",
                           subtitle=f"Currently running: "
                                    f"{running or 'none'}")
        sw.set_active(bool(running))
        sw.connect("notify::active", self._on_nightlight, running)
        self.nl_grp.add(sw)

    def _on_nightlight(self, sw, _pspec, running: str) -> None:
        if sw.get_active():
            for proc in ("hyprsunset", "gammastep", "wlsunset"):
                if have(proc):
                    fire_and_forget(proc)
                    self.toast(f"started {proc}")
                    return
        else:
            if running:
                sh_async(["pkill", "-x", running], None, timeout=3)
                self.toast(f"stopped {running}")


# ──────────────────────────────────────────────────────────────────────
# SOUND — pactl (PipeWire/Pulse), per-sink volume + mute, default switcher
# ──────────────────────────────────────────────────────────────────────
class SoundPage(SectionPage):
    KEY = "sound"

    def build(self) -> None:
        self.server_grp = Adw.PreferencesGroup(title="Audio server")
        self.add_group(self.server_grp)
        self.out_grp = Adw.PreferencesGroup(
            title="Outputs",
            description="Sliders adjust volume; switches mute the device")
        self.add_group(self.out_grp)
        self.in_grp  = Adw.PreferencesGroup(title="Inputs")
        self.add_group(self.in_grp)
        tools = Adw.PreferencesGroup(title="Tools")
        self.add_group(tools)
        if have("pavucontrol"):
            tools.add(action_row("Open pavucontrol",
                                 "Per-application mixer & routing",
                                 "Launch",
                                 lambda: fire_and_forget("pavucontrol")))
        if have("easyeffects"):
            tools.add(action_row("Open EasyEffects",
                                 "EQ, compressor, noise reduction",
                                 "Launch",
                                 lambda: fire_and_forget("easyeffects")))
        tools.add(action_row(
            "Restart audio stack",
            "systemctl --user restart pipewire pipewire-pulse wireplumber",
            "Restart",
            lambda: sh_async(
                ["systemctl", "--user", "restart",
                 "pipewire", "pipewire-pulse", "wireplumber"],
                lambda r: self.toast("audio restarted" if r[0] == 0
                                     else "restart failed"),
                timeout=10),
            css="nyx-pill-warn"))

        self._render_all()
        self.add_pill(status_pill("live", "ok"))
        self.schedule_refresh(6000, self._tick)

    def _tick(self) -> bool:
        self._render_all()
        return True

    def _render_all(self) -> None:
        self._render_server()
        self._render_devices("sinks", self.out_grp, "set-sink-volume",
                             "set-sink-mute", "set-default-sink")
        self._render_devices("sources", self.in_grp, "set-source-volume",
                             "set-source-mute", "set-default-source")

    def _render_server(self) -> None:
        _clear_group(self.server_grp)
        if not have("pactl"):
            self.server_grp.add(empty_row(
                "pactl not installed",
                "Install pipewire-pulse or pulseaudio-utils"))
            return
        rc, out, _ = sh(["pactl", "info"], timeout=3)
        info = {}
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()
        name = info.get("Server Name", "(no audio server)")
        backend = "PipeWire" if "PipeWire" in name else \
                  ("PulseAudio" if "PulseAudio" in name else "?")
        self.server_grp.add(kv_row("Backend", backend))
        self.server_grp.add(kv_row("Server", name))
        self.server_grp.add(kv_row("Default sink",
                                   info.get("Default Sink", "?")))
        self.server_grp.add(kv_row("Default source",
                                   info.get("Default Source", "?")))

    def _render_devices(self, kind: str, grp: Adw.PreferencesGroup,
                        vol_cmd: str, mute_cmd: str, default_cmd: str) -> None:
        _clear_group(grp)
        if not have("pactl"):
            grp.add(empty_row("pactl not installed", ""))
            return
        rc, out, _ = sh(["pactl", "list", kind, "short"], timeout=3)
        if rc != 0 or not out.strip():
            grp.add(empty_row(f"No {kind[:-1]} devices found", ""))
            return
        # Default device id
        rc2, defout, _ = sh(["pactl", "get-default-" + kind[:-1]], timeout=2)
        default_id = defout.strip() if rc2 == 0 else ""

        rc3, full, _ = sh(["pactl", "list", kind], timeout=4)
        # Parse description, mute, volume per device id
        devices = {}
        cur = None
        for line in full.splitlines():
            m = re.match(r"^\s*Name:\s+(.+)$", line)
            if m and not line.startswith("\t\t"):
                cur = m.group(1)
                devices[cur] = {"desc": cur, "mute": False, "vol": 0}
                continue
            if cur is None:
                continue
            md = re.match(r"^\s*Description:\s+(.+)$", line)
            if md:
                devices[cur]["desc"] = md.group(1)
            mm = re.match(r"^\s*Mute:\s+(yes|no)", line)
            if mm:
                devices[cur]["mute"] = (mm.group(1) == "yes")
            mv = re.match(r"^\s*Volume:.*?(\d+)%", line)
            if mv:
                devices[cur]["vol"] = int(mv.group(1))

        for did, d in devices.items():
            is_default = (did == default_id)
            sub = "default device" if is_default else did[:60]
            row = Adw.ActionRow(title=d["desc"], subtitle=sub)
            # Volume slider
            scale = Gtk.Scale.new_with_range(
                Gtk.Orientation.HORIZONTAL, 0, 150, 5)
            scale.set_value(min(d["vol"], 150))
            scale.set_size_request(180, -1)
            scale.set_draw_value(False)
            debounced(scale,
                      lambda v, i=did, c=vol_cmd: sh_async(
                          ["pactl", c, i, f"{int(v)}%"],
                          None, timeout=3))
            row.add_suffix(scale)
            # Mute switch
            mute = Gtk.Switch()
            mute.set_active(not d["mute"])  # active = unmuted (sound on)
            mute.set_valign(Gtk.Align.CENTER)
            mute.set_tooltip_text("toggle audio")
            mute.connect("notify::active",
                         lambda sw, _p, i=did, c=mute_cmd: sh_async(
                             ["pactl", c, i,
                              "0" if sw.get_active() else "1"],
                             None, timeout=3))
            row.add_suffix(mute)
            # Set-default button (if not current default)
            if not is_default:
                btn = Gtk.Button(label="Default")
                btn.add_css_class("nyx-pill")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked",
                            lambda _b, i=did, c=default_cmd: (
                                sh_async(["pactl", c, i],
                                         lambda r: self.toast(
                                             "default set" if r[0] == 0
                                             else "failed"),
                                         timeout=3)))
                row.add_suffix(btn)
            grp.add(row)


# ──────────────────────────────────────────────────────────────────────
# POWER — battery, profiles (powerprofilesctl), CPU governor
# ──────────────────────────────────────────────────────────────────────
class PowerPage(SectionPage):
    """Battery, power profiles, CPU governor, idle/sleep timers, lid &
    button actions, and low-battery thresholds. All edits are real:
      · powerprofilesctl       — live profile switching
      · /sys/.../cpufreq/*     — pkexec write to all cores
      · ~/.config/hypr/hypridle.conf  — regenerated from prefs
      · /etc/systemd/logind.conf.d/00-nyxus-power.conf — pkexec
      · /etc/UPower/UPower.conf — pkexec, restart upower
      · ~/.config/systemd/user/nyxus-power-autoswitch.service — auto AC/bat
    """
    KEY = "power"
    LOGIND_OVERRIDE = "/etc/systemd/logind.conf.d/00-nyxus-power.conf"
    HYPRIDLE_CONF = str(Path.home() / ".config/hypr/hypridle.conf")
    LID_ACTIONS = ["suspend", "lock", "hibernate", "poweroff", "ignore"]
    POWER_KEY_ACTIONS = ["suspend", "poweroff", "reboot", "lock",
                         "hibernate", "ignore"]
    IDLE_ACTIONS = ["suspend", "poweroff", "hibernate", "lock", "ignore"]
    SLEEP_PRESETS = [0, 60, 120, 300, 600, 900, 1800, 3600, 7200]

    def build(self) -> None:
        self.bat_grp = Adw.PreferencesGroup(title="Battery")
        self.add_group(self.bat_grp)
        self.prof_grp = Adw.PreferencesGroup(
            title="Power profile",
            description="Live switching via powerprofilesctl, plus optional "
                        "auto-switch on AC/battery")
        self.add_group(self.prof_grp)
        self.gov_grp = Adw.PreferencesGroup(
            title="CPU governor",
            description="Per-core scaling strategy from /sys/devices/system/cpu")
        self.add_group(self.gov_grp)
        self.sleep_grp = Adw.PreferencesGroup(
            title="Screen & sleep",
            description="Idle timers (managed by hypridle). 'Never' = disabled.")
        self.add_group(self.sleep_grp)
        self.lid_grp = Adw.PreferencesGroup(
            title="Buttons & lid",
            description="Logind actions (written to /etc/systemd/logind.conf.d/"
                        "00-nyxus-power.conf via admin prompt)")
        self.add_group(self.lid_grp)
        self.low_grp = Adw.PreferencesGroup(
            title="Low battery",
            description="UPower thresholds for warning + critical action")
        self.add_group(self.low_grp)
        tools = Adw.PreferencesGroup(title="Tools")
        self.add_group(tools)
        for label, cmd in (("powertop",     "sudo powertop"),
                           ("tlp-stat",     "sudo tlp-stat -s | less"),
                           ("upower dump",  "upower --dump | less")):
            bin0 = label.split()[0]
            if have(bin0):
                tools.add(action_row(
                    f"Open {label}", "Runs in your terminal",
                    "Launch",
                    lambda c=cmd: open_terminal(c, self.win)))

        self._render()
        self.add_pill(status_pill("live", "ok"))
        self.schedule_refresh(8000, self._tick)

    def _tick(self) -> bool:
        # Only refresh fast-changing data (battery + freq) on the timer.
        self._render_battery()
        self._render_governor_freq()
        return True

    def _render(self) -> None:
        self._render_battery()
        self._render_profile()
        self._render_governor()
        self._render_sleep()
        self._render_lid()
        self._render_low_battery()

    # ────────────────────────────────────────────────────────────
    # Battery
    # ────────────────────────────────────────────────────────────
    def _render_battery(self) -> None:
        _clear_group(self.bat_grp)
        psp = Path("/sys/class/power_supply")
        bats = sorted(psp.glob("BAT*")) if psp.exists() else []
        if not bats:
            self.bat_grp.add(empty_row(
                "No battery detected",
                "This appears to be a desktop or VM"))
            return
        for b in bats:
            try:
                cap  = (b / "capacity").read_text().strip()
                stat = (b / "status").read_text().strip()
                row  = Adw.ActionRow(title=b.name,
                                     subtitle=f"{cap}%  ·  {stat}")
                # Health: prefer energy_*, fall back to charge_*
                e1 = e2 = 0
                ef, efd = b / "energy_full", b / "energy_full_design"
                cf, cfd = b / "charge_full", b / "charge_full_design"
                if ef.exists() and efd.exists():
                    e1, e2 = int(ef.read_text()), int(efd.read_text())
                elif cf.exists() and cfd.exists():
                    e1, e2 = int(cf.read_text()), int(cfd.read_text())
                if e2 > 0:
                    pct = e1 * 100 // e2
                    h = Gtk.Label(label=f"health {pct}%")
                    h.add_css_class("nyx-kv-value")
                    row.add_suffix(h)
                self.bat_grp.add(row)

                # Cycle count
                cyc = b / "cycle_count"
                if cyc.exists():
                    try:
                        n = int(cyc.read_text().strip())
                        if n > 0:
                            self.bat_grp.add(kv_row(
                                f"{b.name} cycles", str(n),
                                "lower is better"))
                    except Exception:
                        pass

                # Time remaining
                tr = self._battery_time_remaining(b)
                if tr:
                    self.bat_grp.add(kv_row(
                        f"{b.name} time", tr,
                        "estimate — refines as load stabilizes"))

                # Charge limit (ASUS / Lenovo / Framework / supported)
                ccet = b / "charge_control_end_threshold"
                if ccet.exists():
                    self._render_charge_limit_row(b, ccet)
            except Exception as e:
                log.warning("battery %s: %s", b, e)

    def _render_charge_limit_row(self, bat: Path, ccet_path: Path) -> None:
        try:
            cur = int(ccet_path.read_text().strip())
        except Exception:
            cur = 100
        row = Adw.ActionRow(
            title=f"{bat.name} charge limit",
            subtitle=f"Stop charging at {cur}% (extends battery longevity)")
        scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 50, 100, 5)
        scale.set_value(cur)
        scale.set_size_request(180, -1)
        scale.set_draw_value(True)
        scale.set_value_pos(Gtk.PositionType.RIGHT)

        def _apply(v, p=str(ccet_path)) -> None:
            sh_async(
                ["pkexec", "sh", "-c", f"echo {int(v)} > {p}"],
                lambda r: self.toast(
                    f"charge limit → {int(v)}%" if r[0] == 0
                    else "needs admin / unsupported"),
                timeout=6)

        debounced(scale, _apply, 400)
        row.add_suffix(scale)
        self.bat_grp.add(row)

    def _battery_time_remaining(self, b: Path) -> str:
        try:
            stat = (b / "status").read_text().strip()
            if stat not in ("Discharging", "Charging"):
                return ""
            for now_n, rate_n, full_n in (
                    ("energy_now", "power_now",   "energy_full"),
                    ("charge_now", "current_now", "charge_full")):
                pn, pr, pf = b / now_n, b / rate_n, b / full_n
                if pn.exists() and pr.exists():
                    n = int(pn.read_text())
                    r = int(pr.read_text())
                    if r <= 0:
                        return ""
                    if stat == "Discharging":
                        secs = n * 3600 // r
                        suffix = "until empty"
                    else:
                        if not pf.exists():
                            return ""
                        f = int(pf.read_text())
                        secs = max(f - n, 0) * 3600 // r
                        suffix = "until full"
                    h, m = secs // 3600, (secs % 3600) // 60
                    return f"{h}h {m:02d}m {suffix}"
            return ""
        except Exception:
            return ""

    # ────────────────────────────────────────────────────────────
    # Power profile + auto-switch
    # ────────────────────────────────────────────────────────────
    def _render_profile(self) -> None:
        _clear_group(self.prof_grp)
        if not have("powerprofilesctl"):
            self.prof_grp.add(empty_row(
                "powerprofilesctl not installed",
                "Install power-profiles-daemon"))
            return
        rc, out, _ = sh(["powerprofilesctl", "get"], timeout=3)
        cur = out.strip() if rc == 0 else "?"
        row = Adw.ActionRow(title="Active profile", subtitle=cur)
        box = Gtk.Box(spacing=6)
        box.set_valign(Gtk.Align.CENTER)
        for p in ("power-saver", "balanced", "performance"):
            btn = Gtk.Button(label=p)
            btn.add_css_class("nyx-pill" if p != cur else "nyx-pill-ok")
            btn.connect("clicked", lambda _b, p=p: sh_async(
                ["powerprofilesctl", "set", p],
                lambda r: (self.toast(
                    f"profile → {p}" if r[0] == 0 else "failed"),
                    self._render_profile()),
                timeout=3))
            box.append(btn)
        row.add_suffix(box)
        self.prof_grp.add(row)

        prefs = load_prefs()
        autosw = bool(prefs.get("power", {}).get("auto_profile", False))
        sw_row = Adw.ActionRow(
            title="Auto-switch on AC / battery",
            subtitle="performance on AC, power-saver on battery "
                     "(via systemd --user service)")
        sw = Gtk.Switch()
        sw.set_active(autosw)
        sw.set_valign(Gtk.Align.CENTER)
        sw.connect("notify::active", self._on_auto_profile_toggled)
        sw_row.add_suffix(sw)
        self.prof_grp.add(sw_row)

    def _on_auto_profile_toggled(self, sw, _p) -> None:
        prefs = load_prefs()
        prefs.setdefault("power", {})["auto_profile"] = sw.get_active()
        save_prefs(prefs)
        self._sync_auto_profile_hook()
        self.toast("auto-switch " + ("on" if sw.get_active() else "off"))

    def _sync_auto_profile_hook(self) -> None:
        unit_dir = Path.home() / ".config/systemd/user"
        unit_dir.mkdir(parents=True, exist_ok=True)
        unit = unit_dir / "nyxus-power-autoswitch.service"
        prefs = load_prefs()
        enabled = bool(prefs.get("power", {}).get("auto_profile", False))
        if enabled:
            unit.write_text(textwrap.dedent("""\
                [Unit]
                Description=NYXUS auto power profile switcher (AC/battery)
                After=graphical-session.target

                [Service]
                Type=simple
                ExecStart=/bin/sh -c 'while sleep 15; do ac=$(cat /sys/class/power_supply/A*/online 2>/dev/null | head -1); want=power-saver; [ "$ac" = "1" ] && want=performance; cur=$(powerprofilesctl get 2>/dev/null); [ -n "$cur" ] && [ "$cur" != "$want" ] && powerprofilesctl set "$want" 2>/dev/null || true; done'
                Restart=on-failure
                RestartSec=10

                [Install]
                WantedBy=default.target
                """))
            sh_async(
                ["systemctl", "--user", "daemon-reload"],
                lambda _r: sh_async(
                    ["systemctl", "--user", "enable", "--now",
                     "nyxus-power-autoswitch.service"],
                    None, timeout=4),
                timeout=4)
        else:
            sh_async(
                ["systemctl", "--user", "disable", "--now",
                 "nyxus-power-autoswitch.service"],
                lambda _r: None, timeout=4)
            try:
                unit.unlink()
            except FileNotFoundError:
                pass

    # ────────────────────────────────────────────────────────────
    # CPU governor
    # ────────────────────────────────────────────────────────────
    def _render_governor(self) -> None:
        _clear_group(self.gov_grp)
        gp = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor")
        ap = Path("/sys/devices/system/cpu/cpu0/cpufreq/"
                  "scaling_available_governors")
        if not gp.exists():
            self.gov_grp.add(empty_row(
                "cpufreq not available",
                "This CPU/kernel does not expose scaling governors"))
            return
        try:
            cur = gp.read_text().strip()
            avail = ap.read_text().split() if ap.exists() else [cur]
        except Exception:
            cur, avail = "?", []
        self.gov_grp.add(Adw.ActionRow(
            title="Current governor", subtitle=cur))
        self._freq_row = Adw.ActionRow(
            title="cpu0 frequency", subtitle="reading…")
        self.gov_grp.add(self._freq_row)
        self._render_governor_freq()
        for g in avail:
            btn_row = Adw.ActionRow(
                title=g,
                subtitle="active" if g == cur
                else "Click to switch (requires admin)")
            if g != cur:
                b = Gtk.Button(label="Use")
                b.add_css_class("nyx-pill")
                b.set_valign(Gtk.Align.CENTER)
                b.connect("clicked", lambda _b, g=g: sh_async(
                    ["pkexec", "sh", "-c",
                     f"for f in /sys/devices/system/cpu/cpu*/cpufreq/"
                     f"scaling_governor; do echo {g} > $f; done"],
                    lambda r: (self.toast(
                        f"governor → {g}" if r[0] == 0 else "needs admin"),
                        self._render_governor()),
                    timeout=10))
                btn_row.add_suffix(b)
            self.gov_grp.add(btn_row)

    def _render_governor_freq(self) -> None:
        if not hasattr(self, "_freq_row"):
            return
        fp = Path("/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq")
        if fp.exists():
            try:
                f = int(fp.read_text().strip())
                self._freq_row.set_subtitle(f"{f//1000} MHz")
                return
            except Exception:
                pass
        self._freq_row.set_subtitle("unavailable")

    # ────────────────────────────────────────────────────────────
    # Screen & sleep (hypridle, NYXUS-managed)
    # ────────────────────────────────────────────────────────────
    def _hypridle_prefs(self) -> dict:
        prefs = load_prefs()
        p = prefs.setdefault("power", {})
        defaults = {
            "dim_secs":         300,   # 5 min  — dim screen
            "lock_secs":        600,   # 10 min — lockscreen
            "screen_secs":      900,   # 15 min — DPMS off
            "suspend_secs":    1800,   # 30 min — suspend (battery)
            "suspend_ac_secs":    0,   # 0 = never on AC
        }
        for k, v in defaults.items():
            p.setdefault(k, v)
        return p

    def _render_sleep(self) -> None:
        _clear_group(self.sleep_grp)
        p = self._hypridle_prefs()
        for key, title, sub in (
            ("dim_secs",         "Dim screen after",
             "lower brightness while still showing the screen"),
            ("lock_secs",        "Lock screen after",
             "show the lockscreen (you can keep working)"),
            ("screen_secs",      "Turn off screen after",
             "DPMS off — display sleeps but session continues"),
            ("suspend_secs",     "Suspend after (on battery)",
             "system suspends to RAM"),
            ("suspend_ac_secs",  "Suspend after (on AC)",
             "system suspends while plugged in"),
        ):
            cur = int(p.get(key, 0))
            self.sleep_grp.add(self._duration_row(title, sub, cur, key))

    def _duration_row(self, title: str, sub: str, cur_secs: int,
                      pref_key: str) -> Adw.ActionRow:
        row = Adw.ActionRow(title=title, subtitle=sub)
        try:
            idx = self.SLEEP_PRESETS.index(cur_secs)
        except ValueError:
            idx = min(range(len(self.SLEEP_PRESETS)),
                      key=lambda i: abs(self.SLEEP_PRESETS[i] - cur_secs))
        labels = [self._fmt_secs(s) for s in self.SLEEP_PRESETS]
        dd = Gtk.DropDown.new_from_strings(labels)
        dd.set_selected(idx)
        dd.set_valign(Gtk.Align.CENTER)
        dd.connect("notify::selected",
                   lambda d, _p, k=pref_key: self._on_duration_changed(d, k))
        row.add_suffix(dd)
        return row

    @staticmethod
    def _fmt_secs(s: int) -> str:
        if s == 0:
            return "Never"
        if s < 60:
            return f"{s}s"
        if s < 3600:
            return f"{s // 60} min"
        return f"{s // 3600} h"

    def _on_duration_changed(self, dd, pref_key: str) -> None:
        idx = dd.get_selected()
        if idx < 0 or idx >= len(self.SLEEP_PRESETS):
            return
        secs = self.SLEEP_PRESETS[idx]
        prefs = load_prefs()
        prefs.setdefault("power", {})[pref_key] = secs
        save_prefs(prefs)
        self._regenerate_hypridle()
        self.toast(f"{pref_key.replace('_', ' ')} → {self._fmt_secs(secs)}")

    def _regenerate_hypridle(self) -> None:
        """Rewrite ~/.config/hypr/hypridle.conf from NYXUS prefs.

        Battery-vs-AC suspend is implemented as TWO listeners, each gating
        on the AC online state at fire time, so one of them is always a
        no-op depending on power source."""
        p = self._hypridle_prefs()
        cfg = Path(self.HYPRIDLE_CONF)
        cfg.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# nyxus-managed: regenerated by Settings → Power. "
            "Manual edits will be overwritten.",
            "general {",
            "    lock_cmd = pidof hyprlock || hyprlock",
            "    before_sleep_cmd = loginctl lock-session",
            "    after_sleep_cmd  = hyprctl dispatch dpms on",
            "    ignore_dbus_inhibit = false",
            "}",
            "",
        ]
        if p["dim_secs"] > 0 and have("brightnessctl"):
            lines += [
                "listener {",
                f"    timeout = {p['dim_secs']}",
                "    on-timeout = brightnessctl -s set 10%",
                "    on-resume  = brightnessctl -r",
                "}",
                "",
            ]
        if p["lock_secs"] > 0:
            lines += [
                "listener {",
                f"    timeout = {p['lock_secs']}",
                "    on-timeout = loginctl lock-session",
                "}",
                "",
            ]
        if p["screen_secs"] > 0:
            lines += [
                "listener {",
                f"    timeout = {p['screen_secs']}",
                "    on-timeout = hyprctl dispatch dpms off",
                "    on-resume  = hyprctl dispatch dpms on",
                "}",
                "",
            ]
        if p["suspend_secs"] > 0:
            lines += [
                "listener {",
                f"    timeout = {p['suspend_secs']}",
                "    on-timeout = sh -c 'ac=$(cat /sys/class/power_supply/A*/online 2>/dev/null | head -1); [ \"$ac\" != \"1\" ] && systemctl suspend'",
                "}",
                "",
            ]
        if p["suspend_ac_secs"] > 0:
            lines += [
                "listener {",
                f"    timeout = {p['suspend_ac_secs']}",
                "    on-timeout = sh -c 'ac=$(cat /sys/class/power_supply/A*/online 2>/dev/null | head -1); [ \"$ac\" = \"1\" ] && systemctl suspend'",
                "}",
                "",
            ]
        try:
            cfg.write_text("\n".join(lines))
            sh_async(["systemctl", "--user", "restart", "hypridle.service"],
                     None, timeout=4)
        except Exception as e:
            log.warning("hypridle write: %s", e)
            self.toast("hypridle write failed")

    # ────────────────────────────────────────────────────────────
    # Buttons & lid (logind override)
    # ────────────────────────────────────────────────────────────
    def _logind_overrides(self) -> dict:
        try:
            txt = Path(self.LOGIND_OVERRIDE).read_text()
        except Exception:
            return {}
        out = {}
        for line in txt.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("["):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
        return out

    def _write_logind_overrides(self, updates: dict, on_done=None) -> None:
        cur = self._logind_overrides()
        cur.update(updates)
        cur = {k: v for k, v in cur.items() if v}  # strip empty → falls back
        body = ("# nyxus-managed: written by Settings → Power\n"
                "[Login]\n"
                + "\n".join(f"{k}={v}" for k, v in sorted(cur.items()))
                + "\n")
        cmd = ["pkexec", "sh", "-c",
               f"mkdir -p /etc/systemd/logind.conf.d && "
               f"cat > {self.LOGIND_OVERRIDE} <<'NYXUS_EOF'\n{body}NYXUS_EOF\n"
               f"systemctl kill -s HUP systemd-logind 2>/dev/null || true"]
        sh_async(cmd, on_done, timeout=8)

    def _render_lid(self) -> None:
        _clear_group(self.lid_grp)
        cur = self._logind_overrides()
        rows = (
            ("HandleLidSwitch", "When lid closes (on battery)",
             "system action when laptop lid is closed",
             self.LID_ACTIONS),
            ("HandleLidSwitchExternalPower", "When lid closes (on AC)",
             "system action when lid closed while plugged in",
             self.LID_ACTIONS),
            ("HandleLidSwitchDocked", "When lid closes (docked)",
             "system action when an external monitor is connected",
             self.LID_ACTIONS),
            ("HandlePowerKey", "Power button",
             "system action on a short press of the power key",
             self.POWER_KEY_ACTIONS),
            ("IdleAction", "After idle (logind fallback)",
             "fired only if hypridle isn't already handling it",
             self.IDLE_ACTIONS),
        )
        for key, title, sub, options in rows:
            current = cur.get(key, "")
            row = Adw.ActionRow(title=title, subtitle=sub)
            labels = ["(system default)"] + options
            dd = Gtk.DropDown.new_from_strings(labels)
            try:
                sel = labels.index(current) if current else 0
            except ValueError:
                sel = 0
            dd.set_selected(sel)
            dd.set_valign(Gtk.Align.CENTER)
            dd.connect(
                "notify::selected",
                lambda d, _p, k=key, ls=labels:
                    self._on_lid_changed(d, k, ls))
            row.add_suffix(dd)
            self.lid_grp.add(row)

        sec_row = Adw.ActionRow(
            title="Logind idle timeout",
            subtitle="when to fire the action above (e.g. 30min, 1h, 0 = off)")
        entry = Gtk.Entry()
        entry.set_text(cur.get("IdleActionSec", ""))
        entry.set_placeholder_text("e.g. 30min")
        entry.set_valign(Gtk.Align.CENTER)
        entry.set_size_request(120, -1)
        entry.connect("activate", self._on_idle_sec_set)
        sec_row.add_suffix(entry)
        self.lid_grp.add(sec_row)

    def _on_lid_changed(self, dd, key: str, labels: list) -> None:
        idx = dd.get_selected()
        val = labels[idx] if 0 <= idx < len(labels) else ""
        if val == "(system default)":
            val = ""
        self._write_logind_overrides(
            {key: val},
            lambda r: self.toast(
                f"{key} → {val or 'default'}" if r[0] == 0
                else "needs admin / write failed"))

    def _on_idle_sec_set(self, entry) -> None:
        val = entry.get_text().strip()
        self._write_logind_overrides(
            {"IdleActionSec": val},
            lambda r: self.toast(
                f"idle timeout → {val or 'default'}" if r[0] == 0
                else "needs admin / write failed"))

    # ────────────────────────────────────────────────────────────
    # Low battery (UPower)
    # ────────────────────────────────────────────────────────────
    def _render_low_battery(self) -> None:
        _clear_group(self.low_grp)
        if not have("upower"):
            self.low_grp.add(empty_row(
                "upower not installed",
                "Install upower for low-battery actions"))
            return
        prefs = load_prefs().get("power", {})
        thr = int(prefs.get("low_pct", 15))
        crit = int(prefs.get("crit_pct", 5))
        action = prefs.get("crit_action", "Suspend")

        thr_row = Adw.ActionRow(
            title="Warn at battery level",
            subtitle="show a notification when battery falls below this")
        scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 5, 50, 5)
        scale.set_value(thr)
        scale.set_size_request(180, -1)
        scale.set_draw_value(True)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        debounced(scale,
                  lambda v: self._set_low_pref("low_pct", int(v)), 400)
        thr_row.add_suffix(scale)
        self.low_grp.add(thr_row)

        crit_row = Adw.ActionRow(
            title="Critical at battery level",
            subtitle="trigger action below when battery falls to this")
        cscale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 1, 20, 1)
        cscale.set_value(crit)
        cscale.set_size_request(180, -1)
        cscale.set_draw_value(True)
        cscale.set_value_pos(Gtk.PositionType.RIGHT)
        debounced(cscale,
                  lambda v: self._set_low_pref("crit_pct", int(v)), 400)
        crit_row.add_suffix(cscale)
        self.low_grp.add(crit_row)

        action_row_w = Adw.ActionRow(
            title="At critical level",
            subtitle="written to /etc/UPower/UPower.conf via admin prompt")
        opts = ["Suspend", "Hibernate", "PowerOff", "Ignore"]
        dd = Gtk.DropDown.new_from_strings(opts)
        try:
            dd.set_selected(opts.index(action))
        except ValueError:
            dd.set_selected(0)
        dd.set_valign(Gtk.Align.CENTER)
        dd.connect("notify::selected",
                   lambda d, _p, o=opts: self._on_crit_action(d, o))
        action_row_w.add_suffix(dd)
        self.low_grp.add(action_row_w)

    def _set_low_pref(self, key: str, val) -> None:
        prefs = load_prefs()
        prefs.setdefault("power", {})[key] = val
        save_prefs(prefs)
        self._sync_upower_conf()

    def _on_crit_action(self, dd, opts: list) -> None:
        idx = dd.get_selected()
        if 0 <= idx < len(opts):
            self._set_low_pref("crit_action", opts[idx])
            self.toast(f"critical action → {opts[idx]}")

    def _sync_upower_conf(self) -> None:
        prefs = load_prefs().get("power", {})
        thr = int(prefs.get("low_pct", 15))
        crit = int(prefs.get("crit_pct", 5))
        action = prefs.get("crit_action", "Suspend")
        body = textwrap.dedent(f"""\
            # nyxus-managed: written by Settings → Power
            [UPower]
            PercentageLow={thr}
            PercentageCritical={crit}
            PercentageAction={max(crit - 2, 1)}
            CriticalPowerAction={action}
            """)
        cmd = ["pkexec", "sh", "-c",
               f"cat > /etc/UPower/UPower.conf <<'NYXUS_EOF'\n{body}"
               f"NYXUS_EOF\nsystemctl restart upower 2>/dev/null || true"]
        sh_async(cmd, lambda r: self.toast(
            "UPower updated" if r[0] == 0
            else "UPower write failed (admin?)"), timeout=8)


# ──────────────────────────────────────────────────────────────────────
# NOTIFICATIONS — mako / dunst / swaync
# ──────────────────────────────────────────────────────────────────────
class NotificationsPage(SectionPage):
    KEY = "notifications"

    def _detect(self) -> str:
        for proc in ("mako", "dunst", "swaync"):
            rc, out, _ = sh(["pgrep", "-x", proc], timeout=2)
            if rc == 0 and out.strip():
                return proc
        for proc in ("mako", "dunst", "swaync"):
            if have(proc):
                return proc + ":installed"
        return ""

    def build(self) -> None:
        self.daemon_full = self._detect()
        self.daemon = self.daemon_full.split(":")[0] if self.daemon_full \
            else ""

        # Detection summary
        det = Adw.PreferencesGroup(title="Notification daemon")
        self.add_group(det)
        for name in ("mako", "dunst", "swaync"):
            rc, out, _ = sh(["pgrep", "-x", name], timeout=2)
            running = (rc == 0 and bool(out.strip()))
            installed = have(name) or have(name + "ctl") or \
                        (name == "swaync" and have("swaync-client"))
            mark = "running" if running else \
                   ("installed" if installed else "missing")
            row = kv_row(name, mark)
            det.add(row)

        if not self.daemon:
            warn = Adw.PreferencesGroup(
                title="No daemon active",
                description="Apps that send notifications via D-Bus will "
                            "fail silently until one is installed and "
                            "running. Install mako, dunst, or swaync.")
            self.add_group(warn)
            self.add_pill(status_pill("inactive", "danger"))
            return

        # DND toggle
        dnd_grp = Adw.PreferencesGroup(
            title="Do Not Disturb",
            description="Silences popups system-wide")
        self.add_group(dnd_grp)
        dnd_on = self._dnd_state()
        sw = Adw.SwitchRow(title="Do Not Disturb",
                           subtitle=f"daemon: {self.daemon}")
        sw.set_active(dnd_on)
        sw.connect("notify::active", self._on_dnd)
        dnd_grp.add(sw)

        # Quick controls
        qc = Adw.PreferencesGroup(title="Quick controls")
        self.add_group(qc)
        # Use sh_async so the UI never blocks waiting for the daemon.
        def _ctl(argv, toast_msg):
            sh_async(argv, lambda r: self.toast(toast_msg), timeout=4)

        if self.daemon == "mako":
            qc.add(action_row("Dismiss all", "makoctl dismiss --all",
                              "Dismiss",
                              lambda: _ctl(["makoctl", "dismiss", "--all"],
                                           "dismissed all"),
                              css="nyx-pill-warn"))
            qc.add(action_row("Dismiss latest", "makoctl dismiss",
                              "Dismiss",
                              lambda: _ctl(["makoctl", "dismiss"],
                                           "dismissed latest")))
            qc.add(action_row("Restore last", "makoctl restore",
                              "Restore",
                              lambda: _ctl(["makoctl", "restore"],
                                           "restored")))
            qc.add(action_row("Reload config", "makoctl reload",
                              "Reload",
                              lambda: _ctl(["makoctl", "reload"],
                                           "reloaded")))
        elif self.daemon == "dunst":
            qc.add(action_row("Close all", "dunstctl close-all", "Close",
                              lambda: _ctl(["dunstctl", "close-all"],
                                           "closed all"),
                              css="nyx-pill-warn"))
            qc.add(action_row("Close latest", "dunstctl close", "Close",
                              lambda: _ctl(["dunstctl", "close"],
                                           "closed latest")))
            qc.add(action_row("Show context menu", "dunstctl context",
                              "Open",
                              lambda: _ctl(["dunstctl", "context"],
                                           "context")))
        elif self.daemon == "swaync":
            qc.add(action_row("Toggle panel", "swaync-client -t", "Toggle",
                              lambda: _ctl(["swaync-client", "-t"],
                                           "toggled")))
            qc.add(action_row("Reload", "swaync-client -R", "Reload",
                              lambda: _ctl(["swaync-client", "-R"],
                                           "reloaded")))

        # History
        hist = Adw.PreferencesGroup(title="History")
        self.add_group(hist)
        if self.daemon == "dunst":
            rc, out, _ = sh(["dunstctl", "count", "history"], timeout=3)
            n = (out or "0").strip()
            hist.add(kv_row("Stored notifications", n))
            hist.add(action_row("Show history popup",
                                "dunstctl history-pop",
                                "Show",
                                lambda: sh_async(
                                    ["dunstctl", "history-pop"],
                                    None, timeout=3)))
        elif self.daemon == "mako":
            rc, out, _ = sh(["makoctl", "history"], timeout=3)
            try:
                arr = json.loads(out or "{}").get("data", [[]])[0]
            except Exception:
                arr = []
            hist.add(kv_row("Stored notifications", str(len(arr))))
            for n in arr[-5:]:
                summ = (n.get("summary", {}) or {}).get("data", "?")
                app  = (n.get("app-name", {}) or {}).get("data", "?")
                hist.add(kv_row(f"{app}", str(summ)[:60]))
        else:
            hist.add(empty_row("History viewer not implemented for swaync",
                               "swaync provides its own panel UI"))

        self.add_pill(status_pill(self.daemon, "ok"))

    def _dnd_state(self) -> bool:
        if self.daemon == "mako":
            rc, out, _ = sh(["makoctl", "mode"], timeout=2)
            return "do-not-disturb" in (out or "")
        if self.daemon == "dunst":
            rc, out, _ = sh(["dunstctl", "is-paused"], timeout=2)
            return "true" in (out or "").lower()
        if self.daemon == "swaync":
            rc, out, _ = sh(["swaync-client", "-D"], timeout=2)
            return "true" in (out or "").lower()
        return False

    def _on_dnd(self, sw, _pspec) -> None:
        on = sw.get_active()
        if self.daemon == "mako":
            sh_async(["makoctl", "mode", "-t",
                      "do-not-disturb" if on else "default"],
                     None, timeout=3)
        elif self.daemon == "dunst":
            sh_async(["dunstctl", "set-paused",
                      "true" if on else "false"], None, timeout=3)
        elif self.daemon == "swaync":
            sh_async(["swaync-client", "-d"], None, timeout=3)  # toggles
        self.toast(f"DND {'on' if on else 'off'}")


# ──────────────────────────────────────────────────────────────────────
# DATE & TIME — timedatectl, world clock
# ──────────────────────────────────────────────────────────────────────
class DateTimePage(SectionPage):
    KEY = "datetime"

    def build(self) -> None:
        rc, out, _ = sh(["timedatectl"], timeout=3)
        info = {}
        for line in out.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = v.strip()

        sys_grp = Adw.PreferencesGroup(title="System time")
        self.add_group(sys_grp)
        for label, key in (("Local time",     "Local time"),
                           ("Universal time", "Universal time"),
                           ("RTC time",       "RTC time"),
                           ("Time zone",      "Time zone")):
            sys_grp.add(kv_row(label, info.get(key, "?")))

        # NTP toggle
        ntp_on = info.get("System clock synchronized", "").lower() == "yes"
        ntp_sw = Adw.SwitchRow(
            title="Network time (NTP)",
            subtitle="Auto-sync the system clock from internet time servers")
        ntp_sw.set_active(ntp_on)
        ntp_sw.connect("notify::active", self._on_ntp)
        sys_grp.add(ntp_sw)

        # RTC mode
        rtc_local = info.get("RTC in local TZ", "no").lower() == "yes"
        rtc_sw = Adw.SwitchRow(
            title="RTC stored in local time",
            subtitle="Off = UTC (recommended for Linux-only systems)")
        rtc_sw.set_active(rtc_local)
        rtc_sw.connect("notify::active", self._on_rtc_local)
        sys_grp.add(rtc_sw)

        # Sync now
        sys_grp.add(action_row(
            "Resync clock now",
            "Restart the time service to force an NTP sync",
            "Sync",
            lambda: sh_async(
                ["pkexec", "systemctl", "restart", "systemd-timesyncd"],
                lambda r: self.toast("resynced" if r[0] == 0
                                     else "needs sudo / not installed"),
                timeout=10)))

        # Timezone picker
        tz_grp = Adw.PreferencesGroup(title="Time zone")
        self.add_group(tz_grp)
        rc, tzs_out, _ = sh(["timedatectl", "list-timezones"], timeout=4)
        zones = tzs_out.splitlines() if rc == 0 else []
        if zones:
            sl = Gtk.StringList.new(zones)
            combo = Adw.ComboRow(title="Time zone")
            combo.set_subtitle(f"{len(zones)} zones available")
            combo.set_model(sl)
            cur_tz = info.get("Time zone", "").split(" ")[0]
            try:
                combo.set_selected(zones.index(cur_tz))
            except (ValueError, AttributeError):
                pass
            tz_grp.add(combo)
            tz_grp.add(action_row(
                "Apply selected zone",
                "Requires sudo",
                "Apply",
                lambda c=combo, z=zones: sh_async(
                    ["pkexec", "timedatectl", "set-timezone",
                     z[c.get_selected()]],
                    lambda r: self.toast(
                        f"tz → {z[c.get_selected()]}"
                        if r[0] == 0 else "needs sudo"),
                    timeout=10),
                css="nyx-pill-ok"))
        else:
            tz_grp.add(empty_row("Timezone list unavailable",
                                  "timedatectl list-timezones returned "
                                  "empty"))

        # World clock
        wc = Adw.PreferencesGroup(title="World clock")
        self.add_group(wc)
        for label, tz in (("New York", "America/New_York"),
                          ("London",   "Europe/London"),
                          ("Berlin",   "Europe/Berlin"),
                          ("Tokyo",    "Asia/Tokyo"),
                          ("Sydney",   "Australia/Sydney")):
            rc, t, _ = sh(["env", f"TZ={tz}", "date", "+%a %H:%M:%S"],
                          timeout=2)
            wc.add(kv_row(label, t.strip() or "?", subtitle=tz))

        self.add_pill(status_pill("ntp" if ntp_on else "manual",
                                  "ok" if ntp_on else "warn"))

    def _on_ntp(self, sw, _pspec) -> None:
        sh_async(["pkexec", "timedatectl", "set-ntp",
                  "true" if sw.get_active() else "false"],
                 lambda r: self.toast("NTP changed" if r[0] == 0
                                      else "needs sudo"),
                 timeout=10)

    def _on_rtc_local(self, sw, _pspec) -> None:
        sh_async(["pkexec", "timedatectl", "set-local-rtc",
                  "1" if sw.get_active() else "0"],
                 lambda r: self.toast("RTC mode changed" if r[0] == 0
                                      else "needs sudo"),
                 timeout=10)


# ──────────────────────────────────────────────────────────────────────
# KEYBOARD — hyprctl getoption, layout list, repeat rate
# ──────────────────────────────────────────────────────────────────────
class KeyboardPage(SectionPage):
    KEY = "keyboard"

    def build(self) -> None:
        layout_grp = Adw.PreferencesGroup(
            title="Layout",
            description="Live values from hyprctl getoption input:kb_*")
        self.add_group(layout_grp)
        if not have("hyprctl"):
            layout_grp.add(empty_row(
                "hyprctl not found",
                "This page expects Hyprland"))
            self.add_pill(status_pill("no hypr", "danger"))
            return
        for label, opt in (("Layout",   "input:kb_layout"),
                           ("Variant",  "input:kb_variant"),
                           ("Model",    "input:kb_model"),
                           ("Options",  "input:kb_options"),
                           ("Rules",    "input:kb_rules")):
            rc, out, _ = sh(["hyprctl", "getoption", opt, "-j"], timeout=2)
            try:
                val = json.loads(out or "{}").get("str", "") or "(default)"
            except Exception:
                val = "?"
            layout_grp.add(kv_row(label, val))

        # Repeat rate
        rep = Adw.PreferencesGroup(
            title="Key repeat",
            description="Repeat rate (per second) and delay before repeat "
                        "kicks in")
        self.add_group(rep)
        rc, out, _ = sh(["hyprctl", "getoption", "input:repeat_rate", "-j"],
                        timeout=2)
        try:
            cur_rate = int(json.loads(out or "{}").get("int", 25))
        except Exception:
            cur_rate = 25
        rate_row = Adw.ActionRow(title="Repeat rate",
                                 subtitle=f"current: {cur_rate}/sec")
        rate_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 5, 80, 1)
        rate_scale.set_value(cur_rate)
        rate_scale.set_size_request(220, -1)
        rate_scale.set_draw_value(True)
        debounced(rate_scale,
                  lambda v: sh_async(
                      ["hyprctl", "keyword", "input:repeat_rate",
                       str(int(v))], None, timeout=2))
        rate_row.add_suffix(rate_scale)
        rep.add(rate_row)

        rc, out, _ = sh(["hyprctl", "getoption", "input:repeat_delay", "-j"],
                        timeout=2)
        try:
            cur_delay = int(json.loads(out or "{}").get("int", 600))
        except Exception:
            cur_delay = 600
        delay_row = Adw.ActionRow(title="Repeat delay (ms)",
                                  subtitle=f"current: {cur_delay} ms")
        delay_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 100, 2000, 50)
        delay_scale.set_value(cur_delay)
        delay_scale.set_size_request(220, -1)
        delay_scale.set_draw_value(True)
        debounced(delay_scale,
                  lambda v: sh_async(
                      ["hyprctl", "keyword", "input:repeat_delay",
                       str(int(v))], None, timeout=2))
        delay_row.add_suffix(delay_scale)
        rep.add(delay_row)

        # Numlock on boot
        nl = Adw.PreferencesGroup(title="Modifier behaviour")
        self.add_group(nl)
        rc, out, _ = sh(["hyprctl", "getoption", "input:numlock_by_default",
                         "-j"], timeout=2)
        try:
            nl_on = bool(json.loads(out or "{}").get("int", 0))
        except Exception:
            nl_on = False
        nl_sw = Adw.SwitchRow(title="Numlock on by default",
                              subtitle="Hyprland sets numlock at session "
                                       "start")
        nl_sw.set_active(nl_on)
        nl_sw.connect("notify::active",
                      lambda sw, _p: sh_async(
                          ["hyprctl", "keyword",
                           "input:numlock_by_default",
                           "true" if sw.get_active() else "false"],
                          lambda r: self.toast(
                              "applied" if r[0] == 0 else "failed"),
                          timeout=2))
        nl.add(nl_sw)

        # Cheatsheet jump
        ext = Adw.PreferencesGroup(title="Shortcuts")
        self.add_group(ext)
        ext.add(action_row(
            "Open keyboard cheatsheet",
            "Full list of system & Hyprland shortcuts",
            "Open",
            lambda: fire_and_forget("nyxus-cheatsheet")))
        self.add_pill(status_pill("hypr", "ok"))


# ──────────────────────────────────────────────────────────────────────
# MOUSE — hyprctl input devices, sensitivity, natural scroll, tap-to-click
# ──────────────────────────────────────────────────────────────────────
class MousePage(SectionPage):
    KEY = "mouse"

    def build(self) -> None:
        if not have("hyprctl"):
            grp = Adw.PreferencesGroup(title="Pointer devices")
            self.add_group(grp)
            grp.add(empty_row("hyprctl not found",
                              "This page expects Hyprland"))
            self.add_pill(status_pill("no hypr", "danger"))
            return

        # Sensitivity (global input:sensitivity)
        sens_grp = Adw.PreferencesGroup(
            title="Pointer",
            description="Sensitivity is a multiplier from -1.0 (slow) to "
                        "+1.0 (fast)")
        self.add_group(sens_grp)
        rc, out, _ = sh(["hyprctl", "getoption", "input:sensitivity", "-j"],
                        timeout=2)
        try:
            cur = float(json.loads(out or "{}").get("float", 0.0))
        except Exception:
            cur = 0.0
        sens_row = Adw.ActionRow(title="Sensitivity",
                                 subtitle=f"current: {cur:+.2f}")
        scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, -1.0, 1.0, 0.05)
        scale.set_value(cur)
        scale.set_size_request(240, -1)
        scale.set_draw_value(True)
        debounced(scale,
                  lambda v: sh_async(
                      ["hyprctl", "keyword", "input:sensitivity",
                       f"{v:.2f}"], None, timeout=2))
        sens_row.add_suffix(scale)
        sens_grp.add(sens_row)

        # Accel profile
        rc, out, _ = sh(["hyprctl", "getoption",
                         "input:accel_profile", "-j"], timeout=2)
        try:
            cur_p = json.loads(out or "{}").get("str", "") or "default"
        except Exception:
            cur_p = "default"
        sl = Gtk.StringList.new(["", "flat", "adaptive"])
        prof = Adw.ComboRow(
            title="Acceleration profile",
            subtitle="empty = libinput default · flat = no accel · "
                     "adaptive = libinput accel")
        prof.set_model(sl)
        idx = {"": 0, "flat": 1, "adaptive": 2}.get(
            cur_p if cur_p in ("flat", "adaptive") else "", 0)
        prof.set_selected(idx)
        prof.connect("notify::selected",
                     lambda c, _p: sh_async(
                         ["hyprctl", "keyword", "input:accel_profile",
                          ["", "flat", "adaptive"][c.get_selected()]],
                         None, timeout=2))
        sens_grp.add(prof)

        # Natural scroll (mouse + touchpad have separate options)
        scroll_grp = Adw.PreferencesGroup(title="Scrolling")
        self.add_group(scroll_grp)
        for label, key in (("Mouse natural scroll",     "input:natural_scroll"),
                           ("Touchpad natural scroll",
                            "input:touchpad:natural_scroll")):
            rc, out, _ = sh(["hyprctl", "getoption", key, "-j"], timeout=2)
            try:
                v = bool(json.loads(out or "{}").get("int", 0))
            except Exception:
                v = False
            sw = Adw.SwitchRow(title=label, subtitle=key)
            sw.set_active(v)
            sw.connect("notify::active",
                       lambda s, _p, k=key: sh_async(
                           ["hyprctl", "keyword", k,
                            "true" if s.get_active() else "false"],
                           None, timeout=2))
            scroll_grp.add(sw)

        # Touchpad
        tp_grp = Adw.PreferencesGroup(title="Touchpad")
        self.add_group(tp_grp)
        for label, key in (
                ("Tap to click",        "input:touchpad:tap-to-click"),
                ("Two-finger scroll",   "input:touchpad:scroll_factor"),
                ("Disable while typing","input:touchpad:disable_while_typing"),
                ("Drag lock",           "input:touchpad:drag_lock")):
            rc, out, _ = sh(["hyprctl", "getoption", key, "-j"], timeout=2)
            j = {}
            try:
                j = json.loads(out or "{}")
            except Exception:
                pass
            if "int" in j:
                v = bool(j.get("int", 0))
                sw = Adw.SwitchRow(title=label, subtitle=key)
                sw.set_active(v)
                sw.connect("notify::active",
                           lambda s, _p, k=key: sh_async(
                               ["hyprctl", "keyword", k,
                                "true" if s.get_active() else "false"],
                               None, timeout=2))
                tp_grp.add(sw)
            else:
                tp_grp.add(kv_row(label,
                                  str(j.get("float", j.get("str", "?")))))

        # Live device list
        dev_grp = Adw.PreferencesGroup(
            title="Detected devices",
            description="From hyprctl devices -j")
        self.add_group(dev_grp)
        rc, out, _ = sh(["hyprctl", "devices", "-j"], timeout=3)
        try:
            d = json.loads(out)
        except Exception:
            d = {}
        for kind in ("mice", "touchpads"):
            for dev in d.get(kind, []) or []:
                dev_grp.add(kv_row(dev.get("name", "?"), kind[:-1]))
        if not d.get("mice") and not d.get("touchpads"):
            dev_grp.add(empty_row("No mice or touchpads reported", ""))
        self.add_pill(status_pill("hypr", "ok"))


# ──────────────────────────────────────────────────────────────────────
# PRIVACY — hardware presence, indicators, telemetry audit
# ──────────────────────────────────────────────────────────────────────
class PrivacyPage(SectionPage):
    KEY = "privacy"

    def build(self) -> None:
        # Hardware presence
        hw = Adw.PreferencesGroup(
            title="Capture hardware",
            description="Read-only — listed devices CAN see/hear you when "
                        "an app uses them")
        self.add_group(hw)
        # Cameras
        cams = sorted(Path("/dev").glob("video*"))
        hw.add(kv_row("Cameras", f"{len(cams)} device(s)"
                                  if cams else "none detected"))
        for c in cams:
            hw.add(kv_row(f"  {c.name}", str(c)))
        # Microphones (via pactl sources, exclude monitors)
        mics = []
        if have("pactl"):
            rc, out, _ = sh(["pactl", "list", "sources", "short"],
                            timeout=3)
            for line in out.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2 and ".monitor" not in parts[1]:
                    mics.append(parts[1])
        hw.add(kv_row("Microphones", f"{len(mics)} input(s)"
                                      if mics else "none detected"))
        for m in mics:
            hw.add(kv_row("  source", m[:60]))

        # Active capture watch (PipeWire)
        active = Adw.PreferencesGroup(
            title="Active right now",
            description="Apps currently holding a microphone or camera "
                        "stream (best-effort detection via pw-cli / lsof)")
        self.add_group(active)
        active_apps = set()
        if have("pw-cli"):
            rc, out, _ = sh(["pw-cli", "info", "all"], timeout=4)
            for m in re.finditer(
                    r'application\.name\s*=\s*"([^"]+)"', out):
                active_apps.add(m.group(1))
        if have("fuser"):
            for c in cams:
                rc, out, _ = sh(["fuser", str(c)], timeout=2)
                if rc == 0 and out.strip():
                    active.add(kv_row(f"camera {c.name}", "in use"))
        if active_apps:
            for a in sorted(active_apps)[:10]:
                active.add(kv_row("audio client", a))
        else:
            active.add(empty_row("No active capture detected",
                                  "Nothing is recording you right now"))

        # Location services
        loc = Adw.PreferencesGroup(
            title="Location",
            description="GeoClue exposes location to D-Bus consumers")
        self.add_group(loc)
        rc, out, _ = sh(["systemctl", "is-active", "geoclue.service"],
                        timeout=2)
        loc.add(kv_row("geoclue.service", out.strip() or "?"))
        rc, out, _ = sh(["systemctl", "is-enabled", "geoclue.service"],
                        timeout=2)
        loc.add(kv_row("Auto-start at boot", out.strip() or "?"))
        loc.add(action_row(
            "Disable location service",
            "Stops geoclue and prevents auto-start",
            "Disable",
            lambda: sh_async(
                ["pkexec", "systemctl", "disable", "--now",
                 "geoclue.service"],
                lambda r: self.toast("disabled" if r[0] == 0
                                     else "failed / needs sudo"),
                timeout=10),
            css="nyx-pill-warn"))

        # Telemetry audit
        tel = Adw.PreferencesGroup(
            title="Telemetry & opt-outs",
            description="NYXUS itself ships zero telemetry. Listed values "
                        "show common third-party env opt-outs.")
        self.add_group(tel)
        for var, on_val in (("DO_NOT_TRACK",        "1"),
                            ("DOTNET_CLI_TELEMETRY_OPTOUT", "1"),
                            ("HOMEBREW_NO_ANALYTICS",      "1"),
                            ("NEXT_TELEMETRY_DISABLED",    "1"),
                            ("GATSBY_TELEMETRY_DISABLED",  "1"),
                            ("VUE_CLI_TELEMETRY_DISABLED", "1")):
            v = os.environ.get(var, "")
            ok = (v == on_val)
            tel.add(kv_row(var, "opted out" if ok else f"unset ({v or '∅'})"))
        self.add_pill(status_pill(f"{len(cams)} cam · {len(mics)} mic",
                                  "ok"))


# ──────────────────────────────────────────────────────────────────────
# APPS — installed count, default mime apps, autostart
# ──────────────────────────────────────────────────────────────────────
class AppsPage(SectionPage):
    KEY = "apps"

    def build(self) -> None:
        # Counts
        cnt = Adw.PreferencesGroup(title="Installed packages")
        self.add_group(cnt)
        if have("pacman"):
            rc, out, _ = sh(["pacman", "-Qq"], timeout=4)
            n_total = len(out.splitlines()) if rc == 0 else 0
            rc, out, _ = sh(["pacman", "-Qqe"], timeout=4)
            n_explicit = len(out.splitlines()) if rc == 0 else 0
            rc, out, _ = sh(["pacman", "-Qqm"], timeout=4)
            n_foreign = len(out.splitlines()) if rc == 0 else 0
            cnt.add(kv_row("Total", str(n_total)))
            cnt.add(kv_row("Explicitly installed", str(n_explicit)))
            cnt.add(kv_row("Foreign / AUR / local", str(n_foreign)))
        else:
            cnt.add(empty_row("pacman not available", ""))

        # GUI apps
        gui = Adw.PreferencesGroup(
            title="GUI applications",
            description="Apps that ship a .desktop file in the standard "
                        "search paths")
        self.add_group(gui)
        desktops = []
        for base in ("/usr/share/applications",
                     str(Path.home() / ".local/share/applications")):
            p = Path(base)
            if p.exists():
                desktops.extend(p.glob("*.desktop"))
        gui.add(kv_row("Desktop entries found", str(len(desktops))))
        gui.add(action_row(
            "Open application launcher",
            "rofi / wofi / fuzzel — your configured launcher",
            "Open",
            lambda: fire_and_forget(
                "fuzzel" if have("fuzzel") else
                ("rofi -show drun" if have("rofi") else "wofi --show drun"))))

        # Default apps (xdg-mime)
        defs = Adw.PreferencesGroup(
            title="Default apps",
            description="Resolved from xdg-mime query default")
        self.add_group(defs)
        if have("xdg-mime"):
            for label, mime in (
                    ("Web browser",      "x-scheme-handler/https"),
                    ("Email",            "x-scheme-handler/mailto"),
                    ("Terminal",         "x-scheme-handler/terminal"),
                    ("Plain text",       "text/plain"),
                    ("PDF",              "application/pdf"),
                    ("Image (PNG)",      "image/png"),
                    ("Audio (FLAC)",     "audio/flac"),
                    ("Video (MP4)",      "video/mp4")):
                rc, out, _ = sh(["xdg-mime", "query", "default", mime],
                                timeout=2)
                defs.add(kv_row(label,
                                (out.strip() or "(unset)").replace(
                                    ".desktop", "")))
        else:
            defs.add(empty_row("xdg-mime not installed",
                                "Install xdg-utils"))

        # Autostart
        au = Adw.PreferencesGroup(
            title="Autostart",
            description="Anything in ~/.config/autostart starts at session "
                        "login")
        self.add_group(au)
        as_dir = Path.home() / ".config" / "autostart"
        items = sorted(as_dir.glob("*.desktop")) if as_dir.exists() else []
        if not items:
            au.add(empty_row("No autostart entries",
                              "Drop a .desktop file into "
                              "~/.config/autostart to add one"))
        for it in items:
            au.add(kv_row(it.stem, str(it)))
        self.add_pill(status_pill(f"{len(desktops)} apps", "ok"))


# ──────────────────────────────────────────────────────────────────────
# STORAGE — df / lsblk / smartctl, pacman cache, journal
# ──────────────────────────────────────────────────────────────────────
class StoragePage(SectionPage):
    KEY = "storage"

    def build(self) -> None:
        self.mounts_grp = Adw.PreferencesGroup(
            title="Mounts",
            description="Filesystem usage from df -h (excluding tmpfs/devfs)")
        self.add_group(self.mounts_grp)
        self.disks_grp = Adw.PreferencesGroup(
            title="Block devices",
            description="Physical disks and partitions from lsblk")
        self.add_group(self.disks_grp)
        self.smart_grp = Adw.PreferencesGroup(
            title="SMART health",
            description="Requires smartmontools and root for full data")
        self.add_group(self.smart_grp)

        # Cleanup actions
        clean = Adw.PreferencesGroup(title="Cleanup")
        self.add_group(clean)
        if have("paccache"):
            clean.add(action_row(
                "Trim pacman cache (keep latest 2)",
                "paccache -rk2 — frees /var/cache/pacman/pkg",
                "Trim",
                lambda: sh_async(
                    ["pkexec", "paccache", "-rk2"],
                    lambda r: (self.toast("trimmed" if r[0] == 0
                                          else "failed"),
                               self._render()), timeout=30)))
        else:
            clean.add(empty_row("paccache not installed",
                                "Install pacman-contrib"))
        clean.add(action_row(
            "Vacuum journal (keep 7 days)",
            "journalctl --vacuum-time=7d",
            "Vacuum",
            lambda: sh_async(
                ["pkexec", "journalctl", "--vacuum-time=7d"],
                lambda r: self.toast("vacuumed" if r[0] == 0 else "failed"),
                timeout=30)))
        if have("baobab"):
            clean.add(action_row(
                "Open disk usage analyzer",
                "GNOME baobab — visualize what's using space",
                "Open",
                lambda: fire_and_forget("baobab")))

        self._render()
        self.add_pill(status_pill("live", "ok"))
        self.schedule_refresh(15000, self._tick)

    def _tick(self) -> bool:
        self._render()
        return True

    def _render(self) -> None:
        _clear_group(self.mounts_grp)
        rc, out, _ = sh(
            ["df", "-h", "--output=target,fstype,size,used,avail,pcent",
             "-x", "tmpfs", "-x", "devtmpfs", "-x", "squashfs",
             "-x", "overlay"],
            timeout=4)
        lines = out.splitlines()[1:] if out else []
        if not lines:
            self.mounts_grp.add(empty_row("No mounts found", ""))
        for ln in lines[:20]:
            cols = ln.split()
            if len(cols) < 6:
                continue
            target, fs, size, used, avail, pcent = cols[0], cols[1], \
                cols[2], cols[3], cols[4], cols[5]
            row = Adw.ActionRow(
                title=target,
                subtitle=f"{fs} · {used}/{size} used · {avail} free")
            try:
                pct = int(pcent.rstrip("%"))
            except ValueError:
                pct = 0
            tag_kind = "ok" if pct < 75 else ("warn" if pct < 90
                                              else "danger")
            row.add_suffix(status_pill(pcent, tag_kind))
            self.mounts_grp.add(row)

        # Block devices
        _clear_group(self.disks_grp)
        rc, out, _ = sh(["lsblk", "-d", "-o", "NAME,SIZE,MODEL,ROTA",
                         "-n"], timeout=3)
        lines = out.splitlines() if out else []
        if not lines:
            self.disks_grp.add(empty_row("No block devices found", ""))
        for ln in lines:
            parts = ln.split(None, 3)
            if len(parts) < 2:
                continue
            name = parts[0]
            size = parts[1]
            model = parts[2] if len(parts) >= 3 else ""
            rota = parts[3] if len(parts) >= 4 else "?"
            kind = "HDD" if rota.strip() == "1" else "SSD"
            self.disks_grp.add(kv_row(
                f"/dev/{name}", f"{size} · {kind}",
                subtitle=model.strip() if model.strip() else None))

        # SMART
        _clear_group(self.smart_grp)
        if not have("smartctl"):
            self.smart_grp.add(empty_row(
                "smartctl not installed",
                "Install smartmontools to view SMART status"))
            return
        # Disks already enumerated above
        for ln in lines:
            parts = ln.split(None, 3)
            if len(parts) < 1:
                continue
            name = parts[0]
            dev = f"/dev/{name}"
            rc, out, _ = sh(["smartctl", "-H", dev], timeout=4)
            status = "?"
            for line in out.splitlines():
                if "overall-health" in line.lower():
                    status = line.split(":", 1)[-1].strip()
                    break
            kind = "ok" if "PASSED" in status.upper() else "warn"
            row = Adw.ActionRow(title=dev, subtitle=status)
            row.add_suffix(status_pill(
                "PASS" if "PASSED" in status.upper() else "?", kind))
            self.smart_grp.add(row)


# ──────────────────────────────────────────────────────────────────────
# UPDATES — checkupdates, AUR helpers
# ──────────────────────────────────────────────────────────────────────
class UpdatesPage(SectionPage):
    KEY = "updates"

    def build(self) -> None:
        self.repo_grp = Adw.PreferencesGroup(
            title="Official repositories",
            description="Pending updates from pacman (queried via "
                        "checkupdates — does not need root)")
        self.add_group(self.repo_grp)
        self.aur_grp = Adw.PreferencesGroup(
            title="AUR / foreign packages",
            description="Pending updates for packages installed via paru, "
                        "yay, etc.")
        self.add_group(self.aur_grp)

        # Reboot required
        rb_grp = Adw.PreferencesGroup(title="Reboot")
        self.add_group(rb_grp)
        running_kernel = sh(["uname", "-r"], timeout=2)[1].strip()
        rc, installed_kernel, _ = sh(
            ["pacman", "-Q", "linux"], timeout=2)
        installed_kernel = installed_kernel.strip().split(" ")[-1] \
            if installed_kernel else "?"
        kernel_match = installed_kernel.split("-")[0] in running_kernel
        rb_grp.add(kv_row("Running kernel", running_kernel))
        rb_grp.add(kv_row("Installed kernel", installed_kernel))
        if not kernel_match:
            rb_grp.add(empty_row(
                "Reboot recommended",
                "Installed kernel differs from running kernel — restart "
                "to load it"))

        # Tools
        tools = Adw.PreferencesGroup(title="Tools")
        self.add_group(tools)
        tools.add(action_row(
            "Run full system upgrade",
            "Opens a terminal with sudo pacman -Syu",
            "Run",
            lambda: open_terminal("sudo pacman -Syu", self.win),
            css="nyx-pill-ok"))
        for helper in ("paru", "yay"):
            if have(helper):
                tools.add(action_row(
                    f"AUR upgrade ({helper})",
                    f"{helper} -Syu — includes AUR & repos",
                    "Run",
                    lambda h=helper: open_terminal(f"{h} -Syu", self.win)))
        tools.add(action_row(
            "Refresh mirror list",
            "reflector --country US --age 6 --sort rate "
            "--save /etc/pacman.d/mirrorlist",
            "Refresh",
            lambda: open_terminal(
                "sudo reflector --age 6 --sort rate "
                "--save /etc/pacman.d/mirrorlist",
                self.win)) if have("reflector") else None)

        self._render()
        self.add_pill(status_pill("live", "ok"))
        self.schedule_refresh(60000, self._tick)

    def _tick(self) -> bool:
        self._render()
        return True

    def _render(self) -> None:
        _clear_group(self.repo_grp)
        if not have("checkupdates"):
            self.repo_grp.add(empty_row(
                "checkupdates not installed",
                "Install pacman-contrib to query pending updates without "
                "needing root"))
        else:
            sh_async(["checkupdates"], self._on_repo, timeout=30)

        _clear_group(self.aur_grp)
        helper = "paru" if have("paru") else ("yay" if have("yay") else "")
        if not helper:
            self.aur_grp.add(empty_row(
                "No AUR helper installed",
                "Install paru or yay to track AUR updates"))
            return
        sh_async([helper, "-Qua"], self._on_aur, timeout=60)

    def _on_repo(self, result) -> None:
        rc, out, _ = result
        _clear_group(self.repo_grp)
        if rc == 2:  # checkupdates exits 2 when no updates
            self.repo_grp.add(kv_row("Status", "up to date"))
            return
        lines = [l for l in out.splitlines() if l.strip()]
        self.repo_grp.add(kv_row("Pending", str(len(lines))))
        for line in lines[:25]:
            parts = line.split()
            if len(parts) >= 4:
                self.repo_grp.add(kv_row(
                    parts[0], f"{parts[1]} → {parts[3]}"))

    def _on_aur(self, result) -> None:
        rc, out, _ = result
        _clear_group(self.aur_grp)
        lines = [l for l in out.splitlines() if l.strip()]
        if not lines:
            self.aur_grp.add(kv_row("Status", "up to date"))
            return
        self.aur_grp.add(kv_row("Pending", str(len(lines))))
        for line in lines[:25]:
            parts = line.split()
            if len(parts) >= 4:
                self.aur_grp.add(kv_row(
                    parts[0], f"{parts[1]} → {parts[3]}"))


# ──────────────────────────────────────────────────────────────────────
# ACCESSIBILITY — text scale (gsettings/hyprctl), reduced motion
# ──────────────────────────────────────────────────────────────────────
class AccessibilityPage(SectionPage):
    KEY = "accessibility"

    def build(self) -> None:
        text = Adw.PreferencesGroup(
            title="Reading",
            description="Helps visibility on dense panels and small screens")
        self.add_group(text)

        # Text scale (delegates to Appearance — we mirror it here for
        # discoverability, just like macOS shows display zoom in two places)
        prefs = load_prefs()
        cur_scale = float(prefs.get("font_scale", 1.0))
        scale_row = Adw.ActionRow(
            title="Text scale",
            subtitle=f"current: {cur_scale:.2f}× — also editable in "
                     f"Appearance")
        sc = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, 0.8, 1.6, 0.05)
        sc.set_value(cur_scale)
        sc.set_size_request(220, -1)
        sc.set_draw_value(True)
        debounced(sc, lambda v: self._on_scale_value(v))
        scale_row.add_suffix(sc)
        text.add(scale_row)

        # Cursor size
        rc, out, _ = sh(["hyprctl", "getoption", "cursor:size", "-j"],
                        timeout=2) if have("hyprctl") else (1, "", "")
        try:
            cur_csz = int(json.loads(out or "{}").get("int", 24))
        except Exception:
            cur_csz = 24
        if have("hyprctl"):
            csz_row = Adw.ActionRow(title="Cursor size",
                                    subtitle=f"current: {cur_csz} px")
            csz = Gtk.Scale.new_with_range(
                Gtk.Orientation.HORIZONTAL, 16, 64, 2)
            csz.set_value(cur_csz)
            csz.set_size_request(220, -1)
            csz.set_draw_value(True)
            debounced(csz,
                      lambda v: sh_async(
                          ["hyprctl", "keyword", "cursor:size",
                           str(int(v))], None, timeout=2))
            csz_row.add_suffix(csz)
            text.add(csz_row)

        # Motion (mirrors Appearance toggle)
        motion = Adw.PreferencesGroup(
            title="Motion",
            description="Reduce or disable motion for vestibular comfort")
        self.add_group(motion)
        if have("hyprctl"):
            rc, out, _ = sh(["hyprctl", "getoption",
                             "animations:enabled", "-j"], timeout=2)
            try:
                anims_on = bool(json.loads(out or "{}").get("int", 1))
            except Exception:
                anims_on = True
            sw = Adw.SwitchRow(title="Animations enabled",
                               subtitle="Window open/close, workspace "
                                        "transitions, layer slides")
            sw.set_active(anims_on)
            sw.connect("notify::active",
                       lambda s, _p: sh_async(
                           ["hyprctl", "keyword", "animations:enabled",
                            "true" if s.get_active() else "false"],
                           lambda r: self.toast(
                               "applied" if r[0] == 0 else "failed"),
                           timeout=2))
            motion.add(sw)
        else:
            motion.add(empty_row("hyprctl not found",
                                  "Animation toggle requires Hyprland"))

        # High contrast — locked off per DARK MIRROR contract
        contrast = Adw.PreferencesGroup(
            title="Contrast",
            description="DARK MIRROR locks the visual theme; system high "
                        "contrast is intentionally disabled. Use text "
                        "scale and cursor size instead.")
        self.add_group(contrast)
        contrast.add(kv_row("System theme", "DARK MIRROR (locked)"))

        # Pointers to assistive tools
        tools = Adw.PreferencesGroup(title="Assistive tools")
        self.add_group(tools)
        for label, bin_ in (("Screen magnifier (magnus)", "magnus"),
                            ("On-screen keyboard (wvkbd)", "wvkbd"),
                            ("Screen reader (orca)",       "orca")):
            if have(bin_):
                tools.add(action_row(label, bin_, "Launch",
                                      lambda b=bin_: fire_and_forget(b)))
            else:
                tools.add(empty_row(label,
                                     f"{bin_} not installed"))
        self.add_pill(status_pill("a11y", "ok"))

    def _on_scale_value(self, raw: float) -> None:
        v = round(raw, 2)
        prefs = load_prefs()
        prefs["font_scale"] = v
        save_prefs(prefs)
        self.toast(f"text scale → {v:.2f}× (sign out to apply fully)")


# ──────────────────────────────────────────────────────────────────────
# USERS — current user, groups, password change
# ──────────────────────────────────────────────────────────────────────
class UsersPage(SectionPage):
    KEY = "users"

    def build(self) -> None:
        # Current user
        cur = Adw.PreferencesGroup(title="Current account")
        self.add_group(cur)
        rc, user, _ = sh(["whoami"], timeout=2)
        user = user.strip()
        cur.add(kv_row("Username", user))
        rc, fn, _ = sh(["getent", "passwd", user], timeout=2)
        if rc == 0 and fn.strip():
            parts = fn.strip().split(":")
            if len(parts) >= 7:
                cur.add(kv_row("UID", parts[2]))
                cur.add(kv_row("Primary group", parts[3]))
                cur.add(kv_row("Full name (GECOS)", parts[4] or "(unset)"))
                cur.add(kv_row("Home", parts[5]))
                cur.add(kv_row("Shell", parts[6]))
        rc, groups, _ = sh(["groups"], timeout=2)
        cur.add(kv_row("Groups",
                       groups.strip().split(":")[-1].strip()
                       if ":" in groups else groups.strip()))
        cur.add(action_row(
            "Change password",
            "Opens a terminal with passwd",
            "Change",
            lambda: open_terminal("passwd", self.win)))
        cur.add(action_row(
            "Edit shell",
            "Opens chsh in a terminal — pick from /etc/shells",
            "Edit",
            lambda: open_terminal("chsh", self.win)))

        # Other users on the system
        oth = Adw.PreferencesGroup(
            title="Other accounts",
            description="Local accounts with UID ≥ 1000 (excluding nobody)")
        self.add_group(oth)
        rc, out, _ = sh(["getent", "passwd"], timeout=3)
        others = []
        for line in out.splitlines():
            p = line.split(":")
            if len(p) < 7:
                continue
            try:
                uid = int(p[2])
            except ValueError:
                continue
            if uid >= 1000 and p[0] != "nobody" and p[0] != user:
                others.append((p[0], p[2], p[6]))
        if not others:
            oth.add(empty_row("No other user accounts",
                               "This system has only the current user"))
        for name, uid, shell in others[:10]:
            oth.add(kv_row(name, f"uid {uid} · {shell}"))

        # Add user (delegates to terminal — useradd needs root)
        admin = Adw.PreferencesGroup(
            title="Account management",
            description="Account creation, removal, and group editing "
                        "require root and are best done in a terminal")
        self.add_group(admin)
        admin.add(action_row(
            "Add a new user",
            "Opens useradd interactive helper in a terminal",
            "Add",
            lambda: open_terminal(
                "echo 'Run: sudo useradd -m -G wheel,audio,video,input "
                "-s /bin/bash USERNAME && sudo passwd USERNAME'; "
                "$SHELL", self.win)))
        admin.add(action_row(
            "Edit /etc/sudoers",
            "Opens sudo visudo — safest way to change sudo rules",
            "Open",
            lambda: open_terminal("sudo visudo", self.win),
            css="nyx-pill-warn"))

        # Sessions
        ses = Adw.PreferencesGroup(title="Active sessions")
        self.add_group(ses)
        rc, out, _ = sh(["loginctl", "list-sessions", "--no-legend"],
                        timeout=3)
        rows = [l for l in out.splitlines() if l.strip()]
        if not rows:
            ses.add(empty_row("No active sessions reported", ""))
        for r in rows[:8]:
            parts = r.split()
            if len(parts) >= 4:
                ses.add(kv_row(parts[2],
                               f"session {parts[0]} · seat {parts[3]}"))

        self.add_pill(status_pill(user, "ok"))


# ──────────────────────────────────────────────────────────────────────
# Helper: clear all rows from a PreferencesGroup. libadwaita 1.4+
# provides .remove(); we keep our own list for portability.
# ──────────────────────────────────────────────────────────────────────
def _clear_group(grp: Adw.PreferencesGroup) -> None:
    if not hasattr(grp, "_nyx_rows"):
        grp._nyx_rows = []
    # Capture children added via .add() — track on the next .add() call
    # by replacing it once. Idempotent.
    if not hasattr(grp, "_nyx_patched"):
        original_add = grp.add
        def tracked_add(child):
            grp._nyx_rows.append(child)
            return original_add(child)
        grp.add = tracked_add  # type: ignore[assignment]
        grp._nyx_patched = True
    for child in list(grp._nyx_rows):
        try:
            grp.remove(child)
        except Exception:
            pass
    grp._nyx_rows = []


# ──────────────────────────────────────────────────────────────────────
# Tier-1: APPEARANCE
# ──────────────────────────────────────────────────────────────────────
class AppearancePage(SectionPage):
    KEY = "appearance"

    def build(self) -> None:
        prefs = self.win.prefs

        # ── Theme variant (locked to Dark Mirror) ──────────────────────
        g_theme = Adw.PreferencesGroup(title="Theme")
        row = Adw.ActionRow(title="Variant",
                            subtitle="DARK MIRROR — locked by NYXUS design contract")
        row.add_suffix(status_pill("DARK MIRROR", "ok"))
        g_theme.add(row)
        self.add_group(g_theme)

        # ── Wallpaper grid ────────────────────────────────────────────
        g_wall = Adw.PreferencesGroup(
            title="Wallpaper",
            description="Click a wallpaper to apply it system-wide via swaybg.")
        wall_row = Adw.PreferencesRow()
        wall_row.set_activatable(False)
        wall_row.set_selectable(False)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.NEVER)
        scroll.set_min_content_height(220)
        flow = Gtk.FlowBox()
        flow.set_valign(Gtk.Align.START)
        flow.set_max_children_per_line(6)
        flow.set_min_children_per_line(2)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_homogeneous(True)
        flow.set_column_spacing(10)
        flow.set_row_spacing(10)
        flow.set_margin_start(8)
        flow.set_margin_end(8)
        flow.set_margin_top(8)
        flow.set_margin_bottom(8)

        walls: List[Path] = []
        for d in (WALLS_USR, WALLS_SYS):
            if d.exists():
                walls.extend(sorted(p for p in d.iterdir()
                                    if p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")))

        current = prefs.get("wallpaper", "")

        if not walls:
            empty = Gtk.Label(
                label="No wallpapers installed.\n"
                      "Drop PNG/JPG files into ~/Pictures/Wallpapers or "
                      "/usr/share/backgrounds/nyxus.")
            empty.set_xalign(0)
            empty.set_wrap(True)
            empty.add_css_class("nyx-wip-body")
            flow.append(empty)
        else:
            for wp in walls[:30]:  # cap for perf
                btn = Gtk.Button()
                btn.add_css_class("nyx-wall-tile")
                if str(wp) == current:
                    btn.add_css_class("selected")
                pic = Gtk.Picture.new_for_filename(str(wp))
                pic.set_content_fit(Gtk.ContentFit.COVER)
                pic.set_size_request(180, 110)
                btn.set_child(pic)
                btn.connect("clicked", self._on_wallpaper, wp)
                flow.append(btn)

        scroll.set_child(flow)
        wall_row.set_child(scroll)
        g_wall.add(wall_row)
        self.add_group(g_wall)

        # ── Font scale ────────────────────────────────────────────────
        g_font = Adw.PreferencesGroup(
            title="Text size",
            description="Affects all NYXUS apps. Restart apps to apply.")
        scale_row = Adw.ActionRow(title="UI scale")
        adj = Gtk.Adjustment(value=prefs.get("font_scale", 1.0),
                             lower=0.85, upper=1.40, step_increment=0.05)
        scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                          adjustment=adj)
        scale.set_size_request(220, -1)
        scale.set_draw_value(True)
        scale.set_value_pos(Gtk.PositionType.RIGHT)
        scale.set_digits(2)
        for v in (0.85, 1.00, 1.15, 1.30):
            scale.add_mark(v, Gtk.PositionType.BOTTOM, None)
        scale.connect("value-changed", self._on_font_scale)
        scale_row.add_suffix(scale)
        g_font.add(scale_row)
        self.add_group(g_font)

        # ── Animations ────────────────────────────────────────────────
        g_anim = Adw.PreferencesGroup(title="Motion")
        anim_row = Adw.SwitchRow(title="Enable Hyprland animations",
                                 subtitle="Disable for snappier feel on slow GPUs")
        anim_row.set_active(prefs.get("animations", True))
        anim_row.connect("notify::active", self._on_anim_toggle)
        g_anim.add(anim_row)
        self.add_group(g_anim)

        # Status pill: which compositor backends are available
        backends = []
        if have("swaybg"):     backends.append("swaybg")
        if have("hyprctl"):    backends.append("hyprctl")
        kind = "ok" if backends else "warn"
        msg  = " · ".join(backends) if backends else "no compositor tools"
        self.add_pill(status_pill(msg, kind))

    def _on_wallpaper(self, btn: Gtk.Button, path: Path) -> None:
        # Persist
        self.win.prefs["wallpaper"] = str(path)
        save_prefs(self.win.prefs)
        # Visually mark selection
        flow = btn.get_parent()
        if isinstance(flow, Gtk.FlowBox):
            child = flow.get_first_child()
            while child:
                inner = child.get_first_child()
                if isinstance(inner, Gtk.Button):
                    inner.remove_css_class("selected")
                child = child.get_next_sibling()
        btn.add_css_class("selected")
        # Apply via swaybg (matches Hyprland exec-once + nyxus_install.sh
        # reload logic — single backend across the whole system, audit A7).
        # swaybg has no IPC; replace the running daemon with a fresh one
        # pointed at the new path. `pkill -x` is exact-match so we don't
        # nuke unrelated processes.
        if have("swaybg"):
            sh_async(
                ["sh", "-c",
                 f"pkill -x swaybg 2>/dev/null; "
                 f"swaybg -i {str(path)!r} -m fill -c '#000000' >/dev/null 2>&1 &"],
                lambda r: self.toast(
                    "wallpaper applied" if r[0] == 0
                    else f"swaybg failed: {r[2][:60]}"))
        else:
            self.toast("swaybg not installed — saved selection only")

    def _on_font_scale(self, scale: Gtk.Scale) -> None:
        v = round(scale.get_value(), 2)
        self.win.prefs["font_scale"] = v
        save_prefs(self.win.prefs)

    def _on_anim_toggle(self, row: Adw.SwitchRow, _pspec) -> None:
        on = row.get_active()
        self.win.prefs["animations"] = on
        save_prefs(self.win.prefs)
        if have("hyprctl"):
            sh_async(["hyprctl", "keyword", "animations:enabled",
                      "1" if on else "0"],
                     lambda r: self.toast(
                         f"animations {'on' if on else 'off'}"))


# ──────────────────────────────────────────────────────────────────────
# Tier-1: NETWORK
# ──────────────────────────────────────────────────────────────────────
class NetworkPage(SectionPage):
    KEY = "network"

    def build(self) -> None:
        if not have("nmcli"):
            grp = Adw.PreferencesGroup(title="NetworkManager not available")
            grp.add(Adw.ActionRow(
                title="nmcli not installed",
                subtitle="Install networkmanager to manage Wi-Fi from here."))
            self.add_group(grp)
            self.add_pill(status_pill("nmcli missing", "danger"))
            return

        # ── Wi-Fi ─────────────────────────────────────────────────────
        self.wifi_group = Adw.PreferencesGroup(title="Wi-Fi")
        self.add_group(self.wifi_group)

        # ── Ethernet ──────────────────────────────────────────────────
        self.eth_group = Adw.PreferencesGroup(title="Ethernet")
        self.add_group(self.eth_group)

        # ── VPN ───────────────────────────────────────────────────────
        self.vpn_group = Adw.PreferencesGroup(title="VPN connections")
        self.add_group(self.vpn_group)

        # ── DNS ───────────────────────────────────────────────────────
        self.dns_group = Adw.PreferencesGroup(title="DNS")
        self.add_group(self.dns_group)

        self._render()
        self.schedule_refresh(8000, self._tick)

    # ── live polling tick ─────────────────────────────────────────────
    def _tick(self) -> bool:
        self._render()
        return True  # keep going

    def _clear_group(self, grp: Adw.PreferencesGroup) -> None:
        # Adw.PreferencesGroup doesn't expose remove(); the supported way is
        # to track and dispose rows. We manage rows in _rows lists per group.
        for row in getattr(grp, "_rows", []):
            grp.remove(row)
        grp._rows = []  # type: ignore[attr-defined]

    def _track(self, grp: Adw.PreferencesGroup, row: Gtk.Widget) -> None:
        grp.add(row)
        if not hasattr(grp, "_rows"):
            grp._rows = []  # type: ignore[attr-defined]
        grp._rows.append(row)  # type: ignore[attr-defined]

    def _render(self) -> None:
        for g in (self.wifi_group, self.eth_group, self.vpn_group, self.dns_group):
            self._clear_group(g)
        self.clear_pills()

        # Radio + scan + add network
        rc, out, _ = sh("nmcli radio wifi")
        wifi_on = "enabled" in out
        radio = Adw.SwitchRow(title="Wi-Fi", subtitle="Toggle the wireless radio")
        radio.set_active(wifi_on)
        radio.connect("notify::active", self._on_radio_toggle)
        self._track(self.wifi_group, radio)

        # Active connection summary
        rc, act_out, _ = sh("nmcli -t -f NAME,TYPE,DEVICE connection show --active")
        active_wifi = ""
        for line in act_out.splitlines():
            parts = line.split(":")
            if len(parts) >= 2 and parts[1] in ("802-11-wireless", "wifi"):
                active_wifi = parts[0]
                break
        if active_wifi:
            self.add_pill(status_pill(f"on  {active_wifi}", "ok"))
        elif wifi_on:
            self.add_pill(status_pill("on  unconnected", "warn"))
        else:
            self.add_pill(status_pill("off", "warn"))

        # Available networks
        rc, scan_out, _ = sh("nmcli -t -f IN-USE,SSID,SIGNAL,SECURITY dev wifi")
        seen = set()
        nets = []
        if rc == 0:
            for line in scan_out.splitlines():
                parts = line.split(":")
                if len(parts) < 4:
                    continue
                inuse, ssid, sig, sec = parts[0], parts[1], parts[2], parts[3] or "open"
                if not ssid or ssid in seen:
                    continue
                seen.add(ssid)
                try:
                    nets.append((inuse.strip() == "*", ssid, int(sig or "0"), sec))
                except ValueError:
                    nets.append((inuse.strip() == "*", ssid, 0, sec))
        nets.sort(key=lambda n: (-1 if n[0] else 0, -n[2]))

        if not nets:
            # §9 empty state
            row = Adw.ActionRow(title="No networks in range",
                                subtitle="Try moving closer to a router or pressing Scan.")
            self._track(self.wifi_group, row)
        else:
            for active, ssid, sig, sec in nets[:12]:
                bars = self._signal_glyph(sig)
                lock = " \uf023" if sec.lower() not in ("", "open", "--") else ""
                row = Adw.ActionRow(title=ssid,
                                    subtitle=f"{bars}  {sig}%   {sec}{lock}")
                if active:
                    row.add_suffix(status_pill("connected", "ok"))
                else:
                    btn = Gtk.Button(label="Connect")
                    btn.set_valign(Gtk.Align.CENTER)
                    btn.connect("clicked",
                                lambda _b, s=ssid, sc=sec: self._connect_wifi(s, sc))
                    row.add_suffix(btn)
                self._track(self.wifi_group, row)

        scan_row = Adw.ActionRow(title="Rescan",
                                 subtitle="Force a new wireless scan")
        scan_btn = Gtk.Button(label="Scan now")
        scan_btn.set_valign(Gtk.Align.CENTER)
        scan_btn.connect("clicked", self._on_scan)
        scan_row.add_suffix(scan_btn)
        self._track(self.wifi_group, scan_row)

        # Ethernet
        rc, dev_out, _ = sh("nmcli -t -f DEVICE,TYPE,STATE device")
        eth_seen = False
        for line in dev_out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] == "ethernet":
                eth_seen = True
                state = parts[2]
                kind = "ok" if state == "connected" else "warn"
                row = Adw.ActionRow(title=parts[0], subtitle=f"state · {state}")
                row.add_suffix(status_pill(state, kind))
                self._track(self.eth_group, row)
        if not eth_seen:
            row = Adw.ActionRow(title="No Ethernet interfaces",
                                subtitle="Plug in an Ethernet cable to see this section populate.")
            self._track(self.eth_group, row)

        # VPN
        rc, conn_out, _ = sh("nmcli -t -f NAME,TYPE,STATE connection")
        any_vpn = False
        for line in conn_out.splitlines():
            parts = line.split(":")
            if len(parts) >= 3 and parts[1] in ("vpn", "wireguard"):
                any_vpn = True
                name = parts[0]
                active = "activated" in parts[2]
                row = Adw.ActionRow(title=name, subtitle=parts[1])
                row.add_suffix(status_pill(
                    "connected" if active else "off",
                    "ok" if active else "warn"))
                btn = Gtk.Button(label="Disconnect" if active else "Connect")
                if active:
                    btn.add_css_class("destructive-action")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked",
                            lambda _b, n=name, up=not active: self._toggle_vpn(n, up))
                row.add_suffix(btn)
                self._track(self.vpn_group, row)
        if not any_vpn:
            # §9 empty state
            row = Adw.ActionRow(
                title="No VPN connections configured",
                subtitle="Add one with nmcli connection add type wireguard …")
            self._track(self.vpn_group, row)

        # DNS
        rc, dns_out, _ = sh("resolvectl status", timeout=2)
        active_dns = ""
        for line in dns_out.splitlines():
            ln = line.strip()
            if ln.startswith("Current DNS Server:"):
                active_dns = ln.split(":", 1)[1].strip()
                break
            if ln.startswith("DNS Servers:") and not active_dns:
                active_dns = ln.split(":", 1)[1].strip()
        row = Adw.ActionRow(title="Active DNS server",
                            subtitle=active_dns or "unknown")
        self._track(self.dns_group, row)
        ping_row = Adw.ActionRow(title="Connectivity test",
                                 subtitle="Pings 1.1.1.1 three times")
        ping_btn = Gtk.Button(label="Run ping")
        ping_btn.set_valign(Gtk.Align.CENTER)
        ping_btn.connect("clicked", self._on_ping)
        ping_row.add_suffix(ping_btn)
        self._track(self.dns_group, ping_row)

    # ── helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _signal_glyph(sig: int) -> str:
        # Five steps: 0–20 / 21–40 / 41–60 / 61–80 / 81–100
        bars = ["▁", "▂", "▄", "▆", "█"]
        idx = min(4, max(0, sig // 20))
        return "".join(b if i <= idx else "·" for i, b in enumerate(bars))

    def _on_radio_toggle(self, row: Adw.SwitchRow, _pspec) -> None:
        on = row.get_active()
        sh_async(f"nmcli radio wifi {'on' if on else 'off'}",
                 lambda r: (self.toast(f"wifi {'on' if on else 'off'}"),
                            self._render()))

    def _on_scan(self, _btn: Gtk.Button) -> None:
        sh_async("nmcli dev wifi rescan",
                 lambda r: (self.toast("scanned"), self._render()),
                 timeout=10)

    def _connect_wifi(self, ssid: str, sec: str) -> None:
        secured = sec.lower() not in ("", "open", "--")
        if not secured:
            # List form — never f-string the SSID into a shell command;
            # an SSID like "; reboot ;" would otherwise execute.
            sh_async(["nmcli", "dev", "wifi", "connect", ssid],
                     lambda r: (self.toast(
                         f"connected to {ssid}" if r[0] == 0
                         else f"connect failed: {r[2][:60]}"),
                         self._render()),
                     timeout=20)
            return
        # Password prompt
        dlg = Adw.MessageDialog.new(self.win, f"Connect to {ssid}",
                                    "Enter the network password.")
        entry = Gtk.PasswordEntry()
        entry.set_show_peek_icon(True)
        entry.set_margin_top(8)
        entry.set_margin_bottom(8)
        entry.set_margin_start(8)
        entry.set_margin_end(8)
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("connect", "Connect")
        dlg.set_response_appearance("connect",
                                    Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("connect")
        dlg.set_close_response("cancel")

        def on_resp(_d, resp):
            if resp != "connect":
                return
            pw = entry.get_text()
            cmd = ["nmcli", "dev", "wifi", "connect", ssid, "password", pw]
            sh_async(cmd, lambda r: (
                self.toast(f"connected to {ssid}" if r[0] == 0
                           else f"connect failed: {r[2][:80]}"),
                self._render()), timeout=20)
        dlg.connect("response", on_resp)
        dlg.present()

    def _toggle_vpn(self, name: str, up: bool) -> None:
        action = "up" if up else "down"
        # List-form: NetworkManager allows arbitrary characters in
        # connection names; shell-quoting would be unsafe.
        sh_async(["nmcli", "connection", action, name],
                 lambda r: (self.toast(f"{name} {action}"
                                       if r[0] == 0
                                       else f"{action} failed"),
                            self._render()))

    def _on_ping(self, _btn: Gtk.Button) -> None:
        sh_async("ping -c 3 -W 2 1.1.1.1",
                 lambda r: self.toast(
                     "internet reachable" if r[0] == 0
                     else "ping failed — no internet"),
                 timeout=10)


# ──────────────────────────────────────────────────────────────────────
# Tier-1: BLUETOOTH
# ──────────────────────────────────────────────────────────────────────
class BluetoothPage(SectionPage):
    KEY = "bluetooth"

    def build(self) -> None:
        if not have("bluetoothctl"):
            grp = Adw.PreferencesGroup(title="bluetoothctl not installed")
            grp.add(Adw.ActionRow(
                title="Bluetooth tools missing",
                subtitle="Install bluez and bluez-utils to manage Bluetooth."))
            self.add_group(grp)
            self.add_pill(status_pill("bluez missing", "danger"))
            return

        self.power_group = Adw.PreferencesGroup(title="Adapter")
        self.add_group(self.power_group)

        self.dev_group = Adw.PreferencesGroup(
            title="Devices",
            description="Paired and discovered devices")
        self.add_group(self.dev_group)

        self._render()
        self.schedule_refresh(6000, self._tick)

    def _tick(self) -> bool:
        self._render()
        return True

    def _track(self, grp: Adw.PreferencesGroup, row: Gtk.Widget) -> None:
        grp.add(row)
        if not hasattr(grp, "_rows"):
            grp._rows = []  # type: ignore[attr-defined]
        grp._rows.append(row)  # type: ignore[attr-defined]

    def _clear(self, grp: Adw.PreferencesGroup) -> None:
        for row in getattr(grp, "_rows", []):
            grp.remove(row)
        grp._rows = []  # type: ignore[attr-defined]

    def _render(self) -> None:
        for g in (self.power_group, self.dev_group):
            self._clear(g)
        self.clear_pills()

        # Service status
        _, svc, _ = sh("systemctl is-active bluetooth.service")
        svc_active = svc.strip() == "active"

        # Powered state
        _, show, _ = sh("bluetoothctl show")
        powered = "Powered: yes" in show

        if not svc_active:
            self.add_pill(status_pill("service off", "warn"))
        elif powered:
            self.add_pill(status_pill("on", "ok"))
        else:
            self.add_pill(status_pill("off", "warn"))

        if not svc_active:
            row = Adw.ActionRow(title="bluetooth.service is not running",
                                subtitle="Start it to scan for devices")
            btn = Gtk.Button(label="Start service")
            btn.add_css_class("nyx-primary")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", lambda _b: sh_async(
                "pkexec systemctl start bluetooth",
                lambda r: (self.toast(
                    "bluetooth started" if r[0] == 0
                    else "auth required or failed"),
                    self._render())))
            row.add_suffix(btn)
            self._track(self.power_group, row)
            return

        # Power toggle
        pwr_row = Adw.SwitchRow(title="Power",
                                subtitle="Bluetooth adapter on/off")
        pwr_row.set_active(powered)
        pwr_row.connect("notify::active", self._on_power)
        self._track(self.power_group, pwr_row)

        # Discoverable + scan
        discoverable = "Discoverable: yes" in show
        disc_row = Adw.SwitchRow(title="Discoverable",
                                 subtitle="Allow other devices to find this computer")
        disc_row.set_active(discoverable)
        disc_row.set_sensitive(powered)
        disc_row.connect("notify::active", self._on_discoverable)
        self._track(self.power_group, disc_row)

        scan_row = Adw.ActionRow(title="Scan for new devices",
                                 subtitle="Runs bluetoothctl scan for 10 seconds")
        scan_btn = Gtk.Button(label="Scan")
        scan_btn.set_valign(Gtk.Align.CENTER)
        scan_btn.set_sensitive(powered)
        scan_btn.connect("clicked", self._on_scan)
        scan_row.add_suffix(scan_btn)
        self._track(self.power_group, scan_row)

        if not powered:
            row = Adw.ActionRow(title="Adapter is off",
                                subtitle="Turn power on to see devices.")
            self._track(self.dev_group, row)
            return

        # Devices: paired first, then discovered
        _, paired_out, _ = sh("bluetoothctl devices Paired")
        _, all_out,    _ = sh("bluetoothctl devices")
        paired_macs = {ln.split()[1] for ln in paired_out.splitlines()
                       if ln.startswith("Device ") and len(ln.split()) >= 3}
        seen = set()
        devices: List[Tuple[str, str, bool, bool]] = []  # mac, name, paired, connected
        for ln in (paired_out.splitlines() + all_out.splitlines()):
            parts = ln.split(maxsplit=2)
            if len(parts) < 3 or parts[0] != "Device":
                continue
            mac, name = parts[1], parts[2]
            if mac in seen:
                continue
            seen.add(mac)
            paired = mac in paired_macs
            _, info, _ = sh(f"bluetoothctl info {mac}", timeout=2)
            connected = "Connected: yes" in info
            devices.append((mac, name, paired, connected))

        if not devices:
            # §9 empty state
            row = Adw.ActionRow(title="No devices found",
                                subtitle="Press Scan, then put your device in pairing mode.")
            self._track(self.dev_group, row)
            return

        for mac, name, paired, connected in devices[:12]:
            sub_bits = []
            if paired:    sub_bits.append("paired")
            if connected: sub_bits.append("connected")
            sub_bits.append(mac)
            row = Adw.ActionRow(title=name, subtitle=" · ".join(sub_bits))
            if connected:
                row.add_suffix(status_pill("active", "ok"))

            actions = Gtk.Box(spacing=6)
            actions.set_valign(Gtk.Align.CENTER)
            if connected:
                btn = Gtk.Button(label="Disconnect")
                btn.add_css_class("destructive-action")
                btn.connect("clicked",
                            lambda _b, m=mac: self._do(
                                ["bluetoothctl", "disconnect", m],
                                "disconnected"))
                actions.append(btn)
            elif paired:
                btn = Gtk.Button(label="Connect")
                btn.add_css_class("nyx-primary")
                btn.connect("clicked",
                            lambda _b, m=mac: self._do(
                                ["bluetoothctl", "connect", m],
                                "connecting"))
                actions.append(btn)
            else:
                btn = Gtk.Button(label="Pair")
                btn.add_css_class("nyx-primary")
                btn.connect("clicked",
                            lambda _b, m=mac: self._do_pair(m))
                actions.append(btn)

            if paired:
                rmv = Gtk.Button(label="Forget")
                rmv.connect("clicked",
                            lambda _b, m=mac: self._do(
                                ["bluetoothctl", "remove", m],
                                "forgotten"))
                actions.append(rmv)

            row.add_suffix(actions)
            self._track(self.dev_group, row)

    def _do(self, cmd, label: str) -> None:
        # Accept either a list or string; list-form preferred for safety
        # against MAC addresses or device names with shell metacharacters.
        sh_async(cmd, lambda r: (self.toast(
            f"{label}: ok" if r[0] == 0 else f"{label}: failed"),
            self._render()), timeout=12)

    def _do_pair(self, mac: str) -> None:
        # Pair, then on success trust. Two list-form calls beats
        # `pair && trust` in a shell string.
        sh_async(["bluetoothctl", "pair", mac],
                 lambda r: (sh_async(["bluetoothctl", "trust", mac], None,
                                     timeout=5)
                            if r[0] == 0 else None,
                            self.toast("paired" if r[0] == 0
                                       else "pair failed"),
                            self._render()),
                 timeout=20)

    def _on_power(self, row: Adw.SwitchRow, _pspec) -> None:
        on = row.get_active()
        self._do(["bluetoothctl", "power", "on" if on else "off"],
                 f"power {'on' if on else 'off'}")

    def _on_discoverable(self, row: Adw.SwitchRow, _pspec) -> None:
        on = row.get_active()
        self._do(["bluetoothctl", "discoverable",
                  "on" if on else "off"],
                 "discoverable")

    def _on_scan(self, _btn: Gtk.Button) -> None:
        # Scan in background for 10 s, then re-render.
        sh_async(["bluetoothctl", "--timeout", "10", "scan", "on"],
                 lambda r: (self.toast("scan complete"), self._render()),
                 timeout=15)
        self.toast("scanning…")


# ──────────────────────────────────────────────────────────────────────
# Tier-1: ABOUT
# ──────────────────────────────────────────────────────────────────────
class AboutPage(SectionPage):
    KEY = "about"

    def build(self) -> None:
        # System
        g_sys = Adw.PreferencesGroup(title="System")
        _, host,   _ = sh("hostnamectl --static")
        _, kernel, _ = sh("uname -r")
        _, uptime, _ = sh("uptime -p")
        nyx_ver = self._read_nyx_version()
        for title, value in (
            ("Hostname",       host.strip()  or "(unset)"),
            ("Kernel",         kernel.strip() or "(unknown)"),
            ("NYXUS version",  nyx_ver),
            ("Uptime",         uptime.strip() or "(unknown)"),
        ):
            row = Adw.ActionRow(title=title)
            row.add_suffix(self._mono(value))
            g_sys.add(row)
        self.add_group(g_sys)

        # Hardware
        g_hw = Adw.PreferencesGroup(title="Hardware")
        cpu  = self._cpu_model()
        ram  = self._ram_total()
        gpu  = self._gpu_model()
        disk = self._root_disk()
        for title, value in (
            ("Processor", cpu),
            ("Memory",    ram),
            ("Graphics",  gpu),
            ("Root disk", disk),
        ):
            row = Adw.ActionRow(title=title)
            row.add_suffix(self._mono(value))
            g_hw.add(row)
        self.add_group(g_hw)

        # OS / build
        g_os = Adw.PreferencesGroup(title="OS")
        _, osr, _ = sh("cat /etc/os-release")
        info = {}
        for ln in osr.splitlines():
            if "=" in ln:
                k, v = ln.split("=", 1)
                info[k] = v.strip().strip('"')
        for title, key in (
            ("Distribution", "PRETTY_NAME"),
            ("Build ID",     "BUILD_ID"),
            ("Variant",      "VARIANT"),
        ):
            v = info.get(key, "(n/a)")
            row = Adw.ActionRow(title=title)
            row.add_suffix(self._mono(v))
            g_os.add(row)
        self.add_group(g_os)

        # Credits
        g_credits = Adw.PreferencesGroup(title="NYXUS")
        row = Adw.ActionRow(
            title="Designed and built by Joseph Sierengowski",
            subtitle="© 2026 · DARK MIRROR aesthetic · enterprise grade")
        g_credits.add(row)
        self.add_group(g_credits)

        self.add_pill(status_pill(APP_REV, "ok"))

    @staticmethod
    def _mono(text: str) -> Gtk.Label:
        lbl = Gtk.Label(label=text)
        lbl.add_css_class("nyx-pill")
        return lbl

    @staticmethod
    def _read_nyx_version() -> str:
        for p in (Path("/etc/nyxus-release"),
                  Path("/etc/os-release")):
            if p.exists():
                try:
                    txt = p.read_text()
                    for ln in txt.splitlines():
                        if ln.startswith("NYXUS_VERSION="):
                            return ln.split("=", 1)[1].strip().strip('"')
                except Exception:
                    pass
        return "(unknown)"

    @staticmethod
    def _cpu_model() -> str:
        try:
            for ln in Path("/proc/cpuinfo").read_text().splitlines():
                if ln.startswith("model name"):
                    return ln.split(":", 1)[1].strip()
        except Exception:
            pass
        return "(unknown)"

    @staticmethod
    def _ram_total() -> str:
        try:
            for ln in Path("/proc/meminfo").read_text().splitlines():
                if ln.startswith("MemTotal:"):
                    kb = int(ln.split()[1])
                    gb = kb / 1024 / 1024
                    return f"{gb:.1f} GiB"
        except Exception:
            pass
        return "(unknown)"

    @staticmethod
    def _gpu_model() -> str:
        if have("lspci"):
            _, out, _ = sh("lspci -nn")
            for ln in out.splitlines():
                if "VGA" in ln or "3D controller" in ln or "Display controller" in ln:
                    if ":" in ln:
                        return ln.split(":", 2)[-1].strip()
        return "(unknown)"

    @staticmethod
    def _root_disk() -> str:
        _, out, _ = sh("df -h /")
        lines = out.strip().splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            if len(parts) >= 5:
                return f"{parts[2]} used of {parts[1]}  ({parts[4]} full)"
        return "(unknown)"


# Map section.key → page class.
PAGE_CLASSES = {
    "appearance":    AppearancePage,
    "network":       NetworkPage,
    "bluetooth":     BluetoothPage,
    "display":       DisplayPage,
    "sound":         SoundPage,
    "power":         PowerPage,
    "notifications": NotificationsPage,
    "datetime":      DateTimePage,
    "keyboard":      KeyboardPage,
    "mouse":         MousePage,
    "privacy":       PrivacyPage,
    "apps":          AppsPage,
    "storage":       StoragePage,
    "updates":       UpdatesPage,
    "accessibility": AccessibilityPage,
    "users":         UsersPage,
    "about":         AboutPage,
}


# ──────────────────────────────────────────────────────────────────────
# Sidebar row widget — glyph + title + subtitle.
# ──────────────────────────────────────────────────────────────────────
class SidebarRow(Gtk.ListBoxRow):
    def __init__(self, section: SectionDef):
        super().__init__()
        self.section = section
        self.add_css_class("nyx-section-row")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        glyph = Gtk.Label(label=GLYPHS.get(section.glyph, ""))
        glyph.add_css_class("nyx-section-glyph")
        glyph.set_valign(Gtk.Align.CENTER)
        box.append(glyph)

        text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title = Gtk.Label(label=section.title)
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0.0)
        title.add_css_class("body")
        text.append(title)
        sub = Gtk.Label(label=section.subtitle)
        sub.set_halign(Gtk.Align.START)
        sub.set_xalign(0.0)
        sub.add_css_class("subtitle")
        sub.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        text.append(sub)
        text.set_hexpand(True)
        box.append(text)

        if section.tier == 2:
            box.append(status_pill("WIP", "warn"))

        self.set_child(box)


# ──────────────────────────────────────────────────────────────────────
# Main window
# ──────────────────────────────────────────────────────────────────────
class SettingsWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app, title=APP_NAME)
        self.set_default_size(WIN_W, WIN_H)
        self.prefs = load_prefs()
        self._pages: dict = {}
        self._current_key: Optional[str] = None
        self._build_layout()
        # Land on Appearance first time, otherwise last visited.
        initial = self.prefs.get("last_section", "appearance")
        self._select_key(initial if initial in SECTIONS_BY_KEY else "appearance")
        # Stop ALL live-polling timeouts when the window closes; without
        # this, sh_async threads + GLib.timeouts on the Network and
        # Bluetooth pages keep firing until the process exits.
        self.connect("close-request", self._on_close)

    def _on_close(self, _w) -> bool:
        for page in self._pages.values():
            if isinstance(page, SectionPage):
                page.stop_refresh()
        return False  # allow close

    # ── layout ────────────────────────────────────────────────────────
    def _build_layout(self) -> None:
        split = Adw.NavigationSplitView()
        split.set_max_sidebar_width(320)
        split.set_min_sidebar_width(280)
        split.set_sidebar_width_fraction(0.27)

        # Sidebar
        sidebar_page = Adw.NavigationPage()
        sidebar_page.set_title(APP_NAME)
        sidebar_outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar_outer.add_css_class("nyx-sidebar")

        header = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        header.add_css_class("nyx-sidebar-header")
        title = Gtk.Label(label="NYXUS Settings")
        title.add_css_class("nyx-sidebar-title")
        title.set_halign(Gtk.Align.START)
        header.append(title)
        rev = Gtk.Label(label=APP_REV)
        rev.add_css_class("nyx-sidebar-rev")
        rev.set_halign(Gtk.Align.START)
        header.append(rev)
        sidebar_outer.append(header)

        # Search
        self.search = Gtk.SearchEntry()
        self.search.add_css_class("nyx-search")
        self.search.set_placeholder_text("Search settings…")
        self.search.connect("search-changed", self._on_search)
        sidebar_outer.append(self.search)

        # List
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("background")
        self.listbox.connect("row-selected", self._on_row_selected)
        self.listbox.set_filter_func(self._filter_row)
        for s in SECTIONS:
            self.listbox.append(SidebarRow(s))

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_child(self.listbox)
        sidebar_outer.append(scroll)
        sidebar_page.set_child(sidebar_outer)
        split.set_sidebar(sidebar_page)

        # Content
        self.content_page = Adw.NavigationPage()
        self.content_page.set_title("")
        self.content_stack = Gtk.Stack()
        self.content_stack.set_transition_type(
            Gtk.StackTransitionType.CROSSFADE)
        self.content_stack.set_transition_duration(180)
        self.content_page.set_child(self.content_stack)
        split.set_content(self.content_page)

        # Toast overlay wraps the whole window
        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(split)
        self.set_content(self.toast_overlay)

    # ── search filter ─────────────────────────────────────────────────
    def _on_search(self, _entry: Gtk.SearchEntry) -> None:
        self.listbox.invalidate_filter()

    def _filter_row(self, row: Gtk.ListBoxRow) -> bool:
        q = self.search.get_text().strip().lower()
        if not q:
            return True
        if not isinstance(row, SidebarRow):
            return True
        s = row.section
        haystack = f"{s.title} {s.subtitle} {s.keywords}".lower()
        return all(part in haystack for part in q.split())

    # ── selection ─────────────────────────────────────────────────────
    def _on_row_selected(self, _lb: Gtk.ListBox,
                         row: Optional[Gtk.ListBoxRow]) -> None:
        if not isinstance(row, SidebarRow):
            return
        self._show_section(row.section)

    def _select_key(self, key: str) -> None:
        i = 0
        while True:
            row = self.listbox.get_row_at_index(i)
            if row is None:
                break
            if isinstance(row, SidebarRow) and row.section.key == key:
                self.listbox.select_row(row)
                self._show_section(row.section)
                return
            i += 1

    def _show_section(self, section: SectionDef) -> None:
        if section.key not in self._pages:
            cls = PAGE_CLASSES.get(section.key, AboutPage)
            page = cls(self, section)
            self._pages[section.key] = page
            self.content_stack.add_named(page, section.key)
        self.content_stack.set_visible_child_name(section.key)
        self.content_page.set_title(section.title)
        if self._current_key and self._current_key != section.key:
            prev = self._pages.get(self._current_key)
            if isinstance(prev, SectionPage):
                prev.stop_refresh()
        self._current_key = section.key
        # Persist last visited
        self.prefs["last_section"] = section.key
        save_prefs(self.prefs)

    # ── public API ────────────────────────────────────────────────────
    def toast(self, msg: str) -> None:
        try:
            t = Adw.Toast.new(msg)
            t.set_timeout(3)
            self.toast_overlay.add_toast(t)
        except Exception:
            log.info("toast: %s", msg)


# ──────────────────────────────────────────────────────────────────────
# Application
# ──────────────────────────────────────────────────────────────────────
class SettingsApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        # Force dark scheme — DARK MIRROR is locked.
        sm = self.get_style_manager() if hasattr(self, "get_style_manager") else None
        if sm is None:
            sm = Adw.StyleManager.get_default()
        sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)

    def do_activate(self) -> None:
        install_css()
        win = self.get_active_window()
        if win is None:
            win = SettingsWindow(self)
        win.present()


def main() -> int:
    app = SettingsApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
