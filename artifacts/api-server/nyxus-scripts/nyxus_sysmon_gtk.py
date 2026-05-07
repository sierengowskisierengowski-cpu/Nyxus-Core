#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS SysMon GTK — Enterprise Edition · 8-section live dashboard   ║
# ║  Overview · CPU · Memory · Network · Disk · Processes · Sensors · Sys║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝

__nyxid__ = "4e59582d4a35572d323032362d53494552454e474f57534b492d4c4f434b4544"

def _nyx_integrity():
    try:
        _s = open(__file__, encoding="utf-8").read()
        assert "SIERENGOWSKI" in _s, "NYXUS: tamper detected"
    except (OSError, AssertionError) as _e:
        import sys as _sys; print(f"NYXUS SECURITY: {_e}", file=_sys.stderr)

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

_nyx_integrity()


import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Gio

# ── NYXUS shared chrome (rainbow titles + graffiti walls, system-wide) ──
def _nyxus_load_chrome():
    try:
        from nyxus_chrome import install_chrome, rainbow_markup
        return install_chrome, rainbow_markup
    except ImportError:
        try:
            import os, sys, urllib.request
            _here = os.path.dirname(os.path.abspath(__file__))
            urllib.request.urlretrieve(
                "https://nyxus-core.replit.app/api/download/nyxus/nyxus_chrome.py",
                os.path.join(_here, "nyxus_chrome.py"))
            if _here not in sys.path: sys.path.insert(0, _here)
            from nyxus_chrome import install_chrome, rainbow_markup
            return install_chrome, rainbow_markup
        except Exception:
            return (lambda *a, **kw: None), (lambda t: t)
_nyx_install_chrome, _nyx_rainbow = _nyxus_load_chrome()
import math, time, os, threading, socket, platform, signal, subprocess, traceback, sys
from collections import deque
from datetime import datetime, timedelta

try:
    import psutil
except ImportError:
    subprocess.run([sys.executable,"-m","pip","install","--break-system-packages","--quiet","psutil"],check=True)
    import psutil

HIST = 120  # 2 minutes at 1Hz

PALETTE = [
    (1.0,  0.0,  1.0 ),  # C_PINK
    (0.8,  0.0,  1.0 ),  # C_PURPLE
    (0.0,  0.53, 1.0 ),  # C_BLUE
    (0.22, 1.0,  0.08),  # C_GREEN
    (1.0,  1.0,  0.0 ),  # C_YELLOW
    (1.0,  0.33, 0.0 ),  # C_ORANGE
]
C_PINK, C_PURPLE, C_BLUE, C_GREEN, C_YELLOW, C_ORANGE = PALETTE
C_BG    = (0.031, 0.031, 0.055)   # #08080e deep dark
C_PANEL = (0.052, 0.052, 0.100)   # slightly lighter dark card
C_TEXT  = (0.91,  0.88,  0.96 )   # light lavender text
C_DIM   = (0.44,  0.376, 0.627)   # dim purple

PAGES = [
    ("OVERVIEW",  C_PINK),
    ("CPU",       C_ORANGE),
    ("MEMORY",    C_PURPLE),
    ("NETWORK",   C_BLUE),
    ("DISK",      C_GREEN),
    ("PROCESSES", C_YELLOW),
    ("SENSORS",   C_ORANGE),
    ("SYSTEM",    C_PINK),
]


# ── Drawing helpers ────────────────────────────────────────────────────────────

def pct_color(p):
    return C_GREEN if p < 60 else (C_YELLOW if p < 80 else C_ORANGE)

def temp_color(t):
    return C_GREEN if t < 60 else (C_YELLOW if t < 80 else C_ORANGE)

def fmt_bytes(n, sfx="/s"):
    for u in ("B","KB","MB","GB"):
        if abs(n) < 1024: return f"{n:.1f} {u}{sfx}"
        n /= 1024
    return f"{n:.1f} GB{sfx}"

def fmt_size(n):
    for u in ("B","KB","MB","GB","TB"):
        if abs(n) < 1024: return f"{n:.1f} {u}"
        n /= 1024
    return f"{n:.1f} PB"

def fmt_uptime(secs):
    td = timedelta(seconds=int(secs)); d = td.days
    h, r = divmod(td.seconds, 3600); m, s = divmod(r, 60)
    return f"{d}d {h:02d}:{m:02d}:{s:02d}" if d else f"{h:02d}:{m:02d}:{s:02d}"

def glow_text(cr, x, y, txt, r, g, b, size=12, bold=False):
    """Marker-pen style text — slight ink shadow, handwritten font."""
    cr.select_font_face("Caveat", 0, 1 if bold else 0)
    cr.set_font_size(size)
    cr.set_source_rgba(r, g, b, 0.18); cr.move_to(x+1.2, y+0.8); cr.show_text(txt)
    cr.set_source_rgba(r, g, b, 0.92); cr.move_to(x, y); cr.show_text(txt)

def draw_tilt_badge(cr, x, y, txt, color, angle=-4.5, size=14):
    """Tilted hand-drawn section badge — Caveat + sketch_rect border."""
    r, g, b = color
    cr.save()
    cr.translate(x, y); cr.rotate(math.radians(angle))
    cr.select_font_face("Caveat", 0, 1); cr.set_font_size(size)
    ext = cr.text_extents(txt)
    bw = ext.width + 18; bh = size + 10
    # Sketchy wobbly border
    sketch_rect(cr, -6, -(bh - 3), bw, bh, r, g, b,
                thick=2.2, jitter=2.5, fill_rgba=(r, g, b, 0.14))
    # Neon glow shadow on text
    cr.set_source_rgba(r, g, b, 0.25); cr.move_to(1.5, 1.0); cr.show_text(txt)
    # Text
    cr.set_source_rgba(r, g, b, 0.96); cr.move_to(0, 0); cr.show_text(txt)
    cr.restore()


def draw_nyxus_bg(cr, w, h):
    """Dark base fill — pure Cairo, no image dependency."""
    cr.set_source_rgb(*C_BG); cr.rectangle(0, 0, w, h); cr.fill()
    # Subtle dot grid for texture
    cr.set_source_rgba(0.55, 0.25, 0.85, 0.08)
    step = 22
    for gx in range(0, int(w) + step, step):
        for gy in range(0, int(h) + step, step):
            cr.arc(gx, gy, 1.0, 0, 6.2832)
            cr.fill()

def dim_text(cr, x, y, txt, size=11):
    cr.select_font_face("Caveat", 0, 0)
    cr.set_font_size(size); cr.set_source_rgba(*C_DIM, 0.85)
    cr.move_to(x, y); cr.show_text(txt)

def rainbow_bar(cr, x, y, w, h=2):
    seg = w / len(PALETTE)
    for i, (r, g, b) in enumerate(PALETTE):
        cr.set_source_rgba(r, g, b, 0.90); cr.rectangle(x+i*seg, y, seg, h); cr.fill()

import random as _rand

def _rng_seed(x, y, w=0, h=0):
    return int(x*3 + y*7 + (w or 1)*11 + (h or 1)*13) % 65535

def sketch_rect(cr, x, y, w, h, r, g, b, thick=2.2, jitter=2.8, fill_rgba=None):
    rng = _rand.Random(_rng_seed(x,y,w,h))
    j = lambda s=1.0: rng.uniform(-jitter*s, jitter*s)
    def _path():
        cr.move_to(x+j(.5),y+j(.5))
        cr.curve_to(x+w*.33+j(),y+j(),x+w*.67+j(),y+j(),x+w+j(.5),y+j(.5))
        cr.curve_to(x+w+j(),y+h*.33+j(),x+w+j(),y+h*.67+j(),x+w+j(.5),y+h+j(.5))
        cr.curve_to(x+w*.67+j(),y+h+j(),x+w*.33+j(),y+h+j(),x+j(.5),y+h+j(.5))
        cr.curve_to(x+j(),y+h*.67+j(),x+j(),y+h*.33+j(),x+j(.5),y+j(.5))
        cr.close_path()
    if fill_rgba:
        _path(); cr.set_source_rgba(*fill_rgba); cr.fill()
        rng2 = _rand.Random(_rng_seed(x,y,w,h)); j = lambda s=1.0: rng2.uniform(-jitter*s,jitter*s)
    _path()
    cr.set_source_rgba(r,g,b,0.88); cr.set_line_width(thick)
    cr.set_line_cap(1); cr.set_line_join(1); cr.stroke()

