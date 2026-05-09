# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · main.py
Passwordless GTK4 lifecycle.

Boot order:
   1. Install CSS.
   2. If the legal disclaimer has not been accepted → SetupWizard
      (single-page disclaimer; provisions the per-device encryption key
      on accept). The main window is NEVER built until the wizard succeeds.
   3. Build IntelWindow and present it. No lock screen, no auto-lock.

Cases are still AES-256-GCM encrypted at rest; the key lives in
~/.config/nyxus-intel/device.key (mode 0600). See auth.py.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import os
import sys
import threading
from pathlib import Path
from typing import Optional

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
from gi.repository import Gtk, Gdk, GLib, Gio

# Local
from auth import (
    Session, load_config, save_config,
)
from setup_wizard import SetupWizard
from ui_components import (
    install_css, hand_label, glyph_button, GLYPH, PALETTE, divider,
)
from case_manager import CaseManager
from search_coordinator import run_search, detect_type
from case_viewer import CaseViewer
from settings import SettingsWindow

# NYXUS brand-wide modules — silent fingerprint, tamper detection,
# legal disclaimer, About dialog. See _fingerprint.py / _tamper.py /
# _legal.py / _about.py.
from _fingerprint import _check
from _tamper import verify as _tamper_verify
from _legal import show_disclaimer, is_accepted, record_acceptance
from _about import show_about

APP_ID = "io.nyxus.intel"
APP_NAME = "NYXUS Phantom"
APP_VERSION = "1.0.0"


def _pango_size(px: int):
    """Return a PangoAttrList that sets the font size to px."""
    import gi
    gi.require_version("Pango", "1.0")
    from gi.repository import Pango
    al = Pango.AttrList.new()
    al.insert(Pango.attr_size_new_absolute(px * Pango.SCALE))
    return al


