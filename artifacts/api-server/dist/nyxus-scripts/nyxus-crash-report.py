#!/usr/bin/env python3
# ============================================================================
#  nyxus-crash-report.py · NYXUS · Crash Report client      rev 2026-05-13 r1
#
#  Companion CLI for nyxus_crashd.py. Posts a single crash bundle to the
#  NYXUS crash-reports endpoint (POST /api/crash-reports). Idempotent:
#  the server uses sha256(body) as the report id so re-uploading the same
#  bundle returns the same id.
#
#  Hard rules:
#    · Crash reporting is OPT-IN. We refuse to send unless
#      ~/.config/nyxus/crash-reports.optin exists OR --force is passed.
#    · No telemetry beyond the bundle. The bundle itself is opaque to us
#      (a tar.gz the user can inspect before opt-in).
#    · The bearer token, if present, is sha256-hashed by the server; this
#      client never logs it.
#
#  Usage:
#    nyxus-crash-report submit <bundle.tar.gz> [--token TOK] [--force]
#    nyxus-crash-report status [--token TOK]
#    nyxus-crash-report list   [--token TOK]
#
#  © 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================================
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ENDPOINT = os.environ.get(
    "NYXUS_CRASH_ENDPOINT",
    "https://nyxus.os/api/crash-reports",
)
OPT_IN = Path.home() / ".config" / "nyxus" / "crash-reports.optin"
LOG_DIR = Path.home() / ".cache" / "nyxus"
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    filename=str(LOG_DIR / "crash-report.log"),
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("nyxus-crash-report")

MAX_BODY = 2 * 1024 * 1024  # match server


def _request(
    method: str, path: str, *, token: str | None, body: bytes | None = None,
    content_type: str | None = None,
) -> tuple[int, bytes]:
    url = ENDPOINT if path == "" else f"{ENDPOINT.rstrip('/')}/{path.lstrip('/')}"
    headers: dict[str, str] = {"User-Agent": "nyxus-crash-report/1.0"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, (e.read() or b"")
    except urllib.error.URLError as e:
        log.warning("network error: %s", e)
        return 0, str(e).encode("utf-8", "replace")


def cmd_submit(args: argparse.Namespace) -> int:
    bundle = Path(args.bundle)
    if not bundle.is_file():
        print(f"no such file: {bundle}", file=sys.stderr)
        return 2

    if not OPT_IN.exists() and not args.force:
        print(
            "Crash reporting is OFF.\n"
            f"  Touch {OPT_IN} to opt in,\n"
            "  or pass --force to send this single report.",
            file=sys.stderr,
        )
        return 3

    data = bundle.read_bytes()
    if len(data) > MAX_BODY:
        print(
            f"bundle too large: {len(data)} > {MAX_BODY} bytes",
            file=sys.stderr,
        )
        return 4

    log.info(
        "submit: file=%s size=%d token=%s",
        bundle.name, len(data), "yes" if args.token else "no",
    )
    status, body = _request(
        "POST", "", token=args.token, body=data,
        content_type="application/gzip",
    )
    if status == 200 or status == 201:
        try:
            doc = json.loads(body or b"{}")
        except Exception:
            doc = {}
        rid = doc.get("id") or "?"
        print(f"submitted: id={rid}")
        log.info("submitted ok id=%s", rid)
        return 0
    print(
        f"submit failed: HTTP {status} {body[:400].decode('utf-8','replace')}",
        file=sys.stderr,
    )
    log.warning("submit failed status=%s", status)
    return 1


def cmd_status(args: argparse.Namespace) -> int:
    """Lightweight health check.

    The backend exposes only `GET /api/crash-reports` (list) and
    `GET /api/crash-reports/:id` — there is no dedicated /status route.
    We treat a successful list call as "endpoint reachable" and report
    the count of stored reports the caller can see.
    """
    status, body = _request("GET", "", token=args.token)
    if status == 200:
        try:
            doc = json.loads(body or b"[]")
        except json.JSONDecodeError:
            doc = []
        count = len(doc) if isinstance(doc, list) else len(doc.get("reports", []))
        print(f"endpoint: ok\nreports_visible: {count}")
        return 0
    if status == 401:
        print("endpoint: ok (unauthenticated — pass --token for report counts)")
        return 0
    print(f"status failed: HTTP {status}", file=sys.stderr)
    return 1


def cmd_list(args: argparse.Namespace) -> int:
    status, body = _request("GET", "", token=args.token)
    if status == 200:
        sys.stdout.write(body.decode("utf-8", "replace"))
        if not body.endswith(b"\n"):
            sys.stdout.write("\n")
        return 0
    print(f"list failed: HTTP {status}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="nyxus-crash-report",
        description="NYXUS crash-report uploader (opt-in).",
    )
    p.add_argument("--token", default=os.environ.get("NYXUS_CRASH_TOKEN"))
    sp = p.add_subparsers(dest="cmd", required=True)
    s_sub = sp.add_parser("submit", help="upload a crash bundle (.tar.gz)")
    s_sub.add_argument("bundle")
    s_sub.add_argument("--force", action="store_true",
                       help="bypass the opt-in check (single report).")
    s_sub.set_defaults(func=cmd_submit)
    s_status = sp.add_parser("status", help="server health (rate-limit, queue).")
    s_status.set_defaults(func=cmd_status)
    s_list = sp.add_parser("list", help="list previously submitted reports.")
    s_list.set_defaults(func=cmd_list)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
