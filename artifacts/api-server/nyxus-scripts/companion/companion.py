#!/usr/bin/env python3
"""Nyxus Companion — a live, autonomous alien desktop mascot.

A small sprite lives on a transparent, click-through GTK4 layer-shell overlay
that sits above the wallpaper. It wanders on its own with eased movement and
runs a state machine driven by real system signals:

  * IDLE (no activity for a while)        -> drifts to a corner and sleeps (z z z)
  * NOTIFICATION (dunst history / nudge)  -> perks up, scurries to the top-right
  * HIGH CPU / TEMP (/proc + thermal)     -> excited "working hard" alert pose
  * WORKSPACE SWITCH (hyprland socket2)   -> spooked scurry to a new spot
  * periodic flair                        -> peace sign / wave / bob

Design notes / robustness:
  * The overlay is a SMALL surface repositioned via layer-shell margins instead
    of a full-screen canvas, so movement is cheap (no full-screen recomposite).
  * Click-through is achieved with an empty input region on the GdkSurface.
  * Every signal source is optional and wrapped defensively; a missing tool
    (socat / dunstctl / thermal) just disables that one input.
  * A FIFO at $XDG_RUNTIME_DIR/nyxus-companion.fifo accepts external nudges
    (e.g. `nyxus-companion nudge notification`) so the notification bridge or
    hypridle can be wired in later without touching this app.

Requires libgtk4-layer-shell to be LD_PRELOADed (the `nyxus-companion`
launcher handles that).
"""
from __future__ import annotations

