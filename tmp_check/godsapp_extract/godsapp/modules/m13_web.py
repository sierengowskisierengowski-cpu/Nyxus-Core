"""Module 13 — Web Application Scanner."""
from __future__ import annotations

import shutil

from ui import BaseModule, run_subprocess
import db


class Page(BaseModule):
    NAME = "Web Scanner"
    ICON = "🌐"
    DESCRIPTION = ("nikto, dirb / gobuster, wapiti, sqlmap baseline + WAF detection. "
                   "Flags missing security headers and weak TLS.")

    def build(self):
        self.add_action("🌐 nikto",          self.nikto, primary=True)
        self.add_action("📁 gobuster dir",   self.gobuster)
        self.add_action("📁 dirb",           self.dirb)
        self.add_action("🕷  wapiti",         self.wapiti)
        self.add_action("💉 sqlmap (-u)",    self.sqlmap)
        self.add_action("🛡  WAF detect",     self.wafw00f)
        self.add_action("📋 security headers", self.headers)

    def _u(self) -> str:
        t = self.target
        if not t.startswith(("http://","https://")): t = "http://"+t
        return t

    def nikto(self):
        if not self.target or not self.need("nikto"): return
        rc, out = run_subprocess(["nikto","-h",self._u()], timeout=900); self.write(out)
        db.record_scan(self.NAME, self.target, "nikto", "nikto", f"rc={rc}")

    def gobuster(self):
        if not self.target or not self.need("gobuster"): return
        wl = "/usr/share/wordlists/dirb/common.txt"
        rc, out = run_subprocess(["gobuster","dir","-q","-u",self._u(),"-w",wl,"-t","30"], timeout=600)
        self.write(out)

    def dirb(self):
        if not self.target or not self.need("dirb"): return
        rc, out = run_subprocess(["dirb", self._u()], timeout=600); self.write(out)

    def wapiti(self):
        if not self.target or not self.need("wapiti"): return
        rc, out = run_subprocess(["wapiti","-u",self._u(),"-f","txt","-o","/tmp/wapiti"], timeout=900)
        self.write(out)

    def sqlmap(self):
        if not self.target or not self.need("sqlmap"): return
        rc, out = run_subprocess(["sqlmap","-u",self._u(),"--batch","--crawl","2","--level","2"], timeout=900)
        self.write(out)

    def wafw00f(self):
        if not self.target: return
        if shutil.which("wafw00f"):
            rc, out = run_subprocess(["wafw00f", self._u()], timeout=60); self.write(out)
        else:
            self.write("install wafw00f for WAF detection")

    def headers(self):
        if not self.target: return
        import urllib.request
        try:
            req = urllib.request.Request(self._u(), headers={"User-Agent":"nyxus-godsapp/1.0"})
            r = urllib.request.urlopen(req, timeout=15)
            hdrs = dict(r.headers)
        except Exception as exc:
            self.write(f"error: {exc}"); return
        recommended = ["Strict-Transport-Security","Content-Security-Policy","X-Frame-Options",
                       "X-Content-Type-Options","Referrer-Policy","Permissions-Policy"]
        self.write("--- response headers ---")
        for k,v in hdrs.items(): self.write(f"  {k}: {v}")
        self.write("\n--- missing recommended ---")
        for h in recommended:
            if h not in hdrs: self.write(f"  ⚠  missing: {h}")
