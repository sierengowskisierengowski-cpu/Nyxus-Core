# NYXUS Brand Assets

**Locked rev r15 · 2026-05-14**

This directory is the canonical source of NYXUS brand artwork. Every
chrome surface (SDDM, hyprlock, EWW bar, Plymouth, dock, favicon,
empty-state widgets) loads its mark from here. Do not duplicate or
fork these files into per-app directories.

## The three marks

| Mark              | File                       | Use                                                          |
| ----------------- | -------------------------- | ------------------------------------------------------------ |
| **The Eclipse**   | `eclipse.svg`              | Primary chrome mark. SDDM panel, hyprlock, bar logo, favicon, Plymouth still frame. |
| The Eclipse cream | `eclipse-cream.svg`        | Inverted variant for use on cream surfaces.                  |
| **Constellation N** | `constellation-n.svg`    | Boot/transition mark. Plymouth animation, splash, loading states. |
| **Eye of Nyx**    | `eye-of-nyx.svg`           | Empty-state glyph. Empty inbox, idle lock, no-results, "coming soon". |
| Wordmark          | `wordmark-nyxus.svg`       | Text lockup, used alongside or independently of the marks.   |

## Palette (rev r15, non-negotiable)

| Token              | Hex       | Use                                       |
| ------------------ | --------- | ----------------------------------------- |
| `--nyxus-cream`    | `#f4ead5` | Primary accent, every active surface.     |
| `--nyxus-cream-dim`| `#bfa97a` | Secondary accent, hairlines.              |
| `--nyxus-black-1`  | `#000000` | Page background.                          |
| `--nyxus-black-2`  | `#06060a` | Card surface.                             |
| `--nyxus-black-3`  | `#0a0a0e` | Elevated surface.                         |
| `--nyxus-edge`     | rgba(244,234,213,0.10) | Hairline borders on glass.   |

## PNG renders

PNGs at 16/32/64/128/256/512 are generated at ISO build time from
the SVGs above into `png/`. The generator script lives at
`iso-builder/scripts/render-brand-pngs.sh` and is invoked by the
mkarchiso pre-seal hook. Runtime consumers (hyprlock, Plymouth)
that cannot render SVG natively must reference the PNG variant.

## Updating

If you change a mark, the version-bumped SVG must roll out to every
chrome surface in the same PR. Brand drift is a P0 bug. The
`verify-profile.sh` section 14x asserts that no chrome file
references the old purple accent (`#C084FC` / `192,132,252`) or the
deprecated `◤ X ◥` glyph.

© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
