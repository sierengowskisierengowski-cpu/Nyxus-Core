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

Windows-shaped shell (Mac users still get familiar chrome: dock-like bar, menus, settings):

| Zone | Daily behavior |
|---|---|
| **Bottom taskbar** | Running apps, pinables, Start on the left, system tray + clock on the right |
| **Start** | App grid / search — one place to launch everything |
| **Notification flyout** | Opens from the tray (calendar / quiet hours / quick toggles) — not a mystery panel |
| **Top ticker (optional)** | Keep a thin, calm status strip — weather / clock / soft status — **not** lab threat chrome. Can evolve into a space-theme accent later |
| **Desktop** | Wallpaper + right-click menu + optional icons. Floating windows. **No tiling by default. No station maze.** |
| **Window controls** | Familiar minimize / maximize / close; snap assist optional later |

**WM policy (Hyprland under the hood):** floating default, single desktop (or one “main” workspace only). Power users can unlock more later; first boot must feel like one calm surface.

**Do not ship on Daily:** multi-station decks, Arsenal/MESH/honeypot surfaces, lab threat UI, anything that screams “security researcher only.”

---

## 3. Feel — chill + eye candy

**Tone:** laid-back, matte, soft depth. Rich enough that people stare at it — not busy enough that they get tired of it.

**Motion / materials (shared techniques with lab eye-candy spec, different skin):**
- Frosted glass panels (compositor layer blur — eww/GTK limits still apply)
- Soft float / lift on focus
- Hover-reveal: chrome stays quiet until the pointer arrives (taskbar chips, tray extras, Start affordances)
- Blur behind overlays (Start, flyout, Hub-like quick settings if kept)
- One coherent animation language — 2–3 intentional motions, not noise

**Density rule:** every surface has one job. Prefer fewer chrome pieces done well over lab’s many specialist panels.

---

## 4. Theme & palette — direction (decide after bake / mockups)

Working direction from the owner (not locked):

| Candidate | Base | Accents | Vibe |
|---|---|---|---|
| **A. Matte night + plum** | Near-black / charcoal matte | Plum / soft purple | Calm, premium, night-desk |
| **B. Matte night + plum + teal** | Same base | Plum primary, teal secondary | Slightly more “alive,” still chill |
| **C. Light charcoal + plum + soft gold** | Dark gray (not pure black) | Plum + restrained yellow/gold highlights | Warmer; use yellow sparingly or it fights purple |

**Rules once locked:**
- One named palette module (like lab’s `nyxus_palette`) — no freehand hex in apps
- Forbidden neon / watermark-adjacent trash stays forbidden
- Space / cosmic art direction for wallpapers & lock (not urban-alien murals)
- Flat/matte chrome; glass only on overlays and hover states

**Open decision for owner after seeing mockups:** A vs B (C only if gold stays a thin highlight).

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
Lock palette (A/B), wallpapers, lock/greeter, frosted Start/flyout, hover-reveal pass.  
Mockups before mass CSS.

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

1. **Palette lock:** A (plum) vs B (plum + teal) vs C ( + soft gold)?
2. **Top ticker:** keep thin / redesign space-theme / remove for v1?
3. **App set:** browser choice (Firefox vs Chromium family), office lite or not?
4. **Name:** “NYXUS Daily” vs a distinct product name (same family, clearer marketing)?
5. **When:** after this bake’s click-audit — confirm Phase 1 before shell MVP?

---

## 11. What this brief is not

- Not permission to implement Daily chrome before lab bake verification
- Not a second copy of the eye-candy or DE studies — it points at them
- Not a promise of true per-widget CSS blur (GTK3/eww ceiling — see eye-candy spec)

---

*Written so the next session can start from intent, not from reconstructing chat.*
