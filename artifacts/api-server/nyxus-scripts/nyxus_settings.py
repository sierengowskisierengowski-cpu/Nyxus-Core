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
#  Logs:     ~/.cache/nyxus/settings.log
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
import secrets
import shlex
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
LOG_DIR   = Path.home() / ".cache" / "nyxus"
try:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
except Exception:
    pass
LOG_FILE  = LOG_DIR / "settings.log"
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
NYXUS_GOLD = "#d4b87a"  # warm brand accent — selection, focus rings

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
    "backup":        "\uf187",   # nf-fa-archive
    "sync":          "\uf021",   # nf-fa-refresh
    "drop":          "\uf0ee",   # nf-fa-cloud_upload
    "language":      "\uf1ab",   # nf-fa-language
    "shortcut":      "\uf11c",   # nf-fa-keyboard_o (alt)
    "crash":         "\uf188",   # nf-fa-bug
    "printers":      "\uf02f",   # nf-fa-print
    "gamepad":       "\uf11b",   # nf-fa-gamepad
    "webcam":        "\uf03d",   # nf-fa-video_camera
    "color":         "\uf1fb",   # nf-fa-eyedropper
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


_HYPRLAND_CONF = Path.home() / ".config" / "hypr" / "hyprland.conf"
# Recognized launch commands → friendly user-facing label.
# Anything not in the map falls back to the literal command (truncated)
# so a drifted bind still shows up rather than disappearing silently.
_BIND_LABELS = {
    "nyxus-clipboard":      "NYXUS Clipboard",
    "nyxus-files":          "NYXUS Files",
    "nyxus-updater":        "NYXUS Updater",
    "nyxus-store":          "NYXUS Store",
    "nyxus-backup":         "NYXUS Backup",
    "nyxus-drop":           "NYXUS Drop",
    "nyxus-record":         "NYXUS Record",
    "nyxus-context-menu.sh":"NYXUS Context menu",
    "nyxus-set-wallpaper.sh":"NYXUS Wallpaper",
    "nyxus_wallpaper_studio.py":"NYXUS Wallpaper Studio",
    "nyxus_launcher.py":    "NYXUS Spotlight",
    "nyxus_terminal.py":    "NYXUS Terminal",
    "nyxus_doctor.py":      "Doctor (diagnostics)",
    "nyxus_screenshot.py":  "Screenshot",
    "rofi":                 "Start menu (rofi)",
    "firefox":              "Browser",
    "alacritty":            "Terminal (alacritty)",
    "hyprlock":             "Lock screen",
    "wlogout":              "Logout menu",
    "hyprshot":             "Screenshot region",
    "playerctl":            "Media keys",
    "wpctl":                "Volume",
    "brightnessctl":        "Brightness",
}


def parse_hypr_binds(path: Path = _HYPRLAND_CONF) -> List[Tuple[str, str, str]]:
    """Live-parse `bind = MODS, KEY, action, args` from hyprland.conf.

    Returns [(label, chord, raw_command)] in file order. Empty list if
    the file is missing or unreadable — caller can fall back to a
    curated table.
    """
    if not path.exists():
        return []
    try:
        text = path.read_text(errors="replace")
    except Exception as e:
        log.warning("parse_hypr_binds %s: %s", path, e)
        return []
    out: List[Tuple[str, str, str]] = []
    bind_re = re.compile(
        r"^\s*bind[lermn]*\s*=\s*([^,]*),\s*([^,]+),\s*([^,]+)"
        r"(?:,\s*(.+))?$")
    for line in text.splitlines():
        # strip trailing inline comment
        line_no_cmt = re.sub(r"\s+#.*$", "", line)
        m = bind_re.match(line_no_cmt)
        if not m:
            continue
        mods, key, action, args = m.groups()
        mods = " ".join(mods.split()).replace("$mod", "Super")
        # Build chord (e.g. "Super + Shift + V")
        chord_parts = [p.strip().capitalize() for p in mods.split() if p.strip()]
        chord_parts.append(key.strip())
        chord = " + ".join(chord_parts) if chord_parts else key.strip()
        # Build human label
        action = action.strip()
        args = (args or "").strip()
        if action == "exec":
            # Inspect the first meaningful token of the command
            tokens = re.findall(r"\S+", args)
            target = ""
            for t in tokens:
                base = Path(t).name
                if base in _BIND_LABELS:
                    target = base
                    break
                # Some commands are like `python3 ~/.nyxus/foo.py args`
                if base.endswith(".py") or base.endswith(".sh"):
                    target = base
                    break
                # Skip wrappers
                if base in ("python3", "bash", "sh", "env", "exec",
                            "pkexec", "sudo"):
                    continue
                if not target:
                    target = base
                    break
            label = _BIND_LABELS.get(target, target or args[:36])
        else:
            # Built-in dispatcher (workspace, movefocus, exec-shell, …)
            label = action if not args else f"{action} {args[:24]}"
        out.append((label, chord, f"{action} {args}".strip()))
    return out


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
    category: str = ""  # taxonomy bucket — drives sidebar group headers

# Sidebar order is preserved for category grouping (Mac System Settings
# style). Each section declares its category; SettingsWindow renders a
# subtle header above the first row of each new category.
SECTIONS: Tuple[SectionDef, ...] = (
    # ── Personal ────────────────────────────────────────────────────────
    SectionDef("appearance",    "Appearance",
               "Wallpaper, theme variant, font scale",
               "appearance",
               "wallpaper,background,theme,dark,font,scale,accent,style", 1,
               "Personal"),
    SectionDef("accessibility", "Accessibility",
               "Large text, reduce motion, sticky keys",
               "accessibility",
               "accessibility,a11y,zoom,contrast,motion,sticky,screen reader", 2,
               "Personal"),
    SectionDef("notifications", "Notifications",
               "Do not disturb, history, per-app rules",
               "notifications",
               "notification,dnd,quiet,alert,toast,banner", 2,
               "Personal"),
    # ── Devices ─────────────────────────────────────────────────────────
    SectionDef("display",       "Display",
               "Resolution, refresh, scale, brightness",
               "display",
               "display,monitor,resolution,refresh,scale,brightness,hidpi", 2,
               "Devices"),
    SectionDef("sound",         "Sound",
               "Output, input, per-app volume",
               "sound",
               "sound,audio,volume,microphone,mic,speaker,headphone", 2,
               "Devices"),
    SectionDef("keyboard",      "Keyboard",
               "Layout, repeat rate, shortcuts",
               "keyboard",
               "keyboard,layout,xkb,repeat,shortcut,hotkey,bind", 2,
               "Devices"),
    SectionDef("mouse",         "Mouse & Touchpad",
               "Speed, accel, natural scroll, tap",
               "mouse",
               "mouse,touchpad,trackpad,pointer,scroll,tap,acceleration", 2,
               "Devices"),
    SectionDef("bluetooth",     "Bluetooth",
               "Devices, pairing, audio profile",
               "bluetooth",
               "bluetooth,bt,pair,headphones,speaker,audio,device", 1,
               "Devices"),
    SectionDef("printers",      "Printers & Scanners",
               "CUPS print queues, default printer, test page",
               "printers",
               "printer,scanner,cups,lpstat,lpadmin,print,paper,queue", 1,
               "Devices"),
    SectionDef("cameras_mics",  "Camera & Microphone",
               "Detected video/audio capture devices, test tools",
               "webcam",
               "camera,webcam,microphone,mic,v4l2,video,capture,record,"
               "cheese,arecord,pactl", 1,
               "Devices"),
    SectionDef("controllers",   "Game Controllers",
               "Joysticks, gamepads, axes & button test",
               "gamepad",
               "controller,gamepad,joystick,xbox,playstation,steam,"
               "evtest,jstest,input", 1,
               "Devices"),
    SectionDef("color",         "Color profiles",
               "ICC color profiles per display (colord)",
               "color",
               "color,colord,icc,profile,calibration,monitor,display,"
               "colormgr,gamma", 1,
               "Devices"),
    SectionDef("network",       "Network",
               "Wi-Fi, ethernet, VPN, DNS, hotspot",
               "network",
               "wifi,wireless,ethernet,vpn,dns,internet,connection,"
               "hotspot,tether,share", 1,
               "Devices"),
    # ── System ──────────────────────────────────────────────────────────
    SectionDef("power",         "Power",
               "Battery, profiles, sleep, lid behavior",
               "power",
               "power,battery,sleep,suspend,lid,profile,energy,charge", 2,
               "System"),
    SectionDef("datetime",      "Date & Time",
               "Timezone, NTP, format",
               "datetime",
               "date,time,timezone,clock,ntp,12,24,format", 2,
               "System"),
    SectionDef("privacy",       "Privacy & Security",
               "Location, mic, camera, screen recording",
               "privacy",
               "privacy,security,permission,location,microphone,camera", 2,
               "System"),
    SectionDef("apps",          "Apps & Defaults",
               "Installed apps, default browser/terminal, autostart",
               "apps",
               "apps,application,default,browser,terminal,autostart,mime", 2,
               "System"),
    SectionDef("storage",       "Storage",
               "Disks, usage, SMART health, cleanup",
               "storage",
               "storage,disk,drive,usage,smart,smartctl,health,clean", 2,
               "System"),
    SectionDef("updates",       "Updates",
               "System packages and AUR",
               "updates",
               "update,upgrade,pacman,aur,package,version", 2,
               "System"),
    # ── Account ─────────────────────────────────────────────────────────
    SectionDef("users",         "Users",
               "Account info, password, groups, shell",
               "users",
               "user,account,password,group,shell,passwd,profile", 2,
               "Account"),
    SectionDef("sync",          "NYXUS Account",
               "Opt-in sync of wallpaper, theme, settings",
               "sync",
               "account,sync,cloud,wallpaper,theme,settings,token", 1,
               "Account"),
    SectionDef("backup",        "Backup",
               "Snapshots, schedule, restore (Timeshift)",
               "backup",
               "backup,snapshot,timeshift,restore,schedule,history", 1,
               "Account"),
    SectionDef("drop",          "NYXUS Drop",
               "Send files & text to nearby devices (KDE Connect)",
               "drop",
               "drop,airdrop,share,kdeconnect,phone,nearby,send", 1,
               "Account"),
    SectionDef("about",         "About",
               "System info, kernel, hardware, version",
               "about",
               "about,version,kernel,hardware,cpu,gpu,ram,uptime,build", 1,
               "Account"),
    SectionDef("language",      "Language & Region",
               "Display language, locale (gettext)",
               "language",
               "language,locale,region,gettext,i18n,translation,po,mo,"
               "lang,country", 1,
               "Personal"),
    SectionDef("parental",      "Parental Controls",
               "Bedtime, web blocklist (nudge-only, never lockout)",
               "users",
               "parental,kids,family,bedtime,blocklist,filter,limit,lock", 1,
               "Account"),
    SectionDef("app_perms",     "App Permissions",
               "Per-Flatpak camera, mic, network, filesystem access",
               "apps",
               "permission,sandbox,flatpak,camera,microphone,network,fs,"
               "portal,override", 1,
               "System"),
    # ── System (security lives here so it's reachable from the
    # System bucket users expect; the full Security Center is a
    # standalone app launched from the embedded SectionPage) ──────────
    SectionDef("security",      "Security",
               "Firewall, virus, account, encryption, privacy, panic",
               "privacy",
               "security,defender,firewall,virus,clamav,ufw,encryption,"
               "luks,vault,vpn,doh,tpm,secure boot,usbguard,fwupd,"
               "panic,lockdown,audit,faillock,pam,recovery,trust,"
               "permissions,camera,microphone,location,screen", 1,
               "System"),
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
    box-shadow: inset 3px 0 0 0 {NYXUS_GOLD},
                0 0 18px rgba(212,184,122,0.10);
}}
.nyx-section-glyph {{
    font-family: 'Symbols Nerd Font', 'Symbols Nerd Font Mono', monospace;
    font-size: 14px;
    color: {GREY_LIGHT};
    min-width: 18px;
}}
.nyx-section-row.selected .nyx-section-glyph,
.nyx-section-row:selected .nyx-section-glyph {{
    color: {NYXUS_GOLD};
}}
.nyx-search-count {{
    font-size: 11px;
    color: {GREY_MID};
    padding: 2px 14px 6px;
}}
.nyx-cat-header {{
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 0.18em;
    color: {GREY_TERTIARY};
    padding: 14px 22px 4px;
    text-transform: uppercase;
}}
/* ── Command palette overlay ──────────────────────────────────────── */
.nyx-palette-window {{
    background: rgba(8, 9, 12, 0.96);
}}
.nyx-palette-card {{
    background-color: {GLASS_DARK};
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: {RADIUS_CARD}px;
    box-shadow: 0 24px 64px rgba(0,0,0,0.7),
                0 0 0 1px rgba(212,184,122,0.08);
    padding: 8px;
}}
.nyx-palette-entry {{
    background: transparent;
    border: none;
    color: {WHITE_PURE};
    font-size: 18px;
    padding: 12px 14px;
}}
.nyx-palette-row {{
    padding: 10px 14px;
    border-radius: {RADIUS_PILL}px;
    color: {GREY_LIGHT};
}}
.nyx-palette-row:hover,
.nyx-palette-row.selected,
.nyx-palette-row:selected {{
    background-color: rgba(212,184,122,0.10);
    color: {WHITE_PURE};
}}
.nyx-palette-hint {{
    font-size: 10px;
    color: {GREY_TERTIARY};
    padding: 6px 14px 2px;
    letter-spacing: 0.10em;
    text-transform: uppercase;
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
        # Tracked so rebuild() can tear them all down before calling
        # build() again. Adw.PreferencesPage doesn't expose a public
        # iterator over its added groups, so we keep our own list.
        self._tracked_groups: list[Adw.PreferencesGroup] = []

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
        self._tracked_groups.append(group)

    def rebuild(self) -> None:
        """Tear down every tracked group + pill, then re-run build().

        Used by pages that need to reflect a system mutation (e.g. a
        snapshot delete) without forcing the user to re-navigate.
        """
        for g in list(self._tracked_groups):
            try:
                self.content.remove(g)
            except Exception as e:
                log.warning("rebuild remove group: %s", e)
        self._tracked_groups.clear()
        self.clear_pills()
        try:
            self.build()
        except Exception as e:
            log.exception("rebuild %s: %s", self.section.key, e)
            err = Adw.PreferencesGroup(title="Error")
            err.add(Adw.ActionRow(
                title="Failed to rebuild this section",
                subtitle=str(e)))
            self.add_group(err)

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

        # Make sure hyprland.conf sources our override file so changes
        # made here survive a logout / reboot.
        self._ensure_monitor_source_line()

        scales = ["1.00", "1.25", "1.50", "1.75", "2.00"]
        rots   = ["0°", "90°", "180°", "270°"]

        for m in mons:
            name = m.get("name", "?")
            desc = m.get("description", "")
            cur_w = int(m.get("width", 0) or 0)
            cur_h = int(m.get("height", 0) or 0)
            cur_hz = float(m.get("refreshRate", 0) or 0)
            cur_scale = float(m.get("scale", 1.0) or 1.0)
            cur_t = int(m.get("transform", 0) or 0)
            sub = (f"{cur_w}×{cur_h} @ {cur_hz:.0f}Hz · "
                   f"scale {cur_scale:.2f} · transform {cur_t}")
            if desc:
                sub = f"{desc} · {sub}"

            row = Adw.ExpanderRow(title=name, subtitle=sub)
            if m.get("focused"):
                tag = Gtk.Label(label="primary")
                tag.add_css_class("nyx-pill-ok")
                row.add_suffix(tag)

            # Scale
            sc_combo = Adw.ComboRow(
                title="Scale",
                subtitle="HiDPI scaling factor")
            sc_combo.set_model(Gtk.StringList.new(scales))
            sc_idx = 0
            for i, s in enumerate(scales):
                if abs(float(s) - cur_scale) < 0.005:
                    sc_idx = i
                    break
            sc_combo.set_selected(sc_idx)
            sc_combo.connect(
                "notify::selected",
                lambda c, _p, mn=name: self._apply_monitor(
                    mn, scale=float(scales[c.get_selected()])))
            row.add_row(sc_combo)

            # Rotation
            rt_combo = Adw.ComboRow(
                title="Rotation",
                subtitle="Counterclockwise from landscape")
            rt_combo.set_model(Gtk.StringList.new(rots))
            rt_combo.set_selected(cur_t if 0 <= cur_t <= 3 else 0)
            rt_combo.connect(
                "notify::selected",
                lambda c, _p, mn=name: self._apply_monitor(
                    mn, transform=c.get_selected()))
            row.add_row(rt_combo)

            self.mon_grp.add(row)

    # ── Multi-monitor helpers ───────────────────────────────────────
    def _apply_monitor(self, name: str, *,
                       scale: Optional[float] = None,
                       transform: Optional[int] = None) -> None:
        """Apply a per-monitor change live via hyprctl AND persist it
        to ~/.config/hypr/nyxus-monitors.conf so it survives reboot."""
        rc, out, _ = sh(["hyprctl", "monitors", "-j"], timeout=2)
        try:
            mons = json.loads(out)
        except Exception:
            mons = []
        cur = next((m for m in mons if m.get("name") == name), None)
        if cur is None:
            self.toast(f"monitor {name} not found")
            return
        w  = int(cur.get("width", 0) or 0)
        h  = int(cur.get("height", 0) or 0)
        hz = float(cur.get("refreshRate", 60) or 60)
        x  = int(cur.get("x", 0) or 0)
        y  = int(cur.get("y", 0) or 0)
        s  = float(scale) if scale is not None \
             else float(cur.get("scale", 1.0) or 1.0)
        t  = int(transform) if transform is not None \
             else int(cur.get("transform", 0) or 0)

        spec = (f"{name},{w}x{h}@{hz:.2f},{x}x{y},{s:.2f},"
                f"transform,{t}")
        rc2, _, err = sh(["hyprctl", "keyword", "monitor", spec],
                         timeout=3)
        if rc2 != 0:
            self.toast(f"hyprctl failed: {(err or '').strip()[:60]}")
            return
        self._persist_monitor_override(name, spec)
        self.toast(f"{name}: applied & saved")

    def _persist_monitor_override(self, name: str, spec: str) -> None:
        """Write/replace 'monitor = <spec>' for `name` in
        ~/.config/hypr/nyxus-monitors.conf atomically."""
        p = Path.home() / ".config" / "hypr" / "nyxus-monitors.conf"
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.warning("mkdir hypr: %s", e)
            self.toast(f"persist mkdir failed: {e}")
            return
        keep: List[str] = []
        if p.exists():
            try:
                for ln in p.read_text(encoding="utf-8").splitlines():
                    s = ln.strip()
                    if s.startswith("monitor") and "=" in s:
                        body = s.split("=", 1)[1].strip()
                        if body.split(",", 1)[0].strip() == name:
                            continue  # drop existing override for this
                    keep.append(ln)
            except OSError as e:
                log.warning("read nyxus-monitors.conf: %s", e)
        keep.append(f"monitor = {spec}")
        try:
            tmp = p.with_suffix(".conf.tmp")
            tmp.write_text("\n".join(keep) + "\n", encoding="utf-8")
            os.replace(tmp, p)
        except OSError as e:
            log.warning("write nyxus-monitors.conf: %s", e)
            self.toast(f"persist write failed: {e}")

    def _ensure_monitor_source_line(self) -> None:
        """Append 'source = ./nyxus-monitors.conf' to hyprland.conf if
        missing. Idempotent — safe to call every render. Fails loud
        via toast on read/write errors so persistence problems are
        explicit rather than silent."""
        hp = _HYPRLAND_CONF
        if not hp.exists():
            self.toast(
                "hyprland.conf missing — overrides won't persist "
                "until Hyprland is configured")
            return
        try:
            text = hp.read_text(encoding="utf-8")
        except OSError as e:
            log.warning("read hyprland.conf: %s", e)
            self.toast(f"can't read hyprland.conf: {e}")
            return
        if "nyxus-monitors.conf" in text:
            return
        try:
            with open(hp, "a", encoding="utf-8") as fh:
                fh.write("\n# nyxus monitor overrides "
                         "(auto-managed by Settings)\n"
                         "source = ./nyxus-monitors.conf\n")
        except OSError as e:
            log.warning("append source line: %s", e)
            self.toast(
                f"can't persist to hyprland.conf: {e} — "
                "monitor changes won't survive reboot")

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

    # ── Night light scheduler (Tier 3 #16) ────────────────────────────
    NL_CONF = Path.home() / ".config" / "nyxus" / "nightlight.conf"
    NL_UNIT = (Path.home() / ".config" / "systemd" / "user"
               / "nyxus-nightlight.service")
    NL_HELPER = Path.home() / ".local" / "bin" / "nyxus-nightlight.sh"

    NL_MODES = ("off", "always", "sunset", "custom")
    NL_MODE_LABELS = (
        "Off",
        "Always on",
        "Sunset → sunrise (latitude/longitude)",
        "Custom hours (HH:MM → HH:MM)",
    )

    def _nl_read_conf(self) -> dict:
        defaults = {
            "mode": "off", "temp_day": "6500", "temp_night": "4000",
            "start": "20:00", "stop": "06:00", "lat": "", "lon": "",
        }
        if not self.NL_CONF.exists():
            return defaults
        try:
            for raw in self.NL_CONF.read_text(encoding="utf-8").splitlines():
                s = raw.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, _, v = s.partition("=")
                defaults[k.strip().lower()] = v.strip()
        except OSError as e:
            log.warning("read %s: %s", self.NL_CONF, e)
        return defaults

    def _nl_write_conf(self, cfg: dict) -> bool:
        try:
            self.NL_CONF.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.NL_CONF.with_suffix(".conf.tmp")
            body = "# Written by nyxus_settings — Night Light\n" + \
                "".join(f"{k}={cfg[k]}\n" for k in (
                    "mode", "temp_day", "temp_night",
                    "start", "stop", "lat", "lon"))
            tmp.write_text(body, encoding="utf-8")
            os.replace(tmp, self.NL_CONF)
            return True
        except OSError as e:
            log.warning("write %s: %s", self.NL_CONF, e)
            self.toast(f"can't save night-light config: {e}")
            return False

    def _nl_active(self) -> bool:
        rc, out, _ = sh(["systemctl", "--user", "is-active",
                         "nyxus-nightlight.service"], timeout=2)
        return rc == 0 and out.strip() == "active"

    def _render_nightlight(self) -> None:
        _clear_group(self.nl_grp)
        any_installed = any(have(x) for x in
                            ("hyprsunset", "gammastep", "wlsunset"))
        if not any_installed:
            self.nl_grp.add(empty_row(
                "No night-light backend installed",
                "Install wlsunset (recommended), hyprsunset, or "
                "gammastep — then return here."))
            return

        cfg = self._nl_read_conf()
        active = self._nl_active()

        # Mode picker
        mode_combo = Adw.ComboRow(
            title="Schedule",
            subtitle=("running via systemd --user"
                      if active else "service stopped"))
        mode_combo.set_model(Gtk.StringList.new(list(self.NL_MODE_LABELS)))
        try:
            mode_combo.set_selected(self.NL_MODES.index(cfg["mode"]))
        except (ValueError, KeyError):
            mode_combo.set_selected(0)
        mode_combo.connect("notify::selected", self._on_nl_mode)
        self.nl_grp.add(mode_combo)

        # Temperature pair
        temp_row = Adw.ActionRow(
            title="Color temperature",
            subtitle="Day · Night (Kelvin) — wlsunset interpolates "
                     "between them at sunset/sunrise")
        for key, lo, hi, step in (("temp_day",   4500, 6700, 100),
                                  ("temp_night", 2500, 5500, 100)):
            try:
                val = int(cfg.get(key, "6500" if key == "temp_day"
                                  else "4000"))
            except ValueError:
                val = 6500 if key == "temp_day" else 4000
            sb = Gtk.SpinButton.new_with_range(lo, hi, step)
            sb.set_value(val)
            sb.set_size_request(110, -1)
            sb.set_valign(Gtk.Align.CENTER)
            sb.set_tooltip_text("Day temperature (K)"
                                if key == "temp_day"
                                else "Night temperature (K)")
            sb.connect("value-changed",
                       lambda spin, k=key: self._on_nl_temp(k, spin))
            temp_row.add_suffix(sb)
        self.nl_grp.add(temp_row)

        if cfg["mode"] == "custom":
            start_row = Adw.EntryRow(title="Start (HH:MM)")
            start_row.set_text(cfg.get("start", "20:00"))
            self._wire_nl_time_entry(start_row, "start")
            self.nl_grp.add(start_row)
            stop_row = Adw.EntryRow(title="Stop (HH:MM)")
            stop_row.set_text(cfg.get("stop", "06:00"))
            self._wire_nl_time_entry(stop_row, "stop")
            self.nl_grp.add(stop_row)
        elif cfg["mode"] == "sunset":
            lat_row = Adw.EntryRow(title="Latitude")
            lat_row.set_text(cfg.get("lat", ""))
            self._wire_nl_geo_entry(lat_row, "lat")
            self.nl_grp.add(lat_row)
            lon_row = Adw.EntryRow(title="Longitude")
            lon_row.set_text(cfg.get("lon", ""))
            self._wire_nl_geo_entry(lon_row, "lon")
            self.nl_grp.add(lon_row)

        # Status pill on the page
        if active:
            self.add_pill(status_pill("night light", "ok"))

    def _wire_nl_time_entry(self, row: Adw.EntryRow, key: str) -> None:
        btn = Gtk.Button(label="Apply")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked",
                    lambda _b, r=row, k=key:
                        self._on_nl_time(k, r))
        row.add_suffix(btn)

    def _wire_nl_geo_entry(self, row: Adw.EntryRow, key: str) -> None:
        btn = Gtk.Button(label="Apply")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked",
                    lambda _b, r=row, k=key:
                        self._on_nl_geo(k, r))
        row.add_suffix(btn)

    def _on_nl_mode(self, combo: Adw.ComboRow, _pspec) -> None:
        idx = int(combo.get_selected())
        if idx < 0 or idx >= len(self.NL_MODES):
            return
        cfg = self._nl_read_conf()
        cfg["mode"] = self.NL_MODES[idx]
        if not self._nl_write_conf(cfg):
            return
        self._nl_install_unit()
        self._nl_apply_mode(cfg["mode"])

    def _on_nl_temp(self, key: str, spin: Gtk.SpinButton) -> None:
        cfg = self._nl_read_conf()
        cfg[key] = str(int(spin.get_value()))
        if not self._nl_write_conf(cfg):
            return
        if cfg["mode"] != "off":
            self._nl_apply_mode(cfg["mode"])

    def _on_nl_time(self, key: str, entry: Adw.EntryRow) -> None:
        v = entry.get_text().strip()
        if not re.fullmatch(r"\d{1,2}:\d{2}", v):
            self.toast(f"{key}: use HH:MM (e.g. 20:00)")
            return
        h, m = v.split(":")
        if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
            self.toast(f"{key}: out-of-range time")
            return
        cfg = self._nl_read_conf()
        cfg[key] = f"{int(h):02d}:{int(m):02d}"
        if not self._nl_write_conf(cfg):
            return
        self._nl_apply_mode(cfg["mode"])

    def _on_nl_geo(self, key: str, entry: Adw.EntryRow) -> None:
        v = entry.get_text().strip()
        try:
            num = float(v)
        except ValueError:
            self.toast(f"{key}: must be a number")
            return
        if key == "lat" and not (-90.0 <= num <= 90.0):
            self.toast("latitude must be between −90 and +90")
            return
        if key == "lon" and not (-180.0 <= num <= 180.0):
            self.toast("longitude must be between −180 and +180")
            return
        cfg = self._nl_read_conf()
        cfg[key] = f"{num}"
        if not self._nl_write_conf(cfg):
            return
        self._nl_apply_mode(cfg["mode"])

    def _nl_install_unit(self) -> None:
        """Drop the systemd --user unit + helper script into ~/.local
        and ~/.config so we own them user-side (no pkexec)."""
        try:
            self.NL_HELPER.parent.mkdir(parents=True, exist_ok=True)
            self.NL_UNIT.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.warning("nightlight mkdir: %s", e)
            self.toast(f"can't create unit dirs: {e}")
            return
        # The helper + unit are shipped via the artifact download
        # endpoint at install time, but we re-write them here too so
        # Settings can self-heal a broken install.
        helper_body = textwrap.dedent("""\
            #!/usr/bin/env bash
            # Self-healing stub — see /usr/share/nyxus/nyxus-nightlight.sh
            # for the canonical version installed by the OS package.
            CONF="$HOME/.config/nyxus/nightlight.conf"
            [ -f "$CONF" ] || exit 0
            mode=$(awk -F= '/^mode=/ {gsub(/[[:space:]]/, "", $2); print $2}' "$CONF")
            for proc in wlsunset hyprsunset gammastep; do
              pkill -x "$proc" >/dev/null 2>&1 || true
            done
            [ "$mode" = "off" ] && exit 0
            if command -v wlsunset >/dev/null 2>&1; then
              t_d=$(awk -F= '/^temp_day=/ {print $2}' "$CONF")
              t_n=$(awk -F= '/^temp_night=/ {print $2}' "$CONF")
              case "$mode" in
                always) exec wlsunset -T "${t_n:-4000}" -t "${t_n:-4000}" -S 00:00 -s 23:59 ;;
                custom)
                  s=$(awk -F= '/^start=/ {print $2}' "$CONF")
                  e=$(awk -F= '/^stop=/  {print $2}' "$CONF")
                  exec wlsunset -T "${t_d:-6500}" -t "${t_n:-4000}" -S "$s" -s "$e" ;;
                sunset)
                  la=$(awk -F= '/^lat=/ {print $2}' "$CONF")
                  lo=$(awk -F= '/^lon=/ {print $2}' "$CONF")
                  exec wlsunset -T "${t_d:-6500}" -t "${t_n:-4000}" -l "$la" -L "$lo" ;;
              esac
            fi
            exit 1
            """)
        unit_body = textwrap.dedent(f"""\
            [Unit]
            Description=NYXUS Night Light scheduler
            After=graphical-session.target
            PartOf=graphical-session.target

            [Service]
            Type=simple
            ExecStart={self.NL_HELPER}
            Restart=on-failure
            RestartSec=5s

            [Install]
            WantedBy=graphical-session.target
            """)
        try:
            self.NL_HELPER.write_text(helper_body, encoding="utf-8")
            self.NL_HELPER.chmod(0o755)
            self.NL_UNIT.write_text(unit_body, encoding="utf-8")
        except OSError as e:
            log.warning("nightlight write: %s", e)
            self.toast(f"can't write night-light files: {e}")
            return
        sh_async(["systemctl", "--user", "daemon-reload"], None,
                 timeout=4)

    def _nl_apply_mode(self, mode: str) -> None:
        if mode == "off":
            sh_async(
                ["systemctl", "--user", "disable", "--now",
                 "nyxus-nightlight.service"],
                lambda r: self.toast(
                    "night light off" if r[0] == 0
                    else f"disable failed: {(r[2] or '')[:60]}"),
                timeout=8)
        else:
            sh_async(
                ["systemctl", "--user", "enable", "--now",
                 "nyxus-nightlight.service"],
                lambda r: (
                    self.toast(f"night light · {mode}") if r[0] == 0
                    else self.toast(
                        f"enable failed: {(r[2] or '')[:60]}")),
                timeout=8)
        # Schedule a re-render so the status pill / mode subtitle
        # reflects the new service state.
        GLib.timeout_add(1500, lambda: (self._render_nightlight(),
                                        False)[1])


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

        # ── NYXUS sound theme (system chimes via nyxus-sound.sh) ──
        # Built once in build() — must NEVER be appended in _render_*
        # because those run on a 6s polling tick and would duplicate the
        # group on every refresh. State source of truth is
        # ~/.config/nyxus/sound.conf (key `enabled=0|1`), owned by the
        # nyxus-sound.sh dispatcher itself.
        theme = Adw.PreferencesGroup(
            title="NYXUS sound theme",
            description="System chimes for login, notifications, errors, "
                        "lock, and more (via nyxus-sound.sh)")
        self.add_group(theme)

        sound_conf = (Path.home() / ".config" / "nyxus" / "sound.conf")
        cur_enabled = True
        try:
            if sound_conf.exists():
                for line in sound_conf.read_text().splitlines():
                    if line.startswith("enabled="):
                        cur_enabled = line.split("=", 1)[1].strip() != "0"
                        break
        except Exception as e:
            log.warning("read sound.conf: %s", e)

        mute_row = Adw.SwitchRow(
            title="Mute system chimes",
            subtitle="Calls nyxus-sound.sh --enable/--disable; state lives "
                     "in ~/.config/nyxus/sound.conf")
        # Switch is ON when chimes are muted (i.e. enabled=0)
        mute_row.set_active(not cur_enabled)

        def _on_mute(sw, _p):
            flag = "--disable" if sw.get_active() else "--enable"
            sh_async(
                ["nyxus-sound.sh", flag],
                lambda r: self.toast(
                    "system chimes "
                    + ("muted" if sw.get_active() else "on")
                    if r[0] == 0
                    else f"sound toggle failed: {r[2].strip()}"),
                timeout=3)
        mute_row.connect("notify::active", _on_mute)
        theme.add(mute_row)

        for label, event in (
            ("Test login chime",        "login"),
            ("Test notification chime", "notification"),
            ("Test error chime",        "error"),
            ("Test lock chime",         "lock"),
        ):
            theme.add(action_row(
                label, f"Plays the '{event}' event",
                "Play",
                lambda e=event: fire_and_forget(f"nyxus-sound.sh {e}")))

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
            title="Screen &amp; sleep",
            description="Idle timers (managed by hypridle). 'Never' = disabled.")
        self.add_group(self.sleep_grp)
        self.lid_grp = Adw.PreferencesGroup(
            title="Buttons &amp; lid",
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

        # External-device arrival notifications (USB drives, phones, …)
        ext_grp = Adw.PreferencesGroup(
            title="External devices",
            description="Toast when a USB drive, phone, or media is "
                        "plugged in or removed (nyxus-usb-watch user "
                        "systemd unit)")
        self.add_group(ext_grp)
        rc_a, _, _ = sh(
            ["systemctl", "--user", "is-active",
             "nyxus-usb-watch.service"], timeout=2)
        active = (rc_a == 0)
        usb_sw = Adw.SwitchRow(
            title="Notify on USB plug-in / removal",
            subtitle="active" if active
            else "inactive — no toast on plug events")
        usb_sw.set_active(active)
        usb_sw.connect("notify::active", self._on_usb_watch_toggle)
        ext_grp.add(usb_sw)

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
        elif self.daemon == "swaync":
            # Real history dump via the swaync session-bus method
            # `org.erikreider.swaync.cc.GetHistory`. We invoke it with
            # `busctl --user --json=short` so the output is parseable
            # JSON (`busctl` is part of systemd, always present).
            # The reply has shape:
            #   {"type":"(aa{sv})","data":[[ {<sv map>}, ... ]]}
            # Each entry exposes summary/body/app-name/time as variants.
            rc, n_out, _ = sh(["swaync-client", "--count"], timeout=2)
            try:
                n = int((n_out or "0").strip())
            except ValueError:
                n = 0
            rc2, m_out, _ = sh(["swaync-client", "--get-dnd"], timeout=2)
            dnd_on = "true" in (m_out or "").lower()
            hist.add(kv_row("Pending notifications", str(n)))
            hist.add(kv_row("Do Not Disturb",
                            "ON — silenced" if dnd_on else "OFF"))
            entries = self._swaync_history()
            if entries:
                hist.add(kv_row("Stored in history", str(len(entries))))
                for e in entries[:8]:
                    app = e.get("app", "system")
                    summ = e.get("summary", "")[:60] or "(no summary)"
                    body = e.get("body", "")[:80]
                    sub = f"{app}" + (f"  ·  {body}" if body else "")
                    hist.add(kv_row(summ, sub))
            else:
                hist.add(empty_row(
                    "No history available",
                    "swaync stores nothing or busctl/jq missing"))
            hist.add(action_row(
                "Open notification panel",
                "Toggles the swaync slide-in panel",
                "Open",
                lambda: sh_async(["swaync-client", "-t", "-sw"],
                                 None, timeout=3)))
            hist.add(action_row(
                "Dismiss all notifications",
                "Clears every pending swaync entry",
                "Clear",
                lambda: sh_async(["swaync-client", "-C"],
                                 None, timeout=3)))
            hist.add(action_row(
                "Reload swaync config",
                "Re-reads ~/.config/swaync/config.json",
                "Reload",
                lambda: sh_async(["swaync-client", "-R"],
                                 None, timeout=3)))
        else:
            hist.add(empty_row(
                f"Notification daemon '{self.daemon}' not recognised",
                "Install dunst, mako, or swaync — NYXUS auto-detects"))

        self.add_pill(status_pill(self.daemon, "ok"))

    def _swaync_history(self) -> list[dict]:
        """Pull swaync's notification history off the session bus.

        Uses ``busctl --user --json=short call`` (systemd ships busctl
        everywhere, jq is required to parse). Returns a list of dicts
        ``{app, summary, body, time}`` newest-first, capped at 30. On
        any failure: log + return ``[]`` so the UI shows the empty
        state — never raises.
        """
        if not (have("busctl") and have("jq")):
            return []
        rc, out, err = sh(
            ["busctl", "--user", "--json=short", "call",
             "org.erikreider.swaync.cc", "/swaync",
             "org.erikreider.swaync.cc", "GetHistory"],
            timeout=3)
        if rc != 0 or not out:
            log.info("swaync GetHistory rc=%s err=%s", rc, (err or "")[:80])
            return []
        # busctl --json=short emits {"type":"(aa{sv})","data":[[ {sv...}, ... ]]}
        # Each entry's "value" field carries the variant payload.
        # `sh()` doesn't accept stdin; use subprocess directly so we
        # can pipe the busctl JSON straight into jq.
        jq_filter = (
            '(.data[0] // []) | map({'
            '  app:     ((.["app-name"]    // .app // {}).data // "system"),'
            '  summary: ((.summary         // {}).data // ""),'
            '  body:    (((.body           // {}).data // "")'
            '            | gsub("\\n"; " ") | .[0:160]),'
            '  time:    ((.time            // {}).data // 0)'
            '}) | sort_by(-.time) | .[0:30]'
        )
        try:
            cp = subprocess.run(
                ["jq", "-c", jq_filter],
                input=out, capture_output=True, text=True, timeout=3)
        except Exception as e:  # pylint: disable=broad-except
            log.warning("swaync history jq invoke: %s", e)
            return []
        if cp.returncode != 0 or not cp.stdout.strip():
            log.info("swaync history jq parse err=%s",
                     (cp.stderr or "")[:80])
            return []
        try:
            return json.loads(cp.stdout)
        except Exception as e:  # pylint: disable=broad-except
            log.warning("swaync history json decode: %s", e)
            return []

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

    def _on_usb_watch_toggle(self, sw: Adw.SwitchRow,
                             _pspec: object) -> None:
        wanted = sw.get_active()
        verb = "enable --now" if wanted else "disable --now"
        sh_async(
            f"systemctl --user {verb} nyxus-usb-watch.service",
            lambda r: self.toast(
                "USB watcher " + ("on" if wanted else "off")
                if r[0] == 0
                else f"systemd failed: {(r[2] or '').strip()[:80]}"))


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
# COLOR — colord (`colormgr`) ICC profile import & per-display assign
# ──────────────────────────────────────────────────────────────────────
class ColorPage(SectionPage):
    """Color profile management via colord (`colormgr` CLI).

    Real reads (get-devices-by-kind display, get-profiles), real writes
    (import-profile, device-add-profile, device-make-profile-default).
    Profiles persist in ~/.local/share/icc/ via colord, no behind-the-
    back file edits.
    """
    KEY = "color"

    def build(self) -> None:
        intro = Adw.PreferencesGroup(
            title="Color management",
            description="ICC profiles via colord — applied at session "
                        "start by colord-session.")
        self.add_group(intro)
        if not have("colormgr"):
            intro.add(empty_row(
                "colormgr not installed",
                "Install the `colord` package to manage ICC profiles."))
            self.add_pill(status_pill("colord missing", "danger"))
            return

        self.dev_group = Adw.PreferencesGroup(
            title="Display devices",
            description="Each detected display can hold an assigned ICC "
                        "profile.")
        self.add_group(self.dev_group)

        self.prof_group = Adw.PreferencesGroup(
            title="Imported profiles",
            description="ICC files registered with colord on this user.")
        self.add_group(self.prof_group)

        self._render()
        self.schedule_refresh(15000, self._tick)

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

    @staticmethod
    def _parse_blocks(text: str) -> List[dict]:
        out: List[dict] = []
        cur: dict = {}
        for ln in text.splitlines():
            s = ln.strip()
            if not s:
                if cur:
                    out.append(cur)
                    cur = {}
                continue
            if ":" in s:
                k, v = s.split(":", 1)
                cur[k.strip()] = v.strip()
        if cur:
            out.append(cur)
        return out

    def _list_devices(self) -> List[dict]:
        rc, out, err = sh(["colormgr", "get-devices-by-kind", "display"],
                          timeout=4)
        if rc != 0:
            log.warning("colormgr get-devices-by-kind display rc=%d "
                        "err=%r", rc, err)
            self.toast(f"colormgr device list failed: "
                       f"{(err or 'see log')[:60]}")
            return []
        return self._parse_blocks(out)

    def _list_profiles(self) -> List[dict]:
        rc, out, err = sh(["colormgr", "get-profiles"], timeout=4)
        if rc != 0:
            log.warning("colormgr get-profiles rc=%d err=%r", rc, err)
            self.toast(f"colormgr profile list failed: "
                       f"{(err or 'see log')[:60]}")
            return []
        return self._parse_blocks(out)

    def _render(self) -> None:
        self._clear(self.dev_group)
        self._clear(self.prof_group)
        self.clear_pills()

        devs = self._list_devices()
        if not devs:
            self._track(self.dev_group, empty_row(
                "No color-managed displays detected",
                "Make sure colord.service is running and the session is "
                "registered with colord."))
            self.add_pill(status_pill("0 devices", "warn"))
        else:
            self.add_pill(status_pill(
                f"{len(devs)} display(s)", "ok"))
            for d in devs:
                obj = d.get("Object Path", "")
                model = (d.get("Model") or d.get("Device ID")
                         or "Display")
                cur_prof = (d.get("Default Profile")
                            or d.get("Profile") or "")
                cur_label = (Path(cur_prof).name
                             if cur_prof else "(no profile assigned)")
                row = Adw.ActionRow(title=model,
                                    subtitle=f"profile · {cur_label}")
                btn = Gtk.Button(label="Import & assign ICC")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked",
                            lambda _b, dp=obj: self._pick_icc(dp))
                row.add_suffix(btn)
                self._track(self.dev_group, row)

        profs = self._list_profiles()
        if not profs:
            self._track(self.prof_group, empty_row(
                "No imported profiles",
                "Use Import & assign ICC on a display to add a "
                "profile."))
        else:
            for p in profs[:24]:
                title = (p.get("Title") or p.get("Profile ID")
                         or "(profile)")
                fname = Path(p.get("Filename", "")).name
                sub = fname or p.get("Profile ID", "") or "(no path)"
                self._track(self.prof_group, Adw.ActionRow(
                    title=title, subtitle=sub))

    def _pick_icc(self, dev_path: str) -> None:
        if not dev_path:
            self.toast("device path missing — refresh and try again")
            return
        dlg = Gtk.FileChooserNative(
            title="Pick an ICC profile",
            transient_for=self.win,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="Import",
            cancel_label="Cancel")
        flt = Gtk.FileFilter()
        flt.set_name("ICC profiles")
        flt.add_pattern("*.icc")
        flt.add_pattern("*.icm")
        flt.add_pattern("*.ICC")
        flt.add_pattern("*.ICM")
        dlg.add_filter(flt)
        dlg.connect("response",
                    lambda d, r: self._on_icc_picked(d, r, dev_path))
        dlg.show()
        self._icc_dlg = dlg

    def _on_icc_picked(self, dlg, resp, dev_path: str) -> None:
        if resp != Gtk.ResponseType.ACCEPT:
            dlg.destroy()
            self._icc_dlg = None
            return
        f = dlg.get_file()
        dlg.destroy()
        self._icc_dlg = None
        if not f:
            return
        path = f.get_path()
        if not path:
            self.toast("could not resolve picked file")
            return
        rc, out, err = sh(["colormgr", "import-profile", path], timeout=10)
        if rc != 0:
            self.toast(f"import failed: {(err or 'see log')[:80]}")
            log.warning("colormgr import-profile %s: %s", path, err)
            return
        prof_path = ""
        for ln in out.splitlines():
            s = ln.strip()
            if s.lower().startswith("object path"):
                prof_path = s.split(":", 1)[1].strip()
                break
        if not prof_path:
            for p in self._list_profiles():
                if p.get("Filename", "").endswith(Path(path).name):
                    prof_path = p.get("Object Path", "")
                    break
        if not prof_path:
            self.toast("imported, but couldn't locate profile path")
            log.warning("colormgr import succeeded but Object Path "
                        "missing in stdout=%r", out)
            self._render()
            return
        rc1, _, e1 = sh(["colormgr", "device-add-profile",
                         dev_path, prof_path], timeout=5)
        rc2, _, e2 = sh(["colormgr", "device-make-profile-default",
                         dev_path, prof_path], timeout=5)
        if rc1 == 0 and rc2 == 0:
            self.toast(f"assigned {Path(path).name}")
        else:
            err_msg = (e1 or e2 or "see log").strip()
            self.toast(f"assign failed: {err_msg[:80]}")
            log.warning(
                "colormgr add/make-default failed dev=%s prof=%s "
                "rc=(%d,%d) err=(%r,%r)",
                dev_path, prof_path, rc1, rc2, e1, e2)
        self._render()


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

        # ── Compose key + layout switcher (writes input:kb_options) ──
        # Persists via ~/.config/hypr/nyxus-input.conf with auto-source
        # so settings survive a reboot. Compose and grp tokens are
        # mutated independently — toggling one never disturbs the other.
        sw_grp = Adw.PreferencesGroup(
            title="Compose &amp; layout switcher",
            description="Token edits to input:kb_options "
                        "(persisted to nyxus-input.conf)")
        self.add_group(sw_grp)

        # Canonical local state so back-to-back combo changes don't
        # race on stale hyprctl reads (architect r10b3 fix).
        self._kb_csv = self._kb_options_csv()
        compose_now = self._token_with_prefix(self._kb_csv,
                                              "compose:") or ""
        grp_now = self._token_with_prefix(self._kb_csv, "grp:") or ""

        compose_choices: List[Tuple[str, str]] = [
            ("(off)",       ""),
            ("Right Alt",   "compose:ralt"),
            ("Right Ctrl",  "compose:rctrl"),
            ("Right Win",   "compose:rwin"),
            ("Menu key",    "compose:menu"),
            ("Caps Lock",   "compose:caps"),
        ]
        compose_row = Adw.ComboRow(
            title="Compose key",
            subtitle="Type accented &amp; special characters with a "
                     "two-key sequence")
        compose_model = Gtk.StringList()
        for label, _ in compose_choices:
            compose_model.append(label)
        compose_row.set_model(compose_model)
        try:
            compose_idx = next(i for i, (_, t)
                               in enumerate(compose_choices)
                               if t == compose_now)
        except StopIteration:
            compose_idx = 0
        compose_row.set_selected(compose_idx)
        compose_row.connect(
            "notify::selected",
            lambda r, _p, choices=compose_choices: self._apply_kb_token(
                "compose:", choices[r.get_selected()][1]))
        sw_grp.add(compose_row)

        grp_choices: List[Tuple[str, str]] = [
            ("(off)",          ""),
            ("Alt + Shift",    "grp:alt_shift_toggle"),
            ("Ctrl + Shift",   "grp:ctrl_shift_toggle"),
            ("Win + Space",    "grp:win_space_toggle"),
            ("Caps Lock",      "grp:caps_toggle"),
        ]
        grp_row = Adw.ComboRow(
            title="Layout switcher shortcut",
            subtitle="Cycle between active xkb layouts "
                     "(set kb_layout to a CSV like 'us,de' first)")
        grp_model = Gtk.StringList()
        for label, _ in grp_choices:
            grp_model.append(label)
        grp_row.set_model(grp_model)
        try:
            grp_idx = next(i for i, (_, t)
                           in enumerate(grp_choices)
                           if t == grp_now)
        except StopIteration:
            grp_idx = 0
        grp_row.set_selected(grp_idx)
        grp_row.connect(
            "notify::selected",
            lambda r, _p, choices=grp_choices: self._apply_kb_token(
                "grp:", choices[r.get_selected()][1]))
        sw_grp.add(grp_row)

        # Cheatsheet jump
        ext = Adw.PreferencesGroup(title="Shortcuts")
        self.add_group(ext)
        ext.add(action_row(
            "Open keyboard cheatsheet",
            "Full list of system & Hyprland shortcuts",
            "Open",
            lambda: fire_and_forget("nyxus-cheatsheet")))

        # ── Real, parsed shortcut table from hyprland.conf ──
        # Reads ~/.config/hypr/hyprland.conf, surfaces every NYXUS app
        # bind plus the most useful Hyprland defaults so users can
        # discover (and sanity-check) every key combo from Settings.

        nyxus_grp = Adw.PreferencesGroup(
            title="NYXUS app shortcuts",
            description="Launches the named NYXUS application")
        self.add_group(nyxus_grp)
        wm_grp = Adw.PreferencesGroup(
            title="Window &amp; workspace",
            description="Hyprland window manager bindings")
        self.add_group(wm_grp)
        sys_grp = Adw.PreferencesGroup(
            title="System &amp; overlays",
            description="EWW panels, audio, brightness, screenshots")
        self.add_group(sys_grp)

        # Live-parse hyprland.conf so this list never drifts from the
        # real keybind state. Falls back to a curated set if the config
        # is missing (first-boot, recovery shell, etc.).
        live = parse_hypr_binds()
        nyxus_set: List[Tuple[str, str]] = []
        if live:
            seen: set = set()
            for label, chord, _raw in live:
                # NYXUS app launches → top group; dedupe by chord.
                if (label.startswith("NYXUS ")
                        or label in ("Start menu (rofi)",
                                     "Spotlight", "App switcher",
                                     "Lock screen", "Logout menu",
                                     "Doctor (diagnostics)",
                                     "Screenshot", "Screenshot region")):
                    if chord not in seen:
                        nyxus_set.append((label, chord))
                        seen.add(chord)
            nyxus_grp.set_description(
                "Parsed live from ~/.config/hypr/hyprland.conf "
                f"({len(nyxus_set)} binds)")
        if not nyxus_set:
            # Fallback curated list — kept in sync with shipped config.
            nyxus_set = [
                ("NYXUS Clipboard",    "Super + V"),
                ("NYXUS Files",        "Super + E"),
                ("NYXUS Updater",      "Super + Ctrl + U"),
                ("NYXUS Store",        "Super + Shift + A"),
                ("NYXUS Backup",       "Super + Ctrl + B"),
                ("NYXUS Drop",         "Super + Ctrl + D"),
                ("NYXUS Record",       "Super + Shift + R"),
                ("NYXUS Context menu", "Super + Ctrl + M"),
                ("NYXUS Wallpaper Studio", "Super + W"),
                ("NYXUS Wallpaper",    "Super + Alt + W"),
                ("NYXUS Spotlight",    "Super + Space"),
                ("NYXUS Terminal",     "Super + Return"),
                ("Start menu (rofi)",  "Super + D"),
                ("App switcher",       "Super + Tab"),
                ("Lock screen",        "Super + L"),
                ("Logout menu",        "Super + Shift + E"),
                ("Doctor (diagnostics)","Super + Shift + H"),
            ]
            nyxus_grp.set_description(
                "Curated fallback — hyprland.conf not found")
        for label, chord in nyxus_set:
            nyxus_grp.add(kv_row(label, chord))

        for label, chord in (
            ("Close active window",      "Super + Q"),
            ("Toggle floating",          "Super + Shift + T"),
            ("Fullscreen (maximize)",    "Super + F"),
            ("Fullscreen (true)",        "Super + Shift + F"),
            ("Center window",            "Super + Shift + C"),
            ("Focus left/right/up/down", "Super + ←/→/↑/↓"),
            ("Move window",              "Super + Shift + ←/→/↑/↓"),
            ("Resize window",            "Super + Ctrl + ←/→/↑/↓"),
            ("Workspace 1-10",           "Super + 1..0"),
            ("Move to workspace 1-10",   "Super + Shift + 1..0"),
            ("Scratchpad toggle",        "Super + S"),
        ):
            wm_grp.add(kv_row(label, chord))

        for label, chord in (
            ("Quick Settings",      "Super + A"),
            ("Notifications",       "Super + N"),
            ("Wi-Fi popup",         "Super + W"),
            ("Mixer",               "Super + M"),
            ("Calendar",            "Super + C"),
            ("Bluetooth",           "Super + Shift + B"),
            ("Power menu",          "Super + Escape"),
            ("Dashboard",           "Super + `"),
            ("Cheatsheet",          "Super + /"),
            ("Screenshot region",   "Print"),
            ("Screenshot full",     "Shift + Print"),
            ("Volume up/down/mute", "XF86 keys"),
            ("Brightness up/down",  "XF86 keys"),
        ):
            sys_grp.add(kv_row(label, chord))

        self.add_pill(status_pill("hypr", "ok"))

    # ── kb_options helpers (used by Compose + grp comboboxes) ─────────
    def _kb_options_csv(self) -> str:
        rc, out, _ = sh(["hyprctl", "getoption", "input:kb_options",
                         "-j"], timeout=2)
        try:
            return (json.loads(out or "{}").get("str", "") or "").strip()
        except Exception:
            return ""

    @staticmethod
    def _token_with_prefix(csv: str, prefix: str) -> Optional[str]:
        for tok in (t.strip() for t in csv.split(",")):
            if tok and tok.startswith(prefix):
                return tok
        return None

    def _apply_kb_token(self, family_prefix: str, new_token: str) -> None:
        # Use canonical local state (set in build) instead of re-reading
        # hyprctl every call — fixes race when user toggles compose +
        # grp back-to-back before the previous async apply lands.
        cur = getattr(self, "_kb_csv", None)
        if cur is None:
            cur = self._kb_options_csv()
        keep = [t.strip() for t in cur.split(",")
                if t.strip() and not t.strip().startswith(family_prefix)]
        if new_token:
            keep.append(new_token)
        csv = ",".join(keep)
        # Update canonical state synchronously so a follow-up toggle
        # composes against the up-to-date CSV, not a stale read.
        self._kb_csv = csv
        sh_async(
            ["hyprctl", "keyword", "input:kb_options", csv],
            lambda r: self.toast(
                "applied" if r[0] == 0 else "apply failed"),
            timeout=2)
        self._persist_kb_options(csv)
        self._ensure_input_source_line()

    def _persist_kb_options(self, csv: str) -> None:
        p = Path.home() / ".config" / "hypr" / "nyxus-input.conf"
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.warning("mkdir hypr: %s", e)
            self.toast(f"persist mkdir failed: {e}")
            return
        body = ("# Auto-managed by NYXUS Settings — Keyboard page.\n"
                "input {\n"
                f"    kb_options = {csv}\n"
                "}\n")
        try:
            tmp = p.with_suffix(".conf.tmp")
            tmp.write_text(body, encoding="utf-8")
            os.replace(tmp, p)
        except OSError as e:
            log.warning("write nyxus-input.conf: %s", e)
            self.toast(f"persist write failed: {e}")

    def _ensure_input_source_line(self) -> None:
        hp = _HYPRLAND_CONF
        if not hp.exists():
            self.toast("hyprland.conf missing — kb_options won't persist")
            return
        try:
            text = hp.read_text(encoding="utf-8")
        except OSError as e:
            log.warning("read hyprland.conf: %s", e)
            self.toast(f"can't read hyprland.conf: {e}")
            return
        if "nyxus-input.conf" in text:
            return
        try:
            with open(hp, "a", encoding="utf-8") as fh:
                fh.write("\n# nyxus input overrides "
                         "(auto-managed by Settings)\n"
                         "source = ./nyxus-input.conf\n")
        except OSError as e:
            log.warning("append input source line: %s", e)
            self.toast(
                f"can't persist to hyprland.conf: {e} — "
                "keyboard options won't survive reboot")

    # NB: the parsed-shortcut table below is unaffected by the helpers
    # above — they only mutate kb_options tokens, never bind lines.


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

        # ── Touchpad gestures (libinput-gestures) ────────────────────
        gst_grp = Adw.PreferencesGroup(
            title="Touchpad gestures",
            description="3- & 4-finger swipes powered by "
                        "libinput-gestures (user systemd unit)")
        self.add_group(gst_grp)
        if not have("libinput-gestures"):
            gst_grp.add(empty_row(
                "libinput-gestures not installed",
                "Install libinput-gestures to enable swipe gestures."))
        else:
            rc_a, _, _ = sh(
                ["systemctl", "--user", "is-active",
                 "libinput-gestures.service"], timeout=2)
            active = (rc_a == 0)
            sw = Adw.SwitchRow(
                title="Enable swipe gestures",
                subtitle="3-finger L/R = workspace · 4-finger up = "
                         "fullscreen · 4-finger down = toggle floating")
            sw.set_active(active)
            sw.connect("notify::active", self._on_gestures_toggle)
            gst_grp.add(sw)
            gst_grp.add(action_row(
                "Reset to NYXUS defaults",
                "~/.config/libinput-gestures.conf",
                "Reset",
                lambda: self._write_gestures_conf()))

    def _on_gestures_toggle(self, sw: Adw.SwitchRow,
                            _pspec: object) -> None:
        wanted = sw.get_active()
        # Make sure a config file exists before enabling, else the
        # service will fail with no gestures defined.
        cfg = Path.home() / ".config" / "libinput-gestures.conf"
        if wanted and not cfg.exists():
            self._write_gestures_conf(silent=True)
        verb = "enable --now" if wanted \
               else "disable --now"
        sh_async(
            f"systemctl --user {verb} libinput-gestures.service",
            lambda r: self.toast(
                "gestures " + ("on" if wanted else "off")
                if r[0] == 0
                else f"systemd failed: {(r[2] or '').strip()[:60]}"))

    def _write_gestures_conf(self, *, silent: bool = False) -> None:
        cfg = Path.home() / ".config" / "libinput-gestures.conf"
        try:
            cfg.parent.mkdir(parents=True, exist_ok=True)
            cfg.write_text(
                "# nyxus libinput-gestures defaults — "
                "edit freely, keep header to mark as managed\n"
                "gesture swipe left  3 hyprctl dispatch workspace +1\n"
                "gesture swipe right 3 hyprctl dispatch workspace -1\n"
                "gesture swipe up    4 hyprctl dispatch fullscreen 0\n"
                "gesture swipe down  4 hyprctl dispatch togglefloating\n"
                "gesture pinch in    2 hyprctl dispatch killactive\n",
                encoding="utf-8")
            if not silent:
                self.toast("gestures config reset")
        except OSError as e:
            log.warning("write gestures conf: %s", e)
            if not silent:
                self.toast(f"write failed: {e}")


