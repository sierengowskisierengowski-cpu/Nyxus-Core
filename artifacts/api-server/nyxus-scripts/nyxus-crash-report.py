#!/usr/bin/env python3
"""
NYXUS Crash Reporter UI — list every digest written by nyxus-crashd into
~/.cache/nyxus/crashes/, show details, copy stack/text, and (optionally)
submit to a NYXUS-managed crash endpoint.

Submission is gated by:
  • ~/.config/nyxus/crashd.endpoint  — base URL (e.g. https://api.nyxus...)
  • ~/.config/nyxus/account.token    — bearer token from NYXUS Account
The actual POST goes to <endpoint>/crash-reports as gzipped JSON.

Submission is OFF by default. The endpoint is read from
~/.config/nyxus/crashd.endpoint (one line). When absent or empty, the
"Submit" button is disabled and a friendly note explains why.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gio, Gtk  # noqa: E402

HOME = Path(os.path.expanduser("~"))
CACHE = HOME / ".cache" / "nyxus"
CRASH_DIR = CACHE / "crashes"
CRASH_DIR.mkdir(parents=True, exist_ok=True)
ENDPOINT_FILE = HOME / ".config" / "nyxus" / "crashd.endpoint"
LOG_FILE = CACHE / "crash-report.log"

log = logging.getLogger("nyxus_crash_report")
log.setLevel(logging.INFO)
_h = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=256_000,
                                          backupCount=2)
_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(_h)

GOLD = "#d4b87a"; INK = "#080a10"
CSS = f"""
.crash-window {{ background: {INK}; }}
.crash-header {{ color: {GOLD}; font-weight: 700; font-size: 17px;
                 padding: 4px 0 8px 0; }}
.crash-empty  {{ color: rgba(230,232,238,0.55); padding: 60px 24px;
                 font-style: italic; font-size: 14px; }}
