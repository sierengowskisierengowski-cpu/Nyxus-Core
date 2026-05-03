#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Control — Hardware Control Center  v2                                ║
# ║  Fan · Thermal · Profiles · RGB · Power · Processes                         ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-CTL-2026-SIERENGOWSKI-LOCKED              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

__nyxid__ = "4e59582d4a35572d323032362d53494552454e474f57534b492d4c4f434b4544"

def _nyx_integrity():
    try:
        _s = open(__file__, encoding="utf-8").read()
        assert "SIERENGOWSKI" in _s, "NYXUS: tamper detected"
    except (OSError, AssertionError) as _e:
        import sys as _sys; print(f"NYXUS SECURITY: {_e}", file=_sys.stderr)
_nyx_integrity()


import gi, sys, os, math, json, time, threading, subprocess, random, signal
from pathlib import Path
from collections import deque
from datetime import datetime, timedelta
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio, Pango

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

# ── Paths ──────────────────────────────────────────────────────────────────────
HOME         = Path.home()
NYXUS_DIR    = HOME / ".nyxus"
HW_PROFILE   = NYXUS_DIR / "hw_profile.json"
SYS_PROFILES = NYXUS_DIR / "system_profiles.json"
NYXUS_DIR.mkdir(exist_ok=True)

# ── NYXUS palette ──────────────────────────────────────────────────────────────
C_BG     = (0.031, 0.031, 0.055)
C_PANEL  = (0.052, 0.052, 0.100)
C_TEXT   = (0.91,  0.88,  0.96 )
C_DIM    = (0.44,  0.376, 0.627)
C_PINK   = (1.00,  0.00,  1.00 )
C_PURPLE = (0.80,  0.00,  1.00 )
C_BLUE   = (0.00,  0.53,  1.00 )
C_GREEN  = (0.22,  1.00,  0.08 )
C_YELLOW = (1.00,  1.00,  0.00 )
C_ORANGE = (1.00,  0.33,  0.00 )
C_RED    = (1.00,  0.12,  0.12 )
PALETTE  = [C_PINK, C_PURPLE, C_BLUE, C_GREEN, C_YELLOW, C_ORANGE]
HIST     = 360

PAGES = [
    ("OVERVIEW",  C_PINK  ),
    ("FANS",      C_BLUE  ),
    ("THERMAL",   C_ORANGE),
    ("PROFILES",  C_PURPLE),
    ("RGB",       C_GREEN ),
    ("POWER",     C_YELLOW),
    ("PROCESSES", C_RED   ),
]

# ══════════════════════════════════════════════════════════════════════════════
#  Hardware detection
# ══════════════════════════════════════════════════════════════════════════════
def _read(path, default=""):
    try:   return Path(path).read_text().strip()
    except: return default

def _write_priv(path, value):
    try:
        Path(path).write_text(value + "\n")
        return True, ""
    except PermissionError:
        try:
            r = subprocess.run(["pkexec","tee",path],
                               input=(value+"\n").encode(),
                               capture_output=True, timeout=20)
            return (True,"") if r.returncode==0 else (False, r.stderr.decode().strip())
        except Exception as e: return False, str(e)
    except Exception as e: return False, str(e)

