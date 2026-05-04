"""
NYXUS GodsApp — sqlite scan history + cached lookups.
© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = Path.home() / ".config" / "nyxus-godsapp" / "godsapp.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ts REAL NOT NULL,
    module TEXT NOT NULL,
    target TEXT,
    profile TEXT,
    cmd TEXT,
    result_summary TEXT,
    result_path TEXT
);
CREATE INDEX IF NOT EXISTS idx_scan_ts ON scans(ts);
CREATE INDEX IF NOT EXISTS idx_scan_mod ON scans(module);

CREATE TABLE IF NOT EXISTS findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_id INTEGER REFERENCES scans(id),
    severity TEXT NOT NULL,
    title TEXT NOT NULL,
    detail TEXT,
    cvss REAL,
    cve TEXT
);
CREATE INDEX IF NOT EXISTS idx_findings_sev ON findings(severity);

CREATE TABLE IF NOT EXISTS cve_cache (
    cve TEXT PRIMARY KEY,
    cvss REAL,
    description TEXT,
    refs TEXT,
    fetched REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS device_history (
    mac TEXT NOT NULL,
    ip TEXT,
    hostname TEXT,
    vendor TEXT,
    first_seen REAL NOT NULL,
    last_seen REAL NOT NULL,
    PRIMARY KEY(mac)
);

CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    module TEXT NOT NULL,
    target TEXT,
    cadence_seconds INTEGER NOT NULL,
    next_run REAL NOT NULL,
    enabled INTEGER NOT NULL DEFAULT 1
);
"""


def conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), isolation_level=None, check_same_thread=False)
    c.executescript(SCHEMA)
    return c


def record_scan(module: str, target: str, profile: str, cmd: str,
                summary: str, output_path: str | None = None) -> int:
    c = conn()
    cur = c.execute(
        "INSERT INTO scans(ts,module,target,profile,cmd,result_summary,result_path) "
        "VALUES(?,?,?,?,?,?,?)",
        (time.time(), module, target, profile, cmd, summary, output_path),
    )
    return cur.lastrowid


def add_finding(scan_id: int, severity: str, title: str,
                detail: str = "", cvss: float = 0, cve: str = "") -> None:
    conn().execute(
        "INSERT INTO findings(scan_id,severity,title,detail,cvss,cve) VALUES(?,?,?,?,?,?)",
        (scan_id, severity, title, detail, cvss, cve),
    )


def see_device(mac: str, ip: str = "", hostname: str = "", vendor: str = "") -> None:
    now = time.time()
    c = conn()
    row = c.execute("SELECT first_seen FROM device_history WHERE mac=?", (mac,)).fetchone()
    if row:
        c.execute("UPDATE device_history SET ip=?, hostname=?, vendor=?, last_seen=? "
                  "WHERE mac=?", (ip, hostname, vendor, now, mac))
    else:
        c.execute("INSERT INTO device_history VALUES(?,?,?,?,?,?)",
                  (mac, ip, hostname, vendor, now, now))


def cve_get(cve_id: str) -> dict | None:
    row = conn().execute(
        "SELECT cvss, description, refs FROM cve_cache WHERE cve=?",
        (cve_id,)
    ).fetchone()
    if not row:
        return None
    return {"cve": cve_id, "cvss": row[0], "description": row[1], "refs": json.loads(row[2] or "[]")}


def cve_put(cve_id: str, cvss: float, description: str, refs: list[str]) -> None:
    conn().execute(
        "INSERT OR REPLACE INTO cve_cache VALUES(?,?,?,?,?)",
        (cve_id, cvss, description, json.dumps(refs), time.time()),
    )


def list_recent_scans(limit: int = 50) -> list[dict]:
    cur = conn().execute(
        "SELECT id, ts, module, target, result_summary FROM scans "
        "ORDER BY id DESC LIMIT ?", (limit,)
    )
    return [{"id": r[0], "ts": r[1], "module": r[2], "target": r[3], "summary": r[4]}
            for r in cur.fetchall()]
