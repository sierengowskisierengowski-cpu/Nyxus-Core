# NYXUS — LOGIN FIX + BAR REDESIGN BRIEF (2026-07-26 evening)

**Read this before touching SDDM, the eww bars, or the bottom-bar hub.**

> ⚠ **This work was explicitly requested by the owner.** The Jul 25→26 note
> (`EWW_CHROME_REVERT_BRIEF_2026-07-26.md`) says *"do not restart saucer/time/
> dock/ticker work unless the owner explicitly asks."* On 2026-07-26 the owner
> **did** ask, repeatedly and specifically: redesign the side rails, keep the
> ticker but do more with it, keep the bottom graphs' style, and fix the
> saucer→music flip to a 1980s boombox. **Do not revert this as if it were the
> Jul 25 chrome episode.** It is a different, sanctioned pass.

---

## 1. NO LOGIN SCREEN — root cause found and killed at source ✅ VERIFIED

**Symptom (weeks-long, survived at least one prior "fix"):** no SDDM greeter;
the owner dropped to a TTY and started Hyprland by hand.

**Root cause:** `/etc/sddm.conf.d/nyxus.conf`. SDDM reads `*.conf` in
**alphabetical order**, so bare `nyxus.conf` sorts *after* `10-nyxus.conf` and
wins. It set two fatal keys:

1. `DisplayServer=wayland` → SDDM looks for a wayland greeter compositor
   (weston, not installed) → `HELPER_DISPLAYSERVER_ERROR`, greeter
   `exited with 4`, falls back to `x11-user`.
2. `GreeterEnvironment=QT_WAYLAND_SHELL_INTEGRATION=layer-shell` → this
   **replaces the whole variable**, dropping `QT_QUICK_BACKEND=software`, which
   this hybrid-GPU laptop requires → the x11 fallback greeter SIGSEGVs
   (`exited with 11`). Nothing renders.

**Why a previous session's fix did not stick — THE IMPORTANT PART:**
`artifacts/api-server/nyxus-scripts/sddm-theme/install.sh` **regenerated that
exact file on every run** (heredoc, was ~line 61). Deleting the live file alone
guarantees it comes back. **Fixed:** that heredoc now writes `[Theme]` only,
with a comment explaining that `DisplayServer` / `GreeterEnvironment` belong to
`10-nyxus.conf` and must never be written here.

Verified it was the repo's ONLY writer of `DisplayServer=wayland`; the ISO
profile and `nyxus-fix-login.sh` / `nyxus-restore-login.sh` /
`nyxus-install-sddm.sh` all correctly use x11.

**Live fix (owner ran it, sudo required — agent cannot sudo, fingerprint only):**
```
sudo mv /etc/sddm.conf.d/nyxus.conf /root/nyxus.conf.disabled-20260726
sudo systemctl restart sddm
```
Confirmed working: greeter starts, nyxus theme loads, background renders.
(One `HELPER_DISPLAYSERVER_ERROR` still appears on the first attempt before it
recovers and succeeds — **open, low priority**, see §6.)

**LESSON, generalise it:** when a config keeps reverting, find the installer
that regenerates it. Fixing only the live file is never the fix.

## 2. LOGIN / DESKTOP WALLPAPER WAS THE HACKER-MODE ART ✅

Not an SDDM problem. `~/.config/nyxus/hacker-mode.state` still read `mode=on`.
That state **persists on disk**; nothing re-enables it at boot — it had simply
never been turned off, so every login came up in hacker mode. Ran
`nyxus-hacker-mode off`; `stations.json` restored from the normal backup,
opacity back to 0.90/0.80, and `nyxus-tintd` / `nyxus-pulsed` confirmed resumed
(hacker mode **SIGSTOP**s them — they were frozen, not dead).

Related and already in-tree: `wall-rotation.list` no longer carries
`nyxus-hacker-mode-a/b` in ambient rotation.

## 3. SDDM LOGIN BACKGROUND → URBAN ALIEN ✅