# ──────────────────────────────────────────────────────────────────────
# PRIVACY — hardware presence, indicators, telemetry audit
# ──────────────────────────────────────────────────────────────────────
class PrivacyPage(SectionPage):
    """Capture hardware audit + live recording watch + location service
    control + recent-activity clearing + telemetry audit + NYXUS data
    transparency. All controls are real:
      · pkexec systemctl       — toggle/mask geoclue
      · ~/.local/share/recently-used.xbel — clear recent files
      · ~/.bash_history, ~/.zsh_history — clear shell history
      · ~/.cache/thumbnails/   — clear thumbnail cache
      · NYXUS prefs            — crash-report opt-in (own-controlled)
    """
    KEY = "privacy"

    def build(self) -> None:
        self.hw_grp = Adw.PreferencesGroup(
            title="Capture hardware",
            description="Devices that CAN see/hear you when an app uses them")
        self.add_group(self.hw_grp)
        self.active_grp = Adw.PreferencesGroup(
            title="Active right now",
            description="Apps currently holding a microphone or camera stream")
        self.add_group(self.active_grp)
        self.loc_grp = Adw.PreferencesGroup(
            title="Location services",
            description="GeoClue exposes location data to D-Bus consumers. "
                        "Mask to fully prevent it from ever starting.")
        self.add_group(self.loc_grp)
        self.activity_grp = Adw.PreferencesGroup(
            title="Activity &amp; history",
            description="Clear traces of what you've done on this system")
        self.add_group(self.activity_grp)
        self.idx_grp = Adw.PreferencesGroup(
            title="File indexing",
            description="Background indexers that catalog your files for search")
        self.add_group(self.idx_grp)
        self.tel_grp = Adw.PreferencesGroup(
            title="Telemetry &amp; opt-outs",
            description="NYXUS ships zero telemetry. These show third-party "
                        "env-var opt-outs.")
        self.add_group(self.tel_grp)
        self.data_grp = Adw.PreferencesGroup(
            title="NYXUS data",
            description="What NYXUS itself stores about you, and where")
        self.add_group(self.data_grp)

        self._render()
        self.schedule_refresh(5000, self._tick)

    def _tick(self) -> bool:
        # Capture watch + activity sizes change frequently.
        self._render_active()
        self._render_activity()
        return True

    def _render(self) -> None:
        self._render_hw()
        self._render_active()
        self._render_location()
        self._render_activity()
        self._render_indexing()
        self._render_telemetry()
        self._render_nyxus_data()
        self.clear_pills()
        cams_n = len(self._enumerate_cameras())
        mics_n = len(self._enumerate_microphones())
        self.add_pill(status_pill(f"{cams_n} cam · {mics_n} mic",
                                  "ok" if cams_n + mics_n > 0 else "warn"))

    # ── Hardware ─────────────────────────────────────────────
    def _enumerate_cameras(self) -> list:
        return sorted(Path("/dev").glob("video*"))

    def _enumerate_microphones(self) -> list:
        mics = []
        if have("pactl"):
            rc, out, _ = sh(["pactl", "list", "sources", "short"], timeout=3)
            for line in out.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2 and ".monitor" not in parts[1]:
                    mics.append(parts[1])
        return mics

    def _render_hw(self) -> None:
        _clear_group(self.hw_grp)
        cams = self._enumerate_cameras()
        mics = self._enumerate_microphones()
        self.hw_grp.add(kv_row("Cameras",
                               f"{len(cams)} device(s)" if cams
                               else "none detected"))
        for c in cams:
            self.hw_grp.add(kv_row(f"  {c.name}", str(c)))
        self.hw_grp.add(kv_row("Microphones",
                               f"{len(mics)} input(s)" if mics
                               else "none detected"))
        for m in mics:
            self.hw_grp.add(kv_row("  source", m[:60]))

    # ── Active capture ───────────────────────────────────────
    def _render_active(self) -> None:
        _clear_group(self.active_grp)
        cams = self._enumerate_cameras()
        active_audio = set()
        active_video = []
        if have("pw-dump"):
            rc, out, _ = sh(["pw-dump"], timeout=4)
            try:
                data = json.loads(out) if out.strip() else []
                for node in data:
                    info = node.get("info", {}) or {}
                    props = info.get("props", {}) or {}
                    state = info.get("state", "")
                    media = props.get("media.class", "")
                    name = (props.get("application.name")
                            or props.get("node.name") or "")
                    if (state == "running" and name
                            and ("Stream/Input" in media)):
                        active_audio.add(name)
            except Exception:
                pass
        elif have("pw-cli"):
            rc, out, _ = sh(["pw-cli", "ls", "Node"], timeout=4)
            for m in re.finditer(
                    r'application\.name\s*=\s*"([^"]+)".*?'
                    r'media\.class\s*=\s*"Stream/Input/Audio"',
                    out, re.DOTALL):
                active_audio.add(m.group(1))
        if have("fuser"):
            for c in cams:
                rc, out, _ = sh(["fuser", str(c)], timeout=2)
                if rc == 0 and out.strip():
                    active_video.append(c.name)
        if active_video:
            for v in active_video:
                row = Adw.ActionRow(title=f"📹 {v}",
                                    subtitle="camera in use right now")
                row.add_css_class("nyx-warn-row")
                self.active_grp.add(row)
        if active_audio:
            for a in sorted(active_audio)[:15]:
                row = Adw.ActionRow(title=f"🎤 {a}",
                                    subtitle="audio input client")
                self.active_grp.add(row)
        if not active_video and not active_audio:
            self.active_grp.add(empty_row(
                "No active capture detected",
                "Nothing is recording you right now"))

    # ── Location ─────────────────────────────────────────────
    def _render_location(self) -> None:
        _clear_group(self.loc_grp)
        rc1, st_active, _   = sh(["systemctl", "is-active",
                                  "geoclue.service"], timeout=2)
        rc2, st_enabled, _  = sh(["systemctl", "is-enabled",
                                  "geoclue.service"], timeout=2)
        active = st_active.strip()
        enabled = st_enabled.strip()
        is_masked = (enabled == "masked")
        self.loc_grp.add(kv_row("Service status", active or "?"))
        self.loc_grp.add(kv_row("Boot state", enabled or "?"))

        master_row = Adw.ActionRow(
            title="Location services",
            subtitle="master switch — when off, no app can see your location")
        sw = Gtk.Switch()
        sw.set_valign(Gtk.Align.CENTER)
        sw.set_active(active == "active" and not is_masked)
        sw.connect("notify::active", self._on_location_toggled)
        master_row.add_suffix(sw)
        self.loc_grp.add(master_row)

        if is_masked:
            self.loc_grp.add(action_row(
                "Unmask geoclue",
                "Currently masked — even apps that ask cannot start it.",
                "Unmask",
                lambda: sh_async(
                    ["pkexec", "systemctl", "unmask", "geoclue.service"],
                    lambda r: (self.toast(
                        "unmasked" if r[0] == 0 else "needs admin"),
                        self._render_location()),
                    timeout=10)))
        else:
            self.loc_grp.add(action_row(
                "Mask geoclue (strongest)",
                "Prevents any app from ever starting the location service",
                "Mask",
                lambda: sh_async(
                    ["pkexec", "systemctl", "mask", "geoclue.service"],
                    lambda r: (self.toast(
                        "masked" if r[0] == 0 else "needs admin"),
                        self._render_location()),
                    timeout=10),
                css="nyx-pill-warn"))

    def _on_location_toggled(self, sw, _p) -> None:
        wanted = sw.get_active()
        cmd = ["pkexec", "systemctl",
               "enable" if wanted else "disable",
               "--now", "geoclue.service"]
        sh_async(cmd,
                 lambda r: (self.toast(
                     "location " + ("on" if wanted else "off")
                     if r[0] == 0 else "needs admin"),
                     self._render_location()),
                 timeout=10)

    # ── Activity & history ───────────────────────────────────
    def _render_activity(self) -> None:
        _clear_group(self.activity_grp)
        home = Path.home()

        # Recent files (GTK + Adw apps)
        xbel = home / ".local/share/recently-used.xbel"
        recent_n = 0
        if xbel.exists():
            try:
                recent_n = xbel.read_text(errors="ignore").count("<bookmark ")
            except Exception:
                pass
        recent_row = Adw.ActionRow(
            title="Recent files",
            subtitle=f"{recent_n} entries in recently-used.xbel")
        if recent_n > 0:
            btn = Gtk.Button(label="Clear")
            btn.add_css_class("nyx-pill-warn")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", lambda _b: self._clear_path(
                xbel, "recent files cleared"))
            recent_row.add_suffix(btn)
        self.activity_grp.add(recent_row)

        # Shell history
        for hist_name, label in (("bash_history", "Bash history"),
                                 ("zsh_history",  "Zsh history"),
                                 ("python_history", "Python REPL history")):
            p = home / f".{hist_name}"
            if p.exists():
                try:
                    n = sum(1 for _ in p.open(errors="ignore"))
                except Exception:
                    n = 0
                row = Adw.ActionRow(
                    title=label, subtitle=f"{n} lines in ~/.{hist_name}")
                if n > 0:
                    btn = Gtk.Button(label="Clear")
                    btn.add_css_class("nyx-pill-warn")
                    btn.set_valign(Gtk.Align.CENTER)
                    btn.connect("clicked", lambda _b, pp=p, ll=label:
                                self._clear_path(pp, f"{ll.lower()} cleared"))
                    row.add_suffix(btn)
                self.activity_grp.add(row)

        # Thumbnail cache
        thumb = home / ".cache/thumbnails"
        thumb_size = self._dir_size(thumb)
        thumb_row = Adw.ActionRow(
            title="Thumbnail cache",
            subtitle=f"{self._fmt_bytes(thumb_size)} in ~/.cache/thumbnails")
        if thumb_size > 0:
            btn = Gtk.Button(label="Clear")
            btn.add_css_class("nyx-pill-warn")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", lambda _b: self._clear_dir(
                thumb, "thumbnail cache cleared"))
            thumb_row.add_suffix(btn)
        self.activity_grp.add(thumb_row)

        # Trash
        trash = home / ".local/share/Trash/files"
        if trash.exists():
            try:
                n = len(list(trash.iterdir()))
            except Exception:
                n = 0
            trash_row = Adw.ActionRow(
                title="Trash", subtitle=f"{n} item(s)")
            if n > 0:
                btn = Gtk.Button(label="Empty")
                btn.add_css_class("nyx-pill-warn")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", lambda _b: sh_async(
                    ["sh", "-c", "gio trash --empty 2>/dev/null || "
                     "rm -rf ~/.local/share/Trash/files/* "
                     "~/.local/share/Trash/info/*"],
                    lambda r: (self.toast("trash emptied"),
                               self._render_activity()),
                    timeout=10))
                trash_row.add_suffix(btn)
            self.activity_grp.add(trash_row)

    def _clear_path(self, p: Path, msg: str) -> None:
        try:
            p.write_text("")
            self.toast(msg)
            self._render_activity()
        except Exception as e:
            self.toast(f"failed: {e}")

    def _clear_dir(self, p: Path, msg: str) -> None:
        if not p.exists():
            return
        sh_async(
            ["sh", "-c", f"rm -rf {str(p)}/*"],
            lambda r: (self.toast(msg if r[0] == 0 else "failed"),
                       self._render_activity()),
            timeout=10)

    @staticmethod
    def _dir_size(p: Path) -> int:
        if not p.exists():
            return 0
        total = 0
        try:
            for f in p.rglob("*"):
                if f.is_file():
                    try:
                        total += f.stat().st_size
                    except Exception:
                        pass
        except Exception:
            pass
        return total

    @staticmethod
    def _fmt_bytes(n: int) -> str:
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024:
                return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
            n /= 1024
        return f"{n:.1f} PB"

    # ── File indexing ────────────────────────────────────────
    def _render_indexing(self) -> None:
        _clear_group(self.idx_grp)
        any_indexer = False
        if have("tracker3"):
            any_indexer = True
            rc, out, _ = sh(["tracker3", "status"], timeout=3)
            self.idx_grp.add(kv_row("Tracker", out.split("\n")[0][:60]
                                    if out.strip() else "running"))
            self.idx_grp.add(action_row(
                "Pause indexing",
                "Stops Tracker from scanning new files",
                "Pause",
                lambda: sh_async(
                    ["tracker3", "daemon", "--pause", "nyxus-settings"],
                    lambda r: self.toast("paused" if r[0] == 0
                                         else "failed"),
                    timeout=4)))
            self.idx_grp.add(action_row(
                "Reset Tracker database",
                "Wipes the index — Tracker re-scans from scratch",
                "Reset",
                lambda: sh_async(
                    ["tracker3", "reset", "--filesystem"],
                    lambda r: self.toast("reset" if r[0] == 0
                                         else "failed"),
                    timeout=15),
                css="nyx-pill-warn"))
        if have("baloo_file") or have("balooctl"):
            any_indexer = True
            rc, out, _ = sh(["balooctl", "status"], timeout=3)
            self.idx_grp.add(kv_row("Baloo", out.split("\n")[0][:60]
                                    if out.strip() else "present"))
            self.idx_grp.add(action_row(
                "Disable Baloo",
                "Stops KDE file indexer permanently",
                "Disable",
                lambda: sh_async(
                    ["balooctl", "disable"],
                    lambda r: self.toast("disabled" if r[0] == 0
                                         else "failed"),
                    timeout=4)))
        if not any_indexer:
            self.idx_grp.add(empty_row(
                "No file indexer installed",
                "NYXUS does not ship one by default — searches are live"))

    # ── Telemetry audit ──────────────────────────────────────
    def _render_telemetry(self) -> None:
        _clear_group(self.tel_grp)
        for var, on_val in (("DO_NOT_TRACK",                "1"),
                            ("DOTNET_CLI_TELEMETRY_OPTOUT", "1"),
                            ("HOMEBREW_NO_ANALYTICS",       "1"),
                            ("NEXT_TELEMETRY_DISABLED",     "1"),
                            ("GATSBY_TELEMETRY_DISABLED",   "1"),
                            ("VUE_CLI_TELEMETRY_DISABLED",  "1"),
                            ("AZURE_CORE_COLLECT_TELEMETRY","0"),
                            ("POWERSHELL_TELEMETRY_OPTOUT", "1")):
            v = os.environ.get(var, "")
            ok = (v == on_val)
            self.tel_grp.add(kv_row(
                var, "opted out ✓" if ok else f"unset ({v or '∅'})"))

        # NYXUS-managed: write a profile.d snippet that exports them all
        self.tel_grp.add(action_row(
            "Apply all opt-outs system-wide",
            "Writes /etc/profile.d/nyxus-no-telemetry.sh (admin prompt)",
            "Apply",
            lambda: self._apply_no_telemetry()))

    def _apply_no_telemetry(self) -> None:
        body = textwrap.dedent("""\
            # nyxus-managed: third-party telemetry opt-outs
            export DO_NOT_TRACK=1
            export DOTNET_CLI_TELEMETRY_OPTOUT=1
            export HOMEBREW_NO_ANALYTICS=1
            export NEXT_TELEMETRY_DISABLED=1
            export GATSBY_TELEMETRY_DISABLED=1
            export VUE_CLI_TELEMETRY_DISABLED=1
            export AZURE_CORE_COLLECT_TELEMETRY=0
            export POWERSHELL_TELEMETRY_OPTOUT=1
            """)
        sh_async(
            ["pkexec", "sh", "-c",
             "cat > /etc/profile.d/nyxus-no-telemetry.sh "
             "<<'NYXUS_EOF'\n" + body + "NYXUS_EOF\n"
             "chmod 0644 /etc/profile.d/nyxus-no-telemetry.sh"],
            lambda r: self.toast(
                "applied — log out and back in to take effect"
                if r[0] == 0 else "needs admin"),
            timeout=8)

    # ── NYXUS data transparency ──────────────────────────────
    def _render_nyxus_data(self) -> None:
        _clear_group(self.data_grp)
        # Confirm zero NYXUS analytics
        zero_row = Adw.ActionRow(
            title="NYXUS analytics",
            subtitle="NYXUS sends nothing about you to anyone, ever")
        zero = Gtk.Label(label="✓ none")
        zero.add_css_class("nyx-kv-value")
        zero_row.add_suffix(zero)
        self.data_grp.add(zero_row)

        # Where NYXUS stores its data
        data_dirs = [
            ("~/.config/nyxus",        "settings + per-app prefs"),
            ("~/.local/share/nyxus",   "stickies, notes, app data"),
            ("~/.cache/nyxus",         "thumbnails, runtime cache"),
        ]
        for path_s, desc in data_dirs:
            p = Path(path_s.replace("~", str(Path.home())))
            sz = self._dir_size(p) if p.exists() else 0
            row = Adw.ActionRow(
                title=path_s, subtitle=desc)
            val = Gtk.Label(label=self._fmt_bytes(sz)
                            if p.exists() else "(not created)")
            val.add_css_class("nyx-kv-value")
            row.add_suffix(val)
            if p.exists() and have("xdg-open"):
                btn = Gtk.Button(label="Open")
                btn.add_css_class("nyx-pill")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", lambda _b, pp=p:
                            fire_and_forget(f"xdg-open {pp}"))
                row.add_suffix(btn)
            self.data_grp.add(row)

        # Crash reporter opt-in (NYXUS-controlled)
        prefs = load_prefs()
        crash_optin = bool(prefs.get("privacy", {}).get("crash_optin", False))
        crash_row = Adw.ActionRow(
            title="Send crash logs to me",
            subtitle="OFF by default. When ON, nyxus_error.py uploads "
                     "anonymized stack traces. Off = nothing leaves your "
                     "machine.")
        sw = Gtk.Switch()
        sw.set_valign(Gtk.Align.CENTER)
        sw.set_active(crash_optin)
        sw.connect("notify::active", self._on_crash_optin)
        crash_row.add_suffix(sw)
        self.data_grp.add(crash_row)
        # Quick launcher to the crash-report viewer UI
        self.data_grp.add(action_row(
            "Open crash report viewer",
            "List, inspect and submit captured coredumps "
            "(nyxus-crash-report)",
            "Open",
            lambda: fire_and_forget("nyxus-crash-report")))

    def _on_crash_optin(self, sw, _p) -> None:
        prefs = load_prefs()
        prefs.setdefault("privacy", {})["crash_optin"] = sw.get_active()
        save_prefs(prefs)
        self.toast("crash reports " + ("on" if sw.get_active() else "off"))


