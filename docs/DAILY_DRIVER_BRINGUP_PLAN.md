# NYXUS Daily Driver — Urban-Neon Bring-Up Plan

> Investigation + minimal wiring + phased plan for taking the **locked**
> "Daily Driver" urban-neon direction (teal + amber, frosted dark glass,
> corner-bleed) from approved mockups to a bootable themed desktop.
> Companion to [`DAILY_DRIVER_PRODUCT_BRIEF_2026-08-01.md`](./DAILY_DRIVER_PRODUCT_BRIEF_2026-08-01.md)
> (product brief, §4 = locked visual direction). This doc is the **technical
> bring-up**: real repo paths, the wallpaper/theming pipeline, the **edition
> mechanism**, live-wallpaper options, a design-token spec, and an ordered
> phase 0/1 plan.
>
> ### ⛔ OWNER DECISION (2026-08-01): Daily Driver is a SEPARATE, ADDITIVE EDITION
> The existing **alien-neon** build stays **EXACTLY as-is** and remains the
> default. Its `prism` palette (`accent.json` active=`prism`), its default
> wallpaper (`nyxus-urban-alien`), and its hacker-themed shell must **never** be
> touched by Daily Driver work. Urban-neon (teal+amber) is a **new edition built
> alongside** it in this same repo — selected at bake time, never by regressing
> the shared/alien defaults. This plan is written so the alien build can be baked
> byte-for-byte unchanged.
>
> Status (2026-08-02): the click-audit gate is satisfied and **Phase 1 is
> partly built** — the `NYX_EDITION` bake hook, gate `13pm`, and the daily
> accent / wallpaper / rotation / greeter / lock files all exist and are green
> on both ISO linters. **Still no bake, no palette flip, no default change to
> the shared build**; `NYX_EDITION` defaults to `alien` and the block is an
> untaken branch. The Win11-shaped eww shell (bar, launcher, flyout) has **not**
> been started. Step-by-step status is in §7.

---

## 1. Wallpaper / theming pipeline (how the desktop is actually painted)

### 1.1 Where wallpapers live (source of truth vs. shipped)

- **Canonical bake source:** `artifacts/api-server/nyxus-scripts/` (referred to
  as `NS` in the builder). `iso-builder/build-iso.sh` (~L782–802) stages walls
  from here:
  - `install -m0644 "${NS}"/nyxus-*.png` → **both** `usr/share/backgrounds/nyxus/`
    (system) **and** `etc/skel/.config/hypr/walls/` (per-user skel).
  - rotation art: `"${NS}"/hypr-walls/rotation/*.png` → `.../rotation/` in both
    trees. The root glob is `nyxus-*.png`, so **a wall must be named
    `nyxus-*.png` and sit in `NS` root** (not just `hypr-walls/`) to ship as a
    selectable wallpaper.
- **Shipped locations (committed airootfs mirror):**
  - `iso-builder/nyx-profile/airootfs/usr/share/backgrounds/nyxus/*.png` (+ a
    `manifest.tsv` — slug⇥display, enforced 1:1 by `verify-profile.sh` gate,
    §13c orphan/parity checks).
  - `iso-builder/nyx-profile/airootfs/etc/skel/.config/hypr/walls/` (+ `rotation/`).
  - Greeter/SDDM-theme copies under `.../usr/share/sddm/themes/nyxus/backgrounds/`.

### 1.2 How the default wallpaper is selected at first boot

1. **Persisted choice** — `etc/skel/.config/nyxus/wallpaper.conf`:
   ```
   WALLPAPER="nyxus-urban-alien"
   WALLPAPER_PATH="/usr/share/backgrounds/nyxus/nyxus-urban-alien.png"
   ```
   plus `wallpaper.json` (favorites, tint, fit, live_preset).
2. **Autostart** — Hyprland `exec-once` (see
   `etc/skel/.config/hypr/conf.d/nyxus-services.conf`) runs
   `nyxus-live-wallpaper auto` if present, else `nyxus-wallpaper-autostart`.
   - `usr/local/bin/nyxus-wallpaper-autostart` sources `wallpaper.conf`, and if
     the absolute path doesn't resolve (a different `$HOME` was baked in) it
     recovers via the `WALLPAPER=` **slug** under this user's home, then falls
     back to the shipped default
     `/usr/share/backgrounds/nyxus/nyxus-urban-alien.png`. It hands off to
     `nyxus-set-wallpaper` (awww/swaybg backend).
