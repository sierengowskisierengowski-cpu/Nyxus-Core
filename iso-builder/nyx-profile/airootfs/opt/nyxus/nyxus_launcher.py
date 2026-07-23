#!/usr/bin/env python3
"""
NYXUS Launcher — system-wide app launcher (Spotlight/rofi replacement).

Fuzzy search across:
  • installed .desktop apps (XDG_DATA_DIRS scan)
  • PATH executables
  • shell commands (with the !cmd prefix)
  • web search (with the ?query prefix → opens xdg-open https://duckduckgo.com/?q=)
  • calculator (with the =expr prefix, or auto-detect math input)
  • file search (with the /query prefix — fd if available, else find)
  • system actions (with the >action prefix: lock/logout/reboot/shutdown/suspend)

GTK4 + the unified NYXUS chrome (DARK MIRROR + warm gold accent for
alive states), monochrome dominant.

Bind to a Hyprland keybind in ~/.config/hypr/hyprland.conf:
    bind = SUPER, Space, exec, python3 ~/.local/bin/nyxus_launcher.py

Esc closes. Enter launches selected. Up/Down navigate.
"""
from __future__ import annotations
import gi, os, sys, subprocess, shlex, configparser, time, threading, re, ast, operator

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
        ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_WARN, ACCENT_OK,
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
    ACCENT_PRIMARY='#ff2dad'; ACCENT_SECONDARY='#2bd2ff'
    ACCENT_WARN='#ffb84d'; ACCENT_OK='#7d3dff'
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
            'ACCENT_PRIMARY': ACCENT_PRIMARY,
            'ACCENT_SECONDARY': ACCENT_SECONDARY,
            'ACCENT_WARN': ACCENT_WARN, 'ACCENT_OK': ACCENT_OK,
        }
        return t.format_map(_d)
    def assert_no_forbidden(*a, **k): pass
# ─────────────────────────────────────────────────────────────────────

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, GLib, Gio, Pango, Adw
from pathlib import Path

# Pull NYXUS chrome (frosted graffiti background + rainbow markup helpers).
sys.path.insert(0, str(Path.home() / ".local" / "bin"))
try:
    from nyxus_chrome import install_chrome, rainbow_markup  # type: ignore
    HAS_CHROME = True
except Exception:
    HAS_CHROME = False
    def install_chrome(win, key="_launcher"): return None  # noqa: E704
    def rainbow_markup(s: str) -> str:                    # noqa: E704
        return f"<span foreground='#e8edf5' font_weight='bold'>{s}</span>"

WIN_W, WIN_H = 720, 520
MAX_RESULTS  = 40

# HUD neon family (accent.json-live via nyxus_palette.HUD_PALETTE).
try:
    from nyxus_palette import HUD_PALETTE, hud_css_bundle, install_hud_css
except Exception:
    HUD_PALETTE = {"pink": ACCENT_PRIMARY, "cyan": ACCENT_SECONDARY,
                   "gold": ACCENT_WARN, "purple": ACCENT_OK,
                   "green": "#7dff5e", "orange": "#ff7849",
                   "blue": "#4d9fff", "red": "#ff4d6b",
                   "mono": WHITE_OFF}
    def hud_css_bundle(sel="window", hues=()):  # noqa: E704
        return ""
    install_hud_css = None

NEON_PINK  = HUD_PALETTE["pink"]
NEON_BLUE  = HUD_PALETTE["cyan"]
NEON_GREEN = HUD_PALETTE["green"]
GOLD       = HUD_PALETTE["gold"]

# Result-category → HUD hue (mirrors the per-card hues of the HOME HUD).
KIND_HUE = {
    "app":   "pink",
    "exec":  "cyan",
    "shell": "gold",
    "web":   "blue",
    "calc":  "green",
    "file":  "orange",
    "sys":   "red",
}
KIND_GLYPH = {
    "app": "▢", "exec": "▶", "shell": "⌘",
    "web": "◯", "calc": "=", "file": "▤", "sys": "◈",
}
KIND_LABEL = {
    "app": "APP", "exec": "BIN", "shell": "SH",
    "web": "WEB", "calc": "CALC", "file": "FILE", "sys": "SYS",
}


