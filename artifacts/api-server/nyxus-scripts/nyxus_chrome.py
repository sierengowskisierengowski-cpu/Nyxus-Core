#!/usr/bin/env python3
"""
NYXUS — Shared Chrome Module
Drop-in chrome (rainbow titles, hand-painted graffiti backgrounds, neon
edges, shared CSS) for every NYXUS GTK4 application. One canonical
implementation -- every app imports from here.

Usage in any GTK4 NYXUS app:
    # at top of file (after gi imports)
    from pathlib import Path
    import sys, urllib.request, os
    _CHROME_URL = "https://nyxus-core.replit.app/api/download/nyxus/nyxus_chrome.py"
    try:
        from nyxus_chrome import install_chrome, rainbow_markup
    except ImportError:
        try:
            _here = os.path.dirname(os.path.abspath(__file__))
            urllib.request.urlretrieve(_CHROME_URL,
                os.path.join(_here, "nyxus_chrome.py"))
            if _here not in sys.path: sys.path.insert(0, _here)
            from nyxus_chrome import install_chrome, rainbow_markup
        except Exception:
            def install_chrome(*a, **kw): return None
            def rainbow_markup(t): return t

    # in do_activate, AFTER window content is set:
    install_chrome(self.win, page_key="_notepad")    # or "_stickies", etc.

© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
from gi.repository import Gtk, Gdk, GLib, GdkPixbuf  # noqa: E402

import cairo  # type: ignore
import logging, subprocess, threading
from pathlib import Path
from typing import Dict, Optional, Tuple, Set

log = logging.getLogger("nyxus.chrome")

# ── Palette (matches nyxus_settings.py) ─────────────────────────────────────
NEON_PINK   = (1.00, 0.00, 1.00)
NEON_BLUE   = (0.00, 0.67, 1.00)
NEON_GREEN  = (0.22, 1.00, 0.08)
ACCENT_GOLD = (1.00, 0.78, 0.20)

_RAINBOW_HEX = ("#ff00ff", "#ff2da8", "#b800ff", "#00aaff",
                "#39ff14", "#ffc833", "#ff66dd", "#ff00ff")


def rainbow_markup(text: str) -> str:
    """Per-letter neon Pango spans cycling pink→magenta→blue→green→gold.
    Whitespace stays neutral so the readable letters do the singing."""
    out, i = [], 0
    for ch in text:
        if ch.isspace():
            out.append(ch); continue
        col = _RAINBOW_HEX[i % len(_RAINBOW_HEX)]
        esc = (ch.replace("&", "&amp;").replace("<", "&lt;")
                  .replace(">", "&gt;"))
        out.append(f'<span foreground="{col}">{esc}</span>')
        i += 1
    return "".join(out)


# ── Graffiti image background (hand-painted walls, page-aware) ──────────────
_IMAGE_POOL = [f"nyxus-graffiti-{i:02d}.png" for i in range(1, 25)]
_IMAGE_BASE_URL = "https://nyxus-core.replit.app/api/download/nyxus"
_IMAGE_CACHE_DIR = Path.home() / ".cache" / "nyxus" / "graffiti"

# Per-app default image picks. Each NYXUS app has a signature mural.
_PAGE_IMAGE_OVERRIDE = {
    # nyxus_settings page keys
    "_home":         0,
    "account":       16, "display":       3,  "network":       4,
    "bluetooth":     7,  "sound":        12,  "keyboard":      6,
    "mouse":        15,  "power":        11,  "appearance":   10,
    "workspaces":    5,  "datetime":      9,  "notifications":13,
    "users":        14,  "privacy":      12,  "apps":          1,
    "storage":       1,  "language":      2,  "a11y":          5,
    "printers":      8,  "gaming":        3,  "developer":     8,
    "wallpaper":    10,  "fonts":         6,  "about":         0,
    # other NYXUS apps
    "_notepad":      6,   # mint lettering -- writerly
    "_stickies":    10,   # rainbow on brick
    "_sysmon":       8,   # MAN/STREET tags -- developer feel
    "_control":     11,   # neon eye -- watchful
    "_terminal":     8,   # developer
    "_weather":      9,   # paint drips
    "_quicksettings": 7,  # rainbow flow
    "_widgets":      4,   # walls of crowns
    "_web":          0,
}


class GraffitiBackground(Gtk.DrawingArea):
    """Hand-painted graffiti mural behind any NYXUS window. Cover-fits
    the picked image, lays a soft radial vignette over it, plus a faint
    pink edge bloom. Images live in ~/.cache/nyxus/graffiti/ and are
    fetched async on first launch from the api-server."""

    def __init__(self, page_key: str = "_home"):
        super().__init__()
        self.set_hexpand(True); self.set_vexpand(True)
        self.set_can_target(False)  # never steals clicks
        self.add_css_class("nyx-graffiti-host")
        self.set_draw_func(self._draw)
        self._page_key = page_key if page_key in _PAGE_IMAGE_OVERRIDE else "_home"
        self._pixbuf_cache: Dict[str, GdkPixbuf.Pixbuf] = {}
        self._scaled_cache: Dict[Tuple[str, int, int], GdkPixbuf.Pixbuf] = {}
        self._fetch_inflight: Set[str] = set()
        try:
            _IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            log.warning("graffiti cache dir: %s", e)

    def set_page_key(self, key: str):
        new = key if key in _PAGE_IMAGE_OVERRIDE else "_home"
        if new == self._page_key: return
        self._page_key = new
        self.queue_draw()

    def _image_for_page(self, key: str) -> str:
        idx = _PAGE_IMAGE_OVERRIDE.get(key)
        if idx is None:
            idx = abs(hash(("nyx-graffiti-pick", key))) % len(_IMAGE_POOL)
        idx = max(0, min(idx, len(_IMAGE_POOL) - 1))
        return _IMAGE_POOL[idx]

    def _load_pixbuf(self, name: str) -> Optional[GdkPixbuf.Pixbuf]:
        if name in self._pixbuf_cache:
            return self._pixbuf_cache[name]
        local = _IMAGE_CACHE_DIR / name
        if local.exists() and local.stat().st_size > 1024:
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file(str(local))
                self._pixbuf_cache[name] = pb
                return pb
            except Exception as e:
                log.warning("graffiti load %s: %s", name, e)
                try: local.unlink()
                except Exception: pass
        # async fetch (idempotent)
        if name not in self._fetch_inflight:
            self._fetch_inflight.add(name)
            url = f"{_IMAGE_BASE_URL}/{name}"
            def _worker():
                try:
                    rc = subprocess.call(
                        ["curl", "-fsSL", "--max-time", "30", "-o",
                         str(local), url],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    GLib.idle_add(self._on_fetched, name, rc)
                except Exception as e:
                    log.warning("graffiti fetch %s: %s", name, e)
                    GLib.idle_add(self._on_fetched, name, 1)
            threading.Thread(target=_worker, daemon=True).start()
        return None

    def _on_fetched(self, name: str, rc: int):
        self._fetch_inflight.discard(name)
        local = _IMAGE_CACHE_DIR / name
        if rc == 0 and local.exists() and local.stat().st_size > 1024:
            try:
                pb = GdkPixbuf.Pixbuf.new_from_file(str(local))
                self._pixbuf_cache[name] = pb
                self._scaled_cache = {k: v for k, v in
                                      self._scaled_cache.items()
                                      if k[0] != name}
                self.queue_draw()
            except Exception as e:
                log.warning("graffiti decode %s: %s", name, e)
        return False

    def _scaled_for(self, name: str, w: int, h: int) -> Optional[GdkPixbuf.Pixbuf]:
        bw = max(64, (w // 32) * 32)
        bh = max(64, (h // 32) * 32)
        ck = (name, bw, bh)
        if ck in self._scaled_cache:
            return self._scaled_cache[ck]
        src = self._load_pixbuf(name)
        if src is None: return None
        sw, sh = src.get_width(), src.get_height()
        if sw <= 0 or sh <= 0: return None
        scale = max(bw / sw, bh / sh)  # COVER fit
        tw, th = max(1, int(sw * scale)), max(1, int(sh * scale))
        try:
            scaled = src.scale_simple(tw, th, GdkPixbuf.InterpType.BILINEAR)
        except Exception as e:
            log.warning("graffiti scale %s: %s", name, e)
            return None
        if len(self._scaled_cache) > 6:
            self._scaled_cache.pop(next(iter(self._scaled_cache)))
        self._scaled_cache[ck] = scaled
        return scaled

    def _draw(self, area, cr, w, h, _=None):
        # PURE black baseline
        cr.set_source_rgba(0.0, 0.0, 0.0, 1.0)
        cr.rectangle(0, 0, w, h); cr.fill()

        img_name = self._image_for_page(self._page_key)
        scaled = self._scaled_for(img_name, w, h)
        if scaled is not None:
            sw, sh = scaled.get_width(), scaled.get_height()
            ox = (w - sw) // 2
            oy = (h - sh) // 2
            cr.save()
            cr.rectangle(0, 0, w, h); cr.clip()
            Gdk.cairo_set_source_pixbuf(cr, scaled, ox, oy)
            cr.paint()
            cr.restore()

            # softer vignette -- lets the wall breathe through
            try:
                pat = cairo.RadialGradient(w / 2, h / 2, 0,
                                           w / 2, h / 2, max(w, h) * 0.7)
                pat.add_color_stop_rgba(0.00, 0.0, 0.0, 0.0, 0.36)
                pat.add_color_stop_rgba(0.55, 0.0, 0.0, 0.0, 0.52)
                pat.add_color_stop_rgba(1.00, 0.0, 0.0, 0.0, 0.70)
                cr.set_source(pat)
            except Exception:
                cr.set_source_rgba(0.0, 0.0, 0.0, 0.50)
            cr.rectangle(0, 0, w, h); cr.fill()

            # faint pink top/bottom edge bloom
            try:
                pat2 = cairo.LinearGradient(0, 0, 0, h)
                pat2.add_color_stop_rgba(0.00, 1.0, 0.0, 1.0, 0.07)
                pat2.add_color_stop_rgba(0.50, 1.0, 0.0, 1.0, 0.00)
                pat2.add_color_stop_rgba(1.00, 1.0, 0.0, 1.0, 0.07)
                cr.set_source(pat2)
                cr.rectangle(0, 0, w, h); cr.fill()
            except Exception:
                pass


# ── Shared NYXUS chrome CSS -- "godsapp visual language", system-wide. ────
# Reference: the godsapp screenshot — transparent window so the graffiti
# mural shows through, translucent dark inner panels, semi-opaque entries
# /textviews where text needs to be readable, and rainbow-cycling neon
# button outlines with handwritten Caveat labels. We promote godsapp's
# `* { font-family: Caveat }` universal rule across every NYXUS app, with
# a `.nyx-mono` opt-out class for places that genuinely need a monospace
# face (terminals, code editors, log views). This CSS is loaded at
# Gtk.STYLE_PROVIDER_PRIORITY_USER so it overrides each app's own
# APPLICATION provider — apps don't have to opt-in.
CHROME_CSS = """
/* -- Typography: Caveat everywhere except explicit monospace zones --- */
* {
    font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', cursive;
}
.nyx-mono, .nyx-mono *, .nyx-code, .nyx-code *,
.monospace, .monospace *,
textview.nyx-mono, textview.nyx-mono text,
textview.monospace, textview.monospace text {
    font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', monospace;
}