# ──────────────────────────────────────────────────────────────────────
# APPS — installed count, default mime apps, autostart
# ──────────────────────────────────────────────────────────────────────
class AppsPage(SectionPage):
    """Installed GUI apps + default-app picker + autostart + Flatpak.
    All controls are real:
      · pkexec pacman -Rns <pkg>     — uninstall native apps
      · flatpak uninstall <ref>      — uninstall flatpaks
      · xdg-mime default <d> <mime>  — set per-mime default app
      · ~/.config/autostart/*.desktop — add/remove startup entries
    """
    KEY = "apps"

    DEFAULT_MIMES = [
        ("Web browser",   "x-scheme-handler/https"),
        ("Email",         "x-scheme-handler/mailto"),
        ("Terminal",      "x-scheme-handler/terminal"),
        ("Plain text",    "text/plain"),
        ("PDF",           "application/pdf"),
        ("Image",         "image/png"),
        ("Image (JPEG)",  "image/jpeg"),
        ("Audio",         "audio/flac"),
        ("Audio (MP3)",   "audio/mpeg"),
        ("Video",         "video/mp4"),
        ("Archive",       "application/zip"),
        ("File manager",  "inode/directory"),
    ]

    def build(self) -> None:
        self.cnt_grp = Adw.PreferencesGroup(title="Installed packages")
        self.add_group(self.cnt_grp)

        self.def_grp = Adw.PreferencesGroup(
            title="Default apps",
            description="Pick which app opens which file or URL type")
        self.add_group(self.def_grp)

        self.installed_grp = Adw.PreferencesGroup(
            title="GUI applications",
            description="Apps with a .desktop entry — Launch or Uninstall any")
        self.add_group(self.installed_grp)

        self.flatpak_grp = Adw.PreferencesGroup(
            title="Flatpak",
            description="Sandboxed apps installed via Flatpak")
        self.add_group(self.flatpak_grp)

        self.auto_grp = Adw.PreferencesGroup(
            title="Run at login",
            description="Anything here starts when you log in "
                        "(~/.config/autostart/)")
        self.add_group(self.auto_grp)

        self._desktop_index = self._build_desktop_index()
        self._render()
        self.schedule_refresh(20000, self._tick)

    def _tick(self) -> bool:
        # Refresh package counts and any user changes; the heavy desktop
        # index only re-reads if a file was added/removed.
        new_idx = self._build_desktop_index()
        if {p for _, p, _, _ in new_idx} != \
                {p for _, p, _, _ in self._desktop_index}:
            self._desktop_index = new_idx
            self._render_installed()
        self._render_counts()
        self._render_autostart()
        return True

    def _render(self) -> None:
        self._render_counts()
        self._render_defaults()
        self._render_installed()
        self._render_flatpak()
        self._render_autostart()
        self.clear_pills()
        n = len(self._desktop_index)
        self.add_pill(status_pill(f"{n} apps", "ok"))

    # ── Counts ───────────────────────────────────────────────
    def _render_counts(self) -> None:
        _clear_group(self.cnt_grp)
        if not have("pacman"):
            self.cnt_grp.add(empty_row("pacman not available", ""))
            return
        rc, out, _ = sh(["pacman", "-Qq"], timeout=4)
        n_total = len(out.splitlines()) if rc == 0 else 0
        rc, out, _ = sh(["pacman", "-Qqe"], timeout=4)
        n_explicit = len(out.splitlines()) if rc == 0 else 0
        rc, out, _ = sh(["pacman", "-Qqm"], timeout=4)
        n_foreign = len(out.splitlines()) if rc == 0 else 0
        self.cnt_grp.add(kv_row("Total", str(n_total)))
        self.cnt_grp.add(kv_row("Explicitly installed", str(n_explicit)))
        self.cnt_grp.add(kv_row("Foreign / AUR / local", str(n_foreign)))
        if have("flatpak"):
            rc, out, _ = sh(["flatpak", "list", "--app", "--columns=name"],
                            timeout=4)
            n_fp = len([l for l in out.splitlines() if l.strip()]) - 1
            self.cnt_grp.add(kv_row("Flatpak apps", str(max(n_fp, 0))))

    # ── Default apps ─────────────────────────────────────────
    def _render_defaults(self) -> None:
        _clear_group(self.def_grp)
        if not have("xdg-mime"):
            self.def_grp.add(empty_row("xdg-mime not installed",
                                       "Install xdg-utils"))
            return
        for label, mime in self.DEFAULT_MIMES:
            handlers = self._find_handlers(mime)
            rc, cur_out, _ = sh(["xdg-mime", "query", "default", mime],
                                timeout=2)
            cur = cur_out.strip()
            row = Adw.ActionRow(
                title=label,
                subtitle=mime + (
                    "  ·  " + (cur.replace(".desktop", "") or "(none)")
                    if cur else "  ·  (none)"))
            if not handlers:
                row.add_suffix(Gtk.Label(label="no handlers"))
                self.def_grp.add(row)
                continue
            labels = [name for name, _ in handlers]
            files = [d for _, d in handlers]
            try:
                sel = files.index(cur)
            except ValueError:
                sel = 0
            dd = Gtk.DropDown.new_from_strings(labels)
            dd.set_selected(sel)
            dd.set_valign(Gtk.Align.CENTER)
            dd.connect(
                "notify::selected",
                lambda d, _p, m=mime, fs=files, ls=labels:
                    self._on_default_changed(d, m, fs, ls))
            row.add_suffix(dd)
            self.def_grp.add(row)

    def _find_handlers(self, mime: str) -> list:
        """Return [(human_name, desktop_filename), ...] handling `mime`."""
        out = []
        seen = set()
        for base in ("/usr/share/applications",
                     str(Path.home() / ".local/share/applications")):
            p = Path(base)
            if not p.exists():
                continue
            for f in p.glob("*.desktop"):
                if f.name in seen:
                    continue
                try:
                    txt = f.read_text(errors="ignore")
                except Exception:
                    continue
                if "MimeType=" not in txt:
                    continue
                mt_line = next((l for l in txt.splitlines()
                                if l.startswith("MimeType=")), "")
                if mime not in mt_line:
                    continue
                if "NoDisplay=true" in txt or "Hidden=true" in txt:
                    continue
                name = ""
                for ln in txt.splitlines():
                    if ln.startswith("Name="):
                        name = ln.split("=", 1)[1].strip()
                        break
                if name:
                    out.append((name, f.name))
                    seen.add(f.name)
        out.sort()
        return out

    def _on_default_changed(self, dd, mime: str,
                            files: list, labels: list) -> None:
        idx = dd.get_selected()
        if not (0 <= idx < len(files)):
            return
        sh_async(
            ["xdg-mime", "default", files[idx], mime],
            lambda r: self.toast(
                f"{labels[idx]} → default for {mime}" if r[0] == 0
                else "failed"),
            timeout=4)

    # ── Installed apps with uninstall ────────────────────────
    def _build_desktop_index(self) -> list:
        """Return [(name, desktop_path, exec, owning_pkg), ...]
        sorted alphabetically. Excludes NoDisplay/Hidden entries."""
        items = []
        seen = set()
        for base in ("/usr/share/applications",
                     str(Path.home() / ".local/share/applications")):
            p = Path(base)
            if not p.exists():
                continue
            for f in sorted(p.glob("*.desktop")):
                if f.name in seen:
                    continue
                try:
                    txt = f.read_text(errors="ignore")
                except Exception:
                    continue
                if "NoDisplay=true" in txt or "Hidden=true" in txt:
                    continue
                if "Type=Application" not in txt:
                    continue
                name = ""
                exec_s = ""
                for ln in txt.splitlines():
                    if ln.startswith("Name=") and not name:
                        name = ln.split("=", 1)[1].strip()
                    elif ln.startswith("Exec=") and not exec_s:
                        exec_s = ln.split("=", 1)[1].strip()
                if not name:
                    continue
                items.append((name, str(f), exec_s, ""))
                seen.add(f.name)
        items.sort(key=lambda t: t[0].lower())
        return items

    def _pkg_owner(self, path: str) -> str:
        if not have("pacman"):
            return ""
        rc, out, _ = sh(["pacman", "-Qoq", path], timeout=2)
        if rc == 0 and out.strip():
            return out.strip().split("\n")[0]
        return ""

    def _render_installed(self) -> None:
        _clear_group(self.installed_grp)
        # Search filter
        search_row = Adw.ActionRow(
            title="Search",
            subtitle="filter the list below by app name")
        entry = Gtk.Entry()
        entry.set_placeholder_text("type to filter…")
        entry.set_size_request(220, -1)
        entry.set_valign(Gtk.Align.CENTER)
        entry.connect("changed", self._on_app_filter_changed)
        search_row.add_suffix(entry)
        self.installed_grp.add(search_row)

        # Build rows (cap to 200 visible, search to find more)
        self._app_rows = []
        for (name, path, exec_s, _) in self._desktop_index[:200]:
            row = Adw.ActionRow(title=name, subtitle=Path(path).name)
            if exec_s:
                btn_l = Gtk.Button(label="Launch")
                btn_l.add_css_class("nyx-pill")
                btn_l.set_valign(Gtk.Align.CENTER)
                btn_l.connect(
                    "clicked",
                    lambda _b, e=exec_s: fire_and_forget(
                        "gtk-launch " + Path(path).stem
                        if have("gtk-launch")
                        else re.sub(r"%[fFuUdDnNickvm]", "", e).strip()))
                row.add_suffix(btn_l)
            btn_u = Gtk.Button(label="Uninstall")
            btn_u.add_css_class("nyx-pill-warn")
            btn_u.set_valign(Gtk.Align.CENTER)
            btn_u.connect(
                "clicked",
                lambda _b, n=name, p=path: self._uninstall_app(n, p))
            row.add_suffix(btn_u)
            self.installed_grp.add(row)
            self._app_rows.append((name.lower(), row))

        if len(self._desktop_index) > 200:
            self.installed_grp.add(empty_row(
                f"+ {len(self._desktop_index) - 200} more",
                "use the search field above to find specific apps"))

    def _on_app_filter_changed(self, entry) -> None:
        q = entry.get_text().strip().lower()
        for name_low, row in getattr(self, "_app_rows", []):
            row.set_visible(not q or q in name_low)

    def _uninstall_app(self, name: str, desktop_path: str) -> None:
        owner = self._pkg_owner(desktop_path)
        if not owner:
            self.toast(f"{name}: no pacman package owns this .desktop")
            return
        # Confirmation dialog
        dlg = Adw.MessageDialog(
            transient_for=self.win,
            heading=f"Uninstall {name}?",
            body=f"This will run:\n  pkexec pacman -Rns {owner}\n\n"
                 "Dependencies that nothing else needs will also be "
                 "removed.")
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("ok", "Uninstall")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response", lambda d, resp, p=owner, n=name:
                    self._do_uninstall(resp, p, n))
        dlg.present()

    def _do_uninstall(self, resp: str, pkg: str, name: str) -> None:
        if resp != "ok":
            return
        sh_async(
            ["pkexec", "pacman", "-Rns", "--noconfirm", pkg],
            lambda r: (self.toast(
                f"{name} uninstalled" if r[0] == 0
                else f"failed: {r[2][:80] if r[2] else 'admin denied'}"),
                self._render()),
            timeout=60)

    # ── Flatpak ──────────────────────────────────────────────
    def _render_flatpak(self) -> None:
        _clear_group(self.flatpak_grp)
        if not have("flatpak"):
            self.flatpak_grp.add(empty_row(
                "Flatpak not installed",
                "Install flatpak to manage sandboxed apps"))
            return
        rc, out, _ = sh(
            ["flatpak", "list", "--app",
             "--columns=name,application,version"],
            timeout=5)
        lines = [l for l in out.splitlines() if l.strip()]
        # Skip header
        if lines and lines[0].lower().startswith("name"):
            lines = lines[1:]
        if not lines:
            self.flatpak_grp.add(empty_row(
                "No Flatpak apps installed", ""))
            return
        for ln in lines[:50]:
            parts = ln.split("\t") if "\t" in ln else ln.split(None, 2)
            name = parts[0] if parts else ln
            ref = parts[1] if len(parts) >= 2 else ""
            ver = parts[2] if len(parts) >= 3 else ""
            row = Adw.ActionRow(
                title=name, subtitle=f"{ref}  ·  {ver}" if ver else ref)
            if ref:
                btn = Gtk.Button(label="Uninstall")
                btn.add_css_class("nyx-pill-warn")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect(
                    "clicked",
                    lambda _b, r=ref, n=name:
                        self._uninstall_flatpak(n, r))
                row.add_suffix(btn)
            self.flatpak_grp.add(row)

    def _uninstall_flatpak(self, name: str, ref: str) -> None:
        dlg = Adw.MessageDialog(
            transient_for=self.win,
            heading=f"Uninstall Flatpak: {name}?",
            body=f"This will run:\n  flatpak uninstall -y {ref}")
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("ok", "Uninstall")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.connect("response", lambda d, resp, r=ref, n=name:
                    self._do_uninstall_flatpak(resp, r, n))
        dlg.present()

    def _do_uninstall_flatpak(self, resp: str, ref: str, name: str) -> None:
        if resp != "ok":
            return
        sh_async(
            ["flatpak", "uninstall", "-y", ref],
            lambda r: (self.toast(
                f"{name} uninstalled" if r[0] == 0 else "failed"),
                self._render()),
            timeout=120)

    # ── Autostart ────────────────────────────────────────────
    def _render_autostart(self) -> None:
        _clear_group(self.auto_grp)
        as_dir = Path.home() / ".config" / "autostart"
        items = sorted(as_dir.glob("*.desktop")) if as_dir.exists() else []

        # Add new — picker over installed apps
        add_row = Adw.ActionRow(
            title="Add an app to startup",
            subtitle="pick any installed app to launch at login")
        if self._desktop_index:
            names = [n for n, _, _, _ in self._desktop_index[:300]]
            paths = [p for _, p, _, _ in self._desktop_index[:300]]
            dd = Gtk.DropDown.new_from_strings(["(select)"] + names)
            dd.set_valign(Gtk.Align.CENTER)
            dd.connect(
                "notify::selected",
                lambda d, _p, ps=paths, ns=names:
                    self._on_autostart_add(d, ps, ns))
            add_row.add_suffix(dd)
        self.auto_grp.add(add_row)

        if not items:
            self.auto_grp.add(empty_row(
                "No autostart entries",
                "Pick an app above to add one"))
            return

        for it in items:
            try:
                txt = it.read_text(errors="ignore")
            except Exception:
                txt = ""
            display = it.stem
            for ln in txt.splitlines():
                if ln.startswith("Name="):
                    display = ln.split("=", 1)[1].strip()
                    break
            row = Adw.ActionRow(title=display, subtitle=str(it))
            btn = Gtk.Button(label="Remove")
            btn.add_css_class("nyx-pill-warn")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect(
                "clicked",
                lambda _b, p=it, n=display:
                    self._remove_autostart(p, n))
            row.add_suffix(btn)
            self.auto_grp.add(row)

    def _on_autostart_add(self, dd, paths: list, names: list) -> None:
        idx = dd.get_selected()
        if idx <= 0:  # 0 = "(select)"
            return
        i = idx - 1
        if not (0 <= i < len(paths)):
            return
        src = Path(paths[i])
        as_dir = Path.home() / ".config" / "autostart"
        as_dir.mkdir(parents=True, exist_ok=True)
        dst = as_dir / src.name
        try:
            shutil.copy2(src, dst)
            self.toast(f"{names[i]} added to startup")
            self._render_autostart()
        except Exception as e:
            self.toast(f"failed: {e}")
        dd.set_selected(0)

    def _remove_autostart(self, path: Path, display: str) -> None:
        try:
            path.unlink()
            self.toast(f"{display} removed from startup")
            self._render_autostart()
        except Exception as e:
            self.toast(f"failed: {e}")


# ──────────────────────────────────────────────────────────────────────
# STORAGE — df / lsblk / smartctl, pacman cache, journal
# ──────────────────────────────────────────────────────────────────────
class StoragePage(SectionPage):
    """Mounts + block devices + SMART + per-folder home breakdown +
    multi-target cleanup + largest-files finder. All real:
      · df / lsblk / smartctl       — read-only system data
      · du -sb on home subfolders   — usage breakdown
      · paccache, journalctl vacuum, gio trash, find/sort — cleanup
    """
    KEY = "storage"

    HOME_FOLDERS = [
        ("Documents",       "Documents",            "user files"),
        ("Downloads",       "Downloads",            "downloaded files"),
        ("Pictures",        "Pictures",             "images"),
        ("Videos",          "Videos",               "videos"),
        ("Music",           "Music",                "audio files"),
        ("Desktop",         "Desktop",              "desktop items"),
        ("App data",        ".local/share",         "user-installed app data"),
        ("Cache",           ".cache",               "browser &amp; app caches (safe to clear)"),
        ("Config",          ".config",              "settings &amp; preferences"),
        ("Trash",           ".local/share/Trash",   "files marked for deletion"),
    ]

    def build(self) -> None:
        self.mounts_grp = Adw.PreferencesGroup(
            title="Mounts",
            description="Filesystem usage from df (tmpfs/devfs hidden)")
        self.add_group(self.mounts_grp)
        self.disks_grp = Adw.PreferencesGroup(
            title="Block devices",
            description="Physical disks from lsblk")
        self.add_group(self.disks_grp)
        self.smart_grp = Adw.PreferencesGroup(
            title="SMART health",
            description="Requires smartmontools (and admin for full data)")
        self.add_group(self.smart_grp)
        self.home_grp = Adw.PreferencesGroup(
            title="Your home folder",
            description="What's using space under ~ (computed in background)")
        self.add_group(self.home_grp)
        self.clean_grp = Adw.PreferencesGroup(
            title="Cleanup",
            description="Targeted reclaims that won't affect your work")
        self.add_group(self.clean_grp)
        self.large_grp = Adw.PreferencesGroup(
            title="Largest files in your home",
            description="Computed on demand — may take a few seconds")
        self.add_group(self.large_grp)

        self._home_cache: dict = {}  # folder -> (size, mtime)
        self._render()
        self.add_pill(status_pill("live", "ok"))
        self.schedule_refresh(20000, self._tick)

    def _tick(self) -> bool:
        # Mounts/disks/SMART change rarely; refresh those + home sizes.
        self._render_mounts()
        self._refresh_home_sizes()
        return True

    def _render(self) -> None:
        self._render_mounts()
        self._render_disks_and_smart()
        self._render_home()
        self._render_cleanup()
        self._render_largest()

    # ── Mounts ───────────────────────────────────────────────
    def _render_mounts(self) -> None:
        _clear_group(self.mounts_grp)
        rc, out, _ = sh(
            ["df", "-h", "--output=target,fstype,size,used,avail,pcent",
             "-x", "tmpfs", "-x", "devtmpfs", "-x", "squashfs",
             "-x", "overlay"], timeout=4)
        lines = out.splitlines()[1:] if out else []
        if not lines:
            self.mounts_grp.add(empty_row("No mounts found", ""))
            return
        for ln in lines[:20]:
            cols = ln.split()
            if len(cols) < 6:
                continue
            target, fs, size, used, avail, pcent = cols[:6]
            try:
                pct = int(pcent.rstrip("%"))
            except ValueError:
                pct = 0
            tag = "ok" if pct < 75 else ("warn" if pct < 90 else "danger")
            row = Adw.ActionRow(
                title=target,
                subtitle=f"{fs}  ·  {used} / {size} used  ·  {avail} free")
            # Inline progress bar
            bar = Gtk.LevelBar.new_for_interval(0, 100)
            bar.set_value(pct)
            bar.add_offset_value("low",  75)
            bar.add_offset_value("high", 90)
            bar.add_offset_value("full", 100)
            bar.set_size_request(140, 8)
            bar.set_valign(Gtk.Align.CENTER)
            row.add_suffix(bar)
            row.add_suffix(status_pill(pcent, tag))
            self.mounts_grp.add(row)

    # ── Disks + SMART ────────────────────────────────────────
    def _render_disks_and_smart(self) -> None:
        _clear_group(self.disks_grp)
        _clear_group(self.smart_grp)
        rc, out, _ = sh(
            ["lsblk", "-d", "-o", "NAME,SIZE,MODEL,ROTA", "-n"],
            timeout=3)
        lines = out.splitlines() if out else []
        if not lines:
            self.disks_grp.add(empty_row("No block devices found", ""))
        disk_names = []
        for ln in lines:
            parts = ln.split(None, 3)
            if len(parts) < 2:
                continue
            name, size = parts[0], parts[1]
            model = parts[2] if len(parts) >= 3 else ""
            rota = parts[3] if len(parts) >= 4 else "?"
            kind = "HDD" if rota.strip() == "1" else "SSD"
            self.disks_grp.add(kv_row(
                f"/dev/{name}", f"{size} · {kind}",
                subtitle=model.strip() or None))
            disk_names.append(name)

        if not have("smartctl"):
            self.smart_grp.add(empty_row(
                "smartctl not installed",
                "Install smartmontools to view SMART status"))
            return
        if not disk_names:
            self.smart_grp.add(empty_row("No disks to query", ""))
            return
        for name in disk_names:
            dev = f"/dev/{name}"
            rc, out, _ = sh(["smartctl", "-H", dev], timeout=4)
            status = ""
            for line in out.splitlines():
                if "overall-health" in line.lower():
                    status = line.split(":", 1)[-1].strip()
                    break
            if not status:
                status = "needs admin (try: sudo smartctl -H /dev/X)"
                tag = "warn"
            elif "PASSED" in status.upper():
                tag = "ok"
            else:
                tag = "danger"
            row = Adw.ActionRow(title=dev, subtitle=status)
            row.add_suffix(status_pill(
                "PASS" if "PASSED" in status.upper()
                else ("?" if "admin" in status else "FAIL"),
                tag))
            self.smart_grp.add(row)

    # ── Home folder breakdown ────────────────────────────────
    def _render_home(self) -> None:
        _clear_group(self.home_grp)
        home = Path.home()
        for label, sub_path, desc in self.HOME_FOLDERS:
            p = home / sub_path
            row = Adw.ActionRow(
                title=label, subtitle=f"~/{sub_path}  ·  {desc}")
            if not p.exists():
                row.add_suffix(Gtk.Label(label="(none)"))
                self.home_grp.add(row)
                continue
            size, _ = self._home_cache.get(sub_path, (None, 0))
            val = Gtk.Label(label=self._fmt_bytes(size)
                            if size is not None else "computing…")
            val.add_css_class("nyx-kv-value")
            val.set_valign(Gtk.Align.CENTER)
            row.add_suffix(val)
            if have("xdg-open") and sub_path != ".local/share/Trash":
                btn = Gtk.Button(label="Open")
                btn.add_css_class("nyx-pill")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked",
                            lambda _b, pp=p:
                                fire_and_forget(f"xdg-open {pp}"))
                row.add_suffix(btn)
            self.home_grp.add(row)
        # Kick off background du
        self._refresh_home_sizes()

    def _refresh_home_sizes(self) -> None:
        home = Path.home()
        for _, sub_path, _ in self.HOME_FOLDERS:
            p = home / sub_path
            if not p.exists():
                continue
            sh_async(
                ["du", "-sb", str(p)],
                lambda r, sp=sub_path:
                    self._on_home_size(sp, r),
                timeout=60)

    def _on_home_size(self, sub_path: str, result) -> None:
        rc, out, _ = result
        if rc != 0 or not out.strip():
            return
        try:
            size = int(out.split()[0])
        except Exception:
            return
        self._home_cache[sub_path] = (size, 0)
        # Re-render only the home group to show new value
        self._render_home_values_only()

    def _render_home_values_only(self) -> None:
        # Cheap re-render: just the home group from cache
        _clear_group(self.home_grp)
        home = Path.home()
        for label, sub_path, desc in self.HOME_FOLDERS:
            p = home / sub_path
            row = Adw.ActionRow(
                title=label, subtitle=f"~/{sub_path}  ·  {desc}")
            if not p.exists():
                row.add_suffix(Gtk.Label(label="(none)"))
                self.home_grp.add(row)
                continue
            size, _ = self._home_cache.get(sub_path, (None, 0))
            val = Gtk.Label(label=self._fmt_bytes(size)
                            if size is not None else "computing…")
            val.add_css_class("nyx-kv-value")
            val.set_valign(Gtk.Align.CENTER)
            row.add_suffix(val)
            if have("xdg-open") and sub_path != ".local/share/Trash":
                btn = Gtk.Button(label="Open")
                btn.add_css_class("nyx-pill")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked",
                            lambda _b, pp=p:
                                fire_and_forget(f"xdg-open {pp}"))
                row.add_suffix(btn)
            self.home_grp.add(row)

    @staticmethod
    def _fmt_bytes(n) -> str:
        if n is None:
            return "—"
        n = float(n)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024:
                return f"{int(n)} {unit}" if unit == "B" else f"{n:.1f} {unit}"
            n /= 1024
        return f"{n:.1f} PB"

    # ── Cleanup ──────────────────────────────────────────────
    def _render_cleanup(self) -> None:
        _clear_group(self.clean_grp)
        # Trash empty
        trash = Path.home() / ".local/share/Trash/files"
        n_trash = 0
        if trash.exists():
            try:
                n_trash = len(list(trash.iterdir()))
            except Exception:
                pass
        self.clean_grp.add(action_row(
            "Empty trash",
            f"{n_trash} item(s) in ~/.local/share/Trash" if n_trash > 0
            else "trash is empty",
            "Empty",
            lambda: self._do_cleanup(
                ["sh", "-c",
                 "gio trash --empty 2>/dev/null || "
                 "rm -rf ~/.local/share/Trash/files/* "
                 "~/.local/share/Trash/info/* 2>/dev/null"],
                "trash emptied"),
            css="nyx-pill-warn" if n_trash else "nyx-pill"))

        # ~/.cache total
        cache = Path.home() / ".cache"
        cache_size = self._home_cache.get(".cache", (None, 0))[0]
        self.clean_grp.add(action_row(
            "Clear user cache",
            f"~/.cache  ·  "
            + (self._fmt_bytes(cache_size) if cache_size is not None
               else "size pending"),
            "Clear",
            lambda: self._do_cleanup(
                ["sh", "-c", "rm -rf ~/.cache/*"],
                "cache cleared"),
            css="nyx-pill-warn"))

        # Browser caches
        for name, paths in (
            ("Firefox", "~/.cache/mozilla/firefox/*/cache2 "
                        "~/.cache/mozilla/firefox/*/startupCache"),
            ("Chromium / Chrome",
             "~/.cache/chromium/Default/Cache "
             "~/.cache/google-chrome/Default/Cache"),
            ("Brave",
             "~/.cache/BraveSoftware/Brave-Browser/Default/Cache"),
            ("Thumbnail cache", "~/.cache/thumbnails"),
        ):
            self.clean_grp.add(action_row(
                f"Clear {name} cache",
                paths.replace(" ~/", "  ·  ~/"),
                "Clear",
                lambda p=paths, n=name: self._do_cleanup(
                    ["sh", "-c", f"rm -rf {p}"],
                    f"{n} cache cleared")))

        # paccache
        if have("paccache"):
            self.clean_grp.add(action_row(
                "Trim pacman cache (keep latest 2 versions)",
                "paccache -rk2 — frees /var/cache/pacman/pkg",
                "Trim",
                lambda: sh_async(
                    ["pkexec", "paccache", "-rk2"],
                    lambda r: (self.toast(
                        "trimmed" if r[0] == 0 else "needs admin"),
                        self._render_mounts()),
                    timeout=60),
                css="nyx-pill-warn"))
        else:
            self.clean_grp.add(empty_row(
                "paccache not installed",
                "Install pacman-contrib to enable cache trimming"))

        # journal
        self.clean_grp.add(action_row(
            "Vacuum systemd journal (keep 7 days)",
            "journalctl --vacuum-time=7d",
            "Vacuum",
            lambda: sh_async(
                ["pkexec", "journalctl", "--vacuum-time=7d"],
                lambda r: (self.toast(
                    "vacuumed" if r[0] == 0 else "needs admin"),
                    self._render_mounts()),
                timeout=60),
            css="nyx-pill-warn"))

        # Flatpak unused
        if have("flatpak"):
            self.clean_grp.add(action_row(
                "Remove unused Flatpak runtimes",
                "flatpak uninstall --unused -y",
                "Remove",
                lambda: sh_async(
                    ["flatpak", "uninstall", "--unused", "-y"],
                    lambda r: self.toast(
                        "unused removed" if r[0] == 0 else "failed"),
                    timeout=120)))

        # baobab launcher (optional)
        if have("baobab"):
            self.clean_grp.add(action_row(
                "Open disk usage analyzer",
                "GNOME baobab — visualize what's using space",
                "Open",
                lambda: fire_and_forget("baobab")))

    def _do_cleanup(self, cmd, success_msg: str) -> None:
        sh_async(cmd, lambda r: (
            self.toast(success_msg if r[0] == 0 else "failed"),
            self._render_cleanup(),
            self._refresh_home_sizes(),
        ), timeout=30)

    # ── Largest files in $HOME ───────────────────────────────
    def _render_largest(self) -> None:
        _clear_group(self.large_grp)
        self.large_grp.add(action_row(
            "Find the 20 largest files in your home",
            "uses find — typically completes in a few seconds",
            "Scan",
            lambda: self._scan_largest()))
        # Render previous results, if any
        for size, path in getattr(self, "_largest_cache", []):
            row = Adw.ActionRow(
                title=Path(path).name,
                subtitle=str(path).replace(str(Path.home()), "~"))
            val = Gtk.Label(label=self._fmt_bytes(size))
            val.add_css_class("nyx-kv-value")
            row.add_suffix(val)
            if have("xdg-open"):
                btn = Gtk.Button(label="Open folder")
                btn.add_css_class("nyx-pill")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked",
                            lambda _b, p=path:
                                fire_and_forget(
                                    f"xdg-open {Path(p).parent}"))
                row.add_suffix(btn)
            self.large_grp.add(row)

    def _scan_largest(self) -> None:
        self.toast("scanning…")
        sh_async(
            ["sh", "-c",
             "find ~ -xdev -type f -not -path '*/.cache/*' "
             "-not -path '*/node_modules/*' "
             "-not -path '*/.local/share/Trash/*' "
             "-printf '%s\\t%p\\n' 2>/dev/null | sort -rn | head -20"],
            self._on_largest_done, timeout=90)

    def _on_largest_done(self, result) -> None:
        rc, out, _ = result
        if rc != 0:
            self.toast("scan failed")
            return
        items = []
        for line in out.splitlines():
            try:
                size_s, path = line.split("\t", 1)
                items.append((int(size_s), path))
            except Exception:
                continue
        self._largest_cache = items
        self._render_largest()
        self.toast(f"found {len(items)} files")


