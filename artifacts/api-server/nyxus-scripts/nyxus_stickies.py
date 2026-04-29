#!/usr/bin/env python3
"""NYXUS Stickies — GTK4, Cairo-rendered cards in a FlowBox layout.

Mirrors the web preview design pixel-by-pixel:
  • Rotated paper notes with light pastel colours and dark ink text
  • Masking-tape strip stuck to the top of every card
  • Faint ruled lines on every note (repeating horizontals)
  • Soft drop shadow + inset highlight, matching the web's box-shadow
  • Empty-state with dashed box + neon "+ Create Note" button
"""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio
import json, math, os, random as _rand, uuid
from datetime import datetime
from pathlib import Path

# ── Window / layout constants ───────────────────────────────────────────────
WIN_W, WIN_H = 760, 500

CARD_W       = 210                           # web: width 210
CARD_H       = 218                           # web: min-height 200, +18 for header
TAPE_W       = 52                            # web: width 52
TAPE_OVER    = 10                            # tape extends 10px above the card
SHADOW_PAD   = 12                            # padding around card for drop shadow
TOTAL_W      = CARD_W + SHADOW_PAD * 2       # full DrawingArea width
TOTAL_H      = TAPE_OVER + CARD_H + SHADOW_PAD * 2  # full DrawingArea height
BOARD_PAD    = 32                            # padding around the board
BOARD_GAP    = 36                            # gap between cards (web: gap 36)

