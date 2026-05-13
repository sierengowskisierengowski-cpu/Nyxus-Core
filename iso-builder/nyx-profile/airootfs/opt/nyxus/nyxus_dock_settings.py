#!/usr/bin/env python3
"""
NYXUS · Dock Settings
=====================
GTK4/libadwaita settings page that edits ~/.config/nyxus/dock.toml and asks
nyxus-dockd to reload. Falls back to GTK3 if libadwaita unavailable.

Can be launched standalone (`python3 nyxus_dock_settings.py`) or focused on
a specific entry (`--focus <id>`) from the right-click context menu.

Lives at: /opt/nyxus/nyxus_dock_settings.py
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore

HOME = Path(os.path.expanduser("~"))
CONFIG_PATH = HOME / ".config" / "nyxus" / "dock.toml"
SOCK = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) \
       / "nyxus-dock" / "cmd.sock"


def call_daemon(op: str, **kw: object) -> dict:
    payload = {"op": op, **kw}
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(3.0)
            s.connect(str(SOCK))
            s.sendall(json.dumps(payload).encode())
            data = s.recv(65536)
        return json.loads(data.decode().strip() or "{}")
    except OSError:
        return {"ok": False}


def load_cfg() -> dict:
    try:
        with CONFIG_PATH.open("rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError):
        return {}


def save_cfg(cfg: dict) -> None:
    """Persist config to disk, then ask the daemon to reload — but do the
    socket call on a background thread so the GTK main loop never blocks
    on a missing or hung daemon."""
    import threading
    from nyxus_dockd import _render_toml  # type: ignore
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(_render_toml(cfg))
    threading.Thread(
        target=lambda: call_daemon("reload"),
        daemon=True, name="dock-reload",
    ).start()


# ── GTK UI ─────────────────────────────────────────────────────────────
def build_ui(focus_id: str | None = None) -> int:
    sys.path.insert(0, "/opt/nyxus")
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        gi.require_version("Adw", "1")
        from gi.repository import Gtk, Adw, GLib
    except (ImportError, ValueError):
        return _build_ui_gtk3(focus_id)

    class DockSettingsWindow(Adw.ApplicationWindow):
        def __init__(self, app: Adw.Application):
            super().__init__(application=app, title="NYXUS · Dock", default_width=720, default_height=580)
            self.cfg = load_cfg() or {}
            self.cfg.setdefault("general", {})
            self.cfg.setdefault("pinned", [])

            tb = Adw.ToolbarView()
            hb = Adw.HeaderBar()
            tb.add_top_bar(hb)

            content = Adw.PreferencesPage()
            tb.set_content(content)
            self.set_content(tb)

            # ── Behavior group ──
            grp_behave = Adw.PreferencesGroup(title="Behavior")
            content.add(grp_behave)
            grp_behave.add(self._switch_row("Magnification", "magnification_enabled", True))
            grp_behave.add(self._scale_row("Magnification level", "magnification_max", 1.0, 2.5, 0.05, 1.65))
            grp_behave.add(self._scale_row("Falloff (neighbours)", "magnification_falloff", 0, 4, 1, 2))
            grp_behave.add(self._scale_row("Icon size", "size", 32, 96, 4, 56))
            grp_behave.add(self._switch_row("Auto-hide", "auto_hide", False))
            grp_behave.add(self._switch_row("Show running indicator", "show_running_indicator", True))
            grp_behave.add(self._switch_row("Show notification badges", "show_badges", True))
            grp_behave.add(self._switch_row("Show recently used apps", "show_recents", True))
            grp_behave.add(self._switch_row("Show Trash", "show_trash", True))
            grp_behave.add(self._switch_row("Live icons (Calendar/Clock/Weather)", "live_icons", True))
            grp_behave.add(self._switch_row("Section dividers", "section_dividers", True))

            # ── Position group ──
            grp_pos = Adw.PreferencesGroup(title="Position")
            content.add(grp_pos)
            row = Adw.ComboRow(title="Edge")
            model = Gtk.StringList.new(["bottom", "left", "right"])
            row.set_model(model)
            cur = self.cfg["general"].get("position", "bottom")
            row.set_selected({"bottom": 0, "left": 1, "right": 2}.get(cur, 0))
            row.connect("notify::selected", lambda r, _: self._set_general(
                "position", ["bottom", "left", "right"][r.get_selected()]))
            grp_pos.add(row)
            grp_pos.add(self._switch_row("Follow cursor monitor", "follow_cursor_monitor", False))

            # ── Pinned apps group ──
            grp_pinned = Adw.PreferencesGroup(title="Pinned apps", description="Drag to reorder · click to remove")
            content.add(grp_pinned)
            self.pinned_list = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE,
                                           css_classes=["boxed-list"])
            grp_pinned.add(self.pinned_list)
            self._refresh_pinned()

            add_btn = Gtk.Button(label="+ Add app", halign=Gtk.Align.START, css_classes=["pill"])
            add_btn.connect("clicked", self._on_add_pinned)
            grp_pinned.add(add_btn)

            if focus_id:
                self.set_title(f"NYXUS · Dock · {focus_id}")

        def _switch_row(self, title: str, key: str, default: bool) -> Adw.ActionRow:
            row = Adw.ActionRow(title=title)
            sw = Gtk.Switch(active=bool(self.cfg["general"].get(key, default)),
                            valign=Gtk.Align.CENTER)
            sw.connect("notify::active", lambda s, _: self._set_general(key, s.get_active()))
            row.add_suffix(sw)
            row.set_activatable_widget(sw)
            return row

        def _scale_row(self, title: str, key: str, lo: float, hi: float, step: float, default: float) -> Adw.ActionRow:
            row = Adw.ActionRow(title=title)
            adj = Gtk.Adjustment(value=float(self.cfg["general"].get(key, default)),
                                 lower=lo, upper=hi, step_increment=step, page_increment=step * 4)
            scale = Gtk.Scale(adjustment=adj, draw_value=True, hexpand=True, width_request=240)
            scale.set_digits(2 if step < 1 else 0)
            scale.connect("value-changed", lambda s: self._set_general(
                key, s.get_value() if step < 1 else int(s.get_value())))
            row.add_suffix(scale)
            return row

        def _set_general(self, k: str, v: object) -> None:
            self.cfg["general"][k] = v
            save_cfg(self.cfg)

        def _refresh_pinned(self) -> None:
            child = self.pinned_list.get_first_child()
            while child:
                self.pinned_list.remove(child)
                child = self.pinned_list.get_first_child()
            for p in self.cfg.get("pinned", []):
                row = Adw.ActionRow(title=p.get("label") or p.get("id"),
                                    subtitle=p.get("exec", ""))
                btn = Gtk.Button(icon_name="user-trash-symbolic", valign=Gtk.Align.CENTER,
                                 css_classes=["flat"])
                btn.connect("clicked", lambda _b, pid=p.get("id"): self._remove_pinned(pid))
                row.add_suffix(btn)
                self.pinned_list.append(row)

        def _remove_pinned(self, pid: str) -> None:
            self.cfg["pinned"] = [p for p in self.cfg.get("pinned", []) if p.get("id") != pid]
            save_cfg(self.cfg)
            self._refresh_pinned()

        def _on_add_pinned(self, _btn: Gtk.Button) -> None:
            dlg = Gtk.Window(transient_for=self, modal=True, title="Add app", default_width=420)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, margin_top=12,
                          margin_bottom=12, margin_start=12, margin_end=12)
            id_entry = Gtk.Entry(placeholder_text="App id (matches window class)")
            exec_entry = Gtk.Entry(placeholder_text="Command to launch")
            icon_entry = Gtk.Entry(placeholder_text="Icon name (XDG)")
            label_entry = Gtk.Entry(placeholder_text="Display label (optional)")
            for w in (id_entry, exec_entry, icon_entry, label_entry):
                box.append(w)
            ok = Gtk.Button(label="Pin", css_classes=["suggested-action"])
            box.append(ok)
            dlg.set_child(box)

            def add(_b):
                pid = id_entry.get_text().strip()
                if not pid:
                    dlg.close(); return
                self.cfg.setdefault("pinned", []).append({
                    "id": pid,
                    "exec": exec_entry.get_text().strip() or pid,
                    "icon": icon_entry.get_text().strip() or pid,
                    "label": label_entry.get_text().strip() or pid,
                })
                save_cfg(self.cfg)
                self._refresh_pinned()
                dlg.close()

            ok.connect("clicked", add)
            dlg.present()

    class App(Adw.Application):
        def __init__(self):
            super().__init__(application_id="io.nyxus.DockSettings")

        def do_activate(self):
            win = DockSettingsWindow(self)
            win.present()

    return App().run(None)


def _build_ui_gtk3(focus_id: str | None) -> int:
    """GTK3 fallback for systems without libadwaita."""
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk
    except (ImportError, ValueError):
        sys.stderr.write("GTK not available\n")
        return 2

    cfg = load_cfg() or {}
    cfg.setdefault("general", {})

    win = Gtk.Window(title="NYXUS · Dock")
    win.set_default_size(560, 480)
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=12)
    win.add(box)

    def add_switch(title: str, key: str, default: bool):
        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        h.pack_start(Gtk.Label(label=title, xalign=0), True, True, 0)
        sw = Gtk.Switch()
        sw.set_active(bool(cfg["general"].get(key, default)))
        sw.connect("notify::active", lambda s, _: (cfg["general"].__setitem__(key, s.get_active()), save_cfg(cfg)))
        h.pack_start(sw, False, False, 0)
        box.pack_start(h, False, False, 0)

    add_switch("Magnification", "magnification_enabled", True)
    add_switch("Auto-hide", "auto_hide", False)
    add_switch("Show running indicator", "show_running_indicator", True)
    add_switch("Show notification badges", "show_badges", True)
    add_switch("Show recently used apps", "show_recents", True)
    add_switch("Show Trash", "show_trash", True)
    add_switch("Live icons", "live_icons", True)

    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
    return 0


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--focus", help="Highlight an entry by id")
    args = p.parse_args()
    return build_ui(args.focus)


if __name__ == "__main__":
    sys.exit(main())
