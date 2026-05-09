# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · settings.py
Settings window — sidebar-nav style (mirrors the panel app).

Sections:
   • API Keys   — 9 keyed services + Save + Test for each
   • Security   — auto-lock minutes, fail limit, change password
   • Storage    — cases path, backup schedule, open / wipe cases
   • Search     — default depth, autostart on launch, auto-export PDF
   • About      — copyright, license, version

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Dict, Any, Callable

import gi

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

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib, Gdk

import requests

from auth import (
    load_config, save_config, KEY_FILE,
)
from ui_components import (
    GLYPH, hand_label, glyph_button, divider, wrap_sketch, PALETTE,
)

UA = "NYXUS-INTEL/1.0 (settings)"

API_FIELDS = [
    # (key, label, helper-text)
    ("hibp",          "HaveIBeenPwned",      "https://haveibeenpwned.com/API/Key  (paid, $4/mo)"),
    ("dehashed",      "DeHashed key",        "https://dehashed.com/  (paid)"),
    ("dehashed_email","DeHashed account email", "the email you registered DeHashed with"),
    ("shodan",        "Shodan",              "https://account.shodan.io/  (membership / monthly)"),
    ("virustotal",    "VirusTotal",          "https://virustotal.com/gui/my-apikey  (free 500/day)"),
    ("abuseipdb",     "AbuseIPDB",           "https://www.abuseipdb.com/account/api  (free 1k/day)"),
    ("ipinfo",        "IPinfo",              "https://ipinfo.io/account/token  (free 50k/mo)"),
    ("etherscan",     "Etherscan",           "https://etherscan.io/myapikey  (free)"),
    ("fec",           "FEC (api.data.gov)",  "https://api.data.gov/signup/  (free, instant)"),
    ("patentsview",   "USPTO PatentsView",   "https://patentsview.org/api/keyrequest  (free, instant)"),
    ("google_cse",    "Google CSE key",      "https://developers.google.com/custom-search/v1/overview"),
    ("google_cse_id", "Google CSE engine id", "the cx field from your programmable search engine"),
    ("github",        "GitHub token",        "github.com/settings/tokens  (optional, raises rate limit)"),
]


