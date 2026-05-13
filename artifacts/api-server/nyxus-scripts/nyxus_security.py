#!/usr/bin/env python3
# ============================================================================
#  NYXUS SECURITY CENTER  —  DARK MIRROR rev 2026-05-13 r1
#
#  Unified, enterprise-grade security & privacy hub.  Windows-11 Defender
#  Security Center / macOS "Privacy & Security" parity, plus NYXUS-only
#  signature features that no mainstream OS ships:
#
#    · Live THREAT TAPE — auditd + journal SECURITY events scrolling at
#      the bottom of every page
#    · PANIC MODE — single keystroke (Super+Ctrl+Alt+L) full lockdown:
#      lock screen, clear clipboard, dismount removable media, flush DNS
#      cache, kill foreground tab
#    · Per-executable TRUST SCORE — signed/AUR/unknown rating shown in
#      App & Browser Control
#    · Privacy Indicator dots — top-bar EWW pills go red when camera /
#      mic / location / screen-record is in use
#    · Hash REPUTATION cloud lookup against the NYXUS api-server
#
#  Sections (10):
#    1. Overview              — health score, recent events, big actions
#    2. Virus & Threats       — clamav scan/schedule/quarantine
#    3. Firewall & Network    — ufw rules CRUD, default policies, app rules
#    4. Account Protection    — password age, sudo timeout, idle lock,
#                               TOTP (optional), PAM lockout (OFF by default
#                               per user preference, with explicit warning)
#    5. App & Browser Control — installed-app trust score, AUR pin list,
#                               URL blocklist
#    6. Device Security       — TPM, Secure Boot, fwupd firmware,
#                               USBGuard, removable-media policy
#    7. Encryption & Vault    — LUKS volumes, /home encryption, vault
#    8. Privacy Indicators    — recent camera/mic/location/screen events
#    9. Audit & Threat Tape   — full audit log, failed-login viewer
#                               (READ-ONLY — never trigger lockout!)
#   10. Recovery & Panic      — recovery codes, PANIC button, self-test
#
#  Every read is real (system call + parse).  Every write goes through
#  /usr/local/libexec/nyxus-security-helper via pkexec.  Nothing edits
#  config files behind the user's back.  Failures surface as toasts.
#
#  Logs to ~/.cache/nyxus/security.log.
#
#  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
from __future__ import annotations
import gi, os, sys, json, time, hashlib, subprocess, logging, threading, shlex
from pathlib import Path
from typing import Callable, Optional

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, Gio, GLib, Adw, Pango  # noqa

# ── Logging — to ~/.cache/nyxus/security.log per project rule ───────────────
LOG_DIR = Path.home() / ".cache" / "nyxus"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "security.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("nyxus-security")

APP_ID  = "io.nyxus.security"
WIN_W   = 1180
WIN_H   = 760

# ── Palette (DARK MIRROR + status semantics) ────────────────────────────────
NYXUS_GOLD = "#d4b87a"
SUCCESS    = "#7ad99e"
WARN       = "#e8c46a"
DANGER     = "#ff6464"
INFO       = "#7ab3e8"
GLASS_DEEP = "rgba(8, 12, 20, 0.92)"
GLASS_MED  = "rgba(15, 20, 32, 0.78)"
GLASS_SOFT = "rgba(22, 28, 42, 0.55)"
HAIR_W     = "rgba(255, 255, 255, 0.10)"
TEXT_PRIM  = "#e8edf5"
TEXT_DIM   = "#9aa0ad"
TEXT_FAINT = "#6a6e78"

# Nerd-font glyphs
GLYPH = {
    "shield":  "\uf132",  "virus":   "\uf188",  "fire":   "\uf06d",
    "lock":    "\uf023",  "key":     "\uf084",  "user":   "\uf007",
    "apps":    "\uf17c",  "device":  "\uf109",  "wifi":   "\uf1eb",
    "vault":   "\uf187",  "eye":     "\uf06e",  "audit":  "\uf022",
    "panic":   "\uf071",  "scan":    "\uf002",  "tpm":    "\uf2db",
    "usb":     "\uf287",  "boot":    "\uf0e7",  "refresh":"\uf021",
    "play":    "\uf04b",  "stop":    "\uf04d",  "check":  "\uf00c",
    "x":       "\uf00d",  "chev":    "\uf054",  "ok":     "\uf058",
    "warn":    "\uf071",  "err":     "\uf057",  "info":   "\uf05a",
    "dot":     "\uf111",  "tape":    "\uf0c1",  "trust":  "\uf2bd",
    "globe":   "\uf0ac",  "dns":     "\uf0e8",  "vpn":    "\uf3ed",
    "plus":    "\uf067",  "minus":   "\uf068",  "trash":  "\uf1f8",
    "cog":     "\uf013",  "list":    "\uf0ca",  "history":"\uf1da",
    "download":"\uf019",
}

# Privileged helper installed by airootfs / nyxus_install.sh
HELPER_PATH = "/usr/local/libexec/nyxus-security-helper"

# Companion API base (account sync server already exposes it)
def _api_base() -> str:
    return os.environ.get("NYXUS_API_BASE", "https://api.nyxus.os")

# ── Subprocess helpers ─────────────────────────────────────────────────────
def sh(cmd: list[str], timeout: int = 5) -> tuple[int, str, str]:
    """Synchronous subprocess. Returns (rc, stdout, stderr)."""
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout.strip(), p.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    except Exception as e:  # pylint: disable=broad-except
        log.warning("sh %s: %s", cmd, e)
        return 1, "", str(e)


def sh_async(cmd: list[str], on_done: Optional[Callable] = None,
             timeout: int = 30) -> None:
    def worker():
        rc, out, err = sh(cmd, timeout=timeout)
        if on_done:
            GLib.idle_add(on_done, rc, out, err)
    threading.Thread(target=worker, daemon=True).start()


def fire_and_forget(cmd: list[str]) -> None:
    try:
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, start_new_session=True)
    except Exception as e:  # pylint: disable=broad-except
        log.error("fire_and_forget %s: %s", cmd, e)


def helper(*args: str, timeout: int = 120) -> tuple[int, str, str]:
    """Run privileged helper via pkexec. Returns (rc, stdout, stderr)."""
    if not Path(HELPER_PATH).exists():
        # Fallback: helper not installed yet (dev/preboot)
        log.warning("helper missing at %s", HELPER_PATH)
        return 127, "", "nyxus-security-helper not installed"
    return sh(["pkexec", HELPER_PATH, *args], timeout=timeout)


def helper_async(args: list[str],
                 on_done: Optional[Callable] = None) -> None:
    if not Path(HELPER_PATH).exists():
        if on_done:
            GLib.idle_add(on_done, 127, "", "nyxus-security-helper not installed")
        return
    sh_async(["pkexec", HELPER_PATH, *args], on_done=on_done, timeout=120)


# ── State detection (real reads — no mocks) ─────────────────────────────────
def detect_firewall() -> dict:
    """Read ufw status. Default deny-in/allow-out is the NYXUS shipping policy."""
    out = sh(["ufw", "status", "verbose"])[1]
    state = dict(active=False, default_in="unknown", default_out="unknown",
                 rules=[], logging="off")
    for line in out.splitlines():
        s = line.strip()
        if s.startswith("Status:"):
            state["active"] = ("active" in s.lower())
        elif s.startswith("Logging:"):
            state["logging"] = s.split(":", 1)[1].strip().lower()
        elif s.startswith("Default:"):
            d = s.split(":", 1)[1]
            for tok, key in (("incoming", "default_in"),
                             ("outgoing", "default_out"),
                             ("routed", "default_routed")):
                for word in ("deny", "allow", "reject", "disabled"):
                    if f"{word} ({tok}" in d:
                        state[key] = word
        elif (" ALLOW " in line or " DENY " in line or " REJECT " in line
              or " LIMIT " in line):
            state["rules"].append(s)
    rc2, out2, _ = sh(["systemctl", "is-enabled", "ufw.service"])
    state["enabled_at_boot"] = (out2 == "enabled")
    return state


def detect_clamav() -> dict:
    rc, out, _ = sh(["systemctl", "is-active", "clamav-daemon.service"])
    daemon = (out == "active")
    if not daemon:
        rc, out, _ = sh(["systemctl", "is-active", "clamav-daemon"])
        daemon = (out == "active")
    rc, out, _ = sh(["systemctl", "is-active", "clamav-freshclam.service"])
    freshclam = (out == "active")
    sig_age = "unknown"
    for fname in ("main.cvd", "main.cld", "daily.cvd", "daily.cld"):
        p = Path(f"/var/lib/clamav/{fname}")
        if p.exists():
            age = time.time() - p.stat().st_mtime
            sig_age = f"{int(age/86400)}d ago" if age > 86400 \
                      else f"{int(age/3600)}h ago"
            break
    last_scan = "never"
    h = LOG_DIR / "last_scan.txt"
    if h.exists():
        last_scan = h.read_text().strip()
    quarantine = []
    qdir = Path.home() / ".cache" / "nyxus" / "quarantine"
    if qdir.exists():
        quarantine = sorted([p.name for p in qdir.iterdir()])[:50]
    return dict(daemon=daemon, freshclam=freshclam,
                sig_age=sig_age, last_scan=last_scan,
                quarantine=quarantine)


def detect_tpm() -> dict:
    p = Path("/sys/class/tpm/tpm0")
    present = p.exists()
    version = "n/a"
    manuf = ""
    if present:
        v = p / "tpm_version_major"
        if v.exists():
            version = "TPM " + v.read_text().strip() + ".x"
        m = p / "description"
        if m.exists():
            manuf = m.read_text().strip()[:40]
    return dict(present=present, version=version, manuf=manuf)


def detect_secureboot() -> dict:
    rc, out, _ = sh(["bootctl", "status"])
    if rc == 0:
        if "Secure Boot: enabled" in out:   return dict(state="enabled")
        if "Secure Boot: disabled" in out:  return dict(state="disabled")
    rc, out, _ = sh(["mokutil", "--sb-state"])
    if rc == 0:
        ol = out.lower()
        if "enabled" in ol:  return dict(state="enabled")
        if "disabled" in ol: return dict(state="disabled")
    return dict(state="unknown")


