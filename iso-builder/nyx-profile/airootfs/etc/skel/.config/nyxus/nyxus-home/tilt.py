"""
NYXUS Home - TiltBox: a Gtk.Widget wrapper that rotates its single child by
a static angle (degrees) using GTK4's Gtk.Snapshot.rotate(). Mirrors the
web preview's per-card `transform: rotate(Xdeg)`.

Hover/click hit-tests in GTK4 stay axis-aligned; at <=2 deg this is invisible.
If GTK4 snapshot rotation is unavailable for any reason, the wrapper falls
back to rendering the child un-rotated rather than crashing.

(c) 2026 Joseph A. Sierengowski - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
import math
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
from gi.repository import Gtk, Graphene  # noqa: E402


class TiltBox(Gtk.Widget):
    """Wraps one child widget, paints it rotated by `tilt` degrees about
    the wrapper's own center. Allocates extra space so corners don't clip."""

    def __init__(self, child: Gtk.Widget, tilt: float = 0.0):
        super().__init__()
        self._tilt = float(tilt)
        self._child = child
        child.set_parent(self)

    def do_dispose(self):
        if self._child is not None:
            self._child.unparent()
            self._child = None
        Gtk.Widget.do_dispose(self)

    # Forward sizing to child, padded so the rotated bbox always fits.
    def do_measure(self, orientation, for_size):
        if self._child is None:
            return (0, 0, -1, -1)
        rad = abs(math.radians(self._tilt))
        # Rotated AABB grows by sin(angle)*other_dim. Without knowing the
        # other dim here, use a conservative pad based on for_size when
        # available, else a fixed 24px pad. At small angles this is generous.
        pad = int(math.ceil(max(24, (for_size if for_size > 0 else 320) * rad)))
        min_s, nat_s, min_b, nat_b = self._child.measure(orientation, for_size)
        return (min_s + pad, nat_s + pad, min_b, nat_b)

    def do_size_allocate(self, width, height, baseline):
        if self._child is None:
            return
        # Give the child its natural size centered inside us; the snapshot
        # rotation happens around our center.
        self._child.allocate(width, height, baseline, None)

    def do_snapshot(self, snapshot: Gtk.Snapshot):
        if self._child is None:
            return
        if abs(self._tilt) < 0.01:
            self.snapshot_child(self._child, snapshot)
            return
        try:
            w = self.get_width()
            h = self.get_height()
            cx, cy = w / 2.0, h / 2.0
            snapshot.save()
            snapshot.translate(Graphene.Point().init(cx, cy))
            snapshot.rotate(self._tilt)
            snapshot.translate(Graphene.Point().init(-cx, -cy))
            self.snapshot_child(self._child, snapshot)
            snapshot.restore()
        except Exception:
            # Last-resort fallback: render un-rotated so the UI never breaks.
            self.snapshot_child(self._child, snapshot)