/* -- Window: fully transparent so the graffiti mural reads through ----- */
window {
    background-color: rgba(0, 0, 0, 0.0);
    color: #efefee;
}

/* -- Outer shell layers: translucent dark so graffiti glows through ---- */
window > * > box, window > overlay > box,
.nyx-bg, .nyx-shell-bg {
    background-color: rgba(0, 0, 0, 0.42);
}

/* -- Inner panels (frame/scrolledwindow/listbox/card): darker plate ---- */
frame, scrolledwindow, listbox, .card, .nyx-card, .nyx-panel {
    background-color: rgba(10, 10, 18, 0.55);
    border-radius: 6px;
    border: 1px solid rgba(255, 255, 255, 0.06);
}
list, listbox row {
    background-color: transparent;
}
listbox row:selected {
    background-color: rgba(255, 0, 255, 0.18);
    color: #ffffff;
}
listbox row:hover {
    background-color: rgba(255, 255, 255, 0.04);
}

/* -- Headerbar (Adw apps): translucent so the graffiti shows up top --- */
headerbar, .titlebar {
    background-color: rgba(10, 10, 18, 0.65);
    border-bottom: 1px solid rgba(255, 0, 255, 0.18);
    color: #efefee;
}

/* -- Text inputs: more opaque so text is readable, neon focus ring ---- */
entry, textview, textview text, spinbutton {
    background-color: rgba(16, 16, 25, 0.85);
    color: #efefee;
    border-radius: 6px;
    padding: 8px 12px;
    min-height: 36px;
    font-size: 17px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}
