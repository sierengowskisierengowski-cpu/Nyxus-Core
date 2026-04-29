#!/usr/bin/env python3
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  NYXUS Control — Hardware Control Center                                    ║
# ║  Fan · Thermal · Profiles · RGB · Power · Processes                         ║
# ║  © 2026 JOSEPH SIERENGOWSKI · NYX-CTL-2026-SIERENGOWSKI-LOCKED              ║
# ╚══════════════════════════════════════════════════════════════════════════════╝
import gi, sys, os, math, json, time, threading, subprocess, traceback, random, signal
from pathlib import Path
from collections import deque
from datetime import datetime

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio, Pango

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
HIST     = 360  # 60 min @ 10 s

PAGES = [
    ("OVERVIEW",  C_PINK  ),
    ("FANS",      C_BLUE  ),
    ("THERMAL",   C_ORANGE),
    ("PROFILES",  C_PURPLE),
    ("RGB",       C_GREEN ),
    ("POWER",     C_YELLOW),
    ("PROCESSES", C_ORANGE),
]


# ══════════════════════════════════════════════════════════════════════════════
#  Hardware detection
# ══════════════════════════════════════════════════════════════════════════════

def _read(path: str, default: str = "") -> str:
    try:
        return Path(path).read_text().strip()
    except Exception:
        return default


def _write_priv(path: str, value: str) -> tuple[bool, str]:
    """Write value to sysfs path. Tries direct write then pkexec."""
    try:
        Path(path).write_text(value + "\n")
        return True, ""
    except PermissionError:
        try:
            r = subprocess.run(
                ["pkexec", "tee", path],
                input=(value + "\n").encode(),
                capture_output=True, timeout=20
            )
            if r.returncode == 0:
                return True, ""
            return False, r.stderr.decode().strip()
        except Exception as e:
            return False, str(e)
    except Exception as e:
        return False, str(e)