3. **Live-wallpaper controller** — `usr/local/bin/nyxus-live-wallpaper` reads
   `etc/skel/.config/nyxus/livewall.conf` (`LIVE=on`); if on, it plays a looped
   MP4 via **mpvpaper** on the Wayland `background` layer, otherwise it lets the
   per-workspace still daemon (`nyxus-ws-wallpaperd.service` → `awww-daemon`)
   own the background. First boot shows the still immediately and renders the
   loop in the background to avoid a blank desktop.
4. **hyprpaper is RETIRED** — `etc/skel/.config/hypr/hyprpaper.conf` is
   intentionally empty; wallpaper is owned by awww / `nyxus-live-wallpaper`.

### 1.3 Skel + first-boot delivery (per HANDOFF)

- Core desktop config ships in **`/etc/skel`**; `useradd -m` copies it into
  every home. The offline-complete core is what boots (no network dependency).
- `usr/local/bin/nyxus-bootstrap` / `nyxus-wait-bootstrap` handle first-boot
  provisioning; `airootfs/root/customize_airootfs.sh` builds AUR bits
  (mpvpaper, awww↔swww shim) and provisions greeter dirs.
- `build-iso.sh` **wipes** `skel/.config/hypr` and `skel/.config/eww` then
  restages from `NS`, so those trees' source of truth is `NS`, **not** the
  committed skel copy.

### 1.4 Greeter / lock / accent

- **Greeter:** greetd + regreet. `etc/greetd/{config.toml,regreet.toml,regreet.css}`
  + `nyxus-login-bg.png`; `nyxus-greeter` re-pins the login background and
  rescales the card margins per detected panel. SDDM is absent (greetd is sole DM).
- **Lock:** `etc/skel/.config/hypr/hyprlock.conf` (+ `hyprlock-accent.conf`,
  generated).
- **Accent/theme tokens:** `etc/skel/.config/nyxus/accent.json` (active preset
  `prism`, `follow_wallpaper: false` — **locked off**), consumed by
  `etc/skel/.config/eww/accent.scss` (generated by `nyxus-apply-accent`). GTK is
  `adw-gtk3-dark`; Qt via qt5ct/qt6ct.

---

## 2. Are the approved images "in the system"?

**No — not before this change.** The approved reference mockups and candidate
wallpapers lived **only** in the Cursor assets dir
(`~/.cursor/projects/home-cosmic-Nyxus-Core/assets/`), outside the repo, so
nothing shipped in any ISO.

- The **5 UI mockups** (`set-desktop/notifications/launcher/login/lockscreen`)
  are reference only — they must **not** ship as wallpapers.
- The correct in-repo home for shipped wallpapers is the pair described in
  §1.1: `artifacts/api-server/nyxus-scripts/` (bake source, `nyxus-*.png`) with
  a mirror in `iso-builder/nyx-profile/airootfs/usr/share/backgrounds/nyxus/`
  (+ `manifest.tsv`) and `.../etc/skel/.config/hypr/walls/`.

### What this change wired in (minimal, reversible)

Candidate wallpapers copied (renamed to the `nyxus-*` convention) into **all
three** wall locations, matching how existing hero art (`nyxus-urban-alien`) is
placed:

| Source (assets) | Shipped slug |
|---|---|
| `urban-flower-concrete.png` | `nyxus-urban-flower-concrete.png` |
| `urban-flower-wall.png` | `nyxus-urban-flower-wall.png` |
| `urban-astronaut-moonwalk-v2.png` | `nyxus-urban-astronaut-moonwalk.png` |
| `nyxus-hero-cosmic.png` | `nyxus-hero-cosmic.png` |

- Added to `NS` root, `airootfs/usr/share/backgrounds/nyxus/`, and
  `airootfs/etc/skel/.config/hypr/walls/`.
- `manifest.tsv` updated with the 4 new slug⇥display rows (parity gate).
- The **5 UI mockups** were copied to a docs reference dir
  `docs/assets/daily-driver/` (reference only; not shipped as walls).

**Default wallpaper was NOT changed, and never will be for the shared/alien
build.** The urban walls added above are **inert assets** for the alien build —
files present on disk, but nothing references them, so `nyxus-urban-alien`
stays the alien default. Making an urban wall the *default* is an
**edition-scoped** change (see §3 editions + §7 Phase 1), applied only when
`NYX_EDITION=daily`, never to the shared skel.

