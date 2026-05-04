"""Module 22 — Mobile Device Security."""
from __future__ import annotations

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "Mobile"
    ICON = "📱"
    DESCRIPTION = ("Android (adb) + iOS (libimobiledevice) inspection. Lists devices, "
                   "installed packages, debug-bridge security posture, MDM hints.")

    def build(self):
        self.add_action("📱 adb devices",         self.adb_devices, primary=True)
        self.add_action("📦 adb installed packages", self.adb_pkgs)
        self.add_action("🛂 adb dangerous perms", self.adb_perms)
        self.add_action("🍎 ideviceinfo",         self.ideviceinfo)
        self.add_action("🍎 ideviceinstaller -l", self.ideviceinstaller)

    def adb_devices(self):
        if not self.need("adb"): return
        rc, out = run_subprocess(["adb","devices","-l"], timeout=10); self.write(out)

    def adb_pkgs(self):
        if not self.need("adb"): return
        rc, out = run_subprocess(["adb","shell","pm","list","packages","-3"], timeout=30)
        self.write(out)

    def adb_perms(self):
        if not self.need("adb"): return
        rc, pkgs = run_subprocess(["adb","shell","pm","list","packages","-3"], timeout=30)
        for line in pkgs.splitlines()[:30]:
            pkg = line.replace("package:","").strip()
            rc, perms = run_subprocess(
                ["adb","shell","dumpsys","package", pkg], timeout=10)
            risky = [p for p in perms.splitlines() if "granted=true" in p and any(
                k in p.lower() for k in ("camera","location","contacts","sms","record_audio"))]
            if risky:
                self.write(f"\n--- {pkg} ---")
                for r in risky: self.write("  " + r.strip())

    def ideviceinfo(self):
        rc, out = run_subprocess(["ideviceinfo"], timeout=15)
        self.write(out or "libimobiledevice not installed")

    def ideviceinstaller(self):
        rc, out = run_subprocess(["ideviceinstaller","-l"], timeout=30)
        self.write(out or "ideviceinstaller not installed")
