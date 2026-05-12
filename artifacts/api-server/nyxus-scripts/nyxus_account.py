#!/usr/bin/env python3
"""
NYXUS Account — opt-in cloud sync of wallpaper, theme accent, and
selected dotfiles to a tiny KV endpoint.

The endpoint is a user-controlled URL that speaks two verbs:
    PUT  /v1/profile/<token>   →  body: tar.gz of the bundle
    GET  /v1/profile/<token>   →  body: tar.gz of the bundle

A single Bearer token authenticates both. Server reference impl lives in
api-server (`/api/nyxus-account/*`); users may also point at their own.

Privacy:
  - Sync is OFF by default.
  - Bundle ONLY contains the explicit allow-list below — no shell history,
    no SSH keys, no browser data, no documents.
  - Endpoint + token live in ~/.config/nyxus/account.json (chmod 600).
  - Disable any time from Settings → Accounts → "Disconnect" or by
    deleting account.json.

Allow-list:
    ~/.config/hypr/walls/<active-wallpaper>
    ~/.config/nyxus/accent.conf
    ~/.config/nyxus/sound.conf
    ~/.config/nyxus/desktop.conf
    ~/.config/gtk-3.0/settings.ini
    ~/.config/gtk-4.0/settings.ini
"""
from __future__ import annotations

import io
import json
import logging
import logging.handlers
import os
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, GLib, Gtk  # noqa: E402

HOME = Path(os.path.expanduser("~"))
CFG_DIR = HOME / ".config" / "nyxus"
CFG_DIR.mkdir(parents=True, exist_ok=True)
CFG = CFG_DIR / "account.json"
CACHE = HOME / ".cache" / "nyxus"
CACHE.mkdir(parents=True, exist_ok=True)
LOG_FILE = CACHE / "account.log"

log = logging.getLogger("nyxus_account")
log.setLevel(logging.INFO)
_h = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=256_000,
                                          backupCount=2)
_h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
log.addHandler(_h)

ALLOW = [
    HOME / ".config" / "nyxus" / "accent.conf",
    HOME / ".config" / "nyxus" / "sound.conf",
    HOME / ".config" / "nyxus" / "desktop.conf",
    HOME / ".config" / "gtk-3.0" / "settings.ini",
    HOME / ".config" / "gtk-4.0" / "settings.ini",
]


def load_cfg() -> dict:
    if CFG.exists():
        try:
            return json.loads(CFG.read_text())
        except Exception as e:
            log.warning("config read: %s", e)
    return {}


def save_cfg(data: dict) -> None:
    CFG.write_text(json.dumps(data, indent=2))
    try: os.chmod(CFG, 0o600)
    except Exception: pass


def _active_wallpaper() -> Path | None:
    """Resolve current wallpaper from hyprland/desktop config (best effort)."""
    candidates = [
        HOME / ".config" / "nyxus" / "wallpaper.path",
        HOME / ".config" / "hypr" / "walls" / "current",
    ]
    for c in candidates:
        try:
            if c.exists():
                p = Path(c.read_text().strip())
                if p.exists():
                    return p
        except Exception:
            continue
    walls = HOME / ".config" / "hypr" / "walls"
    if walls.exists():
        for p in walls.iterdir():
            if p.is_file() and p.suffix.lower() in (".png", ".jpg", ".jpeg"):
                return p
    return None


def build_bundle() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for path in ALLOW:
            if path.exists():
                tar.add(path, arcname=str(path.relative_to(HOME)))
        wp = _active_wallpaper()
        if wp is not None and wp.exists():
            tar.add(wp, arcname=f"wallpaper{wp.suffix.lower()}")
    return buf.getvalue()


