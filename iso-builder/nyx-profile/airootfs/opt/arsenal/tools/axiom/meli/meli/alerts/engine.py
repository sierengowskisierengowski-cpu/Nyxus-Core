"""
Alert rule evaluation engine.
Evaluates each enabled AlertRule against incoming events,
respects cooldown periods and active hours, fires notifications.
"""
from __future__ import annotations

import json
import re
import time
import structlog
from datetime import datetime, timedelta, timezone

from meli.database import get_db
from meli.database.models import AlertRule, Alert, Attacker, Event
from meli.utils.helpers import severity_rank

log = structlog.get_logger()

# In-memory cooldown tracker: rule_id -> last_fired_timestamp
_cooldowns: dict[int, float] = {}


class AlertEngine:
    def evaluate(self, event_id: int, event: dict, severity: str) -> None:
        try:
            _inject_alert_context(event)
            with get_db() as db:
                from sqlalchemy import select
                rules = db.execute(
                    select(AlertRule).where(AlertRule.enabled == True)
                ).scalars().all()

                for rule in rules:
                    if self._should_fire(rule, event, severity):
                        self._fire(db, rule, event_id, event, severity)

        except Exception as e:
            log.error("Alert engine error", error=str(e))

    def _should_fire(self, rule: AlertRule, event: dict, severity: str) -> bool:
        # Severity threshold check
        if severity_rank(severity) < severity_rank(rule.severity_threshold):
            return False

        # Active hours check
        if rule.active_hours_start and rule.active_hours_end:
            now_time = datetime.now().strftime("%H:%M")
            if not self._in_active_hours(now_time, rule.active_hours_start, rule.active_hours_end):
                return False

        # Cooldown check
        last_fired = _cooldowns.get(rule.id, 0)
        cooldown = rule.cooldown_seconds or 300
        if time.time() - last_fired < cooldown:
            return False

        # Condition check
        if rule.conditions:
            try:
                conditions = json.loads(rule.conditions)
                if not self._conditions_match(conditions, event):
                    return False
            except Exception:
                pass

        return True

    def _conditions_match(self, conditions: list, event: dict) -> bool:
        for cond in conditions:
            field = cond.get("field", "")
            op = cond.get("operator", "eq")
            value = cond.get("value")
            ev_val = event.get(field, "")

            if op == "eq" and str(ev_val).lower() != str(value).lower():
                return False
            elif op == "in" and str(ev_val).lower() not in [str(v).lower() for v in (value or [])]:
                return False
            elif op == "regex":
                try:
                    if not re.search(value, str(ev_val), re.IGNORECASE):
                        return False
                except Exception:
                    return False
            elif op == "exists":
                if ev_val is None or ev_val == "":
                    return False
            elif op == "gte":
                try:
                    if float(ev_val or 0) < float(value):
                        return False
                except Exception:
                    return False
            elif op == "lte":
                try:
                    if float(ev_val or 0) > float(value):
                        return False
                except Exception:
                    return False
        return True

    def _fire(self, db, rule: AlertRule, event_id: int, event: dict, severity: str) -> None:
        now = datetime.now(timezone.utc)
        summary = self._build_summary(rule, event, severity)

        alert = Alert(
            rule_id=rule.id,
            rule_name=rule.name,
            triggered_at=now,
            event_id=event_id,
            severity=severity,
            summary=summary,
        )
        db.add(alert)
        db.flush()

        rule.last_triggered = now
        rule.fire_count = (rule.fire_count or 0) + 1

        _cooldowns[rule.id] = time.time()

        log.info("Alert fired", rule=rule.name, severity=severity, ip=event.get("source_ip"))

        # Send notifications async
        import threading
        channels = json.loads(rule.notification_channels or "[]")
        threading.Thread(
            target=_send_notifications,
            args=(channels, rule.name, summary, severity),
            daemon=True,
        ).start()

    def _build_summary(self, rule: AlertRule, event: dict, severity: str) -> str:
        ip = event.get("source_ip", "unknown")
        service = event.get("honeypot_service", "unknown")
        action = event.get("action_type", "unknown")
        return (
            f"[{severity}] Rule '{rule.name}' fired — "
            f"IP {ip} on {service} ({action})"
        )

    def _in_active_hours(self, now: str, start: str, end: str) -> bool:
        """Check if now (HH:MM) is within start-end range (may wrap midnight)."""
        if start <= end:
            return start <= now <= end
        # Wraps midnight
        return now >= start or now <= end


