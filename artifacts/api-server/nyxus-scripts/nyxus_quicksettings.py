#!/usr/bin/env python3
"""
NYXUS Quick Settings Panel
~/.config/waybar/quicksettings.py
© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib

import subprocess, json, os, sys

# ── system helpers ─────────────────────────────────────────────────────────────
def _sh(cmd, capture=True):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=capture,
                           text=True, timeout=5)
        return r.stdout.strip() if capture else (r.returncode == 0)
    except Exception:
        return "" if capture else False

def _vol_get():
    raw = _sh("wpctl get-volume @DEFAULT_AUDIO_SINK@")
    try:    return min(100, int(float(raw.split()[-1]) * 100))
    except: return 50

def _vol_set(v): _sh(f"wpctl set-volume @DEFAULT_AUDIO_SINK@ {v/100:.2f}", False)

def _muted():
    return "MUTED" in _sh("wpctl get-volume @DEFAULT_AUDIO_SINK@").upper()

def _mute_toggle(): _sh("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle", False)

def _bright_get():
    try:
        cur = int(_sh("brightnessctl get") or 0)
        mx  = int(_sh("brightnessctl max") or 1)
        return int(cur / mx * 100) if mx else 50
    except: return 50

def _bright_set(v): _sh(f"brightnessctl set {v}%", False)

def _wifi_on():
    return "enabled" in _sh("nmcli radio wifi").lower()

def _wifi_ssid():
    out = _sh("nmcli -t -f ACTIVE,SSID d wifi 2>/dev/null")
    for ln in out.splitlines():
        if ln.startswith("yes:"):
            return ln[4:] or "Connected"
    return "Not connected"

def _wifi_toggle(on):
    _sh(f"nmcli radio wifi {'on' if on else 'off'}", False)

def _bt_on():
    return "yes" in _sh("bluetoothctl show 2>/dev/null | grep -i powered").lower()

def _bt_toggle(on):
    _sh(f"echo -e 'power {'on' if on else 'off'}\\nquit' | bluetoothctl", False)

def _ip():
    return (_sh("ip route get 1 2>/dev/null | awk '{print $7}' | head -1") or "—")

def _monitors():
    try:    return json.loads(_sh("hyprctl monitors -j"))
    except: return []

# ── CSS ────────────────────────────────────────────────────────────────────────
_CSS = """
* { font-family: 'Caveat', 'Patrick Hand', 'Comic Sans MS', 'Sans'; font-size: 15px; }

window {
    background-color: rgba(8, 8, 14, 0.98);
    border: 3px solid rgba(204, 0, 255, 0.50);
    border-radius: 2px;
    box-shadow: 0 0 24px rgba(204, 0, 255, 0.18);
}

/* ─ header ─ */
#hdr {
    background: rgba(12, 10, 22, 0.99);
    padding: 14px 18px 12px;
    border-radius: 0;
    border-bottom: 2px solid rgba(204, 0, 255, 0.22);
}
label.hdr-t {
    color: #cc44ff; font-size: 18px; font-weight: bold; letter-spacing: 4px;
    text-shadow: 0 0 12px rgba(204, 0, 255, 0.60);
}
label.hdr-s { color: rgba(180, 150, 230, 0.65); font-size: 13px; margin-top: 2px; }

/* ─ quick icon row ─ */
.qt-wrap {
    padding: 12px 14px 10px;
    border-bottom: 2px solid rgba(204, 0, 255, 0.12);
}

button.qt {
    background: rgba(18, 14, 32, 0.98);
    border: 2px solid rgba(204, 0, 255, 0.22);
    border-radius: 2px;
    color: rgba(180, 150, 230, 0.65);
    font-size: 20px;
    min-width: 62px;
    min-height: 54px;
    padding: 8px 0 4px;
}
button.qt:hover {
    background: rgba(204, 0, 255, 0.14);
    border-color: rgba(204, 0, 255, 0.60);
    color: #cc44ff;
    box-shadow: 0 0 12px rgba(204, 0, 255, 0.25);
}
button.qt.on {
    background: rgba(204, 0, 255, 0.20);
    border-color: #cc44ff;
    border-width: 2px;
    color: #ee88ff;
    box-shadow: 0 0 14px rgba(204, 0, 255, 0.40);
}
label.qt-l { color: rgba(180, 150, 230, 0.65); font-size: 12px; letter-spacing: 1px; margin-top: 2px; }

