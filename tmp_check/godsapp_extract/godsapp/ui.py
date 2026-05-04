"""
NYXUS GodsApp — hand-drawn UI: main window, sidebar, content stack, BaseModule.
© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED

This module preserves the public API the 30 modules import:
    BaseModule, run_subprocess, have, require_tools

Visuals are now Cairo-painted (sketched borders, Caveat font, tilted headers,
hand-drawn buttons) — no dependency on an external nyxus_theme.
"""
from __future__ import annotations

import importlib.util
import math
import random
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("PangoCairo", "1.0")
from gi.repository import GLib, Gtk, Gdk, Adw, Pango, PangoCairo  # noqa: E402
import cairo  # noqa: E402

# --------------------------------------------------------------------------- #
# constants                                                                   #
# --------------------------------------------------------------------------- #
APP_NAME = "NYXUS GodsApp"
DATA_DIR  = Path.home() / ".config" / "nyxus-godsapp"
CACHE_DIR = Path.home() / ".cache"  / "nyxus-godsapp"
SCAN_DIR  = DATA_DIR / "scans"
AUTHORIZE_FLAG_PATH = DATA_DIR / "authorized.json"
for _d in (DATA_DIR, CACHE_DIR, SCAN_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# palette — same family as Studio / SAGE
NYX = {
    "bg":          (0.039, 0.039, 0.071),  # #0a0a12
    "bg_alt":      (0.063, 0.063, 0.102),  # #101019
    "panel":       (0.094, 0.094, 0.149),  # #181825
    "ink":         (0.937, 0.937, 0.933),  # #efefee
    "dim":         (0.65,  0.65,  0.68),
    "faint":       (0.42,  0.42,  0.46),
    "accent":      (0.659, 0.604, 0.792),  # #a89aca lavender
    "accent_warm": (0.82,  0.74,  0.55),
    "good":        (0.55,  0.78,  0.62),
    "warn":        (0.92,  0.78,  0.45),
    "critical":    (0.86,  0.45,  0.50),
    "info":        (0.55,  0.72,  0.86),
}

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Caveat:wght@400;500;600;700&display=swap');
* { font-family: 'Caveat', 'Comic Sans MS', cursive; }
window, .background { background: #0a0a12; color: #efefee; }
.nyx-mono   { font-family: 'JetBrains Mono', 'Fira Code', monospace; font-size: 13px; }
.nyx-dim    { color: #aeaeb6; }
.nyx-faint  { color: #6c6c75; }
textview              { background: #101019; color: #efefee; padding: 12px; }
textview text         { background: #101019; color: #efefee; }
entry                 { background: #101019; color: #efefee; border-radius: 6px;
                        padding: 8px 12px; min-height: 36px; font-size: 17px; }
dropdown              { font-size: 16px; }
checkbutton label     { font-size: 18px; }
.nyx-statusbar        { color: #8a8a93; padding: 6px 14px; font-size: 16px; }
scrollbar slider      { background: #2a2a36; border-radius: 4px; min-width: 6px; min-height: 6px; }
scrollbar slider:hover{ background: #3a3a48; }
"""


def install_global_css(display):
    if display is None:
        return
    p = Gtk.CssProvider()
    p.load_from_data(CSS.encode("utf-8"))
    Gtk.StyleContext.add_provider_for_display(
        display, p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)


# --------------------------------------------------------------------------- #
# subprocess helpers — public API used by every module                        #
# --------------------------------------------------------------------------- #
def have(*tools: str) -> bool:
    return all(shutil.which(t) for t in tools)


def require_tools(*tools: str) -> str | None:
    missing = [t for t in tools if not shutil.which(t)]
    if not missing:
        return None
    return ("Required tool(s) not installed: " + ", ".join(missing) +
            "\n\nInstall with:  sudo pacman -S " + " ".join(missing) +
            "\n           or:  sudo apt install " + " ".join(missing))


def run_subprocess(cmd: list[str], timeout: float = 60,
                   stdin: str | None = None) -> tuple[int, str]:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True,
                           timeout=timeout, input=stdin)
        return r.returncode, (r.stdout + ("\n--STDERR--\n" + r.stderr if r.stderr else ""))
    except FileNotFoundError:
        return 127, f"{cmd[0]}: not installed"
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s"
    except Exception as exc:
        return 1, f"error: {exc}"


# --------------------------------------------------------------------------- #
# low-level sketch primitives                                                 #
# --------------------------------------------------------------------------- #
def _wobble(seed, amp=1.0):
    random.seed(seed)
    return (random.uniform(-amp, amp), random.uniform(-amp, amp))


def sketch_rect(cr, x, y, w, h, color, *, line_width=1.6, passes=3,
                jitter=1.4, alpha_step=0.85, seed=0):
    cr.save()
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.set_line_width(line_width)
    for i in range(passes):
        r, g, b = color[0], color[1], color[2]
        cr.set_source_rgba(r, g, b, 1.0 * (alpha_step ** i))
        d = lambda k: _wobble(seed * 7 + i * 11 + k, jitter)
        cr.move_to(x + d(0)[0],     y + d(0)[1])
        cr.line_to(x + w + d(1)[0], y + d(1)[1])
        cr.line_to(x + w + d(2)[0], y + h + d(2)[1])
        cr.line_to(x + d(3)[0],     y + h + d(3)[1])
        cr.close_path()
        cr.stroke()
    cr.restore()


def sketch_rect_fill(cr, x, y, w, h, color, alpha=0.18, seed=0):
    cr.save()
    cr.set_source_rgba(color[0], color[1], color[2], alpha)
    cr.rectangle(x, y, w, h)
    cr.fill()
    cr.restore()


def sketch_circle(cr, cx, cy, r, color, *, line_width=1.6, passes=3,
                  jitter=1.0, seed=0):
    cr.save()
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.set_line_width(line_width)
    for i in range(passes):
        cr.set_source_rgba(color[0], color[1], color[2], 1.0 * (0.85 ** i))
        N = 36
        for k in range(N + 1):
            ang = 2 * math.pi * k / N
            j = _wobble(seed * 11 + i * 3 + k, jitter)
            x = cx + math.cos(ang) * r + j[0]
            y = cy + math.sin(ang) * r + j[1]
            (cr.move_to if k == 0 else cr.line_to)(x, y)
        cr.stroke()
    cr.restore()


def draw_text(cr, x, y, text, *, size=16, color=(1, 1, 1, 1),
              bold=False, italic=False, family="Caveat"):
    cr.save()
    layout = PangoCairo.create_layout(cr)
    desc = Pango.FontDescription()
    desc.set_family(family)
    desc.set_absolute_size(size * Pango.SCALE)
    if bold:   desc.set_weight(Pango.Weight.BOLD)
    if italic: desc.set_style(Pango.Style.ITALIC)
    layout.set_font_description(desc)
    layout.set_text(text, -1)
    cr.set_source_rgba(*color)
    cr.move_to(x, y)
    PangoCairo.show_layout(cr, layout)
    cr.restore()
    return layout.get_pixel_size()


# --------------------------------------------------------------------------- #
# SketchButton — looks hand-drawn, but is a real Gtk.Button so module code    #
# that calls .get_style_context().add_class(...) keeps working.               #
# --------------------------------------------------------------------------- #
class SketchButton(Gtk.Button):
    def __init__(self, label: str, *, color=None,
                 on_click: Callable[[], None] | None = None,
                 height: int = 44, hpad: int = 18):
        super().__init__()
        self.set_has_frame(False)
        self._label = label
        self._color = color or NYX["accent"]
        self._h = height
        self._hover = False

        self._darea = Gtk.DrawingArea()
        self._darea.set_draw_func(self._draw)
        self._darea.set_content_height(height)
        self._darea.set_content_width(self._measure_width() + 2 * hpad)
        self.set_child(self._darea)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *a: self._set_hover(True))
        motion.connect("leave", lambda *a: self._set_hover(False))
        self._darea.add_controller(motion)

        if on_click is not None:
            self.connect("clicked", lambda _b: on_click())

    def _measure_width(self) -> int:
        return max(82, int(len(self._label) * 11))

    def _set_hover(self, h):
        self._hover = h
        self._darea.queue_draw()

    def _draw(self, area, cr, w, h):
        c = self._color
        seed = hash(self._label) & 0xff
        alpha = 0.30 if self._hover else 0.16
        sketch_rect_fill(cr, 2, 2, w - 4, h - 4, c, alpha=alpha, seed=seed)
        sketch_rect(cr, 2, 2, w - 4, h - 4, c, line_width=1.8,
                    passes=3, jitter=1.3, seed=seed)
        ink = NYX["ink"]
        layout = PangoCairo.create_layout(cr)
        desc = Pango.FontDescription()
        desc.set_family("Caveat")
        desc.set_weight(Pango.Weight.BOLD)
        desc.set_absolute_size(18 * Pango.SCALE)
        layout.set_font_description(desc)
        layout.set_text(self._label, -1)
        tw, th = layout.get_pixel_size()
        cr.set_source_rgba(ink[0], ink[1], ink[2], 1.0)
        cr.move_to((w - tw) / 2, (h - th) / 2)
        PangoCairo.show_layout(cr, layout)


# --------------------------------------------------------------------------- #
# TiltedHeader — hand-drawn tilted title text                                 #
# --------------------------------------------------------------------------- #
class TiltedHeader(Gtk.DrawingArea):
    def __init__(self, text: str, *, size: int = 42, tilt: float = -3.0,
                 color=None, height: int = 80):
        super().__init__()
        self._text  = text
        self._size  = size
        self._tilt  = tilt
        self._color = color or NYX["ink"]
        self.set_content_height(height)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)

    def _draw(self, area, cr, w, h):
        cr.save()
        cr.translate(28, h * 0.72)
        cr.rotate(math.radians(self._tilt))
        c = self._color
        # ghost behind
        draw_text(cr, 0, -self._size, self._text, size=self._size, bold=True,
                  color=(c[0], c[1], c[2], 0.22))
        # main
        draw_text(cr, 1.4, -self._size + 1, self._text, size=self._size,
                  bold=True, color=(c[0], c[1], c[2], 1.0))
        cr.restore()


# --------------------------------------------------------------------------- #
# SidebarItem — number badge + module name, hand-drawn highlight              #
# --------------------------------------------------------------------------- #
class SidebarItem(Gtk.DrawingArea):
    def __init__(self, idx: int, label: str,
                 on_click: Callable[["SidebarItem"], None] | None = None):
        super().__init__()
        self._idx      = idx
        self._label    = label
        self._selected = False
        self._hover    = False
        self.set_content_height(54)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)

        if on_click is not None:
            click = Gtk.GestureClick()
            click.connect("pressed", lambda *a: on_click(self))
            self.add_controller(click)

        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *a: (setattr(self, "_hover", True),
                                            self.queue_draw()))
        motion.connect("leave", lambda *a: (setattr(self, "_hover", False),
                                            self.queue_draw()))
        self.add_controller(motion)

    def set_selected(self, sel: bool):
        self._selected = sel
        self.queue_draw()

    @property
    def index(self) -> int:
        return self._idx

    def _draw(self, area, cr, w, h):
        if self._selected:
            sketch_rect_fill(cr, 4, 4, w - 8, h - 8, NYX["accent"],
                             alpha=0.22, seed=self._idx)
            sketch_rect(cr, 4, 4, w - 8, h - 8, NYX["accent"],
                        line_width=1.6, passes=2, jitter=1.0, seed=self._idx)
        elif self._hover:
            sketch_rect_fill(cr, 4, 4, w - 8, h - 8, NYX["ink"],
                             alpha=0.06, seed=self._idx + 99)

        bx, by, br = 28, h / 2, 14
        sketch_circle(cr, bx, by, br, NYX["accent"], line_width=1.4,
                      passes=2, jitter=0.8, seed=self._idx)
        layout = PangoCairo.create_layout(cr)
        desc = Pango.FontDescription()
        desc.set_family("Caveat")
        desc.set_weight(Pango.Weight.BOLD)
        desc.set_absolute_size(16 * Pango.SCALE)
        layout.set_font_description(desc)
        layout.set_text(f"{self._idx:02d}", -1)
        tw, th = layout.get_pixel_size()
        cr.set_source_rgba(NYX["ink"][0], NYX["ink"][1], NYX["ink"][2], 1.0)
        cr.move_to(bx - tw / 2, by - th / 2)
        PangoCairo.show_layout(cr, layout)

        c = NYX["ink"] if (self._selected or self._hover) else NYX["dim"]
        draw_text(cr, 56, h / 2 - 13, self._label, size=18,
                  color=(c[0], c[1], c[2], 1.0),
                  bold=self._selected)


# --------------------------------------------------------------------------- #
# SketchPanel — Box with hand-drawn border around its child                   #
# --------------------------------------------------------------------------- #
class SketchPanel(Gtk.Box):
    def __init__(self, *, color=None, padding: int = 8, fill: bool = False):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self._color = color or NYX["ink"]
        self._fill  = fill
        self.set_hexpand(True)
        self.set_vexpand(True)
        self._overlay = Gtk.Overlay(hexpand=True, vexpand=True)
        self._darea   = Gtk.DrawingArea()
        self._darea.set_draw_func(self._draw)
        self._darea.set_can_target(False)
        self._inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                              hexpand=True, vexpand=True,
                              margin_top=padding, margin_bottom=padding,
                              margin_start=padding, margin_end=padding)
        self._overlay.set_child(self._inner)
        self._overlay.add_overlay(self._darea)
        super().append(self._overlay)

    def append(self, w):
        self._inner.append(w)

    def _draw(self, area, cr, w, h):
        if self._fill:
            sketch_rect_fill(cr, 1, 1, w - 2, h - 2, self._color,
                             alpha=0.06, seed=hash(id(self)) & 0xff)
        sketch_rect(cr, 1, 1, w - 2, h - 2, self._color, line_width=1.4,
                    passes=3, jitter=1.2, seed=hash(id(self)) & 0xff)


# --------------------------------------------------------------------------- #
# BaseModule — public API preserved exactly                                   #
# --------------------------------------------------------------------------- #
class BaseModule(Gtk.Box):
    NAME = "Module"
    ICON = "•"
    DESCRIPTION = ""

    def __init__(self, app=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                         margin_top=14, margin_bottom=14,
                         margin_start=22, margin_end=22)
        self.app = app
        self._buttons: list[SketchButton] = []
        self._build_skeleton()
        try:
            self.build()
        except Exception as exc:
            self.write(f"[BUILD ERROR] {exc}")

    def _build_skeleton(self):
        head_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title = TiltedHeader(self.NAME, size=34, tilt=-2.0, height=64)
        head_row.append(title)
        self.spinner = Gtk.Spinner(margin_start=8, margin_top=22)
        head_row.append(self.spinner)
        self.append(head_row)

        if self.DESCRIPTION:
            d = Gtk.Label(label=self.DESCRIPTION, xalign=0, wrap=True)
            d.add_css_class("nyx-dim")
            d.set_margin_start(2)
            d.set_margin_bottom(8)
            self.append(d)

        self.actions_row = Gtk.FlowBox(homogeneous=False,
                                       max_children_per_line=8,
                                       column_spacing=10, row_spacing=10,
                                       selection_mode=Gtk.SelectionMode.NONE,
                                       margin_bottom=8)
        self.append(self.actions_row)

        out_panel = SketchPanel(color=NYX["ink"], padding=2)
        self.output = Gtk.TextView(editable=False, monospace=True,
                                   wrap_mode=Gtk.WrapMode.NONE)
        self.output.add_css_class("nyx-mono")
        sw = Gtk.ScrolledWindow(vexpand=True, hexpand=True)
        sw.set_child(self.output)
        out_panel.append(sw)
        self.append(out_panel)

        self.status = Gtk.Label(label="ready", xalign=0)
        self.status.add_css_class("nyx-faint")
        self.status.set_margin_top(4)
        self.append(self.status)

    # ---- subclass hook -------------------------------------------------- #
    def build(self):
        ...

    # ---- helpers used by every module ---------------------------------- #
    def add_action(self, label: str, handler: Callable[[], None],
                   primary: bool = False, danger: bool = False):
        clean = self._strip_glyph(label)
        color = NYX["accent"] if primary else (NYX["critical"] if danger else NYX["ink"])
        def on_click():
            self.set_running(True)
            self.run_in_thread(handler)
        b = SketchButton(clean, color=color, on_click=on_click)
        self.actions_row.append(b)
        self._buttons.append(b)
        return b

    @staticmethod
    def _strip_glyph(s: str) -> str:
        """Remove the leading non-ASCII / emoji glyph prefix from a label."""
        s = s.strip()
        out: list[str] = []
        skipping = True
        for ch in s:
            if skipping:
                if ord(ch) > 127 or ch in (" ", "\t"):
                    continue
                skipping = False
            out.append(ch)
        return "".join(out).strip() or s

    def write(self, text: str, *, replace: bool = False):
        def do():
            buf = self.output.get_buffer()
            if replace:
                buf.set_text(text)
            else:
                end = buf.get_end_iter()
                buf.insert(end, text + ("\n" if not text.endswith("\n") else ""))
            return False
        GLib.idle_add(do)

    def clear(self):
        self.write("", replace=True)

    def set_status(self, txt: str):
        GLib.idle_add(lambda: (self.status.set_label(txt), False)[1])

    def set_running(self, running: bool):
        def do():
            for b in self._buttons:
                b.set_sensitive(not running)
            if running:
                self.spinner.start()
                self.status.set_label("running …")
            else:
                self.spinner.stop()
                self.status.set_label("ready")
            return False
        GLib.idle_add(do)

    def run_in_thread(self, fn: Callable[[], None]):
        def worker():
            try:
                fn()
            except Exception as exc:
                self.write(f"[ERROR] {exc}")
            finally:
                self.set_running(False)
        threading.Thread(target=worker, daemon=True, name=self.NAME).start()

    @property
    def target(self) -> str:
        if self.app and hasattr(self.app, "target_input"):
            return self.app.target_input.get_text().strip()
        return ""

    def need(self, *tools: str) -> bool:
        msg = require_tools(*tools)
        if msg:
            self.write(msg)
            return False
        return True


# --------------------------------------------------------------------------- #
# module discovery — preserves m##_*.py + Page contract                       #
# --------------------------------------------------------------------------- #
def discover_modules() -> list[tuple[str, type[BaseModule]]]:
    here = Path(__file__).resolve().parent / "modules"
    out: list[tuple[str, type[BaseModule]]] = []
    if not here.is_dir():
        return out
    for f in sorted(here.glob("m*.py")):
        if f.name.startswith("__"):
            continue
        spec = importlib.util.spec_from_file_location(f.stem, str(f))
        if spec is None or spec.loader is None:
            continue
        try:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls = getattr(mod, "Page", None)
            if cls and issubclass(cls, BaseModule):
                out.append((cls.NAME, cls))
        except Exception as exc:
            print(f"[modules] failed to load {f.name}: {exc}", file=sys.stderr)
    return out


# --------------------------------------------------------------------------- #
# HeaderStrip — top bar: tilted title, target entry, profile, GOD MODE        #
# --------------------------------------------------------------------------- #
class HeaderStrip(Gtk.Box):
    def __init__(self, on_god_mode: Callable[[], None]):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=14,
                         margin_top=16, margin_bottom=10,
                         margin_start=22, margin_end=22)
        self.set_hexpand(True)

        self.title = TiltedHeader("GODSAPP", size=46, tilt=-3.0, height=72)
        self.title.set_size_request(320, 72)
        self.append(self.title)

        self.target_input = Gtk.Entry(
            placeholder_text="target  (host / IP / range / URL)",
            hexpand=True)
        self.target_input.set_size_request(-1, 44)
        self.target_input.set_valign(Gtk.Align.CENTER)
        self.append(self.target_input)

        self.profile = Gtk.DropDown.new_from_strings(
            ["Quick", "Full", "Stealth", "Aggressive", "Paranoid", "Insane", "Custom"])
        self.profile.set_valign(Gtk.Align.CENTER)
        self.profile.set_size_request(150, 44)
        self.append(self.profile)

        self.god = SketchButton("GOD MODE", color=NYX["accent_warm"],
                                on_click=on_god_mode, height=44)
        self.god.set_valign(Gtk.Align.CENTER)
        self.append(self.god)


# --------------------------------------------------------------------------- #
# MainWindow                                                                  #
# --------------------------------------------------------------------------- #
class MainWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.app = app
        self.set_title(APP_NAME)
        self.set_default_size(1500, 920)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.header = HeaderStrip(on_god_mode=self.on_god_mode)
        self.target_input = self.header.target_input
        outer.append(self.header)

        # wobbly underline
        ul = Gtk.DrawingArea()
        ul.set_content_height(10)
        ul.set_hexpand(True)
        def _draw_ul(_a, cr, w, h):
            cr.set_line_cap(cairo.LINE_CAP_ROUND)
            cr.set_line_width(1.6)
            for i in range(2):
                cr.set_source_rgba(NYX["ink"][0], NYX["ink"][1], NYX["ink"][2],
                                   0.55 - i * 0.25)
                step = 6
                x = 22.0
                first = True
                while x < w - 22:
                    j = _wobble(int(x) + i * 17, 1.2)
                    if first:
                        cr.move_to(x, 5 + j[1])
                        first = False
                    else:
                        cr.line_to(x, 5 + j[1])
                    x += step
                cr.stroke()
        ul.set_draw_func(_draw_ul)
        outer.append(ul)

        # split: sidebar + content
        split = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                        hexpand=True, vexpand=True)

        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                              margin_top=10, margin_bottom=14,
                              margin_start=14, margin_end=10, spacing=6)
        sidebar_box.set_size_request(290, -1)
        sidebar_box.append(TiltedHeader("modules", size=22, tilt=-2.5, height=42))
        sidebar_panel = SketchPanel(color=NYX["ink"], padding=4)
        sidebar_inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sw_sb = Gtk.ScrolledWindow(vexpand=True, hexpand=True,
                                   hscrollbar_policy=Gtk.PolicyType.NEVER)
        sw_sb.set_child(sidebar_inner)
        sidebar_panel.append(sw_sb)
        sidebar_box.append(sidebar_panel)

        modules = discover_modules()
        self.modules = modules
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE,
                               hexpand=True, vexpand=True)
        self._items: list[SidebarItem] = []
        for i, (name, cls) in enumerate(modules, start=1):
            try:
                page = cls(self)
            except Exception as exc:
                page = Gtk.Label(label=f"[load error] {name}: {exc}", xalign=0)
            self.stack.add_named(page, name)
            item = SidebarItem(i, name, on_click=self._on_select)
            sidebar_inner.append(item)
            self._items.append(item)

        if not modules:
            self.stack.add_named(Gtk.Label(label="no modules discovered", xalign=0),
                                 "empty")
        elif self._items:
            self._items[0].set_selected(True)
            self.stack.set_visible_child_name(modules[0][0])

        split.append(sidebar_box)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                              margin_top=10, margin_bottom=14,
                              margin_start=8, margin_end=14,
                              hexpand=True, vexpand=True)
        content_panel = SketchPanel(color=NYX["ink"], padding=2)
        content_panel.append(self.stack)
        content_box.append(content_panel)
        split.append(content_box)

        outer.append(split)

        sb = Gtk.Label(label=f"{APP_NAME} · {len(modules)} modules loaded · "
                             f"type a target above and pick a module to begin",
                       xalign=0)
        sb.add_css_class("nyx-statusbar")
        outer.append(sb)
        self.statusbar = sb

        # idle screensaver overlay
        from screensaver import ScreensaverOverlay, IdleDetector
        self._sav = ScreensaverOverlay()
        root_overlay = Gtk.Overlay()
        root_overlay.set_child(outer)
        root_overlay.add_overlay(self._sav)
        self._sav.set_visible(False)
        self.set_content(root_overlay)

        self._idle = IdleDetector(self, self._sav, idle_seconds=120)
        self._idle.start()

    # ---- selection ------------------------------------------------------ #
    def _on_select(self, item: SidebarItem):
        for it in self._items:
            it.set_selected(it is item)
        idx = item.index - 1
        if 0 <= idx < len(self.modules):
            name, _cls = self.modules[idx]
            self.stack.set_visible_child_name(name)

    # ---- god mode ------------------------------------------------------- #
    def on_god_mode(self):
        target = self.target_input.get_text().strip()
        if not target:
            self.statusbar.set_label("GOD MODE needs a target — type a host first")
            return
        for i, (name, _cls) in enumerate(self.modules):
            if "GOD" in name.upper() or "MASTER" in name.upper():
                self.stack.set_visible_child_name(name)
                for it in self._items:
                    it.set_selected(False)
                if i < len(self._items):
                    self._items[i].set_selected(True)
                return
        self.statusbar.set_label("GOD MODE module not found")
