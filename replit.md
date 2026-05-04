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
| `nyxus_settings.py`   | `io.nyxus.settings` | rofi / desktop entry |
| `nyxus_control.py`    | `io.nyxus.control`  | waybar control icon |
| `nyxus_terminal.py`   | `io.nyxus.terminal` | $mod+Return |
| `nyxus_quicksettings.py` | `io.nyxus.quicksettings` | click waybar clock |
| `nyxus_launcher.py`   | `io.nyxus.launcher` | $mod+Space |
| `nyxus_powermenu.py`  | `io.nyxus.powermenu`| $mod+Escape |
| `nyxus_screenshot.py` | `io.nyxus.screenshot` | Print / Shift+Print |
| `nyxus_doctor.py`     | `io.nyxus.doctor`   | $mod+Shift+H |

### Phase 2 — Visual Consistency Pass (May 2026)
System-wide audit + tone-down across all 12 GTK apps:
- **Border-radius canon**: 4px / 6px (pills 999px intentional only)
- **Glow alpha cap**: 0.55 max in box-shadow / text-shadow (was 0.95)
- **Pink dominance**: ≤6% per file; pink is accent only, never dominant
- **Graffiti chrome**: 12/12 apps (`install_chrome` from `nyxus_chrome.py`)
- **Caveat font**: 12/12 apps
- **Letter-scrambling titles** (`rainbow_markup`): 9/12 apps (3 omissions
  intentional — tiny dropdowns + custom Cairo titles)

### Phase 2.2 — GodsApp visual language, system-wide (May 2026)
User declared **GodsApp the gold-standard reference** and demanded every
other NYXUS app (start, panel, notifications, settings, all 12 — terminal
excluded) match its exact look: transparent window so the graffiti mural
shows through, translucent dark inner panels, semi-opaque entries/textviews,
rainbow-cycling neon button outlines with handwritten Caveat labels.
- Rewrote `CHROME_CSS` in `nyxus_chrome.py` to promote godsapp's
  visual rules globally:
  - `* { font-family: 'Caveat' }` universal rule (mirrors godsapp/ui.py),
    with `.nyx-mono`/`.nyx-code` opt-out for code/log areas.
  - Window 100% transparent; outer shell boxes at 0.42 alpha; inner
    panels (frame/scrolledwindow/listbox/.card) at 0.55 with 1px
    white-6% border for godsapp's "dark glass plate" look.
  - Buttons: transparent fill, 1.5px neon-pink border by default;
    `nth-child(2n/3n/4n)` cycles through blue/gold/green so adjacent
    buttons in a row each take a different neon hue (matches the
    pink/cyan/gold/magenta button row in the godsapp screenshot).
    Hover adds a matching-color box-shadow glow.
  - Headerbar / titlebar at 0.65 alpha with 1px pink underline so Adw
    apps' top bars also show the graffiti through them.
  - Adw semantic classes (`.suggested-action` -> green outline,
    `.destructive-action` -> red, `.flat` -> borderless w/ hover glow).
  - `entry`/`textview`/`spinbutton` at 0.85 alpha with neon-pink focus
    ring; `dropdown`, `check`, `radio`, `switch`, `scale` all picked up
    matching neon styling. `tooltip` gets the same dark-pink-edged plate.
- Loader hardened: CHROME_CSS is now a Python `str` (so non-ASCII
  characters in comments would be safe) but block was sanitized to
  pure ASCII anyway. `_install_global_css()` encodes to bytes once,
  passes to `Gtk.CssProvider.load_from_data`, falls back to the
  string-arg form on `TypeError` for older GTK4 builds.
- Loaded at `Gtk.STYLE_PROVIDER_PRIORITY_USER` so it overrides every
  app's own APPLICATION-priority CSS without per-app code changes.
- Sync verified: `nyxus-scripts/nyxus_chrome.py` -> `dist/` SHA match,
  `curl localhost:80/api/download/nyxus/nyxus_chrome.py` returns the
  same SHA, key new selectors (`button:nth-child`, `headerbar`,
  `switch:checked`, `tooltip`, `.nyx-mono`) all present in served file.
- Terminal intentionally excluded — it doesn't ship the bootstrap so
  it stays a clean readable monospace surface. All 12 main apps + the
  start/panel/notifications/settings shells inherit the new look on
  next reinstall.

### Phase 2.1 — Adw + Store fixes (May 2026)
Two install-time gaps caught after the first user reinstall:
- **`install_chrome` is now Adw-aware.** `Adw.ApplicationWindow` uses
  `set_content/get_content` (not `set_child/get_child`), so the original
  Gtk-only `install_chrome` silently failed on the 4 Adw apps —
  **godsapp, sage, shield, studio**. Added `_is_adw_app_window()` and
  branched the get/set accessor pair. The auto-injected bootstrap
  in every entry now also monkey-patches `Adw.ApplicationWindow.present`
  in addition to `Gtk.ApplicationWindow.present`.
- **`io.nyxus.store.desktop` no longer self-deletes.** It was listed in
  `OLD_DESKTOPS=( … )` in `nyxus_install.sh`, so the cleanup loop wiped
  it on every install — which is why the App Store launcher disappeared
  from Rofi / the Start menu even though `nyxus-start.tgz` correctly
  creates it. Removed from the legacy list and documented inline.

### Phase 2 — Hyprland integration (May 2026)
- `exec-once = dunst` (was `mako` — conflicted with shipped `dunstrc`)
- `$mod+Space` → launcher (was `centerwindow`, moved to `$mod+Shift+C`)
- `$mod+Escape` → powermenu
- `Print` / `Shift+Print` → screenshot (region / full)
- `$mod+Shift+H` → doctor health audit
- Waybar clock `on-click` → toggle quicksettings panel