/* ─ toggle sections ─ */
.tsec { padding: 10px 16px 8px; border-bottom: 2px solid rgba(204, 0, 255, 0.10); }
label.sec-l { color: rgba(180, 150, 230, 0.60); font-size: 13px; letter-spacing: 2px; margin-bottom: 4px; }

.trow {
    background: rgba(18, 14, 32, 0.98);
    border: 2px solid rgba(204, 0, 255, 0.16);
    border-radius: 2px;
    padding: 8px 14px;
    margin-top: 4px;
}
label.trow-n { color: #e8e0f5; font-size: 15px; font-weight: bold; }
label.trow-s { color: rgba(180, 150, 230, 0.60); font-size: 13px; }

switch {
    border-radius: 2px;
    min-height: 22px;
    min-width: 46px;
    background: rgba(80, 50, 120, 0.40);
    border: 2px solid rgba(204, 0, 255, 0.25);
    outline: none;
}
switch:checked {
    background: rgba(204, 0, 255, 0.55);
    border-color: #cc44ff;
    box-shadow: 0 0 8px rgba(204, 0, 255, 0.45);
}
switch slider { min-width:16px; min-height:16px; border-radius:1px; background:white; margin:2px; border:none; }

/* ─ sliders ─ */
.slsec { padding: 10px 16px 8px; border-bottom: 2px solid rgba(204, 0, 255, 0.10); }
label.sl-t { color: rgba(180, 150, 230, 0.75); font-size: 13px; letter-spacing: 1px; }
label.sl-v { color: #cc44ff; font-size: 14px; font-weight: bold; min-width: 36px;
    text-shadow: 0 0 8px rgba(204, 0, 255, 0.50); }

scale trough   { background: rgba(204, 0, 255, 0.18); border-radius: 2px; min-height: 5px; }
scale highlight{ background: #cc44ff; border-radius: 2px; }
scale slider   { background: #cc44ff; min-width:16px; min-height:16px; border-radius:2px;
                 border:none; box-shadow: 0 0 10px rgba(204, 0, 255, 0.70); margin: -5px 0; }

/* ─ action footer ─ */
.acts {
    padding: 10px 14px 14px;
    background: rgba(10, 8, 20, 0.99);
    border-radius: 0;
    border-top: 2px solid rgba(204, 0, 255, 0.14);
}
button.act {
    background: rgba(18, 14, 32, 0.98);
    border: 2px solid rgba(204, 0, 255, 0.20);
    border-radius: 2px;
    color: rgba(180, 150, 230, 0.80);
    font-size: 14px;
    font-weight: bold;
    padding: 9px 0;
}
button.act:hover {
    background: rgba(204, 0, 255, 0.16);
    border-color: rgba(204, 0, 255, 0.65);
    color: #ee88ff;
    box-shadow: 0 0 10px rgba(204, 0, 255, 0.28);
}
button#btn-power {
    border-color: rgba(255, 80, 50, 0.30);
    color: rgba(255, 100, 80, 0.80);
}
button#btn-power:hover {
    background: rgba(255, 80, 50, 0.14);
    border-color: #ff5533;
    color: #ff8866;
    box-shadow: 0 0 10px rgba(255, 80, 50, 0.30);
}
button#btn-lock {
    border-color: rgba(0, 136, 255, 0.25);
    color: rgba(100, 180, 255, 0.80);
}
button#btn-lock:hover {
    background: rgba(0, 136, 255, 0.14);
    border-color: #0088ff;
    color: #66bbff;
    box-shadow: 0 0 10px rgba(0, 136, 255, 0.28);
}
"""

W, H = 370, 556

class QuickPanel(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.TOPLEVEL)
        self.set_title("nyxus-quicksettings")
        self.set_wmclass("nyxus-quicksettings", "nyxus-quicksettings")
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_default_size(W, H)
        self.set_keep_above(True)
        self.set_skip_taskbar_hint(True)
        self.set_skip_pager_hint(True)
        self.set_type_hint(Gdk.WindowTypeHint.POPUP_MENU)

        p = Gtk.CssProvider()
        p.load_from_data(_CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), p,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._build()
        self.show_all()
        GLib.timeout_add(90, self._position)
        self.connect("focus-out-event", lambda *_: Gtk.main_quit())
        self.connect("key-press-event", self._key)

    # ── positioning ────────────────────────────────────────────────────────────
    def _position(self):
        mons = _monitors()
        if mons:
            m  = mons[0]
            sw = m.get("width", 1920)
            sh = m.get("height", 1080)
        else:
            sc = Gdk.Screen.get_default()
            sw, sh = sc.get_width(), sc.get_height()
        x = sw - W - 10
        y = sh - H - 54
        _sh(f"hyprctl dispatch movewindowpixel exact {x} {y},title:nyxus-quicksettings", False)
        self.move(x, y)
        return False

    # ── layout ─────────────────────────────────────────────────────────────────
    def _build(self):
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.add(root)
        root.pack_start(self._header(),       False, False, 0)
        root.pack_start(self._quick_icons(),  False, False, 0)
        root.pack_start(self._wifi_section(), False, False, 0)
        root.pack_start(self._bt_section(),   False, False, 0)
        root.pack_start(self._slider("🔈  VOLUME",     _vol_get(),    _vol_set),    False, False, 0)
        root.pack_start(self._slider("☀  BRIGHTNESS",  _bright_get(), _bright_set), False, False, 0)
        root.pack_start(self._actions(),      False, False, 0)

    def _header(self):
        b = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=3)
        b.set_name("hdr")
        t = Gtk.Label(label="N Y X U S  ·  Q U I C K  S E T T I N G S")
        t.get_style_context().add_class("hdr-t")
        t.set_halign(Gtk.Align.START)
        ssid = _wifi_ssid()
        ip   = _ip()
        s = Gtk.Label(label=f"{ssid}   ·   IP  {ip}")
        s.get_style_context().add_class("hdr-s")
        s.set_halign(Gtk.Align.START)
        b.pack_start(t, False, False, 0)
        b.pack_start(s, False, False, 0)
        return b

    def _quick_icons(self):
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        wrap.get_style_context().add_class("qt-wrap")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        row.set_homogeneous(True)
        items = [
            ("🔕", "DND",      None),
            ("🌙", "NIGHT",    None),
            ("✈",  "AIRPLANE", lambda on: _sh(f"nmcli radio all {'off' if on else 'on'}", False)),
            ("🖥",  "DISPLAY",  lambda on: _sh("wdisplays &", False)),
            ("🔄", "RELOAD",   lambda on: _sh("hyprctl reload", False)),
        ]
        for icon, label, cb in items:
            row.pack_start(self._icon_btn(icon, label, cb), True, True, 0)
        wrap.pack_start(row, False, False, 0)
        return wrap

    def _icon_btn(self, icon, label, cb=None):
        btn = Gtk.Button()
        btn.get_style_context().add_class("qt")
        vb  = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        il  = Gtk.Label(label=icon); il.set_halign(Gtk.Align.CENTER)
        tl  = Gtk.Label(label=label); tl.get_style_context().add_class("qt-l"); tl.set_halign(Gtk.Align.CENTER)
        vb.pack_start(il, False, False, 0)
        vb.pack_start(tl, False, False, 0)
        btn.add(vb)
        if cb:
            btn._on = False
            def click(w, _cb=cb):
                w._on = not w._on
                _cb(w._on)
                (w.get_style_context().add_class if w._on else w.get_style_context().remove_class)("on")
            btn.connect("clicked", click)
        return btn

    def _toggle_section(self, sec_label, name, sub, state, toggle_cb):
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        wrap.get_style_context().add_class("tsec")
        lbl = Gtk.Label(label=sec_label)
        lbl.get_style_context().add_class("sec-l")
        lbl.set_halign(Gtk.Align.START)
        wrap.pack_start(lbl, False, False, 0)

        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        row.get_style_context().add_class("trow")
        vb  = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        nl  = Gtk.Label(label=name); nl.get_style_context().add_class("trow-n"); nl.set_halign(Gtk.Align.START)
        sl  = Gtk.Label(label=sub);  sl.get_style_context().add_class("trow-s"); sl.set_halign(Gtk.Align.START)
        vb.pack_start(nl, False, False, 0)
        vb.pack_start(sl, False, False, 0)
        row.pack_start(vb, True, True, 0)

        sw = Gtk.Switch(); sw.set_active(state); sw.set_valign(Gtk.Align.CENTER)
        sw.connect("notify::active", lambda s, _: toggle_cb(s.get_active()))
        row.pack_end(sw, False, False, 0)
        wrap.pack_start(row, False, False, 0)
        return wrap

    def _wifi_section(self):
        return self._toggle_section("NETWORK", "🌐  WiFi", _wifi_ssid(), _wifi_on(), _wifi_toggle)

    def _bt_section(self):
        on = _bt_on()
        return self._toggle_section("BLUETOOTH", "🔵  Bluetooth",
                                    "Powered on" if on else "Powered off", on, _bt_toggle)

    def _slider(self, label, init, cb):
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        wrap.get_style_context().add_class("slsec")

        hdr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        tl  = Gtk.Label(label=label); tl.get_style_context().add_class("sl-t"); tl.set_halign(Gtk.Align.START)
        vl  = Gtk.Label(label=f"{init}%"); vl.get_style_context().add_class("sl-v"); vl.set_halign(Gtk.Align.END)
        hdr.pack_start(tl, True, True, 0)
        hdr.pack_end(vl, False, False, 0)
        wrap.pack_start(hdr, False, False, 0)

        adj = Gtk.Adjustment(value=init, lower=0, upper=100, step_increment=5, page_increment=10)
        sc  = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj)
        sc.set_draw_value(False); sc.set_hexpand(True)
        sc.connect("value-changed", lambda s: (vl.set_text(f"{int(s.get_value())}%"), cb(int(s.get_value()))))
        wrap.pack_start(sc, False, False, 0)
        return wrap

    def _actions(self):
        wrap = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        wrap.get_style_context().add_class("acts")
        wrap.set_homogeneous(True)
        acts = [
            ("btn-settings", "⚙  Settings", "gnome-control-center &"),
            ("btn-lock",     "🔒  Lock",     "hyprlock &"),
            ("btn-power",    "⏻  Power",     "wlogout -p layer-shell &"),
        ]
        for name, lbl, cmd in acts:
            b = Gtk.Button(label=lbl)
            b.set_name(name); b.get_style_context().add_class("act")
            b.connect("clicked", lambda w, c=cmd: (_sh(c, False), Gtk.main_quit()))
            wrap.pack_start(b, True, True, 0)
        return wrap

    def _key(self, w, ev):
        if ev.keyval == Gdk.KEY_Escape: Gtk.main_quit()


# ── entry — toggle behaviour ────────────────────────────────────────────────────
if __name__ == "__main__":
    me  = os.path.abspath(__file__)
    pid = _sh(f"pgrep -f 'python3.*quicksettings' | grep -v {os.getpid()}")
    if pid.strip():
        _sh(f"kill {pid.strip()}", False)
        sys.exit(0)
    QuickPanel()
    Gtk.main()
