"""Module 01 — Network Intelligence.

Full network discovery via Nmap, ARP table inspection (Scapy when
available), DHCP/lease enumeration, and rogue-device detection. Every
discovered device is recorded to the device_history table with
timestamps so reappearance over time is tracked.
"""
from __future__ import annotations

import re
import shutil
import socket
from pathlib import Path

from ui import BaseModule, run_subprocess, have
import db


class Page(BaseModule):
    NAME = "Network Intelligence"
    ICON = "🌐"
    DESCRIPTION = ("Discover every device on the LAN, fingerprint vendors, "
                   "watch the ARP table, and flag rogue or new arrivals.")

    def build(self):
        self.add_action("🔎 Full sweep (nmap -sn)", self.action_sweep, primary=True)
        self.add_action("📡 ARP table",            self.action_arp)
        self.add_action("🏷  DHCP leases",          self.action_dhcp)
        self.add_action("👻 Rogue devices",        self.action_rogue)
        self.add_action("🛰  IPv6 hosts",           self.action_ipv6)
        self.add_action("📊 Device history",       self.action_history)

    # --------------------------------------------------------------- #
    def _local_cidr(self) -> str:
        rc, out = run_subprocess(["ip","-4","addr","show","scope","global"])
        for line in out.splitlines():
            line = line.strip()
            if line.startswith("inet "):
                a = line.split()[1]
                ip = a.split("/")[0]
                octs = ip.split(".")
                return f"{octs[0]}.{octs[1]}.{octs[2]}.0/24"
        return "192.168.1.0/24"

    # --------------------------------------------------------------- #
    def action_sweep(self):
        if not self.need("nmap"):
            return
        cidr = self.target or self._local_cidr()
        self.write(f"sweeping {cidr} …")
        rc, out = run_subprocess(["nmap","-sn","--max-retries","1",cidr], timeout=180)
        self.write(out)
        scan_id = db.record_scan(self.NAME, cidr, "ping", f"nmap -sn {cidr}",
                                  f"sweep complete · rc={rc}")
        # parse out hosts and add to device_history
        ip = host = mac = ""
        for line in out.splitlines():
            if line.startswith("Nmap scan report for"):
                rest = line.split("for", 1)[1].strip()
                if "(" in rest:
                    host, ip = rest.split("(", 1)
                    host, ip = host.strip(), ip.rstrip(")")
                else:
                    host, ip = "", rest
                mac = ""
            elif line.startswith("MAC Address:"):
                parts = line.split()
                mac = parts[2]
                vendor = " ".join(parts[3:]).strip("()")
                if mac:
                    db.see_device(mac, ip, host, vendor)
        self.write(f"\n[scan id {scan_id}]  recorded to device_history")

    def action_arp(self):
        if shutil.which("ip"):
            rc, out = run_subprocess(["ip", "neigh", "show"])
            self.write(out or "(empty arp table)")
        elif shutil.which("arp"):
            rc, out = run_subprocess(["arp", "-a"])
            self.write(out)
        else:
            self.write("neither `ip` nor `arp` available")

    def action_dhcp(self):
        # try dhclient lease file or NetworkManager dispatcher leases
        candidates = [
            "/var/lib/dhcp/dhclient.leases",
            "/var/lib/NetworkManager",
            "/var/lib/dhcpcd",
        ]
        for c in candidates:
            p = Path(c)
            if p.exists():
                if p.is_dir():
                    for f in p.rglob("*.lease*"):
                        try:
                            self.write(f"=== {f} ===\n" + f.read_text(errors='replace')[:5000])
                        except Exception:
                            continue
                else:
                    self.write(f"=== {p} ===\n" + p.read_text(errors='replace')[:5000])
                return
        # fallback: parse syslog for DHCPACK
        rc, out = run_subprocess(["journalctl","-t","dhcpd","-t","dhclient","-n","200","--no-pager"], timeout=10)
        self.write(out or "no DHCP server/client info available")

    def action_rogue(self):
        # mark devices first-seen in last 60 min as 'new'
        import time, sqlite3
        c = db.conn()
        cutoff = time.time() - 3600
        cur = c.execute("SELECT mac, ip, hostname, vendor, first_seen "
                         "FROM device_history WHERE first_seen > ? "
                         "ORDER BY first_seen DESC", (cutoff,))
        rows = cur.fetchall()
        if not rows:
            self.write("no new devices in last hour")
            return
        for mac, ip, host, vendor, first in rows:
            ago = int((time.time() - first) // 60)
            self.write(f"⚠ NEW · {ago:>3}m ago · {mac} · {ip:<15} · {host or '?':<25} · {vendor}")

    def action_ipv6(self):
        if not self.need("ping6") and not have("ping"):
            return
        # fe80::1 multicast all-nodes discovery
        rc, out = run_subprocess(
            ["ping","-6","-c","2","-W","1","ff02::1%" + self._default_iface()],
            timeout=10
        )
        self.write(out)
        rc, out = run_subprocess(["ip","-6","neigh","show"])
        self.write("\n=== ipv6 neighbours ===\n" + (out or "(empty)"))

    def _default_iface(self) -> str:
        rc, out = run_subprocess(["ip","route","show","default"])
        m = re.search(r"dev\s+(\S+)", out or "")
        return m.group(1) if m else "eth0"

    def action_history(self):
        cur = db.conn().execute(
            "SELECT mac, ip, hostname, vendor, first_seen, last_seen "
            "FROM device_history ORDER BY last_seen DESC LIMIT 200")
        rows = cur.fetchall()
        if not rows:
            self.write("device_history is empty — run a sweep first")
            return
        import time
        self.write(f"{'MAC':<19} {'IP':<16} {'HOST':<22} {'VENDOR':<25} {'FIRST':<11} {'LAST':<11}")
        self.write("-" * 105)
        for mac, ip, host, vendor, first, last in rows:
            self.write(
                f"{mac:<19} {ip or '?':<16} {(host or '?')[:22]:<22} "
                f"{(vendor or '?')[:25]:<25} "
                f"{time.strftime('%m-%d %H:%M', time.localtime(first)):<11} "
                f"{time.strftime('%m-%d %H:%M', time.localtime(last)):<11}"
            )
