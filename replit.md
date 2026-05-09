# NYXUS

NYXUS is an Arch Linux-based operating system providing a suite of native Python GTK4 applications and widgets.

## Run & Operate

- `pnpm run typecheck`: Full typecheck across all packages.
- `pnpm run build`: Typecheck and build all packages.
- `pnpm --filter @workspace/api-spec run codegen`: Regenerate API hooks and Zod schemas from OpenAPI spec.
- `pnpm --filter @workspace/db run push`: Push DB schema changes (development only).
- `pnpm --filter @workspace/api-server run dev`: Run API server locally.

**Required Environment Variables:**
- `NYX-J5W-2026-SIERENGOWSKI-LOCKED`: Lock code for brand naming.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Where things live

- `/`: Project overview and high-level documentation.
- `iso-builder/`: Archiso profile for building the NYX ISO.
- `artifacts/api-server/nyxus-scripts/`: Contains all GTK4 application sources and installation tarballs.
- `airootfs/etc/nyxus/`: OS-level documentation mirrored from repo root.
- `~/.nyxus/`: Runtime directory for installed GTK4 apps and helper scripts.
- `nyxus-scripts/nyxus_palette.py`: **★ MASTER PALETTE** (Python) — every NYXUS app imports color/font/radius/blur constants from here. Edit this file to change the system look.
- `nyxus-scripts/nyxus-palette.css`: **★ MASTER PALETTE** (CSS) — every CSS file `@import`s this and uses `@define-color` names like `@nyx_white_off`, `@nyx_glass_dark`. Mirrors `nyxus_palette.py` exactly.
- `nyxus-scripts/nyxus_chrome.py`: Source of truth for unified GTK4 application chrome (windows, popovers, headerbars). Imports its colors from `nyxus_palette.py`.
- `iso-builder/nyx-profile/airootfs/etc/skel/.config/hypr/hyprland.conf`: Hyprland configuration template.

## Visual System — DARK MIRROR · TRIPLE-BLACK LAYERED (LOCKED · rev 2026-05-09 r14)

**Triple-black surface stack (rev r14):** Every surface in the system
now uses one of three layered shades of black, defined ONCE in
`nyxus-palette.css` + `nyxus_palette.py`:

| Token         | Value                       | Use                                           |
|---------------|-----------------------------|-----------------------------------------------|
| `nyx_black_smoke` (BLACK_SMOKE) | `rgba(14,14,22,0.55)` | Bars, panels, window backgrounds (lightest, lets blur through) |
| `nyx_black_ink`   (BLACK_INK)   | `rgba(8,8,14,0.78)`   | Raised pebbles, cards, buttons, ticker (mid)  |
| `nyx_black_void`  (BLACK_VOID)  | `rgba(0,0,0,0.92)`    | Hover, active, popovers, tooltips, modals (deepest, maximum pop) |

**Layering rule:** never put two adjacent surfaces at the same tier —
always go one tier darker as you elevate. That's what makes elements
"pop" without using color: pure depth via three blacks.

**White-glow accent (rev r14):** Two new tokens for sparing white-glow
text accents — `nyx_glow_soft` (`rgba(255,255,255,0.45)`) and
`nyx_glow_bright` (`rgba(255,255,255,0.85)`). Use only on wordmarks
(NYXUS, SIERENGOWSKI), focused/active labels, and key headings — never
on body text. Recipe: `text-shadow: 0 0 8px @nyx_glow_bright, 0 0 18px @nyx_glow_soft`.

Legacy tokens (`nyx_glass_dark/deeper/deepest` and Python
`GLASS_DARK/DEEPER/DEEPEST`) are kept as aliases pointing at the new
tiers, so any existing app code keeps working but renders with the new
triple-black palette automatically.

---

### Pre-r14 reference — DARK MIRROR · UNIFIED FROSTED GLASS (rev 2026-05-07 r13 · superseded)

**System-wide active glow (rev r13):** Hyprland window borders now use the
DARK MIRROR rim-light gradient (white `#ffffff` → off-white `#e8edf5` →
light grey `#c8ccd6` → faded black `#0a0a0a` → ink `#000000`, 135°,
animated 240-frame slow rotation). This is the SOLE source of "active
glow" anywhere in the system. Apps no longer draw their own borders,
glows, headerbars, or chrome animations. The terminal in particular is
now a bare VTE widget on dark glass — every visual frame around any
window comes from Hyprland.

