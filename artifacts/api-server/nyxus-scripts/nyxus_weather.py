#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Weather — Native GTK4 Animated Weather Widget                 ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED       ║
# ╚══════════════════════════════════════════════════════════════════════╝
# Install:  pacman -S python-gobject gtk4
# Run:      python3 ~/.nyxus/nyxus_weather.py

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
    0: "CLEAR", 1: "PARTLY_CLOUDY", 2: "PARTLY_CLOUDY", 3: "CLOUDY",
    45: "FOG", 48: "FOG",
    51: "RAIN", 53: "RAIN", 55: "RAIN",
    61: "RAIN", 63: "RAIN", 65: "RAIN",
    71: "SNOW", 73: "SNOW", 75: "SNOW",
    80: "RAIN", 81: "RAIN", 82: "RAIN", 85: "SNOW", 86: "SNOW",
    95: "STORM", 96: "STORM", 99: "STORM",
}
LABELS = {"CLEAR":"CLEAR","PARTLY_CLOUDY":"PARTLY CLOUDY","CLOUDY":"OVERCAST",
          "FOG":"FOG","RAIN":"RAIN","SNOW":"SNOW","STORM":"THUNDERSTORM"}
ICONS  = {"CLEAR":"☀","PARTLY_CLOUDY":"⛅","CLOUDY":"☁","RAIN":"🌧","SNOW":"❄","STORM":"⛈","FOG":"🌫"}

CSS = b"""
* { font-family: 'JetBrains Mono', 'Monospace', monospace; }
window { background-color: #030206; color: #e8e0f5; }
.city-lbl { color: #ff00ff; font-size: 16px; font-weight: bold; letter-spacing: 2px; }
.temp-lbl { color: #e8e0f5; font-size: 50px; font-weight: bold; }
.feels-lbl { color: #7060a0; font-size: 11px; }
.cond-lbl { color: #ffff00; font-size: 12px; font-weight: bold; letter-spacing: 3px; }
.pill { color: #0088ff; font-size: 11px; padding: 2px 8px;
        border: 1px solid rgba(0,136,255,0.3); border-radius: 2px; margin: 2px; }
.fc-day  { color: #7060a0; font-size: 10px; }
.fc-icon { font-size: 18px; }
.fc-hi   { color: #ff00ff; font-size: 11px; font-weight: bold; }
.fc-lo   { color: #7060a0; font-size: 11px; }
.search-entry {
    background-color: #07030f;
    border: 1px solid rgba(204,0,255,0.3);
    color: #e8e0f5; border-radius: 2px;
    padding: 5px 10px; font-size: 11px; box-shadow: none;
}
.search-entry text { background-color: transparent; }
.go-btn {
    background-color: transparent; color: #ff00ff;
    border: 1px solid #ff00ff; border-radius: 2px;
    padding: 4px 12px; font-size: 11px; font-weight: bold;
}
.go-btn:hover { background-color: rgba(255,0,255,0.12); }
.err-lbl { color: #ff5500; font-size: 11px; }
"""


