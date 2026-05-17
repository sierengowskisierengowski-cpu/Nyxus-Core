#!/usr/bin/env python3
"""
NYXUS Backup — Timeshift wrapper GUI.

Lists existing snapshots from `timeshift --list`, lets the user create
on-demand snapshots, restore, or delete. Schedules are configured via
Timeshift's own JSON config (/etc/timeshift/timeshift.json) using its
official `--btrfs|--rsync` flags through pkexec.

Wired into Settings → System → Backup (page key "backup").
Keybind: Super+Ctrl+B (added in hyprland.lua).
Logs to ~/.cache/nyxus/backup.log.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gio, Gtk  # noqa: E402

HOME = Path(os.path.expanduser("~"))
CACHE = HOME / ".cache" / "nyxus"
CACHE.mkdir(parents=True, exist_ok=True)
LOG_FILE = CACHE / "backup.log"
TIMESHIFT_JSON = Path("/etc/timeshift/timeshift.json")

log = logging.getLogger("nyxus_backup")
log.setLevel(logging.INFO)
_h = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=512_000,
                                          backupCount=3)
_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(_h)


def have(cmd: str) -> str | None:
    return shutil.which(cmd)


HAS_TIMESHIFT = bool(have("timeshift"))
HAS_PKEXEC = bool(have("pkexec"))


@dataclass
class Snapshot:
    name: str
    tag: str          # e.g. "O" (on-demand), "B" (boot), "H" (hourly), "D"
    created: str
    desc: str = ""


# ---------- timeshift integration ----------
def _run_capture(cmd: list[str], timeout: int = 60) -> tuple[int, str, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, check=False)
        return r.returncode, r.stdout, r.stderr
    except FileNotFoundError:
        return 127, "", f"{cmd[0]} not found"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:
        return 1, "", str(e)


def list_snapshots() -> list[Snapshot]:
    if not HAS_TIMESHIFT:
        return []
    rc, out, _ = _run_capture(["pkexec", "timeshift", "--list"], timeout=30)
    if rc != 0:
        # try unprivileged (works for read on most setups)
        rc, out, _ = _run_capture(["timeshift", "--list"], timeout=30)
    if rc != 0:
        return []
    snaps: list[Snapshot] = []
    # rows look like: " 0  >  2026-05-12_03-00-01  O  Manual snapshot"
    row_re = re.compile(
        r"^\s*\d+\s*>?\s*(\S+)\s+([A-Z])\s*(.*)$")
    for line in out.splitlines():
        m = row_re.match(line)
        if not m:
            continue
        name = m.group(1)
        tag = m.group(2)
        desc = m.group(3).strip()
        snaps.append(Snapshot(name=name, tag=tag, created=name, desc=desc))
    return snaps


def load_schedule() -> dict[str, str]:
    """Read Timeshift schedule flags from its JSON config. Falls back to
    safe defaults so the UI never crashes when timeshift isn't yet
    initialized."""
    defaults = {"hourly": "false", "daily": "true",
                "weekly": "true", "monthly": "false", "boot": "true"}
    if not TIMESHIFT_JSON.exists():
        return defaults
    try:
        data = json.loads(TIMESHIFT_JSON.read_text())
        return {
            "hourly":  data.get("schedule_hourly",  defaults["hourly"]),
            "daily":   data.get("schedule_daily",   defaults["daily"]),
            "weekly":  data.get("schedule_weekly",  defaults["weekly"]),
            "monthly": data.get("schedule_monthly", defaults["monthly"]),
            "boot":    data.get("schedule_boot",    defaults["boot"]),
        }
    except Exception as e:
        log.warning("schedule read failed: %s", e)
        return defaults


# ---------- GUI ----------
GOLD = "#d4b87a"; INK = "#080a10"

CSS = f"""
.backup-window  {{ background: {INK}; }}
.backup-header  {{ color: {GOLD}; font-weight: 700; font-size: 18px;
                   letter-spacing: 0.04em; padding: 4px 0 12px 0; }}
