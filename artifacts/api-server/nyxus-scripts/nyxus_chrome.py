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
import logging, subprocess, threading, random
from pathlib import Path
from typing import Dict, Optional, Tuple, Set

log = logging.getLogger("nyxus.chrome")

# Bumped with every visible chrome change so apps can log which chrome
# version actually loaded. Curl /api/download/nyxus/nyxus_chrome.py |
# grep NYXUS_CHROME_VERSION to confirm freshness from prod.
NYXUS_CHROME_VERSION = "2026.05.07-r12-darkmirror"

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

# Frost tile assets — small repeatable textures used as background-image
# fills inside cards / headerbars. Fetched once at chrome install time and
# substituted into CHROME_CSS via __NYX_TILE_*__ placeholders. Failing to
# fetch is fine — placeholder becomes empty, CSS falls back to flat cream.
_FROST_TILE_GRID   = "nyxus-frost-tile-grid.png"
_FROST_TILE_GLYPHS = "nyxus-frost-tile-glyphs.png"
_FROST_TILE_ASSETS = [_FROST_TILE_GRID, _FROST_TILE_GLYPHS]


def _ensure_frost_tile(name: str) -> str:
    """Ensure the named frost tile exists in the local cache. Returns a
    file:// URL string usable inside a GTK CSS background-image rule, or
    empty string if the tile could not be fetched."""
    try:
        _IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log.warning("frost tile cache dir: %s", e)
        return ""
    local = _IMAGE_CACHE_DIR / name
    if not (local.exists() and local.stat().st_size > 1024):
        try:
            url = f"{_IMAGE_BASE_URL}/{name}"
            subprocess.call(
                ["curl", "-fsSL", "--max-time", "20", "-o", str(local), url],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            log.warning("frost tile fetch %s: %s", name, e)
    if local.exists() and local.stat().st_size > 1024:
        return f"file://{local}"
    return ""

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
/* ═══════════════════════════════════════════════════════════════════════ *
 *  NYXUS UNIVERSAL APP CHROME · DARK MIRROR · rev 2026-05-07 r12         *
 *                                                                         *
 *  System-wide unified frosted glass for every NYXUS GTK4 app + flyout.  *
 *  Loads at GTK_STYLE_PROVIDER_PRIORITY_USER so it overrides every       *
 *  per-app provider (priority APPLICATION) — no app code changes needed. *
 *                                                                         *
 *  PALETTE (locked — monochrome only, no neon, no defaults)              *
 *      #00000000  fully transparent root (Hyprland blur shows through)   *
 *      rgba(8,12,20,0.55)   primary glass (panels, cards, headerbars)    *
 *      rgba(15,20,32,0.72)  deeper glass (inputs, hovered cards)         *
 *      rgba(5,7,12,0.82)    deepest glass (tooltips, popovers, dropdowns)*
 *      rgba(255,255,255,0.10) hairline borders                           *
 *      rgba(255,255,255,0.22) hover hairline                             *
 *      rgba(255,255,255,0.45) focus / selected accent                    *
 *      #e8edf5  primary text (off-white)                                 *
 *      #c8ccd6  secondary text                                           *
 *      #6a6e78  tertiary / disabled                                      *
 *      #ffffff  pure white (only on hover halos + selected pip)          *
 *                                                                         *
 *  No gold. No pink. No cyan. No green. No purple. No defaults.          *
 *  Every per-app neon class is collapsed to monochrome glass below.      *
 * ═══════════════════════════════════════════════════════════════════════ */

/* -- Root window: pure transparency. Hyprland blur shows the wallpaper.   */
window, window.background, window.solid-csd,
window.nyx-transparent, window.nyx-transparent.background,
window > .background, window > .solid-csd {
    background-color: transparent;
    background-image: none;
    color: #e8edf5;
}
/* Strip every container that an app might fill with an opaque color so      *
 * the Hyprland blur reaches the surface under our explicit glass panels.    */
window > *, window > box, window > overlay,
window > scrolledwindow, window > grid,
window > stack, window > viewport,
window > toolbarview, window > toolbarview > *,
window > windowhandle, window > windowhandle > *,
box, grid, stack, viewport, overlay,
scrolledwindow, scrolledwindow > viewport,
scrolledwindow > viewport > *,
overlay > * {
    background-color: transparent;
    background-image: none;
}

/* -- Universal text + font ------------------------------------------------ */
* {
    font-family: 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
    font-size: 14px;
    color: #e8edf5;
}
.nyx-mono, .nyx-mono *, .nyx-code, .nyx-code *,
.monospace, .monospace *,
textview.nyx-mono, textview.nyx-mono *,
textview.nyx-code, textview.nyx-code *,
.terminal, .terminal *,
vte-terminal, vte-terminal * {
    font-family: 'JetBrains Mono', 'Fira Code', 'DejaVu Sans Mono', monospace;
    font-size: 13px;
}
.nyx-display, .nyx-display *,
.nyx-clock, .nyx-clock *,
.nyx-headline, .nyx-headline *,
.nyx-app-title, .nyx-section-title,
.nyx-rainbow-title, .nyx-h1, .nyx-h2, .nyx-h3 {
    font-family: 'Architects Daughter', 'Caveat', 'Patrick Hand', cursive;
}
.nyx-h1 { font-size: 28px; color: #ffffff; }
.nyx-h2 { font-size: 22px; color: #e8edf5; }
.nyx-h3 { font-size: 18px; color: #c8ccd6; }
.nyx-dim,   .nyx-faint  { color: #6a6e78; }

/* -- Headerbar / titlebar: dark mirror glass plate ------------------------ */
headerbar, .titlebar {
    background-color: rgba(8, 12, 20, 0.62);
    background-image: none;
    color: #e8edf5;
    border-bottom: 1px solid rgba(255, 255, 255, 0.10);
    box-shadow: inset 0  1px 0 rgba(255, 255, 255, 0.10),
                inset 0 -1px 0 rgba(0,   0,  0,  0.40);
    padding: 6px 14px;
}
headerbar label, headerbar label.title,
.titlebar label, .titlebar label.title {
    color: #e8edf5;
    font-family: 'Architects Daughter', 'Caveat', 'Inter', cursive;
    text-shadow: 0  1px 0 rgba(0, 0, 0, 0.65),
                 0 -1px 0 rgba(255, 255, 255, 0.10);
}
headerbar button, .titlebar button {
    background-color: transparent;
    color: #e8edf5;
    border: 1px solid rgba(255, 255, 255, 0.10);
}
headerbar button:hover, .titlebar button:hover {
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.30);
    color: #ffffff;
}

/* -- Universal frosted-glass surface (every panel / card / frame / pane) -- *
 * One single dark mirror treatment for ALL containers. Eliminates every     *
 * per-app neon card class — they all collapse here. Everything is the same. */
.nyx-bg, .nyx-shell-bg, .nyx-frosted, .nyx-panel,
.nyx-godsapp-frame, .nyx-card, .nyx-card-dark, .nyx-hero,
.nyx-threat-score, .sage-issue, .nyx-doc-title,
.nyx-frost-cream, .nyx-frost-white-solid, .nyx-frost-fog,
.nyx-frost-white, .nyx-frost-tar, .nyx-frost-white-soft,
.nyx-frost-dark, .nyx-frost-deeper,
.nyx-frost-pink, .nyx-frost-cyan, .nyx-frost-purple,
.nyx-frost-gold, .nyx-frost-green, .nyx-frost-red, .nyx-frost-orange,
/* per-app card classes (home / notepad / passwords / weather style.py) */
.card-pink, .card-cyan, .card-purple, .card-gold, .card-indigo,
.card-green, .card-orange, .card-blue, .card-red, .card-white,
/* phantom theme.css consumers */
frame {
    background-color: rgba(8, 12, 20, 0.55);
    background-image: none;
    color: #e8edf5;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 14px;
    padding: 12px 14px;
    box-shadow: inset 0  1px 0 rgba(255, 255, 255, 0.08),
                inset 0 -1px 0 rgba(0,   0,  0,  0.45),
                0 4px 14px rgba(0, 0, 0, 0.35);
}
.nyx-card:hover, .card-pink:hover, .card-cyan:hover,
.card-purple:hover, .card-gold:hover, .card-indigo:hover,
.card-green:hover, .card-orange:hover, .card-blue:hover,
.card-red:hover, .nyx-frosted:hover {
    background-color: rgba(15, 20, 32, 0.72);
    border-color: rgba(255, 255, 255, 0.22);
}

/* Per-app neon halos collapse — no glow. Box-shadow stripped. */
.nyx-glow-pink, .nyx-glow-cyan, .nyx-glow-purple,
.nyx-glow-gold, .nyx-glow-green, .nyx-glow-red,
.card-pink-header-glyph, .card-cyan-header-glyph,
.card-purple-header-glyph, .card-gold-header-glyph,
.card-indigo-header-glyph, .card-green-header-glyph,
.card-orange-header-glyph, .card-blue-header-glyph,
.card-red-header-glyph,
.card-pink-header-title, .card-cyan-header-title,
.card-purple-header-title, .card-gold-header-title,
.card-indigo-header-title, .card-green-header-title,
.card-orange-header-title, .card-blue-header-title,
.card-red-header-title {
    color: #e8edf5;
    text-shadow: 0  1px 0 rgba(0,   0,  0,  0.65),
                 0 -1px 0 rgba(255, 255, 255, 0.10);
    box-shadow: none;
}
.card-pink-header-stamp, .card-cyan-header-stamp,
.card-purple-header-stamp, .card-gold-header-stamp,
.card-indigo-header-stamp, .card-green-header-stamp,
.card-orange-header-stamp, .card-blue-header-stamp,
.card-red-header-stamp,
.card-pink-footer, .card-cyan-footer, .card-purple-footer,
.card-gold-footer, .card-indigo-footer, .card-green-footer,
.card-orange-footer, .card-blue-footer, .card-red-footer {
    color: #6a6e78;
}
.card-pink-header-rule, .card-cyan-header-rule,
.card-purple-header-rule, .card-gold-header-rule,
.card-indigo-header-rule, .card-green-header-rule,
.card-orange-header-rule, .card-blue-header-rule,
.card-red-header-rule {
    background: rgba(255, 255, 255, 0.10);
    min-height: 1px;
}

/* -- Text views (notepad body, log surfaces) ------------------------------ */
textview {
    background-color: rgba(15, 20, 32, 0.62);
    color: #e8edf5;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 10px;
    padding: 10px 12px;
}
textview text { background-color: transparent; color: #e8edf5; }

/* -- Lists / rows --------------------------------------------------------- */
list, listview, listbox,
list > row, listview > row, listbox > row {
    background-color: transparent;
    color: #e8edf5;
}
listbox > row:hover, list > row:hover, listview > row:hover {
    background-color: rgba(255, 255, 255, 0.08);
}
listbox > row:selected, list > row:selected, listview > row:selected {
    background-color: rgba(255, 255, 255, 0.14);
    box-shadow: inset 3px 0 0 rgba(255, 255, 255, 0.85);
    color: #ffffff;
}

/* -- Scrollbars: off-white slider on transparent track -------------------- */
scrollbar { background-color: transparent; background: transparent; }
scrollbar slider {
    background-color: rgba(232, 237, 245, 0.30);
    border: none;
    border-radius: 6px;
    min-width: 8px;
    min-height: 8px;
}
scrollbar slider:hover  { background-color: rgba(255, 255, 255, 0.55); }
scrollbar slider:active { background-color: rgba(255, 255, 255, 0.85); }

/* -- Inputs --------------------------------------------------------------- */
entry, spinbutton,
.input-pink, .input-cyan, .input-purple, .input-gold,
.input-indigo, .input-green, .input-orange, .input-blue, .input-red {
    background-color: rgba(15, 20, 32, 0.62);
    background-image: none;
    color: #e8edf5;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 14px;
    caret-color: #ffffff;
}
entry:focus, spinbutton:focus,
.input-pink:focus, .input-cyan:focus, .input-purple:focus,
.input-gold:focus, .input-indigo:focus, .input-green:focus,
.input-orange:focus, .input-blue:focus, .input-red:focus {
    border-color: rgba(255, 255, 255, 0.45);
    box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.10);
}
entry placeholder, entry > placeholder { color: #6a6e78; }

/* -- Buttons (universal) -------------------------------------------------- */
button,
.btn-nav-pink, .btn-nav-cyan, .btn-nav-purple, .btn-nav-gold,
.btn-nav-indigo, .btn-nav-green, .btn-nav-orange, .btn-nav-blue, .btn-nav-red,
.btn-primary-pink, .btn-primary-cyan, .btn-primary-purple, .btn-primary-gold,
.btn-primary-indigo, .btn-primary-green, .btn-primary-orange,
.btn-primary-blue, .btn-primary-red,
.btn-icon-pink, .btn-icon-cyan, .btn-icon-purple, .btn-icon-gold,
.btn-icon-indigo, .btn-icon-green, .btn-icon-orange, .btn-icon-blue,
.btn-icon-red {
    background-color: rgba(15, 20, 32, 0.55);
    background-image: none;
    color: #e8edf5;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 10px;
    padding: 6px 14px;
    font-size: 14px;
    text-shadow: 0 1px 0 rgba(0, 0, 0, 0.65);
    transition: background-color 140ms ease, border-color 140ms ease,
                box-shadow 140ms ease, color 140ms ease;
    box-shadow: none;
}
button:hover,
.btn-nav-pink:hover, .btn-nav-cyan:hover, .btn-nav-purple:hover,
.btn-nav-gold:hover, .btn-nav-indigo:hover, .btn-nav-green:hover,
.btn-nav-orange:hover, .btn-nav-blue:hover, .btn-nav-red:hover,
.btn-primary-pink:hover, .btn-primary-cyan:hover, .btn-primary-purple:hover,
.btn-primary-gold:hover, .btn-primary-indigo:hover, .btn-primary-green:hover,
.btn-primary-orange:hover, .btn-primary-blue:hover, .btn-primary-red:hover,
.btn-icon-pink:hover, .btn-icon-cyan:hover, .btn-icon-purple:hover,
.btn-icon-gold:hover, .btn-icon-indigo:hover, .btn-icon-green:hover,
.btn-icon-orange:hover, .btn-icon-blue:hover, .btn-icon-red:hover {
    background-color: rgba(255, 255, 255, 0.12);
    border-color: rgba(255, 255, 255, 0.45);
    color: #ffffff;
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.10);
}
button:active, button:checked {
    background-color: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.55);
    color: #ffffff;
}
button:disabled {
    color: rgba(232, 237, 245, 0.30);
    border-color: rgba(255, 255, 255, 0.06);
}
button.suggested-action {
    border-color: rgba(255, 255, 255, 0.55);
    color: #ffffff;
}
button.suggested-action:hover {
    background-color: rgba(255, 255, 255, 0.18);
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.30);
}
button.destructive-action {
    border-color: rgba(255, 255, 255, 0.45);
    color: #e8edf5;
}
button.destructive-action:hover {
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.85);
}
button.flat {
    background-color: transparent;
    border-color: transparent;
}
button.flat:hover {
    background-color: rgba(255, 255, 255, 0.10);
    border-color: rgba(255, 255, 255, 0.18);
}

/* -- Sidebar / numbered tab list ----------------------------------------- */
.nyx-tab-list row, .nyx-tab-list listrow,
list.nyx-tab-list row, list.nyx-tab-list listrow {
    background-color: transparent;
    padding: 6px 12px;
    border-radius: 8px;
}
.nyx-tab-list row:hover, list.nyx-tab-list row:hover {
    background-color: rgba(255, 255, 255, 0.08);
}
.nyx-tab-list row:selected, list.nyx-tab-list row:selected {
    background-color: rgba(255, 255, 255, 0.14);
    box-shadow: inset 2px 0 0 #ffffff;
    color: #ffffff;
}
.nyx-tab-num {
    border: 1px solid rgba(255, 255, 255, 0.45);
    border-radius: 999px;
    padding: 0 8px;
    color: #e8edf5;
    font-family: 'JetBrains Mono', monospace;
    font-size: 12px;
    margin-right: 8px;
}

/* -- Switch (mono) -------------------------------------------------------- */
switch {
    background-color: rgba(15, 20, 32, 0.62);
    border: 1px solid rgba(255, 255, 255, 0.18);
}
switch:checked {
    background-color: rgba(255, 255, 255, 0.85);
    border-color: rgba(255, 255, 255, 0.95);
}
switch slider          { background-color: #c8ccd6; }
switch:checked slider  { background-color: #0a0a0c; }

/* -- Dropdowns / popovers / tooltips -------------------------------------- */
dropdown, dropdown > button {
    background-color: rgba(15, 20, 32, 0.72);
    color: #e8edf5;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 10px;
    padding: 4px 10px;
}
popover, popover > contents, popover > arrow {
    background-color: rgba(5, 7, 12, 0.92);
    background-image: none;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 12px;
    color: #e8edf5;
}
tooltip, tooltip.background {
    background-color: rgba(5, 7, 12, 0.96);
    background-image: none;
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 8px;
    color: #e8edf5;
    padding: 4px 8px;
}

/* -- Hero / rainbow titles (mono override — no neon) --------------------- */
.nyx-rainbow-title, .nyx-app-title, .nyx-section-title {
    color: #ffffff;
    text-shadow: 0  1px 0 rgba(0,   0,  0,  0.65),
                 0 -1px 0 rgba(255, 255, 255, 0.15),
                 0  0  18px rgba(255, 255, 255, 0.20);
}

/* -- Output / log / terminal area (deepest glass, mono font) ------------- */
.nyx-output, .nyx-output text, .nyx-output textview,
.nyx-output * textview {
    background-color: rgba(5, 7, 12, 0.82);
    color: #c8ccd6;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    font-size: 13px;
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 10px;
    padding: 10px 14px;
}

/* -- The signature outer frame (collapses to a single white hairline) ---- */
.nyx-chrome-edge, .nyx-godsapp-frame {
    border: 1px solid rgba(255, 255, 255, 0.18);
    border-radius: 14px;
    box-shadow:
        inset 0 0 0 1px rgba(255, 255, 255, 0.06),
        0 6px 20px rgba(0, 0, 0, 0.45);
}

/* -- Statusbar / footer --------------------------------------------------- */
.nyx-statusbar {
    color: #6a6e78;
    padding: 6px 14px;
    font-size: 13px;
    font-family: 'JetBrains Mono', 'Fira Code', monospace;
    background-color: transparent;
}

/* -- Phantom @nyx_* consumer overrides (in case @define-color leaks) ----- *
 * Phantom's nyxus_theme.css defines purple/pink/gold tokens used for      *
 * window bg, headerbars, h1/h2/h3, .nyx-card-active. We override the      *
 * consumers directly here at PRIORITY_USER so phantom looks identical to  *
 * every other NYXUS app.                                                   */
.nyx-card-active {
    border: 1px solid rgba(255, 255, 255, 0.55);
    box-shadow: 0 0 12px rgba(255, 255, 255, 0.18);
    background-color: rgba(15, 20, 32, 0.72);
}

"""

_CHROME_PROVIDER_INSTALLED = False


# ── Hover scramble effect ────────────────────────────────────────────────────
# When the mouse enters any plain Gtk.Label, the visible characters rapidly
# cycle through random ASCII/symbol chars and then "settle" left-to-right
# back to the original text -- the classic terminal-cipher / NYXUS hacker
# scramble. Effect lives entirely in chrome.py so it cascades to every app
# that calls install_chrome (~9 GTK apps) without per-app changes.
#
# Skips: Gtk.Entry / Gtk.TextView / Gtk.SpinButton (editable surfaces),
# labels using Pango markup (rainbow titles -- scrambling would destroy the
# spans), labels with .nyx-no-scramble / .nyx-mono / .nyx-code / .monospace,
# empty labels, and labels longer than 60 chars (status bars/footers).
_SCRAMBLE_POOL = ("!<>-_\\/[]{}=+*^?#@&%$" +
                  "ABCDEFGHIJKLMNOPQRSTUVWXYZ" +
                  "abcdefghijklmnopqrstuvwxyz" +
                  "0123456789")
_SCRAMBLE_TICK_MS    = 28      # frame interval
_SCRAMBLE_TOTAL_TICKS = 18     # ~500ms total animation
_SCRAMBLE_MAX_LEN     = 200    # r4: was 60 — bumped so status bars,
                               # full button labels, and footer copy
                               # all qualify for hover-scramble.


class _Scrambler:
    """Per-label scramble animator. One instance attached to each label."""
    __slots__ = ("label", "original", "tick_id", "step")

    def __init__(self, label: Gtk.Label):
        self.label    = label
        self.original = None
        self.tick_id  = 0
        self.step     = 0

    def trigger(self):
        # Don't re-trigger mid-animation
        if self.tick_id:
            return
        try:
            text = self.label.get_text() or ""
        except Exception:
            return
        if not text or len(text) > _SCRAMBLE_MAX_LEN:
            return
        self.original = text
        self.step     = 0
        try:
            self.tick_id = GLib.timeout_add(_SCRAMBLE_TICK_MS, self._tick)
        except Exception:
            self.tick_id = 0

    def _tick(self):
        self.step += 1
        if self.step >= _SCRAMBLE_TOTAL_TICKS or self.original is None:
            try: self.label.set_text(self.original or "")
            except Exception: pass
            self.tick_id = 0
            return False
        progress = self.step / _SCRAMBLE_TOTAL_TICKS
        reveal   = int(len(self.original) * progress)
        out = []
        for i, ch in enumerate(self.original):
            if i < reveal or ch in (" ", "\n", "\t"):
                out.append(ch)
            else:
                out.append(random.choice(_SCRAMBLE_POOL))
        try:
            self.label.set_text("".join(out))
        except Exception:
            self.tick_id = 0
            return False
        return True


_SCRAMBLE_OPT_OUT_CLASSES = (
    "nyx-no-scramble",
    # NOTE r4: per user request the scramble effect now applies to *every*
    # eligible label across every NYXUS app — including status bars,
    # footers, and mono-font labels. The only opt-out left is the explicit
    # `.nyx-no-scramble` class for cases where an app genuinely needs to
    # disable scrambling on a specific label (e.g. live tickers whose text
    # changes faster than the scramble animation can resolve).
)


def _attach_scramble_to_label(label: Gtk.Label) -> None:
    """Wire a single Gtk.Label up for hover-scramble. Idempotent + defensive."""
    try:
        if not isinstance(label, Gtk.Label):
            return
        if getattr(label, "_nyx_scramble_attached", False):
            return
        # Skip markup labels (rainbow titles etc.) -- scrambling would
        # destroy their Pango spans.
        try:
            if label.get_use_markup():
                return
        except Exception:
            pass
        # Opt-out CSS classes
        for cls in _SCRAMBLE_OPT_OUT_CLASSES:
            try:
                if label.has_css_class(cls):
                    return
            except Exception:
                pass
        text = ""
        try: text = label.get_text() or ""
        except Exception: pass
        if not text or len(text) > _SCRAMBLE_MAX_LEN:
            return

        scrambler = _Scrambler(label)
        motion = Gtk.EventControllerMotion()
        motion.connect("enter", lambda *_a: scrambler.trigger())
        label.add_controller(motion)
        label._nyx_scramble_attached = True
    except Exception as e:
        log.debug("attach_scramble label: %s", e)


def _walk_attach_scramble(widget) -> None:
    """Walk widget tree, attach scramble to every eligible Gtk.Label."""
    try:
        if widget is None:
            return
        if isinstance(widget, Gtk.Label):
            _attach_scramble_to_label(widget)
            return  # labels have no relevant children to walk
        # Skip editable surfaces -- never mess with user-entered text.
        if isinstance(widget, (Gtk.Entry, Gtk.TextView, Gtk.SpinButton,
                               Gtk.SearchEntry, Gtk.PasswordEntry)):
            return
        # Walk children. GTK4 widgets expose get_first_child/get_next_sibling.
        if hasattr(widget, "get_first_child"):
            child = widget.get_first_child()
            while child is not None:
                _walk_attach_scramble(child)
                child = child.get_next_sibling()
    except Exception as e:
        log.debug("walk scramble: %s", e)


def attach_scramble(widget) -> None:
    """Public helper -- apps can call this after building dynamic content
    to wire scramble onto newly-added labels. install_chrome already calls
    it once at install time + on a deferred re-walk; this is for apps that
    swap in big subtrees later (e.g. settings page changes)."""
    _walk_attach_scramble(widget)


def _install_global_css():
    global _CHROME_PROVIDER_INSTALLED
    if _CHROME_PROVIDER_INSTALLED: return
    try:
        prov = Gtk.CssProvider()
        # r12: substitute frost-tile placeholders with resolved file:// URLs.
        # Fetches the tile PNGs into ~/.cache/nyxus/graffiti/ on first call.
        # On fetch failure the placeholder becomes empty -> CSS falls back
        # gracefully to flat cream (background-image: url("") is a no-op).
        css_text = (CHROME_CSS if isinstance(CHROME_CSS, str)
                    else CHROME_CSS.decode("utf-8"))
        try:
            grid_url = _ensure_frost_tile(_FROST_TILE_GRID)
            glyph_url = _ensure_frost_tile(_FROST_TILE_GLYPHS)
            css_text = (css_text
                        .replace("__NYX_TILE_GRID__",   grid_url)
                        .replace("__NYX_TILE_GLYPHS__", glyph_url))
        except Exception as e:
            log.warning("frost tile substitute: %s", e)
            css_text = (css_text
                        .replace("__NYX_TILE_GRID__",   "")
                        .replace("__NYX_TILE_GLYPHS__", ""))
        css_bytes = css_text.encode("utf-8")
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


def _apply_size_policy(window: Gtk.Window) -> None:
    """r5: open SMALL and let GTK auto-grow to natural content size.
    Default 480x320 is intentionally small; min 320x240 so the user can
    shrink further. resizable=True + setting size_request to the small
    minimum (not the default) means content can request more space and
    the window will naturally expand to fit it. Universal NYXUS rule:
    every app + every flyout opens compact, then grows to its content."""
    try:
        window.unmaximize()
    except Exception: pass
    try:
        window.unfullscreen()
    except Exception: pass
    try:
        window.set_resizable(True)
    except Exception: pass
    try:
        window.set_default_size(480, 320)
    except Exception as e:
        log.debug("set_default_size: %s", e)
    try:
        # Min size only — natural request from content drives the actual size.
        window.set_size_request(320, 240)
    except Exception as e:
        log.debug("set_size_request: %s", e)


def install_chrome(window: Gtk.Window, *, page_key: str = "_home",
                   title_label: Optional[Gtk.Label] = None) -> None:
    """Install NYXUS chrome on `window`.

    NEW (r4): the window is made fully transparent so the user\'s desktop
    wallpaper shows through. The graffiti seen behind every app is the
    desktop wallpaper, NOT an embedded image. We no longer wrap the
    window\'s child in a Gtk.Overlay+GraffitiBackground (that was the old
    behaviour — it embedded the mural inside the app, which was wrong).

    What this function still does:
      * installs the global NYXUS CSS provider (Caveat font, neon
        button outlines, frosted-glass panels, GodsApp visual language)
      * forces a sensible 900x650 default window size and clears any
        fullscreen/maximize state the app may have set
      * marks the window transparent so Hyprland can apply blur on top
        of the wallpaper for the frosted-glass look
      * optionally swaps a hero label\'s markup to the rainbow palette
      * walks the widget tree and attaches hover-scramble onto every
        eligible Gtk.Label (with re-walks at +600ms / +2000ms for
        lazy-loaded content like Adw.PreferencesPage rows)

    Compatible with both `Gtk.ApplicationWindow`, `Gtk.Window`, and
    `Adw.ApplicationWindow`. Idempotent: safe to call repeatedly.
    `page_key` is accepted for backward compatibility with the previous
    GraffitiBackground-based API, but is no longer used for image
    selection (no more embedded images). Returns None."""
    if window is None:
        return None
    _install_global_css()
    _apply_size_policy(window)
    _make_window_transparent(window)

    # Re-entrancy guard. Use a plain attribute on the window itself —
    # Gtk.Widget.set_data was removed in PyGObject 3.42+ and would raise.
    if getattr(window, "_nyxus_chrome_installed", False):
        return None
    try:
        window._nyxus_chrome_installed = True
    except Exception:
        # Some widget subclasses are __slots__-locked; we tolerate that
        # and just lose the re-entrancy guard for those windows.
        pass

    # Find the current content widget (Adw uses get_content / Gtk uses
    # get_child) so we can run the scramble walk over it.
    cur = None
    try:
        if _is_adw_app_window(window):
            cur = window.get_content()
        elif hasattr(window, "get_child"):
            cur = window.get_child()
    except Exception as e:
        log.debug("install_chrome get content: %s", e)

    # Optional rainbow markup on a passed-in hero title.
    if title_label is not None:
        try:
            txt = title_label.get_text() or title_label.get_label() or ""
            if txt:
                title_label.set_use_markup(True)
                title_label.set_markup(rainbow_markup(txt))
                title_label.add_css_class("nyx-rainbow-title")
        except Exception as e:
            log.warning("install_chrome title: %s", e)

    # Hover-scramble walk. Walks immediately (static layout) and again
    # at +600ms / +2000ms (catches lazy/async-loaded content).
    try:
        target = cur if cur is not None else window
        _walk_attach_scramble(target)
        GLib.timeout_add(600,  lambda: (_walk_attach_scramble(target), False)[1])
        GLib.timeout_add(2000, lambda: (_walk_attach_scramble(target), False)[1])
    except Exception as e:
        log.debug("install_chrome scramble walk: %s", e)
    return None


def _make_window_transparent(window: Gtk.Window) -> None:
    """Mark the window with the .nyx-transparent CSS class and strip the
    .background class some apps add (which would re-paint the surface
    opaque). Combined with the global `window { background: transparent }`
    rule from CHROME_CSS this gives a fully see-through window surface
    that Hyprland can blur on top of the desktop wallpaper."""
    if window is None:
        return
    try:
        window.add_css_class("nyx-transparent")
    except Exception as e:
        log.debug("add nyx-transparent: %s", e)
    try:
        if window.has_css_class("background"):
            window.remove_css_class("background")
    except Exception:
        pass
    try:
        if window.has_css_class("solid-csd"):
            window.remove_css_class("solid-csd")
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# UNIVERSAL ENFORCEMENT (rev 2026-05-07 r13)
# ──────────────────────────────────────────────────────────────────────────────
# Until now, install_chrome() had to be called explicitly by every app — and
# any per-app set_default_size(900, 700) call would override the small-size
# policy. r13 fixes both by monkey-patching at module import time:
#
#   1. Gtk.Window.set_default_size  → clamped to NYXUS_MAX_DEFAULT (700x480)
#      so no app can open larger than the universal NYXUS default. Apps can
#      still be resized larger BY THE USER via the resizable window edge.
#   2. Gtk.Window.present / Adw.ApplicationWindow.present → wrapped to
#      auto-call install_chrome(self) on first present, so apps that forgot
#      to import or call install_chrome still get DARK MIRROR styling, the
#      small default size, and the transparent surface.
#
# Both patches are idempotent + crash-proof (each call is wrapped in try).
# ──────────────────────────────────────────────────────────────────────────────

NYXUS_MAX_DEFAULT_W = 700
NYXUS_MAX_DEFAULT_H = 480

_NYX_PATCHED_FLAG = "_nyxus_universal_patched"

def _nyx_install_universal_patches():
    """Monkey-patch Gtk.Window + Adw.ApplicationWindow exactly once."""
    try:
        if getattr(Gtk.Window, _NYX_PATCHED_FLAG, False):
            return
    except Exception:
        return

    # ── 1. Clamp set_default_size on EVERY Gtk.Window subclass ──────────────
    try:
        _orig_sds = Gtk.Window.set_default_size
        def _nyx_set_default_size(self, w, h):
            try:
                cw = min(int(w) if w and w > 0 else NYXUS_MAX_DEFAULT_W,
                         NYXUS_MAX_DEFAULT_W)
                ch = min(int(h) if h and h > 0 else NYXUS_MAX_DEFAULT_H,
                         NYXUS_MAX_DEFAULT_H)
                return _orig_sds(self, cw, ch)
            except Exception:
                return _orig_sds(self, w, h)
        Gtk.Window.set_default_size = _nyx_set_default_size
    except Exception as e:
        log.debug("nyx patch set_default_size: %s", e)

    # ── 2. Auto-install chrome on first present() ───────────────────────────
    try:
        _orig_present = Gtk.Window.present
        def _nyx_present(self, *a, **kw):
            try:
                if not getattr(self, "_nyxus_chrome_installed", False):
                    install_chrome(self)
                _apply_size_policy(self)
            except Exception as e:
                log.debug("nyx present hook: %s", e)
            return _orig_present(self, *a, **kw)
        Gtk.Window.present = _nyx_present
    except Exception as e:
        log.debug("nyx patch present: %s", e)

    # ── 3. Same for Adw.ApplicationWindow if available ──────────────────────
    try:
        import gi as _gi
        _gi.require_version("Adw", "1")
        from gi.repository import Adw as _Adw
        _orig_adw_present = _Adw.ApplicationWindow.present
        def _nyx_adw_present(self, *a, **kw):
            try:
                if not getattr(self, "_nyxus_chrome_installed", False):
                    install_chrome(self)
                _apply_size_policy(self)
            except Exception as e:
                log.debug("nyx adw present hook: %s", e)
            return _orig_adw_present(self, *a, **kw)
        _Adw.ApplicationWindow.present = _nyx_adw_present
    except Exception as e:
        log.debug("nyx patch Adw.present (Adw missing is OK): %s", e)

    try:
        setattr(Gtk.Window, _NYX_PATCHED_FLAG, True)
    except Exception:
        pass

# Install patches at module import — every script that imports nyxus_chrome
# gets universal enforcement, even if it never explicitly calls install_chrome.
try:
    _nyx_install_universal_patches()
except Exception as _e:
    log.warning("nyxus_chrome universal patch failed: %s", _e)