**Linters (run because `iso-builder/` was touched):**
`bash iso-builder/verify-profile.sh` → **PASS** (exit 0; only the standing
Hyprland host-vs-ISO version-skew WARN). `bash scripts/iso-build-verify.sh` →
**193 checks passed.** No executables added, so gate `13pc`
(`file_permissions`) was unaffected — `regen-file-permissions.py` not needed.

---

## 3. Editions / build-time variants (how alien and daily coexist)

### 3.1 The builder already has a variant pattern

`iso-builder/build-iso.sh` is driven by **env-var toggles read early and used to
gate what gets staged** — the exact shape an edition flag should take:

| Flag | Effect | Pattern |
|---|---|---|
| `NYX_WITH_KAGE_RYU` (default `1`) | swaps primary kernel + rewrites boot menus (L204–281, L452) | boolean gate |
| `NYX_ISO_TIER=full\|lean` (L197–202) | **swaps a whole staged file** — copies `packages.x86_64.lean` over `packages.x86_64` when `lean` | **file-swap by variant** |
| `NYX_SQUASH_COMP`, `NYX_COW_SPACESIZE`, `NYX_ISO_DATE`, `NYX_MIN_FREE_MB` | tuning knobs | env override |

`NYX_ISO_TIER=lean` is the precedent to copy: a variant name selects an
alternate staged file, defaulting to the untouched baseline. **There is no
existing `NYX_EDITION`** — it does not exist yet; this is the net-new hook.

### 3.2 How theme files ship today (what an edition must swap)

- `accent.json`, `wallpaper.conf`, `wallpaper.json`, `wall-rotation.list` live in
  `airootfs/etc/skel/.config/nyxus/`. **That subtree is NOT in the bake's wipe
  list** (only `skel/.config/hypr` and `skel/.config/eww` are wiped + restaged
  from `NS`), so these ship **as committed in git** → the alien defaults are
  baked in by virtue of being the committed content.
- `accent.json` is consumed by `nyxus-apply-accent`, which regenerates
  `eww/accent.scss`. Its committed `_comment` **locks** `active` to `prism` and
  forbids other presets — so the urban preset must **not** be added to the
  shared file.
- Hypr/eww/greeter code (`hyprlock.conf`, `hyprlock-accent.conf`, eww SCSS,
  `regreet.css`) is structurally shared; only the **token values** differ per
  edition.

### 3.3 Recommended mechanism: build-time `NYX_EDITION` (not a runtime switch)

**Recommendation: a build-time `NYX_EDITION=alien|daily` flag, defaulting to
`alien`.** It mirrors `NYX_ISO_TIER` exactly and gives the strongest guarantee
the owner asked for: with the default, **zero bytes change** vs. today's alien
build (the block is a no-op), so alien can never regress.

Why not a runtime (first-boot/Settings) theme switch as the primary mechanism:
- It forces the **shared** image to carry *both* palettes, *both* shells, a
  switcher UI, and live regeneration of greeter/hyprlock/wallpaper/shell — i.e.
  it puts urban-neon code **inside the alien default**, the opposite of "alien
  stays exactly as-is."
- Greeter (`regreet.css`) and lock backgrounds are pinned at bake / greeter
  start; swapping them live is fragile and risks a lockout (HANDOFF documents
  the greeter card-margin lockout class of bug).
- Accent alone *is* runtime-switchable (`nyxus-apply-accent` already exists), so
  a Settings accent toggle is a fine **later** add **within the daily edition** —
  but it should not be the thing that defines the edition.

**Concrete `NYX_EDITION` implementation (new, ~1 gated block in build-iso.sh):**

1. Add edition variant files as **siblings** (baseline stays untouched):
   - `artifacts/nyxus-config/editions/daily/accent.json` — active=`urban-neon`,
     presets hold the teal/amber tokens (§5).
   - `.../editions/daily/wallpaper.conf` + `wallpaper.json` — default
     `nyxus-urban-flower-wall`.
   - `.../editions/daily/wall-rotation.list` — urban walls only.
   - `.../editions/daily/regreet.css`, `hyprlock-accent.conf`, and eww
     SCSS/`stations*.json` overrides for the Win11-shaped daily shell.
   - (`artifacts/nyxus-config/` already holds the canonical `accent.json` /
     `wallpaper.*` sources; an `editions/daily/` subdir is the natural home.)
