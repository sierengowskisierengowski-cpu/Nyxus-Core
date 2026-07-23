# ============================================================
#  NYXUS PALETTE — single source of truth for DARK MIRROR
#  (LOCKED · rev 2026-05-07 r13)
#
#  Every NYXUS Python app MUST import from this module instead of
#  hard-coding hex values. Every CSS file MUST @import the sibling
#  `nyxus-palette.css` and use the @define-color names.
#
#  When the visual lock changes, EDIT THIS FILE ONLY and re-publish —
#  every app picks up the new palette automatically on next launch.
#
#  Forbidden: introducing new colors here without explicit user approval.
#  Forbidden: per-app palettes anywhere else in the codebase.
#
#  © 2026 Joseph A. Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================

# ── PRIMARY HEX ─────────────────────────────────────────────────────────────
# White / off-white / grey ramp — the entire system reads from these 5.
WHITE_PURE        = "#ffffff"   # rim-light highlight, focused caret, hover halos
WHITE_OFF         = "#e8edf5"   # primary text, primary accent
GREY_LIGHT        = "#c8ccd6"   # secondary text, secondary accent, light rim
GREY_MID          = "#9aa0ad"   # mid-grey (rare — disabled/hint text)
GREY_TERTIARY     = "#6a6e78"   # tertiary text, ghost text
INK_FADED         = "#0a0a0a"   # faded matte black (rim shadow stop)
INK_BLACK         = "#000000"   # pure black (selection fg, deepest shadow)

# ── TRIPLE-BLACK SURFACE STACK (rev r14 · 2026-05-09) ──────────────────────
# Three layered shades of black. Each tier is distinct but harmonious —
# together they "pop" without color, just depth. Use them by elevation:
#   smoke = base/bars/panels       (lightest, most blur shows through)
#   ink   = raised cards/pebbles   (mid)
#   void  = popovers/active/modals (deepest, maximum pop)
BLACK_SMOKE       = "rgba(14, 14, 22, 0.55)"
BLACK_INK         = "rgba(8, 8, 14, 0.78)"
BLACK_VOID        = "rgba(0, 0, 0, 0.92)"

# Backward-compat aliases — legacy names map to new tiers.
GLASS_DARK        = BLACK_SMOKE
GLASS_DEEPER      = BLACK_INK
GLASS_DEEPEST     = BLACK_VOID

# ── WHITE GLOW ACCENT (use sparingly on wordmarks/key labels) ──────────────
GLOW_SOFT         = "rgba(255, 255, 255, 0.45)"
GLOW_BRIGHT       = "rgba(255, 255, 255, 0.85)"

# ── HAIRLINE BORDERS ────────────────────────────────────────────────────────
HAIRLINE_WHITE    = "rgba(255, 255, 255, 0.10)"  # 1px white border on cards
HAIRLINE_INK      = "rgba(0, 0, 0, 0.45)"        # 1px black border on hovers

# ── HYPRLAND ACTIVE-BORDER RIM-LIGHT ────────────────────────────────────────
# Used by hyprland.conf col.active_border. 5-stop gradient at 135deg.
RIM_GRADIENT_135 = (
    "rgba(ffffffff) rgba(e8edf5ee) rgba(c8ccd6cc) "
    "rgba(0a0a0a99) rgba(000000ff) 135deg"
)
RIM_GRADIENT_INACTIVE_135 = (
    "rgba(e8edf522) rgba(c8ccd611) rgba(00000044) 135deg"
)

# ── DROP SHADOW ─────────────────────────────────────────────────────────────
SHADOW_INK_ACTIVE   = "rgba(0, 0, 0, 0.65)"   # focused window
SHADOW_INK_INACTIVE = "rgba(0, 0, 0, 0.20)"   # unfocused window

# ── HYPRLAND OPACITY ────────────────────────────────────────────────────────
WIN_OPACITY_FOCUSED   = 0.92
WIN_OPACITY_UNFOCUSED = 0.78

