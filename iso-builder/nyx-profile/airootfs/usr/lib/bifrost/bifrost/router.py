#!/usr/bin/env python3
"""
Bifrost Router v0.1.0

Fallback chain logic and decision execution routing.
Reads Heimdall decisions and dispatches to the Go executor.
Manages the full fallback chain:
  Local Ollama -> Groq -> Claude -> Deterministic rules
"""

import json
import logging
import os
import sqlite3
import hashlib
import urllib.request
import urllib.error
from typing import Optional

log = logging.getLogger("heimdall.router")

EXECUTOR_URL = "http://127.0.0.1:8766/execute"
EXECUTOR_HEALTH = "http://127.0.0.1:8766/health"


def _safe_json_load(payload):
    if payload is None:
        return None
    if isinstance(payload, dict):
        return payload
    try:
        return json.loads(payload)
    except Exception:
        return None


def _calculate_command_sequence_hash(commands_list: list[str]) -> str:
    normalized = [
        str(cmd).strip().lower()
        for cmd in commands_list
        if cmd is not None and str(cmd).strip()
    ]
    if not normalized:
        return ""
    return hashlib.sha256("|".join(normalized).encode("utf-8")).hexdigest()


def _load_action_context(db_path: str, event_id: int) -> dict:
    if not db_path or not event_id or event_id < 1:
        return {}
    conn = None
    try:
        conn = sqlite3.connect(str(db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT raw_event, compressed_event FROM events WHERE id = ?",
            (event_id,),
        )
        row = cursor.fetchone()
        if not row:
            return {}
        raw_event, compressed_event = row
        raw_data = _safe_json_load(raw_event) or {}
        compressed_data = _safe_json_load(compressed_event) or {}
        session_id = (
            compressed_data.get("session_id")
            or compressed_data.get("session")
            or raw_data.get("session_id")
            or raw_data.get("session")
        )
        ssh_fingerprint = (
            compressed_data.get("ssh_fingerprint")
            or raw_data.get("ssh_fingerprint")
            or raw_data.get("fingerprint")
        )
        command = (
            compressed_data.get("command")
            or raw_data.get("command")
            or raw_data.get("input")
            or raw_data.get("message")
        )
        command_hash = _calculate_command_sequence_hash([command]) if command else ""
        return {
            "session_id": session_id,
            "ssh_fingerprint": ssh_fingerprint,
            "command_hash": command_hash,
        }
    except Exception as e:
        log.warning("Router: failed to load action context: %s", e)
        return {}
    finally:
        if conn:
            conn.close()


def executor_available() -> bool:
    """Check if the Go executor is running and reachable."""
    try:
        with urllib.request.urlopen(EXECUTOR_HEALTH, timeout=2) as resp:
            return resp.status == 200
    except Exception:
        return False


def execute_decision(
    decision: dict,
    event_id: int,
    db_path: str,
    log_ref
) -> bool:
    """
    Sends a Heimdall decision to the Go executor.
    The executor handles the actual system action —
    UFW block, process kill, or file quarantine.
    Returns True if executor accepted the decision.
    """
    action = decision.get("action_required", "NONE")

    if action in ["LOG", "NONE", "ALERT"]:
        log_ref.info(f"Router: non-disruptive action {action} — no executor call.")
        return True

    if not executor_available():
        log_ref.warning(
            f"Router: Go executor not available. "
            f"Action {action} could not be executed. "
            f"Start bifrost-agent service."
        )
        return False

    payload = {
        "action_required": action,
        "target": str(decision.get("target", "")),
        "threat_class": decision.get("threat_class", "unknown"),
        "reasoning": decision.get("reasoning", "")[:200],
        "event_id": event_id,
        "schema_version": decision.get("schema_version", "1.0.0")
    }
    payload.update(_load_action_context(db_path, event_id))

    headers = {"Content-Type": "application/json"}
    token = os.getenv("BIFROST_EXECUTOR_TOKEN", "").strip()
    if not token:
        from bifrost.security import is_production_mode
        if is_production_mode():
            log_ref.error(
                "Router: BIFROST_EXECUTOR_TOKEN unset — refusing dispatch."
            )
            return False
        log_ref.warning(
            "Router: BIFROST_EXECUTOR_TOKEN unset — executor will reject."
        )
    else:
        headers["X-Bifrost-Token"] = token

    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            EXECUTOR_URL,
            data=data,
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            log_ref.info(
                f"Router: executor accepted action={action} "
                f"target={payload['target']} result={result}"
            )
            return True

    except urllib.error.URLError as e:
        log_ref.error(f"Router: executor unreachable: {e}")
        return False
    except Exception as e:
        log_ref.error(f"Router: dispatch error: {e}")
        return False


def rollback_last_action(action_id: int, log_ref) -> bool:
    """
    Rolls back an action by ID via the Go executor rollback endpoint.
    Called from the feedback loop when a false positive is marked.
    """
    rollback_url = "http://127.0.0.1:8766/rollback"

    if not executor_available():
        log_ref.warning("Router: executor not available for rollback.")
        return False

    headers = {"Content-Type": "application/json"}
    token = os.getenv("BIFROST_EXECUTOR_TOKEN", "").strip()
    if not token:
        from bifrost.security import is_production_mode
        if is_production_mode():
            log_ref.error(
                "Router: BIFROST_EXECUTOR_TOKEN unset — refusing rollback."
            )
            return False
    else:
        headers["X-Bifrost-Token"] = token

    try:
        payload = json.dumps({"action_id": action_id}).encode()
        req = urllib.request.Request(
            rollback_url,
            data=payload,
            headers=headers,
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            result = json.loads(resp.read())
            log_ref.info(f"Router: rollback executed action_id={action_id} result={result}")
            return True

    except Exception as e:
        log_ref.error(f"Router: rollback failed: {e}")
        return False


def select_model_route(config: dict) -> str:
    """
    Determines which AI backend to use based on
    hardware tier and availability.
    Returns a string identifying the route selected.
    """
    tier = config.get("hardware_tier", "TIER_4")
    use_local = config.get("use_local_llm", False)

    if use_local and tier in ["TIER_1", "TIER_2"]:
        return "ollama"

    import os
    if os.getenv("HEIMDALL_API_KEY"):
        return "groq"

    if os.getenv("HEIMDALL_CLAUDE_KEY"):
        return "claude"

    return "rules"


def get_fallback_chain(config: dict) -> list:
    """
    Returns the ordered fallback chain for this deployment.
    Heimdall tries each in order until one succeeds.
    """
    tier = config.get("hardware_tier", "TIER_4")
    use_local = config.get("use_local_llm", False)
    chain = []

    if use_local and tier in ["TIER_1", "TIER_2"]:
        chain.append("ollama")

    chain.append("groq")
    chain.append("claude")
    chain.append("rules")

    return chain
