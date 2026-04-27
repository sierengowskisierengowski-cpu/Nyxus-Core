#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Weather — Native GTK4 Animated Weather Widget                 ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
import gi
gi.require_version('Gtk', '4.0')
from gi.repository import Gtk, Gdk, GLib
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
LABELS = {"CLEAR":"CLEAR","PARTLY_CLOUDY":"PARTLY CLOUDY","CLOUDY":"OVERCAST",
          "FOG":"FOG","RAIN":"RAIN","SNOW":"SNOW","STORM":"THUNDERSTORM"}
ICONS  = {"CLEAR":"☀","PARTLY_CLOUDY":"⛅","CLOUDY":"☁","RAIN":"🌧","SNOW":"❄","STORM":"⛈","FOG":"🌫"}

# Neon palette
C_PINK   = (1.0, 0.0, 1.0)
C_PURPLE = (0.8, 0.0, 1.0)
C_BLUE   = (0.0, 0.53, 1.0)
C_GREEN  = (0.22, 1.0, 0.08)
C_YELLOW = (1.0, 1.0, 0.0)
C_ORANGE = (1.0, 0.33, 0.0)


def glow_text(cr, x, y, text, r, g, b, size=13, bold=True):
    cr.select_font_face("JetBrains Mono", 0, 1 if bold else 0)
    cr.set_font_size(size)
    for dx, dy, a in [(-1,-1,.22),(1,-1,.22),(-1,1,.22),(1,1,.22),
                       (-2,0,.09),(2,0,.09),(0,-2,.09),(0,2,.09)]:
        cr.set_source_rgba(r, g, b, a)
        cr.move_to(x+dx, y+dy); cr.show_text(text)
    cr.set_source_rgba(r, g, b, 1.0)
    cr.move_to(x, y); cr.show_text(text)


def draw_neon_card(cr, x, y, w, h, color, rotation=0.0, alpha=0.10):
    """Draw a tilted neon card with glow at (x,y) centered."""
    r, g, b = color
    cr.save()
    cr.translate(x, y)
    cr.rotate(math.radians(rotation))
    hw, hh = w/2, h/2
    # Glow
    for gw, fa in [(18, 0.25), (10, 0.55), (5, 1.0)]:
        cr.set_source_rgba(r, g, b, 0.07 * fa)
        cr.set_line_width(gw)
        cr.rectangle(-hw, -hh, w, h); cr.stroke()
    # Fill
    cr.set_source_rgba(r, g, b, alpha)
    cr.rectangle(-hw, -hh, w, h); cr.fill()
    cr.set_source_rgba(0, 0, 0, 0.55)
    cr.rectangle(-hw, -hh, w, h); cr.fill()
    # Border
    cr.set_source_rgba(r, g, b, 0.9)
    cr.set_line_width(1.4)
    cr.rectangle(-hw, -hh, w, h); cr.stroke()
    cr.restore()


CSS = b"""
* { font-family: 'JetBrains Mono', 'Monospace', monospace; }
window { background-color: #030206; color: #e8e0f5; }
.search-entry {
    background-color: rgba(7,3,15,0.85);
    border: 1px solid rgba(204,0,255,0.35);
    color: #e8e0f5;
    border-radius: 2px;
    padding: 6px 12px;
    font-size: 11px;
    box-shadow: none;
    caret-color: #cc00ff;
}
.search-entry text { background-color: transparent; }
.go-btn {
    background-color: rgba(255,0,255,0.08);
    color: #ff00ff;
    border: 1px solid #ff00ff;
    border-radius: 2px;
    padding: 5px 14px;
    font-size: 11px;
    font-weight: bold;
}
.go-btn:hover { background-color: rgba(255,0,255,0.22); }
.err-lbl { color: #ff5500; font-size: 11px; }
"""


