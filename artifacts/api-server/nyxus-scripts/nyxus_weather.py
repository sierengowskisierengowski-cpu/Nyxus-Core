#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Weather — Composition-notebook dark theme · enterprise-grade  ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝

__nyxid__ = "4e59582d4a35572d323032362d53494552454e474f57534b492d4c4f434b4544"

def _nyx_integrity():
    try:
        _s = open(__file__, encoding="utf-8").read()
        assert "SIERENGOWSKI" in _s, "NYXUS: tamper detected"
    except (OSError, AssertionError) as _e:
        import sys as _sys; print(f"NYXUS SECURITY: {_e}", file=_sys.stderr)
_nyx_integrity()


import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib, Gio
import math, random, threading, json, os
from urllib.request import urlopen, Request
from urllib.parse import quote
from datetime import datetime

CONFIG_FILE = os.path.expanduser("~/.nyxus/weather.json")
os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)

WMO = {
    0:"CLEAR",1:"PARTLY_CLOUDY",2:"PARTLY_CLOUDY",3:"CLOUDY",
    45:"FOG",48:"FOG",51:"RAIN",53:"RAIN",55:"RAIN",
    61:"RAIN",63:"RAIN",65:"RAIN",71:"SNOW",73:"SNOW",75:"SNOW",
    80:"RAIN",81:"RAIN",82:"RAIN",85:"SNOW",86:"SNOW",
    95:"STORM",96:"STORM",99:"STORM",
}
LABELS  = {"CLEAR":"Clear Skies","PARTLY_CLOUDY":"Partly Cloudy","CLOUDY":"Overcast",
           "FOG":"Foggy","RAIN":"Rainy","SNOW":"Snowy","STORM":"Thunderstorm"}
ICONS   = {"CLEAR":"☀","PARTLY_CLOUDY":"⛅","CLOUDY":"☁","RAIN":"🌧","SNOW":"❄","STORM":"⛈","FOG":"🌫"}
WIND_DIRS = ["N","NE","E","SE","S","SW","W","NW"]

# Full NYXUS palette (floats 0-1)
PALETTE = [
    (1.0, 0.0,  1.0 ),   # pink   #ff00ff
    (0.8, 0.0,  1.0 ),   # purple #cc00ff
    (0.0, 0.53, 1.0 ),   # blue   #0088ff
    (0.22,1.0,  0.08),   # green  #39ff14
    (1.0, 1.0,  0.0 ),   # yellow #ffff00
    (1.0, 0.33, 0.0 ),   # orange #ff5500
]
C_PINK   = PALETTE[0]
C_PURPLE = PALETTE[1]
C_BLUE   = PALETTE[2]
C_GREEN  = PALETTE[3]
C_YELLOW = PALETTE[4]
C_ORANGE = PALETTE[5]
C_TEXT   = (0.92, 0.88, 0.98)   # light lavender — for dark panel
C_DIM    = (0.50, 0.44, 0.68)   # dim purple-grey — for dark panel
C_DARK   = (0.031, 0.031, 0.055) # #08080e background

# ── CSS ──────────────────────────────────────────────────────────────────────
CSS = """
window {
  background-color: #08080e;
  font-family: 'Caveat', 'Patrick Hand', cursive;
}
.search-entry {
  background: rgba(255,255,255,0.06);
  border: 2px solid rgba(255,0,255,0.35);
  border-radius: 6px;
  color: rgba(255,255,255,0.88);
  font-family: 'Caveat', cursive;
  font-size: 17px;
  padding: 6px 12px;
  caret-color: #ff00ff;
}
.search-entry:focus { border-color: #ff00ff; box-shadow: 0 0 14px rgba(255,0,255,0.25); }
.go-btn {
  background: #cc00ff;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-family: 'Caveat', cursive;
  font-weight: 700;
  font-size: 18px;
  padding: 6px 18px;
}
.go-btn:hover { background: #ff00ff; }
.err-lbl { color: #ff5500; font-family: 'Caveat', cursive; font-size: 15px; padding: 0 14px; }
"""


# ── Helpers ───────────────────────────────────────────────────────────────────
def _rng(x, y, w=0, h=0):
    return random.Random(int(x*3+y*7+(w or 1)*11+(h or 1)*13) % 65535)

def sketch_rect_w(cr, x, y, w, h, r, g, b, thick=2.2, jitter=2.8, fill_rgba=None):
    rng = _rng(x,y,w,h)
    j = lambda s=1.0: rng.uniform(-jitter*s, jitter*s)
    def _path():
        cr.move_to(x+j(.5), y+j(.5))
        cr.curve_to(x+w*.33+j(), y+j(), x+w*.67+j(), y+j(), x+w+j(.5), y+j(.5))
        cr.curve_to(x+w+j(), y+h*.33+j(), x+w+j(), y+h*.67+j(), x+w+j(.5), y+h+j(.5))
        cr.curve_to(x+w*.67+j(), y+h+j(), x+w*.33+j(), y+h+j(), x+j(.5), y+h+j(.5))
        cr.curve_to(x+j(), y+h*.67+j(), x+j(), y+h*.33+j(), x+j(.5), y+j(.5))
        cr.close_path()
    if fill_rgba:
        _path(); cr.set_source_rgba(*fill_rgba); cr.fill()
        rng2 = _rng(x,y,w,h); j = lambda s=1.0: rng2.uniform(-jitter*s, jitter*s)
    _path()
    cr.set_source_rgba(r,g,b,0.88); cr.set_line_width(thick)
    cr.set_line_cap(1); cr.set_line_join(1); cr.stroke()

