"""
NYXUS Home - palette + CSS
Mirrors HomeDashboard.tsx + waybar-style.css color scheme.
Inter for DARK MIRROR UI text, JetBrains Mono for code/data.
(c) 2026 Joseph A. Sierengowski - NYX-J5W-2026-SIERENGOWSKI-LOCKED
"""
from gi.repository import Gtk, Gdk

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


# OBSIDIAN PRISM palette (rev 2026-07-07) — accent slots kept in
# lockstep by nyxus-apply-accent; this file is a registered consumer.
PALETTE = {
    "mono":   "#e8edf5",
    "pink":   "#794dff",
    "cyan":   "#ff266c",
    "purple": "#26ffb7",
    "gold":   "#ffb026",
    "indigo": "#26ffb7",
    "green":  "#6dffcf",
    "orange": "#ff7849",
    "blue":   "#4d9fff",
    "red":    "#ff4d6b",
    "white":  "#ffffff",
    "text":   "#e8edf5",
    "dim":    "#c8ccd6",
    "void":   "#0f1420",
}

NEONS = ["#794dff", "#ff266c", "#26ffb7", "#ffb026", "#6dffcf",
         "#ff7ae5", "#66efff", "#c084fc", "#ffce85"]


def _card_css(name, color):
    return f"""
.card-{name} {{
    background: rgba(6, 4, 12, 0.62);
    border: 1px dashed alpha({color}, 0.66);
    border-top: 2px solid {color};
    border-radius: 8px;
    padding: 12px 14px;
    box-shadow: 0 0 18px alpha({color}, 0.34),
                0 6px 22px rgba(0,0,0,0.55),
                inset 0 0 24px rgba(0,0,0,0.18);
}}
.card-{name}-header-glyph {{
    color: {color};
    font-size: 18px;
    text-shadow: 0 0 10px {color}, 0 0 18px alpha({color}, 0.55);
}}
.card-{name}-header-title {{
    font-family: "Inter Display", cursive;
    font-size: 24px;
    font-weight: 700;
    color: {color};
    text-shadow: 0 0 8px alpha({color}, 0.40);
    letter-spacing: 0.02em;
}}
.card-{name}-header-stamp {{
    font-family: "JetBrains Mono", monospace;
    font-size: 8px;
    color: alpha({color}, 0.47);
    letter-spacing: 0.22em;
}}
.card-{name}-header-rule {{
    background: alpha({color}, 0.20);
    min-height: 1px;
}}
.card-{name}-footer {{
    font-family: "JetBrains Mono", monospace;
    font-size: 9px;
    color: alpha({color}, 0.55);
    letter-spacing: 0.16em;
    padding-top: 6px;
    border-top: 1px dashed alpha({color}, 0.13);
}}
.btn-nav-{name} {{
    background: transparent;
    border: 1px solid alpha({color}, 0.34);
    color: {color};
    font-family: "JetBrains Mono", monospace;
    font-size: 9px;
    letter-spacing: 0.18em;
    padding: 4px 9px;
    border-radius: 2px;
}}
.btn-nav-{name}:hover {{
    background: alpha({color}, 0.13);
    border-color: {color};
}}
.btn-primary-{name} {{
    background: alpha({color}, 0.13);
    border: 1px solid {color};
    color: {color};
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    letter-spacing: 0.18em;
    font-weight: 700;
    padding: 6px 11px;
    border-radius: 3px;
    text-shadow: 0 0 6px alpha({color}, 0.55);
}}
.btn-primary-{name}:hover {{
    background: alpha({color}, 0.25);
    box-shadow: 0 0 14px alpha({color}, 0.55);
}}
.btn-icon-{name} {{
    background: transparent;
    border: 1px solid alpha({color}, 0.34);
    color: {color};
    font-size: 11px;
    padding: 3px 7px;
    border-radius: 2px;
    min-width: 0;
    min-height: 0;
}}
.btn-icon-{name}:hover {{
    background: alpha({color}, 0.13);
}}
.input-{name} {{
    background: rgba(0, 0, 0, 0.45);
    border: 1px dashed alpha({color}, 0.34);
    border-radius: 3px;
    color: #e8edf5;
    padding: 5px 8px;
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    min-height: 0;
}}
.input-{name}:focus {{
    border-color: {color};
    box-shadow: 0 0 12px alpha({color}, 0.40);
}}
.notif-{name} {{
    border: 1px dashed alpha({color}, 0.20);
    border-left: 3px solid {color};
    background: alpha({color}, 0.06);
    padding: 7px 9px;
    border-radius: 3px;
}}
"""


