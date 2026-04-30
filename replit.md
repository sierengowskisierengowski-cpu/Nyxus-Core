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
