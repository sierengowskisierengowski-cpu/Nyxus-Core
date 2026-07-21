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


def generate_token(length: int = 32) -> str:
    import secrets
    return secrets.token_urlsafe(length)


def country_flag_emoji(country_code: str) -> str:
    """Convert ISO-3166-1 alpha-2 code to flag emoji."""
    if not country_code or len(country_code) != 2:
        return "🏳"
    offset = 127397
    return "".join(chr(ord(c) + offset) for c in country_code.upper())


# Approximate (lat, lon) centroids for ISO-3166-1 alpha-2 country codes.
# Used by the Geographic Map view to plot per-country attack pins when the
# Event records only store the country code (not lat/lon).
_COUNTRY_CENTROIDS: dict[str, tuple[float, float]] = {
    "US": (39.5, -98.35), "CN": (35.86, 104.20), "RU": (61.52, 105.32),
    "BR": (-14.24, -51.93), "IN": (20.59, 78.96), "DE": (51.17, 10.45),
    "GB": (55.38, -3.44), "FR": (46.23, 2.21), "NL": (52.13, 5.29),
    "JP": (36.20, 138.25), "KR": (35.91, 127.77), "KP": (40.34, 127.51),
    "CA": (56.13, -106.35), "MX": (23.63, -102.55), "AU": (-25.27, 133.78),
    "IT": (41.87, 12.57), "ES": (40.46, -3.75), "PL": (51.92, 19.15),
    "UA": (48.38, 31.17), "TR": (38.96, 35.24), "IR": (32.43, 53.69),
    "IQ": (33.22, 43.68), "SA": (23.89, 45.08), "AE": (23.42, 53.85),
    "IL": (31.05, 34.85), "EG": (26.82, 30.80), "ZA": (-30.56, 22.94),
    "NG": (9.08, 8.68), "KE": (-0.02, 37.91), "AR": (-38.42, -63.62),
    "CO": (4.57, -74.30), "VE": (6.42, -66.59), "CL": (-35.68, -71.54),
    "PE": (-9.19, -75.02), "ID": (-0.79, 113.92), "MY": (4.21, 101.98),
    "SG": (1.35, 103.82), "TH": (15.87, 100.99), "VN": (14.06, 108.28),
    "PH": (12.88, 121.77), "PK": (30.38, 69.35), "BD": (23.68, 90.36),
    "TW": (23.70, 121.00), "HK": (22.32, 114.17), "CH": (46.82, 8.23),
    "SE": (60.13, 18.64), "NO": (60.47, 8.47), "FI": (61.92, 25.75),
    "DK": (56.26, 9.50), "BE": (50.50, 4.47), "AT": (47.52, 14.55),
    "CZ": (49.82, 15.47), "RO": (45.94, 24.97), "BG": (42.73, 25.49),
    "GR": (39.07, 21.82), "PT": (39.40, -8.22), "IE": (53.41, -8.24),
    "HU": (47.16, 19.50), "SK": (48.67, 19.70), "BY": (53.71, 27.95),
    "KZ": (48.02, 66.92), "UZ": (41.38, 64.59), "AF": (33.94, 67.71),
    "DZ": (28.03, 1.66), "MA": (31.79, -7.09), "TN": (33.89, 9.54),
    "LY": (26.34, 17.23), "ET": (9.15, 40.49), "SD": (12.86, 30.22),
    "GH": (7.95, -1.02), "CI": (7.54, -5.55), "TZ": (-6.37, 34.89),
    "NZ": (-40.90, 174.89), "EC": (-1.83, -78.18), "BO": (-16.29, -63.59),
    "UY": (-32.52, -55.77), "PY": (-23.44, -58.44),
}


def country_centroid(country_code: str) -> tuple[float, float] | None:
    """Return approximate (lat, lon) for an ISO-3166-1 alpha-2 country code."""
    if not country_code or len(country_code) != 2:
        return None
    return _COUNTRY_CENTROIDS.get(country_code.upper())


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


# Map raw honeypot_service values onto short, recognisable labels for UIs.
# Anything not in this map is shown verbatim so new honeypot types still
# render sensibly without a code change.
_SERVICE_LABELS = {
    "cowrie": "SSH",
    "ssh": "SSH",
    "telnet": "Telnet",
    "http": "HTTP",
    "https": "HTTP",
    "heralding": "Multi",
    "dionaea": "Malware",
    "glastopf": "HTTP",
    "mailoney": "SMTP",
    "unknown": "?",
}


def format_honeypot_services(services: list[str]) -> str:
    """Render a sorted, deduplicated list of service tags for an attacker.

    Used by the Attackers view to make 'SSH only', 'HTTP only', and
    'SSH + HTTP' attackers visually distinct without opening a detail panel.
    """
    if not services:
        return ""
    labels: list[str] = []
    seen: set[str] = set()
    for svc in services:
        label = _SERVICE_LABELS.get((svc or "").lower(), svc or "?")
        if label not in seen:
            labels.append(label)
            seen.add(label)
    return " | ".join(labels)