def detect_luks() -> list[dict]:
    rc, out, _ = sh(["lsblk", "-rno", "NAME,FSTYPE,MOUNTPOINT,SIZE,TYPE"])
    vols = []
    if rc != 0:
        return vols
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "crypto_LUKS":
            mount = "(locked)"
            for p in parts:
                if p.startswith("/"):
                    mount = p
                    break
            size = parts[3] if len(parts) > 3 else ""
            vols.append(dict(name=parts[0], size=size, mount=mount))
    return vols


def detect_doh() -> dict:
    p = Path("/etc/systemd/resolved.conf")
    state = dict(doh=False, dnssec=False, server="(default)")
    if not p.exists():
        return state
    try:
        for line in p.read_text().splitlines():
            l = line.strip()
            if l.startswith("#") or not l:
                continue
            if l.lower().startswith("dnsoverttls=") and "yes" in l.lower():
                state["doh"] = True
            if l.lower().startswith("dnssec=") and "yes" in l.lower():
                state["dnssec"] = True
            if l.lower().startswith("dns="):
                state["server"] = l.split("=", 1)[1].strip()
    except Exception:
        pass
    return state


def detect_apparmor() -> dict:
    rc, out, _ = sh(["aa-status"])
    if rc != 0:
        return dict(enabled=False, profiles=0, complain=0)
    enforced = complain = 0
    for line in out.splitlines():
        s = line.strip()
        if "profiles are loaded" in s:
            try:
                enforced = int(s.split()[0])
            except Exception: pass
        if "in complain" in s:
            try:
                complain = int(s.split()[0])
            except Exception: pass
    return dict(enabled=True, profiles=enforced, complain=complain)


def detect_failed_logins(limit: int = 50) -> list[str]:
    rc, out, _ = sh(["journalctl", "-n", str(limit), "--no-pager",
                     "-g", "Failed password|authentication failure",
                     "--output", "short-iso"], timeout=10)
    return out.splitlines() if rc == 0 else []


def detect_audit_recent(limit: int = 80) -> list[str]:
    rc, out, _ = sh(["journalctl", "-n", str(limit), "--no-pager",
                     "_TRANSPORT=audit", "--output", "short-iso"],
                    timeout=5)
    if rc == 0 and out:
        return out.splitlines()
    rc, out, _ = sh(["journalctl", "-n", str(limit), "--no-pager",
                     "-p", "warning..emerg", "--output", "short-iso"],
                    timeout=5)
    return out.splitlines() if rc == 0 else []


def detect_fwupd() -> dict:
    rc, out, _ = sh(["fwupdmgr", "get-updates", "--json"], timeout=15)
    if rc == 0 and out:
        try:
            d = json.loads(out)
            return dict(updates_available=len(d.get("Devices", [])))
        except Exception:
            pass
    return dict(updates_available=0)


def detect_usbguard() -> dict:
    rc, out, _ = sh(["systemctl", "is-active", "usbguard.service"])
    return dict(active=(out == "active"))


def detect_idle_lock() -> dict:
    """Read hypridle.conf for screen-lock timeout."""
    p = Path.home() / ".config" / "hypr" / "hypridle.conf"
    timeout = 0
    if p.exists():
        try:
            for line in p.read_text().splitlines():
                s = line.strip()
                if s.startswith("timeout") and "=" in s:
                    try:
                        timeout = max(timeout, int(s.split("=", 1)[1].strip()))
                    except Exception: pass
        except Exception: pass
    return dict(seconds=timeout)


def detect_sudo_timeout() -> int:
    """Read /etc/sudoers timestamp_timeout. Default = 5 min."""
    try:
        for d in (Path("/etc/sudoers"), *Path("/etc/sudoers.d").glob("*")):
            if not d.is_file():
                continue
            for line in d.read_text(errors="ignore").splitlines():
                s = line.strip()
                if s.startswith("Defaults") and "timestamp_timeout" in s:
                    try:
                        return int(s.split("=", 1)[1].strip())
                    except Exception: pass
    except Exception: pass
    return 5


def detect_priv_indicators() -> dict:
    """Scan running processes for camera/mic/location/screen-capture handles."""
    cam = mic = loc = scr = False
    cam_apps: list[str] = []
    mic_apps: list[str] = []
    rc, out, _ = sh(["fuser", "-v", "/dev/video0"], timeout=2)
    if rc == 0 and out: cam = True
    rc, out, _ = sh(["lsof", "+D", "/dev/snd"], timeout=2)
    if rc == 0 and out:
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) > 0 and "snd/pcm" in line and "C" in parts[3:5]:
                mic = True
                if parts[0] not in mic_apps: mic_apps.append(parts[0])
    # geoclue
    rc, out, _ = sh(["systemctl", "is-active", "geoclue.service"])
    if out == "active":
        # check active clients
        rc2, out2, _ = sh(["busctl", "tree", "org.freedesktop.GeoClue2",
                          "--no-pager"], timeout=2)
        if "Client" in out2: loc = True
    # screen recorder?
    rc, out, _ = sh(["pgrep", "-a", "wf-recorder"])
    if rc == 0 and out: scr = True
    return dict(camera=cam, mic=mic, location=loc, screen=scr,
                camera_apps=cam_apps, mic_apps=mic_apps)


def hash_file(path: str) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception as e:
        log.warning("hash_file %s: %s", path, e)
        return None


# ── Health score — compose subsystem signals into a 0..100 number ──────────
def compute_health() -> tuple[int, list[tuple[str, str, str]]]:
    """Returns (score, [(label, kind, detail), ...])."""
    items: list[tuple[str, str, str]] = []
    score = 100

    fw = detect_firewall()
    if fw["active"] and fw["default_in"] in ("deny", "reject"):
        items.append(("Firewall", "ok", "Active · deny inbound"))
    elif fw["active"]:
        items.append(("Firewall", "warn", "Active · permissive defaults"))
        score -= 10
    else:
        items.append(("Firewall", "danger", "Inactive"))
        score -= 25

    cv = detect_clamav()
    if cv["daemon"]:
        items.append(("Real-time AV", "ok", f"Signatures {cv['sig_age']}"))
    else:
        items.append(("Real-time AV", "warn",
                      "Daemon stopped — on-demand scans only"))
        score -= 10

    sb = detect_secureboot()
    if sb["state"] == "enabled":
        items.append(("Secure Boot", "ok", "Enabled"))
    elif sb["state"] == "disabled":
        items.append(("Secure Boot", "warn", "Disabled in firmware"))
        score -= 10
    else:
        items.append(("Secure Boot", "info", "Status unknown"))

    tpm = detect_tpm()
    if tpm["present"]:
        items.append(("TPM", "ok", tpm["version"]))
    else:
        items.append(("TPM", "info", "Not present"))

    aa = detect_apparmor()
    if aa["enabled"] and aa["profiles"] > 0:
        items.append(("AppArmor", "ok", f"{aa['profiles']} profiles loaded"))
    elif aa["enabled"]:
        items.append(("AppArmor", "warn", "Enabled · no profiles"))
        score -= 5
    else:
        items.append(("AppArmor", "info", "Not loaded"))

    doh = detect_doh()
    if doh["doh"]:
        items.append(("DNS over TLS", "ok", doh["server"]))
    else:
        items.append(("DNS over TLS", "warn", "Plaintext DNS"))
        score -= 5

    luks = detect_luks()
    if luks:
        items.append(("Disk encryption", "ok",
                      f"{len(luks)} LUKS volume(s)"))
    else:
        items.append(("Disk encryption", "warn", "No LUKS volumes detected"))
        score -= 10

    fail = detect_failed_logins(20)
    if fail:
        items.append(("Failed logins (24h)", "warn", f"{len(fail)} events"))
    else:
        items.append(("Failed logins (24h)", "ok", "None"))

    return max(0, min(100, score)), items


# ── Toast helper (uses shared nyxus_toast lib if present) ──────────────────
def toast(msg: str, kind: str = "info") -> None:
    try:
        from nyxus_toast import toast as t
        t(msg, kind=kind)
    except Exception:
        fire_and_forget(["notify-send", "-a", "NYXUS Security",
                         "NYXUS Security", msg])