# ──────────────────────────────────────────────────────────────────────
# UPDATES — checkupdates, AUR helpers
# ──────────────────────────────────────────────────────────────────────
class UpdatesPage(SectionPage):
    """Repo + AUR pending updates, reboot status, mirror refresh,
    auto-check timer, channel selector, last-upgrade timestamp.
    All real:
      · checkupdates / paru -Qua / yay -Qua  — pending lists
      · /var/log/pacman.log                  — last-upgrade time
      · pkexec reflector                     — mirror refresh
      · ~/.config/systemd/user/nyxus-update-check.{service,timer} — auto
      · pkexec sed on /etc/pacman.conf       — channel toggle
    """
    KEY = "updates"

    REFLECTOR_COUNTRIES = ["United States", "United Kingdom", "Germany",
                           "France", "Netherlands", "Canada", "Japan",
                           "Australia", "Singapore", "Brazil"]
    AUTOCHECK_INTERVALS = [
        ("Off",       0),
        ("Hourly",    3600),
        ("Every 6h",  21600),
        ("Daily",     86400),
        ("Weekly",    604800),
    ]

    def build(self) -> None:
        self.repo_grp = Adw.PreferencesGroup(
            title="Official repositories",
            description="Pending updates from pacman (via checkupdates — "
                        "no root required)")
        self.add_group(self.repo_grp)
        self.aur_grp = Adw.PreferencesGroup(
            title="AUR / foreign packages",
            description="Pending updates for AUR packages")
        self.add_group(self.aur_grp)
        self.rb_grp = Adw.PreferencesGroup(title="Reboot status")
        self.add_group(self.rb_grp)
        self.history_grp = Adw.PreferencesGroup(
            title="Update history",
            description="From /var/log/pacman.log")
        self.add_group(self.history_grp)
        self.auto_grp = Adw.PreferencesGroup(
            title="Auto-check schedule",
            description="Background check via systemd --user timer")
        self.add_group(self.auto_grp)
        self.mirror_grp = Adw.PreferencesGroup(
            title="Mirrors",
            description="Refresh /etc/pacman.d/mirrorlist via reflector "
                        "(admin prompt)")
        self.add_group(self.mirror_grp)
        self.channel_grp = Adw.PreferencesGroup(
            title="Update channel",
            description="Stable (default) or include [testing] / "
                        "[community-testing] (faster updates, more risk)")
        self.add_group(self.channel_grp)
        tools = Adw.PreferencesGroup(title="Tools")
        self.add_group(tools)
        tools.add(action_row(
            "Open NYXUS Updater",
            "Graphical update center (repos + AUR + flatpak), "
            "keybind Super + Ctrl + U",
            "Open",
            lambda: fire_and_forget("nyxus-updater"),
            css="nyx-pill-ok"))
        tools.add(action_row(
            "Run full system upgrade",
            "Opens a terminal with sudo pacman -Syu",
            "Run",
            lambda: open_terminal("sudo pacman -Syu", self.win)))
        for helper in ("paru", "yay"):
            if have(helper):
                tools.add(action_row(
                    f"AUR upgrade ({helper})",
                    f"{helper} -Syu — includes AUR & repos",
                    "Run",
                    lambda h=helper:
                        open_terminal(f"{h} -Syu", self.win)))

        self._render()
        self.add_pill(status_pill("live", "ok"))
        self.schedule_refresh(60000, self._tick)

    def _tick(self) -> bool:
        self._render_repo()
        self._render_aur()
        self._render_history()
        return True

    def _render(self) -> None:
        self._render_repo()
        self._render_aur()
        self._render_reboot()
        self._render_history()
        self._render_autocheck()
        self._render_mirrors()
        self._render_channel()

    # ── Repo + AUR ───────────────────────────────────────────
    def _render_repo(self) -> None:
        _clear_group(self.repo_grp)
        if not have("checkupdates"):
            self.repo_grp.add(empty_row(
                "checkupdates not installed",
                "Install pacman-contrib to query pending updates without "
                "needing root"))
            return
        self.repo_grp.add(kv_row("Status", "checking…"))
        sh_async(["checkupdates"], self._on_repo, timeout=30)

    def _on_repo(self, result) -> None:
        rc, out, _ = result
        _clear_group(self.repo_grp)
        if rc == 2:
            self.repo_grp.add(kv_row("Status", "up to date ✓"))
            return
        lines = [l for l in out.splitlines() if l.strip()]
        n = len(lines)
        self.repo_grp.add(kv_row(
            "Pending", str(n),
            "click 'Run full system upgrade' below to apply"))
        for line in lines[:25]:
            parts = line.split()
            if len(parts) >= 4:
                self.repo_grp.add(kv_row(
                    parts[0], f"{parts[1]} → {parts[3]}"))
        if n > 25:
            self.repo_grp.add(kv_row(
                "+ more", f"{n - 25} additional packages"))
        # Persist last-checked timestamp
        try:
            (Path.home() / ".config/nyxus").mkdir(parents=True, exist_ok=True)
            (Path.home() / ".config/nyxus/last_update_check").write_text(
                datetime.now().isoformat())
        except Exception:
            pass

    def _render_aur(self) -> None:
        _clear_group(self.aur_grp)
        helper = "paru" if have("paru") else ("yay" if have("yay") else "")
        if not helper:
            self.aur_grp.add(empty_row(
                "No AUR helper installed",
                "Install paru or yay to track AUR updates"))
            return
        self.aur_grp.add(kv_row("Status", "checking…"))
        sh_async([helper, "-Qua"], self._on_aur, timeout=60)

    def _on_aur(self, result) -> None:
        rc, out, _ = result
        _clear_group(self.aur_grp)
        lines = [l for l in out.splitlines() if l.strip()]
        if not lines:
            self.aur_grp.add(kv_row("Status", "up to date ✓"))
            return
        self.aur_grp.add(kv_row("Pending", str(len(lines))))
        for line in lines[:25]:
            parts = line.split()
            if len(parts) >= 4:
                self.aur_grp.add(kv_row(
                    parts[0], f"{parts[1]} → {parts[3]}"))

    # ── Reboot status ────────────────────────────────────────
    def _render_reboot(self) -> None:
        _clear_group(self.rb_grp)
        running_kernel = sh(["uname", "-r"], timeout=2)[1].strip()
        rc, ik, _ = sh(["pacman", "-Q", "linux"], timeout=2)
        installed_kernel = ik.strip().split(" ")[-1] if ik else "?"
        kernel_match = installed_kernel.split("-")[0] in running_kernel
        self.rb_grp.add(kv_row("Running kernel", running_kernel))
        self.rb_grp.add(kv_row("Installed kernel", installed_kernel))

        # Check critical packages: systemd, glibc — mtime > boot time?
        rc, btime, _ = sh(
            ["sh", "-c", "stat -c %Y /proc/1"], timeout=2)
        try:
            boot_ts = int(btime.strip())
        except Exception:
            boot_ts = 0
        critical_changed = []
        for pkg in ("systemd", "glibc", "linux", "linux-zen", "linux-lts"):
            rc, mt, _ = sh(
                ["sh", "-c",
                 f"stat -c %Y /var/lib/pacman/local/{pkg}-* 2>/dev/null "
                 "| sort -n | tail -1"], timeout=2)
            try:
                ts = int(mt.strip())
                if ts > boot_ts:
                    critical_changed.append(pkg)
            except Exception:
                continue

        needs_reboot = (not kernel_match) or bool(critical_changed)
        if needs_reboot:
            why = []
            if not kernel_match:
                why.append("kernel differs from running")
            if critical_changed:
                why.append("upgraded since boot: "
                          + ", ".join(critical_changed))
            row = Adw.ActionRow(
                title="⚠ Reboot recommended",
                subtitle=" · ".join(why))
            btn = Gtk.Button(label="Reboot now")
            btn.add_css_class("nyx-pill-warn")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", lambda _b: self._confirm_reboot())
            row.add_suffix(btn)
            self.rb_grp.add(row)
        else:
            self.rb_grp.add(kv_row(
                "Status", "running kernel matches installed ✓"))

    def _confirm_reboot(self) -> None:
        dlg = Adw.MessageDialog(
            transient_for=self.win,
            heading="Reboot now?",
            body="All unsaved work will be lost. Continue?")
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("ok", "Reboot")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.connect("response", lambda d, resp:
                    sh_async(["systemctl", "reboot"], None, timeout=4)
                    if resp == "ok" else None)
        dlg.present()

    # ── History ──────────────────────────────────────────────
    def _render_history(self) -> None:
        _clear_group(self.history_grp)
        log_p = Path("/var/log/pacman.log")
        if not log_p.exists():
            self.history_grp.add(empty_row(
                "No pacman log found",
                "/var/log/pacman.log is missing"))
            return
        # Last upgrade timestamp
        rc, out, _ = sh(
            ["sh", "-c",
             "grep -E 'starting full system upgrade' "
             "/var/log/pacman.log | tail -1"], timeout=4)
        last_full = out.strip()
        m = re.match(r"^\[([^\]]+)\]", last_full)
        if m:
            self.history_grp.add(kv_row(
                "Last full upgrade", m.group(1)))
        else:
            self.history_grp.add(kv_row(
                "Last full upgrade", "(no record)"))

        # Last 5 upgrades
        rc, out, _ = sh(
            ["sh", "-c",
             "grep -E '\\[ALPM\\] upgraded' /var/log/pacman.log "
             "| tail -5"], timeout=4)
        for line in out.splitlines():
            mm = re.match(
                r"^\[([^\]]+)\].*upgraded\s+(\S+)\s+\(([^)]+)\)", line)
            if mm:
                self.history_grp.add(kv_row(
                    mm.group(2), mm.group(3),
                    subtitle=mm.group(1)))

        # Last-checked
        check_p = Path.home() / ".config/nyxus/last_update_check"
        if check_p.exists():
            try:
                self.history_grp.add(kv_row(
                    "Last checked (NYXUS)",
                    check_p.read_text().strip()[:19]))
            except Exception:
                pass

    # ── Auto-check timer ─────────────────────────────────────
    def _render_autocheck(self) -> None:
        _clear_group(self.auto_grp)
        prefs = load_prefs().get("updates", {})
        cur = int(prefs.get("autocheck_secs", 0))
        labels = [n for n, _ in self.AUTOCHECK_INTERVALS]
        secs   = [s for _, s in self.AUTOCHECK_INTERVALS]
        try:
            sel = secs.index(cur)
        except ValueError:
            sel = 0
        row = Adw.ActionRow(
            title="Check for updates automatically",
            subtitle="runs `checkupdates` and writes the count to "
                     "~/.config/nyxus/pending_count")
        dd = Gtk.DropDown.new_from_strings(labels)
        dd.set_selected(sel)
        dd.set_valign(Gtk.Align.CENTER)
        dd.connect("notify::selected",
                   lambda d, _p, ss=secs: self._on_autocheck_changed(d, ss))
        row.add_suffix(dd)
        self.auto_grp.add(row)

    def _on_autocheck_changed(self, dd, secs_list: list) -> None:
        idx = dd.get_selected()
        if not (0 <= idx < len(secs_list)):
            return
        secs = secs_list[idx]
        prefs = load_prefs()
        prefs.setdefault("updates", {})["autocheck_secs"] = secs
        save_prefs(prefs)
        self._sync_autocheck_unit(secs)
        self.toast("auto-check " + ("off" if secs == 0
                   else f"every {secs}s"))

    def _sync_autocheck_unit(self, secs: int) -> None:
        unit_dir = Path.home() / ".config/systemd/user"
        unit_dir.mkdir(parents=True, exist_ok=True)
        svc = unit_dir / "nyxus-update-check.service"
        tmr = unit_dir / "nyxus-update-check.timer"
        if secs <= 0:
            sh_async(
                ["systemctl", "--user", "disable", "--now",
                 "nyxus-update-check.timer"],
                None, timeout=4)
            for p in (svc, tmr):
                try:
                    p.unlink()
                except FileNotFoundError:
                    pass
            return
        svc.write_text(textwrap.dedent("""\
            [Unit]
            Description=NYXUS pending-updates check

            [Service]
            Type=oneshot
            ExecStart=/bin/sh -c 'mkdir -p ~/.config/nyxus && checkupdates 2>/dev/null | wc -l > ~/.config/nyxus/pending_count; date -Iseconds > ~/.config/nyxus/last_update_check'
            """))
        tmr.write_text(textwrap.dedent(f"""\
            [Unit]
            Description=NYXUS pending-updates check (every {secs}s)

            [Timer]
            OnBootSec=2min
            OnUnitActiveSec={secs}s
            Persistent=true

            [Install]
            WantedBy=timers.target
            """))
        sh_async(
            ["systemctl", "--user", "daemon-reload"],
            lambda _r: sh_async(
                ["systemctl", "--user", "enable", "--now",
                 "nyxus-update-check.timer"],
                None, timeout=4),
            timeout=4)

    # ── Mirrors ──────────────────────────────────────────────
    def _render_mirrors(self) -> None:
        _clear_group(self.mirror_grp)
        if not have("reflector"):
            self.mirror_grp.add(empty_row(
                "reflector not installed",
                "Install reflector to refresh mirrors"))
            return
        prefs = load_prefs().get("updates", {})
        country = prefs.get("mirror_country", "United States")
        row = Adw.ActionRow(
            title="Mirror country",
            subtitle="reflector picks the fastest N mirrors in this country")
        dd = Gtk.DropDown.new_from_strings(self.REFLECTOR_COUNTRIES)
        try:
            dd.set_selected(self.REFLECTOR_COUNTRIES.index(country))
        except ValueError:
            dd.set_selected(0)
        dd.set_valign(Gtk.Align.CENTER)
        dd.connect("notify::selected",
                   lambda d, _p: self._on_country_changed(d))
        row.add_suffix(dd)
        self.mirror_grp.add(row)

        self.mirror_grp.add(action_row(
            "Refresh mirror list now",
            f"reflector --country '{country}' --age 6 --sort rate "
            "--save /etc/pacman.d/mirrorlist",
            "Refresh",
            lambda c=country: sh_async(
                ["pkexec", "sh", "-c",
                 f"reflector --country '{c}' --age 6 --sort rate "
                 f"--save /etc/pacman.d/mirrorlist && pacman -Syy"],
                lambda r: self.toast(
                    "mirrors refreshed" if r[0] == 0 else "needs admin"),
                timeout=120),
            css="nyx-pill"))

    def _on_country_changed(self, dd) -> None:
        idx = dd.get_selected()
        if not (0 <= idx < len(self.REFLECTOR_COUNTRIES)):
            return
        country = self.REFLECTOR_COUNTRIES[idx]
        prefs = load_prefs()
        prefs.setdefault("updates", {})["mirror_country"] = country
        save_prefs(prefs)
        self.toast(f"mirror country → {country}")
        self._render_mirrors()

    # ── Channel selector (stable / testing) ──────────────────
    def _render_channel(self) -> None:
        _clear_group(self.channel_grp)
        try:
            txt = Path("/etc/pacman.conf").read_text(errors="ignore")
        except Exception:
            self.channel_grp.add(empty_row(
                "/etc/pacman.conf not readable", ""))
            return
        # Parse: a [testing] section with uncommented Include = ... = enabled
        testing_on = re.search(
            r"^\s*\[testing\]\s*\n([^\[]*?)Include\s*=",
            txt, re.MULTILINE) is not None
        comm_testing_on = re.search(
            r"^\s*\[community-testing\]\s*\n([^\[]*?)Include\s*=",
            txt, re.MULTILINE) is not None

        for label, section, current in (
            ("[testing]",           "testing",           testing_on),
            ("[community-testing]", "community-testing", comm_testing_on),
        ):
            row = Adw.ActionRow(
                title=label,
                subtitle="WARNING: enabling brings unstable packages — "
                         "may break your system")
            sw = Gtk.Switch()
            sw.set_valign(Gtk.Align.CENTER)
            sw.set_active(current)
            sw.connect("notify::active",
                       lambda s, _p, sec=section:
                           self._on_channel_toggled(s, sec))
            row.add_suffix(sw)
            self.channel_grp.add(row)

    def _on_channel_toggled(self, sw, section: str) -> None:
        on = sw.get_active()
        # Idempotent: enable = uncomment [section] + Include line
        # disable = comment them out
        if on:
            # Enable: uncomment if commented, else append a fresh block
            cmd = f"""set -e
if grep -qE '^\\s*#\\s*\\[{section}\\]' /etc/pacman.conf; then
  sed -i -E '/^#\\s*\\[{section}\\]/,/^#\\s*Include/ s/^#//' /etc/pacman.conf
elif ! grep -qE '^\\s*\\[{section}\\]' /etc/pacman.conf; then
  printf '\\n[{section}]\\nInclude = /etc/pacman.d/mirrorlist\\n' >> /etc/pacman.conf
fi
pacman -Syy
"""
        else:
            cmd = (
                f"sed -i -E '/^\\[{section}\\]/,/^Include/ "
                f"s/^([^#].*)/#\\1/' /etc/pacman.conf && pacman -Syy")
        sh_async(
            ["pkexec", "sh", "-c", cmd],
            lambda r: (self.toast(
                f"{section} " + ("enabled" if on else "disabled")
                if r[0] == 0 else "needs admin / failed"),
                self._render_channel()),
            timeout=60)


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

        # Pointers to assistive tools — launch on demand
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

        # Persistent autostart — the macOS / Windows pattern is "ON in
        # accessibility = ON every login". We wire this through the
        # standard XDG autostart mechanism (~/.config/autostart/*.desktop)
        # so it survives reboot AND reflects the system state on every
        # page open. NYXUS does not start an a11y daemon by default;
        # the user explicitly opts in here.
        autos = Adw.PreferencesGroup(
            title="Sign-in autostart",
            description="Start these helpers automatically on every login")
        self.add_group(autos)
        self._autostart_dir = Path.home() / ".config" / "autostart"
        for label, bin_, fname in (
            ("Auto-start screen reader (Orca)",    "orca",   "orca.desktop"),
            ("Auto-start on-screen keyboard",      "wvkbd",  "wvkbd.desktop"),
            ("Auto-start screen magnifier",        "magnus", "magnus.desktop"),
        ):
            if not have(bin_):
                autos.add(empty_row(label, f"{bin_} not installed"))
                continue
            sw_row = Adw.SwitchRow(title=label,
                                   subtitle=f"~/.config/autostart/{fname}")
            sw_row.set_active(self._autostart_present(fname))
            sw_row.connect(
                "notify::active",
                lambda s, _p, b=bin_, f=fname, lbl=label:
                    self._toggle_autostart(s, b, f, lbl))
            autos.add(sw_row)

        self.add_pill(status_pill("a11y", "ok"))

    def _autostart_present(self, fname: str) -> bool:
        try:
            return (self._autostart_dir / fname).exists()
        except Exception:
            return False

    def _toggle_autostart(self, sw, exe: str, fname: str, label: str) -> None:
        """Write or remove an XDG autostart .desktop file. Always-on
        path — no helper required (lives in the user's own home)."""
        try:
            path = self._autostart_dir / fname
            if sw.get_active():
                self._autostart_dir.mkdir(parents=True, exist_ok=True)
                path.write_text(
                    f"[Desktop Entry]\nType=Application\nName={label}\n"
                    f"Exec={exe}\nX-GNOME-Autostart-enabled=true\n"
                    f"NoDisplay=false\nTerminal=false\n",
                    encoding="utf-8")
                self.toast(f"{label}: auto-start ON")
            else:
                if path.exists():
                    path.unlink()
                self.toast(f"{label}: auto-start OFF")
        except Exception as e:
            log.warning("autostart toggle failed: %s", e)
            self.toast(f"failed: {e}")


# ──────────────────────────────────────────────────────────────────────
# PARENTAL CONTROLS — bedtime nudge + web hostname blocklist.
#
# Hard contract (matches user prefs in replit.md):
#   · NEVER touches faillock/pam_tally/pam_faillock — bedtime is a
#     loginctl lock, not a lockout. The user can re-enter their
#     password at any time.
#   · OFF by default. The toggle row makes the helper write its first
#     hosts/timer entry. With no entries, the helper is a no-op.
#   · Every privileged action goes through nyxus-parental-helper via
#     pkexec; this Python file never edits /etc/hosts or
#     /etc/systemd/system itself.
# ──────────────────────────────────────────────────────────────────────
class ParentalControlsPage(SectionPage):
    KEY = "parental"
    HELPER = "/usr/local/libexec/nyxus-parental-helper"

    def build(self) -> None:
        warn = Adw.PreferencesGroup(
            title="Parental Controls",
            description="Bedtime nudge + web hostname blocklist. "
                        "These are NUDGES — never account lockouts. "
                        "The user can always unlock with their password.")
        self.add_group(warn)
        warn.add(kv_row("Helper",
                        "installed" if Path(self.HELPER).exists()
                        else "not installed — see nyxus-parental-helper"))

        # ── Web blocklist ─────────────────────────────────────────────
        web = Adw.PreferencesGroup(
            title="Web blocklist",
            description="Resolves the host to 0.0.0.0 system-wide via "
                        "/etc/hosts. Browsers, apps, everything.")
        self.add_group(web)

        self._blocklist_group = web
        self._refresh_blocklist()

        add_row = Adw.ActionRow(title="Block a hostname",
                                subtitle="example: ads.example.com")
        self._block_entry = Gtk.Entry()
        self._block_entry.set_placeholder_text("hostname")
        self._block_entry.set_size_request(220, -1)
        add_row.add_suffix(self._block_entry)
        add_btn = Gtk.Button(label="Block")
        add_btn.add_css_class("suggested-action")
        add_btn.connect("clicked", lambda *_: self._add_block())
        add_row.add_suffix(add_btn)
        web.add(add_row)

        # ── Bedtime ───────────────────────────────────────────────────
        bed = Adw.PreferencesGroup(
            title="Bedtime",
            description="At the start time, the session locks. The user "
                        "can unlock with their password whenever.")
        self.add_group(bed)

        bed_row = Adw.ActionRow(
            title=f"Set bedtime for current user ({Path('~').expanduser().name})",
            subtitle="HH:MM start, HH:MM end (uses systemd timer)")
        self._bed_user = Gtk.Entry()
        self._bed_user.set_text(Path('~').expanduser().name)
        self._bed_user.set_size_request(120, -1)
        self._bed_user.set_placeholder_text("user")
        bed_row.add_suffix(self._bed_user)
        self._bed_start = Gtk.Entry()
        self._bed_start.set_size_request(80, -1)
        self._bed_start.set_placeholder_text("22:00")
        bed_row.add_suffix(self._bed_start)
        self._bed_end = Gtk.Entry()
        self._bed_end.set_size_request(80, -1)
        self._bed_end.set_placeholder_text("06:00")
        bed_row.add_suffix(self._bed_end)
        set_btn = Gtk.Button(label="Set")
        set_btn.add_css_class("suggested-action")
        set_btn.connect("clicked", lambda *_: self._set_bedtime())
        bed_row.add_suffix(set_btn)
        bed.add(bed_row)

        clear_row = Adw.ActionRow(
            title="Clear bedtime",
            subtitle="Disables the bedtime timer for this user")
        clear_btn = Gtk.Button(label="Clear")
        clear_btn.add_css_class("destructive-action")
        clear_btn.connect("clicked", lambda *_: self._clear_bedtime())
        clear_row.add_suffix(clear_btn)
        bed.add(clear_row)

        self.add_pill(status_pill("parental", "ok"))

    # Read directly from the public, world-readable blocklist file.
    # The helper writes it with mode 0644 so a plain read needs no
    # pkexec — that would gratuitously prompt for a password just to
    # display the page. ALL mutating actions still go through pkexec.
    BLOCKLIST_FILE = Path("/etc/hosts.d/nyxus-parental")

    def _refresh_blocklist(self) -> None:
        for r in getattr(self, "_dyn_block_rows", []):
            try: self._blocklist_group.remove(r)
            except Exception: pass
        self._dyn_block_rows = []

        hosts: list[str] = []
        try:
            if self.BLOCKLIST_FILE.exists():
                for ln in self.BLOCKLIST_FILE.read_text().splitlines():
                    ln = ln.strip()
                    if not ln or ln.startswith("#"): continue
                    parts = ln.split()
                    if len(parts) >= 2:
                        hosts.append(parts[1])
        except Exception as e:
            log.warning("blocklist read failed: %s", e)
        if not hosts:
            row = empty_row("No hosts blocked yet",
                            "Use the box below to add one")
            self._blocklist_group.add(row)
            self._dyn_block_rows.append(row)
            return
        for h in hosts:
            row = Adw.ActionRow(title=h, subtitle="0.0.0.0 → /etc/hosts")
            btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
            btn.add_css_class("flat")
            btn.connect("clicked",
                        lambda _b, hh=h: self._remove_block(hh))
            row.add_suffix(btn)
            self._blocklist_group.add(row)
            self._dyn_block_rows.append(row)

    def _add_block(self) -> None:
        h = (self._block_entry.get_text() or "").strip()
        if not h:
            self.toast("Enter a hostname first"); return
        sh_async(["pkexec", self.HELPER, "add-host-block", h],
                 lambda r: (self._block_entry.set_text(""),
                            self._refresh_blocklist(),
                            self.toast(
                                "blocked" if r[0] == 0
                                else f"failed: {r[2][:80]}")),
                 timeout=10)

    def _remove_block(self, h: str) -> None:
        sh_async(["pkexec", self.HELPER, "remove-host-block", h],
                 lambda r: (self._refresh_blocklist(),
                            self.toast(
                                "unblocked" if r[0] == 0
                                else f"failed: {r[2][:80]}")),
                 timeout=10)

    def _set_bedtime(self) -> None:
        u = (self._bed_user.get_text() or "").strip()
        s = (self._bed_start.get_text() or "").strip()
        e = (self._bed_end.get_text() or "").strip()
        if not (u and s and e):
            self.toast("Fill user, start, and end (HH:MM)"); return
        sh_async(["pkexec", self.HELPER, "set-bedtime", u, s, e],
                 lambda r: self.toast(
                     f"bedtime set for {u}: {s}–{e}" if r[0] == 0
                     else f"failed: {r[2][:80]}"),
                 timeout=10)

    def _clear_bedtime(self) -> None:
        u = (self._bed_user.get_text() or "").strip()
        if not u:
            self.toast("Enter the user to clear"); return
        sh_async(["pkexec", self.HELPER, "clear-bedtime", u],
                 lambda r: self.toast(
                     f"bedtime cleared for {u}" if r[0] == 0
                     else f"failed: {r[2][:80]}"),
                 timeout=10)


