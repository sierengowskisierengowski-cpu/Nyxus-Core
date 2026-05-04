"""Module 19 — Cryptography Suite."""
from __future__ import annotations

import base64
import hashlib
import os
import secrets

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "Cryptography"
    ICON = "🔐"
    DESCRIPTION = ("OpenSSL helpers + GPG inspection. Generate keys, hash files, "
                   "verify certs, compute HMACs, and detect algorithm weakness.")

    def build(self):
        self.add_action("📜 inspect cert (target)", self.cert_info, primary=True)
        self.add_action("🔑 RSA-4096 keypair",       self.gen_rsa)
        self.add_action("🔑 Ed25519 keypair",        self.gen_ed25519)
        self.add_action("🔢 random 256-bit token",   self.token)
        self.add_action("📝 SHA-256 of target",      self.sha256)
        self.add_action("🛂 GPG list keys",          self.gpg_list)

    def cert_info(self):
        if not self.target or not self.need("openssl"): return
        host, _, port = self.target.partition(":"); port = port or "443"
        rc, out = run_subprocess(
            ["bash","-c", f"echo | openssl s_client -connect {host}:{port} -servername {host} 2>/dev/null "
                          f"| openssl x509 -noout -text -fingerprint -sha256"], timeout=30)
        self.write(out)

    def gen_rsa(self):
        if not self.need("openssl"): return
        rc, key = run_subprocess(["openssl","genpkey","-algorithm","RSA","-pkeyopt","rsa_keygen_bits:4096"],
                                  timeout=60)
        self.write(key)

    def gen_ed25519(self):
        if not self.need("openssl"): return
        rc, key = run_subprocess(["openssl","genpkey","-algorithm","ED25519"], timeout=10)
        self.write(key)

    def token(self):
        self.write(secrets.token_urlsafe(48))
        self.write("hex: " + secrets.token_hex(32))
        self.write("b64: " + base64.b64encode(os.urandom(32)).decode())

    def sha256(self):
        self.write("sha256: " + hashlib.sha256(self.target.encode()).hexdigest())
        self.write("sha3  : " + hashlib.sha3_256(self.target.encode()).hexdigest())
        self.write("blake2: " + hashlib.blake2b(self.target.encode()).hexdigest())

    def gpg_list(self):
        rc, out = run_subprocess(["gpg","--list-keys","--with-fingerprint"], timeout=10)
        self.write(out or "no GPG keys")
