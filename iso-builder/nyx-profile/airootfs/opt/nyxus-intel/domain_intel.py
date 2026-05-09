# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · domain_intel.py
Domain investigation — WHOIS, DNS, CT-logs, web archive, Shodan DNS,
basic technology fingerprint.

  • python-whois          — no key
  • dnspython             — no key
  • crt.sh                — public, no key
  • Internet Archive CDX  — public, no key
  • VirusTotal v3 domains — key required (free tier OK)
  • Shodan DNS dump       — key required
  • tech_detect           — no key (HTTP headers + body fingerprint)

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import re
from typing import Dict, Any, Optional, List

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
TIMEOUT = 30


def _err(msg): return {"__error__": msg}


def whois_lookup(domain: str) -> Dict[str, Any]:
    try:
        import whois
    except ImportError:
        return _err("python-whois not installed")
    try:
        w = whois.whois(domain)
    except Exception as e:
        return _err(f"WHOIS: {e}")

    def _to_str(v):
        if v is None: return None
        if isinstance(v, list):
            return [_to_str(x) for x in v]
        try:
            return v.isoformat() if hasattr(v, "isoformat") else str(v)
        except Exception:
            return str(v)

    return {
        "domain":          _to_str(w.domain_name) if hasattr(w, "domain_name") else domain,
        "registrar":       _to_str(w.registrar)        if hasattr(w, "registrar") else None,
        "creation_date":   _to_str(w.creation_date)    if hasattr(w, "creation_date") else None,
        "expiration_date": _to_str(w.expiration_date)  if hasattr(w, "expiration_date") else None,
        "updated_date":    _to_str(w.updated_date)     if hasattr(w, "updated_date") else None,
        "name_servers":    _to_str(w.name_servers)     if hasattr(w, "name_servers") else None,
        "status":          _to_str(w.status)           if hasattr(w, "status") else None,
        "emails":          _to_str(w.emails)           if hasattr(w, "emails") else None,
        "country":         _to_str(w.country)          if hasattr(w, "country") else None,
        "org":             _to_str(w.org)              if hasattr(w, "org") else None,
        "raw":             (str(w.text)[:4000] if getattr(w, "text", None) else None),
    }


def dns_records(domain: str) -> Dict[str, Any]:
    try:
        import dns.resolver
    except ImportError:
        return _err("dnspython not installed")
    out: Dict[str, Any] = {"domain": domain}
    for rtype in ("A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME", "CAA"):
        try:
            ans = dns.resolver.resolve(domain, rtype, lifetime=10)
            out[rtype] = [r.to_text() for r in ans]
        except Exception as e:
            out[rtype + "_error"] = str(e)
    return out


def crtsh_lookup(domain: str) -> Dict[str, Any]:
    """certificate-transparency log search — also yields subdomains."""
    try:
        r = requests.get("https://crt.sh/", params={"q": f"%.{domain}", "output": "json"},
                         timeout=TIMEOUT, headers={"User-Agent": UA})
    except Exception as e:
        return _err(f"crt.sh: {e}")
    if r.status_code != 200:
        return _err(f"crt.sh HTTP {r.status_code}")
    try:
        rows = r.json()
    except Exception:
        return _err("crt.sh returned non-JSON")
    subs = set()
    certs: List[Dict[str, Any]] = []
    for row in rows[:500]:
        for n in (row.get("name_value") or "").splitlines():
            n = n.strip().lower()
            if n.endswith(domain.lower()):
                subs.add(n)
        certs.append({
            "issuer":     row.get("issuer_name"),
            "not_before": row.get("not_before"),
            "not_after":  row.get("not_after"),
            "serial":     row.get("serial_number"),
            "id":         row.get("id"),
        })
    subs = sorted(subs)
    return {
        "domain":            domain,
        "subdomains_count":  len(subs),
        "subdomains":        subs[:500],
        "cert_count":        len(certs),
        "certs":             certs[:200],
    }


def wayback_first_seen(domain: str) -> Dict[str, Any]:
    try:
        r = requests.get(
            "https://web.archive.org/cdx/search/cdx",
            params={"url": domain, "limit": "5", "from": "1996", "output": "json"},
            timeout=TIMEOUT, headers={"User-Agent": UA},
        )
    except Exception as e:
        return _err(f"Wayback: {e}")
    if r.status_code != 200:
        return _err(f"Wayback HTTP {r.status_code}")
    try:
        data = r.json()
    except Exception:
        return _err("Wayback returned non-JSON")
    if not data or len(data) < 2:
        return {"domain": domain, "first_seen": None, "snapshots": 0,
                "examples": []}
    rows = data[1:]
    first_ts = rows[0][1] if rows[0] else None

    pages = 0
    try:
        rc = requests.get(
            "https://web.archive.org/cdx/search/cdx",
            params={"url": domain, "showNumPages": "true"},
            timeout=TIMEOUT, headers={"User-Agent": UA})
        if rc.status_code == 200: pages = int(rc.text.strip())
    except Exception:
        pass

    return {
        "domain":     domain,
        "first_seen": first_ts,
        "snapshots":  pages,
        "examples":   [{"timestamp": r[1],
                        "url":       f"https://web.archive.org/web/{r[1]}/{r[2]}"}
                       for r in rows],
    }


