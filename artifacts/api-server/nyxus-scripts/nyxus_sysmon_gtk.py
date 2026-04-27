#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS SysMon GTK — Neon system monitor · dot-grid panels            ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
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
    subprocess.run(["pip","install","psutil"],check=True)
    import psutil

HIST = 60

C_BG     = (0.012, 0.008, 0.024)
C_PANEL  = (0.027, 0.012, 0.059)
C_PINK   = (1.0,   0.0,   1.0  )
C_PURPLE = (0.8,   0.0,   1.0  )
C_BLUE   = (0.0,   0.533, 1.0  )
C_GREEN  = (0.224, 1.0,   0.078)
C_YELLOW = (1.0,   1.0,   0.0  )
C_ORANGE = (1.0,   0.333, 0.0  )
C_TEXT   = (0.91,  0.88,  0.96 )
C_DIM    = (0.44,  0.376, 0.627)


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


def dot_grid(cr, w, h, spacing=22):
    cr.set_source_rgba(0.28, 0.07, 0.50, 0.10)
    for gx in range(0, w + spacing, spacing):
        for gy in range(0, h + spacing, spacing):
            cr.arc(gx, gy, 0.9, 0, math.pi * 2)
            cr.fill()


def neon_panel_bg(cr, w, h, color=C_PURPLE, tilt=0.0):
    """Draw dot-grid panel background with neon border (optionally tilted)."""
    r, g, b = color
    cr.set_source_rgb(*C_PANEL)
    cr.rectangle(0, 0, w, h); cr.fill()
    dot_grid(cr, w, h)
    # Glow border
    for lw, a in [(8, 0.12), (4, 0.25), (1.5, 0.85)]:
        cr.set_source_rgba(r, g, b, a)
        cr.set_line_width(lw)
        cr.rectangle(1, 1, w-2, h-2); cr.stroke()


def glow_text(cr, x, y, text, r, g, b, size=12, bold=False):
    cr.select_font_face("JetBrains Mono", 0, 1 if bold else 0)
    cr.set_font_size(size)
    for dx, dy, a in [(-1,-1,.20),(1,-1,.20),(-1,1,.20),(1,1,.20),
                       (-2,0,.08),(2,0,.08),(0,-2,.08),(0,2,.08)]:
        cr.set_source_rgba(r, g, b, a)
        cr.move_to(x+dx, y+dy); cr.show_text(text)
    cr.set_source_rgba(r, g, b, 1.0)
    cr.move_to(x, y); cr.show_text(text)


CSS = b"""
* { font-family: 'JetBrains Mono', 'Monospace', monospace; }
window { background-color: #030206; color: #e8e0f5; }
.hdr { background-color: rgba(7,3,15,0.97); border-bottom: 1px solid rgba(255,0,255,0.3); padding: 5px 16px; }
.proc-view { background-color: rgba(7,3,15,0.80); color: #e8e0f5; font-size: 11px; }
.proc-view text { background-color: transparent; }
"""


class State:
    def __init__(self):
        self.cpu=0.0; self.cores=[]; self.freq=None; self.load=(0,0,0)
        self.ram_pct=0.0; self.ram_used=0; self.ram_total=1
        self.swp_pct=0.0; self.swp_used=0; self.swp_total=1
        self.net_up=0.0; self.net_dn=0.0; self.net_conn=0
        self.disks=[]; self.procs=[]
        self.uptime="00:00:00"; self.hostname=socket.gethostname()
        self.cpu_h=deque([0.0]*HIST,maxlen=HIST)
        self.up_h=deque([0.0]*HIST,maxlen=HIST)
        self.dn_h=deque([0.0]*HIST,maxlen=HIST)
        self._pnet=None; self._pnet_t=None


