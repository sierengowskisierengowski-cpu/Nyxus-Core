# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · search_coordinator.py
Auto-detects subject type and dispatches every relevant intel module in
parallel. Returns a structured `findings` dict that downstream pieces
(case_manager, case_viewer, report_generator) consume.

Detection rules:
   email      → contains "@" + "."
   phone      → mostly digits + (), - and . , 7+ digits
   ipv4 / ipv6 → ipaddress parses
   domain     → has "." + valid TLD-ish suffix, no @
   btc        → starts with 1 / 3 (legacy) or "bc1" (bech32)
   eth        → starts with "0x" + 40 hex chars
   n_number   → US FAA aircraft N-number  (e.g. N12345AB)
   image      → file path with .jpg / .jpeg / .png / .tiff / .webp / .bmp
   username   → no spaces, no special chars except _ . -
   person     → free text containing a space
   plain      → fallback

All modules run concurrently. Progress events go through `on_progress`
which the GTK side marshals via GLib.idle_add.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import os
import re
import time
import ipaddress
import concurrent.futures
from typing import Callable, Dict, Any, List, Tuple, Optional

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



EMAIL_RE    = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]{2,}$")
PHONE_RE    = re.compile(r"^[\+\(\)\-\.\s\d]{7,}$")
DOMAIN_RE   = re.compile(r"^(?=.{1,253}$)(?!-)[A-Za-z0-9-]{1,63}(?:\.[A-Za-z0-9-]{1,63})+$")
ETH_RE      = re.compile(r"^0x[a-fA-F0-9]{40}$")
BTC_RE      = re.compile(r"^(bc1[a-z0-9]{6,90}|[13][A-HJ-NP-Za-km-z1-9]{25,39})$")
USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{2,32}$")
N_NUMBER_RE = re.compile(r"^[Nn]\d{1,5}[A-Za-z]{0,2}$")
IMAGE_EXTS  = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp")


def detect_type(raw: str) -> str:
    s = (raw or "").strip()
    if not s: return "plain"
    if os.path.isfile(s) and s.lower().endswith(IMAGE_EXTS): return "image"
    if EMAIL_RE.match(s):    return "email"
    if BTC_RE.match(s):      return "btc"
    if ETH_RE.match(s):      return "eth"
    try:
        ip = ipaddress.ip_address(s)
        return "ipv6" if ip.version == 6 else "ipv4"
    except ValueError:
        pass
    if DOMAIN_RE.match(s):   return "domain"
    if PHONE_RE.match(s) and sum(1 for c in s if c.isdigit()) >= 7: return "phone"
    if N_NUMBER_RE.match(s): return "n_number"
    if " " in s:             return "person"
    if USERNAME_RE.match(s): return "username"
    return "plain"


