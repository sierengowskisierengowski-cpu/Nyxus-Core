"""Module 18 — Industrial / SCADA / IoT."""
from __future__ import annotations

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "SCADA / ICS"
    ICON = "🏭"
    DESCRIPTION = ("Modbus, S7, BACnet, DNP3 and EtherNet/IP enumeration via Nmap NSE. "
                   "READ-ONLY identity probes — never sends control writes.")

    def build(self):
        self.add_action("⚙  Modbus discover (502)", self.modbus, primary=True)
        self.add_action("🏭 Siemens S7 (102)",       self.s7)
        self.add_action("🌡  BACnet (47808/UDP)",    self.bacnet)
        self.add_action("⚡ EtherNet/IP (44818)",     self.enip)
        self.add_action("📡 DNP3 (20000)",           self.dnp3)
        self.add_action("🌐 IoT banners (top 100 ports)", self.banners)

    def modbus(self):
        if not self.target or not self.need("nmap"): return
        rc, out = run_subprocess(
            ["nmap","-p","502","--script","modbus-discover", self.target], timeout=120)
        self.write(out)

    def s7(self):
        if not self.target or not self.need("nmap"): return
        rc, out = run_subprocess(
            ["nmap","-p","102","--script","s7-info", self.target], timeout=120)
        self.write(out)

    def bacnet(self):
        if not self.target or not self.need("nmap"): return
        rc, out = run_subprocess(
            ["nmap","-sU","-p","47808","--script","bacnet-info", self.target], timeout=120)
        self.write(out)

    def enip(self):
        if not self.target or not self.need("nmap"): return
        rc, out = run_subprocess(
            ["nmap","-p","44818","--script","enip-info", self.target], timeout=120)
        self.write(out)

    def dnp3(self):
        if not self.target or not self.need("nmap"): return
        rc, out = run_subprocess(
            ["nmap","-p","20000","--script","dnp3-info", self.target], timeout=120)
        self.write(out)

    def banners(self):
        if not self.target or not self.need("nmap"): return
        rc, out = run_subprocess(["nmap","-sV","--top-ports","100","--version-intensity","2", self.target],
                                  timeout=600)
        self.write(out)
