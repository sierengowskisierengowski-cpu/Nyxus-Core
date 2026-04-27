#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Stickies — Cairo board with rotated neon notes                ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
import json, uuid, os, math, random

DATA_FILE = os.path.expanduser("~/.nyxus/stickies.json")
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

PALETTE = ["#ff00ff", "#cc00ff", "#0088ff", "#39ff14", "#ffff00", "#ff5500"]
NOTE_W, NOTE_H = 210, 158
PAD = 28
COLS = 2

def hex_rgb(h):
    h = h.lstrip('#')
    return int(h[0:2],16)/255, int(h[2:4],16)/255, int(h[4:6],16)/255

def wrap_text(cr, text, max_w, size=10):
    cr.set_font_size(size)
    if not text:
        return []
    lines = []
    cur = ""
    for word in text.split(' '):
        test = (cur + ' ' + word).strip()
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

def glow_text(cr, x, y, text, r, g, b, size=12, bold=False):
    cr.select_font_face("JetBrains Mono", 0, 1 if bold else 0)
    cr.set_font_size(size)
    for dx, dy, a in [(-1,-1,0.18),( 1,-1,0.18),(-1, 1,0.18),( 1, 1,0.18),
                       (-2, 0,0.08),( 2, 0,0.08),( 0,-2,0.08),( 0, 2,0.08)]:
        cr.set_source_rgba(r, g, b, a)
        cr.move_to(x+dx, y+dy)
        cr.show_text(text)
    cr.set_source_rgba(r, g, b, 1.0)
    cr.move_to(x, y)
    cr.show_text(text)


CSS = b"""
* { font-family: 'JetBrains Mono', 'Monospace', monospace; }
window { background-color: #030206; color: #e8e0f5; }

.header {
    background-color: rgba(7,3,15,0.96);
    border-bottom: 1px solid rgba(255,0,255,0.3);
    padding: 7px 14px;
    min-height: 44px;
}
.app-title {
    color: #ff00ff;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 3px;
}
.note-count {
    color: #0088ff;
    font-size: 10px;
    border: 1px solid rgba(0,136,255,0.4);
    padding: 1px 7px;
    margin-left: 8px;
    border-radius: 2px;
}
.btn-new {
    background-color: rgba(255,0,255,0.08);
    color: #ff00ff;
    border: 1px solid #ff00ff;
    border-radius: 2px;
    padding: 4px 12px;
    font-size: 11px;
    font-weight: bold;
    letter-spacing: 1px;
}
.btn-new:hover { background-color: rgba(255,0,255,0.22); }
.btn-purge {
    background-color: transparent;
    color: #ff5500;
    border: 1px solid rgba(255,85,0,0.45);
    border-radius: 2px;
    padding: 4px 10px;
    font-size: 11px;
}
.btn-purge:hover { background-color: rgba(255,85,0,0.15); }

.editor-win { background-color: #07030f; }
.editor-title-entry {
    background-color: transparent;
    color: #ff00ff;
    font-size: 13px;
    font-weight: bold;
    letter-spacing: 1px;
    border: none;
    border-bottom: 1px solid rgba(255,0,255,0.25);
    border-radius: 0;
    padding: 10px 14px;
    box-shadow: none;
    caret-color: #ff00ff;
}
.editor-title-entry text { background-color: transparent; color: #ff00ff; }
.editor-body-view {
    background-color: transparent;
    color: #e8e0f5;
    font-size: 12px;
    caret-color: #cc00ff;
}
.editor-body-view text { background-color: transparent; }
.swatch-bar {
    background-color: rgba(0,0,0,0.55);
    padding: 7px 12px;
    border-top: 1px solid rgba(255,255,255,0.07);
    border-bottom: 1px solid rgba(255,255,255,0.07);
}
.swatch-btn {
    min-width: 18px;
    min-height: 18px;
    border-radius: 50%;
    padding: 0;
    border: 1px solid rgba(255,255,255,0.25);
    margin: 0 2px;
}
.swatch-btn:hover { border: 2px solid rgba(255,255,255,0.85); }
.act-bar {
    background-color: rgba(0,0,0,0.3);
    padding: 7px 12px;
}
.editor-btn-done {
    background-color: rgba(255,0,255,0.1);
    color: #ff00ff;
    border: 1px solid rgba(255,0,255,0.7);
    border-radius: 2px;
    padding: 4px 16px;
    font-size: 11px;
    font-weight: bold;
}
.editor-btn-done:hover { background-color: rgba(255,0,255,0.28); }
.editor-btn-pin {
    background-color: transparent;
    color: #ffff00;
    border: 1px solid rgba(255,255,0,0.4);
    border-radius: 2px;
    padding: 4px 10px;
    font-size: 11px;
}
.editor-btn-pin:hover { background-color: rgba(255,255,0,0.1); }
.editor-btn-del {
    background-color: transparent;
    color: #ff5500;
    border: 1px solid rgba(255,85,0,0.4);
    border-radius: 2px;
    padding: 4px 10px;
    font-size: 11px;
}
.editor-btn-del:hover { background-color: rgba(255,85,0,0.15); }
"""


