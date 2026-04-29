#!/usr/bin/env python3
"""NYXUS Stickies — GTK4 sticky notes matching the web design."""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio
import json, math, os, random as _rand, uuid
from datetime import datetime
from pathlib import Path

WIN_W, WIN_H = 960, 640
DATA_FILE = str(Path.home() / ".nyxus" / "stickies.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

NOTE_W, NOTE_H = 210, 215

# Colors matching the web app exactly (light paper / dark ink)
COLORS = [
    {"bg": (0.996, 0.941, 0.541), "ink": (0.165, 0.125, 0.000), "name": "Lemon"},
    {"bg": (0.992, 0.643, 0.686), "ink": (0.165, 0.000, 0.031), "name": "Rose"},
    {"bg": (0.576, 0.773, 0.992), "ink": (0.000, 0.078, 0.157), "name": "Sky"},
    {"bg": (0.525, 0.937, 0.671), "ink": (0.000, 0.133, 0.078), "name": "Mint"},
    {"bg": (0.914, 0.835, 1.000), "ink": (0.102, 0.000, 0.188), "name": "Lavender"},
    {"bg": (0.992, 0.729, 0.455), "ink": (0.165, 0.071, 0.000), "name": "Peach"},
]

NEON_PINK  = "#ff00ff"
NEON_GREEN = "#39ff14"
NEON_BLUE  = "#0088ff"


# ── Cairo note drawing ────────────────────────────────────────────────────────

def _rng2(x, y):
    return _rand.Random(int(abs(x) * 3 + abs(y) * 7) % 65535)

def _wrap(cr, text, max_w, size=14):
    cr.select_font_face("Caveat", 0, 0)
    cr.set_font_size(size)
    if not text:
        return []
    lines, cur = [], ""
    for word in text.split(" "):
        test = (cur + " " + word).strip()
        try:
            if cr.text_extents(test).width > max_w and cur:
                lines.append(cur)
                cur = word
            else:
                cur = test
        except Exception:
            cur = test
    if cur:
        lines.append(cur)
    return lines

def draw_note(cr, x, y, cidx, title, body, angle, selected=False, pinned=False):
    c = COLORS[cidx % len(COLORS)]
    br, bg, bb = c["bg"]
    ir, ig, ib = c["ink"]
    nw, nh = NOTE_W, NOTE_H

    cr.save()
    cr.translate(x + nw / 2, y + nh / 2)
    cr.rotate(math.radians(angle))
    cr.translate(-nw / 2, -nh / 2)

    # Drop shadow
    for sh, sa in [(12, 0.06), (7, 0.11), (4, 0.20), (2, 0.30)]:
        cr.set_source_rgba(0, 0, 0, sa)
        cr.rectangle(sh, sh + 3, nw, nh)
        cr.fill()

    # Paper body
    cr.set_source_rgb(br, bg, bb)
    cr.rectangle(0, 0, nw, nh)
    cr.fill()

    # Ruled lines (every 28px starting at 40px, matching web)
    cr.set_line_width(0.7)
    for ly in range(40, int(nh) - 8, 28):
        cr.set_source_rgba(ir, ig, ib, 0.09)
        cr.move_to(0, ly)
        cr.line_to(nw, ly)
        cr.stroke()

    # Header band
    cr.set_source_rgba(ir, ig, ib, 0.10)
    cr.rectangle(0, 0, nw, 36)
    cr.fill()
    cr.set_source_rgba(ir, ig, ib, 0.18)
    cr.set_line_width(1.0)
    cr.move_to(0, 36)
    cr.line_to(nw, 36)
    cr.stroke()

    # Selected highlight
    if selected:
        cr.set_source_rgba(1.0, 0.9, 0.0, 0.75)
        cr.set_line_width(3.0)
        cr.rectangle(-2, -2, nw + 4, nh + 4)
        cr.stroke()

    # Border
    cr.set_source_rgba(ir, ig, ib, 0.35)
    cr.set_line_width(1.2)
    cr.rectangle(0, 0, nw, nh)
    cr.stroke()

    # Folded corner
    corner = 18
    cr.set_source_rgba(ir * 0.55, ig * 0.55, ib * 0.55, 0.55)
    cr.move_to(nw - corner, nh)
    cr.line_to(nw, nh - corner)
    cr.line_to(nw, nh)
    cr.close_path()
    cr.fill()
    cr.set_source_rgba(ir, ig, ib, 0.28)
    cr.set_line_width(0.8)
    cr.move_to(nw - corner, nh)
    cr.line_to(nw, nh - corner)
    cr.stroke()

    # Tape strip (white, centered at top)
    tw, th_tape = 52, 18
    tx = (nw - tw) / 2
    cr.set_source_rgba(1.0, 1.0, 1.0, 0.52)
    cr.rectangle(tx, -th_tape / 2, tw, th_tape)
    cr.fill()
    cr.set_source_rgba(0.7, 0.7, 0.7, 0.25)
    cr.set_line_width(0.5)
    cr.rectangle(tx, -th_tape / 2, tw, th_tape)
    cr.stroke()

    # Pin badge (red dot top-right when pinned)
    if pinned:
        cr.set_source_rgba(1.0, 0.13, 0.33, 0.92)
        cr.arc(nw - 8, 8, 5, 0, math.pi * 2)
        cr.fill()

    # Title
    cr.select_font_face("Caveat", 0, 1)
    cr.set_font_size(17)
    t = (title or "Note")[:24]
    cr.set_source_rgba(ir, ig, ib, 0.95)
    cr.move_to(10, 26)
    cr.show_text(t)

    # Body text
    lines = _wrap(cr, body or "", nw - 22, 14)
    cr.set_source_rgba(ir, ig, ib, 0.82)
    for i, line in enumerate(lines[:5]):
        cr.move_to(10, 52 + i * 27)
        cr.show_text(line)
    if len(lines) > 5:
        cr.select_font_face("Caveat", 0, 0)
        cr.set_font_size(11)
        cr.set_source_rgba(ir, ig, ib, 0.42)
        cr.move_to(10, 52 + 5 * 27)
        cr.show_text(f"+ {len(lines) - 5} more")

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


# ── CSS ──────────────────────────────────────────────────────────────────────

CSS = """
* { font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', cursive; }
window { background-color: #08080e; }

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
}
.search-box {
    background-color: rgba(255,255,255,0.05);
    border: 1.5px solid rgba(255,255,255,0.12);
    border-radius: 6px;
    color: rgba(255,255,255,0.75);
    font-size: 16px;
    padding: 5px 12px;
    min-width: 200px;
    caret-color: #ff00ff;
}
.search-box:focus {
    border-color: rgba(255,0,255,0.45);
    outline: none;
}
.count-badge {
    color: #0088ff;
    font-size: 15px;
    border: 1.5px solid rgba(0,136,255,0.33);
    border-radius: 20px;
    padding: 2px 12px;
    background-color: rgba(0,136,255,0.067);
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
.btn-clear:disabled { opacity: 0.30; }

.colorstrip {
    background-color: rgba(0,0,0,0.25);
    border-bottom: 1px solid rgba(255,255,255,0.05);
    padding: 6px 20px;
    min-height: 34px;
}
.strip-lbl {
    color: rgba(255,255,255,0.30);
    font-size: 14px;
}
.strip-clbl {
    color: rgba(255,255,255,0.40);
    font-size: 12px;
}

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
        self.notes = load_notes()
        self._filter = ""
        self._selected = None
        self._drag = None
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

        # ── Toolbar ─────────────────────────────────────────────────────────
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        toolbar.add_css_class("toolbar")
        root.append(toolbar)

        logo = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        logo.set_margin_end(4)
        pin_lbl = Gtk.Label(label="📌")
        logo.append(pin_lbl)
        title_lbl = Gtk.Label(label="NYXUS Stickies")
        title_lbl.add_css_class("app-title")
        logo.append(title_lbl)
        toolbar.append(logo)

        self._search_entry = Gtk.Entry()
        self._search_entry.set_placeholder_text("search notes…")
        self._search_entry.add_css_class("search-box")
        self._search_entry.connect("changed", self._on_search)
        toolbar.append(self._search_entry)

        self._count_lbl = Gtk.Label(label="0 notes")
        self._count_lbl.add_css_class("count-badge")
        toolbar.append(self._count_lbl)

        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        toolbar.append(spacer)

        self._btn_clear = Gtk.Button(label="🗑 Clear")
        self._btn_clear.add_css_class("btn-clear")
        self._btn_clear.connect("clicked", self._on_clear)
        toolbar.append(self._btn_clear)

        btn_new = Gtk.Button(label="＋ New Note")
        btn_new.add_css_class("btn-new")
        btn_new.connect("clicked", self._on_new)
        toolbar.append(btn_new)

        # ── Color strip ──────────────────────────────────────────────────────
        strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        strip.add_css_class("colorstrip")
        root.append(strip)

        clbl = Gtk.Label(label="Colors:")
        clbl.add_css_class("strip-lbl")
        strip.append(clbl)

        for c in COLORS:
            dot_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            dot = Gtk.DrawingArea()
            dot.set_size_request(14, 14)
            dot.set_valign(Gtk.Align.CENTER)
            r, g, b = c["bg"]

            def _make_dot(col):
                def _draw(da, cr, w, h, _):
                    cr.set_source_rgb(*col)
                    cr.arc(w / 2, h / 2, min(w, h) / 2 - 0.5, 0, math.pi * 2)
                    cr.fill()
                    cr.set_source_rgba(0, 0, 0, 0.30)
                    cr.set_line_width(1.5)
                    cr.arc(w / 2, h / 2, min(w, h) / 2 - 0.5, 0, math.pi * 2)
                    cr.stroke()
                return _draw

            dot.set_draw_func(_make_dot((r, g, b)))
            dot_box.append(dot)

            nlbl = Gtk.Label(label=c["name"])
            nlbl.add_css_class("strip-clbl")
            dot_box.append(nlbl)
            strip.append(dot_box)

        # ── Canvas area ──────────────────────────────────────────────────────
        scroll = Gtk.ScrolledWindow()
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        root.append(scroll)

        self._da = Gtk.DrawingArea()
        self._da.set_hexpand(True)
        self._da.set_vexpand(True)
        self._da.set_draw_func(self._draw_canvas)
        scroll.set_child(self._da)

        # Click (single + double)
        click = Gtk.GestureClick()
        click.set_button(0)
        click.connect("pressed", self._on_press)
        self._da.add_controller(click)

        # Drag
        drag = Gtk.GestureDrag()
        drag.connect("drag-begin",  self._on_drag_begin)
        drag.connect("drag-update", self._on_drag_update)
        drag.connect("drag-end",    self._on_drag_end)
        self._da.add_controller(drag)

        self._update_ui()

    # ── Data helpers ─────────────────────────────────────────────────────────

    def _visible_notes(self):
        if not self._filter:
            return list(self.notes)
        f = self._filter.lower()
        return [n for n in self.notes
                if f in (n.get("title", "") + n.get("body", "")).lower()]

    def _update_ui(self):
        vis = self._visible_notes()
        n = len(vis)
        self._count_lbl.set_label(f"{n} note{'s' if n != 1 else ''}")
        self._btn_clear.set_sensitive(len(self.notes) > 0)
        self._da.queue_draw()

    # ── Canvas draw ──────────────────────────────────────────────────────────

    def _draw_canvas(self, da, cr, w, h, _):
        try:
            self._draw_canvas_inner(cr, w, h)
        except Exception:
            import traceback
            err = traceback.format_exc()
            try:
                with open("/tmp/nyxus-stickies.log", "a") as f:
                    f.write(f"canvas crash:\n{err}\n")
            except Exception:
                pass
            # Show error directly on screen
            cr.set_source_rgb(0.08, 0.02, 0.16)
            cr.rectangle(0, 0, w, h)
            cr.fill()
            cr.set_source_rgba(1.0, 0.30, 0.30, 0.95)
            cr.select_font_face("monospace", 0, 0)
            cr.set_font_size(12)
            for i, line in enumerate(err.split("\n")[-12:]):
                cr.move_to(20, 30 + i * 15)
                cr.show_text(line[:92])

    def _draw_canvas_inner(self, cr, w, h):
        # Dark background with faint horizontal lines (matching web)
        cr.set_source_rgb(0.039, 0.039, 0.071)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        cr.set_line_width(0.8)
        for ly in range(27, h + 1, 28):
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.032)
            cr.move_to(0, ly)
            cr.line_to(w, ly)
            cr.stroke()

        visible = self._visible_notes()

        if not visible:
            msg = self._filter and f'No notes match "{self._filter}"' or \
                  "Board is empty — add your first note!"
            cr.select_font_face("Caveat", 0, 0)
            cr.set_font_size(22)
            try:
                ext = cr.text_extents(msg)
                mx = max(20.0, (w - ext.width) / 2)
                my = (h - 40) / 2
            except Exception:
                mx, my = 40.0, h / 2
            cr.set_source_rgba(1, 1, 1, 0.10)
            cr.set_line_width(2)
            cr.set_dash([8, 6], 0)
            cr.rectangle(mx - 40, my - 36, max(200, w * 0.6), 64)
            cr.stroke()
            cr.set_dash([], 0)
            cr.set_source_rgba(1, 1, 1, 0.22)
            cr.move_to(mx, my)
            cr.show_text(msg)
            return

        for note in visible:
            draw_note(
                cr,
                note.get("x", 40),
                note.get("y", 40),
                note.get("cidx", 0),
                note.get("title", ""),
                note.get("body", ""),
                note.get("angle", 0.0),
                selected=(note.get("id") == self._selected),
                pinned=note.get("pinned", False),
            )

    # ── Interactions ─────────────────────────────────────────────────────────

    def _note_at(self, mx, my):
        for note in reversed(self.notes):
            x, y = note.get("x", 40), note.get("y", 40)
            if x <= mx <= x + NOTE_W and y <= my <= y + NOTE_H:
                return note
        return None

    def _on_press(self, gesture, n_press, x, y):
        note = self._note_at(x, y)
        if note:
            self._selected = note["id"]
            if n_press >= 2:
                GLib.idle_add(self._edit_note, note["id"])
        else:
            self._selected = None
        self._da.queue_draw()

    def _on_drag_begin(self, gesture, sx, sy):
        note = self._note_at(sx, sy)
        if note:
            self._drag = {
                "id": note["id"],
                "ox": note.get("x", 40),
                "oy": note.get("y", 40),
            }
        else:
            self._drag = None

    def _on_drag_update(self, gesture, dx, dy):
        if not self._drag:
            return
        nid = self._drag["id"]
        for n in self.notes:
            if n["id"] == nid:
                n["x"] = max(0, self._drag["ox"] + dx)
                n["y"] = max(0, self._drag["oy"] + dy)
                break
        self._da.queue_draw()

    def _on_drag_end(self, gesture, dx, dy):
        if self._drag:
            save_notes(self.notes)
            self._drag = None

    def _on_search(self, entry):
        self._filter = entry.get_text()
        self._update_ui()

    def _on_new(self, btn):
        w = self.get_width() or WIN_W
        h = self.get_height() or WIN_H
        rng = _rand.Random()
        note = {
            "id":      str(uuid.uuid4())[:8],
            "title":   "New Note",
            "body":    "",
            "cidx":    rng.randint(0, len(COLORS) - 1),
            "x":       rng.randint(40, max(50, w - NOTE_W - 60)),
            "y":       rng.randint(40, max(50, h - NOTE_H - 80)),
            "angle":   rng.uniform(-4.0, 4.0),
            "pinned":  False,
            "created": datetime.now().isoformat(),
        }
        self.notes.append(note)
        save_notes(self.notes)
        self._selected = note["id"]
        self._update_ui()
        GLib.idle_add(self._edit_note, note["id"])

    def _on_clear(self, btn):
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
            self._selected = None
            self._update_ui()
        dlg.destroy()

    def _edit_note(self, nid):
        note = next((n for n in self.notes if n["id"] == nid), None)
        if not note:
            return False

        dlg = Gtk.Dialog(title="Edit Note", transient_for=self, modal=True)
        dlg.set_default_size(440, 340)
        box = dlg.get_content_area()
        box.set_spacing(12)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(20)
        box.set_margin_end(20)

        # Title
        te = Gtk.Entry()
        te.add_css_class("dlg-entry")
        te.set_text(note.get("title", ""))
        te.set_placeholder_text("Title…")
        box.append(te)

        # Color row
        crow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        crow.set_margin_top(4)
        cl = Gtk.Label(label="Color:")
        cl.add_css_class("strip-lbl")
        crow.append(cl)
        self._dlg_cidx = note.get("cidx", 0)
        cdots = []
        for i, c in enumerate(COLORS):
            dot = Gtk.DrawingArea()
            dot.set_size_request(24, 24)
            dot.set_valign(Gtk.Align.CENTER)
            cdots.append(dot)

        def _make_cdraw(col, idx, dots_ref):
            def _draw(da, cr, w, h, _):
                sel = (idx == self._dlg_cidx)
                cr.set_source_rgb(*col)
                cr.arc(w / 2, h / 2, min(w, h) / 2 - 1, 0, math.pi * 2)
                cr.fill()
                if sel:
                    cr.set_source_rgba(0, 0, 0, 0.75)
                    cr.set_line_width(3)
                    cr.arc(w / 2, h / 2, min(w, h) / 2 - 1, 0, math.pi * 2)
                    cr.stroke()
                else:
                    cr.set_source_rgba(0, 0, 0, 0.25)
                    cr.set_line_width(1.5)
                    cr.arc(w / 2, h / 2, min(w, h) / 2 - 1, 0, math.pi * 2)
                    cr.stroke()
            return _draw

        def _make_cclick(idx, dots_ref):
            def _click(g, n, cx, cy):
                self._dlg_cidx = idx
                for d in dots_ref:
                    d.queue_draw()
            return _click

        for i, (dot, c) in enumerate(zip(cdots, COLORS)):
            dot.set_draw_func(_make_cdraw(c["bg"], i, cdots))
            gc = Gtk.GestureClick()
            gc.connect("pressed", _make_cclick(i, cdots))
            dot.add_controller(gc)
            crow.append(dot)

        box.append(crow)

        # Body
        sv = Gtk.ScrolledWindow()
        sv.set_min_content_height(150)
        sv.set_vexpand(True)
        tv = Gtk.TextView()
        tv.add_css_class("dlg-body")
        tv.set_wrap_mode(Gtk.WrapMode.WORD)
        tv.set_left_margin(8)
        tv.set_top_margin(6)
        tv.get_buffer().set_text(note.get("body", ""))
        sv.set_child(tv)
        box.append(sv)

        # Pin checkbox
        pin_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        pin_check = Gtk.CheckButton(label="Pin this note")
        pin_check.set_active(note.get("pinned", False))
        pin_box.append(pin_check)
        box.append(pin_box)

        # Buttons
        brow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        brow.set_halign(Gtk.Align.END)
        bs = Gtk.Button(label="Save")
        bs.add_css_class("dlg-save")
        bc = Gtk.Button(label="Cancel")
        bc.add_css_class("dlg-cancel")
        brow.append(bs)
        brow.append(bc)
        box.append(brow)

        def _save(_):
            note["title"]  = te.get_text() or "Note"
            buf            = tv.get_buffer()
            note["body"]   = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
            note["cidx"]   = self._dlg_cidx
            note["pinned"] = pin_check.get_active()
            save_notes(self.notes)
            self._update_ui()
            dlg.destroy()

        bs.connect("clicked", _save)
        te.connect("activate", _save)
        bc.connect("clicked", lambda _: dlg.destroy())
        dlg.present()
        return False


# ── App entry ────────────────────────────────────────────────────────────────

class App(Gtk.Application):
    def __init__(self):
        super().__init__(
            application_id="com.nyxus.stickies",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

    def do_activate(self):
        win = StickyApp(self)
        win.present()


if __name__ == "__main__":
    App().run()