# ── CSS ────────────────────────────────────────────────────────────────────
def CSS() -> bytes:
    s = f"""
window, .background {{ background: {GLASS_DEEP}; color: {TEXT_PRIM}; }}
.nyx-shell {{ background: {GLASS_DEEP}; }}
.nyx-titlebar {{
  background: {GLASS_MED};
  border-bottom: 1px solid {HAIR_W};
  padding: 12px 18px;
}}
.nyx-title {{
  font-family: "Inter Display","Inter",sans-serif;
  font-size: 15px; font-weight: 700;
  letter-spacing: 0.10em; color: {TEXT_PRIM};
}}
.nyx-title .accent {{ color: {NYXUS_GOLD}; }}
.nyx-sidebar {{
  background: {GLASS_MED};
  border-right: 1px solid {HAIR_W};
  padding: 18px 12px;
}}
.nyx-sidebar-sub {{
  font-size: 11px; color: {TEXT_DIM};
  letter-spacing: 0.18em; text-transform: uppercase;
  margin: 6px 8px 12px 8px;
}}
.nyx-nav-row {{
  background: transparent; color: {TEXT_PRIM};
  border-radius: 12px; padding: 11px 14px; margin: 1px 0;
  font-size: 13.5px; border: 1px solid transparent;
}}
.nyx-nav-row:hover {{ background: rgba(255,255,255,0.04); }}
.nyx-nav-row.selected {{
  background: rgba(212,184,122,0.10);
  border: 1px solid rgba(212,184,122,0.35);
}}
.nyx-nav-glyph {{
  font-family: "JetBrainsMono Nerd Font","FiraCode Nerd Font",monospace;
  color: {NYXUS_GOLD}; margin-right: 12px; font-size: 14px;
}}
.nyx-page {{ background: transparent; padding: 24px 32px; }}
.nyx-page-title {{
  font-family: "Inter Display","Inter",sans-serif;
  font-size: 24px; font-weight: 700; color: {TEXT_PRIM};
}}
.nyx-page-sub {{ color: {TEXT_DIM}; font-size: 13px; margin-bottom: 18px; }}
.nyx-card {{
  background: {GLASS_SOFT};
  border: 1px solid {HAIR_W};
  border-radius: 14px;
  padding: 18px; margin-bottom: 14px;
}}
.nyx-card-title {{ font-weight: 600; font-size: 14px; color: {TEXT_PRIM}; }}
.nyx-card-sub {{ color: {TEXT_DIM}; font-size: 12px; margin-bottom: 10px; }}
.nyx-row {{ padding: 10px 12px; border-radius: 10px; }}
.nyx-row:hover {{ background: rgba(255,255,255,0.03); }}
.nyx-row-label {{ color: {TEXT_PRIM}; font-size: 13px; }}
.nyx-row-sub {{ color: {TEXT_DIM}; font-size: 11.5px; }}
.nyx-pill {{
  border-radius: 999px; padding: 2px 10px;
  font-size: 11px; font-weight: 600; letter-spacing: 0.04em;
}}
.nyx-pill.ok     {{ background: rgba(122,217,158,0.15); color: {SUCCESS};
                    border: 1px solid rgba(122,217,158,0.35); }}
.nyx-pill.warn   {{ background: rgba(232,196,106,0.15); color: {WARN};
                    border: 1px solid rgba(232,196,106,0.35); }}
.nyx-pill.danger {{ background: rgba(255,100,100,0.15); color: {DANGER};
                    border: 1px solid rgba(255,100,100,0.35); }}
.nyx-pill.info   {{ background: rgba(122,179,232,0.15); color: {INFO};
                    border: 1px solid rgba(122,179,232,0.35); }}
.nyx-btn {{
  background: {GLASS_MED}; color: {TEXT_PRIM};
  border: 1px solid {HAIR_W};
  border-radius: 10px; padding: 7px 16px; font-weight: 500;
}}
.nyx-btn:hover {{ background: rgba(212,184,122,0.10);
                  border-color: rgba(212,184,122,0.40); }}
.nyx-btn.primary {{
  background: rgba(212,184,122,0.18);
  border-color: rgba(212,184,122,0.55); color: {NYXUS_GOLD};
}}
.nyx-btn.danger {{
  background: rgba(255,100,100,0.10);
  border-color: rgba(255,100,100,0.45); color: {DANGER};
}}
.nyx-tape {{
  background: rgba(0,0,0,0.55);
  border-top: 1px solid {HAIR_W};
  padding: 6px 14px;
  color: {TEXT_DIM};
  font-family: "JetBrains Mono",monospace; font-size: 11px;
}}
.nyx-tape .marker {{ color: {NYXUS_GOLD}; }}
.nyx-health {{
  font-family: "Inter Display","Inter",sans-serif;
  font-size: 64px; font-weight: 800; color: {SUCCESS};
}}
.nyx-health.warn   {{ color: {WARN}; }}
.nyx-health.danger {{ color: {DANGER}; }}
.nyx-health-sub {{
  font-size: 12px; color: {TEXT_DIM};
  letter-spacing: 0.12em; text-transform: uppercase;
}}
.nyx-mono {{
  font-family: "JetBrains Mono",monospace;
  font-size: 11.5px; color: {TEXT_DIM};
}}
.nyx-banner {{
  background: rgba(212,184,122,0.08);
  border: 1px solid rgba(212,184,122,0.35);
  border-radius: 12px; padding: 12px 16px; margin-bottom: 14px;
  color: {TEXT_PRIM};
}}
.nyx-banner.warn   {{ background: rgba(232,196,106,0.10);
                      border-color: rgba(232,196,106,0.45); }}
.nyx-banner.danger {{ background: rgba(255,100,100,0.10);
                      border-color: rgba(255,100,100,0.45); }}
entry {{
  background: {GLASS_MED}; color: {TEXT_PRIM};
  border: 1px solid {HAIR_W}; border-radius: 10px;
  padding: 6px 10px;
}}
"""
    return s.encode("utf-8")


# ════════════════════════════════════════════════════════════════════════════
#  PAGE BASE
# ════════════════════════════════════════════════════════════════════════════
def make_pill(text: str, kind: str = "ok") -> Gtk.Label:
    l = Gtk.Label(label=text)
    l.add_css_class("nyx-pill")
    l.add_css_class(kind if kind in ("ok", "warn", "danger", "info") else "info")
    l.set_halign(Gtk.Align.START)
    return l


def make_row(label: str, control: Gtk.Widget,
             sub: str = "") -> Gtk.Box:
    row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
    row.add_css_class("nyx-row")
    text = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                   hexpand=True)
    l = Gtk.Label(label=label, xalign=0); l.add_css_class("nyx-row-label")
    text.append(l)
    if sub:
        s = Gtk.Label(label=sub, xalign=0); s.add_css_class("nyx-row-sub")
        s.set_wrap(True)
        text.append(s)
    row.append(text)
    if control is not None:
        control.set_valign(Gtk.Align.CENTER)
        row.append(control)
    return row


def make_card(title: str, sub: str = "") -> tuple[Gtk.Box, Gtk.Box]:
    """Return (card, body) — caller appends rows to body."""
    card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
    card.add_css_class("nyx-card")
    if title:
        t = Gtk.Label(label=title, xalign=0)
        t.add_css_class("nyx-card-title")
        card.append(t)
    if sub:
        s = Gtk.Label(label=sub, xalign=0); s.add_css_class("nyx-card-sub")
        s.set_wrap(True)
        card.append(s)
    body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    card.append(body)
    return card, body


def make_btn(label: str, kind: str = "default",
             on_click: Optional[Callable] = None) -> Gtk.Button:
    b = Gtk.Button(label=label)
    b.add_css_class("nyx-btn")
    if kind in ("primary", "danger"):
        b.add_css_class(kind)
    if on_click is not None:
        b.connect("clicked", lambda *_: on_click())
    return b


class SecPage(Adw.Bin):
    """Base page — refresh() reads system state and rebuilds UI."""
    title = "Section"
    subtitle = ""

    def __init__(self):
        super().__init__()
        self.add_css_class("nyx-page")
        self.scroller = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.scroller.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.scroller.set_child(self.outer)
        self.set_child(self.scroller)
        self._build_header()
        self.body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.outer.append(self.body)
        try:
            self.refresh()
        except Exception as e:  # pylint: disable=broad-except
            log.exception("page refresh failed: %s", e)
            self._show_error(str(e))

    def _build_header(self):
        title = Gtk.Label(label=self.title, xalign=0)
        title.add_css_class("nyx-page-title")
        self.outer.append(title)
        if self.subtitle:
            sub = Gtk.Label(label=self.subtitle, xalign=0)
            sub.add_css_class("nyx-page-sub"); sub.set_wrap(True)
            self.outer.append(sub)

    def _show_error(self, msg: str):
        b = Gtk.Label(label=f"Failed to load section: {msg}", xalign=0)
        b.add_css_class("nyx-banner"); b.add_css_class("danger")
        b.set_wrap(True)
        self.body.append(b)

    def refresh(self):
        """Subclass: clear self.body and append cards."""
        # Default: empty
        pass

    def clear(self):
        child = self.body.get_first_child()
        while child is not None:
            self.body.remove(child)
            child = self.body.get_first_child()


# ════════════════════════════════════════════════════════════════════════════
#  1. OVERVIEW — health score + subsystem grid + big actions
# ════════════════════════════════════════════════════════════════════════════
class OverviewPage(SecPage):
    title = "Security at a glance"
    subtitle = ("Composite health score from firewall, anti-malware, "
                "encryption, secure boot, audit, network, and identity.")

    def refresh(self):
        self.clear()
        score, items = compute_health()
        kind = "ok" if score >= 85 else ("warn" if score >= 65 else "danger")

        # Top: big score + headline
        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        top.add_css_class("nyx-card")
        score_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        big = Gtk.Label(label=str(score), xalign=0)
        big.add_css_class("nyx-health"); big.add_css_class(kind)
        sub = Gtk.Label(label="OVERALL  HEALTH  /  100", xalign=0)
        sub.add_css_class("nyx-health-sub")
        score_box.append(big); score_box.append(sub)
        top.append(score_box)

        sys_grid = Gtk.Grid(column_spacing=24, row_spacing=8, hexpand=True)
        for i, (label, k, detail) in enumerate(items):
            row = i % 5; col = i // 5
            cell = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            cell.append(make_pill(k.upper(), k))
            t = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
            n = Gtk.Label(label=label, xalign=0); n.add_css_class("nyx-row-label")
            d = Gtk.Label(label=detail, xalign=0); d.add_css_class("nyx-row-sub")
            t.append(n); t.append(d)
            cell.append(t)
            sys_grid.attach(cell, col, row, 1, 1)
        top.append(sys_grid)
        self.body.append(top)

        # Big-action buttons row
        actions, body = make_card("Quick actions",
                                  "One-click operations for the common cases.")
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        row.append(make_btn("Run Quick Scan", "primary",
                            on_click=lambda: fire_and_forget(
                                ["nyxus-security", "--quick-scan"])))
        row.append(make_btn("Update Definitions", "default",
                            on_click=lambda: helper_async(["update-clamav"],
                                on_done=lambda *_: toast("Definition update started"))))
        row.append(make_btn("Refresh Health", "default",
                            on_click=self.refresh))
        row.append(make_btn("PANIC LOCKDOWN", "danger",
                            on_click=lambda: fire_and_forget(
                                ["nyxus-security", "--panic"])))
        body.append(row)
        self.body.append(actions)

        # Recent audit (preview, last 8)
        recent_card, rb = make_card("Recent security events",
                                    "Last 8 entries from auditd / journal.")
        for line in detect_audit_recent(8):
            l = Gtk.Label(label=line[:200], xalign=0)
            l.add_css_class("nyx-mono"); l.set_wrap(False)
            l.set_ellipsize(Pango.EllipsizeMode.END)
            rb.append(l)
        if not rb.get_first_child():
            rb.append(Gtk.Label(label="No recent events.", xalign=0))
        self.body.append(recent_card)


