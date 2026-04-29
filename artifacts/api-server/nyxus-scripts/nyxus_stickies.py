#!/usr/bin/env python3
"""NYXUS Stickies — GTK4, mirrors the web preview design (pure-widget approach)."""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio, Pango
import json, math, os, random as _rand, uuid
from datetime import datetime
from pathlib import Path

WIN_W, WIN_H = 760, 500
DATA_FILE = str(Path.home() / ".nyxus" / "stickies.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

CARD_W  = 210
CARD_H  = 218
TAPE_H  = 14

# Paper bg / dark ink — matches web palette
COLORS = [
    {"bg": "#fef08a", "ink": "#2a2000", "name": "Lemon"},
    {"bg": "#fda4af", "ink": "#2a0008", "name": "Rose"},
    {"bg": "#93c5fd", "ink": "#001428", "name": "Sky"},
    {"bg": "#86efac", "ink": "#002214", "name": "Mint"},
    {"bg": "#e9d5ff", "ink": "#1a0030", "name": "Lavender"},
    {"bg": "#fdba74", "ink": "#2a1200", "name": "Peach"},
]
COLOR_DOTS = [
    (0.996,0.941,0.541),
    (0.992,0.643,0.686),
    (0.576,0.773,0.992),
    (0.525,0.937,0.671),
    (0.914,0.835,1.000),
    (0.992,0.729,0.455),
]
CNAMES = ["lemon","rose","sky","mint","lavender","peach"]


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


def _make_css():
    lines = ["""
* { font-family: 'Caveat', 'Patrick Hand', cursive; }
window { background-color: #0a0a12; }

.toolbar {
    background-color: rgba(10,10,20,0.97);
    border-bottom: 2px solid rgba(255,0,255,0.20);
    padding: 0 12px;
    min-height: 52px;
}
.app-title { color: #ff00ff; font-size: 21px; font-weight: bold; }

.search-box {
    background-color: rgba(255,255,255,0.05);
    border: 1.5px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    color: rgba(255,255,255,0.75);
    font-size: 15px;
    padding: 4px 10px;
    min-width: 120px;
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
.btn-clear:hover { color: #ff7755; }
.btn-clear:disabled { opacity: 0.25; }

.colorstrip {
    background-color: rgba(0,0,0,0.25);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding: 4px 16px;
    min-height: 28px;
}
.strip-lbl  { color: rgba(255,255,255,0.30); font-size: 13px; }
.strip-clbl { color: rgba(255,255,255,0.38); font-size: 11px; }

/* ── Canvas area ── */
.canvas-area {
    background-color: #0a0a12;
}

/* ── Empty state ── */
.empty-box {
    border: 2px solid rgba(255,255,255,0.12);
    border-radius: 8px;
    padding: 24px 48px;
    margin: 60px auto;
}
.empty-msg { color: rgba(255,255,255,0.22); font-size: 20px; }
.btn-create {
    color: #ff00ff;
    background-color: rgba(255,0,255,0.08);
    border: 2px solid rgba(255,0,255,0.60);
    border-radius: 6px;
    font-size: 18px;
    font-weight: bold;
    padding: 8px 28px;
    margin-top: 14px;
}
.btn-create:hover { background-color: rgba(255,0,255,0.22); }

/* ── Note tape ── */
.note-tape {
    background-color: rgba(225, 222, 210, 0.68);
    border-left: 0.5px solid rgba(160,155,130,0.22);
    border-right: 0.5px solid rgba(160,155,130,0.22);
    min-width: 52px;
    min-height: 14px;
}

/* ── Note cards (one class per colour) ── */
.note-card {
    border-radius: 2px;
    min-width: 210px;
    min-height: 218px;
}
"""]

    for i, c in enumerate(COLORS):
        nm = CNAMES[i]
        bg = c["bg"]
        ink = c["ink"]
        # Slightly darkened ink for header band (10% opacity over paper)
        lines.append(f"""
.note-{nm} {{ background-color: {bg}; }}
.note-title-{nm} {{
    color: {ink};
    font-size: 17px;
    font-weight: bold;
    padding-left: 10px;
    padding-top: 8px;
    padding-bottom: 4px;
}}
.note-body-{nm} {{
    color: {ink};
    font-size: 14px;
    opacity: 0.80;
    padding-left: 10px;
    padding-top: 8px;
}}
.note-header-{nm} {{
    background-color: {bg};
    opacity: 0.90;
    border-bottom: 1px solid {ink}29;
    min-height: 36px;
}}
""")

    lines.append("""
.note-selected {
    outline: 3px solid rgba(255,215,0,0.90);
    outline-offset: -3px;
}
.note-pin {
    color: #ff2255;
    font-size: 14px;
    padding-right: 8px;
    padding-top: 6px;
}

/* ── Edit dialog ── */
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
.dlg-save:hover { background-color: rgba(255,0,255,0.38); color: #fff; }
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
""")
    return "\n".join(lines)


class NoteCard(Gtk.Box):
    """A single sticky note card — pure GTK widget, no Cairo."""

    def __init__(self, note, on_select_cb, on_edit_cb):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._nid      = note["id"]
        self._on_sel   = on_select_cb
        self._on_edit  = on_edit_cb
        self.set_size_request(CARD_W, TAPE_H + CARD_H)
        self.set_halign(Gtk.Align.START)
        self.set_valign(Gtk.Align.START)

        cidx = note.get("cidx", 0) % len(COLORS)
        nm   = CNAMES[cidx]

        # ── Tape strip (centered horizontally) ────────────────────────────
        tape_row = Gtk.Box()
        tape_row.set_size_request(CARD_W, TAPE_H)
        tape_row.set_halign(Gtk.Align.FILL)

        tape = Gtk.Box()
        tape.add_css_class("note-tape")
        tape.set_size_request(52, TAPE_H)
        tape.set_halign(Gtk.Align.CENTER)
        tape.set_hexpand(False)
        tape_row.append(tape)
        self.append(tape_row)

        # ── Card body ──────────────────────────────────────────────────────
        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        card.add_css_class("note-card")
        card.add_css_class(f"note-{nm}")
        card.set_hexpand(True)
        card.set_vexpand(True)
        self._card = card

        # Header row (title + optional pin badge)
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hdr.add_css_class(f"note-header-{nm}")

        title_txt = note.get("title","") or "Title…"
        tl = Gtk.Label(label=title_txt)
        tl.add_css_class(f"note-title-{nm}")
        tl.set_xalign(0.0)
        tl.set_hexpand(True)
        tl.set_ellipsize(Pango.EllipsizeMode.END)
        hdr.append(tl)

        if note.get("pinned"):
            pin = Gtk.Label(label="📌")
            pin.add_css_class("note-pin")
            hdr.append(pin)

        card.append(hdr)

        # Body text
        body_txt = note.get("body","") or "Write something…"
        bl = Gtk.Label(label=body_txt)
        bl.add_css_class(f"note-body-{nm}")
        bl.set_xalign(0.0)
        bl.set_yalign(0.0)
        bl.set_wrap(True)
        bl.set_wrap_mode(Pango.WrapMode.WORD)
        bl.set_lines(5)
        bl.set_ellipsize(Pango.EllipsizeMode.END)
        bl.set_hexpand(True)
        bl.set_vexpand(True)
        card.append(bl)

        self.append(card)

        # ── Click / double-click ───────────────────────────────────────────
        gc = Gtk.GestureClick()
        gc.set_button(1)
        gc.connect("pressed", self._on_press)
        self.add_controller(gc)

    def _on_press(self, gesture, n_press, x, y):
        self._on_sel(self._nid)
        if n_press >= 2:
            self._on_edit(self._nid)

    def set_selected(self, sel: bool):
        if sel:
            self._card.add_css_class("note-selected")
        else:
            self._card.remove_css_class("note-selected")


class StickyApp(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NYXUS Stickies")
        self.set_default_size(WIN_W, WIN_H)
        self.set_resizable(True)
        self.notes   = load_notes()
        self._filter = ""
        self._sel    = None
        self._cards  = {}   # id → NoteCard
        self._build()

    # ─────────────────────────────────────────────────────────────────────────

    def _build(self):
        css_p = Gtk.CssProvider()
        css   = _make_css()
        try:
            css_p.load_from_string(css)
        except AttributeError:
            css_p.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css_p,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.set_child(root)

        # ── Toolbar ──────────────────────────────────────────────────────────
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tb.add_css_class("toolbar")
        root.append(tb)

        logo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
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

        sp = Gtk.Box(); sp.set_hexpand(True); tb.append(sp)

        self._bcl = Gtk.Button(label="🗑 Clear")
        self._bcl.add_css_class("btn-clear")
        self._bcl.connect("clicked", self._on_clear)
        tb.append(self._bcl)

        bn = Gtk.Button(label="＋ New Note")
        bn.add_css_class("btn-new")
        bn.connect("clicked", self._on_new)
        tb.append(bn)

        # ── Colour strip ─────────────────────────────────────────────────────
        cs = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cs.add_css_class("colorstrip")
        root.append(cs)

        cl = Gtk.Label(label="Colors:"); cl.add_css_class("strip-lbl")
        cs.append(cl)

        for i, c in enumerate(COLORS):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
            dot = Gtk.DrawingArea()
            dot.set_size_request(13, 13)
            dot.set_valign(Gtk.Align.CENTER)

            def _mkd(rgb):
                def _fn(da, cr, w, h, _):
                    r, g, b = rgb
                    cr.set_source_rgb(r, g, b)
                    cr.arc(w/2, h/2, min(w,h)/2-0.5, 0, math.pi*2); cr.fill()
                    cr.set_source_rgba(0,0,0,0.28); cr.set_line_width(1.2)
                    cr.arc(w/2, h/2, min(w,h)/2-0.5, 0, math.pi*2); cr.stroke()
                return _fn

            dot.set_draw_func(_mkd(COLOR_DOTS[i]))
            row.append(dot)
            nl = Gtk.Label(label=c["name"]); nl.add_css_class("strip-clbl")
            row.append(nl)
            cs.append(row)

        # ── Canvas: ScrolledWindow → Box (canvas-area) → (empty OR FlowBox) ──
        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        root.append(scroll)

        self._canvas = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._canvas.add_css_class("canvas-area")
        self._canvas.set_hexpand(True)
        self._canvas.set_vexpand(True)
        scroll.set_child(self._canvas)

        # Empty state
        self._empty = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._empty.set_halign(Gtk.Align.CENTER)
        self._empty.set_valign(Gtk.Align.CENTER)
        self._empty.set_hexpand(True)
        self._empty.set_vexpand(True)

        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        inner.add_css_class("empty-box")
        inner.set_halign(Gtk.Align.CENTER)
        em = Gtk.Label(label="Board is empty — add your first note!")
        em.add_css_class("empty-msg")
        inner.append(em)
        bc2 = Gtk.Button(label="+ Create Note")
        bc2.add_css_class("btn-create")
        bc2.set_halign(Gtk.Align.CENTER)
        bc2.connect("clicked", self._on_new)
        inner.append(bc2)
        self._empty.append(inner)
        self._canvas.append(self._empty)

        # FlowBox for notes
        self._flow = Gtk.FlowBox()
        self._flow.set_homogeneous(False)
        self._flow.set_column_spacing(28)
        self._flow.set_row_spacing(28)
        self._flow.set_margin_top(28)
        self._flow.set_margin_start(28)
        self._flow.set_margin_end(28)
        self._flow.set_margin_bottom(28)
        self._flow.set_max_children_per_line(20)
        self._flow.set_min_children_per_line(1)
        self._flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self._flow.set_hexpand(True)
        self._canvas.append(self._flow)

        self._refresh()

    # ─────────────────────────────────────────────────────────────────────────

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

        # Remove all existing cards
        while True:
            child = self._flow.get_child_at_index(0)
            if child is None:
                break
            self._flow.remove(child)
        self._cards.clear()

        show_empty = (n == 0)
        self._empty.set_visible(show_empty)
        self._flow.set_visible(not show_empty)

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
            "pinned":  False,
            "created": datetime.now().isoformat(),
        }
        self.notes.append(note)
        save_notes(self.notes)
        self._sel = note["id"]
        self._refresh()
        GLib.idle_add(self.edit_note, note["id"])

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

    # ── Edit dialog ───────────────────────────────────────────────────────────

    def _edit_note(self, nid):
        self.edit_note(nid)

    def edit_note(self, nid):
        note = next((n for n in self.notes if n["id"] == nid), None)
        if not note:
            return False   # idle_add: don't repeat

        dlg = Gtk.Dialog(title="Edit Note", transient_for=self, modal=True)
        dlg.set_default_size(440, 340)
        box = dlg.get_content_area()
        box.set_spacing(10)
        box.set_margin_top(14); box.set_margin_bottom(14)
        box.set_margin_start(18); box.set_margin_end(18)

        te = Gtk.Entry()
        te.add_css_class("dlg-entry")
        te.set_text(note.get("title",""))
        te.set_placeholder_text("Title…")
        box.append(te)

        # Color picker
        crow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        crow.set_margin_top(2)
        cl2 = Gtk.Label(label="Color:"); cl2.add_css_class("strip-lbl")
        crow.append(cl2)
        self._dlg_cidx = note.get("cidx", 0)
        cdots = []

        def _mkdf(rgb, idx):
            def _draw(da, cr, w, h, _):
                r, g, b = rgb
                cr.set_source_rgb(r, g, b)
                cr.arc(w/2, h/2, min(w,h)/2-1.5, 0, math.pi*2); cr.fill()
                sel = (idx == self._dlg_cidx)
                cr.set_line_width(3.5 if sel else 1.5)
                cr.set_source_rgba(0,0,0, 0.80 if sel else 0.22)
                cr.arc(w/2, h/2, min(w,h)/2-1.5, 0, math.pi*2); cr.stroke()
            return _draw

        def _mkcc(idx):
            def _click(g, n, cx, cy):
                self._dlg_cidx = idx
                for d in cdots: d.queue_draw()
            return _click

        for i in range(len(COLORS)):
            d = Gtk.DrawingArea()
            d.set_size_request(28, 28)
            d.set_valign(Gtk.Align.CENTER)
            d.set_draw_func(_mkdf(COLOR_DOTS[i], i))
            gc = Gtk.GestureClick()
            gc.connect("pressed", _mkcc(i))
            d.add_controller(gc)
            cdots.append(d)
            crow.append(d)
        box.append(crow)

        sv = Gtk.ScrolledWindow()
        sv.set_min_content_height(140)
        sv.set_vexpand(True)
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
        return False   # idle_add: don't repeat


class App(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.nyxus.stickies",
            flags=Gio.ApplicationFlags.FLAGS_NONE)

    def do_activate(self):
        StickyApp(self).present()


if __name__ == "__main__":
    App().run()