# ──────────────────────────────────────────────────────────────────────
# APP PERMISSIONS — per-Flatpak sandbox overrides.
#
# Real reads/writes via `flatpak override --show <app>` and
# `flatpak override --user <app> --(no-)talk-name=…` etc. Lists every
# installed Flatpak app, exposes the four most-asked toggles
# (camera, microphone, network, full filesystem). For deeper control
# the user can launch `flatseal` from the same page.
# ──────────────────────────────────────────────────────────────────────
class AppPermissionsPage(SectionPage):
    KEY = "app_perms"

    # Permission table — the four most-asked Flatpak sandbox toggles.
    # Each entry maps the user-facing label to:
    #   · ini_key + ini_val  — the canonical INI form printed by
    #     `flatpak override --user --show` (e.g. `filesystems=!host`).
    #   · cli_grant          — flag to RESTORE access (positive).
    #   · cli_revoke         — flag to REVOKE access (the `--no…`
    #     form). Using these explicit canonical flags is far more
    #     robust than the previous string-substitution hack.
    PERMS = (
        # label,        subtitle,                  ini_key,      ini_val,     cli_grant,                 cli_revoke
        ("Camera",      "Webcam (v4l2)",           "devices",    "all",       "--device=all",            "--nodevice=all"),
        ("Microphone",  "Audio capture",           "sockets",    "pulseaudio", "--socket=pulseaudio",     "--nosocket=pulseaudio"),
        ("Network",     "Outbound network",        "shared",     "network",   "--share=network",         "--unshare=network"),
        ("Full filesystem", "Read/write /home AND /", "filesystems", "host",   "--filesystem=host",       "--nofilesystem=host"),
    )

    def build(self) -> None:
        if not have("flatpak"):
            self.add_group(empty_group(
                "flatpak not installed",
                "Install flatpak to manage app permissions"))
            self.add_pill(status_pill("flatpak", "warn"))
            return

        head = Adw.PreferencesGroup(
            title="Sandboxed apps",
            description="Per-app permissions for installed Flatpaks. "
                        "Toggles below write to the user override store "
                        "(~/.local/share/flatpak/overrides/<app>).")
        self.add_group(head)
        rc, out, _ = sh(["flatpak", "list", "--app",
                         "--columns=application,name"], timeout=5)
        apps: list[tuple[str, str]] = []
        for ln in (out or "").splitlines():
            ln = ln.strip()
            if not ln: continue
            parts = ln.split("\t")
            if len(parts) >= 2:
                apps.append((parts[0].strip(), parts[1].strip()))
            else:
                apps.append((parts[0], parts[0]))
        if not apps:
            self.add_group(empty_group(
                "No Flatpak apps installed",
                "Install some from the Software Store first"))
            self.add_pill(status_pill("flatpak", "ok"))
            return

        # Quick-launch row for the gold-standard GUI (Flatseal). Open
        # via xdg-open so we don't care which command name distros use.
        if have("flatseal") or have("com.github.tchx84.Flatseal"):
            head.add(action_row(
                "Open Flatseal",
                "Full GUI for every Flatpak permission",
                "Launch",
                lambda: fire_and_forget(
                    "flatseal" if have("flatseal")
                    else "com.github.tchx84.Flatseal")))
        else:
            head.add(empty_row(
                "Install Flatseal for advanced permissions",
                "flatpak install flathub com.github.tchx84.Flatseal"))

        for app_id, app_name in apps[:30]:  # cap to keep page snappy
            grp = Adw.PreferencesGroup(title=app_name,
                                       description=app_id)
            self.add_group(grp)
            rc2, ov, _ = sh(
                ["flatpak", "override", "--user", "--show", app_id],
                timeout=3)
            ov_text = ov or ""
            for label, sub, ini_key, ini_val, grant, revoke in self.PERMS:
                negated = self._is_perm_blocked(ov_text, ini_key, ini_val)
                sw = Adw.SwitchRow(title=label, subtitle=sub)
                # Programmatic-set guard: when the rollback path flips
                # the switch back to its real value after a failed
                # `flatpak override`, we MUST NOT re-fire the toggle
                # handler — otherwise we infinite-loop the failing
                # command. Plain attribute on the widget; checked at
                # the top of _toggle_perm.
                sw._nyxus_suppress = False
                sw.set_active(not negated)
                sw.connect(
                    "notify::active",
                    lambda s, _p, a=app_id, g=grant, rv=revoke, lbl=label:
                        self._toggle_perm(s, a, g, rv, lbl))
                grp.add(sw)

        self.add_pill(status_pill("flatpak", "ok"))

    def _is_perm_blocked(self, ov_text: str, ini_key: str,
                         ini_val: str) -> bool:
        """Detect a revocation in the INI text printed by
        `flatpak override --user --show`. Lines look like:
            shared=network;
            sockets=!pulseaudio;wayland;
        We split each `key=…` line on `;`, strip, and check for the
        canonical negated form `!ini_val`."""
        for ln in ov_text.splitlines():
            ln = ln.strip()
            if "=" not in ln or not ln.startswith(ini_key + "="):
                continue
            vals = [v.strip() for v in ln.split("=", 1)[1].split(";")]
            if f"!{ini_val}" in vals:
                return True
        return False

    def _toggle_perm(self, sw, app_id: str, grant: str,
                     revoke: str, label: str) -> None:
        """Apply a single override. Fail-loud: the toast reflects the
        REAL exit code from flatpak, not just the user's intent."""
        # Re-entrancy guard. The rollback path below flips the switch
        # programmatically; we must skip the resulting notify::active
        # so we don't loop the failing command forever. Lambdas can't
        # be unblocked via handler_block_by_func, so we use a flag.
        if getattr(sw, "_nyxus_suppress", False):
            return
        active = sw.get_active()
        flag = grant if active else revoke
        cmd = ["flatpak", "override", "--user", flag, app_id]

        def done(result: tuple) -> None:
            rc, _out, err = result
            if rc == 0:
                self.toast(f"{label}: {'ON' if active else 'OFF'}")
            else:
                msg = (err or "flatpak override failed")[:140]
                log.warning("flatpak override failed for %s: %s",
                            app_id, msg)
                # Revert the switch to match reality without re-firing
                # the handler.
                sw._nyxus_suppress = True
                try:
                    sw.set_active(not active)
                finally:
                    sw._nyxus_suppress = False
                self.toast(f"{label}: failed — {msg}")
        sh_async(cmd, done, timeout=8)

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
    """Local account management. All real:
      · pkexec useradd / userdel / passwd / chfn / gpasswd
      · ~/.face                — avatar (symlink for accountsservice)
      · /var/lib/AccountsService/users/<u>  — Icon= line
      · loginctl list-sessions  — active sessions
    """
    KEY = "users"

    def build(self) -> None:
        self.cur_grp = Adw.PreferencesGroup(title="Current account")
        self.add_group(self.cur_grp)
        self.others_grp = Adw.PreferencesGroup(
            title="Other accounts",
            description="Local accounts with UID ≥ 1000")
        self.add_group(self.others_grp)
        self.add_grp = Adw.PreferencesGroup(
            title="Add a new account",
            description="Creates the home directory, sets the password, "
                        "optionally grants sudo via the wheel group")
        self.add_group(self.add_grp)
        self.sudoers_grp = Adw.PreferencesGroup(
            title="Sudo rules",
            description="Members of the wheel group can run sudo")
        self.add_group(self.sudoers_grp)
        self.sessions_grp = Adw.PreferencesGroup(title="Active sessions")
        self.add_group(self.sessions_grp)

        self._render()
        self.schedule_refresh(15000, self._tick)

    def _tick(self) -> bool:
        self._render_sessions()
        return True

    def _render(self) -> None:
        self._render_current()
        self._render_others()
        self._render_add()
        self._render_sudoers()
        self._render_sessions()
        self.clear_pills()
        rc, user, _ = sh(["whoami"], timeout=2)
        self.add_pill(status_pill(user.strip(), "ok"))

    # ── Helpers ──────────────────────────────────────────────
    @staticmethod
    def _whoami() -> str:
        rc, u, _ = sh(["whoami"], timeout=2)
        return u.strip()

    @staticmethod
    def _passwd_entry(user: str) -> dict:
        rc, fn, _ = sh(["getent", "passwd", user], timeout=2)
        if rc != 0 or not fn.strip():
            return {}
        p = fn.strip().split(":")
        if len(p) < 7:
            return {}
        return {"name": p[0], "uid": p[2], "gid": p[3],
                "gecos": p[4], "home": p[5], "shell": p[6]}

    @staticmethod
    def _user_groups(user: str) -> list:
        rc, out, _ = sh(["id", "-Gn", user], timeout=2)
        return out.strip().split() if rc == 0 else []

    @staticmethod
    def _list_real_users() -> list:
        rc, out, _ = sh(["getent", "passwd"], timeout=3)
        users = []
        for line in out.splitlines():
            p = line.split(":")
            if len(p) < 7:
                continue
            try:
                uid = int(p[2])
            except ValueError:
                continue
            if uid >= 1000 and p[0] != "nobody":
                users.append((p[0], p[2], p[4] or "", p[6]))
        return sorted(users)

    # ── Current account ──────────────────────────────────────
    def _render_current(self) -> None:
        _clear_group(self.cur_grp)
        user = self._whoami()
        info = self._passwd_entry(user)
        groups = self._user_groups(user)
        is_admin = "wheel" in groups

        self.cur_grp.add(kv_row("Username", user))
        if info:
            self.cur_grp.add(kv_row("UID", info["uid"]))
            self.cur_grp.add(kv_row("Home", info["home"]))
            self.cur_grp.add(kv_row("Shell", info["shell"]))
        self.cur_grp.add(kv_row(
            "Account type", "Administrator" if is_admin else "Standard",
            "wheel group" if is_admin else "no sudo access"))
        self.cur_grp.add(kv_row(
            "Groups", " ".join(groups) if groups else "(none)"))

        # Full name (GECOS) editor — pkexec chfn
        gecos_row = Adw.ActionRow(
            title="Display name",
            subtitle="shown in greeters, file managers, etc.")
        entry = Gtk.Entry()
        entry.set_text(info.get("gecos", "").split(",")[0])
        entry.set_size_request(220, -1)
        entry.set_valign(Gtk.Align.CENTER)
        entry.connect("activate", lambda e, u=user:
                      self._set_gecos(u, e.get_text().strip()))
        gecos_row.add_suffix(entry)
        self.cur_grp.add(gecos_row)

        # Password
        self.cur_grp.add(action_row(
            "Change my password",
            "Opens a terminal with passwd (interactive prompts are needed)",
            "Change",
            lambda: open_terminal("passwd", self.win)))

        # Avatar
        face = Path.home() / ".face"
        face_row = Adw.ActionRow(
            title="Avatar",
            subtitle=str(face) + (
                "  ·  set ✓" if face.exists() else "  ·  not set"))
        btn = Gtk.Button(label="Choose…")
        btn.add_css_class("nyx-pill")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda _b: self._pick_avatar())
        face_row.add_suffix(btn)
        self.cur_grp.add(face_row)

        # Shell editor
        self.cur_grp.add(action_row(
            "Change my shell",
            "Opens chsh in a terminal",
            "Edit",
            lambda: open_terminal("chsh", self.win)))

    def _set_gecos(self, user: str, full_name: str) -> None:
        sh_async(
            ["pkexec", "chfn", "-f", full_name, user],
            lambda r: (self.toast(
                f"name → {full_name}" if r[0] == 0 else "needs admin"),
                self._render_current()),
            timeout=10)

    def _pick_avatar(self) -> None:
        dlg = Gtk.FileChooserNative(
            title="Pick an avatar image",
            transient_for=self.win,
            action=Gtk.FileChooserAction.OPEN,
            accept_label="Use",
            cancel_label="Cancel")
        flt = Gtk.FileFilter()
        flt.set_name("Images")
        for p in ("png", "jpg", "jpeg", "webp"):
            flt.add_pattern(f"*.{p}")
        dlg.add_filter(flt)
        dlg.connect("response", self._on_avatar_picked)
        dlg.show()
        # Keep ref so it isn't GC'd
        self._avatar_dlg = dlg

    def _on_avatar_picked(self, dlg, resp) -> None:
        if resp != Gtk.ResponseType.ACCEPT:
            dlg.destroy()
            return
        f = dlg.get_file()
        dlg.destroy()
        if not f:
            return
        src = f.get_path()
        face = Path.home() / ".face"
        try:
            shutil.copy2(src, face)
            face.chmod(0o644)
            self.toast(f"avatar → {face.name}")
            # Also update accountsservice if available
            user = self._whoami()
            asu = Path(f"/var/lib/AccountsService/users/{user}")
            if asu.parent.exists():
                sh_async(
                    ["pkexec", "sh", "-c",
                     f"mkdir -p /var/lib/AccountsService/users && "
                     f"printf '[User]\\nIcon={face}\\n' > "
                     f"/var/lib/AccountsService/users/{user}"],
                    lambda r: None, timeout=6)
            self._render_current()
        except Exception as e:
            self.toast(f"failed: {e}")

    # ── Other accounts ───────────────────────────────────────
    def _render_others(self) -> None:
        _clear_group(self.others_grp)
        me = self._whoami()
        others = [u for u in self._list_real_users() if u[0] != me]
        if not others:
            self.others_grp.add(empty_row(
                "No other user accounts",
                "This system has only your account"))
            return
        for name, uid, gecos, shell in others[:30]:
            groups = self._user_groups(name)
            is_admin = "wheel" in groups
            row = Adw.ActionRow(
                title=name + (f"  ·  {gecos}" if gecos else ""),
                subtitle=f"uid {uid}  ·  {shell}  ·  "
                         f"{'Administrator' if is_admin else 'Standard'}")

            # Toggle admin
            admin_btn = Gtk.Button(
                label="Demote" if is_admin else "Make admin")
            admin_btn.add_css_class(
                "nyx-pill-warn" if is_admin else "nyx-pill")
            admin_btn.set_valign(Gtk.Align.CENTER)
            admin_btn.connect(
                "clicked",
                lambda _b, u=name, on=not is_admin:
                    self._toggle_admin(u, on))
            row.add_suffix(admin_btn)

            # Reset password
            pwd_btn = Gtk.Button(label="Set password")
            pwd_btn.add_css_class("nyx-pill")
            pwd_btn.set_valign(Gtk.Align.CENTER)
            pwd_btn.connect(
                "clicked",
                lambda _b, u=name: open_terminal(
                    f"sudo passwd {u}", self.win))
            row.add_suffix(pwd_btn)

            # Delete
            del_btn = Gtk.Button(label="Delete")
            del_btn.add_css_class("nyx-pill-warn")
            del_btn.set_valign(Gtk.Align.CENTER)
            del_btn.connect(
                "clicked",
                lambda _b, u=name: self._confirm_delete_user(u))
            row.add_suffix(del_btn)

            self.others_grp.add(row)

    def _toggle_admin(self, user: str, on: bool) -> None:
        cmd = (["pkexec", "gpasswd", "-a", user, "wheel"] if on
               else ["pkexec", "gpasswd", "-d", user, "wheel"])
        sh_async(
            cmd,
            lambda r: (self.toast(
                f"{user} {'now admin' if on else 'demoted'}"
                if r[0] == 0 else "failed"),
                self._render_others()),
            timeout=10)

    def _confirm_delete_user(self, user: str) -> None:
        dlg = Adw.MessageDialog(
            transient_for=self.win,
            heading=f"Delete user {user}?",
            body=f"This will run:\n  pkexec userdel -r {user}\n\n"
                 f"The home directory /home/{user} and all its contents "
                 f"will be permanently deleted. This cannot be undone.")
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("ok", "Delete")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        dlg.connect("response",
                    lambda d, resp, u=user: self._do_delete_user(resp, u))
        dlg.present()

    def _do_delete_user(self, resp: str, user: str) -> None:
        if resp != "ok":
            return
        sh_async(
            ["pkexec", "userdel", "-r", user],
            lambda r: (self.toast(
                f"{user} deleted" if r[0] == 0
                else f"failed: {r[2][:80] if r[2] else 'admin denied'}"),
                self._render_others()),
            timeout=30)

    # ── Add new user ─────────────────────────────────────────
    def _render_add(self) -> None:
        _clear_group(self.add_grp)
        u_row = Adw.ActionRow(title="Username",
                              subtitle="lowercase, no spaces")
        u_entry = Gtk.Entry()
        u_entry.set_size_request(180, -1)
        u_entry.set_valign(Gtk.Align.CENTER)
        u_row.add_suffix(u_entry)
        self.add_grp.add(u_row)
        self._add_username = u_entry

        f_row = Adw.ActionRow(title="Full name (optional)",
                              subtitle="display name shown in greeters")
        f_entry = Gtk.Entry()
        f_entry.set_size_request(220, -1)
        f_entry.set_valign(Gtk.Align.CENTER)
        f_row.add_suffix(f_entry)
        self.add_grp.add(f_row)
        self._add_fullname = f_entry

        a_row = Adw.ActionRow(
            title="Grant administrator (sudo) access",
            subtitle="adds the new user to the wheel group")
        a_sw = Gtk.Switch()
        a_sw.set_valign(Gtk.Align.CENTER)
        a_row.add_suffix(a_sw)
        self.add_grp.add(a_row)
        self._add_admin = a_sw

        action = Adw.ActionRow(
            title="Create account",
            subtitle="you'll be prompted for an admin password to confirm")
        btn = Gtk.Button(label="Create")
        btn.add_css_class("nyx-pill-ok")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda _b: self._create_user())
        action.add_suffix(btn)
        self.add_grp.add(action)

    def _create_user(self) -> None:
        user = self._add_username.get_text().strip()
        fullname = self._add_fullname.get_text().strip()
        admin = self._add_admin.get_active()
        if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", user):
            self.toast("invalid username")
            return
        # Build the create-and-set-password command.
        # We can't take a password input safely here, so we drop the user
        # straight into a terminal for `passwd` after creation.
        groups = "wheel,audio,video,input,storage" if admin \
            else "audio,video,input,storage"
        cmd = (f"useradd -m -G {groups} -s /bin/bash "
               f"-c {shlex.quote(fullname or user)} {user}")
        sh_async(
            ["pkexec", "sh", "-c", cmd],
            lambda r: self._on_user_created(r, user),
            timeout=20)

    def _on_user_created(self, result, user: str) -> None:
        rc, out, err = result
        if rc != 0:
            self.toast(f"create failed: {(err or out)[:80]}")
            return
        self.toast(f"{user} created — opening passwd")
        # Open a terminal so the admin can set the password
        open_terminal(f"sudo passwd {user}", self.win)
        self._render_others()
        self._add_username.set_text("")
        self._add_fullname.set_text("")
        self._add_admin.set_active(False)

    # ── Sudoers ──────────────────────────────────────────────
    def _render_sudoers(self) -> None:
        _clear_group(self.sudoers_grp)
        rc, out, _ = sh(["getent", "group", "wheel"], timeout=2)
        members = []
        if rc == 0 and out.strip():
            parts = out.strip().split(":")
            if len(parts) >= 4 and parts[3]:
                members = parts[3].split(",")
        if members:
            self.sudoers_grp.add(kv_row(
                "wheel members", ", ".join(members),
                "these users can run sudo"))
        else:
            self.sudoers_grp.add(kv_row(
                "wheel members", "(none)",
                "no user has sudo access"))
        self.sudoers_grp.add(action_row(
            "Edit /etc/sudoers safely",
            "Opens visudo — uses syntax checking before saving",
            "Open",
            lambda: open_terminal("sudo visudo", self.win),
            css="nyx-pill-warn"))

    # ── Sessions ─────────────────────────────────────────────
    def _render_sessions(self) -> None:
        _clear_group(self.sessions_grp)
        rc, out, _ = sh(["loginctl", "list-sessions", "--no-legend"],
                        timeout=3)
        rows = [l for l in out.splitlines() if l.strip()]
        if not rows:
            self.sessions_grp.add(empty_row(
                "No active sessions reported", ""))
            return
        for r in rows[:12]:
            parts = r.split()
            if len(parts) >= 4:
                self.sessions_grp.add(kv_row(
                    parts[2],
                    f"session {parts[0]}  ·  seat {parts[3]}"))


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
# Curated DARK MIRROR accent palette.  The "Mirror White" preset is the
# brand default and matches the locked SDDM/hyprlock palette tokens.
ACCENT_PRESETS: List[Tuple[str, str]] = [
    ("Mirror White", "#e8edf5"),
    ("Cyan",         "#5fd3f3"),
    ("Lime",         "#a6e22e"),
    ("Amber",        "#f5b342"),
    ("Magenta",      "#ff5fa7"),
    ("Crimson",      "#ff5f6d"),
    ("Iris",         "#9c8cff"),
    ("Mint",         "#5ff3b8"),
]
DEFAULT_ACCENT = "#e8edf5"

# Files we own for accent propagation. Each is a small idempotent fragment
# included by the parent config (so we never mangle hand-written files).
ACCENT_FRAG_DIR = HOME / ".config" / "nyxus" / "accent"
GTK3_FRAG  = HOME / ".config" / "gtk-3.0" / "nyxus-accent.css"
GTK4_FRAG  = HOME / ".config" / "gtk-4.0" / "nyxus-accent.css"
EWW_FRAG   = HOME / ".config" / "eww" / "_nyxus_accent.scss"
ROFI_FRAG  = HOME / ".config" / "rofi" / "nyxus-accent.rasi"
DUNST_FRAG = HOME / ".config" / "dunst" / "nyxus-accent.conf"   # informative
HYPRLOCK_ACCENT = HOME / ".config" / "hypr" / "hyprlock-accent.conf"
SDDM_THEME_USER = Path("/usr/share/sddm/themes/nyxus/theme.conf.user")


def _hex_to_rgb(hex_str: str) -> Tuple[int, int, int]:
    s = hex_str.lstrip("#")
    if len(s) == 3:
        s = "".join(c * 2 for c in s)
    if len(s) != 6:
        return (232, 237, 245)
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except ValueError:
        return (232, 237, 245)


def _atomic_write(path: Path, text: str) -> bool:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".nyxtmp")
        tmp.write_text(text)
        tmp.replace(path)
        return True
    except Exception as e:
        log.warning("accent write %s failed: %s", path, e)
        return False


