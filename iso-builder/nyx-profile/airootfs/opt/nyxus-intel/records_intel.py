# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · records_intel.py
Real public-records and open-data APIs.

Every function returns either a structured dict with the data or
{"__error__": "human readable reason"} on failure / missing key.

Keyless public APIs:
    fcc_phone           opendata.fcc.gov NPA-NXX  (phone carrier lookup)
    fcc_license_search  opendata.fcc.gov ULS amateur radio (licensee by name)
    opensanctions_search api.opensanctions.org    (sanctions / PEP screening)
    sec_edgar_search    efts.sec.gov              (full-text filings search)
    faa_aircraft        registry.faa.gov          (N-number HTML scrape)
    faa_owner_search    registry.faa.gov          (owner-name HTML scrape)
    wikipedia_search    en.wikipedia.org/w/api    (opensearch + summary)
    archive_org_search  archive.org/advancedsearch (Internet Archive items)
    github_users_search api.github.com            (optional token)
    pastebin_search     psbdmp.ws/api/search      (Pastebin dump search)
    google_news_rss     news.google.com/rss/search (news mentions)

Keyed public APIs:
    fec_search          api.open.fec.gov          (free key, instant)
    uspto_patents       search.patentsview.org    (free key, registration)
    google_dorks        Google CSE (15 preset OSINT dorks)
    google_scholar      Google CSE restricted to scholar.google.com

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import re
import html
from typing import Dict, Any, Optional, List
from urllib.parse import quote

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
TIMEOUT = 25


def _err(msg): return {"__error__": msg}
def _digits(s): return "".join(c for c in s if c.isdigit())


# ── FCC phone NPA-NXX carrier lookup ─────────────────────────────────────
def fcc_phone(phone: str) -> Dict[str, Any]:
    d = _digits(phone)
    if len(d) == 11 and d.startswith("1"): d = d[1:]
    if len(d) != 10:
        return _err("expected a 10-digit US number")
    npa, nxx = d[:3], d[3:6]
    try:
        r = requests.get("https://opendata.fcc.gov/resource/n4w7-a8b8.json",
                         params={"npa": npa, "nxx": nxx},
                         timeout=TIMEOUT, headers={"User-Agent": UA})
    except Exception as e:
        return _err(f"FCC: {e}")
    if r.status_code != 200:
        return _err(f"FCC HTTP {r.status_code}")
    rows = r.json() or []
    return {
        "agency":     "FCC",
        "phone":      phone,
        "npa":        npa,
        "nxx":        nxx,
        "row_count":  len(rows),
        "rows":       rows[:25],
    }


# ── FCC ULS amateur-radio licensee search by name ────────────────────────
def fcc_license_search(name: str) -> Dict[str, Any]:
    """Searches the FCC Universal Licensing System amateur-radio dataset
    (the only ULS dataset with a free public Socrata endpoint and a name
    column). Returns licensee name, callsign, address, FRN."""
    n = (name or "").strip()
    if not n:
        return _err("empty name")
    safe = n.upper().replace("'", "''")
    try:
        r = requests.get(
            "https://opendata.fcc.gov/resource/2sdb-cm5f.json",
            params={"$where": f"upper(licensee_name) like '%{safe}%'",
                    "$limit": 25},
            timeout=TIMEOUT, headers={"User-Agent": UA},
        )
    except Exception as e:
        return _err(f"FCC ULS: {e}")
    if r.status_code != 200:
        return _err(f"FCC ULS HTTP {r.status_code}")
    rows = r.json() or []
    out = []
    for row in rows[:25]:
        out.append({
            "licensee":     row.get("licensee_name"),
            "callsign":     row.get("callsign"),
            "frn":          row.get("frn"),
            "address":      row.get("street_address"),
            "city":         row.get("city"),
            "state":        row.get("state"),
            "zip":          row.get("zip_code"),
            "license_class":row.get("operator_class"),
            "grant_date":   row.get("grant_date"),
            "expiration":   row.get("expired_date"),
        })
    return {
        "agency":       "FCC ULS (amateur)",
        "query":        name,
        "result_count": len(out),
        "results":      out,
    }


