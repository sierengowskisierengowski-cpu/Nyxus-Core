#!/usr/bin/env python3
"""
NYXUS ACTION CENTER
~/.config/waybar/quicksettings.py

Windows-10-style Action Center with 15 quick-tile grid, inline WiFi flyout,
volume + device picker, brightness slider, and notification list.
EVERY action is wired to a real backend (NetworkManager / bluetoothctl /
wpctl / pactl / brightnessctl / dunstctl / hyprshade or wlsunset / grim+slurp).

(c) 2026 JOSEPH SIERENGOWSKI - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""


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
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib, Pango

import subprocess, json, os, sys, shlex, time, re
from datetime import datetime


# ════════════════════════════════════════════════════════════════════════════════
# BACKEND HELPERS - thin wrappers around real system tools
# ════════════════════════════════════════════════════════════════════════════════

def sh(cmd, capture=True, timeout=5):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=capture,
                           text=True, timeout=timeout)
        return r.stdout.strip() if capture else (r.returncode == 0)
    except Exception:
        return "" if capture else False


def has(cmd):
    return bool(sh(f"command -v {shlex.quote(cmd)}"))


def detached(cmd):
    try:
        subprocess.Popen(cmd, shell=True,
                         stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL,
                         start_new_session=True)
        return True
    except Exception:
        return False


# ── audio (pipewire / wpctl + pactl) ─────────────────────────────────────────
def vol_get():
    raw = sh("wpctl get-volume @DEFAULT_AUDIO_SINK@")
    try:
        return min(100, int(float(raw.split()[1]) * 100))
    except Exception:
        return 50


def vol_set(v):
    sh(f"wpctl set-volume @DEFAULT_AUDIO_SINK@ {max(0,min(100,int(v)))/100:.2f}", False)


def vol_muted():
    return "MUTED" in sh("wpctl get-volume @DEFAULT_AUDIO_SINK@").upper()


def vol_mute_toggle():
    sh("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle", False)


def vol_sinks():
    """Return [(id:int, friendly:str, raw:str, is_default:bool), ...]."""
    out = sh("pactl list short sinks") or ""
    # Get default sink name
    default = sh("pactl get-default-sink") or ""
    # Get descriptions
    descs = {}
    raw = sh("pactl list sinks") or ""
    cur_name = None
    for ln in raw.splitlines():
        s = ln.strip()
        m = re.match(r"Name:\s*(\S+)", s)
        if m:
            cur_name = m.group(1); continue
        m = re.match(r"Description:\s*(.+)", s)
        if m and cur_name:
            descs[cur_name] = m.group(1).strip()
            cur_name = None
    sinks = []
    for ln in out.splitlines():
        cols = ln.split("\t")
        if len(cols) < 2:
            continue
        try:
            sid = int(cols[0])
        except Exception:
            continue
        name = cols[1]
        desc = descs.get(name, name)
        sinks.append((sid, sink_label(desc, name), name, name == default))
    return sinks


def vol_set_default(sink_id_or_name):
    sh(f"pactl set-default-sink {shlex.quote(str(sink_id_or_name))}", False)


def sink_label(desc, name):
    """Map a sink description to a Windows-10 style friendly label."""
    n = (desc + " " + name).lower()
    # Bluetooth
    if "bluez" in n or "blueto" in n:
        m = re.search(r"-\s*([^-]+)$", desc)
        brand = (m.group(1).strip() if m else desc).strip()
        return f"Headphones ({brand})"
    # USB / external headset
    if "usb" in n and ("head" in n or "mic" in n):
        return f"Headphones ({desc})"
    # HDMI / S/PDIF / digital
    if "hdmi" in n or "spdif" in n or "iec958" in n or "digital" in n or "optical" in n:
        return "Digital Output / Optical"
    # Built-in / analog speakers
    if ("analog" in n or "built-in" in n or "internal" in n
            or "speaker" in n or "alc" in n or "snd_hda" in n):
        return "Speaker (High Definition Audio Device)"
    return desc


# ── brightness ────────────────────────────────────────────────────────────────
def has_backlight():
    if not has("brightnessctl"):
        return False
    return bool(sh("brightnessctl --list 2>/dev/null"))


def bright_get():
    try:
        cur = int(sh("brightnessctl get") or 0)
        mx = int(sh("brightnessctl max") or 1)
        return int(cur / mx * 100) if mx else 50
    except Exception:
        return 50


def bright_set(v):
    sh(f"brightnessctl set {max(1,min(100,int(v)))}%", False)


# ── WiFi (NetworkManager) ─────────────────────────────────────────────────────
def wifi_on():
    return "enabled" in sh("nmcli radio wifi").lower()


def wifi_set(on):
    sh(f"nmcli radio wifi {'on' if on else 'off'}", False)


def wifi_active():
    out = sh("nmcli -t -f ACTIVE,SSID dev wifi 2>/dev/null")
    for ln in out.splitlines():
        if ln.startswith("yes:"):
            return ln[4:]
    return ""


def has_internet():
    return sh("ping -c1 -W2 -q 1.1.1.1 >/dev/null 2>&1; echo $?").strip() == "0"


def wifi_status_label(security):
    inet = has_internet()
    secured = security and security != "--"
    if not inet:
        return "No Internet, secured" if secured else "No Internet, open"
    return "Connected, secured" if secured else "Connected, open"


def wifi_scan():
    sh("nmcli dev wifi rescan 2>/dev/null", False, timeout=8)
    out = sh("nmcli -t -f IN-USE,SSID,SECURITY,SIGNAL dev wifi list 2>/dev/null")
    nets, seen = [], set()
    for ln in out.splitlines():
        parts = re.split(r"(?<!\\):", ln)
        if len(parts) < 4:
            continue
        in_use = parts[0].strip() == "*"
        ssid = parts[1].replace("\\:", ":").strip()
        sec = parts[2].strip() or "--"
        try:
            sig = int(parts[3])
        except Exception:
            sig = 0
        if not ssid or ssid in seen:
            continue
        seen.add(ssid)
        nets.append({"ssid": ssid, "sec": sec, "sig": sig, "active": in_use})
    nets.sort(key=lambda n: (-n["sig"], n["ssid"].lower()))
    return nets


def wifi_connect(ssid, password=None, autoconnect=True):
    if password:
        cmd = (f"nmcli dev wifi connect {shlex.quote(ssid)} "
               f"password {shlex.quote(password)}")
    else:
        cmd = f"nmcli dev wifi connect {shlex.quote(ssid)}"
    out = sh(cmd, timeout=30)
    ok = "successfully activated" in out.lower()
    if ok and not autoconnect:
        sh(f"nmcli connection modify {shlex.quote(ssid)} connection.autoconnect no",
           False)
    return ok, (out.splitlines()[-1] if out else "Connection failed")


def wifi_disconnect(ssid):
    sh(f"nmcli connection down id {shlex.quote(ssid)}", False, timeout=10)


# ── Bluetooth ─────────────────────────────────────────────────────────────────
def bt_on():
    return "yes" in sh("bluetoothctl show 2>/dev/null | grep -i Powered").lower()


def bt_set(on):
    sh(f"bluetoothctl power {'on' if on else 'off'}", False, timeout=8)


# ── VPN (NetworkManager) ──────────────────────────────────────────────────────
def vpn_list():
    out = sh("nmcli -t -f NAME,TYPE,STATE connection show 2>/dev/null")
    vpns = []
    for ln in out.splitlines():
        parts = re.split(r"(?<!\\):", ln)
        if len(parts) < 3:
            continue
        name, typ, state = parts[0], parts[1], parts[2]
        tl = typ.lower()
        if "vpn" in tl or "wireguard" in tl:
            vpns.append((name.replace("\\:", ":"), state == "activated"))
    return vpns


def vpn_any_on():
    return any(active for _, active in vpn_list())


def vpn_toggle(_unused_state):
    vpns = vpn_list()
    if not vpns:
        return False
    if vpn_any_on():
        for name, active in vpns:
            if active:
                sh(f"nmcli connection down id {shlex.quote(name)}",
                   False, timeout=10)
    else:
        name = vpns[0][0]
        sh(f"nmcli connection up id {shlex.quote(name)}", False, timeout=20)
    return True


# ── Mobile Hotspot ───────────────────────────────────────────────────────────
HOTSPOT_NAME = "NYXUS-Hotspot"
HOTSPOT_PASS = "nyxus2026"


def hotspot_on():
    out = sh("nmcli -t -f NAME,STATE connection show --active 2>/dev/null")
    return any(ln.startswith(HOTSPOT_NAME + ":") and "activated" in ln
               for ln in out.splitlines())


def hotspot_set(on):
    if on:
        dev = ""
        for ln in sh("nmcli -t -f DEVICE,TYPE device 2>/dev/null").splitlines():
            parts = ln.split(":") + [""]
            if parts[1] == "wifi":
                dev = parts[0]; break
        if not dev:
            return False
        sh(f"nmcli dev wifi hotspot ifname {shlex.quote(dev)} "
           f"con-name {HOTSPOT_NAME} ssid {HOTSPOT_NAME} "
           f"password {HOTSPOT_PASS}", False, timeout=12)
    else:
        sh(f"nmcli connection down {HOTSPOT_NAME}", False, timeout=8)
    return True


# ── Airplane Mode ─────────────────────────────────────────────────────────────
def airplane_on():
    return "disabled" in sh("nmcli radio all").lower()


def airplane_set(on):
    sh(f"nmcli radio all {'off' if on else 'on'}", False)
    if on:
        sh("bluetoothctl power off", False, timeout=5)


# ── Tablet Mode (state file + touch transform) ────────────────────────────────
TABLET_FLAG = os.path.expanduser("~/.config/nyxus/tablet.state")


def tablet_on():
    return os.path.exists(TABLET_FLAG)


def tablet_set(on):
    os.makedirs(os.path.dirname(TABLET_FLAG), exist_ok=True)
    if on:
        open(TABLET_FLAG, "w").write("1")
        sh("hyprctl keyword input:touchpad:natural_scroll true", False)
        sh("hyprctl keyword cursor:inactive_timeout 0", False)
    else:
        try: os.remove(TABLET_FLAG)
        except Exception: pass
        sh("hyprctl keyword input:touchpad:natural_scroll false", False)
        sh("hyprctl keyword cursor:inactive_timeout 5", False)


# ── Battery Saver ─────────────────────────────────────────────────────────────
def has_battery():
    p = "/sys/class/power_supply"
    if not os.path.exists(p): return False
    return any(d.startswith("BAT") for d in os.listdir(p)
               if os.path.isdir(f"{p}/{d}"))


def saver_on():
    out = sh("cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor 2>/dev/null")
    return out == "powersave"


def saver_set(on):
    g = "powersave" if on else "performance"
    if has("powerprofilesctl"):
        prof = "power-saver" if on else "balanced"
        sh(f"powerprofilesctl set {prof}", False, timeout=5)
        return
    if has("cpupower"):
        sh(f"sudo -n cpupower frequency-set -g {g} 2>/dev/null "
           f"|| pkexec cpupower frequency-set -g {g}", False, timeout=10)
        return
    for cpu in os.listdir("/sys/devices/system/cpu"):
        if cpu.startswith("cpu") and cpu[3:].isdigit():
            sh(f"echo {g} | sudo -n tee "
               f"/sys/devices/system/cpu/{cpu}/cpufreq/scaling_governor "
               f">/dev/null 2>&1", False)


# ── Night Light ───────────────────────────────────────────────────────────────
def night_on():
    if has("hyprshade"):
        return bool(sh("hyprshade current 2>/dev/null"))
    return bool(sh("pgrep -x wlsunset"))


def night_set(on):
    if has("hyprshade"):
        if on:
            ok = sh("hyprshade on blue-light-filter", False, timeout=4)
            if not ok: sh("hyprshade on vibrance", False, timeout=4)
        else:
            sh("hyprshade off", False, timeout=4)
        return
    if on:
        detached("wlsunset -t 4500 -T 6500")
    else:
        sh("pkill -x wlsunset", False)


# ── Location ──────────────────────────────────────────────────────────────────
LOC_FLAG = os.path.expanduser("~/.config/nyxus/location.state")


def loc_on():
    if has("systemctl"):
        st = sh("systemctl is-active geoclue 2>/dev/null")
        if st in ("active", "inactive"):
            return st == "active"
    return os.path.exists(LOC_FLAG)


def loc_set(on):
    os.makedirs(os.path.dirname(LOC_FLAG), exist_ok=True)
    if on:
        open(LOC_FLAG, "w").write("1")
        sh("sudo -n systemctl start geoclue 2>/dev/null "
           "|| pkexec systemctl start geoclue", False, timeout=8)
    else:
        try: os.remove(LOC_FLAG)
        except Exception: pass
        sh("sudo -n systemctl stop geoclue 2>/dev/null "
           "|| pkexec systemctl stop geoclue", False, timeout=8)


# ── Focus Assist (dunst paused state) ────────────────────────────────────────
# NYXUS standardized on dunst in Phase 2. Dunst exposes paused/unpaused via
# `dunstctl set-paused` rather than mako's named modes, so Focus Assist is
# now a clean two-state toggle: Off ↔ Do Not Disturb.
FOCUS_STATES = ["off", "do-not-disturb"]
FOCUS_LABELS = {"off": "Off", "do-not-disturb": "Do Not Disturb"}


def focus_state():
    out = sh("dunstctl is-paused 2>/dev/null")
    if not out: return "off"
    return "do-not-disturb" if out.strip().lower() == "true" else "off"


def focus_on():
    return focus_state() != "off"


def focus_cycle(_state=None):
    cur = focus_state()
    nxt = "do-not-disturb" if cur == "off" else "off"
    sh(f"dunstctl set-paused {'true' if nxt == 'do-not-disturb' else 'false'} 2>/dev/null", False)
    return nxt


# ── Notification history (dunst) ─────────────────────────────────────────────
def notif_history():
    raw = sh("dunstctl history 2>/dev/null")
    if not raw: return []
    try:
        d = json.loads(raw)
        rows = []
        for note in d.get("data", [[]])[0]:
            def _v(k):
                v = note.get(k)
                return (v.get("data") if isinstance(v, dict) else v) or ""
            rows.append({
                "app": _v("app-name") or "Notification",
                "summary": _v("summary"),
                "body": _v("body"),
                "id": _v("id"),
            })
        return rows
    except Exception:
        return []


def notif_clear():
    # Clear both currently-displayed notifications AND stored history,
    # otherwise history-backed list rows reappear after refresh.
    sh("dunstctl close-all 2>/dev/null", False)
    sh("dunstctl history-clear 2>/dev/null", False)


# ── Launchers ─────────────────────────────────────────────────────────────────
def open_all_settings():
    for p in ("~/.nyxus/nyxus_settings.py",
              "~/.local/share/nyxus/nyxus_settings.py",
              "~/.config/waybar/nyxus_settings.py",
              "~/.config/nyxus/nyxus_settings.py"):
        full = os.path.expanduser(p)
        if os.path.exists(full):
            detached(f"python3 {shlex.quote(full)}")
            return
    if has("gnome-control-center"): detached("gnome-control-center")


def open_project():
    for c in ("wdisplays", "nwg-displays"):
        if has(c): detached(c); return


def open_connect():
    if has("blueman-manager"): detached("blueman-manager"); return
    if has("pavucontrol"):     detached("pavucontrol"); return
    detached("alacritty -e bluetoothctl")


def open_nearby():
    pub = os.path.expanduser("~/Public")
    os.makedirs(pub, exist_ok=True)
    sh("pkill -f 'http.server 8420' 2>/dev/null", False)
    detached(f"sh -c 'cd {shlex.quote(pub)} && python3 -m http.server 8420'")
    if has("xdg-open"):
        detached("xdg-open http://localhost:8420")


def screen_snip(close_cb):
    close_cb()
    GLib.timeout_add(220, _do_snip)


def _do_snip():
    out_dir = os.path.expanduser("~/Pictures/Screenshots")
    os.makedirs(out_dir, exist_ok=True)
    fpath = os.path.join(out_dir, f"snip-{int(time.time())}.png")
    detached(f"sh -c 'grim -g \"$(slurp)\" - | tee {shlex.quote(fpath)} | wl-copy'")
    return False


# ════════════════════════════════════════════════════════════════════════════════
# THEME
# ════════════════════════════════════════════════════════════════════════════════

CSS = format_css("""
* {{
    font-family: 'Inter Display', 'Inter Display', 'Inter', sans-serif;
    font-size: 16px;
}}

