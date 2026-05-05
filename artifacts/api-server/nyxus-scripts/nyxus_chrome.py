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
NYXUS_CHROME_VERSION = "2026.05.05-r11"

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
/* === NYXUS Universal App Chrome — GodsApp visual language =========== *
 *                                                                       *
 * The window itself is FULLY TRANSPARENT so the user\'s desktop          *
 * wallpaper shows through. The "graffiti" the user sees behind every    *
 * app IS the desktop wallpaper, NOT an embedded image — apps must       *
 * never paint their own background. Inner content panels use a          *
 * translucent dark wash ("frosted glass") so text stays legible against *
 * any wallpaper. Combined with Hyprland\'s blur on transparent windows,  *
 * this gives the GodsApp screenshot look across every NYXUS app.        *
 * =================================================================== */

/* -- Root window: pure transparency, NO background image -------------- *
 * r5: also strip background-color from EVERY direct child of the window  *
 * (covers apps that paint a coloured root box, including the purple-     *
 * tinted ones the user reported). The frosted-glass wash is applied      *
 * ONLY via the explicit .nyx-frosted/.nyx-panel/.nyx-godsapp-frame       *
 * classes from now on, never automatically — that prevents any app from  *
 * accidentally turning the whole window opaque.                          */
window, window.background, window.solid-csd,
window.nyx-transparent, window.nyx-transparent.background {
    background-color: transparent;
    background-image: none;
    color: #1a1816;   /* r11: dark ink for Seattle Frost cream wash */
}
/* Strip any background paint that an app or Adw bin paints on the root  *
 * widget directly under the window. Inner panels still get frosted via  *
 * their explicit .nyx-* classes below.                                  */
window > *, window > box, window > overlay,
window > scrolledwindow, window > grid,
window > stack, window > viewport,
window > .background, window > .solid-csd,
window > toolbarview, window > toolbarview > *,
window > headerbar, window > windowhandle, window > windowhandle > * {
    background-color: transparent;
    background-image: none;
}

/* -- Frosted-glass wash: ONLY when an app opts in via these classes ---- *
 * r11: FLIPPED from dark (rgba 10,10,18,0.72) to Seattle Frost cream.   *
 * This is THE single change that converts every app from neon-on-black  *
 * to misty-white-on-cream without touching app code. .nyx-card stays    *
 * cream (already in tier-1 below), so no override needed.              */
.nyx-bg, .nyx-shell-bg, .nyx-frosted, .nyx-panel,
.nyx-godsapp-frame {
    background-color: rgba(245, 243, 239, 0.72);
    color: #1a1816;
}
.nyx-bg label, .nyx-shell-bg label, .nyx-frosted label,
.nyx-panel label, .nyx-godsapp-frame label,
.nyx-bg > *, .nyx-shell-bg > *, .nyx-frosted > *,
.nyx-panel > *, .nyx-godsapp-frame > * {
    color: #1a1816;
}

/* === ACCENT FROST PALETTE — apply to any panel for tinted frosted glass.
 * Layer with .nyx-frosted-* + .nyx-glow-* for soft neon halo.        === */
.nyx-frost-dark    { background-color: rgba(10, 10, 18, 0.65); border-radius: 10px; }
.nyx-frost-deeper  { background-color: rgba(5, 5, 12, 0.82);  border-radius: 10px; }
.nyx-frost-pink    { background-color: rgba(255, 0, 180, 0.28);  border-radius: 10px;
                     border: 1px solid rgba(255, 0, 180, 0.55); }
.nyx-frost-cyan    { background-color: rgba(0, 200, 255, 0.26);  border-radius: 10px;
                     border: 1px solid rgba(0, 200, 255, 0.55); }
.nyx-frost-purple  { background-color: rgba(140, 60, 220, 0.30); border-radius: 10px;
                     border: 1px solid rgba(140, 60, 220, 0.55); }
.nyx-frost-gold    { background-color: rgba(255, 200, 60, 0.24); border-radius: 10px;
                     border: 1px solid rgba(255, 215, 0, 0.65); }