entry:focus, textview:focus, spinbutton:focus {
    border-color: rgba(255, 0, 255, 0.65);
    box-shadow: 0 0 8px rgba(255, 0, 255, 0.30);
}
/* GTK4 placeholder is a child node, not a CSS pseudo-element */
entry > text > placeholder,
entry placeholder {
    color: rgba(174, 174, 182, 0.55);
}

/* -- Buttons: transparent fill, Caveat label, rainbow neon outline --- */
button {
    background-color: rgba(0, 0, 0, 0.35);
    color: #efefee;
    border: 1.5px solid rgba(255, 0, 255, 0.70);
    border-radius: 6px;
    padding: 6px 14px;
    min-height: 32px;
    font-family: 'Caveat', cursive;
    font-size: 17px;
    transition: background-color 120ms ease, box-shadow 120ms ease,
                border-color 120ms ease;
}
button:hover {
    background-color: rgba(255, 0, 255, 0.10);
    box-shadow: 0 0 14px rgba(255, 0, 255, 0.40);
}
button:active, button:checked {
    background-color: rgba(255, 0, 255, 0.18);
    box-shadow: inset 0 0 8px rgba(255, 0, 255, 0.45);
}
button:disabled {
    color: rgba(239, 239, 238, 0.35);
    border-color: rgba(255, 255, 255, 0.12);
}

