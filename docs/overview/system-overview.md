# System Overview

## Identity

Nyxus-Core is the platform repository for NYXUS and its delivery image.

- **NYXUS**: the operating system/platform, its application ecosystem, and the
  bootable ISO that delivers them. `NYX` is not a product name — see
  `LICENSE.md`.

## What the System Contains

NYXUS combines:
- Arch-based operating environment composition
- A bespoke **Kage-Ryu** kernel (`linux-kage-ryu`, XanMod-based, Alder-Lake-tuned, security-lab config) as the **primary** kernel, with stock `linux` retained only as a rescue boot entry
- Hyprland-centered desktop/runtime configuration with **EWW** — **four** bars (top, bottom, left rail, right rail) plus per-station decks, flyouts and OSDs
- Native application payloads and install/runtime scripts — 13 GTK4 desktop apps with launcher entries (plus a CLI Doctor), additional runtime utilities and overlay components
- Web/API distribution surfaces for platform artifacts — **no public host is currently deployed**
- **ALIEN NEON** visual design system (urban-alien graffiti on triple-black glass) shared across all GUI components

### Shipped chrome (verified 2026-07-30)

- **Icon theme**: NYXUS-Dark (31 custom SVGs, inherits Papirus-Dark)
- **Cursor theme**: NYXUS-Aurora (Hyprcursor + XCursor, 12+ shapes). The name is
  historical and **unrelated** to the deleted `aurora` accent preset
- **Wallpaper pack**: alien art only. The **default is `nyxus-urban-alien.png`**,
  and the same hero resolves for the desktop, the greeter, hyprlock, the
  screensaver and wlogout. All 10 station wallpapers are alien art, with 32
  images under `walls/rotation/`. *(This section previously said the default was
  `nyxus-nebula-01` and that the pack was "auto-mirrored to SDDM lockscreen" —
  both untrue since the 2026-07-23 alien-walls-only pass.)*
- **Bars**: live ticker marquee, saucer centre clock that flips to a now-playing
  face, CAVA visualizer, per-flyout sized panels (network, audio, calendar,
  notifications, quick settings)
- **Modes**: Game Mode and Focus Mode toggles (per-output blur/animation/notification policy); Hacker Mode (black / white / red monochrome transform)
- **Stations**: 10 numbered stations + named annexes (HOME / START / LAB) + 10 companions, with per-station wallpaper via `nyxus-workspace-wallpaperd` *(the name `nyxus-ws-wallpaperd` used here previously has never existed)*
- **Reactive layer**: the `nyxus-sense` bus → Mood Engine, Machine Whispers, Supernova, Graffiti Memory Wall, and a real threat signal (`nyxus-threatd`) rendered on the GHOST pill
- **Onboarding**: first-run welcome tour (sentinel-gated) + the Welcome Transmission note
- **Power**: battery health page, network usage tracker per-app
- **Apps**: NYXUS Store curated catalog, accent picker theming engine, plugin/extension API for the bar
- **System polish**: hot corners, night light (gammastep), dynamic wallpaper rotator (sunrise/sunset)
- **Recovery**: Time Machine snapshot browser, Timeshift backup, crash reporter with upload endpoint
- **Brand-defining**: NYXUS Account, NYXUS Drop, screen recorder, Calamares installer with NYXUS branding

## What This Repository Contains

Nyxus-Core is a monorepo that centralizes:
- ISO build pipeline (`iso-builder/`)
- Deployable services and app surfaces (`artifacts/`)
- Shared TypeScript libraries (`lib/`) — including API spec, client, zod, db, and i18n scaffold
- Build/developer automation scripts (`scripts/`)
- Release and governance documents at the repository root
- Design contract and master checklist in `docs/`

## Delivery Model

1. Workspace packages are validated and built.
2. API/web distribution components are produced from `artifacts/`.
3. ISO staging mirrors required runtime payloads into the archiso profile.
4. NYXUS ISO is baked and released as the canonical distribution image.

The live ISO boots into NYXUS with a full chrome layer — Hyprland, four EWW bars,
Dunst notifications, the **greetd → regreet (under cage)** login screen, the
complete Python GTK4 app suite, and NYXUS Phantom (`nyxus-intel`) — all staged at
build time from `artifacts/api-server/nyxus-scripts/`.

> The SDDM QML theme is still staged but is **dormant**: SDDM was abandoned for
> greetd on 2026-07-14 and is not in `packages.x86_64`. This line said "SDDM login
> theme" until 2026-07-30.

> ⚠ **The ISO does not boot a fully-formed desktop by itself, and
> misunderstanding this is what made the build feel circular for months.** It
> ships (1) a baked `/etc/skel` — the **core** desktop: hyprland.conf + its
> shards, all eww bars, theme, wallpaper, keybinds, fully offline — and (2) a
> first-boot bootstrap (`nyxus-bootstrap`) that layers the heavier web-apps and
> chrome library on afterwards, from the pre-staged cache at
> `/opt/nyxus-cache`. The core desktop must **never** depend on the network to
> come up. Full explanation in [`../../HANDOFF.md`](../../HANDOFF.md) §3.


---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