# ── FEC contributions ────────────────────────────────────────────────────
def fec_search(name: str, key: Optional[str]) -> Dict[str, Any]:
    if not key:
        return _err("set FEC API key in Settings (free at api.data.gov)")
    try:
        r = requests.get(
            "https://api.open.fec.gov/v1/schedules/schedule_a/",
            params={"contributor_name": name, "api_key": key,
                    "per_page": 30,
                    "sort": "-contribution_receipt_date"},
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=TIMEOUT,
        )
    except Exception as e:
        return _err(f"FEC: {e}")
    if r.status_code in (401, 403):
        return _err("FEC rejected the API key")
    if r.status_code != 200:
        return _err(f"FEC HTTP {r.status_code}")
    data = r.json()
    rows = []
    for row in data.get("results") or []:
        rows.append({
            "contributor": row.get("contributor_name"),
            "city":        row.get("contributor_city"),
            "state":       row.get("contributor_state"),
            "employer":    row.get("contributor_employer"),
            "occupation":  row.get("contributor_occupation"),
            "amount":      row.get("contribution_receipt_amount"),
            "date":        row.get("contribution_receipt_date"),
            "committee":   (row.get("committee") or {}).get("name"),
            "memo":        row.get("memo_text"),
        })
    return {
        "agency":       "FEC",
        "query":        name,
        "total":        (data.get("pagination") or {}).get("count"),
        "result_count": len(rows),
        "results":      rows,
    }


# ── OpenSanctions ────────────────────────────────────────────────────────
def opensanctions_search(name: str) -> Dict[str, Any]:
    try:
        r = requests.get(
            "https://api.opensanctions.org/search/default",
            params={"q": name, "limit": 25},
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=TIMEOUT,
        )
    except Exception as e:
        return _err(f"OpenSanctions: {e}")
    if r.status_code == 429:
        return _err("OpenSanctions rate-limited")
    if r.status_code != 200:
        return _err(f"OpenSanctions HTTP {r.status_code}")
    d = r.json()
    rows = []
    for r0 in d.get("results") or []:
        props = r0.get("properties") or {}
        rows.append({
            "id":          r0.get("id"),
            "schema":      r0.get("schema"),
            "caption":     r0.get("caption"),
            "score":       r0.get("score"),
            "datasets":    r0.get("datasets"),
            "topics":      props.get("topics"),
            "countries":   props.get("country"),
            "birth_date":  props.get("birthDate"),
            "url":         "https://www.opensanctions.org/entities/" + (r0.get("id") or ""),
        })
    total = d.get("total")
    if isinstance(total, dict):
        total = total.get("value")
    return {
        "agency":       "OpenSanctions",
        "query":        name,
        "total":        total,
        "result_count": len(rows),
        "results":      rows,
    }


# ── SEC EDGAR full-text filings search ───────────────────────────────────
def sec_edgar_search(name: str) -> Dict[str, Any]:
    """SEC EDGAR Full-Text Search API. Public, no key, requires UA."""
    n = (name or "").strip().strip('"')
    if not n:
        return _err("empty query")
    q = f'"{n}"' if " " in n else n
    try:
        r = requests.get(
            "https://efts.sec.gov/LATEST/search-index",
            params={"q": q, "forms": ""},
            headers={"User-Agent": UA, "Accept": "application/json"},
            timeout=TIMEOUT,
        )
    except Exception as e:
        return _err(f"SEC EDGAR: {e}")
    if r.status_code != 200:
        return _err(f"SEC EDGAR HTTP {r.status_code}")
    try:
        d = r.json()
    except Exception:
        return _err("SEC EDGAR returned non-JSON")
    hits = (d.get("hits") or {}).get("hits") or []
    rows = []
    for h in hits[:30]:
        s = h.get("_source") or {}
        adsh = (h.get("_id") or "").split(":")[0]
        cik0 = (s.get("ciks") or [""])[0]
        rows.append({
            "form":      s.get("form"),
            "date":      s.get("file_date"),
            "ciks":      s.get("ciks"),
            "names":     s.get("display_names"),
            "accession": adsh,
            "url":       (f"https://www.sec.gov/cgi-bin/browse-edgar?"
                          f"action=getcompany&CIK={cik0}&type={s.get('form','')}"
                          if cik0 else None),
        })
    total_obj = (d.get("hits") or {}).get("total") or {}
    return {
        "agency":       "SEC EDGAR",
        "query":        name,
        "total":        total_obj.get("value") if isinstance(total_obj, dict) else total_obj,
        "result_count": len(rows),
        "filings":      rows,
    }


