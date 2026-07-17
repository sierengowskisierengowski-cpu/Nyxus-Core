#!/usr/bin/env python3
import json
import logging
import psutil
import urllib.request
from datetime import datetime, timedelta, timezone

_ATTACKER_SESSION_MEMORY = {}
_ANALYST_INFERENCE_CACHE = {}
LOG = logging.getLogger("heimdall.analyst_matrix")

def get_active_ollama_model():
    ollama_tags_url = "http://127.0.0.1:11434/api/tags"
    available_ram_gb = psutil.virtual_memory().available / (1024 ** 3)
    if available_ram_gb < 6.0:
        hardware_target_tier = "qwen2.5:1.5b-instruct"
    elif 6.0 <= available_ram_gb < 10.0:
        hardware_target_tier = "qwen2.5:7b-instruct"
    else:
        hardware_target_tier = "qwen2.5:32b"
    try:
        req = urllib.request.Request(ollama_tags_url, headers={"User-Agent": "Bifrost-Audit"})
        with urllib.request.urlopen(req, timeout=2) as response:
            data = json.loads(response.read().decode("utf-8"))
            models = [m.get("name") for m in data.get("models", [])]
            if hardware_target_tier in models or any(hardware_target_tier in m for m in models):
                return hardware_target_tier
            for target in ["qwen2.5:32b", "qwen2.5:14b", "qwen2.5:7b-instruct", "qwen2.5:1.5b-instruct"]:
                if target in models or any(target in m for m in models):
                    return target
            return models[0] if models else "qwen2.5:7b-instruct"
    except Exception:
        return hardware_target_tier

def execute_gpu_analyst_inference(compacted_log_payload):
    global _ATTACKER_SESSION_MEMORY, _ANALYST_INFERENCE_CACHE
    ollama_endpoint = "http://127.0.0.1:11434/api/generate"
    active_model = get_active_ollama_model()
    compacted_log_payload["_resolved_model_tier"] = active_model
    source_ip = compacted_log_payload.get("attacker", compacted_log_payload.get("attacker_ip", "0.0.0.0"))
    classification = compacted_log_payload.get("classification", "Anomalous Activity Detection")
    current_time = datetime.now(timezone.utc)
    cache_key = f"{source_ip}:{classification}"
    if cache_key in _ANALYST_INFERENCE_CACHE:
        cache_entry = _ANALYST_INFERENCE_CACHE[cache_key]
        if current_time < cache_entry["expiration"]:
            return cache_entry["data"]
    current_action = compacted_log_payload.get("action", compacted_log_payload.get("commands", ["No input"]))
    if isinstance(current_action, list):
        current_action = " | ".join(current_action)
    if source_ip not in _ATTACKER_SESSION_MEMORY:
        _ATTACKER_SESSION_MEMORY[source_ip] = []
    _ATTACKER_SESSION_MEMORY[source_ip].append(current_action)
    if len(_ATTACKER_SESSION_MEMORY[source_ip]) > 10:
        _ATTACKER_SESSION_MEMORY[source_ip].pop(0)
    rolling_session_history = _ATTACKER_SESSION_MEMORY[source_ip]
    system_instructions = (
        f"You are the Bifrost Core Analyst Matrix ({active_model}), an enterprise-grade AI Incident Commander. "
        "Determine the MITRE ATT&CK tactical lifecycle step and output strictly as JSON:\n"
        "{\n"
        "  \"severity\": \"CRITICAL\",\n"
        "  \"mitre_mapping\": [\"TA0040 - Impact\"],\n"
        "  \"threat_actor_attribution\": \"APT group name and reasoning.\",\n"
        "  \"confidence_score\": 0.96,\n"
        "  \"strategic_recommendation\": \"Containment steps.\"\n"
        "}\n"
        "Severity must be: INFO, LOW, MEDIUM, HIGH, or CRITICAL. Return ONLY raw JSON."
    )
    inference_blueprint = {
        "model": active_model,
        "prompt": (
            f"Instructions: {system_instructions}\n"
            f"Suspect IP: {source_ip}\n"
            f"Event: {json.dumps(compacted_log_payload)}\n"
            f"Session History: {json.dumps(rolling_session_history)}"
        ),
        "stream": False,
        "format": "json"
    }
    try:
        raw_bytes = json.dumps(inference_blueprint).encode("utf-8")
        req = urllib.request.Request(
            ollama_endpoint, data=raw_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "Bifrost-Analyst-Matrix"}
        )
        with urllib.request.urlopen(req) as response:
            server_reply = json.loads(response.read().decode("utf-8"))
            parsed_analysis = json.loads(server_reply.get("response", "{}"))
            _ANALYST_INFERENCE_CACHE[cache_key] = {
                "expiration": current_time + timedelta(minutes=60),
                "data": parsed_analysis
            }
            return parsed_analysis
    except Exception as error:
        LOG.warning("Analyst Matrix inference request failed: %s", error)
        return {
            "severity": "HIGH",
            "mitre_mapping": ["TA0001 - Initial Access"],
            "threat_actor_attribution": "Automated Commodity Attack Infrastructure",
            "confidence_score": 0.45,
            "strategic_recommendation": "Invoke Go host defense block protocols via firewall rules."
        }

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ram_now = psutil.virtual_memory().available / (1024 ** 3)
    selected = get_active_ollama_model()
    LOG.info("Analyst Matrix initialized.")
    LOG.info("Available RAM: %.2f GB | Selected Model: %s", ram_now, selected)
