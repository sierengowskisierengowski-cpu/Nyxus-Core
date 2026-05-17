#!/usr/bin/env python3
# ============================================================================
#  nyxus_settings_accessibility.py · NYXUS · Accessibility   rev 2026-05-13 r1
#
#  Standalone GTK4 panel for Settings → Accessibility (P6.32).
#
#  Toggles user-scope state only — never edits root files. Profile choice
#  rewrites ~/.local/share/orca/user-settings.conf (which the orca preset
#  shipped under /etc/skel seeds at first login). High-contrast variant
#  flips the GTK theme via the gsettings interface schema. Magnifier
#  toggle just exec's `gsettings set org.gnome.desktop.a11y.applications`.
#
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

import gi  # type: ignore[import-not-found]

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

LOG_DIR = Path.home() / ".cache" / "nyxus"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "accessibility.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("nyxus_a11y")

ORCA_CONF = Path.home() / ".local" / "share" / "orca" / "user-settings.conf"

PROFILES = ("default", "low-vision", "screen-reader")


def _gsettings(*args: str) -> tuple[bool, str]:
    if not shutil.which("gsettings"):
        return False, "gsettings missing"
    try:
        proc = subprocess.run(
            ["gsettings", *args],
            capture_output=True, text=True, check=False, timeout=10,
        )
    except subprocess.TimeoutExpired:
        return False, "gsettings timed out"
    if proc.returncode != 0:
        return False, proc.stderr.strip() or f"rc={proc.returncode}"
    return True, proc.stdout.rstrip()


def _read_orca() -> dict:
    if not ORCA_CONF.exists():
        return {"general": {}, "activeProfile": "default"}
    try:
        return json.loads(ORCA_CONF.read_text())
    except Exception as exc:  # pragma: no cover
        log.warning("orca read: %s", exc)
        return {"general": {}, "activeProfile": "default"}


def _write_orca(doc: dict) -> None:
    ORCA_CONF.parent.mkdir(parents=True, exist_ok=True)
    tmp = ORCA_CONF.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2))
    tmp.replace(ORCA_CONF)


# ── GTK panel ───────────────────────────────────────────────────────────
class A11yPanel(Gtk.Box):
    def __init__(self) -> None:
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(16)
        self.set_margin_end(16)

        page = Adw.PreferencesPage()
        scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scroller.set_child(page)
        self.append(scroller)

        # ── Vision ───────────────────────────────────────────────────
        vision = Adw.PreferencesGroup(
            title="Vision",
            description=(
                "Theme + magnifier toggles for users with low vision. "
                "All changes apply to your account only."
            ),
        )

        # High-contrast variant — uses the GNOME a11y interface schema, which
        # is the canonical key for forcing the high-contrast theme. Setting
        # color-scheme=prefer-dark would only flip dark/light, not contrast.
        ok, current = _gsettings("get",
                                  "org.gnome.desktop.a11y.interface",
                                  "high-contrast")
        is_high_contrast = "true" in (current or "").lower()
        self.contrast = Adw.SwitchRow(
            title="High-contrast theme",
            subtitle="Forces the high-contrast theme variant.",
            active=is_high_contrast,
        )
        self.contrast.connect("notify::active", self._on_contrast_toggled)
        vision.add(self.contrast)

        # Magnifier.
        ok, mag = _gsettings("get",
                              "org.gnome.desktop.a11y.applications",
                              "screen-magnifier-enabled")
        self.mag = Adw.SwitchRow(
            title="Screen magnifier",
            subtitle="Toggle with Super + Plus once enabled.",
            active="true" in (mag or "").lower(),
        )
        self.mag.connect("notify::active", self._on_mag_toggled)
        vision.add(self.mag)
        page.add(vision)

        # ── Hearing / motor placeholders (ship-ready stubs) ─────────
        hm = Adw.PreferencesGroup(
            title="Hearing & motor",
            description="Sticky keys + visual bell are managed via Hyprland.",
        )
        hm.add(Adw.ActionRow(
            title="Sticky keys",
            subtitle="Configure via Settings → Keyboard → Modifiers.",
        ))
        hm.add(Adw.ActionRow(
            title="Visual bell",
            subtitle="Edit ~/.config/hypr/hyprland.conf → general.flash.",
        ))
        page.add(hm)

        # ── Orca screen reader ──────────────────────────────────────
        orca = Adw.PreferencesGroup(
            title="Screen reader (Orca)",
            description=(
                "Choose an Orca profile. The `default` profile keeps "
                "speech off; `low-vision` enables magnifier + speech; "
                "`screen-reader` enables full speech, key-echo, braille."
            ),
        )
        doc = _read_orca()
        active = str(doc.get("activeProfile", "default"))
        self.profile_combo = Adw.ComboRow(title="Active profile")
        model = Gtk.StringList.new(PROFILES)
        self.profile_combo.set_model(model)
        try:
            self.profile_combo.set_selected(PROFILES.index(active))
        except ValueError:
            self.profile_combo.set_selected(0)
        self.profile_combo.connect("notify::selected", self._on_profile_change)
        orca.add(self.profile_combo)
        page.add(orca)

        # status banner
        self.banner = Gtk.Label(label="", xalign=0)
        self.banner.add_css_class("dim-label")
        self.append(self.banner)

    # ── handlers ────────────────────────────────────────────────────
    def _on_contrast_toggled(self, sw: Adw.SwitchRow, *_: object) -> None:
        ok, msg = _gsettings(
            "set", "org.gnome.desktop.a11y.interface", "high-contrast",
            "true" if sw.get_active() else "false",
        )
        self._flash(
            "Updated high-contrast theme." if ok else f"Failed: {msg}", ok,
        )

    def _on_mag_toggled(self, sw: Adw.SwitchRow, *_: object) -> None:
        ok, msg = _gsettings(
            "set", "org.gnome.desktop.a11y.applications",
            "screen-magnifier-enabled",
            "true" if sw.get_active() else "false",
        )
        self._flash("Magnifier updated." if ok else f"Failed: {msg}", ok)

    def _on_profile_change(self, combo: Adw.ComboRow, *_: object) -> None:
        idx = combo.get_selected()
        if idx < 0 or idx >= len(PROFILES):
            return
        doc = _read_orca()
        doc["activeProfile"] = PROFILES[idx]
        try:
            _write_orca(doc)
            self._flash(f"Orca profile → {PROFILES[idx]}.", True)
        except Exception as exc:  # pragma: no cover
            self._flash(f"Could not write orca config: {exc}", False)

    def _flash(self, msg: str, success: bool) -> None:
        self.banner.set_label(msg)
        css = "success" if success else "error"
        self.banner.add_css_class(css)
        def _clear() -> bool:
            self.banner.remove_css_class(css)
            return False
        GLib.timeout_add_seconds(3, _clear)


def main() -> int:
    app = Adw.Application(application_id="com.nyxus.accessibility")
    def on_activate(_a: Adw.Application) -> None:
        win = Adw.ApplicationWindow(application=_a,
                                    title="NYXUS · Accessibility")
        win.set_default_size(720, 600)
        win.set_content(A11yPanel())
        win.present()
    app.connect("activate", on_activate)
    return app.run(None)


if __name__ == "__main__":
    raise SystemExit(main())
