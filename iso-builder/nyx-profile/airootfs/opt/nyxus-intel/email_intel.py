# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · email_intel.py
Email address investigation. Real APIs only — when a key is missing we
return {"__error__": "set <KEY> in Settings → API Keys"} so the coordinator
can show a clear hint instead of fake data.

  • holehe        — open source, no key, account discovery across 100+ sites
  • HIBP          — paid (key required) — breach list
  • DeHashed      — paid — breach detail (passwords, hashes, sources)
  • Gravatar      — public, no key — md5(email) → profile JSON
  • domain_context — sister-helper — VirusTotal + WHOIS on the email's domain

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import hashlib
import json
import socket
import subprocess
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


UA = ("NYXUS-INTEL/1.0 (research/OSINT; "
      "https://nyxus-core.replit.app)")
TIMEOUT = 20


def _err(msg: str) -> Dict[str, Any]:
    return {"__error__": msg}


# ── holehe ───────────────────────────────────────────────────────────────
def holehe_lookup(email: str) -> Dict[str, Any]:
    """Run holehe as a subprocess (avoids importing its async event loop into
    our thread). Holehe outputs human readable lines — we parse the [+]/[-]
    markers for confirmed accounts."""
    try:
        out = subprocess.run(
            ["holehe", "--only-used", "--no-color", email],
            capture_output=True, text=True, timeout=120,
        )
    except FileNotFoundError:
        return _err("holehe not installed (pip install holehe)")
    except subprocess.TimeoutExpired:
        return _err("holehe timed out after 120s")

    sites = []
    for line in (out.stdout + out.stderr).splitlines():
        line = line.strip()
        if line.startswith("[+]"):
            sites.append({"site": line[3:].strip(), "status": "registered"})
        elif "rate limit" in line.lower():
            sites.append({"site": line, "status": "ratelimited"})

    return {
        "email":  email,
        "found_count": len(sites),
        "sites":  sites,
        "stderr_tail": out.stderr.splitlines()[-3:] if out.stderr else [],
    }


# ── HIBP (Have I Been Pwned) ────────────────────────────────────────────
def hibp_lookup(email: str, api_key: Optional[str]) -> Dict[str, Any]:
    if not api_key:
        return _err("set HIBP API key in Settings → API Keys")
    url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
    headers = {
        "hibp-api-key": api_key,
        "user-agent":   UA,
    }
    params = {"truncateResponse": "false"}
    r = requests.get(url, headers=headers, params=params, timeout=TIMEOUT)
    if r.status_code == 404:
        return {"email": email, "breach_count": 0, "breaches": []}
    if r.status_code == 401:
        return _err("HIBP rejected the API key")
    if r.status_code == 429:
        return _err("HIBP rate-limited (try again in 6s)")
    r.raise_for_status()
    breaches = r.json()
    return {
        "email":        email,
        "breach_count": len(breaches),
        "breaches":     [{"name": b.get("Name"),
                          "domain": b.get("Domain"),
                          "breach_date": b.get("BreachDate"),
                          "pwn_count": b.get("PwnCount"),
                          "data_classes": b.get("DataClasses", []),
                          "verified": b.get("IsVerified"),
                          "description": (b.get("Description") or "")[:400]}
                         for b in breaches],
    }


# ── DeHashed ────────────────────────────────────────────────────────────
def dehashed_lookup(email: str, account_email: Optional[str],
                    api_key: Optional[str]) -> Dict[str, Any]:
    if not api_key or not account_email:
        return _err("set DeHashed account email + API key in Settings")
    url = "https://api.dehashed.com/search"
    r = requests.get(
        url,
        params={"query": f"email:{email}", "size": 100},
        auth=(account_email, api_key),
        headers={"Accept": "application/json", "User-Agent": UA},
        timeout=TIMEOUT,
    )
    if r.status_code == 401:
        return _err("DeHashed rejected the credentials")
    if r.status_code == 429:
        return _err("DeHashed rate-limited")
    r.raise_for_status()
    data = r.json()
    entries = data.get("entries") or []
    return {
        "email":  email,
        "result_count": len(entries),
        "balance": data.get("balance"),
        "entries": [{"db_name":  e.get("database_name"),
                     "username": e.get("username"),
                     "password": "***" if e.get("password") else None,
                     "hashed":   bool(e.get("hashed_password")),
                     "ip":       e.get("ip_address"),
                     "phone":    e.get("phone"),
                     "name":     e.get("name")}
                    for e in entries[:50]],
        "note": "passwords masked client-side; raw values stay encrypted on disk",
    }


