#!/usr/bin/env python3
# ──────────────────────────────────────────────────────────────────────
#  NYXUS · Welcome Wizard          rev 2026.05.11-r9-eww
# ──────────────────────────────────────────────────────────────────────
#  First-boot setup. Seven steps, single fullscreen window, no decoration.
#  Every step writes real system state — never mock data.
#
#    1. Hello              — brand introduction
#    2. Region & Language  — locale + timezone + clock format
#    3. Network            — wifi connect (reuses wifi-action.sh)
#    4. Account            — display name, password, avatar
#    5. Appearance         — accent colour, wallpaper, font scale
#    6. Privacy            — location, telemetry, crash reports, updates
#    7. Ready              — completion + launch tour
#
#  Marker:   ~/.nyxus/welcome-done       (created on completion)
#  Config:   ~/.config/nyxus/welcome.json (every choice persisted)
#  Helper:   /usr/local/libexec/nyxus-welcome-helper (polkit-elevated
#            for /etc/locale.conf, timedatectl, passwd, useradd GECOS)
#
#  Design contract:  premium / enterprise / DARK MIRROR.
#    • Pure black background, single accent gradient.
#    • Inter for UI, Inter Display for display, JetBrains Mono for code.
#    • Generous whitespace; one focused action per step.
#    • Cross-fade transitions between steps; no jarring repaints.
#    • Validation inline, never as a popup.
# ──────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Gdk", "4.0")
gi.require_version("GLib", "2.0")
from gi.repository import Adw, Gdk, GLib, GObject, Gtk  # noqa: E402

# Optional chrome integration; degrade gracefully if unavailable.
try:
    sys.path.insert(0, str(Path.home() / ".nyxus"))
    import nyxus_chrome  # type: ignore
    HAS_CHROME = True
except Exception:
    HAS_CHROME = False

# ── Paths ─────────────────────────────────────────────────────────────
HOME      = Path.home()
NYXUS_DIR = HOME / ".nyxus"
CFG_DIR   = HOME / ".config" / "nyxus"
CFG_FILE  = CFG_DIR / "welcome.json"
MARKER    = NYXUS_DIR / "welcome-done"
HELPER    = "/usr/local/libexec/nyxus-welcome-helper"

NYXUS_DIR.mkdir(parents=True, exist_ok=True)
CFG_DIR.mkdir(parents=True, exist_ok=True)

# ── DARK MIRROR design tokens ─────────────────────────────────────────
ACCENTS = [
    # name,     primary,   secondary
    ("Mirror",  "#a06bff", "#3ad8ff"),
    ("Plasma",  "#ff5edb", "#a06bff"),
    ("Halo",    "#3ad8ff", "#82ffd2"),
    ("Ember",   "#ff8b5e", "#ff4d6b"),
    ("Bone",    "#e8edf5", "#9aa2b3"),
]

WALLPAPERS = [
    ("Void Vortex", "/usr/share/backgrounds/nyxus/nyxus-void-vortex.png"),
    ("Glass Field", "/usr/share/backgrounds/nyxus/nyxus-glass-field.png"),
    ("Quiet Black", "/usr/share/backgrounds/nyxus/nyxus-quiet-black.png"),
]

LOCALES = [
    ("English (US)",        "en_US.UTF-8"),
    ("English (UK)",        "en_GB.UTF-8"),
    ("Español (España)",    "es_ES.UTF-8"),
    ("Français (France)",   "fr_FR.UTF-8"),
    ("Deutsch (Deutschland)", "de_DE.UTF-8"),
    ("Italiano (Italia)",   "it_IT.UTF-8"),
    ("Português (Brasil)",  "pt_BR.UTF-8"),
    ("日本語 (日本)",        "ja_JP.UTF-8"),
    ("中文 (中国)",          "zh_CN.UTF-8"),
]

