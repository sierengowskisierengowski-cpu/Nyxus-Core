# NYXUS — Changelog

NYX-J5W-2026-SIERENGOWSKI-LOCKED

> ⛔ **READ THIS BEFORE READING ANY ENTRY BELOW (banner added 2026-07-30).**
>
> **Everything under "v2.0" and "v1.x" is HISTORY, not current state.** Those
> entries describe the **DARK MIRROR** era and name things that have since been
> purged or replaced. Taken at face value they will send you to reintroduce
> banned colour or configure software that is no longer in the build. Specifically:
>
> - The accent `#7B5EA7` and background `#0a0e16` in the v2.0 "Theme" section are
>   **not** the palette. Canon is **ALIEN NEON** (`prism`): violet `#7d3dff`,
>   magenta `#ff2dad`, neon green `#39ff14`, orange `#ff8a1e`, on void `#05060a`
>   with text `#eef2fa`. **Banned:** cream `#f4ead5`, gold `#d4b87a`, old violet
>   `#a06bff`. Canon lives in `nyxus_palette.py` + `accent.json`; see
>   [`docs/THEME.md`](docs/THEME.md).
> - **Waybar is gone** (removed 2026-05-11, replaced by EWW). The "4-bar signature
>   theme" credited to Waybar in v2.0 is now four **EWW** bars.
> - **SDDM is not the login screen.** greetd → regreet (under cage) has been the
>   greeter since 2026-07-14; the SDDM QML theme is staged but dormant.
> - **`nyxus-core.replit.app` is retired.** The "Download API" section describes a
>   host that no longer exists.
> - `nyxus_weather.py` is not in the tree — weather is an EWW widget.
>
> **The living record of what has actually changed is [`HANDOFF.md`](HANDOFF.md)**,
> which is append-only and dated. This changelog has not been maintained
> per-release since v2.0 and should not be trusted as one. It is kept as an
> authorship/history artifact, and it is mirrored into `/etc/nyxus/` on the ISO.

---

## Unreleased — 2026-07 (post-v2.0 · summarised)

Not a per-commit log; a signpost so this file is not silently 3 months behind.
Full detail, dated, in [`HANDOFF.md`](HANDOFF.md).

- **Palette locked to ALIEN NEON** (2026-07-23). Eight accent presets deleted
  from `accent.json`; `follow_wallpaper: false`; cream / gold / old-violet
  banned; DARK MIRROR and OBSIDIAN PRISM branding purged from every shipped
  surface (deliberate carve-outs: Bifrost, GodsApp, Meli, Arsenal).
- **Kage-Ryu became the primary kernel** — boot entry #0 on live media and on
  installed systems, with stock `linux` kept only as a rescue entry. The bake
  hard-fails if its prebuilt packages are missing.
- **Greeter moved to greetd → regreet under cage**, with tuigreet as the text
  fallback. SDDM abandoned.
- **Waybar fully replaced by EWW** — four bars, ten station decks, the Hub, the
  saucer clock/music flip, CAVA.
- **Station matrix**: stations 9/10 renamed BLAST/EDGE → **BIFROST/ARSENAL**
  (2026-07-27); named annexes HOME/START/LAB; ten companion stations.
- **Reactive layer actually started** (2026-07-29) — `nyxus-sense` had never been
  launched, so the whole mood layer had been sitting on defaults.
- **Calamares fixed** (2026-07-28) — installed as a `[blackarch]` binary package
  instead of being AUR-built in the chroot. Four ISOs had failed on that premise.
- **Squashfs switched `xz` → `zstd`** (2026-07-30): ~10.8% larger ISO, ~7.6×
  faster cold reads.
- **The `~/.local/bin` class of bug fixed** (2026-07-30) — shipped configs were
  reaching 21 tools through a directory that is empty on the ISO, silently
  killing the living/reflex layer, all UI sound, ~20 keybinds and every dynamic
  hyprlock widget.
- **Documentation audit** (2026-07-30) — `KEYBINDS.md`, `SHIPPING.md`,
  `iso-builder/README.md`, `STATUS.md`, `docs/README.md` and this file corrected
  against the tree.

---

## v2.0 — 2026 (ISO Bake / Final Build) — 🧊 HISTORICAL, see banner above

**Build codename: SIGNATURE EDITION**

### System
- Full naming canonicalized: NYX (ISO) and NYXUS (OS + apps) — all legacy names removed
- Hyprland config updated: `windowrulev2` syntax fixed, `GTK_THEME=NYXUS` set, polkit-gnome replaced with `lxpolkit` for bare-Hyprland compatibility
- GTK theme canonicalized to NYXUS, install path updated to `~/.themes/NYXUS`
- All configs stamped: `© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED`

### Applications
- `nyxus_sysmon_gtk.py` — 8-section live dashboard: CPU, Memory, Network, Disk, Processes, Sensors, Sys
- `nyxus_control.py` — Hardware control center v2: fans, thermal profiles, RGB, power
- `nyxus_terminal.py` — GTK4 + VTE terminal with graffiti frame and spray-can controls
- `nyxus_weather.py` — Weather widget with animated sky and particle system
- `nyxus_notepad.py` — Rich-text notes: Markdown preview, code highlighting, tags, notebooks
- `nyxus_stickies.py` — Minimal sticky notes on dark canvas
- `nyxus_settings.py` — System settings control center
- `nyxus_gen_icons.py` — Paint-splatter neon icon generator via Cairo
- All Python files: `__nyxid__` fingerprint + `_nyx_integrity()` tamper check added

### Lock Screen / Login
- Hyprlock: NYXUS wordmark, JetBrains Mono clock, purple glow password field, copyright stamp
- SDDM: Full QML theme — hex-grid canvas, boot-log animation, NYXUS branding, session selector, reboot/shutdown

### Download API
- `nyxus-core.replit.app/api/download/nyxus/:filename` — all files served
- `wallpaper-rotate.sh` added to allowlist
- Docs (README.md, LICENSE.md, CHANGELOG.md, CREDITS.md) added to allowlist

### Theme
- NYXUS GTK3/4 theme: `#0a0e16` background, `#7B5EA7` accent, JetBrains Mono Nerd Font
- Waybar: 4-bar signature theme with neon gradient accents and background images
- Wlogout: NYXUS-themed logout screen
- Hyprlock: dark purple glow lock screen, no GNOME elements
- SDDM: QML login screen, no GNOME/GDM elements

---

## v1.x — 2025–2026 (Development) — 🧊 HISTORICAL, see banner above

- Initial desktop composition: Hyprland + Waybar + Mako + Alacritty + Rofi
- GTK4 Python application suite developed
- NYXUS design system established: Inter + JetBrains Mono + black glass panels
- Web apps: Portal, Notepad, Stickies, SysMon, Widgets, Mirror, HomeDashboard
- Download API established at nyxus-core.replit.app

---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
