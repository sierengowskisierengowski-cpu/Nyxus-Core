#!/usr/bin/env python3
"""
Jett verdict ingestion — surface the REAL EDR verdicts in the guardian.

Jett (the Rust AI-EDR daemon) is the authoritative process-verdict engine on
this host: it emits ALLOW / WOULD-QUARANTINE / QUARANTINE decisions with MITRE
technique chains and calibrated confidence. Historically the guardian ran its
own noisy ProcessWatcher heuristics and (when its LLM analyst was down) flooded
the feed with `parser_error`. The honest reconciliation is to represent Jett's
process-verdict data with correct semantics (process / pid / path / technique /
verdict / confidence) instead of shoehorning processes into an "IP attacker".

This collector tails Jett's durable verdict store (written by
`jeTT::verdict_store`, default ``/var/lib/jett/verdicts.jsonl``) and enqueues
each verdict as a pre-decided event. The router recognises the attached Jett
verdict and uses it directly — it does NOT re-run the LLM analyst on an
already-decided verdict.

Verdict store record shape (one JSON object per line, produced by Jett):
    {"ts":1784194393,"pid":2710018,"process":"bash","path":"/usr/bin/bash",
     "uid":1000,"verdict":"🟡 WOULD-QUARANTINE","kind":"would_quarantine",
     "confidence":0.90,"technique":["T1059.004"],"reason":"...","evidence":[...],
     "mode":"learn","enforce_mode":false,"elapsed_ms":86,"source":"proc"}
"""

from __future__ import annotations

import json
import os
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from bifrost.event_queue import safe_enqueue
from bifrost.mitre import enrich_decision

DEFAULT_VERDICT_STORE = "/var/lib/jett/verdicts.jsonl"

# MITRE tactic hints for the techniques Jett commonly emits (best-effort; the
# technique_id is always authoritative and passed through regardless).
_TACTIC_BY_TECHNIQUE = {
    "T1059": ("TA0002", "Execution"),
    "T1059.004": ("TA0002", "Execution"),
    "T1071": ("TA0011", "Command and Control"),
    "T1071.004": ("TA0011", "Command and Control"),
    "T1003": ("TA0006", "Credential Access"),
    "T1548.001": ("TA0004", "Privilege Escalation"),
    "T1611": ("TA0004", "Privilege Escalation"),
    "T1105": ("TA0011", "Command and Control"),
}


def resolve_verdict_store(config: Mapping[str, Any] | None = None) -> Path:
    env = os.getenv("BIFROST_JETT_VERDICTS", "").strip()
    if env:
        return Path(env).expanduser()
    if config:
        cfg = str(config.get("jett_verdict_store") or "").strip()
        if cfg:
            return Path(cfg).expanduser()
    return Path(DEFAULT_VERDICT_STORE)


def _severity_from_confidence(confidence: float) -> str:
    if confidence >= 0.90:
        return "CRITICAL"
    if confidence >= 0.75:
        return "HIGH"
    if confidence >= 0.50:
        return "MEDIUM"
    if confidence >= 0.25:
        return "LOW"
    return "INFO"


def _mitre_from_techniques(techniques: Any) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    if not isinstance(techniques, (list, tuple)):
        return out
    for tech in techniques:
        tid = str(tech or "").strip()
        if not tid:
            continue
        tactic_id, tactic = _TACTIC_BY_TECHNIQUE.get(tid, ("", ""))
        out.append(
            {
                "tactic_id": tactic_id,
                "tactic": tactic,
                "technique_id": tid,
                "technique": tid,
            }
        )
    return out