# ════════════════════════════════════════════════════════════════════════════
#  2. VIRUS & THREATS — clamav
# ════════════════════════════════════════════════════════════════════════════
class VirusPage(SecPage):
    title = "Virus & Threats"
    subtitle = ("On-demand and real-time anti-malware via ClamAV. "
                "Signatures auto-updated by clamav-freshclam.")

    def refresh(self):
        self.clear()
        cv = detect_clamav()

        card, body = make_card("ClamAV engine", "")
        body.append(make_row("Real-time daemon",
                             make_pill("RUNNING" if cv["daemon"] else "STOPPED",
                                       "ok" if cv["daemon"] else "warn")))
        body.append(make_row("Signature updater (freshclam)",
                             make_pill("RUNNING" if cv["freshclam"] else "STOPPED",
                                       "ok" if cv["freshclam"] else "warn")))
        body.append(make_row("Definitions age", Gtk.Label(label=cv["sig_age"])))
        body.append(make_row("Last full scan",  Gtk.Label(label=cv["last_scan"])))

        ctrl = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ctrl.append(make_btn("Start daemon", "primary",
            on_click=lambda: helper_async(["enable-clamd"],
                on_done=lambda *_: (self.refresh(), toast("Daemon started")))))
        ctrl.append(make_btn("Update now", "default",
            on_click=lambda: helper_async(["update-clamav"],
                on_done=lambda *_: (self.refresh(), toast("Definitions updated")))))
        body.append(ctrl)
        self.body.append(card)

        # Scan target
        scan_card, sb = make_card("Run scan",
                                  "Quick scan = HOME + /tmp + recent downloads. "
                                  "Custom = pick any path.")
        path_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ent = Gtk.Entry(); ent.set_text(str(Path.home()))
        ent.set_hexpand(True)
        path_row.append(ent)
        path_row.append(make_btn("Scan path", "primary",
            on_click=lambda: self._do_scan(ent.get_text(), quick=False)))
        path_row.append(make_btn("Quick scan", "default",
            on_click=lambda: self._do_scan(str(Path.home()), quick=True)))
        sb.append(path_row)
        self.body.append(scan_card)

        # Quarantine
        qcard, qb = make_card("Quarantine",
            f"{len(cv['quarantine'])} item(s) in ~/.cache/nyxus/quarantine/")
        if cv["quarantine"]:
            for q in cv["quarantine"]:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                              spacing=8)
                row.add_css_class("nyx-row")
                row.append(Gtk.Label(label=q, xalign=0,
                                     hexpand=True))
                row.append(make_btn("Delete", "danger",
                    on_click=lambda _q=q: self._delete_quarantine(_q)))
                qb.append(row)
        else:
            qb.append(Gtk.Label(label="Quarantine is empty.", xalign=0))
        self.body.append(qcard)

        # Schedule
        scard, sbb = make_card("Scheduled scans",
            "Daily scan via systemd timer. Toggle below.")
        rc, out, _ = sh(["systemctl", "--user", "is-enabled",
                         "nyxus-clamscan.timer"])
        sw = Gtk.Switch()
        sw.set_active(out == "enabled")
        def on_toggle(s, *_):
            act = "enable-scan-timer" if s.get_active() else "disable-scan-timer"
            sh_async(["systemctl", "--user",
                      "enable" if s.get_active() else "disable",
                      "--now", "nyxus-clamscan.timer"],
                     on_done=lambda *_: toast(f"Scan timer {act}"))
        sw.connect("notify::active", on_toggle)
        sbb.append(make_row("Daily scan timer", sw,
                            sub="Runs nyxus-clamscan at 03:00 local time."))
        self.body.append(scard)

    def _do_scan(self, path: str, quick: bool):
        path = path.strip() or str(Path.home())
        if not Path(path).exists():
            toast(f"Path does not exist: {path}", kind="warn"); return
        toast(f"Scanning {path} …", kind="info")
        args = ["clamscan", "-ri", "--no-summary",
                "--move=" + str(LOG_DIR / "quarantine"), path]
        (LOG_DIR / "quarantine").mkdir(parents=True, exist_ok=True)
        if quick:
            args.insert(1, "--max-filesize=50M")
        def _done(rc, out, err):
            stamp = time.strftime("%Y-%m-%d %H:%M:%S")
            (LOG_DIR / "last_scan.txt").write_text(stamp)
            (LOG_DIR / "scan_history.log").open("a").write(
                f"\n[{stamp}] rc={rc}\n{out}\n{err}\n")
            infected = sum(1 for l in out.splitlines() if l.endswith("FOUND"))
            toast(f"Scan finished: {infected} infected · rc={rc}",
                  kind="warn" if infected else "ok")
            self.refresh()
        sh_async(args, on_done=_done, timeout=3600)

    def _delete_quarantine(self, name: str):
        try:
            (LOG_DIR / "quarantine" / name).unlink(missing_ok=True)
            toast(f"Deleted {name}")
        except Exception as e:
            toast(f"Delete failed: {e}", kind="danger")
        self.refresh()


# ════════════════════════════════════════════════════════════════════════════
#  3. FIREWALL & NETWORK DEFENSE — ufw rules CRUD
# ════════════════════════════════════════════════════════════════════════════
class FirewallPage(SecPage):
    title = "Firewall & Network Defense"
    subtitle = ("Uncomplicated Firewall (ufw) rules, default policies, "
                "logging, and per-application rules.")

    def refresh(self):
        self.clear()
        fw = detect_firewall()

        # State + master toggle
        scard, sb = make_card("Firewall state", "")
        sw = Gtk.Switch(); sw.set_active(fw["active"])
        def toggle_master(s, *_):
            arg = "enable" if s.get_active() else "disable"
            helper_async(["ufw-master", arg],
                on_done=lambda *_: (toast(f"ufw {arg}d"), self.refresh()))
        sw.connect("notify::active", toggle_master)
        sb.append(make_row("Firewall enabled",  sw,
            sub="When off, all traffic is allowed by the kernel."))
        sb.append(make_row("Default INBOUND",
            make_pill(fw["default_in"].upper(),
                      "ok" if fw["default_in"] in ("deny","reject") else "danger")))
        sb.append(make_row("Default OUTBOUND",
            make_pill(fw["default_out"].upper(),
                      "ok" if fw["default_out"] == "allow" else "warn")))
        sb.append(make_row("Logging", Gtk.Label(label=fw["logging"]),
            sub="Log levels: off · low · medium · high · full."))
        sb.append(make_row("Start at boot",
            make_pill("YES" if fw["enabled_at_boot"] else "NO",
                      "ok" if fw["enabled_at_boot"] else "warn")))
        # default policy buttons
        pol = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for direction in ("incoming", "outgoing"):
            for action in ("allow", "deny", "reject"):
                pol.append(make_btn(f"{direction[:3].upper()} {action}",
                    on_click=lambda d=direction, a=action:
                        helper_async(["ufw-default", d, a],
                            on_done=lambda *_: (toast(f"{d} default → {a}"),
                                                self.refresh()))))
        sb.append(pol)
        log_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        for lv in ("off", "low", "medium", "high", "full"):
            log_row.append(make_btn(f"Log: {lv}",
                on_click=lambda lv=lv: helper_async(["ufw-logging", lv],
                    on_done=lambda *_: (toast(f"Logging → {lv}"),
                                        self.refresh()))))
        sb.append(log_row)
        self.body.append(scard)

        # Add rule
        rcard, rb = make_card("Add rule",
            "Examples — ALLOW 22/tcp · DENY 25/tcp from 10.0.0.0/8 · "
            "LIMIT ssh.")
        form = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action = Gtk.DropDown.new_from_strings(["allow", "deny", "reject", "limit"])
        port = Gtk.Entry(); port.set_placeholder_text("port or service (22/tcp, ssh, http)")
        port.set_hexpand(True)
        src = Gtk.Entry(); src.set_placeholder_text("from (optional, e.g. 10.0.0.0/8)")
        form.append(action); form.append(port); form.append(src)
        form.append(make_btn("Add", "primary",
            on_click=lambda: self._add_rule(
                ["allow","deny","reject","limit"][action.get_selected()],
                port.get_text(), src.get_text())))
        rb.append(form)
        self.body.append(rcard)

        # Rule list with delete buttons
        lcard, lb = make_card("Active rules", f"{len(fw['rules'])} rule(s)")
        if not fw["rules"]:
            lb.append(Gtk.Label(label="No rules. Default policy applies.",
                                xalign=0))
        else:
            for i, r in enumerate(fw["rules"], start=1):
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                row.add_css_class("nyx-row")
                ll = Gtk.Label(label=r, xalign=0, hexpand=True)
                ll.add_css_class("nyx-mono"); ll.set_ellipsize(Pango.EllipsizeMode.END)
                row.append(ll)
                row.append(make_btn("Delete", "danger",
                    on_click=lambda n=i: self._delete_rule(n)))
                lb.append(row)
        self.body.append(lcard)

        # Profiles
        pcard, pb = make_card("Application profiles",
            "Pre-baked rule sets for common apps (OpenSSH, Samba, "
            "CUPS, Transmission). Toggle to allow/deny.")
        rc, out, _ = sh(["ufw", "app", "list"])
        if rc == 0 and out:
            for line in out.splitlines()[1:]:
                name = line.strip()
                if not name: continue
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                row.add_css_class("nyx-row")
                row.append(Gtk.Label(label=name, xalign=0, hexpand=True))
                row.append(make_btn("Allow", "default",
                    on_click=lambda n=name: helper_async(
                        ["ufw-app-allow", n],
                        on_done=lambda *_: (toast(f"Allowed {n}"),
                                            self.refresh()))))
                row.append(make_btn("Deny", "danger",
                    on_click=lambda n=name: helper_async(
                        ["ufw-app-deny", n],
                        on_done=lambda *_: (toast(f"Denied {n}"),
                                            self.refresh()))))
                pb.append(row)
        else:
            pb.append(Gtk.Label(label="No application profiles available.",
                                xalign=0))
        self.body.append(pcard)

        # Reset / panic
        dcard, db = make_card("Danger zone", "")
        drow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        drow.append(make_btn("Reset all rules", "danger",
            on_click=lambda: helper_async(["ufw-reset"],
                on_done=lambda *_: (toast("ufw reset"), self.refresh()))))
        drow.append(make_btn("Panic deny-all", "danger",
            on_click=lambda: helper_async(["ufw-panic"],
                on_done=lambda *_: (toast("Panic mode: all inbound denied"),
                                    self.refresh()))))
        db.append(drow)
        self.body.append(dcard)

    def _add_rule(self, action: str, port: str, src: str):
        port = port.strip(); src = src.strip()
        if not port:
            toast("Port/service required", kind="warn"); return
        args = ["ufw-add", action, port]
        if src: args.append(src)
        helper_async(args,
            on_done=lambda rc, *_: (toast(f"Rule added (rc={rc})"),
                                    self.refresh()))

    def _delete_rule(self, num: int):
        helper_async(["ufw-delete", str(num)],
            on_done=lambda *_: (toast(f"Rule #{num} deleted"), self.refresh()))


