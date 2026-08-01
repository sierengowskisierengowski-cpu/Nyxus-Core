# NYXUS DAILY — PRODUCT BRIEF

**Date:** 2026-08-01 · **Status:** product plan only — nothing implemented  
**Owner intent:** keep the current build as the personal / lab experiment; ship a
separate **daily driver** that feels like home for Windows and Mac users, stays
Linux under the hood, and looks chill but badass.

**Related (do not duplicate):**
- DE gaps + edition mechanism → [`DE_COMPLETENESS_AND_EDITIONS_2026-07-31.md`](./DE_COMPLETENESS_AND_EDITIONS_2026-07-31.md)
- Frost / hover / glass feasibility → [`EYE_CANDY_DESIGN_SPEC_2026-07-31.md`](./EYE_CANDY_DESIGN_SPEC_2026-07-31.md)
- Lab build state → [`../HANDOFF.md`](../HANDOFF.md)

---

## 0. One-line product

> A laid-back Linux desktop that feels like Windows or Mac on day one — bottom
> taskbar, Start, notifications where you expect them — with frosted glass,
> hover reveals, and real Settings for everything, so nobody needs a terminal
> unless they want one.

Lab NYXUS stays yours: stations, urban-alien, security tooling, the experiment.  
**Daily** is the little brother people download, live on, and love looking at.

---

## 1. Who it’s for / first-hour promise

**Someone who has never used Linux.** They boot, log in, and within five minutes:

1. Recognize the layout (taskbar bottom, Start left, clock/tray right)
2. Open an app without hunting
3. Right-click the desktop and get a normal menu
4. Double-click a PDF / photo / download and it opens
5. Plug in a USB and it appears
6. Change Wi‑Fi, wallpaper, sound, display, privacy — all in Settings, no terminal

If any of those fail, we failed the product — not the user.

**Emotional target:** chill, confident, not intimidating. “I could live here.”  
Not: cyber-ops lab, workstation maze, “you must learn tiling.”

---

## 2. Layout — muscle memory first

**Cross-OS familiarity is the explicit goal.** Windows users find their
muscle-memory shell; Mac users find the material language and centered launcher
they know. The approved mockups (see §4 → *Reference mockups*) lock the
structure below — a Win11-shaped shell wearing macOS-grade glass.

| Zone | Daily behavior |
|---|---|
| **Bottom taskbar** | Windows 11-style **centered** bar. Launcher orb sits center-left, pinned/running app icons centered next to it, right-side system tray (Wi‑Fi / volume / battery) with clock + date. Frosted glass with corner-bleed (§4). |
| **Start / app launcher** | **Win11-Start-meets-macOS-Launchpad.** Search bar (apps, files, settings) up top, pinned app grid with an **All Apps** affordance, a **Recommended / recent files** list, and a bottom **user + power** row. Opens centered over blurred wallpaper. |
| **Notification + quick-settings flyout** | **Win11 Action Center blended with macOS Control Center.** Right-side flyout: quick-toggle pills (Wi‑Fi, Bluetooth, Airplane, Night Light, Do Not Disturb, Dark Mode), brightness + volume sliders, month calendar, a media / now-playing card, and stacked notification cards with **Clear All**. |
| **Login greeter** | Centered glass card over the shared urban-neon wallpaper: big clock + date, user avatar + name, password field, **Switch User**, and a bottom power row (Shut Down / Restart / Network). Same teal-amber glow as the desktop. |
| **Lock screen (hyprlock)** | Same wallpaper + glass + teal-amber glow: large clock + date centered high, avatar + password field centered, a corner media / now-playing card, tray-style status (Wi‑Fi / battery). |
| **Top ticker (optional)** | Keep a thin, calm status strip — weather / clock / soft status — **not** lab threat chrome. Can evolve into a space-theme accent later |
| **Desktop** | Urban-neon wallpaper + right-click menu + optional icons (Home / Trash). Floating windows. **No tiling by default. No station maze.** |
| **Window controls** | Familiar minimize / maximize / close; snap assist optional later |

**WM policy (Hyprland under the hood):** floating default, single desktop (or one “main” workspace only). Power users can unlock more later; first boot must feel like one calm surface.

**Do not ship on Daily:** multi-station decks, Arsenal/MESH/honeypot surfaces, lab threat UI, anything that screams “security researcher only.”

---

## 3. Feel — chill + eye candy (urban neon)

**Tone:** laid-back but *badass* — a dark cyberpunk city at night you want to
live in, not a threat console. The approved direction is **urban neon**: wet
reflective streets, neon signage, teal + amber glow, "NYXUS" lit in the skyline.
Rich enough that people stare at it — never busy enough that they tire of it.

**Signature material (owner-loved, must-have):** heavily frosted dark glass
panels with a soft teal glow edge and **strong corner-bleed transparency** — the
corners of every panel fade into the wallpaper. Every surface (taskbar,
launcher, flyout, greeter, lock) wears this same glass so the neon city reads
*through* the chrome.