.crash-detail {{ color: #e6e8ee; font-family: monospace; font-size: 11px; }}
.crash-row    {{ padding: 8px 12px; }}
""".encode("utf-8")


def list_crashes() -> list[Path]:
    return sorted(CRASH_DIR.glob("*.json"), reverse=True)


def endpoint() -> str | None:
    try:
        if ENDPOINT_FILE.exists():
            v = ENDPOINT_FILE.read_text().strip()
            return v or None
    except Exception:
        return None
    return None


class ReporterWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app)
        self.set_title("NYXUS Crash Reports")
        self.set_default_size(900, 600)
        self.add_css_class("crash-window")

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)
        btn_clear = Gtk.Button.new_from_icon_name("edit-clear-all-symbolic")
        btn_clear.set_tooltip_text("Delete all stored crash digests")
        btn_clear.connect("clicked", lambda *_: self.clear_all())
        header.pack_end(btn_clear)

        # Split: list on left, detail on right
        split = Adw.NavigationSplitView()
        toolbar.set_content(split)

        # ── sidebar
        sb_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sb_head = Adw.HeaderBar()
        sb_head.set_title_widget(Gtk.Label(label="Reports"))
        sb_box.append(sb_head)
        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.add_css_class("navigation-sidebar")
        self.list_box.connect("row-selected", self._on_row_selected)
        scroll.set_child(self.list_box)
        sb_box.append(scroll)
        split.set_sidebar(Adw.NavigationPage.new(sb_box, "Reports"))

        # ── detail
        det = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        det_head = Adw.HeaderBar()
        title = Gtk.Label(label="Crash Reports"); title.add_css_class("crash-header")
        det_head.set_title_widget(title)
        det.append(det_head)

        self.text = Gtk.TextView()
        self.text.set_editable(False); self.text.set_monospace(True)
        self.text.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.text.add_css_class("crash-detail")
        self.text.set_left_margin(14); self.text.set_right_margin(14)
        self.text.set_top_margin(10);  self.text.set_bottom_margin(10)
        det_scroll = Gtk.ScrolledWindow(); det_scroll.set_vexpand(True)
        det_scroll.set_child(self.text)
        det.append(det_scroll)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_halign(Gtk.Align.END)
        actions.set_margin_top(8); actions.set_margin_bottom(8)
        actions.set_margin_end(12)
        det.append(actions)

        self.btn_copy = Gtk.Button(label="Copy")
        self.btn_copy.connect("clicked", lambda *_: self.copy_current())
        actions.append(self.btn_copy)

        self.btn_open = Gtk.Button(label="Open coredump in terminal")
        self.btn_open.connect("clicked", lambda *_: self.open_in_terminal())
        actions.append(self.btn_open)

        self.btn_submit = Gtk.Button(label="Submit")
        self.btn_submit.add_css_class("suggested-action")
        self.btn_submit.connect("clicked", lambda *_: self.submit_current())
        actions.append(self.btn_submit)

        self.toast = Adw.ToastOverlay(); self.toast.set_child(toolbar)
        split.set_content(Adw.NavigationPage.new(det, "Detail"))
        self.set_content(self.toast)

        self.current: Path | None = None
        GLib.idle_add(self.refresh)

    def refresh(self) -> bool:
        # Drop existing rows
        c = self.list_box.get_first_child()
        while c is not None:
            n = c.get_next_sibling(); self.list_box.remove(c); c = n

        crashes = list_crashes()
        if not crashes:
            row = Gtk.ListBoxRow(); row.set_selectable(False)
            empty = Gtk.Label(label="No crash reports.\nGood news!", xalign=0)
            empty.add_css_class("crash-empty"); empty.set_wrap(True)
            row.set_child(empty); self.list_box.append(row)
            self._set_text("Nothing to show. The crash watcher records "
                           "future events into:\n\n  "
                           f"{CRASH_DIR}\n")
            for b in (self.btn_copy, self.btn_open, self.btn_submit):
                b.set_sensitive(False)
            return False
        for path in crashes:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            box.add_css_class("crash-row")
            try:
                data = json.loads(path.read_text())
                comm = data.get("comm") or "?"
                sig  = data.get("signal") or "?"
                head = Gtk.Label(label=f"{comm}  ·  {sig}", xalign=0)
                head.add_css_class("snap-name")
                box.append(head)
                sub = Gtk.Label(label=path.stem, xalign=0)
                sub.add_css_class("snap-desc"); box.append(sub)
            except Exception:
                box.append(Gtk.Label(label=path.name, xalign=0))
            row.set_child(box)
            row.path = path  # type: ignore[attr-defined]
            self.list_box.append(row)
        first = self.list_box.get_row_at_index(0)
        if first is not None:
            self.list_box.select_row(first)
        return False

    def _on_row_selected(self, _lb, row):
        if row is None: return
        path = getattr(row, "path", None)
        if path is None:
            return
        self.current = path
        try:
            data = json.loads(path.read_text())
            self._set_text(json.dumps(data, indent=2))
        except Exception as e:
            self._set_text(f"Failed to read {path}: {e}")
        for b in (self.btn_copy, self.btn_open):
            b.set_sensitive(True)
        self.btn_submit.set_sensitive(endpoint() is not None)
        if endpoint() is None:
            self.btn_submit.set_tooltip_text(
                "Set ~/.config/nyxus/crashd.endpoint to enable submission.")

    def _set_text(self, body: str) -> None:
        buf = self.text.get_buffer()
        buf.set_text(body)

    def copy_current(self) -> None:
        if self.current is None: return
        clip = Gdk.Display.get_default().get_clipboard()
        try:
            clip.set(self.current.read_text())
            self.toast.add_toast(Adw.Toast.new("Copied report to clipboard"))
        except Exception as e:
            log.warning("copy failed: %s", e)
            self.toast.add_toast(Adw.Toast.new("Copy failed"))

    def open_in_terminal(self) -> None:
        if self.current is None: return
        try:
            data = json.loads(self.current.read_text())
            pid = data.get("pid")
        except Exception:
            pid = None
        sh = (f"coredumpctl info {pid}; echo; "
              f"echo 'Press Enter to close.'; read _") if pid else \
             ("coredumpctl list; echo; "
              "echo 'Press Enter to close.'; read _")
        for term in ("alacritty", "kitty", "foot", "wezterm", "xterm"):
            if shutil.which(term):
                subprocess.Popen([term, "-e", "sh", "-c", sh],
                                 start_new_session=True)
                return
        self.toast.add_toast(Adw.Toast.new("No terminal emulator found"))

    def submit_current(self) -> None:
        ep = endpoint()
        if self.current is None or ep is None:
            self.toast.add_toast(Adw.Toast.new("No endpoint configured"))
            return
        if not shutil.which("curl"):
            self.toast.add_toast(Adw.Toast.new("curl missing"))
            return
        # Bearer token shares the same KV used by NYXUS Account sync —
        # one device-scoped opaque token, never a password. Reports are
        # ALWAYS gzipped before submission to halve transit size and to
        # match the api-server's accepted encodings (gzip OR raw JSON).
        token = self._read_token()
        if not token:
            self.toast.add_toast(Adw.Toast.new(
                "No NYXUS Account token — open Settings → NYXUS Account"))
            return
        url = ep.rstrip("/") + "/crash-reports"
        log.info("submit %s → %s (gzipped, bearer ****%s)",
                 self.current, url, token[-4:])
        try:
            subprocess.Popen(
                ["sh", "-c",
                 f"gzip -c {shlex.quote(str(self.current))} | "
                 f"curl -fsS -X POST "
                 f"-H 'Authorization: Bearer {token}' "
                 f"-H 'Content-Type: application/gzip' "
                 f"--data-binary @- {shlex.quote(url)} "
                 f">>~/.cache/nyxus/crash-upload.log 2>&1"],
                start_new_session=True)
            self.toast.add_toast(Adw.Toast.new("Report submitted"))
        except Exception as e:
            log.error("submit failed: %s", e)
            self.toast.add_toast(Adw.Toast.new("Submit failed"))

    def _read_token(self) -> str | None:
        """Read the NYXUS Account bearer token. Same file used by the
        sync client; we deliberately do NOT prompt or generate one here
        — that's the Account page's job. Missing token → loud refusal."""
        for cand in (
            HOME / ".config" / "nyxus" / "account.token",
            HOME / ".config" / "nyxus" / "crashd.token",
        ):
            try:
                if cand.exists():
                    v = cand.read_text().strip()
                    if v:
                        return v
            except Exception:
                continue
        return None

    def clear_all(self) -> None:
        for p in list_crashes():
            try: p.unlink()
            except Exception: pass
        self.refresh()
        self.toast.add_toast(Adw.Toast.new("All reports cleared"))


class ReporterApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.nyxus.crashreport")
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
        ReporterWindow(self).present()


def main() -> int:
    return ReporterApp().run([])


if __name__ == "__main__":
    sys.exit(main())
