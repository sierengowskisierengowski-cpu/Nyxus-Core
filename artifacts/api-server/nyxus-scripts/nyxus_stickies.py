#!/usr/bin/env python3
"""NYXUS Stickies — GTK4, mirrors the web preview exactly."""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio
import json, math, os, random as _rand, uuid
from datetime import datetime
from pathlib import Path

WIN_W, WIN_H = 800, 540
DATA_FILE = str(Path.home() / ".nyxus" / "stickies.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

CARD_W, CARD_H = 210, 220   # matches web: width 210, min-height 200

# Light paper / dark ink — exactly matches web colours
COLORS = [
    {"bg": (0.996, 0.941, 0.541), "ink": (0.165, 0.125, 0.000), "name": "Lemon"},
    {"bg": (0.992, 0.643, 0.686), "ink": (0.165, 0.000, 0.031), "name": "Rose"},
    {"bg": (0.576, 0.773, 0.992), "ink": (0.000, 0.078, 0.157), "name": "Sky"},
    {"bg": (0.525, 0.937, 0.671), "ink": (0.000, 0.133, 0.078), "name": "Mint"},
    {"bg": (0.914, 0.835, 1.000), "ink": (0.102, 0.000, 0.188), "name": "Lavender"},
    {"bg": (0.992, 0.729, 0.455), "ink": (0.165, 0.071, 0.000), "name": "Peach"},
]


# ── Cairo helpers ─────────────────────────────────────────────────────────────

def _wrap(cr, text, max_w, size=14):
    cr.select_font_face("Caveat", 0, 0)
    cr.set_font_size(size)
    if not text:
        return []
    lines, cur = [], ""
    for word in (text or "").split():
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


def draw_note_cairo(cr, w, h, cidx, title, body, angle=0.0,
                    selected=False, pinned=False):
    """Draw one sticky note card — matches web design exactly."""
    c   = COLORS[cidx % len(COLORS)]
    br, bg_c, bb = c["bg"]
    ir, ig, ib   = c["ink"]

    # Slight rotation (same as web transform)
    cr.save()
    cr.translate(w / 2, h / 2)
    cr.rotate(math.radians(angle))
    cr.translate(-w / 2, -h / 2)

    # Drop shadow (web: 4px 6px 20px rgba(0,0,0,.55))
    for sh, sa in [(10, 0.05), (6, 0.10), (3, 0.20), (1, 0.30)]:
        cr.set_source_rgba(0, 0, 0, sa)
        cr.rectangle(sh, sh + 2, w, h)
        cr.fill()

    # Paper fill
    cr.set_source_rgb(br, bg_c, bb)
    cr.rectangle(0, 0, w, h)
    cr.fill()

    # Ruled lines (web: repeating-linear-gradient every 28px starting at 36px)
    cr.set_line_width(0.7)
    for ly in range(36, int(h) - 4, 28):
        cr.set_source_rgba(ir, ig, ib, 0.09)
        cr.move_to(0, ly)
        cr.line_to(w, ly)
        cr.stroke()

    # Header band
    cr.set_source_rgba(ir, ig, ib, 0.10)
    cr.rectangle(0, 0, w, 36)
    cr.fill()
    cr.set_source_rgba(ir, ig, ib, 0.16)
    cr.set_line_width(1.0)
    cr.move_to(0, 36)
    cr.line_to(w, 36)
    cr.stroke()

    # Selected glow
    if selected:
        cr.set_source_rgba(1.0, 0.85, 0.0, 0.80)
        cr.set_line_width(3.5)
        cr.rectangle(-2, -2, w + 4, h + 4)
        cr.stroke()

    # Card border
    cr.set_source_rgba(ir, ig, ib, 0.28)
    cr.set_line_width(1.2)
    cr.rectangle(0, 0, w, h)
    cr.stroke()

    # Folded corner (web shows slight shadow fold)
    corner = 16
    cr.set_source_rgba(ir * 0.55, ig * 0.55, ib * 0.55, 0.50)
    cr.move_to(w - corner, h)
    cr.line_to(w, h - corner)
    cr.line_to(w, h)
    cr.close_path()
    cr.fill()
    cr.set_source_rgba(ir, ig, ib, 0.22)
    cr.set_line_width(0.8)
    cr.move_to(w - corner, h)
    cr.line_to(w, h - corner)
    cr.stroke()

    # Tape strip at top center (web: width 52, height 20, white 45% opacity)
    tw, th_t = 52, 18
    tx = (w - tw) / 2
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.52)
    cr.rectangle(tx, -th_t / 2, tw, th_t)
    cr.fill()
    cr.set_source_rgba(0.7, 0.7, 0.7, 0.22)
    cr.set_line_width(0.5)
    cr.rectangle(tx, -th_t / 2, tw, th_t)
    cr.stroke()

    # Pin badge
    if pinned:
        cr.set_source_rgba(1.0, 0.13, 0.33, 0.92)
        cr.arc(w - 8, 8, 5, 0, math.pi * 2)
        cr.fill()

    # Title (bold, 17px Caveat, dark ink)
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(17)
    t = (title or "Title…")[:24]
    cr.set_source_rgba(ir, ig, ib, 0.95)
    cr.move_to(10, 26)
    cr.show_text(t)

    # Body text
    cr.select_font_face("Caveat", 0, 0)
    lines = _wrap(cr, body or "", w - 22, 14)
    cr.set_source_rgba(ir, ig, ib, 0.78)
    for i, line in enumerate(lines[:5]):
        cr.move_to(10, 52 + i * 27)
        cr.show_text(line)
    if len(lines) > 5:
        cr.set_font_size(11)
        cr.set_source_rgba(ir, ig, ib, 0.40)
        cr.move_to(10, 52 + 5 * 27)
        cr.show_text(f"+ {len(lines) - 5} more…")

    cr.restore()


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


