"""Module 29 — God Mode Master Dashboard."""
from __future__ import annotations

import time

from ui import BaseModule, run_subprocess
import db


class Page(BaseModule):
    NAME = "✦ GOD MODE"
    ICON = "✦"
    DESCRIPTION = ("One-button master scan. Runs a curated subset of modules against the "
                   "target box and aggregates findings into a single dashboard.")

    SEQUENCE = [
        ("WHOIS",        ["whois"]),
        ("DNS records",  ["dig","+short","ANY"]),
        ("Top 1000 ports + versions", ["nmap","-Pn","--top-ports","1000","-sV","-T4"]),
        ("OS guess",     ["nmap","-Pn","-O","--osscan-guess"]),
        ("Vuln scripts", ["nmap","--script","vuln","-sV"]),
        ("HTTP banner",  ["curl","-sI","--max-time","10"]),
    ]

    def build(self):
        self.add_action("✦ RUN GOD MODE",        self.go, primary=True)
        self.add_action("📊 dashboard summary",   self.dashboard)
        self.add_action("📋 last 50 findings",   self.findings)

    def go(self):
        if not self.target:
            self.write("type a target in the box first"); return
        self.write(f"=== GOD MODE START ({time.strftime('%H:%M:%S')}) — target {self.target} ===\n")
        for label, cmd in self.SEQUENCE:
            self.write(f"\n--- {label} ---")
            full = list(cmd) + [self.target]
            rc, out = run_subprocess(full, timeout=600)
            self.write(out[:8000])
            db.record_scan("GOD MODE", self.target, label, " ".join(full), f"rc={rc}")
        self.write(f"\n=== GOD MODE COMPLETE ({time.strftime('%H:%M:%S')}) ===")

    def dashboard(self):
        c = db.conn()
        scans = c.execute("SELECT COUNT(*) FROM scans").fetchone()[0]
        finds = c.execute("SELECT COUNT(*) FROM findings").fetchone()[0]
        crit  = c.execute("SELECT COUNT(*) FROM findings WHERE severity IN ('CRIT','HIGH')").fetchone()[0]
        cves  = c.execute("SELECT COUNT(*) FROM cve_cache").fetchone()[0]
        devs  = c.execute("SELECT COUNT(*) FROM device_history").fetchone()[0]
        self.write(f"scans recorded   : {scans}")
        self.write(f"findings total   : {finds}")
        self.write(f"  CRIT/HIGH      : {crit}")
        self.write(f"CVEs cached      : {cves}")
        self.write(f"devices observed : {devs}")
        self.write("\nrecent scans:")
        for r in db.list_recent_scans(10):
            ts = time.strftime("%H:%M:%S", time.localtime(r["ts"]))
            self.write(f"  {ts}  {r['module']:<20} {r['target'] or '':<25} {r['summary'] or ''}")

    def findings(self):
        cur = db.conn().execute(
            "SELECT severity, title, cvss, cve FROM findings ORDER BY id DESC LIMIT 50")
        for sev, title, cvss, cve in cur.fetchall():
            self.write(f"[{sev:<5}] {cvss or 0:>4.1f}  {cve or '':<16}  {title[:120]}")
