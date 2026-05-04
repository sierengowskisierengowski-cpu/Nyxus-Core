"""Module 04 — WiFi Arsenal.

Real wireless discovery via iwlist / iw, monitor-mode toggling via airmon-ng,
probe-request capture, evil-twin / deauth detection.
"""
from __future__ import annotations

import re
import shutil
import time
from pathlib import Path

from ui import BaseModule, run_subprocess, have


class Page(BaseModule):
    NAME = "WiFi Arsenal"
    ICON = "📶"
    DESCRIPTION = ("Wireless discovery, monitor-mode management, probe "
                   "requests, evil-twin / deauth detection. Aircrack-ng "
                   "suite when installed.")

    def build(self):
        self.add_action("📡 Scan APs",             self.action_scan, primary=True)
        self.add_action("🛰  Monitor mode ON",      self.action_mon_on)
        self.add_action("🔌 Monitor mode OFF",     self.action_mon_off)
        self.add_action("🐾 Probe requests",       self.action_probes)
        self.add_action("👯 Evil twin scan",       self.action_evil_twin)
        self.add_action("🔓 WPS-enabled APs",      self.action_wps)
        self.add_action("🚨 Deauth detector",      self.action_deauth)

    def _iface(self) -> str:
        rc, out = run_subprocess(["iw","dev"])
        m = re.search(r"Interface\s+(\S+)", out or "")
        return m.group(1) if m else "wlan0"

    def action_scan(self):
        if shutil.which("nmcli"):
            rc, out = run_subprocess(
                ["nmcli","-f","SSID,BSSID,CHAN,SIGNAL,SECURITY,FREQ","device","wifi","list","--rescan","yes"],
                timeout=20
            )
            self.write(out)
        elif shutil.which("iw"):
            iface = self._iface()
            rc, out = run_subprocess(["iw","dev",iface,"scan"], timeout=30)
            # condense to one line per BSSID
            ssid = bssid = sig = ch = ""
            for line in out.splitlines():
                line = line.strip()
                if line.startswith("BSS"):
                    if bssid:
                        self.write(f"{ssid:<30} {bssid:<18} ch={ch:<3} signal={sig}")
                    bssid = line.split()[1].split("(")[0]
                    ssid = sig = ch = ""
                elif line.startswith("SSID:"):
                    ssid = line[5:].strip()
                elif line.startswith("signal:"):
                    sig = line.split(":",1)[1].strip()
                elif line.startswith("freq:"):
                    ch = line.split(":",1)[1].strip()
            if bssid:
                self.write(f"{ssid:<30} {bssid:<18} ch={ch:<3} signal={sig}")
        else:
            self.write("install nmcli or iw")

    def action_mon_on(self):
        if not self.need("airmon-ng"):
            return
        iface = self._iface()
        rc, out = run_subprocess(["pkexec","airmon-ng","start",iface], timeout=20)
        self.write(out)

    def action_mon_off(self):
        if not self.need("airmon-ng"):
            return
        rc, out = run_subprocess(["pkexec","airmon-ng","stop",f"{self._iface()}mon"], timeout=20)
        self.write(out)

    def action_probes(self):
        # Tier 1: airodump-ng if monitor available, otherwise tshark on phy
        if shutil.which("airodump-ng"):
            iface = self._iface() + "mon"
            self.write(f"capturing probes on {iface} for 30s …")
            rc, out = run_subprocess(["timeout","30","airodump-ng",iface,"--output-format","csv","--write","/tmp/probes"],
                                     timeout=40)
            self.write(out[-3000:])
        elif shutil.which("tshark"):
            iface = self._iface()
            self.write(f"capturing 30s with tshark probe-req filter on {iface} …")
            rc, out = run_subprocess(
                ["timeout","30","tshark","-i",iface,"-Y","wlan.fc.type_subtype==4",
                 "-T","fields","-e","wlan.sa","-e","wlan_mgt.ssid"],
                timeout=40
            )
            self.write(out)
        else:
            self.write("install aircrack-ng or wireshark for probe capture")

    def action_evil_twin(self):
        if not self.need("nmcli"):
            return
        rc, out = run_subprocess(["nmcli","-f","SSID,BSSID","-t","device","wifi","list"], timeout=15)
        seen: dict[str, list[str]] = {}
        for line in out.splitlines():
            parts = line.split(":", 1)
            if len(parts) != 2:
                continue
            ssid, bssid = parts
            seen.setdefault(ssid, []).append(bssid)
        flagged = {k: v for k, v in seen.items() if len(v) > 1 and k}
        if not flagged:
            self.write("no duplicate-SSID APs in scan range")
            return
        self.write("⚠  potential evil twins (same SSID, different BSSID):")
        for ssid, bssids in flagged.items():
            self.write(f"  {ssid}")
            for b in bssids:
                self.write(f"    · {b}")

    def action_wps(self):
        if shutil.which("wash"):
            iface = self._iface() + "mon"
            rc, out = run_subprocess(["timeout","20","wash","-i",iface], timeout=25)
            self.write(out)
        elif shutil.which("nmcli"):
            rc, out = run_subprocess(["nmcli","-f","SSID,WPA-FLAGS,WPS","device","wifi","list"], timeout=15)
            self.write(out)
        else:
            self.write("install reaver/wash for WPS detection")

    def action_deauth(self):
        if not have("tshark"):
            self.write("install tshark for deauth detection")
            return
        iface = self._iface()
        self.write(f"watching for deauth frames on {iface} for 30s …")
        rc, out = run_subprocess(
            ["timeout","30","tshark","-i",iface,"-Y","wlan.fc.type_subtype==12",
             "-T","fields","-e","wlan.sa","-e","wlan.da","-e","wlan.fixed.reason_code"],
            timeout=40
        )
        if not out.strip():
            self.write("no deauth frames seen — calm waters")
        else:
            self.write(out)
