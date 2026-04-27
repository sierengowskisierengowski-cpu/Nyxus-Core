#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Notepad — Enterprise · 3-panel · Markdown · Tags · Export     ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Pango
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

def glow_text(cr, x, y, txt, r, g, b, size=12, bold=False):
    cr.select_font_face("JetBrains Mono", 0, 1 if bold else 0)
    cr.set_font_size(size)
    for dx, dy, a in [(-1,-1,.20),(1,-1,.20),(-1,1,.20),(1,1,.20),
                       (-2,0,.08),(2,0,.08),(0,-2,.08),(0,2,.08)]:
        cr.set_source_rgba(r, g, b, a); cr.move_to(x+dx, y+dy); cr.show_text(txt)
    cr.set_source_rgba(r, g, b, 1.0); cr.move_to(x, y); cr.show_text(txt)

def rainbow_bar(cr, x, y, w, h=2):
    seg = w / len(PALETTE)
    for i,(r,g,b) in enumerate(PALETTE):
        cr.set_source_rgba(r,g,b,0.88); cr.rectangle(x+i*seg,y,seg,h); cr.fill()

def dot_grid(cr, x, y, w, h):
    cr.set_source_rgba(0.28, 0.07, 0.50, 0.09)
    for gx in range(int(x),int(x+w)+22,22):
        for gy in range(int(y),int(y+h)+22,22):
            cr.arc(gx,gy,0.9,0,math.pi*2); cr.fill()

def hex_to_rgb(h):
    h=h.lstrip('#'); return int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255

def reading_time(text):
    words=len(text.split()); mins=max(1,round(words/200))
    return f"{mins} MIN READ · {words} WORDS"


CSS = b"""
* { font-family: 'JetBrains Mono', 'Monospace', monospace; }
window { background-color: #030206; color: #e8e0f5; }

.hdr {
    background-color: rgba(4,2,10,0.97);
    border-bottom: 1px solid rgba(255,0,255,0.22);
    padding: 5px 12px; min-height: 46px;
}
.hdr-title { color: #ff00ff; font-size: 14px; font-weight: bold; letter-spacing: 4px; }
.hdr-badge {
    color: #0088ff; font-size: 9px;
    border: 1px solid rgba(0,136,255,0.40);
    padding: 2px 8px; border-radius: 2px; margin-left: 6px;
}
.hdr-badge-green { color: #39ff14; border-color: rgba(57,255,20,0.40); }
.hdr-badge-yellow { color: #ffff00; border-color: rgba(255,255,0,0.40); }
.hdr-badge-orange { color: #ff5500; border-color: rgba(255,85,0,0.40); }
.hdr-badge-purple { color: #cc00ff; border-color: rgba(204,0,255,0.40); }

.sidebar { background-color: rgba(7,3,15,0.97); border-right: 1px solid rgba(204,0,255,0.18); }
.sidebar-hdr {
    color: #cc00ff; font-size: 9px; font-weight: bold;
    letter-spacing: 3px; padding: 6px 10px 4px 10px;
    border-bottom: 1px solid rgba(204,0,255,0.15);
}
.new-btn {
    background-color: rgba(255,0,255,0.08); color: #ff00ff;
    border: 1px solid rgba(255,0,255,0.40); border-radius: 2px;
    padding: 4px 14px; font-size: 10px; font-weight: bold; margin: 4px;
}
.new-btn:hover { background-color: rgba(255,0,255,0.22); }
.del-btn {
    background-color: rgba(255,85,0,0.06); color: #ff5500;
    border: 1px solid rgba(255,85,0,0.35); border-radius: 2px;
    padding: 4px 8px; font-size: 10px; font-weight: bold; margin: 4px 2px;
}
.del-btn:hover { background-color: rgba(255,85,0,0.20); }
.exp-btn {
    background-color: rgba(57,255,20,0.06); color: #39ff14;
    border: 1px solid rgba(57,255,20,0.35); border-radius: 2px;
    padding: 4px 8px; font-size: 10px; font-weight: bold; margin: 4px 2px;
}
.exp-btn:hover { background-color: rgba(57,255,20,0.18); }
.pin-btn {
    background-color: rgba(255,255,0,0.06); color: #ffff00;
    border: 1px solid rgba(255,255,0,0.35); border-radius: 2px;
    padding: 4px 8px; font-size: 10px; font-weight: bold; margin: 4px 2px;
}
.sort-btn {
    background-color: transparent; color: rgba(112,96,160,0.8);
    border: 1px solid rgba(112,96,160,0.25); border-radius: 2px;
    padding: 3px 6px; font-size: 8px; margin: 2px 1px;
}
.sort-btn:hover { color: #cc00ff; border-color: rgba(204,0,255,0.5); }
.sort-active { color: #cc00ff; border-color: rgba(204,0,255,0.7);
               background-color: rgba(204,0,255,0.08); }
.search-e {
    background-color: rgba(7,3,15,0.80); color: #e8e0f5;
    border: 1px solid rgba(204,0,255,0.30); border-radius: 2px;
    padding: 5px 10px; font-size: 10px; box-shadow: none;
    caret-color: #cc00ff; margin: 4px;
}
.search-e text { background-color: transparent; }
.tag-e {
    background-color: rgba(7,3,15,0.80); color: #ffff00;
    border: 1px solid rgba(255,255,0,0.30); border-radius: 2px;
    padding: 4px 8px; font-size: 9px; box-shadow: none;
    caret-color: #ffff00; margin: 0 4px;
}
.tag-e text { background-color: transparent; }
.editor-area {
    background-color: rgba(4,2,12,0.90); color: #e8e0f5;
    border: none; padding: 12px; font-size: 12px;
    caret-color: #ff00ff;
}
.editor-area text { background-color: transparent; color: #e8e0f5; }
.editor-area text selection { background-color: rgba(255,0,255,0.25); }
.clip-hdr {
    color: #0088ff; font-size: 9px; font-weight: bold;
    letter-spacing: 3px; padding: 6px 10px 4px 10px;
    border-bottom: 1px solid rgba(0,136,255,0.15);
}
.clip-btn {
    background-color: transparent; color: #e8e0f5;
    border: none; border-bottom: 1px solid rgba(0,136,255,0.10);
    border-radius: 0; padding: 5px 8px; font-size: 9px; text-align: left;
    min-height: 0;
}
.clip-btn:hover { background-color: rgba(0,136,255,0.08); color: #0088ff; }
.title-e {
    background-color: transparent; color: #ff00ff;
    border: none; border-bottom: 1px solid rgba(255,0,255,0.25);
    border-radius: 0; padding: 6px 12px; font-size: 14px; font-weight: bold;
    letter-spacing: 2px; box-shadow: none; caret-color: #ff00ff;
}
.title-e text { background-color: transparent; color: #ff00ff; }
"""


