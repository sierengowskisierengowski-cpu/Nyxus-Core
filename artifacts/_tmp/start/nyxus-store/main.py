"""
NYXUS App Store — grade-A discovery & install hub for the NYXUS suite.

Features
────────
  • Full catalog of every NYXUS sub-app, grouped by category
  • Rotating "Featured" banner at the top (daily seed)
  • 3-column card grid with neon glyph, Inter Display title/tagline,
    install/update/uninstall/open actions per card
  • Live counts (installed · available · total) in the header
  • Lightweight search filter
  • Spawns the appropriate installer in a real terminal so the user sees
    pacman/sudo prompts and progress
  • Uninstall removes ~/.local/bin launcher and the app's install dir
  • Single-instance toggle (re-run closes the running one)
  • Esc closes; close-request cleans up the PID file
  • Auto-injects nyxus_chrome (DARK MIRROR glass, Inter Display font, neon
    palette) — relies on the central chrome for typography so we never
    fight it with `*` selectors

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import hashlib
import os
import shutil
import signal
import subprocess
import sys
import time
from datetime import date
from pathlib import Path
from typing import Callable, Dict, List, Optional

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
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, Gio, GLib, Pango  # noqa: E402


# ─────────────────────────────────────────────── constants ──
APP_ID    = "io.nyxus.store"
WIN_W     = 940
WIN_H     = 720
CARD_COLS = 3

PID_FILE   = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "nyxus-store.pid"
NYXUS_BASE = "https://nyxus-core.replit.app/api/download/nyxus"
HOME       = Path(os.environ.get("HOME", "/"))
BIN_DIR    = HOME / ".local" / "bin"
SHARE_DIR  = HOME / ".local" / "share"
NYX_DIR    = HOME / ".nyxus"

# Brand palette (matches nyxus_chrome.py)
NEON_PINK   = "#e8edf5"
NEON_GREEN  = "#c8ccd6"
NEON_GOLD   = "#e8edf5"
NEON_BLUE   = "#c8ccd6"
NEON_PURPLE = "#c8ccd6"
TEXT  = "#e8edf5"
DIM   = "#c8ccd6"
FAINT = "#6a6e78"


# ─────────────────────────────────────────────── catalog ──
# Each entry:
#   key       — short identifier
#   title     — display name
#   tagline   — one-line description
#   glyph     — Nerd Font / Font Awesome glyph (no emoji)
#   color     — neon accent for the glyph and card border on hover
#   installer — slug under /api/download/nyxus/ (one-shot bash script)
#   binary    — launcher in $PATH after install (used to detect installed)
#   share     — ~/.local/share/<dir> the installer drops files into
#               (used for clean uninstall — set to "" to skip dir removal)
#   category  — section label
CATALOG: List[Dict[str, str]] = [
    # ── Core (the always-on shell)
    dict(key="start",         title="NYXUS Start",         category="Core",
         glyph="\uf0c9", color=NEON_PINK,
         tagline="Hand-drawn left-side flyout — search, pinned apps, scratchpad, power.",
         installer="nyxus_start_install.sh",
         binary="nyxus-start",         share="nyxus-start"),
    dict(key="panel",         title="NYXUS Panel",         category="Core",
         glyph="\uf0a1", color=NEON_BLUE,
         tagline="Right-side info flyout — weather, system stats, news, settings.",
         installer="nyxus_panel_install.sh",
         binary="nyxus-panel",         share="nyxus-panel"),
    dict(key="notifications", title="NYXUS Notifications", category="Core",
         glyph="\uf0f3", color=NEON_GOLD,
         tagline="Bottom-right notifications flyout with calendar and DND toggle.",
         installer="nyxus_start_install.sh",
         binary="nyxus-notifications", share="nyxus-notifications"),
    dict(key="settings",      title="NYXUS Settings",      category="Core",
         glyph="\uf013", color=NEON_GREEN,
         tagline="One window for appearance, profile, notifications & every NYXUS app.",
         installer="nyxus_panel_install.sh",
         binary="nyxus-settings",      share=""),

    # ── Productivity
    dict(key="home",          title="NYXUS Home",          category="Productivity",
         glyph="\uf015", color=NEON_PINK,
         tagline="Personalized home dashboard — bookmarks, feeds, quick links.",
         installer="nyxus_home_install.sh",
         binary="nyxus-home",          share="nyxus-home"),
    dict(key="notepad",       title="NyxRX Notepad",       category="Productivity",
         glyph="\uf249", color=NEON_GREEN,
         tagline="Sticky notes with search, tags, and graffiti theming.",
         installer="nyxus_notepad_install.sh",
         binary="nyxus-notepad",       share="nyxus-notepad"),
    dict(key="weather",       title="NYXUS Weather",       category="Productivity",
         glyph="\uf0e7", color=NEON_BLUE,
         tagline="Hyper-local weather widget with neon icons and animated radar.",
         installer="nyxus_weather_install.sh",
         binary="nyxus-weather",       share="nyxus-weather"),
    dict(key="passwords",     title="NYXUS Passwords",     category="Productivity",
         glyph="\uf084", color=NEON_GOLD,
         tagline="Encrypted vault — generate, store, search and autofill.",
         installer="nyxus_passwords_install.sh",
         binary="nyxus-passwords",     share="nyxus-passwords"),

    # ── Security
    dict(key="shield",        title="NYXUS Shield",        category="Security",
         glyph="\uf3ed", color=NEON_GREEN,
         tagline="Hardening, firewall, and audit dashboards for the NYXUS box.",
         installer="nyxus_security_install.sh",
         binary="nyxus-shield",        share="nyxus-shield"),
    dict(key="intel",         title="NYXUS Intel",         category="Security",
         glyph="\uf21b", color=NEON_BLUE,
         tagline="OSINT workstation — case management, evidence, encrypted vaults.",
         installer="nyxus_intel_install.sh",
         binary="nyxus-intel",         share="nyxus-intel"),

    # ── Creative
    dict(key="studio",        title="NYXUS Studio",        category="Creative",
         glyph="\uf03d", color=NEON_PINK,
         tagline="Creative suite preset — audio, video, and ComfyUI launchers.",
         installer="nyxus_studio_install.sh",
         binary="nyxus-studio",        share="nyxus-studio"),
    dict(key="godsapp",       title="GodsApp",             category="Creative",
         glyph="\uf005", color=NEON_GOLD,
         tagline="The NYXUS launcher's mother-app — handwritten everything.",
         installer="nyxus_godsapp_install.sh",
         binary="godsapp",             share="godsapp"),

    # ── AI
    dict(key="sage",          title="NYXUS Sage",          category="AI",
         glyph="\uf544", color=NEON_PURPLE,
         tagline="AI assistant + system co-pilot baked into your desktop.",
         installer="nyxus_sage_install.sh",
         binary="nyxus-sage",          share="sage"),
]

CATEGORIES      = ["Core", "Productivity", "Security", "Creative", "AI"]
CATEGORY_COLORS = {
    "Core":         NEON_PINK,
    "Productivity": NEON_GREEN,
    "Security":     NEON_BLUE,
    "Creative":     NEON_GOLD,
    "AI":           NEON_PURPLE,
}


# ─────────────────────────────────────────────── helpers ──
def _is_installed(entry: Dict[str, str]) -> bool:
    """An app is installed if its launcher is on PATH or in ~/.local/bin."""
    if shutil.which(entry["binary"]) is not None:
        return True
    return (BIN_DIR / entry["binary"]).exists()


def _featured_today() -> Dict[str, str]:
    """Pick a featured app deterministically from the date so it rotates
    daily but stays the same all day.  Falls back to GodsApp on errors."""
    try:
        seed = date.today().isoformat().encode()
        idx  = int(hashlib.sha1(seed).hexdigest(), 16) % len(CATALOG)
        return CATALOG[idx]
    except Exception:
        for e in CATALOG:
            if e["key"] == "godsapp":
                return e
        return CATALOG[0]


def _spawn_terminal(title: str, cmd: str) -> bool:
    """Run `cmd` in a fresh terminal so the user sees pacman/sudo output.
    Returns True if a terminal was found and launched."""
    candidates = [
        ["alacritty", "-T", title, "-e", "bash", "-lc", cmd],
        ["kitty",     "-T", title,        "bash", "-lc", cmd],
        ["foot",      "-T", title,        "bash", "-lc", cmd],
        ["wezterm",   "start", "--",      "bash", "-lc", cmd],
        ["xterm",     "-T", title, "-e",  "bash", "-lc", cmd],
        ["gnome-terminal", "--title", title, "--", "bash", "-lc", cmd],
        ["konsole",   "-p", f"tabtitle={title}", "-e", "bash", "-lc", cmd],
    ]
    for argv in candidates:
        if shutil.which(argv[0]):
            try:
                subprocess.Popen(argv, start_new_session=True)
                return True
            except Exception:
                continue
    return False


def _spawn_installer(entry: Dict[str, str]) -> None:
    """Install or reinstall an entry by piping its installer through bash."""
    url   = f"{NYXUS_BASE}/{entry['installer']}"
    title = f"NYXUS · Installing {entry['title']}"
    cmd   = (
        f"echo '── installing {entry['title']} ──'; "
        f"curl -fsSL {url} | sudo bash; "
        f"echo; echo '── done. press Enter to close ──'; read"
    )
    if not _spawn_terminal(title, cmd):
        # No terminal — run silently and notify the user
        try:
            subprocess.Popen(["bash", "-lc", cmd], start_new_session=True)
            if shutil.which("notify-send"):
                subprocess.Popen(
                    ["notify-send", "-a", "NYXUS Store",
                     f"Installing {entry['title']}",
                     "Running headless — check `journalctl --user -f` for output."],
                    start_new_session=True,
                )
        except Exception:
            pass


def _uninstall(entry: Dict[str, str]) -> None:
    """Remove the launcher script and the app's install dir."""
    title = f"NYXUS · Uninstalling {entry['title']}"
    paths = [str(BIN_DIR / entry["binary"])]
    if entry.get("share"):
        paths.append(str(SHARE_DIR / entry["share"]))
    # Also try common .desktop file naming
    paths.append(str(SHARE_DIR / "applications" / f"io.nyxus.{entry['key']}.desktop"))

    rm_lines = " ".join(f"'{p}'" for p in paths)
    cmd = (
        f"echo '── uninstalling {entry['title']} ──'; "
        f"for p in {rm_lines}; do "
        f"  if [[ -e \"$p\" || -L \"$p\" ]]; then "
        f"    rm -rf \"$p\" && echo \"  removed: $p\" || echo \"  failed:  $p\"; "
        f"  fi; "
        f"done; "
        f"echo; echo '── done. press Enter to close ──'; read"
    )
    if not _spawn_terminal(title, cmd):
        try:
            subprocess.Popen(["bash", "-lc", cmd], start_new_session=True)
        except Exception:
            pass


