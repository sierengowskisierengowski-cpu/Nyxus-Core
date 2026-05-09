# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · case_viewer.py
Tabbed display for an opened case payload.

Tabs (in order):
   Overview · Identity · Breach Data · Public Records · Digital Footprint
   Historical · Financial · Photos · Crypto · Network · Notes · Raw Data

Each tab introspects per-module dicts by an `agency` / `source` marker
or by content keys, so new modules are picked up automatically.

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Iterable, Tuple

import gi

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

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib

from ui_components import GLYPH, hand_label, divider, card


# ── helpers ─────────────────────────────────────────────────────────────
def _kv_grid(items: Iterable[Tuple[str, Any]]) -> Gtk.Widget:
    grid = Gtk.Grid(column_spacing=18, row_spacing=4)
    for r, (k, v) in enumerate(items):
        kl = Gtk.Label(label=str(k), xalign=1)
        kl.add_css_class("nx-dim"); kl.add_css_class("nx-mono")
        vl = Gtk.Label(label=_fmt_value(v), xalign=0, wrap=True,
                       wrap_mode=2, selectable=True)
        vl.add_css_class("nx-mono")
        grid.attach(kl, 0, r, 1, 1)
        grid.attach(vl, 1, r, 1, 1)
    return grid


def _fmt_value(v: Any) -> str:
    if v is None: return "—"
    if isinstance(v, bool): return "yes" if v else "no"
    if isinstance(v, (int, float, str)): return str(v)
    if isinstance(v, (list, tuple)):
        if not v: return "[]"
        if all(isinstance(x, (str, int, float)) for x in v):
            return ", ".join(str(x) for x in v[:25]) + (f"  (+{len(v)-25} more)" if len(v) > 25 else "")
        return f"{len(v)} items"
    if isinstance(v, dict):
        return f"{len(v)} fields"
    return repr(v)


def _section(title: str, glyph: str, body: Gtk.Widget) -> Gtk.Widget:
    return card(title, body, glyph=glyph)


def _items_list(items: List[Dict[str, Any]], cols: List[Tuple[str, str]]) -> Gtk.Widget:
    grid = Gtk.Grid(column_spacing=18, row_spacing=4)
    for ci, (label, _key) in enumerate(cols):
        h = Gtk.Label(label=label, xalign=0)
        h.add_css_class("nx-h3"); h.add_css_class("nx-accent")
        grid.attach(h, ci, 0, 1, 1)
    for ri, row in enumerate(items, start=1):
        for ci, (_label, key) in enumerate(cols):
            v = row.get(key) if isinstance(row, dict) else None
            l = Gtk.Label(label=_fmt_value(v), xalign=0, wrap=True,
                          wrap_mode=2, selectable=True)
            l.add_css_class("nx-mono")
            grid.attach(l, ci, ri, 1, 1)
    return grid


def _link_block(title: str, url: str | None,
                snippet: str | None = None) -> Gtk.Widget:
    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
    t = Gtk.Label(label=title or "—", xalign=0, wrap=True, wrap_mode=2,
                  selectable=True)
    t.add_css_class("nx-body")
    box.append(t)
    if url:
        u = Gtk.Label(label=url, xalign=0, wrap=True, wrap_mode=2, selectable=True)
        u.add_css_class("nx-dim"); u.add_css_class("nx-mono")
        box.append(u)
    if snippet:
        s = Gtk.Label(label=snippet, xalign=0, wrap=True, wrap_mode=2, selectable=True)
        s.add_css_class("nx-dim")
        box.append(s)
    return box