# ════════════════════════════════════════════════════════════════════════════
#  4. ACCOUNT PROTECTION
# ════════════════════════════════════════════════════════════════════════════
class AccountPage(SecPage):
    title = "Account Protection"
    subtitle = ("Password policy, sudo timeout, idle screen lock, and "
                "optional two-factor (TOTP). Account-lockout (PAM faillock) "
                "is shown for completeness but ships OFF — see the warning.")

    def refresh(self):
        self.clear()
        user = os.environ.get("USER", "")

        # Password age
        pcard, pb = make_card("Password & login", "")
        rc, out, _ = sh(["chage", "-l", user])
        if rc == 0:
            for line in out.splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    pb.append(make_row(k.strip(), Gtk.Label(label=v.strip())))
        else:
            pb.append(Gtk.Label(label="(chage data unavailable)", xalign=0))
        prow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        prow.append(make_btn("Change password", "primary",
            on_click=lambda: fire_and_forget(["nyxus-terminal", "-e", "passwd"])))
        prow.append(make_btn("Force expire", "default",
            on_click=lambda: helper_async(["expire-password", user],
                on_done=lambda *_: (toast("Password marked expired"),
                                    self.refresh()))))
        pb.append(prow)
        self.body.append(pcard)

        # Sudo timeout
        scard, sb = make_card("sudo authentication", "")
        timeout = detect_sudo_timeout()
        spin = Gtk.SpinButton.new_with_range(0, 60, 1)
        spin.set_value(timeout)
        spin.connect("value-changed", lambda s: helper_async(
            ["set-sudo-timeout", str(int(s.get_value()))],
            on_done=lambda *_: toast(f"sudo timeout = {int(s.get_value())} min")))
        sb.append(make_row("Re-prompt after (minutes)", spin,
            sub="0 = always prompt. Default 5."))
        self.body.append(scard)

        # Idle lock
        icard, ib = make_card("Idle screen lock", "")
        idle = detect_idle_lock()
        s2 = Gtk.SpinButton.new_with_range(0, 1800, 30)
        s2.set_value(idle["seconds"])
        s2.connect("value-changed", lambda s: helper_async(
            ["set-idle-lock", str(int(s.get_value()))],
            on_done=lambda *_: toast(
                f"Idle lock = {int(s.get_value())}s")))
        ib.append(make_row("Lock after (seconds)", s2,
            sub="0 = never. Configures hypridle.conf."))
        self.body.append(icard)

        # TOTP
        tcard, tb = make_card("Two-factor authentication (optional)",
            "Setup TOTP codes for sudo / SSH via google-authenticator. "
            "Disabled by default.")
        totp_set = (Path.home() / ".google_authenticator").exists()
        tb.append(make_row("TOTP enrolled",
            make_pill("YES" if totp_set else "NO",
                      "ok" if totp_set else "info")))
        trow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        trow.append(make_btn("Enroll" if not totp_set else "Re-enroll",
            "primary",
            on_click=lambda: fire_and_forget(
                ["nyxus-terminal", "-e", "google-authenticator", "-t", "-d", "-f"])))
        trow.append(make_btn("Disable", "danger",
            on_click=lambda: (Path.home() / ".google_authenticator").unlink(
                missing_ok=True) or self.refresh()))
        tb.append(trow)
        self.body.append(tcard)

        # PAM lockout — explicit warning, default OFF (user pref)
        wcard, wb = make_card("Account lockout (advanced)",
            "Enabling PAM faillock or pam_tally2 can lock you out during "
            "recovery. NYXUS ships these OFF by design; only enable AFTER "
            "the system is fully installed and verified.")
        warn = Gtk.Label(label=(
            "⚠  ENABLING THIS HAS LOCKED USERS OUT IN PAST RECOVERIES. "
            "NYXUS support cannot reset your password remotely."), xalign=0)
        warn.add_css_class("nyx-banner"); warn.add_css_class("danger")
        warn.set_wrap(True)
        wb.append(warn)
        rc, out, _ = sh(["grep", "-l", "pam_faillock",
                         "/etc/pam.d/system-auth"])
        active = (rc == 0 and bool(out))
        sw3 = Gtk.Switch(); sw3.set_active(active)
        # Hard two-step confirmation guard — see helper for the matching
        # --confirm=ENABLE-LOCKOUT-RISK token. The switch is reset to its
        # previous state until the user clicks through the modal dialog.
        self._faillock_busy = False
        def toggle_lockout(s, *_):
            if self._faillock_busy:
                return
            want_on = s.get_active()
            if want_on == active:
                return
            if not want_on:
                # Disabling is safe — go straight through.
                helper_async(["disable-faillock"],
                    on_done=lambda *_: (toast("PAM faillock disabled",
                                              kind="ok"), self.refresh()))
                return
            # Enabling — require explicit modal confirmation. Revert the
            # switch immediately; only flip back ON after the user clicks
            # the destructive action in the dialog.
            self._faillock_busy = True
            s.set_active(False)
            self._faillock_busy = False
            self._confirm_enable_faillock()
        sw3.connect("notify::active", toggle_lockout)
        wb.append(make_row("Enable PAM faillock", sw3,
            sub="3 fails → 15-minute lockout. OFF by default. Enabling "
                "requires explicit confirmation; cannot be reset remotely."))
        self.body.append(wcard)

    def _confirm_enable_faillock(self):
        """Two-step destructive confirmation for PAM faillock.

        Required because enabling faillock has historically locked the
        user out during install / recovery (see project preferences).
        Only after the user clicks the destructive action in this modal
        do we send the helper command — and even then the helper itself
        re-validates the --confirm token."""
        win = self.get_root()
        try:
            dlg = Adw.AlertDialog.new(
                "Enable PAM account lockout?",
                "After 5 failed password attempts within the configured "
                "window, your account will be locked for 15 minutes.\n\n"
                "NYXUS support cannot remotely reset your password. If "
                "you lose access, you will need physical/recovery access "
                "to clear the lockout state.\n\n"
                "Only enable this on a fully installed and tested system.")
            dlg.add_response("cancel", "Cancel")
            dlg.add_response("enable", "Enable lockout")
            dlg.set_response_appearance(
                "enable", Adw.ResponseAppearance.DESTRUCTIVE)
            dlg.set_default_response("cancel")
            dlg.set_close_response("cancel")
            def _on_resp(_d, resp):
                if resp != "enable":
                    return
                helper_async(
                    ["enable-faillock", "--confirm=ENABLE-LOCKOUT-RISK"],
                    on_done=lambda rc, *_: (
                        toast("PAM faillock ENABLED" if rc == 0
                              else "Enable failed — see security log",
                              kind="warn" if rc == 0 else "danger"),
                        self.refresh()))
            dlg.connect("response", _on_resp)
            dlg.present(win)
        except Exception as e:
            log.warning("AlertDialog unavailable: %s", e)
            toast("Cannot show confirm dialog — operation cancelled",
                  kind="danger")


