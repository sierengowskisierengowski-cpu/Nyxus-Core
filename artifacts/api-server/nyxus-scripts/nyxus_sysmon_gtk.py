#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS SysMon GTK — Native GTK4 System Monitoring Dashboard          ║
# ║  Full-screen · Workspace 6 · Cairo charts · psutil                   ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
# Install:  pacman -S python-gobject gtk4 python-psutil
# Run:      python3 ~/.nyxus/nyxus_sysmon_gtk.py

import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
import math, time, os, threading, socket
from collections import deque
from datetime import datetime

try:
    import psutil
except ImportError:
    import subprocess
    subprocess.run(["pip", "install", "psutil"], check=True)
    import psutil

HIST = 60

# Cairo color tuples (r,g,b,a)
C_BG     = (0.012, 0.008, 0.024, 1)
C_PANEL  = (0.027, 0.012, 0.059, 1)
C_PINK   = (1.0,   0.0,   1.0,   1)
C_PURPLE = (0.8,   0.0,   1.0,   1)
C_BLUE   = (0.0,   0.533, 1.0,   1)
C_GREEN  = (0.224, 1.0,   0.078, 1)
C_YELLOW = (1.0,   1.0,   0.0,   1)
C_ORANGE = (1.0,   0.333, 0.0,   1)
C_TEXT   = (0.91,  0.88,  0.96,  1)
C_DIM    = (0.44,  0.376, 0.627, 1)
C_BORDER = (0.12,  0.067, 0.235, 1)

CSS = b"""
* { font-family: 'JetBrains Mono', 'Monospace', monospace; }
window { background-color: #030206; color: #e8e0f5; }
.hdr { background-color: #07030f; border-bottom: 1px solid rgba(204,0,255,0.25); padding: 5px 14px; }
.hdr-title { color: #ff00ff; font-size: 13px; font-weight: bold; letter-spacing: 2px; }
.hdr-host  { color: #7060a0; font-size: 11px; }
.hdr-clock { color: #ffff00; font-size: 13px; font-weight: bold; }
.hdr-live  { color: #39ff14; font-size: 14px; }
.section-title { color: #7060a0; font-size: 10px; font-weight: bold; letter-spacing: 3px; margin-bottom: 2px; }
.big-stat { color: #e8e0f5; font-size: 30px; font-weight: bold; }
.small-stat { color: #7060a0; font-size: 10px; }
.speed-up   { color: #ff5500; font-size: 18px; font-weight: bold; }
.speed-down { color: #0088ff; font-size: 18px; font-weight: bold; }
.stat-label { color: #7060a0; font-size: 10px; }
progressbar trough { background-color: rgba(255,255,255,0.06); border-radius: 2px; min-height: 6px; }
progressbar progress { border-radius: 2px; }
.pbar-cpu    progress { background-color: #ff00ff; }
.pbar-mem    progress { background-color: #cc00ff; }
.pbar-swap   progress { background-color: #0088ff; }
.pbar-disk-ok   progress { background-color: #39ff14; }
.pbar-disk-warn progress { background-color: #ffff00; }
.pbar-disk-hot  progress { background-color: #ff5500; }
"""


def clamp_rgb(c): return (min(1,max(0,c[0])), min(1,max(0,c[1])), min(1,max(0,c[2])))

def pct_color(pct):
    if pct < 60: return C_GREEN
    elif pct < 80: return C_YELLOW
    return C_ORANGE

def fmt_bytes(n, sfx="/s"):
    for u in ("B","KB","MB","GB"):
        if abs(n) < 1024: return f"{n:.1f} {u}{sfx}"
        n /= 1024
    return f"{n:.1f} TB{sfx}"

def fmt_size(n):
    for u in ("B","KB","MB","GB","TB"):
        if abs(n) < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"