def virustotal_domain(domain: str, key: Optional[str]) -> Dict[str, Any]:
    if not key:
        return _err("set VirusTotal API key in Settings")
    try:
        r = requests.get(
            f"https://www.virustotal.com/api/v3/domains/{domain}",
            headers={"x-apikey": key, "User-Agent": UA},
            timeout=TIMEOUT,
        )
    except Exception as e:
        return _err(f"VirusTotal: {e}")
    if r.status_code == 401: return _err("VirusTotal rejected the API key")
    if r.status_code == 429: return _err("VirusTotal rate-limited")
    if r.status_code == 404: return {"domain": domain, "found": False}
    if r.status_code != 200: return _err(f"VirusTotal HTTP {r.status_code}")
    a = (r.json().get("data") or {}).get("attributes") or {}
    return {
        "domain":              domain,
        "reputation":          a.get("reputation"),
        "categories":          a.get("categories"),
        "last_analysis_stats": a.get("last_analysis_stats"),
        "creation_date":       a.get("creation_date"),
        "registrar":           a.get("registrar"),
        "tags":                a.get("tags"),
    }


def shodan_domain(domain: str, key: Optional[str]) -> Dict[str, Any]:
    """Shodan DNS dump for a domain — subdomains + record history."""
    if not key:
        return _err("set Shodan API key in Settings")
    try:
        r = requests.get(f"https://api.shodan.io/dns/domain/{domain}",
                         params={"key": key},
                         headers={"User-Agent": UA}, timeout=TIMEOUT)
    except Exception as e:
        return _err(f"Shodan domain: {e}")
    if r.status_code in (401, 403): return _err("Shodan rejected the API key")
    if r.status_code == 404: return {"domain": domain, "found": False}
    if r.status_code != 200: return _err(f"Shodan domain HTTP {r.status_code}")
    d = r.json()
    return {
        "domain":      d.get("domain"),
        "tags":        d.get("tags"),
        "subdomains":  d.get("subdomains") or [],
        "subdomain_count": len(d.get("subdomains") or []),
        "data":        [{"subdomain": rec.get("subdomain"),
                         "type":      rec.get("type"),
                         "value":     rec.get("value"),
                         "last_seen": rec.get("last_seen"),
                         "ports":     rec.get("ports")}
                        for rec in (d.get("data") or [])[:100]],
    }


# ── Tech fingerprinting (header + body sniff) ────────────────────────────
TECH_FPS = [
    ("WordPress",     "b", re.compile(r"/wp-content/|/wp-includes/", re.I)),
    ("Drupal",        "b", re.compile(r"sites/default/files|drupal-settings-json", re.I)),
    ("Joomla",        "b", re.compile(r"/components/com_|joomla", re.I)),
    ("Shopify",       "h", "X-Shopify-Stage"),
    ("Squarespace",   "h", "X-Served-By-Squarespace"),
    ("Wix",           "h", "X-Wix-Request-Id"),
    ("Webflow",       "h", "Webflow"),
    ("Cloudflare",    "h", "CF-RAY"),
    ("Akamai",        "h", "X-Akamai-Transformed"),
    ("Fastly",        "h", "Fastly-Debug-Digest"),
    ("Vercel",        "h", "X-Vercel-Id"),
    ("Netlify",       "h", "X-Nf-Request-Id"),
    ("AWS CloudFront","h", "X-Amz-Cf-Id"),
    ("Google Cloud",  "h", "X-Cloud-Trace-Context"),
    ("React",         "b", re.compile(r"__NEXT_DATA__|data-reactroot|react-dom", re.I)),
    ("Next.js",       "b", re.compile(r"__NEXT_DATA__", re.I)),
    ("Vue",           "b", re.compile(r"data-v-app|__vue__", re.I)),
    ("Angular",       "b", re.compile(r"ng-version|ng-app", re.I)),
    ("Svelte/Kit",    "b", re.compile(r"__sveltekit_", re.I)),
    ("jQuery",        "b", re.compile(r"jquery(?:\.min)?\.js", re.I)),
    ("Bootstrap",     "b", re.compile(r"bootstrap(?:\.min)?\.css", re.I)),
    ("Tailwind",      "b", re.compile(r"tailwind", re.I)),
    ("Stripe",        "b", re.compile(r"js\.stripe\.com", re.I)),
    ("Google Analytics","b", re.compile(r"google-analytics\.com|googletagmanager\.com", re.I)),
    ("Facebook Pixel","b", re.compile(r"connect\.facebook\.net/en_US/fbevents\.js", re.I)),
    ("HubSpot",       "b", re.compile(r"hs-scripts\.com|hubspot\.com", re.I)),
]


def tech_detect(domain: str) -> Dict[str, Any]:
    try:
        url = "https://" + domain.strip()
        r = requests.get(url, timeout=TIMEOUT,
                         headers={"User-Agent": UA},
                         allow_redirects=True, verify=True)
    except requests.exceptions.SSLError:
        try:
            url = "http://" + domain.strip()
            r = requests.get(url, timeout=TIMEOUT,
                             headers={"User-Agent": UA},
                             allow_redirects=True)
        except Exception as e:
            return _err(f"tech_detect HTTP: {e}")
    except Exception as e:
        return _err(f"tech_detect: {e}")

    body_s = r.text[:200_000] if r.text else ""
    found: List[str] = []
    for label, kind, needle in TECH_FPS:
        if kind == "h":
            if any(needle.lower() == k.lower() or needle.lower() in k.lower()
                   for k in r.headers):
                found.append(label)
        else:
            if needle.search(body_s):
                found.append(label)

    server = r.headers.get("Server")
    powered = r.headers.get("X-Powered-By")
    title_m = re.search(r"<title[^>]*>(.*?)</title>", body_s, re.I | re.DOTALL)

    return {
        "domain":          domain,
        "url":             r.url,
        "status":          r.status_code,
        "title":           (title_m.group(1).strip()[:200] if title_m else None),
        "server_header":   server,
        "powered_by":      powered,
        "technologies":    sorted(set(found)),
        "headers_seen":    {k: v for k, v in list(r.headers.items())[:30]},
        "redirect_chain":  [resp.url for resp in r.history] + [r.url],
    }
