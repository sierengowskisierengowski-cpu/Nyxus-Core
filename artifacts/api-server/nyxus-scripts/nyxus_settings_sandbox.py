#!/usr/bin/env python3
# ============================================================================
#  nyxus_settings_sandbox.py · NYXUS · App Sandbox UI    rev 2026-05-13 r1
#
#  Standalone GTK4 panel for Settings → Privacy → App Permissions.
#  Surfaces flatpak per-app overrides as toggleable rows. No shell-out
#  string concat anywhere — every flatpak override invocation is a flat
#  argv list, validated against a strict allowlist of permission keys.
#
#  HARD POLICY (P6.30):
#    · We only call `flatpak override --user`. No --system writes.
#    · Permission keys are restricted to the flatpak schema; any free-form
#      input is rejected.
#    · If flatpak is not installed, the panel renders a friendly "no apps"
#      placeholder instead of an error.
#
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
from __future__ import annotations

import json
import logging
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import gi  # type: ignore[import-not-found]

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

LOG_DIR = Path.home() / ".cache" / "nyxus"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "sandbox.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("nyxus_sandbox")

# Allowlisted permission categories the UI surfaces. Anything not in this
# set will be rejected before the flatpak invocation.
PERMISSION_TOGGLES: list[tuple[str, str, str]] = [
    # (label, flatpak namespace, key inside namespace)
    ("Network access",        "share",     "network"),
    ("IPC (X11/wayland passthrough)", "share", "ipc"),
    ("X11 fallback",          "socket",    "x11"),
    ("Pulseaudio / pipewire", "socket",    "pulseaudio"),
    ("System-wide D-Bus",     "socket",    "system-bus"),
    ("Read host filesystem",  "filesystem","host"),
    ("Read user home",        "filesystem","home"),
    ("Bluetooth",             "device",    "all"),
    ("USB devices",           "device",    "shm"),
]
ALLOWED_NS  = {ns for _, ns, _ in PERMISSION_TOGGLES}
ALLOWED_KEY = {f"{ns}/{key}" for _, ns, key in PERMISSION_TOGGLES}

APP_ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]{2,127}$")


# ── flatpak shellwrappers (argv only, never shell=True) ────────────────
def _flatpak(*args: str) -> tuple[bool, str]:
    if not shutil.which("flatpak"):
        return False, "flatpak not installed"
    cmd = ["flatpak", *args]
    log.info("invoke: %s", shlex.join(cmd))
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, check=False, timeout=20,
        )
    except subprocess.TimeoutExpired:
        return False, "flatpak timed out"
    if proc.returncode != 0:
        return False, proc.stderr.strip() or f"rc={proc.returncode}"
    return True, proc.stdout.rstrip()


@dataclass(frozen=True)
class FlatpakApp:
    app_id: str
    name: str
    version: str


def list_installed() -> list[FlatpakApp]:
    """Best-effort `flatpak list --app --columns=...` parser."""
    ok, out = _flatpak("list", "--app",
                       "--columns=application,name,version")
    if not ok:
        return []
    rows: list[FlatpakApp] = []
    for line in out.splitlines():
        parts = line.split("\t")
        if len(parts) < 1:
            continue
        app_id = parts[0].strip()
        if not APP_ID_RE.match(app_id):
            continue
        name = parts[1].strip() if len(parts) > 1 else app_id
        ver  = parts[2].strip() if len(parts) > 2 else ""
        rows.append(FlatpakApp(app_id=app_id, name=name, version=ver))
    return rows


def get_overrides(app_id: str) -> dict[str, set[str]]:
    """Parse `flatpak override --user --show <app>` into {ns: {keys}}."""
    if not APP_ID_RE.match(app_id):
        raise ValueError(f"invalid app_id: {app_id!r}")
    ok, out = _flatpak("override", "--user", "--show", app_id)
    overrides: dict[str, set[str]] = {ns: set() for ns in ALLOWED_NS}
    if not ok:
        return overrides
    # ini-shaped output:  [Context]\n shared=network;ipc;\n
    section = ""
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("[") and s.endswith("]"):
            section = s[1:-1].lower()
            continue
        if "=" not in s:
            continue
        key, _, val = s.partition("=")
        for v in (v.strip() for v in val.split(";") if v.strip()):
            mapped_ns = {
                "shared":      "share",
                "sockets":     "socket",
                "devices":     "device",
                "filesystems": "filesystem",
            }.get(key.strip())
            if mapped_ns and mapped_ns in overrides:
                overrides[mapped_ns].add(v.lstrip("!"))  # ! = override-deny
    return overrides


