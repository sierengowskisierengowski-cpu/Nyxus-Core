"""Module 24 — Physical Security."""
from __future__ import annotations

from pathlib import Path

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "Physical Security"
    ICON = "🔒"
    DESCRIPTION = ("Webcam / mic exposure, kernel-locked-down state, secure-boot, "
                   "TPM presence, BIOS security, port and lid sensor checks.")

    def build(self):
        self.add_action("📷 video / mic devices",  self.video_mic, primary=True)
        self.add_action("🛡  Secure Boot status",   self.secboot)
        self.add_action("🧷 TPM presence",          self.tpm)
        self.add_action("🔧 BIOS / DMI",            self.dmi)
        self.add_action("🐧 kernel lockdown",       self.lockdown)
        self.add_action("🔌 USB port count",        self.usbports)

    def video_mic(self):
        for d in sorted(Path("/dev").glob("video*")):
            self.write(f"video device: {d}")
        for d in sorted(Path("/proc/asound").glob("card*")):
            self.write(f"audio card  : {d.name}")
        rc, out = run_subprocess(["arecord","-l"], timeout=10); self.write(out)

    def secboot(self):
        rc, out = run_subprocess(["mokutil","--sb-state"], timeout=5)
        self.write(out or "mokutil not present")
        rc, out = run_subprocess(["bootctl","status"], timeout=5)
        self.write(out)

    def tpm(self):
        for d in ("/dev/tpm0","/dev/tpmrm0"):
            self.write(f"{d}: {'present' if Path(d).exists() else 'absent'}")
        rc, out = run_subprocess(["tpm2_getcap","properties-fixed"], timeout=10)
        if out: self.write(out[:4000])

    def dmi(self):
        rc, out = run_subprocess(
            ["bash","-c","sudo -n dmidecode -t bios -t system -t chassis 2>&1 || dmidecode -t bios -t system -t chassis 2>&1"],
            timeout=15)
        self.write(out)

    def lockdown(self):
        try:
            self.write("kernel lockdown: " + Path("/sys/kernel/security/lockdown").read_text().strip())
        except Exception as e:
            self.write(f"(unavailable: {e})")

    def usbports(self):
        rc, out = run_subprocess(["lsusb"], timeout=10)
        self.write(out)
        self.write(f"\n{len(out.splitlines())} USB devices currently enumerated")
