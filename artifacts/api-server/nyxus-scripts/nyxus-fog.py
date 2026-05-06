#!/usr/bin/env python3
"""
nyxus-fog.py — Animated fog daemon for NYXUS waybars (rev 2026-05-06k).

Spawns 4 transparent wlr-layer-shell windows (BOTTOM layer), one anchored
to each screen edge at the same size + margins as the corresponding waybar.
Each window renders a Cairo particle system at 30fps:

    - 14 soft-edged fog blobs per bar (56 total)
    - Pure white + off-white (cream raised) + occasional warm gold (~15%)
    - Smooth drift velocities + sinusoidal wobble for organic motion
    - Wraps off-edge cleanly (blobs leave one side, enter the other)
    - Radial-gradient soft falloff (no hard edges)

Architecture: matches the locked NYXUS Visual System — pure white /
off-white #fbfaf6 / gold #d4a73a (jewelry accent only). Runs underneath
the translucent waybar shell so the fog reads as living atmosphere
trapped inside the bars.

CPU cost: ~1-3% single core for 56 blobs at 30fps.

Autostart from Hyprland:
    exec-once = python3 ~/.nyxus/nyxus-fog.py
"""
from __future__ import annotations

# ─────────────────────────────────────────────────────────────────────────────
# LD_PRELOAD BOOTSTRAP (rev 2026-05-06k)
# gtk4-layer-shell MUST be loaded before libwayland-client or the wayland
# layer-surface hook never registers ("Failed to initialize layer surface,
# GTK4 Layer Shell may have been linked after libwayland"). The official fix
# is LD_PRELOAD=/usr/lib/libgtk4-layer-shell.so. We probe a few standard
# Arch/Fedora/Debian paths and re-exec ourselves with it set if missing.
# ─────────────────────────────────────────────────────────────────────────────
import os, sys
_LAYER_SHELL_CANDIDATES = (
    "/usr/lib/libgtk4-layer-shell.so",
    "/usr/lib/libgtk4-layer-shell.so.0",
    "/usr/lib64/libgtk4-layer-shell.so",
    "/usr/lib64/libgtk4-layer-shell.so.0",
    "/usr/lib/x86_64-linux-gnu/libgtk4-layer-shell.so",
    "/usr/lib/x86_64-linux-gnu/libgtk4-layer-shell.so.0",
)
def _ensure_ld_preload() -> None:
    lib = next((p for p in _LAYER_SHELL_CANDIDATES if os.path.exists(p)), None)
    if not lib:
        sys.stderr.write(
            "[nyxus-fog] FATAL: libgtk4-layer-shell.so not found in standard "
            "paths. Install with:  sudo pacman -S gtk4-layer-shell\n"
        )
        sys.exit(2)
    cur = os.environ.get("LD_PRELOAD", "")
    if lib in cur:
        return  # already preloaded — proceed
    new_preload = f"{lib}:{cur}" if cur else lib
    env = os.environ.copy()
    env["LD_PRELOAD"] = new_preload
    sys.stderr.write(f"[nyxus-fog] re-exec with LD_PRELOAD={lib}\n")
    os.execvpe(sys.executable, [sys.executable, __file__, *sys.argv[1:]], env)
_ensure_ld_preload()

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gtk, Gtk4LayerShell as LS, GLib, Gdk

import cairo
import random
import math
import signal

# ── BAR DIMENSIONS (mirror waybar-config.json EXACTLY so fog stays inside) ──
# Top bar:    height 60,  margin-top 5,  margin-left/right 10
# Bottom bar: height 30,  margin-bottom 5, margin-left/right 10
# Left bar:   width  64,  margin-top 280, margin-bottom 280
# Right bar:  width  72,  margin-top 220, margin-bottom 220
BAR_TOP_HEIGHT             = 60
BAR_TOP_MARGIN_TOP         = 5
BAR_TOP_MARGIN_LEFT        = 10
BAR_TOP_MARGIN_RIGHT       = 10
BAR_BOTTOM_HEIGHT          = 30
BAR_BOTTOM_MARGIN_BOTTOM   = 5
BAR_BOTTOM_MARGIN_LEFT     = 10
BAR_BOTTOM_MARGIN_RIGHT    = 10
BAR_LEFT_WIDTH             = 64
BAR_LEFT_MARGIN_TOP        = 280
BAR_LEFT_MARGIN_BOTTOM     = 280
BAR_RIGHT_WIDTH            = 72
BAR_RIGHT_MARGIN_TOP       = 220
BAR_RIGHT_MARGIN_BOTTOM    = 220