**Standalone duplicates removed (rev r13):** `nyxus_notepad.py` and
`nyxus_weather.py` standalone scripts have been deleted. The rich
GTK4 tarball editions (`nyxus-notepad.tgz`, `nyxus-weather.tgz`) are
the sole survivors; install.sh extracts them via the existing tarball
pipeline and they create their own `.desktop` entries
(`io.nyxus.notepad.desktop`, `io.nyxus.weather.desktop`).



**Apps + flyout (rev 2026-05-07 r12 — replaces EMBOSSED CREAM PAPER for apps):**
All 11 GTK4 apps (godsapp, home, intel, notepad, passwords, phantom, sage,
shield, start, studio, weather) and the flyout (panel) now share one
unified DARK MIRROR look enforced centrally by `nyxus_chrome.py` CHROME_CSS
loaded at `Gtk.STYLE_PROVIDER_PRIORITY_USER` (overrides every per-app
provider — no app code changes needed). Per-app neon palettes (card-pink,
card-cyan, card-gold, btn-primary-*, phantom @nyx_purple/pink/gold, etc.)
are all collapsed to the same monochrome glass.

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
The waybar shells, pebbles, beads, ticker, plaques, and tooltips remain
**DARK FROSTED GLASS** — translucent near-black `rgba(8,12,20,0.58)` shells
with darker blue-black pebbles `rgba(15,20,32,0.72)`, light text `#e8edf5`,
cool silver-white starlight halos `rgba(230,240,255, …)` on hover. **NO
GOLD anywhere** in the waybar — silver/cool-white only. Workspaces appear
ONLY on the left bar. The OWL signature lives on the bottom bar
modules-right next to Panel.

The wallpaper is the **black-hole / cosmic ink swirl**
(`nyxus-ink-swirl.png`, 2560×1396, mostly black with silver-white wisps).

---

### Legacy reference — EMBOSSED CREAM PAPER (rev 2026-05-06v · superseded for apps)

The cream-paper rules below described the previous app + waybar treatment.
They are kept for reference only — the waybar dark-glass spec above
supersedes the cream waybar rules, and the DARK MIRROR spec above
supersedes the cream chrome for apps. Do NOT use cream paper rules in new
work unless the user explicitly reverts the lock.

The wallpaper is the **black-hole / cosmic ink swirl** (`nyxus-ink-swirl.png`,
2560×1396, mostly black with silver-white wisps). The waybar shells, pebbles,
beads, ticker, plaques, and tooltips are now **DARK FROSTED GLASS** —
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

## Architecture decisions

