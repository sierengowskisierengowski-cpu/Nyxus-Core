"""End-to-end tests for the alert engine: context injection, built-in
rule seeding, rule evaluation, and notifier dispatch."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import select


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Spin up a fresh isolated SQLite DB for each test.

    ``_DATA_DIR`` in ``meli.config`` is evaluated at module import time, so
    flipping env vars alone won't change the SQLite path. We force a unique
    DB path per test by stubbing ``Config.db_path``.
    """
    import meli.database.models as models_mod
    import meli.database as db_mod
    import meli.alerts.engine as engine_mod
    import meli.config as cfg_mod

    monkeypatch.setenv("MELI_CONFIG_DIR", str(tmp_path / "cfg"))
    monkeypatch.setenv("MELI_DATA_DIR", str(tmp_path / "data"))
    (tmp_path / "cfg").mkdir()
    (tmp_path / "data").mkdir()

    test_db_path = str(tmp_path / "meli.db")
    monkeypatch.setattr(
        cfg_mod.Config, "db_path",
        property(lambda self: test_db_path),
    )

    # Reset module-level singletons
    cfg_mod._config = None
    models_mod._engine = None
    models_mod._SessionLocal = None
    engine_mod._cooldowns.clear()

    db_mod.init_db()
    yield
    eng = models_mod._engine
    if eng is not None:
        eng.dispose()
    models_mod._engine = None
    models_mod._SessionLocal = None


# ─── Built-in rule seeding ─────────────────────────────────────────────────

def test_seed_inserts_both_builtin_rules():
    from meli.database import get_db
    from meli.database.models import AlertRule

    with get_db() as db:
        names = {r.name for r in db.execute(select(AlertRule)).scalars().all()}
    assert "New attacker IP (first seen / silent 7+ days)" in names
    assert "Login brute-force burst (50+ attempts / minute)" in names


def test_seed_is_idempotent():
    from meli.alerts.engine import seed_builtin_alert_rules
    from meli.database import get_db
    from meli.database.models import AlertRule

    seed_builtin_alert_rules()
    seed_builtin_alert_rules()
    with get_db() as db:
        names = [r.name for r in db.execute(select(AlertRule)).scalars().all()]
    # Each built-in name appears exactly once
    assert names.count("New attacker IP (first seen / silent 7+ days)") == 1
    assert names.count("Login brute-force burst (50+ attempts / minute)") == 1


def test_seed_preserves_user_edits():
    """If a user disables a built-in rule, re-seeding must not re-enable it."""
    from meli.alerts.engine import seed_builtin_alert_rules
    from meli.database import get_db
    from meli.database.models import AlertRule

    with get_db() as db:
        rule = db.execute(
            select(AlertRule).where(AlertRule.name.like("New attacker IP%"))
        ).scalar_one()
        rule.enabled = False
        rule.cooldown_seconds = 999

    seed_builtin_alert_rules()

    with get_db() as db:
        rule = db.execute(
            select(AlertRule).where(AlertRule.name.like("New attacker IP%"))
        ).scalar_one()
        assert rule.enabled is False
        assert rule.cooldown_seconds == 999


# ─── Context injection ────────────────────────────────────────────────────

def test_context_marks_unseen_ip_as_new():
    from meli.alerts.engine import _inject_alert_context

    event = {"source_ip": "203.0.113.99"}
    _inject_alert_context(event)
    assert event["attacker_is_new_7d"] is True
    assert event["attacker_login_attempts_1min"] == 0


def test_context_marks_recently_seen_ip_as_not_new():
    from meli.alerts.engine import _inject_alert_context
    from meli.database import get_db
    from meli.database.models import Attacker

    now = datetime.now(timezone.utc)
    with get_db() as db:
        db.add(Attacker(
            ip="198.51.100.7",
            first_seen=now - timedelta(days=2),
            last_seen=now - timedelta(hours=1),
            total_events=4,
            max_severity="LOW",
        ))

    event = {"source_ip": "198.51.100.7"}
    _inject_alert_context(event)
    assert event["attacker_is_new_7d"] is False


