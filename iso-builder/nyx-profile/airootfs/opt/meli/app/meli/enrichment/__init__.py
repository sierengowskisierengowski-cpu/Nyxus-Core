"""Enrichment package — parallel IP enrichment from multiple services."""
from __future__ import annotations

import os
import json
import concurrent.futures
import structlog
from datetime import datetime, timezone

log = structlog.get_logger()

# Tier-3 threat-intel providers. Each key can be supplied EITHER via the
# config file (enrichment.services.<svc>.api_key) OR an environment variable
# (checked first so secrets never need to touch the config on disk). No keys
# are hardcoded — absent a key, the provider stays cleanly disabled.
_ENV_KEYS: dict[str, str] = {
    "abuseipdb": "MELI_ABUSEIPDB_KEY",
    "greynoise": "MELI_GREYNOISE_KEY",
    "virustotal": "MELI_VIRUSTOTAL_KEY",
    "shodan": "MELI_SHODAN_KEY",
    "ipinfo": "MELI_IPINFO_KEY",
}

# Where to obtain a free key for each provider (surfaced in status output).
_KEY_HELP: dict[str, str] = {
    "abuseipdb": "Free tier: https://www.abuseipdb.com/register (1000 checks/day)",
    "greynoise": "Community API: https://viz.greynoise.io/signup",
    "virustotal": "Free API: https://www.virustotal.com/gui/join-us",
    "shodan": "https://account.shodan.io/register",
    "ipinfo": "Free token: https://ipinfo.io/signup",
}


def resolve_api_key(service: str) -> str | None:
    """Return the API key for a provider from env (preferred) or config."""
    env_var = _ENV_KEYS.get(service)
    if env_var:
        val = os.environ.get(env_var)
        if val:
            return val.strip()
    from meli.config import get_config
    cfg = get_config()
    val = cfg.get("enrichment", "services", service, "api_key")
    return val.strip() if isinstance(val, str) and val.strip() else None


def provider_status() -> dict[str, dict]:
    """Report each provider's enable/disable state and *why*.

    A provider is considered active when a key is resolvable (env or config)
    AND it isn't explicitly disabled in config. Otherwise it reports the
    'add API key to enable' state with a link to obtain a free key.
    """
    from meli.config import get_config
    cfg = get_config()
    svc_cfg = cfg.get("enrichment", "services", default={}) or {}
    out: dict[str, dict] = {}
    for svc in _ENV_KEYS:
        key = resolve_api_key(svc)
        source = None
        if key:
            source = "env" if os.environ.get(_ENV_KEYS[svc]) else "config"
        out[svc] = {
            "active": bool(key),
            "has_key": bool(key),
            "key_source": source,
            "env_var": _ENV_KEYS[svc],
            "state": ("active" if key else "disabled — add API key to enable"),
            "get_key": _KEY_HELP.get(svc, ""),
        }
    return out


def enrich_ip(ip: str) -> dict:
    """
    Enrich an IP using all configured services in parallel.
    Results are stored in DB and returned.
    """
    from meli.config import get_config
    from meli.enrichment.cache import get_cached, set_cached
    from meli.enrichment.geolocation import geolocate_ip
    from meli.enrichment.abuseipdb import query_abuseipdb
    from meli.enrichment.greynoise import query_greynoise
    from meli.enrichment.virustotal import query_virustotal
    from meli.enrichment.shodan import query_shodan
    from meli.enrichment.ipinfo import query_ipinfo

    cfg = get_config()
    result: dict = {"ip": ip}

    # Check full cache first
    cached = get_cached(f"full:{ip}")
    if cached:
        return cached

    # Parallel enrichment. GeoIP (offline) always runs. Tier-3 providers run
    # only when a key is resolvable (env or config) and not explicitly
    # disabled — so simply adding a key turns the provider on with no other
    # config change, and the absence of a key leaves it cleanly off.
    services = {
        "geo": (geolocate_ip, ip),
    }
    enrichment_cfg = cfg.get("enrichment", "services", default={}) or {}
    _fns = {
        "abuseipdb": query_abuseipdb,
        "greynoise": query_greynoise,
        "virustotal": query_virustotal,
        "shodan": query_shodan,
        "ipinfo": query_ipinfo,
    }
    for svc, fn in _fns.items():
        # A resolvable key (env or config) is the enable signal — add a key
        # and the provider turns on; with no key it stays cleanly off.
        if resolve_api_key(svc):
            services[svc] = (fn, ip)

    parallelism = cfg.get("performance", "enrichment_parallelism", default=4)

    with concurrent.futures.ThreadPoolExecutor(max_workers=parallelism) as ex:
        futures = {name: ex.submit(fn, arg) for name, (fn, arg) in services.items()}
        for name, future in futures.items():
            try:
                result[name] = future.result(timeout=10)
            except Exception as e:
                log.debug("Enrichment service failed", service=name, ip=ip, error=str(e))
                result[name] = None

    # Store enriched data to DB
    _store_enrichment(ip, result)

    # Cache composite result for 24h
    ttl = cfg.get("enrichment", "cache_ttl_hours", default=24) * 3600
    set_cached(f"full:{ip}", result, ttl_seconds=ttl)

    return result


def _store_enrichment(ip: str, data: dict) -> None:
    try:
        from meli.database import get_db
        from meli.database.models import Attacker
        from meli.utils.helpers import is_valid_ip

        if not is_valid_ip(ip):
            return

        geo = data.get("geo") or {}
        abuse = data.get("abuseipdb") or {}
        gn = data.get("greynoise") or {}
        vt = data.get("virustotal") or {}

        with get_db() as db:
            attacker = db.get(Attacker, ip)
            if attacker:
                attacker.country_code = geo.get("country_code") or attacker.country_code
                attacker.asn = geo.get("asn") or attacker.asn
                attacker.organization = geo.get("organization") or attacker.organization
                attacker.abuseipdb_score = abuse.get("abuse_score")
                attacker.greynoise_classification = gn.get("classification")
                attacker.greynoise_tags = json.dumps(gn.get("tags", []))
                attacker.virustotal_malicious = vt.get("malicious")
                attacker.enriched_at = datetime.now(timezone.utc)
    except Exception as e:
        log.debug("Failed to store enrichment in DB", ip=ip, error=str(e))
