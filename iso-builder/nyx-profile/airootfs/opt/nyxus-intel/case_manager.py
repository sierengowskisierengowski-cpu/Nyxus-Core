# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · case_manager.py
On-disk case storage.

Each case lives as one encrypted JSON envelope (see encryption.py) on the
filesystem inside ~/.config/nyxus-intel/cases/. We also keep an SQLite
INDEX with the metadata we need for the A-Z sidebar (subject, type,
created_at, file path, last opened) — the index does NOT contain any
investigation findings, only what's needed to list and find cases. The
index can always be rebuilt from disk by walking the cases dir and
decrypting each envelope's metadata block.

Auto case-filing structure:
   <cases_root>/
       SIERENGOWSKI_JOSEPH_2026-05-01/
           identity/
           breach_data/
           public_records/
           digital_footprint/
           historical/
           financial/
           photos/
           crypto/
           communications/
           location/
           network/
           notes/
           case.nxc          ← the encrypted case envelope
           report.pdf        ← latest exported report

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import os
import re
import json
import time
import sqlite3
import threading
import datetime as dt
from pathlib import Path
from typing import Optional, List, Dict, Any, Iterable

from encryption import encrypt_case, decrypt_case, secure_delete

# ── NYXUS palette (single source of truth · rev r13) ────────────────
try:
    from nyxus_palette import (
        WHITE_PURE, WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        INK_FADED, INK_BLACK,
        GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE, HAIRLINE_INK,
        SHADOW_INK_ACTIVE, SHADOW_INK_INACTIVE,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
        format_css, assert_no_forbidden,
    )
except Exception:
    # palette module is shipped alongside every NYXUS app via
    # nyxus_install.sh; if it's missing, fall back to literals so
    # the app still launches.
    WHITE_PURE='#ffffff'; WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    INK_FADED='#0a0a0a'; INK_BLACK='#000000'
    GLASS_DARK='rgba(8, 12, 20, 0.55)'
    GLASS_DEEPER='rgba(15, 20, 32, 0.72)'
    GLASS_DEEPEST='rgba(5, 7, 12, 0.92)'
    HAIRLINE_WHITE='rgba(255, 255, 255, 0.10)'
    HAIRLINE_INK='rgba(0, 0, 0, 0.45)'
    SHADOW_INK_ACTIVE='rgba(0, 0, 0, 0.65)'
    SHADOW_INK_INACTIVE='rgba(0, 0, 0, 0.20)'
    RADIUS_CARD=14; RADIUS_PILL=12; RADIUS_INPUT=10
    FONT_UI='Inter'; FONT_MONO='JetBrains Mono'; FONT_DISPLAY='Inter Display'
    def format_css(t):
        _d = {
            'WHITE_PURE': WHITE_PURE, 'WHITE_OFF': WHITE_OFF,
            'GREY_LIGHT': GREY_LIGHT, 'GREY_MID': GREY_MID,
            'GREY_TERTIARY': GREY_TERTIARY,
            'INK_FADED': INK_FADED, 'INK_BLACK': INK_BLACK,
            'GLASS_DARK': GLASS_DARK, 'GLASS_DEEPER': GLASS_DEEPER,
            'GLASS_DEEPEST': GLASS_DEEPEST,
            'HAIRLINE_WHITE': HAIRLINE_WHITE, 'HAIRLINE_INK': HAIRLINE_INK,
            'SHADOW_INK_ACTIVE': SHADOW_INK_ACTIVE,
            'SHADOW_INK_INACTIVE': SHADOW_INK_INACTIVE,
            'RADIUS_CARD': RADIUS_CARD, 'RADIUS_PILL': RADIUS_PILL,
            'RADIUS_INPUT': RADIUS_INPUT,
            'FONT_UI': FONT_UI, 'FONT_MONO': FONT_MONO,
            'FONT_DISPLAY': FONT_DISPLAY,
        }
        return t.format_map(_d)
    def assert_no_forbidden(*a, **k): pass
# ─────────────────────────────────────────────────────────────────────


CASES_ROOT  = Path.home() / ".config" / "nyxus-intel" / "cases"
INDEX_DB    = Path.home() / ".config" / "nyxus-intel" / "index.db"

CASE_SUBDIRS = (
    "identity", "breach_data", "public_records", "digital_footprint",
    "historical", "financial", "photos", "crypto", "communications",
    "location", "network", "notes",
)

