"""Module 21 — Log Analysis Engine."""
from __future__ import annotations

import re
from collections import Counter

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "Log Analysis"
    ICON = "📜"
    DESCRIPTION = ("journalctl + auth.log triage: failed logins, sudo abuse, kernel "
                   "anomalies, brute-force IPs, and per-unit error counts.")

    def build(self):
        self.add_action("🚨 failed logins (today)", self.failed, primary=True)
        self.add_action("🛂 sudo events (today)",   self.sudo)
        self.add_action("🐧 kernel errors (today)", self.kernel)
        self.add_action("📊 top noisy units",       self.top_units)
        self.add_action("🌐 brute-force source IPs", self.brute_ips)

    def failed(self):
        rc, out = run_subprocess(
            ["journalctl","--since","today","-g","Failed password|authentication failure",
             "--no-pager","-q"], timeout=20)
        self.write(out or "(no failed logins today)")

    def sudo(self):
        rc, out = run_subprocess(
            ["journalctl","_COMM=sudo","--since","today","--no-pager","-q"], timeout=20)
        self.write(out or "(no sudo activity today)")

    def kernel(self):
        rc, out = run_subprocess(
            ["journalctl","-k","--since","today","-p","err","--no-pager","-q"], timeout=20)
        self.write(out or "(no kernel errors today)")

    def top_units(self):
        rc, out = run_subprocess(
            ["journalctl","--since","today","-p","err","-o","short-iso","--no-pager","-q"], timeout=20)
        units: Counter[str] = Counter()
        for line in out.splitlines():
            m = re.search(r"\b([\w.-]+)\[\d+\]:", line)
            if m: units[m.group(1)] += 1
        for unit, n in units.most_common(20):
            self.write(f"  {n:>6}  {unit}")

    def brute_ips(self):
        rc, out = run_subprocess(
            ["journalctl","--since","today","-g","Failed password","--no-pager","-q"], timeout=30)
        ips: Counter[str] = Counter()
        for line in out.splitlines():
            m = re.search(r"from\s+(\d+\.\d+\.\d+\.\d+)", line)
            if m: ips[m.group(1)] += 1
        for ip, n in ips.most_common(40):
            self.write(f"  {n:>6}  {ip}")
        if not ips: self.write("(no brute-force sources today)")