# ── ANIMATION ──────────────────────────────────────────────────────────────
FPS              = 30
FRAME_MS         = int(1000 / FPS)
BLOBS_PER_BAR    = 18

# ── PALETTE (NYXUS locked: pure white / off-white / gold jewelry accent) ───
COLOR_WHITE      = (1.000, 1.000, 1.000)
COLOR_OFFWHITE   = (0.984, 0.980, 0.965)   # #fbfaf6 cream raised
COLOR_CREAM_BASE = (0.960, 0.953, 0.937)   # #f5f3ef cream base
COLOR_GOLD       = (0.831, 0.655, 0.227)   # #d4a73a jewelry accent

# Weighted bag of colors — mostly white, some off-white, rare gold.
COLOR_BAG = (
    [COLOR_WHITE]      * 5 +
    [COLOR_OFFWHITE]   * 4 +
    [COLOR_CREAM_BASE] * 2 +
    [COLOR_GOLD]       * 2
)

# ─────────────────────────────────────────────────────────────────────────────
class FogBlob:
    """One soft-edged radial-gradient fog particle drifting across the bar."""

    __slots__ = ("w", "h", "x", "y", "vx", "vy",
                 "wobble_phase", "wobble_speed",
                 "radius", "alpha", "color")

    def __init__(self, w: int, h: int):
        self.w = w
        self.h = h
        self.x = random.uniform(0, w)
        self.y = random.uniform(0, h)

        speed = random.uniform(0.15, 0.50)
        angle = random.uniform(0, 2 * math.pi)
        self.vx = math.cos(angle) * speed
        self.vy = math.sin(angle) * speed

        self.wobble_phase = random.uniform(0, 2 * math.pi)
        self.wobble_speed = random.uniform(0.006, 0.022)

        # Radius scaled to bar's smaller dimension so blobs feel proportional.
        scale = max(28, min(w, h))
        self.radius = random.uniform(scale * 1.4, scale * 3.2)

        # Alpha bumped (rev 2026-05-06k) so fog punches through compositor
        # blur. Even at 0.95 the soft radial falloff keeps it cloud-like.
        self.color = random.choice(COLOR_BAG)
        if self.color == COLOR_GOLD:
            self.alpha = random.uniform(0.25, 0.50)   # warm wisps
        else:
            self.alpha = random.uniform(0.55, 0.95)   # bright fog

    def update(self):
        self.wobble_phase += self.wobble_speed
        wobble = math.sin(self.wobble_phase) * 0.20
        self.x += self.vx + wobble
        self.y += self.vy + wobble * 0.4

        m = self.radius
        if self.x < -m:        self.x = self.w + m
        elif self.x > self.w + m: self.x = -m
        if self.y < -m:        self.y = self.h + m
        elif self.y > self.h + m: self.y = -m

    def draw(self, ctx: cairo.Context):
        r, g, b = self.color
        pat = cairo.RadialGradient(self.x, self.y, 0,
                                   self.x, self.y, self.radius)
        pat.add_color_stop_rgba(0.00, r, g, b, self.alpha)
        pat.add_color_stop_rgba(0.45, r, g, b, self.alpha * 0.40)
        pat.add_color_stop_rgba(1.00, r, g, b, 0.0)
        ctx.set_source(pat)
        ctx.rectangle(self.x - self.radius, self.y - self.radius,
                      self.radius * 2, self.radius * 2)
        ctx.fill()