def dot_grid(cr, x, y, w, h, spacing=22):
    """Faint neon grid on dark background."""
    cr.set_line_width(0.40)
    for gx in range(int(x), int(x+w)+spacing, spacing):
        cr.set_source_rgba(0.30, 0.20, 0.60, 0.13)
        cr.move_to(gx, y); cr.line_to(gx, y+h); cr.stroke()
    for gy in range(int(y), int(y+h)+spacing, spacing):
        cr.set_source_rgba(0.30, 0.20, 0.60, 0.13)
        cr.move_to(x, gy); cr.line_to(x+w, gy); cr.stroke()

def neon_card(cr, x, y, w, h, color, tint=0.09):
    r, g, b = color
    # Neon glow shadow behind card
    cr.set_source_rgba(r, g, b, 0.08)
    cr.rectangle(x+5, y+6, w, h); cr.fill()
    # Card dark background
    cr.set_source_rgb(*C_PANEL); cr.rectangle(x, y, w, h); cr.fill()
    # Very subtle graph grid inside
    dot_grid(cr, x, y, w, h, spacing=20)
    # Wobbly marker border
    sketch_rect(cr, x+2, y+2, w-4, h-4, r, g, b, thick=2.5, jitter=2.5,
                fill_rgba=(r, g, b, 0.06))

def ring_chart(cr, cx, cy, R, pct, color):
    cr.set_source_rgba(*C_DIM, 0.20); cr.set_line_width(14)
    cr.arc(cx, cy, R, -math.pi/2, 3*math.pi/2); cr.stroke()
    if pct > 0:
        end = -math.pi/2 + (pct/100)*2*math.pi
        cr.set_source_rgba(*color); cr.set_line_width(14)
        cr.arc(cx, cy, R, -math.pi/2, end); cr.stroke()
        cr.set_source_rgba(*color, 0.22); cr.set_line_width(26)
        cr.arc(cx, cy, R, -math.pi/2, end); cr.stroke()

def hbar(cr, x, y, w, h, pct, color):
    cr.set_source_rgba(*C_DIM, 0.12); cr.rectangle(x, y, w, h); cr.fill()
    if pct > 0:
        fw = (pct/100)*w
        cr.set_source_rgba(*color, 0.9); cr.rectangle(x, y, fw, h); cr.fill()
        cr.set_source_rgba(*color, 0.22); cr.set_line_width(h+6)
        cr.move_to(x, y+h/2); cr.line_to(x+fw, y+h/2); cr.stroke()

def sparkline(cr, x, y, w, h, hist, color, max_val=None, grid=True):
    vals = list(hist)
    if not vals: return
    mv = max_val or (max(vals) if max(vals) > 0 else 1.0)
    step = w / max(len(vals)-1, 1)
    if grid:
        cr.set_source_rgba(*C_DIM, 0.08); cr.set_line_width(1)
        for pct in [25, 50, 75]:
            gy = y + h - (pct/100)*h
            cr.move_to(x, gy); cr.line_to(x+w, gy); cr.stroke()
    pts = [(x+i*step, y+h-(v/mv)*h*0.88) for i, v in enumerate(vals)]
    cr.new_path(); cr.move_to(x, y+h)
    for px, py in pts: cr.line_to(px, py)
    cr.line_to(x+(len(vals)-1)*step, y+h); cr.close_path()
    cr.set_source_rgba(*color, 0.15); cr.fill()
    cr.new_path()
    for i, (px, py) in enumerate(pts):
        if i == 0: cr.move_to(px, py)
        else: cr.line_to(px, py)
    cr.set_source_rgba(*color, 0.95); cr.set_line_width(1.8); cr.stroke()
    cr.new_path()
    for i, (px, py) in enumerate(pts):
        if i == 0: cr.move_to(px, py)
        else: cr.line_to(px, py)
    cr.set_source_rgba(*color, 0.22); cr.set_line_width(6); cr.stroke()


# ── Data ──────────────────────────────────────────────────────────────────────

class State:
    def __init__(self):
        self.cpu_pct=0.0; self.cpu_cores=[]; self.cpu_freq=None; self.cpu_freq_max=None
        self.cpu_load=(0,0,0); self.cpu_count_l=1; self.cpu_count_p=1
        self.cpu_model=""; self.cpu_temp=None
        self.ram_pct=0.0; self.ram_used=0; self.ram_total=1; self.ram_avail=0; self.ram_cached=0
        self.swp_pct=0.0; self.swp_used=0; self.swp_total=1
        self.net_up=0.0; self.net_dn=0.0; self.net_conn=0
        self.net_ifaces={}; self.net_conns_by_state={}
        self.net_total_sent=0; self.net_total_recv=0
        self.disks=[]; self.disk_io={}
        self.procs=[]; self.proc_count=0; self.proc_run=0
        self.temps={}; self.battery=None; self.fans={}
        self.gpu_util=None; self.gpu_mem_used=None; self.gpu_mem_total=None; self.gpu_temp=None
        self.hostname=socket.gethostname(); self.uptime="00:00:00"; self.boot_time=""
        self.os_name=""; self.kernel=""; self.arch=platform.machine()
        self.cpu_h=deque([0.0]*HIST,maxlen=HIST); self.ram_h=deque([0.0]*HIST,maxlen=HIST)
        self.up_h=deque([0.0]*HIST,maxlen=HIST);  self.dn_h=deque([0.0]*HIST,maxlen=HIST)
        self._pnet=None; self._pnet_t=None; self._pnic={}; self._pnic_t=None
        self._pdisk=None; self._pdisk_t=None

def _cpu_model():
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line: return line.split(":")[1].strip()[:44]
    except Exception: pass
    return platform.processor()[:44] or "Unknown CPU"

def _os_name():
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="): return line.split("=",1)[1].strip().strip('"')
    except Exception: pass
    return platform.system()

def _nvidia():
    try:
        out = subprocess.check_output(
            ["nvidia-smi","--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"], timeout=2, stderr=subprocess.DEVNULL
        ).decode().strip().split(",")
        if len(out) >= 4:
            return float(out[0]), int(out[1]), int(out[2]), float(out[3])
    except Exception: pass
    return None, None, None, None

