#!/usr/bin/env python3
"""
NYXUS Screenshot — grim + slurp wrapper with annotation, copy, OCR.

Usage modes (CLI flags or interactive picker):
  region         — slurp a rectangle, save + copy
  fullscreen     — current monitor
  window         — active hyprctl window
  --copy-only    — to clipboard, don't save
  --annotate     — open in swappy after capture
  --ocr          — extract text via tesseract → clipboard
  --delay N      — wait N seconds before capture (countdown)
  --no-sound     — skip the shutter chime

Without args opens a small NYXUS-styled picker window.
"""
from __future__ import annotations
import argparse, gi, os, subprocess, sys, time, json
from datetime import datetime
from pathlib import Path

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, Gdk, GLib, Gio

sys.path.insert(0, str(Path.home() / ".local" / "bin"))
try:
    from nyxus_chrome import install_chrome, rainbow_markup  # type: ignore
    HAS_CHROME = True
except Exception:
    HAS_CHROME = False
    def install_chrome(win, key="_screenshot"): return None
    def rainbow_markup(s: str) -> str:
        return f"<span foreground='#ff00ff' font_weight='bold'>{s}</span>"

PIC_DIR = Path.home() / "Pictures" / "Screenshots"


def have(cmd: str) -> bool:
    return any((Path(p) / cmd).exists()
               for p in os.environ.get("PATH", "").split(":"))


def shutter_path() -> str:
    return f"{PIC_DIR}/nyxus-{datetime.now():%Y%m%d-%H%M%S}.png"


def notify(msg: str, title: str = "NYXUS Screenshot") -> None:
    if have("notify-send"):
        subprocess.run(["notify-send", "-a", "nyxus-screenshot",
                        title, msg], timeout=2)