# ── USPTO PatentsView (inventor name) ────────────────────────────────────
def uspto_patents(name: str, key: Optional[str]) -> Dict[str, Any]:
    """PatentsView API requires a free X-Api-Key (patentsview.org/api/keyrequest)."""
    if not key:
        return _err("set PatentsView API key in Settings "
                    "(free at patentsview.org/api/keyrequest)")
    parts = name.split()
    if len(parts) >= 2:
        q = {"_and": [{"_text_phrase": {"inventors.inventor_name_first": parts[0]}},
                       {"_text_phrase": {"inventors.inventor_name_last":  parts[-1]}}]}
    else:
        q = {"_text_phrase": {"inventors.inventor_name_last": name}}
    body = {
        "q": q,
        "f": ["patent_id", "patent_title", "patent_date", "inventors"],
        "o": {"size": 25},
    }
    try:
        r = requests.post("https://search.patentsview.org/api/v1/patent/",
                          json=body,
                          headers={"X-Api-Key": key, "User-Agent": UA,
                                   "Accept": "application/json"},
                          timeout=TIMEOUT)
    except Exception as e:
        return _err(f"PatentsView: {e}")
    if r.status_code in (401, 403):
        return _err("PatentsView rejected the API key")
    if r.status_code != 200:
        return _err(f"PatentsView HTTP {r.status_code}")
    d = r.json()
    rows = []
    for p in (d.get("patents") or [])[:30]:
        invs = ", ".join(
            f"{(i.get('inventor_name_first') or '').strip()} "
            f"{(i.get('inventor_name_last') or '').strip()}".strip()
            for i in (p.get("inventors") or [])[:5])
        rows.append({
            "patent_id": p.get("patent_id"),
            "title":     p.get("patent_title"),
            "date":      p.get("patent_date"),
            "inventors": invs,
            "url":       f"https://patents.google.com/patent/US{p.get('patent_id')}",
        })
    return {
        "agency":       "USPTO PatentsView",
        "query":        name,
        "total":        d.get("total_hits"),
        "result_count": len(rows),
        "patents":      rows,
    }


# ── USPTO trademark search by owner (Google CSE pivot) ───────────────────
def uspto_trademarks(name: str, cse_key: Optional[str], cx: Optional[str]) -> Dict[str, Any]:
    """USPTO has no public JSON owner-name API. We pivot through Google CSE
    restricted to tsdr.uspto.gov / tmsearch.uspto.gov."""
    if not cse_key or not cx:
        return _err("set Google CSE key + engine id in Settings (used to search USPTO TM records)")
    q = f'"{name}" site:tsdr.uspto.gov OR site:tmsearch.uspto.gov'
    try:
        r = requests.get("https://www.googleapis.com/customsearch/v1",
                         params={"key": cse_key, "cx": cx, "q": q, "num": 10},
                         headers={"User-Agent": UA}, timeout=TIMEOUT)
    except Exception as e:
        return _err(f"USPTO TM (CSE): {e}")
    if r.status_code == 403:
        return _err("Google CSE quota exhausted or key invalid")
    if r.status_code != 200:
        return _err(f"USPTO TM (CSE) HTTP {r.status_code}")
    items = r.json().get("items") or []
    return {
        "agency":       "USPTO Trademarks (via Google CSE)",
        "query":        name,
        "result_count": len(items),
        "results":      [{"title": it.get("title"), "url": it.get("link"),
                          "snippet": it.get("snippet")} for it in items],
    }


# ── FAA aircraft registry ────────────────────────────────────────────────
N_NUMBER_RE = re.compile(r"^[Nn]?(\d{1,5}[A-Za-z]{0,2})$")


def is_n_number(s: str) -> bool:
    return bool(N_NUMBER_RE.match((s or "").strip()))


