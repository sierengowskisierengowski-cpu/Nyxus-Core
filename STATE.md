# NYXUS — STATE.md (Phase 0 Reconciliation Inventory)

Date: 2026-07-10 · Branch: `nyxus-hyprland-055-fixes` · Hyprland 0.55.4 · eww 0.5.0

This is the "what exists today" baseline: local machine vs. GitHub, plus every
duplicate, orphan, and stale reference found. **Update 2026-07-10 (Session 3):
theming + wiring pass largely complete; GitHub matches machine** (HEAD
`43a3b33`, 0 ahead / 0 behind origin). See §11 for done / in-progress / plan.
§5b lists intentional keeps that must never be re-flagged as legacy/orphans.

---

## 1. Repo topology & sync state

- **Canonical repo:** `~/GowskiNet-Vault/OS/Nyxus-Core` (symlinked at
  `~/Projects/nyxus-core`), remote
  `github.com/sierengowskisierengowski-cpu/Nyxus-Core`.
- **Active branch:** `nyxus-hyprland-055-fixes` — working tree clean, **in
  sync with `origin/nyxus-hyprland-055-fixes`** (0 ahead / 0 behind, verified
  2026-07-10). `main` is stale/divergent — the hyprland branch is the real line
  of development.
- **Sync mechanism:** live configs live in `~/.config/*` + `~/.local/bin/nyxus-*`;
  `scripts/sync-live-config.sh` rsyncs them into
  `iso-builder/nyx-profile/airootfs/` (skel + `/usr/local/bin`). The repo is a
  *snapshot* of live — live machine is source of truth.
- Worktree branches `nyxus-prism-flair-pulse` and `worktree-home-hud-rebuild`
  are both already merged into HEAD.
- The Cursor workspace repo `~/Projects/bifrost` is a **separate project**
  (Bifrost ops-center screensaver) — not part of the Nyxus build itself.

## 2. Live vs. repo drift

**Resolved** for the major surfaces (living theme, eww, hypr, settings, apps)
via commits `b8b3d03` → `43a3b33`. Remaining benign drift only:

| Surface | Status |
|---|---|
| `~/.config/eww/*.bak*` | Local editor backups — not synced (correct) |
| `~/.nyxus/__pycache__` | Bytecode only — not synced (correct) |
| `hypr/walls/live/*.mp4` | Excluded by sync script (`--exclude '*.mp4'`) — intentional |
| `nyxus/settings.json` | Per-user cursor (`last_section`) — may differ per machine |

## 3. Sync-script coverage gaps (things that can silently drift)

`sync-live-config.sh` CONFIG_DIRS does **not** cover these live config dirs:

- `~/.config/nyxus-home/`, `nyxus-panel/`, `nyxus-start/`, `nyxus-stickies/`
  (app state/config for Nyxus apps)
- `~/.config/nyxus-intel/`, `nyxus-sage/` (data dirs — probably correct to
  exclude, but should be an explicit decision)
- `~/.nyxus/` GTK app tree — **now synced** (added in commit `35af614`); app
  state dirs (`nyxus-home/`, `nyxus-panel/`, etc.) still not in CONFIG_DIRS
- Live user units `nyxus-eww.service` and `nyxus-usb-watch.service` exist in
  `~/.config/systemd/user/` but are **not in repo skel** (repo has 8 units,
  live has 10 nyxus units)

## 4. Duplicate keybinds — RESOLVED (2026-07-09 de-dup pass)

All three double-fire conflicts fixed; `hyprctl binds -j` piped through a
duplicate checker confirms **0 duplicate (modmask,key) pairs** across all
118 live binds.

| Keys | Winner (kept) | Loser (moved/removed) |
|---|---|---|
| `Super+T` | `nyxus-tint toggle` (signature) | `layoutmsg togglesplit` → **moved to `Super+J`** |
| `Super+Shift+W` | `nyxus-accent-from-wallpaper` (signature) | `hyprshot -m region` → **removed** (screenshots consolidated, §6) |
| `Super+Alt+W` | `nyxus-wall-next` (signature) | `nyxus wallpaper_studio` → **moved to `Super+Alt+S`** |

## 5. Legacy-vs-current-gen bindings — RESOLVED (2026-07-09)

Canonical picks locked in and implemented:

| Key | Canonical (live) | What changed |
|---|---|---|
| `Super+Return` | `alacritty` (canonical terminal) | was `nyxus_terminal.py` → kitty fallback chain |
| `Super+Shift+Return` | `[float] alacritty` | floating variant — distinct, not a duplicate |
| `Super+Space` | `~/.nyxus/nyxus_launcher.py` — **CANONICAL launcher** | rofi drun duplicates removed: `Super+D`, `Super+Shift+D`; `Super+R` re-added as a muscle-memory alias of Super+Space (launcher has `!cmd` prefix for run mode) |
| `Super+Tab` | rofi window switcher | KEPT — distinct function, not a duplicate |
| `Print` family | `~/.nyxus/nyxus_screenshot.py` — **CANONICAL screenshots** | see §6 |
| `Super+Shift+H` | `alacritty -e ~/.nyxus/nyxus_doctor.py` | no duplicate — intentional keep |
| eww app_rail SysMon/Notepad/Stickies | fall back to `~/.nyxus/*.py` if new binary missing | untouched (theming pass owns `~/.nyxus`) |