def test_context_marks_long_silent_ip_as_new_again():
    from meli.alerts.engine import _inject_alert_context
    from meli.database import get_db
    from meli.database.models import Attacker

    now = datetime.now(timezone.utc)
    with get_db() as db:
        db.add(Attacker(
            ip="198.51.100.8",
            first_seen=now - timedelta(days=60),
            last_seen=now - timedelta(days=30),
            total_events=10,
            max_severity="LOW",
        ))

    event = {"source_ip": "198.51.100.8"}
    _inject_alert_context(event)
    assert event["attacker_is_new_7d"] is True


def test_context_counts_login_attempts_in_last_minute():
    from meli.alerts.engine import _inject_alert_context
    from meli.database import get_db
    from meli.database.models import Event

    now = datetime.now(timezone.utc)
    with get_db() as db:
        # 3 recent login attempts
        for i in range(3):
            db.add(Event(
                timestamp=now - timedelta(seconds=10 * i),
                source_ip="192.0.2.42",
                honeypot_service="cowrie",
                severity="LOW",
                action_type="login_attempt",
            ))
        # 1 old login attempt (> 60s ago) — should not count
        db.add(Event(
            timestamp=now - timedelta(seconds=120),
            source_ip="192.0.2.42",
            honeypot_service="cowrie",
            severity="LOW",
            action_type="login_attempt",
        ))
        # Recent non-login events from the same IP — must NOT inflate the count
        for atype in ("connection", "web_request", "file_upload"):
            db.add(Event(
                timestamp=now - timedelta(seconds=5),
                source_ip="192.0.2.42",
                honeypot_service="cowrie",
                severity="LOW",
                action_type=atype,
            ))

    event = {"source_ip": "192.0.2.42", "action_type": "connection"}
    _inject_alert_context(event)
    assert event["attacker_login_attempts_1min"] == 3


# ─── End-to-end rule firing via the engine ────────────────────────────────

def _create_real_event(ip: str = "203.0.113.222") -> int:
    """Insert a real Event row so Alert FK to events.id can resolve."""
    from meli.database import get_db
    from meli.database.models import Event

    with get_db() as db:
        ev = Event(
            timestamp=datetime.now(timezone.utc),
            source_ip=ip,
            honeypot_service="cowrie",
            severity="INFO",
        )
        db.add(ev)
        db.flush()
        return ev.id


def test_new_ip_rule_fires_and_invokes_webhook():
    from meli.alerts.engine import AlertEngine
    from meli.database import get_db
    from meli.database.models import Alert
    from meli.config import get_config

    cfg = get_config()
    cfg.set("alerts", "webhook_url", "https://example.test/hook")

    ip = "203.0.113.222"
    event_id = _create_real_event(ip)
    engine = AlertEngine()
    event = {
        "source_ip": ip,
        "honeypot_service": "cowrie",
        "action_type": "connection",
    }

    with patch("meli.alerts.notifiers.webhook.requests.post") as post:
        engine.evaluate(event_id=event_id, event=event, severity="INFO")
        # Notifications fire on a background thread
        import time
        for _ in range(50):
            if post.called:
                break
            time.sleep(0.02)

    assert post.called, "webhook notifier should have been invoked"
    url, kwargs = post.call_args.args, post.call_args.kwargs
    assert url[0] == "https://example.test/hook"
    payload = kwargs["json"]
    assert payload["source"] == "meli"
    assert "New attacker IP" in payload["rule"]

    with get_db() as db:
        names = [a.rule_name for a in db.execute(select(Alert)).scalars().all()]
    assert any("New attacker IP" in n for n in names)


