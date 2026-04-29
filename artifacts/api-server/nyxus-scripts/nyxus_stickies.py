#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Stickies — Hand-drawn · Real sticky notes on cork board       ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
import json, uuid, os, math, random as _rand
from datetime import datetime

DATA_FILE = os.path.expanduser("~/.nyxus/stickies.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# Sticky note card colors (dark neon)
NOTE_PAPER = [
    (0.10, 0.02, 0.10),   # dark magenta card
    (0.07, 0.02, 0.14),   # dark purple card
    (0.02, 0.06, 0.14),   # dark blue card
    (0.02, 0.10, 0.02),   # dark green card
    (0.10, 0.10, 0.02),   # dark yellow card
    (0.12, 0.04, 0.02),   # dark orange card
]
# Neon marker ink colors (borders, text, accents)
NOTE_INK = [
    (1.00, 0.00, 1.00),   # neon magenta/pink
    (0.80, 0.00, 1.00),   # neon purple
    (0.00, 0.53, 1.00),   # neon blue
    (0.22, 1.00, 0.08),   # neon green
    (1.00, 1.00, 0.00),   # neon yellow
    (1.00, 0.33, 0.00),   # neon orange
]
PALETTE_HEX = ["#ff00ff","#cc00ff","#0088ff","#39ff14","#ffff00","#ff5500"]
NOTE_W, NOTE_H = 230, 175
PAD = 26


# ── Sketch / paper helpers ──────────────────────────────────────────────────

def _rng(x, y, w=0, h=0):
    return _rand.Random(int(x*3 + y*7 + (w or 1)*11 + (h or 1)*13) % 65535)

def sketch_rect(cr, x, y, w, h, r, g, b, thick=2.2, jitter=2.8, fill_rgba=None):
    rng = _rng(x, y, w, h); j = lambda s=1.0: rng.uniform(-jitter*s, jitter*s)
    def _path():
        cr.move_to(x+j(.5),  y+j(.5))
        cr.curve_to(x+w*.33+j(), y+j(),      x+w*.67+j(), y+j(),      x+w+j(.5), y+j(.5))
        cr.curve_to(x+w+j(),     y+h*.33+j(), x+w+j(),    y+h*.67+j(), x+w+j(.5), y+h+j(.5))
        cr.curve_to(x+w*.67+j(), y+h+j(),    x+w*.33+j(), y+h+j(),    x+j(.5),   y+h+j(.5))
        cr.curve_to(x+j(),       y+h*.67+j(), x+j(),      y+h*.33+j(), x+j(.5),   y+j(.5))
        cr.close_path()
    if fill_rgba:
        _path(); cr.set_source_rgba(*fill_rgba); cr.fill()
        rng2 = _rng(x, y, w, h); j = lambda s=1.0: rng2.uniform(-jitter*s, jitter*s)
    _path()
    cr.set_source_rgba(r, g, b, 0.88)
    cr.set_line_width(thick); cr.set_line_cap(1); cr.set_line_join(1)
    cr.stroke()

def paper_bg(cr, w, h):
    """Dark NYXUS background with subtle neon dot grid."""
    cr.set_source_rgb(0.031, 0.031, 0.055); cr.rectangle(0, 0, w, h); cr.fill()
    # Subtle dot grid
    spacing = 28
    cr.set_line_width(1.0)
    neons = [(1,0,1),(0.8,0,1),(0,0.53,1),(0.22,1,0.08),(1,1,0),(1,0.33,0)]
    rng = _rand.Random(99)
    for gx in range(spacing, int(w), spacing):
        for gy in range(spacing, int(h), spacing):
            nc = rng.choice(neons)
            cr.set_source_rgba(*nc, 0.08)
            cr.arc(gx, gy, 1.2, 0, math.pi*2); cr.fill()
    # Faint ambient splatter
    for _ in range(80):
        bx = rng.uniform(0, w); by = rng.uniform(0, h)
        br = rng.uniform(2, 14)
        nc = rng.choice(neons)
        cr.set_source_rgba(*nc, rng.uniform(0.02, 0.06))
        cr.arc(bx, by, br, 0, math.pi*2); cr.fill()

def handwriting(cr, x, y, txt, r, g, b, size=13, bold=False, alpha=0.90):
    cr.select_font_face("Caveat", 0, 1 if bold else 0)
    cr.set_font_size(size)
    cr.set_source_rgba(r, g, b, alpha*0.18)
    cr.move_to(x+1.0, y+0.7); cr.show_text(txt)
    cr.set_source_rgba(r, g, b, alpha)
    cr.move_to(x, y); cr.show_text(txt)

def wrap_text(cr, text, max_w, size=12):
    cr.select_font_face("Caveat", 0, 0); cr.set_font_size(size)
    if not text: return []
    lines=[]; cur=""
    for word in text.split(' '):
        test = (cur+' '+word).strip()
        if cr.text_extents(test).width > max_w and cur:
            lines.append(cur); cur = word
        else:
            cur = test
    if cur: lines.append(cur)
    return lines

def hex_rgb(h):
    h=h.lstrip('#'); return int(h[0:2],16)/255,int(h[2:4],16)/255,int(h[4:6],16)/255

def color_index(hex_color):
    try: return PALETTE_HEX.index(hex_color)
    except ValueError: return 0


# ── Draw a single sticky note ───────────────────────────────────────────────

def draw_sticky(cr, nx, ny, nw, nh, cidx, title, body, angle, selected=False):
    cidx = cidx % len(NOTE_PAPER)
    pr, pg, pb = NOTE_PAPER[cidx]
    ir, ig, ib = NOTE_INK[cidx]

    cr.save()
    cx, cy = nx+nw/2, ny+nh/2
    cr.translate(cx, cy); cr.rotate(math.radians(angle)); cr.translate(-nw/2, -nh/2)

    # Neon glow shadow
    for sh, sa in [(10, 0.08), (6, 0.12), (3, 0.16)]:
        cr.set_source_rgba(ir, ig, ib, sa)
        cr.rectangle(sh, sh+2, nw, nh); cr.fill()

    # Main paper body
    cr.set_source_rgb(pr, pg, pb)
    cr.rectangle(0, 0, nw, nh); cr.fill()

    # Glue strip at top (slightly darker, like the sticky adhesive band)
    cr.set_source_rgba(ir, ig, ib, 0.10)
    cr.rectangle(0, 0, nw, 32); cr.fill()
    cr.set_source_rgba(ir, ig, ib, 0.20)
    cr.rectangle(0, 30, nw, 2); cr.fill()

    # Ruled lines (like a real notepad)
    cr.set_line_width(0.55)
    for ly in range(48, int(nh)-6, 19):
        cr.set_source_rgba(ir, ig, ib, 0.12)
        cr.move_to(10, ly); cr.line_to(nw-10, ly); cr.stroke()

    # Wobbly border — hand-drawn feel
    sketch_rect(cr, 1, 1, nw-2, nh-2, ir, ig, ib, thick=2.0, jitter=2.2)

    # Selected highlight
    if selected:
        sketch_rect(cr, -3, -3, nw+6, nh+6, 0.08, 0.08, 0.80, thick=3.0, jitter=3.5)

    # Folded corner (bottom-right)
    corner = 18
    cr.set_source_rgba(ir*0.35, ig*0.35, ib*0.35, 0.95)
    cr.move_to(nw-corner, nh)
    cr.line_to(nw, nh-corner)
    cr.line_to(nw, nh)
    cr.close_path(); cr.fill()
    # Fold shadow line
    cr.set_source_rgba(ir, ig, ib, 0.35)
    cr.set_line_width(0.8)
    cr.move_to(nw-corner, nh); cr.line_to(nw, nh-corner); cr.stroke()

    # Pushpin / tack
    pin_r = 5
    cr.set_source_rgba(ir, ig, ib, 0.30)
    cr.arc(nw//2+1.5, pin_r+3.5, pin_r, 0, math.pi*2); cr.fill()
    cr.set_source_rgba(ir, ig, ib, 0.75)
    cr.arc(nw//2, pin_r+2, pin_r, 0, math.pi*2)
    cr.set_line_width(1.2); cr.stroke()
    cr.set_source_rgba(1.0, 0.96, 0.90, 0.80)
    cr.arc(nw//2-1.5, pin_r+1.5, 2.5, 0, math.pi*2); cr.fill()

    # Title in header
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(12)
    cr.set_source_rgba(ir, ig, ib, 0.82)
    t = (title or "Note")[:22]
    cr.move_to(10, 22); cr.show_text(t)

    # Body text
    cr.select_font_face("Caveat", 0, 0)
    cr.set_font_size(13)
    cr.set_source_rgba(ir, ig, ib, 0.80)
    lines = wrap_text(cr, body or "", nw-22)
    for i, line in enumerate(lines[:5]):
        cr.move_to(11, 50 + i*19); cr.show_text(line)
    if len(lines) > 5:
        cr.set_source_rgba(ir, ig, ib, 0.40)
        cr.set_font_size(10)
        cr.move_to(11, 50+5*19); cr.show_text(f"+ {len(lines)-5} more lines…")

    cr.restore()


# ── CSS — warm paper toolbar ────────────────────────────────────────────────

CSS = """
* { font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', 'Sans'; }
window { background-color: #08080e; color: rgba(232,224,245,0.92); }
.hdr {
    background-color: #0d0d1a;
    border-bottom: 2px solid rgba(255,0,255,0.18);
    padding: 6px 16px; min-height: 52px;
}
.hdr-title {
    color: #ff88ff;
    font-size: 20px; font-weight: bold; letter-spacing: 2px;
}
.add-btn {
    background-color: rgba(255,0,255,0.14); color: #ff88ff;
    border: 2px solid rgba(255,0,255,0.50); border-radius: 4px;
    padding: 6px 18px; font-size: 14px; font-weight: bold;
}
.add-btn:hover { background-color: rgba(255,0,255,0.30); }
.del-btn {
    background-color: rgba(255,50,30,0.16); color: #ff6655;
    border: 2px solid rgba(255,80,50,0.50); border-radius: 4px;
    padding: 6px 16px; font-size: 14px; font-weight: bold;
}
.del-btn:hover { background-color: rgba(255,80,50,0.30); }
.search-e {
    background-color: rgba(255,255,255,0.06);
    border: 2px solid rgba(255,0,255,0.30);
    color: rgba(232,224,245,0.88); border-radius: 4px;
    padding: 5px 12px; font-size: 13px; caret-color: #ff00ff;
}
.search-e text { background-color: transparent; }
.count-lbl { color: rgba(180,160,220,0.75); font-size: 12px; }
.col-btn {
    border-radius: 50%; min-width:22px; min-height:22px;
    padding:0; border: 2px solid rgba(255,255,255,0.20);
}
.col-btn:hover { border: 2px solid rgba(255,255,255,0.65); }
"""


# ── Data ────────────────────────────────────────────────────────────────────

def load_notes():
    try:
        with open(DATA_FILE) as f: return json.load(f)
    except Exception: return []

def save_notes(notes):
    try:
        with open(DATA_FILE,'w') as f: json.dump(notes, f, indent=2)
    except Exception: pass


# ── Main window ─────────────────────────────────────────────────────────────

class StickyApp(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NYXUS Stickies")
        self.set_default_size(1100, 720)
        self.notes = load_notes()
        self.selected = None
        self.drag_id = None
        self.drag_dx = self.drag_dy = 0
        self._build()

    def _build(self):
        css_p = Gtk.CssProvider()
        try: css_p.load_from_string(CSS)
        except AttributeError: css_p.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_p,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(box)

        # Header
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        hdr.add_css_class("hdr")
        title = Gtk.Label(label="📌  NYXUS STICKIES"); title.add_css_class("hdr-title")
        hdr.append(title)

        search = Gtk.Entry(); search.set_placeholder_text("search notes…")
        search.add_css_class("search-e"); search.set_hexpand(True)
        search.connect("changed", self._on_search); hdr.append(search)

        self.count_lbl = Gtk.Label(label=""); self.count_lbl.add_css_class("count-lbl")
        hdr.append(self.count_lbl)

        add_btn = Gtk.Button(label="+ New Note"); add_btn.add_css_class("add-btn")
        add_btn.connect("clicked", self._add_note); hdr.append(add_btn)

        del_btn = Gtk.Button(label="✕ Delete"); del_btn.add_css_class("del-btn")
        del_btn.connect("clicked", self._del_note); hdr.append(del_btn)

        # Color picker row
        hdr2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        hdr2.add_css_class("hdr"); hdr2.set_margin_top(0)
        for i, (pr, pg, pb) in enumerate(NOTE_PAPER):
            btn = Gtk.Button(); btn.add_css_class("col-btn")
            btn.set_size_request(22, 22)
            r16=int(pr*255); g16=int(pg*255); b16=int(pb*255)
            btn.get_style_context().add_provider(
                self._color_provider(f"button{{background-color:rgb({r16},{g16},{b16});}}"),
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            btn.connect("clicked", self._set_color, i); hdr2.append(btn)
        lbl = Gtk.Label(label="  Color:"); hdr2.prepend(lbl)
        box.append(hdr); box.append(hdr2)

        # Canvas
        self.da = Gtk.DrawingArea()
        self.da.set_hexpand(True); self.da.set_vexpand(True)
        self.da.set_draw_func(self._draw)
        box.append(self.da)

        # Gestures
        click = Gtk.GestureClick()
        click.connect("pressed", self._on_press)
        click.connect("released", self._on_release)
        self.da.add_controller(click)

        drag = Gtk.GestureDrag()
        drag.connect("drag-begin",  self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end",    self._drag_end)
        self.da.add_controller(drag)

        self._update_count()

    def _color_provider(self, css):
        p = Gtk.CssProvider(); p.load_from_data(css.encode()); return p

    def _update_count(self):
        n = len(self.notes)
        self.count_lbl.set_label(f"{n} note{'s' if n!=1 else ''}")

    def _add_note(self, *_):
        w,h = self.da.get_width(), self.da.get_height()
        rng = _rand.Random()
        next_color = len(self.notes) % len(NOTE_PAPER)
        self.notes.append({
            "id": str(uuid.uuid4()),
            "title": f"Note {len(self.notes)+1}",
            "body": "",
            "color": next_color,
            "x": max(20, min(w-NOTE_W-20, rng.randint(60, max(61,w-NOTE_W-60)))),
            "y": max(20, min(h-NOTE_H-20, rng.randint(60, max(61,h-NOTE_H-60)))),
            "angle": rng.uniform(-6, 6),
            "created": datetime.now().isoformat(),
        })
        self.selected = self.notes[-1]["id"]
        save_notes(self.notes); self._update_count(); self.da.queue_draw()

    def _del_note(self, *_):
        if not self.selected: return
        self.notes = [n for n in self.notes if n["id"] != self.selected]
        self.selected = None
        save_notes(self.notes); self._update_count(); self.da.queue_draw()

    def _set_color(self, btn, idx):
        if not self.selected: return
        for n in self.notes:
            if n["id"] == self.selected: n["color"] = idx
        save_notes(self.notes); self.da.queue_draw()

    def _on_search(self, entry, *_):
        self._filter = entry.get_text().lower()
        self.da.queue_draw()

    _filter = ""

    def _hit_test(self, mx, my):
        for n in reversed(self.notes):
            nx,ny = n["x"],n["y"]
            # Approx hit (ignore rotation for simplicity)
            if nx <= mx <= nx+NOTE_W and ny <= my <= ny+NOTE_H:
                return n
        return None

    def _on_press(self, gesture, npress, mx, my):
        n = self._hit_test(mx, my)
        if n:
            self.selected = n["id"]
            if npress == 2: self._edit_note(n)
        else:
            self.selected = None
        self.da.queue_draw()

    def _on_release(self, *_): pass

    def _drag_begin(self, gesture, x, y):
        n = self._hit_test(x, y)
        if n:
            self.drag_id = n["id"]
            self.drag_sx, self.drag_sy = n["x"], n["y"]
            self.drag_ox, self.drag_oy = x, y
            # Move to top
            self.notes.remove(n); self.notes.append(n)

    def _drag_update(self, gesture, dx, dy):
        if not self.drag_id: return
        for n in self.notes:
            if n["id"] == self.drag_id:
                n["x"] = self.drag_sx + dx
                n["y"] = self.drag_sy + dy
        self.da.queue_draw()

    def _drag_end(self, *_):
        if self.drag_id:
            save_notes(self.notes)
        self.drag_id = None

    def _edit_note(self, note):
        dlg = Gtk.Dialog(title="Edit Note", transient_for=self, modal=True)
        dlg.set_default_size(360, 280)
        box = dlg.get_content_area(); box.set_spacing(10); box.set_margin_start(16)
        box.set_margin_end(16); box.set_margin_top(12); box.set_margin_bottom(12)

        title_e = Gtk.Entry(); title_e.set_text(note.get("title",""))
        title_e.set_placeholder_text("Title…"); box.append(title_e)

        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True)
        tv = Gtk.TextView(); tv.set_wrap_mode(Gtk.WrapMode.WORD)
        tv.get_buffer().set_text(note.get("body",""))
        scroll.set_child(tv); box.append(scroll)

        save_btn = Gtk.Button(label="Save"); save_btn.add_css_class("add-btn")
        box.append(save_btn)

        def _save(*_):
            note["title"] = title_e.get_text()
            buf = tv.get_buffer()
            note["body"] = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
            save_notes(self.notes); self.da.queue_draw(); dlg.close()

        save_btn.connect("clicked", _save)
        dlg.present()

    def _draw(self, area, cr, w, h, _):
        paper_bg(cr, w, h)

        filt = self._filter
        for n in self.notes:
            if filt and filt not in (n.get("title","") + n.get("body","")).lower():
                continue
            draw_sticky(cr,
                n.get("x", 40), n.get("y", 40),
                NOTE_W, NOTE_H,
                n.get("color", 0),
                n.get("title", "Note"),
                n.get("body", ""),
                n.get("angle", 0),
                selected=(n["id"] == self.selected))

        # Watermark at bottom
        cr.select_font_face("Caveat", 0, 0); cr.set_font_size(11)
        cr.set_source_rgba(0.55, 0.45, 0.75, 0.35)
        cr.move_to(12, h-8); cr.show_text("NYXUS Stickies  ·  double-click to edit  ·  drag to move")


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.nyxus.stickies")
    def do_activate(self):
        win = StickyApp(self)
        win.present()

App().run()
