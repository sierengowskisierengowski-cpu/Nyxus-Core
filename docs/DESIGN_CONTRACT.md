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
| Bar (EWW main bar)              | PASS (audited 2026-05-11) | Right cluster spacing 6→8 (§2 tight range), left/center untouched |
| Quick Settings flyout           | PASS (audited 2026-05-11) | Tile grid + sliders, no list = no empty state needed |
| WiFi flyout                     | PASS (audited 2026-05-11) | Empty state added: "No networks in range" |
| Bluetooth flyout                | PASS (audited 2026-05-11) | Empty state added: powered/off-aware copy |
| Audio Mixer flyout              | PASS (audited 2026-05-11) | Empty state added: "No apps playing audio" |
| Calendar flyout                 | PASS (audited 2026-05-11) | Static grid, no list = no empty state needed |
| Notification Center             | PASS (audited 2026-05-11) | Empty state added: DND-aware ("All caught up" / "DND on") |
| Cheatsheet                      | PASS (audited 2026-05-11) | Title + 3 cols + close button + Esc — no list = no empty state needed |
| Powermenu                       | PASS (audited 2026-05-11) | Added `.power-btn-danger` variant: Shutdown/Restart now red-bordered with red glyph (§8) |
| Dashboard                       | PASS (audited 2026-05-11) | Wrapped in `(scroll …)` so content never overflows 1366×768 (§12); replaced all 8 emoji toggles with nerd-font glyphs (§6) |
| Welcome Wizard                  | PASS (built to contract) | Reference implementation |
| Settings app                    | PASS (rev r11 — full build) | libadwaita Adw.NavigationSplitView, 17 sections all fully wired with real backends: Appearance (swww/hyprctl), Network (nmcli), Bluetooth (bluetoothctl), Display (hyprctl monitors + brightnessctl + night-light), Sound (pactl sinks/sources/mute/default), Power (battery + powerprofilesctl + cpufreq governor + logind), Notifications (mako/dunst/swaync auto-detect + DND + history), Date/Time (timedatectl + tz picker + world clock), Keyboard (hyprctl input:kb_* + repeat rate/delay), Mouse (sensitivity + accel + natural scroll + touchpad), Privacy (camera/mic detection + active-capture watch + geoclue + telemetry audit), Apps (pacman + xdg-mime defaults + autostart), Storage (df + lsblk + smartctl + paccache + journal vacuum), Updates (checkupdates + paru/yay -Qua + reboot-required check), Accessibility (text scale + cursor size + animations toggle), Users (whoami + getent + sessions + visudo). Every page either has live data or an honest §9 empty state. Live polling on Display/Sound/Power/Storage/Updates with cleanup on window close. EWW dashboard gear tile (󰒓) launches `nyxus-settings`. |
| SysMon app                      | PASS (audited 2026-05-12) | Refactored to `Adw.Application` + `Adw.ApplicationWindow` + `Adw.NavigationSplitView` with `Adw.HeaderBar` carrying live host/uptime/procs/clock pills. All 8 Cairo content pages preserved (Overview, CPU, Memory, Disk, Network, GPU, Processes, Sensors). FORCE_DARK color scheme. §9 honored on every page (sensors falls back to "no readings" copy when lm_sensors empty). |
| Notepad app                     | PASS (built to contract) | Standalone `Adw.ApplicationWindow` markdown editor + Pango-rendered preview pane via `Gtk.Paned`, file open/save/save-as via `Gtk.FileDialog`, recent files menu with §9 "No recent files" empty state, 2s debounced autosave, restore-last-session, Ctrl+N/O/S/Shift-S/P shortcuts, `Adw.MessageDialog` discard confirm. FORCE_DARK. |
| Stickies app                    | PASS (audited 2026-05-12) | Cairo paper-note canvas (intentional creative aesthetic) wrapped in `Adw.Application` + FORCE_DARK so it boots and themes consistently with the rest of the family. JSON persistence, drag-to-reposition, color-picker per note, double-click to edit. |
| Notes app                       | PASS (audited 2026-05-12) | Lightweight scratchpad: `Adw.Application` + FORCE_DARK + dirty-state save indicator with §9 empty state for first-run. |
| Control app                     | PASS (audited 2026-05-12) | Tactile Cairo control surface (HW profile + fan curves + RGB + processes + profiles) wrapped in `Adw.Application` + FORCE_DARK. All 6 nav pages render; toast surface for live actions. |
| Launcher                        | PASS (audited 2026-05-12) | Rofi-style fuzzy app launcher: `Adw.Application` + FORCE_DARK, `.desktop` scan + fuzzy match scoring, keyboard-driven (Up/Down/Enter/Esc), §9 "No matches" empty state. |
| Terminal app                    | PASS (audited 2026-05-12) | VTE-backed terminal: `Adw.Application` + FORCE_DARK; honest fallback label when VTE GTK4 binding (`vte-2.91-gtk4`) is missing rather than a blank window. |
| Screenshot picker               | PASS (audited 2026-05-12) | Region/full-screen `grim`+`slurp` wrapper: `Adw.Application` + FORCE_DARK, decorated borderless window with chrome glow, mode picker. |
| Screensaver                     | PASS (audited 2026-05-12) | Fullscreen Cairo screensaver: `Adw.Application` + FORCE_DARK, SIGTERM/SIGINT honored so `hypridle` can wake cleanly. |
| Welcome Wizard                  | PASS (rev r13 — Adw audit 2026-05-12) | `Adw.ApplicationWindow` + step-rail wizard (Hello → Region → Network → Account → Appearance → Privacy → Ready). `Adw.MessageDialog` for confirms. Region populated from `timedatectl` + curated tz list, network from `nmcli`. Reference implementation for the family. |
| Doctor (CLI)                    | PASS (audited 2026-05-12) | Single-shot health audit — intentionally CLI (no GTK), uses NYXUS palette tokens for colored terminal report. Exits 0 (green) / 1 (yellow or red). Listed in APPS_LIST as a terminal launcher. |
| Fog overlay                     | PASS (audited 2026-05-12) | Layer-shell Cairo fog drifting around bar edges: `Adw.Application` + FORCE_DARK. **Launch blocker fixed**: `FogBlob.__init__` referenced an undefined `COLOR_GOLD` token (palette only ships white/off-white/grey wisps) — branch removed; alpha now uses the single bright-fog range. |
| Demon Wake (jumpscare)          | PASS (audited 2026-05-12) | Lock/wake jumpscare overlay: `Adw.Application` + FORCE_DARK; SIGTERM/SIGINT honored, hard-kill timer ensures it always exits even if fade glitches. |
| App family Adw consistency      | PASS (audited 2026-05-12) | All 13 GUI Python apps in `nyxus-scripts/` (notepad, stickies, notes, sysmon_gtk, settings, control, terminal, launcher, screenshot, screensaver, welcome, fog, demon_wake) now subclass `Adw.Application`, call `Adw.init()`, and force `Adw.ColorScheme.FORCE_DARK` on activate. Same shared `nyxus_chrome` graffiti background + `nyxus_palette` tokens. Doctor stays CLI by design. `APPS_LIST` in `iso-builder/build-iso.sh` cleaned: phantom `weather`/`quicksettings`/`powermenu` entries removed (those live in EWW, not as standalone .py), duplicate `settings:` entry collapsed, missing `notes` entry added. Every entry maps to a real `nyxus_<mod>.py`. |

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
