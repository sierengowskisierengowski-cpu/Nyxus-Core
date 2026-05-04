"""Module 12 — Active Directory and Network Services."""
from __future__ import annotations

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "AD / NetServices"
    ICON = "🏛"
    DESCRIPTION = ("SMB / NetBIOS / LDAP / Kerberos enumeration with smbclient, "
                   "rpcclient, ldapsearch, and Nmap NSE AD scripts.")

    def build(self):
        self.add_action("📡 SMB enum (Nmap)",   self.smb_nmap, primary=True)
        self.add_action("📂 SMB shares",        self.smb_shares)
        self.add_action("👥 SMB users (rpc)",   self.rpc_users)
        self.add_action("🌳 LDAP root DSE",     self.ldap_root)
        self.add_action("🎟  Kerberos pre-auth", self.kerberos)

    def smb_nmap(self):
        if not self.target or not self.need("nmap"): return
        cmd = ["nmap","-p","139,445","--script",
               "smb-enum-shares,smb-enum-users,smb-os-discovery,smb-security-mode,smb2-security-mode",
               self.target]
        rc, out = run_subprocess(cmd, timeout=300)
        self.write(out)

    def smb_shares(self):
        if not self.target or not self.need("smbclient"): return
        rc, out = run_subprocess(["smbclient","-L","//"+self.target,"-N"], timeout=30)
        self.write(out)

    def rpc_users(self):
        if not self.target or not self.need("rpcclient"): return
        rc, out = run_subprocess(
            ["rpcclient","-U",""," -N", self.target, "-c","enumdomusers"], timeout=30)
        self.write(out)

    def ldap_root(self):
        if not self.target or not self.need("ldapsearch"): return
        rc, out = run_subprocess(
            ["ldapsearch","-x","-H","ldap://"+self.target,"-s","base","-b",""], timeout=30)
        self.write(out)

    def kerberos(self):
        if not self.target or not self.need("nmap"): return
        rc, out = run_subprocess(
            ["nmap","-p","88","--script","krb5-enum-users",
             "--script-args", "krb5-enum-users.realm='"+self.target+"'", self.target], timeout=120)
        self.write(out)