# ── BLUR (Hyprland) ─────────────────────────────────────────────────────────
BLUR_SIZE       = 14
BLUR_PASSES     = 4
BLUR_BRIGHTNESS = 0.92
BLUR_VIBRANCY   = 0.18
BLUR_NOISE      = 0.06

# ── RADII / SPACING ─────────────────────────────────────────────────────────
RADIUS_CARD     = 14
RADIUS_PILL     = 12
RADIUS_INPUT    = 10
HAIRLINE_PX     = 1
BORDER_PX       = 2

# ── FONTS ───────────────────────────────────────────────────────────────────
FONT_UI         = "Inter"
FONT_MONO       = "JetBrains Mono"
FONT_DISPLAY    = "Inter Display"   # fallback to Inter

# ── DEFAULT WINDOW SIZE CLAMPS ──────────────────────────────────────────────
# Enforced system-wide by nyxus_chrome.py monkey-patch.
MAX_DEFAULT_W = 700
MAX_DEFAULT_H = 480

# ── LIVE ACCENT (PRISM pipeline · rev 2026-07-09) ───────────────────────────
# The desktop accent is owned by ~/.config/nyxus/accent.json and applied by
# nyxus-apply-accent (which regenerates eww/GTK CSS). Python apps get the
# SAME source of truth here: the active preset is read at import time, so
# every launch reflects whatever `nyxus accent set <name>` last applied.
# Fallback is the canonical PRISM preset — never white/grey.
_ACCENT_FALLBACK = {
    "primary":   "#ff2dad",
    "secondary": "#2bd2ff",
    "warn":      "#ffb84d",
    "ok":        "#7d3dff",
}

def _load_accent() -> dict:
    import json as _json
    import os as _os
    conf = _os.path.expanduser("~/.config/nyxus/accent.json")
    try:
        with open(conf, encoding="utf-8") as fh:
            data = _json.load(fh)
        preset = data.get("presets", {}).get(data.get("active", "prism"), {})
        out = dict(_ACCENT_FALLBACK)
        for key in out:
            val = preset.get(key)
            if isinstance(val, str) and len(val.lstrip("#")) == 6:
                out[key] = val if val.startswith("#") else "#" + val
        return out
    except Exception:
        return dict(_ACCENT_FALLBACK)

_ACCENT = _load_accent()
ACCENT_PRIMARY   = _ACCENT["primary"]
ACCENT_SECONDARY = _ACCENT["secondary"]
ACCENT_WARN      = _ACCENT["warn"]
ACCENT_OK        = _ACCENT["ok"]

def reload_accent() -> None:
    """Re-read accent.json (call after nyxus-apply-accent) and refresh the
    module-level ACCENT_* constants + the CSS template dict."""
    global ACCENT_PRIMARY, ACCENT_SECONDARY, ACCENT_WARN, ACCENT_OK, _ACCENT
    _ACCENT = _load_accent()
    ACCENT_PRIMARY   = _ACCENT["primary"]
    ACCENT_SECONDARY = _ACCENT["secondary"]
    ACCENT_WARN      = _ACCENT["warn"]
    ACCENT_OK        = _ACCENT["ok"]
    _PALETTE_DICT.update(
        ACCENT_PRIMARY=ACCENT_PRIMARY, ACCENT_SECONDARY=ACCENT_SECONDARY,
        ACCENT_WARN=ACCENT_WARN, ACCENT_OK=ACCENT_OK,
    )

# ── HUD VISUAL LANGUAGE (rev 2026-07-09 · from nyxus-home/style.py) ─────────
# The HOME HUD is the reference surface for every NYXUS window: near-black
# cards on rgba(5,1,13) void, 1px neon hairlines + solid accent top rules,
# JetBrains Mono small-caps micro-labels, dim-gray mono metadata, subtle
# neon bloom. These helpers are THE shared source — apps compose their CSS
# from them instead of duplicating card blocks.
#
# The first four hues track the live accent.json preset; the rest are the
# fixed HUD neon family (nyxus-home PALETTE / NEONS).
def _hud_palette() -> dict:
    return {
        "pink":   ACCENT_PRIMARY,
        "cyan":   ACCENT_SECONDARY,
        "gold":   ACCENT_WARN,
        "purple": ACCENT_OK,
        "green":  "#7dff5e",
        "orange": "#ff7849",
        "blue":   "#4d9fff",
        "red":    "#ff4d6b",
        "mono":   WHITE_OFF,
    }