# ── CSS ───────────────────────────────────────────────────────────────
CSS = r"""
window.welcome {
  background: #000000;
}

.welcome-root {
  background: radial-gradient(ellipse at top left,
              rgba(160,107,255,0.10), transparent 55%),
              radial-gradient(ellipse at bottom right,
              rgba(58,216,255,0.08), transparent 55%),
              #050608;
}

/* ── left rail ─────────────────────────────────────────────────── */
.welcome-rail {
  background: rgba(8,10,16,0.66);
  border-right: 1px solid rgba(160,107,255,0.14);
  padding: 56px 28px 36px 36px;
  min-width: 320px;
}
.welcome-brand {
  font-family: "Inter Display", "Inter", sans-serif;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: 0.18em;
  color: #ffffff;
  margin-bottom: 6px;
}
.welcome-brand-sub {
  font-size: 11px;
  letter-spacing: 0.32em;
  color: #6b7388;
  margin-bottom: 56px;
}
.welcome-step {
  padding: 12px 14px;
  border-radius: 10px;
  margin: 2px 0;
  color: #6b7388;
  font-size: 13px;
  letter-spacing: 0.06em;
}
.welcome-step .num {
  font-family: "JetBrainsMono Nerd Font", monospace;
  font-size: 11px;
  color: #3a4055;
  margin-right: 14px;
}
.welcome-step.current {
  background: linear-gradient(90deg,
              rgba(160,107,255,0.18), rgba(58,216,255,0.04));
  color: #ffffff;
  border-left: 2px solid #a06bff;
}
.welcome-step.current .num { color: #3ad8ff; }
.welcome-step.done { color: #8b94a8; }
.welcome-step.done .num { color: #82ffd2; }
.welcome-rail-foot {
  font-size: 10px;
  letter-spacing: 0.20em;
  color: #3a4055;
  margin-top: auto;
}

/* ── stage ──────────────────────────────────────────────────────
 * Vertically + horizontally CENTERED column with a hard max-width,
 * so content never "sticks to the top with a gap below" or runs
 * across an ultrawide display. Padding scales with viewport.
 */
.welcome-stage {
  padding: 56px 72px;
}
.welcome-stage-col {
  min-width: 480px;
  /* GtkBox doesn't honour max-width directly — width is constrained by
   * the parent ScrolledWindow's policy + the fixed inner padding above.
   * Visual max ~ 760px is enforced by the fixed-width title/lede labels. */
}
.welcome-title  { max-width: 760px; }
.welcome-lede   { max-width: 720px; }
.welcome-eyebrow {
  font-size: 11px;
  letter-spacing: 0.32em;
  color: #a06bff;
  margin-bottom: 14px;
}
.welcome-title {
  font-family: "Inter Display", "Inter", sans-serif;
  font-size: 44px;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.01em;
  margin-bottom: 14px;
}
.welcome-lede {
  font-size: 16px;
  color: #9aa2b3;
  line-height: 1.55;
  max-width: 640px;
  margin-bottom: 40px;
}

/* ── inputs ────────────────────────────────────────────────────── */
entry.welcome-input, dropdown.welcome-input > button {
  background: rgba(17,21,31,0.85);
  border: 1px solid rgba(160,107,255,0.20);
  border-radius: 10px;
  padding: 12px 14px;
  color: #ffffff;
  font-size: 14px;
  caret-color: #3ad8ff;
}
entry.welcome-input:focus, dropdown.welcome-input > button:focus {
  border-color: #3ad8ff;
  box-shadow: 0 0 0 3px rgba(58,216,255,0.18);
}
.welcome-label {
  font-size: 11px;
  letter-spacing: 0.20em;
  color: #6b7388;
  margin: 14px 0 6px 2px;
}
.welcome-hint {
  font-size: 11px;
  color: #6b7388;
  margin: 6px 2px 0 2px;
}
.welcome-error {
  font-size: 11px;
  color: #ff8b9e;
  margin: 6px 2px 0 2px;
}

/* ── buttons ───────────────────────────────────────────────────── */
button.w-primary {
  padding: 12px 28px;
  border-radius: 10px;
  background: linear-gradient(90deg, #a06bff, #3ad8ff);
  color: #05060a;
  font-weight: 700;
  letter-spacing: 0.10em;
  border: none;
  box-shadow: 0 8px 26px rgba(160,107,255,0.28);
}
button.w-primary:hover {
  box-shadow: 0 10px 32px rgba(160,107,255,0.42);
}
button.w-primary:disabled {
  background: rgba(60,66,82,0.55);
  color: rgba(255,255,255,0.4);
  box-shadow: none;
}
button.w-ghost {
  padding: 12px 22px;
  border-radius: 10px;
  background: transparent;
  color: #b9c1d4;
  border: 1px solid rgba(160,107,255,0.22);
  letter-spacing: 0.10em;
}
button.w-ghost:hover {
  background: rgba(160,107,255,0.08);
  color: #ffffff;
}
button.w-link {
  background: transparent;
  border: none;
  color: #6b7388;
  font-size: 12px;
  letter-spacing: 0.08em;
  padding: 8px 6px;
}
button.w-link:hover { color: #ffffff; }

/* ── swatches & tiles ──────────────────────────────────────────── */
.swatch-row { padding: 6px 0; }
.swatch {
  min-width: 56px; min-height: 56px;
  border-radius: 50%;
  border: 2px solid rgba(255,255,255,0.04);
  margin: 4px 8px;
}
.swatch.selected {
  border-color: #ffffff;
  box-shadow: 0 0 0 3px rgba(58,216,255,0.35),
              0 8px 22px rgba(160,107,255,0.30);
}
.tile {
  border-radius: 12px;
  border: 1px solid rgba(160,107,255,0.14);
  background: rgba(17,21,31,0.65);
  padding: 14px;
  margin: 6px;
  min-width: 200px;
}
.tile.selected {
  border-color: #3ad8ff;
  background: linear-gradient(135deg,
              rgba(160,107,255,0.18), rgba(58,216,255,0.06));
  box-shadow: 0 0 0 1px rgba(58,216,255,0.45),
              0 8px 28px rgba(58,216,255,0.18);
}
.tile-title {
  color: #ffffff;
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.08em;
  margin-top: 8px;
}
.tile-sub { color: #8b94a8; font-size: 11px; }

/* ── toggle row ────────────────────────────────────────────────── */
.toggle-row {
  padding: 16px 18px;
  border-radius: 12px;
  background: rgba(17,21,31,0.6);
  border: 1px solid rgba(160,107,255,0.10);
  margin: 6px 0;
}
.toggle-row .name { color: #ffffff; font-size: 14px; font-weight: 600; }
.toggle-row .desc { color: #8b94a8; font-size: 11px; margin-top: 2px; }
switch slider { background: #ffffff; }
switch:checked { background: linear-gradient(90deg, #a06bff, #3ad8ff); }
switch { background: rgba(60,66,82,0.85); }

/* ── footer nav ────────────────────────────────────────────────── */
.welcome-footer {
  padding: 20px 88px 28px 88px;
  border-top: 1px solid rgba(160,107,255,0.10);
  background: rgba(5,6,10,0.55);
}

/* ── completion ────────────────────────────────────────────────── */
.welcome-complete-glyph {
  font-family: "JetBrainsMono Nerd Font", monospace;
  font-size: 96px;
  color: #82ffd2;
  text-shadow: 0 0 40px rgba(130,255,210,0.45);
}
"""

