# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
First-launch legal disclaimer.

Shown once per user, per app. Acceptance is recorded with a UTC
timestamp in ~/.config/nyxus/accepted.json. The dialog is a single
GTK4 modal with one acknowledgement checkbox and one Continue button —
the button stays insensitive until the box is checked.

After acceptance the file looks like:

    {
        "NYXUS Phantom": {
            "accepted": true,
            "ts": "2026-05-02T14:31:08+00:00",
            "version": "1.0.0",
            "iso": "nyx-2026.05.02-x86_64.iso"
        }
    }
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

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
from gi.repository import Gtk

DISCLAIMER_TEXT = (
    "NYXUS is original software created by\n"
    "Joseph Sierengowski.\n"
    "Copyright © 2026. All Rights Reserved.\n"
    "Personal use only.\n"
    "Redistribution and commercial use\n"
    "are strictly prohibited."
)


def _accepted_path() -> Path:
    p = Path.home() / ".config" / "nyxus"
    p.mkdir(parents=True, exist_ok=True)
    return p / "accepted.json"


def _load() -> dict:
    p = _accepted_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save(data: dict) -> None:
    try:
        _accepted_path().write_text(
            json.dumps(data, indent=2, sort_keys=True), encoding="utf-8"
        )
    except OSError:
        pass


def is_accepted(app_name: str) -> bool:
    rec = _load().get(app_name)
    return bool(rec and rec.get("accepted"))


def record_acceptance(app_name: str, version: str = "1.0.0") -> None:
    data = _load()
    data[app_name] = {
        "accepted": True,
        "ts": datetime.now(timezone.utc).isoformat(),
        "version": version,
        "iso": "nyx-2026.05.02-x86_64.iso",
    }
    _save(data)


def show_disclaimer(parent: Gtk.Window | None,
                    app_name: str,
                    on_accepted) -> None:
    """
    Show the modal disclaimer. Calls on_accepted() exactly once when the
    user checks the box and clicks Continue. The dialog has no Cancel —
    the only way to dismiss it is to accept.
    """
    if is_accepted(app_name):
        on_accepted()
        return

    dlg = Gtk.Window(title=f"{app_name} — Legal")
    dlg.set_modal(True)
    if parent is not None:
        dlg.set_transient_for(parent)
    dlg.set_default_size(560, 360)
    dlg.set_resizable(False)

    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=14,
                  margin_top=22, margin_bottom=18,
                  margin_start=24, margin_end=24)
    dlg.set_child(box)

    title = Gtk.Label(label=f"{app_name}  ·  Legal Notice")
    title.add_css_class("title-2")
    title.set_xalign(0.0)
    box.append(title)

    sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
    box.append(sep)

    body = Gtk.Label(label=DISCLAIMER_TEXT)
    body.set_wrap(True); body.set_xalign(0.0); body.set_yalign(0.0)
    body.set_vexpand(True)
    box.append(body)

    chk = Gtk.CheckButton(
        label="I have read and accept the NYX & NYXUS license."
    )
    box.append(chk)

    btn_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8,
                      halign=Gtk.Align.END)
    box.append(btn_row)

    btn = Gtk.Button(label="Continue")
    btn.add_css_class("suggested-action")
    btn.set_sensitive(False)
    btn_row.append(btn)

    def _on_toggle(_widget):
        btn.set_sensitive(chk.get_active())
    chk.connect("toggled", _on_toggle)

    def _on_continue(_widget):
        record_acceptance(app_name)
        dlg.close()
        on_accepted()
    btn.connect("clicked", _on_continue)

    dlg.present()
