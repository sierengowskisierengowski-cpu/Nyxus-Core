#!/usr/bin/env python3
"""
NYXUS Hotkeys Settings page  (GTK4 / libadwaita with GTK3 fallback)

Embeddable in the main Settings shell as a child window OR runnable
standalone.  All long-running daemon RPC + TOML writes happen on a
background thread so the UI never blocks.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path

try:
    import tomllib  # py311+
except ImportError:                       # pragma: no cover
    import tomli as tomllib  # type: ignore

HOME    = Path(os.path.expanduser("~"))
CFG     = HOME / ".config" / "nyxus" / "hotkeys.toml"
RUN     = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")) / "nyxus-hotkey"
SOCK    = RUN / "cmd.sock"

# ─── try GTK4 + Adw, fall back to GTK3 ──────────────────────────────────
GTK4 = True
try:
    import gi
    gi.require_version("Gtk", "4.0")
    gi.require_version("Adw", "1")
    from gi.repository import Gtk, Adw, GLib, Gio
    Adw.init()
except (ImportError, ValueError):
    try:
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk, GLib, Gio  # type: ignore
        Adw = None  # type: ignore
        GTK4 = False
    except (ImportError, ValueError) as e:
        print("GTK not available:", e, file=sys.stderr); sys.exit(1)


# ─── small async helpers ────────────────────────────────────────────────
def run_async(target, *args, on_done=None) -> None:
    def _w():
        try:
            res = target(*args)
        except Exception as e:                # noqa: BLE001
            res = ("error", str(e))
        if on_done:
            GLib.idle_add(on_done, res)
    threading.Thread(target=_w, daemon=True).start()


def rpc(op: str, **kw) -> dict:
    if not SOCK.exists():
        return {"ok": False, "error": "daemon not running"}
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect(str(SOCK))
        s.send((json.dumps({"op": op, **kw}) + "\n").encode())
        buf = b""
        while True:
            chunk = s.recv(8192)
            if not chunk: break
            buf += chunk
            if buf.endswith(b"\n"): break
        s.close()
        return json.loads(buf.decode("utf-8", errors="replace").splitlines()[0])
    except (OSError, json.JSONDecodeError) as e:
        return {"ok": False, "error": str(e)}


def load_cfg() -> dict:
    if not CFG.exists():
        return {"meta": {"version": 1, "active_preset": "custom"}, "options": {}}
    with CFG.open("rb") as f:
        return tomllib.load(f)


def save_cfg(data: dict) -> None:
    """Write TOML round-trip via minimal serializer."""
    out: list[str] = []
    if "meta" in data:
        out.append("[meta]")
        for k, v in data["meta"].items():
            out.append(f"{k} = {json.dumps(v)}")
        out.append("")
    if "options" in data:
        out.append("[options]")
        for k, v in data["options"].items():
            out.append(f"{k} = {json.dumps(v)}")
        out.append("")
    for b in data.get("bind", []) or []:
        out.append("[[bind]]")
        for k in ("mods", "key", "action", "desc", "category"):
            if k in b: out.append(f"{k} = {json.dumps(b[k])}")
        out.append("")
    for c in data.get("chord", []) or []:
        out.append("[[chord]]")
        for k in ("trigger", "desc", "category"):
            if k in c: out.append(f"{k} = {json.dumps(c[k])}")
        if "steps" in c:
            out.append("steps = [")
            for s in c["steps"]:
                out.append("  { " + ", ".join(f"{k} = {json.dumps(v)}" for k, v in s.items()) + " },")
            out.append("]")
        out.append("")
    for m in data.get("mod_tap", []) or []:
        out.append("[[mod_tap]]")
        for k in ("mod", "action", "desc"):
            if k in m: out.append(f"{k} = {json.dumps(m[k])}")
        out.append("")
    for g in data.get("gesture", []) or []:
        out.append("[[gesture]]")
        for k in ("type", "fingers", "direction", "action", "desc"):
            if k in g: out.append(f"{k} = {json.dumps(g[k])}")
        out.append("")
    for ao in data.get("app_override", []) or []:
        out.append("[[app_override]]")
        if "match" in ao: out.append(f"match = {json.dumps(ao['match'])}")
        for b in ao.get("bind", []) or []:
            out.append("[[app_override.bind]]")
            for k in ("mods", "key", "action", "desc", "category"):
                if k in b: out.append(f"{k} = {json.dumps(b[k])}")
        out.append("")
    CFG.parent.mkdir(parents=True, exist_ok=True)
    tmp = CFG.with_suffix(".toml.tmp")
    tmp.write_text("\n".join(out) + "\n")
    tmp.replace(CFG)


# ─── UI ─────────────────────────────────────────────────────────────────
def build_root() -> "Gtk.Widget":
    if GTK4:
        page = Adw.PreferencesPage()
        page.set_title("Hotkeys")

        # ── group: presets ───────────────────────────────────────────
        gp = Adw.PreferencesGroup(title="Preset")
        page.add(gp)
        preset_row = Adw.ComboRow()
        preset_row.set_title("Active preset")
        preset_row.set_subtitle("Switch keymap profile")
        model = Gtk.StringList.new(["macos", "windows", "vscode", "vim", "custom"])
        preset_row.set_model(model)
        try:
            cur = load_cfg().get("meta", {}).get("active_preset", "macos")
            preset_row.set_selected(["macos","windows","vscode","vim","custom"].index(cur))
        except ValueError:
            preset_row.set_selected(0)

        def _on_preset(_row, _spec):
            idx = preset_row.get_selected()
            name = ["macos","windows","vscode","vim","custom"][idx]
            run_async(lambda: (save_cfg({**load_cfg(), "meta": {**load_cfg().get("meta",{}), "active_preset": name}}), rpc("reload")))
        preset_row.connect("notify::selected", _on_preset)
        gp.add(preset_row)

        # ── group: options ───────────────────────────────────────────
        og = Adw.PreferencesGroup(title="Options")
        page.add(og)
        opts = load_cfg().get("options", {})

        def _add_int(title, key, lo, hi, step, default):
            row = Adw.SpinRow.new_with_range(lo, hi, step)
            row.set_title(title)
            row.set_value(int(opts.get(key, default)))
            def _save(_r, _p):
                d = load_cfg(); d.setdefault("options", {})[key] = int(row.get_value())
                run_async(lambda: (save_cfg(d), rpc("reload")))
            row.connect("notify::value", _save)
            og.add(row)

        _add_int("Chord timeout (ms)",       "chord_timeout_ms",     200, 5000, 50, 800)
        _add_int("Modifier-tap threshold (ms)","tap_threshold_ms",   100, 1000, 10, 220)
        _add_int("Swipe minimum px",         "gesture_swipe_min_px",  20,  500, 10,  80)

        for title, key, default in (
            ("Group cheat-sheet by category", "cheatsheet_grouped", True),
            ("Warn on conflicts",             "warn_on_conflict",   True),
            ("Hot reload on save",            "hot_reload",         True)):
            sw = Adw.SwitchRow()
            sw.set_title(title)
            sw.set_active(bool(opts.get(key, default)))
            def _save(switch, _p, k=key):
                d = load_cfg(); d.setdefault("options", {})[k] = bool(switch.get_active())
                run_async(lambda: (save_cfg(d), rpc("reload")))
            sw.connect("notify::active", _save)
            og.add(sw)

        # ── group: binds list ────────────────────────────────────────
        bg = Adw.PreferencesGroup(title="Bindings")
        page.add(bg)
        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        listbox.add_css_class("boxed-list")

        def _refresh_listbox():
            child = listbox.get_first_child()
            while child:
                nxt = child.get_next_sibling()
                listbox.remove(child)
                child = nxt
            data = load_cfg()
            for i, b in enumerate(data.get("bind", []) or []):
                row = Adw.ActionRow()
                combo = (str(b.get("mods","")) + "+" + str(b.get("key",""))).strip("+")
                row.set_title(combo or "(none)")
                row.set_subtitle(str(b.get("desc","")) + "   →   " + str(b.get("action",""))[:60])
                btn = Gtk.Button.new_from_icon_name("user-trash-symbolic")
                btn.add_css_class("flat")
                def _del(_btn, idx=i):
                    d = load_cfg(); lst = d.get("bind", []) or []
                    if 0 <= idx < len(lst):
                        del lst[idx]; d["bind"] = lst
                        run_async(lambda: (save_cfg(d), rpc("reload")), on_done=lambda _r: _refresh_listbox())
                btn.connect("clicked", _del)
                row.add_suffix(btn)
                listbox.append(row)
        _refresh_listbox()

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True); scroll.set_min_content_height(280)
        scroll.set_child(listbox)
        bg.add(scroll)

        # add bind button
        ag = Adw.PreferencesGroup()
        page.add(ag)
        add_btn = Gtk.Button(label="＋  Add bind")
        add_btn.add_css_class("suggested-action")
        def _add_dialog(_b):
            dlg = Adw.MessageDialog.new(page.get_root(), "New bind", None)
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            e_combo = Gtk.Entry(placeholder_text="SUPER+k")
            e_action = Gtk.Entry(placeholder_text="action shell command")
            e_desc = Gtk.Entry(placeholder_text="description")
            e_cat = Gtk.Entry(placeholder_text="category (Apps, Window, …)")
            for w in (e_combo, e_action, e_desc, e_cat): box.append(w)
            rec_btn = Gtk.Button(label="🎙  Record combo")
            def _rec(_b):
                def _do():
                    try:
                        out = subprocess.check_output(["/usr/local/bin/nyxus-hotkey","record"], timeout=20).decode().strip()
                    except (subprocess.SubprocessError, OSError) as ex:
                        return ("err", str(ex))
                    return ("ok", out)
                def _done(res):
                    if res[0] == "ok": e_combo.set_text(res[1])
                run_async(_do, on_done=_done)
            rec_btn.connect("clicked", _rec)
            box.append(rec_btn)
            dlg.set_extra_child(box)
            dlg.add_response("cancel", "Cancel")
            dlg.add_response("ok", "Add")
            dlg.set_default_response("ok")
            dlg.set_response_appearance("ok", Adw.ResponseAppearance.SUGGESTED)
            def _resp(d, resp):
                if resp == "ok":
                    combo = e_combo.get_text().strip()
                    if combo:
                        mods, _, key = combo.rpartition("+")
                        d2 = load_cfg(); d2.setdefault("bind", []).append({
                            "mods": mods, "key": key,
                            "action": e_action.get_text(),
                            "desc": e_desc.get_text(),
                            "category": e_cat.get_text() or "Custom",
                        })
                        run_async(lambda: (save_cfg(d2), rpc("reload")),
                                  on_done=lambda _r: _refresh_listbox())
                d.close()
            dlg.connect("response", _resp)
            dlg.present()
        add_btn.connect("clicked", _add_dialog)
        ag.add(add_btn)

        # ── group: conflicts ─────────────────────────────────────────
        cg = Adw.PreferencesGroup(title="Conflicts")
        page.add(cg)
        conflict_label = Gtk.Label(label="Loading…", xalign=0)
        cg.add(conflict_label)
        def _load_conflicts():
            r = rpc("conflicts")
            cs = r.get("conflicts", []) if r.get("ok") else []
            if not cs:
                GLib.idle_add(conflict_label.set_text, "✓  No conflicts")
            else:
                lines = [f"⚠  {c['combo']}  ({c['count']} bindings)" for c in cs]
                GLib.idle_add(conflict_label.set_text, "\n".join(lines))
        run_async(_load_conflicts)

        return page

    # ── GTK3 fallback ────────────────────────────────────────────────
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, border_width=12)  # type: ignore
    box.add(Gtk.Label(label="<b>NYXUS Hotkeys</b>", use_markup=True, xalign=0))
    box.add(Gtk.Label(label="GTK4/libadwaita not present — open with the GTK4 build for the full editor.", xalign=0, wrap=True))
    btn = Gtk.Button.new_with_label("Open ~/.config/nyxus/hotkeys.toml")
    def _open(_b):
        subprocess.Popen(["xdg-open", str(CFG)])
    btn.connect("clicked", _open)
    box.add(btn)
    return box


def main() -> int:
    win = Gtk.Window(title="NYXUS Hotkeys")
    win.set_default_size(720, 720)
    win.set_child(build_root()) if GTK4 else win.add(build_root())
    win.connect("close-request" if GTK4 else "destroy", lambda *_: (Gtk.main_quit() if not GTK4 else None) or False)
    if GTK4:
        win.present()
        GLib.MainLoop().run()
    else:
        win.show_all()  # type: ignore
        Gtk.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
