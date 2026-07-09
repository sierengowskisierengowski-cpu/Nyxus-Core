# NYXUS — STATE.md (Phase 0 Reconciliation Inventory)

Date: 2026-07-09 · Branch: `nyxus-hyprland-055-fixes` · Hyprland 0.55.4 · eww 0.5.0

This is the "what exists today" baseline: local machine vs. GitHub, plus every
duplicate, orphan, and stale reference found. **Identify only — nothing here
has been fixed yet.** Decisions on what stays canonical happen in the next
session (see brief §8, Session 2).

---

## 1. Repo topology & sync state

- **Canonical repo:** `~/GowskiNet-Vault/OS/Nyxus-Core` (symlinked at
  `~/Projects/nyxus-core`), remote
  `github.com/sierengowskisierengowski-cpu/Nyxus-Core`.
- **Active branch:** `nyxus-hyprland-055-fixes` — working tree clean, **in
  sync with `origin/nyxus-hyprland-055-fixes`** (0 ahead / 0 behind as of this
  pass). `main` is stale/divergent (189 ahead, 181 behind) — the hyprland
  branch is the real line of development.
- **Sync mechanism:** live configs live in `~/.config/*` + `~/.local/bin/nyxus-*`;
  `scripts/sync-live-config.sh` rsyncs them into
  `iso-builder/nyx-profile/airootfs/` (skel + `/usr/local/bin`). The repo is a
  *snapshot* of live — live machine is source of truth.
- Worktree branches `nyxus-prism-flair-pulse` and `worktree-home-hud-rebuild`
  are both already merged into HEAD.
- The Cursor workspace repo `~/Projects/bifrost` is a **separate project**
  (Bifrost ops-center screensaver) — not part of the Nyxus build itself.

## 2. Live vs. repo drift (uncommitted since last live-sync)

Live `~/.config` has moved past the last synced snapshot (`7fd20b1`):

| Surface | Drift |
|---|---|
| `eww/eww.yuck` | Live adds **living-theme pulse fields** (`pr/pg/pb/ps/fr/fg/fb/fs`) to the PRISM deflisten + all four bar `:style` strings |
| `eww/scripts/prism-anim.sh` | Live adds living-theme frame mixer (reads `$XDG_RUNTIME_DIR/nyxus-pulse.json`) |
| `hypr/conf.d/nyxus-signature.conf` | Live adds §9b LIVING THEME: `Super+Alt+L` bind + `exec-once nyxus-living on`; removes old commented `nyxus-tintd` autostart |
| `~/.local/bin/nyxus-living` | **Live-only, not in repo at all** |
| `~/.local/bin/nyxus-pulsed` | **Live-only, not in repo at all** |
| `hypr/walls/live/nyxus-void-vortex-live.mp4` | Live-only wallpaper (note: `*.mp4` is excluded by sync script — decide if intentional) |
| `nyxus/settings.json` | Trivial (`last_section` cursor) |

→ **Action next session:** run `scripts/sync-live-config.sh`, verify
`nyxus-living`/`nyxus-pulsed` get picked up (they will — script globs
`~/.local/bin/nyxus-*`), commit as "living theme live-sync".

## 3. Sync-script coverage gaps (things that can silently drift)

`sync-live-config.sh` CONFIG_DIRS does **not** cover these live config dirs:

- `~/.config/nyxus-home/`, `nyxus-panel/`, `nyxus-start/`, `nyxus-stickies/`
  (app state/config for Nyxus apps)
- `~/.config/nyxus-intel/`, `nyxus-sage/` (data dirs — probably correct to
  exclude, but should be an explicit decision)
- `~/.nyxus/` legacy GTK app tree (see §5) is not synced at all
- Live user units `nyxus-eww.service` and `nyxus-usb-watch.service` exist in
  `~/.config/systemd/user/` but are **not in repo skel** (repo has 8 units,
  live has 10 nyxus units)

## 4. Duplicate keybinds — CONFIRMED LIVE (both actions fire on one press)

Verified via `hyprctl binds`:

| Keys | Binding A (hyprland.conf) | Binding B (nyxus-signature.conf) |
|---|---|---|
| `Super+T` | `layoutmsg togglesplit` | `nyxus-tint toggle` |
| `Super+Shift+W` | `hyprshot -m region` | `nyxus-accent-from-wallpaper` |
| `Super+Alt+W` | `nyxus wallpaper_studio` | `nyxus-wall-next` |

These are real conflicts — Hyprland executes *both* dispatchers.

## 5. Legacy `~/.nyxus` GTK layer still wired into current binds

Old-generation Python/GTK apps still bound alongside their replacements:

| Key | Legacy target | Current-gen equivalent |
|---|---|---|
| `Super+Return` | `~/.nyxus/nyxus_terminal.py` (falls back kitty→alacritty) | plain terminal (`Super+Shift+Return` = alacritty) |
| `Super+Space` | `~/.nyxus/nyxus_launcher.py` | rofi (`Super+D` / `Super+R`) |
| `Print` / `Shift+Print` | `~/.nyxus/nyxus_screenshot.py` | `nyxus-shot` (`Super+Print` family) |
| `Super+Shift+H` | `alacritty -e ~/.nyxus/nyxus_doctor.py` | (none — may be intentional keep) |
| eww app_rail SysMon/Notepad/Stickies | fall back to `~/.nyxus/*.py` if new binary missing | `nyxus-sysmon` / `nyxus-notepad` / `nyxus-stickies` |