class Particles:
    def __init__(self):
        self.t = 0.0
        self.condition = "CLEAR"
        self.is_day = True
        self.lightning_timer = random.uniform(4, 8)
        self.lightning_flash = 0.0
        self.sun_angle = 0.0
        self.stars = [{"x": random.uniform(0,380), "y": random.uniform(0,220),
                       "r": random.uniform(0.8,2.0), "phase": random.uniform(0, math.pi*2)} for _ in range(80)]
        self.rain = [{"x": random.uniform(0,380), "y": random.uniform(-20,220),
                      "speed": random.uniform(5,10), "len": random.uniform(8,18),
                      "op": random.uniform(0.3,0.8)} for _ in range(110)]
        self.snow = [{"x": random.uniform(0,380), "y": random.uniform(-10,220),
                      "vx": random.uniform(-0.3,0.3), "vy": random.uniform(0.4,1.2),
                      "r": random.uniform(2,5), "op": random.uniform(0.5,1.0),
                      "ph": random.uniform(0,math.pi*2)} for _ in range(65)]
        self.clouds = [{"x": random.uniform(-80,380), "y": random.uniform(20,100),
                        "w": random.uniform(90,160), "spd": random.uniform(0.08,0.25)} for _ in range(5)]
        self.fog = [{"x": 0, "y": random.uniform(10,200), "op": random.uniform(0.05,0.12),
                     "spd": random.uniform(0.05,0.18)} for _ in range(5)]

    def step(self, width, height, dt=0.05):
        self.t += dt
        c = self.condition
        if c in ("RAIN", "STORM"):
            for p in self.rain:
                p["y"] += p["speed"]; p["x"] -= p["speed"] * 0.12
                if p["y"] > height or p["x"] < -5:
                    p["y"] = random.uniform(-20, 0); p["x"] = random.uniform(0, width)
        if c == "SNOW":
            for p in self.snow:
                p["y"] += p["vy"]
                p["x"] += p["vx"] + math.sin(self.t * 0.6 + p["ph"]) * 0.35
                if p["y"] > height: p["y"] = -8; p["x"] = random.uniform(0, width)
                if p["x"] < -5: p["x"] = width
                if p["x"] > width + 5: p["x"] = 0
        if c == "STORM":
            self.lightning_timer -= dt
            if self.lightning_flash > 0:
                self.lightning_flash = max(0, self.lightning_flash - dt * 3)
            elif self.lightning_timer <= 0:
                self.lightning_flash = 1.0
                self.lightning_timer = random.uniform(4, 9)
        if c in ("CLOUDY", "PARTLY_CLOUDY"):
            for cl in self.clouds:
                cl["x"] += cl["spd"]
                if cl["x"] > width + cl["w"]: cl["x"] = -cl["w"]
        if c == "FOG":
            for f in self.fog:
                f["x"] += f["spd"]
                if f["x"] > width + 80: f["x"] = -80
        self.sun_angle += dt * 0.12

    def draw(self, cr, width, height):
        self._sky(cr, width, height)
        c = self.condition; day = self.is_day
        if c == "CLEAR":
            if day: self._sun(cr, width, height)
            else:   self._stars(cr, width, height); self._moon(cr, width, height)
        elif c == "PARTLY_CLOUDY":
            if day: self._sun(cr, width, height)
            else:   self._stars(cr, width, height); self._moon(cr, width, height)
            self._clouds(cr, width, height, 2)
        elif c == "CLOUDY":
            self._clouds(cr, width, height, 4)
        elif c == "RAIN":
            self._clouds(cr, width, height, 3, dark=True)
            self._rain(cr, width, height)
        elif c == "SNOW":
            self._clouds(cr, width, height, 2)
            self._snow_draw(cr, width, height)
        elif c == "STORM":
            if self.lightning_flash > 0:
                cr.set_source_rgba(1, 1, 0.9, self.lightning_flash * 0.35)
                cr.rectangle(0, 0, width, height); cr.fill()
            self._clouds(cr, width, height, 4, dark=True)
            self._rain(cr, width, height)
        elif c == "FOG":
            self._fog_draw(cr, width, height)

    def _sky(self, cr, w, h):
        c = self.condition; day = self.is_day
        skies = {
            ("CLEAR", True):  ((0.10,0.04,0.01), (0.01,0.01,0.02)),
            ("CLEAR", False): ((0.02,0.01,0.07), (0.01,0.01,0.02)),
            ("RAIN",  True):  ((0.02,0.03,0.07), (0.01,0.01,0.02)),
            ("STORM", True):  ((0.01,0.01,0.05), (0.01,0.01,0.02)),
            ("SNOW",  True):  ((0.04,0.02,0.08), (0.01,0.01,0.02)),
            ("FOG",   True):  ((0.05,0.04,0.07), (0.02,0.01,0.03)),
        }
        key = (c if c in ("RAIN","STORM","SNOW","FOG") else "CLEAR", day)
        top, bot = skies.get(key, ((0.03,0.02,0.06),(0.01,0.01,0.02)))
        for i in range(h):
            t = i / h
            r = top[0] + (bot[0]-top[0])*t
            g = top[1] + (bot[1]-top[1])*t
            b = top[2] + (bot[2]-top[2])*t
            cr.set_source_rgb(r, g, b)
            cr.rectangle(0, i, w, 1); cr.fill()

    def _sun(self, cr, w, h):
        cx, cy = w*0.72, h*0.28
        cr.set_source_rgba(1,0.5,0,0.07); cr.arc(cx,cy,55,0,math.pi*2); cr.fill()
        cr.set_source_rgba(1,0.65,0.1,0.14); cr.arc(cx,cy,40,0,math.pi*2); cr.fill()
        for i in range(12):
            a = self.sun_angle + i*math.pi*2/12
            ri, ro = 24, 37 + 5*math.sin(self.t*2+i)
            cr.set_source_rgba(1, 0.65, 0.1, 0.65)
            cr.set_line_width(2)
            cr.move_to(cx+math.cos(a)*ri, cy+math.sin(a)*ri)
            cr.line_to(cx+math.cos(a)*ro, cy+math.sin(a)*ro); cr.stroke()
        cr.set_source_rgba(1,0.88,0.3,1); cr.arc(cx,cy,22,0,math.pi*2); cr.fill()

    def _moon(self, cr, w, h):
        cx, cy = w*0.72, h*0.2
        cr.set_source_rgba(0,0.5,1,0.07); cr.arc(cx,cy,26,0,math.pi*2); cr.fill()
        cr.set_source_rgba(0.85,0.9,1,0.92); cr.arc(cx,cy,17,0,math.pi*2); cr.fill()
        cr.set_source_rgb(0.02,0.01,0.07); cr.arc(cx+6,cy-4,13,0,math.pi*2); cr.fill()

    def _stars(self, cr, w, h):
        for s in self.stars:
            op = s["r"]/2 * (0.5 + 0.5*math.sin(self.t*1.8+s["phase"]))
            cr.set_source_rgba(0.9,0.85,1,op)
            cr.arc(s["x"],s["y"],s["r"]*0.6,0,math.pi*2); cr.fill()

    def _rain(self, cr, w, h):
        for p in self.rain:
            cr.set_source_rgba(0.1,0.5,1,p["op"])
            cr.set_line_width(1.0)
            cr.move_to(p["x"], p["y"])
            cr.line_to(p["x"]-p["len"]*0.13, p["y"]-p["len"]); cr.stroke()

    def _snow_draw(self, cr, w, h):
        for p in self.snow:
            cr.set_source_rgba(0.85,0.92,1,p["op"])
            cr.arc(p["x"],p["y"],p["r"],0,math.pi*2); cr.fill()

    def _clouds(self, cr, w, h, n=3, dark=False):
        col = (0.11,0.07,0.17) if dark else (0.18,0.12,0.26)
        for cl in self.clouds[:n]:
            cr.set_source_rgba(*col, 0.55)
            cw, cx, cy = cl["w"], cl["x"], cl["y"]
            ch = cw*0.42
            cr.arc(cx+cw*0.2, cy+ch*0.5, ch*0.55, 0, math.pi*2); cr.fill()
            cr.arc(cx+cw*0.5, cy+ch*0.3, ch*0.65, 0, math.pi*2); cr.fill()
            cr.arc(cx+cw*0.8, cy+ch*0.5, ch*0.48, 0, math.pi*2); cr.fill()
            cr.rectangle(cx+cw*0.1, cy+ch*0.4, cw*0.8, ch*0.6); cr.fill()

    def _fog_draw(self, cr, w, h):
        for f in self.fog:
            cr.set_source_rgba(0.2,0.15,0.25, f["op"])
            cr.rectangle(f["x"]-60, f["y"], w+120, 28); cr.fill()


