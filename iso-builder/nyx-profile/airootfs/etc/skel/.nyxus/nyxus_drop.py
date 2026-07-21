#!/usr/bin/env python3
"""
NYXUS Drop — branded share dialog over kdeconnect-cli.

Lists paired KDE Connect devices (phones, tablets, other Linux/Mac/Win
boxes running KDE Connect) and lets the user push files or text. Plain
wrapper — no daemon of our own. The KDE Connect daemon (`kdeconnectd`)
must be running in the user session; we start it on demand.

Wired:
    Super+Shift+D            → opens Drop with a file picker
    nyxus-drop --send <path> → headless send to first paired device
    nyxus-drop --text "..."  → send text/clipboard to first paired device
"""
from __future__ import annotations

import argparse
import json
import logging
import logging.handlers
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gio, Gtk  # noqa: E402

HOME = Path(os.path.expanduser("~"))
CACHE = HOME / ".cache" / "nyxus"; CACHE.mkdir(parents=True, exist_ok=True)
LOG_FILE = CACHE / "drop.log"

log = logging.getLogger("nyxus_drop")
log.setLevel(logging.INFO)
_h = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=256_000,
                                          backupCount=2)
_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(_h)


def have(cmd: str) -> str | None:
    return shutil.which(cmd)


HAS_KDECONNECT = bool(have("kdeconnect-cli"))


@dataclass
class Device:
    id: str
    name: str
    type: str          # phone | tablet | desktop | laptop | tv | unknown
    reachable: bool
    paired: bool


def ensure_daemon() -> None:
    if not HAS_KDECONNECT:
        return
    # KDE Connect daemon is started on-demand by D-Bus activation when
    # `kdeconnect-cli --list-devices` is called, but on minimal sessions
    # we hint systemd to start its user unit if available.
    if have("systemctl"):
        subprocess.Popen(["systemctl", "--user", "start",
                          "kdeconnectd.service"],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)


def list_devices() -> list[Device]:
    if not HAS_KDECONNECT:
        return []
    ensure_daemon()
    rc, out = subprocess.getstatusoutput(
        "kdeconnect-cli --list-devices --id-name-only")
    if rc != 0:
        return []
    rc2, paired = subprocess.getstatusoutput(
        "kdeconnect-cli --list-available --id-only")
    paired_ids = set(paired.split()) if rc2 == 0 else set()
    devs: list[Device] = []
    for line in out.splitlines():
        line = line.strip()
        if not line or " " not in line:
            continue
        did, name = line.split(" ", 1)
        devs.append(Device(id=did, name=name.strip(),
                           type="unknown",
                           reachable=did in paired_ids,
                           paired=True))
    return devs


