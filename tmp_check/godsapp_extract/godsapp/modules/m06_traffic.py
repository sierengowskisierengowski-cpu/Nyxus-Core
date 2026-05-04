"""Module 06 — Traffic Intelligence. tcpdump + per-flow stats."""
from __future__ import annotations

import re
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path

from ui import BaseModule, run_subprocess
import db


class Page(BaseModule):
    NAME = "Traffic Intelligence"
    ICON = "📡"
    DESCRIPTION = ("Live tcpdump capture + per-talker / per-port flow stats. "
                   "Saves a rolling pcap to ~/.cache/nyxus-godsapp/.")

    def build(self):
        self.add_action("▶ 30 s capture", self.capture, primary=True)
        self.add_action("📊 Top talkers (last pcap)", self.top_talkers)
        self.add_action("🔎 DNS query log",  self.dns_log)
        self.add_action("⚠  Plaintext creds (telnet/ftp/http auth)", self.plain)

    def _iface(self) -> str:
        # default route iface
        try:
            r = subprocess.run(["ip","route","get","1.1.1.1"], capture_output=True, text=True, timeout=3)
            m = re.search(r"dev (\S+)", r.stdout)
            return m.group(1) if m else "any"
        except Exception:
            return "any"

    def capture(self):
        if not self.need("tcpdump"):
            return
        iface = self._iface()
        out_pcap = Path.home() / ".cache/nyxus-godsapp/last.pcap"
        cmd = ["tcpdump","-i",iface,"-w",str(out_pcap),"-G","30","-W","1"]
        self.write(f"$ {' '.join(cmd)}\n")
        rc, out = run_subprocess(cmd, timeout=45)
        self.write(out + f"\nsaved → {out_pcap}")
        db.record_scan(self.NAME, iface, "capture30", " ".join(cmd), f"rc={rc}", str(out_pcap))

    def top_talkers(self):
        pcap = Path.home() / ".cache/nyxus-godsapp/last.pcap"
        if not pcap.exists() or not self.need("tcpdump"):
            self.write("no capture yet — run a 30 s capture first")
            return
        rc, out = run_subprocess(["tcpdump","-r",str(pcap),"-nn","-q"], timeout=60)
        srcs: Counter[str] = Counter()
        for line in out.splitlines():
            m = re.search(r"IP6?\s+([\w:.]+)\s*[.:]\d+\s*>", line)
            if m: srcs[m.group(1)] += 1
        self.write("top 20 source IPs:")
        for ip, n in srcs.most_common(20):
            self.write(f"  {n:>6}  {ip}")

    def dns_log(self):
        if not self.need("tcpdump"):
            return
        iface = self._iface()
        rc, out = run_subprocess(
            ["tcpdump","-i",iface,"-nn","-c","100","port","53"], timeout=60
        )
        self.write(out)

    def plain(self):
        if not self.need("tcpdump"):
            return
        iface = self._iface()
        rc, out = run_subprocess(
            ["tcpdump","-i",iface,"-A","-c","50",
             "tcp port 21 or tcp port 23 or tcp port 80"], timeout=60
        )
        self.write(out)
        for line in out.splitlines():
            if any(k in line.lower() for k in ("password","user ","pass ","authorization:")):
                self.write(f"⚠  plaintext: {line[:140]}")
