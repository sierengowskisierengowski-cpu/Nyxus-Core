#!/usr/bin/env python3
# ============================================================================
#  nyxus_settings_snapshots.py · NYXUS · Snapshots tab    rev 2026-05-13 r1
#
#  Standalone GTK4 panel for the "Time Machine" snapshot scrubber.
#  Imported by nyxus_settings.py → Backup → Snapshots, but also runnable
#  on its own via:  /usr/local/bin/nyxus snapshots
#
#  Reads `timeshift --list` (RSYNC + BTRFS modes both supported by the
#  same parser) and exposes restore + delete via the privileged helper
#  /usr/local/libexec/nyxus-backup-helper. No shell-out string concat —
#  every helper call is a flat argv list.
#
#  HARD POLICY (P6.27): Restore prompts a destructive-action confirmation
#  dialog AND re-routes through pkexec; this module never touches root
#  state directly.
#
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
from __future__ import annotations

import logging
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import gi  # type: ignore[import-not-found]

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

LOG_DIR = Path.home() / ".cache" / "nyxus"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "snapshots.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("nyxus_snapshots")

HELPER = "/usr/local/libexec/nyxus-backup-helper"

# Matches rows like:
#   1     >  2026-05-13_07-30-01   D  ...   pre-update
#   23      2026-05-12_22-00-00   M  ...   weekly
TIMESHIFT_ROW = re.compile(
    r"^\s*(\d+)\s*[>\s]\s*(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})"
    r"\s+([A-Z])\s+(.*)$"
)


@dataclass(frozen=True)
class Snapshot:
    num: int
    name: str            # e.g. 2026-05-13_07-30-01 — used as the helper id
    tag: str             # one of D/W/M/H/B (timeshift tags)
    description: str     # free-text comment


def _parse_timeshift(stdout: str) -> list[Snapshot]:
    out: list[Snapshot] = []
    for line in stdout.splitlines():
        m = TIMESHIFT_ROW.match(line)
        if not m:
            continue
        out.append(
            Snapshot(
                num=int(m.group(1)),
                name=m.group(2),
                tag=m.group(3),
                description=m.group(4).strip(),
            )
        )
    return out


def _list_snapshots() -> tuple[bool, list[Snapshot] | str]:
    """Run helper:list (no privilege required for read), parse output."""
    if not Path(HELPER).exists():
        return False, "Backup helper not installed."
    if not shutil.which("pkexec"):
        return False, "pkexec missing."
    try:
        proc = subprocess.run(
            ["pkexec", HELPER, "list"],
            capture_output=True, text=True, check=False, timeout=20,
        )
    except subprocess.TimeoutExpired:
        return False, "Helper timed out."
    if proc.returncode != 0:
        return False, proc.stderr.strip() or f"rc={proc.returncode}"
    return True, _parse_timeshift(proc.stdout)


def _helper(*args: str) -> tuple[bool, str]:
    cmd = ["pkexec", HELPER, *args]
    log.info("invoke: %s", shlex.join(cmd))
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=600,
        )
    except subprocess.TimeoutExpired:
        return False, "Helper timed out."
    if proc.returncode != 0:
        return False, proc.stderr.strip() or f"rc={proc.returncode}"
    return True, proc.stdout.strip()