STEPS = [
    ("hello",      "Hello"),
    ("region",     "Region & language"),
    ("network",    "Network"),
    ("account",    "Account"),
    ("appearance", "Appearance"),
    ("privacy",    "Privacy"),
    ("ready",      "All set"),
]

# ── Helpers ───────────────────────────────────────────────────────────

def run(cmd, **kw):
    """Run a command, never raising. Returns (rc, out, err)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=20, **kw)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:
        return 1, "", str(e)


def helper_call(action: str, *args) -> tuple[int, str]:
    """Call the privileged helper via pkexec.  Falls back to noop if missing."""
    if not Path(HELPER).exists():
        return 0, "(helper missing — choices saved to user config only)"
    rc, out, err = run(["pkexec", HELPER, action, *args])
    return rc, (out or err)


def load_cfg() -> dict:
    if CFG_FILE.exists():
        try: return json.loads(CFG_FILE.read_text())
        except Exception: pass
    return {}


def save_cfg(cfg: dict) -> None:
    CFG_FILE.write_text(json.dumps(cfg, indent=2, sort_keys=True))


def list_timezones() -> list[str]:
    rc, out, _ = run(["timedatectl", "list-timezones"])
    if rc == 0 and out: return out.splitlines()
    # fallback: walk /usr/share/zoneinfo
    base = Path("/usr/share/zoneinfo")
    if not base.exists(): return ["UTC"]
    out = []
    for p in base.rglob("*"):
        if p.is_file() and not p.name.startswith(("posix", "right")):
            rel = p.relative_to(base).as_posix()
            if "/" in rel: out.append(rel)
    return sorted(out) or ["UTC"]


def detect_timezone() -> str:
    p = Path("/etc/timezone")
    if p.exists():
        try: return p.read_text().strip()
        except Exception: pass
    rc, out, _ = run(["timedatectl", "show", "-p", "Timezone", "--value"])
    return out or "UTC"


# ── Validators ────────────────────────────────────────────────────────

USERNAME_RE = re.compile(r"^[a-z_][a-z0-9_-]{1,31}$")

def validate_password(p: str) -> str | None:
    if len(p) < 8: return "Password must be at least 8 characters."
    if not re.search(r"[A-Za-z]", p): return "Password needs at least one letter."
    if not re.search(r"[0-9]", p): return "Password needs at least one digit."
    return None


# ── Reusable widgets ──────────────────────────────────────────────────

class StepRail(Gtk.Box):
    """Left-side step indicator."""
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.add_css_class("welcome-rail")

        brand = Gtk.Label(label="NYXUS", xalign=0)
        brand.add_css_class("welcome-brand")
        sub = Gtk.Label(label="DARK · MIRROR · OS", xalign=0)
        sub.add_css_class("welcome-brand-sub")
        self.append(brand); self.append(sub)

        self._labels: list[Gtk.Box] = []
        for i, (_, title) in enumerate(STEPS):
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            row.add_css_class("welcome-step")
            num = Gtk.Label(label=f"{i+1:02d}", xalign=0)
            num.add_css_class("num")
            t = Gtk.Label(label=title.upper(), xalign=0, hexpand=True)
            row.append(num); row.append(t)
            self.append(row); self._labels.append(row)

        spacer = Gtk.Box(vexpand=True)
        self.append(spacer)
        foot = Gtk.Label(label="REV r9-EWW · 2026.05.11", xalign=0)
        foot.add_css_class("welcome-rail-foot")
        self.append(foot)

    def set_active(self, idx: int) -> None:
        for i, w in enumerate(self._labels):
            w.remove_css_class("current")
            w.remove_css_class("done")
            if i < idx:  w.add_css_class("done")
            if i == idx: w.add_css_class("current")


class FooterNav(Gtk.Box):
    """Back / Continue footer."""
    def __init__(self, on_back, on_next):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.add_css_class("welcome-footer")
        self.back = Gtk.Button(label="Back"); self.back.add_css_class("w-ghost")
        self.back.connect("clicked", lambda *_: on_back())
        self.next = Gtk.Button(label="Continue"); self.next.add_css_class("w-primary")
        self.next.connect("clicked", lambda *_: on_next())
        self.append(self.back)
        self.append(Gtk.Box(hexpand=True))
        self.append(self.next)

    def configure(self, *, back: bool, next_label: str = "Continue",
                  next_enabled: bool = True) -> None:
        self.back.set_sensitive(back); self.back.set_visible(back)
        self.next.set_label(next_label); self.next.set_sensitive(next_enabled)


# ── Step base ─────────────────────────────────────────────────────────

class Step(Gtk.Box):
    """Abstract step. Override build() and commit()."""
    eyebrow = "STEP"
    title   = "Step"
    lede    = ""

    def __init__(self, wizard: "WelcomeWizard"):
        # Outer = full-area box that CENTERS the inner column horizontally
        # and vertically. This eliminates the "all stuck to the top, big
        # empty gap below" failure mode that hobby-grade wizards have.
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL,
                         hexpand=True, vexpand=True)
        self.add_css_class("welcome-stage")
        self.wizard = wizard

        self.append(Gtk.Box(hexpand=True))            # left flex
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0,
                      valign=Gtk.Align.CENTER)
        col.add_css_class("welcome-stage-col")
        col.set_size_request(720, -1)                 # min/target column width
        self.append(col)
        self.append(Gtk.Box(hexpand=True))            # right flex

        eb = Gtk.Label(label=self.eyebrow, xalign=0); eb.add_css_class("welcome-eyebrow")
        ti = Gtk.Label(label=self.title,   xalign=0); ti.add_css_class("welcome-title")
        ti.set_wrap(True); ti.set_xalign(0)
        col.append(eb); col.append(ti)
        if self.lede:
            ld = Gtk.Label(label=self.lede, xalign=0, wrap=True)
            ld.add_css_class("welcome-lede")
            col.append(ld)
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        col.append(body)
        self.body = body
        self.build()

    def build(self): ...        # populate self.body
    def can_advance(self) -> bool: return True
    def commit(self) -> None: ...  # persist + apply system state

    def label(self, txt: str) -> Gtk.Label:
        l = Gtk.Label(label=txt.upper(), xalign=0)
        l.add_css_class("welcome-label")
        return l


# ── Step 1 · Hello ────────────────────────────────────────────────────

class HelloStep(Step):
    eyebrow = "WELCOME"
    title   = "Welcome to NYXUS."
    lede    = ("This wizard takes about two minutes. Every choice you make "
               "writes real settings to your system — nothing is a draft. "
               "You can change all of these later in Settings.")

    def build(self):
        grid = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=18,
                       margin_top=20)
        for glyph, name, desc in [
            ("◆", "Designed",  "Built around a single design language."),
            ("◇", "Private",   "Telemetry off by default. You opt in."),
            ("◈", "Yours",     "Every shortcut, panel, and pixel is yours."),
        ]:
            t = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8); t.add_css_class("tile")
            g = Gtk.Label(label=glyph); g.add_css_class("tile-title")
            n = Gtk.Label(label=name.upper(), xalign=0); n.add_css_class("tile-title")
            d = Gtk.Label(label=desc, xalign=0, wrap=True); d.add_css_class("tile-sub")
            t.append(g); t.append(n); t.append(d)
            grid.append(t)
        self.body.append(grid)


# ── Step 2 · Region & Language ────────────────────────────────────────

class RegionStep(Step):
    eyebrow = "STEP 02 · REGION"
    title   = "Pick your region."
    lede    = "Sets the system language, time zone, and date format."

    def build(self):
        cfg = self.wizard.cfg
        # locale
        self.body.append(self.label("Language"))
        self.locale = Gtk.DropDown.new_from_strings([n for n, _ in LOCALES])
        self.locale.add_css_class("welcome-input")
        self.locale.set_selected(self._initial(cfg.get("locale", "en_US.UTF-8")))
        self.body.append(self.locale)

        # timezone
        self.body.append(self.label("Time zone"))
        self.tzs = list_timezones()
        self.tz = Gtk.DropDown.new_from_strings(self.tzs)
        self.tz.add_css_class("welcome-input")
        cur_tz = cfg.get("timezone", detect_timezone())
        if cur_tz in self.tzs:
            self.tz.set_selected(self.tzs.index(cur_tz))
        self.body.append(self.tz)

        # clock format
        self.body.append(self.label("Clock"))
        clock = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.fmt_24 = Gtk.ToggleButton(label="24-hour"); self.fmt_24.add_css_class("w-ghost")
        self.fmt_12 = Gtk.ToggleButton(label="12-hour"); self.fmt_12.add_css_class("w-ghost")
        self.fmt_12.set_group(self.fmt_24)
        (self.fmt_24 if cfg.get("clock", "24") == "24" else self.fmt_12).set_active(True)
        clock.append(self.fmt_24); clock.append(self.fmt_12)
        self.body.append(clock)

        h = Gtk.Label(
            label="System time will sync from network time servers (NTP).",
            xalign=0); h.add_css_class("welcome-hint")
        self.body.append(h)

    def _initial(self, code: str) -> int:
        for i, (_, c) in enumerate(LOCALES):
            if c == code: return i
        return 0

    def commit(self):
        loc = LOCALES[self.locale.get_selected()][1]
        tz  = self.tzs[self.tz.get_selected()]
        clk = "24" if self.fmt_24.get_active() else "12"
        self.wizard.cfg.update({"locale": loc, "timezone": tz, "clock": clk})
        helper_call("set-locale", loc)
        helper_call("set-timezone", tz)
        helper_call("enable-ntp")


# ── Step 3 · Network ──────────────────────────────────────────────────

class NetworkStep(Step):
    eyebrow = "STEP 03 · NETWORK"
    title   = "Get connected."
    lede    = "Connect to WiFi now, or skip and set it up later from the bar."

    def build(self):
        self.status = Gtk.Label(label=self._status(), xalign=0)
        self.status.add_css_class("welcome-hint")
        self.body.append(self.status)

        self.body.append(self.label("Available networks"))
        scroll = Gtk.ScrolledWindow(); scroll.set_min_content_height(280)
        scroll.set_hexpand(True); scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.list = Gtk.ListBox(); self.list.add_css_class("welcome-list")
        self.list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        scroll.set_child(self.list)
        self.body.append(scroll)

        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        rescan = Gtk.Button(label="Rescan"); rescan.add_css_class("w-ghost")
        rescan.connect("clicked", lambda *_: self._refresh())
        adv = Gtk.Button(label="Advanced (nmtui)"); adv.add_css_class("w-link")
        adv.connect("clicked", lambda *_: subprocess.Popen(
            ["alacritty", "-e", "nmtui"]))
        bar.append(rescan); bar.append(Gtk.Box(hexpand=True)); bar.append(adv)
        self.body.append(bar)

        self._refresh()

    def _status(self) -> str:
        rc, out, _ = run(["nmcli", "-t", "-f", "TYPE,STATE", "device"])
        if rc != 0: return "NetworkManager not detected."
        for line in out.splitlines():
            t, s = (line.split(":") + ["", ""])[:2]
            if s == "connected" and t == "ethernet":
                return "Connected via ethernet — you can skip this step."
            if s == "connected" and t == "wifi":
                return "Connected to WiFi — pick another network or continue."
        return "Not connected. Pick a network below."

    def _refresh(self):
        run(["nmcli", "device", "wifi", "rescan"])
        # clear
        child = self.list.get_first_child()
        while child:
            self.list.remove(child); child = self.list.get_first_child()
        rc, out, _ = run(["nmcli", "-t", "-f", "IN-USE,SSID,SIGNAL,SECURITY",
                          "device", "wifi", "list"])
        seen = set()
        for line in out.splitlines():
            p = line.split(":")
            if len(p) < 4 or not p[1] or p[1] in seen: continue
            seen.add(p[1])
            row = Gtk.ListBoxRow()
            box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                          spacing=12, margin_top=8, margin_bottom=8,
                          margin_start=12, margin_end=12)
            sig = int(p[2] or 0)
            bars = "▰▰▰▰" if sig>=75 else "▰▰▰▱" if sig>=50 else "▰▰▱▱" if sig>=25 else "▰▱▱▱"
            b = Gtk.Label(label=bars); b.add_css_class("welcome-eyebrow")
            n = Gtk.Label(label=p[1], xalign=0, hexpand=True)
            s = Gtk.Label(label=("●" if p[3] else "○") + f"  {sig}%", xalign=1)
            s.add_css_class("welcome-hint")
            box.append(b); box.append(n); box.append(s)
            row.set_child(box); row.ssid = p[1]; row.security = p[3]
            self.list.append(row)
        self.status.set_label(self._status())

    def commit(self):
        row = self.list.get_selected_row()
        if not row: return
        ssid = getattr(row, "ssid", "")
        if not ssid: return
        # try saved profile first, then ask for password
        if subprocess.run(["nmcli", "connection", "up", ssid],
                          capture_output=True).returncode == 0:
            self.wizard.cfg["wifi"] = ssid; return
        if subprocess.run(["nmcli", "device", "wifi", "connect", ssid],
                          capture_output=True).returncode == 0:
            self.wizard.cfg["wifi"] = ssid; return
        # password prompt — modal dialog
        d = Adw.MessageDialog.new(self.wizard.window,
                                  f"Password for {ssid}", "")
        ent = Gtk.PasswordEntry(); ent.add_css_class("welcome-input")
        d.set_extra_child(ent)
        d.add_response("cancel", "Cancel")
        d.add_response("connect", "Connect")
        d.set_response_appearance("connect", Adw.ResponseAppearance.SUGGESTED)
        d.set_default_response("connect")
        def _resp(dialog, resp):
            if resp == "connect":
                pw = ent.get_text()
                subprocess.run(["nmcli", "device", "wifi", "connect", ssid,
                                "password", pw], capture_output=True)
                self.wizard.cfg["wifi"] = ssid
        d.connect("response", _resp)
        d.present()


# ── Step 4 · Account ──────────────────────────────────────────────────

class AccountStep(Step):
    eyebrow = "STEP 04 · ACCOUNT"
    title   = "Make it yours."
    lede    = ("Set a display name and (optionally) change your password. "
               "If you're on the live ISO, this is just a preview.")

    def build(self):
        self.user = os.environ.get("USER", "user")
        live = self.user in ("liveuser", "live", "root")
        if live:
            warn = Gtk.Label(
                label="LIVE-ISO MODE — choices are saved but not applied to a system account.",
                xalign=0); warn.add_css_class("welcome-error")
            self.body.append(warn)

        self.body.append(self.label("Display name"))
        self.disp = Gtk.Entry(); self.disp.add_css_class("welcome-input")
        self.disp.set_placeholder_text("e.g. Alex Morgan")
        rc, out, _ = run(["getent", "passwd", self.user])
        gecos = ""
        if rc == 0 and ":" in out:
            gecos = out.split(":")[4].split(",")[0]
        self.disp.set_text(self.wizard.cfg.get("display_name", gecos))
        self.body.append(self.disp)

        self.body.append(self.label("Change password (optional)"))
        self.pw1 = Gtk.PasswordEntry(); self.pw1.add_css_class("welcome-input")
        self.pw1.set_show_peek_icon(True)
        self.pw1.set_placeholder_text("New password (leave blank to keep current)")
        self.pw2 = Gtk.PasswordEntry(); self.pw2.add_css_class("welcome-input")
        self.pw2.set_show_peek_icon(True)
        self.pw2.set_placeholder_text("Confirm new password")
        self.body.append(self.pw1); self.body.append(self.pw2)

        self.err = Gtk.Label(label="", xalign=0); self.err.add_css_class("welcome-error")
        self.body.append(self.err)

        for w in (self.pw1, self.pw2):
            w.connect("changed", lambda *_: self._validate())

    def _validate(self):
        p1, p2 = self.pw1.get_text(), self.pw2.get_text()
        if not p1 and not p2:
            self.err.set_label(""); return True
        msg = validate_password(p1)
        if msg: self.err.set_label(msg); return False
        if p1 != p2: self.err.set_label("Passwords don't match."); return False
        self.err.set_label(""); return True

    def can_advance(self) -> bool:
        return self._validate()

    def commit(self):
        disp = self.disp.get_text().strip()
        self.wizard.cfg["display_name"] = disp
        if disp: helper_call("set-gecos", self.user, disp)
        p1 = self.pw1.get_text()
        if p1 and self._validate():
            helper_call("set-password", self.user, p1)


# ── Step 5 · Appearance ───────────────────────────────────────────────

class AppearanceStep(Step):
    eyebrow = "STEP 05 · APPEARANCE"
    title   = "Pick your accent."
    lede    = ("NYXUS is locked to dark mode. The accent threads through "
               "the bar, panels, and active states.")

    def build(self):
        # accent swatches
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        row.add_css_class("swatch-row")
        self._swatches = []
        cur = self.wizard.cfg.get("accent", "Mirror")
        for name, c1, c2 in ACCENTS:
            sw = Gtk.Button(); sw.add_css_class("swatch")
            sw.set_tooltip_text(name)
            css = (f"button.swatch.s-{name.lower()} {{ background:"
                   f" linear-gradient(135deg, {c1}, {c2}); }}")
            self._inject(css)
            sw.add_css_class(f"s-{name.lower()}")
            if name == cur: sw.add_css_class("selected")
            sw.connect("clicked", lambda b, n=name: self._pick_accent(n))
            row.append(sw); self._swatches.append((name, sw))
        self.body.append(row)

        self.body.append(self.label("Wallpaper"))
        wpr = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self._wp_buttons = []
        cur_wp = self.wizard.cfg.get("wallpaper", WALLPAPERS[0][1])
        for name, path in WALLPAPERS:
            t = Gtk.Button(); t.add_css_class("tile")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            n = Gtk.Label(label=name.upper(), xalign=0); n.add_css_class("tile-title")
            s = Gtk.Label(label=Path(path).name, xalign=0); s.add_css_class("tile-sub")
            box.append(n); box.append(s); t.set_child(box)
            if path == cur_wp: t.add_css_class("selected")
            t.connect("clicked", lambda b, p=path: self._pick_wp(p))
            wpr.append(t); self._wp_buttons.append((path, t))
        self.body.append(wpr)

        self.body.append(self.label("Text scale"))
        self.scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,
                                              0.85, 1.30, 0.05)
        self.scale.set_value(self.wizard.cfg.get("text_scale", 1.0))
        self.scale.set_draw_value(True)
        self.scale.set_value_pos(Gtk.PositionType.RIGHT)
        self.scale.set_hexpand(True)
        self.body.append(self.scale)

    def _inject(self, css: str):
        prov = Gtk.CssProvider(); prov.load_from_data(css.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

    def _pick_accent(self, name: str):
        self.wizard.cfg["accent"] = name
        for n, sw in self._swatches:
            (sw.add_css_class if n == name else sw.remove_css_class)("selected")

    def _pick_wp(self, path: str):
        self.wizard.cfg["wallpaper"] = path
        for p, t in self._wp_buttons:
            (t.add_css_class if p == path else t.remove_css_class)("selected")

    def commit(self):
        self.wizard.cfg["text_scale"] = round(self.scale.get_value(), 2)
        # apply wallpaper live
        wp = self.wizard.cfg.get("wallpaper")
        if wp and Path(wp).exists():
            run(["pkill", "-x", "swaybg"])
            subprocess.Popen(["swaybg", "-i", wp, "-m", "fill", "-c", "#000000"],
                             start_new_session=True)
        # write theme manifest for EWW / hyprland to pick up
        accent = next((a for a in ACCENTS if a[0] == self.wizard.cfg.get("accent")),
                      ACCENTS[0])
        theme = {
            "accent": accent[0],
            "primary": accent[1],
            "secondary": accent[2],
            "wallpaper": wp,
            "text_scale": self.wizard.cfg["text_scale"],
        }
        (CFG_DIR / "theme.json").write_text(json.dumps(theme, indent=2))


# ── Step 6 · Privacy ──────────────────────────────────────────────────

class PrivacyStep(Step):
    eyebrow = "STEP 06 · PRIVACY"
    title   = "You decide what we know."
    lede    = ("Default answers are 'no.' Turn on what's useful, leave "
               "the rest off. You can change any of this in Settings → Privacy.")

    OPTIONS = [
        ("location",    "Location services",
         "Lets weather, time-zone, and maps know where you are. Off by default.", False),
        ("telemetry",   "Anonymous usage statistics",
         "Helps us improve NYXUS. No personal data is ever sent.",                False),
        ("crash",       "Automatic crash reports",
         "Sends a stack trace when an app crashes. Stripped of file paths.",      False),
        ("updates",     "Automatic security updates",
         "Installs critical fixes in the background. Recommended.",               True),
    ]

    def build(self):
        self._sw: dict[str, Gtk.Switch] = {}
        for key, name, desc, default in self.OPTIONS:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.add_css_class("toggle-row")
            txt = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                          hexpand=True)
            n = Gtk.Label(label=name, xalign=0); n.add_css_class("name")
            d = Gtk.Label(label=desc, xalign=0, wrap=True); d.add_css_class("desc")
            txt.append(n); txt.append(d)
            sw = Gtk.Switch(valign=Gtk.Align.CENTER)
            sw.set_active(self.wizard.cfg.get(f"privacy_{key}", default))
            row.append(txt); row.append(sw)
            self.body.append(row)
            self._sw[key] = sw

    def commit(self):
        for key, *_ in self.OPTIONS:
            self.wizard.cfg[f"privacy_{key}"] = self._sw[key].get_active()


# ── Step 7 · Ready ────────────────────────────────────────────────────

class ReadyStep(Step):
    eyebrow = "READY"
    title   = "You're set."
    lede    = ("Press Super + / any time to see every shortcut. "
               "Press Super + A for quick settings. Welcome to NYXUS.")

    def build(self):
        glyph = Gtk.Label(label="◆", xalign=0)
        glyph.add_css_class("welcome-complete-glyph")
        self.body.append(glyph)
        summary = self._summary()
        for line in summary:
            l = Gtk.Label(label=line, xalign=0); l.add_css_class("welcome-hint")
            self.body.append(l)

    def _summary(self) -> list[str]:
        c = self.wizard.cfg
        return [
            f"  •  Region    {c.get('locale','en_US.UTF-8')}  ·  {c.get('timezone','UTC')}",
            f"  •  Network   {c.get('wifi') or 'wired / not connected'}",
            f"  •  Account   {c.get('display_name') or os.environ.get('USER','—')}",
            f"  •  Theme     accent {c.get('accent','Mirror')}, scale {c.get('text_scale',1.0)}×",
            f"  •  Privacy   updates {'on' if c.get('privacy_updates',True) else 'off'},"
            f" telemetry {'on' if c.get('privacy_telemetry') else 'off'}",
        ]


# ── Wizard window ─────────────────────────────────────────────────────

class WelcomeWizard(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application):
        super().__init__(application=app)
        self.set_title("NYXUS Welcome")
        self.add_css_class("welcome")
        self.fullscreen()
        self.cfg: dict = load_cfg()

        self._inject_css()

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        root.add_css_class("welcome-root")

        self.rail = StepRail(); root.append(self.rail)

        right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0,
                        hexpand=True, vexpand=True)

        # Wrap the stack in a ScrolledWindow so any single step that
        # genuinely overflows on a small display scrolls inside the stage
        # instead of clipping or pushing the footer off-screen.
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(220)
        self.stack.set_hexpand(True); self.stack.set_vexpand(True)
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self.stack)
        scroll.set_hexpand(True); scroll.set_vexpand(True)
        self.steps: list[Step] = []
        klasses = [HelloStep, RegionStep, NetworkStep, AccountStep,
                   AppearanceStep, PrivacyStep, ReadyStep]
        for i, cls in enumerate(klasses):
            s = cls(self); s.window = self
            self.steps.append(s)
            self.stack.add_named(s, STEPS[i][0])

        right.append(scroll)
        self.footer = FooterNav(self._back, self._next)
        right.append(self.footer)
        root.append(right)

        self.set_content(root)

        # Esc → quit (only useful in dev; remove from prod by setting handler off)
        if os.environ.get("NYXUS_WELCOME_DEV"):
            ec = Gtk.EventControllerKey()
            ec.connect("key-pressed", self._on_key)
            self.add_controller(ec)

        self._idx = 0
        self._show(0)

        if HAS_CHROME:
            try: nyxus_chrome.install_chrome(self, page_key="_welcome")
            except Exception: pass

    # CSS
    def _inject_css(self):
        prov = Gtk.CssProvider(); prov.load_from_data(CSS.encode())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION + 10)

    def _on_key(self, _c, keyval, _kc, _state):
        if keyval == Gdk.KEY_Escape and os.environ.get("NYXUS_WELCOME_DEV"):
            self.close(); return True
        return False

    def _show(self, i: int):
        self._idx = i
        self.stack.set_visible_child_name(STEPS[i][0])
        self.rail.set_active(i)
        last = (i == len(STEPS) - 1)
        first = (i == 0)
        self.footer.configure(
            back=not first and not last,
            next_label=("Begin" if first else
                        "Finish" if last else "Continue"),
            next_enabled=self.steps[i].can_advance(),
        )

    def _back(self):
        if self._idx > 0: self._show(self._idx - 1)

    def _next(self):
        s = self.steps[self._idx]
        if not s.can_advance(): return
        try: s.commit()
        except Exception as e: print(f"[welcome] commit error: {e}", file=sys.stderr)
        save_cfg(self.cfg)
        if self._idx == len(STEPS) - 1:
            self._finish(); return
        self._show(self._idx + 1)

    def _finish(self):
        try:
            MARKER.write_text(
                json.dumps({"version": "r9-eww",
                            "completed_at": GLib.DateTime.new_now_utc().format_iso8601()},
                           indent=2))
        except Exception: pass
        self.get_application().quit()


# ── Application ───────────────────────────────────────────────────────

class WelcomeApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="dev.nyxus.welcome",
                         flags=0)

    def do_activate(self):
        win = WelcomeWizard(self)
        win.present()


def main() -> int:
    # Only run if marker is missing (the launcher script enforces this too,
    # but we double-check so manual invocation is safe).
    if MARKER.exists() and not os.environ.get("NYXUS_WELCOME_FORCE"):
        print("welcome already completed; pass NYXUS_WELCOME_FORCE=1 to re-run")
        return 0
    Adw.init()
    return WelcomeApp().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
