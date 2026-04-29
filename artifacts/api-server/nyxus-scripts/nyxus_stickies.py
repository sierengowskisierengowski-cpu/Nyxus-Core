#!/usr/bin/env python3
"""NYXUS Stickies — GTK4, mirrors the web preview design."""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio
import json, math, os, random as _rand, uuid
from datetime import datetime
from pathlib import Path

WIN_W, WIN_H = 780, 520

DATA_FILE = str(Path.home() / ".nyxus" / "stickies.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# Card geometry — matches web (width 210, min-height 200)
TAPE_H   = 14    # space above card for tape strip
CARD_W   = 210
CARD_H   = 218   # card body height
SLOT_H   = TAPE_H + CARD_H   # total vertical slot per note
MARGIN   = 28    # canvas outer padding
GAP      = 28    # space between cards (web: gap 36)

# Light paper / dark ink — identical to web colour palette
COLORS = [
    {"bg": (0.996, 0.941, 0.541), "ink": (0.165, 0.125, 0.000), "name": "Lemon"},
    {"bg": (0.992, 0.643, 0.686), "ink": (0.165, 0.000, 0.031), "name": "Rose"},
    {"bg": (0.576, 0.773, 0.992), "ink": (0.000, 0.078, 0.157), "name": "Sky"},
    {"bg": (0.525, 0.937, 0.671), "ink": (0.000, 0.133, 0.078), "name": "Mint"},
    {"bg": (0.914, 0.835, 1.000), "ink": (0.102, 0.000, 0.188), "name": "Lavender"},
    {"bg": (0.992, 0.729, 0.455), "ink": (0.165, 0.071, 0.000), "name": "Peach"},
]


# ── Cairo drawing ─────────────────────────────────────────────────────────────

def _cols(canvas_w):
    """Number of columns that fit in canvas_w."""
    return max(1, int((canvas_w - MARGIN + GAP) // (CARD_W + GAP)))

def _note_pos(idx, canvas_w):
    """(x, y) top-left of the tape area for the idx-th note."""
    c = _cols(canvas_w)
    col = idx % c
    row = idx // c
    x = MARGIN + col * (CARD_W + GAP)
    y = MARGIN + row * (SLOT_H + GAP)
    return x, y

def _canvas_height(n, canvas_w):
    if n == 0:
        return 400
    c = _cols(canvas_w)
    rows = math.ceil(n / c)
    return MARGIN + rows * (SLOT_H + GAP) + MARGIN

def _wrap(cr, text, max_w, size=14):
    cr.select_font_face("Caveat", 0, 0)
    cr.set_font_size(size)
    if not text:
        return []
    lines, cur = [], ""
    for word in text.split():
        test = (cur + " " + word).strip() if cur else word
        try:
            if cur and cr.text_extents(test).width > max_w:
                lines.append(cur)
                cur = word
            else:
                cur = test
        except Exception:
            cur = test
    if cur:
        lines.append(cur)
    return lines

def draw_note(cr, x, y, cidx, title, body, angle=0.0, selected=False, pinned=False):
    """
    Draw a sticky note card.
    (x, y) is the top-left of the TAPE area (TAPE_H px above the card body).
    """
    c  = COLORS[cidx % len(COLORS)]
    br, bg, bb = c["bg"]
    ir, ig, ib = c["ink"]
    cw, ch = CARD_W, CARD_H
    cx, cy = x, y + TAPE_H   # card body top-left

    # ── Tape strip (white semi-transparent, centered) ──────────────────────
    tw = 52
    tx = x + (cw - tw) / 2
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.52)
    cr.rectangle(tx, y, tw, TAPE_H)
    cr.fill()
    cr.set_source_rgba(0.65, 0.65, 0.65, 0.22)
    cr.set_line_width(0.5)
    cr.rectangle(tx, y, tw, TAPE_H)
    cr.stroke()

    # ── Drop shadow ────────────────────────────────────────────────────────
    for sh, sa in [(8, 0.06), (5, 0.11), (3, 0.20), (1, 0.28)]:
        cr.set_source_rgba(0, 0, 0, sa)
        cr.rectangle(cx + sh, cy + sh + 2, cw, ch)
        cr.fill()

    # ── Paper body ─────────────────────────────────────────────────────────
    cr.set_source_rgb(br, bg, bb)
    cr.rectangle(cx, cy, cw, ch)
    cr.fill()

    # ── Ruled lines (web: every 28px, starting 36px from card top) ─────────
    cr.set_line_width(0.7)
    for ly in range(36, int(ch) - 4, 28):
        cr.set_source_rgba(ir, ig, ib, 0.09)
        cr.move_to(cx, cy + ly)
        cr.line_to(cx + cw, cy + ly)
        cr.stroke()

    # ── Header band ────────────────────────────────────────────────────────
    cr.set_source_rgba(ir, ig, ib, 0.10)
    cr.rectangle(cx, cy, cw, 36)
    cr.fill()
    cr.set_source_rgba(ir, ig, ib, 0.16)
    cr.set_line_width(1.0)
    cr.move_to(cx, cy + 36)
    cr.line_to(cx + cw, cy + 36)
    cr.stroke()

    # ── Selection glow ─────────────────────────────────────────────────────
    if selected:
        cr.set_source_rgba(1.0, 0.85, 0.0, 0.85)
        cr.set_line_width(3.5)
        cr.rectangle(cx - 2, cy - 2, cw + 4, ch + 4)
        cr.stroke()

    # ── Card border ────────────────────────────────────────────────────────
    cr.set_source_rgba(ir, ig, ib, 0.28)
    cr.set_line_width(1.2)
    cr.rectangle(cx, cy, cw, ch)
    cr.stroke()

    # ── Folded corner ──────────────────────────────────────────────────────
    corner = 16
    cr.set_source_rgba(ir * 0.50, ig * 0.50, ib * 0.50, 0.50)
    cr.move_to(cx + cw - corner, cy + ch)
    cr.line_to(cx + cw, cy + ch - corner)
    cr.line_to(cx + cw, cy + ch)
    cr.close_path()
    cr.fill()
    cr.set_source_rgba(ir, ig, ib, 0.22)
    cr.set_line_width(0.8)
    cr.move_to(cx + cw - corner, cy + ch)
    cr.line_to(cx + cw, cy + ch - corner)
    cr.stroke()

    # ── Pin badge ──────────────────────────────────────────────────────────
    if pinned:
        cr.set_source_rgba(1.0, 0.13, 0.33, 0.92)
        cr.arc(cx + cw - 8, cy + 8, 5, 0, math.pi * 2)
        cr.fill()

    # ── Title (bold, dark ink) ─────────────────────────────────────────────
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(17)
    t = (title or "Title…")[:24]
    cr.set_source_rgba(ir, ig, ib, 0.92)
    cr.move_to(cx + 10, cy + 25)
    cr.show_text(t)

    # ── Body text ──────────────────────────────────────────────────────────
    lines = _wrap(cr, body or "", cw - 22, 14)
    cr.set_source_rgba(ir, ig, ib, 0.75)
    for i, line in enumerate(lines[:5]):
        cr.move_to(cx + 10, cy + 52 + i * 27)
        cr.show_text(line)
    if len(lines) > 5:
        cr.select_font_face("Caveat", 0, 0)
        cr.set_font_size(11)
        cr.set_source_rgba(ir, ig, ib, 0.38)
        cr.move_to(cx + 10, cy + 52 + 5 * 27)
        cr.show_text(f"+ {len(lines) - 5} more…")


# ── Data ─────────────────────────────────────────────────────────────────────

def load_notes():
    try:
        with open(DATA_FILE) as f:
            return json.load(f)
    except Exception:
        return []

def save_notes(notes):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(notes, f, indent=2)
    except Exception:
        pass


# ── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
* { font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', cursive; }
window { background-color: #0a0a12; }

.toolbar {
    background-color: rgba(10,10,20,0.97);
    border-bottom: 2px solid rgba(255,0,255,0.20);
    padding: 0 14px;
    min-height: 52px;
}
.app-title {
    color: #ff00ff;
    font-size: 21px;
    font-weight: bold;
    letter-spacing: 1px;
}
.search-box {
    background-color: rgba(255,255,255,0.05);
    border: 1.5px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    color: rgba(255,255,255,0.75);
    font-size: 15px;
    padding: 4px 10px;
    min-width: 130px;
    caret-color: #ff00ff;
}
.search-box:focus { border-color: rgba(255,0,255,0.50); }

.count-badge {
    color: #0088ff;
    font-size: 14px;
    border: 1.5px solid rgba(0,136,255,0.33);
    border-radius: 20px;
    padding: 2px 10px;
    background-color: rgba(0,136,255,0.07);
}
.btn-new {
    background-color: #39ff14;
    color: #000000;
    font-size: 16px;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 5px 14px;
}
.btn-new:hover { background-color: #55ff30; }

.btn-clear {
    color: rgba(255,255,255,0.48);
    background-color: transparent;
    font-size: 15px;
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 6px;
    padding: 3px 10px;
}
.btn-clear:hover { color: #ff7755; border-color: rgba(255,119,85,0.38); }
.btn-clear:disabled { opacity: 0.25; }

.colorstrip {
    background-color: rgba(0,0,0,0.25);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding: 4px 18px;
    min-height: 30px;
}
.strip-lbl  { color: rgba(255,255,255,0.30); font-size: 13px; }
.strip-clbl { color: rgba(255,255,255,0.38); font-size: 11px; }

.dlg-entry {
    background-color: rgba(20,10,35,0.98);
    border: 1.5px solid rgba(255,0,255,0.40);
    border-radius: 4px;
    color: rgba(240,220,255,0.95);
    font-size: 17px;
    padding: 7px 12px;
    caret-color: #ff00ff;
}
.dlg-body {
    background-color: rgba(16,8,26,0.98);
    border: 1.5px solid rgba(140,60,220,0.35);
    border-radius: 4px;
    color: rgba(230,220,245,0.92);
    font-size: 15px;
}
.dlg-save {
    background-color: rgba(255,0,255,0.18);
    color: #ff66ff;
    border: 2px solid rgba(255,0,255,0.75);
    border-radius: 4px;
    padding: 7px 24px;
    font-size: 16px;
    font-weight: bold;
}
.dlg-save:hover { background-color: rgba(255,0,255,0.38); color: #ffffff; }
.dlg-cancel {
    color: rgba(255,255,255,0.42);
    background-color: transparent;
    border: 1px solid rgba(255,255,255,0.14);
    border-radius: 4px;
    padding: 7px 14px;
    font-size: 15px;
}
.dlg-del {
    color: #ff6644;
    background-color: transparent;
    border: 1px solid rgba(255,100,68,0.30);
    border-radius: 4px;
    padding: 7px 14px;
    font-size: 15px;
}
.dlg-del:hover { background-color: rgba(255,100,68,0.12); }
"""


# ── Main window ───────────────────────────────────────────────────────────────

class StickyApp(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NYXUS Stickies")
        self.set_default_size(WIN_W, WIN_H)
        self.set_resizable(True)
        self.notes   = load_notes()
        self._filter = ""
        self._sel    = None   # selected note id
        self._build()

    # ── Layout ───────────────────────────────────────────────────────────────

    def _build(self):
        css_p = Gtk.CssProvider()
        try:
            css_p.load_from_string(CSS)
        except AttributeError:
            css_p.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_p,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(root)

        # ── Toolbar ──────────────────────────────────────────────────────────
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tb.add_css_class("toolbar")
        root.append(tb)

        logo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        logo.set_margin_end(2)
        logo.append(Gtk.Label(label="📌"))
        tl = Gtk.Label(label="NYXUS Stickies")
        tl.add_css_class("app-title")
        logo.append(tl)
        tb.append(logo)

        self._se = Gtk.Entry()
        self._se.set_placeholder_text("search notes…")
        self._se.add_css_class("search-box")
        self._se.connect("changed", self._on_search)
        tb.append(self._se)

        self._cnt = Gtk.Label(label="0 notes")
        self._cnt.add_css_class("count-badge")
        tb.append(self._cnt)

        sp = Gtk.Box(); sp.set_hexpand(True)
        tb.append(sp)

        self._bcl = Gtk.Button(label="🗑 Clear")
        self._bcl.add_css_class("btn-clear")
        self._bcl.connect("clicked", self._on_clear)
        tb.append(self._bcl)

        bn = Gtk.Button(label="＋ New Note")
        bn.add_css_class("btn-new")
        bn.connect("clicked", self._on_new)
        tb.append(bn)

        # ── Color strip ──────────────────────────────────────────────────────
        cs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cs.add_css_class("colorstrip")
        root.append(cs)

        cl = Gtk.Label(label="Colors:")
        cl.add_css_class("strip-lbl")
        cs.append(cl)

        for c in COLORS:
            db = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
            dot = Gtk.DrawingArea()
            dot.set_size_request(13, 13)
            dot.set_valign(Gtk.Align.CENTER)

            def _mkdot(col):
                def _d(da, cr, w, h, _):
                    cr.set_source_rgb(*col)
                    cr.arc(w/2, h/2, min(w,h)/2-0.5, 0, math.pi*2); cr.fill()
                    cr.set_source_rgba(0,0,0,0.28); cr.set_line_width(1.2)
                    cr.arc(w/2, h/2, min(w,h)/2-0.5, 0, math.pi*2); cr.stroke()
                return _d

            dot.set_draw_func(_mkdot(c["bg"]))
            db.append(dot)
            nl = Gtk.Label(label=c["name"])
            nl.add_css_class("strip-clbl")
            db.append(nl)
            cs.append(db)

        # ── Canvas (ScrolledWindow + single DrawingArea) ──────────────────────
        # NEVER horizontal policy forces the DrawingArea to fill the full
        # viewport width — with AUTOMATIC it would get 0-width allocation.
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_hexpand(True)
        self._scroll.set_vexpand(True)
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root.append(self._scroll)

        self._da = Gtk.DrawingArea()
        self._da.set_hexpand(True)
        self._da.set_vexpand(False)   # height driven by set_content_height below
        self._da.set_content_width(WIN_W)
        self._da.set_content_height(400)
        self._da.set_draw_func(self._on_draw)
        self._scroll.set_child(self._da)

        # Input gestures
        gc = Gtk.GestureClick()
        gc.set_button(0)
        gc.connect("pressed", self._on_click)
        self._da.add_controller(gc)

        self._update()

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _visible(self):
        if not self._filter:
            return list(self.notes)
        f = self._filter.lower()
        return [n for n in self.notes
                if f in (n.get("title","") + n.get("body","")).lower()]

    def _update(self):
        vis = self._visible()
        n   = len(vis)
        self._cnt.set_label(f"{n} note{'s' if n != 1 else ''}")
        self._bcl.set_sensitive(len(self.notes) > 0)
        # set_content_height tells the ScrolledWindow how tall the canvas is
        # so vertical scrollbars appear when notes overflow the viewport.
        cw = self._da.get_width() or WIN_W
        needed = _canvas_height(n, cw)
        self._da.set_content_height(max(300, needed))
        self._da.queue_draw()

    def _note_at(self, mx, my):
        """Return the note at canvas coordinate (mx, my), or None."""
        vis = self._visible()
        cw  = self._da.get_width() or WIN_W
        for i, note in enumerate(vis):
            x, y = _note_pos(i, cw)
            cx, cy = x, y + TAPE_H
            if cx <= mx <= cx + CARD_W and cy <= my <= cy + CARD_H:
                return note
        return None

    # ── Canvas draw ──────────────────────────────────────────────────────────

    def _on_draw(self, da, cr, w, h, _):
        try:
            self._draw_inner(cr, w, h)
        except Exception:
            import traceback
            err = traceback.format_exc()
            try:
                open("/tmp/nyxus-stickies.log", "a").write(f"draw error:\n{err}\n")
            except Exception:
                pass
            cr.set_source_rgb(0.08, 0.02, 0.16)
            cr.rectangle(0, 0, w, h); cr.fill()
            cr.set_source_rgba(1, 0.3, 0.3, 0.9)
            cr.select_font_face("monospace", 0, 0)
            cr.set_font_size(11)
            for i, ln in enumerate(err.split("\n")[-10:]):
                cr.move_to(16, 24 + i * 14)
                cr.show_text(ln[:96])

    def _draw_inner(self, cr, w, h):
        # Dark background with faint horizontal rules (matching web)
        cr.set_source_rgb(0.039, 0.039, 0.071)
        cr.rectangle(0, 0, w, h); cr.fill()
        cr.set_line_width(0.8)
        for ly in range(27, h + 1, 28):
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.030)
            cr.move_to(0, ly); cr.line_to(w, ly); cr.stroke()

        vis = self._visible()

        if not vis:
            # Empty state — dashed box + "Board is empty" text (matching web)
            msg  = self._filter and f'No notes match "{self._filter}"' \
                   or "Board is empty — add your first note!"
            cr.select_font_face("Caveat", 0, 0)
            cr.set_font_size(20)
            try:
                ext = cr.text_extents(msg)
                mx  = max(20.0, (w - ext.width) / 2)
                my  = h / 2 - 20
            except Exception:
                mx, my = 40.0, h / 2 - 20
            bw, bh = max(300, w * 0.55), 56
            bx = (w - bw) / 2
            by = my - 28
            cr.set_source_rgba(1, 1, 1, 0.10)
            cr.set_line_width(2)
            cr.set_dash([8, 6], 0)
            cr.rectangle(bx, by, bw, bh); cr.stroke()
            cr.set_dash([], 0)
            cr.set_source_rgba(1, 1, 1, 0.22)
            cr.move_to(max(bx + 20, mx), my); cr.show_text(msg)

            # "+ Create Note" button hint
            cr.select_font_face("Caveat", 0, 1)
            cr.set_font_size(18)
            btn_txt = "+ Create Note"
            try:
                be = cr.text_extents(btn_txt)
                bx2 = (w - be.width - 32) / 2
            except Exception:
                bx2 = w / 2 - 80
            by2 = by + bh + 24
            cr.set_source_rgba(1, 0, 1, 0.35)
            cr.set_line_width(2)
            cr.rectangle(bx2 - 2, by2 - 22, be.width + 36 if True else 180, 36)
            cr.stroke()
            cr.set_source_rgba(1, 0, 1, 0.80)
            cr.move_to(bx2 + 14, by2); cr.show_text(btn_txt)
            return

        for i, note in enumerate(vis):
            nx, ny = _note_pos(i, w)
            draw_note(
                cr, nx, ny,
                note.get("cidx", 0),
                note.get("title", ""),
                note.get("body", ""),
                note.get("angle", 0.0),
                selected=(note.get("id") == self._sel),
                pinned=note.get("pinned", False),
            )

    # ── Interactions ─────────────────────────────────────────────────────────

    def _on_click(self, gesture, n_press, x, y):
        note = self._note_at(x, y)
        if note:
            self._sel = note["id"]
            self._da.queue_draw()
            if n_press >= 2:
                self._edit_note(note["id"])
        else:
            self._sel = None
            self._da.queue_draw()

    def _on_search(self, entry):
        self._filter = entry.get_text()
        self._update()

    def _on_new(self, _=None):
        note = {
            "id":      str(uuid.uuid4())[:8],
            "title":   "",
            "body":    "",
            "cidx":    _rand.randint(0, len(COLORS) - 1),
            "angle":   _rand.uniform(-3.0, 3.0),
            "pinned":  False,
            "created": datetime.now().isoformat(),
        }
        self.notes.append(note)
        save_notes(self.notes)
        self._sel = note["id"]
        self._update()
        # Use idle_add so the canvas draws the new (empty) card before the
        # edit dialog steals focus and freezes the main window.
        GLib.idle_add(self._edit_note, note["id"])

    def _on_clear(self, _=None):
        dlg = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Delete all notes?",
        )
        dlg.format_secondary_text("This cannot be undone.")
        dlg.connect("response", self._clear_resp)
        dlg.present()

    def _clear_resp(self, dlg, resp):
        if resp == Gtk.ResponseType.OK:
            self.notes.clear()
            save_notes(self.notes)
            self._sel = None
            self._update()
        dlg.destroy()

    # ── Edit dialog ──────────────────────────────────────────────────────────

    def _edit_note(self, nid):
        note = next((n for n in self.notes if n["id"] == nid), None)
        if not note:
            return

        dlg = Gtk.Dialog(title="Edit Note", transient_for=self, modal=True)
        dlg.set_default_size(440, 340)
        box = dlg.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(14); box.set_margin_bottom(14)
        box.set_margin_start(18); box.set_margin_end(18)

        te = Gtk.Entry()
        te.add_css_class("dlg-entry")
        te.set_text(note.get("title", ""))
        te.set_placeholder_text("Title…")
        box.append(te)

        # Color picker dots
        crow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        crow.set_margin_top(2)
        cl2 = Gtk.Label(label="Color:"); cl2.add_css_class("strip-lbl")
        crow.append(cl2)
        self._dlg_cidx = note.get("cidx", 0)
        cdots = []

        def _mkcd(col, idx):
            def _d(da, cr, w, h, _):
                sel = (idx == self._dlg_cidx)
                cr.set_source_rgb(*col)
                cr.arc(w/2, h/2, min(w,h)/2-1, 0, math.pi*2); cr.fill()
                cr.set_line_width(3.0 if sel else 1.5)
                cr.set_source_rgba(0,0,0, 0.75 if sel else 0.22)
                cr.arc(w/2, h/2, min(w,h)/2-1, 0, math.pi*2); cr.stroke()
            return _d

        def _mkcc(idx):
            def _c(g, n, cx, cy):
                self._dlg_cidx = idx
                for d in cdots: d.queue_draw()
            return _c

        for i, c in enumerate(COLORS):
            d = Gtk.DrawingArea()
            d.set_size_request(26, 26)
            d.set_valign(Gtk.Align.CENTER)
            d.set_draw_func(_mkcd(c["bg"], i))
            gc = Gtk.GestureClick()
            gc.connect("pressed", _mkcc(i))
            d.add_controller(gc)
            cdots.append(d)
            crow.append(d)
        box.append(crow)

        # Body textarea
        sv = Gtk.ScrolledWindow()
        sv.set_min_content_height(140); sv.set_vexpand(True)
        tv = Gtk.TextView()
        tv.add_css_class("dlg-body")
        tv.set_wrap_mode(Gtk.WrapMode.WORD)
        tv.set_left_margin(8); tv.set_top_margin(6)
        tv.get_buffer().set_text(note.get("body", ""))
        sv.set_child(tv)
        box.append(sv)

        # Pin checkbox
        pc = Gtk.CheckButton(label="📌 Pin this note")
        pc.set_active(note.get("pinned", False))
        box.append(pc)

        # Action buttons row
        brow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        bd = Gtk.Button(label="🗑 Delete")
        bd.add_css_class("dlg-del")
        brow.append(bd)

        sp2 = Gtk.Box(); sp2.set_hexpand(True); brow.append(sp2)

        bc = Gtk.Button(label="Cancel"); bc.add_css_class("dlg-cancel")
        bs = Gtk.Button(label="Save");   bs.add_css_class("dlg-save")
        brow.append(bc); brow.append(bs)
        box.append(brow)

        def _save(_):
            note["title"]  = te.get_text()
            buf            = tv.get_buffer()
            note["body"]   = buf.get_text(buf.get_start_iter(),
                                          buf.get_end_iter(), False)
            note["cidx"]   = self._dlg_cidx
            note["pinned"] = pc.get_active()
            save_notes(self.notes)
            self._update()
            dlg.destroy()

        def _delete(_):
            self.notes = [n for n in self.notes if n["id"] != nid]
            if self._sel == nid:
                self._sel = None
            save_notes(self.notes)
            self._update()
            dlg.destroy()

        bs.connect("clicked", _save)
        te.connect("activate", _save)
        bc.connect("clicked", lambda _: dlg.destroy())
        bd.connect("clicked", _delete)
        dlg.present()


# ── App entry ─────────────────────────────────────────────────────────────────

class App(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.nyxus.stickies",
            flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        StickyApp(self).present()


if __name__ == "__main__":
    App().run()
