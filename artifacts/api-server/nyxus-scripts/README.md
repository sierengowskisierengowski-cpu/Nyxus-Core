# NYXUS

**NYX** is the ISO.  
**NYXUS** is the operating system and all its applications.

---

## What is NYXUS

NYXUS is a hand-crafted Arch Linux distribution built on Hyprland. It ships a complete, opinionated desktop environment — Waybar, Hyprlock, SDDM, Rofi, Mako, Alacritty — alongside a full suite of native GTK4 Python applications designed as a cohesive system.

Every visual element follows the NYXUS design language: black frosted-glass panels, Caveat handwriting font for UI, JetBrains Mono for data and code, neon pink/purple/green/gold palette.

---

## Applications

| App | Description |
|---|---|
| nyxus_sysmon_gtk.py | Live system monitor — CPU, RAM, Network, Disk, Processes |
| nyxus_weather.py | Weather widget with animated sky |
| nyxus_notepad.py | Rich-text notes with Markdown preview |
| nyxus_stickies.py | Minimal sticky notes on a dark canvas |
| nyxus_terminal.py | GTK4 + VTE terminal with graffiti frame |
| nyxus_control.py | Hardware control — fans, thermal, RGB, power profiles |
| nyxus_settings.py | System settings control center |
| nyxus_gen_icons.py | Generates all NYXUS paint-splatter app icons |
| nyxus_motd.py | Terminal message-of-the-day |
| nyxus_splash.py | Boot splash screen |
| nyxus_preboot.py | Pre-boot flicker sequence |

---

## Install

```zsh
curl -fsSL https://nyxus-core.replit.app/api/download/nyxus/nyxus_install.sh | bash
```

---

## Design Tokens

- **Background**: `#080808`
- **Glass panels**: `rgba(6,4,12,0.55)` + `backdrop-filter: blur(14px) saturate(1.6)`
- **UI font**: Caveat
- **Code/data font**: JetBrains Mono
- **Pink accent**: `#ff00ff` / `#c084fc`
- **Green accent**: `#39ff14`
- **Stamp**: `© 2026 NYX-J5W-2026-SIERENGOWSKI-LOCKED`

---

© 2026 JOSEPH SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