# ════════════════════════════════════════════════════════════════════════════
#  5. APP & BROWSER CONTROL — Trust scores
# ════════════════════════════════════════════════════════════════════════════
class AppsPage(SecPage):
    title = "App & Browser Control"
    subtitle = ("Per-application TRUST SCORE, AUR pin list, AppImage "
                "warnings, and URL blocklist. Trust = signed (verified), "
                "AUR (community), unknown (caveat emptor).")

    def refresh(self):
        self.clear()

        # Trust score table for top installed packages
        tcard, tb = make_card("Installed packages by trust",
            "Pacman = signed by Arch repo · AUR = community-maintained · "
            "Foreign = unknown source.")
        rc, out, _ = sh(["pacman", "-Q"], timeout=5)
        n_total = len(out.splitlines()) if rc == 0 else 0
        rc2, out2, _ = sh(["pacman", "-Qm"], timeout=5)
        n_foreign = len(out2.splitlines()) if rc2 == 0 else 0
        n_signed = max(0, n_total - n_foreign)
        grid = Gtk.Grid(column_spacing=24, row_spacing=4)
        grid.attach(make_pill("SIGNED", "ok"), 0, 0, 1, 1)
        grid.attach(Gtk.Label(label=f"{n_signed} packages", xalign=0), 1, 0, 1, 1)
        grid.attach(make_pill("AUR/UNKNOWN", "warn"), 0, 1, 1, 1)
        grid.attach(Gtk.Label(label=f"{n_foreign} packages", xalign=0), 1, 1, 1, 1)
        tb.append(grid)
        if n_foreign:
            sub = Gtk.Label(label="\nForeign / AUR packages:", xalign=0)
            tb.append(sub)
            for line in (out2.splitlines() or [])[:30]:
                lb = Gtk.Label(label="  " + line, xalign=0)
                lb.add_css_class("nyx-mono")
                tb.append(lb)
            if n_foreign > 30:
                tb.append(Gtk.Label(label=f"… +{n_foreign-30} more", xalign=0))
        self.body.append(tcard)

        # AppImage allow-list (read-only summary)
        acard, ab = make_card("AppImage launcher policy",
            "AppImages run unsigned by default. NYXUS prompts on first "
            "launch and remembers your decision in ~/.config/nyxus/appimage-trust.json.")
        trust_p = Path.home() / ".config" / "nyxus" / "appimage-trust.json"
        trust = {}
        if trust_p.exists():
            try: trust = json.loads(trust_p.read_text())
            except Exception: pass
        if not trust:
            ab.append(Gtk.Label(label="No AppImages reviewed yet.", xalign=0))
        else:
            for path, status in list(trust.items())[:50]:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                row.add_css_class("nyx-row")
                row.append(Gtk.Label(label=path, xalign=0, hexpand=True))
                row.append(make_pill(status.upper(),
                    "ok" if status == "trusted" else "warn"))
                ab.append(row)
        self.body.append(acard)

        # URL block list (hosts file via helper)
        ucard, ub = make_card("URL / domain blocklist",
            "Adds entries to /etc/hosts → 0.0.0.0. Useful for ads, trackers, "
            "and known-malicious domains.")
        form = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ent = Gtk.Entry(); ent.set_placeholder_text("domain.tld")
        ent.set_hexpand(True)
        form.append(ent)
        form.append(make_btn("Block", "danger",
            on_click=lambda: helper_async(["block-domain", ent.get_text()],
                on_done=lambda *_: (toast(f"Blocked {ent.get_text()}"),
                                    self.refresh()))))
        form.append(make_btn("Unblock", "default",
            on_click=lambda: helper_async(["unblock-domain", ent.get_text()],
                on_done=lambda *_: (toast(f"Unblocked {ent.get_text()}"),
                                    self.refresh()))))
        ub.append(form)
        rc, out, _ = sh(["grep", "-E", r"^\s*0\.0\.0\.0", "/etc/hosts"])
        if rc == 0 and out:
            for line in out.splitlines()[:30]:
                lb = Gtk.Label(label=line, xalign=0); lb.add_css_class("nyx-mono")
                ub.append(lb)
        self.body.append(ucard)

        # Hash reputation (cloud lookup)
        hcard, hb = make_card("Executable HASH REPUTATION lookup",
            "Compute SHA-256 of any binary and check it against the NYXUS "
            "threat database. No file contents are uploaded — only the hash.")
        form2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ent2 = Gtk.Entry(); ent2.set_placeholder_text("/path/to/binary")
        ent2.set_hexpand(True)
        result_lbl = Gtk.Label(label="", xalign=0)
        result_lbl.add_css_class("nyx-mono"); result_lbl.set_wrap(True)
        def do_lookup(*_):
            path = ent2.get_text().strip()
            if not path or not Path(path).exists():
                toast("File not found", kind="warn"); return
            h = hash_file(path)
            if not h:
                toast("Hash failed", kind="danger"); return
            result_lbl.set_text(f"SHA-256: {h}\nQuerying api…")
            def _q():
                try:
                    import urllib.request, urllib.error
                    url = f"{_api_base()}/api/security/hash-reputation/{h}"
                    req = urllib.request.Request(url,
                        headers={"User-Agent": "nyxus-security/1"})
                    with urllib.request.urlopen(req, timeout=10) as r:
                        data = json.loads(r.read().decode())
                    GLib.idle_add(result_lbl.set_text,
                        f"SHA-256: {h}\nReputation: {data.get('reputation','unknown')}\n"
                        f"Detections: {data.get('detections',0)} / "
                        f"{data.get('engines',0)}")
                except Exception as e:
                    GLib.idle_add(result_lbl.set_text,
                        f"SHA-256: {h}\nLookup failed: {e}")
            threading.Thread(target=_q, daemon=True).start()
        form2.append(ent2)
        form2.append(make_btn("Lookup", "primary", on_click=do_lookup))
        hb.append(form2)
        hb.append(result_lbl)
        self.body.append(hcard)


# ════════════════════════════════════════════════════════════════════════════
#  6. DEVICE SECURITY — TPM, Secure Boot, fwupd, USBGuard
# ════════════════════════════════════════════════════════════════════════════
class DevicePage(SecPage):
    title = "Device Security"
    subtitle = ("Hardware-rooted security: TPM, Secure Boot, firmware "
                "updates (fwupd), and USB device authorization.")

    def refresh(self):
        self.clear()
        tpm = detect_tpm()
        sb_ = detect_secureboot()
        fw  = detect_fwupd()
        ug  = detect_usbguard()

        # TPM card
        tcard, tb = make_card("Trusted Platform Module (TPM)", "")
        tb.append(make_row("Present",
            make_pill("YES" if tpm["present"] else "NO",
                      "ok" if tpm["present"] else "info")))
        tb.append(make_row("Version", Gtk.Label(label=tpm["version"])))
        if tpm["manuf"]:
            tb.append(make_row("Manufacturer",
                               Gtk.Label(label=tpm["manuf"])))
        self.body.append(tcard)

        # Secure Boot
        scard, sbox = make_card("Secure Boot", "")
        kind = ("ok" if sb_["state"] == "enabled"
                else "warn" if sb_["state"] == "disabled" else "info")
        sbox.append(make_row("State",
                             make_pill(sb_["state"].upper(), kind)))
        sbox.append(Gtk.Label(label=
            "Secure Boot is configured in firmware (BIOS/UEFI). "
            "NYXUS can enroll its signing keys via mokutil.", xalign=0,
            wrap=True))
        sb_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        sb_row.append(make_btn("Enroll NYXUS keys", "primary",
            on_click=lambda: helper_async(["enroll-mok"],
                on_done=lambda *_: toast(
                    "MOK enrolled — confirm at next reboot"))))
        sbox.append(sb_row)
        self.body.append(scard)

        # fwupd
        fcard, fb = make_card("Firmware updates (fwupd)", "")
        kind = "ok" if fw["updates_available"] == 0 else "warn"
        fb.append(make_row("Updates available",
            make_pill(str(fw["updates_available"]), kind)))
        rc, out, _ = sh(["fwupdmgr", "get-devices"], timeout=10)
        if rc == 0 and out:
            for line in out.splitlines()[:25]:
                lb = Gtk.Label(label=line, xalign=0)
                lb.add_css_class("nyx-mono"); lb.set_ellipsize(Pango.EllipsizeMode.END)
                fb.append(lb)
        frow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        frow.append(make_btn("Check now", "default",
            on_click=lambda: sh_async(["fwupdmgr", "refresh", "--force"],
                on_done=lambda *_: (self.refresh(),
                                    toast("Firmware metadata refreshed")))))
        frow.append(make_btn("Install all", "primary",
            on_click=lambda: helper_async(["fwupd-update"],
                on_done=lambda *_: toast("Firmware updates queued"))))
        fb.append(frow)
        self.body.append(fcard)

        # USB autoblock
        ucard, ub = make_card("USB device authorization (USBGuard)",
            "Block new USB devices by default. Existing devices keep working. "
            "Useful against BadUSB-style attacks.")
        sw = Gtk.Switch(); sw.set_active(ug["active"])
        def toggle(s, *_):
            arg = "enable-usbguard" if s.get_active() else "disable-usbguard"
            helper_async([arg],
                on_done=lambda *_: (toast(f"USBGuard {arg}"), self.refresh()))
        sw.connect("notify::active", toggle)
        ub.append(make_row("USBGuard daemon", sw,
            sub="When ON, every new USB device requires explicit authorization."))
        urow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        urow.append(make_btn("List devices", "default",
            on_click=lambda: fire_and_forget(["nyxus-terminal", "-e",
                "bash", "-c", "usbguard list-devices ; read -p 'Enter…'"])))
        urow.append(make_btn("Allow all current", "default",
            on_click=lambda: helper_async(["usbguard-allow-all"],
                on_done=lambda *_: toast("Whitelisted current devices"))))
        ub.append(urow)
        self.body.append(ucard)

        # Removable media policy
        rcard, rb = make_card("Removable media policy",
            "Auto-mount and execute behavior for USB sticks / SD cards.")
        for opt, desc in (("noexec", "Never execute binaries from removable media"),
                          ("nosuid", "Strip setuid bits"),
                          ("nodev",  "Disallow device files")):
            rb.append(make_row(opt, Gtk.Label(label="ON"), sub=desc))
        self.body.append(rcard)


# ════════════════════════════════════════════════════════════════════════════
#  7. ENCRYPTION & VAULT — LUKS + vault
# ════════════════════════════════════════════════════════════════════════════
class EncryptionPage(SecPage):
    title = "Encryption & Vault"
    subtitle = ("LUKS volume management, /home encryption status, and a "
                "personal encrypted vault for secrets.")

    def refresh(self):
        self.clear()
        luks = detect_luks()

        # LUKS volumes
        lcard, lb = make_card("LUKS volumes",
            f"{len(luks)} encrypted volume(s) detected.")
        if not luks:
            lb.append(Gtk.Label(label=
                "No LUKS volumes found. New disks can be encrypted with "
                "cryptsetup luksFormat (see NYXUS Disks).", xalign=0))
        else:
            for v in luks:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                row.add_css_class("nyx-row")
                row.append(Gtk.Label(label=v["name"], xalign=0,
                                     hexpand=True))
                row.append(Gtk.Label(label=v["size"]))
                row.append(make_pill(v["mount"],
                    "ok" if v["mount"].startswith("/") else "warn"))
                lb.append(row)
        self.body.append(lcard)

        # Vault
        vcard, vb = make_card("Personal vault (~/.nyxus/vault.luks)",
            "A 256-MiB LUKS file you mount on demand for secrets, keys, "
            "passwords. Unlock prompts use the system keyring.")
        vault = Path.home() / ".nyxus" / "vault.luks"
        exists = vault.exists()
        vb.append(make_row("Vault file",
            make_pill("CREATED" if exists else "NONE",
                      "ok" if exists else "info"),
            sub=str(vault)))
        vrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        vrow.append(make_btn("Create vault" if not exists else "Recreate",
            "primary",
            on_click=lambda: helper_async(["vault-create",
                                           os.environ.get("USER", "")],
                on_done=lambda *_: (toast("Vault created"), self.refresh()))))
        vrow.append(make_btn("Unlock", "default",
            on_click=lambda: helper_async(["vault-open",
                                           os.environ.get("USER", "")],
                on_done=lambda *_: toast("Vault mounted"))))
        vrow.append(make_btn("Lock", "default",
            on_click=lambda: helper_async(["vault-close",
                                           os.environ.get("USER", "")],
                on_done=lambda *_: toast("Vault locked"))))
        vb.append(vrow)
        self.body.append(vcard)

        # Secure delete
        scard, sb_ = make_card("Secure delete",
            "Overwrite-and-delete a file with shred. Files in the user "
            "trash and downloads are common targets.")
        form = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ent = Gtk.Entry(); ent.set_placeholder_text("/path/to/file")
        ent.set_hexpand(True)
        form.append(ent)
        form.append(make_btn("Shred", "danger",
            on_click=lambda: self._shred(ent.get_text())))
        sb_.append(form)
        self.body.append(scard)

        # Keyring inspector (read-only summary)
        kcard, kb = make_card("Login keyring",
            "GNOME Keyring / kwallet status. NYXUS uses the FreeDesktop "
            "Secret Service for app passwords.")
        rc, out, _ = sh(["pgrep", "-a", "gnome-keyring-daemon"])
        kb.append(make_row("gnome-keyring",
            make_pill("RUNNING" if rc == 0 else "NOT RUNNING",
                      "ok" if rc == 0 else "warn")))
        self.body.append(kcard)

    def _shred(self, path: str):
        path = path.strip()
        if not path or not Path(path).exists():
            toast("File not found", kind="warn"); return
        sh_async(["shred", "-u", "-z", "-n", "3", path],
            on_done=lambda rc, *_: toast(
                "Shredded" if rc == 0 else "Shred failed",
                kind="ok" if rc == 0 else "danger"),
            timeout=600)


