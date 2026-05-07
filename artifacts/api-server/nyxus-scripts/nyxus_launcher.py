#!/usr/bin/env python3
"""
NYXUS Launcher — system-wide app launcher (Spotlight/rofi replacement).

Fuzzy search across:
  • installed .desktop apps (XDG_DATA_DIRS scan)
  • PATH executables
  • shell commands (with the !cmd prefix)
  • web search (with the ?query prefix → opens xdg-open https://duckduckgo.com/?q=)

GTK4 + the unified NYXUS chrome (graffiti background, frosted glass,
rainbow-markup title, scrambling letters in headings).

Bind to a Hyprland keybind in ~/.config/hypr/hyprland.conf:
    bind = SUPER, Space, exec, python3 ~/.local/bin/nyxus_launcher.py

Esc closes. Enter launches selected. Up/Down navigate.
"""
from __future__ import annotations
import gi, os, sys, subprocess, shlex, configparser, time, threading, re
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio, Pango
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

NEON_PINK  = "#e8edf5"
NEON_BLUE  = "#00aaff"
NEON_GREEN = "#39ff14"
GOLD       = "#ffd700"


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
class Launcher(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.launcher",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self._all: list[dict] = []
        self._results: list[dict] = []
        self._selected = 0

    def do_activate(self):
        # CSS
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

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

        # ── header with rainbow title ────────────────────────────────
        title = Gtk.Label()
        title.set_markup(rainbow_markup("NYXUS LAUNCHER"))
        title.set_halign(Gtk.Align.START)
        title.add_css_class("nyxus-title")
        outer.append(title)

        # search row
        self.search = Gtk.Entry()
        self.search.set_placeholder_text(
            "type to search · !cmd shell · ?query web")
        self.search.add_css_class("nyxus-search")
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
        hint = Gtk.Label(label="↑↓ navigate · enter launch · esc close",
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
        row = Gtk.ListBoxRow()
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_margin_top(6); box.set_margin_bottom(6)
        box.set_margin_start(10); box.set_margin_end(10)
        # kind badge
        badge = Gtk.Label()
        emoji = {"app": "▢", "exec": "▶", "shell": "⌘",
                 "web": "◯"}.get(it["kind"], "•")
        badge.set_markup(f"<span foreground='{NEON_PINK}' "
                         f"font_weight='bold' size='large'>{emoji}</span>")
        badge.set_size_request(28, -1)
        box.append(badge)
        # name + comment
        v = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        nl = Gtk.Label(label=it["name"], xalign=0)
        nl.add_css_class("nyxus-name")
        v.append(nl)
        if it.get("comment"):
            cl = Gtk.Label(label=it["comment"][:96], xalign=0)
            cl.add_css_class("nyxus-cmt")
            v.append(cl)
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


# ── CSS — matches NYXUS chrome aesthetic ────────────────────────────────
CSS = """
window.nyxus-launcher {
    background: rgba(8, 6, 14, 0.78);
    border-radius: 6px;
}
.nyxus-title {
    font-family: 'Caveat', 'Patrick Hand', sans-serif;
    font-size: 28px;
    margin-bottom: 4px;
    text-shadow: 0 0 10px rgba(255, 0, 255, 0.45);
}
.nyxus-search {
    font-family: 'Caveat', 'Patrick Hand', sans-serif;
    font-size: 22px;
    background: rgba(15, 12, 24, 0.92);
    color: #ffffff;
    caret-color: #e8edf5;
    border: 2px solid rgba(255, 0, 255, 0.55);
    border-radius: 4px;
    padding: 10px 14px;
    box-shadow: 0 0 14px rgba(255, 0, 255, 0.25);
}
.nyxus-search:focus {
    border-color: #e8edf5;
    box-shadow: 0 0 22px rgba(255, 0, 255, 0.55);
}
.nyxus-list {
    background: rgba(8, 6, 14, 0.55);
    border: 1px solid rgba(255, 0, 255, 0.20);
    border-radius: 4px;
    padding: 4px;
}
.nyxus-list row {
    background: transparent;
    border-radius: 4px;
    padding: 0;
}
.nyxus-list row:selected {
    background: rgba(255, 0, 255, 0.22);
    box-shadow: inset 0 0 0 1px rgba(255, 0, 255, 0.45);
}
.nyxus-list row:hover {
    background: rgba(255, 0, 255, 0.12);
}
.nyxus-name {
    font-family: 'Caveat', 'Patrick Hand', sans-serif;
    font-size: 18px;
    color: #ffffff;
}
.nyxus-cmt {
    font-family: 'Caveat', sans-serif;
    font-size: 14px;
    color: rgba(255, 255, 255, 0.55);
}
.nyxus-hint {
    font-family: 'Caveat', sans-serif;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.42);
}
"""


if __name__ == "__main__":
    sys.exit(Launcher().run(sys.argv))
