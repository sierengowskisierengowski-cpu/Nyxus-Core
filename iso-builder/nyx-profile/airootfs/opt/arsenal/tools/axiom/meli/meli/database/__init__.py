"""Database package — SQLAlchemy + SQLite."""
from meli.database.models import Base, get_engine, get_session


def init_db() -> None:
    """Create all tables if they don't exist, and apply lightweight schema bumps."""
    engine = get_engine()
    Base.metadata.create_all(engine)
    _apply_schema_bumps(engine)
    _seed_builtin_rules()


def _seed_builtin_rules() -> None:
    """Seed built-in alert rules. Safe to call on every startup."""
    try:
        from meli.alerts.engine import seed_builtin_alert_rules
        seed_builtin_alert_rules()
    except Exception:
        # Don't block startup if seeding fails — the engine still works
        # against any user-defined rules.
        pass


def _apply_schema_bumps(engine) -> None:
    """Add columns that were introduced after the initial schema was created.

    SQLite tolerates ALTER TABLE ADD COLUMN cheaply, so we use it as a poor
    man's migration: inspect existing columns and add any that the ORM model
    declares but the DB doesn't have yet. Safe to run on every startup.
    """
    from sqlalchemy import inspect, text

    bumps = {
        "events": [
            ("latitude", "FLOAT"),
            ("longitude", "FLOAT"),
            ("action_type", "VARCHAR(50)"),
        ],
        "attackers": [
            ("latitude", "FLOAT"),
            ("longitude", "FLOAT"),
            ("city", "VARCHAR(255)"),
        ],
    }

    insp = inspect(engine)
    with engine.begin() as conn:
        for table, cols in bumps.items():
            if not insp.has_table(table):
                continue
            existing = {c["name"] for c in insp.get_columns(table)}
            for name, sql_type in cols:
                if name not in existing:
                    conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {name} {sql_type}'))


def get_db():
    """Context manager for database sessions."""
    return get_session()