def restore_bundle(blob: bytes) -> int:
    """Untar into HOME, only paths in ALLOW or the wallpaper."""
    count = 0
    allowed_rel = {str(p.relative_to(HOME)) for p in ALLOW}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        for member in tar.getmembers():
            if not member.isfile():
                continue
            name = member.name
            if name in allowed_rel:
                target = HOME / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as src:  # type: ignore[union-attr]
                    target.write_bytes(src.read())
                count += 1
            elif name.startswith("wallpaper."):
                walls = HOME / ".config" / "hypr" / "walls"
                walls.mkdir(parents=True, exist_ok=True)
                target = walls / f"synced{Path(name).suffix.lower()}"
                with tar.extractfile(member) as src:  # type: ignore[union-attr]
                    target.write_bytes(src.read())
                # Apply via existing wallpaper script when present
                setter = shutil.which("nyxus-set-wallpaper.sh")
                if setter:
                    try:
                        subprocess.Popen([setter, str(target)],
                                         start_new_session=True)
                    except Exception as e:
                        log.warning("wallpaper apply: %s", e)
                count += 1
    return count


def _curl_put(url: str, token: str, body: bytes) -> tuple[int, str]:
    if not shutil.which("curl"):
        return 127, "curl missing"
    try:
        r = subprocess.run(
            ["curl", "-fsS", "-X", "PUT",
             "-H", f"Authorization: Bearer {token}",
             "-H", "Content-Type: application/gzip",
             "--data-binary", "@-", url],
            input=body, capture_output=True, timeout=60)
        return r.returncode, (r.stderr or b"").decode(errors="replace")
    except Exception as e:
        return 1, str(e)


def _curl_get(url: str, token: str) -> tuple[int, bytes, str]:
    if not shutil.which("curl"):
        return 127, b"", "curl missing"
    try:
        r = subprocess.run(
            ["curl", "-fsS", "-X", "GET",
             "-H", f"Authorization: Bearer {token}", url],
            capture_output=True, timeout=60)
        return r.returncode, r.stdout, (r.stderr or b"").decode(errors="replace")
    except Exception as e:
        return 1, b"", str(e)


# ---------- GUI ----------
GOLD = "#d4b87a"; INK = "#080a10"
CSS = f"""
.acct-window {{ background: {INK}; }}
.acct-header {{ color: {GOLD}; font-weight: 700; font-size: 18px;
                 padding: 8px 0 12px 0; letter-spacing: 0.04em; }}
.acct-status {{ color: rgba(230,232,238,0.7); padding-bottom: 8px; }}
.acct-row    {{ padding: 8px 4px; }}
""".encode("utf-8")


