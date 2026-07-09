# NYXUS — STATE.md (Phase 0 Reconciliation Inventory)

Date: 2026-07-09 · Branch: `nyxus-hyprland-055-fixes` · Hyprland 0.55.4 · eww 0.5.0

This is the "what exists today" baseline: local machine vs. GitHub, plus every
duplicate, orphan, and stale reference found. **Update 2026-07-09 (Session 2):
the keybind de-dup / orphan-removal decisions were made and implemented** —
§4–§7 and §10 now reflect the *resolved* state; §5b lists intentional keeps
that must never be re-flagged as legacy/orphans.

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
- **Settings:** `nyxus-settings` (main app) + quicksettings eww panel
  (`nyxus-qsd`) — *intentional* per user; still needs the
  canonical-vs-quick-access relationship documented and both themed.
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

## 10. Session 2 decisions — status

1. ~~Canonical terminal~~ → **DECIDED + IMPLEMENTED: alacritty** (§5/§6).
2. ~~Legacy `~/.nyxus` bindings~~ → **DECIDED + IMPLEMENTED:** terminal
   retired in favor of alacritty; launcher/screenshot/doctor are canonical
   keeps (§5b).
3. ~~Keybind conflicts~~ → **DECIDED + IMPLEMENTED:** signature layer wins
   all three; losers moved to `Super+J` / `Super+Alt+S` or removed (§4).
4. ~~swaync + hyprpaper~~ → **DECIDED + IMPLEMENTED: deleted** (§6).
5. Advanced escape hatches (§8): replace with themed in-panel pages, or
   theme-wrap the external tools? — **still open**.
6. Should `nyxus-home/-panel/-start/-stickies` config dirs be added to
   `sync-live-config.sh` CONFIG_DIRS? — **still open**.
7. ~~`nyxus-fx.conf`~~ → **DECIDED + IMPLEMENTED: folded into
   nyxus-signature.conf** (spray on `Super+Z`), file deleted (§7).
