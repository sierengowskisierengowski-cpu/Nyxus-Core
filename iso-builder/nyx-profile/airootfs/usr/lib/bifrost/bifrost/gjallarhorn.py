#!/usr/bin/env python3
import os
import json
import base64
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timezone

_ALERT_DEDUPLICATION_CACHE = {}
_GLOBAL_WINDOW_TRACKER = {"start_time": datetime.now(timezone.utc), "alert_count": 0}
LOG = logging.getLogger("heimdall.gjallarhorn")

def generate_ascii_forensic_chart(count):
    bars = min(count, 15)
    return "[" + "█" * bars + "░" * (15 - bars) + f"] Velocity Rank: {count} events/min"

def dispatch_sms_via_twilio(body_text):
    """Fallback signaling daemon triggering SMS warnings via Twilio REST API."""
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    to_num = os.getenv("TWILIO_TO_NUMBER")
    from_num = os.getenv("TWILIO_FROM_NUMBER")

    if not all([sid, token, to_num, from_num]):
        return False # Silently skip fallback if keys are unconfigured

    twilio_url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
    raw_payload = {"To": to_num, "From": from_num, "Body": body_text}
    encoded_data = urllib.parse.urlencode(raw_payload).encode("utf-8")
    
    try:
        req = urllib.request.Request(twilio_url, data=encoded_data, method="POST")
        auth_string = f"{sid}:{token}"
        encoded_auth = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
        req.add_header("Authorization", f"Basic {encoded_auth}")
        
        with urllib.request.urlopen(req) as res:
            return res.status == 201
    except Exception as err:
        LOG.warning("Twilio SMS fallback failed: %s", err)
        return False

def dispatch_discord_alert(telemetry, analysis=None):
    global _ALERT_DEDUPLICATION_CACHE, _GLOBAL_WINDOW_TRACKER
    
    analysis = analysis or {}
    severity = telemetry.get("severity", analysis.get("severity", "MEDIUM")).upper()

    # FEATURE 1: SEVERITY GATING - Silently log and ignore LOW/INFO/MEDIUM tiers
    if severity not in ["HIGH", "CRITICAL"]:
        LOG.debug("Gjallarhorn suppressing low-risk alert: severity=%s", severity)
        return True

    webhook_url = os.getenv("GJALLARHORN_WEBHOOK_URL")
    current_time = datetime.now(timezone.utc)

    # FEATURE 2: GLOBAL RATE-LIMITING - Caps absolute notification floods across ALL IPs
    time_delta = (current_time - _GLOBAL_WINDOW_TRACKER["start_time"]).total_seconds()
    if time_delta < 60:
        if _GLOBAL_WINDOW_TRACKER["alert_count"] >= 10: # Max 10 system alerts per minute total
            LOG.warning("Gjallarhorn global alert cap exceeded; suppressing notification.")
            return True
        _GLOBAL_WINDOW_TRACKER["alert_count"] += 1
    else:
        _GLOBAL_WINDOW_TRACKER = {"start_time": current_time, "alert_count": 1}

    # FEATURE 3: IP-DEDUPLICATION LOGIC
    source_ip = telemetry.get("attacker_ip", telemetry.get("attacker", "0.0.0.0"))
    classification = telemetry.get("classification", "Privilege Escalation Vector")
    dedup_key = f"{source_ip}:{classification}"

    if dedup_key in _ALERT_DEDUPLICATION_CACHE:
        cache_entry = _ALERT_DEDUPLICATION_CACHE[dedup_key]
        if (current_time - cache_entry["first_triggered"]).total_seconds() < 60:
            cache_entry["count"] += 1
            return True
        else:
            _ALERT_DEDUPLICATION_CACHE.pop(dedup_key)

    _ALERT_DEDUPLICATION_CACHE[dedup_key] = {"first_triggered": current_time, "count": 1}
    event_count = _ALERT_DEDUPLICATION_CACHE[dedup_key]["count"]

    event_id = telemetry.get("event_id", "BIF-HEX-99F1")
    commands = telemetry.get("commands", telemetry.get("actions", ["kernel hook exploitation"]))
    mitre_tactics = ", ".join(analysis.get("mitre_mapping", ["TA0003 - Persistence"]))
    confidence = analysis.get("confidence_score", 0.95) * 100
    strategy = analysis.get("strategic_recommendation", "Isolate container system network interface hooks immediately.")

    velocity_chart = generate_ascii_forensic_chart(event_count)
    embed_color = 15539236 if severity == "CRITICAL" else 16753920

    alert_card = {
        "username": "Bifrost Core Infrastructure",
        "embeds": [{
            "title": f"⚡ [BIFROST HEIMDALL SECURITY ENGAGEMENT] — LEVEL: {severity}",
            "description": f"Autonomous containment mechanisms engaged at perimeter interface boundary.",
            "color": embed_color,
            "fields": [
                {"name": "🛰️ Sentry Node Telemetry ID", "value": f"`{event_id}`", "inline": True},
                {"name": "🎯 Hostile IP Fingerprint", "value": f"`{source_ip}`", "inline": True},
                {"name": "📉 Real-Time Adversary Injection Velocity", "value": f"`{velocity_chart}`", "inline": False},
                {"name": "🎭 Threat Signature Classification", "value": f"**{classification}**", "inline": False},
                {"name": "📟 Intercepted Kernel Execution String", "value": f"```bash\n" + "\n".join(commands)[:400] + "\n```", "inline": False},
                {"name": "🧠 Local 32B Brain Attribution", "value": f"`{mitre_tactics}` (`{confidence:.1f}% Confidence`)", "inline": False},
                {"name": "🛡️ Active Containment Mitigation Actions", "value": f"```diff\n- {strategy}\n```", "inline": False}
            ],
            "footer": {"text": "🚨 Sovereign Deployment Area — Perimeter Isolation Circuit Active"}
        }]
    }

    # Execute SMS fallback for high-criticality threats
    sms_summary = f"[Bifrost Alert] {severity}: Critical attack sequence identified from IP {source_ip}. Countermeasures deployed."
    dispatch_sms_via_twilio(sms_summary)

    if not webhook_url:
        LOG.info("Gjallarhorn webhook not configured; alert logged only.")
        return True

    try:
        req = urllib.request.Request(
            webhook_url, data=json.dumps(alert_card).encode("utf-8"),
            headers={"Content-Type": "application/json", "User-Agent": "Bifrost-Gjallarhorn"}
        )
        with urllib.request.urlopen(req) as response:
            return response.status == 204
    except Exception as error:
        LOG.warning("Gjallarhorn dispatch error: %s", error)
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    LOG.info("Gjallarhorn module initialized.")
