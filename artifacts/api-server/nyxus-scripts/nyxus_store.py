#!/usr/bin/env python3
"""
NYXUS App Store — Settings-style libadwaita package manager GUI.

DARK MIRROR rev r1 · 2026-05-12

Sections (Adw.NavigationSplitView sidebar):
    Featured       Curated NYXUS picks (one-click install)
    Installed      pacman -Qe (explicitly installed) + paccache stats
    Updates        checkupdates + paru/yay -Qua + flatpak remote-ls --updates
    Search         pacman -Ss + paru/yay -Ss + flatpak search (live, debounced)
    Repositories   /etc/pacman.conf [repo] + flatpak remotes (read-only)
    About          Version + backend availability matrix

Backends (auto-detected, gracefully missing):
    pacman       (always present on Arch — required)
    paru / yay   (AUR helper — optional, first-found wins)
    flatpak      (flatpak hub — optional)
    checkupdates (pacman-contrib — optional, falls back to `pacman -Qu`)

Privilege escalation: every install/uninstall/update goes through `pkexec`
so the user gets a polkit prompt instead of us silently failing.
DRY_RUN: set NYXUS_DRY_RUN=1 to print commands instead of executing.

Every section honors §9: empty states are explicit ("No updates" / "No
matches" / "No AUR helper installed — install paru or yay") rather than
blank panels.

© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, GLib, Gio, Pango, Adw  # noqa: E402

# ── NYXUS shared chrome (rainbow titles + graffiti walls, system-wide) ──
sys.path.insert(0, str(Path.home() / ".local" / "bin"))
sys.path.insert(0, "/opt/nyxus")
try:
    from nyxus_chrome import install_chrome  # type: ignore
    HAS_CHROME = True
except Exception:
    HAS_CHROME = False

APP_ID = "io.nyxus.store"
DRY_RUN = os.environ.get("NYXUS_DRY_RUN") == "1"

# ════════════════════════════════════════════════════════════════════════════
#  Backend detection
# ════════════════════════════════════════════════════════════════════════════

def _which(name: str) -> Optional[str]:
    return shutil.which(name)

AUR_HELPER = _which("paru") or _which("yay")  # first-found wins
HAS_PACMAN = bool(_which("pacman"))
HAS_FLATPAK = bool(_which("flatpak"))
HAS_CHECKUPDATES = bool(_which("checkupdates"))
HAS_PKEXEC = bool(_which("pkexec"))

# Curated featured list — apps we want to recommend by default. Keep
# small + universally useful. Each tuple: (pkg, repo, display, blurb).
FEATURED = [
    ("firefox",         "extra",   "Firefox",          "Fast, private web browser from Mozilla."),
    ("thunderbird",     "extra",   "Thunderbird",      "Email, calendar, and chat client."),
    ("libreoffice-fresh","extra",  "LibreOffice",      "Full office suite — Writer, Calc, Impress."),
    ("gimp",            "extra",   "GIMP",             "Professional raster image editor."),
    ("inkscape",        "extra",   "Inkscape",         "Vector graphics editor — SVG-native."),
    ("blender",         "extra",   "Blender",          "3D modeling, animation, and rendering."),
    ("vlc",             "extra",   "VLC",              "Plays virtually every audio and video format."),
    ("obs-studio",      "extra",   "OBS Studio",       "Live streaming and screen recording."),
    ("krita",           "extra",   "Krita",            "Digital painting tailored for artists."),
    ("audacity",        "extra",   "Audacity",         "Multi-track audio editor and recorder."),
    ("code",            "extra",   "VS Code (OSS)",    "Microsoft's open-source code editor."),
    ("kdenlive",        "extra",   "Kdenlive",         "Non-linear video editor."),
]

# ════════════════════════════════════════════════════════════════════════════
#  Subprocess helpers — all blocking helpers MUST run on a worker thread
# ════════════════════════════════════════════════════════════════════════════

def _run_cap(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    """Capture stdout/stderr. Returns (rc, out, err). Never raises."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, check=False)
        return p.returncode, p.stdout, p.stderr
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{cmd[0]}: timed out after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


def _run_async(cmd: list[str]) -> bool:
    """Fire-and-forget exec. Used for opening helpers in a terminal."""
    if DRY_RUN:
        sys.stderr.write(f"[store DRY_RUN] {' '.join(cmd)}\n")
        return True
    try:
        subprocess.Popen(cmd, start_new_session=True)
        return True
    except Exception as e:
        sys.stderr.write(f"[store] {' '.join(cmd)} failed: {e}\n")
        return False


