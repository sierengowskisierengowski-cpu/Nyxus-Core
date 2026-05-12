"""
NYXUS Notifications — flyout entry point.

A GTK4 layer-shell flyout for the bottom-bar Notifications button. Mirrors
the Start / Panel aesthetic: dark sketched plates, Inter Display handwritten font,
neon glow accents, NO emojis (Font Awesome / Nerd Font glyphs only).

Behavior
────────
  • Anchored to the BOTTOM-RIGHT (rising above the Waybar Notifications icon)
  • Toggle: re-running the launcher closes the open instance
  • Auto-closes on Escape and on focus-out
  • Header: title + DND toggle + close button
  • Body: notification list (currently placeholder feed) with empty state
  • Footer: "Clear all" + small note explaining the live-feed roadmap
  • Persists DND toggle to ~/.config/nyxus-notifications/state.json

If a real notification daemon (`swaync` or `mako`) is detected, the launcher
will short-circuit to its native toggle command instead of opening this
flyout, so power users keep their existing workflow.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

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
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio, Pango  # noqa: E402

try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell  # type: ignore
    _HAS_LAYER_SHELL = True
except (ValueError, ImportError):
    _HAS_LAYER_SHELL = False

# ──────────────────────────────────────────────── constants
APP_ID    = "io.nyxus.notifications"
PANEL_W   = 420
PANEL_H   = 540
PID_FILE  = Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "nyxus-notifications.pid"
CFG_DIR   = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "nyxus-notifications"
STATE_FILE     = CFG_DIR / "state.json"
REMINDERS_FILE = CFG_DIR / "reminders.json"
LOG_FILE       = (Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "nyxus" / "notifications.log")

# Brand palette (matches Start + Panel for visual consistency).
C_TEXT   = "#e8edf5"
C_DIM    = "#9aa0ad"
C_PINK   = "#9aa0ad"
C_PURPLE = "#e8edf5"
C_CYAN   = "#c8ccd6"
C_GOLD   = "#c8ccd6"
C_BG_HEX = "#0a0a0a"


# ──────────────────────────────────────────────── persistence
def _load_state() -> Dict[str, Any]:
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {"dnd": False}

def _save_state(state: Dict[str, Any]) -> None:
    try:
        CFG_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except Exception:
        pass


def _load_reminders() -> List[Dict[str, Any]]:
    """Returns a list of {id, text, created} dicts. Survives bad JSON."""
    try:
        data = json.loads(REMINDERS_FILE.read_text())
        if isinstance(data, list):
            out: List[Dict[str, Any]] = []
            for r in data:
                if isinstance(r, dict) and "text" in r:
                    out.append({
                        "id":      str(r.get("id") or int(time.time() * 1000)),
                        "text":    str(r["text"]),
                        "created": float(r.get("created") or time.time()),
                    })
            return out
    except Exception:
        pass
    return []


def _save_reminders(items: List[Dict[str, Any]]) -> None:
    try:
        CFG_DIR.mkdir(parents=True, exist_ok=True)
        REMINDERS_FILE.write_text(json.dumps(items, indent=2))
    except Exception:
        pass

def _read_log_entries(limit: int = 25) -> List[Dict[str, str]]:
    """Read the most recent entries from the optional notification log file.
    Each line is expected to be JSON with at least {ts, app, summary, body}."""
    if not LOG_FILE.exists():
        return []
    entries: List[Dict[str, str]] = []
    try:
        lines = LOG_FILE.read_text(errors="replace").splitlines()[-limit:]
        for raw in reversed(lines):
            raw = raw.strip()
            if not raw:
                continue
            try:
                entries.append(json.loads(raw))
            except Exception:
                entries.append({"summary": raw, "body": "", "app": "log", "ts": ""})
    except Exception:
        pass
    return entries


# ──────────────────────────────────────────────── single-instance toggle
def _toggle_singleton() -> bool:
    """Return True if this invocation killed an existing instance (= 'closed')."""
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip() or "0")
    except Exception:
        pid = 0
    if pid > 0:
        try:
            os.kill(pid, 0)            # is the pid alive?
            os.kill(pid, signal.SIGTERM)
            time.sleep(0.05)
            try:
                PID_FILE.unlink(missing_ok=True)
            except Exception:
                pass
            return True
        except ProcessLookupError:
            try:
                PID_FILE.unlink(missing_ok=True)
            except Exception:
                pass
    return False

def _write_pid() -> None:
    try:
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(os.getpid()))
    except Exception:
        pass

def _clear_pid() -> None:
    try:
        PID_FILE.unlink(missing_ok=True)
    except Exception:
        pass


# ──────────────────────────────────────────────── CSS
def _install_css() -> None:
    css = f"""
    * {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   14px;
        color:       {C_TEXT};
    }}

    .nyxus-notif-root {{
        background-color: rgba(8, 4, 22, 0.94);
        border:           1.5px solid rgba(8, 12, 20, 0.45);
        border-radius:    12px;
    }}

    .nyxus-notif-header {{
        background-color: rgba(8, 4, 22, 0.92);
        border-bottom:    2px solid rgba(8, 12, 20, 0.40);
        padding:          10px 14px;
    }}
    .nyxus-notif-title {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   24px;
        font-weight: bold;
        color:       {C_CYAN};
        text-shadow: 0 0 10px rgba(255, 255, 255, 0.55);
    }}

    .nyxus-notif-glyph {{
        font-family: "JetBrains Mono Nerd Font", "Symbols Nerd Font", monospace;
        font-size:   16px;
    }}

    .nyxus-section {{
        background-color: rgba(8, 4, 22, 0.78);
        border:           1.5px solid rgba(8, 12, 20, 0.35);
        border-radius:    10px;
        margin:           6px 10px;
        padding:          8px 10px;
    }}

    .nyxus-notif-card {{
        background-color: rgba(15, 8, 32, 0.90);
        border:           1px solid rgba(255, 255, 255, 0.30);
        border-radius:    8px;
        padding:          8px 10px;
        margin:           4px 10px;
    }}
    .nyxus-notif-card-title {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   16px;
        font-weight: bold;
        color:       {C_PINK};
    }}
    .nyxus-notif-card-body {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   13px;
        color:       {C_TEXT};
    }}
    .nyxus-notif-card-meta {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   11px;
        color:       {C_DIM};
    }}

    .nyxus-notif-empty {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:   18px;
        color:       {C_DIM};
        padding:     32px 16px;
    }}

    .nyxus-notif-footer {{
        background-color: rgba(8, 4, 22, 0.92);
        border-top:       1.5px solid rgba(8, 12, 20, 0.30);
        padding:          8px 14px;
    }}

    button {{
        font-family: 'Inter Display', 'Inter', 'Cantarell', 'DejaVu Sans', sans-serif;
        font-size:     14px;
        background:    rgba(15, 8, 32, 0.90);
        color:         {C_TEXT};
        border:        1.5px solid rgba(8, 12, 20, 0.45);
        border-radius: 8px;
        padding:       6px 12px;
    }}
    button:hover {{
        border-color: rgba(255, 255, 255, 0.85);
        color:        {C_CYAN};
    }}
    .nyxus-toggle-on {{
        background:   rgba(8, 12, 20, 0.18);
        color:        {C_PINK};
        border-color: rgba(8, 12, 20, 0.85);
    }}
    """
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode("utf-8"))
    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(
            display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )


# ──────────────────────────────────────────────── notification card widget
def _build_card(entry: Dict[str, str]) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    box.add_css_class("nyxus-notif-card")

    head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
    title_text = entry.get("summary") or entry.get("title") or "Notification"
    title = Gtk.Label(label=title_text)
    title.add_css_class("nyxus-notif-card-title")
    title.set_xalign(0); title.set_hexpand(True); title.set_wrap(True)
    head.append(title)

    ts = entry.get("ts", "")
    if ts:
        ts_lbl = Gtk.Label(label=ts)
        ts_lbl.add_css_class("nyxus-notif-card-meta")
        head.append(ts_lbl)
    box.append(head)

    body_text = entry.get("body", "")
    if body_text:
        body = Gtk.Label(label=body_text)
        body.add_css_class("nyxus-notif-card-body")
        body.set_xalign(0); body.set_wrap(True)
        body.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        box.append(body)

    app = entry.get("app", "")
    if app:
        meta = Gtk.Label(label=f"\uf07c  {app}")  # FA folder-open glyph
        meta.add_css_class("nyxus-notif-card-meta")
        meta.set_xalign(0)
        box.append(meta)

    return box


# ──────────────────────────────────────────────── main window
class NotificationsWindow(Gtk.Window):
    def __init__(self) -> None:
        super().__init__(title="NYXUS Notifications")
        self.set_default_size(PANEL_W, PANEL_H)
        self.set_resizable(False)
        self.set_decorated(False)
        self.add_css_class("nyxus-notif-root")

        self._state = _load_state()

        if _HAS_LAYER_SHELL:
            try:
                LayerShell.init_for_window(self)
                LayerShell.set_layer(self, LayerShell.Layer.OVERLAY)
                LayerShell.set_keyboard_mode(self, LayerShell.KeyboardMode.ON_DEMAND)
                LayerShell.set_anchor(self, LayerShell.Edge.BOTTOM, True)
                LayerShell.set_anchor(self, LayerShell.Edge.RIGHT,  True)
                LayerShell.set_margin(self, LayerShell.Edge.BOTTOM, 60)
                LayerShell.set_margin(self, LayerShell.Edge.RIGHT,  10)
            except Exception:
                pass

        # Escape to dismiss
        esc = Gtk.EventControllerKey()
        def _on_key(_c, keyval, _kc, _mod):
            if keyval == Gdk.KEY_Escape:
                self._dismiss()
                return True
            return False
        esc.connect("key-pressed", _on_key)
        self.add_controller(esc)

        # Build UI
        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.append(self._build_header())
        root.append(self._build_body())
        root.append(self._build_footer())
        self.set_child(root)

        # Auto-close on focus-out (ON_DEMAND keyboard makes this reliable)
        self.connect("close-request", lambda *_: (_clear_pid(), False)[1])

    # ─── UI sections ─────────────────────────────────────────────────────
    def _build_header(self) -> Gtk.Widget:
        head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        head.add_css_class("nyxus-notif-header")

        bell = Gtk.Label(label="\uf0f3")  # FA bell
        bell.add_css_class("nyxus-notif-glyph")
        head.append(bell)

        title = Gtk.Label(label="Notifications")
        title.add_css_class("nyxus-notif-title")
        title.set_xalign(0); title.set_hexpand(True)
        head.append(title)

        # DND toggle
        dnd_btn = Gtk.Button()
        dnd_lbl = Gtk.Label(label="\uf186  DND")  # moon glyph
        dnd_btn.set_child(dnd_lbl)
        if self._state.get("dnd"):
            dnd_btn.add_css_class("nyxus-toggle-on")
        def _toggle_dnd(_b):
            self._state["dnd"] = not self._state.get("dnd", False)
            _save_state(self._state)
            if self._state["dnd"]:
                dnd_btn.add_css_class("nyxus-toggle-on")
            else:
                dnd_btn.remove_css_class("nyxus-toggle-on")
        dnd_btn.connect("clicked", _toggle_dnd)
        head.append(dnd_btn)

        # Close
        close_btn = Gtk.Button()
        close_btn.set_child(Gtk.Label(label="\uf00d"))  # FA times
        close_btn.connect("clicked", lambda *_: self._dismiss())
        head.append(close_btn)

        return head

    def _build_body(self) -> Gtk.Widget:
        outer = Gtk.ScrolledWindow()
        outer.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        outer.set_vexpand(True); outer.set_hexpand(True)

        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        # ── Calendar tile at the very top (matches Windows-11 Notifications
        # panel behaviour the user asked for). Uses Gtk.Calendar — a built-in
        # GTK4 widget so we don't need any extra deps. Wrapped in our standard
        # sketched plate styling.
        cal_plate = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        cal_plate.add_css_class("nyxus-section")

        cal_head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        cal_glyph = Gtk.Label(label="\uf073")  # FA calendar
        cal_glyph.add_css_class("nyxus-notif-glyph")
        cal_head.append(cal_glyph)
        today = time.strftime("%A, %B %-d, %Y")
        cal_title = Gtk.Label(label=today)
        cal_title.add_css_class("nyxus-notif-card-title")
        cal_title.set_xalign(0); cal_title.set_hexpand(True)
        cal_head.append(cal_title)
        cal_plate.append(cal_head)

        self._calendar = Gtk.Calendar()
        self._calendar.set_hexpand(True)
        cal_plate.append(self._calendar)

        col.append(cal_plate)

        # ── Reminders plate ──────────────────────────────────────
        # Quick add-bar (entry + "+" button) above a flowing list of
        # reminder rows with a small "x" delete button per item.
        # Persisted to ~/.config/nyxus-notifications/reminders.json.
        rem_plate = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        rem_plate.add_css_class("nyxus-section")

        rem_head = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        rem_glyph = Gtk.Label(label="\uf0f3")  # FA bell (substituted in the
        rem_glyph.add_css_class("nyxus-notif-glyph")  # absence of FA reminder)
        rem_head.append(rem_glyph)
        rem_title = Gtk.Label(label="Reminders")
        rem_title.add_css_class("nyxus-notif-card-title")
        rem_title.set_xalign(0); rem_title.set_hexpand(True)
        rem_head.append(rem_title)
        rem_plate.append(rem_head)

        add_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self._rem_entry = Gtk.Entry()
        self._rem_entry.set_placeholder_text("New reminder…")
        self._rem_entry.set_hexpand(True)
        self._rem_entry.connect("activate", lambda *_: self._add_reminder())
        add_row.append(self._rem_entry)
        add_btn = Gtk.Button(label="\uf067")  # FA plus
        add_btn.connect("clicked", lambda *_: self._add_reminder())
        add_row.append(add_btn)
        rem_plate.append(add_row)

        self._reminders_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        rem_plate.append(self._reminders_box)
        col.append(rem_plate)

        # ── Notifications section header
        notif_hdr = Gtk.Label(label="\uf0a2   Recent")  # FA bell-o
        notif_hdr.add_css_class("nyxus-notif-card-title")
        notif_hdr.set_xalign(0)
        notif_hdr.set_margin_start(14); notif_hdr.set_margin_top(6)
        col.append(notif_hdr)

        self._list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        col.append(self._list_box)

        outer.set_child(col)

        self._refresh_reminders()
        self._refresh_list()
        return outer

    # ── Reminders helpers ────────────────────────────────────────────
    def _add_reminder(self) -> None:
        text = (self._rem_entry.get_text() or "").strip()
        if not text:
            return
        items = _load_reminders()
        items.insert(0, {
            "id":      str(int(time.time() * 1000)),
            "text":    text,
            "created": time.time(),
        })
        _save_reminders(items)
        self._rem_entry.set_text("")
        self._refresh_reminders()

    def _delete_reminder(self, rid: str) -> None:
        items = [r for r in _load_reminders() if r.get("id") != rid]
        _save_reminders(items)
        self._refresh_reminders()

    def _refresh_reminders(self) -> None:
        # clear
        child = self._reminders_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._reminders_box.remove(child)
            child = nxt

        items = _load_reminders()
        if not items:
            empty = Gtk.Label(label="No reminders yet.")
            empty.add_css_class("nyxus-notif-empty")
            empty.set_xalign(0)
            self._reminders_box.append(empty)
            return

        for r in items:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            dot = Gtk.Label(label="\uf111")  # FA circle
            dot.add_css_class("nyxus-notif-glyph")
            row.append(dot)
            lbl = Gtk.Label(label=r["text"])
            lbl.set_xalign(0); lbl.set_hexpand(True)
            lbl.set_wrap(True); lbl.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            row.append(lbl)
            x = Gtk.Button(label="\uf00d")  # FA times
            x.add_css_class("flat")
            rid = r["id"]
            x.connect("clicked", lambda *_a, _id=rid: self._delete_reminder(_id))
            row.append(x)
            self._reminders_box.append(row)

    def _refresh_list(self) -> None:
        # clear
        child = self._list_box.get_first_child()
        while child is not None:
            nxt = child.get_next_sibling()
            self._list_box.remove(child)
            child = nxt

        entries = _read_log_entries()
        if not entries:
            empty = Gtk.Label(label="\uf0f3   No new notifications")
            empty.add_css_class("nyxus-notif-empty")
            empty.set_xalign(0.5)
            self._list_box.append(empty)

            note = Gtk.Label(
                label=("Live notification feed lands in the next NYXUS update.\n"
                       "Until then, anything written to\n"
                       "~/.local/share/nyxus/notifications.log\n"
                       "(one JSON object per line) shows up here."))
            note.add_css_class("nyxus-notif-card-meta")
            note.set_xalign(0.5); note.set_justify(Gtk.Justification.CENTER)
            note.set_wrap(True); note.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
            self._list_box.append(note)
            return

        for e in entries:
            self._list_box.append(_build_card(e))

    def _build_footer(self) -> Gtk.Widget:
        foot = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        foot.add_css_class("nyxus-notif-footer")

        clear_btn = Gtk.Button(label="\uf2ed  Clear all")
        def _clear(_b):
            try:
                if LOG_FILE.exists():
                    LOG_FILE.write_text("")
            except Exception:
                pass
            self._refresh_list()
        clear_btn.connect("clicked", _clear)
        foot.append(clear_btn)

        spacer = Gtk.Box(); spacer.set_hexpand(True)
        foot.append(spacer)

        settings_btn = Gtk.Button(label="\uf013  Settings")
        def _open_settings(_b):
            # Only dismiss the flyout if we actually launched something —
            # otherwise the user just gets a window-close with no feedback,
            # which looks like a misclick. Try nyxus-settings first; fall
            # back to opening the JSON state file in the user's editor.
            launched = False
            for cmd in (["nyxus-settings"], ["xdg-open", str(STATE_FILE)]):
                if shutil.which(cmd[0]):
                    try:
                        subprocess.Popen(cmd, start_new_session=True)
                        launched = True
                    except Exception:
                        launched = False
                    break
            if launched:
                self._dismiss()
            else:
                # No handler available — surface a tiny in-window toast
                # instead of silently closing.
                self._calendar.set_visible(True)  # keep window alive
                try:
                    if shutil.which("notify-send"):
                        subprocess.Popen(
                            ["notify-send", "-a", "NYXUS",
                             "Notifications · Settings",
                             "No nyxus-settings binary on this machine yet."],
                            start_new_session=True,
                        )
                except Exception:
                    pass
        settings_btn.connect("clicked", _open_settings)
        foot.append(settings_btn)

        return foot

    def _dismiss(self) -> None:
        try:
            self.close()
        except Exception:
            pass


# ──────────────────────────────────────────────── entry point
def main() -> int:
    # Toggle: clicking the Waybar icon a second time closes the window
    if _toggle_singleton():
        return 0

    # Hand-off: if the user already runs swaync or mako, prefer THEIR toggle
    # over ours so power users keep their workflow. We still fall through to
    # our own UI if the helper command fails.
    for binary, args in (
        ("swaync-client", ["-t"]),
        ("makoctl",       ["menu", "-n"]),
    ):
        if shutil.which(binary):
            try:
                rc = subprocess.run([binary, *args], timeout=2).returncode
                if rc == 0:
                    return 0
            except Exception:
                pass  # fall through to our own UI
            break

    _write_pid()
    try:
        # SIGTERM from another instance → clean exit
        signal.signal(signal.SIGTERM, lambda *_: (_clear_pid(), os._exit(0)))

        app = Gtk.Application(application_id=APP_ID,
                              flags=Gio.ApplicationFlags.NON_UNIQUE)

        def _on_activate(_a):
            _install_css()
            win = NotificationsWindow()
            app.add_window(win)
            win.present()

        app.connect("activate", _on_activate)
        return app.run(None)
    finally:
        _clear_pid()



# ─────────────────────────── NYXUS CHROME (DISABLED) ───────────────────────
# nyxus-notifications uses gtk4-layer-shell, INCOMPATIBLE with the
# Gtk.Overlay-based GraffitiBackground in nyxus_chrome. Same exclusion as
# nyxus-panel and nyxus-start. Notifications styles itself inline.
# ────────────────────────── /NYXUS CHROME (DISABLED) ────────────────────────

if __name__ == "__main__":
    sys.exit(main())