def glow_text(cr, x, y, text, r, g, b, size=14, bold=True):
    cr.select_font_face("Caveat", 0, 1 if bold else 0)
    cr.set_font_size(size)
    cr.set_source_rgba(r,g,b,0.18); cr.move_to(x+1.2,y+0.8); cr.show_text(text)
    cr.set_source_rgba(r,g,b,0.92); cr.move_to(x,y); cr.show_text(text)

def text_cx(cr, cx, y, text, r, g, b, size=14, bold=True, alpha=0.92):
    cr.select_font_face("Caveat", 0, 1 if bold else 0)
    cr.set_font_size(size)
    ext = cr.text_extents(text)
    cr.set_source_rgba(r,g,b,alpha)
    cr.move_to(cx - ext.width/2 - ext.x_bearing, y)
    cr.show_text(text)

def rainbow_bar(cr, x, y, w, h):
    stops = [(0,*C_PINK),(1/5,*C_PURPLE),(2/5,*C_BLUE),(3/5,*C_GREEN),(4/5,*C_YELLOW),(1,*C_ORANGE)]
    pat = __import__('cairo').LinearGradient(x,y,x+w,y)
    for stop in stops: pat.add_color_stop_rgb(*stop)
    cr.rectangle(x,y,w,h); cr.set_source(pat); cr.fill()

def dark_panel_bg(cr, w, h, rule_every=28):
    """Dark #08080e + icon-generator-style paint splatters + ruled lines."""
    cr.set_source_rgb(*C_DARK); cr.rectangle(0,0,w,h); cr.fill()
    rng = random.Random(77)
    neons = [C_PINK, C_PURPLE, C_BLUE, C_GREEN, C_YELLOW, C_ORANGE]
    # Large paint blobs
    for _ in range(14):
        bx = rng.uniform(0, w); by = rng.uniform(0, h)
        brad = rng.uniform(5, 20); nc = rng.choice(neons)
        cr.set_source_rgba(*nc, rng.uniform(0.04, 0.12))
        cr.arc(bx, by, brad, 0, math.pi * 2); cr.fill()
    # Splatter streaks
    for _ in range(18):
        sx = rng.uniform(0, w); sy = rng.uniform(0, h)
        ex = sx + rng.uniform(-80, 80); ey = sy + rng.uniform(-10, 10)
        nc = rng.choice(neons)
        cr.set_source_rgba(*nc, rng.uniform(0.05, 0.15))
        cr.set_line_width(rng.uniform(0.6, 1.8))
        cr.move_to(sx, sy); cr.line_to(ex, ey); cr.stroke()
    # Dense small dots
    for _ in range(60):
        bx = rng.uniform(0, w); by = rng.uniform(0, h)
        brad = rng.uniform(0.8, 3.0); nc = rng.choice(neons)
        cr.set_source_rgba(*nc, rng.uniform(0.08, 0.22))
        cr.arc(bx, by, brad, 0, math.pi * 2); cr.fill()
    # Ruled notebook lines
    cr.set_line_width(0.45)
    for ry in range(rule_every, int(h), rule_every):
        cr.set_source_rgba(1, 1, 1, 0.040)
        cr.move_to(0, ry); cr.line_to(w, ry); cr.stroke()

def arc_gauge(cr, cx, cy, radius, pct, color, thick=3.5, bg_alpha=0.15):
    """Draw a simple arc progress gauge."""
    angle_start = math.pi * 0.75
    angle_end   = math.pi * 2.25
    span = angle_end - angle_start
    cr.set_line_width(thick); cr.set_line_cap(0)  # BUTT cap
    cr.set_source_rgba(*color, bg_alpha)
    cr.arc(cx, cy, radius, angle_start, angle_end); cr.stroke()
    if pct > 0:
        cr.set_source_rgba(*color, 0.88)
        cr.arc(cx, cy, radius, angle_start, angle_start + span*min(pct,1)); cr.stroke()

def wind_compass(cr, cx, cy, radius, deg, color):
    """Draw a minimal compass rose with a needle pointing to wind direction."""
    cr.set_source_rgba(*color, 0.20)
    cr.arc(cx,cy,radius,0,math.pi*2); cr.stroke()
    rad = math.radians(deg)
    tip_x = cx + math.sin(rad)*(radius-2)
    tip_y = cy - math.cos(rad)*(radius-2)
    base_x = cx - math.sin(rad)*(radius*0.4)
    base_y = cy + math.cos(rad)*(radius*0.4)
    cr.set_source_rgba(*color, 0.88); cr.set_line_width(2)
    cr.move_to(base_x, base_y); cr.line_to(tip_x, tip_y); cr.stroke()
    cr.set_source_rgba(*color, 0.88); cr.arc(cx,cy,2.5,0,math.pi*2); cr.fill()
    for i,lbl in enumerate(["N","E","S","W"]):
        a = math.radians(i*90)
        lx = cx + math.sin(a)*(radius+10)
        ly = cy - math.cos(a)*(radius+10)
        cr.select_font_face("Caveat",0,1); cr.set_font_size(13)
        ext = cr.text_extents(lbl)
        cr.set_source_rgba(*color, 0.55)
        cr.move_to(lx - ext.width/2 - ext.x_bearing, ly - ext.height/2 - ext.y_bearing + 4)
        cr.show_text(lbl)


