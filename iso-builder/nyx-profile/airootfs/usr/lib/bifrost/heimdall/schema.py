#!/usr/bin/env python3
"""
Bifrost Schema v0.1.0

Strict data contracts for pipeline internals.
- RawEvent: event envelope entering pipeline
- Decision: reasoner output entering policy gate

Rule: Convert dict <-> model only at IO boundaries.
"""

from __future__ import annotations
import logging
from enum import Enum
from typing import Optional, Any
from datetime import datetime, timezone

_logger = logging.getLogger("heimdall.schema")

SCHEMA_VERSION = "0.1.0"

try:
    from pydantic import BaseModel, ConfigDict, Field, field_validator
    PYDANTIC_AVAILABLE = True
except ImportError:
    PYDANTIC_AVAILABLE = False


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH     = "HIGH"
    MEDIUM   = "MEDIUM"
    LOW      = "LOW"
    INFO     = "INFO"


class Boundary(str, Enum):
    HOST      = "HOST"
    HONEYPOT  = "HONEYPOT"
    NETWORK   = "NETWORK"
    UNKNOWN   = "UNKNOWN"


class ActionType(str, Enum):
    KILL       = "KILL"
    BLOCK      = "BLOCK"
    QUARANTINE = "QUARANTINE"
    ALERT      = "ALERT"
    LOG        = "LOG"
    NONE       = "NONE"


DESTRUCTIVE_ACTIONS = {ActionType.KILL, ActionType.BLOCK, ActionType.QUARANTINE}
SAFE_ACTIONS        = {ActionType.ALERT, ActionType.LOG, ActionType.NONE}


def _normalize_iso8601(ts: str) -> str:
    if not ts:
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    t = ts.strip()
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    parsed = datetime.fromisoformat(t)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


if PYDANTIC_AVAILABLE:

    class RawEvent(BaseModel):
        model_config = ConfigDict(extra="forbid", validate_assignment=True)

        source:    str
        timestamp: str
        boundary:  Boundary
        raw:       Any

        @field_validator("timestamp", mode="before")
        @classmethod
        def validate_timestamp(cls, v):
            return _normalize_iso8601("" if v is None else str(v))

        @field_validator("source")
        @classmethod
        def validate_source(cls, v: str):
            if not v or not v.strip():
                raise ValueError("source cannot be empty")
            return v.strip()

        def to_dict(self) -> dict:
            return {
                "source":    self.source,
                "timestamp": self.timestamp,
                "boundary":  self.boundary.value,
                "raw":       self.raw,
            }

        @classmethod
        def from_dict(cls, d: dict) -> "RawEvent":
            return cls.model_validate(d)


    class Decision(BaseModel):
        model_config = ConfigDict(extra="forbid", validate_assignment=True)

        schema_version:    str            = SCHEMA_VERSION
        incident_detected: bool           = False
        severity:          Severity       = Severity.INFO
        boundary:          Boundary       = Boundary.UNKNOWN
        threat_class:      str            = "unknown"
        confidence:        float          = 0.0
        action_required:   ActionType     = ActionType.NONE
        target:            Optional[str]  = None
        gjallarhorn_tier:  int            = 1
        reasoning:         str            = ""
        extractor_model:   str            = "unknown"
        reasoner_model:    str            = "unknown"
        hardware_tier:     str            = "TIER_4"
        mitre_attack:      list[dict[str, str]] = Field(default_factory=list)
        action_effective:  Optional[ActionType] = None
        policy_rationale:  Optional[str]  = None
        rollback_id:       Optional[str]  = None
        event_id:          Optional[str]  = None

        @field_validator("schema_version", mode="before")
        @classmethod
        def normalize_schema_version(cls, v):
            if v and str(v) != SCHEMA_VERSION:
                import logging
                logging.getLogger("heimdall.schema").warning(
                    f"schema_version mismatch: got {v}, locking to {SCHEMA_VERSION}"
                )
            return SCHEMA_VERSION

        @field_validator("confidence", mode="before")
        @classmethod
        def clamp_confidence(cls, v):
            try:
                f = float(v)
            except Exception:
                f = 0.0
            return max(0.0, min(1.0, f))

        @field_validator("reasoning", mode="before")
        @classmethod
        def truncate_reasoning(cls, v):
            return ("" if v is None else str(v))[:200]

        @field_validator("gjallarhorn_tier", mode="before")
        @classmethod
        def validate_tier(cls, v):
            try:
                i = int(v)
            except Exception:
                i = 1
            return i if i in (1, 2) else 2

        def is_destructive(self) -> bool:
            return self.action_required in DESTRUCTIVE_ACTIONS

        def is_safe(self) -> bool:
            return self.action_required in SAFE_ACTIONS

        def to_dict(self) -> dict:
            return {
                "schema_version":    self.schema_version,
                "incident_detected": self.incident_detected,
                "severity":          self.severity.value,
                "boundary":          self.boundary.value,
                "threat_class":      self.threat_class,
                "confidence":        round(self.confidence, 3),
                "action_required":   self.action_required.value,
                "target":            self.target,
                "gjallarhorn_tier":  self.gjallarhorn_tier,
                "reasoning":         self.reasoning,
                "extractor_model":   self.extractor_model,
                "reasoner_model":    self.reasoner_model,
                "hardware_tier":     self.hardware_tier,
                "mitre_attack":      self.mitre_attack,
                "action_effective":  self.action_effective.value
                                     if self.action_effective else None,
                "policy_rationale":  self.policy_rationale,
                "rollback_id":       self.rollback_id,
                "event_id":          self.event_id,
            }

        @classmethod
        def from_dict(cls, d: dict) -> "Decision":
            import logging
            log = logging.getLogger("heimdall.schema")
            decision = cls.model_validate(d)
            if not decision.incident_detected and decision.is_destructive():
                log.warning(
                    f"Contradictory payload: incident_detected=False "
                    f"but action={decision.action_required.value}. "
                    f"Downgrading to ALERT."
                )
                decision.action_required = ActionType.ALERT
            return decision

        @classmethod
        def safe_fallback(cls, reason: str = "parser_error") -> "Decision":
            return cls(
                schema_version=SCHEMA_VERSION,
                incident_detected=True,
                severity=Severity.LOW,
                boundary=Boundary.UNKNOWN,
                threat_class="parser_error",
                confidence=0.5,
                action_required=ActionType.ALERT,
                reasoning=f"Safe fallback: {reason}"[:200],
                reasoner_model="safe_fallback",
            )

