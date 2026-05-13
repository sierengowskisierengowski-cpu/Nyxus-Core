#!/usr/bin/env python3
# ============================================================================
#  nyxus_parental.py · NYXUS · Parental Controls   rev 2026-05-13 r1
#
#  GTK4 panel for the Settings → Privacy → Parental Controls page.
#
#  HARD POLICY: this UI ships installed, but every control is OFF by
#  default. The first toggle requires a confirmation dialog AND a polkit
#  prompt. Restrictions are written to /etc/nyxus/parental.toml by the
#  privileged helper /usr/local/libexec/nyxus-parental-helper, NOT this
#  process — this UI never edits root-owned files directly.
#
#  Surface area (ALL default OFF):
#    1. Time limits         — daily allowance + bedtime window
#    2. App allowlist       — block a curated set of apps from launching
#    3. Web filter          — sync to /etc/hosts.d/parental-blocklist
#    4. SafeSearch          — DNS rewrite to family-safe resolvers
#    5. Pause now           — single click freezes the user session
#
#  Everything is local. No external accounts, no cloud sync.
#
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
from __future__ import annotations

import json
import logging
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Any

import gi  # type: ignore[import-not-found]

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

LOG_DIR = Path.home() / ".cache" / "nyxus"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "parental.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("nyxus_parental")

POLICY_PATH = Path("/etc/nyxus/parental.toml")
HELPER = "/usr/local/libexec/nyxus-parental-helper"


# ── helper-call wrapper ─────────────────────────────────────────────────
def _pkexec(*args: str) -> tuple[bool, str]:
    """Invoke the parental helper via pkexec; never shell-out a string.

    args are passed as a flat argv list, never composed with ``shell=True``.
    """
    if not shutil.which("pkexec"):
        return False, "pkexec not available"
    if not Path(HELPER).exists():
        return False, f"helper missing: {HELPER}"
    cmd = ["pkexec", HELPER, *args]
    log.info("invoking helper: %s", shlex.join(cmd))
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=30
        )
    except subprocess.TimeoutExpired:
        return False, "helper timed out"
    if proc.returncode != 0:
        log.warning("helper rc=%s err=%s", proc.returncode, proc.stderr.strip())
        return False, proc.stderr.strip() or f"rc={proc.returncode}"
    return True, proc.stdout.strip()


def _read_policy() -> dict[str, Any]:
    """Read /etc/nyxus/parental.toml. Returns the all-OFF default if missing.

    We deliberately accept JSON (the helper writes JSON for portability;
    .toml is the convention but every field maps 1:1).
    """
    if not POLICY_PATH.exists():
        return {
            "enabled": False,
            "user": "",
            "time_limits": {"enabled": False, "daily_minutes": 0,
                            "bedtime_start": "22:00", "bedtime_end": "07:00"},
            "app_allowlist": {"enabled": False, "apps": []},
            "web_filter":    {"enabled": False, "blocklist": []},
            "safesearch":    {"enabled": False},
        }
    try:
        return json.loads(POLICY_PATH.read_text())
    except Exception as exc:  # pragma: no cover — best-effort fallback
        log.warning("could not parse %s: %s", POLICY_PATH, exc)
        return {"enabled": False}


