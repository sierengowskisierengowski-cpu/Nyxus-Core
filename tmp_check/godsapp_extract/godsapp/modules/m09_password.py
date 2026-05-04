"""Module 09 — Password and Hash Analysis."""
from __future__ import annotations

import hashlib
import os
import shutil
import tempfile

from ui import BaseModule, run_subprocess
import db


class Page(BaseModule):
    NAME = "Password / Hash"
    ICON = "🔑"
    DESCRIPTION = ("Hash identification, dictionary cracking via john / hashcat, "
                   "and password-strength entropy estimates. Provide hash in target box.")

    HASH_LENS = {32:"MD5",40:"SHA-1",56:"SHA-224",64:"SHA-256",96:"SHA-384",128:"SHA-512"}

    def build(self):
        self.add_action("🔍 identify hash",         self.identify, primary=True)
        self.add_action("📐 entropy of target",     self.entropy)
        self.add_action("🔨 john (rockyou wordlist)", self.john)
        self.add_action("🔨 hashcat (auto mode)",   self.hashcat)
        self.add_action("📚 SHA-256 of target",     self.sha256)

    def identify(self):
        h = self.target.strip().lower()
        if not h:
            self.write("paste a hash in the target box"); return
        if all(c in "0123456789abcdef" for c in h) and len(h) in self.HASH_LENS:
            self.write(f"length={len(h)} → likely {self.HASH_LENS[len(h)]}")
        elif h.startswith("$2"):
            self.write("bcrypt ($2a/$2b/$2y)")
        elif h.startswith("$argon2"):
            self.write("Argon2")
        elif h.startswith("$6$"): self.write("SHA-512 crypt (Linux /etc/shadow)")
        elif h.startswith("$5$"): self.write("SHA-256 crypt (Linux /etc/shadow)")
        elif h.startswith("$1$"): self.write("MD5 crypt (Linux /etc/shadow, weak)")
        else:
            self.write("unrecognised — try hashid / hash-identifier")
        if shutil.which("hashid"):
            rc, out = run_subprocess(["hashid","-m", h], timeout=10)
            self.write("\n--- hashid ---\n" + out)

    def entropy(self):
        s = self.target
        if not s:
            return
        from math import log2
        pool = 0
        if any(c.islower() for c in s): pool += 26
        if any(c.isupper() for c in s): pool += 26
        if any(c.isdigit() for c in s): pool += 10
        if any(not c.isalnum() for c in s): pool += 32
        bits = len(s) * (log2(pool) if pool else 0)
        verdict = ("trivial" if bits<28 else "weak" if bits<36
                   else "fair" if bits<60 else "strong" if bits<128 else "very strong")
        self.write(f"length={len(s)}  pool={pool}  entropy≈{bits:.1f} bits  ({verdict})")

    def _wordlist(self) -> str:
        for p in ("/usr/share/wordlists/rockyou.txt",
                  "/usr/share/dict/words","/usr/share/wordlists/fasttrack.txt"):
            if os.path.exists(p):
                return p
        return ""

    def john(self):
        if not self.target or not self.need("john"):
            return
        wl = self._wordlist()
        if not wl:
            self.write("no wordlist found — install wordlists package"); return
        with tempfile.NamedTemporaryFile("w", suffix=".hash", delete=False) as fh:
            fh.write(self.target.strip()+"\n")
            path = fh.name
        rc, out = run_subprocess(["john","--wordlist="+wl, path], timeout=600)
        self.write(out)
        rc, out = run_subprocess(["john","--show", path], timeout=10)
        self.write("\n--- show ---\n" + out)
        db.record_scan(self.NAME, "<hash>", "john", "john", f"rc={rc}")

    def hashcat(self):
        if not self.target or not self.need("hashcat"):
            return
        wl = self._wordlist()
        if not wl:
            self.write("no wordlist found"); return
        with tempfile.NamedTemporaryFile("w", suffix=".hash", delete=False) as fh:
            fh.write(self.target.strip()+"\n"); path = fh.name
        rc, out = run_subprocess(["hashcat","-a","0","-m","0", path, wl, "--force"], timeout=600)
        self.write(out)

    def sha256(self):
        s = self.target.encode()
        self.write("sha256: " + hashlib.sha256(s).hexdigest())
        self.write("sha1  : " + hashlib.sha1(s).hexdigest())
        self.write("md5   : " + hashlib.md5(s).hexdigest())