.snap-row       {{ padding: 10px 12px; }}
.snap-name      {{ color: #fff; font-family: monospace; font-weight: 500; }}
.snap-tag       {{ color: {INK}; background: {GOLD}; border-radius: 4px;
                   padding: 1px 6px; font-size: 10px; font-weight: 700; }}
.snap-desc      {{ color: rgba(230,232,238,0.6); font-size: 11px; }}
.backup-empty   {{ color: rgba(230,232,238,0.55); padding: 60px 24px;
                   font-style: italic; font-size: 14px; }}
.action-primary {{ background: {GOLD}; color: {INK}; border-radius: 6px;
                   padding: 6px 14px; font-weight: 700; }}
""".encode("utf-8")


class BackupWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app)
        self.set_title("NYXUS Backup")
        self.set_default_size(820, 580)
        self.add_css_class("backup-window")
        self.snapshots: list[Snapshot] = []

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        btn_new = Gtk.Button.new_from_icon_name("list-add-symbolic")
        btn_new.set_tooltip_text("Create a new snapshot now")
        btn_new.connect("clicked", lambda *_: self.create_snapshot())
        header.pack_start(btn_new)

        btn_refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        btn_refresh.set_tooltip_text("Refresh snapshot list (F5)")
        btn_refresh.connect("clicked", lambda *_: self.refresh())
        header.pack_start(btn_refresh)

        btn_settings = Gtk.Button.new_from_icon_name("preferences-system-symbolic")
        btn_settings.set_tooltip_text("Schedule (open in Settings)")
        btn_settings.connect("clicked", lambda *_: self.open_schedule())
        header.pack_end(btn_settings)

        # Time Machine — open the snapshot scrubber on the selected
        # snapshot. Discoverable from the main backup window AND it's
        # the same Adw.Window pattern as Restore so users build muscle
        # memory.
        btn_scrub = Gtk.Button.new_from_icon_name("document-open-recent-symbolic")
        btn_scrub.set_tooltip_text("Browse files inside selected snapshot (Time Machine)")
        btn_scrub.connect("clicked", lambda *_: self.open_snapshot_browser())
        header.pack_end(btn_scrub)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        outer.set_margin_start(16); outer.set_margin_end(16)
        outer.set_margin_top(8); outer.set_margin_bottom(12)
        toolbar.set_content(outer)

        title = Gtk.Label(label="System Snapshots", xalign=0)
        title.add_css_class("backup-header")
        outer.append(title)

        if not HAS_TIMESHIFT:
            warn = Gtk.Label(
                label="Timeshift is not installed. Install it from the App "
                      "Store (Settings → System → Backup) to enable "
                      "snapshots.",
                xalign=0)
            warn.add_css_class("backup-empty")
            warn.set_wrap(True)
            outer.append(warn)
        else:
            sched = load_schedule()
            sched_lbl = Gtk.Label(
                label=("Schedule:  "
                       + ("hourly · " if sched["hourly"] == "true" else "")
                       + ("daily · " if sched["daily"] == "true" else "")
                       + ("weekly · " if sched["weekly"] == "true" else "")
                       + ("monthly · " if sched["monthly"] == "true" else "")
                       + ("on-boot" if sched["boot"] == "true" else "")
                       ).rstrip(" ·"),
                xalign=0)
            sched_lbl.add_css_class("dim-label")
            outer.append(sched_lbl)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        outer.append(scroll)

        self.list_box = Gtk.ListBox()
        self.list_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.list_box.add_css_class("boxed-list")
        scroll.set_child(self.list_box)

        # bottom action bar
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.set_halign(Gtk.Align.END)
        bar.set_margin_top(10)
        outer.append(bar)
        self.btn_restore = Gtk.Button(label="Restore Selected")
        self.btn_restore.connect("clicked",
                                  lambda *_: self.restore_selected())
        self.btn_restore.add_css_class("destructive-action")
        bar.append(self.btn_restore)
        self.btn_delete = Gtk.Button(label="Delete")
        self.btn_delete.connect("clicked",
                                 lambda *_: self.delete_selected())
        bar.append(self.btn_delete)

        self.toast = Adw.ToastOverlay()
        self.toast.set_child(toolbar)
        self.set_content(self.toast)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

        GLib.idle_add(self.refresh)

    def _on_key(self, c, kv, kc, st):
        if kv == Gdk.KEY_F5:
            self.refresh(); return True
        return False

    def refresh(self) -> bool:
        self.snapshots = list_snapshots() if HAS_TIMESHIFT else []
        child = self.list_box.get_first_child()
        while child is not None:
            n = child.get_next_sibling(); self.list_box.remove(child); child = n
        if not self.snapshots:
            row = Gtk.ListBoxRow()
            empty = Gtk.Label(label="No snapshots yet.\n"
                                    "Click + above to create one.",
                              xalign=0)
            empty.add_css_class("backup-empty")
            empty.set_wrap(True)
            row.set_child(empty); row.set_selectable(False)
            self.list_box.append(row)
            self.btn_restore.set_sensitive(False)
            self.btn_delete.set_sensitive(False)
            return False
        for s in self.snapshots:
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            box.add_css_class("snap-row")
            tag_lbl = Gtk.Label(label=s.tag); tag_lbl.add_css_class("snap-tag")
            box.append(tag_lbl)
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            n = Gtk.Label(label=s.name, xalign=0); n.add_css_class("snap-name")
            inner.append(n)
            if s.desc:
                d = Gtk.Label(label=s.desc, xalign=0)
                d.add_css_class("snap-desc"); inner.append(d)
            inner.set_hexpand(True); box.append(inner)
            row.set_child(box); row.snap = s  # type: ignore[attr-defined]
            self.list_box.append(row)
        self.btn_restore.set_sensitive(True)
        self.btn_delete.set_sensitive(True)
        return False

    def _selected_snapshot(self) -> Snapshot | None:
        row = self.list_box.get_selected_row()
        if row is None: return None
        return getattr(row, "snap", None)

    def create_snapshot(self) -> None:
        if not HAS_TIMESHIFT or not HAS_PKEXEC:
            self.toast.add_toast(Adw.Toast.new("Timeshift/pkexec missing"))
            return
        comment = f"NYXUS · {datetime.now().isoformat(timespec='seconds')}"
        log.info("create snapshot: %s", comment)
        cmd = ["pkexec", "timeshift", "--create",
               "--comments", comment, "--tags", "O"]
        self._run_async(cmd, "Creating snapshot…",
                        "Snapshot created.", "Snapshot failed.")

    def restore_selected(self) -> None:
        snap = self._selected_snapshot()
        if snap is None:
            self.toast.add_toast(Adw.Toast.new("Select a snapshot first"))
            return
        dialog = Adw.MessageDialog.new(
            self,
            "Restore this snapshot?",
            f"Your system will revert to:\n\n{snap.name}\n\n"
            f"This reboots into the restore environment.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("restore", "Restore")
        dialog.set_response_appearance(
            "restore", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_restore_resp, snap)
        dialog.present()

    def _on_restore_resp(self, dialog, response, snap):
        if response != "restore": return
        cmd = ["pkexec", "timeshift", "--restore",
               "--snapshot", snap.name, "--yes"]
        self._run_async(cmd, "Restoring…",
                        "Restore queued — system will reboot.",
                        "Restore failed.")

    def delete_selected(self) -> None:
        snap = self._selected_snapshot()
        if snap is None:
            self.toast.add_toast(Adw.Toast.new("Select a snapshot first"))
            return
        cmd = ["pkexec", "timeshift", "--delete",
               "--snapshot", snap.name, "--yes"]
        self._run_async(cmd, "Deleting…",
                        "Snapshot deleted.", "Delete failed.")

    def _run_async(self, cmd: list[str], busy: str,
                   ok: str, err: str) -> None:
        self.toast.add_toast(Adw.Toast.new(busy))
        log.info("run: %s", " ".join(cmd))
        def done(proc, res):
            try:
                _, _stdout, _stderr = proc.communicate_utf8_finish(res)
                rc = proc.get_exit_status()
            except Exception as e:
                log.error("async wait failed: %s", e); rc = 1
            self.toast.add_toast(Adw.Toast.new(ok if rc == 0 else err))
            self.refresh()
        try:
            proc = Gio.Subprocess.new(
                cmd, Gio.SubprocessFlags.STDOUT_PIPE
                | Gio.SubprocessFlags.STDERR_PIPE)
            proc.communicate_utf8_async(None, None, done)
        except Exception as e:
            log.error("spawn failed: %s", e)
            self.toast.add_toast(Adw.Toast.new(err))

    def open_schedule(self) -> None:
        try:
            subprocess.Popen(
                ["nyxus-settings", "--page", "backup"],
                start_new_session=True)
        except Exception:
            self.toast.add_toast(Adw.Toast.new(
                "Open Settings → System → Backup to schedule."))

    # ─────────────────────────────────────────────────────────────────
    # Time Machine snapshot scrubber.
    #
    # macOS Time Machine lets the user "fly" through past snapshots and
    # browse files at that point in time. We surface the same idea with
    # a list of snapshots + their actual mounted paths (Timeshift mounts
    # under /run/timeshift/backup/snapshots/<id>/localhost/). When the
    # user picks one, we open that path in the file manager — same
    # navigation, same file metadata, copy-out works exactly like
    # macOS Finder Time Machine.
    # ─────────────────────────────────────────────────────────────────
    SNAP_ROOT = Path("/run/timeshift/backup/snapshots")

    def open_snapshot_browser(self) -> None:
        snap = self._selected_snapshot()
        if snap is None:
            self.toast.add_toast(Adw.Toast.new(
                "Select a snapshot first to browse its files"))
            return
        self._present_scrubber(snap)

    def _present_scrubber(self, focus_snap) -> None:
        win = Adw.Window(transient_for=self, modal=True)
        win.set_title("Time Machine — Snapshot Scrubber")
        win.set_default_size(720, 480)
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        win.set_content(outer)

        header = Adw.HeaderBar()
        outer.append(header)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.set_margin_start(16); body.set_margin_end(16)
        body.set_margin_top(12); body.set_margin_bottom(12)
        outer.append(body)

        intro = Gtk.Label(
            label="Pick a moment in time. Each snapshot mounts a "
                  "complete read-only copy of the system at that "
                  "instant — copy any file out to restore it without "
                  "touching the live disk.",
            xalign=0)
        intro.set_wrap(True)
        intro.add_css_class("dim-label")
        body.append(intro)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        listbox.add_css_class("boxed-list")
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_vexpand(True)
        scroll.set_child(listbox)
        body.append(scroll)

        if not self.snapshots:
            empty = Gtk.Label(
                label="No snapshots — create one from the main window first.",
                xalign=0.5)
            empty.add_css_class("backup-empty")
            listbox.append(empty)
        else:
            for s in self.snapshots:
                mount = self.SNAP_ROOT / s.name / "localhost"
                mounted = mount.exists()
                row = Adw.ActionRow(
                    title=s.name,
                    subtitle=(str(mount) if mounted
                              else "not mounted (Timeshift mounts on demand)"))
                if mounted:
                    btn = Gtk.Button(label="Browse")
                    btn.add_css_class("suggested-action")
                    btn.connect(
                        "clicked",
                        lambda _b, m=str(mount): self._open_in_files(m))
                    row.add_suffix(btn)
                else:
                    note = Gtk.Label(label="—")
                    note.add_css_class("dim-label")
                    row.add_suffix(note)
                listbox.append(row)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_halign(Gtk.Align.END)
        body.append(actions)
        close_btn = Gtk.Button(label="Close")
        close_btn.connect("clicked", lambda *_: win.close())
        actions.append(close_btn)

        win.present()

    def _open_in_files(self, path: str) -> None:
        for fm in ("nyxus-files", "nautilus", "thunar", "xdg-open"):
            if shutil.which(fm):
                try:
                    subprocess.Popen([fm, path], start_new_session=True)
                    return
                except Exception as e:
                    log.warning("scrubber open via %s failed: %s", fm, e)
                    continue
        self.toast.add_toast(Adw.Toast.new(
            f"No file manager available to open {path}"))


class BackupApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.nyxus.backup")
    def do_activate(self):  # type: ignore[override]
        try:
            Adw.StyleManager.get_default().set_color_scheme(
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
        BackupWindow(self).present()


def main() -> int:
    return BackupApp().run([])


if __name__ == "__main__":
    sys.exit(main())