# ─────────────────────────────────────────────────────────────────────────────
class FogWindow(Gtk.Window):
    """One layer-shell window anchored to a screen edge, drawing fog."""

    def __init__(self, app: Gtk.Application, position: str,
                 width: int | None = None, height: int | None = None,
                 margin_top: int = 0, margin_bottom: int = 0,
                 margin_left: int = 0, margin_right: int = 0):
        super().__init__(application=app)
        self.position = position

        # ── wlr-layer-shell setup ──
        LS.init_for_window(self)
        LS.set_layer(self, LS.Layer.BOTTOM)        # below waybar (TOP)
        LS.set_namespace(self, "nyxus-fog")
        LS.set_anchor(self, LS.Edge.LEFT,
                      position in ("top", "bottom", "left"))
        LS.set_anchor(self, LS.Edge.RIGHT,
                      position in ("top", "bottom", "right"))
        LS.set_anchor(self, LS.Edge.TOP,
                      position in ("top", "left", "right"))
        LS.set_anchor(self, LS.Edge.BOTTOM,
                      position in ("bottom", "left", "right"))
        LS.set_keyboard_mode(self, LS.KeyboardMode.NONE)
        LS.set_exclusive_zone(self, 0)
        if margin_top:
            LS.set_margin(self, LS.Edge.TOP, margin_top)
        if margin_bottom:
            LS.set_margin(self, LS.Edge.BOTTOM, margin_bottom)
        if margin_left:
            LS.set_margin(self, LS.Edge.LEFT, margin_left)
        if margin_right:
            LS.set_margin(self, LS.Edge.RIGHT, margin_right)

        if height is not None:
            self.set_default_size(1, height)
        if width is not None:
            self.set_default_size(width, 1)

        # Force transparent window background via CSS provider.
        css = Gtk.CssProvider()
        css.load_from_data(b"window { background: rgba(0,0,0,0); }")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

        # Drawing area
        self.area = Gtk.DrawingArea()
        self.area.set_draw_func(self.on_draw)
        self.set_child(self.area)

        self.blobs: list[FogBlob] = []
        self.last_w = 0
        self.last_h = 0

        GLib.timeout_add(FRAME_MS, self.tick)

    def _init_blobs(self, w: int, h: int):
        self.blobs = [FogBlob(w, h) for _ in range(BLOBS_PER_BAR)]
        self.last_w = w
        self.last_h = h

    def on_draw(self, _area, ctx: cairo.Context, w: int, h: int):
        if not self.blobs or w != self.last_w or h != self.last_h:
            self._init_blobs(w, h)

        # Clear to fully transparent.
        ctx.set_operator(cairo.OPERATOR_CLEAR)
        ctx.paint()

        # Composite blobs additively-soft (OPERATOR_OVER with alpha).
        ctx.set_operator(cairo.OPERATOR_OVER)
        for blob in self.blobs:
            blob.draw(ctx)

    def tick(self):
        for blob in self.blobs:
            blob.update()
        self.area.queue_draw()
        return True


# ─────────────────────────────────────────────────────────────────────────────
class FogApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="org.nyxus.fog",
                         flags=0)

    def do_activate(self):
        self.win_top = FogWindow(
            self, "top", height=BAR_TOP_HEIGHT,
            margin_top=BAR_TOP_MARGIN_TOP,
            margin_left=BAR_TOP_MARGIN_LEFT,
            margin_right=BAR_TOP_MARGIN_RIGHT,
        )
        self.win_bottom = FogWindow(
            self, "bottom", height=BAR_BOTTOM_HEIGHT,
            margin_bottom=BAR_BOTTOM_MARGIN_BOTTOM,
            margin_left=BAR_BOTTOM_MARGIN_LEFT,
            margin_right=BAR_BOTTOM_MARGIN_RIGHT,
        )
        self.win_left = FogWindow(
            self, "left", width=BAR_LEFT_WIDTH,
            margin_top=BAR_LEFT_MARGIN_TOP,
            margin_bottom=BAR_LEFT_MARGIN_BOTTOM,
        )
        self.win_right = FogWindow(
            self, "right", width=BAR_RIGHT_WIDTH,
            margin_top=BAR_RIGHT_MARGIN_TOP,
            margin_bottom=BAR_RIGHT_MARGIN_BOTTOM,
        )
        for w in (self.win_top, self.win_bottom,
                  self.win_left, self.win_right):
            w.present()


# ─────────────────────────────────────────────────────────────────────────────
def main() -> int:
    sys.stderr.write(
        f"[nyxus-fog] starting — {BLOBS_PER_BAR} blobs/bar × 4 bars "
        f"@ {FPS}fps (rev 2026-05-06k)\n"
    )
    app = FogApp()

    # Graceful shutdown on SIGTERM/SIGINT — capture app instance directly
    # so we don't depend on Gtk.Application.get_default() being non-None
    # if a signal arrives before/after activation.
    def _term(*_):
        sys.stderr.write("[nyxus-fog] shutting down\n")
        try:
            GLib.idle_add(app.quit)
        except Exception:
            sys.exit(0)
    signal.signal(signal.SIGTERM, _term)
    signal.signal(signal.SIGINT, _term)

    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
