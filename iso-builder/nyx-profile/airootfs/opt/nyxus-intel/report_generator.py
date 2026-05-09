# ============================================
# NYXUS — nyx-2026.05.02-x86_64.iso
# Copyright © 2026 Joseph Sierengowski
# All Rights Reserved
# Unauthorized use or distribution prohibited
# NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================
"""
NYXUS INTEL · report_generator.py
PDF investigation report.

Each report has:
   • cover page with NYXUS INTEL header, subject, case id, generated-at
   • executive summary
   • per-module sections (one section per data category)
   • errors / missing-key annotations
   • appendix: raw JSON for repeatability
   • footer on every page with the © marker

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from __future__ import annotations

import json
import datetime as dt
from pathlib import Path
from typing import Any, Dict

from reportlab.lib.pagesizes import LETTER
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    KeepTogether,
)


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

from reportlab.lib.enums import TA_LEFT, TA_CENTER

COPYRIGHT = "© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED"


def _styles() -> Dict[str, ParagraphStyle]:
    s = getSampleStyleSheet()
    h1 = ParagraphStyle("nx-h1", parent=s["Title"], fontName="Helvetica-Bold",
                        fontSize=24, leading=28, textColor=colors.HexColor("#0f1420"))
    h2 = ParagraphStyle("nx-h2", parent=s["Heading2"], fontName="Helvetica-Bold",
                        fontSize=14, leading=18, textColor=colors.HexColor("#1a1e2a"),
                        spaceBefore=14, spaceAfter=6)
    h3 = ParagraphStyle("nx-h3", parent=s["Heading3"], fontName="Helvetica-Bold",
                        fontSize=11, leading=14, textColor=colors.HexColor("#3a3e4a"),
                        spaceBefore=10, spaceAfter=4)
    body = ParagraphStyle("nx-body", parent=s["BodyText"], fontName="Inter",
                          fontSize=10, leading=14, textColor=colors.HexColor("#1a1e2a"))
    mono = ParagraphStyle("nx-mono", parent=s["BodyText"], fontName="Courier",
                          fontSize=8.5, leading=11, textColor=colors.HexColor("#1a1e2a"))
    dim = ParagraphStyle("nx-dim", parent=body, textColor=colors.HexColor("#6a6e78"))
    return {"h1": h1, "h2": h2, "h3": h3, "body": body, "mono": mono, "dim": dim}


def _fmt(v: Any, max_chars: int = 600) -> str:
    if v is None: return "—"
    if isinstance(v, bool): return "yes" if v else "no"
    if isinstance(v, (int, float)): return str(v)
    if isinstance(v, str):
        return (v[:max_chars] + ("…" if len(v) > max_chars else "")).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    try:
        s = json.dumps(v, default=str, ensure_ascii=False)
    except Exception:
        s = repr(v)
    s = s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return s[:max_chars] + ("…" if len(s) > max_chars else "")


def _kv_table(items, st):
    rows = [[Paragraph(f"<b>{k}</b>", st["body"]),
             Paragraph(_fmt(v), st["body"])] for k, v in items if v is not None]
    if not rows:
        return Paragraph("(none)", st["dim"])
    t = Table(rows, colWidths=[1.6 * inch, 5.0 * inch])
    t.setStyle(TableStyle([
        ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#e8edf5")),
        ("BOX",        (0, 0), (-1, -1), 0.4, colors.HexColor("#c8ccd6")),
        ("INNERGRID",  (0, 0), (-1, -1), 0.2, colors.HexColor("#c8ccd6")),
        ("LEFTPADDING",(0,0),(-1,-1), 6), ("RIGHTPADDING",(0,0),(-1,-1), 6),
        ("TOPPADDING", (0,0),(-1,-1), 3), ("BOTTOMPADDING",(0,0),(-1,-1), 3),
    ]))
    return t


def _on_page(canv, doc):
    canv.saveState()
    w, h = LETTER
    canv.setFont("Inter", 7.5)
    canv.setFillColor(colors.HexColor("#6a6e78"))
    canv.drawString(0.5 * inch, 0.4 * inch, COPYRIGHT)
    canv.drawRightString(w - 0.5 * inch, 0.4 * inch,
                         f"page {canv.getPageNumber()}")
    canv.setStrokeColor(colors.HexColor("#c8ccd6"))
    canv.setLineWidth(0.4)
    canv.line(0.5 * inch, 0.55 * inch, w - 0.5 * inch, 0.55 * inch)
    canv.restoreState()


def generate_pdf(payload: Dict[str, Any], target: Path) -> Path:
    findings = payload.get("findings") or {}
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(target), pagesize=LETTER,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.7 * inch,  bottomMargin=0.7 * inch,
        title=f"NYXUS INTEL — {payload.get('subject','case')}",
        author="NYXUS INTEL",
    )
    st = _styles()
    story = []

    # ── cover ──────────────────────────────────────────────────────
    story.append(Paragraph("NYXUS INTEL", st["h1"]))
    story.append(Paragraph("Investigation report", st["dim"]))
    story.append(Spacer(1, 0.3 * inch))

    story.append(_kv_table([
        ("Subject",        payload.get("subject")),
        ("Detected type",  findings.get("detected_type")),
        ("Generated at",   dt.datetime.utcnow().isoformat(timespec="seconds") + "Z"),
        ("Modules run",    len(findings.get("modules") or {})),
        ("Errors",         len(findings.get("errors") or {})),
        ("Started",        findings.get("started_at")),
        ("Finished",       findings.get("finished_at")),
        ("Elapsed (s)",    findings.get("elapsed")),
    ], st))

    if findings.get("summary"):
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph("Executive summary", st["h2"]))
        story.append(Paragraph(_fmt(findings["summary"], max_chars=4000), st["body"]))

    # ── per-module ─────────────────────────────────────────────────
    if findings.get("modules"):
        story.append(PageBreak())
        story.append(Paragraph("Findings by module", st["h2"]))
        for label, data in findings["modules"].items():
            story.append(Paragraph(label, st["h3"]))
            if isinstance(data, dict):
                # Top-level k/v (ignore deep lists/dicts in this table)
                primary = []
                deep    = []
                for k, v in data.items():
                    if isinstance(v, (list, dict)) and v:
                        deep.append((k, v))
                    else:
                        primary.append((k, v))
                story.append(_kv_table(primary, st))

                # Render deeper tables for lists of dicts
                for k, v in deep:
                    if isinstance(v, list) and v and isinstance(v[0], dict):
                        cols = list(v[0].keys())[:6]
                        rows = [[Paragraph(f"<b>{c}</b>", st["body"]) for c in cols]]
                        for item in v[:25]:
                            rows.append([Paragraph(_fmt(item.get(c), 200), st["body"])
                                         for c in cols])
                        widths = [6.6 * inch / max(1, len(cols))] * len(cols)
                        t = Table(rows, colWidths=widths, repeatRows=1)
                        t.setStyle(TableStyle([
                            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
                            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1e2a")),
                            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor("#e8edf5")),
                            ("BOX",        (0, 0), (-1, -1), 0.4, colors.HexColor("#c8ccd6")),
                            ("INNERGRID",  (0, 0), (-1, -1), 0.2, colors.HexColor("#c8ccd6")),
                            ("LEFTPADDING",(0,0),(-1,-1), 4), ("RIGHTPADDING",(0,0),(-1,-1), 4),
                            ("TOPPADDING", (0,0),(-1,-1), 2), ("BOTTOMPADDING",(0,0),(-1,-1), 2),
                        ]))
                        story.append(Paragraph(f"<i>{k}</i>", st["dim"]))
                        story.append(t)
                        story.append(Spacer(1, 0.1 * inch))
                    else:
                        story.append(Paragraph(f"<b>{k}</b>: {_fmt(v, 1500)}", st["body"]))
            else:
                story.append(Paragraph(_fmt(data, 4000), st["body"]))

            story.append(Spacer(1, 0.18 * inch))

    # ── errors ─────────────────────────────────────────────────────
    if findings.get("errors"):
        story.append(PageBreak())
        story.append(Paragraph("Errors / missing API keys", st["h2"]))
        rows = [[Paragraph("<b>module</b>", st["body"]), Paragraph("<b>message</b>", st["body"])]]
        for k, v in findings["errors"].items():
            rows.append([Paragraph(_fmt(k), st["body"]), Paragraph(_fmt(v), st["body"])])
        t = Table(rows, colWidths=[2.2 * inch, 4.4 * inch], repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a1e2a")),
            ("TEXTCOLOR",  (0, 0), (-1, 0), colors.HexColor("#e8edf5")),
            ("BOX",        (0, 0), (-1, -1), 0.4, colors.HexColor("#c8ccd6")),
            ("INNERGRID",  (0, 0), (-1, -1), 0.2, colors.HexColor("#c8ccd6")),
            ("VALIGN",     (0, 0), (-1, -1), "TOP"),
        ]))
        story.append(t)

    # ── investigator notes ─────────────────────────────────────────
    if (payload.get("notes") or "").strip():
        story.append(PageBreak())
        story.append(Paragraph("Investigator notes", st["h2"]))
        story.append(Paragraph(_fmt(payload["notes"], 100_000), st["body"]))

    # ── raw JSON appendix ──────────────────────────────────────────
    story.append(PageBreak())
    story.append(Paragraph("Raw findings (appendix)", st["h2"]))
    raw = json.dumps(findings, indent=2, default=str)
    # Chunk so reportlab does not OOM on huge findings
    for chunk in _chunk(raw, 3000):
        story.append(Paragraph("<pre>" + chunk.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;") + "</pre>",
                               st["mono"]))

    doc.build(story, onFirstPage=_on_page, onLaterPages=_on_page)
    return target


def _chunk(s: str, size: int):
    for i in range(0, len(s), size):
        yield s[i:i+size]