HUD_PALETTE = _hud_palette()
HUD_NEONS = ["#ff2dad", "#39ff14", "#2bd2ff", "#ff8a1e", "#ffe600",
             "#ff7ae5", "#66efff", "#7d3dff", "#e367ff"]
HUD_VOID       = "rgba(5, 1, 13, 0.97)"    # window background
HUD_CARD_BG    = "rgba(7, 5, 14, 0.93)"    # card background
HUD_CARD_HOVER = "rgba(9, 6, 18, 0.97)"
HUD_INPUT_BG   = "rgba(0, 0, 0, 0.45)"

# Graffiti type system (ships in ~/.local/share/fonts/nyxus):
#   Permanent Marker — spray-paint wordmarks / card headers
#   Caveat           — handwritten script greetings / flourishes
#   Orbitron         — chunky techno numerals (clock/gauge style)
FONT_GRAFFITI = "Permanent Marker"
FONT_SCRIPT   = "Caveat"
FONT_TECH     = "Orbitron"


def neon_flicker_css() -> str:
    """Just the neon-sign flicker keyframes + opt-in classes, for apps
    that keep their own stylesheet (e.g. nyxus_settings)."""
    return """
@keyframes nyx-neon-flicker {
    0%     { opacity: 1; }
    38.0%  { opacity: 1; }
    38.6%  { opacity: 0.42; }
    39.2%  { opacity: 0.95; }
    40.1%  { opacity: 0.30; filter: saturate(0.35) brightness(0.8); }
    40.9%  { opacity: 1;    filter: none; }
    61.0%  { opacity: 1; }
    61.5%  { opacity: 0.72; }
    62.2%  { opacity: 1; }
    85.0%  { opacity: 1; }
    85.5%  { opacity: 0.48; }
    86.2%  { opacity: 0.92; }
    87.0%  { opacity: 0.58; filter: saturate(0.45); }
    87.8%  { opacity: 1;    filter: none; }
    100%   { opacity: 1; }
}
.neon-flicker      { animation: nyx-neon-flicker 8s linear infinite; }
.neon-flicker-slow { animation: nyx-neon-flicker 13s linear infinite; }
"""


def hud_base_css(window_selector: str = "window") -> str:
    """Void background + generic HUD label classes shared by all apps."""
    return f"""
{window_selector} {{
    background: {HUD_VOID};
    color: {WHITE_OFF};
    font-family: "Inter Display", "{FONT_MONO}", sans-serif;
}}
.hud-tag {{
    font-family: "{FONT_MONO}", monospace;
    font-size: 9px;
    color: alpha({WHITE_OFF}, 0.66);
    letter-spacing: 0.28em;
}}
.hud-stamp {{
    font-family: "{FONT_MONO}", monospace;
    font-size: 8px;
    color: {GREY_TERTIARY};
    letter-spacing: 0.22em;
}}
.hud-dim {{
    font-family: "{FONT_MONO}", monospace;
    font-size: 9px;
    color: {GREY_MID};
    letter-spacing: 0.12em;
}}
.hud-value {{
    font-family: "{FONT_MONO}", monospace;
    font-weight: 700;
    color: {WHITE_OFF};
    text-shadow: 0 0 8px alpha({WHITE_OFF}, 0.35);
}}
scrollbar, scrollbar trough {{ background: transparent; }}
scrollbar slider {{
    background: alpha({WHITE_OFF}, 0.18);
    border-radius: 999px;
    min-width: 5px;
}}
/* graffiti voice — spray wordmarks, script flourishes, techno numerals */
.hud-script {{
    font-family: "{FONT_SCRIPT}", cursive;
    font-size: 26px;
    color: {WHITE_OFF};
    text-shadow: 0 0 14px alpha({WHITE_OFF}, 0.40),
                 0 0 28px alpha({WHITE_OFF}, 0.20);
}}
.hud-tech {{
    font-family: "{FONT_TECH}", "{FONT_MONO}", monospace;
    font-weight: 700;
    color: {WHITE_OFF};
    text-shadow: 0 0 14px alpha({WHITE_OFF}, 0.55),
                 0 0 28px alpha({WHITE_OFF}, 0.27);
}}
""" + neon_flicker_css()