# ── dispatch table builder ───────────────────────────────────────────────
def _build_dispatch(api_keys: Dict[str, str]
                    ) -> Dict[str, List[Tuple[str, Callable]]]:

    def _imp(mod): return __import__(mod)

    table: Dict[str, List[Tuple[str, Callable]]] = {}

    def add(t, label, fn):
        table.setdefault(t, []).append((label, fn))

    G_KEY  = api_keys.get("google_cse")
    G_CX   = api_keys.get("google_cse_id")
    GH_TOK = api_keys.get("github")

    # ─── EMAIL ──────────────────────────────────────────────────────────
    add("email", "Holehe account discovery",
        lambda s: _imp("email_intel").holehe_lookup(s))
    add("email", "HaveIBeenPwned breaches",
        lambda s: _imp("email_intel").hibp_lookup(s, api_keys.get("hibp")))
    add("email", "DeHashed breaches",
        lambda s: _imp("email_intel").dehashed_lookup(s,
            api_keys.get("dehashed_email"), api_keys.get("dehashed")))
    add("email", "Gravatar profile",
        lambda s: _imp("email_intel").gravatar_lookup(s))
    add("email", "Domain context (MX + reputation)",
        lambda s: _imp("email_intel").domain_context(s, api_keys.get("virustotal")))
    add("email", "Sherlock (email local-part)",
        lambda s: _imp("username_intel").sherlock_lookup(s.split("@")[0]))
    add("email", "GitHub profile (email local-part)",
        lambda s: _imp("username_intel").github_lookup(s.split("@")[0], GH_TOK))
    add("email", "Reddit profile (email local-part)",
        lambda s: _imp("username_intel").reddit_lookup(s.split("@")[0]))
    add("email", "GitHub user search (email)",
        lambda s: _imp("records_intel").github_users_search(s, GH_TOK))
    add("email", "Pastebin dumps (psbdmp.ws)",
        lambda s: _imp("records_intel").pastebin_search(s))
    add("email", "Google News mentions",
        lambda s: _imp("records_intel").google_news_rss(s))
    add("email", "Google CSE web mentions",
        lambda s: _imp("person_intel").google_cse(s, G_KEY, G_CX))

    # ─── USERNAME ───────────────────────────────────────────────────────
    add("username", "Sherlock cross-platform scan",
        lambda s: _imp("username_intel").sherlock_lookup(s))
    add("username", "GitHub profile",
        lambda s: _imp("username_intel").github_lookup(s, GH_TOK))
    add("username", "GitHub user search",
        lambda s: _imp("records_intel").github_users_search(s, GH_TOK))
    add("username", "Reddit profile",
        lambda s: _imp("username_intel").reddit_lookup(s))
    add("username", "Wikipedia",
        lambda s: _imp("records_intel").wikipedia_search(s))
    add("username", "Internet Archive",
        lambda s: _imp("records_intel").archive_org_search(s))
    add("username", "Pastebin dumps (psbdmp.ws)",
        lambda s: _imp("records_intel").pastebin_search(s))
    add("username", "Google News mentions",
        lambda s: _imp("records_intel").google_news_rss(s))
    add("username", "Google CSE web mentions",
        lambda s: _imp("person_intel").google_cse(s, G_KEY, G_CX))

    # ─── PERSON (free text with spaces) ─────────────────────────────────
    def _slug(s: str) -> str: return re.sub(r"\s+", "", s).lower()

    add("person", "Sherlock cross-platform scan",
        lambda s: _imp("username_intel").sherlock_lookup(_slug(s)))
    add("person", "GitHub user search",
        lambda s: _imp("records_intel").github_users_search(s, GH_TOK))
    add("person", "GitHub profile (no-space)",
        lambda s: _imp("username_intel").github_lookup(_slug(s), GH_TOK))
    add("person", "Reddit profile (no-space)",
        lambda s: _imp("username_intel").reddit_lookup(_slug(s)))

    add("person", "FEC campaign contributions",
        lambda s: _imp("records_intel").fec_search(s, api_keys.get("fec")))
    add("person", "OpenSanctions watchlist",
        lambda s: _imp("records_intel").opensanctions_search(s))
    add("person", "SEC EDGAR filings",
        lambda s: _imp("records_intel").sec_edgar_search(s))
    add("person", "USPTO patents (PatentsView)",
        lambda s: _imp("records_intel").uspto_patents(s, api_keys.get("patentsview")))
    add("person", "USPTO trademarks (CSE)",
        lambda s: _imp("records_intel").uspto_trademarks(s, G_KEY, G_CX))
    add("person", "FAA aircraft (owner search)",
        lambda s: _imp("records_intel").faa_owner_search(s))
    add("person", "FCC ULS amateur licensees",
        lambda s: _imp("records_intel").fcc_license_search(s))

    add("person", "Wikipedia",
        lambda s: _imp("records_intel").wikipedia_search(s))
    add("person", "Internet Archive",
        lambda s: _imp("records_intel").archive_org_search(s))
    add("person", "Pastebin dumps (psbdmp.ws)",
        lambda s: _imp("records_intel").pastebin_search(s))
    add("person", "Google News mentions",
        lambda s: _imp("records_intel").google_news_rss(s))
    add("person", "Google Scholar (academic)",
        lambda s: _imp("records_intel").google_scholar(s, G_KEY, G_CX))
    add("person", "Google CSE preset OSINT dorks (15)",
        lambda s: _imp("records_intel").google_dorks(s, G_KEY, G_CX))
    add("person", "Google CSE web mentions",
        lambda s: _imp("person_intel").google_cse(s, G_KEY, G_CX))

    # ─── PLAIN (single short word) ──────────────────────────────────────
    add("plain", "Sherlock cross-platform scan",
        lambda s: _imp("username_intel").sherlock_lookup(s))
    add("plain", "GitHub profile",
        lambda s: _imp("username_intel").github_lookup(s, GH_TOK))
    add("plain", "GitHub user search",
        lambda s: _imp("records_intel").github_users_search(s, GH_TOK))
    add("plain", "Reddit profile",
        lambda s: _imp("username_intel").reddit_lookup(s))
    add("plain", "OpenSanctions watchlist",
        lambda s: _imp("records_intel").opensanctions_search(s))
    add("plain", "SEC EDGAR filings",
        lambda s: _imp("records_intel").sec_edgar_search(s))
    add("plain", "Wikipedia",
        lambda s: _imp("records_intel").wikipedia_search(s))
    add("plain", "Internet Archive",
        lambda s: _imp("records_intel").archive_org_search(s))
    add("plain", "Pastebin dumps (psbdmp.ws)",
        lambda s: _imp("records_intel").pastebin_search(s))
    add("plain", "Google News mentions",
        lambda s: _imp("records_intel").google_news_rss(s))
    add("plain", "Google CSE web mentions",
        lambda s: _imp("person_intel").google_cse(s, G_KEY, G_CX))

    # ─── PHONE ──────────────────────────────────────────────────────────
    add("phone", "FCC carrier (NPA-NXX)",
        lambda s: _imp("records_intel").fcc_phone(s))
    add("phone", "Google News mentions",
        lambda s: _imp("records_intel").google_news_rss(s))
    add("phone", "Google CSE web mentions",
        lambda s: _imp("person_intel").google_cse(s, G_KEY, G_CX))

    # ─── N-NUMBER (FAA aircraft) ────────────────────────────────────────
    add("n_number", "FAA aircraft registry",
        lambda s: _imp("records_intel").faa_aircraft(s))
    add("n_number", "Google News mentions",
        lambda s: _imp("records_intel").google_news_rss(s))
    add("n_number", "Google CSE web mentions",
        lambda s: _imp("person_intel").google_cse(s, G_KEY, G_CX))

    # ─── IP (v4 + v6) ───────────────────────────────────────────────────
    for t in ("ipv4", "ipv6"):
        add(t, "IPinfo geolocation",
            lambda s: _imp("ip_intel").ipinfo_lookup(s, api_keys.get("ipinfo")))
        add(t, "AbuseIPDB reputation",
            lambda s: _imp("ip_intel").abuseipdb_lookup(s, api_keys.get("abuseipdb")))
        add(t, "Shodan exposure",
            lambda s: _imp("ip_intel").shodan_lookup(s, api_keys.get("shodan")))
        add(t, "VirusTotal IP report",
            lambda s: _imp("ip_intel").virustotal_ip(s, api_keys.get("virustotal")))
        add(t, "Tor exit-node check",
            lambda s: _imp("ip_intel").tor_check(s))
        add(t, "Reverse DNS (PTR)",
            lambda s: _imp("ip_intel").reverse_dns(s))
        add(t, "WHOIS (RDAP)",
            lambda s: _imp("ip_intel").rdap_ip(s))

    # ─── DOMAIN ─────────────────────────────────────────────────────────
    add("domain", "WHOIS",
        lambda s: _imp("domain_intel").whois_lookup(s))
    add("domain", "DNS records (A/AAAA/MX/NS/TXT/SOA/CNAME)",
        lambda s: _imp("domain_intel").dns_records(s))
    add("domain", "crt.sh certificate transparency",
        lambda s: _imp("domain_intel").crtsh_lookup(s))
    add("domain", "Wayback Machine snapshots",
        lambda s: _imp("domain_intel").wayback_first_seen(s))
    add("domain", "VirusTotal domain reputation",
        lambda s: _imp("domain_intel").virustotal_domain(s, api_keys.get("virustotal")))
    add("domain", "Shodan domain DNS dump",
        lambda s: _imp("domain_intel").shodan_domain(s, api_keys.get("shodan")))
    add("domain", "Technology fingerprint",
        lambda s: _imp("domain_intel").tech_detect(s))

    # ─── CRYPTO ─────────────────────────────────────────────────────────
    add("btc", "blockchain.info BTC address",
        lambda s: _imp("crypto_intel").btc_address(s))
    add("eth", "Etherscan v2 ETH address",
        lambda s: _imp("crypto_intel").eth_address(s, api_keys.get("etherscan")))

    # ─── IMAGE ──────────────────────────────────────────────────────────
    add("image", "EXIF + GPS + integrity",
        lambda s: _imp("photo_intel").analyse_image(s))

    return table