### Phase 2 — Unified chrome across every GTK app (May 2026)
A full audit found **13 distinct GTK entries** across the 12 tarballs
(nyxus-start ships three: start, notifications, store). All 12 GUI
entries now carry an auto-injected chrome bootstrap; one entry is
intentionally excluded.

- **Patched (12)**: home, weather, notepad, passwords, intel, start,
  notifications, store, sage, studio, shield, godsapp.
- **Excluded — `nyxus-panel`**: uses `Gtk4LayerShell.init_for_window`
  which is incompatible with re-parenting the window content into a
  `Gtk.Overlay`. Wrapping it would break LayerShell anchoring.
- **Excluded — `nyxus-phantom`**: silent background daemon, no GTK
  windows at all.

Bootstrap design (post code-review):

- Inserted **above** `if __name__ == "__main__":` so the monkey-patch
  is in place before `app.run()` blocks. (An earlier appended-at-EOF
  version never executed — caught by the architect review.)
- Monkey-patches `Gtk.ApplicationWindow.present` so the canonical
  `install_chrome()` from `nyxus_chrome.py` runs exactly once per
  top-level window. Idempotent on two layers — class-level
  `_nyx_chrome_hooked` guard + `install_chrome`'s own
  `nyxus-chrome-installed` window-data flag.
- **No synchronous network fetch** (also from review). The bootstrap
  prepends `~/.nyxus` to `sys.path`, imports `nyxus_chrome` locally,
  and silently no-ops if the module is missing. `nyxus_install.sh`
  now ships `nyxus_chrome.py` (and `nyxus_quicksettings.py`) to
  `$SCRIPTS_DIR` (`~/.nyxus`) so the import always succeeds offline.
- Each entry is keyed by its own `_NYX_PAGE_KEY` (`_home`, `_intel`,
  `_store`, etc.) so the right graffiti mural is selected per-app;
  unknown keys fall back to `_home` inside `GraffitiBackground`.
- Per-tarball `install.sh` scripts and pre-existing per-app
  `graffiti.py`/`style.py` files are left intact — the chrome rides on
  top via Gtk.Overlay so legacy paint code keeps rendering underneath
  if it was already styled.

### Phase 2 — SDDM login theme wired in (May 2026)
- `nyxus_install.sh` now installs the NYXUS SDDM theme: ensures `sddm` +
  `qt5-quickcontrols2` + `qt5-graphicaleffects` packages, downloads
  `nyxus-sddm-theme.tar.gz`, runs the bundled `install.sh` (writes
  `/etc/sddm.conf.d/nyxus.conf`), then disables `gdm.service` if active
  and enables `sddm.service`. Effective on next reboot.
- The tarball's internal `install.sh` had a stale wallpaper-fallback URL
  pointing at `jsierengowski-workspace.replit.app` — repacked with the
  current `nyxus-core.replit.app` URL.
- `iso-builder/nyx-profile/packages.x86_64` adds `sddm`,
  `qt5-quickcontrols2`, `qt5-graphicaleffects`.
- `iso-builder/build-iso.sh` `stage_nyxus_chrome` now extracts the
  SDDM tarball into `airootfs/usr/share/sddm/themes/nyxus/` and writes
  `airootfs/etc/sddm.conf.d/nyxus.conf` so the theme is dormant on the
  live ISO (which uses Hyprland autologin) but ready for the disk
  installer (Job 2) to enable on a real install.

### Phase 2 — Mako → Dunst migration (May 2026)
NYXUS standardized on **dunst** as the sole notification daemon. Removed
mako install + autostart from `nyxus_install.sh` and migrated active code:
- `nyxus_install.sh`: pacman install, `MAKO_DIR`, `systemctl --user enable mako`,
  `dl mako-config`, and `makoctl reload` block all removed/replaced with dunst
  equivalents (`pkill -SIGUSR2 dunst` for live reload).
- `nyxus_quicksettings.py`: Focus Assist now uses `dunstctl set-paused`
  (2-state toggle Off ↔ DND, was 3-state mako modes); notif history reads
  `dunstctl history`; `notif_clear` uses `dunstctl close-all`; capability
  probe checks `has("dunstctl")`.
- `nyxus-ui-theme/install.sh`: dropped mako step (now `[1/3]` is a noop note);
  steps relabeled.
- `download.ts`: `mako-config` route entry removed (now 404s).
- Orphan files deleted: `nyxus-scripts/mako-config`,
  `nyxus-scripts/nyxus-ui-theme/mako/config`, 4× stale `waybar-config.json.bak*`.
- **Intentionally retained**: `nyxus_settings.py` notification panel keeps
  multi-daemon support (mako/dunst/swaync) — that's a defensive Settings UI
  for non-NYXUS Arch boxes that may have a different daemon installed.

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
- `iso-builder/build-iso.sh` `stage_nyxus_chrome` step (lines 84-186) — copies
  the full Phase 2 chrome layer (configs, 19 GTK apps, 16 wallpapers,
  3 helper scripts, 12 launcher wrappers + .desktop entries) from
  `artifacts/api-server/nyxus-scripts/` (single source of truth) into
  airootfs at bake time. Idempotent. Adds skel symlink `~/.nyxus →
  /opt/nyxus` so the same hyprland.conf works on both the live ISO and
  the download-portal install flow.
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
