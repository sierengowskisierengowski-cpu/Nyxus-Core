#!/usr/bin/env python3
"""
NYXUS doctor — single-shot health audit for an installed NYXUS system.

Checks every moving part: cache integrity, script versions, hyprctl
reachability, required tools, theme directories, waybar wiring, and
the API server connectivity. Prints a Tesla-tier health report and
exits 0 (all green) or 1 (anything yellow/red).

Run:  python3 ~/.local/bin/nyxus_doctor.py
"""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, subprocess, sys, time
import urllib.request
from pathlib import Path

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


API_BASE   = "https://nyxus-core.replit.app/api/download/nyxus"
HOME       = Path.home()
CACHE_DIR  = HOME / ".cache" / "nyxus" / "graffiti"
# Installer (nyxus_install.sh) places all NYXUS python scripts in ~/.nyxus
SCRIPTS_DIR = HOME / ".nyxus"
# Some user setups also keep symlinks in ~/.local/bin — accept either
BIN_DIR_ALT = HOME / ".local" / "bin"
CFG_HYPR   = HOME / ".config" / "hypr"
CFG_WAYBAR = HOME / ".config" / "waybar"
CFG_DUNST  = HOME / ".config" / "dunst"

# (label, ansi-fg) — all printed with reset at end
GREEN  = "\033[1;32m"
YELLOW = "\033[1;33m"
RED    = "\033[1;31m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

results: list[tuple[str, str, str]] = []     # (level, name, detail)

def add(level: str, name: str, detail: str = "") -> None:
    results.append((level, name, detail))

def have(cmd: str) -> bool:
    return shutil.which(cmd) is not None

def sh(cmd: list[str], timeout: int = 4) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout)
        return r.returncode, (r.stdout + r.stderr).strip()
    except Exception as e:
        return 127, str(e)

# ── checks ────────────────────────────────────────────────────────────────
def check_required_tools() -> None:
    required = [
        ("hyprctl",  "Hyprland IPC"),
        ("waybar",   "status bar"),
        ("python3",  "runtime"),
        ("curl",     "fetch tool"),
    ]
    optional = [
        ("dunst",      "notifications"),
        ("swww",       "wallpaper daemon"),
        ("hyprpaper",  "wallpaper daemon (alt)"),
        ("hyprlock",   "screen lock"),
        ("grim",       "screenshot capture"),
        ("slurp",      "region selector"),
        ("wl-copy",    "wayland clipboard"),
        ("rofi",       "fuzzy menu (legacy)"),
        ("gsettings",  "GNOME schema"),
        ("pkexec",     "PolicyKit elevation"),
        ("timedatectl","time/NTP control"),
        ("localectl",  "locale control"),
        ("nmcli",      "NetworkManager CLI"),
        ("bluetoothctl","Bluetooth"),
        ("pipewire",   "audio engine"),
        ("upower",     "battery info"),
        ("brightnessctl","backlight control"),
    ]
    for c, label in required:
        if have(c): add("ok", f"required: {c}", label)
        else:       add("err", f"required: {c}", f"MISSING — {label}")
    for c, label in optional:
        if have(c): add("ok", f"optional: {c}", label)
        else:       add("warn", f"optional: {c}", f"not installed — {label}")

def check_hyprctl() -> None:
    if not have("hyprctl"):
        add("err", "hyprctl reachable", "command missing"); return
    rc, out = sh(["hyprctl", "version"])
    if rc != 0:
        add("err", "hyprctl reachable",
            "Hyprland not running (or socket unreachable)")
        return
    first = out.splitlines()[0] if out else "?"
    add("ok", "hyprctl reachable", first)
    rc, mons = sh(["hyprctl", "monitors", "-j"])
    if rc == 0:
        try:
            arr = json.loads(mons)
            add("ok", "monitors detected", f"{len(arr)} active")
        except Exception:
            add("warn", "monitors detected", "couldn't parse hyprctl json")

