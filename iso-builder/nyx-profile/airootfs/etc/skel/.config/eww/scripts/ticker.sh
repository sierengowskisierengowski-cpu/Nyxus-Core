#!/usr/bin/env bash
# NYXUS · EWW · top-bar ticker — rainbow Pango marquee (rev 2026-07-10)
# Streams {"text":"<markup>…","tooltip":"…"} for :markup true label.
set -u
export LC_ALL=C.UTF-8

[[ -r "${HOME}/.config/eww/nyxus.conf" ]] && . "${HOME}/.config/eww/nyxus.conf" 2>/dev/null || true
WINDOW="${NYXUS_TICKER_COLS:-180}"

exec python3 -u - "$WINDOW" <<'PY'
import json, os, random, subprocess, sys, time

WINDOW = int(sys.argv[1])
HOME = os.path.expanduser("~")
CACHE_DIR = os.path.join(os.environ.get("XDG_RUNTIME_DIR", "/tmp"), "nyxus-ticker")
os.makedirs(CACHE_DIR, exist_ok=True)
CACHE_SEGS = os.path.join(CACHE_DIR, "segments.json")
CACHE_TS = os.path.join(CACHE_DIR, "ts")
CACHE_OFFSET = os.path.join(CACHE_DIR, "offset")
CACHE_TIP = os.path.join(CACHE_DIR, "tooltip")
REGEN_SECS = 30

ACCENT = os.path.join(HOME, ".config/nyxus/accent.json")
COLORS = {
    "brand": "#ff4994",
    "cpu": "#26ffb7",
    "mem": "#a06bff",
    "temp": "#ffb45e",
    "net": "#3ad8ff",
    "disk": "#ff8b26",
    "time": "#ff8b26",
    "meta": "#26ff39",
    "dim": "#7e8794",
}
try:
    with open(ACCENT) as f:
        acc = json.load(f)
    active = acc.get("active", "wallpaper")
    preset = acc.get("presets", {}).get(active, acc.get("presets", {}).get("wallpaper", {}))
    if preset:
        COLORS["brand"] = preset.get("primary", COLORS["brand"])
        COLORS["cpu"] = preset.get("ok", COLORS["cpu"])
        COLORS["mem"] = preset.get("ok", COLORS["mem"])
        COLORS["temp"] = preset.get("warn", COLORS["temp"])
        COLORS["net"] = preset.get("secondary", COLORS["net"])
        COLORS["disk"] = preset.get("warn", COLORS["disk"])
        COLORS["time"] = preset.get("warn", COLORS["time"])
        COLORS["meta"] = preset.get("secondary", COLORS["meta"])
except (OSError, ValueError, KeyError):
    pass

HUE_FOR = {
    "NYXUS": "brand", "DARK": "brand", "MIRROR": "brand", "LIVE": "brand",
    "TIME": "time", "HOST": "brand", "KERNEL": "meta", "UPTIME": "meta",
    "LOAD": "meta", "CPU": "cpu", "MEM": "mem", "TEMP": "temp",
    "DISK": "disk", "PROCS": "dim", "USERS": "dim", "NET": "net",
    "GW": "net", "WIFI": "net", "PKGS": "dim",
}


def hue_key(seg_text):
    parts = seg_text.split()
    if len(parts) >= 2 and parts[0] == "▌":
        return HUE_FOR.get(parts[1].rstrip("·"), "meta")
    return "meta"


