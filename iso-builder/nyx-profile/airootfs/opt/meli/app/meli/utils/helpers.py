"""General-purpose helpers for Meli."""
from __future__ import annotations

import re
import socket
import ipaddress
from datetime import datetime, timezone
from typing import Any


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    if seconds < 3600:
        return f"{int(seconds // 60)}m {int(seconds % 60)}s"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m}m"


def is_valid_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False


def is_private_ip(ip: str) -> bool:
    try:
        return ipaddress.ip_address(ip).is_private
    except ValueError:
        return False


def truncate(s: str, max_len: int = 80) -> str:
    return s if len(s) <= max_len else s[:max_len - 3] + "..."


def severity_color(severity: str) -> str:
    """Return CSS color name for a severity level."""
    return {
        "INFO": "#94a3b8",
        "LOW": "#60a5fa",
        "MEDIUM": "#f59e0b",
        "HIGH": "#f97316",
        "CRITICAL": "#ef4444",
    }.get(severity.upper(), "#94a3b8")


def severity_rank(severity: str) -> int:
    return {"INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}.get(severity.upper(), 0)


# Post-auth command intent taxonomy. Kept here (not in the GTK UI layer) so
# the headless ingest daemon can classify command intent without importing Gtk.
_COMMAND_INTENTS: dict[str, tuple[str, ...]] = {
    "download": ("wget", "curl", "tftp", "ftpget", "scp", "rsync", "fetch "),
    "persistence": ("crontab", "rc.local", "init.d", "authorized_keys",
                    "useradd", "systemctl enable", "chattr"),
    "recon": ("uname", "ifconfig", "ip addr", "ps aux", "/etc/passwd",
              "/etc/shadow", "whoami", "lscpu", "cat /proc"),
    "escalation": ("sudo", "su -", "chmod +s", "setuid", "chmod 777"),
    "mining": ("xmrig", "minerd", "stratum", "pool.", "cpuminer"),
    "evasion": ("history -c", "shred", "unset histfile", "rm -rf /tmp",
                "iptables -f", "> /var/log"),
    "destruction": ("rm -rf /", "mkfs", "dd if=/dev/zero", ":(){ :|:& };:"),
}


def classify_command_intent(cmd: str) -> str:
    """Best-effort intent label for an attacker-issued shell command."""
    if not cmd:
        return "unknown"
    cmd_lower = cmd.lower()
    for intent, patterns in _COMMAND_INTENTS.items():
        if any(p in cmd_lower for p in patterns):
            return intent
    return "unknown"


def generate_token(length: int = 32) -> str:
    import secrets
    return secrets.token_urlsafe(length)


def country_flag_emoji(country_code: str) -> str:
    """Convert ISO-3166-1 alpha-2 code to flag emoji."""
    if not country_code or len(country_code) != 2:
        return "🏳"
    offset = 127397
    return "".join(chr(ord(c) + offset) for c in country_code.upper())


def parse_cidr_or_ip(value: str) -> list[str]:
    """Expand a CIDR block or single IP into a list of IPs (max 256)."""
    try:
        net = ipaddress.ip_network(value, strict=False)
        hosts = list(net.hosts())
        return [str(h) for h in hosts[:256]]
    except ValueError:
        if is_valid_ip(value):
            return [value]
        return []