**Motion / materials (shared techniques with lab eye-candy spec, different skin):**
- Frosted dark-glass panels with teal glow edge + corner-bleed (compositor layer blur — eww/GTK limits still apply)
- Soft float / lift on focus
- Hover-reveal: chrome stays quiet until the pointer arrives (taskbar chips, tray extras, Start affordances)
- Blur behind overlays (Start, flyout, Hub-like quick settings if kept)
- One coherent animation language — 2–3 intentional motions, not noise

**Density rule:** every surface has one job. Prefer fewer chrome pieces done well over lab’s many specialist panels.

---

## 4. Theme & palette — LOCKED (approved 2026-08-01)

**Decided.** The owner approved the desktop UI mockups on 2026-08-01; the
candidate table (A/B/C plum matte) is retired. The canonical look is **urban
neon** — a dark cyberpunk city/alley at night — with a **teal + amber** accent
palette and a **frosted dark-glass, corner-bleed** material.

**Canonical palette:**

| Role | Direction |
|---|---|
| Base | Near-black / deep charcoal (wet-night city dark) |
| Primary accent | **Teal / cyan** neon — glow edges, active states, primary highlights, "NYXUS" skyline sign |
| Secondary accent | **Amber / warm orange** neon — signage warmth, secondary highlights, contrast against teal |
| Surface material | Heavily frosted dark glass, soft teal glow edge, **strong corner-bleed** (panel corners fade into the wallpaper) |

**Signature UI material — non-negotiable:** frosted dark-glass panels with a
soft teal glow edge and **strong corner-bleed transparency**. Corner-bleed is an
owner-loved, must-have feature — every panel (taskbar, launcher, flyout,
greeter, lock) fades at the corners into the neon city behind it.

**Wallpapers:** urban-neon "flower/city" art direction (the approved
urban-flower set), default wallpaper carries **"NYXUS" glowing in the skyline**.
This supersedes the earlier "space / cosmic, not urban" note.

**Rules once locked (now in force):**
- One named palette module (like lab’s `nyxus_palette`) — no freehand hex in apps; teal + amber + dark base only
- Neon is now *intentional art direction* (urban-neon signage), not the forbidden watermark-adjacent trash — that ban still applies to cheap/garish neon UI chrome
- Urban-neon city art direction for wallpapers, greeter & lock (this replaces the prior space/cosmic direction for Daily)
- Frosted glass + corner-bleed is the shell material across taskbar, launcher, flyout, greeter and lock — not glass-only-on-hover

### Reference mockups (approved 2026-08-01) — source of truth

These are the **approved** desktop UI mockups defining the Daily look & feel.
They are committed to the repo at **`docs/assets/daily-driver/`**. They were
generated into the Cursor project assets directory, which is not cloned, not
backed up and does not survive a lost session — so the repo copy is the source
of truth and the one to reference.

| File | Defines |
|---|---|
| `set-desktop.png` | Desktop wallpaper + centered bottom taskbar (launcher orb, pinned icons, right tray + clock/date), "NYXUS" skyline sign |
| `set-notifications.png` | Notification + quick-settings flyout (toggle pills, brightness/volume sliders, calendar, media card, notification cards) |
| `set-launcher.png` | Start menu / app launcher (search, pinned grid, recommended/recent files, user + power row) |
| `set-login.png` | Login greeter (clock, avatar, password, Switch User, power row) |
| `set-lockscreen.png` | Hyprlock lock screen (clock, avatar + password, media card, status) |

The approved **wallpapers are not reference art — they ship.** Each is staged
into the three trees the bake and `nyxus-wall-cycle` actually read
(`artifacts/api-server/nyxus-scripts/`, skel `.config/hypr/walls/`, and
`/usr/share/backgrounds/nyxus/`) and registered in that directory's
`manifest.tsv`, which is what makes them selectable rather than merely present:

| Wallpaper | Ships as |
|---|---|
| Urban flower · wall | `nyxus-urban-flower-wall.png` |
| Urban flower · concrete | `nyxus-urban-flower-concrete.png` |
| Urban astronaut · moonwalk | `nyxus-urban-astronaut-moonwalk.png` |
| NYXUS cosmic hero | `nyxus-hero-cosmic.png` |

They are *added*, not substituted: no existing wallpaper was replaced and the
alien build's `nyxus-urban-alien` default is untouched, per the additive-edition
decision.

Future agents: treat these images as the canonical visual spec for Daily shell
work; match them before writing mass CSS.

---

## 5. What Daily keeps / strips / adds

### Keep (shared DNA)
- Hyprland + greetd + Settings architecture
- File manager, terminal (available, not required), browser, media basics
- Lock / idle / polkit / PipeWire / NetworkManager / Bluetooth
- Privacy-respecting defaults (see §6)
- Eye-candy *machinery* (blur layers, hover-reveal patterns) — reskinned