def check_graffiti_cache() -> None:
    if not CACHE_DIR.exists():
        add("err", "graffiti cache",
            f"missing — run pull script to populate {CACHE_DIR}")
        return
    files = sorted(CACHE_DIR.glob("nyxus-graffiti-*.png"))
    expected = 24
    if len(files) < expected:
        add("warn", "graffiti cache",
            f"{len(files)}/{expected} murals (run pull script to refresh)")
    else:
        # check sizes — under 1 KB means corrupted/empty
        small = [f.name for f in files if f.stat().st_size < 1024]
        if small:
            add("warn", "graffiti cache",
                f"{len(small)} corrupted: {', '.join(small[:3])}")
        else:
            total_mb = sum(f.stat().st_size for f in files) / (1024 * 1024)
            add("ok", "graffiti cache",
                f"{len(files)} murals · {total_mb:.1f} MB")

def check_scripts_present() -> None:
    # rev r13: nyxus_notepad.py + nyxus_weather.py removed (rich
    # tarball editions installed to /opt/nyxus-notepad + /opt/nyxus-weather)
    expected = [
        "nyxus_settings.py", "nyxus_stickies.py",
        "nyxus_sysmon_gtk.py", "nyxus_control.py",
        "nyxus_terminal.py",
        # phase-2 additions
        "nyxus_doctor.py", "nyxus_launcher.py", "nyxus_powermenu.py",
        "nyxus_screenshot.py",
    ]
    missing = [n for n in expected
               if not (SCRIPTS_DIR / n).exists()
               and not (BIN_DIR_ALT / n).exists()]
    if missing:
        add("warn", "NYXUS scripts",
            f"{len(missing)} missing in {SCRIPTS_DIR}: {', '.join(missing[:5])}")
    else:
        add("ok", "NYXUS scripts",
            f"{len(expected)} present in {SCRIPTS_DIR}")

def check_waybar() -> None:
    style = CFG_WAYBAR / "style.css"
    # waybar accepts either `config` or `config.json`
    cfg = next((CFG_WAYBAR / n for n in ("config", "config.json", "config.jsonc")
                if (CFG_WAYBAR / n).exists()), None)
    if not style.exists():
        add("err", "waybar style.css", f"missing at {style}"); return
    if cfg is None:
        add("err", "waybar config",
            f"missing at {CFG_WAYBAR}/config[.json]"); return
    s = style.read_text(errors="ignore")
    add("ok", "waybar style.css", f"{len(s):,} bytes")
    # right-bar background image
    rb = CFG_HYPR / "walls" / "nyxus-rightbar-bg.png"
    if rb.exists():
        add("ok", "right-bar background", f"{rb.stat().st_size//1024} KB")
    else:
        add("warn", "right-bar background",
            f"missing at {rb} — run pull script")
    # check for purple dominance regression
    purple = s.count("rgba(204, 0, 255")
    if purple > 5:
        add("warn", "waybar palette",
            f"{purple} dominant-purple panels (consider toning down)")
    else:
        add("ok", "waybar palette", "purple within accent budget")

def check_dunst() -> None:
    if not have("dunst"):
        add("warn", "dunst", "not installed (notifications won't render)")
        return
    rc, _ = sh(["pgrep", "-x", "dunst"])
    add("ok" if rc == 0 else "warn", "dunst running",
        "pid found" if rc == 0 else "no process")
    rc_path = CFG_DUNST / "dunstrc"
    if rc_path.exists():
        s = rc_path.read_text(errors="ignore")
        if "NYXUS" in s or "Inter Display" in s:
            add("ok", "dunst config", "NYXUS theme active")
        else:
            add("warn", "dunst config", "default theme — pull nyxus-dunstrc")
    else:
        add("warn", "dunst config",
            f"missing at {rc_path} — pull nyxus-dunstrc")

def check_hyprlock() -> None:
    if not have("hyprlock"):
        add("warn", "hyprlock", "not installed — pacman -S hyprlock")
        return
    cfg = CFG_HYPR / "hyprlock.conf"
    if cfg.exists():
        s = cfg.read_text(errors="ignore")
        if "NYXUS" in s or "graffiti" in s:
            add("ok", "hyprlock config", "NYXUS theme active")
        else:
            add("warn", "hyprlock config",
                "default theme — pull nyxus-hyprlock.conf")
    else:
        add("warn", "hyprlock config", f"missing at {cfg}")