def collect(st):
    st.cpu=psutil.cpu_percent(interval=None)
    st.cores=psutil.cpu_percent(percpu=True,interval=None)
    f=psutil.cpu_freq(); st.freq=f.current if f else None
    st.load=psutil.getloadavg()
    vm=psutil.virtual_memory(); sw=psutil.swap_memory()
    st.ram_pct=vm.percent; st.ram_used=vm.used; st.ram_total=vm.total
    st.swp_pct=sw.percent; st.swp_used=sw.used; st.swp_total=sw.total
    now=time.time(); cnt=psutil.net_io_counters()
    if st._pnet and st._pnet_t:
        dt=now-st._pnet_t
        if dt>0:
            st.net_up=max(0,(cnt.bytes_sent-st._pnet.bytes_sent)/dt)
            st.net_dn=max(0,(cnt.bytes_recv-st._pnet.bytes_recv)/dt)
    st._pnet=cnt; st._pnet_t=now
    try: st.net_conn=len([c for c in psutil.net_connections("inet") if c.status=="ESTABLISHED"])
    except Exception: st.net_conn=0
    st.disks=[]
    for p in psutil.disk_partitions():
        if p.fstype in ("tmpfs","devtmpfs","squashfs","overlay",""): continue
        try:
            u=psutil.disk_usage(p.mountpoint)
            st.disks.append({"dev":p.device.split("/")[-1],"mount":p.mountpoint,
                              "pct":u.percent,"free":u.free,"total":u.total})
        except Exception: pass
    procs=[]
    for p in psutil.process_iter(["pid","name","cpu_percent","memory_percent","status"]):
        try:
            i=p.info
            procs.append((i["pid"],(i["name"] or "")[:28],
                           round(i["cpu_percent"] or 0,1),
                           round(i["memory_percent"] or 0,2),
                           i["status"] or ""))
        except Exception: pass
    st.procs=sorted(procs,key=lambda x:x[2],reverse=True)[:25]
    up=int(time.time()-psutil.boot_time()); h,r=divmod(up,3600); m,s=divmod(r,60)
    st.uptime=f"{h:02d}:{m:02d}:{s:02d}"
    st.cpu_h.append(st.cpu); st.up_h.append(st.net_up); st.dn_h.append(st.net_dn)


