"""Tests for the GeoLite2 auto-update scheduler."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import meli.enrichment.geoip_scheduler as sched
from meli.config import get_config


def _reset_state() -> None:
    cfg = get_config()
    cfg.set("enrichment", "maxmind_license_key", None)
    cfg.set("enrichment", "geoip_auto_update_enabled", True)
    cfg.set("enrichment", "geoip_auto_update_interval_days", 7)
    cfg.set("enrichment", "geoip_last_auto_update_at", None)
    cfg.set("enrichment", "geoip_last_auto_update_status", None)
    cfg.set("enrichment", "geoip_last_auto_update_error", None)


def test_skips_when_no_license_key():
    _reset_state()
    calls: list[tuple] = []
    result = sched.run_update_once(downloader=lambda k, d: calls.append((k, d)) or True)
    assert result == "skipped_no_key"
    assert calls == []
    assert get_config().get("enrichment", "geoip_last_auto_update_status") == "skipped_no_key"


def test_skips_when_disabled():
    _reset_state()
    cfg = get_config()
    cfg.set("enrichment", "maxmind_license_key", "abc")
    cfg.set("enrichment", "geoip_auto_update_enabled", False)
    calls: list[tuple] = []
    result = sched.run_update_once(downloader=lambda k, d: calls.append((k, d)) or True)
    assert result == "skipped_disabled"
    assert calls == []


def test_records_success():
    _reset_state()
    get_config().set("enrichment", "maxmind_license_key", "abc")
    result = sched.run_update_once(downloader=lambda k, d: True)
    cfg = get_config()
    assert result == "success"
    assert cfg.get("enrichment", "geoip_last_auto_update_status") == "success"
    assert cfg.get("enrichment", "geoip_last_auto_update_at") is not None
    assert cfg.get("enrichment", "geoip_last_auto_update_error") is None


def test_records_failure_on_false():
    _reset_state()
    get_config().set("enrichment", "maxmind_license_key", "abc")
    result = sched.run_update_once(downloader=lambda k, d: False)
    cfg = get_config()
    assert result == "failure"
    assert cfg.get("enrichment", "geoip_last_auto_update_status") == "failure"
    assert cfg.get("enrichment", "geoip_last_auto_update_error")


def test_records_failure_on_exception():
    _reset_state()
    get_config().set("enrichment", "maxmind_license_key", "abc")

    def boom(k, d):
        raise RuntimeError("network down")

    result = sched.run_update_once(downloader=boom)
    cfg = get_config()
    assert result == "failure"
    assert cfg.get("enrichment", "geoip_last_auto_update_status") == "failure"
    assert "network down" in (cfg.get("enrichment", "geoip_last_auto_update_error") or "")


def test_is_due_logic():
    _reset_state()
    now = datetime.now(tz=timezone.utc)
    assert sched._is_due(now) is True  # never run
    get_config().set(
        "enrichment",
        "geoip_last_auto_update_at",
        (now - timedelta(days=2)).isoformat(timespec="seconds"),
    )
    assert sched._is_due(now) is False  # interval 7 days
    get_config().set(
        "enrichment",
        "geoip_last_auto_update_at",
        (now - timedelta(days=8)).isoformat(timespec="seconds"),
    )
    assert sched._is_due(now) is True
