#!/usr/bin/env python3
"""
NYXUS Updater — pacman + AUR + flatpak system update GUI.

Single window. Lists pending updates from every backend, lets the user
review individual packages, runs `pacman -Syu` (and AUR/flatpak peers)
through pkexec in a real terminal so the user sees the live transaction.
Logs every run to ~/.cache/nyxus/updater.log + a shareable transcript
at ~/.cache/nyxus/updater-last.txt.

Launch:
    nyxus-updater                 # GUI
    nyxus-updater --check         # exit 0 if no updates, 10 if any (for tray)
    nyxus-updater --count         # print count of pending updates

Hyprland keybind: Super+Ctrl+U
"""
from __future__ import annotations

import logging
import logging.handlers
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gio, Gtk  # noqa: E402

HOME = Path(os.path.expanduser("~"))
CACHE = HOME / ".cache" / "nyxus"
CACHE.mkdir(parents=True, exist_ok=True)
LOG_FILE = CACHE / "updater.log"
TRANSCRIPT = CACHE / "updater-last.txt"

log = logging.getLogger("nyxus_updater")
log.setLevel(logging.INFO)
_h = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=512_000,
                                          backupCount=3)
_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(_h)


def have(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


AUR_HELPER = have("paru") or have("yay")
HAS_FLATPAK = bool(have("flatpak"))
HAS_CHECKUPDATES = bool(have("checkupdates"))


# ---------- model ----------
@dataclass
class Update:
    name: str
    cur: str
    new: str
    repo: str   # "official" | "AUR" | "flatpak"


def _run_capture(cmd: list[str], timeout: int = 30) -> tuple[int, str, str]:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True,
                             timeout=timeout, check=False)
        return res.returncode, res.stdout, res.stderr
    except FileNotFoundError:
        return 127, "", f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, "", f"{cmd[0]}: timeout"
    except Exception as e:
        return 1, "", str(e)


def fetch_official() -> list[Update]:
    if not HAS_CHECKUPDATES:
        return []
    rc, out, _ = _run_capture(["checkupdates"], timeout=60)
    if rc not in (0, 2):  # 2 = no updates
        return []
    out_list: list[Update] = []
    for line in out.splitlines():
        # format: name cur -> new
        parts = line.split()
        if len(parts) >= 4 and parts[2] == "->":
            out_list.append(Update(parts[0], parts[1], parts[3], "official"))
    return out_list


def fetch_aur() -> list[Update]:
    if not AUR_HELPER:
        return []
    rc, out, _ = _run_capture([AUR_HELPER, "-Qua"], timeout=60)
    if rc != 0:
        return []
    res: list[Update] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and parts[2] == "->":
            res.append(Update(parts[0], parts[1], parts[3], "AUR"))
    return res


def fetch_flatpak() -> list[Update]:
    if not HAS_FLATPAK:
        return []
    rc, out, _ = _run_capture(
        ["flatpak", "remote-ls", "--updates",
         "--columns=application,version"],
        timeout=60)
    if rc != 0:
        return []
    res: list[Update] = []
    for line in out.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) >= 1:
            name = parts[0]
            new = parts[1] if len(parts) > 1 else "?"
            res.append(Update(name, "?", new, "flatpak"))
    return res


def fetch_all() -> list[Update]:
    out: list[Update] = []
    out += fetch_official()
    out += fetch_aur()
    out += fetch_flatpak()
    return out


# ---------- terminal runner ----------
def _terminal_run(title: str, sh_cmd: str) -> None:
    """Open a terminal that runs sh_cmd, then pauses for keypress so the
    user sees the result. Tee output to TRANSCRIPT for later viewing."""
    payload = (
        f"{{ {sh_cmd}; rc=$?; "
        f"echo; echo '────────────'; echo \"exit: $rc\"; "
        f"echo 'Press Enter to close.'; read _; "
        f"}} 2>&1 | tee '{TRANSCRIPT}'"
    )
    for term in ("alacritty", "kitty", "foot", "wezterm",
                 "xterm", "konsole"):
        if have(term):
            try:
                subprocess.Popen([term, "-e", "sh", "-c", payload],
                                 start_new_session=True)
                return
            except Exception as e:
                log.warning("%s spawn failed: %s", term, e)
    log.error("no terminal emulator found to run update")


# ---------- GUI ----------
GOLD = "#d4b87a"
INK = "#080a10"
INK2 = "#10131c"

CSS = f"""
.updater-window {{ background: {INK}; }}
.updater-header {{
    color: {GOLD}; font-weight: 700; font-size: 16px;
    letter-spacing: 0.04em; padding: 4px 0 8px 0;
}}
.updater-summary {{
    color: rgba(230, 232, 238, 0.8);
    padding-bottom: 6px;
}}
.updater-row {{ padding: 8px 12px; }}
.updater-pkg {{ color: #ffffff; font-weight: 500; }}
.updater-ver {{ color: {GOLD}; font-family: monospace; font-size: 11px; }}
.updater-repo {{
    color: {INK}; background: {GOLD};
    border-radius: 4px; padding: 1px 6px; font-size: 10px;
    font-weight: 700;
}}
.updater-empty {{
    color: rgba(230, 232, 238, 0.55);
    padding: 80px 24px; font-style: italic;
    font-size: 14px;
}}
.updater-action {{
    background: {GOLD}; color: {INK};
    border-radius: 6px; padding: 6px 14px;
    font-weight: 700;
}}
""".encode("utf-8")


class UpdaterWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app)
        self.set_title("NYXUS Updater")
        self.set_default_size(720, 560)
        self.add_css_class("updater-window")
        self.updates: list[Update] = []

        toolbar = Adw.ToolbarView()
        self.set_content(toolbar)

        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        self.btn_refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        self.btn_refresh.set_tooltip_text("Re-check for updates (F5)")
        self.btn_refresh.connect("clicked", lambda *_: self.refresh())
        header.pack_start(self.btn_refresh)

        self.btn_run = Gtk.Button(label="Update All")
        self.btn_run.add_css_class("updater-action")
        self.btn_run.add_css_class("suggested-action")
        self.btn_run.connect("clicked", lambda *_: self.run_all())
        header.pack_end(self.btn_run)

        # body
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_start(16); outer.set_margin_end(16)
        outer.set_margin_top(8); outer.set_margin_bottom(12)
        toolbar.set_content(outer)

        title = Gtk.Label(label="System Updates", xalign=0)
        title.add_css_class("updater-header")
        outer.append(title)

        self.summary = Gtk.Label(label="Checking…", xalign=0)
        self.summary.add_css_class("updater-summary")
        outer.append(self.summary)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        outer.append(scroll)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list_box.add_css_class("boxed-list")
        scroll.set_child(self.list_box)

        # toast overlay
        self.toast = Adw.ToastOverlay()
        self.toast.set_child(toolbar)
        self.set_content(self.toast)

        # F5 keyboard
        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

        GLib.idle_add(self.refresh)

    def _on_key(self, ctrl, keyval, keycode, state) -> bool:
        if keyval == Gdk.KEY_F5:
            self.refresh()
            return True
        return False

    def refresh(self) -> bool:
        self.btn_refresh.set_sensitive(False)
        self.summary.set_label("Checking for updates…")
        # blocking: keep things simple. checkupdates is local to pacman db.
        # AUR/flatpak hit network, but the dialog stays responsive enough.
        try:
            updates = fetch_all()
        except Exception as e:
            log.error("fetch failed: %s", e)
            updates = []
        self.updates = updates
        # render
        child = self.list_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.list_box.remove(child)
            child = nxt
        if not updates:
            empty = Gtk.Label(label="✓  Your system is up to date.",
                              xalign=0)
            empty.add_css_class("updater-empty")
            row = Gtk.ListBoxRow()
            row.set_child(empty)
            row.set_selectable(False)
            self.list_box.append(row)
            self.btn_run.set_sensitive(False)
            self.summary.set_label("0 packages to update.")
        else:
            counts: dict[str, int] = {}
            for u in updates:
                counts[u.repo] = counts.get(u.repo, 0) + 1
            parts = [f"{n} {repo}" for repo, n in counts.items()]
            self.summary.set_label(
                f"{len(updates)} package(s) — " + ", ".join(parts))
            self.btn_run.set_sensitive(True)
            for u in updates:
                row = Gtk.ListBoxRow()
                box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                              spacing=10)
                box.add_css_class("updater-row")
                name = Gtk.Label(label=u.name, xalign=0)
                name.add_css_class("updater-pkg")
                name.set_hexpand(True)
                box.append(name)
                ver = Gtk.Label(label=f"{u.cur} → {u.new}", xalign=1)
                ver.add_css_class("updater-ver")
                box.append(ver)
                rep = Gtk.Label(label=u.repo)
                rep.add_css_class("updater-repo")
                box.append(rep)
                row.set_child(box)
                self.list_box.append(row)
        self.btn_refresh.set_sensitive(True)
        return False

    def run_all(self) -> None:
        if not self.updates:
            return
        cmds: list[str] = []
        if any(u.repo == "official" for u in self.updates):
            cmds.append("pkexec pacman -Syu --noconfirm")
        if AUR_HELPER and any(u.repo == "AUR" for u in self.updates):
            cmds.append(f"{AUR_HELPER} -Sua --noconfirm")
        if HAS_FLATPAK and any(u.repo == "flatpak" for u in self.updates):
            cmds.append("flatpak update -y")
        if not cmds:
            self.toast.add_toast(Adw.Toast.new("No applicable backend"))
            return
        sh = " && ".join(cmds)
        log.info("running: %s", sh)
        with TRANSCRIPT.open("w") as f:
            f.write(f"NYXUS Updater run @ {datetime.now().isoformat()}\n")
            f.write(f"Cmd: {sh}\n\n")
        _terminal_run("System Update", sh)
        self.toast.add_toast(Adw.Toast.new(
            "Update started in terminal. Window will refresh after."))
        # schedule a re-check
        GLib.timeout_add_seconds(30, lambda: (self.refresh(), False)[1])


class UpdaterApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(application_id="com.nyxus.updater")

    def do_activate(self) -> None:  # type: ignore[override]
        try:
            sm = Adw.StyleManager.get_default()
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        except Exception:
            pass
        prov = Gtk.CssProvider()
        try: prov.load_from_data(CSS)
        except Exception:
            try: prov.load_from_string(CSS.decode())
            except Exception: pass
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        win = UpdaterWindow(self)
        win.present()


def main() -> int:
    if "--check" in sys.argv:
        n = len(fetch_all())
        print(n)
        return 0 if n == 0 else 10
    if "--count" in sys.argv:
        print(len(fetch_all()))
        return 0
    return UpdaterApp().run([])


if __name__ == "__main__":
    sys.exit(main())