def _pkexec_install(backend: str, pkg: str) -> list[str]:
    """Build a pkexec command for `pacman -S` or `pacman -R`. AUR helpers
    can't be run as root, so paru/yay installs run as the current user
    (they will pkexec internally)."""
    if backend == "pacman_install":
        return ["pkexec", "pacman", "-S", "--noconfirm", pkg]
    if backend == "pacman_remove":
        return ["pkexec", "pacman", "-R", "--noconfirm", pkg]
    if backend == "pacman_update":
        return ["pkexec", "pacman", "-Syu", "--noconfirm"]
    if backend == "aur_install" and AUR_HELPER:
        return [AUR_HELPER, "-S", "--noconfirm", pkg]
    if backend == "flatpak_install":
        return ["flatpak", "install", "-y", "flathub", pkg]
    if backend == "flatpak_remove":
        return ["flatpak", "uninstall", "-y", pkg]
    if backend == "flatpak_update":
        return ["flatpak", "update", "-y"]
    return []


def _exec_in_terminal(cmd: list[str]) -> None:
    """Run a long-running install/remove/update inside a terminal window so
    the user sees progress and any conflict prompts. Falls back through a
    list of common terminals."""
    if DRY_RUN:
        sys.stderr.write(f"[store DRY_RUN] terminal exec: {' '.join(cmd)}\n")
        return
    cmdline = " ".join(map(_shell_quote, cmd)) + "; echo; echo Press Enter to close; read"
    for term, flag in [
        ("alacritty", "-e"),
        ("kitty", "-e"),
        ("foot", "-e"),
        ("wezterm", "-e"),
        ("xterm", "-e"),
    ]:
        if shutil.which(term):
            _run_async([term, flag, "sh", "-c", cmdline])
            return
    # Last resort — fire it in the background and dump to journal.
    _run_async(cmd)


def _shell_quote(s: str) -> str:
    if not s or any(c in s for c in " \"'$\\;&|<>"):
        return "'" + s.replace("'", "'\\''") + "'"
    return s


# ════════════════════════════════════════════════════════════════════════════
#  Data fetchers — pure functions, all called from worker threads
# ════════════════════════════════════════════════════════════════════════════

@dataclass
class Pkg:
    name: str
    version: str
    repo: str          # "extra" | "core" | "AUR" | "flatpak" | "installed"
    summary: str = ""

    @property
    def key(self) -> str:
        return f"{self.repo}/{self.name}"


def fetch_installed() -> list[Pkg]:
    if not HAS_PACMAN:
        return []
    rc, out, _ = _run_cap(["pacman", "-Qe"], timeout=10)
    if rc != 0:
        return []
    pkgs = []
    for line in out.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2:
            pkgs.append(Pkg(name=parts[0], version=parts[1], repo="installed"))
    pkgs.sort(key=lambda p: p.name.lower())
    return pkgs


def fetch_updates() -> list[Pkg]:
    out = ""
    if HAS_CHECKUPDATES:
        rc, out, _ = _run_cap(["checkupdates"], timeout=30)
        # checkupdates returns 2 when there are no updates — that's fine.
        if rc not in (0, 2):
            out = ""
    if not out and HAS_PACMAN:
        rc, out, _ = _run_cap(["pacman", "-Qu"], timeout=15)
        if rc != 0:
            out = ""
    pkgs = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[2] == "->":
            pkgs.append(Pkg(name=parts[0], version=f"{parts[1]} → {parts[3]}", repo="update"))
    if AUR_HELPER:
        rc, aur, _ = _run_cap([AUR_HELPER, "-Qua"], timeout=30)
        if rc == 0:
            for line in aur.splitlines():
                parts = line.split()
                if len(parts) >= 4 and parts[2] == "->":
                    pkgs.append(Pkg(name=parts[0], version=f"{parts[1]} → {parts[3]}", repo="AUR"))
    if HAS_FLATPAK:
        rc, fp, _ = _run_cap(["flatpak", "remote-ls", "--updates", "--columns=application,version"], timeout=30)
        if rc == 0:
            for line in fp.splitlines():
                parts = line.split(maxsplit=1)
                if parts:
                    ver = parts[1] if len(parts) > 1 else ""
                    pkgs.append(Pkg(name=parts[0], version=ver, repo="flatpak"))
    pkgs.sort(key=lambda p: p.name.lower())
    return pkgs