Dead comment references cleaned: `nyxus-fog.py` autostart comment removed
from `nyxus-hyprland-fog.conf`; commented legacy autostarts (nyxus-weather,
`nyxus_stickies.py`, nyxus-notepad) removed from hyprland.conf.

### 5b. INTENTIONAL KEEPS — do not re-flag as legacy/orphans

- `~/.nyxus/nyxus_launcher.py` — `Super+Space`, the canonical launcher.
- `~/.nyxus/nyxus_screenshot.py` — canonical screenshot app (grim+slurp GTK:
  region/window/fullscreen/picker, `--annotate`, `--ocr`, `--delay`). Bound
  on `Print`, `Shift+Print`, and the whole `Super+Print` family.
- `~/.nyxus/nyxus_doctor.py` — `Super+Shift+H`, no duplicate exists.
- `conf.d/nyxus-safemode.conf` — recovery profile, **unsourced by design**
  (header now says so explicitly).
- `Super+Tab` rofi window switcher — distinct function; rofi configs/themes
  stay (used by the window switcher and various scripts).
- grimblast binary stays installed (harmless; only the `nyxus-shot` wrapper
  was removed).

## 6. Duplicate / parallel subsystems — RESOLVED (2026-07-09)

- **Terminals:** **alacritty is canonical.** `Super+Return` → alacritty,
  `Super+Shift+Return` → floating alacritty. kitty remains installed but is
  no longer bound anywhere.
- **Launchers:** **`nyxus_launcher.py` is canonical** (`Super+Space`). The
  rofi drun binds are gone; rofi survives only as the `Super+Tab` window
  switcher. `nyxus-start` (start-menu) is a separate surface, untouched.
- **Screenshots:** **`nyxus_screenshot.py` is canonical** — all five binds
  point at it: `Print` (region), `Shift+Print` (picker), `Super+Print`
  (region), `Super+Shift+Print` (fullscreen), `Super+Ctrl+Print` (window).
  The `nyxus-shot` grimblast wrapper is **deleted** (live + repo rootfs);
  the `hyprshot` bind is removed.
- **Notifications:** dunst only. `~/.config/swaync/` **deleted** (live +
  skel), removed from sync-script CONFIG_DIRS; `swaync.service` verified
  disabled (vendor unit, no user unit present).
- **Wallpaper engines:** swww/mpvpaper stack only. `hyprpaper.conf`
  **deleted**; `hyprpaper.service` verified disabled (vendor unit).
- **Settings:** `nyxus-settings` → canonical 14k-line control center
  (`~/.nyxus/nyxus_settings.py`, fixed in `35af614`); quicksettings eww panel
  (`nyxus-qsd`) = deliberate quick-access layer. Both themed to HUD language.
- **Wallpaper accent:** `nyxus-waybar-state` **deleted** (live + repo
  rootfs) — no waybar in this build, zero references.

## 7. Orphaned / unsourced config fragments — RESOLVED (2026-07-09)

- `hypr/conf.d/nyxus-fx.conf` — **deleted**; its binds folded into
  nyxus-signature.conf (§9c): spray moved `Super+G` → **`Super+Z`** (G
  collides with the live deepcore bind), wall-fx toggle kept on
  `Super+Shift+P` (verified free — beat vacated it for `Super+Alt+B`).
  Both binds are now live for the first time.
- `hypr/conf.d/nyxus-safemode.conf` — kept; header now explicitly marks it
  as intentionally unsourced (recovery profile). See §5b.
- `~/.config/swaync/`, `hyprpaper.conf` — deleted (see §6).
- VBox log files and `db-old/`, backup dirs in various repos — outside Nyxus
  scope, ignore.

## 8. Escape hatches — RESOLVED (2026-07-09, commit `913a3ee`)

WiFi / Bluetooth / Mixer flyouts now use **themed in-panel pages** (saved
networks, trust/pair controls, input-device mixer). Deeper cases fall back to
`nyxus-settings`, not nmtui/blueman/pavucontrol.

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

## 10. Session 2 decisions — status

1. ~~Canonical terminal~~ → **DECIDED + IMPLEMENTED: alacritty** (§5/§6).
2. ~~Legacy `~/.nyxus` bindings~~ → **DECIDED + IMPLEMENTED:** terminal
   retired in favor of alacritty; launcher/screenshot/doctor are canonical
   keeps (§5b).
3. ~~Keybind conflicts~~ → **DECIDED + IMPLEMENTED:** signature layer wins
   all three; losers moved to `Super+J` / `Super+Alt+S` or removed (§4).
