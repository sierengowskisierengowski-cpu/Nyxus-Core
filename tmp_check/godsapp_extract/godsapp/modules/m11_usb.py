"""Module 11 — USB and Hardware Monitor."""
from __future__ import annotations

import time

from ui import BaseModule, run_subprocess
import db


class Page(BaseModule):
    NAME = "USB / Hardware"
    ICON = "🔌"
    DESCRIPTION = ("Live USB enumeration via lsusb / udevadm, BadUSB / mass-storage "
                   "warnings, dmesg device events, and PCI hardware inventory.")

    def build(self):
        self.add_action("📋 lsusb",                self.lsusb, primary=True)
        self.add_action("📜 dmesg (last 200)",     self.dmesg)
        self.add_action("🧷 udevadm monitor 30 s", self.udev)
        self.add_action("🖥 PCI devices",         self.pci)
        self.add_action("⚠  USBGuard policy",      self.usbguard)

    def lsusb(self):
        if not self.need("lsusb"):
            return
        rc, out = run_subprocess(["lsusb","-v"], timeout=20)
        self.write(out[:60000])
        rc, brief = run_subprocess(["lsusb"], timeout=10)
        self.write("\n--- summary ---\n" + brief)
        for line in brief.splitlines():
            parts = line.split()
            if len(parts) >= 6 and parts[0] == "Bus":
                vidpid = parts[5]
                desc = " ".join(parts[6:])
                db.see_device(vidpid.lower(), vendor=desc)

    def dmesg(self):
        rc, out = run_subprocess(["dmesg","-T","--ctime"], timeout=15)
        tail = "\n".join(out.splitlines()[-200:])
        self.write(tail)

    def udev(self):
        if not self.need("udevadm"):
            return
        # short non-blocking watch
        rc, out = run_subprocess(["timeout","30","udevadm","monitor","--udev"], timeout=35)
        self.write(out)

    def pci(self):
        if not self.need("lspci"):
            return
        rc, out = run_subprocess(["lspci","-vnn"], timeout=15)
        self.write(out)

    def usbguard(self):
        rc, out = run_subprocess(["usbguard","list-devices"], timeout=10)
        self.write(out or "usbguard not installed — `sudo pacman -S usbguard`")