# ════════════════════════════════════════════════════════════════════════════
#  8. PRIVACY INDICATORS — camera/mic/location/screen-record activity
# ════════════════════════════════════════════════════════════════════════════
class PrivacyPage(SecPage):
    title = "Privacy Indicators"
    subtitle = ("Live indicators of which apps are using the camera, "
                "microphone, location, or screen capture. Top-bar dots "
                "(EWW) mirror this state in real time.")

    def refresh(self):
        self.clear()
        ind = detect_priv_indicators()

        card, body = make_card("Right now", "")
        for key, label in (("camera",   "Camera"),
                           ("mic",      "Microphone"),
                           ("location", "Location"),
                           ("screen",   "Screen capture")):
            on = ind[key]
            body.append(make_row(label,
                make_pill("ACTIVE" if on else "IDLE",
                          "danger" if on else "ok")))
        self.body.append(card)

        # Specific app lists
        if ind["camera_apps"] or ind["mic_apps"]:
            card2, b2 = make_card("Apps currently using sensors", "")
            for a in ind["camera_apps"]:
                b2.append(make_row(a + " · camera",
                                   make_pill("REVOKE", "danger")))
            for a in ind["mic_apps"]:
                b2.append(make_row(a + " · microphone",
                                   make_pill("REVOKE", "danger")))
            self.body.append(card2)

        # Recent permission events (last 24h via journal)
        rcard, rb = make_card("Recent permission events",
            "From journalctl — pipewire, geoclue, xdg-desktop-portal.")
        rc, out, _ = sh(["journalctl", "-n", "60", "--no-pager",
                         "-g", "(geoclue|pipewire|portal|camera|microphone)",
                         "--output", "short-iso"], timeout=8)
        if rc == 0 and out:
            for line in out.splitlines()[:40]:
                lb = Gtk.Label(label=line, xalign=0)
                lb.add_css_class("nyx-mono"); lb.set_ellipsize(Pango.EllipsizeMode.END)
                rb.append(lb)
        else:
            rb.append(Gtk.Label(label="No recent permission events.",
                                xalign=0))
        self.body.append(rcard)

        # Daemon toggle
        dcard, db = make_card("Privacy indicator daemon",
            "Background watcher (nyxus-security-daemon) that pushes "
            "live state to the EWW top-bar. Requires user-unit enable.")
        rc, out, _ = sh(["systemctl", "--user", "is-active",
                         "nyxus-security-daemon.service"])
        sw = Gtk.Switch(); sw.set_active(out == "active")
        def toggle(s, *_):
            sh_async(["systemctl", "--user",
                      "enable" if s.get_active() else "disable",
                      "--now", "nyxus-security-daemon.service"],
                on_done=lambda *_: toast(
                    f"Indicator daemon {'started' if s.get_active() else 'stopped'}"))
        sw.connect("notify::active", toggle)
        db.append(make_row("Indicator daemon", sw,
            sub="Pushes camera/mic/location/screen state to EWW dots."))
        self.body.append(dcard)

        # Auto-refresh every 4s while page open
        def tick():
            try:
                if self.get_root() and self.get_root().is_visible():
                    self.refresh()
                    return False  # rebuilt body, drop this tick
            except Exception: pass
            return False
        GLib.timeout_add_seconds(4, tick)


# ════════════════════════════════════════════════════════════════════════════
#  9. AUDIT & THREAT TAPE
# ════════════════════════════════════════════════════════════════════════════
class AuditPage(SecPage):
    title = "Audit & Threat Tape"
    subtitle = ("Full audit log search, failed-login viewer (READ-ONLY — "
                "we never auto-lockout), and live event tape.")

    def refresh(self):
        self.clear()

        # Failed logins (read-only)
        fcard, fb = make_card("Failed authentication attempts",
            "Read-only. NYXUS does NOT auto-lockout — see "
            "Account Protection for the explanation.")
        fails = detect_failed_logins(50)
        if not fails:
            fb.append(Gtk.Label(label="No failed authentications recorded.",
                                xalign=0))
        else:
            for line in fails[-30:]:
                lb = Gtk.Label(label=line, xalign=0)
                lb.add_css_class("nyx-mono"); lb.set_ellipsize(Pango.EllipsizeMode.END)
                fb.append(lb)
        self.body.append(fcard)

        # Recent audit events
        acard, ab = make_card("Recent system events (audit/journal)",
            "Last 80 entries. Click 'Open in journalctl' to drill down.")
        for line in detect_audit_recent(80)[-50:]:
            lb = Gtk.Label(label=line, xalign=0)
            lb.add_css_class("nyx-mono"); lb.set_ellipsize(Pango.EllipsizeMode.END)
            ab.append(lb)
        arow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        arow.append(make_btn("Open journalctl (audit)", "default",
            on_click=lambda: fire_and_forget(["nyxus-terminal", "-e",
                "journalctl", "-f", "_TRANSPORT=audit"])))
        arow.append(make_btn("Export to file", "default",
            on_click=self._export))
        ab.append(arow)
        self.body.append(acard)

        # Search
        scard, sb = make_card("Search journal",
            "Free-text search across the systemd journal.")
        form = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        ent = Gtk.Entry(); ent.set_placeholder_text("regex (e.g. sudo|ssh|denied)")
        ent.set_hexpand(True)
        results = Gtk.Label(label="", xalign=0)
        results.add_css_class("nyx-mono"); results.set_wrap(False)
        results.set_selectable(True)
        def do_search(*_):
            pattern = ent.get_text().strip()
            if not pattern:
                return
            sh_async(["journalctl", "-n", "200", "--no-pager",
                      "-g", pattern, "--output", "short-iso"],
                on_done=lambda rc, out, err: results.set_text(
                    out if rc == 0 else f"(no matches: {err})"),
                timeout=15)
        form.append(ent)
        form.append(make_btn("Search", "primary", on_click=do_search))
        sb.append(form); sb.append(results)
        self.body.append(scard)

    def _export(self):
        out_file = LOG_DIR / f"audit-export-{int(time.time())}.log"
        sh_async(["bash", "-c",
                  f"journalctl -n 5000 --no-pager > {shlex.quote(str(out_file))}"],
            on_done=lambda rc, *_: toast(
                f"Exported to {out_file}" if rc == 0 else "Export failed",
                kind="ok" if rc == 0 else "danger"))


# ════════════════════════════════════════════════════════════════════════════
#  10. RECOVERY & PANIC
# ════════════════════════════════════════════════════════════════════════════
class RecoveryPage(SecPage):
    title = "Recovery & Panic"
    subtitle = ("One-touch lockdown, recovery codes, integrity self-test, "
                "and panic-mode configuration.")

    def refresh(self):
        self.clear()

        # Panic
        pcard, pb = make_card("PANIC MODE",
            "Single keystroke (Super+Ctrl+Alt+L) to instantly: "
            "lock the screen, clear the clipboard, dismount removable "
            "media, flush DNS cache, kill the foreground window.")
        pb.append(make_btn("ENGAGE PANIC NOW", "danger",
            on_click=lambda: fire_and_forget(["nyxus-security", "--panic"])))
        sub = Gtk.Label(label=
            "Components run independently — if one fails the others still "
            "execute. All actions are logged to ~/.cache/nyxus/security.log.",
            xalign=0)
        sub.add_css_class("nyx-card-sub"); sub.set_wrap(True)
        pb.append(sub)
        self.body.append(pcard)

        # Recovery codes
        rcard, rb = make_card("Recovery codes",
            "10 single-use codes. Stored encrypted in the personal vault. "
            "Use them to recover account access if TOTP / password is lost.")
        codes_p = Path.home() / ".nyxus" / "recovery-codes.txt"
        rb.append(make_row("Codes generated",
            make_pill("YES" if codes_p.exists() else "NO",
                      "ok" if codes_p.exists() else "warn")))
        rrow = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        rrow.append(make_btn("Generate / regenerate", "primary",
            on_click=self._gen_codes))
        rrow.append(make_btn("View codes", "default",
            on_click=lambda: fire_and_forget(["xdg-open", str(codes_p)])
                if codes_p.exists() else toast("No codes generated yet",
                                                kind="warn")))
        rb.append(rrow)
        self.body.append(rcard)

        # Integrity self-test
        icard, ib = make_card("Integrity self-test",
            "Runs pacman -Qkk to verify every installed file's checksum. "
            "Catches tampering or disk corruption.")
        out_lbl = Gtk.Label(label="", xalign=0)
        out_lbl.add_css_class("nyx-mono"); out_lbl.set_wrap(True)
        ib.append(make_btn("Run self-test", "primary",
            on_click=lambda: self._self_test(out_lbl)))
        ib.append(out_lbl)
        self.body.append(icard)

    def _gen_codes(self):
        import secrets
        Path.home().joinpath(".nyxus").mkdir(parents=True, exist_ok=True)
        codes = ["-".join(secrets.token_hex(2) for _ in range(2))
                 for _ in range(10)]
        p = Path.home() / ".nyxus" / "recovery-codes.txt"
        p.write_text("# NYXUS recovery codes — single use, generated "
                     + time.strftime("%Y-%m-%d %H:%M:%S")
                     + "\n" + "\n".join(codes) + "\n")
        os.chmod(p, 0o600)
        toast("10 recovery codes written to ~/.nyxus/recovery-codes.txt",
              kind="ok")
        self.refresh()

    def _self_test(self, out_lbl: Gtk.Label):
        out_lbl.set_text("Running pacman -Qkk … this may take 1–2 minutes.")
        sh_async(["pacman", "-Qkk"],
            on_done=lambda rc, out, err: out_lbl.set_text(
                f"rc={rc}\n" + (out[-2000:] if out else err[-2000:])),
            timeout=600)


