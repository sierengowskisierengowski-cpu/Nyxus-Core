"""
Meli brand widget — glowing honeypot logo + wordmark, reusable across the app.
"""
from __future__ import annotations

from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk  # noqa: E402


_ASSETS = Path(__file__).resolve().parent.parent.parent.parent / "assets"
_LOGO_PATH = _ASSETS / "icons" / "meli.svg"


def _logo_picture(size_px: int) -> Gtk.Widget:
    """Return a Gtk.Picture of the Meli logo at the requested square size."""
    if _LOGO_PATH.exists():
        pic = Gtk.Picture.new_for_filename(str(_LOGO_PATH))
        pic.set_can_shrink(True)
        pic.set_content_fit(Gtk.ContentFit.CONTAIN)
        pic.set_size_request(size_px, size_px)
        pic.add_css_class("meli-brand-logo")
        return pic
    # Fallback — typographic M
    lbl = Gtk.Label(label="M")
    lbl.add_css_class("display")
    lbl.add_css_class("honey-glow")
    return lbl


class MeliBrand(Gtk.Box):
    """
    Compact brand block: logo + 'MELI' + subtitle.

    Parameters
    ----------
    size : 'sm' | 'md' | 'lg'
        Visual size.
    layout : 'horizontal' | 'vertical'
        Stack direction.
    show_subtitle : bool
        Show 'HONEYPOT COMMAND CENTER' caption.
    """

    _SIZES = {
        "sm": (36, "title-3"),
        "md": (56, "title-2"),
        "lg": (140, "display"),
    }

    def __init__(
        self,
        size: str = "md",
        layout: str = "horizontal",
        show_subtitle: bool = True,
    ) -> None:
        is_vertical = layout == "vertical"
        super().__init__(
            orientation=Gtk.Orientation.VERTICAL if is_vertical else Gtk.Orientation.HORIZONTAL,
            spacing=12 if is_vertical else 14,
        )
        self.add_css_class("meli-brand")
        if is_vertical:
            self.set_halign(Gtk.Align.CENTER)

        px, title_class = self._SIZES.get(size, self._SIZES["md"])

        # Logo (with subtle pulse via CSS hook)
        logo = _logo_picture(px)
        self.append(logo)

        # Text block
        text_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
        )
        if is_vertical:
            text_box.set_halign(Gtk.Align.CENTER)

        title = Gtk.Label(label="MELI")
        title.add_css_class(title_class)
        title.add_css_class("meli-brand-title")
        title.add_css_class("honey-glow")
        if not is_vertical:
            title.set_halign(Gtk.Align.START)
        text_box.append(title)

        if show_subtitle:
            sub = Gtk.Label(label="HONEYPOT COMMAND CENTER")
            sub.add_css_class("meli-brand-sub")
            if not is_vertical:
                sub.set_halign(Gtk.Align.START)
            text_box.append(sub)

        self.append(text_box)