def play_chime() -> None:
    for cmd, args in (
            ("paplay", ["/usr/share/sounds/freedesktop/stereo/camera-shutter.oga"]),
            ("aplay", ["-q",
                       "/usr/share/sounds/freedesktop/stereo/camera-shutter.oga"]),
    ):
        if have(cmd):
            try:
                subprocess.Popen([cmd] + args,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
                return
            except Exception:
                pass


def copy_image(path: str) -> bool:
    if have("wl-copy"):
        try:
            with open(path, "rb") as f:
                p = subprocess.Popen(["wl-copy", "--type", "image/png"],
                                     stdin=subprocess.PIPE)
                p.communicate(f.read(), timeout=4)
            return True
        except Exception:
            return False
    return False


def get_active_window_geom() -> str | None:
    if not have("hyprctl"): return None
    try:
        rc = subprocess.run(["hyprctl", "-j", "activewindow"],
                            capture_output=True, text=True, timeout=2)
        if rc.returncode != 0: return None
        w = json.loads(rc.stdout)
        x, y = w.get("at", [0, 0]); ww, wh = w.get("size", [0, 0])
        if ww <= 0 or wh <= 0: return None
        return f"{x},{y} {ww}x{wh}"
    except Exception:
        return None


def capture(mode: str, opts) -> str | None:
    PIC_DIR.mkdir(parents=True, exist_ok=True)
    out = shutter_path()
    if not have("grim"):
        notify("grim not installed (pacman -S grim)"); return None

    geom = ""
    if mode == "region":
        if not have("slurp"):
            notify("slurp not installed (pacman -S slurp)"); return None
        try:
            r = subprocess.run(["slurp"], capture_output=True, text=True,
                               timeout=60)
            if r.returncode != 0 or not r.stdout.strip():
                return None
            geom = r.stdout.strip()
        except Exception as e:
            notify(f"slurp failed: {e}"); return None
    elif mode == "window":
        g = get_active_window_geom()
        if not g:
            notify("could not determine active window"); return None
        geom = g

    if opts.delay > 0:
        for s in range(opts.delay, 0, -1):
            notify(f"capturing in {s}s…"); time.sleep(1)

    cmd = ["grim"]
    if geom: cmd += ["-g", geom]
    cmd += [out]
    rc = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    if rc.returncode != 0:
        notify(f"grim failed: {rc.stderr.strip()}"); return None

    if not opts.no_sound: play_chime()

    copied = copy_image(out)
    if opts.copy_only:
        Path(out).unlink(missing_ok=True)
        notify("copied to clipboard")
        return out

    if opts.ocr and have("tesseract"):
        try:
            txt = subprocess.run(
                ["tesseract", out, "-", "-l", "eng"],
                capture_output=True, text=True, timeout=30).stdout.strip()
            if txt and have("wl-copy"):
                p = subprocess.Popen(["wl-copy"], stdin=subprocess.PIPE)
                p.communicate(txt.encode(), timeout=4)
                notify(f"OCR · {len(txt)} chars copied")
        except Exception as e:
            notify(f"OCR failed: {e}")

    if opts.annotate and have("swappy"):
        subprocess.Popen(["swappy", "-f", out], start_new_session=True)
    else:
        notify(f"saved → {out}" + ("  (clipboard)" if copied else ""))

    return out


# ── interactive picker ──────────────────────────────────────────────────
class Picker(Gtk.Application):
    def __init__(self, opts):
        super().__init__(application_id="io.nyxus.screenshot",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self._opts = opts

    def do_activate(self):
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self.win = Gtk.ApplicationWindow(application=self,
                                         title="NYXUS Screenshot")
        self.win.set_default_size(520, 360)
        self.win.set_decorated(False)
        self.win.set_resizable(False)
        self.win.add_css_class("nyxus-shot")
        if HAS_CHROME:
            try: install_chrome(self.win, key="_screenshot")
            except Exception: pass

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        outer.set_margin_top(20); outer.set_margin_bottom(20)
        outer.set_margin_start(22); outer.set_margin_end(22)
        outer.set_halign(Gtk.Align.CENTER)
        outer.set_valign(Gtk.Align.CENTER)
        self.win.set_child(outer)

        title = Gtk.Label()
        title.set_markup(rainbow_markup("SCREENSHOT · NYXUS"))
        title.add_css_class("nyxus-title")
        outer.append(title)

        # mode buttons
        modes = [
            ("Region",     "region",     "▭", "#39ff14"),
            ("Window",     "window",     "🗖", "#00aaff"),
            ("Full screen","fullscreen", "▣", "#ffd700"),
        ]
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        row.set_halign(Gtk.Align.CENTER)
        outer.append(row)
        for label, mode, glyph, color in modes:
            b = Gtk.Button()
            b.set_size_request(130, 90)
            b.add_css_class("nyxus-shotbtn")
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            g = Gtk.Label()
            g.set_markup(f"<span foreground='{color}' size='xx-large' "
                         f"font_weight='bold'>{glyph}</span>")
            inner.append(g)
            l = Gtk.Label()
            l.set_markup(f"<span foreground='{color}' size='large' "
                         f"font_weight='bold'>{label}</span>")
            inner.append(l)
            b.set_child(inner)
            b.connect("clicked", lambda _b, m=mode: self._do(m))
            row.append(b)

        # toggles
        opts_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                           spacing=14, halign=Gtk.Align.CENTER)
        outer.append(opts_row)
        self._cb_annotate = Gtk.CheckButton(label="Annotate (swappy)")
        self._cb_annotate.set_active(have("swappy"))
        self._cb_annotate.add_css_class("nyxus-cb")
        opts_row.append(self._cb_annotate)
        self._cb_copy = Gtk.CheckButton(label="Copy only")
        self._cb_copy.add_css_class("nyxus-cb")
        opts_row.append(self._cb_copy)
        self._cb_ocr = Gtk.CheckButton(label="OCR")
        self._cb_ocr.set_sensitive(have("tesseract"))
        self._cb_ocr.add_css_class("nyxus-cb")
        opts_row.append(self._cb_ocr)

        hint = Gtk.Label(label="esc cancel · pictures saved to ~/Pictures/Screenshots",
                         xalign=0.5)
        hint.add_css_class("nyxus-hint")
        outer.append(hint)

        kc = Gtk.EventControllerKey()
        kc.connect("key-pressed",
                   lambda *a: self.quit() if a[1] == Gdk.KEY_Escape else False)
        kc.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        self.win.add_controller(kc)
        self.win.present()

    def _do(self, mode: str):
        self._opts.annotate  = self._cb_annotate.get_active()
        self._opts.copy_only = self._cb_copy.get_active()
        self._opts.ocr       = self._cb_ocr.get_active()
        self.win.hide()
        # let GTK process the hide before the slurp grab
        GLib.timeout_add(100, lambda: (capture(mode, self._opts),
                                       self.quit(), False)[2])


CSS = """
window.nyxus-shot {
    background: rgba(8, 6, 14, 0.86);
    border-radius: 8px;
}
.nyxus-title {
    font-family: 'Caveat', sans-serif;
    font-size: 28px;
    text-shadow: 0 0 12px rgba(255, 0, 255, 0.6);
}
.nyxus-shotbtn {
    background: rgba(15, 12, 24, 0.92);
    border: 2px solid rgba(255, 0, 255, 0.40);
    border-radius: 6px;
}
.nyxus-shotbtn:hover {
    background: rgba(255, 0, 255, 0.16);
    border-color: #ff00ff;
    box-shadow: 0 0 14px rgba(255, 0, 255, 0.5);
}
.nyxus-cb {
    font-family: 'Caveat', sans-serif;
    font-size: 16px;
    color: #ffffff;
}
.nyxus-hint {
    font-family: 'Caveat', sans-serif;
    font-size: 13px;
    color: rgba(255, 255, 255, 0.45);
}
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="NYXUS screenshot")
    ap.add_argument("mode", nargs="?",
                    choices=["region", "window", "fullscreen", "picker"],
                    default="picker")
    ap.add_argument("--copy-only", action="store_true",
                    dest="copy_only")
    ap.add_argument("--annotate", action="store_true")
    ap.add_argument("--ocr", action="store_true")
    ap.add_argument("--delay", type=int, default=0)
    ap.add_argument("--no-sound", action="store_true", dest="no_sound")
    args = ap.parse_args()
    if args.mode == "picker":
        return Picker(args).run([sys.argv[0]])
    return 0 if capture(args.mode, args) else 1


if __name__ == "__main__":
    sys.exit(main())