class AppearancePage(SectionPage):
    """Single source of truth for accent + theme. All fully wired:
      · accent picker → GTK3/4 frag, EWW scss, rofi rasi, hyprlock accent,
        dunst frame_color, SDDM theme.conf.user (pkexec)
      · color scheme  → gsettings org.gnome.desktop.interface color-scheme
      · cursor theme  → ~/.icons/default + gsettings + GTK_CURSOR_THEME
      · icon theme    → gsettings icon-theme
      · fonts         → gsettings font-name + monospace-font-name
      · wallpaper     → swaybg (existing) + rotation timer
      · text scale    → font_scale pref + GTK_DPI hint
      · motion        → hyprctl keyword animations:enabled
    """
    KEY = "appearance"

    # ── Build ─────────────────────────────────────────────────────────
    def build(self) -> None:
        prefs = self.win.prefs

        # Theme variant — locked
        g_theme = Adw.PreferencesGroup(title="Theme")
        v_row = Adw.ActionRow(
            title="Variant",
            subtitle="DARK MIRROR — locked by NYXUS design contract")
        v_row.add_suffix(status_pill("DARK MIRROR", "ok"))
        g_theme.add(v_row)
        self.add_group(g_theme)

        # Accent picker
        self.accent_grp = Adw.PreferencesGroup(
            title="Accent",
            description="Single source of truth — propagates to GTK, EWW, "
                        "rofi, hyprlock, dunst, SDDM")
        self.add_group(self.accent_grp)

        # Color scheme
        self.scheme_grp = Adw.PreferencesGroup(
            title="Color scheme",
            description="Affects GTK4/libadwaita apps that respect the "
                        "system color-scheme setting")
        self.add_group(self.scheme_grp)

        # Cursor theme
        self.cursor_grp = Adw.PreferencesGroup(
            title="Cursor theme",
            description="Reads /usr/share/icons and ~/.icons")
        self.add_group(self.cursor_grp)

        # Icon theme
        self.icon_grp = Adw.PreferencesGroup(
            title="Icon theme",
            description="Reads /usr/share/icons and ~/.icons")
        self.add_group(self.icon_grp)

        # Fonts
        self.font_grp = Adw.PreferencesGroup(
            title="Fonts",
            description="System UI font and monospace font for terminals")
        self.add_group(self.font_grp)

        # Wallpaper grid (kept from previous + rotation switch)
        self.wall_grp = Adw.PreferencesGroup(
            title="Wallpaper",
            description="Click a wallpaper to apply it system-wide via swaybg")
        self.add_group(self.wall_grp)

        # Text size
        self.scale_grp = Adw.PreferencesGroup(
            title="Text size",
            description="UI scale for NYXUS apps — restart apps to apply")
        self.add_group(self.scale_grp)

        # Hot Corners (Tier 3 #15)
        self.hot_grp = Adw.PreferencesGroup(
            title="Hot Corners",
            description="Trigger an action by parking the cursor in a "
                        "screen corner (Hyprland-only)")
        self.add_group(self.hot_grp)

        # Motion
        self.motion_grp = Adw.PreferencesGroup(title="Motion")
        self.add_group(self.motion_grp)

        self._render()

    def _render(self) -> None:
        self._render_accent()
        self._render_scheme()
        self._render_cursor()
        self._render_icons()
        self._render_fonts()
        self._render_wallpaper()
        self._render_hotcorners()
        self._render_scale()
        self._render_motion()

        self.clear_pills()
        backends = []
        if have("swaybg"):  backends.append("swaybg")
        if have("hyprctl"): backends.append("hyprctl")
        if have("gsettings"): backends.append("gsettings")
        kind = "ok" if len(backends) >= 2 else "warn"
        self.add_pill(status_pill(
            " · ".join(backends) if backends else "no backends", kind))

    # ── Accent ────────────────────────────────────────────────────────
    def _render_accent(self) -> None:
        _clear_group(self.accent_grp)
        prefs = self.win.prefs
        current = prefs.get("accent_hex", DEFAULT_ACCENT)

        # Swatch row — flowbox of preset chips
        chip_row = Adw.PreferencesRow()
        chip_row.set_activatable(False)
        chip_row.set_selectable(False)
        flow = Gtk.FlowBox()
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        flow.set_max_children_per_line(8)
        flow.set_min_children_per_line(4)
        flow.set_homogeneous(True)
        flow.set_column_spacing(8)
        flow.set_row_spacing(8)
        flow.set_margin_start(8)
        flow.set_margin_end(8)
        flow.set_margin_top(10)
        flow.set_margin_bottom(10)

        for name, hex_val in ACCENT_PRESETS:
            chip = Gtk.Button()
            chip.set_size_request(64, 48)
            chip.set_tooltip_text(f"{name}  ·  {hex_val}")
            chip.add_css_class("nyx-accent-chip")
            if hex_val.lower() == current.lower():
                chip.add_css_class("selected")
            # Inline CSS provider for the chip color (per-widget)
            css = Gtk.CssProvider()
            css.load_from_data(
                f"button.nyx-accent-chip {{"
                f"  background: {hex_val};"
                f"  border: 1px solid rgba(255,255,255,0.18);"
                f"  border-radius: 10px;"
                f"  min-width: 60px; min-height: 44px;"
                f"}}"
                f"button.nyx-accent-chip.selected {{"
                f"  border: 2px solid #ffffff;"
                f"}}".encode())
            chip.get_style_context().add_provider(
                css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            chip.connect("clicked",
                         lambda _b, h=hex_val: self._set_accent(h))
            flow.append(chip)

        chip_row.set_child(flow)
        self.accent_grp.add(chip_row)

        # Custom hex entry
        hex_row = Adw.ActionRow(
            title="Custom",
            subtitle=f"Currently: {current}  ·  enter a #RRGGBB value")
        entry = Gtk.Entry()
        entry.set_placeholder_text("#5fd3f3")
        entry.set_text(current)
        entry.set_max_length(7)
        entry.set_size_request(110, -1)
        entry.set_valign(Gtk.Align.CENTER)
        entry.connect("activate", lambda e: self._set_accent(e.get_text()))
        hex_row.add_suffix(entry)
        apply_btn = Gtk.Button(label="Apply")
        apply_btn.add_css_class("nyx-pill-ok")
        apply_btn.set_valign(Gtk.Align.CENTER)
        apply_btn.connect("clicked",
                          lambda _b: self._set_accent(entry.get_text()))
        hex_row.add_suffix(apply_btn)
        self.accent_grp.add(hex_row)

        # Reset
        reset = action_row(
            "Reset to default",
            f"Restores Mirror White ({DEFAULT_ACCENT})",
            "Reset",
            lambda: self._set_accent(DEFAULT_ACCENT))
        self.accent_grp.add(reset)

        # Status: which propagation targets are present
        targets = []
        if (HOME / ".config" / "gtk-3.0").exists() or \
           (HOME / ".config" / "gtk-4.0").exists():
            targets.append("GTK")
        if (HOME / ".config" / "eww").exists():
            targets.append("EWW")
        if (HOME / ".config" / "rofi").exists():
            targets.append("rofi")
        if (HOME / ".config" / "hypr").exists():
            targets.append("hyprlock")
        if (HOME / ".config" / "dunst").exists():
            targets.append("dunst")
        if SDDM_THEME_USER.parent.exists():
            targets.append("SDDM")
        info = Adw.ActionRow(
            title="Propagates to",
            subtitle=", ".join(targets) if targets
                     else "no theme dirs found yet — first apply will create them")
        self.accent_grp.add(info)

    def _set_accent(self, hex_str: str) -> None:
        h = (hex_str or "").strip()
        if not re.fullmatch(r"#?[0-9A-Fa-f]{3}([0-9A-Fa-f]{3})?", h):
            self.toast("invalid hex — use #RRGGBB")
            return
        if not h.startswith("#"):
            h = "#" + h
        # Expand 3-digit to 6-digit
        if len(h) == 4:
            h = "#" + "".join(c * 2 for c in h[1:])
        h = h.lower()

        # Persist
        self.win.prefs["accent_hex"] = h
        save_prefs(self.win.prefs)

        results = self._apply_accent(h)
        ok = [k for k, v in results.items() if v]
        fail = [k for k, v in results.items() if not v]
        if fail:
            self.toast(f"accent {h}  ·  ok: {', '.join(ok) or '—'}  "
                       f"·  failed: {', '.join(fail)}")
        else:
            self.toast(f"accent {h} applied to {', '.join(ok)}")
        self._render_accent()

    def _apply_accent(self, h: str) -> dict:
        """Write accent fragments + reload the apps that read them.
        Each target is independent; one failure does not block the rest."""
        r, g, b = _hex_to_rgb(h)
        results: dict = {}

        # 1) GTK3 — @define-color override
        gtk3_text = textwrap.dedent(f"""\
            /* nyxus accent — auto-generated by Settings, do not edit */
            @define-color nyxus_accent {h};
            @define-color accent_color {h};
            @define-color accent_bg_color {h};
            @define-color theme_selected_bg_color {h};
            """)
        results["gtk-3"] = _atomic_write(GTK3_FRAG, gtk3_text)
        # Try to ensure gtk.css imports the fragment
        self._ensure_gtk_import(HOME / ".config" / "gtk-3.0" / "gtk.css",
                                "nyxus-accent.css")

        # 2) GTK4
        results["gtk-4"] = _atomic_write(GTK4_FRAG, gtk3_text)
        self._ensure_gtk_import(HOME / ".config" / "gtk-4.0" / "gtk.css",
                                "nyxus-accent.css")

        # 3) EWW — SCSS variable
        eww_text = (f"// nyxus accent — auto-generated\n"
                    f"$nyxus-accent: {h};\n"
                    f"$accent: {h};\n")
        results["eww"] = _atomic_write(EWW_FRAG, eww_text)

        # 4) rofi — rasi color block
        rofi_text = (f"/* nyxus accent — auto-generated */\n"
                     f"* {{\n"
                     f"  nyxus-accent: {h};\n"
                     f"  selected-normal-background: {h};\n"
                     f"  active-foreground: {h};\n"
                     f"}}\n")
        results["rofi"] = _atomic_write(ROFI_FRAG, rofi_text)

        # 5) hyprlock — separate accent file the user can $source from
        # hyprlock.conf, OR we patch the inner_color/outer_color directly.
        hl_text = textwrap.dedent(f"""\
            # nyxus accent — auto-generated. $source = ~/.config/hypr/hyprlock-accent.conf
            $nyxus_accent_r = {r}
            $nyxus_accent_g = {g}
            $nyxus_accent_b = {b}
            $nyxus_accent_rgba = rgba({r}, {g}, {b}, 0.85)
            """)
        results["hyprlock"] = _atomic_write(HYPRLOCK_ACCENT, hl_text)

        # 6) dunst — frame_color in fragment + signal reload
        dunst_text = (f"# nyxus accent — auto-generated.\n"
                      f"# include this from your dunstrc [global] section, e.g.:\n"
                      f"#   frame_color = \"{h}\"\n"
                      f"frame_color = \"{h}\"\n")
        results["dunst"] = _atomic_write(DUNST_FRAG, dunst_text)
        self._patch_dunstrc(h)

        # 7) SDDM — needs root, dispatch async; report real outcome via toast.
        # We mark it "pending" synchronously so the immediate UI message
        # doesn't lie about success.
        if SDDM_THEME_USER.parent.exists():
            sddm_text = (f"[General]\n"
                         f"background=background.png\n"
                         f"# nyxus accent\n"
                         f"Accent={h}\n")
            sh_async(
                ["pkexec", "sh", "-c",
                 f"cat > {SDDM_THEME_USER} <<'NYXUS_EOF'\n"
                 f"{sddm_text}NYXUS_EOF\n"],
                lambda res: self.toast(
                    "SDDM accent applied" if res[0] == 0
                    else "SDDM accent denied (admin auth required)"),
                timeout=15)
            results["sddm"] = "pending"  # truthful: not-yet-confirmed
        else:
            results["sddm"] = False

        # 8) Reload apps that read these files
        if have("dunstify") or have("dunst"):
            sh_async(["sh", "-c",
                      "pkill -SIGUSR2 dunst 2>/dev/null || true"],
                     lambda r: None, timeout=3)
        if have("eww"):
            sh_async(["eww", "reload"], lambda r: None, timeout=4)
        if have("hyprctl"):
            sh_async(["hyprctl", "reload"], lambda r: None, timeout=4)

        return results

    @staticmethod
    def _ensure_gtk_import(gtk_css: Path, frag_name: str) -> None:
        """Idempotently add @import url("nyxus-accent.css"); to gtk.css."""
        try:
            gtk_css.parent.mkdir(parents=True, exist_ok=True)
            existing = gtk_css.read_text() if gtk_css.exists() else ""
            line = f'@import url("{frag_name}");'
            if line in existing:
                return
            new = line + "\n" + existing
            gtk_css.write_text(new)
        except Exception as e:
            log.warning("ensure_gtk_import %s: %s", gtk_css, e)

    @staticmethod
    def _patch_dunstrc(h: str) -> None:
        """Best-effort in-place patch of frame_color in ~/.config/dunst/dunstrc.
        Idempotent — only rewrites the matching line."""
        rc = HOME / ".config" / "dunst" / "dunstrc"
        if not rc.exists():
            return
        try:
            txt = rc.read_text()
            new = re.sub(
                r'^(\s*frame_color\s*=\s*)"[^"]*"',
                lambda m: f'{m.group(1)}"{h}"',
                txt, flags=re.MULTILINE)
            if new != txt:
                rc.write_text(new)
        except Exception as e:
            log.warning("patch dunstrc: %s", e)

    # ── Color scheme ──────────────────────────────────────────────────
    def _render_scheme(self) -> None:
        _clear_group(self.scheme_grp)
        # Read current
        rc, out, _ = sh(["gsettings", "get",
                         "org.gnome.desktop.interface", "color-scheme"],
                        timeout=2)
        cur = out.strip().strip("'")
        is_dark = "dark" in cur
        row = Adw.SwitchRow(
            title="Prefer dark color scheme",
            subtitle="Currently: " + (cur or "(unset)"))
        row.set_active(is_dark or not cur)
        row.connect("notify::active", self._on_scheme_toggle)
        self.scheme_grp.add(row)

    def _on_scheme_toggle(self, row: Adw.SwitchRow, _ps) -> None:
        v = "prefer-dark" if row.get_active() else "default"
        if not have("gsettings"):
            self.toast("gsettings not installed")
            return
        sh_async(
            ["gsettings", "set", "org.gnome.desktop.interface",
             "color-scheme", v],
            lambda r: self.toast(
                f"color-scheme → {v}" if r[0] == 0 else "failed"),
            timeout=4)

    # ── Cursor / Icon theme pickers ───────────────────────────────────
    @staticmethod
    def _list_cursor_themes() -> List[str]:
        roots = [Path("/usr/share/icons"), HOME / ".icons",
                 HOME / ".local" / "share" / "icons"]
        themes: set = set()
        for root in roots:
            if not root.exists():
                continue
            for child in root.iterdir():
                if (child / "cursors").is_dir():
                    themes.add(child.name)
        return sorted(themes)

    @staticmethod
    def _list_icon_themes() -> List[str]:
        roots = [Path("/usr/share/icons"), HOME / ".icons",
                 HOME / ".local" / "share" / "icons"]
        themes: set = set()
        for root in roots:
            if not root.exists():
                continue
            for child in root.iterdir():
                idx = child / "index.theme"
                if not idx.is_file():
                    continue
                # Skip cursor-only themes (no Directories= line is a hint)
                try:
                    txt = idx.read_text(errors="ignore")
                    if "Directories=" in txt:
                        themes.add(child.name)
                except Exception:
                    continue
        return sorted(themes)

    def _render_cursor(self) -> None:
        _clear_group(self.cursor_grp)
        themes = self._list_cursor_themes()
        rc, cur, _ = sh(["gsettings", "get",
                         "org.gnome.desktop.interface", "cursor-theme"],
                        timeout=2)
        current = cur.strip().strip("'") or "default"
        if not themes:
            self.cursor_grp.add(empty_row(
                "No cursor themes found",
                "Install a cursor theme package, e.g. xcursor-breeze"))
            return
        row = Adw.ComboRow(
            title="Cursor theme",
            subtitle=f"current: {current}")
        store = Gtk.StringList()
        sel_idx = 0
        for i, t in enumerate(themes):
            store.append(t)
            if t == current:
                sel_idx = i
        row.set_model(store)
        row.set_selected(sel_idx)
        row.connect("notify::selected",
                    lambda r, _p: self._set_cursor_theme(
                        themes[r.get_selected()]))
        self.cursor_grp.add(row)

        # Size
        rc, sz, _ = sh(["gsettings", "get",
                        "org.gnome.desktop.interface", "cursor-size"],
                       timeout=2)
        try:
            cur_sz = int(sz.strip())
        except ValueError:
            cur_sz = 24
        sz_row = Adw.ActionRow(title="Cursor size",
                               subtitle="default 24 — try 32 on HiDPI")
        adj = Gtk.Adjustment(value=cur_sz, lower=16, upper=64,
                             step_increment=4)
        spin = Gtk.SpinButton()
        spin.set_adjustment(adj)
        spin.set_valign(Gtk.Align.CENTER)
        spin.connect("value-changed",
                     lambda s: self._set_cursor_size(s.get_value_as_int()))
        sz_row.add_suffix(spin)
        self.cursor_grp.add(sz_row)

    def _set_cursor_theme(self, name: str) -> None:
        if not have("gsettings"):
            self.toast("gsettings missing")
            return
        sh_async(
            ["gsettings", "set", "org.gnome.desktop.interface",
             "cursor-theme", name],
            lambda r: self.toast(f"cursor → {name}"
                                 if r[0] == 0 else "failed"),
            timeout=4)
        # Also set Hyprland cursor at runtime
        if have("hyprctl"):
            sh_async(["hyprctl", "setcursor", name, "24"],
                     lambda r: None, timeout=3)

    def _set_cursor_size(self, sz: int) -> None:
        if not have("gsettings"):
            return
        sh_async(
            ["gsettings", "set", "org.gnome.desktop.interface",
             "cursor-size", str(sz)],
            lambda r: self.toast(f"cursor size → {sz}"),
            timeout=4)

    def _render_icons(self) -> None:
        _clear_group(self.icon_grp)
        themes = self._list_icon_themes()
        rc, cur, _ = sh(["gsettings", "get",
                         "org.gnome.desktop.interface", "icon-theme"],
                        timeout=2)
        current = cur.strip().strip("'") or "Adwaita"
        if not themes:
            self.icon_grp.add(empty_row(
                "No icon themes found",
                "Install one, e.g. papirus-icon-theme"))
            return
        row = Adw.ComboRow(
            title="Icon theme",
            subtitle=f"current: {current}")
        store = Gtk.StringList()
        sel_idx = 0
        for i, t in enumerate(themes):
            store.append(t)
            if t == current:
                sel_idx = i
        row.set_model(store)
        row.set_selected(sel_idx)
        row.connect("notify::selected",
                    lambda r, _p: self._set_icon_theme(
                        themes[r.get_selected()]))
        self.icon_grp.add(row)

    def _set_icon_theme(self, name: str) -> None:
        if not have("gsettings"):
            self.toast("gsettings missing")
            return
        sh_async(
            ["gsettings", "set", "org.gnome.desktop.interface",
             "icon-theme", name],
            lambda r: self.toast(f"icons → {name}"
                                 if r[0] == 0 else "failed"),
            timeout=4)

    # ── Fonts ─────────────────────────────────────────────────────────
    def _render_fonts(self) -> None:
        _clear_group(self.font_grp)
        rc, ui, _ = sh(["gsettings", "get",
                        "org.gnome.desktop.interface", "font-name"],
                       timeout=2)
        rc, mono, _ = sh(["gsettings", "get",
                          "org.gnome.desktop.interface",
                          "monospace-font-name"], timeout=2)
        ui = ui.strip().strip("'")
        mono = mono.strip().strip("'")

        ui_row = Adw.ActionRow(
            title="Interface font",
            subtitle=ui or "(unset)")
        ui_btn = Gtk.Button(label="Choose…")
        ui_btn.add_css_class("nyx-pill")
        ui_btn.set_valign(Gtk.Align.CENTER)
        ui_btn.connect("clicked",
                       lambda _b: self._pick_font(
                           "font-name", ui or "Inter 11"))
        ui_row.add_suffix(ui_btn)
        self.font_grp.add(ui_row)

        m_row = Adw.ActionRow(
            title="Monospace font",
            subtitle=mono or "(unset)")
        m_btn = Gtk.Button(label="Choose…")
        m_btn.add_css_class("nyx-pill")
        m_btn.set_valign(Gtk.Align.CENTER)
        m_btn.connect("clicked",
                      lambda _b: self._pick_font(
                          "monospace-font-name",
                          mono or "JetBrains Mono 11"))
        m_row.add_suffix(m_btn)
        self.font_grp.add(m_row)

    def _pick_font(self, key: str, current: str) -> None:
        # GTK 4.10+ provides Gtk.FontDialog. On older builds we fall back
        # to a plain text-entry asking for a Pango font string.
        if not hasattr(Gtk, "FontDialog"):
            self._pick_font_fallback(key, current)
            return
        try:
            from gi.repository import Pango
            dlg = Gtk.FontDialog()
            dlg.set_title("Choose a font")
            initial = Pango.FontDescription.from_string(current)
            dlg.choose_font(self.win, initial, None,
                            lambda d, res: self._on_font_picked(
                                d, res, key))
        except Exception as e:
            log.warning("FontDialog failed: %s — falling back", e)
            self._pick_font_fallback(key, current)

    def _pick_font_fallback(self, key: str, current: str) -> None:
        dlg = Adw.MessageDialog(
            transient_for=self.win,
            heading="Choose a font",
            body="Type a Pango font description, e.g. 'Inter 11' or "
                 "'JetBrains Mono Bold 12'.")
        entry = Gtk.Entry()
        entry.set_text(current)
        entry.set_margin_top(8)
        entry.set_margin_bottom(8)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dlg.set_extra_child(entry)
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("ok", "Apply")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("ok")

        def on_resp(_d, resp):
            if resp != "ok":
                return
            name = entry.get_text().strip()
            if not name:
                return
            sh_async(
                ["gsettings", "set",
                 "org.gnome.desktop.interface", key, name],
                lambda r: (self.toast(f"{key} → {name}"),
                           self._render_fonts()),
                timeout=4)
        dlg.connect("response", on_resp)
        dlg.present()

    def _on_font_picked(self, dlg, res, key: str) -> None:
        try:
            font_desc = dlg.choose_font_finish(res)
        except Exception:
            return
        if not font_desc:
            return
        name = font_desc.to_string()
        if not have("gsettings"):
            self.toast("gsettings missing")
            return
        sh_async(
            ["gsettings", "set", "org.gnome.desktop.interface", key, name],
            lambda r: (self.toast(f"{key} → {name}"),
                       self._render_fonts()),
            timeout=4)

    # ── Wallpaper ─────────────────────────────────────────────────────
    def _render_wallpaper(self) -> None:
        _clear_group(self.wall_grp)
        prefs = self.win.prefs

        self.wall_grp.add(action_row(
            "Wallpaper Studio",
            "Open the dedicated NYXUS Wallpaper Studio app",
            "Launch",
            lambda: fire_and_forget(
                "nyxus wallpaper_studio >/dev/null 2>&1 "
                "|| python3 ~/.nyxus/nyxus_wallpaper_studio.py >/dev/null 2>&1"
            )))

        # Rotation toggle
        rot_row = Adw.SwitchRow(
            title="Rotate wallpaper",
            subtitle="Cycle through ~/Pictures/Wallpapers every 30 minutes")
        rot_row.set_active(prefs.get("wallpaper_rotate", False))
        rot_row.connect("notify::active", self._on_wall_rotate)
        self.wall_grp.add(rot_row)

        # Dynamic / time-of-day wallpaper (Tier 3 #17)
        dyn_row = Adw.SwitchRow(
            title="Dynamic wallpaper",
            subtitle="Switches between dawn/day/dusk/night images "
                     "automatically (hourly systemd --user timer)")
        dyn_row.set_active(prefs.get("wallpaper_dynamic", False))
        dyn_row.connect("notify::active", self._on_wall_dynamic)
        self.wall_grp.add(dyn_row)
        if prefs.get("wallpaper_dynamic", False):
            set_combo = Adw.ComboRow(
                title="Dynamic set",
                subtitle="Image group used by the time-of-day picker")
            sets = ["cosmos", "darkmirror", "watercolor"]
            set_combo.set_model(Gtk.StringList.new(sets))
            cur_set = str(prefs.get("wallpaper_dynamic_set", "cosmos"))
            try:
                set_combo.set_selected(sets.index(cur_set))
            except ValueError:
                set_combo.set_selected(0)
            set_combo.connect(
                "notify::selected",
                lambda c, _p, opts=sets: self._on_wall_dynamic_set(
                    opts[c.get_selected()]))
            self.wall_grp.add(set_combo)

        # Grid wrapper
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
                walls.extend(sorted(
                    p for p in d.iterdir()
                    if p.suffix.lower() in (".png", ".jpg",
                                            ".jpeg", ".webp")))
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
            for wp in walls[:30]:
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
        self.wall_grp.add(wall_row)

    def _on_wallpaper(self, btn: Gtk.Button, path: Path) -> None:
        self.win.prefs["wallpaper"] = str(path)
        save_prefs(self.win.prefs)
        flow = btn.get_parent()
        if isinstance(flow, Gtk.FlowBox):
            child = flow.get_first_child()
            while child:
                inner = child.get_first_child()
                if isinstance(inner, Gtk.Button):
                    inner.remove_css_class("selected")
                child = child.get_next_sibling()
        btn.add_css_class("selected")
        if have("swaybg"):
            sh_async(
                ["sh", "-c",
                 f"pkill -x swaybg 2>/dev/null; "
                 f"swaybg -i {str(path)!r} -m fill -c '#000000' "
                 f">/dev/null 2>&1 &"],
                lambda r: self.toast(
                    "wallpaper applied" if r[0] == 0
                    else f"swaybg failed: {r[2][:60]}"))
        else:
            self.toast("swaybg not installed — saved selection only")

    def _on_wall_rotate(self, row: Adw.SwitchRow, _ps) -> None:
        on = row.get_active()
        self.win.prefs["wallpaper_rotate"] = on
        save_prefs(self.win.prefs)
        # Install or remove a small systemd --user timer
        unit_dir = HOME / ".config" / "systemd" / "user"
        unit_dir.mkdir(parents=True, exist_ok=True)
        timer  = unit_dir / "nyxus-wall-rotate.timer"
        svc    = unit_dir / "nyxus-wall-rotate.service"
        helper = HOME / ".local" / "share" / "nyxus" / "wall-rotate.sh"
        if on:
            helper.parent.mkdir(parents=True, exist_ok=True)
            helper.write_text(textwrap.dedent(f"""\
                #!/usr/bin/env bash
                set -eu
                shopt -s nullglob
                walls=( "{WALLS_USR}"/*.{{png,jpg,jpeg,webp}} \\
                        "{WALLS_SYS}"/*.{{png,jpg,jpeg,webp}} )
                [ ${{#walls[@]}} -eq 0 ] && exit 0
                pick="${{walls[RANDOM % ${{#walls[@]}}]}}"
                pkill -x swaybg 2>/dev/null || true
                swaybg -i "$pick" -m fill -c '#000000' >/dev/null 2>&1 &
                """))
            helper.chmod(0o755)
            svc.write_text(textwrap.dedent(f"""\
                [Unit]
                Description=NYXUS wallpaper rotator
                [Service]
                Type=oneshot
                ExecStart={helper}
                """))
            timer.write_text(textwrap.dedent("""\
                [Unit]
                Description=Rotate NYXUS wallpaper every 30 minutes
                [Timer]
                OnBootSec=5min
                OnUnitActiveSec=30min
                Persistent=true
                [Install]
                WantedBy=timers.target
                """))
            sh_async(
                ["sh", "-c",
                 "systemctl --user daemon-reload && "
                 "systemctl --user enable --now nyxus-wall-rotate.timer"],
                lambda r: self.toast(
                    "rotation enabled" if r[0] == 0
                    else "failed to enable timer"),
                timeout=8)
        else:
            sh_async(
                ["sh", "-c",
                 "systemctl --user disable --now "
                 "nyxus-wall-rotate.timer 2>/dev/null || true"],
                lambda r: self.toast("rotation disabled"),
                timeout=6)

    # ── Dynamic / time-of-day wallpaper (Tier 3 #17) ──────────────────
    DYN_CONF = (Path.home() / ".config" / "nyxus"
                / "dynamic-wallpaper.conf")

    def _dyn_write_conf(self, set_name: str) -> bool:
        try:
            self.DYN_CONF.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.DYN_CONF.with_suffix(".conf.tmp")
            tmp.write_text(
                f"# Written by nyxus_settings\nset={set_name}\n",
                encoding="utf-8")
            os.replace(tmp, self.DYN_CONF)
            return True
        except OSError as e:
            log.warning("write %s: %s", self.DYN_CONF, e)
            self.toast(f"can't save dynamic-wallpaper config: {e}")
            return False

    def _on_wall_dynamic(self, row: Adw.SwitchRow, _ps) -> None:
        on = row.get_active()
        prefs = self.win.prefs
        prefs["wallpaper_dynamic"] = on
        save_prefs(prefs)
        if on:
            cur_set = str(prefs.get("wallpaper_dynamic_set", "cosmos"))
            if not self._dyn_write_conf(cur_set):
                row.set_active(False)
                return
            sh_async(
                ["sh", "-c",
                 "systemctl --user daemon-reload >/dev/null 2>&1; "
                 "systemctl --user enable --now "
                 "nyxus-dynamic-wallpaper.timer"],
                lambda r: (
                    self.toast(f"dynamic wallpaper · {cur_set}")
                    if r[0] == 0
                    else self.toast(
                        f"timer enable failed: {(r[2] or '')[:60]}"),
                    self._render_wallpaper())[1],
                timeout=8)
        else:
            sh_async(
                ["sh", "-c",
                 "systemctl --user disable --now "
                 "nyxus-dynamic-wallpaper.timer 2>/dev/null || true"],
                lambda r: (self.toast("dynamic wallpaper disabled"),
                           self._render_wallpaper())[1],
                timeout=6)

    def _on_wall_dynamic_set(self, set_name: str) -> None:
        self.win.prefs["wallpaper_dynamic_set"] = set_name
        save_prefs(self.win.prefs)
        if not self._dyn_write_conf(set_name):
            return
        # Trigger a one-shot run so the new set takes effect immediately
        # without waiting for the next hourly tick.
        sh_async(
            ["systemctl", "--user", "start",
             "nyxus-dynamic-wallpaper.service"],
            lambda r: self.toast(
                f"applied {set_name}" if r[0] == 0
                else f"set apply failed: {(r[2] or '')[:60]}"),
            timeout=6)

    # ── Hot Corners (Tier 3 #15) ──────────────────────────────────────
    HC_CONF = Path.home() / ".config" / "nyxus" / "hotcorners.conf"
    HC_UNIT = (Path.home() / ".config" / "systemd" / "user"
               / "nyxus-hotcorners.service")
    HC_CORNERS = ("tl", "tr", "bl", "br")
    HC_CORNER_LABELS = {
        "tl": "Top-left", "tr": "Top-right",
        "bl": "Bottom-left", "br": "Bottom-right",
    }
    HC_ACTIONS = (
        ("none",            "Off"),
        ("mission_control", "Mission Control"),
        ("spotlight",       "Spotlight search"),
        ("show_desktop",    "Show desktop (scratch)"),
        ("lock",            "Lock screen"),
        ("menu",            "Start menu"),
        ("control_center",  "Control Center"),
        ("notifications",   "Notifications panel"),
    )

    def _hc_read_conf(self) -> dict:
        cfg = {c: "none" for c in self.HC_CORNERS}
        if not self.HC_CONF.exists():
            return cfg
        try:
            for raw in self.HC_CONF.read_text(
                    encoding="utf-8").splitlines():
                s = raw.strip()
                if not s or s.startswith("#") or "=" not in s:
                    continue
                k, _, v = s.partition("=")
                k, v = k.strip().lower(), v.strip()
                if k in cfg:
                    cfg[k] = v
        except OSError as e:
            log.warning("read %s: %s", self.HC_CONF, e)
        return cfg

    def _hc_write_conf(self, cfg: dict) -> bool:
        try:
            self.HC_CONF.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.HC_CONF.with_suffix(".conf.tmp")
            body = "# Written by nyxus_settings — Hot Corners\n"
            for c in self.HC_CORNERS:
                body += f"{c}={cfg.get(c, 'none')}\n"
            tmp.write_text(body, encoding="utf-8")
            os.replace(tmp, self.HC_CONF)
            return True
        except OSError as e:
            log.warning("write %s: %s", self.HC_CONF, e)
            self.toast(f"can't save hot-corner config: {e}")
            return False

    def _hc_active(self) -> bool:
        rc, out, _ = sh(["systemctl", "--user", "is-active",
                         "nyxus-hotcorners.service"], timeout=2)
        return rc == 0 and out.strip() == "active"

    def _render_hotcorners(self) -> None:
        _clear_group(self.hot_grp)
        if not have("hyprctl"):
            self.hot_grp.add(empty_row(
                "Hyprland not detected",
                "Hot corners require hyprctl to read cursor position. "
                "Switch to Hyprland to enable."))
            return

        cfg = self._hc_read_conf()
        active = self._hc_active()

        # Master enable switch — drives the systemd --user service.
        sw = Adw.SwitchRow(
            title="Hot Corners enabled",
            subtitle=("daemon running" if active
                      else "daemon stopped"))
        sw.set_active(active)
        sw.connect("notify::active", self._on_hc_enable)
        self.hot_grp.add(sw)

        action_keys = [a[0] for a in self.HC_ACTIONS]
        action_labels = [a[1] for a in self.HC_ACTIONS]

        for corner in self.HC_CORNERS:
            combo = Adw.ComboRow(title=self.HC_CORNER_LABELS[corner])
            combo.set_model(Gtk.StringList.new(action_labels))
            cur = cfg.get(corner, "none")
            try:
                combo.set_selected(action_keys.index(cur))
            except ValueError:
                combo.set_selected(0)
            combo.connect(
                "notify::selected",
                lambda c, _p, ck=corner, ak=action_keys:
                    self._on_hc_action(ck, ak[c.get_selected()]))
            self.hot_grp.add(combo)

        if active:
            self.add_pill(status_pill("hot corners", "ok"))

    def _hc_install_unit(self) -> None:
        try:
            self.HC_UNIT.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            log.warning("hc unit mkdir: %s", e)
            self.toast(f"can't create unit dir: {e}")
            return
        # Self-healing: re-write the unit so a broken install can be
        # repaired from Settings without re-running the OS installer.
        unit_body = textwrap.dedent("""\
            [Unit]
            Description=NYXUS Hot Corners daemon
            After=graphical-session.target
            PartOf=graphical-session.target

            [Service]
            Type=simple
            ExecStart=/usr/bin/env python3 %h/.local/bin/nyxus_hotcorners.py
            Restart=on-failure
            RestartSec=3s

            [Install]
            WantedBy=graphical-session.target
            """)
        try:
            self.HC_UNIT.write_text(unit_body, encoding="utf-8")
        except OSError as e:
            log.warning("hc unit write: %s", e)
            self.toast(f"can't write hot-corners unit: {e}")
            return
        sh_async(["systemctl", "--user", "daemon-reload"], None,
                 timeout=4)

    def _on_hc_enable(self, row: Adw.SwitchRow, _ps) -> None:
        on = row.get_active()
        if on:
            self._hc_install_unit()
            sh_async(
                ["systemctl", "--user", "enable", "--now",
                 "nyxus-hotcorners.service"],
                lambda r: (
                    self.toast("hot corners enabled") if r[0] == 0
                    else self.toast(
                        f"enable failed: {(r[2] or '')[:60]}"),
                    self._render_hotcorners())[1],
                timeout=8)
        else:
            sh_async(
                ["systemctl", "--user", "disable", "--now",
                 "nyxus-hotcorners.service"],
                lambda r: (self.toast("hot corners disabled"),
                           self._render_hotcorners())[1],
                timeout=6)

    def _on_hc_action(self, corner: str, action: str) -> None:
        cfg = self._hc_read_conf()
        cfg[corner] = action
        if not self._hc_write_conf(cfg):
            return
        # Daemon hot-reloads on conf mtime change (see
        # nyxus_hotcorners.py main loop) so we don't need to restart it.
        self.toast(f"{self.HC_CORNER_LABELS[corner]} · "
                   f"{dict(self.HC_ACTIONS).get(action, action)}")

    # ── Text scale ────────────────────────────────────────────────────
    def _render_scale(self) -> None:
        _clear_group(self.scale_grp)
        prefs = self.win.prefs
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
        self.scale_grp.add(scale_row)

    def _on_font_scale(self, scale: Gtk.Scale) -> None:
        v = round(scale.get_value(), 2)
        self.win.prefs["font_scale"] = v
        save_prefs(self.win.prefs)
        if have("gsettings"):
            sh_async(
                ["gsettings", "set", "org.gnome.desktop.interface",
                 "text-scaling-factor", str(v)],
                lambda r: None, timeout=3)

    # ── Motion ────────────────────────────────────────────────────────
    def _render_motion(self) -> None:
        _clear_group(self.motion_grp)
        prefs = self.win.prefs
        anim_row = Adw.SwitchRow(
            title="Enable Hyprland animations",
            subtitle="Disable for snappier feel on slow GPUs")
        anim_row.set_active(prefs.get("animations", True))
        anim_row.connect("notify::active", self._on_anim_toggle)
        self.motion_grp.add(anim_row)

        reduce_row = Adw.SwitchRow(
            title="Reduce motion (apps)",
            subtitle="gsettings org.gnome.desktop.interface "
                     "enable-animations")
        rc, val, _ = sh(["gsettings", "get",
                         "org.gnome.desktop.interface",
                         "enable-animations"], timeout=2)
        # When animations are *enabled*, reduce-motion is OFF
        currently_anim = "true" in val.lower()
        reduce_row.set_active(not currently_anim)
        reduce_row.connect("notify::active", self._on_reduce_motion)
        self.motion_grp.add(reduce_row)

    def _on_anim_toggle(self, row: Adw.SwitchRow, _pspec) -> None:
        on = row.get_active()
        self.win.prefs["animations"] = on
        save_prefs(self.win.prefs)
        if have("hyprctl"):
            sh_async(["hyprctl", "keyword", "animations:enabled",
                      "1" if on else "0"],
                     lambda r: self.toast(
                         f"animations {'on' if on else 'off'}"))

    def _on_reduce_motion(self, row: Adw.SwitchRow, _pspec) -> None:
        reduce = row.get_active()
        if not have("gsettings"):
            self.toast("gsettings missing")
            return
        sh_async(
            ["gsettings", "set", "org.gnome.desktop.interface",
             "enable-animations", "false" if reduce else "true"],
            lambda r: self.toast(
                f"reduce motion {'on' if reduce else 'off'}"),
            timeout=4)


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

        # ── Mobile hotspot ────────────────────────────────────────────
        self.hotspot_group = Adw.PreferencesGroup(
            title="Mobile hotspot",
            description="Share this machine's connection over Wi-Fi")
        self.add_group(self.hotspot_group)

        # ── Ethernet ──────────────────────────────────────────────────
        self.eth_group = Adw.PreferencesGroup(title="Ethernet")
        self.add_group(self.eth_group)

        # ── VPN ───────────────────────────────────────────────────────
        self.vpn_group = Adw.PreferencesGroup(title="VPN connections")
        self.add_group(self.vpn_group)

        # ── DNS ───────────────────────────────────────────────────────
        self.dns_group = Adw.PreferencesGroup(title="DNS")
        self.add_group(self.dns_group)

        # ── DNS-over-TLS (Tier 2 #13) ─────────────────────────────────
        self.doh_group = Adw.PreferencesGroup(
            title="Encrypted DNS",
            description="Tunnel DNS lookups through TLS via systemd-"
                        "resolved (drop-in at /etc/systemd/resolved."
                        "conf.d/nyxus-doh.conf).")
        self.add_group(self.doh_group)

        # ── Proxy (Tier 2 #12) ────────────────────────────────────────
        self.proxy_group = Adw.PreferencesGroup(
            title="System proxy",
            description="GNOME desktop proxy (org.gnome.system.proxy). "
                        "Apps that honour libproxy/glib-networking will "
                        "use these settings automatically.")
        self.add_group(self.proxy_group)

        # ── Firewall surface (Tier 2 #14) ─────────────────────────────
        self.fw_group = Adw.PreferencesGroup(
            title="Firewall",
            description="Mirror of the UFW rule set; managed by the "
                        "Security Center for full editing.")
        self.add_group(self.fw_group)

        # Lazy state holders for proxy/doh combos so we don't fight the
        # user mid-edit. Filled by _render_proxy/_render_doh on first
        # paint and updated only when the live system value diverges.
        self._proxy_mode_lock = False
        self._doh_lock = False

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
        for g in (self.wifi_group, self.hotspot_group, self.eth_group,
                  self.vpn_group, self.dns_group, self.doh_group,
                  self.proxy_group, self.fw_group):
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

        # Mobile hotspot
        self._render_hotspot()

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

        # Tier 2 #13 / #12 / #14
        self._render_doh()
        self._render_proxy()
        self._render_firewall()

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

    # ── Hotspot helpers ───────────────────────────────────────────────
    HOTSPOT_CONN = "Hotspot"

    def _wifi_device(self) -> str:
        rc, dev_out, err = sh("nmcli -t -f DEVICE,TYPE device")
        if rc != 0:
            log.warning("nmcli device enum rc=%d err=%r", rc, err)
            self.toast(f"hotspot device probe failed: "
                       f"{(err or 'see log')[:60]}")
            return ""
        for ln in dev_out.splitlines():
            p = ln.split(":")
            if len(p) >= 2 and p[1] == "wifi":
                return p[0]
        return ""

    def _hotspot_active(self, dev: str) -> bool:
        rc, out, err = sh(["nmcli", "-t", "-f",
                           "NAME,DEVICE,TYPE",
                           "connection", "show", "--active"])
        if rc != 0:
            log.warning("nmcli connection show --active rc=%d err=%r",
                        rc, err)
            self.toast(f"hotspot state probe failed: "
                       f"{(err or 'see log')[:60]}")
            return False
        for ln in out.splitlines():
            p = ln.split(":")
            if len(p) >= 3 and p[1] == dev and p[2] in (
                    "802-11-wireless", "wifi"):
                rc2, mout, _ = sh(["nmcli", "-t", "-f",
                                   "802-11-wireless.mode",
                                   "connection", "show", p[0]])
                if rc2 == 0 and "ap" in mout.lower():
                    return True
        return False

    def _hotspot_creds(self) -> Tuple[str, str]:
        rc, out, err = sh([
            "nmcli", "-s", "-t", "-f",
            "802-11-wireless.ssid,802-11-wireless-security.psk",
            "connection", "show", self.HOTSPOT_CONN])
        ssid, pwd = "", ""
        if rc != 0:
            # Connection may simply not exist yet — that's an expected
            # cold-start state, not a hard failure. Only log; don't
            # toast (would spam on every render before first hotspot).
            log.info("nmcli show %s rc=%d err=%r (likely "
                     "first-run, no Hotspot connection yet)",
                     self.HOTSPOT_CONN, rc, err)
            return ssid, pwd
        for ln in out.splitlines():
            if ln.startswith("802-11-wireless.ssid:"):
                ssid = ln.split(":", 1)[1]
            elif ln.startswith("802-11-wireless-security.psk:"):
                pwd = ln.split(":", 1)[1]
        return ssid, pwd

    def _render_hotspot(self) -> None:
        if not have("nmcli"):
            return
        dev = self._wifi_device()
        if not dev:
            row = Adw.ActionRow(
                title="No Wi-Fi adapter for hotspot",
                subtitle="Plug in a USB Wi-Fi adapter to share Internet "
                         "from Ethernet over Wi-Fi.")
            self._track(self.hotspot_group, row)
            return

        active = self._hotspot_active(dev)
        sw = Adw.SwitchRow(
            title=f"Mobile hotspot on {dev}",
            subtitle="Generates a random SSID + WPA2 password the first "
                     "time it's enabled (saved by NetworkManager).")
        sw.set_active(bool(active))
        sw.connect("notify::active",
                   lambda r, _p, d=dev: self._on_hotspot_toggle(r, d))
        self._track(self.hotspot_group, sw)

        if not active:
            return

        self.add_pill(status_pill("hotspot on", "ok"))
        ssid, pwd = self._hotspot_creds()
        if ssid:
            self._track(self.hotspot_group,
                        Adw.ActionRow(title="SSID", subtitle=ssid))
        if pwd:
            pwd_row = Adw.ActionRow(title="Password", subtitle=pwd)
            cpy = Gtk.Button(label="Copy")
            cpy.set_valign(Gtk.Align.CENTER)
            cpy.connect("clicked",
                        lambda _b, t=pwd: self._copy_hotspot_pw(t))
            pwd_row.add_suffix(cpy)
            self._track(self.hotspot_group, pwd_row)

        rc, sta, _ = sh(["iw", "dev", dev, "station", "dump"],
                        timeout=2)
        n = sta.count("Station ") if rc == 0 else 0
        self._track(self.hotspot_group, Adw.ActionRow(
            title="Connected clients",
            subtitle=f"{n} connected"))

    def _on_hotspot_toggle(self,
                           row: Adw.SwitchRow,
                           dev: str) -> None:
        on = row.get_active()
        if on:
            ssid_existing, pwd_existing = self._hotspot_creds()
            ssid = ssid_existing or f"NYXUS-{secrets.token_hex(2).upper()}"
            pwd = pwd_existing or secrets.token_urlsafe(10)
            sh_async(
                ["nmcli", "device", "wifi", "hotspot",
                 "ifname", dev,
                 "con-name", self.HOTSPOT_CONN,
                 "ssid", ssid,
                 "password", pwd],
                lambda r: (self.toast(
                    f"hotspot up · {ssid}" if r[0] == 0
                    else f"hotspot failed: "
                         f"{(r[2] or 'see log')[:80]}"),
                    self._render()),
                timeout=15)
        else:
            sh_async(
                ["nmcli", "connection", "down", self.HOTSPOT_CONN],
                lambda r: (self.toast(
                    "hotspot stopped" if r[0] == 0
                    else f"stop failed: "
                         f"{(r[2] or 'see log')[:60]}"),
                    self._render()),
                timeout=10)

    def _copy_hotspot_pw(self, pw: str) -> None:
        if have("wl-copy"):
            try:
                proc = subprocess.Popen(
                    ["wl-copy"], stdin=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL)
                proc.communicate(pw.encode("utf-8"), timeout=2)
                self.toast("password copied")
            except (OSError, subprocess.SubprocessError) as e:
                log.warning("wl-copy hotspot pw: %s", e)
                self.toast(f"copy failed: {e}")
        else:
            self.toast("wl-copy not installed — can't copy")

    # ── DoH / Encrypted DNS (Tier 2 #13) ──────────────────────────────
    DOH_DROPIN = Path("/etc/systemd/resolved.conf.d/nyxus-doh.conf")
    DOH_PRESETS = (
        ("off",        "Off — system default", "", ""),
        ("cloudflare", "Cloudflare (1.1.1.1)",
         "1.1.1.1#cloudflare-dns.com 1.0.0.1#cloudflare-dns.com",
         "2606:4700:4700::1111#cloudflare-dns.com"),
        ("quad9",      "Quad9 (9.9.9.9 — malware-blocking)",
         "9.9.9.9#dns.quad9.net 149.112.112.112#dns.quad9.net",
         "2620:fe::fe#dns.quad9.net"),
        ("google",     "Google (8.8.8.8)",
         "8.8.8.8#dns.google 8.8.4.4#dns.google",
         "2001:4860:4860::8888#dns.google"),
    )

    def _doh_current(self) -> Optional[str]:
        """Return preset key currently written into the drop-in.

        Returns 'off' if the file is genuinely absent (FileNotFoundError),
        a real preset key if matched, or None if the file exists but
        couldn't be read — that distinction lets the renderer show a
        degraded-state row instead of falsely reporting 'Off'.
        """
        try:
            txt = self.DOH_DROPIN.read_text(encoding="utf-8")
        except FileNotFoundError:
            return "off"
        except OSError as e:
            log.warning("read %s: %s", self.DOH_DROPIN, e)
            return None
        for key, _label, v4, _v6 in self.DOH_PRESETS:
            if key == "off" or not v4:
                continue
            first_ip = v4.split()[0].split("#")[0]
            if first_ip in txt:
                return key
        return "off"

    def _render_doh(self) -> None:
        if not have("resolvectl"):
            row = Adw.ActionRow(
                title="systemd-resolved not installed",
                subtitle="Install systemd-resolved to enable encrypted "
                         "DNS over TLS.")
            self._track(self.doh_group, row)
            return
        rc, rout, _ = sh(["resolvectl", "status"], timeout=2)
        dot_state = "unknown"
        if rc == 0:
            for ln in rout.splitlines():
                s = ln.strip()
                if s.startswith("DNSOverTLS setting:"):
                    dot_state = s.split(":", 1)[1].strip() or "no"
                    break
            else:
                dot_state = "no"
        cur = self._doh_current()
        if cur is None:
            row = Adw.ActionRow(
                title="Encrypted DNS state unavailable",
                subtitle=f"Could not read {self.DOH_DROPIN} — see "
                         "~/.cache/nyxus/settings.log")
            self._track(self.doh_group, row)
            return
        keys = [p[0] for p in self.DOH_PRESETS]
        labels = [p[1] for p in self.DOH_PRESETS]
        combo = Adw.ComboRow(
            title="Encrypted DNS provider",
            subtitle=f"DNSOverTLS={dot_state}  ·  drop-in: "
                     f"{self.DOH_DROPIN.name}")
        model = Gtk.StringList()
        for lab in labels:
            model.append(lab)
        combo.set_model(model)
        try:
            combo.set_selected(keys.index(cur))
        except ValueError:
            combo.set_selected(0)
        # Disable while an apply is in flight so we cannot enqueue a
        # second pkexec write before the first completes.
        combo.set_sensitive(not self._doh_lock)
        combo.connect("notify::selected", self._on_doh_picked)
        self._track(self.doh_group, combo)
        if dot_state in ("yes", "opportunistic"):
            self.add_pill(status_pill("doh on", "ok"))

    def _on_doh_picked(self, combo: Adw.ComboRow, _pspec) -> None:
        # Hard lock: even if a stale signal slips through after the
        # widget is desensitised, refuse to enqueue a second writer.
        if self._doh_lock:
            return
        idx = int(combo.get_selected())
        if idx < 0 or idx >= len(self.DOH_PRESETS):
            return
        key, label, v4, v6 = self.DOH_PRESETS[idx]
        if key == "off":
            cmd = ["pkexec", "sh", "-c",
                   f"rm -f {shlex.quote(str(self.DOH_DROPIN))} && "
                   "systemctl restart systemd-resolved"]
        else:
            body = (
                "# Written by nyxus_settings — Encrypted DNS preset: "
                f"{key}\n"
                "[Resolve]\n"
                f"DNS={v4}\n"
                f"FallbackDNS={v6}\n"
                "DNSOverTLS=yes\n"
                "DNSSEC=allow-downgrade\n"
                "Cache=yes\n")
            cmd = ["pkexec", "sh", "-c",
                   f"mkdir -p {shlex.quote(str(self.DOH_DROPIN.parent))} && "
                   f"printf %s {shlex.quote(body)} > "
                   f"{shlex.quote(str(self.DOH_DROPIN))} && "
                   "systemctl restart systemd-resolved"]
        self._doh_lock = True

        def done(r):
            self._doh_lock = False
            if r[0] == 0:
                self.toast(f"DNS · {label}")
            else:
                self.toast(f"DoH apply failed: {(r[2] or 'see log')[:80]}")
                log.warning("DoH apply rc=%d err=%s", r[0], r[2])
            self._render()
        sh_async(cmd, done, timeout=12)

    # ── System proxy (Tier 2 #12) ─────────────────────────────────────
    PROXY_MODES = ("none", "manual", "auto")
    PROXY_MODE_LABELS = ("Off", "Manual host:port", "Automatic (PAC URL)")
    PROXY_PROTOS = ("http", "https", "ftp", "socks")

    def _gset_get(self, schema: str, key: str) -> Optional[str]:
        """Return the gsettings string value, or None on read failure.

        Empty-string is a legitimate value (e.g. cleared host); failure
        must be distinguishable so the renderer can show an honest
        degraded-state row instead of pretending the value is empty.
        """
        rc, out, err = sh(["gsettings", "get", schema, key], timeout=2)
        if rc != 0:
            log.warning("gsettings get %s %s rc=%d err=%r",
                        schema, key, rc, err)
            return None
        return out.strip().strip("'").strip('"')

    def _proxy_mode(self) -> Optional[str]:
        m = self._gset_get("org.gnome.system.proxy", "mode")
        if m is None:
            return None
        return m if m in self.PROXY_MODES else "none"

    def _proxy_field(self, proto: str) -> Tuple[str, int]:
        host = self._gset_get(f"org.gnome.system.proxy.{proto}", "host")
        port_raw = self._gset_get(
            f"org.gnome.system.proxy.{proto}", "port")
        # Treat read failures as empty for individual field rendering;
        # the mode-level read already gates whether we even render
        # these rows, so a per-field failure here is non-fatal.
        if host is None:
            host = ""
        try:
            port = int(port_raw or "0")
        except (ValueError, TypeError):
            port = 0
        return host, port

    def _render_proxy(self) -> None:
        if not have("gsettings"):
            row = Adw.ActionRow(
                title="gsettings not installed",
                subtitle="Install glib2 / dconf to manage the system "
                         "proxy.")
            self._track(self.proxy_group, row)
            return
        mode = self._proxy_mode()
        if mode is None:
            row = Adw.ActionRow(
                title="Proxy state unavailable",
                subtitle="Could not read org.gnome.system.proxy — see "
                         "~/.cache/nyxus/settings.log")
            self._track(self.proxy_group, row)
            return
        combo = Adw.ComboRow(
            title="Proxy mode",
            subtitle="Off · Manual host/port · Automatic PAC URL")
        model = Gtk.StringList()
        for lab in self.PROXY_MODE_LABELS:
            model.append(lab)
        combo.set_model(model)
        try:
            combo.set_selected(self.PROXY_MODES.index(mode))
        except ValueError:
            combo.set_selected(0)
        # Same belt-and-braces approach as DoH: desensitise the widget
        # while an apply is in flight, then refuse stale signals in the
        # handler itself (see _on_proxy_mode).
        combo.set_sensitive(not self._proxy_mode_lock)
        combo.connect("notify::selected", self._on_proxy_mode)
        self._track(self.proxy_group, combo)

        if mode == "manual":
            for proto in self.PROXY_PROTOS:
                host, port = self._proxy_field(proto)
                ent = Adw.EntryRow(title=proto.upper())
                ent.set_text(f"{host}:{port}" if host else "")
                btn = Gtk.Button(label="Apply")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect(
                    "clicked",
                    lambda _b, p=proto, e=ent:
                        self._apply_proxy_field(p, e))
                ent.add_suffix(btn)
                self._track(self.proxy_group, ent)
            self.add_pill(status_pill("proxy manual", "ok"))
        elif mode == "auto":
            url = self._gset_get("org.gnome.system.proxy",
                                 "autoconfig-url") or ""
            ent = Adw.EntryRow(title="PAC URL")
            ent.set_text(url)
            btn = Gtk.Button(label="Apply")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked",
                        lambda _b, e=ent: self._apply_proxy_pac(e))
            ent.add_suffix(btn)
            self._track(self.proxy_group, ent)
            self.add_pill(status_pill("proxy auto", "ok"))

    def _on_proxy_mode(self, combo: Adw.ComboRow, _pspec) -> None:
        # Hard lock first — drop any stale signal that may have slipped
        # through before the widget was desensitised on the next render.
        if self._proxy_mode_lock:
            return
        idx = int(combo.get_selected())
        if idx < 0 or idx >= len(self.PROXY_MODES):
            return
        mode = self.PROXY_MODES[idx]
        self._proxy_mode_lock = True
        combo.set_sensitive(False)

        def done(r):
            self._proxy_mode_lock = False
            if r[0] == 0:
                self.toast(f"proxy · {self.PROXY_MODE_LABELS[idx]}")
            else:
                self.toast(f"proxy mode failed: "
                           f"{(r[2] or 'see log')[:60]}")
                log.warning("gsettings set proxy mode rc=%d err=%s",
                            r[0], r[2])
            self._render()
        sh_async(
            ["gsettings", "set", "org.gnome.system.proxy", "mode", mode],
            done, timeout=4)

    def _apply_proxy_field(self, proto: str,
                           entry: Adw.EntryRow) -> None:
        text = entry.get_text().strip()
        host, port = "", 0
        if text:
            if ":" not in text:
                self.toast(f"{proto.upper()}: use host:port "
                           "(e.g. proxy.local:8080)")
                return
            h, _, p = text.rpartition(":")
            host = h.strip()
            try:
                port = int(p.strip())
            except ValueError:
                self.toast(f"{proto.upper()}: port must be a number")
                return
            if not (1 <= port <= 65535):
                self.toast(f"{proto.upper()}: port out of range "
                           "(1–65535)")
                return
        schema = f"org.gnome.system.proxy.{proto}"

        def step2(r1):
            if r1[0] != 0:
                self.toast(f"{proto.upper()} host failed: "
                           f"{(r1[2] or 'see log')[:60]}")
                log.warning("gsettings set %s host rc=%d err=%s",
                            schema, r1[0], r1[2])
                return

            def done(r2):
                if r2[0] == 0:
                    self.toast(f"{proto.upper()} → {host}:{port}"
                               if host
                               else f"{proto.upper()} cleared")
                else:
                    self.toast(f"{proto.upper()} port failed: "
                               f"{(r2[2] or 'see log')[:60]}")
                    log.warning("gsettings set %s port rc=%d err=%s",
                                schema, r2[0], r2[2])
                self._render()
            sh_async(["gsettings", "set", schema, "port", str(port)],
                     done, timeout=4)
        sh_async(["gsettings", "set", schema, "host", host],
                 step2, timeout=4)

    def _apply_proxy_pac(self, entry: Adw.EntryRow) -> None:
        url = entry.get_text().strip()

        def done(r):
            if r[0] == 0:
                self.toast(f"PAC → {url}" if url else "PAC cleared")
            else:
                self.toast(f"PAC apply failed: "
                           f"{(r[2] or 'see log')[:60]}")
                log.warning("gsettings set autoconfig-url rc=%d err=%s",
                            r[0], r[2])
            self._render()
        sh_async(["gsettings", "set", "org.gnome.system.proxy",
                  "autoconfig-url", url], done, timeout=4)

    # ── Firewall surface (Tier 2 #14) ─────────────────────────────────
    def _render_firewall(self) -> None:
        if not have("ufw"):
            row = Adw.ActionRow(
                title="ufw not installed",
                subtitle="Install ufw, or use the full firewall stack "
                         "in the Security Center.")
            btn = Gtk.Button(label="Open Security Center")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect(
                "clicked",
                lambda *_: fire_and_forget("nyxus-security"))
            row.add_suffix(btn)
            self._track(self.fw_group, row)
            return

        # ufw status normally needs root; if our user can read it
        # passwordless via polkit/sudoers we'll see it, otherwise
        # rc!=0 and we degrade to a safe summary.
        rc, sout, err = sh(["ufw", "status", "verbose"], timeout=3)
        if rc == 0:
            active = "Status: active" in sout
            deny_in = "deny (incoming" in sout
            sw = Adw.SwitchRow(
                title="UFW firewall",
                subtitle=("active · deny inbound"
                          if (active and deny_in)
                          else "active · permissive"
                          if active
                          else "inactive"))
            sw.set_active(active)
            sw.connect("notify::active", self._on_fw_toggle)
            self._track(self.fw_group, sw)

            if active:
                n_rules = sum(
                    1 for ln in sout.splitlines()
                    if (" ALLOW " in ln or " DENY " in ln
                        or " REJECT " in ln or " LIMIT " in ln))
                self._track(self.fw_group, Adw.ActionRow(
                    title="Active rules",
                    subtitle=f"{n_rules} rule(s) — open Security "
                             "Center to edit"))
            self.add_pill(status_pill(
                "fw on" if active else "fw off",
                "ok" if active else "warn"))
        else:
            # Read denied — surface honestly instead of pretending.
            log.info("ufw status rc=%d err=%r (likely needs polkit)",
                     rc, err)
            row = Adw.ActionRow(
                title="UFW status unavailable",
                subtitle="Toggle requires admin authentication; open "
                         "Security Center for the full firewall view.")
            self._track(self.fw_group, row)

        # Always offer the deep link.
        link = Adw.ActionRow(
            title="Open Security Center",
            subtitle="Edit rules, profiles, and view live blocks")
        btn = Gtk.Button(label="Open")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked",
                    lambda *_: fire_and_forget("nyxus-security"))
        link.add_suffix(btn)
        self._track(self.fw_group, link)

    def _on_fw_toggle(self, row: Adw.SwitchRow, _pspec) -> None:
        on = row.get_active()
        cmd = ["pkexec", "ufw", "enable" if on else "disable"]

        def done(r):
            if r[0] == 0:
                self.toast(f"firewall {'enabled' if on else 'disabled'}")
            else:
                self.toast(f"firewall toggle failed: "
                           f"{(r[2] or 'see log')[:60]}")
                log.warning("ufw toggle rc=%d err=%s", r[0], r[2])
            self._render()
        sh_async(cmd, done, timeout=10)


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
class PrintersPage(SectionPage):
    """Printers & Scanners — CUPS-backed queue manager.

    Reads via lpstat / lpinfo, writes via lpadmin + cupsenable/cupsdisable
    behind pkexec. Service status pill mirrors cups.service.
    """
    KEY = "printers"

    def build(self) -> None:
        if not have("lpstat"):
            grp = Adw.PreferencesGroup(title="CUPS not installed")
            grp.add(empty_row(
                "Printing tools missing",
                "Install cups + cups-pk-helper to manage printers."))
            self.add_group(grp)
            self.add_pill(status_pill("cups missing", "danger"))
            return

        self.svc_grp = Adw.PreferencesGroup(title="Print service")
        self.add_group(self.svc_grp)

        self.dev_grp = Adw.PreferencesGroup(
            title="Printers",
            description="Configured CUPS print queues")
        self.add_group(self.dev_grp)

        tools = Adw.PreferencesGroup(title="Tools")
        self.add_group(tools)
        if have("system-config-printer"):
            tools.add(action_row(
                "Add a printer",
                "Open the system printer configuration dialog",
                "Open",
                lambda: subprocess.Popen(["system-config-printer"])))
        tools.add(action_row(
            "Open CUPS web admin",
            "http://localhost:631 (browser)",
            "Open",
            lambda: subprocess.Popen(["xdg-open",
                                      "http://localhost:631"])))

        self._render()
        self.schedule_refresh(8000, self._tick)

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
        for g in (self.svc_grp, self.dev_grp):
            self._clear(g)
        self.clear_pills()

        _, svc, _ = sh("systemctl is-active cups.service")
        active = svc.strip() == "active"

        if active:
            self.add_pill(status_pill("on", "ok"))
        else:
            self.add_pill(status_pill("service off", "warn"))

        svc_row = Adw.ActionRow(
            title="cups.service",
            subtitle="active" if active
            else "inactive — print queue offline")
        verb = "stop" if active else "start"
        btn = Gtk.Button(label="Stop" if active else "Start")
        if not active:
            btn.add_css_class("nyx-primary")
        btn.set_valign(Gtk.Align.CENTER)
        btn.connect("clicked", lambda _b: sh_async(
            f"pkexec systemctl {verb} cups.service",
            lambda r: (self.toast(
                f"cups {verb}ed" if r[0] == 0
                else "auth required or failed"),
                self._render())))
        svc_row.add_suffix(btn)
        self._track(self.svc_grp, svc_row)

        if not active:
            row = empty_row(
                "No queues available",
                "Start cups.service to manage printers.")
            self._track(self.dev_grp, row)
            return

        # Default printer
        _, def_out, _ = sh("lpstat -d")
        default = ""
        if ":" in def_out:
            tail = def_out.split(":", 1)[1].strip()
            if not tail.lower().startswith("no system"):
                default = tail

        # Queue list
        _, plist, _ = sh("lpstat -p")
        if not plist.strip():
            row = empty_row(
                "No printers configured",
                "Click 'Add a printer' to set one up.")
            self._track(self.dev_grp, row)
            return

        for line in plist.splitlines():
            if not line.startswith("printer "):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            name = parts[1]
            if "is idle" in line:
                state = "idle"
            elif "now printing" in line:
                state = "printing"
            elif "disabled" in line:
                state = "stopped"
            else:
                state = "?"
            is_default = (name == default)
            sub_bits = [state]
            if is_default:
                sub_bits.append("default")
            row = Adw.ActionRow(title=name,
                                subtitle=" · ".join(sub_bits))

            if not is_default:
                d = Gtk.Button(label="Set default")
                d.set_valign(Gtk.Align.CENTER)
                d.connect("clicked", lambda _b, n=name: sh_async(
                    f"pkexec lpadmin -d {shlex.quote(n)}",
                    lambda r, nm=n: (self.toast(
                        f"default → {nm}" if r[0] == 0
                        else "auth required or failed"),
                        self._render())))
                row.add_suffix(d)

            t = Gtk.Button(label="Test")
            t.set_valign(Gtk.Align.CENTER)
            t.connect("clicked", lambda _b, n=name: sh_async(
                f"lp -d {shlex.quote(n)} "
                f"/usr/share/cups/data/testprint",
                lambda r: self.toast(
                    "test page sent" if r[0] == 0
                    else "send failed — check queue")))
            row.add_suffix(t)

            paused = (state == "stopped")
            cmd = "cupsenable" if paused else "cupsdisable"
            p = Gtk.Button(label="Resume" if paused else "Pause")
            p.set_valign(Gtk.Align.CENTER)
            p.connect("clicked", lambda _b, n=name, c=cmd: sh_async(
                f"pkexec {c} {shlex.quote(n)}",
                lambda r, nm=n, was_paused=paused: (self.toast(
                    f"{nm} {'resumed' if was_paused else 'paused'}"
                    if r[0] == 0 else "auth required or failed"),
                    self._render())))
            row.add_suffix(p)

            x = Gtk.Button(label="Remove")
            x.add_css_class("destructive-action")
            x.set_valign(Gtk.Align.CENTER)
            x.connect("clicked", lambda _b, n=name: sh_async(
                f"pkexec lpadmin -x {shlex.quote(n)}",
                lambda r, nm=n: (self.toast(
                    f"removed {nm}" if r[0] == 0
                    else "auth required or failed"),
                    self._render())))
            row.add_suffix(x)

            self._track(self.dev_grp, row)