/* -- Sibling-cycling neon outlines so adjacent buttons differ in hue -- */
/* (matches godsapp where each button in a row has its own neon color) */
/* Gated to .nyx-rainbow-row so titlebar/utility buttons stay uniform   */
/* pink. Apps that want the godsapp action-bar look wrap their button   */
/* row container in `.nyx-rainbow-row`.                                 */
.nyx-rainbow-row > button:nth-child(2n) {
    border-color: rgba(0, 170, 255, 0.75);
}
.nyx-rainbow-row > button:nth-child(2n):hover {
    background-color: rgba(0, 170, 255, 0.10);
    box-shadow: 0 0 14px rgba(0, 170, 255, 0.40);
}
.nyx-rainbow-row > button:nth-child(3n) {
    border-color: rgba(255, 215, 0, 0.75);
}
.nyx-rainbow-row > button:nth-child(3n):hover {
    background-color: rgba(255, 215, 0, 0.10);
    box-shadow: 0 0 14px rgba(255, 215, 0, 0.40);
}
.nyx-rainbow-row > button:nth-child(4n) {
    border-color: rgba(57, 255, 20, 0.75);
}
.nyx-rainbow-row > button:nth-child(4n):hover {
    background-color: rgba(57, 255, 20, 0.10);
    box-shadow: 0 0 14px rgba(57, 255, 20, 0.40);
}

/* Adwaita semantic button classes (Adw apps use these heavily) */
button.suggested-action {
    border-color: rgba(57, 255, 20, 0.85);
    color: #d6ffcd;
}
button.destructive-action {
    border-color: rgba(255, 80, 100, 0.85);
    color: #ffd6dc;
}
button.flat {
    border-color: transparent;
    background-color: transparent;
}
button.flat:hover {
    background-color: rgba(255, 0, 255, 0.10);
    border-color: rgba(255, 0, 255, 0.40);
}

/* -- Dropdowns / combos: same treatment as buttons -------------------- */
dropdown, combobox > box.linked > button {
    background-color: rgba(16, 16, 25, 0.85);
    border: 1px solid rgba(255, 0, 255, 0.55);
    border-radius: 6px;
    padding: 6px 12px;
    min-height: 36px;
    font-size: 16px;
    color: #efefee;
}

/* -- Checkbuttons / switches: Caveat label, neon accent --------------- */
checkbutton label, switch label, radiobutton label {
    font-size: 18px;
    color: #efefee;
}
check, radio {
    background-color: rgba(16, 16, 25, 0.85);
    border: 1.5px solid rgba(255, 0, 255, 0.55);
    min-width: 18px; min-height: 18px;
    border-radius: 4px;
}
check:checked, radio:checked {
    background-color: rgba(255, 0, 255, 0.55);
    color: #ffffff;
}
switch slider {
    background-color: rgba(239, 239, 238, 0.85);
    border-radius: 999px;
}
switch:checked {
    background-color: rgba(255, 0, 255, 0.55);
}