def test_brute_force_burst_rule_fires_on_50_login_attempts():
    from meli.alerts.engine import AlertEngine
    from meli.database import get_db
    from meli.database.models import Event, Alert

    now = datetime.now(timezone.utc)
    ip = "198.51.100.99"
    # Seed 60 recent login_attempt events from this IP
    with get_db() as db:
        for i in range(60):
            db.add(Event(
                timestamp=now - timedelta(seconds=i),
                source_ip=ip,
                honeypot_service="cowrie",
                severity="LOW",
                action_type="login_attempt",
            ))

    # Disable the "new IP" rule so we only assert on the burst rule
    from meli.database.models import AlertRule
    with get_db() as db:
        new_rule = db.execute(
            select(AlertRule).where(AlertRule.name.like("New attacker IP%"))
        ).scalar_one()
        new_rule.enabled = False

    engine = AlertEngine()
    event = {
        "source_ip": ip,
        "honeypot_service": "cowrie",
        "action_type": "login_attempt",
    }
    event_id = _create_real_event(ip)

    with patch("meli.alerts.notifiers.webhook.requests.post"):
        engine.evaluate(event_id=event_id, event=event, severity="INFO")

    with get_db() as db:
        names = [a.rule_name for a in db.execute(select(Alert)).scalars().all()]
    assert any("brute-force burst" in n for n in names), \
        f"Expected brute-force alert, got: {names}"


def test_brute_force_rule_does_not_fire_below_threshold():
    from meli.alerts.engine import AlertEngine
    from meli.database import get_db
    from meli.database.models import Event, Alert, AlertRule

    now = datetime.now(timezone.utc)
    ip = "198.51.100.50"
    # Only 10 recent login attempts — well under 50
    with get_db() as db:
        for i in range(10):
            db.add(Event(
                timestamp=now - timedelta(seconds=i),
                source_ip=ip,
                honeypot_service="cowrie",
                severity="LOW",
                action_type="login_attempt",
            ))
        # Pre-existing attacker so "new IP" rule doesn't also fire
        from meli.database.models import Attacker
        db.add(Attacker(
            ip=ip,
            first_seen=now - timedelta(days=1),
            last_seen=now - timedelta(minutes=1),
            total_events=10,
            max_severity="LOW",
        ))

    engine = AlertEngine()
    event = {
        "source_ip": ip,
        "honeypot_service": "cowrie",
        "action_type": "login_attempt",
    }
    event_id = _create_real_event(ip)
    with patch("meli.alerts.notifiers.webhook.requests.post"):
        engine.evaluate(event_id=event_id, event=event, severity="INFO")

    with get_db() as db:
        burst_alerts = db.execute(
            select(Alert).where(Alert.rule_name.like("%brute-force%"))
        ).scalars().all()
    assert burst_alerts == []


def test_disabled_rule_does_not_fire():
    from meli.alerts.engine import AlertEngine
    from meli.database import get_db
    from meli.database.models import AlertRule, Alert

    with get_db() as db:
        for r in db.execute(select(AlertRule)).scalars().all():
            r.enabled = False

    engine = AlertEngine()
    with patch("meli.alerts.notifiers.webhook.requests.post") as post:
        engine.evaluate(
            event_id=0,
            event={"source_ip": "1.2.3.4", "action_type": "connection"},
            severity="INFO",
        )

    with get_db() as db:
        alerts = db.execute(select(Alert)).scalars().all()
    assert alerts == []
    assert not post.called


# ─── Notifier sanity ──────────────────────────────────────────────────────

def test_webhook_notifier_skips_when_no_url():
    from meli.alerts.notifiers import webhook
    from meli.config import get_config

    cfg = get_config()
    cfg.set("alerts", "webhook_url", None)
    with patch("meli.alerts.notifiers.webhook.requests.post") as post:
        webhook.notify("rule", "summary", "HIGH")
    assert not post.called