def collect(st):
    st.cpu_pct   = psutil.cpu_percent(interval=None)
    st.cpu_cores = psutil.cpu_percent(percpu=True, interval=None)
    f = psutil.cpu_freq()
    st.cpu_freq = f.current if f else None
    st.cpu_freq_max = f.max if f else None
    st.cpu_load = psutil.getloadavg()
    st.cpu_count_l = psutil.cpu_count(logical=True)
    st.cpu_count_p = psutil.cpu_count(logical=False) or 1
    if not st.cpu_model: st.cpu_model = _cpu_model()

    try:
        temps = psutil.sensors_temperatures()
        for key in ("coretemp","k10temp","cpu_thermal","acpitz","zenpower"):
            if key in temps and temps[key]:
                st.cpu_temp = max(t.current for t in temps[key]); break
        st.temps = temps
    except Exception: st.temps = {}

    vm = psutil.virtual_memory(); sw = psutil.swap_memory()
    st.ram_pct=vm.percent; st.ram_used=vm.used; st.ram_total=vm.total
    st.ram_avail=vm.available; st.ram_cached=getattr(vm,'cached',0)
    st.swp_pct=sw.percent; st.swp_used=sw.used; st.swp_total=sw.total

    now = time.time(); cnt = psutil.net_io_counters()
    st.net_total_sent = cnt.bytes_sent; st.net_total_recv = cnt.bytes_recv
    if st._pnet and st._pnet_t:
        dt = now - st._pnet_t
        if dt > 0:
            st.net_up = max(0, (cnt.bytes_sent-st._pnet.bytes_sent)/dt)
            st.net_dn = max(0, (cnt.bytes_recv-st._pnet.bytes_recv)/dt)
    st._pnet=cnt; st._pnet_t=now
    try:
        conns=psutil.net_connections("inet")
        st.net_conn=len([c for c in conns if c.status=="ESTABLISHED"])
        sc={}
        for c in conns:
            if c.status: sc[c.status]=sc.get(c.status,0)+1
        st.net_conns_by_state=sc
    except Exception: pass

    try:
        nics=psutil.net_io_counters(pernic=True); addrs=psutil.net_if_addrs()
        nt=time.time(); ifaces={}
        for nic,nc in nics.items():
            if nic=="lo": continue
            prev=st._pnic.get(nic); pt=st._pnic_t; up_bps=dn_bps=0.0
            if prev and pt:
                dt2=nt-pt
                if dt2>0: up_bps=max(0,(nc.bytes_sent-prev.bytes_sent)/dt2); dn_bps=max(0,(nc.bytes_recv-prev.bytes_recv)/dt2)
            ip=mac=""
            for addr in addrs.get(nic,[]):
                import socket as _s
                if addr.family==_s.AF_INET: ip=addr.address
                elif hasattr(addr.family,'name') and addr.family.name=="AF_PACKET": mac=addr.address
            ifaces[nic]={"up":up_bps,"dn":dn_bps,"ip":ip,"mac":mac,"total_sent":nc.bytes_sent,"total_recv":nc.bytes_recv}
        st.net_ifaces=ifaces; st._pnic={n:nics[n] for n in nics}; st._pnic_t=nt
    except Exception: pass

    st.disks=[]
    for p in psutil.disk_partitions():
        if p.fstype in ("tmpfs","devtmpfs","squashfs","overlay","","proc","sysfs","efivarfs"): continue
        try:
            u=psutil.disk_usage(p.mountpoint)
            st.disks.append({"dev":p.device.split("/")[-1],"mount":p.mountpoint,
                              "fstype":p.fstype,"pct":u.percent,"free":u.free,
                              "total":u.total,"used":u.used})
        except Exception: pass

    try:
        dicnt=psutil.disk_io_counters(perdisk=True); dt3=time.time()
        io={}
        for dev,dc in dicnt.items():
            prev=(st._pdisk or {}).get(dev); pt=st._pdisk_t; rb=wb=0.0
            if prev and pt:
                dtd=dt3-pt
                if dtd>0: rb=max(0,(dc.read_bytes-prev.read_bytes)/dtd); wb=max(0,(dc.write_bytes-prev.write_bytes)/dtd)
            io[dev]={"read_bps":rb,"write_bps":wb,"reads":dc.read_count,"writes":dc.write_count}
        st.disk_io=io; st._pdisk=dicnt; st._pdisk_t=dt3
    except Exception: pass

    procs=[]; run=0
    for p in psutil.process_iter(["pid","name","cpu_percent","memory_percent","status","memory_info","username"]):
        try:
            i=p.info
            if i["status"]=="running": run+=1
            rss=i["memory_info"].rss if i["memory_info"] else 0
            procs.append((i["pid"],(i["name"] or "")[:28],round(i["cpu_percent"] or 0,1),
                          round(i["memory_percent"] or 0,2),i["status"] or "",rss,i["username"] or ""))
        except Exception: pass
    st.procs=sorted(procs,key=lambda x:x[2],reverse=True)[:80]
    st.proc_count=len(procs); st.proc_run=run

    try:
        b=psutil.sensors_battery()
        st.battery={"pct":b.percent,"charging":b.power_plugged,
                    "secs_left":b.secsleft if b and b.secsleft and b.secsleft>0 else None} if b else None
    except Exception: st.battery=None
    try: st.fans=psutil.sensors_fans()
    except Exception: st.fans={}

    st.gpu_util,st.gpu_mem_used,st.gpu_mem_total,st.gpu_temp=_nvidia()

    up=time.time()-psutil.boot_time()
    st.uptime=fmt_uptime(up)
    if not st.boot_time: st.boot_time=datetime.fromtimestamp(psutil.boot_time()).strftime("%d %b %Y %H:%M")
    if not st.os_name: st.os_name=_os_name()
    if not st.kernel: st.kernel=platform.uname().release[:40]

    st.cpu_h.append(st.cpu_pct); st.ram_h.append(st.ram_pct)
    st.up_h.append(st.net_up);   st.dn_h.append(st.net_dn)


# ── CSS ───────────────────────────────────────────────────────────────────────

CSS = format_css("""
* {{ font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', 'Sans'; }}
window {{ background-color: #08080e; color: rgba(232,224,245,0.92); }}

/* ── Nav sidebar ─────────────────────────────────────────────────────── */
.nav-bar {{
    background-color: {INK_BLACK};
    border-right: 3px solid rgba(255,0,255,0.30);
    min-width: 168px;
}}
.nav-btn {{
    background-color: rgba(255,255,255,0.03);
    color: rgba(180,160,220,0.75);
    border: 1px solid rgba(255,0,255,0.14);
    border-left: 5px solid transparent;
    border-radius: 4px;
    padding: 13px 14px 13px 15px;
    margin: 3px 8px;
    font-size: 17px; font-weight: bold; letter-spacing: 2px; min-height: 0;
}}
.nav-btn:hover {{
    background-color: rgba(255,0,255,0.11);
    color: rgba(255,200,255,0.96);
    border-color: rgba(255,0,255,0.38);
}}
.nav-active-pink   {{ background: rgba(255,0,255,0.14); color: #ff99ff;
                     border-left: 5px solid {WHITE_OFF};
                     border-color: rgba(255,0,255,0.45); }}
.nav-active-orange {{ background: rgba(255,85,0,0.14); color: #ff9966;
                     border-left: 5px solid {WHITE_OFF};
                     border-color: rgba(255,85,0,0.45); }}
.nav-active-purple {{ background: rgba(204,0,255,0.14); color: #ee99ff;
                     border-left: 5px solid {WHITE_OFF};
                     border-color: rgba(204,0,255,0.45); }}
.nav-active-blue   {{ background: rgba(0,136,255,0.14); color: #77ccff;
                     border-left: 5px solid {GREY_LIGHT};
                     border-color: rgba(0,136,255,0.45); }}
.nav-active-green  {{ background: rgba(57,255,20,0.11); color: #99ff66;
                     border-left: 5px solid {GREY_LIGHT};
                     border-color: rgba(57,255,20,0.45); }}
.nav-active-yellow {{ background: rgba(255,255,0,0.11); color: #ffff99;
                     border-left: 5px solid {WHITE_OFF};
                     border-color: rgba(255,255,0,0.45); }}

/* ── Search input ────────────────────────────────────────────────────── */
.search-e {{
    background-color: rgba(255,255,255,0.06);
    color: rgba(232,224,245,0.88);
    border: 2px solid rgba(255,0,255,0.30); border-radius: 4px;
    padding: 5px 12px; font-size: 15px; box-shadow: none; caret-color: {WHITE_OFF};
}}
.search-e text {{ background-color: transparent; }}
.search-e:focus {{ border-color: {WHITE_OFF}; }}

/* ── Process action buttons ──────────────────────────────────────────── */
.kill-btn {{
    background-color: rgba(255,50,30,0.18); color: #ff6655;
    border: 2px solid rgba(255,80,50,0.45); border-radius: 4px;
    padding: 5px 12px; font-size: 14px; font-weight: bold;
}}
.kill-btn:hover {{ background-color: rgba(255,80,50,0.32); }}
.sort-btn {{
    background-color: rgba(255,255,255,0.06); color: rgba(200,180,240,0.80);
    border: 1px solid rgba(255,255,255,0.12); border-radius: 4px;
    padding: 4px 10px; font-size: 13px;
}}
.sort-btn:hover {{ background-color: rgba(255,255,255,0.12); }}
.sort-active {{
    color: #ffff88; border-color: rgba(255,255,0,0.50);
    background-color: rgba(255,255,0,0.10);
}}

/* ── Process treeview ────────────────────────────────────────────────── */
treeview {{
    background-color: #0a0a14; color: rgba(230,220,245,0.88);
    font-size: 14px; font-family: 'Caveat', 'Sans';
}}
treeview:selected {{
    background-color: rgba(255,0,255,0.18); color: #ffaaff;
}}
treeview header button {{
    background-color: {INK_BLACK}; color: rgba(180,160,220,0.80);
    border: none; font-size: 13px; font-weight: bold;
    border-bottom: 2px solid rgba(255,0,255,0.18);
}}
""")

COLOR_NAMES = {
    C_PINK:"pink", C_ORANGE:"orange", C_PURPLE:"purple",
    C_BLUE:"blue", C_GREEN:"green", C_YELLOW:"yellow"
}