# ── coordinator ──────────────────────────────────────────────────────────
ProgressFn = Callable[[str, str, Optional[Dict[str, Any]]], None]


def run_search(subject: str, api_keys: Dict[str, str],
               on_progress: ProgressFn,
               max_workers: int = 14) -> Dict[str, Any]:
    """Blocking. Run from a worker thread; on_progress should marshal to the
    GTK main loop with GLib.idle_add."""
    detected = detect_type(subject)
    dispatch = _build_dispatch(api_keys)
    tasks    = list(dispatch.get(detected, []))
    started  = time.time()

    on_progress("start", f"detected: {detected}",
                {"subject": subject, "type": detected, "task_count": len(tasks)})

    findings: Dict[str, Any] = {
        "subject":       subject,
        "detected_type": detected,
        "started_at":    int(started),
        "modules":       {},
        "errors":        {},
        "summary":       "",
    }

    if not tasks:
        on_progress("done", "no modules registered for this subject type",
                    {"elapsed": 0.0})
        return findings

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers,
                                               thread_name_prefix="nyx-intel") as ex:
        futures = {}
        for label, fn in tasks:
            on_progress("task_start", label, None)
            futures[ex.submit(_safe_call, fn, subject)] = label
        for fut in concurrent.futures.as_completed(futures):
            label = futures[fut]
            try:
                result = fut.result()
                if isinstance(result, dict) and result.get("__error__"):
                    findings["errors"][label] = result["__error__"]
                    on_progress("task_error", label, {"error": result["__error__"]})
                else:
                    findings["modules"][label] = result
                    on_progress("task_done", label, {"result": result})
            except Exception as e:
                findings["errors"][label] = repr(e)
                on_progress("task_error", label, {"error": repr(e)})

    findings["finished_at"] = int(time.time())
    findings["elapsed"]     = round(findings["finished_at"] - started, 2)
    findings["summary"]     = _summarise(findings)
    on_progress("done", findings["summary"], {"elapsed": findings["elapsed"]})
    return findings