class CamerasMicsPage(SectionPage):
    """Camera & Microphone — enumerates capture devices and offers
    real, non-mock test launchers (cheese, pavucontrol level meter,
    pw-cli mic check). Reads /dev/video*, v4l2-ctl, pactl/pw-cli.
    No persistence required — purely a discovery + test surface."""
    KEY = "cameras_mics"

    def build(self) -> None:
        self.cam_grp = Adw.PreferencesGroup(
            title="Cameras",
            description="Video capture devices reported by the kernel "
                        "(/dev/video*) — names from v4l2-ctl when present")
        self.add_group(self.cam_grp)

        self.mic_grp = Adw.PreferencesGroup(
            title="Microphones",
            description="Audio sources reported by PipeWire / PulseAudio")
        self.add_group(self.mic_grp)

        tools = Adw.PreferencesGroup(title="Tests")
        self.add_group(tools)
        if have("cheese"):
            tools.add(action_row(
                "Open Camera viewer",
                "Live preview using cheese",
                "Open",
                lambda: subprocess.Popen(["cheese"])))
        elif have("guvcview"):
            tools.add(action_row(
                "Open Camera viewer",
                "Live preview using guvcview",
                "Open",
                lambda: subprocess.Popen(["guvcview"])))
        else:
            tools.add(empty_row(
                "No camera viewer installed",
                "Install 'cheese' or 'guvcview' to preview cameras."))
        if have("pavucontrol"):
            tools.add(action_row(
                "Open Audio mixer (level meters)",
                "Watch microphone input levels in pavucontrol",
                "Open",
                lambda: subprocess.Popen(["pavucontrol", "-t", "4"])))

        self._render()
        self.schedule_refresh(8000, self._tick)

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
        for g in (self.cam_grp, self.mic_grp):
            self._clear(g)
        self.clear_pills()

        # Cameras
        try:
            vids = sorted(p for p in os.listdir("/dev")
                          if p.startswith("video") and p[5:].isdigit())
        except FileNotFoundError:
            vids = []
        cam_count = 0
        for node in vids:
            path = f"/dev/{node}"
            name = node
            if have("v4l2-ctl"):
                rc, out, _ = sh(["v4l2-ctl", "-d", path,
                                 "--info"], timeout=2)
                for ln in (out or "").splitlines():
                    if "Card type" in ln:
                        name = ln.split(":", 1)[1].strip() or name
                        break
            row = Adw.ActionRow(title=name, subtitle=path)
            self._track(self.cam_grp, row)
            cam_count += 1
        if cam_count == 0:
            self._track(self.cam_grp,
                        empty_row("No cameras detected",
                                  "Plug in a webcam to see it here."))

        # Microphones — prefer pw-cli if present, fall back to pactl
        mic_count = 0
        if have("pactl"):
            rc, out, _ = sh(["pactl", "list", "short", "sources"],
                            timeout=3)
            for ln in (out or "").splitlines():
                parts = ln.split()
                if len(parts) < 2:
                    continue
                name = parts[1]
                # Skip monitor sources (loopback of outputs)
                if name.endswith(".monitor"):
                    continue
                row = Adw.ActionRow(title=name.split(".")[-1] or name,
                                    subtitle=name)
                self._track(self.mic_grp, row)
                mic_count += 1
        if mic_count == 0:
            self._track(self.mic_grp,
                        empty_row("No microphones detected",
                                  "Connect a mic or check audio service."))

        if cam_count + mic_count > 0:
            self.add_pill(status_pill(
                f"{cam_count} cam · {mic_count} mic", "ok"))
        else:
            self.add_pill(status_pill("none", "warn"))


class ControllersPage(SectionPage):
    """Game Controllers — enumerates joystick devices (/dev/input/js*),
    surfaces evtest/jstest as real test launchers, and links to the
    in-browser HTML5 gamepad tester for users without those CLI tools.
    Read-only by design — controllers self-configure via udev."""
    KEY = "controllers"

    def build(self) -> None:
        self.dev_grp = Adw.PreferencesGroup(
            title="Connected controllers",
            description="Joystick / gamepad devices reported by the kernel")
        self.add_group(self.dev_grp)

        tools = Adw.PreferencesGroup(title="Tests")
        self.add_group(tools)
        if have("jstest-gtk"):
            tools.add(action_row(
                "Open jstest-gtk",
                "Graphical joystick test tool",
                "Open",
                lambda: subprocess.Popen(["jstest-gtk"])))
        elif have("jstest"):
            tools.add(action_row(
                "Test in terminal (jstest)",
                "Live axis & button readout",
                "Open",
                lambda: open_terminal(
                    "jstest /dev/input/js0 || (echo 'no js0'; read _)",
                    self.win)))
        if have("evtest"):
            tools.add(action_row(
                "Test in terminal (evtest)",
                "Pick a /dev/input/event* node and watch events",
                "Open",
                lambda: open_terminal("evtest; read _", self.win)))
        tools.add(action_row(
            "Open browser gamepad tester",
            "https://hardwaretester.com/gamepad",
            "Open",
            lambda: subprocess.Popen(
                ["xdg-open", "https://hardwaretester.com/gamepad"])))

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
        self._clear(self.dev_grp)
        self.clear_pills()

        try:
            js_nodes = sorted(
                p for p in os.listdir("/dev/input")
                if p.startswith("js") and p[2:].isdigit())
        except FileNotFoundError:
            js_nodes = []

        if not js_nodes:
            self._track(self.dev_grp, empty_row(
                "No controllers connected",
                "Plug in a gamepad — it should appear here within a few "
                "seconds."))
            self.add_pill(status_pill("none", "warn"))
            return

        for node in js_nodes:
            name = node
            sysname_path = f"/sys/class/input/{node}/device/name"
            try:
                with open(sysname_path, "r", encoding="utf-8") as fh:
                    n = fh.read().strip()
                    if n:
                        name = n
            except OSError:
                pass
            row = Adw.ActionRow(title=name,
                                subtitle=f"/dev/input/{node}")
            self._track(self.dev_grp, row)

        self.add_pill(status_pill(f"{len(js_nodes)} connected", "ok"))


class AboutPage(SectionPage):
    """Branded system summary. All real reads:
      · /etc/os-release · /etc/nyxus-release · /proc/cpuinfo · /proc/meminfo
      · hostnamectl · uname · uptime -p
      · ip -4/-6/link · ip route (default route → primary IP/MAC)
      · bootctl status / efibootmgr / ls /sys/firmware/efi
      · readlink /proc/1/exe → init system
      · $XDG_SESSION_TYPE  $XDG_CURRENT_DESKTOP
      · lspci -nn (GPU)  ·  df -h / (root disk)
    Plus: branded header, Copy Report, jump to Updates."""
    KEY = "about"

    def build(self) -> None:
        self._reset_groups()
        self._render()

    def _reset_groups(self) -> None:
        # NYXUS branded header
        self.brand_grp = Adw.PreferencesGroup()
        self.add_group(self.brand_grp)
        # System
        self.sys_grp = Adw.PreferencesGroup(title="System")
        self.add_group(self.sys_grp)
        # Hardware
        self.hw_grp = Adw.PreferencesGroup(title="Hardware")
        self.add_group(self.hw_grp)
        # Network
        self.net_grp = Adw.PreferencesGroup(
            title="Network",
            description="Primary route (where default traffic goes)")
        self.add_group(self.net_grp)
        # Boot / session
        self.boot_grp = Adw.PreferencesGroup(
            title="Boot &amp; session",
            description="Firmware, bootloader, init, and session type")
        self.add_group(self.boot_grp)
        # Actions
        self.actions_grp = Adw.PreferencesGroup(title="Support")
        self.add_group(self.actions_grp)
        # Credits
        self.credits_grp = Adw.PreferencesGroup(title="NYXUS")
        self.add_group(self.credits_grp)

    def _render(self) -> None:
        # Brand header
        _clear_group(self.brand_grp)
        nyx_ver = self._read_nyx_version()
        header = Adw.ActionRow()
        header.set_title("NYXUS")
        header.set_subtitle(f"DARK MIRROR  ·  {nyx_ver}")
        big = Gtk.Label(label="◐")
        big.add_css_class("nyx-section-glyph")
        big.set_valign(Gtk.Align.CENTER)
        header.add_prefix(big)
        header.add_suffix(status_pill(nyx_ver, "ok"))
        self.brand_grp.add(header)

        # System
        _clear_group(self.sys_grp)
        _, host, _ = sh("hostnamectl --static")
        _, ker, _  = sh(["uname", "-r"])
        _, up, _   = sh(["uptime", "-p"])
        os_info = self._os_release()
        for title, value in (
            ("Distribution",  os_info.get("PRETTY_NAME", "(n/a)")),
            ("NYXUS version", nyx_ver),
            ("Build ID",      os_info.get("BUILD_ID", "(n/a)")),
            ("Variant",       os_info.get("VARIANT", "(n/a)")),
            ("Hostname",      host.strip() or "(unset)"),
            ("Kernel",        ker.strip() or "(unknown)"),
            ("Architecture",  os.uname().machine),
            ("Uptime",        up.strip() or "(unknown)"),
        ):
            r = Adw.ActionRow(title=title)
            r.add_suffix(self._mono(value))
            self.sys_grp.add(r)

        # Hardware
        _clear_group(self.hw_grp)
        for title, value in (
            ("Processor", self._cpu_model()),
            ("CPU cores", self._cpu_cores()),
            ("Memory",    self._ram_total()),
            ("Graphics",  self._gpu_model()),
            ("Root disk", self._root_disk()),
        ):
            r = Adw.ActionRow(title=title)
            r.add_suffix(self._mono(value))
            self.hw_grp.add(r)

        # Network
        _clear_group(self.net_grp)
        iface, ipv4, mac, gateway = self._primary_route()
        ipv6 = self._primary_ipv6(iface)
        if iface:
            for title, value in (
                ("Interface",    iface),
                ("IPv4 address", ipv4 or "(none)"),
                ("IPv6 address", ipv6 or "(none)"),
                ("MAC address",  mac or "(unknown)"),
                ("Gateway",      gateway or "(none)"),
            ):
                r = Adw.ActionRow(title=title)
                r.add_suffix(self._mono(value))
                self.net_grp.add(r)
        else:
            self.net_grp.add(empty_row(
                "No active network",
                "No default route detected — connect to a network first"))

        # Boot & session
        _clear_group(self.boot_grp)
        for title, value in (
            ("Firmware",     self._firmware()),
            ("Bootloader",   self._bootloader()),
            ("Init system",  self._init_system()),
            ("Session type", os.environ.get("XDG_SESSION_TYPE", "(unknown)")),
            ("Desktop",      os.environ.get("XDG_CURRENT_DESKTOP",
                                            "Hyprland")),
            ("Display",      os.environ.get("WAYLAND_DISPLAY",
                                            os.environ.get("DISPLAY",
                                                           "(none)"))),
        ):
            r = Adw.ActionRow(title=title)
            r.add_suffix(self._mono(value))
            self.boot_grp.add(r)

        # Actions
        _clear_group(self.actions_grp)
        self.actions_grp.add(action_row(
            "Copy system report",
            "Copies a full plain-text report to the clipboard for support",
            "Copy",
            self._copy_report))
        self.actions_grp.add(action_row(
            "Check for updates",
            "Opens the Updates section",
            "Open",
            lambda: self._jump_to("updates")))
        self.actions_grp.add(action_row(
            "Open documentation",
            "Launches the NYXUS handbook",
            "Open",
            lambda: sh_async(
                ["xdg-open", "https://nyxus.io/docs"],
                lambda r: None, timeout=5)))

        # Credits
        _clear_group(self.credits_grp)
        cr = Adw.ActionRow(
            title="Designed and built by Joseph Sierengowski",
            subtitle="© 2026  ·  DARK MIRROR aesthetic  ·  enterprise grade")
        self.credits_grp.add(cr)

        self.clear_pills()
        self.add_pill(status_pill(APP_REV, "ok"))

    # ── Helpers ───────────────────────────────────────────────────────
    @staticmethod
    def _mono(text: str) -> Gtk.Label:
        lbl = Gtk.Label(label=text)
        lbl.add_css_class("nyx-pill")
        lbl.set_selectable(True)
        return lbl

    @staticmethod
    def _os_release() -> dict:
        info: dict = {}
        try:
            for ln in Path("/etc/os-release").read_text().splitlines():
                if "=" in ln:
                    k, v = ln.split("=", 1)
                    info[k] = v.strip().strip('"')
        except Exception:
            pass
        return info

    @staticmethod
    def _read_nyx_version() -> str:
        for p in (Path("/etc/nyxus-release"), Path("/etc/os-release")):
            if not p.exists():
                continue
            try:
                for ln in p.read_text().splitlines():
                    if ln.startswith("NYXUS_VERSION="):
                        return ln.split("=", 1)[1].strip().strip('"')
            except Exception:
                continue
        return APP_REV

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
    def _cpu_cores() -> str:
        try:
            cores = sum(1 for ln in Path("/proc/cpuinfo")
                        .read_text().splitlines()
                        if ln.startswith("processor"))
            return f"{cores} threads"
        except Exception:
            return "(unknown)"

    @staticmethod
    def _ram_total() -> str:
        try:
            for ln in Path("/proc/meminfo").read_text().splitlines():
                if ln.startswith("MemTotal:"):
                    kb = int(ln.split()[1])
                    return f"{kb / 1024 / 1024:.1f} GiB"
        except Exception:
            pass
        return "(unknown)"

    @staticmethod
    def _gpu_model() -> str:
        if not have("lspci"):
            return "(lspci missing)"
        _, out, _ = sh(["lspci", "-nn"])
        gpus = []
        for ln in out.splitlines():
            if any(k in ln for k in ("VGA", "3D controller",
                                     "Display controller")):
                if ":" in ln:
                    gpus.append(ln.split(":", 2)[-1].strip())
        return "  ·  ".join(gpus) if gpus else "(unknown)"

    @staticmethod
    def _root_disk() -> str:
        _, out, _ = sh(["df", "-h", "/"])
        lines = out.strip().splitlines()
        if len(lines) >= 2:
            p = lines[1].split()
            if len(p) >= 5:
                return f"{p[2]} used of {p[1]}  ({p[4]} full)"
        return "(unknown)"

    @staticmethod
    def _primary_route() -> Tuple[str, str, str, str]:
        """Return (iface, ipv4, mac, gateway) for the default route."""
        if not have("ip"):
            return ("", "", "", "")
        _, route, _ = sh(["ip", "-4", "route", "show", "default"])
        iface = ""
        gw = ""
        for tok in route.split():
            if tok == "dev":
                pass
        parts = route.split()
        for i, tok in enumerate(parts):
            if tok == "dev" and i + 1 < len(parts):
                iface = parts[i + 1]
            if tok == "via" and i + 1 < len(parts):
                gw = parts[i + 1]
        if not iface:
            return ("", "", "", "")
        # IPv4 of that interface
        _, ipo, _ = sh(["ip", "-4", "-o", "addr", "show", "dev", iface])
        ipv4 = ""
        for ln in ipo.splitlines():
            m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", ln)
            if m:
                ipv4 = m.group(1)
                break
        # MAC of that interface
        _, lk, _ = sh(["ip", "-o", "link", "show", "dev", iface])
        mac = ""
        m = re.search(r"link/\w+\s+([0-9a-f:]{17})", lk)
        if m:
            mac = m.group(1)
        return (iface, ipv4, mac, gw)

    @staticmethod
    def _primary_ipv6(iface: str) -> str:
        if not iface or not have("ip"):
            return ""
        _, ipo, _ = sh(["ip", "-6", "-o", "addr", "show", "dev",
                        iface, "scope", "global"])
        for ln in ipo.splitlines():
            m = re.search(r"inet6\s+([0-9a-f:]+)", ln)
            if m:
                return m.group(1)
        return ""

    @staticmethod
    def _firmware() -> str:
        if Path("/sys/firmware/efi").exists():
            return "UEFI"
        return "Legacy BIOS"

    @staticmethod
    def _bootloader() -> str:
        # systemd-boot first
        if have("bootctl"):
            _, out, _ = sh(["bootctl", "status"], timeout=2)
            for ln in out.splitlines():
                ln = ln.strip()
                if ln.lower().startswith("product:"):
                    return ln.split(":", 1)[1].strip()
        # GRUB
        for p in (Path("/boot/grub/grub.cfg"),
                  Path("/boot/grub2/grub.cfg")):
            if p.exists():
                return "GRUB"
        # rEFInd
        if Path("/boot/EFI/refind").exists() or \
           Path("/boot/efi/EFI/refind").exists():
            return "rEFInd"
        # systemd-boot (loader entries present)
        if Path("/boot/loader/entries").exists():
            return "systemd-boot"
        return "(unknown)"

    @staticmethod
    def _init_system() -> str:
        try:
            tgt = os.readlink("/proc/1/exe")
            base = os.path.basename(tgt)
            if "systemd" in tgt:
                _, ver, _ = sh(["systemctl", "--version"], timeout=2)
                first = ver.splitlines()[0] if ver else "systemd"
                return first.strip()
            return base
        except Exception:
            return "(unknown)"

    # ── Actions ───────────────────────────────────────────────────────
    def _build_report(self) -> str:
        nyx_ver = self._read_nyx_version()
        os_info = self._os_release()
        _, host, _ = sh("hostnamectl --static")
        _, ker, _  = sh(["uname", "-r"])
        _, up, _   = sh(["uptime", "-p"])
        iface, ipv4, mac, gw = self._primary_route()
        ipv6 = self._primary_ipv6(iface)
        lines = [
            "═══════════════════════════════════════════════",
            f"  NYXUS SYSTEM REPORT  ·  {datetime.now():%Y-%m-%d %H:%M}",
            "═══════════════════════════════════════════════",
            "",
            "[ System ]",
            f"  Distribution : {os_info.get('PRETTY_NAME', '(n/a)')}",
            f"  NYXUS        : {nyx_ver}",
            f"  Build ID     : {os_info.get('BUILD_ID', '(n/a)')}",
            f"  Variant      : {os_info.get('VARIANT', '(n/a)')}",
            f"  Hostname     : {host.strip() or '(unset)'}",
            f"  Kernel       : {ker.strip() or '(unknown)'}",
            f"  Architecture : {os.uname().machine}",
            f"  Uptime       : {up.strip() or '(unknown)'}",
            "",
            "[ Hardware ]",
            f"  CPU          : {self._cpu_model()}",
            f"  Cores        : {self._cpu_cores()}",
            f"  RAM          : {self._ram_total()}",
            f"  GPU          : {self._gpu_model()}",
            f"  Root disk    : {self._root_disk()}",
            "",
            "[ Network ]",
            f"  Interface    : {iface or '(none)'}",
            f"  IPv4         : {ipv4 or '(none)'}",
            f"  IPv6         : {ipv6 or '(none)'}",
            f"  MAC          : {mac or '(unknown)'}",
            f"  Gateway      : {gw or '(none)'}",
            "",
            "[ Boot & session ]",
            f"  Firmware     : {self._firmware()}",
            f"  Bootloader   : {self._bootloader()}",
            f"  Init         : {self._init_system()}",
            f"  Session      : {os.environ.get('XDG_SESSION_TYPE', '?')}",
            f"  Desktop      : {os.environ.get('XDG_CURRENT_DESKTOP', 'Hyprland')}",
            "",
            "═══════════════════════════════════════════════",
        ]
        return "\n".join(lines)

    def _copy_report(self) -> None:
        report = self._build_report()
        try:
            disp = Gdk.Display.get_default()
            cb = disp.get_clipboard()
            cb.set(report)
            self.toast(f"copied {len(report)} chars to clipboard")
        except Exception as e:
            # Fallback: wl-copy / xclip
            if have("wl-copy"):
                p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                p.communicate(report.encode())
                self.toast("copied via wl-copy")
            elif have("xclip"):
                p = subprocess.Popen(
                    ["xclip", "-selection", "clipboard"],
                    stdin=subprocess.PIPE)
                p.communicate(report.encode())
                self.toast("copied via xclip")
            else:
                self.toast(f"clipboard failed: {e}")

    def _jump_to(self, key: str) -> None:
        try:
            self.win._select_key(key)
        except Exception as e:
            self.toast(f"navigation failed: {e}")