def search(query: str) -> list[Pkg]:
    """Search across pacman + AUR + flatpak. Caps each backend at 60 hits
    to keep UI responsive."""
    results: list[Pkg] = []
    if not query.strip():
        return results

    if HAS_PACMAN:
        rc, out, _ = _run_cap(["pacman", "-Ss", query], timeout=15)
        if rc == 0:
            results.extend(_parse_pacman_search(out, "pacman", cap=60))

    if AUR_HELPER:
        rc, out, _ = _run_cap([AUR_HELPER, "-Ss", "--aur", query], timeout=20)
        if rc == 0:
            results.extend(_parse_pacman_search(out, "AUR", cap=60))

    if HAS_FLATPAK:
        rc, out, _ = _run_cap(
            ["flatpak", "search", "--columns=application,version,description", query],
            timeout=15,
        )
        if rc == 0:
            for line in out.splitlines()[:60]:
                cols = [c.strip() for c in line.split("\t")]
                if len(cols) >= 1 and cols[0] and cols[0] != "Application ID":
                    name = cols[0]
                    ver = cols[1] if len(cols) > 1 else ""
                    desc = cols[2] if len(cols) > 2 else ""
                    results.append(Pkg(name=name, version=ver, repo="flatpak", summary=desc))

    return results


def _parse_pacman_search(out: str, label: str, cap: int = 60) -> list[Pkg]:
    """pacman/paru/yay -Ss prints two-line records:
        repo/name version [flags]
            description
    """
    results: list[Pkg] = []
    lines = out.splitlines()
    i = 0
    while i < len(lines) and len(results) < cap:
        head = lines[i]
        if "/" in head and not head.startswith(" "):
            repo_name, _, rest = head.partition(" ")
            repo, _, name = repo_name.partition("/")
            ver = rest.split(" ", 1)[0] if rest else ""
            desc = ""
            if i + 1 < len(lines) and lines[i + 1].startswith(" "):
                desc = lines[i + 1].strip()
                i += 1
            results.append(Pkg(name=name, version=ver, repo=label or repo,
                               summary=desc))
        i += 1
    return results


def fetch_repos() -> list[tuple[str, str]]:
    """Returns [(repo_name, source)]. source = pacman.conf path or
    'flatpak' for flatpak remotes."""
    out: list[tuple[str, str]] = []
    pacman_conf = Path("/etc/pacman.conf")
    if pacman_conf.exists():
        try:
            for raw in pacman_conf.read_text().splitlines():
                line = raw.strip()
                if line.startswith("[") and line.endswith("]") and line != "[options]":
                    out.append((line[1:-1], str(pacman_conf)))
        except Exception:
            pass
    if HAS_FLATPAK:
        rc, fp, _ = _run_cap(["flatpak", "remotes", "--columns=name,url"], timeout=10)
        if rc == 0:
            for line in fp.splitlines():
                parts = line.split(None, 1)
                if parts:
                    url = parts[1] if len(parts) > 1 else "flatpak"
                    out.append((parts[0], url))
    return out


# ════════════════════════════════════════════════════════════════════════════
#  CSS
# ════════════════════════════════════════════════════════════════════════════