def set_permission(app_id: str, ns: str, key: str, granted: bool) -> tuple[bool, str]:
    if not APP_ID_RE.match(app_id):
        return False, f"invalid app id: {app_id}"
    if f"{ns}/{key}" not in ALLOWED_KEY:
        return False, f"permission not allowed in UI: {ns}/{key}"
    flag = {
        "share":      "--share",
        "socket":     "--socket",
        "device":     "--device",
        "filesystem": "--filesystem",
    }[ns]
    arg = key if granted else f"!{key}"  # ! denies in flatpak override
    return _flatpak("override", "--user", flag + "=" + arg, app_id)


# ── GTK panel ───────────────────────────────────────────────────────────
class SandboxPanel(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(16)
        self.set_margin_end(16)

        title = Gtk.Label(
            label="<b>App permissions</b>", use_markup=True, xalign=0,
        )
        self.append(title)

        sub = Gtk.Label(
            xalign=0, wrap=True,
            label=(
                "Permissions apply only to apps installed via flatpak. "
                "Changes take effect the next time the app starts."
            ),
        )
        sub.add_css_class("dim-label")
        self.append(sub)

        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.list = Gtk.ListBox()
        self.list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.list.add_css_class("boxed-list")
        scroller.set_child(self.list)
        self.append(scroller)

        self.banner = Gtk.Label(label="", xalign=0)
        self.banner.add_css_class("dim-label")
        self.append(self.banner)

        self.refresh()

    def refresh(self) -> None:
        # Drop existing rows.
        child = self.list.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self.list.remove(child)
            child = nxt

        apps = list_installed()
        if not apps:
            placeholder = Adw.ActionRow(
                title="No flatpak apps installed",
                subtitle="Install an app from NYXUS Store to manage its permissions here.",
            )
            self.list.append(placeholder)
            return

        for app in apps:
            self.list.append(self._build_expander(app))

    def _build_expander(self, app: FlatpakApp) -> Adw.ExpanderRow:
        row = Adw.ExpanderRow(
            title=app.name,
            subtitle=f"{app.app_id}  ·  {app.version}",
        )
        try:
            current = get_overrides(app.app_id)
        except Exception as exc:  # pragma: no cover
            log.warning("get_overrides %s: %s", app.app_id, exc)
            current = {ns: set() for ns in ALLOWED_NS}
        for label, ns, key in PERMISSION_TOGGLES:
            sw = Adw.SwitchRow(title=label, subtitle=f"{ns}/{key}")
            sw.set_active(key in current.get(ns, set()))
            sw.connect(
                "notify::active",
                lambda widget, _gp, app_id=app.app_id, ns=ns, key=key:
                    self._on_toggle(widget, app_id, ns, key),
            )
            row.add_row(sw)
        return row

    def _on_toggle(
        self, switch: Adw.SwitchRow, app_id: str, ns: str, key: str,
    ) -> None:
        granted = switch.get_active()
        ok, msg = set_permission(app_id, ns, key, granted)
        if ok:
            self.banner.set_label(
                f"Updated {app_id}: {ns}/{key} → {'granted' if granted else 'denied'}.")
        else:
            self.banner.set_label(f"Update failed: {msg}")
            # roll back the switch.
            switch.handler_block_by_func(self._on_toggle)
            switch.set_active(not granted)
            switch.handler_unblock_by_func(self._on_toggle)
        GLib.timeout_add_seconds(
            3, lambda: (self.banner.set_label(""), False)[1])


def main() -> int:
    app = Adw.Application(application_id="com.nyxus.sandbox")
    def on_activate(_a: Adw.Application) -> None:
        win = Adw.ApplicationWindow(application=_a,
                                    title="NYXUS · App Permissions")
        win.set_default_size(760, 620)
        win.set_content(SandboxPanel())
        win.present()
    app.connect("activate", on_activate)
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