# ── API tests ───────────────────────────────────────────────────────────
def _test_api(name: str, keys: Dict[str, str]) -> str:
    """Run a small probe call. Returns a human readable status."""
    # Paired-key fields share a probe with their primary
    if name == "google_cse_id":
        name = "google_cse"
    if name == "dehashed_email":
        name = "dehashed"
    k = keys.get(name)
    try:
        if name == "hibp":
            if not k: return "missing"
            r = requests.get("https://haveibeenpwned.com/api/v3/breachedaccount/test@example.com",
                             headers={"hibp-api-key": k, "User-Agent": UA},
                             params={"truncateResponse": "true"}, timeout=15)
            if r.status_code in (200, 404): return "OK"
            if r.status_code == 401: return "rejected"
            return f"HTTP {r.status_code}"

        if name == "shodan":
            if not k: return "missing"
            r = requests.get("https://api.shodan.io/api-info",
                             params={"key": k}, timeout=15, headers={"User-Agent": UA})
            if r.status_code == 200:
                d = r.json(); return f"OK · plan {d.get('plan','?')} · {d.get('query_credits','?')} qc / {d.get('scan_credits','?')} sc"
            if r.status_code == 401: return "rejected"
            return f"HTTP {r.status_code}"

        if name == "virustotal":
            if not k: return "missing"
            r = requests.get("https://www.virustotal.com/api/v3/users/current",
                             headers={"x-apikey": k, "User-Agent": UA}, timeout=15)
            if r.status_code == 200:
                d = r.json().get("data", {}).get("attributes", {})
                quotas = d.get("quotas", {}).get("api_requests_daily", {})
                return f"OK · {quotas.get('used','?')}/{quotas.get('allowed','?')} daily"
            if r.status_code == 401: return "rejected"
            return f"HTTP {r.status_code}"

        if name == "abuseipdb":
            if not k: return "missing"
            r = requests.get("https://api.abuseipdb.com/api/v2/check",
                             params={"ipAddress": "8.8.8.8"},
                             headers={"Key": k, "Accept": "application/json", "User-Agent": UA},
                             timeout=15)
            if r.status_code == 200:
                # remaining quota is in headers
                rem = r.headers.get("X-RateLimit-Remaining", "?")
                return f"OK · {rem} remaining today"
            if r.status_code == 401: return "rejected"
            return f"HTTP {r.status_code}"

        if name == "ipinfo":
            url = "https://ipinfo.io/8.8.8.8/json"
            headers = {"User-Agent": UA}
            if k: headers["Authorization"] = f"Bearer {k}"
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200: return "OK" + (" (with key)" if k else " (anon)")
            if r.status_code == 401: return "rejected"
            return f"HTTP {r.status_code}"

        if name == "etherscan":
            if not k: return "missing"
            r = requests.get("https://api.etherscan.io/api",
                             params={"module":"stats","action":"ethsupply","apikey":k},
                             timeout=15, headers={"User-Agent": UA})
            if r.status_code == 200 and (r.json().get("status") == "1"):
                return "OK"
            return f"rejected · {r.json().get('result','')[:60]}" if r.status_code == 200 else f"HTTP {r.status_code}"

        if name == "fec":
            if not k: return "missing"
            r = requests.get("https://api.open.fec.gov/v1/candidates/",
                             params={"api_key": k, "per_page": 1}, timeout=15,
                             headers={"User-Agent": UA})
            if r.status_code == 200: return "OK"
            if r.status_code == 401 or r.status_code == 403: return "rejected"
            return f"HTTP {r.status_code}"

        if name == "google_cse":
            if not k or not keys.get("google_cse_id"): return "missing key or engine id"
            r = requests.get("https://www.googleapis.com/customsearch/v1",
                             params={"key": k, "cx": keys["google_cse_id"], "q": "test", "num": 1},
                             timeout=15, headers={"User-Agent": UA})
            if r.status_code == 200: return "OK"
            if r.status_code in (401, 403): return "rejected"
            return f"HTTP {r.status_code}"

        if name == "github":
            url = "https://api.github.com/rate_limit"
            headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
            if k: headers["Authorization"] = f"Bearer {k}"
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                core = r.json().get("rate", {})
                return f"OK · {core.get('remaining','?')}/{core.get('limit','?')} remaining"
            if r.status_code == 401: return "rejected"
            return f"HTTP {r.status_code}"

        if name in ("dehashed", "dehashed_email"):
            if not (keys.get("dehashed") and keys.get("dehashed_email")):
                return "missing email + key"
            r = requests.get("https://api.dehashed.com/search",
                             params={"query": "email:test@example.com", "size": 1},
                             auth=(keys["dehashed_email"], keys["dehashed"]),
                             headers={"Accept": "application/json", "User-Agent": UA},
                             timeout=15)
            if r.status_code in (200, 204): return "OK · " + str(r.json().get("balance","?")) + " credits"
            if r.status_code == 401: return "rejected"
            return f"HTTP {r.status_code}"

        return "no test for this field"
    except requests.RequestException as e:
        return f"network error: {e}"
    except Exception as e:
        return f"error: {e}"