DATA_FILE = str(Path.home() / ".nyxus" / "stickies.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

# ── Paper colours (web's NYXUS_COLORS / INK / LINE_COLOR) ────────────────────
COLORS = [
    {"bg": (0.996, 0.941, 0.541), "ink": (0.165, 0.125, 0.000), "name": "Lemon"},
    {"bg": (0.992, 0.643, 0.686), "ink": (0.165, 0.000, 0.031), "name": "Rose"},
    {"bg": (0.576, 0.773, 0.992), "ink": (0.000, 0.078, 0.157), "name": "Sky"},
    {"bg": (0.525, 0.937, 0.671), "ink": (0.000, 0.133, 0.078), "name": "Mint"},
    {"bg": (0.914, 0.835, 1.000), "ink": (0.102, 0.000, 0.188), "name": "Lavender"},
    {"bg": (0.992, 0.729, 0.455), "ink": (0.165, 0.071, 0.000), "name": "Peach"},
]


# ── Persistence ──────────────────────────────────────────────────────────────

def load_notes():
    try:
        with open(DATA_FILE) as f:
            data = json.load(f)
            # Migrate old data
            for n in data:
                n.setdefault("angle", _rand.uniform(-3.0, 3.0))
                n.setdefault("cidx", 0)
                n.setdefault("pinned", False)
            return data
    except Exception:
        return []

def save_notes(notes):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(notes, f, indent=2)
    except Exception:
        pass


# ── Per-note Cairo card (Gtk.DrawingArea wrapped for FlowBox) ───────────────

class NoteCard(Gtk.DrawingArea):
    def __init__(self, note, on_select, on_edit):
        super().__init__()
        self.note     = note
        self._on_sel  = on_select
        self._on_edit = on_edit
        self._sel     = False

        # CRITICAL: set BOTH so every GTK4 version respects the size.
        self.set_size_request(TOTAL_W, TOTAL_H)
        try:
            self.set_content_width(TOTAL_W)
            self.set_content_height(TOTAL_H)
        except Exception:
            pass
        self.set_hexpand(False)
        self.set_vexpand(False)
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.START)
        self.set_draw_func(self._draw)

        gc = Gtk.GestureClick()
        gc.set_button(1)
        gc.connect("pressed", self._press)
        self.add_controller(gc)

    def set_selected(self, sel: bool):
        if sel != self._sel:
            self._sel = sel
            self.queue_draw()

    def _press(self, gesture, n_press, x, y):
        self._on_sel(self.note["id"])
        if n_press >= 2:
            self._on_edit(self.note["id"])

    # ── Cairo render ─────────────────────────────────────────────────────────

    def _draw(self, area, cr, w, h, _data):
        try:
            self._draw_inner(cr, w, h)
        except Exception:
            import traceback
            err = traceback.format_exc()
            try:
                with open("/tmp/nyxus-stickies.log", "a") as f:
                    f.write(f"[card draw] {err}\n")
            except Exception:
                pass
            cr.set_source_rgb(0.6, 0.0, 0.0)
            cr.rectangle(0, 0, w, h); cr.fill()

    def _draw_inner(self, cr, w, h):
        cidx = self.note.get("cidx", 0) % len(COLORS)
        c    = COLORS[cidx]
        br, bg, bb = c["bg"]
        ir, ig, ib = c["ink"]
        title  = self.note.get("title",  "") or "Title…"
        body   = self.note.get("body",   "") or "Write something…"
        angle  = self.note.get("angle",  0.0)
        pinned = self.note.get("pinned", False)

        # Card body coords (within the larger DrawingArea)
        card_x = SHADOW_PAD
        card_y = SHADOW_PAD + TAPE_OVER
        cw, ch = CARD_W, CARD_H

        # ── Apply rotation around the card centre ─────────────────────────
        cx, cy = card_x + cw / 2, card_y + ch / 2
        cr.save()
        cr.translate(cx, cy)
        cr.rotate(angle * math.pi / 180.0)
        cr.translate(-cx, -cy)

        # ── Drop shadow (multiple soft layers) ────────────────────────────
        for off, alpha in [(8, 0.08), (5, 0.14), (3, 0.22), (1, 0.32)]:
            cr.set_source_rgba(0, 0, 0, alpha)
            cr.rectangle(card_x + off, card_y + off + 2, cw, ch)
            cr.fill()

        # ── Paper body ────────────────────────────────────────────────────
        cr.set_source_rgb(br, bg, bb)
        cr.rectangle(card_x, card_y, cw, ch)
        cr.fill()

        # ── Inset highlight (top-left, like web's box-shadow inset) ───────
        cr.set_source_rgba(1, 1, 1, 0.25)
        cr.set_line_width(1.0)
        cr.move_to(card_x + 0.5, card_y + 0.5)
        cr.line_to(card_x + cw - 0.5, card_y + 0.5)
        cr.move_to(card_x + 0.5, card_y + 0.5)
        cr.line_to(card_x + 0.5, card_y + ch - 0.5)
        cr.stroke()

        # ── Ruled horizontal lines (web: every 28px, starting 36px down) ──
        line_a = 0.08
        cr.set_source_rgba(ir, ig, ib, line_a)
        cr.set_line_width(0.7)
        ly = 36
        while ly < ch - 2:
            cr.move_to(card_x, card_y + ly)
            cr.line_to(card_x + cw, card_y + ly)
            cr.stroke()
            ly += 28

        # ── Header divider ────────────────────────────────────────────────
        cr.set_source_rgba(ir, ig, ib, 0.18)
        cr.set_line_width(1.0)
        cr.move_to(card_x, card_y + 36)
        cr.line_to(card_x + cw, card_y + 36)
        cr.stroke()

        # ── Folded corner (subtle) ────────────────────────────────────────
        fold = 14
        cr.set_source_rgba(ir * 0.4, ig * 0.4, ib * 0.4, 0.30)
        cr.move_to(card_x + cw - fold, card_y + ch)
        cr.line_to(card_x + cw, card_y + ch - fold)
        cr.line_to(card_x + cw, card_y + ch)
        cr.close_path()
        cr.fill()

        # ── Card border ───────────────────────────────────────────────────
        cr.set_source_rgba(ir, ig, ib, 0.22)
        cr.set_line_width(1.0)
        cr.rectangle(card_x + 0.5, card_y + 0.5, cw - 1, ch - 1)
        cr.stroke()

        # ── Title (bold Caveat) ───────────────────────────────────────────
        cr.set_source_rgba(ir, ig, ib, 0.95)
        cr.select_font_face("Caveat", 0, 1)
        cr.set_font_size(19)
        cr.move_to(card_x + 12, card_y + 26)
        try:
            t = title
            ext = cr.text_extents(t)
            if ext.width > cw - 24:
                while t and cr.text_extents(t + "…").width > cw - 24:
                    t = t[:-1]
                t = t + "…"
            cr.show_text(t)
        except Exception:
            cr.show_text(title[:24])

        # ── Body (Caveat regular, line-height 28px) ───────────────────────
        cr.set_source_rgba(ir, ig, ib, 0.78)
        cr.select_font_face("Caveat", 0, 0)
        cr.set_font_size(16)
        max_line_w = cw - 24
        lines = self._wrap(cr, body, max_line_w)
        max_lines = (ch - 56) // 28
        for i, line in enumerate(lines[:max_lines]):
            cr.move_to(card_x + 12, card_y + 64 + i * 28)
            cr.show_text(line)
        if len(lines) > max_lines:
            cr.set_source_rgba(ir, ig, ib, 0.42)
            cr.set_font_size(13)
            cr.move_to(card_x + 12, card_y + 64 + max_lines * 28 - 4)
            cr.show_text(f"+ {len(lines) - max_lines} more…")

        # ── Pin badge (top-right red dot if pinned) ───────────────────────
        if pinned:
            cr.set_source_rgba(1.0, 0.13, 0.33, 0.95)
            cr.arc(card_x + cw - 8, card_y + 8, 6, 0, math.pi * 2)
            cr.fill()
            cr.set_source_rgba(1, 1, 1, 0.85)
            cr.set_line_width(1.5)
            cr.arc(card_x + cw - 8, card_y + 8, 6, 0, math.pi * 2)
            cr.stroke()

        # ── Selection glow ────────────────────────────────────────────────
        if self._sel:
            cr.set_source_rgba(1.0, 0.84, 0.0, 0.95)
            cr.set_line_width(3.0)
            cr.rectangle(card_x - 3, card_y - 3, cw + 6, ch + 6)
            cr.stroke()

        cr.restore()

        # ── Tape strip (NOT rotated — sits flat on top, web style) ────────
        # Drawn AFTER restore so rotation doesn't apply to the tape; the tape
        # is rotated with the card by re-applying the rotation, which gives
        # the natural look of tape stuck to a tilted note.
        cr.save()
        cr.translate(cx, cy)
        cr.rotate(angle * math.pi / 180.0)
        cr.translate(-cx, -cy)

        tx = card_x + (cw - TAPE_W) / 2
        ty = card_y - TAPE_OVER
        # Tape shadow
        cr.set_source_rgba(0, 0, 0, 0.18)
        cr.rectangle(tx + 1, ty + 2, TAPE_W, 20)
        cr.fill()
        # Tape body — translucent white masking tape
        cr.set_source_rgba(1, 1, 1, 0.55)
        cr.rectangle(tx, ty, TAPE_W, 20)
        cr.fill()
        # Subtle horizontal stripes (real masking-tape texture)
        cr.set_source_rgba(0, 0, 0, 0.04)
        for i in range(0, 20, 4):
            cr.rectangle(tx, ty + i, TAPE_W, 2)
            cr.fill()
        # Tape edge
        cr.set_source_rgba(0, 0, 0, 0.16)
        cr.set_line_width(0.5)
        cr.rectangle(tx + 0.25, ty + 0.25, TAPE_W - 0.5, 19.5)
        cr.stroke()

        cr.restore()


    @staticmethod
    def _wrap(cr, text, max_w):
        if not text:
            return []
        out, cur = [], ""
        for word in text.replace("\r", "").split("\n"):
            if not word:
                if cur:
                    out.append(cur); cur = ""
                out.append("")
                continue
            for w in word.split(" "):
                test = (cur + " " + w).strip() if cur else w
                try:
                    if cur and cr.text_extents(test).width > max_w:
                        out.append(cur); cur = w
                    else:
                        cur = test
                except Exception:
                    cur = test
            if cur:
                out.append(cur); cur = ""
        if cur:
            out.append(cur)
        return out