CSS = b"""
window.store-window { background: rgba(8, 12, 20, 0.92); }

.store-header-title {
    font-family: "Inter Display", "Inter", sans-serif;
    font-weight: 600;
    font-size: 18px;
    color: #ffffff;
    letter-spacing: 0.06em;
}

.store-section-title {
    font-family: "Inter Display", "Inter", sans-serif;
    font-weight: 600;
    font-size: 24px;
    color: #ffffff;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
}
.store-section-sub {
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    color: #9aa0ad;
    letter-spacing: 0.18em;
    margin-bottom: 18px;
}

.store-card {
    background: rgba(15, 20, 32, 0.72);
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 14px;
    padding: 16px 18px;
}
.store-card:hover { border-color: rgba(255, 255, 255, 0.20); }

.store-pkg-name {
    font-family: "Inter", sans-serif;
    font-weight: 600;
    font-size: 14px;
    color: #ffffff;
}
.store-pkg-version {
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    color: #9aa0ad;
    letter-spacing: 0.10em;
}
.store-pkg-summary {
    font-family: "Inter", sans-serif;
    font-size: 12px;
    color: #c8ccd6;
    margin-top: 4px;
}
.store-pkg-repo {
    font-family: "JetBrains Mono", monospace;
    font-size: 9.5px;
    color: #6a6e78;
    letter-spacing: 0.20em;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 2px 8px;
}

.store-empty {
    font-family: "Inter", sans-serif;
    font-size: 13px;
    color: #9aa0ad;
    margin: 32px 0;
}
.store-empty-hint {
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    color: #6a6e78;
    letter-spacing: 0.16em;
}

.store-search-entry { min-height: 36px; }

.store-toast {
    background: rgba(15, 20, 32, 0.92);
    color: #e8edf5;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 10px;
    padding: 10px 14px;
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    letter-spacing: 0.10em;
}

.store-backend-row {
    font-family: "JetBrains Mono", monospace;
    font-size: 12px;
    color: #c8ccd6;
}
.store-backend-ok    { color: #6ee7a3; }
.store-backend-miss  { color: #ff9a7a; }
"""


# ════════════════════════════════════════════════════════════════════════════
#  UI helpers
# ════════════════════════════════════════════════════════════════════════════

def _empty_state(title: str, hint: str = "") -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                  halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                  spacing=8)
    lab = Gtk.Label(label=title)
    lab.add_css_class("store-empty")
    lab.set_xalign(0.5)
    box.append(lab)
    if hint:
        h = Gtk.Label(label=hint)
        h.add_css_class("store-empty-hint")
        h.set_xalign(0.5)
        box.append(h)
    return box


def _scrolled(child: Gtk.Widget) -> Gtk.ScrolledWindow:
    sw = Gtk.ScrolledWindow()
    sw.set_hexpand(True)
    sw.set_vexpand(True)
    sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
    sw.set_child(child)
    return sw


def _section_header(title: str, subtitle: str) -> Gtk.Box:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
    box.set_margin_bottom(6)
    t = Gtk.Label(label=title); t.set_xalign(0)
    t.add_css_class("store-section-title")
    s = Gtk.Label(label=subtitle.upper()); s.set_xalign(0)
    s.add_css_class("store-section-sub")
    box.append(t); box.append(s)
    return box


def _pkg_card(pkg: Pkg, primary_label: str,
              on_primary: Callable[[Pkg], None],
              secondary_label: Optional[str] = None,
              on_secondary: Optional[Callable[[Pkg], None]] = None) -> Gtk.Widget:
    card = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
    card.add_css_class("store-card")
    card.set_margin_bottom(8)

    info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    info.set_hexpand(True)

    head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
    name = Gtk.Label(label=pkg.name); name.set_xalign(0)
    name.add_css_class("store-pkg-name")
    repo = Gtk.Label(label=pkg.repo.upper()); repo.set_xalign(0)
    repo.add_css_class("store-pkg-repo")
    head.append(name)
    head.append(repo)

    ver = Gtk.Label(label=pkg.version or ""); ver.set_xalign(0)
    ver.add_css_class("store-pkg-version")
    ver.set_ellipsize(Pango.EllipsizeMode.END)

    info.append(head)
    info.append(ver)
    if pkg.summary:
        s = Gtk.Label(label=pkg.summary); s.set_xalign(0)
        s.add_css_class("store-pkg-summary")
        s.set_wrap(True); s.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        s.set_max_width_chars(72)
        info.append(s)

    btns = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                   valign=Gtk.Align.CENTER)
    if secondary_label and on_secondary:
        sb = Gtk.Button(label=secondary_label)
        sb.connect("clicked", lambda _b: on_secondary(pkg))
        btns.append(sb)

    pb = Gtk.Button(label=primary_label)
    pb.add_css_class("suggested-action")
    pb.connect("clicked", lambda _b: on_primary(pkg))
    btns.append(pb)

    card.append(info)
    card.append(btns)
    return card


# ════════════════════════════════════════════════════════════════════════════
#  Sections
# ════════════════════════════════════════════════════════════════════════════

