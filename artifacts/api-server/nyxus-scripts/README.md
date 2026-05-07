# NYXUS

**NYX** is the ISO.  
**NYXUS** is the operating system and all its applications.

---

## What is NYXUS

NYXUS is a hand-crafted Arch Linux distribution built on Hyprland. It ships a complete, opinionated desktop environment — Waybar, Hyprlock, SDDM, Rofi, Dunst, Alacritty — alongside a full suite of native GTK4 Python applications designed as a cohesive system.

Every visual element follows the NYXUS design language: black frosted-glass panels, Inter handwriting font for UI, JetBrains Mono for data and code, neon pink/purple/green/gold palette.

---

## Applications

| App | Description |
|---|---|
| nyxus_sysmon_gtk.py | Live system monitor — CPU, RAM, Network, Disk, Processes |
| nyxus_quicksettings.py | Quick settings flyout and toggles |
| nyxus_calendar.py | Calendar window with notes support |
| nyxus_clock.py | Clock window with utility modes |
| nyxus_stickies.py | Minimal sticky notes on a dark canvas |
| nyxus_terminal.py | GTK4 + VTE terminal with graffiti frame |
| nyxus_control.py | Hardware control — fans, thermal, RGB, power profiles |
| nyxus_settings.py | System settings control center |
| nyxus_launcher.py | Launcher / app search UI |
| nyxus_powermenu.py | Power actions menu |
| nyxus_screenshot.py | Screenshot utility shell |
| nyxus_gen_icons.py | Generates all NYXUS paint-splatter app icons |
| nyxus_motd.py | Terminal message-of-the-day |
| nyxus_splash.py | Boot splash screen |
| nyxus_preboot.py | Pre-boot flicker sequence |

Tarball-delivered apps are published as `.tgz` packages (for example `nyxus-weather.tgz` and `nyxus-notepad.tgz`) with matching installer shells (`nyxus_*_install.sh`).

---

## Theme archive

Inactive/alternate theme variants are kept in:

- `theme-archive/boot-splash/`
- `theme-archive/boot-splash-void/`
- `theme-archive/nyxus-ui-theme/`
- `theme-archive/wlogout-theme/`

These are intentionally stored off the active build path for cleaner default builds while preserving assets for future reuse.

---

## Install

```zsh
curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_install.sh | bash
```

---

## Design Tokens

- **Background**: `#0a0e16`
- **Glass panels**: `rgba(6,4,12,0.55)` + `backdrop-filter: blur(14px) saturate(1.6)`
- **UI font**: Inter
- **Code/data font**: JetBrains Mono
- **Pink accent**: `#e8edf5` / `#c8ccd6`
- **Green accent**: `#c8ccd6`
- **Stamp**: `© 2026 NYX-J5W-2026-SIERENGOWSKI-LOCKED`

---

© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
