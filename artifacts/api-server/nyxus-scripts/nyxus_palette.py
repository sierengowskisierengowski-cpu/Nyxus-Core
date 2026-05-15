# ============================================================
#  NYXUS PALETTE — single source of truth for DARK MIRROR
#  (LOCKED · rev 2026-05-14 r15 — CREAM + HANDWRITTEN)
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
#  rev r15 (2026-05-14):
#    - Replaced grey/gold/purple drift with the user-locked contract:
#      triple-black + off-white + CREAM warm accent.
#    - Two display fonts now first-class: FONT_HAND (Caveat,
#      handwritten — used for badges, brand marks, accent labels)
#      and FONT_BODY (Inter — used for chrome text). FONT_MONO
#      (JetBrains Mono Nerd) stays for code/numbers/glyphs.
#    - Corners are now near-sharp slightly rounded (3px) — old
#      14/12/10 radii ramp deprecated; legacy aliases kept for
#      compatibility but all resolve to 3.
#    - GLOW + TILT + HANDDRAWN tokens added so any widget can opt
#      into the system-wide effect vocabulary by name.
#
#  © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
# ============================================================

# ── PRIMARY RAMP (off-white text on triple-black) ──────────────────────────
WHITE_PURE        = "#ffffff"   # rim-light highlight, focused caret, hover halos
WHITE_OFF         = "#e8edf5"   # primary text on dark surfaces
GREY_LIGHT        = "#c8ccd6"   # secondary text
GREY_MID          = "#9aa0ad"   # tertiary text, hint text
GREY_TERTIARY     = "#6a6e78"   # disabled / ghost text
INK_FADED         = "#0a0a0a"   # faded matte black (rim shadow stop)
INK_BLACK         = "#000000"   # pure black (selection fg, deepest shadow)

# ── CREAM WARM ACCENT (rev r15) ─────────────────────────────────────────────
# The single brand accent. Used on focus rings, selection, brand marks,
# active workspace, "alive" states. Three temperatures:
#   CREAM        — primary  (warmest, highest weight)
#   CREAM_SOFT   — hover / glow halo   (~12% lighter)
#   CREAM_DEEP   — pressed / dim badge (~22% darker)
CREAM             = "#f4ead5"
CREAM_SOFT        = "#fbf3e2"
CREAM_DEEP        = "#c4b491"
CREAM_GLOW_15     = "rgba(244, 234, 213, 0.15)"
CREAM_GLOW_28     = "rgba(244, 234, 213, 0.28)"
CREAM_GLOW_45     = "rgba(244, 234, 213, 0.45)"
CREAM_EDGE_55     = "rgba(244, 234, 213, 0.55)"

# Backward-compat: NYXUS_GOLD was the old name for the warm accent.
# Code still importing NYXUS_GOLD continues to work and now reads cream.
NYXUS_GOLD        = CREAM

# ── COPPER WARM SECONDARY (rev r16 · 2026-05-15) ────────────────────────────
# The Eclipse halo's warmer "edge of the corona" — used for selection
# stripes, active window borders, hover glows on dark surfaces. Sits
# one octave warmer than CREAM and reads against triple-black without
# ever crossing into red/orange. CREAM is the diffuse light, COPPER is
# the rim-light. Use COPPER ONLY for accent edges / active state /
# selection — never for body text or large fill areas.
COPPER            = "#b8865a"   # primary copper accent
COPPER_SOFT       = "#d4a978"   # hover halo (12% lighter)
COPPER_DEEP       = "#8a6444"   # pressed / dim badge (22% darker)
COPPER_GLOW_18    = "rgba(184, 134, 90, 0.18)"
COPPER_GLOW_32    = "rgba(184, 134, 90, 0.32)"
COPPER_GLOW_55    = "rgba(184, 134, 90, 0.55)"
COPPER_EDGE_88    = "rgba(184, 134, 90, 0.88)"

# ── DESTRUCTIVE / SIGNAL (RESERVED) ─────────────────────────────────────────
# Only legitimate non-cream chroma in the system. Use ONLY for
# destructive confirmations, alarm/critical state. Never decorative.
DANGER_RED        = "#d96b6b"   # softer than the prior #ff4d6b strobe
DANGER_BG_18      = "rgba(217, 107, 107, 0.18)"

