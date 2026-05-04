"""Module 27 — Automation and Scheduling."""
from __future__ import annotations

import time

from ui import BaseModule
import db


class Page(BaseModule):
    NAME = "Automation"
    ICON = "⏱"
    DESCRIPTION = ("Schedule recurring scans (any module) at fixed intervals. "
                   "Persisted in sqlite and executed by the GodsApp scheduler thread.")

    PRESETS = [
        ("hourly Quick Surface scan", "m07_attack_surface", 3600),
        ("daily SSL audit",            "m05_vulns",          86400),
        ("daily failed-login report",  "m21_logs",           86400),
        ("weekly full vuln scan",      "m05_vulns",          604800),
    ]

    def build(self):
        self.add_action("📋 list schedules",     self.list_, primary=True)
        for label, mod, sec in self.PRESETS:
            self.add_action(f"➕ {label}",
                            lambda m=mod, s=sec, n=label: self.add(n, m, s))
        self.add_action("🗑 disable all",        self.disable_all, danger=True)

    def list_(self):
        cur = db.conn().execute(
            "SELECT id,name,module,target,cadence_seconds,next_run,enabled FROM schedules ORDER BY id")
        rows = cur.fetchall()
        if not rows:
            self.write("(no schedules)"); return
        for r in rows:
            mins = r[4] // 60
            nxt  = time.strftime("%Y-%m-%d %H:%M", time.localtime(r[5]))
            on   = "ON " if r[6] else "off"
            self.write(f"  [{r[0]:>3}] {on}  every {mins:>5} min  next={nxt}  {r[1]}")

    def add(self, name: str, module: str, secs: int):
        db.conn().execute(
            "INSERT INTO schedules(name,module,target,cadence_seconds,next_run,enabled) "
            "VALUES(?,?,?,?,?,1)", (name, module, self.target or "", secs, time.time()+secs))
        self.write(f"added: {name} (every {secs//60} min)")

    def disable_all(self):
        db.conn().execute("UPDATE schedules SET enabled=0")
        self.write("all schedules disabled")
