#!/usr/bin/env python3
"""Nyxus Companion — PILOTED-saucer alien (default mode).

The little grey NYXUS alien from the wallpaper (nyxus-wall-alien-hero.png) is
posted up in the center UFO-ship clock on the bottom bar, kicked back like he's
piloting it. He mostly chills (slow breathing, tiny sway) and reacts to events
by throwing up a PEACE SIGN (and quick wave / cheer / alarm variants) before
settling back into his idle. No wandering — he stays parked on the saucer.

Art: two real-art frames cut from the wallpaper by gen_piloted_sprites.py —
``chill`` (head + NYXUS cap + hoodie bust) and ``peace`` (bust + raised peace
hand). Every reaction is one of those two frames plus an engine-driven motion
envelope (bounce / sway / shake / tint), so it stays tiny, clean and in-style.

Reuses the proven bits from the free-roam build: transparent layer-shell surface
(no black box), sound via nyxus-sound (laugh / chatter / yell), the nudge FIFO,
hyprland socket2 + dunst signals, and the same autostart launcher.

The older free-roaming engine is preserved at legacy-freeroam/companion.py and
selectable with NYXUS_COMPANION_MODE=freeroam (see the nyxus-companion launcher).

Requires libgtk4-layer-shell LD_PRELOADed (the launcher handles that).
"""
from __future__ import annotations

import json
import math
import os
import random
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GLib, Gtk, Gtk4LayerShell  # noqa: E402
import cairo  # noqa: E402

HERE = Path(__file__).resolve().parent
FRAMES_DIR = Path(os.environ.get("NYXUS_COMPANION_FRAMES", HERE / "assets" / "frames"))
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
FIFO_PATH = RUNTIME_DIR / "nyxus-companion.fifo"


def _envf(name, default):
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _envi(name, default):
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _envb(name, default):
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


# ---- Tunables ---------------------------------------------------------------
CPU_ALERT = _envf("NYXUS_COMPANION_CPU_ALERT", 85.0)
TEMP_ALERT = _envf("NYXUS_COMPANION_TEMP_ALERT", 84.0)
SOUND = _envb("NYXUS_COMPANION_SOUND", True)
LAYER_NAME = os.environ.get("NYXUS_COMPANION_LAYER", "top").lower()

TARGET_H = _envi("NYXUS_COMPANION_HEIGHT", 150)   # on-screen bust height (px)
# Fine placement over the center saucer clock.
X_OFFSET = _envi("NYXUS_COMPANION_X_OFFSET", 0)   # +right / -left from center
# How far his bottom sits below the bar's top edge (so he perches ON the saucer
# without covering the clock readout lower in the bar).
SADDLE = _envi("NYXUS_COMPANION_SADDLE", 6)
BAR_HEIGHT_FALLBACK = _envi("NYXUS_COMPANION_BAR_H", 112)

# Ambient sound cooldown so he never spams.
SOUND_COOLDOWN = _envf("NYXUS_COMPANION_SOUND_COOLDOWN", 40.0)
# Long, lazy gaps between spontaneous gestures — he's chilling.
DECIDE_MIN = _envf("NYXUS_COMPANION_DECIDE_MIN", 16.0)
DECIDE_MAX = _envf("NYXUS_COMPANION_DECIDE_MAX", 42.0)

TICK_ACTIVE_MS = 16    # ~60fps during a reaction
TICK_IDLE_MS = 110     # ~9fps while just breathing

LAYERS = {
    "background": Gtk4LayerShell.Layer.BACKGROUND,
    "bottom": Gtk4LayerShell.Layer.BOTTOM,
    "top": Gtk4LayerShell.Layer.TOP,
    "overlay": Gtk4LayerShell.Layer.OVERLAY,
}
MAGENTA = (1.0, 0.149, 0.404)


def _resolve_sound_bin():
    for c in (shutil.which("nyxus-sound"),
              os.path.expanduser("~/.local/bin/nyxus-sound"),
              "/usr/local/bin/nyxus-sound", "/usr/bin/nyxus-sound"):
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