# ── CSS for chrome (toolbar, color strip, empty state, dialog) ──────────────

CSS = """
* { font-family: 'Caveat', 'Patrick Hand', cursive; }
window { background-color: #0a0a12; }

.toolbar {
    background-color: rgba(10,10,20,0.96);
    border-bottom: 2px solid rgba(255,0,255,0.20);
    padding: 0 18px;
    min-height: 56px;
}
.app-title {
    color: #ff00ff;
    font-size: 22px;
    font-weight: bold;
    letter-spacing: 1px;
    text-shadow: 0 0 12px rgba(255,0,255,0.55);
}
.search-box {
    background-color: rgba(255,255,255,0.05);
    border: 1.5px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    color: rgba(255,255,255,0.78);
    font-size: 16px;
    padding: 5px 10px;
    min-width: 160px;
}
.search-box:focus { border-color: rgba(255,0,255,0.55); }
.count-badge {
    color: #0088ff;
    font-size: 15px;
    border: 1.5px solid rgba(0,136,255,0.40);
    border-radius: 20px;
    padding: 2px 12px;
    background-color: rgba(0,136,255,0.07);
}
.btn-new {
    background-color: #39ff14;
    color: #000;
    font-size: 17px;
    font-weight: bold;
    border: none;
    border-radius: 6px;
    padding: 6px 18px;
}
.btn-new:hover { background-color: #55ff30; }
.btn-clear {
    color: rgba(255,255,255,0.50);
    background-color: transparent;
    font-size: 16px;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 6px;
    padding: 4px 12px;
}
.btn-clear:hover { color: #ff7755; border-color: rgba(255,119,85,0.40); }
.btn-clear:disabled { opacity: 0.25; }

.colorstrip {
    background-color: rgba(0,0,0,0.25);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding: 6px 20px;
    min-height: 30px;
}
.strip-lbl  { color: rgba(255,255,255,0.30); font-size: 14px; }
.strip-clbl { color: rgba(255,255,255,0.40); font-size: 12px; }

.empty-msg {
    color: rgba(255,255,255,0.22);
    font-size: 22px;
    border: 2px dashed rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 24px 40px;
}
.btn-create {
    color: #ff00ff;
    background-color: rgba(255,0,255,0.10);
    border: 2px solid rgba(255,0,255,0.55);
    border-radius: 6px;
    font-size: 20px;
    font-weight: bold;
    padding: 10px 32px;
    margin-top: 18px;
}
.btn-create:hover { background-color: rgba(255,0,255,0.22); }

.dlg-entry {
    background-color: rgba(20,10,35,0.98);
    border: 1.5px solid rgba(255,0,255,0.40);
    border-radius: 4px;
    color: rgba(240,220,255,0.95);
    font-size: 17px;
    padding: 7px 12px;
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
.dlg-save:hover { background-color: rgba(255,0,255,0.40); color: #fff; }
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
"""


