# NYXUS Start

A Windows-11-style left-side flyout menu for the NYXUS desktop on Hyprland / Arch Linux.

```
┌──────────────────────────────────────────────┐
│  ◉ NYXUS  Joey            [search]  09:42 PM │
├──────────────────────────────────────────────┤
│  PINNED                                       │
│  [grid 4 columns of icons]                    │
├──────────────────────────────────────────────┤
│  RECENTLY USED                       ⌫ Clear │
├──────────────────────────────────────────────┤
│  ALL APPS                  [System]…   ▾     │
├──────────────────────────────────────────────┤
│  GowskiNet  · Phantom · Honeypot · VPN · Net │
├──────────────────────────────────────────────┤
│  [ Joey ]   ⏻  ↻  ⏾  ⎋  🔒                   │
└──────────────────────────────────────────────┘
```

## Features

- **460 × 680 floating window** — anchored bottom-left above the Waybar Start button via `gtk4-layer-shell`.
- **Click-to-toggle** — re-running the launcher kills the running instance, so a single Waybar custom module gives you a click-to-toggle button.
- **Slide-up animation** — opens with a smooth reveal, closes on Escape or focus-out.
- **Search-as-you-type** — instant filtering across every installed `.desktop` app.
- **Pinned apps grid** — 4-per-row, right-click to launch / unpin / open file location, "Edit pins" picker for everything else.
- **Recently used** — last 10 launched apps + recent files (via `Gtk.RecentManager`), with humanized timestamps.
- **All apps** — alphabetical, with NYXUS category chips (System, Security, Internet, Media, Development, Games, Settings, Other).
- **GowskiNet quick status** — Phantom daemon, honeypot attacks, VPN, network reachability — click any tile to open the relevant NYXUS app.
- **Power row** — Lock, Log Out, Suspend, Restart, Shutdown — Restart and Shutdown require confirmation.
- **Same NYXUS aesthetic** — Cairo-rendered DARK MIRROR glass, Inter font, Font Awesome / Nerd Font glyphs, semi-transparent dark plates over the wall.

## Install

```bash
chmod +x install.sh
./install.sh
```

The installer:

1. Installs system packages (`gtk4`, `python-gobject`, `python-cairo`, `gtk4-layer-shell`, `python-psutil`, `jq`) via `pacman`.
2. Lays files into `~/.nyxus/nyxus-start/`.
3. Drops a launcher at `~/.local/bin/nyxus-start` and a `.desktop` entry.
4. Patches `~/.config/waybar/config` with `jq` to:
   - Add `custom/nyxus-start` to the **far left** of the bottom bar.
   - Move `custom/nyxus-panel` to the **far right** of the bottom bar.
5. Appends button styling to `~/.config/waybar/style.css`.
6. Reloads Waybar (`pkill -SIGUSR2 waybar`).

## Usage

```bash
nyxus-start              # toggle open / closed
nyxus-start --no-toggle  # always open (don't kill existing instance)
```

## Config

| File                                            | Purpose                          |
|-------------------------------------------------|----------------------------------|
| `~/.config/nyxus-start/config.json`             | User preferences                 |
| `~/.config/nyxus-start/pins.json`               | Pinned `.desktop` ids            |
| `~/.config/nyxus-start/recent.json`             | App-launch history (rotating 10) |
| `~/.cache/nyxus-start/bg-460x680.png`           | Cached graffiti background       |

## Files

```
nyxus-start/
├── main.py        — GTK4 entry, layer-shell anchor, full UI
├── apps.py        — Gio.AppInfo discovery + NYXUS category mapping
├── recent.py      — Gtk.RecentManager + JSON-backed app recents
├── power.py       — Lock / logout / suspend / restart / shutdown
├── status.py      — GowskiNet quick status probes
└── settings.py    — Config + pins persistence
```

## Waybar additions

If you prefer to wire Waybar by hand instead of letting the installer do it, see `waybar_additions.json` and `waybar_styles.css`.

The two new modules are:

- `custom/nyxus-start` — far left of the bottom bar, opens NYXUS Start.
- `custom/nyxus-panel` — far right of the bottom bar, opens NYXUS Panel (already exists; the installer just makes sure it sits at the very end).

## License

© 2026 Joseph Sierengowski — NYX-J5W-2026-SIERENGOWSKI-LOCKED