def faa_aircraft(n_number: str) -> Dict[str, Any]:
    s = (n_number or "").strip().upper()
    m = N_NUMBER_RE.match(s)
    if not m:
        return _err("not a valid US N-number (e.g. N12345)")
    n = "N" + m.group(1)
    try:
        r = requests.get(
            "https://registry.faa.gov/aircraftinquiry/Search/NNumberResult",
            params={"nNumberTxt": n[1:]},
            headers={"User-Agent": UA, "Accept": "text/html"},
            timeout=TIMEOUT,
        )
    except Exception as e:
        return _err(f"FAA: {e}")
    if r.status_code != 200:
        return _err(f"FAA HTTP {r.status_code}")
    return {"agency": "FAA Aircraft Registry", "n_number": n, **_parse_faa_html(r.text, n)}


def _parse_faa_html(h: str, n: str) -> Dict[str, Any]:
    """Best-effort pull of label/value pairs from the FAA result table."""
    def grab(label):
        for pat in (
            rf"data-label=\"{re.escape(label)}\"[^>]*>\s*<span[^>]*>([^<]+)<",
            rf"<td[^>]*>\s*{re.escape(label)}\s*</td>\s*<td[^>]*>\s*([^<]+)<",
            rf"<th[^>]*>\s*{re.escape(label)}\s*</th>\s*<td[^>]*>\s*([^<]+)<",
        ):
            m = re.search(pat, h, re.IGNORECASE | re.DOTALL)
            if m:
                return html.unescape(m.group(1)).strip()
        return None

    aircraft = {
        "serial":         grab("Serial Number"),
        "manufacturer":   grab("Manufacturer Name") or grab("Manufacturer"),
        "model":          grab("Model"),
        "year_mfr":       grab("Year Manufacturer") or grab("Year"),
        "type_aircraft":  grab("Type Aircraft"),
        "owner":          grab("Name") or grab("Owner"),
        "address":        grab("Street") or grab("Street Address"),
        "city":           grab("City"),
        "state":          grab("State"),
        "country":        grab("Country"),
        "zip":            grab("Zip Code"),
        "status":         grab("Status"),
        "cert_issue":     grab("Cert Issue Date"),
        "engine":         grab("Engine Manufacturer") or grab("Engine"),
        "engine_model":   grab("Engine Model"),
        "engine_count":   grab("Number of Engines"),
        "weight":         grab("A/W Date") or grab("Aircraft Weight"),
    }
    found = any(v for v in aircraft.values())
    return {
        "found":    found,
        "aircraft": aircraft if found else None,
        "url":      f"https://registry.faa.gov/aircraftinquiry/Search/NNumberResult?nNumberTxt={n[1:]}",
    }


def faa_owner_search(name: str) -> Dict[str, Any]:
    """FAA owner-name aircraft search. Posts the registry's name form and
    parses returned aircraft rows."""
    if not name or len(name.strip()) < 2:
        return _err("name required")
    try:
        r = requests.post(
            "https://registry.faa.gov/aircraftinquiry/Search/NameResult",
            data={"nameTxt": name.strip(),
                  "sortOption": "1", "PageNo": "1"},
            headers={"User-Agent": UA, "Accept": "text/html",
                     "Content-Type": "application/x-www-form-urlencoded"},
            timeout=TIMEOUT,
        )
    except Exception as e:
        return _err(f"FAA owner: {e}")
    if r.status_code != 200:
        return _err(f"FAA owner HTTP {r.status_code}")
    h = r.text
    aircraft = []
    for m in re.finditer(
            r"<tr[^>]*>\s*<td[^>]*>\s*<a[^>]*nNumberTxt=([^\"&]+)[^>]*>([^<]+)</a>"
            r".*?</tr>",
            h, re.IGNORECASE | re.DOTALL):
        block = m.group(0)
        cells = [html.unescape(c.strip()) for c in
                 re.findall(r"<td[^>]*>(.*?)</td>", block, re.IGNORECASE | re.DOTALL)]
        cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
        aircraft.append({
            "n_number":     "N" + m.group(1),
            "serial":       cells[1] if len(cells) > 1 else None,
            "manufacturer": cells[2] if len(cells) > 2 else None,
            "model":        cells[3] if len(cells) > 3 else None,
            "year":         cells[4] if len(cells) > 4 else None,
            "owner":        cells[5] if len(cells) > 5 else None,
            "url":          f"https://registry.faa.gov/aircraftinquiry/Search/NNumberResult?nNumberTxt={m.group(1)}",
        })
    return {
        "agency":       "FAA Aircraft Registry (owner search)",
        "query":        name,
        "result_count": len(aircraft),
        "results":      aircraft[:25],
    }


