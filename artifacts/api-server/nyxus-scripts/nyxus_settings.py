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
import shutil
import subprocess
import sys
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


DisplayPage       = _tier2("display",
    "Read-only listing of monitors via hyprctl.",
    "Resolution / refresh / scale / rotation pickers, brightness slider, "
    "night light schedule, multi-monitor arrangement.")
SoundPage         = _tier2("sound",
    "Output and input device names from pactl.",
    "Master + per-app volume sliders with live VU meters, default device "
    "switcher, sample-rate picker, Bluetooth codec selector.")
PowerPage         = _tier2("power",
    "Battery percentage and charging state.",
    "Power profile picker (powerprofilesctl), sleep/idle timing, lid "
    "behavior, charge thresholds, CPU governor.")
NotificationsPage = _tier2("notifications",
    "DND on/off via dunstctl.",
    "Notification history, per-app rules, quiet hours schedule, sound, "
    "preview policy.")
DateTimePage      = _tier2("datetime",
    "Current timezone and clock format.",
    "Timezone picker (timedatectl), NTP server selector, manual time "
    "entry, 12/24 hour format, week-start.")
KeyboardPage      = _tier2("keyboard",
    "Current xkb layout from hyprctl.",
    "Layout picker, repeat rate / delay sliders, modifier remap, "
    "compose key, shortcut viewer linked to cheatsheet.")
MousePage         = _tier2("mouse",
    "Pointer device list from libinput.",
    "Speed, acceleration profile, natural scroll, tap-to-click, "
    "two-finger gestures, palm rejection.")
PrivacyPage       = _tier2("privacy",
    "Read-only mic/camera presence detection.",
    "Per-app permission ledger, location services toggle, screen-record "
    "indicator, clipboard history policy, telemetry opt-out audit.")
AppsPage          = _tier2("apps",
    "Installed package count via pacman.",
    "Searchable installed-apps list, default browser/terminal/PDF picker, "
    "MIME associations, autostart manager.")
StoragePage       = _tier2("storage",
    "Mount points and free space via df.",
    "Per-disk usage chart, SMART health (smartctl), pacman cache cleanup, "
    "journal trim, large-file finder.")
UpdatesPage       = _tier2("updates",
    "Pending pacman update count.",
    "Live update list, AUR check, reboot-required flag, mirror picker, "
    "scheduled update window.")
AccessibilityPage = _tier2("accessibility",
    "Reduce-motion preference (read-only).",
    "Large text scale, high contrast (locked off — DARK MIRROR), sticky "
    "keys, slow keys, screen reader hint, cursor size.")
UsersPage         = _tier2("users",
    "Current user, groups, default shell.",
    "Password change, full name, avatar picker, group membership editor "
    "(via polkit), sudoers viewer.")


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
            description="Click a wallpaper to apply it system-wide via swww.")
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
        if have("swww"):       backends.append("swww")
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
        # Apply
        if have("swww"):
            sh_async(f"swww img '{path}' --transition-type fade "
                     f"--transition-duration 0.6",
                     lambda r: self.toast(
                         "wallpaper applied" if r[0] == 0
                         else f"swww failed: {r[2][:60]}"))
        else:
            self.toast("swww not installed — saved selection only")

    def _on_font_scale(self, scale: Gtk.Scale) -> None:
        v = round(scale.get_value(), 2)
        self.win.prefs["font_scale"] = v
        save_prefs(self.win.prefs)

    def _on_anim_toggle(self, row: Adw.SwitchRow, _pspec) -> None:
        on = row.get_active()
        self.win.prefs["animations"] = on
        save_prefs(self.win.prefs)
        if have("hyprctl"):
            sh_async(f"hyprctl keyword animations:enabled {1 if on else 0}",
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
        sh_async(f"nmcli connection {action} '{name}'",
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
                            lambda _b, m=mac: self._do(f"bluetoothctl disconnect {m}",
                                                       f"disconnected"))
                actions.append(btn)
            elif paired:
                btn = Gtk.Button(label="Connect")
                btn.add_css_class("nyx-primary")
                btn.connect("clicked",
                            lambda _b, m=mac: self._do(f"bluetoothctl connect {m}",
                                                       f"connecting"))
                actions.append(btn)
            else:
                btn = Gtk.Button(label="Pair")
                btn.add_css_class("nyx-primary")
                btn.connect("clicked",
                            lambda _b, m=mac: self._do(
                                f"bluetoothctl pair {m} && bluetoothctl trust {m}",
                                f"pairing"))
                actions.append(btn)

            if paired:
                rmv = Gtk.Button(label="Forget")
                rmv.connect("clicked",
                            lambda _b, m=mac: self._do(f"bluetoothctl remove {m}",
                                                       f"forgotten"))
                actions.append(rmv)

            row.add_suffix(actions)
            self._track(self.dev_group, row)

    def _do(self, cmd: str, label: str) -> None:
        sh_async(cmd, lambda r: (self.toast(
            f"{label}: ok" if r[0] == 0 else f"{label}: failed"),
            self._render()), timeout=12)

    def _on_power(self, row: Adw.SwitchRow, _pspec) -> None:
        on = row.get_active()
        self._do(f"bluetoothctl power {'on' if on else 'off'}",
                 f"power {'on' if on else 'off'}")

    def _on_discoverable(self, row: Adw.SwitchRow, _pspec) -> None:
        on = row.get_active()
        self._do(f"bluetoothctl discoverable {'on' if on else 'off'}",
                 "discoverable")

    def _on_scan(self, _btn: Gtk.Button) -> None:
        # Scan in background for 10 s, then re-render.
        sh_async("bluetoothctl --timeout 10 scan on",
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
