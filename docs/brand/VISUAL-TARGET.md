# NYXUS Visual Target

**Sources of truth (in order of authority):**

1. `docs/brand/nyxus-eclipse-reference.png` — the original eclipse
   reference. Defines mood, palette, materials.
2. `docs/brand/nyxus-desktop-target.png` — the canonical desktop UI
   target. Defines layout: slim top bar, right sidebar of icons,
   eclipse wallpaper centred, pure black surround. Sprint I locks
   the OS to this composition.
3. `/usr/share/sddm/themes/nyxus/background.png` — the locked
   SDDM login background (eclipse ring above plinth scene).
4. `/usr/share/backgrounds/nyxus/nyxus-eclipse-horizon.png` — the
   default desktop wallpaper (cinematic eclipse + reflective water +
   distant terrain). This is what the user sees the second they
   land on the desktop.

These images are the single visual reference every NYXUS sprint must
reach toward. If a UI change does not move the OS *closer* to how
they feel, it is the wrong change.

## Layout target (Sprint I lock)

The desktop composition is fixed by `nyxus-desktop-target.png`:

- **Slim top bar** (eww `bar-top`, 26px tall, 100% wide, hairline
  bottom edge). One row of small icons left, clock/title centre,
  small icons right.
- **Right sidebar** (eww `bar-right`, 56px wide, 70% tall, anchored
  centre-right) — the app/launcher rail.
- **No bottom dock by default.** `bar-bottom` is still defined for
  power users who want a taskbar — opt-in via
  `~/.config/eww/nyxus.conf` `NYXUS_EWW_BARS`.
- **No left workspace rail by default.** Same opt-in story.
- **Eclipse wallpaper as hero**, centred horizontally, halo just above
  vertical centre, distant terrain at the bottom edge.
- **Pure black surround** — no padding chrome around the wallpaper,
  it goes edge-to-edge.

## What the image is

A black eclipse mark, centered, hovering above a still water surface.
A single soft cream halo behind the mark is the only light source.
The eclipse casts a vertical reflection across the water below.
Distant misty silhouettes hint at terrain. The whole frame is matte
ink with the cream-warm light bias.

## What it locks in

| Element             | What it teaches                                              |
|---------------------|--------------------------------------------------------------|
| **Black eclipse**   | The Eclipse mark is the PRIMARY brand. Boot, login, dock — every "this is NYXUS" moment uses it. The Constellation N is for boot only; Eye of Nyx is for empty states. |
| **Cream halo**      | One light source per surface. CREAM `#f4ead5` only. No second accent, no gradient hue-shift, no purple/cyan/red ever. |
| **Reflection**      | Depth comes from reflection, not from drop-shadow. Layer mirrors the layer above it (think: dock pill reflects the bar accent above it). |
| **Triple-black**    | True black `#0a0a0a`. Not purple-tinted `#0a0a14`, not navy `#0d0a12`. Pure ink. |
| **Mist + silhouette** | Atmospheric depth via blur + low contrast, not via additional colors. Hyprland blur kernels and frosted-glass should evoke this haze. |
| **Stillness**       | Animations are slow, deliberate, contemplative. Bouncy easings betray the brand. |

## Concrete rules this enforces

- **Single light source per panel.** Bar/dock/notification — only one
  cream highlight per surface. Eww accent variables that defined two
  cream stops were collapsed to one in Sprint G.
- **No red, no cyan, no purple.** Even for terminal ANSI red and
  notification critical urgency. Use brighter cream `#fff8e0` +
  thicker frame for critical hierarchy. (Sprint G round-2.)
- **Reflection > shadow.** Where macOS uses drop-shadow for depth, we
  use a downward fade-mirror of the surface above. Hyprland's xray
  layer rules already start this; floating window opacity stays high
  so the wallpaper reads through cleanly.
- **One Eclipse, multiple appearances.** The mark may hover (lockscreen,
  welcome wizard), partial-eclipse (loading state), or full-disc (boot
  splash), but it is always the SAME geometry — never re-drawn,
  never alternate cuts.

## Operational notes

- The reference image ships with the OS at
  `/usr/share/backgrounds/nyxus/nyxus-eclipse-reference.png` so it is
  always available to the wallpaper picker, lockscreen background, and
  welcome wizard.