def gather_stats():
    def sh(cmd):
        try:
            return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL, timeout=3).strip()
        except Exception:
            return ""

    up = sh("uptime -p 2>/dev/null | sed 's/^up //'")
    load = sh("awk '{print $1, $2, $3}' /proc/loadavg 2>/dev/null")
    procs = sh("ps -e --no-headers 2>/dev/null | wc -l")
    users = sh("who | wc -l")
    kern = sh("uname -r 2>/dev/null")
    host = sh("hostname 2>/dev/null")
    disk = sh("df -h --output=pcent / 2>/dev/null | tail -1 | tr -d ' %'")
    inet = sh("ip -4 addr show 2>/dev/null | awk '/inet /{print $2}' | grep -v '^127' | head -1")
    gw = sh("ip route 2>/dev/null | awk '/default/{print $3; exit}'")
    cpu = sh("top -bn1 2>/dev/null | awk '/Cpu\\(s\\)/{printf \"%d\", $2+$4}'")
    mem = sh("free -m 2>/dev/null | awk '/Mem:/{printf \"%d\", $3/$2*100}'")
    temp = "--"
    tz = "/sys/class/thermal/thermal_zone0/temp"
    if os.path.isfile(tz):
        try:
            temp = f"{int(open(tz).read().strip()) // 1000}°C"
        except (OSError, ValueError):
            pass
    wifi = sh("nmcli -t -f IN-USE,SSID,SIGNAL device wifi list 2>/dev/null | awk -F: '/^\\*/{print $2 \" \" $3 \"%\"; exit}'")
    pkg = sh("pacman -Qq 2>/dev/null | wc -l")
    clock = time.strftime("%H:%M:%S")
    return [
        ("▌ NYXUS · DARK MIRROR · LIVE", True),
        (f"▌ TIME {clock}", False),
        (f"▌ HOST {host or '?'}", False),
        (f"▌ KERNEL {kern or '?'}", False),
        (f"▌ UPTIME {up or '?'}", False),
        (f"▌ LOAD {load or '? ? ?'}", False),
        (f"▌ CPU {cpu or '?'}%", False),
        (f"▌ MEM {mem or '?'}%", False),
        (f"▌ TEMP {temp}", False),
        (f"▌ DISK {disk or '?'}%", False),
        (f"▌ PROCS {procs or '?'}", False),
        (f"▌ USERS {users or '?'}", False),
        (f"▌ NET {inet or 'offline'}", False),
        (f"▌ GW {gw or '—'}", False),
        (f"▌ WIFI {wifi or '—'}", False),
        (f"▌ PKGS {pkg or '?'}", False),
    ]


def regen_segments():
    segs = gather_stats()
    random.shuffle(segs)
    colored = []
    for text, bold in segs:
        colored.append({
            "text": text + "     ",
            "color": COLORS[hue_key(text)],
            "bold": bold or text.startswith("▌ NYXUS"),
        })
    with open(CACHE_SEGS, "w") as f:
        json.dump(colored, f)
    with open(CACHE_TS, "w") as f:
        f.write(str(int(time.time())))
    tip = f"NYXUS LIVE · CPU {colored[5]['text'].split()[-1] if len(colored) > 5 else '?'} · scroll"
    with open(CACHE_TIP, "w") as f:
        f.write(tip)


def load_segments():
    with open(CACHE_SEGS) as f:
        return json.load(f)


def build_ribbon(segments):
    chars = []
    for seg in segments:
        color = seg["color"]
        bold = seg.get("bold", False)
        for ch in seg["text"]:
            chars.append((ch, color, bold))
    return chars


def spans_from_window(chars):
    if not chars:
        return ""
    spans = []
    cur_color = chars[0][1]
    cur_bold = chars[0][2]
    buf = []
    for ch, color, bold in chars:
        if color != cur_color or bold != cur_bold:
            spans.append((cur_color, cur_bold, "".join(buf)))
            buf = []
            cur_color, cur_bold = color, bold
        buf.append(ch)
    if buf:
        spans.append((cur_color, cur_bold, "".join(buf)))
    parts = []
    for color, bold, text in spans:
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if bold:
            parts.append(f"<span foreground='{color}' weight='bold'>{text}</span>")
        else:
            parts.append(f"<span foreground='{color}'>{text}</span>")
    return "".join(parts)


now = int(time.time())
last = 0
if os.path.isfile(CACHE_TS):
    try:
        last = int(open(CACHE_TS).read().strip())
    except ValueError:
        last = 0

if not os.path.isfile(CACHE_SEGS) or now - last >= REGEN_SECS:
    regen_segments()

segments = load_segments()
ribbon = build_ribbon(segments)
rlen = len(ribbon)
if rlen < WINDOW + 1:
    while len(ribbon) < WINDOW + 1:
        ribbon = ribbon + ribbon
    rlen = len(ribbon)

off = 0
if os.path.isfile(CACHE_OFFSET):
    try:
        off = int(open(CACHE_OFFSET).read().strip())
    except ValueError:
        off = 0
off = (off + 1) % rlen
with open(CACHE_OFFSET, "w") as f:
    f.write(str(off))

double = ribbon + ribbon
window = double[off:off + WINDOW]
markup = spans_from_window(window)
tooltip = open(CACHE_TIP).read().strip() if os.path.isfile(CACHE_TIP) else "NYXUS LIVE"
print(json.dumps({"text": markup, "tooltip": tooltip}), flush=True)
PY
