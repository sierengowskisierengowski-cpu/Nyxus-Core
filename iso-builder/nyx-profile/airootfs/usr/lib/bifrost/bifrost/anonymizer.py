#!/usr/bin/env python3
"""
Bifrost Anonymizer v0.1.0

The privacy layer. Before any event data reaches the
Claude API or any external service, it passes through
here. Internal IPs, hostnames, usernames, and paths
are replaced with tokens. A session map maintains the
mapping so responses can be acted on with real targets.

Your internal network topology never leaves your machine.
"""

import re
import json
import logging
from typing import Any

log = logging.getLogger("heimdall.anonymizer")

# Patterns to detect and replace
PRIVATE_IP_PATTERN = re.compile(
    r'\b(192\.168\.\d{1,3}\.\d{1,3}|'
    r'10\.\d{1,3}\.\d{1,3}\.\d{1,3}|'
    r'172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})\b'
)
MAC_PATTERN = re.compile(
    r'\b([0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}\b'
)
USERNAME_PATTERN = re.compile(
    r'/home/([a-zA-Z0-9_-]+)/'
)
HOSTNAME_PATTERN = re.compile(
    r'\b(NyxOS|NyXxOS|nyx-cosmic|gowski|GowskiNet)\b',
    re.IGNORECASE
)


class Anonymizer:
    """
    Session-scoped anonymizer. Maintains token maps for
    the duration of a single API call so responses can
    be de-anonymized and acted on with real targets.
    """

    def __init__(self):
        self.ip_map: dict[str, str] = {}
        self.ip_counter = 0
        self.user_map: dict[str, str] = {}
        self.user_counter = 0
        self.host_map: dict[str, str] = {}
        self.host_counter = 0
        self.reverse_map: dict[str, str] = {}

    def _token_for_ip(self, ip: str) -> str:
        if ip not in self.ip_map:
            self.ip_counter += 1
            token = f"INTERNAL_HOST_{chr(64 + self.ip_counter)}"
            self.ip_map[ip] = token
            self.reverse_map[token] = ip
        return self.ip_map[ip]

    def _token_for_user(self, username: str) -> str:
        if username not in self.user_map:
            self.user_counter += 1
            token = f"REDACTED_USER_{self.user_counter}"
            self.user_map[username] = token
            self.reverse_map[token] = username
        return self.user_map[username]

    def _token_for_host(self, hostname: str) -> str:
        key = hostname.lower()
        if key not in self.host_map:
            self.host_counter += 1
            token = f"INTERNAL_NODE_{self.host_counter}"
            self.host_map[key] = token
            self.reverse_map[token] = hostname
        return self.host_map[key]

    def anonymize_string(self, text: str) -> str:
        if not isinstance(text, str):
            return text

        # Replace private IPs
        def replace_ip(match):
            return self._token_for_ip(match.group(0))
        text = PRIVATE_IP_PATTERN.sub(replace_ip, text)

        # Replace MAC addresses
        text = MAC_PATTERN.sub("[MAC_REDACTED]", text)

        # Replace /home/username/ paths
        def replace_user(match):
            token = self._token_for_user(match.group(1))
            return f"/home/{token}/"
        text = USERNAME_PATTERN.sub(replace_user, text)

        # Replace known hostnames
        def replace_host(match):
            return self._token_for_host(match.group(0))
        text = HOSTNAME_PATTERN.sub(replace_host, text)

        return text

    def anonymize_dict(self, data: Any) -> Any:
        if isinstance(data, str):
            return self.anonymize_string(data)
        elif isinstance(data, dict):
            return {k: self.anonymize_dict(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self.anonymize_dict(item) for item in data]
        else:
            return data

    def anonymize_event(self, compressed: dict) -> dict:
        return self.anonymize_dict(compressed)

    def deanonymize_decision(self, decision: dict) -> dict:
        """
        Replaces tokens in the decision back with real values
        so the executor can act on real IPs and paths.
        """
        decision_str = json.dumps(decision)
        for token, real_value in self.reverse_map.items():
            decision_str = decision_str.replace(token, real_value)
        try:
            return json.loads(decision_str)
        except Exception:
            return decision

    def get_session_map(self) -> dict:
        return {
            "ip_map": self.ip_map,
            "user_map": self.user_map,
            "host_map": self.host_map
        }


def anonymize_for_external_api(
    compressed: dict,
    config: dict
) -> tuple[dict, "Anonymizer"]:
    """
    Main entry point. Anonymizes a compressed event
    before sending to any external API.
    Returns the anonymized event and the anonymizer
    instance needed to de-anonymize the response.

    Only runs when routing to external APIs.
    Local Ollama calls do not need anonymization.
    """
    tier = config.get("hardware_tier", "TIER_4")
    use_local = config.get("use_local_llm", False)

    anonymizer = Anonymizer()

    # Local Ollama — no anonymization needed
    # Data never leaves the machine
    if use_local and tier in ["TIER_1", "TIER_2"]:
        log.debug("Local model — anonymization skipped.")
        return compressed, anonymizer

    # External API — anonymize everything
    log.debug("External API route — anonymizing event.")
    anonymized = anonymizer.anonymize_event(compressed)
    return anonymized, anonymizer


if __name__ == "__main__":
    test_compressed = {
        "event_type": "network_watcher",
        "boundary": "HOST",
        "ip": "192.168.0.172",
        "port": 4444,
        "process": "implant",
        "path": "/home/nyx/implant",
        "command": "/home/nyx/implant -c 192.168.0.172",
        "alert_signal": "honeypot_to_host_connection",
        "raw_snippet": "NyxOS connection from 192.168.0.125 to 192.168.0.172:4444"
    }

    test_config = {
        "hardware_tier": "TIER_4",
        "use_local_llm": False
    }

    print("Testing anonymization...")
    anonymizer = Anonymizer()
    anonymized = anonymizer.anonymize_event(test_compressed)
    print("Anonymized:")
    print(json.dumps(anonymized, indent=2))

    fake_decision = {
        "action_required": "BLOCK",
        "target": "INTERNAL_HOST_A",
        "reasoning": "INTERNAL_HOST_A attempting breakout"
    }

    print("\nDe-anonymizing decision...")
    real_decision = anonymizer.deanonymize_decision(fake_decision)
    print(json.dumps(real_decision, indent=2))

    print("\nSession map:")
    print(json.dumps(anonymizer.get_session_map(), indent=2))
