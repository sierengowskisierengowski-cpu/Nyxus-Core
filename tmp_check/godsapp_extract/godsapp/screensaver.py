"""
NYXUS GodsApp — idle screensaver overlay.
© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED

Tracks user input on the main window via GTK4 event controllers. After
IDLE_SECONDS without input, fades in a fullscreen overlay painting a
big tilted hand-drawn "GODSAPP" word with slow drift, vignette wash,
and a subtitle hint. Any motion / key / scroll / click dismisses it.
"""
from __future__ import annotations

import math
import time

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("PangoCairo", "1.0")
from gi.repository import Gtk, GLib, Pango, PangoCairo  # noqa: E402
import cairo  # noqa: E402

import ui  # noqa: E402  — for NYX palette + draw_text


class ScreensaverOverlay(Gtk.DrawingArea):
    """Fullscreen DrawingArea added as an overlay on the main window."""

    def __init__(self):
        super().__init__()
        self.set_can_target(True)            # absorb clicks while visible
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_draw_func(self._draw)
        self._t0 = time.time()
        self._fade = 0.0
        self._tick = None

        # any click on the overlay dismisses it (also dismissed via the
        # window-level IdleDetector controllers below, so this is belt-and-
        # braces).
        click = Gtk.GestureClick()
        click.connect("pressed", lambda *a: self.hide_now())
        self.add_controller(click)

    # ---- show / hide --------------------------------------------------- #
    def show_now(self):
        self.set_visible(True)
        self._t0 = time.time()
        self._fade = 0.0
        if self._tick is None:
            self._tick = GLib.timeout_add(33, self._on_tick)

    def hide_now(self):
        self.set_visible(False)
        if self._tick is not None:
            try:
                GLib.source_remove(self._tick)
            except Exception:
                pass
            self._tick = None

    # ---- ticking ------------------------------------------------------- #
    def _on_tick(self):
        if not self.get_visible():
            self._tick = None
            return False
        elapsed = time.time() - self._t0
        if elapsed < 1.2:
            self._fade = elapsed / 1.2
        else:
            self._fade = 1.0
        self.queue_draw()
        return True

    # ---- paint --------------------------------------------------------- #
    def _draw(self, area, cr, w, h):
        f = self._fade

        # dark wash
        cr.set_source_rgba(0.027, 0.027, 0.055, 0.92 * f)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        # vignette
        pat = cairo.RadialGradient(w / 2, h / 2, min(w, h) * 0.15,
                                   w / 2, h / 2, max(w, h) * 0.7)
        pat.add_color_stop_rgba(0, 0, 0, 0, 0)
        pat.add_color_stop_rgba(1, 0, 0, 0, 0.55 * f)
        cr.set_source(pat)
        cr.rectangle(0, 0, w, h)
        cr.fill()

        # animation params
        elapsed = time.time() - self._t0
        drift_x = math.sin(elapsed * 0.6) * 9.0
        drift_y = math.sin(elapsed * 0.4 + 1.0) * 4.0
        tilt    = math.sin(elapsed * 0.5) * 1.6  # degrees of sway

        text = "GODSAPP"
        size = int(min(w, h) * 0.22)
        ink  = ui.NYX["ink"]

        # main word — three offset passes for hand-drawn depth
        cr.save()
        cr.translate(w / 2 + drift_x, h / 2 + drift_y)
        cr.rotate(math.radians(-3.0 + tilt))
        for i in range(3):
            ox = (i - 1) * 1.6
            oy = (i - 1) * 1.6
            alpha = f * (0.96 if i == 1 else 0.30)
            self._draw_centered_text(cr, text, size,
                                     (ink[0], ink[1], ink[2], alpha),
                                     ox=ox, oy=oy, bold=True)
        cr.restore()

        # subtitle
        cr.save()
        cr.translate(w / 2, h / 2 + size * 0.65 + 30)
        cr.rotate(math.radians(-1.4))
        sub = "tap any key or click to wake"
        d = ui.NYX["dim"]
        self._draw_centered_text(cr, sub, 22,
                                 (d[0], d[1], d[2], 0.72 * f), italic=True)
        cr.restore()

        # corner brand
        faint = ui.NYX["faint"]
        ui.draw_text(cr, 28, h - 42, "NYXUS · idle", size=18,
                     color=(faint[0], faint[1], faint[2], 0.65 * f),
                     italic=True)

    @staticmethod
    def _draw_centered_text(cr, text, size, color, *, ox=0, oy=0,
                            bold=False, italic=False):
        layout = PangoCairo.create_layout(cr)
        desc = Pango.FontDescription()
        desc.set_family("Caveat")
        if bold:   desc.set_weight(Pango.Weight.BOLD)
        if italic: desc.set_style(Pango.Style.ITALIC)
        desc.set_absolute_size(size * Pango.SCALE)
        layout.set_font_description(desc)
        layout.set_text(text, -1)
        tw, th = layout.get_pixel_size()
        cr.set_source_rgba(*color)
        cr.move_to(-tw / 2 + ox, -th / 2 + oy)
        PangoCairo.show_layout(cr, layout)


class IdleDetector:
    """Polls every second; if last input > idle_seconds, shows overlay."""

    def __init__(self, window: Gtk.Window, overlay: ScreensaverOverlay,
                 *, idle_seconds: int = 120):
        self.window  = window
        self.overlay = overlay
        self.idle    = idle_seconds
        self.last    = time.monotonic()
        self._tid    = None

    def start(self):
        # mouse motion + enter
        motion = Gtk.EventControllerMotion()
        motion.connect("motion", self._on_event)
        motion.connect("enter",  self._on_event)
        self.window.add_controller(motion)

        # keys (capture phase so we see them before children)
        keys = Gtk.EventControllerKey()
        keys.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        keys.connect("key-pressed",  self._on_key)
        keys.connect("key-released", self._on_event)
        self.window.add_controller(keys)

        # scroll
        scroll = Gtk.EventControllerScroll.new(
            Gtk.EventControllerScrollFlags.BOTH_AXES)
        scroll.connect("scroll", self._on_scroll)
        self.window.add_controller(scroll)

        # clicks (capture so any click counts)
        click = Gtk.GestureClick()
        click.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        click.connect("pressed", self._on_event)
        self.window.add_controller(click)

        self._tid = GLib.timeout_add_seconds(1, self._poll)

    # event handlers — must return False/None to not consume keys/scroll
    def _on_event(self, *_a):
        self._tap()

    def _on_key(self, *_a):
        self._tap()
        return False

    def _on_scroll(self, *_a):
        self._tap()
        return False

    # ---- internals ----------------------------------------------------- #
    def _tap(self):
        self.last = time.monotonic()
        if self.overlay.get_visible():
            self.overlay.hide_now()

    def _poll(self):
        if not self.overlay.get_visible():
            if time.monotonic() - self.last >= self.idle:
                self.overlay.show_now()
        return True
