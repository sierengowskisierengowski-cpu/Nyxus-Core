"""Module 20 — Binary and File Analysis."""
from __future__ import annotations

import hashlib
from pathlib import Path

from ui import BaseModule, run_subprocess


class Page(BaseModule):
    NAME = "Binary Analysis"
    ICON = "🧩"
    DESCRIPTION = ("file, strings, objdump, readelf, nm, ldd, checksec.sh, and "
                   "rabin2 (radare2) if available. Target box = path to a binary.")

    def build(self):
        self.add_action("📄 file + sha256",     self.fileinfo, primary=True)
        self.add_action("🔡 strings",           self.strings)
        self.add_action("📚 readelf -h -d",     self.readelf)
        self.add_action("🛠 ldd / dynamic libs", self.ldd)
        self.add_action("🔒 checksec",          self.checksec)
        self.add_action("⚡ rabin2 -I",          self.rabin2)

    def _path(self) -> Path | None:
        p = Path(self.target).expanduser()
        if not p.is_file():
            self.write(f"file not found: {p}"); return None
        return p

    def fileinfo(self):
        p = self._path()
        if not p: return
        rc, out = run_subprocess(["file","-b", str(p)], timeout=10)
        self.write("type: " + out.strip())
        h = hashlib.sha256()
        with open(p,"rb") as f:
            for c in iter(lambda: f.read(65536), b""): h.update(c)
        self.write(f"sha256: {h.hexdigest()}\nsize:   {p.stat().st_size}")

    def strings(self):
        p = self._path()
        if not p: return
        rc, out = run_subprocess(["strings","-n","8", str(p)], timeout=60)
        self.write("\n".join(out.splitlines()[:500]))

    def readelf(self):
        p = self._path()
        if not p or not self.need("readelf"): return
        rc, out = run_subprocess(["readelf","-h","-d","-l", str(p)], timeout=30)
        self.write(out)

    def ldd(self):
        p = self._path()
        if not p or not self.need("ldd"): return
        rc, out = run_subprocess(["ldd", str(p)], timeout=30)
        self.write(out)

    def checksec(self):
        p = self._path()
        if not p or not self.need("checksec"): return
        rc, out = run_subprocess(["checksec","--file="+str(p)], timeout=30)
        self.write(out)

    def rabin2(self):
        p = self._path()
        if not p or not self.need("rabin2"): return
        rc, out = run_subprocess(["rabin2","-I", str(p)], timeout=30)
        self.write(out)
