"""
NYXUS Panel — RSS news engine.

Background-threaded fetcher for all enabled feeds.  Parses with feedparser,
extracts a thumbnail (media:thumbnail / media:content / enclosure / first
<img> in the summary), downloads & resizes it via Pillow into the cache,
and pushes the merged + filtered + sorted article list back to the UI
through GLib.idle_add.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from gi.repository import GLib  # type: ignore

from settings import CACHE_DIR, all_sources

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


ARTICLES_CACHE = CACHE_DIR / "articles.json"
THUMBS_DIR     = CACHE_DIR / "thumbs"
FAV_DIR        = CACHE_DIR / "favicons"
THUMBS_DIR.mkdir(parents=True, exist_ok=True)
FAV_DIR.mkdir(parents=True, exist_ok=True)

_HTTP_TIMEOUT = 8
_THUMB_W, _THUMB_H = 408, 156
_SUB_W,   _SUB_H   = 200, 140
UA = "Mozilla/5.0 (X11; Linux x86_64) NYXUS-Panel/1.0"

# soft import — feedparser may need pip
try:
    import feedparser  # type: ignore
except ImportError:
    feedparser = None  # type: ignore

try:
    import requests  # type: ignore
except ImportError:
    requests = None  # type: ignore

try:
    from bs4 import BeautifulSoup  # type: ignore
except ImportError:
    BeautifulSoup = None  # type: ignore

try:
    from PIL import Image  # type: ignore
except ImportError:
    Image = None  # type: ignore


# ───────────────────────────── helpers
def _hash(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8", "ignore")).hexdigest()[:16]


def _img_url_from_entry(entry: Any) -> Optional[str]:
    # 1. media:thumbnail / media:content
    for k in ("media_thumbnail", "media_content"):
        v = getattr(entry, k, None) or entry.get(k) if isinstance(entry, dict) else None
        if isinstance(v, list) and v:
            url = v[0].get("url")
            if url:
                return url
    # 2. enclosure
    for enc in entry.get("enclosures", []) or []:
        if isinstance(enc, dict):
            t = (enc.get("type") or "").lower()
            if t.startswith("image/"):
                return enc.get("href") or enc.get("url")
    # 3. <img> inside summary / content
    html_blobs: List[str] = []
    for k in ("summary", "description"):
        if entry.get(k):
            html_blobs.append(entry[k])
    if isinstance(entry.get("content"), list):
        for c in entry["content"]:
            if isinstance(c, dict) and c.get("value"):
                html_blobs.append(c["value"])
    for html in html_blobs:
        if BeautifulSoup is not None:
            try:
                soup = BeautifulSoup(html, "html.parser")
                img = soup.find("img")
                if img and img.get("src"):
                    return img["src"]
            except Exception:
                pass
        else:
            m = re.search(r'<img[^>]+src=["\']([^"\']+)', html)
            if m:
                return m.group(1)
    return None


def _published_ts(entry: Any) -> float:
    for k in ("published_parsed", "updated_parsed"):
        v = entry.get(k)
        if v:
            try:
                return time.mktime(v)
            except (TypeError, ValueError):
                pass
    return 0.0


def _strip_html(s: str) -> str:
    if not s:
        return ""
    if BeautifulSoup is not None:
        try:
            return BeautifulSoup(s, "html.parser").get_text(" ", strip=True)
        except Exception:
            return re.sub(r"<[^>]+>", " ", s).strip()
    return re.sub(r"<[^>]+>", " ", s).strip()


def _download_image(url: str, dest: Path, w: int, h: int) -> Optional[str]:
    if requests is None or Image is None:
        return None
    if dest.exists():
        return str(dest)
    try:
        r = requests.get(url, timeout=_HTTP_TIMEOUT, headers={"User-Agent": UA}, stream=True)
        r.raise_for_status()
        raw_path = dest.with_suffix(".raw")
        with raw_path.open("wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        try:
            im = Image.open(raw_path)
            im = im.convert("RGB")
            # cover-fit resize: fill the box, keep aspect, crop overflow
            iw, ih = im.size
            ratio = max(w / iw, h / ih)
            new = (max(1, int(iw * ratio)), max(1, int(ih * ratio)))
            im = im.resize(new, Image.LANCZOS)
            left = (im.size[0] - w) // 2
            top  = (im.size[1] - h) // 2
            im = im.crop((left, top, left + w, top + h))
            im.save(dest, "JPEG", quality=82)
            raw_path.unlink(missing_ok=True)
            return str(dest)
        except Exception:
            raw_path.unlink(missing_ok=True)
            return None
    except Exception:
        return None


def _favicon_for(url: str) -> Optional[str]:
    if not url:
        return None
    host = urlparse(url).netloc
    if not host:
        return None
    dest = FAV_DIR / f"{_hash(host)}.png"
    if dest.exists():
        return str(dest)
    if requests is None or Image is None:
        return None
    candidates = [
        f"https://www.google.com/s2/favicons?sz=32&domain={host}",
        f"https://{host}/favicon.ico",
    ]
    for u in candidates:
        try:
            r = requests.get(u, timeout=_HTTP_TIMEOUT, headers={"User-Agent": UA})
            r.raise_for_status()
            raw = dest.with_suffix(".raw")
            raw.write_bytes(r.content)
            try:
                im = Image.open(raw).convert("RGBA").resize((24, 24), Image.LANCZOS)
                im.save(dest, "PNG")
                raw.unlink(missing_ok=True)
                return str(dest)
            except Exception:
                raw.unlink(missing_ok=True)
                continue
        except Exception:
            continue
    return None


def _passes_filters(article: Dict[str, Any], allow: List[str], block: List[str]) -> bool:
    text = (article.get("title", "") + " " + article.get("summary", "")).lower()
    if any(b.lower() in text for b in block):
        return False
    if allow and not any(a.lower() in text for a in allow):
        return False
    return True


# ───────────────────────────── public engine
class NewsEngine:
    """Threaded RSS aggregator.  One instance per panel."""

    def __init__(self, cfg_provider: Callable[[], Dict[str, Any]]):
        self._cfg_provider = cfg_provider
        self._listeners: List[Callable[[List[Dict[str, Any]]], None]] = []
        self._lock = threading.Lock()
        self._refreshing = False
        self._timer_id = 0

    # ────── listeners
    def add_listener(self, cb: Callable[[List[Dict[str, Any]]], None]) -> None:
        self._listeners.append(cb)

    def _emit(self, articles: List[Dict[str, Any]]) -> None:
        for cb in list(self._listeners):
            try:
                cb(articles)
            except Exception:
                pass

    # ────── disk cache
    def cached(self) -> List[Dict[str, Any]]:
        if not ARTICLES_CACHE.exists():
            return []
        try:
            with ARTICLES_CACHE.open() as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

    def _write_cache(self, articles: List[Dict[str, Any]]) -> None:
        try:
            with ARTICLES_CACHE.open("w") as f:
                json.dump(articles, f)
        except OSError:
            pass

    # ────── periodic
    def start_auto_refresh(self) -> None:
        self.stop_auto_refresh()
        cfg = self._cfg_provider()
        mins = max(5, int(cfg.get("refresh_interval_min", 30)))
        # First refresh kicks off immediately when started
        self.refresh_async()
        self._timer_id = GLib.timeout_add_seconds(mins * 60, self._on_tick)

    def stop_auto_refresh(self) -> None:
        if self._timer_id:
            GLib.source_remove(self._timer_id)
            self._timer_id = 0

    def _on_tick(self) -> bool:
        self.refresh_async()
        return True

    # ────── refresh
    def refresh_async(self) -> None:
        with self._lock:
            if self._refreshing:
                return
            self._refreshing = True
        threading.Thread(target=self._refresh, daemon=True).start()

    def _refresh(self) -> None:
        try:
            cfg = self._cfg_provider()
            sources = all_sources(cfg)
            allow   = cfg.get("keyword_allow", []) or []
            block   = cfg.get("keyword_block", []) or []
            max_n   = int(cfg.get("max_articles", 30))
            articles: List[Dict[str, Any]] = []

            if feedparser is None:
                # Cannot proceed without feedparser; emit cache
                GLib.idle_add(self._emit, self.cached())
                return

            for src in sources:
                try:
                    feed = feedparser.parse(src["url"], request_headers={"User-Agent": UA})
                except Exception:
                    continue
                fav = _favicon_for(src["url"])
                # cap per-source so one busy feed can't drown out the rest
                for entry in (feed.entries or [])[:12]:
                    title   = (entry.get("title") or "").strip()
                    link    = entry.get("link") or ""
                    if not title or not link:
                        continue
                    summary = _strip_html(entry.get("summary", "") or entry.get("description", ""))
                    art = {
                        "id":           _hash(link),
                        "title":        title,
                        "link":         link,
                        "summary":      summary[:400],
                        "published":    _published_ts(entry),
                        "source_id":    src["id"],
                        "source_label": src["label"],
                        "source_cat":   src.get("cat", ""),
                        "favicon":      fav,
                        "thumb":        None,
                        "img_url":      _img_url_from_entry(entry),
                    }
                    if not _passes_filters(art, allow, block):
                        continue
                    articles.append(art)

            # newest first
            articles.sort(key=lambda a: a["published"] or 0, reverse=True)
            articles = articles[:max_n]

            # Push partial result *first* so the UI gets text + sources fast,
            # then fill in thumbnails as they download.  We pass DEEP COPIES
            # of each dict so the UI thread is reading immutable snapshots
            # while the worker thread continues mutating its own copies.
            self._write_cache(articles)
            GLib.idle_add(self._emit, [dict(a) for a in articles])

            # ── second pass: download thumbnails (size depends on rank)
            for idx, art in enumerate(articles):
                url = art.get("img_url")
                if not url:
                    continue
                # hero gets the big thumb; rest use the smaller cover
                w, h = (_THUMB_W, _THUMB_H) if idx == 0 else (_SUB_W, _SUB_H)
                dest = THUMBS_DIR / f"{art['id']}_{w}x{h}.jpg"
                path = _download_image(url, dest, w, h)
                if path:
                    art["thumb"] = path

            self._write_cache(articles)
            GLib.idle_add(self._emit, [dict(a) for a in articles])
        finally:
            with self._lock:
                self._refreshing = False


__all__ = ["NewsEngine"]