def _send_notifications(channels: list[str], rule_name: str, summary: str, severity: str) -> None:
    from meli.alerts import notifiers
    for channel in channels:
        try:
            if channel == "desktop":
                notifiers.desktop.notify(rule_name, summary, severity)
            elif channel == "sound":
                from meli.alerts.sound import play_alert_sound
                play_alert_sound(severity)
            elif channel == "discord":
                notifiers.discord.notify(rule_name, summary, severity)
            elif channel == "slack":
                notifiers.slack.notify(rule_name, summary, severity)
            elif channel == "telegram":
                notifiers.telegram.notify(rule_name, summary, severity)
            elif channel == "email":
                notifiers.email_smtp.notify(rule_name, summary, severity)
            elif channel == "webhook":
                notifiers.webhook.notify(rule_name, summary, severity)
            elif channel == "ntfy":
                notifiers.ntfy.notify(rule_name, summary, severity)
        except Exception as e:
            log.error("Notification failed", channel=channel, error=str(e))


def _inject_alert_context(event: dict) -> None:
    """
    Enrich the event dict with derived fields that built-in alert rules
    rely on but parsers don't natively produce:

    - ``attacker_is_new_7d``: True if the attacker IP has not been seen in
      the previous 7 days (either brand new, or last_seen > 7 days ago).
      The ingest processor computes this BEFORE upserting the Attacker row
      and sets it on the event; the engine only falls back to a fresh DB
      lookup when the field is missing (e.g. tests calling evaluate()
      directly).
    - ``attacker_login_attempts_1min``: count of login_attempt events from
      this source IP in the last 60 seconds. Only events whose
      ``action_type`` column equals ``login_attempt`` are counted, so the
      value reflects real login bursts and isn't inflated by web probes,
      file uploads, or generic connections from the same IP.
    """
    ip = event.get("source_ip")
    if not ip:
        return

    now = datetime.now(timezone.utc)
    seven_days_ago = now - timedelta(days=7)
    one_minute_ago = now - timedelta(seconds=60)

    try:
        from sqlalchemy import select, func
        with get_db() as db:
            if "attacker_is_new_7d" not in event:
                attacker = db.get(Attacker, ip)
                if attacker is None:
                    event["attacker_is_new_7d"] = True
                else:
                    last_seen = attacker.last_seen
                    # Handle naive datetimes coming from SQLite
                    if last_seen is not None and last_seen.tzinfo is None:
                        last_seen = last_seen.replace(tzinfo=timezone.utc)
                    event["attacker_is_new_7d"] = (
                        last_seen is None or last_seen < seven_days_ago
                    )

            count = db.execute(
                select(func.count(Event.id)).where(
                    Event.source_ip == ip,
                    Event.timestamp >= one_minute_ago,
                    Event.action_type == "login_attempt",
                )
            ).scalar() or 0

            # Make sure the current event counts too: when invoked from
            # the ingest pipeline the row is already persisted, but in
            # direct-evaluate paths (and edge cases where the action_type
            # column hasn't been populated yet) we add one for the event
            # under evaluation if it's itself a login attempt.
            if event.get("action_type") == "login_attempt":
                count = max(count, 1)
            event["attacker_login_attempts_1min"] = int(count)
    except Exception as e:
        log.debug("Alert context injection failed", error=str(e))


# ── Built-in seeded rules ────────────────────────────────────────────────────

BUILTIN_RULES: list[dict] = [
    {
        "name": "New attacker IP (first seen / silent 7+ days)",
        "description": (
            "Fires the first time a source IP is observed, or when an IP "
            "returns after at least 7 days of silence."
        ),
        "severity_threshold": "INFO",
        "conditions": [
            {"field": "attacker_is_new_7d", "operator": "eq", "value": True},
        ],
        "notification_channels": ["desktop", "webhook"],
        "cooldown_seconds": 0,
    },
    {
        "name": "Login brute-force burst (50+ attempts / minute)",
        "description": (
            "Fires when a single source IP makes 50 or more login attempts "
            "within a 60-second window."
        ),
        "severity_threshold": "INFO",
        "conditions": [
            {"field": "action_type", "operator": "eq", "value": "login_attempt"},
            {"field": "attacker_login_attempts_1min", "operator": "gte", "value": 50},
        ],
        "notification_channels": ["desktop", "webhook"],
        "cooldown_seconds": 60,
    },
]


def seed_builtin_alert_rules() -> None:
    """Insert built-in alert rules if they don't already exist (by name).

    Idempotent: only inserts rules whose name is not already present.
    User edits (enabled flag, channels, cooldown) are preserved across runs
    because we never overwrite an existing row.
    """
    try:
        from sqlalchemy import select
        with get_db() as db:
            existing = {
                r.name for r in db.execute(select(AlertRule)).scalars().all()
            }
            for spec in BUILTIN_RULES:
                if spec["name"] in existing:
                    continue
                db.add(AlertRule(
                    name=spec["name"],
                    description=spec.get("description"),
                    enabled=True,
                    severity_threshold=spec["severity_threshold"],
                    conditions=json.dumps(spec["conditions"]),
                    notification_channels=json.dumps(spec["notification_channels"]),
                    cooldown_seconds=spec.get("cooldown_seconds", 300),
                ))
                log.info("Seeded built-in alert rule", name=spec["name"])
    except Exception as e:
        log.error("Failed to seed built-in alert rules", error=str(e))