def _open_app(entry: Dict[str, str]) -> None:
    """Launch an installed app by its binary name."""
    bin_path = shutil.which(entry["binary"]) or str(BIN_DIR / entry["binary"])
    try:
        subprocess.Popen([bin_path], start_new_session=True)
    except Exception:
        pass


# ─────────────────────────────────────────────── single instance ──
def _toggle_singleton() -> bool:
    """If a previous nyxus-store instance is alive, kill it and exit
    (toggle behaviour). Validates /proc/<pid>/cmdline before SIGTERM so a
    stale/reused PID can never SIGTERM an unrelated process."""
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip() or "0")
    except Exception:
        pid = 0
    if pid <= 0 or pid == os.getpid():
        try: PID_FILE.unlink(missing_ok=True)
        except Exception: pass
        return False
    try:
        # Cheap liveness probe
        os.kill(pid, 0)
    except ProcessLookupError:
        try: PID_FILE.unlink(missing_ok=True)
        except Exception: pass
        return False
    except PermissionError:
        # Process exists but isn't ours — never signal it
        try: PID_FILE.unlink(missing_ok=True)
        except Exception: pass
        return False
    # Validate it's actually a NYXUS Store process
    try:
        cmdline = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="replace")
    except Exception:
        cmdline = ""
    if "nyxus-store" not in cmdline and "nyxus_store" not in cmdline:
        # Stale/reused PID — clear the file, don't toggle
        try: PID_FILE.unlink(missing_ok=True)
        except Exception: pass
        return False
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.05)
    except Exception:
        pass
    try: PID_FILE.unlink(missing_ok=True)
    except Exception: pass
    return True