def _safe_call(fn, arg):
    try:
        return fn(arg)
    except Exception as e:
        return {"__error__": f"{type(e).__name__}: {e}"}


def _summarise(findings: Dict[str, Any]) -> str:
    bits = []
    n_mod = len(findings["modules"])
    n_err = len(findings["errors"])
    bits.append(f"{n_mod} modules returned data")
    if n_err: bits.append(f"{n_err} errors / missing keys")

    for label, data in findings["modules"].items():
        if not isinstance(data, dict): continue
        if data.get("breach_count"):    bits.append(f"{data['breach_count']} breaches")
        if data.get("found_count"):     bits.append(f"{data['found_count']} accounts via {label.split()[0]}")
        if data.get("subdomains_count"):bits.append(f"{data['subdomains_count']} subdomains")
        if data.get("balance_btc") is not None: bits.append(f"BTC balance {data['balance_btc']}")
        if data.get("balance_eth") is not None: bits.append(f"ETH balance {data['balance_eth']}")
        if data.get("agency") and data.get("result_count"):
            bits.append(f"{data['result_count']} {data['agency']} hits")
        if data.get("source") == "GitHub" and data.get("match_count"):
            bits.append(f"{data['match_count']} GitHub users")
        if data.get("exif_gps"): bits.append("EXIF GPS present")
    return " · ".join(bits[:8])