# Reaction table: name -> (frame, motion, duration, sound). Motion is an engine
# envelope applied on top of the pose so two frames cover the whole repertoire.
REACTIONS = {
    "peace": ("peace", "pop",    2.4, None),
    "wave":  ("peace", "sway",   2.4, None),
    "cheer": ("peace", "double", 2.4, "chatter"),
    "laugh": ("peace", "big",    2.6, "laugh"),
    "notify":("peace", "pop",    2.6, "chatter"),
    "alert": ("peace", "shake",  2.6, "yell"),
}


class Companion:
    def __init__(self, app):
        self.app = app
        self.surfaces = {}
        self.manifest = {}
        self._load_frames()

        base_w = self.manifest.get("sprite_width", 342)
        base_h = self.manifest.get("sprite_height", 318)
        self.scale = TARGET_H / float(base_h)
        self.frame_w = int(round(base_w * self.scale))
        self.frame_h = int(round(base_h * self.scale))
        self.baseline_y = self.manifest.get("baseline_y", base_h - 4) * self.scale

        # Small window: sprite + headroom for the reaction bounce.
        self.pad_x = 24
        self.head_room = 46
        self.surface_w = self.frame_w + self.pad_x * 2
        self.surface_h = self.frame_h + self.head_room
        self.anchor_x = self.surface_w / 2.0
        self.ground_y = self.surface_h - 2          # sprite bottom rests here

        self.screen_w, self.screen_h = self._monitor_size()
        self.bar_top_y = self._bottom_bar_top()
        # Bottom-anchored: the sprite's bottom (ground_y, 2px above the surface
        # bottom) should land SADDLE px below the bar's top edge so he perches
        # on the saucer. sprite_bottom_screen = screen_h - margin - (surface_h -
        # ground_y); solve for margin.
        foot_gap = self.surface_h - self.ground_y            # == 2
        self.win_bottom_margin = max(
            0, int(self.screen_h - self.bar_top_y - SADDLE - foot_gap))
        self.win_left_margin = int((self.screen_w - self.surface_w) / 2 + X_OFFSET)

        # State: chill idle + a transient reaction.
        self.reaction = None            # {"motion","until","start","tint"}
        self.cur_pose = "chill"
        self.fade_from = None
        self.fade_start = 0.0
        self.next_decision = time.monotonic() + random.uniform(6, 14)
        self._last_sound = 0.0
        self.sound_bin = _resolve_sound_bin()
        self._t0 = time.monotonic()
        self._last_tick = time.monotonic()
        self._tick_interval = TICK_IDLE_MS
        self._idle_phase = None

        self._cpu_prev = self._read_cpu_raw()
        self._dunst_count = self._dunst_history()
        self._dunst_ok = self._dunst_count is not None
        self._socat = None

        self._build_window()
        self._start_signal_sources()

    # ---- Assets ------------------------------------------------------------
    def _load_frames(self):
        mf = FRAMES_DIR / "manifest.json"
        self.manifest = json.loads(mf.read_text()) if mf.exists() else {"states": {}}
        names = set()
        for cfg in self.manifest.get("states", {}).values():
            names.update(cfg.get("frames", []))
        if not names:
            names = {p.stem for p in FRAMES_DIR.glob("*.png")}
        for name in names:
            p = FRAMES_DIR / f"{name}.png"
            if p.exists():
                try:
                    self.surfaces[name] = cairo.ImageSurface.create_from_png(str(p))
                except Exception as e:
                    print("nyxus-companion: bad frame", p, e, file=sys.stderr)
        if not self.surfaces:
            print("nyxus-companion: no frames in", FRAMES_DIR, file=sys.stderr)

    def _surf(self, name):
        s = self.surfaces.get(name)
        if s is not None:
            return s
        for fb in ("chill", "peace", *self.surfaces.keys()):
            if fb in self.surfaces:
                return self.surfaces[fb]
        return None

    # ---- Environment -------------------------------------------------------
    def _monitor_size(self):
        try:
            out = subprocess.run(["hyprctl", "monitors", "-j"],
                                 capture_output=True, text=True, timeout=2).stdout
            mons = json.loads(out)
            m = next((x for x in mons if x.get("focused")), mons[0])
            sc = m.get("scale", 1.0) or 1.0
            w, h = int(m["width"] / sc), int(m["height"] / sc)
            if m.get("transform", 0) in (1, 3, 5, 7):
                w, h = h, w
            return w, h
        except Exception:
            return 1920, 1080

    def _bottom_bar_top(self):
        try:
            data = json.loads(subprocess.run(["hyprctl", "layers", "-j"],
                              capture_output=True, text=True, timeout=2).stdout)
            # A real bottom bar sits in the lower part of the screen and spans
            # most of the width. Stale eww instances (during hub/eww churn) can
            # leave junk layers, so pick the widest bar-bottom whose top edge is
            # in the bottom third — and among those, the LOWEST (largest y).
            best = None
            for mon in data.values():
                for lvl in mon.get("levels", {}).values():
                    for layer in lvl:
                        ns = layer.get("namespace", "")
                        if not ("bar-bottom" in ns or ns.endswith("bottom-bar")):
                            continue
                        top = layer.get("y", 0)
                        wide = layer.get("w", 0) >= self.screen_w * 0.6
                        if wide and self.screen_h * 0.6 < top < self.screen_h:
                            best = top if best is None else max(best, top)
            if best is not None:
                return int(best)
        except Exception:
            pass
        return int(self.screen_h - BAR_HEIGHT_FALLBACK)

    # ---- Window ------------------------------------------------------------
    def _build_window(self):
        self.win = Gtk.ApplicationWindow(application=self.app)
        self.win.set_default_size(self.surface_w, self.surface_h)
        self.win.set_decorated(False)
        self.win.add_css_class("nyxus-companion")

        Gtk4LayerShell.init_for_window(self.win)
        Gtk4LayerShell.set_namespace(self.win, "nyxus-companion")
        Gtk4LayerShell.set_layer(self.win, LAYERS.get(LAYER_NAME, Gtk4LayerShell.Layer.TOP))
        Gtk4LayerShell.set_keyboard_mode(self.win, Gtk4LayerShell.KeyboardMode.NONE)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.BOTTOM, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.RIGHT, False)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.TOP, False)
        Gtk4LayerShell.set_exclusive_zone(self.win, -1)
        Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.LEFT, self.win_left_margin)
        Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.BOTTOM, self.win_bottom_margin)

        # True transparency: drop the theme ".background" node + override at USER
        # priority (APPLICATION priority loses to some themes -> black box).
        self.win.remove_css_class("background")
        css_text = ("window.nyxus-companion, window.nyxus-companion *,"
                    " window.nyxus-companion decoration {"
                    " background: transparent; background-color: transparent;"
                    " background-image: none; border: none; box-shadow: none; }")
        css = Gtk.CssProvider()
        try:
            css.load_from_string(css_text)
        except AttributeError:
            css.load_from_data(css_text.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_USER)

        self.area = Gtk.DrawingArea()
        self.area.set_content_width(self.surface_w)
        self.area.set_content_height(self.surface_h)
        self.area.set_draw_func(self._draw)
        self.win.set_child(self.area)

        click = Gtk.GestureClick()
        click.set_button(0)
        click.connect("pressed", lambda *a: self.react("laugh"))
        self.area.add_controller(click)

        self.win.connect("realize", lambda *_: self._apply_click_region())
        self.win.connect("map", lambda *_: self._apply_click_region())
        self.win.present()

        GLib.timeout_add(self._tick_interval, self._tick)
        GLib.timeout_add(2000, self._poll_system)
        GLib.timeout_add(1500, self._poll_dunst)

    def _apply_click_region(self):
        try:
            surface = self.win.get_surface()
            if surface is None:
                return
            w = int(self.frame_w * 0.9)
            x0 = int(self.anchor_x - w / 2)
            region = cairo.Region(cairo.RectangleInt(x0, 0, w, self.surface_h))
            surface.set_input_region(region)
        except Exception as e:
            print("nyxus-companion: input region failed:", e, file=sys.stderr)

    # ---- Motion envelope ---------------------------------------------------
    def _envelope(self, now):
        """Return (dy, dx, scale_pop, tilt, tint_a) for the active reaction."""
        if not self.reaction:
            # chill: slow breathing bob only
            t = now - self._t0
            return (math.sin(t * 1.5) * 1.5, 0.0, 1.0 + math.sin(t * 1.5) * 0.008, 0.0, 0.0)
        r = self.reaction
        p = (now - r["start"]) / (r["until"] - r["start"])
        p = max(0.0, min(1.0, p))
        ease = math.sin(min(1.0, p) * math.pi)          # 0..1..0
        motion = r["motion"]
        dy = dx = tilt = 0.0
        pop = 1.0
        if motion == "pop":
            dy = -10 * ease
            pop = 1.0 + 0.05 * ease
        elif motion == "big":
            dy = -20 * math.sin(min(1.0, p) * math.pi) - 4 * abs(math.sin(p * math.pi * 3))
            pop = 1.0 + 0.09 * ease
        elif motion == "double":
            dy = -14 * abs(math.sin(p * math.pi * 2)) * (1 - p * 0.3)
            pop = 1.0 + 0.05 * ease
        elif motion == "sway":
            dx = math.sin(p * math.pi * 3) * 9 * (1 - p * 0.2)
            tilt = math.sin(p * math.pi * 3) * 0.05
        elif motion == "shake":
            dx = math.sin(p * math.pi * 12) * 6 * (1 - p)
            pop = 1.0 + 0.03 * ease
        tint = 0.0
        if r.get("tint"):
            tint = 0.5 * abs(math.sin(p * math.pi * 4)) * (1 - p)
        return (dy, dx, pop, tilt, tint)

    # ---- Drawing -----------------------------------------------------------
    def _blit(self, cr, pb, cx, by, pop, tilt, alpha, tint):
        """Draw one pose surface centered-bottom at (cx,by) with transform."""
        sw, sh = pb.get_width(), pb.get_height()
        cr.save()
        cr.translate(cx, by)
        if tilt:
            cr.rotate(tilt)
        cr.scale(self.scale * pop, self.scale * pop)
        cr.translate(-sw / 2.0, -sh)
        cr.set_source_surface(pb, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_GOOD)
        if alpha >= 0.999:
            cr.paint()
        else:
            cr.paint_with_alpha(alpha)
        if tint > 0:
            cr.push_group()
            cr.set_source_rgba(*MAGENTA, 1.0)
            cr.mask_surface(pb, 0, 0)
            cr.pop_group_to_source()
            cr.paint_with_alpha(tint * alpha)
        cr.restore()

    def _draw(self, area, cr, width, height):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
        now = time.monotonic()

        dy, dx, pop, tilt, tint = self._envelope(now)
        cx = self.anchor_x + dx
        by = self.ground_y + dy

        pb = self._surf(self.cur_pose)
        if pb is None:
            return
        fp = 1.0
        if self.fade_from is not None:
            fp = (now - self.fade_start) / 0.18
            if fp >= 1.0:
                self.fade_from = None
                fp = 1.0
            else:
                fpb = self._surf(self.fade_from)
                if fpb is not None:
                    self._blit(cr, fpb, cx, by, pop, tilt, 1.0 - fp, 0.0)
        self._blit(cr, pb, cx, by, pop, tilt, fp, tint)

    # ---- Behaviour ---------------------------------------------------------
    def _set_pose(self, name):
        if name != self.cur_pose:
            self.fade_from = self.cur_pose
            self.fade_start = time.monotonic()
            self.cur_pose = name

    def react(self, name):
        cfg = REACTIONS.get(name)
        if cfg is None:
            return
        frame, motion, dur, snd = cfg
        now = time.monotonic()
        self.reaction = {"motion": motion, "start": now, "until": now + dur,
                         "tint": name == "alert"}
        self._set_pose(frame)
        if snd:
            ambient = name not in ("laugh",)
            self._play_sound(snd, ambient=ambient)
        self._go_active()

    def _tick(self):
        now = time.monotonic()
        self._last_tick = now
        if self.reaction and now >= self.reaction["until"]:
            self.reaction = None
            self._set_pose("chill")
        # spontaneous, lazy gestures
        if self.reaction is None and now >= self.next_decision:
            self.next_decision = now + random.uniform(DECIDE_MIN, DECIDE_MAX)
            r = random.random()
            if r < 0.5:
                self.react("peace")
            elif r < 0.8:
                self.react("wave")
            else:
                self.react("cheer")

        active = self.reaction is not None or self.fade_from is not None
        if active:
            self.area.queue_draw()
        else:
            phase = int(now * 9)
            if phase != self._idle_phase:
                self._idle_phase = phase
                self.area.queue_draw()
        want = TICK_ACTIVE_MS if active else TICK_IDLE_MS
        if want != self._tick_interval:
            self._tick_interval = want
            GLib.timeout_add(want, self._tick)
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def _go_active(self):
        if self._tick_interval != TICK_ACTIVE_MS:
            self._tick_interval = TICK_ACTIVE_MS
            GLib.timeout_add(TICK_ACTIVE_MS, self._tick)

    # ---- Sound -------------------------------------------------------------
    def _play_sound(self, event, ambient=True):
        if not SOUND or not self.sound_bin:
            return
        now = time.monotonic()
        if ambient and now - self._last_sound < SOUND_COOLDOWN:
            return
        self._last_sound = now
        try:
            subprocess.Popen([self.sound_bin, event],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                             stdin=subprocess.DEVNULL, start_new_session=True)
        except Exception:
            pass

    # ---- Events ------------------------------------------------------------
    def on_nudge(self, cmd):
        cmd = cmd.strip().lower()
        if cmd in ("notification", "notify"):
            self.react("notify")
        elif cmd == "workspace":
            self.react("wave")
        elif cmd in ("peace",):
            self.react("peace")
        elif cmd in ("wave", "hello", "hi"):
            self.react("wave")
        elif cmd in ("cheer", "point"):
            self.react("cheer")
        elif cmd in ("laugh", "click"):
            self.react("laugh")
        elif cmd in ("alert",):
            self.react("alert")
        elif cmd in ("idle", "active", "wake", "jump", "stroll", "sit", "sleep"):
            pass  # no-op in piloted mode
        elif cmd == "quit":
            self.app.quit()

    # ---- Signal sources ----------------------------------------------------
    def _start_signal_sources(self):
        self._start_fifo()
        self._start_hypr_socket()

    def _start_fifo(self):
        try:
            if not FIFO_PATH.exists():
                os.mkfifo(FIFO_PATH)
            fd = os.open(str(FIFO_PATH), os.O_RDWR | os.O_NONBLOCK)
            self._fifo_buf = b""
            GLib.io_add_watch(GLib.IOChannel.unix_new(fd), GLib.IO_IN, self._on_fifo)
        except Exception as e:
            print("nyxus-companion: FIFO disabled:", e, file=sys.stderr)

    def _on_fifo(self, chan, cond):
        try:
            data = os.read(chan.unix_get_fd(), 4096)
            if data:
                self._fifo_buf += data
                while b"\n" in self._fifo_buf:
                    line, self._fifo_buf = self._fifo_buf.split(b"\n", 1)
                    txt = line.decode("utf-8", "replace").strip()
                    if txt:
                        self.on_nudge(txt)
        except BlockingIOError:
            pass
        except Exception as e:
            print("nyxus-companion: fifo read error:", e, file=sys.stderr)
        return True

    def _start_hypr_socket(self):
        sig = os.environ.get("HYPRLAND_INSTANCE_SIGNATURE")
        if not sig:
            return
        sock = RUNTIME_DIR / "hypr" / sig / ".socket2.sock"
        if not sock.exists() or not shutil.which("socat"):
            return
        try:
            self._socat = subprocess.Popen(["socat", "-U", "-", f"UNIX-CONNECT:{sock}"],
                                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            os.set_blocking(self._socat.stdout.fileno(), False)
            self._hypr_buf = b""
            GLib.io_add_watch(GLib.IOChannel.unix_new(self._socat.stdout.fileno()),
                              GLib.IO_IN | GLib.IO_HUP, self._on_hypr)
        except Exception as e:
            print("nyxus-companion: hypr socket disabled:", e, file=sys.stderr)

    def _on_hypr(self, chan, cond):
        try:
            data = os.read(chan.unix_get_fd(), 8192)
            if not data:
                return True
            self._hypr_buf += data
            while b"\n" in self._hypr_buf:
                line, self._hypr_buf = self._hypr_buf.split(b"\n", 1)
                name = line.decode("utf-8", "replace").split(">>", 1)[0]
                if name in ("workspace", "workspacev2", "focusedmon",
                            "createworkspace", "createworkspacev2", "moveworkspace"):
                    if self.reaction is None:
                        self.react("wave")
        except BlockingIOError:
            pass
        except Exception as e:
            print("nyxus-companion: hypr read error:", e, file=sys.stderr)
        return True

    def _poll_dunst(self):
        if not self._dunst_ok:
            return GLib.SOURCE_REMOVE
        c = self._dunst_history()
        if c is None:
            return GLib.SOURCE_CONTINUE
        if self._dunst_count is not None and c > self._dunst_count:
            self.react("notify")
        self._dunst_count = c
        return GLib.SOURCE_CONTINUE

    @staticmethod
    def _dunst_history():
        try:
            out = subprocess.run(["dunstctl", "count", "history"],
                                 capture_output=True, text=True, timeout=1.5)
            return int(out.stdout.strip() or 0) if out.returncode == 0 else None
        except Exception:
            return None

    def _poll_system(self):
        try:
            raw = self._read_cpu_raw()
            cpu = self._cpu_percent(self._cpu_prev, raw)
            self._cpu_prev = raw
        except Exception:
            cpu = 0.0
        temp = self._read_temp()
        if (cpu >= CPU_ALERT or (temp is not None and temp >= TEMP_ALERT)) and self.reaction is None:
            self.react("alert")
        return GLib.SOURCE_CONTINUE

    @staticmethod
    def _read_cpu_raw():
        with open("/proc/stat") as f:
            vals = [int(x) for x in f.readline().split()[1:]]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        return sum(vals), idle

    @staticmethod
    def _cpu_percent(prev, cur):
        dt = cur[0] - prev[0]
        di = cur[1] - prev[1]
        return 0.0 if dt <= 0 else 100.0 * (1.0 - di / dt)

    @staticmethod
    def _read_temp():
        best = None
        try:
            for zone in Path("/sys/class/thermal").glob("thermal_zone*/temp"):
                try:
                    v = int(zone.read_text().strip()) / 1000.0
                    if 20 <= v <= 130:
                        best = v if best is None else max(best, v)
                except Exception:
                    continue
        except Exception:
            pass
        return best

    def shutdown(self):
        try:
            if self._socat:
                self._socat.terminate()
        except Exception:
            pass


def main():
    app = Gtk.Application(application_id="com.nyxus.Companion")
    holder = {}

    def on_activate(a):
        if "c" not in holder:
            holder["c"] = Companion(a)

    app.connect("activate", on_activate)

    def _sig(*_):
        c = holder.get("c")
        if c:
            c.shutdown()
        app.quit()

    for s in (signal.SIGINT, signal.SIGTERM):
        try:
            GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, s, lambda: (_sig(), False)[1])
        except Exception:
            signal.signal(s, _sig)

    app.run(None)
    c = holder.get("c")
    if c:
        c.shutdown()


if __name__ == "__main__":
    main()