class NyxusSysmonGtk(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.sysmon")
        self.st=State(); self._anim_t=0.0
        psutil.cpu_percent(interval=0.1)
        psutil.cpu_percent(percpu=True,interval=None)

    def do_activate(self):
        prov=Gtk.CssProvider(); prov.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),prov,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.win=Gtk.ApplicationWindow(application=self,title="NYXUS SysMon")
        self.win.set_default_size(1280,720)
        self.win.fullscreen()

        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)
        root.append(self._build_hdr())

        # Top row: 4 stat panels (cairo DrawingArea each)
        top=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=2)
        top.set_margin_top(2); top.set_margin_start(2); top.set_margin_end(2)
        top.set_homogeneous(True)
        self._cpu_da  = self._da(self._draw_cpu_card,  -1, 180)
        self._mem_da  = self._da(self._draw_mem_card,  -1, 180)
        self._net_da  = self._da(self._draw_net_card,  -1, 180)
        self._disk_da = self._da(self._draw_disk_card, -1, 180)
        for da in [self._cpu_da,self._mem_da,self._net_da,self._disk_da]:
            top.append(da)
        root.append(top)

        # Core bars
        self._core_da=self._da(self._draw_cores,-1,72)
        cg=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        cg.set_margin_top(2); cg.set_margin_start(2); cg.set_margin_end(2)
        cg.append(self._core_da)
        root.append(cg)

        # Bottom: charts + processes
        bot=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=2)
        bot.set_vexpand(True); bot.set_margin_top(2)
        bot.set_margin_start(2); bot.set_margin_end(2); bot.set_margin_bottom(2)

        charts=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
        charts.set_hexpand(True)
        self._cpu_h_da=self._da(self._draw_cpu_hist,-1,-1); self._cpu_h_da.set_vexpand(True)
        self._net_h_da=self._da(self._draw_net_hist,-1,-1); self._net_h_da.set_vexpand(True)
        charts.append(self._cpu_h_da); charts.append(self._net_h_da)
        bot.append(charts)

        self._proc_da=self._da(self._draw_proc_panel,-1,-1)
        self._proc_da.set_hexpand(True)
        bot.append(self._proc_da)
        root.append(bot)

        GLib.timeout_add(50,self._anim_tick)
        GLib.timeout_add(2000,self._data_tick)
        GLib.timeout_add(1000,self._clock_tick)
        self._data_tick()
        self.win.present()

    # ── Header ─────────────────────────────────────────────────────────────────
    def _build_hdr(self):
        h=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=12)
        h.add_css_class("hdr")
        # We draw the header title in a DrawingArea for glow effect
        hdr_da=self._da(self._draw_hdr_title,280,40)
        h.append(hdr_da)
        self._host_lbl=Gtk.Label(label=self.st.hostname)
        self._host_lbl.set_margin_start(8)
        h.append(self._host_lbl)
        self._up_lbl=Gtk.Label(label="UP 00:00:00")
        h.append(self._up_lbl)
        sp=Gtk.Box(); sp.set_hexpand(True); h.append(sp)
        self._live_da=self._da(self._draw_live_badge,100,40)
        h.append(self._live_da)
        self._clk_da=self._da(self._draw_clock,120,40)
        h.append(self._clk_da)
        return h

    def _draw_hdr_title(self,area,cr,w,h,_):
        cr.set_source_rgba(0.027,0.012,0.059,0.0); cr.rectangle(0,0,w,h); cr.fill()
        glow_text(cr,4,h-10,"NYXUS_SYSMON",*C_PINK,size=15,bold=True)

    def _draw_live_badge(self,area,cr,w,h,_):
        cr.set_source_rgba(0,0,0,0); cr.rectangle(0,0,w,h); cr.fill()
        pulse=0.7+0.3*math.sin(self._anim_t*3)
        cr.set_source_rgba(*C_GREEN,pulse)
        cr.arc(16,h//2,5,0,math.pi*2); cr.fill()
        glow_text(cr,26,h//2+5,"LIVE",*C_GREEN,size=12,bold=True)

    def _draw_clock(self,area,cr,w,h,_):
        cr.set_source_rgba(0,0,0,0); cr.rectangle(0,0,w,h); cr.fill()
        now=datetime.now().strftime("%H:%M:%S")
        glow_text(cr,4,h-10,now,*C_YELLOW,size=14,bold=True)

    def _clock_tick(self):
        for da in [self._live_da,self._clk_da]: da.queue_draw()
        return GLib.SOURCE_CONTINUE

    # ── Stat cards ─────────────────────────────────────────────────────────────
    def _draw_cpu_card(self,area,cr,w,h,_):
        neon_panel_bg(cr,w,h,C_PINK)
        glow_text(cr,10,22,"CPU USAGE",*C_PINK,size=9,bold=True)
        # Ring
        cx,cy=w//2,h//2+8; R=min(w,h)//2-22
        pct=self.st.cpu; color=pct_color(pct)
        # Track
        cr.set_source_rgba(*C_DIM,0.25); cr.set_line_width(14)
        cr.arc(cx,cy,R,-math.pi/2,3*math.pi/2); cr.stroke()
        # Arc
        if pct>0:
            end=-math.pi/2+(pct/100)*2*math.pi
            cr.set_source_rgba(*color,1.0); cr.set_line_width(14)
            cr.arc(cx,cy,R,-math.pi/2,end); cr.stroke()
            cr.set_source_rgba(*color,0.20); cr.set_line_width(24)
            cr.arc(cx,cy,R,-math.pi/2,end); cr.stroke()
        # Text
        txt=f"{pct:.0f}%"
        cr.select_font_face("JetBrains Mono",0,1); cr.set_font_size(20)
        ext=cr.text_extents(txt)
        glow_text(cr,cx-ext.width/2-ext.x_bearing,cy-ext.height/2-ext.y_bearing+ext.height,
                  txt,*color,size=20,bold=True)
        # Sub-stats
        cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
        cr.set_source_rgba(*C_DIM,0.9)
        freq_txt=f"FREQ: {self.st.freq/1000:.2f} GHz" if self.st.freq else "FREQ: --"
        cr.move_to(10,h-22); cr.show_text(freq_txt)
        load=f"LOAD: {self.st.load[0]:.2f} {self.st.load[1]:.2f}"
        cr.move_to(10,h-10); cr.show_text(load)

    def _draw_mem_card(self,area,cr,w,h,_):
        neon_panel_bg(cr,w,h,C_PURPLE)
        glow_text(cr,10,22,"MEMORY",*C_PURPLE,size=9,bold=True)
        pct=self.st.ram_pct
        txt=f"{pct:.0f}%"
        cr.select_font_face("JetBrains Mono",0,1); cr.set_font_size(36)
        ext=cr.text_extents(txt)
        glow_text(cr,10,64,txt,*C_PURPLE,size=36,bold=True)
        # RAM bar
        bx,by,bw,bh=10,76,w-20,10
        cr.set_source_rgba(*C_DIM,0.15); cr.rectangle(bx,by,bw,bh); cr.fill()
        if pct>0:
            cr.set_source_rgba(*C_PURPLE,0.9); cr.rectangle(bx,by,(pct/100)*bw,bh); cr.fill()
            cr.set_source_rgba(*C_PURPLE,0.25); cr.set_line_width(bh+4)
            cr.move_to(bx,by+bh/2); cr.line_to(bx+(pct/100)*bw,by+bh/2); cr.stroke()
        cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
        cr.set_source_rgba(*C_DIM,0.85)
        cr.move_to(10,96); cr.show_text(f"RAM: {fmt_size(self.st.ram_used)} / {fmt_size(self.st.ram_total)}")
        # SWAP bar
        spct=self.st.swp_pct
        bx2,by2=10,110
        cr.set_source_rgba(*C_DIM,0.12); cr.rectangle(bx2,by2,bw,8); cr.fill()
        if spct>0:
            cr.set_source_rgba(*C_BLUE,0.7); cr.rectangle(bx2,by2,(spct/100)*bw,8); cr.fill()
        cr.move_to(10,130); cr.show_text(f"SWAP: {spct:.0f}%  {fmt_size(self.st.swp_used)}")

    def _draw_net_card(self,area,cr,w,h,_):
        neon_panel_bg(cr,w,h,C_ORANGE)
        glow_text(cr,10,22,"NETWORK",*C_ORANGE,size=9,bold=True)
        # Upload
        glow_text(cr,10,56,f"↑ {fmt_bytes(self.st.net_up)}",*C_ORANGE,size=16,bold=True)
        # Download
        glow_text(cr,10,86,f"↓ {fmt_bytes(self.st.net_dn)}",*C_BLUE,size=16,bold=True)
        cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
        cr.set_source_rgba(*C_DIM,0.85)
        cr.move_to(10,108); cr.show_text(f"ESTABLISHED: {self.st.net_conn}")
        # Tilted accent card
        cr.save(); cr.translate(w-46,h-40); cr.rotate(math.radians(-8))
        cr.set_source_rgba(*C_ORANGE,0.12); cr.rectangle(-30,-20,60,38); cr.fill()
        cr.set_source_rgba(*C_ORANGE,0.55); cr.set_line_width(1)
        cr.rectangle(-30,-20,60,38); cr.stroke()
        cr.restore()

    def _draw_disk_card(self,area,cr,w,h,_):
        neon_panel_bg(cr,w,h,C_GREEN)
        glow_text(cr,10,22,"DISK",*C_GREEN,size=9,bold=True)
        y=40
        for d in self.st.disks[:5]:
            pct=d["pct"]
            if pct>85: color=C_ORANGE
            elif pct>70: color=C_YELLOW
            else: color=C_GREEN
            cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
            cr.set_source_rgba(*C_DIM,0.85)
            lbl=f"{d['mount']}  {pct:.0f}%"
            cr.move_to(10,y); cr.show_text(lbl); y+=12
            bx,by,bw,bh=10,y,w-20,6
            cr.set_source_rgba(*C_DIM,0.12); cr.rectangle(bx,by,bw,bh); cr.fill()
            if pct>0:
                cr.set_source_rgba(*color,0.9); cr.rectangle(bx,by,(pct/100)*bw,bh); cr.fill()
                cr.set_source_rgba(*color,0.25); cr.set_line_width(bh+4)
                cr.move_to(bx,by+bh/2); cr.line_to(bx+(pct/100)*bw,by+bh/2); cr.stroke()
            cr.set_source_rgba(*C_DIM,0.6); cr.set_font_size(8)
            cr.move_to(10,y+14); cr.show_text(f"  {fmt_size(d['free'])} free")
            y+=26
            if y > h-20: break

    # ── Core bars ──────────────────────────────────────────────────────────────
    def _draw_cores(self,area,cr,w,h,_):
        neon_panel_bg(cr,w,h,C_PURPLE)
        glow_text(cr,8,18,"CPU CORES",*C_DIM,size=8,bold=True)
        cores=self.st.cores
        if not cores: return
        n=len(cores); bw=max(4,(w-(n+1)*3)/n)
        for i,pct in enumerate(cores):
            x=3+i*(bw+3)
            cr.set_source_rgba(*C_DIM,0.15)
            cr.rectangle(x,22,bw,h-32); cr.fill()
            fh=(pct/100)*(h-32)
            col=pct_color(pct)
            cr.set_source_rgba(*col,0.9)
            cr.rectangle(x,22+(h-32-fh),bw,fh); cr.fill()
            # Glow
            cr.set_source_rgba(*col,0.25); cr.set_line_width(bw+4)
            cr.move_to(x+bw/2,22+(h-32)); cr.line_to(x+bw/2,22+(h-32-fh)); cr.stroke()
            cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(7)
            cr.set_source_rgba(*C_DIM,0.8)
            lbl=f"{int(pct)}"
            ext=cr.text_extents(lbl)
            cr.move_to(x+bw/2-ext.width/2-ext.x_bearing,h-4); cr.show_text(lbl)

    # ── History charts ──────────────────────────────────────────────────────────
    def _area_chart(self,cr,w,h,hist,color,max_val=None):
        vals=list(hist)
        if not vals: return
        mv=max_val or (max(vals) if max(vals)>0 else 1.0)
        step=w/max(len(vals)-1,1)
        cr.new_path(); cr.move_to(0,h)
        for i,v in enumerate(vals): cr.line_to(i*step,h-(v/mv)*h*0.88)
        cr.line_to((len(vals)-1)*step,h); cr.close_path()
        cr.set_source_rgba(*color,0.14); cr.fill()
        cr.new_path()
        for i,v in enumerate(vals):
            x,y=i*step,h-(v/mv)*h*0.88
            if i==0: cr.move_to(x,y)
            else: cr.line_to(x,y)
        cr.set_source_rgba(*color,0.95); cr.set_line_width(1.6); cr.stroke()
        # Glow stroke
        cr.new_path()
        for i,v in enumerate(vals):
            x,y=i*step,h-(v/mv)*h*0.88
            if i==0: cr.move_to(x,y)
            else: cr.line_to(x,y)
        cr.set_source_rgba(*color,0.18); cr.set_line_width(5); cr.stroke()

    def _draw_cpu_hist(self,area,cr,w,h,_):
        neon_panel_bg(cr,w,h,C_PINK)
        glow_text(cr,10,20,"CPU HISTORY",*C_PINK,size=9,bold=True)
        self._area_chart(cr,w,h-28,self.st.cpu_h,C_PINK,100.0)
        cr.select_font_face("JetBrains Mono",0,1); cr.set_font_size(10)
        cr.set_source_rgba(*C_PINK,0.8)
        cr.move_to(w-90,20); cr.show_text(f"{self.st.cpu:.1f}%")

    def _draw_net_hist(self,area,cr,w,h,_):
        neon_panel_bg(cr,w,h,C_BLUE)
        glow_text(cr,10,20,"NETWORK THROUGHPUT",*C_BLUE,size=9,bold=True)
        all_v=list(self.st.up_h)+list(self.st.dn_h)
        mv=max(all_v) if any(v>0 for v in all_v) else 1.0
        self._area_chart(cr,w,h-28,self.st.up_h,C_ORANGE,mv)
        self._area_chart(cr,w,h-28,self.st.dn_h,C_BLUE,mv)
        cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
        cr.set_source_rgba(*C_ORANGE,0.85); cr.move_to(10,h-6)
        cr.show_text(f"↑ {fmt_bytes(self.st.net_up)}")
        cr.set_source_rgba(*C_BLUE,0.85); cr.move_to(200,h-6)
        cr.show_text(f"↓ {fmt_bytes(self.st.net_dn)}")

    # ── Process panel ──────────────────────────────────────────────────────────
    def _draw_proc_panel(self,area,cr,w,h,_):
        neon_panel_bg(cr,w,h,C_PURPLE)
        glow_text(cr,10,20,"PROCESSES",*C_PURPLE,size=9,bold=True)
        # Column headers
        cr.set_source_rgba(*C_DIM,0.5); cr.set_line_width(1)
        cr.move_to(0,28); cr.line_to(w,28); cr.stroke()
        cr.select_font_face("JetBrains Mono",0,1); cr.set_font_size(9)
        cr.set_source_rgba(*C_PURPLE,0.8)
        for lbl,x in [("PID",6),("NAME",52),("CPU%",260),("MEM%",310)]:
            cr.move_to(x,26); cr.show_text(lbl)
        # Rows
        cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
        y=40
        for pid,name,cpu,mem,status in self.st.procs[:20]:
            if y > h-10: break
            row_a=0.06 if (y//14)%2==0 else 0.0
            cr.set_source_rgba(*C_PURPLE,row_a); cr.rectangle(0,y-10,w,14); cr.fill()
            # Color code by CPU
            if cpu>50: tcol=C_ORANGE
            elif cpu>20: tcol=C_YELLOW
            else: tcol=C_TEXT
            cr.set_source_rgba(*tcol,0.85)
            cr.move_to(6,y); cr.show_text(str(pid)[:6])
            cr.move_to(52,y); cr.show_text(name[:24])
            cpu_txt=f"{cpu:.1f}"
            cr.set_source_rgba(*pct_color(cpu),0.9)
            cr.move_to(260,y); cr.show_text(cpu_txt)
            cr.set_source_rgba(*C_DIM,0.85)
            cr.move_to(310,y); cr.show_text(f"{mem:.2f}")
            y+=14

    # ── Ticks ──────────────────────────────────────────────────────────────────
    def _anim_tick(self):
        self._anim_t += 0.04
        self._live_da.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _data_tick(self):
        threading.Thread(target=self._collect,daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _collect(self):
        collect(self.st); GLib.idle_add(self._refresh_ui)

    def _refresh_ui(self):
        self._up_lbl.set_text(f"UP: {self.st.uptime}")
        for da in [self._cpu_da,self._mem_da,self._net_da,self._disk_da,
                   self._core_da,self._cpu_h_da,self._net_h_da,self._proc_da]:
            da.queue_draw()
        return GLib.SOURCE_REMOVE

    # ── Helper ─────────────────────────────────────────────────────────────────
    def _da(self,fn,w,h):
        a=Gtk.DrawingArea(); a.set_size_request(w,h); a.set_draw_func(fn,None)
        return a


if __name__ == "__main__":
    NyxusSysmonGtk().run(None)