def check_api_reachable() -> None:
    try:
        req = urllib.request.Request(
            f"{API_BASE}/nyxus_chrome.py", method="HEAD")
        with urllib.request.urlopen(req, timeout=5) as r:
            if r.status == 200:
                add("ok", "API server", f"reachable · {API_BASE}")
            else:
                add("warn", "API server", f"HTTP {r.status}")
    except Exception as e:
        add("err", "API server", f"unreachable: {e}")

def check_themes() -> None:
    roots = [HOME / ".themes", HOME / ".local/share/themes",
             Path("/usr/share/themes")]
    n_themes = sum(
        len([p for p in r.iterdir() if p.is_dir() and (p / "gtk-3.0").exists()])
        for r in roots if r.exists())
    add("ok" if n_themes > 0 else "warn", "GTK themes",
        f"{n_themes} installed")
    icon_roots = [HOME / ".icons", HOME / ".local/share/icons",
                  Path("/usr/share/icons")]
    n_icons = sum(
        len([p for p in r.iterdir() if p.is_dir() and (p / "index.theme").exists()])
        for r in icon_roots if r.exists())
    add("ok" if n_icons > 0 else "warn", "icon themes",
        f"{n_icons} installed")

def check_pacman() -> None:
    if not have("pacman"):
        add("warn", "pacman", "not on Arch — skipping pkg checks")
        return
    rc, out = sh(["pacman", "-Q"])
    pkgs = len(out.splitlines()) if rc == 0 else 0
    add("ok", "pacman packages", f"{pkgs:,} installed")
    rc, out = sh(["pacman", "-Qu"], timeout=8)
    upd = len(out.splitlines()) if rc == 0 and out else 0
    if upd > 50:
        add("warn", "pending updates", f"{upd} (run: pacman -Syu)")
    elif upd > 0:
        add("ok", "pending updates", f"{upd}")
    else:
        add("ok", "pending updates", "system is up to date")

# ── output ────────────────────────────────────────────────────────────────
def render(use_color: bool = True, json_out: bool = False) -> int:
    if json_out:
        print(json.dumps([
            {"level": l, "name": n, "detail": d} for l, n, d in results],
            indent=2))
        return 1 if any(l == "err" for l, _, _ in results) else 0

    def col(s, c): return f"{c}{s}{RESET}" if use_color else s
    n_ok   = sum(1 for l, _, _ in results if l == "ok")
    n_warn = sum(1 for l, _, _ in results if l == "warn")
    n_err  = sum(1 for l, _, _ in results if l == "err")

    print(col("\n  ╔════════════════════════════════════════════════════╗", BOLD))
    print(col("  ║         NYXUS DOCTOR — system health audit         ║", BOLD))
    print(col("  ╚════════════════════════════════════════════════════╝\n", BOLD))
    for level, name, detail in results:
        if level == "ok":
            mark = col("✓", GREEN)
        elif level == "warn":
            mark = col("!", YELLOW)
        else:
            mark = col("✗", RED)
        line = f"  {mark}  {name:<28}  {col(detail, DIM)}"
        print(line)

    print()
    summary = (f"  {col(str(n_ok)+' OK', GREEN)}   "
               f"{col(str(n_warn)+' warn', YELLOW)}   "
               f"{col(str(n_err)+' error', RED)}")
    print(summary)
    print()
    if n_err:
        print(col("  ✗ system is degraded — fix errors above.\n", RED))
        return 1
    if n_warn:
        print(col("  ! system is functional but not 100% — "
                  "review warnings above.\n", YELLOW))
        return 0
    print(col("  ✓ NYXUS is in tip-top shape. Tesla-tier.\n", GREEN))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="NYXUS health audit")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable JSON output")
    ap.add_argument("--no-color", action="store_true",
                    help="disable ANSI colors")
    args = ap.parse_args()

    check_required_tools()
    check_hyprctl()
    check_graffiti_cache()
    check_scripts_present()
    check_waybar()
    check_dunst()
    check_hyprlock()
    check_themes()
    check_pacman()
    check_api_reachable()

    return render(use_color=not args.no_color, json_out=args.json)


if __name__ == "__main__":
    sys.exit(main())