def hud_header_css(name: str, color: str) -> str:
    """Neon section-header trio (glyph + small-caps title + laser rule),
    identical to the HUD ghost cards. Includes a spray-paint wordmark
    variant (.hud-spray-{name}) in the graffiti Permanent Marker voice."""
    return f"""
.hud-spray-{name} {{
    font-family: "{FONT_GRAFFITI}", cursive;
    font-size: 22px;
    color: {color};
    text-shadow: 0 0 10px alpha({color}, 0.70),
                 0 0 26px alpha({color}, 0.40),
                 0 0 48px alpha({color}, 0.20);
    letter-spacing: 0.03em;
}}
.hud-script-{name} {{
    font-family: "{FONT_SCRIPT}", cursive;
    font-size: 24px;
    color: {color};
    text-shadow: 0 0 12px alpha({color}, 0.55);
}}
.hud-glyph-{name} {{
    color: {color};
    font-size: 16px;
    text-shadow: 0 0 10px {color}, 0 0 18px alpha({color}, 0.55);
}}
.hud-title-{name} {{
    font-family: "{FONT_MONO}", monospace;
    font-size: 12px;
    font-weight: 700;
    color: {color};
    letter-spacing: 0.30em;
    text-shadow: 0 0 8px alpha({color}, 0.45);
}}
.hud-rule-{name} {{
    background: linear-gradient(to right,
        {color}, alpha({color}, 0.35), transparent);
    min-height: 1px;
}}
"""


def hud_card_css(name: str, color: str) -> str:
    """Near-black HUD card + button/input family in one neon hue —
    ported verbatim from nyxus-home style.py so every app matches."""
    return f"""
.hud-card-{name} {{
    background: {HUD_CARD_BG};
    border: 1px dashed alpha({color}, 0.75);
    border-top: 2px solid {color};
    border-radius: 8px;
    padding: 12px 14px;
    box-shadow: 0 0 18px alpha({color}, 0.34),
                0 6px 22px rgba(0,0,0,0.55),
                inset 0 0 24px rgba(0,0,0,0.18);
    transition: box-shadow 320ms ease, border-color 320ms ease;
}}
.hud-card-{name}:hover {{
    background: {HUD_CARD_HOVER};
    border-color: alpha({color}, 0.95);
    box-shadow: 0 0 30px alpha({color}, 0.55),
                0 10px 34px rgba(0,0,0,0.65),
                inset 0 0 24px rgba(0,0,0,0.18);
}}
.hud-htitle-{name} {{
    font-family: "Inter Display", cursive;
    font-size: 24px;
    font-weight: 700;
    color: {color};
    text-shadow: 0 0 8px alpha({color}, 0.40);
    letter-spacing: 0.02em;
}}
.hud-btn-{name} {{
    background: transparent;
    border: 1px solid alpha({color}, 0.34);
    color: {color};
    font-family: "{FONT_MONO}", monospace;
    font-size: 9px;
    letter-spacing: 0.18em;
    padding: 4px 9px;
    border-radius: 2px;
}}
.hud-btn-{name}:hover {{
    background: alpha({color}, 0.13);
    border-color: {color};
}}
.hud-btn-primary-{name} {{
    background: alpha({color}, 0.13);
    border: 1px solid {color};
    color: {color};
    font-family: "{FONT_MONO}", monospace;
    font-size: 10px;
    letter-spacing: 0.18em;
    font-weight: 700;
    padding: 6px 11px;
    border-radius: 3px;
    text-shadow: 0 0 6px alpha({color}, 0.55);
}}
.hud-btn-primary-{name}:hover {{
    background: alpha({color}, 0.25);
    box-shadow: 0 0 14px alpha({color}, 0.55);
}}
.hud-input-{name} {{
    background: {HUD_INPUT_BG};
    border: 1px dashed alpha({color}, 0.34);
    border-radius: 3px;
    color: {WHITE_OFF};
    padding: 5px 8px;
    font-family: "{FONT_MONO}", monospace;
    font-size: 11px;
}}
.hud-input-{name}:focus, .hud-input-{name}:focus-within {{
    border-color: {color};
    border-style: solid;
    box-shadow: 0 0 12px alpha({color}, 0.40);
}}
""" + hud_header_css(name, color)