.nyx-frost-green   { background-color: rgba(60, 255, 140, 0.24); border-radius: 10px;
                     border: 1px solid rgba(57, 255, 20, 0.55); }
.nyx-frost-red     { background-color: rgba(255, 60, 80, 0.30);  border-radius: 10px;
                     border: 1px solid rgba(255, 80, 100, 0.55); }
.nyx-frost-orange  { background-color: rgba(255, 140, 0, 0.26);  border-radius: 10px;
                     border: 1px solid rgba(255, 140, 0, 0.55); }

.nyx-glow-pink   { box-shadow: 0 0 18px rgba(255, 0, 180, 0.45); }
.nyx-glow-cyan   { box-shadow: 0 0 18px rgba(0, 200, 255, 0.45); }
.nyx-glow-purple { box-shadow: 0 0 18px rgba(140, 60, 220, 0.55); }
.nyx-glow-gold   { box-shadow: 0 0 22px rgba(255, 215, 0, 0.65); }
.nyx-glow-green  { box-shadow: 0 0 18px rgba(57, 255, 20, 0.45); }
.nyx-glow-red    { box-shadow: 0 0 18px rgba(255, 80, 100, 0.55); }

/* === SEATTLE-WASHED TRI-TONE PALETTE ============================= *
 * Aged paper / overcast fog / sun-bleached espresso. Muted, warm    *
 * greys instead of pure white-on-black so neon accents sing. Think  *
 * driftwood, weathered concrete, washed denim, faded tarmac.        *
 *                                                                    *
 *   .nyx-frost-cream  → warm off-white milk-glass, nearly solid      *
 *   .nyx-frost-fog    → light driftwood-grey, wallpaper hints through*
 *   .nyx-frost-tar    → sun-bleached espresso-black, warm light text *
 *                                                                    *
 * Plus legacy aliases (.nyx-frost-white-solid etc.) so existing      *
 * apps keep working without churn.                                  */

/* TIER 1 — cream / aged-paper hero. Heavy frost, you can read code */
.nyx-frost-cream,
.nyx-frost-white-solid {
    background-color: rgba(245, 243, 239, 0.92);
    border: 1px solid rgba(255, 252, 244, 0.85);
    border-radius: 12px;
    color: #1a1816;
}
.nyx-frost-cream label, .nyx-frost-cream > *,
.nyx-frost-white-solid label, .nyx-frost-white-solid > * {
    color: #1a1816;
}

/* TIER 2 — fog / overcast Seattle grey. Wallpaper bleeds through.  */
.nyx-frost-fog,
.nyx-frost-white {
    background-color: rgba(220, 217, 211, 0.72);
    border: 1px solid rgba(245, 243, 239, 0.55);
    border-radius: 12px;
    color: #2a2622;
}
.nyx-frost-fog label, .nyx-frost-fog > *,
.nyx-frost-white label, .nyx-frost-white > * {
    color: #2a2622;
}

