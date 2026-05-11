# NYXUS Design Contract

**Version 1 · 2026-05-11 · rev r9-eww**

This is the **single quality bar** for everything in NYXUS — every panel,
flyout, window, dialog, menu, page, and overlay. Old work and new work
both. If something fails this contract, it's a bug — file it, don't ship it.

The benchmark is **macOS Sonoma / Windows 11 / iOS 17**. Not "indie Linux."

---

## 1. Layout & Fit

> **No content stuck to the top with a gap below. No content overflowing the edges. Nothing pushed off-screen on a laptop display.**

- Every panel must be **vertically centered** in its viewport unless the
  content genuinely fills it. Use a flex spacer above and below an inner
  column, **not** padding-top alone.
- Every panel must have a **hard max-width** for body text/labels.
  Default: title ≤ 760px, body copy ≤ 720px. Never let a paragraph
  stretch across an ultrawide monitor.
- Every panel must have a **min-width** so it doesn't collapse on small
  screens. Default: 480px.
- Every panel must work at **1366×768** (the smallest display we support)
  without clipping the footer or hiding any control.
- If content might overflow, wrap it in a `Gtk.ScrolledWindow` /
  EWW `scroll` widget with a fixed `height`. Never let a window grow
  unbounded.
- Footer/toolbar always anchored at the bottom edge. Primary action
  always on the right. Back/secondary always on the left.
- **Test on every breakpoint before merging:** 1366×768, 1920×1080, 2560×1440, 3840×2160.

## 2. Spacing

- Outer panel padding: **18-24px** (small flyouts) or **56-72px** (full-screen apps).
- Section spacing: **14-20px** vertical between distinct groups.
- Tight spacing (label → input): **6-10px**.
- Never use `0px` spacing between sibling elements unless they visually
  belong to the same component (e.g. a button group).

## 3. Typography

| Use                         | Family                       | Size | Weight | Tracking |
|-----------------------------|------------------------------|------|--------|----------|
| Display headline            | Space Grotesk / Inter        | 44px | 700    | -0.01em  |
| Section title               | Inter                        | 22px | 700    | 0.18em   |
| Body                        | Inter                        | 14px | 400    | normal   |
| Eyebrow / label             | Inter                        | 11px | 600    | 0.20-0.32em |
| Hint / metadata             | Inter                        | 11px | 400    | normal   |
| Mono (code, IDs, glyph nums)| JetBrainsMono Nerd Font      | 11-14px | 400 | normal   |

- All caps **only** for eyebrows, labels, section headers. Never for body.
- Never use system-default font fallback in production. If the font is
  missing, install it.

## 4. Color

DARK MIRROR palette is locked. Do **not** invent new colors.

| Token             | Value                          | Use                            |
|-------------------|--------------------------------|--------------------------------|
| `--bg-page`       | `#000000` to `#050608` gradient| Window background              |
| `--surface-1`     | `rgba(8,10,16,0.66)`           | Rails, sidebars                |
| `--surface-2`     | `rgba(17,21,31,0.85)`          | Inputs, list rows              |
| `--accent-primary`| `#a06bff` (Mirror purple)      | Primary actions, focus         |
| `--accent-secondary`| `#3ad8ff` (Mirror cyan)      | Gradient pair                  |
| `--success`       | `#82ffd2`                      | Confirmations, "done" state    |
| `--warning`       | `#ffb45e`                      | Pending, caution               |
| `--danger`        | `#ff4d6b`                      | Errors, destructive            |
| `--text-strong`   | `#ffffff`                      | Headings, primary copy         |
| `--text`          | `#e8edf5`                      | Body                           |
| `--text-muted`    | `#9aa2b3` / `#8b94a8`          | Hints, captions                |
| `--text-subtle`   | `#6b7388`                      | Eyebrows, footnotes            |
| `--text-faint`    | `#3a4055`                      | Disabled                       |

- Use the gradient `linear-gradient(90deg, #a06bff, #3ad8ff)` for primary
  buttons and progress fills only. Don't sprinkle it on cards.
- Never use saturated red/green/yellow at full brightness. The danger
  token is muted on purpose.

## 5. Borders, radii, and shadows

- Border radius: **10px** (inputs, small buttons), **12px** (cards, tiles),
  **16px** (windows, large panels), **999px** (pills, slider tracks).
- Default border: `1px solid rgba(160,107,255,0.10-0.32)` (intensity tracks
  the hierarchy of the surface).
- Focus ring: `border-color: #3ad8ff; box-shadow: 0 0 0 3px rgba(58,216,255,0.18);`
- Window shadow: `0 24px 60px rgba(0,0,0,0.70)` plus inner highlight
  `inset 0 0 28px rgba(160,107,255,0.06)`.
- Never use a hard `1px solid black` border — always use the purple/cyan
  family at low alpha.

## 6. Motion

- All transitions: **160-220ms**, ease-out or ease-in-out only.
- Page transitions: cross-fade (Gtk.StackTransitionType.CROSSFADE) or
  slide-then-fade. Never instant.
- Hover/focus state changes: 120-180ms.
- No bouncing, no spring overshoot, no carnival animations.

## 7. Inputs