- `docs/brand/nyxus-eclipse-reference.png` is the version-controlled
  copy that survives ISO rebuilds.
- When in doubt about a UI decision, open this image side-by-side
  with the surface you are changing. Ask: "Does this make NYXUS feel
  more like the eclipse image, or less?"

## What this image does NOT mean

- It does NOT mean every screen needs a literal black circle on it.
  The Eclipse mark is for brand moments (boot, login, lock, welcome,
  dock-launcher). Working surfaces (Settings, file manager, terminal)
  use the same palette + materials but not the literal mark.
- It does NOT mean the OS should be sparse or empty. Density is fine
  — the rule is monochromatic palette + single light source + matte
  materials, not minimal content.

— Locked rev r15 · 2026-05-14

---

## Sprint J update — rev r16 · 2026-05-14

Sprint J adds a **second** accent and a **second** brand mark. The
primaries from rev r15 stay locked exactly as they are; rev r16 is
purely additive.

### Second accent: COPPER `#b8865a`
- **Primary stays cream** (`#f4ead5`) — prose, brand wordmarks, most
  surfaces, the warm-light-source feeling of the Eclipse reference.
- **Copper is reserved for**:
  - Icon ring outlines (every NYXUS-Glyph app icon)
  - Micro-accents: toggle thumbs, progress fills, focus rings
  - High-contrast highlights where cream would lose against bright
    cream backgrounds
- Hex `#b8865a` is intentionally desaturated. It must read as **warm
  metal**, never **yellow gold**. Bright golds (`#d4b87a`, `#ffd700`)
  remain BANNED.
- SCSS tokens: `$copper, $copper-soft, $copper-deep, $copper-glow,
  $copper-edge, $copper-bg-soft, $copper-bg-active`.
- Accent registry: `accent.json` "copper" preset is now selectable
  alongside "aurora" (cream).
- Welcome wizard: "Copper" is the second option in the accent picker,
  right after "Eclipse Cream".

### Second mark: THIN-RING ECLIPSE
- **Primary stays the filled-disc Eclipse** (`docs/brand/nyxus-eclipse-reference.png`)
  — boot, login, lock, welcome hero, dock-launcher.
- **Thin-ring is reserved for small-context UI**:
  - Login glyph (small SDDM avatar)
  - Plymouth subtle states (low-contrast progress)
  - Icon-grid centre symbols where filled disc would dominate
  - Welcome wizard step glyphs
- Reference: `docs/brand/nyxus-eclipse-thinring-mark.png` (image 6 —
  "NYUS" monolith with pencil-stroke circle + water reflection).
- Live SVG: `usr/share/icons/NYXUS-Glyph/scalable/places/nyxus-eclipse-thinring.svg`
  — single 0.7px cream stroke at r=18 with a small bright-spot
  diamond suggestion at top-right.

### Icon contract: NYXUS-Glyph
The **unified app-icon contract** for every shipped NYXUS app:
- Black puck (radial gradient `#1c1c1c → #000`)
- Thin copper ring at r=23.5 (stroke 0.9, copper `#b8865a` at 92% opacity)
- Centred cream glyph (`#f4ead5`, stroke 1.4, line-cap round)
- Reference mood: `docs/brand/nyxus-icon-style-reference.png` and
  `docs/brand/nyxus-icon-grid-reference.png`
- Theme directory: `usr/share/icons/NYXUS-Glyph/`
- Default GTK icon theme (gtk-3.0 + gtk-4.0) switched to NYXUS-Glyph;
  inherits NYXUS-Dark → Papirus-Dark → Adwaita → hicolor for every
  non-NYXUS app.

### What this does NOT change
- The cream `#f4ead5` lock from rev r15 is still in force. Nothing
  cream-coloured becomes copper without an explicit design decision.
- The filled-disc Eclipse stays the primary brand mark. Boot, login,
  lock, welcome, and dock-launcher still use it — unchanged.
- The banned palette (`#a06bff, #3ad8ff, #d4b87a, #ff4d6b, ...`)
  stays banned. Copper `#b8865a` is a NEW token, not a relaxation
  of the ban.

— Updated rev r16 · 2026-05-14
