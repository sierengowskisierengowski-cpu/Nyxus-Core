#!/usr/bin/env python3
"""Nyxus Companion — a calm, alive alien-dude desktop character.

A full-body grey alien street dude (NYXUS UFO snapback, graffiti hoodie, ripped
jeans, gold chain, chunky sneakers — the Nyxus house character) lives on a
transparent GTK4 layer-shell overlay above the wallpaper and behaves like a
chill little video-game character:

  * MOSTLY IDLE — subtle breathing, occasional look-arounds and small gestures
    (wave / peace / point), with an OCCASIONAL short stroll every few minutes
    and a nap when the desktop has been quiet for a while.
  * SMOOTH, EASED LOCOMOTION — velocity ramps up and down (accelerate /
    decelerate), position is tweened sub-pixel at a steady frame rate, the leg
    cycle advances from actual distance travelled, and he faces (flips into)
    the direction of travel. No teleporting, no sliding, no jitter.
  * REAL PHYSICS FLAVOR — rare jumps use a gravity arc with squash & stretch;
    a soft contact shadow tracks under him and shrinks when airborne.
  * CROSS-FADED POSES — pose switches blend briefly so actions never pop.
  * AUDIO ONLY, NO TEXT — no speech bubbles. He giggles (alien laugh) when
    clicked, occasionally chatters, and does an urgent alien yell on critical
    alerts. All sounds go through `nyxus-sound` (synth theme in sounds/).
  * REAL SIGNALS — hyprland socket2 (workspace/window), dunst history
    (notifications), /proc + thermal (busy/hot), plus a FIFO for nudges
    (`nyxus-companion nudge <event>`). Every source is optional/defensive.
  * LOW CPU — pose pixmaps are pre-decoded cairo surfaces; the tick drops to a
    slow idle rate when nothing is moving and only redraws what changed.

The art is a set of foot-anchored, uniformly-scaled key poses in assets/frames/
(baked by gen_companion_sprites.py from green-screen renders of the character).

Requires libgtk4-layer-shell LD_PRELOADed (the `nyxus-companion` launcher does
that).
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


# ---- Tunables (override via env) --------------------------------------------
IDLE_SECONDS = _envf("NYXUS_COMPANION_IDLE", 240.0)      # quiet desktop -> nap
CPU_ALERT = _envf("NYXUS_COMPANION_CPU_ALERT", 85.0)     # percent
TEMP_ALERT = _envf("NYXUS_COMPANION_TEMP_ALERT", 84.0)   # deg C
SHADOW = _envb("NYXUS_COMPANION_SHADOW", True)
SOUND = _envb("NYXUS_COMPANION_SOUND", True)
LAYER_NAME = os.environ.get("NYXUS_COMPANION_LAYER", "bottom").lower()
SCALE = _envf("NYXUS_COMPANION_SCALE", 1.0)

# Calm, natural stroll. Eased: accelerates to speed, decelerates to stop.
WALK_SPEED = _envf("NYXUS_COMPANION_WALK_SPEED", 52.0)    # px/s cruise
RUN_SPEED = _envf("NYXUS_COMPANION_RUN_SPEED", 170.0)     # px/s (rare)
ACCEL = _envf("NYXUS_COMPANION_ACCEL", 120.0)             # px/s^2
JUMP_V0 = _envf("NYXUS_COMPANION_JUMP", 300.0)            # px/s launch
GRAVITY = _envf("NYXUS_COMPANION_GRAVITY", 1000.0)        # px/s^2

# How often he decides to do something (seconds between decisions) and the
# weighted menu of what he picks. Mostly: keep idling.
DECIDE_MIN = _envf("NYXUS_COMPANION_DECIDE_MIN", 9.0)
DECIDE_MAX = _envf("NYXUS_COMPANION_DECIDE_MAX", 26.0)
STROLL_EVERY = _envf("NYXUS_COMPANION_STROLL_EVERY", 150.0)  # avg secs between strolls

TICK_ACTIVE_MS = 16     # ~60 fps while anything is in motion
TICK_IDLE_MS = 125      # ~8 fps while just breathing

JUMP_HEADROOM = 150
SIDE_ROOM = 40
GROUND_PAD = 8
STRIDE_WALK = 42.0   # px of travel per half stride (leg swap) at walk
STRIDE_RUN = 66.0
FADE_TIME = 0.18

# Min seconds between ambient (non-click) sounds so he never gets annoying.
SOUND_COOLDOWN = 45.0

LAYERS = {
    "background": Gtk4LayerShell.Layer.BACKGROUND,
    "bottom": Gtk4LayerShell.Layer.BOTTOM,
    "top": Gtk4LayerShell.Layer.TOP,
    "overlay": Gtk4LayerShell.Layer.OVERLAY,
}


class Companion:
    def __init__(self, app: Gtk.Application):
        self.app = app
        self.surfaces: dict[str, cairo.ImageSurface] = {}
        self.manifest: dict = {}
        self._load_frames()

        self.frame_w = int(self.manifest.get("sprite_width", 206) * SCALE)
        self.frame_h = int(self.manifest.get("sprite_height", 238) * SCALE)
        self.baseline_y = self.manifest.get("baseline_y", self.frame_h - 10) * SCALE
        self.anchor_x = self.frame_w / 2.0

        self.surface_w = self.frame_w + SIDE_ROOM * 2
        self.surface_h = self.frame_h + JUMP_HEADROOM
        self.ground_y = self.surface_h - GROUND_PAD          # feet rest here
        self.center_x = self.surface_w / 2.0

        # Screen bounds (focused monitor).
        self.screen_w, self.screen_h = self._monitor_size()
        self.max_x = max(0, self.screen_w - self.surface_w)
        self.win_top = max(0, self.screen_h - self.ground_y - 2)

        # Position/motion (floats for sub-pixel easing).
        self.x = float(random.randint(0, self.max_x)) if self.max_x else 0.0
        self.tx = self.x
        self.vx = 0.0
        self.speed_cap = WALK_SPEED
        self.gait = "walk"
        self.facing = 1
        self.last_win_x = None

        # Jump physics.
        self.lift = 0.0
        self.vlift = 0.0
        self.jumping = False
        self.squash = 0.0

        # Behaviour state.
        self.mode = "wander"               # wander | sleep
        self.action = None                 # {name, start, until}
        self.stride_phase = 0.0
        self.next_decision = time.monotonic() + random.uniform(4, 10)
        self.next_stroll = time.monotonic() + random.uniform(30, STROLL_EVERY)
        self.last_activity = time.monotonic()
        self.look_wobble = 0.0
        self._last_sound = 0.0
        self._t0 = time.monotonic()
        self._last_tick = time.monotonic()

        # Cross-fade between poses.
        self.cur_pose = "idle"
        self.fade_from = None
        self.fade_start = 0.0

        # Adaptive tick bookkeeping.
        self._tick_interval = TICK_ACTIVE_MS
        self._idle_draw_phase = None

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
            if not p.exists():
                continue
            try:
                surf = cairo.ImageSurface.create_from_png(str(p))
            except Exception as e:
                print("nyxus-companion: bad frame", p, e, file=sys.stderr)
                continue
            if SCALE != 1.0:
                nw = max(1, int(surf.get_width() * SCALE))
                nh = max(1, int(surf.get_height() * SCALE))
                scaled = cairo.ImageSurface(cairo.FORMAT_ARGB32, nw, nh)
                c = cairo.Context(scaled)
                c.scale(SCALE, SCALE)
                c.set_source_surface(surf, 0, 0)
                c.get_source().set_filter(cairo.FILTER_GOOD)
                c.paint()
                surf = scaled
            self.surfaces[name] = surf
        if not self.surfaces:
            print("nyxus-companion: no sprite frames in", FRAMES_DIR, file=sys.stderr)

    def _surf(self, name: str):
        s = self.surfaces.get(name)
        if s is not None:
            return s
        for fb in ("idle", *self.surfaces.keys()):
            if fb in self.surfaces:
                return self.surfaces[fb]
        return None

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
            if focused.get("transform", 0) in (1, 3, 5, 7):
                w, h = h, w
            return w, h
        except Exception:
            return 1920, 1080

    # ---- Window / layer shell ---------------------------------------------
    def _build_window(self):
        self.win = Gtk.ApplicationWindow(application=self.app)
        self.win.set_default_size(self.surface_w, self.surface_h)
        self.win.set_decorated(False)
        self.win.add_css_class("nyxus-companion")
        # GTK4 windows carry a ".background" style class that paints the theme's
        # window background even over CSS overrides on some themes — drop it so
        # the compositor gets true per-pixel alpha (no faint rectangle).
        self.win.remove_css_class("background")

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
        Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.TOP, int(self.win_top))

        # Fully transparent window: kill the theme's window/decoration background
        # on every node of this window. Without this the compositor shows an
        # opaque rectangle behind the sprite.
        css_text = (
            "window.nyxus-companion, window.nyxus-companion * {"
            " background: transparent; background-color: transparent;"
            " border: none; box-shadow: none; }"
        )
        css = Gtk.CssProvider()
        try:
            css.load_from_string(css_text)            # GTK >= 4.12
        except AttributeError:
            css.load_from_data(css_text.encode())     # older pygobject
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), css, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

        self.area = Gtk.DrawingArea()
        self.area.set_content_width(self.surface_w)
        self.area.set_content_height(self.surface_h)
        self.area.set_draw_func(self._draw)
        self.win.set_child(self.area)

        # Click reaction: only the body box is interactive (rest passes through).
        click = Gtk.GestureClick()
        click.set_button(0)
        click.connect("pressed", self._on_pressed)
        self.area.add_controller(click)

        self.win.connect("realize", lambda *_: self._apply_click_region())
        self.win.connect("map", lambda *_: self._apply_click_region())
        self.win.present()

        GLib.timeout_add(self._tick_interval, self._tick)
        GLib.timeout_add(2000, self._poll_system)
        GLib.timeout_add(1500, self._poll_dunst)

    def _body_rect(self):
        w = min(self.surface_w, int(self.frame_w * 0.8))
        x0 = int(self.center_x - w / 2)
        top = max(0, int(self.ground_y - self.baseline_y - 4))
        h = int(self.surface_h - top)
        return x0, top, w, h

    def _apply_click_region(self):
        """Clicks pass through everywhere except the character's body box."""
        try:
            surface = self.win.get_surface()
            if surface is None:
                return
            x0, y0, w, h = self._body_rect()
            region = cairo.Region(cairo.RectangleInt(x0, y0, w, h))
            surface.set_input_region(region)
        except Exception as e:
            print("nyxus-companion: input region failed:", e, file=sys.stderr)

    # ---- Drawing -----------------------------------------------------------
    def _pose_transform(self, cr, surf, foot_x, foot_y, sx, sy, lean, alpha):
        cr.save()
        cr.translate(foot_x, foot_y)
        if lean:
            cr.rotate(lean)
        cr.scale(self.facing * sx, sy)
        cr.translate(-self.anchor_x, -self.baseline_y)
        cr.set_source_surface(surf, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_GOOD)
        if alpha >= 0.999:
            cr.paint()
        else:
            cr.paint_with_alpha(alpha)
        cr.restore()

    def _draw(self, area, cr, width, height):
        cr.set_operator(cairo.OPERATOR_CLEAR)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)

        now = time.monotonic()
        t = now - self._t0
        frac_x = self.x - math.floor(self.x)
        foot_x = self.center_x + frac_x
        foot_y = self.ground_y - self.lift

        # --- squash / stretch -------------------------------------------------
        sx = sy = 1.0
        moving = abs(self.vx) > 4.0 and not self.jumping and not self._busy()
        if self.mode == "sleep" and not self.action:
            # slow, deep sleeping breath
            br = math.sin(t * 0.9) * 0.012
            sy = 1.0 + br
            sx = 1.0 - br * 0.5
        elif self.jumping:
            pass  # squash impulse handles it
        elif moving:
            # gentle stride bounce, feet planted (scale from the ground up)
            b = abs(math.sin(self.stride_phase * math.pi))
            amp = 0.04 if self.gait == "run" else 0.022
            sy = 1.0 - amp * (1.0 - b)
            sx = 1.0 + (1.0 - sy) * 0.5
        else:
            # calm breathing
            br = math.sin(t * 1.6) * 0.015
            sy = 1.0 + br
            sx = 1.0 - br * 0.5

        sy += self.squash
        sx -= self.squash * 0.6

        # lean into travel (proportional to velocity, capped subtle)
        lean = 0.0
        if not self.jumping and self.mode != "sleep":
            lean = max(-0.10, min(0.10, self.vx / 1400.0))
        lean += self.look_wobble

        if SHADOW:
            self._draw_shadow(cr, foot_x, self.ground_y + 2, sx)

        pose = self.cur_pose
        pb = self._surf(pose)
        if pb is not None:
            if self.fade_from is not None:
                p = (now - self.fade_start) / FADE_TIME
                if p >= 1.0:
                    self.fade_from = None
                else:
                    fpb = self._surf(self.fade_from)
                    if fpb is not None:
                        self._pose_transform(cr, fpb, foot_x, foot_y, sx, sy, lean, 1.0 - p)
                    self._pose_transform(cr, pb, foot_x, foot_y, sx, sy, lean, p)
            if self.fade_from is None:
                self._pose_transform(cr, pb, foot_x, foot_y, sx, sy, lean, 1.0)

    def _draw_shadow(self, cr, cx, cy, sx):
        cr.save()
        h = max(0.0, self.lift)
        k = 1.0 / (1.0 + h / 130.0)
        rx = max(1.0, (self.frame_w * 0.30) * sx * k)
        ry = rx * 0.26
        cr.translate(cx, cy)
        cr.scale(1.0, ry / rx)
        grad = cairo.RadialGradient(0, 0, 0, 0, 0, rx)
        grad.add_color_stop_rgba(0, 0, 0, 0, 0.40 * k)
        grad.add_color_stop_rgba(1, 0, 0, 0, 0.0)
        cr.set_source(grad)
        cr.arc(0, 0, rx, 0, 2 * math.pi)
        cr.fill()
        cr.restore()

    # ---- Pose selection ----------------------------------------------------
    def _busy(self) -> bool:
        return self.action is not None and time.monotonic() < self.action["until"]

    def _set_pose(self, name: str, crossfade: bool = True):
        if name == self.cur_pose:
            return
        if crossfade:
            self.fade_from = self.cur_pose
            self.fade_start = time.monotonic()
        else:
            self.fade_from = None
        self.cur_pose = name

    def _frames_for(self, state: str):
        cfg = self.manifest.get("states", {}).get(state)
        if cfg and cfg.get("frames"):
            return cfg["frames"], max(1, cfg.get("fps", 3))
        return [state if state in self.surfaces else "idle"], 3

    # ---- Main tick (physics + animation) ----------------------------------
    def _tick(self):
        now = time.monotonic()
        dt = min(0.12, now - self._last_tick)
        self._last_tick = now

        self._decide(now)

        # --- jump physics ---
        if self.jumping:
            self.lift += self.vlift * dt
            self.vlift -= GRAVITY * dt
            if self.lift <= 0.0:
                self.lift = 0.0
                self.jumping = False
                self.squash = -0.10
        if self.squash:
            self.squash *= math.exp(-dt * 9.0)
            if abs(self.squash) < 0.002:
                self.squash = 0.0

        # --- eased horizontal locomotion (accelerate, cruise, decelerate) ---
        prev_x = self.x
        allow_move = self.mode != "sleep" and not self._busy()
        if allow_move:
            dxr = self.tx - self.x
            dist = abs(dxr)
            if dist > 0.5:
                # decelerate so we stop exactly at the target: v^2 = 2*a*d
                v_stop = math.sqrt(2.0 * ACCEL * dist)
                v_target = math.copysign(min(self.speed_cap, v_stop), dxr)
            else:
                self.x = self.tx
                v_target = 0.0
            # ramp velocity toward target
            dv = v_target - self.vx
            max_dv = ACCEL * dt
            if abs(dv) > max_dv:
                dv = math.copysign(max_dv, dv)
            self.vx += dv
            self.x += self.vx * dt
            # snap when we cross the target while decelerating
            if (self.tx - self.x) * dxr < 0:
                self.x = self.tx
                self.vx = 0.0
        else:
            self.vx = 0.0

        if abs(self.vx) > 6.0:
            self.facing = 1 if self.vx > 0 else -1

        # --- stride phase from distance travelled (no ice-skating) ---
        moved = abs(self.x - prev_x)
        stride = STRIDE_RUN if self.gait == "run" else STRIDE_WALK
        if moved > 0.001:
            self.stride_phase += moved / stride

        if self.look_wobble:
            self.look_wobble *= math.exp(-dt * 5.0)
            if abs(self.look_wobble) < 0.001:
                self.look_wobble = 0.0

        self._update_pose(now)

        # --- move the window (integer margin; sub-pixel drawn inside) ---
        win_x = int(math.floor(self.x))
        if win_x != self.last_win_x:
            Gtk4LayerShell.set_margin(self.win, Gtk4LayerShell.Edge.LEFT, win_x)
            self.last_win_x = win_x

        # --- adaptive tick + redraw ---
        active = (
            abs(self.vx) > 0.5 or self.jumping or self._busy()
            or self.fade_from is not None or abs(self.squash) > 0.003
            or abs(self.look_wobble) > 0.003
        )
        if active:
            self.area.queue_draw()
            self._idle_draw_phase = None
        else:
            # breathing only: ~8 redraws/s is plenty for a ±3px breath cycle
            phase = int((now - self._t0) * 8)
            if phase != self._idle_draw_phase:
                self._idle_draw_phase = phase
                self.area.queue_draw()

        want = TICK_ACTIVE_MS if active else TICK_IDLE_MS
        if want != self._tick_interval:
            self._tick_interval = want
            GLib.timeout_add(want, self._tick)
            return GLib.SOURCE_REMOVE
        return GLib.SOURCE_CONTINUE

    def _update_pose(self, now):
        if self.mode == "sleep" and not self._busy():
            self._set_pose("sit")
            return
        if self.jumping:
            self._set_pose("jump", crossfade=False)
            return
        if self._busy():
            frames, fps = self._frames_for(self.action["name"])
            idx = int((now - self.action["start"]) * fps) % len(frames)
            self._set_pose(frames[idx], crossfade=(len(frames) == 1))
            return
        if abs(self.vx) > 6.0:
            state = "run" if self.gait == "run" and abs(self.vx) > WALK_SPEED * 1.6 else "walk"
            frames, _ = self._frames_for(state)
            idx = int(self.stride_phase) % len(frames)
            self._set_pose(frames[idx], crossfade=False)
        else:
            self._set_pose("idle")

    # ---- Behaviour: calm weighted state machine -----------------------------
    def _decide(self, now):
        if self.action and now >= self.action["until"]:
            self.action = None

        idle_for = now - self.last_activity
        if self.mode != "sleep" and idle_for >= IDLE_SECONDS and not self._busy():
            self._go_sleep(now)
            return
        if self.mode == "sleep" or self._busy() or self.jumping:
            return
        if abs(self.tx - self.x) > 2.0:      # still travelling
            return
        if now < self.next_decision:
            return
        self.next_decision = now + random.uniform(DECIDE_MIN, DECIDE_MAX)

        # A stroll is on its own slow clock; everything else is a light gesture.
        if now >= self.next_stroll:
            self.next_stroll = now + random.uniform(STROLL_EVERY * 0.6, STROLL_EVERY * 1.5)
            if random.random() < 0.18:
                self._start_run(now)          # rare playful dash
            else:
                self._stroll(now)
            return

        r = random.random()
        if r < 0.55:
            pass                              # keep chilling (most common)
        elif r < 0.70:
            # look around: flip to face the other way with a tiny head wobble
            self.facing *= -1
            self.look_wobble = 0.06 * self.facing
        elif r < 0.79:
            self._do_action(now, "wave", 2.2)
        elif r < 0.88:
            self._do_action(now, "peace", 2.2)
        elif r < 0.95:
            self.facing = random.choice([-1, 1])
            self._do_action(now, "point", 2.2)
        else:
            self._do_jump(now)

    def _stroll(self, now):
        self.gait = "walk"
        self.speed_cap = WALK_SPEED
        # short, believable stroll: 120-420 px from here, not across the world
        span = random.uniform(120, 420) * random.choice([-1, 1])
        self.tx = float(max(0, min(self.max_x, self.x + span)))

    def _start_run(self, now):
        self.gait = "run"
        self.speed_cap = RUN_SPEED
        span = random.uniform(400, 900) * random.choice([-1, 1])
        self.tx = float(max(0, min(self.max_x, self.x + span)))

    def _do_jump(self, now):
        if self.jumping:
            return
        self.jumping = True
        self.vlift = JUMP_V0 * random.uniform(0.85, 1.1)
        self.squash = 0.12
        self.gait = "walk"
        self.speed_cap = WALK_SPEED

    def _do_action(self, now, name, secs):
        self.tx = self.x
        self.action = {"name": name, "start": now, "until": now + secs}

    def _go_sleep(self, now):
        self.mode = "sleep"
        self.action = None
        self.gait = "walk"
        self.speed_cap = WALK_SPEED
        # doze off close to where he is (drift toward the nearest side a bit)
        edge = 0.0 if self.x < self.max_x / 2 else float(self.max_x)
        self.tx = self.x + (edge - self.x) * 0.3

    def _wake(self):
        if self.mode == "sleep":
            self.mode = "wander"
            self.next_decision = time.monotonic() + random.uniform(2, 6)

    def _register_activity(self):
        self.last_activity = time.monotonic()
        self._wake()

    # ---- Sound ---------------------------------------------------------------
    def _play_sound(self, event, ambient=True):
        """Fire-and-forget through nyxus-sound. Ambient sounds are rate-limited."""
        if not SOUND:
            return
        now = time.monotonic()
        if ambient and now - self._last_sound < SOUND_COOLDOWN:
            return
        self._last_sound = now
        try:
            subprocess.Popen(
                ["nyxus-sound", event],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL, start_new_session=True,
            )
        except Exception:
            pass

    # ---- Event handlers ----------------------------------------------------
    def _on_pressed(self, gesture, n_press, x, y):
        self.laugh()

    def laugh(self):
        self._register_activity()
        now = time.monotonic()
        self.jumping = False
        self.lift = 0.0
        self.tx = self.x
        self.action = {"name": "laugh", "start": now, "until": now + 2.4}
        self._play_sound("laugh", ambient=False)

    def on_notification(self):
        self._register_activity()
        now = time.monotonic()
        self.action = {"name": "notify", "start": now, "until": now + 2.8}
        self.facing = 1
        self._play_sound("chatter")

    def on_workspace(self):
        self._register_activity()
        now = time.monotonic()
        # a calm acknowledging look, occasionally a little hop
        if random.random() < 0.25 and not self.jumping:
            self.jumping = True
            self.vlift = JUMP_V0 * 0.55
            self.squash = 0.08
        else:
            self.look_wobble = 0.06 * self.facing

    def on_alert(self, on: bool):
        if not on or self._busy():
            return
        now = time.monotonic()
        self.action = {"name": "alert", "start": now, "until": now + 2.4}
        self._play_sound("yell")

    def on_nudge(self, cmd: str):
        cmd = cmd.strip().lower()
        now = time.monotonic()
        if cmd in ("notification", "notify"):
            self.on_notification()
        elif cmd == "workspace":
            self.on_workspace()
        elif cmd == "idle":
            self.last_activity = now - IDLE_SECONDS - 1
        elif cmd in ("active", "wake"):
            self._register_activity()
        elif cmd == "peace":
            self._register_activity()
            self._do_action(now, "peace", 2.4)
        elif cmd in ("wave", "hello", "hi"):
            self._register_activity()
            self._do_action(now, "wave", 2.4)
        elif cmd == "point":
            self._register_activity()
            self._do_action(now, "point", 2.4)
        elif cmd in ("laugh", "click"):
            self.laugh()
        elif cmd == "jump":
            self._register_activity()
            self._do_jump(now)
        elif cmd == "stroll":
            self._register_activity()
            self._stroll(now)
        elif cmd in ("sit", "sleep"):
            self._go_sleep(now)
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
        if not shutil.which("socat"):
            print("nyxus-companion: socat missing; hypr events off", file=sys.stderr)
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