# ── Wikipedia opensearch + summary ───────────────────────────────────────
def wikipedia_search(query: str) -> Dict[str, Any]:
    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action": "opensearch", "search": query,
                    "limit": 10, "format": "json"},
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        )
    except Exception as e:
        return _err(f"Wikipedia: {e}")
    if r.status_code != 200:
        return _err(f"Wikipedia HTTP {r.status_code}")
    arr = r.json()
    if not isinstance(arr, list) or len(arr) < 4:
        return {"source": "Wikipedia", "query": query, "result_count": 0, "pages": []}
    titles, descriptions, urls = arr[1] or [], arr[2] or [], arr[3] or []
    pages = []
    for i, t in enumerate(titles[:10]):
        pages.append({
            "title":       t,
            "description": descriptions[i] if i < len(descriptions) else None,
            "url":         urls[i] if i < len(urls) else None,
        })
    summary = None
    if pages:
        try:
            sr = requests.get(
                "https://en.wikipedia.org/api/rest_v1/page/summary/" +
                quote(pages[0]["title"], safe=""),
                headers={"User-Agent": UA}, timeout=TIMEOUT)
            if sr.status_code == 200:
                sd = sr.json()
                summary = {
                    "title":       sd.get("title"),
                    "extract":     sd.get("extract"),
                    "thumbnail":   (sd.get("thumbnail") or {}).get("source"),
                    "description": sd.get("description"),
                    "url":         (sd.get("content_urls") or {}).get("desktop", {}).get("page"),
                }
        except Exception:
            pass
    return {
        "source":       "Wikipedia",
        "query":        query,
        "result_count": len(pages),
        "pages":        pages,
        "summary":      summary,
    }


# ── Internet Archive search ──────────────────────────────────────────────
def archive_org_search(query: str) -> Dict[str, Any]:
    try:
        r = requests.get(
            "https://archive.org/advancedsearch.php",
            params={"q": query,
                    "fl[]": ["identifier", "title", "date",
                             "mediatype", "creator", "subject"],
                    "rows": 25, "page": 1, "output": "json"},
            headers={"User-Agent": UA}, timeout=TIMEOUT,
        )
    except Exception as e:
        return _err(f"Internet Archive: {e}")
    if r.status_code != 200:
        return _err(f"Internet Archive HTTP {r.status_code}")
    try:
        d = r.json()
    except Exception:
        return _err("Internet Archive returned non-JSON")
    docs = ((d.get("response") or {}).get("docs")) or []
    items = []
    for doc in docs[:25]:
        items.append({
            "identifier": doc.get("identifier"),
            "title":      doc.get("title"),
            "date":       doc.get("date"),
            "mediatype":  doc.get("mediatype"),
            "creator":    doc.get("creator"),
            "url":        "https://archive.org/details/" + (doc.get("identifier") or ""),
        })
    return {
        "source":       "Internet Archive",
        "query":        query,
        "total":        ((d.get("response") or {}).get("numFound")) or 0,
        "result_count": len(items),
        "items":        items,
    }


# ── GitHub user search ───────────────────────────────────────────────────
def github_users_search(query: str, token: Optional[str]) -> Dict[str, Any]:
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    try:
        r = requests.get("https://api.github.com/search/users",
                         params={"q": query, "per_page": 20},
                         headers=headers, timeout=TIMEOUT)
    except Exception as e:
        return _err(f"GitHub: {e}")
    if r.status_code == 403:
        return _err("GitHub rate-limit hit (set token in Settings)")
    if r.status_code == 422:
        return _err("GitHub: query rejected (check name format)")
    if r.status_code != 200:
        return _err(f"GitHub HTTP {r.status_code}")
    d = r.json()
    matches = []
    for u in (d.get("items") or [])[:20]:
        matches.append({
            "login":    u.get("login"),
            "id":       u.get("id"),
            "type":     u.get("type"),
            "html_url": u.get("html_url"),
            "avatar":   u.get("avatar_url"),
            "score":    u.get("score"),
        })
    return {
        "source":      "GitHub",
        "query":       query,
        "total":       d.get("total_count"),
        "match_count": len(matches),
        "matches":     matches,
    }


