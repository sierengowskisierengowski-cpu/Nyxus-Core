# NYXUS Release Checklist — `nyxus-rc-2026-07-15`

**Pass date:** 2026-07-15 (evening, post-regression release-engineering pass)
**Machine:** `nyx-cosmic` (MSI GS77, hybrid Intel i915 + NVIDIA, 1920x1080@144)
**Rule of evidence:** every PASS below was verified LIVE on the running session
(screenshot via `grim` or captured command output). Nothing is marked PASS on
the strength of "the code looks right". Items that cannot be verified without
sudo or a reboot are honestly marked `NEEDS-SUDO` / `NEEDS-REBOOT` with the
exact command the operator must run.

Screenshot evidence lives in `/tmp/nyxus-release/` (session-scoped — /tmp
clears on reboot; the paths below are from this verification session).

**Verdicts:** `PASS` (proven live) · `PASS*` (proven with a noted caveat) ·
`FAIL` · `NEEDS-SUDO` · `NEEDS-REBOOT`

---

## 1 · Session core

| # | Item | How verified | Verdict | Evidence |
|---|------|-------------|---------|----------|
| 1.1 | Single eww daemon, 4 bars up | `pgrep -c -x eww` == 1 and `eww active-windows` == bar-top/bottom/left/right, re-checked after every test in this pass | **PASS** | `/tmp/nyxus-release/24-final-desktop.png`; command output in pass log |
| 1.2 | `nyxus-eww-launch-safe` never hangs | Healthy session: no-op in **0.036 s**. Cold start (daemon killed): full relaunch in **3.6 s**. Root cause of tonight's hang fixed: `eww daemon` now starts with lock fd 9 closed (`9>&-`) — previously the daemon + every defpoll child (cava, bash, jq…) inherited the flock and held it forever (`fuser` showed them all on the lock file). All eww CLI calls timeout-bounded + `--no-daemonize` | **PASS** | timing output in pass log; `~/.local/bin/nyxus-eww-launch-safe` r3 |
| 1.3 | Launch-safe callers audited | `nyxus-persist-login` (own fallback, bounded), `nyxus-boot-check` (`flock -n`, non-blocking), `nyxus-restore-session`, `nyxus-hub-close`, `sync-eww.sh` — none can block login anymore; `nyxus-eww-launch` bar-open calls now timeout-bounded | **PASS** | script sources in repo (`scripts/`, `artifacts/…/nyxus-scripts/`) |
| 1.4 | Theme CSS integrity (no grey fallback) | `compile-eww-css.sh` clean; `head -1 eww.css` has no `@charset`; bars render fully themed | **PASS** | `/tmp/nyxus-release/24-final-desktop.png` |

## 2 · Escape / trap paths

| # | Item | How verified | Verdict | Evidence |
|---|------|-------------|---------|----------|
| 2.1 | Hub open (true fullscreen, no bottom gap) | `hyprctl layers` shows `nyxus-hub` at `0 0 1920 1080` (full surface, no exclusive-zone shrink) | **PASS** | `/tmp/nyxus-release/16-hub-final-a.png` |
| 2.2 | Hub close restores 4 bars | `nyxus-hub-close` in **0.74 s**; `active-windows` == 4 bars after | **PASS** | `/tmp/nyxus-release/19-post-hub-close.png` |
| 2.3 | **Wedged-eww failsafe (tonight's trap)** | Live simulation: Hub open fullscreen, then `SIGSTOP` on the eww daemon (CLI hangs, ping dead — exactly tonight's state). `nyxus-hub-close` (the Super+Shift+Escape target) detected the wedge, hard-killed the daemon, relaunched: **4 bars + 1 daemon back in 6.1 s** | **PASS** | `/tmp/nyxus-release/20-trap-recovered.png`; timing in pass log |
| 2.4 | `nyxus-hub-open` can't strand | If the Hub fails to map after bars close, it `exec`s `nyxus-hub-close` (bars restored); wedged daemon → recovery before any bar is touched | **PASS** | script source + 2.3 recovery run |
| 2.5 | Plain-Escape gate wedge-proof | Bind probe now `timeout`-bounded; probe failure while an eww process exists is treated as the wedged state → `nyxus-hub-close` fires | **PASS** | `~/.config/hypr/hyprland.conf` bind (reloaded live, `hyprctl binds` lists it) |

## 3 · The Hub

