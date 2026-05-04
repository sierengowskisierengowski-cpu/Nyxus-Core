"""Module 14 — MITM Framework (defensive posture)."""
from __future__ import annotations

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "MITM Framework"
    ICON = "🪞"
    DESCRIPTION = ("Defensive ARP / DNS / SSL anomaly detection plus active toolkits "
                   "(arp-scan, mitmproxy, ettercap) for authorised lab testing.")

    def build(self):
        self.add_action("📋 ARP table",          self.arp_table, primary=True)
        self.add_action("🔎 arp-scan local",     self.arp_scan)
        self.add_action("🛡  ARP poisoning watch (10 s)", self.arp_watch)
        self.add_action("🌐 DNS resolver test",  self.dns_test)
        self.add_action("ℹ  mitmproxy status",   self.mitm)
        self.add_action("ℹ  ettercap NG check",  self.ettercap)

    def arp_table(self):
        rc, out = run_subprocess(["ip","neigh","show"], timeout=5); self.write(out)

    def arp_scan(self):
        if not self.need("arp-scan"): return
        rc, out = run_subprocess(["arp-scan","--localnet"], timeout=60); self.write(out)

    def arp_watch(self):
        # snapshot, sleep, snapshot, diff
        rc, a = run_subprocess(["ip","neigh","show"], timeout=5)
        rc, _ = run_subprocess(["sleep","10"], timeout=12)
        rc, b = run_subprocess(["ip","neigh","show"], timeout=5)
        sa = {l.split(maxsplit=4)[0]: l for l in a.splitlines() if l}
        sb = {l.split(maxsplit=4)[0]: l for l in b.splitlines() if l}
        for ip in set(sa) | set(sb):
            if sa.get(ip) != sb.get(ip):
                self.write(f"⚠  changed {ip}\n  was: {sa.get(ip,'(absent)')}\n  now: {sb.get(ip,'(absent)')}")
        if all(sa.get(ip) == sb.get(ip) for ip in set(sa) | set(sb)):
            self.write("ARP table stable — no changes in 10 s")

    def dns_test(self):
        if not self.need("dig"): return
        for resolver in ("1.1.1.1","8.8.8.8","9.9.9.9"):
            rc, out = run_subprocess(["dig","@"+resolver,"+short", self.target or "example.com"], timeout=5)
            self.write(f"{resolver}: {out.strip() or '(no answer)'}")

    def mitm(self):
        rc, out = run_subprocess(["mitmproxy","--version"], timeout=5); self.write(out)

    def ettercap(self):
        rc, out = run_subprocess(["ettercap","-v"], timeout=5); self.write(out)