def _write_pid() -> None:
    try:
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))
    except Exception:
        pass


def _clear_pid() -> None:
    try: PID_FILE.unlink(missing_ok=True)
    except Exception: pass


# ─────────────────────────────────────────────── CSS ──
# Store-only accents.  Loaded at APPLICATION priority so the central
# nyxus_chrome (USER priority) wins on typography and shell — we only
# add scoped classes here, never touch `*` or unscoped widget tags.
def _install_css() -> None:
    css = f"""
    .nyx-store-counts {{
        font-family: 'Inter Display', cursive;
        font-size:   17px;
        color:       {DIM};
        padding:     0 14px;
    }}
    .nyx-store-counts-num-installed {{ color: {NEON_GREEN}; }}
    .nyx-store-counts-num-available {{ color: {NEON_PINK}; }}
    .nyx-store-counts-num-total     {{ color: {NEON_GOLD}; }}

    .nyx-store-cat-header {{
        font-family:  'Inter Display', cursive;
        font-size:    24px;
        font-weight:  bold;
        padding:      14px 16px 6px 16px;
        text-shadow:  0 0 10px rgba(8, 12, 20, 0.40);
    }}
    .nyx-store-cat-header-core         {{ color: {NEON_PINK};   }}
    .nyx-store-cat-header-productivity {{ color: {NEON_GREEN};  }}
    .nyx-store-cat-header-security     {{ color: {NEON_BLUE};   }}
    .nyx-store-cat-header-creative     {{ color: {NEON_GOLD};   }}
    .nyx-store-cat-header-ai           {{ color: {NEON_PURPLE}; }}

    .nyx-store-card {{
        background-color: rgba(10, 10, 18, 0.55);
        border-radius:    12px;
        border:           1.5px solid rgba(8, 12, 20, 0.40);
        padding:          14px;
        margin:           6px;
        min-width:        260px;
        min-height:       170px;
        transition:       border-color 140ms ease, background-color 140ms ease,
                          box-shadow 140ms ease;
    }}
    .nyx-store-card:hover {{
        background-color: rgba(20, 16, 36, 0.65);
        box-shadow:       0 0 18px rgba(8, 12, 20, 0.30);
    }}
    .nyx-store-card-glyph {{
        font-family: 'JetBrains Mono Nerd Font', 'Symbols Nerd Font', 'Font Awesome 6 Free', monospace;
        font-size:   30px;
        padding:     0 10px 0 4px;
    }}
    .nyx-store-card-title {{
        font-family: 'Inter Display', cursive;
        font-size:   22px;
        font-weight: bold;
        color:       {TEXT};
    }}
    .nyx-store-card-body {{
        font-family: 'Inter Display', cursive;
        font-size:   15px;
        color:       {DIM};
    }}
    .nyx-store-card-status-installed   {{ color: {NEON_GREEN}; font-size: 14px; }}
    .nyx-store-card-status-available   {{ color: {DIM};        font-size: 14px; }}

    .nyx-store-featured {{
        background-color: rgba(20, 8, 32, 0.70);
        border:           2px solid rgba(255, 255, 255, 0.85);
        border-radius:    14px;
        padding:          18px;
        margin:           14px 12px 6px 12px;
        box-shadow:       0 0 28px rgba(255, 255, 255, 0.30);
    }}
    .nyx-store-featured-tag {{
        font-family: 'Inter Display', cursive;
        font-size:   14px;
        font-weight: bold;
        color:       {NEON_GOLD};
        padding-bottom: 4px;
    }}
    .nyx-store-featured-title {{
        font-family: 'Inter Display', cursive;
        font-size:   34px;
        font-weight: bold;
        color:       {TEXT};
        text-shadow: 0 0 14px rgba(255, 255, 255, 0.55);
    }}
    .nyx-store-featured-body {{
        font-family: 'Inter Display', cursive;
        font-size:   18px;
        color:       {DIM};
    }}
    .nyx-store-featured-glyph {{
        font-family: 'JetBrains Mono Nerd Font', 'Symbols Nerd Font', monospace;
        font-size:   46px;
        color:       {NEON_GOLD};
        padding:     0 18px;
    }}

    .nyx-store-empty {{
        font-family: 'Inter Display', cursive;
        font-size:   20px;
        color:       {FAINT};
        padding:     40px;
    }}
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode("utf-8"))
    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )


# ─────────────────────────────────────────────── widgets ──
def _glyph_label(glyph: str, color_hex: str, size_pt: int = 30) -> Gtk.Label:
    """Build a Pango-coloured glyph label so the neon hue lands on the icon."""
    lbl = Gtk.Label(label=glyph)
    lbl.add_css_class("nyx-store-card-glyph")
    color = color_hex.lstrip("#")
    r = int(color[0:2], 16) * 257
    g = int(color[2:4], 16) * 257
    b = int(color[4:6], 16) * 257
    attrs = Pango.AttrList()
    attrs.insert(Pango.attr_foreground_new(r, g, b))
    attrs.insert(Pango.attr_size_new(size_pt * Pango.SCALE))
    lbl.set_attributes(attrs)
    return lbl


def _build_card(entry: Dict[str, str],
                on_install:   Callable[[Dict[str, str]], None],
                on_uninstall: Callable[[Dict[str, str]], None],
                on_open:      Callable[[Dict[str, str]], None]) -> Gtk.Widget:
    """Single app card — glyph + title + tagline + action row."""
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    card.add_css_class("nyx-store-card")
    card.set_hexpand(True)

    # ── top row: glyph + title/status
    top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    top.append(_glyph_label(entry["glyph"], entry["color"]))

    title_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    title_col.set_hexpand(True)

    title = Gtk.Label(label=entry["title"])
    title.add_css_class("nyx-store-card-title")
    title.set_xalign(0)
    title_col.append(title)

    installed = _is_installed(entry)
    status = Gtk.Label(label=("\uf00c  Installed" if installed else "\uf019  Available"))
    status.add_css_class(
        "nyx-store-card-status-installed" if installed
        else "nyx-store-card-status-available"
    )
    status.set_xalign(0)
    title_col.append(status)

    top.append(title_col)
    card.append(top)

    # ── body: tagline
    body = Gtk.Label(label=entry["tagline"])
    body.add_css_class("nyx-store-card-body")
    body.set_xalign(0)
    body.set_wrap(True)
    body.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    body.set_max_width_chars(34)
    body.set_vexpand(True)
    body.set_valign(Gtk.Align.START)
    card.append(body)

    # ── action row (rainbow-cycling colours via .nyx-rainbow-row)
    actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6,
                      halign=Gtk.Align.END)
    actions.add_css_class("nyx-rainbow-row")

    if installed:
        b_open = Gtk.Button(label="\uf04b  Open")
        b_open.connect("clicked", lambda *_: on_open(entry))
        actions.append(b_open)

        b_re = Gtk.Button(label="\uf021  Reinstall")
        b_re.connect("clicked", lambda *_: on_install(entry))
        actions.append(b_re)

        b_un = Gtk.Button(label="\uf2ed  Remove")
        b_un.add_css_class("destructive-action")
        b_un.connect("clicked", lambda *_: on_uninstall(entry))
        actions.append(b_un)
    else:
        b_in = Gtk.Button(label="\uf019  Install")
        b_in.add_css_class("suggested-action")
        b_in.connect("clicked", lambda *_: on_install(entry))
        actions.append(b_in)

    card.append(actions)
    return card


def _build_featured(entry: Dict[str, str],
                    on_install: Callable[[Dict[str, str]], None],
                    on_open:    Callable[[Dict[str, str]], None]) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    box.add_css_class("nyx-store-featured")

    box.append(_glyph_label(entry["glyph"], NEON_GOLD, size_pt=46))

    col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    col.set_hexpand(True)

    tag = Gtk.Label(label="\uf005  FEATURED · APP OF THE DAY")
    tag.add_css_class("nyx-store-featured-tag")
    tag.set_xalign(0)
    col.append(tag)

    title = Gtk.Label(label=entry["title"])
    title.add_css_class("nyx-store-featured-title")
    title.set_xalign(0)
    col.append(title)

    body = Gtk.Label(label=entry["tagline"])
    body.add_css_class("nyx-store-featured-body")
    body.set_xalign(0)
    body.set_wrap(True)
    body.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
    col.append(body)

    box.append(col)

    # Action button on the right
    btn_col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                      valign=Gtk.Align.CENTER)
    if _is_installed(entry):
        b = Gtk.Button(label="\uf04b  Open")
        b.add_css_class("suggested-action")
        b.connect("clicked", lambda *_: on_open(entry))
    else:
        b = Gtk.Button(label="\uf019  Install Now")
        b.add_css_class("suggested-action")
        b.connect("clicked", lambda *_: on_install(entry))
    btn_col.append(b)
    box.append(btn_col)
    return box


# ─────────────────────────────────────────────── main window ──
class StoreWindow(Gtk.ApplicationWindow):
    def __init__(self, app: Gtk.Application) -> None:
        super().__init__(application=app, title="NYXUS App Store")
        self.set_default_size(WIN_W, WIN_H)
        self.add_css_class("nyx-shell-bg")

        self._search_text: str = ""

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(self._build_header())
        root.append(self._build_body())
        root.append(self._build_action_bar())
        self.set_child(root)

        # Esc closes
        esc = Gtk.EventControllerKey()
        def _on_key(_c, keyval, _kc, _mod):
            if keyval == Gdk.KEY_Escape:
                self.close()
                return True
            return False
        esc.connect("key-pressed", _on_key)
        self.add_controller(esc)

        self.connect("close-request", lambda *_: (_clear_pid(), False)[1])

    # ── header
    def _build_header(self) -> Gtk.Widget:
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        head.set_margin_top(12)
        head.set_margin_start(16); head.set_margin_end(16)
        head.set_margin_bottom(8)

        head.append(_glyph_label("\uf07a", NEON_PINK, size_pt=24))

        title = Gtk.Label(label="NYXUS App Store")
        title.add_css_class("nyx-rainbow-title")
        title.set_xalign(0); title.set_hexpand(True)
        head.append(title)

        # counts
        installed = sum(1 for e in CATALOG if _is_installed(e))
        total     = len(CATALOG)
        avail     = total - installed
        counts = Gtk.Label()
        counts.set_use_markup(True)
        counts.set_markup(
            f"<span foreground='{NEON_GREEN}'>{installed}</span> installed   "
            f"<span foreground='{NEON_PINK}'>{avail}</span> available   "
            f"<span foreground='{NEON_GOLD}'>{total}</span> total"
        )
        counts.add_css_class("nyx-store-counts")
        head.append(counts)
        self._counts_lbl = counts

        # search
        self._search = Gtk.SearchEntry()
        self._search.set_placeholder_text("Filter…")
        self._search.set_size_request(220, -1)
        self._search.connect("search-changed", lambda *_: self._on_search_changed())
        head.append(self._search)

        return head

    def _on_search_changed(self) -> None:
        self._search_text = (self._search.get_text() or "").strip().lower()
        self._refresh_grid()

    # ── body (scrollable: featured + categorized cards)
    def _build_body(self) -> Gtk.Widget:
        scroller = Gtk.ScrolledWindow()
        scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroller.set_vexpand(True); scroller.set_hexpand(True)

        self._content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._content.set_margin_bottom(8)
        scroller.set_child(self._content)
        self._refresh_grid()
        return scroller

    def _refresh_grid(self) -> None:
        # Clear current children
        child = self._content.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._content.remove(child)
            child = nxt

        # Featured (skip when searching)
        if not self._search_text:
            self._content.append(
                _build_featured(_featured_today(),
                                self._on_install, self._on_open)
            )

        # Categorized grid
        any_match = False
        for cat in CATEGORIES:
            entries = [
                e for e in CATALOG
                if e["category"] == cat and self._matches_search(e)
            ]
            if not entries:
                continue
            any_match = True
            self._content.append(self._cat_header(cat, len(entries)))
            self._content.append(self._cat_grid(entries))

        if not any_match:
            empty = Gtk.Label(label=f"No apps match \"{self._search_text}\".")
            empty.add_css_class("nyx-store-empty")
            self._content.append(empty)

        # Refresh the counts label too (installs may have changed state)
        if hasattr(self, "_counts_lbl"):
            installed = sum(1 for e in CATALOG if _is_installed(e))
            total     = len(CATALOG)
            avail     = total - installed
            self._counts_lbl.set_markup(
                f"<span foreground='{NEON_GREEN}'>{installed}</span> installed   "
                f"<span foreground='{NEON_PINK}'>{avail}</span> available   "
                f"<span foreground='{NEON_GOLD}'>{total}</span> total"
            )

    def _matches_search(self, entry: Dict[str, str]) -> bool:
        if not self._search_text:
            return True
        q = self._search_text
        return (
            q in entry["title"].lower()
            or q in entry["tagline"].lower()
            or q in entry["category"].lower()
            or q in entry["key"].lower()
        )

    def _cat_header(self, cat: str, count: int) -> Gtk.Widget:
        wrap = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        h = Gtk.Label(label=f"{cat.upper()}")
        h.add_css_class("nyx-store-cat-header")
        h.add_css_class(f"nyx-store-cat-header-{cat.lower()}")
        h.set_xalign(0)
        wrap.append(h)

        meta = Gtk.Label(label=f"· {count} app{'s' if count != 1 else ''}")
        meta.add_css_class("nyx-dim")
        meta.set_valign(Gtk.Align.CENTER)
        wrap.append(meta)
        wrap.set_margin_start(10)
        return wrap

    def _cat_grid(self, entries: List[Dict[str, str]]) -> Gtk.Widget:
        grid = Gtk.FlowBox()
        grid.set_max_children_per_line(CARD_COLS)
        grid.set_min_children_per_line(1)
        grid.set_selection_mode(Gtk.SelectionMode.NONE)
        grid.set_homogeneous(True)
        grid.set_row_spacing(0)
        grid.set_column_spacing(0)
        grid.set_margin_start(6); grid.set_margin_end(6)
        for e in entries:
            grid.append(_build_card(e, self._on_install, self._on_uninstall, self._on_open))
        return grid

    # ── action bar (footer)
    def _build_action_bar(self) -> Gtk.Widget:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.set_margin_top(6); bar.set_margin_bottom(10)
        bar.set_margin_start(16); bar.set_margin_end(16)
        bar.add_css_class("nyx-rainbow-row")

        spacer = Gtk.Label()
        spacer.set_hexpand(True)

        b_refresh = Gtk.Button(label="\uf021  Refresh")
        b_refresh.connect("clicked", lambda *_: self._refresh_grid())

        b_install_missing = Gtk.Button(label="\uf019  Install All Missing")
        b_install_missing.add_css_class("suggested-action")
        b_install_missing.connect("clicked", lambda *_: self._install_all_missing())

        b_close = Gtk.Button(label="\uf00d  Close")
        b_close.connect("clicked", lambda *_: self.close())

        bar.append(b_refresh)
        bar.append(spacer)
        bar.append(b_install_missing)
        bar.append(b_close)
        return bar

    # ── actions
    def _on_install(self, entry: Dict[str, str]) -> None:
        _spawn_installer(entry)
        # Auto-refresh after a delay so card flips to "Installed" if quick
        GLib.timeout_add_seconds(8, self._refresh_grid_once)

    def _on_uninstall(self, entry: Dict[str, str]) -> None:
        _uninstall(entry)
        GLib.timeout_add_seconds(3, self._refresh_grid_once)

    def _on_open(self, entry: Dict[str, str]) -> None:
        _open_app(entry)

    def _install_all_missing(self) -> None:
        missing = [e for e in CATALOG if not _is_installed(e)]
        if not missing:
            return
        # Build one terminal session that installs every missing app in order
        lines = ["echo '── installing all missing NYXUS apps ──'"]
        for e in missing:
            url = f"{NYXUS_BASE}/{e['installer']}"
            lines.append(f"echo; echo '── {e['title']} ──'; "
                         f"curl -fsSL {url} | sudo bash || echo '  (failed: {e['title']})'")
        lines.append("echo; echo '── all done. press Enter to close ──'; read")
        cmd = "; ".join(lines)
        _spawn_terminal("NYXUS · Installing missing apps", cmd)
        GLib.timeout_add_seconds(20, self._refresh_grid_once)

    def _refresh_grid_once(self) -> bool:
        self._refresh_grid()
        return False  # one-shot timer


# ─────────────────────────────────────────────── entry point ──
def main() -> int:
    if _toggle_singleton():
        return 0

    _write_pid()
    try:
        signal.signal(signal.SIGTERM, lambda *_: (_clear_pid(), os._exit(0)))

        app = Gtk.Application(application_id=APP_ID,
                              flags=Gio.ApplicationFlags.NON_UNIQUE)

        def _on_activate(_a):
            _install_css()
            win = StoreWindow(app)
            win.present()

        app.connect("activate", _on_activate)
        return app.run(None)
    finally:
        _clear_pid()


# ─────────────────────────── NYXUS CHROME (auto-injected) ───────────────────
# Unifies look across every NYXUS GTK4 app: DARK MIRROR glass, Inter Display
# font, DARK MIRROR palette. Monkey-patches BOTH Gtk.ApplicationWindow.present
# AND Adw.ApplicationWindow.present so the canonical install_chrome()
# runs once per top-level window — without touching the app's own
# window-construction code. install_chrome auto-detects Adw vs Gtk
# windows and uses set_content/get_content vs set_child/get_child
# accordingly. nyxus-panel and nyxus-start are intentionally excluded
# (LayerShell incompatibility with Gtk.Overlay). nyxus_chrome.py is
# shipped to ~/.nyxus by nyxus_install.sh.
try:
    import os as _nyx_os, sys as _nyx_sys
    _nyx_chrome_dir = _nyx_os.path.expanduser("~/.nyxus")
    if _nyx_chrome_dir not in _nyx_sys.path:
        _nyx_sys.path.insert(0, _nyx_chrome_dir)
    try:
        from nyxus_chrome import install_chrome as _nyx_install_chrome
    except ImportError:
        _nyx_install_chrome = lambda *a, **kw: None  # silent no-op
    _NYX_PAGE_KEY = "_store"
    def _nyx_make_present_hook(_orig):
        def _nyx_present(self):
            try: _nyx_install_chrome(self, page_key=_NYX_PAGE_KEY)
            except Exception: pass
            return _orig(self)
        return _nyx_present
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk as _NyxGtk
        if not getattr(_NyxGtk.ApplicationWindow, "_nyx_chrome_hooked", False):
            _NyxGtk.ApplicationWindow.present = _nyx_make_present_hook(
                _NyxGtk.ApplicationWindow.present)
            _NyxGtk.ApplicationWindow._nyx_chrome_hooked = True
    except Exception as _nyx_eg:
        import sys as _nyx_sys
        print("nyxus-chrome Gtk hook skipped: %s" % _nyx_eg, file=_nyx_sys.stderr)
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Adw", "1")
        from gi.repository import Adw as _NyxAdw
        if not getattr(_NyxAdw.ApplicationWindow, "_nyx_chrome_hooked", False):
            _NyxAdw.ApplicationWindow.present = _nyx_make_present_hook(
                _NyxAdw.ApplicationWindow.present)
            _NyxAdw.ApplicationWindow._nyx_chrome_hooked = True
    except Exception as _nyx_ea:
        if not isinstance(_nyx_ea, (ImportError, ValueError)):
            import sys as _nyx_sys
            print("nyxus-chrome Adw hook skipped: %s" % _nyx_ea, file=_nyx_sys.stderr)
except Exception as _nyx_e:
    import sys as _nyx_sys
    print("nyxus-chrome bootstrap skipped: %s" % _nyx_e, file=_nyx_sys.stderr)
# ────────────────────────── /NYXUS CHROME ───────────────────────────────────


if __name__ == "__main__":
    sys.exit(main())
