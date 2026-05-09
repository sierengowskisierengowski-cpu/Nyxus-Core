# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · ip_intel.py
IPv4 / IPv6 investigation.

  • IPinfo      — free tier, key required (50k/mo)
  • AbuseIPDB   — free tier, key required (1k/day)
  • Shodan      — paid (or membership), key required
  • VirusTotal  — free tier, key required
  • Tor exit list — public file from check.torproject.org
  • Reverse DNS — gethostbyaddr, no key
  • RDAP WHOIS — public ARIN/RIPE/APNIC RDAP, no key

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import socket
import time
from pathlib import Path
from typing import Dict, Any, Optional

import requests

# ── NYXUS palette (single source of truth · rev r13) ────────────────
try:
    from nyxus_palette import (
        WHITE_PURE, WHITE_OFF, GREY_LIGHT, GREY_MID, GREY_TERTIARY,
        INK_FADED, INK_BLACK,
        GLASS_DARK, GLASS_DEEPER, GLASS_DEEPEST,
        HAIRLINE_WHITE, HAIRLINE_INK,
        SHADOW_INK_ACTIVE, SHADOW_INK_INACTIVE,
        RADIUS_CARD, RADIUS_PILL, RADIUS_INPUT,
        FONT_UI, FONT_MONO, FONT_DISPLAY,
        format_css, assert_no_forbidden,
    )
except Exception:
    # palette module is shipped alongside every NYXUS app via
    # nyxus_install.sh; if it's missing, fall back to literals so
    # the app still launches.
    WHITE_PURE='#ffffff'; WHITE_OFF='#e8edf5'; GREY_LIGHT='#c8ccd6'
    GREY_MID='#9aa0ad'; GREY_TERTIARY='#6a6e78'
    INK_FADED='#0a0a0a'; INK_BLACK='#000000'
    GLASS_DARK='rgba(8, 12, 20, 0.55)'
    GLASS_DEEPER='rgba(15, 20, 32, 0.72)'
    GLASS_DEEPEST='rgba(5, 7, 12, 0.92)'
    HAIRLINE_WHITE='rgba(255, 255, 255, 0.10)'
    HAIRLINE_INK='rgba(0, 0, 0, 0.45)'
    SHADOW_INK_ACTIVE='rgba(0, 0, 0, 0.65)'
    SHADOW_INK_INACTIVE='rgba(0, 0, 0, 0.20)'
    RADIUS_CARD=14; RADIUS_PILL=12; RADIUS_INPUT=10
    FONT_UI='Inter'; FONT_MONO='JetBrains Mono'; FONT_DISPLAY='Inter Display'
    def format_css(t):
        _d = {
            'WHITE_PURE': WHITE_PURE, 'WHITE_OFF': WHITE_OFF,
            'GREY_LIGHT': GREY_LIGHT, 'GREY_MID': GREY_MID,
            'GREY_TERTIARY': GREY_TERTIARY,
            'INK_FADED': INK_FADED, 'INK_BLACK': INK_BLACK,
            'GLASS_DARK': GLASS_DARK, 'GLASS_DEEPER': GLASS_DEEPER,
            'GLASS_DEEPEST': GLASS_DEEPEST,
            'HAIRLINE_WHITE': HAIRLINE_WHITE, 'HAIRLINE_INK': HAIRLINE_INK,
            'SHADOW_INK_ACTIVE': SHADOW_INK_ACTIVE,
            'SHADOW_INK_INACTIVE': SHADOW_INK_INACTIVE,
            'RADIUS_CARD': RADIUS_CARD, 'RADIUS_PILL': RADIUS_PILL,
            'RADIUS_INPUT': RADIUS_INPUT,
            'FONT_UI': FONT_UI, 'FONT_MONO': FONT_MONO,
            'FONT_DISPLAY': FONT_DISPLAY,
        }
        return t.format_map(_d)
    def assert_no_forbidden(*a, **k): pass
# ─────────────────────────────────────────────────────────────────────


UA = "NYXUS-INTEL/1.0 (research/OSINT)"
TIMEOUT = 20
TOR_LIST_PATH = Path.home() / ".cache" / "nyxus-intel" / "tor_exit_nodes.txt"
TOR_LIST_TTL  = 6 * 3600


