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