def have(cmd: str) -> bool:
    return any((Path(p) / cmd).exists() for p in os.environ.get(
        "PATH", "/usr/bin:/usr/local/bin").split(":"))


# ── data sources ─────────────────────────────────────────────────────────
def desktop_dirs() -> list[Path]:
    roots = [Path.home() / ".local/share/applications"]
    xdg = os.environ.get("XDG_DATA_DIRS",
                         "/usr/local/share:/usr/share").split(":")
    for r in xdg:
        roots.append(Path(r) / "applications")
    return [r for r in roots if r.exists()]


_FIELD_CODE_RE = re.compile(r"%[fFuUdDnNickvm]")

def parse_desktop(p: Path) -> dict | None:
    try:
        cp = configparser.ConfigParser(interpolation=None, strict=False)
        cp.read(p, encoding="utf-8")
        if "Desktop Entry" not in cp: return None
        e = cp["Desktop Entry"]
        if e.get("NoDisplay", "false").lower() == "true": return None
        if e.get("Hidden", "false").lower() == "true": return None
        if e.get("Type", "Application") != "Application": return None
        name = e.get("Name", p.stem)
        exec_s = e.get("Exec", "").strip()
        if not exec_s: return None
        # strip XDG field codes (%f, %F, %u, %U, %i, %c, %k, etc.)
        exec_s = _FIELD_CODE_RE.sub("", exec_s).strip()
        # parse to argv NOW so launch is shell-free
        try:
            argv = shlex.split(exec_s, posix=True)
        except ValueError:
            return None
        if not argv: return None
        return {
            "kind":    "app",
            "name":    name,
            "argv":    argv,             # safe argv form (no shell)
            "exec":    exec_s,           # display only
            "icon":    e.get("Icon", "application-x-executable"),
            "comment": e.get("Comment", ""),
            "term":    e.get("Terminal", "false").lower() == "true",
            "path":    str(p),
        }
    except Exception:
        return None


def scan_apps() -> list[dict]:
    seen = {}
    for d in desktop_dirs():
        try:
            for f in d.glob("*.desktop"):
                e = parse_desktop(f)
                if e: seen.setdefault(e["name"], e)
        except Exception:
            pass
    return sorted(seen.values(), key=lambda x: x["name"].lower())


def scan_path_execs(limit: int = 4000) -> list[dict]:
    """Scan PATH for executables. Capped to keep startup snappy on
    systems with huge PATHs (anaconda, nix, etc.)."""
    seen: dict[str, dict] = {}
    for p in os.environ.get("PATH", "").split(":"):
        if not p: continue
        d = Path(p)
        if not d.is_dir(): continue
        try:
            for f in d.iterdir():
                if not f.is_file(): continue
                if not os.access(f, os.X_OK): continue
                seen.setdefault(f.name, {
                    "kind": "exec", "name": f.name,
                    "argv": [str(f)],
                    "exec": str(f),
                    "comment": str(f), "icon": "utilities-terminal",
                    "term": False,
                })
                if len(seen) >= limit: break
        except Exception:
            pass
        if len(seen) >= limit: break
    return sorted(seen.values(), key=lambda x: x["name"].lower())


# ── calculator (safe AST eval, no exec) ──────────────────────────────────
_CALC_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.Mod: operator.mod, ast.Pow: operator.pow,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}
_CALC_MATH_RE = re.compile(r"^[\d\s\.\+\-\*\/\(\)\%\^]+$")