# ──────────────────────────────────────────────────────────────────────
# BACKUP — Timeshift snapshots, schedule, restore
# ──────────────────────────────────────────────────────────────────────
class BackupPage(SectionPage):
    """Timeshift wrapper. Reads real snapshot list via `timeshift --list`,
    surfaces schedule from /etc/timeshift/timeshift.json, exposes the
    full nyxus_backup app for create/restore/delete operations.
    """
    KEY = "backup"

    def build(self) -> None:
        if not have("timeshift"):
            grp = Adw.PreferencesGroup(
                title="Timeshift not installed",
                description="The backup engine is missing. Install with "
                            "`sudo pacman -S timeshift` and reopen.")
            self.add_group(grp)
            grp.add(action_row(
                "Install Timeshift",
                "Opens a terminal with sudo pacman -S timeshift",
                "Install",
                lambda: open_terminal("sudo pacman -S timeshift", self.win)))
            self.add_pill(status_pill("missing", "danger"))
            return

        # Snapshots overview — must NEVER silently report 0.
        # If pkexec is denied/cancelled or timeshift errors out, surface
        # the failure explicitly so the user knows the count isn't real.
        snaps = Adw.PreferencesGroup(
            title="Snapshots",
            description="Restore points captured by Timeshift")
        self.add_group(snaps)
        rc, out, err = sh(["pkexec", "timeshift", "--list"], timeout=12)
        # Initialize before the branch so the final pill below is safe
        # to reference even on the failure path.
        count = 0
        read_ok = (rc == 0)
        # Time Machine-style scrubber (Phase 6.27): each snapshot gets
        # a row with Restore + Delete buttons so the user can scrub
        # back through history without leaving Settings.
        snap_rows: list[tuple[str, str, str]] = []  # (name, ts, tag)
        if not read_ok:
            snaps.add(empty_row(
                "Could not read snapshot list",
                (err or "pkexec denied or timeshift failed").strip()
                + " — open the full Backup app to retry"))
        else:
            latest = "—"
            for line in (out or "").splitlines():
                line = line.strip()
                if re.match(r"^\d+\s+>", line):
                    count += 1
                    parts = line.split()
                    if len(parts) >= 4:
                        # Layout: NUM > NAME [TAG] [DESCRIPTION...]
                        name = parts[2]
                        tag  = parts[3] if len(parts) >= 4 else ""
                        # Snapshot name IS its timestamp in timeshift
                        # (e.g. 2026-05-13_10-30-15) — display it
                        # untouched, that's what `timeshift --restore
                        # --snapshot` expects.
                        ts   = name.replace("_", " ")
                        snap_rows.append((name, ts, tag))
                        if latest == "—":
                            latest = ts
            snaps.add(kv_row("Total snapshots", str(count)))
            snaps.add(kv_row("Most recent", latest))

        if snap_rows:
            scrub = Adw.PreferencesGroup(
                title="Restore points",
                description="Time Machine-style scrubber — Restore "
                            "queues a reboot via pkexec; Delete is "
                            "non-recoverable")
            self.add_group(scrub)
            # Cap visible rows to keep the page snappy on systems with
            # hundreds of snapshots; everything is still reachable
            # through the full Backup app.
            VISIBLE = 12
            for name, ts, tag in snap_rows[:VISIBLE]:
                row = Adw.ActionRow(
                    title=ts,
                    subtitle=f"id={name}  ·  tag={tag or '—'}")
                restore_btn = Gtk.Button(label="Restore")
                restore_btn.add_css_class("destructive-action")
                restore_btn.set_valign(Gtk.Align.CENTER)
                restore_btn.set_tooltip_text(
                    "Reboots into recovery to restore this snapshot")
                restore_btn.connect(
                    "clicked",
                    lambda _b, n=name: self._snap_confirm_restore(n))
                row.add_suffix(restore_btn)

                del_btn = Gtk.Button(label="Delete")
                del_btn.set_valign(Gtk.Align.CENTER)
                del_btn.set_tooltip_text(
                    "Permanently remove this snapshot (cannot be undone)")
                del_btn.connect(
                    "clicked",
                    lambda _b, n=name: self._snap_confirm_delete(n))
                row.add_suffix(del_btn)
                scrub.add(row)
            if len(snap_rows) > VISIBLE:
                scrub.add(empty_row(
                    f"+ {len(snap_rows) - VISIBLE} more snapshot(s) "
                    f"hidden",
                    "Open the full Backup app to see all of them"))

        # Launcher + schedule prefs
        tools = Adw.PreferencesGroup(
            title="Tools",
            description="Full backup UI · keybind Super + Ctrl + B")
        self.add_group(tools)
        tools.add(action_row(
            "Open NYXUS Backup",
            "Create, restore and delete snapshots with the full UI",
            "Open",
            lambda: fire_and_forget("nyxus-backup"),
            css="nyx-pill-ok"))
        tools.add(action_row(
            "Create snapshot now",
            "Runs `timeshift --create` with a 'manual' tag (admin prompt)",
            "Snapshot",
            lambda: open_terminal(
                "sudo timeshift --create --comments 'manual from settings' "
                "--tags M", self.win)))

        sched = Adw.PreferencesGroup(
            title="Schedule",
            description="Configure schedule from the full Backup app — "
                        "Timeshift writes to /etc/timeshift/timeshift.json")
        self.add_group(sched)
        cfg_path = Path("/etc/timeshift/timeshift.json")
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text())
                for label, key in (
                    ("Hourly schedule", "schedule_hourly"),
                    ("Daily schedule",  "schedule_daily"),
                    ("Weekly schedule", "schedule_weekly"),
                    ("Monthly schedule","schedule_monthly"),
                    ("Boot schedule",   "schedule_boot"),
                ):
                    val = str(cfg.get(key, "false")).lower()
                    sched.add(kv_row(label,
                                     "on" if val == "true" else "off"))
            except Exception as e:
                sched.add(empty_row("Could not read config", str(e)))
        else:
            sched.add(empty_row(
                "No Timeshift config yet",
                "Open the full Backup app once to initialize"))

        if read_ok:
            self.add_pill(status_pill(f"{count} snap", "ok"))
        else:
            self.add_pill(status_pill("read failed", "danger"))

    # ── Snapshot scrubber actions (Phase 6.27) ────────────────────────
    def _snap_confirm_restore(self, name: str) -> None:
        """Confirm dialog → pkexec timeshift --restore.

        Restore is destructive (queues a reboot) so we always show a
        confirmation. The Backup app does the same — keeping the
        contract identical avoids surprise.
        """
        dialog = Adw.MessageDialog.new(
            self.win,
            "Restore this snapshot?",
            f"NYXUS will reboot into recovery and roll the system "
            f"back to:\n\n  {name.replace('_', ' ')}\n\n"
            f"Unsaved work in any open app will be lost.")
        dialog.add_response("cancel",  "Cancel")
        dialog.add_response("restore", "Restore")
        dialog.set_response_appearance(
            "restore", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._snap_on_restore_resp, name)
        dialog.present()

    def _snap_on_restore_resp(self, _dialog, response: str,
                              name: str) -> None:
        if response != "restore":
            return
        # Validate the snapshot name matches the timeshift format
        # before letting it anywhere near a pkexec command line —
        # belt-and-braces against the (highly unlikely) case of a
        # malicious /etc/timeshift state polluting the parsed list.
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}_"
                            r"[0-9]{2}-[0-9]{2}-[0-9]{2}", name):
            self.toast(f"refusing odd snapshot name: {name[:32]}")
            log.warning("snapshot name failed regex: %r", name)
            return
        sh_async(
            ["pkexec", "timeshift", "--restore",
             "--snapshot", name, "--yes"],
            lambda r: self.toast(
                "restore queued — system will reboot" if r[0] == 0
                else f"restore failed: {(r[2] or '')[:80]}"),
            timeout=20)

    def _snap_confirm_delete(self, name: str) -> None:
        dialog = Adw.MessageDialog.new(
            self.win,
            "Delete this snapshot?",
            f"This permanently removes:\n\n  "
            f"{name.replace('_', ' ')}\n\n"
            f"You won't be able to restore from it afterwards.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance(
            "delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._snap_on_delete_resp, name)
        dialog.present()

    def _snap_on_delete_resp(self, _dialog, response: str,
                             name: str) -> None:
        if response != "delete":
            return
        if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}_"
                            r"[0-9]{2}-[0-9]{2}-[0-9]{2}", name):
            self.toast(f"refusing odd snapshot name: {name[:32]}")
            log.warning("snapshot name failed regex: %r", name)
            return
        def _on_done(r):
            if r[0] == 0:
                self.toast(f"deleted {name.replace('_', ' ')}")
                # Re-render so the row disappears from the scrubber.
                self.rebuild()
            else:
                self.toast(f"delete failed: {(r[2] or '')[:80]}")
        sh_async(
            ["pkexec", "timeshift", "--delete",
             "--snapshot", name, "--yes"],
            _on_done,
            timeout=15)


# ──────────────────────────────────────────────────────────────────────
# SYNC — NYXUS Account opt-in sync (wallpaper / theme / settings)
# ──────────────────────────────────────────────────────────────────────
class SyncPage(SectionPage):
    """Front-end for nyxus_account: configure endpoint + token, view
    last sync timestamp, trigger push/pull. All sync is user-initiated;
    auto-pull at login is intentionally disabled (data-loss risk).
    """
    KEY = "sync"
    CFG = Path.home() / ".config" / "nyxus" / "account.json"

    def build(self) -> None:
        cfg = {}
        cfg_err = None
        if self.CFG.exists():
            try:
                cfg = json.loads(self.CFG.read_text())
            except Exception as e:
                cfg_err = str(e)
                log.warning("account.json read: %s", e)

        # Connection — key is `url` (matches nyxus_account.py CLI/UI)
        conn = Adw.PreferencesGroup(
            title="Connection",
            description="Sync server endpoint & access token (chmod 600)")
        self.add_group(conn)
        if cfg_err:
            conn.add(empty_row("Could not read account.json", cfg_err))
        url = cfg.get("url", "")
        conn.add(kv_row("Endpoint URL", url or "(not set)"))
        token = cfg.get("token", "")
        conn.add(kv_row("Token",
                        "•" * 12 if token else "(not set)"))
        conn.add(kv_row("Last sync",
                        cfg.get("last_sync", "never")))

        # Operations
        ops = Adw.PreferencesGroup(
            title="Operations",
            description="All sync is user-initiated — automatic pulls are "
                        "disabled to prevent overwriting local prefs")
        self.add_group(ops)
        ops.add(action_row(
            "Open NYXUS Account",
            "Configure endpoint + token, push/pull from the full UI",
            "Open",
            lambda: fire_and_forget("nyxus-account"),
            css="nyx-pill-ok"))
        ops.add(action_row(
            "Push now",
            "Bundle wallpaper + theme + settings and upload",
            "Push",
            lambda: fire_and_forget("nyxus-account --push")))
        ops.add(action_row(
            "Pull now",
            "Download remote bundle and apply locally",
            "Pull",
            lambda: fire_and_forget("nyxus-account --pull")))

        # Scope
        scope = Adw.PreferencesGroup(
            title="Sync scope",
            description="What gets included in the bundle (allow-list, "
                        "locked for safety)")
        self.add_group(scope)
        for item in (
            "Accent colour (~/.config/nyxus/accent.conf)",
            "Sound prefs (~/.config/nyxus/sound.conf)",
            "Desktop layout (~/.config/nyxus/desktop.conf)",
            "GTK 3 settings (~/.config/gtk-3.0/settings.ini)",
            "GTK 4 settings (~/.config/gtk-4.0/settings.ini)",
            "Active wallpaper symlink",
        ):
            scope.add(kv_row(item, "included"))

        self.add_pill(status_pill(
            "configured" if url else "not set up",
            "ok" if url else "warn"))


# ──────────────────────────────────────────────────────────────────────
# DROP — KDE Connect rebranded as NYXUS Drop (file & text share)
# ──────────────────────────────────────────────────────────────────────
class DropPage(SectionPage):
    """Surfaces KDE Connect device list, daemon status, and launches the
    full nyxus_drop UI for sending files / text to nearby devices.
    """
    KEY = "drop"

    def build(self) -> None:
        if not have("kdeconnect-cli"):
            grp = Adw.PreferencesGroup(
                title="KDE Connect not installed",
                description="NYXUS Drop is built on KDE Connect. Install "
                            "with `sudo pacman -S kdeconnect`.")
            self.add_group(grp)
            grp.add(action_row(
                "Install KDE Connect",
                "Opens a terminal with sudo pacman -S kdeconnect",
                "Install",
                lambda: open_terminal("sudo pacman -S kdeconnect",
                                      self.win)))
            self.add_pill(status_pill("missing", "danger"))
            return

        # Daemon status
        status = Adw.PreferencesGroup(
            title="Daemon",
            description="kdeconnectd handles discovery and pairing")
        self.add_group(status)
        rc, out, _ = sh(["pgrep", "-x", "kdeconnectd"], timeout=2)
        running = (rc == 0 and out.strip())
        status.add(kv_row("kdeconnectd",
                          "running" if running else "stopped"))

        # Devices
        dev_grp = Adw.PreferencesGroup(
            title="Devices",
            description="Paired and reachable devices on this network")
        self.add_group(dev_grp)
        rc, out, _ = sh(["kdeconnect-cli", "--list-devices"], timeout=4)
        devices = []
        if rc == 0 and out:
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("- "):
                    devices.append(line[2:])
        if devices:
            for d in devices:
                dev_grp.add(kv_row(d, ""))
        else:
            dev_grp.add(empty_row(
                "No devices found",
                "Install KDE Connect on your phone and pair it"))

        # Tools
        tools = Adw.PreferencesGroup(
            title="Tools",
            description="Send files & text · keybind Super + Ctrl + D")
        self.add_group(tools)
        tools.add(action_row(
            "Open NYXUS Drop",
            "Send files & text to paired devices from the full UI",
            "Open",
            lambda: fire_and_forget("nyxus-drop"),
            css="nyx-pill-ok"))
        tools.add(action_row(
            "Refresh devices",
            "Re-poll kdeconnect-cli --refresh",
            "Refresh",
            lambda: sh_async(
                ["kdeconnect-cli", "--refresh"],
                lambda r: self.toast(
                    "refreshed" if r[0] == 0 else "refresh failed"),
                timeout=4)))

        self.add_pill(status_pill(
            f"{len(devices)} dev" if devices else "0 dev",
            "ok" if devices else "warn"))


# ──────────────────────────────────────────────────────────────────────
# SECURITY — embedded summary + launcher for the standalone
# nyxus_security.py Security Center. Settings is the discovery surface
# (every page rolled up under one health score); the standalone app is
# the management surface (10 sections, full CRUD).
# ──────────────────────────────────────────────────────────────────────
class SecurityPage(SectionPage):
    """Inline summary of system security posture + launchers for the
    full Security Center, the PANIC button, and the quick-scan path.

    Reads:
      · `ufw status verbose`               → firewall state
      · `systemctl is-active clamav-*`     → AV engine
      · `bootctl status` / `mokutil`        → secure boot
      · `/sys/class/tpm/tpm0`              → TPM presence
      · `lsblk` for crypto_LUKS volumes
      · `journalctl -g 'Failed password'`   → recent failed logins
    Writes: none — all mutations happen in the standalone Security
    Center via the polkit-elevated nyxus-security-helper.
    """
    KEY = "security"

    def build(self) -> None:
        # Headline group + open-app
        head = Adw.PreferencesGroup()
        head.set_title("NYXUS Security Center")
        head.set_description(
            "Unified hub for firewall, anti-malware, encryption, account "
            "protection, device security, privacy indicators, and audit. "
            "Use the buttons below to open the full center, run a quick "
            "scan, or engage panic lockdown.")
        row_open = Adw.ActionRow(title="Open Security Center",
                                 subtitle="10 sections · live threat tape · panic mode")
        btn_open = Gtk.Button(label="Open"); btn_open.add_css_class("suggested-action")
        btn_open.set_valign(Gtk.Align.CENTER)
        btn_open.connect("clicked",
                         lambda *_: fire_and_forget("nyxus-security"))
        row_open.add_suffix(btn_open)
        row_open.set_activatable_widget(btn_open)
        head.add(row_open)

        row_scan = Adw.ActionRow(title="Run quick scan",
                                 subtitle="ClamAV scan of $HOME and /tmp")
        btn_scan = Gtk.Button(label="Scan")
        btn_scan.set_valign(Gtk.Align.CENTER)
        btn_scan.connect("clicked",
                         lambda *_: fire_and_forget("nyxus-security --quick-scan"))
        row_scan.add_suffix(btn_scan)
        head.add(row_scan)

        row_panic = Adw.ActionRow(title="Panic lockdown",
                                  subtitle="Lock screen, clear clipboard, "
                                  "dismount removable, flush DNS")
        btn_panic = Gtk.Button(label="PANIC"); btn_panic.add_css_class("destructive-action")
        btn_panic.set_valign(Gtk.Align.CENTER)
        btn_panic.connect("clicked",
                          lambda *_: fire_and_forget("nyxus-security --panic"))
        row_panic.add_suffix(btn_panic)
        head.add(row_panic)
        self.add_group(head)

        # Subsystem state — read live, no caching
        sub = Adw.PreferencesGroup()
        sub.set_title("System posture")
        sub.set_description("Live status from the kernel, systemd, and ufw.")
        self.add_group(sub)
        self._sub = sub

        # Render rows asynchronously so we don't block the Settings UI.
        self._render_posture_async()

    def _render_posture_async(self) -> None:
        def worker():
            posture = self._collect_posture()
            GLib.idle_add(self._fill_posture, posture)
        threading.Thread(target=worker, daemon=True).start()

    def _collect_posture(self) -> list[tuple[str, str, str]]:
        """Returns [(label, kind, detail)]. Subprocess-only, no GTK."""
        out: list[tuple[str, str, str]] = []
        # Firewall
        rc, sout, _ = run(["ufw", "status", "verbose"], timeout=4)
        if rc == 0:
            active = "Status: active" in sout
            deny_in = "deny (incoming" in sout
            if active and deny_in:
                out.append(("Firewall", "ok", "active · deny inbound"))
            elif active:
                out.append(("Firewall", "warn", "active · permissive"))
            else:
                out.append(("Firewall", "danger", "inactive"))
        else:
            out.append(("Firewall", "warn", "ufw not installed"))
        # ClamAV
        for svc in ("clamav-daemon.service", "clamav-daemon", "clamd@scan"):
            rc, sout, _ = run(["systemctl", "is-active", svc], timeout=2)
            if sout == "active":
                out.append(("Real-time AV", "ok", f"{svc} running"))
                break
        else:
            out.append(("Real-time AV", "warn",
                        "daemon stopped — on-demand only"))
        # Secure Boot
        rc, sout, _ = run(["bootctl", "status"], timeout=3)
        if "Secure Boot: enabled" in sout:
            out.append(("Secure Boot", "ok", "enabled"))
        elif "Secure Boot: disabled" in sout:
            out.append(("Secure Boot", "warn", "disabled in firmware"))
        else:
            out.append(("Secure Boot", "warn", "unknown"))
        # TPM
        if Path("/sys/class/tpm/tpm0").exists():
            out.append(("TPM", "ok", "present"))
        else:
            out.append(("TPM", "warn", "not present"))
        # LUKS
        rc, sout, _ = run(["lsblk", "-rno", "FSTYPE"], timeout=3)
        if "crypto_LUKS" in sout:
            n = sum(1 for l in sout.splitlines() if l.strip() == "crypto_LUKS")
            out.append(("Disk encryption", "ok", f"{n} LUKS volume(s)"))
        else:
            out.append(("Disk encryption", "warn", "no LUKS volumes"))
        # Failed logins
        rc, sout, _ = run(["journalctl", "-n", "20", "--no-pager",
                           "-g", "Failed password|authentication failure"],
                          timeout=4)
        n = len(sout.splitlines()) if sout else 0
        out.append(("Failed logins (24h)",
                    "ok" if n == 0 else "warn",
                    f"{n} event(s)"))
        return out

    def _fill_posture(self, posture: list[tuple[str, str, str]]) -> bool:
        for label, kind, detail in posture:
            row = Adw.ActionRow(title=label, subtitle=detail)
            row.add_suffix(status_pill(kind.upper(), kind))
            self._sub.add(row)
        return False


# Tiny helper used above — wraps subprocess for the page's posture probe.
def run(cmd, timeout: int = 5):
    try:
        import subprocess as _sp
        p = _sp.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout or "").strip(), (p.stderr or "").strip()
    except FileNotFoundError:
        return 127, "", f"not found: {cmd[0]}"
    except Exception as e:  # pylint: disable=broad-except
        return 1, "", str(e)


# ──────────────────────────────────────────────────────────────────────
# LANGUAGE & REGION — gettext locale picker.
#
# Real reads/writes:
#   · current language ← nyxus_i18n.current_language() (env + user conf)
#   · system locale    ← /etc/locale.conf (LANG=)
#   · available locales← nyxus_i18n.available_locales() (.mo + scaffold)
#                        + `locale -a` filtered to UTF-8 entries
#   · user pick        → ~/.config/nyxus/locale.conf (LANGUAGE=…)
#                        → optional pkexec write of /etc/locale.conf
#
# Never silent-swallows an error: every failure path toasts the user
# AND logs to ~/.cache/nyxus/i18n.log via the shim.
# ──────────────────────────────────────────────────────────────────────
class LanguagePage(SectionPage):
    KEY = "language"

    # Friendly labels for the short codes the gettext shim reports.
    _LANG_LABELS = {
        "en": "English",
        "es": "Español (Spanish)",
        "fr": "Français (French)",
        "de": "Deutsch (German)",
        "it": "Italiano (Italian)",
        "pt": "Português (Portuguese)",
        "ja": "日本語 (Japanese)",
        "zh": "中文 (Chinese)",
        "ru": "Русский (Russian)",
        "ar": "العربية (Arabic)",
    }

    def build(self) -> None:
        # Lazy import — keep the shim optional so settings still loads
        # if someone deletes the locale tree.
        try:
            import nyxus_i18n as i18n  # noqa: WPS433 (runtime import OK)
        except Exception as e:  # pylint: disable=broad-except
            self.add_group(empty_group(
                "i18n shim missing",
                f"nyxus_i18n.py failed to import: {e}"))
            self.add_pill(status_pill("i18n", "warn"))
            return

        cur_lang = i18n.current_language()
        ldir = i18n.localedir()
        # Live selection — read by the system-apply button at click
        # time, not at build time, so the user's freshly-picked combo
        # value is always what gets written to /etc/locale.conf.
        self._selected_lang = cur_lang
        self._i18n = i18n

        # ── Status group ───────────────────────────────────────
        st = Adw.PreferencesGroup(
            title="Current",
            description="Reads from $NYXUS_LANG → user override → "
                        "$LANGUAGE → $LANG → fallback 'en'.")
        self.add_group(st)
        st.add(kv_row("Active language",
                      self._LANG_LABELS.get(cur_lang, cur_lang)))
        st.add(kv_row("gettext domain", "nyxus"))
        st.add(kv_row("Locale directory", ldir))

        # System-wide LANG (read-only display, edit via pkexec below)
        sys_lang = self._read_system_lang()
        st.add(kv_row("System LANG (/etc/locale.conf)",
                      sys_lang or "(unset)"))

        # ── Picker ─────────────────────────────────────────────
        pick = Adw.PreferencesGroup(
            title="Display language",
            description="Applied at next sign-in. Sign out & back in "
                        "to see translated UI everywhere.")
        self.add_group(pick)

        codes = i18n.available_locales()
        if cur_lang not in codes:
            codes = sorted(set(codes) | {cur_lang})
        labels = [self._LANG_LABELS.get(c, c) for c in codes]

        combo_row = Adw.ComboRow(
            title="Language",
            subtitle="Persisted to ~/.config/nyxus/locale.conf")
        sl = Gtk.StringList()
        for lbl in labels:
            sl.append(lbl)
        combo_row.set_model(sl)
        try:
            combo_row.set_selected(codes.index(cur_lang))
        except ValueError:
            combo_row.set_selected(0)
        # Re-entrancy guard so the initial set_selected above doesn't
        # immediately rewrite the user conf with the same value.
        combo_row._nyxus_armed = False  # type: ignore[attr-defined]

        def _on_selected(row, _pspec, codes=codes):
            if not getattr(row, "_nyxus_armed", False):
                row._nyxus_armed = True  # type: ignore[attr-defined]
                return
            idx = row.get_selected()
            if idx < 0 or idx >= len(codes):
                return
            new_code = codes[idx]
            try:
                i18n.write_user_locale(new_code)
                self._selected_lang = new_code
                self.toast(
                    f"language → {new_code} · sign out to apply")
            except Exception as e:  # pylint: disable=broad-except
                log.exception("write user locale: %s", e)
                self.toast(f"failed to save language: {e}")
        combo_row.connect("notify::selected", _on_selected)
        # Mark armed AFTER connecting so the very first signal (which
        # GTK fires when the model is bound) is ignored.
        GLib.idle_add(
            lambda r=combo_row: (setattr(r, "_nyxus_armed", True), False)[1])
        pick.add(combo_row)

        # ── System-wide apply ──────────────────────────────────
        sysg = Adw.PreferencesGroup(
            title="System-wide (login screen + non-NYXUS apps)",
            description="Writes /etc/locale.conf via pkexec. Affects "
                        "every user on this machine — admin password "
                        "required.")
        self.add_group(sysg)
        sysg.add(action_row(
            "Apply current pick to /etc/locale.conf",
            "LANG=<lang>.UTF-8 (one line)",
            "Apply",
            # Read self._selected_lang at CLICK time, not build time,
            # so the user's freshly-picked combo value is what's
            # written. (Capturing cur_lang in the closure would write
            # the page-load value forever.)
            lambda: self._apply_system_lang(self._selected_lang)))

        # ── Translator tools ───────────────────────────────────
        tools = Adw.PreferencesGroup(
            title="Translator tools",
            description="Re-extract template strings or compile .po → "
                        ".mo after editing translations.")
        self.add_group(tools)
        scripts_dir = Path(ldir).parent if Path(ldir).name == "locale" \
            else Path(__file__).resolve().parent
        ex = scripts_dir / "locale" / "extract.sh"
        co = scripts_dir / "locale" / "compile.sh"
        tools.add(action_row(
            "Extract strings → nyxus.pot",
            str(ex),
            "Run",
            lambda p=ex: open_terminal(f"bash {p}", self.win)))
        tools.add(action_row(
            "Compile *.po → *.mo",
            str(co),
            "Run",
            lambda p=co: open_terminal(f"bash {p}", self.win)))

        self.add_pill(status_pill("i18n", "ok"))

    def _read_system_lang(self) -> str:
        try:
            for ln in Path("/etc/locale.conf") \
                    .read_text(encoding="utf-8").splitlines():
                ln = ln.strip()
                if ln.startswith("LANG="):
                    return ln.split("=", 1)[1].strip().strip('"')
        except Exception:  # pylint: disable=broad-except
            pass
        return ""

    def _apply_system_lang(self, code: str) -> None:
        # Whitelist the code: lowercase letters, optional underscore +
        # uppercase letters. Refuses anything that could shell-escape.
        import re as _re
        short = (code or "en").split("_")[0].lower()
        if not _re.fullmatch(r"[a-z]{2,3}", short):
            self.toast(f"refusing odd lang code: {short[:8]!r}")
            return
        lang = f"{short}_{short.upper()}.UTF-8" if short != "en" \
            else "en_US.UTF-8"
        body = f"LANG={lang}\n"
        cmd = ["pkexec", "sh", "-c",
               f"printf %s {shlex.quote(body)} > /etc/locale.conf"]

        def done(r):
            if r[0] == 0:
                self.toast(f"system locale → {lang} · reboot to apply")
            else:
                msg = (r[2] or "")[:120] or "admin denied"
                self.toast(f"failed: {msg}")
        sh_async(cmd, done, timeout=10)


# Map section.key → page class.
PAGE_CLASSES = {
    "appearance":    AppearancePage,
    "network":       NetworkPage,
    "bluetooth":     BluetoothPage,
    "printers":      PrintersPage,
    "cameras_mics":  CamerasMicsPage,
    "controllers":   ControllersPage,
    "color":         ColorPage,
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
    "backup":        BackupPage,
    "sync":          SyncPage,
    "drop":          DropPage,
    "security":      SecurityPage,
    "parental":      ParentalControlsPage,
    "app_perms":     AppPermissionsPage,
    "language":      LanguagePage,
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
        self.search.set_placeholder_text("Search settings…   (Ctrl + F)")
        self.search.connect("search-changed", self._on_search)
        sidebar_outer.append(self.search)
        # Live match counter — hidden when search box is empty
        self.search_count = Gtk.Label(label="", xalign=0.0)
        self.search_count.add_css_class("nyx-search-count")
        self.search_count.set_visible(False)
        sidebar_outer.append(self.search_count)

        # List
        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("background")
        self.listbox.connect("row-selected", self._on_row_selected)
        self.listbox.set_filter_func(self._filter_row)
        # Category headers — Mac System Settings style group dividers
        self.listbox.set_header_func(self._sidebar_header_func)
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

        # ── Window-level keyboard shortcuts ──────────────────────────
        # Ctrl+F  → focus search · Esc → clear search & focus sidebar
        # Ctrl+L  → focus sidebar list · Ctrl+W/Q → close window
        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._on_window_key)
        self.add_controller(kc)

    def _on_window_key(self, _ctrl, keyval, _kc, state) -> bool:
        ctrl = bool(state & Gdk.ModifierType.CONTROL_MASK)
        if ctrl and keyval in (Gdk.KEY_f, Gdk.KEY_F):
            self.search.grab_focus()
            return True
        if ctrl and keyval in (Gdk.KEY_l, Gdk.KEY_L):
            self.listbox.grab_focus()
            return True
        if ctrl and keyval in (Gdk.KEY_k, Gdk.KEY_K):
            self.open_command_palette()
            return True
        if ctrl and keyval in (Gdk.KEY_w, Gdk.KEY_W,
                               Gdk.KEY_q, Gdk.KEY_Q):
            self.close()
            return True
        if keyval == Gdk.KEY_Escape:
            if self.search.get_text():
                self.search.set_text("")
                self.listbox.grab_focus()
                return True
        return False

    # ── Command palette ──────────────────────────────────────────────
    def open_command_palette(self) -> None:
        """Open a Spotlight-style overlay (Ctrl+K) to jump to any
        section by typing. Uses the same keyword/title index as the
        sidebar search but as a focused overlay window."""
        try:
            pal = CommandPalette(self)
            pal.present()
        except Exception as e:
            log.warning("command palette: %s", e)
            self.toast("Command palette unavailable")

    def _sidebar_header_func(self, row: Gtk.ListBoxRow,
                             before: Optional[Gtk.ListBoxRow]) -> None:
        """Show a small-caps category label above the first row of each
        category, like macOS System Settings. Hidden during search so
        filtered results stay tightly packed.
        """
        if not isinstance(row, SidebarRow):
            row.set_header(None)
            return
        if self.search.get_text().strip():
            row.set_header(None)
            return
        cat = row.section.category or ""
        prev_cat = ""
        if isinstance(before, SidebarRow):
            prev_cat = before.section.category or ""
        if cat and cat != prev_cat:
            lbl = Gtk.Label(label=cat.upper(), xalign=0.0)
            lbl.add_css_class("nyx-cat-header")
            row.set_header(lbl)
        else:
            row.set_header(None)

    # ── search filter ─────────────────────────────────────────────────
    def _on_search(self, _entry: Gtk.SearchEntry) -> None:
        self.listbox.invalidate_filter()
        # Headers are hidden while filtering; force a re-eval.
        self.listbox.invalidate_headers()
        # Update the live match counter
        q = self.search.get_text().strip()
        if not q:
            self.search_count.set_visible(False)
            return
        total = len(SECTIONS)
        shown = 0
        i = 0
        while True:
            row = self.listbox.get_row_at_index(i)
            if row is None:
                break
            if isinstance(row, SidebarRow) and self._filter_row(row):
                shown += 1
            i += 1
        self.search_count.set_text(f"{shown} of {total} match")
        self.search_count.set_visible(True)

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
# Command palette — Ctrl+K Spotlight-style jump menu
# ──────────────────────────────────────────────────────────────────────
class CommandPalette(Adw.Window):
    """Modal overlay window. Type to fuzzy-match any section by title,
    keyword or category. Enter activates the highlighted row.
    Up/Down navigate; Esc dismisses; click selects.
    """

    def __init__(self, parent: "SettingsWindow"):
        super().__init__(transient_for=parent, modal=True,
                         title="NYXUS Quick Jump")
        self.parent = parent
        self.set_default_size(540, 420)
        self.set_resizable(False)
        self.add_css_class("nyx-palette-window")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(12); outer.set_margin_bottom(12)
        outer.set_margin_start(12); outer.set_margin_end(12)
        self.set_content(outer)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class("nyx-palette-card")
        outer.append(card)

        self.entry = Gtk.SearchEntry()
        self.entry.set_placeholder_text("Type to jump…   "
                                        "↑↓ navigate · Enter open · Esc close")
        self.entry.add_css_class("nyx-palette-entry")
        self.entry.connect("search-changed", lambda *_: self._refresh())
        self.entry.connect("activate", lambda *_: self._activate_selected())
        card.append(self.entry)

        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_height(320)
        card.append(scroll)

        self.listbox = Gtk.ListBox()
        self.listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.listbox.add_css_class("background")
        self.listbox.connect("row-activated",
                             lambda _lb, _row: self._activate_selected())
        scroll.set_child(self.listbox)

        hint = Gtk.Label(
            label="↵ open · ↑/↓ navigate · esc dismiss",
            xalign=0.0)
        hint.add_css_class("nyx-palette-hint")
        card.append(hint)

        # Window-level keyboard navigation
        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._on_key)
        self.add_controller(kc)

        self._refresh()
        # Focus the entry so the user can type immediately.
        GLib.idle_add(self.entry.grab_focus)

    def _refresh(self) -> None:
        """Rebuild the rows from the current query."""
        # Clear
        child = self.listbox.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.listbox.remove(child)
            child = nxt
        q = self.entry.get_text().strip().lower()
        parts = [p for p in q.split() if p]
        for s in SECTIONS:
            hay = (f"{s.title} {s.subtitle} {s.keywords} "
                   f"{s.category}").lower()
            if parts and not all(p in hay for p in parts):
                continue
            row = Gtk.ListBoxRow()
            row.add_css_class("nyx-palette-row")
            row.section_key = s.key  # type: ignore[attr-defined]
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                          spacing=12)
            glyph = Gtk.Label(label=GLYPHS.get(s.glyph, ""))
            glyph.add_css_class("nyx-section-glyph")
            box.append(glyph)
            text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                           spacing=0)
            t = Gtk.Label(label=s.title, xalign=0.0)
            t.add_css_class("body")
            text.append(t)
            sub_text = (f"{s.category} · {s.subtitle}"
                        if s.category else s.subtitle)
            sub = Gtk.Label(label=sub_text, xalign=0.0)
            sub.add_css_class("subtitle")
            sub.set_ellipsize(3)
            text.append(sub)
            text.set_hexpand(True)
            box.append(text)
            row.set_child(box)
            self.listbox.append(row)
        # Auto-select first row so Enter just works
        first = self.listbox.get_row_at_index(0)
        if first is not None:
            self.listbox.select_row(first)

    def _activate_selected(self) -> None:
        row = self.listbox.get_selected_row()
        if row is None:
            row = self.listbox.get_row_at_index(0)
        if row is None:
            return
        key = getattr(row, "section_key", None)
        if key:
            self.parent._select_key(key)
        self.close()

    def _on_key(self, _ctrl, keyval, _kc, _state) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.close()
            return True
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            cur = self.listbox.get_selected_row()
            cur_idx = cur.get_index() if cur is not None else -1
            new_idx = cur_idx + (1 if keyval == Gdk.KEY_Down else -1)
            new_row = self.listbox.get_row_at_index(max(0, new_idx))
            if new_row is not None:
                self.listbox.select_row(new_row)
                new_row.grab_focus()
            return True
        return False


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
            # Honour deep-link argv: `nyxus-settings sound`
            if self._initial_section:
                try:
                    win._select_key(self._initial_section)
                except Exception as e:
                    log.warning("deep-link %s: %s",
                                self._initial_section, e)
        win.present()

    # Set by main() before run()
    _initial_section: Optional[str] = None


def main() -> int:
    """Entry point. Supports a single positional argv:

        nyxus-settings              → open last visited section
        nyxus-settings sound        → jump straight to Sound
        nyxus-settings keyboard     → jump straight to Keyboard
        nyxus-settings --list       → print all section keys + exit

    Unknown keys print a hint to stderr and continue with default.
    """
    argv = list(sys.argv)
    initial: Optional[str] = None
    if len(argv) > 1 and argv[1] in ("--list", "-l"):
        for s in SECTIONS:
            print(f"  {s.key:14s}  — {s.title}")
        return 0
    if len(argv) > 1 and not argv[1].startswith("-"):
        cand = argv[1].strip().lower()
        if cand in SECTIONS_BY_KEY:
            initial = cand
            argv.pop(1)  # don't pass it down to GApplication
        else:
            print(f"nyxus-settings: unknown section '{cand}' "
                  f"(try --list)", file=sys.stderr)
    app = SettingsApp()
    app._initial_section = initial
    return app.run(argv)


if __name__ == "__main__":
    raise SystemExit(main())