class Note:
    def __init__(self, data=None):
        if data:
            self.id       = data.get("id", str(uuid.uuid4())[:8])
            self.title    = data.get("title", "")
            self.content  = data.get("content", "")
            self.color    = data.get("color", "#ff00ff")
            self.pinned   = data.get("pinned", False)
            self.x        = data.get("x", -1)
            self.y        = data.get("y", -1)
            self.rotation = data.get("rotation", self._stable_rotation(data.get("id","x")))
        else:
            self.id       = str(uuid.uuid4())[:8]
            self.title    = ""
            self.content  = ""
            self.color    = random.choice(PALETTE)
            self.pinned   = False
            self.x        = -1
            self.y        = -1
            self.rotation = random.uniform(-4.0, 4.0)

    def _stable_rotation(self, nid):
        seed = sum(ord(c) for c in nid)
        return ((seed % 80) - 40) / 10.0

    def to_dict(self):
        return {
            "id": self.id, "title": self.title, "content": self.content,
            "color": self.color, "pinned": self.pinned,
            "x": self.x, "y": self.y, "rotation": self.rotation,
        }

    def hit_test(self, px, py):
        cx = self.x + NOTE_W / 2
        cy = self.y + NOTE_H / 2
        dx, dy = px - cx, py - cy
        a = -math.radians(self.rotation)
        lx = dx * math.cos(a) - dy * math.sin(a)
        ly = dx * math.sin(a) + dy * math.cos(a)
        return -NOTE_W/2 <= lx <= NOTE_W/2 and -NOTE_H/2 <= ly <= NOTE_H/2

    def swatch_hit(self, px, py):
        cx = self.x + NOTE_W / 2
        cy = self.y + NOTE_H / 2
        dx, dy = px - cx, py - cy
        a = -math.radians(self.rotation)
        lx = dx * math.cos(a) - dy * math.sin(a)
        ly = dx * math.sin(a) + dy * math.cos(a)
        hw, hh = NOTE_W/2, NOTE_H/2
        if abs(ly - (hh - 14)) < 11:
            for i in range(len(PALETTE)):
                sx = -hw + 16 + i * 20
                if abs(lx - sx) < 9:
                    return i
        return -1