def hud_css_bundle(window_selector: str = "window",
                   hues: tuple = ()) -> str:
    """Base + one card family per requested hue name (default: all)."""
    pal = _hud_palette()
    names = hues or tuple(pal.keys())
    css = hud_base_css(window_selector)
    for n in names:
        if n in pal:
            css += hud_card_css(n, pal[n])
    return css


def install_hud_css(css: str) -> bool:
    """Install app CSS at PRIORITY_USER + 1 so it outranks the universal
    nyxus_chrome glass layer (which loads at PRIORITY_USER and would
    otherwise silently flatten every HUD card back to monochrome —
    exactly how nyxus-home/style.py wins the cascade)."""
    try:
        import gi
        gi.require_version("Gtk", "4.0")
        from gi.repository import Gtk, Gdk
        display = Gdk.Display.get_default()
        if display is None:
            return False
        prov = Gtk.CssProvider()
        prov.load_from_data(css.encode("utf-8"))
        Gtk.StyleContext.add_provider_for_display(
            display, prov, Gtk.STYLE_PROVIDER_PRIORITY_USER + 1)
        return True
    except Exception:
        return False


# ── HELPERS ─────────────────────────────────────────────────────────────────
def hex_to_rgba_tuple(h: str, a: float = 1.0):
    """'#e8edf5' -> (0.91, 0.93, 0.96, 1.0). For Cairo / Gdk.RGBA fields."""
    h = h.lstrip("#")
    if len(h) == 6:
        return (int(h[0:2], 16) / 255.0,
                int(h[2:4], 16) / 255.0,
                int(h[4:6], 16) / 255.0,
                a)
    raise ValueError(f"bad hex: {h}")

def rgba_str(h: str, a: float = 1.0) -> str:
    """'#e8edf5', 0.5 -> 'rgba(232, 237, 245, 0.5)'. For CSS strings."""
    h = h.lstrip("#")
    return (f"rgba({int(h[0:2], 16)}, "
            f"{int(h[2:4], 16)}, "
            f"{int(h[4:6], 16)}, {a})")

# ── FORBIDDEN EVERYWHERE (sanity check helper) ──────────────────────────────
# Apps may call assert_no_forbidden(text) at import time on their CSS to
# fail loudly if they accidentally reintroduce a banned color.
FORBIDDEN = (
    "#ff5500", "#ff00ff", "#cc44ff", "#22d3ee", "#d4a73a", "#ec4899",
    "#f0e8fa", "#a855f7", "#39ff14", "#ffff00", "#0088ff", "#8800ff",
    "#cc00ff", "#ff3344", "#ff4d6d", "#ffd700", "#6fffb0", "#00aaff",
    "#bf5cff", "#f5f3ef", "#fbfaf6",
)

def assert_no_forbidden(text: str, source: str = "<inline>") -> None:
    low = text.lower()
    bad = [c for c in FORBIDDEN if c in low]
    if bad:
        raise RuntimeError(
            f"NYXUS palette violation in {source}: forbidden colors "
            f"{bad} — use nyxus_palette constants instead."
        )