class StoreSection:
    """Base — every section provides a build() returning a widget and a
    refresh() that re-fetches its data."""
    title = "Section"
    subtitle = ""

    def __init__(self, app: "StoreApp"):
        self.app = app
        self.box: Gtk.Box | None = None

    def build(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_margin_top(24)
        outer.set_margin_bottom(24)
        outer.set_margin_start(28)
        outer.set_margin_end(28)
        outer.append(_section_header(self.title, self.subtitle))
        self.box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.set_vexpand(True)
        outer.append(self.box)
        self.refresh()
        return outer

    def refresh(self) -> None:
        pass

    def _set_content(self, w: Gtk.Widget) -> None:
        if self.box is None:
            return
        # Drop existing children
        child = self.box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.box.remove(child)
            child = nxt
        self.box.append(w)


class FeaturedSection(StoreSection):
    title = "Featured"
    subtitle = "Curated NYXUS picks"

    def refresh(self) -> None:
        installed_names = {p.name for p in self.app.cache_installed}
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for pkg_name, repo, display, blurb in FEATURED:
            pkg = Pkg(name=pkg_name, version=display, repo=repo, summary=blurb)
            if pkg_name in installed_names:
                card = _pkg_card(pkg, "Installed",
                                 on_primary=lambda _p: None,
                                 secondary_label="Remove",
                                 on_secondary=self.app.remove_pacman)
            else:
                card = _pkg_card(pkg, "Install", on_primary=self.app.install_pacman)
            list_box.append(card)
        self._set_content(_scrolled(list_box))


class InstalledSection(StoreSection):
    title = "Installed"
    subtitle = "Explicitly installed packages (pacman -Qe)"

    def refresh(self) -> None:
        if not HAS_PACMAN:
            self._set_content(_empty_state(
                "pacman is not available on this system",
                "The NYXUS App Store requires Arch's pacman."))
            return

        def work():
            data = fetch_installed()
            self.app.cache_installed = data
            GLib.idle_add(self._render, data)
        self._set_content(_empty_state("Loading installed packages…"))
        threading.Thread(target=work, daemon=True).start()

    def _render(self, data: list[Pkg]):
        if not data:
            self._set_content(_empty_state(
                "No explicitly installed packages",
                "Try: pacman -Qe in a terminal"))
            return False
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for pkg in data:
            card = _pkg_card(pkg, "Remove", on_primary=self.app.remove_pacman)
            list_box.append(card)
        self._set_content(_scrolled(list_box))
        return False


class UpdatesSection(StoreSection):
    title = "Updates"
    subtitle = "Out-of-date packages across all backends"

    def refresh(self) -> None:
        def work():
            data = fetch_updates()
            GLib.idle_add(self._render, data)
        self._set_content(_empty_state("Checking for updates…"))
        threading.Thread(target=work, daemon=True).start()

    def _render(self, data: list[Pkg]):
        if not data:
            hint_parts = ["pacman ✓"]
            hint_parts.append("AUR ✓" if AUR_HELPER else "AUR —")
            hint_parts.append("flatpak ✓" if HAS_FLATPAK else "flatpak —")
            self._set_content(_empty_state(
                "Everything is up to date",
                " · ".join(hint_parts)))
            return False
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        # Update-all bar
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.set_margin_bottom(12)
        count = Gtk.Label(label=f"{len(data)} package(s) to update")
        count.set_xalign(0); count.set_hexpand(True)
        count.add_css_class("store-pkg-name")
        all_btn = Gtk.Button(label="Update All (pacman)")
        all_btn.add_css_class("suggested-action")
        all_btn.connect("clicked", lambda _b: self.app.update_all_pacman())
        bar.append(count); bar.append(all_btn)
        if HAS_FLATPAK:
            fpb = Gtk.Button(label="Update Flatpaks")
            fpb.connect("clicked", lambda _b: self.app.update_all_flatpak())
            bar.append(fpb)
        outer.append(bar)
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for pkg in data:
            card = _pkg_card(pkg, "Update", on_primary=self.app.update_one)
            list_box.append(card)
        outer.append(_scrolled(list_box))
        self._set_content(outer)
        return False


class SearchSection(StoreSection):
    title = "Search"
    subtitle = "Across pacman, AUR, and flatpak"

    def __init__(self, app: "StoreApp"):
        super().__init__(app)
        self._entry: Gtk.SearchEntry | None = None
        self._results_box: Gtk.Box | None = None
        self._debounce_id: int | None = None
        self._last_query = ""

    def build(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_margin_top(24); outer.set_margin_bottom(24)
        outer.set_margin_start(28); outer.set_margin_end(28)
        outer.append(_section_header(self.title, self.subtitle))

        entry = Gtk.SearchEntry()
        entry.add_css_class("store-search-entry")
        entry.set_placeholder_text("Search packages…")
        entry.connect("search-changed", self._on_changed)
        entry.set_margin_bottom(14)
        self._entry = entry
        outer.append(entry)

        self._results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._results_box.set_vexpand(True)
        self._results_box.append(_empty_state(
            "Type to search",
            f"Backends: pacman {'✓' if HAS_PACMAN else '—'}  "
            f"AUR {'✓ ' + Path(AUR_HELPER).name if AUR_HELPER else '—'}  "
            f"flatpak {'✓' if HAS_FLATPAK else '—'}"))
        outer.append(self._results_box)
        return outer

    def _on_changed(self, entry: Gtk.SearchEntry):
        if self._debounce_id is not None:
            GLib.source_remove(self._debounce_id)
        self._debounce_id = GLib.timeout_add(350, self._fire, entry.get_text())

    def _fire(self, query: str):
        self._debounce_id = None
        query = query.strip()
        if query == self._last_query:
            return False
        self._last_query = query
        if not query:
            self._render([], query)
            return False
        self._set_results(_empty_state(f"Searching for “{query}”…"))

        def work():
            data = search(query)
            GLib.idle_add(self._render, data, query)
        threading.Thread(target=work, daemon=True).start()
        return False

    def _set_results(self, w: Gtk.Widget):
        if self._results_box is None:
            return
        c = self._results_box.get_first_child()
        while c is not None:
            n = c.get_next_sibling()
            self._results_box.remove(c)
            c = n
        self._results_box.append(w)

    def _render(self, data: list[Pkg], query: str):
        # Drop stale results: if a newer query has been submitted while
        # this worker was running, ignore its results entirely.
        if query != self._last_query:
            return False
        if not data:
            self._set_results(_empty_state(
                f"No packages match “{query}”",
                "Try a shorter or different keyword."))
            return False
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for pkg in data:
            if pkg.repo == "flatpak":
                card = _pkg_card(pkg, "Install", on_primary=self.app.install_flatpak)
            elif pkg.repo == "AUR":
                card = _pkg_card(pkg, "Install (AUR)", on_primary=self.app.install_aur)
            else:
                card = _pkg_card(pkg, "Install", on_primary=self.app.install_pacman)
            list_box.append(card)
        self._set_results(_scrolled(list_box))
        return False


class ReposSection(StoreSection):
    title = "Repositories"
    subtitle = "Configured pacman + flatpak sources"

    def refresh(self) -> None:
        repos = fetch_repos()
        if not repos:
            self._set_content(_empty_state(
                "No repositories detected",
                "/etc/pacman.conf is missing or unreadable."))
            return
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        for name, src in repos:
            card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            card.add_css_class("store-card")
            card.set_margin_bottom(8)
            n = Gtk.Label(label=name); n.set_xalign(0)
            n.add_css_class("store-pkg-name")
            s = Gtk.Label(label=src); s.set_xalign(0)
            s.add_css_class("store-pkg-version")
            s.set_ellipsize(Pango.EllipsizeMode.END)
            card.append(n); card.append(s)
            list_box.append(card)
        self._set_content(_scrolled(list_box))


class AboutSection(StoreSection):
    title = "About"
    subtitle = "Backend availability"

    def refresh(self) -> None:
        rows = [
            ("pacman",       HAS_PACMAN,      "Arch package manager — required"),
            ("checkupdates", HAS_CHECKUPDATES,"Faster update check (pacman-contrib)"),
            ("paru / yay",   bool(AUR_HELPER),f"AUR helper{f' — using {Path(AUR_HELPER).name}' if AUR_HELPER else ''}"),
            ("flatpak",      HAS_FLATPAK,     "Flathub sandboxed apps"),
            ("pkexec",       HAS_PKEXEC,      "Polkit elevation for installs"),
        ]
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        for name, ok, blurb in rows:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.add_css_class("store-card")
            row.set_margin_bottom(6)
            label = Gtk.Label(label=("✓ " if ok else "✗ ") + name); label.set_xalign(0)
            label.add_css_class("store-backend-row")
            label.add_css_class("store-backend-ok" if ok else "store-backend-miss")
            label.set_size_request(180, -1)
            blurb_lab = Gtk.Label(label=blurb); blurb_lab.set_xalign(0)
            blurb_lab.add_css_class("store-pkg-summary")
            blurb_lab.set_hexpand(True)
            row.append(label); row.append(blurb_lab)
            list_box.append(row)

        # Tagline
        tag = Gtk.Label(label="NYXUS App Store — DARK MIRROR rev r1 · 2026-05-12")
        tag.add_css_class("store-empty-hint")
        tag.set_xalign(0); tag.set_margin_top(18)
        list_box.append(tag)

        self._set_content(_scrolled(list_box))


# ════════════════════════════════════════════════════════════════════════════
#  Application
# ════════════════════════════════════════════════════════════════════════════

class StoreApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        try: Adw.init()
        except Exception: pass

        # cache so Featured can quickly check installed-state
        self.cache_installed: list[Pkg] = []

        self.sections: dict[str, StoreSection] = {}
        self._toast_overlay: Adw.ToastOverlay | None = None
        self._content_stack: Gtk.Stack | None = None

    # ─── activation ────────────────────────────────────────────────────────
    def do_activate(self):
        try:
            sm = Adw.StyleManager.get_default()
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        except Exception: pass

        prov = Gtk.CssProvider()
        try: prov.load_from_data(CSS)
        except Exception:
            try: prov.load_from_string(CSS.decode())
            except Exception: pass
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        win = Adw.ApplicationWindow(application=self, title="NYXUS App Store")
        win.set_default_size(1180, 720)
        win.add_css_class("store-window")
        if HAS_CHROME:
            try: install_chrome(win, key="_store")
            except Exception: pass

        # Pre-warm installed cache so Featured boots correctly.
        self.cache_installed = fetch_installed()

        # Build sections
        order = [
            ("featured",     FeaturedSection(self)),
            ("installed",    InstalledSection(self)),
            ("updates",      UpdatesSection(self)),
            ("search",       SearchSection(self)),
            ("repositories", ReposSection(self)),
            ("about",        AboutSection(self)),
        ]
        for key, sec in order:
            self.sections[key] = sec

        # Sidebar
        sidebar_page = self._build_sidebar(order)
        # Content stack
        stack = Gtk.Stack()
        stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        for key, sec in order:
            stack.add_named(sec.build(), key)
        self._content_stack = stack

        toast = Adw.ToastOverlay()
        toast.set_child(stack)
        self._toast_overlay = toast

        content_page = Adw.NavigationPage.new(toast, "App Store")
        # Header bar with refresh + reload-installed button
        header = Adw.HeaderBar()
        title_label = Gtk.Label(label="NYXUS App Store")
        title_label.add_css_class("store-header-title")
        header.set_title_widget(title_label)

        refresh_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh current section")
        refresh_btn.connect("clicked", lambda _b: self._refresh_current())
        header.pack_end(refresh_btn)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.append(header)
        outer.append(toast)
        content_page = Adw.NavigationPage.new(outer, "App Store")

        split = Adw.NavigationSplitView()
        split.set_sidebar(sidebar_page)
        split.set_content(content_page)
        split.set_min_sidebar_width(180)
        split.set_max_sidebar_width(240)

        win.set_content(split)
        win.present()

    # ─── sidebar ──────────────────────────────────────────────────────────
    def _build_sidebar(self, order: list[tuple[str, StoreSection]]) -> Adw.NavigationPage:
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        list_box.add_css_class("navigation-sidebar")
        for key, sec in order:
            row = Gtk.ListBoxRow()
            row.set_name(key)
            lbl = Gtk.Label(label=sec.title)
            lbl.set_xalign(0)
            lbl.set_margin_top(10); lbl.set_margin_bottom(10)
            lbl.set_margin_start(16); lbl.set_margin_end(16)
            row.set_child(lbl)
            list_box.append(row)

        def _on_row_selected(_lb, row):
            if row is None or self._content_stack is None:
                return
            self._content_stack.set_visible_child_name(row.get_name())

        list_box.connect("row-selected", _on_row_selected)
        # Select first row by default
        first = list_box.get_row_at_index(0)
        if first is not None:
            list_box.select_row(first)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_child(list_box)

        # Sidebar with header
        header = Adw.HeaderBar()
        title = Gtk.Label(label="Store")
        title.add_css_class("store-header-title")
        header.set_title_widget(title)

        side_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        side_box.append(header)
        side_box.append(scrolled)

        return Adw.NavigationPage.new(side_box, "Store")

    # ─── action handlers ──────────────────────────────────────────────────
    def _toast(self, msg: str) -> None:
        if self._toast_overlay is None:
            return
        t = Adw.Toast.new(msg)
        t.set_timeout(3)
        self._toast_overlay.add_toast(t)

    def _refresh_current(self) -> None:
        if self._content_stack is None:
            return
        name = self._content_stack.get_visible_child_name()
        if name and name in self.sections:
            self.cache_installed = fetch_installed()  # keep Featured in sync
            self.sections[name].refresh()
            self._toast(f"Refreshed {self.sections[name].title}")

    def _confirm_then(self, title: str, body: str,
                      destructive: bool, on_yes: Callable[[], None]) -> None:
        win = self.get_active_window()
        if win is None:
            on_yes(); return
        dlg = Adw.MessageDialog.new(win, title, body)
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("ok", title)
        dlg.set_response_appearance(
            "ok",
            Adw.ResponseAppearance.DESTRUCTIVE if destructive
            else Adw.ResponseAppearance.SUGGESTED)
        dlg.set_default_response("cancel")
        dlg.set_close_response("cancel")
        def _r(_d, resp):
            if resp == "ok":
                on_yes()
        dlg.connect("response", _r)
        dlg.present()

    # — pacman —
    def install_pacman(self, pkg: Pkg) -> None:
        if not HAS_PACMAN:
            self._toast("pacman not available"); return
        self._confirm_then(
            "Install", f"Install {pkg.name} from pacman?",
            destructive=False,
            on_yes=lambda: (
                _exec_in_terminal(_pkexec_install("pacman_install", pkg.name)),
                self._toast(f"Installing {pkg.name}…"),
            ))

    def remove_pacman(self, pkg: Pkg) -> None:
        if not HAS_PACMAN:
            self._toast("pacman not available"); return
        self._confirm_then(
            "Remove", f"Remove {pkg.name}? Configuration files are kept.",
            destructive=True,
            on_yes=lambda: (
                _exec_in_terminal(_pkexec_install("pacman_remove", pkg.name)),
                self._toast(f"Removing {pkg.name}…"),
            ))

    def update_all_pacman(self) -> None:
        if not HAS_PACMAN:
            self._toast("pacman not available"); return
        self._confirm_then(
            "Update All", "Run a full system upgrade (pacman -Syu)?",
            destructive=False,
            on_yes=lambda: (
                _exec_in_terminal(_pkexec_install("pacman_update", "")),
                self._toast("System upgrade running…"),
            ))

    def update_one(self, pkg: Pkg) -> None:
        if pkg.repo == "AUR":
            self.install_aur(pkg)
        elif pkg.repo == "flatpak":
            self.update_all_flatpak()
        else:
            self.install_pacman(pkg)

    # — AUR —
    def install_aur(self, pkg: Pkg) -> None:
        if not AUR_HELPER:
            self._toast("No AUR helper installed (paru / yay)"); return
        self._confirm_then(
            "Install (AUR)",
            f"Install {pkg.name} from AUR using {Path(AUR_HELPER).name}?",
            destructive=False,
            on_yes=lambda: (
                _exec_in_terminal(_pkexec_install("aur_install", pkg.name)),
                self._toast(f"Installing {pkg.name} from AUR…"),
            ))

    # — flatpak —
    def install_flatpak(self, pkg: Pkg) -> None:
        if not HAS_FLATPAK:
            self._toast("flatpak not installed"); return
        self._confirm_then(
            "Install (flatpak)",
            f"Install {pkg.name} from Flathub?",
            destructive=False,
            on_yes=lambda: (
                _exec_in_terminal(_pkexec_install("flatpak_install", pkg.name)),
                self._toast(f"Installing {pkg.name} from Flathub…"),
            ))

    def update_all_flatpak(self) -> None:
        if not HAS_FLATPAK:
            self._toast("flatpak not installed"); return
        _exec_in_terminal(_pkexec_install("flatpak_update", ""))
        self._toast("Updating Flatpaks…")


def main() -> int:
    return StoreApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
