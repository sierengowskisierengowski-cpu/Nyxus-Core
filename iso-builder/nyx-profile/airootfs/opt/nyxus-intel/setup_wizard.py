# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · setup_wizard.py
First-launch flow: legal disclaimer only.

The app is passwordless — cases are still AES-256-GCM encrypted at rest
using a per-device key generated automatically on first launch (see
auth.get_or_create_device_key). The user only has to accept the legal
disclaimer once.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import time

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
from gi.repository import Gtk, GLib

from auth import save_config, load_config, get_or_create_device_key

DISCLAIMER_TEXT = (
    "NYXUS INTEL is a professional grade Open Source Intelligence (OSINT) "
    "investigation workstation. It queries publicly available data sources "
    "and aggregates the results into encrypted case files on your machine.\n\n"
    "By continuing, you certify that:\n\n"
    "  •  You will only investigate subjects you are legally authorised to "
    "investigate (yourself, persons who have given consent, or as part of "
    "lawful work).\n\n"
    "  •  You will comply with the Computer Fraud and Abuse Act (US), "
    "GDPR (EU), and any other privacy and surveillance laws that apply to "
    "you and your subject.\n\n"
    "  •  You will not use this tool for stalking, harassment, doxxing, "
    "discrimination, or any other malicious purpose.\n\n"
    "  •  You understand that aggregated open-source data, even when each "
    "individual datum is public, can be highly sensitive in combination "
    "and you will protect your case files accordingly.\n\n"
    "All cases are stored AES-256-GCM encrypted on this device only — using "
    "a per-device key auto-generated at ~/.config/nyxus-intel/device.key. "
    "Nothing is ever transmitted to NYXUS or any third party other than the "
    "specific OSINT API you choose to invoke.\n\n"
    "© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED"
)


class SetupWizard(Gtk.Window):
    """Single-page disclaimer window. Calls `on_done(True)` once the user
    accepts; calls `on_done(False)` if they close it without accepting."""

    def __init__(self, on_done):
        super().__init__(title="NYXUS INTEL — Setup")
        self.set_default_size(720, 620)
        self._on_done = on_done
        self._finished = False

        self.connect("close-request", self._on_close)
        self.set_child(self._build_disclaimer())
        self.add_css_class("nx-window")

    def _build_disclaimer(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                        margin_top=20, margin_bottom=20,
                        margin_start=24, margin_end=24)

        title = Gtk.Label(label="Legal Disclaimer")
        title.add_css_class("nx-h1"); title.set_xalign(0)
        outer.append(title)

        sub = Gtk.Label(label="Please read carefully — required once.")
        sub.add_css_class("nx-dim"); sub.set_xalign(0)
        outer.append(sub)

        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        body = Gtk.Label(label=DISCLAIMER_TEXT, wrap=True, xalign=0, yalign=0,
                         margin_top=8, margin_bottom=8,
                         margin_start=8, margin_end=8)
        body.add_css_class("nx-body")
        scroll.set_child(body)
        outer.append(scroll)

        chk = Gtk.CheckButton(label="I understand and accept these terms")
        chk.add_css_class("nx-check")
        outer.append(chk)

        btnrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                         halign=Gtk.Align.END, margin_top=8)
        cancel = Gtk.Button(label="Quit")
        cancel.connect("clicked", lambda *_: self.close())
        btnrow.append(cancel)

        cont = Gtk.Button(label="Continue")
        cont.add_css_class("suggested-action")
        cont.add_css_class("nx-primary")
        cont.set_sensitive(False)
        chk.connect("toggled", lambda c: cont.set_sensitive(c.get_active()))
        cont.connect("clicked", self._on_accept)
        btnrow.append(cont)
        outer.append(btnrow)

        return outer

    def _on_accept(self, *_):
        try:
            # Provision the device key on disk (idempotent).
            get_or_create_device_key()
            cfg = load_config()
            cfg["disclaimer_accepted_at"] = int(time.time())
            save_config(cfg)
        except Exception as e:
            # Surface the error in the title bar — there's no _msg label here.
            self.set_title(f"NYXUS INTEL — Setup error: {e}")
            return
        self._finished = True
        self.close()

    def _on_close(self, *_):
        GLib.idle_add(self._on_done, self._finished)
        return False