class NyxusWeather(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.weather")
        self._particles  = Particles()
        self._city       = "LOCATING..."
        self._temp       = None
        self._feels      = None
        self._cond       = "CLEAR"
        self._is_day     = True
        self._wind       = None
        self._humidity   = None
        self._forecast   = []
        self._err        = ""
        self._lat        = None
        self._lon        = None

    def do_activate(self):
        p = Gtk.CssProvider(); p.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), p, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self, title="NYXUS Weather")
        self.win.set_default_size(380, 560); self.win.set_resizable(False)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)

        # Scene canvas
        self._scene = Gtk.DrawingArea()
        self._scene.set_size_request(380, 230)
        self._scene.set_draw_func(self._draw_scene, None)
        root.append(self._scene)

        # Data panel
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        panel.set_margin_top(8); panel.set_margin_bottom(6)
        panel.set_margin_start(14); panel.set_margin_end(14)
        root.append(panel)

        self._city_lbl = Gtk.Label(label="LOCATING...")
        self._city_lbl.add_css_class("city-lbl"); self._city_lbl.set_halign(Gtk.Align.START)
        panel.append(self._city_lbl)

        temp_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)
        temp_row.set_valign(Gtk.Align.CENTER)
        self._temp_lbl = Gtk.Label(label="--°")
        self._temp_lbl.add_css_class("temp-lbl")
        temp_row.append(self._temp_lbl)
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        right.set_valign(Gtk.Align.CENTER)
        self._cond_lbl = Gtk.Label(label="---")
        self._cond_lbl.add_css_class("cond-lbl"); self._cond_lbl.set_halign(Gtk.Align.START)
        right.append(self._cond_lbl)
        self._feels_lbl = Gtk.Label(label="Feels like --°")
        self._feels_lbl.add_css_class("feels-lbl"); self._feels_lbl.set_halign(Gtk.Align.START)
        right.append(self._feels_lbl)
        temp_row.append(right)
        panel.append(temp_row)

        pills = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._wind_lbl = Gtk.Label(label="↑ -- mph"); self._wind_lbl.add_css_class("pill")
        self._hum_lbl  = Gtk.Label(label="💧 --%");   self._hum_lbl.add_css_class("pill")
        pills.append(self._wind_lbl); pills.append(self._hum_lbl)
        panel.append(pills)

        # Search
        search = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        search.set_margin_top(2)
        self._search = Gtk.Entry(); self._search.add_css_class("search-entry")
        self._search.set_placeholder_text("Enter city name...")
        self._search.set_hexpand(True)
        self._search.connect("activate", lambda *_: self._on_search())
        search.append(self._search)
        go = Gtk.Button(label="GO"); go.add_css_class("go-btn")
        go.connect("clicked", lambda *_: self._on_search())
        search.append(go)
        panel.append(search)

        self._err_lbl = Gtk.Label(label="")
        self._err_lbl.add_css_class("err-lbl"); self._err_lbl.set_halign(Gtk.Align.START)
        panel.append(self._err_lbl)

        sep = Gtk.Separator(); sep.set_margin_top(4); sep.set_margin_bottom(4)
        panel.append(sep)

        self._fc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._fc_box.set_homogeneous(True)
        panel.append(self._fc_box)

        GLib.timeout_add(50, self._animate)
        GLib.timeout_add_seconds(600, self._refresh)
        threading.Thread(target=self._geoip_locate, daemon=True).start()
        self.win.present()

    def _animate(self):
        w = self._scene.get_width() or 380
        h = self._scene.get_height() or 230
        self._particles.step(w, h)
        self._scene.queue_draw()
        return GLib.SOURCE_CONTINUE

    def _draw_scene(self, area, cr, width, height, _):
        self._particles.draw(cr, width, height)

    # ── Location + weather fetch ────────────────────────────────────────────────
    def _geoip_locate(self):
        try:
            with urlopen("http://ip-api.com/json/?fields=lat,lon,city,status", timeout=6) as r:
                geo = json.loads(r.read())
            if geo.get("status") == "success":
                self._lat = geo["lat"]; self._lon = geo["lon"]
                self._city = geo.get("city","").upper()
                self._fetch_weather(); return
        except Exception: pass
        try:
            with open(CONFIG_FILE) as f:
                cfg = json.load(f)
            if cfg.get("lat"):
                self._lat = cfg["lat"]; self._lon = cfg["lon"]
                self._city = cfg.get("city","CONFIGURED").upper()
                self._fetch_weather(); return
        except Exception: pass
        GLib.idle_add(lambda: (self._city_lbl.set_text("ENTER CITY BELOW"), GLib.SOURCE_REMOVE)[1])

    def _fetch_weather(self):
        url = (f"https://api.open-meteo.com/v1/forecast?latitude={self._lat}&longitude={self._lon}"
               f"&current=temperature_2m,apparent_temperature,is_day,weather_code,wind_speed_10m,relative_humidity_2m"
               f"&daily=temperature_2m_max,temperature_2m_min,weather_code"
               f"&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=auto&forecast_days=5")
        try:
            with urlopen(url, timeout=10) as r:
                d = json.loads(r.read())
            cur = d.get("current", {}); daily = d.get("daily", {})
            self._temp     = round(cur.get("temperature_2m", 0))
            self._feels    = round(cur.get("apparent_temperature", 0))
            self._is_day   = bool(cur.get("is_day", 1))
            self._wind     = round(cur.get("wind_speed_10m", 0))
            self._humidity = cur.get("relative_humidity_2m", 0)
            self._cond     = WMO.get(cur.get("weather_code", 0), "CLEAR")
            self._forecast = []
            times = daily.get("time", [])
            for i in range(min(5, len(times))):
                self._forecast.append({
                    "day": datetime.strptime(times[i], "%Y-%m-%d").strftime("%a").upper(),
                    "hi": round(daily["temperature_2m_max"][i]) if daily.get("temperature_2m_max") else None,
                    "lo": round(daily["temperature_2m_min"][i]) if daily.get("temperature_2m_min") else None,
                    "cond": WMO.get(daily["weather_code"][i], "CLEAR") if daily.get("weather_code") else "CLEAR",
                })
            self._err = ""
            GLib.idle_add(self._update_ui)
        except Exception as e:
            self._err = str(e)[:50]
            GLib.idle_add(self._update_ui)

    def _refresh(self):
        if self._lat: threading.Thread(target=self._fetch_weather, daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _on_search(self):
        city = self._search.get_text().strip()
        if not city: return
        self._err_lbl.set_text("Searching...")
        threading.Thread(target=self._geocode, args=(city,), daemon=True).start()

    def _geocode(self, city):
        url = f"https://nominatim.openstreetmap.org/search?q={quote(city)}&format=json&limit=1"
        try:
            req = Request(url, headers={"User-Agent": "NYXUS-Weather/1.0"})
            with urlopen(req, timeout=8) as r:
                res = json.loads(r.read())
            if res:
                self._lat = float(res[0]["lat"]); self._lon = float(res[0]["lon"])
                self._city = city.upper()
                with open(CONFIG_FILE, "w") as f:
                    json.dump({"city": self._city, "lat": self._lat, "lon": self._lon}, f)
                self._fetch_weather()
            else:
                GLib.idle_add(lambda: (self._err_lbl.set_text(f"City not found: {city}"), None))
        except Exception as e:
            GLib.idle_add(lambda: (self._err_lbl.set_text(str(e)[:50]), None))

    def _update_ui(self):
        self._city_lbl.set_text(self._city)
        if self._temp is not None:
            self._temp_lbl.set_text(f"{self._temp}°F")
            self._feels_lbl.set_text(f"Feels like {self._feels}°F")
            self._wind_lbl.set_text(f"↑ {self._wind} mph")
            self._hum_lbl.set_text(f"💧 {self._humidity}%")
            lbl = LABELS.get(self._cond, self._cond)
            if not self._is_day and self._cond == "CLEAR": lbl = "CLEAR NIGHT"
            self._cond_lbl.set_text(lbl)
        self._err_lbl.set_text(self._err)
        self._particles.condition = self._cond
        self._particles.is_day = self._is_day

        c = self._fc_box.get_first_child()
        while c:
            n = c.get_next_sibling(); self._fc_box.remove(c); c = n
        for fc in self._forecast:
            col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            col.set_halign(Gtk.Align.CENTER)
            for text, css in [(fc["day"],"fc-day"),(ICONS.get(fc["cond"],"—"),"fc-icon"),
                               (f"{fc['hi']}°" if fc["hi"] else "—","fc-hi"),
                               (f"{fc['lo']}°" if fc["lo"] else "—","fc-lo")]:
                lbl = Gtk.Label(label=text); lbl.add_css_class(css)
                col.append(lbl)
            self._fc_box.append(col)
        return GLib.SOURCE_REMOVE


if __name__ == "__main__":
    NyxusWeather().run(None)
