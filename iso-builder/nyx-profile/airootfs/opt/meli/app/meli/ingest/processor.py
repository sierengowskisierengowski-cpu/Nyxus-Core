"""
Event processor — classifies, enriches, stores, and fires alerts.
Called by both the MQTT handler and HTTP ingest handler.
"""
from __future__ import annotations

import hashlib
import json
import threading
import time
import structlog
from datetime import datetime, timezone

log = structlog.get_logger()

# Striped per-IP locking: a fixed-size array of locks indexed by a hash
# of the IP. Two simultaneous events from the same brand-new attacker
# always hash to the same lock, so the second one waits and sees the
# row the first one inserted (preventing the UNIQUE-constraint crash).
# Unrelated IPs collide only ~1/N of the time, so ingest stays parallel.
# Crucially, memory is bounded — earlier per-IP dict grew without limit
# on internet-facing honeypots.
_LOCK_STRIPES = 256
_attacker_stripe_locks: tuple[threading.Lock, ...] = tuple(
    threading.Lock() for _ in range(_LOCK_STRIPES)
)


def _lock_for_ip(ip: str) -> threading.Lock:
    # Hash so adjacent IPs distribute evenly across stripes.
    h = int.from_bytes(hashlib.md5(ip.encode("utf-8", "replace")).digest()[:4], "big")
    return _attacker_stripe_locks[h % _LOCK_STRIPES]


