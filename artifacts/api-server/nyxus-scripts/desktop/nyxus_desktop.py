#!/usr/bin/env python3
"""
NYXUS Desktop — interactive layer-shell desktop client.

Replaces swaybg. Paints the wallpaper itself per-monitor at the `bottom`
layer-shell layer (under bars, under all windows). Catches mouse events
on the wallpaper and dispatches to nyxus-context-menu.sh.

Turn 1 scope (this file): wallpaper paint + click dispatch + multi-monitor
+ hot-plug + IPC socket hook for live wallpaper hot-swap. No icons yet
(those land in T2).

Config:  ~/.config/nyxus/desktop.toml  (wallpaper, fit, bg_color)
State:   ~/.config/nyxus/desktop-icons.json  (used by T2)
Log:     ~/.cache/nyxus/desktop.log
IPC:     $XDG_RUNTIME_DIR/nyxus-desktop.sock  (line protocol)
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import socket
import subprocess
import sys
import threading
from pathlib import Path
from typing import Optional

import gi

# --- hard-required deps -----------------------------------------------------
try:
    gi.require_version("Gtk", "4.0")
    gi.require_version("Gdk", "4.0")
    from gi.repository import Gdk, Gio, GLib, Gtk  # noqa: E402
except Exception as _gtk_err:
    sys.stderr.write(f"nyxus_desktop: GTK4 unavailable ({_gtk_err}); "
                     "falling back to swaybg.\n")
    os.execvp("swaybg", [
        "swaybg", "-i",
        os.path.expanduser(
            "~/.config/hypr/walls/nyxus-void-vortex.png"),
        "-m", "fill", "-c", "#000000",
    ])

# --- soft-required: gtk4-layer-shell (no shell layer = no desktop) ---------
try:
    gi.require_version("Gtk4LayerShell", "1.0")
    from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402
except Exception as _ls_err:
    sys.stderr.write(f"nyxus_desktop: gtk4-layer-shell unavailable "
                     f"({_ls_err}); falling back to swaybg.\n")
    os.execvp("swaybg", [
        "swaybg", "-i",
        os.path.expanduser(
            "~/.config/hypr/walls/nyxus-void-vortex.png"),
        "-m", "fill", "-c", "#000000",
    ])

# ---------- paths ----------
HOME = Path(os.path.expanduser("~"))
CFG_DIR = HOME / ".config" / "nyxus"
CACHE_DIR = HOME / ".cache" / "nyxus"
CFG_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CFG_FILE = CFG_DIR / "desktop.toml"
LOG_FILE = CACHE_DIR / "desktop.log"
SOCK_PATH = Path(
    os.environ.get("XDG_RUNTIME_DIR", "/tmp")
) / "nyxus-desktop.sock"

DEFAULT_WALL = HOME / ".config" / "hypr" / "walls" / "nyxus-void-vortex.png"
DEFAULT_BG = "#080a10"
CONTEXT_MENU = "nyxus-context-menu.sh"

# ---------- logging ----------
log = logging.getLogger("nyxus_desktop")
log.setLevel(logging.INFO)
_handler = logging.handlers.RotatingFileHandler(
    LOG_FILE, maxBytes=512_000, backupCount=3
)
_handler.setFormatter(
    logging.Formatter("%(asctime)s %(levelname)s %(message)s")
)
log.addHandler(_handler)


# ---------- config ----------
def load_config() -> dict:
    """Return wallpaper config. TOML if available, else defaults."""
    cfg = {
        "wallpaper": str(DEFAULT_WALL),
        "fit": "fill",
        "bg_color": DEFAULT_BG,
    }
    if CFG_FILE.exists():
        try:
            import tomllib  # py 3.11+
            with CFG_FILE.open("rb") as f:
                data = tomllib.load(f)
            cfg.update({k: v for k, v in data.items() if k in cfg})
        except Exception as e:
            log.warning("config parse failed: %s", e)
    # resolve ~ in wallpaper
    cfg["wallpaper"] = os.path.expanduser(cfg["wallpaper"])
    return cfg


def save_config(cfg: dict) -> None:
    lines = [
        f'wallpaper = "{cfg["wallpaper"]}"',
        f'fit = "{cfg["fit"]}"',
        f'bg_color = "{cfg["bg_color"]}"',
    ]
    CFG_FILE.write_text("\n".join(lines) + "\n")


# ---------- desktop window per monitor ----------
class DesktopSurface(Gtk.ApplicationWindow):
    """One layer-shell window per monitor."""

    def __init__(
        self,
        app: Gtk.Application,
        monitor: Gdk.Monitor,
        cfg: dict,
    ) -> None:
        super().__init__(application=app)
        self.monitor = monitor
        self.cfg = cfg
        self._build_layer()
        self._build_content()
        self._build_input()

    # -- layer-shell config --
    def _build_layer(self) -> None:
        LayerShell.init_for_window(self)
        LayerShell.set_layer(self, LayerShell.Layer.BOTTOM)
        LayerShell.set_monitor(self, self.monitor)
        for edge in (
            LayerShell.Edge.TOP,
            LayerShell.Edge.BOTTOM,
            LayerShell.Edge.LEFT,
            LayerShell.Edge.RIGHT,
        ):
            LayerShell.set_anchor(self, edge, True)
        # do not push other layers around
        LayerShell.set_exclusive_zone(self, -1)
        LayerShell.set_namespace(self, "nyxus-desktop")
        LayerShell.set_keyboard_mode(self, LayerShell.KeyboardMode.NONE)

    # -- content (wallpaper + future icon layer) --
    def _build_content(self) -> None:
        self.overlay = Gtk.Overlay()
        self.set_child(self.overlay)

        # background fill (always covers, even before image loads)
        bg = Gtk.Box()
        bg.add_css_class("nyxus-desktop-bg")
        self.overlay.set_child(bg)

        # wallpaper picture
        self.picture = Gtk.Picture()
        self.picture.set_can_shrink(True)
        self.picture.set_keep_aspect_ratio(False)  # fit=fill
        self._apply_wallpaper(self.cfg.get("wallpaper", ""))
        self.overlay.add_overlay(self.picture)

        # icon layer (populated in T2). Transparent, swallows nothing.
        self.icon_layer = Gtk.Fixed()
        self.icon_layer.add_css_class("nyxus-desktop-icons")
        self.overlay.add_overlay(self.icon_layer)

    def _apply_wallpaper(self, path: str) -> None:
        p = Path(os.path.expanduser(path or ""))
        if not p.exists():
            log.warning("wallpaper missing: %s", p)
            return
        try:
            self.picture.set_filename(str(p))
            log.info("wallpaper applied on %s: %s",
                     self.monitor.get_connector(), p.name)
        except Exception as e:
            log.error("set wallpaper failed: %s", e)

    # -- input: right/left click on bare desktop --
    # Attached to the overlay (so we always see clicks), but T2 icon widgets
    # MUST call `gesture.set_state(Gtk.EventSequenceState.CLAIMED)` in their
    # own GestureClick handler so this background handler ignores them.
    # As a second guard, _on_click uses Gtk.Widget.pick() to detect whether
    # the click landed on an icon child and bails out if so.
    def _build_input(self) -> None:
        gesture = Gtk.GestureClick()
        gesture.set_button(0)  # any
        gesture.set_propagation_phase(Gtk.PropagationPhase.BUBBLE)
        gesture.connect("pressed", self._on_click)
        self.overlay.add_controller(gesture)

    def _hit_is_icon(self, x: float, y: float) -> bool:
        """True if (x,y) lands inside an icon widget on the icon layer."""
        try:
            target = self.overlay.pick(x, y, Gtk.PickFlags.DEFAULT)
        except Exception:
            return False
        w = target
        while w is not None:
            if w is self.icon_layer:
                # bare icon_layer (no child) = bare desktop, treat as bg
                return target is not self.icon_layer
            w = w.get_parent()
        return False

    def _on_click(self, gesture: Gtk.GestureClick, n: int,
                  x: float, y: float) -> None:
        if self._hit_is_icon(x, y):
            return  # icon handler owns it
        button = gesture.get_current_button()
        if button == Gdk.BUTTON_SECONDARY:
            self._spawn_menu("main")
        elif button == Gdk.BUTTON_PRIMARY:
            self._spawn_menu("dismiss")

    def _spawn_menu(self, mode: str) -> None:
        try:
            subprocess.Popen(
                [CONTEXT_MENU, mode],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
        except FileNotFoundError:
            log.error("context menu script not on PATH: %s", CONTEXT_MENU)
        except Exception as e:
            log.error("menu spawn failed: %s", e)

    # -- public: hot-swap wallpaper --
    def set_wallpaper(self, path: str) -> None:
        self.cfg["wallpaper"] = path
        self._apply_wallpaper(path)


# ---------- IPC server (live wallpaper hot-swap from any process) ----------
class IPCServer(threading.Thread):
    """Tiny line-protocol Unix socket. Commands:
        WALLPAPER <abs-path>\n   -> swap on all monitors
        RELOAD\n                 -> re-read config
        PING\n                   -> reply PONG
    """

    def __init__(self, app: "DesktopApp") -> None:
        super().__init__(daemon=True)
        self.app = app

    def run(self) -> None:
        try:
            if SOCK_PATH.exists():
                SOCK_PATH.unlink()
            srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            srv.bind(str(SOCK_PATH))
            os.chmod(SOCK_PATH, 0o600)
            srv.listen(4)
            log.info("ipc listening on %s", SOCK_PATH)
            while True:
                conn, _ = srv.accept()
                try:
                    data = conn.recv(4096).decode("utf-8", "ignore").strip()
                    self._handle(conn, data)
                finally:
                    conn.close()
        except Exception as e:
            log.error("ipc crashed: %s", e)

    def _handle(self, conn: socket.socket, data: str) -> None:
        if not data:
            return
        if data == "PING":
            conn.sendall(b"PONG\n")
            return
        if data.startswith("WALLPAPER "):
            path = data[len("WALLPAPER "):].strip()
            GLib.idle_add(self.app.set_wallpaper_all, path)
            conn.sendall(b"OK\n")
            return
        if data == "RELOAD":
            GLib.idle_add(self.app.reload_config)
            conn.sendall(b"OK\n")
            return
        conn.sendall(b"ERR unknown command\n")


# ---------- application ----------
CSS = b"""
.nyxus-desktop-bg { background: #080a10; }
.nyxus-desktop-icons { background: transparent; }
"""


class DesktopApp(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id="com.nyxus.desktop",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
        )
        self.windows_by_monitor: dict[str, DesktopSurface] = {}
        self.cfg: dict = load_config()

    def do_startup(self) -> None:  # type: ignore[override]
        Gtk.Application.do_startup(self)
        provider = Gtk.CssProvider()
        provider.load_from_data(CSS)
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def do_activate(self) -> None:  # type: ignore[override]
        display = Gdk.Display.get_default()
        if display is None:
            log.error("no Gdk display; bailing")
            return
        self._spawn_for_all_monitors(display)
        # hot-plug
        monitors = display.get_monitors()
        monitors.connect("items-changed", self._on_monitors_changed, display)
        # ipc
        IPCServer(self).start()

    # -- monitors --
    def _spawn_for_all_monitors(self, display: Gdk.Display) -> None:
        monitors = display.get_monitors()
        for i in range(monitors.get_n_items()):
            monitor = monitors.get_item(i)
            if monitor is None:
                continue
            self._spawn_for_monitor(monitor)

    def _spawn_for_monitor(self, monitor: Gdk.Monitor) -> None:
        key = monitor.get_connector() or f"mon{id(monitor)}"
        if key in self.windows_by_monitor:
            return
        win = DesktopSurface(self, monitor, dict(self.cfg))
        win.present()
        self.windows_by_monitor[key] = win
        log.info("desktop spawned on %s", key)

    def _on_monitors_changed(
        self,
        monitors,
        position: int,
        removed: int,
        added: int,
        display: Gdk.Display,
    ) -> None:
        # rebuild known set
        present = set()
        for i in range(monitors.get_n_items()):
            mon = monitors.get_item(i)
            if mon is None:
                continue
            key = mon.get_connector() or f"mon{id(mon)}"
            present.add(key)
            if key not in self.windows_by_monitor:
                self._spawn_for_monitor(mon)
        # close stale
        for key in list(self.windows_by_monitor.keys()):
            if key not in present:
                self.windows_by_monitor[key].close()
                del self.windows_by_monitor[key]
                log.info("desktop closed on %s (unplugged)", key)

    # -- public hooks for IPC --
    def set_wallpaper_all(self, path: str) -> bool:
        self.cfg["wallpaper"] = path
        save_config(self.cfg)
        for win in self.windows_by_monitor.values():
            win.set_wallpaper(path)
        return False  # one-shot idle

    def reload_config(self) -> bool:
        self.cfg = load_config()
        for win in self.windows_by_monitor.values():
            win.set_wallpaper(self.cfg["wallpaper"])
        return False


def main() -> int:
    app = DesktopApp()
    try:
        return app.run(sys.argv)
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    sys.exit(main())
