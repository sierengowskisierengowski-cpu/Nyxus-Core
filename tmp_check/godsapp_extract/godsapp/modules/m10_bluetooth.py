"""Module 10 — Bluetooth Scanner."""
from __future__ import annotations

from ui import BaseModule, run_subprocess
import db


class Page(BaseModule):
    NAME = "Bluetooth"
    ICON = "📶"
    DESCRIPTION = ("Bluetooth Classic + BLE discovery via bluetoothctl / hcitool / btmgmt. "
                   "Lists devices, services, and weak/legacy pairing modes.")

    def build(self):
        self.add_action("📡 scan 30 s",            self.scan, primary=True)
        self.add_action("🔎 BLE scan (bluetoothctl)", self.ble)
        self.add_action("🛰 inquiry (hcitool)",   self.hcitool)
        self.add_action("📋 paired devices",       self.paired)
        self.add_action("🔧 controllers / status", self.status)

    def status(self):
        rc, out = run_subprocess(["bluetoothctl","show"], timeout=10)
        self.write(out)

    def scan(self):
        if not self.need("bluetoothctl"):
            return
        rc, out = run_subprocess(
            ["bluetoothctl","--timeout","30","scan","on"], timeout=45)
        self.write(out)
        rc, devs = run_subprocess(["bluetoothctl","devices"], timeout=10)
        self.write("\n--- discovered ---\n" + devs)
        for line in devs.splitlines():
            parts = line.split(maxsplit=2)
            if len(parts) == 3 and parts[0] == "Device":
                db.see_device(parts[1].lower(), hostname=parts[2], vendor="bt")

    def ble(self):
        if not self.need("bluetoothctl"):
            return
        rc, out = run_subprocess(
            ["bluetoothctl","--timeout","20","scan","le"], timeout=30)
        self.write(out)

    def hcitool(self):
        if not self.need("hcitool"):
            return
        rc, out = run_subprocess(["hcitool","scan"], timeout=20)
        self.write(out)
        rc, out = run_subprocess(["hcitool","inq"], timeout=20)
        self.write("\n--- inquiry ---\n" + out)

    def paired(self):
        rc, out = run_subprocess(["bluetoothctl","paired-devices"], timeout=10)
        self.write(out or "(none paired)")
