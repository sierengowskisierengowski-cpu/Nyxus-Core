# NYXUS Theme Reference — "DARK MIRROR"

> Single source-of-truth for every color, font, and effect token used across
> the NYXUS desktop (EWW bars/menus, GTK apps, Hyprland, login/lock). Worker-B
> owns this file (Phase 5.1). Phase 2 (login/lock) consumes the accent + surface
> tokens documented in [§8](#8-tokens-for-phase-2-loginlock).

Aesthetic in one line: **deep-space triple-black glass, pink/magenta + purple
neon accent, white glow, a Rolls-Royce starlight twinkle motif**, with the
current wallpaper (`nyxus-graffiti-space.png`) as the single background reference
for every surface.

---

## 1. Where tokens live (source of truth)

| Layer | File(s) | Owns |
|-------|---------|------|
| **Monochrome / surface palette** | `~/.config/eww/nyxus-palette.css` **and** `~/.nyxus/nyxus_palette.py` | White→grey ramp, triple-black surfaces, glows, hairlines, shadows, blur, radii, fonts. Edited **in lockstep** — the `.css` and `.py` are NOT generated from each other. |
| **Hypr palette mirror** | `~/.config/hypr/nyxus-palette.css` | Identical copy of the eww palette css so Hyprland-side consumers `@import` the same tokens. |
| **Live accent** | `~/.config/nyxus/accent.json` → `nyxus-apply-accent` → `~/.config/eww/accent.scss` (`$nyxus-accent-*`), `_nyxus_accent.scss`, GTK `@define-color accent_*`, `hyprlock-accent.conf` | The 4 accent slots (primary/secondary/warn/ok). Follows the wallpaper. **Do not hand-edit** the generated `accent.scss` / GTK accent block — change `accent.json` and re-run `nyxus-apply-accent`. |
| **Fixed HUD neon family** | `~/.config/eww/eww.scss.source` header (`$neon-*`) mirrors `nyxus_palette.py` `HUD_*` | Preset-independent neon hues used by monitoring widgets. |

**Rule:** app CSS must `@import` the palette and reference the `@define-color`
names (or `$nyxus-accent-*` / `$neon-*` SCSS vars). Never hard-code hex inline.
Python apps `import` `nyxus_palette` instead of literal hex.

---

## 2. Monochrome ramp + surfaces (LOCKED, preset-independent)

CSS `@define-color` name (eww/GTK) / `nyxus_palette.py` constant / value:

### Primary ramp
| CSS name | Python | Value | Use |
|----------|--------|-------|-----|
| `nyx_white` | `WHITE_PURE` | `#ffffff` | rim highlight, focused caret, hover halo |
| `nyx_white_off` | `WHITE_OFF` | `#e8edf5` | primary text |
| `nyx_grey_light` | `GREY_LIGHT` | `#c8ccd6` | secondary text |
| `nyx_grey_mid` | `GREY_MID` | `#9aa0ad` | disabled / hint text |
| `nyx_grey_tertiary` | `GREY_TERTIARY` | `#6a6e78` | ghost text |
| `nyx_ink_faded` | `INK_FADED` | `#0a0a0a` | rim shadow stop |
| `nyx_ink_black` | `INK_BLACK` | `#000000` | selection fg, deepest shadow |

### Triple-black surface stack (elevation)
| CSS name | Python | Value | Elevation |
|----------|--------|-------|-----------|
| `nyx_black_smoke` | `BLACK_SMOKE` | `rgba(14,14,22,0.55)` | base / bars / panels (most blur shows through) |
| `nyx_black_ink` | `BLACK_INK` | `rgba(8,8,14,0.78)` | raised cards / pebbles / buttons |
| `nyx_black_void` | `BLACK_VOID` | `rgba(0,0,0,0.92)` | popovers / tooltips / modals / active |

Legacy aliases (same values): `nyx_glass_dark`/`GLASS_DARK`,
`nyx_glass_deeper`/`GLASS_DEEPER`, `nyx_glass_deepest`/`GLASS_DEEPEST`.

EWW HUD deep-void fills (in `eww.scss.source`, mirror `nyxus_palette.py`):
`$void-card` = `rgba(7,5,14,0.93)` (card fill), `$void-deep` = `rgba(5,1,13,0.97)`
(root sheet), `HUD_VOID` = `rgba(5,1,13,0.97)`, `HUD_CARD_BG` = `rgba(7,5,14,0.93)`.

### Glow / hairline / shadow
| CSS name | Value | Use |
|----------|-------|-----|
| `nyx_glow_soft` | `rgba(255,255,255,0.45)` | soft white glow on wordmarks |
| `nyx_glow_bright` | `rgba(255,255,255,0.85)` | bright white glow (sparingly) |
| `nyx_hairline_white` | `rgba(255,255,255,0.10)` | 1px card border |
| `nyx_hairline_ink` | `rgba(0,0,0,0.45)` | 1px hover border |
| `nyx_shadow_active` | `rgba(0,0,0,0.65)` | focused window shadow |
| `nyx_shadow_inactive` | `rgba(0,0,0,0.20)` | unfocused window shadow |

### Semantic aliases (preferred in app CSS)
`nyx_text`→white_off, `nyx_text_dim`→grey_light, `nyx_text_ghost`→grey_tertiary,
`nyx_bg`→smoke, `nyx_bg_hover`→ink, `nyx_bg_popover`→void,
`nyx_border`→hairline_white, `nyx_caret`→white, `nyx_select_bg`→grey_light,
`nyx_select_fg`→ink_black.

---

## 3. Accent tokens (LIVE — follow the wallpaper)

Four slots, applied everywhere by `nyxus-apply-accent`. Current active preset is
`wallpaper`:

| Slot | SCSS var | GTK | Wallpaper value | Meaning |
|------|----------|-----|-----------------|---------|
| primary | `$nyxus-accent-primary` | `@accent_color` | **`#7949f2`** (purple) | primary accent, brand, focus |
| secondary | `$nyxus-accent-secondary` | — | **`#ff2667`** (magenta/pink) | data readouts, signal, rims |
| warn | `$nyxus-accent-warn` | — | **`#ffb026`** (gold) | warnings / highlights |
| ok | `$nyxus-accent-ok` | — | **`#26ffb7`** (mint) | ok / tertiary refraction |

Derived soft/deep tints (auto-follow the preset), defined in `eww.scss.source`:
`$accent-primary-soft` = `mix(#fff, primary, 42%)`, `$accent-secondary-soft`
= `mix(#fff, secondary, 45%)`, `$accent-ok-soft`, `$accent-warn-soft`,
`$accent-primary-deep` = `mix(#000, primary, 30%)`.

**Pipeline:** `accent.json` (presets + `active`) → `nyxus-apply-accent [preset]`
rewrites `accent.scss`, the GTK `/* nyxus-accent-begin … end */` block, and
`hyprlock-accent.conf`, then substitutes old→new hex across all registered
consumers from a canonical PRISM baseline in `~/.config/nyxus/accent-baseline/`,
recompiles `eww.css`, and live-reloads eww/hypr/dunst/swaync/cava.
Presets available: `prism, aurora, ember, verdant, violet, rose, ice, noir,
wallpaper`.

> Because `eww.scss.source` is variable-driven (`@import "_nyxus_accent"`), theme
> edits use `$nyxus-accent-*` and never raw preset hex — so any accent swap keeps
> the DARK MIRROR structure intact.

---

## 4. Fixed HUD neon family (preset-independent)

Monitoring widgets use a stable neon set so graphs read consistently regardless
of accent. In `eww.scss.source` (mirror `nyxus_palette.py` `HUD_PALETTE`):

| SCSS var | Value | Monitoring use |
|----------|-------|----------------|
| `$neon-orange` | `#ff7849` | fans / power |
| `$neon-green` | `#6dffcf` | network |
| `$neon-blue` | `#4d9fff` | GPU / bluetooth |
| `$neon-red` | `#ff4d6b` | critical / music / danger |
| `$neon-cyan` | `#ff2667` | legacy HOME-station hue (== secondary) |

HUD hue map (`hud_tile`/graph widgets): CPU = pink (primary), RAM = purple (ok),
GPU = blue, TEMP = orange, FAN = orange, NET-down = green, NET-up = secondary.

`HUD_NEONS` (Python, extended set for multi-series charts): `#ff4994 #26ff39
#26ffb7 #ff8b26 #6dffcf #ff7ae5 #66efff #c084fc #ffce85`.

---

## 5. Fonts — "GRAFFITI TYPE SYSTEM"

Ships in `~/.local/share/fonts/nyxus`. The GRAFFITI block must stay **LAST** in
the SCSS cascade. EWW must be **restarted** (not reloaded) to pick up new fonts.

| Role | Font | Python | Where |
|------|------|--------|-------|
| Titles / brand / button labels | **Permanent Marker** | `FONT_GRAFFITI` | hub/card headers, wordmarks, spray labels (`.hud-spray-*`) |
| Dates / subtitles / hints | **Caveat** | `FONT_SCRIPT` | greetings, flourishes, sub-labels — sized **~1.5×** the px of the sans it replaces |
| Hero clocks / gauges | **Orbitron** | `FONT_TECH` | big clock numerals, gauge numbers |
| Data readouts | **JetBrainsMono Nerd Font** | `FONT_MONO` | bar metrics, graph values, mono stamps, Nerd-Font glyphs |
| UI body | **Inter / Inter Display** | `FONT_UI` / `FONT_DISPLAY` | general labels, sliders |

Glyphs: use Font Awesome / Nerd-Font **codepoints** (not literal `:glyph ""`
strings, which can silently blank). Keep bar-label `letter-spacing` **≤ 0.14em**
(more makes GTK ellipsize to `NYX…`).

---

## 6. Effects & shared mixins

### Radii / spacing (`eww.scss.source` + `nyxus_palette.py`)
`$radius-sm` 8px, `$radius-md` 12px, `$radius-lg` 14px, `$radius-xl` 16px;
Python `RADIUS_CARD` 14, `RADIUS_PILL` 12, `RADIUS_INPUT` 10, `HAIRLINE_PX` 1,
`BORDER_PX` 2.

### Motion
`$ease-apple` = `cubic-bezier(0.23,1,0.32,1)`, `$ease-glass` =
`cubic-bezier(0.16,1,0.2,1)`; `$t-fast` 200ms, `$t-med` 280ms, `$t-slow` 350ms.

### Blur / opacity (Hyprland, `nyxus_palette.py`)
`BLUR_SIZE` 14, `BLUR_PASSES` 4, `BLUR_BRIGHTNESS` 0.92, `BLUR_VIBRANCY` 0.18,
`BLUR_NOISE` 0.06; `WIN_OPACITY_FOCUSED` 0.92, `WIN_OPACITY_UNFOCUSED` 0.78.

### Signature mixins (`eww.scss.source`)
- **`obsidian-vessel($hue,$strength)`** — the bar-pill/tile DNA: deep obsidian
  fill + fog texture, 1px accent hairline, 2px solid accent top-rule, colored
  outer glow, ink drop-shadow, inner vignette. `obsidian-vessel-hover`,
  `obsidian-press` complete the set.
- **`flyout-glass($hue,$strength)`** — lighter frosted obsidian for flyout cards
  so the cosmic art breathes through; `flyout-glass-hover` for hover.
- **HUD card family** (`nyxus_palette.py` `hud_card_css`/`hud_header_css`): near-
  black card, 1px dashed neon border + 2px solid neon top-rule, neon bloom.

### Animated FX drivers (streamed into inline `:style`, GTK ignores @keyframes)
| Driver | Stream var | Effect |
|--------|-----------|--------|
| `neon-flicker.sh` | `NEONFLICK` | rare neon-tube flicker on wordmarks |
| `prism-anim.sh` | `PRISM` | rotating rim gradient + breathing glow on bar borders |
| `starlight-anim.sh` | `STARLIGHT` `{f,tw}` | fiber-optic **starfield twinkle** (16 frames) — see §7 |
| `fog-swirl.sh` | `FOG` | trapped fog drift inside pill vessels |
| `starfield-lock-anim.sh` | `STARFIELD` | fullscreen lock/screensaver twinkle |

`NYXUS_BAR_FX=off` in `nyxus.conf` freezes all bar FX at zero CPU.

---

## 7. Starfield / twinkle motif (Rolls-Royce starlight headliner)

Recurring background motif on every "deep" surface. Implemented as pre-rendered
twinkle PNG frames swapped by `starlight-anim.sh` (`STARLIGHT.f`, 0–15) layered
under a translucent void fill so stars appear to breathe.

Assets (`~/.config/eww/assets/`, regen via `gen-starlight-assets.py`):
`starlight-strip.png` / `-top.png` / `-rail.png` (static bases),
`starlight-twinkle-{strip,top,rail}-{0..15}.png` (animated frames),
`starfall-backdrop-card.png` (960×640 card starfield),
`starfield-lock-*` (fullscreen lock frames).

Applied on: bar backgrounds, the Hub, fullscreen overlays (dashboard/deepcore/
mission/powermenu/cheatsheet), and flyout panels — via the `starfield-veil`
class + a `${STARLIGHT.f}` top background-image layer (screen-blended so it sits
over the panel fill without blocking clicks). Keep it **subtle** (low-opacity
veil), not noisy.

---

## 8. Tokens for Phase 2 (login/lock)

Phase 2 owns hyprlock/SDDM styling; consume these tokens so login matches DARK
MIRROR. Accent is exposed to hyprlock via generated `~/.config/hypr/hyprlock-accent.conf`:

```
$nyxus_accent_rgba   = rgba(121, 73, 242, 1.0)   # primary #7949f2
$nyxus_accent_glow   = rgba(121, 73, 242, 0.45)
$nyxus_accent_dim    = rgba(121, 73, 242, 0.75)
$nyxus_accent_faint  = rgba(121, 73, 242, 0.20)
$nyxus_accent2_rgba  = rgba(255, 38, 103, 1.0)   # secondary #ff2667
$nyxus_accent2_glow  = rgba(255, 38, 103, 0.45)
$nyxus_accent2_dim   = rgba(255, 38, 103, 0.75)
```

Recommended login/lock surface tokens:
- Backdrop: the wallpaper nebula + fullscreen starfield (`starfield-lock-base.png`
  + `starfield-lock-twinkle-{0..15}.png`, driver `starfield-lock-anim.sh`).
- Login box: frosted smoked glass = `rgba(5,2,11,0.78)` fill, 1px
  `rgba(121,73,242,0.32)` border, 2px `rgba(121,73,242,0.62)` top-rule, blur
  behind (Hyprland blur 14/4).
- Text: `#e8edf5` primary, `#c8ccd6` secondary, `#6a6e78` hints.
- Fonts: Permanent Marker (Nyxus wordmark), Orbitron (clock), Inter (fields),
  Caveat (greeting, ~1.5×).

> Brief item **5.3 (theme login/lock) is intentionally left unchecked here** —
> owned by Phase 2, which should consume the tokens above.

---

## 9. Hard constraints (violating these silently breaks the bars)

1. **SCSS must be PURE ASCII.** Any non-ASCII char (bullets, em-dashes,
   ellipses, curly quotes — even in comments) makes Sass emit `@charset "UTF-8"`,
   which EWW's GTK CSS parser rejects → the whole theme drops to grey. After
   compiling, `grep -n '@charset' ~/.config/eww/eww.css` MUST return nothing.
2. **No web-CSS props GTK rejects:** `justify-content`, `align-items`,
   `flex-direction`, `text-align`, `display:flex`, `width:100%`, `margin:0 auto`.
   The compile step strips these defensively.
3. **Bar stacking:** horizontal bars (`bar-top`, `bar-bottom`) use
   `:stacking "bottom"`; vertical rails (`bar-left`, `bar-right`) use `"fg"`.
   Never move bar-top/bottom to `"fg"` (x-drift against the rails' exclusive
   zones).
4. **Floating island inset:** `margin: 0 12px` on `.bar-bottom`/`.bar-top` with a
   100%-width surface — never a `<100%` geometry width.
5. **Bar open order:** `bar-bottom bar-top bar-left bar-right` (from
   `nyxus.conf` `NYXUS_EWW_BARS`) so full-width bars claim monitor width before
   the rails' exclusive zones exist.
6. **Restart eww for new fonts** (`eww kill; eww daemon; eww open-many …`) — a
   reload does not re-scan fonts.
7. **GRAFFITI TYPE SYSTEM block stays LAST** in the SCSS cascade.

---

## 10. Changing the theme safely

1. Edit `~/.config/eww/eww.scss.source` (ASCII only). Monochrome via
   `@import`ed palette names / `$neon-*`; accent via `$nyxus-accent-*`.
2. `~/.config/eww/scripts/compile-eww-css.sh` (Sass `--no-charset` → strips web
   props → `eww.css`).
3. `grep -n '@charset' ~/.config/eww/eww.css` → must be empty.
4. `eww kill; eww daemon; eww open-many bar-bottom bar-top bar-left bar-right`.
5. `eww active-windows` → all four present and themed (not grey); spot-check
   flyouts open.
6. Palette hex change? Edit **both** `nyxus-palette.css` and `nyxus_palette.py`
   in lockstep, then mirror the css to every consumer (`nyxus-audit-sync.sh`
   step 3).
7. Accent change? Edit `accent.json`, run `nyxus-apply-accent` — never hand-edit
   generated accent files.

---

## 11. Shipped signature components (current reality · rev 2026-07-15)

The DARK MIRROR tokens above drive these live surfaces. All are shipped and
verified; none are placeholders.

| Component | Where | Notes |
|-----------|-------|-------|
| **The Hub** | `eww.yuck` `nyxus_hub_layout`; `nyxus-hub-launch` / `nyxus-hub-close` / `nyxus-hub-apps` / `nyxus-hub-search` | Redesigned full-screen launcher/command surface: NYXUS/ALL app toggle, search, now-playing, and a STATIONS footer switcher (OP..ED, from `stations.json`) + power actions. Closed by `nyxus-hub-close` and by the global `Escape` / `Super+Shift+Escape` binds. |
| **Station rail** | `eww.yuck` `workspaces_rail` / `station_pill` | Left rail = HOME `◈` + station pills OP/FG/GH/PL/WV/CR/MS/SC/BL/ED, hue-tinted per station, driven by `~/.config/nyxus/stations.json`. Matches Hyprland workspace identity 1-10 (see NYXUS_STATUS station reconciliation). |
| **Saucer center clock + music** | `eww.yuck` `.saucer-*` classes; `nyxus-nowplaying` | UFO-saucer center clock on `bar-bottom`; flips to a source-agnostic MPRIS now-playing readout when any player is active. |
| **NYXUS PULSE** | `nyxus-pulsed` / `nyxus-beat*`; `~/.config/nyxus/pulse-cava.conf`, `cava.conf` | Cava-driven audio-reactive beat feed used by bar FX / visualizers. |
| **HOME dashboard** | `~/.nyxus/nyxus-home/` (GTK4, workspace name:0) | Command deck: clock, weather, SYSTEM CORE rings + per-core bars, JETT AI EDR, HONEYPOT GRID, MUSIC DECK, NETWORK, Fans/Storage/Calendar/Notepad/Processes/Notifications/Password. Builds its own `CosmicSceneArea` backdrop — it pre-arms the `nyxus_chrome` guard so the shared present-hook doesn't re-wrap (and blank) its overlay. |
| **Matrix screensaver** | `~/.nyxus/nyxus_matrix_saver.py`; `nyxus-screensaver` | Idle/lock-adjacent matrix-rain saver in the neon palette. |
| **hyprlock (UFO art)** | `~/.config/hypr/hyprlock.conf` + `hyprlock-accent.conf`; `assets/nyxus-hyprlock-ufo.png` | Lock screen over the UFO art + fullscreen starfield; consumes the generated accent tokens (§8). |
| **Branded splash** | `eww/splash.yuck` + `.splash-*` in `eww.scss.source`; `assets/nyxus-splash-brand.png` | Session-start curtain = full-bleed graffiti "NYXUS HYPRLAND" brand art with top/bottom scrim for legible boot text. Pre-scaled to the panel resolution because the compile step strips `background-size`. |
| **Brand art set** | `~/.config/eww/assets/nyxus-brand-*.png` | `nyxus`, `sierengowski`, `hyprland`, `nyxus-hyprland` graffiti wordmarks on nebula brick/wet-pavement scenes — the source for the splash backdrop and available for hero/branding surfaces. |

### Overlay safety (LOCKED)

Every EWW overlay/flyout/fullscreen window is `:focusable false`. This is a
**hard rule** — a focusable overlay previously created a keyboard trap that
forced reboots. Never set any overlay back to `:focusable true`.
