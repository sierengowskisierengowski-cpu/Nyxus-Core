# NYXUS Status — Release Candidate

**Updated:** 2026-07-15 (late) · release-engineering pass `nyxus-rc-2026-07-15`
**Prior safepoint:** `nyxus-good-state-2026-07-14-legend` (Legend build, below)

---

## 2026-07-15 (LATE) — RELEASE-ENGINEERING PASS (`nyxus-rc-2026-07-15`)

Root-cause fixes for the evening regression (eww launch hang → no bars at
login; Hub fullscreen trap; night-filter haze at login; greeter "login
loop"), plus the terminal installer and the release checklist. Every fix was
verified LIVE and backported to the canonical ship tree — see
`docs/RELEASE_CHECKLIST.md` for per-item evidence.

| Area | What shipped |
|------|--------------|
| **eww launch never hangs** | `nyxus-eww-launch-safe` r3: healthy-session fast-path (no daemon churn), numeric-validated bounded `flock` waits, and — the true root cause — `eww daemon` now starts with the lock fd closed (`9>&-`). Previously the daemon and every defpoll child (cava, bash, hyprctl…) inherited fd 9 and held the launch lock FOREVER, so the next launcher blocked and login came up bar-less. All eww CLI calls in the launch/close path are `timeout`-bounded (a wedged daemon blocks the bare CLI indefinitely) and use `--no-daemonize` so a CLI can never fork a rogue second daemon. |
| **Hub trap killed** | `nyxus-hub-open` restores the bars immediately if the Hub fails to map; `nyxus-hub-close` ping-checks first and hard-recovers a wedged daemon (`pkill -9` → `nyxus-eww-launch-safe`). Wedge scenario tested live via SIGSTOP on the daemon: Super+Shift+Escape path recovered 4 bars + single daemon in ~6s. Plain-Escape gate is timeout-bounded and treats a wedged daemon as "needs recovery". |
| **Hub rock-steady** | Residual "moves on its own" pinned: NET tile rate strings now fixed-width (`sys-pulse.sh` `fmt_rate`), hub clock-date letter-spacing brought into GTK's measured range (was ellipsizing). Proof: two screenshots 2s apart differ only in live digits (955 px = 0.05%, zero layout motion). |
| **Night-light OFF at login** | Root cause of the orange haze: Hub "Night" tile → `nyxus-shader night` persisted in `shader.state` and `exec-once = nyxus-shader restore` re-applied it every login. `restore` now maps `night`→`off` (night is session-transient; artistic filters still persist). Toggle verified both ways live. |
| **Login loop / terminal flash** | greetd kills the greeter (cage) on successful auth; the fallback chain misread that signal-death as a crash and spawned a SECOND greeter — the "login loops back" effect. `nyxus-greeter` now treats exit≥128 as teardown and stops. The "hyprland terminal" flash: the stale root-owned `/usr/local/bin/nyxus-session-start` (no VT-clear/log-redirect) shadows the fixed copy — needs one sudo `install` (see RELEASE_CHECKLIST). |
| **Terminal installer** | `install.sh` at repo root: NYXUS ASCII banner, staged deploy (deps → configs → CSS compile → live reload → summary) onto all live surfaces, curated launcher manifest, idempotent (re-run converges to 0 changes — verified). README gained an Install section. |
| **Repo hygiene** | Stale `artifacts/_tmp/` staging tree removed from the ship; `.gitignore` hardened (backup dirs, `*.bak`, ISO work dirs); secret scan clean (no tokens/keys in tracked content). Matrix saver ship copy added (`nyxus_matrix_saver.py`) — was live-only. |

---

## 2026-07-15 — DAILY-DRIVER READINESS PASS

Desktop-scope readiness work (eww/hypr configs, HOME dashboard, splash, docs,
repo hygiene). Session kept `pgrep -c -x eww` == 1 throughout; no
reboot/logout/lock.

| Area | What shipped |
|------|--------------|
| **Station naming reconciliation** | Ended the split-brain: `nyxus-hyprland-general.conf` no longer defines `WEB/CODE/TERM/FILES/MEDIA/COMMS`. Workspace 1-10 identity now has ONE source — `conf.d/nyxus-stations.conf` (sourced from `hyprland.conf`) — matching `~/.config/nyxus/stations.json` and the EWW left rail: **OPS · FORGE · GHOST · PULSE · WAVE · CORE · MESH · SCRIBE · BLAST · EDGE**. Verified via `hyprctl workspaces`. |
| **Station auto-launch** | `on-created-empty` wired for a small "ready to work" login set — OPS→`alacritty`, PULSE→`firefox`, CORE→`thunar`. Every other station documents its signature app on a commented line (opt-in). Station 10 (EDGE) reserved as the landing pad for the forthcoming NYXUS master hub (Bifrost) — launch left commented pending confirmation. |
| **HOME dashboard render fix** | Workspace-0 `nyxus-home` GTK4 dashboard was rendering **blank** — the auto-injected `nyxus_chrome` present-hook called `overlay.add_overlay(cur)` on the window's own `Gtk.Overlay` while it still had a parent ("already has parent"), orphaning the whole card grid. Pre-arming the chrome re-entrancy guard in `nyxus-home/main.py` skips the redundant cosmic wrap (HOME builds its own `CosmicSceneArea`). Full deck now renders: giant clock, weather, SYSTEM CORE rings + per-core bars, JETT AI EDR, HONEYPOT GRID, MUSIC DECK, NETWORK, Fans/Storage/Calendar/Notepad/Processes/Notifications/Password. |
| **Branded urban splash** | Session-start splash upgraded from the plain starfield/text curtain to the full-bleed graffiti brand art (`assets/nyxus-splash-brand.png`, pre-scaled 1920x1080 so it covers despite the compile step stripping `background-size`). Top/bottom scrim keeps the boot text legible. GTK-valid, no grey fallback. |
| **Stale-file cleanup** | Removed Tokyo-Night rofi leftover `~/.config/rofi/nexus.rasi` (nothing sourced it) and dangling symlink `~/.local/bin/pmos-james`. |

---

## COMPLETED (Legend build · 2026-07-14)

Work landed across agents in this session (newest first):

| Area | What shipped |
|------|--------------|
| **Sound theme** | 10 synthesized Ogg Vorbis events (`startup`, `login`, `logout`, `lock`, `unlock`, `notification`, `alert`, `app-open`, `error`, `success`); `nyxus-sound` + `nyxus-sound-bake`; wired into login/lock/unlock/logout (hyprland + hypridle) |
| **Sound wiring (this safepoint)** | Notification chimes in `nyxus-notif-to-eww` (CRITICAL → `alert`, else `notification`); debounced OSD tick in `osd-show.sh` (`app-open`) |
| **Urban re-theme** | Violet scrollbars, urban marker font on panel titles, settings accent gold → NYXUS urban violet |
| **Startup fixes** | Reliable EWW/wallpaper autostart; kill greeter login flash; yellow-tint shader addressed |
| **UFO notification popup** | Dunst → EWW bridge (`nyxus-notif-to-eww`); UFO-console popup widget; `nyxus-dunstrc` icon path |
| **Bottom bar** | Stacked dual-fan + net cells, RAM graph, balanced 3-per-side layout |
| **Center clock** | UFO saucer center clock on bottom bar |
| **Grey bars fix** | Root cause: one invalid CSS property stripped at compile — full theme restored |
| **The Hub** | Renamed "The Hub"; app launcher; NYXUS/ALL toggle (`nyxus-hub-apps`, `nyxus-nowplaying`) |
| **Hero backdrops** | Hub crew meet + power menu body shop (scrim for readability) |
| **Urban art set** | Alien-hero wallpaper, hyprlock UFO, panel nebula, notification frame assets |
| **Login / greetd pivot** | greetd + regreet configs; never-lock-out fallback chain (`nyxus-persist-login`, `nyxus-restore-login`, `nyxus-boot-check`) |
| **Phase 1 consolidation** | Canonical source under `artifacts/api-server/nyxus-scripts/`; `nyxus-restore-desktop.sh`; prior tags `consolidated-takeover-2026-07-14`, `phase-1-complete-2026-07-14`, `nyxus-good-state-2026-07-14-bars-art` |
| **Alien companion (v1)** | `companion/companion.py` GTK4 layer-shell engine; placeholder sprite frames + manifest; `nyxus-companion` launcher; state machine (idle/sleep/notify/alert/workspace/flair) |
| **Companion deploy (this safepoint)** | `hyprland.conf` exec-once autostart; `nyxus-restore-desktop.sh` stages companion + sounds + launchers |

---

## IN PROGRESS

Agents may still be running or work is partially landed:

- **Sound deferred wiring** — Some OSD/notification paths now wired; Settings/Hub mute toggle UI not done
- **Alien companion** — Placeholder sprites only; click/laugh/voice reactions not implemented
- **Living wallpaper** — Scripts exist (`nyxus-living`, `nyxus-live-wallpaper`); parallax nebula + drifting UFO not finished
- **Cinematic boot sequence** — Plymouth UFO landing not integrated
- **Voice control** — Wake-word commands not started

---

## TODO / REMAINING

- Companion: polished sprite frames, click reactions, alien laugh/voice lines
- Living wallpaper (parallax nebula + drifting UFO)
- Cinematic boot (Plymouth UFO landing)
- Voice control (wake-word commands)
- Settings app deeper visual overhaul
- Wire companion autostart into `hyprland.conf` *(done this safepoint — `exec-once` via `nyxus-companion start`)*
- Wire notification sounds into bridge *(partially done — chimes in bridge; verify end-to-end after login)*
- Settings/Hub sound toggle UI
- Phase 2.4 backdoor login keybind
- Phase 2.7/2.8 reboot verify + safepoint
- kage-ryu kernel boot validation
- Phase 8 E2E test + v1.0 tag
- Merge branch to `main`
- Extend `nyxus-restore-desktop.sh` to deploy `companion/` + `nyxus-companion` + `nyxus-sound` helpers *(done this safepoint)*

---

## KNOWN ISSUES / USER ACTION NEEDED

Flagged by the 2026-07-15 readiness pass (each needs sudo / a reboot / a
package install / a user decision — intentionally NOT auto-applied):

1. **Root-owned cache symlink** — `sudo rm /opt/nyxus-cache` (root-owned broken
   symlink → `…/GowskiNet-Vault/OS/Nyxus-Core/artifacts/api-server/dist/nyxus-scripts`;
   needs sudo, so left for the user).
2. **Plymouth cinematic boot splash** — `sudo scripts/nyxus-setup-plymouth.sh`
   (needs sudo; not deployed).
3. **greetd greeter verification** — needs a reboot to confirm the login flash
   fix / greeter theme.
4. **Voice control (Vosk)** — `nyxus-voice-install` needs a package + model
   download; not installed.
5. **Companion art redo + re-enable** — placeholder sprites only; needs an art
   decision before re-enabling autostart.
6. **Station master-hub launch** — station 10 (EDGE) reserved for Bifrost; the
   `on-created-empty` line is commented pending the Bifrost build landing and a
   confirmed launch command (currently only a shell alias, not a PATH binary).
7. **Fuller station auto-launch** — only OPS/PULSE/CORE auto-launch at login by
   default; uncomment the per-station lines in `conf.d/nyxus-stations.conf` to
   opt each remaining station into launching its signature app.

Recent regression-guard fixes confirmed intact this pass: all EWW overlays
`:focusable false` (keyboard-trap fix), `nyxus-hub-close`, Escape /
Super+Shift+Escape binds, redesigned Hub (`nyxus_hub_layout`), saucer/music
widgets + `.saucer-*` CSS, hyprlock (UFO art), matrix screensaver, NYXUS PULSE.

---

## SAFEPOINT TAG

```
nyxus-good-state-2026-07-14-legend
```

Message: *Legend build safepoint: UFO theme, sounds, companion, startup fixes, urban re-theme*

---

## HOW TO RESTORE

From any clone of Nyxus-Core:

```bash
git fetch origin
git checkout nyxus-good-state-2026-07-14-legend
bash scripts/nyxus-restore-desktop.sh
```

Then log out and back in (or reboot for greetd changes).

**One-shot without an existing clone:**

```bash
git clone --depth 1 -b cursor/restore-last-night-state-15e2 \
  https://github.com/sierengowskisierengowski-cpu/Nyxus-Core /tmp/nyxus-restore
cd /tmp/nyxus-restore
git checkout nyxus-good-state-2026-07-14-legend
bash scripts/nyxus-restore-desktop.sh
```

**Deploy companion + sounds after restore** — `nyxus-restore-desktop.sh` now stages these automatically. Manual fallback:

```bash
mkdir -p ~/.local/share/nyxus/companion ~/.local/share/nyxus/sounds
cp -a artifacts/api-server/nyxus-scripts/companion/. ~/.local/share/nyxus/companion/
cp -a artifacts/api-server/nyxus-scripts/sounds/*.ogg ~/.local/share/nyxus/sounds/
install -m 0755 artifacts/api-server/nyxus-scripts/companion/nyxus-companion ~/.local/bin/
install -m 0755 artifacts/api-server/nyxus-scripts/nyxus-sound ~/.local/bin/
nyxus-companion start
```

---

## FILES EXCLUDED FROM GIT (intentional)

- `artifacts/api-server/nyxus-scripts/nyxus-persist-login` — absolute-path symlink to `scripts/`
- `artifacts/api-server/nyxus-scripts/nyxus-restore-login` — absolute-path symlink to `scripts/`
- `~/.config/nyxus/accent.json`, `sound.state`, `shader.state` — live runtime state
- Secrets / credentials (none committed)

---

*Generated 2026-07-14 by safepoint agent. Update this file at the next milestone.*
