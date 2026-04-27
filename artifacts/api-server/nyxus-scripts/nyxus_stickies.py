#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Stickies — Native GTK4 Sticky Notes Widget                   ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
# Install:  pacman -S python-gobject gtk4
# Run:      python3 ~/.nyxus/nyxus_stickies.py

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Pango
import json, uuid, os
from datetime import datetime

DATA_FILE = os.path.expanduser("~/.nyxus/stickies.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

PALETTE = [
    ("#ff00ff", "1,0,1"),
    ("#cc00ff", "0.8,0,1"),
    ("#0088ff", "0,0.53,1"),
    ("#39ff14", "0.22,1,0.08"),
    ("#ffff00", "1,1,0"),
    ("#ff5500", "1,0.33,0"),
]

CSS = b"""
* { font-family: 'JetBrains Mono', 'Monospace', monospace; }
window { background-color: #030206; color: #e8e0f5; }

.header {
    background-color: #07030f;
    border-bottom: 1px solid rgba(204,0,255,0.3);
    padding: 6px 12px;
    min-height: 42px;
}
.app-title { color: #ff00ff; font-size: 13px; font-weight: bold; letter-spacing: 2px; }
.note-count { color: #7060a0; font-size: 11px; margin-left: 8px; }

.btn-new {
    background-color: transparent;
    color: #ff00ff;
    border: 1px solid #ff00ff;
    border-radius: 2px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}
.btn-new:hover { background-color: rgba(255,0,255,0.12); }

.btn-purge {
    background-color: transparent;
    color: #ff5500;
    border: 1px solid rgba(255,85,0,0.4);
    border-radius: 2px;
    padding: 3px 8px;
    font-size: 11px;
}
.btn-purge:hover { background-color: rgba(255,85,0,0.12); }

.board { background-color: #030206; }

.note-card {
    background-color: #07030f;
    border: 1px solid #ff00ff;
    border-radius: 3px;
    margin: 6px;
}
.note-title {
    background-color: transparent;
    color: #e8e0f5;
    font-size: 12px;
    font-weight: bold;
    border: none;
    padding: 0;
    min-width: 0;
    box-shadow: none;
}
.note-title text { background-color: transparent; }
.note-body {
    background-color: transparent;
    color: #c0b0e0;
    font-size: 11px;
    border: none;
}
.note-body text { background-color: transparent; }
.btn-icon {
    background-color: transparent;
    border: none;
    color: #7060a0;
    padding: 1px 4px;
    font-size: 12px;
    min-width: 0;
    min-height: 0;
}
.btn-icon:hover { color: #e8e0f5; }
.btn-del { color: #ff5500; }
.btn-del:hover { color: #ff8844; }
.btn-pin-on { color: #ffff00; }

.swatch {
    min-width: 14px;
    min-height: 14px;
    border-radius: 50%;
    border: 1px solid rgba(255,255,255,0.15);
    padding: 0;
    margin: 1px;
}
.swatch:hover { border: 1px solid rgba(255,255,255,0.7); }

.empty-msg { color: #2a1a4a; font-size: 13px; letter-spacing: 3px; }
.empty-btn {
    background-color: transparent;
    color: #ff00ff;
    border: 2px solid #ff00ff;
    border-radius: 2px;
    padding: 10px 24px;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1px;
}
.empty-btn:hover { background-color: rgba(255,0,255,0.1); }
"""


class Note:
    def __init__(self, data=None):
        if data:
            self.id      = data.get("id", str(uuid.uuid4())[:8])
            self.title   = data.get("title", "")
            self.content = data.get("content", "")
            self.color   = data.get("color", "#ff00ff")
            self.pinned  = data.get("pinned", False)
        else:
            self.id      = str(uuid.uuid4())[:8]
            self.title   = ""
            self.content = ""
            self.color   = "#ff00ff"
            self.pinned  = False

    def to_dict(self):
        return {"id": self.id, "title": self.title, "content": self.content,
                "color": self.color, "pinned": self.pinned}


class NyxusStickies(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.stickies")
        self.notes = []
        self._save_tid = None
        self._load()

    def do_activate(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self, title="NYXUS Stickies")
        self.win.set_default_size(480, 560)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)
        root.append(self._build_header())

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.board = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.board.add_css_class("board")
        scroll.set_child(self.board)
        root.append(scroll)

        self._render()
        self.win.present()

    def _build_header(self):
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hdr.add_css_class("header")

        t = Gtk.Label(label="NYXUS_STICKIES")
        t.add_css_class("app-title")
        hdr.append(t)

        self._count_lbl = Gtk.Label(label="")
        self._count_lbl.add_css_class("note-count")
        hdr.append(self._count_lbl)

        sp = Gtk.Box(); sp.set_hexpand(True)
        hdr.append(sp)

        bn = Gtk.Button(label="+ NEW")
        bn.add_css_class("btn-new")
        bn.connect("clicked", lambda *_: self._new_note())
        hdr.append(bn)

        bp = Gtk.Button(label="PURGE")
        bp.add_css_class("btn-purge")
        bp.connect("clicked", lambda *_: self._purge())
        hdr.append(bp)
        return hdr

    def _render(self):
        c = self.board.get_first_child()
        while c:
            n = c.get_next_sibling(); self.board.remove(c); c = n

        n = len(self.notes)
        self._count_lbl.set_text(f"{n} {'NOTE' if n==1 else 'NOTES'}")

        if not self.notes:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
            box.set_vexpand(True); box.set_valign(Gtk.Align.CENTER); box.set_halign(Gtk.Align.CENTER)
            msg = Gtk.Label(label="NO NOTES PINNED TO MEMORY")
            msg.add_css_class("empty-msg")
            box.append(msg)
            btn = Gtk.Button(label="INITIALIZE NOTE")
            btn.add_css_class("empty-btn")
            btn.connect("clicked", lambda *_: self._new_note())
            box.append(btn)
            self.board.append(box)
            return

        flow = Gtk.FlowBox()
        flow.set_max_children_per_line(2)
        flow.set_min_children_per_line(1)
        flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.board.append(flow)

        sorted_notes = sorted(self.notes, key=lambda x: (not x.pinned, 0))
        for note in sorted_notes:
            flow.append(self._make_card(note))

    def _make_card(self, note):
        display = Gdk.Display.get_default()
        r, g, b = self._hex_rgb(note.color)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        card.add_css_class("note-card")
        card.set_size_request(200, -1)
        card.set_margin_top(6); card.set_margin_bottom(6)
        card.set_margin_start(6); card.set_margin_end(6)

        css_cls = f"nc-{note.id}"
        p = Gtk.CssProvider()
        glow = 14 if note.pinned else 8
        alpha = 0.7 if note.pinned else 0.4
        p.load_from_data(
            f".{css_cls}{{border-color:{note.color};box-shadow:0 0 {glow}px rgba({r},{g},{b},{alpha});}}".encode())
        Gtk.StyleContext.add_provider_for_display(display, p, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        card.add_css_class(css_cls)

        # Header row
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        row.set_margin_top(6); row.set_margin_start(8); row.set_margin_end(4)

        title = Gtk.Entry()
        title.add_css_class("note-title")
        title.set_text(note.title)
        title.set_placeholder_text("TITLE...")
        title.set_hexpand(True); title.set_has_frame(False)
        title.connect("changed", lambda w, n=note: self._title_changed(w, n))
        row.append(title)

        pin_lbl = "📌" if note.pinned else "○"
        bp = Gtk.Button(label=pin_lbl)
        bp.add_css_class("btn-icon")
        if note.pinned: bp.add_css_class("btn-pin-on")
        bp.connect("clicked", lambda *_, n=note: self._toggle_pin(n))
        row.append(bp)

        bd = Gtk.Button(label="✕")
        bd.add_css_class("btn-icon"); bd.add_css_class("btn-del")
        bd.connect("clicked", lambda *_, n=note: self._delete(n))
        row.append(bd)
        card.append(row)

        sep = Gtk.Separator()
        sep.set_margin_start(8); sep.set_margin_end(8)
        card.append(sep)

        tv = Gtk.TextView()
        tv.add_css_class("note-body")
        tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        tv.set_left_margin(8); tv.set_right_margin(8)
        tv.set_top_margin(4); tv.set_bottom_margin(4)
        tv.set_size_request(-1, 90)
        tv.get_buffer().set_text(note.content)
        tv.get_buffer().connect("changed", lambda b, n=note: self._body_changed(b, n))
        card.append(tv)

        # Color swatches
        sw_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        sw_row.set_margin_start(8); sw_row.set_margin_bottom(8)
        for hex_col, _ in PALETTE:
            sw = Gtk.Button()
            sw.add_css_class("swatch")
            sw.set_size_request(14, 14)
            sp2 = Gtk.CssProvider()
            sc = f"swatch-{hex_col[1:]}"
            sp2.load_from_data(f".{sc}{{background-color:{hex_col};}}".encode())
            Gtk.StyleContext.add_provider_for_display(display, sp2, Gtk.STYLE_PROVIDER_PRIORITY_USER)
            sw.add_css_class(sc)
            sw.connect("clicked", lambda *_, h=hex_col, n=note: self._recolor(n, h))
            sw_row.append(sw)
        card.append(sw_row)

        wrapper = Gtk.Box()
        wrapper.append(card)
        return wrapper

    def _title_changed(self, entry, note):
        note.title = entry.get_text(); self._schedule_save()

    def _body_changed(self, buf, note):
        s, e = buf.get_bounds()
        note.content = buf.get_text(s, e, False); self._schedule_save()

    def _toggle_pin(self, note):
        note.pinned = not note.pinned; self._save(); self._render()

    def _delete(self, note):
        self.notes = [n for n in self.notes if n.id != note.id]
        self._save(); self._render()

    def _recolor(self, note, color):
        note.color = color; self._save(); self._render()

    def _new_note(self):
        self.notes.insert(0, Note()); self._save(); self._render()

    def _purge(self):
        self.notes = []; self._save(); self._render()

    def _schedule_save(self):
        if self._save_tid:
            GLib.source_remove(self._save_tid)
        self._save_tid = GLib.timeout_add(500, self._do_save)

    def _do_save(self):
        self._save(); self._save_tid = None; return GLib.SOURCE_REMOVE

    def _save(self):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump({"notes": [n.to_dict() for n in self.notes]}, f, indent=2)
        except Exception as e:
            print(f"[stickies] save error: {e}")

    def _load(self):
        try:
            with open(DATA_FILE) as f:
                self.notes = [Note(d) for d in json.load(f).get("notes", [])]
        except Exception:
            self.notes = []

    def _hex_rgb(self, h):
        h = h.lstrip('#')
        return int(h[0:2],16), int(h[2:4],16), int(h[4:6],16)


if __name__ == "__main__":
    NyxusStickies().run(None)