def _detect_hwmon():
    devs = []
    root = Path("/sys/class/hwmon")
    if not root.exists(): return devs
    for hwmon in sorted(root.iterdir()):
        name = _read(str(hwmon/"name"), hwmon.name)
        temps, fans, pwms = [], [], []
        for f in sorted(hwmon.iterdir()):
            fn = f.name
            if fn.startswith("temp") and fn.endswith("_input"):
                idx = fn[4:-6]
                lbl = _read(str(hwmon/f"temp{idx}_label"), f"Temp {idx}")
                crit= _read(str(hwmon/f"temp{idx}_crit"), "")
                mx  = _read(str(hwmon/f"temp{idx}_max"), "")
                temps.append({"idx":idx,"label":lbl,"path":str(f),
                              "crit":int(crit)//1000 if crit.isdigit() else None,
                              "max": int(mx)//1000   if mx.isdigit()   else None})
            elif fn.startswith("fan") and fn.endswith("_input"):
                idx = fn[3:-6]
                lbl = _read(str(hwmon/f"fan{idx}_label"), f"Fan {idx}")
                mn  = _read(str(hwmon/f"fan{idx}_min"), "0")
                fans.append({"idx":idx,"label":lbl,"path":str(f),
                             "min_rpm":int(mn) if mn.isdigit() else 0})
            elif fn.startswith("pwm") and "_" not in fn:
                idx = fn[3:]
                pwms.append({"idx":idx,"path":str(f),
                             "enable_path":str(hwmon/f"pwm{idx}_enable")})
        if temps or fans:
            devs.append({"name":name,"path":str(hwmon),
                         "temps":temps,"fans":fans,"pwms":pwms})
    return devs

def _detect_cpu():
    model = ""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    model = line.split(":",1)[1].strip(); break
    except: pass
    gov_p  = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    boost_p= "/sys/devices/system/cpu/cpufreq/boost"
    import platform
    return {
        "model":    model or platform.processor() or "Unknown CPU",
        "cores":    os.cpu_count() or 1,
        "governor": _read(gov_p,"unknown"),
        "governors": _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors","").split()
                     or ["powersave","schedutil","performance"],
        "boost_path": boost_p,
        "boost_supported": Path(boost_p).exists(),
        "boost": _read(boost_p,"0") == "1",
    }

def _detect_gpu():
    # Column order: name, temperature.gpu, power.draw, power.limit,
    #               memory.used, memory.total, utilization.gpu
    try:
        out = subprocess.check_output(
            ["nvidia-smi",
             "--query-gpu=name,temperature.gpu,power.draw,power.limit,"
             "memory.used,memory.total,utilization.gpu",
             "--format=csv,noheader,nounits"],
            timeout=5, stderr=subprocess.DEVNULL).decode().strip()
        p = [x.strip() for x in out.split(",")]
        if len(p) >= 7:
            return {"vendor":"nvidia","name":p[0],"detected":True,
                    "temp":      _safe_float(p[1]),
                    "power_draw":_safe_float(p[2]),
                    "power_limit":_safe_float(p[3]),
                    "mem_used":  _safe_int(p[4]),
                    "mem_total": _safe_int(p[5]),
                    "util":      _safe_float(p[6])}
    except Exception:
        pass
    # AMD fallback
    for drm in Path("/sys/class/drm").glob("card*/device"):
        if _read(str(drm/"vendor")) == "0x1002":
            return {"vendor":"amd","name":"AMD GPU","detected":True}
    return {"vendor":"none","name":"No GPU","detected":False}

def _safe_float(s, default=0.0):
    try:    return float(s)
    except: return default

def _safe_int(s, default=0):
    try:    return int(float(s))
    except: return default

def _detect_battery():
    ps = Path("/sys/class/power_supply")
    if not ps.exists(): return None
    for p in ps.iterdir():
        if _read(str(p/"type")) == "Battery":
            pct   = _read(str(p/"capacity"),"0")
            stat  = _read(str(p/"status"),"Unknown")
            clim  = str(p/"charge_control_end_threshold")
            return {"path":str(p),"pct":int(pct) if pct.isdigit() else 0,
                    "status":stat,
                    "charge_limit_path":clim if Path(clim).exists() else None}
    return None

def build_hw_profile():
    dmi   = Path("/sys/class/dmi/id")
    board = (_read(str(dmi/"board_vendor"),"")+" "+_read(str(dmi/"board_name"),"")).strip() \
            or _read(str(dmi/"product_name"),"Unknown Board")
    profile = {"generated":datetime.now().isoformat(),
               "board":board,"cpu":_detect_cpu(),"gpu":_detect_gpu(),
               "battery":_detect_battery(),"hwmon":_detect_hwmon()}
    HW_PROFILE.write_text(json.dumps(profile,indent=2))
    return profile

def load_hw_profile():
    if HW_PROFILE.exists():
        try:
            p = json.loads(HW_PROFILE.read_text())
            # Always re-detect GPU — cached "none" from earlier session is wrong
            if not p.get("gpu", {}).get("detected"):
                p["gpu"] = _detect_gpu()
                HW_PROFILE.write_text(json.dumps(p, indent=2))
            return p
        except: pass
    return build_hw_profile()

# ══════════════════════════════════════════════════════════════════════════════
#  Live data collector
# ══════════════════════════════════════════════════════════════════════════════
class LiveData:
    def __init__(self, hw):
        self.hw        = hw
        self.temps:    dict = {}
        self.fans:     dict = {}
        self.pwms:     dict = {}
        self.governor  = hw.get("cpu",{}).get("governor","unknown")
        self.boost     = hw.get("cpu",{}).get("boost",False)
        self.cpu_freq  = 0.0
        self.cpu_pcts: list = []
        self.mem_used  = 0.0
        self.mem_total = 0.0
        self.gpu:  dict = {}
        self.battery:  dict = {}
        self.procs:    list = []
        self.uptime_s  = 0
        self.temp_hist: dict = {}
        self.fan_hist:  dict = {}
        self.cpu_hist:  deque = deque(maxlen=HIST)
        self.mem_hist:  deque = deque(maxlen=HIST)
        for dev in hw.get("hwmon",[]):
            for t in dev["temps"]:
                k = f"{dev['name']}:{t['label']}"
                self.temp_hist[k] = deque(maxlen=HIST)
            for f in dev["fans"]:
                k = f"{dev['name']}:{f['label']}"
                self.fan_hist[k]  = deque(maxlen=HIST)

    def collect(self):
        # Hwmon temps + fans
        for dev in self.hw.get("hwmon",[]):
            for t in dev["temps"]:
                raw = _read(t["path"],"0")
                try:
                    c = int(raw)/1000.0
                    k = f"{dev['name']}:{t['label']}"
                    self.temps[k] = c; self.temp_hist[k].append(c)
                except: pass
            for f in dev["fans"]:
                raw = _read(f["path"],"0")
                try:
                    rpm = int(raw)
                    k   = f"{dev['name']}:{f['label']}"
                    self.fans[k] = rpm; self.fan_hist[k].append(rpm)
                except: pass
            for p in dev.get("pwms",[]):
                raw = _read(p["path"],"128")
                try: self.pwms[p["path"]] = int(raw)
                except: pass

        # Governor / boost / freq
        self.governor = _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor",
                               self.governor)
        self.boost = _read("/sys/devices/system/cpu/cpufreq/boost","0") == "1"
        try:
            self.cpu_freq = int(_read(
                "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq","0"))/1000.0
        except: pass

        # Per-core CPU %
        try:
            import psutil
            pcts = psutil.cpu_percent(percpu=True)
            self.cpu_pcts = pcts
            avg  = sum(pcts)/len(pcts) if pcts else 0
            self.cpu_hist.append(avg)
            vm   = psutil.virtual_memory()
            self.mem_used  = vm.used  / 1024**3
            self.mem_total = vm.total / 1024**3
            self.mem_hist.append(vm.percent)
            self.uptime_s  = int(time.time() - psutil.boot_time())
        except: pass

        # GPU — same column order as _detect_gpu
        if self.hw.get("gpu",{}).get("vendor") == "nvidia":
            try:
                out = subprocess.check_output(
                    ["nvidia-smi",
                     "--query-gpu=name,temperature.gpu,power.draw,power.limit,"
                     "memory.used,memory.total,utilization.gpu",
                     "--format=csv,noheader,nounits"],
                    timeout=4, stderr=subprocess.DEVNULL).decode().strip()
                p = [x.strip() for x in out.split(",")]
                if len(p) >= 7:
                    self.gpu = {
                        "name":        p[0],
                        "temp":        _safe_float(p[1]),
                        "power_draw":  _safe_float(p[2]),
                        "power_limit": _safe_float(p[3]),
                        "mem_used":    _safe_int(p[4]),
                        "mem_total":   _safe_int(p[5]),
                        "util":        _safe_float(p[6]),
                    }
                    # Also keep hw profile in sync so GPU card shows correct name
                    if not self.hw.get("gpu",{}).get("detected"):
                        self.hw["gpu"] = {"vendor":"nvidia","detected":True,
                                          **self.gpu}
            except Exception:
                pass

        # Battery
        batt = self.hw.get("battery")
        if batt:
            pct  = _read(str(Path(batt["path"])/"capacity"),"0")
            stat = _read(str(Path(batt["path"])/"status"),"Unknown")
            try: self.battery = {"pct":int(pct),"status":stat}
            except: pass

        # Processes
        try:
            import psutil
            procs = []
            for p in sorted(psutil.process_iter(
                    ["pid","name","cpu_percent","memory_percent","nice","status","username"]),
                    key=lambda x: x.info.get("cpu_percent",0) or 0, reverse=True)[:80]:
                try:
                    procs.append({"pid":p.info["pid"],
                                  "name":(p.info["name"] or "")[:28],
                                  "cpu": p.info.get("cpu_percent") or 0.0,
                                  "mem": p.info.get("memory_percent") or 0.0,
                                  "nice":p.info.get("nice") or 0,
                                  "stat":p.info.get("status","")[:4],
                                  "user":(p.info.get("username") or "")[:10]})
                except: pass
            self.procs = procs
        except:
            try:
                out = subprocess.check_output(
                    ["ps","-eo","pid,comm,pcpu,pmem,nice,stat,user",
                     "--sort=-pcpu","--no-headers"],
                    timeout=3, stderr=subprocess.DEVNULL).decode().strip()
                procs = []
                for line in out.splitlines()[:80]:
                    parts = line.split(None, 6)
                    if len(parts) >= 5:
                        try:
                            procs.append({"pid":int(parts[0]),"name":parts[1][:28],
                                          "cpu":float(parts[2]),"mem":float(parts[3]),
                                          "nice":int(parts[4]),
                                          "stat":parts[5][:4] if len(parts)>5 else "",
                                          "user":parts[6][:10] if len(parts)>6 else ""})
                        except: pass
                self.procs = procs
            except: pass

# ══════════════════════════════════════════════════════════════════════════════
#  Profile management
# ══════════════════════════════════════════════════════════════════════════════
def _default_profiles():
    return [
        {"name":"Silent",      "governor":"powersave",  "boost":False,
         "fan_pwm_pct":20,"description":"Quiet & cool — minimal fan noise"},
        {"name":"Balanced",    "governor":"schedutil",  "boost":True,
         "fan_pwm_pct":50,"description":"Smart everyday performance"},
        {"name":"Performance", "governor":"performance","boost":True,
         "fan_pwm_pct":80,"description":"Full speed for demanding tasks"},
        {"name":"Beast Mode",  "governor":"performance","boost":True,
         "fan_pwm_pct":100,"description":"Maximum everything — hold on"},
    ]

def load_profiles():
    if SYS_PROFILES.exists():
        try: return json.loads(SYS_PROFILES.read_text())
        except: pass
    ps = _default_profiles()
    SYS_PROFILES.write_text(json.dumps(ps,indent=2))
    return ps

def save_profiles(ps):
    SYS_PROFILES.write_text(json.dumps(ps,indent=2))

def apply_profile(profile, hw):
    msgs = []
    gov = profile.get("governor","schedutil")
    for cpu in Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_governor"):
        ok, err = _write_priv(str(cpu), gov)
        if not ok: msgs.append(f"Governor failed: {err}"); break
    else: msgs.append(f"Governor → {gov}")
    boost_path = "/sys/devices/system/cpu/cpufreq/boost"
    if Path(boost_path).exists():
        val = "1" if profile.get("boost",True) else "0"
        ok, err = _write_priv(boost_path, val)
        msgs.append(f"Boost → {'on' if val=='1' else 'off'}" if ok else f"Boost failed: {err}")
    fan_pct = profile.get("fan_pwm_pct",50)
    pwm_val = int(fan_pct/100*255)
    for dev in hw.get("hwmon",[]):
        for pwm in dev.get("pwms",[]):
            _write_priv(pwm["enable_path"],"1")
            _write_priv(pwm["path"], str(pwm_val))
    if any(dev.get("pwms") for dev in hw.get("hwmon",[])):
        msgs.append(f"Fans → {fan_pct}% ({pwm_val}/255 PWM)")
    return msgs

# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════
CSS = """
* { font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', 'Sans'; }
window { background-color: #08080e; color: rgba(232,224,245,0.92); }

.nav-bar {
    background-color: #000000;
    border-right: 3px solid rgba(255,0,255,0.25);
    min-width: 160px;
}
.nav-btn {
    background-color: transparent;
    color: rgba(180,160,220,0.70);
    border: none; border-left: 4px solid transparent; border-radius: 0;
    padding: 14px 14px 14px 18px;
    font-size: 17px; font-weight: bold; min-height: 0; text-align: left;
}
.nav-btn:hover { background-color: rgba(255,0,255,0.10); color: rgba(255,180,255,0.95); }
.nav-active-pink   { background: rgba(255,0,255,0.14);  color: #ff88ff;
                     border-left: 4px solid #ff00ff;
                     box-shadow: inset 4px 0 16px rgba(255,0,255,0.14); }
.nav-active-red    { background: rgba(255,30,30,0.14);  color: #ff6655;
                     border-left: 4px solid #ff2020; }
.nav-active-orange { background: rgba(255,85,0,0.14);  color: #ff8855;
                     border-left: 4px solid #ff5500; }
.nav-active-purple { background: rgba(204,0,255,0.14); color: #dd88ff;
                     border-left: 4px solid #cc00ff; }
.nav-active-blue   { background: rgba(0,136,255,0.14); color: #66bbff;
                     border-left: 4px solid #0088ff; }
.nav-active-green  { background: rgba(57,255,20,0.12); color: #88ff55;
                     border-left: 4px solid #39ff14; }
.nav-active-yellow { background: rgba(255,255,0,0.12); color: #ffff88;
                     border-left: 4px solid #ffff00; }

scale trough { background-color: rgba(255,255,255,0.08); border-radius: 2px; min-height: 8px; }
scale highlight { border-radius: 2px; min-height: 8px; }
scale.pink   highlight { background-color: #ff00ff; }
scale.blue   highlight { background-color: #0088ff; }
scale.green  highlight { background-color: #39ff14; }
scale.yellow highlight { background-color: #ffff00; }
scale.orange highlight { background-color: #ff5500; }
scale.purple highlight { background-color: #cc00ff; }
scale.red    highlight { background-color: #ff2020; }
scale slider { min-width:18px; min-height:18px; border-radius:2px; background:white;
               border:2px solid rgba(255,255,255,0.50); }

.neon-btn {
    background-color: rgba(255,0,255,0.14); color: #ff88ff;
    border: 2px solid rgba(255,0,255,0.45); border-radius: 4px;
    padding: 9px 20px; font-size: 16px; font-weight: bold;
    box-shadow: 0 0 8px rgba(255,0,255,0.18);
}
.neon-btn:hover { background-color: rgba(255,0,255,0.26); border-color:#ff00ff;
                  box-shadow: 0 0 18px rgba(255,0,255,0.40); }
.neon-btn-blue  { background-color:rgba(0,136,255,0.14); color:#66bbff;
                  border:2px solid rgba(0,136,255,0.45); border-radius:4px;
                  padding:9px 20px; font-size:16px; font-weight:bold; }
.neon-btn-blue:hover  { background-color:rgba(0,136,255,0.26); border-color:#0088ff; }
.neon-btn-green { background-color:rgba(57,255,20,0.12); color:#88ff55;
                  border:2px solid rgba(57,255,20,0.45); border-radius:4px;
                  padding:9px 20px; font-size:16px; font-weight:bold; }
.neon-btn-green:hover { background-color:rgba(57,255,20,0.24); border-color:#39ff14; }
.neon-btn-red   { background-color:rgba(255,30,30,0.14); color:#ff6655;
                  border:2px solid rgba(255,60,40,0.45); border-radius:4px;
                  padding:9px 20px; font-size:16px; font-weight:bold; }
.neon-btn-red:hover { background-color:rgba(255,60,40,0.28); }
.neon-btn-yellow{ background-color:rgba(255,255,0,0.12); color:#ffff88;
                  border:2px solid rgba(255,255,0,0.45); border-radius:4px;
                  padding:9px 20px; font-size:16px; font-weight:bold; }
.neon-btn-yellow:hover { background-color:rgba(255,255,0,0.24); border-color:#ffff00; }
.neon-btn-orange{ background-color:rgba(255,85,0,0.14); color:#ff8855;
                  border:2px solid rgba(255,85,0,0.45); border-radius:4px;
                  padding:9px 20px; font-size:16px; font-weight:bold; }
.neon-btn-orange:hover { background-color:rgba(255,85,0,0.26); border-color:#ff5500; }
.neon-btn-purple{ background-color:rgba(200,0,255,0.14); color:#dd88ff;
                  border:2px solid rgba(200,0,255,0.45); border-radius:4px;
                  padding:9px 20px; font-size:16px; font-weight:bold; }
.neon-btn-purple:hover { background-color:rgba(200,0,255,0.26); border-color:#cc00ff; }

entry {
    background-color: rgba(255,255,255,0.05); color: rgba(232,224,245,0.90);
    border: 2px solid rgba(255,0,255,0.30); border-radius: 4px;
    padding: 7px 14px; font-size: 16px; caret-color: #ff00ff;
}
entry:focus { border-color: #ff00ff; box-shadow: 0 0 12px rgba(255,0,255,0.25); }
entry text { background-color: transparent; }

scrollbar { background-color: transparent; }
scrollbar slider { background-color: rgba(255,0,255,0.22); border-radius: 2px; min-width:5px; }
"""

# ══════════════════════════════════════════════════════════════════════════════
#  Drawing helpers  (NO cairo import needed — use cr.arc for all fills)
# ══════════════════════════════════════════════════════════════════════════════
_rng_inst = random.Random(0x4E5958)   # "NYX"

def _rng(x, y=0, w=0, h=0):
    return random.Random(int(abs(x*3+y*7+(w or 1)*11+(h or 1)*13)) % 65535)

def glow_text(cr, x, y, txt, r, g, b, size=13, bold=False):
    cr.select_font_face("Caveat", 0, 1 if bold else 0)
    cr.set_font_size(size)
    cr.set_source_rgba(r, g, b, 0.22); cr.move_to(x+1.5,y+1.0); cr.show_text(txt)
    cr.set_source_rgba(r, g, b, 0.94); cr.move_to(x, y);         cr.show_text(txt)

def glow_text_c(cr, cx, y, txt, r, g, b, size=13, bold=False):
    """Centered glow text."""
    cr.select_font_face("Caveat", 0, 1 if bold else 0)
    cr.set_font_size(size)
    ext = cr.text_extents(txt)
    x   = cx - ext.width/2 - ext.x_bearing
    glow_text(cr, x, y, txt, r, g, b, size, bold)

def rainbow_bar(cr, x, y, w, h=3):
    seg = w / len(PALETTE)
    for i, (r,g,b) in enumerate(PALETTE):
        cr.set_source_rgba(r,g,b,0.90)
        cr.rectangle(x+i*seg, y, seg, h); cr.fill()

def sketch_rect(cr, x, y, w, h, r, g, b, thick=2.5, jitter=3.0, fill_rgba=None):
    rng = _rng(x, y, w, h)
    j   = lambda s=1.0: rng.uniform(-jitter*s, jitter*s)
    def _path():
        cr.move_to(x+j(.4),y+j(.4))
        cr.curve_to(x+w*.33+j(),y+j(),x+w*.67+j(),y+j(),x+w+j(.4),y+j(.4))
        cr.curve_to(x+w+j(),y+h*.33+j(),x+w+j(),y+h*.67+j(),x+w+j(.4),y+h+j(.4))
        cr.curve_to(x+w*.67+j(),y+h+j(),x+w*.33+j(),y+h+j(),x+j(.4),y+h+j(.4))
        cr.curve_to(x+j(),y+h*.67+j(),x+j(),y+h*.33+j(),x+j(.4),y+j(.4))
        cr.close_path()
    if fill_rgba:
        _path(); cr.set_source_rgba(*fill_rgba); cr.fill()
        rng2 = _rng(x,y,w,h); j = lambda s=1.0: rng2.uniform(-jitter*s, jitter*s)
    _path()
    cr.set_source_rgba(r,g,b,0.90); cr.set_line_width(thick)
    cr.set_line_cap(1); cr.set_line_join(1); cr.stroke()

def draw_nyxus_bg(cr, w, h):
    """Dark base fill — pure Cairo, no image dependency."""
    cr.set_source_rgb(*C_BG); cr.rectangle(0, 0, w, h); cr.fill()
    # Subtle dot grid for texture
    cr.set_source_rgba(0.55, 0.25, 0.85, 0.07)
    step = 24
    for gx in range(0, int(w) + step, step):
        for gy in range(0, int(h) + step, step):
            cr.arc(gx, gy, 1.0, 0, 6.2832)
            cr.fill()

def neon_card(cr, x, y, w, h, color, tint=0.07, jitter=2.5):
    r,g,b = color
    # Shadow
    cr.set_source_rgba(r,g,b,0.06); cr.rectangle(x+5,y+6,w,h); cr.fill()
    # Body
    cr.set_source_rgb(*C_PANEL); cr.rectangle(x,y,w,h); cr.fill()
    # Inner dot grid
    cr.set_line_width(0.3)
    sp = 20
    for gx in range(int(x),int(x+w),sp):
        cr.set_source_rgba(r,g,b,0.04)
        cr.move_to(gx,y); cr.line_to(gx,y+h); cr.stroke()
    for gy in range(int(y),int(y+h),sp):
        cr.set_source_rgba(r,g,b,0.04)
        cr.move_to(x,gy); cr.line_to(x+w,gy); cr.stroke()
    sketch_rect(cr,x+2,y+2,w-4,h-4,r,g,b,thick=2.5,jitter=jitter,
                fill_rgba=(r,g,b,tint))

def hbar(cr, x, y, w, h, pct, color):
    cr.set_source_rgba(*C_DIM,0.12); cr.rectangle(x,y,w,h); cr.fill()
    if pct > 0:
        fw = max(0,min(pct/100,1.0))*w
        cr.set_source_rgba(*color,0.88); cr.rectangle(x,y,fw,h); cr.fill()
        cr.set_source_rgba(*color,0.18); cr.set_line_width(h+6)
        cr.move_to(x,y+h/2); cr.line_to(x+fw,y+h/2); cr.stroke()

def arc_gauge(cr, cx, cy, R, pct, color, thick=14, label=""):
    a0 = math.pi*0.75; a1 = math.pi*2.25; span = a1-a0
    cr.set_source_rgba(*C_DIM,0.18); cr.set_line_width(thick)
    cr.arc(cx,cy,R,a0,a1); cr.stroke()
    if pct > 0:
        end = a0+span*min(pct/100,1.0)
        cr.set_source_rgba(*color,0.20); cr.set_line_width(thick+10)
        cr.arc(cx,cy,R,a0,end); cr.stroke()
        cr.set_source_rgba(*color,0.92); cr.set_line_width(thick)
        cr.arc(cx,cy,R,a0,end); cr.stroke()
    if label:
        glow_text_c(cr, cx, cy+8, label, *color, size=14, bold=True)

def sparkline(cr, x, y, w, h, vals, color, max_val=None):
    if not vals: return
    mv   = max_val or (max(vals) if max(vals) > 0 else 1.0)
    step = w/max(len(vals)-1,1)
    pts  = [(x+i*step, y+h-(v/mv)*h*0.88) for i,v in enumerate(vals)]
    cr.new_path(); cr.move_to(x,y+h)
    for px,py in pts: cr.line_to(px,py)
    cr.line_to(x+(len(vals)-1)*step,y+h); cr.close_path()
    cr.set_source_rgba(*color,0.13); cr.fill()
    cr.new_path()
    for i,(px,py) in enumerate(pts):
        (cr.move_to if i==0 else cr.line_to)(px,py)
    cr.set_source_rgba(*color,0.92); cr.set_line_width(1.8); cr.stroke()

def temp_color(t):
    if t is None: return C_DIM
    return C_GREEN if t<60 else (C_YELLOW if t<80 else (C_ORANGE if t<90 else C_RED))

def pct_color(p):
    return C_GREEN if p<50 else (C_YELLOW if p<75 else (C_ORANGE if p<90 else C_RED))

# ══════════════════════════════════════════════════════════════════════════════
#  Application
# ══════════════════════════════════════════════════════════════════════════════
class NyxusControl(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.control",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.hw        = load_hw_profile()
        self.live      = LiveData(self.hw)
        self.profiles  = load_profiles()
        self._cur_page = "OVERVIEW"
        self._anim_t   = 0.0
        self._toast_msg     = ""
        self._toast_until   = 0.0
        self._fan_sliders:  dict = {}
        self._fan_manual    = False
        self._nav_btns:     dict = {}
        self._das:          dict = {}
        self._selected_prof_idx = 0
        self._proc_filter   = ""
        self._proc_sort_key = "cpu"
        self._proc_nice_delta = 0
        self._rgb_color     = (1.0, 0.0, 1.0)

    # ──────────────────────────────────────────────────────── activate ──────────
    def do_activate(self):
        prov = Gtk.CssProvider()
        try:    prov.load_from_string(CSS)
        except: prov.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self, title="NYXUS Control")
        self.win.set_default_size(1200, 750)
        self.win.connect("close-request", self._on_close)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)
        try: _nyx_install_chrome(self.win, page_key="_control")
        except Exception: pass

        # Header bar
        hdr_da = Gtk.DrawingArea()
        hdr_da.set_size_request(-1, 56)
        hdr_da.set_draw_func(self._draw_hdr, None)
        self._hdr_da = hdr_da
        root.append(hdr_da)

        # Body
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_vexpand(True)
        root.append(body)
        body.append(self._build_nav())

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(80)
        self._stack.set_hexpand(True)
        self._stack.set_vexpand(True)
        body.append(self._stack)

        self._stack.add_named(self._build_overview(),  "OVERVIEW")
        self._stack.add_named(self._build_fans(),      "FANS")
        self._stack.add_named(self._build_thermal(),   "THERMAL")
        self._stack.add_named(self._build_profiles(),  "PROFILES")
        self._stack.add_named(self._build_rgb(),       "RGB")
        self._stack.add_named(self._build_power(),     "POWER")
        self._stack.add_named(self._build_processes(), "PROCESSES")
        self._stack.set_visible_child_name("OVERVIEW")

        # Toast
        self._toast_da = Gtk.DrawingArea()
        self._toast_da.set_size_request(-1,0)
        self._toast_da.set_draw_func(self._draw_toast, None)
        root.append(self._toast_da)

        GLib.timeout_add(500, self._anim_tick)          # 2 fps — clock only
        GLib.timeout_add_seconds(5, self._data_tick)    # 5 s — sensor poll
        threading.Thread(target=self._initial_collect, daemon=True).start()
        self.win.present()

    def _on_close(self, *_):
        self.win.hide(); return True

    def _da(self, fn, w=-1, h=-1, expand=True):
        a = Gtk.DrawingArea()
        a.set_size_request(w, h)
        if expand: a.set_vexpand(True); a.set_hexpand(True)
        a.set_draw_func(fn, None)
        return a

    # ──────────────────────────────────────────────────────── header ────────────
    def _draw_hdr(self, area, cr, w, h, _):
        # Dark purple header band — pure Cairo
        cr.set_source_rgb(0.10, 0.04, 0.18); cr.rectangle(0, 0, w, h); cr.fill()
        # Bottom rainbow bar
        rainbow_bar(cr, 0, h-3, w, 3)
        # Thin top border
        cr.set_source_rgba(*C_PINK, 0.18); cr.set_line_width(1)
        cr.move_to(0, 1); cr.line_to(w, 1); cr.stroke()
        # Pulse dot
        pulse = 0.5 + 0.5*math.sin(self._anim_t * 2.5)
        cr.set_source_rgba(*C_GREEN, pulse); cr.arc(22, h//2, 5, 0, math.pi*2); cr.fill()
        glow_text(cr, 38, h-14, "NYXUS  Control", *C_PINK, size=18, bold=True)
        # Board
        board = self.hw.get("board","Unknown Board")[:38]
        cr.select_font_face("Caveat",0,0); cr.set_font_size(13)
        cr.set_source_rgba(*C_DIM, 0.80)
        cr.move_to(260, h-14); cr.show_text(board)
        # Clock
        clk = datetime.now().strftime("%A  %H:%M:%S")
        cr.select_font_face("Caveat",0,1); cr.set_font_size(15)
        ext = cr.text_extents(clk)
        glow_text(cr, w-ext.width-20, h-12, clk, *C_ORANGE, size=15, bold=True)

    def _draw_toast(self, area, cr, w, h, _):
        if self._toast_msg and time.time() < self._toast_until:
            area.set_size_request(-1,36)
            cr.set_source_rgba(0.08,0.05,0.18,0.96); cr.rectangle(0,0,w,36); cr.fill()
            cr.set_source_rgba(*C_PURPLE,0.55); cr.set_line_width(1.5)
            cr.rectangle(0,0,w,36); cr.stroke()
            glow_text(cr, 20, 24, self._toast_msg, *C_PURPLE, size=14)
        else:
            area.set_size_request(-1,0); self._toast_msg=""

    def _toast(self, msg, secs=4.0):
        self._toast_msg=msg; self._toast_until=time.time()+secs
        GLib.idle_add(self._toast_da.queue_draw)

    # ──────────────────────────────────────────────────────── nav ───────────────
    def _build_nav(self):
        nav_da = Gtk.DrawingArea()
        nav_da.set_size_request(164, -1)
        nav_da.set_vexpand(True)
        nav_da.set_draw_func(self._draw_nav, None)
        self._nav_da = nav_da
        self._das["nav"] = nav_da
        click = Gtk.GestureClick()
        click.connect("pressed", self._on_nav_click)
        nav_da.add_controller(click)
        return nav_da

    def _draw_nav(self, area, cr, w, h, _):
        # Background — full height NYXUS style
        draw_nyxus_bg(cr, w, h)
        # Right border
        cr.set_source_rgba(*C_PINK, 0.28); cr.set_line_width(2.5)
        cr.move_to(w-1, 0); cr.line_to(w-1, h); cr.stroke()
        # Top label
        cr.select_font_face("Caveat", 0, 1); cr.set_font_size(11)
        cr.set_source_rgba(*C_DIM, 0.50)
        cr.move_to(12, 20); cr.show_text("NAVIGATION")
        rainbow_bar(cr, 0, 26, w, 2)

        item_h = min(58, (h - 32) / max(len(PAGES), 1))
        for i, (name, color) in enumerate(PAGES):
            iy     = 32 + i * item_h
            active = (name == self._cur_page)
            r, g, b = color

            # Active highlight
            if active:
                # Glow fill
                cr.set_source_rgba(r, g, b, 0.14)
                cr.rectangle(0, iy, w, item_h); cr.fill()
                # Left accent bar
                cr.set_source_rgba(r, g, b, 0.95)
                cr.rectangle(0, iy + 4, 5, item_h - 8); cr.fill()
                # Glow bar
                cr.set_source_rgba(r, g, b, 0.22)
                cr.rectangle(0, iy + 4, 18, item_h - 8); cr.fill()
                # Sketch underline
                rng = _rng(i * 37, iy)
                j   = lambda s=1.0: rng.uniform(-2*s, 2*s)
                cr.set_source_rgba(r, g, b, 0.70); cr.set_line_width(1.5)
                y_ul = iy + item_h - 6
                cr.move_to(10+j(), y_ul+j()); cr.line_to(w-10+j(), y_ul+j())
                cr.stroke()
            else:
                # Subtle hover-ready bg
                cr.set_source_rgba(r, g, b, 0.03)
                cr.rectangle(0, iy, w, item_h); cr.fill()

            # Label — Caveat via Cairo
            cy = iy + item_h * 0.62
            if active:
                glow_text(cr, 16, cy, name, r, g, b, size=17, bold=True)
            else:
                cr.select_font_face("Caveat", 0, 0)
                cr.set_font_size(15)
                cr.set_source_rgba(r, g, b, 0.55)
                cr.move_to(16, cy); cr.show_text(name)

            # Row separator
            cr.set_source_rgba(1, 1, 1, 0.04); cr.set_line_width(0.6)
            cr.move_to(0, iy + item_h); cr.line_to(w, iy + item_h); cr.stroke()

        # Fill remaining space below items with continued bg pattern
        last_y = 32 + len(PAGES) * item_h
        if last_y < h:
            # Small rainbow tick at the very bottom
            rainbow_bar(cr, 0, h - 3, w, 3)

    def _on_nav_click(self, gesture, n_press, x, y):
        item_h = min(58, (self._nav_da.get_height() - 32) / max(len(PAGES), 1))
        idx    = int((y - 32) / item_h)
        if 0 <= idx < len(PAGES):
            name = PAGES[idx][0]
            self._cur_page = name
            self._stack.set_visible_child_name(name)
            self._nav_da.queue_draw()

    def _on_nav(self, btn, name):
        self._cur_page = name
        self._stack.set_visible_child_name(name)

    def _update_nav(self, active):
        pass  # handled by Cairo draw

    # ──────────────────────────────────────────────────────── data ──────────────
    def _initial_collect(self):
        """Run first data collection in background then schedule the regular tick."""
        time.sleep(1)          # let GTK finish setting up first
        self.live.collect()
        GLib.idle_add(self._refresh_ui)

    def _data_tick(self):
        if getattr(self, "_collecting", False):
            return GLib.SOURCE_CONTINUE   # previous poll still running — skip
        self._collecting = True
        threading.Thread(target=self._collect, daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _collect(self):
        try:
            self.live.collect()
        finally:
            self._collecting = False
        GLib.idle_add(self._refresh_ui)

    def _refresh_ui(self):
        # Redraw data panels — NOT the nav (it only needs to change on page switch)
        skip = {"nav"}
        for key, da in self._das.items():
            if key not in skip:
                da.queue_draw()
        return GLib.SOURCE_REMOVE

    def _anim_tick(self):
        self._anim_t += 0.10   # larger step since we're at 2 fps now
        self._hdr_da.queue_draw()
        self._toast_da.queue_draw()
        return GLib.SOURCE_CONTINUE

    # ══════════════════════════════════════════════════════════════════════════
    #  OVERVIEW PAGE  — full-size, all 4 system areas tiled
    # ══════════════════════════════════════════════════════════════════════════
    def _build_overview(self):
        da = self._da(self._draw_overview)
        self._das["overview"] = da
        return da

    def _draw_overview(self, area, cr, w, h, _):
        draw_nyxus_bg(cr, w, h)
        pad = 18
        col_w = (w - pad*3) / 2
        # Row heights — split remaining height into 3 rows
        rh1 = (h - pad*4) * 0.38   # CPU + GPU
        rh2 = (h - pad*4) * 0.28   # Fans + Thermal
        rh3 = (h - pad*4) * 0.34   # Battery/Profile + System info
        r1y = pad
        r2y = r1y + rh1 + pad
        r3y = r2y + rh2 + pad

        # ── CPU card ──────────────────────────────────────────────────────────
        cx, cy = pad, r1y; cw, ch = col_w, rh1
        neon_card(cr, cx, cy, cw, ch, C_PINK)
        cpu = self.hw.get("cpu",{})
        cores = cpu.get("cores",1)
        glow_text(cr, cx+16, cy+30, "CPU", *C_PINK, size=17, bold=True)
        model = cpu.get("model","Unknown CPU")
        cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
        cr.set_source_rgba(*C_DIM,0.80)
        cr.move_to(cx+16, cy+50); cr.show_text(model[:46])
        freq  = f"{self.live.cpu_freq:.0f} MHz" if self.live.cpu_freq else "-- MHz"
        gov   = self.live.governor
        boost = "BOOST ON" if self.live.boost else "boost off"
        cr.move_to(cx+16, cy+68)
        cr.show_text(f"{cores} cores  ·  {gov}  ·  {boost}  ·  {freq}")
        # Per-core heatmap
        pcts = self.live.cpu_pcts or [0]*cores
        n = min(len(pcts), 32)
        bw = max(4, min(24, (cw-32) / max(n,1) - 2))
        bh = 20
        for i in range(n):
            bx = cx+16 + i*(bw+2); by = cy+82
            p  = pcts[i] if i < len(pcts) else 0
            col = pct_color(p)
            cr.set_source_rgba(*col, 0.15); cr.rectangle(bx,by,bw,bh); cr.fill()
            cr.set_source_rgba(*col, 0.90)
            cr.rectangle(bx, by+bh*(1-p/100), bw, bh*(p/100)); cr.fill()
        cr.select_font_face("Caveat",0,0); cr.set_font_size(11)
        cr.set_source_rgba(*C_DIM,0.60); cr.move_to(cx+16,cy+116)
        cr.show_text(f"core load  (avg {sum(pcts)/max(len(pcts),1):.1f}%)")
        # CPU temp hbars
        ty = cy+136
        for k,v in self.live.temps.items():
            if not any(x in k.lower() for x in ("cpu","core","k10","tctl","tdie")): continue
            col = temp_color(v)
            label = k.split(":")[-1][:22]
            glow_text(cr, cx+16, ty, f"{label}", *col, size=12)
            ext = cr.text_extents(f"{v:.0f}°C")
            glow_text(cr, cx+cw-ext.width-20, ty, f"{v:.0f}°C", *col, size=12, bold=True)
            hbar(cr, cx+16, ty+4, cw-32, 7, min(v,120)/120*100, col)
            ty += 26
            if ty > cy+ch-20: break
        if ty == cy+136:
            glow_text(cr, cx+16, ty, "no CPU temp sensors", *C_DIM, size=12)
        # CPU sparkline
        if self.live.cpu_hist:
            sl_y = cy + ch - 48
            sparkline(cr, cx+16, sl_y, cw-32, 38, list(self.live.cpu_hist), C_PINK, 100)
            glow_text(cr, cx+16, sl_y+38, "CPU% history", *C_DIM, size=10)

        # ── GPU card ──────────────────────────────────────────────────────────
        gx, gy = pad*2+col_w, r1y; gw, gh = col_w, rh1
        gpu_hw  = self.hw.get("gpu",{})
        gpu_col = C_PURPLE if gpu_hw.get("vendor")=="nvidia" else C_BLUE
        neon_card(cr, gx, gy, gw, gh, gpu_col)
        vendor_tag = gpu_hw.get("vendor","").upper()
        glow_text(cr, gx+16, gy+30, f"GPU  [{vendor_tag}]", *gpu_col, size=17, bold=True)
        cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
        cr.set_source_rgba(*C_DIM,0.80)
        cr.move_to(gx+16, gy+50); cr.show_text(gpu_hw.get("name","Not detected")[:44])
        if self.live.gpu:
            g = self.live.gpu
            items = [
                ("Util",   f"{g.get('util',0):.0f}%",    g.get("util",0),    gpu_col),
                ("Temp",   f"{g.get('temp',0):.0f}°C",   min(g.get("temp",0),120)/120*100, temp_color(g.get("temp",0))),
                ("VRAM",   f"{g.get('mem_used',0)} / {gpu_hw.get('mem_total',0)} MB",
                           g.get("mem_used",0)/max(gpu_hw.get("mem_total",1),1)*100, gpu_col),
                ("Power",  f"{g.get('power_draw',0):.1f} / {gpu_hw.get('power_limit',0):.0f} W",
                           g.get("power_draw",0)/max(gpu_hw.get("power_limit",1),1)*100, C_YELLOW),
            ]
            ty2 = gy+76
            for lbl,val,pct,col in items:
                glow_text(cr, gx+16, ty2, lbl, *C_DIM, size=12)
                ext = cr.text_extents(val)
                glow_text(cr, gx+gw-ext.width-20, ty2, val, *col, size=12, bold=True)
                hbar(cr, gx+16, ty2+4, gw-32, 7, pct, col)
                ty2 += 28
        elif not gpu_hw.get("detected"):
            glow_text(cr, gx+16, gy+90, "No GPU detected", *C_DIM, size=13)
        else:
            glow_text(cr, gx+16, gy+90, "Live data unavailable", *C_DIM, size=13)

        # ── Fans card ─────────────────────────────────────────────────────────
        fx, fy = pad, r2y; fw, fh = col_w, rh2
        neon_card(cr, fx, fy, fw, fh, C_BLUE)
        glow_text(cr, fx+16, fy+28, "FANS", *C_BLUE, size=16, bold=True)
        if self.live.fans:
            ty3 = fy+52
            for k,rpm in list(self.live.fans.items())[:int((fh-60)/24)]:
                col = C_GREEN if rpm<1500 else (C_YELLOW if rpm<3000 else C_ORANGE)
                label = k.split(":")[-1][:20]
                glow_text(cr, fx+16, ty3, label, *col, size=12)
                ext = cr.text_extents(f"{rpm} RPM")
                glow_text(cr, fx+fw-ext.width-16, ty3, f"{rpm} RPM", *col, size=12, bold=True)
                hbar(cr, fx+16, ty3+4, fw-32, 7, min(rpm,4500)/4500*100, col)
                ty3 += 26
        else:
            glow_text(cr, fx+16, fy+60, "no fan sensors", *C_DIM, size=13)

        # ── Thermal card ──────────────────────────────────────────────────────
        tx, ty_c = pad*2+col_w, r2y; tw, th = col_w, rh2
        neon_card(cr, tx, ty_c, tw, th, C_ORANGE)
        glow_text(cr, tx+16, ty_c+28, "THERMAL", *C_ORANGE, size=16, bold=True)
        if self.live.temps:
            ty4 = ty_c+52
            for k,v in list(self.live.temps.items())[:int((th-60)/24)]:
                col = temp_color(v)
                label = k.split(":")[-1][:22]
                glow_text(cr, tx+16, ty4, label, *col, size=12)
                ext = cr.text_extents(f"{v:.0f}°C")
                glow_text(cr, tx+tw-ext.width-16, ty4, f"{v:.0f}°C", *col, size=12, bold=True)
                hbar(cr, tx+16, ty4+4, tw-32, 7, min(v,120)/120*100, col)
                ty4 += 26
        else:
            glow_text(cr, tx+16, ty_c+60, "no temp sensors", *C_DIM, size=13)

        # ── Battery card ──────────────────────────────────────────────────────
        bx, by = pad, r3y; bw2, bh2 = col_w, rh3
        batt = self.live.battery or self.hw.get("battery") or {}
        batt_col = C_GREEN
        neon_card(cr, bx, by, bw2, bh2, batt_col)
        glow_text(cr, bx+16, by+30, "BATTERY", *batt_col, size=16, bold=True)
        if batt:
            pct  = batt.get("pct",0); stat = batt.get("status","Unknown")
            col  = C_GREEN if pct>40 else (C_YELLOW if pct>15 else C_RED)
            glow_text_c(cr, bx+bw2/2, by+bh2*0.44, f"{pct}%", *col, size=38, bold=True)
            glow_text_c(cr, bx+bw2/2, by+bh2*0.62, stat.upper(), *C_DIM, size=14)
            hbar(cr, bx+20, by+bh2*0.70, bw2-40, 14, pct, col)
            # Battery arc
            arc_gauge(cr, bx+bw2//2, by+bh2*0.45, min(bw2,bh2)*0.28,
                      pct, col, thick=10, label=f"{pct}%")
        else:
            glow_text_c(cr, bx+bw2//2, by+bh2//2, "No Battery / Desktop", *C_DIM, size=14)

        # ── System info card ──────────────────────────────────────────────────
        sx, sy = pad*2+col_w, r3y; sw2, sh2 = col_w, rh3
        neon_card(cr, sx, sy, sw2, sh2, C_YELLOW)
        glow_text(cr, sx+16, sy+30, "SYSTEM", *C_YELLOW, size=16, bold=True)
        # Uptime
        up = self.live.uptime_s
        d,rem = divmod(up,86400); hh,rem2 = divmod(rem,3600); mm,ss = divmod(rem2,60)
        upstr = f"{d}d {hh:02d}:{mm:02d}:{ss:02d}" if d else f"{hh:02d}:{mm:02d}:{ss:02d}"
        glow_text(cr, sx+16, sy+60, f"uptime  {upstr}", *C_YELLOW, size=13)
        # Governor + boost
        gov_col = C_GREEN if self.live.governor=="performance" else \
                  (C_YELLOW if self.live.governor=="schedutil" else C_BLUE)
        glow_text(cr, sx+16, sy+86, f"governor  {self.live.governor}", *gov_col, size=13)
        boost_col = C_GREEN if self.live.boost else C_DIM
        glow_text(cr, sx+16, sy+110, f"boost  {'ON' if self.live.boost else 'off'}", *boost_col, size=13)
        # Mem
        if self.live.mem_total > 0:
            mem_pct = self.live.mem_used/self.live.mem_total*100
            mem_col = pct_color(mem_pct)
            glow_text(cr, sx+16, sy+136,
                      f"RAM  {self.live.mem_used:.1f} / {self.live.mem_total:.1f} GB",
                      *mem_col, size=13)
            hbar(cr, sx+16, sy+142, sw2-32, 7, mem_pct, mem_col)
            if self.live.mem_hist:
                sparkline(cr, sx+16, sy+sh2-54, sw2-32, 40,
                          list(self.live.mem_hist), mem_col, 100)
                glow_text(cr, sx+16, sy+sh2-12, "RAM% history", *C_DIM, size=10)

    # ══════════════════════════════════════════════════════════════════════════
    #  FANS PAGE  — large arc-gauge cards per fan + PWM sliders
    # ══════════════════════════════════════════════════════════════════════════
    def _build_fans(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Preset toolbar
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        tb.set_margin_top(14); tb.set_margin_start(18); tb.set_margin_end(18)
        tb.set_margin_bottom(8)
        lbl = Gtk.Label(label="Fan Preset:")
        lbl.set_markup("<span font='Caveat 16' color='#88aaff'>Fan Preset:</span>")
        tb.append(lbl)
        for name, pct, css in [
            ("Silent",      20,  "neon-btn-blue"),
            ("Balanced",    50,  "neon-btn-green"),
            ("Performance", 80,  "neon-btn-orange"),
            ("Turbo",       100, "neon-btn-red"),
            ("Auto",        -1,  "neon-btn-purple"),
        ]:
            b = Gtk.Button(label=name)
            b.add_css_class(css)
            b.connect("clicked", self._on_fan_preset, pct)
            tb.append(b)
        box.append(tb)

        # Cairo fan gauges + history chart
        da = self._da(self._draw_fans)
        self._das["fans"] = da
        da.set_vexpand(True)
        box.append(da)

        # PWM sliders
        self._fan_sliders = {}
        self._fan_value_labels = {}
        devs = self.hw.get("hwmon",[])
        for dev in devs:
            for pwm in dev.get("pwms",[]):
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row.set_margin_start(18); row.set_margin_end(18)
                row.set_margin_bottom(8)
                lbl2 = Gtk.Label(label=f"PWM {pwm['idx']}")
                lbl2.set_size_request(120,-1); lbl2.set_xalign(0)
                row.append(lbl2)
                sc = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,255,1)
                sc.add_css_class("blue"); sc.set_hexpand(True)
                cur = self.live.pwms.get(pwm["path"],128)
                sc.set_value(cur); sc.set_draw_value(True)
                sc.connect("value-changed", self._on_pwm_changed, pwm)
                row.append(sc)
                pct_lbl = Gtk.Label(label=f"{int(cur/255*100)}%")
                pct_lbl.set_size_request(52,-1)
                row.append(pct_lbl)
                sc._pct_label = pct_lbl
                self._fan_sliders[pwm["path"]] = sc
                box.append(row)
        return box

    def _draw_fans(self, area, cr, w, h, _):
        draw_nyxus_bg(cr, w, h)
        fans = list(self.live.fans.items())
        if not fans:
            glow_text_c(cr, w//2, h//2-20, "No fan sensors detected", *C_DIM, size=16)
            cr.select_font_face("Caveat",0,0); cr.set_font_size(13)
            cr.set_source_rgba(*C_DIM,0.60)
            cr.move_to(w//2-160, h//2+10)
            cr.show_text("Install lm_sensors: sudo pacman -S lm_sensors && sudo sensors-detect")
            return

        # Split: top = gauge cards, bottom = history sparklines
        gauge_h = min(h*0.62, 300)
        hist_h  = h - gauge_h - 16

        # ── Fan gauge cards ────────────────────────────────────────────────────
        n   = len(fans)
        pad = 16
        cw  = (w - pad*(n+1)) / max(n,1)
        ch  = gauge_h - pad*2

        for i, (k, rpm) in enumerate(fans):
            cx  = pad + i*(cw+pad)
            cy  = pad
            col = C_GREEN if rpm<1500 else (C_YELLOW if rpm<3000 else (C_ORANGE if rpm<4000 else C_RED))
            neon_card(cr, cx, cy, cw, ch, col)
            label = k.split(":")[-1][:18]
            dev   = k.split(":")[0][:12]
            glow_text_c(cr, cx+cw//2, cy+22, label, *col, size=14, bold=True)
            cr.select_font_face("Caveat",0,0); cr.set_font_size(11)
            cr.set_source_rgba(*C_DIM,0.60)
            cr.move_to(cx+8, cy+36); cr.show_text(dev)

            # Big RPM gauge
            R   = min(cw,ch)*0.28
            gcx = cx + cw//2; gcy = cy + ch*0.48
            max_rpm = max(rpm, 5000)
            arc_gauge(cr, gcx, gcy, R, rpm/max_rpm*100, col, thick=14)
            glow_text_c(cr, gcx, gcy+8, f"{rpm}", *col, size=22, bold=True)
            glow_text_c(cr, gcx, gcy+30, "RPM", *C_DIM, size=12)

            # Speed zone label
            zone = "IDLE" if rpm<200 else ("SILENT" if rpm<1500 else
                   ("MED" if rpm<3000 else ("HIGH" if rpm<4000 else "MAX")))
            sketch_rect(cr, cx+cw//2-32, gcy+38, 64, 22, *col,
                        thick=1.8, jitter=2.0, fill_rgba=(*col,0.08))
            glow_text_c(cr, cx+cw//2, gcy+54, zone, *col, size=12, bold=True)

            # Min RPM from hwmon
            fan_info = next((f for dev_d in self.hw.get("hwmon",[])
                            for f in dev_d["fans"]
                            if f"{dev_d['name']}:{f['label']}"==k), {})
            min_rpm = fan_info.get("min_rpm",0)
            cr.select_font_face("Caveat",0,0); cr.set_font_size(10)
            cr.set_source_rgba(*C_DIM,0.55)
            cr.move_to(cx+8, cy+ch-8); cr.show_text(f"min {min_rpm} RPM")

            # History sparkline at bottom of card
            hist_vals = list(self.live.fan_hist.get(k,[]))
            if hist_vals and len(hist_vals) > 2:
                sl_h = ch*0.16; sl_y = cy+ch-sl_h-18
                sparkline(cr, cx+8, sl_y, cw-16, sl_h, hist_vals, col,
                          max_val=max(max(hist_vals),5000))

        # ── Fan history panel ──────────────────────────────────────────────────
        hy = gauge_h + 8
        cr.set_source_rgba(*C_PANEL,0.70); cr.rectangle(pad, hy, w-pad*2, hist_h-8); cr.fill()
        sketch_rect(cr, pad, hy, w-pad*2, hist_h-8, *C_BLUE, thick=2.0, jitter=2.0)
        glow_text(cr, pad+12, hy+22, "Fan Speed History  (60 min)", *C_BLUE, size=13, bold=True)
        for i,(k,_) in enumerate(fans):
            col = PALETTE[i%len(PALETTE)]
            hist_vals = [v for v in self.live.fan_hist.get(k,[])]
            if hist_vals and len(hist_vals)>2:
                sparkline(cr, pad+12, hy+30, w-pad*2-24, hist_h-48,
                          hist_vals, col, max_val=max(max(hist_vals),5000))
            label = k.split(":")[-1][:16]
            last  = list(self.live.fan_hist.get(k,[[-1]])); last_v = last[-1] if last else 0
            cr.select_font_face("Caveat",0,0); cr.set_font_size(11)
            cr.set_source_rgba(*col,0.80)
            cr.move_to(pad+14+i*160, hy+hist_h-12); cr.show_text(f"{label}: {last_v} rpm")

    def _on_fan_preset(self, btn, pct):
        self._fan_manual = pct >= 0
        for dev in self.hw.get("hwmon",[]):
            for pwm in dev.get("pwms",[]):
                if pct < 0:
                    _write_priv(pwm["enable_path"],"2")
                    if pwm["path"] in self._fan_sliders:
                        self._fan_sliders[pwm["path"]].set_sensitive(False)
                else:
                    _write_priv(pwm["enable_path"],"1")
                    val = int(pct/100*255)
                    ok,err = _write_priv(pwm["path"],str(val))
                    if pwm["path"] in self._fan_sliders:
                        self._fan_sliders[pwm["path"]].set_value(val)
                        self._fan_sliders[pwm["path"]].set_sensitive(True)
                    if not ok:
                        self._toast(f"Fan control needs elevated permissions: {err}"); return
        names = {-1:"Auto",20:"Silent",50:"Balanced",80:"Performance",100:"Turbo"}
        self._toast(f"Fans → {names.get(pct,f'{pct}%')}")

    def _on_pwm_changed(self, scale, pwm):
        val = int(scale.get_value()); pct = int(val/255*100)
        if hasattr(scale,"_pct_label"): scale._pct_label.set_text(f"{pct}%")
        if self._fan_manual:
            _write_priv(pwm["enable_path"],"1")
            _write_priv(pwm["path"],str(val))

    # ══════════════════════════════════════════════════════════════════════════
    #  THERMAL PAGE  — sensor cards with big numbers, history sparklines, thresholds
    # ══════════════════════════════════════════════════════════════════════════
    def _build_thermal(self):
        da = self._da(self._draw_thermal)
        self._das["thermal"] = da
        return da

    def _draw_thermal(self, area, cr, w, h, _):
        draw_nyxus_bg(cr, w, h)
        glow_text(cr, 16, 32, "THERMAL MONITORING", *C_ORANGE, size=18, bold=True)
        rainbow_bar(cr, 0, 40, w, 2)

        # Colour key
        zones = [("< 60°C COOL",C_GREEN),("60–80 WARM",C_YELLOW),
                 ("80–90 HOT",C_ORANGE),("> 90 CRIT",C_RED)]
        for i,(zt,zc) in enumerate(zones):
            cr.set_source_rgba(*zc,0.85); cr.arc(16+i*120+4, 56, 4, 0, math.pi*2); cr.fill()
            cr.select_font_face("Caveat",0,0); cr.set_font_size(11)
            cr.set_source_rgba(*zc,0.80); cr.move_to(26+i*120,60); cr.show_text(zt)

        if not self.live.temps:
            glow_text_c(cr,w//2,h//2,"No temperature sensors detected",*C_DIM,size=16)
            cr.select_font_face("Caveat",0,0); cr.set_font_size(13)
            cr.set_source_rgba(*C_DIM,0.55)
            cr.move_to(w//2-200, h//2+28)
            cr.show_text("Install: sudo pacman -S lm_sensors && sudo sensors-detect && sudo sensors")
            return

        sensors = list(self.live.temps.items())
        # Layout: fit sensors in a grid filling the space
        pad = 14
        top_off = 72
        avail_w = w - pad
        avail_h = h - top_off - pad
        cols = min(len(sensors), max(1, int(avail_w / 260)))
        rows = math.ceil(len(sensors)/cols)
        cw   = (avail_w - pad*(cols+1)) / cols
        rh   = (avail_h - pad*(rows+1)) / max(rows,1)
        ch   = max(rh, 140)

        for idx,(k,cur) in enumerate(sensors):
            col_i = idx % cols; row_i = idx // cols
            cx = pad + col_i*(cw+pad)
            cy = top_off + row_i*(ch+pad)
            color = temp_color(cur)
            neon_card(cr, cx, cy, cw, ch, color, tint=0.05)

            label = k.split(":")[-1][:22]
            dev   = k.split(":")[0][:14]
            glow_text(cr, cx+12, cy+24, label, *color, size=14, bold=True)
            cr.select_font_face("Caveat",0,0); cr.set_font_size(11)
            cr.set_source_rgba(*C_DIM,0.60)
            cr.move_to(cx+12, cy+40); cr.show_text(dev)

            # Big temperature number
            big_y = cy + ch*0.44
            glow_text_c(cr, cx+cw//2, big_y, f"{cur:.1f}°C", *color, size=28, bold=True)

            # Threshold info
            hw_info = next((t for d in self.hw.get("hwmon",[])
                              for t in d["temps"]
                              if f"{d['name']}:{t['label']}"==k), {})
            crit = hw_info.get("crit"); mx = hw_info.get("max")
            info_parts = []
            if mx:   info_parts.append(f"max {mx}°")
            if crit: info_parts.append(f"crit {crit}°")
            if info_parts:
                cr.select_font_face("Caveat",0,0); cr.set_font_size(11)
                cr.set_source_rgba(*C_RED,0.70)
                cr.move_to(cx+12, cy+ch*0.52+4); cr.show_text("  /  ".join(info_parts))

            # Warning badge if hot
            if cur >= 80:
                badge_txt = "!!  CRITICAL" if cur>=90 else "!  HOT"
                sketch_rect(cr, cx+cw-84, cy+6, 78, 20, *C_RED,
                            thick=2.0, jitter=2.0, fill_rgba=(*C_RED,0.15))
                glow_text_c(cr, cx+cw-45, cy+20, badge_txt, *C_RED, size=10, bold=True)

            # Sparkline history
            hist_vals = list(self.live.temp_hist.get(k,[]))
            sl_top = cy + ch*0.58
            sl_h   = ch - ch*0.58 - 12
            if hist_vals and sl_h > 20:
                sparkline(cr, cx+12, sl_top, cw-24, sl_h, hist_vals, color, max_val=100)
                # Crit threshold line
                if crit and sl_h > 0:
                    yc = sl_top + sl_h - (crit/100)*sl_h*0.88
                    cr.set_source_rgba(*C_RED,0.50); cr.set_line_width(1.2)
                    cr.move_to(cx+12,yc); cr.line_to(cx+cw-12,yc); cr.stroke()
            glow_text(cr, cx+12, cy+ch-4, "60 min history", *C_DIM, size=9)

    # ══════════════════════════════════════════════════════════════════════════
    #  PROFILES PAGE  — visual profile tiles + editor
    # ══════════════════════════════════════════════════════════════════════════
    def _build_profiles(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Profile tiles (Cairo)
        tiles_da = self._da(self._draw_profile_tiles, -1, -1, expand=False)
        tiles_da.set_size_request(-1, 200)
        tiles_da.set_content_width(800)
        tiles_da.set_draw_func(self._draw_profile_tiles, None)
        # Allow click selection
        click = Gtk.GestureClick()
        click.connect("pressed", self._on_profile_tile_click)
        tiles_da.add_controller(click)
        self._tiles_da = tiles_da
        self._das["profile_tiles"] = tiles_da
        box.append(tiles_da)

        # Editor area
        editor = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        editor.set_margin_top(16); editor.set_margin_start(20)
        editor.set_margin_end(20); editor.set_margin_bottom(16)
        editor.set_vexpand(True)

        # Left: detail canvas
        detail_da = self._da(self._draw_profile_detail)
        self._das["profile_detail"] = detail_da
        editor.append(detail_da)

        # Right: controls
        ctrl = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        ctrl.set_size_request(280, -1)

        def _row(label_txt, widget):
            r = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            lbl = Gtk.Label(label=label_txt)
            lbl.set_size_request(120,-1); lbl.set_xalign(0)
            r.append(lbl); r.append(widget)
            return r

        self._prof_name_entry = Gtk.Entry()
        self._prof_name_entry.set_placeholder_text("Profile name...")
        self._prof_name_entry.set_hexpand(True)
        ctrl.append(_row("Name:", self._prof_name_entry))

        self._prof_desc_entry = Gtk.Entry()
        self._prof_desc_entry.set_placeholder_text("Description...")
        self._prof_desc_entry.set_hexpand(True)
        ctrl.append(_row("Description:", self._prof_desc_entry))

        govs = self.hw.get("cpu",{}).get("governors",["powersave","schedutil","performance"])
        self._gov_combo = Gtk.DropDown.new_from_strings(govs)
        ctrl.append(_row("Governor:", self._gov_combo))

        self._boost_sw = Gtk.Switch(); self._boost_sw.set_active(True)
        ctrl.append(_row("CPU Boost:", self._boost_sw))

        self._fan_pct_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,0,100,1)
        self._fan_pct_scale.add_css_class("blue"); self._fan_pct_scale.set_value(50)
        self._fan_pct_scale.set_hexpand(True); self._fan_pct_scale.set_draw_value(True)
        ctrl.append(_row("Fan %:", self._fan_pct_scale))

        save_btn = Gtk.Button(label="💾  Save Profile")
        save_btn.add_css_class("neon-btn"); save_btn.connect("clicked", self._on_save_profile_edit)
        ctrl.append(save_btn)

        apply_btn = Gtk.Button(label="⚡  Apply Now")
        apply_btn.add_css_class("neon-btn-green"); apply_btn.connect("clicked", self._on_apply_profile)
        ctrl.append(apply_btn)

        new_btn = Gtk.Button(label="+ New Profile")
        new_btn.add_css_class("neon-btn-blue"); new_btn.connect("clicked", self._on_new_profile)
        ctrl.append(new_btn)

        del_btn = Gtk.Button(label="Delete Profile")
        del_btn.add_css_class("neon-btn-red"); del_btn.connect("clicked", self._on_delete_profile)
        ctrl.append(del_btn)

        editor.append(ctrl)
        box.append(editor)
        self._load_profile_into_editor(0)
        return box

    def _draw_profile_tiles(self, area, cr, w, h, _):
        draw_nyxus_bg(cr, w, h)
        glow_text(cr, 16, 28, "SAVED PROFILES — click to select", *C_PURPLE, size=15, bold=True)
        rainbow_bar(cr, 0, 34, w, 2)
        n   = len(self.profiles)
        if n == 0: return
        pad = 14
        tw  = (w - pad*(n+1)) / n
        th  = h - 44 - pad*2
        tile_colors = [C_BLUE, C_GREEN, C_ORANGE, C_PINK, C_PURPLE, C_YELLOW]
        for i,p in enumerate(self.profiles):
            tx  = pad + i*(tw+pad)
            ty  = 42
            col = tile_colors[i % len(tile_colors)]
            active = (i == self._selected_prof_idx)
            tint   = 0.18 if active else 0.06
            thick  = 3.5  if active else 2.0
            neon_card(cr, tx, ty, tw, th, col, tint=tint, jitter=3.5 if active else 2.0)
            if active:
                sketch_rect(cr, tx, ty, tw, th, *col, thick=thick+1, jitter=4.0)
            glow_text_c(cr, tx+tw//2, ty+28, p.get("name","Profile"), *col, size=16, bold=True)
            cr.select_font_face("Caveat",0,0); cr.set_font_size(11)
            cr.set_source_rgba(*C_DIM,0.70)
            desc = p.get("description","")[:28]
            ext  = cr.text_extents(desc); dx = tx+tw//2-ext.width//2
            cr.move_to(dx, ty+46); cr.show_text(desc)
            items = [
                (f"gov: {p.get('governor','?')}", C_YELLOW),
                (f"boost: {'ON' if p.get('boost') else 'off'}", C_GREEN if p.get("boost") else C_DIM),
                (f"fans: {p.get('fan_pwm_pct',50)}%", C_BLUE),
            ]
            for j,(txt,icol) in enumerate(items):
                glow_text_c(cr, tx+tw//2, ty+66+j*20, txt, *icol, size=12)
            if active:
                glow_text_c(cr, tx+tw//2, ty+th-14, "● SELECTED", *col, size=11, bold=True)

    def _on_profile_tile_click(self, gesture, n_press, x, y):
        w   = self._tiles_da.get_width()
        h   = self._tiles_da.get_height()
        n   = len(self.profiles)
        if n == 0: return
        pad = 14
        tw  = (w - pad*(n+1)) / n
        idx = int((x - pad) / (tw + pad))
        if 0 <= idx < n:
            self._selected_prof_idx = idx
            self._load_profile_into_editor(idx)
            for da in [self._tiles_da, self._das["profile_detail"]]:
                da.queue_draw()

    def _load_profile_into_editor(self, idx):
        if not (0 <= idx < len(self.profiles)): return
        p    = self.profiles[idx]
        govs = self.hw.get("cpu",{}).get("governors",["schedutil"])
        self._prof_name_entry.set_text(p.get("name",""))
        self._prof_desc_entry.set_text(p.get("description",""))
        gov  = p.get("governor","schedutil")
        if gov in govs:
            self._gov_combo.set_selected(govs.index(gov))
        self._boost_sw.set_active(p.get("boost",True))
        self._fan_pct_scale.set_value(p.get("fan_pwm_pct",50))

    def _draw_profile_detail(self, area, cr, w, h, _):
        draw_nyxus_bg(cr, w, h)
        idx = self._selected_prof_idx
        if not (0 <= idx < len(self.profiles)): return
        p     = self.profiles[idx]
        col   = [C_BLUE,C_GREEN,C_ORANGE,C_PINK,C_PURPLE,C_YELLOW][idx%6]
        name  = p.get("name","Profile")
        desc  = p.get("description","")
        gov   = p.get("governor","?")
        boost = p.get("boost",True)
        fan   = p.get("fan_pwm_pct",50)

        sketch_rect(cr, 12, 12, w-24, h-24, *col, thick=3.0, jitter=4.0,
                    fill_rgba=(*col, 0.04))
        glow_text_c(cr, w//2, 52, name, *col, size=30, bold=True)
        cr.select_font_face("Caveat",0,0); cr.set_font_size(14)
        cr.set_source_rgba(*C_DIM,0.80)
        ext = cr.text_extents(desc); cr.move_to(w//2-ext.width//2, 76); cr.show_text(desc)

        # Governor badge
        gbc = C_GREEN if gov=="performance" else (C_YELLOW if gov=="schedutil" else C_BLUE)
        sketch_rect(cr, w//2-80, 94, 160, 30, *gbc,
                    thick=2.0, jitter=2.5, fill_rgba=(*gbc,0.10))
        glow_text_c(cr, w//2, 114, gov.upper(), *gbc, size=14, bold=True)

        # Boost badge
        bc = C_GREEN if boost else C_DIM
        sketch_rect(cr, w//2-50, 134, 100, 26, *bc,
                    thick=2.0, jitter=2.0, fill_rgba=(*bc,0.10))
        glow_text_c(cr, w//2, 151, f"BOOST {'ON' if boost else 'OFF'}", *bc, size=13, bold=True)

        # Fan gauge
        glow_text(cr, 24, 186, "Fan Speed", *C_BLUE, size=13, bold=True)
        hbar(cr, 24, 192, w-48, 14, fan, C_BLUE)
        glow_text_c(cr, w//2, 218, f"{fan}%", *C_BLUE, size=16, bold=True)

        # Quick stats
        stats = [
            ("Governor",    gov,            gbc),
            ("CPU Boost",   "ON" if boost else "off", bc),
            ("Fan Speed",   f"{fan}%",      C_BLUE),
        ]
        sy = 240
        for lbl,val,sc in stats:
            glow_text(cr, 24, sy, lbl+":", *C_DIM, size=13)
            ext = cr.text_extents(val)
            glow_text(cr, w-ext.width-28, sy, val, *sc, size=13, bold=True)
            sy += 28

        # Apply indicator
        cur_gov = self.live.governor
        is_active = (gov==cur_gov)
        if is_active:
            sketch_rect(cr, w//2-70, h-40, 140, 28, *C_GREEN,
                        thick=2.0, jitter=2.0, fill_rgba=(*C_GREEN,0.12))
            glow_text_c(cr, w//2, h-22, "● ACTIVE NOW", *C_GREEN, size=13, bold=True)

    def _on_prof_selected(self, lb, row):
        if row is None: return
        idx = row.get_index()
        self._selected_prof_idx = idx
        self._load_profile_into_editor(idx)
        for k in ("profile_tiles","profile_detail"):
            if k in self._das: self._das[k].queue_draw()

    def _on_apply_profile(self, *_):
        idx = self._selected_prof_idx
        if 0 <= idx < len(self.profiles):
            msgs = apply_profile(self.profiles[idx], self.hw)
            self._toast("  ·  ".join(msgs[:3]))

    def _on_new_profile(self, *_):
        self.profiles.append({"name":"New Profile","governor":"schedutil",
                               "boost":True,"fan_pwm_pct":50,"description":"Custom"})
        save_profiles(self.profiles)
        self._selected_prof_idx = len(self.profiles)-1
        self._load_profile_into_editor(self._selected_prof_idx)
        for k in ("profile_tiles","profile_detail"):
            if k in self._das: self._das[k].queue_draw()
        self._toast("New profile created")

    def _on_delete_profile(self, *_):
        idx = self._selected_prof_idx
        if 0 <= idx < len(self.profiles) and len(self.profiles) > 1:
            name = self.profiles.pop(idx)["name"]
            self._selected_prof_idx = max(0,idx-1)
            save_profiles(self.profiles)
            self._load_profile_into_editor(self._selected_prof_idx)
            for k in ("profile_tiles","profile_detail"):
                if k in self._das: self._das[k].queue_draw()
            self._toast(f"Deleted: {name}")

    def _on_save_profile_edit(self, *_):
        idx = self._selected_prof_idx
        if 0 <= idx < len(self.profiles):
            govs = self.hw.get("cpu",{}).get("governors",["schedutil"])
            sel  = self._gov_combo.get_selected()
            gov  = govs[sel] if sel < len(govs) else "schedutil"
            self.profiles[idx].update({
                "name":        self._prof_name_entry.get_text() or "Profile",
                "description": self._prof_desc_entry.get_text(),
                "governor":    gov,
                "boost":       self._boost_sw.get_active(),
                "fan_pwm_pct": int(self._fan_pct_scale.get_value()),
            })
            save_profiles(self.profiles)
            for k in ("profile_tiles","profile_detail"):
                if k in self._das: self._das[k].queue_draw()
            self._toast(f"Saved: {self.profiles[idx]['name']}")

    # ══════════════════════════════════════════════════════════════════════════
    #  RGB PAGE  — paint-blob palette + OpenRGB integration
    # ══════════════════════════════════════════════════════════════════════════
    def _build_rgb(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        da  = self._da(self._draw_rgb)
        self._das["rgb"] = da
        box.append(da)

        # Color preset buttons
        btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_row.set_margin_start(18); btn_row.set_margin_end(18)
        btn_row.set_margin_top(8); btn_row.set_margin_bottom(12)
        for name, col, css in [
            ("Pink",   C_PINK,   "neon-btn"),
            ("Purple", C_PURPLE, "neon-btn-purple"),
            ("Blue",   C_BLUE,   "neon-btn-blue"),
            ("Green",  C_GREEN,  "neon-btn-green"),
            ("Yellow", C_YELLOW, "neon-btn-yellow"),
            ("Orange", C_ORANGE, "neon-btn-orange"),
            ("Red",    C_RED,    "neon-btn-red"),
            ("Cycle",  None,     "neon-btn-blue"),
        ]:
            b = Gtk.Button(label=name)
            b.add_css_class(css)
            b.connect("clicked", self._on_rgb_color, col, name)
            btn_row.append(b)
        box.append(btn_row)

        # OpenRGB commands
        cmd_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        cmd_row.set_margin_start(18); cmd_row.set_margin_end(18)
        cmd_row.set_margin_bottom(12)
        for name, cmd in [
            ("All OFF",   ["openrgb","--mode","off"]),
            ("Static",    None),
            ("Rainbow",   ["openrgb","--mode","rainbow"]),
            ("Breathing", ["openrgb","--mode","breathing"]),
        ]:
            b = Gtk.Button(label=name)
            b.add_css_class("neon-btn-blue")
            b.connect("clicked", self._on_rgb_cmd, cmd, name)
            cmd_row.append(b)
        box.append(cmd_row)
        return box

    def _draw_rgb(self, area, cr, w, h, _):
        draw_nyxus_bg(cr, w, h)
        glow_text(cr, 16, 32, "RGB LIGHTING CONTROL", *C_GREEN, size=18, bold=True)
        rainbow_bar(cr, 0, 38, w, 3)

        # Paint-blob palette display
        colors = [C_PINK,C_PURPLE,C_BLUE,C_GREEN,C_YELLOW,C_ORANGE,C_RED]
        n = len(colors); blobr = min(w/(n*3), 60)
        blob_y = h*0.30
        for i,col in enumerate(colors):
            bx = (w/(n+1))*(i+1)
            is_sel = (col == self._rgb_color)
            # Outer glow blob
            for layer in range(5):
                rr = blobr*(1.4-layer*0.10)
                cr.set_source_rgba(*col, 0.06+layer*0.02 if not is_sel else 0.10+layer*0.03)
                cr.arc(bx, blob_y, rr, 0, math.pi*2); cr.fill()
            # Main blob
            cr.set_source_rgba(*col, 0.88 if is_sel else 0.60)
            cr.arc(bx, blob_y, blobr, 0, math.pi*2); cr.fill()
            if is_sel:
                sketch_rect(cr, bx-blobr-4, blob_y-blobr-4, blobr*2+8, blobr*2+8,
                            *col, thick=3.0, jitter=4.0)
                glow_text_c(cr, bx, blob_y+blobr+20, "SELECTED", *col, size=11, bold=True)

        # Current color display
        r,g,b = self._rgb_color
        glow_text_c(cr, w//2, h*0.56, "ACTIVE COLOR", *C_DIM, size=13)
        glow_text_c(cr, w//2, h*0.64,
                    f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}",
                    *self._rgb_color, size=24, bold=True)

        # OpenRGB status
        try:
            has_org = subprocess.run(["which","openrgb"],
                                      capture_output=True,timeout=1).returncode==0
        except: has_org = False
        status_col = C_GREEN if has_org else C_ORANGE
        status_txt = "OpenRGB found — commands ready" if has_org else \
                     "OpenRGB not found — install: sudo pacman -S openrgb"
        glow_text_c(cr, w//2, h*0.78, status_txt, *status_col, size=13)

        # Tips
        tips = [
            "Click a color button below to set RGB",
            "Use the mode buttons to set effects",
            "OpenRGB supports per-device control",
        ]
        for i,tip in enumerate(tips):
            glow_text_c(cr, w//2, h*0.86+i*20, tip, *C_DIM, size=11)

    def _on_rgb_color(self, btn, col, name):
        if col is None:
            self._toast("Cycle mode — use OpenRGB for animated effects"); return
        self._rgb_color = col
        r,g,b = col
        hex_col = f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"
        try:
            subprocess.Popen(["openrgb","--color",hex_col],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._toast(f"RGB → {name}  ({hex_col})")
        except FileNotFoundError:
            self._toast(f"OpenRGB not found — color set to {name} locally")
        if "rgb" in self._das: self._das["rgb"].queue_draw()

    def _on_rgb_cmd(self, btn, cmd, name):
        if cmd is None:
            r,g,b = self._rgb_color
            hex_col = f"#{int(r*255):02X}{int(g*255):02X}{int(b*255):02X}"
            cmd = ["openrgb","--mode","static","--color",hex_col]
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._toast(f"RGB mode → {name}")
        except FileNotFoundError:
            self._toast("OpenRGB not installed")

    # ══════════════════════════════════════════════════════════════════════════
    #  POWER PAGE  — governor, freq, battery, TDP, uptime — all drawn
    # ══════════════════════════════════════════════════════════════════════════
    def _build_power(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Governor quick-set buttons
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tb.set_margin_top(14); tb.set_margin_start(18)
        tb.set_margin_end(18); tb.set_margin_bottom(10)
        govs = self.hw.get("cpu",{}).get("governors",
               ["powersave","schedutil","performance","ondemand","conservative"])
        gov_css = {"powersave":"neon-btn-blue","schedutil":"neon-btn-green",
                   "performance":"neon-btn-orange","ondemand":"neon-btn-yellow",
                   "conservative":"neon-btn-purple"}
        for gov in govs:
            b = Gtk.Button(label=gov)
            b.add_css_class(gov_css.get(gov,"neon-btn"))
            b.connect("clicked", self._on_set_governor, gov)
            tb.append(b)
        box.append(tb)

        # Boost toggle
        boost_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        boost_row.set_margin_start(18); boost_row.set_margin_bottom(10)
        bl = Gtk.Label(label="CPU Boost")
        bl.set_markup("<span font='Caveat 16'>CPU Boost</span>")
        boost_row.append(bl)
        self._pwr_boost_sw = Gtk.Switch()
        self._pwr_boost_sw.set_active(self.live.boost)
        self._pwr_boost_sw.connect("notify::active", self._on_boost_toggle)
        boost_row.append(self._pwr_boost_sw)
        box.append(boost_row)

        # Cairo power display
        da = self._da(self._draw_power)
        self._das["power"] = da
        box.append(da)
        return box

    def _draw_power(self, area, cr, w, h, _):
        draw_nyxus_bg(cr, w, h)
        glow_text(cr, 16, 32, "POWER MANAGEMENT", *C_YELLOW, size=18, bold=True)
        rainbow_bar(cr, 0, 38, w, 2)

        # ── Auto-fit layout: 4 rows split proportionally to window height ────
        pad = 18; cw = (w-pad*3)//2
        title_h = 50
        avail = h - title_h - pad*5
        rh1 = int(avail * 0.22)   # Governor + Boost
        rh2 = int(avail * 0.16)   # Per-Core Frequency
        rh3 = int(avail * 0.18)   # Uptime + Battery
        rh4 = avail - rh1 - rh2 - rh3   # CPU Load history (rest)
        y1 = title_h
        y2 = y1 + rh1 + pad
        y3 = y2 + rh2 + pad
        y4 = y3 + rh3 + pad

        # ── Governor card ─────────────────────────────────────────────────────
        neon_card(cr, pad, y1, cw, rh1, C_YELLOW)
        glow_text(cr, pad+14, y1+28, "CPU GOVERNOR", *C_YELLOW, size=14, bold=True)
        gov = self.live.governor
        gov_col = C_GREEN if gov=="performance" else \
                  (C_YELLOW if gov=="schedutil" else (C_BLUE if gov=="powersave" else C_ORANGE))
        glow_text_c(cr, pad+cw//2, y1+rh1//2+10, gov.upper(), *gov_col, size=26, bold=True)
        freq_str = f"{self.live.cpu_freq:.0f} MHz" if self.live.cpu_freq else "--"
        glow_text_c(cr, pad+cw//2, y1+rh1-14, freq_str, *C_DIM, size=16)
        sketch_rect(cr, pad+2, y1+2, cw-4, rh1-4, *C_YELLOW, thick=2.5, jitter=2.5)

        # ── Boost card ────────────────────────────────────────────────────────
        gx = pad*2+cw
        bc = C_GREEN if self.live.boost else C_DIM
        neon_card(cr, gx, y1, cw, rh1, bc)
        glow_text(cr, gx+14, y1+28, "CPU BOOST", *bc, size=14, bold=True)
        glow_text_c(cr, gx+cw//2, y1+rh1//2+12, "ON" if self.live.boost else "OFF", *bc, size=36, bold=True)
        cr.select_font_face("Caveat",0,0); cr.set_font_size(12)
        cr.set_source_rgba(*C_DIM,0.70)
        cr.move_to(gx+14, y1+rh1-14)
        cr.show_text("Turbo Boost / AMD Precision Boost")
        sketch_rect(cr, gx+2, y1+2, cw-4, rh1-4, *bc, thick=2.5, jitter=2.5)

        # ── Frequency display ─────────────────────────────────────────────────
        neon_card(cr, pad, y2, w-pad*2, rh2, C_PURPLE)
        glow_text(cr, pad+14, y2+24, "PER-CORE FREQUENCY  (cpu0 scaling)", *C_PURPLE, size=13, bold=True)
        try:
            freqs = []
            for cpu_p in sorted(Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_cur_freq")):
                try: freqs.append(int(cpu_p.read_text().strip())/1000)
                except: pass
            if freqs:
                mn,mx,av = min(freqs),max(freqs),sum(freqs)/len(freqs)
                glow_text(cr, pad+14, y2+rh2//2+8, f"min {mn:.0f}  avg {av:.0f}  max {mx:.0f}  MHz",
                          *C_PURPLE, size=14)
                hbar(cr, pad+14, y2+rh2-18, w-pad*2-28, 10, (av-mn)/(max(mx-mn,1))*100, C_PURPLE)
        except: pass
        sketch_rect(cr, pad+2, y2+2, w-pad*2-4, rh2-4, *C_PURPLE, thick=2.2, jitter=2.2)

        # ── Uptime card ───────────────────────────────────────────────────────
        neon_card(cr, pad, y3, cw, rh3, C_ORANGE)
        glow_text(cr, pad+14, y3+24, "UPTIME", *C_ORANGE, size=14, bold=True)
        up = self.live.uptime_s
        d,rem = divmod(up,86400); hh,rem2 = divmod(rem,3600); mm,ss = divmod(rem2,60)
        up_str = f"{d}d {hh:02d}h {mm:02d}m" if d else f"{hh:02d}h {mm:02d}m {ss:02d}s"
        glow_text_c(cr, pad+cw//2, y3+rh3//2+10, up_str, *C_ORANGE, size=20, bold=True)
        sketch_rect(cr, pad+2, y3+2, cw-4, rh3-4, *C_ORANGE, thick=2.2, jitter=2.2)

        # ── Battery card ──────────────────────────────────────────────────────
        batt = self.live.battery or self.hw.get("battery") or {}
        bx = pad*2+cw
        bc2 = C_GREEN if batt.get("status","")=="Charging" else \
              (C_YELLOW if batt else C_DIM)
        neon_card(cr, bx, y3, cw, rh3, bc2)
        glow_text(cr, bx+14, y3+24, "BATTERY", *bc2, size=14, bold=True)
        if batt:
            pct = batt.get("pct",0); stat = batt.get("status","Unknown")
            col = C_GREEN if pct>40 else (C_YELLOW if pct>15 else C_RED)
            glow_text_c(cr, bx+cw//2, y3+rh3//2,    f"{pct}%", *col, size=26, bold=True)
            glow_text_c(cr, bx+cw//2, y3+rh3//2+22, stat.upper(), *C_DIM, size=13)
            hbar(cr, bx+14, y3+rh3-18, cw-28, 8, pct, col)
        else:
            glow_text_c(cr, bx+cw//2, y3+rh3//2+6, "No Battery", *C_DIM, size=14)
        sketch_rect(cr, bx+2, y3+2, cw-4, rh3-4, *bc2, thick=2.2, jitter=2.2)

        # ── CPU Load history (fills remaining bottom space) ──────────────────
        if rh4 > 60:
            neon_card(cr, pad, y4, w-pad*2, rh4, C_PINK)
            glow_text(cr, pad+14, y4+24, "CPU Load History  (3-sec samples)", *C_PINK, size=13, bold=True)
            if self.live.cpu_hist:
                sparkline(cr, pad+14, y4+32, w-pad*2-28, rh4-44,
                          list(self.live.cpu_hist), C_PINK, 100)
            if self.live.mem_hist:
                sparkline(cr, pad+14, y4+32, w-pad*2-28, rh4-44,
                          list(self.live.mem_hist), C_BLUE, 100)
            cr.select_font_face("Caveat",0,0); cr.set_font_size(11)
            cr.set_source_rgba(*C_PINK,0.80); cr.move_to(pad+14,y4+rh4-8)
            cr.show_text("CPU%")
            cr.set_source_rgba(*C_BLUE,0.80); cr.move_to(pad+72,y4+rh4-8)
            cr.show_text("MEM%")
            sketch_rect(cr, pad+2, y4+2, w-pad*2-4, rh4-4, *C_PINK, thick=2.2, jitter=2.2)

    def _on_set_governor(self, btn, gov):
        ok_any = False
        for cpu in Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_governor"):
            ok,err = _write_priv(str(cpu),gov)
            if ok: ok_any=True
            else:  self._toast(f"Governor failed: {err}"); return
        if ok_any:
            self.live.governor = gov
            self._toast(f"Governor set to {gov}")
            if "power" in self._das: self._das["power"].queue_draw()

    def _on_boost_toggle(self, sw, param):
        val = "1" if sw.get_active() else "0"
        ok,err = _write_priv("/sys/devices/system/cpu/cpufreq/boost", val)
        if ok:
            self.live.boost = sw.get_active()
            self._toast(f"CPU Boost {'ON' if sw.get_active() else 'OFF'}")
        else:
            self._toast(f"Boost toggle failed: {err}")

    # ══════════════════════════════════════════════════════════════════════════
    #  PROCESSES PAGE  — live Cairo-rendered process list with kill / nice
    # ══════════════════════════════════════════════════════════════════════════
    def _build_processes(self):
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        # Toolbar
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        tb.set_margin_top(12); tb.set_margin_start(18)
        tb.set_margin_end(18); tb.set_margin_bottom(8)

        self._proc_search = Gtk.Entry()
        self._proc_search.set_placeholder_text("  filter processes...")
        self._proc_search.set_hexpand(True)
        self._proc_search.connect("changed", self._on_proc_search)
        tb.append(self._proc_search)

        for name,css,nice in [
            ("Raise prio (nice -5)", "neon-btn-green", -5),
            ("Lower prio (nice +10)","neon-btn-orange", 10),
        ]:
            b = Gtk.Button(label=name)
            b.add_css_class(css)
            b.connect("clicked", self._on_renice, nice)
            tb.append(b)

        kill_btn = Gtk.Button(label="Kill")
        kill_btn.add_css_class("neon-btn-red")
        kill_btn.connect("clicked", self._on_kill)
        tb.append(kill_btn)

        box.append(tb)

        # Sort buttons
        sort_tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        sort_tb.set_margin_start(18); sort_tb.set_margin_bottom(8)
        sort_lbl = Gtk.Label(label="Sort by:")
        sort_lbl.set_markup("<span font='Caveat 14' color='#8866aa'>Sort by:</span>")
        sort_tb.append(sort_lbl)
        self._sort_btns = {}
        for key,lbl in [("cpu","CPU%"),("mem","MEM%"),("pid","PID"),("name","Name")]:
            b = Gtk.Button(label=lbl)
            b.add_css_class("neon-btn-blue" if key=="cpu" else "neon-btn-purple")
            b.connect("clicked", self._on_proc_sort, key)
            sort_tb.append(b)
            self._sort_btns[key] = b
        box.append(sort_tb)

        # Scrolled Cairo canvas
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_vexpand(True)
        da = Gtk.DrawingArea()
        da.set_hexpand(True)
        da.set_size_request(-1, 80*30)   # 80 rows × 30px
        da.set_draw_func(self._draw_processes, None)
        self._das["processes"] = da
        sw.set_child(da)
        box.append(sw)

        # Stats bar
        stats_da = Gtk.DrawingArea()
        stats_da.set_size_request(-1, 40)
        stats_da.set_hexpand(True)
        stats_da.set_draw_func(self._draw_proc_stats, None)
        self._das["proc_stats"] = stats_da
        box.append(stats_da)

        # Selection tracking
        self._proc_selected_pid = None
        click = Gtk.GestureClick()
        click.connect("pressed", self._on_proc_click)
        da.add_controller(click)
        return box

    def _filtered_procs(self):
        procs = self.live.procs or []
        f = self._proc_filter.lower()
        if f:
            procs = [p for p in procs if f in p["name"].lower() or f in str(p["pid"])]
        key  = self._proc_sort_key
        rev  = key in ("cpu","mem")
        return sorted(procs, key=lambda p: p.get(key,0), reverse=rev)

    def _draw_processes(self, area, cr, w, h, _):
        cr.set_source_rgb(*C_BG); cr.rectangle(0,0,w,h); cr.fill()
        procs = self._filtered_procs()

        # Header
        row_h = 30
        cols  = [("PID",50),("Name",240),("CPU%",80),("MEM%",80),
                 ("Nice",56),("Stat",60),("User",100)]
        hdr_h = 32

        cr.set_source_rgba(*C_PANEL,0.98); cr.rectangle(0,0,w,hdr_h); cr.fill()
        rainbow_bar(cr, 0, hdr_h-2, w, 2)
        x = 8
        for lbl,cw in cols:
            glow_text(cr, x, hdr_h-10, lbl,
                      *C_YELLOW if lbl.lower()==self._proc_sort_key else C_DIM,
                      size=13, bold=True)
            x += cw

        # Rows
        for i,p in enumerate(procs[:80]):
            ry  = hdr_h + i*row_h
            cpu = p.get("cpu",0); mem = p.get("mem",0)
            pid = p["pid"]

            # Row bg
            if pid == self._proc_selected_pid:
                cr.set_source_rgba(*C_PURPLE,0.20)
            elif i%2==0:
                cr.set_source_rgba(1,1,1,0.02)
            else:
                cr.set_source_rgba(0,0,0,0.0)
            cr.rectangle(0,ry,w,row_h); cr.fill()

            # CPU heat bar on left edge
            heat = min(cpu/100,1.0)
            col  = pct_color(cpu)
            cr.set_source_rgba(*col, 0.60*heat)
            cr.rectangle(0, ry, 4, row_h); cr.fill()

            # MEM heat on right edge
            mcol = pct_color(mem*4)
            cr.set_source_rgba(*mcol, 0.40*min(mem/10,1.0))
            cr.rectangle(w-4, ry, 4, row_h); cr.fill()

            # Data
            sel_col = C_PURPLE if pid==self._proc_selected_pid else None
            txt_col = sel_col or (col if cpu>10 else C_TEXT)

            x  = 8
            texts = [
                (str(pid),          C_DIM,    50),
                (p["name"],         txt_col, 240),
                (f"{cpu:.1f}",      col,      80),
                (f"{mem:.2f}",      pct_color(mem*4), 80),
                (str(p.get("nice",0)), C_DIM, 56),
                (p.get("stat",""), C_DIM,     60),
                (p.get("user",""), C_DIM,    100),
            ]
            for txt, tc, fw in texts:
                cr.select_font_face("Caveat",0,0); cr.set_font_size(13)
                cr.set_source_rgba(*tc,0.90)
                cr.move_to(x, ry+row_h-9); cr.show_text(txt[:int(fw/7)])
                x += fw

            # Separator
            cr.set_source_rgba(1,1,1,0.04); cr.set_line_width(0.5)
            cr.move_to(0,ry+row_h-0.5); cr.line_to(w,ry+row_h-0.5); cr.stroke()

        if not procs:
            glow_text_c(cr, w//2, hdr_h+80, "No processes found", *C_DIM, size=16)

    def _draw_proc_stats(self, area, cr, w, h, _):
        cr.set_source_rgb(*C_BG); cr.rectangle(0,0,w,h); cr.fill()
        rainbow_bar(cr, 0, 0, w, 2)
        procs  = self.live.procs or []
        total  = len(procs)
        cpu_t  = sum(p.get("cpu",0) for p in procs)
        mem_t  = sum(p.get("mem",0) for p in procs)
        sel    = next((p for p in procs if p["pid"]==self._proc_selected_pid), None)
        glow_text(cr, 14, 28, f"Processes: {total}   Total CPU: {cpu_t:.1f}%   Total MEM: {mem_t:.1f}%",
                  *C_DIM, size=13)
        if sel:
            glow_text(cr, 400, 28,
                      f"Selected: {sel['name']} (PID {sel['pid']})  CPU {sel['cpu']:.1f}%  MEM {sel['mem']:.2f}%",
                      *C_PURPLE, size=13)

    def _on_proc_click(self, gesture, n_press, x, y):
        row_h = 30; hdr_h = 32
        if y < hdr_h: return
        idx = int((y-hdr_h)//row_h)
        procs = self._filtered_procs()
        if 0 <= idx < len(procs):
            self._proc_selected_pid = procs[idx]["pid"]
            if "processes" in self._das: self._das["processes"].queue_draw()
            if "proc_stats" in self._das: self._das["proc_stats"].queue_draw()

    def _on_proc_search(self, entry):
        self._proc_filter = entry.get_text()
        if "processes" in self._das: self._das["processes"].queue_draw()

    def _on_proc_sort(self, btn, key):
        self._proc_sort_key = key
        if "processes" in self._das: self._das["processes"].queue_draw()

    def _on_renice(self, btn, delta):
        pid = self._proc_selected_pid
        if pid is None: self._toast("Select a process first"); return
        ok,err = _write_priv("/dev/null","")  # dummy check
        try:
            subprocess.run(["renice","-n",str(delta),"-p",str(pid)],
                           timeout=3, capture_output=True)
            self._toast(f"Reniced PID {pid} by {delta:+d}")
        except Exception as e:
            self._toast(f"renice failed: {e}")

    def _on_kill(self, btn):
        pid = self._proc_selected_pid
        if pid is None: self._toast("Select a process first"); return
        try:
            os.kill(pid, signal.SIGTERM)
            self._toast(f"SIGTERM → PID {pid}")
            self._proc_selected_pid = None
        except PermissionError:
            self._toast(f"Permission denied — try pkexec kill {pid}")
        except ProcessLookupError:
            self._toast(f"Process {pid} already gone")

# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    app = NyxusControl()
    sys.exit(app.run(sys.argv))
