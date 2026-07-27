#!/usr/bin/env python3
"""
NYXUS · EWW · GHOST station feed  (Security · Intel · Recon)

Emits one JSON blob for the GHOST deck. Every number here is REAL and probed
live - if the honeypots have seen nothing, this reports zero rather than
inventing activity. A security console that lies is worse than none.

PERF: docker calls are the slow part, so everything is probed once per call
with short timeouts and the deck polls this at 15s, not 1s.
"""
import json
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()

# containers that make up the honeypot stack (docker names)
POTS = ["cowrie", "dionaea", "conpot", "heralding", "endlessh",
        "http-honeypot", "grafana", "prometheus", "loki", "promtail"]

# the three defence daemons, as declared in ~/Arsenal/registry.toml
# name, is-active probe, and the journalctl args the deck row opens.
# The journal args live HERE, not in eww.yuck: a nested ternary with escaped
# quotes inside a ${} interpolation is not valid yuck (it fails with
# "Invalid token"), and data belongs in the feed anyway.
DEFENSE = [
    ("jeTT",    ["systemctl", "is-active", "jett-daemon"],      "-u jett-daemon"),
    ("Bifrost", ["systemctl", "is-active", "bifrost-guardian"], "-u bifrost-guardian"),
    ("Meli",    ["systemctl", "--user", "is-active", "meli-ingest"], "--user -u meli-ingest"),
]


def _run(cmd, timeout=4):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout).stdout
    except Exception:
        return ""


def state():
    try:
        raw = _run(["bash", str(HOME / ".config/eww/scripts/security-state.sh")])
        d = json.loads(raw)
    except Exception:
        d = {}
    hacker = d.get("hacker", "off") == "on"
    ghost = d.get("ghost", "off") == "on"
    panic = d.get("panic", "idle")
    # posture is a rollup for the big readout
    if panic not in ("idle", ""):
        label, tone = "PANIC", "hot"
    elif hacker:
        label, tone = "HACKER", "warn"
    elif ghost:
        label, tone = "GHOST", "cool"
    else:
        label, tone = "NOMINAL", "ok"
    return {"hacker": hacker, "ghost": ghost, "panic": panic,
            "label": label, "tone": tone}


def defense():
    out = []
    for name, cmd, jargs in DEFENSE:
        out.append({"name": name, "ok": _run(cmd, 2).strip() == "active",
                    "jargs": jargs})
    return out


def pots():
    running = set()
    for line in _run(["docker", "ps", "--format", "{{.Names}}"], 6).splitlines():
        running.add(line.strip())
    rows = [{"name": p, "ok": p in running} for p in POTS]
    return rows, sum(1 for r in rows if r["ok"]), len(rows)


def attacks():
    """Cowrie connection attempts. Honest zero when the pots are quiet."""
    log = _run(["docker", "logs", "--tail", "400", "cowrie"], 6)
    hits = re.findall(r"New connection:\s*([0-9.]+)", log)
    recent = []
    for ip in reversed(hits):
        if ip not in [r["ip"] for r in recent]:
            recent.append({"ip": ip, "note": "ssh probe"})
        if len(recent) >= 5:
            break
    return {"total": len(hits), "recent": recent, "quiet": not hits}


def exposure():
    ports = set()
    for line in _run(["ss", "-tulnH"], 4).splitlines():
        parts = line.split()
        if len(parts) >= 5:
            m = re.search(r":(\d+)$", parts[4])
            if m:
                ports.add(int(m.group(1)))
    top = sorted(ports)[:16]
    # pre-joined: eww renders a raw list as its JSON literal ("21","22"...)
    return {"count": len(ports),
            "ports": [str(p) for p in top],
            "ports_str": "  ".join(str(p) for p in top)}


def auth():
    log = _run(["journalctl", "--since", "24 hours ago", "-q", "-n", "2000"], 6)
    n = len(re.findall(r"authentication failure|Failed password|invalid user",
                       log, re.I))
    return {"failed": n}


def firewall():
    """ufw rule detail needs root, so report the unit state (which does not)
    rather than prompting for a password from a status poll."""
    ufw = _run(["systemctl", "is-active", "ufw"], 2).strip() == "active"
    bridges = len([l for l in _run(["ip", "-br", "addr"], 3).splitlines()
                   if l.startswith("br-")])
    return {"ufw": ufw, "bridges": bridges}


def conns():
    est = [l for l in _run(["ss", "-tnH", "state", "established"], 4).splitlines() if l.strip()]
    foreign = []
    for l in est:
        parts = l.split()
        if len(parts) >= 4:
            ip = parts[3].rsplit(":", 1)[0].strip("[]")
            if ip and not ip.startswith(("127.", "::1")) and ip not in foreign:
                foreign.append(ip)
    return {"count": len(est), "foreign": len(foreign),
            "top": "  ".join(foreign[:4])}


def sessions():
    rows = [l for l in _run(["who"], 3).splitlines() if l.strip()]
    return {"count": len(rows), "who": rows[0][:30] if rows else "none"}


def scanners():
    """rkhunter / clamav: installed but never run is a REAL finding, so say
    so instead of hiding the card."""
    import shutil
    rk = bool(shutil.which("rkhunter"))
    cl = bool(shutil.which("clamscan"))
    rk_log = Path("/var/log/rkhunter.log")
    cl_db = list(Path("/var/lib/clamav").glob("*.c?d")) if Path("/var/lib/clamav").is_dir() else []
    return {
        "rk": rk, "rk_run": rk_log.exists(),
        "cl": cl, "cl_db": bool(cl_db),
        "stale": (rk and not rk_log.exists()) or (cl and not cl_db),
    }


if __name__ == "__main__":
    fallback = {
        "state": {"hacker": False, "ghost": False, "panic": "idle",
                  "label": "UNKNOWN", "tone": "cool"},
        "defense": [], "pots": [], "pots_up": 0, "pots_total": 0,
        "attacks": {"total": 0, "recent": [], "quiet": True},
        "exposure": {"count": 0, "ports": [], "ports_str": ""}, "auth": {"failed": 0},
        "firewall": {"ufw": False, "bridges": 0},
        "conns": {"count": 0, "foreign": 0, "top": ""},
        "sessions": {"count": 0, "who": ""},
        "scanners": {"rk": False, "rk_run": False, "cl": False, "cl_db": False, "stale": False},
    }
    try:
        rows, up, total = pots()
        print(json.dumps({
            "state": state(),
            "defense": defense(),
            "pots": rows, "pots_up": up, "pots_total": total,
            "attacks": attacks(),
            "exposure": exposure(),
            "auth": auth(),
            "firewall": firewall(),
            "conns": conns(),
            "sessions": sessions(),
            "scanners": scanners(),
        }))
    except Exception:
        print(json.dumps(fallback))
