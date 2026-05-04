"""Module 03 — Packet Capture & Analysis.

Live capture via tcpdump / pyshark. Interface picker, BPF filter helpers,
protocol distribution, plaintext credential extraction, conversation
matrix. PCAP files written to ~/.cache/nyxus-godsapp/captures/.
"""
from __future__ import annotations

import shutil
import time
from collections import Counter, defaultdict
from pathlib import Path

from ui import BaseModule, run_subprocess, have


CAP_DIR = Path.home() / ".cache" / "nyxus-godsapp" / "captures"
CAP_DIR.mkdir(parents=True, exist_ok=True)


class Page(BaseModule):
    NAME = "Packet Capture & Analysis"
    ICON = "📡"
    DESCRIPTION = ("Live packet capture (tcpdump / pyshark) with deep "
                   "inspection, plaintext-credential surfacing, and "
                   "protocol-distribution stats.")

    def build(self):
        self.add_action("📥 Quick 10s capture",    self.action_quick, primary=True)
        self.add_action("🔍 Capture HTTP only",    self.action_http)
        self.add_action("📞 Capture VoIP (RTP)",   self.action_voip)
        self.add_action("🗝  Plaintext creds scan", self.action_creds)
        self.add_action("📊 Protocol stats",       self.action_stats)
        self.add_action("💬 Conversation matrix",  self.action_matrix)
        self.add_action("📂 Open captures dir",    self.action_open_dir)
        self.add_action("📥 Import existing PCAP", self.action_import)

    def _iface(self) -> str:
        rc, out = run_subprocess(["ip","route","show","default"])
        for line in out.splitlines():
            tok = line.split()
            if "dev" in tok:
                return tok[tok.index("dev") + 1]
        return "any"

    def _capture(self, bpf: str = "", duration: int = 10) -> Path | None:
        if not self.need("tcpdump"):
            return None
        path = CAP_DIR / f"cap_{int(time.time())}.pcap"
        cmd = ["tcpdump","-i",self._iface(),"-w",str(path),"-G",str(duration),"-W","1"]
        if bpf:
            cmd.append(bpf)
        self.write(f"$ {' '.join(cmd)}\n  capturing for {duration}s on {self._iface()} …")
        rc, out = run_subprocess(cmd, timeout=duration + 10)
        if path.exists():
            self.write(f"saved → {path}  ({path.stat().st_size:,} bytes)")
            return path
        self.write(out)
        return None

    def action_quick(self):
        self._capture(duration=10)

    def action_http(self):
        self._capture(bpf="tcp port 80 or tcp port 8080", duration=20)

    def action_voip(self):
        self._capture(bpf="udp portrange 10000-20000 or port 5060", duration=30)

    def action_creds(self):
        path = self._capture(duration=15)
        if not path:
            return
        # use tshark to extract auth-bearing fields
        if not have("tshark"):
            self.write("\ninstall tshark for credential extraction")
            return
        for kind, fields in [
            ("HTTP basic auth", "http.authorization"),
            ("HTTP cookies",    "http.cookie"),
            ("FTP creds",       "ftp.request.command,ftp.request.arg"),
            ("Telnet",          "telnet.data"),
            ("POP3",            "pop"),
            ("SMTP",            "smtp.req.parameter"),
        ]:
            self.write(f"\n=== {kind} ===")
            cmd = ["tshark","-r",str(path),"-Y",fields.split(",")[0].split(".")[0],
                   "-T","fields"]
            for f in fields.split(","):
                cmd += ["-e", f]
            rc, out = run_subprocess(cmd, timeout=30)
            self.write(out.strip() or "  (none)")

    def action_stats(self):
        path = self._capture(duration=10)
        if not path:
            return
        if not have("tshark"):
            self.write("install tshark for protocol stats")
            return
        rc, out = run_subprocess(
            ["tshark","-r",str(path),"-q","-z","io,phs"], timeout=60
        )
        self.write(out)

    def action_matrix(self):
        path = self._capture(duration=10)
        if not path:
            return
        if not have("tshark"):
            self.write("install tshark for conversation matrix")
            return
        rc, out = run_subprocess(
            ["tshark","-r",str(path),"-q","-z","conv,ip"], timeout=60
        )
        self.write(out)

    def action_open_dir(self):
        self.write(f"captures live in: {CAP_DIR}\n")
        for f in sorted(CAP_DIR.iterdir(), reverse=True)[:30]:
            self.write(f"  {f.name:<40} {f.stat().st_size:>10,} bytes  "
                       f"{time.strftime('%Y-%m-%d %H:%M', time.localtime(f.stat().st_mtime))}")

    def action_import(self):
        self.write("place a .pcap file in:")
        self.write(f"  {CAP_DIR}")
        self.write("then use 'Plaintext creds scan' / 'Protocol stats' / 'Conversation matrix' "
                   "(they always operate on the most recent capture).")