/* -- Sliders ----------------------------------------------------------- */
scale trough {
    background-color: rgba(16, 16, 25, 0.85);
    border-radius: 4px;
    min-height: 6px;
}
scale highlight {
    background-color: rgba(255, 0, 255, 0.65);
    border-radius: 4px;
}
scale slider {
    background-color: #efefee;
    box-shadow: 0 0 8px rgba(255, 0, 255, 0.55);
    border-radius: 999px;
    min-width: 16px; min-height: 16px;
}

/* -- Hero / rainbow title labels (callers add .nyx-rainbow-title) ----- */
.nyx-rainbow-title {
    font-family: 'Caveat', 'Patrick Hand', cursive;
    font-weight: bold;
    font-size: 28px;
    text-shadow: 0 0 14px rgba(255, 255, 255, 0.55),
                 0 0 28px rgba(255, 0, 255, 0.45);
}

/* -- Window edge glow (callers add .nyx-chrome-edge to a wrapper) ----- */
.nyx-chrome-edge {
    border: 3px solid rgba(255, 0, 255, 0.85);
    border-radius: 6px;
    box-shadow: 0 0 36px rgba(255, 0, 255, 0.45),
                inset 0 0 2px rgba(255, 0, 255, 0.65);
}

/* -- Status / footer bar ----------------------------------------------- */
.nyx-statusbar {
    color: #8a8a93;
    padding: 6px 14px;
    font-size: 16px;
}