# ── CSS TEMPLATE FORMATTER ──────────────────────────────────────────────────
# Apps that embed CSS as a Python string can use placeholders instead of
# hex literals. CSS braces must be doubled ({{ }}) inside the template.
#
#   CSS = format_css("""
#     window {{ background: {GLASS_DARK}; color: {WHITE_OFF}; }}
#     entry  {{ border: 1px solid {HAIRLINE_WHITE}; }}
#   """)
#
# Future palette changes propagate automatically — apps never need to be
# touched again.
_PALETTE_DICT = {
    "WHITE_PURE": WHITE_PURE, "WHITE_OFF": WHITE_OFF,
    "GREY_LIGHT": GREY_LIGHT, "GREY_MID": GREY_MID,
    "GREY_TERTIARY": GREY_TERTIARY,
    "INK_FADED": INK_FADED, "INK_BLACK": INK_BLACK,
    "BLACK_SMOKE": BLACK_SMOKE, "BLACK_INK": BLACK_INK, "BLACK_VOID": BLACK_VOID,
    "GLOW_SOFT": GLOW_SOFT, "GLOW_BRIGHT": GLOW_BRIGHT,
    "GLASS_DARK": GLASS_DARK, "GLASS_DEEPER": GLASS_DEEPER,
    "GLASS_DEEPEST": GLASS_DEEPEST,
    "HAIRLINE_WHITE": HAIRLINE_WHITE, "HAIRLINE_INK": HAIRLINE_INK,
    "SHADOW_INK_ACTIVE": SHADOW_INK_ACTIVE,
    "SHADOW_INK_INACTIVE": SHADOW_INK_INACTIVE,
    "RADIUS_CARD": RADIUS_CARD, "RADIUS_PILL": RADIUS_PILL,
    "RADIUS_INPUT": RADIUS_INPUT,
    "HAIRLINE_PX": HAIRLINE_PX, "BORDER_PX": BORDER_PX,
    "FONT_UI": FONT_UI, "FONT_MONO": FONT_MONO, "FONT_DISPLAY": FONT_DISPLAY,
    "ACCENT_PRIMARY": ACCENT_PRIMARY, "ACCENT_SECONDARY": ACCENT_SECONDARY,
    "ACCENT_WARN": ACCENT_WARN, "ACCENT_OK": ACCENT_OK,
}

def format_css(tpl: str) -> str:
    """Substitute {WHITE_OFF}, {GLASS_DARK}, etc. with palette values.

    CSS literal braces must be doubled in the template ({{ }})."""
    return tpl.format_map(_PALETTE_DICT)


__all__ = [
    "WHITE_PURE", "WHITE_OFF", "GREY_LIGHT", "GREY_MID", "GREY_TERTIARY",
    "INK_FADED", "INK_BLACK",
    "BLACK_SMOKE", "BLACK_INK", "BLACK_VOID",
    "GLOW_SOFT", "GLOW_BRIGHT",
    "GLASS_DARK", "GLASS_DEEPER", "GLASS_DEEPEST",
    "HAIRLINE_WHITE", "HAIRLINE_INK",
    "RIM_GRADIENT_135", "RIM_GRADIENT_INACTIVE_135",
    "SHADOW_INK_ACTIVE", "SHADOW_INK_INACTIVE",
    "WIN_OPACITY_FOCUSED", "WIN_OPACITY_UNFOCUSED",
    "BLUR_SIZE", "BLUR_PASSES", "BLUR_BRIGHTNESS", "BLUR_VIBRANCY", "BLUR_NOISE",
    "RADIUS_CARD", "RADIUS_PILL", "RADIUS_INPUT", "HAIRLINE_PX", "BORDER_PX",
    "FONT_UI", "FONT_MONO", "FONT_DISPLAY",
    "ACCENT_PRIMARY", "ACCENT_SECONDARY", "ACCENT_WARN", "ACCENT_OK",
    "reload_accent",
    "MAX_DEFAULT_W", "MAX_DEFAULT_H",
    "hex_to_rgba_tuple", "rgba_str", "assert_no_forbidden",
    "format_css", "FORBIDDEN",
    "HUD_PALETTE", "HUD_NEONS", "HUD_VOID", "HUD_CARD_BG",
    "HUD_CARD_HOVER", "HUD_INPUT_BG",
    "FONT_GRAFFITI", "FONT_SCRIPT", "FONT_TECH",
    "hud_base_css", "hud_header_css", "hud_card_css", "hud_css_bundle",
    "install_hud_css", "neon_flicker_css",
]
