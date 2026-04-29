#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Stickies — Full Cairo UI · Hand-drawn · Neon Cards           ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED      ║
# ╚══════════════════════════════════════════════════════════════════════╝
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Gio, Pango
import json, uuid, os, math, random as _rand
from datetime import datetime

DATA_FILE = os.path.expanduser("~/.nyxus/stickies.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

WIN_W, WIN_H = 1100, 720
TOOLBAR_H    = 68
COLORBAR_H   = 44
CANVAS_Y     = TOOLBAR_H + COLORBAR_H
NOTE_W, NOTE_H = 288, 218
C_DARK = (0.031, 0.031, 0.055)

# Neon ink (border/text color per theme)
NOTE_INK = [
    (1.00, 0.00, 1.00),   # pink
    (0.80, 0.00, 1.00),   # purple
    (0.00, 0.53, 1.00),   # blue
    (0.22, 1.00, 0.08),   # green
    (1.00, 1.00, 0.00),   # yellow
    (1.00, 0.33, 0.00),   # orange
]
# Card fill (very dark tinted)
NOTE_PAPER = [
    (0.09, 0.01, 0.09),
    (0.05, 0.01, 0.11),
    (0.01, 0.04, 0.12),
    (0.01, 0.09, 0.02),
    (0.09, 0.09, 0.01),
    (0.10, 0.03, 0.01),
]
THEME_NAMES = ["PINK","PURPLE","BLUE","GREEN","YELLOW","ORANGE"]
PALETTE_HEX = ["#ff00ff","#cc00ff","#0088ff","#39ff14","#ffff00","#ff5500"]


# ── Cairo helpers ─────────────────────────────────────────────────────────────

def _rng(seed):
    return _rand.Random(int(seed) % 65535)

def _rng2(x, y=0, w=0, h=0):
    return _rand.Random(int(x*3 + y*7 + (w or 1)*11 + (h or 1)*13) % 65535)

def spray_dots(cr, cx, cy, col, n=60, spread=18, alpha_max=0.55, rng=None):
    r, g, b = col
    if rng is None: rng = _rand.Random()
    for _ in range(n):
        angle = rng.uniform(0, math.pi*2)
        dist  = abs(rng.gauss(0, spread*0.38))
        dot_r = rng.uniform(0.5, 2.2)
        alpha = alpha_max * max(0, 1 - dist/(spread+1)) * rng.uniform(0.6,1.0)
        if alpha < 0.02: continue
        cr.set_source_rgba(r, g, b, alpha)
        cr.arc(cx + math.cos(angle)*dist, cy + math.sin(angle)*dist,
               dot_r, 0, math.pi*2)
        cr.fill()

def sketch_rect(cr, x, y, w, h, col, thick=2.8, jitter=3.0, fill_rgba=None):
    r, g, b = col
    rng = _rng2(x, y, w, h)
    j = lambda s=1.0: rng.uniform(-jitter*s, jitter*s)
    def _path():
        cr.move_to(x+j(.4),      y+j(.4))
        cr.curve_to(x+w*.33+j(), y+j(),      x+w*.67+j(), y+j(),       x+w+j(.4), y+j(.4))
        cr.curve_to(x+w+j(),     y+h*.33+j(),x+w+j(),     y+h*.67+j(), x+w+j(.4), y+h+j(.4))
        cr.curve_to(x+w*.67+j(), y+h+j(),    x+w*.33+j(), y+h+j(),     x+j(.4),   y+h+j(.4))
        cr.curve_to(x+j(),       y+h*.67+j(),x+j(),       y+h*.33+j(), x+j(.4),   y+j(.4))
        cr.close_path()
    if fill_rgba:
        _path(); cr.set_source_rgba(*fill_rgba); cr.fill()
        rng = _rng2(x+1,y+1,w,h); j = lambda s=1.0: rng.uniform(-jitter*s, jitter*s)
    _path()
    cr.set_source_rgba(r, g, b, 0.92)
    cr.set_line_width(thick); cr.set_line_cap(1); cr.set_line_join(1)
    cr.stroke()

def glow_sketch_rect(cr, x, y, w, h, col, thick=3.0):
    r, g, b = col
    for blur, alpha in [(20,0.05),(13,0.10),(8,0.18),(4,0.28),(2,0.40)]:
        cr.set_source_rgba(r, g, b, alpha)
        cr.set_line_width(thick + blur)
        cr.rectangle(x, y, w, h); cr.stroke()
    sketch_rect(cr, x, y, w, h, col, thick=thick, jitter=2.8)

def caveat(cr, size, bold=False):
    cr.select_font_face("Caveat", 0, 1 if bold else 0)
    cr.set_font_size(size)

def glow_text(cr, x, y, txt, col, size, bold=False, glow_alpha=0.22):
    r, g, b = col
    caveat(cr, size, bold)
    cr.set_source_rgba(r, g, b, glow_alpha)
    cr.move_to(x+2, y+2); cr.show_text(txt)
    cr.set_source_rgba(r, g, b, 0.96)
    cr.move_to(x, y); cr.show_text(txt)

def _wrap(cr, text, max_w, size=14):
    caveat(cr, size)
    if not text: return []
    lines=[]; cur=""
    for word in text.split(' '):
        test = (cur+' '+word).strip()
        if cr.text_extents(test).width > max_w and cur:
            lines.append(cur); cur=word
        else: cur=test
    if cur: lines.append(cur)
    return lines


# ── Background ────────────────────────────────────────────────────────────────

def draw_canvas_bg(cr, x, y, w, h):
    """Paint-splatter background for the sticky note canvas only."""
    cr.set_source_rgb(*C_DARK); cr.rectangle(x,y,w,h); cr.fill()
    neons = list(NOTE_INK)
    rng = _rand.Random(77)
    for _ in range(24):
        bx=x+rng.uniform(0,w); by=y+rng.uniform(0,h); br=rng.uniform(8,38)
        cr.set_source_rgba(*rng.choice(neons), rng.uniform(0.04,0.13))
        cr.arc(bx,by,br,0,math.pi*2); cr.fill()
    for _ in range(32):
        sx=x+rng.uniform(0,w); sy=y+rng.uniform(0,h)
        ex=sx+rng.uniform(-110,110); ey=sy+rng.uniform(-16,16)
        cr.set_source_rgba(*rng.choice(neons), rng.uniform(0.04,0.14))
        cr.set_line_width(rng.uniform(0.6,2.6))
        cr.move_to(sx,sy); cr.line_to(ex,ey); cr.stroke()
    for _ in range(8):
        spray_dots(cr, x+rng.uniform(0,w), y+rng.uniform(0,h),
                   rng.choice(neons), n=35, spread=int(rng.uniform(22,65)),
                   alpha_max=0.14, rng=rng)
    for _ in range(130):
        cr.set_source_rgba(*rng.choice(neons), rng.uniform(0.05,0.18))
        cr.arc(x+rng.uniform(0,w), y+rng.uniform(0,h),
               rng.uniform(0.6,2.8), 0, math.pi*2); cr.fill()
    sp=32
    for gx in range(int(x)+sp, int(x+w), sp):
        for gy in range(int(y)+sp, int(y+h), sp):
            cr.set_source_rgba(*rng.choice(neons), 0.05)
            cr.arc(gx,gy,1.1,0,math.pi*2); cr.fill()
    cr.set_line_width(0.35)
    for ry in range(int(y)+32,int(y+h),32):
        cr.set_source_rgba(1,1,1,0.025)
        cr.move_to(x,ry); cr.line_to(x+w,ry); cr.stroke()


# ── Toolbar ───────────────────────────────────────────────────────────────────

def draw_toolbar(cr, w, note_count, selected_theme, search_txt, hovered_btn):
    # Distinctly purple-dark band — very different from canvas
    cr.set_source_rgb(0.10, 0.04, 0.18)
    cr.rectangle(0, 0, w, TOOLBAR_H); cr.fill()

    # Neon top edge line
    cr.set_source_rgba(1, 0, 1, 0.70); cr.set_line_width(2.5)
    cr.move_to(0, 1); cr.line_to(w, 1); cr.stroke()
    # Neon bottom edge line
    cr.set_source_rgba(1, 0, 1, 0.55); cr.set_line_width(2.0)
    cr.move_to(0, TOOLBAR_H-1); cr.line_to(w, TOOLBAR_H-1); cr.stroke()

    # Title — very bright, large
    glow_text(cr, 18, 44, "NYXUS STICKIES", (1, 0, 1), 30, bold=True, glow_alpha=0.35)

    # Note count
    caveat(cr, 15)
    cr.set_source_rgba(0.80, 0.60, 1.0, 0.80)
    cr.move_to(295, 42)
    cr.show_text(f"{note_count} note{'s' if note_count!=1 else ''}")

    # Search box border (GTK Entry is overlaid transparently here)
    search_x = w - 580
    sketch_rect(cr, search_x, 15, 212, 38, (0.7, 0.3, 1.0), thick=2.0, jitter=1.8,
                fill_rgba=(0.06, 0.02, 0.12, 0.95))
    if not search_txt:
        caveat(cr, 14)
        cr.set_source_rgba(0.55, 0.40, 0.80, 0.50)
        cr.move_to(search_x+12, 39); cr.show_text("search notes...")

    # + NEW NOTE button
    new_x = w - 352; new_col = (1.0, 0.0, 1.0)
    hov_new = hovered_btn == "new"
    sketch_rect(cr, new_x, 11, 156, 46, new_col, thick=2.6, jitter=2.4,
                fill_rgba=(0.30, 0.0, 0.30, 0.95) if hov_new else (0.16, 0.0, 0.20, 0.95))
    glow_text(cr, new_x+12, 41, "+ NEW NOTE", new_col, 17, bold=True, glow_alpha=0.30)

    # ✕ DELETE button
    del_x = w - 182; del_col = (1.0, 0.28, 0.08)
    hov_del = hovered_btn == "del"
    sketch_rect(cr, del_x, 11, 142, 46, del_col, thick=2.6, jitter=2.4,
                fill_rgba=(0.28, 0.06, 0.02, 0.95) if hov_del else (0.15, 0.03, 0.01, 0.95))
    glow_text(cr, del_x+14, 41, "✕ DELETE", del_col, 17, bold=True, glow_alpha=0.28)


def draw_colorbar(cr, w, selected_theme, hovered_color):
    cr.set_source_rgba(0.05,0.03,0.09,0.98)
    cr.rectangle(0, TOOLBAR_H, w, COLORBAR_H); cr.fill()
    cr.set_source_rgba(0.5,0.2,0.7,0.18); cr.set_line_width(1.0)
    cr.move_to(0,TOOLBAR_H+COLORBAR_H); cr.line_to(w,TOOLBAR_H+COLORBAR_H); cr.stroke()

    caveat(cr, 13)
    cr.set_source_rgba(0.65,0.50,0.85,0.65)
    cr.move_to(18, TOOLBAR_H+28); cr.show_text("NOTE THEME:")

    cx_start = 150
    for i, (name, col) in enumerate(zip(THEME_NAMES, NOTE_INK)):
        bx = cx_start + i*108
        by = TOOLBAR_H + 7
        bw, bh = 96, 30
        is_sel = (i == selected_theme)
        is_hov = (hovered_color == i)
        fill_a = 0.35 if (is_sel or is_hov) else 0.14
        sketch_rect(cr, bx, by, bw, bh, col, thick=2.5 if is_sel else 1.8,
                    jitter=2.0, fill_rgba=(*col, fill_a))
        glow_text(cr, bx+14, by+22, name, col, 14, bold=is_sel)
        if is_sel:
            # Extra tick mark — selected state
            caveat(cr, 11)
            cr.set_source_rgba(*col, 0.70)
            cr.move_to(bx+bw-14, by+22); cr.show_text("✓")


# ── Sticky note card ──────────────────────────────────────────────────────────

def draw_sticky(cr, nx, ny, nw, nh, cidx, title, body, angle,
                selected=False, created=""):
    cidx %= len(NOTE_INK)
    ir, ig, ib = NOTE_INK[cidx]
    pr, pg, pb = NOTE_PAPER[cidx]
    rng = _rng2(nx, ny, nw, nh)

    cr.save()
    cr.translate(nx+nw/2, ny+nh/2)
    cr.rotate(math.radians(angle))
    cr.translate(-nw/2, -nh/2)

    # Drop shadow
    for sh, sa in [(14,0.07),(9,0.12),(5,0.17),(2,0.24)]:
        cr.set_source_rgba(ir,ig,ib,sa)
        cr.rectangle(sh, sh+3, nw, nh); cr.fill()

    # Card body
    cr.set_source_rgb(pr,pg,pb)
    cr.rectangle(0,0,nw,nh); cr.fill()

    # Subtle spray texture on paper
    for _ in range(rng.randint(2,5)):
        spray_dots(cr, rng.uniform(0,nw), rng.uniform(0,nh),
                   (ir,ig,ib), n=9, spread=14, alpha_max=0.08, rng=rng)

    # Header band
    header_h = 40
    cr.set_source_rgba(ir,ig,ib,0.16); cr.rectangle(0,0,nw,header_h); cr.fill()
    cr.set_source_rgba(ir,ig,ib,0.60); cr.set_line_width(1.4)
    cr.move_to(0,header_h); cr.line_to(nw,header_h); cr.stroke()

    # Ruled lines
    cr.set_line_width(0.5)
    for ly in range(header_h+20, int(nh)-8, 22):
        cr.set_source_rgba(ir,ig,ib,0.11)
        cr.move_to(12,ly); cr.line_to(nw-12,ly); cr.stroke()

    # Glow border (the key visual)
    if selected:
        glow_sketch_rect(cr,-4,-4,nw+8,nh+8,(1,1,1),thick=2.2)
    glow_sketch_rect(cr,1,1,nw-2,nh-2,(ir,ig,ib),thick=3.2)

    # Folded corner
    corner=22
    cr.set_source_rgba(ir*0.25,ig*0.25,ib*0.25,0.96)
    cr.move_to(nw-corner,nh); cr.line_to(nw,nh-corner)
    cr.line_to(nw,nh); cr.close_path(); cr.fill()
    cr.set_source_rgba(ir,ig,ib,0.42); cr.set_line_width(0.9)
    cr.move_to(nw-corner,nh); cr.line_to(nw,nh-corner); cr.stroke()
    cr.set_source_rgba(1,1,1,0.14)
    cr.move_to(nw-corner+2,nh-1); cr.line_to(nw-1,nh-corner+2); cr.stroke()

    # Pushpin
    pcx,pcy,pr2=nw//2,8,7
    cr.set_source_rgba(0,0,0,0.45); cr.arc(pcx+2,pcy+3,pr2,0,math.pi*2); cr.fill()
    cr.set_source_rgba(ir,ig,ib,0.26); cr.arc(pcx,pcy,pr2,0,math.pi*2); cr.fill()
    cr.set_source_rgba(ir,ig,ib,0.88); cr.set_line_width(1.8)
    cr.arc(pcx,pcy,pr2,0,math.pi*2); cr.stroke()
    cr.set_source_rgba(1.0,0.96,0.88,0.80); cr.arc(pcx-2.5,pcy-2.5,3.2,0,math.pi*2); cr.fill()

    # Title
    caveat(cr,16,bold=True)
    t=(title or "Note")[:26]
    cr.set_source_rgba(0,0,0,0.50); cr.move_to(12,28); cr.show_text(t)
    cr.set_source_rgba(ir,ig,ib,0.22); cr.move_to(11,27); cr.show_text(t)
    cr.set_source_rgba(ir,ig,ib,0.96); cr.move_to(11,27); cr.show_text(t)

    # Body text
    lines=_wrap(cr,body or "",nw-26,14)
    for i,line in enumerate(lines[:6]):
        cr.set_source_rgba(ir,ig,ib,0.80)
        cr.move_to(13, header_h+18+i*22); cr.show_text(line)
    if len(lines)>6:
        caveat(cr,11); cr.set_source_rgba(ir,ig,ib,0.38)
        cr.move_to(13,header_h+18+6*22); cr.show_text(f"+ {len(lines)-6} more…")

    # Timestamp
    if created:
        try:    ts=datetime.fromisoformat(created).strftime("%b %d  %H:%M")
        except: ts=created[:16]
        caveat(cr,10); cr.set_source_rgba(ir,ig,ib,0.32)
        cr.move_to(10,nh-8); cr.show_text(ts)

    cr.restore()


# ── Data ──────────────────────────────────────────────────────────────────────

def load_notes():
    try:
        with open(DATA_FILE) as f: return json.load(f)
    except Exception: return []

def save_notes(notes):
    try:
        with open(DATA_FILE,'w') as f: json.dump(notes,f,indent=2)
    except Exception: pass


# ── Hit regions ───────────────────────────────────────────────────────────────

def toolbar_hit(mx, my, win_w):
    if my < 0 or my > TOOLBAR_H: return None
    new_x = win_w - 350
    del_x = win_w - 185
    if new_x <= mx <= new_x+152: return "new"
    if del_x <= mx <= del_x+140: return "del"
    return None

def colorbar_hit(mx, my):
    if my < TOOLBAR_H or my > TOOLBAR_H+COLORBAR_H: return None
    cx_start=150
    for i in range(6):
        bx=cx_start+i*108; bw=96
        if bx <= mx <= bx+bw: return i
    return None

def canvas_hit(mx, my, notes, canvas_y):
    cy_off = canvas_y
    for n in reversed(notes):
        nx,ny=n["x"],n["y"]+cy_off
        if nx<=mx<=nx+NOTE_W and ny<=my<=ny+NOTE_H:
            return n
    return None


# ── Main app ──────────────────────────────────────────────────────────────────

CSS_MIN = """
* { font-family: 'Caveat','Patrick Hand','Comic Sans MS',sans-serif; }
window { background-color: #08080e; }
.search-e {
    background-color: transparent;
    border: none; outline: none;
    color: rgba(200,180,240,0.90);
    font-size: 14px; font-family: 'Caveat', sans-serif;
    padding: 4px 8px;
}
.search-e text { background-color: transparent; }
.dlg-title-e {
    background-color: rgba(20,10,30,0.98);
    border: 2px solid rgba(255,0,255,0.50); border-radius: 4px;
    color: rgba(240,220,255,0.95); font-size:17px; padding:7px 12px;
}
.dlg-body {
    background-color: rgba(16,8,26,0.98);
    border: 2px solid rgba(140,60,220,0.40); border-radius: 4px;
    color: rgba(230,220,245,0.92); font-size:15px; padding:6px;
}
.dlg-save {
    background-color: rgba(255,0,255,0.18); color: #ff66ff;
    border: 2px solid rgba(255,0,255,0.75); border-radius:4px;
    padding:8px 28px; font-size:16px; font-weight:bold; margin-top:8px;
}
.dlg-save:hover { background-color: rgba(255,0,255,0.38); color:#fff; }
"""


class StickyApp(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NYXUS Stickies")
        self.set_default_size(WIN_W, WIN_H)
        self.set_resizable(True)
        self.notes          = load_notes()
        self.selected_id    = None
        self.selected_theme = 0      # currently chosen color for new/recolor
        self.hovered_btn    = None   # "new" | "del" | None
        self.hovered_color  = None   # 0-5 | None
        self.drag_id        = None
        self.drag_sx        = 0
        self.drag_sy        = 0
        self._filter        = ""
        self._search_txt    = ""
        self._build()

    # ── Build ──────────────────────────────────────────────────────────────

    def _build(self):
        css_p = Gtk.CssProvider()
        try:    css_p.load_from_string(CSS_MIN)
        except AttributeError: css_p.load_from_data(CSS_MIN.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        overlay = Gtk.Overlay()
        self.set_child(overlay)

        # Full-window Cairo drawing area
        self.da = Gtk.DrawingArea()
        self.da.set_draw_func(self._draw)
        overlay.set_child(self.da)

        # Floating search entry (positioned over the search slot in toolbar)
        self._search = Gtk.Entry()
        self._search.set_placeholder_text("search notes...")
        self._search.add_css_class("search-e")
        self._search.set_halign(Gtk.Align.START)
        self._search.set_valign(Gtk.Align.START)
        self._search.connect("changed", self._on_search)
        overlay.add_overlay(self._search)
        overlay.set_clip_overlay(self._search, False)
        GLib.idle_add(self._reposition_search)

        # Gestures
        click = Gtk.GestureClick()
        click.set_button(0)
        click.connect("pressed", self._on_press)
        self.da.add_controller(click)

        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_motion)
        self.da.add_controller(motion)

        drag = Gtk.GestureDrag()
        drag.connect("drag-begin",  self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end",    self._drag_end)
        self.da.add_controller(drag)

        key = Gtk.EventControllerKey()
        key.connect("key-pressed", self._on_key)
        self.add_controller(key)

        self.connect("notify::default-size", self._on_resize)

    def _reposition_search(self):
        w = self.get_width() or WIN_W
        search_x = w - 580
        self._search.set_margin_start(search_x + 10)
        self._search.set_margin_top(20)
        self._search.set_size_request(192, 32)
        return False

    def _on_resize(self, *_):
        GLib.idle_add(self._reposition_search)

    # ── Draw ───────────────────────────────────────────────────────────────

    def _draw(self, area, cr, w, h, _):
        # 1. Full window base fill
        cr.set_source_rgb(*C_DARK); cr.rectangle(0,0,w,h); cr.fill()

        # 2. Toolbar (distinctly purple-dark band at top)
        draw_toolbar(cr, w, len(self.notes), self.selected_theme,
                     self._search_txt, self.hovered_btn)

        # 3. Color bar
        draw_colorbar(cr, w, self.selected_theme, self.hovered_color)

        # 4. Canvas paint-splatter background (below the bars only)
        canvas_h = h - CANVAS_Y
        if canvas_h > 0:
            draw_canvas_bg(cr, 0, CANVAS_Y, w, canvas_h)

        # 5. Notes
        filt = self._filter
        for n in self.notes:
            if filt and filt not in (n.get("title","")+n.get("body","")).lower():
                continue
            ny_draw = n.get("y", 40) + CANVAS_Y
            draw_sticky(cr,
                n.get("x", 40), ny_draw,
                NOTE_W, NOTE_H,
                n.get("color", 0),
                n.get("title", "Note"),
                n.get("body", ""),
                n.get("angle", 0),
                selected=(n["id"] == self.selected_id),
                created=n.get("created",""))

        # 6. Watermark
        caveat(cr, 11)
        cr.set_source_rgba(0.50, 0.38, 0.70, 0.25)
        cr.move_to(14, h-8)
        cr.show_text("NYXUS Stickies  ·  double-click to edit  ·  drag to move")

    # ── Input ──────────────────────────────────────────────────────────────

    def _on_motion(self, ctrl, mx, my):
        btn = toolbar_hit(mx, my, self.get_width() or WIN_W)
        col = colorbar_hit(mx, my) if btn is None else None
        changed = (btn != self.hovered_btn or col != self.hovered_color)
        self.hovered_btn   = btn
        self.hovered_color = col
        if changed: self.da.queue_draw()

    def _on_press(self, gesture, npress, mx, my):
        w = self.get_width() or WIN_W

        # Toolbar buttons
        btn = toolbar_hit(mx, my, w)
        if btn == "new":  self._add_note(); return
        if btn == "del":  self._del_note(); return

        # Color bar
        cidx = colorbar_hit(mx, my)
        if cidx is not None:
            self.selected_theme = cidx
            # Also recolor the selected note immediately
            if self.selected_id:
                for n in self.notes:
                    if n["id"] == self.selected_id:
                        n["color"] = cidx
                save_notes(self.notes)
            self.da.queue_draw(); return

        # Canvas notes
        if my < CANVAS_Y: return
        n = self._canvas_hit(mx, my)
        if n:
            self.selected_id = n["id"]
            if npress == 2: self._edit_note(n)
        else:
            self.selected_id = None
        self.da.queue_draw()

    def _on_key(self, ctrl, keyval, keycode, state):
        if keyval == Gdk.KEY_Escape:
            self.selected_id = None; self.da.queue_draw()

    def _on_search(self, entry, *_):
        self._filter     = entry.get_text().lower()
        self._search_txt = entry.get_text()
        self.da.queue_draw()

    # ── Canvas hit test ────────────────────────────────────────────────────

    def _canvas_hit(self, mx, my):
        for n in reversed(self.notes):
            nx = n["x"]; ny = n["y"] + CANVAS_Y
            if nx <= mx <= nx+NOTE_W and ny <= my <= ny+NOTE_H:
                return n
        return None

    # ── Actions ────────────────────────────────────────────────────────────

    def _add_note(self):
        w = self.get_width()  or WIN_W
        h = self.get_height() or WIN_H
        ch = h - CANVAS_Y
        rng = _rand.Random()
        self.notes.append({
            "id":      str(uuid.uuid4()),
            "title":   f"Note {len(self.notes)+1}",
            "body":    "",
            "color":   self.selected_theme,
            "x":       max(10, min(w-NOTE_W-10, rng.randint(40, max(41,w-NOTE_W-40)))),
            "y":       max(10, min(ch-NOTE_H-10, rng.randint(30, max(31,ch-NOTE_H-30)))),
            "angle":   rng.uniform(-6,6),
            "created": datetime.now().isoformat(),
        })
        self.selected_id = self.notes[-1]["id"]
        save_notes(self.notes); self.da.queue_draw()

    def _del_note(self):
        if not self.selected_id: return
        self.notes = [n for n in self.notes if n["id"] != self.selected_id]
        self.selected_id = None
        save_notes(self.notes); self.da.queue_draw()

    # ── Drag ───────────────────────────────────────────────────────────────

    def _drag_begin(self, gesture, x, y):
        if y < CANVAS_Y: return
        n = self._canvas_hit(x, y)
        if n:
            self.drag_id = n["id"]
            self.drag_sx, self.drag_sy = n["x"], n["y"]
            self.notes.remove(n); self.notes.append(n)

    def _drag_update(self, gesture, dx, dy):
        if not self.drag_id: return
        for n in self.notes:
            if n["id"] == self.drag_id:
                n["x"] = self.drag_sx + dx
                n["y"] = self.drag_sy + dy
        self.da.queue_draw()

    def _drag_end(self, *_):
        if self.drag_id: save_notes(self.notes)
        self.drag_id = None

    # ── Edit dialog ────────────────────────────────────────────────────────

    def _edit_note(self, note):
        dlg = Gtk.Dialog(title="Edit Note", transient_for=self, modal=True)
        dlg.set_default_size(420, 340)
        box = dlg.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(18); box.set_margin_end(18)
        box.set_margin_top(16);   box.set_margin_bottom(16)

        title_e = Gtk.Entry()
        title_e.set_text(note.get("title",""))
        title_e.set_placeholder_text("Title…")
        title_e.add_css_class("dlg-title-e")
        box.append(title_e)

        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True)
        tv = Gtk.TextView(); tv.set_wrap_mode(Gtk.WrapMode.WORD)
        tv.add_css_class("dlg-body")
        tv.get_buffer().set_text(note.get("body",""))
        scroll.set_child(tv); box.append(scroll)

        save_btn = Gtk.Button(label="✓ SAVE")
        save_btn.add_css_class("dlg-save")
        save_btn.set_halign(Gtk.Align.CENTER)
        box.append(save_btn)

        def _save(*_):
            note["title"] = title_e.get_text()
            buf = tv.get_buffer()
            note["body"] = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
            save_notes(self.notes); self.da.queue_draw(); dlg.close()

        save_btn.connect("clicked", _save)
        dlg.present()


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.stickies",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
    def do_activate(self):
        StickyApp(self).present()

App().run()