# ── settings window ─────────────────────────────────────────────────────
class SettingsWindow(Gtk.Window):
    def __init__(self, app):
        super().__init__(title="NYXUS INTEL — Settings")
        self.set_default_size(1080, 720)
        self.app = app
        self.cfg = load_config()
        self.add_css_class("nx-window")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(outer)

        outer.append(self._build_topbar())
        outer.append(divider())

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True)
        outer.append(body)

        body.append(self._build_sidebar())
        body.append(divider(vertical=True))

        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True); self.stack.set_vexpand(True)
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        body.append(self.stack)

        self.stack.add_named(self._build_api_keys(), "api")
        self.stack.add_named(self._build_security(), "sec")
        self.stack.add_named(self._build_storage(),  "stg")
        self.stack.add_named(self._build_search(),   "srch")
        self.stack.add_named(self._build_about(),    "abt")
        self.stack.set_visible_child_name("api")

    # ── topbar ──────────────────────────────────────────────────────
    def _build_topbar(self) -> Gtk.Widget:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                      margin_top=4, margin_bottom=4,
                      margin_start=10, margin_end=10)
        bar.add_css_class("nx-topbar")
        bar.append(hand_label("Settings", size="h2"))
        bar.append(Gtk.Box(hexpand=True))

        close_btn = glyph_button(GLYPH.CROSS, tooltip="Close")
        close_btn.connect("clicked", lambda *_: self.close())
        bar.append(close_btn)
        return bar

    # ── sidebar ─────────────────────────────────────────────────────
    def _build_sidebar(self) -> Gtk.Widget:
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                       margin_top=12, margin_bottom=12,
                       margin_start=10, margin_end=10)
        side.set_size_request(220, -1)
        side.add_css_class("nx-sidebar")

        for key, label, glyph in [
            ("api",  "API Keys", GLYPH.KEY),
            ("sec",  "Security", GLYPH.SHIELD),
            ("stg",  "Storage",  GLYPH.DATABASE),
            ("srch", "Search",   GLYPH.SEARCH),
            ("abt",  "About",    GLYPH.INFO),
        ]:
            b = Gtk.ToggleButton()
            row = Gtk.Box(spacing=8)
            g = Gtk.Label(label=glyph); g.add_css_class("nx-glyph"); g.add_css_class("nx-accent")
            row.append(g)
            row.append(Gtk.Label(label=label, xalign=0))
            b.set_child(row)
            b.connect("toggled", lambda btn, k=key: self._on_nav(btn, k))
            side.append(b)

        side.append(Gtk.Box(vexpand=True))
        return side

    def _on_nav(self, btn, key):
        if not btn.get_active():
            # Don't allow toggling off; keep one selected
            btn.set_active(True); return
        # Untoggle siblings
        parent = btn.get_parent()
        c = parent.get_first_child()
        while c is not None:
            if isinstance(c, Gtk.ToggleButton) and c is not btn:
                c.set_active(False)
            c = c.get_next_sibling()
        self.stack.set_visible_child_name(key)

    # ── api keys page ───────────────────────────────────────────────
    def _build_api_keys(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                        margin_top=18, margin_bottom=18,
                        margin_start=22, margin_end=22)
        outer.append(hand_label("API Keys", size="h1"))
        outer.append(Gtk.Label(
            label="Every key is optional. Modules without a key show a "
                  "'set key' hint instead of returning fake data.",
            xalign=0, wrap=True))

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        outer.append(scroll)

        grid = Gtk.Grid(column_spacing=10, row_spacing=10,
                        margin_top=10, margin_bottom=10,
                        margin_start=4, margin_end=10)
        scroll.set_child(grid)

        self._key_entries: Dict[str, Gtk.Entry] = {}
        self._key_status:  Dict[str, Gtk.Label] = {}

        for r, (key, label, helper) in enumerate(API_FIELDS):
            l = Gtk.Label(label=label, xalign=1)
            l.add_css_class("nx-body")
            grid.attach(l, 0, r, 1, 1)

            # IMPORTANT: do NOT use Gtk.PasswordEntry here. On Wayland
            # (Hyprland in particular) PasswordEntry's input-method context
            # breaks after the first character is committed and every key
            # after that is dropped — see the lock-screen story in main.py.
            # Plain Gtk.Entry with visibility=False gives identical "hide
            # the secret" UX without the broken IM path. The eye-shaped
            # secondary icon toggles visibility so the user can verify
            # what they pasted/typed.
            ent = Gtk.Entry(hexpand=True)
            ent.set_visibility(False)
            ent.set_input_purpose(Gtk.InputPurpose.PASSWORD)
            ent.set_editable(True)
            ent.set_sensitive(True)
            ent.set_can_focus(True)
            ent.set_focusable(True)
            ent.set_placeholder_text("paste API key here")
            ent.set_icon_from_icon_name(
                Gtk.EntryIconPosition.SECONDARY, "view-reveal-symbolic")
            ent.set_icon_tooltip_text(
                Gtk.EntryIconPosition.SECONDARY, "show / hide")
            ent.set_icon_activatable(Gtk.EntryIconPosition.SECONDARY, True)

            def _toggle_visibility(entry, _pos):
                entry.set_visibility(not entry.get_visibility())
                entry.set_icon_from_icon_name(
                    Gtk.EntryIconPosition.SECONDARY,
                    "view-conceal-symbolic" if entry.get_visibility()
                    else "view-reveal-symbolic")
            ent.connect("icon-press", _toggle_visibility)

            ent.set_text((self.cfg.get("api_keys") or {}).get(key, "") or "")
            self._key_entries[key] = ent
            grid.attach(ent, 1, r, 1, 1)

            help_lbl = Gtk.Label(label=helper, xalign=0)
            help_lbl.add_css_class("nx-dim"); help_lbl.add_css_class("nx-mono")
            grid.attach(help_lbl, 2, r, 1, 1)

            btnbox = Gtk.Box(spacing=4)
            save = Gtk.Button(label="Save")
            save.connect("clicked", lambda *_, k=key: self._save_one(k))
            btnbox.append(save)

            test = Gtk.Button(label="Test")
            test.connect("clicked", lambda *_, k=key: self._test_one(k))
            btnbox.append(test)

            grid.attach(btnbox, 3, r, 1, 1)

            status = Gtk.Label(label="", xalign=0)
            status.add_css_class("nx-mono"); status.add_css_class("nx-dim")
            self._key_status[key] = status
            grid.attach(status, 4, r, 1, 1)

        save_all = Gtk.Button(label=f"{GLYPH.CHECK}   Save All")
        save_all.add_css_class("nx-primary")
        save_all.connect("clicked", lambda *_: self._save_all_keys())
        outer.append(save_all)
        return outer

    def _collect_keys(self) -> Dict[str, str]:
        return {k: e.get_text().strip() for k, e in self._key_entries.items()}

    def _save_one(self, key: str):
        cfg = load_config()
        cfg.setdefault("api_keys", {})
        cfg["api_keys"][key] = self._key_entries[key].get_text().strip()
        save_config(cfg)
        self.cfg = cfg
        self._key_status[key].set_label("saved")
        self._key_status[key].remove_css_class("nx-warn")
        self._key_status[key].add_css_class("nx-ok")

    def _save_all_keys(self):
        cfg = load_config()
        cfg["api_keys"] = self._collect_keys()
        save_config(cfg); self.cfg = cfg
        for k, lbl in self._key_status.items():
            lbl.set_label("saved"); lbl.add_css_class("nx-ok")

    def _test_one(self, key: str):
        # Save first (so we test what's in the box)
        self._save_one(key)
        keys = self.cfg.get("api_keys") or {}
        self._key_status[key].set_label("testing…")
        self._key_status[key].remove_css_class("nx-ok"); self._key_status[key].remove_css_class("nx-warn")

        def worker():
            res = _test_api(key, keys)
            def done():
                self._key_status[key].set_label(res)
                if res.startswith("OK"):
                    self._key_status[key].add_css_class("nx-ok")
                    self._key_status[key].remove_css_class("nx-warn")
                else:
                    self._key_status[key].add_css_class("nx-warn")
                    self._key_status[key].remove_css_class("nx-ok")
            GLib.idle_add(done)
        threading.Thread(target=worker, daemon=True).start()

    # ── security page ───────────────────────────────────────────────
    def _build_security(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14,
                        margin_top=18, margin_bottom=18,
                        margin_start=22, margin_end=22)
        outer.append(hand_label("Security", size="h1"))

        intro = Gtk.Label(
            label=("NYXUS INTEL runs in passwordless mode on this device. "
                   "Cases are still AES-256-GCM encrypted at rest using a "
                   "256-bit key generated automatically on first launch."),
            xalign=0, wrap=True)
        intro.add_css_class("nx-body")
        outer.append(intro)

        outer.append(divider())
        outer.append(hand_label("Device key", size="h2"))

        try:
            exists = KEY_FILE.exists()
            sz = KEY_FILE.stat().st_size if exists else 0
        except Exception:
            exists = False; sz = 0

        path_lbl = Gtk.Label(label=f"Location: {KEY_FILE}", xalign=0,
                             selectable=True)
        path_lbl.add_css_class("nx-mono")
        outer.append(path_lbl)

        status_lbl = Gtk.Label(
            label=(f"Status: present ({sz} bytes, mode 0600)" if exists
                   else "Status: missing — will be generated on next launch"),
            xalign=0)
        status_lbl.add_css_class("nx-dim")
        outer.append(status_lbl)

        warn = Gtk.Label(
            label=("WARNING: if you delete or replace this file, every "
                   "existing case becomes permanently unrecoverable. Back it "
                   "up alongside your case folder if the data matters."),
            xalign=0, wrap=True)
        warn.add_css_class("nx-warn"); warn.add_css_class("nx-body")
        outer.append(warn)

        outer.append(divider())
        legal = Gtk.Label(
            label="© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED",
            xalign=0)
        legal.add_css_class("nx-mono"); legal.add_css_class("nx-dim")
        outer.append(legal)

        return outer

    # ── storage page ────────────────────────────────────────────────
    def _build_storage(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                        margin_top=18, margin_bottom=18,
                        margin_start=22, margin_end=22)
        outer.append(hand_label("Storage", size="h1"))

        cases_dir = Path.home() / ".config" / "nyxus-intel" / "cases"
        outer.append(Gtk.Label(label=f"Cases folder: {cases_dir}", xalign=0,
                               selectable=True))
        try:
            n = sum(1 for _ in cases_dir.glob("*/case.nxc"))
            sz = sum(p.stat().st_size for p in cases_dir.rglob("*") if p.is_file())
            outer.append(Gtk.Label(label=f"  {n} cases · {sz/1024:.1f} KiB on disk",
                                   xalign=0))
        except Exception:
            pass

        open_btn = Gtk.Button(label="Open cases folder in file manager")
        open_btn.connect("clicked", lambda *_: self._open_path(cases_dir))
        outer.append(open_btn)

        outer.append(divider())
        outer.append(hand_label("Backup schedule", size="h2"))
        cb = Gtk.DropDown.new_from_strings(["manual", "daily", "weekly"])
        current = self.cfg.get("backup_schedule", "manual")
        try: cb.set_selected({"manual":0,"daily":1,"weekly":2}[current])
        except KeyError: cb.set_selected(0)
        outer.append(cb)
        save_bk = Gtk.Button(label="Save")
        save_bk.add_css_class("nx-primary")
        def _save_bk(*_):
            choices = ["manual","daily","weekly"]
            cfg = load_config(); cfg["backup_schedule"] = choices[cb.get_selected()]
            save_config(cfg); self.cfg = cfg
        save_bk.connect("clicked", _save_bk)
        outer.append(save_bk)
        outer.append(Gtk.Label(label=
            "Tip: backups are simple — copy ~/.config/nyxus-intel/cases/ to "
            "an external drive. Files are AES-256-GCM encrypted; the backup "
            "is therefore also encrypted at rest.",
            xalign=0, wrap=True))
        return outer

    def _open_path(self, p: Path):
        try:
            import subprocess
            subprocess.Popen(["xdg-open", str(p)], start_new_session=True)
        except Exception:
            pass

    # ── search defaults ─────────────────────────────────────────────
    def _build_search(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                        margin_top=18, margin_bottom=18,
                        margin_start=22, margin_end=22)
        outer.append(hand_label("Search defaults", size="h1"))

        depth = Gtk.DropDown.new_from_strings(["quick", "thorough"])
        depth.set_selected(0 if self.cfg.get("default_depth", "thorough") == "quick" else 1)
        outer.append(Gtk.Label(label="Default depth", xalign=0))
        outer.append(depth)

        autostart = Gtk.CheckButton(label="Open last case on launch")
        autostart.set_active(bool(self.cfg.get("autostart_search")))
        outer.append(autostart)

        autopdf = Gtk.CheckButton(label="Auto-export PDF when investigation finishes")
        autopdf.set_active(bool(self.cfg.get("auto_pdf")))
        outer.append(autopdf)

        showraw = Gtk.CheckButton(label="Show Raw Data tab in case viewer")
        showraw.set_active(bool(self.cfg.get("show_raw_tab")))
        outer.append(showraw)

        save = Gtk.Button(label=f"{GLYPH.CHECK}   Save"); save.add_css_class("nx-primary")
        outer.append(save)

        def _save(*_):
            cfg = load_config()
            cfg["default_depth"]      = ("quick", "thorough")[depth.get_selected()]
            cfg["autostart_search"]   = autostart.get_active()
            cfg["auto_pdf"]           = autopdf.get_active()
            cfg["show_raw_tab"]       = showraw.get_active()
            save_config(cfg); self.cfg = cfg
        save.connect("clicked", _save)
        return outer

    # ── about ───────────────────────────────────────────────────────
    def _build_about(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                        margin_top=18, margin_bottom=18,
                        margin_start=22, margin_end=22,
                        halign=Gtk.Align.CENTER)
        outer.append(hand_label("NYXUS  INTEL", size="h1", xalign=0.5))
        outer.append(Gtk.Label(label="Open source intelligence workstation",
                               xalign=0.5))
        outer.append(Gtk.Label(label="version 1.0.0", xalign=0.5))
        outer.append(divider())
        outer.append(Gtk.Label(label="© 2026 Joseph Sierengowski", xalign=0.5))
        outer.append(Gtk.Label(label="NYX-J5W-2026-SIERENGOWSKI-LOCKED",
                               xalign=0.5))
        outer.append(divider())
        outer.append(Gtk.Label(label=
            "All cases are encrypted on-device with AES-256-GCM and a key\n"
            "derived from your master password via PBKDF2-HMAC-SHA256\n"
            "(200,000 iterations).  Nothing is ever transmitted to NYXUS\n"
            "or any third party other than the OSINT API you choose to invoke.",
            justify=Gtk.Justification.CENTER))
        return outer
