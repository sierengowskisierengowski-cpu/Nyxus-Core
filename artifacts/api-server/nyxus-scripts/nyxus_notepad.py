#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Notepad — Native GTK4 Markdown Notepad                        ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
# Install:  pacman -S python-gobject gtk4
# Run:      python3 ~/.nyxus/nyxus_notepad.py

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Pango
import json, uuid, os
from datetime import datetime

DATA_FILE  = os.path.expanduser("~/.nyxus/notepad.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

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
.note-count { color: #7060a0; font-size: 11px; margin-left: 6px; }

.btn-toolbar {
    background-color: transparent;
    color: #cc00ff;
    border: 1px solid rgba(204,0,255,0.35);
    border-radius: 2px;
    padding: 3px 10px;
    font-size: 11px;
    font-weight: bold;
}
.btn-toolbar:hover { background-color: rgba(204,0,255,0.1); }
.btn-danger {
    background-color: transparent;
    color: #ff5500;
    border: 1px solid rgba(255,85,0,0.35);
    border-radius: 2px;
    padding: 3px 8px;
    font-size: 11px;
}
.btn-danger:hover { background-color: rgba(255,85,0,0.1); }
.btn-clip {
    background-color: transparent;
    color: #0088ff;
    border: 1px solid rgba(0,136,255,0.35);
    border-radius: 2px;
    padding: 3px 8px;
    font-size: 11px;
}
.btn-clip:hover { background-color: rgba(0,136,255,0.1); }

.sidebar {
    background-color: #07030f;
    border-right: 1px solid rgba(204,0,255,0.2);
    min-width: 180px;
}
.note-row {
    background-color: transparent;
    padding: 8px 10px;
    border-bottom: 1px solid rgba(204,0,255,0.1);
}
.note-row:hover { background-color: rgba(204,0,255,0.07); }
.note-row-selected { background-color: rgba(204,0,255,0.14); border-left: 3px solid #cc00ff; }
.note-row-name { color: #e8e0f5; font-size: 12px; font-weight: bold; }
.note-row-date { color: #7060a0; font-size: 10px; }

.search-entry {
    background-color: transparent;
    color: #e8e0f5;
    border: none;
    border-bottom: 1px solid rgba(204,0,255,0.25);
    border-radius: 0;
    padding: 6px 10px;
    font-size: 11px;
    box-shadow: none;
}
.search-entry text { background-color: transparent; }

.editor-title {
    background-color: transparent;
    color: #ff00ff;
    font-size: 15px;
    font-weight: bold;
    border: none;
    border-bottom: 1px solid rgba(255,0,255,0.2);
    border-radius: 0;
    padding: 10px 16px;
    box-shadow: none;
}
.editor-title text { background-color: transparent; }

.editor-body {
    background-color: transparent;
    color: #e8e0f5;
    font-size: 13px;
    border: none;
}
.editor-body text { background-color: transparent; }

.statusbar {
    background-color: #07030f;
    border-top: 1px solid rgba(204,0,255,0.15);
    padding: 3px 12px;
}
.status-text { color: #7060a0; font-size: 10px; }
.status-saved { color: #39ff14; }

.empty-lbl { color: #2a1a4a; font-size: 12px; letter-spacing: 2px; }
"""


class NoteItem:
    def __init__(self, data=None):
        if data:
            self.id      = data.get("id", str(uuid.uuid4())[:8])
            self.title   = data.get("title", "Untitled")
            self.content = data.get("content", "")
            self.updated = data.get("updated", datetime.now().isoformat())
        else:
            self.id      = str(uuid.uuid4())[:8]
            self.title   = "New Note"
            self.content = ""
            self.updated = datetime.now().isoformat()

    def to_dict(self):
        return {"id": self.id, "title": self.title,
                "content": self.content, "updated": self.updated}

    @property
    def date_label(self):
        try:
            dt = datetime.fromisoformat(self.updated)
            return dt.strftime("%d %b %Y")
        except Exception:
            return ""


class NyxusNotepad(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.notepad")
        self.notes    = []
        self.selected = None
        self._save_tid = None
        self._load()

    def do_activate(self):
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self, title="NYXUS Notepad")
        self.win.set_default_size(760, 540)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)
        root.append(self._build_header())

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_vexpand(True)
        root.append(body)
        body.append(self._build_sidebar())
        body.append(self._build_editor())

        root.append(self._build_statusbar())

        if self.notes:
            self._select(self.notes[0])
        self.win.present()

    # ── Header ──────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hdr.add_css_class("header")

        t = Gtk.Label(label="NYXUS_NOTEPAD")
        t.add_css_class("app-title")
        hdr.append(t)

        self._count_lbl = Gtk.Label(label="")
        self._count_lbl.add_css_class("note-count")
        hdr.append(self._count_lbl)

        sp = Gtk.Box(); sp.set_hexpand(True); hdr.append(sp)

        bn = Gtk.Button(label="+ NEW NOTE")
        bn.add_css_class("btn-toolbar")
        bn.connect("clicked", lambda *_: self._new_note())
        hdr.append(bn)

        self._clip_btn = Gtk.Button(label="⎘ COPY")
        self._clip_btn.add_css_class("btn-clip")
        self._clip_btn.connect("clicked", lambda *_: self._copy_to_clipboard())
        hdr.append(self._clip_btn)

        bd = Gtk.Button(label="🗑 DELETE")
        bd.add_css_class("btn-danger")
        bd.connect("clicked", lambda *_: self._delete_selected())
        hdr.append(bd)
        return hdr

    # ── Sidebar ─────────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class("sidebar")

        self._search = Gtk.Entry()
        self._search.add_css_class("search-entry")
        self._search.set_placeholder_text("SEARCH NOTES...")
        self._search.connect("changed", lambda *_: self._refresh_list())
        box.append(self._search)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroll.set_child(self._list_box)
        box.append(scroll)

        self._refresh_list()
        return box

    def _refresh_list(self):
        c = self._list_box.get_first_child()
        while c:
            n = c.get_next_sibling(); self._list_box.remove(c); c = n

        q = self._search.get_text().lower() if hasattr(self, '_search') else ""
        filtered = [n for n in self.notes if q in n.title.lower() or q in n.content.lower()] if q else self.notes

        self._count_lbl.set_text(f"{len(self.notes)} NOTES")

        for note in filtered:
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            row.add_css_class("note-row")
            if self.selected and self.selected.id == note.id:
                row.add_css_class("note-row-selected")

            name = Gtk.Label(label=note.title[:26] + ("…" if len(note.title) > 26 else ""))
            name.add_css_class("note-row-name"); name.set_halign(Gtk.Align.START)
            row.append(name)

            date = Gtk.Label(label=note.date_label)
            date.add_css_class("note-row-date"); date.set_halign(Gtk.Align.START)
            row.append(date)

            click = Gtk.GestureClick()
            click.connect("pressed", lambda *_, n=note: self._select(n))
            row.add_controller(click)
            self._list_box.append(row)

        if not filtered:
            lbl = Gtk.Label(label="NO NOTES" if not self.notes else "NO RESULTS")
            lbl.add_css_class("empty-lbl")
            lbl.set_margin_top(24)
            self._list_box.append(lbl)

    # ── Editor ──────────────────────────────────────────────────────────────────
    def _build_editor(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_hexpand(True)

        self._title_entry = Gtk.Entry()
        self._title_entry.add_css_class("editor-title")
        self._title_entry.set_placeholder_text("NOTE TITLE...")
        self._title_entry.set_has_frame(False)
        self._title_entry.connect("changed", self._on_title_changed)
        box.append(self._title_entry)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._body_view = Gtk.TextView()
        self._body_view.add_css_class("editor-body")
        self._body_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._body_view.set_left_margin(16); self._body_view.set_right_margin(16)
        self._body_view.set_top_margin(12);  self._body_view.set_bottom_margin(12)
        self._body_view.set_pixels_above_lines(2)
        self._body_buf = self._body_view.get_buffer()
        self._body_buf.connect("changed", self._on_body_changed)
        scroll.set_child(self._body_view)
        box.append(scroll)

        self._set_editor_sensitive(False)
        return box

    def _set_editor_sensitive(self, on):
        self._title_entry.set_sensitive(on)
        self._body_view.set_sensitive(on)

    def _select(self, note):
        self.selected = note
        self._title_entry.set_text(note.title)
        self._body_buf.set_text(note.content)
        self._set_editor_sensitive(True)
        self._refresh_list()
        self._update_status()

    def _on_title_changed(self, entry):
        if not self.selected: return
        self.selected.title = entry.get_text()
        self.selected.updated = datetime.now().isoformat()
        self._schedule_save()
        self._refresh_list()

    def _on_body_changed(self, buf):
        if not self.selected: return
        s, e = buf.get_bounds()
        self.selected.content = buf.get_text(s, e, False)
        self.selected.updated = datetime.now().isoformat()
        self._schedule_save()
        self._update_status()

    def _update_status(self):
        if not self.selected:
            self._status_lbl.set_text("NO NOTE SELECTED")
            return
        s, e = self._body_buf.get_bounds()
        text = self._body_buf.get_text(s, e, False)
        words = len(text.split()) if text.strip() else 0
        chars = len(text)
        self._status_lbl.set_text(f"{len(self.notes)} NOTES  ·  {words} WORDS  ·  {chars} CHARS")

    # ── Status bar ──────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bar.add_css_class("statusbar")
        self._status_lbl = Gtk.Label(label="READY")
        self._status_lbl.add_css_class("status-text")
        bar.append(self._status_lbl)
        sp = Gtk.Box(); sp.set_hexpand(True); bar.append(sp)
        self._saved_lbl = Gtk.Label(label="● SAVED")
        self._saved_lbl.add_css_class("status-text"); self._saved_lbl.add_css_class("status-saved")
        bar.append(self._saved_lbl)
        return bar

    # ── Actions ─────────────────────────────────────────────────────────────────
    def _new_note(self):
        note = NoteItem()
        self.notes.insert(0, note)
        self._save(); self._select(note)

    def _delete_selected(self):
        if not self.selected: return
        self.notes = [n for n in self.notes if n.id != self.selected.id]
        self.selected = None
        self._title_entry.set_text("")
        self._body_buf.set_text("")
        self._set_editor_sensitive(False)
        self._save(); self._refresh_list()
        if self.notes: self._select(self.notes[0])

    def _copy_to_clipboard(self):
        if not self.selected: return
        s, e = self._body_buf.get_bounds()
        text = self._body_buf.get_text(s, e, False)
        clip = Gdk.Display.get_default().get_clipboard()
        clip.set(text)
        self._saved_lbl.set_text("● COPIED")
        GLib.timeout_add(2000, lambda: (self._saved_lbl.set_text("● SAVED"), GLib.SOURCE_REMOVE)[1])

    def _schedule_save(self):
        self._saved_lbl.set_text("○ SAVING...")
        if self._save_tid: GLib.source_remove(self._save_tid)
        self._save_tid = GLib.timeout_add(500, self._do_save)

    def _do_save(self):
        self._save()
        self._saved_lbl.set_text("● SAVED")
        self._save_tid = None
        return GLib.SOURCE_REMOVE

    def _save(self):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump({"notes": [n.to_dict() for n in self.notes]}, f, indent=2)
        except Exception as e:
            print(f"[notepad] save error: {e}")

    def _load(self):
        try:
            with open(DATA_FILE) as f:
                self.notes = [NoteItem(d) for d in json.load(f).get("notes", [])]
        except Exception:
            self.notes = []


if __name__ == "__main__":
    NyxusNotepad().run(None)