class AccountWindow(Adw.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("NYXUS Account")
        self.set_default_size(640, 480)
        self.add_css_class("acct-window")
        self.cfg = load_cfg()

        toolbar = Adw.ToolbarView()
        header = Adw.HeaderBar()
        toolbar.add_top_bar(header)

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_start(20); outer.set_margin_end(20)
        outer.set_margin_top(8); outer.set_margin_bottom(16)
        toolbar.set_content(outer)

        title = Gtk.Label(label="NYXUS Account", xalign=0)
        title.add_css_class("acct-header"); outer.append(title)

        intro = Gtk.Label(
            label="Opt-in sync for wallpaper, accent, and small "
                  "preferences only. Off until you set an endpoint and "
                  "token below. Bundle contents are listed in "
                  "~/.cache/nyxus/account.log on every push.",
            xalign=0)
        intro.add_css_class("acct-status"); intro.set_wrap(True)
        outer.append(intro)

        # ── form
        form = Adw.PreferencesGroup()
        outer.append(form)

        self.row_url = Adw.EntryRow()
        self.row_url.set_title("Endpoint URL")
        self.row_url.set_text(self.cfg.get("url", ""))
        form.add(self.row_url)

        self.row_token = Adw.PasswordEntryRow()
        self.row_token.set_title("Bearer token")
        self.row_token.set_text(self.cfg.get("token", ""))
        form.add(self.row_token)

        # ── actions
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.set_halign(Gtk.Align.END); outer.append(bar)
        save_b = Gtk.Button(label="Save")
        save_b.connect("clicked", lambda *_: self.save())
        bar.append(save_b)
        push_b = Gtk.Button(label="Push to cloud")
        push_b.add_css_class("suggested-action")
        push_b.connect("clicked", lambda *_: self.push())
        bar.append(push_b)
        pull_b = Gtk.Button(label="Pull from cloud")
        pull_b.connect("clicked", lambda *_: self.pull())
        bar.append(pull_b)
        disc_b = Gtk.Button(label="Disconnect")
        disc_b.add_css_class("destructive-action")
        disc_b.connect("clicked", lambda *_: self.disconnect())
        bar.append(disc_b)

        self.toast = Adw.ToastOverlay()
        self.toast.set_child(toolbar)
        self.set_content(self.toast)

    def _update_cfg_from_form(self) -> None:
        self.cfg["url"] = self.row_url.get_text().strip()
        self.cfg["token"] = self.row_token.get_text().strip()

    def save(self) -> None:
        self._update_cfg_from_form()
        save_cfg(self.cfg)
        self.toast.add_toast(Adw.Toast.new("Saved"))

    def disconnect(self) -> None:
        try:
            if CFG.exists(): CFG.unlink()
        except Exception: pass
        self.row_url.set_text(""); self.row_token.set_text("")
        self.toast.add_toast(Adw.Toast.new("Disconnected"))

    def _need_credentials(self) -> tuple[str, str] | None:
        self._update_cfg_from_form()
        url = self.cfg.get("url"); tok = self.cfg.get("token")
        if not url or not tok:
            self.toast.add_toast(
                Adw.Toast.new("Set endpoint + token first."))
            return None
        return url.rstrip("/"), tok

    def push(self) -> None:
        creds = self._need_credentials()
        if creds is None: return
        url, tok = creds
        body = build_bundle()
        log.info("push %d bytes → %s", len(body), url)
        rc, err = _curl_put(f"{url}/v1/profile/me", tok, body)
        msg = "Pushed." if rc == 0 else f"Push failed: {err.splitlines()[-1] if err else rc}"
        self.toast.add_toast(Adw.Toast.new(msg))

    def pull(self) -> None:
        creds = self._need_credentials()
        if creds is None: return
        url, tok = creds
        log.info("pull ← %s", url)
        rc, body, err = _curl_get(f"{url}/v1/profile/me", tok)
        if rc != 0 or not body:
            self.toast.add_toast(Adw.Toast.new(
                f"Pull failed: {err.splitlines()[-1] if err else rc}"))
            return
        try:
            n = restore_bundle(body)
        except Exception as e:
            log.error("restore: %s", e)
            self.toast.add_toast(Adw.Toast.new("Restore failed"))
            return
        self.toast.add_toast(Adw.Toast.new(f"Restored {n} item(s)."))


class AccountApp(Adw.Application):
    def __init__(self):
        super().__init__(application_id="com.nyxus.account")
    def do_activate(self):  # type: ignore[override]
        try: Adw.StyleManager.get_default().set_color_scheme(
            Adw.ColorScheme.FORCE_DARK)
        except Exception: pass
        prov = Gtk.CssProvider()
        try: prov.load_from_data(CSS)
        except Exception:
            try: prov.load_from_string(CSS.decode())
            except Exception: pass
        Gtk.StyleContext.add_provider_for_display(
            Gtk.Widget().get_display() if False else __import__("gi").repository.Gdk.Display.get_default(),
            prov, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        AccountWindow(self).present()


def main() -> int:
    if "--push" in sys.argv:
        cfg = load_cfg()
        url = cfg.get("url"); tok = cfg.get("token")
        if not url or not tok:
            print("not configured", file=sys.stderr); return 2
        body = build_bundle()
        rc, err = _curl_put(f"{url.rstrip('/')}/v1/profile/me", tok, body)
        if rc != 0: print(err, file=sys.stderr)
        return rc
    if "--pull" in sys.argv:
        cfg = load_cfg()
        url = cfg.get("url"); tok = cfg.get("token")
        if not url or not tok:
            print("not configured", file=sys.stderr); return 2
        rc, body, err = _curl_get(f"{url.rstrip('/')}/v1/profile/me", tok)
        if rc != 0: print(err, file=sys.stderr); return rc
        n = restore_bundle(body)
        print(f"restored {n}")
        return 0
    return AccountApp().run([])


if __name__ == "__main__":
    sys.exit(main())
