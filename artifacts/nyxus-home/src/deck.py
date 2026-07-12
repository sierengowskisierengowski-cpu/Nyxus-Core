"""
NYXUS Home — MUSIC DECK (rev r1 · 2026-07-12)
Real MPRIS transport via playerctl (1 s follow) + a genuine live audio
spectrum: cava is spawned in raw-ascii mode against the default PipeWire
monitor, its bar stream is read on a background thread and painted as a
mirrored neon analyzer.  No player → deck idles with a breathing standby
trace (clearly labelled STANDBY, not fake audio).
(c) 2026 Joseph Sierengowski - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import math
import os
import shutil
import subprocess
import tempfile
import threading
import time

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

from style import PALETTE  # noqa: E402
from hud import make_ghost, _rgb  # noqa: E402

BARS = 44

CAVA_CONF = f"""
[general]
bars = {BARS}
framerate = 30
autosens = 1
[output]
method = raw
raw_target = /dev/stdout
data_format = ascii
ascii_max_range = 100
bar_delimiter = 59
frame_delimiter = 10
[smoothing]
noise_reduction = 66
"""


class SpectrumArea(Gtk.DrawingArea):
    """Mirrored analyzer fed by cava; falls back to a flat standby line."""

    def __init__(self, height=88):
        super().__init__()
        self.bars = [0.0] * BARS
        self.live = False
        self._t0 = time.monotonic()
        self.set_content_height(height)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)
        GLib.timeout_add(33, self._tick)

    def _tick(self):
        self.queue_draw()
        return True

    def _draw(self, _a, cr, w, h):
        n = len(self.bars)
        gap = 3.0
        bw = max(2.0, (w - gap * (n - 1)) / n)
        mid = h * 0.62
        c1 = _rgb(PALETTE["pink"])
        c2 = _rgb(PALETTE["cyan"])
        t = time.monotonic() - self._t0
        for i, v in enumerate(self.bars):
            f = i / max(1, n - 1)
            r = c1[0] + (c2[0] - c1[0]) * f
            g = c1[1] + (c2[1] - c1[1]) * f
            b = c1[2] + (c2[2] - c1[2]) * f
            if not self.live:
                # standby: tiny breathing baseline (labelled, not fake music)
                v = 2.5 + 2.0 * math.sin(t * 1.2 + i * 0.35) ** 2
            x = i * (bw + gap)
            up = (v / 100.0) * (mid - 4)
            dn = up * 0.45
            # glow
            cr.set_source_rgba(r, g, b, 0.20)
            cr.rectangle(x - 1, mid - up - 1, bw + 2, up + dn + 2)
            cr.fill()
            # main bar (up) + reflection (down)
            grad = cairo.LinearGradient(0, mid - up, 0, mid)
            grad.add_color_stop_rgba(0, min(1, r + .25), min(1, g + .25),
                                     min(1, b + .25), 1.0)
            grad.add_color_stop_rgba(1, r, g, b, 0.55)
            cr.set_source(grad)
            cr.rectangle(x, mid - up, bw, up)
            cr.fill()
            refl = cairo.LinearGradient(0, mid, 0, mid + dn)
            refl.add_color_stop_rgba(0, r, g, b, 0.30)
            refl.add_color_stop_rgba(1, r, g, b, 0.0)
            cr.set_source(refl)
            cr.rectangle(x, mid + 1, bw, dn)
            cr.fill()
        # axis
        cr.set_source_rgba(1, 1, 1, 0.15)
        cr.set_line_width(1)
        cr.move_to(0, mid)
        cr.line_to(w, mid)
        cr.stroke()


class _CavaFeed:
    """Background cava process → SpectrumArea."""

    def __init__(self, area: SpectrumArea):
        self.area = area
        self.proc = None
        if shutil.which("cava"):
            threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        conf = os.path.join(tempfile.gettempdir(),
                            f"nyxus-home-cava-{os.getuid()}.conf")
        try:
            with open(conf, "w") as f:
                f.write(CAVA_CONF)
            self.proc = subprocess.Popen(
                ["cava", "-p", conf], stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1)
            for line in self.proc.stdout:
                vals = line.strip().rstrip(";").split(";")
                if len(vals) < 4:
                    continue
                try:
                    bars = [float(v) for v in vals[:BARS]]
                except ValueError:
                    continue
                live = max(bars) > 1.0

                def apply(bars=bars, live=live):
                    # ease toward target so 30fps feed looks liquid
                    cur = self.area.bars
                    self.area.bars = [c + (t - c) * 0.55
                                      for c, t in zip(cur, bars)]
                    self.area.live = live
                    return False
                GLib.idle_add(apply)
        except Exception:
            pass


class MusicDeckCard:
    def __init__(self):
        self.root, content, self.set_footer = make_ghost(
            "purple", "MUSIC DECK", "♫")

        # track strip
        strip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        info.set_hexpand(True)
        info.set_valign(Gtk.Align.CENTER)
        self.title_lbl = Gtk.Label(xalign=0.0, label="NOTHING PLAYING")
        self.title_lbl.add_css_class("deck-title")
        self.title_lbl.set_ellipsize(3)
        self.artist_lbl = Gtk.Label(xalign=0.0,
                                    label="start any MPRIS player")
        self.artist_lbl.add_css_class("deck-artist")
        self.artist_lbl.set_ellipsize(3)
        info.append(self.title_lbl)
        info.append(self.artist_lbl)
        strip.append(info)

        # transport
        ctl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        ctl.set_valign(Gtk.Align.CENTER)
        for glyph, cmd in (("⏮", "previous"), ("⏯", "play-pause"),
                           ("⏭", "next")):
            btn = Gtk.Button(label=glyph)
            btn.add_css_class("deck-btn")
            btn.connect("clicked", self._ctl, cmd)
            ctl.append(btn)
        strip.append(ctl)
        content.append(strip)

        # progress
        prow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.pos_lbl = Gtk.Label(label="--:--")
        self.pos_lbl.add_css_class("deck-time")
        self.progress = Gtk.ProgressBar()
        self.progress.add_css_class("deck-progress")
        self.progress.set_hexpand(True)
        self.progress.set_valign(Gtk.Align.CENTER)
        self.len_lbl = Gtk.Label(label="--:--")
        self.len_lbl.add_css_class("deck-time")
        prow.append(self.pos_lbl)
        prow.append(self.progress)
        prow.append(self.len_lbl)
        content.append(prow)

        # spectrum
        self.spectrum = SpectrumArea()
        content.append(self.spectrum)
        _CavaFeed(self.spectrum)

        self._busy = False
        GLib.timeout_add(1000, self._poll)
        self._poll()

    def _ctl(self, _b, cmd):
        subprocess.Popen(["playerctl", cmd],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)

    @staticmethod
    def _fmt(us):
        s = int(us // 1_000_000)
        return f"{s // 60}:{s % 60:02d}"

    def _poll(self):
        if self._busy:
            return True
        self._busy = True
        threading.Thread(target=self._poll_bg, daemon=True).start()
        return True

    def _poll_bg(self):
        def pc(*args):
            try:
                return subprocess.run(
                    ["playerctl", *args], capture_output=True, text=True,
                    timeout=3).stdout.strip()
            except Exception:
                return ""
        status = pc("status")
        meta = {}
        if status:
            out = pc("metadata", "--format",
                     "{{title}}\t{{artist}}\t{{mpris:length}}\t{{playerName}}")
            parts = out.split("\t")
            if len(parts) == 4:
                meta = {"title": parts[0], "artist": parts[1],
                        "length": parts[2], "player": parts[3]}
            meta["pos"] = pc("position")

        def apply():
            self._busy = False
            if status and meta.get("title"):
                self.title_lbl.set_text(meta["title"][:70])
                self.artist_lbl.set_text(meta.get("artist") or "unknown artist")
                try:
                    length = float(meta.get("length") or 0)
                    pos = float(meta.get("pos") or 0) * 1_000_000
                    if length > 0:
                        self.progress.set_fraction(
                            max(0.0, min(1.0, pos / length)))
                    self.pos_lbl.set_text(self._fmt(pos))
                    self.len_lbl.set_text(self._fmt(length))
                except ValueError:
                    pass
                self.set_footer(
                    f"{(meta.get('player') or 'MPRIS').upper()} · "
                    f"{status.upper()} · CAVA SPECTRUM LIVE")
            else:
                self.title_lbl.set_text("NOTHING PLAYING")
                self.artist_lbl.set_text("start any MPRIS player")
                self.progress.set_fraction(0)
                self.pos_lbl.set_text("--:--")
                self.len_lbl.set_text("--:--")
                self.set_footer("MPRIS IDLE · SPECTRUM ON STANDBY")
            return False
        GLib.idle_add(apply)
