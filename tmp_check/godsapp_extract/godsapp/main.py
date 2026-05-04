#!/usr/bin/env python3
"""
NYXUS GodsApp — entry point.
© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED

First launch presents the authorization gate exactly once.
After that, the main window runs with hand-drawn UI and an idle screensaver.

    sudo nyxus-godsapp           # full capabilities
    nyxus-godsapp                # user mode (limited)
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GLib, Gtk, Gdk, Gio, Adw  # noqa: E402

# make local modules (ui, screensaver, modules/) importable
sys.path.insert(0, str(Path(__file__).resolve().parent))

from ui import (  # noqa: E402
    MainWindow,
    AUTHORIZE_FLAG_PATH,
    NYX,
    install_global_css,
    TiltedHeader,
    SketchPanel,
    SketchButton,
)

APP_ID = "co.nyxus.GodsApp"


class AuthorizationGate(Adw.ApplicationWindow):
    """Shown ONCE. Records timestamp + user acceptance. Never reappears."""

    BODY = (
        "NYXUS GodsApp is a professional security auditing and research tool.\n\n"
        "You are solely responsible for ensuring you have proper authorization "
        "before scanning, auditing, or testing any network, system, or device "
        "you do not own. Unauthorized use of these tools may be illegal in "
        "your jurisdiction.\n\n"
        "By continuing you accept full and complete responsibility for how you "
        "use these tools."
    )

    def __init__(self, app):
        super().__init__(application=app, title="NYXUS GodsApp · Authorization")
        self.app = app
        self.set_default_size(820, 620)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                        margin_top=28, margin_bottom=28,
                        margin_start=44, margin_end=44, spacing=14)

        outer.append(TiltedHeader("GODSAPP", size=56, tilt=-3.5, height=98))
        outer.append(TiltedHeader("authorization required",
                                  size=24, tilt=-1.5, height=42))

        body_panel = SketchPanel(color=NYX["ink"], padding=18)
        body_panel.set_vexpand(True)
        body = Gtk.Label(label=self.BODY, wrap=True, xalign=0, yalign=0)
        body.set_max_width_chars(72)
        body.add_css_class("nyx-dim")
        body_panel.append(body)
        outer.append(body_panel)

        self.check = Gtk.CheckButton(
            label="I accept full responsibility for my use of these tools.")
        self.check.connect("toggled",
                           lambda c: self.cont.set_sensitive(c.get_active()))
        outer.append(self.check)

        bar = Gtk.Box(spacing=14, halign=Gtk.Align.END)
        cancel = SketchButton("Cancel", color=NYX["dim"],
                              on_click=lambda: app.quit())
        self.cont = SketchButton("Continue", color=NYX["accent"],
                                 on_click=self.on_continue)
        self.cont.set_sensitive(False)
        bar.append(cancel)
        bar.append(self.cont)
        outer.append(bar)

        self.set_content(outer)

    def on_continue(self):
        AUTHORIZE_FLAG_PATH.parent.mkdir(parents=True, exist_ok=True)
        AUTHORIZE_FLAG_PATH.write_text(json.dumps({
            "accepted": True,
            "ts": time.time(),
            "ts_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "user": os.environ.get("USER", "?"),
            "uid": os.getuid(),
        }, indent=2))
        self.close()
        self.app.launch_main()


class GodsApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.HANDLES_OPEN)
        self.connect("activate", self.on_activate)
        self.win: MainWindow | None = None

    def on_activate(self, _a):
        install_global_css(Gdk.Display.get_default())
        if AUTHORIZE_FLAG_PATH.exists():
            self.launch_main()
        else:
            AuthorizationGate(self).present()

    def launch_main(self):
        self.win = MainWindow(self)
        self.win.present()


def main() -> int:
    return GodsApp().run(None)



# ─────────────────────────── NYXUS CHROME (auto-injected) ───────────────────
# Unifies look across every NYXUS GTK4 app: graffiti background, Caveat
# font, neon palette. Monkey-patches BOTH Gtk.ApplicationWindow.present
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
    _NYX_PAGE_KEY = "_godsapp"
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