# ── GTK panel ───────────────────────────────────────────────────────────
class ParentalWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application) -> None:
        super().__init__(application=app, title="NYXUS · Parental Controls")
        self.set_default_size(720, 640)
        self.policy = _read_policy()

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        page = Adw.PreferencesPage()
        scroller.set_child(page)
        toolbar.set_content(scroller)
        self.set_content(toolbar)

        # Master kill switch.
        master = Adw.PreferencesGroup(
            title="Parental Controls",
            description=(
                "All controls are OFF by default. Enabling any control "
                "writes a policy to /etc/nyxus/parental.toml via a polkit "
                "prompt. Disable to remove all restrictions."
            ),
        )
        self.master_row = Adw.SwitchRow(
            title="Enable parental controls for this device",
            active=bool(self.policy.get("enabled")),
        )
        self.master_row.connect("notify::active", self._on_master_toggled)
        master.add(self.master_row)
        page.add(master)

        # Time limits.
        tl = Adw.PreferencesGroup(title="Screen Time")
        self.tl_row = Adw.SwitchRow(
            title="Daily time limit",
            subtitle="Lock the session after the daily allowance is exhausted.",
            active=self.policy["time_limits"]["enabled"],
        )
        self.tl_row.connect("notify::active", lambda *_: self._save())
        tl.add(self.tl_row)

        self.daily = Adw.SpinRow.new_with_range(0, 1440, 15)
        self.daily.set_title("Daily allowance (minutes)")
        self.daily.set_value(int(self.policy["time_limits"]["daily_minutes"]))
        self.daily.connect("notify::value", lambda *_: self._save())
        tl.add(self.daily)
        page.add(tl)

        # App allowlist.
        al = Adw.PreferencesGroup(title="App Allowlist")
        self.al_row = Adw.SwitchRow(
            title="Restrict to allowed apps only",
            subtitle="Block .desktop launches outside the allowlist.",
            active=self.policy["app_allowlist"]["enabled"],
        )
        self.al_row.connect("notify::active", lambda *_: self._save())
        al.add(self.al_row)
        page.add(al)

        # Web filter.
        wf = Adw.PreferencesGroup(title="Web Filter")
        self.wf_row = Adw.SwitchRow(
            title="Block adult/violent sites",
            subtitle="Syncs a curated blocklist into /etc/hosts.d/.",
            active=self.policy["web_filter"]["enabled"],
        )
        self.wf_row.connect("notify::active", lambda *_: self._save())
        wf.add(self.wf_row)

        self.ss_row = Adw.SwitchRow(
            title="SafeSearch DNS",
            subtitle="Route to OpenDNS FamilyShield (208.67.222.123).",
            active=self.policy["safesearch"]["enabled"],
        )
        self.ss_row.connect("notify::active", lambda *_: self._save())
        wf.add(self.ss_row)
        page.add(wf)

        # Pause now.
        pn = Adw.PreferencesGroup(title="Immediate Action")
        pause_row = Adw.ActionRow(
            title="Pause this session now",
            subtitle="Locks the screen and disables app launches until you unpause.",
        )
        pause_btn = Gtk.Button(label="Pause now")
        pause_btn.add_css_class("destructive-action")
        pause_btn.connect("clicked", self._on_pause_clicked)
        pause_row.add_suffix(pause_btn)
        pn.add(pause_row)
        page.add(pn)

        # Footer status banner.
        self.banner = Adw.Banner(revealed=False)
        toolbar.add_top_bar(self.banner)

        self._sync_sensitivity()

    # ── handlers ────────────────────────────────────────────────────────
    def _on_master_toggled(self, switch: Adw.SwitchRow, *_: Any) -> None:
        self._sync_sensitivity()
        if switch.get_active():
            self._show_first_enable_warning()
        self._save()

    def _on_pause_clicked(self, *_: Any) -> None:
        ok, msg = _pkexec("pause", os.environ.get("USER", ""))
        self._flash("Session paused." if ok else f"Pause failed: {msg}",
                    success=ok)

    def _sync_sensitivity(self) -> None:
        on = self.master_row.get_active()
        for row in (self.tl_row, self.daily, self.al_row,
                    self.wf_row, self.ss_row):
            row.set_sensitive(on)

    def _show_first_enable_warning(self) -> None:
        if self.policy.get("enabled"):
            return
        dlg = Adw.AlertDialog(
            heading="Enable Parental Controls?",
            body=(
                "You are about to write a parental-controls policy to this "
                "device. This will require an administrator prompt for "
                "every change you make on this page.\n\n"
                "All restrictions can be removed by disabling the master "
                "switch at any time."
            ),
        )
        dlg.add_response("cancel", "Cancel")
        dlg.add_response("ok", "Enable")
        dlg.set_default_response("cancel")
        dlg.set_response_appearance("ok", Adw.ResponseAppearance.DESTRUCTIVE)
        def _on(_d: Adw.AlertDialog, response: str) -> None:
            if response != "ok":
                # Roll back the master switch.
                self.master_row.handler_block_by_func(self._on_master_toggled)
                self.master_row.set_active(False)
                self.master_row.handler_unblock_by_func(self._on_master_toggled)
                self._sync_sensitivity()
        dlg.connect("response", _on)
        dlg.present(self)

    def _save(self) -> None:
        """Snapshot current widget state → JSON, hand to helper."""
        snap = {
            "enabled": self.master_row.get_active(),
            "user": os.environ.get("USER", ""),
            "time_limits": {
                "enabled": self.tl_row.get_active(),
                "daily_minutes": int(self.daily.get_value()),
                "bedtime_start": self.policy["time_limits"]["bedtime_start"],
                "bedtime_end":   self.policy["time_limits"]["bedtime_end"],
            },
            "app_allowlist": {
                "enabled": self.al_row.get_active(),
                "apps":    self.policy["app_allowlist"].get("apps", []),
            },
            "web_filter": {
                "enabled":   self.wf_row.get_active(),
                "blocklist": self.policy["web_filter"].get("blocklist", []),
            },
            "safesearch": {"enabled": self.ss_row.get_active()},
        }
        # Marshal the JSON via stdin so we never shell-concat the payload.
        # The helper accepts `apply -` to read JSON from stdin.
        if not Path(HELPER).exists():
            self._flash("Parental helper not installed — install nyxus first.",
                        success=False)
            return
        try:
            proc = subprocess.run(
                ["pkexec", HELPER, "apply", "-"],
                input=json.dumps(snap),
                capture_output=True, text=True, check=False, timeout=30,
            )
        except subprocess.TimeoutExpired:
            self._flash("Helper timed out.", success=False)
            return
        if proc.returncode == 0:
            self.policy = snap
            self._flash("Saved.", success=True)
        else:
            self._flash(f"Save failed: {proc.stderr.strip()}", success=False)

    def _flash(self, msg: str, *, success: bool) -> None:
        self.banner.set_title(msg)
        self.banner.set_revealed(True)
        self.banner.add_css_class("success" if success else "error")
        GLib.timeout_add_seconds(3, lambda: (self.banner.set_revealed(False), False)[1])


def main() -> int:
    app = Adw.Application(application_id="com.nyxus.parental")
    def on_activate(_a: Adw.Application) -> None:
        ParentalWindow(_a).present()
    app.connect("activate", on_activate)
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