# ── Pastebin search via psbdmp.ws ────────────────────────────────────────
def pastebin_search(query: str) -> Dict[str, Any]:
    """psbdmp.ws indexes Pastebin dumps. Free, no key."""
    q = (query or "").strip()
    if not q:
        return _err("empty query")
    try:
        r = requests.get(f"https://psbdmp.ws/api/search/{quote(q)}",
                         headers={"User-Agent": UA, "Accept": "application/json"},
                         timeout=TIMEOUT)
    except Exception as e:
        return _err(f"psbdmp: {e}")
    if r.status_code == 404:
        return {"source": "psbdmp.ws (Pastebin)", "query": q,
                "result_count": 0, "pastes": []}
    if r.status_code != 200:
        return _err(f"psbdmp HTTP {r.status_code}")
    try:
        d = r.json()
    except Exception:
        return _err("psbdmp returned non-JSON (service may be down)")
    data = d.get("data") if isinstance(d, dict) else d
    if not isinstance(data, list): data = []
    pastes = []
    for row in data[:50]:
        pid = row.get("id") if isinstance(row, dict) else None
        pastes.append({
            "id":   pid,
            "date": row.get("date") if isinstance(row, dict) else None,
            "tags": row.get("tags") if isinstance(row, dict) else None,
            "url":  f"https://pastebin.com/{pid}" if pid else None,
        })
    return {
        "source":       "psbdmp.ws (Pastebin)",
        "query":        q,
        "count":        d.get("count") if isinstance(d, dict) else len(pastes),
        "result_count": len(pastes),
        "pastes":       pastes,
    }


# ── Google News RSS ──────────────────────────────────────────────────────
def google_news_rss(query: str) -> Dict[str, Any]:
    q = (query or "").strip()
    if not q: return _err("empty query")
    try:
        r = requests.get("https://news.google.com/rss/search",
                         params={"q": q, "hl": "en-US",
                                 "gl": "US", "ceid": "US:en"},
                         headers={"User-Agent": UA},
                         timeout=TIMEOUT)
    except Exception as e:
        return _err(f"Google News: {e}")
    if r.status_code != 200:
        return _err(f"Google News HTTP {r.status_code}")
    items = []
    for m in re.finditer(
            r"<item>\s*<title>(.*?)</title>\s*<link>(.*?)</link>"
            r"\s*<guid[^>]*>.*?</guid>\s*<pubDate>(.*?)</pubDate>"
            r"\s*<description>(.*?)</description>"
            r"(?:\s*<source[^>]*>(.*?)</source>)?",
            r.text, re.DOTALL):
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip()
        link  = html.unescape(m.group(2)).strip()
        date  = m.group(3).strip()
        desc  = html.unescape(re.sub(r"<[^>]+>", "", m.group(4))).strip()
        src   = (m.group(5) or "").strip()
        items.append({"title": title, "url": link, "date": date,
                      "snippet": desc[:300], "source": src})
        if len(items) >= 30: break
    return {
        "source":       "Google News",
        "query":        q,
        "result_count": len(items),
        "results":      items,
    }


# ── Google CSE preset OSINT dorks (15 patterns) ──────────────────────────
DORKS = [
    ('"{q}" filetype:pdf',                            "PDF documents mentioning name"),
    ('"{q}" filetype:doc OR filetype:docx',           "Word documents"),
    ('"{q}" filetype:xls OR filetype:xlsx',           "Spreadsheets"),
    ('"{q}" intext:"resume" OR intext:"curriculum vitae"', "Resumes / CVs"),
    ('"{q}" site:linkedin.com/in',                    "LinkedIn profiles"),
    ('"{q}" site:facebook.com',                       "Facebook profiles"),
    ('"{q}" site:twitter.com OR site:x.com',          "Twitter / X mentions"),
    ('"{q}" site:instagram.com',                      "Instagram profiles"),
    ('"{q}" site:github.com',                         "GitHub mentions"),
    ('"{q}" site:reddit.com',                         "Reddit mentions"),
    ('"{q}" "phone" OR "mobile" OR "tel"',            "Contact info leaks"),
    ('"{q}" "email" OR "contact"',                    "Email leaks"),
    ('"{q}" "address" OR "lives in" OR "residence"',  "Address mentions"),
    ('"{q}" "arrested" OR "charged" OR "convicted" OR "lawsuit"', "Legal mentions"),
    ('"{q}" inurl:profile OR inurl:about OR inurl:bio', "Profile pages"),
]