def _err(msg): return {"__error__": msg}


def ipinfo_lookup(ip: str, key: Optional[str]) -> Dict[str, Any]:
    headers = {"User-Agent": UA}
    if key: headers["Authorization"] = f"Bearer {key}"
    try:
        r = requests.get(f"https://ipinfo.io/{ip}/json",
                         headers=headers, timeout=TIMEOUT)
    except Exception as e:
        return _err(f"IPinfo: {e}")
    if r.status_code == 401: return _err("IPinfo rejected the API key")
    if r.status_code == 429: return _err("IPinfo rate-limited")
    if r.status_code != 200: return _err(f"IPinfo HTTP {r.status_code}")
    d = r.json()
    return {
        "ip":         d.get("ip"),
        "hostname":   d.get("hostname"),
        "city":       d.get("city"),
        "region":     d.get("region"),
        "country":    d.get("country"),
        "loc":        d.get("loc"),
        "org":        d.get("org"),
        "postal":     d.get("postal"),
        "timezone":   d.get("timezone"),
        "asn":        (d.get("asn") or {}).get("asn") if isinstance(d.get("asn"), dict) else None,
        "anycast":    d.get("anycast"),
        "key_used":   bool(key),
    }


def abuseipdb_lookup(ip: str, key: Optional[str]) -> Dict[str, Any]:
    if not key:
        return _err("set AbuseIPDB API key in Settings")
    try:
        r = requests.get(
            "https://api.abuseipdb.com/api/v2/check",
            params={"ipAddress": ip, "maxAgeInDays": 90, "verbose": ""},
            headers={"Key": key, "Accept": "application/json", "User-Agent": UA},
            timeout=TIMEOUT,
        )
    except Exception as e:
        return _err(f"AbuseIPDB: {e}")
    if r.status_code == 401: return _err("AbuseIPDB rejected the API key")
    if r.status_code == 429: return _err("AbuseIPDB rate-limited")
    if r.status_code != 200: return _err(f"AbuseIPDB HTTP {r.status_code}")
    d = r.json().get("data") or {}
    return {
        "ip":            d.get("ipAddress"),
        "abuse_score":   d.get("abuseConfidenceScore"),
        "country":       d.get("countryCode"),
        "isp":           d.get("isp"),
        "domain":        d.get("domain"),
        "usage_type":    d.get("usageType"),
        "total_reports": d.get("totalReports"),
        "last_reported": d.get("lastReportedAt"),
        "reports": [{"reported_at": rep.get("reportedAt"),
                     "comment":     (rep.get("comment") or "")[:200],
                     "categories":  rep.get("categories")}
                    for rep in (d.get("reports") or [])[:20]],
    }


def shodan_lookup(ip: str, key: Optional[str]) -> Dict[str, Any]:
    if not key:
        return _err("set Shodan API key in Settings")
    try:
        r = requests.get(f"https://api.shodan.io/shodan/host/{ip}",
                         params={"key": key, "minify": "false"},
                         headers={"User-Agent": UA}, timeout=TIMEOUT)
    except Exception as e:
        return _err(f"Shodan: {e}")
    if r.status_code in (401, 403): return _err("Shodan rejected the API key")
    if r.status_code == 404: return {"ip": ip, "found": False}
    if r.status_code != 200: return _err(f"Shodan HTTP {r.status_code}")
    d = r.json()
    return {
        "ip":           d.get("ip_str"),
        "found":        True,
        "ports":        d.get("ports"),
        "hostnames":    d.get("hostnames"),
        "country":      d.get("country_name"),
        "city":         d.get("city"),
        "isp":          d.get("isp"),
        "org":          d.get("org"),
        "os":           d.get("os"),
        "asn":          d.get("asn"),
        "last_update":  d.get("last_update"),
        "vulns":        list((d.get("vulns") or {}).keys()) if isinstance(d.get("vulns"), dict)
                        else d.get("vulns"),
        "services":     [{"port":      s.get("port"),
                          "transport": s.get("transport"),
                          "product":   s.get("product"),
                          "version":   s.get("version"),
                          "banner":    (s.get("data") or "")[:300]}
                         for s in (d.get("data") or [])[:25]],
    }


