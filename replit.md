# Workspace

## Overview

pnpm workspace monorepo using TypeScript. Each package manages its own dependencies.

## GOLDEN RULE — ALL NYXUS Apps & Widgets

**Every NYXUS app and widget MUST be native Python GTK4. No exceptions.**
- No web/Chromium-based widgets or apps
- No Electron, no WebView
- All apps use `gi.require_version('Gtk', '4.0')` + `from gi.repository import Gtk, Gdk, GLib`
- Cairo (`DrawingArea.set_draw_func`) for all custom drawing and animations
- `GLib.timeout_add()` for timers, `GLib.idle_add()` for thread-safe UI updates
- Styling via `Gtk.CssProvider` with JetBrains Mono + NYXUS neon palette
- Data persisted to `~/.nyxus/<appname>.json`
- App IDs: `io.nyxus.<name>` (stickies, notepad, weather, sysmon)
- GTK deps: `python-gobject gtk4 python-psutil python-cairo` (Arch: pacman)

### Current GTK4 Apps (in `artifacts/api-server/nyxus-scripts/`)
| File | App ID | Launch |
|---|---|---|
| `nyxus_notepad.py`    | `io.nyxus.notepad`  | Hyprland keybind or rofi |
| `nyxus_stickies.py`   | `io.nyxus.stickies` | float, pinned, move 1430 100 |
| `nyxus_weather.py`    | `io.nyxus.weather`  | float, pinned, move 20 100 |
| `nyxus_sysmon_gtk.py` | `io.nyxus.sysmon`   | workspace 6, fullscreen |

### NYXUS Studio (multi-module GTK4 creative suite)
- Tarball: `artifacts/api-server/nyxus-scripts/nyxus-studio.tgz` (~61 KB).
- Installer entry: `nyxus_studio_install.sh` — installed via
  `curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_studio_install.sh | bash`.
- Tarball top-level: `studio/install.sh`, `studio/README.md`, `studio/packages.txt`,
  `studio/requirements.txt`, `studio/studio/{main,document,engine,ui,
  audio_engine,video_engine,three_d_engine}.py`, `studio/studio/modules/m01–m09.py`.
- Modules: paint (m01), vector (m02), 3d (m03), video (m04), animate (m05),
  photo (m06), layout (m07), type (m08), voice (m09).
- Deploy target: `/opt/nyxus-studio`; launcher `/usr/local/bin/nyxus-studio`;
  desktop entry + generated icon under user XDG paths.
- Arch system deps (PACMAN_PKGS): `gtk4 libadwaita python-gobject python-cairo
  python-numpy python-pillow ffmpeg ttf-caveat`.  `libadwaita` is required for
  `Adw.Application*` in `main.py`; `ttf-caveat` is the sketchbook font used by
  the whole UI (CSS + Cairo).  Optional pip extras: sounddevice, soundfile,
  scipy, trimesh.
- Cross-module wiring audit (apr 2026): every `_broadcast` and `_switch_then`
  target invoked by `main.py` resolves to a real method on the target module;
  every `engine/ui/audio_engine/video_engine/three_d_engine/document` reference
  resolves to a real symbol.

### NYXUS Start + Panel flyouts — typography
- All UI text (labels, buttons, titles, sub-headers, status lines, notepad
  body) in both `nyxus-start/main.py` and `nyxus-panel/main.py` uses the
  exact GodsApp font stack: `'Caveat', 'Comic Sans MS', cursive`.
- Glyph-only classes (Font Awesome / Nerd Font icons in the power row,
  weather widget, system widget, news cards) keep their explicit
  `"JetBrains Mono Nerd Font", "Symbols Nerd Font", monospace` family —
  swapping these would break icon rendering.

### Waybar bottom-bar buttons (installed by Start's `install.sh`)
- Four custom modules — three exec-driven (rendered by
  `~/.local/bin/nyxus-waybar-state {start|panel|notifications}`) plus a
  static cog button:
  - `custom/nyxus-start` — far-left, magenta `#ff7af0`, label "Start"
  - `custom/nyxus-settings` — right side, white cog glyph (\uf013),
    on-click → `nyxus-settings` (the unified Settings window from Panel).
  - `custom/nyxus-panel` — right side, lavender `#c4a8ff`, label "The Panel"
  - `custom/nyxus-notifications` — far-right, cyan `#7ae0ff`, label
    "Notifications".
- Idempotent jq patch in `install.sh` rewrites `modules-left` /
  `modules-right` / `modules-center` so re-running the installer never
  duplicates entries; aggressive `startswith("clock")` filter strips ANY
  clock variant (`clock`, `clock#main`, etc.) from the bottom bar — the
  user keeps the date/time module on the TOP bar only.

### NYXUS Start menu — page-switched layout (Apps | Store)
- The middle scrollable area is a `Gtk.Stack` with two named pages,
  switched by toggle buttons in a header strip:
  - `apps` page: search results, Pinned grid, Recently Used, All Apps
    (current behavior, unchanged).
  - `store` page: inline NYXUS App Store catalog. Each row detects
    installation via `shutil.which(binary)` and shows either
    `\uf04b Open` (run binary) or `\uf019 Install` (curl|sudo bash the
    installer in a terminal — foot/alacritty/kitty/xterm fallback chain).
    A footer button opens the standalone `nyxus-store` window.
- `_switch_page` uses an `_in_switch_page` re-entry guard to avoid the
  recursive-toggle infinite loop common to manual radio implementations.

