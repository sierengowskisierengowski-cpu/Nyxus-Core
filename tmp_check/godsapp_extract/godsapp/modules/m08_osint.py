"""Module 08 — OSINT Engine."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request

from ui import BaseModule, run_subprocess
import db


class Page(BaseModule):
    NAME = "OSINT Engine"
    ICON = "🕵"
    DESCRIPTION = ("Open-source intelligence collection: DNS records, WHOIS, "
                   "Wayback Machine snapshots, GitHub mentions, email harvesting via dorks.")

    def build(self):
        self.add_action("📜 DNS records (all)",   self.dns_all, primary=True)
        self.add_action("🕰  Wayback snapshots",   self.wayback)
        self.add_action("📨 email patterns",      self.emails)
        self.add_action("🐙 GitHub mentions",     self.github)
        self.add_action("📰 dork: PDFs",          lambda: self.dork("filetype:pdf"))
        self.add_action("📰 dork: index of",      lambda: self.dork("intitle:\"index of\""))

    def dns_all(self):
        if not self.target or not self.need("dig"):
            return
        for rt in ("A","AAAA","MX","NS","TXT","SOA","CAA","SRV"):
            rc, out = run_subprocess(["dig","+short", rt, self.target], timeout=10)
            self.write(f"--- {rt} ---\n{out or '(none)'}")
        db.record_scan(self.NAME, self.target, "dns", "dig", "ok")

    def wayback(self):
        if not self.target:
            return
        url = ("http://web.archive.org/cdx/search/cdx?output=json&fl=timestamp,original"
               f"&limit=50&url={urllib.parse.quote(self.target)}")
        try:
            with urllib.request.urlopen(url, timeout=20) as r:
                rows = json.load(r)
        except Exception as exc:
            self.write(f"wayback error: {exc}"); return
        for row in rows[1:]:
            self.write(f"  {row[0]}  {row[1][:120]}")

    def emails(self):
        if not self.target:
            return
        # google dork via duckduckgo lite (no JS)
        q = f'site:{self.target} ("@" OR "email" OR "contact")'
        try:
            req = urllib.request.Request(
                "https://duckduckgo.com/html/?q="+urllib.parse.quote(q),
                headers={"User-Agent":"nyxus-godsapp/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                html = r.read(200000).decode("utf8","ignore")
        except Exception as exc:
            self.write(f"search error: {exc}"); return
        emails = sorted(set(re.findall(r"[A-Za-z0-9._%+-]+@"+re.escape(self.target), html)))
        for e in emails:
            self.write(f"  {e}")
        if not emails:
            self.write("(no emails matched the target domain in first page)")

    def github(self):
        if not self.target:
            return
        url = "https://api.github.com/search/code?q=" + urllib.parse.quote(self.target)
        try:
            req = urllib.request.Request(url, headers={"Accept":"application/vnd.github+json",
                                                        "User-Agent":"nyxus-godsapp/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.load(r)
        except Exception as exc:
            self.write(f"github error (rate-limit?): {exc}"); return
        for item in data.get("items", [])[:30]:
            self.write(f"  {item['repository']['full_name']:<40}  {item['path']}")

    def dork(self, fragment: str):
        if not self.target:
            return
        q = f"site:{self.target} {fragment}"
        url = "https://duckduckgo.com/html/?q=" + urllib.parse.quote(q)
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"nyxus-godsapp/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                html = r.read(200000).decode("utf8","ignore")
        except Exception as exc:
            self.write(f"dork error: {exc}"); return
        for m in re.finditer(r'<a [^>]*class="result__a"[^>]*href="([^"]+)"', html):
            self.write(f"  {m.group(1)[:160]}")