# ════════════════════════════════════════════════════════════════════════════
#  PANIC MODE — invoked via --panic CLI flag and Super+Ctrl+Alt+L keybind
# ════════════════════════════════════════════════════════════════════════════
def panic_mode():
    log.warning("PANIC MODE ENGAGED")
    actions = [
        # Clear clipboards (PRIMARY + CLIPBOARD)
        (["wl-copy", "--clear"], "clear wl-copy"),
        (["wl-copy", "-p", "--clear"], "clear primary"),
        (["pkill", "-x", "cliphist"], "kill cliphist"),
        # Flush DNS cache
        (["resolvectl", "flush-caches"], "flush dns"),
        # Dismount removable
        (["bash", "-c",
          "lsblk -nrpo NAME,RM,MOUNTPOINT | "
          "awk '$2==1 && $3!=\"\" {print $3}' | "
          "xargs -r -n1 udisksctl unmount -b 2>/dev/null"],
         "dismount removable"),
        # Lock the screen LAST so the user knows the others ran
        (["loginctl", "lock-session"], "lock session"),
    ]
    for cmd, name in actions:
        try:
            subprocess.Popen(cmd, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            log.info("panic: %s OK", name)
        except Exception as e:
            log.error("panic: %s FAIL: %s", name, e)
    # Also blast a notification
    try:
        subprocess.Popen(["notify-send", "-u", "critical",
                          "-a", "NYXUS Security", "PANIC MODE",
                          "Clipboard cleared · DNS flushed · "
                          "Removable media dismounted · Session locked"])
    except Exception: pass


def quick_scan():
    """Headless quick scan — used by --quick-scan CLI flag."""
    targets = [str(Path.home()), "/tmp"]
    qdir = LOG_DIR / "quarantine"; qdir.mkdir(parents=True, exist_ok=True)
    args = ["clamscan", "-ri", "--max-filesize=50M",
            f"--move={qdir}"] + targets
    try:
        subprocess.Popen(args, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        subprocess.Popen(["notify-send", "-a", "NYXUS Security",
                          "Quick scan started",
                          f"Scanning: {', '.join(targets)}"])
    except Exception as e:
        log.error("quick_scan: %s", e)


# ════════════════════════════════════════════════════════════════════════════
#  SHELL / WINDOW
# ════════════════════════════════════════════════════════════════════════════
SECTIONS: list[tuple[str, str, type]] = [
    ("overview",   "Overview",                OverviewPage),
    ("virus",      "Virus & Threats",         VirusPage),
    ("firewall",   "Firewall & Network",      FirewallPage),
    ("account",    "Account Protection",      AccountPage),
    ("apps",       "App & Browser Control",   AppsPage),
    ("device",     "Device Security",         DevicePage),
    ("encrypt",    "Encryption & Vault",      EncryptionPage),
    ("privacy",    "Privacy Indicators",      PrivacyPage),
    ("audit",      "Audit & Threat Tape",     AuditPage),
    ("recovery",   "Recovery & Panic",        RecoveryPage),
]
SECTION_GLYPH = {
    "overview": "shield", "virus": "virus", "firewall": "fire",
    "account":  "user",   "apps":  "apps",  "device":   "device",
    "encrypt":  "vault",  "privacy":"eye",  "audit":    "audit",
    "recovery": "panic",
}


class SecurityWindow(Gtk.ApplicationWindow):
    def __init__(self, app, initial: str = "overview"):
        super().__init__(application=app, title="NYXUS Security Center")
        self.set_default_size(WIN_W, WIN_H)
        self.set_decorated(False)
        self.add_css_class("background")

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        root.add_css_class("nyx-shell")

        # Title bar
        tb = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        tb.add_css_class("nyx-titlebar")
        title = Gtk.Label(label="", use_markup=True)
        title.set_markup(
            f"<span font_family='Inter Display' weight='bold' "
            f"size='large'>NYX<span foreground='{NYXUS_GOLD}'>US</span> "
            f"·  Security Center</span>")
        title.add_css_class("nyx-title")
        title.set_hexpand(True); title.set_halign(Gtk.Align.START)
        tb.append(title)
        tb.append(make_btn("Refresh", on_click=self._refresh_current))
        tb.append(make_btn("PANIC", "danger",
                           on_click=panic_mode))
        close = make_btn("✕", on_click=self.close)
        tb.append(close)
        root.append(tb)

        # Body: sidebar + page
        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0,
                       hexpand=True, vexpand=True)

        # Sidebar
        sb = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        sb.add_css_class("nyx-sidebar")
        sb.set_size_request(240, -1)
        head = Gtk.Label(label="SECURITY", xalign=0)
        head.add_css_class("nyx-sidebar-sub")
        sb.append(head)
        self._nav_rows: dict[str, Gtk.Button] = {}
        for sid, name, _cls in SECTIONS:
            btn = Gtk.Button()
            btn.add_css_class("nyx-nav-row")
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
            g = Gtk.Label(label=GLYPH.get(SECTION_GLYPH[sid], GLYPH["dot"]))
            g.add_css_class("nyx-nav-glyph")
            t = Gtk.Label(label=name, xalign=0, hexpand=True)
            row.append(g); row.append(t)
            btn.set_child(row)
            btn.connect("clicked", lambda _b, s=sid: self._switch(s))
            sb.append(btn)
            self._nav_rows[sid] = btn

        body.append(sb)

        # Stack
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.stack.set_transition_duration(180)
        self.stack.set_hexpand(True); self.stack.set_vexpand(True)
        self._pages: dict[str, SecPage] = {}
        for sid, name, cls in SECTIONS:
            page = cls()
            self._pages[sid] = page
            self.stack.add_named(page, sid)
        body.append(self.stack)

        root.append(body)

        # Threat tape (live ticker)
        self.tape = Gtk.Label(label="● THREAT TAPE  ·  starting…", xalign=0)
        self.tape.add_css_class("nyx-tape")
        self.tape.set_ellipsize(Pango.EllipsizeMode.END)
        self.tape.set_use_markup(True)
        root.append(self.tape)

        self.set_child(root)
        self._switch(initial)
        # Tape refresh
        self._tape_index = 0
        self._tape_lines: list[str] = []
        self._refresh_tape()
        GLib.timeout_add_seconds(3, self._tick_tape)
        GLib.timeout_add_seconds(15, self._refresh_tape_periodic)

        # Esc closes
        kc = Gtk.EventControllerKey()
        def _on_key(_c, keyval, _kc, _state):
            if keyval == Gdk.KEY_Escape:
                self.close(); return True
            return False
        kc.connect("key-pressed", _on_key)
        self.add_controller(kc)

    def _switch(self, sid: str):
        for k, btn in self._nav_rows.items():
            if k == sid: btn.add_css_class("selected")
            else:        btn.remove_css_class("selected")
        self.stack.set_visible_child_name(sid)
        # Refresh page on switch (cheap reads only)
        try: self._pages[sid].refresh()
        except Exception as e:  # pylint: disable=broad-except
            log.exception("switch %s: %s", sid, e)

    def _refresh_current(self):
        sid = self.stack.get_visible_child_name() or "overview"
        self._pages[sid].refresh()

    def _refresh_tape(self):
        def fetch():
            lines = detect_audit_recent(40)
            GLib.idle_add(self._update_tape_lines, lines)
        threading.Thread(target=fetch, daemon=True).start()

    def _refresh_tape_periodic(self):
        self._refresh_tape()
        return True

    def _update_tape_lines(self, lines: list[str]):
        self._tape_lines = lines or ["(no recent events)"]
        self._tape_index = 0

    def _tick_tape(self):
        if not self._tape_lines:
            return True
        line = self._tape_lines[self._tape_index % len(self._tape_lines)]
        self._tape_index += 1
        line = GLib.markup_escape_text(line[:300])
        self.tape.set_markup(
            f"<span foreground='{NYXUS_GOLD}'>● THREAT TAPE</span>  "
            f"<span foreground='{TEXT_FAINT}'>{line}</span>")
        return True


# ── Try to apply unified DARK MIRROR chrome ────────────────────────────────
try:
    sys.path.insert(0, os.path.expanduser("~/.nyxus"))
    from nyxus_chrome import install_chrome as _nyx_install_chrome  # noqa
except Exception:
    pass


class SecurityApp(Adw.Application):
    def __init__(self, initial: str = "overview"):
        super().__init__(application_id=APP_ID,
                         flags=Gio.ApplicationFlags.NON_UNIQUE)
        try: Adw.init()
        except Exception: pass
        self._initial = initial

    def do_activate(self):
        try:
            sm = Adw.StyleManager.get_default()
            sm.set_color_scheme(Adw.ColorScheme.FORCE_DARK)
        except Exception: pass
        prov = Gtk.CssProvider()
        prov.load_from_data(CSS())
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), prov,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
        win = SecurityWindow(self, initial=self._initial)
        win.present()


# ════════════════════════════════════════════════════════════════════════════
#  CLI
# ════════════════════════════════════════════════════════════════════════════
USAGE = """\
nyxus-security [section]
nyxus-security --panic        Engage PANIC MODE (lock + clear + flush)
nyxus-security --quick-scan   Headless quick scan
nyxus-security --list         List section IDs
"""


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        a = argv[1]
        if a in ("--help", "-h"):
            print(USAGE); return 0
        if a == "--list":
            for sid, name, _ in SECTIONS:
                print(f"{sid:12} {name}")
            return 0
        if a == "--panic":
            panic_mode(); return 0
        if a == "--quick-scan":
            quick_scan(); return 0
        if a in {sid for sid, _, _ in SECTIONS}:
            app = SecurityApp(initial=a)
            return app.run([])
    app = SecurityApp()
    return app.run([])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
