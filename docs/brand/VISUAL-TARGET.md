# NYXUS Visual Target

**Source of truth:** `docs/brand/nyxus-eclipse-reference.png`

This image is the single visual reference every NYXUS sprint must
reach toward. If a UI change does not move the OS *closer* to how
this image feels, it is the wrong change.

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
