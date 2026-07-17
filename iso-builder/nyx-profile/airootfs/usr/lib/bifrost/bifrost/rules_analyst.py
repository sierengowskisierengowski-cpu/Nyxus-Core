#!/usr/bin/env python3
"""
Deterministic rules analyst — the honest floor for Heimdall.

When the LLM analyst is unavailable (local Ollama not running, circuit breaker
open, request timeouts, etc.) the guardian must NOT flood the incident feed with
blanket ``parser_error`` / LOW verdicts. That makes real data indistinguishable
from "the analyst is offline".

Instead we classify events deterministically from the indicators the collectors
already extracted (execution path, kernel masquerade, honeypot breakout, shell
pipelines, credential-file access, honeypot boundary, …). This produces a real
severity distribution and honest, specific ``threat_class`` values with a
``reasoner_model`` of ``deterministic_rules`` so it is obvious the verdict came
from the rules floor, not the neural analyst.

Anything that matches no rule is reported honestly as benign observation
(``threat_class="benign_activity"``, ``severity="INFO"``, ``incident_detected``
False) rather than a fake threat.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from bifrost.mitre import enrich_decision

# threat_class emitted when even the rules floor cannot run (should be rare).
ANALYST_UNAVAILABLE_CLASS = "analyst_unavailable"

# Reasons from the LLM path that mean "analyst is offline / infrastructure
# failure" as opposed to a genuine parse/schema problem. Callers use this to
# decide whether to fall through to the rules floor and to mark analyst_status.
ANALYST_OFFLINE_REASONS = frozenset(
    {
        "analyst_circuit_open",
        "extractor_circuit_open",
        "llm_error",
        "no_analyst_model",
        "no_analyst_client",
        "circuit_open",
        # Fixed sentinel used when the rules floor itself also throws inside
        # guardian._reason_event's outer exception handler (double failure).
        "reasoner_error",
    }
)

_SCRATCH_PREFIXES = ("/tmp/", "/var/tmp/", "/dev/shm/")
_CRED_FILES = ("/etc/shadow", "/etc/passwd", "/etc/sudoers", "/etc/gshadow")
_DOWNLOADERS = ("curl", "wget")
_PIPE_TO_SHELL = ("| sh", "|sh", "| bash", "|bash", "| /bin/sh", "| /bin/bash")


def _as_dict(value: Any) -> dict:
    return dict(value) if isinstance(value, Mapping) else {}


def _decision(
    *,
    severity: str,
    threat_class: str,
    confidence: float,
    action: str,
    reasoning: str,
    boundary: str,
    incident: bool,
    target: Any = None,
    config: Mapping[str, Any] | None = None,
    extractor_model: str = "degraded",
) -> dict:
    tier = str((config or {}).get("hardware_tier", "TIER_4"))
    gjallarhorn_tier = 2 if severity in {"CRITICAL", "HIGH"} else 1
    return enrich_decision(
        {
            "schema_version": "0.1.0",
            "incident_detected": incident,
            "severity": severity,
            "boundary": boundary,
            "threat_class": threat_class,
            "confidence": round(float(confidence), 2),
            "action_required": action,
            "target": str(target) if target not in (None, "") else None,
            "gjallarhorn_tier": gjallarhorn_tier,
            "reasoning": reasoning[:200],
            "extractor_model": extractor_model,
            "reasoner_model": "deterministic_rules",
            "hardware_tier": tier,
            # Honest provenance markers so the UI can show "analyst offline".
            "analyst_status": "degraded_rules",
        }
    )


def classify(event: Mapping[str, Any], config: Mapping[str, Any] | None = None) -> dict:
    """Classify an event deterministically from its collected indicators."""
    config = config or {}
    raw = _as_dict(event.get("raw"))
    boundary = str(event.get("boundary") or "UNKNOWN").upper()
    indicators = _as_dict(raw.get("indicators"))

    exe = str(raw.get("exe") or raw.get("process_name") or raw.get("path") or "")
    cmdline = str(raw.get("cmdline") or raw.get("command") or "")
    pid = raw.get("pid")
    combined = f"{exe} {cmdline}".lower()
    alert = str(raw.get("alert") or "")

    proc_name = Path(exe).name if exe else str(raw.get("process_name") or "process")
    target = f"pid:{pid}" if pid not in (None, "") else (exe or None)

    # 1. Honeypot → host breakout / container escape (highest confidence signal).
    if alert in {"honeypot_to_host_connection", "container_escape_detected"}:
        return _decision(
            severity="CRITICAL",
            threat_class="container_escape"
            if alert == "container_escape_detected"
            else "honeypot_to_host_connection",
            confidence=0.95,
            action="BLOCK",
            reasoning=f"Honeypot boundary breakout detected: {alert}.",
            boundary=boundary if boundary != "UNKNOWN" else "NETWORK",
            incident=True,
            target=raw.get("remote_ip") or target,
            config=config,
        )

    # 2. Kernel-thread masquerade.
    if indicators.get("kernel_masquerade"):
        return _decision(
            severity="HIGH",
            threat_class="process_masquerade",
            confidence=0.8,
            action="ALERT",
            reasoning=f"{proc_name} masquerades as a kernel thread (exe={exe}).",
            boundary=boundary if boundary != "UNKNOWN" else "HOST",
            incident=True,
            target=target,
            config=config,
        )

    # 3. Credential-file access.
    if any(cf in cmdline for cf in _CRED_FILES):
        return _decision(
            severity="CRITICAL",
            threat_class="credential_tampering",
            confidence=0.9,
            action="ALERT",
            reasoning=f"{proc_name} references credential file(s) in its command line.",
            boundary=boundary if boundary != "UNKNOWN" else "HOST",
            incident=True,
            target=target,
            config=config,
        )

    # 4. Download-piped-to-shell (curl|sh, wget|bash).
    if any(d in combined for d in _DOWNLOADERS) and any(p in combined for p in _PIPE_TO_SHELL):
        return _decision(
            severity="HIGH",
            threat_class="suspicious_download",
            confidence=0.75,
            action="ALERT",
            reasoning=f"{proc_name} pipes a download directly into a shell.",
            boundary=boundary if boundary != "UNKNOWN" else "HOST",
            incident=True,
            target=target,
            config=config,
        )

    # 5. Fileless / scratch-space execution.
    if indicators.get("scratch_space_exec") or exe.startswith("/dev/shm/"):
        if exe.startswith("/dev/shm/"):
            return _decision(
                severity="CRITICAL",
                threat_class="fileless_execution",
                confidence=0.9,
                action="ALERT",
                reasoning=f"{proc_name} executes from tmpfs {exe}.",
                boundary=boundary if boundary != "UNKNOWN" else "HOST",
                incident=True,
                target=target,
                config=config,
            )
        return _decision(
            severity="MEDIUM",
            threat_class="scratch_space_execution",
            confidence=0.55,
            action="ALERT",
            reasoning=f"{proc_name} executes from scratch space {exe}.",
            boundary=boundary if boundary != "UNKNOWN" else "HOST",
            incident=True,
            target=target,
            config=config,
        )

    if exe.startswith(_SCRATCH_PREFIXES):
        return _decision(
            severity="MEDIUM",
            threat_class="scratch_space_execution",
            confidence=0.5,
            action="ALERT",
            reasoning=f"{proc_name} executes from scratch path {exe}.",
            boundary=boundary if boundary != "UNKNOWN" else "HOST",
            incident=True,
            target=target,
            config=config,
        )

    # 6. Honeypot boundary activity that reached the reasoner — expected noise.
    if boundary == "HONEYPOT":
        return _decision(
            severity="LOW",
            threat_class="honeypot_activity",
            confidence=0.2,
            action="LOG",
            reasoning="Honeypot-zone activity observed (expected noise).",
            boundary="HONEYPOT",
            incident=False,
            target=target,
            config=config,
        )

    # 7. No rule matched — honest benign observation, NOT a fake threat.
    return _decision(
        severity="INFO",
        threat_class="benign_activity",
        confidence=0.1,
        action="LOG",
        reasoning=(
            f"No suspicious indicators for {proc_name}; analyst offline, "
            "classified by rules floor."
        ),
        boundary=boundary,
        incident=False,
        target=target,
        config=config,
    )