CASE_FILE_NAME = "case.nxc"


def _slug(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_]+", "_", (s or "").strip()).strip("_")
    return s.upper()[:60] or "UNNAMED"


def _today() -> str:
    return dt.date.today().isoformat()


def make_case_dir(subject: str, root: Path = CASES_ROOT) -> Path:
    """Create the SUBJECT_DATE folder + 12 sub-folders. If the same
    SUBJECT_DATE already exists we append _2, _3, … to keep them distinct."""
    base = _slug(subject)
    candidate = root / f"{base}_{_today()}"
    n = 2
    while candidate.exists():
        candidate = root / f"{base}_{_today()}_{n}"
        n += 1
    for sub in CASE_SUBDIRS:
        (candidate / sub).mkdir(parents=True, exist_ok=True)
    return candidate


def _split_subject(subject: str) -> tuple[str, str]:
    """Best-effort first/last name split. 'Joseph Sierengowski' → ('JOSEPH','SIERENGOWSKI').
    For non-name subjects (emails, IPs, etc.) we just return ('', upper(subject))."""
    parts = (subject or "").strip().split()
    if len(parts) >= 2 and all(p.replace("-", "").isalpha() for p in parts):
        first = _slug(parts[0])
        last  = _slug(" ".join(parts[1:]))
        return first, last
    return "", _slug(subject)


def make_case_dir_for_person(subject: str, root: Path = CASES_ROOT) -> Path:
    """LASTNAME_FIRSTNAME_DATE for actual people, falls back to SUBJECT_DATE."""
    first, last = _split_subject(subject)
    if first:
        slug = f"{last}_{first}"
    else:
        slug = last
    candidate = root / f"{slug}_{_today()}"
    n = 2
    while candidate.exists():
        candidate = root / f"{slug}_{_today()}_{n}"
        n += 1
    for sub in CASE_SUBDIRS:
        (candidate / sub).mkdir(parents=True, exist_ok=True)
    return candidate


# ── index ────────────────────────────────────────────────────────────────
class CaseIndex:
    """SQLite index over case metadata — one row per case file on disk."""

    def __init__(self, db_path: Path = INDEX_DB):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False so background search threads can write
        # the case row when a search finishes; we serialise all access
        # through self._lock to make that safe.
        self._db = sqlite3.connect(str(db_path), check_same_thread=False)
        self._lock = threading.RLock()
        self._db.execute(
            """CREATE TABLE IF NOT EXISTS cases(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject     TEXT NOT NULL,
                detected_type TEXT NOT NULL,
                created_at  INTEGER NOT NULL,
                opened_at   INTEGER NOT NULL,
                folder      TEXT NOT NULL UNIQUE,
                tags        TEXT,
                summary     TEXT
            )""")
        self._db.execute(
            "CREATE INDEX IF NOT EXISTS ix_cases_subject ON cases(subject COLLATE NOCASE)")
        self._db.commit()

    def add(self, subject: str, detected_type: str, folder: Path,
            summary: str = "", tags: Iterable[str] = ()) -> int:
        now = int(time.time())
        with self._lock:
            cur = self._db.execute(
                """INSERT INTO cases(subject, detected_type, created_at,
                                     opened_at, folder, tags, summary)
                   VALUES(?,?,?,?,?,?,?)""",
                (subject, detected_type, now, now, str(folder),
                 ",".join(tags), summary))
            self._db.commit()
            return cur.lastrowid

    def update_summary(self, case_id: int, summary: str) -> None:
        with self._lock:
            self._db.execute("UPDATE cases SET summary=? WHERE id=?",
                             (summary, case_id))
            self._db.commit()

    def touch_opened(self, case_id: int) -> None:
        with self._lock:
            self._db.execute("UPDATE cases SET opened_at=? WHERE id=?",
                             (int(time.time()), case_id))
            self._db.commit()

    def list_alpha(self) -> List[sqlite3.Row]:
        with self._lock:
            self._db.row_factory = sqlite3.Row
            cur = self._db.execute(
                "SELECT * FROM cases ORDER BY subject COLLATE NOCASE ASC, created_at DESC")
            return cur.fetchall()

    def search(self, q: str) -> List[sqlite3.Row]:
        with self._lock:
            self._db.row_factory = sqlite3.Row
            like = f"%{q}%"
            cur = self._db.execute(
                "SELECT * FROM cases WHERE subject LIKE ? OR summary LIKE ? OR tags LIKE ? "
                "ORDER BY subject COLLATE NOCASE ASC", (like, like, like))
            return cur.fetchall()

    def get(self, case_id: int) -> Optional[sqlite3.Row]:
        with self._lock:
            self._db.row_factory = sqlite3.Row
            cur = self._db.execute("SELECT * FROM cases WHERE id=?", (case_id,))
            return cur.fetchone()

    def delete(self, case_id: int) -> Optional[str]:
        with self._lock:
            row = self.get(case_id)
            if row is None: return None
            self._db.execute("DELETE FROM cases WHERE id=?", (case_id,))
            self._db.commit()
            return row["folder"]

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            cur = self._db.execute(
                "SELECT COUNT(*) AS n, MIN(created_at) AS first, MAX(opened_at) AS last "
                "FROM cases")
            n, first, last = cur.fetchone()
            return {"count": n or 0, "first": first or 0, "last": last or 0}

    def close(self) -> None:
        with self._lock:
            try: self._db.close()
            except Exception: pass


