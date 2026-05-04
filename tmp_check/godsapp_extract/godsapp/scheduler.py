"""
NYXUS GodsApp — scheduling engine.
© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED

Runs as a background thread inside the main app process. Reads
scheduled-job rows from the godsapp.db `schedules` table and triggers
the corresponding module's CLI handler.
"""
from __future__ import annotations

import threading
import time
from typing import Callable

from db import conn


class Scheduler:
    def __init__(self, dispatch: Callable[[str, str], None]):
        """`dispatch(module_name, target)` is called when a job fires."""
        self.dispatch = dispatch
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None

    def start(self) -> None:
        self.thread = threading.Thread(target=self._loop, daemon=True, name="sched")
        self.thread.start()

    def shutdown(self) -> None:
        self.stop.set()

    def _loop(self) -> None:
        while not self.stop.wait(15):
            now = time.time()
            c = conn()
            cur = c.execute(
                "SELECT id, name, module, target, cadence_seconds "
                "FROM schedules WHERE enabled=1 AND next_run <= ?",
                (now,),
            )
            for sid, name, module, target, cadence in cur.fetchall():
                try:
                    self.dispatch(module, target or "")
                except Exception:
                    pass
                c.execute("UPDATE schedules SET next_run=? WHERE id=?",
                          (now + cadence, sid))


def add_schedule(name: str, module: str, target: str, cadence_seconds: int) -> int:
    c = conn()
    cur = c.execute(
        "INSERT INTO schedules(name, module, target, cadence_seconds, next_run) "
        "VALUES(?,?,?,?,?)",
        (name, module, target, cadence_seconds, time.time() + cadence_seconds),
    )
    return cur.lastrowid


def list_schedules() -> list[dict]:
    cur = conn().execute("SELECT id,name,module,target,cadence_seconds,next_run,enabled "
                         "FROM schedules ORDER BY id")
    return [{"id": r[0], "name": r[1], "module": r[2], "target": r[3],
             "cadence_seconds": r[4], "next_run": r[5], "enabled": bool(r[6])}
            for r in cur.fetchall()]


def toggle_schedule(sid: int, enabled: bool) -> None:
    conn().execute("UPDATE schedules SET enabled=? WHERE id=?",
                   (1 if enabled else 0, sid))


def delete_schedule(sid: int) -> None:
    conn().execute("DELETE FROM schedules WHERE id=?", (sid,))
