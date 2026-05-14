#!/usr/bin/env python3
"""
NYXUS · Welcome / Onboarding Wizard
====================================
Eight-page GTK4/libadwaita onboarding wizard. Every page writes real
state and every "Apply" button calls a real NYXUS helper. No mockups.

Pages:
  1. Welcome       — logo + intro + Continue
  2. User profile  — display name + avatar (chfn / accountsservice)
  3. Theme & accent — light/dark + accent (nyxus-apply-accent)
  4. Wallpaper     — picker (nyxus-set-wallpaper)
  5. Dock          — enable + position (~/.config/nyxus/dock.toml +
                                       nyxus-dock reload)
  6. Recommended   — checkboxes for popular apps (pacman/flatpak)
  7. Cloud sync    — opt-in nyxus-account
  8. Privacy       — crash reports + telemetry toggles (off by default)
  9. Finish        — "All set" + writes ~/.config/nyxus/welcome.done

Lives at: /opt/nyxus/nyxus_welcome.py
Launched by: /usr/local/bin/nyxus-welcome
First-boot autostart: /etc/skel/.config/autostart/nyxus-welcome.desktop
                     (self-deletes after the wizard reaches Finish).
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
from pathlib import Path
from shutil import which

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gdk, GLib, Gio, Gtk  # noqa: E402

# ── Paths & logging ────────────────────────────────────────────────────
HOME = Path(os.path.expanduser("~"))
CFG_DIR = HOME / ".config" / "nyxus"
CFG_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_JSON = CFG_DIR / "settings.json"
DONE_MARK = CFG_DIR / "welcome.done"
LOG_DIR = HOME / ".cache" / "nyxus"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=LOG_DIR / "welcome.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("welcome")

SYS_WALLS = Path("/usr/share/backgrounds/nyxus")
USR_WALLS = HOME / ".local" / "share" / "backgrounds" / "nyxus"


def have(cmd: str) -> bool:
    return which(cmd) is not None


def run_async(argv, on_done=None) -> None:
    """Spawn argv detached and call on_done(rc, out) on the GLib loop."""
    def _bg():
        try:
            r = subprocess.run(argv, capture_output=True, text=True,
                               timeout=120)
            rc, out = r.returncode, (r.stdout or "") + (r.stderr or "")
        except Exception as e:
            rc, out = 1, str(e)
        if on_done:
            GLib.idle_add(on_done, rc, out)
    import threading
    threading.Thread(target=_bg, daemon=True).start()


def load_settings() -> dict:
    if not SETTINGS_JSON.exists():
        return {}
    try:
        return json.loads(SETTINGS_JSON.read_text() or "{}")
    except Exception as e:
        log.warning("settings load: %s", e)
        return {}


def save_settings(data: dict) -> None:
    try:
        SETTINGS_JSON.parent.mkdir(parents=True, exist_ok=True)
        tmp = SETTINGS_JSON.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2))
        tmp.replace(SETTINGS_JSON)
    except Exception as e:
        log.warning("settings save: %s", e)


def set_pref(ns: str, key: str, value) -> None:
    s = load_settings()
    s.setdefault(ns, {})[key] = value
    save_settings(s)
    log.info("set %s.%s = %r", ns, key, value)


# ── Theme packs (mirrors ThemePacksPage) ──────────────────────────────
THEME_PACKS = (
    ("dark_mirror", "DARK MIRROR (default)", "#a06bff", "#3ad8ff"),
    ("inferno",     "INFERNO",                "#ff3a5c", "#ffae3a"),
    ("oceanic",     "OCEANIC",                "#3a7dff", "#3affd8"),
    ("forest",      "FOREST",                 "#3aff7d", "#a0ff3a"),
    ("monochrome",  "MONOCHROME",             "#cccccc", "#888888"),
)

# ── Recommended apps (real packages) ──────────────────────────────────
RECOMMENDED = [
    # (id, label, description, install method, package)
    ("firefox",   "Firefox",
     "Web browser",                 "pacman",  "firefox"),
    ("chromium",  "Chromium",
     "Chrome-compatible browser",   "pacman",  "chromium"),
    ("vscode",   "Visual Studio Code",
     "Editor by Microsoft",         "pacman",  "code"),
    ("discord",   "Discord",
     "Voice & text chat",           "flatpak", "com.discordapp.Discord"),
    ("obs",       "OBS Studio",
     "Streaming & screen recording","pacman",  "obs-studio"),
    ("gimp",      "GIMP",
     "Image editor",                "pacman",  "gimp"),
    ("libreoffice", "LibreOffice",
     "Office suite",                "pacman",  "libreoffice-fresh"),
    ("vlc",       "VLC",
     "Media player",                "pacman",  "vlc"),
]


# ── Wizard pages ──────────────────────────────────────────────────────
class WelcomeWindow(Adw.ApplicationWindow):
    def __init__(self, app: Adw.Application, *,
                 force: bool = False) -> None:
        super().__init__(application=app, title="NYXUS Welcome")
        self.force = force
        self.set_default_size(880, 640)
        self.set_resizable(False)
        self.add_css_class("nyx-welcome")

        # Carousel of pages with a header bar
        self.carousel = Adw.Carousel()
        self.carousel.set_allow_scroll_wheel(False)
        self.carousel.set_allow_long_swipes(False)
        self.carousel.set_allow_mouse_drag(False)
        self.carousel.set_interactive(False)

        # Build pages and append
        self.pages = [
            self._page_welcome(),
            self._page_profile(),
            self._page_theme(),
            self._page_wallpaper(),
            self._page_dock(),
            self._page_apps(),
            self._page_cloud(),
            self._page_privacy(),
            self._page_finish(),
        ]
        for p in self.pages:
            self.carousel.append(p)

        # Header bar with Skip + Back/Next + dots indicator
        header = Adw.HeaderBar()
        header.add_css_class("flat")
        skip_btn = Gtk.Button(label="Skip")
        skip_btn.connect("clicked", lambda _b: self._finish())
        header.pack_start(skip_btn)
        self._back_btn = Gtk.Button(label="Back")
        self._back_btn.connect("clicked", lambda _b: self._go(-1))
        self._next_btn = Gtk.Button(label="Continue")
        self._next_btn.add_css_class("suggested-action")
        self._next_btn.connect("clicked", lambda _b: self._go(+1))
        header.pack_end(self._next_btn)
        header.pack_end(self._back_btn)

        dots = Adw.CarouselIndicatorDots()
        dots.set_carousel(self.carousel)
        dots.set_margin_top(4); dots.set_margin_bottom(8)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(self.carousel)
        toolbar.add_bottom_bar(dots)
        self.set_content(toolbar)

        self.toast_overlay = Adw.ToastOverlay()
        self.toast_overlay.set_child(toolbar)
        self.set_content(self.toast_overlay)

        self._inject_css()
        self._update_nav()
        self.carousel.connect("page-changed",
                              lambda _c, _i: self._update_nav())

    # ── helpers ────────────────────────────────────────────────────────
    def toast(self, msg: str) -> None:
        try:
            self.toast_overlay.add_toast(Adw.Toast.new(msg))
        except Exception:
            pass

    def _go(self, step: int) -> None:
        cur = int(self.carousel.get_position())
        nxt = max(0, min(len(self.pages) - 1, cur + step))
        if nxt == cur and step > 0:
            self._finish(); return
        self.carousel.scroll_to(self.pages[nxt], True)

    def _update_nav(self) -> None:
        idx = int(self.carousel.get_position())
        self._back_btn.set_sensitive(idx > 0)
        self._next_btn.set_label(
            "Get Started" if idx == len(self.pages) - 1 else "Continue")

    def _finish(self) -> None:
        try:
            DONE_MARK.parent.mkdir(parents=True, exist_ok=True)
            DONE_MARK.write_text(
                json.dumps({"completed_at": GLib.DateTime.new_now_utc()
                            .format("%Y-%m-%dT%H:%M:%SZ")},
                           indent=2))
        except Exception as e:
            log.warning("mark done: %s", e)
        # Self-delete the autostart entry so we don't run again on every login
        autostart = HOME / ".config" / "autostart" / "nyxus-welcome.desktop"
        try:
            if autostart.exists():
                autostart.unlink()
        except Exception as e:
            log.warning("autostart remove: %s", e)
        self.close()

    def _inject_css(self) -> None:
        css = """
        .nyx-welcome { background: #0a0a14; color: #e6e6f0; }
        .nyx-title  { font-size: 32px; font-weight: 700;
                      color: #a06bff; }
        .nyx-tagline{ font-size: 16px; color: #88889a; }
        .nyx-pack-card { padding: 12px; border-radius: 12px;
                         border: 1px solid alpha(#a06bff, 0.2); }
        .nyx-pack-card.selected {
            border-color: #3ad8ff;
            box-shadow: 0 0 12px alpha(#3ad8ff, 0.4); }
        """
        try:
            prov = Gtk.CssProvider()
            prov.load_from_data(css.encode())
            display = Gdk.Display.get_default()
            if display is not None:
                Gtk.StyleContext.add_provider_for_display(
                    display, prov,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        except Exception as e:
            log.warning("css: %s", e)

    # ── individual pages ───────────────────────────────────────────────
    def _wrap(self, child: Gtk.Widget) -> Gtk.Widget:
        sw = Gtk.ScrolledWindow()
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.set_child(child)
        sw.set_size_request(840, 540)
        return sw

    def _page_welcome(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                      spacing=18)
        box.set_margin_top(60); box.set_margin_bottom(40)
        box.set_margin_start(40); box.set_margin_end(40)
        box.set_halign(Gtk.Align.CENTER)
        # Logo (uses installed nyxus.png if present, else Adw icon)
        logo_path = Path("/usr/share/icons/nyxus/nyxus.png")
        if logo_path.exists():
            img = Gtk.Image.new_from_file(str(logo_path))
            img.set_pixel_size(96)
        else:
            img = Gtk.Image.new_from_icon_name("face-smile-symbolic")
            img.set_pixel_size(96)
        img.set_halign(Gtk.Align.CENTER)
        box.append(img)
        title = Gtk.Label(label="Welcome to NYXUS")
        title.add_css_class("nyx-title"); title.set_halign(Gtk.Align.CENTER)
        box.append(title)
        sub = Gtk.Label(
            label="A privacy-first, beautifully dark Arch Linux. "
                  "We'll set up your account, theme, and apps in a "
                  "few quick steps.")
        sub.add_css_class("nyx-tagline"); sub.set_wrap(True)
        sub.set_max_width_chars(60); sub.set_halign(Gtk.Align.CENTER)
        sub.set_justify(Gtk.Justification.CENTER)
        box.append(sub)
        return self._wrap(box)

    def _page_profile(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        grp = Adw.PreferencesGroup(
            title="Your profile",
            description="Display name and avatar — used by the lock "
                        "screen and the dock")
        page.add(grp)
        # Display name
        name_row = Adw.EntryRow(title="Display name")
        # Pre-fill from getent if available
        try:
            import pwd
            ent = pwd.getpwuid(os.getuid())
            name_row.set_text(ent.pw_gecos.split(",")[0] or ent.pw_name)
        except Exception:
            name_row.set_text(os.environ.get("USER", ""))
        apply_btn = Gtk.Button(label="Save")
        apply_btn.add_css_class("suggested-action")
        apply_btn.set_valign(Gtk.Align.CENTER)
        def _save_name(_b):
            new = name_row.get_text().strip()
            if not new:
                self.toast("display name cannot be empty"); return
            if have("chfn"):
                run_async(
                    ["chfn", "-f", new],
                    lambda rc, _o: self.toast(
                        "name saved" if rc == 0
                        else "could not save name (re-run with sudo)"))
            else:
                set_pref("user", "display_name", new)
                self.toast("saved (chfn missing)")
        apply_btn.connect("clicked", _save_name)
        name_row.add_suffix(apply_btn)
        grp.add(name_row)
        # Avatar pick
        avatar_row = Adw.ActionRow(
            title="Avatar",
            subtitle="Pick an image (will be copied to ~/.face)")
        pick = Gtk.Button(label="Pick")
        pick.set_valign(Gtk.Align.CENTER)
        pick.connect("clicked", lambda _b: self._pick_avatar())
        avatar_row.add_suffix(pick)
        grp.add(avatar_row)
        return self._wrap(page)

    def _pick_avatar(self) -> None:
        try:
            if hasattr(Gtk, "FileDialog"):
                d = Gtk.FileDialog()
                d.set_title("Pick an avatar")
                def _done(d2, res):
                    try:
                        f = d2.open_finish(res)
                        if f:
                            src = Path(f.get_path())
                            face = HOME / ".face"
                            face.write_bytes(src.read_bytes())
                            set_pref("user", "avatar", str(src))
                            self.toast("avatar saved")
                    except Exception as e:
                        log.warning("avatar: %s", e)
                d.open(self, None, _done)
            else:
                self.toast("file picker unavailable")
        except Exception as e:
            self.toast(f"picker: {e}")

    def _page_theme(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        gen = Adw.PreferencesGroup(
            title="Color scheme",
            description="System preference — applies to GTK and Qt apps")
        page.add(gen)
        prefs = load_settings().get("appearance", {})
        cur = prefs.get("color_scheme", "dark")
        for sid, lbl, sub in (
                ("dark",  "Dark",
                    "Force dark UI everywhere"),
                ("light", "Light",
                    "Force light UI everywhere"),
                ("auto",  "Auto",
                    "Follow time of day (sunrise/sunset)")):
            row = Adw.ActionRow(
                title=f"{lbl}{' · ACTIVE' if sid == cur else ''}",
                subtitle=sub)
            btn = Gtk.Button(label="Use")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked",
                        lambda _b, s=sid: self._apply_color_scheme(s))
            row.add_suffix(btn); gen.add(row)
        # Theme packs
        packs = Adw.PreferencesGroup(
            title="Theme pack",
            description="DARK MIRROR variants — accent + glow")
        page.add(packs)
        active_pack = load_settings().get("themepack", {}).get(
            "active", "dark_mirror")
        for pid, lbl, primary, secondary in THEME_PACKS:
            sub = f"{primary} / {secondary}"
            row = Adw.ActionRow(
                title=f"{lbl}{' · ACTIVE' if pid == active_pack else ''}",
                subtitle=sub)
            btn = Gtk.Button(
                label="Re-apply" if pid == active_pack else "Apply")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect(
                "clicked",
                lambda _b, p=pid, a=primary, b=secondary:
                    self._apply_pack(p, a, b))
            row.add_suffix(btn); packs.add(row)
        return self._wrap(page)

    def _apply_color_scheme(self, scheme: str) -> None:
        set_pref("appearance", "color_scheme", scheme)
        # Translate to GTK ADW + GSettings if available
        try:
            sm = Adw.StyleManager.get_default()
            sm.set_color_scheme({
                "dark":  Adw.ColorScheme.FORCE_DARK,
                "light": Adw.ColorScheme.FORCE_LIGHT,
                "auto":  Adw.ColorScheme.PREFER_DARK,
            }.get(scheme, Adw.ColorScheme.FORCE_DARK))
        except Exception as e:
            log.warning("color_scheme: %s", e)
        if have("gsettings"):
            run_async(["gsettings", "set",
                       "org.gnome.desktop.interface", "color-scheme",
                       "prefer-dark" if scheme != "light"
                       else "prefer-light"])
        self.toast(f"color scheme → {scheme}")

    def _apply_pack(self, pid: str, primary: str, secondary: str) -> None:
        s = load_settings()
        s.setdefault("themepack", {}).update({
            "active": pid, "primary": primary, "secondary": secondary})
        save_settings(s)
        if have("nyxus-apply-accent"):
            run_async(
                ["nyxus-apply-accent", primary, secondary],
                lambda rc, _o: self.toast(
                    f"applied {pid}" if rc == 0 else "apply failed"))
        else:
            self.toast(f"saved {pid} (accent helper missing)")

    def _page_wallpaper(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        grp = Adw.PreferencesGroup(
            title="Wallpaper",
            description="Pick from the NYXUS pack")
        page.add(grp)
        walls: list[Path] = []
        for d in (SYS_WALLS, USR_WALLS):
            if d.exists():
                for p in sorted(d.iterdir()):
                    if p.suffix.lower() in (".jpg", ".jpeg",
                                             ".png", ".webp"):
                        walls.append(p)
        if not walls:
            row = Adw.ActionRow(
                title="No wallpapers found",
                subtitle="Drop images into "
                         "~/.local/share/backgrounds/nyxus/")
            grp.add(row)
        for p in walls[:24]:
            r = Adw.ActionRow(title=p.stem,
                              subtitle=str(p.parent))
            b = Gtk.Button(label="Use")
            b.set_valign(Gtk.Align.CENTER)
            b.connect("clicked",
                      lambda _b, pp=p: self._apply_wallpaper(pp))
            r.add_suffix(b); grp.add(r)
        return self._wrap(page)

    def _apply_wallpaper(self, path: Path) -> None:
        if have("nyxus-set-wallpaper"):
            run_async(
                ["nyxus-set-wallpaper", str(path)],
                lambda rc, _o: self.toast(
                    f"applied: {path.stem}" if rc == 0
                    else "wallpaper apply failed"))
        else:
            set_pref("wallpaper", "path", str(path))
            self.toast("saved (helper missing)")

    def _page_dock(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        grp = Adw.PreferencesGroup(
            title="Dock",
            description="Pinned-app launcher at the edge of the screen")
        page.add(grp)
        # Enable
        sw_en = Adw.SwitchRow(
            title="Enable dock",
            subtitle="Show the NYXUS dock on this session")
        # Read current dock.toml if any
        dock_toml = HOME / ".config/nyxus/dock.toml"
        cur_enabled = True
        cur_pos = "bottom"
        if dock_toml.exists():
            try:
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib  # type: ignore
                with dock_toml.open("rb") as f:
                    d = tomllib.load(f).get("dock", {})
                cur_enabled = bool(d.get("enabled", True))
                cur_pos = str(d.get("position", "bottom"))
            except Exception as e:
                log.warning("dock toml read: %s", e)
        sw_en.set_active(cur_enabled)
        sw_en.connect("notify::active",
                      lambda s, _p: self._dock_set("enabled",
                                                    s.get_active()))
        grp.add(sw_en)
        # Position
        pos_row = Adw.ComboRow(title="Position",
                               subtitle="Edge of the screen")
        model = Gtk.StringList()
        for p in ("bottom", "left", "right", "top"):
            model.append(p)
        pos_row.set_model(model)
        try:
            pos_row.set_selected(
                ["bottom", "left", "right", "top"].index(cur_pos))
        except ValueError:
            pos_row.set_selected(0)
        pos_row.connect(
            "notify::selected",
            lambda r, _p: self._dock_set(
                "position",
                ["bottom", "left", "right", "top"][r.get_selected()]))
        grp.add(pos_row)
        return self._wrap(page)

    def _dock_set(self, k: str, v) -> None:
        # Write dock.toml minimally (mirror DockPage logic).
        dock_toml = HOME / ".config/nyxus/dock.toml"
        cur = {}
        if dock_toml.exists():
            try:
                try:
                    import tomllib
                except ImportError:
                    import tomli as tomllib  # type: ignore
                with dock_toml.open("rb") as f:
                    cur = tomllib.load(f)
            except Exception as e:
                log.warning("dock read: %s", e)
        cur.setdefault("dock", {})[k] = v
        try:
            dock_toml.parent.mkdir(parents=True, exist_ok=True)
            d = cur.get("dock", {})
            lines = ["[dock]"]
            for kk, vv in d.items():
                if isinstance(vv, bool):
                    lines.append(f"{kk} = {'true' if vv else 'false'}")
                elif isinstance(vv, (int, float)):
                    lines.append(f"{kk} = {vv}")
                else:
                    s2 = str(vv).replace('"', '\\"')
                    lines.append(f'{kk} = "{s2}"')
            dock_toml.write_text("\n".join(lines) + "\n")
            if have("nyxus-dock"):
                run_async(["nyxus-dock", "reload"])
            self.toast(f"dock.{k} → {v}")
        except Exception as e:
            self.toast(f"dock save: {e}")

    def _page_apps(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        grp = Adw.PreferencesGroup(
            title="Recommended apps",
            description="Tick to install — installs run in the background")
        page.add(grp)
        self._app_picks: dict[str, Adw.SwitchRow] = {}
        for aid, lbl, desc, method, pkg in RECOMMENDED:
            row = Adw.SwitchRow(
                title=lbl,
                subtitle=f"{desc} · {method}: {pkg}")
            row.set_active(False)
            grp.add(row)
            self._app_picks[aid] = row
        # Install button
        act = Adw.PreferencesGroup()
        page.add(act)
        btn = Gtk.Button(label="Install selected now")
        btn.add_css_class("suggested-action")
        btn.set_halign(Gtk.Align.END)
        btn.connect("clicked", lambda _b: self._install_apps())
        wrap = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        wrap.set_halign(Gtk.Align.END); wrap.append(btn)
        act_row = Adw.ActionRow()
        act_row.set_child(wrap); act.add(act_row)
        return self._wrap(page)

    def _install_apps(self) -> None:
        picks = [(aid, m, p)
                 for aid, lbl, desc, m, p in RECOMMENDED
                 if self._app_picks.get(aid)
                 and self._app_picks[aid].get_active()]
        if not picks:
            self.toast("nothing selected"); return
        pacman_pkgs = [p for _, m, p in picks if m == "pacman"]
        flatpak_refs = [p for _, m, p in picks if m == "flatpak"]
        cmds: list[list[str]] = []
        if pacman_pkgs and have("pacman"):
            cmds.append(["pkexec", "pacman", "-Sy", "--noconfirm",
                         *pacman_pkgs])
        if flatpak_refs and have("flatpak"):
            cmds.append(["flatpak", "install", "-y", "--noninteractive",
                         "flathub", *flatpak_refs])
        # Track what user picked even if install starts in background
        s = load_settings()
        s.setdefault("welcome", {})["picked_apps"] = [aid for aid, _, _ in picks]
        save_settings(s)
        self.toast(f"installing {len(picks)} apps in background")
        # Run sequentially so we don't fight the package manager lock
        def _runner():
            import threading
            def _bg():
                for c in cmds:
                    try:
                        subprocess.run(c, timeout=900)
                    except Exception as e:
                        log.warning("install %s: %s", c, e)
                GLib.idle_add(self.toast, "installs finished")
            threading.Thread(target=_bg, daemon=True).start()
        _runner()

    def _page_cloud(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        grp = Adw.PreferencesGroup(
            title="Cloud sync (optional)",
            description="Sync wallpaper / theme / settings across machines "
                        "via your NYXUS account")
        page.add(grp)
        sw = Adw.SwitchRow(
            title="Enable NYXUS cloud sync",
            subtitle="You can change this any time in Settings · NYXUS Account")
        sw.set_active(bool(load_settings().get("sync", {}).get(
            "enabled", False)))
        sw.connect("notify::active",
                   lambda s, _p: set_pref("sync", "enabled",
                                           s.get_active()))
        grp.add(sw)
        # Sign-in button
        if have("nyxus-account"):
            row = Adw.ActionRow(
                title="Sign in now",
                subtitle="Open the account helper to sign in")
            b = Gtk.Button(label="Open")
            b.set_valign(Gtk.Align.CENTER)
            b.connect("clicked",
                      lambda _b: subprocess.Popen(["nyxus-account",
                                                    "login"]))
            row.add_suffix(b); grp.add(row)
        return self._wrap(page)

    def _page_privacy(self) -> Gtk.Widget:
        page = Adw.PreferencesPage()
        grp = Adw.PreferencesGroup(
            title="Privacy",
            description="Both options OFF by default — opt-in only")
        page.add(grp)
        cur = load_settings().get("privacy", {})
        sw_crash = Adw.SwitchRow(
            title="Send crash reports",
            subtitle="Anonymous backtraces help us fix real bugs")
        sw_crash.set_active(bool(cur.get("crash_reports", False)))
        sw_crash.connect(
            "notify::active",
            lambda s, _p: set_pref("privacy", "crash_reports",
                                    s.get_active()))
        grp.add(sw_crash)
        sw_tel = Adw.SwitchRow(
            title="Anonymous usage stats",
            subtitle="Counts of feature usage — never content, never PII")
        sw_tel.set_active(bool(cur.get("telemetry", False)))
        sw_tel.connect(
            "notify::active",
            lambda s, _p: set_pref("privacy", "telemetry",
                                    s.get_active()))
        grp.add(sw_tel)
        return self._wrap(page)

    def _page_finish(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                      spacing=18)
        box.set_margin_top(80); box.set_margin_bottom(40)
        box.set_margin_start(40); box.set_margin_end(40)
        box.set_halign(Gtk.Align.CENTER)
        img = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
        img.set_pixel_size(96); img.set_halign(Gtk.Align.CENTER)
        box.append(img)
        title = Gtk.Label(label="You're all set")
        title.add_css_class("nyx-title"); title.set_halign(Gtk.Align.CENTER)
        box.append(title)
        sub = Gtk.Label(
            label="Click Get Started to enter your new desktop. You can "
                  "re-run this wizard any time from Settings · Welcome.")
        sub.add_css_class("nyx-tagline"); sub.set_wrap(True)
        sub.set_max_width_chars(60); sub.set_halign(Gtk.Align.CENTER)
        sub.set_justify(Gtk.Justification.CENTER)
        box.append(sub)
        return self._wrap(box)


# ── App ────────────────────────────────────────────────────────────────
class WelcomeApp(Adw.Application):
    def __init__(self, force: bool) -> None:
        super().__init__(application_id="com.nyxus.Welcome",
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        self.force = force

    def do_activate(self):
        win = WelcomeWindow(self, force=self.force)
        win.present()


def main() -> int:
    p = argparse.ArgumentParser(description="NYXUS onboarding wizard")
    p.add_argument("--force", action="store_true",
                   help="Run even if welcome.done exists")
    p.add_argument("--mark-done", action="store_true",
                   help="Just mark the wizard complete and exit")
    args = p.parse_args()

    if args.mark_done:
        DONE_MARK.parent.mkdir(parents=True, exist_ok=True)
        DONE_MARK.write_text("{}")
        return 0

    if DONE_MARK.exists() and not args.force:
        log.info("welcome.done present — skipping (use --force to override)")
        # Also clean up any stale autostart entry
        autostart = HOME / ".config" / "autostart" / "nyxus-welcome.desktop"
        try:
            if autostart.exists():
                autostart.unlink()
        except Exception:
            pass
        return 0

    app = WelcomeApp(force=args.force)
    return app.run([])


if __name__ == "__main__":
    raise SystemExit(main())