class Particles:
    def __init__(self):
        self.t = 0.0
        self.condition = "CLEAR"
        self.is_day    = True
        self.sun_angle = 0.0
        self.lightning_timer = random.uniform(4,8)
        self.lightning_flash = 0.0
        self.stars  = [{"x":random.uniform(0,380),"y":random.uniform(0,220),
                         "r":random.uniform(0.8,2.0),"ph":random.uniform(0,math.pi*2)} for _ in range(80)]
        self.rain   = [{"x":random.uniform(0,380),"y":random.uniform(-20,220),
                         "spd":random.uniform(5,10),"len":random.uniform(8,18),
                         "op":random.uniform(0.3,0.8)} for _ in range(110)]
        self.snow   = [{"x":random.uniform(0,380),"y":random.uniform(-10,220),
                         "vx":random.uniform(-0.3,0.3),"vy":random.uniform(0.4,1.2),
                         "r":random.uniform(2,5),"op":random.uniform(0.5,1.0),
                         "ph":random.uniform(0,math.pi*2)} for _ in range(65)]
        self.clouds = [{"x":random.uniform(-80,380),"y":random.uniform(20,100),
                         "w":random.uniform(90,160),"spd":random.uniform(0.08,0.25)} for _ in range(5)]
        self.fog    = [{"x":0,"y":random.uniform(10,200),
                         "op":random.uniform(0.05,0.12),"spd":random.uniform(0.05,0.18)} for _ in range(5)]

    def step(self, W, H, dt=0.05):
        self.t += dt; c = self.condition
        if c in ("RAIN","STORM"):
            for p in self.rain:
                p["y"] += p["spd"]; p["x"] -= p["spd"]*0.12
                if p["y"] > H or p["x"] < -5:
                    p["y"]=random.uniform(-20,0); p["x"]=random.uniform(0,W)
        if c == "SNOW":
            for p in self.snow:
                p["y"] += p["vy"]; p["x"] += p["vx"]+math.sin(self.t*0.6+p["ph"])*0.35
                if p["y"] > H: p["y"]=-8; p["x"]=random.uniform(0,W)
                if p["x"] < -5: p["x"]=W
                if p["x"] > W+5: p["x"]=0
        if c == "STORM":
            self.lightning_timer -= dt
            if self.lightning_flash > 0: self.lightning_flash = max(0,self.lightning_flash-dt*3)
            elif self.lightning_timer <= 0: self.lightning_flash=1.0; self.lightning_timer=random.uniform(4,9)
        if c in ("CLOUDY","PARTLY_CLOUDY"):
            for cl in self.clouds:
                cl["x"] += cl["spd"]
                if cl["x"] > W+cl["w"]: cl["x"]=-cl["w"]
        if c == "FOG":
            for f in self.fog:
                f["x"] += f["spd"]
                if f["x"] > W+80: f["x"]=-80
        self.sun_angle += dt*0.12

    def draw(self, cr, W, H):
        self._sky(cr, W, H); c=self.condition; day=self.is_day
        if   c=="CLEAR":         (self._sun if day else self._moon_stars)(cr,W,H)
        elif c=="PARTLY_CLOUDY": (self._sun if day else self._moon_stars)(cr,W,H); self._clouds(cr,W,H,2)
        elif c=="CLOUDY":        self._clouds(cr,W,H,4)
        elif c=="RAIN":          self._clouds(cr,W,H,3,dark=True); self._rain(cr,W,H)
        elif c=="SNOW":          self._clouds(cr,W,H,2); self._snow_draw(cr,W,H)
        elif c=="STORM":
            if self.lightning_flash>0:
                cr.set_source_rgba(1,1,0.9,self.lightning_flash*0.35)
                cr.rectangle(0,0,W,H); cr.fill()
            self._clouds(cr,W,H,4,dark=True); self._rain(cr,W,H)
        elif c=="FOG": self._fog_draw(cr,W,H)

    def _sky(self,cr,w,h):
        c=self.condition; day=self.is_day
        skies={("CLEAR",True):((0.10,0.04,0.01),(0.01,0.01,0.02)),
               ("CLEAR",False):((0.02,0.01,0.07),(0.01,0.01,0.02)),
               ("RAIN",True):((0.02,0.03,0.07),(0.01,0.01,0.02)),
               ("STORM",True):((0.01,0.01,0.05),(0.01,0.01,0.02)),
               ("SNOW",True):((0.04,0.02,0.08),(0.01,0.01,0.02)),
               ("FOG",True):((0.05,0.04,0.07),(0.02,0.01,0.03))}
        key=(c if c in("RAIN","STORM","SNOW","FOG") else "CLEAR",day)
        top,bot=skies.get(key,((0.03,0.02,0.06),(0.01,0.01,0.02)))
        for i in range(h):
            t=i/h; r=top[0]+(bot[0]-top[0])*t; g=top[1]+(bot[1]-top[1])*t; b=top[2]+(bot[2]-top[2])*t
            cr.set_source_rgb(r,g,b); cr.rectangle(0,i,w,1); cr.fill()

    def _sun(self,cr,w,h):
        cx,cy=w*0.72,h*0.28
        cr.set_source_rgba(1,0.5,0,0.07); cr.arc(cx,cy,55,0,math.pi*2); cr.fill()
        cr.set_source_rgba(1,0.65,0.1,0.14); cr.arc(cx,cy,40,0,math.pi*2); cr.fill()
        for i in range(12):
            a=self.sun_angle+i*math.pi*2/12; ri,ro=24,37+5*math.sin(self.t*2+i)
            cr.set_source_rgba(1,0.65,0.1,0.65); cr.set_line_width(2)
            cr.move_to(cx+math.cos(a)*ri,cy+math.sin(a)*ri)
            cr.line_to(cx+math.cos(a)*ro,cy+math.sin(a)*ro); cr.stroke()
        cr.set_source_rgba(1,0.88,0.3,1); cr.arc(cx,cy,22,0,math.pi*2); cr.fill()

    def _moon_stars(self,cr,w,h):
        for s in self.stars:
            op=s["r"]/2*(0.5+0.5*math.sin(self.t*1.8+s["ph"]))
            cr.set_source_rgba(0.9,0.85,1,op); cr.arc(s["x"],s["y"],s["r"]*0.6,0,math.pi*2); cr.fill()
        cx,cy=w*0.72,h*0.2
        cr.set_source_rgba(0,0.5,1,0.07); cr.arc(cx,cy,26,0,math.pi*2); cr.fill()
        cr.set_source_rgba(0.85,0.9,1,0.92); cr.arc(cx,cy,17,0,math.pi*2); cr.fill()
        cr.set_source_rgb(0.02,0.01,0.07); cr.arc(cx+6,cy-4,13,0,math.pi*2); cr.fill()

    def _moon_stars(self,cr,w,h): # consolidated
        for s in self.stars:
            op=s["r"]/2*(0.5+0.5*math.sin(self.t*1.8+s["ph"]))
            cr.set_source_rgba(0.9,0.85,1,op); cr.arc(s["x"],s["y"],s["r"]*0.6,0,math.pi*2); cr.fill()
        cx,cy=w*0.72,h*0.2
        cr.set_source_rgba(0,0.5,1,0.07); cr.arc(cx,cy,26,0,math.pi*2); cr.fill()
        cr.set_source_rgba(0.85,0.9,1,0.92); cr.arc(cx,cy,17,0,math.pi*2); cr.fill()
        cr.set_source_rgb(0.02,0.01,0.07); cr.arc(cx+6,cy-4,13,0,math.pi*2); cr.fill()

    def _rain(self,cr,w,h):
        for p in self.rain:
            cr.set_source_rgba(0.1,0.5,1,p["op"]); cr.set_line_width(1.0)
            cr.move_to(p["x"],p["y"]); cr.line_to(p["x"]-p["len"]*0.13,p["y"]-p["len"]); cr.stroke()

    def _snow_draw(self,cr,w,h):
        for p in self.snow:
            cr.set_source_rgba(0.85,0.92,1,p["op"]); cr.arc(p["x"],p["y"],p["r"],0,math.pi*2); cr.fill()

    def _clouds(self,cr,w,h,n=3,dark=False):
        col=(0.11,0.07,0.17) if dark else (0.18,0.12,0.26)
        for cl in self.clouds[:n]:
            cr.set_source_rgba(*col,0.55)
            cw,cx,cy=cl["w"],cl["x"],cl["y"]; ch=cw*0.42
            cr.arc(cx+cw*0.2,cy+ch*0.5,ch*0.55,0,math.pi*2); cr.fill()
            cr.arc(cx+cw*0.5,cy+ch*0.3,ch*0.65,0,math.pi*2); cr.fill()
            cr.arc(cx+cw*0.8,cy+ch*0.5,ch*0.48,0,math.pi*2); cr.fill()
            cr.rectangle(cx+cw*0.1,cy+ch*0.4,cw*0.8,ch*0.6); cr.fill()

    def _fog_draw(self,cr,w,h):
        for f in self.fog:
            cr.set_source_rgba(0.2,0.15,0.25,f["op"]); cr.rectangle(f["x"]-60,f["y"],w+120,28); cr.fill()