class NyxusStickies(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.stickies")
        self.notes = []
        self._selected = None
        self._editor_win = None
        self._anim_t = 0.0
        self._load()
        self._arrange()

    def _arrange(self):
        arranged = []
        i = 0
        for note in self.notes:
            if note.x < 0 or note.y < 0:
                col = i % COLS
                row = i // COLS
                note.x = PAD + col * (NOTE_W + PAD * 2) + random.randint(-6, 6)
                note.y = PAD + row * (NOTE_H + PAD) + random.randint(-6, 6)
                i += 1
            else:
                i += 1

    def do_activate(self):
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self, title="NYXUS Stickies")
        self.win.set_default_size(550, 600)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)
        root.append(self._build_header())

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self._board = Gtk.DrawingArea()
        self._board.set_size_request(550, self._board_h())
        self._board.set_draw_func(self._draw_board, None)

        click = Gtk.GestureClick()
        click.connect("pressed", self._on_click)
        self._board.add_controller(click)

        scroll.set_child(self._board)
        root.append(scroll)

        GLib.timeout_add(50, self._tick)
        self.win.present()

    def _build_header(self):
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        hdr.add_css_class("header")

        t = Gtk.Label(label="NYXUS_STICKIES")
        t.add_css_class("app-title")
        hdr.append(t)

        self._count_lbl = Gtk.Label()
        self._count_lbl.add_css_class("note-count")
        hdr.append(self._count_lbl)
        self._sync_count()

        sp = Gtk.Box(); sp.set_hexpand(True); hdr.append(sp)

        bn = Gtk.Button(label="+ NEW NOTE")
        bn.add_css_class("btn-new")
        bn.connect("clicked", lambda *_: self._new_note())
        hdr.append(bn)

        bp = Gtk.Button(label="PURGE")
        bp.add_css_class("btn-purge")
        bp.connect("clicked", lambda *_: self._purge())
        hdr.append(bp)
        return hdr

    def _board_h(self):
        if not self.notes:
            return 500
        return max(500, max(n.y + NOTE_H + PAD + 20 for n in self.notes))

    def _tick(self):
        self._anim_t += 0.04
        self._board.queue_draw()
        return GLib.SOURCE_CONTINUE

    # ── Cairo board ──────────────────────────────────────────────────────────────
    def _draw_board(self, area, cr, w, h, _):
        cr.set_source_rgb(0.012, 0.008, 0.024)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        # Dot grid
        sp = 26
        cr.set_source_rgba(0.28, 0.07, 0.50, 0.12)
        for gx in range(0, w + sp, sp):
            for gy in range(0, h + sp, sp):
                cr.arc(gx, gy, 1.0, 0, math.pi * 2)
                cr.fill()
        # Draw notes
        order = sorted(self.notes, key=lambda n: (
            1 if n.pinned else 0,
            1 if (self._selected and n.id == self._selected.id) else 0,
        ))
        for note in order:
            self._draw_note(cr, note)

    def _draw_note(self, cr, note):
        cx = note.x + NOTE_W / 2
        cy = note.y + NOTE_H / 2
        r, g, b = hex_rgb(note.color)
        is_sel  = self._selected and self._selected.id == note.id
        hw, hh  = NOTE_W / 2, NOTE_H / 2

        cr.save()
        cr.translate(cx, cy)
        cr.rotate(math.radians(note.rotation))

        # Glow layers
        if note.pinned:
            ga = 0.11 + 0.06 * math.sin(self._anim_t * 2.2)
        elif is_sel:
            ga = 0.20
        else:
            ga = 0.055
        for gw, fa in [(24, 0.30), (15, 0.60), (8, 1.0)]:
            cr.set_source_rgba(r, g, b, ga * fa)
            cr.set_line_width(gw)
            cr.rectangle(-hw, -hh, NOTE_W, NOTE_H)
            cr.stroke()

        # 10% color tint bg
        cr.set_source_rgba(r, g, b, 0.10)
        cr.rectangle(-hw, -hh, NOTE_W, NOTE_H)
        cr.fill()
        # Dark overlay
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.62)
        cr.rectangle(-hw, -hh, NOTE_W, NOTE_H)
        cr.fill()
        # Header strip
        cr.set_source_rgba(0.0, 0.0, 0.0, 0.40)
        cr.rectangle(-hw, -hh, NOTE_W, 27)
        cr.fill()
        # Header separator
        cr.set_source_rgba(r, g, b, 0.28)
        cr.set_line_width(1.0)
        cr.move_to(-hw, -hh + 27); cr.line_to(hw, -hh + 27)
        cr.stroke()
        # Border
        ba = 0.85 + 0.12 * math.sin(self._anim_t * 3) if note.pinned else (1.0 if is_sel else 0.78)
        cr.set_source_rgba(r, g, b, ba)
        cr.set_line_width(1.5)
        cr.rectangle(-hw, -hh, NOTE_W, NOTE_H)
        cr.stroke()

        # Pin indicator
        if note.pinned:
            cr.set_source_rgba(1.0, 1.0, 0.0, 0.95)
            cr.arc(hw - 10, -hh + 13, 4, 0, math.pi * 2)
            cr.fill()

        # Title (with glow)
        cr.select_font_face("JetBrains Mono", 0, 1)
        title_txt = (note.title.upper() if note.title else "TITLE...")[:24]
        for dx, dy, a in [(-1,-1,0.22),(1,-1,0.22),(-1,1,0.22),(1,1,0.22)]:
            cr.set_source_rgba(r, g, b, a)
            cr.set_font_size(11)
            cr.move_to(-hw + 8 + dx, -hh + 19 + dy)
            cr.show_text(title_txt)
        cr.set_source_rgba(r, g, b, 1.0)
        cr.set_font_size(11)
        cr.move_to(-hw + 8, -hh + 19)
        cr.show_text(title_txt)

        # Body
        cr.set_source_rgba(0.91, 0.88, 0.96, 0.82)
        body = note.content or "Click to edit..."
        lines = wrap_text(cr, body, NOTE_W - 20, size=10)
        cr.select_font_face("JetBrains Mono", 0, 0)
        for i, line in enumerate(lines[:5]):
            cr.move_to(-hw + 9, -hh + 40 + i * 15)
            cr.show_text(line)

        # Color swatches at bottom
        sw_y = hh - 14
        for i, col in enumerate(PALETTE):
            sr, sg, sb = hex_rgb(col)
            is_active = col == note.color
            r2 = 5.0 if is_active else 3.5
            cr.set_source_rgba(sr, sg, sb, 1.0 if is_active else 0.65)
            cr.arc(-hw + 16 + i * 20, sw_y, r2, 0, math.pi * 2)
            cr.fill()
            if is_active:
                cr.set_source_rgba(1, 1, 1, 0.8)
                cr.set_line_width(1.0)
                cr.arc(-hw + 16 + i * 20, sw_y, 6.5, 0, math.pi * 2)
                cr.stroke()

        cr.restore()

    # ── Interaction ──────────────────────────────────────────────────────────────
    def _on_click(self, gesture, n_press, x, y):
        for note in reversed(self.notes):
            if note.hit_test(x, y):
                si = note.swatch_hit(x, y)
                if si >= 0:
                    note.color = PALETTE[si]
                    self._save()
                    return
                self._selected = note
                self._open_editor(note)
                return
        self._selected = None

    def _open_editor(self, note):
        if self._editor_win:
            try:
                self._editor_win.destroy()
            except Exception:
                pass
            self._editor_win = None

        r, g, b = hex_rgb(note.color)
        ri, gi, bi = int(r*255), int(g*255), int(b*255)

        border_css = (
            f".editor-win {{ border: 1px solid {note.color}; "
            f"box-shadow: 0 0 24px rgba({ri},{gi},{bi},0.45); }}"
        ).encode()

        extra_prov = Gtk.CssProvider()
        extra_prov.load_from_data(border_css)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), extra_prov, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        ed = Gtk.Window()
        ed.set_title("Edit Note")
        ed.set_transient_for(self.win)
        ed.set_modal(False)
        ed.set_default_size(310, 240)
        ed.add_css_class("editor-win")
        self._editor_win = ed

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        ed.set_child(root)

        title_entry = Gtk.Entry()
        title_entry.add_css_class("editor-title-entry")
        title_entry.set_text(note.title)
        title_entry.set_placeholder_text("TITLE...")
        title_entry.set_has_frame(False)
        root.append(title_entry)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)

        tv = Gtk.TextView()
        tv.add_css_class("editor-body-view")
        tv.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        tv.set_left_margin(14); tv.set_right_margin(14)
        tv.set_top_margin(10); tv.set_bottom_margin(10)
        buf = tv.get_buffer()
        buf.set_text(note.content)
        scroll.set_child(tv)
        root.append(scroll)

        # Swatches
        sw_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        sw_bar.add_css_class("swatch-bar")
        disp = Gdk.Display.get_default()
        for col in PALETTE:
            btn = Gtk.Button()
            btn.add_css_class("swatch-btn")
            btn.set_size_request(18, 18)
            sp = Gtk.CssProvider()
            cls = f"sw{col[1:]}"
            bg = f"background-color:{col};border-color:{'rgba(255,255,255,0.9)' if col==note.color else 'rgba(255,255,255,0.2)'};"
            sp.load_from_data(f".{cls}{{{bg}}}".encode())
            Gtk.StyleContext.add_provider_for_display(disp, sp, Gtk.STYLE_PROVIDER_PRIORITY_USER)
            btn.add_css_class(cls)
            btn.connect("clicked", lambda *_, c=col, te=title_entry, b=buf: self._recolor(note, c, te, b, ed))
            sw_bar.append(btn)
        root.append(sw_bar)

        act = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        act.add_css_class("act-bar")

        pin_lbl = "UNPIN" if note.pinned else "PIN"
        btn_pin = Gtk.Button(label=pin_lbl); btn_pin.add_css_class("editor-btn-pin")
        btn_del = Gtk.Button(label="DELETE");  btn_del.add_css_class("editor-btn-del")
        sp2 = Gtk.Box(); sp2.set_hexpand(True)
        btn_done = Gtk.Button(label="DONE"); btn_done.add_css_class("editor-btn-done")

        act.append(btn_pin); act.append(btn_del)
        act.append(sp2); act.append(btn_done)
        root.append(act)

        def _flush(te, b):
            note.title = te.get_text()
            s, e = b.get_bounds()
            note.content = b.get_text(s, e, False)

        def save_close(*_):
            _flush(title_entry, buf)
            self._save(); self._board.queue_draw()
            ed.destroy(); self._editor_win = None

        def do_pin(*_):
            _flush(title_entry, buf)
            note.pinned = not note.pinned
            self._save(); self._board.queue_draw()
            ed.destroy(); self._editor_win = None

        def do_del(*_):
            self.notes = [n for n in self.notes if n.id != note.id]
            self._selected = None
            self._save(); self._sync_count(); self._board.queue_draw()
            ed.destroy(); self._editor_win = None

        btn_done.connect("clicked", save_close)
        btn_pin.connect("clicked", do_pin)
        btn_del.connect("clicked", do_del)
        ed.connect("close-request", lambda *_: save_close() or False)

        ed.present()
        GLib.idle_add(lambda: (title_entry.grab_focus() if not note.title else tv.grab_focus()) or False)

    def _recolor(self, note, color, title_entry, buf, ed):
        note.title = title_entry.get_text()
        s, e = buf.get_bounds()
        note.content = buf.get_text(s, e, False)
        note.color = color
        self._save(); self._board.queue_draw()
        ed.destroy(); self._editor_win = None
        GLib.idle_add(lambda: self._open_editor(note) or False)

    def _new_note(self):
        note = Note()
        n = len(self.notes)
        col = n % COLS; row = n // COLS
        note.x = PAD + col * (NOTE_W + PAD * 2) + random.randint(-7, 7)
        note.y = PAD + row * (NOTE_H + PAD) + random.randint(-7, 7)
        self.notes.append(note)
        self._board.set_size_request(550, self._board_h())
        self._save(); self._sync_count()
        self._selected = note
        self._open_editor(note)

    def _purge(self):
        self.notes = []; self._selected = None
        self._save(); self._sync_count(); self._board.queue_draw()

    def _sync_count(self):
        n = len(self.notes)
        self._count_lbl.set_text(f"{n} {'MEMORY' if n==1 else 'MEMORIES'}")

    def _save(self):
        try:
            with open(DATA_FILE, "w") as f:
                json.dump({"notes": [n.to_dict() for n in self.notes]}, f, indent=2)
        except Exception as ex:
            print(f"[stickies] save: {ex}")

    def _load(self):
        try:
            with open(DATA_FILE) as f:
                self.notes = [Note(d) for d in json.load(f).get("notes", [])]
        except Exception:
            self.notes = []


if __name__ == "__main__":
    NyxusStickies().run(None)
