"""
NYXUS Panel — News card widgets.

Two card variants:
  • HeroCard  — large image, big headline; one per refresh, sits at top of feed
  • SubCard   — thumbnail-left layout for the masonry feed

Each card renders title, source + favicon, time-ago, and an action row
(heart / bookmark / share).  Clicking the card opens the article in the
configured browser.

© 2026 Joseph A. Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import os
import shlex
import subprocess
import time
from typing import Any, Callable, Dict, Optional

import gi

# ── NYXUS palette (single source of truth · rev r13) ────────────────
try:
    from nyxus_palette import (
        WHITE_PURE, WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        INK_FADED, INK_BLACK,
        GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE, HAIRLINE_INK,
        SHADOW_INK_ACTIVE, SHADOW_INK_INACTIVE,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
        format_css, assert_no_forbidden,
    )
except Exception:
    # palette module is shipped alongside every NYXUS app via
    # nyxus_install.sh; if it's missing, fall back to literals so
    # the app still launches.
    WHITE_PURE='#ffffff'; WHITE_OFF='#eef2fa'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    INK_FADED='#0a0a0a'; INK_BLACK='#000000'
    GLASS_DARK='rgba(8, 12, 20, 0.55)'
    GLASS_DEEPER='rgba(15, 20, 32, 0.72)'
    GLASS_DEEPEST='rgba(5, 7, 12, 0.92)'
    HAIRLINE_WHITE='rgba(255, 255, 255, 0.10)'
    HAIRLINE_INK='rgba(0, 0, 0, 0.45)'
    SHADOW_INK_ACTIVE='rgba(0, 0, 0, 0.65)'
    SHADOW_INK_INACTIVE='rgba(0, 0, 0, 0.20)'
    RADIUS_CARD=14; RADIUS_PILL=12; RADIUS_INPUT=10
    FONT_UI='Inter'; FONT_MONO='JetBrains Mono'; FONT_DISPLAY='Inter Display'
    def format_css(t):
        _d = {
            'WHITE_PURE': WHITE_PURE, 'WHITE_OFF': WHITE_OFF,
            'GREY_LIGHT': GREY_LIGHT, 'GREY_MID': GREY_MID,
            'GREY_TERTIARY': GREY_TERTIARY,
            'INK_FADED': INK_FADED, 'INK_BLACK': INK_BLACK,
            'GLASS_DARK': GLASS_DARK, 'GLASS_DEEPER': GLASS_DEEPER,
            'GLASS_DEEPEST': GLASS_DEEPEST,
            'HAIRLINE_WHITE': HAIRLINE_WHITE, 'HAIRLINE_INK': HAIRLINE_INK,
            'SHADOW_INK_ACTIVE': SHADOW_INK_ACTIVE,
            'SHADOW_INK_INACTIVE': SHADOW_INK_INACTIVE,
            'RADIUS_CARD': RADIUS_CARD, 'RADIUS_PILL': RADIUS_PILL,
            'RADIUS_INPUT': RADIUS_INPUT,
            'FONT_UI': FONT_UI, 'FONT_MONO': FONT_MONO,
            'FONT_DISPLAY': FONT_DISPLAY,
        }
        return t.format_map(_d)
    def assert_no_forbidden(*a, **k): pass
# ─────────────────────────────────────────────────────────────────────

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf, Pango  # noqa: E402


# ─────────────────────────────────────────── helpers
def time_ago(ts: float) -> str:
    if not ts:
        return ""
    now = time.time()
    d = max(0, now - ts)
    if d < 60:        return "just now"
    if d < 3600:      return f"{int(d/60)}m ago"
    if d < 86400:     return f"{int(d/3600)}h ago"
    if d < 7*86400:   return f"{int(d/86400)}d ago"
    return time.strftime("%b %-d", time.localtime(ts))


def _open_in_browser(url: str, cfg: Dict[str, Any]) -> None:
    if not url:
        return
    browser = cfg.get("browser", "chromium")
    private = cfg.get("browser_private", False)
    args = [browser]
    if private:
        if browser in ("chromium", "google-chrome", "brave"):
            args.append("--incognito")
        elif browser == "firefox":
            args.append("--private-window")
    args.append(url)
    try:
        subprocess.Popen(
            args,
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        # last-ditch fallback
        try:
            subprocess.Popen(
                ["xdg-open", url],
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            pass


def _copy_to_clipboard(url: str) -> None:
    disp = Gdk.Display.get_default()
    if disp is None:
        return
    cb = disp.get_clipboard()
    cb.set(url)


def _picture_from_path(path: Optional[str], w: int, h: int) -> Gtk.Widget:
    if path and os.path.exists(path):
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(path, w, h, True)
            pic = Gtk.Picture.new_for_pixbuf(pix)
            pic.set_can_shrink(True); pic.set_content_fit(Gtk.ContentFit.COVER)
            pic.set_size_request(w, h)
            pic.add_css_class("nyxus-card-img")
            return pic
        except Exception:
            pass
    # placeholder
    ph = Gtk.Box(orientation=Gtk.Orientation.VERTICAL); ph.set_size_request(w, h)
    ph.add_css_class("nyxus-card-img-placeholder")
    g = Gtk.Label(label="\uf03e"); g.set_valign(Gtk.Align.CENTER); g.set_halign(Gtk.Align.CENTER)
    g.add_css_class("nyxus-card-img-glyph"); g.set_vexpand(True); g.set_hexpand(True)
    ph.append(g)
    return ph


# ─────────────────────────────────────────── base card
class _ArticleCard(Gtk.Box):
    """Common click + actions wrapper for hero / sub variants."""

    def __init__(self, article: Dict[str, Any], cfg_provider: Callable[[], Dict[str, Any]],
                 cfg_updater: Callable[[Dict[str, Any]], None]):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._article = article
        self._cfg = cfg_provider
        self._save_cfg = cfg_updater
        self._click = Gtk.GestureClick()
        self._click.connect("released", self._on_click)
        self.add_controller(self._click)
        self.set_cursor_from_name("pointer")

    def _on_click(self, gesture, n_press, x, y) -> None:
        # Use widget hit-testing to find what was actually clicked.  Buttons
        # have their own click controllers that claim the sequence first, so
        # in practice we only get here when the click missed the action row,
        # but we double-check via Widget.pick() to be safe.
        widget = gesture.get_widget()
        if widget is None:
            return
        target = widget.pick(x, y, Gtk.PickFlags.DEFAULT) if hasattr(widget, "pick") else None
        w = target
        while w is not None and w is not widget:
            if isinstance(w, Gtk.Button):
                return
            w = w.get_parent()
        _open_in_browser(self._article.get("link", ""), self._cfg())

    def _action_row(self) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4,
                      margin_top=4, margin_start=4, margin_end=4, margin_bottom=4)
        cfg = self._cfg()
        url = self._article.get("link", "")
        is_saved = url in cfg.get("saved_articles", [])
        is_later = url in cfg.get("read_later", [])

        heart    = self._mini_button("\uf004",  "Save",        active=is_saved)
        bookmark = self._mini_button("\uf02e",  "Read later",  active=is_later)
        share    = self._mini_button("\uf0c1",  "Copy link")

        def _toggle(key: str, on_done: Callable[[bool], None]):
            def handler(_b):
                c = self._cfg()
                lst = list(c.get(key, []))
                if url in lst:
                    lst.remove(url)
                    on_done(False)
                else:
                    lst.append(url)
                    on_done(True)
                c[key] = lst
                self._save_cfg(c)
            return handler

        def _set_btn_active(b: Gtk.Button, active: bool):
            if active:
                b.add_css_class("nyxus-action-active")
            else:
                b.remove_css_class("nyxus-action-active")

        heart.connect("clicked",    _toggle("saved_articles", lambda a: _set_btn_active(heart, a)))
        bookmark.connect("clicked", _toggle("read_later",     lambda a: _set_btn_active(bookmark, a)))
        share.connect("clicked",    lambda *_: _copy_to_clipboard(url))

        spacer = Gtk.Label(label=""); spacer.set_hexpand(True)
        row.append(spacer); row.append(heart); row.append(bookmark); row.append(share)
        return row

    def _mini_button(self, glyph: str, tooltip: str, active: bool = False) -> Gtk.Button:
        b = Gtk.Button(label=glyph)
        b.add_css_class("nyxus-action")
        if active:
            b.add_css_class("nyxus-action-active")
        b.set_tooltip_text(tooltip)
        return b

    def _meta_row(self) -> Gtk.Box:
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        # favicon
        fav = self._article.get("favicon")
        if fav and os.path.exists(fav):
            try:
                pix = GdkPixbuf.Pixbuf.new_from_file_at_scale(fav, 14, 14, True)
                ico = Gtk.Image.new_from_pixbuf(pix)
                row.append(ico)
            except Exception:
                pass
        src = Gtk.Label(label=self._article.get("source_label", ""))
        src.add_css_class("nyxus-card-source"); src.set_xalign(0)
        ts  = Gtk.Label(label=time_ago(self._article.get("published", 0)))
        ts.add_css_class("nyxus-card-time")
        spacer = Gtk.Label(label=""); spacer.set_hexpand(True)
        row.append(src); row.append(spacer); row.append(ts)
        return row


# ─────────────────────────────────────────── hero card
class HeroCard(_ArticleCard):
    def __init__(self, article: Dict[str, Any], cfg_provider, cfg_updater):
        super().__init__(article, cfg_provider, cfg_updater)
        self.add_css_class("nyxus-card"); self.add_css_class("nyxus-card-hero")

        img = _picture_from_path(article.get("thumb"), 408, 156)
        self.append(img)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                       margin_top=10, margin_bottom=8, margin_start=12, margin_end=12)
        title = Gtk.Label(label=article.get("title", "(untitled)"))
        title.set_xalign(0); title.set_wrap(True)
        title.set_lines(3); title.set_ellipsize(Pango.EllipsizeMode.END)
        title.add_css_class("nyxus-card-title-hero")
        body.append(title)
        body.append(self._meta_row())
        self.append(body)
        self.append(self._action_row())


# ─────────────────────────────────────────── sub card
class SubCard(_ArticleCard):
    def __init__(self, article: Dict[str, Any], cfg_provider, cfg_updater):
        super().__init__(article, cfg_provider, cfg_updater)
        self.add_css_class("nyxus-card"); self.add_css_class("nyxus-card-sub")

        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10,
                    margin_top=8, margin_bottom=4, margin_start=8, margin_end=8)
        img = _picture_from_path(article.get("thumb"), 92, 78)
        h.append(img)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        body.set_hexpand(True)
        title = Gtk.Label(label=article.get("title", "(untitled)"))
        title.set_xalign(0); title.set_wrap(True)
        title.set_lines(2); title.set_ellipsize(Pango.EllipsizeMode.END)
        title.add_css_class("nyxus-card-title")
        body.append(title)
        body.append(self._meta_row())
        h.append(body)
        self.append(h)
        self.append(self._action_row())


__all__ = ["HeroCard", "SubCard", "time_ago"]
