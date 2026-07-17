#!/usr/bin/env python3
"""
Bifrost resilience helpers — fail-closed validation, logging, and DB safety.
"""

from __future__ import annotations

import json
import logging
import sqlite3
import sys
import time
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger("heimdall.resilience")

MAX_EVENT_RAW_BYTES = 256 * 1024
MAX_INGEST_BODY_BYTES = 512 * 1024
VALID_BOUNDARIES = frozenset({"HOST", "HONEYPOT", "NETWORK", "UNKNOWN"})


def validate_event_envelope(event: Any) -> tuple[bool, str]:
    """
    Validate an incoming event envelope. Returns (ok, error_message).
    Rejects oversize or malformed payloads — fail closed.
    """
    if not isinstance(event, dict):
        return False, "event must be a JSON object"

    for field in ("source", "boundary", "raw"):
        if field not in event:
            return False, f"missing required field: {field}"

    source = event.get("source")
    if not isinstance(source, str) or not source.strip():
        return False, "source must be a non-empty string"
    if len(source) > 128:
        return False, "source exceeds max length"

    boundary = event.get("boundary")
    if not isinstance(boundary, str) or boundary not in VALID_BOUNDARIES:
        return False, f"invalid boundary: {boundary!r}"

    try:
        raw_size = len(json.dumps(event.get("raw"), default=str))
    except (TypeError, ValueError):
        return False, "raw field is not JSON-serializable"

    if raw_size > MAX_EVENT_RAW_BYTES:
        return False, f"raw payload exceeds {MAX_EVENT_RAW_BYTES} bytes"

    timestamp = event.get("timestamp")
    if timestamp is not None and not isinstance(timestamp, str):
        return False, "timestamp must be a string when present"

    return True, ""


class FailoverLoggingHandler(logging.Handler):
    """
    Log to file; on disk-full or write failure, fall back to stderr only.
    Never silently drops log records.
    """

    def __init__(self, file_path: Path):
        super().__init__()
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._file_handler = logging.FileHandler(self.file_path)
        self._stderr_handler = logging.StreamHandler(sys.stderr)
        self._stderr_only = False
        self._warned = False

    def emit(self, record: logging.LogRecord) -> None:
        if self._stderr_only:
            self._stderr_handler.emit(record)
            return
        try:
            self._file_handler.emit(record)
        except Exception as exc:
            self._stderr_only = True
            if not self._warned:
                self._warned = True
                sys.stderr.write(
                    f"[heimdall] Log file write failed ({exc}); "
                    f"falling back to stderr only.\n"
                )
            self._stderr_handler.emit(record)

    def close(self) -> None:
        try:
            self._file_handler.close()
        except Exception:
            pass
        self._stderr_handler.close()
        super().close()


def configure_sqlite_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")


def verify_database_integrity(conn: sqlite3.Connection) -> tuple[bool, str]:
    try:
        row = conn.execute("PRAGMA integrity_check").fetchone()
        if row and row[0] == "ok":
            return True, "ok"
        return False, str(row[0] if row else "integrity_check failed")
    except sqlite3.Error as exc:
        return False, str(exc)


def execute_with_db_retry(
    conn: sqlite3.Connection,
    db_path: str,
    operation,
    logger: logging.Logger,
    max_attempts: int = 3,
) -> tuple[Any, Optional[sqlite3.Connection]]:
    """
    Run operation(conn) with retry on SQLITE_BUSY/locked errors.
    Returns (result, conn) — conn may be replaced after reconnect.
    """
    last_error = None
    current_conn = conn

    for attempt in range(1, max_attempts + 1):
        try:
            return operation(current_conn), current_conn
        except sqlite3.OperationalError as exc:
            last_error = exc
            message = str(exc).lower()
            if "locked" in message or "busy" in message:
                logger.warning(
                    "SQLite busy (attempt %d/%d): %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                time.sleep(0.1 * attempt)
                continue
            if "corrupt" in message or "malformed" in message:
                logger.critical("SQLite corruption detected: %s", exc)
                raise
            raise
        except sqlite3.DatabaseError as exc:
            last_error = exc
            message = str(exc).lower()
            if "corrupt" in message or "malformed" in message:
                logger.critical("SQLite corruption detected: %s", exc)
                raise
            if attempt < max_attempts:
                logger.warning(
                    "SQLite error (attempt %d/%d): %s",
                    attempt,
                    max_attempts,
                    exc,
                )
                try:
                    current_conn.close()
                except sqlite3.Error:
                    pass
                current_conn = sqlite3.connect(
                    db_path, check_same_thread=False
                )
                configure_sqlite_connection(current_conn)
                time.sleep(0.1 * attempt)
                continue
            raise

    raise last_error  # type: ignore[misc]


def verify_config_integrity(config_path: Path) -> tuple[bool, str]:
    """Re-check config file and checksum. Used during runtime."""
    if not config_path.exists():
        return False, "config file missing"

    checksum_path = config_path.with_suffix(".sha256")
    if not checksum_path.exists():
        return False, "config checksum file missing"

    import hashlib

    actual = hashlib.sha256(config_path.read_bytes()).hexdigest()
    expected = checksum_path.read_text().strip()
    if actual != expected:
        return False, "config checksum mismatch"
    return True, "ok"
