#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Notepad — GTK4 editor + clipboard history                     ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
import json, uuid, os, math
from datetime import datetime

DATA_FILE  = os.path.expanduser("~/.nyxus/notepad.json")
CLIP_FILE  = os.path.expanduser("~/.nyxus/clipboard.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

def glow_text(cr, x, y, text, r, g, b, size=12, bold=False):
    cr.select_font_face("JetBrains Mono", 0, 1 if bold else 0)
    cr.set_font_size(size)
    for dx, dy, a in [(-1,-1,0.20),(1,-1,0.20),(-1,1,0.20),(1,1,0.20),
                       (-2,0,0.08),(2,0,0.08),(0,-2,0.08),(0,2,0.08)]:
        cr.set_source_rgba(r, g, b, a)
        cr.move_to(x+dx, y+dy)
        cr.show_text(text)
    cr.set_source_rgba(r, g, b, 1.0)
    cr.move_to(x, y)
    cr.show_text(text)

CSS = b"""
* { font-family: 'JetBrains Mono', 'Monospace', monospace; }
window { background-color: #030206; color: #e8e0f5; }

.hdr {
    background-color: rgba(7,3,15,0.97);
    border-bottom: 1px solid rgba(255,0,255,0.28);
    padding: 6px 14px;
    min-height: 44px;
}
.hdr-title {
    color: #ff00ff;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 3px;
}
.hdr-count {
    color: #0088ff;
    font-size: 10px;
    border: 1px solid rgba(0,136,255,0.35);
    padding: 1px 7px;
    border-radius: 2px;
    margin-left: 8px;
}
.btn-new {
    background-color: rgba(204,0,255,0.08);
    color: #cc00ff;
    border: 1px solid rgba(204,0,255,0.7);
    border-radius: 2px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: bold;
}
.btn-new:hover { background-color: rgba(204,0,255,0.22); }
.btn-copy {
    background-color: rgba(0,136,255,0.08);
    color: #0088ff;
    border: 1px solid rgba(0,136,255,0.5);
    border-radius: 2px;
    padding: 4px 10px;
    font-size: 11px;
}
.btn-copy:hover { background-color: rgba(0,136,255,0.2); }
.btn-del {
    background-color: transparent;
    color: #ff5500;
    border: 1px solid rgba(255,85,0,0.4);
    border-radius: 2px;
    padding: 4px 10px;
    font-size: 11px;
}
.btn-del:hover { background-color: rgba(255,85,0,0.15); }
.hdr-saved { color: #39ff14; font-size: 10px; letter-spacing: 1px; }
.hdr-saving { color: #ffff00; font-size: 10px; letter-spacing: 1px; }

/* Sidebar */
.sidebar {
    background-color: rgba(7,3,15,0.85);
    border-right: 1px solid rgba(204,0,255,0.2);
    min-width: 210px;
    max-width: 210px;
}
.sidebar-title {
    color: #cc00ff;
    font-size: 9px;
    font-weight: bold;
    letter-spacing: 3px;
    padding: 8px 12px 4px 12px;
    border-bottom: 1px solid rgba(204,0,255,0.15);
}
.search-entry {
    background-color: transparent;
    color: #e8e0f5;
    border: none;
    border-bottom: 1px solid rgba(204,0,255,0.2);
    border-radius: 0;
    padding: 7px 12px;
    font-size: 11px;
    box-shadow: none;
    caret-color: #cc00ff;
}
.search-entry text { background-color: transparent; }
.note-row {
    background-color: transparent;
    padding: 9px 12px;
    border-bottom: 1px solid rgba(204,0,255,0.08);
}
.note-row:hover { background-color: rgba(204,0,255,0.06); }
.note-row-sel {
    background-color: rgba(204,0,255,0.12);
    border-left: 3px solid #cc00ff;
}
.note-name { color: #e8e0f5; font-size: 12px; font-weight: bold; }
.note-name-sel { color: #cc00ff; }
.note-date { color: rgba(112,96,160,0.8); font-size: 9px; }
.note-preview { color: rgba(232,224,245,0.45); font-size: 10px; }

/* Editor */
.editor-area { background-color: #030206; }
.editor-title {
    background-color: transparent;
    color: #ff00ff;
    font-size: 16px;
    font-weight: bold;
    letter-spacing: 1px;
    border: none;
    border-bottom: 1px solid rgba(255,0,255,0.18);
    border-radius: 0;
    padding: 12px 18px;
    box-shadow: none;
    caret-color: #ff00ff;
}
.editor-title text { background-color: transparent; color: #ff00ff; }
.editor-body {
    background-color: transparent;
    color: #e8e0f5;
    font-size: 13px;
    caret-color: #cc00ff;
}
.editor-body text { background-color: transparent; }

/* Statusbar */
.statusbar {
    background-color: rgba(7,3,15,0.90);
    border-top: 1px solid rgba(204,0,255,0.15);
    padding: 4px 14px;
}
.status-txt { color: rgba(112,96,160,0.9); font-size: 10px; }

/* Clipboard panel */
.clip-panel {
    background-color: rgba(5,2,12,0.90);
    border-left: 1px solid rgba(0,136,255,0.2);
    min-width: 200px;
    max-width: 200px;
}
.clip-title {
    color: #0088ff;
    font-size: 9px;
    font-weight: bold;
    letter-spacing: 3px;
    padding: 8px 12px 4px 12px;
    border-bottom: 1px solid rgba(0,136,255,0.18);
}
.clip-entry {
    background-color: transparent;
    padding: 7px 10px;
    border-bottom: 1px solid rgba(0,136,255,0.08);
}
.clip-entry:hover { background-color: rgba(0,136,255,0.08); }
.clip-text { color: rgba(232,224,245,0.75); font-size: 10px; }
.clip-meta { color: rgba(0,136,255,0.6); font-size: 9px; }
.clip-clear-btn {
    background-color: transparent;
    color: rgba(255,85,0,0.7);
    border: none;
    font-size: 10px;
    padding: 3px 8px;
}
.clip-clear-btn:hover { color: #ff5500; }
.empty-msg { color: rgba(42,26,74,0.9); font-size: 11px; letter-spacing: 2px; }
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
        return {"id":self.id,"title":self.title,"content":self.content,"updated":self.updated}

    @property
    def date_label(self):
        try:
            return datetime.fromisoformat(self.updated).strftime("%d %b %Y · %H:%M")
        except Exception:
            return ""


class ClipEntry:
    def __init__(self, text):
        self.id        = str(uuid.uuid4())[:8]
        self.text      = text
        self.timestamp = datetime.now().isoformat()
        self.chars     = len(text)

    @classmethod
    def from_dict(cls, d):
        obj = cls.__new__(cls)
        obj.id        = d.get("id", str(uuid.uuid4())[:8])
        obj.text      = d.get("text", "")
        obj.timestamp = d.get("timestamp", datetime.now().isoformat())
        obj.chars     = d.get("chars", len(obj.text))
        return obj

    def to_dict(self):
        return {"id":self.id,"text":self.text,"timestamp":self.timestamp,"chars":self.chars}

    @property
    def date_label(self):
        try:
            return datetime.fromisoformat(self.timestamp).strftime("%H:%M · %d %b")
        except Exception:
            return ""

    @property
    def preview(self):
        t = self.text.strip().replace('\n',' ')
        return t[:38] + ("…" if len(t) > 38 else "")


class NyxusNotepad(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.notepad")
        self.notes    = []
        self.selected = None
        self.clip_hist = []
        self._save_tid = None
        self._ignore_body_change = False
        self._load()
        self._load_clip()

    def do_activate(self):
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self, title="NYXUS Notepad")
        self.win.set_default_size(920, 580)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)
        root.append(self._build_header())

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_vexpand(True)
        root.append(body)

        body.append(self._build_sidebar())
        body.append(self._build_editor())
        body.append(self._build_clip_panel())

        root.append(self._build_statusbar())

        if self.notes:
            self._select(self.notes[0])
        self.win.present()

    # ── Header ─────────────────────────────────────────────────────────────────
    def _build_header(self):
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hdr.add_css_class("hdr")

        t = Gtk.Label(label="NYXUS_NOTEPAD")
        t.add_css_class("hdr-title")
        hdr.append(t)

        self._count_lbl = Gtk.Label()
        self._count_lbl.add_css_class("hdr-count")
        hdr.append(self._count_lbl)
        self._sync_count()

        sp = Gtk.Box(); sp.set_hexpand(True); hdr.append(sp)

        bn = Gtk.Button(label="+ NEW NOTE"); bn.add_css_class("btn-new")
        bn.connect("clicked", lambda *_: self._new_note()); hdr.append(bn)

        bc = Gtk.Button(label="⎘ COPY"); bc.add_css_class("btn-copy")
        bc.connect("clicked", lambda *_: self._copy_note()); hdr.append(bc)

        bd = Gtk.Button(label="DELETE"); bd.add_css_class("btn-del")
        bd.connect("clicked", lambda *_: self._delete_selected()); hdr.append(bd)

        self._saved_lbl = Gtk.Label(label="● SAVED")
        self._saved_lbl.add_css_class("hdr-saved")
        self._saved_lbl.set_margin_start(12)
        hdr.append(self._saved_lbl)
        return hdr

    # ── Sidebar ─────────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        sb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sb.add_css_class("sidebar")

        tl = Gtk.Label(label="NOTES"); tl.add_css_class("sidebar-title")
        tl.set_halign(Gtk.Align.START); sb.append(tl)

        self._search = Gtk.Entry()
        self._search.add_css_class("search-entry")
        self._search.set_placeholder_text("SEARCH NOTES...")
        self._search.set_has_frame(False)
        self._search.connect("changed", lambda *_: self._refresh_list())
        sb.append(self._search)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroll.set_child(self._list_box)
        sb.append(scroll)
        self._refresh_list()
        return sb

    def _refresh_list(self):
        c = self._list_box.get_first_child()
        while c:
            n = c.get_next_sibling(); self._list_box.remove(c); c = n

        q = self._search.get_text().lower() if hasattr(self, '_search') else ""
        notes = [n for n in self.notes
                 if q in n.title.lower() or q in n.content.lower()] if q else self.notes

        for note in notes:
            is_sel = self.selected and self.selected.id == note.id
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            row.add_css_class("note-row")
            if is_sel:
                row.add_css_class("note-row-sel")

            nm = Gtk.Label(label=note.title[:22] + ("…" if len(note.title) > 22 else ""))
            nm.add_css_class("note-name" + ("-sel" if is_sel else ""))
            nm.set_halign(Gtk.Align.START); nm.set_xalign(0)
            row.append(nm)

            pr_txt = note.content[:32].replace('\n', ' ') + ("…" if len(note.content) > 32 else "")
            pr = Gtk.Label(label=pr_txt)
            pr.add_css_class("note-preview"); pr.set_halign(Gtk.Align.START); pr.set_xalign(0)
            row.append(pr)

            dt = Gtk.Label(label=note.date_label)
            dt.add_css_class("note-date"); dt.set_halign(Gtk.Align.START); dt.set_xalign(0)
            row.append(dt)

            gc = Gtk.GestureClick()
            gc.connect("pressed", lambda *_, n=note: self._select(n))
            row.add_controller(gc)
            self._list_box.append(row)

        if not notes:
            lbl = Gtk.Label(label="NO NOTES" if not self.notes else "NO RESULTS")
            lbl.add_css_class("empty-msg"); lbl.set_margin_top(24)
            self._list_box.append(lbl)

    # ── Editor ──────────────────────────────────────────────────────────────────
    def _build_editor(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_hexpand(True); box.add_css_class("editor-area")

        self._title_entry = Gtk.Entry()
        self._title_entry.add_css_class("editor-title")
        self._title_entry.set_placeholder_text("NOTE TITLE...")
        self._title_entry.set_has_frame(False)
        self._title_entry.connect("changed", self._on_title_changed)
        box.append(self._title_entry)

        # Dot-grid background drawn behind the text area
        self._editor_scroll = Gtk.ScrolledWindow()
        self._editor_scroll.set_vexpand(True)
        self._editor_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        self._body_view = Gtk.TextView()
        self._body_view.add_css_class("editor-body")
        self._body_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self._body_view.set_left_margin(18); self._body_view.set_right_margin(18)
        self._body_view.set_top_margin(14);  self._body_view.set_bottom_margin(14)
        self._body_view.set_pixels_above_lines(3)
        self._body_buf = self._body_view.get_buffer()
        self._body_buf.connect("changed", self._on_body_changed)

        # Clipboard capture: intercept Ctrl+V
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key_pressed)
        self._body_view.add_controller(key_ctrl)

        self._editor_scroll.set_child(self._body_view)
        box.append(self._editor_scroll)

        self._set_editor_sensitive(False)
        return box

    def _set_editor_sensitive(self, on):
        self._title_entry.set_sensitive(on)
        self._body_view.set_sensitive(on)
        if not on:
            self._title_entry.set_text("")
            self._ignore_body_change = True
            self._body_buf.set_text("")
            self._ignore_body_change = False

    def _select(self, note):
        self.selected = note
        self._ignore_body_change = True
        self._title_entry.set_text(note.title)
        self._body_buf.set_text(note.content)
        self._ignore_body_change = False
        self._set_editor_sensitive(True)
        self._refresh_list()
        self._update_status()
        GLib.idle_add(lambda: self._body_view.grab_focus() or False)

    def _on_title_changed(self, entry):
        if not self.selected: return
        self.selected.title = entry.get_text()
        self.selected.updated = datetime.now().isoformat()
        self._schedule_save()
        self._refresh_list()

    def _on_body_changed(self, buf):
        if self._ignore_body_change or not self.selected: return
        s, e = buf.get_bounds()
        self.selected.content = buf.get_text(s, e, False)
        self.selected.updated = datetime.now().isoformat()
        self._schedule_save()
        self._update_status()

    def _on_key_pressed(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_v and (state & Gdk.ModifierType.CONTROL_MASK):
            clip = Gdk.Display.get_default().get_clipboard()
            clip.read_text_async(None, self._on_clip_read)
        return False  # allow default paste to happen

    def _on_clip_read(self, clip, result):
        try:
            text = clip.read_text_finish(result)
            if text and text.strip():
                self._add_clip_entry(text)
        except Exception:
            pass

    # ── Clipboard panel ─────────────────────────────────────────────────────────
    def _build_clip_panel(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class("clip-panel")

        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        tl = Gtk.Label(label="CLIPBOARD"); tl.add_css_class("clip-title")
        tl.set_halign(Gtk.Align.START); tl.set_hexpand(True)
        hdr.append(tl)
        cl = Gtk.Button(label="CLEAR"); cl.add_css_class("clip-clear-btn")
        cl.connect("clicked", lambda *_: self._clear_clip())
        hdr.append(cl)
        box.append(hdr)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._clip_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        scroll.set_child(self._clip_box)
        box.append(scroll)

        self._refresh_clip_panel()
        return box

    def _refresh_clip_panel(self):
        c = self._clip_box.get_first_child()
        while c:
            n = c.get_next_sibling(); self._clip_box.remove(c); c = n

        for entry in self.clip_hist[:50]:
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            row.add_css_class("clip-entry")

            pr = Gtk.Label(label=entry.preview)
            pr.add_css_class("clip-text"); pr.set_halign(Gtk.Align.START)
            pr.set_xalign(0); pr.set_wrap(True); pr.set_max_width_chars(22)
            row.append(pr)

            meta = Gtk.Label(label=f"{entry.date_label} · {entry.chars}c")
            meta.add_css_class("clip-meta"); meta.set_halign(Gtk.Align.START)
            row.append(meta)

            gc = Gtk.GestureClick()
            gc.connect("pressed", lambda *_, e=entry: self._paste_clip_entry(e))
            row.add_controller(gc)
            self._clip_box.append(row)

        if not self.clip_hist:
            lbl = Gtk.Label(label="NO HISTORY")
            lbl.add_css_class("empty-msg"); lbl.set_margin_top(20)
            self._clip_box.append(lbl)

    def _add_clip_entry(self, text):
        if self.clip_hist and self.clip_hist[0].text == text:
            return
        entry = ClipEntry(text)
        self.clip_hist.insert(0, entry)
        self.clip_hist = self.clip_hist[:50]
        self._save_clip()
        self._refresh_clip_panel()

    def _paste_clip_entry(self, entry):
        if not self.selected or not self._body_view.get_sensitive():
            return
        buf = self._body_buf
        buf.insert_at_cursor(entry.text)
        self._body_view.grab_focus()

    def _clear_clip(self):
        self.clip_hist = []
        self._save_clip()
        self._refresh_clip_panel()

    # ── Statusbar ──────────────────────────────────────────────────────────────
    def _build_statusbar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        bar.add_css_class("statusbar")
        self._status_lbl = Gtk.Label(label="READY")
        self._status_lbl.add_css_class("status-txt")
        bar.append(self._status_lbl)
        return bar

    def _update_status(self):
        if not self.selected:
            self._status_lbl.set_text("NO NOTE SELECTED")
            return
        s, e = self._body_buf.get_bounds()
        text  = self._body_buf.get_text(s, e, False)
        words = len(text.split()) if text.strip() else 0
        self._status_lbl.set_text(
            f"{len(self.notes)} NOTES  ·  {words} WORDS  ·  {len(text)} CHARS"
            f"  ·  {len(self.clip_hist)} CLIPS"
        )

    # ── Actions ────────────────────────────────────────────────────────────────
    def _new_note(self):
        note = NoteItem()
        self.notes.insert(0, note)
        self._save(); self._sync_count()
        self._select(note)
        GLib.idle_add(lambda: self._title_entry.grab_focus() or False)

    def _delete_selected(self):
        if not self.selected: return
        self.notes = [n for n in self.notes if n.id != self.selected.id]
        self.selected = None
        self._set_editor_sensitive(False)
        self._save(); self._sync_count(); self._refresh_list()
        if self.notes:
            self._select(self.notes[0])

    def _copy_note(self):
        if not self.selected: return
        s, e = self._body_buf.get_bounds()
        text = self._body_buf.get_text(s, e, False)
        Gdk.Display.get_default().get_clipboard().set(text)
        self._add_clip_entry(text)
        self._saved_lbl.set_text("⎘ COPIED")
        self._saved_lbl.remove_css_class("hdr-saved")
        self._saved_lbl.add_css_class("hdr-saving")
        GLib.timeout_add(2000, self._reset_saved_lbl)

    def _reset_saved_lbl(self):
        self._saved_lbl.set_text("● SAVED")
        self._saved_lbl.remove_css_class("hdr-saving")
        self._saved_lbl.add_css_class("hdr-saved")
        return GLib.SOURCE_REMOVE

    def _sync_count(self):
        n = len(self.notes)
        self._count_lbl.set_text(f"{n} {'NOTE' if n==1 else 'NOTES'}")

    # ── Save / Load ────────────────────────────────────────────────────────────
    def _schedule_save(self):
        self._saved_lbl.set_text("○ SAVING...")
        self._saved_lbl.remove_css_class("hdr-saved")
        self._saved_lbl.add_css_class("hdr-saving")
        if self._save_tid:
            GLib.source_remove(self._save_tid)
        self._save_tid = GLib.timeout_add(600, self._do_save)

    def _do_save(self):
        self._save()
        self._saved_lbl.set_text("● SAVED")
        self._saved_lbl.remove_css_class("hdr-saving")
        self._saved_lbl.add_css_class("hdr-saved")
        self._save_tid = None
        return GLib.SOURCE_REMOVE

    def _save(self):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump({"notes": [n.to_dict() for n in self.notes]}, f, indent=2)
        except Exception as ex:
            print(f"[notepad] save: {ex}")

    def _load(self):
        try:
            with open(DATA_FILE) as f:
                self.notes = [NoteItem(d) for d in json.load(f).get("notes", [])]
        except Exception:
            self.notes = []

    def _save_clip(self):
        try:
            with open(CLIP_FILE, "w") as f:
                json.dump({"history": [e.to_dict() for e in self.clip_hist]}, f, indent=2)
        except Exception as ex:
            print(f"[notepad] clip save: {ex}")

    def _load_clip(self):
        try:
            with open(CLIP_FILE) as f:
                self.clip_hist = [ClipEntry.from_dict(d) for d in json.load(f).get("history", [])]
        except Exception:
            self.clip_hist = []


if __name__ == "__main__":
    NyxusNotepad().run(None)
