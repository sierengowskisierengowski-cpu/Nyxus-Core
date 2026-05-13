# NYXUS Changelog

## v1.1.0 — Phase 2 (May 2026)

### Phase 2 Build — EWW Desktop + Full App Suite Rebuild

#### System
- Custom Linux base (Arch)
- Hyprland Wayland compositor
- **EWW** top/bottom bars — replaces Waybar (rev r6-eww)
- DARK MIRROR · TRIPLE-BLACK LAYERED visual system (rev r14)
- Hyprlock screen locker / Hypridle idle daemon
- Dunst notifications (replaced Mako)
- SDDM login theme (nyxus QML theme, active on disk-installed systems)
- Auto-dated ISO naming (`nyx-YYYY.MM.DD-x86_64.iso`)
- 116 base packages baked into squashfs

#### Desktop App Suite — 12 apps with desktop entries
All apps built on libadwaita (`Adw.Application` / `Adw.ApplicationWindow`),
FORCE_DARK color scheme, shared `nyxus_chrome` + `nyxus_palette` libraries.

| App | Module | Role |
|-----|--------|------|
| NYXUS System Monitor | `nyxus_sysmon_gtk` | Real-time CPU/memory/disk/network/GPU/process/sensor metrics |
| NYXUS Settings | `nyxus_settings` | System control center — 17 wired sections |
| NYXUS Notepad | `nyxus_notepad` | Markdown editor with Pango-rendered preview |
| NYXUS Stickies | `nyxus_stickies` | Cairo paper-note sticky notes |
| NYXUS Notes | `nyxus_notes` | Lightweight scratchpad |
| NYXUS Control | `nyxus_control` | HW profiles, fan curves, RGB, process tiles |
| NYXUS Terminal | `nyxus_terminal` | VTE-backed terminal |
| NYXUS Launcher | `nyxus_launcher` | Fuzzy app launcher |
| NYXUS Screenshot | `nyxus_screenshot` | Region/full-screen capture via grim+slurp |
| NYXUS App Store | `nyxus_store` | Browse/install/update via pacman+AUR+flatpak |
| NYXUS Power Menu | `nyxus_powermenu` | Lock/suspend/logout/restart/shutdown |
| NYXUS Doctor | `nyxus_doctor` | CLI health audit (intentionally terminal-only) |

#### Additional Python modules staged to /opt/nyxus/
- `nyxus_welcome` — 7-step first-boot welcome wizard
- `nyxus_screensaver` — Cairo fullscreen screensaver
- `nyxus_demon_wake` — lock/wake jumpscare overlay
- `nyxus_security` — security settings helper
- `nyxus_backup` — backup manager
- `nyxus_files` — file manager helper
- `nyxus_clipboard` — clipboard manager
- `nyxus_updater` — system update helper
- `nyxus_drop` — drag-and-drop utility
- `nyxus_crashd` — crash daemon
- `nyxus_usb_watch` — USB monitor (user systemd unit)
- `nyxus_account` — account management
- `nyxus_splash` — boot splash
- `nyxus_preboot` — pre-boot helper
- `nyxus_chrome` — shared GTK chrome library
- `nyxus_palette` — shared DARK MIRROR color tokens
- `nyxus_toast` — toast notification helper
- `nyxus_error` — error dialog helper
- `nyxus_motd` — MOTD generator
- `nyxus_gen_icons` — icon generation utility
- `nyxus-fog` — layer-shell fog overlay
- `nyxus-security-daemon` — background security daemon
- `nyxus-crash-report` — crash report uploader

#### NYXUS Phantom (nyxus-intel)
- Installed to `/opt/nyxus-intel/` from `nyxus-intel.tgz`
- Professional OSINT and investigation workstation
- Tamper manifest sealed at `.manifest.sha256` on every bake

#### Platform / Distribution
- Offline cache staged to `/opt/nyxus-cache/` from `artifacts/api-server/dist/nyxus-scripts/`
- API server (`artifacts/api-server`) serves installers, tarballs, and distribution payloads
- Web surfaces: `nyxus-web` (main), plus demo surfaces (`nyxus-notepad`, `nyxus-stickies`, `nyxus-sysmon`, `nyxus-widgets`)
- `lib/i18n` scaffold added — gettext extraction pipeline for multi-language support

#### Identity
- Tagline: Silent. Dark. Purely Functional.
- Secondary: The Night Has Eyes.
- Mascot: Owl
- Display font: Space Grotesk / Inter
- Mono font: JetBrains Mono Nerd Font

---

## v1.0.0 — 2026

### Initial Release
ISO: nyx-2026.05.02-x86_64.iso

#### System
- Custom Linux base
- Hyprland Wayland compositor
- Full NYXUS theme
- Custom Waybar top and bottom bars
- Hyprlock screen locker

#### App Suite — 14 native GTK4 apps
- NYXUS SYSMON v1.0
- NYXUS Control v1.0
- NYXUS Terminal v1.0
- NYXUS Notepad v1.0
- NYXUS Stickies v1.0
- NYXUS Weather v1.0
- NYXUS Settings v1.0
- NYXUS SAGE v1.0
- NYXUS Shield v1.0
- NYXUS Panel v1.0
- NYXUS Start v1.0
- NYXUS GodsApp v1.0
- NYXUS Phantom v1.0
- NYXUS Creative Studio v1.0

#### Identity
- Tagline: Silent. Dark. Purely Functional.
- Secondary: The Night Has Eyes.
- Mascot: Owl
- Font: JetBrains Mono Nerd Font

Copyright © 2026 Joseph Sierengowski
