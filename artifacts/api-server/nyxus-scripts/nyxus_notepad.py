#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Notepad — Enterprise · 3-panel · Markdown · Tags · Export     ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Pango, Gio
import json, uuid, os, math, re
from datetime import datetime

DATA_FILE = os.path.expanduser("~/.nyxus/notepad.json")
CLIP_FILE = os.path.expanduser("~/.nyxus/clipboard.json")
TAGS_FILE = os.path.expanduser("~/.nyxus/tags.json")
EXPORT_DIR= os.path.expanduser("~/.nyxus/exports/")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)

PALETTE = [
    (1.0,  0.0,  1.0 ),
    (0.8,  0.0,  1.0 ),
    (0.0,  0.53, 1.0 ),
    (0.22, 1.0,  0.08),
    (1.0,  1.0,  0.0 ),
    (1.0,  0.33, 0.0 ),
]
C_PINK, C_PURPLE, C_BLUE, C_GREEN, C_YELLOW, C_ORANGE = PALETTE
C_DIM  = (0.44, 0.376, 0.627)
C_TEXT = (0.91, 0.88,  0.96 )

TAG_COLORS = ["#ff00ff","#cc00ff","#0088ff","#39ff14","#ffff00","#ff5500"]

import random as _rand

def _rng_seed(x, y, w=0, h=0):
    return int(x*3 + y*7 + (w or 1)*11 + (h or 1)*13) % 65535

def sketch_rect(cr, x, y, w, h, r, g, b, thick=2.2, jitter=2.8, fill_rgba=None):
    rng = _rand.Random(_rng_seed(x,y,w,h))
    j = lambda s=1.0: rng.uniform(-jitter*s, jitter*s)
    def _path():
        cr.move_to(x+j(.5),y+j(.5))
        cr.curve_to(x+w*.33+j(),y+j(),x+w*.67+j(),y+j(),x+w+j(.5),y+j(.5))
        cr.curve_to(x+w+j(),y+h*.33+j(),x+w+j(),y+h*.67+j(),x+w+j(.5),y+h+j(.5))
        cr.curve_to(x+w*.67+j(),y+h+j(),x+w*.33+j(),y+h+j(),x+j(.5),y+h+j(.5))
        cr.curve_to(x+j(),y+h*.67+j(),x+j(),y+h*.33+j(),x+j(.5),y+j(.5))
        cr.close_path()
    if fill_rgba:
        _path(); cr.set_source_rgba(*fill_rgba); cr.fill()
        rng2 = _rand.Random(_rng_seed(x,y,w,h)); j = lambda s=1.0: rng2.uniform(-jitter*s,jitter*s)
    _path()
    cr.set_source_rgba(r,g,b,0.88); cr.set_line_width(thick)
    cr.set_line_cap(1); cr.set_line_join(1); cr.stroke()

def marker_text(cr, x, y, txt, r, g, b, size=13, bold=False, alpha=0.90):
    cr.select_font_face("Caveat", 0, 1 if bold else 0)
    cr.set_font_size(size)
    cr.set_source_rgba(r, g, b, alpha*0.15); cr.move_to(x+1.0, y+0.8); cr.show_text(txt)
    cr.set_source_rgba(r, g, b, alpha);      cr.move_to(x, y);          cr.show_text(txt)

def glow_text(cr, x, y, txt, r, g, b, size=12, bold=False):
    marker_text(cr, x, y, txt, r, g, b, size=size, bold=bold)

def sketch_badge(cr, x, y, txt, color, angle=-4.0, size=10):
    r, g, b = color; cr.save()
    cr.translate(x, y); cr.rotate(math.radians(angle))
    cr.select_font_face("Caveat", 0, 1); cr.set_font_size(size)
    ext = cr.text_extents(txt); bw = ext.width+18; bh = size+10
    sketch_rect(cr,-6,-(bh-2),bw,bh,r,g,b,thick=2.0,jitter=2.0,fill_rgba=(r,g,b,0.12))
    cr.set_source_rgba(r,g,b,0.92); cr.move_to(0,0); cr.show_text(txt); cr.restore()

