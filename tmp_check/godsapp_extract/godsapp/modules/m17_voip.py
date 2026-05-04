"""Module 17 — VoIP Security."""
from __future__ import annotations

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "VoIP"
    ICON = "📞"
    DESCRIPTION = ("SIP enumeration via Nmap NSE / svmap (sipvicious), RTP probes, "
                   "and basic call-quality / encryption checks.")

    def build(self):
        self.add_action("📞 SIP scan (Nmap NSE)", self.sip_nmap, primary=True)
        self.add_action("📞 svmap scan",          self.svmap)
        self.add_action("☎  SIP OPTIONS probe",   self.options)
        self.add_action("🔐 SRTP / TLS check",    self.srtp)

    def sip_nmap(self):
        if not self.target or not self.need("nmap"): return
        rc, out = run_subprocess(
            ["nmap","-sU","-sV","-p","5060,5061","--script","sip-enum-users,sip-methods", self.target],
            timeout=300)
        self.write(out)

    def svmap(self):
        if not self.target or not self.need("svmap"): return
        rc, out = run_subprocess(["svmap", self.target], timeout=120)
        self.write(out)

    def options(self):
        if not self.target: return
        rc, out = run_subprocess(["nmap","-sU","-p","5060","--script","sip-methods", self.target], timeout=60)
        self.write(out)

    def srtp(self):
        if not self.target or not self.need("nmap"): return
        rc, out = run_subprocess(
            ["nmap","-p","5061","--script","ssl-enum-ciphers,ssl-cert", self.target], timeout=120)
        self.write(out)