# ── TRIPLE-BLACK SURFACE STACK ──────────────────────────────────────────────
# Three layered shades of black. Each tier is distinct but harmonious —
# together they "pop" without color, just depth. Use them by elevation:
#   smoke = base/bars/panels       (lightest, most blur shows through)
#   ink   = raised cards/pebbles   (mid)
#   void  = popovers/active/modals (deepest, maximum pop)
BLACK_SMOKE       = "rgba(14, 14, 22, 0.55)"
BLACK_INK         = "rgba(8, 8, 14, 0.78)"
BLACK_VOID        = "rgba(0, 0, 0, 0.92)"

# Solid (non-alpha) fallbacks for surfaces that can't blur.
BLACK_SMOKE_SOLID = "#0e0e16"
BLACK_INK_SOLID   = "#08080e"
BLACK_VOID_SOLID  = "#000000"

# Backward-compat aliases — legacy names map to new tiers.
GLASS_DARK        = BLACK_SMOKE
GLASS_DEEPER      = BLACK_INK
GLASS_DEEPEST     = BLACK_VOID

# ── WHITE GLOW HALO (use sparingly on wordmarks / key labels) ──────────────
GLOW_SOFT         = "rgba(255, 255, 255, 0.45)"
GLOW_BRIGHT       = "rgba(255, 255, 255, 0.85)"

# ── HAIRLINE BORDERS ────────────────────────────────────────────────────────
HAIRLINE_WHITE    = "rgba(255, 255, 255, 0.10)"  # 1px white border on cards
HAIRLINE_INK      = "rgba(0, 0, 0, 0.45)"        # 1px black border on hovers
HAIRLINE_CREAM    = "rgba(244, 234, 213, 0.22)"  # 1px cream border on focus