### Strip (lab-only)
- Station maze & lab decks
- Honeypots, Arsenal, Bifrost, Meli, heavy BlackArch / recon / exploit stacks
- Threat-reactive / ops chrome that intimidates normals
- Anything that exists only for Joseph’s experiment path

### Add (Daily product)
- Bottom taskbar + Start + notification flyout as **primary** chrome
- Floating / single-desktop session profile
- Wave 1–2 DE completeness (desktop layer, MIME, clipboard, USB mount, keyring, portals) — see DE study
- Full Settings coverage for daily life (display, sound, network, bluetooth, users, privacy, updates, appearance) — **no terminal required**
- Sensible default apps (browser, files, images, PDF, notes, calculator, screenshot)

### “Handles any load”
- Solid compositor defaults, earlyoom / sane memory policy from lab where it helps
- Updates path that doesn’t require CLI
- Optional “power / pro” toggle later — not on first boot

---

## 6. Safe & private — without the lab threat model

Daily is not a honeypot OS. It should still feel trustworthy:

- Firewall on by default (simple UI in Settings)
- Sensible privacy toggles (telemetry off, mic/cam indicators if feasible)
- Encrypted install path via Calamares when installing
- No surprise network services
- Updates and permissions explained in plain language

Lab keeps the deep security theater. Daily keeps **quiet hygiene**.

---

## 7. Architecture — how we build it without repeating history

**Do not fork into a second repo of copied configs.** That is how this project loses weeks.

| Approach | Verdict |
|---|---|
| Separate full repo of duplicated skel/ISO | Reject — drift guaranteed |
| `packages.x86_64.lean` duplicate list | Reject — already proven stale (DE study §3.1) |
| **`NYX_EDITION=lab\|daily` in this repo, subtractive + Daily chrome shards** | **Recommend** |
| Optional later: thin sibling repo that only holds Daily branding if marketing needs a separate GitHub face — still consumes shared packages from here | Optional marketing wrapper only |

Daily chrome lives in clearly named paths (e.g. `editions/daily/…` or `nyxus-daily-*` shards) so lab and daily never overwrite each other’s bars by accident.

Build stamp must record edition: `/etc/nyxus-build` includes `edition=daily|lab`.

---

## 8. Phased roadmap (after the current lab bake + click-audit)

### Phase 0 — Lab solid (now)
Bake tip, flash, click-audit Hub / Power / Settings / apps. Fix blockers.  
Daily work does **not** start until lab sticks match tip.

### Phase 1 — “Feels like a real OS” wiring (shared)
DE study Wave 1–2: desktop layer, MIME, clipboard, USB, keyring, portals, viewers.  
Benefits both editions.

### Phase 2 — Daily shell MVP
Bottom taskbar, Start, tray + notification flyout, floating single-desktop profile.  
Ship as `NYX_EDITION=daily` bake. Lab unchanged.

### Phase 3 — Skin & space theme
Apply the locked urban-neon teal+amber palette (§4), urban-flower wallpapers, lock/greeter, frosted corner-bleed Start/flyout, hover-reveal pass.  
Palette + mockups are approved (§4 *Reference mockups*) — match them before mass CSS.

### Phase 4 — Polish & “love to look at”
Motion coherence, Settings completeness pass, default-app polish, install UX,  
optional top ticker redesign (chill / space), performance pass under load.

### Phase 5 — Public face (optional)
Landing page, download of Daily ISO, clear “Lab vs Daily” story. Lab stays personal.

---

## 9. Success criteria (Daily v1)

Someone from Windows or Mac can:

- [ ] Use the machine for a full day without opening a terminal
- [ ] Find Start, notifications, Wi‑Fi, volume, and Settings without a guide
- [ ] Say the desktop looks intentional and calm (not “another Linux rice”)
- [ ] Open common files and removable media without friction
- [ ] Prefer staying on it — aesthetics + comfort, not novelty alone

---

## 10. Owner decisions still open

1. ~~**Palette lock:** A (plum) vs B (plum + teal) vs C ( + soft gold)?~~ **DECIDED 2026-08-01** — none of the above. Locked to **urban-neon teal + amber** on a dark base with frosted-glass corner-bleed material (see §4).
2. ~~**Wallpaper / art direction:** space/cosmic vs other?~~ **DECIDED 2026-08-01** — **urban-neon city** art direction (urban-flower set), default carries "NYXUS" in the skyline (see §4). Supersedes the old space/cosmic note.
3. **Top ticker:** keep thin / redesign space-theme / remove for v1?
4. **App set:** browser choice (Firefox vs Chromium family), office lite or not?
5. **Name:** “NYXUS Daily” vs a distinct product name (same family, clearer marketing)?
6. **When:** after this bake’s click-audit — confirm Phase 1 before shell MVP?

---

## 11. What this brief is not

- Not permission to implement Daily chrome before lab bake verification
- Not a second copy of the eye-candy or DE studies — it points at them
- Not a promise of true per-widget CSS blur (GTK3/eww ceiling — see eye-candy spec)

---

*Written so the next session can start from intent, not from reconstructing chat.*
