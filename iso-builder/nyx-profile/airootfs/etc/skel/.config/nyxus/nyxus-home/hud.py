"""
NYXUS Home — SYSTEM HUD widgets (rev r1 · 2026-07-08)
Borderless neon instrumentation: ring gauges, fan dials, mirrored
net graph, per-core bars, storage + process readouts. All data is
sampled from /proc, /sys/class/hwmon and nvidia-smi — no fake numbers.
(c) 2026 Joseph Sierengowski - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import glob
import math
import os
import shutil
import subprocess
import threading
import time
from collections import deque

import cairo
import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib  # noqa: E402

from style import PALETTE  # noqa: E402

HISTORY = 120  # seconds of graph history


def _rgb(hexstr):
    h = hexstr.lstrip("#")
    return int(h[0:2], 16) / 255, int(h[2:4], 16) / 255, int(h[4:6], 16) / 255


def _temp_color(t):
    """Heat-coded color for a °C reading."""
    if t is None:
        return PALETTE["dim"]
    if t >= 85:
        return PALETTE["red"]
    if t >= 75:
        return PALETTE["orange"]
    if t >= 60:
        return PALETTE["gold"]
    return PALETTE["green"]


def _fmt_rate(bps):
    if bps >= 1073741824:
        return f"{bps / 1073741824:.1f} GB/s"
    if bps >= 1048576:
        return f"{bps / 1048576:.1f} MB/s"
    if bps >= 1024:
        return f"{bps / 1024:.0f} KB/s"
    return f"{int(bps)} B/s"


# ═══════════════════════════════════════════════════════════════════
#  SAMPLER — one shared 1 Hz probe; widgets subscribe to ticks.
# ═══════════════════════════════════════════════════════════════════
class Sampler:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self._subs = []

        # rolling histories (0-100 unless noted)
        self.cpu_hist = deque([0.0] * HISTORY, maxlen=HISTORY)
        self.ram_hist = deque([0.0] * HISTORY, maxlen=HISTORY)
        self.gpu_hist = deque([0.0] * HISTORY, maxlen=HISTORY)
        self.rx_hist = deque([0.0] * HISTORY, maxlen=HISTORY)   # bytes/s
        self.tx_hist = deque([0.0] * HISTORY, maxlen=HISTORY)   # bytes/s
        self.io_hist = deque([0.0] * HISTORY, maxlen=HISTORY)   # bytes/s

        # instantaneous values
        self.cpu = 0.0
        self.cores = []           # per-core 0-100
        self.cpu_freq = 0.0       # GHz
        self.cpu_temp = None
        self.ram = 0.0
        self.ram_used_g = 0.0
        self.ram_total_g = 0.0
        self.swap = 0.0
        self.rx_rate = 0.0
        self.tx_rate = 0.0
        self.io_rate = 0.0
        self.fans = []            # [(label, rpm), ...]
        self.temps = []           # [(label, °C), ...]
        self.load1 = 0.0
        self.load5 = 0.0
        self.uptime = 0.0
        self.disk_used = 0.0      # %
        self.disk_used_g = 0.0
        self.disk_total_g = 0.0
        self.bat_pct = None
        self.bat_status = ""
        self.bat_watts = None
        self.net_ifaces = []      # [(name, state, extra)]

        # nvidia (background thread)
        self.gpu_util = None
        self.gpu_temp = None
        self.gpu_mem_used = None
        self.gpu_mem_total = None
        self.gpu_watts = None
        self.gpu_name = ""

        # top processes (background thread)
        self.procs = []           # [(pcpu, pmem, comm)]

        # hwmon discovery
        self._fan_paths = []      # (label, path)
        self._temp_paths = []     # (label, path, divisor-applied later)
        self._discover_hwmon()

        self._prev_cpu = self._read_cpu_raw()
        self._prev_cores = self._read_cores_raw()
        self._prev_net = self._read_net_raw()
        self._prev_io = self._read_io_raw()
        self._prev_t = time.monotonic()

        self._nv_ok = shutil.which("nvidia-smi") is not None
        self._nv_busy = False
        self._ps_busy = False

        self._tick()
        GLib.timeout_add(1000, self._tick)

    def subscribe(self, cb):
        self._subs.append(cb)

    # ── discovery ────────────────────────────────────────────────────
    def _discover_hwmon(self):
        cpu_temp = nvme_temp = wifi_temp = ram_temp = None
        for hw in sorted(glob.glob("/sys/class/hwmon/hwmon*")):
            try:
                name = open(os.path.join(hw, "name")).read().strip()
            except OSError:
                continue
            for fp in sorted(glob.glob(os.path.join(hw, "fan*_input"))):
                idx = os.path.basename(fp)[3:-6]
                lbl_f = os.path.join(hw, f"fan{idx}_label")
                try:
                    lbl = open(lbl_f).read().strip().upper()
                except OSError:
                    lbl = f"FAN {idx}"
                self._fan_paths.append((lbl, fp))
            if name in ("coretemp", "k10temp", "zenpower") and cpu_temp is None:
                p = os.path.join(hw, "temp1_input")
                if os.path.exists(p):
                    cpu_temp = p
            elif name == "nvme" and nvme_temp is None:
                p = os.path.join(hw, "temp1_input")
                if os.path.exists(p):
                    nvme_temp = p
            elif name.startswith("iwlwifi") and wifi_temp is None:
                p = os.path.join(hw, "temp1_input")
                if os.path.exists(p):
                    wifi_temp = p
            elif name == "spd5118" and ram_temp is None:
                p = os.path.join(hw, "temp1_input")
                if os.path.exists(p):
                    ram_temp = p
        self._cpu_temp_path = cpu_temp
        for lbl, p in (("NVME", nvme_temp), ("RAM", ram_temp),
                       ("WIFI", wifi_temp)):
            if p:
                self._temp_paths.append((lbl, p))

    # ── raw readers ──────────────────────────────────────────────────
    @staticmethod
    def _read_cpu_raw():
        with open("/proc/stat") as f:
            parts = f.readline().split()[1:]
        vals = [int(x) for x in parts]
        idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
        return idle, sum(vals)

    @staticmethod
    def _read_cores_raw():
        out = []
        with open("/proc/stat") as f:
            for line in f:
                if not line.startswith("cpu") or line.startswith("cpu "):
                    continue
                vals = [int(x) for x in line.split()[1:]]
                idle = vals[3] + (vals[4] if len(vals) > 4 else 0)
                out.append((idle, sum(vals)))
        return out

    @staticmethod
    def _read_net_raw():
        rx = tx = 0
        with open("/proc/net/dev") as f:
            for line in f.readlines()[2:]:
                name, data = line.split(":", 1)
                name = name.strip()
                if (name == "lo" or name.startswith(("veth", "br-", "docker",
                                                     "virbr", "tun", "tap"))):
                    continue
                cols = data.split()
                rx += int(cols[0])
                tx += int(cols[8])
        return rx, tx

    @staticmethod
    def _read_io_raw():
        total = 0
        try:
            with open("/proc/diskstats") as f:
                for line in f:
                    cols = line.split()
                    # whole physical devices only (nvme0n1 / sda), no partitions
                    dev = cols[2]
                    if (dev.startswith("nvme") and "p" not in dev) or \
                       (dev.startswith("sd") and not dev[-1].isdigit()):
                        total += (int(cols[5]) + int(cols[9])) * 512
        except OSError:
            pass
        return total

    def _read_temp_mC(self, path):
        try:
            return int(open(path).read()) / 1000.0
        except (OSError, ValueError):
            return None

    # ── background probes ────────────────────────────────────────────
    def _poll_nvidia(self):
        try:
            out = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=utilization.gpu,temperature.gpu,memory.used,"
                 "memory.total,power.draw,name",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip().split("\n")[0].split(", ")
            vals = (float(out[0]), float(out[1]), float(out[2]),
                    float(out[3]), float(out[4]), out[5])
        except Exception:
            vals = None

        def apply():
            self._nv_busy = False
            if vals:
                (self.gpu_util, self.gpu_temp, self.gpu_mem_used,
                 self.gpu_mem_total, self.gpu_watts, self.gpu_name) = vals
            return False
        GLib.idle_add(apply)

    def _poll_ps(self):
        try:
            out = subprocess.run(
                ["ps", "-eo", "pcpu,pmem,comm", "--sort=-pcpu",
                 "--no-headers"],
                capture_output=True, text=True, timeout=5,
            ).stdout.strip().split("\n")[:7]
            procs = []
            for line in out:
                parts = line.split(None, 2)
                if len(parts) == 3:
                    procs.append((float(parts[0]), float(parts[1]), parts[2]))
        except Exception:
            procs = []

        def apply():
            self._ps_busy = False
            if procs:
                self.procs = procs
            return False
        GLib.idle_add(apply)

    # ── 1 Hz tick ────────────────────────────────────────────────────
    def _tick(self):
        now = time.monotonic()
        dt = max(0.2, now - self._prev_t)
        self._prev_t = now

        # CPU total
        idle, total = self._read_cpu_raw()
        didle = idle - self._prev_cpu[0]
        dtotal = max(1, total - self._prev_cpu[1])
        self._prev_cpu = (idle, total)
        self.cpu = max(0.0, min(100.0, 100.0 * (1.0 - didle / dtotal)))
        self.cpu_hist.append(self.cpu)

        # per-core
        cores_now = self._read_cores_raw()
        cores = []
        for i, (ci, ct) in enumerate(cores_now):
            if i < len(self._prev_cores):
                pi, pt = self._prev_cores[i]
                d_t = max(1, ct - pt)
                cores.append(max(0.0, min(100.0,
                             100.0 * (1.0 - (ci - pi) / d_t))))
        self._prev_cores = cores_now
        self.cores = cores

        # cpu freq (avg over policies)
        freqs = []
        for p in glob.glob(
                "/sys/devices/system/cpu/cpufreq/policy*/scaling_cur_freq"):
            try:
                freqs.append(int(open(p).read()))
            except (OSError, ValueError):
                pass
        if freqs:
            self.cpu_freq = sum(freqs) / len(freqs) / 1e6

        # cpu temp
        if self._cpu_temp_path:
            self.cpu_temp = self._read_temp_mC(self._cpu_temp_path)

        # RAM + swap
        info = {}
        with open("/proc/meminfo") as f:
            for line in f:
                k, v = line.split(":", 1)
                info[k] = int(v.strip().split()[0])
        total_kb = info.get("MemTotal", 1)
        avail_kb = info.get("MemAvailable", total_kb)
        self.ram = 100.0 * (total_kb - avail_kb) / total_kb
        self.ram_used_g = (total_kb - avail_kb) / 1048576
        self.ram_total_g = total_kb / 1048576
        self.ram_hist.append(self.ram)
        st, sf = info.get("SwapTotal", 0), info.get("SwapFree", 0)
        self.swap = 100.0 * (st - sf) / st if st else 0.0

        # NET split rates
        rx, tx = self._read_net_raw()
        self.rx_rate = max(0.0, (rx - self._prev_net[0]) / dt)
        self.tx_rate = max(0.0, (tx - self._prev_net[1]) / dt)
        self._prev_net = (rx, tx)
        self.rx_hist.append(self.rx_rate)
        self.tx_hist.append(self.tx_rate)

        # interface states
        ifaces = []
        for path in sorted(glob.glob("/sys/class/net/*")):
            name = os.path.basename(path)
            if (name == "lo" or name.startswith(("veth", "br-", "docker",
                                                 "virbr", "tun", "tap"))):
                continue
            try:
                state = open(os.path.join(path, "operstate")).read().strip()
            except OSError:
                state = "?"
            extra = ""
            if state == "up":
                try:
                    spd = int(open(os.path.join(path, "speed")).read())
                    if spd > 0:
                        extra = f"{spd} Mb/s"
                except (OSError, ValueError):
                    pass
                if name.startswith("wl"):
                    try:
                        with open("/proc/net/wireless") as f:
                            for line in f.readlines()[2:]:
                                if line.strip().startswith(name):
                                    q = float(line.split()[2].rstrip("."))
                                    extra = f"link {q:.0f}/70"
                    except OSError:
                        pass
            ifaces.append((name, state, extra))
        self.net_ifaces = ifaces

        # DISK usage + io
        try:
            st_ = os.statvfs("/")
            total_b = st_.f_blocks * st_.f_frsize
            free_b = st_.f_bavail * st_.f_frsize
            self.disk_total_g = total_b / 1073741824
            self.disk_used_g = (total_b - free_b) / 1073741824
            self.disk_used = 100.0 * (total_b - free_b) / max(1, total_b)
        except OSError:
            pass
        io = self._read_io_raw()
        self.io_rate = max(0.0, (io - self._prev_io) / dt)
        self._prev_io = io
        self.io_hist.append(self.io_rate)

        # FANS
        fans = []
        for lbl, p in self._fan_paths:
            try:
                fans.append((lbl, int(open(p).read())))
            except (OSError, ValueError):
                fans.append((lbl, 0))
        self.fans = fans

        # TEMPS strip
        temps = []
        if self.cpu_temp is not None:
            temps.append(("CPU", self.cpu_temp))
        if self.gpu_temp is not None:
            temps.append(("GPU", self.gpu_temp))
        for lbl, p in self._temp_paths:
            t = self._read_temp_mC(p)
            if t is not None:
                temps.append((lbl, t))
        self.temps = temps

        # load / uptime
        try:
            self.load1, self.load5, _ = os.getloadavg()
            self.uptime = float(open("/proc/uptime").read().split()[0])
        except OSError:
            pass

        # battery
        for bat in glob.glob("/sys/class/power_supply/BAT*"):
            try:
                self.bat_pct = int(open(os.path.join(bat, "capacity")).read())
                self.bat_status = open(
                    os.path.join(bat, "status")).read().strip()
                try:
                    ua = int(open(os.path.join(bat, "current_now")).read())
                    uv = int(open(os.path.join(bat, "voltage_now")).read())
                    self.bat_watts = ua * uv / 1e12
                except OSError:
                    try:
                        self.bat_watts = int(open(
                            os.path.join(bat, "power_now")).read()) / 1e6
                    except OSError:
                        self.bat_watts = None
            except (OSError, ValueError):
                pass
            break

        # gpu history (even between polls, repeat last value)
        self.gpu_hist.append(self.gpu_util or 0.0)

        # async probes
        if self._nv_ok and not self._nv_busy:
            self._nv_busy = True
            threading.Thread(target=self._poll_nvidia, daemon=True).start()
        if not self._ps_busy:
            self._ps_busy = True
            threading.Thread(target=self._poll_ps, daemon=True).start()

        for cb in self._subs:
            try:
                cb()
            except Exception:
                pass
        return True


# ═══════════════════════════════════════════════════════════════════
#  SHARED ANIMATION CLOCK — 20 fps, drives fan spin + graph sweeps
# ═══════════════════════════════════════════════════════════════════
class _AnimClock:
    _subs = []
    _started = False

    @classmethod
    def add(cls, widget):
        cls._subs.append(widget)
        if not cls._started:
            cls._started = True
            GLib.timeout_add(50, cls._tick)

    @classmethod
    def _tick(cls):
        for w in cls._subs:
            try:
                w.anim_tick()
            except Exception:
                pass
        return True


# ═══════════════════════════════════════════════════════════════════
#  RING GAUGE — neon 270° arc with layered glow + Overlay labels
# ═══════════════════════════════════════════════════════════════════
class RingGauge(Gtk.Overlay):
    START = math.radians(135)
    SWEEP = math.radians(270)

    def __init__(self, color_hex, title, size=132):
        super().__init__()
        self.color = _rgb(color_hex)
        self.color_hex = color_hex
        self.pct = 0.0
        self._shown = 0.0   # eased display value

        self.area = Gtk.DrawingArea()
        self.area.set_content_width(size)
        self.area.set_content_height(size)
        self.area.set_draw_func(self._draw)
        self.set_child(self.area)

        centre = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        centre.set_halign(Gtk.Align.CENTER)
        centre.set_valign(Gtk.Align.CENTER)
        self.value_lbl = Gtk.Label(label="—")
        self.value_lbl.add_css_class("ring-value")
        self.sub_lbl = Gtk.Label(label="")
        self.sub_lbl.add_css_class("ring-sub")
        centre.append(self.value_lbl)
        centre.append(self.sub_lbl)
        self.add_overlay(centre)

        title_lbl = Gtk.Label(label=title)
        title_lbl.add_css_class(f"ring-title-{self._css_key(color_hex)}")
        title_lbl.set_halign(Gtk.Align.CENTER)
        title_lbl.set_valign(Gtk.Align.END)
        title_lbl.set_margin_bottom(2)
        self.add_overlay(title_lbl)
        _AnimClock.add(self)

    @staticmethod
    def _css_key(hexstr):
        for k, v in PALETTE.items():
            if v == hexstr:
                return k
        return "mono"

    def set_value(self, pct, value_text, sub_text=""):
        self.pct = max(0.0, min(100.0, pct))
        self.value_lbl.set_text(value_text)
        self.sub_lbl.set_text(sub_text)

    def anim_tick(self):
        # ease toward target for a liquid needle feel
        d = self.pct - self._shown
        if abs(d) > 0.15:
            self._shown += d * 0.18
            self.area.queue_draw()

    def _draw(self, _a, cr, w, h):
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 12
        r, g, b = self.color

        # track
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_source_rgba(r, g, b, 0.10)
        cr.set_line_width(6)
        cr.arc(cx, cy, radius, self.START, self.START + self.SWEEP)
        cr.stroke()

        # minor ticks on the track
        cr.set_source_rgba(1, 1, 1, 0.12)
        cr.set_line_width(1)
        for i in range(11):
            a = self.START + self.SWEEP * i / 10
            x1 = cx + math.cos(a) * (radius - 8)
            y1 = cy + math.sin(a) * (radius - 8)
            x2 = cx + math.cos(a) * (radius - 12)
            y2 = cy + math.sin(a) * (radius - 12)
            cr.move_to(x1, y1)
            cr.line_to(x2, y2)
            cr.stroke()

        frac = self._shown / 100.0
        if frac <= 0.004:
            return
        end = self.START + self.SWEEP * frac

        # layered glow strokes (outer → core)
        for lw, alpha in ((14, 0.07), (9, 0.16), (5.5, 0.85)):
            cr.set_source_rgba(r, g, b, alpha)
            cr.set_line_width(lw)
            cr.arc(cx, cy, radius, self.START, end)
            cr.stroke()

        # hot tip dot
        tx = cx + math.cos(end) * radius
        ty = cy + math.sin(end) * radius
        for rad, alpha in ((7, 0.25), (3.2, 1.0)):
            cr.set_source_rgba(min(1, r + 0.3), min(1, g + 0.3),
                               min(1, b + 0.3), alpha)
            cr.arc(tx, ty, rad, 0, 2 * math.pi)
            cr.fill()


# ═══════════════════════════════════════════════════════════════════
#  FAN DIAL — spinning 3-blade rotor, speed ∝ RPM
# ═══════════════════════════════════════════════════════════════════
class FanDial(Gtk.Box):
    def __init__(self, color_hex, size=84):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        self.color = _rgb(color_hex)
        self.rpm = 0
        self.angle = 0.0
        self.size = size

        self.area = Gtk.DrawingArea()
        self.area.set_content_width(size)
        self.area.set_content_height(size)
        self.area.set_draw_func(self._draw)
        self.area.set_halign(Gtk.Align.CENTER)
        self.append(self.area)

        self.rpm_lbl = Gtk.Label(label="—")
        self.rpm_lbl.add_css_class("fan-rpm")
        self.append(self.rpm_lbl)
        self.name_lbl = Gtk.Label(label="")
        self.name_lbl.add_css_class("fan-name")
        self.append(self.name_lbl)
        _AnimClock.add(self)

    def set_fan(self, label, rpm):
        self.rpm = rpm
        self.name_lbl.set_text(label)
        self.rpm_lbl.set_text(f"{rpm:,} RPM" if rpm > 0 else "IDLE")

    def anim_tick(self):
        if self.rpm > 0:
            # visual spin: up to ~1.2 rot/s at 10k RPM — readable, not a blur
            self.angle += (self.rpm / 10000.0) * 0.38
            self.area.queue_draw()

    def _draw(self, _a, cr, w, h):
        cx, cy = w / 2, h / 2
        radius = min(w, h) / 2 - 6
        r, g, b = self.color
        spinning = self.rpm > 0
        base_a = 1.0 if spinning else 0.28

        # housing ring
        cr.set_source_rgba(r, g, b, 0.22 * base_a)
        cr.set_line_width(2)
        cr.arc(cx, cy, radius, 0, 2 * math.pi)
        cr.stroke()
        if spinning:
            cr.set_source_rgba(r, g, b, 0.08)
            cr.set_line_width(6)
            cr.arc(cx, cy, radius, 0, 2 * math.pi)
            cr.stroke()

        # 3 swept blades
        cr.save()
        cr.translate(cx, cy)
        cr.rotate(self.angle)
        for i in range(3):
            cr.save()
            cr.rotate(i * 2 * math.pi / 3)
            cr.move_to(0, 0)
            cr.curve_to(radius * 0.55, -radius * 0.10,
                        radius * 0.80, -radius * 0.42,
                        radius * 0.86, -radius * 0.16)
            cr.curve_to(radius * 0.70, radius * 0.10,
                        radius * 0.35, radius * 0.12,
                        0, 0)
            cr.close_path()
            grad = cairo.LinearGradient(0, 0, radius * 0.86, 0)
            grad.add_color_stop_rgba(0, r, g, b, 0.30 * base_a)
            grad.add_color_stop_rgba(1, r, g, b, 0.92 * base_a)
            cr.set_source(grad)
            cr.fill()
            cr.restore()
        cr.restore()

        # hub
        cr.set_source_rgba(r, g, b, 0.9 * base_a)
        cr.arc(cx, cy, 4.5, 0, 2 * math.pi)
        cr.fill()
        cr.set_source_rgba(0.03, 0.02, 0.06, 1)
        cr.arc(cx, cy, 2.0, 0, 2 * math.pi)
        cr.fill()


# ═══════════════════════════════════════════════════════════════════
#  GRAPHS
# ═══════════════════════════════════════════════════════════════════
class GlowSpark(Gtk.DrawingArea):
    """Filled sparkline (0-100 history) with glow crest + sweep line."""

    def __init__(self, color_hex, history, height=52, sweep=True):
        super().__init__()
        self.color = _rgb(color_hex)
        self.history = history
        self.sweep = sweep
        self.set_content_height(height)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)
        if sweep:
            _AnimClock.add(self)

    def anim_tick(self):
        self.queue_draw()

    def _draw(self, _a, cr, w, h):
        pts = list(self.history)
        if len(pts) < 2:
            return
        r, g, b = self.color
        # grid
        cr.set_source_rgba(1, 1, 1, 0.05)
        cr.set_line_width(1)
        for frac in (0.25, 0.5, 0.75):
            cr.move_to(0, h * frac)
            cr.line_to(w, h * frac)
            cr.stroke()
        step = w / (len(pts) - 1)

        def y(v):
            return h - (max(0.0, min(100.0, v)) / 100.0) * (h - 4) - 1

        cr.move_to(0, h)
        for i, v in enumerate(pts):
            cr.line_to(i * step, y(v))
        cr.line_to(w, h)
        cr.close_path()
        grad = cairo.LinearGradient(0, 0, 0, h)
        grad.add_color_stop_rgba(0, r, g, b, 0.30)
        grad.add_color_stop_rgba(1, r, g, b, 0.01)
        cr.set_source(grad)
        cr.fill()
        # glow crest
        for lw, alpha in ((4.5, 0.18), (1.7, 0.95)):
            cr.set_source_rgba(r, g, b, alpha)
            cr.set_line_width(lw)
            for i, v in enumerate(pts):
                (cr.move_to if i == 0 else cr.line_to)(i * step, y(v))
            cr.stroke()
        # sweep line
        if self.sweep:
            sx = (time.monotonic() % 6.0) / 6.0 * w
            grad = cairo.LinearGradient(sx - 40, 0, sx, 0)
            grad.add_color_stop_rgba(0, r, g, b, 0)
            grad.add_color_stop_rgba(1, r, g, b, 0.30)
            cr.set_source(grad)
            cr.rectangle(sx - 40, 0, 40, h)
            cr.fill()


class DualNetGraph(Gtk.DrawingArea):
    """Mirrored RX (up from axis) / TX (down from axis) area graph,
    per-direction rolling-peak autoscale."""

    def __init__(self, sampler, height=96):
        super().__init__()
        self.s = sampler
        self.rx_color = _rgb(PALETTE["cyan"])
        self.tx_color = _rgb(PALETTE["pink"])
        self._rx_peak = 1024.0
        self._tx_peak = 1024.0
        self.set_content_height(height)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)
        _AnimClock.add(self)

    def anim_tick(self):
        self.queue_draw()

    def _half(self, cr, pts, peak, w, mid, sign, color):
        r, g, b = color
        if len(pts) < 2:
            return
        step = w / (len(pts) - 1)
        amp = mid - 6

        def y(v):
            return mid + sign * (min(1.0, v / peak) * amp)

        cr.move_to(0, mid)
        for i, v in enumerate(pts):
            cr.line_to(i * step, y(v))
        cr.line_to(w, mid)
        cr.close_path()
        grad = cairo.LinearGradient(0, mid, 0, mid + sign * amp)
        grad.add_color_stop_rgba(0, r, g, b, 0.04)
        grad.add_color_stop_rgba(1, r, g, b, 0.34)
        cr.set_source(grad)
        cr.fill()
        for lw, alpha in ((4, 0.16), (1.6, 0.95)):
            cr.set_source_rgba(r, g, b, alpha)
            cr.set_line_width(lw)
            for i, v in enumerate(pts):
                (cr.move_to if i == 0 else cr.line_to)(i * step, y(v))
            cr.stroke()

    def _draw(self, _a, cr, w, h):
        mid = h / 2
        rx = list(self.s.rx_hist)
        tx = list(self.s.tx_hist)
        self._rx_peak = max(self._rx_peak * 0.995, 10240.0, *rx)
        self._tx_peak = max(self._tx_peak * 0.995, 10240.0, *tx)

        # centre axis — dashed
        cr.set_source_rgba(1, 1, 1, 0.16)
        cr.set_line_width(1)
        cr.set_dash([3, 4])
        cr.move_to(0, mid)
        cr.line_to(w, mid)
        cr.stroke()
        cr.set_dash([])

        self._half(cr, rx, self._rx_peak, w, mid, -1, self.rx_color)   # down = above
        self._half(cr, tx, self._tx_peak, w, mid, +1, self.tx_color)   # up = below

        # sweep
        sx = (time.monotonic() % 6.0) / 6.0 * w
        grad = cairo.LinearGradient(sx - 50, 0, sx, 0)
        grad.add_color_stop_rgba(0, 1, 1, 1, 0)
        grad.add_color_stop_rgba(1, 1, 1, 1, 0.10)
        cr.set_source(grad)
        cr.rectangle(sx - 50, 0, 50, h)
        cr.fill()


class CoreGrid(Gtk.DrawingArea):
    """One neon bar per logical core, hue-shifted across the row."""

    def __init__(self, sampler, height=54):
        super().__init__()
        self.s = sampler
        self.set_content_height(height)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)
        self._shown = []

    def refresh(self):
        cores = self.s.cores
        if len(self._shown) != len(cores):
            self._shown = list(cores)
        else:
            self._shown = [s + (c - s) * 0.45
                           for s, c in zip(self._shown, cores)]
        self.queue_draw()

    def _draw(self, _a, cr, w, h):
        cores = self._shown
        n = len(cores)
        if not n:
            return
        gap = 5.0
        bw = max(3.0, (w - gap * (n - 1)) / n)
        c1 = _rgb(PALETTE["pink"])
        c2 = _rgb(PALETTE["purple"])
        for i, v in enumerate(cores):
            t = i / max(1, n - 1)
            r = c1[0] + (c2[0] - c1[0]) * t
            g = c1[1] + (c2[1] - c1[1]) * t
            b = c1[2] + (c2[2] - c1[2]) * t
            x = i * (bw + gap)
            # socket track
            cr.set_source_rgba(r, g, b, 0.10)
            cr.rectangle(x, 2, bw, h - 4)
            cr.fill()
            bh = (max(1.5, v) / 100.0) * (h - 4)
            # glow pass + core bar
            cr.set_source_rgba(r, g, b, 0.25)
            cr.rectangle(x - 1, h - 2 - bh - 1, bw + 2, bh + 2)
            cr.fill()
            grad = cairo.LinearGradient(0, h - 2 - bh, 0, h - 2)
            grad.add_color_stop_rgba(0, min(1, r + 0.25), min(1, g + 0.25),
                                     min(1, b + 0.25), 1.0)
            grad.add_color_stop_rgba(1, r, g, b, 0.55)
            cr.set_source(grad)
            cr.rectangle(x, h - 2 - bh, bw, bh)
            cr.fill()


class BarMeter(Gtk.DrawingArea):
    """Slim horizontal neon bar (0-100)."""

    def __init__(self, color_hex, height=10):
        super().__init__()
        self.color = _rgb(color_hex)
        self.pct = 0.0
        self.set_content_height(height)
        self.set_hexpand(True)
        self.set_draw_func(self._draw)

    def set_pct(self, pct):
        self.pct = max(0.0, min(100.0, pct))
        self.queue_draw()

    def _draw(self, _a, cr, w, h):
        r, g, b = self.color
        mid = h / 2
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        cr.set_source_rgba(r, g, b, 0.12)
        cr.set_line_width(4)
        cr.move_to(3, mid)
        cr.line_to(w - 3, mid)
        cr.stroke()
        x = 3 + (w - 6) * self.pct / 100.0
        for lw, alpha in ((8, 0.14), (4, 0.95)):
            cr.set_source_rgba(r, g, b, alpha)
            cr.set_line_width(lw)
            cr.move_to(3, mid)
            cr.line_to(x, mid)
            cr.stroke()
        cr.set_source_rgba(1, 1, 1, 0.9)
        cr.arc(x, mid, 2.2, 0, 2 * math.pi)
        cr.fill()


# ═══════════════════════════════════════════════════════════════════
#  GHOST CHROME — borderless card header (no box, just a laser rule)
# ═══════════════════════════════════════════════════════════════════
def make_ghost(color_key, title, glyph):
    root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    root.add_css_class("ghost-card")
    root.set_hexpand(True)

    header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    g = Gtk.Label(label=glyph)
    g.add_css_class(f"ghost-glyph-{color_key}")
    t = Gtk.Label(label=title, xalign=0.0)
    t.add_css_class(f"ghost-title-{color_key}")
    header.append(g)
    header.append(t)
    spacer = Gtk.Box()
    spacer.set_hexpand(True)
    header.append(spacer)
    root.append(header)

    rule = Gtk.Box()
    rule.add_css_class(f"ghost-rule-{color_key}")
    rule.set_size_request(-1, 1)
    root.append(rule)

    content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
    content.set_vexpand(True)
    root.append(content)

    footer = Gtk.Label(label="", xalign=0.0)
    footer.add_css_class(f"ghost-footer-{color_key}")
    root.append(footer)
    return root, content, footer.set_text


# ═══════════════════════════════════════════════════════════════════
#  CARDS
# ═══════════════════════════════════════════════════════════════════
class SystemCoreCard:
    """Centerpiece: CPU / GPU / RAM / BAT rings + per-core bars + temps."""

    def __init__(self):
        self.s = Sampler.get()
        self.root, content, self.set_footer = make_ghost(
            "pink", "SYSTEM CORE", "◉")

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)

        self.cpu_ring = RingGauge(PALETTE["pink"], "CPU")
        self.gpu_ring = RingGauge(PALETTE["green"], "GPU")
        self.ram_ring = RingGauge(PALETTE["purple"], "RAM")
        self.bat_ring = RingGauge(PALETTE["gold"], "PWR")
        for ring in (self.cpu_ring, self.gpu_ring,
                     self.ram_ring, self.bat_ring):
            ring.set_halign(Gtk.Align.CENTER)
            row.append(ring)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        right.set_hexpand(True)
        right.set_valign(Gtk.Align.CENTER)

        core_head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        cl = Gtk.Label(label="CORES", xalign=0.0)
        cl.add_css_class("hud-mini-title")
        cl.set_hexpand(True)
        self.freq_lbl = Gtk.Label(label="", xalign=1.0)
        self.freq_lbl.add_css_class("hud-mini-value")
        core_head.append(cl)
        core_head.append(self.freq_lbl)
        right.append(core_head)

        self.core_grid = CoreGrid(self.s)
        right.append(self.core_grid)

        self.temp_lbl = Gtk.Label(xalign=0.0)
        self.temp_lbl.set_use_markup(True)
        self.temp_lbl.add_css_class("hud-temp-strip")
        self.temp_lbl.set_wrap(True)
        right.append(self.temp_lbl)

        row.append(right)
        content.append(row)

        self.s.subscribe(self._refresh)
        self._refresh()

    def _refresh(self):
        s = self.s
        tc = f" · {s.cpu_temp:.0f}°C" if s.cpu_temp is not None else ""
        self.cpu_ring.set_value(s.cpu, f"{s.cpu:.0f}%",
                                f"{s.cpu_freq:.1f} GHz" if s.cpu_freq else "")
        if s.gpu_util is not None:
            gsub = f"{s.gpu_watts:.0f} W" if s.gpu_watts is not None else ""
            self.gpu_ring.set_value(s.gpu_util, f"{s.gpu_util:.0f}%", gsub)
        else:
            self.gpu_ring.set_value(0, "—", "no probe")
        self.ram_ring.set_value(
            s.ram, f"{s.ram:.0f}%",
            f"{s.ram_used_g:.1f}/{s.ram_total_g:.0f}G")
        if s.bat_pct is not None:
            stat = {"Charging": "CHG", "Discharging": "BAT",
                    "Full": "FULL", "Not charging": "AC"}.get(
                        s.bat_status, s.bat_status.upper()[:4])
            wsub = (f"{stat} {s.bat_watts:.0f}W"
                    if s.bat_watts else stat)
            self.bat_ring.set_value(s.bat_pct, f"{s.bat_pct}%", wsub)
        else:
            self.bat_ring.set_value(0, "AC", "desktop")

        self.freq_lbl.set_text(
            f"{len(s.cores)} THREADS · {s.cpu_freq:.2f} GHZ{tc}")
        self.core_grid.refresh()

        # heat-coded temp strip
        parts = []
        for lbl, t in s.temps:
            c = _temp_color(t)
            parts.append(
                f"<span foreground='{PALETTE['dim']}'>{lbl}</span> "
                f"<span foreground='{c}'>{t:.0f}°</span>")
        self.temp_lbl.set_markup(
            "<span letter_spacing='2048'>" + "   ".join(parts) + "</span>"
            if parts else "")

        up = s.uptime
        d, hrs, mins = int(up // 86400), int(up % 86400 // 3600), int(up % 3600 // 60)
        upstr = (f"{d}d {hrs}h {mins:02d}m" if d else f"{hrs}h {mins:02d}m")
        self.set_footer(
            f"LOAD {s.load1:.2f} / {s.load5:.2f} · SWAP {s.swap:.0f}% "
            f"· UP {upstr} · /proc + hwmon @ 1 HZ")


class FansCard:
    def __init__(self):
        self.s = Sampler.get()
        self.root, content, self.set_footer = make_ghost(
            "gold", "FANS", "✹")
        self.flow = Gtk.FlowBox()
        self.flow.set_selection_mode(Gtk.SelectionMode.NONE)
        self.flow.set_max_children_per_line(2)
        self.flow.set_min_children_per_line(2)
        self.flow.set_column_spacing(8)
        self.flow.set_row_spacing(6)
        self.dials = []
        colors = [PALETTE["gold"], PALETTE["orange"],
                  PALETTE["cyan"], PALETTE["purple"]]
        for i in range(len(self.s.fans)):
            dial = FanDial(colors[i % len(colors)])
            self.dials.append(dial)
            self.flow.append(dial)
        if not self.dials:
            none = Gtk.Label(label="no fan sensors exposed")
            none.add_css_class("hud-dim-note")
            content.append(none)
        content.append(self.flow)
        self.s.subscribe(self._refresh)
        self._refresh()

    def _refresh(self):
        active = 0
        for dial, (lbl, rpm) in zip(self.dials, self.s.fans):
            dial.set_fan(lbl, rpm)
            if rpm > 0:
                active += 1
        self.set_footer(
            f"{active}/{len(self.dials)} SPINNING · msi_wmi_platform")


class NetworkCard:
    def __init__(self):
        self.s = Sampler.get()
        self.root, content, self.set_footer = make_ghost(
            "cyan", "NETWORK", "⇅")

        rates = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18)
        self.rx_lbl = Gtk.Label(xalign=0.0)
        self.rx_lbl.set_use_markup(True)
        self.rx_lbl.add_css_class("net-rate")
        self.tx_lbl = Gtk.Label(xalign=0.0)
        self.tx_lbl.set_use_markup(True)
        self.tx_lbl.add_css_class("net-rate")
        rates.append(self.rx_lbl)
        rates.append(self.tx_lbl)
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        rates.append(spacer)
        self.if_lbl = Gtk.Label(xalign=1.0)
        self.if_lbl.set_use_markup(True)
        self.if_lbl.add_css_class("net-ifaces")
        rates.append(self.if_lbl)
        content.append(rates)

        content.append(DualNetGraph(self.s))
        self.s.subscribe(self._refresh)
        self._refresh()

    def _refresh(self):
        s = self.s
        self.rx_lbl.set_markup(
            f"<span foreground='{PALETTE['cyan']}'>▼ RX</span> "
            f"<span foreground='#e8edf5'>{_fmt_rate(s.rx_rate)}</span>")
        self.tx_lbl.set_markup(
            f"<span foreground='{PALETTE['pink']}'>▲ TX</span> "
            f"<span foreground='#e8edf5'>{_fmt_rate(s.tx_rate)}</span>")
        chunks = []
        for name, state, extra in s.net_ifaces:
            c = PALETTE["green"] if state == "up" else PALETTE["dim"]
            ex = f" {extra}" if extra else ""
            chunks.append(f"<span foreground='{c}'>{name}{ex}</span>")
        self.if_lbl.set_markup("  ·  ".join(chunks))
        self.set_footer("RX ABOVE AXIS · TX BELOW · AUTOSCALED PEAK")


class StorageCard:
    def __init__(self):
        self.s = Sampler.get()
        self.root, content, self.set_footer = make_ghost(
            "orange", "STORAGE", "⛁")

        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        lbl = Gtk.Label(label="/", xalign=0.0)
        lbl.add_css_class("hud-mini-title")
        lbl.set_hexpand(True)
        self.use_lbl = Gtk.Label(xalign=1.0)
        self.use_lbl.add_css_class("hud-mini-value")
        head.append(lbl)
        head.append(self.use_lbl)
        content.append(head)

        self.bar = BarMeter(PALETTE["orange"])
        content.append(self.bar)

        io_head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        io_lbl = Gtk.Label(label="DISK I/O", xalign=0.0)
        io_lbl.add_css_class("hud-mini-title")
        io_lbl.set_hexpand(True)
        self.io_lbl = Gtk.Label(xalign=1.0)
        self.io_lbl.add_css_class("hud-mini-value")
        io_head.append(io_lbl)
        io_head.append(self.io_lbl)
        content.append(io_head)

        self._io_pct = deque([0.0] * HISTORY, maxlen=HISTORY)
        self._io_peak = 1048576.0
        self.spark = GlowSpark(PALETTE["orange"], self._io_pct, height=44)
        content.append(self.spark)

        self.s.subscribe(self._refresh)
        self._refresh()

    def _refresh(self):
        s = self.s
        self.use_lbl.set_text(
            f"{s.disk_used_g:.0f} / {s.disk_total_g:.0f} G · {s.disk_used:.0f}%")
        self.bar.set_pct(s.disk_used)
        self.io_lbl.set_text(_fmt_rate(s.io_rate))
        self._io_peak = max(self._io_peak * 0.995, 1048576.0, s.io_rate)
        self._io_pct.append(100.0 * s.io_rate / self._io_peak)
        nvme = next((t for l, t in s.temps if l == "NVME"), None)
        tail = f" · NVME {nvme:.0f}°C" if nvme is not None else ""
        self.set_footer(f"STATVFS + DISKSTATS{tail}")


class ProcessesCard:
    ROWS = 6

    def __init__(self):
        self.s = Sampler.get()
        self.root, content, self.set_footer = make_ghost(
            "blue", "TOP PROCS", "≡")
        self.rows = []
        for _ in range(self.ROWS):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            name = Gtk.Label(xalign=0.0)
            name.add_css_class("proc-name")
            name.set_hexpand(True)
            name.set_ellipsize(3)
            bar = BarMeter(PALETTE["blue"], height=8)
            bar.set_size_request(72, -1)
            bar.set_hexpand(False)
            pct = Gtk.Label(xalign=1.0)
            pct.add_css_class("proc-pct")
            pct.set_width_chars(6)
            row.append(name)
            row.append(bar)
            row.append(pct)
            content.append(row)
            self.rows.append((name, bar, pct))
        self.s.subscribe(self._refresh)
        self._refresh()

    def _refresh(self):
        procs = self.s.procs[:self.ROWS]
        ncpu = max(1, len(self.s.cores))
        for i, (name, bar, pct) in enumerate(self.rows):
            if i < len(procs):
                pc, pm, comm = procs[i]
                name.set_text(comm)
                bar.set_pct(min(100.0, pc / ncpu * 4))  # 25% of a core = full-ish
                pct.set_text(f"{pc:.1f}%")
            else:
                name.set_text("")
                bar.set_pct(0)
                pct.set_text("")
        self.set_footer("PS · SORTED BY CPU · 3S CADENCE")