# ── HYPRLAND ACTIVE-BORDER RIM-LIGHT (cream-tinted at 135deg) ──────────────
RIM_GRADIENT_135 = (
    "rgba(f4ead5ff) rgba(e8edf5ee) rgba(c8ccd6cc) "
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

# ── RADII / SPACING (rev r15: near-sharp slightly rounded) ──────────────────
# All radii now resolve to 3px — closer to sharp than rounded, but never
# fully square. Kept as named constants so future tightenings only need
# to touch this file.
RADIUS_TIGHT    = 3
RADIUS_CARD     = 3   # was 14 (rev r13)
RADIUS_PILL     = 3   # was 12 (rev r13)
RADIUS_INPUT    = 3   # was 10 (rev r13)
RADIUS_PANEL    = 3   # bars/eww panels (rev r15)
HAIRLINE_PX     = 1
BORDER_PX       = 2

# ── FONTS ───────────────────────────────────────────────────────────────────
# Three-font stack (rev r15):
#   FONT_HAND   — Caveat: handwritten display, used SPARINGLY on badges,
#                 brand marks, accent labels, hand-drawn callouts.
#   FONT_BODY   — Inter:  primary chrome / body / row text.
#   FONT_MONO   — JetBrains Mono Nerd Font: code, numbers, glyphs, status.
# Backward-compat: FONT_UI alias maps to FONT_BODY; FONT_DISPLAY maps to
# FONT_HAND so older callers do the right thing automatically.
FONT_HAND       = "Caveat"
FONT_BODY       = "Inter"
FONT_MONO       = "JetBrains Mono Nerd Font"
FONT_UI         = FONT_BODY      # back-compat
FONT_DISPLAY    = FONT_HAND      # back-compat

FONT_STACK_BODY = ('"Inter", "Inter Display", "DejaVu Sans", '
                   'system-ui, sans-serif')
FONT_STACK_HAND = ('"Caveat", "Caveat Brush", "Comic Neue", '
                   '"DejaVu Sans", cursive')
FONT_STACK_MONO = ('"JetBrains Mono Nerd Font", "JetBrains Mono", '
                   '"Cascadia Code", "DejaVu Sans Mono", monospace')

# ── EFFECT TOKENS (rev r15) ─────────────────────────────────────────────────
# Used by .nyx-glow / .nyx-tilt / .nyx-handdrawn / .nyx-scramble
# helper classes in gtk.css and eww.scss. Keep them here so the look
# is system-wide consistent.
GLOW_BOX_HOVER  = ("0 0 16px rgba(244, 234, 213, 0.28), "
                   "0 0 4px rgba(255, 255, 255, 0.18)")
GLOW_BOX_FOCUS  = ("0 0 22px rgba(244, 234, 213, 0.45), "
                   "0 0 6px rgba(255, 255, 255, 0.28)")
TILT_LEFT_DEG   = -1.5
TILT_RIGHT_DEG  =  1.5
HANDDRAWN_DASH  = "3 4"           # dasharray for sketchy borders

# ── DEFAULT WINDOW SIZE CLAMPS ──────────────────────────────────────────────
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

# ── FORBIDDEN EVERYWHERE (sanity check helper, rev r15) ────────────────────
# Apps may call assert_no_forbidden(text) at import time on their CSS to
# fail loudly if they accidentally reintroduce a banned color.
# rev r15 added: the prior cycle's purple/cyan/gold drift is now banned
# along with all the older neon escapees.
FORBIDDEN = (
    # Sprint A purple/cyan drift (now off-brand vs cream lock)
    "#a06bff", "#3ad8ff",
    # Old eww gold/violet drift
    "#d4b87a", "#e8d4a0", "#8a6f3a", "#8b6f3a", "#e8c66b",
    # Old grey-as-accent gtk drift (kept as TEXT but never as ACCENT)
    # — these aren't banned because they're legit text colors.
    # Old neon strays from earlier revs
    "#ff5500", "#ff00ff", "#cc44ff", "#22d3ee", "#d4a73a", "#ec4899",
    "#f0e8fa", "#a855f7", "#39ff14", "#ffff00", "#0088ff", "#8800ff",
    "#cc00ff", "#ff3344", "#ff4d6b", "#ff4d6d", "#ffd700", "#6fffb0",
    "#00aaff", "#bf5cff", "#f5f3ef", "#fbfaf6",
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
_PALETTE_DICT = {
    "WHITE_PURE": WHITE_PURE, "WHITE_OFF": WHITE_OFF,
    "GREY_LIGHT": GREY_LIGHT, "GREY_MID": GREY_MID,
    "GREY_TERTIARY": GREY_TERTIARY,
    "INK_FADED": INK_FADED, "INK_BLACK": INK_BLACK,
    "CREAM": CREAM, "CREAM_SOFT": CREAM_SOFT, "CREAM_DEEP": CREAM_DEEP,
    "CREAM_GLOW_15": CREAM_GLOW_15, "CREAM_GLOW_28": CREAM_GLOW_28,
    "CREAM_GLOW_45": CREAM_GLOW_45, "CREAM_EDGE_55": CREAM_EDGE_55,
    "NYXUS_GOLD": NYXUS_GOLD,
    "COPPER": COPPER, "COPPER_SOFT": COPPER_SOFT, "COPPER_DEEP": COPPER_DEEP,
    "COPPER_GLOW_18": COPPER_GLOW_18, "COPPER_GLOW_32": COPPER_GLOW_32,
    "COPPER_GLOW_55": COPPER_GLOW_55, "COPPER_EDGE_88": COPPER_EDGE_88,
    "DANGER_RED": DANGER_RED, "DANGER_BG_18": DANGER_BG_18,
    "BLACK_SMOKE": BLACK_SMOKE, "BLACK_INK": BLACK_INK, "BLACK_VOID": BLACK_VOID,
    "BLACK_SMOKE_SOLID": BLACK_SMOKE_SOLID,
    "BLACK_INK_SOLID":   BLACK_INK_SOLID,
    "BLACK_VOID_SOLID":  BLACK_VOID_SOLID,
    "GLOW_SOFT": GLOW_SOFT, "GLOW_BRIGHT": GLOW_BRIGHT,
    "GLASS_DARK": GLASS_DARK, "GLASS_DEEPER": GLASS_DEEPER,
    "GLASS_DEEPEST": GLASS_DEEPEST,
    "HAIRLINE_WHITE": HAIRLINE_WHITE, "HAIRLINE_INK": HAIRLINE_INK,
    "HAIRLINE_CREAM": HAIRLINE_CREAM,
    "SHADOW_INK_ACTIVE": SHADOW_INK_ACTIVE,
    "SHADOW_INK_INACTIVE": SHADOW_INK_INACTIVE,
    "RADIUS_TIGHT": RADIUS_TIGHT, "RADIUS_CARD": RADIUS_CARD,
    "RADIUS_PILL": RADIUS_PILL, "RADIUS_INPUT": RADIUS_INPUT,
    "RADIUS_PANEL": RADIUS_PANEL,
    "HAIRLINE_PX": HAIRLINE_PX, "BORDER_PX": BORDER_PX,
    "FONT_HAND": FONT_HAND, "FONT_BODY": FONT_BODY, "FONT_MONO": FONT_MONO,
    "FONT_UI": FONT_UI, "FONT_DISPLAY": FONT_DISPLAY,
    "FONT_STACK_BODY": FONT_STACK_BODY,
    "FONT_STACK_HAND": FONT_STACK_HAND,
    "FONT_STACK_MONO": FONT_STACK_MONO,
    "GLOW_BOX_HOVER": GLOW_BOX_HOVER,
    "GLOW_BOX_FOCUS": GLOW_BOX_FOCUS,
    "TILT_LEFT_DEG": TILT_LEFT_DEG,
    "TILT_RIGHT_DEG": TILT_RIGHT_DEG,
    "HANDDRAWN_DASH": HANDDRAWN_DASH,
}

def format_css(tpl: str) -> str:
    """Substitute {WHITE_OFF}, {GLASS_DARK}, etc. with palette values.

    CSS literal braces must be doubled in the template ({{ }})."""
    return tpl.format_map(_PALETTE_DICT)


__all__ = [
    "WHITE_PURE", "WHITE_OFF", "GREY_LIGHT", "GREY_MID", "GREY_TERTIARY",
    "INK_FADED", "INK_BLACK",
    "CREAM", "CREAM_SOFT", "CREAM_DEEP",
    "CREAM_GLOW_15", "CREAM_GLOW_28", "CREAM_GLOW_45", "CREAM_EDGE_55",
    "NYXUS_GOLD",
    "COPPER", "COPPER_SOFT", "COPPER_DEEP",
    "COPPER_GLOW_18", "COPPER_GLOW_32", "COPPER_GLOW_55", "COPPER_EDGE_88",
    "DANGER_RED", "DANGER_BG_18",
    "BLACK_SMOKE", "BLACK_INK", "BLACK_VOID",
    "BLACK_SMOKE_SOLID", "BLACK_INK_SOLID", "BLACK_VOID_SOLID",
    "GLOW_SOFT", "GLOW_BRIGHT",
    "GLASS_DARK", "GLASS_DEEPER", "GLASS_DEEPEST",
    "HAIRLINE_WHITE", "HAIRLINE_INK", "HAIRLINE_CREAM",
    "RIM_GRADIENT_135", "RIM_GRADIENT_INACTIVE_135",
    "SHADOW_INK_ACTIVE", "SHADOW_INK_INACTIVE",
    "WIN_OPACITY_FOCUSED", "WIN_OPACITY_UNFOCUSED",
    "BLUR_SIZE", "BLUR_PASSES", "BLUR_BRIGHTNESS", "BLUR_VIBRANCY", "BLUR_NOISE",
    "RADIUS_TIGHT", "RADIUS_CARD", "RADIUS_PILL",
    "RADIUS_INPUT", "RADIUS_PANEL",
    "HAIRLINE_PX", "BORDER_PX",
    "FONT_HAND", "FONT_BODY", "FONT_MONO", "FONT_UI", "FONT_DISPLAY",
    "FONT_STACK_BODY", "FONT_STACK_HAND", "FONT_STACK_MONO",
    "GLOW_BOX_HOVER", "GLOW_BOX_FOCUS",
    "TILT_LEFT_DEG", "TILT_RIGHT_DEG", "HANDDRAWN_DASH",
    "MAX_DEFAULT_W", "MAX_DEFAULT_H",
    "hex_to_rgba_tuple", "rgba_str", "assert_no_forbidden",
    "format_css", "FORBIDDEN",
]