class State:
    def __init__(self):
        self.cpu      = 0.0
        self.cores    = []
        self.freq     = None
        self.load     = (0,0,0)
        self.ram_pct  = 0.0
        self.ram_used = 0; self.ram_total = 1
        self.swp_pct  = 0.0
        self.swp_used = 0; self.swp_total = 1
        self.net_up   = 0.0; self.net_dn  = 0.0; self.net_conn = 0
        self.disks    = []
        self.procs    = []
        self.uptime   = "00:00:00"
        self.hostname = socket.gethostname()
        self.cpu_h    = deque([0.0]*HIST, maxlen=HIST)
        self.up_h     = deque([0.0]*HIST, maxlen=HIST)
        self.dn_h     = deque([0.0]*HIST, maxlen=HIST)
        self._pnet    = None; self._pnet_t = None


def collect(st):
    st.cpu   = psutil.cpu_percent(interval=None)
    st.cores = psutil.cpu_percent(percpu=True, interval=None)
    f = psutil.cpu_freq()
    st.freq  = f.current if f else None
    st.load  = psutil.getloadavg()

    vm = psutil.virtual_memory(); sw = psutil.swap_memory()
    st.ram_pct  = vm.percent; st.ram_used = vm.used; st.ram_total = vm.total
    st.swp_pct  = sw.percent; st.swp_used = sw.used; st.swp_total = sw.total

    now = time.time(); cnt = psutil.net_io_counters()
    if st._pnet and st._pnet_t:
        dt = now - st._pnet_t
        if dt > 0:
            st.net_up = max(0, (cnt.bytes_sent - st._pnet.bytes_sent)/dt)
            st.net_dn = max(0, (cnt.bytes_recv - st._pnet.bytes_recv)/dt)
    st._pnet = cnt; st._pnet_t = now
    try: st.net_conn = len([c for c in psutil.net_connections("inet") if c.status=="ESTABLISHED"])
    except Exception: st.net_conn = 0

    st.disks = []
    for p in psutil.disk_partitions():
        if p.fstype in ("tmpfs","devtmpfs","squashfs","overlay",""): continue
        try:
            u = psutil.disk_usage(p.mountpoint)
            st.disks.append({"dev": p.device.split("/")[-1], "mount": p.mountpoint,
                              "pct": u.percent, "free": u.free, "total": u.total})
        except Exception: pass

    procs = []
    for p in psutil.process_iter(["pid","name","cpu_percent","memory_percent","status"]):
        try:
            i = p.info
            procs.append((i["pid"], (i["name"] or "")[:30],
                          round(i["cpu_percent"] or 0,1),
                          round(i["memory_percent"] or 0,2),
                          i["status"] or ""))
        except Exception: pass
    st.procs = sorted(procs, key=lambda x: x[2], reverse=True)[:25]

    up = int(time.time() - psutil.boot_time())
    h, r = divmod(up, 3600); m, s = divmod(r, 60)
    st.uptime = f"{h:02d}:{m:02d}:{s:02d}"

    st.cpu_h.append(st.cpu)
    st.up_h.append(st.net_up)
    st.dn_h.append(st.net_dn)


