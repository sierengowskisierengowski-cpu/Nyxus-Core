"""Module 28 — Forensics."""
from __future__ import annotations

import hashlib
import time
from pathlib import Path

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "Forensics"
    ICON = "🧪"
    DESCRIPTION = ("Disk imaging (dd / dcfldd), Sleuthkit triage, Volatility memory "
                   "analysis, evidence hashing + chain-of-custody log.")

    def build(self):
        self.add_action("🧷 hash file (sha256+md5)",     self.hash_file, primary=True)
        self.add_action("📦 dd image (target → ~/evidence)", self.dd_image)
        self.add_action("📂 fls / mmls (Sleuthkit)",     self.sleuthkit)
        self.add_action("🧠 vol2 image info",            self.vol_imageinfo)
        self.add_action("📓 view chain-of-custody",      self.coc)

    def _coc_path(self) -> Path:
        d = Path.home() / "evidence"; d.mkdir(exist_ok=True)
        return d / "chain_of_custody.log"

    def hash_file(self):
        p = Path(self.target).expanduser()
        if not p.is_file(): self.write(f"not a file: {p}"); return
        sha = hashlib.sha256(); md = hashlib.md5()
        with open(p,"rb") as f:
            for c in iter(lambda: f.read(1<<16), b""):
                sha.update(c); md.update(c)
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}  HASH  {p}  sha256={sha.hexdigest()} md5={md.hexdigest()}"
        self.write(line)
        with open(self._coc_path(),"a") as f: f.write(line + "\n")

    def dd_image(self):
        if not self.target: return
        src = self.target
        dst = Path.home() / "evidence" / (Path(src).name + f".{int(time.time())}.img")
        dst.parent.mkdir(exist_ok=True)
        rc, out = run_subprocess(
            ["sudo","-n","dd",f"if={src}",f"of={dst}","bs=1M","status=progress","conv=noerror,sync"],
            timeout=3600)
        self.write(out + f"\nimage → {dst}")
        line = f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}  IMAGE {src}  →  {dst}"
        with open(self._coc_path(),"a") as f: f.write(line + "\n")

    def sleuthkit(self):
        if not self.target: return
        rc, out = run_subprocess(["mmls", self.target], timeout=60); self.write(out)
        rc, out = run_subprocess(["fls","-r", self.target], timeout=120); self.write(out[:60000])

    def vol_imageinfo(self):
        if not self.target: return
        # Volatility 3 syntax
        rc, out = run_subprocess(["vol","-f", self.target, "windows.info"], timeout=300)
        self.write(out or "install volatility3 (`pip install volatility3`)")

    def coc(self):
        p = self._coc_path()
        if not p.exists():
            self.write("(no chain-of-custody entries yet)"); return
        self.write(p.read_text())
