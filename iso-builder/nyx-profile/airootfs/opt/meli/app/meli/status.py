"""
Machine-readable status surface for external callers (e.g. the Bifrost UI).

Everything here is read-only and headless (no GTK, no auth) so it is safe to
invoke from `meli --status` / `meli --report ...` in a shell-out context.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import structlog

log = structlog.get_logger()


def _db_counts() -> dict[str, int]:
    from meli.database import get_db
    from meli.database.models import (
        Event, Attacker, Credential, Command, Payload, Alert, Report,
    )
    from sqlalchemy import func, select
    out: dict[str, int] = {}
    with get_db() as db:
        for name, model in (
            ("events", Event), ("attackers", Attacker),
            ("credentials", Credential), ("commands", Command),
            ("payloads", Payload), ("alerts", Alert), ("reports", Report),
        ):
            pk = list(model.__table__.primary_key.columns)[0]
            out[name] = db.execute(select(func.count(pk))).scalar() or 0
    return out


def _alert_config() -> dict[str, Any]:
    from meli.config import get_config
    cfg = get_config()
    # Which notification channels are configured (without leaking secrets).
    def _set(*path):
        return bool(cfg.get(*path))
    return {
        "desktop_notifications": cfg.get("alerts", "desktop_notifications", default=True),
        "sound_enabled": cfg.get("alerts", "sound_enabled", default=True),
        "channels_configured": {
            "discord": _set("alerts", "discord_webhook"),
            "slack": _set("alerts", "slack_webhook"),
            "telegram": _set("alerts", "telegram_bot_token") and _set("alerts", "telegram_chat_id"),
            "email": _set("alerts", "email_smtp_host") and _set("alerts", "email_to"),
        },
        "quiet_hours_enabled": cfg.get("alerts", "quiet_hours_enabled", default=False),
    }


def _alert_rules() -> list[dict[str, Any]]:
    from meli.database import get_db
    from meli.database.models import AlertRule
    from sqlalchemy import select
    rules = []
    with get_db() as db:
        for r in db.execute(select(AlertRule)).scalars().all():
            rules.append({
                "id": r.id,
                "name": r.name,
                "enabled": bool(r.enabled),
                "severity_threshold": r.severity_threshold,
                "fire_count": r.fire_count or 0,
                "last_triggered": str(r.last_triggered) if r.last_triggered else None,
            })
    return rules


def _recent_reports(limit: int = 10) -> list[dict[str, Any]]:
    from meli.database import get_db
    from meli.database.models import Report
    from sqlalchemy import select
    out = []
    with get_db() as db:
        rows = db.execute(
            select(Report).order_by(Report.generated_at.desc()).limit(limit)
        ).scalars().all()
        for r in rows:
            out.append({
                "id": r.id,
                "type": r.report_type,
                "format": r.report_format,
                "generated_at": str(r.generated_at),
                "file_path": r.file_path,
                "summary": r.summary,
            })
    return out


def build_status() -> dict[str, Any]:
    """Assemble the full read-only status blob for the Bifrost UI."""
    from meli.config import get_config
    from meli.enrichment import provider_status
    cfg = get_config()
    status: dict[str, Any] = {
        "service": "meli",
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        status["db_counts"] = _db_counts()
    except Exception as e:  # noqa: BLE001
        status["db_counts"] = {"error": str(e)}
    try:
        status["alerts"] = {"config": _alert_config(), "rules": _alert_rules()}
    except Exception as e:  # noqa: BLE001
        status["alerts"] = {"error": str(e)}
    try:
        status["enrichment_providers"] = provider_status()
    except Exception as e:  # noqa: BLE001
        status["enrichment_providers"] = {"error": str(e)}
    try:
        status["reports"] = {
            "output_path": cfg.get("reports", "output_path"),
            "recent": _recent_reports(),
        }
    except Exception as e:  # noqa: BLE001
        status["reports"] = {"error": str(e)}
    return status


def status_json() -> str:
    return json.dumps(build_status(), indent=2, default=str)