# ── main intel window ───────────────────────────────────────────────────
class IntelWindow(Gtk.ApplicationWindow):
    def __init__(self, app: "NyxusIntelApp"):
        super().__init__(application=app, title="NYXUS INTEL")
        self.set_default_size(1280, 820)
        self.app = app
        self.add_css_class("nx-window")

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_child(root)

        root.append(self._build_topbar())
        root.append(divider())

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, vexpand=True)
        root.append(body)
        body.append(self._build_sidebar())
        body.append(divider(vertical=True))

        self._main_stack = Gtk.Stack()
        self._main_stack.set_hexpand(True); self._main_stack.set_vexpand(True)
        self._main_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self._main_stack.add_named(self._build_welcome(),  "welcome")
        body.append(self._main_stack)

        root.append(divider())
        root.append(self._build_statusbar())

        # No Ctrl+L handler — the app is passwordless. No activity tracker
        # is needed either because there is no auto-lock timer.

    # ── topbar ───────────────────────────────────────────────────────
    def _build_topbar(self) -> Gtk.Widget:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                      margin_top=4, margin_bottom=4,
                      margin_start=10, margin_end=10)
        bar.add_css_class("nx-topbar")

        title = hand_label("NYXUS  INTEL", size="h2")
        bar.append(title)

        spacer = Gtk.Box(hexpand=True)
        bar.append(spacer)

        about_btn = glyph_button(GLYPH.INFO if hasattr(GLYPH, "INFO") else GLYPH.GEAR,
                                  tooltip="About")
        about_btn.connect("clicked",
            lambda *_: show_about(self, app_name=APP_NAME, version=APP_VERSION))
        bar.append(about_btn)

        gear_btn = glyph_button(GLYPH.GEAR, tooltip="Settings")
        gear_btn.connect("clicked", lambda *_: self.app.open_settings())
        bar.append(gear_btn)
        return bar

    # ── sidebar ──────────────────────────────────────────────────────
    def _build_sidebar(self) -> Gtk.Widget:
        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                       margin_top=10, margin_bottom=10,
                       margin_start=8, margin_end=8)
        side.set_size_request(280, -1)
        side.add_css_class("nx-sidebar")

        new_btn = Gtk.Button(label=f"{GLYPH.PLUS}   New Search")
        new_btn.add_css_class("nx-primary")
        new_btn.connect("clicked", lambda *_: self._focus_search())
        side.append(new_btn)

        self._search_entry = Gtk.Entry(placeholder_text="Search subjects…")
        self._search_entry.connect("changed", lambda *_: self._refresh_index())
        side.append(self._search_entry)

        self._search_input = Gtk.Entry(placeholder_text=
            "Enter email, phone, IP, domain, BTC, ETH, name…")
        self._search_input.connect("activate", lambda *_: self._start_search())
        side.append(self._search_input)

        side.append(divider())

        self._index_box = Gtk.ListBox()
        self._index_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._index_box.connect("row-activated", self._on_case_open)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_child(self._index_box)
        side.append(scroll)

        side.append(divider())
        settings_btn = Gtk.Button(label=f"{GLYPH.GEAR}   Settings")
        settings_btn.connect("clicked", lambda *_: self.app.open_settings())
        side.append(settings_btn)

        self._refresh_index()
        return side

    def _focus_search(self):
        self._search_input.grab_focus()

    def _refresh_index(self):
        # clear
        child = self._index_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._index_box.remove(child)
            child = nxt

        q = self._search_entry.get_text().strip()
        rows = self.app.cases.search(q) if q else self.app.cases.alpha()
        last_letter = ""
        for row in rows:
            subj = row["subject"] or "(unnamed)"
            letter = subj[0].upper() if subj and subj[0].isalpha() else "#"
            if letter != last_letter:
                hdr_row = Gtk.ListBoxRow(activatable=False, selectable=False)
                hdr_row.set_child(hand_label(letter, size="h3", xalign=0))
                hdr_row.add_css_class("nx-az-letter")
                self._index_box.append(hdr_row)
                last_letter = letter

            r = Gtk.ListBoxRow()
            r.case_id = row["id"]   # type: ignore[attr-defined]
            r.add_css_class("nx-az-row")
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            ttl = Gtk.Label(label=subj, xalign=0)
            ttl.add_css_class("nx-body")
            sub = Gtk.Label(label=f"{row['detected_type']} · {row['summary'] or ''}",
                            xalign=0)
            sub.add_css_class("nx-dim"); sub.add_css_class("nx-mono")
            box.append(ttl); box.append(sub)
            r.set_child(box)
            self._index_box.append(r)

    def _on_case_open(self, lb, row):
        case_id = getattr(row, "case_id", None)
        if case_id is None: return
        try:
            payload = self.app.cases.open(case_id)
        except Exception as e:
            self._set_status(f"failed to open case: {e}", warn=True); return
        self._show_case(payload)

    # ── main area ────────────────────────────────────────────────────
    def _build_welcome(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                        halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                        spacing=14)
        glyph = Gtk.Label(label=GLYPH.SEARCH)
        glyph.add_css_class("nx-glyph"); glyph.add_css_class("nx-glyph-accent")
        glyph.set_attributes(_pango_size(48))
        outer.append(glyph)
        outer.append(hand_label("Start an investigation",
                                size="h1", xalign=0.5))
        outer.append(Gtk.Label(label=
            "Type into the search box on the left.\n"
            "We auto-detect emails, phones, IPs, domains, crypto addresses, "
            "drag-dropped photos, usernames, and free-text names.",
            justify=Gtk.Justification.CENTER, wrap=True))
        return outer

    def _build_progress_view(self, subject: str, detected: str) -> tuple[Gtk.Widget, Gtk.Label, Gtk.ListBox, Gtk.ProgressBar]:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                        margin_top=20, margin_bottom=20,
                        margin_start=24, margin_end=24)
        outer.append(hand_label(f"Investigating: {subject}", size="h1"))
        sub = Gtk.Label(label=f"detected type: {detected}", xalign=0)
        sub.add_css_class("nx-dim"); outer.append(sub)

        prog = Gtk.ProgressBar(show_text=True)
        outer.append(prog)

        msg = Gtk.Label(label="starting…", xalign=0); msg.add_css_class("nx-dim")
        outer.append(msg)

        listbox = Gtk.ListBox()
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(listbox); outer.append(scroll)
        return outer, msg, listbox, prog

    def _start_search(self):
        subject = self._search_input.get_text().strip()
        if not subject: return
        self._search_input.set_text("")
        detected = detect_type(subject)
        view, msg, listbox, prog = self._build_progress_view(subject, detected)
        self._main_stack.add_named(view, "progress")
        self._main_stack.set_visible_child_name("progress")

        state = {"done": 0, "total": 1}

        def cb(event, message, data):
            def apply():
                if event == "start":
                    state["total"] = max(1, (data or {}).get("task_count", 1))
                    msg.set_label(f"running {state['total']} modules…")
                    prog.set_fraction(0.0)
                    prog.set_text("0 / %d" % state["total"])
                elif event == "task_start":
                    row = Gtk.ListBoxRow(activatable=False)
                    box = Gtk.Box(spacing=8)
                    g = Gtk.Label(label=GLYPH.REFRESH)
                    g.add_css_class("nx-glyph"); g.add_css_class("nx-dim")
                    box.append(g)
                    box.append(Gtk.Label(label=message, xalign=0))
                    row.set_child(box); row.task_label = message  # type: ignore[attr-defined]
                    listbox.append(row)
                elif event in ("task_done", "task_error"):
                    state["done"] += 1
                    f = state["done"] / state["total"]
                    prog.set_fraction(f)
                    prog.set_text(f"{state['done']} / {state['total']}")
                    # update the matching row
                    child = listbox.get_first_child()
                    while child is not None:
                        if getattr(child, "task_label", None) == message:
                            box = Gtk.Box(spacing=8)
                            ok = event == "task_done"
                            g = Gtk.Label(label=GLYPH.CHECK if ok else GLYPH.WARNING)
                            g.add_css_class("nx-glyph")
                            g.add_css_class("nx-ok" if ok else "nx-warn")
                            box.append(g)
                            txt = message if ok else f"{message} — {data.get('error','')}"
                            l = Gtk.Label(label=txt, xalign=0)
                            l.set_wrap(True)
                            box.append(l)
                            child.set_child(box)
                            break
                        child = child.get_next_sibling()
                elif event == "done":
                    msg.set_label(message)
                    prog.set_fraction(1.0)
            GLib.idle_add(apply)

        def worker():
            findings = run_search(subject, self.app.api_keys(), cb)
            try:
                case_id, folder = self.app.cases.create(subject, detected, findings)
            except Exception as e:
                GLib.idle_add(lambda: self._set_status(
                    f"failed to save case: {e}", warn=True))
                return
            payload = self.app.cases.open(case_id)
            GLib.idle_add(lambda: (self._refresh_index(), self._show_case(payload)))

        threading.Thread(target=worker, daemon=True).start()
        self._set_status(f"searching {subject}…")

    def _show_case(self, payload):
        viewer = CaseViewer(payload, app=self.app)
        # Replace any existing viewer
        existing = self._main_stack.get_child_by_name("case")
        if existing is not None:
            self._main_stack.remove(existing)
        self._main_stack.add_named(viewer, "case")
        self._main_stack.set_visible_child_name("case")

    # ── statusbar ────────────────────────────────────────────────────
    def _build_statusbar(self) -> Gtk.Widget:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        bar.add_css_class("nx-statusbar")

        self._status_lbl = Gtk.Label(label="ready", xalign=0)
        self._status_lbl.add_css_class("nx-mono")
        bar.append(self._status_lbl)

        spacer = Gtk.Box(hexpand=True)
        bar.append(spacer)

        cr = Gtk.Label(
            label="© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED")
        cr.add_css_class("nx-mono"); cr.add_css_class("nx-dim")
        bar.append(cr)
        return bar

    def _set_status(self, msg: str, warn: bool = False):
        self._status_lbl.set_label(msg)
        if warn:
            self._status_lbl.add_css_class("nx-warn")
        else:
            self._status_lbl.remove_css_class("nx-warn")

