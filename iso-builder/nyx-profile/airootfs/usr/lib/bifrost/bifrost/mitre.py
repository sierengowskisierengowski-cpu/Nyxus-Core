#!/usr/bin/env python3
"""MITRE ATT&CK mappings for common Bifrost threat classes."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AttackMapping:
    tactic_id: str
    tactic: str
    technique_id: str
    technique: str


_MAPPINGS: dict[str, tuple[AttackMapping, ...]] = {
    "brute_force_ssh": (
        AttackMapping("TA0006", "Credential Access", "T1110", "Brute Force"),
    ),
    "credential_access_chain": (
        AttackMapping("TA0006", "Credential Access", "T1003", "OS Credential Dumping"),
    ),
    "credential_theft": (
        AttackMapping("TA0006", "Credential Access", "T1003", "OS Credential Dumping"),
    ),
    "cowrie_dns_pivot": (
        AttackMapping("TA0011", "Command and Control", "T1071.004", "Application Layer Protocol: DNS"),
    ),
    "execution_tmp_exec": (
        AttackMapping("TA0002", "Execution", "T1059", "Command and Scripting Interpreter"),
    ),
    "initial_access": (
        AttackMapping("TA0001", "Initial Access", "T1190", "Exploit Public-Facing Application"),
    ),
    "lateral_movement": (
        AttackMapping("TA0008", "Lateral Movement", "T1021", "Remote Services"),
    ),
    "mdrfckr_botnet": (
        AttackMapping("TA0011", "Command and Control", "T1071", "Application Layer Protocol"),
    ),
    "persistence_systemd": (
        AttackMapping("TA0003", "Persistence", "T1543.002", "Create or Modify System Process: Systemd Service"),
    ),
    "port_scan": (
        AttackMapping("TA0043", "Reconnaissance", "T1046", "Network Service Scanning"),
    ),
    "suid_binary": (
        AttackMapping("TA0004", "Privilege Escalation", "T1548.001", "Abuse Elevation Control Mechanism: Setuid and Setgid"),
    ),
    "suspicious_process_spawn": (
        AttackMapping("TA0002", "Execution", "T1059", "Command and Scripting Interpreter"),
    ),
    "container_escape_detected": (
        AttackMapping("TA0004", "Privilege Escalation", "T1611", "Escape to Host"),
    ),
    "honeypot_to_host_connection": (
        AttackMapping("TA0008", "Lateral Movement", "T1021", "Remote Services"),
    ),
}

_ALIASES = {
    "bruteforce_ssh": "brute_force_ssh",
    "cowrie_dns_pivot_2026_05_29": "cowrie_dns_pivot",
    "execution": "execution_tmp_exec",
    "portscan": "port_scan",
}


def _normalize_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    for old, new in (("-", "_"), (" ", "_"), ("/", "_"), (".jsonl", "")):
        text = text.replace(old, new)
    while "__" in text:
        text = text.replace("__", "_")
    return _ALIASES.get(text, text)


def lookup_attack(threat_class: Any) -> list[dict[str, str]]:
    key = _normalize_key(threat_class)
    mappings = _MAPPINGS.get(key, ())
    if mappings:
        return [asdict(mapping) for mapping in mappings]

    for known_key, known_mappings in _MAPPINGS.items():
        if key and key in known_key:
            return [asdict(mapping) for mapping in known_mappings]
    return []


def enrich_decision(decision: dict[str, Any] | None) -> dict[str, Any]:
    enriched = dict(decision or {})
    existing = enriched.get("mitre_attack")
    if isinstance(existing, list) and existing:
        return enriched
    enriched["mitre_attack"] = lookup_attack(enriched.get("threat_class"))
    return enriched