### NYXUS Settings window — sidebar-nav premium layout
- Replaced the old `Gtk.Notebook` with a hero header + sidebar nav
  (`Gtk.ToggleButton` list) + content `Gtk.Stack` (cross-fade transition).
- Pages: Appearance, Profile, Notifications, Panel, News Sources,
  Filters, Browser, Cache, About — each with its own Font Awesome glyph.
- About is pushed to the bottom of the sidebar via a `vexpand` spacer.
- Hero header: cog glyph badge + "NYXUS Settings" title (Caveat) +
  rounded version pill on the right.
- `_select_page` uses an `_in_select_page` re-entry guard (same pattern
  as the Start page-switcher) to handle the cascade of toggle events.
- Standalone launcher (`/usr/local/bin/nyxus-settings`) imports
  `_install_css` from `panel/main.py` so the standalone window inherits
  the same hand-drawn theme it would when launched from inside Panel.

## Stack

- **Monorepo tool**: pnpm workspaces
- **Node.js version**: 24
- **Package manager**: pnpm
- **TypeScript version**: 5.9
- **API framework**: Express 5
- **Database**: PostgreSQL + Drizzle ORM
- **Validation**: Zod (`zod/v4`), `drizzle-zod`
- **API codegen**: Orval (from OpenAPI spec)
- **Build**: esbuild (CJS bundle)

## Key Commands

- `pnpm run typecheck` — full typecheck across all packages
- `pnpm run build` — typecheck + build all packages
- `pnpm --filter @workspace/api-spec run codegen` — regenerate API hooks and Zod schemas from OpenAPI spec
- `pnpm --filter @workspace/db run push` — push DB schema changes (dev only)
- `pnpm --filter @workspace/api-server run dev` — run API server locally

See the `pnpm-workspace` skill for workspace structure, TypeScript setup, and package details.

## NYX ISO build (iso-builder/)

The `iso-builder/` directory contains the archiso profile that bakes
the NYX ISO. **Cannot be built inside Replit** — `mkarchiso` requires
root + loop devices + an Arch Linux host. The user runs this on their
MSI Arch box.

- `iso-builder/build-iso.sh` — one-command wrapper. Pulls the latest
  `nyxus-intel.tgz` from production (or local), seeds the tamper
  manifest at `airootfs/opt/nyxus-intel/.manifest.sha256`, mirrors
  OS-level docs into `airootfs/etc/nyxus/`, runs mkarchiso, renames
  the output to `nyx-2026.05.02-x86_64.iso`.
- `iso-builder/nyx-profile/profiledef.sh` — ISO label `NYX_2026_05`,
  iso_name `nyx`, iso_version `2026.05.02`, BIOS+UEFI bootmodes.
- `iso-builder/nyx-profile/packages.x86_64` — full pacman list:
  hyprland stack, gtk4, python-gobject, calamares, fonts, etc.
- `iso-builder/nyx-profile/airootfs/etc/skel/.config/hypr/hyprland.conf`
  is a **placeholder** — user must drop their daily-driver config in
  before final bake.
- Boot menus (`syslinux/syslinux.cfg`, `efiboot/loader/entries/01-nyx.conf`,
  `grub/grub.cfg`) all branded "NYXUS — The Night Has Eyes".
- `airootfs/etc/os-release` sets `NAME=NYXUS`, `BUILD_ID=nyx-2026.05.02-x86_64`.

## OS-level docs (repo root)

- `LICENSE.md` — NYX & NYXUS Custom License v1.0 (covers both ISO and OS)
- `README.md` — project overview + repo layout
- `CHANGELOG.md` — v1.0.0 release notes for the OS + 14-app suite
- `CREDITS.md` — author + tooling credits
These same docs are mirrored into `iso-builder/nyx-profile/airootfs/etc/nyxus/`
by `build-iso.sh` so they live at `/etc/nyxus/` on the live system.

## Brand naming rule (CRITICAL — do not get this wrong)

- **NYX** = the ISO file. Filename: `nyx-2026.05.02-x86_64.iso`.
- **NYXUS** = the operating system. Everything inside the ISO,
  every app, every doc, every menu, every About dialog says NYXUS.
- The LICENSE is "NYX & NYXUS LICENSE" because it covers both.
- No other brand names — no NyX.x.OS, NyXxOS, GowskiNet, NyX.OS-V1
  (the GitHub URL is the one allowed exception, in LICENSE.md).
- Author is always: **Joseph Sierengowski**.
- Lock code: `NYX-J5W-2026-SIERENGOWSKI-LOCKED`.

## NYXUS Phantom watermarking (nyxus-intel.tgz)

The OSINT tarball at `artifacts/api-server/nyxus-scripts/nyxus-intel.tgz`
ships with comprehensive ownership protection:
- 6-line copyright banner on every Python/Bash/CSS file
- `_fingerprint.py` silent `_check()` called from `main()`
- `_tamper.py` SHA-256s every shipped `.py` (including itself —
  non-bypassable) against `/opt/nyxus-intel/.manifest.sha256`. Mismatch
  prints exact warning text and appends a JSON record to
  `~/.config/nyxus/tamper.log`. App always continues.
- `_legal.py` first-launch disclaimer modal stored in
  `~/.config/nyxus/accepted.json` keyed by app name.
- `_about.py` standard NYXUS About window wired to the topbar info button.
- `install.sh` seeds the tamper manifest at install time and deploys
  per-app LICENSE/README/CHANGELOG/CREDITS to `/opt/nyxus-intel/`.