def google_dorks(query: str, cse_key: Optional[str], cx: Optional[str]) -> Dict[str, Any]:
    """Runs the 15 preset dorks via Google CSE. Each dork costs one CSE call
    (CSE free tier is 100/day so a single person search uses 15)."""
    if not cse_key or not cx:
        return _err("set Google CSE key + engine id in Settings")
    q = (query or "").strip()
    if not q: return _err("empty query")
    out_dorks = []
    total_hits = 0
    for tmpl, label in DORKS:
        dork = tmpl.format(q=q)
        try:
            r = requests.get("https://www.googleapis.com/customsearch/v1",
                             params={"key": cse_key, "cx": cx,
                                     "q": dork, "num": 5},
                             headers={"User-Agent": UA}, timeout=TIMEOUT)
        except Exception as e:
            out_dorks.append({"dork": label, "query": dork, "error": str(e),
                              "result_count": 0, "results": []})
            continue
        if r.status_code == 403:
            out_dorks.append({"dork": label, "query": dork,
                              "error": "Google CSE quota exhausted or rejected",
                              "result_count": 0, "results": []})
            continue
        if r.status_code != 200:
            out_dorks.append({"dork": label, "query": dork,
                              "error": f"HTTP {r.status_code}",
                              "result_count": 0, "results": []})
            continue
        items = (r.json().get("items") or [])
        rows = [{"title": it.get("title"), "url": it.get("link"),
                 "snippet": it.get("snippet")} for it in items[:5]]
        out_dorks.append({"dork": label, "query": dork,
                          "result_count": len(rows), "results": rows})
        total_hits += len(rows)
    return {
        "source":     "Google CSE preset OSINT dorks (15)",
        "query":      q,
        "total_hits": total_hits,
        "dorks":      out_dorks,
    }


# ── Google Scholar via CSE ───────────────────────────────────────────────
def google_scholar(query: str, cse_key: Optional[str], cx: Optional[str]) -> Dict[str, Any]:
    """Academic paper search by author name via CSE restricted to scholar."""
    if not cse_key or not cx:
        return _err("set Google CSE key + engine id in Settings")
    q = (query or "").strip()
    if not q: return _err("empty query")
    dork = f'"{q}" site:scholar.google.com OR site:arxiv.org OR site:researchgate.net OR site:academia.edu OR site:pubmed.ncbi.nlm.nih.gov'
    try:
        r = requests.get("https://www.googleapis.com/customsearch/v1",
                         params={"key": cse_key, "cx": cx, "q": dork, "num": 10},
                         headers={"User-Agent": UA}, timeout=TIMEOUT)
    except Exception as e:
        return _err(f"Google Scholar: {e}")
    if r.status_code == 403:
        return _err("Google CSE quota exhausted or rejected")
    if r.status_code != 200:
        return _err(f"Google Scholar HTTP {r.status_code}")
    items = r.json().get("items") or []
    return {
        "source":       "Google Scholar (via CSE)",
        "query":        q,
        "result_count": len(items),
        "results":      [{"title": it.get("title"), "url": it.get("link"),
                          "snippet": it.get("snippet"), "source": it.get("displayLink")}
                         for it in items],
    }


# ── back-compat aggregator (old callers) ─────────────────────────────────
_fec_search = fec_search
_opensanctions_search = opensanctions_search


def person_records(name: str, api_keys: Dict[str, str]) -> Dict[str, Any]:
    return {
        "fec":           fec_search(name, api_keys.get("fec")),
        "opensanctions": opensanctions_search(name),
    }