# ── case file IO ─────────────────────────────────────────────────────────
def save_case(case_dir: Path, payload: Dict[str, Any], password: str) -> Path:
    case_dir.mkdir(parents=True, exist_ok=True)
    target = case_dir / CASE_FILE_NAME
    env = encrypt_case(payload, password)
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(env), "utf-8")
    os.replace(tmp, target)
    try: os.chmod(target, 0o600)
    except OSError: pass
    return target


def load_case(case_dir: Path, password: str) -> Dict[str, Any]:
    target = case_dir / CASE_FILE_NAME
    if not target.exists():
        raise FileNotFoundError(f"no case file at {target}")
    env = json.loads(target.read_text("utf-8"))
    return decrypt_case(env, password)


def delete_case(case_dir: Path) -> None:
    """Securely overwrite + remove every file under the case dir, then rmdir."""
    if not case_dir.exists():
        return
    for root, _dirs, files in os.walk(case_dir, topdown=False):
        for name in files:
            secure_delete(os.path.join(root, name))
        try: os.rmdir(root)
        except OSError: pass


# ── manager facade ───────────────────────────────────────────────────────
class CaseManager:
    def __init__(self, password_provider):
        """password_provider() → str. Called every time we need to encrypt or
        decrypt; the actual password lives only in the Session object."""
        CASES_ROOT.mkdir(parents=True, exist_ok=True)
        self._pw = password_provider
        self.index = CaseIndex()

    def create(self, subject: str, detected_type: str,
               findings: Dict[str, Any]) -> tuple[int, Path]:
        if detected_type == "person" or detected_type == "plain":
            folder = make_case_dir_for_person(subject)
        else:
            folder = make_case_dir(subject)
        payload = {
            "subject":       subject,
            "detected_type": detected_type,
            "created_at":    int(time.time()),
            "findings":      findings,
            "notes":         "",
        }
        save_case(folder, payload, self._pw())
        summary = (findings.get("summary") or "")[:200]
        case_id = self.index.add(subject, detected_type, folder, summary)
        return case_id, folder

    def update(self, case_id: int, mutator) -> None:
        row = self.index.get(case_id)
        if row is None:
            raise KeyError(case_id)
        folder = Path(row["folder"])
        payload = load_case(folder, self._pw())
        mutator(payload)
        save_case(folder, payload, self._pw())
        if "summary" in payload.get("findings", {}):
            self.index.update_summary(case_id, payload["findings"]["summary"][:200])

    def open(self, case_id: int) -> Dict[str, Any]:
        row = self.index.get(case_id)
        if row is None:
            raise KeyError(case_id)
        self.index.touch_opened(case_id)
        return load_case(Path(row["folder"]), self._pw())

    def folder(self, case_id: int) -> Optional[Path]:
        row = self.index.get(case_id)
        return Path(row["folder"]) if row else None

    def delete(self, case_id: int) -> None:
        folder = self.index.delete(case_id)
        if folder:
            delete_case(Path(folder))

    def alpha(self) -> List[sqlite3.Row]:
        return self.index.list_alpha()

    def search(self, q: str) -> List[sqlite3.Row]:
        return self.index.search(q)
