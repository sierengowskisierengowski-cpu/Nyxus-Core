"""Background scheduler that periodically refreshes the local
MaxMind GeoLite2 City + ASN databases.

MaxMind ships new GeoLite2 databases roughly twice a week. Without this
scheduler the user must remember to click "Download / Update GeoLite2
Databases Now" in Settings and the data drifts. This worker re-runs
``download_geolite2`` on a configurable interval (default: weekly) whenever
``enrichment.maxmind_license_key`` is set, records the last-attempt
timestamp + result in config, and never crashes the host daemon.
"""
from __future__ import annotations

import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import structlog

from meli.config import get_config

log = structlog.get_logger()

_TICK_SECONDS = 60 * 15  # re-check eligibility every 15 minutes


def _utcnow_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat(timespec="seconds")


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _record_result(status: str, error: str | None = None) -> None:
    cfg = get_config()
    cfg.set("enrichment", "geoip_last_auto_update_at", _utcnow_iso())
    cfg.set("enrichment", "geoip_last_auto_update_status", status)
    cfg.set("enrichment", "geoip_last_auto_update_error", error)


def _is_due(now: datetime) -> bool:
    cfg = get_config()
    interval_days = int(
        cfg.get("enrichment", "geoip_auto_update_interval_days", default=7) or 7
    )
    last = _parse_iso(cfg.get("enrichment", "geoip_last_auto_update_at"))
    if last is None:
        return True
    return (now - last) >= timedelta(days=interval_days)


def run_update_once(
    downloader: Callable[[str, str], bool] | None = None,
) -> str:
    """Run a single update attempt synchronously.

    Returns one of: ``"success"``, ``"failure"``, ``"skipped_no_key"``,
    ``"skipped_disabled"``. Always records the outcome in config (except
    when disabled, to avoid spamming the status row).
    """
    cfg = get_config()

    if not cfg.get("enrichment", "geoip_auto_update_enabled", default=True):
        return "skipped_disabled"

    key = cfg.get("enrichment", "maxmind_license_key")
    if not key:
        _record_result("skipped_no_key", error="No MaxMind license key configured")
        return "skipped_no_key"

    output_dir = str(cfg.data_dir / "geoip")

    if downloader is None:
        from meli.enrichment.geolocation import download_geolite2 as downloader  # type: ignore

    try:
        ok = downloader(key, output_dir)
    except Exception as e:  # never let a bad download crash the daemon
        log.error("GeoLite2 auto-update raised", error=str(e))
        _record_result("failure", error=str(e))
        return "failure"

    if ok:
        log.info("GeoLite2 auto-update succeeded", dest=output_dir)
        _record_result("success")
        return "success"

    log.warning("GeoLite2 auto-update failed", dest=output_dir)
    _record_result("failure", error="download_geolite2 returned False")
    return "failure"


class GeoIPUpdateScheduler:
    """Tiny background scheduler that runs ``run_update_once`` periodically.

    Runs in a daemon thread. Wakes every ``_TICK_SECONDS`` seconds, checks
    whether the configured interval has elapsed since the last attempt, and
    if so triggers a download. Cleanly stoppable via :meth:`stop`.
    """

    def __init__(
        self,
        tick_seconds: int = _TICK_SECONDS,
        downloader: Callable[[str, str], bool] | None = None,
    ) -> None:
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._tick_seconds = max(1, int(tick_seconds))
        self._downloader = downloader

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="geoip-auto-update"
        )
        self._thread.start()
        log.info(
            "GeoLite2 auto-update scheduler started",
            interval_days=get_config().get(
                "enrichment", "geoip_auto_update_interval_days", default=7
            ),
        )

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception as e:  # belt and suspenders
                log.error("GeoLite2 scheduler tick failed", error=str(e))
            # Sleep in 1s chunks so stop() is responsive
            for _ in range(self._tick_seconds):
                if self._stop_event.is_set():
                    return
                self._stop_event.wait(1.0)

    def _tick(self) -> None:
        cfg = get_config()
        if not cfg.get("enrichment", "geoip_auto_update_enabled", default=True):
            return
        if not cfg.get("enrichment", "maxmind_license_key"):
            return
        if not _is_due(datetime.now(tz=timezone.utc)):
            return
        log.info("GeoLite2 auto-update due — starting download")
        run_update_once(downloader=self._downloader)