Commented-out but still present: `nyxus-fog.py` autostart (file **missing**
from `~/.nyxus` — dead reference), `nyxus_stickies.py` / `nyxus-notepad`
autostarts.

## 6. Duplicate / parallel subsystems

- **Terminals:** alacritty AND kitty both installed and both referenced.
  Dock + eww app_rail + safemode use **alacritty**; `Super+Return` prefers
  legacy `nyxus_terminal.py` then **kitty**. No single canonical terminal.
- **Launchers:** rofi (3 themed modes) AND legacy `nyxus_launcher.py`
  (`Super+Space`) AND `nyxus-start` (start-menu — `~/.config/nyxus-start/`).
- **Screenshots:** `nyxus-shot` AND legacy `nyxus_screenshot.py` AND raw
  `hyprshot` bind (`Super+Shift+W`) — three paths.
- **Notifications:** **dunst is the live daemon** (exec-once + eww
  notifications window reads it). `~/.config/swaync/` + a disabled
  `swaync.service` still exist — orphaned unless deliberately kept as spare.
- **Wallpaper engines:** `hyprpaper.conf` + disabled `hyprpaper.service`
  still present, but live path is `nyxus-live-wallpaper auto` (swww/mpvpaper)
  + `nyxus-ws-wallpaperd` per-workspace daemon. hyprpaper looks orphaned.
- **Settings:** `nyxus-settings` (main settings app) + quicksettings eww
  panel (`nyxus-qsd` daemon) — *intentional* per user, but needs the
  canonical-vs-quick-access relationship documented and both themed.
- **Wallpaper accent:** `nyxus-waybar-state` script exists in `~/.local/bin`
  but no waybar is in use (eww build) — likely orphaned.

## 7. Orphaned / unsourced config fragments

- `hypr/conf.d/nyxus-fx.conf` — **NOT sourced** by hyprland.conf. Its binds
  (`Super+G` spray, `Super+Shift+P` wall-fx) are inactive. Note: `Super+G` in
  it would collide with the live `Super+G → deepcore` bind if ever sourced.
  wall-fx/spray shipped in commit `7375c3e` — determine where they're meant
  to be bound.
- `hypr/conf.d/nyxus-safemode.conf` — not sourced; **intentional** (recovery
  profile referencing mako/waybar fallbacks). Keep, but document.
- `~/.config/swaync/` (see §6), `hyprpaper.conf` (see §6).
- VBox log files and `db-old/`, backup dirs in various repos — outside Nyxus
  scope, ignore.

## 8. Escape hatches that break theming (reference-image violations)

Quicksettings sub-panels shell out to foreign-styled tools:

- WiFi → "Advanced (nmtui)" → `alacritty -e nmtui`
- Bluetooth → "Advanced" → `blueman-manager`
- Mixer → "Advanced (pavucontrol)" → `pavucontrol`

These are exactly the "second, separately-styled settings surface" problem
called out in the brief §3.

## 9. Current surface inventory (for the theming pass)

- **eww windows (28 registered):** bar-top/bottom/left/right, dashboard
  (fullscreen control-center — *this is the reference-image surface*,
  `Super+grave`), quicksettings, wifi, bluetooth, mixer, calendar,
  notifications, powermenu, cheatsheet, hotkey-cheatsheet, hotkey-recorder,
  dock, dock-reveal, deepcore, mission, screensaver, splash, snap-toast,
  snap-picker, osd-volume/brightness/mic/capslock, brightness-flyout,
  quicksettings-daemon.
- **Bars:** 4 eww bars (top/bottom/left/right) with PRISM animated rims —
  single `eww.scss` + `_nyxus_accent.scss` (symlink) + `nyxus-palette.css`
  token files already exist. Bottom bar = main action surface.
- **Hyprland conf:** `hyprland.conf` + 10 sourced conf.d fragments + 2
  unsourced (§7). 94 binds in main + ~30 in fragments.
- **Daemons (running):** nyxus-hotkeyd, missiond, qsd, snapd, ws-wallpaperd,
  dunst, hypridle. Enabled-not-running set matches exec-once startup design.
- **Plugins built for 0.55.4:** hyprexpo, hyprfocus, dynamic-cursors
  (`~/.local/lib/nyxus-plugins/`, loaded on demand via `nyxus-plugins`;
  autostart lines commented out).
- **Nyxus apps present:** nyxus-home (HUD, ws name:0), nyxus-panel,
  nyxus-start, nyxus-stickies, nyxus-notepad, nyxus-sysmon, nyxus-store,
  nyxus-settings, nyxus-welcome, nyxus-intel, nyxus-sage, wallpaper-studio.

## 10. Open questions for Session 2 (decisions, not yet made)

1. Canonical terminal: alacritty or kitty? (everything except `Super+Return`
   already points at alacritty)
2. Legacy `~/.nyxus` GTK apps: retire terminal/launcher/screenshot bindings
   in favor of current-gen, or keep any deliberately?
3. Keybind conflicts (§4): which side of each pair wins?
4. swaync + hyprpaper leftovers: delete or archive?
5. Advanced escape hatches (§8): replace with themed in-panel pages, or
   theme-wrap the external tools?
6. Should `nyxus-home/-panel/-start/-stickies` config dirs be added to
   `sync-live-config.sh` CONFIG_DIRS?
7. `nyxus-fx.conf`: source it (rebinding spray off `Super+G`) or fold its
   binds into nyxus-signature.conf?