class NyxusSysmonGtk(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.sysmon")
        self.st = State()
        psutil.cpu_percent(interval=0.1)
        psutil.cpu_percent(percpu=True, interval=None)

    def do_activate(self):
        p = Gtk.CssProvider(); p.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self, title="NYXUS SysMon")
        self.win.set_default_size(1280, 720)
        self.win.fullscreen()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)

        root.append(self._hdr())

        # Top stat cards
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        top.set_margin_top(1); top.set_homogeneous(True)
        top.append(self._card("CPU",     self._build_cpu_card()))
        top.append(self._card("MEMORY",  self._build_mem_card()))
        top.append(self._card("NETWORK", self._build_net_card()))
        top.append(self._card("DISK",    self._build_disk_card()))
        root.append(top)

        # Core grid
        self._core_area = self._da(self._draw_cores, -1, 70)
        cg = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        cg.set_margin_top(1); cg.set_margin_start(2); cg.set_margin_end(2)
        cg.append(self._lbl("CPU CORES", "section-title"))
        cg.append(self._core_area)
        root.append(cg)

        # Bottom: charts + procs
        bot = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        bot.set_vexpand(True); bot.set_margin_top(1)
        root.append(bot)

        charts = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        charts.set_hexpand(True)
        self._cpu_h_area = self._da(self._draw_cpu_hist, -1, -1)
        self._cpu_h_area.set_vexpand(True)
        charts.append(self._card("CPU HISTORY (2 MIN)", self._cpu_h_area))
        self._net_h_area = self._da(self._draw_net_hist, -1, -1)
        self._net_h_area.set_vexpand(True)
        charts.append(self._card("NETWORK THROUGHPUT (2 MIN)", self._net_h_area))
        bot.append(charts)

        proc_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        proc_box.set_hexpand(True)
        proc_box.append(self._lbl("PROCESSES", "section-title"))
        proc_box.append(self._build_proc_table())
        bot.append(proc_box)

        GLib.timeout_add(2000, self._tick)
        GLib.timeout_add(1000, self._clock_tick)
        self._tick()
        self.win.present()

    # ── Header ──────────────────────────────────────────────────────────────────
    def _hdr(self):
        h = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        h.add_css_class("hdr")
        t = Gtk.Label(label="NYXUS_SYSMON"); t.add_css_class("hdr-title"); h.append(t)
        sep = Gtk.Label(label="·"); sep.add_css_class("hdr-host"); h.append(sep)
        self._host_lbl = Gtk.Label(label=self.st.hostname); self._host_lbl.add_css_class("hdr-host"); h.append(self._host_lbl)
        self._up_lbl   = Gtk.Label(label="UP 00:00:00");    self._up_lbl.add_css_class("hdr-host");  h.append(self._up_lbl)
        sp = Gtk.Box(); sp.set_hexpand(True); h.append(sp)
        dot = Gtk.Label(label="●"); dot.add_css_class("hdr-live"); h.append(dot)
        self._clk = Gtk.Label(label="00:00:00"); self._clk.add_css_class("hdr-clock"); h.append(self._clk)
        return h

    def _clock_tick(self):
        self._clk.set_text(datetime.now().strftime("%H:%M:%S"))
        return GLib.SOURCE_CONTINUE

    # ── Stat cards ──────────────────────────────────────────────────────────────
    def _build_cpu_card(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._cpu_da = self._da(self._draw_cpu_ring, 160, 160)
        box.append(self._cpu_da)
        self._cpu_load = self._lbl("LOAD: --", "small-stat"); box.append(self._cpu_load)
        self._cpu_freq_lbl = self._lbl("FREQ: --", "small-stat"); box.append(self._cpu_freq_lbl)
        return box

    def _build_mem_card(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self._ram_pct_lbl = Gtk.Label(label="--"); self._ram_pct_lbl.add_css_class("big-stat")
        self._ram_pct_lbl.set_halign(Gtk.Align.START); box.append(self._ram_pct_lbl)
        box.append(self._lbl("RAM", "stat-label"))
        self._ram_bar = Gtk.ProgressBar(); self._ram_bar.add_css_class("pbar-mem"); box.append(self._ram_bar)
        self._ram_lbl = self._lbl("-- / --", "small-stat"); box.append(self._ram_lbl)
        box.append(self._lbl("SWAP", "stat-label"))
        self._swp_bar = Gtk.ProgressBar(); self._swp_bar.add_css_class("pbar-swap"); box.append(self._swp_bar)
        self._swp_lbl = self._lbl("-- / --", "small-stat"); box.append(self._swp_lbl)
        return box

    def _build_net_card(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_valign(Gtk.Align.CENTER)
        self._up_spd = Gtk.Label(label="↑ -- B/s"); self._up_spd.add_css_class("speed-up"); self._up_spd.set_halign(Gtk.Align.START)
        self._dn_spd = Gtk.Label(label="↓ -- B/s"); self._dn_spd.add_css_class("speed-down"); self._dn_spd.set_halign(Gtk.Align.START)
        self._conn_lbl = self._lbl("ESTABLISHED: --", "small-stat")
        box.append(self._up_spd); box.append(self._dn_spd); box.append(self._conn_lbl)
        return box

    def _build_disk_card(self):
        self._disk_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        return self._disk_box

    def _build_proc_table(self):
        self._proc_store = Gtk.ListStore(int, str, str, str, str)
        tv = Gtk.TreeView(model=self._proc_store)
        tv.set_headers_visible(True)
        for title, col in [("PID",0),("NAME",1),("CPU%",2),("MEM%",3),("STATUS",4)]:
            r = Gtk.CellRendererText()
            c = Gtk.TreeViewColumn(title, r, text=col); c.set_resizable(True); tv.append_column(c)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True); scroll.set_hexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(tv)
        return scroll

    # ── Cairo drawing ────────────────────────────────────────────────────────────
    def _draw_cpu_ring(self, area, cr, w, h, _):
        cx, cy = w/2, h/2
        r = min(cx,cy) - 10
        pct = self.st.cpu
        color = pct_color(pct)
        # Background ring
        cr.set_source_rgba(*C_BORDER); cr.set_line_width(16)
        cr.arc(cx, cy, r-8, -math.pi/2, 3*math.pi/2); cr.stroke()
        # Colored arc
        if pct > 0:
            end = -math.pi/2 + (pct/100)*2*math.pi
            cr.set_source_rgba(*color); cr.set_line_width(16)
            cr.arc(cx, cy, r-8, -math.pi/2, end); cr.stroke()
        # Glow
        cr.set_source_rgba(color[0],color[1],color[2],0.18); cr.set_line_width(26)
        cr.arc(cx, cy, r-8, -math.pi/2, -math.pi/2+(pct/100)*2*math.pi); cr.stroke()
        # Percent text
        cr.set_source_rgba(*C_TEXT); cr.set_font_size(22)
        txt = f"{pct:.0f}%"
        ext = cr.text_extents(txt)
        cr.move_to(cx - ext.width/2 - ext.x_bearing, cy - ext.height/2 - ext.y_bearing)
        cr.show_text(txt)

    def _draw_cores(self, area, cr, w, h, _):
        cores = self.st.cores
        if not cores: return
        n = len(cores)
        bw = max(4, (w - (n+1)*2) / n)
        for i, pct in enumerate(cores):
            x = 2 + i*(bw+2)
            cr.set_source_rgba(*C_BORDER)
            cr.rectangle(x, 2, bw, h-18); cr.fill()
            fh = (pct/100)*(h-18)
            cr.set_source_rgba(*pct_color(pct))
            cr.rectangle(x, 2+(h-18-fh), bw, fh); cr.fill()
            cr.set_source_rgba(*C_DIM); cr.set_font_size(7)
            lbl = f"{int(pct)}"
            ext = cr.text_extents(lbl)
            cr.move_to(x+bw/2-ext.width/2-ext.x_bearing, h-4); cr.show_text(lbl)

    def _draw_area_chart(self, cr, w, h, hist, color, max_val=None):
        vals = list(hist)
        if not vals: return
        mv = max_val or (max(vals) if max(vals) > 0 else 1.0)
        step = w / max(len(vals)-1, 1)
        cr.new_path(); cr.move_to(0, h)
        for i, v in enumerate(vals):
            cr.line_to(i*step, h-(v/mv)*h*0.9)
        cr.line_to((len(vals)-1)*step, h); cr.close_path()
        cr.set_source_rgba(color[0],color[1],color[2],0.12); cr.fill()
        cr.new_path()
        for i, v in enumerate(vals):
            x, y = i*step, h-(v/mv)*h*0.9
            if i == 0: cr.move_to(x, y)
            else:       cr.line_to(x, y)
        cr.set_source_rgba(*color[:3], 0.9); cr.set_line_width(1.5); cr.stroke()

    def _draw_cpu_hist(self, area, cr, w, h, _):
        cr.set_source_rgba(*C_PANEL); cr.rectangle(0,0,w,h); cr.fill()
        self._draw_area_chart(cr, w, h, self.st.cpu_h, C_PINK, 100.0)
        cr.set_source_rgba(*C_DIM); cr.set_font_size(9)
        cr.move_to(4, 12); cr.show_text(f"CPU {self.st.cpu:.1f}%")

    def _draw_net_hist(self, area, cr, w, h, _):
        cr.set_source_rgba(*C_PANEL); cr.rectangle(0,0,w,h); cr.fill()
        all_v = list(self.st.up_h) + list(self.st.dn_h)
        mv = max(all_v) if any(v>0 for v in all_v) else 1.0
        self._draw_area_chart(cr, w, h, self.st.up_h, C_ORANGE, mv)
        self._draw_area_chart(cr, w, h, self.st.dn_h, C_BLUE, mv)
        cr.set_source_rgba(*C_DIM); cr.set_font_size(9)
        cr.move_to(4, 12)
        cr.show_text(f"↑ {fmt_bytes(self.st.net_up)}  ↓ {fmt_bytes(self.st.net_dn)}")

    # ── Data refresh ─────────────────────────────────────────────────────────────
    def _tick(self):
        threading.Thread(target=self._collect, daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _collect(self):
        collect(self.st); GLib.idle_add(self._refresh_ui)

    def _refresh_ui(self):
        st = self.st
        self._up_lbl.set_text(f"UP: {st.uptime}")
        self._cpu_load.set_text(f"LOAD: {st.load[0]:.2f} {st.load[1]:.2f} {st.load[2]:.2f}")
        if st.freq: self._cpu_freq_lbl.set_text(f"FREQ: {st.freq/1000:.2f} GHz")
        self._ram_pct_lbl.set_text(f"{st.ram_pct:.0f}%")
        self._ram_bar.set_fraction(st.ram_pct/100)
        self._ram_lbl.set_text(f"{fmt_size(st.ram_used)} / {fmt_size(st.ram_total)}")
        self._swp_bar.set_fraction(st.swp_pct/100 if st.swp_total > 0 else 0)
        self._swp_lbl.set_text(f"SWAP {st.swp_pct:.0f}%  {fmt_size(st.swp_used)} / {fmt_size(st.swp_total)}")
        self._up_spd.set_text(f"↑ {fmt_bytes(st.net_up)}")
        self._dn_spd.set_text(f"↓ {fmt_bytes(st.net_dn)}")
        self._conn_lbl.set_text(f"ESTABLISHED: {st.net_conn}")

        c = self._disk_box.get_first_child()
        while c:
            n = c.get_next_sibling(); self._disk_box.remove(c); c = n
        for d in st.disks[:5]:
            row = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
            css = "pbar-disk-hot" if d["pct"]>85 else ("pbar-disk-warn" if d["pct"]>70 else "pbar-disk-ok")
            lbl = Gtk.Label(label=f"{d['mount']}  {d['pct']:.0f}%  {fmt_size(d['free'])} free")
            lbl.add_css_class("small-stat"); lbl.set_halign(Gtk.Align.START)
            bar = Gtk.ProgressBar(); bar.add_css_class(css); bar.set_fraction(d["pct"]/100)
            row.append(lbl); row.append(bar); self._disk_box.append(row)

        self._proc_store.clear()
        for pid, name, cpu, mem, status in st.procs:
            self._proc_store.append([pid, name, f"{cpu:.1f}", f"{mem:.2f}", status])

        for a in [self._cpu_da, self._core_area, self._cpu_h_area, self._net_h_area]:
            a.queue_draw()
        return GLib.SOURCE_REMOVE

    # ── Helpers ──────────────────────────────────────────────────────────────────
    def _da(self, draw_func, w, h):
        a = Gtk.DrawingArea()
        a.set_size_request(w, h)
        a.set_draw_func(draw_func, None)
        return a

    def _card(self, title, child):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8); box.set_margin_bottom(8)
        box.set_margin_start(8); box.set_margin_end(8)
        box.append(self._lbl(title, "section-title"))
        box.append(child)
        return box

    def _lbl(self, text, css):
        l = Gtk.Label(label=text); l.add_css_class(css)
        l.set_halign(Gtk.Align.START)
        return l


if __name__ == "__main__":
    NyxusSysmonGtk().run(None)