else:
    _logger.warning(
        "Pydantic not available. Running in degraded mode. "
        "Full schema validation active; destructive actions blocked at policy gate."
    )
    import dataclasses

    _VALID_BOUNDARIES   = {"HOST", "HONEYPOT", "NETWORK", "UNKNOWN"}
    _VALID_SEVERITIES   = {"CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"}
    _VALID_ACTIONS      = {"KILL", "BLOCK", "QUARANTINE", "ALERT", "LOG", "NONE"}
    _VALID_TIERS        = {"TIER_1", "TIER_2", "TIER_3", "TIER_4"}

    @dataclasses.dataclass
    class RawEvent:
        source:    str
        timestamp: str
        boundary:  Boundary           # stored as Boundary enum in degraded mode too
        raw:       Any

        def to_dict(self) -> dict:
            return {
                "source":    self.source,
                "timestamp": self.timestamp,
                "boundary":  self.boundary.value,
                "raw":       self.raw,
            }

        @classmethod
        def from_dict(cls, d: dict):
            # Reject unknown fields — mirrors Pydantic extra="forbid"
            allowed = {"source", "timestamp", "boundary", "raw"}
            extra = set(d.keys()) - allowed
            if extra:
                raise ValueError(f"unknown fields: {extra!r}")

            src = str(d.get("source", "")).strip()
            if not src:
                raise ValueError("source cannot be empty")
            ts = _normalize_iso8601(str(d.get("timestamp", "")))
            b_raw = str(d.get("boundary", "UNKNOWN"))
            if b_raw not in _VALID_BOUNDARIES:
                raise ValueError(f"invalid boundary: {b_raw!r}")
            return cls(
                source=src, timestamp=ts,
                boundary=Boundary(b_raw), raw=d.get("raw", {})
            )

    @dataclasses.dataclass
    class Decision:
        schema_version:    str            = SCHEMA_VERSION
        incident_detected: bool           = False
        severity:          Severity       = Severity.INFO
        boundary:          Boundary       = Boundary.UNKNOWN
        threat_class:      str            = "unknown"
        confidence:        float          = 0.0
        action_required:   ActionType     = ActionType.NONE
        target:            Any            = None
        gjallarhorn_tier:  int            = 1
        reasoning:         str            = ""
        extractor_model:   str            = "unknown"
        reasoner_model:    str            = "unknown"
        hardware_tier:     str            = "TIER_4"
        mitre_attack:      Any            = dataclasses.field(default_factory=list)
        action_effective:  Any            = None
        policy_rationale:  Any            = None
        rollback_id:       Any            = None
        event_id:          Any            = None

        def __post_init__(self):
            # Normalise confidence
            self.confidence = max(0.0, min(1.0, float(self.confidence)))
            # Truncate reasoning
            self.reasoning = str(self.reasoning)[:200]
            # Clamp gjallarhorn tier
            if self.gjallarhorn_tier not in (1, 2):
                self.gjallarhorn_tier = 2
            # Coerce enum fields when passed as strings
            if isinstance(self.severity, str):
                v = self.severity.upper()
                self.severity = Severity(v) if v in _VALID_SEVERITIES else Severity.INFO
            if isinstance(self.boundary, str):
                v = self.boundary.upper()
                self.boundary = Boundary(v) if v in _VALID_BOUNDARIES else Boundary.UNKNOWN
            if isinstance(self.action_required, str):
                v = self.action_required.upper()
                if v not in _VALID_ACTIONS:
                    raise ValueError(
                        f"Invalid action_required {v!r}. "
                        f"Must be one of {sorted(_VALID_ACTIONS)!r}."
                    )
                self.action_required = ActionType(v)
            if isinstance(self.action_effective, str):
                v = self.action_effective.upper()
                self.action_effective = ActionType(v) if v in _VALID_ACTIONS else None
            # Validate hardware_tier
            if isinstance(self.hardware_tier, str):
                v = self.hardware_tier.upper()
                if v not in _VALID_TIERS:
                    raise ValueError(
                        f"Invalid hardware_tier {v!r}. "
                        f"Must be one of {sorted(_VALID_TIERS)!r}."
                    )
                self.hardware_tier = v
            # Lock schema_version
            self.schema_version = SCHEMA_VERSION

        def is_destructive(self):
            return self.action_required in DESTRUCTIVE_ACTIONS

        def is_safe(self):
            return self.action_required in SAFE_ACTIONS

        def to_dict(self):
            def _enum_val(v):
                """Return v.value if it is an enum, else v as-is (defensive fallback)."""
                return v.value if hasattr(v, "value") else v

            return {
                "schema_version":    self.schema_version,
                "incident_detected": self.incident_detected,
                "severity":          _enum_val(self.severity),
                "boundary":          _enum_val(self.boundary),
                "threat_class":      self.threat_class,
                "confidence":        round(self.confidence, 3),
                "action_required":   _enum_val(self.action_required),
                "target":            self.target,
                "gjallarhorn_tier":  self.gjallarhorn_tier,
                "reasoning":         self.reasoning,
                "extractor_model":   self.extractor_model,
                "reasoner_model":    self.reasoner_model,
                "hardware_tier":     self.hardware_tier,
                "mitre_attack":      list(self.mitre_attack or []),
                "action_effective":  _enum_val(self.action_effective)
                                     if self.action_effective is not None else None,
                "policy_rationale":  self.policy_rationale,
                "rollback_id":       self.rollback_id,
                "event_id":          self.event_id,
            }

        @classmethod
        def from_dict(cls, d):
            allowed = {f.name for f in dataclasses.fields(cls)}
            # Reject unknown fields — mirrors Pydantic extra="forbid"
            extra = set(d.keys()) - allowed
            if extra:
                raise ValueError(f"unknown fields: {extra!r}")
            data = {k: v for k, v in d.items() if k in allowed}
            decision = cls(**data)
            # Contradictory payload guard
            if not decision.incident_detected and decision.is_destructive():
                _logger.warning(
                    f"Contradictory payload: incident_detected=False "
                    f"but action={decision.action_required.value}. "
                    f"Downgrading to ALERT."
                )
                decision.action_required = ActionType.ALERT
            return decision

        @classmethod
        def safe_fallback(cls, reason="parser_error"):
            return cls(
                schema_version=SCHEMA_VERSION,
                incident_detected=True,
                severity="LOW",
                boundary="UNKNOWN",
                threat_class="parser_error",
                confidence=0.5,
                action_required="ALERT",
                reasoning=f"Safe fallback: {reason}"[:200],
                reasoner_model="safe_fallback",
            )


def validate_decision_dict(d: dict) -> "Decision":
    try:
        return Decision.from_dict(d)
    except Exception as e:
        _logger.warning(f"Decision validation failed: {e}. Using safe fallback.")
        return Decision.safe_fallback(str(e))


def validate_raw_event(d: dict) -> "RawEvent":
    try:
        return RawEvent.from_dict(d)
    except Exception as e:
        raise ValueError(f"Invalid event envelope: {e}")
