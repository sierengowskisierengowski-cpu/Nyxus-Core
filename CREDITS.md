# NYXUS — Credits

NYX-J5W-2026-SIERENGOWSKI-LOCKED

---

## Author

**Joseph A. Sierengowski**  
Creator, System Designer, and Platform Architect of NYXUS  
© 2026 — All rights reserved

---

## NYXUS Build

*Component list corrected 2026-07-30 — SDDM was listed as the display manager;
the live greeter has been greetd since 2026-07-14.*

| Component | Role |
|---|---|
| Hyprland | Wayland compositor |
| EWW (`eww-wayland`) | Bars + station decks + dashboard + flyouts + OSDs (4 bars) |
| Hyprlock | Lock screen |
| greetd + regreet + cage | **Display manager / login screen** (tuigreet = text fallback) |
| SDDM | QML theme staged but **dormant** — not in `packages.x86_64`, unused by the live session |
| Dunst | Notification daemon |
| Alacritty · kitty | Terminal emulators |
| Rofi | Run prompt / window switcher |
| swaybg · awww (`swww`) · mpvpaper | Static and live wallpaper |
| wlogout | Logout / power menu |
| CAVA | Audio spectrum (bars, PULSE halo, bass-reactive borders) |
| btop | Terminal system monitor (NYXUS-themed) |
| lxpolkit | Polkit authentication agent |
| hypridle | Idle daemon |
| plymouth | Boot splash ("Cosmic Arrival") |
| GRUB · syslinux | UEFI (themed) and BIOS (plain) boot menus |
| Calamares | Disk installer (binary package from `[blackarch]`) |

## NYXUS Applications (original work by Joseph A. Sierengowski)

- **NYXUS Kage-Ryu** — the custom kernel: XanMod 7.0.12 base, Alder-Lake-tuned,
  lean security-lab config (kprobes/uprobes/BPF/BTF, userns, overlayfs, CRIU,
  KVM-Intel, BBR+FQ, MGLRU, io_uring), plus the `scx_kage` sched-ext scheduler
- NYXUS SysMon — live system dashboard
- NYXUS Terminal — GTK4 + VTE terminal
- NYXUS Notepad — rich-text notes
- NYXUS Stickies — minimal sticky notes
- NYXUS Notes — scratchpad
- NYXUS Control — hardware control center
- NYXUS Settings — system settings
- NYXUS Store — package/app store
- NYXUS Launcher — fuzzy app launcher
- NYXUS Screenshot — region / screen / window capture
- NYXUS Screensaver — urban-alien idle saver
- NYXUS Power Menu — standalone GTK4 power window
- NYXUS Welcome — first-run wizard
- NYXUS Doctor — CLI health audit
- NYXUS Intel (Phantom) — intelligence dashboard
- NYXUS Sage — AI assistant interface
- NYXUS Passwords — credential manager
- NYXUS Studio — creative suite
- NYXUS Hub, station decks, bars and flyouts — the EWW chrome layer

*Retired, and deliberately not listed as shipping (corrected 2026-07-30):*
**NYXUS Home** (the GTK4 app is disabled; the EWW `home-deck` replaced it),
**NYXUS Start** (retired for trapping the desktop; the START station replaced
it), **NYXUS Weather / Calendar / Clock / Notifications / Panel** (these are EWW
widgets and flyouts, not standalone applications — `nyxus_weather.py` does not
exist in the tree).

## Third-Party Open Source

| Project | License |
|---|---|
| Linux kernel | GPL v2 |
| XanMod patchset (Kage-Ryu's base) | GPL v2 |
| Python 3 | PSF License |
| GTK4 / GLib / GObject / libadwaita | LGPL v2.1 |
| Cairo (pycairo) | LGPL v2.1 |
| psutil | BSD 3-Clause |
| Hyprland / hyprlock / hypridle / hyprcursor | BSD 3-Clause |
| EWW (ElKowar's Wacky Widgets) | MIT |
| greetd / regreet / cage | GPL-3.0 / MIT / MIT |
| Calamares | GPL v3 |
| Arch Linux · BlackArch | Various (GPL, MIT, BSD) |

---

## Fonts

The **GRAFFITI TYPE SYSTEM** — the three display faces below are as much a part
of the ALIEN NEON identity as the palette is, and were missing from this list
until 2026-07-30. All ship in `~/.local/share/fonts/nyxus`.

- **Permanent Marker** — spray-paint wordmarks, card headers, station pills  
  Designer: Font Diner · License: SIL Open Font License 1.1

- **Caveat** — handwritten script greetings and flourishes  
  Designer: Impallari Type (Pablo Impallari) · License: SIL Open Font License 1.1

- **Orbitron** — chunky techno numerals (hero clocks, gauges)  
  Designer: Matt McInerney · License: SIL Open Font License 1.1

- **Inter / Inter Display** — UI headings and body labels  
  Designer: Rasmus Andersson · License: SIL Open Font License 1.1

- **JetBrains Mono** (Nerd Font patched) — code, data, stamps, terminal, glyphs  
  Designer: JetBrains · License: SIL Open Font License 1.1

- **DejaVu Sans** — the Tifinagh (U+2D30) companion-station glyphs  
  License: DejaVu Fonts License (Bitstream Vera derivative)

---

© 2026 JOSEPH A. SIERENGOWSKI · NYX-J5W-2026-SIERENGOWSKI-LOCKED