class NyxusWeather(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.weather")
        self._particles = Particles()
        self._city = "LOCATING..."; self._temp=None; self._feels=None
        self._cond="CLEAR"; self._is_day=True; self._wind=None
        self._humidity=None; self._forecast=[]; self._err=""
        self._lat=None; self._lon=None
        self._anim_t = 0.0

    def do_activate(self):
        p=Gtk.CssProvider(); p.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(),p,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        self.win=Gtk.ApplicationWindow(application=self,title="NYXUS Weather")
        self.win.set_default_size(380,580); self.win.set_resizable(False)
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)

        # Animated scene
        self._scene=Gtk.DrawingArea()
        self._scene.set_size_request(380,220)
        self._scene.set_draw_func(self._draw_scene,None)
        root.append(self._scene)

        # Neon data panel (cairo-drawn)
        self._panel=Gtk.DrawingArea()
        self._panel.set_size_request(380,200)
        self._panel.set_draw_func(self._draw_panel,None)
        root.append(self._panel)

        # Search bar
        search=Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,spacing=6)
        search.set_margin_top(4);search.set_margin_start(14);search.set_margin_end(14)
        self._search=Gtk.Entry(); self._search.add_css_class("search-entry")
        self._search.set_placeholder_text("Enter city name...")
        self._search.set_hexpand(True)
        self._search.connect("activate",lambda *_:self._on_search())
        search.append(self._search)
        go=Gtk.Button(label="GO"); go.add_css_class("go-btn")
        go.connect("clicked",lambda *_:self._on_search())
        search.append(go)
        root.append(search)
        self._err_lbl=Gtk.Label(label="")
        self._err_lbl.add_css_class("err-lbl")
        self._err_lbl.set_halign(Gtk.Align.START)
        self._err_lbl.set_margin_start(14)
        root.append(self._err_lbl)

        # Forecast panel (cairo)
        self._fc_area=Gtk.DrawingArea()
        self._fc_area.set_size_request(380,90)
        self._fc_area.set_draw_func(self._draw_forecast,None)
        root.append(self._fc_area)

        GLib.timeout_add(50,self._animate)
        GLib.timeout_add_seconds(600,self._refresh)
        threading.Thread(target=self._geoip_locate,daemon=True).start()
        self.win.present()

    def _animate(self):
        self._anim_t += 0.04
        W=self._scene.get_width() or 380
        H=self._scene.get_height() or 220
        self._particles.step(W,H)
        self._scene.queue_draw()
        self._panel.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _draw_scene(self,area,cr,W,H,_):
        self._particles.draw(cr,W,H)
        # Dot-grid overlay
        cr.set_source_rgba(0.28,0.07,0.50,0.08)
        for gx in range(0,W+24,24):
            for gy in range(0,H+24,24):
                cr.arc(gx,gy,0.9,0,math.pi*2); cr.fill()
        # Location + system badge
        glow_text(cr,14,H-36,self._city,*C_PINK,size=18,bold=True)
        badge="[DAY]" if self._is_day else "[NIGHT]"
        cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(10)
        cr.set_source_rgba(*C_BLUE,0.7); cr.move_to(14,H-18); cr.show_text(f"{badge} SYS.ONLINE")

    def _draw_panel(self,area,cr,W,H,_):
        # Panel background
        cr.set_source_rgb(0.012,0.008,0.024); cr.rectangle(0,0,W,H); cr.fill()
        # Dot grid
        cr.set_source_rgba(0.28,0.07,0.50,0.10)
        for gx in range(0,W+24,24):
            for gy in range(0,H+24,24):
                cr.arc(gx,gy,0.9,0,math.pi*2); cr.fill()

        if self._temp is None:
            glow_text(cr,W//2-60,H//2,"LOCATING...",*C_PURPLE,size=16,bold=True)
            return

        # Big temperature
        temp_txt=f"{self._temp}°F"
        cr.select_font_face("JetBrains Mono",0,1); cr.set_font_size(58)
        ext=cr.text_extents(temp_txt)
        glow_text(cr,14,-ext.y_bearing+8,temp_txt,*C_PINK,size=58,bold=True)

        # Condition badge (tilted card)
        draw_neon_card(cr,W-80,50,130,32,C_GREEN,-2.0,0.08)
        cr.save(); cr.translate(W-80,50); cr.rotate(math.radians(-2.0))
        cond_lbl=LABELS.get(self._cond,self._cond)
        cr.select_font_face("JetBrains Mono",0,1); cr.set_font_size(11)
        ext2=cr.text_extents(cond_lbl)
        cr.set_source_rgba(*C_GREEN,1.0)
        cr.move_to(-ext2.width/2-ext2.x_bearing, -ext2.height/2-ext2.y_bearing+2)
        cr.show_text(cond_lbl)
        cr.restore()

        # Feels like
        cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(11)
        cr.set_source_rgba(0.91,0.88,0.96,0.6)
        cr.move_to(14,80); cr.show_text(f"FEELS_LIKE: {self._feels}°F")

        # Stat cards (wind + humidity) — tilted neon cards
        if self._wind is not None:
            draw_neon_card(cr, 100, 128, 158, 52, C_ORANGE, -2.5, 0.09)
            cr.save(); cr.translate(100,128); cr.rotate(math.radians(-2.5))
            cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
            cr.set_source_rgba(0.91,0.88,0.96,0.5)
            cr.move_to(-50,-14); cr.show_text("WIND_SPD")
            glow_text(cr,-50,6,f"{self._wind} MPH",*C_ORANGE,size=16,bold=True)
            cr.restore()

        if self._humidity is not None:
            draw_neon_card(cr, 280, 128, 158, 52, C_BLUE, 2.5, 0.09)
            cr.save(); cr.translate(280,128); cr.rotate(math.radians(2.5))
            cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(9)
            cr.set_source_rgba(0.91,0.88,0.96,0.5)
            cr.move_to(-50,-14); cr.show_text("HUMIDITY")
            glow_text(cr,-50,6,f"{self._humidity}%",*C_BLUE,size=16,bold=True)
            cr.restore()

    def _draw_forecast(self,area,cr,W,H,_):
        # Forecast panel bg
        cr.set_source_rgba(0.012,0.008,0.024,0.95)
        cr.rectangle(0,0,W,H); cr.fill()
        # Border top
        cr.set_source_rgba(*C_PURPLE,0.25); cr.set_line_width(1)
        cr.move_to(0,0); cr.line_to(W,0); cr.stroke()
        # Dot grid
        cr.set_source_rgba(0.28,0.07,0.50,0.08)
        for gx in range(0,W+24,24):
            for gy in range(0,H+24,24):
                cr.arc(gx,gy,0.9,0,math.pi*2); cr.fill()
        # Header
        glow_text(cr,14,22,"FORECAST_5D",*C_PURPLE,size=10,bold=True)
        cr.set_source_rgba(*C_PURPLE,0.25); cr.set_line_width(1)
        cr.move_to(0,30); cr.line_to(W,30); cr.stroke()

        if not self._forecast: return
        n = len(self._forecast)
        col_w = W / n
        for i, fc in enumerate(self._forecast[:5]):
            cx = col_w*i + col_w/2
            # Day name
            cr.select_font_face("JetBrains Mono",0,1); cr.set_font_size(10)
            cr.set_source_rgba(0.91,0.88,0.96,0.8)
            ext=cr.text_extents(fc["day"])
            cr.move_to(cx-ext.width/2-ext.x_bearing,46); cr.show_text(fc["day"])
            # Icon
            cr.select_font_face("",0,0); cr.set_font_size(16)
            icon=ICONS.get(fc["cond"],"—")
            ext2=cr.text_extents(icon)
            cr.set_source_rgba(*C_GREEN,0.9)
            cr.move_to(cx-ext2.width/2-ext2.x_bearing,64); cr.show_text(icon)
            # Hi/lo
            hi=f"{fc['hi']}°" if fc.get("hi") is not None else "—"
            lo=f"{fc['lo']}°" if fc.get("lo") is not None else "—"
            cr.select_font_face("JetBrains Mono",0,1); cr.set_font_size(10)
            ext3=cr.text_extents(hi)
            cr.set_source_rgba(*C_PINK,0.9)
            cr.move_to(cx-ext3.width/2-ext3.x_bearing,80); cr.show_text(hi)
            cr.select_font_face("JetBrains Mono",0,0); cr.set_font_size(10)
            ext4=cr.text_extents(lo)
            cr.set_source_rgba(*C_BLUE,0.8)
            cr.move_to(cx-ext4.width/2-ext4.x_bearing,H-4); cr.show_text(lo)

    # ── Fetch / update ──────────────────────────────────────────────────────────
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
                self._city=cfg.get("city","CONFIGURED").upper()
                self._fetch_weather(); return
        except Exception: pass
        GLib.idle_add(lambda:(self._panel.queue_draw(),self._scene.queue_draw(),None)[2])

    def _fetch_weather(self):
        url=(f"https://api.open-meteo.com/v1/forecast?latitude={self._lat}&longitude={self._lon}"
             f"&current=temperature_2m,apparent_temperature,is_day,weather_code,wind_speed_10m,relative_humidity_2m"
             f"&daily=temperature_2m_max,temperature_2m_min,weather_code"
             f"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=5")
        try:
            with urlopen(url,timeout=10) as r: d=json.loads(r.read())
            cur=d.get("current",{}); daily=d.get("daily",{})
            self._temp     = round(cur.get("temperature_2m",0))
            self._feels    = round(cur.get("apparent_temperature",0))
            self._is_day   = bool(cur.get("is_day",1))
            self._wind     = round(cur.get("wind_speed_10m",0))
            self._humidity = cur.get("relative_humidity_2m",0)
            self._cond     = WMO.get(cur.get("weather_code",0),"CLEAR")
            times=daily.get("time",[])
            self._forecast=[{
                "day":datetime.strptime(times[i],"%Y-%m-%d").strftime("%a").upper(),
                "hi":round(daily["temperature_2m_max"][i]) if daily.get("temperature_2m_max") else None,
                "lo":round(daily["temperature_2m_min"][i]) if daily.get("temperature_2m_min") else None,
                "cond":WMO.get(daily["weather_code"][i],"CLEAR") if daily.get("weather_code") else "CLEAR",
            } for i in range(min(5,len(times)))]
            self._err=""
            GLib.idle_add(self._update_ui)
        except Exception as e:
            self._err=str(e)[:50]; GLib.idle_add(self._update_ui)

    def _refresh(self):
        if self._lat: threading.Thread(target=self._fetch_weather,daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _on_search(self):
        city=self._search.get_text().strip()
        if not city: return
        self._err_lbl.set_text("SCANNING...")
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
                GLib.idle_add(lambda:(self._err_lbl.set_text(f"NOT FOUND: {city}"),None)[1])
        except Exception as e:
            GLib.idle_add(lambda:(self._err_lbl.set_text(str(e)[:50]),None)[1])

    def _update_ui(self):
        self._err_lbl.set_text(self._err)
        self._particles.condition=self._cond
        self._particles.is_day=self._is_day
        self._panel.queue_draw()
        self._fc_area.queue_draw()
        self._scene.queue_draw()
        return GLib.SOURCE_REMOVE


if __name__ == "__main__":
    NyxusWeather().run(None)
