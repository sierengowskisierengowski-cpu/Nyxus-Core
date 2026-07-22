"""ntfy.sh push notification."""
import requests
import structlog
from meli.config import get_config

log = structlog.get_logger()

_SEVERITY_PRIORITY = {
    "INFO": "1",
    "LOW": "2",
    "MEDIUM": "3",
    "HIGH": "4",
    "CRITICAL": "5",
}

_SEVERITY_TAGS = {
    "INFO": "information_source",
    "LOW": "speech_balloon",
    "MEDIUM": "warning",
    "HIGH": "rotating_light",
    "CRITICAL": "rotating_light,fire",
}


def notify(rule_name: str, summary: str, severity: str) -> None:
    cfg = get_config()
    url = cfg.get("alerts", "ntfy_url")
    if not url:
        return
    headers = {
        "Title": f"Meli: {rule_name}",
        "Priority": _SEVERITY_PRIORITY.get(severity.upper(), "3"),
        "Tags": _SEVERITY_TAGS.get(severity.upper(), "warning"),
    }
    token = cfg.get("alerts", "ntfy_token")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        requests.post(url, data=summary.encode("utf-8"), headers=headers, timeout=8)
    except Exception as e:
        log.warning("ntfy notification failed", error=str(e))
