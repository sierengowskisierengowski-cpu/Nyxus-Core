# NYXUS — Legacy Visual System Reference

This document preserves superseded visual specifications for historical
reference only. **Do NOT use these rules in new work** unless the user
explicitly reverts the active lock.

The current locked spec (DARK MIRROR · TRIPLE-BLACK LAYERED, rev r14)
lives in `replit.md` under "Visual System". Each section below names
which active spec replaced it.

---

## DARK MIRROR · UNIFIED FROSTED GLASS (rev 2026-05-07 r13)

**Status:** Superseded by TRIPLE-BLACK LAYERED (r14, 2026-05-09).
The single dark-glass tier is now split into three layered shades
(`nyx_black_smoke` / `nyx_black_ink` / `nyx_black_void`).

**System-wide active glow (rev r13):** Hyprland window borders use the
DARK MIRROR rim-light gradient (white `#ffffff` → off-white `#e8edf5` →
light grey `#c8ccd6` → faded black `#0a0a0a` → ink `#000000`, 135°,
animated 240-frame slow rotation). This is the SOLE source of "active
glow" anywhere in the system. Apps no longer draw their own borders,
glows, headerbars, or chrome animations. The terminal in particular is
a bare VTE widget on dark glass — every visual frame around any window
comes from Hyprland.

**Standalone duplicates removed (rev r13):** `nyxus_notepad.py` and
`nyxus_weather.py` standalone scripts were deleted. The rich GTK4
tarball editions (`nyxus-notepad.tgz`, `nyxus-weather.tgz`) are the
sole survivors; install.sh extracts them via the existing tarball
pipeline and they create their own `.desktop` entries
(`io.nyxus.notepad.desktop`, `io.nyxus.weather.desktop`).

**Apps + flyout (rev 2026-05-07 r12 — replaces EMBOSSED CREAM PAPER for apps):**
All 11 GTK4 apps (godsapp, home, intel, notepad, passwords, phantom, sage,
shield, start, studio, weather) and the flyout (panel) shared one
unified DARK MIRROR look enforced centrally by `nyxus_chrome.py` CHROME_CSS
loaded at `Gtk.STYLE_PROVIDER_PRIORITY_USER` (overrides every per-app
provider — no app code changes needed). Per-app neon palettes (card-pink,
card-cyan, card-gold, btn-primary-*, phantom @nyx_purple/pink/gold, etc.)
were all collapsed to the same monochrome glass.

- **Window root**: fully transparent — Hyprland blur paints the wallpaper.
- **Panels / cards / frames / headerbars**: `rgba(8,12,20,0.55)` dark glass
  with `rgba(255,255,255,0.10)` white hairline border + 14px radius.
- **Inputs / hovered cards**: `rgba(15,20,32,0.72)` deeper glass.
- **Tooltips / popovers / dropdowns**: `rgba(5,7,12,0.82–0.96)` deepest glass.
- **Text**: `#e8edf5` primary off-white, `#c8ccd6` secondary, `#6a6e78`
  tertiary, `#ffffff` only on hover halos + selected pip.
- **Hyprland active border**: pure white → off-white `#e8edf5` → black
  gradient at 135° (starlight rim-light fading into ink). Inactive border
  is the same gradient at low alpha.
- **Hyprland blur**: size 14, 4 passes, brightness 0.92 (darkens the
  wallpaper behind the dark glass), vibrancy 0.18, noise 0.06.
- **Hyprland window opacity**: 0.92 focused / 0.78 unfocused, applied
  uniformly to every NYXUS class (`org.nyxus.*`, `nyxus-*`, the 11 apps,
  the flyout) via `nyxus-hyprland-opacity.conf`.
- **No gold, no pink, no cyan, no green, no purple anywhere in apps**.
  Monochrome only. Every accent is white / off-white / black.

**Waybar (unchanged from rev 2026-05-06v):**
The waybar shells, pebbles, beads, ticker, plaques, and tooltips remained
**DARK FROSTED GLASS** — translucent near-black `rgba(8,12,20,0.58)` shells
with darker blue-black pebbles `rgba(15,20,32,0.72)`, light text `#e8edf5`,
cool silver-white starlight halos `rgba(230,240,255, …)` on hover. **NO
GOLD anywhere** in the waybar — silver/cool-white only. Workspaces appear
ONLY on the left bar. The OWL signature lives on the bottom bar
modules-right next to Panel.

The wallpaper is the **black-hole / cosmic ink swirl**
(`nyxus-ink-swirl.png`, 2560×1396, mostly black with silver-white wisps).

---

## EMBOSSED CREAM PAPER (rev 2026-05-06v)

**Status:** Superseded by DARK MIRROR for apps (r12, 2026-05-07) and by
DARK GLASS WAYBAR for the bars (r12, same revision).

The wallpaper is the **black-hole / cosmic ink swirl** (`nyxus-ink-swirl.png`,
2560×1396, mostly black with silver-white wisps). The waybar shells, pebbles,
beads, ticker, plaques, and tooltips are **DARK FROSTED GLASS** —
translucent near-black `rgba(8,12,20,0.58)` shells with darker blue-black
pebbles `rgba(15,20,32,0.72)`, light text `#e8edf5`, and cool silver-white
starlight halos `rgba(230,240,255, …)` on hover. **NO GOLD anywhere** in
the waybar — silver/cool-white only. Engraved text-shadow direction is
flipped for dark surfaces: dark above (`0 -1px 0 rgba(0,0,0,0.65)`),
light below (`0 1px 0 rgba(230,240,255,0.20-0.30)`). Workspaces appear
ONLY on the left bar. The OWL signature lives on the bottom bar
modules-right next to Panel.