# ── Main window ─────────────────────────────────────────────────────────────

class StickyApp(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NYXUS Stickies")
        self.set_default_size(WIN_W, WIN_H)
        self.set_resizable(True)
        self.notes   = load_notes()
        self._filter = ""
        self._sel    = None
        self._cards  = {}
        self._build()

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

        # Toolbar
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tb.add_css_class("toolbar")
        root.append(tb)

        logo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        logo.append(Gtk.Label(label="📌"))
        tlbl = Gtk.Label(label="NYXUS Stickies")
        tlbl.add_css_class("app-title")
        logo.append(tlbl)
        tb.append(logo)

        self._se = Gtk.Entry()
        self._se.set_placeholder_text("search notes…")
        self._se.add_css_class("search-box")
        self._se.connect("changed", self._on_search)
        tb.append(self._se)

        self._cnt = Gtk.Label(label="0 notes")
        self._cnt.add_css_class("count-badge")
        tb.append(self._cnt)

        sp = Gtk.Box(); sp.set_hexpand(True); tb.append(sp)

        self._bcl = Gtk.Button(label="🗑 Clear")
        self._bcl.add_css_class("btn-clear")
        self._bcl.connect("clicked", self._on_clear)
        tb.append(self._bcl)

        bn = Gtk.Button(label="＋ New Note")
        bn.add_css_class("btn-new")
        bn.connect("clicked", self._on_new)
        tb.append(bn)

        # Color strip
        cs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cs.add_css_class("colorstrip")
        root.append(cs)
        cl = Gtk.Label(label="Colors:")
        cl.add_css_class("strip-lbl")
        cs.append(cl)
        for c in COLORS:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            dot = Gtk.DrawingArea()
            dot.set_size_request(14, 14)
            dot.set_valign(Gtk.Align.CENTER)
            def _mkd(rgb):
                def _fn(da, cr, w, h, _):
                    cr.set_source_rgb(*rgb)
                    cr.arc(w/2, h/2, min(w,h)/2 - 0.5, 0, math.pi*2); cr.fill()
                    cr.set_source_rgba(0,0,0,0.32); cr.set_line_width(1.2)
                    cr.arc(w/2, h/2, min(w,h)/2 - 0.5, 0, math.pi*2); cr.stroke()
                return _fn
            dot.set_draw_func(_mkd(c["bg"]))
            row.append(dot)
            nl = Gtk.Label(label=c["name"]); nl.add_css_class("strip-clbl")
            row.append(nl)
            cs.append(row)

        # Board (ScrolledWindow with FlowBox + Empty state)
        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True); scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root.append(scroll)

        board = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        board.set_hexpand(True); board.set_vexpand(True)
        scroll.set_child(board)

        # Empty state
        self._empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._empty.set_halign(Gtk.Align.CENTER)
        self._empty.set_valign(Gtk.Align.CENTER)
        self._empty.set_hexpand(True); self._empty.set_vexpand(True)
        em = Gtk.Label(label="Board is empty — add your first note!")
        em.add_css_class("empty-msg"); em.set_halign(Gtk.Align.CENTER)
        self._empty.append(em)
        bc2 = Gtk.Button(label="+ Create Note")
        bc2.add_css_class("btn-create")
        bc2.set_halign(Gtk.Align.CENTER)
        bc2.connect("clicked", self._on_new)
        self._empty.append(bc2)
        board.append(self._empty)

        # FlowBox for notes
        self._flow = Gtk.FlowBox()
        self._flow.set_homogeneous(False)
        self._flow.set_column_spacing(BOARD_GAP)
        self._flow.set_row_spacing(BOARD_GAP)
        self._flow.set_margin_top(BOARD_PAD)
        self._flow.set_margin_bottom(BOARD_PAD)
        self._flow.set_margin_start(BOARD_PAD)
        self._flow.set_margin_end(BOARD_PAD)
        self._flow.set_max_children_per_line(50)
        self._flow.set_min_children_per_line(1)
        self._flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flow.set_hexpand(True); self._flow.set_vexpand(True)
        self._flow.set_valign(Gtk.Align.START)
        board.append(self._flow)

        self._refresh()

    def _visible(self):
        if not self._filter:
            return list(self.notes)
        f = self._filter.lower()
        return [n for n in self.notes
                if f in (n.get("title","") + n.get("body","")).lower()]

    def _refresh(self):
        vis = self._visible()
        n   = len(vis)
        self._cnt.set_label(f"{n} note{'s' if n != 1 else ''}")
        self._bcl.set_sensitive(len(self.notes) > 0)

        # Clear all FlowBox children
        while True:
            child = self._flow.get_child_at_index(0)
            if child is None:
                break
            self._flow.remove(child)
        self._cards.clear()

        empty = (n == 0)
        self._empty.set_visible(empty)
        self._flow.set_visible(not empty)

        for note in vis:
            card = NoteCard(note, self._on_select, self._edit_note)
            card.set_selected(note["id"] == self._sel)
            self._cards[note["id"]] = card
            self._flow.append(card)

    def _on_select(self, nid):
        self._sel = nid
        for cid, card in self._cards.items():
            card.set_selected(cid == nid)

    def _on_search(self, entry):
        self._filter = entry.get_text()
        self._refresh()

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
        self._refresh()
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
            self.notes.clear(); save_notes(self.notes)
            self._sel = None; self._refresh()
        dlg.destroy()

    # ── Edit dialog ─────────────────────────────────────────────────────────

    def _edit_note(self, nid):
        note = next((n for n in self.notes if n["id"] == nid), None)
        if not note:
            return False

        dlg = Gtk.Dialog(title="Edit Note", transient_for=self, modal=True)
        dlg.set_default_size(440, 360)
        box = dlg.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(14); box.set_margin_bottom(14)
        box.set_margin_start(18); box.set_margin_end(18)

        te = Gtk.Entry()
        te.add_css_class("dlg-entry")
        te.set_text(note.get("title",""))
        te.set_placeholder_text("Title…")
        box.append(te)

        crow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        crow.set_margin_top(2)
        cl2 = Gtk.Label(label="Color:"); cl2.add_css_class("strip-lbl")
        crow.append(cl2)
        self._dlg_cidx = note.get("cidx", 0)
        cdots = []

        def _mkdf(rgb, idx):
            def _draw(da, cr, w, h, _):
                cr.set_source_rgb(*rgb)
                cr.arc(w/2, h/2, min(w,h)/2 - 1.5, 0, math.pi*2); cr.fill()
                sel = (idx == self._dlg_cidx)
                cr.set_line_width(3.5 if sel else 1.5)
                cr.set_source_rgba(0,0,0, 0.80 if sel else 0.22)
                cr.arc(w/2, h/2, min(w,h)/2 - 1.5, 0, math.pi*2); cr.stroke()
            return _draw

        def _mkcc(idx):
            def _click(g, n, cx, cy):
                self._dlg_cidx = idx
                for d in cdots: d.queue_draw()
            return _click

        for i, c in enumerate(COLORS):
            d = Gtk.DrawingArea()
            d.set_size_request(28, 28)
            d.set_valign(Gtk.Align.CENTER)
            d.set_draw_func(_mkdf(c["bg"], i))
            gc = Gtk.GestureClick()
            gc.connect("pressed", _mkcc(i))
            d.add_controller(gc)
            cdots.append(d)
            crow.append(d)
        box.append(crow)

        sv = Gtk.ScrolledWindow()
        sv.set_min_content_height(140); sv.set_vexpand(True)
        tv = Gtk.TextView()
        tv.add_css_class("dlg-body")
        tv.set_wrap_mode(Gtk.WrapMode.WORD)
        tv.set_left_margin(8); tv.set_top_margin(6)
        tv.get_buffer().set_text(note.get("body",""))
        sv.set_child(tv)
        box.append(sv)

        pc = Gtk.CheckButton(label="📌 Pin this note")
        pc.set_active(note.get("pinned", False))
        box.append(pc)

        brow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bd = Gtk.Button(label="🗑 Delete"); bd.add_css_class("dlg-del")
        sp2 = Gtk.Box(); sp2.set_hexpand(True)
        bc = Gtk.Button(label="Cancel");   bc.add_css_class("dlg-cancel")
        bs = Gtk.Button(label="Save");     bs.add_css_class("dlg-save")
        brow.append(bd); brow.append(sp2); brow.append(bc); brow.append(bs)
        box.append(brow)

        def _save(_):
            note["title"]  = te.get_text()
            buf            = tv.get_buffer()
            note["body"]   = buf.get_text(buf.get_start_iter(),
                                          buf.get_end_iter(), False)
            note["cidx"]   = self._dlg_cidx
            note["pinned"] = pc.get_active()
            save_notes(self.notes)
            self._refresh()
            dlg.destroy()

        def _delete(_):
            self.notes = [n for n in self.notes if n["id"] != nid]
            if self._sel == nid: self._sel = None
            save_notes(self.notes)
            self._refresh()
            dlg.destroy()

        bs.connect("clicked", _save)
        te.connect("activate", _save)
        bc.connect("clicked", lambda _: dlg.destroy())
        bd.connect("clicked", _delete)
        dlg.present()
        return False


class App(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.nyxus.stickies",
            flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        StickyApp(self).present()


if __name__ == "__main__":
    App().run()