import json
import math
import os
import random
import signal
import subprocess
import sys
import time
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("GdkPixbuf", "2.0")
gi.require_version("Gtk4LayerShell", "1.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk, Gtk4LayerShell  # noqa: E402
import cairo  # noqa: E402

HERE = Path(__file__).resolve().parent
FRAMES_DIR = Path(os.environ.get("NYXUS_COMPANION_FRAMES", HERE / "assets" / "frames"))
RUNTIME_DIR = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp"))
FIFO_PATH = RUNTIME_DIR / "nyxus-companion.fifo"

# ---- Tunables (override via env) --------------------------------------------
def _envf(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _envi(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _envb(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


IDLE_SECONDS = _envf("NYXUS_COMPANION_IDLE", 90.0)        # -> go to sleep
CPU_ALERT = _envf("NYXUS_COMPANION_CPU_ALERT", 82.0)      # percent
TEMP_ALERT = _envf("NYXUS_COMPANION_TEMP_ALERT", 82.0)    # deg C
ANIM_MS = _envi("NYXUS_COMPANION_ANIM_MS", 33)            # ~30 fps tick
BUBBLES = _envb("NYXUS_COMPANION_BUBBLES", True)
SHADOW = _envb("NYXUS_COMPANION_SHADOW", True)
LAYER_NAME = os.environ.get("NYXUS_COMPANION_LAYER", "bottom").lower()
SCALE = _envf("NYXUS_COMPANION_SCALE", 1.0)

SURFACE_W = 340
SURFACE_H = 280

LAYERS = {
    "background": Gtk4LayerShell.Layer.BACKGROUND,
    "bottom": Gtk4LayerShell.Layer.BOTTOM,
    "top": Gtk4LayerShell.Layer.TOP,
    "overlay": Gtk4LayerShell.Layer.OVERLAY,
}

ONE_LINERS = {
    "notify": ["yo, incoming transmission", "ping! check the corner", "you got mail, earthling"],
    "workspace": ["woah, warp jump", "new sector", "hold up, teleporting"],
    "alert": ["cores are cookin'", "we goin' warp speed", "somebody's workin' hard"],
    "sleep": ["zzz...", "beam me later", "power nap"],
    "peace": ["peace, human", "stay cosmic", "we come in peace"],
    "wave": ["ayo", "sup", "greetings"],
    "hello": ["we come in peace", "beep boop", "take me to your dealer"],
}

VIOLET = (0.474, 0.286, 0.949)
MAGENTA = (1.0, 0.149, 0.404)


class Companion:
    def __init__(self, app: Gtk.Application):
        self.app = app
        self.frames: dict[str, GdkPixbuf.Pixbuf] = {}
        self.manifest: dict = {}
        self._load_frames()

        # Screen bounds (focused monitor).
        self.screen_w, self.screen_h = self._monitor_size()
        self.max_x = max(0, self.screen_w - SURFACE_W)
        self.max_y = max(0, self.screen_h - SURFACE_H)

        # Position (top-left margin of the surface), float for easing.
        self.x = float(random.randint(0, self.max_x))
        self.y = float(self.max_y)  # start near the bottom
        self.tx = self.x
        self.ty = self.y
        self.last_mx = -1
        self.last_my = -1
        self.facing = 1  # 1 = right (default art faces right), -1 = left
        self.move_ease = 0.06

        # State machine.
        self.mode = "wander"          # wander | sleep
        self.transient = None         # {"state":..., "until": float}
        self.anim_state = "idle"
        self.anim_frame = 0
        self._anim_accum = 0.0
        self.dwell_until = 0.0
        self.next_flair = time.monotonic() + random.uniform(15, 30)
        self.last_activity = time.monotonic()
        self.bubble_text = ""
        self.bubble_until = 0.0
        self._t0 = time.monotonic()

        # Signal-source state.
        self._cpu_prev = self._read_cpu_raw()
        self._dunst_count = self._dunst_history()
        self._dunst_ok = self._dunst_count is not None
        self._socat = None

        self._build_window()
        self._start_signal_sources()

    # ---- Assets ------------------------------------------------------------
    def _load_frames(self):
        mf = FRAMES_DIR / "manifest.json"
        if mf.exists():
            self.manifest = json.loads(mf.read_text())
        else:
            self.manifest = {"states": {}}
        states = self.manifest.get("states", {})
        names = set()
        for cfg in states.values():
            names.update(cfg.get("frames", []))
        if not names:
            names = {p.stem for p in FRAMES_DIR.glob("*.png")}
        for name in names:
            p = FRAMES_DIR / f"{name}.png"
            if p.exists():
                pb = GdkPixbuf.Pixbuf.new_from_file(str(p))
                if SCALE != 1.0:
                    pb = pb.scale_simple(
                        max(1, int(pb.get_width() * SCALE)),
                        max(1, int(pb.get_height() * SCALE)),
                        GdkPixbuf.InterpType.BILINEAR,
                    )
                self.frames[name] = pb
        if not self.frames:
            print("nyxus-companion: no sprite frames found in", FRAMES_DIR, file=sys.stderr)

    def _state_cfg(self, state: str) -> dict:
        return self.manifest.get("states", {}).get(state, {"frames": ["idle_0"], "fps": 2})

    def _current_pixbuf(self) -> GdkPixbuf.Pixbuf | None:
        cfg = self._state_cfg(self.anim_state)
        frames = cfg.get("frames") or ["idle_0"]
        name = frames[self.anim_frame % len(frames)]
        pb = self.frames.get(name)
        if pb is None:
            for fallback in ("idle_0", *self.frames.keys()):
                if fallback in self.frames:
                    return self.frames[fallback]
            return None
        return pb

    # ---- Environment probing ----------------------------------------------
    def _monitor_size(self):
        try:
            out = subprocess.run(
                ["hyprctl", "monitors", "-j"], capture_output=True, text=True, timeout=2
            ).stdout
            mons = json.loads(out)
            focused = next((m for m in mons if m.get("focused")), mons[0])
            scale = focused.get("scale", 1.0) or 1.0
            w = int(focused["width"] / scale)
            h = int(focused["height"] / scale)
            # account for transform (rotated monitors swap w/h)
            if focused.get("transform", 0) in (1, 3, 5, 7):
                w, h = h, w
            return w, h
        except Exception:
            return 1920, 1080

    # ---- Window / layer shell ---------------------------------------------
    def _build_window(self):
        self.win = Gtk.ApplicationWindow(application=self.app)
        self.win.set_default_size(SURFACE_W, SURFACE_H)
        self.win.set_decorated(False)
        self.win.add_css_class("nyxus-companion")

        Gtk4LayerShell.init_for_window(self.win)
        Gtk4LayerShell.set_namespace(self.win, "nyxus-companion")
        Gtk4LayerShell.set_layer(self.win, LAYERS.get(LAYER_NAME, Gtk4LayerShell.Layer.BOTTOM))
        Gtk4LayerShell.set_keyboard_mode(self.win, Gtk4LayerShell.KeyboardMode.NONE)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.LEFT, True)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.RIGHT, False)
        Gtk4LayerShell.set_anchor(self.win, Gtk4LayerShell.Edge.BOTTOM, False)
        Gtk4LayerShell.set_exclusive_zone(self.win, 0)
        Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.LEFT, int(self.x))
        Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.TOP, int(self.y))

        # Transparent background.
        css = Gtk.CssProvider()
        css.load_from_data(b".nyxus-companion { background: transparent; }")
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.area = Gtk.DrawingArea()
        self.area.set_content_width(SURFACE_W)
        self.area.set_content_height(SURFACE_H)
        self.area.set_draw_func(self._draw)
        self.win.set_child(self.area)

        self.win.connect("realize", self._on_realize)
        self.win.connect("map", lambda *_: self._apply_click_through())
        self.win.present()

        GLib.timeout_add(ANIM_MS, self._tick)
        # Slow pollers.
        GLib.timeout_add(2000, self._poll_system)
        GLib.timeout_add(1500, self._poll_dunst)

    def _on_realize(self, *_):
        self._apply_click_through()

    def _apply_click_through(self):
        """Empty input region => pointer/clicks pass straight through."""
        try:
            surface = self.win.get_surface()
            if surface is not None:
                region = cairo.Region()  # empty
                surface.set_input_region(region)
        except Exception as e:
            print("nyxus-companion: click-through failed:", e, file=sys.stderr)

    # ---- Drawing -----------------------------------------------------------
    def _draw(self, area, cr, width, height):
        pb = self._current_pixbuf()
        if pb is None:
            return
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        sw, sh = pb.get_width(), pb.get_height()
        t = time.monotonic() - self._t0

        # Vertical bob (float feel); frozen while sleeping.
        if self.mode == "sleep" and not self.transient:
            bob = 0.0
        elif self.anim_state in ("walk",):
            bob = math.sin(t * 9.0) * 3.0
        else:
            bob = math.sin(t * 2.2) * 4.0

        sx = (SURFACE_W - sw) / 2.0
        sy = SURFACE_H - sh - 16 + bob

        if SHADOW:
            self._draw_shadow(cr, SURFACE_W / 2.0, SURFACE_H - 14, sw * 0.42, bob)

        cr.save()
        if self.facing < 0:
            cr.translate(sx + sw, sy)
            cr.scale(-1, 1)
            Gdk.cairo_set_source_pixbuf(cr, pb, 0, 0)
        else:
            Gdk.cairo_set_source_pixbuf(cr, pb, sx, sy)
        cr.paint()
        cr.restore()

        # Sleep 'z z z'.
        if self.mode == "sleep" and not self.transient:
            self._draw_zees(cr, sx + sw * (0.72 if self.facing > 0 else 0.28), sy + 6, t)

        # Speech bubble.
        if BUBBLES and self.bubble_text and time.monotonic() < self.bubble_until:
            self._draw_bubble(cr, SURFACE_W / 2.0, sy - 6, self.bubble_text)

    def _draw_shadow(self, cr, cx, cy, rx, bob):
        cr.save()
        squash = 1.0 - min(0.35, abs(bob) / 40.0)
        cr.translate(cx, cy)
        cr.scale(1.0, 0.28)
        cr.arc(0, 0, rx * squash, 0, 2 * math.pi)
        cr.set_source_rgba(0, 0, 0, 0.28)
        cr.fill()
        cr.restore()

    def _draw_zees(self, cr, x, y, t):
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_BOLD)
        for i in range(3):
            ph = (t * 0.6 + i * 0.33) % 1.0
            size = 12 + i * 5
            zx = x + i * 12 + math.sin(t * 2 + i) * 3
            zy = y - ph * 42
            cr.set_font_size(size)
            cr.set_source_rgba(*VIOLET, max(0.0, 1.0 - ph))
            cr.move_to(zx, zy)
            cr.show_text("z")

    def _draw_bubble(self, cr, cx, bottom_y, text):
        cr.select_font_face("sans-serif", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        cr.set_font_size(15)
        ext = cr.text_extents(text)
        pad = 12
        w = ext.width + pad * 2
        h = ext.height + pad * 2
        x = cx - w / 2
        y = bottom_y - h - 10
        x = max(4, min(SURFACE_W - w - 4, x))
        y = max(4, y)

        r = 12
        cr.new_sub_path()
        cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
        cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
        cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
        cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
        cr.close_path()
        cr.set_source_rgba(0.04, 0.02, 0.09, 0.92)
        cr.fill_preserve()
        cr.set_source_rgba(*VIOLET, 0.95)
        cr.set_line_width(2)
        cr.stroke()
        # tail
        cr.move_to(cx - 7, y + h - 1)
        cr.line_to(cx + 7, y + h - 1)
        cr.line_to(cx, y + h + 10)
        cr.close_path()
        cr.set_source_rgba(0.04, 0.02, 0.09, 0.92)
        cr.fill()

        cr.set_source_rgba(0.95, 0.93, 1.0, 1.0)
        cr.move_to(x + pad, y + pad + ext.height - ext.y_bearing - ext.height)
        cr.move_to(x + pad, y + pad - ext.y_bearing)
        cr.show_text(text)

    # ---- Main tick ---------------------------------------------------------
    def _tick(self):
        now = time.monotonic()
        dt = ANIM_MS / 1000.0
        changed = False

        self._update_state(now)

        # Movement easing.
        dx = self.tx - self.x
        dy = self.ty - self.y
        if abs(dx) > 0.6 or abs(dy) > 0.6:
            self.x += dx * self.move_ease
            self.y += dy * self.move_ease
            if abs(self.tx - self.x) > 3 and self.mode != "sleep" and not self.transient:
                self._set_anim("walk")
            self.facing = 1 if dx >= 0 else -1
            changed = True
        else:
            self.x, self.y = self.tx, self.ty
            if self.anim_state == "walk":
                self._set_anim("idle")
                changed = True

        mx, my = int(round(self.x)), int(round(self.y))
        if mx != self.last_mx or my != self.last_my:
            Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.LEFT, mx)
            Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.TOP, my)
            self.last_mx, self.last_my = mx, my

        # Animation frame advance.
        cfg = self._state_cfg(self.anim_state)
        fps = max(1, cfg.get("fps", 2))
        self._anim_accum += dt
        if self._anim_accum >= 1.0 / fps:
            self._anim_accum = 0.0
            self.anim_frame += 1
            changed = True

        # Continuous effects that need redraw.
        if self.mode == "sleep" or (BUBBLES and self.bubble_text and now < self.bubble_until):
            changed = True
        if self.anim_state in ("idle", "alert", "sleep", "wave", "peace", "notify", "point"):
            changed = True  # bob animation

        if changed:
            self.area.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _update_state(self, now):
        # Expire transient states.
        if self.transient and now >= self.transient["until"]:
            self.transient = None

        # Idle -> sleep.
        idle_for = now - self.last_activity
        if not self.transient:
            if idle_for >= IDLE_SECONDS and self.mode != "sleep":
                self._go_sleep()
            elif idle_for < IDLE_SECONDS and self.mode == "sleep":
                self._wake()

        if self.transient:
            self._set_anim(self.transient["state"])
            return

        if self.mode == "sleep":
            self._set_anim("sleep")
            return

        # Wander behavior.
        if now >= self.dwell_until and abs(self.tx - self.x) < 2 and abs(self.ty - self.y) < 2:
            self._pick_wander_target(now)

        if now >= self.next_flair and abs(self.tx - self.x) < 2:
            self._do_flair(now)

    def _set_anim(self, state):
        if state != self.anim_state:
            self.anim_state = state
            self.anim_frame = 0
            self._anim_accum = 0.0

    # ---- Behaviors ---------------------------------------------------------
    def _pick_wander_target(self, now):
        self.tx = float(random.randint(0, self.max_x))
        # bias toward lower half so it "walks the ground", with occasional floats
        if random.random() < 0.3:
            self.ty = float(random.randint(0, self.max_y))
        else:
            self.ty = float(random.randint(int(self.max_y * 0.55), self.max_y))
        self.move_ease = 0.05
        self.dwell_until = now + random.uniform(3.5, 8.0)

    def _do_flair(self, now):
        kind = random.choice(["peace", "wave", "peace"])
        self.transient = {"state": kind, "until": now + 2.4}
        if BUBBLES and random.random() < 0.5:
            self._say(random.choice(ONE_LINERS.get(kind, ["!"])), 2.4)
        self.next_flair = now + random.uniform(22, 48)

    def _go_sleep(self):
        self.mode = "sleep"
        # drift to nearest corner
        self.tx = 0.0 if self.x < self.max_x / 2 else float(self.max_x)
        self.ty = float(self.max_y)
        self.move_ease = 0.04
        if BUBBLES:
            self._say(random.choice(ONE_LINERS["sleep"]), 3.0)

    def _wake(self):
        self.mode = "wander"
        self.dwell_until = 0.0

    def _say(self, text, secs):
        self.bubble_text = text
        self.bubble_until = time.monotonic() + secs

    def _register_activity(self):
        self.last_activity = time.monotonic()
        if self.mode == "sleep":
            self._wake()

    # ---- Event handlers ----------------------------------------------------
    def on_notification(self):
        self._register_activity()
        now = time.monotonic()
        self.transient = {"state": "notify", "until": now + 5.0}
        # scurry toward the top-right (where notifications appear)
        self.tx = float(self.max_x)
        self.ty = 0.0
        self.move_ease = 0.09
        self.facing = 1
        if BUBBLES:
            self._say(random.choice(ONE_LINERS["notify"]), 4.0)

    def on_workspace(self):
        self._register_activity()
        now = time.monotonic()
        self.transient = {"state": "walk", "until": now + 1.4}
        # spooked dash to a new random spot
        self.tx = float(random.randint(0, self.max_x))
        self.ty = float(random.randint(int(self.max_y * 0.4), self.max_y))
        self.move_ease = 0.14
        if BUBBLES and random.random() < 0.4:
            self._say(random.choice(ONE_LINERS["workspace"]), 2.0)

    def on_alert(self, on: bool):
        now = time.monotonic()
        if on:
            self.transient = {"state": "alert", "until": now + 3.0}
            if BUBBLES and random.random() < 0.25:
                self._say(random.choice(ONE_LINERS["alert"]), 3.0)

    def on_nudge(self, cmd: str):
        cmd = cmd.strip().lower()
        if cmd in ("notification", "notify"):
            self.on_notification()
        elif cmd == "workspace":
            self.on_workspace()
        elif cmd == "idle":
            self.last_activity = time.monotonic() - IDLE_SECONDS - 1
        elif cmd in ("active", "wake"):
            self._register_activity()
        elif cmd == "peace":
            self._register_activity()
            self.transient = {"state": "peace", "until": time.monotonic() + 2.5}
            if BUBBLES:
                self._say(random.choice(ONE_LINERS["peace"]), 2.5)
        elif cmd in ("wave", "hello", "hi"):
            self._register_activity()
            self.transient = {"state": "wave", "until": time.monotonic() + 2.5}
            if BUBBLES:
                self._say(random.choice(ONE_LINERS["hello"]), 2.5)
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
            fd = chan.unix_get_fd()
            data = os.read(fd, 4096)
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
            print("nyxus-companion: no HYPRLAND_INSTANCE_SIGNATURE; hypr events off", file=sys.stderr)
            return
        sock = RUNTIME_DIR / "hypr" / sig / ".socket2.sock"
        if not sock.exists():
            print("nyxus-companion: hypr socket2 not found:", sock, file=sys.stderr)
            return
        try:
            self._socat = subprocess.Popen(
                ["socat", "-U", "-", f"UNIX-CONNECT:{sock}"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            os.set_blocking(self._socat.stdout.fileno(), False)
            self._hypr_buf = b""
            GLib.io_add_watch(
                GLib.IOChannel.unix_new(self._socat.stdout.fileno()),
                GLib.IO_IN | GLib.IO_HUP,
                self._on_hypr,
            )
        except Exception as e:
            print("nyxus-companion: hypr socket disabled:", e, file=sys.stderr)

    def _on_hypr(self, chan, cond):
        try:
            fd = chan.unix_get_fd()
            data = os.read(fd, 8192)
            if not data:
                return True
            self._hypr_buf += data
            while b"\n" in self._hypr_buf:
                line, self._hypr_buf = self._hypr_buf.split(b"\n", 1)
                self._handle_hypr_event(line.decode("utf-8", "replace"))
        except BlockingIOError:
            pass
        except Exception as e:
            print("nyxus-companion: hypr read error:", e, file=sys.stderr)
        return True

    def _handle_hypr_event(self, line: str):
        name = line.split(">>", 1)[0]
        if name in ("workspace", "workspacev2", "focusedmon", "createworkspace",
                    "createworkspacev2", "moveworkspace"):
            self.on_workspace()
        elif name in ("activewindow", "activewindowv2", "openwindow", "closewindow",
                      "movewindow", "fullscreen"):
            self._register_activity()

    def _poll_dunst(self):
        if not self._dunst_ok:
            return GLib.SOURCE_REMOVE
        c = self._dunst_history()
        if c is None:
            return GLib.SOURCE_CONTINUE
        if self._dunst_count is not None and c > self._dunst_count:
            self.on_notification()
        self._dunst_count = c
        return GLib.SOURCE_CONTINUE

    @staticmethod
    def _dunst_history():
        try:
            out = subprocess.run(
                ["dunstctl", "count", "history"], capture_output=True, text=True, timeout=1.5
            )
            if out.returncode != 0:
                return None
            return int(out.stdout.strip() or 0)
        except Exception:
            return None

    def _poll_system(self):
        # CPU
        try:
            raw = self._read_cpu_raw()
            cpu_pct = self._cpu_percent(self._cpu_prev, raw)
            self._cpu_prev = raw
        except Exception:
            cpu_pct = 0.0
        temp = self._read_temp()
        hot = cpu_pct >= CPU_ALERT or (temp is not None and temp >= TEMP_ALERT)
        if hot:
            self.on_alert(True)
        return GLib.SOURCE_CONTINUE

    @staticmethod
    def _read_cpu_raw():
        with open("/proc/stat") as f:
            parts = f.readline().split()[1:]
        vals = [int(x) for x in parts]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        total = sum(vals)
        return total, idle

    @staticmethod
    def _cpu_percent(prev, cur):
        dt = cur[0] - prev[0]
        di = cur[1] - prev[1]
        if dt <= 0:
            return 0.0
        return 100.0 * (1.0 - di / dt)

    @staticmethod
    def _read_temp():
        best = None
        try:
            base = Path("/sys/class/thermal")
            for zone in base.glob("thermal_zone*/temp"):
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