/* TIER 3 — tar / sun-bleached espresso. Warm faded black w/ cream ink */
.nyx-frost-tar {
    background-color: rgba(42, 38, 34, 0.78);
    border: 1px solid rgba(176, 172, 164, 0.35);
    border-radius: 12px;
    color: #f0ede7;
}
.nyx-frost-tar label, .nyx-frost-tar > * { color: #f0ede7; }

/* Very translucent variant — image-2 wallpaper-forward look */
.nyx-frost-white-soft {
    background-color: rgba(245, 243, 239, 0.30);
    border: 1px solid rgba(245, 243, 239, 0.45);
    border-radius: 12px;
    color: #1a1816;
}
.nyx-frost-white-soft label, .nyx-frost-white-soft > * { color: #1a1816; }

/* Shield/sage/studio hero widgets — auto-promote shared classes to *
 * the cream-paper tier so apps inherit the look without code edits.*/
.nyx-card,
.nyx-hero,
.nyx-threat-score,
.sage-issue,
.nyx-doc-title {
    background-color: rgba(245, 243, 239, 0.88);
    color: #1a1816;
    border: 1px solid rgba(176, 172, 164, 0.45);
    border-radius: 12px;
    padding: 12px;
}
.nyx-card label, .nyx-card > *,
.nyx-hero  label, .nyx-hero  > *,
.sage-issue label, .sage-issue > *,
.nyx-threat-score, .nyx-threat-label {
    color: #1a1816;
}
.nyx-threat-score { font-size: 38px; font-weight: bold; color: #1a1816; }
/* Keep plain — em-unit spacing breaks GTK4 stylesheet load */
.nyx-threat-label { font-size: 14px; color: #5c5852; }

/* Opt-out: any app that needs the original dark card explicitly. */
.nyx-card-dark {
    background-color: rgba(42, 38, 34, 0.78);
    color: #f0ede7;
    border: 1px solid rgba(176, 172, 164, 0.35);
    border-radius: 12px;
}
.nyx-card-dark label, .nyx-card-dark > * { color: #f0ede7; }

/* === UNIVERSAL frost for content widgets that apps commonly paint solid.
 * Catches GTK textview/entry/listrows everywhere so leftover solid bg
 * panels become frosted automatically without per-app patches.       === */
textview {
    background-color: rgba(245, 243, 239, 0.85);   /* r11: cream glass */
    color: #1a1816;                                /* r11: pencil-ink */
    border-radius: 8px;
}
textview text { background-color: transparent; color: #1a1816; }

scrolledwindow > viewport,
scrolledwindow > viewport > * {
    background-color: transparent;
}

list, listview, listbox,
list > row, listview > row, listbox > row {
    background-color: transparent;
    color: #1a1816;   /* r11: dark ink on cream */
}
listbox > row:hover, list > row:hover, listview > row:hover {
    background-color: rgba(49, 49, 49, 0.12);   /* r11: charcoal smoke */
}
listbox > row:selected, list > row:selected, listview > row:selected {
    background-color: rgba(49, 49, 49, 0.22);
    box-shadow: inset 3px 0 0 rgba(26, 24, 22, 0.85);
}

frame > border { border-color: rgba(192, 132, 252, 0.30); }

/* Scrollbars: r11 — pencil-grey default, charcoal on hover */
scrollbar { background: transparent; }
scrollbar slider {
    background: rgba(49, 49, 49, 0.45);
    border-radius: 4px;
    min-width: 8px;
    min-height: 8px;
}
scrollbar slider:hover {
    background: rgba(26, 24, 22, 0.85);
}

/* -- Typography: r11 Seattle Frost font policy ---------------------- *
 *  - Body / labels / menus / app content → Inter (clean sans-serif)   *
 *  - Display / titles / clock / workspace names → Architects Daughter *
 *  - Code / terminal / hex → JetBrains Mono (opt-in via .nyx-mono)    *
 *  Falls back through hand-drawn alternatives if Inter/AD missing.    */
* {
    font-family: \'Inter\', \'Inter Light\', \'Cantarell\', \'DejaVu Sans\', sans-serif;
    font-size: 14px;
}
.nyx-display, .nyx-display *,
.nyx-clock, .nyx-clock *,
.nyx-workspace, .nyx-workspace *,
.nyx-headline, .nyx-headline *,
.nyx-app-title, .nyx-section-title,
.nyx-rainbow-title {
    font-family: \'Architects Daughter\', \'Caveat\', \'Patrick Hand\', \'Comic Sans MS\', cursive;
}
/* Opt-out for code/terminal/log surfaces — keep them in real mono. */
.nyx-mono, .nyx-mono *,
.nyx-code, .nyx-code *,
.monospace, .monospace *,
textview.nyx-mono, textview.nyx-mono *,
textview.nyx-code, textview.nyx-code *,
.terminal, .terminal *,
vte-terminal, vte-terminal * {
    font-family: \'JetBrains Mono\', \'Fira Code\', \'DejaVu Sans Mono\', monospace;
    font-size: 13px;
}

/* -- Headerbar / titlebar: r11 cream frosted, charcoal pencil line --- */
headerbar, .titlebar {
    background-color: rgba(245, 243, 239, 0.78);
    color: #1a1816;
    border-bottom: 1px solid rgba(49, 49, 49, 0.27);
}

/* -- Text inputs: r11 cream glass, charcoal focus ring -------------- */
entry, spinbutton {
    background-color: rgba(255, 255, 255, 0.55);
    color: #1a1816;
    border: 1px solid rgba(49, 49, 49, 0.35);
    border-radius: 10px;
    padding: 8px 14px;
    font-size: 14px;
    caret-color: #1a1816;
}
entry:focus, spinbutton:focus {
    border-color: rgba(26, 24, 22, 0.85);
    box-shadow: 0 0 0 2px rgba(209, 209, 209, 0.55);
}
entry placeholder, entry > placeholder { color: #8a8580; }

/* -- Buttons: r11 cream glass, charcoal pencil outline -------------- */
button {
    background-color: rgba(255, 255, 255, 0.45);
    color: #1a1816;
    border: 1px solid rgba(49, 49, 49, 0.45);
    border-radius: 10px;
    padding: 6px 14px;
    font-size: 14px;
    transition: background-color 140ms ease, box-shadow 140ms ease,
                border-color 140ms ease;
}
button:hover {
    background-color: rgba(255, 255, 255, 0.78);
    border-color: rgba(26, 24, 22, 0.85);
}
button:active, button:checked {
    background-color: rgba(209, 209, 209, 0.65);
    border-color: rgba(26, 24, 22, 0.95);
}
button:disabled {
    color: rgba(26, 24, 22, 0.35);
    border-color: rgba(49, 49, 49, 0.18);
}

/* Adwaita semantic button classes — purple = action, red = danger */
button.suggested-action {
    border-color: rgba(192, 132, 252, 0.95);
    color: #c084fc;
}
button.suggested-action:hover {
    box-shadow: 0 0 14px rgba(192, 132, 252, 0.65);
}
button.destructive-action {
    border-color: rgba(255, 80, 100, 0.85);
    color: #ff5066;
}
button.destructive-action:hover {
    box-shadow: 0 0 14px rgba(255, 80, 100, 0.65);
}
button.flat {
    border-color: transparent;
    background-color: transparent;
}
button.flat:hover {
    background-color: rgba(255, 0, 255, 0.10);
    border-color: rgba(255, 0, 255, 0.35);
}

/* -- GodsApp\'s color-cycling action button row ---------------------- */
/* Wrap a Gtk.Box of buttons in .nyx-rainbow-row to get the look.    */
.nyx-rainbow-row > button:nth-child(2n)   { border-color: rgba(0,170,255,0.85); }
.nyx-rainbow-row > button:nth-child(2n):hover { box-shadow: 0 0 14px rgba(0,170,255,0.55); }
.nyx-rainbow-row > button:nth-child(3n)   { border-color: rgba(255,215,0,0.85); }
.nyx-rainbow-row > button:nth-child(3n):hover { box-shadow: 0 0 14px rgba(255,215,0,0.55); }
.nyx-rainbow-row > button:nth-child(4n)   { border-color: rgba(57,255,20,0.85); }
.nyx-rainbow-row > button:nth-child(4n):hover { box-shadow: 0 0 14px rgba(57,255,20,0.55); }

/* -- The "GOD MODE" gold action button ------------------------------ */
.nyx-god-mode {
    border-color: rgba(255, 215, 0, 0.95);
    color: #ffd700;
    font-weight: 700;
    text-shadow: 0 0 6px rgba(255, 215, 0, 0.55);
}
.nyx-god-mode:hover {
    background-color: rgba(255, 215, 0, 0.15);
    box-shadow: 0 0 18px rgba(255, 215, 0, 0.75);
}

/* -- Numbered sidebar tabs (01, 02, 03, ...) — GodsApp left rail --- */
.nyx-tab-list row, .nyx-tab-list listrow,
list.nyx-tab-list row, list.nyx-tab-list listrow {
    background-color: transparent;
    padding: 4px 12px;
    border-radius: 8px;
}
.nyx-tab-list row:hover, list.nyx-tab-list row:hover {
    background-color: rgba(192, 132, 252, 0.10);
}
.nyx-tab-list row:selected, list.nyx-tab-list row:selected {
    background-color: rgba(192, 132, 252, 0.18);
    box-shadow: inset 2px 0 0 #c084fc;
}
.nyx-tab-num {
    border: 1px solid rgba(0, 255, 255, 0.85);
    border-radius: 999px;
    padding: 0 8px;
    color: #00ffff;
    font-family: \'JetBrains Mono\', monospace;
    font-size: 12px;
    margin-right: 8px;
}

/* -- Switch: neon pink when active ---------------------------------- */
switch:checked {
    background-color: rgba(255, 0, 255, 0.65);
}
switch:checked slider { background-color: #ffe0ff; }

/* -- Hero / rainbow / title labels --------------------------------- */
.nyx-rainbow-title {
    font-family: \'Caveat\', \'Patrick Hand\', cursive;
    font-weight: bold;
    font-size: 32px;
    text-shadow: 0 0 14px rgba(255, 255, 255, 0.55),
                 0 0 28px rgba(255, 0, 255, 0.45),
                 0 0 42px rgba(0, 255, 255, 0.30);
}
.nyx-app-title {
    font-family: \'Caveat\', \'Patrick Hand\', cursive;
    font-size: 36px;
    color: #efefee;
    text-shadow: 0 0 12px rgba(255, 0, 255, 0.45);
}
.nyx-section-title {
    font-family: \'Caveat\', \'Patrick Hand\', cursive;
    font-size: 26px;
    color: #efefee;
}

/* -- Status / footer bar -------------------------------------------- */
.nyx-statusbar {
    color: #8a8a93;
    padding: 6px 14px;
    font-size: 13px;
    font-family: \'JetBrains Mono\', \'Fira Code\', monospace;
    background-color: transparent;
}

/* -- Convenience text classes -------------------------------------- */
.nyx-dim   { color: #aeaeb6; }
.nyx-faint { color: #6c6c75; }

/* -- Output / log / terminal area (black frosted, mono) ----------- */
.nyx-output, .nyx-output text, .nyx-output textview,
.nyx-output * textview {
    background-color: rgba(0, 0, 0, 0.78);
    color: #d8d8de;
    font-family: \'JetBrains Mono\', \'Fira Code\', monospace;
    font-size: 13px;
    border: 1px solid rgba(192, 132, 252, 0.45);
    border-radius: 10px;
    padding: 10px 14px;
}

/* -- The signature GodsApp neon-gradient outer frame --------------- */
/* Apps wrap their root in a Gtk.Frame with .nyx-godsapp-frame to     */
/* get the multi-color glow border seen in the godsapp screenshot.   */
.nyx-chrome-edge, .nyx-godsapp-frame {
    border: 2px solid rgba(192, 132, 252, 0.95);
    border-radius: 14px;
    box-shadow:
        inset 0 0 0 2px rgba(255, 0, 255, 0.55),
        0 0 24px rgba(192, 132, 252, 0.55),
        0 0 48px rgba(255, 0, 255, 0.30),
        0 0 72px rgba(0, 255, 255, 0.20);
}

/* -- Scrollbars: neon pink slider on transparent track ------------- */
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

/* -- Tooltips ------------------------------------------------------ */
tooltip {
    background-color: rgba(10, 10, 18, 0.96);
    border: 1px solid rgba(255, 0, 255, 0.55);
    border-radius: 8px;
    color: #efefee;
}

/* -- Dropdowns + popovers (Quick selector, settings menus, etc.) -- */
dropdown, dropdown > button {
    background-color: rgba(0, 0, 0, 0.55);
    color: #efefee;
    border: 1px solid rgba(192, 132, 252, 0.55);
    border-radius: 10px;
    padding: 4px 10px;
}
popover, popover > contents, popover > arrow {
    background-color: rgba(10, 10, 18, 0.96);
    border: 1px solid rgba(192, 132, 252, 0.55);
    border-radius: 12px;
    color: #efefee;
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
