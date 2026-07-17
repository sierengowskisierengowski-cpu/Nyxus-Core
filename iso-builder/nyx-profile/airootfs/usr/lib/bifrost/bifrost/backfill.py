#!/usr/bin/env python3
"""
Backfill heimdall_decision for historical events stored without AI classification.

Replays the compress → reason → policy pipeline for rows where heimdall_decision
IS NULL. Never dispatches destructive executor actions — decisions are written only.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
from queue import Queue

from bifrost import paths as bifrost_paths
from bifrost.guardian import (
    EventRouter,
    _normalize_compressed_event,
    load_config,
    refresh_runtime_paths,
)
from bifrost.resilience import configure_sqlite_connection, execute_with_db_retry

log = logging.getLogger("heimdall.backfill")


def row_to_event(row: tuple) -> tuple[dict, int, str | None]:
    """Convert a SQLite row into an event envelope and metadata."""
    event_id, timestamp, source, boundary, raw_event, compressed_event = row
    try:
        raw = json.loads(raw_event)
    except json.JSONDecodeError:
        raw = {"parse_error": True, "raw": raw_event[:500]}
    event = {
        "source": source,
        "timestamp": timestamp,
        "boundary": boundary,
        "raw": raw,
    }
    return event, event_id, compressed_event


def fetch_pending_rows(
    conn: sqlite3.Connection,
    *,
    limit: int | None = None,
) -> list[tuple]:
    query = """
        SELECT id, timestamp, source, boundary, raw_event, compressed_event
        FROM events
        WHERE heimdall_decision IS NULL
          AND false_positive = 0
          AND raw_event IS NOT NULL
          AND TRIM(raw_event) != ''
        ORDER BY timestamp ASC, id ASC
    """
    if limit is not None:
        query += f" LIMIT {int(limit)}"
    return conn.execute(query).fetchall()


def update_event_decision(
    conn: sqlite3.Connection,
    db_path: str,
    logger: logging.Logger,
    event_id: int,
    compressed: str | None,
    decision: dict,
) -> sqlite3.Connection:
    """Persist backfilled compressed telemetry and Heimdall decision."""
    action = (
        decision.get("action_effective")
        or decision.get("action_required", "NONE")
    )
    params = (
        _normalize_compressed_event(compressed),
        json.dumps(decision),
        action,
        event_id,
    )

    def _update(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            UPDATE events
            SET compressed_event = COALESCE(?, compressed_event),
                heimdall_decision = ?,
                action_taken = ?
            WHERE id = ?
            """,
            params,
        )
        connection.commit()

    _, conn = execute_with_db_retry(conn, db_path, _update, logger)
    return conn


def process_event(
    router: EventRouter,
    conn: sqlite3.Connection,
    row: tuple,
    *,
    reuse_compressed: bool,
    dry_run: bool,
) -> tuple[sqlite3.Connection, str]:
    """
    Run one event through the reasoning pipeline and optionally persist.

    Returns (conn, status) where status is updated|skipped|dry_run|error.
    """
    event_id = row[0]
    raw_event = row[4]
    if raw_event is None or not str(raw_event).strip():
        return conn, "skipped"

    event, event_id, stored_compressed = row_to_event(row)

    if reuse_compressed and stored_compressed:
        compressed = _normalize_compressed_event(stored_compressed) or ""
    else:
        compressed = router.compress_event(event)

    decision = router._reason_event(event, compressed)
    decision = router.apply_policy_gate(decision, event)
    decision["execution_result"] = "backfill_skipped"
    decision["backfill"] = True

    if dry_run:
        return conn, "dry_run"

    conn = update_event_decision(
        conn,
        router.db_path,
        router.log,
        event_id,
        compressed,
        decision,
    )
    return conn, "updated"


def run_backfill(
    *,
    db_path: str,
    config: dict,
    limit: int | None = None,
    reuse_compressed: bool = True,
    dry_run: bool = False,
    progress_interval: int = 50,
    delay_seconds: float = 0.5,
) -> dict[str, int]:
    """Backfill NULL heimdall_decision rows in chronological order."""
    logger = logging.getLogger("heimdall.backfill")
    conn = sqlite3.connect(db_path)
    configure_sqlite_connection(conn)

    rows = fetch_pending_rows(conn, limit=limit)
    total = len(rows)
    logger.info("Found %d events pending backfill", total)

    if total == 0:
        conn.close()
        return {"total": 0, "updated": 0, "skipped": 0, "errors": 0, "dry_run": 0}

    router = EventRouter(Queue(maxsize=1), config, db_path, logger)
    stats = {"total": total, "updated": 0, "skipped": 0, "errors": 0, "dry_run": 0}
    started = time.monotonic()

    for index, row in enumerate(rows, start=1):
        event_id = row[0]
        try:
            conn, status = process_event(
                router,
                conn,
                row,
                reuse_compressed=reuse_compressed,
                dry_run=dry_run,
            )
            stats[status] += 1
        except Exception as exc:
            stats["errors"] += 1
            logger.error(
                "Backfill failed for event_id=%s: %s",
                event_id,
                exc,
                exc_info=True,
            )

        if progress_interval and index % progress_interval == 0:
            elapsed = time.monotonic() - started
            rate = index / elapsed if elapsed > 0 else 0.0
            classified = stats.get("updated", 0)
            logger.info(
                "Progress: %d/%d classified=%d skipped=%d errors=%d (%.2f ev/s)",
                index,
                total,
                classified,
                stats.get("skipped", 0),
                stats.get("errors", 0),
                rate,
            )
            print(
                f"[backfill] {index}/{total} processed, "
                f"{classified} decisions written",
                flush=True,
            )

        if delay_seconds > 0 and index < total:
            time.sleep(delay_seconds)

    router.flush_db()
    router.conn.close()
    conn.close()

    elapsed = time.monotonic() - started
    logger.info(
        "Backfill complete in %.1fs: %s",
        elapsed,
        stats,
    )
    return stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill heimdall_decision for historical events.",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="SQLite events database (default: from config / HEIMDALL_DB_PATH).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of pending rows to process.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run reasoning but do not write to the database.",
    )
    parser.add_argument(
        "--recompress",
        action="store_true",
        help="Re-run extractor even when compressed_event is already stored.",
    )
    parser.add_argument(
        "--progress-interval",
        type=int,
        default=50,
        help="Log progress every N events (0 to disable).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Seconds to wait between events (Ollama rate limit).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    )

    os.environ.setdefault("HEIMDALL_ENV", "development")
    config = load_config()
    refresh_runtime_paths(config)

    db_path = args.db_path or str(bifrost_paths.db_path(config))
    if not os.path.isfile(db_path):
        log.error("Database not found: %s", db_path)
        return 1

    log.info("Backfilling decisions in %s", db_path)
    stats = run_backfill(
        db_path=db_path,
        config=config,
        limit=args.limit,
        reuse_compressed=not args.recompress,
        dry_run=args.dry_run,
        progress_interval=args.progress_interval,
        delay_seconds=args.delay,
    )

    if stats.get("errors", 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
