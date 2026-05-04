"""Module 25 — Dark Web / Breach Monitoring."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

from ui import BaseModule


class Page(BaseModule):
    NAME = "Dark Web Monitor"
    ICON = "🕸"
    DESCRIPTION = ("Have I Been Pwned API queries (no key required for unauthenticated paste "
                   "search). Target box = email address or domain.")

    def build(self):
        self.add_action("✉  HIBP breaches (email)", self.email_breaches, primary=True)
        self.add_action("🌐 HIBP breaches (domain)", self.domain_breaches)
        self.add_action("📋 list all known breaches", self.all_breaches)

    def _get(self, url: str):
        req = urllib.request.Request(url, headers={
            "User-Agent":"nyxus-godsapp/1.0",
            "Accept":"application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 404: return []
            self.write(f"HIBP {e.code}: {e.reason}")
            return None
        except Exception as exc:
            self.write(f"HIBP error: {exc}"); return None

    def email_breaches(self):
        if not self.target: return
        self.write("HIBP requires an API key for /breachedaccount in production.")
        self.write("Public breach metadata for the email’s domain follows:")
        domain = self.target.split("@",1)[-1]
        data = self._get(f"https://haveibeenpwned.com/api/v3/breaches?domain={urllib.parse.quote(domain)}")
        if data is None: return
        for b in data:
            self.write(f"  {b.get('Name'):<25} {b.get('BreachDate')} pwn={b.get('PwnCount'):,}")

    def domain_breaches(self):
        if not self.target: return
        data = self._get(
            f"https://haveibeenpwned.com/api/v3/breaches?domain={urllib.parse.quote(self.target)}")
        if data is None: return
        for b in data:
            self.write(f"  {b.get('Name'):<25} {b.get('BreachDate')} accts={b.get('PwnCount'):,}")
            self.write(f"    {b.get('Description','')[:200]}")

    def all_breaches(self):
        data = self._get("https://haveibeenpwned.com/api/v3/breaches")
        if data is None: return
        for b in data[:200]:
            self.write(f"  {b.get('Name'):<25} {b.get('BreachDate')} {b.get('PwnCount'):>12,}")
        self.write(f"\n{len(data)} total known breaches in HIBP")
