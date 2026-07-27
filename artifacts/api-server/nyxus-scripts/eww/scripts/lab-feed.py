#!/usr/bin/env python3
"""
NYXUS · EWW · LAB station feed  (home lab: VMs + live attacker view)

Three things the lab deck needs, all probed live:
  vms      VirtualBox guests, their real power state and snapshot count
  attack   live honeypot hits from the HoneyHive API (same source the GHOST
           deck uses - one API, not two scrapers)
  net      the host-only network the lab VMs sit on

VBoxManage is the slow part (~150ms per call), so the whole thing is probed
once per invocation and the deck polls it at 8s.
"""
import json
import re
import subprocess
from pathlib import Path

HIVE = "http://localhost:8888"

# The lab guests. `role` drives what the deck says each box is FOR - the
# attacker box is the one you watch, the honeypot target is what it hits.
VMS = [
    ("lab-attacker", "attacker", "the box you drive"),
    ("bifrost-test", "target", "Bifrost EDR under test"),
    ("bifrost-test2", "target", "Bifrost EDR - snapshots"),
]


def _run(cmd, timeout=6):
    try:
        return subprocess.run(cmd, capture_output=True, text=True,
                              timeout=timeout).stdout
    except Exception:
        return ""


def _vm_info(name):
    raw = _run(["VBoxManage", "showvminfo", name, "--machinereadable"], 6)
    if not raw:
        return None
    def field(key):
        m = re.search(rf'^{key}="?([^"\n]*)"?$', raw, re.M)
        return m.group(1) if m else ""
    state = field("VMState") or "unknown"
    snaps = len(re.findall(r'^SnapshotName', raw, re.M))
    mem = field("memory")
    return {
        "state": state,
        # running covers both "running" and "paused"; aborted is a crash, and
        # saying so is more useful than folding it into "off"
        "on": state in ("running", "paused"),
        "aborted": state == "aborted",
        "mem": f"{int(mem)//1024}G" if mem.isdigit() else "?",
        "os": field("ostype").replace(" (64-bit)", ""),
        "net": field("nic1"),
        "snaps": snaps,
    }


def vms():
    rows, up = [], 0
    for name, role, note in VMS:
        info = _vm_info(name)
        if not info:
            continue
        if info["on"]:
            up += 1
        rows.append({"name": name, "role": role, "note": note, **info})
    return rows, up


def _hive(path, timeout=3):
    raw = _run(["curl", "-fsS", "--max-time", str(timeout), HIVE + path], timeout + 1)
    try:
        return json.loads(raw)
    except Exception:
        return None


def attack():
    """Live attacker activity, straight off the HoneyHive API."""
    st = _hive("/api/stats") or {}
    feed = _hive("/api/feed?since=0&limit=7") or []
    rows = []
    for e in feed[:7]:
        if not isinstance(e, dict):
            continue
        rows.append({
            "ip": e.get("src_ip") or "?",
            "port": str(e.get("dst_port") or ""),
            "proto": (e.get("protocol") or "").upper(),
            "pot": e.get("honeypot") or "?",
            "kind": (e.get("event_type") or "").split(".")[-1][:12],
        })
    return {
        "up": bool(st),
        "h1": st.get("hits_1h", 0),
        "total": st.get("total", 0),
        "ips": st.get("unique_ips", 0),
        "rows": rows,
        "quiet": not rows,
    }


def net():
    """The host-only network the lab guests are wired to."""
    ifs = []
    for line in _run(["VBoxManage", "list", "hostonlyifs"], 6).splitlines():
        m = re.match(r'^(Name|IPAddress|Status):\s+(.*)$', line.strip())
        if m:
            ifs.append((m.group(1), m.group(2).strip()))
    name = ip = status = ""
    for k, v in ifs:
        if k == "Name" and not name:
            name = v
        elif k == "IPAddress" and not ip:
            ip = v
        elif k == "Status" and not status:
            status = v
    return {"iface": name or "none", "ip": ip or "-", "up": status.lower() == "up"}


if __name__ == "__main__":
    fallback = {"vms": [], "vms_up": 0,
                "attack": {"up": False, "h1": 0, "total": 0, "ips": 0,
                           "rows": [], "quiet": True},
                "net": {"iface": "none", "ip": "-", "up": False}}
    try:
        rows, up = vms()
        print(json.dumps({"vms": rows, "vms_up": up,
                          "attack": attack(), "net": net()}))
    except Exception:
        print(json.dumps(fallback))