4. ~~swaync + hyprpaper~~ → **DECIDED + IMPLEMENTED: deleted** (§6).
5. ~~Advanced escape hatches~~ → **IMPLEMENTED** (§8).
6. Should `nyxus-home/-panel/-start/-stickies` **config state dirs** be added
   to `sync-live-config.sh` CONFIG_DIRS? — **still open** (app *code* syncs;
   per-user pins/recent JSON does not).
7. ~~`nyxus-fx.conf`~~ → **DECIDED + IMPLEMENTED** (§7).

---

## 11. Session 3 — build status (2026-07-10)

### Theme target (locked)

Fusion of three ingredients: **(1)** HOME HUD card language (`rgba(7,5,14)`
ink, per-card neon hues, dot-matrix numerals, hairline borders), **(2)** prism
living-theme animation (pulse/tint/beat), **(3)** graffiti wallpaper energy
(script flourishes, spray glow, faint bar textures). Accent source of truth:
`~/.config/nyxus/accent.json` → `nyxus-apply-accent` → shared tokens.

### Done (committed + pushed to `origin/nyxus-hyprland-055-fixes`)

| Area | Commit(s) | Notes |
|---|---|---|
| Phase 0 inventory | `ce390be` | This file |
| Living theme sync | `b8b3d03` | nyxus-living/pulsed, pulse-reactive rims |
| Keybind de-dup | `f08cd73` | 118 binds, 0 duplicates; alacritty canonical |
| Settings control center | `35af614` | Wrapper fix, 48 sections audited, dead buttons fixed |
| Flyouts + click audit | `913a3ee` | In-panel WiFi/BT/mixer/updates; 12 dead clicks fixed |
| Lock / login / splash | `1a10b3e` | hyprlock HUD; greetd login chain for ISO; galaxy-eye plymouth restored in rootfs |
| Bars + dashboard v1 | `96d6fc2` | HUD tiles, aurora fills, overlay bleed fix, neon flicker |
| Alacritty + Super+R | `8d35dbc` | Config error fixed; HUD ANSI palette |
| GTK apps HUD sweep | `9719c38` | Launcher, start, panel, welcome, etc.; fixed nyxus_chrome override bug |
| Bars polish + graffiti assets | `43a3b33` | Graffiti PNG strips, mascot sprite sheet (128 frames), bar session sync |

### Four-bar cohesion pass (2026-07-10, live `~/.config/eww/`)

| Task | Status | Notes |
|---|---|---|
| T1 Fonts + NEONFLICK wordmarks | **done** | Permanent Marker on `.ticker-label`/`.brand`; 13px + bloom; flicker dips to ~0.5 |
| T2 Rainbow Pango ticker | **done** | `ticker.sh` emits per-segment accent colors; `:markup true` on marquee label |
| T3 Mascot on bottom bar | **done** | `mascot.py` deflisten; 44×48 sprite; bar-bottom height 56px; `.bar-mascot` overflow |
| T4 Unified four-bar ink | **done** | 408830e ink + graffiti on all bars; rails `rgba(7,5,14)`; unified 38px rail pills |
| T5 Top-left cluster polish | **done** | Marker NYXUS·LIVE + NEONFLICK; HOST hud_tile unchanged |
| Liquid fills / comets | **deferred** | Next pass after cohesion QA |

**Test on NYXUS TTY:** `eww reload` then reopen bars if needed. `fc-match "Permanent Marker"` must not fall back to DejaVu.

### Not started / deferred

| Item | Notes |
|---|---|
| Full QA checklist (brief §6) | Every bar click, every keybind, fresh relogin test |
| Fresh-login / greeter test on this machine | ISO login stack built; cosmic-greeter still active here |
| `sudo nyxus-plymouth-install` | Arms galaxy-eye boot splash on **this** machine (user action) |
| Ecosystem adopt/skip picks | Research delivered; user to confirm (hyprlang migration ~Aug 2026 urgent) |
| Terminal netinstall script | "Download like a real distro" — nyxus-installer bones exist |
| Swap this machine to NYXUS-only login | After QA green; replace cosmic-greeter |
| Workspaces eye-candy pass | Indicators improved; full animation/showcase pass deferred |
| Notifications / rofi / wlogout / lock idle unified token audit | Partially done via accent engine |
| Bottom-bar access consolidation | Most modules reachable; audit vs brief §4.7 remaining |
| `main` branch reconciliation | 189 ahead / 181 behind — do not merge blindly |

### How to launch / test

- **Side-by-side (current):** COSMIC on tty1; NYXUS Hyprland on spare TTY (`Hyprland`).
- **Full session test:** Log out → greeter → pick **NYXUS Hyprland** (cosmic-greeter remembers last choice).
- **Key surfaces:** `Super+Space` launcher · `Super+grave` dashboard · `Super+A` quicksettings · `Super+0` HOME HUD · `nyxus-settings` main settings.

### GitHub sync

- **Nyxus-Core** `nyxus-hyprland-055-fixes`: sync pending commit (Session 3 eye-candy live).
- **Bifrost** (`~/Projects/bifrost`): separate project; has local uncommitted edits only (README, RELEASE_NOTES, screenshot) — not part of NYXUS build.
