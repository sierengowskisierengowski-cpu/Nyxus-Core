"""Module 07 — Attack Surface Mapper. ASN, subdomains, exposed services."""
from __future__ import annotations

import json
import socket
import urllib.request
import urllib.parse

from ui import BaseModule, run_subprocess
import db


class Page(BaseModule):
    NAME = "Attack Surface"
    ICON = "🗺"
    DESCRIPTION = ("Builds an attack-surface picture: WHOIS, ASN/BGP, reverse DNS, "
                   "crt.sh subdomain enum, public Shodan-style port hints (via Nmap).")

    def build(self):
        self.add_action("🌐 WHOIS",                 self.whois, primary=True)
        self.add_action("🌍 ASN / route",           self.asn)
        self.add_action("🔁 reverse DNS sweep",     self.reverse_dns)
        self.add_action("🌳 crt.sh subdomains",     self.crtsh)
        self.add_action("🚪 top-1000 ports",        self.top_ports)

    def whois(self):
        if not self.target or not self.need("whois"):
            return
        rc, out = run_subprocess(["whois", self.target], timeout=30)
        self.write(out)
        db.record_scan(self.NAME, self.target, "whois", "whois", f"rc={rc}")

    def asn(self):
        if not self.target:
            return
        try:
            ip = socket.gethostbyname(self.target.split("/")[0])
        except Exception as exc:
            self.write(f"resolve failed: {exc}")
            return
        # Team Cymru DNS-based ASN lookup (no install required)
        rev = ".".join(reversed(ip.split(".")))
        rc, out = run_subprocess(["dig","+short","TXT", f"{rev}.origin.asn.cymru.com"], timeout=10)
        self.write(f"IP {ip}\nASN: {out or '(unknown)'}")

    def reverse_dns(self):
        if not self.target:
            return
        # accept CIDR like 10.0.0.0/29 or single host
        if "/" in self.target:
            try:
                import ipaddress
                net = ipaddress.ip_network(self.target, strict=False)
                hosts = list(net.hosts())[:64]
            except Exception as exc:
                self.write(f"bad CIDR: {exc}"); return
        else:
            hosts = [self.target]
        for h in hosts:
            try:
                name, _aliases, _ips = socket.gethostbyaddr(str(h))
                self.write(f"  {h}  →  {name}")
            except Exception:
                self.write(f"  {h}  →  (no PTR)")

    def crtsh(self):
        if not self.target:
            return
        url = "https://crt.sh/?output=json&q=" + urllib.parse.quote("%."+self.target)
        self.write(f"GET {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"nyxus-godsapp/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.load(r)
        except Exception as exc:
            self.write(f"crt.sh error: {exc}"); return
        names = sorted({n.strip() for entry in data
                        for n in str(entry.get("name_value","")).splitlines()})
        for n in names[:200]:
            self.write(f"  {n}")
        self.write(f"\n{len(names)} unique subdomains")

    def top_ports(self):
        if not self.target or not self.need("nmap"):
            return
        cmd = ["nmap","-Pn","--top-ports","1000","-T4","-sV", self.target]
        self.write(f"$ {' '.join(cmd)}")
        rc, out = run_subprocess(cmd, timeout=600)
        self.write(out)