def verdict_to_decision(
    record: Mapping[str, Any], config: Mapping[str, Any] | None = None
) -> dict:
    """Translate a Jett verdict record into a guardian decision dict.

    Jett owns enforcement; the guardian is a read/display plane, so the mapped
    action is non-destructive (ALERT/LOG) — the guardian NEVER re-enforces or
    controls Jett's process lifecycle.
    """
    config = config or {}
    kind = str(record.get("kind") or "").lower()
    try:
        confidence = float(record.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    techniques = record.get("technique") or []
    mitre = _mitre_from_techniques(techniques)
    primary_technique = mitre[0]["technique_id"] if mitre else None

    process = str(record.get("process") or "process")
    path = str(record.get("path") or "")
    pid = record.get("pid")
    evidence = record.get("evidence") or []
    reason = str(record.get("reason") or "").strip()

    if kind == "allow":
        incident = False
        severity = "INFO"
        threat_class = "benign_process"
        action = "LOG"
    elif kind in {"quarantine", "would_quarantine"}:
        incident = True
        severity = _severity_from_confidence(confidence)
        threat_class = (
            f"malicious_process:{primary_technique}"
            if primary_technique
            else "malicious_process"
        )
        action = "ALERT"  # display-only; Jett performs any real enforcement
    elif kind == "review":
        incident = True
        severity = "MEDIUM"
        threat_class = "needs_review"
        action = "ALERT"
    elif kind == "contain":
        incident = True
        severity = _severity_from_confidence(max(confidence, 0.75))
        threat_class = "contained_process"
        action = "ALERT"
    else:
        incident = False
        severity = "LOW"
        threat_class = f"jett_{kind or 'unknown'}"
        action = "LOG"

    summary = reason or f"Jett verdict {record.get('verdict') or kind} for {process}."
    if evidence:
        summary = f"{summary} evidence={','.join(str(e) for e in evidence[:4])}"

    decision = enrich_decision(
        {
            "schema_version": "0.1.0",
            "incident_detected": incident,
            "severity": severity,
            "boundary": "HOST",
            "threat_class": threat_class,
            "confidence": round(confidence, 2),
            "action_required": action,
            "target": f"pid:{pid}" if pid not in (None, "") else (path or None),
            "gjallarhorn_tier": 2 if severity in {"CRITICAL", "HIGH"} else 1,
            "reasoning": summary[:200],
            "extractor_model": "jett",
            "reasoner_model": "jett-edr",
            "hardware_tier": str(config.get("hardware_tier", "TIER_3")),
            "mitre_attack": mitre,
            # Provenance: this verdict came from Jett, not the guardian analyst.
            "analyst_status": "jett_edr",
            "jett_mode": record.get("mode"),
        }
    )
    return decision


def verdict_to_event(record: Mapping[str, Any]) -> dict:
    """Wrap a Jett verdict record into a guardian event envelope."""
    ts = record.get("ts")
    try:
        iso = datetime.fromtimestamp(float(ts), tz=timezone.utc).isoformat().replace(
            "+00:00", "Z"
        )
    except (TypeError, ValueError, OSError):
        iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    path = str(record.get("path") or "")
    return {
        "source": "jett",
        "timestamp": iso,
        "boundary": "HOST",
        "event_id": f"jett-{record.get('pid')}-{ts}",
        "raw": {
            "pid": record.get("pid"),
            "process_name": path or record.get("process"),
            "exe": path,
            "cmdline": str(record.get("process") or ""),
            "uid": record.get("uid"),
            "host": "jett",
            # The router uses this to skip the LLM and use Jett's verdict.
            "_jett_verdict": dict(record),
        },
    }


class JettVerdictCollector(threading.Thread):
    """Tail Jett's durable verdict store and feed verdicts into the pipeline."""

    RETRY_INTERVAL = 1.0

    def __init__(self, queue, log, stop_event, *, config=None, store_path=None):
        super().__init__(daemon=True, name="collector.jett")
        self.queue = queue
        self.log = log
        self.stop_event = stop_event
        self.config = config or {}
        self.store_path = Path(store_path) if store_path else resolve_verdict_store(config)

    def run(self) -> None:
        self.log.info("JettVerdictCollector started. store=%s", self.store_path)
        warned_missing = False
        while not self.stop_event.is_set():
            if not self.store_path.exists():
                if not warned_missing:
                    self.log.info(
                        "Jett verdict store not found at %s yet (Jett may need a "
                        "rebuild/restart). Retrying.",
                        self.store_path,
                    )
                    warned_missing = True
                if self.stop_event.wait(self.RETRY_INTERVAL):
                    break
                continue
            warned_missing = False
            try:
                self._follow()
            except OSError as exc:
                self.log.warning("JettVerdictCollector read error: %s", exc)
                if self.stop_event.wait(self.RETRY_INTERVAL):
                    break

    def _follow(self) -> None:
        with open(self.store_path, "r", encoding="utf-8") as fh:
            # Start at end so we only ingest new verdicts, not historical bulk.
            fh.seek(0, 2)
            inode = os.fstat(fh.fileno()).st_ino
            while not self.stop_event.is_set():
                try:
                    if os.stat(self.store_path).st_ino != inode:
                        self.log.info("Jett verdict store rotated. Reopening.")
                        return
                except OSError:
                    return
                line = fh.readline()
                if not line:
                    if self.stop_event.wait(0.2):
                        return
                    continue
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    self.log.debug("Jett verdict parse error: %s", exc)
                    continue
                if not isinstance(record, dict):
                    continue
                event = verdict_to_event(record)
                safe_enqueue(self.queue, event, "jett", self.log)