Live background was `nyxus-ink-swirl.png` (cosmic swirl, off-theme). Now
`nyxus-login-wall.png` (urban-alien graffiti, matches hyprlock's UFO art),
scaled `1920x1080^` + centre-extent so the panel never letterboxes.

**Also fixed the regenerator:** `sddm-theme/install.sh`'s background priority
chain had `nyxus-login-stars.png` (starfield) winning, which is why the login
screen kept drifting away from the theme. New order: `nyxus-login-wall.png` →
`nyxus-urban-alien.png` → `nyxus-login-stars.png` → bundled → network.

## 4. "SHADOW BLOCKS" AROUND THE BARS ✅

Owner reported dark rectangular blocks around the left/right rails and parts of
the bottom bar. **Not** Hyprland blur — A/B'd with `decoration:blur:enabled`
off/on, bars rendered identically.

Cause: `@mixin obsidian-vessel` (`eww.scss.source` ~line 44), shared by **every**
rail pill, bottom-bar orb, ticker tile, brand and clock. It carried:
- `0 6px 18px rgba(0,0,0,0.62)` — a hard ink drop shadow with no falloff room;
  on a 38px pill that reads as a rectangular **block**, not a shadow. (59 sites.)
- `background-color: rgba(8,3,16,0.985)` — effectively opaque, so Hyprland's
  dual-kawase layer blur had nothing to show through; every pill was a flat
  black tile.

Fixed: drop shadow removed, background → `0.55` (still well above the
`ignore_alpha 0.2` layerrule threshold, so bars stay blurred), inset softened
`.52` → `.32`. `.brand` / `.brand:hover` had the same token hardcoded outside
the mixin — fixed too.

## 5. BAR REDESIGN (owner-requested) ✅

### Side rails — "NEON SPINE" (fully redesigned, hand-built, no external art)
- A glowing tube runs the rail behind the caps, drawn purely with gradient
  colour **stops** (never `background-size` — see §7). Caps read as beads on a
  lit wire instead of loose floating tiles.
- Caps are slanted graffiti keycaps (`border-radius: 16px 5px 16px 5px`) with a
  chrome bevel, not plain rounded squares. 42x42, 2px neon rim.
- Glow carries state: idle dim → hover bloom → active full bloom. The live
  workspace is a lit spray-tag (violet→magenta→orange gradient, white rim).
- **Per-hue rules are GENERATED from the accent colours already resolved in
  `eww.css`**, so the accent engine keeps control of the palette and nothing is
  hardcoded to today's purple. Note the hue *names* do not match literal
  colours (`app-pill-green` currently resolves to magenta) — that is the accent
  remap, not a bug. Regenerate rather than hand-editing colours.

### Top ticker — kept, with a lit rail
Owner wanted the ticker to stay but do more. Added a neon rail under the crawl
(gradient on `.bar-top-ticker-only`) plus label glow/letter-spacing.

### Bottom metrics — style kept, more phosphor
Owner likes the graphs; only spacing + glow changed. Cluster spacing 14 → 26
(they were cramped), plus `.mon-trace` / `.mon-glyph` text glow.

### Bottom hub — saucer ↔ 1980s ALIEN BOOMBOX flip
- Asset: `eww/assets/nyxus-boombox-band.png`, built from
  `Meshy_AI_nyxus-boombox-transparent-v4.png`.
  **That source is NOT transparent** despite the filename (solid black
  backdrop). Keyed with a **four-corner alpha floodfill** — a global
  black→transparent eats the boombox's own dark chrome body.
- Cropped to the speaker deck `1254x360 at y480`, centre-extended to
  `1254x380`. **y470 slices the woofer bottoms** (that was the owner's "cut off
  at the bottom"); **y850+ catches the NYXUS graffiti tag**. Top/bottom edges
  **feathered** to transparency — a hard cut through the chassis is what read as
  "not clean". Radial bloom baked in behind.
- **Both faces scaled 116px → 150px tall** (saucer min-width 551, boombox 495).
  The `bar-bottom` window auto-grows to its content, so the layer and the
  reserved zone grew with it.
- **APERTURES ARE MEASURED, NEVER EYEBALLED** (the yuck has carried a warning
  about this since the art last changed): saucer cockpit `646x192 of 1351x368`;
  boombox display `424x294 of 1254x380` → renders 167x116 at the 150px height,
  centre 4.2px above band centre → `margin-bottom: 6px`.
- Panel `.saucer-screen-music`: 158x108, **opaque** (translucent let the art
  bleed through behind the text and looked dirty), **no border** — the art
  already paints a green+magenta bezel and a second ring inside it was the main
  "muddy" complaint. Styled as a backlit VFD (phosphor scanlines + top-lit
  wash). Chrome transport keys.
- **Bass reaction:** display glow driven inline by `CAVA_BASS`, plus two
  `boombox_cone` overlay discs on the MEASURED cone centres (x=205/1045 of 1254
  → 81px/412px at the 495px render width). They **must be rings** (transparent
  centre, border + outer glow) — filled discs paint flat colour straight over
  the cone art and wash the woofers out.

## 6. OPEN / NOT DONE

- **Greeter first-attempt error.** Login works, but the journal still shows one
  `HELPER_DISPLAYSERVER_ERROR` before SDDM recovers and the greeter succeeds.
  Investigate; it means it is falling back rather than succeeding first try.
- **Boombox art direction.** Owner wants a bolder **flat pop-art / screenprint**
  look (high-contrast, glitch marks) in the NYXUS palette, rather than the
  current detailed chrome render. Owner has since said **do not use Meshy** —
  design it in-house. No image-generation tool is available to agents; only
  ImageMagick transforms.
- **Boombox pulse + track readout are WIRED BUT UNVERIFIED** — `PLAYER` is a 1s
  defpoll and `CAVA`/`CAVA_BASS` are deflisten-fed, so injected test values are
  overwritten before a screenshot lands. Needs a real track playing.
- **hypridle**: it *does* lock, but only via suspend at 600s
  (`before_sleep_cmd` → `loginctl lock-session` → hyprlock). There is **no
  dedicated lock listener**. hyprlock's background already matches the theme.
- **Wall rotation** still carries pure-space scenes with no urban element
  (`black-void`, `deep-void-stars`, `milkyway-void`, `big-bang`) — trim
  candidates if "urban" is the bar.
- **Ticker art** (`Meshy_AI_nyxus-ticker-bar-transparent.png`) has a grey
  checkerboard **baked into the pixels** (corner = `srgb(127,126,125)`).
  Colour-keying will not fix it; it needs a re-export. Not used.
- **Side dock art** (`nyxus-{left,right}-dock.png`) is staged in `eww/assets`
  but **not wired** and now superseded by the hand-built rails above. Aspect was
  the blocker: 937x1678 (0.56) vs a 56x756 rail (0.074).

## 7. TOOLCHAIN TRAPS (cost real time — do not rediscover)

- **`sass` is NOT installed on this box.** `eww/scripts/compile-eww-css.sh`
  silently **no-ops** without it (`exit 0`). Editing `eww.scss.source` alone
  changes nothing on screen. `nyxus-apply-accent` calls the same script, so
  **nothing on this machine regenerates `eww.css`**.
- **The live `eww.css` has DRIFTED from `eww.scss.source`** (~164 lines):
  formatting *and* several resolved colours differ
  (`rgb(100%,67.9%,38.2%)` vs `rgb(255,160.5,127.6)`). **Never overwrite
  `eww.css` with a wholesale recompile — it shifts the palette.**
- **Therefore: append an OVERRIDE BLOCK at the end of `eww.css`.** GTK CSS
  resolves equal-specificity conflicts by document order, so a later
  single-class rule beats the same selector earlier in the sheet without editing
  any existing line. Mirror it verbatim at the end of `eww.scss.source`. All
  2026-07-26 bar work lives in those blocks and reverts by deleting them.
  To compile for validation only:
  `npx --yes sass --no-charset --load-path=. eww.scss.source /tmp/out.css`.
- **The compile step STRIPS `background-size`** (and width/height/position/etc).
  Background images set from CSS cannot be scaled — pre-scale the PNG, or set
  size via inline `:style` in `eww.yuck`, which is NOT stripped.
- **Reload with `eww reload`.** `nyxus-eww-launch-safe` only launches when
  something is down — it prints "nothing to do" and does **not** pick up CSS
  changes. Repeated kill/reload cycles can leave two daemons → double bars.
- **Three surfaces must stay in sync** for every bar change: live
  `~/.config/eww/`, repo `artifacts/api-server/nyxus-scripts/eww/`, and ISO skel
  `iso-builder/nyx-profile/airootfs/etc/skel/.config/eww/`.
- Backups from this session: `eww.{scss.source,css}.bak-20260726-shadowfix`.

## 8. ALSO IN THIS COMMIT (pre-existing, from an earlier session)

- `hyprland.conf`: 0.6s head-start on `nyxus-persist-login` so the wallpaper has
  a frame before the bars' exclusive zones claim space (cold-boot box artifact).
  Not a bootstrap/network gate — still offline-first.
- `wall-rotation.list`: hacker-mode walls removed from ambient rotation.