def _detect_hwmon() -> list:
    devices = []
    hwmon_root = Path("/sys/class/hwmon")
    if not hwmon_root.exists():
        return devices
    for hwmon in sorted(hwmon_root.iterdir()):
        name = _read(str(hwmon / "name"), hwmon.name)
        temps, fans, pwms = [], [], []
        for f in sorted(hwmon.iterdir()):
            fn = f.name
            if fn.startswith("temp") and fn.endswith("_input"):
                idx = fn[4:-6]
                label = _read(str(hwmon / f"temp{idx}_label"), f"Temp {idx}")
                crit  = _read(str(hwmon / f"temp{idx}_crit"), "")
                max_  = _read(str(hwmon / f"temp{idx}_max"), "")
                temps.append({"idx": idx, "label": label,
                               "path": str(f),
                               "crit": int(crit)//1000 if crit.isdigit() else None,
                               "max":  int(max_)//1000  if max_.isdigit()  else None})
            elif fn.startswith("fan") and fn.endswith("_input"):
                idx   = fn[3:-6]
                label = _read(str(hwmon / f"fan{idx}_label"), f"Fan {idx}")
                min_  = _read(str(hwmon / f"fan{idx}_min"), "0")
                fans.append({"idx": idx, "label": label,
                              "path": str(f),
                              "min_rpm": int(min_) if min_.isdigit() else 0})
            elif fn.startswith("pwm") and "_" not in fn:
                idx    = fn[3:]
                pwms.append({"idx": idx,
                              "path": str(f),
                              "enable_path": str(hwmon / f"pwm{idx}_enable")})
        if temps or fans:
            devices.append({"name": name, "path": str(hwmon),
                             "temps": temps, "fans": fans, "pwms": pwms})
    return devices


def _detect_cpu() -> dict:
    model = ""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if "model name" in line:
                    model = line.split(":", 1)[1].strip(); break
    except Exception:
        pass
    gov_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor"
    governor  = _read(gov_path, "unknown")
    governors = _read("/sys/devices/system/cpu/cpu0/cpufreq/scaling_available_governors", "").split()
    boost_path = "/sys/devices/system/cpu/cpufreq/boost"
    boost = _read(boost_path, "0") == "1"
    import platform
    return {
        "model":    model or platform.processor() or "Unknown CPU",
        "cores":    os.cpu_count() or 1,
        "governor": governor,
        "governors": governors or ["powersave", "schedutil", "performance"],
        "boost_path": boost_path,
        "boost_supported": Path(boost_path).exists(),
        "boost": boost,
    }


def _detect_gpu() -> dict:
    try:
        out = subprocess.check_output(
            ["nvidia-smi",
             "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu,power.draw,power.limit",
             "--format=csv,noheader,nounits"],
            timeout=3, stderr=subprocess.DEVNULL
        ).decode().strip()
        p = [x.strip() for x in out.split(",")]
        if len(p) >= 7:
            return {"vendor": "nvidia", "name": p[0], "detected": True,
                    "util": float(p[1]), "mem_used": int(p[2]),
                    "mem_total": int(p[3]), "temp": float(p[4]),
                    "power_draw": float(p[5]), "power_limit": float(p[6])}
    except Exception:
        pass
    for drm in Path("/sys/class/drm").glob("card*/device"):
        if _read(str(drm / "vendor")) == "0x1002":
            return {"vendor": "amd", "name": "AMD GPU", "detected": True}
    return {"vendor": "none", "name": "No GPU", "detected": False}


def _detect_battery() -> dict | None:
    ps = Path("/sys/class/power_supply")
    if not ps.exists():
        return None
    for p in ps.iterdir():
        if _read(str(p / "type")) == "Battery":
            pct    = _read(str(p / "capacity"), "0")
            status = _read(str(p / "status"), "Unknown")
            climit = str(p / "charge_control_end_threshold")
            return {
                "path": str(p),
                "pct":  int(pct) if pct.isdigit() else 0,
                "status": status,
                "charge_limit_path": climit if Path(climit).exists() else None,
            }
    return None


def build_hw_profile() -> dict:
    dmi = Path("/sys/class/dmi/id")
    board = (_read(str(dmi / "board_vendor"), "") + " " +
             _read(str(dmi / "board_name"), "")).strip() or \
            _read(str(dmi / "product_name"), "Unknown Board")
    profile = {
        "generated": datetime.now().isoformat(),
        "board":     board,
        "cpu":       _detect_cpu(),
        "gpu":       _detect_gpu(),
        "battery":   _detect_battery(),
        "hwmon":     _detect_hwmon(),
    }
    HW_PROFILE.write_text(json.dumps(profile, indent=2))
    return profile


def load_hw_profile() -> dict:
    if HW_PROFILE.exists():
        try:
            return json.loads(HW_PROFILE.read_text())
        except Exception:
            pass
    return build_hw_profile()


# ══════════════════════════════════════════════════════════════════════════════
#  Live data collector
# ══════════════════════════════════════════════════════════════════════════════

class LiveData:
    def __init__(self, hw: dict):
        self.hw         = hw
        self.temps:     dict[str, float] = {}
        self.fans:      dict[str, int]   = {}
        self.pwms:      dict[str, int]   = {}
        self.governor   = hw.get("cpu", {}).get("governor", "unknown")
        self.boost      = hw.get("cpu", {}).get("boost", False)
        self.cpu_freq   = 0.0
        self.gpu:       dict = {}
        self.battery:   dict = {}
        self.procs:     list = []
        self.temp_hist: dict[str, deque] = {}
        self.fan_hist:  dict[str, deque] = {}
        for dev in hw.get("hwmon", []):
            for t in dev["temps"]:
                k = f"{dev['name']}:{t['label']}"
                self.temp_hist[k] = deque(maxlen=HIST)
            for f in dev["fans"]:
                k = f"{dev['name']}:{f['label']}"
                self.fan_hist[k] = deque(maxlen=HIST)

    def collect(self):
        for dev in self.hw.get("hwmon", []):
            for t in dev["temps"]:
                raw = _read(t["path"], "0")
                try:
                    c = int(raw) / 1000.0
                    k = f"{dev['name']}:{t['label']}"
                    self.temps[k] = c
                    self.temp_hist[k].append((time.time(), c))
                except Exception:
                    pass
            for f in dev["fans"]:
                raw = _read(f["path"], "0")
                try:
                    rpm = int(raw)
                    k = f"{dev['name']}:{f['label']}"
                    self.fans[k] = rpm
                    self.fan_hist[k].append((time.time(), rpm))
                except Exception:
                    pass
            for p in dev.get("pwms", []):
                raw = _read(p["path"], "128")
                try:
                    self.pwms[p["path"]] = int(raw)
                except Exception:
                    pass

        self.governor = _read(
            "/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", self.governor)
        self.boost = _read(
            "/sys/devices/system/cpu/cpufreq/boost", "0") == "1"
        try:
            self.cpu_freq = int(_read(
                "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq", "0")) / 1000.0
        except Exception:
            pass

        if self.hw.get("gpu", {}).get("vendor") == "nvidia":
            try:
                out = subprocess.check_output(
                    ["nvidia-smi",
                     "--query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw",
                     "--format=csv,noheader,nounits"],
                    timeout=2, stderr=subprocess.DEVNULL
                ).decode().strip()
                p = [x.strip() for x in out.split(",")]
                if len(p) >= 4:
                    self.gpu = {"util": float(p[0]), "mem_used": int(p[1]),
                                "temp": float(p[2]), "power_draw": float(p[3])}
            except Exception:
                pass

        batt = self.hw.get("battery")
        if batt:
            pct    = _read(str(Path(batt["path"]) / "capacity"), "0")
            status = _read(str(Path(batt["path"]) / "status"), "Unknown")
            try:
                self.battery = {"pct": int(pct), "status": status}
            except Exception:
                pass

        try:
            out = subprocess.check_output(
                ["ps", "-eo", "pid,comm,pcpu,pmem,nice,stat", "--sort=-pcpu", "--no-headers"],
                timeout=3, stderr=subprocess.DEVNULL
            ).decode().strip()
            procs = []
            for line in out.splitlines()[:60]:
                parts = line.split(None, 5)
                if len(parts) >= 5:
                    try:
                        procs.append({
                            "pid":  int(parts[0]),
                            "name": parts[1][:28],
                            "cpu":  float(parts[2]),
                            "mem":  float(parts[3]),
                            "nice": int(parts[4]),
                            "stat": parts[5] if len(parts) > 5 else "",
                        })
                    except Exception:
                        pass
            self.procs = procs
        except Exception:
            pass


# ══════════════════════════════════════════════════════════════════════════════
#  Profile management
# ══════════════════════════════════════════════════════════════════════════════

def _default_profiles() -> list:
    return [
        {"name": "Silent",      "governor": "powersave",  "boost": False,
         "fan_pwm_pct": 20, "description": "Quiet & cool — minimal fan noise"},
        {"name": "Balanced",    "governor": "schedutil",  "boost": True,
         "fan_pwm_pct": 50, "description": "Smart everyday performance"},
        {"name": "Performance", "governor": "performance","boost": True,
         "fan_pwm_pct": 80, "description": "Full speed for demanding tasks"},
        {"name": "Beast Mode",  "governor": "performance","boost": True,
         "fan_pwm_pct": 100,"description": "Maximum everything — hold on"},
    ]


def load_profiles() -> list:
    if SYS_PROFILES.exists():
        try:
            return json.loads(SYS_PROFILES.read_text())
        except Exception:
            pass
    profiles = _default_profiles()
    SYS_PROFILES.write_text(json.dumps(profiles, indent=2))
    return profiles


def save_profiles(profiles: list):
    SYS_PROFILES.write_text(json.dumps(profiles, indent=2))


def apply_profile(profile: dict, hw: dict) -> list[str]:
    msgs = []
    gov = profile.get("governor", "schedutil")
    for cpu in Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_governor"):
        ok, err = _write_priv(str(cpu), gov)
        if not ok:
            msgs.append(f"Governor failed: {err}")
            break
    else:
        msgs.append(f"Governor → {gov}")

    boost_path = "/sys/devices/system/cpu/cpufreq/boost"
    if Path(boost_path).exists():
        val = "1" if profile.get("boost", True) else "0"
        ok, err = _write_priv(boost_path, val)
        msgs.append(f"Boost → {'on' if val=='1' else 'off'}" if ok else f"Boost failed: {err}")

    fan_pct = profile.get("fan_pwm_pct", 50)
    pwm_val = int(fan_pct / 100 * 255)
    for dev in hw.get("hwmon", []):
        for pwm in dev.get("pwms", []):
            _write_priv(pwm["enable_path"], "1")
            _write_priv(pwm["path"], str(pwm_val))
    if any(dev.get("pwms") for dev in hw.get("hwmon", [])):
        msgs.append(f"Fans → {fan_pct}% ({pwm_val}/255 PWM)")

    return msgs


# ══════════════════════════════════════════════════════════════════════════════
#  CSS
# ══════════════════════════════════════════════════════════════════════════════

CSS = """
* { font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', 'Sans'; }
window { background-color: #08080e; color: rgba(232,224,245,0.92); }

.nav-bar {
    background-color: #0d0d1a;
    border-right: 2px solid rgba(255,0,255,0.18);
    min-width: 152px;
}
.nav-btn {
    background-color: transparent;
    color: rgba(180,160,220,0.70);
    border: none; border-left: 4px solid transparent; border-radius: 0;
    padding: 11px 14px 11px 16px;
    font-size: 16px; font-weight: bold; min-height: 0;
}
.nav-btn:hover  { background-color: rgba(255,0,255,0.09); color: rgba(255,180,255,0.92); }
.nav-active-pink   { background: rgba(255,0,255,0.12);  color: #ff88ff;
                     border-left: 4px solid #ff00ff; }
.nav-active-orange { background: rgba(255,85,0,0.12);  color: #ff8855;
                     border-left: 4px solid #ff5500; }
.nav-active-purple { background: rgba(204,0,255,0.12); color: #dd88ff;
                     border-left: 4px solid #cc00ff; }
.nav-active-blue   { background: rgba(0,136,255,0.12); color: #66bbff;
                     border-left: 4px solid #0088ff; }
.nav-active-green  { background: rgba(57,255,20,0.10); color: #88ff55;
                     border-left: 4px solid #39ff14; }
.nav-active-yellow { background: rgba(255,255,0,0.10); color: #ffff88;
                     border-left: 4px solid #ffff00; }

scale trough {
    background-color: rgba(255,255,255,0.08);
    border-radius: 6px; min-height: 8px;
}
scale highlight { border-radius: 6px; min-height: 8px; }
scale.pink    highlight { background-color: #ff00ff; }
scale.blue    highlight { background-color: #0088ff; }
scale.green   highlight { background-color: #39ff14; }
scale.yellow  highlight { background-color: #ffff00; }
scale.orange  highlight { background-color: #ff5500; }
scale.purple  highlight { background-color: #cc00ff; }
scale slider  { min-width: 18px; min-height: 18px;
                border-radius: 50%; background: white;
                border: 2px solid rgba(255,255,255,0.50); }

.card {
    background-color: rgba(14,14,28,0.85);
    border-radius: 10px;
    padding: 14px 18px;
    margin: 6px;
}
.neon-btn {
    background-color: rgba(255,0,255,0.12);
    color: #ff88ff;
    border: 2px solid rgba(255,0,255,0.40);
    border-radius: 8px;
    padding: 8px 18px; font-size: 15px; font-weight: bold;
}
.neon-btn:hover { background-color: rgba(255,0,255,0.22); border-color: #ff00ff; }
.neon-btn-blue  { background-color: rgba(0,136,255,0.12); color:#66bbff;
                  border-color: rgba(0,136,255,0.40); }
.neon-btn-blue:hover { background-color: rgba(0,136,255,0.22); border-color:#0088ff; }
.neon-btn-green { background-color: rgba(57,255,20,0.10); color:#88ff55;
                  border-color: rgba(57,255,20,0.35); }
.neon-btn-green:hover { background-color: rgba(57,255,20,0.20); border-color:#39ff14; }
.neon-btn-red   { background-color: rgba(255,30,30,0.15); color:#ff6655;
                  border-color: rgba(255,60,40,0.45); }
.neon-btn-red:hover { background-color: rgba(255,60,40,0.28); }
.neon-btn-yellow{ background-color: rgba(255,255,0,0.10); color:#ffff88;
                  border-color: rgba(255,255,0,0.40); }
.neon-btn-yellow:hover { background-color: rgba(255,255,0,0.20); border-color:#ffff00; }
.neon-btn-orange{ background-color: rgba(255,85,0,0.12); color:#ff8855;
                  border-color: rgba(255,85,0,0.40); }
.neon-btn-orange:hover { background-color: rgba(255,85,0,0.22); border-color:#ff5500; }

.profile-row { background-color: transparent; border: none; }
.profile-row:selected { background-color: rgba(255,0,255,0.12); }

entry, .search-e {
    background-color: rgba(255,255,255,0.05);
    color: rgba(232,224,245,0.88);
    border: 2px solid rgba(255,0,255,0.25); border-radius: 6px;
    padding: 6px 12px; font-size: 15px;
}
entry:focus { border-color: #ff00ff; }

treeview { background-color: #0a0a14; color: rgba(230,220,245,0.88); font-size: 14px; }
treeview:selected { background-color: rgba(255,0,255,0.18); color: #ffaaff; }
treeview header button {
    background-color: #0d0d1a; color: rgba(180,160,220,0.80);
    border: none; font-size: 13px; font-weight: bold;
    border-bottom: 2px solid rgba(255,0,255,0.18);
}
scrollbar { background-color: transparent; }
scrollbar slider { background-color: rgba(255,0,255,0.20); border-radius: 4px; min-width:6px; }
"""


# ══════════════════════════════════════════════════════════════════════════════
#  Drawing helpers
# ══════════════════════════════════════════════════════════════════════════════

import random as _rand

def _rng(x, y=0, w=0, h=0):
    return _rand.Random(int(abs(x*3+y*7+(w or 1)*11+(h or 1)*13)) % 65535)

def glow_text(cr, x, y, txt, r, g, b, size=13, bold=False):
    cr.select_font_face("Caveat", 0, 1 if bold else 0)
    cr.set_font_size(size)
    cr.set_source_rgba(r, g, b, 0.18); cr.move_to(x+1.2, y+0.8); cr.show_text(txt)
    cr.set_source_rgba(r, g, b, 0.92); cr.move_to(x, y);        cr.show_text(txt)

def rainbow_bar(cr, x, y, w, h=3):
    seg = w / len(PALETTE)
    for i, (r, g, b) in enumerate(PALETTE):
        cr.set_source_rgba(r, g, b, 0.90)
        cr.rectangle(x+i*seg, y, seg, h); cr.fill()

def sketch_rect(cr, x, y, w, h, r, g, b, thick=2.2, jitter=2.5, fill_rgba=None):
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
    cr.set_source_rgba(r, g, b, 0.88); cr.set_line_width(thick)
    cr.set_line_cap(1); cr.set_line_join(1); cr.stroke()

def dot_grid(cr, x, y, w, h, spacing=22):
    cr.set_line_width(0.35)
    for gx in range(int(x), int(x+w)+spacing, spacing):
        cr.set_source_rgba(0.28, 0.18, 0.55, 0.12)
        cr.move_to(gx, y); cr.line_to(gx, y+h); cr.stroke()
    for gy in range(int(y), int(y+h)+spacing, spacing):
        cr.set_source_rgba(0.28, 0.18, 0.55, 0.12)
        cr.move_to(x, gy); cr.line_to(x+w, gy); cr.stroke()

def neon_card(cr, x, y, w, h, color, tint=0.08):
    r, g, b = color
    cr.set_source_rgba(r, g, b, 0.07); cr.rectangle(x+5, y+6, w, h); cr.fill()
    cr.set_source_rgb(*C_PANEL);        cr.rectangle(x, y, w, h);     cr.fill()
    dot_grid(cr, x, y, w, h, 20)
    sketch_rect(cr, x+2, y+2, w-4, h-4, r, g, b, thick=2.4, jitter=2.4,
                fill_rgba=(r, g, b, tint))

def ring_chart(cr, cx, cy, R, pct, color):
    cr.set_source_rgba(*C_DIM, 0.20); cr.set_line_width(14)
    cr.arc(cx, cy, R, -math.pi/2, 3*math.pi/2); cr.stroke()
    if pct > 0:
        end = -math.pi/2 + (pct/100)*2*math.pi
        cr.set_source_rgba(*color);      cr.set_line_width(14)
        cr.arc(cx, cy, R, -math.pi/2, end); cr.stroke()
        cr.set_source_rgba(*color, 0.20); cr.set_line_width(26)
        cr.arc(cx, cy, R, -math.pi/2, end); cr.stroke()

def hbar(cr, x, y, w, h, pct, color):
    cr.set_source_rgba(*C_DIM, 0.12); cr.rectangle(x, y, w, h); cr.fill()
    if pct > 0:
        fw = max(0, min(pct/100, 1.0)) * w
        cr.set_source_rgba(*color, 0.90); cr.rectangle(x, y, fw, h); cr.fill()
        cr.set_source_rgba(*color, 0.20); cr.set_line_width(h+6)
        cr.move_to(x, y+h/2); cr.line_to(x+fw, y+h/2); cr.stroke()

def sparkline(cr, x, y, w, h, hist, color, max_val=None):
    vals = list(hist)
    if not vals: return
    mv = max_val or (max(vals) if max(vals) > 0 else 1.0)
    step = w / max(len(vals)-1, 1)
    pts = [(x+i*step, y+h-(v/mv)*h*0.88) for i, v in enumerate(vals)]
    cr.new_path(); cr.move_to(x, y+h)
    for px, py in pts: cr.line_to(px, py)
    cr.line_to(x+(len(vals)-1)*step, y+h); cr.close_path()
    cr.set_source_rgba(*color, 0.14); cr.fill()
    cr.new_path()
    for i, (px, py) in enumerate(pts):
        (cr.move_to if i==0 else cr.line_to)(px, py)
    cr.set_source_rgba(*color, 0.95); cr.set_line_width(1.8); cr.stroke()

def temp_color(t):
    if t is None: return C_DIM
    return C_GREEN if t < 60 else (C_YELLOW if t < 80 else (C_ORANGE if t < 90 else C_RED))

def pct_color(p):
    return C_GREEN if p < 60 else (C_YELLOW if p < 80 else C_ORANGE)


# ══════════════════════════════════════════════════════════════════════════════
#  Application
# ══════════════════════════════════════════════════════════════════════════════

class NyxusControl(Gtk.Application):
    def __init__(self):
        super().__init__(application_id="io.nyxus.control",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.hw       = load_hw_profile()
        self.live     = LiveData(self.hw)
        self.profiles = load_profiles()
        self._cur_page = "OVERVIEW"
        self._anim_t   = 0.0
        self._toast_msg = ""
        self._toast_until = 0.0
        self._fan_sliders: dict = {}   # pwm_path -> Gtk.Scale
        self._fan_manual  = False
        self._nav_btns: dict = {}
        self._das: dict = {}

    # ─────────────────────────────────────────────── activate ──────────────────

    def do_activate(self):
        prov = Gtk.CssProvider()
        try:
            prov.load_from_string(CSS)
        except AttributeError:
            prov.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self, title="NYXUS Control")
        self.win.set_default_size(1440, 900)
        self.win.connect("close-request", self._on_close)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.win.set_child(root)

        # Header
        self._hdr = self._da(self._draw_hdr, -1, 50)
        root.append(self._hdr)
        self._das["hdr"] = self._hdr

        # Body = nav + stack
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        body.set_vexpand(True)
        root.append(body)
        body.append(self._build_nav())

        self._stack = Gtk.Stack()
        self._stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._stack.set_transition_duration(100)
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

        # Toast bar (bottom)
        self._toast_da = self._da(self._draw_toast, -1, 0)
        root.append(self._toast_da)

        GLib.timeout_add(50,    self._anim_tick)
        GLib.timeout_add(10000, self._data_tick)
        self._data_tick()
        self.win.present()

    def _on_close(self, *_):
        self.win.hide()
        return True  # suppress destroy — keep running

    # ─────────────────────────────────────────────── DA helper ─────────────────

    def _da(self, fn, w, h):
        a = Gtk.DrawingArea()
        a.set_size_request(w, h)
        a.set_draw_func(fn, None)
        return a

    # ─────────────────────────────────────────────── header ────────────────────

    def _draw_hdr(self, area, cr, w, h, _):
        cr.set_source_rgb(*C_BG); cr.rectangle(0, 0, w, h); cr.fill()
        cr.set_source_rgba(0.50, 0.40, 0.10, 0.20); cr.set_line_width(1.5)
        cr.move_to(0, h-1); cr.line_to(w, h-1); cr.stroke()
        glow_text(cr, 14, h-10, "NYXUS  Control", *C_PINK, size=16, bold=True)
        cr.select_font_face("Caveat", 0, 0); cr.set_font_size(13)
        board = self.hw.get("board", "Unknown Board")[:40]
        cr.set_source_rgba(*C_DIM, 0.80); cr.move_to(220, h-10); cr.show_text(board)
        clk = datetime.now().strftime("%H:%M:%S")
        cr.select_font_face("Caveat", 0, 1)
        ext = cr.text_extents(clk)
        glow_text(cr, w-ext.width-16, h-8, clk, *C_ORANGE, size=15, bold=True)
        pulse = 0.5 + 0.5*math.sin(self._anim_t * 3)
        cr.set_source_rgba(*C_GREEN, pulse)
        cr.arc(w-ext.width-36, h//2, 5, 0, math.pi*2); cr.fill()
        rainbow_bar(cr, 0, h-3, w, 3)

    def _draw_toast(self, area, cr, w, h, _):
        if self._toast_msg and time.time() < self._toast_until:
            area.set_size_request(-1, 36)
            cr.set_source_rgba(0.08, 0.05, 0.18, 0.95); cr.rectangle(0,0,w,36); cr.fill()
            cr.set_source_rgba(*C_PURPLE, 0.60); cr.set_line_width(1)
            cr.rectangle(0,0,w,36); cr.stroke()
            glow_text(cr, 20, 24, self._toast_msg, *C_PURPLE, size=13)
        else:
            area.set_size_request(-1, 0)
            self._toast_msg = ""

    def _toast(self, msg: str, secs: float = 4.0):
        self._toast_msg   = msg
        self._toast_until = time.time() + secs
        GLib.idle_add(self._toast_da.queue_draw)

    # ─────────────────────────────────────────────── nav ───────────────────────

    def _build_nav(self) -> Gtk.Widget:
        nav = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        nav.add_css_class("nav-bar")
        for name, color in PAGES:
            btn = Gtk.Button(label=name)
            btn.add_css_class("nav-btn")
            btn.connect("clicked", self._on_nav, name)
            self._nav_btns[name] = (btn, color)
            nav.append(btn)
        self._update_nav("OVERVIEW")
        return nav

    def _on_nav(self, btn, name):
        self._cur_page = name
        self._stack.set_visible_child_name(name)
        self._update_nav(name)

    def _update_nav(self, active):
        COLOR_CLASS = {
            C_PINK: "pink", C_ORANGE: "orange", C_PURPLE: "purple",
            C_BLUE: "blue", C_GREEN: "green", C_YELLOW: "yellow",
        }
        for name, (btn, col) in self._nav_btns.items():
            for c in list(btn.get_css_classes()):
                if c.startswith("nav-active"):
                    btn.remove_css_class(c)
            if name == active:
                cls = f"nav-active-{COLOR_CLASS.get(col, 'pink')}"
                btn.add_css_class(cls)

    # ─────────────────────────────────────────────── data ──────────────────────

    def _data_tick(self):
        threading.Thread(target=self._collect, daemon=True).start()
        return GLib.SOURCE_CONTINUE

    def _collect(self):
        self.live.collect()
        GLib.idle_add(self._refresh_ui)

    def _refresh_ui(self):
        for da in self._das.values():
            da.queue_draw()
        self._refresh_fan_labels()
        return GLib.SOURCE_REMOVE

    def _anim_tick(self):
        self._anim_t += 0.04
        self._hdr.queue_draw()
        self._toast_da.queue_draw()
        return GLib.SOURCE_CONTINUE

    # ══════════════════════════════════════════════════════════════════════════
    #  OVERVIEW PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_overview(self) -> Gtk.Widget:
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        da = self._da(self._draw_overview, -1, 700)
        self._das["overview"] = da
        sw.set_child(da)
        return sw

    def _draw_overview(self, area, cr, w, h, _):
        cr.set_source_rgb(*C_BG); cr.rectangle(0, 0, w, h); cr.fill()
        dot_grid(cr, 0, 0, w, h, 28)

        pad = 20
        cw  = (w - pad*3) / 2
        # ── CPU card ──
        cx, cy = pad, pad
        neon_card(cr, cx, cy, cw, 220, C_PINK)
        cpu  = self.hw.get("cpu", {})
        gov  = self.live.governor
        freq = f"{self.live.cpu_freq:.0f} MHz" if self.live.cpu_freq else ""
        glow_text(cr, cx+14, cy+28, "CPU", *C_PINK, size=14, bold=True)
        cr.select_font_face("Caveat", 0, 0); cr.set_font_size(11)
        cr.set_source_rgba(*C_DIM, 0.80)
        cr.move_to(cx+14, cy+46); cr.show_text(cpu.get("model","")[:50])
        cr.move_to(cx+14, cy+62); cr.show_text(f"{cpu.get('cores',0)} cores  ·  {gov}  ·  boost {'on' if self.live.boost else 'off'}  {freq}")
        # CPU temps from hwmon
        ty = cy + 80
        for k, v in self.live.temps.items():
            if "cpu" in k.lower() or "core" in k.lower() or "k10" in k.lower():
                col = temp_color(v)
                glow_text(cr, cx+14, ty, f"{k.split(':')[-1][:18]}  {v:.1f}°C", *col, size=12)
                hbar(cr, cx+14, ty+4, cw-28, 8, min(v,120)/120*100, col)
                ty += 26
                if ty > cy+200: break
        if not any("cpu" in k.lower() or "core" in k.lower() or "k10" in k.lower()
                   for k in self.live.temps):
            glow_text(cr, cx+14, ty, "No CPU temp sensors detected", *C_DIM, size=12)
        sketch_rect(cr, cx+2, cy+2, cw-4, 216, *C_PINK, thick=2.2, jitter=2.2)

        # ── GPU card ──
        gx, gy = pad*2+cw, pad
        gpu_hw = self.hw.get("gpu", {})
        gpu_col = C_PURPLE if gpu_hw.get("vendor") == "nvidia" else C_BLUE
        neon_card(cr, gx, gy, cw, 220, gpu_col)
        glow_text(cr, gx+14, gy+28, "GPU", *gpu_col, size=14, bold=True)
        cr.select_font_face("Caveat", 0, 0); cr.set_font_size(11)
        cr.set_source_rgba(*C_DIM, 0.80)
        cr.move_to(gx+14, gy+46); cr.show_text(gpu_hw.get("name", "Not detected"))
        if self.live.gpu:
            g = self.live.gpu
            glow_text(cr, gx+14, gy+72, f"Util  {g.get('util',0):.0f}%", *gpu_col, size=12)
            hbar(cr, gx+14, gy+80, cw-28, 8, g.get("util",0), gpu_col)
            glow_text(cr, gx+14, gy+100, f"Temp  {g.get('temp',0):.0f}°C", *temp_color(g.get("temp")), size=12)
            hbar(cr, gx+14, gy+108, cw-28, 8, min(g.get("temp",0),120)/120*100, temp_color(g.get("temp")))
            glow_text(cr, gx+14, gy+128, f"VRAM  {g.get('mem_used',0)} / {gpu_hw.get('mem_total',0)} MB", *C_DIM, size=12)
            glow_text(cr, gx+14, gy+148, f"Power {g.get('power_draw',0):.1f} / {gpu_hw.get('power_limit',0):.0f} W", *gpu_col, size=12)
        elif not gpu_hw.get("detected"):
            glow_text(cr, gx+14, gy+80, "No GPU detected", *C_DIM, size=12)
        else:
            glow_text(cr, gx+14, gy+80, "Live data unavailable", *C_DIM, size=11)
        sketch_rect(cr, gx+2, gy+2, cw-4, 216, *gpu_col, thick=2.2, jitter=2.2)

        # ── Fans card ──
        fx, fy = pad, pad + 240
        neon_card(cr, fx, fy, cw, 220, C_BLUE)
        glow_text(cr, fx+14, fy+28, "FANS", *C_BLUE, size=14, bold=True)
        if self.live.fans:
            ty2 = fy + 54
            for k, rpm in self.live.fans.items():
                label = k.split(":")[-1][:20]
                col = C_GREEN if rpm < 2000 else (C_YELLOW if rpm < 3500 else C_ORANGE)
                glow_text(cr, fx+14, ty2, f"{label}  {rpm} RPM", *col, size=12)
                hbar(cr, fx+14, ty2+4, cw-28, 8, min(rpm, 4000)/4000*100, col)
                ty2 += 26
                if ty2 > fy+200: break
        else:
            glow_text(cr, fx+14, fy+80, "No fan sensors detected", *C_DIM, size=12)
        sketch_rect(cr, fx+2, fy+2, cw-4, 216, *C_BLUE, thick=2.2, jitter=2.2)

        # ── Temps card ──
        tx2, ty3 = pad*2+cw, pad + 240
        neon_card(cr, tx2, ty3, cw, 220, C_ORANGE)
        glow_text(cr, tx2+14, ty3+28, "THERMAL", *C_ORANGE, size=14, bold=True)
        if self.live.temps:
            yt = ty3 + 54
            for k, v in list(self.live.temps.items())[:7]:
                col = temp_color(v)
                label = k.split(":")[-1][:22]
                glow_text(cr, tx2+14, yt, f"{label}  {v:.1f}°C", *col, size=12)
                hbar(cr, tx2+14, yt+4, cw-28, 8, min(v,120)/120*100, col)
                yt += 26
        else:
            glow_text(cr, tx2+14, ty3+80, "No temperature sensors", *C_DIM, size=12)
        sketch_rect(cr, tx2+2, ty3+2, cw-4, 216, *C_ORANGE, thick=2.2, jitter=2.2)

        # ── Battery ──
        batt = self.live.battery or self.hw.get("battery")
        if batt:
            bx, by = pad, pad + 480
            neon_card(cr, bx, by, cw, 120, C_GREEN)
            glow_text(cr, bx+14, by+28, "BATTERY", *C_GREEN, size=14, bold=True)
            pct = batt.get("pct", 0)
            st  = batt.get("status", "Unknown")
            col = C_GREEN if pct > 40 else (C_YELLOW if pct > 15 else C_RED)
            glow_text(cr, bx+14, by+54, f"{pct}%  ·  {st}", *col, size=13)
            hbar(cr, bx+14, by+70, cw-28, 12, pct, col)
            sketch_rect(cr, bx+2, by+2, cw-4, 116, *C_GREEN, thick=2.2, jitter=2.2)

        # ── System profile indicator ──
        px2, py2 = pad*2+cw, pad + 480
        neon_card(cr, px2, py2, cw, 120, C_YELLOW)
        glow_text(cr, px2+14, py2+28, "ACTIVE PROFILE", *C_YELLOW, size=14, bold=True)
        glow_text(cr, px2+14, py2+58, self.live.governor.upper(), *C_YELLOW, size=22, bold=True)
        bst = "BOOST ON" if self.live.boost else "BOOST OFF"
        cr.select_font_face("Caveat", 0, 0); cr.set_font_size(11)
        cr.set_source_rgba(*C_DIM, 0.80)
        cr.move_to(px2+14, py2+84); cr.show_text(bst)
        sketch_rect(cr, px2+2, py2+2, cw-4, 116, *C_YELLOW, thick=2.2, jitter=2.2)

    # ══════════════════════════════════════════════════════════════════════════
    #  FANS PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_fans(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_margin_top(16); outer.set_margin_bottom(16)
        outer.set_margin_start(20); outer.set_margin_end(20)

        # Header with preset buttons
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        top.set_margin_bottom(16)
        lbl = Gtk.Label(label="Fan Control")
        lbl.add_css_class("neon-btn")  # reuse pill style
        top.append(lbl)
        for name, pct, css in [
            ("Silent",      20,  "neon-btn-blue"),
            ("Balanced",    50,  "neon-btn"),
            ("Performance", 80,  "neon-btn-orange"),
            ("Turbo",       100, "neon-btn-red"),
            ("Auto",        -1,  "neon-btn-green"),
        ]:
            b = Gtk.Button(label=name)
            b.add_css_class(css)
            b.connect("clicked", self._on_fan_preset, pct)
            top.append(b)
        outer.append(top)

        # Fan rows from hwmon
        self._fan_value_labels: dict = {}
        self._fan_sliders = {}
        devs = self.hw.get("hwmon", [])
        has_fans = False
        for dev in devs:
            if not dev.get("fans") and not dev.get("pwms"):
                continue
            has_fans = True
            # Section header
            sh = Gtk.Label(label=f"  {dev['name'].upper()}  ")
            sh.set_xalign(0)
            cr_stub_color = C_BLUE
            outer.append(sh)

            for fan in dev.get("fans", []):
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row.set_margin_bottom(6)
                lname = Gtk.Label(label=fan["label"])
                lname.set_size_request(140, -1)
                lname.set_xalign(0)
                row.append(lname)
                rpm_lbl = Gtk.Label(label="-- RPM")
                rpm_lbl.set_size_request(100, -1)
                rpm_lbl.set_xalign(1)
                row.append(rpm_lbl)
                fk = f"{dev['name']}:{fan['label']}"
                self._fan_value_labels[fk] = rpm_lbl
                outer.append(row)

            for pwm in dev.get("pwms", []):
                row2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
                row2.set_margin_bottom(12)
                lbl2 = Gtk.Label(label=f"PWM {pwm['idx']}")
                lbl2.set_size_request(140, -1); lbl2.set_xalign(0)
                row2.append(lbl2)
                scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 255, 1)
                scale.add_css_class("blue")
                scale.set_hexpand(True)
                cur = self.live.pwms.get(pwm["path"], 128)
                scale.set_value(cur)
                scale.set_draw_value(True)
                scale.connect("value-changed", self._on_pwm_changed, pwm)
                row2.append(scale)
                pct_lbl = Gtk.Label(label=f"{int(cur/255*100)}%")
                pct_lbl.set_size_request(50, -1)
                row2.append(pct_lbl)
                scale._pct_label = pct_lbl
                self._fan_sliders[pwm["path"]] = scale
                outer.append(row2)

        if not has_fans:
            no_fans = Gtk.Label(label="No fan control sensors detected on this machine.\nCheck that lm-sensors is installed: sudo pacman -S lm_sensors\nThen run: sudo sensors-detect")
            no_fans.set_xalign(0); no_fans.set_margin_top(40); no_fans.set_margin_start(20)
            outer.append(no_fans)

        # Live fan chart
        da = self._da(self._draw_fan_chart, -1, 200)
        da.set_vexpand(False)
        da.set_margin_top(20)
        self._das["fans"] = da
        outer.append(da)

        sw = Gtk.ScrolledWindow()
        sw.set_child(outer)
        return sw

    def _on_fan_preset(self, btn, pct):
        self._fan_manual = pct >= 0
        for dev in self.hw.get("hwmon", []):
            for pwm in dev.get("pwms", []):
                if pct < 0:
                    _write_priv(pwm["enable_path"], "2")  # auto
                    if pwm["path"] in self._fan_sliders:
                        self._fan_sliders[pwm["path"]].set_sensitive(False)
                else:
                    _write_priv(pwm["enable_path"], "1")
                    val = int(pct / 100 * 255)
                    ok, err = _write_priv(pwm["path"], str(val))
                    if pwm["path"] in self._fan_sliders:
                        self._fan_sliders[pwm["path"]].set_value(val)
                        self._fan_sliders[pwm["path"]].set_sensitive(True)
                    if not ok:
                        self._toast(f"Fan control needs elevated permissions: {err}")
                        return
        label = {-1:"Auto", 20:"Silent", 50:"Balanced", 80:"Performance", 100:"Turbo"}.get(pct, f"{pct}%")
        self._toast(f"Fans set to {label}" + (" mode" if pct >= 0 else " (controlled by motherboard)"))

    def _on_pwm_changed(self, scale, pwm):
        val = int(scale.get_value())
        pct = int(val / 255 * 100)
        if hasattr(scale, "_pct_label"):
            scale._pct_label.set_text(f"{pct}%")
        if self._fan_manual:
            _write_priv(pwm["enable_path"], "1")
            _write_priv(pwm["path"], str(val))

    def _refresh_fan_labels(self):
        for k, lbl in self._fan_value_labels.items():
            rpm = self.live.fans.get(k)
            if rpm is not None:
                lbl.set_text(f"{rpm} RPM")

    def _draw_fan_chart(self, area, cr, w, h, _):
        cr.set_source_rgb(*C_BG); cr.rectangle(0, 0, w, h); cr.fill()
        dot_grid(cr, 0, 0, w, h, 24)
        glow_text(cr, 12, 22, "Fan Speed History", *C_BLUE, size=12, bold=True)
        if not self.live.fan_hist:
            return
        ch_x, ch_y, ch_w, ch_h = 12, 32, w-24, h-44
        for i, (k, hist) in enumerate(self.live.fan_hist.items()):
            vals = [v for _, v in hist]
            if not vals: continue
            col = PALETTE[i % len(PALETTE)]
            sparkline(cr, ch_x, ch_y, ch_w, ch_h, vals, col,
                      max_val=max(max(vals), 4000))
            last = vals[-1] if vals else 0
            cr.select_font_face("Caveat", 0, 0); cr.set_font_size(10)
            cr.set_source_rgba(*col, 0.80)
            label = k.split(":")[-1][:14]
            cr.move_to(ch_x + 4 + i*110, ch_y + ch_h - 4)
            cr.show_text(f"{label}: {last} RPM")

    # ══════════════════════════════════════════════════════════════════════════
    #  THERMAL PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_thermal(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        da  = self._da(self._draw_thermal, -1, -1)
        da.set_vexpand(True)
        self._das["thermal"] = da
        box.append(da)
        return box

    def _draw_thermal(self, area, cr, w, h, _):
        cr.set_source_rgb(*C_BG); cr.rectangle(0, 0, w, h); cr.fill()
        dot_grid(cr, 0, 0, w, h, 28)
        glow_text(cr, 14, 32, "Thermal Monitoring  —  60 min history", *C_ORANGE, size=15, bold=True)
        rainbow_bar(cr, 0, 40, w, 2)

        if not self.live.temps:
            glow_text(cr, w//2-120, h//2, "No temperature sensors detected", *C_DIM, size=14)
            return

        sensors = list(self.live.temps.items())
        cols = min(len(sensors), 3)
        rows = math.ceil(len(sensors) / cols)
        pad  = 14
        cw   = (w - pad*(cols+1)) / cols
        ch   = min(180, (h - 80 - pad*(rows+1)) / max(rows, 1))

        for i, (k, cur_temp) in enumerate(sensors):
            col = i % cols
            row = i // cols
            cx  = pad + col * (cw + pad)
            cy  = 54 + row * (ch + pad)
            color = temp_color(cur_temp)

            neon_card(cr, cx, cy, cw, ch, color)
            label = k.split(":")[-1][:24]
            dev   = k.split(":")[0][:12]
            glow_text(cr, cx+12, cy+22, label, *color, size=12, bold=True)
            cr.select_font_face("Caveat", 0, 0); cr.set_font_size(10)
            cr.set_source_rgba(*C_DIM, 0.70)
            cr.move_to(cx+12, cy+36); cr.show_text(dev)

            # Big temp
            glow_text(cr, cx+cw-70, cy+22, f"{cur_temp:.1f}°C", *color, size=18, bold=True)

            # Sparkline
            hist_vals = [v for _, v in self.live.temp_hist.get(k, [])]
            if hist_vals:
                sparkline(cr, cx+8, cy+46, cw-16, ch-58, hist_vals, color, max_val=100)

            # Crit line
            temp_info = next(
                (t for dev_d in self.hw.get("hwmon",[])
                   for t in dev_d["temps"]
                   if f"{dev_d['name']}:{t['label']}" == k), None)
            if temp_info and temp_info.get("crit"):
                crit = temp_info["crit"]
                yc   = cy + 46 + (ch-58) - (crit/100)*(ch-58)*0.88
                cr.set_source_rgba(*C_RED, 0.45); cr.set_line_width(1)
                cr.move_to(cx+8, yc); cr.line_to(cx+cw-8, yc); cr.stroke()
                cr.select_font_face("Caveat", 0, 0); cr.set_font_size(9)
                cr.set_source_rgba(*C_RED, 0.70)
                cr.move_to(cx+cw-44, yc-2); cr.show_text(f"crit {crit}°")

            sketch_rect(cr, cx+2, cy+2, cw-4, ch-4, *color, thick=2.2, jitter=2.2)

    # ══════════════════════════════════════════════════════════════════════════
    #  PROFILES PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_profiles(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        box.set_margin_top(20); box.set_margin_bottom(20)
        box.set_margin_start(20); box.set_margin_end(20)
        box.set_spacing(20)

        # Left: profile list
        left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        left.set_size_request(280, -1)

        list_lbl = Gtk.Label(label="Saved Profiles")
        list_lbl.set_xalign(0)
        left.append(list_lbl)

        self._prof_listbox = Gtk.ListBox()
        self._prof_listbox.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._prof_listbox.connect("row-selected", self._on_prof_selected)
        self._refresh_profile_list()
        left.append(self._prof_listbox)

        apply_btn = Gtk.Button(label="⚡ Apply Profile")
        apply_btn.add_css_class("neon-btn")
        apply_btn.connect("clicked", self._on_apply_profile)
        left.append(apply_btn)

        new_btn = Gtk.Button(label="+ New Profile")
        new_btn.add_css_class("neon-btn-green")
        new_btn.connect("clicked", self._on_new_profile)
        left.append(new_btn)

        del_btn = Gtk.Button(label="Delete")
        del_btn.add_css_class("neon-btn-red")
        del_btn.connect("clicked", self._on_delete_profile)
        left.append(del_btn)

        box.append(left)

        # Right: detail editor
        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14)
        right.set_hexpand(True)

        da = self._da(self._draw_profile_detail, -1, 300)
        self._das["profiles_da"] = da
        right.append(da)

        # Governor selector
        gov_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        Gtk.Label(label="Governor:")
        gov_lbl = Gtk.Label(label="Governor:")
        gov_lbl.set_size_request(110, -1); gov_lbl.set_xalign(0)
        gov_box.append(gov_lbl)
        self._gov_combo = Gtk.DropDown.new_from_strings(
            self.hw.get("cpu", {}).get("governors", ["powersave","schedutil","performance"]))
        gov_box.append(self._gov_combo)
        right.append(gov_box)

        # Boost toggle
        boost_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        boost_lbl = Gtk.Label(label="CPU Boost:")
        boost_lbl.set_size_request(110, -1); boost_lbl.set_xalign(0)
        boost_box.append(boost_lbl)
        self._boost_sw = Gtk.Switch()
        self._boost_sw.set_active(True)
        boost_box.append(self._boost_sw)
        right.append(boost_box)

        # Fan PWM
        fan_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        fan_lbl = Gtk.Label(label="Fan %:")
        fan_lbl.set_size_request(110, -1); fan_lbl.set_xalign(0)
        fan_box.append(fan_lbl)
        self._fan_pct_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 0, 100, 1)
        self._fan_pct_scale.add_css_class("blue")
        self._fan_pct_scale.set_value(50)
        self._fan_pct_scale.set_hexpand(True)
        self._fan_pct_scale.set_draw_value(True)
        fan_box.append(self._fan_pct_scale)
        right.append(fan_box)

        # Name entry
        name_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        name_lbl = Gtk.Label(label="Name:")
        name_lbl.set_size_request(110, -1); name_lbl.set_xalign(0)
        name_box.append(name_lbl)
        self._prof_name_entry = Gtk.Entry()
        self._prof_name_entry.set_placeholder_text("Profile name...")
        self._prof_name_entry.set_hexpand(True)
        name_box.append(self._prof_name_entry)
        right.append(name_box)

        # Description
        desc_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        desc_lbl = Gtk.Label(label="Description:")
        desc_lbl.set_size_request(110, -1); desc_lbl.set_xalign(0)
        desc_box.append(desc_lbl)
        self._prof_desc_entry = Gtk.Entry()
        self._prof_desc_entry.set_placeholder_text("Short description...")
        self._prof_desc_entry.set_hexpand(True)
        desc_box.append(self._prof_desc_entry)
        right.append(desc_box)

        save_btn = Gtk.Button(label="Save Changes")
        save_btn.add_css_class("neon-btn-purple" if False else "neon-btn")
        save_btn.connect("clicked", self._on_save_profile_edit)
        right.append(save_btn)

        box.append(right)
        self._selected_prof_idx = 0
        return box

    def _refresh_profile_list(self):
        while True:
            row = self._prof_listbox.get_row_at_index(0) if hasattr(self, "_prof_listbox") else None
            if row is None: break
            self._prof_listbox.remove(row)
        for i, p in enumerate(self.profiles):
            lbl = Gtk.Label(label=f"  {p['name']}")
            lbl.set_xalign(0)
            lbl.set_size_request(240, 36)
            row = Gtk.ListBoxRow()
            row.set_child(lbl)
            self._prof_listbox.append(row)

    def _on_prof_selected(self, lb, row):
        if row is None: return
        idx = row.get_index()
        self._selected_prof_idx = idx
        p = self.profiles[idx]
        self._prof_name_entry.set_text(p.get("name",""))
        self._prof_desc_entry.set_text(p.get("description",""))
        govs = self.hw.get("cpu",{}).get("governors", [])
        gov  = p.get("governor","schedutil")
        if gov in govs:
            self._gov_combo.set_selected(govs.index(gov))
        self._boost_sw.set_active(p.get("boost", True))
        self._fan_pct_scale.set_value(p.get("fan_pwm_pct", 50))
        if "profiles_da" in self._das:
            self._das["profiles_da"].queue_draw()

    def _on_apply_profile(self, *_):
        idx = self._selected_prof_idx
        if 0 <= idx < len(self.profiles):
            msgs = apply_profile(self.profiles[idx], self.hw)
            self._toast("  ·  ".join(msgs[:3]))

    def _on_new_profile(self, *_):
        self.profiles.append({
            "name": "New Profile",
            "governor": "schedutil",
            "boost": True,
            "fan_pwm_pct": 50,
            "description": "Custom profile",
        })
        save_profiles(self.profiles)
        self._refresh_profile_list()
        self._toast("New profile created — edit and save it")

    def _on_delete_profile(self, *_):
        idx = getattr(self, "_selected_prof_idx", 0)
        if 0 <= idx < len(self.profiles) and len(self.profiles) > 1:
            name = self.profiles[idx]["name"]
            self.profiles.pop(idx)
            self._selected_prof_idx = max(0, idx-1)
            save_profiles(self.profiles)
            self._refresh_profile_list()
            self._toast(f"Deleted: {name}")

    def _on_save_profile_edit(self, *_):
        idx = getattr(self, "_selected_prof_idx", 0)
        if 0 <= idx < len(self.profiles):
            govs = self.hw.get("cpu",{}).get("governors", ["schedutil"])
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
            self._refresh_profile_list()
            self._toast(f"Saved: {self.profiles[idx]['name']}")

    def _draw_profile_detail(self, area, cr, w, h, _):
        cr.set_source_rgb(*C_BG); cr.rectangle(0,0,w,h); cr.fill()
        dot_grid(cr, 0, 0, w, h, 26)
        idx = getattr(self, "_selected_prof_idx", 0)
        if not (0 <= idx < len(self.profiles)):
            return
        p = self.profiles[idx]
        name = p.get("name", "Profile")
        glow_text(cr, 20, 44, name, *C_PURPLE, size=26, bold=True)
        cr.select_font_face("Caveat", 0, 0); cr.set_font_size(13)
        cr.set_source_rgba(*C_DIM, 0.80)
        cr.move_to(20, 68); cr.show_text(p.get("description",""))
        items = [
            (f"Governor:  {p.get('governor','?')}", C_YELLOW),
            (f"CPU Boost: {'ON' if p.get('boost') else 'OFF'}", C_GREEN if p.get('boost') else C_DIM),
            (f"Fan Speed: {p.get('fan_pwm_pct',50)}%", C_BLUE),
        ]
        for i, (txt, col) in enumerate(items):
            glow_text(cr, 20, 100 + i*28, txt, *col, size=14)
        # Fan pct bar
        hbar(cr, 20, 190, w-40, 14, p.get("fan_pwm_pct",50), C_BLUE)
        sketch_rect(cr, 8, 8, w-16, h-16, *C_PURPLE, thick=2.0, jitter=2.2)

    # ══════════════════════════════════════════════════════════════════════════
    #  RGB PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_rgb(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.set_margin_top(20); box.set_margin_bottom(20)
        box.set_margin_start(20); box.set_margin_end(20)
        box.set_spacing(14)
        da = self._da(self._draw_rgb, -1, 200)
        self._das["rgb"] = da
        box.append(da)

        # OpenRGB connection status
        status_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._rgb_status_lbl = Gtk.Label(label="Checking OpenRGB...")
        self._rgb_status_lbl.set_xalign(0)
        status_box.append(self._rgb_status_lbl)
        conn_btn = Gtk.Button(label="Connect to OpenRGB")
        conn_btn.add_css_class("neon-btn-green")
        conn_btn.connect("clicked", self._rgb_connect)
        status_box.append(conn_btn)
        box.append(status_box)

        # NYXUS preset colors
        presets_lbl = Gtk.Label(label="NYXUS RGB Presets")
        presets_lbl.set_xalign(0)
        box.append(presets_lbl)
        presets_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for name, hex_col, css in [
            ("NyX Default", "#ff00ff", "neon-btn"),
            ("Chill Blue",  "#0088ff", "neon-btn-blue"),
            ("Ghost Green", "#39ff14", "neon-btn-green"),
            ("Solar",       "#ff5500", "neon-btn-orange"),
            ("All Off",     "#000000", "neon-btn-red"),
        ]:
            b = Gtk.Button(label=name)
            b.add_css_class(css)
            b.connect("clicked", self._on_rgb_preset, hex_col)
            presets_row.append(b)
        box.append(presets_row)

        # Audio sync toggle
        async_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        al = Gtk.Label(label="Audio Sync (requires OpenRGB plug-in):")
        al.set_xalign(0)
        async_box.append(al)
        self._audio_sync_sw = Gtk.Switch()
        async_box.append(self._audio_sync_sw)
        box.append(async_box)

        # Instructions
        info = Gtk.Label()
        info.set_markup(
            "OpenRGB must be running:  <b>openrgb --server</b>\n"
            "Install:  <b>sudo pacman -S openrgb</b>   then launch and enable server mode.\n"
            "State-linked RGB: neon pink at idle, red when thermals &gt; 85°C, blue on battery."
        )
        info.set_xalign(0)
        box.append(info)

        self._rgb_connect(None)
        return box

    def _rgb_connect(self, *_):
        try:
            import urllib.request
            with urllib.request.urlopen("http://localhost:6742/api/devices", timeout=1) as r:
                devs = json.loads(r.read())
                self._rgb_devices = devs
                self._rgb_status_lbl.set_text(f"OpenRGB: {len(devs)} device(s) connected")
        except Exception:
            self._rgb_devices = []
            self._rgb_status_lbl.set_text("OpenRGB not running. Start with: openrgb --server")

    def _on_rgb_preset(self, btn, hex_col):
        r = int(hex_col[1:3], 16)
        g = int(hex_col[3:5], 16)
        b = int(hex_col[5:7], 16)
        for i, dev in enumerate(getattr(self, "_rgb_devices", [])):
            try:
                import urllib.request
                payload = json.dumps({
                    "mode": 0,
                    "colors": [{"red": r, "green": g, "blue": b}]
                }).encode()
                req = urllib.request.Request(
                    f"http://localhost:6742/api/devices/{i}/resizable",
                    data=payload, method="POST",
                    headers={"Content-Type": "application/json"}
                )
                urllib.request.urlopen(req, timeout=2)
            except Exception:
                pass
        self._toast(f"RGB set to {hex_col} on {len(getattr(self,'_rgb_devices',[]))} device(s)")

    def _draw_rgb(self, area, cr, w, h, _):
        cr.set_source_rgb(*C_BG); cr.rectangle(0,0,w,h); cr.fill()
        dot_grid(cr, 0, 0, w, h, 24)
        glow_text(cr, 16, 34, "RGB Control", *C_GREEN, size=16, bold=True)
        # Neon light simulation
        t = self._anim_t
        for i, (r, g, b) in enumerate(PALETTE):
            cx = 80 + i * 110
            cy = 130
            pulse = 0.4 + 0.35*math.sin(t*2 + i*1.1)
            cr.set_source_rgba(r, g, b, pulse*0.22)
            cr.arc(cx, cy, 36, 0, math.pi*2); cr.fill()
            cr.set_source_rgba(r, g, b, 0.85)
            cr.arc(cx, cy, 18, 0, math.pi*2); cr.fill()
            cr.set_source_rgba(1,1,1,0.55)
            cr.arc(cx-5, cy-5, 5, 0, math.pi*2); cr.fill()
        sketch_rect(cr, 8, 8, w-16, h-16, *C_GREEN, thick=2.0, jitter=2.0)

    # ══════════════════════════════════════════════════════════════════════════
    #  POWER PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_power(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_margin_top(20); box.set_margin_bottom(20)
        box.set_margin_start(24); box.set_margin_end(24)

        da = self._da(self._draw_power_header, -1, 120)
        self._das["power"] = da
        box.append(da)

        # CPU Governor
        gov_frame_lbl = Gtk.Label(label="CPU Governor")
        gov_frame_lbl.set_xalign(0)
        box.append(gov_frame_lbl)
        gov_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        govs = self.hw.get("cpu",{}).get("governors", ["powersave","schedutil","performance"])
        self._power_gov_btns = {}
        for gov in govs:
            b = Gtk.Button(label=gov)
            css = {"powersave":"neon-btn-blue","schedutil":"neon-btn-green",
                   "performance":"neon-btn-orange","conservative":"neon-btn"}.get(gov,"neon-btn")
            b.add_css_class(css)
            b.connect("clicked", self._on_set_governor, gov)
            gov_row.append(b)
            self._power_gov_btns[gov] = b
        box.append(gov_row)

        # CPU Boost
        boost_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bl = Gtk.Label(label="CPU Boost:")
        bl.set_size_request(140, -1); bl.set_xalign(0)
        boost_row.append(bl)
        self._power_boost_sw = Gtk.Switch()
        self._power_boost_sw.set_active(self.hw.get("cpu",{}).get("boost", True))
        self._power_boost_sw.connect("notify::active", self._on_set_boost)
        boost_row.append(self._power_boost_sw)
        boost_row.append(Gtk.Label(label="  (requires /sys/devices/system/cpu/cpufreq/boost)"))
        box.append(boost_row)

        if not self.hw.get("cpu",{}).get("boost_supported"):
            bl2 = Gtk.Label(label="CPU boost toggle not supported on this machine.")
            bl2.set_xalign(0)
            box.append(bl2)

        # NVIDIA GPU Power Limit
        gpu = self.hw.get("gpu",{})
        if gpu.get("vendor") == "nvidia":
            sep = Gtk.Label(label="GPU Power Limit  (NVIDIA)")
            sep.set_xalign(0); sep.set_margin_top(12)
            box.append(sep)
            gpu_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            gl = Gtk.Label(label="Power limit (W):")
            gl.set_size_request(160,-1); gl.set_xalign(0)
            gpu_row.append(gl)
            self._gpu_power_scale = Gtk.Scale.new_with_range(
                Gtk.Orientation.HORIZONTAL,
                50, gpu.get("power_limit", 200), 5)
            self._gpu_power_scale.add_css_class("orange")
            self._gpu_power_scale.set_value(gpu.get("power_limit", 150))
            self._gpu_power_scale.set_hexpand(True)
            self._gpu_power_scale.set_draw_value(True)
            gpu_row.append(self._gpu_power_scale)
            apply_gpu = Gtk.Button(label="Apply")
            apply_gpu.add_css_class("neon-btn-orange")
            apply_gpu.connect("clicked", self._on_set_gpu_power)
            gpu_row.append(apply_gpu)
            box.append(gpu_row)

        # Battery charge limit
        batt = self.hw.get("battery",{}) or {}
        if batt.get("charge_limit_path"):
            sep2 = Gtk.Label(label="Battery Charge Limit")
            sep2.set_xalign(0); sep2.set_margin_top(12)
            box.append(sep2)
            brow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
            blbl = Gtk.Label(label="Max charge %:")
            blbl.set_size_request(160,-1); blbl.set_xalign(0)
            brow.append(blbl)
            self._batt_limit_scale = Gtk.Scale.new_with_range(
                Gtk.Orientation.HORIZONTAL, 50, 100, 1)
            self._batt_limit_scale.add_css_class("green")
            self._batt_limit_scale.set_value(80)
            self._batt_limit_scale.set_hexpand(True)
            self._batt_limit_scale.set_draw_value(True)
            brow.append(self._batt_limit_scale)
            apply_batt = Gtk.Button(label="Apply")
            apply_batt.add_css_class("neon-btn-green")
            apply_batt.connect("clicked", self._on_set_batt_limit)
            brow.append(apply_batt)
            box.append(brow)

        return box

    def _on_set_governor(self, btn, gov):
        cpus = list(Path("/sys/devices/system/cpu").glob("cpu[0-9]*/cpufreq/scaling_governor"))
        failed = 0
        for cpu_path in cpus:
            ok, _ = _write_priv(str(cpu_path), gov)
            if not ok: failed += 1
        if failed:
            self._toast(f"Failed to set governor on {failed} CPUs — may need pkexec/polkit")
        else:
            self._toast(f"CPU governor → {gov}")
        self._das.get("power") and self._das["power"].queue_draw()

    def _on_set_boost(self, sw, _):
        active = sw.get_active()
        ok, err = _write_priv("/sys/devices/system/cpu/cpufreq/boost", "1" if active else "0")
        self._toast(f"CPU boost {'enabled' if active else 'disabled'}" if ok
                    else f"Boost change failed: {err}")

    def _on_set_gpu_power(self, *_):
        limit = int(self._gpu_power_scale.get_value())
        try:
            subprocess.run(
                ["nvidia-smi", f"--power-limit={limit}"],
                check=True, capture_output=True, timeout=5)
            self._toast(f"GPU power limit set to {limit} W")
        except Exception as e:
            self._toast(f"GPU power limit failed: {e}")

    def _on_set_batt_limit(self, *_):
        limit = int(self._batt_limit_scale.get_value())
        batt  = self.hw.get("battery",{}) or {}
        path  = batt.get("charge_limit_path","")
        if path:
            ok, err = _write_priv(path, str(limit))
            self._toast(f"Battery limit → {limit}%" if ok else f"Battery limit failed: {err}")

    def _draw_power_header(self, area, cr, w, h, _):
        cr.set_source_rgb(*C_BG); cr.rectangle(0,0,w,h); cr.fill()
        dot_grid(cr, 0, 0, w, h, 24)
        glow_text(cr, 16, 34, "Power Management", *C_YELLOW, size=16, bold=True)
        gov = self.live.governor
        boost = "BOOST ON" if self.live.boost else "BOOST OFF"
        freq  = f"{self.live.cpu_freq:.0f} MHz" if self.live.cpu_freq else ""
        cr.select_font_face("Caveat", 0, 0); cr.set_font_size(13)
        cr.set_source_rgba(*C_DIM, 0.80)
        cr.move_to(16, 58)
        cr.show_text(f"Current:  governor = {gov}   {boost}   {freq}")
        # Governor visual
        govs = self.hw.get("cpu",{}).get("governors", [])
        bw = min(140, (w - 32) / max(len(govs), 1))
        for i, g in enumerate(govs):
            col = (C_BLUE if g=="powersave" else C_GREEN if g=="schedutil"
                   else C_ORANGE if g=="performance" else C_DIM)
            active = g == gov
            fill = (*col, 0.25 if active else 0.06)
            sketch_rect(cr, 16+i*bw, 70, bw-8, 38, *col, thick=2.2 if active else 1.2,
                        jitter=2.0, fill_rgba=fill)
            cr.select_font_face("Caveat", 0, 1 if active else 0)
            cr.set_font_size(11)
            cr.set_source_rgba(*col, 0.90 if active else 0.55)
            ext = cr.text_extents(g)
            cr.move_to(16+i*bw + (bw-8-ext.width)/2 - ext.x_bearing, 94)
            cr.show_text(g)
        sketch_rect(cr, 4, 4, w-8, h-8, *C_YELLOW, thick=1.8, jitter=1.8)

    # ══════════════════════════════════════════════════════════════════════════
    #  PROCESSES PAGE
    # ══════════════════════════════════════════════════════════════════════════

    def _build_processes(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # Toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_margin_top(12); toolbar.set_margin_start(12)
        toolbar.set_margin_end(12); toolbar.set_margin_bottom(8)

        search = Gtk.SearchEntry()
        search.set_placeholder_text("Filter processes...")
        search.set_hexpand(True)
        search.connect("search-changed", self._on_proc_search)
        toolbar.append(search)

        renice_btn = Gtk.Button(label="Raise Priority (nice -5)")
        renice_btn.add_css_class("neon-btn-green")
        renice_btn.connect("clicked", self._on_renice)
        toolbar.append(renice_btn)

        lower_btn = Gtk.Button(label="Lower Priority (nice +10)")
        lower_btn.add_css_class("neon-btn-blue")
        lower_btn.connect("clicked", self._on_lower_nice)
        toolbar.append(lower_btn)

        kill_btn = Gtk.Button(label="Kill")
        kill_btn.add_css_class("neon-btn-red")
        kill_btn.connect("clicked", self._on_kill_proc)
        toolbar.append(kill_btn)

        box.append(toolbar)

        # Process list as a Gtk.ListView
        self._proc_store = Gtk.StringList()
        self._proc_filter_text = ""
        self._proc_data: list = []

        col_model = Gtk.ColumnView()
        col_model.set_vexpand(True)
        col_model.set_show_row_separators(True)

        # We'll use a simpler TreeView approach
        self._proc_tv_store = Gtk.ListStore(int, str, float, float, int, str)
        self._proc_tv = Gtk.TreeView(model=self._proc_tv_store)
        self._proc_tv.set_vexpand(True)

        cols_def = [
            ("PID",   0, 70),
            ("Name",  1, 180),
            ("CPU %", 2, 80),
            ("MEM %", 3, 80),
            ("Nice",  4, 60),
            ("Stat",  5, 60),
        ]
        for title, col_idx, width in cols_def:
            renderer = Gtk.CellRendererText()
            col = Gtk.TreeViewColumn(title, renderer, text=col_idx)
            col.set_fixed_width(width)
            col.set_resizable(True)
            col.set_sort_column_id(col_idx)
            self._proc_tv.append_column(col)

        self._proc_tv.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        self._proc_tv.set_headers_visible(True)

        sw = Gtk.ScrolledWindow()
        sw.set_vexpand(True)
        sw.set_child(self._proc_tv)
        box.append(sw)

        self._refresh_proc_tv()
        return box

    def _refresh_proc_tv(self):
        flt = getattr(self, "_proc_filter_text", "")
        self._proc_tv_store.clear()
        for p in self.live.procs:
            if flt and flt.lower() not in p["name"].lower():
                continue
            self._proc_tv_store.append([
                p["pid"], p["name"],
                p["cpu"], p["mem"],
                p["nice"], p["stat"]
            ])

    def _on_proc_search(self, entry):
        self._proc_filter_text = entry.get_text()
        self._refresh_proc_tv()

    def _selected_pid(self) -> int | None:
        sel = self._proc_tv.get_selection()
        model, it = sel.get_selected()
        if it is None: return None
        return model.get_value(it, 0)

    def _on_renice(self, *_):
        pid = self._selected_pid()
        if pid is None:
            self._toast("Select a process first"); return
        try:
            subprocess.run(["renice", "-n", "-5", "-p", str(pid)], check=True, capture_output=True)
            self._toast(f"PID {pid}: priority raised (nice -5)")
        except Exception as e:
            self._toast(f"renice failed: {e}")

    def _on_lower_nice(self, *_):
        pid = self._selected_pid()
        if pid is None:
            self._toast("Select a process first"); return
        try:
            subprocess.run(["renice", "-n", "+10", "-p", str(pid)], check=True, capture_output=True)
            self._toast(f"PID {pid}: priority lowered (nice +10)")
        except Exception as e:
            self._toast(f"renice failed: {e}")

    def _on_kill_proc(self, *_):
        pid = self._selected_pid()
        if pid is None:
            self._toast("Select a process first"); return
        try:
            os.kill(pid, signal.SIGTERM)
            self._toast(f"SIGTERM sent to PID {pid}")
        except Exception as e:
            self._toast(f"Kill failed: {e}")
        GLib.timeout_add(800, lambda: (self._refresh_proc_tv(), False))

    def _refresh_ui(self):
        for da in self._das.values():
            da.queue_draw()
        self._refresh_fan_labels()
        self._refresh_proc_tv()
        return GLib.SOURCE_REMOVE


# ══════════════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    try:
        NyxusControl().run(None)
    except Exception:
        log = "/tmp/nyxus-control.log"
        with open(log, "w") as f:
            traceback.print_exc(file=f)
        print(f"NYXUS Control crashed — see {log}")
        sys.exit(1)