- **Native GTK4 for all apps**: Every NYXUS app and widget is developed exclusively with native Python GTK4, prohibiting any web-based frameworks for performance and consistency.
- **Unified Visual Chrome**: A single `nyxus_chrome.py` module applies system-wide EMBOSSED CREAM PAPER styling to all GTK4 applications by monkey-patching `Gtk.ApplicationWindow.present`. See the Visual System section above for the locked-in rules `nyxus_chrome.py` enforces.
- **Offline-first Chrome Bootstrap**: The chrome bootstrap mechanism avoids synchronous network fetches by distributing `nyxus_chrome.py` locally during installation, ensuring offline functionality.
- **Dunst for Notifications**: Switched from Mako to Dunst as the sole notification daemon for system-wide consistency and improved features.
- **Modular Studio Suite**: NYXUS Studio is a multi-module GTK4 creative suite, architected with distinct modules (paint, vector, 3d, video, etc.) connected via internal broadcast mechanisms.
- **No-op for `nyxus-panel` Chrome**: `nyxus-panel` is intentionally excluded from the unified chrome bootstrap due to its reliance on `Gtk4LayerShell` which conflicts with window re-parenting.
- **Live fog daemon under waybars** (locked 2026-05-06j): Animated swirling fog inside the bars is rendered by `nyxus-fog.py` — a Python GTK4 + Cairo particle daemon that spawns 4 transparent `wlr-layer-shell` BOTTOM-layer windows aligned to each bar (top/bottom/left/right) and draws 14 soft-edged radial-gradient blobs per bar at 30fps. Palette: pure white + off-white #fbfaf6 + occasional gold #d4a73a (~15%, jewelry accent only). Waybar shell is intentionally low-alpha (~0.18) so the fog reads through. Autostart via Hyprland `exec-once = python3 ~/.nyxus/nyxus-fog.py`. CSS-based animation in waybar was tried (rev i) and abandoned — GTK3 CSS does not animate `background-position` reliably.
- **Wallpaper is full-bleed** (locked 2026-05-06c): `nyxus-frost-sierengowski.png` is the unpadded SIERENGOWSKI graffiti-on-cream artwork edge-to-edge. The padded variant was reverted at user request — side waybars (now 64px left / 72px right) will overlap the outermost letter strokes; the frosted blur softens the overlap. Do NOT re-pad without explicit user confirmation.
- **Asset-driven design pipeline** (locked 2026-05-06): high-fidelity
  3D look (sculpted plaques, liquid drips, extruded monograms) is
  produced as **rendered assets** by the user (Blender / Inkscape /
  Figma) or via AI image generation — NOT faked with CSS box-shadows.
  Pure CSS is reserved for the floating-neomorphic-button recipe and
  positioning. When the user drops a PNG/SVG, it's added to the
  `download.ts` whitelist, mirrored to `dist/`, and wired in as a
  background-image or icon. Stop trying to sculpt 3D depth in CSS.

## Product

- **GTK4 Application Suite**: A collection of native Python GTK4 applications including notepad, stickies, weather, system monitor, settings, terminal, quick settings, launcher, power menu, and screenshot tools.
- **NYXUS Studio**: A comprehensive creative suite with modules for painting, vector graphics, 3D modeling, video editing, animation, photo manipulation, layout, typography, and voice.
- **Integrated Desktop Environment**: Features a custom Waybar setup, Hyprland integration, and a themed SDDM login manager.
- **Application Store**: `nyxus-start` includes an inline NYXUS App Store for discovering and installing additional applications.
- **System Health Auditing**: `nyxus_doctor.py` provides a health audit tool for the system.
- **Notification Management**: Centralized notification system managed by Dunst, with controls in quick settings and a dedicated notifications panel.

## User preferences

- **Visual style is LOCKED** to DARK MIRROR (apps + flyout) + DARK GLASS
  WAYBAR (waybar shells) — see "Visual System" section above (rev
  2026-05-07 r12). Every future change MUST follow the locked monochrome
  palette: white / off-white `#e8edf5` / `#c8ccd6` / black / dark-glass
  rgba(8,12,20,0.55). No neon, no gold, no per-app colors, no alternate
  themes. The only accent permitted is per-workspace identity stripes on
  the bottom waybar.
- **Brand-naming lock**: "NYX" = ISO file only. "NYXUS" = OS + every
  component. "SIERENGOWSKI" = creator wordmark on wallpaper + plaques.
- **Propose-before-build for visual direction changes**: when the user
  shares a reference image or asks for a new look, present options +
  tradeoffs first; do not start implementing until they greenlight.

## Gotchas

- **ISO Build Environment**: The `iso-builder/` cannot be built within Replit; it requires root privileges and an Arch Linux host.
- **Hyprland Config Placeholder**: `iso-builder/nyx-profile/airootfs/etc/skel/.config/hypr/hyprland.conf` is a placeholder; users must replace it with their daily-driver configuration before building the ISO.
- **Brand Naming**: Strictly adhere to "NYX" for the ISO file and "NYXUS" for the operating system and all its components.

## Pointers

- **pnpm-workspace skill**: Refer to the `pnpm-workspace` skill for details on workspace structure, TypeScript setup, and package management.
- **OpenAPI Spec**: The OpenAPI specification defines API contracts and is used for codegen.
- **Drizzle ORM Documentation**: Consult Drizzle ORM documentation for database schema management.
- **Orval Documentation**: Refer to Orval documentation for API codegen specifics.
- **GTK4 Documentation**: For native Python GTK4 development, refer to official GTK4 documentation.