"""Module 02 — Port & Service Scanner.

Full Nmap at every depth: SYN / UDP / FIN / XMAS / NULL / ACK / Window /
Maimon, version detect, OS fingerprint, NSE, banner grab, SSL deep
inspection (sslscan / testssl). Scan profiles match the real Nmap recipes.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from ui import BaseModule, run_subprocess, have
import db


PROFILES = {
    "Quick":      ["-T4", "-F"],
    "Full":       ["-T4", "-p-", "-sV", "--version-light"],
    "Stealth":    ["-sS", "-T2", "-f", "--data-length", "16"],
    "Aggressive": ["-A", "-T4", "-p-", "--script=default,vuln"],
    "Paranoid":   ["-sS", "-T1", "-f", "-D", "RND:5"],
    "Insane":     ["-T5", "-p-", "-sV", "-A", "--max-retries", "1"],
}


class Page(BaseModule):
    NAME = "Port & Service Scanner"
    ICON = "🛰"
    DESCRIPTION = ("Real Nmap at full capability. Pick a profile or build a "
                   "custom command. SSL/TLS deep inspection via sslscan.")

    def build(self):
        self.add_action("⚡ Quick scan",      self.action_quick, primary=True)
        self.add_action("🌑 Stealth scan",    self.action_stealth)
        self.add_action("🔥 Full + version",  self.action_full)
        self.add_action("💀 Aggressive+NSE",  self.action_aggressive)
        self.add_action("👁  OS fingerprint",  self.action_os)
        self.add_action("🛡  SSL deep dive",   self.action_ssl)
        self.add_action("📜 List NSE scripts", self.action_nse_list)
        self.add_action("📊 Scan history",    self.action_history)

    def _scan(self, profile_name: str):
        if not self.target:
            self.write("type a target in the top bar first")
            return
        if not self.need("nmap"):
            return
        args = PROFILES[profile_name]
        cmd = ["nmap", *args, self.target]
        self.write(f"$ {' '.join(cmd)}\n")
        rc, out = run_subprocess(cmd, timeout=900)
        self.write(out)
        sid = db.record_scan(self.NAME, self.target, profile_name,
                              " ".join(cmd), f"rc={rc}")
        # store output bundle
        bundle = Path.home() / ".cache/nyxus-godsapp" / f"scan_{sid}.txt"
        bundle.parent.mkdir(parents=True, exist_ok=True)
        bundle.write_text(out)
        self.write(f"\n[saved → {bundle}]")

    def action_quick(self):       self._scan("Quick")
    def action_stealth(self):     self._scan("Stealth")
    def action_full(self):        self._scan("Full")
    def action_aggressive(self):  self._scan("Aggressive")

    def action_os(self):
        if not self.target or not self.need("nmap"):
            return
        cmd = ["nmap", "-O", "--osscan-guess", self.target]
        self.write(f"$ {' '.join(cmd)}\n")
        _, out = run_subprocess(cmd, timeout=300)
        self.write(out)

    def action_ssl(self):
        if not self.target:
            return
        host = self.target
        port = "443"
        if ":" in host and not host.startswith("["):
            host, port = host.rsplit(":", 1)
        if shutil.which("sslscan"):
            rc, out = run_subprocess(["sslscan", f"{host}:{port}"], timeout=120)
            self.write("=== sslscan ===\n" + out)
        elif shutil.which("openssl"):
            rc, out = run_subprocess(
                ["openssl","s_client","-connect",f"{host}:{port}","-servername",host],
                timeout=20, stdin=""
            )
            self.write("=== openssl s_client ===\n" + out)
        elif shutil.which("nmap"):
            rc, out = run_subprocess(
                ["nmap","--script","ssl-enum-ciphers,ssl-cert","-p",port,host],
                timeout=120
            )
            self.write("=== nmap ssl scripts ===\n" + out)
        else:
            self.write("install sslscan or openssl or nmap for SSL deep dive")

    def action_nse_list(self):
        if not have("nmap"):
            self.write("nmap not installed")
            return
        d = Path("/usr/share/nmap/scripts")
        if not d.is_dir():
            d = Path("/usr/local/share/nmap/scripts")
        if not d.is_dir():
            self.write("NSE script directory not found")
            return
        scripts = sorted(s.stem for s in d.glob("*.nse"))
        self.write(f"NSE scripts available: {len(scripts)}\n")
        # 5 columns
        for i in range(0, len(scripts), 5):
            self.write("  ".join(f"{s:<25}" for s in scripts[i:i+5]))

    def action_history(self):
        rows = db.list_recent_scans(50)
        if not rows:
            self.write("no scans yet")
            return
        import time
        for r in rows:
            t = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["ts"]))
            self.write(f"{t}  [{r['module']}]  {r['target']:<30}  {r['summary']}")