# ── Particle System ───────────────────────────────────────────────────────────
class Particles:
    def __init__(self):
        self.condition="CLEAR"; self.is_day=True
        self.rain=[];  self.snow=[]; self.fog=[]; self.stars=[]
        self.clouds=[];self._t=0
        self._init_stars(); self._init_clouds()

    def _init_stars(self):
        rng=random.Random(42)
        self.stars=[{"x":rng.uniform(0,400),"y":rng.uniform(0,200),
                     "r":rng.uniform(0.4,2.2),"op":rng.uniform(0.4,1.0),
                     "ph":rng.uniform(0,math.pi*2)} for _ in range(60)]

    def _init_clouds(self):
        rng=random.Random(7)
        self.clouds=[{"x":rng.uniform(-60,420),"y":rng.uniform(15,90),"w":rng.uniform(90,180),"sp":rng.uniform(0.12,0.28)} for _ in range(5)]

    def _spawn_rain(self,W,H):
        if len(self.rain)<85:
            rng=random.Random()
            self.rain.append({"x":rng.uniform(0,W),"y":rng.uniform(-H,0),"sp":rng.uniform(8,16),"len":rng.uniform(10,22),"op":rng.uniform(0.3,0.7)})

    def _spawn_snow(self,W,H):
        if len(self.snow)<55:
            rng=random.Random()
            self.snow.append({"x":rng.uniform(0,W),"y":-5,"r":rng.uniform(1.5,4.5),"sp":rng.uniform(1,3),"op":rng.uniform(0.5,1.0),"sw":rng.uniform(0.5,1.5),"ph":rng.uniform(0,math.pi*2)})

    def _spawn_fog(self,W,H):
        if len(self.fog)<10:
            rng=random.Random()
            self.fog.append({"x":rng.uniform(-80,W*1.4),"y":rng.uniform(0,H*0.8),"sp":rng.uniform(0.2,0.5),"op":rng.uniform(0.05,0.18)})

    def step(self,W,H):
        self._t+=1
        c=self.condition
        if c in("RAIN","STORM"): self._spawn_rain(W,H)
        if c=="SNOW":             self._spawn_snow(W,H)
        if c=="FOG":              self._spawn_fog(W,H)
        for p in self.rain[:]:
            p["x"]-=0.4; p["y"]+=p["sp"]
            if p["y"]>H: self.rain.remove(p)
        for p in self.snow[:]:
            p["x"]+=math.sin(self._t*0.05+p["ph"])*p["sw"]; p["y"]+=p["sp"]
            if p["y"]>H: self.snow.remove(p)
        for f in self.fog[:]:
            f["x"]+=f["sp"]
            if f["x"]>W+120: self.fog.remove(f)
        for cl in self.clouds:
            cl["x"]+=cl["sp"]
            if cl["x"]>W+200: cl["x"]=-200

    def draw(self,cr,W,H):
        self._draw_sky(cr,W,H)
        is_night=not self.is_day
        if is_night: self._draw_stars(cr,W,H)
        self._draw_sun_moon(cr,W,H)
        c=self.condition
        if c in("CLOUDY","PARTLY_CLOUDY","STORM"): self._draw_clouds(cr,W,H,n=5 if c=="CLOUDY" else 2,dark=is_night)
        if c in("RAIN","STORM"):   self._draw_rain(cr,W,H)
        if c=="SNOW":              self._draw_snow(cr,W,H)
        if c=="FOG":               self._draw_fog(cr,W,H)

    def _draw_sky(self,cr,W,H):
        import cairo as _cairo
        if self.is_day:
            c={"CLEAR":[(0.38,0.58,0.96),(0.62,0.82,1.0),(0.80,0.92,1.0)],
               "CLOUDY":[(0.45,0.48,0.56),(0.60,0.62,0.68),(0.76,0.78,0.82)],
               "STORM" :[(0.18,0.16,0.28),(0.30,0.28,0.40),(0.50,0.48,0.56)],
               "RAIN"  :[(0.30,0.38,0.58),(0.50,0.58,0.75),(0.70,0.76,0.88)],
               "SNOW"  :[(0.65,0.72,0.88),(0.80,0.84,0.94),(0.92,0.94,0.98)],
               "FOG"   :[(0.72,0.74,0.78),(0.84,0.85,0.87),(0.94,0.94,0.95)],
               }.get(self.condition,[(0.38,0.58,0.96),(0.62,0.82,1.0),(0.80,0.92,1.0)])
        else:
            c=[(0.04,0.02,0.10),(0.08,0.04,0.18),(0.14,0.06,0.28)]
        pat=_cairo.LinearGradient(0,0,0,H)
        pat.add_color_stop_rgb(0.0,*c[0]); pat.add_color_stop_rgb(0.5,*c[1]); pat.add_color_stop_rgb(1.0,*c[2])
        cr.set_source(pat); cr.rectangle(0,0,W,H); cr.fill()

    def _draw_stars(self,cr,W,H):
        t=self._t*0.015
        for s in self.stars:
            op=s["op"]*(0.5+0.5*math.sin(t+s["ph"]))
            cr.set_source_rgba(0.9,0.85,1,op); cr.arc(s["x"],s["y"],s["r"],0,math.pi*2); cr.fill()

    @staticmethod
    def _calc_moon_phase():
        """Return (phase_fraction 0-1, phase_name, waxing). 0=new, 0.5=full."""
        from datetime import date
        today = date.today()
        ref = date(2024, 1, 11)  # known new moon
        days = (today - ref).days
        cycle = 29.53058867
        pos = (days % cycle) / cycle
        waxing = pos < 0.5
        illum = (1 - math.cos(pos * 2 * math.pi)) / 2
        if pos < 0.04 or pos > 0.96:   name = "NEW MOON"
        elif pos < 0.22:                name = "WAXING CRESCENT"
        elif pos < 0.28:                name = "FIRST QUARTER"
        elif pos < 0.47:                name = "WAXING GIBBOUS"
        elif pos < 0.53:                name = "FULL MOON"
        elif pos < 0.72:                name = "WANING GIBBOUS"
        elif pos < 0.78:                name = "LAST QUARTER"
        else:                           name = "WANING CRESCENT"
        return illum, name, waxing

    def _draw_sun_moon(self,cr,W,H):
        if self.is_day:
            # Golden sun
            sx,sy=W*0.78,H*0.28
            cr.set_source_rgba(1.0,0.92,0.3,0.18); cr.arc(sx,sy,42,0,math.pi*2); cr.fill()
            cr.set_source_rgba(1.0,0.88,0.2,0.30); cr.arc(sx,sy,28,0,math.pi*2); cr.fill()
            cr.set_source_rgba(1.0,0.95,0.5,0.95); cr.arc(sx,sy,16,0,math.pi*2); cr.fill()
            # Rays
            cr.set_line_width(1.5); cr.set_source_rgba(1.0,0.92,0.3,0.28)
            for i in range(8):
                a=math.radians(i*45+self._t*0.3)
                cr.move_to(sx+math.cos(a)*20,sy+math.sin(a)*20)
                cr.line_to(sx+math.cos(a)*38,sy+math.sin(a)*38); cr.stroke()
        else:
            # Real moon phase
            illum, phase_name, waxing = self._calc_moon_phase()
            mx,my = W*0.78, H*0.28
            R = 18
            # Full disk (dim base)
            cr.set_source_rgba(0.75, 0.72, 0.90, 0.90)
            cr.arc(mx, my, R, 0, math.pi*2); cr.fill()
            # Draw shadow to show correct phase
            if phase_name == "NEW MOON":
                # All dark
                cr.set_source_rgba(0.10, 0.06, 0.20, 0.92)
                cr.arc(mx, my, R, 0, math.pi*2); cr.fill()
            elif phase_name != "FULL MOON":
                # Shadow ellipse method: cover dark portion
                cr.save()
                cr.arc(mx, my, R, -math.pi/2, math.pi/2)  # right half clip
                cr.close_path(); cr.clip()
                # Shadow X offset based on phase
                if waxing:
                    # Waxing: shadow on left → dark ellipse shifted left
                    shadow_x = mx - R * (1 - 2*illum)
                else:
                    # Waning: shadow on right → dark ellipse shifted right
                    shadow_x = mx + R * (1 - 2*illum)
                cr.reset_clip()
                cr.save()
                # Dark shadow disk
                cr.set_source_rgba(0.06, 0.03, 0.14, 0.94)
                # For waxing: cover left side
                if waxing:
                    cr.arc(mx, my, R, math.pi/2, 3*math.pi/2)
                    cr.close_path(); cr.fill()
                    # Ellipse to trim correctly
                    x_scale = abs(1 - 2*illum)
                    cr.save()
                    cr.translate(mx, my); cr.scale(x_scale, 1.0)
                    cr.arc(0, 0, R, -math.pi/2, math.pi/2)
                    cr.close_path()
                    if illum < 0.5:
                        cr.fill()
                    else:
                        cr.set_source_rgba(0.75, 0.72, 0.90, 0.90); cr.fill()
                    cr.restore()
                else:
                    cr.arc(mx, my, R, -math.pi/2, math.pi/2)
                    cr.close_path(); cr.fill()
                    x_scale = abs(1 - 2*illum)
                    cr.save()
                    cr.translate(mx, my); cr.scale(x_scale, 1.0)
                    cr.arc(0, 0, R, math.pi/2, 3*math.pi/2)
                    cr.close_path()
                    if illum < 0.5:
                        cr.fill()
                    else:
                        cr.set_source_rgba(0.75, 0.72, 0.90, 0.90); cr.fill()
                    cr.restore()
                cr.restore()
            # Soft glow ring
            cr.set_source_rgba(0.70, 0.65, 0.95, 0.22)
            cr.set_line_width(5); cr.arc(mx,my,R+2,0,math.pi*2); cr.stroke()
            # Phase name label
            cr.select_font_face("Caveat", 0, 0); cr.set_font_size(13)
            cr.set_source_rgba(0.70, 0.65, 0.95, 0.70)
            ext = cr.text_extents(phase_name)
            cr.move_to(mx - ext.width/2, my + R + 13); cr.show_text(phase_name)

    def _draw_rain(self,cr,W,H):
        for p in self.rain:
            cr.set_source_rgba(0.15,0.45,0.85,p["op"]); cr.set_line_width(1.0)
            cr.move_to(p["x"],p["y"]); cr.line_to(p["x"]-p["len"]*0.13,p["y"]-p["len"]); cr.stroke()

    def _draw_snow(self,cr,W,H):
        for p in self.snow:
            cr.set_source_rgba(0.88,0.94,1,p["op"]); cr.arc(p["x"],p["y"],p["r"],0,math.pi*2); cr.fill()

    def _draw_clouds(self,cr,W,H,n=3,dark=False):
        col=(0.15,0.10,0.22) if dark else (0.22,0.16,0.35)
        for cl in self.clouds[:n]:
            cr.set_source_rgba(*col,0.55)
            cw,cx,cy=cl["w"],cl["x"],cl["y"]; ch=cw*0.40
            cr.arc(cx+cw*0.20,cy+ch*0.5,ch*0.52,0,math.pi*2); cr.fill()
            cr.arc(cx+cw*0.50,cy+ch*0.3,ch*0.62,0,math.pi*2); cr.fill()
            cr.arc(cx+cw*0.80,cy+ch*0.5,ch*0.48,0,math.pi*2); cr.fill()
            cr.rectangle(cx+cw*0.1,cy+ch*0.4,cw*0.8,ch*0.6); cr.fill()

    def _draw_fog(self,cr,W,H):
        for f in self.fog:
            cr.set_source_rgba(0.22,0.18,0.28,f["op"]); cr.rectangle(f["x"]-80,f["y"],W+160,26); cr.fill()