def _as_utc(dt):
    """Coerce a datetime to timezone-aware UTC.

    SQLite hands values from ``DateTime(timezone=True)`` columns back as
    *naive* datetimes, while freshly-parsed event timestamps are *aware*.
    Comparing the two raises TypeError, so normalise before any comparison.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def process_event(raw: dict, source: str = "mqtt",
                  dedup_uuid: str | None = None, live: bool = True) -> bool:
    """Full event pipeline: parse → classify → store → enrich → alert.

    Returns True if a new event row was written, False if it was skipped
    (unparseable, or a duplicate when ``dedup_uuid`` is supplied).

    ``dedup_uuid`` — when set, the event is stored with this deterministic
    UUID and skipped entirely if a row with that UUID already exists. This
    makes bulk/backfill imports idempotent (safe to re-run).

    ``live`` — when False (backfill/import), the per-event alert, enrichment,
    MQTT re-publish, and in-process UI signal side effects are suppressed so
    a large import doesn't stampede the running daemon. Aggregation tables
    are still populated.
    """
    try:
        from meli.ingest.parsers.generic_json import GenericJsonParser
        from meli.classification.severity import classify_event
        from meli.enrichment.geolocation import geolocate_ip
        from meli.database import get_db
        from meli.database.models import Event, Attacker

        # Normalise to internal format
        parser = GenericJsonParser()
        normalized = parser.parse(raw)
        if not normalized:
            log.debug("Event skipped by parser", raw_keys=list(raw.keys()))
            return False

        # Carry through trusted in-band fields from internal sources
        # (Labyrinth tarpit emits canary-trip / honeytoken events whose
        # severity is set authoritatively by the trap itself — these
        # are not adversary-controlled, so we honor them instead of
        # routing through classify_event's heuristic rules). The eventid
        # is preserved into normalized so downstream alert rules can
        # target 'labyrinth.canary.tripped' specifically.
        inline_severity = None
        if source == "labyrinth":
            ev_id = raw.get("eventid")
            if ev_id:
                normalized["eventid"] = ev_id
            for k in ("canary_token", "canary_path", "canary_summary",
                      "bot_score", "bot_confidence"):
                if k in raw:
                    normalized[k] = raw[k]
            raw_sev = raw.get("severity")
            if isinstance(raw_sev, str) and raw_sev.upper() in (
                "INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"
            ):
                inline_severity = raw_sev.upper()

        # Classify (heuristic). For trusted inline severity, take the
        # MAX of rule-derived and inline so we never silently demote a
        # canary trip and we still pick up any rule-added matches.
        severity, matched_rules = classify_event(normalized)
        if inline_severity is not None:
            from meli.utils.helpers import severity_rank
            if severity_rank(inline_severity) > severity_rank(severity):
                severity = inline_severity
                matched_rules = list(matched_rules) + ["labyrinth.inline-severity"]
        normalized["severity"] = severity
        normalized["classification_rules_matched"] = json.dumps(matched_rules)

        # Geolocate
        ip = normalized.get("source_ip", "")
        geo = geolocate_ip(ip)
        normalized["country_code"] = geo.get("country_code")

        # ── Atomic event + attacker write ─────────────────────────
        # Hold the per-IP stripe lock around the WHOLE transaction so:
        #   (a) the UNIQUE(Attacker.ip) race is closed (two threads on
        #       the same brand-new IP can't both INSERT), and
        #   (b) we never commit an event without the corresponding
        #       attacker upsert (no aggregate drift even if the DB is
        #       transiently locked).
        # On SQLite, retry up to 3 times when the writer lock is held by
        # someone else (WAL "database is locked" appears as OperationalError).
        from sqlalchemy.exc import OperationalError, IntegrityError
        from meli.utils.helpers import severity_rank
        # Event timestamp drives aggregation first/last-seen bookkeeping too,
        # so both the historical importer and live path stay consistent.
        ev_ts = normalized.get("timestamp") or datetime.now(timezone.utc)
        if not isinstance(ev_ts, datetime):
            ev_ts = datetime.now(timezone.utc)
        event_id = None
        stored = False
        attempts = 3
        last_exc = None
        for attempt in range(attempts):
            try:
                with _lock_for_ip(ip):
                    with get_db() as db:
                        # Idempotency: on a backfill/re-import, skip events
                        # we've already stored (keyed by deterministic UUID).
                        if dedup_uuid is not None:
                            from sqlalchemy import select
                            existing = db.execute(
                                select(Event.id).where(Event.event_uuid == dedup_uuid)
                            ).first()
                            if existing:
                                return False

                        ev = Event(
                            timestamp=ev_ts,
                            source_ip=normalized.get("source_ip", ""),
                            source_port=normalized.get("source_port"),
                            destination_port=normalized.get("destination_port"),
                            honeypot_service=normalized.get("honeypot_service", "unknown"),
                            protocol=normalized.get("protocol"),
                            transport=normalized.get("transport"),
                            severity=severity,
                            parsed_data=json.dumps(normalized, default=str),
                            session_id=normalized.get("session_id"),
                            country_code=normalized.get("country_code"),
                            username=normalized.get("username"),
                            password=normalized.get("password"),
                            command=normalized.get("command"),
                            payload_hash=normalized.get("payload_hash"),
                            classification_rules_matched=normalized["classification_rules_matched"],
                            enrichment_status="pending",
                        )
                        if dedup_uuid is not None:
                            ev.event_uuid = dedup_uuid
                        db.add(ev)
                        db.flush()
                        event_id = ev.id

                        attacker = db.get(Attacker, ip)
                        if attacker:
                            if ev_ts > (_as_utc(attacker.last_seen) or ev_ts):
                                attacker.last_seen = ev_ts
                            if attacker.first_seen and ev_ts < _as_utc(attacker.first_seen):
                                attacker.first_seen = ev_ts
                            attacker.total_events += 1
                            if severity_rank(severity) > severity_rank(attacker.max_severity):
                                attacker.max_severity = severity
                        else:
                            db.add(Attacker(
                                ip=ip,
                                first_seen=ev_ts,
                                last_seen=ev_ts,
                                total_events=1,
                                max_severity=severity,
                                country_code=normalized.get("country_code"),
                            ))

                        # Populate the dedicated aggregation tables
                        # (credentials / commands / payloads) in the SAME
                        # transaction so counts never drift from events.
                        _update_aggregates(db, normalized, ev_ts)
                stored = True
                break  # success
            except (OperationalError, IntegrityError) as oe:
                last_exc = oe
                # SQLite writer-lock contention (OperationalError) or a race
                # on a shared credential/command/payload unique key
                # (IntegrityError) — the whole transaction rolled back, so
                # back off and retry cleanly; the second pass sees the row
                # the racing writer inserted and just increments its count.
                time.sleep(0.05 * (attempt + 1))
        else:
            # All retries exhausted: log loudly and bail. Neither row
            # was committed because each attempt was a single transaction.
            log.error("Event+attacker write failed after retries",
                      ip=ip, attempts=attempts, error=str(last_exc))
            return False

        if not live:
            # Backfill/import mode: skip per-event alerting, enrichment,
            # MQTT re-publish and UI signalling. Callers batch-enrich the
            # unique attacker set once at the end instead.
            return stored

        # Fire alerts asynchronously
        threading.Thread(
            target=_check_alerts,
            args=(event_id, normalized, severity),
            daemon=True,
        ).start()

        # Enrich IP asynchronously
        threading.Thread(
            target=_enrich_ip,
            args=(ip,),
            daemon=True,
        ).start()

        # Publish to processed MQTT topic
        _publish_processed(normalized)

        # In-process signal so the dashboard pot pulses in real time.
        # Subscribers re-dispatch to the GTK main loop themselves.
        try:
            from meli import event_bus
            event_bus.publish("event.ingested", {
                "severity": severity,
                "source_ip": ip,
                "honeypot_service": normalized.get("honeypot_service", "unknown"),
            })
        except Exception:
            pass

        log.debug("Event processed", ip=ip, severity=severity, source=source)
        return stored

    except Exception as e:
        log.error("Event processing error", error=str(e), exc_info=True)
        return False


def _merge_json_list(existing: str | None, value: str, cap: int = 500) -> str:
    """Merge ``value`` into a JSON-encoded list column, de-duplicated + capped."""
    try:
        items = json.loads(existing) if existing else []
        if not isinstance(items, list):
            items = []
    except (ValueError, TypeError):
        items = []
    if value and value not in items:
        items.append(value)
        if len(items) > cap:
            items = items[-cap:]
    return json.dumps(items)


def _update_aggregates(db, normalized: dict, ev_ts: datetime) -> None:
    """Upsert the credentials / commands / payloads aggregation tables.

    Runs inside the caller's transaction. Each distinct credential pair,
    command string, and payload hash is stored once with running counts and
    first/last-seen bookkeeping, plus the set of source honeypots / IPs.
    """
    from meli.database.models import Credential, Command, Payload
    from meli.utils.helpers import classify_command_intent
    from sqlalchemy import select

    service = (normalized.get("honeypot_service") or "unknown")
    ip = normalized.get("source_ip") or ""

    # ── Credentials (username + password pair) ────────────────────────
    username = normalized.get("username")
    password = normalized.get("password")
    if (username is not None and username != "") or (password is not None and password != ""):
        u = username or ""
        p = password or ""
        cred = db.execute(
            select(Credential).where(
                Credential.username == u, Credential.password == p
            )
        ).scalar_one_or_none()
        if cred:
            cred.attempt_count = (cred.attempt_count or 0) + 1
            if ev_ts > (_as_utc(cred.last_seen) or ev_ts):
                cred.last_seen = ev_ts
            if cred.first_seen and ev_ts < _as_utc(cred.first_seen):
                cred.first_seen = ev_ts
            cred.source_honeypots = _merge_json_list(cred.source_honeypots, service, cap=50)
            cred.source_ips = _merge_json_list(cred.source_ips, ip)
        else:
            db.add(Credential(
                username=u,
                password=p,
                attempt_count=1,
                first_seen=ev_ts,
                last_seen=ev_ts,
                source_honeypots=json.dumps([service] if service else []),
                source_ips=json.dumps([ip] if ip else []),
            ))

    # ── Commands (post-auth shell input) ──────────────────────────────
    command = normalized.get("command")
    if command:
        cmd = db.execute(
            select(Command).where(Command.command_text == command)
        ).scalar_one_or_none()
        if cmd:
            cmd.execution_count = (cmd.execution_count or 0) + 1
            if ev_ts > (_as_utc(cmd.last_seen) or ev_ts):
                cmd.last_seen = ev_ts
            if cmd.first_seen and ev_ts < _as_utc(cmd.first_seen):
                cmd.first_seen = ev_ts
            cmd.source_ips = _merge_json_list(cmd.source_ips, ip)
            if not cmd.detected_intent or cmd.detected_intent == "unknown":
                cmd.detected_intent = classify_command_intent(command)
        else:
            db.add(Command(
                command_text=command,
                execution_count=1,
                detected_intent=classify_command_intent(command),
                first_seen=ev_ts,
                last_seen=ev_ts,
                source_ips=json.dumps([ip] if ip else []),
            ))

    # ── Payloads (captured sample hashes) ─────────────────────────────
    payload_hash = normalized.get("payload_hash")
    if payload_hash and len(str(payload_hash)) >= 32:
        sha256 = str(payload_hash)
        exists = db.execute(
            select(Payload.id).where(Payload.sha256 == sha256)
        ).first()
        if not exists:
            filename = normalized.get("payload_filename") or ""
            file_type = None
            if "." in str(filename):
                file_type = str(filename).rsplit(".", 1)[-1][:100]
            db.add(Payload(
                sha256=sha256,
                file_type=file_type,
                captured_at=ev_ts,
                source_ip=ip,
                source_honeypot=service,
                file_path=normalized.get("payload_filename"),
            ))


def _check_alerts(event_id: int, event: dict, severity: str) -> None:
    try:
        from meli.alerts.engine import AlertEngine
        engine = AlertEngine()
        engine.evaluate(event_id, event, severity)
    except Exception as e:
        log.error("Alert check failed", error=str(e))


def _enrich_ip(ip: str) -> None:
    try:
        from meli.enrichment import enrich_ip
        enrich_ip(ip)
    except Exception as e:
        log.debug("Enrichment failed", ip=ip, error=str(e))


def _publish_processed(event: dict) -> None:
    try:
        import paho.mqtt.publish as publish
        from meli.config import get_config
        cfg = get_config()
        publish.single(
            topic=cfg.get("mqtt", "topic_processed", default="meli/events/processed"),
            payload=json.dumps(event, default=str),
            hostname=cfg.get("mqtt", "host", default="127.0.0.1"),
            port=cfg.get("mqtt", "port", default=1883),
            qos=0,
        )
    except Exception:
        pass  # MQTT publish failure is non-fatal