# ── Per-note card widget ──────────────────────────────────────────────────────

class NoteCard(Gtk.DrawingArea):
    """A single sticky note rendered with Cairo — placed in the FlowBox."""

    def __init__(self, note, on_edit_cb, on_select_cb):
        super().__init__()
        self.note       = note
        self._on_edit   = on_edit_cb
        self._on_select = on_select_cb
        self._selected  = False

        # Extra top margin so the tape strip isn't clipped
        self.set_margin_top(12)
        self.set_margin_bottom(4)
        self.set_margin_start(4)
        self.set_margin_end(4)
        self.set_size_request(CARD_W, CARD_H)
        self.set_draw_func(self._draw)

        gc = Gtk.GestureClick()
        gc.set_button(0)
        gc.connect("pressed", self._on_click)
        self.add_controller(gc)

    def set_selected(self, yes: bool):
        self._selected = yes
        self.queue_draw()

    def _on_click(self, g, n_press, x, y):
        self._on_select(self.note["id"])
        if n_press >= 2:
            GLib.idle_add(self._on_edit, self.note["id"])

    def _draw(self, da, cr, w, h, _):
        try:
            draw_note_cairo(
                cr, w, h,
                self.note.get("cidx", 0),
                self.note.get("title", ""),
                self.note.get("body", ""),
                self.note.get("angle", 0.0),
                selected=self._selected,
                pinned=self.note.get("pinned", False),
            )
        except Exception:
            import traceback
            err = traceback.format_exc()
            try:
                with open("/tmp/nyxus-stickies.log", "a") as f:
                    f.write(f"NoteCard draw error:\n{err}\n")
            except Exception:
                pass
            cr.set_source_rgba(1, 0.3, 0.3, 0.9)
            cr.select_font_face("monospace", 0, 0)
            cr.set_font_size(10)
            cr.move_to(4, 14)
            cr.show_text("draw error — see /tmp/nyxus-stickies.log")


# ── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
* { font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', cursive; }
window { background-color: #0a0a12; }

.toolbar {
    background-color: rgba(10,10,20,0.97);
    border-bottom: 2px solid rgba(255,0,255,0.20);
    padding: 0 16px;
    min-height: 56px;
}
.app-title {
    color: #ff00ff;
    font-size: 22px;
    font-weight: bold;
    letter-spacing: 1px;
    text-shadow: 0 0 12px rgba(255,0,255,0.5);
}
.search-box {
    background-color: rgba(255,255,255,0.05);
    border: 1.5px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    color: rgba(255,255,255,0.75);
    font-size: 16px;
    padding: 5px 12px;
    min-width: 140px;
    caret-color: #ff00ff;
}
.search-box:focus { border-color: rgba(255,0,255,0.50); }

.count-badge {
    color: #0088ff;
    font-size: 15px;
    border: 1.5px solid rgba(0,136,255,0.35);
    border-radius: 20px;
    padding: 2px 12px;
    background-color: rgba(0,136,255,0.07);
}
.btn-new {
    background-color: #39ff14;
    color: #000000;
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
.btn-clear:disabled { opacity: 0.28; }

.colorstrip {
    background-color: rgba(0,0,0,0.28);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding: 5px 20px;
    min-height: 32px;
}
.strip-lbl  { color: rgba(255,255,255,0.30); font-size: 14px; }
.strip-clbl { color: rgba(255,255,255,0.40); font-size: 12px; }

.canvas-area {
    background-color: #0a0a12;
    background-image: none;
}

.empty-msg {
    color: rgba(255,255,255,0.22);
    font-size: 22px;
    border: 2px dashed rgba(255,255,255,0.10);
    border-radius: 8px;
    padding: 24px 40px;
}
.btn-create {
    color: #ff00ff;
    font-size: 20px;
    font-weight: bold;
    background-color: rgba(255,0,255,0.09);
    border: 2px solid rgba(255,0,255,0.35);
    border-radius: 6px;
    padding: 10px 32px;
}
.btn-create:hover { background-color: rgba(255,0,255,0.18); }

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
    padding: 8px 28px;
    font-size: 16px;
    font-weight: bold;
}
.dlg-save:hover { background-color: rgba(255,0,255,0.38); color: #ffffff; }
.dlg-cancel {
    color: rgba(255,255,255,0.45);
    background-color: transparent;
    border: 1px solid rgba(255,255,255,0.15);
    border-radius: 4px;
    padding: 8px 16px;
    font-size: 16px;
}
"""


# ── Main window ───────────────────────────────────────────────────────────────

class StickyApp(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NYXUS Stickies")
        self.set_default_size(WIN_W, WIN_H)
        self.set_resizable(True)
        self.notes    = load_notes()
        self._filter  = ""
        self._sel_id  = None
        self._cards   = {}   # note id → NoteCard widget
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

        # ── Toolbar (mirrors web exactly) ────────────────────────────────────
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tb.add_css_class("toolbar")
        root.append(tb)

        logo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
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

        sp = Gtk.Box()
        sp.set_hexpand(True)
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
        cs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        cs.add_css_class("colorstrip")
        root.append(cs)

        lbl = Gtk.Label(label="Colors:")
        lbl.add_css_class("strip-lbl")
        cs.append(lbl)

        for c in COLORS:
            db = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            dot = Gtk.DrawingArea()
            dot.set_size_request(14, 14)
            dot.set_valign(Gtk.Align.CENTER)

            def _mkdot(col):
                def _d(da, cr, w, h, _):
                    cr.set_source_rgb(*col)
                    cr.arc(w/2, h/2, min(w,h)/2-0.5, 0, math.pi*2); cr.fill()
                    cr.set_source_rgba(0,0,0,0.30); cr.set_line_width(1.5)
                    cr.arc(w/2, h/2, min(w,h)/2-0.5, 0, math.pi*2); cr.stroke()
                return _d

            dot.set_draw_func(_mkdot(c["bg"]))
            db.append(dot)
            nl = Gtk.Label(label=c["name"])
            nl.add_css_class("strip-clbl")
            db.append(nl)
            cs.append(db)

        # ── Board (ScrolledWindow + FlowBox) — mirrors web flex-wrap ─────────
        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scroll.add_css_class("canvas-area")
        root.append(scroll)

        # Outer box so we can swap between empty-state and flow
        self._board = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        scroll.set_child(self._board)

        # Empty state panel
        self._empty_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self._empty_box.set_halign(Gtk.Align.CENTER)
        self._empty_box.set_valign(Gtk.Align.CENTER)
        self._empty_box.set_hexpand(True)
        self._empty_box.set_vexpand(True)
        self._empty_lbl = Gtk.Label(label="Board is empty — add your first note!")
        self._empty_lbl.add_css_class("empty-msg")
        self._empty_box.append(self._empty_lbl)
        btn_c = Gtk.Button(label="＋ Create Note")
        btn_c.add_css_class("btn-create")
        btn_c.set_halign(Gtk.Align.CENTER)
        btn_c.connect("clicked", self._on_new)
        self._empty_box.append(btn_c)
        self._board.append(self._empty_box)

        # Flow box for notes (web: display flex, flex-wrap wrap, gap 36px)
        self._flow = Gtk.FlowBox()
        self._flow.set_homogeneous(False)
        self._flow.set_column_spacing(28)
        self._flow.set_row_spacing(28)
        self._flow.set_margin_top(28)
        self._flow.set_margin_start(28)
        self._flow.set_margin_end(28)
        self._flow.set_margin_bottom(28)
        self._flow.set_max_children_per_line(30)
        self._flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._board.append(self._flow)

        self._refresh_board()

    # ── Board management ─────────────────────────────────────────────────────

    def _refresh_board(self):
        """Rebuild the FlowBox to match current notes / filter."""
        # Clear old cards
        while True:
            ch = self._flow.get_first_child()
            if ch is None:
                break
            self._flow.remove(ch)
        self._cards.clear()

        vis = self._visible()
        n   = len(vis)

        # Update count badge
        self._cnt.set_label(f"{n} note{'s' if n != 1 else ''}")
        self._bcl.set_sensitive(len(self.notes) > 0)

        # Toggle empty / flow visibility
        self._empty_box.set_visible(n == 0)
        self._flow.set_visible(n > 0)

        if self._filter and n == 0:
            self._empty_lbl.set_label(
                f'No notes match "{self._filter}"')
        else:
            self._empty_lbl.set_label(
                "Board is empty — add your first note!")

        # Build cards
        for note in vis:
            card = NoteCard(note, self._edit_note, self._on_select)
            card.set_selected(note.get("id") == self._sel_id)
            self._cards[note["id"]] = card
            self._flow.append(card)

    def _visible(self):
        if not self._filter:
            return list(self.notes)
        f = self._filter.lower()
        return [n for n in self.notes
                if f in (n.get("title","") + n.get("body","")).lower()]

    # ── Events ───────────────────────────────────────────────────────────────

    def _on_select(self, nid):
        self._sel_id = nid
        for cid, card in self._cards.items():
            card.set_selected(cid == nid)

    def _on_search(self, entry):
        self._filter = entry.get_text()
        self._refresh_board()

    def _on_new(self, _btn=None):
        note = {
            "id":      str(uuid.uuid4())[:8],
            "title":   "",
            "body":    "",
            "cidx":    _rand.randint(0, len(COLORS) - 1),
            "angle":   _rand.uniform(-3.5, 3.5),
            "pinned":  False,
            "created": datetime.now().isoformat(),
        }
        self.notes.append(note)
        save_notes(self.notes)
        self._sel_id = note["id"]
        self._refresh_board()
        GLib.idle_add(self._edit_note, note["id"])

    def _on_clear(self, _btn=None):
        dlg = Gtk.MessageDialog(
            transient_for=self, modal=True,
            message_type=Gtk.MessageType.WARNING,
            buttons=Gtk.ButtonsType.OK_CANCEL,
            text="Delete all notes?",
        )
        dlg.format_secondary_text("This cannot be undone.")
        dlg.connect("response", self._on_clear_resp)
        dlg.present()

    def _on_clear_resp(self, dlg, resp):
        if resp == Gtk.ResponseType.OK:
            self.notes.clear()
            save_notes(self.notes)
            self._sel_id = None
            self._refresh_board()
        dlg.destroy()

    # ── Edit dialog ───────────────────────────────────────────────────────────

    def _edit_note(self, nid):
        note = next((n for n in self.notes if n["id"] == nid), None)
        if not note:
            return False

        dlg = Gtk.Dialog(title="Edit Note", transient_for=self, modal=True)
        dlg.set_default_size(440, 340)
        box = dlg.get_content_area()
        box.set_spacing(12)
        box.set_margin_top(16); box.set_margin_bottom(16)
        box.set_margin_start(20); box.set_margin_end(20)

        te = Gtk.Entry()
        te.add_css_class("dlg-entry")
        te.set_text(note.get("title", ""))
        te.set_placeholder_text("Title…")
        box.append(te)

        # Color picker
        crow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        crow.set_margin_top(2)
        cl = Gtk.Label(label="Color:")
        cl.add_css_class("strip-lbl")
        crow.append(cl)
        self._dlg_cidx = note.get("cidx", 0)
        cdots = []

        def _mkcdraw(col, idx):
            def _d(da, cr, w, h, _):
                sel = (idx == self._dlg_cidx)
                cr.set_source_rgb(*col)
                cr.arc(w/2, h/2, min(w,h)/2-1, 0, math.pi*2); cr.fill()
                cr.set_line_width(3.0 if sel else 1.5)
                cr.set_source_rgba(0, 0, 0, 0.75 if sel else 0.25)
                cr.arc(w/2, h/2, min(w,h)/2-1, 0, math.pi*2); cr.stroke()
            return _d

        def _mkcclick(idx):
            def _c(g, n, cx, cy):
                self._dlg_cidx = idx
                for d in cdots: d.queue_draw()
            return _c

        for i, c in enumerate(COLORS):
            d = Gtk.DrawingArea()
            d.set_size_request(26, 26)
            d.set_valign(Gtk.Align.CENTER)
            d.set_draw_func(_mkcdraw(c["bg"], i))
            gc = Gtk.GestureClick()
            gc.connect("pressed", _mkcclick(i))
            d.add_controller(gc)
            cdots.append(d)
            crow.append(d)
        box.append(crow)

        # Body
        sv = Gtk.ScrolledWindow()
        sv.set_min_content_height(150)
        sv.set_vexpand(True)
        tv = Gtk.TextView()
        tv.add_css_class("dlg-body")
        tv.set_wrap_mode(Gtk.WrapMode.WORD)
        tv.set_left_margin(8); tv.set_top_margin(6)
        tv.get_buffer().set_text(note.get("body", ""))
        sv.set_child(tv)
        box.append(sv)

        # Pin
        pc = Gtk.CheckButton(label="Pin this note")
        pc.set_active(note.get("pinned", False))
        box.append(pc)

        # Buttons
        br2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        br2.set_halign(Gtk.Align.END)
        bs = Gtk.Button(label="Save"); bs.add_css_class("dlg-save")
        bc2 = Gtk.Button(label="Cancel"); bc2.add_css_class("dlg-cancel")
        br2.append(bs); br2.append(bc2)
        box.append(br2)

        # Delete this note
        br3 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        br3.set_halign(Gtk.Align.START)
        bd = Gtk.Button(label="🗑 Delete Note")
        bd.add_css_class("btn-clear")
        br3.append(bd)
        box.append(br3)

        def _save(_):
            note["title"]  = te.get_text()
            buf            = tv.get_buffer()
            note["body"]   = buf.get_text(buf.get_start_iter(),
                                          buf.get_end_iter(), False)
            note["cidx"]   = self._dlg_cidx
            note["pinned"] = pc.get_active()
            save_notes(self.notes)
            self._refresh_board()
            dlg.destroy()

        def _delete(_):
            self.notes = [n for n in self.notes if n["id"] != nid]
            save_notes(self.notes)
            if self._sel_id == nid:
                self._sel_id = None
            self._refresh_board()
            dlg.destroy()

        bs.connect("clicked", _save)
        te.connect("activate", _save)
        bc2.connect("clicked", lambda _: dlg.destroy())
        bd.connect("clicked", _delete)
        dlg.present()
        return False


# ── Application ───────────────────────────────────────────────────────────────

class App(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.nyxus.stickies",
            flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        StickyApp(self).present()


if __name__ == "__main__":
    App().run()