- Every text input: 12-14px padding, 10px radius, focus ring per §5.
- Every dropdown: same chrome as text inputs.
- Every switch: gradient when on, neutral grey when off, white knob.
- Every slider: thin track (5-6px), gradient highlight, white knob with
  glow.
- Validation: **inline below the field**, not in a popup. Red text only,
  no icons unless the design includes them by default.
- Required fields: never marked with red asterisks. Use a soft hint or
  rely on the validator.

## 8. Buttons

| Variant   | Use                         | Style                                     |
|-----------|-----------------------------|-------------------------------------------|
| Primary   | The single main action      | Gradient fill, dark text, glow on hover   |
| Ghost     | Secondary actions           | Transparent, purple border, white on hover|
| Link      | Tertiary / "skip" / "advanced" | No border, muted text, white on hover  |
| Destructive | Delete, forget, sign out  | Red-tinted ghost; solid red only on confirm dialogs |

- One primary per panel. If you need two, one of them is wrong.
- Never use emoji as a button label substitute. Glyphs (✕, ↻, ◉) are okay.

## 9. Empty / loading / error states

- Every list, every grid, every panel must define what it shows when:
  1. **Empty** — short copy + a primary action ("Connect to WiFi", not just "No networks")
  2. **Loading** — skeleton or spinner placed where the content would be
  3. **Error** — short copy + retry button + advanced action (open logs)
- Never show a blank panel. Never throw a stack trace into the UI.

## 10. Copy

- Sentence case. Not Title Case.
- Active voice. Second person. ("Pick your accent." not "Accent Selection")
- No exclamation marks unless on a single celebratory moment per app.
- No "click here." Buttons say what they do.

## 11. Accessibility

- Minimum contrast: **4.5:1** for body text, **3:1** for large text.
- All interactive elements ≥ **40×40px** target on touch displays.
- Every input has a label (visible or `aria-label`).
- Focus is always visible. Never `outline: none` without a replacement.
- Keyboard: every action reachable with Tab + Enter. Esc closes flyouts.

## 12. Per-component checklists

### Flyouts (EWW windows)

- [ ] Geometry uses `:anchor "bottom right"` (or matching corner), `:y "78"` to clear bar
- [ ] Has explicit `:width` and `:height` (or `"auto"` for height only)
- [ ] Inner padding 18-20px, root border-radius 16px
- [ ] Title at top, content middle, action row at bottom
- [ ] Close button in action row labelled "Close (Esc)"
- [ ] List content wrapped in `scroll` with fixed `:height`
- [ ] Empty state defined (e.g. "No paired devices")
- [ ] Namespace starts with `nyxus-` so layerblur catch-all picks it up

### Wizards / multi-step flows

- [ ] Step rail on left with current/done/upcoming states
- [ ] Stage content vertically AND horizontally centered in viewport
- [ ] Footer pinned to bottom with Back (left) / Continue (right)
- [ ] Continue disabled when current step's validation fails
- [ ] Each step's commit() applies real system state — no mockups
- [ ] Marker file written on completion so it never re-runs

### Settings panes

- [ ] Sidebar nav on left with icon + label
- [ ] Pane title at top, eyebrow above
- [ ] Settings grouped into named sections with 14px spacing
- [ ] Every toggle/dropdown writes immediately on change (no Save button)
- [ ] Search bar in shell finds settings by name AND keyword

### Dialogs

- [ ] Adw.MessageDialog or matching style
- [ ] Title sentence case
- [ ] Body 1-2 short paragraphs, no walls of text
- [ ] Two-button max (Cancel left, Action right). Three only with reason.
- [ ] Destructive actions in danger color

---

## 13. Audit trail (existing components)

Every component built before this contract was written must be audited
against §1-12. Score each as PASS / NEEDS-FIX / FAIL.

| Component                       | Status                 | Notes |
|---------------------------------|------------------------|-------|
| Bar (EWW main bar)              | TODO audit             | Check spacing on right cluster |
| Quick Settings flyout           | PASS (audited 2026-05-11) | Tile grid + sliders, no list = no empty state needed |
| WiFi flyout                     | PASS (audited 2026-05-11) | Empty state added: "No networks in range" |
| Bluetooth flyout                | PASS (audited 2026-05-11) | Empty state added: powered/off-aware copy |
| Audio Mixer flyout              | PASS (audited 2026-05-11) | Empty state added: "No apps playing audio" |
| Calendar flyout                 | PASS (audited 2026-05-11) | Static grid, no list = no empty state needed |
| Notification Center             | PASS (audited 2026-05-11) | Empty state added: DND-aware ("All caught up" / "DND on") |
| Cheatsheet                      | TODO audit             | Three-column layout fit |
| Powermenu                       | TODO audit             | Centering + button hierarchy |
| Dashboard                       | TODO audit             | Largest known offender — full pass |
| Welcome Wizard                  | PASS (built to contract) | Reference implementation |
| Settings app                    | NOT BUILT              | Must be built to contract from day 1 |

Audit pass: walk every component on a 1366×768 display. Anything that
fails ships a fix in the same sprint as the audit.

---

## 14. Process

- Every PR/commit that adds or changes UI **must** include a screenshot
  on at least 1366×768 and 1920×1080.
- No "we'll fix the polish later." Polish is shipping criteria, not
  follow-up work.
- If you can't make it look like Apple/Microsoft would ship it, file a
  blocker before merging.
