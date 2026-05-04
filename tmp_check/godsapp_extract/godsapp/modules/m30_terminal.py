"""Module 30 — Built-in Terminal."""
from __future__ import annotations

import shlex

from ui import BaseModule, run_subprocess

ALLOWED_PREFIXES = (
    "nmap","dig","whois","curl","ip","ss","ping","traceroute","tcpdump","arp","arp-scan",
    "nikto","gobuster","dirb","sqlmap","wapiti","searchsploit","clamscan","yara","strings",
    "file","openssl","gpg","journalctl","dmesg","lsusb","lspci","lsmod","systemctl","ufw",
    "iptables","nft","mokutil","bootctl","dmidecode","tpm2_getcap","aws","gcloud","az",
    "adb","ideviceinfo","ideviceinstaller","setoolkit","mmls","fls","vol","echo","cat",
    "ls","head","tail","wc","sort","uniq","grep","awk","sed","ps","top","htop","uname",
    "hostnamectl","ip-route","ip-link","ip-addr","ip-neigh"
)


class Page(BaseModule):
    NAME = "Terminal"
    ICON = "💻"
    DESCRIPTION = ("Run security tools directly from inside GodsApp. Output is captured "
                   "to the pane and recorded in the scan database. Allow-listed binaries only.")

    def build(self):
        self.input = self.target  # not used; we use the global target box as command
        self.add_action("▶ run command (target box)", self.run_cmd, primary=True)
        for preset in (
            "nmap -sV --top-ports 100 192.168.1.1",
            "dig +short example.com ANY",
            "ss -tulpn",
            "journalctl -p err --since today",
            "ip -br addr",
            "ufw status verbose",
            "lsusb",
        ):
            self.add_action(f"📋 {preset}", lambda c=preset: self.run_preset(c))

    def _allowed(self, cmd_list: list[str]) -> bool:
        if not cmd_list: return False
        bin_name = cmd_list[0].split("/")[-1]
        return any(bin_name == p or bin_name.startswith(p+"-") for p in ALLOWED_PREFIXES)

    def run_cmd(self):
        cmd = self.target.strip()
        if not cmd:
            self.write("type a command in the target box, e.g.  nmap -sV scanme.nmap.org")
            return
        try:
            parts = shlex.split(cmd)
        except ValueError as e:
            self.write(f"parse error: {e}"); return
        if not self._allowed(parts):
            self.write(f"⚠  blocked: '{parts[0]}' is not on the allow-list.\n"
                        f"Allow-list: {', '.join(ALLOWED_PREFIXES[:30])}…")
            return
        self.write(f"$ {cmd}")
        rc, out = run_subprocess(parts, timeout=600)
        self.write(out + f"\n[exit {rc}]")
        import db
        db.record_scan(self.NAME, "", "terminal", cmd, f"rc={rc}")

    def run_preset(self, cmd: str):
        # temporarily override
        old = self.app.target_input.get_text() if self.app else ""
        self.app.target_input.set_text(cmd)
        try:
            self.run_cmd()
        finally:
            self.app.target_input.set_text(old)
