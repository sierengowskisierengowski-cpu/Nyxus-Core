#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Stickies — Graffiti Notes · Neon Cards · Cork Board          ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED      ║
# ╚══════════════════════════════════════════════════════════════════════╝
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Gio
import json, uuid, os, math, random as _rand
from datetime import datetime

DATA_FILE = os.path.expanduser("~/.nyxus/stickies.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# ── Palette ──────────────────────────────────────────────────────────────────
NOTE_PAPER = [
    (0.08, 0.01, 0.09),   # dark magenta
    (0.05, 0.01, 0.12),   # dark purple
    (0.01, 0.04, 0.13),   # dark blue
    (0.01, 0.09, 0.02),   # dark green
    (0.09, 0.09, 0.01),   # dark yellow
    (0.11, 0.03, 0.01),   # dark orange
]
NOTE_INK = [
    (1.00, 0.00, 1.00),
    (0.80, 0.00, 1.00),
    (0.00, 0.53, 1.00),
    (0.22, 1.00, 0.08),
    (1.00, 1.00, 0.00),
    (1.00, 0.33, 0.00),
]
PALETTE_HEX = ["#ff00ff","#cc00ff","#0088ff","#39ff14","#ffff00","#ff5500"]
THEME_NAMES = ["PINK","PURPLE","BLUE","GREEN","YELLOW","ORANGE"]
NOTE_W, NOTE_H = 292, 220
C_DARK = (0.031, 0.031, 0.055)


# ── Drawing helpers ───────────────────────────────────────────────────────────

def _rng(x, y=0, w=0, h=0):
    return _rand.Random(int(x*3 + y*7 + (w or 1)*11 + (h or 1)*13) % 65535)

def spray_dots(cr, cx, cy, color, n=60, spread=18, alpha_max=0.55, rng=None):
    r, g, b = color
    if rng is None: rng = _rand.Random()
    for _ in range(n):
        angle  = rng.uniform(0, math.pi * 2)
        dist   = abs(rng.gauss(0, spread * 0.38))
        dot_r  = rng.uniform(0.4, 2.0)
        alpha  = alpha_max * max(0, 1 - dist / (spread + 1))
        if alpha < 0.02: continue
        cr.set_source_rgba(r, g, b, alpha * rng.uniform(0.6, 1.0))
        cr.arc(cx + math.cos(angle)*dist, cy + math.sin(angle)*dist,
               dot_r, 0, math.pi*2)
        cr.fill()

def sketch_rect(cr, x, y, w, h, r, g, b, thick=2.8, jitter=3.2, fill_rgba=None):
    rng = _rng(x, y, w, h); j = lambda s=1.0: rng.uniform(-jitter*s, jitter*s)
    def _path():
        cr.move_to(x+j(.4),       y+j(.4))
        cr.curve_to(x+w*.33+j(),  y+j(),       x+w*.67+j(), y+j(),        x+w+j(.4), y+j(.4))
        cr.curve_to(x+w+j(),      y+h*.33+j(), x+w+j(),     y+h*.67+j(),  x+w+j(.4), y+h+j(.4))
        cr.curve_to(x+w*.67+j(),  y+h+j(),     x+w*.33+j(), y+h+j(),      x+j(.4),   y+h+j(.4))
        cr.curve_to(x+j(),        y+h*.67+j(), x+j(),       y+h*.33+j(),  x+j(.4),   y+j(.4))
        cr.close_path()
    if fill_rgba:
        _path(); cr.set_source_rgba(*fill_rgba); cr.fill()
        rng2 = _rng(x+1, y+1, w, h); j = lambda s=1.0: rng2.uniform(-jitter*s, jitter*s)
    _path()
    cr.set_source_rgba(r, g, b, 0.92)
    cr.set_line_width(thick); cr.set_line_cap(1); cr.set_line_join(1)
    cr.stroke()

def neon_glow_rect(cr, x, y, w, h, r, g, b, thick=3.0):
    """Multi-pass neon glow border — same style as control app profile cards."""
    for blur, alpha in [(18, 0.06), (12, 0.12), (7, 0.20), (4, 0.30), (2, 0.45)]:
        cr.set_source_rgba(r, g, b, alpha)
        cr.set_line_width(thick + blur)
        cr.rectangle(x, y, w, h); cr.stroke()
    # Sharp final stroke
    sketch_rect(cr, x, y, w, h, r, g, b, thick=thick, jitter=2.8)

def paper_bg(cr, w, h):
    """Dark NYXUS board — layered splatters, spray streaks, dot grid."""
    cr.set_source_rgb(*C_DARK); cr.rectangle(0, 0, w, h); cr.fill()
    neons = [(1,0,1),(0.8,0,1),(0,0.53,1),(0.22,1,0.08),(1,1,0),(1,0.33,0)]
    rng = _rand.Random(99)

    # Large organic paint blobs
    for _ in range(22):
        bx = rng.uniform(0, w); by = rng.uniform(0, h)
        br = rng.uniform(8, 36); nc = rng.choice(neons)
        cr.set_source_rgba(*nc, rng.uniform(0.04, 0.13))
        cr.arc(bx, by, br, 0, math.pi*2); cr.fill()

    # Spray streaks
    for _ in range(30):
        sx = rng.uniform(0, w); sy = rng.uniform(0, h)
        ex = sx + rng.uniform(-100, 100); ey = sy + rng.uniform(-14, 14)
        nc = rng.choice(neons)
        cr.set_source_rgba(*nc, rng.uniform(0.05, 0.16))
        cr.set_line_width(rng.uniform(0.6, 2.4))
        cr.move_to(sx, sy); cr.line_to(ex, ey); cr.stroke()

    # Spray dot clouds
    for _ in range(6):
        cx2 = rng.uniform(0, w); cy2 = rng.uniform(0, h)
        spray_dots(cr, cx2, cy2, rng.choice(neons),
                   n=40, spread=int(rng.uniform(20, 60)),
                   alpha_max=0.16, rng=rng)

    # Dense fine dots
    for _ in range(120):
        bx = rng.uniform(0, w); by = rng.uniform(0, h)
        br = rng.uniform(0.6, 2.8); nc = rng.choice(neons)
        cr.set_source_rgba(*nc, rng.uniform(0.06, 0.20))
        cr.arc(bx, by, br, 0, math.pi*2); cr.fill()

    # Subtle dot grid
    spacing = 32
    for gx in range(spacing, int(w), spacing):
        for gy in range(spacing, int(h), spacing):
            nc = rng.choice(neons)
            cr.set_source_rgba(*nc, 0.055)
            cr.arc(gx, gy, 1.1, 0, math.pi*2); cr.fill()

    # Faint ruled lines
    cr.set_line_width(0.35)
    for ry in range(32, int(h), 32):
        cr.set_source_rgba(1, 1, 1, 0.028)
        cr.move_to(0, ry); cr.line_to(w, ry); cr.stroke()


# ── Draw a single sticky note ─────────────────────────────────────────────────

def draw_sticky(cr, nx, ny, nw, nh, cidx, title, body, angle,
                selected=False, created="", pinned=False):
    cidx = cidx % len(NOTE_PAPER)
    pr, pg, pb = NOTE_PAPER[cidx]
    ir, ig, ib = NOTE_INK[cidx]
    rng = _rng(nx, ny, nw, nh)

    cr.save()
    cr.translate(nx + nw/2, ny + nh/2)
    cr.rotate(math.radians(angle))
    cr.translate(-nw/2, -nh/2)

    # ── Drop shadow with neon tint ────────────────────────────────────────
    for sh, sa in [(14, 0.07), (9, 0.11), (5, 0.16), (2, 0.22)]:
        cr.set_source_rgba(ir, ig, ib, sa)
        cr.rectangle(sh, sh+3, nw, nh); cr.fill()

    # ── Card body ─────────────────────────────────────────────────────────
    cr.set_source_rgb(pr, pg, pb)
    cr.rectangle(0, 0, nw, nh); cr.fill()

    # Subtle inner paper texture — faint spray scatter
    for _ in range(rng.randint(3, 6)):
        tx = rng.uniform(0, nw); ty = rng.uniform(0, nh)
        spray_dots(cr, tx, ty, (ir, ig, ib), n=8, spread=14,
                   alpha_max=0.07, rng=rng)

    # ── Header band ───────────────────────────────────────────────────────
    header_h = 38
    cr.set_source_rgba(ir, ig, ib, 0.14)
    cr.rectangle(0, 0, nw, header_h); cr.fill()
    # Header bottom rule — bright neon line
    cr.set_source_rgba(ir, ig, ib, 0.55)
    cr.set_line_width(1.2)
    cr.move_to(0, header_h); cr.line_to(nw, header_h); cr.stroke()

    # ── Ruled lines in body ───────────────────────────────────────────────
    cr.set_line_width(0.5)
    for ly in range(header_h + 20, int(nh) - 8, 21):
        cr.set_source_rgba(ir, ig, ib, 0.10)
        cr.move_to(12, ly); cr.line_to(nw - 12, ly); cr.stroke()

    # ── Neon glowing border (the signature look) ──────────────────────────
    if selected:
        # Double-ring selection state
        neon_glow_rect(cr, -4, -4, nw+8, nh+8, 1, 1, 1, thick=2.5)
    neon_glow_rect(cr, 1, 1, nw-2, nh-2, ir, ig, ib, thick=3.0)

    # ── Folded corner (bottom-right) ──────────────────────────────────────
    corner = 22
    cr.set_source_rgba(ir*0.28, ig*0.28, ib*0.28, 0.96)
    cr.move_to(nw-corner, nh); cr.line_to(nw, nh-corner)
    cr.line_to(nw, nh); cr.close_path(); cr.fill()
    cr.set_source_rgba(ir, ig, ib, 0.40)
    cr.set_line_width(0.9)
    cr.move_to(nw-corner, nh); cr.line_to(nw, nh-corner); cr.stroke()
    # Fold highlight
    cr.set_source_rgba(1, 1, 1, 0.12)
    cr.move_to(nw-corner+2, nh-1); cr.line_to(nw-1, nh-corner+2); cr.stroke()

    # ── Pushpin ───────────────────────────────────────────────────────────
    pin_cx, pin_cy = nw//2, 8
    pin_r = 7
    # Pin shadow
    cr.set_source_rgba(0, 0, 0, 0.45)
    cr.arc(pin_cx+2, pin_cy+3, pin_r, 0, math.pi*2); cr.fill()
    # Pin body — neon color ring
    cr.set_source_rgba(ir, ig, ib, 0.28)
    cr.arc(pin_cx, pin_cy, pin_r, 0, math.pi*2); cr.fill()
    cr.set_source_rgba(ir, ig, ib, 0.85)
    cr.set_line_width(1.6)
    cr.arc(pin_cx, pin_cy, pin_r, 0, math.pi*2); cr.stroke()
    # Pin highlight
    cr.set_source_rgba(1.0, 0.96, 0.88, 0.78)
    cr.arc(pin_cx - 2.5, pin_cy - 2.5, 3.2, 0, math.pi*2); cr.fill()
    # Pin stem
    if pinned:
        cr.set_source_rgba(ir, ig, ib, 0.60)
        cr.set_line_width(1.0)
        cr.move_to(pin_cx, pin_cy + pin_r)
        cr.line_to(pin_cx + 1, pin_cy + pin_r + 10); cr.stroke()

    # ── Title text ────────────────────────────────────────────────────────
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(15)
    t = (title or "Note")[:26]
    # Shadow
    cr.set_source_rgba(0, 0, 0, 0.50)
    cr.move_to(12, 27); cr.show_text(t)
    # Glow
    cr.set_source_rgba(ir, ig, ib, 0.22)
    cr.move_to(11, 26); cr.show_text(t)
    # Main
    cr.set_source_rgba(ir, ig, ib, 0.95)
    cr.move_to(11, 26); cr.show_text(t)

    # ── Body text ─────────────────────────────────────────────────────────
    cr.select_font_face("Caveat", 0, 0)
    cr.set_font_size(14)
    lines = _wrap(cr, body or "", nw - 26)
    for i, line in enumerate(lines[:6]):
        yt = header_h + 18 + i * 21
        cr.set_source_rgba(ir, ig, ib, 0.78)
        cr.move_to(13, yt); cr.show_text(line)
    if len(lines) > 6:
        cr.set_font_size(11)
        cr.set_source_rgba(ir, ig, ib, 0.38)
        cr.move_to(13, header_h + 18 + 6*21)
        cr.show_text(f"+ {len(lines)-6} more…")

    # ── Created timestamp (bottom-left, tiny) ─────────────────────────────
    if created:
        try:
            dt = datetime.fromisoformat(created)
            ts = dt.strftime("%b %d  %H:%M")
        except Exception:
            ts = created[:16]
        cr.select_font_face("Caveat", 0, 0)
        cr.set_font_size(10)
        cr.set_source_rgba(ir, ig, ib, 0.35)
        cr.move_to(10, nh - 8); cr.show_text(ts)

    cr.restore()


def _wrap(cr, text, max_w, size=14):
    cr.select_font_face("Caveat", 0, 0); cr.set_font_size(size)
    if not text: return []
    lines = []; cur = ""
    for word in text.split(' '):
        test = (cur + ' ' + word).strip()
        if cr.text_extents(test).width > max_w and cur:
            lines.append(cur); cur = word
        else:
            cur = test
    if cur: lines.append(cur)
    return lines


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = """
* { font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', sans-serif; }

window { background-color: #08080e; color: rgba(232,224,245,0.92); }

.toolbar {
    background-color: rgba(8,8,18,0.96);
    border-bottom: 2px solid rgba(255,0,255,0.28);
    padding: 10px 18px;
    min-height: 62px;
}

.theme-bar {
    background-color: rgba(6,6,15,0.98);
    border-bottom: 1px solid rgba(140,60,200,0.22);
    padding: 6px 18px;
    min-height: 40px;
}

.app-title {
    color: #ff44ff;
    font-size: 26px;
    font-weight: bold;
    letter-spacing: 4px;
    text-shadow: 0 0 18px #ff00ff, 0 0 6px #ff00ff;
    margin-right: 12px;
}

.count-lbl {
    color: rgba(200,160,240,0.72);
    font-size: 15px;
    margin: 0 8px;
}

.add-btn {
    background-color: rgba(255,0,255,0.14);
    color: #ff66ff;
    border: 2px solid rgba(255,0,255,0.65);
    border-radius: 4px;
    padding: 7px 20px;
    font-size: 16px;
    font-weight: bold;
    margin: 2px 4px;
    text-shadow: 0 0 10px #ff00ff;
}
.add-btn:hover {
    background-color: rgba(255,0,255,0.30);
    color: #ffffff;
    border-color: #ff00ff;
}

.del-btn {
    background-color: rgba(255,40,20,0.12);
    color: #ff6644;
    border: 2px solid rgba(255,70,40,0.60);
    border-radius: 4px;
    padding: 7px 18px;
    font-size: 16px;
    font-weight: bold;
    margin: 2px 4px;
}
.del-btn:hover { background-color: rgba(255,70,40,0.28); color: #ffffff; }

.search-e {
    background-color: rgba(255,255,255,0.04);
    border: 2px solid rgba(255,0,255,0.40);
    color: rgba(232,224,245,0.92);
    border-radius: 4px;
    padding: 6px 14px;
    font-size: 15px;
    min-width: 220px;
}
.search-e text { background-color: transparent; }

.theme-lbl {
    color: rgba(180,130,220,0.65);
    font-size: 13px;
    margin-right: 10px;
}

.col-pink   { background-color: rgba(255,0,255,0.16);   color: #ff00ff; border: 2px solid #ff00ff;   border-radius: 4px; padding: 4px 12px; font-size: 13px; font-weight: bold; margin: 1px 2px; }
.col-purple { background-color: rgba(204,0,255,0.16);   color: #cc00ff; border: 2px solid #cc00ff;   border-radius: 4px; padding: 4px 12px; font-size: 13px; font-weight: bold; margin: 1px 2px; }
.col-blue   { background-color: rgba(0,136,255,0.16);   color: #0088ff; border: 2px solid #0088ff;   border-radius: 4px; padding: 4px 12px; font-size: 13px; font-weight: bold; margin: 1px 2px; }
.col-green  { background-color: rgba(57,255,20,0.13);   color: #39ff14; border: 2px solid #39ff14;   border-radius: 4px; padding: 4px 12px; font-size: 13px; font-weight: bold; margin: 1px 2px; }
.col-yellow { background-color: rgba(255,255,0,0.13);   color: #e8e800; border: 2px solid #e8e800;   border-radius: 4px; padding: 4px 12px; font-size: 13px; font-weight: bold; margin: 1px 2px; }
.col-orange { background-color: rgba(255,85,0,0.16);    color: #ff5500; border: 2px solid #ff5500;   border-radius: 4px; padding: 4px 12px; font-size: 13px; font-weight: bold; margin: 1px 2px; }

.col-pink:hover   { background-color: rgba(255,0,255,0.36);   color: #fff; }
.col-purple:hover { background-color: rgba(204,0,255,0.36);   color: #fff; }
.col-blue:hover   { background-color: rgba(0,136,255,0.36);   color: #fff; }
.col-green:hover  { background-color: rgba(57,255,20,0.32);   color: #fff; }
.col-yellow:hover { background-color: rgba(255,255,0,0.32);   color: #fff; }
.col-orange:hover { background-color: rgba(255,85,0,0.36);    color: #fff; }

/* Edit dialog */
.dlg-title-e {
    background-color: rgba(255,255,255,0.05);
    border: 2px solid rgba(255,0,255,0.45);
    color: rgba(240,230,255,0.95);
    border-radius: 4px;
    padding: 8px 14px;
    font-size: 17px;
    margin-bottom: 6px;
}
.dlg-body {
    background-color: rgba(255,255,255,0.04);
    border: 2px solid rgba(140,60,220,0.35);
    color: rgba(232,224,245,0.92);
    border-radius: 4px;
    padding: 6px;
    font-size: 15px;
}
.dlg-save {
    background-color: rgba(255,0,255,0.18);
    color: #ff66ff;
    border: 2px solid rgba(255,0,255,0.70);
    border-radius: 4px;
    padding: 8px 28px;
    font-size: 16px;
    font-weight: bold;
    margin-top: 8px;
}
.dlg-save:hover { background-color: rgba(255,0,255,0.38); color: #fff; }
"""


# ── Data ──────────────────────────────────────────────────────────────────────

def load_notes():
    try:
        with open(DATA_FILE) as f: return json.load(f)
    except Exception: return []

def save_notes(notes):
    try:
        with open(DATA_FILE, 'w') as f: json.dump(notes, f, indent=2)
    except Exception: pass


# ── Main window ───────────────────────────────────────────────────────────────

class StickyApp(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NYXUS Stickies")
        self.set_default_size(1100, 720)
        self.notes    = load_notes()
        self.selected = None
        self.drag_id  = None
        self._filter  = ""
        self._build()

    def _build(self):
        css_p = Gtk.CssProvider()
        try:    css_p.load_from_string(CSS)
        except AttributeError: css_p.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_p,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root)

        # ── Toolbar ───────────────────────────────────────────────────────
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.add_css_class("toolbar")

        lbl = Gtk.Label(label="NYXUS STICKIES"); lbl.add_css_class("app-title")
        toolbar.append(lbl)

        self.count_lbl = Gtk.Label(label=""); self.count_lbl.add_css_class("count-lbl")
        toolbar.append(self.count_lbl)

        spacer = Gtk.Box(); spacer.set_hexpand(True); toolbar.append(spacer)

        search = Gtk.Entry(); search.set_placeholder_text("search notes...")
        search.add_css_class("search-e")
        search.connect("changed", self._on_search); toolbar.append(search)

        add_btn = Gtk.Button(label="+ NEW NOTE"); add_btn.add_css_class("add-btn")
        add_btn.connect("clicked", self._add_note); toolbar.append(add_btn)

        del_btn = Gtk.Button(label="✕ DELETE"); del_btn.add_css_class("del-btn")
        del_btn.connect("clicked", self._del_note); toolbar.append(del_btn)

        # ── Theme color bar ───────────────────────────────────────────────
        theme_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        theme_bar.add_css_class("theme-bar")

        tlbl = Gtk.Label(label="NOTE THEME:"); tlbl.add_css_class("theme-lbl")
        theme_bar.append(tlbl)

        css_cls = ["col-pink","col-purple","col-blue","col-green","col-yellow","col-orange"]
        for i, (name, cls) in enumerate(zip(THEME_NAMES, css_cls)):
            btn = Gtk.Button(label=name); btn.add_css_class(cls)
            btn.connect("clicked", self._set_color, i); theme_bar.append(btn)

        root.append(toolbar); root.append(theme_bar)

        # ── Canvas ────────────────────────────────────────────────────────
        self.da = Gtk.DrawingArea()
        self.da.set_hexpand(True); self.da.set_vexpand(True)
        self.da.set_draw_func(self._draw)
        root.append(self.da)

        click = Gtk.GestureClick()
        click.connect("pressed",  self._on_press)
        click.connect("released", self._on_release)
        self.da.add_controller(click)

        drag = Gtk.GestureDrag()
        drag.connect("drag-begin",  self._drag_begin)
        drag.connect("drag-update", self._drag_update)
        drag.connect("drag-end",    self._drag_end)
        self.da.add_controller(drag)

        self._update_count()

    # ── Helpers ───────────────────────────────────────────────────────────

    def _update_count(self):
        n = len(self.notes)
        self.count_lbl.set_label(f"{n} note{'s' if n != 1 else ''}")

    def _hit_test(self, mx, my):
        for n in reversed(self.notes):
            nx, ny = n["x"], n["y"]
            if nx <= mx <= nx + NOTE_W and ny <= my <= ny + NOTE_H:
                return n
        return None

    # ── Actions ───────────────────────────────────────────────────────────

    def _add_note(self, *_):
        w, h = self.da.get_width(), self.da.get_height()
        rng  = _rand.Random()
        cidx = len(self.notes) % len(NOTE_PAPER)
        self.notes.append({
            "id":      str(uuid.uuid4()),
            "title":   f"Note {len(self.notes)+1}",
            "body":    "",
            "color":   cidx,
            "x":       max(20, min(w-NOTE_W-20, rng.randint(60, max(61, w-NOTE_W-60)))),
            "y":       max(20, min(h-NOTE_H-20, rng.randint(60, max(61, h-NOTE_H-60)))),
            "angle":   rng.uniform(-6, 6),
            "pinned":  False,
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
        self._filter = entry.get_text().lower(); self.da.queue_draw()

    # ── Gestures ──────────────────────────────────────────────────────────

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

    # ── Edit dialog ───────────────────────────────────────────────────────

    def _edit_note(self, note):
        dlg = Gtk.Dialog(title="Edit Note", transient_for=self, modal=True)
        dlg.set_default_size(400, 320)

        box = dlg.get_content_area()
        box.set_spacing(8)
        box.set_margin_start(18); box.set_margin_end(18)
        box.set_margin_top(16);   box.set_margin_bottom(16)

        # Title entry
        title_e = Gtk.Entry()
        title_e.set_text(note.get("title", ""))
        title_e.set_placeholder_text("Title…")
        title_e.add_css_class("dlg-title-e")
        box.append(title_e)

        # Body text view
        scroll = Gtk.ScrolledWindow(); scroll.set_vexpand(True)
        tv = Gtk.TextView(); tv.set_wrap_mode(Gtk.WrapMode.WORD)
        tv.add_css_class("dlg-body")
        tv.get_buffer().set_text(note.get("body", ""))
        scroll.set_child(tv); box.append(scroll)

        # Color strip
        color_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        clbl = Gtk.Label(label="Color:"); clbl.add_css_class("theme-lbl")
        color_row.append(clbl)
        css_cls = ["col-pink","col-purple","col-blue","col-green","col-yellow","col-orange"]
        for i, (nm, cls) in enumerate(zip(THEME_NAMES, css_cls)):
            cb = Gtk.Button(label=nm); cb.add_css_class(cls)
            def _pick(b, idx=i): note["color"] = idx; self.da.queue_draw()
            cb.connect("clicked", _pick); color_row.append(cb)
        box.append(color_row)

        # Save button
        save_btn = Gtk.Button(label="✓ SAVE"); save_btn.add_css_class("dlg-save")
        save_btn.set_halign(Gtk.Align.CENTER)
        box.append(save_btn)

        def _save(*_):
            note["title"] = title_e.get_text()
            buf = tv.get_buffer()
            note["body"] = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
            save_notes(self.notes); self.da.queue_draw(); dlg.close()

        save_btn.connect("clicked", _save)
        dlg.present()

    # ── Draw ──────────────────────────────────────────────────────────────

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
                selected=(n["id"] == self.selected),
                created=n.get("created", ""),
                pinned=n.get("pinned", False))

        # Watermark
        cr.select_font_face("Caveat", 0, 0); cr.set_font_size(11)
        cr.set_source_rgba(0.55, 0.40, 0.75, 0.28)
        cr.move_to(14, h - 8)
        cr.show_text("NYXUS Stickies  ·  double-click to edit  ·  drag to move")


class App(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.stickies",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
    def do_activate(self):
        StickyApp(self).present()

App().run()