def virustotal_ip(ip: str, key: Optional[str]) -> Dict[str, Any]:
    if not key:
        return _err("set VirusTotal API key in Settings")
    try:
        r = requests.get(
            f"https://www.virustotal.com/api/v3/ip_addresses/{ip}",
            headers={"x-apikey": key, "User-Agent": UA}, timeout=TIMEOUT,
        )
    except Exception as e:
        return _err(f"VirusTotal: {e}")
    if r.status_code == 401: return _err("VirusTotal rejected the API key")
    if r.status_code == 429: return _err("VirusTotal rate-limited")
    if r.status_code != 200: return _err(f"VirusTotal HTTP {r.status_code}")
    a = (r.json().get("data") or {}).get("attributes") or {}
    return {
        "ip":                  ip,
        "reputation":          a.get("reputation"),
        "country":             a.get("country"),
        "as_owner":            a.get("as_owner"),
        "asn":                 a.get("asn"),
        "network":             a.get("network"),
        "last_analysis_stats": a.get("last_analysis_stats"),
        "tags":                a.get("tags"),
    }


def tor_check(ip: str) -> Dict[str, Any]:
    try:
        TOR_LIST_PATH.parent.mkdir(parents=True, exist_ok=True)
        need_refresh = (
            not TOR_LIST_PATH.exists()
            or (time.time() - TOR_LIST_PATH.stat().st_mtime) > TOR_LIST_TTL
        )
        if need_refresh:
            r = requests.get("https://check.torproject.org/torbulkexitlist",
                             timeout=TIMEOUT, headers={"User-Agent": UA})
            if r.status_code == 200:
                TOR_LIST_PATH.write_text(r.text, "utf-8")
        if not TOR_LIST_PATH.exists():
            return _err("could not fetch Tor exit-node list")
        with open(TOR_LIST_PATH, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip() == ip:
                    return {"ip": ip, "is_tor_exit": True,
                            "list_age_seconds": int(time.time() - TOR_LIST_PATH.stat().st_mtime)}
        return {"ip": ip, "is_tor_exit": False,
                "list_age_seconds": int(time.time() - TOR_LIST_PATH.stat().st_mtime)}
    except Exception as e:
        return _err(f"tor_check: {e}")


def reverse_dns(ip: str) -> Dict[str, Any]:
    try:
        host, aliases, _ = socket.gethostbyaddr(ip)
        return {"ip": ip, "ptr": host, "aliases": aliases}
    except (socket.herror, socket.gaierror) as e:
        return {"ip": ip, "ptr": None, "error": str(e)}


def rdap_ip(ip: str) -> Dict[str, Any]:
    """Public RDAP: rdap.org redirects to the right RIR (ARIN/RIPE/APNIC/...)."""
    try:
        r = requests.get(f"https://rdap.org/ip/{ip}",
                         headers={"User-Agent": UA, "Accept": "application/rdap+json"},
                         timeout=TIMEOUT, allow_redirects=True)
    except Exception as e:
        return _err(f"RDAP: {e}")
    if r.status_code != 200:
        return _err(f"RDAP HTTP {r.status_code}")
    try:
        d = r.json()
    except Exception:
        return _err("RDAP returned non-JSON")
    entities = []
    for e in (d.get("entities") or [])[:6]:
        entities.append({
            "handle": e.get("handle"),
            "roles":  e.get("roles"),
            "name":   _vcard_name(e.get("vcardArray")),
        })
    return {
        "ip":          ip,
        "handle":      d.get("handle"),
        "name":        d.get("name"),
        "type":        d.get("type"),
        "country":     d.get("country"),
        "start":       d.get("startAddress"),
        "end":         d.get("endAddress"),
        "cidr":        [c.get("v4prefix") or c.get("v6prefix")
                        for c in (d.get("cidr0_cidrs") or [])],
        "entities":    entities,
        "remarks":     [(rk.get("title"), (rk.get("description") or [""])[0])
                        for rk in (d.get("remarks") or [])[:3]],
    }


def _vcard_name(vcard):
    if not vcard or len(vcard) < 2: return None
    for entry in vcard[1]:
        if isinstance(entry, list) and len(entry) >= 4 and entry[0] == "fn":
            return entry[3]
    return None
