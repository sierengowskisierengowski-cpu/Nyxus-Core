#!/usr/bin/env python3
# ============================================================================
# NYXUS — Demon Wake (idle-resume jumpscare overlay)
# /usr/share/nyxus/scripts/nyxus_demon_wake.py
#
# Spawned by hypridle's on-resume hook the moment input is detected after
# the idle screensaver has fired. Shows a fullscreen scary demon image and
# plays a deep evil laugh, then fades out over ~2.5s.
#
# Audio is synthesized in pure Python with the stdlib `wave` module — no
# external sound assets are required to ship this. Playback is attempted
# via pw-play (PipeWire) → paplay (PulseAudio) → aplay (ALSA), in order.
#
# © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
import gi
import math
import os
import random
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import wave

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
    WHITE_PURE='#ffffff'; WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
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

# ── chrome intentionally NOT imported: this app runs fullscreen and the
#    chrome size-policy hook would unfullscreen it. The unified palette is
#    still applied via in-file CSS that uses nyxus_palette constants.
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio  # noqa: E402


# ── tunables ────────────────────────────────────────────────────────────────
DEMON_IMG = "/usr/share/nyxus/demon.png"
SAMPLE_RATE = 22050
SOUND_DURATION_S = 3.0
FADE_DURATION_MS = 2500
FADE_TICK_MS = 40
HARD_KILL_MS = FADE_DURATION_MS + 1500


# ── audio synthesis ─────────────────────────────────────────────────────────
def _synthesize_evil_laugh(out_path):
    """Write a synthesized 'MWAHAHAHA' WAV to `out_path`.

    Sequence of 7 'HA' bursts at deep pitch (~78Hz fundamental) with rapid
    attack, exponential decay, and pseudo-reverb tail of three echoes.
    """
    n_total = int(SAMPLE_RATE * SOUND_DURATION_S)
    samples = [0.0] * n_total

    # (start_seconds, fundamental_hz)  — decreasing gaps == accelerating cadence
    schedule = [
        (0.00, 78), (0.30, 82), (0.54, 76), (0.74, 84),
        (0.92, 80), (1.08, 76), (1.22, 72),
    ]
    syll_dur = 0.24
    n_syl = int(syll_dur * SAMPLE_RATE)

    for s_start, f0 in schedule:
        n0 = int(s_start * SAMPLE_RATE)
        for i in range(n_syl):
            t = i / SAMPLE_RATE
            # Envelope: 18ms attack, then exp decay (tau ~110ms)
            if t < 0.018:
                env = t / 0.018
            else:
                env = math.exp(-(t - 0.018) * 9.5)
            # Fundamental + harmonic stack approximating a "HA" formant
            v = (
                math.sin(2 * math.pi * f0 * t) * 0.55
                + math.sin(2 * math.pi * f0 * 1.5 * t) * 0.30
                + math.sin(2 * math.pi * f0 * 2.1 * t) * 0.18
                + math.sin(2 * math.pi * f0 * 3.0 * t) * 0.10
            ) * env
            # Noise burst at attack for the consonant texture
            if t < 0.030:
                v += (random.random() - 0.5) * env * 0.45
            idx = n0 + i
            if idx < n_total:
                samples[idx] += v

    # Pseudo-reverb: three exponentially-decaying delays
    out = list(samples)
    for delay_ms, gain in ((180, 0.45), (360, 0.25), (560, 0.13)):
        d_n = int(delay_ms / 1000 * SAMPLE_RATE)
        for i in range(n_total - d_n):
            out[i + d_n] += samples[i] * gain

    # Normalize
    peak = max(abs(x) for x in out) or 1.0
    scale = 0.95 / peak

    with wave.open(out_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SAMPLE_RATE)
        frames = bytearray()
        for x in out:
            v = int(max(-32767, min(32767, x * scale * 32767)))
            frames += struct.pack("<h", v)
        w.writeframes(bytes(frames))