def build_css():
    css = format_css("""
window, .home-root {{
    background: rgba(6, 0, 16, 0.65);
    color: {WHITE_OFF};
    font-family: "Inter Display", "JetBrains Mono", sans-serif;
}}
.header-tag {{
    font-family: "JetBrains Mono", monospace;
    font-size: 9px;
    color: alpha({WHITE_OFF}, 0.66);
    letter-spacing: 0.28em;
}}
.header-title {{
    font-family: "Inter Display", cursive;
    font-size: 32px;
    color: {WHITE_OFF};
    text-shadow: 0 0 14px alpha({WHITE_OFF}, 0.40),
                 0 0 28px alpha({WHITE_OFF}, 0.20);
    letter-spacing: 0.02em;
}}
.header-title-pink  {{ color: {WHITE_OFF}; }}
.header-title-gold  {{ color: {WHITE_OFF}; }}
.header-stamp {{
    font-family: "JetBrains Mono", monospace;
    font-size: 8px;
    color: {GREY_TERTIARY};
    letter-spacing: 0.22em;
}}
.clock-time {{
    font-family: "JetBrains Mono", monospace;
    font-size: 42px;
    font-weight: 700;
    color: {WHITE_OFF};
    letter-spacing: 0.05em;
    text-shadow: 0 0 14px alpha({WHITE_OFF}, 0.55),
                 0 0 28px alpha({WHITE_OFF}, 0.27);
}}
.clock-colon       {{ color: {WHITE_OFF}; }}
.clock-colon-dim   {{ color: {WHITE_OFF}; opacity: 0.4; }}
.clock-secs {{
    font-family: "JetBrains Mono", monospace;
    font-size: 18px;
    color: {GREY_LIGHT};
}}
.clock-day {{
    font-family: "Inter Display", cursive;
    font-size: 22px;
    color: {GREY_LIGHT};
    text-shadow: 0 0 8px alpha({GREY_LIGHT}, 0.40);
    letter-spacing: 0.04em;
}}
.clock-date {{
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    color: {GREY_LIGHT};
    letter-spacing: 0.10em;
}}
.wx-glyph {{
    font-size: 36px;
    color: {WHITE_OFF};
    text-shadow: 0 0 12px alpha({WHITE_OFF}, 0.55);
}}
.wx-temp {{
    font-family: "JetBrains Mono", monospace;
    font-size: 34px;
    font-weight: 700;
    color: {WHITE_OFF};
    text-shadow: 0 0 10px alpha({WHITE_OFF}, 0.40);
}}
.wx-unit {{
    font-family: "JetBrains Mono", monospace;
    font-size: 16px;
    color: {GREY_LIGHT};
}}
.wx-label {{
    font-family: "Inter Display", cursive;
    font-size: 17px;
    color: {WHITE_OFF};
    letter-spacing: 0.02em;
}}
.wx-stats {{
    font-family: "JetBrains Mono", monospace;
    font-size: 10px;
    color: {GREY_LIGHT};
    letter-spacing: 0.05em;
}}
.wx-loc {{
    font-family: "Inter Display", cursive;
    font-size: 15px;
    color: {GREY_LIGHT};
    letter-spacing: 0.03em;
}}
.cal-month {{
    font-family: "Inter Display", cursive;
    font-size: 20px;
    color: {WHITE_OFF};
    text-shadow: 0 0 8px alpha({WHITE_OFF}, 0.34);
    letter-spacing: 0.04em;
}}
.cal-dow {{
    font-family: "JetBrains Mono", monospace;
    font-size: 9px;
    color: alpha({WHITE_OFF}, 0.66);
    letter-spacing: 0.18em;
}}
.cal-day {{
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    color: {WHITE_OFF};
    padding: 3px 0;
}}
.cal-day-today {{
    font-family: "Inter Display", cursive;
    font-size: 14px;
    font-weight: 800;
    color: #0f1420;
    background: radial-gradient(circle at 35% 35%, {WHITE_OFF}, {WHITE_OFF} 80%);
    border-radius: 50%;
    box-shadow: 0 0 12px {WHITE_OFF}, 0 0 20px alpha({WHITE_OFF}, 0.40);
    min-width: 22px;
    min-height: 22px;
    padding: 2px;
}}
.notif-title {{
    font-family: "Inter Display", cursive;
    font-size: 15px;
    letter-spacing: 0.03em;
}}
.notif-time {{
    font-family: "JetBrains Mono", monospace;
    font-size: 8px;
    color: {GREY_LIGHT};
    letter-spacing: 0.10em;
}}
.notif-body {{
    font-size: 10px;
    color: {GREY_LIGHT};
}}
.notif-glyph {{
    font-size: 14px;
}}
.np-textarea {{
    font-family: "Inter Display", cursive;
    font-size: 18px;
    letter-spacing: 0.02em;
    color: {WHITE_OFF};
    background: rgba(0, 0, 0, 0.55);
    border: 1px dashed alpha({GREY_LIGHT}, 0.27);
    border-radius: 4px;
    padding: 10px 13px;
}}
.np-textarea text {{
    background: transparent;
    color: {WHITE_OFF};
}}
.np-textarea:focus {{
    border-color: alpha({GREY_LIGHT}, 0.66);
    box-shadow: inset 0 0 16px alpha({GREY_LIGHT}, 0.13),
                0 0 18px alpha({GREY_LIGHT}, 0.27);
}}
.pw-section {{
    border: 1px dashed alpha({WHITE_OFF}, 0.27);
    border-radius: 4px;
    background: alpha({WHITE_OFF}, 0.04);
    padding: 9px 11px;
}}
.pw-gen-label {{
    font-family: "Inter Display", cursive;
    font-size: 15px;
    color: {WHITE_OFF};
}}
.pw-gen-len {{
    font-family: "JetBrains Mono", monospace;
    font-size: 8px;
    color: alpha({WHITE_OFF}, 0.55);
    letter-spacing: 0.18em;
}}
.pw-gen-preview {{
    font-family: "JetBrains Mono", monospace;
    font-size: 12px;
    color: {WHITE_OFF};
    background: rgba(0, 0, 0, 0.55);
    padding: 6px 9px;
    border: 1px dashed alpha({WHITE_OFF}, 0.34);
    border-radius: 3px;
    letter-spacing: 0.02em;
}}
.pw-row {{
    border: 1px dashed alpha({WHITE_OFF}, 0.20);
    background: rgba(0, 0, 0, 0.35);
    border-radius: 3px;
    padding: 6px 9px;
}}
.pw-row-site {{
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    color: {WHITE_OFF};
    letter-spacing: 0.04em;
}}
.pw-row-user {{
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    color: {GREY_LIGHT};
}}
.pw-row-pass {{
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    color: {WHITE_OFF};
}}
.pw-row-pass-hidden {{
    color: {GREY_LIGHT};
}}
checkbutton {{
    color: {GREY_LIGHT};
    font-family: "JetBrains Mono", monospace;
    font-size: 9px;
    letter-spacing: 0.08em;
}}
scale trough {{
    background: rgba(8, 12, 20, 0.20);
    border-radius: 2px;
    min-height: 4px;
}}
scale highlight {{
    background: {WHITE_OFF};
    border-radius: 2px;
}}
scale slider {{
    background: {WHITE_OFF};
    border: 1px solid {WHITE_OFF};
    box-shadow: 0 0 10px alpha({WHITE_OFF}, 0.55);
    min-width: 12px;
    min-height: 12px;
    border-radius: 50%;
}}
""")
    for name in ("pink", "cyan", "purple", "gold", "green", "orange", "red", "mono"):
        css += _card_css(name, PALETTE[name])

    # System Pulse metric labels
    css += f"""
.pulse-metric-title {{
    font-family: "JetBrains Mono", monospace;
    font-size: 9px;
    font-weight: 700;
    color: {PALETTE['dim']};
    letter-spacing: 0.22em;
}}
.pulse-metric-value {{
    font-family: "JetBrains Mono", monospace;
    font-size: 11px;
    color: {PALETTE['text']};
}}
"""
    return css


def install_css():
    provider = Gtk.CssProvider()
    provider.load_from_data(build_css().encode("utf-8"))
    display = Gdk.Display.get_default()
    if display is not None:
        Gtk.StyleContext.add_provider_for_display(
            display, provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

# ── palette guard (rev r13) ─────────────────────────────────────────
try: assert_no_forbidden(build_css(), __file__)
except Exception as _e: import sys; sys.stderr.write(str(_e)+chr(10))