# ── Application ─────────────────────────────────────────────────────────
class NyxusIntelApp(Gtk.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.FLAGS_NONE)
        self.session: Optional[Session] = None
        self.cases:   Optional[CaseManager] = None
        self._main_window: Optional[IntelWindow] = None
        self._settings_window: Optional[SettingsWindow] = None

    def do_activate(self):  # type: ignore[override]
        install_css()
        # If a main window already exists (e.g. second activate from the
        # desktop file), just present it again.
        if self._main_window is not None:
            self._main_window.present()
            return
        # First-run: legal disclaimer (also provisions the device key).
        if not load_config().get("disclaimer_accepted_at"):
            wiz = SetupWizard(self._after_setup)
            wiz.set_application(self)
            wiz.present()
            return
        # Per-app brand acceptance lives at ~/.config/nyxus/accepted.json.
        # If the wizard ran but the brand record is missing (older install),
        # seed it now from the legacy disclaimer flag.
        if not is_accepted(APP_NAME):
            record_acceptance(APP_NAME, APP_VERSION)
        self._start_main()

    def _after_setup(self, ok: bool):
        if not ok:
            self.quit(); return
        # Mirror acceptance into the shared brand file.
        record_acceptance(APP_NAME, APP_VERSION)
        self._start_main()

    def _start_main(self):
        if self.session is None:
            self.session = Session()
            self.cases   = CaseManager(
                password_provider=lambda: self.session.password())
        self._main_window = IntelWindow(self)
        self._main_window.present()

    def lock(self):
        # Passwordless mode — nothing to lock. Kept as a no-op so any code
        # that still calls app.lock() doesn't crash.
        return

    def open_settings(self):
        if self._settings_window is not None and self._settings_window.get_visible():
            self._settings_window.present(); return
        self._settings_window = SettingsWindow(self)
        self._settings_window.set_application(self)
        self._settings_window.present()

    def api_keys(self) -> dict:
        return load_config().get("api_keys", {}) or {}