2. In `build-iso.sh`, **after** skel assembly (after L618+ config staging,
   before squashfs), add:
   ```sh
   NYX_EDITION="${NYX_EDITION:-alien}"
   if [[ "${NYX_EDITION}" == "daily" ]]; then
     ED="${NS}/editions/daily"   # or artifacts/nyxus-config/editions/daily
     install -m0644 "${ED}/accent.json"       "${SKEL}/.config/nyxus/accent.json"
     install -m0644 "${ED}/wallpaper.conf"    "${SKEL}/.config/nyxus/wallpaper.conf"
     install -m0644 "${ED}/wallpaper.json"    "${SKEL}/.config/nyxus/wallpaper.json"
     install -m0644 "${ED}/wall-rotation.list" "${SKEL}/.config/nyxus/wall-rotation.list"
     install -m0644 "${ED}/regreet.css"       "${PROFILE_DIR}/airootfs/etc/greetd/regreet.css"
     # regenerate eww accent.scss from the daily preset; stage daily shell shards
     ok "NYX_EDITION=daily — urban-neon theme staged (alien untouched by default)"
   fi
   ```
3. Stamp the ISO name/label with the edition (as tier/kernel are stamped, L514).
4. Add a `verify-profile.sh` guard: with no `NYX_EDITION` (alien default), the
   committed `accent.json` active **must** be `prism` and `wallpaper.conf`
   **must** be `nyxus-urban-alien` — a gate so Daily work can never silently
   change the shared default.

---

## 4. Live / animated wallpaper options on Hyprland

The stack **already ships the machinery** for a living wallpaper — this is a
question of asset + tuning, not new infrastructure.

| Option | What it is | Fit here | Cost |
|---|---|---|---|
| **mpvpaper** (video) | mpv on the Wayland background layer | **Already wired** (`nyxus-live-wallpaper`, `livewall.conf LIVE=on`, mpvpaper built in `customize_airootfs.sh`). IPC socket already exposed for live speed/hue. | GPU decode is cheap; **battery/CPU cost is real on a laptop** — a 4K loop decodes continuously. Mitigate with 1080p, ~24fps, a short seamless loop, and pausing on lock/idle. |
| **swww/awww** (animated transitions) | still images with GPU crossfade/wipe transitions | Backend is already the still-wallpaper owner (`awww-daemon`). Great for an *ambient shuffle* of the urban-flower/astronaut stills with a slow dissolve — "alive" without a video. | Near-zero idle cost. Not truly animated. |
| **glpaper / shader** | GLSL shader on the background layer | Most "breathtaking" ceiling (parallax neon rain, drifting fog) and lowest asset weight, but glpaper is unmaintained and not packaged; would need a new AUR build + a hand-written shader. | Low runtime cost if simple; **high build/maintenance cost**, new package risk. |

**Recommendation:** stay on **mpvpaper** as the flagship live path (it's the
one already integrated, guarded, and fallback-safe), and pair it with an
**awww slow-dissolve shuffle** of the urban-neon stills as the default
"alive-but-cheap" experience. Reserve glpaper/shader as a later stretch goal.

**Asset needed for the mpvpaper flagship:** a **seamless looping MP4** of one of
the locked urban-neon scenes (e.g. `nyxus-urban-flower-wall`) — 1920×1080,
~20–30s loop, ~24fps, no audio, subtle motion (rain streaks, neon flicker,
distant traffic, a slow parallax push). Drop it at
`NS/hypr-walls/live/` and render/stage it to
`~/.config/hypr/walls/live/nyxus-livewall-flagship.mp4`
(`nyxus-livewall-flagship` can also render a loop from a still via ffmpeg as a
fallback). Default to `LIVE=off` on battery-class hardware; expose the toggle in
Settings.

---

## 5. System identity / cohesion — design-token spec