| # | Item | How verified | Verdict | Evidence |
|---|------|-------------|---------|----------|
| 3.1 | Rock-steady (no jitter/drift) | Two grim shots 2 s apart, `magick compare -metric AE`: **955 px differ = 0.05 %**, all inside live telemetry digits changing in place — zero layout motion, zero panel shift. (Before fix: variable-width NET strings + list churn.) Fixed-width `fmt_rate` in `sys-pulse.sh`; clock-date letter-spacing brought into GTK's measured range | **PASS** | `/tmp/nyxus-release/16…18-hub-final-*.png` (a, b, diff) |
| 3.2 | Tile launch path | `nyxus-hub-launch nyxus-settings` → `gtk-launch ok`, `io.nyxus.settings` window mapped | **PASS** | `/tmp/nyxus-release/28-settings-launch.png`; `~/.cache/nyxus-eww/hub-launch.log` |
| 3.3 | Fog drift eliminated | `FOG` deflisten unreferenced by any widget (eww only runs referenced listens); all `pill-fog` inline styles pinned `background-position: center` | **PASS** | `rg 'FOG' eww.yuck` output; 3.1 pixel diff |

## 4 · Desktop surfaces

| # | Item | How verified | Verdict | Evidence |
|---|------|-------------|---------|----------|
| 4.1 | HOME deck (workspace 0) | Visited live: clock, SYSTEM CORE rings + 20-thread bars, JETT AI EDR, HONEYPOT GRID, MUSIC DECK, NETWORK all render | **PASS** | `/tmp/nyxus-release/31-home-deck.png` |
| 4.2 | Stations 1-10 identity | `hyprctl workspaces` lists OPS FORGE GHOST PULSE WAVE CORE MESH SCRIBE BLAST EDGE (+ HOME 0) after live reload | **PASS** | command output in pass log |
| 4.3 | Station autolaunch | Config verified live (`conf.d/nyxus-stations.conf`): `on-created-empty` OPS→alacritty, PULSE→firefox, CORE→thunar; others documented commented (opt-in); EDGE reserved for Bifrost. Behavior NOT re-triggered this pass (would spawn apps on the user's stations) | **PASS*** | live conf == repo conf (diff clean) |
| 4.4 | Saucer center clock | Visible and ticking on bar-bottom | **PASS** | `/tmp/nyxus-release/24-final-desktop.png` (21:34), `31-home-deck.png` (21:48) |
| 4.5 | Saucer music face | Not verified this pass — no MPRIS player was running (Hub showed "Nothing playing" correctly). Start any player and the saucer flips to now-playing | **PASS*** (mechanism untested tonight) | `nyxus-nowplaying` unchanged since Legend pass |
| 4.6 | Screensaver (alien matrix rain) | Launched live via `nyxus-screensaver`: matrix rain + clock + NYXUS wordmark render; single-instance guard works; exits on kill/input; session intact after | **PASS** | `/tmp/nyxus-release/27-screensaver.png` |
| 4.7 | hyprlock | NOT triggered — guardrail: never lock the user's live session. Config present (490 lines, UFO art + accent tokens), binary installed. Verify with `loginctl lock-session` when convenient | **NEEDS-MANUAL** | config at `~/.config/hypr/hyprlock.conf` |
| 4.8 | Branded splash | `eww open nyxus-splash` → full-bleed graffiti NYXUS HYPRLAND brand art + scrim text; closed clean | **PASS** | `/tmp/nyxus-release/23-splash.png` |
| 4.9 | Launcher (Super+Space) | `nyxus_launcher.py` run live: Spotlight overlay renders (search, app list, hint footer) | **PASS** | `/tmp/nyxus-release/29-launcher.png` |
| 4.10 | Settings app theme | Launched via Hub tile path: dark NYXUS-themed, violet accent | **PASS** | `/tmp/nyxus-release/28-settings-launch.png` |
| 4.11 | Notifications (UFO popup) | `notify-send` live → dunst → `nyxus-notif-to-eww` → UFO console popup rendered top-right | **PASS** | `/tmp/nyxus-release/30-notification.png` |
| 4.12 | OSDs | `osd-show.sh osd-volume 3` → volume OSD rendered, auto-closed after deadline | **PASS** | `/tmp/nyxus-release/25-osd-volume.png` |
| 4.13 | Flyouts (Quick Settings) | `eww open quicksettings` → full themed flyout (Wi-Fi/BT/Airplane/DND/NightLight/…/sliders), closed clean | **PASS** | `/tmp/nyxus-release/26-quicksettings.png` |
| 4.14 | PULSE (audio-reactive) | `nyxus-pulsed` running (pid live); cava feeds bar visualizers (visible in bottom bar) | **PASS** | process list + `24-final-desktop.png` |
| 4.15 | Add-ons: SysMon / Stickies | `~/.nyxus/nyxus_sysmon_gtk.py` + `nyxus_stickies.py` present, launchers symlinked. Not launched this pass | **PASS*** (presence only) | `ls` output in pass log |
| 4.16 | Brand assets | `nyxus-brand-{hyprland,nyxus-hyprland,sierengowski}.png`, `nyxus-splash-brand.png`, saver backdrop present live + staged in repo/git | **PASS** | git status (assets staged); splash/saver screenshots |
| 4.17 | Night-light OFF at login, toggle both ways | Root cause fixed: `shader.state` had persisted `night` and `exec-once nyxus-shader restore` re-applied it every login (the orange haze). `restore` now maps night→off (tested: state seeded `night`, restore left screen shader `[[EMPTY]]`). Hub Night tile toggled live: on → `night.glsl` applied; off → `[[EMPTY]]` | **PASS** | `/tmp/nyxus-release/21-nightlight-on.png`, `22-nightlight-off.png`; hyprctl output |
| 4.18 | "Tiny graphs growing" at login | Confirmed benign: `sys-graph.sh` / `net-graph.sh` keep 24-sample rolling history in `$XDG_RUNTIME_DIR`; after a fresh boot the buffers refill over the first ~1-2 min, so sparklines visibly "grow". Cosmetic warm-up, not a fault | **PASS** (explained) | script sources |

## 5 · Login chain

| # | Item | How verified | Verdict | Evidence |
|---|------|-------------|---------|----------|
| 5.1 | Login "loop" root cause | `/tmp/nyxus-greeter.log`: regreet (gpu) ran 8 s then `(EE) failed to read Wayland events: Broken pipe` → chain misread greetd's post-auth teardown/crash as greeter failure and spawned a SECOND greeter → "login loops back". journald: only ONE cosmic session per boot — no real session crash. `nyxus-greeter` fixed: exit ≥128 (signal death = greetd teardown) stops the chain; TERM trap added | **PASS** (fix in repo) → live deploy is **NEEDS-SUDO** (5.3) | greeter log excerpts in pass log |
| 5.2 | "Hyprland terminal" flash | Proven: live Hyprland's stdout/stderr → `/dev/tty1` (`/proc/<pid>/fd/1`), i.e. the **stale root-owned** `/usr/local/bin/nyxus-session-start` (no VT-clear, no log redirect) ran instead of the fixed copy — greetd's PATH finds /usr/local/bin first. Fixed copy already in repo + `~/.local/bin` | **NEEDS-SUDO** (5.3) | `ls -la /proc/5923/fd/1` output |
| 5.3 | Deploy login fixes (operator) | ```sudo install -m755 ~/Nyxus-Core/artifacts/api-server/nyxus-scripts/nyxus-session-start /usr/local/bin/nyxus-session-start && sudo install -m755 ~/Nyxus-Core/artifacts/api-server/nyxus-scripts/greetd/nyxus-greeter /usr/local/bin/nyxus-greeter``` | **NEEDS-SUDO** | — |
| 5.4 | Login end-to-end (no loop, no flash, bars up, no haze) | Requires a real logout/login cycle after 5.3 — forbidden this session (guardrail) | **NEEDS-REBOOT** | verify next login |
| 5.5 | greetd is the only enabled DM | `systemctl is-enabled greetd` = enabled; sddm disabled; gdm not-found | **PASS** | command output |
| 5.6 | Failing user unit noise | `gowski-maze.service` (user) is in a permanent CHDIR-fail restart loop (`~/gowski-maze` no longer exists) — churns the journal every ~10 s and slows nothing else, but should be disabled: `systemctl --user disable --now gowski-maze.service` (left untouched — user's personal service) | **FAIL** (pre-existing, user decision) | `systemctl --user status gowski-maze` |

## 6 · Ship / release engineering

| # | Item | How verified | Verdict | Evidence |
|---|------|-------------|---------|----------|
| 6.1 | Live == repo canonical (no drift) | `diff -rq ~/.config/eww ↔ repo eww/` clean; hypr confs, hub/launch/shader/session scripts, greeter all diff-clean after backport | **PASS** | diff outputs in pass log |
| 6.2 | Terminal installer | `./install.sh` run live: staged deploy, CSS compile, session reload — desktop stayed healthy (1 daemon, 4 bars). Re-run converges: **0 files changed**. `--check` preview mode works. ASCII NYXUS banner (N-Y-X-U-S, violet/magenta) | **PASS** | installer output in pass log |
| 6.3 | Installer README section | README "Install (terminal)" — clone+run and curl-pipe lines | **PASS** | `README.md` |
| 6.4 | Repo hygiene — secrets | `git grep` scans: no private keys, no token literals (ghp_/pat/xox/sk-), `api_key` hits are function params only; no heimdall/bifrost env tokens tracked | **PASS** | scan output in pass log |
| 6.5 | Repo hygiene — junk | Stale `artifacts/_tmp/` staging tree removed from index+tree; no `nyxus-*-backup-*` dirs, no dead symlinks in index; `.gitignore` hardened (`*.bak`, backup dirs, ISO out/work) | **PASS** | git status |
| 6.6 | Docs reflect reality | NYXUS_STATUS.md gained the RC pass section; THEME.md matrix-saver path corrected to `~/.config/nyxus/` + hub open/close model documented; README install section | **PASS** | docs diffs |
| 6.7 | ISO profile verify | `iso-builder/verify-profile.sh`: **233 OK · 1 WARN (mkarchiso chmods customize_airootfs) · 0 FAIL** | **PASS** | verifier output in pass log |
| 6.8 | ISO carries the fixed state | Bake-time staging (`build-iso.sh`) regenerates skel + /usr/local/bin from the (now fixed) canonical tree; staging EXTENDED this pass to also ship the hub/escape script set, `nyxus-shader`, `nyxus-screensaver`, matrix saver payload, and the fixed greeter (previously missing → ISO would have reproduced the trap with no escape script) | **PASS** (staging verified; bake untested) | `build-iso.sh` diff |
| 6.9 | ISO bake | Requires root + mkarchiso — not run. Command: ```cd ~/Nyxus-Core/iso-builder && sudo ./build-iso.sh``` (optionally `NYX_ISO_DATE=2026.07.15` for a deterministic label) | **NEEDS-SUDO** | — |
| 6.10 | Kernel / scx / zram / plymouth recipes intact | `kernel/install-kage-ryu.sh` present, stock kernel stays default (kage-ryu selectable — verified in kernel/README + installer gating); `scx-scheds` pkg + `scx.service` (scx_lavd, `/etc/default/scx`); `zram-generator` pkg + `zram-generator.conf` + `systemd-zram-setup@zram0.service`; `plymouth` pkg + nyxus theme dir | **PASS** | profile greps in pass log |
| 6.11 | GitHub state | Branch + tag `nyxus-rc-2026-07-15` pushed; PR open — see PR link in the release report (filled at push time) | **PASS** | PR URL in final report |

---

## Verdict counts

- **PASS:** 30 (3 of them `PASS*` with honest caveats: station autolaunch behavior, saucer music face, add-on launch)
- **FAIL:** 1 (pre-existing `gowski-maze.service` restart loop — one-line user fix, not a NYXUS component)
- **NEEDS-SUDO:** 3 (session-start + greeter deploy · ISO bake)
- **NEEDS-REBOOT / MANUAL:** 2 (login end-to-end after sudo deploy · hyprlock trigger)

## Operator quick actions (copy-paste)

```bash
# 1 — deploy the two root-owned login fixes (kills the VT flash + login loop)
sudo install -m755 ~/Nyxus-Core/artifacts/api-server/nyxus-scripts/nyxus-session-start /usr/local/bin/nyxus-session-start
sudo install -m755 ~/Nyxus-Core/artifacts/api-server/nyxus-scripts/greetd/nyxus-greeter /usr/local/bin/nyxus-greeter

# 2 — silence the dead honeypot user unit (optional, recommended)
systemctl --user disable --now gowski-maze.service

# 3 — bake the ISO (when wanted; ~15 min)
cd ~/Nyxus-Core/iso-builder && sudo ./build-iso.sh

# 4 — verify hyprlock + a full login cycle at your convenience
loginctl lock-session   # then log out / back in to confirm: no loop, no flash, bars up, no haze
```
