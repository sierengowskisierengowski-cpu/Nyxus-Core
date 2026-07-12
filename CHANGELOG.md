# NYXUS — Changelog

NYX-J5W-2026-SIERENGOWSKI-LOCKED

---

## [2026-07-12] - Audit & Polish Pass

### Removed
- `attached_assets/` — pasted-log clutter (dead weight)
- `artifacts/_tmp/` scratch contents (directory kept with `.gitkeep`)
- `artifacts/api-server/nyxus-scripts/eww/eww.yuck.bak2-20260710-*` — EWW backup files
- `.canvas/` — Replit tool state directory

### Added
- `install.sh` — curl-able one-command terminal installer with DARK MIRROR ASCII banner
- `scripts/nyxus-update` — auto-update script with rollback safety, pacman -Syu, notifications
- `scripts/nyxus-update.service` + `scripts/nyxus-update.timer` — systemd user auto-update timer (daily 04:00)
- `scripts/nyxus-sync` — live-sync one-liner: git pull + config deploy + hot-reload EWW/Hyprland

### Fixed
- dunst DARK MIRROR theme: violet frame (#a06bff), cyan critical border (#3ad8ff), obsidian bg (#0c0c12), progress bar cyan
- wlogout DARK MIRROR theme: updated from old prism palette to canonical #a06bff/#3ad8ff
- `.gitignore`: permanently excludes `attached_assets/`, `.canvas/`, `artifacts/_tmp/`, `*.bak`, `*.bak2-*`
- All shell scripts updated to use 24-bit DARK MIRROR ANSI colors (#a06bff violet, #3ad8ff cyan)

---

## v2.0 — 2026 (ISO Bake / Final Build)

**Build codename: SIGNATURE EDITION**

### System
- Full naming canonicalized: NYX (ISO) and NYXUS (OS + apps) — all legacy names removed
- Hyprland config updated: `windowrulev2` syntax fixed, `GTK_THEME=NYXUS` set, polkit-gnome replaced with `lxpolkit` for bare-Hyprland compatibility
- GTK theme canonicalized to NYXUS, install path updated to `~/.themes/NYXUS`
- All configs stamped: `© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED`

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

## v1.x — 2025–2026 (Development)

- Initial desktop composition: Hyprland + Waybar + Mako + Alacritty + Rofi
- GTK4 Python application suite developed
- NYXUS design system established: Inter + JetBrains Mono + black glass panels
- Web apps: Portal, Notepad, Stickies, SysMon, Widgets, Mirror, HomeDashboard
- Download API established at nyxus-core.replit.app

---

© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
