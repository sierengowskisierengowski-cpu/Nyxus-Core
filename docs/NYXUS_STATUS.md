# NYXUS Status — Legend Build Safepoint

**Safepoint date/time:** 2026-07-14 09:07 EDT  
**Branch:** `cursor/restore-last-night-state-15e2`  
**Latest commit:** at tag `nyxus-good-state-2026-07-14-legend` — run `git log -1 --oneline`  
**Safepoint tag:** `nyxus-good-state-2026-07-14-legend`

---

## COMPLETED

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
- Wire companion autostart into `hyprland.conf`
- Wire notification sounds into bridge *(partially done — chimes in bridge; verify end-to-end after login)*
- Settings/Hub sound toggle UI
- Phase 2.4 backdoor login keybind
- Phase 2.7/2.8 reboot verify + safepoint
- kage-ryu kernel boot validation
- Phase 8 E2E test + v1.0 tag
- Merge branch to `main`
- Extend `nyxus-restore-desktop.sh` to deploy `companion/` + `nyxus-companion` + `nyxus-sound` helpers

---

## KNOWN ISSUES / USER ACTION NEEDED

1. **Log out / log back in** — Verify EWW bars autostart and full session stack after restore.
2. **Greeter flash fix** — Run `sudo scripts/nyxus-setup-greetd.sh` then reboot for greetd/regreet login flash fix.
3. **Broken cache symlink** — `sudo rm /opt/nyxus-cache` (broken symlink on this host).
4. **Live vs repo drift** — `~/.config/hypr/hyprland.conf` on disk may lag repo (repo has Phase 3 keybind consolidation); run restore to sync.
5. **Companion not autostarted** — Launch manually: `nyxus-companion start` until hyprland exec-once is wired.

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

**Deploy companion + sounds after restore (manual until restore script updated):**

```bash
mkdir -p ~/.local/share/nyxus/companion ~/.local/share/nyxus/sounds
cp -a artifacts/api-server/nyxus-scripts/companion/. ~/.local/share/nyxus/companion/
cp -a artifacts/api-server/nyxus-scripts/sounds/*.ogg ~/.local/share/nyxus/sounds/
install -m 0755 artifacts/api-server/nyxus-scripts/companion/nyxus-companion ~/.local/bin/
install -m 0755 artifacts/api-server/nyxus-scripts/nyxus-sound ~/.local/bin/
install -m 0755 artifacts/api-server/nyxus-scripts/nyxus-sound-bake ~/.local/bin/
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
