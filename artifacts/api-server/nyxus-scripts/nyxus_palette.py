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
#  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
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
    "GLASS_DARK": GLASS_DARK, "GLASS_DEEPER": GLASS_DEEPER,
    "GLASS_DEEPEST": GLASS_DEEPEST,
    "HAIRLINE_WHITE": HAIRLINE_WHITE, "HAIRLINE_INK": HAIRLINE_INK,
    "SHADOW_INK_ACTIVE": SHADOW_INK_ACTIVE,
    "SHADOW_INK_INACTIVE": SHADOW_INK_INACTIVE,
    "RADIUS_CARD": RADIUS_CARD, "RADIUS_PILL": RADIUS_PILL,
    "RADIUS_INPUT": RADIUS_INPUT,
    "HAIRLINE_PX": HAIRLINE_PX, "BORDER_PX": BORDER_PX,
    "FONT_UI": FONT_UI, "FONT_MONO": FONT_MONO, "FONT_DISPLAY": FONT_DISPLAY,
}

def format_css(tpl: str) -> str:
    """Substitute {WHITE_OFF}, {GLASS_DARK}, etc. with palette values.

    CSS literal braces must be doubled in the template ({{ }})."""
    return tpl.format_map(_PALETTE_DICT)


__all__ = [
    "WHITE_PURE", "WHITE_OFF", "GREY_LIGHT", "GREY_MID", "GREY_TERTIARY",
    "INK_FADED", "INK_BLACK",
    "GLASS_DARK", "GLASS_DEEPER", "GLASS_DEEPEST",
    "HAIRLINE_WHITE", "HAIRLINE_INK",
    "RIM_GRADIENT_135", "RIM_GRADIENT_INACTIVE_135",
    "SHADOW_INK_ACTIVE", "SHADOW_INK_INACTIVE",
    "WIN_OPACITY_FOCUSED", "WIN_OPACITY_UNFOCUSED",
    "BLUR_SIZE", "BLUR_PASSES", "BLUR_BRIGHTNESS", "BLUR_VIBRANCY", "BLUR_NOISE",
    "RADIUS_CARD", "RADIUS_PILL", "RADIUS_INPUT", "HAIRLINE_PX", "BORDER_PX",
    "FONT_UI", "FONT_MONO", "FONT_DISPLAY",
    "MAX_DEFAULT_W", "MAX_DEFAULT_H",
    "hex_to_rgba_tuple", "rgba_str", "assert_no_forbidden",
    "format_css", "FORBIDDEN",
]