def main(argv=None) -> int:
    # Silent ownership fingerprint — never visible to the user.
    _check()
    # Tamper detection — warns + logs but never blocks execution.
    _tamper_verify(APP_NAME)
    app = NyxusIntelApp()
    return app.run(argv if argv is not None else sys.argv)



# ─────────────────────────── NYXUS CHROME (auto-injected) ───────────────────
# Unifies look across every NYXUS GTK4 app: DARK MIRROR glass, Inter
# font, DARK MIRROR palette. Monkey-patches BOTH Gtk.ApplicationWindow.present
# AND Adw.ApplicationWindow.present so the canonical install_chrome()
# runs once per top-level window — without touching the app's own
# window-construction code. install_chrome auto-detects Adw vs Gtk
# windows and uses set_content/get_content vs set_child/get_child
# accordingly. nyxus-panel is intentionally excluded (LayerShell
# incompatibility with Gtk.Overlay). nyxus_chrome.py is shipped to
# ~/.nyxus by nyxus_install.sh.
try:
    import os as _nyx_os, sys as _nyx_sys
    _nyx_chrome_dir = _nyx_os.path.expanduser("~/.nyxus")
    if _nyx_chrome_dir not in _nyx_sys.path:
        _nyx_sys.path.insert(0, _nyx_chrome_dir)
    try:
        from nyxus_chrome import install_chrome as _nyx_install_chrome
    except ImportError:
        _nyx_install_chrome = lambda *a, **kw: None  # silent no-op
    _NYX_PAGE_KEY = "_intel"
    def _nyx_make_present_hook(_orig):
        def _nyx_present(self):
            try: _nyx_install_chrome(self, page_key=_NYX_PAGE_KEY)
            except Exception: pass
            return _orig(self)
        return _nyx_present
    # Hook Gtk.ApplicationWindow (covers most NYXUS apps)
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk as _NyxGtk
        if not getattr(_NyxGtk.ApplicationWindow, "_nyx_chrome_hooked", False):
            _NyxGtk.ApplicationWindow.present = _nyx_make_present_hook(
                _NyxGtk.ApplicationWindow.present)
            _NyxGtk.ApplicationWindow._nyx_chrome_hooked = True
    except Exception as _nyx_eg:
        import sys as _nyx_sys
        print("nyxus-chrome Gtk hook skipped: %s" % _nyx_eg, file=_nyx_sys.stderr)
    # Hook Adw.ApplicationWindow (covers shield, sage, studio, godsapp)
    try:
        import gi as _nyx_gi
        _nyx_gi.require_version("Adw", "1")
        from gi.repository import Adw as _NyxAdw
        if not getattr(_NyxAdw.ApplicationWindow, "_nyx_chrome_hooked", False):
            _NyxAdw.ApplicationWindow.present = _nyx_make_present_hook(
                _NyxAdw.ApplicationWindow.present)
            _NyxAdw.ApplicationWindow._nyx_chrome_hooked = True
    except Exception as _nyx_ea:
        # Adw missing is fine for pure-Gtk apps; only log if non-import
        if not isinstance(_nyx_ea, (ImportError, ValueError)):
            import sys as _nyx_sys
            print("nyxus-chrome Adw hook skipped: %s" % _nyx_ea, file=_nyx_sys.stderr)
except Exception as _nyx_e:
    import sys as _nyx_sys
    print("nyxus-chrome bootstrap skipped: %s" % _nyx_e, file=_nyx_sys.stderr)
# ────────────────────────── /NYXUS CHROME ───────────────────────────────────

if __name__ == "__main__":
    raise SystemExit(main())