def test_context_not_overwritten_when_processor_pre_sets_it():
    """If processor pre-computes attacker_is_new_7d, engine must respect it."""
    from meli.alerts.engine import _inject_alert_context
    from meli.database import get_db
    from meli.database.models import Attacker

    now = datetime.now(timezone.utc)
    # Attacker was seen 1 minute ago — naive lookup would say NOT new.
    with get_db() as db:
        db.add(Attacker(
            ip="10.0.0.7",
            first_seen=now - timedelta(days=1),
            last_seen=now - timedelta(minutes=1),
            total_events=1,
            max_severity="INFO",
        ))

    # Processor's snapshot taken BEFORE the upsert says it WAS new.
    event = {"source_ip": "10.0.0.7", "attacker_is_new_7d": True}
    _inject_alert_context(event)
    assert event["attacker_is_new_7d"] is True


# ─── Full ingest-pipeline integration ─────────────────────────────────────

def test_process_event_fires_new_ip_rule_for_first_seen_ip():
    """A brand-new IP flowing through process_event must trigger the
    seeded "New attacker IP" rule, even though process_event upserts the
    Attacker row before alerts evaluate.
    """
    from meli.ingest.processor import process_event
    from meli.database import get_db
    from meli.database.models import Alert
    from meli.config import get_config
    import time as _time

    cfg = get_config()
    cfg.set("alerts", "webhook_url", "https://example.test/hook")

    raw = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_ip": "203.0.113.77",
        "honeypot_service": "cowrie",
        "action": "login_attempt",
        "username": "root",
        "password": "toor",
    }

    with patch("meli.alerts.notifiers.webhook.requests.post") as post, \
         patch("meli.enrichment.geolocation.geolocate_ip", return_value={}), \
         patch("meli.enrichment.enrich_ip"):
        process_event(raw, source="test")
        # Alerts fire on a background thread inside process_event
        for _ in range(100):
            if post.called:
                break
            _time.sleep(0.02)

    with get_db() as db:
        names = [a.rule_name for a in db.execute(select(Alert)).scalars().all()]
    assert any("New attacker IP" in n for n in names), \
        f"Expected new-IP alert via process_event, got: {names}"


def test_process_event_does_not_fire_new_ip_rule_for_recently_seen_ip():
    """An IP seen 1 minute ago should NOT trigger the new-IP rule even
    though process_event will update its last_seen to now."""
    from meli.ingest.processor import process_event
    from meli.database import get_db
    from meli.database.models import Alert, Attacker, AlertRule

    now = datetime.now(timezone.utc)
    ip = "203.0.113.88"
    with get_db() as db:
        db.add(Attacker(
            ip=ip,
            first_seen=now - timedelta(days=1),
            last_seen=now - timedelta(minutes=1),
            total_events=5,
            max_severity="LOW",
        ))
        # Disable burst rule so it can't accidentally fire either
        burst = db.execute(
            select(AlertRule).where(AlertRule.name.like("%brute-force%"))
        ).scalar_one()
        burst.enabled = False

    raw = {
        "timestamp": now.isoformat(),
        "source_ip": ip,
        "honeypot_service": "cowrie",
        "action": "connection",
    }

    with patch("meli.alerts.notifiers.webhook.requests.post"), \
         patch("meli.enrichment.geolocation.geolocate_ip", return_value={}), \
         patch("meli.enrichment.enrich_ip"):
        process_event(raw, source="test")
        import time as _time
        _time.sleep(0.2)  # let any background thread settle

    with get_db() as db:
        names = [a.rule_name for a in db.execute(select(Alert)).scalars().all()]
    assert not any("New attacker IP" in n for n in names), \
        f"new-IP rule fired for recently seen IP: {names}"


def test_ntfy_notifier_posts_with_priority_and_title():
    from meli.alerts.notifiers import ntfy
    from meli.config import get_config

    cfg = get_config()
    cfg.set("alerts", "ntfy_url", "https://ntfy.sh/meli-test")

    with patch("meli.alerts.notifiers.ntfy.requests.post") as post:
        ntfy.notify("My Rule", "Something happened", "HIGH")

    assert post.called
    args, kwargs = post.call_args.args, post.call_args.kwargs
    assert args[0] == "https://ntfy.sh/meli-test"
    assert kwargs["headers"]["Title"] == "Meli: My Rule"
    assert kwargs["headers"]["Priority"] == "4"