One named token module (mirroring lab's `nyxus_palette`) feeds **every** shell
surface: GTK theme, eww/bar, hyprlock, greeter (regreet.css), and app accents.
No freehand hex in apps.

**Hex values sampled directly from the approved mockups** (teal glow, amber
signage, dark base):

```
# ── NYXUS Daily Driver · Urban-Neon tokens ────────────────────
# Accent — TEAL (primary): glow edges, active states, primary highlights
accent-teal          #2ee6d6   # core primary
accent-teal-glow     #8ffcff   # bright edge / neon glow (sampled ~#82ffff)
accent-teal-deep     #0f8593   # pressed / deep fill (sampled core)

# Accent — AMBER (secondary): signage warmth, secondary highlights
accent-amber         #ff9d2e   # core secondary
accent-amber-glow    #ffca55   # bright signage (sampled)
accent-amber-deep    #bd7730   # deep fill (sampled core)

# Base — dark, slightly cool/teal-tinted near-black
base-void            #06090c   # deepest bg (sampled dark ~#070f10)
base-surface         #0d1418   # panel body under frost
base-elevated        #131b21   # cards / tray rows

# Text
text-primary         #eef2fa
text-muted           #a7b2bd
text-dim             #6a7178

# Signal (reuse existing semantics, retuned toward the palette)
signal-ok            #39ff14
signal-warn          #ff9d2e   # = amber
signal-danger        #ff2d55   # errors only, never focus

# ── Frosted glass / corner-bleed material ─────────────────────
glass-fill           rgba(9, 16, 20, 0.55)    # panel body (frost tint)
glass-fill-strong    rgba(9, 16, 20, 0.72)    # dense panels (flyout/launcher)
glass-border         rgba(46, 230, 214, 0.45) # 1px teal edge
glass-glow           rgba(46, 230, 214, 0.30) # outer teal glow bloom
corner-radius        18px                      # panels / cards
corner-radius-sm     12px                      # tray chips / list rows
corner-bleed         # panel corners fade to transparent (radial alpha
                     # falloff) so the wallpaper reads through — compositor
                     # layer blur + GTK/eww alpha; NOT true per-widget CSS blur
glow-blur            22px                      # box-shadow spread for neon edge
```

**Where each token lands** (all in the **daily edition** files — never the
shared/alien ones):
- **accent.json (edition-specific)** — the daily edition's
  `artifacts/nyxus-config/editions/daily/accent.json` sets active=`urban-neon`
  with preset (`primary=#2ee6d6`, `secondary=#ff9d2e`, `warn=#ff9d2e`,
  `ok=#39ff14`), `follow_wallpaper:false`. The **shared** `accent.json` stays
  alien `prism`, unchanged.
- **eww** — `accent.scss` regenerated by `nyxus-apply-accent`; glass + corner
  tokens go in the eww SCSS partials (bar, flyout, launcher).
- **hyprlock** — `hyprlock-accent.conf` (generated) picks up teal/amber;
  card uses `glass-*` + `corner-radius`.
- **regreet.css** — swap the ALIEN NEON violet/magenta header comment + values
  (`#7d3dff/#ff2dad`) for teal/amber; keep the per-panel margin rescale logic.
- **GTK/Qt** — `adw-gtk3-dark` base + an accent override where supported.

**Notification "saucer":** the quick-settings / notification flyout
(mockup `set-notifications.png`) is the signature widget — a rounded frosted
card (`glass-fill-strong`, `corner-radius`, teal `glass-border` + `glass-glow`)
holding toggle pills, sliders, a calendar, a now-playing card, and stacked
notification rows. That same card recipe (fill + border + glow + radius) is the
**shared widget language** reused by the launcher panel, greeter/lock cards, and
per-app dialogs — so the whole system reads as one identity.

---

## 6. Shared (edition-neutral) vs. edition-specific files

The dividing line that protects the alien build: **shared files must stay
edition-neutral** (Daily work may add to them only in ways inert to alien, or
not touch them at all). **Edition-specific content lives in
`artifacts/nyxus-config/editions/daily/`** and is only staged when
`NYX_EDITION=daily`, so it can never regress alien.

### SHARED — must NOT change behavior for the alien default
| File / area | Why it stays neutral |
|---|---|
| `airootfs/etc/skel/.config/nyxus/accent.json` | stays alien `prism`; edition swaps it at bake, never edits it |
| `airootfs/etc/skel/.config/nyxus/wallpaper.conf` / `wallpaper.json` | stays `nyxus-urban-alien` default |
| `airootfs/etc/skel/.config/nyxus/wall-rotation.list` | stays alien-only rotation |
| `usr/share/backgrounds/nyxus/*.png` + `manifest.tsv` | urban walls added here are **inert assets** for alien (present but unreferenced) — safe |
| `etc/skel/.config/hypr/walls/` (+ skel copies) | same — additive files only |
| Shell **code**: eww `eww.yuck`/SCSS structure, `hyprlock.conf`, `regreet.toml`, `nyxus-greeter`, `nyxus-apply-accent`, `nyxus-live-wallpaper` | structure is shared; only token *values*/staged variants differ. **Caveat found 2026-08-02 — see §6.1:** two of these hardcode alien *values*, so "structure only" was not true |
| **Notification daemon** — `dunst` `exec-once` in `hyprland.conf`; `swaync` masked at `etc/systemd/user/swaync.service` | alien keeps **dunst** and its appearance is unchanged. The mask is what stops the two racing (audit §11.4). Both packages stay in `packages.x86_64` — Daily needs swaync |
| `iso-builder/build-iso.sh` (baseline paths), `verify-profile.sh`, `scripts/` | the edition hook is **additive** and default-off |
| `stations.json` / `stations-hacker.json` (alien hacker shell) | untouched; daily ships its own shell shards |

### EDITION-SPECIFIC — only staged when `NYX_EDITION=daily`
| Surface | Daily edition file (new) |
|---|---|
| Accent preset | `artifacts/nyxus-config/editions/daily/accent.json` (active=`urban-neon`) — **done** |
| Default wallpaper | `.../editions/daily/wallpaper.conf` + `wallpaper.json` (`nyxus-urban-flower-wall`) — **done** |
| Rotation | `.../editions/daily/wall-rotation.list` (urban walls) — **done** |
| Greeter theme | `.../editions/daily/regreet.css` (teal/amber) — **done** |
| Lock accent | `.../editions/daily/hyprlock-accent.conf` — **done** |
| **Notification daemon** | **swaync.** The daily block deletes the alien mask and rewrites the staged skel's `exec-once = dunst` → `exec-once = swaync`. The approved flyout (calendar, quiet hours, quick-toggle pills — `set-notifications.png`) is a swaync control-centre feature set dunst has no equivalent for |
| Lock + login background | not a file — the daily block **re-pins** `hyprlock.conf`'s `path =` and `nyxus-greeter`'s `_pick=` on the throwaway profile copy (§6.1) |
| Bar/flyout/launcher | `.../editions/daily/eww/*` (Win11-shaped shell + glass tokens) — **not started** |
| Shell layout | `.../editions/daily/stations*.json` / hypr conf.d overrides — **not started** |
| Live wall default | `.../editions/daily/livewall.conf` + flagship loop asset — **not started** |
| Bake hook | new `NYX_EDITION` block in `build-iso.sh` (default `alien` = no-op) — **done** |

Shared **structural** files the edition *reads through* (unchanged, values
supplied by the staged edition files): `nyxus-apply-accent` → `eww/accent.scss`,
`hyprlock.conf`, `nyxus-greeter`, `nyxus-live-wallpaper`, GTK `adw-gtk3-dark` +
qt5ct/qt6ct.

### 6.1 Correction (2026-08-02): "shared structure, edition values" was not true

Two of the files listed above as purely structural carry **alien values** in
their bodies, and Phase 1 hit both:

- `hyprlock.conf` names `/usr/share/backgrounds/nyxus/nyxus-urban-alien.png` in
  its `background { path = }` block.
- `nyxus-greeter` copies `$_wdir/nyxus-urban-alien.png` over the greeter cache
  on **every** start, so it wins over anything staged at `/etc/greetd/`.

Left alone, a Daily stick would wear urban-neon on the desktop and the alien
mural on its lock and login screens. Both are asserted by `verify-profile` gate
`13ua` on the committed trees, so neither can be edited in git without failing
the linter — which is correct, because that pin *is* the alien build.

**How it was resolved:** the daily staging block rewrites those two lines on the
**throwaway profile copy** at bake time, one anchored `sed` each, asserting the
anchor matched before and that nothing names the old hero after. Every committed
byte stays alien; only the daily bake diverges. Prefer this shape over adding an
edition variable to shared code — it keeps the "alien does not change by a byte"
guarantee literal, and a re-wording upstream fails the bake loudly instead of
silently shipping alien art.

**Still unresolved — the greeter card is right-parked, the mockup is centred.**
`regreet.css` positions the login card with absolute pixel margins, and the pair
of margins is also what sets the card's **width** (`1920 − 1360 − 40 = 520px`).
GTK4 CSS has no percentage margins and no `halign`, so "centred" cannot be
expressed in the stylesheet at all. `nyxus-greeter` recomputes both margins for
the detected panel — it must, or absolute pixels lock the operator out on a
narrower screen — using a card centre hardcoded at `0.845 × W`, chosen because
the alien art is centre-composed and the card had to clear the figure.
`set-login.png` shows the card centred over the alley. Centring Daily therefore
requires making the card centre an **input** to that arithmetic (e.g. a
declaration read out of the stylesheet, defaulting to today's formula when
absent, so alien is bit-identical). Not attempted this session: `nyxus-greeter`
is the documented lockout-class file and the change deserves its own review.
The daily `regreet.css` deliberately ships the *same* right-parked numbers the
shared greeter computes, so the never-lock-out fallback and the generated sheet
agree — do not "fix" it by editing those two numbers alone.

---

## 7. Phase 0/1 — ordered first steps (additive edition, alien untouched)

Every step names real paths and marks **[headless]** (validated by the profile
linters here) vs **[VM]** (needs a bake + UEFI boot). **No step edits the shared
alien defaults.** The shared build is proven unchanged by baking with the
default `NYX_EDITION=alien` (no-op) and confirming it's byte-identical to today.

**Phase 0 — additive assets in the tree (this change, done):**
0.1 Add the 4 candidate walls to `NS` + airootfs backgrounds + skel walls (inert
    assets for alien), update `manifest.tsv`. **[headless — PASS]**
0.2 Land the 5 UI mockups in `docs/assets/daily-driver/` as reference. **[headless]**
0.3 This doc + HANDOFF pointer. **[headless]**

**Phase 1 — stand up the `daily` edition (nothing shared flips):**
1.1 ✅ **DONE 2026-08-02.** **Create the edition hook.** `NYX_EDITION` is read
    in `iso-builder/build-iso.sh` right after `ISO_NAME=`, validated to
    `alien|daily` (anything else exits non-zero), and renames the output to
    `nyxus-daily-<date>-x86_64.iso`. The staging block is the **last** staging
    step, before the `file_permissions` derivation. It is recorded in
    `/etc/nyxus-build` as an `edition` line. **[headless — `bash -n`]**
    *Two corrections to §3.3's sketch, both found by doing it:* the block goes
    after **every** staging step, not "after L618" — `greetd/regreet.css` is
    staged around L977 and Arsenal/Meli/jeTT later still, so an earlier
    placement is overwritten by the alien copies; and the edition dir is
    `${REPO_ROOT}/artifacts/nyxus-config/editions/daily`, not `${NS}/editions/`.
    *Gotcha:* `/etc/nyxus-build` is printed at login by a **positional**
    `sed -n '3,7p'` in the generated `profile.d/nyxus-build-stamp.sh`, so adding
    the `edition` field required widening it to `3,8p` or the banner would have
    silently dropped `iso label`. The `iso_label` itself is **not** stamped per
    edition — it must stay identical across profiledef and all five
    `archisolabel` refs or live media will not boot.
1.2 ✅ **DONE 2026-08-02.** **Guard the shared default** — `verify-profile.sh`
    gate **`13pm`**. Asserts: skel `accent.json` active is `prism`; skel
    `wallpaper.conf` names `nyxus-urban-alien` in both the slug and
    `WALLPAPER_PATH`; `NYX_EDITION` still defaults to `alien` and the block is
    still guarded on `== daily`; every file the daily block installs exists,
    is non-empty and (for `.json`) parses; `editions/daily/accent.json` is
    actually `urban-neon`; and every wall the daily configs name is both on
    disk **and** in `backgrounds/manifest.tsv`. The required-file list is read
    out of `build-iso.sh`'s own loop rather than duplicated, so adding a file to
    the staging block automatically makes it required. Proved in both
    directions with eight deliberate breakages. **[headless]**
1.3 ✅ **DONE 2026-08-02.** **Author edition files** under
    `artifacts/nyxus-config/editions/daily/`: `accent.json` (active=`urban-neon`,
    §5 teal/amber + `_palette_fixed`/`_glass` token blocks), `wallpaper.conf` +
    `wallpaper.json` (`nyxus-urban-flower-wall`), `wall-rotation.list` (the four
    approved urban walls). **[headless]**
1.4 ◑ **PARTIAL 2026-08-02 — greeter + lock done, eww shell not started.**
    `regreet.css` (teal/amber glass card; focus ring is **teal**, `#ff2d55`
    appears in exactly one rule, `.error`) and `hyprlock-accent.conf` (the ten
    variables `nyxus-apply-accent` §3 generates, from `#2ee6d6` / `#ff9d2e`)
    are authored and staged. The per-panel margin rescale in `nyxus-greeter` is
    untouched and the daily sheet keeps the line shape it rewrites — but see
    §6.1: the card lands **right-parked**, not centred as `set-login.png` shows,
    and that needs a `nyxus-greeter` change. The Win11-shaped eww shell
    (`eww/*`) is **not started** and is the next large chunk.
    **[headless lint; bare metal for visual — hyprlock renders nothing under
    `virtio-vga-gl`, audit §11.5]**
1.5 ☐ **Daily live wall** (optional): `livewall.conf` default + mpvpaper
    flagship loop asset (§4); pair with an awww slow-dissolve still shuffle.
    **[headless]**
1.6 ✅ **DONE 2026-08-02 for the alien path.** `bash -n build-iso.sh` clean,
    `verify-profile.sh` **0 FAIL**, `iso-build-verify.sh` **193/193**, gate
    `13pc` did not trip (nothing executable was added). The three bake-time
    rewrites were replayed against the real `hyprlock.conf`, `nyxus-greeter` and
    `hyprland.conf`: one line matched each, zero after, comments untouched, and
    `nyxus-greeter` still parses. The **daily** path cannot be linted end to end
    here — the linters read the committed profile, and the daily divergence only
    exists inside a bake. **[headless]**
1.7 ☐ **Bake both, click-verify.** Bake `NYX_EDITION=alien` (confirm alien is
    unchanged) **and** `NYX_EDITION=daily` (greeter card + teal/amber glow,
    urban default wall, bar/flyout "saucer" glass, launcher, hyprlock). Only a
    UEFI boot proves greetd/firstboot/squashfs/skel bootstrap, the swaync
    handover, and that `systemctl --user --failed` is finally empty. **[VM]**

**Gate before any of Phase 1: SATISFIED (2026-08-01).** The click-audit is done
and written up as `docs/ISO_FULL_AUDIT_2026-07-31.md` §11. Hub, Power, Quick
Settings, greeter, overlays and station switching were all exercised in a live
guest. Three of its findings change Phase 1 and should be read before starting:

- **`swaync` never runs — this blocks the flyout Daily is designed around.**
  `dunst` is started from `hyprland.conf` `exec-once` and takes
  `org.freedesktop.Notifications` first, so `swaync.service` fails the start
  limit on every boot (§11.4). The Win11-Action-Center-meets-Control-Center
  flyout in brief §2 has no daemon behind it today, and Settings already ships a
  notifications page configuring the daemon that isn't there. **Pick one daemon
  before 1.4**, because the choice decides what the flyout is even built on.
  **SETTLED 2026-08-02 — one daemon per edition, and it is not the same one.**
  Alien keeps **dunst** with its appearance unchanged, and `swaync.service` is
  masked (`airootfs/etc/systemd/user/swaync.service -> /dev/null`) so the failed
  unit goes away; masking rather than disabling because the unit is
  `disabled; preset: enabled` and a preset can re-arm anything that is merely
  disabled. Daily uses **swaync** — the daily block deletes that mask and
  rewrites `exec-once = dunst` to `exec-once = swaync` in the staged skel. The
  swaync *package* stays in `packages.x86_64`: masking is per-image state,
  dropping the package would be per-repo and would take Daily's flyout with it.
  Settings' notifications page therefore has a live backend on Daily and is
  still a page over a masked daemon on alien — an alien-side gap, tracked in
  audit §11.4, not a Daily blocker.
- **Station decks leak orphan eww daemons** (§11.3): `eww open` self-daemonises
  during the login race, so surfaces exist that `eww close` cannot reach. Daily
  strips stations, but it inherits the same launch path — fix it at the launcher,
  not the switcher, or Daily ships the same leak in its own shell.
- **Five GTK apps were rendering empty windows** (§11.2, fixed in `9a746a57`).
  Settings, Control, Notepad, Stickies and Store are all shared DNA Daily keeps,
  so this had to be fixed before any Daily shell work sat on top of it.

Still owed from the audit and worth having before 1.7: app launches,
double-click-to-open, the screensaver, and anything MIME (which needs a bake
carrying `f8d07a9b` first). The lock screen's *appearance* cannot be judged in
the VM at all — hyprlock renders nothing under `virtio-vga-gl`, so 1.4's lock
work needs bare metal to verify.

**Later (within the daily edition only):** a Settings/runtime accent toggle via
the existing `nyxus-apply-accent` is a reasonable add — but it lives inside the
daily edition and must never introduce urban-neon code paths into the shared
alien default.