/* -- Convenience text classes (mirror godsapp's ui.py) ---------------- */
.nyx-dim   { color: #aeaeb6; }
.nyx-faint { color: #6c6c75; }

/* -- Scrollbars: neon pink slider on transparent track ---------------- */
scrollbar { background-color: transparent; }
scrollbar slider {
    background-color: rgba(255, 0, 255, 0.45);
    border: 1px solid rgba(255, 0, 255, 0.65);
    border-radius: 6px;
    min-width: 8px; min-height: 8px;
}
scrollbar slider:hover {
    background-color: rgba(255, 0, 255, 0.65);
}

/* -- Tooltips ---------------------------------------------------------- */
tooltip {
    background-color: rgba(10, 10, 18, 0.92);
    border: 1px solid rgba(255, 0, 255, 0.55);
    border-radius: 6px;
    color: #efefee;
    padding: 6px 10px;
}

/* -- Popovers / menus / menubuttons ----------------------------------- */
popover, popover.menu, popover > contents, popover > arrow {
    background-color: rgba(10, 10, 18, 0.92);
    color: #efefee;
    border: 1px solid rgba(255, 0, 255, 0.55);
    border-radius: 6px;
    box-shadow: 0 0 18px rgba(255, 0, 255, 0.25);
}
popover modelbutton, popover button {
    background-color: transparent;
    border: none;
    color: #efefee;
    padding: 6px 12px;
    font-size: 16px;
}
popover modelbutton:hover, popover button:hover {
    background-color: rgba(255, 0, 255, 0.18);
    color: #ffffff;
    box-shadow: none;
}
menubutton button, menubutton > button {
    background-color: rgba(0, 0, 0, 0.35);
    border: 1.5px solid rgba(255, 0, 255, 0.70);
    border-radius: 6px;
    color: #efefee;
}
menubutton button:hover {
    background-color: rgba(255, 0, 255, 0.10);
    box-shadow: 0 0 14px rgba(255, 0, 255, 0.40);
}

/* -- Progress bars ---------------------------------------------------- */
progressbar trough {
    background-color: rgba(16, 16, 25, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 4px;
    min-height: 6px;
}
progressbar progress {
    background-color: rgba(255, 0, 255, 0.65);
    border-radius: 4px;
    box-shadow: 0 0 10px rgba(255, 0, 255, 0.45);
}
progressbar text {
    color: #efefee;
    font-size: 14px;
}

/* -- Notebook / tabs (used by some Adw/Gtk apps) ---------------------- */
notebook header {
    background-color: rgba(10, 10, 18, 0.65);
    border-bottom: 1px solid rgba(255, 0, 255, 0.18);
}
notebook tab {
    background-color: transparent;
    color: #aeaeb6;
    padding: 6px 14px;
    font-size: 16px;
    border: none;
}
notebook tab:checked {
    color: #ffffff;
    box-shadow: inset 0 -2px 0 rgba(255, 0, 255, 0.85);
}
notebook tab:hover {
    color: #efefee;
}
"""

_CHROME_PROVIDER_INSTALLED = False


def _install_global_css():
    global _CHROME_PROVIDER_INSTALLED
    if _CHROME_PROVIDER_INSTALLED: return
    try:
        prov = Gtk.CssProvider()
        # CHROME_CSS may be str or bytes depending on Python literal used.
        # GTK4's load_from_data accepts both forms across versions; we try
        # bytes first (most permissive), then fall back to str.
        css_bytes = (CHROME_CSS.encode("utf-8")
                     if isinstance(CHROME_CSS, str) else CHROME_CSS)
        try:
            prov.load_from_data(css_bytes)
        except TypeError:
            try:
                prov.load_from_data(css_bytes.decode("utf-8"))
            except Exception as e:
                log.warning("nyxus_chrome css load: %s", e)
                return
        disp = Gdk.Display.get_default()
        if disp is None: return
        # USER priority -- runs AFTER each app's APPLICATION provider so
        # the chrome translucency overrides whatever the app set first.
        Gtk.StyleContext.add_provider_for_display(
            disp, prov, Gtk.STYLE_PROVIDER_PRIORITY_USER)
        _CHROME_PROVIDER_INSTALLED = True
    except Exception as e:
        log.warning("nyxus_chrome css: %s", e)


def _is_adw_app_window(window) -> bool:
    """True if `window` is an Adw.ApplicationWindow (uses set_content/
    get_content), False for plain Gtk.ApplicationWindow (uses set_child/
    get_child). Adw is optional — falls back to False if unavailable."""
    try:
        import gi as _gi
        _gi.require_version("Adw", "1")
        from gi.repository import Adw as _Adw
        return isinstance(window, _Adw.ApplicationWindow)
    except Exception:
        return False


def install_chrome(window: Gtk.Window, *, page_key: str = "_home",
                   title_label: Optional[Gtk.Label] = None) -> Optional[GraffitiBackground]:
    """Wrap `window`'s current child in a Gtk.Overlay with a graffiti
    mural underneath. Inject shared NYXUS chrome CSS. Optionally swap a
    hero label's markup to the rainbow palette.

    Handles both `Gtk.ApplicationWindow` (set_child/get_child) and
    `Adw.ApplicationWindow` (set_content/get_content).

    Returns the GraffitiBackground instance so callers can call
    `.set_page_key(...)` later (e.g. when changing tabs).

    Idempotent: safe to call once per window."""
    if window is None: return None
    _install_global_css()

    # Pick the right accessor pair for the window class — Gtk uses
    # set_child/get_child; Adw.ApplicationWindow uses set_content/
    # get_content (its set_child is reserved for the internal layout).
    is_adw = _is_adw_app_window(window)
    if is_adw:
        get_content = window.get_content
        set_content = window.set_content
    else:
        get_content = window.get_child
        set_content = window.set_child

    # Already wrapped? (re-entrancy guard)
    cur = get_content()
    if cur is None: return None
    if isinstance(cur, Gtk.Overlay) and cur.get_data("nyxus-chrome-installed"):
        bg = cur.get_data("nyxus-chrome-bg")
        if bg and page_key:
            try: bg.set_page_key(page_key)
            except Exception: pass
        return bg

    try:
        # Detach current content, build overlay [graffiti, original]
        set_content(None)
        overlay = Gtk.Overlay()
        overlay.set_hexpand(True); overlay.set_vexpand(True)
        bg = GraffitiBackground(page_key=page_key)
        overlay.set_child(bg)
        # original content rides on top, fully sized
        cur.set_hexpand(True); cur.set_vexpand(True)
        overlay.add_overlay(cur)
        overlay.set_data("nyxus-chrome-installed", True)
        overlay.set_data("nyxus-chrome-bg", bg)
        set_content(overlay)
    except Exception as e:
        log.warning("install_chrome: %s", e)
        # restore on failure
        try: set_content(cur)
        except Exception: pass
        return None

    if title_label is not None:
        try:
            txt = title_label.get_text() or title_label.get_label() or ""
            if txt:
                title_label.set_use_markup(True)
                title_label.set_markup(rainbow_markup(txt))
                title_label.add_css_class("nyx-rainbow-title")
        except Exception as e:
            log.warning("install_chrome title: %s", e)
    return bg