class NyxusSysmonGtk(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.sysmon",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.st=State(); self._anim_t=0.0; self._cur_page="OVERVIEW"
        self._proc_sort="cpu"; self._proc_filter=""; self._proc_sel_pid=None
        psutil.cpu_percent(interval=0.1); psutil.cpu_percent(percpu=True,interval=None)

    def do_activate(self):
        try:
            self._do_activate_inner()
        except Exception:
            log="/tmp/nyxus-sysmon.log"
            with open(log,"a") as f:
                f.write("do_activate crash:\n")
                traceback.print_exc(file=f)
            print(f"NYXUS SysMon do_activate crashed — see {log}")

    def _do_activate_inner(self):
        prov=Gtk.CssProvider()
        try: prov.load_from_string(CSS)
        except Exception:
            try: prov.load_from_data(CSS.encode())
            except Exception: pass
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),prov,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.win=Gtk.ApplicationWindow(application=self,title="NYXUS SysMon")
        self.win.set_default_size(1280,800)

        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)
        try: _nyx_install_chrome(self.win, page_key="_sysmon")
        except Exception: pass

        # Header
        self._hdr_da=self._da(self._draw_hdr,-1,46)
        root.append(self._hdr_da)

        body=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_vexpand(True); root.append(body)

        # Nav sidebar
        body.append(self._build_nav())

        # Page stack
        self._stack=Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(120)
        self._stack.set_hexpand(True); self._stack.set_vexpand(True)
        body.append(self._stack)

        # Build all pages
        self._das = {}  # DrawingAreas to queue_draw on update
        self._stack.add_named(self._build_overview(),  "OVERVIEW")
        self._stack.add_named(self._build_cpu(),       "CPU")
        self._stack.add_named(self._build_memory(),    "MEMORY")
        self._stack.add_named(self._build_network(),   "NETWORK")
        self._stack.add_named(self._build_disk(),      "DISK")
        self._stack.add_named(self._build_processes(), "PROCESSES")
        self._stack.add_named(self._build_sensors(),   "SENSORS")
        self._stack.add_named(self._build_system(),    "SYSTEM")

        self._stack.set_visible_child_name("OVERVIEW")

        GLib.timeout_add(50,  self._anim_tick)
        GLib.timeout_add(1000,self._data_tick)
        GLib.timeout_add(1000,self._clock_tick)
        self._data_tick()
        self.win.present()

    # ── Header ─────────────────────────────────────────────────────────────────
    def _draw_hdr(self,area,cr,w,h,_):
        draw_nyxus_bg(cr, w, h)
        # Subtle bottom border in warm ink
        cr.set_source_rgba(0.50,0.40,0.10,0.22); cr.set_line_width(1.5)
        cr.move_to(0,h-1); cr.line_to(w,h-1); cr.stroke()
        glow_text(cr,14,h-10,"NYXUS  SysMon",*C_PINK[:3],size=16,bold=True)
        cr.select_font_face("Caveat",0,0); cr.set_font_size(13)
        items=[
            (f"  {self.st.hostname}", C_DIM),
            (f"  ·  up {self.st.uptime}", C_DIM),
            (f"  ·  {self.st.proc_count} procs", C_GREEN),
        ]
        xp=200
        for txt,col in items:
            cr.set_source_rgba(*col,0.85); cr.move_to(xp,h-10); cr.show_text(txt)
            xp+=cr.text_extents(txt).width
        now=datetime.now()
        clk=now.strftime("%H:%M:%S")
        cr.select_font_face("Caveat",0,1)
        ext=cr.text_extents(clk)
        glow_text(cr,w-ext.width-16,h-8,clk,*C_ORANGE[:3],size=15,bold=True)
        pulse=0.5+0.5*math.sin(self._anim_t*3)
        cr.set_source_rgba(*C_GREEN,pulse); cr.arc(w-ext.width-36,h//2,5,0,math.pi*2); cr.fill()
        rainbow_bar(cr,0,h-3,w,3)

    # ── Nav sidebar ─────────────────────────────────────────────────────────────
    def _build_nav(self):
        outer=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.add_css_class("nav-bar")
        outer.set_vexpand(True)
        # Spacer above — pushes buttons to center
        top_spacer=Gtk.Box(); top_spacer.set_vexpand(True)
        outer.append(top_spacer)
        # Buttons
        self._nav_btns={}
        for name,color in PAGES:
            btn=Gtk.Button(label=name)
            btn.add_css_class("nav-btn")
            btn.connect("clicked",lambda *_,n=name:self._nav(n))
            outer.append(btn); self._nav_btns[name]=btn
        # Spacer below — mirrors top
        bot_spacer=Gtk.Box(); bot_spacer.set_vexpand(True)
        outer.append(bot_spacer)
        self._nav_update()
        return outer

    def _nav(self,name):
        self._cur_page=name
        self._stack.set_visible_child_name(name)
        self._nav_update()

    def _nav_update(self):
        page_color_class={
            "OVERVIEW":"pink","CPU":"orange","MEMORY":"purple",
            "NETWORK":"blue","DISK":"green","PROCESSES":"yellow",
            "SENSORS":"orange","SYSTEM":"pink",
        }
        for n,btn in self._nav_btns.items():
            for cls in ["nav-active-pink","nav-active-orange","nav-active-purple",
                        "nav-active-blue","nav-active-green","nav-active-yellow"]:
                btn.remove_css_class(cls)
            if n==self._cur_page:
                btn.add_css_class(f"nav-active-{page_color_class[n]}")

    # ── Overview ────────────────────────────────────────────────────────────────
    def _build_overview(self):
        da=self._da(self._draw_overview,-1,-1)
        da.set_hexpand(True); da.set_vexpand(True)
        self._das["OVERVIEW"]=da; return da

    def _draw_overview(self,area,cr,w,h,_):
        draw_nyxus_bg(cr, w, h)
        dot_grid(cr,0,0,w,h)
        p=4; cw=(w-p*5)//4; ch=160
        cards=[("CPU USAGE",self.st.cpu_pct,C_PINK),
               ("MEMORY",self.st.ram_pct,C_PURPLE),
               ("NETWORK ↑",self.st.net_up/(1024*1024)*100 if self.st.net_up<100*1024*1024 else 99,C_BLUE),
               ("DISK USAGE",self.st.disks[0]["pct"] if self.st.disks else 0,C_GREEN)]
        tilts = [-4.5, 3.0, -3.0, 4.5]
        for i,(title,pct,color) in enumerate(cards):
            x=p+i*(cw+p); y=p
            cx2=x+cw//2; cy2=y+ch//2
            angle=tilts[i]
            # Draw entire card (bg + borders + content) in tilted space
            cr.save()
            cr.translate(cx2,cy2); cr.rotate(math.radians(angle)); cr.translate(-cx2,-cy2)
            neon_card(cr,x,y,cw,ch,color)
            draw_tilt_badge(cr,x+14,y+22,title,color,angle=0,size=9)
            R=min(cw,ch)//2-26
            ring_chart(cr,cx2,cy2+8,R,pct,pct_color(pct))
            txt=f"{pct:.0f}%"
            cr.select_font_face("Caveat",0,1); cr.set_font_size(18)
            ext=cr.text_extents(txt)
            glow_text(cr,cx2-ext.width/2-ext.x_bearing,cy2+18,
                      txt,*pct_color(pct),size=18,bold=True)
            cr.set_font_size(11); cr.select_font_face("Caveat",0,0)
            cr.set_source_rgba(*C_DIM,0.8)
            if title=="CPU USAGE":
                sub=f"FREQ: {self.st.cpu_freq/1000:.2f}GHz" if self.st.cpu_freq else "FREQ: --"
                cr.move_to(x+8,y+ch-18); cr.show_text(sub)
                sub2=f"LOAD: {self.st.cpu_load[0]:.1f}"
                cr.move_to(x+8,y+ch-7); cr.show_text(sub2)
            elif title=="MEMORY":
                cr.move_to(x+8,y+ch-18); cr.show_text(f"{fmt_size(self.st.ram_used)} / {fmt_size(self.st.ram_total)}")
                cr.move_to(x+8,y+ch-7); cr.show_text(f"AVAIL: {fmt_size(self.st.ram_avail)}")
            elif title=="NETWORK ↑":
                glow_text(cr,x+8,y+ch-20,f"↑{fmt_bytes(self.st.net_up)}",*C_ORANGE,size=9,bold=True)
                glow_text(cr,x+8,y+ch-8, f"↓{fmt_bytes(self.st.net_dn)}",*C_BLUE,  size=9,bold=True)
            elif title=="DISK USAGE" and self.st.disks:
                cr.move_to(x+8,y+ch-18); cr.show_text(f"FREE: {fmt_size(self.st.disks[0]['free'])}")
                cr.move_to(x+8,y+ch-7); cr.show_text(self.st.disks[0]['mount'])
            cr.restore()

        # 3 charts
        ch2=int((h-ch-p*4)//3); cy_off=ch+p*2
        charts=[("CPU HISTORY (2 MIN)",self.st.cpu_h,C_PINK,100.0),
                ("RAM HISTORY (2 MIN)",self.st.ram_h,C_PURPLE,100.0),
                ("NETWORK (2 MIN)",None,None,None)]
        for i,(title,hist,color,mx) in enumerate(charts):
            y=cy_off+i*(ch2+p)
            neon_card(cr,p,y,w-p*2,ch2,color or C_BLUE)
            draw_tilt_badge(cr,p+14,y+22,title,color or C_BLUE,angle=-3.5)
            if hist is not None:
                sparkline(cr,p+8,y+28,w-p*2-16,ch2-36,hist,color,mx)
                val=f"{list(hist)[-1]:.1f}%" if hist else "--"
                cr.select_font_face("Caveat",0,1); cr.set_font_size(13)
                cr.set_source_rgba(*color,0.9)
                cr.move_to(w-p*2-60,y+18); cr.show_text(val)
            else:
                all_v=list(self.st.up_h)+list(self.st.dn_h)
                mv=max(all_v) if any(v>0 for v in all_v) else 1.0
                sparkline(cr,p+8,y+28,w-p*2-16,ch2-36,self.st.up_h,C_ORANGE,mv,grid=False)
                sparkline(cr,p+8,y+28,w-p*2-16,ch2-36,self.st.dn_h,C_BLUE,mv,grid=False)
                glow_text(cr,w-p*2-120,y+18,f"↑{fmt_bytes(self.st.net_up)}",*C_ORANGE,size=9,bold=True)
                glow_text(cr,w-p*2-60,y+18, f"↓{fmt_bytes(self.st.net_dn)}",*C_BLUE,  size=9,bold=True)
        rainbow_bar(cr,0,h-3,w,3)

    # ── CPU ─────────────────────────────────────────────────────────────────────
    def _build_cpu(self):
        da=self._da(self._draw_cpu,-1,-1); da.set_hexpand(True); da.set_vexpand(True)
        self._das["CPU"]=da; return da

    def _draw_cpu(self,area,cr,w,h,_):
        draw_nyxus_bg(cr, w, h)
        dot_grid(cr,0,0,w,h); p=8
        # Left: ring + info  Right: cores + history
        lw=min(360,w//2-p*2)
        neon_card(cr,p,p,lw,280,C_ORANGE)
        draw_tilt_badge(cr,p+14,p+26,"CPU DETAIL",C_ORANGE,angle=-4.0)
        ring_chart(cr,p+lw//2,p+120,80,self.st.cpu_pct,pct_color(self.st.cpu_pct))
        txt=f"{self.st.cpu_pct:.1f}%"
        cr.select_font_face("Caveat",0,1); cr.set_font_size(22)
        ext=cr.text_extents(txt)
        glow_text(cr,p+lw//2-ext.width/2-ext.x_bearing,p+130,txt,*pct_color(self.st.cpu_pct),size=22,bold=True)
        info=[
            ("MODEL",self.st.cpu_model[:30] if self.st.cpu_model else "--"),
            ("CORES",f"{self.st.cpu_count_p} PHYS / {self.st.cpu_count_l} LOG"),
            ("FREQ", f"{self.st.cpu_freq/1000:.3f} GHz" if self.st.cpu_freq else "--"),
            ("MAX",  f"{self.st.cpu_freq_max/1000:.3f} GHz" if self.st.cpu_freq_max else "--"),
            ("TEMP", f"{self.st.cpu_temp:.1f}°C" if self.st.cpu_temp else "N/A"),
            ("LOAD", f"{self.st.cpu_load[0]:.2f}  {self.st.cpu_load[1]:.2f}  {self.st.cpu_load[2]:.2f}"),
            ("ARCH", self.st.arch),
        ]
        iy=p+220
        for label,val in info:
            cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
            cr.set_source_rgba(*C_DIM,0.7); cr.move_to(p+12,iy); cr.show_text(f"{label}:")
            cr.set_source_rgba(*C_TEXT,0.9); cr.move_to(p+80,iy); cr.show_text(val)
            iy+=14
        # Right side: per-core bars + history
        rx=p*2+lw; rw=w-rx-p
        neon_card(cr,rx,p,rw,200,C_PINK)
        draw_tilt_badge(cr,rx+14,p+26,"PER-CORE UTILIZATION",C_PINK,angle=-4.0)
        cores=self.st.cpu_cores
        if cores:
            n=len(cores); bw=max(4,(rw-24)/n)
            for i,pct in enumerate(cores):
                x2=rx+12+i*(bw+1); col=pct_color(pct)
                cr.set_source_rgba(*C_DIM,0.12); cr.rectangle(x2,p+34,bw,140); cr.fill()
                fh=(pct/100)*140
                cr.set_source_rgba(*col,0.9); cr.rectangle(x2,p+34+140-fh,bw,fh); cr.fill()
                cr.set_source_rgba(*col,0.22); cr.set_line_width(bw+4)
                cr.move_to(x2+bw/2,p+34+140); cr.line_to(x2+bw/2,p+34+140-fh); cr.stroke()
                cr.select_font_face("Caveat",0,0); cr.set_font_size(13)
                cr.set_source_rgba(*C_DIM,0.8)
                lbl=f"{int(pct)}"; ext2=cr.text_extents(lbl)
                cr.move_to(x2+bw/2-ext2.width/2,p+188); cr.show_text(lbl)
        # History chart
        hch=min(180,h-p*4-210)
        neon_card(cr,rx,p*2+200,rw,hch,C_ORANGE)
        draw_tilt_badge(cr,rx+14,p*2+226,"CPU HISTORY (2 MIN)",C_ORANGE,angle=-3.5)
        sparkline(cr,rx+8,p*2+234,rw-16,hch-40,self.st.cpu_h,C_ORANGE,100.0)
        cr.select_font_face("Caveat",0,1); cr.set_font_size(13)
        cr.set_source_rgba(*C_ORANGE,0.9); cr.move_to(rx+rw-70,p*2+222)
        cr.show_text(f"{self.st.cpu_pct:.1f}%")
        rainbow_bar(cr,0,h-3,w,3)

    # ── Memory ──────────────────────────────────────────────────────────────────
    def _build_memory(self):
        da=self._da(self._draw_memory,-1,-1); da.set_hexpand(True); da.set_vexpand(True)
        self._das["MEMORY"]=da; return da

    def _draw_memory(self,area,cr,w,h,_):
        draw_nyxus_bg(cr, w, h)
        dot_grid(cr,0,0,w,h); p=8
        hw=(w-p*3)//2
        # RAM card
        neon_card(cr,p,p,hw,200,C_PURPLE)
        draw_tilt_badge(cr,p+14,p+26,"RAM (PHYSICAL)",C_PURPLE,angle=-4.0)
        glow_text(cr,p+12,p+70,f"{self.st.ram_pct:.1f}%",*C_PURPLE,size=44,bold=True)
        hbar(cr,p+12,p+90,hw-24,12,self.st.ram_pct,C_PURPLE)
        info=[("USED",fmt_size(self.st.ram_used)),("FREE",fmt_size(self.st.ram_avail)),
              ("TOTAL",fmt_size(self.st.ram_total)),("CACHED",fmt_size(self.st.ram_cached))]
        iy=p+115
        for lbl,val in info:
            col=[C_PURPLE,C_GREEN,C_DIM,C_BLUE][info.index((lbl,val))]
            cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
            cr.set_source_rgba(*C_DIM,0.7); cr.move_to(p+12,iy); cr.show_text(f"{lbl}:")
            glow_text(cr,p+80,iy,val,*col,size=9,bold=False)
            iy+=16
        # Swap card
        neon_card(cr,p*2+hw,p,hw,200,C_BLUE)
        draw_tilt_badge(cr,p*2+hw+14,p+26,"SWAP",C_BLUE,angle=-4.0)
        glow_text(cr,p*2+hw+12,p+70,f"{self.st.swp_pct:.1f}%",*C_BLUE,size=44,bold=True)
        hbar(cr,p*2+hw+12,p+90,hw-24,12,self.st.swp_pct,C_BLUE)
        swinfo=[("USED",fmt_size(self.st.swp_used)),("FREE",fmt_size(max(0,self.st.swp_total-self.st.swp_used))),
                ("TOTAL",fmt_size(self.st.swp_total))]
        iy2=p+115
        for lbl,val in swinfo:
            cr.set_font_size(12); cr.set_source_rgba(*C_DIM,0.7)
            cr.move_to(p*2+hw+12,iy2); cr.show_text(f"{lbl}:")
            cr.set_source_rgba(*C_TEXT,0.9); cr.move_to(p*2+hw+80,iy2); cr.show_text(val)
            iy2+=16
        # RAM history chart
        neon_card(cr,p,p*2+200,w-p*2,200,C_PURPLE)
        draw_tilt_badge(cr,p+14,p*2+226,"RAM USAGE HISTORY (2 MIN)",C_PURPLE,angle=-3.5)
        sparkline(cr,p+8,p*2+236,w-p*2-16,160,self.st.ram_h,C_PURPLE,100.0)
        # Top memory processes
        neon_card(cr,p,p*3+400,w-p*2,h-p*4-400,C_PURPLE)
        draw_tilt_badge(cr,p+14,p*3+426,"TOP MEMORY CONSUMERS",C_PURPLE,angle=-4.0)
        iy3=p*3+442; bh=h-p*4-400-30
        top_mem=sorted(self.st.procs,key=lambda x:x[5],reverse=True)[:int(bh//14)]
        for pid,name,cpu,mem,status,rss,user in top_mem:
            if iy3>h-p: break
            cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
            col=C_ORANGE if mem>5 else (C_YELLOW if mem>2 else C_TEXT)
            cr.set_source_rgba(*col,0.85); cr.move_to(p+12,iy3); cr.show_text(f"{name:<28}")
            glow_text(cr,p+240,iy3,f"{mem:.2f}%",*col,size=9); cr.set_source_rgba(*C_DIM,0.7)
            cr.move_to(p+310,iy3); cr.show_text(fmt_size(rss))
            iy3+=14
        rainbow_bar(cr,0,h-3,w,3)

    # ── Network ─────────────────────────────────────────────────────────────────
    def _build_network(self):
        da=self._da(self._draw_network,-1,-1); da.set_hexpand(True); da.set_vexpand(True)
        self._das["NETWORK"]=da; return da

    def _draw_network(self,area,cr,w,h,_):
        draw_nyxus_bg(cr, w, h)
        dot_grid(cr,0,0,w,h); p=8
        # Top: total speeds
        neon_card(cr,p,p,w//2-p-4,110,C_ORANGE)
        draw_tilt_badge(cr,p+14,p+26,"UPLOAD",C_ORANGE,angle=-4.0)
        glow_text(cr,p+12,p+75,fmt_bytes(self.st.net_up),*C_ORANGE,size=22,bold=True)
        dim_text(cr,p+12,p+95,f"TOTAL: {fmt_size(self.st.net_total_sent)}")

        neon_card(cr,w//2+p,p,w//2-p-8,110,C_BLUE)
        draw_tilt_badge(cr,w//2+p+14,p+26,"DOWNLOAD",C_BLUE,angle=-4.0)
        glow_text(cr,w//2+p+12,p+75,fmt_bytes(self.st.net_dn),*C_BLUE,size=22,bold=True)
        dim_text(cr,w//2+p+12,p+95,f"TOTAL: {fmt_size(self.st.net_total_recv)}")

        # Per-NIC cards
        nifaces=list(self.st.net_ifaces.items())
        if nifaces:
            nw=min(260,(w-p*(len(nifaces)+1))//len(nifaces))
            for i,(nic,data) in enumerate(nifaces[:5]):
                nx=p+i*(nw+p)
            # Actually draw them in a row
            row_y=p*2+110; total_nw=(w-p*2)//max(1,len(nifaces[:4]))
            for i,(nic,data) in enumerate(nifaces[:4]):
                nx=p+i*total_nw; nw2=total_nw-p
                neon_card(cr,nx,row_y,nw2,120,PALETTE[i%len(PALETTE)])
                col=PALETTE[i%len(PALETTE)]
                glow_text(cr,nx+10,row_y+22,nic.upper(),*col,size=9,bold=True)
                cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
                glow_text(cr,nx+10,row_y+50,fmt_bytes(data["up"]),*C_ORANGE,size=10,bold=True)
                glow_text(cr,nx+10,row_y+66,fmt_bytes(data["dn"]),*C_BLUE,  size=10,bold=True)
                cr.set_source_rgba(*C_DIM,0.7); cr.set_font_size(11)
                cr.move_to(nx+10,row_y+82); cr.show_text(f"IP: {data['ip'] or 'N/A'}")
                cr.move_to(nx+10,row_y+94); cr.show_text(f"MAC: {data['mac'] or 'N/A'}")
                cr.move_to(nx+10,row_y+106); cr.show_text(f"↑{fmt_size(data['total_sent'])} ↓{fmt_size(data['total_recv'])}")

        # History chart
        hcy=p*3+230
        neon_card(cr,p,hcy,w-p*2,160,C_BLUE)
        draw_tilt_badge(cr,p+14,hcy+24,"THROUGHPUT HISTORY (2 MIN)",C_BLUE,angle=-3.5)
        all_v=list(self.st.up_h)+list(self.st.dn_h); mv=max(all_v) if any(v>0 for v in all_v) else 1.0
        sparkline(cr,p+8,hcy+32,w-p*2-16,116,self.st.up_h,C_ORANGE,mv,grid=False)
        sparkline(cr,p+8,hcy+32,w-p*2-16,116,self.st.dn_h,C_BLUE,mv,grid=False)
        glow_text(cr,p+10,hcy+158,f"↑ UPLOAD",*C_ORANGE,size=8)
        glow_text(cr,p+100,hcy+158,f"↓ DOWNLOAD",*C_BLUE,size=8)

        # Connection states — fill remaining height down to bottom
        if self.st.net_conns_by_state:
            cs_y = hcy + 168
            cs_h = max(80, h - cs_y - p)
            neon_card(cr,p,cs_y,w-p*2,cs_h,C_GREEN)
            draw_tilt_badge(cr,p+14,hcy+192,"CONNECTION STATES",C_GREEN,angle=-4.0)
            xc=p+12; yc=hcy+208
            for j,(state,count) in enumerate(sorted(self.st.net_conns_by_state.items(),key=lambda x:-x[1])[:8]):
                col=C_GREEN if state=="ESTABLISHED" else (C_YELLOW if state=="TIME_WAIT" else C_DIM)
                cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
                cr.set_source_rgba(*col,0.85); cr.move_to(xc,yc); cr.show_text(f"{state}: {count}")
                xc+=180
                if (j+1)%3==0: xc=p+12; yc+=14
        rainbow_bar(cr,0,h-3,w,3)

    # ── Disk ────────────────────────────────────────────────────────────────────
    def _build_disk(self):
        da=self._da(self._draw_disk,-1,-1); da.set_hexpand(True); da.set_vexpand(True)
        self._das["DISK"]=da; return da

    def _draw_disk(self,area,cr,w,h,_):
        draw_nyxus_bg(cr, w, h)
        dot_grid(cr,0,0,w,h); p=8
        # Auto-fit: partitions card 55% of height, I/O card 45% — fill window
        part_h = int((h - p*3) * 0.55)
        io_h   = (h - p*3) - part_h
        neon_card(cr,p,p,w-p*2,part_h,C_GREEN)
        draw_tilt_badge(cr,p+14,p+26,"DISK PARTITIONS",C_GREEN,angle=-4.0)
        iy=p+44
        for i,d in enumerate(self.st.disks[:8]):
            if iy > p + part_h - 32: break
            col=C_ORANGE if d["pct"]>85 else (C_YELLOW if d["pct"]>70 else C_GREEN)
            glow_text(cr,p+12,iy,d["mount"],*col,size=10,bold=True)
            cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
            cr.set_source_rgba(*C_DIM,0.75); cr.move_to(p+170,iy); cr.show_text(f"[{d['fstype']}]  {d['dev']}")
            cr.set_source_rgba(*col,0.9); cr.move_to(w-p-80,iy); cr.show_text(f"{d['pct']:.1f}%")
            hbar(cr,p+12,iy+4,w-p*2-24,8,d["pct"],col)
            cr.select_font_face("Caveat",0,0); cr.set_font_size(11); cr.set_source_rgba(*C_DIM,0.7)
            cr.move_to(p+12,iy+20); cr.show_text(f"USED: {fmt_size(d['used'])}  FREE: {fmt_size(d['free'])}  TOTAL: {fmt_size(d['total'])}")
            iy+=38
        # Disk I/O — fills bottom half down to window edge
        if self.st.disk_io:
            io_y = p*2 + part_h
            neon_card(cr,p,io_y,w-p*2,io_h,C_YELLOW)
            draw_tilt_badge(cr,p+14,io_y+26,"DISK I/O RATES",C_YELLOW,angle=-4.0)
            iy2=io_y+44
            for dev,(iod) in list(self.st.disk_io.items())[:6]:
                if iy2 > io_y + io_h - 12: break
                glow_text(cr,p+12,iy2,dev,*C_YELLOW,size=9,bold=True)
                glow_text(cr,p+120,iy2,f"R: {fmt_bytes(iod['read_bps'],'')}/s",*C_GREEN,size=9)
                glow_text(cr,p+260,iy2,f"W: {fmt_bytes(iod['write_bps'],'')}/s",*C_ORANGE,size=9)
                cr.select_font_face("Caveat",0,0); cr.set_font_size(11); cr.set_source_rgba(*C_DIM,0.6)
                cr.move_to(p+400,iy2); cr.show_text(f"Reads:{iod['reads']}  Writes:{iod['writes']}")
                iy2+=16
        rainbow_bar(cr,0,h-3,w,3)

    # ── Processes ───────────────────────────────────────────────────────────────
    def _build_processes(self):
        box=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=0)
        # Toolbar
        tb=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        tb.set_margin_top(8); tb.set_margin_start(8); tb.set_margin_end(8); tb.set_margin_bottom(4)
        self._proc_search=Gtk.Entry(); self._proc_search.add_css_class("search-e")
        self._proc_search.set_placeholder_text("FILTER BY NAME OR PID...")
        self._proc_search.set_hexpand(True)
        self._proc_search.connect("changed",self._on_proc_filter)
        tb.append(self._proc_search)
        for lbl,key in [("CPU","cpu"),("MEM","mem"),("PID","pid"),("NAME","name")]:
            b=Gtk.Button(label=f"SORT: {lbl}"); b.add_css_class("sort-btn")
            if key==self._proc_sort: b.add_css_class("sort-active")
            b.connect("clicked",lambda *_,k=key:self._proc_sort_set(k,b))
            tb.append(b)
        kill=Gtk.Button(label="KILL SELECTED"); kill.add_css_class("kill-btn")
        kill.connect("clicked",self._proc_kill); tb.append(kill)
        box.append(tb)
        # TreeView
        self._proc_store=Gtk.ListStore(int,str,str,str,str,str)
        tv=Gtk.TreeView(model=self._proc_store); tv.set_vexpand(True)
        for title,col,w2 in [("PID",0,70),("NAME",1,280),("CPU%",2,80),("MEM%",3,80),("STATUS",4,90),("USER",5,100)]:
            r=Gtk.CellRendererText(); c=Gtk.TreeViewColumn(title,r,text=col)
            c.set_fixed_width(w2); c.set_resizable(True); tv.append_column(c)
        self._proc_tv=tv; self._proc_sel=tv.get_selection()
        sc=Gtk.ScrolledWindow(); sc.set_vexpand(True)
        sc.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.AUTOMATIC); sc.set_child(tv)
        box.append(sc)
        self._proc_da_header=self._da(self._draw_proc_header,-1,28)
        box.append(self._proc_da_header)
        return box

    def _draw_proc_header(self,area,cr,w,h,_):
        draw_nyxus_bg(cr, w, h)
        rainbow_bar(cr,0,0,w,2)
        info=f"PROCS: {self.st.proc_count}  RUNNING: {self.st.proc_run}  CPU: {self.st.cpu_pct:.1f}%  RAM: {self.st.ram_pct:.1f}%"
        cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
        cr.set_source_rgba(*C_DIM,0.85); cr.move_to(10,h-6); cr.show_text(info)

    def _on_proc_filter(self,entry):
        self._proc_filter=entry.get_text().lower(); self._refresh_proc_list()

    def _proc_sort_set(self,key,btn):
        self._proc_sort=key; self._refresh_proc_list()

    def _refresh_proc_list(self):
        q=self._proc_filter; sort=self._proc_sort
        procs=self.st.procs
        if q:
            procs=[p for p in procs if q in p[1].lower() or q in str(p[0])]
        if sort=="cpu":   procs=sorted(procs,key=lambda x:x[2],reverse=True)
        elif sort=="mem": procs=sorted(procs,key=lambda x:x[3],reverse=True)
        elif sort=="pid": procs=sorted(procs,key=lambda x:x[0])
        elif sort=="name":procs=sorted(procs,key=lambda x:x[1].lower())
        self._proc_store.clear()
        for pid,name,cpu,mem,status,rss,user in procs[:80]:
            self._proc_store.append([pid,name,f"{cpu:.1f}",f"{mem:.2f}",status,user])
        if hasattr(self,'_proc_da_header'): self._proc_da_header.queue_draw()

    def _proc_kill(self,btn):
        model,it=self._proc_sel.get_selected()
        if not it: return
        pid=model[it][0]
        dlg=Gtk.MessageDialog(transient_for=self.win,modal=True,
            message_type=Gtk.MessageType.WARNING,buttons=Gtk.ButtonsType.YES_NO,
            text=f"Kill PID {pid}?")
        dlg.format_secondary_text(f"Process: {model[it][1]}\nThis sends SIGTERM.")
        dlg.connect("response",lambda d,r,p=pid:(os.kill(p,signal.SIGTERM) if r==Gtk.ResponseType.YES and self._proc_killable(p) else None,d.destroy()))
        dlg.present()

    def _proc_killable(self,pid):
        try: os.kill(pid,0); return True
        except Exception: return False

    # ── Sensors ─────────────────────────────────────────────────────────────────
    def _build_sensors(self):
        da=self._da(self._draw_sensors,-1,-1); da.set_hexpand(True); da.set_vexpand(True)
        self._das["SENSORS"]=da; return da

    def _draw_sensors(self,area,cr,w,h,_):
        draw_nyxus_bg(cr, w, h)
        dot_grid(cr,0,0,w,h); p=8
        hw=(w-p*3)//2
        full_h = h - p*2
        # Left column: temperature sensors fills full height
        neon_card(cr,p,p,hw,full_h,C_ORANGE)
        draw_tilt_badge(cr,p+14,p+26,"TEMPERATURE SENSORS",C_ORANGE,angle=-4.0)
        iy=p+42
        if self.st.temps:
            for chip,readings in self.st.temps.items():
                if iy > p + full_h - 24: break
                glow_text(cr,p+12,iy,chip.upper(),*C_YELLOW,size=9,bold=True); iy+=14
                for r in readings[:8]:
                    if iy > p + full_h - 14: break
                    tc=temp_color(r.current); lbl=r.label or f"Sensor"
                    cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
                    cr.set_source_rgba(*C_DIM,0.7); cr.move_to(p+20,iy); cr.show_text(f"  {lbl[:20]}")
                    glow_text(cr,p+180,iy,f"{r.current:.1f}°C",*tc,size=9,bold=True)
                    if hasattr(r,'high') and r.high: cr.set_source_rgba(*C_DIM,0.5); cr.set_font_size(11); cr.move_to(p+240,iy); cr.show_text(f"(max {r.high:.0f}°C)")
                    iy+=13
        else:
            cr.select_font_face("Caveat",0,0); cr.set_font_size(13)
            cr.set_source_rgba(*C_DIM,0.5); cr.move_to(p+12,iy+30); cr.show_text("NO SENSORS DETECTED")
        # Right column: battery / gpu / fans split full height equally
        bw=hw; bx=p*2+hw
        right_h = (full_h - p*2) // 3
        # Battery
        by1 = p
        neon_card(cr,bx,by1,bw,right_h,C_GREEN)
        draw_tilt_badge(cr,bx+14,by1+26,"BATTERY",C_GREEN,angle=-4.0)
        if self.st.battery:
            b=self.st.battery; pct=b["pct"]
            col=C_GREEN if pct>40 else (C_YELLOW if pct>20 else C_ORANGE)
            glow_text(cr,bx+12,by1+right_h//2+8,f"{pct:.1f}%",*col,size=36,bold=True)
            status="⚡ CHARGING" if b["charging"] else "🔋 DISCHARGING"
            cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
            cr.set_source_rgba(*col,0.85); cr.move_to(bx+12,by1+right_h//2+30)
            cr.show_text(status)
            if b["secs_left"]:
                cr.set_source_rgba(*C_DIM,0.7); cr.move_to(bx+12,by1+right_h-12)
                cr.show_text(f"REMAINING: {fmt_uptime(b['secs_left'])}")
        else:
            cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
            cr.set_source_rgba(*C_DIM,0.5); cr.move_to(bx+12,by1+right_h//2); cr.show_text("NO BATTERY DETECTED")
        # GPU
        by2 = by1 + right_h + p
        neon_card(cr,bx,by2,bw,right_h,C_BLUE)
        draw_tilt_badge(cr,bx+14,by2+26,"GPU (NVIDIA)",C_BLUE,angle=-4.0)
        if self.st.gpu_util is not None:
            glow_text(cr,bx+12,by2+right_h//2+8,f"{self.st.gpu_util:.0f}%",*C_BLUE,size=32,bold=True)
            ring_chart(cr,bx+bw-60,by2+right_h//2+8,35,self.st.gpu_util,C_BLUE)
            cr.select_font_face("Caveat",0,0); cr.set_font_size(12); cr.set_source_rgba(*C_DIM,0.7)
            cr.move_to(bx+12,by2+right_h-26); cr.show_text(f"VRAM: {self.st.gpu_mem_used}MB / {self.st.gpu_mem_total}MB")
            cr.move_to(bx+12,by2+right_h-12); cr.show_text(f"TEMP: {self.st.gpu_temp:.0f}°C")
        else:
            cr.set_font_size(12); cr.set_source_rgba(*C_DIM,0.5)
            cr.move_to(bx+12,by2+right_h//2);     cr.show_text("nvidia-smi NOT AVAILABLE")
            cr.move_to(bx+12,by2+right_h//2+15); cr.show_text("or no NVIDIA GPU found")
        # Fans
        by3 = by2 + right_h + p
        fan_h = h - by3 - p
        neon_card(cr,bx,by3,bw,fan_h,C_PURPLE)
        draw_tilt_badge(cr,bx+14,by3+26,"FANS",C_PURPLE,angle=-4.0)
        if self.st.fans:
            ffy=by3+44
            for chip,readings in self.st.fans.items():
                for r in readings:
                    if ffy > by3 + fan_h - 8: break
                    cr.set_font_size(12); cr.set_source_rgba(*C_DIM,0.7)
                    cr.move_to(bx+12,ffy); cr.show_text(f"{r.label or chip}: ")
                    glow_text(cr,bx+140,ffy,f"{r.current} RPM",*C_PURPLE,size=9)
                    ffy+=14
        else:
            cr.set_font_size(12); cr.set_source_rgba(*C_DIM,0.5)
            cr.move_to(bx+12,by3+fan_h//2); cr.show_text("NO FAN SENSORS")
        rainbow_bar(cr,0,h-3,w,3)

    # ── System Info ─────────────────────────────────────────────────────────────
    def _build_system(self):
        da=self._da(self._draw_system,-1,-1); da.set_hexpand(True); da.set_vexpand(True)
        self._das["SYSTEM"]=da; return da

    def _draw_system(self,area,cr,w,h,_):
        draw_nyxus_bg(cr, w, h)
        dot_grid(cr,0,0,w,h); p=8
        # Big system info card — auto-fits 75% of height, LIVE STATUS gets 25%
        sys_h = int((h - p*3) * 0.75)
        neon_card(cr,p,p,w-p*2,sys_h,C_PINK)
        glow_text(cr,p+10,p+30,"SYSTEM INFORMATION",*C_PINK,size=13,bold=True)
        rainbow_bar(cr,p,p+38,w-p*2,2)
        uname=platform.uname()
        rows=[
            ("HOSTNAME",   self.st.hostname,         C_PINK),
            ("OS",         self.st.os_name,           C_PURPLE),
            ("KERNEL",     self.st.kernel,            C_BLUE),
            ("ARCHITECTURE",self.st.arch,             C_GREEN),
            ("CPU MODEL",  self.st.cpu_model,         C_ORANGE),
            ("CPU CORES",  f"{self.st.cpu_count_p} physical / {self.st.cpu_count_l} logical", C_YELLOW),
            ("RAM",        fmt_size(self.st.ram_total),C_PURPLE),
            ("SWAP",       fmt_size(self.st.swp_total),C_BLUE),
            ("UPTIME",     self.st.uptime,            C_GREEN),
            ("BOOT TIME",  self.st.boot_time,         C_DIM),
            ("PYTHON",     platform.python_version(), C_YELLOW),
            ("PROCESSOR",  uname.processor[:40] or "N/A", C_ORANGE),
            ("MACHINE",    uname.machine,             C_PINK),
        ]
        iy=p+54
        for lbl,val,col in rows:
            if iy>p+340: break
            cr.select_font_face("Caveat",0,0); cr.set_font_size(13)
            cr.set_source_rgba(*C_DIM,0.65); cr.move_to(p+16,iy); cr.show_text(f"{lbl}:")
            glow_text(cr,p+200,iy,val[:52],*col,size=10,bold=False)
            # Dim separator
            cr.set_source_rgba(*C_PURPLE,0.08); cr.set_line_width(1)
            cr.move_to(p+8,iy+4); cr.line_to(w-p*2-8,iy+4); cr.stroke()
            iy+=22
        # Live quick stats — fills bottom 25% of window
        qy = p*2 + sys_h
        qh = h - qy - p
        neon_card(cr,p,qy,w-p*2,qh,C_PINK)
        draw_tilt_badge(cr,p+14,qy+26,"LIVE STATUS",C_PINK,angle=-4.0)
        qs=[
            (f"CPU: {self.st.cpu_pct:.1f}%",   C_ORANGE),
            (f"RAM: {self.st.ram_pct:.1f}%",    C_PURPLE),
            (f"↑ {fmt_bytes(self.st.net_up)}",  C_ORANGE),
            (f"↓ {fmt_bytes(self.st.net_dn)}",  C_BLUE),
            (f"PROCS: {self.st.proc_count}",    C_GREEN),
            (f"UPTIME: {self.st.uptime}",       C_YELLOW),
        ]
        xq=p+12
        for i,(txt,col) in enumerate(qs):
            glow_text(cr,xq,qy+60,txt,*col,size=12,bold=True)
            xq+=max(140,cr.text_extents(txt).width+24)
        rainbow_bar(cr,0,h-3,w,3)

    # ── Ticks / refresh ─────────────────────────────────────────────────────────
    def _anim_tick(self):
        self._anim_t+=0.04
        self._hdr_da.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _clock_tick(self):
        self._hdr_da.queue_draw()
        if hasattr(self,'_proc_da_header'): self._proc_da_header.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _data_tick(self):
        threading.Thread(target=self._collect,daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _collect(self):
        collect(self.st); GLib.idle_add(self._refresh_ui)

    def _refresh_ui(self):
        for name,da in self._das.items():
            da.queue_draw()
        self._refresh_proc_list()
        self._hdr_da.queue_draw()
        return GLib.SOURCE_REMOVE

    def _da(self,fn,w,h):
        a=Gtk.DrawingArea(); a.set_size_request(w,h); a.set_draw_func(fn,None)
        return a


if __name__=="__main__":
    try:
        NyxusSysmonGtk().run(None)
    except Exception:
        log="/tmp/nyxus-sysmon.log"
        with open(log,"w") as f: traceback.print_exc(file=f)
        print(f"NYXUS SysMon crashed — see {log}")
        sys.exit(1)

# ── palette guard (rev r13) ─────────────────────────────────────────
try: assert_no_forbidden(CSS, __file__)
except Exception as _e: import sys; sys.stderr.write(str(_e)+chr(10))