# ── Gravatar ────────────────────────────────────────────────────────────
def gravatar_lookup(email: str) -> Dict[str, Any]:
    h = hashlib.md5(email.strip().lower().encode("utf-8")).hexdigest()
    url = f"https://www.gravatar.com/{h}.json"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    if r.status_code == 404:
        return {"email": email, "exists": False, "hash": h}
    if r.status_code != 200:
        return _err(f"Gravatar HTTP {r.status_code}")
    try:
        data = r.json()
    except json.JSONDecodeError:
        return {"email": email, "exists": False, "hash": h}
    profiles = (data or {}).get("entry") or []
    p = profiles[0] if profiles else {}
    return {
        "email":         email,
        "exists":        True,
        "hash":          h,
        "display_name":  p.get("displayName"),
        "preferred_username": p.get("preferredUsername"),
        "profile_url":   p.get("profileUrl"),
        "thumbnail_url": p.get("thumbnailUrl"),
        "accounts":      [{"shortname": a.get("shortname"),
                           "url":       a.get("url")}
                          for a in (p.get("accounts") or [])],
        "name":          p.get("name"),
        "about":         p.get("aboutMe"),
    }


# ── domain context ──────────────────────────────────────────────────────
def domain_context(email: str, vt_key: Optional[str]) -> Dict[str, Any]:
    domain = email.rsplit("@", 1)[-1].strip().lower()
    out: Dict[str, Any] = {"email": email, "domain": domain}

    # MX records
    try:
        import dns.resolver  # python-dnspython
        mx = []
        for r in dns.resolver.resolve(domain, "MX", lifetime=10):
            mx.append({"priority": r.preference, "exchange": str(r.exchange).rstrip(".")})
        out["mx"] = mx
    except Exception as e:
        out["mx_error"] = str(e)

    # Common provider hints
    out["provider_hint"] = _provider_hint(out.get("mx") or [], domain)

    # VirusTotal domain reputation (only if key)
    if vt_key:
        try:
            r = requests.get(
                f"https://www.virustotal.com/api/v3/domains/{domain}",
                headers={"x-apikey": vt_key, "User-Agent": UA},
                timeout=TIMEOUT,
            )
            if r.status_code == 200:
                d = r.json().get("data", {}).get("attributes", {})
                out["vt"] = {
                    "reputation": d.get("reputation"),
                    "categories": d.get("categories"),
                    "last_analysis_stats": d.get("last_analysis_stats"),
                }
            elif r.status_code == 401:
                out["vt_error"] = "VirusTotal rejected the API key"
            else:
                out["vt_error"] = f"VirusTotal HTTP {r.status_code}"
        except Exception as e:
            out["vt_error"] = str(e)
    else:
        out["vt_hint"] = "set VirusTotal API key in Settings for domain reputation"

    return out


def _provider_hint(mx: list, domain: str) -> Optional[str]:
    text = " ".join((m.get("exchange") or "").lower() for m in mx)
    text += " " + domain
    if "google.com" in text or "googlemail" in text: return "Google Workspace / Gmail"
    if "outlook.com" in text or "office365" in text: return "Microsoft 365 / Outlook"
    if "icloud" in text or "apple.com" in text:      return "Apple iCloud"
    if "yahoodns" in text or "yahoo.com" in text:    return "Yahoo Mail"
    if "protonmail" in text or "proton.me" in text:  return "Proton Mail"
    if "zoho" in text:                               return "Zoho Mail"
    if "mailgun" in text or "sendgrid" in text:      return "transactional service (Mailgun/SendGrid)"
    return None