def _try_play(wav_path):
    """Attempt to play `wav_path` via pw-play → paplay → aplay. Returns True if launched."""
    for argv in (
        ["pw-play", wav_path],
        ["paplay", wav_path],
        ["aplay", "-q", wav_path],
    ):
        try:
            subprocess.Popen(
                argv,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
            )
            return True
        except FileNotFoundError:
            continue
    return False


def _audio_worker():
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp.close()
        _synthesize_evil_laugh(tmp.name)
        _try_play(tmp.name)
        # Defer cleanup so the player has time to open the file
        GLib.timeout_add(8000, lambda: (os.unlink(tmp.name) if os.path.exists(tmp.name) else None) or False)
    except Exception as e:
        print(f"[nyxus-demon-wake] audio failed: {e}", file=sys.stderr)


# ── overlay window ──────────────────────────────────────────────────────────
_CSS = b"""
window.nyx-jumpscare { background: #000000; }
"""


class JumpscareWindow(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="NYXUS Wake")
        self.add_css_class("nyx-jumpscare")
        self.set_decorated(False)
        self.fullscreen()

        css = Gtk.CssProvider()
        css.load_from_data(_CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css,
            Gtk.STYLE_PROVIDER_PRIORITY_USER,
        )

        if os.path.isfile(DEMON_IMG):
            pic = Gtk.Picture.new_for_filename(DEMON_IMG)
            pic.set_can_shrink(True)
            pic.set_keep_aspect_ratio(True)
            try:
                pic.set_content_fit(Gtk.ContentFit.COVER)
            except Exception:
                pass
            pic.set_hexpand(True)
            pic.set_vexpand(True)
            self.set_child(pic)
        else:
            placeholder = Gtk.Label(label="\u2620")
            placeholder.set_hexpand(True)
            placeholder.set_vexpand(True)
            self.set_child(placeholder)

        self._opacity = 1.0
        self.set_opacity(1.0)
        n_ticks = max(1, FADE_DURATION_MS // FADE_TICK_MS)
        self._fade_step = 1.0 / n_ticks
        GLib.timeout_add(FADE_TICK_MS, self._on_fade_tick)

    def _on_fade_tick(self):
        self._opacity -= self._fade_step
        if self._opacity <= 0.0:
            try:
                self.close()
            except Exception:
                pass
            app = self.get_application()
            if app is not None:
                app.quit()
            return False
        self.set_opacity(self._opacity)
        return True


def _is_session_locked():
    """Return True if the user's session is locked.

    Two-tier check, most-authoritative first:
      1. systemd-logind's LockedHint property (whoever called lock-session
         flips this regardless of which lockscreen owns the surface)
      2. fallback: pgrep for the hyprlock process (covers manual `hyprlock`
         invocation outside of loginctl)
    """
    try:
        sid = os.environ.get("XDG_SESSION_ID", "").strip()
        if sid:
            r = subprocess.run(
                ["loginctl", "show-session", sid, "-p", "LockedHint", "--value"],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=1.0,
            )
            if r.returncode == 0 and r.stdout.strip().lower() == b"yes":
                return True
    except Exception:
        pass
    try:
        if subprocess.run(
            ["pgrep", "-x", "hyprlock"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=1.0,
        ).returncode == 0:
            return True
    except Exception:
        pass
    return False


def _on_activate(app):
    # Don't jumpscare while the session is locked — the overlay would render
    # underneath hyprlock's layer surface but the audio would still blast.
    if _is_session_locked():
        app.quit()
        return

    win = JumpscareWindow(app)
    win.present()
    threading.Thread(target=_audio_worker, daemon=True).start()
    # Hard-kill safety net — guarantees the overlay always tears down even
    # if the fade timer or GTK present chain glitches.
    GLib.timeout_add(HARD_KILL_MS, app.quit)


def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))
    signal.signal(signal.SIGINT, lambda *_: sys.exit(0))

    app = Gtk.Application(
        application_id="app.nyxus.DemonWake",
        flags=Gio.ApplicationFlags.FLAGS_NONE,
    )
    app.connect("activate", _on_activate)
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
