# NYXUS · EWW Widget Stack

**ElKowar's Wacky Widgets** powering the NYXUS DARK MIRROR shell.

> © 2026 Joseph Sierengowski · NYX-J5W-2026-SIERENGOWSKI-LOCKED
> Replaces waybar entirely. 4 bars + 4 overlays + 3 OSD pop-ups.

---

## 1. Files

| Path | Purpose |
|---|---|
| `eww.yuck` | Widget tree, windows, defpoll variables |
| `eww.scss` | DARK MIRROR theme (violet `#a06bff`, cyan `#3ad8ff`) |
| `nyxus.conf` | User-tunable config (sourced by launcher + service) |
| `scripts/*.sh` | Data probes called by `defpoll` |
| `~/.config/systemd/user/nyxus-eww.service` | Auto-start + restart-on-failure |
| `/usr/local/bin/nyxus-eww-launch` | Daemon-wait + bar opener (logged) |

## 2. Windows

| Window | Trigger | Description |
|---|---|---|
| `bar-bottom` | auto | Main bar — 14 modules across left/center/right clusters |
| `bar-top` | auto | Live ticker (RSS/system events) + now-playing |
| `bar-left` | auto | Workspace pills 1–10 with occupied detection |
| `bar-right` | auto | App quick-launch rail (8 apps) |
| `dashboard` | clock click · `Super + ` ` ` | Full overlay: clock, calendar, weather, system, power, per-core CPU, sliders, media controls, quick toggles |
| `powermenu` | `Super + Escape` | Shutdown / restart / suspend / logout / lock |
| `cheatsheet` | `Super + /` | 3-column keybind reference |
| `osd-volume` | volume keys / right-click audio pill | Transient (1.5s) |
| `osd-brightness` | brightness keys / right-click brightness pill | Transient (1.5s) |
| `osd-mic` | (programmatic) | Transient (1.5s) |
| `screensaver` | hypridle @ 180s | Fullscreen idle clock + brand |

## 3. Bar modules (bottom bar, right cluster)

`brightness · audio · mic · network · bluetooth · battery · power-profile · updates · notifications · power`

Every pill supports left/right click and (where useful) middle/scroll. Tooltips explain available actions.

## 4. Data probes (`scripts/`)

| Script | Polled | Output keys |
|---|---|---|
| `ticker.sh` | 3s | `text`, `tooltip` |
| `sys-pulse.sh` | 2s | `cpu`, `mem`, `temp` |
| `cpu-bars.sh` | 3s | `cores[]` |
| `battery.sh` | 10s | `capacity`, `status`, `icon`, `tooltip` |
| `network.sh` | 5s | `icon`, `label`, `tooltip` |
| `bluetooth.sh` | 5s | `icon`, `label`, `tooltip`, `powered`, `connected`, `paired` |
| `audio.sh` | 2s | `icon`, `vol`, `tooltip` |
| `mic.sh` | 2s | `icon`, `mute`, `vol`, `tooltip` |
| `brightness.sh` | 5s | `percent` |
| `workspaces.sh` | 1s | `active`, `occupied[]` |
| `weather.sh` | 15m, 15m cache | `temp`, `summary` |
| `calendar.sh` | 60s | `month`, `grid` |
| `power-profile.sh` | 10s | `active`, `icon`, `label`, `tooltip` |
| `updates.sh` | 30m, 30m cache | `count`, `icon`, `label`, `tooltip` |
| `player.sh` | 2s | `status`, `title`, `artist`, `icon`, `tooltip` |
| `notifications.sh` | 3s | `icon`, `label`, `tooltip`, `paused`, `total` |
| `osd-show.sh` | helper | Opens window, closes after `NYXUS_OSD_DURATION` (default 1.5s) |

All probes JSON-escape via `jq` so quotes/backslashes in dynamic strings (SSIDs, device names, song titles, weather descriptions) cannot break the defpoll parse.

## 5. Configuration (`nyxus.conf`)

| Variable | Default | Description |
|---|---|---|
| `NYXUS_EWW_BARS` | `bar-bottom bar-top bar-left bar-right` | Subset of bars to open |
| `NYXUS_EWW_TIMEOUT` | `30` | Daemon socket-wait timeout (seconds) |
| `NYXUS_EWW_LOG_DIR` | `~/.cache/nyxus-eww` | Log destination |
| `NYXUS_WEATHER_LOCATION` | (geo-IP) | wttr.in location override |
| `NYXUS_OSD_DURATION` | `1.5` | OSD pop-up duration (seconds) |
| `NYXUS_SCREENSAVER_ENABLED` | `true` | Enable hypridle screensaver overlay |

After editing, reload with: `systemctl --user restart nyxus-eww`.

## 6. Lifecycle

1. Hyprland starts.
2. `exec-once = nyxus-wait-bootstrap nyxus-eww-launch` runs.
3. Or, if you prefer the systemd path: `systemctl --user enable --now nyxus-eww.service`.
4. Daemon comes up → `nyxus-eww-launch` waits (wall-clock deadline) for the IPC socket, then opens every bar listed in `NYXUS_EWW_BARS`.
5. All actions log to `${NYXUS_EWW_LOG_DIR}/launch.log` and `daemon.log`.

## 7. Replaces

| Python module | Status |
|---|---|
| `nyxus_powermenu.py` | Replaced by `powermenu` window |
| `nyxus_quicksettings.py` | Replaced by `dashboard` window |
| `nyxus_clock.py` / `nyxus_calendar.py` | Replaced by dashboard cards |
| `nyxus_cheatsheet.py` | Replaced by `cheatsheet` window |
| Volume/brightness OSDs | Replaced by `osd-*` windows |
| Idle screen | Replaced by `screensaver` + hypridle pipeline |

The Python modules **remain installed** until the audit confirms parity, then they are removed in a single sweep.

## 8. Theme tokens

```
--violet  #a06bff
--cyan    #3ad8ff
--ink     #05060a
--paper   #c8ccd6
--mute    #5a6278
--alert   #ff5577
--warn    #ffb04a
--ok      #4ade80
```

## 9. Troubleshooting

```sh
# tail launcher + daemon logs
tail -F ~/.cache/nyxus-eww/*.log

# manual restart
systemctl --user restart nyxus-eww
# or, without systemd
eww kill && eww daemon && nyxus-eww-launch

# verify socket
ls -la "${XDG_RUNTIME_DIR}/eww-server_default"
```
