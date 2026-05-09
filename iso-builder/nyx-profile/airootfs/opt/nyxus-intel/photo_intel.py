# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · photo_intel.py
EXIF + GPS extraction with integrity warnings.

We use piexif (lightweight, pure-python) so we get raw EXIF tags without
Pillow's normalization losing data. GPS coordinates are converted to
decimal degrees and reverse-geocoded via OpenStreetMap Nominatim (no key
needed; we identify with a NYXUS UA per their TOS).

Integrity warnings:
   • software field mentions "photoshop" / "lightroom" → likely edited
   • DateTimeDigitized != DateTimeOriginal → possibly re-saved
   • no EXIF at all → metadata stripped (often a screenshot or social media)

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import os
import hashlib
from typing import Dict, Any, Tuple, Optional

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
TIMEOUT = 25


def _err(msg): return {"__error__": msg}


def analyse_image(path: str) -> Dict[str, Any]:
    if not os.path.isfile(path):
        return _err(f"file not found: {path}")
    try:
        sha = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                sha.update(chunk)
    except OSError as e:
        return _err(f"read error: {e}")

    info: Dict[str, Any] = {
        "path":       path,
        "size_bytes": os.path.getsize(path),
        "sha256":     sha.hexdigest(),
    }

    # Pillow: dimensions, format, mode
    try:
        from PIL import Image
        with Image.open(path) as img:
            info["format"]     = img.format
            info["mode"]       = img.mode
            info["width"]      = img.width
            info["height"]     = img.height
    except Exception as e:
        info["pillow_error"] = str(e)

    # piexif: full raw EXIF
    exif_present = False
    exif: Dict[str, Any] = {}
    try:
        import piexif
        try:
            raw = piexif.load(path)
            exif_present = any(raw.get(k) for k in ("0th", "Exif", "GPS", "1st"))
            for ifd in ("0th", "Exif", "GPS", "1st"):
                tagdict = raw.get(ifd) or {}
                exif[ifd] = {
                    piexif.TAGS[ifd][tag]["name"]: _safe_val(v)
                    for tag, v in tagdict.items()
                    if tag in piexif.TAGS.get(ifd, {})
                }
        except piexif.InvalidImageDataError:
            exif_present = False
        except Exception as e:
            info["piexif_error"] = str(e)
    except ImportError:
        info["piexif_error"] = "piexif not installed"

    info["exif_present"] = exif_present
    info["exif"] = exif

    # GPS → decimal + reverse geocode
    gps = exif.get("GPS") or {}
    if gps:
        coords = _gps_to_decimal(gps)
        if coords:
            info["exif_gps"] = {"lat": coords[0], "lng": coords[1]}
            info["map_url"] = f"https://www.openstreetmap.org/?mlat={coords[0]}&mlon={coords[1]}#map=15/{coords[0]}/{coords[1]}"
            info["geocode"] = _reverse_geocode(coords[0], coords[1])

    # Integrity warnings
    warns = []
    if not exif_present:
        warns.append("no EXIF — metadata likely stripped (screenshot, social repost, edit)")
    sw = (exif.get("0th", {}) or {}).get("Software", "") or ""
    if isinstance(sw, str) and sw:
        low = sw.lower()
        if any(t in low for t in ("photoshop", "lightroom", "gimp", "affinity")):
            warns.append(f"software tag suggests editing: {sw!r}")
    dto = (exif.get("Exif", {}) or {}).get("DateTimeOriginal")
    dtd = (exif.get("Exif", {}) or {}).get("DateTimeDigitized")
    if dto and dtd and dto != dtd:
        warns.append(f"DateTimeOriginal ({dto}) != DateTimeDigitized ({dtd}) — re-saved?")
    info["integrity_warnings"] = warns

    return info


def _safe_val(v):
    if isinstance(v, bytes):
        try:    return v.decode("utf-8", errors="replace").strip("\x00")
        except: return repr(v)
    if isinstance(v, tuple):
        return [list(x) if isinstance(x, tuple) else x for x in v]
    return v


def _gps_to_decimal(gps_ifd: Dict[str, Any]) -> Optional[Tuple[float, float]]:
    """Convert piexif GPS IFD to (lat, lng) decimal degrees."""
    try:
        lat = gps_ifd.get("GPSLatitude")
        lon = gps_ifd.get("GPSLongitude")
        latref = gps_ifd.get("GPSLatitudeRef") or "N"
        lonref = gps_ifd.get("GPSLongitudeRef") or "E"
        if not lat or not lon: return None

        def to_deg(part):
            d, m, s = part
            deg = d[0] / d[1] if isinstance(d, (list, tuple)) else float(d)
            mn  = m[0] / m[1] if isinstance(m, (list, tuple)) else float(m)
            sc  = s[0] / s[1] if isinstance(s, (list, tuple)) else float(s)
            return deg + mn/60 + sc/3600

        latd = to_deg(lat)
        lond = to_deg(lon)
        if str(latref).upper().startswith("S"): latd = -latd
        if str(lonref).upper().startswith("W"): lond = -lond
        return latd, lond
    except Exception:
        return None


def _reverse_geocode(lat: float, lng: float) -> Dict[str, Any]:
    try:
        r = requests.get(
            "https://nominatim.openstreetmap.org/reverse",
            params={"lat": lat, "lon": lng, "format": "jsonv2", "zoom": 18},
            headers={"User-Agent": UA},
            timeout=TIMEOUT,
        )
        if r.status_code != 200:
            return {"error": f"Nominatim HTTP {r.status_code}"}
        d = r.json()
        return {
            "display_name": d.get("display_name"),
            "address":      d.get("address"),
            "osm_type":     d.get("osm_type"),
            "osm_id":       d.get("osm_id"),
        }
    except Exception as e:
        return {"error": str(e)}