def rainbow_bar(cr, x, y, w, h=3):
    seg = w / len(PALETTE)
    for i,(r,g,b) in enumerate(PALETTE):
        cr.set_source_rgba(r,g,b,0.75); cr.rectangle(x+i*seg,y,seg,h); cr.fill()

def dot_grid(cr, x, y, w, h):
    pass  # replaced by paper lines

def notebook_lines(cr, x, y, w, h, spacing=22):
    """Faint ruled lines for the dark paper look."""
    cr.set_line_width(0.5)
    for ly in range(int(y)+spacing, int(y+h), spacing):
        cr.set_source_rgba(0.38, 0.48, 0.90, 0.18)
        cr.move_to(x, ly); cr.line_to(x+w, ly); cr.stroke()
    # Red margin line
    cr.set_source_rgba(0.85, 0.22, 0.22, 0.42); cr.set_line_width(1.0)
    cr.move_to(x+48, y); cr.line_to(x+48, y+h); cr.stroke()

def hex_to_rgb(h):
    h=h.lstrip('#'); return int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255

def reading_time(text):
    words=len(text.split()); mins=max(1,round(words/200))
    return f"{mins} MIN READ · {words} WORDS"


CSS = """
* { font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', 'Sans'; }
window { background-color: #08080e; color: rgba(232,224,245,0.92); }

.hdr {
    background-color: #0d0d1a;
    border-bottom: 2px solid rgba(255,0,255,0.18);
    padding: 5px 14px; min-height: 48px;
}
.sidebar {
    background-color: #0d0d1a;
    border-right: 2px solid rgba(204,0,255,0.18);
}
.sidebar-hdr {
    color: rgba(180,160,220,0.80); font-size: 12px; font-weight: bold;
    letter-spacing: 2px; padding: 7px 12px 5px 12px;
    border-bottom: 1px solid rgba(204,0,255,0.14);
}
.new-btn {
    background-color: rgba(255,0,255,0.14); color: #ff88ff;
    border: 2px solid rgba(255,0,255,0.45); border-radius: 4px;
    padding: 5px 14px; font-size: 13px; font-weight: bold; margin: 4px;
}
.new-btn:hover { background-color: rgba(255,0,255,0.28); }
.del-btn {
    background-color: rgba(255,50,30,0.16); color: #ff6655;
    border: 2px solid rgba(255,80,50,0.45); border-radius: 4px;
    padding: 5px 10px; font-size: 13px; font-weight: bold; margin: 4px 2px;
}
.del-btn:hover { background-color: rgba(255,80,50,0.30); }
.exp-btn {
    background-color: rgba(57,255,20,0.10); color: #88ff55;
    border: 2px solid rgba(57,255,20,0.40); border-radius: 4px;
    padding: 5px 10px; font-size: 13px; font-weight: bold; margin: 4px 2px;
}
.exp-btn:hover { background-color: rgba(57,255,20,0.22); }
.pin-btn {
    background-color: rgba(255,255,0,0.10); color: #ffff88;
    border: 2px solid rgba(255,255,0,0.40); border-radius: 4px;
    padding: 5px 10px; font-size: 13px; font-weight: bold; margin: 4px 2px;
}
.sort-btn {
    background-color: rgba(255,255,255,0.06); color: rgba(200,180,240,0.80);
    border: 1px solid rgba(255,255,255,0.12); border-radius: 3px;
    padding: 3px 8px; font-size: 11px; margin: 2px 1px;
}
.sort-btn:hover { background-color: rgba(255,255,255,0.12); }
.sort-active {
    color: #ffff88; border-color: rgba(255,255,0,0.50);
    background-color: rgba(255,255,0,0.10);
}
.search-e {
    background-color: rgba(255,255,255,0.06); color: rgba(232,224,245,0.88);
    border: 2px solid rgba(255,0,255,0.30); border-radius: 4px;
    padding: 5px 12px; font-size: 13px; box-shadow: none;
    caret-color: #ff00ff; margin: 4px;
}
.search-e:focus { border-color: #ff00ff; }
.search-e text { background-color: transparent; }
.tag-e {
    background-color: rgba(255,255,255,0.06); color: rgba(232,224,245,0.88);
    border: 2px solid rgba(255,255,0,0.28); border-radius: 4px;
    padding: 4px 10px; font-size: 12px; box-shadow: none;
    caret-color: #ffff00; margin: 0 4px;
}
.tag-e text { background-color: transparent; }
.editor-area {
    background-color: #08080e; color: rgba(232,224,245,0.92);
    border: none; padding: 14px 14px 14px 60px; font-size: 15px;
    caret-color: #ff00ff;
    font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', 'Sans';
}
.editor-area text { background-color: transparent; color: rgba(232,224,245,0.92); }
.editor-area text selection { background-color: rgba(255,0,255,0.22); }
.clip-btn {
    background-color: transparent; color: rgba(180,160,220,0.80);
    border: none; border-bottom: 1px solid rgba(255,0,255,0.10);
    border-radius: 0; padding: 6px 10px; font-size: 12px; text-align: left;
    min-height: 0;
}
.clip-btn:hover { background-color: rgba(0,136,255,0.10); color: #66bbff; }
.title-e {
    background-color: transparent; color: #ff88ff;
    border: none; border-bottom: 2px solid rgba(255,0,255,0.35);
    border-radius: 0; padding: 6px 14px; font-size: 18px; font-weight: bold;
    letter-spacing: 1px;
    font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', 'Sans';
}
.title-e text { background-color: transparent; color: #ff88ff; }

textview { background-color: #08080e; color: rgba(232,224,245,0.92); }
textview text { background-color: transparent; color: rgba(232,224,245,0.92); }
textview text selection { background-color: rgba(255,0,255,0.22); }
scrolledwindow { background-color: #08080e; }
scrolledwindow undershoot.top, scrolledwindow undershoot.bottom,
scrolledwindow overshoot.top, scrolledwindow overshoot.bottom {
    background: none;
}
listbox { background-color: #0d0d1a; }
listbox row { background-color: transparent; padding: 2px 0; }
listbox row:selected { background-color: rgba(255,0,255,0.14); }
entry { background-color: rgba(255,255,255,0.05); color: rgba(232,224,245,0.90); }
entry text { background-color: transparent; color: rgba(232,224,245,0.90); }
"""


