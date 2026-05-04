"""Module 05 — Vulnerability Engine.

Wraps Nmap NSE vuln scripts, nikto, sslyze/sslscan, and the NVD CVE
search API. Findings persisted to the findings table with CVSS scores.
"""
from __future__ import annotations

import json
import re
import shutil
import urllib.parse
import urllib.request

from ui import BaseModule, run_subprocess, have
import db


NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={q}&resultsPerPage=15"


class Page(BaseModule):
    NAME = "Vulnerability Engine"
    ICON = "🛡"
    DESCRIPTION = ("Real CVE lookups via the NVD API + Nmap NSE vuln "
                   "library + nikto + sslscan. Findings stored with CVSS.")

    def build(self):
        self.add_action("🔍 Nmap vuln scripts",  self.action_nmap_vuln, primary=True)
        self.add_action("🌐 nikto web scan",     self.action_nikto)
        self.add_action("🔐 SSL/TLS audit",      self.action_ssl)
        self.add_action("📚 CVE search (NVD)",   self.action_cve)
        self.add_action("🧪 SMB checks",         self.action_smb)
        self.add_action("🗝  Default creds",      self.action_default_creds)
        self.add_action("📋 Findings",           self.action_findings)

    def action_nmap_vuln(self):
        if not self.target or not self.need("nmap"):
            return
        cmd = ["nmap","--script","vuln","-sV",self.target]
        self.write(f"$ {' '.join(cmd)}\n")
        rc, out = run_subprocess(cmd, timeout=900)
        self.write(out)
        sid = db.record_scan(self.NAME, self.target, "nmap-vuln",
                             " ".join(cmd), f"rc={rc}")
        # parse VULNERABLE / CVE-IDs
        for cve in set(re.findall(r"CVE-\d{4}-\d{4,7}", out)):
            db.add_finding(sid, "HIGH", f"CVE referenced: {cve}", cve=cve)

    def action_nikto(self):
        if not self.target or not self.need("nikto"):
            return
        target = self.target
        if not target.startswith(("http://","https://")):
            target = "http://" + target
        rc, out = run_subprocess(["nikto","-h",target,"-Tuning","x4567"], timeout=900)
        self.write(out)
        sid = db.record_scan(self.NAME, target, "nikto", "nikto", f"rc={rc}")
        for line in out.splitlines():
            if line.startswith("+ ") and any(k in line for k in ("OSVDB","CVE","vulnerable","disclosure")):
                sev = "HIGH" if "vulnerable" in line.lower() else "MED"
                db.add_finding(sid, sev, line[2:].strip())

    def action_ssl(self):
        if not self.target:
            return
        host, _, port = self.target.partition(":")
        port = port or "443"
        if shutil.which("sslscan"):
            rc, out = run_subprocess(["sslscan", f"{host}:{port}"], timeout=180)
        elif shutil.which("sslyze"):
            rc, out = run_subprocess(["sslyze", f"{host}:{port}"], timeout=180)
        elif shutil.which("nmap"):
            rc, out = run_subprocess(
                ["nmap","--script","ssl-enum-ciphers,ssl-cert,ssl-dh-params",
                 "-p",port,host], timeout=180
            )
        else:
            self.write("install sslscan / sslyze / nmap for SSL audit")
            return
        self.write(out)
        # quick weakness flagging
        for marker, sev in [("SSLv2","CRIT"),("SSLv3","CRIT"),("TLSv1.0","HIGH"),
                            ("RC4","HIGH"),("DES","HIGH"),("EXPORT","HIGH"),
                            ("MD5","MED"),("SHA1","MED"),("Heartbleed","CRIT"),
                            ("POODLE","CRIT"),("ROBOT","CRIT"),("BEAST","HIGH")]:
            if marker.lower() in out.lower():
                self.write(f"⚠  weakness: {marker} present")

    def action_cve(self):
        q = self.target or ""
        if not q:
            self.write("type a product/version in the target box (e.g. 'openssh 8.4')")
            return
        url = NVD_URL.format(q=urllib.parse.quote(q))
        self.write(f"GET {url}")
        try:
            req = urllib.request.Request(url, headers={"User-Agent":"nyxus-godsapp/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                data = json.load(r)
        except Exception as exc:
            self.write(f"NVD error: {exc}")
            return
        for entry in data.get("vulnerabilities", []):
            cve = entry["cve"]["id"]
            descs = entry["cve"].get("descriptions", [])
            d = next((x["value"] for x in descs if x["lang"]=="en"), "")
            metrics = entry["cve"].get("metrics", {})
            cvss = 0.0
            for k in ("cvssMetricV31","cvssMetricV30","cvssMetricV2"):
                if k in metrics:
                    try:
                        cvss = float(metrics[k][0]["cvssData"]["baseScore"])
                        break
                    except Exception:
                        pass
            db.cve_put(cve, cvss, d, [r["url"] for r in entry["cve"].get("references", [])])
            self.write(f"\n[{cvss:>4.1f}]  {cve}\n        {d[:200]}")

    def action_smb(self):
        if not self.target or not self.need("nmap"):
            return
        cmd = ["nmap","-p","139,445","--script",
               "smb-vuln-ms17-010,smb-vuln-cve-2017-7494,smb-vuln-cve2009-3103,"
               "smb-vuln-ms08-067,smb-protocols", self.target]
        self.write(f"$ {' '.join(cmd)}\n")
        rc, out = run_subprocess(cmd, timeout=300)
        self.write(out)

    def action_default_creds(self):
        if not self.target or not self.need("nmap"):
            return
        cmd = ["nmap","--script","http-default-accounts","-p","80,443,8080,8443",
               self.target]
        rc, out = run_subprocess(cmd, timeout=300)
        self.write(out)

    def action_findings(self):
        cur = db.conn().execute(
            "SELECT severity, title, cvss, cve FROM findings ORDER BY id DESC LIMIT 100"
        )
        for sev, title, cvss, cve in cur.fetchall():
            cvss_s = f"{cvss:>4.1f}" if cvss else "    "
            cve_s  = cve or ""
            self.write(f"[{sev:<5}] [{cvss_s}] {cve_s:<16} {title[:120]}")