# ── App ───────────────────────────────────────────────────────────────────────
class NyxusWeather(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.weather",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self._particles = Particles()
        self._city="LOCATING..."; self._temp=None; self._feels=None
        self._cond="CLEAR"; self._is_day=True; self._wind=None
        self._humidity=None; self._uv=None; self._pressure=None
        self._wind_dir=None; self._forecast=[]; self._err=""
        self._lat=None; self._lon=None; self._anim_t=0.0

    def do_activate(self):
        p=Gtk.CssProvider()
        try: p.load_from_string(CSS)
        except AttributeError: p.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),p,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.win=Gtk.ApplicationWindow(application=self,title="NYXUS Weather")
        self.win.set_default_size(400,720); self.win.set_resizable(False)
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)

        # Sky animation canvas
        self._scene=Gtk.DrawingArea(); self._scene.set_size_request(400,190)
        self._scene.set_draw_func(self._draw_scene,None); root.append(self._scene)

        # Main data panel (dark, ruled lines)
        self._panel=Gtk.DrawingArea(); self._panel.set_size_request(400,310)
        self._panel.set_draw_func(self._draw_panel,None); root.append(self._panel)

        # Search bar
        search=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=8)
        search.set_margin_top(4); search.set_margin_bottom(4)
        search.set_margin_start(12); search.set_margin_end(12)
        self._search=Gtk.Entry(); self._search.add_css_class("search-entry")
        self._search.set_placeholder_text("Search city…"); self._search.set_hexpand(True)
        self._search.connect("activate",lambda *_:self._on_search()); search.append(self._search)
        go=Gtk.Button(label="Go"); go.add_css_class("go-btn")
        go.connect("clicked",lambda *_:self._on_search()); search.append(go)
        root.append(search)
        self._err_lbl=Gtk.Label(); self._err_lbl.add_css_class("err-lbl")
        self._err_lbl.set_halign(Gtk.Align.START); self._err_lbl.set_margin_start(14)
        root.append(self._err_lbl)

        # 5-day forecast
        self._fc_area=Gtk.DrawingArea(); self._fc_area.set_size_request(400,120)
        self._fc_area.set_draw_func(self._draw_forecast,None); root.append(self._fc_area)

        GLib.timeout_add(50,self._animate)
        GLib.timeout_add_seconds(600,self._refresh)
        threading.Thread(target=self._geoip_locate,daemon=True).start()
        self.win.present()

    def _animate(self):
        self._anim_t+=0.04
        W=self._scene.get_width() or 400; H=self._scene.get_height() or 190
        self._particles.step(W,H)
        self._scene.queue_draw(); self._panel.queue_draw(); self._fc_area.queue_draw()
        return GLib.SOURCE_CONTINUE

    # ── Sky Scene ─────────────────────────────────────────────────────────────
    def _draw_scene(self,area,cr,W,H,_):
        self._particles.draw(cr,W,H)

        # Dot-grid overlay
        cr.set_source_rgba(0.20,0.05,0.38,0.06)
        for gx in range(0,W+20,20):
            for gy in range(0,H+20,20):
                cr.arc(gx,gy,0.7,0,math.pi*2); cr.fill()

        # Gradient vignette at bottom
        import cairo as _cairo
        pat=_cairo.LinearGradient(0,H*0.55,0,H)
        pat.add_color_stop_rgba(0,0,0,0,0); pat.add_color_stop_rgba(1,0.031,0.031,0.055,0.78)
        cr.rectangle(0,0,W,H); cr.set_source(pat); cr.fill()

        # City name — big Caveat
        cr.select_font_face("Caveat",0,1); cr.set_font_size(28)
        city_ext = cr.text_extents(self._city)
        cx = W/2 - city_ext.width/2 - city_ext.x_bearing
        # Subtle glow
        cr.set_source_rgba(*C_PINK,0.14); cr.move_to(cx+1.5,H-22+1); cr.show_text(self._city)
        cr.set_source_rgba(*C_PINK,0.92); cr.move_to(cx,H-22); cr.show_text(self._city)

        # Status pills
        t=datetime.now().strftime("%H:%M")
        badge="DAY" if self._is_day else "NIGHT"
        items=[(t,C_YELLOW),(badge,C_BLUE),(LABELS.get(self._cond,self._cond),C_GREEN)]
        xpos=16
        for txt,col in items:
            cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
            ext=cr.text_extents(txt)
            # pill bg
            pad=5
            cr.set_source_rgba(*col,0.15); cr.rectangle(xpos-pad,H-46-12,ext.width+pad*2,16); cr.fill()
            cr.set_source_rgba(*col,0.88); cr.move_to(xpos,H-46); cr.show_text(txt)
            xpos+=ext.width+20

        # Rainbow bottom bar
        rainbow_bar(cr,0,H-3,W,3)

    # ── Main Data Panel ───────────────────────────────────────────────────────
    def _draw_panel(self,area,cr,W,H,_):
        dark_panel_bg(cr,W,H)

        if self._temp is None:
            cr.select_font_face("Caveat",0,1); cr.set_font_size(22)
            cr.set_source_rgba(*C_PURPLE,0.8)
            cr.move_to(W/2-80, H/2); cr.show_text("LOCATING…")
            return

        # ── Big temperature ────────────────────────────────────────────────
        temp_txt=f"{self._temp}°"
        cr.select_font_face("Caveat",0,1); cr.set_font_size(82)
        ext=cr.text_extents(temp_txt)
        tx,ty=18,-ext.y_bearing+10
        # glow shadow
        cr.set_source_rgba(*C_PINK,0.13); cr.move_to(tx+2,ty+2); cr.show_text(temp_txt)
        cr.set_source_rgba(*C_PINK,0.92); cr.move_to(tx,ty); cr.show_text(temp_txt)

        # Unit F label
        cr.select_font_face("Caveat",0,0); cr.set_font_size(16)
        cr.set_source_rgba(*C_DIM,0.8); cr.move_to(tx+ext.width+4,ty); cr.show_text("°F")

        # ── Condition badge ────────────────────────────────────────────────
        cond_lbl=LABELS.get(self._cond,self._cond)
        icon=ICONS.get(self._cond,"?")
        badge_x=W-160; badge_y=16; badge_w=148; badge_h=44
        sketch_rect_w(cr,badge_x,badge_y,badge_w,badge_h,*C_GREEN,thick=2.0,jitter=2.5,
                      fill_rgba=(*C_GREEN,0.08))
        cr.select_font_face("",0,0); cr.set_font_size(22)
        cr.set_source_rgba(*C_GREEN,0.90)
        cr.move_to(badge_x+10,badge_y+30); cr.show_text(icon)
        cr.select_font_face("Caveat",0,1); cr.set_font_size(16)
        cr.set_source_rgba(*C_GREEN,0.90)
        cr.move_to(badge_x+36,badge_y+30); cr.show_text(cond_lbl)

        # Feels like sub-line
        feels_y = ty+8
        cr.select_font_face("Caveat",0,0); cr.set_font_size(16)
        cr.set_source_rgba(*C_DIM,0.80)
        cr.move_to(20, feels_y); cr.show_text(f"Feels like {self._feels}°F")

        # Rainbow divider
        div_y = 100
        rainbow_bar(cr,0,div_y,W,2)

        # ── 6-stat grid (2 rows × 3 cols) ─────────────────────────────────
        # Stats: Wind, Humidity, UV Index, Pressure, Feels Like, Condition
        wind_dir_txt=""
        if self._wind_dir is not None:
            idx=round(self._wind_dir/45)%8
            wind_dir_txt=WIND_DIRS[idx]

        stats=[
            ("Wind",       f"{self._wind} mph" if self._wind is not None else "—",
             C_ORANGE, f"{wind_dir_txt}" if wind_dir_txt else ""),
            ("Humidity",   f"{self._humidity}%" if self._humidity is not None else "—",
             C_BLUE, ""),
            ("UV Index",   str(self._uv) if self._uv is not None else "—",
             C_YELLOW, _uv_label(self._uv)),
            ("Pressure",   f"{self._pressure} hPa" if self._pressure is not None else "—",
             C_PURPLE, ""),
            ("Dew Point",  f"{_dew(self._temp,self._humidity)}°F" if self._temp and self._humidity else "—",
             C_GREEN, ""),
            ("Updated",    datetime.now().strftime("%H:%M"),
             C_PINK, ""),
        ]

        cols=3; rows=2
        pad_left=12; pad_right=12
        cell_w=(W-pad_left-pad_right)//cols
        cell_h=82
        top_y=div_y+10

        for i,(label,value,color,sub) in enumerate(stats):
            row=i//cols; col=i%cols
            cx=pad_left+col*cell_w+cell_w//2
            cy=top_y+row*cell_h+cell_h//2
            bx=pad_left+col*cell_w+4
            by=top_y+row*cell_h+6
            bw=cell_w-8; bh=cell_h-10
            tilt=[-2.0,2.5,-1.5,1.8,-2.2,1.4][i]

            # Sketch border card
            sketch_rect_w(cr,bx,by,bw,bh,*color,thick=1.8,jitter=2.2,fill_rgba=(*color,0.07))

            cr.save(); cr.translate(cx,cy); cr.rotate(math.radians(tilt))
            # Label
            cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
            cr.set_source_rgba(*C_DIM,0.75)
            label_ext=cr.text_extents(label)
            cr.move_to(-label_ext.width/2-label_ext.x_bearing,-24); cr.show_text(label)
            # Value
            cr.select_font_face("Caveat",0,1); cr.set_font_size(20)
            cr.set_source_rgba(*color,0.92)
            val_ext=cr.text_extents(value)
            cr.move_to(-val_ext.width/2-val_ext.x_bearing,-2); cr.show_text(value)
            # Sub-label
            if sub:
                cr.select_font_face("Caveat",0,0); cr.set_font_size(11)
                cr.set_source_rgba(*color,0.55)
                sub_ext=cr.text_extents(sub)
                cr.move_to(-sub_ext.width/2-sub_ext.x_bearing,16); cr.show_text(sub)
            # Dot accent
            cr.set_source_rgba(*color,0.70); cr.arc(0,28,2.5,0,math.pi*2); cr.fill()
            cr.restore()

        # Bottom gauge strip
        gauge_y = div_y + rows*cell_h + 20
        rainbow_bar(cr,0,gauge_y,W,2)

        # Humidity arc gauge
        if self._humidity is not None:
            arc_gauge(cr,60,gauge_y+48,34,self._humidity/100,C_BLUE,thick=4.0)
            text_cx(cr,60,gauge_y+50,"HUM",*C_DIM,size=9,bold=False)

        # Wind speed gauge
        if self._wind is not None:
            speed_pct=min(self._wind/60,1.0)
            arc_gauge(cr,160,gauge_y+48,34,speed_pct,C_ORANGE,thick=4.0)
            text_cx(cr,160,gauge_y+50,"WIND",*C_DIM,size=9,bold=False)

        # UV gauge
        if self._uv is not None:
            uv_pct=min(self._uv/11,1.0)
            arc_gauge(cr,260,gauge_y+48,34,uv_pct,C_YELLOW,thick=4.0)
            text_cx(cr,260,gauge_y+50,"UV",*C_DIM,size=9,bold=False)

        # Wind compass
        if self._wind_dir is not None:
            wind_compass(cr,340,gauge_y+48,22,self._wind_dir,C_ORANGE)

        rainbow_bar(cr,0,H-3,W,3)

    # ── 5-day Forecast ────────────────────────────────────────────────────────
    def _draw_forecast(self,area,cr,W,H,_):
        dark_panel_bg(cr,W,H,rule_every=24)
        rainbow_bar(cr,0,0,W,2)

        # Header
        glow_text(cr,14,22,"5-Day Forecast",*C_PURPLE,size=16,bold=True)
        cr.set_source_rgba(*C_PURPLE,0.18); cr.set_line_width(1.2)
        cr.move_to(0,30); cr.line_to(W,30); cr.stroke()

        if not self._forecast: return
        n=min(5,len(self._forecast)); col_w=W/n

        for i,fc in enumerate(self._forecast[:5]):
            col=PALETTE[i%len(PALETTE)]
            cx=col_w*i+col_w/2

            if i>0:
                cr.set_source_rgba(*col,0.12); cr.set_line_width(1)
                cr.move_to(col_w*i,30); cr.line_to(col_w*i,H-2); cr.stroke()

            # Column bg tint
            cr.set_source_rgba(*col,0.05); cr.rectangle(col_w*i,30,col_w,H-30); cr.fill()

            # Day name
            cr.select_font_face("Caveat",0,1); cr.set_font_size(15)
            cr.set_source_rgba(*col,0.92)
            day_ext=cr.text_extents(fc["day"])
            cr.move_to(cx-day_ext.width/2-day_ext.x_bearing,52); cr.show_text(fc["day"])

            # Icon
            cr.select_font_face("",0,0); cr.set_font_size(22)
            icon=ICONS.get(fc["cond"],"?")
            icon_ext=cr.text_extents(icon)
            cr.set_source_rgba(*col,0.90)
            cr.move_to(cx-icon_ext.width/2-icon_ext.x_bearing,78); cr.show_text(icon)

            # Hi temp
            hi=f"{fc['hi']}°" if fc.get("hi") is not None else "—"
            cr.select_font_face("Caveat",0,1); cr.set_font_size(17)
            cr.set_source_rgba(*col,0.92)
            hi_ext=cr.text_extents(hi)
            cr.move_to(cx-hi_ext.width/2-hi_ext.x_bearing,98); cr.show_text(hi)

            # Lo temp
            lo=f"{fc['lo']}°" if fc.get("lo") is not None else "—"
            cr.select_font_face("Caveat",0,0); cr.set_font_size(13)
            cr.set_source_rgba(*C_DIM,0.70)
            lo_ext=cr.text_extents(lo)
            cr.move_to(cx-lo_ext.width/2-lo_ext.x_bearing,H-10); cr.show_text(lo)

            # Accent dot
            cr.set_source_rgba(*col,0.60); cr.arc(cx,H-22,2.5,0,math.pi*2); cr.fill()

    # ── Data Fetching ─────────────────────────────────────────────────────────
    def _geoip_locate(self):
        try:
            with urlopen("http://ip-api.com/json/?fields=lat,lon,city,status",timeout=6) as r:
                geo=json.loads(r.read())
            if geo.get("status")=="success":
                self._lat=geo["lat"]; self._lon=geo["lon"]
                self._city=geo.get("city","").upper()
                self._fetch_weather(); return
        except Exception: pass
        try:
            with open(CONFIG_FILE) as f: cfg=json.load(f)
            if cfg.get("lat"):
                self._lat=cfg["lat"]; self._lon=cfg["lon"]
                self._city=cfg.get("city","CONFIG").upper()
                self._fetch_weather(); return
        except Exception: pass
        GLib.idle_add(lambda:(self._panel.queue_draw(),None)[1])

    def _fetch_weather(self):
        url=(f"https://api.open-meteo.com/v1/forecast?latitude={self._lat}&longitude={self._lon}"
             f"&current=temperature_2m,apparent_temperature,is_day,weather_code,wind_speed_10m,"
             f"wind_direction_10m,relative_humidity_2m,uv_index,surface_pressure"
             f"&daily=temperature_2m_max,temperature_2m_min,weather_code"
             f"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=5")
        try:
            with urlopen(url,timeout=10) as r: d=json.loads(r.read())
            cur=d.get("current",{}); daily=d.get("daily",{})
            self._temp      =round(cur.get("temperature_2m",0))
            self._feels     =round(cur.get("apparent_temperature",0))
            self._is_day    =bool(cur.get("is_day",1))
            self._wind      =round(cur.get("wind_speed_10m",0))
            self._wind_dir  =cur.get("wind_direction_10m")
            self._humidity  =cur.get("relative_humidity_2m")
            self._uv        =round(cur.get("uv_index",0),1) if cur.get("uv_index") is not None else None
            self._pressure  =round(cur.get("surface_pressure",0)) if cur.get("surface_pressure") is not None else None
            self._cond      =WMO.get(cur.get("weather_code",0),"CLEAR")
            times=daily.get("time",[])
            self._forecast=[{
                "day":  datetime.strptime(times[i],"%Y-%m-%d").strftime("%a").upper(),
                "hi":   round(daily["temperature_2m_max"][i]) if daily.get("temperature_2m_max") else None,
                "lo":   round(daily["temperature_2m_min"][i]) if daily.get("temperature_2m_min") else None,
                "cond": WMO.get(daily["weather_code"][i],"CLEAR") if daily.get("weather_code") else "CLEAR",
            } for i in range(min(5,len(times)))]
            self._err=""
            GLib.idle_add(self._update_ui)
        except Exception as e:
            self._err=str(e)[:55]; GLib.idle_add(self._update_ui)

    def _refresh(self):
        if self._lat: threading.Thread(target=self._fetch_weather,daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _on_search(self):
        city=self._search.get_text().strip()
        if not city: return
        self._err_lbl.set_text("Searching…")
        threading.Thread(target=self._geocode,args=(city,),daemon=True).start()

    def _geocode(self,city):
        url=f"https://nominatim.openstreetmap.org/search?q={quote(city)}&format=json&limit=1"
        try:
            req=Request(url,headers={"User-Agent":"NYXUS-Weather/1.0"})
            with urlopen(req,timeout=8) as r: res=json.loads(r.read())
            if res:
                self._lat=float(res[0]["lat"]); self._lon=float(res[0]["lon"])
                self._city=city.upper()
                with open(CONFIG_FILE,"w") as f:
                    json.dump({"city":self._city,"lat":self._lat,"lon":self._lon},f)
                self._fetch_weather()
            else:
                GLib.idle_add(lambda:(self._err_lbl.set_text(f"City not found: {city}"),None)[1])
        except Exception as e:
            GLib.idle_add(lambda:(self._err_lbl.set_text(str(e)[:55]),None)[1])

    def _update_ui(self):
        self._err_lbl.set_text(self._err)
        self._particles.condition=self._cond
        self._particles.is_day=self._is_day
        self._panel.queue_draw(); self._fc_area.queue_draw(); self._scene.queue_draw()
        return GLib.SOURCE_REMOVE


# ── Helpers ───────────────────────────────────────────────────────────────────
def _uv_label(uv):
    if uv is None: return ""
    if uv < 3:  return "Low"
    if uv < 6:  return "Moderate"
    if uv < 8:  return "High"
    if uv < 11: return "Very High"
    return "Extreme"

def _dew(temp_f, rh):
    """Approximate dew point in Fahrenheit."""
    if temp_f is None or rh is None: return None
    tc=(temp_f-32)*5/9
    dp=tc-(100-rh)/5
    return round(dp*9/5+32)


if __name__=="__main__":
    NyxusWeather().run(None)
