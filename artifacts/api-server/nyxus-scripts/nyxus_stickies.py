#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Stickies — Cairo board · Drag-to-move · Full rainbow palette  ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
import json, uuid, os, math, random
from datetime import datetime

DATA_FILE = os.path.expanduser("~/.nyxus/stickies.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

PALETTE = ["#ff00ff","#cc00ff","#0088ff","#39ff14","#ffff00","#ff5500"]
NOTE_W, NOTE_H = 220, 168
PAD = 24

def hex_rgb(h):
    h=h.lstrip('#'); return int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255

COLORS_RGB = [hex_rgb(c) for c in PALETTE]

def wrap_text(cr, text, max_w, size=10):
    cr.set_font_size(size)
    if not text: return []
    lines=[]; cur=""
    for word in text.split(' '):
        test=(cur+' '+word).strip()
        try:
            if cr.text_extents(test).width>max_w and cur: lines.append(cur); cur=word
            else: cur=test
        except Exception: cur=test
    if cur: lines.append(cur)
    return lines

def glow_text(cr, x, y, text, r, g, b, size=12, bold=False):
    cr.select_font_face("JetBrains Mono",0,1 if bold else 0)
    cr.set_font_size(size)
    for dx,dy,a in [(-1,-1,.20),(1,-1,.20),(-1,1,.20),(1,1,.20),
                     (-2,0,.08),(2,0,.08),(0,-2,.08),(0,2,.08),
                     (-4,0,.04),(4,0,.04),(0,-4,.04),(0,4,.04)]:
        cr.set_source_rgba(r,g,b,a); cr.move_to(x+dx,y+dy); cr.show_text(text)
    cr.set_source_rgba(r,g,b,1.0); cr.move_to(x,y); cr.show_text(text)

def rainbow_bar(cr, x, y, w, h=2):
    seg=w/len(PALETTE)
    for i,c in enumerate(PALETTE):
        r,g,b=hex_rgb(c); cr.set_source_rgba(r,g,b,0.88)
        cr.rectangle(x+i*seg,y,seg,h); cr.fill()

def dot_grid(cr, x, y, w, h, col_idx=None):
    for i,gx in enumerate(range(int(x),int(x+w)+22,22)):
        for j,gy in enumerate(range(int(y),int(y+h)+22,22)):
            if col_idx is None:
                r,g,b=hex_rgb(PALETTE[(i+j)%len(PALETTE)])
                cr.set_source_rgba(r,g,b,0.06)
            else:
                r,g,b=COLORS_RGB[col_idx%len(COLORS_RGB)]
                cr.set_source_rgba(r,g,b,0.08)
            cr.arc(gx,gy,0.9,0,math.pi*2); cr.fill()


CSS = b"""
* { font-family: 'JetBrains Mono', 'Monospace', monospace; }
window { background-color: #030206; color: #e8e0f5; }
.hdr {
    background-color: rgba(4,2,10,0.97);
    border-bottom: 1px solid rgba(255,0,255,0.22);
    padding: 5px 14px; min-height: 48px;
}
.hdr-title { color: #ff00ff; font-size: 14px; font-weight: bold; letter-spacing: 4px; }
.add-btn {
    background-color: rgba(255,0,255,0.10); color: #ff00ff;
    border: 1px solid rgba(255,0,255,0.50); border-radius: 2px;
    padding: 5px 16px; font-size: 11px; font-weight: bold;
}
.add-btn:hover { background-color: rgba(255,0,255,0.25); }
.search-e {
    background-color: rgba(7,3,15,0.85); color: #e8e0f5;
    border: 1px solid rgba(204,0,255,0.35); border-radius: 2px;
    padding: 4px 10px; font-size: 10px; box-shadow: none; caret-color: #cc00ff;
    min-width: 200px;
}
.search-e text { background-color: transparent; }
.note-title-e {
    background-color: transparent; color: #e8e0f5;
    border: none; border-bottom: 1px solid rgba(255,255,255,0.15);
    border-radius: 0; padding: 4px 8px; font-size: 11px; font-weight: bold;
    box-shadow: none; caret-color: #ff00ff;
}
.note-title-e text { background-color: transparent; color: #e8e0f5; }
.note-body-e {
    background-color: transparent; color: #e8e0f5;
    border: none; padding: 6px 8px; font-size: 11px;
    caret-color: #ff00ff;
}
.note-body-e text { background-color: transparent; color: #e8e0f5; }
"""


class NyxusStickies(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.stickies")
        self._notes=[]; self._drag_id=None; self._drag_ox=0; self._drag_oy=0
        self._drag_nx=0; self._drag_ny=0; self._search=""
        self._load()

    def _load(self):
        try:
            with open(DATA_FILE) as f: self._notes=json.load(f)
            for n in self._notes:
                if "x" not in n: n["x"]=random.randint(PAD,600)
                if "y" not in n: n["y"]=random.randint(PAD,400)
                if "rotation" not in n: n["rotation"]=random.uniform(-4,4)
                if "pinned" not in n: n["pinned"]=False
        except Exception: self._notes=[]

    def _save(self):
        try:
            with open(DATA_FILE,"w") as f: json.dump(self._notes,f,indent=2)
        except Exception: pass

    def do_activate(self):
        prov=Gtk.CssProvider(); prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),prov,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.win=Gtk.ApplicationWindow(application=self,title="NYXUS Stickies")
        self.win.set_default_size(1200,800)

        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)

        # Header
        hdr=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        hdr.add_css_class("hdr")
        title=Gtk.Label(label="NYXUS_STICKIES"); title.add_css_class("hdr-title")
        title.set_halign(Gtk.Align.START); title.set_hexpand(True)
        hdr.append(title)

        self._search_e=Gtk.Entry(); self._search_e.add_css_class("search-e")
        self._search_e.set_placeholder_text("SEARCH NOTES...")
        self._search_e.connect("changed",lambda e:setattr(self,'_search',e.get_text().lower()) or self._board.queue_draw())
        hdr.append(self._search_e)

        # Color swatches
        for i,col in enumerate(PALETTE):
            swatch=self._make_swatch(col,i); hdr.append(swatch)

        add=Gtk.Button(label="+ NEW NOTE"); add.add_css_class("add-btn")
        add.connect("clicked",self._add_note); hdr.append(add)

        hdr_da=Gtk.DrawingArea(); hdr_da.set_size_request(-1,48)
        hdr_da.set_draw_func(self._draw_hdr,None)

        root.append(hdr)

        # Board
        sc=Gtk.ScrolledWindow(); sc.set_vexpand(True)
        sc.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC)
        self._board=Gtk.DrawingArea(); self._board.set_size_request(1600,1100)
        self._board.set_draw_func(self._draw_board,None)

        # Drag gesture
        drag=Gtk.GestureDrag()
        drag.connect("drag-begin",  self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end",    self._drag_end)
        self._board.add_controller(drag)

        # Double-click for edit
        click=Gtk.GestureClick(); click.set_button(0)
        click.connect("pressed",self._on_click)
        self._board.add_controller(click)

        sc.set_child(self._board); root.append(sc)

        # Status bar
        self._stat=Gtk.DrawingArea(); self._stat.set_size_request(-1,24)
        self._stat.set_draw_func(self._draw_stat,None)
        root.append(self._stat)

        GLib.timeout_add(5000,lambda:(self._save(),GLib.SOURCE_CONTINUE)[1])
        self.win.present()

    def _make_swatch(self,col,idx):
        r,g,b=hex_rgb(col)
        da=Gtk.DrawingArea(); da.set_size_request(24,24)
        da.set_draw_func(lambda area,cr,w,h,c=(r,g,b):(
            cr.set_source_rgba(*c,0.85),cr.arc(w/2,h/2,9,0,math.pi*2),cr.fill(),
            cr.set_source_rgba(*c,1.0),cr.set_line_width(1.5),cr.arc(w/2,h/2,9,0,math.pi*2),cr.stroke()
        )[0],None)
        click=Gtk.GestureClick()
        click.connect("pressed",lambda *_,c=col:self._add_note_color(c))
        da.add_controller(click); return da

    # ── Drawing ──────────────────────────────────────────────────────────────────
    def _draw_hdr(self,area,cr,w,h,_):
        rainbow_bar(cr,0,h-2,w,2)

    def _draw_board(self,area,cr,w,h,_):
        # Deep space background
        cr.set_source_rgb(0.012,0.008,0.024); cr.rectangle(0,0,w,h); cr.fill()
        # Multi-color dot grid (rainbow dots)
        dot_grid(cr,0,0,w,h)

        # Subtle grid lines for reference
        cr.set_source_rgba(0.18,0.07,0.36,0.04); cr.set_line_width(1)
        for gx in range(0,w,80):
            cr.move_to(gx,0); cr.line_to(gx,h); cr.stroke()
        for gy in range(0,h,80):
            cr.move_to(0,gy); cr.line_to(w,gy); cr.stroke()

        q=self._search
        visible=[n for n in self._notes if not q or q in n.get("title","").lower() or q in n.get("text","").lower()]
        hidden_count=len(self._notes)-len(visible)
        # Draw non-dragged first, then dragged on top
        for n in visible:
            if n["id"]!=self._drag_id: self._draw_note(cr,n)
        for n in visible:
            if n["id"]==self._drag_id: self._draw_note(cr,n,dragging=True)

        # If searching, show faded hidden notes
        if hidden_count>0:
            cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(10)
            cr.set_source_rgba(0.44,0.376,0.627,0.5)
            cr.move_to(w-200,h-16); cr.show_text(f"+{hidden_count} HIDDEN BY SEARCH")

    def _draw_note(self, cr, n, dragging=False):
        r,g,b=hex_rgb(n.get("color","#cc00ff"))
        rot=math.radians(n.get("rotation",0))
        nx=n["x"]; ny=n["y"]
        if dragging:
            nx=self._drag_nx; ny=self._drag_ny
            cr.set_source_rgba(r,g,b,0.35); cr.set_line_width(4)  # Drop shadow hint
            cr.rectangle(nx-NOTE_W//2+6,ny-NOTE_H//2+8,NOTE_W,NOTE_H); cr.fill()

        cr.save()
        cr.translate(nx,ny); cr.rotate(rot)
        hw,hh=NOTE_W//2,NOTE_H//2

        # Card background with tint
        cr.set_source_rgba(0.02,0.01,0.05,0.96); cr.rectangle(-hw,-hh,NOTE_W,NOTE_H); cr.fill()

        # Colored tint
        cr.set_source_rgba(r,g,b,0.09); cr.rectangle(-hw,-hh,NOTE_W,NOTE_H); cr.fill()

        # Dot grid inside the note (uses note's color)
        idx=PALETTE.index(n.get("color","#cc00ff")) if n.get("color") in PALETTE else 1
        cr.save()
        cr.rectangle(-hw,-hh,NOTE_W,NOTE_H); cr.clip()
        dot_grid(cr,-hw,-hh,NOTE_W,NOTE_H,idx)
        cr.restore()

        # Glow border layers
        for lw,a in [(14,0.08),(7,0.20),(2,0.90)]:
            cr.set_source_rgba(r,g,b,a); cr.set_line_width(lw)
            cr.rectangle(-hw,-hh,NOTE_W,NOTE_H); cr.stroke()

        # Top color bar
        cr.set_source_rgba(r,g,b,0.55); cr.rectangle(-hw,-hh,NOTE_W,6); cr.fill()

        # Rainbow corner dots
        for cx2,cy2,ci in [(-hw+6,-hh+14,0),(hw-6,-hh+14,3),(-hw+6,hh-6,1),(hw-6,hh-6,4)]:
            cr.set_source_rgba(*hex_rgb(PALETTE[ci]),0.7); cr.arc(cx2,cy2,3,0,math.pi*2); cr.fill()

        # Pin indicator
        if n.get("pinned"):
            cr.set_source_rgba(1,1,0,0.9); cr.arc(hw-10,-hh+14,4,0,math.pi*2); cr.fill()

        # Title
        cr.select_font_face("JetBrains Mono",0,1); cr.set_font_size(10)
        title=n.get("title","Untitled")[:24]
        cr.set_source_rgba(*hex_rgb(n.get("color","#cc00ff")),0.9)
        glow_text(cr,-hw+8,-hh+22,title,r,g,b,size=10,bold=True)

        # Date
        mod=n.get("modified","")[:10]
        cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(7)
        cr.set_source_rgba(r,g,b,0.40); ext=cr.text_extents(mod)
        cr.move_to(hw-ext.width-6,-hh+22); cr.show_text(mod)

        # Separator
        cr.set_source_rgba(r,g,b,0.25); cr.set_line_width(1)
        cr.move_to(-hw+6,-hh+28); cr.line_to(hw-6,-hh+28); cr.stroke()

        # Body text
        txt=n.get("text","")
        lines=wrap_text(cr,txt,NOTE_W-20,size=9)
        cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
        cr.set_source_rgba(0.91,0.88,0.96,0.85)
        ty=-hh+42
        for line in lines[:8]:
            if ty>hh-12: break
            cr.move_to(-hw+8,ty); cr.show_text(line); ty+=13

        # Word count
        wc=len(txt.split()); wc_txt=f"{wc}W"
        cr.set_font_size(7); cr.set_source_rgba(r,g,b,0.35)
        cr.move_to(-hw+8,hh-6); cr.show_text(wc_txt)

        cr.restore()

    def _draw_stat(self, area, cr, w, h, _):
        cr.set_source_rgb(0.012,0.006,0.025); cr.rectangle(0,0,w,h); cr.fill()
        rainbow_bar(cr,0,0,w,2)
        cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
        parts=[
            (f"NOTES: {len(self._notes)}", (1,0,1)),
            ("  ·  ", (0.44,0.376,0.627)),
            ("DRAG TO MOVE",  (0.22,1,0.08)),
            ("  ·  ", (0.44,0.376,0.627)),
            ("DOUBLE-CLICK TO EDIT", (0,0.53,1)),
            ("  ·  ", (0.44,0.376,0.627)),
            ("CLICK SWATCH TO SET COLOR", (1,1,0)),
        ]
        xp=10
        for txt,col in parts:
            cr.set_source_rgba(*col,0.80); cr.move_to(xp,h-5); cr.show_text(txt)
            xp+=cr.text_extents(txt).width

    # ── Interaction ──────────────────────────────────────────────────────────────
    def _hit_note(self,x,y,notes=None):
        if notes is None: notes=self._notes
        for n in reversed(notes):
            nx,ny=n["x"],n["y"]
            if abs(x-nx)<NOTE_W//2+6 and abs(y-ny)<NOTE_H//2+6: return n
        return None

    def _drag_begin(self,gesture,sx,sy):
        n=self._hit_note(sx,sy)
        if n: self._drag_id=n["id"]; self._drag_ox=sx-n["x"]; self._drag_oy=sy-n["y"]
        else: self._drag_id=None

    def _drag_update(self,gesture,ox,oy):
        if not self._drag_id: return
        sx,sy=gesture.get_start_point()[1],gesture.get_start_point()[2]
        self._drag_nx=sx+ox-self._drag_ox; self._drag_ny=sy+oy-self._drag_oy
        self._board.queue_draw()

    def _drag_end(self,gesture,ox,oy):
        if not self._drag_id: return
        n=next((x for x in self._notes if x["id"]==self._drag_id),None)
        if n:
            n["x"]=self._drag_nx; n["y"]=self._drag_ny
            n["x"]=max(NOTE_W//2,min(1560,n["x"]))
            n["y"]=max(NOTE_H//2,min(1060,n["y"]))
        self._drag_id=None; self._save(); self._board.queue_draw()

    def _on_click(self,gesture,n_press,x,y):
        n=self._hit_note(x,y)
        if not n: return
        if n_press==2: self._open_editor(n)  # double-click
        elif n_press==3: self._toggle_pin(n)  # triple-click = pin

    def _toggle_pin(self,n):
        n["pinned"]=not n.get("pinned",False); self._save(); self._board.queue_draw()

    # ── Editor dialog ─────────────────────────────────────────────────────────
    def _open_editor(self,n):
        r,g,b=hex_rgb(n.get("color","#cc00ff"))
        dlg=Gtk.Dialog(transient_for=self.win,modal=True)
        dlg.set_title("EDIT NOTE"); dlg.set_default_size(480,520)

        content=dlg.get_content_area()
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=4)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_margin_start(8); box.set_margin_end(8)
        content.append(box)

        # Color bar at top
        da=Gtk.DrawingArea(); da.set_size_request(-1,8)
        da.set_draw_func(lambda a,cr,w,h,c=(r,g,b):(
            cr.set_source_rgba(*c,0.9),cr.rectangle(0,0,w,h),cr.fill()
        )[0],None); box.append(da)

        # Title
        title_e=Gtk.Entry(); title_e.add_css_class("note-title-e")
        title_e.set_text(n.get("title",""))
        title_e.set_placeholder_text("NOTE TITLE..."); box.append(title_e)

        # Color row
        crow=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        crow.set_margin_top(4); crow.set_margin_bottom(4)
        clbl=Gtk.Label(label="COLOR:"); clbl.set_markup('<span font="9" foreground="#cc00ff" weight="bold">COLOR: </span>')
        crow.append(clbl)
        for ci,hexcol in enumerate(PALETTE):
            cr2,cg2,cb2=hex_rgb(hexcol)
            dot=Gtk.DrawingArea(); dot.set_size_request(22,22)
            sel=(hexcol==n.get("color","#cc00ff"))
            dot.set_draw_func(lambda a,cr,w,h,c=(cr2,cg2,cb2),s=sel:(
                cr.set_source_rgba(*c,0.9),cr.arc(w/2,h/2,8,0,math.pi*2),cr.fill(),
                cr.set_source_rgba(1,1,1,0.8 if s else 0),cr.set_line_width(2),cr.arc(w/2,h/2,9,0,math.pi*2),cr.stroke()
            )[0],None)
            clk=Gtk.GestureClick(); clk.connect("pressed",lambda *_,hc=hexcol,ne=n,d=dlg,te=title_e:
                (setattr(ne,'__dict__',{**ne,'color':hc}),ne.update({'color':hc}),
                 self._save(),self._board.queue_draw())[0])
            dot.add_controller(clk); crow.append(dot)
        box.append(crow)

        # Tags
        tag_row=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=4)
        tlbl=Gtk.Label(); tlbl.set_markup('<span font="9" foreground="#ffff00" weight="bold">TAGS: </span>')
        tag_row.append(tlbl)
        tag_e=Gtk.Entry(); tag_e.add_css_class("tag-e") if hasattr(tag_e,'add_css_class') else None
        tag_e.set_text(", ".join(n.get("tags",[])))
        tag_e.set_placeholder_text("tag1, tag2, tag3"); tag_e.set_hexpand(True)
        tag_row.append(tag_e); box.append(tag_row)

        # Body
        buf=Gtk.TextBuffer(); buf.set_text(n.get("text",""))
        tv=Gtk.TextView(buffer=buf); tv.set_wrap_mode(Gtk.WrapMode.WORD)
        tv.add_css_class("note-body-e")
        sc=Gtk.ScrolledWindow(); sc.set_vexpand(True); sc.set_child(tv); box.append(sc)

        # Buttons
        btnbox=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=6)
        save_b=Gtk.Button(label="SAVE"); save_b.add_css_class("add-btn")
        del_b=Gtk.Button(label="DELETE"); del_b.add_css_class("del-btn")
        pin_b=Gtk.Button(label="📌 PIN" if not n.get("pinned") else "📌 UNPIN"); pin_b.add_css_class("pin-btn")
        tilt_b=Gtk.Button(label="↻ TILT"); tilt_b.connect("clicked",lambda *_,ne=n:(
            ne.update({"rotation":random.uniform(-6,6)}),
            self._save(),self._board.queue_draw()))

        def _save_edit(*_):
            n["title"]=title_e.get_text() or "Untitled"
            n["text"]=buf.get_text(buf.get_start_iter(),buf.get_end_iter(),False)
            n["modified"]=datetime.now().isoformat()[:19]
            raw=tag_e.get_text().strip()
            n["tags"]=[t.strip() for t in raw.split(",") if t.strip()][:5]
            self._save(); self._board.queue_draw(); dlg.destroy()

        def _delete_note(*_):
            self._notes=[x for x in self._notes if x["id"]!=n["id"]]
            self._save(); self._board.queue_draw(); dlg.destroy()

        def _pin_note(*_):
            n["pinned"]=not n.get("pinned",False)
            self._save(); self._board.queue_draw()

        save_b.connect("clicked",_save_edit)
        del_b.connect("clicked",_delete_note)
        pin_b.connect("clicked",_pin_note)
        btnbox.append(save_b); btnbox.append(pin_b); btnbox.append(tilt_b)
        btnbox.set_hexpand(True)
        del_b.set_halign(Gtk.Align.END); btnbox.append(del_b)
        box.append(btnbox)

        GLib.idle_add(tv.grab_focus); dlg.present()

    # ── Add notes ────────────────────────────────────────────────────────────────
    def _add_note(self,*_):
        self._add_note_color(PALETTE[len(self._notes)%len(PALETTE)])

    def _add_note_color(self,col):
        W=self._board.get_width() or 900; H=self._board.get_height() or 700
        n={"id":str(uuid.uuid4()),"title":"New Note","text":"",
           "color":col,"rotation":random.uniform(-5,5),
           "x":random.randint(NOTE_W//2+PAD,max(NOTE_W,W-NOTE_W//2-PAD)),
           "y":random.randint(NOTE_H//2+PAD,max(NOTE_H,H-NOTE_H//2-PAD)),
           "created":datetime.now().isoformat()[:19],
           "modified":datetime.now().isoformat()[:19],
           "pinned":False,"tags":[]}
        self._notes.append(n); self._save(); self._board.queue_draw()
        GLib.idle_add(lambda:self._open_editor(n))


class pin_btn(Gtk.Button): pass  # stub for CSS

if __name__=="__main__":
    NyxusStickies().run(None)