# ── viewer ──────────────────────────────────────────────────────────────
class CaseViewer(Gtk.Box):
    def __init__(self, payload: Dict[str, Any], app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8,
                         margin_top=10, margin_bottom=10,
                         margin_start=12, margin_end=12)
        self.payload = payload
        self.app = app
        self.findings = payload.get("findings") or {}

        self.append(self._build_header())
        self.append(divider())

        self.notebook = Gtk.Notebook(scrollable=True, vexpand=True)
        self.append(self.notebook)

        self._add_tab("Overview",          GLYPH.INFO,     self._tab_overview())
        self._add_tab("Identity",          GLYPH.USER,     self._tab_identity())
        self._add_tab("Breach Data",       GLYPH.SHIELD,   self._tab_breach())
        self._add_tab("Public Records",    GLYPH.DOCUMENT, self._tab_records())
        self._add_tab("Digital Footprint", GLYPH.GLOBE,    self._tab_footprint())
        self._add_tab("Historical",        GLYPH.CLOCK,    self._tab_historical())
        self._add_tab("Financial",         GLYPH.CHART,    self._tab_financial())
        self._add_tab("Photos",            GLYPH.PHOTO,    self._tab_photos())
        self._add_tab("Crypto",            GLYPH.CRYPTO,   self._tab_crypto())
        self._add_tab("Network",           GLYPH.SERVER,   self._tab_network())
        self._add_tab("Notes",             GLYPH.NOTES,    self._tab_notes())
        self._add_tab("Raw Data",          GLYPH.DATABASE, self._tab_raw())

    def _add_tab(self, title: str, glyph: str, child: Gtk.Widget):
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        wrap = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                       margin_top=12, margin_bottom=12,
                       margin_start=14, margin_end=14)
        wrap.append(child)
        scroll.set_child(wrap)
        label = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        g = Gtk.Label(label=glyph); g.add_css_class("nx-glyph")
        label.append(g)
        label.append(Gtk.Label(label=title))
        self.notebook.append_page(scroll, label)

    # ── header ──────────────────────────────────────────────────────
    def _build_header(self) -> Gtk.Widget:
        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        col = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                      hexpand=True)
        col.append(hand_label(self.findings.get("subject")
                              or self.payload.get("subject", "(unnamed)"),
                              size="h1"))
        sub = Gtk.Label(
            label=f"detected: {self.findings.get('detected_type','?')}  "
                  f"·  {self.findings.get('summary','')}",
            xalign=0, wrap=True)
        sub.add_css_class("nx-dim"); sub.add_css_class("nx-body")
        col.append(sub)
        outer.append(col)

        export = Gtk.Button(label=f"{GLYPH.EXPORT}   Export PDF")
        export.add_css_class("nx-primary")
        export.connect("clicked", self._on_export)
        outer.append(export)
        return outer

    def _on_export(self, *_):
        from report_generator import generate_pdf
        target = Path.home() / f"nyxus-intel-{self.payload.get('subject','case')}.pdf"
        try:
            for row in self.app.cases.alpha():
                if row["subject"] == self.payload.get("subject"):
                    target = Path(row["folder"]) / "report.pdf"
                    break
        except Exception:
            pass

        def worker():
            try:
                generate_pdf(self.payload, target)
                GLib.idle_add(lambda: self._toast(f"PDF saved → {target}"))
            except Exception as e:
                GLib.idle_add(lambda: self._toast(f"PDF failed: {e}", warn=True))
        threading.Thread(target=worker, daemon=True).start()
        self._toast("writing PDF…")

    def _toast(self, msg, warn=False):
        if not hasattr(self, "_toast_lbl"):
            self._toast_lbl = Gtk.Label(label="", xalign=1)
            self._toast_lbl.add_css_class("nx-dim"); self._toast_lbl.add_css_class("nx-mono")
            self.append(self._toast_lbl)
        self._toast_lbl.set_label(msg)
        if warn: self._toast_lbl.add_css_class("nx-warn")
        else:    self._toast_lbl.remove_css_class("nx-warn")

    # ── per-tab data accessors ───────────────────────────────────────
    def _modules(self): return self.findings.get("modules") or {}
    def _errors(self):  return self.findings.get("errors")  or {}

    def _modules_with(self, *keys) -> List[Tuple[str, Dict[str, Any]]]:
        out = []
        for label, data in self._modules().items():
            if isinstance(data, dict) and any(k in data for k in keys):
                out.append((label, data))
        return out

    # ── Overview ─────────────────────────────────────────────────────
    def _tab_overview(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.append(_section("Summary", GLYPH.INFO, _kv_grid([
            ("Subject",       self.findings.get("subject")),
            ("Detected type", self.findings.get("detected_type")),
            ("Modules run",   len(self._modules())),
            ("Errors",        len(self._errors())),
            ("Started",       self.findings.get("started_at")),
            ("Finished",      self.findings.get("finished_at")),
            ("Elapsed (s)",   self.findings.get("elapsed")),
        ])))
        roster = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        for label, data in self._modules().items():
            line = self._headline(data)
            row = Gtk.Box(spacing=8)
            g = Gtk.Label(label=GLYPH.CHECK); g.add_css_class("nx-glyph"); g.add_css_class("nx-ok")
            row.append(g)
            row.append(Gtk.Label(label=f"{label}: {line}", xalign=0,
                                 wrap=True, wrap_mode=2, selectable=True))
            roster.append(row)
        box.append(_section("Modules that returned data", GLYPH.CHECK, roster))

        if self._errors():
            err_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            for lab, msg in self._errors().items():
                row = Gtk.Box(spacing=6)
                g = Gtk.Label(label=GLYPH.WARNING); g.add_css_class("nx-glyph"); g.add_css_class("nx-warn")
                row.append(g)
                row.append(Gtk.Label(label=f"{lab}: {msg}", xalign=0, wrap=True,
                                     wrap_mode=2, selectable=True))
                err_box.append(row)
            box.append(_section("Errors / Missing API Keys", GLYPH.WARNING, err_box))
        return box

    def _headline(self, data: Any) -> str:
        if not isinstance(data, dict): return _fmt_value(data)
        if "found_count" in data:    return f"{data['found_count']} accounts"
        if "match_count" in data:    return f"{data['match_count']} matches"
        if "result_count" in data:   return f"{data['result_count']} results"
        if "subdomain_count" in data:return f"{data['subdomain_count']} subdomains"
        if "subdomains_count" in data:return f"{data['subdomains_count']} subdomains"
        if "breach_count" in data:   return f"{data['breach_count']} breaches"
        if "snapshots" in data:      return f"{data['snapshots']} archive snapshots"
        if "n_tx" in data:           return f"{data['n_tx']} BTC tx"
        if "tx_count" in data:       return f"{data['tx_count']} ETH tx"
        if "ports" in data:          return f"ports: {data['ports']}"
        if "exif_present" in data:   return "EXIF analysed"
        if "is_tor_exit" in data:    return f"tor exit: {data['is_tor_exit']}"
        if data.get("found") is False: return "not found"
        return "ok"

    # ── Identity ─────────────────────────────────────────────────────
    def _tab_identity(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for label, data in self._modules_with("name", "display_name", "preferred_username",
                                              "twitter", "bio", "company"):
            box.append(_section(label, GLYPH.USER, _kv_grid([
                ("name",     data.get("name") or data.get("display_name")),
                ("username", data.get("username") or data.get("preferred_username")),
                ("bio",      data.get("bio") or data.get("about")),
                ("company",  data.get("company")),
                ("location", data.get("location")),
                ("blog",     data.get("blog")),
                ("twitter",  data.get("twitter")),
                ("created",  data.get("created_at") or data.get("created_utc")),
                ("profile",  data.get("html_url") or data.get("profile_url") or data.get("url")),
            ])))
        for label, data in self._modules().items():
            if isinstance(data, dict) and isinstance(data.get("summary"), dict):
                s = data["summary"]
                box.append(_section(f"{label} — top match", GLYPH.USER, _kv_grid([
                    ("title",       s.get("title")),
                    ("description", s.get("description")),
                    ("extract",     s.get("extract")),
                    ("url",         s.get("url")),
                ])))
        for label, data in self._modules().items():
            if (isinstance(data, dict) and (data.get("source") or "").lower() == "github"
                and data.get("matches")):
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                inner.append(_kv_grid([("matches", data.get("match_count")),
                                       ("total GitHub hits", data.get("total"))]))
                inner.append(_items_list(data["matches"][:15],
                    [("login","login"),("type","type"),("score","score"),
                     ("url","html_url")]))
                box.append(_section(label, GLYPH.USER, inner))
        if not box.get_first_child():
            box.append(Gtk.Label(label="No identity data collected.", xalign=0))
        return box

    # ── Breach Data ──────────────────────────────────────────────────
    def _tab_breach(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for label, data in self._modules_with("breach_count", "breaches", "entries"):
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            inner.append(_kv_grid([
                ("breaches", data.get("breach_count")),
                ("entries",  data.get("result_count")),
            ]))
            if data.get("breaches"):
                inner.append(_items_list(data["breaches"],
                    [("name","name"),("date","breach_date"),("pwn count","pwn_count"),
                     ("data classes","data_classes")]))
            if data.get("entries"):
                inner.append(_items_list(data["entries"],
                    [("db","db_name"),("username","username"),("ip","ip"),
                     ("name","name"),("phone","phone")]))
            box.append(_section(label, GLYPH.SHIELD, inner))
        for label, data in self._modules().items():
            if (isinstance(data, dict) and "pastes" in data and data.get("pastes")):
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                inner.append(_kv_grid([("count", data.get("count") or data.get("result_count"))]))
                inner.append(_items_list(data["pastes"],
                    [("paste id","id"),("date","date"),("url","url")]))
                box.append(_section(label, GLYPH.SHIELD, inner))
        if not box.get_first_child():
            box.append(Gtk.Label(
                label="No breach data found. Email-typed subjects also try HIBP and DeHashed.",
                xalign=0, wrap=True))
        return box

    # ── Public Records ───────────────────────────────────────────────
    def _tab_records(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for label, data in self._modules().items():
            if not isinstance(data, dict): continue
            if not (data.get("agency") or "fec" in data or "rows" in data):
                continue
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            agency = data.get("agency") or ""

            if data.get("results") and "FEC" in agency and "ULS" not in agency:
                inner.append(hand_label("FEC contributions", size="h3"))
                inner.append(_items_list(data["results"],
                    [("contributor","contributor"),("city","city"),("state","state"),
                     ("amount","amount"),("date","date"),("committee","committee")]))
            elif data.get("results") and "OpenSanctions" in agency:
                inner.append(hand_label("OpenSanctions matches", size="h3"))
                inner.append(_items_list(data["results"],
                    [("name","caption"),("score","score"),("schema","schema"),
                     ("countries","countries"),("topics","topics"),("url","url")]))
            elif data.get("results") and "ULS" in agency:
                inner.append(hand_label("FCC ULS amateur licensees", size="h3"))
                inner.append(_items_list(data["results"],
                    [("name","licensee"),("callsign","callsign"),("city","city"),
                     ("state","state"),("class","license_class"),("expires","expiration")]))
            elif data.get("results") and "FAA" in agency and "owner" in agency.lower():
                inner.append(hand_label("FAA aircraft owned by name", size="h3"))
                inner.append(_items_list(data["results"],
                    [("N-number","n_number"),("manufacturer","manufacturer"),
                     ("model","model"),("year","year"),("owner","owner")]))
            elif data.get("results") and "Trademarks" in agency:
                inner.append(hand_label("USPTO trademark hits (via Google CSE)", size="h3"))
                inner.append(_items_list(data["results"],
                    [("title","title"),("url","url"),("snippet","snippet")]))

            if data.get("filings"):
                inner.append(hand_label("SEC EDGAR filings", size="h3"))
                inner.append(_items_list(data["filings"],
                    [("form","form"),("date","date"),("ciks","ciks"),
                     ("names","names"),("accession","accession")]))

            if data.get("patents"):
                inner.append(hand_label("USPTO patents", size="h3"))
                inner.append(_items_list(data["patents"],
                    [("patent","patent_id"),("title","title"),("date","date"),
                     ("inventors","inventors"),("url","url")]))

            if isinstance(data.get("aircraft"), dict):
                inner.append(hand_label(f"FAA aircraft {data.get('n_number','')}",
                                        size="h3"))
                inner.append(_kv_grid(data["aircraft"].items()))

            if data.get("rows"):
                inner.append(hand_label("FCC NPA-NXX rows", size="h3"))
                inner.append(Gtk.Label(label=json.dumps(data["rows"], indent=2),
                                       xalign=0, selectable=True, wrap=True, wrap_mode=2))

            if isinstance(data.get("fec"), dict) and data["fec"].get("results"):
                inner.append(hand_label("FEC contributions", size="h3"))
                inner.append(_items_list(data["fec"]["results"],
                    [("contributor","contributor"),("city","city"),("state","state"),
                     ("amount","amount"),("date","date")]))
            if isinstance(data.get("opensanctions"), dict) and data["opensanctions"].get("results"):
                inner.append(hand_label("OpenSanctions matches", size="h3"))
                inner.append(_items_list(data["opensanctions"]["results"],
                    [("name","caption"),("score","score"),("schema","schema")]))

            if inner.get_first_child():
                box.append(_section(label, GLYPH.DOCUMENT, inner))

        if not box.get_first_child():
            box.append(Gtk.Label(label="No public-records hits.", xalign=0))
        return box

    # ── Digital Footprint ────────────────────────────────────────────
    def _tab_footprint(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for label, data in self._modules_with("sites"):
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            inner.append(_kv_grid([("found", data.get("found_count"))]))
            for s in (data.get("sites") or [])[:300]:
                row = Gtk.Box(spacing=8)
                g = Gtk.Label(label=GLYPH.LINK); g.add_css_class("nx-glyph"); g.add_css_class("nx-accent")
                row.append(g)
                t = (s.get("site") or "") + ("  " + s.get("url","") if s.get("url") else "")
                row.append(Gtk.Label(label=t, xalign=0, wrap=True, wrap_mode=2, selectable=True))
                inner.append(row)
            box.append(_section(label, GLYPH.GLOBE, inner))

        for label, data in self._modules().items():
            if not isinstance(data, dict): continue
            if not isinstance(data.get("results"), list): continue
            agency = (data.get("agency") or "").lower()
            if agency and any(a in agency for a in ("fec","opensanctions","uls","faa","trademark")):
                continue
            if (data.get("source") or "").lower() == "github":
                continue
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            for r in data["results"][:50]:
                inner.append(_link_block(r.get("title"), r.get("link") or r.get("url"),
                                         r.get("snippet")))
                inner.append(divider())
            if inner.get_first_child():
                box.append(_section(label, GLYPH.SEARCH, inner))

        for label, data in self._modules().items():
            if isinstance(data, dict) and isinstance(data.get("dorks"), list):
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
                inner.append(_kv_grid([("total hits", data.get("total_hits"))]))
                for dk in data["dorks"]:
                    sub = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                                  margin_start=8)
                    sub.append(hand_label(dk.get("dork", ""), size="h3"))
                    if dk.get("error"):
                        sub.append(Gtk.Label(label=f"  {GLYPH.WARNING} {dk['error']}",
                                             xalign=0))
                    for r in dk.get("results", [])[:5]:
                        sub.append(_link_block(r.get("title"), r.get("url"),
                                               r.get("snippet")))
                    inner.append(sub)
                    inner.append(divider())
                box.append(_section(label, GLYPH.SEARCH, inner))

        for label, data in self._modules().items():
            if isinstance(data, dict) and data.get("pages"):
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                for p in data["pages"][:15]:
                    inner.append(_link_block(p.get("title"), p.get("url"),
                                             p.get("description")))
                box.append(_section(label, GLYPH.GLOBE, inner))

        for label, data in self._modules().items():
            if isinstance(data, dict) and data.get("items"):
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
                inner.append(_kv_grid([("total", data.get("total"))]))
                for it in data["items"][:20]:
                    inner.append(_link_block(
                        it.get("title") or it.get("identifier"),
                        it.get("url"),
                        f"{it.get('date','')}  ·  {it.get('mediatype','')}  ·  {it.get('creator','')}"))
                box.append(_section(label, GLYPH.GLOBE, inner))

        for label, data in self._modules_with("recent_comments"):
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            for c in (data.get("recent_comments") or [])[:30]:
                inner.append(Gtk.Label(
                    label=f"r/{c.get('subreddit')}  ·  score {c.get('score')}\n"
                          f"{c.get('body')}\n{c.get('permalink')}",
                    xalign=0, wrap=True, wrap_mode=2, selectable=True))
                inner.append(divider())
            box.append(_section(label, GLYPH.NOTES, inner))

        if not box.get_first_child():
            box.append(Gtk.Label(label="No digital footprint data collected.", xalign=0))
        return box

    # ── Historical ───────────────────────────────────────────────────
    def _tab_historical(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for label, data in self._modules_with("first_seen", "creation_date",
                                              "snapshots", "examples"):
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            inner.append(_kv_grid([
                ("first seen", data.get("first_seen")),
                ("creation",   data.get("creation_date")),
                ("expiration", data.get("expiration_date")),
                ("snapshots",  data.get("snapshots")),
                ("registrar",  data.get("registrar")),
            ]))
            for ex in (data.get("examples") or [])[:15]:
                inner.append(Gtk.Label(label=f"  {ex.get('timestamp')}  →  {ex.get('url')}",
                                       xalign=0, selectable=True, wrap=True, wrap_mode=2))
            box.append(_section(label, GLYPH.CLOCK, inner))

        for label, data in self._modules().items():
            if isinstance(data, dict) and data.get("filings"):
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                rows = sorted(data["filings"], key=lambda r: r.get("date") or "",
                              reverse=True)[:25]
                inner.append(_items_list(rows,
                    [("date","date"),("form","form"),("ciks","ciks"),("names","names")]))
                box.append(_section(f"{label} (timeline)", GLYPH.CLOCK, inner))
        for label, data in self._modules().items():
            if isinstance(data, dict) and data.get("patents"):
                inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
                rows = sorted(data["patents"], key=lambda r: r.get("date") or "",
                              reverse=True)[:25]
                inner.append(_items_list(rows,
                    [("date","date"),("patent","patent_id"),("title","title"),
                     ("inventors","inventors")]))
                box.append(_section(f"{label} (timeline)", GLYPH.CLOCK, inner))

        if not box.get_first_child():
            box.append(Gtk.Label(label="No historical data collected.", xalign=0))
        return box

    # ── Financial ────────────────────────────────────────────────────
    def _tab_financial(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for label, data in self._modules_with("balance_btc", "balance_eth"):
            box.append(_section(label, GLYPH.CHART, _kv_grid([
                ("balance BTC",  data.get("balance_btc")),
                ("balance ETH",  data.get("balance_eth")),
                ("received BTC", data.get("received_btc")),
                ("sent BTC",     data.get("sent_btc")),
                ("tx count",     data.get("n_tx") or data.get("tx_count")),
            ])))
        for label, data in self._modules().items():
            if isinstance(data, dict) and (data.get("agency") or "").startswith("FEC") \
                    and data.get("results"):
                amount = sum((r.get("amount") or 0) for r in data["results"])
                box.append(_section(f"{label} — totals", GLYPH.CHART, _kv_grid([
                    ("contributions count", len(data["results"])),
                    ("total reported $",    f"{amount:,.2f}"),
                ])))
            if isinstance(data, dict) and isinstance(data.get("fec"), dict) \
                    and data["fec"].get("results"):
                amount = sum((r.get("amount") or 0) for r in data["fec"]["results"])
                box.append(_section(f"{label} (FEC)", GLYPH.CHART, _kv_grid([
                    ("contributions count", len(data["fec"]["results"])),
                    ("total reported $",    f"{amount:,.2f}"),
                ])))
        if not box.get_first_child():
            box.append(Gtk.Label(label="No financial data collected.", xalign=0))
        return box

    # ── Photos ───────────────────────────────────────────────────────
    def _tab_photos(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for label, data in self._modules_with("exif_present", "exif_gps", "sha256"):
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            inner.append(_kv_grid([
                ("path",         data.get("path")),
                ("size",         data.get("size_bytes")),
                ("sha-256",      data.get("sha256")),
                ("dimensions",   f"{data.get('width','?')}x{data.get('height','?')}"),
                ("format",       data.get("format")),
                ("exif present", data.get("exif_present")),
            ]))
            if data.get("exif_gps"):
                gps = data["exif_gps"]
                inner.append(_kv_grid([
                    ("lat",     gps.get("lat")),
                    ("lng",     gps.get("lng")),
                    ("map",     data.get("map_url")),
                    ("address", (data.get("geocode") or {}).get("display_name")),
                ]))
            for w in data.get("integrity_warnings") or []:
                row = Gtk.Box(spacing=6)
                g = Gtk.Label(label=GLYPH.WARNING); g.add_css_class("nx-glyph"); g.add_css_class("nx-warn")
                row.append(g)
                row.append(Gtk.Label(label=w, xalign=0, wrap=True, wrap_mode=2, selectable=True))
                inner.append(row)
            box.append(_section(label, GLYPH.PHOTO, inner))
        if not box.get_first_child():
            box.append(Gtk.Label(label="No photo data collected.", xalign=0))
        return box

    # ── Crypto ───────────────────────────────────────────────────────
    def _tab_crypto(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for label, data in self._modules_with("balance_btc", "balance_eth", "transactions"):
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
            inner.append(_kv_grid([
                ("address",  data.get("address")),
                ("explorer", data.get("explorer")),
                ("api",      data.get("api")),
                ("balance",  data.get("balance_btc") or data.get("balance_eth")),
                ("tx count", data.get("n_tx") or data.get("tx_count")),
            ]))
            txs = data.get("transactions") or []
            if txs:
                inner.append(hand_label("Transactions", size="h3"))
                cols = ([("hash","hash"),("time","time"),("result","result"),("fee","fee")]
                        if "result" in (txs[0] if txs else {})
                        else [("hash","hash"),("time","time"),("from","from"),("to","to"),
                              ("value ETH","value_eth")])
                inner.append(_items_list(txs, cols))
            tt = data.get("token_transfers") or []
            if tt:
                inner.append(hand_label("Token transfers", size="h3"))
                inner.append(_items_list(tt,
                    [("token","token"),("amount","amount"),("from","from"),
                     ("to","to"),("time","time")]))
            box.append(_section(label, GLYPH.CRYPTO, inner))
        if not box.get_first_child():
            box.append(Gtk.Label(label="No crypto data collected.", xalign=0))
        return box

    # ── Network ──────────────────────────────────────────────────────
    def _tab_network(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for label, data in self._modules_with("ports", "asn", "country", "ptr",
                                              "is_tor_exit", "subdomains_count",
                                              "subdomain_count",
                                              "A", "MX", "NS", "technologies", "handle"):
            inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            inner.append(_kv_grid([
                ("ip",         data.get("ip")),
                ("hostname",   data.get("hostname") or data.get("ptr")),
                ("city",       data.get("city")),
                ("country",    data.get("country")),
                ("asn",        data.get("asn") or data.get("as_owner")),
                ("isp/org",    data.get("isp") or data.get("org")),
                ("tor exit",   data.get("is_tor_exit")),
                ("ports",      data.get("ports")),
                ("vulns",      data.get("vulns")),
                ("abuse score",data.get("abuse_score")),
                ("subdomains", data.get("subdomains_count") or data.get("subdomain_count")),
                ("RDAP handle",data.get("handle")),
                ("CIDR",       data.get("cidr")),
                ("Server",     data.get("server_header")),
                ("X-Powered-By", data.get("powered_by")),
                ("technologies", data.get("technologies")),
            ]))
            for rt in ("A","AAAA","MX","NS","TXT","SOA","CNAME","CAA"):
                if data.get(rt):
                    inner.append(Gtk.Label(label=f"{rt}: " + ", ".join(data[rt]),
                                           xalign=0, wrap=True, wrap_mode=2, selectable=True))
            services = data.get("services") or []
            if services:
                inner.append(hand_label("Exposed services", size="h3"))
                inner.append(_items_list(services,
                    [("port","port"),("transport","transport"),("product","product"),
                     ("version","version")]))
            shodan_data = data.get("data") or []
            if shodan_data and isinstance(shodan_data[0], dict) and "subdomain" in shodan_data[0]:
                inner.append(hand_label("Shodan DNS records", size="h3"))
                inner.append(_items_list(shodan_data[:50],
                    [("subdomain","subdomain"),("type","type"),("value","value"),
                     ("last seen","last_seen")]))
            box.append(_section(label, GLYPH.SERVER, inner))
        if not box.get_first_child():
            box.append(Gtk.Label(label="No network data collected.", xalign=0))
        return box

    # ── Notes ────────────────────────────────────────────────────────
    def _tab_notes(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.append(hand_label("Investigator notes", size="h2"))
        view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, vexpand=True)
        view.set_size_request(-1, 240)
        view.add_css_class("nx-body")
        buf = view.get_buffer()
        buf.set_text(self.payload.get("notes", ""))
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(view)
        box.append(scroll)

        save = Gtk.Button(label="Save notes")
        save.add_css_class("nx-primary")

        def _save(*_):
            txt = buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)
            try:
                for row in self.app.cases.alpha():
                    if row["subject"] == self.payload.get("subject"):
                        self.app.cases.update_notes(row["id"], txt)
                        self._toast("notes saved")
                        return
                self._toast("could not locate case row", warn=True)
            except Exception as e:
                self._toast(f"save failed: {e}", warn=True)
        save.connect("clicked", _save)
        box.append(save)
        return box

    # ── Raw Data ─────────────────────────────────────────────────────
    def _tab_raw(self) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        view = Gtk.TextView(wrap_mode=Gtk.WrapMode.WORD_CHAR, vexpand=True,
                            editable=False, monospace=True)
        view.add_css_class("nx-mono")
        try:
            view.get_buffer().set_text(json.dumps(self.findings, indent=2,
                                                  default=str))
        except Exception as e:
            view.get_buffer().set_text(f"failed to render: {e}")
        scroll = Gtk.ScrolledWindow(vexpand=True)
        scroll.set_child(view)
        box.append(scroll)
        return box
