# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · username_intel.py
Username investigation across social platforms.

  • Sherlock — open source CLI, no key, scans 400+ sites
  • GitHub   — public, optional token (raises rate limit)
  • Reddit   — Pushshift / old-reddit JSON, no key

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
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
TIMEOUT = 20


def _err(msg: str) -> Dict[str, Any]:
    return {"__error__": msg}


# ── Sherlock ────────────────────────────────────────────────────────────
def sherlock_lookup(username: str) -> Dict[str, Any]:
    if not username:
        return _err("empty username")
    binary = shutil.which("sherlock")
    if binary is None:
        # try python -m sherlock_project
        cmd = ["python3", "-m", "sherlock_project", username, "--print-found",
               "--no-color", "--timeout", "15"]
    else:
        cmd = [binary, username, "--print-found", "--no-color", "--timeout", "15"]

    with tempfile.TemporaryDirectory() as tmp:
        try:
            out = subprocess.run(cmd + ["--folderoutput", tmp],
                                 capture_output=True, text=True, timeout=240)
        except FileNotFoundError:
            return _err("sherlock not installed (pip install sherlock-project)")
        except subprocess.TimeoutExpired:
            return _err("sherlock timed out after 240s")

        # Sherlock writes <username>.txt with one URL per line (only found).
        results: List[Dict[str, str]] = []
        path = os.path.join(tmp, f"{username}.txt")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and line.startswith("http"):
                        results.append({"url": line, "site": _site_from_url(line)})

        return {
            "username":     username,
            "found_count":  len(results),
            "sites":        results,
            "stderr_tail":  out.stderr.splitlines()[-3:] if out.stderr else [],
        }


def _site_from_url(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([^/]+)/", url + "/")
    return m.group(1) if m else url


# ── GitHub ──────────────────────────────────────────────────────────────
def github_lookup(username: str, token: Optional[str]) -> Dict[str, Any]:
    headers = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if token: headers["Authorization"] = f"Bearer {token}"

    r = requests.get(f"https://api.github.com/users/{username}",
                     headers=headers, timeout=TIMEOUT)
    if r.status_code == 404:
        return {"username": username, "exists": False}
    if r.status_code == 403:
        return _err("GitHub rate-limit hit (set token in Settings to raise it)")
    if r.status_code == 401:
        return _err("GitHub rejected the token")
    r.raise_for_status()
    user = r.json()

    # Top public repos
    repos: List[Dict[str, Any]] = []
    rr = requests.get(f"https://api.github.com/users/{username}/repos",
                      params={"sort": "updated", "per_page": 30},
                      headers=headers, timeout=TIMEOUT)
    if rr.status_code == 200:
        for repo in rr.json():
            repos.append({"name":     repo.get("name"),
                          "fork":     repo.get("fork"),
                          "stars":    repo.get("stargazers_count"),
                          "forks":    repo.get("forks_count"),
                          "language": repo.get("language"),
                          "updated":  repo.get("updated_at"),
                          "url":      repo.get("html_url"),
                          "description": repo.get("description")})

    return {
        "username":   username,
        "exists":     True,
        "id":         user.get("id"),
        "name":       user.get("name"),
        "company":    user.get("company"),
        "blog":       user.get("blog"),
        "location":   user.get("location"),
        "email":      user.get("email"),
        "bio":        user.get("bio"),
        "twitter":    user.get("twitter_username"),
        "public_repos": user.get("public_repos"),
        "followers":  user.get("followers"),
        "following":  user.get("following"),
        "created_at": user.get("created_at"),
        "html_url":   user.get("html_url"),
        "avatar_url": user.get("avatar_url"),
        "repos":      repos,
    }


# ── Reddit ──────────────────────────────────────────────────────────────
def reddit_lookup(username: str) -> Dict[str, Any]:
    # Public JSON endpoint — no auth, but UA is required.
    url = f"https://www.reddit.com/user/{username}/about.json"
    r = requests.get(url, headers={"User-Agent": UA}, timeout=TIMEOUT)
    if r.status_code == 404:
        return {"username": username, "exists": False}
    if r.status_code == 429:
        return _err("Reddit rate-limited")
    if r.status_code != 200:
        return _err(f"Reddit HTTP {r.status_code}")
    data = (r.json() or {}).get("data") or {}

    out = {
        "username":     username,
        "exists":       True,
        "id":           data.get("id"),
        "created_utc":  data.get("created_utc"),
        "comment_karma": data.get("comment_karma"),
        "link_karma":   data.get("link_karma"),
        "is_employee":  data.get("is_employee"),
        "is_mod":       data.get("is_mod"),
        "verified":     data.get("verified"),
        "icon_img":     data.get("icon_img"),
        "url":          f"https://www.reddit.com/user/{username}/",
    }

    # Recent comments
    cr = requests.get(
        f"https://www.reddit.com/user/{username}/comments.json?limit=25",
        headers={"User-Agent": UA}, timeout=TIMEOUT)
    comments: List[Dict[str, Any]] = []
    if cr.status_code == 200:
        for c in (cr.json().get("data") or {}).get("children") or []:
            cd = c.get("data") or {}
            comments.append({
                "subreddit": cd.get("subreddit"),
                "score":     cd.get("score"),
                "created_utc": cd.get("created_utc"),
                "permalink": "https://www.reddit.com" + (cd.get("permalink") or ""),
                "body":      (cd.get("body") or "")[:300],
            })
    out["recent_comments"] = comments
    return out