class NyxusNotepad(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.notepad",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self._notes = []; self._sel_id = None; self._sort = "modified"
        self._filter_q = ""; self._filter_tag = ""
        self._clipboard_history = []
        self._load_notes(); self._load_clipboard()

    def _load_notes(self):
        try:
            with open(DATA_FILE) as f: self._notes = json.load(f)
            for n in self._notes:
                if "pinned"   not in n: n["pinned"]   = False
                if "tags"     not in n: n["tags"]      = []
                if "color"    not in n: n["color"]     = "#cc00ff"
                if "wordcount"not in n: n["wordcount"] = len(n.get("text","").split())
        except Exception: self._notes = []

    def _save_notes(self):
        try:
            with open(DATA_FILE, "w") as f: json.dump(self._notes, f, indent=2)
        except Exception: pass

    def _load_clipboard(self):
        try:
            with open(CLIP_FILE) as f: self._clipboard_history = json.load(f)
        except Exception: self._clipboard_history = []

    def _save_clipboard(self):
        try:
            with open(CLIP_FILE, "w") as f: json.dump(self._clipboard_history[:50], f, indent=2)
        except Exception: pass

    def do_activate(self):
        prov = Gtk.CssProvider()
        try: prov.load_from_string(CSS)
        except AttributeError: prov.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self, title="NYXUS Notepad")
        self.win.set_default_size(1280, 800)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)

        # Header bar with rainbow
        self._hdr_da = Gtk.DrawingArea(); self._hdr_da.set_size_request(-1, 50)
        self._hdr_da.set_draw_func(self._draw_hdr, None); root.append(self._hdr_da)

        # Status bar (cairo)
        self._stat_da = Gtk.DrawingArea(); self._stat_da.set_size_request(-1, 28)
        self._stat_da.set_draw_func(self._draw_stat, None)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_vexpand(True); root.append(body)

        body.append(self._build_sidebar())
        body.append(self._build_editor())
        body.append(self._build_clipboard())

        root.append(self._stat_da)

        GLib.timeout_add(2000, self._autosave)
        self.win.present()
        self._refresh_list()

    # ── Header ─────────────────────────────────────────────────────────────────
    def _draw_hdr(self, area, cr, w, h, _):
        cr.set_source_rgb(0.05, 0.05, 0.10); cr.rectangle(0,0,w,h); cr.fill()
        notebook_lines(cr, 0, 0, w, h, spacing=18)
        sketch_badge(cr, 16, h-10, "  NYXUS NOTEPAD", C_PINK, angle=-2.0, size=15)
        n = len(self._notes)
        stats = [
            (f" {n} notes ", C_BLUE),
            (f" {len(self._clipboard_history)} clips ", C_GREEN),
            (f" {self._cur_words()} words ", C_YELLOW),
            (f" {self._cur_read_time()} ", C_PURPLE),
        ]
        xp = 260
        for stxt, col in stats:
            cr.select_font_face("Caveat", 0, 1); cr.set_font_size(11)
            ew = cr.text_extents(stxt).width
            sketch_rect(cr, xp, h-22, ew+10, 18, *col, thick=1.6, jitter=1.8, fill_rgba=(*col,0.10))
            cr.set_source_rgba(*col, 0.90); cr.move_to(xp+5, h-8); cr.show_text(stxt)
            xp += ew + 18
        rainbow_bar(cr, 0, h-3, w, 3)

    def _draw_stat(self, area, cr, w, h, _):
        cr.set_source_rgb(0.05, 0.05, 0.10); cr.rectangle(0,0,w,h); cr.fill()
        rainbow_bar(cr, 0, 0, w, 3)
        note = self._cur_note()
        if note:
            txt = note.get("text","")
            chars = len(txt); words = len(txt.split()) if txt.strip() else 0
            sents = txt.count('.')+txt.count('!')+txt.count('?')
            parts = [
                (f" Chars: {chars} ",   C_PINK),
                (f" Words: {words} ",   C_PURPLE),
                (f" Sentences: {sents} ", C_BLUE),
                (f" {self._cur_read_time()} ", C_GREEN),
                (f" Tags: {', '.join(note.get('tags',[])) or 'none'} ", C_YELLOW),
            ]
            xp = 10
            for stxt, col in parts:
                cr.select_font_face("Caveat", 0, 1); cr.set_font_size(10)
                ew = cr.text_extents(stxt).width
                sketch_rect(cr, xp, 3, ew+8, h-8, *col, thick=1.5, jitter=1.6, fill_rgba=(*col,0.08))
                cr.set_source_rgba(*col, 0.90); cr.move_to(xp+4, h-7); cr.show_text(stxt)
                xp += ew + 12
            mod = note.get("modified","")[:16]
            cr.select_font_face("Caveat",0,0); cr.set_font_size(10)
            cr.set_source_rgba(*C_DIM, 0.65)
            ext = cr.text_extents(f"saved {mod}")
            cr.move_to(w-ext.width-12, h-7); cr.show_text(f"saved {mod}")

    # ── Sidebar ─────────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.add_css_class("sidebar"); box.set_size_request(260,-1)

        hdr = Gtk.Label(label="NOTES"); hdr.add_css_class("sidebar-hdr")
        hdr.set_halign(Gtk.Align.START); box.append(hdr)

        # Search
        self._search = Gtk.Entry(); self._search.add_css_class("search-e")
        self._search.set_placeholder_text("SEARCH NOTES...")
        self._search.connect("changed", lambda e: setattr(self,'_filter_q',e.get_text().lower()) or self._refresh_list())
        box.append(self._search)

        # Sort buttons
        sort_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        sort_box.set_margin_start(4); sort_box.set_margin_end(4)
        self._sort_btns = {}
        for lbl, key in [("DATE","modified"),("TITLE","title"),("WORDS","wordcount")]:
            b = Gtk.Button(label=lbl); b.add_css_class("sort-btn")
            if key == self._sort: b.add_css_class("sort-active")
            b.connect("clicked", lambda *_,k=key:self._set_sort(k))
            sort_box.append(b); self._sort_btns[key] = b
        box.append(sort_box)

        # Note list
        sc = Gtk.ScrolledWindow(); sc.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        sc.set_vexpand(True)
        self._list_da = Gtk.DrawingArea(); self._list_da.set_size_request(260,-1)
        self._list_da.set_draw_func(self._draw_list, None)
        click = Gtk.GestureClick(); click.connect("pressed", self._list_click)
        self._list_da.add_controller(click)
        sc.set_child(self._list_da); box.append(sc)

        # Bottom buttons
        bb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        bb.set_margin_start(4); bb.set_margin_end(4); bb.set_margin_bottom(4)
        new = Gtk.Button(label="+ NEW"); new.add_css_class("new-btn"); new.set_hexpand(True)
        new.connect("clicked", lambda *_: self._new_note()); bb.append(new)
        pin = Gtk.Button(label="📌 PIN"); pin.add_css_class("pin-btn")
        pin.connect("clicked", lambda *_: self._toggle_pin()); bb.append(pin)
        delete = Gtk.Button(label="✕"); delete.add_css_class("del-btn")
        delete.connect("clicked", lambda *_: self._delete_note()); bb.append(delete)
        exp = Gtk.Button(label="⬇"); exp.add_css_class("exp-btn")
        exp.connect("clicked", lambda *_: self._export_note()); bb.append(exp)
        box.append(bb)
        return box

    def _draw_list(self, area, cr, w, h, _):
        cr.set_source_rgb(0.027,0.012,0.059); cr.rectangle(0,0,w,h); cr.fill()
        dot_grid(cr,0,0,w,max(h,600))
        notes = self._filtered_sorted_notes()
        row_h = 68; self._list_rows = notes
        cr.set_size_request(260, max(400, len(notes)*row_h+4))
        for i, n in enumerate(notes):
            y = i*row_h; active = n["id"]==self._sel_id
            col = hex_to_rgb(n.get("color","#cc00ff"))
            if active:
                cr.set_source_rgba(*col, 0.12); cr.rectangle(0,y,w,row_h); cr.fill()
                cr.set_source_rgba(*col,0.9); cr.set_line_width(2)
                cr.move_to(0,y); cr.line_to(0,y+row_h); cr.stroke()
            else:
                cr.set_source_rgba(*col, 0.03); cr.rectangle(0,y,w,row_h); cr.fill()
            # Pin indicator
            if n.get("pinned"):
                cr.set_source_rgba(*C_YELLOW,0.8); cr.arc(w-10,y+10,3,0,math.pi*2); cr.fill()
            # Title
            title = n.get("title","Untitled")[:24]
            glow_text(cr,10,y+20,title,*col,size=10,bold=True)
            # Preview
            txt = n.get("text","").replace('\n',' ')[:60]+"…" if len(n.get("text",""))>60 else n.get("text","").replace('\n',' ')
            cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(8)
            cr.set_source_rgba(*C_DIM,0.75); cr.move_to(10,y+34); cr.show_text(txt[:46])
            # Tags
            tags=n.get("tags",[]); tx=10
            for j,tag in enumerate(tags[:3]):
                tc = hex_to_rgb(TAG_COLORS[j%len(TAG_COLORS)])
                cr.set_source_rgba(*tc,0.15); cr.rectangle(tx,y+40,len(tag)*5+8,12); cr.fill()
                cr.set_source_rgba(*tc,0.9); cr.set_font_size(7)
                cr.move_to(tx+4,y+50); cr.show_text(tag.upper()); tx+=len(tag)*5+14
            # Date
            mod = n.get("modified","")[:10]
            cr.set_font_size(7); cr.set_source_rgba(*C_DIM,0.5)
            ext = cr.text_extents(mod)
            cr.move_to(w-ext.width-6,y+row_h-5); cr.show_text(mod)
            # Separator
            cr.set_source_rgba(*col,0.06); cr.set_line_width(1)
            cr.move_to(0,y+row_h-1); cr.line_to(w,y+row_h-1); cr.stroke()

    def _list_click(self, gesture, n_press, x, y):
        if not hasattr(self,'_list_rows'): return
        row_h=68; idx=int(y//row_h)
        if 0<=idx<len(self._list_rows):
            self._sel_id=self._list_rows[idx]["id"]; self._load_into_editor()

    # ── Editor ──────────────────────────────────────────────────────────────────
    def _build_editor(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_hexpand(True); box.add_css_class("editor-pane")
        # Editor header row
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        top.set_margin_start(8); top.set_margin_end(8); top.set_margin_top(4)
        self._title_e = Gtk.Entry(); self._title_e.add_css_class("title-e")
        self._title_e.set_hexpand(True)
        self._title_e.connect("changed", self._on_title_change)
        top.append(self._title_e)
        # Color picker dots
        for i, hexcol in enumerate(TAG_COLORS[:6]):
            col = hex_to_rgb(hexcol)
            dot = self._color_dot(hexcol, col); top.append(dot)
        box.append(top)
        # Tag row
        tag_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tag_row.set_margin_start(8); tag_row.set_margin_end(8); tag_row.set_margin_top(2)
        lbl = Gtk.Label(label="TAGS:"); lbl.set_markup('<span font="9" foreground="#cc00ff" weight="bold"> TAGS: </span>')
        tag_row.append(lbl)
        self._tag_e = Gtk.Entry(); self._tag_e.add_css_class("tag-e"); self._tag_e.set_hexpand(True)
        self._tag_e.set_placeholder_text("add,comma,separated,tags  ↵ to save")
        self._tag_e.connect("activate", self._save_tags)
        tag_row.append(self._tag_e)
        box.append(tag_row)
        # Rainbow separator
        sep = Gtk.DrawingArea(); sep.set_size_request(-1, 3)
        sep.set_draw_func(lambda a,cr,w,h,_:(rainbow_bar(cr,0,0,w,3),None)[1],None)
        box.append(sep)
        # Text area
        sc = Gtk.ScrolledWindow(); sc.set_vexpand(True)
        self._buf = Gtk.TextBuffer()
        self._buf.connect("changed", self._on_text_change)
        self._tv = Gtk.TextView(buffer=self._buf)
        self._tv.set_wrap_mode(Gtk.WrapMode.WORD)
        self._tv.add_css_class("editor-area")
        # Clipboard capture
        key_ctrl = Gtk.EventControllerKey()
        key_ctrl.connect("key-pressed", self._on_key)
        self._tv.add_controller(key_ctrl)
        sc.set_child(self._tv); box.append(sc)
        return box

    def _color_dot(self, hexcol, col):
        da = Gtk.DrawingArea(); da.set_size_request(20,20)
        da.set_draw_func(lambda a,cr,w,h,c=col:(
            cr.set_source_rgba(*c,0.85),cr.arc(w/2,h/2,7,0,math.pi*2),cr.fill(),
            cr.set_source_rgba(*c,1.0),cr.set_line_width(1.5),cr.arc(w/2,h/2,7,0,math.pi*2),cr.stroke()
        )[0],None)
        click=Gtk.GestureClick(); click.connect("pressed",lambda *_,h=hexcol:self._set_color(h))
        da.add_controller(click); return da

    def _set_color(self, hexcol):
        n=self._cur_note()
        if n: n["color"]=hexcol; self._save_notes(); self._refresh_list()

    def _build_clipboard(self):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_size_request(220,-1)
        # Header
        da_hdr=Gtk.DrawingArea(); da_hdr.set_size_request(-1,30)
        da_hdr.set_draw_func(self._draw_clip_hdr,None); box.append(da_hdr)
        # Clip list
        sc=Gtk.ScrolledWindow(); sc.set_vexpand(True)
        sc.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC)
        self._clip_box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        sc.set_child(self._clip_box); box.append(sc)
        # Clear button
        clr=Gtk.Button(label="CLEAR HISTORY")
        clr.connect("clicked",self._clear_clips)
        box.append(clr)
        self._refresh_clip_ui()
        return box

    def _draw_clip_hdr(self,area,cr,w,h,_):
        cr.set_source_rgb(0.05, 0.05, 0.10); cr.rectangle(0,0,w,h); cr.fill()
        cr.set_source_rgba(*C_BLUE,0.22); cr.set_line_width(1.5)
        cr.move_to(0,h-1); cr.line_to(w,h-1); cr.stroke()
        sketch_badge(cr,10,h-8,"✂  Clipboard",C_BLUE,angle=-2.5,size=10)

    def _refresh_clip_ui(self):
        for ch in list(self._clip_box):
            self._clip_box.remove(ch)
        for i,entry in enumerate(self._clipboard_history[:30]):
            txt=entry.get("text","") if isinstance(entry,dict) else str(entry)
            col=PALETTE[i%len(PALETTE)]
            da=Gtk.DrawingArea(); da.set_size_request(-1,44)
            da.set_draw_func(self._make_clip_draw(txt,col,i),None)
            click=Gtk.GestureClick(); click.connect("pressed",lambda *_,t=txt:self._paste_clip(t))
            da.add_controller(click); self._clip_box.append(da)

    def _make_clip_draw(self,txt,col,idx):
        def draw(area,cr,w,h,_):
            bg=0.04 if idx%2==0 else 0.0
            cr.set_source_rgba(*col,bg); cr.rectangle(0,0,w,h); cr.fill()
            cr.set_source_rgba(*col,0.6); cr.set_line_width(2)
            cr.move_to(0,0); cr.line_to(0,h); cr.stroke()
            cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(8)
            cr.set_source_rgba(*col,0.85)
            preview=txt.replace('\n',' ')[:36]
            cr.move_to(8,16); cr.show_text(preview)
            if len(txt)>36:
                cr.set_source_rgba(*col,0.5); cr.move_to(8,28); cr.show_text(txt.replace('\n',' ')[36:72])
            cr.set_source_rgba(*col,0.3); cr.set_line_width(1)
            cr.move_to(0,h-1); cr.line_to(w,h-1); cr.stroke()
        return draw

    def _paste_clip(self,txt):
        clip=Gdk.Display.get_default().get_clipboard()
        clip.set(txt)

    def _clear_clips(self,*_):
        self._clipboard_history=[]; self._save_clipboard(); self._refresh_clip_ui()

    # ── Editor actions ──────────────────────────────────────────────────────────
    def _on_key(self,ctrl,keyval,keycode,state):
        if keyval==Gdk.KEY_v and (state & Gdk.ModifierType.CONTROL_MASK):
            clip=Gdk.Display.get_default().get_clipboard()
            clip.read_text_async(None,self._on_paste_done)
        return False

    def _on_paste_done(self,clip,res):
        try:
            txt=clip.read_text_finish(res)
            if txt and txt.strip():
                entry={"text":txt,"time":datetime.now().isoformat()[:19]}
                if not self._clipboard_history or self._clipboard_history[0].get("text")!=txt:
                    self._clipboard_history.insert(0,entry)
                    self._save_clipboard(); GLib.idle_add(self._refresh_clip_ui)
        except Exception: pass

    def _on_title_change(self,entry):
        n=self._cur_note()
        if n:
            n["title"]=entry.get_text(); n["modified"]=datetime.now().isoformat()[:19]
            self._refresh_list()

    def _on_text_change(self,buf):
        n=self._cur_note()
        if n:
            n["text"]=buf.get_text(buf.get_start_iter(),buf.get_end_iter(),False)
            n["modified"]=datetime.now().isoformat()[:19]
            n["wordcount"]=len(n["text"].split())
            self._hdr_da.queue_draw(); self._stat_da.queue_draw()

    def _save_tags(self,entry):
        n=self._cur_note()
        if n:
            raw=entry.get_text().strip()
            n["tags"]=[t.strip() for t in raw.split(",") if t.strip()][:6]
            self._save_notes(); self._refresh_list(); self._stat_da.queue_draw()

    def _load_into_editor(self):
        n=self._cur_note()
        if not n:
            self._title_e.set_text(""); self._buf.set_text(""); self._tag_e.set_text("")
            return
        self._title_e.set_text(n.get("title",""))
        self._buf.handler_block_by_func(self._on_text_change)
        self._buf.set_text(n.get("text",""))
        self._buf.handler_unblock_by_func(self._on_text_change)
        self._tag_e.set_text(", ".join(n.get("tags",[])))
        GLib.idle_add(self._tv.grab_focus)
        self._hdr_da.queue_draw(); self._stat_da.queue_draw()
        self._list_da.queue_draw()

    def _new_note(self):
        n={"id":str(uuid.uuid4()),"title":"New Note","text":"",
           "created":datetime.now().isoformat()[:19],"modified":datetime.now().isoformat()[:19],
           "pinned":False,"tags":[],"color":TAG_COLORS[len(self._notes)%len(TAG_COLORS)],"wordcount":0}
        self._notes.insert(0,n); self._sel_id=n["id"]
        self._save_notes(); self._refresh_list(); self._load_into_editor()

    def _delete_note(self):
        if not self._sel_id: return
        self._notes=[x for x in self._notes if x["id"]!=self._sel_id]
        self._sel_id=self._notes[0]["id"] if self._notes else None
        self._save_notes(); self._refresh_list(); self._load_into_editor()

    def _toggle_pin(self):
        n=self._cur_note()
        if n: n["pinned"]=not n.get("pinned",False); self._save_notes(); self._refresh_list()

    def _export_note(self):
        n=self._cur_note()
        if not n: return
        fname=re.sub(r'[^a-zA-Z0-9_-]','_',n.get("title","note"))[:30]
        path=os.path.join(EXPORT_DIR,f"{fname}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md")
        with open(path,"w") as f:
            f.write(f"# {n['title']}\n\n")
            if n.get("tags"): f.write(f"**Tags:** {', '.join(n['tags'])}\n\n")
            f.write(f"*Created: {n.get('created','')}*  \n*Modified: {n.get('modified','')}*\n\n---\n\n")
            f.write(n.get("text",""))
        dlg=Gtk.MessageDialog(transient_for=self.win,modal=True,
            message_type=Gtk.MessageType.INFO,buttons=Gtk.ButtonsType.OK,
            text="Note Exported")
        dlg.format_secondary_text(f"Saved to: {path}")
        dlg.connect("response",lambda d,_:d.destroy()); dlg.present()

    def _set_sort(self,key):
        self._sort=key
        for k,b in self._sort_btns.items():
            b.remove_css_class("sort-active")
            if k==key: b.add_css_class("sort-active")
        self._refresh_list()

    def _filtered_sorted_notes(self):
        notes=list(self._notes)
        if self._filter_q:
            notes=[n for n in notes if self._filter_q in n.get("title","").lower()
                   or self._filter_q in n.get("text","").lower()
                   or any(self._filter_q in t.lower() for t in n.get("tags",[]))]
        # Pinned always first
        pinned=[n for n in notes if n.get("pinned")]
        unpinned=[n for n in notes if not n.get("pinned")]
        for lst in [pinned,unpinned]:
            if self._sort=="modified":
                lst.sort(key=lambda x:x.get("modified",""),reverse=True)
            elif self._sort=="title":
                lst.sort(key=lambda x:x.get("title","").lower())
            elif self._sort=="wordcount":
                lst.sort(key=lambda x:x.get("wordcount",0),reverse=True)
        return pinned+unpinned

    def _refresh_list(self):
        h=max(400,len(self._notes)*68+4)
        self._list_da.set_size_request(260,h); self._list_da.queue_draw()
        self._hdr_da.queue_draw()

    def _cur_note(self):
        if not self._sel_id: return None
        return next((n for n in self._notes if n["id"]==self._sel_id),None)

    def _cur_words(self):
        n=self._cur_note(); return len(n.get("text","").split()) if n else 0

    def _cur_read_time(self):
        n=self._cur_note()
        if not n: return "--"
        w=len(n.get("text","").split()); return f"~{max(1,round(w/200))} MIN READ"

    def _autosave(self):
        self._save_notes(); return GLib.SOURCE_CONTINUE


if __name__=="__main__":
    NyxusNotepad().run(None)
