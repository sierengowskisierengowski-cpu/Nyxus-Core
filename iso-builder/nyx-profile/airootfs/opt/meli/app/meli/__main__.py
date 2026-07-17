"""
Meli entry point — handles both GUI launch and daemon modes.
Run as: python -m meli [--daemon ingest]
"""
import sys
import click
from meli import __version__


@click.command()
@click.version_option(__version__, prog_name="meli")
@click.option("--daemon", type=click.Choice(["ingest"]), default=None,
              help="Run a background daemon instead of the GUI")
@click.option("--debug", is_flag=True, default=False,
              help="Enable debug logging")
@click.option("--reset-auth", is_flag=True, default=False,
              help="Reset authentication (emergency recovery)")
@click.option("--kiosk", is_flag=True, default=False,
              help="Launch directly into the fullscreen Labyrinth Atrium "
                   "display (wall-mounted monitor mode)")
@click.option("--status", "status_json", is_flag=True, default=False,
              help="Print machine-readable status JSON (alerts, enrichment "
                   "providers, report history, DB counts) and exit. "
                   "Headless — intended for the Bifrost UI to shell out to.")
@click.option("--report", "report_type",
              type=click.Choice(["daily", "weekly", "monthly", "all", "custom"]),
              default=None,
              help="Generate a threat-intel report and print its path, then exit.")
@click.option("--report-format", "report_format",
              type=click.Choice(["markdown", "json", "pdf", "csv"]),
              default="markdown", help="Format for --report (default markdown).")
@click.option("--report-from", "report_from", default=None,
              help="ISO start datetime for --report custom (e.g. 2026-05-01).")
@click.option("--report-to", "report_to", default=None,
              help="ISO end datetime for --report custom.")
def main(daemon: str | None, debug: bool, reset_auth: bool,
         kiosk: bool, status_json: bool, report_type: str | None,
         report_format: str, report_from: str | None,
         report_to: str | None) -> None:
    """Meli — Honeypot Command Center"""
    import structlog
    from meli.utils.logger import setup_logging
    setup_logging(debug=debug)
    log = structlog.get_logger()

    if reset_auth:
        from meli.auth import reset_auth as do_reset
        do_reset()
        click.echo("Authentication reset. Launch Meli normally to set a new master password.")
        sys.exit(0)

    # ── Headless read-only surfaces for external callers (Bifrost) ─────────
    if status_json:
        from meli.status import status_json as _sj
        click.echo(_sj())
        sys.exit(0)

    if report_type:
        from datetime import datetime, timezone
        from meli.reports.generator import generate_report

        def _parse_iso(s: str) -> datetime:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

        gen_type = report_type
        from_dt = to_dt = None
        if report_type == "all":
            # Whole-history report — spans everything currently in the DB.
            gen_type = "custom"
            from_dt = datetime(2000, 1, 1, tzinfo=timezone.utc)
            to_dt = datetime.now(timezone.utc)
        elif report_type == "custom":
            if not report_from:
                click.echo("--report custom requires --report-from (and optionally --report-to)", err=True)
                sys.exit(2)
            from_dt = _parse_iso(report_from)
            to_dt = _parse_iso(report_to) if report_to else datetime.now(timezone.utc)

        path = generate_report(gen_type, fmt=report_format,
                               from_dt=from_dt, to_dt=to_dt)
        # Emit JSON so callers can parse path + type reliably.
        import json as _json
        click.echo(_json.dumps({"status": "ok", "report_type": report_type,
                                "format": report_format, "path": str(path)}))
        sys.exit(0)

    if daemon == "ingest":
        log.info("Starting Meli ingest daemon", version=__version__)
        from meli.ingest.daemon import IngestDaemon
        d = IngestDaemon()
        d.run()
        return

    # GUI launch
    log.info("Starting Meli GUI", version=__version__, kiosk=kiosk)
    from meli.app import MeliApplication
    app = MeliApplication(kiosk=kiosk)
    sys.exit(app.run(sys.argv[:1]))


if __name__ == "__main__":
    main()
