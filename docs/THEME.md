# NYXUS Theme Reference — "ALIEN NEON"

> Single source-of-truth for every color, font, and effect token used across
> the NYXUS desktop (EWW bars/menus, GTK apps, Hyprland, login/lock).
> Login/lock consumes the accent + surface tokens documented in
> [§8](#8-tokens-for-phase-2-loginlock).
>
> **Fact-checked against `nyxus_palette.py`, `accent.json` and the shipped
> configs on 2026-07-30.** Four stale statements were corrected in place and are
> annotated inline so nobody re-derives them: the accent "follows the wallpaper"
> (it does not), §8 pointing at "DARK MIRROR", the `eww.scss.source` void-fill
> mirror claim, and §11's screensaver / hyprlock / brand-art rows.

> **Palette LOCKED 2026-07-23.** The single accent preset is `prism` and
> `follow_wallpaper` is **false**. The older "DARK MIRROR" / "OBSIDIAN PRISM"
> palette this file used to document was **purged** from the tree; its hexes are
> banned. History lives in [`legacy-visuals.md`](./legacy-visuals.md).

Aesthetic in one line: **urban-alien graffiti on deep-space triple-black glass —
violet + magenta neon, neon-green signal, white glow, a starlight twinkle
motif**, with `nyxus-urban-alien.png` as the single background reference for
every surface.

---

## 1. Where tokens live (source of truth)

| Layer | File(s) | Owns |
|-------|---------|------|
| **Monochrome / surface palette** | `~/.config/eww/nyxus-palette.css` **and** `~/.nyxus/nyxus_palette.py` | White→grey ramp, triple-black surfaces, glows, hairlines, shadows, blur, radii, fonts. Edited **in lockstep** — the `.css` and `.py` are NOT generated from each other. |
| **Hypr palette mirror** | `~/.config/hypr/nyxus-palette.css` | Identical copy of the eww palette css so Hyprland-side consumers `@import` the same tokens. |
| **Live accent** | `~/.config/nyxus/accent.json` → `nyxus-apply-accent` → `~/.config/eww/accent.scss` (`$nyxus-accent-*`), `_nyxus_accent.scss`, GTK `@define-color accent_*`, `hyprlock-accent.conf` | The 4 accent slots (primary/secondary/warn/ok). ⛔ **Does NOT follow the wallpaper** — `follow_wallpaper: false`, locked 2026-07-23 (this line said "Follows the wallpaper" until 2026-07-30; it was wrong and it contradicted §3 of this same file). **Do not hand-edit** the generated `accent.scss` / GTK accent block — change `accent.json` and re-run `nyxus-apply-accent prism`. |
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
| `nyx_white_off` | `WHITE_OFF` | `#eef2fa` | primary text (canon cool white) |
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

EWW HUD deep-void fills — `nyxus_palette.py` is canon:
`HUD_VOID` = `rgba(5,6,10,0.97)` (root sheet, from `VOID` `#05060a`),
`HUD_CARD_BG` = `rgba(7,8,14,0.93)` (card fill).

> ⚠ **`eww.scss.source` does not currently match these** (measured 2026-07-30):
> it declares `$void-deep: rgba(5,1,13,0.97)` and `$void-card: rgba(7,5,14,0.93)`.
> The two sets are visually indistinguishable near-blacks, so this is a
> bookkeeping divergence rather than a rendering bug — but it is a real
> divergence, and the earlier claim in this file that the SCSS "mirrors these"
> was false. `nyxus_palette.py` is the canon; the SCSS is what actually paints
> eww. Reconcile deliberately if you touch either, and note that `eww.css` has
> drifted ~3500 lines from `eww.scss.source`, so **do not recompile casually**.

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

## 3. Accent tokens (LOCKED — `prism` only)

Four slots, applied everywhere by `nyxus-apply-accent`. There is exactly **one**
preset and the accent does **not** follow the wallpaper:

| Slot | SCSS var | GTK | Value | Meaning |
|------|----------|-----|-------|---------|
| primary | `$nyxus-accent-primary` | `@accent_color` | **`#7d3dff`** (violet) | primary accent, brand, focus |
| secondary | `$nyxus-accent-secondary` | — | **`#ff2dad`** (magenta) | data readouts, signal, rims |
| warn | `$nyxus-accent-warn` | — | **`#ff8a1e`** (orange) | warnings / highlights |
| ok | `$nyxus-accent-ok` | — | **`#39ff14`** (neon green) | ok / tertiary refraction |

Derived soft/deep tints (defined in `eww.scss.source`):
`$accent-primary-soft` = `mix(#fff, primary, 42%)`, `$accent-secondary-soft`
= `mix(#fff, secondary, 45%)`, `$accent-ok-soft`, `$accent-warn-soft`,
`$accent-primary-deep` = `mix(#000, primary, 30%)`.

**Pipeline:** `accent.json` (`active` + `presets`) → `nyxus-apply-accent [preset]`
rewrites `accent.scss`, the GTK `/* nyxus-accent-begin … end */` block, and
`hyprlock-accent.conf`, then substitutes old→new hex across all registered
consumers from a canonical PRISM baseline in `~/.config/nyxus/accent-baseline/`,
recompiles `eww.css`, and live-reloads eww/hypr/dunst/swaync/cava.

> **`prism` is the only preset.** `aurora, ember, verdant, violet, rose, ice,
> noir, wallpaper` were **deleted** from `accent.json` on 2026-07-23 — do not
> reference them and do not re-add them. Wallpaper→accent extraction is what
> kept dragging the desktop off-theme; `follow_wallpaper: false` is deliberate
> and `nyxus-accent-from-wallpaper` is dev-only behind
> `NYXUS_ALLOW_WALLPAPER_ACCENT=1`.
>
> Unrelated uses of these words are fine and are NOT presets: the
> `NYXUS-Aurora` cursor theme, the eww "aurora curtain" CSS animation, and
> `nyxus-shader ember|noir` post-process filters.

## 4. Fixed HUD neon family (preset-independent)

Monitoring widgets use a stable neon set so graphs read consistently regardless
of accent. `nyxus_palette.py` is the canon; `eww.scss.source` mirrors it:

| SCSS var | Value | Monitoring use |
|----------|-------|----------------|
| `$neon-orange` | `#ff8a1e` | fans / power (== warn slot) |
| `$neon-green` | `#7dff5e` | network (lifted tint of `#39ff14`) |
| `$neon-blue` | `#2bd2ff` | GPU / bluetooth (== `CYAN_FIXED`) |
| `$neon-red` | `#ff2d55` | critical / music / danger (== `RED_FIXED`) |
| `$neon-cyan` | `#ff2d55` | legacy HOME-station hue (alias of red — historical) |

Fixed, preset-independent constants (`nyxus_palette.py`): `CYAN_FIXED` `#2bd2ff`,
`RED_FIXED` `#ff2d55`, `YELLOW_FIXED` `#ffe600`, `ORCHID` `#e367ff`,
`GREEN_OK` `#39ff14`, `VOID` `#05060a`.

`HUD_PALETTE` key → value (note the historical key names: `pink` is the violet
primary and `cyan` is the magenta secondary):
`pink` `#7d3dff` · `cyan` `#ff2dad` · `gold`/`orange` `#ff8a1e` ·
`purple` `#7d3dff` · `green` `#39ff14` · `blue` `#2bd2ff` · `red` `#ff2d55` ·
`orchid` `#e367ff` · `mono` `#eef2fa`.

`HUD_NEONS` (extended set for multi-series charts): `#7d3dff #ff2dad #39ff14
#2bd2ff #ff8a1e #ffe600 #e367ff #ff2d55`.

> Any Python app that hardcodes a HUD colour must mirror `HUD_PALETTE` exactly
> in its `except ImportError` fallback, or the app renders a near-miss palette
> whenever the import fails. Three of them had drifted this way.

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

Consume these tokens so login and lock match **ALIEN NEON**. (This paragraph said
"so login matches DARK MIRROR" until 2026-07-30 — a leftover from the purged
brand.) The live greeter is **greetd → `nyxus-greeter` → regreet under cage**;
SDDM is dormant. Accent is exposed to hyprlock via the generated
`~/.config/hypr/hyprlock-accent.conf`:

`hyprlock-accent.conf` **ships empty** (so `hyprlock.conf`'s `source =` resolves
on a fresh account) and is written by `nyxus-apply-accent` at runtime. With the
locked `prism` preset it generates:

```
$nyxus_accent_rgba   = rgba(125, 61, 255, 1.0)   # primary #7d3dff
$nyxus_accent_glow   = rgba(125, 61, 255, 0.45)
$nyxus_accent_dim    = rgba(125, 61, 255, 0.75)
$nyxus_accent_faint  = rgba(125, 61, 255, 0.20)
$nyxus_accent2_rgba  = rgba(255, 45, 173, 1.0)   # secondary #ff2dad
$nyxus_accent2_glow  = rgba(255, 45, 173, 0.45)
$nyxus_accent2_dim   = rgba(255, 45, 173, 0.75)
```

Recommended login/lock surface tokens:
- Backdrop: the urban-alien wallpaper + fullscreen starfield (`starfield-lock-base.png`
  + `starfield-lock-twinkle-{0..15}.png`, driver `starfield-lock-anim.sh`).
- Login box: frosted smoked glass = `rgba(5,6,10,0.78)` fill, 1px
  `rgba(125,61,255,0.32)` border, 2px `rgba(125,61,255,0.62)` top-rule, blur
  behind (Hyprland blur 14/4).
- Text: `#eef2fa` primary, `#c8ccd6` secondary, `#6a6e78` hints.
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

## 11. Shipped signature components (current reality · rev **2026-07-30**)

The ALIEN NEON tokens above drive these live surfaces. All are shipped and
verified; none are placeholders.

| Component | Where | Notes |
|-----------|-------|-------|
| **The Hub** | `eww.yuck` `nyxus_hub_layout`; `nyxus-hub-open` / `nyxus-hub-launch` / `nyxus-hub-close` / `nyxus-hub-apps` / `nyxus-hub-search` | Full-screen launcher/command surface: NYXUS/ALL app toggle, search, now-playing, a STATIONS footer switcher (from `stations.json`) + power actions. Opened via `nyxus-hub-open` (stashes+closes the bars so it maps truly fullscreen, restores on any failure). **`:stacking "fg"` (TOP) since 2026-07-30** — it was `overlay`, which meant anything it launched landed *behind* it and read as dead (gate `13ai`). Three independent escape routes: bare `Escape`, `Super+Shift+Escape` (bare `eww close nyxus-hub` first), and `Super+Ctrl+Shift+Escape` (`eww close-all` → `nyxus-eww-launch-safe`, touching no NYXUS script). **eww SIGKILLs a widget handler after 200 ms**, so every handler must background the slow half — `(nyxus-hub-close; X) &`, never `nyxus-hub-close; X` (gate `13ah`). `(eventbox :onclick "true")` blocks nothing and has been deleted; do not re-add it. |
| **Station rail** | `eww.yuck` `workspaces_rail` / `station_pill` | Left rail = HOME / START / 1-10, hue-tinted per station, driven by `~/.config/nyxus/stations.json`. Stations are OPS · FORGE · GHOST · PULSE · WAVE · CORE · MESH · SCRIBE · BIFROST · ARSENAL (9/10 were renamed from BLAST/EDGE on 2026-07-27). Named annex stations HOME / START / LAB live in `nyxus-stations-named.conf`; identity must stay identical across `stations.json` and `stations-hacker.json` — gate 13w asserts it. |
| **Saucer center clock + music** | `eww.yuck` `.saucer-*` classes; `nyxus-nowplaying` | UFO-saucer center clock on `bar-bottom`; flips to a source-agnostic MPRIS now-playing readout when any player is active. |
| **NYXUS PULSE** | `nyxus-pulsed` / `nyxus-beat*`; `~/.config/nyxus/pulse-cava.conf`, `cava.conf` | Cava-driven audio-reactive beat feed used by bar FX / visualizers. |
| **HOME dashboard** | eww `home-deck` window on the **HOME** station (`Super+Home`) | Command deck: clock, weather, SYSTEM CORE rings + per-core bars, JETT AI EDR, HONEYPOT GRID, MUSIC DECK, NETWORK, Fans/Storage/Calendar/Notepad/Processes/Notifications/Password. **The GTK4 `nyxus-home` app is DISABLED** (it rendered an empty window); the eww deck replaced it, opened/closed by `nyxus-home-deck` following the Hyprland socket. The old workspace `name:0` was renamed `name:HOME` because a numeric `name:0` resolves into Hyprland's SPECIAL range and was never visible. |
| **Screensaver** | `nyxus-screensaver` → **`nyxus_screensaver.py`** | Urban-alien idle saver (dimmed alien skyline behind a glass card, violet↔magenta breathing pulse), pinned to `NYXUS_SCREENSAVER_WALL` = `/usr/share/backgrounds/nyxus/nyxus-urban-alien.png`. Launched by hypridle at 300 s. The launcher falls through **three** payload locations (`~/.config/nyxus/` → `~/.nyxus/` → `/opt/nyxus/`) because a single hardcoded path meant the idle screen silently did nothing while hypridle reported success. Gate `13ua` asserts the whole chain. ⚠ **The matrix-rain saver (`nyxus_matrix_saver.py`) is RETIRED** — it still ships, and this table claimed until 2026-07-30 that it was what `nyxus-screensaver` launches. It is not. |
| **hyprlock** | `~/.config/hypr/hyprlock.conf` + `hyprlock-accent.conf` | Lock screen over **`/usr/share/backgrounds/nyxus/nyxus-urban-alien.png`** + fullscreen starfield; consumes the generated accent tokens (§8). *(Earlier revisions of this table said "over the UFO art / `assets/nyxus-hyprlock-ufo.png`" — that asset still exists in `~/.config/eww/assets/` and `hypr-walls/`, but `hyprlock.conf` has been pinned to the urban-alien hero since `e5c381d1`.)* Also renders weather, lock art and track chip/title/artist — all five of those widgets were **dead on every stick** until 2026-07-30 because they invoked their tools through an empty `~/.local/bin` (gate `13z`). |
| **Branded splash** | `eww/splash.yuck` + `.splash-*` in `eww.scss.source`; `~/.config/eww/assets/nyxus-splash-brand.png` | Session-start curtain = full-bleed graffiti "NYXUS HYPRLAND" brand art with top/bottom scrim for legible boot text. Pre-scaled to the panel resolution because the compile step strips `background-size`. |
| **Login (greetd + regreet)** | `/etc/greetd/regreet.css` + `regreet.toml`, staged from `nyxus-scripts/greetd/`; `nyxus-greeter` | The urban-alien hero is re-copied to `/var/cache/regreet/nyxus-login-bg.png` on **every** greeter start. The login card sits at `margin-left: 1360px` / `margin-right: 40px` (2026-07-30) and `nyxus-greeter` **rescales both margins for the detected panel** from `/sys/class/drm/*/modes`, because GTK4 CSS has no percentage margins and absolute pixels tuned for 1920 would push the card off a 1366-wide screen — a lockout. Gates `13ua` / `13ub`. |
| **NYXUS · POWER** | wlogout (`Super+Shift+E`) · eww `powermenu` (`Super+Escape`) · `nyxus_powermenu.py` (app menu) | **Three separate surfaces**, all now carrying the urban-alien art. wlogout was being un-themed at runtime by `nyxus-gen-backdrop` rewriting the first `background-image` url in its stylesheet on every wallpaper change; that rewrite is now opt-in to `starfall-backdrop.png` only. The eww overlay's scrim is `0.52/0.60` (was `0.76/0.82`); gate `13ub` fails if it goes back above `0.70`. |
| **Brand art set** | `~/.config/eww/assets/nyxus-brand-*.png` | Three wordmarks ship: `nyxus-brand-hyprland`, `nyxus-brand-nyxus-hyprland`, `nyxus-brand-sierengowski` — graffiti on nebula brick/wet-pavement scenes, the source for the splash backdrop. *(A standalone `nyxus-brand-nyxus.png` is listed in older revisions of this table but has never existed.)* |

### Overlay safety (LOCKED)

Two hard rules, both bought with hard resets:

1. **`:focusable true` on an eww window is a session-wide keyboard grab** in eww
   0.5. A focusable overlay previously created a keyboard trap that forced
   reboots.
2. **Never put a full-screen *input* surface on the `overlay` layer.** While one
   is mapped, nothing else on the desktop can be clicked, so anything it launches
   lands behind it and reads as dead. `nyxus-hub`, `dashboard`, `powermenu` and
   `cheatsheet` were moved to `:stacking "fg"` (TOP) on 2026-07-30 for exactly
   this reason (gate `13ai`). `screensaver` stays on `overlay` deliberately.

> ⚠ **Known live exception, flagged 2026-07-30, NOT changed by this audit:**
> `defwindow start-search` in `eww.yuck` is `:stacking "overlay"` **and**
> `:focusable true` — it is the only `:focusable true` in the file and it breaks
> both rules at once. It is *mitigated*: `Super+Shift+Z` is a compositor bind that
> runs `eww close start-search`, so there is a guaranteed way out that does not
> depend on the surface itself. Left alone because eww surfaces were owned by a
> concurrent workstream during this audit and because changing focus/layer on a
> live search box without a session to test in is precisely how this build has
> trapped the desktop before. **Owner/next agent: decide whether the search box
> genuinely needs the keyboard grab, and if so document the exception here
> instead of letting the rule read as absolute.**