class NyxusNotepad(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.notepad")
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
        prov = Gtk.CssProvider(); prov.load_from_data(CSS)
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
        cr.set_source_rgb(0.016, 0.008, 0.035); cr.rectangle(0,0,w,h); cr.fill()
        dot_grid(cr, 0, 0, w, 50)
        glow_text(cr, 14, h-12, "NYXUS_NOTEPAD", *C_PINK, size=15, bold=True)
        n = len(self._notes)
        cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
        items = [
            (f"  {n} NOTES", C_BLUE),
            (f"  ·  {len(self._clipboard_history)} CLIPS", C_GREEN),
            (f"  ·  {self._cur_words()} WORDS", C_YELLOW),
            (f"  ·  {self._cur_read_time()}", C_PURPLE),
        ]
        xp = 200
        for txt, col in items:
            cr.set_source_rgba(*col, 0.85); cr.move_to(xp, h-12); cr.show_text(txt)
            xp += cr.text_extents(txt).width + 4
        rainbow_bar(cr, 0, h-2, w, 2)

    def _draw_stat(self, area, cr, w, h, _):
        cr.set_source_rgb(0.012,0.006,0.025); cr.rectangle(0,0,w,h); cr.fill()
        rainbow_bar(cr, 0, 0, w, 2)
        note = self._cur_note()
        if note:
            txt = note.get("text","")
            chars = len(txt); words = len(txt.split()) if txt.strip() else 0
            sents = txt.count('.')+txt.count('!')+txt.count('?')
            parts = [
                (f"CHARS: {chars}",  C_PINK),
                ("  ·  ",            C_DIM),
                (f"WORDS: {words}",  C_PURPLE),
                ("  ·  ",            C_DIM),
                (f"SENTENCES: {sents}", C_BLUE),
                ("  ·  ",            C_DIM),
                (f"{self._cur_read_time()}", C_GREEN),
                ("  ·  ",            C_DIM),
                (f"TAGS: {', '.join(note.get('tags',[])) or 'none'}", C_YELLOW),
            ]
            xp = 10
            cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
            for txt2,col in parts:
                cr.set_source_rgba(*col, 0.85); cr.move_to(xp, h-6); cr.show_text(txt2)
                xp += cr.text_extents(txt2).width
            mod = note.get("modified","")[:16]
            cr.set_source_rgba(*C_DIM, 0.6)
            ext = cr.text_extents(f"MOD: {mod}")
            cr.move_to(w-ext.width-12, h-6); cr.show_text(f"MOD: {mod}")

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
        cr.set_source_rgb(0.012,0.006,0.025); cr.rectangle(0,0,w,h); cr.fill()
        cr.set_source_rgba(*C_BLUE,0.18); cr.set_line_width(1)
        cr.move_to(0,h-1); cr.line_to(w,h-1); cr.stroke()
        glow_text(cr,10,h-8,"CLIPBOARD HISTORY",*C_BLUE,size=9,bold=True)

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