def _calc_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _CALC_OPS:
        return _CALC_OPS[type(node.op)](_calc_eval(node.left),
                                        _calc_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _CALC_OPS:
        return _CALC_OPS[type(node.op)](_calc_eval(node.operand))
    raise ValueError("unsupported expression")

def safe_calc(expr: str):
    """Return (value, formatted_str) or (None, None)."""
    s = expr.strip().replace("^", "**").replace("×", "*").replace("÷", "/")
    if not s: return (None, None)
    try:
        tree = ast.parse(s, mode="eval")
        v = _calc_eval(tree.body)
    except Exception:
        return (None, None)
    if isinstance(v, float):
        if v.is_integer():
            disp = str(int(v))
        else:
            disp = f"{v:.10g}"
    else:
        disp = str(v)
    return (v, disp)


# ── file search (tracker3 → fd → find, in that order) ────────────────────
# tracker3 gives us full-text and metadata (titles, EXIF, ID3, PDF body)
# in O(1) once the index is warm — that's the macOS Spotlight feel. fd
# is the live filesystem walk fallback (fast on cold caches and on dirs
# tracker3 wasn't told to index). find is the universal last resort.
def search_files(query: str, limit: int = 30) -> list[dict]:
    if not query: return []
    home = str(Path.home())
    out: list[str] = []
    if have("tracker3"):
        # `tracker3 search -f --limit N -- <q>` returns one file URI per
        # line. We strip the "file://" prefix and decode percent-escapes.
        try:
            from urllib.parse import unquote, urlparse
            r = subprocess.run(
                ["tracker3", "search", "-f", "--limit", str(limit),
                 "--", query],
                capture_output=True, text=True, timeout=2)
            for ln in r.stdout.splitlines():
                ln = ln.strip()
                if ln.startswith("file://"):
                    out.append(unquote(urlparse(ln).path))
                elif ln.startswith("/"):
                    out.append(ln)
            out = out[:limit]
        except Exception:
            out = []
    if not out and have("fd"):
        try:
            r = subprocess.run(
                ["fd", "--hidden", "--no-ignore-vcs", "-t", "f",
                 "--max-results", str(limit), query, home],
                capture_output=True, text=True, timeout=2)
            out = [l for l in r.stdout.splitlines() if l]
        except Exception:
            out = []
    if not out:
        try:
            r = subprocess.run(
                ["find", home, "-maxdepth", "6", "-type", "f",
                 "-iname", f"*{query}*"],
                capture_output=True, text=True, timeout=2)
            out = [l for l in r.stdout.splitlines() if l][:limit]
        except Exception:
            out = []
    items = []
    for p in out:
        items.append({
            "kind": "file", "name": Path(p).name,
            "argv": ["xdg-open", p],
            "exec": f"xdg-open {p}",
            "comment": p, "icon": "text-x-generic", "term": False,
        })
    return items


# ── system actions ───────────────────────────────────────────────────────
def system_actions() -> list[dict]:
    """Built-in NYXUS power/session actions."""
    return [
        {"kind": "sys", "name": "Lock screen",
         "argv": ["sh", "-c",
                  "command -v hyprlock >/dev/null && hyprlock "
                  "|| loginctl lock-session"],
         "exec": "lock", "comment": "hyprlock / loginctl lock-session",
         "icon": "system-lock-screen", "term": False},
        {"kind": "sys", "name": "Suspend",
         "argv": ["systemctl", "suspend"],
         "exec": "systemctl suspend", "comment": "sleep, keep RAM",
         "icon": "system-suspend", "term": False},
        {"kind": "sys", "name": "Hibernate",
         "argv": ["systemctl", "hibernate"],
         "exec": "systemctl hibernate", "comment": "save RAM to disk, power off",
         "icon": "system-suspend-hibernate", "term": False},
        {"kind": "sys", "name": "Log out",
         "argv": ["sh", "-c",
                  "hyprctl dispatch exit 2>/dev/null "
                  "|| loginctl terminate-user $USER"],
         "exec": "logout", "comment": "end Hyprland session",
         "icon": "system-log-out", "term": False},
        {"kind": "sys", "name": "Reboot",
         "argv": ["systemctl", "reboot"],
         "exec": "systemctl reboot", "comment": "restart system",
         "icon": "system-reboot", "term": False},
        {"kind": "sys", "name": "Shutdown",
         "argv": ["systemctl", "poweroff"],
         "exec": "systemctl poweroff", "comment": "power off",
         "icon": "system-shutdown", "term": False},
        {"kind": "sys", "name": "Open NYXUS Settings",
         "argv": ["sh", "-c",
                  "command -v nyxus_settings.py >/dev/null && nyxus_settings.py "
                  "|| xdg-open about:settings"],
         "exec": "nyxus_settings.py", "comment": "control panel",
         "icon": "preferences-system", "term": False},
        {"kind": "sys", "name": "Open Security Center",
         "argv": ["sh", "-c",
                  "command -v nyxus-security >/dev/null && nyxus-security "
                  "|| python3 ~/.nyxus/nyxus_security.py"],
         "exec": "nyxus-security",
         "comment": "firewall, virus, encryption, panic",
         "icon": "security-high", "term": False},
        {"kind": "sys", "name": "Run quick virus scan",
         "argv": ["sh", "-c",
                  "command -v nyxus-security >/dev/null && nyxus-security --quick-scan "
                  "|| python3 ~/.nyxus/nyxus_security.py --quick-scan"],
         "exec": "nyxus-security --quick-scan",
         "comment": "ClamAV scan of $HOME and /tmp",
         "icon": "security-medium", "term": False},
        {"kind": "sys", "name": "Engage PANIC lockdown",
         "argv": ["sh", "-c",
                  "command -v nyxus-security >/dev/null && nyxus-security --panic "
                  "|| python3 ~/.nyxus/nyxus_security.py --panic"],
         "exec": "nyxus-security --panic",
         "comment": "lock + clear clipboard + dismount + flush DNS",
         "icon": "security-low", "term": False},
    ]


# ── fuzzy matching ───────────────────────────────────────────────────────
def fuzzy_score(needle: str, hay: str) -> int:
    """Return higher = better match. 0 = no match."""
    if not needle: return 1
    needle = needle.lower(); hay = hay.lower()
    if needle == hay: return 10_000
    if hay.startswith(needle): return 5_000 - len(hay)
    if needle in hay: return 2_000 - hay.index(needle) - len(hay)
    # subsequence match
    i = 0
    for ch in hay:
        if i < len(needle) and ch == needle[i]: i += 1
    return 1_000 - len(hay) if i == len(needle) else 0


# ── window ───────────────────────────────────────────────────────────────
class Launcher(Adw.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.launcher",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        try: Adw.init()
        except Exception: pass
        self._all: list[dict] = []
        self._results: list[dict] = []
        self._selected = 0

    def do_activate(self):
        # Force dark theme to match NYXUS DARK MIRROR aesthetic
        try:
            sm = Adw.StyleManager.get_default()
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        except Exception: pass
        # CSS — PRIORITY_USER + 1 so the HUD language outranks the
        # universal nyxus_chrome glass layer (PRIORITY_USER). At the old
        # APPLICATION priority the chrome flattened every card back to
        # monochrome and the launcher kept its legacy look.
        if install_hud_css is None or not install_hud_css(CSS):
            prov = Gtk.CssProvider()
            prov.load_from_data(CSS.encode("utf-8"))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(), prov,
                Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)

        self.win = Gtk.ApplicationWindow(application=self,
                                         title="NYXUS Launcher")
        self.win.set_default_size(WIN_W, WIN_H)
        self.win.set_decorated(False)
        self.win.set_resizable(False)
        self.win.add_css_class("nyxus-launcher")

        # NYXUS unified chrome (graffiti + frosted glass behind everything)
        if HAS_CHROME:
            try: install_chrome(self.win, key="_launcher")
            except Exception: pass

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_top(18); outer.set_margin_bottom(18)
        outer.set_margin_start(20); outer.set_margin_end(20)
        self.win.set_child(outer)

        # ── HUD header: glyph + small-caps neon title + stamp + rule ──
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        glyph = Gtk.Label(label="◈")
        glyph.add_css_class("hud-glyph-pink")
        head.append(glyph)
        # spray-paint wordmark (graffiti voice) + small-caps mono echo
        title = Gtk.Label(label="Launcher")
        title.add_css_class("hud-spray-pink")
        title.add_css_class("neon-flicker")
        head.append(title)
        echo = Gtk.Label(label="SPOTLIGHT")
        echo.add_css_class("hud-title-cyan")
        echo.add_css_class("neon-flicker-slow")
        echo.set_valign(Gtk.Align.END)
        echo.set_margin_bottom(4)
        head.append(echo)
        spacer = Gtk.Box(); spacer.set_hexpand(True)
        head.append(spacer)
        stamp = Gtk.Label(label="NYX · SUPER+SPACE")
        stamp.add_css_class("hud-stamp")
        head.append(stamp)
        outer.append(head)
        rule = Gtk.Box()
        rule.add_css_class("hud-rule-pink")
        rule.set_margin_top(6)
        outer.append(rule)

        # search row
        self.search = Gtk.Entry()
        self.search.set_placeholder_text(
            "search · =calc · /files · ?web · !shell · >system")
        self.search.add_css_class("nyxus-search")
        self.search.add_css_class("hud-input-pink")
        self.search.set_margin_top(10); self.search.set_margin_bottom(10)
        self.search.connect("changed", self._on_changed)
        self.search.connect("activate", lambda _e: self._launch_selected())
        outer.append(self.search)

        # results list
        self.scroll = Gtk.ScrolledWindow()
        self.scroll.set_policy(Gtk.PolicyType.NEVER,
                               Gtk.PolicyType.AUTOMATIC)
        self.scroll.set_vexpand(True)
        self.list = Gtk.ListBox()
        self.list.add_css_class("nyxus-list")
        self.list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list.connect("row-activated",
                          lambda _l, _r: self._launch_selected())
        self.scroll.set_child(self.list)
        outer.append(self.scroll)

        # footer hint
        hint = Gtk.Label(
            label="↑↓ navigate · enter launch · esc close · "
                  "= calc · / files · ? web · ! shell · > system",
            xalign=0)
        hint.add_css_class("nyxus-hint")
        hint.set_margin_top(8)
        outer.append(hint)

        # ── input ────────────────────────────────────────────────────
        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed", self._on_key)
        kc.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.win.add_controller(kc)

        # focus search immediately
        GLib.idle_add(lambda: (self.search.grab_focus(), False)[1])

        # background load + initial render
        GLib.idle_add(self._load_data)
        self.win.present()

    # ── data ────────────────────────────────────────────────────────────
    def _load_data(self):
        # Apps are fast (small set), load synchronously so user sees
        # results immediately. PATH scan can be slow on huge PATHs, so
        # do it in a background thread and merge when it lands.
        self._all = scan_apps()
        self._refresh()
        threading.Thread(target=self._load_path_async,
                         daemon=True).start()
        return False

    def _load_path_async(self):
        execs = scan_path_execs()
        # merge on the GTK main thread
        def merge():
            names = {it["name"] for it in self._all}
            self._all += [e for e in execs if e["name"] not in names]
            self._refresh()
            return False
        GLib.idle_add(merge)

    # ── search/refresh ──────────────────────────────────────────────────
    def _on_changed(self, _entry):
        self._refresh()

    def _refresh(self):
        q = self.search.get_text().strip()
        items: list[tuple[int, dict]] = []

        if q.startswith("!"):
            cmd = q[1:].strip()
            if cmd:
                items.append((10_000, {
                    "kind": "shell", "name": f"Run: {cmd}",
                    "argv": ["sh", "-c", cmd],
                    "exec": cmd, "comment": "shell command",
                    "icon": "utilities-terminal", "term": True,
                }))
        elif q.startswith("?"):
            qq = q[1:].strip() or "nyxus"
            url = f"https://duckduckgo.com/?q={qq.replace(' ', '+')}"
            items.append((10_000, {
                "kind": "web", "name": f"Search web: {qq}",
                "argv": ["xdg-open", url],
                "exec": f"xdg-open {url}",
                "comment": url, "icon": "applications-internet", "term": False,
            }))
        elif q.startswith("="):
            expr = q[1:].strip()
            v, disp = safe_calc(expr)
            if disp is not None:
                items.append((10_000, {
                    "kind": "calc", "name": f"= {disp}",
                    "argv": ["sh", "-c",
                             f"printf %s {shlex.quote(disp)} | "
                             "wl-copy 2>/dev/null || "
                             f"printf %s {shlex.quote(disp)} | xclip -sel clip"],
                    "exec": f"copy {disp}",
                    "comment": f"{expr}  →  press Enter to copy",
                    "icon": "accessories-calculator", "term": False,
                }))
            else:
                items.append((10_000, {
                    "kind": "calc", "name": "= (invalid expression)",
                    "argv": ["true"], "exec": "noop",
                    "comment": "supports + - * / % ** ( )",
                    "icon": "accessories-calculator", "term": False,
                }))
        elif q.startswith("/"):
            qq = q[1:].strip()
            for f in search_files(qq):
                items.append((9_000, f))
        elif q.startswith(">"):
            qq = q[1:].strip().lower()
            for a in system_actions():
                s = fuzzy_score(qq, a["name"]) if qq else 5_000
                if s > 0:
                    items.append((s, a))
        elif _CALC_MATH_RE.match(q) and any(op in q for op in "+-*/^%"):
            # Auto-detect: pure-math input with at least one operator
            # acts as if user typed "=expr".
            v, disp = safe_calc(q)
            if disp is not None:
                items.append((10_000, {
                    "kind": "calc", "name": f"= {disp}",
                    "argv": ["sh", "-c",
                             f"printf %s {shlex.quote(disp)} | "
                             "wl-copy 2>/dev/null || "
                             f"printf %s {shlex.quote(disp)} | xclip -sel clip"],
                    "exec": f"copy {disp}",
                    "comment": f"{q}  →  Enter to copy",
                    "icon": "accessories-calculator", "term": False,
                }))
            # also fall through to apps below for short queries like "1+1"
            for it in self._all:
                s = fuzzy_score(q, it["name"])
                if s > 0:
                    items.append((s, it))
        else:
            for it in self._all:
                s = max(fuzzy_score(q, it["name"]),
                        int(fuzzy_score(q, it.get("comment", "")) * 0.6))
                if s > 0:
                    items.append((s, it))

        items.sort(key=lambda x: -x[0])
        self._results = [it for _, it in items[:MAX_RESULTS]]
        # rebuild list
        c = self.list.get_first_child()
        while c:
            n = c.get_next_sibling(); self.list.remove(c); c = n
        for it in self._results:
            self.list.append(self._row(it))
        self._selected = 0
        if self._results:
            self.list.select_row(self.list.get_row_at_index(0))

    def _row(self, it: dict) -> Gtk.ListBoxRow:
        hue = KIND_HUE.get(it["kind"], "pink")
        color = HUD_PALETTE.get(hue, NEON_PINK)
        row = Gtk.ListBoxRow()
        row.add_css_class(f"nyxus-row-{hue}")
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(7); box.set_margin_bottom(7)
        box.set_margin_start(10); box.set_margin_end(12)
        # neon kind badge: glyph + small-caps category tag in its hue
        badge = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        g = Gtk.Label()
        g.set_markup(f"<span foreground='{color}' font_weight='bold' "
                     f"size='large'>{KIND_GLYPH.get(it['kind'], '•')}</span>")
        g.add_css_class(f"hud-glyph-{hue}")
        badge.append(g)
        tag = Gtk.Label()
        tag.set_markup(
            f"<span foreground='{color}' size='6800' "
            f"font_family='JetBrains Mono' font_weight='bold' "
            f"letter_spacing='2048'>{KIND_LABEL.get(it['kind'], '·')}</span>")
        badge.append(tag)
        badge.set_size_request(44, -1)
        box.append(badge)
        # name + comment
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        v.set_valign(Gtk.Align.CENTER)
        nl = Gtk.Label(label=it["name"], xalign=0)
        nl.add_css_class("nyxus-name")
        nl.set_ellipsize(Pango.EllipsizeMode.END)
        v.append(nl)
        if it.get("comment"):
            cl = Gtk.Label(label=it["comment"][:96], xalign=0)
            cl.add_css_class("nyxus-cmt")
            cl.set_ellipsize(Pango.EllipsizeMode.END)
            v.append(cl)
        v.set_hexpand(True)
        box.append(v)
        row.set_child(box)
        return row

    # ── input ──────────────────────────────────────────────────────────
    def _on_key(self, _ctl, keyval, _kc, _state):
        if keyval == Gdk.KEY_Escape:
            self.quit(); return True
        if keyval == Gdk.KEY_Down:
            self._move(+1); return True
        if keyval == Gdk.KEY_Up:
            self._move(-1); return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self._launch_selected(); return True
        return False

    def _move(self, delta: int):
        if not self._results: return
        self._selected = max(0, min(len(self._results) - 1,
                                    self._selected + delta))
        row = self.list.get_row_at_index(self._selected)
        if row:
            self.list.select_row(row)
            row.grab_focus()
            self.search.grab_focus()  # keep typing focus

    def _launch_selected(self):
        if not self._results: return
        it = self._results[self._selected]
        self._spawn(it)
        self.quit()

    def _spawn(self, it: dict):
        # Always launch via argv (no shell=True). Desktop Exec was
        # already split with shlex at parse time. The only "shell"
        # path is the explicit !cmd entry, whose argv is ["sh","-c",…]
        # — that is the user's deliberate intent.
        argv = it.get("argv") or []
        if not argv:
            print("launch error: empty argv", file=sys.stderr); return
        try:
            if it.get("term"):
                term = (os.environ.get("TERMINAL")
                        or ("nyxus_terminal.py" if have("nyxus_terminal.py")
                            else "alacritty"))
                subprocess.Popen([term, "-e", *argv],
                                 start_new_session=True)
            else:
                subprocess.Popen(argv, start_new_session=True)
        except FileNotFoundError as e:
            print(f"launch error (not found): {e}", file=sys.stderr)
        except Exception as e:
            print(f"launch error: {e}", file=sys.stderr)


# ── CSS — HOME HUD visual language, composed from the shared
#    nyxus_palette HUD helpers (single source; no duplicated card CSS).
#    Window = one big neon HUD card; every result category wears its
#    own hue like the HUD cards do (pink/cyan/gold/blue/green/orange/red).
def _launcher_css() -> str:
    pink = HUD_PALETTE["pink"]
    css = hud_css_bundle("window.nyxus-launcher", ("pink",))
    css += format_css("""
window.nyxus-launcher {{
    background: rgba(7, 5, 14, 0.95);
    border: 1px dashed alpha(@PINK@, 0.75);
    border-top: 2px solid @PINK@;
    border-radius: 8px;
    box-shadow: 0 0 30px alpha(@PINK@, 0.40),
                0 10px 34px rgba(0,0,0,0.65);
}}
.nyxus-search {{
    font-family: '{FONT_MONO}', monospace;
    font-size: 20px;
    color: {WHITE_PURE};
    caret-color: @PINK@;
    padding: 10px 14px;
}}
.nyxus-list {{
    background: rgba(0, 0, 0, 0.35);
    border: 1px dashed alpha({WHITE_OFF}, 0.13);
    border-radius: 4px;
    padding: 4px;
}}
.nyxus-list row {{
    background: transparent;
    border-radius: 3px;
    border-left: 3px solid transparent;
    padding: 0;
}}
.nyxus-list row:hover {{
    background: rgba(255, 255, 255, 0.04);
}}
.nyxus-name {{
    font-family: 'Inter Display', cursive;
    font-size: 18px;
    color: {WHITE_OFF};
    letter-spacing: 0.02em;
}}
.nyxus-cmt {{
    font-family: '{FONT_MONO}', monospace;
    font-size: 10px;
    color: {GREY_MID};
    letter-spacing: 0.06em;
}}
.nyxus-hint {{
    font-family: '{FONT_MONO}', monospace;
    font-size: 9px;
    color: {GREY_MID};
    letter-spacing: 0.14em;
}}
""").replace("@PINK@", pink)
    # Per-category row hues — selected row becomes a glowing slab in
    # the category's neon, exactly like an active HUD card.
    for kind, hue in KIND_HUE.items():
        c = HUD_PALETTE.get(hue, pink)
        css += f"""
.nyxus-list row.nyxus-row-{hue}:selected {{
    background: alpha({c}, 0.10);
    border-left: 3px solid {c};
    box-shadow: inset 0 0 0 1px alpha({c}, 0.30),
                0 0 16px alpha({c}, 0.25);
}}
.nyxus-list row.nyxus-row-{hue}:selected .nyxus-name {{
    color: {c};
    text-shadow: 0 0 8px alpha({c}, 0.45);
}}
"""
        # glyph header css per hue for the badges
        css += hud_header_css(hue, c) if hue != "pink" else ""
    return css

try:
    from nyxus_palette import hud_header_css
except Exception:
    def hud_header_css(n, c):  # noqa: E704
        return ""

CSS = _launcher_css()


if __name__ == "__main__":
    sys.exit(Launcher().run(sys.argv))

# ── palette guard (rev r13) ─────────────────────────────────────────
try: assert_no_forbidden(CSS, __file__)
except Exception as _e: import sys; sys.stderr.write(str(_e)+chr(10))