def send_file(device_id: str, path: Path) -> tuple[int, str]:
    if not HAS_KDECONNECT:
        return 127, "kdeconnect-cli not installed"
    cmd = ["kdeconnect-cli", "-d", device_id, "--share", str(path)]
    log.info("send: %s", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return r.returncode, (r.stderr or r.stdout or "").strip()


def send_text(device_id: str, text: str) -> tuple[int, str]:
    if not HAS_KDECONNECT:
        return 127, "kdeconnect-cli not installed"
    cmd = ["kdeconnect-cli", "-d", device_id, "--share-text", text]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return r.returncode, (r.stderr or r.stdout or "").strip()


# ---------- GUI ----------
GOLD = "#d4b87a"; INK = "#080a10"
CSS = f"""
.drop-window {{ background: {INK}; }}
.drop-header {{ color: {GOLD}; font-weight: 700; font-size: 18px;
                padding: 8px 0 6px 0; letter-spacing: 0.04em; }}
.drop-empty  {{ color: rgba(230,232,238,0.55); padding: 60px 24px;
                font-style: italic; font-size: 14px; }}
.dev-name    {{ color: #fff; font-weight: 500; }}
.dev-meta    {{ color: rgba(230,232,238,0.55); font-size: 11px; }}
""".encode("utf-8")


class DropWindow(Adw.ApplicationWindow):
    def __init__(self, app, initial_path: Path | None = None):
        super().__init__(application=app)
        self.set_title("NYXUS Drop")
        self.set_default_size(560, 480)
        self.add_css_class("drop-window")
        self.queued_path: Path | None = initial_path

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar(); toolbar.add_top_bar(header)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        outer.set_margin_start(18); outer.set_margin_end(18)
        outer.set_margin_top(8); outer.set_margin_bottom(14)
        toolbar.set_content(outer)

        title = Gtk.Label(label="Send to a paired device", xalign=0)
        title.add_css_class("drop-header"); outer.append(title)

        # Picker
        pickbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        outer.append(pickbar)
        self.path_lbl = Gtk.Label(
            label=str(initial_path) if initial_path else "No file selected",
            xalign=0)
        self.path_lbl.set_hexpand(True); self.path_lbl.add_css_class("dev-meta")
        self.path_lbl.set_ellipsize(3)
        pickbar.append(self.path_lbl)
        choose = Gtk.Button(label="Choose file…")
        choose.connect("clicked", lambda *_: self.choose_file())
        pickbar.append(choose)
        text_btn = Gtk.Button(label="Send text…")
        text_btn.connect("clicked", lambda *_: self.send_text_dialog())
        pickbar.append(text_btn)

        # Device list
        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        outer.append(scroll)
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.add_css_class("boxed-list")
        scroll.set_child(self.list_box)

        # Action bar
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.set_halign(Gtk.Align.END); bar.set_margin_top(8)
        outer.append(bar)
        refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh.connect("clicked", lambda *_: self.refresh())
        bar.append(refresh)
        pair = Gtk.Button(label="Pair new device…")
        pair.connect("clicked", lambda *_: self.open_pair())
        bar.append(pair)
        self.send_btn = Gtk.Button(label="Send")
        self.send_btn.add_css_class("suggested-action")
        self.send_btn.connect("clicked", lambda *_: self.send_now())
        bar.append(self.send_btn)

        self.toast = Adw.ToastOverlay()
        self.toast.set_child(toolbar)
        self.set_content(self.toast)
        GLib.idle_add(self.refresh)

    def refresh(self) -> bool:
        c = self.list_box.get_first_child()
        while c is not None:
            n = c.get_next_sibling(); self.list_box.remove(c); c = n
        devs = list_devices()
        if not HAS_KDECONNECT:
            row = Gtk.ListBoxRow(); row.set_selectable(False)
            empty = Gtk.Label(
                label="KDE Connect is not installed.\n\n"
                      "Install:  pacman -S kdeconnect", xalign=0)
            empty.add_css_class("drop-empty"); empty.set_wrap(True)
            row.set_child(empty); self.list_box.append(row)
            return False
        if not devs:
            row = Gtk.ListBoxRow(); row.set_selectable(False)
            empty = Gtk.Label(
                label="No paired devices.\n"
                      "Click Pair new device… to add a phone or another "
                      "computer.", xalign=0)
            empty.add_css_class("drop-empty"); empty.set_wrap(True)
            row.set_child(empty); self.list_box.append(row)
            return False
        for d in devs:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.set_margin_top(8); box.set_margin_bottom(8)
            box.set_margin_start(12); box.set_margin_end(12)
            n = Gtk.Label(label=d.name, xalign=0); n.add_css_class("dev-name")
            box.append(n)
            sub = Gtk.Label(
                label=f"{'reachable' if d.reachable else 'offline'}  ·  "
                      f"id {d.id[:12]}…",
                xalign=0)
            sub.add_css_class("dev-meta"); box.append(sub)
            row.set_child(box); row.dev = d  # type: ignore[attr-defined]
            self.list_box.append(row)
        first = self.list_box.get_row_at_index(0)
        if first is not None: self.list_box.select_row(first)
        return False

    def choose_file(self) -> None:
        dlg = Gtk.FileDialog()
        dlg.open(self, None, self._on_file_chosen)

    def _on_file_chosen(self, dialog, res):
        try:
            f = dialog.open_finish(res)
            if f is None: return
            self.queued_path = Path(f.get_path())
            self.path_lbl.set_label(str(self.queued_path))
        except GLib.Error:
            pass

    def send_text_dialog(self) -> None:
        d = Adw.MessageDialog.new(self, "Send text",
                                   "Type or paste, then Send.")
        entry = Gtk.Entry(); entry.set_hexpand(True)
        d.set_extra_child(entry)
        d.add_response("cancel", "Cancel")
        d.add_response("send", "Send")
        d.set_default_response("send")
        d.set_response_appearance("send", Adw.ResponseAppearance.SUGGESTED)
        def _resp(dialog, resp):
            if resp != "send": return
            text = entry.get_text().strip()
            if not text: return
            row = self.list_box.get_selected_row()
            dev = getattr(row, "dev", None) if row else None
            if dev is None:
                self.toast.add_toast(Adw.Toast.new("Pick a device first"))
                return
            rc, err = send_text(dev.id, text)
            self.toast.add_toast(Adw.Toast.new(
                "Text sent." if rc == 0 else f"Failed: {err}"))
        d.connect("response", _resp); d.present()

    def send_now(self) -> None:
        row = self.list_box.get_selected_row()
        dev = getattr(row, "dev", None) if row else None
        if dev is None:
            self.toast.add_toast(Adw.Toast.new("Pick a device first"))
            return
        if self.queued_path is None or not self.queued_path.exists():
            self.toast.add_toast(Adw.Toast.new("Choose a file first"))
            return
        rc, err = send_file(dev.id, self.queued_path)
        self.toast.add_toast(Adw.Toast.new(
            "Sent." if rc == 0 else f"Failed: {err}"))

    def open_pair(self) -> None:
        for app in ("kdeconnect-app", "kdeconnect-settings"):
            if have(app):
                subprocess.Popen([app], start_new_session=True)
                return
        self.toast.add_toast(Adw.Toast.new(
            "Pair using:  kdeconnect-cli --pair --device <id>"))


class DropApp(Adw.Application):
    def __init__(self, initial: Path | None = None):
        super().__init__(application_id="com.nyxus.drop")
        self._initial = initial
    def do_activate(self):  # type: ignore[override]
        try: Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_DARK)
        except Exception: pass
        prov = Gtk.CssProvider()
        try: prov.load_from_data(CSS)
        except Exception:
            try: prov.load_from_string(CSS.decode())
            except Exception: pass
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        DropWindow(self, self._initial).present()


def main() -> int:
    ap = argparse.ArgumentParser(description="NYXUS Drop")
    ap.add_argument("--send", metavar="PATH",
                    help="headless send file to first paired device")
    ap.add_argument("--text", metavar="STR",
                    help="headless send text to first paired device")
    ap.add_argument("path", nargs="?",
                    help="prefill file in the GUI dialog")
    args = ap.parse_args()
    if args.send or args.text:
        devs = [d for d in list_devices() if d.reachable]
        if not devs:
            print("no reachable paired devices", file=sys.stderr); return 2
        target = devs[0].id
        if args.send:
            rc, err = send_file(target, Path(args.send))
        else:
            rc, err = send_text(target, args.text)
        if rc != 0: print(err, file=sys.stderr)
        return rc
    initial = Path(args.path) if args.path else None
    return DropApp(initial).run([])


if __name__ == "__main__":
    sys.exit(main())