window#actioncenter {{
    background-image: __BG_URL__;
    background-size: cover;
    background-position: center;
    background-color: rgba(10, 10, 18, 0.92);
    color: #e8edf5;
    border: 3px solid rgba(8, 12, 20, 0.55);
    border-radius: 4px;
}}
window#actioncenter > * {{
    background-color: rgba(8, 6, 14, 0.78);
}}

.ac-hdr {{
    background: rgba(15, 12, 24, 0.99);
    padding: 14px 18px 12px;
    border-bottom: 2px solid rgba(8, 12, 20, 0.30);
}}
.ac-title {{
    color: {WHITE_OFF};
    font-size: 22px;
    font-weight: bold;
    letter-spacing: 5px;
    text-shadow: 0 0 10px rgba(8, 12, 20, 0.45);
}}
.ac-time {{ color: rgba(255, 255, 255, 0.85); font-size: 16px; }}

.ac-section {{ padding: 10px 16px; }}
.ac-section-hdr {{
    color: rgba(255, 255, 255, 0.82);
    font-size: 14px;
    letter-spacing: 3px;
}}
.ac-link {{
    color: {WHITE_OFF}; font-size: 15px;
    background: transparent;
    border: none;
    padding: 2px 6px;
}}
.ac-link:hover {{ color: #9aa0ad; text-shadow: 0 0 6px rgba(8, 12, 20, 0.45); }}

.ac-notiflist {{ background: transparent; min-height: 60px; }}
.ac-notif-row {{
    background: rgba(20, 16, 36, 0.95);
    border: 2px solid rgba(8, 12, 20, 0.18);
    border-radius: 4px;
    padding: 8px 12px;
    margin-bottom: 4px;
}}
.ac-notif-app {{ color: {WHITE_OFF}; font-size: 13px; letter-spacing: 1px; }}
.ac-notif-sum {{ color: #e8edf5; font-size: 16px; font-weight: bold; }}
.ac-notif-body {{ color: rgba(255, 255, 255, 0.75); font-size: 14px; }}
.ac-notif-empty {{
    color: rgba(255, 255, 255, 0.55);
    font-size: 16px;
    font-style: italic;
    padding: 12px 0;
}}

.ac-tile {{
    background: rgba(20, 16, 36, 0.96);
    border: 2px solid rgba(8, 12, 20, 0.22);
    border-radius: 4px;
    color: rgba(255, 255, 255, 0.85);
    min-width: 78px;
    min-height: 70px;
    padding: 6px 4px;
}}
.ac-tile:hover {{
    background: rgba(8, 12, 20, 0.14);
    border-color: rgba(8, 12, 20, 0.65);
    color: #e8edf5;
}}
.ac-tile.on {{
    background: rgba(8, 12, 20, 0.24);
    border-color: {WHITE_OFF};
    color: {WHITE_PURE};
    box-shadow: 0 0 14px rgba(8, 12, 20, 0.50);
}}
.ac-tile.unavailable {{
    color: rgba(8, 12, 20, 0.45);
}}
.ac-tile-glyph {{
    font-family: 'Font Awesome 6 Free', 'Font Awesome 5 Free',
                 'JetBrainsMono Nerd Font', 'Symbols Nerd Font Mono';
    font-size: 22px;
    margin-bottom: 4px;
}}
.ac-tile-label {{ font-size: 14px; letter-spacing: 1px; }}

.ac-slider-row {{ padding: 8px 16px; }}
.ac-slider-icon {{
    font-family: 'Font Awesome 6 Free', 'JetBrainsMono Nerd Font',
                 'Symbols Nerd Font Mono';
    font-size: 16px;
    color: {WHITE_OFF};
    text-shadow: 0 0 6px rgba(8, 12, 20, 0.50);
    margin-right: 8px;
}}
.ac-slider-label {{
    color: rgba(255, 255, 255, 0.80);
    font-size: 14px;
    letter-spacing: 1px;
}}
.ac-slider-val {{
    color: {WHITE_OFF};
    font-size: 14px;
    font-weight: bold;
    min-width: 40px;
    text-shadow: 0 0 6px rgba(8, 12, 20, 0.40);
}}
scale trough    {{ background: rgba(8, 12, 20, 0.18); border-radius: 2px; min-height: 5px; }}
scale highlight {{ background: {WHITE_OFF}; border-radius: 2px; }}
scale slider    {{
    background: {WHITE_OFF};
    min-width: 16px; min-height: 16px;
    border-radius: 4px; border: none;
    box-shadow: 0 0 8px rgba(8, 12, 20, 0.45);
    margin: -5px 0;
}}

button.ac-chev {{
    font-family: 'Font Awesome 6 Free', 'JetBrainsMono Nerd Font';
    font-size: 12px;
    color: rgba(255, 255, 255, 0.70);
    background: transparent;
    border: 2px solid rgba(8, 12, 20, 0.20);
    border-radius: 4px;
    min-width: 26px;
    min-height: 22px;
    padding: 0 6px;
    margin-left: 6px;
}}
button.ac-chev:hover {{ color: {WHITE_OFF}; border-color: {WHITE_OFF}; }}

.ac-device-row {{
    background: rgba(15, 12, 24, 0.95);
    border-left: 2px solid rgba(8, 12, 20, 0.24);
    padding: 6px 16px 6px 26px;
    color: rgba(255, 255, 255, 0.80);
}}
.ac-device-row:hover {{
    background: rgba(8, 12, 20, 0.14);
    color: #e8edf5;
}}
.ac-device-row.on {{
    color: {WHITE_OFF};
    font-weight: bold;
}}

.ac-wifi-flyout {{
    background: rgba(8, 6, 14, 0.99);
    border-top: 2px solid rgba(8, 12, 20, 0.22);
    border-bottom: 2px solid rgba(8, 12, 20, 0.22);
}}
.ac-wifirow {{
    background: rgba(15, 12, 24, 0.96);
    border-bottom: 1px solid rgba(8, 12, 20, 0.10);
    padding: 8px 16px;
}}
.ac-wifirow:hover {{ background: rgba(8, 12, 20, 0.10); }}
.ac-wifirow.active {{ background: rgba(8, 12, 20, 0.12); }}
.ac-wifi-ssid {{ color: #e8edf5; font-size: 16px; font-weight: bold; }}
.ac-wifirow.active .ac-wifi-ssid {{ color: {WHITE_OFF}; }}
.ac-wifi-state {{ color: rgba(255, 255, 255, 0.75); font-size: 13px; }}
.ac-wifi-sig {{
    font-family: 'Font Awesome 6 Free', 'JetBrainsMono Nerd Font';
    font-size: 14px;
    color: rgba(255, 255, 255, 0.70);
}}
.ac-wifi-lock {{
    font-family: 'Font Awesome 6 Free', 'JetBrainsMono Nerd Font';
    font-size: 12px;
    color: rgba(255, 255, 255, 0.60);
    margin-right: 6px;
}}

button.ac-btn {{
    background: rgba(20, 16, 36, 0.96);
    border: 2px solid rgba(8, 12, 20, 0.30);
    border-radius: 4px;
    color: #e8edf5;
    font-size: 14px;
    padding: 6px 14px;
}}
button.ac-btn:hover {{
    background: rgba(8, 12, 20, 0.18);
    border-color: {WHITE_OFF};
    color: #e8edf5;
}}
button.ac-btn:disabled {{
    color: rgba(255, 255, 255, 0.40);
    border-color: rgba(8, 12, 20, 0.15);
}}

entry {{
    background: rgba(10, 8, 20, 0.99);
    color: #e8edf5;
    border: 2px solid rgba(8, 12, 20, 0.30);
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 14px;
}}
entry:focus {{ border-color: {WHITE_OFF}; }}

checkbutton {{ color: rgba(255, 255, 255, 0.80); font-size: 14px; }}
checkbutton check {{
    background: rgba(20, 16, 36, 0.96);
    border: 2px solid rgba(8, 12, 20, 0.30);
    min-width: 16px; min-height: 16px;
    border-radius: 2px;
}}
checkbutton check:checked {{
    background: {WHITE_OFF};
    border-color: {WHITE_OFF};
}}

separator {{ background: rgba(8, 12, 20, 0.18); min-height: 1px; }}

scrollbar slider {{
    background: rgba(8, 12, 20, 0.40);
    border-radius: 2px;
    min-width: 6px;
}}
scrollbar slider:hover {{ background: {WHITE_OFF}; }}
""")


# Font-Awesome glyphs (Nerd Font / FontAwesome 6 Free)
G = {
    "bluetooth": "\uf293",
    "wifi":      "\uf1eb",
    "vpn":       "\uf3ed",
    "hotspot":   "\uf519",
    "airplane":  "\uf072",
    "settings":  "\uf013",
    "tablet":    "\uf10a",
    "battery":   "\uf240",
    "moon":      "\uf186",
    "location":  "\uf124",
    "focus":     "\uf02e",
    "project":   "\uf26c",
    "share":     "\uf1e0",
    "camera":    "\uf030",
    "link":      "\uf0c1",
    "volume":    "\uf028",
    "vol_mute":  "\uf6a9",
    "sun":       "\uf185",
    "chev_dn":   "\uf078",
    "chev_up":   "\uf077",
    "lock":      "\uf023",
    "trash":     "\uf2ed",
}


def signal_glyph(strength):
    if strength >= 75: return "\u25b0\u25b0\u25b0\u25b0"
    if strength >= 50: return "\u25b0\u25b0\u25b0\u25b1"
    if strength >= 25: return "\u25b0\u25b0\u25b1\u25b1"
    if strength >  5:  return "\u25b0\u25b1\u25b1\u25b1"
    return "\u25b1\u25b1\u25b1\u25b1"


# ════════════════════════════════════════════════════════════════════════════════
# WIDGETS
# ════════════════════════════════════════════════════════════════════════════════

class Tile(Gtk.Button):
    def __init__(self, glyph, label, on_click=None, get_state=None,
                 available=True):
        super().__init__()
        self.get_style_context().add_class("ac-tile")
        if not available:
            self.get_style_context().add_class("unavailable")
            self.set_sensitive(False)
        self.set_relief(Gtk.ReliefStyle.NONE)

        vb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        gl = Gtk.Label(label=glyph)
        gl.get_style_context().add_class("ac-tile-glyph")
        gl.set_halign(Gtk.Align.CENTER)
        ll = Gtk.Label(label=label)
        ll.get_style_context().add_class("ac-tile-label")
        ll.set_halign(Gtk.Align.CENTER)
        ll.set_ellipsize(Pango.EllipsizeMode.END)
        ll.set_max_width_chars(10)
        vb.pack_start(gl, False, False, 0)
        vb.pack_start(ll, False, False, 0)
        self.add(vb)
        self._get_state = get_state
        self._on_click = on_click
        if on_click:
            self.connect("clicked", self._handle_click)
        self.refresh()

    def _handle_click(self, *_):
        self._on_click(self)
        # backend may take time; refresh shortly after
        GLib.timeout_add(220, self._refresh_idle)

    def _refresh_idle(self):
        self.refresh()
        return False

    def refresh(self):
        if self._get_state is None: return
        try:
            on = bool(self._get_state())
        except Exception:
            on = False
        ctx = self.get_style_context()
        if on: ctx.add_class("on")
        else:  ctx.remove_class("on")


class WifiFlyout(Gtk.Box):
    def __init__(self, on_change):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.get_style_context().add_class("ac-wifi-flyout")
        self._on_change = on_change
        self.refresh()

    def refresh(self):
        self._clear()
        loading = Gtk.Label(label="Checking network requirements...")
        loading.get_style_context().add_class("ac-wifi-state")
        loading.set_halign(Gtk.Align.START)
        loading.set_margin_top(10); loading.set_margin_bottom(10)
        loading.set_margin_start(16); loading.set_margin_end(16)
        self.pack_start(loading, False, False, 0)
        self.show_all()
        GLib.timeout_add(50, self._do_scan)

    def _do_scan(self):
        if not wifi_on():
            self._clear()
            l = Gtk.Label(label="WiFi is off. Turn on the Network tile above.")
            l.get_style_context().add_class("ac-wifi-state")
            l.set_margin_top(12); l.set_margin_bottom(12)
            l.set_margin_start(16); l.set_margin_end(16)
            l.set_halign(Gtk.Align.START)
            self.pack_start(l, False, False, 0)
            self.show_all()
            return False
        nets = wifi_scan()
        active = wifi_active()
        self._clear()
        if not nets:
            l = Gtk.Label(label="No networks in range")
            l.get_style_context().add_class("ac-wifi-state")
            l.set_margin_top(12); l.set_margin_bottom(12)
            l.set_margin_start(16); l.set_margin_end(16)
            l.set_halign(Gtk.Align.START)
            self.pack_start(l, False, False, 0)
        else:
            for n in nets[:14]:
                self.pack_start(self._row(n, n["ssid"] == active),
                                False, False, 0)
        self.show_all()
        return False

    def _clear(self):
        for c in list(self.get_children()):
            self.remove(c)

    def _row(self, net, is_active):
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        rowbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        rowbox.get_style_context().add_class("ac-wifirow")
        if is_active:
            rowbox.get_style_context().add_class("active")

        secured = net["sec"] not in ("--", "")
        lock = Gtk.Label(label=G["lock"] if secured else " ")
        lock.get_style_context().add_class("ac-wifi-lock")
        lock.set_valign(Gtk.Align.CENTER)

        info = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        ssid_l = Gtk.Label(label=net["ssid"])
        ssid_l.set_halign(Gtk.Align.START)
        ssid_l.set_ellipsize(Pango.EllipsizeMode.END)
        ssid_l.set_max_width_chars(28)
        ssid_l.get_style_context().add_class("ac-wifi-ssid")

        if is_active:
            state_text = wifi_status_label(net["sec"])
        else:
            state_text = ("Open network" if not secured
                          else f"Secured ({net['sec']})")
        state_l = Gtk.Label(label=state_text)
        state_l.set_halign(Gtk.Align.START)
        state_l.get_style_context().add_class("ac-wifi-state")

        info.pack_start(ssid_l, False, False, 0)
        info.pack_start(state_l, False, False, 0)

        sig = Gtk.Label(label=signal_glyph(net["sig"]))
        sig.get_style_context().add_class("ac-wifi-sig")
        sig.set_valign(Gtk.Align.CENTER)

        rowbox.pack_start(lock, False, False, 0)
        rowbox.pack_start(info, True, True, 0)
        rowbox.pack_end(sig, False, False, 0)

        rev = Gtk.Revealer()
        rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        rev.set_transition_duration(160)
        rev.add(self._body(net, is_active, rev))

        evt = Gtk.EventBox()
        evt.add(rowbox)
        evt.connect("button-press-event",
                    lambda *_: rev.set_reveal_child(not rev.get_reveal_child()))

        outer.pack_start(evt, False, False, 0)
        outer.pack_start(rev, False, False, 0)
        if is_active:
            rev.set_reveal_child(True)
        return outer

    def _body(self, net, is_active, rev):
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.set_margin_start(36); body.set_margin_end(16)
        body.set_margin_top(6); body.set_margin_bottom(10)

        if is_active:
            btn = Gtk.Button(label="Disconnect")
            btn.get_style_context().add_class("ac-btn")
            btn.set_halign(Gtk.Align.END)
            def _disc(*_):
                wifi_disconnect(net["ssid"])
                GLib.timeout_add(900, lambda: (self.refresh(),
                                               self._on_change(), False)[2])
            btn.connect("clicked", _disc)
            body.pack_start(btn, False, False, 0)
            return body

        secured = net["sec"] not in ("--", "")

        auto = Gtk.CheckButton(label="Connect automatically")
        auto.set_active(True)
        body.pack_start(auto, False, False, 0)

        entry = None
        if secured:
            entry = Gtk.Entry()
            entry.set_visibility(False)
            entry.set_placeholder_text("Enter the network security key")
            body.pack_start(entry, False, False, 0)

        status = Gtk.Label(label="")
        status.get_style_context().add_class("ac-wifi-state")
        status.set_halign(Gtk.Align.START)
        body.pack_start(status, False, False, 0)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.set_halign(Gtk.Align.END)
        cancel  = Gtk.Button(label="Cancel")
        cancel.get_style_context().add_class("ac-btn")
        cancel.connect("clicked", lambda *_: rev.set_reveal_child(False))

        connect = Gtk.Button(label="Connect")
        connect.get_style_context().add_class("ac-btn")

        def _do(*_):
            pwd = entry.get_text() if entry else None
            status.set_text("Checking network requirements...")
            connect.set_sensitive(False)
            def _go():
                ok, msg = wifi_connect(net["ssid"], pwd,
                                       autoconnect=auto.get_active())
                if ok:
                    status.set_text("Connected, secured" if secured
                                    else "Connected, open")
                    GLib.timeout_add(900, lambda: (self.refresh(),
                                                   self._on_change(), False)[2])
                else:
                    status.set_text(f"Action needed - {msg}")
                connect.set_sensitive(True)
                return False
            GLib.timeout_add(80, _go)

        connect.connect("clicked", _do)
        actions.pack_end(connect, False, False, 0)
        actions.pack_end(cancel,  False, False, 0)
        body.pack_start(actions, False, False, 0)
        return body


class VolumeRow(Gtk.Box):
    def __init__(self, on_device_change=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.get_style_context().add_class("ac-slider-row")
        self._on_device_change = on_device_change

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        icon = Gtk.Label(label=G["volume"])
        icon.get_style_context().add_class("ac-slider-icon")
        lab = Gtk.Label(label="VOLUME")
        lab.get_style_context().add_class("ac-slider-label")
        lab.set_halign(Gtk.Align.START)

        # active sink label
        self._sink_label = Gtk.Label(label=self._current_sink_label())
        self._sink_label.set_halign(Gtk.Align.END)
        self._sink_label.get_style_context().add_class("ac-slider-label")
        self._sink_label.set_ellipsize(Pango.EllipsizeMode.END)
        self._sink_label.set_max_width_chars(28)

        self._chev = Gtk.Button(label=G["chev_dn"])
        self._chev.get_style_context().add_class("ac-chev")
        self._chev.connect("clicked", self._toggle_picker)

        top.pack_start(icon, False, False, 0)
        top.pack_start(lab, False, False, 0)
        top.pack_end(self._chev, False, False, 0)
        top.pack_end(self._sink_label, True, True, 0)

        adj = Gtk.Adjustment(value=vol_get(), lower=0, upper=100,
                             step_increment=2, page_increment=10)
        self._scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                                adjustment=adj)
        self._scale.set_draw_value(False)
        self._scale.set_hexpand(True)
        self._val = Gtk.Label(label=f"{vol_get()}%")
        self._val.get_style_context().add_class("ac-slider-val")
        self._val.set_halign(Gtk.Align.END)

        slider_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        slider_row.pack_start(self._scale, True, True, 0)
        slider_row.pack_end(self._val, False, False, 0)

        self._scale.connect("value-changed", self._on_vol)

        self.pack_start(top, False, False, 0)
        self.pack_start(slider_row, False, False, 0)

        self._picker = Gtk.Revealer()
        self._picker.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self._picker.set_transition_duration(140)
        self._picker_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                   spacing=0)
        self._picker.add(self._picker_box)
        self.pack_start(self._picker, False, False, 0)

    def _current_sink_label(self):
        for sid, friendly, raw, is_def in vol_sinks():
            if is_def:
                return friendly
        return "No audio device"

    def _on_vol(self, sc):
        v = int(sc.get_value())
        self._val.set_text(f"{v}%")
        vol_set(v)

    def _toggle_picker(self, *_):
        if self._picker.get_reveal_child():
            self._picker.set_reveal_child(False)
            self._chev.set_label(G["chev_dn"])
            return
        for c in list(self._picker_box.get_children()):
            self._picker_box.remove(c)
        sinks = vol_sinks()
        if not sinks:
            l = Gtk.Label(label="No audio output devices found")
            l.get_style_context().add_class("ac-device-row")
            l.set_halign(Gtk.Align.START)
            self._picker_box.pack_start(l, False, False, 0)
        else:
            for sid, friendly, raw, is_def in sinks:
                btn = Gtk.Button(label=friendly)
                btn.set_relief(Gtk.ReliefStyle.NONE)
                ctx = btn.get_style_context()
                ctx.add_class("ac-device-row")
                if is_def:
                    ctx.add_class("on")
                btn.connect("clicked", self._pick_sink, raw)
                self._picker_box.pack_start(btn, False, False, 0)
        self._picker_box.show_all()
        self._picker.set_reveal_child(True)
        self._chev.set_label(G["chev_up"])

    def _pick_sink(self, btn, name):
        vol_set_default(name)
        GLib.timeout_add(160, self._post_pick)

    def _post_pick(self):
        self._sink_label.set_text(self._current_sink_label())
        self._toggle_picker()
        if self._on_device_change:
            self._on_device_change()
        return False

    def refresh(self):
        v = vol_get()
        self._scale.set_value(v)
        self._val.set_text(f"{v}%")
        self._sink_label.set_text(self._current_sink_label())


class BrightnessRow(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.get_style_context().add_class("ac-slider-row")
        available = has_backlight()

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        icon = Gtk.Label(label=G["sun"])
        icon.get_style_context().add_class("ac-slider-icon")
        lab = Gtk.Label(label="BRIGHTNESS")
        lab.get_style_context().add_class("ac-slider-label")
        lab.set_halign(Gtk.Align.START)
        top.pack_start(icon, False, False, 0)
        top.pack_start(lab, False, False, 0)

        if available:
            init = bright_get()
        else:
            init = 0
        adj = Gtk.Adjustment(value=init, lower=0, upper=100,
                             step_increment=5, page_increment=10)
        self._scale = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL,
                                adjustment=adj)
        self._scale.set_draw_value(False)
        self._scale.set_hexpand(True)
        self._val = Gtk.Label(label=f"{init}%" if available else "External display")
        self._val.get_style_context().add_class("ac-slider-val")
        self._val.set_halign(Gtk.Align.END)

        if not available:
            self._scale.set_sensitive(False)

        slider_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        slider_row.pack_start(self._scale, True, True, 0)
        slider_row.pack_end(self._val, False, False, 0)

        self._scale.connect("value-changed", self._on_b)

        self.pack_start(top, False, False, 0)
        self.pack_start(slider_row, False, False, 0)

    def _on_b(self, sc):
        v = int(sc.get_value())
        self._val.set_text(f"{v}%")
        bright_set(v)


# ════════════════════════════════════════════════════════════════════════════════
# MAIN ACTION CENTER
# ════════════════════════════════════════════════════════════════════════════════

W, H_COLLAPSED, H_EXPANDED = 400, 620, 820


class ActionCenter(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_name("actioncenter")
        self.set_title("nyxus-actioncenter")
        self.set_wmclass("nyxus-actioncenter", "nyxus-actioncenter")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(W, H_COLLAPSED)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)

        # NYXUS unified graffiti chrome — pulls from the same 24-image pool
        # that powers Settings/Notepad/Stickies/SysMon/Control/Weather.
        bg_url = self._ensure_graffiti_bg()
        css_text = CSS.replace("__BG_URL__", bg_url)
        p = Gtk.CssProvider()
        p.load_from_data(css_text.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), p,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._expanded = False
        self._wifi_visible = False
        self._tiles = []

        self._build()
        self.show_all()
        self._wifi_rev.set_reveal_child(False)
        self._extra_tiles_rev.set_reveal_child(False)

        GLib.timeout_add(80, self._position)
        self.connect("focus-out-event", lambda *_: Gtk.main_quit())
        self.connect("key-press-event", self._on_key)
        # tick clock
        GLib.timeout_add_seconds(20, self._tick)

    def _ensure_graffiti_bg(self):
        """Pick a mural from the unified NYXUS pool, fetch if missing,
        return a CSS-ready url(...) value. Falls back to 'none' on failure."""
        try:
            import urllib.request, hashlib, pathlib
            pool = [f"nyxus-graffiti-{i:02d}.png" for i in range(1, 25)]
            # deterministic per-host so the popup mural is stable per machine
            key = (os.uname().nodename + "_quicksettings").encode()
            idx = int(hashlib.sha1(key).hexdigest(), 16) % len(pool)
            name = pool[idx]
            cache = pathlib.Path.home() / ".cache" / "nyxus" / "graffiti"
            cache.mkdir(parents=True, exist_ok=True)
            dest = cache / name
            if not dest.exists() or dest.stat().st_size < 1024:
                url = f"https://nyxus-core.replit.app/api/download/nyxus/{name}"
                try:
                    with urllib.request.urlopen(url, timeout=3) as r:
                        dest.write_bytes(r.read())
                except Exception:
                    return "none"
            return f"url('file://{dest}')"
        except Exception:
            return "none"

    def _position(self):
        sc = Gdk.Screen.get_default()
        sw, sh = sc.get_width(), sc.get_height()
        try:
            mons = json.loads(sh_or_empty("hyprctl monitors -j"))
            if mons:
                m = mons[0]
                sw = int(m.get("width", sw) / m.get("scale", 1))
                sh = int(m.get("height", sh) / m.get("scale", 1))
        except Exception:
            pass
        x = sw - W - 12
        y = sh - H_COLLAPSED - 60
        sh_or_empty(f"hyprctl dispatch movewindowpixel "
                    f"exact {x} {y},title:nyxus-actioncenter")
        self.move(x, y)
        return False

    def _on_key(self, w, ev):
        if ev.keyval == Gdk.KEY_Escape:
            Gtk.main_quit()

    def _tick(self):
        self._time_lbl.set_text(datetime.now().strftime("%a  %b %-d  %-I:%M %p"))
        return True

    # ── layout ────────────────────────────────────────────────────────────────
    def _build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(root)

        # HEADER
        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        hdr.get_style_context().add_class("ac-hdr")
        title = Gtk.Label(label="A C T I O N   C E N T E R")
        title.get_style_context().add_class("ac-title")
        title.set_halign(Gtk.Align.START)
        self._time_lbl = Gtk.Label(
            label=datetime.now().strftime("%a  %b %-d  %-I:%M %p"))
        self._time_lbl.get_style_context().add_class("ac-time")
        self._time_lbl.set_halign(Gtk.Align.END)
        hdr.pack_start(title, True, True, 0)
        hdr.pack_end(self._time_lbl, False, False, 0)
        root.pack_start(hdr, False, False, 0)

        # NOTIFICATIONS
        notif_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        notif_section.get_style_context().add_class("ac-section")
        nh = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        nh_lbl = Gtk.Label(label="NOTIFICATIONS")
        nh_lbl.get_style_context().add_class("ac-section-hdr")
        nh_lbl.set_halign(Gtk.Align.START)
        clr = Gtk.Button(label="Clear all")
        clr.get_style_context().add_class("ac-link")
        clr.set_relief(Gtk.ReliefStyle.NONE)
        clr.connect("clicked", lambda *_: (notif_clear(),
                                           self._refresh_notifs()))
        nh.pack_start(nh_lbl, True, True, 0)
        nh.pack_end(clr, False, False, 0)
        notif_section.pack_start(nh, False, False, 0)

        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_min_content_height(120)
        sw.set_max_content_height(220)
        self._notif_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self._notif_box.get_style_context().add_class("ac-notiflist")
        sw.add(self._notif_box)
        notif_section.pack_start(sw, True, True, 0)
        root.pack_start(notif_section, True, True, 0)

        sep1 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        root.pack_start(sep1, False, False, 0)

        # EXPAND LINK
        link_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        link_row.set_margin_top(4); link_row.set_margin_bottom(2)
        link_row.set_margin_start(16); link_row.set_margin_end(16)
        spacer = Gtk.Label(label=""); spacer.set_hexpand(True)
        self._expand_btn = Gtk.Button(label="Expand  " + G["chev_dn"])
        self._expand_btn.set_relief(Gtk.ReliefStyle.NONE)
        self._expand_btn.get_style_context().add_class("ac-link")
        self._expand_btn.connect("clicked", lambda *_: self._toggle_expand())
        link_row.pack_start(spacer, True, True, 0)
        link_row.pack_end(self._expand_btn, False, False, 0)
        root.pack_start(link_row, False, False, 0)

        # TOP-ROW TILES (4 visible when collapsed)
        top_row = self._tile_row([
            ("bluetooth", "Bluetooth", G["bluetooth"], bt_on, lambda t: bt_set(not bt_on())),
            ("wifi",      "Network",   G["wifi"],      wifi_on, self._on_wifi_tile),
            ("vpn",       "VPN",       G["vpn"],       vpn_any_on, vpn_toggle),
            ("hotspot",   "Hotspot",   G["hotspot"],   hotspot_on, lambda t: hotspot_set(not hotspot_on())),
        ], available_filter={
            "vpn":     bool(vpn_list()),
            "hotspot": has("nmcli"),
        })
        top_row.set_margin_start(12); top_row.set_margin_end(12)
        top_row.set_margin_top(6); top_row.set_margin_bottom(6)
        root.pack_start(top_row, False, False, 0)

        # WIFI FLYOUT (revealer attached to Network tile)
        self._wifi_rev = Gtk.Revealer()
        self._wifi_rev.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self._wifi_rev.set_transition_duration(180)
        self._wifi_flyout = WifiFlyout(self._on_wifi_change)
        self._wifi_rev.add(self._wifi_flyout)
        root.pack_start(self._wifi_rev, False, False, 0)

        # EXTRA TILES (rows 2, 3, 4)
        self._extra_tiles_rev = Gtk.Revealer()
        self._extra_tiles_rev.set_transition_type(
            Gtk.RevealerTransitionType.SLIDE_DOWN)
        self._extra_tiles_rev.set_transition_duration(180)
        extras = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        extras.set_margin_start(12); extras.set_margin_end(12)
        extras.set_margin_bottom(6)

        row2 = self._tile_row([
            ("airplane", "Airplane", G["airplane"], airplane_on, lambda t: airplane_set(not airplane_on())),
            ("settings", "Settings", G["settings"], None, lambda t: (open_all_settings(), Gtk.main_quit())),
            ("tablet",   "Tablet",   G["tablet"],   tablet_on, lambda t: tablet_set(not tablet_on())),
            ("battery",  "Battery",  G["battery"],  saver_on, lambda t: saver_set(not saver_on())),
        ], available_filter={"battery": has_battery()})

        row3 = self._tile_row([
            ("night",    "Night",    G["moon"],     night_on, lambda t: night_set(not night_on())),
            ("location", "Location", G["location"], loc_on,   lambda t: loc_set(not loc_on())),
            ("focus",    "Focus",    G["focus"],    focus_on, lambda t: focus_cycle()),
            ("project",  "Displays", G["project"],  None,     lambda t: (open_project(), Gtk.main_quit())),
        ], available_filter={
            "focus":    has("dunstctl"),
            "location": has("systemctl") or True,
        })

        row4 = self._tile_row([
            ("share",   "Nearby",      G["share"],  None, lambda t: (open_nearby(), Gtk.main_quit())),
            ("snip",    "Screen Snip", G["camera"], None, lambda t: screen_snip(self._close)),
            ("connect", "Connect",     G["link"],   None, lambda t: (open_connect(), Gtk.main_quit())),
            (None, None, None, None, None),  # filler to keep 4-col grid
        ], available_filter={"snip": has("grim") and has("slurp")})

        extras.pack_start(row2, False, False, 0)
        extras.pack_start(row3, False, False, 0)
        extras.pack_start(row4, False, False, 0)
        self._extra_tiles_rev.add(extras)
        root.pack_start(self._extra_tiles_rev, False, False, 0)

        sep2 = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        root.pack_start(sep2, False, False, 0)

        # VOLUME
        self._vol_row = VolumeRow()
        root.pack_start(self._vol_row, False, False, 0)

        # BRIGHTNESS
        self._br_row = BrightnessRow()
        root.pack_start(self._br_row, False, False, 0)

        self._refresh_notifs()

    def _tile_row(self, items, available_filter=None):
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_homogeneous(True)
        for key, label, glyph, get_state, on_click in items:
            if key is None:
                # filler
                row.pack_start(Gtk.Box(), True, True, 0)
                continue
            avail = True if not available_filter else available_filter.get(key, True)
            t = Tile(glyph, label, on_click=on_click, get_state=get_state,
                     available=avail)
            self._tiles.append(t)
            row.pack_start(t, True, True, 0)
        return row

    # ── events ────────────────────────────────────────────────────────────────
    def _toggle_expand(self):
        self._expanded = not self._expanded
        self._extra_tiles_rev.set_reveal_child(self._expanded)
        self._expand_btn.set_label(
            ("Collapse  " + G["chev_up"]) if self._expanded
            else ("Expand  " + G["chev_dn"]))
        new_h = H_EXPANDED if self._expanded else H_COLLAPSED
        self.resize(W, new_h)
        GLib.timeout_add(40, self._reposition_after_resize)

    def _reposition_after_resize(self):
        self._position()
        return False

    def _on_wifi_tile(self, tile):
        # Toggle WiFi radio AND flyout
        if not wifi_on():
            wifi_set(True)
            GLib.timeout_add(900, lambda: (self._wifi_flyout.refresh(),
                                           self._show_wifi(True), False)[2])
        else:
            self._show_wifi(not self._wifi_visible)

    def _show_wifi(self, on):
        self._wifi_visible = on
        if on:
            self._wifi_flyout.refresh()
        self._wifi_rev.set_reveal_child(on)

    def _on_wifi_change(self):
        for t in self._tiles:
            t.refresh()

    def _refresh_notifs(self):
        for c in list(self._notif_box.get_children()):
            self._notif_box.remove(c)
        rows = notif_history()
        if not rows:
            empty = Gtk.Label(label="No new notifications")
            empty.get_style_context().add_class("ac-notif-empty")
            empty.set_halign(Gtk.Align.CENTER)
            self._notif_box.pack_start(empty, False, False, 0)
        else:
            for r in rows[-30:]:
                self._notif_box.pack_start(self._build_notif(r), False, False, 0)
        self._notif_box.show_all()

    def _build_notif(self, r):
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        b.get_style_context().add_class("ac-notif-row")
        a = Gtk.Label(label=str(r["app"]).upper())
        a.get_style_context().add_class("ac-notif-app")
        a.set_halign(Gtk.Align.START)
        s = Gtk.Label(label=str(r["summary"]))
        s.get_style_context().add_class("ac-notif-sum")
        s.set_halign(Gtk.Align.START)
        s.set_line_wrap(True)
        b.pack_start(a, False, False, 0)
        b.pack_start(s, False, False, 0)
        if r.get("body"):
            body = Gtk.Label(label=str(r["body"]))
            body.get_style_context().add_class("ac-notif-body")
            body.set_halign(Gtk.Align.START)
            body.set_line_wrap(True)
            body.set_max_width_chars(40)
            b.pack_start(body, False, False, 0)
        return b

    def _close(self):
        self.hide()
        GLib.timeout_add(50, lambda: (Gtk.main_quit(), False)[1])


def sh_or_empty(cmd):
    try:
        return subprocess.run(cmd, shell=True, capture_output=True,
                              text=True, timeout=3).stdout.strip()
    except Exception:
        return ""


# ════════════════════════════════════════════════════════════════════════════════
# ENTRY POINT - toggle behaviour (re-running closes it)
# ════════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    me_pid = os.getpid()
    pids = sh(f"pgrep -f 'python3.*quicksettings' | grep -v ^{me_pid}$")
    if pids.strip():
        for pid in pids.splitlines():
            sh(f"kill {pid.strip()}", False)
        sys.exit(0)
    ActionCenter()
    Gtk.main()


# ─────────────────────────── NYXUS CHROME (auto-injected r4) ────────────────
# Unifies look across every NYXUS GTK4 app: fully transparent window so the
# user's desktop wallpaper shows through, frosted-glass dark panels, Inter
# font, neon-pink outlined buttons, hover-scramble labels. install_chrome()
# is idempotent and runs once per top-level window via a `present` hook.
# nyxus_chrome.py is shipped to ~/.nyxus by the install pipeline.
try:
    import os as _nyx_os, sys as _nyx_sys
    _nyx_chrome_dir = _nyx_os.path.expanduser("~/.nyxus")
    if _nyx_chrome_dir not in _nyx_sys.path:
        _nyx_sys.path.insert(0, _nyx_chrome_dir)
    try:
        from nyxus_chrome import install_chrome as _nyx_install_chrome
    except ImportError:
        _nyx_install_chrome = lambda *a, **kw: None  # noqa: E731 silent no-op
    _NYX_PAGE_KEY = "_quicksettings"

    def _nyx_make_present_hook(_orig):
        def _nyx_present(self, *args, **kwargs):
            try:
                _nyx_install_chrome(self, page_key=_NYX_PAGE_KEY)
            except Exception:
                pass
            return _orig(self, *args, **kwargs)
        return _nyx_present

    # Gtk.Window.present — base case, also covers Gtk.ApplicationWindow.
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk as _NyxGtk
        if not getattr(_NyxGtk.Window, "_nyx_chrome_hooked", False):
            _NyxGtk.Window.present = _nyx_make_present_hook(_NyxGtk.Window.present)
            _NyxGtk.Window._nyx_chrome_hooked = True
    except Exception as _nyx_eg:
        import sys as _nyx_sys
        print("nyxus-chrome Gtk.Window hook skipped: %s" % _nyx_eg, file=_nyx_sys.stderr)

    # Adw.ApplicationWindow.present — covers shield, sage, studio, godsapp.
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Adw", "1")
        from gi.repository import Adw as _NyxAdw
        if not getattr(_NyxAdw.ApplicationWindow, "_nyx_chrome_hooked", False):
            _NyxAdw.ApplicationWindow.present = _nyx_make_present_hook(
                _NyxAdw.ApplicationWindow.present)
            _NyxAdw.ApplicationWindow._nyx_chrome_hooked = True
    except Exception:
        pass  # Adw is optional
except Exception as _nyx_e:
    import sys as _nyx_sys
    print("nyxus-chrome injection failed: %s" % _nyx_e, file=_nyx_sys.stderr)

# ── palette guard (rev r13) ─────────────────────────────────────────
try: assert_no_forbidden(CSS, __file__)
except Exception as _e: import sys; sys.stderr.write(str(_e)+chr(10))
