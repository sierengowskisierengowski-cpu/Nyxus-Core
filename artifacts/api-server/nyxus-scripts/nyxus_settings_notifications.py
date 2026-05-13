#!/usr/bin/env python3
# ============================================================================
#  nyxus_settings_notifications.py · NYXUS · Notifications  rev 2026-05-13 r1
#
#  Standalone GTK4 panel for Settings → Notifications (P7.34).
#
#  Wraps `swaync-client --list-history -j` and renders the history. Also
#  surfaces DND toggle + clear-all action. Refresh is manual + 5 s
#  background poll while the window has focus.
#
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
from __future__ import annotations

import datetime as _dt
import json
import logging
import shlex
import shutil
import subprocess
from pathlib import Path

import gi  # type: ignore[import-not-found]

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

LOG_DIR = Path.home() / ".cache" / "nyxus"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "notifications.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("nyxus_notifications")


def _swaync(*args: str) -> tuple[bool, str]:
    if not shutil.which("swaync-client"):
        return False, "swaync-client not installed"
    cmd = ["swaync-client", *args]
    log.info("invoke: %s", shlex.join(cmd))
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=10,
        )
    except subprocess.TimeoutExpired:
        return False, "swaync-client timed out"
    if proc.returncode != 0:
        return False, proc.stderr.strip() or f"rc={proc.returncode}"
    return True, proc.stdout.rstrip()


def _format_ts(raw: object) -> str:
    try:
        v = float(raw)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return ""
    # swaync emits microseconds since epoch (or seconds in newer builds);
    # autodetect by magnitude.
    if v > 1e14:
        v /= 1_000_000.0
    elif v > 1e11:
        v /= 1000.0
    try:
        return _dt.datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M:%S")
    except (OSError, OverflowError, ValueError):
        return ""


class NotificationsPanel(Gtk.Box):
    POLL_SECONDS = 5

    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(16)
        self.set_margin_end(16)

        # ── Header: title + DND switch + clear-all ──────────────────
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = Gtk.Label(
            label="<b>Notifications history</b>",
            use_markup=True, xalign=0,
        )
        title.set_hexpand(True)
        header.append(title)

        self.dnd = Gtk.Switch(valign=Gtk.Align.CENTER)
        self.dnd.set_tooltip_text("Do Not Disturb")
        # NOTE: do NOT connect the toggle handler here — _sync_dnd() (called
        # below in __init__) calls set_active() which would otherwise fire
        # _on_dnd_toggled() and flip the real DND state during init.
        self._dnd_handler_id: int = 0
        header.append(self.dnd)

        clear = Gtk.Button(label="Clear all")
        clear.add_css_class("destructive-action")
        clear.connect("clicked", self._on_clear)
        header.append(clear)

        refresh = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        refresh.set_tooltip_text("Refresh")
        refresh.connect("clicked", lambda *_: self.refresh())
        header.append(refresh)
        self.append(header)

        self.banner = Gtk.Label(label="", xalign=0)
        self.banner.add_css_class("dim-label")
        self.append(self.banner)

        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.list = Gtk.ListBox()
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list.add_css_class("boxed-list")
        scroller.set_child(self.list)
        self.append(scroller)

        self._poll_id: int | None = None
        self.refresh()
        # Sync DND state FIRST, then connect the handler. Otherwise the
        # initial set_active() during sync would trigger a real DND toggle.
        self._sync_dnd()
        self._dnd_handler_id = self.dnd.connect(
            "notify::active", self._on_dnd_toggled,
        )
        self._start_polling()

    # ── data flow ───────────────────────────────────────────────────
    def refresh(self) -> None:
        # Drop existing rows.
        child = self.list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.list.remove(child)
            child = nxt

        ok, payload = _swaync("--list-history", "-j")
        if not ok:
            self.banner.set_label(
                f"Could not read swaync history: {payload}")
            placeholder = Adw.ActionRow(
                title="No history yet",
                subtitle="Notifications will appear here once swaync receives any.",
            )
            self.list.append(placeholder)
            return

        try:
            doc = json.loads(payload or "[]")
        except json.JSONDecodeError as exc:
            self.banner.set_label(f"swaync output not JSON: {exc}")
            return

        items = doc if isinstance(doc, list) else doc.get("data", [])
        if not items:
            placeholder = Adw.ActionRow(
                title="No notifications in history",
                subtitle="When swaync sends a notification, it lands here.",
            )
            self.list.append(placeholder)
            return

        self.banner.set_label(f"{len(items)} notification(s).")
        for it in items:
            self.list.append(self._build_row(it))

    def _build_row(self, n: dict) -> Adw.ActionRow:
        app = str(n.get("app-name") or n.get("app_name") or "?")
        summary = str(n.get("summary") or "")
        body = str(n.get("body") or "")
        ts = _format_ts(n.get("time"))
        subtitle_parts = [s for s in (body, ts and f"· {ts}") if s]
        row = Adw.ActionRow(
            title=f"<b>{GLib.markup_escape_text(app)}</b> — "
                  f"{GLib.markup_escape_text(summary)}",
            subtitle=" ".join(subtitle_parts),
        )
        row.set_use_markup(True)
        return row

    # ── DND ─────────────────────────────────────────────────────────
    def _sync_dnd(self) -> None:
        ok, val = _swaync("--get-dnd")
        if ok:
            self.dnd.set_active("true" in val.lower())

    def _on_dnd_toggled(self, *_a: object) -> None:
        ok, msg = _swaync("--toggle-dnd")
        if not ok:
            self.banner.set_label(f"DND toggle failed: {msg}")
            # Roll back the switch using the stored handler id to avoid
            # re-entering this handler.
            if self._dnd_handler_id:
                self.dnd.handler_block(self._dnd_handler_id)
                self.dnd.set_active(not self.dnd.get_active())
                self.dnd.handler_unblock(self._dnd_handler_id)

    def _on_clear(self, *_a: object) -> None:
        dlg = Adw.AlertDialog(
            heading="Clear all notifications?",
            body="History will be wiped from swaync.",
        )
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("ok", "Clear")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        def _go(_d: Adw.AlertDialog, response: str) -> None:
            if response != "ok":
                return
            ok, msg = _swaync("--close-all")
            if not ok:
                self.banner.set_label(f"Clear failed: {msg}")
            self.refresh()
        dlg.connect("response", _go)
        dlg.present(self.get_root())

    # ── poll ────────────────────────────────────────────────────────
    def _start_polling(self) -> None:
        if self._poll_id is not None:
            return
        self._poll_id = GLib.timeout_add_seconds(
            self.POLL_SECONDS, self._poll_tick,
        )

    def _poll_tick(self) -> bool:
        self.refresh()
        return True  # keep ticking


def main() -> int:
    app = Adw.Application(application_id="com.nyxus.notifications")
    def on_activate(_a: Adw.Application) -> None:
        win = Adw.ApplicationWindow(application=_a,
                                    title="NYXUS · Notifications")
        win.set_default_size(720, 600)
        win.set_content(NotificationsPanel())
        win.present()
    app.connect("activate", on_activate)
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