Apps and dialogs (NOT the waybar) keep the EMBOSSED CREAM PAPER chrome
described below. The dark glass treatment applies exclusively to the
floating waybar modules.

- **Aesthetic**: Cream-on-cream tone-on-tone embossed stationery. Deeply
  carved sculptural plaques. Hand-cast nameplates. Engraved labels.
  Reference: bottom waybar (`waybar-style.css`) is the canonical example.
- **Palette** (use these hex values everywhere — no other colors):
  - Cream base: `#f5f3ef` (wallpaper letterbox, bar background)
  - Cream raised: `#fbfaf6` (tile/pill surface)
  - Cream highlight: `#ffffff` (hover, top inset highlight)
  - Cream shadow stack: `#ebe8e2` → `#ddd9d3` (slab layers behind bars)
  - Charcoal pencil ink: `#1a1816` (all primary text)
  - Pencil-light: `#58524c` (secondary text, sublabels)
  - Pencil-faint: `#9e948a` (disabled, dimmed)
  - Charcoal border alphas: `rgba(26,24,22, 0.18 / 0.22 / 0.32 / 0.45)`
  - Workspace identity stripes (only place color is allowed): pink
    `rgba(236, 72, 153, …)`, orange `rgba(234,126, 60, …)`, gold
    `rgba(212,167, 58, …)`, green `rgba(106,168,114, …)`, blue
    `rgba( 90,138,171, …)`, purple `rgba(138,106,170, …)` — at 0.55
    inactive / 0.95 active.
  - **Warm gold jewelry accent** (locked 2026-05-06f): `#d4a73a` is
    permitted as a *jewelry-scale* accent ONLY — wordmarks
    (NYXUS / SIERENGOWSKI / hyprland), focused-workspace ring,
    notification dot, "now playing" indicator. Always paired with a
    soft warm glow `0 0 12px rgba(212,167,58,0.55)` and an engraved
    text-shadow. **Never** as a fill on surfaces, buttons, bars, or
    icons. If in doubt, leave it cream. Gold is the ONLY second hue
    permitted in the system; no other accent colors will ever be
    added.
- **Fonts**:
  - `Architects Daughter` (or `Caveat` fallback) — handwritten labels,
    NYXUS wordmarks, app titles, hand-feel accents.
  - `Inter` — system text, stats, sublabels, UI body.
  - `JetBrains Mono` — workspace numbers, code, monospace data.
  - **Never** use the old Caveat-only or neon-pixel font stacks.
- **Emboss recipe** (every raised tile / pill / card / plaque):
  - 1px charcoal border at 0.22 alpha (deeper plaques: 2px at 0.32)
  - `inset 1px 1px 0 rgba(255,255,255,0.95)` — top-left highlight
  - `inset -1px -1px 0 rgba(26,24,22,0.08)` — bottom-right shadow
  - `inset 0 -2px 0 rgba(26,24,22,0.06)` — bottom rim depth
  - `0 2px 5px rgba(26,24,22,0.14)` — outer drop shadow
  - Bigger plaques scale all values up proportionally.
- **Engraved text recipe** (every label):
  - `text-shadow: 0 1px 0 rgba(255,255,255,0.85), 0 -1px 0 rgba(26,24,22,0.18)`
- **Waybar shell = invisible** (locked 2026-05-06): both top + bottom
  bars use `background: rgba(0,0,0,0); border:none; box-shadow:none`.
  No bar substrate, no slab depth on the bar itself — the wallpaper
  shows through. Modules float independently as cream "clay" buttons.
  Hyprland needs `windowrule = noborder, ^(waybar)$` +
  `windowrule = noshadow, ^(waybar)$` to keep the float clean.
- **Floating neomorphic button recipe** (every waybar module):
  - `background: #fbfaf6; margin: 8px 5px; padding: 6px 14px;`
  - `border-radius: 12px;`
  - Dual outer shadow: `4px 4px 10px rgba(26,24,22,0.18)` (dark, lower-right)
    + `-3px -3px 8px rgba(255,255,255,0.90)` (light, upper-left)
  - Inset bevel rims: `inset 1px 1px 0 rgba(255,255,255,0.95)` +
    `inset -1px -1px 0 rgba(26,24,22,0.06)`
  - Engraved text-shadow on every label.
  - Active workspace = INVERTED (inset shadows instead of outset) =
    "pressed-in" feel, same cream, no color accent.
- **Slab/nameplate depth** (for Python GTK4 app cards / dialogs / panels
  — NOT the waybar): stack 2 cream slabs behind, offsets `6px/12px`
  (standard) / `8px/16px` (deeper), with progressively darker rim
  shadows + a soft outer drop.
- **Tile texture fills**: cards / headerbars get the `frost-tile-grid`
  (triangle tessellation, 220px repeat) or `frost-tile-glyphs` (runic
  wall, 180×320) repeating background-image at 0.85-0.92 cream-overlay
  alpha. Substituted at runtime via `__NYX_TILE_*__` placeholders in
  `nyxus_chrome.py`.
- **Forbidden**: neon colors, glow effects, gradient backgrounds, dark
  mode, sharp 90° corners under 8px radius, sans-serif-only mockups,
  raster icons that aren't nerd-font / Phosphor / hand-drawn.