# ── GTK panel ───────────────────────────────────────────────────────────
class SnapshotsPanel(Gtk.Box):
    """Self-contained widget; embed in Settings → Backup → Snapshots."""

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(16)
        self.set_margin_end(16)

        # ── Header row: title + refresh + create ────────────────────
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(label="<b>Snapshots</b>", use_markup=True, xalign=0)
        title.set_hexpand(True)
        header.append(title)

        refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh.set_tooltip_text("Refresh")
        refresh.connect("clicked", lambda *_: self.refresh())
        header.append(refresh)

        create = Gtk.Button(label="Create snapshot")
        create.add_css_class("suggested-action")
        create.connect("clicked", self._on_create_clicked)
        header.append(create)
        self.append(header)

        # ── Status banner ────────────────────────────────────────────
        self.status = Gtk.Label(label="", xalign=0)
        self.status.add_css_class("dim-label")
        self.append(self.status)

        # ── ScrolledWindow + ListBox ────────────────────────────────
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.list = Gtk.ListBox()
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list.add_css_class("boxed-list")
        scroller.set_child(self.list)
        self.append(scroller)

        self.refresh()

    # ── data flow ───────────────────────────────────────────────────
    def refresh(self) -> None:
        self.status.set_label("Loading…")
        # Drop existing rows.
        child = self.list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.list.remove(child)
            child = nxt

        ok, payload = _list_snapshots()
        if not ok:
            self.status.set_label(f"Could not list snapshots: {payload}")
            return
        snaps = payload  # type: ignore[assignment]
        if not snaps:
            self.status.set_label("No snapshots yet. Create one to get started.")
            return
        self.status.set_label(f"{len(snaps)} snapshot(s).")
        for s in snaps:
            self.list.append(self._build_row(s))

    def _build_row(self, s: Snapshot) -> Adw.ActionRow:
        row = Adw.ActionRow(
            title=s.name,
            subtitle=f"#{s.num} · tag {s.tag} · {s.description or '—'}",
        )
        restore = Gtk.Button(label="Restore")
        restore.add_css_class("destructive-action")
        restore.connect("clicked", lambda *_: self._on_restore_clicked(s))
        row.add_suffix(restore)
        delete = Gtk.Button.new_from_icon_name("user-trash-symbolic")
        delete.set_tooltip_text("Delete this snapshot")
        delete.connect("clicked", lambda *_: self._on_delete_clicked(s))
        row.add_suffix(delete)
        return row

    # ── handlers ────────────────────────────────────────────────────
    def _on_create_clicked(self, _btn: Gtk.Button) -> None:
        ok, msg = _helper("create", "manual: nyxus settings")
        self._toast("Snapshot created." if ok else f"Create failed: {msg}", ok)
        self.refresh()

    def _on_restore_clicked(self, s: Snapshot) -> None:
        dlg = Adw.AlertDialog(
            heading="Restore this snapshot?",
            body=(
                f"Snapshot {s.name} will be restored. The system will reboot "
                "into the restored state. Files modified since this snapshot "
                "may be lost.\n\nThis action cannot be undone from the UI."
            ),
        )
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("ok", "Restore and reboot")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        dlg.set_default_response("cancel")
        def _go(_d: Adw.AlertDialog, response: str) -> None:
            if response != "ok":
                return
            ok, msg = _helper("restore", s.name)
            self._toast("Restore queued." if ok else f"Restore failed: {msg}", ok)
        dlg.connect("response", _go)
        dlg.present(self.get_root())

    def _on_delete_clicked(self, s: Snapshot) -> None:
        dlg = Adw.AlertDialog(
            heading="Delete this snapshot?",
            body=f"Snapshot {s.name} will be permanently removed.",
        )
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("ok", "Delete")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        def _go(_d: Adw.AlertDialog, response: str) -> None:
            if response != "ok":
                return
            ok, msg = _helper("delete", s.name)
            self._toast("Deleted." if ok else f"Delete failed: {msg}", ok)
            self.refresh()
        dlg.connect("response", _go)
        dlg.present(self.get_root())

    def _toast(self, msg: str, success: bool) -> None:
        self.status.set_label(msg)
        css = "success" if success else "error"
        self.status.add_css_class(css)
        def _clear() -> bool:
            self.status.remove_css_class(css)
            return False
        GLib.timeout_add_seconds(3, _clear)


# ── standalone runner ──────────────────────────────────────────────────
def main() -> int:
    app = Adw.Application(application_id="com.nyxus.snapshots")
    def on_activate(_a: Adw.Application) -> None:
        win = Adw.ApplicationWindow(application=_a, title="NYXUS · Snapshots")
        win.set_default_size(720, 600)
        win.set_content(SnapshotsPanel())
        win.present()
    app.connect("activate", on_activate)
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
